"""NYSE-calendar-aware interior gap detection for cached parquet files.

Compares a cached parquet's date index against the expected NYSE trading
calendar to find actual missing trading days (not holidays or weekends).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from volforecast.data.trading_calendar import get_trading_days

# Source name → subdirectory under data/raw/
_SOURCE_DIRS: dict[str, str] = {
    "ticks": "data/raw/ticks",
    "iv": "data/raw/iv",
    "ohlcv": "data/raw/ohlcv",
    "microstructure": "data/raw/micro",
    "cross_asset": "data/raw/cross_asset",
    "correlation": "data/raw/correlation",
}


def detect_gaps(
    source: str,
    symbol: str,
    start_date: date,
    end_date: date,
    *,
    project_root: Path | None = None,
) -> list[date]:
    """Detect missing trading days in a cached parquet file.

    Compares the parquet's date index against the NYSE trading calendar
    to find interior gaps (days that should have data but don't).

    Parameters
    ----------
    source : str
        Source name (e.g., "ohlcv", "iv", "ticks", "cross_asset").
    symbol : str
        Symbol name (e.g., "AAPL") or group name for cross_asset (e.g., "rates").
    start_date : date
        Start of the expected date range.
    end_date : date
        End of the expected date range.
    project_root : Path, optional
        Project root directory. Resolved automatically if not provided.

    Returns
    -------
    list[date]
        Sorted list of missing trading days.
    """
    if project_root is None:
        from volforecast.utils.paths import resolve_project_root

        project_root = resolve_project_root()

    # Resolve parquet path
    subdir = _SOURCE_DIRS.get(source)
    if subdir is None:
        raise ValueError(f"Unknown source: {source!r}. Valid: {list(_SOURCE_DIRS)}")

    parquet_path = project_root / subdir / f"{symbol}.parquet"

    # Expected trading days
    expected = set(get_trading_days(start_date, end_date))

    if not parquet_path.exists():
        return sorted(expected)

    # Load index from cached parquet
    df = pd.read_parquet(parquet_path, columns=[])  # metadata only — just the index
    cached_dates = _extract_dates(df.index)

    missing = sorted(expected - cached_dates)
    return missing


def _extract_dates(index: pd.Index) -> set[date]:
    """Extract date objects from a parquet index (handles DatetimeIndex or date Index)."""
    if isinstance(index, pd.DatetimeIndex):
        return {ts.date() for ts in index}
    # Plain date objects or strings
    result: set[date] = set()
    for val in index:
        if isinstance(val, date):
            result.add(val)
        elif hasattr(val, "date"):
            result.add(val.date())
        else:
            # Try parsing string
            result.add(pd.Timestamp(val).date())
    return result


def coalesce_dates(days: list[date]) -> list[tuple[date, date]]:
    """Merge a sorted list of dates into contiguous ranges for efficient fetching.

    Two consecutive dates are merged if they are ≤ 3 calendar days apart
    (to account for weekends between Friday and Monday).

    Parameters
    ----------
    days : list[date]
        Sorted list of trading days to coalesce.

    Returns
    -------
    list[tuple[date, date]]
        List of (start, end) date ranges.
    """
    if not days:
        return []

    days = sorted(days)
    ranges: list[tuple[date, date]] = []
    range_start = days[0]
    range_end = days[0]

    for i in range(1, len(days)):
        gap = (days[i] - range_end).days
        if gap <= 3:
            # Merge: within normal weekend gap
            range_end = days[i]
        else:
            # New range
            ranges.append((range_start, range_end))
            range_start = days[i]
            range_end = days[i]

    ranges.append((range_start, range_end))
    return ranges
