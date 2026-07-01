"""Calibrated LightGBM: post-hoc affine recalibration to fix QLIKE level bias.

The hypothesis: LightGBM predictions have good rank-ordering (high R²) but
biased levels that inflate QLIKE. An affine correction learned on a holdout
set (a*pred + b) can shift predictions to QLIKE-optimal levels while
preserving discrimination.

Architecture:
    1. Split training data into base-train and calibration-holdout (last 15%)
    2. Fit LightGBM on base-train
    3. Predict on calibration-holdout
    4. Fit affine correction: minimize QLIKE(y_cal, a*pred_cal + b) via OLS
       (since QLIKE's optimal predictor is E[log RV | X], linear recal ≈ OLS)
    5. Refit LightGBM on FULL training data
    6. At predict time: raw_pred * a + b
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from volforecast.models._base import _BaseModel, temporal_holdout_split
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


@register_model("lightgbm_calibrated")
class CalibratedLightGBM(_BaseModel):
    """LightGBM with post-hoc affine calibration.

    Parameters
    ----------
    cal_fraction : float
        Fraction of training data for calibration holdout (default 0.15).
    cal_purge_gap : int
        Gap between base-train and calibration-holdout (default 10).
    All other params are forwarded to LightGBMVolModel.
    """

    REQUIRED_LAYERS = [
        "har_core",
        "asymmetry",
        "noise_robust",
        "options",
        "calendar",
        "tree_expansion",
    ]
    name = "lightgbm_calibrated"
    supports_tuning = False

    def __init__(
        self,
        cal_fraction: float = 0.15,
        cal_purge_gap: int = 10,
        **kwargs: Any,
    ) -> None:
        self.cal_fraction = cal_fraction
        self.cal_purge_gap = cal_purge_gap
        self.lgbm_params = kwargs
        self._lgbm = None
        self._cal_slope = 1.0
        self._cal_intercept = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> CalibratedLightGBM:
        """Fit LightGBM then learn affine calibration on holdout."""
        from volforecast.models.lightgbm import LightGBMVolModel

        split = temporal_holdout_split(len(X), self.cal_fraction, self.cal_purge_gap)
        if split is None:
            # Not enough data — skip calibration
            logger.warning("Not enough data for calibration (n=%d). Skipping.", len(X))
            self._lgbm = LightGBMVolModel(**self.lgbm_params)
            self._lgbm.fit(X, y)
            self._cal_slope = 1.0
            self._cal_intercept = 0.0
            return self

        split_idx, cal_start = split

        # Phase 1: Fit LightGBM on base-train
        X_base, X_cal = X.iloc[:split_idx], X.iloc[cal_start:]
        y_base, y_cal = y.iloc[:split_idx], y.iloc[cal_start:]

        lgbm_base = LightGBMVolModel(**self.lgbm_params)
        lgbm_base.fit(X_base, y_base)

        # Phase 2: Predict on calibration holdout
        cal_preds = lgbm_base.predict(X_cal)
        y_cal_arr = y_cal.values

        # Only use valid predictions for calibration
        valid = ~(np.isnan(cal_preds) | np.isnan(y_cal_arr))
        cal_preds_clean = cal_preds[valid].reshape(-1, 1)
        y_cal_clean = y_cal_arr[valid]

        if len(y_cal_clean) < 10:
            logger.warning("Too few valid calibration samples (%d). Skipping.", len(y_cal_clean))
            self._lgbm = LightGBMVolModel(**self.lgbm_params)
            self._lgbm.fit(X, y)
            self._cal_slope = 1.0
            self._cal_intercept = 0.0
            return self

        # Phase 3: Learn affine correction via OLS (y_cal = a*pred + b)
        # OLS minimizes MSE which in log-space approximates QLIKE-optimal E[log RV|pred]
        calibrator = LinearRegression()
        calibrator.fit(cal_preds_clean, y_cal_clean)
        self._cal_slope = float(calibrator.coef_[0])
        self._cal_intercept = float(calibrator.intercept_)

        logger.info(
            "Calibration: slope=%.4f, intercept=%.4f (bias correction=%.4f)",
            self._cal_slope,
            self._cal_intercept,
            self._cal_intercept + (self._cal_slope - 1.0) * cal_preds_clean.mean(),
        )

        # Phase 4: Refit LightGBM on FULL training data
        self._lgbm = LightGBMVolModel(**self.lgbm_params)
        self._lgbm.fit(X, y)

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate calibrated predictions."""
        if self._lgbm is None:
            raise RuntimeError("Model has not been fitted")

        raw_preds = self._lgbm.predict(X)
        return self._cal_slope * raw_preds + self._cal_intercept

    @property
    def summary(self) -> dict[str, float]:
        """Calibration parameters plus LightGBM feature importance."""
        result = {
            "cal_slope": self._cal_slope,
            "cal_intercept": self._cal_intercept,
        }
        if self._lgbm is not None:
            # Add top-5 features by importance
            lgbm_summary = self._lgbm.summary
            top_features = sorted(lgbm_summary.items(), key=lambda x: -x[1])[:5]
            for name, imp in top_features:
                result[f"feat_{name}"] = imp
        return result
