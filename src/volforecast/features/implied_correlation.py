"""Implied correlation feature layer — options-implied forward-looking correlation.

This layer provides OPTIONS-IMPLIED correlation features from Marquee EDR_INDEX
datasets. Unlike the ``realized_correlation`` layer (which computes
backward-looking panel correlation from OHLCV returns), this layer uses
market-implied forward-looking correlation from SPX index options.

Correlation risk premium (implied > realized) signals systemic risk repricing
and is a known predictor of future volatility at monthly horizons.

Features produced (market-wide signal — same value for all symbols on a given
date):

    implied_corr_spx_1m   — SPX 1m implied correlation
    realized_corr_spx_1m  — SPX 1m realized correlation
    corr_risk_premium     — implied minus realized
    dispersion_signal     — average member implied vol
    corr_momentum         — daily change in implied correlation
    corr_zscore           — 60-day z-score of implied correlation
"""

from __future__ import annotations

import logging
from functools import lru_cache

import pandas as pd

from volforecast.registry import register_feature_layer
from volforecast.utils.paths import correlation_cache_dir

logger = logging.getLogger(__name__)

_COLUMNS = [
    "implied_corr_spx_1m",
    "realized_corr_spx_1m",
    "corr_risk_premium",
    "dispersion_signal",
    "corr_momentum",
    "corr_zscore",
]


@lru_cache(maxsize=1)
def _read_correlation_parquet(cache_key: str) -> pd.DataFrame:
    """Read spx_correlation.parquet from cache dir. Cached to avoid repeated I/O."""
    from pathlib import Path

    path = Path(cache_key) / "spx_correlation.parquet"
    if not path.exists():
        logger.warning("implied_correlation: parquet not found at %s", path)
        return pd.DataFrame(columns=_COLUMNS)
    try:
        df = pd.read_parquet(path)
    except Exception as exc:
        logger.warning("implied_correlation: failed to read %s — %s", path, exc)
        return pd.DataFrame(columns=_COLUMNS)
    # Ensure only expected columns are returned
    missing = [c for c in _COLUMNS if c not in df.columns]
    if missing:
        logger.warning("implied_correlation: missing columns %s", missing)
        return pd.DataFrame(columns=_COLUMNS)
    return df[_COLUMNS]


@register_feature_layer("implied_correlation")
class ImpliedCorrelationLayer:
    """Options-implied correlation features from pre-computed parquet cache."""

    name = "implied_correlation"

    def compute(self, daily_data: pd.DataFrame, *, context: dict | None = None) -> pd.DataFrame:
        """Reindex cached implied correlation data onto daily_data.index with ffill."""
        cache_key = str(correlation_cache_dir())
        raw = _read_correlation_parquet(cache_key)

        if raw.empty:
            return pd.DataFrame(columns=_COLUMNS)

        # Reindex onto the target date index with forward-fill for gaps
        result = raw.reindex(daily_data.index, method="ffill")
        return result
