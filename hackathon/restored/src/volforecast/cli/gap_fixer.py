"""Source-specific gap filling — fetches missing days and merges into cache.

Each source has a dedicated fetch function wrapper. The fix_gaps() orchestrator
coalesces missing days into ranges, fetches them, and atomically merges with
the existing cache.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from volforecast.cli.gap_detector import _SOURCE_DIRS, coalesce_dates

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of a gap-fill operation."""

    source: str
    symbol: str
    days_planned: int
    days_filled: int = 0
    days_failed: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False


def fix_gaps(
    source: str,
    symbol: str,
    missing_days: list[date],
    *,
    dry_run: bool = False,
    project_root: Path | None = None,
) -> FixResult:
    """Fill interior gaps for a given source/symbol.

    Parameters
    ----------
    source : str
        Source name (e.g., "ohlcv", "iv", "ticks", "cross_asset").
    symbol : str
        Symbol name or group name for cross_asset.
    missing_days : list[date]
        Sorted list of missing trading days to fill.
    dry_run : bool
        If True, report what would be done without fetching.
    project_root : Path, optional
        Project root. Resolved automatically if not provided.

    Returns
    -------
    FixResult
        Summary of the fix operation.
    """
    if project_root is None:
        from volforecast.utils.paths import resolve_project_root

        project_root = resolve_project_root()

    result = FixResult(
        source=source,
        symbol=symbol,
        days_planned=len(missing_days),
        dry_run=dry_run,
    )

    if not missing_days:
        return result

    if dry_run:
        return result

    # Coalesce into ranges for efficient fetching
    ranges = coalesce_dates(missing_days)

    # Resolve parquet path
    subdir = _SOURCE_DIRS.get(source)
    if subdir is None:
        result.errors.append(f"Unknown source: {source!r}")
        result.days_failed = len(missing_days)
        return result

    parquet_path = project_root / subdir / f"{symbol}.parquet"

    # Load existing cache (may not exist)
    existing_df: pd.DataFrame | None = None
    if parquet_path.exists():
        existing_df = pd.read_parquet(parquet_path)

    # Fetch each range and collect new data
    fetched_frames: list[pd.DataFrame] = []
    for range_start, range_end in ranges:
        try:
            new_df = _dispatch_fetch(source, symbol, range_start, range_end)
            if new_df is not None and not new_df.empty:
                fetched_frames.append(new_df)
                result.days_filled += len(new_df)
        except Exception as e:
            err_msg = f"{source}/{symbol} [{range_start} to {range_end}]: {e}"
            result.errors.append(err_msg)
            logger.warning("Gap-fill failed: %s", err_msg)

    if not fetched_frames:
        result.days_failed = len(missing_days) - result.days_filled
        return result

    # Merge: existing + all fetched chunks
    frames = [existing_df] if existing_df is not None else []
    frames.extend(fetched_frames)
    merged = pd.concat(frames).sort_index()
    # Drop duplicate index entries (keep last to prefer fresh data)
    merged = merged[~merged.index.duplicated(keep="last")]

    # Atomic write: write to .tmp then rename
    tmp_path = parquet_path.with_suffix(".parquet.tmp")
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(tmp_path)
    os.replace(tmp_path, parquet_path)

    result.days_failed = len(missing_days) - result.days_filled
    return result


def _dispatch_fetch(source: str, symbol: str, start: date, end: date) -> pd.DataFrame | None:
    """Route fetch to the appropriate source-specific function."""
    if source == "ohlcv":
        return _fetch_ohlcv_range(symbol, start, end)
    elif source == "iv":
        return _fetch_iv_range(symbol, start, end)
    elif source == "ticks":
        return _fetch_ticks_range(symbol, start, end)
    elif source == "microstructure":
        return _fetch_micro_range(symbol, start, end)
    elif source == "cross_asset":
        return _fetch_cross_asset_range(symbol, start, end)
    else:
        raise ValueError(f"No fetch dispatcher for source: {source!r}")


def _fetch_ohlcv_range(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Fetch OHLCV data for a date range."""
    from volforecast.data.ohlcv import fetch_ohlcv

    return fetch_ohlcv(symbol, start, end)


def _fetch_iv_range(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Fetch IV/EDRVOL data for a date range."""
    from volforecast.data.edrvol import fetch_edrvol

    return fetch_edrvol(symbol, start, end)


def _fetch_ticks_range(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Fetch tick-based RV data for a date range."""
    from volforecast.data.trading_calendar import get_trading_days

    days = get_trading_days(start, end)
    if not days:
        return pd.DataFrame()

    from volforecast.data.micro import fetch_micro_bars

    # fetch_micro_bars returns dict[date, DataFrame] of intraday bars
    # We need the RV panel computation, which is in rv_panel
    from volforecast.data.rv_panel import compute_rv_from_bars

    bars = fetch_micro_bars(symbol, days)
    return compute_rv_from_bars(bars, symbol)


def _fetch_micro_range(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Fetch microstructure aggregates for a date range."""
    from volforecast.data.trading_calendar import get_trading_days

    days = get_trading_days(start, end)
    if not days:
        return pd.DataFrame()

    from volforecast.data.micro import fetch_micro_bars

    bars = fetch_micro_bars(symbol, days)
    # Aggregate bars into daily microstructure features
    from volforecast.data.micro import compute_daily_micro

    return compute_daily_micro(bars)


def _fetch_cross_asset_range(group: str, start: date, end: date) -> pd.DataFrame:
    """Fetch cross-asset data for a group (rates, fx_vol, credit, commodity)."""
    from volforecast.data.cross_asset_ingest import (
        ingest_commodity,
        ingest_credit,
        ingest_fx_vol,
        ingest_rates,
    )

    dispatch = {
        "rates": ingest_rates,
        "fx_vol": ingest_fx_vol,
        "credit": ingest_credit,
        "commodity": ingest_commodity,
    }

    fn = dispatch.get(group)
    if fn is None:
        raise ValueError(f"Unknown cross_asset group: {group!r}. Valid: {list(dispatch)}")

    # These functions write directly to disk with force=True
    result = fn(start, end, force=True)
    # Re-read the written file to get the new data for the range
    if result.outpath and result.outpath.exists():
        df = pd.read_parquet(result.outpath)
        # Filter to just the requested range
        mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
        return df[mask]
    return pd.DataFrame()
