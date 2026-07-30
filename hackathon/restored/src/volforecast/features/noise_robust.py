"""Noise-robust realized variance estimators.

Implements estimators that correct for microstructure noise in tick-level data:
- Realized Kernel (Barndorff-Nielsen et al. 2008)
- Two-Scales Realized Volatility, TSRV (Zhang et al. 2005)
- Pre-averaging (Jacod et al. 2009)
- Volatility signature plot helper

All estimators target integrated variance IV_t from noisy tick prices.
Use as features alongside 5-min RV, not as replacement targets
(Liu et al. 2015: estimation accuracy != forecast accuracy).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import fftconvolve

from volforecast.data.measures import noise_gap, realized_kernel  # noqa: F401
from volforecast.features.transforms import lagged_log_features
from volforecast.registry import register_feature_layer


def tsrv(
    log_prices: np.ndarray,
    slow_scale: int | None = None,
) -> float:
    """Compute Two-Scales Realized Volatility (TSRV).

    Uses a fast scale (every tick) and a slow scale (spaced-out returns)
    to cancel the noise bias (Zhang et al. 2005).

    IV_TSRV = RV_avg_slow - (n_bar_slow / n) * RV_all

    Convergence rate: n^{-1/6}. If slow_scale is None, uses K ~ n^{2/3}.
    """
    log_prices = np.asarray(log_prices, dtype=np.float64)
    n = len(log_prices) - 1  # number of tick returns

    if n < 2:
        return float(np.sum(np.diff(log_prices) ** 2))

    # Fast scale: all tick returns
    all_returns = np.diff(log_prices)
    rv_all = float(np.sum(all_returns**2))

    # Slow scale with subsampling
    if slow_scale is None:
        slow_scale = max(2, int(np.ceil(n ** (2.0 / 3.0))))

    K = min(slow_scale, n)

    # Compute subsampled RV: average over K grids offset by 1 tick
    rv_sub_sum = 0.0
    count = 0
    for offset in range(K):
        # Extract prices at positions offset, offset+K, offset+2K, ...
        grid_prices = log_prices[offset::K]
        if len(grid_prices) >= 2:
            grid_returns = np.diff(grid_prices)
            rv_sub_sum += float(np.sum(grid_returns**2))
            count += 1

    if count == 0:
        return rv_all

    rv_avg_slow = rv_sub_sum / count

    # Correction factor
    n_bar_slow = (n - K + 1) / K
    correction = (n_bar_slow / n) * rv_all

    result = rv_avg_slow - correction
    return max(result, 0.0)


def pre_averaged_rv(
    log_prices: np.ndarray,
    block_length: int | None = None,
) -> float:
    """Compute pre-averaged realized variance (Jacod et al. 2009).

    Smooths noisy prices over local blocks before squaring.
    Achieves optimal n^{-1/4} convergence rate. If block_length is None, uses L ~ n^{1/2}.
    """
    log_prices = np.asarray(log_prices, dtype=np.float64)
    n = len(log_prices) - 1  # number of tick returns

    if n < 4:
        return float(np.sum(np.diff(log_prices) ** 2))

    # Optimal block length: L ~ n^{1/2}
    if block_length is None:
        block_length = max(2, int(np.ceil(np.sqrt(n))))

    L = min(block_length, n)
    returns = np.diff(log_prices)

    # Weight function g(x) = min(x, 1-x) — triangular
    weights = np.array([min(j / L, 1.0 - j / L) for j in range(1, L)])

    # psi constants for the triangular weight function
    # psi_1 = int_0^1 [g'(x)]^2 dx = 1
    # psi_2 = int_0^1 [g(x)]^2 dx = 1/12 (for triangular g)
    psi_1 = 1.0
    psi_2 = 1.0 / 12.0

    # Compute pre-averaged returns via convolution (O(n log n) vs O(n*L) loop)
    n_pa = n - L + 1
    if n_pa < 1:
        return float(np.sum(returns**2))

    pa_returns = fftconvolve(returns, weights[::-1], mode="valid")[:n_pa]

    # All-tick RV for bias correction
    rv_all = float(np.sum(returns**2))

    # Pre-averaged RV
    pa_rv = (1.0 / (L * psi_2)) * np.sum(pa_returns**2) - (psi_1 / (2.0 * L * psi_2)) * rv_all

    return max(float(pa_rv), 0.0)


def volatility_signature_plot_data(
    log_prices: np.ndarray,
    frequencies: list[int] | None = None,
) -> pd.DataFrame:
    """Compute average RV at multiple sampling frequencies for one day.

    Used to build the volatility signature plot diagnostic.
    Returns DataFrame with columns: 'freq_ticks', 'rv', 'n_returns'.
    """
    log_prices = np.asarray(log_prices, dtype=np.float64)
    n = len(log_prices) - 1

    if frequencies is None:
        max_freq = max(n // 4, 2)
        frequencies = sorted({int(f) for f in np.logspace(0, np.log10(max_freq), 30)})

    rows = []
    for freq in frequencies:
        if freq < 1 or freq > n:
            continue
        # Subsampled RV: average over all offset grids
        rv_sum = 0.0
        count = 0
        for offset in range(freq):
            sampled = log_prices[offset::freq]
            if len(sampled) >= 2:
                rets = np.diff(sampled)
                rv_sum += float(np.sum(rets**2))
                count += 1
        if count > 0:
            rows.append(
                {
                    "freq_ticks": freq,
                    "rv": rv_sum / count,
                    "n_returns": int(n / freq),
                }
            )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# FeatureLayer wrapper (Tier 2: daily DataFrame → daily DataFrame)
# ---------------------------------------------------------------------------


@register_feature_layer("noise_robust")
class NoiseRobustLayer:
    """Noise-robust feature layer.

    Expects ``daily_data`` to have 'rk' and 'noise_gap' columns
    (produced by Tier 1 tick aggregation). Computes rolling features.
    """

    name = "noise_robust"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """Build noise-robust features from pre-computed daily measures.

        Always emits features when columns exist, regardless of NaN coverage.
        Tree models (LightGBM) handle NaN natively via best-split routing.
        OLS models drop NaN rows internally in their _fit() method.
        """
        result = pd.DataFrame(index=daily_data.index)

        if "rk" in daily_data.columns:
            rk_features = lagged_log_features(daily_data["rk"], "rk", windows=[5])
            result = pd.concat([result, rk_features], axis=1)

        if "noise_gap" in daily_data.columns:
            ng = daily_data["noise_gap"]
            result["noise_gap_d"] = ng
            result["noise_gap_w"] = ng.rolling(5).mean()

        # Volume anomaly: deviation of log tick count from 22-day mean
        if "n_ticks" in daily_data.columns:
            log_nticks = np.log(daily_data["n_ticks"].clip(lower=1))
            result["vol_anomaly"] = log_nticks - log_nticks.rolling(22).mean()

        return result
