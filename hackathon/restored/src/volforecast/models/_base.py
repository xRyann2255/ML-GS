"""Unified base classes for all volforecast models.

_BaseModel  — root base: save/load/summary interface shared by ALL models.
_BaseOLS    — OLS/regularized regression models (HAR family): feature selection + fit logic.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class _BaseModel:
    """Shared interface for all volforecast models."""

    REQUIRED_LAYERS: list[str] = ["har_core"]
    supports_tuning: bool = False
    family: str = "unknown"
    description: str = ""
    # Sequence-first models (LSTM/TCN) set this True so the Pipeline runner
    # dispatches to the sequence path, feeding a SequenceTensor instead of a
    # tabular DataFrame. Tabular models keep the default (False) and the
    # existing path is unchanged.
    requires_sequences: bool = False

    # Capability flags — deliberately separate from supports_tuning, which
    # only means "tune_and_fit() exists". The runner keys these behaviours
    # off the flags below instead of overloading supports_tuning:
    supports_fit_progress: bool = False    # fit(X, y, on_progress=...) accepted
    supports_shap_selection: bool = False  # TreeSHAP feature selection is valid
    accepts_gpu_device: bool = False       # constructor accepts gpu_device_id

    coefficients_: np.ndarray | None = None
    intercept_: float | None = None
    _feature_names: list[str] = []

    @classmethod
    def tune_and_fit(
        cls,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        tuning_config,
        base_params: dict | None = None,
    ):
        """Tune hyperparameters on training data and return a fitted model.

        Subclasses that support tuning must override this method and set
        ``supports_tuning = True``.

        Parameters
        ----------
        X_train : pd.DataFrame
            Training features for this outer CV fold.
        y_train : pd.Series
            Training target for this outer CV fold.
        tuning_config : TuningConfig
            Tuning configuration (n_trials, timeout, inner_cv, etc.).

        Returns
        -------
        _BaseModel
            A fitted model instance with tuned hyperparameters.
        """
        raise NotImplementedError(
            f"{cls.__name__} does not support hyperparameter tuning. "
            f"Set supports_tuning = True and implement tune_and_fit()."
        )

    @property
    def summary(self) -> dict[str, float]:
        """Default summary: intercept + named coefficients."""
        if self.coefficients_ is None:
            return {}
        d: dict[str, float] = {"intercept": self.intercept_}
        for name, coef in zip(self._feature_names, self.coefficients_):
            d[name] = float(coef)
        return d

    def save(self, path: Path) -> Path:
        """Serialize fitted model to disk via joblib."""
        from joblib import dump as _dump

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path):
        """Load a previously saved model from disk."""
        from joblib import load as _load

        return _load(path)


class _BaseOLS(_BaseModel):
    """OLS/regularized regression models (HAR family)."""

    family: str = "har"
    description: str = "HAR-family linear model"

    # Subclasses override to restrict features. None means use all columns.
    _FEATURES: list[str] | None = None

    # Alpha-tuning hooks. har_family.py sets these on every registered
    # ridge_/lasso_/elasticnet_ variant; None means "not tunable".
    _ALPHA_GRID: list[float] | None = None
    _L1_RATIO_GRID: list[float] | None = None

    def __init__(self, model=None) -> None:
        if model is None:
            from sklearn.linear_model import LinearRegression

            model = LinearRegression()
        self._model = model
        self.coefficients_: np.ndarray | None = None
        self.intercept_: float | None = None
        self._feature_names: list[str] = []

    def _select_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Filter X to only the columns this model uses."""
        if self._FEATURES is None:
            return X
        cols = [c for c in self._FEATURES if c in X.columns]
        if not cols:
            raise ValueError(
                f"{type(self).__name__} requires features {self._FEATURES} "
                f"but got columns {list(X.columns)}"
            )
        return X[cols]

    def _fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        X = self._select_features(X)
        # Drop columns that are entirely NaN (e.g. noise_robust features
        # absent for this symbol in pooled mode with union columns)
        all_nan_cols = X.columns[X.isna().all()]
        if len(all_nan_cols) > 0:
            X = X.drop(columns=all_nan_cols)
        mask = ~(X.isna().any(axis=1) | y.isna())
        X_clean = X.loc[mask]
        y_clean = y.loc[mask]
        self._feature_names = list(X_clean.columns)
        self._model.fit(X_clean.values, y_clean.values)
        # Extract coefficients — handle sklearn Pipeline wrapping a scaler+estimator
        estimator = self._model
        if hasattr(estimator, "named_steps"):
            estimator = estimator[-1]
        self.coefficients_ = estimator.coef_
        self.intercept_ = float(estimator.intercept_)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.coefficients_ is None:
            raise RuntimeError("Model has not been fitted yet")
        X_sel = X[self._feature_names]
        # Rows with NaN get NaN predictions (OLS can't handle missing values)
        valid_mask = ~X_sel.isna().any(axis=1)
        result = np.full(len(X_sel), np.nan)
        if valid_mask.any():
            result[valid_mask.values] = self._model.predict(X_sel.loc[valid_mask].values)
        return result

    def get_params(self) -> dict[str, float]:
        """Constructor-kwarg snapshot for the runner's cached-params re-fit."""
        params: dict[str, float] = {}
        for key in ("alpha", "l1_ratio"):
            val = getattr(self, key, None)
            if val is not None:
                params[key] = val
        return params

    @classmethod
    def tune_and_fit(
        cls,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        tuning_config,
        base_params: dict | None = None,
    ):
        """Grid-search (alpha, l1_ratio) on inner CV, refit best on full fold.

        Falls back to class-default parameters when the outer training
        window is too small to build inner folds.
        """
        from volforecast.config import CVConfig
        from volforecast.models.linear_tuning import tune_linear_alpha

        if cls._ALPHA_GRID is None:
            raise NotImplementedError(
                f"{cls.__name__} has no tunable parameters (set _ALPHA_GRID)."
            )

        search_space = tuning_config.search_space or {}

        def _grid(key: str, default: list[float] | None) -> list[float] | None:
            if default is None:
                return None
            override = search_space.get(key) or {}
            values = override.get("values")
            if values:
                return [float(v) for v in values]
            return list(default)

        param_grid: dict[str, list[float]] = {"alpha": _grid("alpha", cls._ALPHA_GRID)}
        l1_grid = _grid("l1_ratio", cls._L1_RATIO_GRID)
        if l1_grid is not None:
            param_grid["l1_ratio"] = l1_grid

        inner_cv = tuning_config.inner_cv or CVConfig(
            method="expanding_window",
            purge_gap=10,
            train_size=max(252, len(X_train) // 2),
            test_size=63,
        )
        result = tune_linear_alpha(
            cls, X_train, y_train, param_grid, inner_cv,
            on_trial_complete=tuning_config._on_trial_complete,
            on_tuning_start=getattr(tuning_config, "_on_tuning_start", None),
            on_hpo_event=getattr(tuning_config, "_on_hpo_event", None),
        )
        if result is None:
            model = cls()
            model.tuning_result_ = None
        else:
            model = cls(**result.best_params)
            model.tuning_result_ = result
            logger.info(
                "%s: tuned %s (inner QLIKE %.5f over %d combos)",
                cls.__name__,
                result.best_params,
                result.best_inner_qlike,
                len(result.grid_results),
            )
        model.fit(X_train, y_train)
        return model


def temporal_holdout_split(
    n: int,
    fraction: float,
    purge_gap: int,
    min_holdout: int = 20,
) -> tuple[int, int] | None:
    """Compute split indices for a temporal holdout with purge gap.

    Returns ``(train_end, holdout_start)`` or ``None`` if the holdout
    set would be smaller than *min_holdout* rows.
    """
    train_end = int(n * (1.0 - fraction))
    holdout_start = train_end + purge_gap
    if holdout_start >= n - min_holdout:
        return None
    return train_end, holdout_start
