"""LightGBM model with QLIKE custom objective (gradient boosting).

Implements LightGBM for tabular volatility forecasting with:
- Custom QLIKE objective function (gradient and hessian)
- Custom QLIKE evaluation metric
- Feature importance via built-in gain/split
- Hyperparameter tuning with purged k-fold CV
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
    "num_leaves": 31,
    "max_depth": 5,
    "min_child_samples": 50,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "reg_lambda": 1.0,
    # 8 threads is empirically optimal for LightGBM with custom objectives on
    # data sizes 500-25K rows. More threads = OpenMP sync overhead dominates.
    # (Benchmarked on 208-core H100 node: 8 threads ≈ 0.4s, 208 threads ≈ 4min
    # for 500 rounds on 2000 rows.)
    "num_threads": 8,
    "verbose": -1,
    "seed": 42,
    # Disable feature_pre_filter: it can trigger a fatal C++ assertion
    # (num_features > 0) when combined with aggressive feature_fraction or
    # min_child_samples on small CV folds. The assertion aborts threads
    # uncatchably, deadlocking Optuna's parallel trial pool.
    "feature_pre_filter": False,
}

# NOTE: GPU is NOT used for training because our custom QLIKE objective forces
# a CPU↔GPU sync barrier every boosting round (gradient computed in Python,
# tree built on GPU). With 208 CPU cores, parallel CPU training is faster.
# GPU would only help with built-in objectives (binary, regression, etc.).
# See: https://lightgbm.readthedocs.io/en/latest/GPU-Tutorial.html

# Keys not searched by Optuna — training-control params handled separately.
_INIT_ONLY_KEYS = frozenset(
    {
        "val_fraction",
        "val_purge_gap",
        "early_stopping_rounds",
        "n_estimators",
        "gpu_device_id",
        "drop_features",
        "monotone_constraints_named",
        "residual_scale",
        "sample_reweight",
    }
)


def qlike_objective(y_pred: np.ndarray, dtrain: Any) -> tuple[np.ndarray, np.ndarray]:
    """Custom QLIKE objective for LightGBM.

    Log-space QLIKE: L = exp(y_true - y_pred) - (y_true - y_pred) - 1
    gradient (dL/dy_pred) = 1 - exp(y_true - y_pred)
    hessian  (d²L/dy_pred²) = exp(y_true - y_pred)

    Parameters
    ----------
    y_pred : np.ndarray
        Current predictions (log-RV space).
    dtrain : lgb.Dataset
        Training dataset (labels accessed via get_label()).

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (gradient, hessian) pair.
    """
    y_true = dtrain.get_label()
    # Symmetric clip: pure overflow protection. exp(709) overflows float64.
    # Data range is ~10 (log RV spans -14 to -4), so ±10 covers all cases.
    # QLIKE's natural exponential already penalizes under-prediction harder.
    diff = np.clip(y_true - y_pred, -10.0, 10.0)
    exp_diff = np.exp(diff)
    grad = 1.0 - exp_diff
    hess = np.maximum(exp_diff, 1e-6)
    return grad, hess


def _make_weighted_qlike_objective(
    weights: np.ndarray,
) -> callable:
    """Create a QLIKE objective with per-sample weights baked in.

    LightGBM ignores Dataset.weight when a custom objective is used.
    This closure multiplies grad and hess by the weight vector, which
    changes the split gain criterion (weighted samples influence splits more).
    """

    def weighted_qlike_objective(
        y_pred: np.ndarray, dtrain: Any
    ) -> tuple[np.ndarray, np.ndarray]:
        y_true = dtrain.get_label()
        diff = np.clip(y_true - y_pred, -10.0, 10.0)
        exp_diff = np.exp(diff)
        grad = (1.0 - exp_diff) * weights
        hess = np.maximum(exp_diff, 1e-6) * weights
        return grad, hess

    return weighted_qlike_objective


def qlike_eval(y_pred: np.ndarray, dtrain: Any) -> tuple[str, float, bool]:
    """Custom QLIKE evaluation metric for LightGBM.

    Parameters
    ----------
    y_pred : np.ndarray
        Current predictions.
    dtrain : lgb.Dataset
        Training dataset.

    Returns
    -------
    tuple[str, float, bool]
        (metric_name, value, is_higher_better).
    """
    y_true = dtrain.get_label()
    diff = y_true - y_pred
    # Symmetric clip: overflow protection only. Matches qlike_objective.
    loss = float(np.mean(np.exp(np.clip(diff, -10.0, 10.0)) - diff - 1.0))
    return "qlike", loss, False


@register_model("lightgbm")
class LightGBMVolModel(_BaseModel):
    """LightGBM model for realized volatility forecasting.

    Optimizes QLIKE loss via custom objective. Supports feature
    importance analysis and hyperparameter tuning.

    Parameters are accepted as flat kwargs (consistent with HAR models):
        num_leaves, learning_rate, feature_fraction, etc.
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
    name = "lightgbm"
    family = "lightgbm"
    description = "Gradient-boosted trees with QLIKE custom objective"
    supports_tuning = True

    def get_feature_importance(self, top_n: int = 20) -> list[tuple[str, float]]:
        """Return top-N features by gain importance as (name, pct) pairs."""
        if self._model is None:
            return []
        importance = self._model.feature_importance(importance_type="gain")
        names = self._model.feature_name()
        total = importance.sum()
        if total == 0:
            return []
        pairs = sorted(zip(names, importance / total * 100), key=lambda x: -x[1])
        return pairs[:top_n]

    @classmethod
    def tune_and_fit(
        cls,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        tuning_config,
        base_params: dict[str, Any] | None = None,
    ) -> LightGBMVolModel:
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
            Config-level model params to preserve during tuning (e.g. boosting_type,
            drop_rate). These are merged into every Optuna trial but not searched over.

        Returns
        -------
        LightGBMVolModel
            Fitted model with Optuna-tuned hyperparameters.
        """
        from volforecast.config import CVConfig

        # Build inner CV config: use explicit inner_cv if provided, else derive from outer fold
        inner_cv = tuning_config.inner_cv
        if inner_cv is None:
            inner_train_size = max(252, len(X_train) // 2)
            inner_cv = CVConfig(
                method="expanding_window",
                purge_gap=5,
                train_size=inner_train_size,
                test_size=63,
            )

        # Resolve storage path (None = in-memory)
        storage_path = None
        if tuning_config.storage_dir:
            storage_path = Path(tuning_config.storage_dir)

        best_params = tune_hyperparameters(
            X_train,
            y_train,
            cv_config=inner_cv,
            n_trials=tuning_config.n_trials,
            timeout=tuning_config.timeout,
            storage_path=storage_path,
            on_trial_complete=tuning_config._on_trial_complete,
            base_params=base_params,
            n_jobs=tuning_config.n_jobs,
            n_workers=tuning_config.n_workers,
        )
        n_est = best_params.pop("n_estimators", 1000)
        model = cls(n_estimators=n_est, **best_params)
        model.fit(X_train, y_train, on_progress=tuning_config._on_train_progress)
        return model

    def __init__(
        self,
        n_estimators: int = 1000,
        early_stopping_rounds: int = 100,
        val_fraction: float = 0.15,
        val_purge_gap: int = 5,
        base_model: str | None = None,
        residual_scale: float = 1.0,
        **kwargs: Any,
    ) -> None:
        self.base_model_name = base_model
        self.residual_scale = residual_scale
        self.params = {**DEFAULT_PARAMS, **kwargs}
        self.n_estimators = n_estimators
        self.early_stopping_rounds = early_stopping_rounds
        self.val_fraction = val_fraction
        self.val_purge_gap = val_purge_gap
        self._model = None
        self._base_model = None
        self._feature_names: list[str] | None = None
        self._selected_features: list[str] | None = None
        self._selection_metadata: dict | None = None

    def get_params(self) -> dict[str, Any]:
        """Return params dict suitable for re-instantiation via cls(**params)."""
        params = {
            **self.params,
            "n_estimators": self.n_estimators,
            "early_stopping_rounds": self.early_stopping_rounds,
            "val_fraction": self.val_fraction,
            "val_purge_gap": self.val_purge_gap,
        }
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
        # Horizon-specific feature selection: drop columns listed in params.
        drop_features = self.params.pop("drop_features", None)
        if drop_features:
            cols_to_drop = [c for c in drop_features if c in X.columns]
            if cols_to_drop:
                X = X.drop(columns=cols_to_drop)
                logger.info("Dropped %d features: %s", len(cols_to_drop), cols_to_drop[:5])

        # LightGBM handles NaN features natively (routes to best split).
        # Only drop rows where the target is NaN or all features are NaN.
        X = X.replace([np.inf, -np.inf], np.nan)
        mask = y.notna() & ~X.isna().all(axis=1)

        # Detect panel (pooled multi-symbol) data: MultiIndex with 'date' level.
        date_array: np.ndarray | None = None
        if isinstance(X.index, pd.MultiIndex) and "date" in X.index.names:
            date_array = X.loc[mask].index.get_level_values("date").values

        X_clean = X.loc[mask].reset_index(drop=True)
        y_clean = y.loc[mask].reset_index(drop=True)

        # Drop columns that are entirely NaN — LightGBM's feature_pre_filter
        # can crash with "num_features > 0" assertion if all cols are dropped.
        nan_cols = X_clean.columns[X_clean.isna().all()]
        if len(nan_cols) > 0:
            X_clean = X_clean.drop(columns=nan_cols)

        if len(X_clean) == 0 or X_clean.shape[1] == 0:
            raise ValueError(
                f"Cannot fit LightGBM: {len(X_clean)} rows, "
                f"{X_clean.shape[1]} features after NaN removal."
            )

        self._feature_names = list(X_clean.columns)
        return X_clean, y_clean, date_array

    def _resolve_named_constraints(self) -> None:
        """Map named monotone/interaction constraints to positional indices.

        Pops ``monotone_constraints_named`` and ``interaction_constraints_named``
        from ``self.params`` and replaces them with positional LightGBM params.
        Must be called after ``self._feature_names`` is set.
        """
        named_monotone = self.params.pop("monotone_constraints_named", None)
        named_interactions = self.params.pop("interaction_constraints_named", None)

        if named_monotone:
            constraints = [named_monotone.get(f, 0) for f in self._feature_names]
            self.params["monotone_constraints"] = constraints
            n_constrained = sum(1 for c in constraints if c != 0)
            logger.info(
                "Monotone constraints: %d/%d features constrained",
                n_constrained,
                len(constraints),
            )

        if named_interactions:
            feat_to_idx = {f: i for i, f in enumerate(self._feature_names)}
            positional_groups = []
            for group in named_interactions:
                indices = [feat_to_idx[f] for f in group if f in feat_to_idx]
                if indices:
                    positional_groups.append(indices)
            if positional_groups:
                self.params["interaction_constraints"] = positional_groups
                logger.info(
                    "Interaction constraints: %d groups covering %d features",
                    len(positional_groups),
                    sum(len(g) for g in positional_groups),
                )

    def _fit_base_model(self, X_clean: pd.DataFrame, y_clean: pd.Series) -> pd.Series:
        """Fit the base model for init_score and apply residual scaling.

        Sets ``self._base_model`` and ``self._init_score_vector``.
        Returns *y_clean* (possibly modified by residual scaling).
        """
        if self.base_model_name:
            from volforecast.registry import MODEL_REGISTRY, ensure_registered

            ensure_registered()
            base_cls = MODEL_REGISTRY[self.base_model_name]
            self._base_model = base_cls()
            self._base_model.fit(X_clean, y_clean)
            base_preds = self._base_model.predict(X_clean)
            # NaN fallback: where base model can't predict, use scalar mean
            scalar_mean = float(y_clean.mean())
            nan_mask = np.isnan(base_preds)
            if nan_mask.any():
                base_preds[nan_mask] = scalar_mean
            self._init_score_vector = base_preds
            self._init_score = None  # signal that we use vector, not scalar

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

        # Date-aware purge for panel data: val_purge_gap means DATES, not rows.
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
                val_start = n  # not enough dates for purge
            logger.debug(
                "Panel val purge: gap=%d dates, split_idx=%d, val_start=%d (skipped %d rows)",
                self.val_purge_gap,
                split_idx,
                val_start,
                val_start - split_idx,
            )
        else:
            val_start = split_idx + self.val_purge_gap

        # Fall back to no-purge if purged val set is too small
        if val_start >= n - 20:
            val_start = split_idx
        return split_idx, val_start

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        on_progress: Any | None = None,
    ) -> LightGBMVolModel:
        """Fit LightGBM with QLIKE custom objective.

        When val_fraction > 0, splits the last val_fraction of training data
        as validation for early stopping. When val_fraction == 0 (default),
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
        LightGBMVolModel
            Fitted model (self).
        """
        import lightgbm as lgb

        X_clean, y_clean, date_array = self._clean_inputs(X, y)
        self._resolve_named_constraints()
        y_clean = self._fit_base_model(X_clean, y_clean)

        train_params = {
            k: v for k, v in self.params.items() if k not in _INIT_ONLY_KEYS
        }
        train_params["objective"] = qlike_objective

        # Parse sample_reweight config
        reweight_cfg = self.params.get("sample_reweight")
        reweight_enabled = reweight_cfg and reweight_cfg.get("enabled", False)

        if self.val_fraction > 0:
            split_idx, val_start = self._build_val_split(X_clean, y_clean, date_array)

            X_train = X_clean.iloc[:split_idx]
            X_val = X_clean.iloc[val_start:]
            y_train = y_clean.iloc[:split_idx]
            y_val = y_clean.iloc[val_start:]

            # init_score: use base model vector or scalar mean
            if self._init_score_vector is not None:
                init_train = self._init_score_vector[:split_idx]
                init_val = self._init_score_vector[val_start:]
            else:
                self._init_score = float(y_train.mean())
                init_train = np.full(len(X_train), self._init_score)
                init_val = np.full(len(X_val), self._init_score)

            # --- Pass 1: fit without weights ---
            dtrain = lgb.Dataset(X_train, label=y_train, init_score=init_train)
            dval = lgb.Dataset(X_val, label=y_val, reference=dtrain, init_score=init_val)

            callbacks = [
                lgb.early_stopping(self.early_stopping_rounds, verbose=False),
                lgb.log_evaluation(-1),
            ]
            if on_progress is not None:
                _total = self.n_estimators

                def _progress_cb(env):
                    on_progress(env.iteration, _total)

                callbacks.append(_progress_cb)

            self._model = lgb.train(
                params=train_params,
                train_set=dtrain,
                num_boost_round=self.n_estimators,
                valid_sets=[dval],
                valid_names=["val"],
                feval=qlike_eval,
                callbacks=callbacks,
            )

            # --- Pass 2: reweight and retrain if enabled ---
            if reweight_enabled:
                weights = self._compute_reweight(
                    X_train, y_train, init_train, reweight_cfg,
                )
                # LightGBM ignores Dataset weight= with custom objectives.
                # Instead, create a weighted objective that multiplies grad/hess
                # by per-sample weights (changes split criterion).
                weighted_obj = _make_weighted_qlike_objective(weights)
                train_params_p2 = {**train_params, "objective": weighted_obj}
                dtrain_w = lgb.Dataset(
                    X_train, label=y_train, init_score=init_train,
                )
                dval_w = lgb.Dataset(
                    X_val, label=y_val, reference=dtrain_w, init_score=init_val,
                )
                # Fresh callbacks (early_stopping is stateful, cannot reuse)
                callbacks_p2 = [
                    lgb.early_stopping(self.early_stopping_rounds, verbose=False),
                    lgb.log_evaluation(-1),
                ]
                self._model = lgb.train(
                    params=train_params_p2,
                    train_set=dtrain_w,
                    num_boost_round=self.n_estimators,
                    valid_sets=[dval_w],
                    valid_names=["val"],
                    feval=qlike_eval,
                    callbacks=callbacks_p2,
                )
        else:
            # No validation split — train on all data with fixed rounds
            if self._init_score_vector is not None:
                init_all = self._init_score_vector
            else:
                self._init_score = float(y_clean.mean())
                init_all = np.full(len(X_clean), self._init_score)

            # --- Pass 1 ---
            dtrain = lgb.Dataset(X_clean, label=y_clean, init_score=init_all)
            callbacks = [lgb.log_evaluation(-1)]
            if on_progress is not None:
                _total = self.n_estimators

                def _progress_cb_noval(env):
                    on_progress(env.iteration, _total)

                callbacks.append(_progress_cb_noval)

            self._model = lgb.train(
                params=train_params,
                train_set=dtrain,
                num_boost_round=self.n_estimators,
                callbacks=callbacks,
            )

            # --- Pass 2: reweight and retrain if enabled (no-val path) ---
            if reweight_enabled:
                weights = self._compute_reweight(
                    X_clean, y_clean, init_all, reweight_cfg,
                )
                weighted_obj = _make_weighted_qlike_objective(weights)
                train_params_p2 = {**train_params, "objective": weighted_obj}
                dtrain_w = lgb.Dataset(
                    X_clean, label=y_clean, init_score=init_all,
                )
                self._model = lgb.train(
                    params=train_params_p2,
                    train_set=dtrain_w,
                    num_boost_round=self.n_estimators,
                    callbacks=callbacks,
                )

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
            Init score (HAR-IV init) for each sample.
        cfg : dict
            Reweight config with keys: alpha, source, clip_max, normalize.

        Returns
        -------
        np.ndarray
            Per-sample weights (mean=1 if normalize=True).
        """
        alpha = cfg.get("alpha", 1.0)
        source = cfg.get("source", "conditional")
        clip_max = cfg.get("clip_max", 10.0)
        normalize = cfg.get("normalize", True)

        if source == "conditional":
            # Conditional QLIKE: residual after pass-1 tree predictions
            pass1_preds = self._model.predict(X) + init_score
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
        # LightGBM predict() returns tree output only; add init_score back
        raw = self._model.predict(X[self._feature_names])
        if self._base_model is not None:
            # Undo residual scaling: tree learned on amplified residual, divide back
            if self.residual_scale != 1.0:
                raw = raw / self.residual_scale
            base_preds = self._base_model.predict(X)
            # NaN fallback for prediction time
            nan_mask = np.isnan(base_preds)
            if nan_mask.any():
                fallback = float(np.nanmean(base_preds))
                base_preds[nan_mask] = fallback
            return raw + base_preds
        return raw + self._init_score

    @property
    def summary(self) -> dict[str, float]:
        """Feature importance (gain) as dict."""
        if self._model is None:
            return {}
        importance = self._model.feature_importance(importance_type="gain")
        return dict(zip(self._feature_names, importance.astype(float)))

    @property
    def feature_importance(self) -> dict[str, int]:
        """Feature importance (split count) as dict."""
        if self._model is None:
            return {}
        importance = self._model.feature_importance(importance_type="split")
        return dict(zip(self._feature_names, importance.astype(int)))

    @classmethod
    def from_tuned(
        cls,
        X: pd.DataFrame,
        y: pd.Series,
        cv_config: Any | None = None,
        n_trials: int = 50,
        **kwargs: Any,
    ) -> LightGBMVolModel:
        """Create a fitted model with Optuna-tuned hyperparameters.

        Parameters
        ----------
        X : pd.DataFrame
            Full training features.
        y : pd.Series
            Full training target (log RV).
        cv_config : CVConfig, optional
            CV configuration (defaults to expanding window).
        n_trials : int
            Number of Optuna trials.
        **kwargs
            Forwarded to tune_hyperparameters (timeout, storage_path, seed).

        Returns
        -------
        LightGBMVolModel
            Fitted model with best hyperparameters.
        """
        best_params = tune_hyperparameters(X, y, cv_config, n_trials, **kwargs)
        n_est = best_params.pop("n_estimators", 1000)
        model = cls(n_estimators=n_est, **best_params)
        model.fit(X, y)
        return model


