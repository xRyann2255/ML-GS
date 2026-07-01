"""Regime-conditional ensemble: HAR + LightGBM with regime-dependent weights.

Research finding (2026-05-27): Optimal blend weight is massively
regime-dependent at h=22:
  - Low-vol: LightGBM dominates (optimal HAR weight ~0.05)
  - High-vol: HAR dominates (optimal HAR weight ~0.80)

Architecture:
    1. Fit HAR and LightGBM on full training data
    2. Classify test observations into regimes using log_rv_w threshold
    3. Apply regime-specific blend weights

Variants (controlled by `blend_strategy` param):
    - "fixed_regime": Pre-set weights per regime (no calibration)
    - "val_calibrated": Calibrate weights per regime on validation holdout
    - "residual_highvol": Use residual stacking in high-vol, blend in low-vol
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from volforecast.models._base import _BaseModel, temporal_holdout_split
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


@register_model("regime_blend")
class RegimeBlendModel(_BaseModel):
    """Regime-conditional HAR + LightGBM ensemble.

    Parameters
    ----------
    har_model : str
        HAR variant to use (default "har").
    blend_strategy : str
        "fixed_regime", "val_calibrated", or "residual_highvol".
    regime_feature : str
        Feature used as regime indicator (default "log_rv_w").
    regime_percentile : float
        Percentile threshold for high-vol regime (default 75).
    w_har_low : float
        HAR weight in low-vol regime (default 0.05).
    w_har_high : float
        HAR weight in high-vol regime (default 0.80).
    val_fraction : float
        Fraction of training data for weight calibration (default 0.20).
    val_purge_gap : int
        Gap between train and val split (default 10).
    **kwargs
        Parameters passed through to LightGBMVolModel.
    """

    REQUIRED_LAYERS = [
        "har_core",
        "asymmetry",
        "noise_robust",
        "options",
        "calendar",
        "tree_expansion",
    ]
    name = "regime_blend"
    supports_tuning = False

    def __init__(
        self,
        har_model: str = "har",
        blend_strategy: str = "fixed_regime",
        regime_feature: str = "log_rv_w",
        regime_percentile: float = 75.0,
        w_har_low: float = 0.05,
        w_har_high: float = 0.80,
        val_fraction: float = 0.20,
        val_purge_gap: int = 10,
        **kwargs: Any,
    ) -> None:
        self.har_model_name = har_model
        self.blend_strategy = blend_strategy
        self.regime_feature = regime_feature
        self.regime_percentile = regime_percentile
        self.w_har_low = w_har_low
        self.w_har_high = w_har_high
        self.val_fraction = val_fraction
        self.val_purge_gap = val_purge_gap
        self.lgbm_params = kwargs

        self._har = None
        self._lgbm = None
        self._lgbm_resid = None  # For residual_highvol strategy
        self._regime_threshold = None
        self._calibrated_w_low = None
        self._calibrated_w_high = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RegimeBlendModel:
        """Fit regime blend ensemble."""
        from volforecast.models.lightgbm import LightGBMVolModel
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()

        # Compute regime threshold from training data
        if self.regime_feature in X.columns:
            regime_vals = X[self.regime_feature].dropna()
            self._regime_threshold = float(
                np.percentile(regime_vals.values, self.regime_percentile)
            )
            logger.info(
                "Regime threshold: %s > %.4f = high-vol (p%d of training)",
                self.regime_feature,
                self._regime_threshold,
                int(self.regime_percentile),
            )
        else:
            logger.warning(
                "Regime feature %r not found in X. Using median of target as fallback.",
                self.regime_feature,
            )
            self._regime_threshold = float(np.median(y.dropna().values))

        # Fit HAR on full training data
        har_cls = MODEL_REGISTRY[self.har_model_name]
        self._har = har_cls()
        self._har.fit(X, y)

        # Fit LightGBM on full training data
        self._lgbm = LightGBMVolModel(**self.lgbm_params)
        self._lgbm.fit(X, y)

        # Strategy-specific fitting
        if self.blend_strategy == "val_calibrated":
            self._calibrate_weights(X, y)
        elif self.blend_strategy == "residual_highvol":
            self._fit_residual_model(X, y)

        return self

    def _calibrate_weights(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Calibrate per-regime weights on validation holdout."""
        from volforecast.models.lightgbm import LightGBMVolModel
        from volforecast.registry import MODEL_REGISTRY

        split = temporal_holdout_split(
            len(X),
            self.val_fraction,
            self.val_purge_gap,
            min_holdout=50,
        )
        if split is None:
            logger.warning("Not enough data for weight calibration. Using fixed weights.")
            self._calibrated_w_low = self.w_har_low
            self._calibrated_w_high = self.w_har_high
            return

        split_idx, val_start = split
        X_base, X_val = X.iloc[:split_idx], X.iloc[val_start:]
        y_base, y_val = y.iloc[:split_idx], y.iloc[val_start:]

        # Fit sub-models on base portion
        har_cls = MODEL_REGISTRY[self.har_model_name]
        har_base = har_cls()
        har_base.fit(X_base, y_base)

        lgbm_base = LightGBMVolModel(**self.lgbm_params)
        lgbm_base.fit(X_base, y_base)

        # Get predictions on validation
        har_val = har_base.predict(X_val)
        lgbm_val = lgbm_base.predict(X_val)
        y_val_arr = y_val.values

        # Classify val observations into regimes
        if self.regime_feature in X_val.columns:
            regime_vals = X_val[self.regime_feature].values
        else:
            regime_vals = np.full(len(X_val), np.nan)

        high_mask = regime_vals >= self._regime_threshold
        low_mask = ~high_mask & ~np.isnan(regime_vals)

        # Grid search optimal weight per regime
        self._calibrated_w_low = (
            self._grid_search_weight(har_val[low_mask], lgbm_val[low_mask], y_val_arr[low_mask])
            if low_mask.sum() > 20
            else self.w_har_low
        )

        self._calibrated_w_high = (
            self._grid_search_weight(har_val[high_mask], lgbm_val[high_mask], y_val_arr[high_mask])
            if high_mask.sum() > 20
            else self.w_har_high
        )

        logger.info(
            "Calibrated weights: low-vol w_har=%.2f, high-vol w_har=%.2f",
            self._calibrated_w_low,
            self._calibrated_w_high,
        )

    def _fit_residual_model(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Fit a secondary LightGBM on HAR residuals for high-vol regime."""
        from volforecast.models.lightgbm import LightGBMVolModel

        har_preds = self._har.predict(X)
        residuals = y.values - har_preds
        valid = ~np.isnan(residuals)

        if valid.sum() < 100:
            logger.warning("Too few valid residuals for residual model.")
            return

        y_resid = pd.Series(residuals[valid], index=y.index[valid])
        self._lgbm_resid = LightGBMVolModel(**self.lgbm_params)
        self._lgbm_resid.fit(X[valid], y_resid)
        logger.info("Residual LightGBM fitted on %d observations.", valid.sum())

    @staticmethod
    def _grid_search_weight(
        har_preds: np.ndarray,
        lgbm_preds: np.ndarray,
        y_true: np.ndarray,
    ) -> float:
        """Find optimal HAR weight by grid search on QLIKE."""
        valid = ~(np.isnan(har_preds) | np.isnan(lgbm_preds) | np.isnan(y_true))
        if valid.sum() < 10:
            return 0.5

        har_v = har_preds[valid]
        lgbm_v = lgbm_preds[valid]
        y_v = y_true[valid]

        best_w = 0.5
        best_qlike = float("inf")
        for w in np.arange(0.0, 1.01, 0.05):
            blend = w * har_v + (1 - w) * lgbm_v
            # QLIKE in variance space
            rv_true = np.exp(y_v)
            rv_pred = np.exp(blend)
            ratio = rv_true / rv_pred
            qlike = float(np.mean(ratio - np.log(ratio) - 1.0))
            if qlike < best_qlike:
                best_qlike = qlike
                best_w = w
        return best_w

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate regime-conditional blended predictions."""
        if self._har is None or self._lgbm is None:
            raise RuntimeError("Model has not been fitted")

        har_preds = self._har.predict(X)
        lgbm_preds = self._lgbm.predict(X)

        # Classify into regimes
        if self.regime_feature in X.columns:
            regime_vals = X[self.regime_feature].values
        else:
            # Fallback: no regime info — use equal blend
            return 0.5 * har_preds + 0.5 * lgbm_preds

        high_mask = regime_vals >= self._regime_threshold
        low_mask = ~high_mask

        # Get effective weights
        if self.blend_strategy == "val_calibrated" and self._calibrated_w_low is not None:
            w_low = self._calibrated_w_low
            w_high = self._calibrated_w_high
        else:
            w_low = self.w_har_low
            w_high = self.w_har_high

        # Apply regime-specific blending
        result = np.full(len(X), np.nan)

        if self.blend_strategy == "residual_highvol" and self._lgbm_resid is not None:
            # Low-vol: standard blend
            if low_mask.any():
                result[low_mask] = w_low * har_preds[low_mask] + (1 - w_low) * lgbm_preds[low_mask]
            # High-vol: HAR + residual correction (capped)
            if high_mask.any():
                resid_correction = self._lgbm_resid.predict(X[high_mask])
                result[high_mask] = har_preds[high_mask] + (1 - w_high) * resid_correction
        else:
            # Standard regime blend
            if low_mask.any():
                result[low_mask] = w_low * har_preds[low_mask] + (1 - w_low) * lgbm_preds[low_mask]
            if high_mask.any():
                result[high_mask] = (
                    w_high * har_preds[high_mask] + (1 - w_high) * lgbm_preds[high_mask]
                )

        # Handle NaN regime values: use the overall average weight
        nan_mask = np.isnan(regime_vals)
        if nan_mask.any():
            w_avg = (w_low + w_high) / 2
            result[nan_mask] = w_avg * har_preds[nan_mask] + (1 - w_avg) * lgbm_preds[nan_mask]

        return result

    @property
    def summary(self) -> dict[str, float]:
        """Summary of regime blend configuration."""
        info = {
            "regime_threshold": self._regime_threshold or 0.0,
            "w_har_low": self.w_har_low,
            "w_har_high": self.w_har_high,
        }
        if self._calibrated_w_low is not None:
            info["calibrated_w_har_low"] = self._calibrated_w_low
            info["calibrated_w_har_high"] = self._calibrated_w_high
        return info
