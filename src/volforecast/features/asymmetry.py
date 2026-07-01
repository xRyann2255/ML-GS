"""Asymmetric volatility features (Layer 1).

Captures the leverage effect and jump dynamics:
- Realized semivariances (positive/negative components)
- Bipower variation (BPV) for continuous variation
- Jump detection and jump variation
- Signed jump variation (directional jumps)
- Continuous variation (RV minus jumps)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from volforecast.data.measures import (  # noqa: F401
    compute_bpv,
    compute_continuous_variation,
    compute_jump_variation,
    compute_realized_moments,
    compute_realized_tripower_quarticity,
    compute_semivariances,
    compute_signed_jumps,
    detect_jumps,
    lee_mykland_test,
)
from volforecast.features.transforms import lagged_log_features, safe_log
from volforecast.registry import register_feature_layer


def build_asymmetry_features(
    intraday_returns: pd.Series,
    rv: float,
    rq: float,
) -> dict[str, float]:
    """Compute all Layer 1 asymmetry features for a single day.

    Returns keys: rs_positive, rs_negative, signed_jump, bpv,
    z_stat, p_value, jump_indicator, jump_variation, continuous_variation.
    """
    semivars = compute_semivariances(intraday_returns)
    bpv = compute_bpv(intraday_returns)
    n_obs = len(intraday_returns)
    rtq = compute_realized_tripower_quarticity(intraday_returns)
    jump_test = detect_jumps(rv, bpv, rtq, n_obs)
    j_var = compute_jump_variation(rv, bpv, jump_test["jump_indicator"])
    c_var = compute_continuous_variation(rv, j_var)

    return {
        **semivars,
        "bpv": bpv,
        **jump_test,
        "jump_variation": j_var,
        "continuous_variation": c_var,
    }


# ---------------------------------------------------------------------------
# FeatureLayer wrapper (Tier 2: daily DataFrame → daily DataFrame)
# ---------------------------------------------------------------------------


@register_feature_layer("asymmetry")
class AsymmetryLayer:
    """Asymmetry feature layer: semivariances, BPV, jumps at daily/weekly/monthly.

    Expects ``daily_data`` to have columns from Tier 1 aggregation:
    rs_positive, rs_negative, bpv, jump_variation, continuous_variation.
    Produces rolling averages and log-transformed design matrix columns.
    """

    name = "asymmetry"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """Build asymmetry design matrix from pre-computed daily measures."""
        result = pd.DataFrame(index=daily_data.index)

        # Log semivariances (daily, weekly, monthly) — shifted for forecasting
        for col in ["rs_positive", "rs_negative"]:
            if col not in daily_data.columns:
                continue
            features = lagged_log_features(daily_data[col], col)
            result = pd.concat([result, features], axis=1)

        # BPV (daily, weekly)
        if "bpv" in daily_data.columns:
            bpv_features = lagged_log_features(daily_data["bpv"], "bpv", windows=[5])
            result = pd.concat([result, bpv_features], axis=1)

        # Jump variation (daily)
        if "jump_variation" in daily_data.columns:
            jv = daily_data["jump_variation"]
            result["log_jump_d"] = safe_log(jv)

        # Continuous variation (daily, weekly)
        if "continuous_variation" in daily_data.columns:
            cont_features = lagged_log_features(
                daily_data["continuous_variation"], "cont", windows=[5]
            )
            result = pd.concat([result, cont_features], axis=1)

        # Signed daily return (leverage effect proxy) — available at end of day t
        if "close" in daily_data.columns:
            log_ret = np.log(daily_data["close"] / daily_data["close"].shift(1))
            result["signed_return_d"] = log_ret
            # Absolute return — strong predictor of next-day RV
            result["abs_ret_d"] = log_ret.abs()
            # Weekly average absolute return (smoothed volatility proxy)
            result["abs_ret_w"] = log_ret.abs().rolling(5).mean()
            # 5-day cumulative log return (weekly momentum)
            result["ret_5d"] = log_ret.rolling(5).sum()

        return result
