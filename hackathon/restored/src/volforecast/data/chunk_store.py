"""Tick data access via pytickclient (Chunk Store).

Provides functions to fetch L1 trade/quote data for all 34 symbols and
L2 order book depth data for E-mini S&P 500. Raw tick data is the
foundation for computing realized volatility measures at arbitrary
frequencies (5-min, 1-min, tick-by-tick).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import date, datetime, timedelta
from datetime import time as dt_time

import pandas as pd

try:
    from pytickclient import query
except ImportError:
    query = None  # Not available outside GS network

try:
    from goldmansachs import pyslang as _pyslang
except ImportError:
    _pyslang = None

# Suppress noisy pyslang.launch logging (it adds its own StreamHandler at import time)
logging.getLogger("goldmansachs.pyslang.launch").setLevel(logging.ERROR)

from volforecast.constants import CHUNKDB, L1_FIELDS, SYMBOL_UNIVERSE, TICKER_TO_RIC, TZ

logger = logging.getLogger(__name__)

_session_started = False
_session_lock = threading.Lock()
_MAX_SESSION_RETRIES = 3


def _reset_session() -> None:
    """Mark session as dead so the next _ensure_session() re-initializes."""
    global _session_started  # noqa: PLW0603
    with _session_lock:
        if _session_started:
            try:
                _pyslang.stop()
            except Exception:  # noqa: BLE001
                pass
            _session_started = False


def _ensure_session() -> None:
    """Lazily start a pyslang session (thread-safe, double-checked locking).

    pyslang.start() internally spawns secexpr and waits up to 5 minutes
    (grace period) for it to become responsive. If start() returns without
    raising, the session is ready — no extra health check needed.

    If pyslang is not available or secexpr is not installed (e.g. Coder
    workspace), skip session start — pytickclient can connect to Chunk Store
    directly via its REST transport layer.

    If the secexpr subprocess crashes during startup (forrtl error 200,
    ret_code 255), we retry with increasing delays to avoid resource
    contention from rapid respawns.
    """
    global _session_started  # noqa: PLW0603
    if _session_started:
        return
    with _session_lock:
        if _session_started:
            return
        if _pyslang is None:
            # No pyslang available — pytickclient can still connect directly
            # to Chunk Store via REST.
            logger.debug("pyslang not available; pytickclient will connect directly to Chunk Store")
            _session_started = True
            return
        for attempt in range(_MAX_SESSION_RETRIES):
            try:
                _pyslang.start(subprocess=True, object_database="Equity")
            except FileNotFoundError as exc:
                # secexpr/runmapsecenv binary not installed — skip pyslang entirely.
                # pytickclient can connect to Chunk Store directly via REST.
                logger.info(
                    "secexpr not found (%s); pytickclient will connect directly to Chunk Store",
                    exc,
                )
                _session_started = True
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "pyslang.start() failed (attempt %d/%d): %s",
                    attempt + 1,
                    _MAX_SESSION_RETRIES,
                    exc,
                )
                if attempt < _MAX_SESSION_RETRIES - 1:
                    # Exponential backoff: 10s, 20s between retries
                    # Gives time for port/resource cleanup after crash
                    time.sleep(10 * (attempt + 1))
                    continue
                raise ConnectionError(
                    f"pyslang session failed to start after {_MAX_SESSION_RETRIES} attempts: {exc}"
                ) from exc

            # pyslang.start() succeeded — its internal grace period already
            # proved the session is responsive. Actual liveness confirmed by
            # the first chunk_query call (which has its own retry + reset).
            _session_started = True
            return

        raise ConnectionError(
            "pyslang session failed to start after "
            f"{_MAX_SESSION_RETRIES} attempts. "
            "Check network connectivity and try again."
        )


# E-mini S&P 500 contract cycle (quarterly: H=Mar, M=Jun, U=Sep, Z=Dec)
# Rolls to next contract on the Thursday before 3rd Friday of expiry month.
_ES_EXPIRY_MONTHS = {3: "H", 6: "M", 9: "U", 12: "Z"}


def _third_friday(year: int, month: int) -> date:
    """Return the 3rd Friday of the given month/year."""
    # First day of month
    first = date(year, month, 1)
    # Day of week: 0=Mon, 4=Fri
    days_until_friday = (4 - first.weekday()) % 7
    first_friday = first.day + days_until_friday
    return date(year, month, first_friday + 14)  # +14 gives 3rd Friday


def _es_roll_date(year: int, month: int) -> date:
    """Return the ES roll date: Thursday before 3rd Friday of expiry month."""
    third_fri = _third_friday(year, month)
    return third_fri - timedelta(days=1)  # Thursday


def _resolve_es_symbol(trade_date: date) -> str:
    """Map a date to the correct front-month E-mini S&P 500 RIC.

    ES contracts expire quarterly (H=Mar, M=Jun, U=Sep, Z=Dec).
    The front contract rolls to the next quarter on the Thursday
    before the 3rd Friday of the expiry month. Before that date,
    the expiring contract is still the front month.
    """
    # Determine current and next expiry months relative to trade_date
    expiry_months = [3, 6, 9, 12]

    # Find the current-quarter expiry month (>= trade_date's month)
    current_expiry_month = None
    for em in expiry_months:
        if trade_date.month <= em:
            current_expiry_month = em
            break
    if current_expiry_month is None:
        # Past December -> next year's March
        current_expiry_month = 3

    # Year for the current expiry
    current_year = trade_date.year
    if current_expiry_month < trade_date.month:
        current_year += 1

    # Check if we've passed the roll date for this contract
    roll = _es_roll_date(current_year, current_expiry_month)
    if trade_date >= roll:
        # Already rolled: front contract is the NEXT quarter
        idx = expiry_months.index(current_expiry_month)
        next_idx = (idx + 1) % 4
        next_month = expiry_months[next_idx]
        next_year = current_year + (1 if next_idx == 0 else 0)
        code = _ES_EXPIRY_MONTHS[next_month]
        return f"ES{code}{next_year % 100:02d}"

    # Before roll: current contract is still front
    code = _ES_EXPIRY_MONTHS[current_expiry_month]
    return f"ES{code}{current_year % 100:02d}"


def _generate_trading_days(start: date, end: date):
    """Yield weekdays between start and end (inclusive)."""
    current = start
    while current <= end:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)


def _validate_symbol(symbol: str) -> None:
    if symbol not in SYMBOL_UNIVERSE:
        raise ValueError(
            f"Symbol '{symbol}' not in the symbol universe ({len(SYMBOL_UNIVERSE)} symbols). "
            f"Add it to EQUITY_SYMBOLS in constants.py."
        )


def fetch_trades(
    symbol: str,
    start_date: date,
    end_date: date,
    exchange: str | None = None,
) -> pd.DataFrame:
    """Fetch L1 trade ticks from Chunk Store.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g., 'AAPL', 'SPY', 'ES' for E-mini).
    start_date, end_date : date
        Date range (inclusive).
    exchange : str, optional
        Filter to specific exchange.

    Returns
    -------
    pd.DataFrame
        Columns: price, size. Index: tz-aware DatetimeIndex (US/Eastern).
    """
    _validate_symbol(symbol)

    if query is None:
        raise ConnectionError("pytickclient not available. Run on GS desktop with pyslang started.")
    _ensure_session()

    frames = []
    for td in _generate_trading_days(start_date, end_date):
        chunk_symbol = (
            _resolve_es_symbol(td) if symbol == "ES" else TICKER_TO_RIC.get(symbol, symbol)
        )

        st = TZ.localize(datetime(td.year, td.month, td.day, 9, 30, 0))
        et = TZ.localize(datetime(td.year, td.month, td.day, 16, 0, 0))

        raw = query.chunk_query([chunk_symbol], st, et, CHUNKDB, fields=L1_FIELDS)
        df = pd.DataFrame(raw)
        if df.empty:
            continue

        # Forward-fill and parse
        for f in L1_FIELDS:
            if f in df.columns:
                df[f] = df[f].ffill()
        df["Time"] = pd.to_datetime(df["Time"])
        if df["Time"].dt.tz is None:
            df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)

        # Keep only rows with valid trade prices
        df = df[df["TRDPRC_1"] > 0].copy()
        if df.empty:
            continue

        timestamps = pd.DatetimeIndex(df["Time"])
        day_df = pd.DataFrame(
            {
                "price": pd.to_numeric(df["TRDPRC_1"], errors="coerce").values,
                "size": pd.to_numeric(df["TRDVOL_1"], errors="coerce").values,
            },
            index=timestamps,
        )
        day_df.index.name = "timestamp"
        frames.append(day_df)

    if not frames:
        return pd.DataFrame(columns=["price", "size"])

    return pd.concat(frames).sort_index()


# ---------------------------------------------------------------------------
# Batch fetching with retry / timeout
# ---------------------------------------------------------------------------


def _chunk_query_with_timeout(
    symbols: list[str],
    st: datetime,
    et: datetime,
    chunkdb: str,
    fields: list[str],
    timeout_s: float = 120.0,
    retries: int = 2,
    backoff_base: float = 2.0,
    processors: list | None = None,
) -> dict:
    """Call chunk_query with wall-clock timeout and exponential-backoff retry.

    Uses a disposable single-thread executor for timeout enforcement.
    On timeout or error, ``shutdown(wait=False)`` is called so the caller
    is never blocked by a hung chunk_query thread (the orphaned thread will
    eventually terminate when the underlying C call returns or the process exits).
    """
    last_exc: Exception | None = None
    for attempt in range(1 + retries):
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            kwargs: dict = {"fields": fields}
            if processors is not None:
                kwargs["processors"] = processors
            future = executor.submit(query.chunk_query, symbols, st, et, chunkdb, **kwargs)
            result = future.result(timeout=timeout_s)
            executor.shutdown(wait=False)
            return result
        except FuturesTimeoutError:
            # Critical: shutdown(wait=False) so we don't block on the hung thread.
            executor.shutdown(wait=False, cancel_futures=True)
            logger.warning(
                "chunk_query timeout (%.0fs) for %s %s->%s, attempt %d/%d",
                timeout_s,
                symbols,
                st,
                et,
                attempt + 1,
                1 + retries,
            )
            last_exc = TimeoutError(f"chunk_query timed out after {timeout_s}s")
        except (ConnectionResetError, BrokenPipeError, OSError) as exc:
            executor.shutdown(wait=False, cancel_futures=True)
            # Session died -- reset so next call re-initializes
            logger.warning(
                "chunk_query session crash for %s %s->%s, attempt %d/%d: %s",
                symbols,
                st,
                et,
                attempt + 1,
                1 + retries,
                exc,
            )
            _reset_session()
            last_exc = exc
        except Exception as exc:  # noqa: BLE001
            executor.shutdown(wait=False, cancel_futures=True)
            logger.warning(
                "chunk_query error for %s %s->%s, attempt %d/%d: %s",
                symbols,
                st,
                et,
                attempt + 1,
                1 + retries,
                exc,
            )
            last_exc = exc
        if attempt < retries:
            time.sleep(backoff_base**attempt)
    # All retries exhausted
    logger.error(
        "chunk_query failed after %d attempts for %s: %s",
        1 + retries,
        symbols,
        last_exc,
    )
    return {}


def _group_contiguous_dates(dates: list[date]) -> list[list[date]]:
    """Group sorted weekday dates into contiguous trading-day runs.

    Two dates are contiguous if there are no weekday gaps between them
    (weekend gaps are allowed).
    """
    if not dates:
        return []
    groups: list[list[date]] = [[dates[0]]]
    for prev, cur in zip(dates, dates[1:]):
        # Count weekdays in the gap (exclusive of both endpoints)
        gap_weekdays = 0
        if cur > prev + timedelta(days=1):
            gap_weekdays = sum(
                1 for _ in _generate_trading_days(prev + timedelta(days=1), cur - timedelta(days=1))
            )
        if gap_weekdays == 0:
            groups[-1].append(cur)
        else:
            groups.append([cur])
    return groups


def _parse_raw_to_day_frames(raw: dict) -> dict[date, pd.DataFrame]:
    """Parse a raw chunk_query response into per-day trade DataFrames."""
    df = pd.DataFrame(raw)
    if df.empty:
        return {}

    for f in L1_FIELDS:
        if f in df.columns:
            df[f] = df[f].ffill()
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is None:
        df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)

    df = df[df["TRDPRC_1"] > 0].copy()
    if df.empty:
        return {}

    df["_date"] = df["Time"].dt.date
    result: dict[date, pd.DataFrame] = {}
    for day, grp in df.groupby("_date"):
        timestamps = pd.DatetimeIndex(grp["Time"])
        day_df = pd.DataFrame(
            {
                "price": pd.to_numeric(grp["TRDPRC_1"], errors="coerce").values,
                "size": pd.to_numeric(grp["TRDVOL_1"], errors="coerce").values,
            },
            index=timestamps,
        )
        day_df.index.name = "timestamp"
        result[day] = day_df
    return result


def fetch_trades_batch(
    symbol: str,
    dates: list[date],
    batch_size: int = 5,
    timeout_s: float = 120.0,
    retries: int = 2,
    on_fetch: Callable[[str, list[date], int, float], None] | None = None,
) -> dict[date, pd.DataFrame]:
    """Fetch trades for multiple dates using batched API calls.

    Groups dates into contiguous runs and issues one ``chunk_query`` per
    batch (up to *batch_size* days), reducing total API calls.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    dates : list[date]
        Specific dates to fetch (must be weekdays).
    batch_size : int
        Maximum days per single API call (default 5).
    timeout_s : float
        Timeout per API call in seconds (default 120).
    retries : int
        Number of retries per failed API call (default 2).
    on_fetch : callable, optional
        Progress callback ``(event, chunk_dates, n_ticks, elapsed_s)``.
        *event* is ``"start"`` (before API call) or ``"done"`` (after).

    Returns
    -------
    dict[date, pd.DataFrame]
        Mapping of date -> trades DataFrame. Dates with no data get
        an empty DataFrame.
    """
    if not dates:
        return {}

    _validate_symbol(symbol)
    if query is None:
        raise ConnectionError("pytickclient not available.")
    _ensure_session()

    empty_df = pd.DataFrame(columns=["price", "size"])
    result: dict[date, pd.DataFrame] = {d: empty_df for d in dates}

    def _notify(event: str, chunk: list[date], n_ticks: int, elapsed_s: float) -> None:
        if on_fetch is None:
            return
        try:
            on_fetch(event, chunk, n_ticks, elapsed_s)
        except Exception:  # noqa: BLE001
            logger.debug("on_fetch callback error (event=%s)", event, exc_info=True)

    def _fetch_chunk(chunk_symbol: str, chunk: list[date]) -> None:
        _notify("start", chunk, 0, 0.0)
        t0 = time.perf_counter()
        # Query each day individually to avoid enormous multi-day payloads
        # that exceed timeout (SPY has ~280K ticks/day).
        all_parsed: dict[date, pd.DataFrame] = {}
        for day in chunk:
            st = TZ.localize(datetime(day.year, day.month, day.day, 9, 30, 0))
            et = TZ.localize(datetime(day.year, day.month, day.day, 16, 0, 0))
            raw = _chunk_query_with_timeout(
                [chunk_symbol],
                st,
                et,
                CHUNKDB,
                L1_FIELDS,
                timeout_s=timeout_s,
                retries=retries,
            )
            parsed = _parse_raw_to_day_frames(raw)
            all_parsed.update(parsed)
        n_ticks = sum(len(df) for df in all_parsed.values())
        for day, day_df in all_parsed.items():
            if day in result:
                result[day] = day_df
        _notify("done", chunk, n_ticks, time.perf_counter() - t0)

    if symbol == "ES":
        # ES needs per-day contract resolution; group by contract
        contract_groups: dict[str, list[date]] = {}
        for d in sorted(dates):
            cs = _resolve_es_symbol(d)
            contract_groups.setdefault(cs, []).append(d)
        for cs, cs_dates in contract_groups.items():
            for group in _group_contiguous_dates(cs_dates):
                for i in range(0, len(group), batch_size):
                    _fetch_chunk(cs, group[i : i + batch_size])
    else:
        # Resolve bare ticker to exchange-suffixed RIC for Chunk Store
        chunk_ric = TICKER_TO_RIC.get(symbol, symbol)
        for group in _group_contiguous_dates(sorted(dates)):
            for i in range(0, len(group), batch_size):
                _fetch_chunk(chunk_ric, group[i : i + batch_size])

    return result


# ---------------------------------------------------------------------------
# AggGroupBy bar fetching (fast path -- server-side aggregation)
# ---------------------------------------------------------------------------

try:
    from pytickclient import processor as _processor
except ImportError:
    _processor = None

_BAR_OPERATIONS = [
    "first(TRDPRC_1)",
    "max(TRDPRC_1)",
    "min(TRDPRC_1)",
    "last(TRDPRC_1)",
    "sum(TRDVOL_1)",
    "count(TRDPRC_1)",
]

_BAR_FIELDS = ["TRDPRC_1", "TRDVOL_1"]

_BAR_COLUMN_MAP = {
    "first_TRDPRC_1": "open",
    "max_TRDPRC_1": "high",
    "min_TRDPRC_1": "low",
    "last_TRDPRC_1": "close",
    "sum_TRDVOL_1": "volume",
    "count_TRDPRC_1": "n_ticks",
}


def fetch_bars(
    symbol: str,
    dates: list[date],
    interval: float = 300.0,
    batch_size: int = 20,
    timeout_s: float = 120.0,
    retries: int = 2,
) -> dict[date, pd.DataFrame]:
    """Fetch 5-min OHLCV bars via AggGroupBy server-side aggregation.

    Returns ~78 rows per day instead of millions of raw ticks. ~14x faster.
    Uses the same query window (09:30-16:00 ET per day) as fetch_trades_batch().

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g., 'SPY', 'AAPL', 'ES').
    dates : list[date]
        Trading days to fetch.
    interval : float
        Bar interval in seconds (default 300 = 5 minutes).
    batch_size : int
        Max days per API call (default 20).
    timeout_s : float
        Timeout per call.
    retries : int
        Retry count per failed call.

    Returns
    -------
    dict[date, pd.DataFrame]
        Mapping of date -> DataFrame with columns:
        [time, open, high, low, close, volume, n_ticks]
    """
    if not dates:
        return {}

    _validate_symbol(symbol)
    if query is None:
        raise ConnectionError("pytickclient not available.")
    if _processor is None:
        raise ConnectionError("pytickclient.processor not available.")
    _ensure_session()

    result: dict[date, pd.DataFrame] = {}

    def _fetch_bar_chunk(chunk_symbol: str, chunk: list[date]) -> None:
        # Query window spans all days in the chunk
        first_day = chunk[0]
        last_day = chunk[-1]
        st = TZ.localize(datetime(first_day.year, first_day.month, first_day.day, 9, 30, 0))
        et = TZ.localize(datetime(last_day.year, last_day.month, last_day.day, 16, 0, 0))

        proc = _processor.AggGroupBy(groupByOperations=_BAR_OPERATIONS, interval=interval)

        raw = _chunk_query_with_timeout(
            [chunk_symbol],
            st,
            et,
            CHUNKDB,
            _BAR_FIELDS,
            timeout_s=timeout_s,
            retries=retries,
            processors=[proc],
        )

        if isinstance(raw, dict) and not raw:
            return
        if hasattr(raw, "__len__") and len(raw) == 0:
            return

        df = pd.DataFrame(raw)
        if df.empty:
            return

        # Coerce numeric columns
        for col in _BAR_COLUMN_MAP:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Parse and convert timestamps: UTC -> Eastern
        df["Time"] = pd.to_datetime(df["Time"])
        if df["Time"].dt.tz is None:
            df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)
        else:
            df["Time"] = df["Time"].dt.tz_convert(TZ)

        # Split by date
        df["_date"] = df["Time"].dt.date
        for day, grp in df.groupby("_date"):
            if day not in [d for d in chunk]:
                continue
            # Filter to market hours only (09:30-16:00 ET) — overnight bins
            # from multi-day batches have zero trades and corrupt RV.
            mkt_open = grp["Time"].dt.time >= dt_time(9, 30)
            mkt_close = grp["Time"].dt.time <= dt_time(16, 0)
            grp = grp[mkt_open & mkt_close]
            if grp.empty:
                continue
            day_df = grp.rename(columns=_BAR_COLUMN_MAP).copy()
            day_df["time"] = day_df["Time"]
            bar_cols = ["time", "open", "high", "low", "close", "volume", "n_ticks"]
            day_df = day_df[bar_cols].reset_index(drop=True)
            # Coerce n_ticks to int where possible
            day_df["n_ticks"] = (
                pd.to_numeric(day_df["n_ticks"], errors="coerce").fillna(0).astype(int)
            )
            result[day] = day_df

    if symbol == "ES":
        contract_groups: dict[str, list[date]] = {}
        for d in sorted(dates):
            cs = _resolve_es_symbol(d)
            contract_groups.setdefault(cs, []).append(d)
        for cs, cs_dates in contract_groups.items():
            for group in _group_contiguous_dates(cs_dates):
                for i in range(0, len(group), batch_size):
                    _fetch_bar_chunk(cs, group[i : i + batch_size])
    else:
        chunk_ric = TICKER_TO_RIC.get(symbol, symbol)
        for group in _group_contiguous_dates(sorted(dates)):
            for i in range(0, len(group), batch_size):
                _fetch_bar_chunk(chunk_ric, group[i : i + batch_size])

    return result


def fetch_quotes(
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch L1 quote ticks (bid/ask) from Chunk Store.

    Returns
    -------
    pd.DataFrame
        Columns: bid_price, ask_price, bid_size, ask_size.
        Index: tz-aware DatetimeIndex (US/Eastern).
    """
    _validate_symbol(symbol)

    if query is None:
        raise ConnectionError("pytickclient not available. Run on GS desktop with pyslang started.")
    _ensure_session()

    frames = []
    for td in _generate_trading_days(start_date, end_date):
        chunk_symbol = (
            _resolve_es_symbol(td) if symbol == "ES" else TICKER_TO_RIC.get(symbol, symbol)
        )

        st = TZ.localize(datetime(td.year, td.month, td.day, 9, 30, 0))
        et = TZ.localize(datetime(td.year, td.month, td.day, 16, 0, 0))

        raw = query.chunk_query([chunk_symbol], st, et, CHUNKDB, fields=L1_FIELDS)
        df = pd.DataFrame(raw)
        if df.empty:
            continue

        for f in L1_FIELDS:
            if f in df.columns:
                df[f] = df[f].ffill()
        df["Time"] = pd.to_datetime(df["Time"])
        if df["Time"].dt.tz is None:
            df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)

        timestamps = pd.DatetimeIndex(df["Time"])
        day_df = pd.DataFrame(
            {
                "bid_price": df["BID"].values,
                "ask_price": df["ASK"].values,
                "bid_size": df["BIDSIZE"].values,
                "ask_size": df["ASKSIZE"].values,
            },
            index=timestamps,
        )
        day_df.index.name = "timestamp"
        frames.append(day_df)

    if not frames:
        return pd.DataFrame(columns=["bid_price", "ask_price", "bid_size", "ask_size"])

    return pd.concat(frames).sort_index()


