"""Tick-to-scalar aggregation functions (canonical home).

All tick-level → scalar computations live here. Feature layers in
features/*.py re-export these for backward compatibility.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.signal import fftconvolve

# ---------------------------------------------------------------------------
# HAR core measures
# ---------------------------------------------------------------------------


def compute_realized_variance(
    intraday_returns: pd.Series,
) -> float:
    """Compute realized variance from intraday returns.

    RV_t = sum(r_{t,i}^2).  No mean subtraction (Andersen et al. 2003).
    """
    r = np.asarray(intraday_returns, dtype=np.float64)
    return float(np.sum(r**2))


def compute_rq(
    intraday_returns: pd.Series,
) -> float:
    """Compute realized quarticity (RQ) for measurement quality.

    RQ = (N/3) * sum(r_i^4) where N is the number of intraday observations.
    """
    r = np.asarray(intraday_returns, dtype=np.float64)
    n = len(r)
    return float((n / 3.0) * np.sum(r**4))


# ---------------------------------------------------------------------------
# Asymmetry measures
# ---------------------------------------------------------------------------


def compute_semivariances(
    intraday_returns: pd.Series,
) -> dict[str, float]:
    """Compute positive and negative realized semivariances.

    RS+ = sum(r_i^2 * I(r_i >= 0))
    RS- = sum(r_i^2 * I(r_i < 0))

    Follows Patton & Sheppard (2015): RS+ uses >= 0 so that
    RS+ + RS- = RV always holds (exhaustive partition).
    """
    r = np.asarray(intraday_returns, dtype=np.float64)
    r_sq = r**2
    rs_pos = float(np.sum(r_sq[r >= 0]))
    rs_neg = float(np.sum(r_sq[r < 0]))
    return {
        "rs_positive": rs_pos,
        "rs_negative": rs_neg,
        "signed_jump": rs_pos - rs_neg,
    }


def compute_bpv(
    intraday_returns: pd.Series,
) -> float:
    """Compute bipower variation (BPV).

    BPV = (pi/2) * sum(|r_i| * |r_{i-1}|) for i = 2, ..., N.
    BPV is robust to jumps and estimates integrated variance
    (Barndorff-Nielsen & Shephard 2004).
    """
    r = np.asarray(intraday_returns, dtype=np.float64)
    abs_r = np.abs(r)
    products = abs_r[1:] * abs_r[:-1]
    return float((np.pi / 2.0) * np.sum(products))


def compute_realized_tripower_quarticity(
    intraday_returns: pd.Series,
) -> float:
    """Compute realized tri-power quarticity for BNS test variance.

    RTQ = n * mu_{4/3}^{-3} * sum_{i=2}^{n-1} |r_i|^{4/3} |r_{i-1}|^{4/3} |r_{i-2}|^{4/3}

    Per Barndorff-Nielsen & Shephard (2006, J Financial Econometrics).
    The sum has (n-2) terms; the n multiplier ensures correct convergence.
    mu_{4/3} = 2^{2/3} * Gamma(7/6) / Gamma(1/2) ~ 0.8309.
    """
    r = np.asarray(intraday_returns, dtype=np.float64)
    n = len(r)
    abs_r = np.abs(r)
    p = 4.0 / 3.0
    mu_43 = 2 ** (2.0 / 3.0) * math.gamma(7.0 / 6.0) / math.gamma(0.5)
    products = abs_r[2:] ** p * abs_r[1:-1] ** p * abs_r[:-2] ** p
    return float(n * mu_43 ** (-3) * np.sum(products))


def detect_jumps(
    rv: float,
    bpv: float,
    rtq: float,
    n_obs: int,
    alpha: float = 0.999,
) -> dict[str, float]:
    """Test for significant jumps using the BNS (2006) Theorem 2 z-test.

    Z_BNS = (RV - BPV) / sqrt(theta * RTQ / n)
    where theta = (pi^2/4 + pi - 5) approx 0.6090.
    """
    theta = (np.pi**2 / 4.0) + np.pi - 5.0
    denom_sq = max(theta * rtq / n_obs, 1e-20)
    z_stat = (rv - bpv) / np.sqrt(denom_sq)

    from scipy.stats import norm

    p_value = 1.0 - norm.cdf(z_stat)
    critical_value = norm.ppf(alpha)
    jump_indicator = 1.0 if z_stat > critical_value else 0.0

    return {
        "z_stat": float(z_stat),
        "p_value": float(p_value),
        "jump_indicator": jump_indicator,
    }


def compute_jump_variation(
    rv: float,
    bpv: float,
    jump_indicator: float,
) -> float:
    """Compute jump component of realized variance.

    J^2 = max(RV - BPV, 0) * jump_indicator.
    """
    return max(rv - bpv, 0.0) * jump_indicator


def compute_continuous_variation(
    rv: float,
    jump_variation: float,
) -> float:
    """Compute continuous component of realized variance.

    C = RV - J (continuous variation = total minus jumps).
    """
    return max(rv - jump_variation, 0.0)


def lee_mykland_test(
    intraday_returns: pd.Series,
    local_window: int = 156,
    alpha: float = 0.01,
) -> pd.DataFrame:
    """Lee-Mykland (2008) intraday jump detection test.

    For each return r_i, standardize by local BPV-based volatility
    and compare to Gumbel extreme-value threshold.
    """
    r = np.asarray(intraday_returns, dtype=np.float64)
    n = len(r)

    if n < local_window:
        raise ValueError(f"Series length ({n}) must be >= local_window ({local_window})")

    c_n = np.sqrt(2.0 * np.log(n))
    threshold = c_n - (np.log(np.pi) + np.log(np.log(n))) / (2.0 * c_n)

    abs_r = np.abs(r)
    products = abs_r[1:] * abs_r[:-1]

    test_stat = np.full(n, np.nan)
    for i in range(n):
        end = min(i, n - 1)
        start = max(0, end - local_window)
        if end <= start:
            continue

        local_products = products[start:end]
        if len(local_products) < 2:
            continue

        local_bpv = (np.pi / 2.0) * np.mean(local_products)
        sigma_i = np.sqrt(max(local_bpv, 1e-20))
        test_stat[i] = r[i] / sigma_i

    is_jump = np.abs(test_stat) > threshold

    return pd.DataFrame(
        {
            "return": r,
            "test_stat": test_stat,
            "threshold": np.full(n, threshold),
            "is_jump": is_jump,
            "jump_size": np.where(is_jump, r**2, 0.0),
            "jump_sign": np.where(is_jump, np.sign(r), 0.0),
        },
        index=intraday_returns.index if hasattr(intraday_returns, "index") else None,
    )


def compute_realized_moments(
    intraday_returns: pd.Series,
) -> dict[str, float]:
    """Compute realized skewness and kurtosis (Amaya et al. 2015 JFE).

    realized_skewness = sqrt(N) * mean(r^3) / mean(r^2)^(3/2)
    realized_kurtosis = N * mean(r^4) / mean(r^2)^2
    """
    r = np.asarray(intraday_returns, dtype=np.float64)
    n = len(r)
    mean_r2 = np.mean(r**2)
    mean_r3 = np.mean(r**3)
    mean_r4 = np.mean(r**4)

    skewness = np.sqrt(n) * mean_r3 / max(mean_r2, 1e-30) ** (3.0 / 2.0)
    kurtosis = n * mean_r4 / max(mean_r2, 1e-30) ** 2

    return {
        "realized_skewness": float(skewness),
        "realized_kurtosis": float(kurtosis),
    }


def compute_signed_jumps(
    intraday_returns: pd.Series,
    jump_flags: pd.Series,
) -> dict[str, float]:
    """Compute signed jump variation (J+ and J-).

    J+ = sum(r^2 * I(r > 0, is_jump))
    J- = sum(r^2 * I(r < 0, is_jump))
    """
    r = np.asarray(intraday_returns, dtype=np.float64)
    flags = np.asarray(jump_flags, dtype=bool)
    r_sq = r**2

    j_pos = float(np.sum(r_sq[(r > 0) & flags]))
    j_neg = float(np.sum(r_sq[(r < 0) & flags]))

    return {"j_positive": j_pos, "j_negative": j_neg}


# ---------------------------------------------------------------------------
# Noise-robust measures
# ---------------------------------------------------------------------------


def _parzen_kernel_vec(x: np.ndarray) -> np.ndarray:
    """Vectorized Parzen kernel for arrays of normalized lags."""
    x = np.abs(x)
    result = np.zeros_like(x)
    mask1 = x <= 0.5
    mask2 = (x > 0.5) & (x <= 1.0)
    result[mask1] = 1.0 - 6.0 * x[mask1] ** 2 + 6.0 * x[mask1] ** 3
    result[mask2] = 2.0 * (1.0 - x[mask2]) ** 3
    return result


def realized_kernel(
    log_prices: np.ndarray,
    bandwidth: int | None = None,
) -> float:
    """Compute Realized Kernel estimator of integrated variance.

    RK_t = sum_{h=-H}^{H} k(h/(H+1)) * gamma_hat_h

    Uses the flat-top Parzen kernel (Barndorff-Nielsen, Hansen, Lunde &
    Shephard 2008, Econometrica). Achieves the optimal n^{-1/5} MSE rate.

    Default bandwidth: H = ceil(n^{3/5}). This is a plug-in approximation
    of the BNHLS optimal H* = c* * xi^{4/5} * n^{3/5} where xi is the
    noise-to-signal ratio and c* depends on the kernel. Without a pilot
    estimate of xi, H = n^{3/5} (i.e., c*xi^{4/5} = 1) is standard.
    """
    log_prices = np.asarray(log_prices, dtype=np.float64)
    returns = np.diff(log_prices)
    n = len(returns)

    if n < 2:
        return float(np.sum(returns**2))

    if bandwidth is None:
        bandwidth = max(1, int(np.ceil(n ** (3.0 / 5.0))))

    H = min(bandwidth, n - 1)

    full_acov = fftconvolve(returns, returns[::-1], mode="full")
    acov = full_acov[n - 1 : n - 1 + H + 1]

    h_values = np.arange(1, H + 1)
    weights = _parzen_kernel_vec(h_values / (H + 1))
    rk = float(acov[0]) + 2.0 * float(np.dot(weights, acov[1:]))

    return max(rk, 0.0)


def noise_gap(
    rk_value: float,
    rv_5min: float,
) -> float:
    """Compute the noise gap: (RK - RV_5min) / RV_5min.

    A liquidity/noise intensity proxy.
    """
    if rv_5min <= 0:
        return 0.0
    return (rk_value - rv_5min) / rv_5min
