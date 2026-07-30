"""Tests that HPO inner objective uses base_model for init (not constant mean)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

xgb = pytest.importorskip("xgboost")
optuna = pytest.importorskip("optuna")

from volforecast.models.xgboost import (  # noqa: E402
    XGBoostVolModel,
    _make_objective_xgb,
    _prebuild_cv_folds_xgb,
    tune_hyperparameters_xgb,
)


@pytest.fixture
def synthetic_data():
    """Minimal synthetic data for base_model threading tests."""
    rng = np.random.default_rng(99)
    n = 300
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
            "feat_a": rng.normal(0, 1, n),
            "feat_b": rng.normal(0, 1, n),
        }
    )
    y = pd.Series(rng.normal(-8, 1, n), name="target")
    return X, y


class MockBaseModel:
    """A trivially fittable base model for testing base_model plumbing."""

    def __init__(self):
        self._mean = None

    def fit(self, X, y):
        self._mean = y.mean()
        return self

    def predict(self, X):
        return np.full(len(X), self._mean)


class TestTuneHyperparametersPassesBaseModel:
    """Verify tune_hyperparameters_xgb threads base_model to _prebuild_cv_folds_xgb."""

    def test_single_process_threads_base_model(self, synthetic_data, tmp_path):
        """When base_params contains 'base_model', tune_hyperparameters_xgb should
        fit that model and pass it to _prebuild_cv_folds_xgb."""
        X, y = synthetic_data

        from volforecast.config import CVConfig

        cv = CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=50)

        # Patch _prebuild_cv_folds_xgb to capture what it receives
        with patch(
            "volforecast.models.xgboost._prebuild_cv_folds_xgb", wraps=_prebuild_cv_folds_xgb
        ) as mock_prebuild:
            # Patch MODEL_REGISTRY to include our mock
            mock_registry = {"mock_base": MockBaseModel}
            with patch("volforecast.registry.MODEL_REGISTRY", mock_registry):
                with patch("volforecast.registry.ensure_registered"):
                    tune_hyperparameters_xgb(
                        X,
                        y,
                        cv_config=cv,
                        n_trials=1,
                        timeout=30,
                        storage_path=tmp_path,
                        seed=42,
                        base_params={"base_model": "mock_base", "seed": 42},
                        n_workers=1,
                        gpu_device_ids=None,
                    )

            # _prebuild_cv_folds_xgb should have been called with base_model != None
            assert mock_prebuild.called, "_prebuild_cv_folds_xgb was not called"
            call_kwargs = mock_prebuild.call_args
            # Could be positional or keyword — check the base_model arg
            if call_kwargs.kwargs.get("base_model") is not None:
                passed_model = call_kwargs.kwargs["base_model"]
            elif len(call_kwargs.args) > 3:
                # positional: (X, y, cv_config, val_fraction, purge_gap, base_model)
                passed_model = call_kwargs.args[3] if len(call_kwargs.args) > 3 else None
            else:
                passed_model = None

            assert passed_model is not None, (
                "base_model was not passed to _prebuild_cv_folds_xgb "
                f"(kwargs={call_kwargs.kwargs}, args count={len(call_kwargs.args)})"
            )
            # Must be a fitted instance, not the class itself
            assert hasattr(passed_model, "_mean"), "base_model was not fitted"
            assert passed_model._mean is not None, "base_model._mean is None (not fitted)"


class TestMakeObjectivePassesBaseModel:
    """Verify _make_objective_xgb passes base_model to its fallback prebuild."""

    def test_fallback_prebuild_receives_base_model(self, synthetic_data):
        """When prebuilt_folds=None, _make_objective_xgb should pass base_model
        to _prebuild_cv_folds_xgb."""
        X, y = synthetic_data
        from volforecast.config import CVConfig

        cv = CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=50)

        mock_model = MockBaseModel()
        mock_model.fit(X, y)

        with patch(
            "volforecast.models.xgboost._prebuild_cv_folds_xgb", wraps=_prebuild_cv_folds_xgb
        ) as mock_prebuild:
            _make_objective_xgb(
                X,
                y,
                cv,
                seed=42,
                base_params=None,
                device="cpu",
                prebuilt_folds=None,
                base_model=mock_model,
            )
            assert mock_prebuild.called
            call_kwargs = mock_prebuild.call_args
            passed_model = call_kwargs.kwargs.get("base_model")
            assert passed_model is mock_model, (
                f"base_model not threaded to _prebuild_cv_folds_xgb: {call_kwargs}"
            )


class TestTuneAndFitFitsBaseModel:
    """Verify tune_and_fit fits the base model before calling HPO."""

    def test_tune_and_fit_fits_and_passes_base_model(self, synthetic_data, tmp_path):
        """tune_and_fit should fit the base model from registry and pass it to HPO."""
        X, y = synthetic_data

        from volforecast.config import CVConfig, TuningConfig

        tuning_cfg = TuningConfig(
            enabled=True,
            n_trials=1,
            timeout=30,
            storage_dir=str(tmp_path),
            inner_cv=CVConfig(
                method="expanding_window", purge_gap=5, train_size=150, test_size=50
            ),
        )

        # Patch tune_hyperparameters_xgb to capture the base_model arg
        with patch(
            "volforecast.models.xgboost.tune_hyperparameters_xgb"
        ) as mock_tune:
            # Make it return valid params so tune_and_fit can proceed
            mock_tune.return_value = {"max_depth": 4, "learning_rate": 0.05}

            mock_registry = {"mock_base": MockBaseModel}
            with patch("volforecast.registry.MODEL_REGISTRY", mock_registry):
                with patch("volforecast.registry.ensure_registered"):
                    XGBoostVolModel.tune_and_fit(
                        X,
                        y,
                        tuning_config=tuning_cfg,
                        base_params={"base_model": "mock_base", "seed": 42},
                    )

            assert mock_tune.called, "tune_hyperparameters_xgb was not called"
            call_kwargs = mock_tune.call_args.kwargs
            passed_model = call_kwargs.get("base_model")
            assert passed_model is not None, (
                f"base_model not passed to tune_hyperparameters_xgb: {call_kwargs.keys()}"
            )
            assert isinstance(passed_model, MockBaseModel)
            assert passed_model._mean is not None, "base_model not fitted before passing to HPO"
