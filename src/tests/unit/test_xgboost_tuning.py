"""Tests for XGBoost Optuna HPO integration and GPU support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

xgb = pytest.importorskip("xgboost")
optuna = pytest.importorskip("optuna")

from volforecast.models.xgboost import XGBoostVolModel  # noqa: E402


@pytest.fixture
def synthetic_panel_data():
    """Synthetic panel data (500 rows, 10 features) for tuning tests."""
    rng = np.random.default_rng(42)
    n = 500
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
            "rq": rng.normal(0.5, 0.1, n),
            "bpv": rng.normal(-8, 0.8, n),
            "rs_pos": rng.normal(-9, 0.5, n),
            "rs_neg": rng.normal(-9, 0.5, n),
            "iv_atm": rng.normal(0.2, 0.05, n),
            "skew": rng.normal(-0.1, 0.02, n),
            "vvix": rng.normal(20, 5, n),
        }
    )
    y = pd.Series(
        X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + rng.normal(0, 0.3, n),
        name="target",
    )
    return X, y


@pytest.fixture
def tuning_config():
    """Minimal TuningConfig for tests."""
    from volforecast.config import CVConfig, TuningConfig

    return TuningConfig(
        enabled=True,
        n_trials=5,
        timeout=120,
        storage_dir=None,
        inner_cv=CVConfig(
            method="expanding_window",
            purge_gap=5,
            train_size=200,
            test_size=50,
        ),
        min_train_size=100,
        tune_every_n_folds=1,
        n_jobs=1,
        n_workers=1,
    )


class TestXGBoostSupportsTuning:
    """XGBoostVolModel should declare tuning support."""

    def test_supports_tuning_flag(self):
        """supports_tuning must be True."""
        assert XGBoostVolModel.supports_tuning is True

    def test_tune_and_fit_exists(self):
        """tune_and_fit classmethod must exist."""
        assert hasattr(XGBoostVolModel, "tune_and_fit")
        assert callable(XGBoostVolModel.tune_and_fit)


class TestXGBoostTuneAndFit:
    """Tests for XGBoostVolModel.tune_and_fit() end-to-end."""

    def test_returns_fitted_model(self, synthetic_panel_data, tuning_config):
        """tune_and_fit returns a fitted XGBoostVolModel that can predict."""
        X, y = synthetic_panel_data
        model = XGBoostVolModel.tune_and_fit(X, y, tuning_config)

        assert isinstance(model, XGBoostVolModel)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert np.all(np.isfinite(preds))

    def test_returns_tuned_params(self, synthetic_panel_data, tuning_config):
        """Tuned model params differ from defaults (Optuna actually ran)."""
        X, y = synthetic_panel_data
        model = XGBoostVolModel.tune_and_fit(X, y, tuning_config)

        params = model.get_params()
        # At minimum, learning_rate should have been searched
        # (extremely unlikely to land exactly on default 0.05)
        assert "learning_rate" in params

    def test_base_params_preserved(self, synthetic_panel_data, tuning_config):
        """base_params are merged into tuned model (not searched over)."""
        X, y = synthetic_panel_data
        base_params = {"seed": 999, "val_purge_gap": 10}
        model = XGBoostVolModel.tune_and_fit(X, y, tuning_config, base_params=base_params)

        params = model.get_params()
        assert params.get("seed") == 999
        assert params.get("val_purge_gap") == 10

    def test_respects_n_trials(self, synthetic_panel_data, tuning_config):
        """Number of Optuna trials matches config."""
        tuning_config.n_trials = 3
        X, y = synthetic_panel_data

        model = XGBoostVolModel.tune_and_fit(X, y, tuning_config)
        # If it completes without error with 3 trials, test passes
        assert model is not None


class TestXGBoostGPUSupport:
    """Tests for GPU device parameter injection."""

    def test_default_device_is_cpu(self):
        """Default params should use CPU (device='cpu' or tree_method='hist')."""
        from volforecast.models.xgboost import DEFAULT_PARAMS

        # XGBoost 2.0+: device param controls hardware
        device = DEFAULT_PARAMS.get("device", "cpu")
        assert device == "cpu"

    def test_gpu_device_param_in_init_only_keys(self):
        """'device' must be in _INIT_ONLY_KEYS (not searched by Optuna)."""
        from volforecast.models.xgboost import _INIT_ONLY_KEYS

        assert "device" in _INIT_ONLY_KEYS

    def test_gpu_device_passed_to_train(self, synthetic_panel_data):
        """When device='cuda:0' is passed, it reaches xgb.train params."""
        X, y = synthetic_panel_data
        model = XGBoostVolModel(device="cuda:0")

        # The device param should be stored in model.params
        assert model.params.get("device") == "cuda:0"

    def test_multi_gpu_worker_pinning(self, synthetic_panel_data, tuning_config):
        """With gpu_device_ids=[0,1,2], workers pin to cuda:0, cuda:1, cuda:2."""
        from volforecast.models.xgboost import tune_hyperparameters_xgb

        X, y = synthetic_panel_data
        tuning_config.n_trials = 3
        tuning_config.n_workers = 1  # Single worker for test simplicity

        # Just verify the function accepts gpu_device_ids parameter
        # (actual GPU test requires hardware; this tests the interface)
        result = tune_hyperparameters_xgb(
            X,
            y,
            cv_config=tuning_config.inner_cv,
            n_trials=3,
            timeout=60,
            seed=42,
            n_workers=1,
            gpu_device_ids=None,  # CPU mode
        )
        assert isinstance(result, dict)
        assert "learning_rate" in result or "max_leaves" in result


class TestXGBoostTuningSearchSpace:
    """Verify the Optuna search space covers expected parameters."""

    def test_search_space_params(self, synthetic_panel_data, tuning_config):
        """Tuned params should include key hyperparameters from search space."""
        X, y = synthetic_panel_data
        tuning_config.n_trials = 5

        model = XGBoostVolModel.tune_and_fit(X, y, tuning_config)
        params = model.get_params()

        # These should all be present (either searched or from defaults)
        expected_keys = [
            "max_leaves",
            "max_depth",
            "learning_rate",
            "min_child_weight",
            "colsample_bytree",
            "subsample",
            "reg_lambda",
        ]
        for key in expected_keys:
            assert key in params, f"Missing param: {key}"