def _trial_callback(on_trial_complete):
    """Create an Optuna callback that fires on_trial_complete(trial_num, n_trials)."""

    def _callback(study, trial):  # noqa: ARG001 — Optuna callback signature
        n_complete = len([t for t in study.trials if t.state.is_finished()])
        on_trial_complete(n_complete)

    return _callback


def _make_objective(
    X: pd.DataFrame,
    y: pd.Series,
    cv_config: Any,
    seed: int,
    base_params: dict[str, Any] | None,
    threads_per_trial: int,
):
    """Build an Optuna objective closure for QLIKE-optimized LightGBM tuning."""
    import optuna

    from volforecast.evaluation.metrics import qlike
    from volforecast.utils.cv import ExpandingWindowCV

    def objective(trial: optuna.Trial) -> float:
        params = {
            "num_leaves": trial.suggest_int("num_leaves", 8, 128),
            "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.1, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 50, 300),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "bagging_freq": trial.suggest_int("bagging_freq", 1, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "n_estimators": trial.suggest_int("n_estimators", 300, 1500),
            "num_threads": threads_per_trial,
            "verbose": -1,
            "seed": seed,
        }

        if base_params:
            for k, v in base_params.items():
                if k not in params and k not in _INIT_ONLY_KEYS:
                    params[k] = v

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

        scores: list[float] = []
        for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(X, y)):
            n_est = params.pop("n_estimators", 1000)
            model = LightGBMVolModel(n_estimators=n_est, val_fraction=0.0, **params)
            params["n_estimators"] = n_est

            n_train = len(train_idx)
            if params.get("min_child_samples", 0) >= n_train:
                raise optuna.TrialPruned()

            try:
                model.fit(X.iloc[train_idx], y.iloc[train_idx])
            except Exception:
                raise optuna.TrialPruned()
            pred = model.predict(X.iloc[test_idx])
            scores.append(qlike(y.iloc[test_idx].values, pred))

            trial.report(float(np.mean(scores)), fold_idx)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return float(np.mean(scores))

    return objective


