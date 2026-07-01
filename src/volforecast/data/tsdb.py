"""Daily data access from TSDB (Time Series Database).

Provides functions to fetch daily OHLCV data, treasury yields,
FX rates, commodity prices, VIX, VIX futures, and SPX index data
used for cross-asset feature construction.

Uses TSDBSymbol (gs_quant_internal) as the primary API path —
no pyslang session required. Falls back gracefully when the
GS internal packages are unavailable (raises ConnectionError).

Key functions:
    fetch_daily_ohlcv      — Daily OHLCV for equity/ETF symbols
    fetch_treasury_yields  — Daily treasury yields (2y/5y/10y/30y)
    fetch_fx_rates         — Daily FX rates (USD/JPY, EUR/USD)
    fetch_commodity_prices — Daily commodity prices (CL, GC)
    fetch_vix              — VIX close level
    fetch_vix_futures      — VIX futures term structure (VX1/VX2/VX3)
    fetch_spx_index        — SPX index OHLCV
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from datetime import date

import pandas as pd

from volforecast.constants import (
    COMMODITY_SYMBOLS,
    FX_SYMBOLS,
    OHLCV_FIELDS,
    SYMBOL_UNIVERSE,
    TICKER_TO_RIC,
    TREASURY_SYMBOLS,
)

try:
    from gs_quant.errors import MqUninitialisedError
    from gs_quant.session import GsSession  # noqa: F401 — availability check
    from gs_quant_internal.tsdb import TSDBSymbol

    _HAS_GS_QUANT = True
    _GS_SESSION_ERRORS = (MqUninitialisedError,)
except ImportError:
    _HAS_GS_QUANT = False
    _GS_SESSION_ERRORS = ()

# ---------------------------------------------------------------------------
# Ticker-to-RIC mapping — uses canonical TICKER_TO_RIC from constants.py
# ---------------------------------------------------------------------------

_TENOR_TO_RIC: dict[str, str] = {
    "2y": "US2YT=RR",
    "5y": "US5YT=RR",
    "10y": "US10YT=RR",
    "30y": "US30YT=RR",
}

_PAIR_TO_TSDB: dict[str, str] = {
    "USD/JPY": "eqpad_usd/jpy@close",
    "EUR/USD": "eqpad_usd/eur@close",  # CME convention: inverted quote (eur/usd returns 500)
}


def _ticker_to_ric(ticker: str) -> str:
    """Convert a bare ticker to a Reuters RIC for TSDB lookups.

    Uses the canonical TICKER_TO_RIC mapping from volforecast.constants.

    Raises ValueError if the ticker is not in SYMBOL_UNIVERSE or
    has no exchange mapping (e.g. futures like 'ES' use a different path).
    """
    if ticker not in SYMBOL_UNIVERSE:
        raise ValueError(
            f"Symbol '{ticker}' not in the 34-symbol universe. "
            f"Valid symbols: {sorted(SYMBOL_UNIVERSE)}"
        )
    if ticker not in TICKER_TO_RIC:
        raise ValueError(f"No RIC mapping for '{ticker}'. Futures use a different query path.")
    return TICKER_TO_RIC[ticker]


_PRICE_FIELDS = {"open", "high", "low", "close"}

_SESSION_LOCK = threading.Lock()


def _ensure_session() -> None:
    """Ensure GsSession is active; initialize on first use if needed.

    Thread-safe: uses a lock to prevent concurrent GsSession.use() calls
    which can corrupt session state (base URL becomes 'PROD' instead of
    the actual endpoint).
    """
    if not _HAS_GS_QUANT:
        raise ConnectionError("gs_quant_internal not available. Run on GS desktop.")
    try:
        _ = GsSession.current
    except _GS_SESSION_ERRORS:
        with _SESSION_LOCK:
            # Double-check after acquiring lock (another thread may have initialized)
            try:
                _ = GsSession.current
            except _GS_SESSION_ERRORS:
                try:
                    GsSession.use()
                except Exception as exc:  # noqa: BLE001
                    raise ConnectionError(
                        "TSDB unavailable: could not initialize GsSession."
                    ) from exc


def _tsdb_symbol(ric: str, field: str, adjusted: bool = False) -> str:
    """Build a TSDB symbol string from a RIC and field name."""
    if adjusted and field in _PRICE_FIELDS:
        return f"eqpad_{ric}@{field}.adj.allincdiv"
    return f"eqpad_{ric}@{field}"


def _get_tsdb_data(symbol: str, start: str, end: str) -> pd.Series:
    """Fetch a single TSDB symbol series. Thread-safe session initialization."""
    _ensure_session()
    try:
        return TSDBSymbol(symbol).get_data(start=start, end=end)
    except _GS_SESSION_ERRORS:
        # Session expired mid-request; re-initialize and retry once
        _ensure_session()
        try:
            return TSDBSymbol(symbol).get_data(start=start, end=end)
        except Exception as retry_exc:  # noqa: BLE001
            raise ConnectionError(
                f"TSDB unavailable for '{symbol}' after re-initializing GsSession."
            ) from retry_exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_daily_ohlcv(
    symbols: Sequence[str],
    start_date: date,
    end_date: date,
    adjusted: bool = True,
) -> pd.DataFrame:
    """Fetch daily OHLCV data from TSDB.

    Parameters
    ----------
    symbols : Sequence[str]
        List of ticker symbols (e.g. ['AAPL', 'SPY']).
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    adjusted : bool
        Whether to return corporate-action-adjusted prices
        (default: True). Applies to open/high/low/close.
        Volume is always unadjusted.

    Returns
    -------
    pd.DataFrame
        MultiIndex (date, symbol) with columns: open, high, low, close, volume.

    Raises
    ------
    ValueError
        If any symbol is not in the 34-symbol universe.
    ConnectionError
        If GS Quant packages are unavailable.
    """
    if not symbols:
        return pd.DataFrame(
            columns=OHLCV_FIELDS,
            index=pd.MultiIndex.from_tuples([], names=["date", "symbol"]),
        )

    # Validate all symbols up front
    for sym in symbols:
        _ticker_to_ric(sym)  # raises ValueError if invalid

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    frames = []

    for sym in symbols:
        ric = _ticker_to_ric(sym)
        field_data: dict[str, pd.Series] = {}
        for field in OHLCV_FIELDS:
            use_adj = adjusted and field in _PRICE_FIELDS
            tsdb_sym = _tsdb_symbol(ric, field, adjusted=use_adj)
            series = _get_tsdb_data(tsdb_sym, start_str, end_str)
            field_data[field] = series

        sym_df = pd.DataFrame(field_data)
        sym_df.index = pd.DatetimeIndex(sym_df.index)
        sym_df.index.name = "date"
        sym_df["symbol"] = sym
        frames.append(sym_df)

    combined = pd.concat(frames)
    combined = combined.set_index("symbol", append=True)
    combined.index.names = ["date", "symbol"]
    return combined


def fetch_treasury_yields(
    start_date: date,
    end_date: date,
    tenors: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch daily treasury prices from TSDB.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    tenors : Sequence[str], optional
        Tenor labels to fetch (default: ['2y', '5y', '10y', '30y']).

    Returns
    -------
    pd.DataFrame
        Index: DatetimeIndex. Columns: tenor labels (e.g., '2y', '10y').

    Notes
    -----
    TSDB returns bond *prices*, not yields. The column labels use tenor
    names for convenience; downstream code should be aware these are
    price levels, not yield percentages.
    """
    if tenors is None:
        tenors = list(TREASURY_SYMBOLS.keys())

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    result: dict[str, pd.Series] = {}

    for tenor in tenors:
        ric = _TENOR_TO_RIC[tenor]
        tsdb_sym = f"eqpad_{ric}@close"
        series = _get_tsdb_data(tsdb_sym, start_str, end_str)
        result[tenor] = series

    df = pd.DataFrame(result)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df


