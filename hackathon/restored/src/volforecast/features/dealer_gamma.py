"""Dealer Gamma (GEX) feature layer — loads SPX GEX data and broadcasts to panel.

This is an SPX-only market-wide signal, broadcast to every symbol via
index-based reindex (same pattern as VIX/VVIX in IVSurfaceLayer).

Config example:
    feature_layers: [iv_surface, har_core, asymmetry, options, dealer_gamma]
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from volforecast.data.gex_ingest import load_gex_cache
from volforecast.data.options_oi import build_gex_features
from volforecast.registry import register_feature_layer

logger = logging.getLogger(__name__)


@register_feature_layer("dealer_gamma")
class DealerGammaLayer:
    """Load SPX dealer gamma exposure and produce ML features.

    Loads from data/raw/options_oi/spx_gex_daily.parquet via load_gex_cache().
    Computes 5 features via build_gex_features():
        gex_sign_d, gex_zscore_d, gex_quintile_d, gex_regime_d, gex_momentum_d

    SPX-only signal broadcast to all symbols — no per-symbol variation.
    """

    name = "dealer_gamma"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict | None = None,
    ) -> pd.DataFrame:
        result = pd.DataFrame(index=daily_data.index)

        # Load the GEX cache (SPX-only, market-wide signal)
        gex_raw = load_gex_cache()
        if gex_raw.empty:
            logger.debug("DealerGammaLayer: no GEX cache available, returning NaN")
            return result

        # Ensure date index
        if "date" in gex_raw.columns:
            gex_raw = gex_raw.set_index("date")
        gex_raw.index = pd.DatetimeIndex(gex_raw.index)

        # build_gex_features expects columns: gex_net, gex_sign, gex_zscore
        # The raw cache has gex_net, gex_sign but may not have gex_zscore
        # Check and compute if needed
        if "gex_zscore" not in gex_raw.columns and "gex_net" in gex_raw.columns:
            gex_raw["gex_zscore"] = (
                gex_raw["gex_net"] - gex_raw["gex_net"].rolling(63).mean()
            ) / gex_raw["gex_net"].rolling(63).std()
        if "gex_sign" not in gex_raw.columns and "gex_net" in gex_raw.columns:
            gex_raw["gex_sign"] = np.sign(gex_raw["gex_net"])

        # Build the 5 ML features
        gex_features = build_gex_features(gex_raw)
        if gex_features.empty:
            logger.debug("DealerGammaLayer: build_gex_features returned empty")
            return result

        # Broadcast to panel: reindex to daily_data.index (no forward-fill)
        for col in gex_features.columns:
            result[col] = gex_features[col].reindex(daily_data.index)

        # --- GEX interaction features ---
        # Computed when options/iv_surface columns are available in daily_data
        # (layer ordering: iv_surface → options → dealer_gamma ensures this).
        gex_z = result.get("gex_zscore_d")
        gex_regime = result.get("gex_regime_d")

        if gex_z is not None and gex_z.notna().any():
            if "iv_term_slope_d" in daily_data.columns:
                result["gex_x_iv_term_slope"] = gex_z * daily_data["iv_term_slope_d"]
            if "vrp_d" in daily_data.columns:
                result["gex_x_vrp"] = gex_z * daily_data["vrp_d"]

        if gex_regime is not None and gex_regime.notna().any():
            if "iv_rv_gap_d" in daily_data.columns:
                result["gex_x_iv_rv_gap"] = gex_regime * daily_data["iv_rv_gap_d"]
            if "vix" in daily_data.columns:
                result["gex_x_vix"] = gex_regime * daily_data["vix"]

        return result
