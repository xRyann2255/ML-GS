"""Tree expansion feature layer for gradient-boosted models.

Applies triple_expand (level, change, z-score) to all base features
from prior layers, giving tree models richer split surfaces. This layer
should appear AFTER the base layers it expands (har_core, asymmetry, noise_robust).

HAR OLS models do NOT use this layer — it is LightGBM/XGBoost-only.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from volforecast.features.expansion import triple_expand
from volforecast.registry import register_feature_layer

# Columns matching these prefixes are continuous time-series features
# suitable for change/zscore expansion. Calendar dummies, categoricals,
# and proximity counters are excluded — trees split on them directly.
_EXPANDABLE_PREFIXES = (
    "log_rv_",
    "log_rs_",
    "log_jump_",
    "log_cont_",
    "sqrt_rq",
    "rq_rv_interaction",
    "signed_jump",
    "signed_return",
    "abs_ret",
    "ret_5d",
    "vol_anomaly",
    "vix_change_x_abs_ret",
    "overnight_return",
    "noise_gap",
    "log_rk_",
    "log_bpv_",
    "rv_ratio_",
    "log_atm_iv_",
    "vrp_",
    "iv_skew_",
    "iv_term_",
    "iv_butterfly_",
    "iv_rv_gap_",
    "vix_",
    "vol_of_vix_",
    "vts_",
    "forward_vol_",
    "d_fx_iv_",
    "d_credit_",
    "d_rate_vol",
    "d_yield_slope",
    "d_gold_vol",
    "d_oil_vol",
    "z_fx_iv_",
    "z_credit_",
    "z_rate_vol",
    "z_yield_slope",
    "z_gold_vol",
    "z_oil_vol",
    "xasset_",
)


def _filter_expandable(columns: pd.Index) -> list[str]:
    """Return only columns whose names match _EXPANDABLE_PREFIXES."""
    return [c for c in columns if any(c.startswith(p) for p in _EXPANDABLE_PREFIXES)]


@register_feature_layer("tree_expansion")
class TreeExpansionLayer:
    """Applies triple_expand to all numeric columns from preceding layers.

    For each input column, produces {name}_change, {name}_zscore.
    The original columns are NOT included (they already exist from base layers).

    Only continuous time-series features are expanded. Calendar dummies,
    categoricals, and event indicators are passed through without expansion.
    """

    name = "tree_expansion"
    _needs_base_features = True

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, Any] | None = None,
        base_features: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Expand base features into level/change/zscore triples.

        Parameters
        ----------
        daily_data : pd.DataFrame
            Raw daily data (used to derive features if base_features not given).
        context : dict, optional
            Additional context (unused by this layer).
        base_features : pd.DataFrame, optional
            If provided, expand these columns (filtered by prefix allowlist).
            Otherwise fall back to expanding numeric columns from daily_data
            that match known feature patterns.

        Returns
        -------
        pd.DataFrame
            Expanded columns (2x the expandable column count). Only the
            _change and _zscore columns are returned (level duplicates
            the base feature which already exists from prior layers).
        """
        if base_features is not None:
            cols = _filter_expandable(base_features.columns)
            if not cols:
                return pd.DataFrame(index=daily_data.index)
            source = base_features[cols]
        else:
            cols = _filter_expandable(daily_data.columns)
            if not cols:
                return pd.DataFrame(index=daily_data.index)
            source = daily_data[cols]

        frames = []
        for col in source.columns:
            expanded = triple_expand(source[col], window=20)
            # Drop _level (duplicate of original) — keep only change and zscore
            change_col = f"{col}_change"
            zscore_col = f"{col}_zscore"
            if change_col in expanded.columns:
                frames.append(expanded[[change_col, zscore_col]])

        if not frames:
            return pd.DataFrame(index=daily_data.index)

        return pd.concat(frames, axis=1)
