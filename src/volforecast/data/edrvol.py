"""Per-symbol implied volatility ingestion from TSDB edrvol_ namespace.

Fetches ATM IV (1w, 1m, 3m) and 25-delta put/call IV for each symbol, plus the
market-wide CBOE VVIX index. Stores per-symbol parquets in data/raw/iv/.

Public API:
    fetch_edrvol      — Fetch IV fields for a single symbol
    fetch_vvix        — Fetch CBOE VVIX index
    save_iv_cache     — Persist per-symbol IV DataFrame to parquet
    load_iv_cache     — Load cached per-symbol IV (or None if missing)
    compute_iv_dispersion — Cross-sectional IV dispersion from all cached symbols

Unit convention: IV stored as vol points (25.0 = 25%), NOT decimals.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from volforecast.constants import TICKER_TO_EDRVOL_RIC, TICKER_TO_MARQUEE_RIC
from volforecast.utils.paths import cross_asset_cache_dir, iv_cache_dir, processed_dir

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TSDB field mapping
# ---------------------------------------------------------------------------

# edrvol fields -> output column names
_FIELD_MAP: dict[str, str] = {
    "1watms": "iv_1w_atm",
    "1matms": "iv_1m_atm",
    "3matms": "iv_3m_atm",
    "1m25dp": "iv_1m_25dp",
    "1m25dc": "iv_1m_25dc",
}

_DEFAULT_FIELDS = list(_FIELD_MAP.keys())

# VVIX TSDB symbol
_VVIX_SYMBOL = "eqsp_s_.vvix@close"

# VIX index TSDB symbol
_VIX_SYMBOL = "eqpad_.VIX@close"

# OVX proxy: USO (United States Oil Fund) 1-month ATM implied vol via edrvol_
# The actual CBOE OVX index is not available in TSDB; USO ATM IV is a close proxy.
_OVX_SYMBOL = "edrvol_uso.p@1matms"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_tsdb_data(symbol: str, start: str, end: str) -> pd.Series:
    """Fetch a single TSDB symbol series. Delegates to tsdb module."""
    from volforecast.data.tsdb import _get_tsdb_data as _tsdb_fetch

    return _tsdb_fetch(symbol, start, end)


def _build_edrvol_symbol(ric: str, field: str) -> str:
    """Build edrvol TSDB symbol string: edrvol_{ric}@{field}."""
    return f"edrvol_{ric}@{field}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_edrvol(
    symbol: str,
    start_date: date,
    end_date: date,
    fields: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch per-symbol implied volatility from TSDB edrvol_ namespace.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g., 'AAPL', 'SPY').
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    fields : list[str], optional
        TSDB field names to fetch. Defaults to ['1watms', '1matms', '3matms', '1m25dp', '1m25dc'].

    Returns
    -------
    pd.DataFrame
        DatetimeIndex with columns: iv_1w_atm, iv_1m_atm, iv_3m_atm, iv_1m_25dp, iv_1m_25dc.
        Values in vol points (25.0 = 25%).

    Raises
    ------
    ValueError
        If symbol has no EDRVOL RIC mapping.
    ConnectionError
        If TSDB is unavailable.
    """
    if symbol not in TICKER_TO_EDRVOL_RIC:
        raise ValueError(
            f"No EDRVOL RIC mapping for '{symbol}'. "
            f"Valid symbols: {sorted(TICKER_TO_EDRVOL_RIC.keys())}"
        )

    ric = TICKER_TO_EDRVOL_RIC[symbol]
    if fields is None:
        fields = _DEFAULT_FIELDS

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    col_data: dict[str, pd.Series] = {}
    for field in fields:
        tsdb_sym = _build_edrvol_symbol(ric, field)
        col_name = _FIELD_MAP.get(field, field)
        try:
            series = _get_tsdb_data(tsdb_sym, start_str, end_str)
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            col_data[col_name] = series
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch %s for %s: %s", field, symbol, exc)
            continue

    if not col_data:
        return pd.DataFrame(
            columns=[_FIELD_MAP.get(f, f) for f in fields],
            index=pd.DatetimeIndex([], name="date"),
        )

    df = pd.DataFrame(col_data)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"

    # TSDB edrvol_ returns vol points directly (15.0 = 15%); no conversion needed

    return df


def fetch_vvix(start_date: date, end_date: date) -> pd.Series:
    """Fetch CBOE VVIX index from TSDB.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).

    Returns
    -------
    pd.Series
        Named 'vvix', index points (e.g., 100 = 100%).

    Raises
    ------
    ConnectionError
        If TSDB is unavailable.
    """
    series = _get_tsdb_data(_VVIX_SYMBOL, start_date.isoformat(), end_date.isoformat())
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    series.name = "vvix"
    return series


