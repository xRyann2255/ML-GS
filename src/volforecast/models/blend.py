"""Prediction-level blending of independent sub-models.

Trains each sub-model on its own data representation (tabular or sequence),
calibrates blend weights on a temporal holdout, then combines predictions.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from volforecast.config import BlendConfig
from volforecast.evaluation.metrics import qlike
from volforecast.models._base import _BaseModel, temporal_holdout_split
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


@register_model("blend")
class PredictionBlendModel(_BaseModel):
    REQUIRED_LAYERS: list[str] = []
    name = "blend"
    supports_tuning = False
    requires_sequences = False

    def __init__(self, blend_config: BlendConfig, **kwargs: Any) -> None:
        self._config = blend_config
        self._sub_models: list[_BaseModel] = []
        self._weights: np.ndarray | None = None
        self._regime_weights: dict[str, np.ndarray] | None = None
        self._regime_threshold_value: float | None = None
        self._ridge_model: Ridge | None = None
        self._meta_intercept: float | None = None
        self._per_model_qlike: list[float] = []

    def _resolve_sub_models(self) -> None:
        """Instantiate sub-models from registry if not already injected."""
        if self._sub_models:
            return
        from volforecast.registry import MODEL_REGISTRY

        for sub_cfg in self._config.models:
            if sub_cfg.name not in MODEL_REGISTRY:
                raise ValueError(
                    f"Blend sub-model {sub_cfg.name!r} not in MODEL_REGISTRY. "
                    f"Available: {list(MODEL_REGISTRY.keys())}"
                )
            model_cls = MODEL_REGISTRY[sub_cfg.name]
            self._sub_models.append(model_cls(**sub_cfg.params))

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        *,
        sequence_data: Any = None,
        **kwargs: Any,
    ) -> PredictionBlendModel:
        self._resolve_sub_models()
        n = len(X)
        split = temporal_holdout_split(
            n, self._config.val_fraction, self._config.val_purge_gap
        )

        if split is None:
            logger.warning(
                "Not enough data for weight calibration (n=%d). "
                "Falling back to equal weights.",
                n,
            )
            self._weights = np.full(
                len(self._sub_models), 1.0 / len(self._sub_models)
            )
            for model in self._sub_models:
                model.fit(X, y)
            return self

        train_end, val_start = split
        X_base, X_val = X.iloc[:train_end], X.iloc[val_start:]
        y_base, y_val = y.iloc[:train_end], y.iloc[val_start:]

        # Phase 2: fit on base portion
        for model in self._sub_models:
            model.fit(X_base, y_base)

        # Phase 3: OOS predictions on holdout
        # Predict on full X and slice — avoids shape mismatch when a sub-model's
        # predict captures external state sized to the full dataset.
        oos_preds = {}
        for i, model in enumerate(self._sub_models):
            full_preds = model.predict(X)
            oos_preds[i] = full_preds[val_start:]

        # Phase 4: calibrate weights
        y_val_arr = y_val.values
        if self._config.weight_method == "fixed":
            self._calibrate_fixed()
        elif self._config.weight_method == "inverse_qlike":
            self._calibrate_inverse_qlike(oos_preds, y_val_arr)
        elif self._config.weight_method == "ridge_meta":
            self._calibrate_ridge_meta(oos_preds, y_val_arr)
        elif self._config.weight_method == "regime_dependent":
            self._calibrate_regime(oos_preds, y_val_arr, X_val)

        # Phase 5: refit on full data
        for model in self._sub_models:
            model.fit(X, y)

        return self

    def predict(
        self,
        X: pd.DataFrame,
        *,
        sequence_data: Any = None,
        **kwargs: Any,
    ) -> np.ndarray:
        if self._config.weight_method == "ridge_meta" and self._ridge_model is not None:
            preds_matrix = np.column_stack(
                [m.predict(X) for m in self._sub_models]
            )
            return self._ridge_model.predict(preds_matrix)

        if (
            self._config.weight_method == "regime_dependent"
            and self._regime_weights is not None
            and self._config.regime_indicator is not None
            and self._config.regime_indicator in X.columns
        ):
            return self._predict_regime(X)

        preds = [m.predict(X) for m in self._sub_models]
        return sum(w * p for w, p in zip(self._weights, preds))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _predict_regime(self, X: pd.DataFrame) -> np.ndarray:
        indicator = X[self._config.regime_indicator].values
        threshold = self._regime_threshold_value
        preds = [m.predict(X) for m in self._sub_models]
        result = np.zeros(len(X))
        high_mask = indicator >= threshold
        low_mask = ~high_mask
        for mask, regime_key in [(high_mask, "high"), (low_mask, "low")]:
            if mask.any():
                w = self._regime_weights[regime_key]
                result[mask] = sum(
                    w_k * p[mask] for w_k, p in zip(w, preds)
                )
        return result

    def _calibrate_fixed(self) -> None:
        self._weights = np.array(self._config.fixed_weights, dtype=np.float64)

    def _calibrate_inverse_qlike(
        self, oos_preds: dict[int, np.ndarray], y_val: np.ndarray
    ) -> None:
        qlikes = []
        for i in range(len(self._sub_models)):
            q = qlike(y_val, oos_preds[i], log_space=True)
            qlikes.append(max(q, 1e-8))
        self._per_model_qlike = qlikes
        inv = np.array([1.0 / q for q in qlikes])
        self._weights = inv / inv.sum()

    def _calibrate_ridge_meta(
        self, oos_preds: dict[int, np.ndarray], y_val: np.ndarray
    ) -> None:
        preds_matrix = np.column_stack(
            [oos_preds[i] for i in range(len(self._sub_models))]
        )
        self._ridge_model = Ridge(alpha=self._config.ridge_alpha)
        self._ridge_model.fit(preds_matrix, y_val)
        self._meta_intercept = float(self._ridge_model.intercept_)
        self._weights = self._ridge_model.coef_.copy()

    def _calibrate_regime(
        self,
        oos_preds: dict[int, np.ndarray],
        y_val: np.ndarray,
        X_val: pd.DataFrame,
    ) -> None:
        indicator_col = self._config.regime_indicator
        if indicator_col not in X_val.columns:
            logger.warning(
                "Regime indicator %r not in X_val. Falling back to equal weights.",
                indicator_col,
            )
            w = np.full(len(self._sub_models), 1.0 / len(self._sub_models))
            self._regime_weights = {"high": w, "low": w.copy()}
            self._weights = w.copy()
            return

        indicator_vals = X_val[indicator_col].values

        if self._config.regime_threshold is not None:
            if self._config.regime_threshold_type == "percentile":
                self._regime_threshold_value = float(
                    np.percentile(
                        indicator_vals, self._config.regime_threshold * 100
                    )
                )
            else:
                self._regime_threshold_value = self._config.regime_threshold
        else:
            self._regime_threshold_value = float(np.median(indicator_vals))

        high_mask = indicator_vals >= self._regime_threshold_value
        low_mask = ~high_mask

        self._regime_weights = {}
        for mask, key in [(high_mask, "high"), (low_mask, "low")]:
            if mask.sum() > 10:
                sub_oos = {
                    i: oos_preds[i][mask] for i in range(len(self._sub_models))
                }
                sub_y = y_val[mask]
                qlikes = [
                    max(qlike(sub_y, sub_oos[i], log_space=True), 1e-8)
                    for i in range(len(self._sub_models))
                ]
                inv = np.array([1.0 / q for q in qlikes])
                self._regime_weights[key] = inv / inv.sum()
            else:
                self._regime_weights[key] = np.full(
                    len(self._sub_models), 1.0 / len(self._sub_models)
                )

        self._weights = (
            self._regime_weights["high"] + self._regime_weights["low"]
        ) / 2.0

    @property
    def summary(self) -> dict[str, float]:
        s: dict[str, float] = {}
        if self._weights is not None:
            for i, w in enumerate(self._weights):
                s[f"weight_model_{i}"] = float(w)
        if self._per_model_qlike:
            for i, q in enumerate(self._per_model_qlike):
                s[f"qlike_model_{i}"] = float(q)
        if self._meta_intercept is not None:
            s["ridge_intercept"] = self._meta_intercept
        s["weights"] = (
            float(self._weights.sum()) if self._weights is not None else 0.0
        )
        return s
