"""Shared transform utilities for feature layers.

- safe_log: log transform with zero-floor protection
- lagged_log_features: d/w/m rolling log-transformed and lagged features
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def safe_log(
    x: pd.Series | pd.DataFrame | np.ndarray | float,
    min_value: float = 1e-20,
) -> pd.Series | pd.DataFrame | np.ndarray | float:
    """Log transform with zero-floor protection.

    Clips values to min_value before taking log, preventing -inf
    from zeros or negative values in RV-like series.

    Works with Series, DataFrame, ndarray, or scalar float.
    """
    if isinstance(x, (pd.Series, pd.DataFrame)):
        return np.log(x.clip(lower=min_value))
    if isinstance(x, np.ndarray):
        return np.log(np.clip(x, a_min=min_value, a_max=None))
    # Scalar
    return float(np.log(max(x, min_value)))


def lagged_log_features(
    series: pd.Series,
    name: str,
    windows: list[int] | None = None,
    min_value: float = 1e-20,
) -> pd.DataFrame:
    """Compute log-transformed features at daily/weekly/monthly horizons.

    For each window w, computes: log(rolling_mean(series, w).clip(min_value))
    Also includes the daily log value.

    Parameters
    ----------
    series : pd.Series
        Raw (non-log) daily series (e.g., RV, BPV, semivariances).
    name : str
        Base name for output columns (e.g., "rv" -> "log_rv_d", "log_rv_w", "log_rv_m").
    windows : list[int], optional
        Rolling windows. Default [5, 22]. Window 5 maps to "_w", 22 maps to "_m".
    min_value : float
        Floor before log to prevent -inf. Default 1e-20.

    Returns
    -------
    pd.DataFrame
        Columns: log_{name}_d, and log_{name}_{label} for each window.
    """
    if windows is None:
        windows = [5, 22]

    log_daily = safe_log(series, min_value)

    result: dict[str, pd.Series] = {}
    result[f"log_{name}_d"] = log_daily

    window_labels = {5: "w", 22: "m"}
    for w in windows:
        label = window_labels.get(w, f"{w}d")
        rolling_mean = series.rolling(w).mean()
        result[f"log_{name}_{label}"] = safe_log(rolling_mean, min_value)

    return pd.DataFrame(result, index=series.index)