def fetch_vix_index(start_date: date, end_date: date) -> pd.Series:
    """Fetch CBOE VIX index close from TSDB.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).

    Returns
    -------
    pd.Series
        Named 'vix', index points (e.g., 20.0 = 20%).
    """
    series = _get_tsdb_data(_VIX_SYMBOL, start_date.isoformat(), end_date.isoformat())
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    series.name = "vix"
    return series


def fetch_ovx(start_date: date, end_date: date) -> pd.Series:
    """Fetch oil volatility proxy (USO 1M ATM IV) from TSDB.

    The actual CBOE OVX index is not available in TSDB. We use USO
    (United States Oil Fund ETF) 1-month ATM implied vol as a proxy.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).

    Returns
    -------
    pd.Series
        Named 'ovx', vol points (e.g., 30.0 = 30%).
    """
    series = _get_tsdb_data(_OVX_SYMBOL, start_date.isoformat(), end_date.isoformat())
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    series.name = "ovx"
    return series


# CBOE Yield Index symbols via eqsp_s_ namespace.
# Raw values are yield * 10 (TNX=41.3 means 4.13%). We divide by 10 after fetch.
# Note: IRX (13-week) is broken in TSDB (returns constant 0.03); no 2Y index available.
_TREASURY_YIELD_SYMBOLS: dict[str, str] = {
    "5y": "eqsp_s_.fvx",
    "10y": "eqsp_s_.tnx",
    "30y": "eqsp_s_.tyx",
}


