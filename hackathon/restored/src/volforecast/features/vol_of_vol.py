"""Vol-of-vol feature layer (SpotV2Net edge-feature proxy).

Trailing 22-day standard deviation of lagged daily log-RV per symbol.
Emitted as node-feature columns so graph_data can lift them onto edges;
also usable by tree models directly.
"""

from __future__ import annotations

import pandas as pd

from volforecast.features.transforms import safe_log
from volforecast.registry import register_feature_layer


@register_feature_layer("vol_of_vol")
class VolOfVolLayer:
    """Trailing vol-of-vol: 22d std of lagged daily log-RV (SpotV2Net edge-feature proxy)."""

    name = "vol_of_vol"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict | None = None,
    ) -> pd.DataFrame:
        """Compute vol-of-vol features from daily RV.

        vov_d = rolling(22).std() of log(rv).shift(1)
        vov_w = rolling(5).mean() of vov_d

        The shift(1) is applied BEFORE rolling to ensure no look-ahead:
        vov_d at time t depends only on log_rv values dated <= t-1.
        """
        log_rv_lag = safe_log(daily_data["rv"]).shift(1)
        vov_d = log_rv_lag.rolling(22).std()
        vov_w = vov_d.rolling(5).mean()
        return pd.DataFrame({"vov_d": vov_d, "vov_w": vov_w}, index=daily_data.index)
