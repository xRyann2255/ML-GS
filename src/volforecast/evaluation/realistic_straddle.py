"""Realistic delta-hedged straddle backtest (Phase 1: analytic corrections).

Implements the full P&L waterfall from the plan:
    Gross gamma PnL (tenor-decayed gamma)
    + Vanna PnL (spot-vol correlation)
    + Volga PnL (vol-of-vol convexity)
    - Option cost (maturity-varying, event-driven)
    - Hedge cost (N rebalances x spread)
    ± Hedge error (zero-mean, inflates RISK only)
    = Net P&L with honest Sharpe denominator

References:
    - Boyle & Emanuel (1980): discrete hedging error variance, 1/N scaling
    - Leland (1985): modified vol for hedge cost
    - Doshi, Pari, Shamsuddin (2025): maturity-dependent option spreads
    - Li & Wu (2026): graded sizing beats binary
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm


@dataclass
class RealisticStraddleConfig:
    """Configuration for the realistic straddle backtest."""

    tenor_days: int = 30
    roll_at_days: int = 5
    spread_bps: float = 2.0
    kappa: float = 4.0
    rebalances_per_day: int = 26
    sizing_mode: str = "binary"  # "binary" or "graded"
    signal_form: str = "difference"  # "difference", "ratio", "log_ratio"
    max_leverage: float = 2.0
    graded_lookback: int = 63
    option_cost_base: float = 1.0  # Base option half-spread in vol points


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


def option_spread_vol_pts(T_rem_days: float, base_spread: float) -> float:
    """Maturity-adjusted option spread per Doshi et al. (2025) schedule.

    Parameters
    ----------
    T_rem_days : float
        Remaining tenor in trading days.
    base_spread : float
        Base half-spread in vol points for 21-48 day tenor.

    Returns
    -------
    float
        Adjusted spread in vol points.
    """
    if T_rem_days <= 6:
        return base_spread * 4.5
    elif T_rem_days <= 13:
        return base_spread * 1.75
    else:
        return base_spread


def compute_tenor_decayed_gamma(spot: float, iv: float, T_rem_days: float) -> float:
    """ATM straddle gamma with tenor decay.

    Gamma_ATM = 2 / (S * sigma * sqrt(T_rem))

    Parameters
    ----------
    spot : float
        Underlying spot price.
    iv : float
        ATM implied vol (annualized decimal).
    T_rem_days : float
        Remaining tenor in trading days.

    Returns
    -------
    float
        ATM straddle dollar gamma.
    """
    T_rem = T_rem_days / 252.0
    iv_safe = max(iv, 1e-8)
    return 2.0 / (spot * iv_safe * np.sqrt(T_rem))


def _compute_d1_d2(iv: np.ndarray, T_rem_years: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute ATM d1, d2 (K=S, so log(S/K)=0).

    d1 = 0.5 * sigma * sqrt(T)
    d2 = -0.5 * sigma * sqrt(T)
    """
    iv_safe = np.maximum(iv, 1e-8)
    sqrt_T = np.sqrt(np.maximum(T_rem_years, 1e-8))
    d1 = 0.5 * iv_safe * sqrt_T
    d2 = -0.5 * iv_safe * sqrt_T
    return d1, d2


def compute_vanna_pnl(
    spot: np.ndarray,
    iv: np.ndarray,
    T_rem_days: np.ndarray,
    delta_spot: np.ndarray,
    delta_iv: np.ndarray,
    q: float = 0.0,
) -> np.ndarray:
    """Daily vanna P&L from spot-vol correlation leakage.

    Vanna = -exp(-q*T) * N'(d1) * d2 / sigma
    PnL_vanna = Vanna * delta_spot * delta_iv

    For a straddle (2 options): multiply by 2.

    Parameters
    ----------
    spot : np.ndarray
        Spot prices.
    iv : np.ndarray
        ATM implied vol (annualized).
    T_rem_days : np.ndarray
        Remaining tenor in trading days.
    delta_spot : np.ndarray
        Daily spot price change.
    delta_iv : np.ndarray
        Daily IV change (annualized decimal).
    q : float
        Continuous dividend yield (default 0).

    Returns
    -------
    np.ndarray
        Vanna P&L per day (dollar terms, normalized by spot later).
    """
    T_rem_years = T_rem_days / 252.0
    d1, d2 = _compute_d1_d2(iv, T_rem_years)
    iv_safe = np.maximum(iv, 1e-8)

    # Vanna per option = -exp(-q*T) * N'(d1) * d2 / sigma
    nprime_d1 = norm.pdf(d1)
    vanna_per_option = -np.exp(-q * T_rem_years) * nprime_d1 * d2 / iv_safe

    # Straddle: 2 options
    vanna_straddle = 2.0 * vanna_per_option

    return vanna_straddle * delta_spot * delta_iv


