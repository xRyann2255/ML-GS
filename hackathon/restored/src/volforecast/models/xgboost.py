"""XGBoost model with QLIKE custom objective (gradient boosting).

Implements XGBoost for tabular volatility forecasting with:
- Custom QLIKE objective function (gradient and hessian)
- Custom QLIKE evaluation metric
- Feature importance via built-in gain/split
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from volforecast.models._base import _BaseModel
from volforecast.registry import register_model

logger = logging.getLogger(__name__)
_CPU_COUNT = os.cpu_count() or 1


DEFAULT_PARAMS: dict[str, Any] = {
    "max_leaves": 31,
    "max_depth": 5,
    "min_child_weight": 50,
    "learning_rate": 0.05,
    "colsample_bytree": 0.8,
    "subsample": 0.8,
    "reg_lambda": 1.0,
    "nthread": 8,
    "verbosity": 0,
    "seed": 42,
    "tree_method": "hist",
    "grow_policy": "lossguide",
    "device": "cpu",
    "base_score": 0.0,
}

_INIT_ONLY_KEYS = frozenset(
    {
        "val_fraction",
        "val_purge_gap",
        "early_stopping_rounds",
        "n_estimators",
        "drop_features",
        "residual_scale",
        "sample_reweight",
        "objective",
        "device",
    }
)


def qlike_objective_xgb(y_pred: np.ndarray, dtrain: Any) -> tuple[np.ndarray, np.ndarray]:
    """Custom QLIKE objective for XGBoost.

    Log-space QLIKE: L = exp(y_true - y_pred) - (y_true - y_pred) - 1
    gradient (dL/dy_pred) = 1 - exp(y_true - y_pred)
    hessian  (d²L/dy_pred²) = exp(y_true - y_pred)

    Parameters
    ----------
    y_pred : np.ndarray
        Current predictions (log-RV space).
    dtrain : xgb.DMatrix
        Training dataset (labels accessed via get_label()).

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (gradient, hessian) pair.
    """
    y_true = dtrain.get_label()
    diff = np.clip(y_true - y_pred, -10.0, 10.0)
    exp_diff = np.exp(diff)
    grad = 1.0 - exp_diff
    hess = np.maximum(exp_diff, 1e-6)
    return grad, hess


def qlike_eval_xgb(y_pred: np.ndarray, dtrain: Any) -> list[tuple[str, float]]:
    """Custom QLIKE evaluation metric for XGBoost.

    Parameters
    ----------
    y_pred : np.ndarray
        Current predictions.
    dtrain : xgb.DMatrix
        Training dataset.

    Returns
    -------
    list[tuple[str, float]]
        [(metric_name, value)].
    """
    y_true = dtrain.get_label()
    diff = y_true - y_pred
    loss = float(np.mean(np.exp(np.clip(diff, -10.0, 10.0)) - diff - 1.0))
    return [("qlike", loss)]


@register_model("xgboost")
class XGBoostVolModel(_BaseModel):
    """XGBoost model for realized volatility forecasting.

    Optimizes QLIKE loss via custom objective. Supports feature
    importance analysis.

    Parameters are accepted as flat kwargs:
        max_leaves, learning_rate, colsample_bytree, etc.
    Plus training-control kwargs:
        n_estimators, early_stopping_rounds, val_fraction.
    """

    REQUIRED_LAYERS = [
        "har_core",
        "asymmetry",
        "noise_robust",
        "options",
        "calendar",
        "tree_expansion",
    ]
    name = "xgboost"
    family = "xgboost"
    description = "Gradient-boosted trees (XGBoost) with QLIKE custom objective"
    supports_tuning = True
    supports_fit_progress = True
    supports_shap_selection = True
    accepts_gpu_device = True

    def __init__(
        self,
        n_estimators: int = 1000,
        early_stopping_rounds: int = 100,
        val_fraction: float = 0.15,
        val_purge_gap: int = 5,
        base_model: str | None = None,
        residual_scale: float = 1.0,
        objective: str = "qlike",
        **kwargs: Any,
    ) -> None:
        self.base_model_name = base_model
        self.residual_scale = residual_scale
        self.objective = objective  # "qlike" or "mse"
        self.params = {**DEFAULT_PARAMS, **kwargs}
        self.n_estimators = n_estimators
        self.early_stopping_rounds = early_stopping_rounds
        self.val_fraction = val_fraction
        self.val_purge_gap = val_purge_gap
        self._model = None
        self._base_model = None
        self._init_score: float | None = None
        self._init_score_vector: np.ndarray | None = None
        self._feature_names: list[str] | None = None

    def get_params(self) -> dict[str, Any]:
        """Return params dict suitable for re-instantiation via cls(**params)."""
        params = {
            **self.params,
            "n_estimators": self.n_estimators,
            "early_stopping_rounds": self.early_stopping_rounds,
            "val_fraction": self.val_fraction,
            "val_purge_gap": self.val_purge_gap,
        }
        if self.objective != "qlike":
            params["objective"] = self.objective
        if self.base_model_name:
            params["base_model"] = self.base_model_name
        if self.residual_scale != 1.0:
            params["residual_scale"] = self.residual_scale
        return params

    def _clean_inputs(
        self, X: pd.DataFrame, y: pd.Series
    ) -> tuple[pd.DataFrame, pd.Series, np.ndarray | None]:
        """Sanitize inputs: drop features, replace Inf, filter rows, drop all-NaN cols.

        Returns (X_clean, y_clean, date_array). Sets ``self._feature_names``.
        """
        drop_features = self.params.get("drop_features", None)
        if drop_features:
            cols_to_drop = [c for c in drop_features if c in X.columns]
            if cols_to_drop:
                X = X.drop(columns=cols_to_drop)
                logger.info("Dropped %d features: %s", len(cols_to_drop), cols_to_drop[:5])

        X = X.replace([np.inf, -np.inf], np.nan)
        mask = y.notna() & ~X.isna().all(axis=1)

        date_array: np.ndarray | None = None
        if isinstance(X.index, pd.MultiIndex) and "date" in X.index.names:
            date_array = X.loc[mask].index.get_level_values("date").values

        X_clean = X.loc[mask].reset_index(drop=True)
        y_clean = y.loc[mask].reset_index(drop=True)

        nan_cols = X_clean.columns[X_clean.isna().all()]
        if len(nan_cols) > 0:
            X_clean = X_clean.drop(columns=nan_cols)

        if len(X_clean) == 0 or X_clean.shape[1] == 0:
            raise ValueError(
                f"Cannot fit XGBoost: {len(X_clean)} rows, "
                f"{X_clean.shape[1]} features after NaN removal."
            )

        self._feature_names = list(X_clean.columns)
        return X_clean, y_clean, date_array

    def _fit_base_model(
        self, X_clean: pd.DataFrame, y_clean: pd.Series, train_end_idx: int | None = None
    ) -> pd.Series:
        """Fit the base model for init_score and apply residual scaling.

        Sets ``self._base_model`` and ``self._init_score_vector``.
        Returns *y_clean* (possibly modified by residual scaling).

        Parameters
        ----------
        train_end_idx : int, optional
            If provided, fit the base model only on X_clean[:train_end_idx]
            (excluding validation rows), but predict on ALL rows for
            init_score_vector.
        """
        if self.base_model_name:
            from volforecast.registry import MODEL_REGISTRY, ensure_registered

            ensure_registered()
            base_cls = MODEL_REGISTRY[self.base_model_name]
            self._base_model = base_cls()

            if train_end_idx is not None:
                self._base_model.fit(X_clean.iloc[:train_end_idx], y_clean.iloc[:train_end_idx])
            else:
                self._base_model.fit(X_clean, y_clean)

            base_preds = self._base_model.predict(X_clean)
            scalar_mean = float(y_clean.mean())
            nan_mask = np.isnan(base_preds)
            if nan_mask.any():
                base_preds[nan_mask] = scalar_mean
            self._init_score_vector = base_preds
            self._init_score = None

            if self.residual_scale != 1.0:
                residual = y_clean.values - base_preds
                y_clean = pd.Series(
                    base_preds + self.residual_scale * residual,
                    index=y_clean.index,
                )
                logger.info(
                    "Residual scaling: factor=%.1f, residual std %.4f -> %.4f",
                    self.residual_scale,
                    residual.std(),
                    residual.std() * self.residual_scale,
                )
        else:
            self._base_model = None
            self._init_score_vector = None

        return y_clean

    def _build_val_split(
        self,
        X_clean: pd.DataFrame,
        y_clean: pd.Series,
        date_array: np.ndarray | None,
    ) -> tuple[int, int]:
        """Compute train/val split indices with date-aware purge for panel data.

        Returns ``(split_idx, val_start)`` — always returns valid indices.
        If the purged holdout would be too small, degrades to no-purge split.
        """
        n = len(X_clean)
        split_idx = int(n * (1.0 - self.val_fraction))

        if date_array is not None:
            unique_dates_after = np.unique(date_array[split_idx:])
            unique_dates_after.sort()
            if len(unique_dates_after) > self.val_purge_gap:
                val_start_date = unique_dates_after[self.val_purge_gap]
                val_start = (
                    int(np.searchsorted(date_array[split_idx:], val_start_date, side="left"))
                    + split_idx
                )
            else:
                val_start = n
            logger.debug(
                "Panel val purge: gap=%d dates, split_idx=%d, val_start=%d (skipped %d rows)",
                self.val_purge_gap,
                split_idx,
                val_start,
                val_start - split_idx,
            )
        else:
            val_start = split_idx + self.val_purge_gap

        if val_start >= n - 20:
            val_start = split_idx
        return split_idx, val_start

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        on_progress: Any | None = None,
    ) -> XGBoostVolModel:
        """Fit XGBoost with QLIKE custom objective.

        When val_fraction > 0, splits the last val_fraction of training data
        as validation for early stopping. When val_fraction == 0,
        trains on all data with fixed n_estimators (no early stopping).

        Parameters
        ----------
        X : pd.DataFrame
            Training features (log-space).
        y : pd.Series
            Training target (log RV).
        on_progress : callable, optional
            Called with (current_round, total_rounds) during training.

        Returns
        -------
        XGBoostVolModel
            Fitted model (self).
        """
        import xgboost as xgb

        X_clean, y_clean, date_array = self._clean_inputs(X, y)

        # Compute val split BEFORE fitting base model so base model
        # never trains on the early-stopping validation tail.
        if self.val_fraction > 0:
            split_idx, val_start = self._build_val_split(X_clean, y_clean, date_array)
        else:
            split_idx = None
            val_start = None

        y_clean = self._fit_base_model(X_clean, y_clean, train_end_idx=split_idx)

        # Build train params (exclude init-only keys)
        train_params = {k: v for k, v in self.params.items() if k not in _INIT_ONLY_KEYS}
        # device must reach xgb.train even though it's in _INIT_ONLY_KEYS (not HPO-searchable)
        if "device" in self.params:
            train_params["device"] = self.params["device"]

        # Determine objective/metric configuration
        use_mse = self.objective == "mse"
        if use_mse:
            train_params["objective"] = "reg:squarederror"
            obj_fn = None
            custom_metric_fn = None
            es_metric = "rmse"
        else:
            obj_fn = qlike_objective_xgb
            custom_metric_fn = qlike_eval_xgb
            es_metric = "qlike"

        # Parse sample_reweight config
        reweight_cfg = self.params.get("sample_reweight")
        reweight_enabled = reweight_cfg and reweight_cfg.get("enabled", False)

        if self.val_fraction > 0:
            X_train, X_val = X_clean.iloc[:split_idx], X_clean.iloc[val_start:]
            y_train, y_val = y_clean.iloc[:split_idx], y_clean.iloc[val_start:]

            if self._init_score_vector is not None:
                init_train = self._init_score_vector[:split_idx]
                init_val = self._init_score_vector[val_start:]
            else:
                self._init_score = float(y_train.mean())
                init_train = np.full(len(X_train), self._init_score)
                init_val = np.full(len(X_val), self._init_score)

            # --- Pass 1: fit without weights (or single pass if reweight disabled) ---
            dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self._feature_names)
            dval = xgb.DMatrix(X_val, label=y_val, feature_names=self._feature_names)
            dtrain.set_base_margin(init_train)
            dval.set_base_margin(init_val)

            callbacks = [
                xgb.callback.EarlyStopping(
                    rounds=self.early_stopping_rounds,
                    metric_name=es_metric,
                    maximize=False,
                    save_best=True,
                ),
            ]

            train_kwargs: dict[str, Any] = {
                "params": train_params,
                "dtrain": dtrain,
                "num_boost_round": self.n_estimators,
                "evals": [(dval, "val")],
                "verbose_eval": False,
                "callbacks": callbacks,
            }
            if obj_fn is not None:
                train_kwargs["obj"] = obj_fn
            if custom_metric_fn is not None:
                train_kwargs["custom_metric"] = custom_metric_fn

            self._model = xgb.train(**train_kwargs)

            # --- Pass 2: reweight and retrain if enabled ---
            if reweight_enabled:
                weights = self._compute_reweight(
                    X_train, y_train, init_train, reweight_cfg,
                )
                dtrain_w = xgb.DMatrix(
                    X_train, label=y_train, weight=weights,
                    feature_names=self._feature_names,
                )
                dtrain_w.set_base_margin(init_train)
                # Fresh callbacks (EarlyStopping is stateful, cannot reuse)
                callbacks_p2 = [
                    xgb.callback.EarlyStopping(
                        rounds=self.early_stopping_rounds,
                        metric_name=es_metric,
                        maximize=False,
                        save_best=True,
                    ),
                ]
                # Val set is NOT reweighted
                train_kwargs_p2: dict[str, Any] = {
                    "params": train_params,
                    "dtrain": dtrain_w,
                    "num_boost_round": self.n_estimators,
                    "evals": [(dval, "val")],
                    "verbose_eval": False,
                    "callbacks": callbacks_p2,
                }
                if obj_fn is not None:
                    train_kwargs_p2["obj"] = obj_fn
                if custom_metric_fn is not None:
                    train_kwargs_p2["custom_metric"] = custom_metric_fn

                self._model = xgb.train(**train_kwargs_p2)
        else:
            # No validation — train on all data
            if self._init_score_vector is not None:
                init_all = self._init_score_vector
            else:
                self._init_score = float(y_clean.mean())
                init_all = np.full(len(X_clean), self._init_score)

            dtrain = xgb.DMatrix(X_clean, label=y_clean, feature_names=self._feature_names)
            dtrain.set_base_margin(init_all)

            train_kwargs_noval: dict[str, Any] = {
                "params": train_params,
                "dtrain": dtrain,
                "num_boost_round": self.n_estimators,
                "verbose_eval": False,
            }
            if obj_fn is not None:
                train_kwargs_noval["obj"] = obj_fn

            self._model = xgb.train(**train_kwargs_noval)

            # --- Pass 2: reweight and retrain if enabled (no-val path) ---
            if reweight_enabled:
                weights = self._compute_reweight(
                    X_clean, y_clean, init_all, reweight_cfg,
                )
                dtrain_w = xgb.DMatrix(
                    X_clean, label=y_clean, weight=weights,
                    feature_names=self._feature_names,
                )
                dtrain_w.set_base_margin(init_all)
                train_kwargs_noval_p2: dict[str, Any] = {
                    "params": train_params,
                    "dtrain": dtrain_w,
                    "num_boost_round": self.n_estimators,
                    "verbose_eval": False,
                }
                if obj_fn is not None:
                    train_kwargs_noval_p2["obj"] = obj_fn

                self._model = xgb.train(**train_kwargs_noval_p2)

        return self

    def _compute_reweight(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        init_score: np.ndarray,
        cfg: dict[str, Any],
    ) -> np.ndarray:
        """Compute per-sample QLIKE-importance weights from pass-1 model.

        Parameters
        ----------
        X : pd.DataFrame
            Training features.
        y : pd.Series
            Training targets (log RV).
        init_score : np.ndarray
            Base margin (HAR-IV init) for each sample.
        cfg : dict
            Reweight config with keys: alpha, source, clip_max, normalize.

        Returns
        -------
        np.ndarray
            Per-sample weights (mean=1 if normalize=True).
        """
        import xgboost as xgb

        alpha = cfg.get("alpha", 1.0)
        source = cfg.get("source", "conditional")
        clip_max = cfg.get("clip_max", 10.0)
        normalize = cfg.get("normalize", True)

        if source == "conditional":
            # Conditional QLIKE: residual after pass-1 tree predictions
            # predict() returns tree_output + base_score (0.0); full prediction = tree_output + init_score
            dmat = xgb.DMatrix(X, feature_names=self._feature_names)
            tree_output = self._model.predict(dmat)
            pass1_preds = tree_output + init_score
            diff = y.values - pass1_preds
        else:
            # Raw QLIKE: residual after init only (no tree correction)
            diff = y.values - init_score

        # Per-sample QLIKE: exp(y - pred) - (y - pred) - 1
        diff_clipped = np.clip(diff, -10.0, 10.0)
        per_sample_qlike = np.exp(diff_clipped) - diff_clipped - 1.0

        # Floor to avoid zero weights, raise to alpha, cap at clip_max
        weights = np.maximum(per_sample_qlike, 1e-4) ** alpha
        weights = np.minimum(weights, clip_max)

        # Normalize to mean=1 to preserve effective regularization
        if normalize and weights.sum() > 0:
            weights = weights * (len(weights) / weights.sum())

        logger.info(
            "Sample reweight (source=%s, alpha=%.1f): "
            "weight stats mean=%.3f, std=%.3f, max=%.3f, >2x count=%d/%d",
            source, alpha,
            weights.mean(), weights.std(), weights.max(),
            int((weights > 2.0).sum()), len(weights),
        )

        return weights

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions.

        Parameters
        ----------
        X : pd.DataFrame
            Feature DataFrame.

        Returns
        -------
        np.ndarray
            Predicted log(RV) values.
        """
        if self._model is None:
            raise RuntimeError("Model has not been fitted")
        import xgboost as xgb

        dmat = xgb.DMatrix(X[self._feature_names], feature_names=self._feature_names)
        # XGBoost predict returns tree_output + base_score (base_score=0.0, so effectively tree output only)
        raw = self._model.predict(dmat)
        if self._base_model is not None:
            if self.residual_scale != 1.0:
                raw = raw / self.residual_scale
            base_preds = self._base_model.predict(X)
            nan_mask = np.isnan(base_preds)
            if nan_mask.any():
                fallback = float(np.nanmean(base_preds))
                base_preds[nan_mask] = fallback
            return raw + base_preds
        return raw + self._init_score

    def get_feature_importance(self, top_n: int = 20) -> list[tuple[str, float]]:
        """Return top-N features by gain importance as (name, pct) pairs."""
        if self._model is None:
            return []
        scores = self._model.get_score(importance_type="gain")
        total = sum(scores.values())
        if total == 0:
            return []
        pairs = sorted(
            [(name, val / total * 100) for name, val in scores.items()],
            key=lambda x: -x[1],
        )
        return pairs[:top_n]

    @property
    def summary(self) -> dict[str, float]:
        """Feature importance (gain) as dict."""
        if self._model is None:
            return {}
        return {name: float(val) for name, val in self._model.get_score(importance_type="gain").items()}

    @classmethod
    def tune_and_fit(
        cls,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        tuning_config,
        base_params: dict[str, Any] | None = None,
    ) -> XGBoostVolModel:
        """Tune hyperparameters via Optuna inner CV, then fit on full training fold.

        Parameters
        ----------
        X_train : pd.DataFrame
            Training features for this outer CV fold.
        y_train : pd.Series
            Training target for this outer CV fold.
        tuning_config : TuningConfig
            Tuning configuration (n_trials, timeout, inner_cv, storage_dir, etc.).
        base_params : dict, optional
            Config-level model params to preserve during tuning (e.g. seed,
            val_purge_gap). These are merged into every Optuna trial but not searched.

        Returns
        -------
        XGBoostVolModel
            Fitted model with Optuna-tuned hyperparameters.
        """
        from volforecast.config import CVConfig

        inner_cv = tuning_config.inner_cv
        if inner_cv is None:
            inner_train_size = max(252, len(X_train) // 2)
            inner_cv = CVConfig(
                method="expanding_window",
                purge_gap=5,
                train_size=inner_train_size,
                test_size=63,
            )

        storage_path = None
        if tuning_config.storage_dir:
            storage_path = Path(tuning_config.storage_dir)

        # Determine GPU device IDs from base_params
        gpu_device_ids = None
        device = None
        if base_params:
            device = base_params.get("device")
        if device and device.startswith("cuda"):
            # Multi-GPU: generate list of device IDs for workers
            import torch

            n_gpus = torch.cuda.device_count()
            if n_gpus > 0:
                gpu_device_ids = list(range(n_gpus))

        # Fit the base model (e.g. HAR-IV) so HPO inner CV uses it for init
        fitted_base_model = None
        base_model_name = base_params.get("base_model") if base_params else None
        if base_model_name:
            from volforecast.registry import MODEL_REGISTRY, ensure_registered

            ensure_registered()
            base_cls = MODEL_REGISTRY[base_model_name]
            fitted_base_model = base_cls()
            fitted_base_model.fit(X_train, y_train)

        best_params = tune_hyperparameters_xgb(
            X_train,
            y_train,
            cv_config=inner_cv,
            n_trials=tuning_config.n_trials,
            timeout=tuning_config.timeout,
            storage_path=storage_path,
            seed=base_params.get("seed", 42) if base_params else 42,
            on_trial_complete=tuning_config._on_trial_complete,
            on_hpo_event=tuning_config._on_hpo_event,
            base_params=base_params,
            n_workers=tuning_config.n_workers,
            gpu_device_ids=gpu_device_ids,
            base_model=fitted_base_model,
        )
        # n_estimators is no longer searched (early stopping handles it during HPO).
        # For the final model fit, use the config value (with early stopping in .fit()).
        default_n_est = base_params.get("n_estimators", 2000) if base_params else 2000
        n_est = best_params.pop("n_estimators", default_n_est)

        # Merge init-only keys from base_params (not searched, but needed for model init)
        if base_params:
            for k in _INIT_ONLY_KEYS:
                if k in base_params and k not in best_params and k != "n_estimators":
                    best_params[k] = base_params[k]

        model = cls(n_estimators=n_est, **best_params)
        model.fit(X_train, y_train)
        return model

    @property
    def feature_importance(self) -> dict[str, int]:
        """Feature importance (weight / split count) as dict."""
        if self._model is None:
            return {}
        return {name: int(val) for name, val in self._model.get_score(importance_type="weight").items()}


# ---------------------------------------------------------------------------
# Optuna HPO for XGBoost
# ---------------------------------------------------------------------------


def _make_study_name_xgb(base_params: dict[str, Any] | None) -> str:
    """Build a deterministic study name that includes a hash of relevant params.

    This ensures that when model params change (e.g. search ranges, base_model,
    feature config), old trials from a prior config are not reused.

    Excludes 'seed' from the hash since seed doesn't change model semantics.
    """
    import hashlib
    import json

    prefix = "xgboost_qlike"
    if not base_params:
        return prefix

    # Filter out keys that shouldn't affect the study identity
    exclude_keys = {"seed"}
    hashable = {k: v for k, v in sorted(base_params.items()) if k not in exclude_keys}

    # Convert to deterministic JSON and hash
    param_str = json.dumps(hashable, sort_keys=True, default=str)
    h = hashlib.sha256(param_str.encode()).hexdigest()[:12]
    return f"{prefix}_{h}"


def _prebuild_cv_folds_xgb(
    X: pd.DataFrame,
    y: pd.Series,
    cv_config: Any,
    val_fraction: float = 0.15,
    purge_gap: int = 10,
    base_model: Any | None = None,
):
    """Pre-build DMatrix objects and CV fold indices once (reused across all trials).

    For each inner CV fold, splits into train/val/test where val is used for
    early stopping and test for QLIKE evaluation.

    When the data has a MultiIndex with a 'date' level, splitting and purging
    operate on unique dates (not raw row indices) to prevent intra-day leakage
    in pooled panel data.

    When base_model is provided, uses base_model.predict() for base_margin
    instead of a constant mean.

    Returns list of (dtrain, dval, dtest, init_score, y_test_values) tuples.
    """
    import xgboost as xgb

    from volforecast.utils.cv import ExpandingWindowCV

    # Detect panel data with date level
    has_date_index = isinstance(X.index, pd.MultiIndex) and "date" in X.index.names

    if has_date_index:
        # Date-based splitting: operate on unique dates
        dates = X.index.get_level_values("date")
        unique_dates = dates.unique().sort_values()
        n_dates = len(unique_dates)

        test_sz = cv_config.test_size or 63
        train_sz = cv_config.train_size or 500
        purge = cv_config.purge_gap or 5
        available = n_dates - train_sz - purge - test_sz
        max_folds = 3
        step_size = max(test_sz, available // max_folds) if available > 0 else test_sz

        # Use ExpandingWindowCV on the date dimension
        splitter = ExpandingWindowCV(
            min_train_size=train_sz,
            test_size=test_sz,
            step_size=step_size,
            purge_gap=purge,
        )

        # Create a dummy array of length n_dates for the splitter
        dummy = pd.DataFrame({"x": np.zeros(n_dates)})
        folds = []
        for date_train_idx, date_test_idx in splitter.split(dummy):
            train_dates = unique_dates[date_train_idx]
            test_dates = unique_dates[date_test_idx]

            # Select rows belonging to train/test dates
            train_mask = dates.isin(train_dates)
            test_mask = dates.isin(test_dates)

            X_tr_full = X.loc[train_mask].reset_index(drop=True)
            y_tr_full = y.loc[train_mask].reset_index(drop=True)
            X_te = X.loc[test_mask].reset_index(drop=True)
            y_te = y.loc[test_mask].reset_index(drop=True)

            # Split train into train/val for early stopping
            n_train = len(X_tr_full)
            val_size = max(int(n_train * val_fraction), 20)
            val_purge_rows = purge_gap  # row-level purge between train/val within a fold
            split_idx = n_train - val_size - val_purge_rows
            val_start = n_train - val_size + val_purge_rows

            if split_idx < 50:
                split_idx = n_train
                val_start = None

            # Compute base_margin
            if base_model is not None:
                train_margin = base_model.predict(X_tr_full.iloc[:split_idx])
                nan_mask = np.isnan(train_margin)
                if nan_mask.any():
                    train_margin[nan_mask] = float(y_tr_full.iloc[:split_idx].mean())
                test_margin = base_model.predict(X_te)
                nan_mask_te = np.isnan(test_margin)
                if nan_mask_te.any():
                    test_margin[nan_mask_te] = float(y_tr_full.iloc[:split_idx].mean())
                init_score = 0.0  # placeholder — actual margin is per-sample
            else:
                init_score = float(y_tr_full.iloc[:split_idx].mean())
                train_margin = np.full(split_idx, init_score)
                test_margin = np.full(len(X_te), init_score)

            dtrain = xgb.DMatrix(X_tr_full.iloc[:split_idx], label=y_tr_full.iloc[:split_idx])
            dtrain.set_base_margin(train_margin)

            dval = None
            if val_start is not None and val_start < n_train:
                if base_model is not None:
                    val_margin = base_model.predict(X_tr_full.iloc[val_start:])
                    nan_mask_v = np.isnan(val_margin)
                    if nan_mask_v.any():
                        val_margin[nan_mask_v] = float(y_tr_full.iloc[:split_idx].mean())
                else:
                    val_margin = np.full(n_train - val_start, init_score)
                dval = xgb.DMatrix(X_tr_full.iloc[val_start:], label=y_tr_full.iloc[val_start:])
                dval.set_base_margin(val_margin)

            dtest = xgb.DMatrix(X_te)
            dtest.set_base_margin(test_margin)

            folds.append((dtrain, dval, dtest, init_score, y_te.values))

        return folds

    # --- Row-based splitting (non-panel data) ---
    n_data = len(X)
    test_sz = cv_config.test_size or 63
    train_sz = cv_config.train_size or 500
    available = n_data - train_sz - (cv_config.purge_gap or 5) - test_sz
    max_folds = 3
    step_size = max(test_sz, available // max_folds) if available > 0 else test_sz

    splitter = ExpandingWindowCV(
        min_train_size=train_sz,
        test_size=test_sz,
        step_size=step_size,
        purge_gap=cv_config.purge_gap,
    )

    folds = []
    for train_idx, test_idx in splitter.split(X, y):
        X_tr_full, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr_full, y_te = y.iloc[train_idx], y.iloc[test_idx]

        # Split train into train/val for early stopping (purge gap between them)
        n_train = len(X_tr_full)
        val_size = max(int(n_train * val_fraction), 20)
        val_start = n_train - val_size + purge_gap  # purge gap before val
        split_idx = n_train - val_size - purge_gap

        if split_idx < 50:
            # Not enough data for val split — use full train, no early stopping
            split_idx = n_train
            val_start = None

        # Compute base_margin
        if base_model is not None:
            train_margin = base_model.predict(X_tr_full.iloc[:split_idx])
            nan_mask = np.isnan(train_margin)
            if nan_mask.any():
                train_margin[nan_mask] = float(y_tr_full.iloc[:split_idx].mean())
            test_margin = base_model.predict(X_te)
            nan_mask_te = np.isnan(test_margin)
            if nan_mask_te.any():
                test_margin[nan_mask_te] = float(y_tr_full.iloc[:split_idx].mean())
            init_score = 0.0
        else:
            init_score = float(y_tr_full.iloc[:split_idx].mean())
            train_margin = np.full(split_idx, init_score)
            test_margin = np.full(len(X_te), init_score)

        dtrain = xgb.DMatrix(X_tr_full.iloc[:split_idx], label=y_tr_full.iloc[:split_idx])
        dtrain.set_base_margin(train_margin)

        dval = None
        if val_start is not None and val_start < n_train:
            if base_model is not None:
                val_margin = base_model.predict(X_tr_full.iloc[val_start:])
                nan_mask_v = np.isnan(val_margin)
                if nan_mask_v.any():
                    val_margin[nan_mask_v] = float(y_tr_full.iloc[:split_idx].mean())
            else:
                val_margin = np.full(n_train - val_start, init_score)
            dval = xgb.DMatrix(X_tr_full.iloc[val_start:], label=y_tr_full.iloc[val_start:])
            dval.set_base_margin(val_margin)

        dtest = xgb.DMatrix(X_te)
        dtest.set_base_margin(test_margin)

        folds.append((dtrain, dval, dtest, init_score, y_te.values))

    return folds


def _make_objective_xgb(
    X: pd.DataFrame,
    y: pd.Series,
    cv_config: Any,
    seed: int,
    base_params: dict[str, Any] | None,
    device: str,
    prebuilt_folds: list | None = None,
    base_model: Any | None = None,
):
    """Build an Optuna objective closure for QLIKE-optimized XGBoost tuning.

    Optimizations over naive approach:
    1. DMatrix objects pre-built once (not per trial) — saves ~30% time
    2. Early stopping on val split replaces searching n_estimators — removes
       a search dimension AND avoids wasteful over-training
    3. Optuna MedianPruner prunes after fold 1 if QLIKE is worse than median
    """
    import optuna
    import xgboost as xgb

    from volforecast.evaluation.metrics import qlike

    # Pre-build folds if not provided (single-worker path)
    if prebuilt_folds is None:
        prebuilt_folds = _prebuild_cv_folds_xgb(X, y, cv_config, base_model=base_model)

    # Fixed n_estimators with early stopping (no longer a search param)
    max_rounds = 2000
    early_stopping_rounds = 100

    def objective(trial: optuna.Trial) -> float:
        params = {
            "max_leaves": trial.suggest_int("max_leaves", 8, 128),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.1, log=True),
            "min_child_weight": trial.suggest_int("min_child_weight", 20, 300),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
            "tree_method": "hist",
            "grow_policy": "lossguide",
            "device": device,
            "nthread": 8,
            "verbosity": 0,
            "seed": seed,
        }

        if base_params:
            for k, v in base_params.items():
                if k not in params and k not in _INIT_ONLY_KEYS:
                    params[k] = v

        # Build train params (exclude init-only keys)
        train_params = {k: v for k, v in params.items() if k not in _INIT_ONLY_KEYS}
        # device must reach xgb.train even though it's in _INIT_ONLY_KEYS (not HPO-searchable)
        if "device" in params:
            train_params["device"] = params["device"]

        scores: list[float] = []
        for fold_idx, (dtrain, dval, dtest, init_score, y_te) in enumerate(prebuilt_folds):
            try:
                if dval is not None:
                    callbacks = [
                        xgb.callback.EarlyStopping(
                            rounds=early_stopping_rounds,
                            metric_name="qlike",
                            maximize=False,
                            save_best=True,
                        ),
                    ]
                    model = xgb.train(
                        params=train_params,
                        dtrain=dtrain,
                        num_boost_round=max_rounds,
                        evals=[(dval, "val")],
                        obj=qlike_objective_xgb,
                        custom_metric=qlike_eval_xgb,
                        verbose_eval=False,
                        callbacks=callbacks,
                    )
                else:
                    model = xgb.train(
                        params=train_params,
                        dtrain=dtrain,
                        num_boost_round=max_rounds,
                        obj=qlike_objective_xgb,
                        verbose_eval=False,
                    )
            except Exception:
                raise optuna.TrialPruned()

            pred = model.predict(dtest)
            scores.append(qlike(y_te, pred))

            trial.report(float(np.mean(scores)), fold_idx)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return float(np.mean(scores))

    return objective


def _make_trial_done_callback_xgb(progress_queue: Any | None, device_id: int):
    """Create an Optuna callback that emits trial-complete events via queue."""

    def callback(study, frozen_trial) -> None:  # noqa: ANN001
        if progress_queue is None:
            return
        params = frozen_trial.params
        state = frozen_trial.state.name  # COMPLETE, PRUNED, FAIL
        qlike = frozen_trial.value if frozen_trial.value is not None else float("inf")
        progress_queue.put({
            "type": "tuning_trial_complete",
            "trial_num": frozen_trial.number,
            "qlike": qlike,
            "params": params,
            "device_id": device_id,
            "state": state,
        })

    return callback


def _optuna_worker_xgb(
    worker_id: int,
    n_trials_per_worker: int,
    X_path_or_data: Any,
    y_path_or_data: Any,
    cv_config_dict: dict,
    timeout: int | None,
    journal_path: str,
    seed: int,
    base_params: dict[str, Any] | None,
    device: str,
    progress_queue: Any | None = None,
) -> int:
    """Single Optuna worker process for XGBoost tuning.

    Each worker pins to a specific GPU device (or CPU) and runs its share
    of trials. All workers share a JournalStorage file for coordination.
    Emits progress events via progress_queue for nested progress bars.
    """
    import optuna

    from volforecast.config import CVConfig

    X = X_path_or_data
    y = y_path_or_data
    cv_cfg = CVConfig(**cv_config_dict)

    # Extract device_id from device string (e.g. "cuda:3" -> 3)
    device_id = int(device.split(":")[1]) if ":" in device else worker_id

    # Fit the base model locally (can't pickle across processes)
    fitted_base_model = None
    base_model_name = base_params.get("base_model") if base_params else None
    if base_model_name:
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        base_cls = MODEL_REGISTRY[base_model_name]
        fitted_base_model = base_cls()
        fitted_base_model.fit(X, y)

    # Pre-build DMatrix objects once per worker (reused across all trials)
    prebuilt_folds = _prebuild_cv_folds_xgb(X, y, cv_cfg, base_model=fitted_base_model)

    journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
    storage = optuna.storages.JournalStorage(journal_backend)

    objective = _make_objective_xgb(X, y, cv_cfg, seed, base_params, device, prebuilt_folds)

    study_name = _make_study_name_xgb(base_params)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction="minimize",
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=seed + worker_id, n_startup_trials=10),
        pruner=optuna.pruners.MedianPruner(
            n_startup_trials=10,
            n_warmup_steps=1,
        ),
    )
    study.optimize(
        objective,
        n_trials=n_trials_per_worker,
        timeout=timeout,
        n_jobs=1,
        catch=(Exception,),
        callbacks=[_make_trial_done_callback_xgb(progress_queue, device_id)],
    )
    return n_trials_per_worker


