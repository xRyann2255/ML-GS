"""Cross-asset signal features (forward-looking implied vol levels + changes).

Loads pre-computed cross-asset implied vols and spreads from data/raw/cross_asset/
and produces both LEVEL and MOMENTUM features.

Ablation (2026-06-05) showed:
- LEVELS dominate for h=1: rate_vol +139 bps, credit_cdx +85 bps, fx_iv +65 bps
- CHANGES/momentum add noise on top of levels
- The old CrossAssetLayer (compute_rolling_vol on already-IV data) was broken

Features produced (levels — log-transformed for scale):
    - xasset_rate_vol, xasset_credit_cdx, xasset_fx_usdjpy,
      xasset_fx_eurusd, xasset_gvz

Features produced (momentum — 1d/5d changes + z-score):
    - d_fx_iv_usdjpy_1d, d_fx_iv_usdjpy_5d, z_fx_iv_usdjpy
    - d_fx_iv_eurusd_1d, d_fx_iv_eurusd_5d, z_fx_iv_eurusd
    - d_credit_cdx_1d, d_credit_cdx_5d, z_credit_cdx
    - d_rate_vol_1d, d_rate_vol_5d, z_rate_vol
    - d_yield_slope_1d, d_yield_slope_5d, z_yield_slope
    - d_gold_vol_1d, d_gold_vol_5d, z_gold_vol
    - d_oil_vol_1d, d_oil_vol_5d, z_oil_vol
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from volforecast.registry import register_feature_layer
from volforecast.utils.paths import cross_asset_cache_dir

logger = logging.getLogger(__name__)

# Z-score window (20 trading days = ~1 month)
_ZSCORE_WINDOW = 20

# Top cross-asset signals (ablation 2026-06-05, SPY h=1 OLS):
# rate_vol_1y10y: +139 bps, credit_vol_cdx: +85 bps,
# fx_iv_usdjpy: +65 bps, fx_iv_eurusd: +65 bps, gvz: +24 bps
_LEVEL_SIGNALS = {
    "xasset_rate_vol": ("rates", "rate_vol_1y10y"),
    "xasset_credit_cdx": ("credit", "credit_vol_cdx"),
    "xasset_fx_usdjpy": ("fx", "fx_iv_usdjpy"),
    "xasset_fx_eurusd": ("fx", "fx_iv_eurusd"),
    "xasset_gvz": ("commodity", "gvz"),
}


def _compute_momentum_features(
    series: pd.Series,
    name: str,
) -> pd.DataFrame:
    """Compute 1d change, 5d change, and z-score for a single series.

    Parameters
    ----------
    series : pd.Series
        Raw daily series (e.g., FX implied vol, credit spread).
    name : str
        Feature name prefix.

    Returns
    -------
    pd.DataFrame
        Three columns: d_{name}_1d, d_{name}_5d, z_{name}.
    """
    result = pd.DataFrame(index=series.index)
    result[f"d_{name}_1d"] = series.diff(1)
    result[f"d_{name}_5d"] = series.diff(5)

    rolling_mean = series.rolling(_ZSCORE_WINDOW).mean()
    rolling_std = series.rolling(_ZSCORE_WINDOW).std()
    result[f"z_{name}"] = (series - rolling_mean) / rolling_std

    return result


def _load_cross_asset_parquets() -> dict[str, pd.DataFrame]:
    """Load raw cross-asset parquets from cache."""
    cache_dir = cross_asset_cache_dir()
    data = {}

    files = {
        "rates": "rates.parquet",
        "fx": "fx_vol.parquet",
        "credit": "credit.parquet",
        "commodity": "commodity.parquet",
    }

    for key, filename in files.items():
        path = cache_dir / filename
        if path.exists():
            data[key] = pd.read_parquet(path)
        else:
            logger.debug("Cross-asset file not found: %s", path)

    return data


@register_feature_layer("cross_asset_momentum")
class CrossAssetMomentumLayer:
    """Cross-asset signal features (levels + momentum).

    Produces:
    - Log-level features for top 5 signals (xasset_*)
    - Daily/weekly changes and z-scores for all signals (d_*, z_*)

    Does NOT require context dict — loads data directly from cache.
    """

    name = "cross_asset_momentum"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Compute cross-asset level + momentum features."""
        raw = _load_cross_asset_parquets()

        if not raw:
            logger.warning(
                "No cross-asset data found. Run `vol ingest-xasset`. Returning empty DataFrame."
            )
            return pd.DataFrame(index=daily_data.index)

        result = pd.DataFrame(index=daily_data.index)

        # --- LEVEL features (log-transformed, top signals from ablation) ---
        for feat_name, (source_key, col_name) in _LEVEL_SIGNALS.items():
            if source_key in raw:
                source_df = raw[source_key].reindex(daily_data.index)
                if col_name in source_df.columns:
                    series = source_df[col_name]
                    result[feat_name] = np.log(series.clip(lower=1e-10))

        # --- MOMENTUM features (changes + z-scores) ---

        # FX implied vol
        if "fx" in raw:
            fx = raw["fx"].reindex(daily_data.index)
            if "fx_iv_usdjpy" in fx.columns:
                feats = _compute_momentum_features(fx["fx_iv_usdjpy"], "fx_iv_usdjpy")
                result = pd.concat([result, feats], axis=1)
            if "fx_iv_eurusd" in fx.columns:
                feats = _compute_momentum_features(fx["fx_iv_eurusd"], "fx_iv_eurusd")
                result = pd.concat([result, feats], axis=1)

        # Credit spread
        if "credit" in raw:
            credit = raw["credit"].reindex(daily_data.index)
            if "credit_vol_cdx" in credit.columns:
                feats = _compute_momentum_features(credit["credit_vol_cdx"], "credit_cdx")
                result = pd.concat([result, feats], axis=1)

        # Rate vol + yield slope
        if "rates" in raw:
            rates = raw["rates"].reindex(daily_data.index)
            if "rate_vol_1y10y" in rates.columns:
                feats = _compute_momentum_features(rates["rate_vol_1y10y"], "rate_vol")
                result = pd.concat([result, feats], axis=1)
            if "yield_slope_10y5y" in rates.columns:
                feats = _compute_momentum_features(rates["yield_slope_10y5y"], "yield_slope")
                result = pd.concat([result, feats], axis=1)

        # Commodity vol
        if "commodity" in raw:
            comm = raw["commodity"].reindex(daily_data.index)
            if "gold_vol" in comm.columns:
                feats = _compute_momentum_features(comm["gold_vol"], "gold_vol")
                result = pd.concat([result, feats], axis=1)
            if "oil_vol" in comm.columns:
                feats = _compute_momentum_features(comm["oil_vol"], "oil_vol")
                result = pd.concat([result, feats], axis=1)

        n_features = len(result.columns)
        logger.info("CrossAssetMomentumLayer produced %d features", n_features)
        return result
