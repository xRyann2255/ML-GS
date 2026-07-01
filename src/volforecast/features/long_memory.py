"""Long-memory feature layer for extended-horizon forecasting.

Adds 60-day and 90-day rolling averages of RV and semivariances,
providing the model with longer persistence information beyond
the standard HAR d/w/m (1/5/22) lags.

These features capture the slow mean-reversion dynamics relevant
for h=22 forecasting where the standard monthly (22d) lag is
insufficient — the model needs to see 2-4 month history.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from volforecast.features.transforms import safe_log
from volforecast.registry import register_feature_layer


@register_feature_layer("long_memory")
class LongMemoryLayer:
    """Extended-lag features: 60d and 90d rolling averages.

    Computes:
    - log_rv_60d, log_rv_90d: log of 60/90-day rolling mean RV
    - log_rs_positive_60d, log_rs_positive_90d: positive semivariance lags
    - log_rs_negative_60d, log_rs_negative_90d: negative semivariance lags
    - log_bpv_60d: 60-day bipower variation (robust vol proxy)
    - rv_ratio_d_60d: RV(1d) / RV(60d) — mean-reversion indicator

    All features use end-of-day-t data to forecast day t+h.
    """

    name = "long_memory"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """Build long-memory feature matrix."""
        result = pd.DataFrame(index=daily_data.index)
        rv = daily_data["rv"]

        # Log RV at 60d and 90d
        rv_60 = rv.rolling(60).mean()
        rv_90 = rv.rolling(90).mean()
        result["log_rv_60d"] = safe_log(rv_60)
        result["log_rv_90d"] = safe_log(rv_90)

        # Mean-reversion ratio: current daily vs long-term average
        # High ratio = vol spike above long-term, likely to mean-revert at h=22
        result["rv_ratio_d_60d"] = np.log(rv / rv_60.clip(lower=1e-20))

        # Semivariances at 60d/90d (asymmetric long memory)
        if "rs_positive" in daily_data.columns:
            rsp = daily_data["rs_positive"]
            result["log_rs_positive_60d"] = safe_log(rsp.rolling(60).mean())
            result["log_rs_positive_90d"] = safe_log(rsp.rolling(90).mean())

        if "rs_negative" in daily_data.columns:
            rsn = daily_data["rs_negative"]
            result["log_rs_negative_60d"] = safe_log(rsn.rolling(60).mean())
            result["log_rs_negative_90d"] = safe_log(rsn.rolling(90).mean())

        # BPV 60d (noise-robust long-term vol)
        if "bpv" in daily_data.columns:
            result["log_bpv_60d"] = safe_log(daily_data["bpv"].rolling(60).mean())

        return result