def tune_hyperparameters_xgb(
    X: pd.DataFrame,
    y: pd.Series,
    cv_config: Any | None = None,
    n_trials: int = 50,
    timeout: int | None = 3600,
    storage_path: Path | None = None,
    seed: int = 42,
    on_trial_complete: Any | None = None,
    on_hpo_event: Any | None = None,
    base_params: dict[str, Any] | None = None,
    n_workers: int = 1,
    gpu_device_ids: list[int] | None = None,
    base_model: Any | None = None,
) -> dict[str, Any]:
    """Tune XGBoost hyperparameters via Optuna with walk-forward CV.

    Uses ExpandingWindowCV (walk-forward) to prevent look-ahead bias.
    Optimizes QLIKE loss with TPE sampler.

    When gpu_device_ids is provided, each worker is pinned to a separate
    GPU (round-robin). With 8 GPUs and 8 workers, all trials run in
    parallel on different devices.

    Parameters
    ----------
    X : pd.DataFrame
        Full training features.
    y : pd.Series
        Full training target (log RV).
    cv_config : CVConfig, optional
        CV configuration. Defaults to expanding window.
    n_trials : int
        Total number of Optuna trials (default: 50).
    timeout : int, optional
        Maximum seconds for optimization (default: 3600).
    storage_path : Path, optional
        Path for study storage (enables resume).
    seed : int
        Random seed for reproducibility (default: 42).
    on_trial_complete : callable, optional
        Progress callback, called with total completed trial count.
    base_params : dict, optional
        Fixed params to merge into every trial.
    n_workers : int
        Number of parallel worker processes (default: 1).
    gpu_device_ids : list[int], optional
        GPU device indices for multi-GPU training. When provided,
        worker i uses device cuda:{gpu_device_ids[i % len(gpu_device_ids)]}.

    Returns
    -------
    dict[str, Any]
        Best hyperparameters found.
    """
    import optuna

    from volforecast.config import CVConfig

    # Fit base model from name if not provided as pre-fitted instance
    if base_model is None:
        base_model_name = base_params.get("base_model") if base_params else None
        if base_model_name:
            from volforecast.registry import MODEL_REGISTRY, ensure_registered

            ensure_registered()
            base_cls = MODEL_REGISTRY[base_model_name]
            base_model = base_cls()
            base_model.fit(X, y)

    if cv_config is None:
        cv_config = CVConfig(
            method="expanding_window",
            n_splits=5,
            purge_gap=5,
            train_size=500,
            test_size=63,
        )

    if storage_path is None:
        import tempfile

        storage_path = Path(tempfile.mkdtemp()) / "optuna_xgb_study"

    storage_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path = str(storage_path.with_suffix(".journal"))

    # Determine effective worker count
    if gpu_device_ids:
        # With GPUs: cap workers at number of GPUs
        effective_workers = min(n_workers, len(gpu_device_ids))
    else:
        # CPU mode: cap at cores / 8 threads per trial
        max_workers = min(16, max(1, _CPU_COUNT // 8))
        effective_workers = min(n_workers, max_workers)

    if effective_workers < n_workers:
        logger.info(
            "Capping n_workers from %d to %d (GPUs=%s, CPU cores=%d)",
            n_workers,
            effective_workers,
            gpu_device_ids,
            _CPU_COUNT,
        )

    logger.info(
        "XGBoost Optuna: %d trials across %d workers (GPU IDs: %s)",
        n_trials,
        effective_workers,
        gpu_device_ids,
    )

    cv_config_dict = {
        "method": cv_config.method,
        "n_splits": cv_config.n_splits,
        "purge_gap": cv_config.purge_gap,
        "train_size": cv_config.train_size,
        "test_size": cv_config.test_size,
    }

    # Set up progress queue for multi-GPU events
    progress_queue = None
    if on_hpo_event and effective_workers > 1:
        import multiprocessing as mp

        mgr = mp.Manager()
        progress_queue = mgr.Queue()

    # Emit tuning_start event
    if on_hpo_event:
        on_hpo_event({
            "type": "tuning_start",
            "n_trials": n_trials,
            "n_gpus": effective_workers,
            "max_epochs": 0,  # XGBoost doesn't have epochs; folds are fast
        })

    if effective_workers > 1:
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor

        ctx = mp.get_context("spawn")
        trials_per_worker = n_trials // effective_workers
        remainder = n_trials % effective_workers

        futures = []
        with ProcessPoolExecutor(max_workers=effective_workers, mp_context=ctx) as executor:
            for i in range(effective_workers):
                worker_trials = trials_per_worker + (1 if i < remainder else 0)
                # Pin each worker to a GPU (round-robin)
                if gpu_device_ids:
                    device = f"cuda:{gpu_device_ids[i % len(gpu_device_ids)]}"
                else:
                    device = "cpu"

                future = executor.submit(
                    _optuna_worker_xgb,
                    worker_id=i,
                    n_trials_per_worker=worker_trials,
                    X_path_or_data=X,
                    y_path_or_data=y,
                    cv_config_dict=cv_config_dict,
                    timeout=timeout,
                    journal_path=journal_path,
                    seed=seed,
                    base_params=base_params,
                    device=device,
                    progress_queue=progress_queue,
                )
                futures.append(future)

            # Poll progress: consume queue events + journal for trial count
            import time

            study_name = _make_study_name_xgb(base_params)
            initial_count = 0
            try:
                jb = optuna.storages.journal.JournalFileBackend(journal_path)
                st = optuna.storages.JournalStorage(jb)
                study_tmp = optuna.load_study(
                    study_name=study_name,
                    storage=st,
                    load_if_exists=True,
                )
                initial_count = len([t for t in study_tmp.trials if t.state.is_finished()])
            except Exception:
                pass

            reported = 0
            while True:
                done_futures = [f for f in futures if f.done()]

                # Drain progress queue events
                if progress_queue is not None:
                    while not progress_queue.empty():
                        try:
                            event = progress_queue.get_nowait()
                            if on_hpo_event:
                                on_hpo_event(event)
                        except Exception:
                            break

                # Poll journal for completed trial count (for simple callback)
                if on_trial_complete:
                    try:
                        jb = optuna.storages.journal.JournalFileBackend(journal_path)
                        st = optuna.storages.JournalStorage(jb)
                        study_tmp = optuna.load_study(
                            study_name=study_name,
                            storage=st,
                            load_if_exists=True,
                        )
                        n_done = (
                            len([t for t in study_tmp.trials if t.state.is_finished()])
                            - initial_count
                        )
                        if n_done > reported:
                            on_trial_complete(n_done)
                            reported = n_done
                    except Exception:
                        pass

                if len(done_futures) == len(futures):
                    # Drain any remaining queue events
                    if progress_queue is not None:
                        while not progress_queue.empty():
                            try:
                                event = progress_queue.get_nowait()
                                if on_hpo_event:
                                    on_hpo_event(event)
                            except Exception:
                                break
                    break
                time.sleep(0.5)

            total_completed = sum(f.result() for f in futures)

        logger.info("Multi-process XGBoost tuning complete: %d trials finished", total_completed)

        if on_trial_complete:
            on_trial_complete(n_trials)

        # Emit tuning_complete event
        study_name = _make_study_name_xgb(base_params)
        journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
        storage = optuna.storages.JournalStorage(journal_backend)
        study = optuna.load_study(
            study_name=study_name,
            storage=storage,
        )
        if on_hpo_event:
            completed_trials = [t for t in study.trials if t.state.name == "COMPLETE"]
            pruned_trials = [t for t in study.trials if t.state.name == "PRUNED"]
            best_qlike = study.best_value if completed_trials else float("inf")
            best_trial_num = study.best_trial.number if completed_trials else -1
            best_params = study.best_params if completed_trials else {}
            on_hpo_event({
                "type": "tuning_complete",
                "n_completed": len(completed_trials),
                "n_pruned": len(pruned_trials),
                "best_qlike": best_qlike,
                "best_trial": best_trial_num,
                "best_params": best_params,
            })
    else:
        # Single-process path
        journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
        storage = optuna.storages.JournalStorage(journal_backend)

        device = "cpu"
        if gpu_device_ids:
            device = f"cuda:{gpu_device_ids[0]}"
        device_id = int(device.split(":")[1]) if ":" in device else 0

        # Pre-build DMatrix objects once (reused across all trials)
        prebuilt_folds = _prebuild_cv_folds_xgb(X, y, cv_config, base_model=base_model)

        objective = _make_objective_xgb(X, y, cv_config, seed, base_params, device, prebuilt_folds)

        def _callback(study, frozen_trial):  # noqa: ARG001
            if on_trial_complete:
                n_complete = len([t for t in study.trials if t.state.is_finished()])
                on_trial_complete(n_complete)
            if on_hpo_event:
                state = frozen_trial.state.name
                qlike = frozen_trial.value if frozen_trial.value is not None else float("inf")
                on_hpo_event({
                    "type": "tuning_trial_complete",
                    "trial_num": frozen_trial.number,
                    "qlike": qlike,
                    "params": frozen_trial.params,
                    "device_id": device_id,
                    "state": state,
                })

        study_name = _make_study_name_xgb(base_params)
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(
            direction="minimize",
            study_name=study_name,
            storage=storage,
            load_if_exists=True,
            sampler=optuna.samplers.TPESampler(seed=seed, n_startup_trials=10),
            pruner=optuna.pruners.MedianPruner(
                n_startup_trials=10,
                n_warmup_steps=1,
            ),
        )
        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            n_jobs=1,
            callbacks=[_callback],
            catch=(Exception,),
        )

        # Emit tuning_complete for single-process
        if on_hpo_event:
            completed_trials = [t for t in study.trials if t.state.name == "COMPLETE"]
            pruned_trials = [t for t in study.trials if t.state.name == "PRUNED"]
            best_qlike = study.best_value if completed_trials else float("inf")
            best_trial_num = study.best_trial.number if completed_trials else -1
            best_params_result = study.best_params if completed_trials else {}
            on_hpo_event({
                "type": "tuning_complete",
                "n_completed": len(completed_trials),
                "n_pruned": len(pruned_trials),
                "best_qlike": best_qlike,
                "best_trial": best_trial_num,
                "best_params": best_params_result,
            })

    # Extract best params
    try:
        best = study.best_params
    except ValueError:
        logger.warning("All %d XGBoost Optuna trials pruned/failed; returning defaults", n_trials)
        best = {
            "max_leaves": 31,
            "max_depth": 5,
            "min_child_weight": 50,
            "learning_rate": 0.05,
            "n_estimators": 1000,
        }

    # Merge base_params
    if base_params:
        for k, v in base_params.items():
            if k not in best and k not in _INIT_ONLY_KEYS:
                best[k] = v
    return best
