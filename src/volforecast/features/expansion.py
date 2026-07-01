"""Triple expansion utility for LightGBM feature enrichment.

For each base feature series, produces three columns:
- level: the raw value (identity)
- change: first difference (x_t - x_{t-1})
- zscore: rolling z-score (x_t - mean) / std over a window

This systematic expansion is applied to all base quantities before
feeding into gradient-boosted tree models (Vol-project-ref Ch. 6.3, 8.4).
HAR OLS models use original features directly — this is LightGBM-only.
"""

from __future__ import annotations

import pandas as pd


def triple_expand(series: pd.Series, window: int = 20) -> pd.DataFrame:
    """Expand a single feature into level, change, and z-score columns.

    Parameters
    ----------
    series : pd.Series
        Input feature series. Must have a `name` attribute.
    window : int
        Rolling window size for z-score computation (default: 20).

    Returns
    -------
    pd.DataFrame
        Three columns: ``{name}_level``, ``{name}_change``, ``{name}_zscore``.
        Same index as input.
    """
    name = series.name
    level = series.rename(f"{name}_level")
    change = series.diff().rename(f"{name}_change")
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()
    zscore = ((series - rolling_mean) / rolling_std).rename(f"{name}_zscore")

    return pd.DataFrame({level.name: level, change.name: change, zscore.name: zscore})