def _optuna_worker(
    worker_id: int,
    n_trials_per_worker: int,
    X_path_or_data: Any,
    y_path_or_data: Any,
    cv_config_dict: dict,
    timeout: int | None,
    journal_path: str,
    seed: int,
    base_params: dict[str, Any] | None,
    threads_per_trial: int,
) -> int:
    """Single Optuna worker process — runs n_trials_per_worker trials.

    Each worker gets its own process with isolated LightGBM memory space.
    All workers share the same JournalStorage file (append-only, process safe).
    Returns number of completed trials.
    """
    import optuna

    from volforecast.config import CVConfig

    X = X_path_or_data
    y = y_path_or_data
    cv_cfg = CVConfig(**cv_config_dict)

    # Connect to shared journal storage
    journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
    storage = optuna.storages.JournalStorage(journal_backend)

    objective = _make_objective(X, y, cv_cfg, seed, base_params, threads_per_trial)

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    # Each worker uses a different seed offset for TPE diversity
    study = optuna.create_study(
        direction="minimize",
        study_name="lightgbm_qlike",
        storage=storage,
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=seed + worker_id, n_startup_trials=10),
        pruner=optuna.pruners.MedianPruner(
            n_startup_trials=10,
            n_warmup_steps=2,
        ),
    )
    study.optimize(
        objective,
        n_trials=n_trials_per_worker,
        timeout=timeout,
        n_jobs=1,  # Always 1 within each process
        catch=(Exception,),
    )
    return n_trials_per_worker