def compute_volga_pnl(
    spot: np.ndarray,
    iv: np.ndarray,
    T_rem_days: np.ndarray,
    delta_iv: np.ndarray,
) -> np.ndarray:
    """Daily volga P&L from vol-of-vol exposure.

    Volga = Vega * d1 * d2 / sigma
    PnL_volga = 0.5 * Volga * (delta_iv)^2

    Vega_ATM = S * sqrt(T) * N'(d1) per option.
    For a straddle: Vega = 2 * S * sqrt(T) * N'(d1).

    Parameters
    ----------
    spot : np.ndarray
        Spot prices.
    iv : np.ndarray
        ATM implied vol (annualized).
    T_rem_days : np.ndarray
        Remaining tenor in trading days.
    delta_iv : np.ndarray
        Daily IV change (annualized decimal).

    Returns
    -------
    np.ndarray
        Volga P&L per day.
    """
    T_rem_years = T_rem_days / 252.0
    d1, d2 = _compute_d1_d2(iv, T_rem_years)
    iv_safe = np.maximum(iv, 1e-8)
    sqrt_T = np.sqrt(np.maximum(T_rem_years, 1e-8))

    nprime_d1 = norm.pdf(d1)
    # Vega per straddle = 2 * S * sqrt(T) * N'(d1)
    vega_straddle = 2.0 * spot * sqrt_T * nprime_d1

    # Volga = Vega * d1 * d2 / sigma
    volga = vega_straddle * d1 * d2 / iv_safe

    return 0.5 * volga * delta_iv**2


def delta_hedge_cost_per_day(
    gamma: np.ndarray,
    spot: np.ndarray,
    iv: np.ndarray,
    spread_bps: float = 2.0,
    rebalances: int = 26,
) -> np.ndarray:
    """Expected daily delta-hedge transaction cost.

    Per rebalance:
        E[|delta_change|] = gamma * S * IV * sqrt(dt) * sqrt(2/pi)
        cost_per_rebalance = E[|delta_change|] * S * spread/10000

    Total daily = N * cost_per_rebalance.

    Parameters
    ----------
    gamma : np.ndarray
        Straddle gamma.
    spot : np.ndarray
        Spot prices.
    iv : np.ndarray
        ATM implied vol (annualized).
    spread_bps : float
        Round-trip spread of underlying in basis points.
    rebalances : int
        Number of hedge rebalances per day.

    Returns
    -------
    np.ndarray
        Daily hedge cost (dollar terms).
    """
    dt = 1.0 / (252.0 * rebalances)
    sqrt_2_pi = np.sqrt(2.0 / np.pi)
    iv_safe = np.maximum(iv, 1e-8)

    # Expected absolute delta change per rebalance
    expected_abs_delta_change = gamma * spot * iv_safe * np.sqrt(dt) * sqrt_2_pi

    # Cost per rebalance = |shares traded| * price * half-spread
    cost_per_rebalance = expected_abs_delta_change * spot * (spread_bps / 10000.0)

    return rebalances * cost_per_rebalance


