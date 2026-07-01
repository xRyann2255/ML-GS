"""Tick-to-bar resampling and daily RV computation from tick data.

Bridges raw tick data (from Chunk Store) to the RV/feature computation
modules in features/. Handles irregular tick spacing via previous-tick
interpolation to a regular grid.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from volforecast.data.measures import (
    compute_bpv,
    compute_continuous_variation,
    compute_jump_variation,
    compute_realized_moments,
    compute_realized_tripower_quarticity,
    compute_realized_variance,
    compute_rq,
    compute_semivariances,
    compute_signed_jumps,
    detect_jumps,
    lee_mykland_test,
    noise_gap,
    realized_kernel,
)

# Lee-Mykland (2008) local window: ~2h of 5-min bars (2 * 78 bars/day)
LM_LOCAL_WINDOW = 156


def resample_trades_to_bars(
    trades: pd.DataFrame,
    freq: str = "5min",
    market_open: str = "09:30",
    market_close: str = "16:00",
) -> pd.DataFrame:
    """Resample irregular tick data to regular bars using previous-tick interpolation.

    Parameters
    ----------
    trades : pd.DataFrame
        Must have a DatetimeIndex (tz-aware) and a 'price' column.
    freq : str
        Pandas offset alias for bar frequency (default: '5min').
    market_open, market_close : str
        Market hours as HH:MM strings.

    Returns
    -------
    pd.DataFrame
        Regular-frequency bars with columns: price, log_return.
        Index: DatetimeIndex at bar boundaries.
    """
    if trades.empty:
        return pd.DataFrame(columns=["price", "log_return"])

    prices = trades["price"].copy()

    # Deduplicate: multiple ticks can share the same timestamp in real data.
    # Keep the last price at each timestamp (previous-tick convention).
    prices = prices[~prices.index.duplicated(keep="last")]

    # Determine the trading day from the data
    first_ts = prices.index[0]
    trade_date = first_ts.date()
    tz = first_ts.tzinfo

    # Build regular grid within market hours
    open_dt = pd.Timestamp(
        year=trade_date.year,
        month=trade_date.month,
        day=trade_date.day,
        hour=int(market_open.split(":")[0]),
        minute=int(market_open.split(":")[1]),
        tz=tz,
    )
    close_dt = pd.Timestamp(
        year=trade_date.year,
        month=trade_date.month,
        day=trade_date.day,
        hour=int(market_close.split(":")[0]),
        minute=int(market_close.split(":")[1]),
        tz=tz,
    )

    grid = pd.date_range(start=open_dt, end=close_dt, freq=freq)

    # Reindex tick prices onto the regular grid using forward-fill
    # (previous-tick interpolation: each bar gets the last trade price at or before it)
    combined_index = prices.index.union(grid)
    prices_reindexed = prices.reindex(combined_index).ffill()
    bar_prices = prices_reindexed.reindex(grid)

    # Backfill any leading NaNs (if first tick is after first grid point)
    bar_prices = bar_prices.bfill()

    # Compute log returns
    log_returns = np.log(bar_prices / bar_prices.shift(1))

    return pd.DataFrame(
        {"price": bar_prices, "log_return": log_returns},
        index=grid,
    )


def compute_daily_rv_from_ticks(
    trades: pd.DataFrame,
    freq: str = "5min",
    market_open: str = "09:30",
    market_close: str = "16:00",
) -> dict:
    """Compute all daily RV measures from tick-level trade data.

    Parameters
    ----------
    trades : pd.DataFrame
        Tick data with DatetimeIndex and 'price' column.
    freq : str
        Bar sampling frequency (default: '5min').
    market_open, market_close : str
        Market hours.

    Returns
    -------
    dict
        Keys: rv, log_rv, rq, bpv, rs_positive, rs_negative,
        jump_stat, jump_indicator, rk, noise_gap, n_ticks, n_bars.
    """
    # Step 1: Resample to bars
    bars = resample_trades_to_bars(trades, freq, market_open, market_close)
    returns = bars["log_return"].dropna()
    returns_series = pd.Series(returns.values)

    # Step 2: Compute RV measures from bar returns
    rv = compute_realized_variance(returns_series)
    rq = compute_rq(returns_series)
    bpv = compute_bpv(returns_series)
    rtq = compute_realized_tripower_quarticity(returns_series)
    semivars = compute_semivariances(returns_series)
    n_obs = len(returns_series)
    jump_test = detect_jumps(rv, bpv, rtq, n_obs)
    j_var = compute_jump_variation(rv, bpv, jump_test["jump_indicator"])
    c_var = compute_continuous_variation(rv, j_var)

    # Step 3: Noise-robust estimators from tick-level log prices
    tick_log_prices = np.log(trades["price"].values)
    rk_value = realized_kernel(tick_log_prices)
    gap = noise_gap(rk_value, rv)

    # Step 4: Lee-Mykland intraday jump detection + signed jumps
    lm_result = lee_mykland_test(returns_series, local_window=min(LM_LOCAL_WINDOW, n_obs - 1))
    signed_jumps = compute_signed_jumps(returns_series, lm_result["is_jump"])

    # Step 5: Realized moments (skewness, kurtosis)
    moments = compute_realized_moments(returns_series)

    return {
        "rv": rv,
        "log_rv": float(np.log(rv)) if rv > 0 else float("-inf"),
        "rq": rq,
        "rtq": rtq,
        "bpv": bpv,
        "rs_positive": semivars["rs_positive"],
        "rs_negative": semivars["rs_negative"],
        "jump_stat": jump_test["z_stat"],
        "jump_indicator": jump_test["jump_indicator"],
        "continuous_variation": c_var,
        "jump_variation": j_var,
        "j_positive": signed_jumps["j_positive"],
        "j_negative": signed_jumps["j_negative"],
        "realized_skewness": moments["realized_skewness"],
        "realized_kurtosis": moments["realized_kurtosis"],
        "rk": rk_value,
        "noise_gap": gap,
        "n_ticks": len(trades),
        "n_bars": len(returns),
    }


def compute_daily_rv_from_bars(bars: pd.DataFrame) -> dict:
    """Compute all Layer 0+1 features from pre-aggregated 5-min bars.

    Equivalent to compute_daily_rv_from_ticks() but operates on ~78 bars
    instead of millions of raw ticks. Does NOT compute realized_kernel or
    noise_gap (those require tick-level data).

    Parameters
    ----------
    bars : pd.DataFrame
        5-min bars with columns: close (required), plus optionally
        open, high, low, volume, n_ticks. Must be sorted by time.

    Returns
    -------
    dict
        Same keys as compute_daily_rv_from_ticks() with rk=NaN, noise_gap=NaN.

    Raises
    ------
    ValueError
        If bars has fewer than 2 rows (need at least 1 return).
    """
    if len(bars) < 2:
        raise ValueError(f"Need at least 2 bars to compute returns, got {len(bars)}")

    close_prices = bars["close"].values.astype(np.float64)

    # Replace zeros/NaNs with previous valid price (no trade = price unchanged)
    mask = (close_prices == 0) | np.isnan(close_prices)
    if mask.any():
        for i in range(len(close_prices)):
            if mask[i]:
                close_prices[i] = close_prices[i - 1] if i > 0 else np.nan
        # If leading bars are still invalid, drop them
        first_valid = np.argmax(~np.isnan(close_prices))
        if first_valid > 0:
            close_prices = close_prices[first_valid:]
        if len(close_prices) < 2:
            raise ValueError("Not enough valid close prices after removing zeros")

    log_returns = np.diff(np.log(close_prices))
    returns_series = pd.Series(log_returns)

    n_obs = len(returns_series)

    # Core measures
    rv = compute_realized_variance(returns_series)
    rq = compute_rq(returns_series)
    bpv = compute_bpv(returns_series)
    rtq = compute_realized_tripower_quarticity(returns_series)
    semivars = compute_semivariances(returns_series)
    jump_test = detect_jumps(rv, bpv, rtq, n_obs)
    j_var = compute_jump_variation(rv, bpv, jump_test["jump_indicator"])
    c_var = compute_continuous_variation(rv, j_var)

    # Lee-Mykland intraday jump detection + signed jumps
    lm_result = lee_mykland_test(returns_series, local_window=min(LM_LOCAL_WINDOW, n_obs - 1))
    signed_jumps = compute_signed_jumps(returns_series, lm_result["is_jump"])

    # Realized moments
    moments = compute_realized_moments(returns_series)

    # Tick count from bars (sum of per-bar n_ticks if available)
    if "n_ticks" in bars.columns:
        total_ticks = int(bars["n_ticks"].sum())
    else:
        total_ticks = 0

    return {
        "rv": rv,
        "log_rv": float(np.log(rv)) if rv > 0 else float("-inf"),
        "rq": rq,
        "rtq": rtq,
        "bpv": bpv,
        "rs_positive": semivars["rs_positive"],
        "rs_negative": semivars["rs_negative"],
        "jump_stat": jump_test["z_stat"],
        "jump_indicator": jump_test["jump_indicator"],
        "continuous_variation": c_var,
        "jump_variation": j_var,
        "j_positive": signed_jumps["j_positive"],
        "j_negative": signed_jumps["j_negative"],
        "realized_skewness": moments["realized_skewness"],
        "realized_kurtosis": moments["realized_kurtosis"],
        "rk": np.nan,
        "noise_gap": np.nan,
        "n_ticks": total_ticks,
        "n_bars": n_obs,
    }


def aggregate_to_5min(
    df: pd.DataFrame,
    bar_interval_s: int = 10,
    target_interval_s: int = 300,
) -> pd.DataFrame:
    """Aggregate sub-5-min bars into 5-minute bars per date.

    Parameters
    ----------
    df : pd.DataFrame
        Columns must include [date, bar_idx, log_ret]. ``bar_idx`` runs
        0..N per date.
    bar_interval_s : int
        Interval of the input bars in seconds (default 10).
    target_interval_s : int
        Desired output interval in seconds (default 300 = 5 min).

    Returns
    -------
    pd.DataFrame
        Columns: [date, bar_idx, log_ret, abs_ret, rv_5min].
    """
    out_cols = ["date", "bar_idx", "log_ret", "abs_ret", "rv_5min"]

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    bars_per_group = target_interval_s // bar_interval_s

    df = df.copy()
    df["group_idx"] = df["bar_idx"] // bars_per_group

    # Count bars per (date, group) to detect incomplete trailing groups
    group_sizes = df.groupby(["date", "group_idx"])["log_ret"].transform("count")
    df = df[group_sizes == bars_per_group]

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    agg = df.groupby(["date", "group_idx"], sort=True).agg(
        log_ret=("log_ret", "sum"),
        rv_5min=("log_ret", lambda x: (x**2).sum()),
    ).reset_index()

    agg["abs_ret"] = agg["log_ret"].abs()

    # Sequential bar_idx 0..N-1 per date
    agg["bar_idx"] = agg.groupby("date").cumcount()

    return agg[out_cols].reset_index(drop=True)