def tune_hyperparameters(
    X: pd.DataFrame,
    y: pd.Series,
    cv_config: Any | None = None,
    n_trials: int = 50,
    timeout: int | None = 3600,
    storage_path: Path | None = None,
    seed: int = 42,
    on_trial_complete: Any | None = None,
    base_params: dict[str, Any] | None = None,
    n_jobs: int = 1,
    n_workers: int = 1,
) -> dict[str, Any]:
    """Tune LightGBM hyperparameters via Optuna with walk-forward CV.

    Uses ExpandingWindowCV (walk-forward) to prevent look-ahead bias.
    Optimizes QLIKE loss with TPE sampler.

    When n_workers > 1, spawns separate processes each running a share of
    trials. Each process has its own LightGBM instance (avoids thread-safety
    segfaults). All processes coordinate via JournalStorage (append-only file).

    Parameters
    ----------
    X : pd.DataFrame
        Full training features.
    y : pd.Series
        Full training target (log RV).
    cv_config : CVConfig, optional
        CV configuration. Defaults to expanding window with
        train_size=500, test_size=63, purge_gap=5.
    n_trials : int
        Total number of Optuna trials (default: 50).
    timeout : int, optional
        Maximum seconds for optimization (default: 3600).
    storage_path : Path, optional
        Path for study storage (enables resume and multi-process coordination).
    seed : int
        Random seed for reproducibility (default: 42).
    on_trial_complete : callable, optional
        Progress callback, called with total completed trial count.
    base_params : dict, optional
        Fixed params to merge into every trial.
    n_jobs : int
        Deprecated. Use n_workers instead (kept for backward compat).
    n_workers : int
        Number of parallel worker processes (default: 1). Each process
        runs n_trials // n_workers trials with 8 threads. Recommended: 8
        on a 208-core system (64 cores total, fits one NUMA socket).

    Returns
    -------
    dict[str, Any]
        Best hyperparameters found (includes base_params).
    """
    import optuna

    from volforecast.config import CVConfig

    if cv_config is None:
        cv_config = CVConfig(
            method="expanding_window",
            n_splits=5,
            purge_gap=5,
            train_size=500,
            test_size=63,
        )

    threads_per_trial = 8

    # Ensure storage is available (required for multi-process coordination)
    if storage_path is None:
        # Use a temp path if none specified
        import tempfile

        storage_path = Path(tempfile.mkdtemp()) / "optuna_study"

    storage_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path = str(storage_path.with_suffix(".journal"))

    # Cap workers at reasonable limit: cores // threads_per_trial, max 16
    max_workers = min(16, max(1, _CPU_COUNT // threads_per_trial))
    effective_workers = min(n_workers, max_workers)
    if effective_workers < n_workers:
        logger.info(
            "Capping n_workers from %d to %d (CPU cores=%d, threads/trial=%d)",
            n_workers,
            effective_workers,
            _CPU_COUNT,
            threads_per_trial,
        )

    logger.info(
        "Optuna: %d trials across %d worker processes × %d threads/trial (%d cores used of %d)",
        n_trials,
        effective_workers,
        threads_per_trial,
        effective_workers * threads_per_trial,
        _CPU_COUNT,
    )

    # Serialize cv_config for pickling across process boundaries
    cv_config_dict = {
        "method": cv_config.method,
        "n_splits": cv_config.n_splits,
        "purge_gap": cv_config.purge_gap,
        "train_size": cv_config.train_size,
        "test_size": cv_config.test_size,
    }

    if effective_workers > 1:
        # Multi-process path: each worker is a separate process with its own
        # LightGBM instance (no thread-safety issues).
        # Use 'spawn' context to avoid fork-after-thread deadlocks.
        # REQUIRES callers to have if __name__ == '__main__' guard (standard
        # Python multiprocessing requirement). CLI entry point (__main__.py)
        # satisfies this. Tests must also use proper guard.
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor

        ctx = mp.get_context("spawn")

        trials_per_worker = n_trials // effective_workers
        remainder = n_trials % effective_workers

        futures = []
        with ProcessPoolExecutor(max_workers=effective_workers, mp_context=ctx) as executor:
            for i in range(effective_workers):
                # Distribute remainder trials to first workers
                worker_trials = trials_per_worker + (1 if i < remainder else 0)
                future = executor.submit(
                    _optuna_worker,
                    worker_id=i,
                    n_trials_per_worker=worker_trials,
                    X_path_or_data=X,
                    y_path_or_data=y,
                    cv_config_dict=cv_config_dict,
                    timeout=timeout,
                    journal_path=journal_path,
                    seed=seed,
                    base_params=base_params,
                    threads_per_trial=threads_per_trial,
                )
                futures.append(future)

            # Poll journal file for real-time progress reporting.
            # Count only NEW trials from this run (subtract pre-existing).
            if on_trial_complete:
                import time

                # Count pre-existing trials (from prior resume or stale journal)
                initial_count = 0
                try:
                    jb = optuna.storages.journal.JournalFileBackend(journal_path)
                    st = optuna.storages.JournalStorage(jb)
                    study_tmp = optuna.load_study(
                        study_name="lightgbm_qlike",
                        storage=st,
                        load_if_exists=True,
                    )
                    initial_count = len([t for t in study_tmp.trials if t.state.is_finished()])
                except Exception:
                    pass

                reported = 0
                while True:
                    done_futures = [f for f in futures if f.done()]
                    # Count new completed trials (subtract initial)
                    try:
                        jb = optuna.storages.journal.JournalFileBackend(journal_path)
                        st = optuna.storages.JournalStorage(jb)
                        study_tmp = optuna.load_study(
                            study_name="lightgbm_qlike",
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
                        pass  # Journal may not exist yet or be mid-write

                    if len(done_futures) == len(futures):
                        break
                    time.sleep(1.0)

            # Collect results (re-raise any worker exceptions)
            total_completed = sum(f.result() for f in futures)

        logger.info("Multi-process tuning complete: %d trials finished", total_completed)

        # Final progress update (ensures bar reaches 100%)
        if on_trial_complete:
            on_trial_complete(n_trials)

        # Load the study to get best params
        journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
        storage = optuna.storages.JournalStorage(journal_backend)
        study = optuna.load_study(
            study_name="lightgbm_qlike",
            storage=storage,
        )
    else:
        # Single-process path (original behavior, n_workers=1)
        journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
        storage = optuna.storages.JournalStorage(journal_backend)

        objective = _make_objective(X, y, cv_config, seed, base_params, threads_per_trial)

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(
            direction="minimize",
            study_name="lightgbm_qlike",
            storage=storage,
            load_if_exists=True,
            sampler=optuna.samplers.TPESampler(seed=seed, n_startup_trials=10),
            pruner=optuna.pruners.MedianPruner(
                n_startup_trials=10,
                n_warmup_steps=2,
            ),
        )
        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            n_jobs=1,
            callbacks=[_trial_callback(on_trial_complete)] if on_trial_complete else [],
            catch=(Exception,),
        )

    # Extract best params from the study
    try:
        best = study.best_params
    except ValueError:
        logger.warning("All %d Optuna trials pruned/failed; returning default params", n_trials)
        best = {
            "num_leaves": 31,
            "max_depth": 5,
            "min_child_samples": 50,
            "learning_rate": 0.05,
            "n_estimators": 1000,
        }

    # Merge base_params into result (preserves boosting_type, drop_rate, etc.)
    if base_params:
        for k, v in base_params.items():
            if k not in best and k not in _INIT_ONLY_KEYS:
                best[k] = v
    return best


DART_PARAMS: dict[str, Any] = {
    "boosting_type": "dart",
    "drop_rate": 0.1,
    "skip_drop": 0.5,
    "max_drop": 50,
    "num_leaves": 16,
    "max_depth": 4,
    "min_child_samples": 150,
    "learning_rate": 0.1,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 3,
    "reg_lambda": 5.0,
    "reg_alpha": 0.1,
    "num_threads": _CPU_COUNT,
    "verbose": -1,
    "seed": 42,
}


@register_model("lightgbm_dart")
class DARTVolModel(LightGBMVolModel):
    """LightGBM DART variant: dropout regularization for less overconfident predictions."""

    name = "lightgbm_dart"

    def __init__(
        self,
        n_estimators: int = 200,
        early_stopping_rounds: int = 50,
        val_fraction: float = 0.0,
        **kwargs: Any,
    ) -> None:
        merged = {**DART_PARAMS, **kwargs}
        super().__init__(
            n_estimators=n_estimators,
            early_stopping_rounds=early_stopping_rounds,
            val_fraction=val_fraction,
            **merged,
        )