def fetch_treasury_yields(
    start_date: date,
    end_date: date,
    tenors: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch daily treasury yields from TSDB.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    tenors : list[str], optional
        Tenor labels. Defaults to ['2y', '5y', '10y', '30y'].

    Returns
    -------
    pd.DataFrame
        Columns: tenor labels. Values: yield in percentage points (e.g., 4.5 = 4.5%).
    """
    if tenors is None:
        tenors = list(_TREASURY_YIELD_SYMBOLS.keys())

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    result: dict[str, pd.Series] = {}

    for tenor in tenors:
        tsdb_sym = _TREASURY_YIELD_SYMBOLS.get(tenor)
        if tsdb_sym is None:
            logger.warning("No TSDB symbol for tenor %s (not available)", tenor)
            continue
        try:
            series = _get_tsdb_data(tsdb_sym, start_str, end_str)
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            # CBOE yield indices store yield * 10 (e.g., TNX=41.3 -> 4.13%)
            result[tenor] = series / 10.0
        except Exception as exc:
            logger.warning("Failed to fetch treasury yield %s: %s", tenor, exc)

    if not result:
        return pd.DataFrame(columns=tenors, index=pd.DatetimeIndex([], name="date"))

    df = pd.DataFrame(result)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df


def save_iv_cache(symbol: str, data: pd.DataFrame) -> Path:
    """Persist per-symbol IV DataFrame to parquet.

    Merges new data with any existing cache — new rows take priority
    for overlapping dates. Never discards existing history.

    Parameters
    ----------
    symbol : str
        Ticker symbol or special name ('_VVIX', '_MARKET').
    data : pd.DataFrame or pd.Series
        IV data to save.

    Returns
    -------
    Path
        Path to the written parquet file.
    """
    out_dir = iv_cache_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}.parquet"

    if isinstance(data, pd.Series):
        data = data.to_frame()

    # Merge with existing cache (never discard old data)
    if path.exists():
        try:
            existing = pd.read_parquet(path)
            merged = pd.concat([existing, data])
            merged = merged[~merged.index.duplicated(keep="last")]
            merged = merged.sort_index()
            data = merged
        except Exception:  # noqa: BLE001
            logger.warning("Could not read existing cache for %s, writing new data only", symbol)

    data.to_parquet(path, engine="pyarrow")
    logger.info("Saved IV cache: %s (%d rows)", path, len(data))
    return path


def load_iv_cache(symbol: str) -> pd.DataFrame | None:
    """Load cached per-symbol IV from parquet.

    Parameters
    ----------
    symbol : str
        Ticker symbol or special name ('_VVIX', '_MARKET').

    Returns
    -------
    pd.DataFrame or None
        Cached data, or None if file doesn't exist.
    """
    path = iv_cache_dir() / f"{symbol}.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df


def compute_iv_dispersion(symbols: list[str] | None = None) -> pd.Series:
    """Compute cross-sectional IV dispersion from cached per-symbol IV.

    IV dispersion = cross-sectional standard deviation of iv_1m_atm across symbols.

    Parameters
    ----------
    symbols : list[str], optional
        Symbols to include. Defaults to all cached symbols with IV data.

    Returns
    -------
    pd.Series
        Named 'iv_dispersion', indexed by date.
    """
    if symbols is None:
        cache_dir = iv_cache_dir()
        if not cache_dir.exists():
            return pd.Series(dtype=float, name="iv_dispersion")
        symbols = [p.stem for p in cache_dir.glob("*.parquet") if not p.stem.startswith("_")]

    atm_ivs: dict[str, pd.Series] = {}
    for sym in symbols:
        cached = load_iv_cache(sym)
        if cached is not None and "iv_1m_atm" in cached.columns:
            atm_ivs[sym] = cached["iv_1m_atm"]

    if len(atm_ivs) < 2:
        return pd.Series(dtype=float, name="iv_dispersion")

    panel = pd.DataFrame(atm_ivs)
    dispersion = panel.std(axis=1, ddof=1)
    dispersion.name = "iv_dispersion"
    return dispersion


# ---------------------------------------------------------------------------
# 0DTE IV — Nearest-expiry implied volatility from EDRVOL_PERCENT_EXPIRY
# ---------------------------------------------------------------------------

_EXPIRY_DATASET_ID = "EDRVOL_PERCENT_EXPIRY"
_EXPIRY_CHUNK_MONTHS = 3  # SPX has daily expirations; 3 months keeps payloads small
_EXPIRY_MAX_RETRIES = 3
_EXPIRY_RETRY_BACKOFF = (2.0, 4.0, 8.0)


def _ensure_expiry_session() -> None:
    """Ensure GsSession is active for expiry dataset queries."""
    try:
        from gs_quant.session import GsSession

        try:
            _ = GsSession.current
        except Exception:
            GsSession.use()
    except ImportError:
        raise ConnectionError("gs_quant not available. Run on GS desktop with active session.")


def _fetch_expiry_chunk(
    ds: object,
    ric: str,
    start: date,
    end: date,
) -> pd.DataFrame | None:
    """Fetch a single date-range chunk with exponential backoff retry."""
    for attempt in range(_EXPIRY_MAX_RETRIES):
        try:
            chunk = ds.get_data(
                start=start,
                end=end,
                ric=ric,
                strikeReference="forward",
                relativeStrike=1.0,
            )
            if chunk is not None and not chunk.empty:
                return chunk
            return None
        except Exception:  # noqa: BLE001
            if attempt < _EXPIRY_MAX_RETRIES - 1:
                time.sleep(_EXPIRY_RETRY_BACKOFF[attempt])
                logger.debug(
                    "Retry %d/%d for expiry chunk %s %s to %s",
                    attempt + 1,
                    _EXPIRY_MAX_RETRIES,
                    ric,
                    start,
                    end,
                )
            else:
                logger.warning(
                    "Failed to fetch expiry chunk %s %s to %s after %d attempts",
                    ric,
                    start,
                    end,
                    _EXPIRY_MAX_RETRIES,
                )
                return None
    return None


def _query_marquee_expiry(ric: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Query EDRVOL_PERCENT_EXPIRY for a single RIC, chunked with retry.

    Splits large date ranges into 3-month chunks to avoid read timeouts
    on liquid underlyings like SPX (which have daily expirations).

    Returns raw DataFrame from Marquee with columns including
    expirationDate, relativeStrike, strikeReference, impliedVolatility.
    """
    _ensure_expiry_session()

    try:
        from gs_quant.data import Dataset
    except ImportError:
        raise ConnectionError("gs_quant not available. Run on GS desktop with active session.")

    ds = Dataset(_EXPIRY_DATASET_ID)

    # Short ranges go in a single request
    delta = relativedelta(end_date, start_date)
    total_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
    if total_months <= _EXPIRY_CHUNK_MONTHS:
        result = _fetch_expiry_chunk(ds, ric, start_date, end_date)
        return result if result is not None else pd.DataFrame()

    # Build chunk date ranges
    chunks: list[pd.DataFrame] = []
    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(
            chunk_start + relativedelta(months=_EXPIRY_CHUNK_MONTHS) - relativedelta(days=1),
            end_date,
        )
        chunk = _fetch_expiry_chunk(ds, ric, chunk_start, chunk_end)
        if chunk is not None and not chunk.empty:
            chunks.append(chunk)
        chunk_start = chunk_end + relativedelta(days=1)

    if not chunks:
        return pd.DataFrame()

    return pd.concat(chunks)


# Minimum plausible impliedVolatility from EDRVOL_PERCENT_EXPIRY. Marquee
# occasionally returns garbage near-zero values (e.g. SPY 2017-09-13 returned
# 1e-05 for iv_0dte). Real ATM IV is never below ~1% annualized; 0.005 is a
# conservative floor that catches the broken values without rejecting any
# legitimate observation. Applies to both decimal- and percent-scaled symbols
# (0.005% annualized vol is equally impossible). Filtered values become NaN
# so they propagate as missing data instead of corrupting downstream
# log_atm_iv_* features (where log(1e-5) ≈ -11.5 destroys linear baselines).
_MIN_PLAUSIBLE_IV = 0.005


def _fetch_expiry_iv(
    symbol: str,
    start_date: date,
    end_date: date,
    min_dte: int = 0,
) -> pd.Series:
    """Fetch ATM implied volatility at a specific DTE offset.

    Uses Marquee EDRVOL_PERCENT_EXPIRY dataset which provides IV indexed
    by listed expiration date. For SPX, daily expiries exist (Mon-Fri).
    For equities/ETFs, nearest available expiry is used.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g., 'SPY', 'SPX', 'AAPL').
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    min_dte : int
        Minimum days-to-expiry. 0 = nearest expiry >= obs_date (0DTE),
        1 = nearest expiry > obs_date (1DTE — prices tomorrow's vol).

    Returns
    -------
    pd.Series
        Named 'iv_0dte' or 'iv_1dte', indexed by observation date.
        Values in vol points (e.g., 18.5 = 18.5% annualized).
        Empty series on failure.
    """
    col_name = f"iv_{min_dte}dte"
    empty = pd.Series(dtype=float, name=col_name)
    empty.index.name = "date"

    if symbol not in TICKER_TO_MARQUEE_RIC:
        raise ValueError(
            f"No Marquee RIC mapping for '{symbol}'. "
            f"Valid symbols: {sorted(TICKER_TO_MARQUEE_RIC.keys())}"
        )

    ric = TICKER_TO_MARQUEE_RIC[symbol]

    try:
        raw = _query_marquee_expiry(ric, start_date, end_date)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch %s IV for %s: %s", col_name, symbol, exc)
        return empty

    if raw is None or raw.empty:
        return empty

    # Ensure required columns exist
    required = {"expirationDate", "impliedVolatility"}
    if not required.issubset(raw.columns):
        logger.warning(
            "EDRVOL_PERCENT_EXPIRY missing columns for %s: %s",
            symbol,
            raw.columns.tolist(),
        )
        return empty

    # Normalize the date index
    if "date" in raw.columns:
        raw["obs_date"] = pd.to_datetime(raw["date"]).dt.normalize()
    elif raw.index.name == "date" or isinstance(raw.index, pd.DatetimeIndex):
        raw["obs_date"] = pd.to_datetime(raw.index).normalize()
    else:
        logger.warning("Cannot determine observation date for %s", symbol)
        return empty

    raw["expirationDate"] = pd.to_datetime(raw["expirationDate"]).dt.normalize()

    # For each observation date, select the nearest expiry with DTE >= min_dte
    results: dict[pd.Timestamp, float] = {}
    rejected = 0
    for obs_date, group in raw.groupby("obs_date"):
        if min_dte == 0:
            valid = group[group["expirationDate"] >= obs_date]
        else:
            # Strictly after: expiry > obs_date + (min_dte - 1) business days
            valid = group[group["expirationDate"] > obs_date]
        if valid.empty:
            continue
        # Pick the nearest expiry
        nearest_expiry = valid["expirationDate"].min()
        nearest = valid[valid["expirationDate"] == nearest_expiry]
        # Client-side ATM filter: if multiple strikes present, pick closest to 1.0
        if "relativeStrike" in nearest.columns and len(nearest) > 1:
            atm_idx = (nearest["relativeStrike"] - 1.0).abs().idxmin()
            iv_val = float(nearest.loc[atm_idx, "impliedVolatility"])
        else:
            iv_val = nearest["impliedVolatility"].mean()
        # Outlier guard: drop obviously broken Marquee values (see
        # _MIN_PLAUSIBLE_IV comment). Skip the date entirely so downstream
        # reindex yields NaN, signalling "missing" rather than "near-zero IV".
        if not np.isfinite(iv_val) or iv_val < _MIN_PLAUSIBLE_IV:
            rejected += 1
            continue
        results[obs_date] = iv_val

    if rejected:
        logger.warning(
            "Dropped %d %s observation(s) for %s with impliedVolatility < %s "
            "(Marquee data quality issue — values treated as missing).",
            rejected,
            col_name,
            symbol,
            _MIN_PLAUSIBLE_IV,
        )

    if not results:
        return empty

    series = pd.Series(results, name=col_name)
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    return series.sort_index()


def fetch_0dte_iv(
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.Series:
    """Fetch nearest-expiry (0DTE) ATM implied volatility for a symbol.

    Uses Marquee EDRVOL_PERCENT_EXPIRY dataset which provides IV indexed
    by listed expiration date. For SPX, daily expiries exist (Mon-Fri).
    For equities/ETFs, nearest available expiry is used (typically 0-2 days out).

    Returns
    -------
    pd.Series
        Named 'iv_0dte', indexed by observation date. Values in vol points
        (e.g., 18.5 = 18.5% annualized). Empty series on failure.
    """
    series = _fetch_expiry_iv(symbol, start_date, end_date, min_dte=0)
    series.name = "iv_0dte"
    return series


def fetch_1dte_iv(
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.Series:
    """Fetch next-day-expiry (1DTE) ATM implied volatility for a symbol.

    At close of day t, this returns the IV for options expiring on day t+1,
    i.e., the market's expectation of tomorrow's realized volatility.
    This is the correct comparand for a model predicting RV_{t+1}.

    Uses Marquee EDRVOL_PERCENT_EXPIRY dataset with strict > filter
    (expirationDate > observation date).

    Returns
    -------
    pd.Series
        Named 'iv_1dte', indexed by observation date. Values in vol points
        (e.g., 18.5 = 18.5% annualized). Empty series on failure.
    """
    return _fetch_expiry_iv(symbol, start_date, end_date, min_dte=1)


# ---------------------------------------------------------------------------
# GSVIVS01 — Variance Swap Strategy Index
# ---------------------------------------------------------------------------

_GSVIVS_SYMBOL = "midas_.GSVIVS01"
_GSVIVS_CACHE_FILENAME = "gsvivs01.parquet"


def save_gsvivs_cache(data: pd.Series) -> Path:
    """Persist GSVIVS01 index levels to parquet cache.

    Refuses to overwrite an existing cache with a STRICTLY SMALLER series
    (defends against silent truncation when TSDB returns a partial range
    due to entitlement limits or transient connectivity). Logs a warning
    and returns the existing cache path unchanged when shrinkage is
    detected. Equal or larger series replace the cache as usual.

    Parameters
    ----------
    data : pd.Series
        Daily GSVIVS01 index levels with DatetimeIndex.

    Returns
    -------
    Path
        Path to the parquet file (written or preserved).
    """
    out_dir = cross_asset_cache_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _GSVIVS_CACHE_FILENAME
    df = data.to_frame(name="gsvivs01") if isinstance(data, pd.Series) else data

    if path.exists():
        try:
            existing_n = len(pd.read_parquet(path))
        except Exception:
            existing_n = 0
        if existing_n > len(df):
            logger.warning(
                "Refusing to shrink GSVIVS01 cache: existing=%d rows > incoming=%d rows. "
                "Preserving cache at %s",
                existing_n,
                len(df),
                path,
            )
            return path

    df.to_parquet(path, engine="pyarrow")
    logger.info("Saved GSVIVS01 cache: %s (%d rows)", path, len(df))
    return path


def load_gsvivs_cache() -> pd.Series | None:
    """Load cached GSVIVS01 index levels from parquet.

    Returns
    -------
    pd.Series or None
        Named 'gsvivs01' with DatetimeIndex, or None if cache doesn't exist.
    """
    path = cross_asset_cache_dir() / _GSVIVS_CACHE_FILENAME
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    series = df.iloc[:, 0] if isinstance(df, pd.DataFrame) else df
    series.name = "gsvivs01"
    return series


def fetch_gsvivs_index(
    start_date: date | None = None, end_date: date | None = None
) -> pd.Series | None:
    """Fetch GSVIVS01 variance swap strategy index levels.

    Tries local cache first (data/raw/cross_asset/gsvivs01.parquet).
    Falls back to TSDB if cache is missing, and saves to cache on success.

    GSVIVS01 is a MIDAS Managed Portfolio Asset that sells equity variance
    (short volatility via EqOptions + Futures). The index level represents
    cumulative strategy performance since inception (May 2022).

    Parameters
    ----------
    start_date : date, optional
        Start of date range (inclusive). Defaults to 2022-05-01.
    end_date : date, optional
        End of date range (inclusive). Defaults to today.

    Returns
    -------
    pd.Series or None
        Named 'gsvivs01', daily index levels with DatetimeIndex.
        Returns None if both cache and TSDB are unavailable.
    """
    # Try cache first
    cached = load_gsvivs_cache()
    if cached is not None and len(cached) >= 30:
        logger.debug("Loaded GSVIVS01 from cache (%d rows)", len(cached))
        return cached

    # Fall back to TSDB
    if start_date is None:
        start_date = date(2022, 5, 1)
    if end_date is None:
        end_date = date.today()
    try:
        series = _get_tsdb_data(_GSVIVS_SYMBOL, start_date.isoformat(), end_date.isoformat())
    except Exception:
        logger.warning("TSDB unavailable for GSVIVS01 and no cache found")
        return None
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    series.name = "gsvivs01"
    # Save to cache for future offline use
    save_gsvivs_cache(series)
    return series


# ---------------------------------------------------------------------------
# EDRVS — Variance Swap Strike (prev-close 1-DTE from EDRVS_EXPIRY_INTRADAY)
# ---------------------------------------------------------------------------
# The correct IV for GSVIVS01 signal is the *previous day's close* of the
# varswap expiring today. This gives us the market's 0-DTE implied variance
# as of 16:00 ET the day before, available well before the 09:10 ET signal.
#
# Dataset: EDRVS_EXPIRY_INTRADAY (5-min snapshots, per-expiry)
# Extraction: For each trade date T, take the last snapshot from day T-1
#   where expirationDate == T and hour >= 19 UTC (15:00+ ET).
# Unit: fairVolatility is already in annualized vol % (e.g. 12.5 = 12.5%).

_EDRVS_INTRADAY_DATASET_ID = "EDRVS_EXPIRY_INTRADAY"
_EDRVS_CHUNK_DAYS = 7  # Query 1 week at a time (intraday data is large)
_EDRVS_MAX_RETRIES = 3
_EDRVS_RETRY_BACKOFF = (2.0, 4.0, 8.0)
_EDRVS_CACHE_FILENAME = "SPX_edrvs_0dte.parquet"


def _fetch_edrvs_intraday_chunk(
    ds: object,
    start: date,
    end: date,
) -> pd.DataFrame | None:
    """Fetch a single date-range chunk from EDRVS_EXPIRY_INTRADAY with retry."""
    from datetime import datetime

    # Intraday dataset requires datetime start/end (not date)
    start_time = datetime(start.year, start.month, start.day, 13, 0, 0)
    end_time = datetime(end.year, end.month, end.day, 21, 0, 0)

    for attempt in range(_EDRVS_MAX_RETRIES):
        try:
            chunk = ds.get_data(start=start_time, end=end_time, bbid="SPX")
            if chunk is not None and not chunk.empty:
                return chunk
            return None
        except Exception as exc:  # noqa: BLE001
            if attempt < _EDRVS_MAX_RETRIES - 1:
                time.sleep(_EDRVS_RETRY_BACKOFF[attempt])
                logger.debug(
                    "Retry %d/%d for EDRVS_EXPIRY_INTRADAY chunk %s to %s: %s",
                    attempt + 1,
                    _EDRVS_MAX_RETRIES,
                    start,
                    end,
                    exc,
                )
            else:
                logger.warning(
                    "Failed to fetch EDRVS_EXPIRY_INTRADAY chunk %s to %s after %d attempts: %s",
                    start,
                    end,
                    _EDRVS_MAX_RETRIES,
                    exc,
                )
                return None
    return None


def _query_edrvs_intraday(start_date: date, end_date: date) -> pd.DataFrame:
    """Query EDRVS_EXPIRY_INTRADAY for SPX, chunked into weekly requests.

    Returns raw DataFrame from Marquee with DatetimeIndex (UTC) and columns
    including expirationDate, fairVariance, fairVolatility, bbid.
    """
    from datetime import timedelta

    _ensure_expiry_session()

    try:
        from gs_quant.data import Dataset
    except ImportError:
        raise ConnectionError("gs_quant not available. Run on GS desktop with active session.")

    ds = Dataset(_EDRVS_INTRADAY_DATASET_ID)

    chunks: list[pd.DataFrame] = []
    current = start_date
    chunk_size = timedelta(days=_EDRVS_CHUNK_DAYS)

    while current <= end_date:
        chunk_end = min(current + chunk_size - timedelta(days=1), end_date)
        chunk = _fetch_edrvs_intraday_chunk(ds, current, chunk_end)
        if chunk is not None and not chunk.empty:
            chunks.append(chunk)
        current = chunk_end + timedelta(days=1)

    if not chunks:
        return pd.DataFrame()

    result = pd.concat(chunks)
    # Ensure UTC-aware DatetimeIndex
    if not isinstance(result.index, pd.DatetimeIndex):
        result.index = pd.DatetimeIndex(result.index)
    if result.index.tz is None:
        result.index = result.index.tz_localize("UTC")
    return result


def _build_prev_close_1dte(raw: pd.DataFrame) -> pd.Series:
    """Extract prev-day close 1-DTE series from raw intraday data.

    For each trading day T, finds the last snapshot from day T-1 where:
      - expirationDate == T (i.e. the contract expiring today)
      - hour >= 19 UTC (15:00+ ET, near market close)

    This gives us the varswap fair vol for today's 0-DTE session, captured
    at yesterday's close — no lookahead bias, available at 09:10 ET.

    Returns
    -------
    pd.Series
        Named 'iv_vs_0dte', indexed by trade date (the day the signal fires).
        Values in annualized vol % (e.g. 14.9 = 14.9%).
    """
    raw = raw.copy()
    raw["obs_date"] = raw.index.normalize()
    raw["hour"] = raw.index.hour

    # Normalize expirationDate to tz-naive date for comparison
    raw["expirationDate"] = pd.to_datetime(raw["expirationDate"])
    if raw["expirationDate"].dt.tz is not None:
        raw["expirationDate"] = raw["expirationDate"].dt.tz_localize(None)
    raw["expirationDate"] = raw["expirationDate"].dt.normalize()

    # Group by observation date for efficient lookup
    grouped = {k: v for k, v in raw.groupby("obs_date")}
    obs_dates = sorted(grouped.keys())

    results: dict[pd.Timestamp, float] = {}

    for obs_dt in obs_dates:
        day_data = grouped[obs_dt]
        trade_date_naive = obs_dt.tz_localize(None) if obs_dt.tzinfo else obs_dt

        # The *next* business day is the trade date this snapshot serves
        next_bday = trade_date_naive + pd.offsets.BDay(1)
        next_bday_norm = next_bday.normalize()

        # Filter: close window (19-21h UTC = 15:00-17:00 ET) with expiry = next day
        close_mask = (day_data["hour"] >= 19) & (day_data["expirationDate"] == next_bday_norm)
        close_data = day_data[close_mask]

        if not close_data.empty:
            # Take the latest snapshot (closest to actual close)
            fair_vol = float(close_data.iloc[-1]["fairVolatility"])
            if fair_vol > 0:
                results[next_bday_norm] = fair_vol
        else:
            # Fallback: 18h+ with matching expiry (slightly earlier snapshot)
            fallback_mask = (day_data["hour"] >= 18) & (
                day_data["expirationDate"] == next_bday_norm
            )
            fallback_data = day_data[fallback_mask]
            if not fallback_data.empty:
                fair_vol = float(fallback_data.iloc[-1]["fairVolatility"])
                if fair_vol > 0:
                    results[next_bday_norm] = fair_vol

    if not results:
        return pd.Series(dtype=float, name="iv_vs_0dte")

    series = pd.Series(results, name="iv_vs_0dte")
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    return series.sort_index()


def fetch_edrvs_0dte(
    start_date: date,
    end_date: date,
) -> pd.Series:
    """Fetch prev-close 1-DTE variance swap fair vol for SPX.

    Uses EDRVS_EXPIRY_INTRADAY to capture the previous day's close
    (~16:00 ET) of the varswap expiring today. This is the correct IV
    for the GSVIVS01 signal decision at 09:10 ET — no lookahead bias.

    The prev-close 1-DTE captures the market's pricing of today's
    intraday variance as of yesterday's close. It includes overnight
    risk premium but is the most timely available varswap price.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive). We fetch from start_date - 1 bday
        to capture the prev-close for start_date.
    end_date : date
        End of date range (inclusive).

    Returns
    -------
    pd.Series
        Named 'iv_vs_0dte', indexed by trade date.
        Values in vol % (e.g., 14.9 = 14.9% annualized).
        Empty series on failure.
    """
    col_name = "iv_vs_0dte"
    empty = pd.Series(dtype=float, name=col_name)
    empty.index.name = "date"

    # Fetch from one day before start to get prev-close for start_date
    fetch_start = (pd.Timestamp(start_date) - pd.offsets.BDay(1)).date()

    try:
        raw = _query_edrvs_intraday(fetch_start, end_date)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch EDRVS_EXPIRY_INTRADAY for SPX: %s", exc)
        return empty

    if raw is None or raw.empty:
        logger.warning("No EDRVS_EXPIRY_INTRADAY data returned for SPX")
        return empty

    if "fairVolatility" not in raw.columns:
        logger.warning(
            "EDRVS_EXPIRY_INTRADAY missing 'fairVolatility'. Got: %s",
            raw.columns.tolist(),
        )
        return empty

    series = _build_prev_close_1dte(raw)

    # Trim to requested range
    if not series.empty:
        mask = (series.index >= pd.Timestamp(start_date)) & (series.index <= pd.Timestamp(end_date))
        series = series[mask]

    return series


# --- EDRVS cache persistence ---


def save_edrvs_cache(data: pd.Series) -> Path:
    """Persist EDRVS prev-close 1-DTE variance swap strike to parquet cache.

    Parameters
    ----------
    data : pd.Series
        Named 'iv_vs_0dte' with DatetimeIndex.

    Returns
    -------
    Path
        Path to the written parquet file.
    """
    out_dir = iv_cache_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _EDRVS_CACHE_FILENAME
    df = data.to_frame(name="iv_vs_0dte") if isinstance(data, pd.Series) else data
    df.to_parquet(path, engine="pyarrow")
    logger.info("Saved EDRVS prev-close 1-DTE cache: %s (%d rows)", path, len(df))
    return path


def load_edrvs_cache() -> pd.Series | None:
    """Load cached EDRVS prev-close 1-DTE variance swap strike from parquet.

    Returns
    -------
    pd.Series or None
        Named 'iv_vs_0dte' with DatetimeIndex, or None if cache doesn't exist.
    """
    path = iv_cache_dir() / _EDRVS_CACHE_FILENAME
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    series = df.iloc[:, 0] if isinstance(df, pd.DataFrame) else df
    series.name = "iv_vs_0dte"
    return series


# ---------------------------------------------------------------------------
# Execution Kvar (from GSVIVS strip replication)
# ---------------------------------------------------------------------------

_KVAR_CACHE_FILENAME = "gsvivs_kvar_daily.parquet"


def load_kvar_cache() -> pd.Series | None:
    """Load cached 0DTE Kvar (variance-swap strike from GSVIVS strip marks).

    The parquet at data/processed/gsvivs_kvar_daily.parquet contains daily Kvar
    computed via CBOE discrete formula from baseline_risks.price marks (NOT
    execution fill prices -- those do not exist in output.json).
    Unit: annualized vol points (15.0 = 15%).

    NOTE: This is a mark-derived Kvar, not an execution Kvar. The strategy's
    signal fires at 09:10 ET, TWAP execution is 09:30-10:00 ET.
    T = 6.83 hours / 8760 for the CBOE formula.

    Returns
    -------
    pd.Series or None
        Named 'kvar_0dte' with DatetimeIndex, or None if cache doesn't exist.
    """
    path = processed_dir() / _KVAR_CACHE_FILENAME
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    # Prefer 0DTE execution Kvar; fall back to 1DTE baseline if 0DTE unavailable
    if "kvar_0dte" in df.columns and df["kvar_0dte"].notna().any():
        series = df["kvar_0dte"]
        series.name = "kvar_0dte"
    else:
        series = df["kvar_1dte"]
        series.name = "kvar_1dte"
    return series


# ---------------------------------------------------------------------------
# Execution Kvar (true fill prices from output.json)
# ---------------------------------------------------------------------------

_EXEC_KVAR_CACHE_FILENAME = "gsvivs_exec_kvar.parquet"


def save_exec_kvar_cache(data: pd.Series | pd.DataFrame) -> Path:
    """Persist execution Kvar (true fill prices from GSVIVS strip) to parquet.

    The parquet layout stores the effective date explicitly in a ``trade_date``
    column so downstream loaders can recover the series even if a caller writes
    with a default RangeIndex.

    Parameters
    ----------
    data : pd.Series or pd.DataFrame
        Execution-Kvar cache content indexed by trade date.

    Returns
    -------
    Path
        Path to the written parquet file.
    """
    out_dir = processed_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _EXEC_KVAR_CACHE_FILENAME

    df = data.to_frame(name="kvar_vol_pct") if isinstance(data, pd.Series) else data.copy()
    if "kvar_vol_pct" not in df.columns:
        raise ValueError("Execution Kvar cache requires a kvar_vol_pct column")

    index_dates = pd.to_datetime(df.index, errors="coerce")
    if index_dates.isna().any():
        raise ValueError("Execution Kvar cache index must contain valid trade dates")

    df.index = pd.DatetimeIndex(index_dates).normalize()
    df.index.name = "date"
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    out = df.reset_index(names="trade_date")
    out.to_parquet(path, engine="pyarrow", index=False)
    logger.info("Saved execution Kvar cache: %s (%d rows)", path, len(out))
    return path


def load_exec_kvar_cache() -> pd.Series | None:
    """Load cached execution Kvar (true fill prices from GSVIVS strip).

    Returns
    -------
    pd.Series or None
        Named 'kvar_vol_pct' with DatetimeIndex (ann vol %), or None if missing.
    """
    path = processed_dir() / _EXEC_KVAR_CACHE_FILENAME
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    if "kvar_vol_pct" not in df.columns:
        logger.warning("Execution Kvar cache missing kvar_vol_pct column: %s", path)
        return None

    raw_dates = df["trade_date"] if "trade_date" in df.columns else df.index
    parsed_dates = pd.to_datetime(raw_dates, errors="coerce")
    valid_dates = ~parsed_dates.isna()
    if not valid_dates.any():
        logger.warning("Execution Kvar cache has no valid dates: %s", path)
        return None

    df = df.loc[valid_dates].copy()
    df.index = pd.DatetimeIndex(parsed_dates[valid_dates]).normalize()
    df.index.name = "date"
    series = df["kvar_vol_pct"].sort_index()
    if not series.index.is_unique:
        series = series[~series.index.duplicated(keep="last")]
    series.name = "kvar_vol_pct"
    return series


# ---------------------------------------------------------------------------
# EDRVS Morning 1-DTE (09:30 ET snapshot)
# ---------------------------------------------------------------------------

_EDRVS_MORNING_CACHE_FILENAME = "edrvs_morning_1dte.parquet"


def load_edrvs_morning_cache() -> pd.Series | None:
    """Load cached EDRVS morning 1-DTE variance swap strike.

    This is the 09:30 ET (13:30 UTC) snapshot of the EDRVS fairVolatility
    for the nearest expiry (typically next business day). Unit: annualized
    vol points, calendar-day convention.

    Returns
    -------
    pd.Series or None
        Named 'iv_morning_1dte' with DatetimeIndex, or None if missing.
    """
    path = processed_dir() / _EDRVS_MORNING_CACHE_FILENAME
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    series = df["iv_morning_1dte"]
    series.name = "iv_morning_1dte"
    return series
