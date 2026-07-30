"""IV surface data from Marquee EDRVOL_PERCENT.

.. deprecated::
    This module is superseded by ``volforecast.data.edrvol`` which fetches
    per-symbol IV from TSDB edrvol_ namespace. Retained for backward
    compatibility only. Use ``vol ingest-edrvol`` for new ingestion.

Provides functions to fetch SPX implied volatility surface data
used for computing options-implied features (Layer 2):
ATM IV, VRP, skew, term structure slope, butterfly, VVIX.

Uses gs_quant Dataset API. Requires GsSession to be active.
Queries are chunked by month to avoid API rate limits on large date ranges.

Key functions:
    fetch_iv_surface — Fetch full IV surface grid (strike x tenor)
    fetch_atm_iv     — Fetch ATM implied volatility term structure
    fetch_skew       — Fetch 25-delta risk reversal (skew)
    fetch_vvix       — Fetch VVIX (vol-of-vol index) from TSDB
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta

try:
    from gs_quant.data import Dataset
    from gs_quant.errors import MqUninitialisedError
    from gs_quant.session import GsSession

    _HAS_GS_QUANT = True
    _GS_SESSION_ERRORS = (MqUninitialisedError,)
except ImportError:
    _HAS_GS_QUANT = False
    _GS_SESSION_ERRORS = ()

# Also need TSDB for VVIX
try:
    from gs_quant_internal.tsdb import TSDBSymbol  # noqa: F401

    _HAS_TSDB = True
except ImportError:
    _HAS_TSDB = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATASET_ID = "EDRVOL_PERCENT"
_DEFAULT_TENORS = ["1m", "2m", "3m", "6m", "1y"]
_DEFAULT_SKEW_TENORS = ["1m", "3m"]
_ATM_STRIKE = 1.0  # relativeStrike = 1.0, strikeReference = "forward"
_ATM_STRIKE_REF = "forward"  # Use forward strike reference for ATM
_SKEW_PUT_STRIKE = 0.75  # 25-delta put (call-delta: 75-delta call ≈ 25-delta put)
_SKEW_CALL_STRIKE = 0.25  # 25-delta call (call-delta convention)
_SKEW_STRIKES = (_SKEW_PUT_STRIKE, _SKEW_CALL_STRIKE)
_MAX_CHUNK_MONTHS = 3  # Safe with server-side filtering (~6 rows/day)
_MAX_WORKERS = 6  # Concurrent Marquee requests
_MAX_RETRIES = 3  # Retry attempts per chunk on transient failure
_RETRY_BACKOFF = (1.0, 2.0, 4.0)  # Seconds between retries

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_session() -> None:
    """Ensure GsSession is active; initialize on first use if needed."""
    if not _HAS_GS_QUANT:
        raise ConnectionError("gs_quant not available. Run on GS desktop with active session.")
    try:
        _ = GsSession.current
    except _GS_SESSION_ERRORS:
        try:
            GsSession.use()
        except Exception as exc:  # noqa: BLE001
            raise ConnectionError("Marquee unavailable: could not initialize GsSession.") from exc


def _query_erdvol(
    start_date: date,
    end_date: date,
    on_chunk: object = None,
    max_workers: int = _MAX_WORKERS,
    **kwargs: object,
) -> pd.DataFrame:
    """Query EDRVOL_PERCENT dataset for SPX, chunked and parallelized.

    Chunks by quarter (3 months) and fetches concurrently using a thread pool.
    Each chunk is retried up to 3 times with exponential backoff on failure.

    Parameters
    ----------
    on_chunk : callable, optional
        Called with (chunks_done: int, total_chunks: int) after each chunk.
    max_workers : int
        Max concurrent API requests (default: 6).
    """
    _ensure_session()
    ds = Dataset(_DATASET_ID)

    # Short ranges (<=chunk size) go in a single request
    delta = relativedelta(end_date, start_date)
    total_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
    if total_months <= _MAX_CHUNK_MONTHS:
        result = _fetch_chunk_with_retry(ds, start_date, end_date, **kwargs)
        if on_chunk:
            on_chunk(1, 1)
        return result if result is not None else pd.DataFrame()

    # Build chunk date ranges
    chunk_ranges: list[tuple[date, date]] = []
    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(
            chunk_start + relativedelta(months=_MAX_CHUNK_MONTHS) - relativedelta(days=1),
            end_date,
        )
        chunk_ranges.append((chunk_start, chunk_end))
        chunk_start = chunk_end + relativedelta(days=1)

    total_chunks = len(chunk_ranges)

    # Fetch chunks in parallel
    results: dict[int, pd.DataFrame] = {}
    done_count = 0

    with ThreadPoolExecutor(max_workers=min(max_workers, total_chunks)) as executor:
        futures = {
            executor.submit(_fetch_chunk_with_retry, ds, cs, ce, **kwargs): idx
            for idx, (cs, ce) in enumerate(chunk_ranges)
        }
        for future in as_completed(futures):
            idx = futures[future]
            chunk = future.result()
            if chunk is not None and not chunk.empty:
                results[idx] = chunk
            done_count += 1
            if on_chunk:
                on_chunk(done_count, total_chunks)

    if not results:
        return pd.DataFrame()

    # Reassemble in date order
    ordered = [results[i] for i in sorted(results.keys())]
    return pd.concat(ordered)


def _fetch_chunk_with_retry(
    ds: object,
    start: date,
    end: date,
    **kwargs: object,
) -> pd.DataFrame | None:
    """Fetch a single chunk with exponential backoff retry on failure.

    Re-ensures GsSession in each worker thread since session context
    is not inherited by ThreadPoolExecutor threads.
    """
    _ensure_session()
    for attempt in range(_MAX_RETRIES):
        try:
            chunk = ds.get_data(start=start, end=end, bbid="SPX", **kwargs)
            if chunk is not None and not chunk.empty:
                return chunk
            return None
        except Exception:  # noqa: BLE001
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF[attempt])
                logger.debug(
                    "Retry %d/%d for chunk %s to %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    start,
                    end,
                )
            else:
                logger.warning(
                    "Failed to fetch chunk %s to %s after %d attempts",
                    start,
                    end,
                    _MAX_RETRIES,
                )
                return None
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_iv_surface(
    start_date: date,
    end_date: date,
    tenors: Sequence[str] | None = None,
    strikes: Sequence[float] | None = None,
) -> pd.DataFrame:
    """Fetch SPX IV surface from Marquee EDRVOL_PERCENT.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    tenors : Sequence[str], optional
        Tenor labels (e.g., ['1m', '3m', '6m', '1y']).
        If None, fetch all available tenors.
    strikes : Sequence[float], optional
        Moneyness strikes (e.g., [0.9, 0.95, 1.0, 1.05, 1.1]).
        If None, fetch all available strikes.

    Returns
    -------
    pd.DataFrame
        MultiIndex (date, tenor) with columns for each strike level.

    Raises
    ------
    ConnectionError
        If Marquee API is unreachable.
    """
    raw = _query_erdvol(start_date, end_date)

    if raw.empty:
        return pd.DataFrame()

    # Filter by tenors if specified
    if tenors is not None and "tenor" in raw.columns:
        raw = raw[raw["tenor"].isin(tenors)]

    # Filter by strikes if specified
    if strikes is not None and "relativeStrike" in raw.columns:
        raw = raw[raw["relativeStrike"].isin(strikes)]

    # Pivot: index=(date, tenor), columns=relativeStrike, values=impliedVolatility
    if "tenor" in raw.columns and "relativeStrike" in raw.columns:
        pivot = raw.pivot_table(
            index=[raw.index, "tenor"],
            columns="relativeStrike",
            values="impliedVolatility",
            aggfunc="first",
        )
        pivot.index.names = ["date", "tenor"]
        return pivot

    return raw


def fetch_atm_iv(
    start_date: date,
    end_date: date,
    tenors: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch ATM implied volatility term structure.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    tenors : Sequence[str], optional
        Tenor labels (default: ['1m', '2m', '3m', '6m', '1y']).

    Returns
    -------
    pd.DataFrame
        Index: DatetimeIndex. Columns: tenor labels with ATM IV values.
    """
    if tenors is None:
        tenors = list(_DEFAULT_TENORS)

    raw = _query_erdvol(start_date, end_date)

    if raw.empty:
        return pd.DataFrame(columns=tenors)

    # Filter to ATM strike and requested tenors
    mask = pd.Series(True, index=raw.index)
    if "relativeStrike" in raw.columns:
        mask &= raw["relativeStrike"] == _ATM_STRIKE
    if "tenor" in raw.columns:
        mask &= raw["tenor"].isin(tenors)

    filtered = raw[mask]

    if filtered.empty:
        return pd.DataFrame(columns=tenors)

    # Pivot: index=date, columns=tenor
    pivot = filtered.pivot_table(
        index=filtered.index,
        columns="tenor",
        values="impliedVolatility",
        aggfunc="first",
    )
    pivot.index = pd.DatetimeIndex(pivot.index)
    pivot.index.name = "date"

    # Reorder columns to match requested tenors
    present = [t for t in tenors if t in pivot.columns]
    return pivot[present]


