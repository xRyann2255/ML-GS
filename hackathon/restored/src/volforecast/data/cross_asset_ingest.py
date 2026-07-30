"""Cross-asset data ingestion for Layer 4 features.

Fetches rates, FX vol, credit, and commodity data from TSDB, edrvol,
and Marquee Dataset API. Writes 4 parquet files to data/raw/cross_asset/.

Key functions:
    ingest_rates      — Treasury yields + swaption vol + TLT realized vol
    ingest_fx_vol     — FX implied vol (Marquee) + DXY level
    ingest_credit     — Credit implied vol + ETF IV + stress proxies
    ingest_commodity  — Commodity implied vol + GVZ + ETF realized vol
    load_cross_asset_context — Read cached parquets for CrossAssetLayer
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

from volforecast.constants import (
    DXY_TSDB_SYMBOL,
    GVZ_TSDB_SYMBOL,
    MARQUEE_COMMODITY_VOL,
    MARQUEE_CREDIT_VOL,
    MARQUEE_FX_VOL,
    MARQUEE_RATE_VOL,
    XASSET_ETF_PRICE,
)
from volforecast.utils.paths import cross_asset_cache_dir

logger = logging.getLogger(__name__)


class IngestResult(NamedTuple):
    """Result from a sub-group ingestion."""

    path: Path
    rows: int
    skipped: bool


# ---------------------------------------------------------------------------
# Index normalization
# ---------------------------------------------------------------------------


def _normalize_index(s: pd.Series) -> pd.Series:
    """Normalize a Series index to tz-naive midnight timestamps.

    Prevents duplicate rows when combining Series from sources with
    different time components (Marquee uses noon, TSDB uses midnight).
    """
    if hasattr(s.index, "tz") and s.index.tz is not None:
        s = s.copy()
        s.index = s.index.tz_localize(None)
    if hasattr(s.index, "normalize"):
        s = s.copy()
        s.index = s.index.normalize()
    return s


def _build_aligned_df(parts: dict[str, pd.Series]) -> pd.DataFrame:
    """Build DataFrame from dict of Series, deduplicating by date."""
    normalized = {k: _normalize_index(v) for k, v in parts.items()}
    df = pd.DataFrame(normalized)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    # Deduplicate: keep first non-NaN row per date
    if df.index.duplicated().any():
        df = df.groupby(level=0).first()
    return df.sort_index()


# ---------------------------------------------------------------------------
# Cache check
# ---------------------------------------------------------------------------


def _cache_covers_range(filepath: Path, start: date, end: date) -> bool:
    """Check if a cached parquet covers the requested date range."""
    if not filepath.exists():
        return False
    try:
        df = pd.read_parquet(filepath)
    except Exception:  # noqa: BLE001
        return False
    if df.empty:
        return False
    idx = df.index
    if hasattr(idx, "date"):
        cached_start = idx.min().date()
        cached_end = idx.max().date()
    else:
        cached_start = idx.min()
        cached_end = idx.max()
    return cached_start <= start and cached_end >= end


# ---------------------------------------------------------------------------
# TSDB helpers (thin wrappers for testability)
# ---------------------------------------------------------------------------


def _fetch_tsdb_series(symbol: str, start: date, end: date) -> pd.Series:
    """Fetch a single TSDB time series."""
    from volforecast.data.tsdb import _get_tsdb_data

    return _get_tsdb_data(symbol, start.isoformat(), end.isoformat())


def _fetch_treasury_yields(start: date, end: date) -> pd.DataFrame:
    """Fetch treasury data (5y/10y/30y) from TSDB.

    Returns DataFrame with columns: yield_5y, yield_10y, yield_30y.
    Note: TSDB returns bond prices, not yields. Naming convention
    retained for downstream feature compatibility.
    """
    from volforecast.data.tsdb import fetch_treasury_yields

    df = fetch_treasury_yields(start, end, tenors=["5y", "10y", "30y"])
    if df.empty:
        return df
    # Rename tenor labels to yield_* for downstream compatibility
    df = df.rename(columns={"5y": "yield_5y", "10y": "yield_10y", "30y": "yield_30y"})
    return df


def _fetch_etf_prices(symbols: list[str], start: date, end: date) -> pd.DataFrame:
    """Fetch adjusted close prices for ETFs from TSDB."""
    from volforecast.data.tsdb import _get_tsdb_data

    series_list = []
    for ticker in symbols:
        ric = XASSET_ETF_PRICE[ticker]
        sym = f"eqpad_{ric}@close.adj.allincdiv"
        try:
            s = _get_tsdb_data(sym, start.isoformat(), end.isoformat())
            s.name = ticker
            series_list.append(s)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch %s: %s", ticker, exc)
    if not series_list:
        return pd.DataFrame()
    df = pd.concat(series_list, axis=1)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df


def _fetch_etf_iv(ticker: str, start: date, end: date) -> pd.Series:
    """Fetch 1m ATM implied vol for an ETF from edrvol namespace."""
    from volforecast.data.edrvol import fetch_edrvol

    df = fetch_edrvol(ticker, start, end, fields=["1matms"])
    if df is not None and not df.empty and "iv_1m_atm" in df.columns:
        return df["iv_1m_atm"]
    return pd.Series(dtype="float64", name=f"{ticker.lower()}_iv")


def _fetch_marquee_series(
    dataset_id: str,
    start: date,
    end: date,
    value_col: str,
    post_filter: dict | None = None,
    **query_params: object,
) -> pd.Series:
    """Fetch a Marquee dataset time series with retry."""
    from volforecast.data.marquee import fetch_dataset_timeseries

    return fetch_dataset_timeseries(
        dataset_id,
        start,
        end,
        value_col=value_col,
        post_filter=post_filter,
        **query_params,
    )


# ---------------------------------------------------------------------------
# Sub-group ingest functions
# ---------------------------------------------------------------------------


def ingest_rates(start_date: date, end_date: date, force: bool = False) -> IngestResult:
    """Ingest rates data: treasury yields + swaption vol + TLT RV.

    Output: data/raw/cross_asset/rates.parquet
    Columns: yield_5y, yield_10y, yield_30y, yield_slope_10y5y,
             rate_vol_1y10y, tlt_rv_22d
    """
    outpath = cross_asset_cache_dir() / "rates.parquet"
    if not force and _cache_covers_range(outpath, start_date, end_date):
        return IngestResult(outpath, 0, skipped=True)

    parts: dict[str, pd.Series] = {}

    # Treasury yields (5y/10y/30y from edrvol module)
    yields = _fetch_treasury_yields(start_date, end_date)
    if not yields.empty:
        for col in yields.columns:
            # Map column names (edrvol returns yield_5y, yield_10y, yield_30y)
            parts[col] = yields[col]

    # Derived: yield slope
    if "yield_10y" in parts and "yield_5y" in parts:
        parts["yield_slope_10y5y"] = parts["yield_10y"] - parts["yield_5y"]

    # Swaption vol (1y into 10y) from Marquee
    try:
        cfg = MARQUEE_RATE_VOL
        rate_vol = _fetch_marquee_series(
            cfg["dataset_id"],
            start_date,
            end_date,
            value_col=cfg["value_col"],
            **cfg["query"],
        )
        if not rate_vol.empty:
            rate_vol.name = "rate_vol_1y10y"
            parts["rate_vol_1y10y"] = rate_vol
    except Exception as exc:  # noqa: BLE001
        logger.warning("Marquee rate vol failed (non-fatal): %s", exc)

    # TLT realized vol (rates vol proxy)
    tlt_prices = _fetch_etf_prices(["TLT"], start_date, end_date)
    if not tlt_prices.empty and "TLT" in tlt_prices.columns:
        from volforecast.features.cross_asset import compute_rolling_vol

        tlt_rv = compute_rolling_vol(tlt_prices["TLT"], window=22)
        tlt_rv.name = "tlt_rv_22d"
        parts["tlt_rv_22d"] = tlt_rv

    if not parts:
        return IngestResult(outpath, 0, skipped=False)

    df = _build_aligned_df(parts)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(outpath)
    return IngestResult(outpath, len(df), skipped=False)


def ingest_fx_vol(start_date: date, end_date: date, force: bool = False) -> IngestResult:
    """Ingest FX vol data: implied vol (Marquee) + DXY level.

    Output: data/raw/cross_asset/fx_vol.parquet
    Columns: fx_iv_usdjpy, fx_iv_eurusd, dollar_strength
    """
    outpath = cross_asset_cache_dir() / "fx_vol.parquet"
    if not force and _cache_covers_range(outpath, start_date, end_date):
        return IngestResult(outpath, 0, skipped=True)

    parts: dict[str, pd.Series] = {}

    # FX implied vol from Marquee
    cfg = MARQUEE_FX_VOL
    for pair, params in cfg["pairs"].items():
        try:
            iv = _fetch_marquee_series(
                cfg["dataset_id"],
                start_date,
                end_date,
                value_col=cfg["value_col"],
                **params,
            )
            if not iv.empty:
                col_name = f"fx_iv_{pair.lower()}"
                iv.name = col_name
                parts[col_name] = iv
        except Exception as exc:  # noqa: BLE001
            logger.warning("Marquee FX vol %s failed: %s", pair, exc)

    # DXY (dollar strength index)
    try:
        dxy = _fetch_tsdb_series(DXY_TSDB_SYMBOL, start_date, end_date)
        if not dxy.empty:
            dxy.name = "dollar_strength"
            parts["dollar_strength"] = dxy
    except Exception as exc:  # noqa: BLE001
        logger.warning("DXY fetch failed: %s", exc)

    if not parts:
        return IngestResult(outpath, 0, skipped=False)

    df = _build_aligned_df(parts)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(outpath)
    return IngestResult(outpath, len(df), skipped=False)


def ingest_credit(start_date: date, end_date: date, force: bool = False) -> IngestResult:
    """Ingest credit data: CDX vol + ETF IV + stress proxies.

    Output: data/raw/cross_asset/credit.parquet
    Columns: credit_vol_cdx, hyg_iv, credit_stress, eem_iv, xlf_iv, em_risk
    """
    outpath = cross_asset_cache_dir() / "credit.parquet"
    if not force and _cache_covers_range(outpath, start_date, end_date):
        return IngestResult(outpath, 0, skipped=True)

    parts: dict[str, pd.Series] = {}

    # CDX implied vol from Marquee
    try:
        cfg = MARQUEE_CREDIT_VOL
        cdx = _fetch_marquee_series(
            cfg["dataset_id"],
            start_date,
            end_date,
            value_col=cfg["value_col"],
            post_filter=cfg["post_filter"],
            **cfg["query"],
        )
        if not cdx.empty:
            cdx.name = "credit_vol_cdx"
            parts["credit_vol_cdx"] = cdx
    except Exception as exc:  # noqa: BLE001
        logger.warning("Marquee CDSIVOL failed: %s", exc)

    # ETF implied vols
    for ticker in ("HYG", "EEM", "XLF"):
        try:
            iv = _fetch_etf_iv(ticker, start_date, end_date)
            if not iv.empty:
                col_name = f"{ticker.lower()}_iv"
                iv.name = col_name
                parts[col_name] = iv
        except Exception as exc:  # noqa: BLE001
            logger.warning("edrvol %s failed: %s", ticker, exc)

    # Credit stress: HYG - TLT return spread
    etf_prices = _fetch_etf_prices(["HYG", "TLT", "EEM"], start_date, end_date)
    if not etf_prices.empty:
        if "HYG" in etf_prices.columns and "TLT" in etf_prices.columns:
            hyg_ret = np.log(etf_prices["HYG"] / etf_prices["HYG"].shift(1))
            tlt_ret = np.log(etf_prices["TLT"] / etf_prices["TLT"].shift(1))
            credit_stress = hyg_ret - tlt_ret
            credit_stress.name = "credit_stress"
            parts["credit_stress"] = credit_stress

        if "EEM" in etf_prices.columns:
            em_risk = np.log(etf_prices["EEM"] / etf_prices["EEM"].shift(1))
            em_risk.name = "em_risk"
            parts["em_risk"] = em_risk

    if not parts:
        return IngestResult(outpath, 0, skipped=False)

    df = _build_aligned_df(parts)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(outpath)
    return IngestResult(outpath, len(df), skipped=False)


def ingest_commodity(start_date: date, end_date: date, force: bool = False) -> IngestResult:
    """Ingest commodity data: implied vol (Marquee + edrvol) + realized vol.

    Output: data/raw/cross_asset/commodity.parquet
    Columns: commodity_vol_cl, gvz, gld_iv, gold_vol, oil_vol
    """
    outpath = cross_asset_cache_dir() / "commodity.parquet"
    if not force and _cache_covers_range(outpath, start_date, end_date):
        return IngestResult(outpath, 0, skipped=True)

    parts: dict[str, pd.Series] = {}

    # WTI crude implied vol from Marquee
    try:
        cfg = MARQUEE_COMMODITY_VOL
        cl_vol = _fetch_marquee_series(
            cfg["dataset_id"],
            start_date,
            end_date,
            value_col=cfg["value_col"],
            **cfg["query"],
        )
        if not cl_vol.empty:
            cl_vol.name = "commodity_vol_cl"
            parts["commodity_vol_cl"] = cl_vol
    except Exception as exc:  # noqa: BLE001
        logger.warning("Marquee COMMODVOL failed: %s", exc)

    # GVZ (CBOE Gold Volatility Index)
    try:
        gvz = _fetch_tsdb_series(GVZ_TSDB_SYMBOL, start_date, end_date)
        if not gvz.empty:
            gvz.name = "gvz"
            parts["gvz"] = gvz
    except Exception as exc:  # noqa: BLE001
        logger.warning("GVZ fetch failed: %s", exc)

    # GLD implied vol
    try:
        gld_iv = _fetch_etf_iv("GLD", start_date, end_date)
        if not gld_iv.empty:
            gld_iv.name = "gld_iv"
            parts["gld_iv"] = gld_iv
    except Exception as exc:  # noqa: BLE001
        logger.warning("edrvol GLD failed: %s", exc)

    # Realized vol from ETF prices (GLD, USO)
    etf_prices = _fetch_etf_prices(["GLD", "USO"], start_date, end_date)
    if not etf_prices.empty:
        from volforecast.features.cross_asset import compute_rolling_vol

        if "GLD" in etf_prices.columns:
            gold_vol = compute_rolling_vol(etf_prices["GLD"], window=22)
            gold_vol.name = "gold_vol"
            parts["gold_vol"] = gold_vol
        if "USO" in etf_prices.columns:
            oil_vol = compute_rolling_vol(etf_prices["USO"], window=22)
            oil_vol.name = "oil_vol"
            parts["oil_vol"] = oil_vol

    if not parts:
        return IngestResult(outpath, 0, skipped=False)

    df = _build_aligned_df(parts)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(outpath)
    return IngestResult(outpath, len(df), skipped=False)


# ---------------------------------------------------------------------------
# Context loader (for CrossAssetLayer integration)
# ---------------------------------------------------------------------------


def load_cross_asset_context(
    start: date | None = None,
    end: date | None = None,
) -> dict[str, pd.DataFrame]:
    """Load cached cross-asset parquets and return context dict.

    Returns a dict with keys matching CrossAssetLayer.compute() expectations:
      - treasury: yield columns
      - fx: FX vol columns
      - commodity: commodity vol columns
      - credit: credit columns

    The VIX series (needed by CrossAssetLayer) is loaded from the IV cache
    (produced by ``vol ingest-iv``).

    Raises
    ------
    FileNotFoundError
        If no cross-asset parquets exist (run ``vol ingest-xasset`` first).
    """
    cache_dir = cross_asset_cache_dir()
    context: dict[str, pd.DataFrame] = {}

    files = {
        "treasury": "rates.parquet",
        "fx": "fx_vol.parquet",
        "credit": "credit.parquet",
        "commodity": "commodity.parquet",
    }

    found_any = False
    for key, filename in files.items():
        path = cache_dir / filename
        if path.exists():
            df = pd.read_parquet(path)
            if start is not None:
                df = df[df.index >= pd.Timestamp(start)]
            if end is not None:
                df = df[df.index <= pd.Timestamp(end)]
            context[key] = df
            found_any = True
        else:
            context[key] = pd.DataFrame()

    if not found_any:
        raise FileNotFoundError(
            f"No cross-asset data found in {cache_dir}. "
            "Run `vol ingest-xasset` to fetch cross-asset data first."
        )

    # Load VIX from IV cache (produced by vol ingest-iv)
    from volforecast.utils.paths import iv_cache_dir

    vix_path = iv_cache_dir() / "_VIX.parquet"
    if vix_path.exists():
        vix_df = pd.read_parquet(vix_path)
        if start is not None:
            vix_df = vix_df[vix_df.index >= pd.Timestamp(start)]
        if end is not None:
            vix_df = vix_df[vix_df.index <= pd.Timestamp(end)]
        context["vix"] = vix_df
    else:
        context["vix"] = pd.DataFrame()

    return context