def compute_hedge_error_variance(
    gamma: np.ndarray,
    spot: np.ndarray,
    iv: np.ndarray,
    kappa: float = 4.0,
    N: int = 26,
) -> np.ndarray:
    """Per-day discrete hedging error variance (Boyle-Emanuel 1980).

    Var(HE_day) = (0.5 * Gamma * S^2)^2 * (kappa - 1) * sigma^4 / (252^2 * N)

    Parameters
    ----------
    gamma : np.ndarray
        Straddle gamma per day.
    spot : np.ndarray
        Spot prices.
    iv : np.ndarray
        ATM implied vol (annualized).
    kappa : float
        Return kurtosis (4.0 = leptokurtic default for 15-min bars).
    N : int
        Number of hedge rebalances per day.

    Returns
    -------
    np.ndarray
        Per-day hedge error variance (in dollar^2 / spot^2 for normalized PnL).
    """
    iv_safe = np.maximum(iv, 1e-8)
    half_gamma_s2 = 0.5 * gamma * spot**2
    var_he = half_gamma_s2**2 * (kappa - 1.0) * iv_safe**4 / (252.0**2 * N)
    # Normalize by spot^2 to match normalized PnL units
    return var_he / spot**2


def graded_signal(
    gap: np.ndarray,
    lookback: int = 63,
    max_leverage: float = 2.0,
) -> np.ndarray:
    """Graded sizing: position = clip(gap / rolling_std(gap), -max, +max).

    Parameters
    ----------
    gap : np.ndarray
        IV - RV forecast gap (same units, annualized vol).
    lookback : int
        Rolling window for standard deviation.
    max_leverage : float
        Maximum absolute position size.

    Returns
    -------
    np.ndarray
        Position sizes in [-max_leverage, +max_leverage].
    """
    n = len(gap)
    result = np.zeros(n)

    # Expanding window until we hit lookback
    for i in range(1, n):
        window = gap[max(0, i - lookback) : i]
        std = np.std(window, ddof=1) if len(window) > 1 else 1.0
        if std < 1e-12:
            std = 1.0
        result[i] = np.clip(gap[i] / std, -max_leverage, max_leverage)

    return result


def _compute_signal(
    iv: np.ndarray,
    forecast_ann_vol: np.ndarray,
    signal_form: str,
    sizing_mode: str,
    threshold: float,
    lookback: int,
    max_leverage: float,
) -> np.ndarray:
    """Compute trading signal from IV and RV forecast.

    Parameters
    ----------
    iv : np.ndarray
        Implied vol (annualized).
    forecast_ann_vol : np.ndarray
        Forecasted RV (annualized vol).
    signal_form : str
        One of "difference", "ratio", "log_ratio".
    sizing_mode : str
        "binary" or "graded".
    threshold : float
        Dead zone threshold (for binary mode).
    lookback : int
        Lookback for graded std normalization.
    max_leverage : float
        Position size cap for graded mode.

    Returns
    -------
    np.ndarray
        Signal array. Binary: in {-1, 0, 1}. Graded: continuous.
    """
    iv_safe = np.maximum(iv, 1e-8)
    rv_safe = np.maximum(forecast_ann_vol, 1e-8)

    if signal_form == "difference":
        gap = iv - forecast_ann_vol
    elif signal_form == "ratio":
        gap = iv_safe / rv_safe - 1.0
    elif signal_form == "log_ratio":
        gap = np.log(iv_safe / rv_safe)
    else:
        gap = iv - forecast_ann_vol

    if sizing_mode == "graded":
        return graded_signal(gap, lookback=lookback, max_leverage=max_leverage)
    else:
        # Binary mode
        signal = np.zeros(len(gap))
        signal[gap > threshold] = 1.0
        signal[gap < -threshold] = -1.0
        return signal


# ---------------------------------------------------------------------------
# Main Phase 1 engine
# ---------------------------------------------------------------------------


