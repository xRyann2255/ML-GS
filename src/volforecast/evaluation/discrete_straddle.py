"""Phase 2: Discrete delta-hedged straddle simulator.

Bar-by-bar simulation using 15-min bars aggregated from 10s VWAP data.
Implements Steps 11-15 of the realistic-dh-straddle plan.

Key differences from Phase 1 (analytic):
- Execution price uses proper volume-weighted 15-min VWAP
- Full Black-Scholes delta at each bar (actual moneyness, not ATM approximation)
- Greeks captured mechanically through BS revaluation
- Per-day realized kurtosis from 15-min returns (replaces flat kappa)
- Hedge error emerges from simulation (not analytic formula)

References:
    - Boyle & Emanuel (1980): discrete hedging error
    - Broden & Tankov (2010): jump floor in hedging error
    - Amaya et al. (2015): realized kurtosis
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

# ---------------------------------------------------------------------------
# Step 11: 15-min bar aggregation
# ---------------------------------------------------------------------------


def aggregate_10s_to_15min(
    df: pd.DataFrame,
    bars_per_bucket: int = 90,
) -> pd.DataFrame:
    """Aggregate 10-second bars into 15-minute bars with proper VWAP.

    VWAP_15min = sum(vwap_i * volume_i) / sum(volume_i)
    where volume_i = buy_vol_i + sell_vol_i.

    Parameters
    ----------
    df : pd.DataFrame
        10s bar data with columns: date, bar_idx, buy_vol, sell_vol,
        net_flow, vwap, n_trades.
    bars_per_bucket : int
        Number of 10s bars per 15-min bucket (default 90 = 15min / 10s).

    Returns
    -------
    pd.DataFrame
        15-min bars with columns: date, bucket, vwap, close, volume,
        buy_vol, sell_vol, net_flow, n_trades.
    """
    df = df.copy()
    df["volume"] = df["buy_vol"] + df["sell_vol"]
    df["bucket"] = df["bar_idx"] // bars_per_bucket
    df["vwap_x_vol"] = df["vwap"] * df["volume"]

    grouped = df.groupby(["date", "bucket"], sort=True)

    agg = grouped.agg(
        vwap_x_vol_sum=("vwap_x_vol", "sum"),
        volume_sum=("volume", "sum"),
        close=("vwap", "last"),
        buy_vol=("buy_vol", "sum"),
        sell_vol=("sell_vol", "sum"),
        net_flow=("net_flow", "sum"),
        n_trades=("n_trades", "sum"),
    ).reset_index()

    # Proper VWAP: exclude zero-volume buckets from weight
    agg["vwap"] = np.where(
        agg["volume_sum"] > 0,
        agg["vwap_x_vol_sum"] / agg["volume_sum"],
        agg["close"],  # Fallback to last price if no volume
    )
    agg["volume"] = agg["volume_sum"]

    return agg[
        ["date", "bucket", "vwap", "close", "volume", "buy_vol", "sell_vol", "net_flow", "n_trades"]
    ]


# ---------------------------------------------------------------------------
# Step 12: Discrete hedging simulator
# ---------------------------------------------------------------------------


def _bs_call_price(S: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    """Black-Scholes call price."""
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0)
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def _bs_put_price(S: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    """Black-Scholes put price."""
    if T <= 0 or sigma <= 0:
        return max(K - S, 0.0)
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def _bs_straddle_delta(S: float, K: float, T: float, sigma: float) -> float:
    """Full BS straddle delta: 2*N(d1) - 1."""
    if T <= 0 or sigma <= 0:
        return 0.0
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * sigma**2 * T) / (sigma * sqrt_T)
    return 2.0 * norm.cdf(d1) - 1.0


def simulate_discrete_hedge_pnl(
    signal: np.ndarray,
    bars_15min: pd.DataFrame,
    implied_vol: np.ndarray,
    spot_prices: np.ndarray,
    tenor_days: int = 30,
    roll_at_days: int = 5,
    spread_bps: float = 2.0,
    option_cost_base: float = 1.0,
) -> dict[str, np.ndarray]:
    """Bar-by-bar discrete hedging simulation.

    For each day:
    1. Track fixed strike K (set at entry, reset on roll/flip)
    2. Track T_rem (decrements daily)
    3. At each 15-min bar: observe price from bar i-1 (the lag),
       compute full BS delta, execute at bar i's VWAP
    4. Compute option P&L from BS revaluation, hedge P&L from fills,
       and hedge cost from spread

    Parameters
    ----------
    signal : np.ndarray
        Daily position sizes. +ve = short vol, -ve = long vol.
        Shape: (n_days,).
    bars_15min : pd.DataFrame
        15-min bars with columns: date, bucket, vwap, close, volume.
    implied_vol : np.ndarray
        Daily ATM implied vol (annualized decimal). Shape: (n_days,).
    spot_prices : np.ndarray
        Daily spot prices (used for strike setting). Shape: (n_days,).
    tenor_days : int
        Initial option tenor in trading days.
    roll_at_days : int
        Roll when T_rem falls below this.
    spread_bps : float
        Round-trip spread of underlying in basis points.
    option_cost_base : float
        Base option half-spread in vol points.

    Returns
    -------
    dict[str, np.ndarray]
        Keys: pnl_option, pnl_hedge, cost_hedge, cost_option, pnl_net, T_rem.
        All arrays have shape (n_days,).
    """
    from volforecast.evaluation.realistic_straddle import option_spread_vol_pts

    signal = np.asarray(signal, dtype=np.float64)
    implied_vol = np.asarray(implied_vol, dtype=np.float64)
    spot_prices = np.asarray(spot_prices, dtype=np.float64)
    n_days = len(signal)

    # Get unique dates in order
    dates = bars_15min["date"].unique()
    if len(dates) < n_days:
        n_days = len(dates)
        signal = signal[:n_days]
        implied_vol = implied_vol[:n_days]
        spot_prices = spot_prices[:n_days]

    # Pre-index bars by date for fast lookup
    bars_by_date = {d: grp for d, grp in bars_15min.groupby("date", sort=True)}

    # Output arrays
    pnl_option = np.zeros(n_days)
    pnl_hedge = np.zeros(n_days)
    cost_hedge = np.zeros(n_days)
    cost_option = np.zeros(n_days)
    T_rem_arr = np.zeros(n_days)

    # State
    current_T_rem = float(tenor_days)
    strike = spot_prices[0]  # ATM at entry
    prev_signal = 0.0
    prev_delta = 0.0  # Shares held from previous period

    for day_idx in range(n_days):
        curr_sig = signal[day_idx]
        iv = max(implied_vol[day_idx], 1e-8)
        date_key = dates[day_idx]

        # --- Event detection ---
        entered = prev_signal == 0.0 and curr_sig != 0.0
        exited = prev_signal != 0.0 and curr_sig == 0.0
        flipped = (prev_signal > 0 and curr_sig < 0) or (prev_signal < 0 and curr_sig > 0)
        rolled = False

        # Check for roll
        if curr_sig != 0.0 and current_T_rem <= roll_at_days:
            rolled = True
            # Charge roll cost
            exit_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            entry_spread = option_spread_vol_pts(float(tenor_days), option_cost_base)
            vega = spot_prices[day_idx] * np.sqrt(float(tenor_days) / 252.0) * norm.pdf(0.0)
            cost_option[day_idx] = (2 * exit_spread + 2 * entry_spread) / 100.0 * vega
            # Reset state
            current_T_rem = float(tenor_days)
            strike = spot_prices[day_idx]
            prev_delta = 0.0
        elif entered:
            entry_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            vega = spot_prices[day_idx] * np.sqrt(current_T_rem / 252.0) * norm.pdf(0.0)
            cost_option[day_idx] = 2 * entry_spread / 100.0 * vega
            strike = spot_prices[day_idx]
            prev_delta = 0.0
        elif flipped:
            exit_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            entry_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            vega = spot_prices[day_idx] * np.sqrt(current_T_rem / 252.0) * norm.pdf(0.0)
            cost_option[day_idx] = (2 * exit_spread + 2 * entry_spread) / 100.0 * vega
            strike = spot_prices[day_idx]
            prev_delta = 0.0
        elif exited:
            exit_spread = option_spread_vol_pts(current_T_rem, option_cost_base)
            vega = spot_prices[day_idx] * np.sqrt(current_T_rem / 252.0) * norm.pdf(0.0)
            cost_option[day_idx] = 2 * exit_spread / 100.0 * vega
            prev_delta = 0.0

        T_rem_arr[day_idx] = current_T_rem

        if curr_sig == 0.0:
            prev_signal = curr_sig
            if not rolled:
                current_T_rem -= 1.0
                current_T_rem = max(current_T_rem, 1.0)
            continue

        # --- Intraday simulation ---
        T_rem_years = current_T_rem / 252.0

        # Get today's bars
        if date_key in bars_by_date:
            day_bars = bars_by_date[date_key].sort_values("bucket")
            bar_vwaps = day_bars["vwap"].values
            bar_closes = day_bars["close"].values
        else:
            # No bar data for this day - use spot price
            bar_vwaps = np.full(26, spot_prices[day_idx])
            bar_closes = np.full(26, spot_prices[day_idx])

        n_bars = len(bar_vwaps)

        # Option value at start of day (mark at yesterday's close or today's open)
        S_start = bar_closes[0] if n_bars > 0 else spot_prices[day_idx]
        opt_val_start = _bs_call_price(S_start, strike, T_rem_years, iv) + _bs_put_price(
            S_start, strike, T_rem_years, iv
        )

        # Simulate hedging bar by bar
        day_hedge_pnl = 0.0
        day_hedge_cost = 0.0
        current_shares = prev_delta

        for bar_i in range(n_bars):
            # Observe price from bar i (lag: compute delta from previous close)
            if bar_i == 0:
                obs_price = S_start
            else:
                obs_price = bar_closes[bar_i - 1]

            # Compute target delta from observed price
            target_delta = _bs_straddle_delta(obs_price, strike, T_rem_years, iv)
            # For short vol (signal > 0): we are short the straddle,
            # so hedge is -position * straddle_delta
            target_shares = -curr_sig * target_delta

            # Execute at this bar's VWAP
            exec_price = bar_vwaps[bar_i]
            shares_traded = target_shares - current_shares

            # Hedge cost
            trade_cost = abs(shares_traded) * exec_price * (spread_bps / 10000.0)
            day_hedge_cost += trade_cost

            # Hedge P&L: shares held * price change
            if bar_i > 0:
                price_change = bar_closes[bar_i] - bar_closes[bar_i - 1]
                day_hedge_pnl += current_shares * price_change

            current_shares = target_shares

        # End-of-day: mark to close
        S_end = bar_closes[-1] if n_bars > 0 else spot_prices[day_idx]

        # Option value at end of day
        T_rem_end = max(T_rem_years - 1.0 / 252.0, 1e-8)
        opt_val_end = _bs_call_price(S_end, strike, T_rem_end, iv) + _bs_put_price(
            S_end, strike, T_rem_end, iv
        )

        # Option P&L: for short vol, profit from option value decrease
        option_pnl = -curr_sig * (opt_val_end - opt_val_start)

        # Normalize by spot
        spot_norm = max(spot_prices[day_idx], 1e-8)
        pnl_option[day_idx] = option_pnl / spot_norm
        pnl_hedge[day_idx] = day_hedge_pnl / spot_norm
        cost_hedge[day_idx] = day_hedge_cost / spot_norm

        # Store end-of-day delta for next day
        prev_delta = current_shares
        prev_signal = curr_sig

        # Decrement tenor
        if not rolled:
            current_T_rem -= 1.0
            current_T_rem = max(current_T_rem, 1.0)

    # Net P&L = option P&L + hedge P&L - costs
    cost_option_norm = np.abs(signal[:n_days]) * cost_option / np.maximum(spot_prices, 1e-8)
    pnl_net = pnl_option + pnl_hedge - cost_hedge - cost_option_norm

    return {
        "pnl_option": pnl_option,
        "pnl_hedge": pnl_hedge,
        "cost_hedge": cost_hedge,
        "cost_option": cost_option_norm,
        "pnl_net": pnl_net,
        "T_rem": T_rem_arr,
    }


# ---------------------------------------------------------------------------
# Step 14: Per-day realized kurtosis
# ---------------------------------------------------------------------------


def compute_per_day_realized_kurtosis(bars: pd.DataFrame) -> np.ndarray:
    """Compute per-day realized kurtosis from 15-min bar closes.

    RK_t = n * sum(r^4) / (sum(r^2))^2

    where r are 15-min log returns within day t.

    Parameters
    ----------
    bars : pd.DataFrame
        15-min bars with columns: date, bucket, close.

    Returns
    -------
    np.ndarray
        Per-day realized kurtosis values.
    """
    dates = bars["date"].unique()
    kurtosis = np.zeros(len(dates))

    for i, date in enumerate(dates):
        day_bars = bars[bars["date"] == date].sort_values("bucket")
        closes = day_bars["close"].values

        if len(closes) < 3:
            kurtosis[i] = 3.0  # Default to normal
            continue

        # Log returns between consecutive bars
        returns = np.diff(np.log(closes))
        n = len(returns)

        if n < 2:
            kurtosis[i] = 3.0
            continue

        r2_sum = np.sum(returns**2)
        r4_sum = np.sum(returns**4)

        if r2_sum < 1e-20:
            kurtosis[i] = 3.0
            continue

        # Realized kurtosis: n * sum(r^4) / (sum(r^2))^2
        kurtosis[i] = n * r4_sum / (r2_sum**2)

    return kurtosis


# ---------------------------------------------------------------------------
# Step 13: Hedging-error floor experiment
# ---------------------------------------------------------------------------


def hedging_error_floor_experiment(
    n_values: list[int],
    variances: list[float],
) -> tuple[float, float]:
    """Fit Var(hedge_error) = a/N + b to estimate jump floor.

    Under pure diffusion, b should be ~0. Under jumps (Broden & Tankov 2010),
    b > 0 materially indicates a variance floor that doesn't disappear
    with more frequent hedging.

    Parameters
    ----------
    n_values : list[int]
        Number of rebalances per day tested.
    variances : list[float]
        Measured hedge error variance at each N.

    Returns
    -------
    tuple[float, float]
        (a, b) coefficients from the fit Var = a/N + b.
    """
    # Fit: var = a * (1/N) + b using least squares
    # Design matrix: [1/N, 1]
    x = np.array([1.0 / n for n in n_values])
    y = np.array(variances)

    # Linear regression: y = a*x + b
    x_mean = np.mean(x)
    y_mean = np.mean(y)

    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    ss_xx = np.sum((x - x_mean) ** 2)

    if ss_xx < 1e-20:
        return 0.0, float(y_mean)

    a = float(ss_xy / ss_xx)
    b = float(y_mean - a * x_mean)

    return a, b


# ---------------------------------------------------------------------------
# Step 15: Phase 1 vs Phase 2 validation
# ---------------------------------------------------------------------------


def validate_phase1_vs_phase2(
    metrics_p1: dict[str, float],
    metrics_p2: dict[str, float],
) -> dict[str, bool]:
    """Validate Phase 1 analytic vs Phase 2 simulated results.

    Checks:
    - Mean PnL match within 10%
    - Std match within 25%
    - Sharpe match within 0.3

    Parameters
    ----------
    metrics_p1 : dict
        Phase 1 metrics with keys: sharpe, mean_pnl, std_pnl.
    metrics_p2 : dict
        Phase 2 metrics with keys: sharpe, mean_pnl, std_pnl.

    Returns
    -------
    dict[str, bool]
        Keys: sharpe_pass, mean_pnl_pass, std_pass.
    """
    sharpe_diff = abs(metrics_p1["sharpe"] - metrics_p2["sharpe"])
    sharpe_pass = sharpe_diff <= 0.3

    # Mean PnL: within 10%
    p1_mean = abs(metrics_p1["mean_pnl"])
    p2_mean = abs(metrics_p2["mean_pnl"])
    denom = max(p1_mean, p2_mean, 1e-12)
    mean_pnl_pass = abs(p1_mean - p2_mean) / denom <= 0.10

    # Std: within 25%
    p1_std = metrics_p1["std_pnl"]
    p2_std = metrics_p2["std_pnl"]
    std_denom = max(p1_std, p2_std, 1e-12)
    std_pass = abs(p1_std - p2_std) / std_denom <= 0.25

    return {
        "sharpe_pass": sharpe_pass,
        "mean_pnl_pass": mean_pnl_pass,
        "std_pass": std_pass,
    }
