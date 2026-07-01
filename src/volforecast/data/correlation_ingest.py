"""Correlation data ingestion for Layer 7 features.

Fetches SPX implied/realized correlation and average member implied vol
from Marquee Dataset API. Derives risk premium, momentum, and z-score
signals. Writes a single parquet to data/raw/correlation/.

Key functions:
    ingest_correlation       — Fetch and derive all correlation features
    load_correlation_context — Read cached parquet for downstream layers
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from volforecast.constants import (
    CORR_ZSCORE_WINDOW,
    MARQUEE_AVG_IMPLIED_VOL,
    MARQUEE_IMPLIED_CORR,
    MARQUEE_REALIZED_CORR,
)
from volforecast.utils.paths import correlation_cache_dir

logger = logging.getLogger(__name__)


class IngestResult(NamedTuple):
    """Result from correlation ingestion."""

    path: Path
    rows: int
    skipped: bool


# ---------------------------------------------------------------------------
# Index normalization
# ---------------------------------------------------------------------------


def _normalize_index(s: pd.Series) -> pd.Series:
    """Normalize a Series index to tz-naive midnight timestamps."""
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
# Marquee fetch helper
# ---------------------------------------------------------------------------


def _fetch_marquee_series(
    dataset_id: str,
    start: date,
    end: date,
    value_col: str,
    **query_params: object,
) -> pd.Series:
    """Fetch a Marquee dataset time series with retry."""
    from volforecast.data.marquee import fetch_dataset_timeseries

    return fetch_dataset_timeseries(
        dataset_id,
        start,
        end,
        value_col=value_col,
        **query_params,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_correlation(
    start_date: date, end_date: date, force: bool = False,
    on_step: object = None,
) -> IngestResult:
    """Ingest SPX correlation data and derived features.

    Output: data/raw/correlation/spx_correlation.parquet
    Columns: implied_corr_spx_1m, realized_corr_spx_1m, corr_risk_premium,
             dispersion_signal, corr_momentum, corr_zscore

    Parameters
    ----------
    on_step : callable, optional
        Called with a message string after each fetch/derive step completes.
    """
    outpath = correlation_cache_dir() / "spx_correlation.parquet"

    if not force and _cache_covers_range(outpath, start_date, end_date):
        return IngestResult(outpath, 0, skipped=True)

    _step = on_step if callable(on_step) else lambda msg: None

    # Fetch implied correlation
    logger.info("Fetching implied correlation (EDR_INDEX_IMPLIEDCORR)...")
    implied_corr = _fetch_marquee_series(
        MARQUEE_IMPLIED_CORR["dataset_id"],
        start_date,
        end_date,
        MARQUEE_IMPLIED_CORR["value_col"],
        **MARQUEE_IMPLIED_CORR["query"],
    )
    _step(f"implied_corr: {len(implied_corr)} rows")

    # Fetch realized correlation
    logger.info("Fetching realized correlation (EDR_INDEX_REALIZEDCORR)...")
    realized_corr = _fetch_marquee_series(
        MARQUEE_REALIZED_CORR["dataset_id"],
        start_date,
        end_date,
        MARQUEE_REALIZED_CORR["value_col"],
        **MARQUEE_REALIZED_CORR["query"],
    )
    _step(f"realized_corr: {len(realized_corr)} rows")

    # Fetch average member implied vol (dispersion signal)
    logger.info("Fetching average member IV (EDR_INDEX_AVERAGE_IMPLIED_VOL)...")
    avg_member_iv = _fetch_marquee_series(
        MARQUEE_AVG_IMPLIED_VOL["dataset_id"],
        start_date,
        end_date,
        MARQUEE_AVG_IMPLIED_VOL["value_col"],
        **MARQUEE_AVG_IMPLIED_VOL["query"],
    )
    _step(f"avg_member_iv: {len(avg_member_iv)} rows")

    # Derive features from implied correlation
    corr_risk_premium = implied_corr - realized_corr
    corr_momentum = implied_corr.diff(1)
    rolling_mean = implied_corr.rolling(CORR_ZSCORE_WINDOW).mean()
    rolling_std = implied_corr.rolling(CORR_ZSCORE_WINDOW).std()
    corr_zscore = (implied_corr - rolling_mean) / rolling_std

    # Build aligned DataFrame (partial data OK — NaN for missing series)
    parts: dict[str, pd.Series] = {
        "implied_corr_spx_1m": implied_corr,
        "realized_corr_spx_1m": realized_corr,
        "corr_risk_premium": corr_risk_premium,
        "dispersion_signal": avg_member_iv,
        "corr_momentum": corr_momentum,
        "corr_zscore": corr_zscore,
    }

    df = _build_aligned_df(parts)

    # Write output
    outpath.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(outpath)
    _step(f"derived + wrote {len(df)} rows")
    logger.info("Wrote %d rows to %s", len(df), outpath)

    return IngestResult(outpath, len(df), skipped=False)


def load_correlation_context() -> pd.DataFrame:
    """Read cached correlation parquet. Returns empty DataFrame if missing."""
    filepath = correlation_cache_dir() / "spx_correlation.parquet"
    if not filepath.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(filepath)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to read %s, returning empty DataFrame", filepath)
        return pd.DataFrame()
