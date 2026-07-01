"""HAR-family feature computation (Layer 0: HAR core + measurement quality).

Computes heterogeneous autoregressive (HAR) features from realized volatility:
- log RV at daily, weekly, monthly horizons
- Realized quarticity (RQ) for measurement quality
- RQ interaction terms (RQ x RV)
- HARQ extensions with time-varying coefficients
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from volforecast.data.measures import compute_realized_variance, compute_rq  # noqa: F401
from volforecast.features.transforms import safe_log
from volforecast.registry import register_feature_layer

logger = logging.getLogger(__name__)

# Overnight returns exceeding this absolute threshold indicate corrupted data
# (e.g. split-unadjusted open vs split-adjusted close).
_OVERNIGHT_RETURN_MAX_ABS = 0.5


def compute_log_rv_features(
    rv_series: pd.Series,
    date: pd.Timestamp,
) -> dict[str, float]:
    """Compute log RV at daily, weekly (5d), and monthly (22d) horizons.

    Returns keys: 'log_rv_d', 'log_rv_w', 'log_rv_m'.
    Raises ValueError if fewer than 22 observations up to date.
    """
    # Get data up to and including date
    rv_up_to = rv_series.loc[:date]
    if len(rv_up_to) < 22:
        raise ValueError(f"Need at least 22 observations up to {date}, got {len(rv_up_to)}")

    rv_d = rv_up_to.iloc[-1]
    rv_w = rv_up_to.iloc[-5:].mean()
    rv_m = rv_up_to.iloc[-22:].mean()

    return {
        "log_rv_d": float(safe_log(rv_d)),
        "log_rv_w": float(safe_log(rv_w)),
        "log_rv_m": float(safe_log(rv_m)),
    }


def compute_harq_features(
    rv_series: pd.Series,
    rq_series: pd.Series,
    date: pd.Timestamp,
) -> dict[str, float]:
    """Compute full HARQ feature set including RQ interaction terms.

    Features: log_rv_d, log_rv_w, log_rv_m, sqrt_rq_d,
              rq_rv_interaction_d (= log_rv_d * sqrt(rq_d)).
    """
    log_rv = compute_log_rv_features(rv_series, date)

    rq_up_to = rq_series.loc[:date]
    if len(rq_up_to) < 1:
        raise ValueError("Need at least 1 RQ observation up to date")

    sqrt_rq_d = float(np.sqrt(rq_up_to.iloc[-1]))

    return {
        **log_rv,
        "sqrt_rq_d": sqrt_rq_d,
        "rq_rv_interaction_d": log_rv["log_rv_d"] * sqrt_rq_d,
    }


def build_har_design_matrix(
    rv_series: pd.Series,
    rq_series: pd.Series | None = None,
    include_rq_interaction: bool = False,
) -> pd.DataFrame:
    """Build the full HAR/HARQ design matrix for a time series.

    Returns DataFrame with columns aligned to rv_series index (NaN for first 21 rows).
    """
    log_rv = safe_log(rv_series)

    # Daily: log(RV_t) — available at end of day t
    log_rv_d = log_rv

    # Weekly: log(mean RV over t-4 to t) — available at end of day t
    log_rv_w = safe_log(rv_series.rolling(5).mean())

    # Monthly: log(mean RV over t-21 to t) — available at end of day t
    log_rv_m = safe_log(rv_series.rolling(22).mean())

    result = pd.DataFrame(
        {
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_w,
            "log_rv_m": log_rv_m,
        },
        index=rv_series.index,
    )

    if include_rq_interaction and rq_series is not None:
        sqrt_rq = np.sqrt(rq_series)
        result["sqrt_rq_d"] = sqrt_rq
        result["rq_rv_interaction_d"] = log_rv_d * sqrt_rq

    return result


# ---------------------------------------------------------------------------
# FeatureLayer wrapper (Tier 2: daily DataFrame → daily DataFrame)
# ---------------------------------------------------------------------------


@register_feature_layer("har_core")
class HARCoreLayer:
    """HAR feature layer: log RV at daily/weekly/monthly horizons + optional RQ.

    Expects ``daily_data`` to have at minimum an 'rv' column.
    If 'rq' column is present, includes RQ interaction features.
    """

    name = "har_core"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """Build HAR design matrix from daily RV data."""
        rv = daily_data["rv"]
        rq = daily_data.get("rq")
        include_rq = rq is not None and not rq.isna().all()
        result = build_har_design_matrix(
            rv_series=rv,
            rq_series=rq if include_rq else None,
            include_rq_interaction=include_rq,
        )

        # Standalone sqrt_rq_d always exposed when rq exists (for tree models)
        if include_rq and "sqrt_rq_d" not in result.columns:
            result["sqrt_rq_d"] = np.sqrt(rq)

        # Overnight return: log(open_t / close_{t-1}) — available at open of day t
        if (
            "open" in daily_data.columns
            and "close" in daily_data.columns
            and not daily_data["open"].isna().all()
        ):
            overnight = np.log(daily_data["open"] / daily_data["close"].shift(1))
            # NaN-out corrupted overnight returns (split-unadjusted open vs
            # split-adjusted close produces values like log(10) ≈ 2.3).
            # We keep the column but mask individual corrupt values so that
            # tree models (LightGBM) can still use the valid observations.
            corrupt_mask = overnight.abs() > _OVERNIGHT_RETURN_MAX_ABS
            n_corrupt = corrupt_mask.sum()
            if n_corrupt > 0:
                overnight = overnight.where(~corrupt_mask)
                logger.info(
                    "overnight_return: masked %d/%d corrupt values (|r| > %.2f, max=%.3f)",
                    n_corrupt,
                    len(overnight.dropna()) + n_corrupt,
                    _OVERNIGHT_RETURN_MAX_ABS,
                    overnight.abs().max() if overnight.notna().any() else 0.0,
                )
            result["overnight_return"] = overnight

        return result