def fetch_skew(
    start_date: date,
    end_date: date,
    tenors: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch 25-delta risk reversal (skew) for SPX.

    Skew = IV(25d put) - IV(25d call) = IV(delta=0.75) - IV(delta=0.25).
    Uses call-delta convention where delta=0.75 ≈ 25-delta put.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    tenors : Sequence[str], optional
        Tenor labels (default: ['1m', '3m']).

    Returns
    -------
    pd.DataFrame
        Index: DatetimeIndex. Columns: tenor labels with skew values.
    """
    if tenors is None:
        tenors = list(_DEFAULT_SKEW_TENORS)

    raw = _query_erdvol(start_date, end_date)

    if raw.empty:
        return pd.DataFrame(columns=tenors)

    # Filter to the two strike levels used for skew
    put_strike, call_strike = _SKEW_STRIKES
    mask_tenor = raw["tenor"].isin(tenors) if "tenor" in raw.columns else True

    put_mask = mask_tenor & (raw["relativeStrike"] == put_strike)
    call_mask = mask_tenor & (raw["relativeStrike"] == call_strike)

    put_df = raw[put_mask].pivot_table(
        index=raw[put_mask].index,
        columns="tenor",
        values="impliedVolatility",
        aggfunc="first",
    )
    call_df = raw[call_mask].pivot_table(
        index=raw[call_mask].index,
        columns="tenor",
        values="impliedVolatility",
        aggfunc="first",
    )

    # Align indices and compute skew = put IV - call IV
    put_df, call_df = put_df.align(call_df, join="inner")
    skew = put_df - call_df
    skew.index = pd.DatetimeIndex(skew.index)
    skew.index.name = "date"

    present = [t for t in tenors if t in skew.columns]
    return skew[present]


def fetch_vvix(
    start_date: date,
    end_date: date,
) -> pd.Series:
    """Fetch VVIX (vol-of-vol index) time series from TSDB.

    VVIX measures the implied volatility of VIX options — it is
    fetched from TSDB, not Marquee.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).

    Returns
    -------
    pd.Series
        Index: DatetimeIndex (name='date'). Values: VVIX level.
    """
    if not _HAS_TSDB:
        raise ConnectionError("gs_quant_internal not available. Run on GS desktop.")
    series = _get_vvix_tsdb_data(start_date.isoformat(), end_date.isoformat())
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    series.name = "vvix"
    return series


def _get_vvix_tsdb_data(start: str, end: str) -> pd.Series:
    """Fetch VVIX from TSDB. Thin wrapper for testability."""
    return TSDBSymbol("eqsp_s_.vvix@close").get_data(start=start, end=end)


# ---------------------------------------------------------------------------
# Generic Dataset API (for cross-asset vol surfaces)
# ---------------------------------------------------------------------------


def fetch_dataset_timeseries(
    dataset_id: str,
    start_date: date,
    end_date: date,
    value_col: str = "impliedVolatility",
    post_filter: dict[str, str] | None = None,
    **query_params: object,
) -> pd.Series:
    """Fetch a single time series from any Marquee Dataset.

    Uses the same chunking and retry logic as EDRVOL_PERCENT fetches.

    Parameters
    ----------
    dataset_id : str
        Marquee dataset ID (e.g., 'FXIMPLIEDVOL_PREMIUM').
    start_date, end_date : date
        Date range (inclusive).
    value_col : str
        Column name containing the value to extract.
    post_filter : dict, optional
        Column→value filters applied after fetch (for datasets that
        don't support server-side filtering on all fields).
    **query_params
        Passed directly to ``Dataset.get_data()`` (e.g., bbid, tenor).

    Returns
    -------
    pd.Series
        DatetimeIndex, values from ``value_col``. Empty series on failure.
    """
    _ensure_session()
    ds = Dataset(dataset_id)

    # Build chunk ranges (3-month chunks)
    delta = relativedelta(end_date, start_date)
    total_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)

    if total_months <= _MAX_CHUNK_MONTHS:
        chunk_ranges = [(start_date, end_date)]
    else:
        chunk_ranges = []
        chunk_start = start_date
        while chunk_start <= end_date:
            chunk_end = min(
                chunk_start + relativedelta(months=_MAX_CHUNK_MONTHS) - relativedelta(days=1),
                end_date,
            )
            chunk_ranges.append((chunk_start, chunk_end))
            chunk_start = chunk_end + relativedelta(days=1)

    # Fetch chunks sequentially (API rate limits)
    frames: list[pd.DataFrame] = []
    for cs, ce in chunk_ranges:
        for attempt in range(_MAX_RETRIES):
            try:
                _ensure_session()
                chunk = ds.get_data(start=cs, end=ce, **query_params)
                if chunk is not None and not chunk.empty:
                    frames.append(chunk)
                break
            except Exception:  # noqa: BLE001
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BACKOFF[attempt])
                else:
                    logger.warning(
                        "Failed %s chunk %s-%s after %d retries",
                        dataset_id,
                        cs,
                        ce,
                        _MAX_RETRIES,
                    )

    if not frames:
        return pd.Series(dtype="float64", name=value_col)

    raw = pd.concat(frames)

    # Apply post-fetch filters
    if post_filter:
        for col, val in post_filter.items():
            if col in raw.columns:
                raw = raw[raw[col] == val]

    if raw.empty or value_col not in raw.columns:
        return pd.Series(dtype="float64", name=value_col)

    # Extract the value column, deduplicate by date (take first)
    result = raw[value_col].groupby(raw.index).first()
    result.index = pd.DatetimeIndex(result.index)
    result.index.name = "date"
    result.name = value_col
    return result
