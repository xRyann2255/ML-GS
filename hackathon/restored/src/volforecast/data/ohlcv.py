"""Per-symbol OHLCV ingestion from TSDB eqpad_ namespace.

Fetches split-adjusted daily OHLCV for each symbol and stores per-symbol
parquets in data/raw/ohlcv/.

Public API:
    fetch_ohlcv         — Fetch adjusted OHLCV for a single symbol
    save_ohlcv_cache    — Persist per-symbol OHLCV DataFrame to parquet
    load_ohlcv_cache    — Load cached per-symbol OHLCV (or None if missing)
    cache_covers_range  — Check if cached data covers requested date range

Adjustment convention:
    TSDB only provides adjusted close (close.adj.allincdiv). We derive
    adjusted open/high/low by applying the same corporate-action factor:
        adj_price = raw_price * (adj_close / raw_close)
    Volume is always unadjusted.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from volforecast.constants import FUTURES_SYMBOLS, TICKER_TO_RIC
from volforecast.utils.paths import ohlcv_cache_path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_tsdb_data(symbol: str, start: str, end: str) -> pd.Series:
    """Fetch a single TSDB symbol series. Delegates to tsdb module."""
    from volforecast.data.tsdb import _get_tsdb_data as _tsdb_fetch

    return _tsdb_fetch(symbol, start, end)


def _tsdb_symbol(ric: str, field: str, adjusted: bool = False) -> str:
    """Build a TSDB symbol string from a RIC and field name."""
    from volforecast.data.tsdb import _tsdb_symbol as _build_sym

    return _build_sym(ric, field, adjusted)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_ohlcv(
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch split-adjusted daily OHLCV from TSDB for a single symbol.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g., 'AAPL', 'SPY'). Futures (ES) not supported.
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).

    Returns
    -------
    pd.DataFrame
        DatetimeIndex ('date') with columns: open, high, low, close, volume.
        Prices are split-adjusted. Volume is unadjusted.

    Raises
    ------
    ValueError
        If symbol is a futures symbol or has no RIC mapping.
    ConnectionError
        If TSDB is unavailable.
    """
    if symbol in FUTURES_SYMBOLS:
        raise ValueError(
            f"No RIC mapping for futures symbol '{symbol}'. "
            "OHLCV ingestion only supports equities and ETFs."
        )
    if symbol not in TICKER_TO_RIC:
        raise ValueError(
            f"No RIC mapping for '{symbol}'. Valid symbols: {sorted(TICKER_TO_RIC.keys())}"
        )

    ric = TICKER_TO_RIC[symbol]
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    # Fetch raw prices (unadjusted) for open, high, low, close
    raw_open = _get_tsdb_data(_tsdb_symbol(ric, "open", adjusted=False), start_str, end_str)
    raw_high = _get_tsdb_data(_tsdb_symbol(ric, "high", adjusted=False), start_str, end_str)
    raw_low = _get_tsdb_data(_tsdb_symbol(ric, "low", adjusted=False), start_str, end_str)
    raw_close = _get_tsdb_data(_tsdb_symbol(ric, "close", adjusted=False), start_str, end_str)

    # Fetch adjusted close (the only adjusted field TSDB provides)
    adj_close = _get_tsdb_data(_tsdb_symbol(ric, "close", adjusted=True), start_str, end_str)

    # Fetch volume (always unadjusted)
    volume = _get_tsdb_data(_tsdb_symbol(ric, "volume", adjusted=False), start_str, end_str)

    # Handle empty response
    if adj_close.empty:
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
            index=pd.DatetimeIndex([], name="date"),
        )

    # Compute adjustment factor: adj_close / raw_close
    # This handles stock splits, reverse splits, etc.
    adj_factor = adj_close / raw_close

    # Apply factor to derive adjusted open/high/low
    adj_open = raw_open * adj_factor
    adj_high = raw_high * adj_factor
    adj_low = raw_low * adj_factor

    df = pd.DataFrame(
        {
            "open": adj_open,
            "high": adj_high,
            "low": adj_low,
            "close": adj_close,
            "volume": volume,
        }
    )
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"

    return df


def save_ohlcv_cache(symbol: str, df: pd.DataFrame) -> Path:
    """Persist per-symbol OHLCV DataFrame to parquet (atomic write).

    Merges new data with any existing cache — new rows take priority
    for overlapping dates. Never discards existing history.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    df : pd.DataFrame
        OHLCV DataFrame with DatetimeIndex.

    Returns
    -------
    Path
        Path to the written parquet file.
    """
    path = ohlcv_cache_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing cache (never discard old data)
    if path.exists():
        try:
            existing = pd.read_parquet(path)
            merged = pd.concat([existing, df])
            merged = merged[~merged.index.duplicated(keep="last")]
            merged = merged.sort_index()
            df = merged
        except Exception:  # noqa: BLE001
            logger.warning(
                "Could not read existing OHLCV cache for %s, writing new data only",
                symbol,
            )

    # Atomic write: write to temp file then rename
    fd, tmp = tempfile.mkstemp(suffix=".parquet", dir=str(path.parent))
    try:
        os.close(fd)
        df.to_parquet(tmp)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    return path


def load_ohlcv_cache(symbol: str) -> pd.DataFrame | None:
    """Load cached per-symbol OHLCV, or return None if missing.

    Parameters
    ----------
    symbol : str
        Ticker symbol.

    Returns
    -------
    pd.DataFrame or None
        OHLCV DataFrame if cache exists, None otherwise.
    """
    path = ohlcv_cache_path(symbol)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def cache_covers_range(symbol: str, start: date, end: date) -> bool:
    """Check whether the cached OHLCV data covers the requested date range.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    start : date
        Requested start date.
    end : date
        Requested end date.

    Returns
    -------
    bool
        True if cache exists and covers [start, end], False otherwise.
    """
    df = load_ohlcv_cache(symbol)
    if df is None or df.empty:
        return False
    cached_start = df.index.min().date()
    cached_end = df.index.max().date()
    return cached_start <= start and cached_end >= end
