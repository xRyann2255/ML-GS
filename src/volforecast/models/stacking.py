"""Stacking ensemble: LightGBM + HAR predictions blended via Ridge.

The hypothesis: LightGBM has high R² (good discrimination) but biased levels
that hurt QLIKE. HAR has calibrated levels. A Ridge meta-learner on both
predictions should inherit LightGBM's discrimination while anchoring to HAR's
calibration.

Architecture:
    1. Split training data into base-train and blend-holdout (last 20%)
    2. Fit HAR on base-train, predict on blend-holdout
    3. Fit LightGBM on base-train, predict on blend-holdout
    4. Fit Ridge on [har_pred, lgbm_pred] -> y_blend
    5. Refit HAR and LightGBM on FULL training data for final predictions
    6. At predict time: get both sub-model preds, feed to Ridge meta-model
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from volforecast.models._base import _BaseModel, temporal_holdout_split
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


@register_model("stacking_har_lgbm")
class StackingHARLightGBM(_BaseModel):
    """Stacking ensemble: HAR + LightGBM -> Ridge meta-learner.

    Parameters
    ----------
    blend_fraction : float
        Fraction of training data to hold out for blending (default 0.20).
    blend_purge_gap : int
        Gap between base-train and blend-holdout (default 10).
    ridge_alpha : float
        Ridge regularization for meta-learner (default 1.0).
    lgbm_params : dict
        Parameters passed to LightGBMVolModel.
    har_model : str
        Which HAR variant to use as base learner (default "har").
    """

    REQUIRED_LAYERS = [
        "har_core",
        "asymmetry",
        "noise_robust",
        "options",
        "calendar",
        "tree_expansion",
    ]
    name = "stacking_har_lgbm"
    supports_tuning = False

    def __init__(
        self,
        blend_fraction: float = 0.20,
        blend_purge_gap: int = 10,
        ridge_alpha: float = 1.0,
        har_model: str = "har",
        **kwargs: Any,
    ) -> None:
        self.blend_fraction = blend_fraction
        self.blend_purge_gap = blend_purge_gap
        self.ridge_alpha = ridge_alpha
        self.har_model_name = har_model
        self.lgbm_params = kwargs
        self._har = None
        self._lgbm = None
        self._meta = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> StackingHARLightGBM:
        """Fit stacking ensemble with blend holdout for meta-learner training."""
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()

        split = temporal_holdout_split(len(X), self.blend_fraction, self.blend_purge_gap)
        if split is None:
            # Not enough data for blending — fall back to equal-weight average
            logger.warning(
                "Not enough data for stacking blend (n=%d). "
                "Falling back to equal-weight averaging.",
                len(X),
            )
            self._fallback = True
            # Fit both on full data
            har_cls = MODEL_REGISTRY[self.har_model_name]
            self._har = har_cls()
            self._har.fit(X, y)

            from volforecast.models.lightgbm import LightGBMVolModel

            self._lgbm = LightGBMVolModel(**self.lgbm_params)
            self._lgbm.fit(X, y)
            return self

        self._fallback = False
        split_idx, blend_start = split

        # Phase 1: Split into base-train and blend-holdout
        X_base, X_blend = X.iloc[:split_idx], X.iloc[blend_start:]
        y_base, y_blend = y.iloc[:split_idx], y.iloc[blend_start:]

        # Phase 2: Fit sub-models on base-train
        har_cls = MODEL_REGISTRY[self.har_model_name]
        har_base = har_cls()
        har_base.fit(X_base, y_base)

        from volforecast.models.lightgbm import LightGBMVolModel

        lgbm_base = LightGBMVolModel(**self.lgbm_params)
        lgbm_base.fit(X_base, y_base)

        # Phase 3: Generate blend predictions
        har_blend_preds = har_base.predict(X_blend)
        lgbm_blend_preds = lgbm_base.predict(X_blend)

        # Build meta-features (only use rows where both preds are valid)
        meta_X = np.column_stack([har_blend_preds, lgbm_blend_preds])
        y_blend_arr = y_blend.values
        valid = ~(np.isnan(meta_X).any(axis=1) | np.isnan(y_blend_arr))
        meta_X_clean = meta_X[valid]
        y_blend_clean = y_blend_arr[valid]

        if len(y_blend_clean) < 10:
            logger.warning(
                "Too few valid blend samples (%d). Using equal weights.", len(y_blend_clean)
            )
            self._fallback = True
            self._har = har_cls()
            self._har.fit(X, y)
            self._lgbm = LightGBMVolModel(**self.lgbm_params)
            self._lgbm.fit(X, y)
            return self

        # Phase 4: Fit Ridge meta-learner
        self._meta = Ridge(alpha=self.ridge_alpha, fit_intercept=True)
        self._meta.fit(meta_X_clean, y_blend_clean)
        logger.info(
            "Stacking meta-learner weights: HAR=%.3f, LightGBM=%.3f, intercept=%.4f",
            self._meta.coef_[0],
            self._meta.coef_[1],
            self._meta.intercept_,
        )

        # Phase 5: Refit sub-models on FULL training data for final predictions
        self._har = har_cls()
        self._har.fit(X, y)

        self._lgbm = LightGBMVolModel(**self.lgbm_params)
        self._lgbm.fit(X, y)

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate stacked predictions."""
        if self._har is None or self._lgbm is None:
            raise RuntimeError("Model has not been fitted")

        har_preds = self._har.predict(X)
        lgbm_preds = self._lgbm.predict(X)

        if getattr(self, "_fallback", False) or self._meta is None:
            # Equal-weight fallback
            return 0.5 * har_preds + 0.5 * lgbm_preds

        meta_X = np.column_stack([har_preds, lgbm_preds])
        # Handle NaN: where either sub-model gives NaN, output NaN
        valid = ~np.isnan(meta_X).any(axis=1)
        result = np.full(len(X), np.nan)
        if valid.any():
            result[valid] = self._meta.predict(meta_X[valid])
        return result

    @property
    def summary(self) -> dict[str, float]:
        """Meta-learner weights."""
        if self._meta is None:
            return {"fallback": 1.0}
        return {
            "har_weight": float(self._meta.coef_[0]),
            "lgbm_weight": float(self._meta.coef_[1]),
            "intercept": float(self._meta.intercept_),
        }