def fetch_fx_rates(
    start_date: date,
    end_date: date,
    pairs: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch daily FX rates from TSDB.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    pairs : Sequence[str], optional
        Currency pair labels (default: ['USDJPY', 'EURUSD']).
        Must match keys in ``volforecast.constants.FX_SYMBOLS``.

    Returns
    -------
    pd.DataFrame
        Index: DatetimeIndex. Columns: pair labels.

    Notes
    -----
    The Slang TSDB wrapper uses lowercase pair format (``"usd/jpy"``).
    This function uses TSDBSymbol with the ``eqpad_`` prefix instead.
    """
    if pairs is None:
        pairs = list(FX_SYMBOLS.keys())

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    result: dict[str, pd.Series] = {}

    for pair in pairs:
        tsdb_sym = _PAIR_TO_TSDB[pair]
        series = _get_tsdb_data(tsdb_sym, start_str, end_str)
        result[pair] = series

    df = pd.DataFrame(result)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df


def fetch_commodity_prices(
    start_date: date,
    end_date: date,
    symbols: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch daily commodity settle prices from TSDB.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    symbols : Sequence[str], optional
        Commodity labels (default: ['CL', 'GC']).

    Returns
    -------
    pd.DataFrame
        Index: DatetimeIndex. Columns: commodity labels.

    Notes
    -----
    Generic front-month symbols (CLv1, GCv1) do **not** work in TSDB.
    This function queries the specific front contract (e.g. ``CLM26``)
    resolved for the midpoint of the requested date range. For ranges
    spanning a roll boundary, the caller should split into sub-ranges
    or use a continuous front series.
    """
    if symbols is None:
        symbols = list(COMMODITY_SYMBOLS.keys())

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    # Resolve front-month contract for midpoint of range
    midpoint = date.fromordinal((start_date.toordinal() + end_date.toordinal()) // 2)
    result: dict[str, pd.Series] = {}

    for sym in symbols:
        contract = _resolve_front_contract(sym, midpoint)
        tsdb_sym = f"eqpad_{contract}@settle"
        series = _get_tsdb_data(tsdb_sym, start_str, end_str)
        result[sym] = series

    df = pd.DataFrame(result)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df


# ---------------------------------------------------------------------------
# Commodity contract rolling
# ---------------------------------------------------------------------------

# CME month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun,
#                  N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
_MONTH_CODE = "FGHJKMNQUVXZ"


def _resolve_front_contract(commodity: str, ref_date: date) -> str:
    """Resolve the front-month contract symbol for a commodity.

    Uses the month *after* ref_date's month as the front contract
    (contracts expire around the 20th of the prior month).
    """
    month = ref_date.month
    year = ref_date.year
    # Front month is next month's contract
    front_month = month % 12 + 1
    if front_month == 1:
        year += 1
    code = _MONTH_CODE[front_month - 1]
    return f"{commodity}{code}{year % 100:02d}"


def _resolve_vx_contracts(ref_date: date, n: int = 3) -> list[str]:
    """Resolve VIX futures contract symbols (VX + month_code + YY).

    VIX futures expire on the Wednesday 30 days before the 3rd Friday
    of the following month. For simplicity we use the same "next month"
    heuristic as commodity contracts.

    Returns *n* consecutive contract symbols starting from front month.
    """
    contracts = []
    month = ref_date.month
    year = ref_date.year
    for _ in range(n):
        month = month % 12 + 1
        if month == 1:
            year += 1
        code = _MONTH_CODE[month - 1]
        contracts.append(f"VX{code}{year % 100:02d}")
    return contracts


# ---------------------------------------------------------------------------
# VIX, VIX Futures, SPX Index
# ---------------------------------------------------------------------------


def fetch_vix(
    start_date: date,
    end_date: date,
) -> pd.Series:
    """Fetch VIX close level from TSDB.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).

    Returns
    -------
    pd.Series
        Index: DatetimeIndex (name='date'). Values: VIX close level.
    """
    tsdb_sym = "eqpad_.VIX@close"
    series = _get_tsdb_data(tsdb_sym, start_date.isoformat(), end_date.isoformat())
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    series.name = "vix"
    return series


def fetch_vix_futures(
    start_date: date,
    end_date: date,
    n_contracts: int = 3,
) -> pd.DataFrame:
    """Fetch VIX futures term structure from TSDB.

    Retrieves settle prices for the front *n_contracts* VIX futures
    contracts, enabling term slope and curvature computation.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    n_contracts : int
        Number of consecutive contracts to fetch (default: 3).

    Returns
    -------
    pd.DataFrame
        Index: DatetimeIndex (name='date').
        Columns: 'VX1', 'VX2', 'VX3', ... (generic labels).
    """
    midpoint = date.fromordinal((start_date.toordinal() + end_date.toordinal()) // 2)
    contracts = _resolve_vx_contracts(midpoint, n=n_contracts)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    result: dict[str, pd.Series] = {}
    for i, contract in enumerate(contracts, start=1):
        tsdb_sym = f"eqpad_{contract}@settle"
        series = _get_tsdb_data(tsdb_sym, start_str, end_str)
        result[f"VX{i}"] = series

    df = pd.DataFrame(result)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df


def fetch_spx_index(
    start_date: date,
    end_date: date,
    fields: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch SPX index OHLCV from TSDB.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    fields : Sequence[str], optional
        Fields to fetch (default: ['open', 'high', 'low', 'close']).

    Returns
    -------
    pd.DataFrame
        Index: DatetimeIndex (name='date'). Columns: requested fields.
    """
    if fields is None:
        fields = ["open", "high", "low", "close"]

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    result: dict[str, pd.Series] = {}

    for field in fields:
        tsdb_sym = f"eqpad_.SPX@{field}"
        series = _get_tsdb_data(tsdb_sym, start_str, end_str)
        result[field] = series

    df = pd.DataFrame(result)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df