def realistic_straddle_pnl(
    signal: np.ndarray,
    realized_var: np.ndarray,
    implied_vol: np.ndarray,
    spot_prices: np.ndarray,
    delta_spot: np.ndarray,
    delta_iv: np.ndarray,
    tenor_days: int = 30,
    roll_at_days: int = 5,
    spread_bps: float = 2.0,
    option_cost_base: float = 0.3,
    kappa: float = 4.0,
    rebalances_per_day: int = 26,
) -> dict[str, np.ndarray]:
    """Compute realistic delta-hedged straddle P&L with full waterfall.

    Parameters
    ----------
    signal : np.ndarray
        Position sizes (binary or graded). +ve = short vol, -ve = long vol.
    realized_var : np.ndarray
        Daily realized variance (not annualized).
    implied_vol : np.ndarray
        ATM implied vol (annualized decimal).
    spot_prices : np.ndarray
        Underlying spot prices.
    delta_spot : np.ndarray
        Daily spot price changes.
    delta_iv : np.ndarray
        Daily IV changes (annualized decimal).
    tenor_days : int
        Initial option tenor in trading days.
    roll_at_days : int
        Roll when T_rem falls below this.
    spread_bps : float
        Underlying spread for delta hedging (bps).
    option_cost_base : float
        Base option half-spread in vol points (default: 0.3 for mega-cap ATM).
    kappa : float
        Return kurtosis for hedge error variance.
    rebalances_per_day : int
        Number of daily delta rebalances.

    Returns
    -------
    dict[str, np.ndarray]
        Keys: pnl_gamma, pnl_vanna, pnl_volga, cost_option, cost_hedge,
        pnl_net, hedge_error_var, T_rem.
    """
    signal = np.asarray(signal, dtype=np.float64)
    realized_var = np.asarray(realized_var, dtype=np.float64)
    implied_vol = np.asarray(implied_vol, dtype=np.float64)
    spot_prices = np.asarray(spot_prices, dtype=np.float64)
    delta_spot = np.asarray(delta_spot, dtype=np.float64)
    delta_iv = np.asarray(delta_iv, dtype=np.float64)

    # Prevent roll_at_days >= tenor_days (would cause immediate roll)
    if roll_at_days >= tenor_days:
        roll_at_days = max(1, tenor_days // 3)

    n = len(signal)
    dt = 1.0 / 252.0

    # --- Tenor tracking with rolls ---
    T_rem = np.zeros(n)
    current_T_rem = float(tenor_days)
    # Track events: entry, flip, roll for option cost
    option_cost = np.zeros(n)

    prev_signal = 0.0
    for i in range(n):
        # Detect signal transitions for event-driven costing
        curr_sig = signal[i]
        entered = prev_signal == 0.0 and curr_sig != 0.0
        exited = prev_signal != 0.0 and curr_sig == 0.0
        flipped = (prev_signal > 0 and curr_sig < 0) or (prev_signal < 0 and curr_sig > 0)
        rolled = False

        # Check for roll
        if curr_sig != 0.0 and current_T_rem <= roll_at_days:
            rolled = True
            # Charge exit at current (elevated) maturity spread
            exit_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            # Charge entry at new tenor (base) spread
            entry_spread = option_spread_vol_pts(float(tenor_days), option_cost_base)
            # 4 legs: 2 to close + 2 to open
            vega_per_opt = spot_prices[i] * np.sqrt(float(tenor_days) / 252.0) * norm.pdf(0.0)
            option_cost[i] = (2 * exit_spread + 2 * entry_spread) / 100.0 * vega_per_opt
            current_T_rem = float(tenor_days)
        elif entered:
            # 2 legs
            entry_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            vega_per_opt = spot_prices[i] * np.sqrt(current_T_rem / 252.0) * norm.pdf(0.0)
            option_cost[i] = 2 * entry_spread / 100.0 * vega_per_opt
        elif flipped:
            # 4 legs: close + open
            exit_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            entry_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            vega_per_opt = spot_prices[i] * np.sqrt(current_T_rem / 252.0) * norm.pdf(0.0)
            option_cost[i] = (2 * exit_spread + 2 * entry_spread) / 100.0 * vega_per_opt
        elif exited:
            # 2 legs
            exit_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            vega_per_opt = spot_prices[i] * np.sqrt(current_T_rem / 252.0) * norm.pdf(0.0)
            option_cost[i] = 2 * exit_spread / 100.0 * vega_per_opt

        T_rem[i] = current_T_rem

        # Decrement tenor (only if position active and not just rolled)
        if curr_sig != 0.0 and not rolled and i > 0:
            current_T_rem -= 1.0
            current_T_rem = max(current_T_rem, 1.0)

        prev_signal = curr_sig

    # --- Vectorized computations ---
    T_rem_years = T_rem / 252.0
    iv_safe = np.maximum(implied_vol, 1e-8)

    # Tenor-decayed gamma
    gamma = 2.0 / (spot_prices * iv_safe * np.sqrt(T_rem_years))

    # Gamma PnL
    daily_implied_var = iv_safe**2 * dt
    raw_gamma_pnl = 0.5 * gamma * spot_prices**2 * (realized_var - daily_implied_var)
    # Direction: signal > 0 means short vol (negate raw, which is long-gamma)
    pnl_gamma = -signal * raw_gamma_pnl / np.maximum(spot_prices, 1e-8)

    # Vanna PnL (normalized by spot)
    pnl_vanna_raw = compute_vanna_pnl(spot_prices, implied_vol, T_rem, delta_spot, delta_iv)
    # For short vol (signal > 0), we are short the straddle -> negate vanna
    pnl_vanna = -signal * pnl_vanna_raw / np.maximum(spot_prices, 1e-8)

    # Volga PnL (normalized by spot)
    pnl_volga_raw = compute_volga_pnl(spot_prices, implied_vol, T_rem, delta_iv)
    pnl_volga = -signal * pnl_volga_raw / np.maximum(spot_prices, 1e-8)

    # Hedge cost (normalized by spot)
    hedge_cost_raw = delta_hedge_cost_per_day(
        gamma, spot_prices, implied_vol, spread_bps, rebalances_per_day
    )
    cost_hedge = np.abs(signal) * hedge_cost_raw / np.maximum(spot_prices, 1e-8)

    # Option cost (already dollar, normalize by spot)
    cost_option_norm = np.abs(signal) * option_cost / np.maximum(spot_prices, 1e-8)

    # Net PnL
    pnl_net = pnl_gamma + pnl_vanna + pnl_volga - cost_option_norm - cost_hedge

    # Hedge error variance (normalized)
    hedge_error_var = compute_hedge_error_variance(
        gamma, spot_prices, implied_vol, kappa=kappa, N=rebalances_per_day
    )
    # Only accrue when position is active
    hedge_error_var = hedge_error_var * signal**2

    return {
        "pnl_gamma": pnl_gamma,
        "pnl_vanna": pnl_vanna,
        "pnl_volga": pnl_volga,
        "cost_option": cost_option_norm,
        "cost_hedge": cost_hedge,
        "pnl_net": pnl_net,
        "hedge_error_var": hedge_error_var,
        "T_rem": T_rem,
    }


# ---------------------------------------------------------------------------
# Cost band and deflated Sharpe
# ---------------------------------------------------------------------------


def cost_band_sharpes(
    pnl_gross: np.ndarray,
    gamma: np.ndarray,
    spot: np.ndarray,
    iv: np.ndarray,
    T_rem_days: np.ndarray,
    spread_bps: float = 2.0,
    rebalances: int = 26,
) -> dict[str, float]:
    """Compute Sharpe at three cost bands (Muravyev & Pearson 2020).

    Bands: timing_aware (0.5 vol pts), effective (1.0), quoted (1.5).

    Parameters
    ----------
    pnl_gross : np.ndarray
        Gross P&L before option cost (gamma + vanna + volga - hedge cost).
    gamma : np.ndarray
        Straddle gamma.
    spot : np.ndarray
        Spot prices.
    iv : np.ndarray
        Implied vol.
    T_rem_days : np.ndarray
        Remaining tenor in days.
    spread_bps : float
        Underlying spread for hedge cost (bps).
    rebalances : int
        Rebalances per day.

    Returns
    -------
    dict[str, float]
        Sharpe ratios at timing_aware, effective, and quoted bands.
    """
    from volforecast.evaluation.economic_value import compute_sharpe

    bands = {"timing_aware": 0.5, "effective": 1.0, "quoted": 1.5}
    result = {}

    T_rem_years = T_rem_days / 252.0
    vega_norm = np.sqrt(np.maximum(T_rem_years, 1e-8)) * norm.pdf(0.0)

    for band_name, base_vol_pts in bands.items():
        # Compute per-day option cost at this band level with maturity adjustment
        adjusted_cost = np.zeros(len(pnl_gross))
        for i in range(len(pnl_gross)):
            mult = option_spread_vol_pts(T_rem_days[i], base_vol_pts) / base_vol_pts
            # Amortized daily: assume 22-day holding period
            adjusted_cost[i] = 2.0 * (base_vol_pts * mult / 100.0) * vega_norm[i] / 22.0

        pnl_net = pnl_gross - adjusted_cost
        result[band_name] = compute_sharpe(pnl_net)

    return result


def deflated_sharpe_ratio(
    observed_sharpe: float,
    T: int,
    skewness: float,
    kurtosis: float,
    N_trials: int,
) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).

    DSR = Phi((SR_hat - SR_0) * sqrt(T-1) / sqrt(1 - gamma3*SR + (gamma4-1)/4 * SR^2))

    SR_0 = sqrt(Var[SR_n]) * [(1-gamma_E)*Phi^{-1}(1-1/N) + gamma_E*Phi^{-1}(1-1/(Ne))]

    Parameters
    ----------
    observed_sharpe : float
        Annualized observed Sharpe ratio (non-annualized internally: divide by sqrt(252)).
    T : int
        Number of daily observations.
    skewness : float
        Skewness of daily returns.
    kurtosis : float
        Kurtosis of daily returns (3.0 = normal).
    N_trials : int
        Number of strategy configurations tested (for multiple-testing correction).

    Returns
    -------
    float
        DSR probability in [0, 1].
    """
    # Work with non-annualized SR for the formula
    sr = observed_sharpe / np.sqrt(252.0)

    # Variance of SR estimator under non-normality
    var_sr = (1.0 - skewness * sr + (kurtosis - 1.0) / 4.0 * sr**2) / (T - 1.0)
    std_sr = np.sqrt(max(var_sr, 1e-12))

    # Expected maximum SR under null (SR_0)
    gamma_E = 0.5772156649  # Euler-Mascheroni constant
    if N_trials <= 1:
        sr_0 = 0.0
    else:
        sr_0 = std_sr * (
            (1.0 - gamma_E) * norm.ppf(1.0 - 1.0 / N_trials)
            + gamma_E * norm.ppf(1.0 - 1.0 / (N_trials * np.e))
        )

    # Denominator
    denom = np.sqrt(max(var_sr, 1e-12))

    # DSR
    z = (sr - sr_0) / denom
    return float(norm.cdf(z))


def block_bootstrap_ci(
    pnl: np.ndarray,
    n_bootstrap: int = 1000,
    block_size: int = 5,
    alpha: float = 0.05,
    seed: int | None = None,
) -> tuple[float, float]:
    """Block-bootstrap confidence interval for annualized Sharpe.

    Resamples whole blocks of consecutive days to preserve autocorrelation.

    Parameters
    ----------
    pnl : np.ndarray
        Daily P&L series.
    n_bootstrap : int
        Number of bootstrap replications.
    block_size : int
        Number of consecutive days per block.
    alpha : float
        Significance level (default 0.05 for 95% CI).
    seed : int or None
        Random seed for reproducibility.

    Returns
    -------
    tuple[float, float]
        (lower, upper) bounds of the confidence interval for annualized Sharpe.
    """
    from volforecast.evaluation.economic_value import compute_sharpe

    rng = np.random.default_rng(seed)
    n = len(pnl)
    n_blocks = (n + block_size - 1) // block_size  # Ceil division

    sharpes = np.zeros(n_bootstrap)

    for b in range(n_bootstrap):
        # Sample blocks with replacement
        block_starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        sample = np.concatenate([pnl[s : s + block_size] for s in block_starts])[:n]
        sharpes[b] = compute_sharpe(sample)

    lower = float(np.percentile(sharpes, 100 * alpha / 2))
    upper = float(np.percentile(sharpes, 100 * (1 - alpha / 2)))
    return lower, upper


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def realistic_delta_hedged_sharpe(
    log_rv_predictions: np.ndarray,
    implied_vol: np.ndarray,
    realized_var: np.ndarray,
    spot_prices: np.ndarray,
    threshold: float = 0.0,
    tenor_days: int = 30,
    roll_at_days: int = 5,
    spread_bps: float = 2.0,
    option_cost_base: float = 0.3,
    kappa: float = 4.0,
    rebalances_per_day: int = 26,
    sizing_mode: str = "binary",
    signal_form: str = "difference",
    max_leverage: float = 2.0,
    graded_lookback: int = 63,
    n_bootstrap: int = 1000,
    bootstrap_seed: int | None = 42,
) -> dict[str, float | dict]:
    """Compute realistic delta-hedged straddle metrics.

    Full Phase 1 engine: tenor-decayed gamma, vanna/volga, event-driven
    option cost, hedge cost, hedge error variance, cost band, DSR.

    Parameters
    ----------
    log_rv_predictions : np.ndarray
        Model OOS predictions in log(RV) space (daily, not annualized).
    implied_vol : np.ndarray
        ATM implied vol (annualized decimal).
    realized_var : np.ndarray
        Actual daily realized variance.
    spot_prices : np.ndarray
        Underlying spot prices.
    threshold : float
        Signal threshold (binary mode).
    tenor_days : int
        Option tenor in trading days.
    roll_at_days : int
        Roll when T_rem falls below this.
    spread_bps : float
        Underlying spread for delta hedging.
    option_cost_base : float
        Base option half-spread in vol points.
    kappa : float
        Return kurtosis.
    rebalances_per_day : int
        Delta rebalances per day.
    sizing_mode : str
        "binary" or "graded".
    signal_form : str
        "difference", "ratio", or "log_ratio".
    max_leverage : float
        Max position size (graded mode).
    graded_lookback : int
        Lookback for graded std normalization.
    n_bootstrap : int
        Bootstrap replications for CI.
    bootstrap_seed : int or None
        Seed for bootstrap.

    Returns
    -------
    dict
        Keys: dh_sharpe, dh_sharpe_adjusted, dh_pnl, dh_max_dd, dh_hit_rate,
        dh_ann_ret, dh_ann_vol, cost_band, dsr, bootstrap_ci, kappa_sensitivity.
    """
    log_rv_predictions = np.asarray(log_rv_predictions, dtype=np.float64)
    implied_vol = np.asarray(implied_vol, dtype=np.float64)
    realized_var = np.asarray(realized_var, dtype=np.float64)
    spot_prices = np.asarray(spot_prices, dtype=np.float64)

    # Prevent roll_at_days >= tenor_days (would cause immediate roll)
    if roll_at_days >= tenor_days:
        roll_at_days = max(1, tenor_days // 3)

    # Convert log-RV to annualized vol
    forecast_ann_vol = np.sqrt(252.0 * np.exp(log_rv_predictions))

    # Compute signal
    signal = _compute_signal(
        implied_vol,
        forecast_ann_vol,
        signal_form,
        sizing_mode,
        threshold,
        graded_lookback,
        max_leverage,
    )

    # Compute delta_spot and delta_iv from price/IV series
    delta_spot = np.zeros(len(spot_prices))
    delta_spot[1:] = np.diff(spot_prices)
    delta_iv = np.zeros(len(implied_vol))
    delta_iv[1:] = np.diff(implied_vol)

    # Run Phase 1 engine
    result = realistic_straddle_pnl(
        signal=signal,
        realized_var=realized_var,
        implied_vol=implied_vol,
        spot_prices=spot_prices,
        delta_spot=delta_spot,
        delta_iv=delta_iv,
        tenor_days=tenor_days,
        roll_at_days=roll_at_days,
        spread_bps=spread_bps,
        option_cost_base=option_cost_base,
        kappa=kappa,
        rebalances_per_day=rebalances_per_day,
    )

    pnl_net = result["pnl_net"]
    valid = ~np.isnan(pnl_net)
    pnl_clean = np.where(valid, pnl_net, 0.0)

    # --- Metrics ---
    from volforecast.evaluation.economic_value import compute_sharpe

    sharpe_raw = compute_sharpe(pnl_clean)

    # Adjusted Sharpe: inflate std with hedge error variance
    observed_var = np.var(pnl_clean, ddof=1)
    mean_he_var = np.mean(result["hedge_error_var"])
    total_std = np.sqrt(observed_var + mean_he_var)
    mean_pnl = np.mean(pnl_clean)
    sharpe_adjusted = float(mean_pnl / total_std * np.sqrt(252.0)) if total_std > 1e-12 else 0.0

    # Cumulative PnL
    cum_curve = np.cumsum(pnl_clean)
    cum_pnl = float(cum_curve[-1] * 100) if len(cum_curve) > 0 else 0.0
    peak = np.maximum.accumulate(cum_curve)
    dd = cum_curve - peak
    max_dd = float(np.min(dd) * 100) if len(dd) > 0 else 0.0

    # Hit rate
    active = np.abs(signal) > 0
    hit_rate = float(np.mean(pnl_clean[active] > 0)) if active.any() else 0.0

    # Annualized return and vol
    ann_ret = float(mean_pnl * 252 * 100) if len(pnl_clean) > 1 else 0.0
    ann_vol = float(np.std(pnl_clean, ddof=1) * np.sqrt(252) * 100) if len(pnl_clean) > 1 else 0.0

    # Cost band
    # Gross PnL = gamma + vanna + volga - hedge cost (before option cost)
    pnl_gross = (
        result["pnl_gamma"] + result["pnl_vanna"] + result["pnl_volga"] - result["cost_hedge"]
    )
    T_rem_years = result["T_rem"] / 252.0
    gamma = 2.0 / (spot_prices * np.maximum(implied_vol, 1e-8) * np.sqrt(T_rem_years))
    cost_band = cost_band_sharpes(
        pnl_gross,
        gamma,
        spot_prices,
        implied_vol,
        result["T_rem"],
        spread_bps=spread_bps,
        rebalances=rebalances_per_day,
    )

    # Deflated Sharpe
    skewness = float(np.mean(((pnl_clean - mean_pnl) / max(np.std(pnl_clean, ddof=1), 1e-12)) ** 3))
    kurt = float(np.mean(((pnl_clean - mean_pnl) / max(np.std(pnl_clean, ddof=1), 1e-12)) ** 4))
    dsr = deflated_sharpe_ratio(
        observed_sharpe=sharpe_raw,
        T=len(pnl_clean),
        skewness=skewness,
        kurtosis=kurt,
        N_trials=10,  # Conservative: assume 10 configs tried
    )

    # Block-bootstrap CI
    ci_low, ci_high = block_bootstrap_ci(
        pnl_clean, n_bootstrap=n_bootstrap, block_size=5, seed=bootstrap_seed
    )

    # Kurtosis sensitivity
    kappa_sensitivity = {}
    for k_val in [3.0, 4.0, 6.0]:
        he_var_k = compute_hedge_error_variance(
            gamma, spot_prices, implied_vol, kappa=k_val, N=rebalances_per_day
        )
        he_var_k = he_var_k * signal**2
        total_std_k = np.sqrt(observed_var + np.mean(he_var_k))
        sr_k = float(mean_pnl / total_std_k * np.sqrt(252.0)) if total_std_k > 1e-12 else 0.0
        kappa_sensitivity[f"kappa_{k_val:.0f}"] = sr_k

    return {
        "dh_sharpe": sharpe_raw,
        "dh_sharpe_adjusted": sharpe_adjusted,
        "dh_pnl": cum_pnl,
        "dh_max_dd": max_dd,
        "dh_hit_rate": hit_rate,
        "dh_ann_ret": ann_ret,
        "dh_ann_vol": ann_vol,
        "cost_band": cost_band,
        "dsr": dsr,
        "bootstrap_ci": (ci_low, ci_high),
        "kappa_sensitivity": kappa_sensitivity,
    }
