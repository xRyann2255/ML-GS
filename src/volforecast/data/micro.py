"""Per-symbol microstructure ingestion from ChunkStore LeeReady processor.

Fetches tick data with server-side LeeReadySumVolume trade classification,
aggregates into 10-second signed-volume bars, then produces:
  1. Daily aggregates (signed_volume_ratio, vpin, ofi) → data/raw/micro/{SYM}.parquet
  2. 10-second bar sequences (for LSTM/TCN) → data/raw/micro/sequences/{SYM}.parquet

Public API:
    ingest_symbol_micro  — Fetch + compute + save for one symbol (both outputs)
    fetch_micro_bars     — LeeReady + AggGroupBy fetch from ChunkStore
    compute_vpin         — Volume-time bucket VPIN (Easley et al. 2012)
    compute_daily_micro  — 10s bars → daily scalar aggregates
    save_micro_cache     — Persist daily aggregates parquet (atomic)
    save_sequences_cache — Persist 10s bar sequences parquet (atomic)
    load_micro_cache     — Load cached daily aggregates (or None)
    load_sequences_cache — Load cached sequences (or None)
    cache_covers_range   — Check if cached daily data covers requested dates
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Callable
from datetime import date, datetime
from datetime import time as dt_time
from pathlib import Path

import numpy as np
import pandas as pd

from volforecast.constants import (
    CHUNKDB,
    MICRO_BAR_INTERVAL,
    MICRO_DAILY_COLUMNS,
    MICRO_FIELDS,
    TICKER_TO_RIC,
    VPIN_N_BUCKETS,
)
from volforecast.utils.paths import micro_cache_dir, micro_sequences_dir, micro_staging_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Processor construction
# ---------------------------------------------------------------------------

_AGG_OPERATIONS = [
    "sum(TRDVOL_1)",
    "count(TRDPRC_1)",
    "first(TRDPRC_1)",
    "last(TRDPRC_1)",
]


def _build_processors(interval: float = MICRO_BAR_INTERVAL) -> list:
    """Build AggGroupBy processor for server-side 10s bar aggregation.

    Client-side BVC (Bulk Volume Classification) is applied after fetch
    to classify bars as buy/sell initiated using the tick rule.

    Returns
    -------
    list
        Single-element list: [AggGroupBy(...)].

    Raises
    ------
    ConnectionError
        If pytickclient.processor is not available.
    """
    try:
        from pytickclient import processor
    except ImportError as exc:
        raise ConnectionError("pytickclient.processor not available") from exc

    agg = processor.AggGroupBy(
        groupByOperations=_AGG_OPERATIONS,
        interval=interval,
    )

    return [agg]


def _classify_bars_bvc(df: pd.DataFrame) -> pd.DataFrame:
    """Apply Bulk Volume Classification (tick rule) to OHLCV bars.

    For each bar:
      - close > open → all volume is buy-initiated
      - close < open → all volume is sell-initiated
      - close == open → split 50/50

    Adds columns: buy_vol, sell_vol, neutral_vol.
    """
    volume = df["volume"].values.astype(np.float64)
    open_p = df["open"].values.astype(np.float64)
    close_p = df["close"].values.astype(np.float64)

    buy_vol = np.zeros_like(volume)
    sell_vol = np.zeros_like(volume)
    neutral_vol = np.zeros_like(volume)

    up = close_p > open_p
    down = close_p < open_p
    flat = ~up & ~down

    buy_vol[up] = volume[up]
    sell_vol[down] = volume[down]
    # Flat bars: split evenly
    buy_vol[flat] = volume[flat] * 0.5
    sell_vol[flat] = volume[flat] * 0.5

    df = df.copy()
    df["buy_vol"] = buy_vol
    df["sell_vol"] = sell_vol
    df["neutral_vol"] = neutral_vol
    return df


# ---------------------------------------------------------------------------
# Fetch from ChunkStore
# ---------------------------------------------------------------------------


def fetch_micro_bars(
    symbol: str,
    dates: list[date],
    batch_size: int = 20,
    timeout_s: float = 120.0,
    retries: int = 2,
    interval: float = MICRO_BAR_INTERVAL,
    on_batch: Callable[[dict[date, pd.DataFrame]], None] | None = None,
    progress=None,
) -> dict[date, pd.DataFrame]:
    """Fetch 10-second OHLCV bars and classify via BVC (tick rule).

    Server-side AggGroupBy produces OHLCV bars. Client-side BVC then
    classifies each bar's volume as buy or sell initiated.

    Parameters
    ----------
    symbol : str
        Ticker symbol (must be in SYMBOL_UNIVERSE).
    dates : list[date]
        Trading days to fetch.
    batch_size : int
        Max days per API call (default 20).
    timeout_s : float
        Timeout per call.
    retries : int
        Retry count per failed call.
    interval : float
        Bar interval in seconds (default 10.0).
    on_batch : callable, optional
        Callback invoked after each successful batch with the new bars.
        Signature: on_batch(batch_bars: dict[date, DataFrame]).
        Used for incremental staging writes.
    progress : optional
        Progress display handle (StageProgress). Used for per-symbol subtask.

    Returns
    -------
    dict[date, pd.DataFrame]
        Mapping of date → DataFrame with columns:
        [buy_vol, sell_vol, neutral_vol, vwap, n_trades]
    """
    from volforecast.data.chunk_store import (
        _chunk_query_with_timeout,
        _ensure_session,
        _group_contiguous_dates,
        _resolve_es_symbol,
        _validate_symbol,
    )

    if not dates:
        return {}

    _validate_symbol(symbol)

    try:
        from pytickclient import query  # noqa: F401
    except ImportError as exc:
        raise ConnectionError("pytickclient not available") from exc

    _ensure_session()

    import pytz

    TZ = pytz.timezone("America/New_York")

    processors = _build_processors(interval=interval)
    result: dict[date, pd.DataFrame] = {}

    # Per-symbol subtask progress bar
    _sub_key: str | None = None
    total_days = len(dates)
    days_fetched = 0
    if progress is not None:
        _sub_key = progress.add_subtask(
            total=total_days, description=f"{symbol} (0/{total_days} days)"
        )

    # Column mapping from AggGroupBy output → intermediate names
    _COL_MAP = {
        "sum_TRDVOL_1": "volume",
        "count_TRDPRC_1": "n_trades",
        "last_TRDPRC_1": "close",
        "first_TRDPRC_1": "open",
    }

    def _fetch_chunk(chunk_symbol: str, chunk: list[date]) -> None:
        first_day = chunk[0]
        last_day = chunk[-1]
        st = TZ.localize(datetime(first_day.year, first_day.month, first_day.day, 9, 30, 0))
        et = TZ.localize(datetime(last_day.year, last_day.month, last_day.day, 16, 0, 0))

        raw = _chunk_query_with_timeout(
            [chunk_symbol],
            st,
            et,
            CHUNKDB,
            MICRO_FIELDS,
            timeout_s=timeout_s,
            retries=retries,
            processors=processors,
        )

        if isinstance(raw, dict) and not raw:
            return
        if hasattr(raw, "__len__") and len(raw) == 0:
            return

        df = pd.DataFrame(raw)
        if df.empty:
            return

        # Coerce numeric columns
        for col in _COL_MAP:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Parse timestamps: UTC → Eastern
        df["Time"] = pd.to_datetime(df["Time"])
        if df["Time"].dt.tz is None:
            df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)
        else:
            df["Time"] = df["Time"].dt.tz_convert(TZ)

        # Rename columns
        df = df.rename(columns=_COL_MAP)

        # Split by date
        df["_date"] = df["Time"].dt.date
        for day, grp in df.groupby("_date"):
            if day not in chunk:
                continue
            # Filter to RTH only (09:30-16:00 ET)
            mkt_open = grp["Time"].dt.time >= dt_time(9, 30)
            mkt_close = grp["Time"].dt.time <= dt_time(16, 0)
            grp = grp[mkt_open & mkt_close].copy()
            if grp.empty:
                continue

            # Apply BVC classification
            grp = _classify_bars_bvc(grp)

            # NOTE: "vwap" is actually midprice (open+close)/2, not true VWAP.
            # Kept as "vwap" for backward compatibility with downstream paths.
            grp["vwap"] = (grp["open"] + grp["close"]) / 2.0

            out_cols = ["buy_vol", "sell_vol", "neutral_vol", "vwap", "n_trades"]
            result[day] = grp[out_cols].reset_index(drop=True)

    def _fetch_chunk_and_stage(chunk_symbol: str, chunk: list[date]) -> None:
        """Fetch a chunk and invoke on_batch callback with new bars."""
        nonlocal days_fetched
        before_keys = set(result.keys())
        _fetch_chunk(chunk_symbol, chunk)
        new_keys = set(result.keys()) - before_keys
        if new_keys and on_batch is not None:
            batch_bars = {d: result[d] for d in new_keys}
            on_batch(batch_bars)
        # Advance per-symbol subtask by number of days in this chunk
        n_new = len(chunk)
        days_fetched += n_new
        if progress is not None and _sub_key is not None:
            progress.advance(_sub_key, n_new)
            progress.update_subtask(
                _sub_key,
                f"{symbol} ({days_fetched}/{total_days} days)",
            )

    # Dispatch: handle ES contract rolling vs normal symbols
    if symbol == "ES":
        contract_groups: dict[str, list[date]] = {}
        for d in sorted(dates):
            cs = _resolve_es_symbol(d)
            contract_groups.setdefault(cs, []).append(d)
        for cs, cs_dates in contract_groups.items():
            for group in _group_contiguous_dates(cs_dates):
                for i in range(0, len(group), batch_size):
                    _fetch_chunk_and_stage(cs, group[i : i + batch_size])
    else:
        chunk_ric = TICKER_TO_RIC.get(symbol, symbol)
        for group in _group_contiguous_dates(sorted(dates)):
            for i in range(0, len(group), batch_size):
                _fetch_chunk_and_stage(chunk_ric, group[i : i + batch_size])

    # Remove subtask when done
    if progress is not None and _sub_key is not None:
        progress.remove_subtask(_sub_key)

    return result


# ---------------------------------------------------------------------------
# VPIN computation
# ---------------------------------------------------------------------------


def compute_vpin(
    buy_vols: np.ndarray,
    sell_vols: np.ndarray,
    bucket_volume: int | float,
    n_buckets: int = VPIN_N_BUCKETS,
) -> float:
    """Compute Volume-Synchronized Probability of Informed Trading (VPIN).

    Reference: Easley, Lopez de Prado & O'Hara (2012), Eq. 1.

    VPIN = (1/n) * Σ |V^B_i - V^S_i| / V_bucket

    Volume-time buckets: each bucket accumulates bars until total volume
    reaches `bucket_volume`. Bars crossing bucket boundaries are split
    proportionally between the current and next bucket.

    Parameters
    ----------
    buy_vols : ndarray
        Buy volume per bar.
    sell_vols : ndarray
        Sell volume per bar.
    bucket_volume : int or float
        Target volume per bucket.
    n_buckets : int
        Number of buckets for VPIN estimation (default: 50).

    Returns
    -------
    float
        VPIN estimate in [0, 1]. NaN if insufficient volume.
    """
    buy_vols = np.asarray(buy_vols, dtype=np.float64)
    sell_vols = np.asarray(sell_vols, dtype=np.float64)

    total_volume = buy_vols.sum() + sell_vols.sum()
    if total_volume <= 0 or bucket_volume <= 0:
        return float("nan")

    # Check if we have enough volume for n_buckets
    if total_volume < bucket_volume * n_buckets:
        return float("nan")

    # Accumulate bars into volume-time buckets
    bucket_buy = 0.0
    bucket_sell = 0.0
    bucket_filled = 0.0
    bucket_imbalances: list[float] = []

    for i in range(len(buy_vols)):
        bar_buy = buy_vols[i]
        bar_sell = sell_vols[i]
        bar_total = bar_buy + bar_sell

        if bar_total <= 0:
            continue

        remaining_bar = bar_total

        while remaining_bar > 0:
            space_in_bucket = bucket_volume - bucket_filled
            fill = min(remaining_bar, space_in_bucket)

            # Use the bar's overall buy/sell ratio for proportional split
            buy_ratio = bar_buy / bar_total

            bucket_buy += fill * buy_ratio
            bucket_sell += fill * (1.0 - buy_ratio)
            bucket_filled += fill
            remaining_bar -= fill

            # Bucket full?
            if bucket_filled >= bucket_volume - 1e-10:
                imbalance = abs(bucket_buy - bucket_sell) / bucket_volume
                bucket_imbalances.append(imbalance)
                bucket_buy = 0.0
                bucket_sell = 0.0
                bucket_filled = 0.0

                # If we have enough buckets, we can stop
                if len(bucket_imbalances) >= n_buckets:
                    break

        if len(bucket_imbalances) >= n_buckets:
            break

    if len(bucket_imbalances) < n_buckets:
        return float("nan")

    # VPIN = mean of last n_buckets imbalances
    return float(np.mean(bucket_imbalances[-n_buckets:]))


# ---------------------------------------------------------------------------
# Daily aggregate computation
# ---------------------------------------------------------------------------


def compute_daily_micro(
    bars_by_date: dict[date, pd.DataFrame],
    bucket_volume: int | float,
    n_buckets: int = VPIN_N_BUCKETS,
) -> pd.DataFrame:
    """Aggregate 10-second bars to daily microstructure scalars.

    Parameters
    ----------
    bars_by_date : dict[date, DataFrame]
        Mapping of date → DataFrame with at least columns [buy_vol, sell_vol].
    bucket_volume : int or float
        VPIN bucket volume (total volume per bucket).
    n_buckets : int
        Number of VPIN buckets (default: 50).

    Returns
    -------
    pd.DataFrame
        Daily features with columns from MICRO_DAILY_COLUMNS.
        Index: date objects (sorted ascending).
    """
    records: list[dict] = []

    for day in sorted(bars_by_date.keys()):
        bars = bars_by_date[day]
        buy = bars["buy_vol"].values.astype(np.float64)
        sell = bars["sell_vol"].values.astype(np.float64)

        total_buy = float(buy.sum())
        total_sell = float(sell.sum())
        total_vol = total_buy + total_sell

        if total_vol <= 0:
            records.append(
                {
                    "date": day,
                    "signed_volume_ratio": float("nan"),
                    "vpin": float("nan"),
                    "order_flow_imbalance": float("nan"),
                    "buy_volume": 0.0,
                    "sell_volume": 0.0,
                    "total_volume": 0.0,
                }
            )
            continue

        signed_volume_ratio = abs(total_buy - total_sell) / total_vol
        order_flow_imbalance = (total_buy - total_sell) / total_vol
        vpin = compute_vpin(buy, sell, bucket_volume, n_buckets=n_buckets)

        records.append(
            {
                "date": day,
                "signed_volume_ratio": signed_volume_ratio,
                "vpin": vpin,
                "order_flow_imbalance": order_flow_imbalance,
                "buy_volume": total_buy,
                "sell_volume": total_sell,
                "total_volume": total_vol,
            }
        )

    if not records:
        return pd.DataFrame(columns=MICRO_DAILY_COLUMNS)

    df = pd.DataFrame(records).set_index("date")
    return df[MICRO_DAILY_COLUMNS]


# ---------------------------------------------------------------------------
# Sequence bar construction
# ---------------------------------------------------------------------------


def _build_sequences_df(bars_by_date: dict[date, pd.DataFrame]) -> pd.DataFrame:
    """Build flat sequences DataFrame from per-day 10s bars.

    Output schema (v3): [date, bar_idx, buy_vol, sell_vol, net_flow, vwap,
                         n_trades, log_ret, vol_share, buy_ratio,
                         log_n_trades, abs_ret, price_accel, rolling_vpin,
                         cum_rv, session_frac]

    V1 columns (buy_vol, sell_vol, net_flow, vwap, n_trades) preserved for
    backward compatibility with compute_daily_micro() and discrete_straddle.
    V2 columns (log_ret, vol_share, buy_ratio, log_n_trades, abs_ret) are
    stationary, split-invariant features for LSTM consumption.
    V3 columns (price_accel, rolling_vpin, cum_rv, session_frac) are enriched
    sequence features for improved LSTM signal discovery.
    """
    rows: list[pd.DataFrame] = []

    for day in sorted(bars_by_date.keys()):
        bars = bars_by_date[day]
        n_bars = len(bars)
        if n_bars == 0:
            continue

        buy = bars["buy_vol"].values.astype(np.float64)
        sell = bars["sell_vol"].values.astype(np.float64)
        mid = bars["vwap"].values.astype(np.float64) if "vwap" in bars.columns else np.full(n_bars, np.nan)
        nt = bars["n_trades"].values.astype(np.float64) if "n_trades" in bars.columns else np.zeros(n_bars)

        # --- v2 stationary features ---
        # 1. Bar-to-bar log return (first bar = 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            log_ret = np.log(mid[1:] / mid[:-1])
        log_ret = np.concatenate([[0.0], log_ret])
        log_ret = np.nan_to_num(log_ret, nan=0.0, posinf=0.0, neginf=0.0)

        # 2. Volume share (fraction of daily total)
        total_vol = buy + sell
        daily_total = total_vol.sum()
        vol_share = total_vol / (daily_total + 1e-10)

        # 3. Buy ratio (order flow imbalance)
        buy_ratio = buy / (total_vol + 1e-10)

        # 4. Detrended log trade count
        log_nt = np.log1p(nt)
        log_n_trades = log_nt - np.median(log_nt)

        # 5. Absolute return (spread/volatility proxy)
        abs_ret = np.abs(log_ret)

        # --- v3 enriched features ---
        # 6. Price acceleration (2nd difference of log prices, Optiver #1 feature)
        price_accel = np.diff(log_ret, prepend=0.0)
        price_accel[0] = 0.0  # first bar has no prior log_ret

        # 7. Rolling VPIN (volume-synchronized informed trading, 50-bar window)
        vpin_window = 50
        imbalance = np.abs(buy - sell)
        bar_total = buy + sell
        cum_imbalance = np.cumsum(imbalance)
        cum_total = np.cumsum(bar_total)
        # Step 1.4: vectorised rolling/expanding window. Equivalence to the
        # original loop:
        #   for i < W:  num = cum[i] - 0          = cum_pad[i] is 0  (pad zone)
        #   for i >= W: num = cum[i] - cum[i - W] = cum_pad[i] = cum[i - W]
        # Build a zero-prefixed cumulative sum so cum_pad[:n_bars] gives the
        # value to subtract: 0 in the expanding region and cum[i - W] in the
        # rolling region.
        pad = np.zeros(vpin_window, dtype=cum_imbalance.dtype)
        cim_pad = np.concatenate([pad, cum_imbalance])
        ctot_pad = np.concatenate([pad, cum_total])
        num = cum_imbalance - cim_pad[:n_bars]
        den = cum_total - ctot_pad[:n_bars]
        rolling_vpin = num / (den + 1e-10)

        # 8. Cumulative intraday realized variance
        cum_rv = np.cumsum(log_ret ** 2)

        # 9. Session fraction (time-of-day encoding [0, 1])
        session_frac = np.arange(n_bars, dtype=np.float64) / max(n_bars - 1, 1)

        seq = pd.DataFrame(
            {
                "date": [day] * n_bars,
                "bar_idx": np.arange(n_bars),
                # V1 columns (backward compat)
                "buy_vol": buy,
                "sell_vol": sell,
                "net_flow": buy - sell,
                "vwap": mid,
                "n_trades": nt,
                # V2 columns (stationary)
                "log_ret": log_ret,
                "vol_share": vol_share,
                "buy_ratio": buy_ratio,
                "log_n_trades": log_n_trades,
                "abs_ret": abs_ret,
                # V3 columns (enriched)
                "price_accel": price_accel,
                "rolling_vpin": rolling_vpin,
                "cum_rv": cum_rv,
                "session_frac": session_frac,
            }
        )
        rows.append(seq)

    if not rows:
        cols = [
            "date", "bar_idx", "buy_vol", "sell_vol", "net_flow", "vwap",
            "n_trades", "log_ret", "vol_share", "buy_ratio", "log_n_trades",
            "abs_ret", "price_accel", "rolling_vpin", "cum_rv", "session_frac",
        ]
        return pd.DataFrame(columns=cols)

    return pd.concat(rows, ignore_index=True)


def _build_5min_sequences_df(
    bars_by_date: dict[date, pd.DataFrame],
) -> pd.DataFrame:
    """Aggregate 10-second bars into 5-minute bars with 12 enriched features.

    Parameters
    ----------
    bars_by_date : dict[date, pd.DataFrame]
        Same format as ``_build_sequences_df`` — each value has columns
        ``buy_vol``, ``sell_vol``, ``vwap``, ``n_trades``.

    Returns
    -------
    pd.DataFrame
        Columns: date, bar_idx, log_ret, abs_ret, vol_share, buy_ratio,
        order_flow_imbalance, rolling_vpin, cum_rv, session_frac,
        price_accel, log_n_trades, intrabar_rv, volume_surprise.
    """
    _5MIN_COLS = [
        "date", "bar_idx", "log_ret", "abs_ret", "vol_share", "buy_ratio",
        "order_flow_imbalance", "rolling_vpin", "cum_rv", "session_frac",
        "price_accel", "log_n_trades", "intrabar_rv", "volume_surprise",
    ]
    EPS = 1e-10
    GROUP_SIZE = 30
    VPIN_WINDOW = 10
    VOL_SURPRISE_WINDOW = 10

    rows: list[pd.DataFrame] = []

    for day in sorted(bars_by_date.keys()):
        bars = bars_by_date[day]
        n_bars_10s = len(bars)
        if n_bars_10s == 0:
            continue

        buy = bars["buy_vol"].values.astype(np.float64)
        sell = bars["sell_vol"].values.astype(np.float64)
        vwap = bars["vwap"].values.astype(np.float64)
        nt = bars["n_trades"].values.astype(np.float64) if "n_trades" in bars.columns else np.zeros(n_bars_10s)

        # 10s-level log returns (first bar = 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            log_ret_10s = np.log(vwap[1:] / vwap[:-1])
        log_ret_10s = np.concatenate([[0.0], log_ret_10s])
        log_ret_10s = np.nan_to_num(log_ret_10s, nan=0.0, posinf=0.0, neginf=0.0)

        # Number of 5-min bars (ceil division)
        n_5min = (n_bars_10s + GROUP_SIZE - 1) // GROUP_SIZE

        # Per-5-min-bar aggregates
        arr_log_ret = np.empty(n_5min)
        arr_intrabar_rv = np.empty(n_5min)
        arr_buy_sum = np.empty(n_5min)
        arr_sell_sum = np.empty(n_5min)
        arr_n_trades_sum = np.empty(n_5min)

        for i in range(n_5min):
            s = i * GROUP_SIZE
            e = min((i + 1) * GROUP_SIZE, n_bars_10s)

            # log_ret: log(last_vwap / first_vwap) for the 5-min bar
            first_vwap = vwap[s]
            last_vwap = vwap[e - 1]
            with np.errstate(divide="ignore", invalid="ignore"):
                lr = np.log(last_vwap / first_vwap)
            arr_log_ret[i] = 0.0 if (np.isnan(lr) or np.isinf(lr)) else lr

            # intrabar_rv: sum of 10s log_ret² within this group
            arr_intrabar_rv[i] = np.sum(log_ret_10s[s:e] ** 2)

            # volume sums
            arr_buy_sum[i] = buy[s:e].sum()
            arr_sell_sum[i] = sell[s:e].sum()
            arr_n_trades_sum[i] = nt[s:e].sum()

        # Derived features from aggregated arrays
        arr_abs_ret = np.abs(arr_log_ret)

        bar_vol = arr_buy_sum + arr_sell_sum
        daily_total_vol = bar_vol.sum()
        arr_vol_share = bar_vol / (daily_total_vol + EPS)

        arr_buy_ratio = arr_buy_sum / (arr_buy_sum + arr_sell_sum + EPS)

        arr_ofi = (arr_buy_sum - arr_sell_sum) / (arr_buy_sum + arr_sell_sum + EPS)

        # rolling_vpin on 5-min bars (window=10)
        imbalance = np.abs(arr_buy_sum - arr_sell_sum)
        cum_imbalance = np.cumsum(imbalance)
        cum_bar_total = np.cumsum(bar_vol)
        pad = np.zeros(VPIN_WINDOW, dtype=cum_imbalance.dtype)
        cim_pad = np.concatenate([pad, cum_imbalance])
        ctot_pad = np.concatenate([pad, cum_bar_total])
        num = cum_imbalance - cim_pad[:n_5min]
        den = cum_bar_total - ctot_pad[:n_5min]
        arr_rolling_vpin = num / (den + EPS)

        # cum_rv: cumsum of 5-min log_ret²
        arr_cum_rv = np.cumsum(arr_log_ret ** 2)

        # session_frac
        arr_session_frac = np.arange(n_5min, dtype=np.float64) / max(n_5min - 1, 1)

        # price_accel: diff(log_ret), first bar = 0
        arr_price_accel = np.diff(arr_log_ret, prepend=0.0)
        arr_price_accel[0] = 0.0

        # log_n_trades: detrended within day
        log_nt_5min = np.log1p(arr_n_trades_sum)
        arr_log_n_trades = log_nt_5min - np.median(log_nt_5min)

        # volume_surprise: bar_vol / rolling_mean(bar_vol, window=10)
        # Use expanding mean for first bars, then rolling window
        arr_volume_surprise = np.empty(n_5min)
        cum_vol = np.cumsum(bar_vol)
        for i in range(n_5min):
            if i < VOL_SURPRISE_WINDOW:
                # expanding mean: mean of bars 0..i
                mean_vol = cum_vol[i] / (i + 1)
            else:
                mean_vol = (cum_vol[i] - cum_vol[i - VOL_SURPRISE_WINDOW]) / VOL_SURPRISE_WINDOW
            arr_volume_surprise[i] = bar_vol[i] / (mean_vol + EPS)

        seq = pd.DataFrame(
            {
                "date": [day] * n_5min,
                "bar_idx": np.arange(n_5min),
                "log_ret": arr_log_ret,
                "abs_ret": arr_abs_ret,
                "vol_share": arr_vol_share,
                "buy_ratio": arr_buy_ratio,
                "order_flow_imbalance": arr_ofi,
                "rolling_vpin": arr_rolling_vpin,
                "cum_rv": arr_cum_rv,
                "session_frac": arr_session_frac,
                "price_accel": arr_price_accel,
                "log_n_trades": arr_log_n_trades,
                "intrabar_rv": arr_intrabar_rv,
                "volume_surprise": arr_volume_surprise,
            }
        )
        rows.append(seq)

    if not rows:
        return pd.DataFrame(columns=_5MIN_COLS)

    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------------------
# Cache I/O (atomic writes)
# ---------------------------------------------------------------------------


def save_micro_cache(
    symbol: str,
    df: pd.DataFrame,
    *,
    cache_dir: Path | None = None,
) -> Path:
    """Persist daily micro aggregates to parquet (atomic write).

    Merges new data with any existing cache — new rows take priority
    for overlapping dates. Never discards existing history.
    """
    if cache_dir is None:
        cache_dir = micro_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{symbol}.parquet"

    # Merge with existing cache (never discard old data)
    if target.exists():
        try:
            existing = pd.read_parquet(target)
            merged = pd.concat([existing, df])
            merged = merged[~merged.index.duplicated(keep="last")]
            merged = merged.sort_index()
            df = merged
        except Exception:  # noqa: BLE001
            logger.warning(
                "Could not read existing micro cache for %s, writing new data only",
                symbol,
            )

    fd, tmp_path = tempfile.mkstemp(suffix=".parquet", dir=cache_dir)
    try:
        os.close(fd)
        df.to_parquet(tmp_path, index=True)
        os.replace(tmp_path, target)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return target


def save_sequences_cache(
    symbol: str,
    df: pd.DataFrame,
    *,
    sequences_dir: Path | None = None,
    bar_interval: int = 10,
) -> Path:
    """Persist bar sequences to parquet (atomic write)."""
    if sequences_dir is None:
        sequences_dir = micro_sequences_dir().parent / "sequences_5min" if bar_interval == 300 else micro_sequences_dir()
    sequences_dir.mkdir(parents=True, exist_ok=True)
    target = sequences_dir / f"{symbol}.parquet"

    fd, tmp_path = tempfile.mkstemp(suffix=".parquet", dir=sequences_dir)
    try:
        os.close(fd)
        df.to_parquet(tmp_path, index=False)
        os.replace(tmp_path, target)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return target


def load_micro_cache(symbol: str, *, cache_dir: Path | None = None) -> pd.DataFrame | None:
    """Load cached daily micro aggregates (or None if missing)."""
    if cache_dir is None:
        cache_dir = micro_cache_dir()
    path = cache_dir / f"{symbol}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


def load_sequences_cache(symbol: str, *, sequences_dir: Path | None = None) -> pd.DataFrame | None:
    """Load cached 10s bar sequences (or None if missing)."""
    if sequences_dir is None:
        sequences_dir = micro_sequences_dir()
    path = sequences_dir / f"{symbol}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


def cache_covers_range(
    symbol: str,
    start_date: date,
    end_date: date,
    *,
    cache_dir: Path | None = None,
) -> bool:
    """Check if cached daily parquet covers the requested date range."""
    df = load_micro_cache(symbol, cache_dir=cache_dir)
    if df is None:
        return False
    if df.empty:
        return False

    idx = pd.DatetimeIndex(df.index)
    cached_start = idx.min().date()
    cached_end = idx.max().date()
    return cached_start <= start_date and cached_end >= end_date


def _get_cached_dates(
    symbol: str, *, sequences_dir: Path | None = None
) -> set[date]:
    """Return set of dates present in the existing sequences parquet.

    Sequences are the authoritative source for which dates have been
    ingested (daily aggregates can be recomputed from them).
    """
    if sequences_dir is None:
        sequences_dir = micro_sequences_dir()
    path = sequences_dir / f"{symbol}.parquet"
    if not path.exists():
        return set()
    try:
        df = pd.read_parquet(path, columns=["date"])
    except Exception:  # noqa: BLE001
        return set()
    dates_found: set[date] = set()
    for d in df["date"].unique():
        if isinstance(d, str):
            dates_found.add(date.fromisoformat(d))
        elif isinstance(d, date):
            dates_found.add(d)
        else:
            # numpy datetime64 or pd.Timestamp
            dates_found.add(pd.Timestamp(d).date())
    return dates_found


def detect_gaps(
    symbol: str,
    start_date: date,
    end_date: date,
    *,
    sequences_dir: Path | None = None,
) -> list[date]:
    """Return trading days missing from the sequences cache.

    Compares NYSE trading calendar against cached dates.
    Returns sorted list of missing dates (excludes holidays).
    """
    from volforecast.data.trading_calendar import get_trading_days

    trading_days = get_trading_days(start_date, end_date)
    cached = _get_cached_dates(symbol, sequences_dir=sequences_dir)
    missing = sorted(d for d in trading_days if d not in cached)
    return missing


def _format_date_ranges(dates: list[date]) -> str:
    """Format a list of dates as compact contiguous ranges for logging.

    Example: [Jan2, Jan3, Jan4, Jan8, Jan9] → "2024-01-02→2024-01-04, 2024-01-08→2024-01-09"
    """
    if not dates:
        return "(none)"
    sorted_dates = sorted(dates)
    ranges: list[str] = []
    range_start = sorted_dates[0]
    prev = sorted_dates[0]
    for d in sorted_dates[1:]:
        if (d - prev).days <= 3:  # Allow weekends within a "contiguous" range
            prev = d
        else:
            if range_start == prev:
                ranges.append(str(range_start))
            else:
                ranges.append(f"{range_start}\u2192{prev}")
            range_start = d
            prev = d
    # Final range
    if range_start == prev:
        ranges.append(str(range_start))
    else:
        ranges.append(f"{range_start}\u2192{prev}")
    return ", ".join(ranges)


# ---------------------------------------------------------------------------
# Staging I/O (incremental batch persistence for mid-symbol resume)
# ---------------------------------------------------------------------------


def _get_staged_dates(symbol: str) -> set[date]:
    """Return set of dates already written to staging for this symbol."""
    staging = micro_staging_dir(symbol)
    if not staging.exists():
        return set()
    dates_found: set[date] = set()
    for f in staging.iterdir():
        if f.suffix == ".parquet":
            try:
                df = pd.read_parquet(f, columns=["date"])
                for d in df["date"].unique():
                    if isinstance(d, str):
                        dates_found.add(date.fromisoformat(d))
                    else:
                        dates_found.add(d)
            except Exception:  # noqa: BLE001
                continue
    return dates_found


def _write_staging_batch(
    symbol: str,
    batch_bars: dict[date, pd.DataFrame],
) -> None:
    """Write a batch of bars to the staging directory as a parquet chunk."""
    if not batch_bars:
        return
    staging = micro_staging_dir(symbol)
    staging.mkdir(parents=True, exist_ok=True)

    seq_df = _build_sequences_df(batch_bars)
    if seq_df.empty:
        return

    # Filename encodes the date range for easy identification
    sorted_dates = sorted(batch_bars.keys())
    fname = f"{sorted_dates[0].isoformat()}_{sorted_dates[-1].isoformat()}.parquet"
    target = staging / fname

    fd, tmp_path = tempfile.mkstemp(suffix=".parquet", dir=staging)
    try:
        os.close(fd)
        seq_df.to_parquet(tmp_path, index=False)
        os.replace(tmp_path, target)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _consolidate_staging(symbol: str, *, sequences_dir: Path | None = None) -> pd.DataFrame:
    """Consolidate all staging parquets into the final sequences file.

    Merges staging chunks with any existing sequences parquet (preserving
    historical data), deduplicates, writes final parquet, then removes
    the staging directory.

    Returns the consolidated DataFrame (existing + new).
    """
    if sequences_dir is None:
        sequences_dir = micro_sequences_dir()
    staging = micro_staging_dir(symbol)

    if not staging.exists():
        return pd.DataFrame()

    chunks: list[pd.DataFrame] = []

    # Load existing sequences first (preserve historical data)
    existing_path = sequences_dir / f"{symbol}.parquet"
    if existing_path.exists():
        try:
            chunks.append(pd.read_parquet(existing_path))
        except Exception:  # noqa: BLE001
            logger.warning(f"{symbol}: could not read existing sequences, rebuilding from staging only")

    # Then load staging chunks
    for f in sorted(staging.iterdir()):
        if f.suffix == ".parquet":
            try:
                chunks.append(pd.read_parquet(f))
            except Exception:  # noqa: BLE001
                logger.warning(f"{symbol}: corrupt staging file {f.name}, skipping")

    if not chunks:
        return pd.DataFrame()

    seq_df = pd.concat(chunks, ignore_index=True)

    # Deduplicate by (date, bar_idx) — staging (last) wins over existing
    seq_df = seq_df.drop_duplicates(subset=["date", "bar_idx"], keep="last")
    seq_df = seq_df.sort_values(["date", "bar_idx"]).reset_index(drop=True)

    # Write final sequences parquet
    save_sequences_cache(symbol, seq_df, sequences_dir=sequences_dir)

    # Clean up staging directory
    import shutil

    shutil.rmtree(staging, ignore_errors=True)

    return seq_df


# ---------------------------------------------------------------------------
# Orchestrator: ingest one symbol
# ---------------------------------------------------------------------------


def ingest_symbol_micro(
    symbol: str,
    start_date: date,
    end_date: date,
    *,
    force: bool = False,
    recompute: bool = False,
    fill_gaps: bool = False,
    batch_size: int = 20,
    bucket_volume: int | None = None,
    cache_dir: Path | None = None,
    sequences_dir: Path | None = None,
    progress=None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch tick data with LeeReady, compute daily micro + sequences for one symbol.

    Parameters
    ----------
    symbol : str
        Ticker symbol (must be in SYMBOL_UNIVERSE).
    start_date, end_date : date
        Inclusive date range.
    force : bool
        Re-fetch even if cache covers the date range.
    recompute : bool
        Re-derive dailies from cached sequences (no network).
    fill_gaps : bool
        If True, also fetch missing dates within the existing cached range.
        If False (default), only fetch dates after the latest cached date
        (forward extension).
    batch_size : int
        Trading days per API call.
    bucket_volume : int, optional
        VPIN bucket volume. If None, auto-calibrate from data.
    cache_dir : Path, optional
        Override daily cache directory.
    sequences_dir : Path, optional
        Override sequences directory.
    progress : optional
        Progress display handle.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (daily_df, sequences_df). Empty DataFrames if no data.
    """
    if cache_dir is None:
        cache_dir = micro_cache_dir()
    if sequences_dir is None:
        sequences_dir = micro_sequences_dir()

    cache_dir.mkdir(parents=True, exist_ok=True)
    sequences_dir.mkdir(parents=True, exist_ok=True)

    # Recompute path: re-derive dailies AND rebuild sequences from cached bars
    if recompute:
        seq_df = load_sequences_cache(symbol, sequences_dir=sequences_dir)
        if seq_df is None or seq_df.empty:
            logger.warning(f"{symbol}: no cached sequences for recompute")
            return pd.DataFrame(columns=MICRO_DAILY_COLUMNS), pd.DataFrame()

        # Reconstruct bars_by_date from sequences
        bars_by_date: dict[date, pd.DataFrame] = {}
        for day, grp in seq_df.groupby("date"):
            if isinstance(day, str):
                day = date.fromisoformat(day)
            cols = ["buy_vol", "sell_vol", "vwap", "n_trades"]
            bars_by_date[day] = grp[cols].reset_index(drop=True)

        # Rebuild sequences with current schema (picks up new derived features)
        seq_df = _build_sequences_df(bars_by_date)
        save_sequences_cache(symbol, seq_df, sequences_dir=sequences_dir)

        # Auto-calibrate bucket volume
        if bucket_volume is None:
            bucket_volume = _auto_bucket_volume(bars_by_date)

        daily_df = compute_daily_micro(bars_by_date, bucket_volume)
        save_micro_cache(symbol, daily_df, cache_dir=cache_dir)
        return daily_df, seq_df

    # Normal fetch path
    from volforecast.data.trading_calendar import get_trading_days

    trading_days = get_trading_days(start_date, end_date)
    if not trading_days:
        return pd.DataFrame(columns=MICRO_DAILY_COLUMNS), pd.DataFrame()

    # Date-level delta: determine which dates actually need fetching
    staged_dates = _get_staged_dates(symbol)
    if force:
        remaining_days = trading_days
    else:
        cached_dates = _get_cached_dates(symbol, sequences_dir=sequences_dir)
        already_have = cached_dates | staged_dates
        all_missing = [d for d in trading_days if d not in already_have]

        # Default: forward-extension only (dates after max cached/staged date)
        # --fill-gaps: also fetch missing dates within the existing range
        if all_missing and not fill_gaps and (cached_dates or staged_dates):
            max_cached = max(cached_dates | staged_dates)
            remaining_days = [d for d in all_missing if d > max_cached]
            n_gaps = len(all_missing) - len(remaining_days)
            if n_gaps > 0:
                logger.info(
                    f"{symbol}: {n_gaps} historical gaps ignored "
                    f"(use --fill-gaps to fetch them)"
                )
        else:
            remaining_days = all_missing

        # Log skip/fetch information
        n_cached = len(cached_dates & set(trading_days))
        n_staged = len(staged_dates & set(trading_days))
        n_missing = len(remaining_days)

        if n_cached > 0 and n_missing > 0:
            logger.info(
                f"{symbol}: {n_cached} days cached, "
                f"fetching {n_missing} missing days "
                f"({_format_date_ranges(remaining_days)})"
            )
        elif n_cached > 0 and n_missing == 0:
            logger.info(
                f"{symbol}: all {n_cached} days cached "
                f"({trading_days[0]}→{trading_days[-1]}), skipping"
            )
        elif n_staged > 0 and n_missing > 0:
            logger.info(
                f"{symbol}: resuming — {n_staged} days staged, "
                f"{n_missing} remaining ({_format_date_ranges(remaining_days)})"
            )

    # Staging callback: persist each batch incrementally
    def _on_batch(batch_bars: dict[date, pd.DataFrame]) -> None:
        _write_staging_batch(symbol, batch_bars)

    # Fetch only the remaining days
    if remaining_days:
        bars_by_date = fetch_micro_bars(
            symbol,
            remaining_days,
            batch_size=batch_size,
            on_batch=_on_batch,
            progress=progress,
        )
    else:
        bars_by_date = {}

    # Consolidate staging files (merges with existing sequences)
    seq_df = _consolidate_staging(symbol, sequences_dir=sequences_dir)

    # Fallback: if staging was bypassed (e.g. mocked fetch), merge with existing
    if seq_df.empty and bars_by_date:
        new_seq_df = _build_sequences_df(bars_by_date)
        if not new_seq_df.empty:
            # Merge with existing sequences if present
            existing = load_sequences_cache(symbol, sequences_dir=sequences_dir)
            if existing is not None and not existing.empty:
                seq_df = pd.concat([existing, new_seq_df], ignore_index=True)
                seq_df = seq_df.drop_duplicates(subset=["date", "bar_idx"], keep="last")
                seq_df = seq_df.sort_values(["date", "bar_idx"]).reset_index(drop=True)
            else:
                seq_df = new_seq_df
            save_sequences_cache(symbol, seq_df, sequences_dir=sequences_dir)
    elif seq_df.empty and not bars_by_date:
        # No new data fetched and no staging — try loading existing sequences
        existing = load_sequences_cache(symbol, sequences_dir=sequences_dir)
        if existing is not None and not existing.empty:
            seq_df = existing
        else:
            return pd.DataFrame(columns=MICRO_DAILY_COLUMNS), pd.DataFrame()

    # Reconstruct full bars_by_date from consolidated sequences for daily computation
    all_bars_by_date: dict[date, pd.DataFrame] = {}
    if not seq_df.empty:
        for day, grp in seq_df.groupby("date"):
            if isinstance(day, str):
                day = date.fromisoformat(day)
            cols = ["buy_vol", "sell_vol", "vwap", "n_trades"]
            available = [c for c in cols if c in grp.columns]
            all_bars_by_date[day] = grp[available].reset_index(drop=True)
    else:
        all_bars_by_date = bars_by_date

    if not all_bars_by_date:
        return pd.DataFrame(columns=MICRO_DAILY_COLUMNS), pd.DataFrame()

    # Auto-calibrate bucket volume from fetched data
    if bucket_volume is None:
        bucket_volume = _auto_bucket_volume(all_bars_by_date)

    # Compute daily aggregates
    daily_df = compute_daily_micro(all_bars_by_date, bucket_volume)

    # Save daily output
    if not daily_df.empty:
        save_micro_cache(symbol, daily_df, cache_dir=cache_dir)

    return daily_df, seq_df


def _auto_bucket_volume(bars_by_date: dict[date, pd.DataFrame]) -> int:
    """Auto-calibrate VPIN bucket volume from data.

    Strategy: median daily volume / VPIN_N_BUCKETS.
    This ensures ~50 buckets per typical day.
    """
    daily_vols = []
    for bars in bars_by_date.values():
        total = bars["buy_vol"].sum() + bars["sell_vol"].sum()
        if total > 0:
            daily_vols.append(total)

    if not daily_vols:
        return 10000  # fallback

    median_vol = float(np.median(daily_vols))
    bucket_vol = max(1, int(median_vol / VPIN_N_BUCKETS))
    return bucket_vol