def fetch_depth(
    start_date: date,
    end_date: date,
    levels: int = 5,
) -> pd.DataFrame:
    """Fetch L2 order book depth for E-mini S&P 500.

    Parameters
    ----------
    start_date, end_date : date
        Date range (inclusive).
    levels : int
        Number of book levels (max 5).

    Returns
    -------
    pd.DataFrame
        L2 depth data with bid/ask prices and sizes per level.
        Index: tz-aware DatetimeIndex (US/Eastern).
    """
    if query is None:
        raise ConnectionError("pytickclient not available. Run on GS desktop with pyslang started.")
    _ensure_session()

    levels = min(levels, 5)
    depth_fields = []
    for lvl in range(1, levels + 1):
        depth_fields.extend(
            [
                f"BEST_BID{lvl}",
                f"BEST_ASK{lvl}",
                f"BEST_BSIZ{lvl}",
                f"BEST_ASIZ{lvl}",
            ]
        )

    frames = []
    for td in _generate_trading_days(start_date, end_date):
        es_sym = _resolve_es_symbol(td) + "m"  # Deep-book symbol

        st = TZ.localize(datetime(td.year, td.month, td.day, 9, 30, 0))
        et = TZ.localize(datetime(td.year, td.month, td.day, 16, 0, 0))

        raw = query.chunk_query([es_sym], st, et, CHUNKDB, fields=depth_fields)
        df = pd.DataFrame(raw)
        if df.empty:
            continue

        for f in depth_fields:
            if f in df.columns:
                df[f] = df[f].ffill()
        df["Time"] = pd.to_datetime(df["Time"])
        if df["Time"].dt.tz is None:
            df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)

        df = df.set_index("Time")
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames).sort_index()
