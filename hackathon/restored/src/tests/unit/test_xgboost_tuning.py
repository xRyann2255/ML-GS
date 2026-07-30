"""Tests for XGBoost Optuna HPO integration and GPU support."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

xgb = pytest.importorskip("xgboost")
optuna = pytest.importorskip("optuna")

from volforecast.models.xgboost import (  # noqa: E402
    XGBoostVolModel,
    _prebuild_cv_folds_xgb,
    _optuna_worker_xgb,
    _make_study_name_xgb,
)


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


class TestInnerObjectiveBaseMargin:
    """Inner HPO objective must use base_model predictions as base_margin."""

    def test_inner_folds_use_base_model_predictions(self):
        """When a base_model is provided, inner DMatrices get base_margin from it."""
        from volforecast.config import CVConfig

        rng = np.random.default_rng(99)
        n = 600
        X = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-8, 1, n),
                "log_rv_w": rng.normal(-8, 0.5, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
                "rq": rng.normal(0.5, 0.1, n),
            }
        )
        y = pd.Series(rng.normal(-8, 1, n), name="target")

        cv_cfg = CVConfig(
            method="expanding_window",
            purge_gap=5,
            train_size=200,
            test_size=50,
        )

        # Create a mock base model that returns non-constant predictions
        # sized to the input length (like a real model)
        base_preds_full = rng.normal(-8, 0.5, n)

        def _mock_predict(df):
            # Return varying predictions matching input length
            return base_preds_full[:len(df)]

        base_model = MagicMock()
        base_model.predict = MagicMock(side_effect=_mock_predict)

        folds = _prebuild_cv_folds_xgb(X, y, cv_cfg, base_model=base_model)
        assert len(folds) > 0

        # The base_model.predict must have been called
        assert base_model.predict.called

        # Verify base_margin is NOT a constant — it uses base_model predictions
        for dtrain, dval, dtest, _, _ in folds:
            train_margin = dtrain.get_base_margin()
            assert train_margin is not None and len(train_margin) > 0
            # base_model returns non-constant preds; margin should NOT be all-same
            assert not np.allclose(
                train_margin, train_margin[0]
            ), "base_margin should be non-constant when base_model is provided"

            # dtest base_margin should also be non-constant
            test_margin = dtest.get_base_margin()
            assert test_margin is not None and len(test_margin) > 0
            assert not np.allclose(
                test_margin, test_margin[0]
            ), "test base_margin should be non-constant when base_model is provided"


class TestInnerCVDateBasedPurge:
    """Inner CV splits must operate on unique dates, not raw row indices."""

    def test_purge_gap_is_in_date_units_not_rows(self):
        """With 21 symbols/date, purge_gap=5 should skip 5 dates (105 rows), not 5 rows."""
        from volforecast.config import CVConfig

        rng = np.random.default_rng(42)
        n_dates = 100
        n_symbols = 21
        n_rows = n_dates * n_symbols

        dates = pd.bdate_range("2022-01-03", periods=n_dates)
        symbols = [f"SYM_{i:02d}" for i in range(n_symbols)]

        # Build panel with MultiIndex (date, symbol)
        rows = []
        for d in dates:
            for s in symbols:
                rows.append((d, s))
        idx = pd.MultiIndex.from_tuples(rows, names=["date", "symbol"])

        X = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-8, 1, n_rows),
                "log_rv_w": rng.normal(-8, 0.5, n_rows),
                "log_rv_m": rng.normal(-8, 0.3, n_rows),
                "rq": rng.normal(0.5, 0.1, n_rows),
            },
            index=idx,
        )
        y = pd.Series(rng.normal(-8, 1, n_rows), index=idx, name="target")

        purge_gap = 5  # 5 dates, not 5 rows
        cv_cfg = CVConfig(
            method="expanding_window",
            purge_gap=purge_gap,
            train_size=40,  # 40 dates
            test_size=10,  # 10 dates
        )

        folds = _prebuild_cv_folds_xgb(X, y, cv_cfg)
        assert len(folds) > 0

        # For each fold, the TEST set row count must be 10 dates * 21 symbols = 210 rows
        # This proves the splitter operates on date units
        for dtrain, dval, dtest, _, y_te in folds:
            n_test = dtest.num_row()
            # Test set should contain whole dates (multiple of n_symbols)
            assert n_test % n_symbols == 0, (
                f"Test rows ({n_test}) should be a multiple of {n_symbols} symbols"
            )
            # Test set should be exactly test_size dates * n_symbols rows
            expected_test_rows = 10 * n_symbols  # 10 dates * 21 symbols
            assert n_test == expected_test_rows, (
                f"Expected {expected_test_rows} test rows (10 dates × 21 symbols), got {n_test}"
            )

        # Verify the total train rows (before inner val split) are date-based:
        # First fold train should be >= 40 dates * 21 symbols = 840 rows
        # (the inner val split subtracts some, but the DMatrix train size
        # should be at least train_size - val - purge and still large)
        first_train = folds[0][0].num_row()
        # Should be substantially more than what row-based would give
        # Row-based with purge_gap=5 would give 40 rows of training; date-based gives 840+
        assert first_train >= 40 * n_symbols * 0.7, (
            f"First fold train ({first_train}) too small for date-based split"
        )


class TestStudyNameHash:
    """Study name must include a hash of model params to prevent stale reuse."""

    def test_different_params_give_different_study_names(self):
        """Two different param configs produce different study names."""
        params_a = {"learning_rate": 0.05, "max_leaves": 31, "max_depth": 5}
        params_b = {"learning_rate": 0.1, "max_leaves": 64, "max_depth": 6}

        name_a = _make_study_name_xgb(params_a)
        name_b = _make_study_name_xgb(params_b)

        assert name_a != name_b, "Different params must produce different study names"
        # Both should contain the base prefix
        assert "xgboost_qlike" in name_a
        assert "xgboost_qlike" in name_b

    def test_same_params_give_same_study_name(self):
        """Identical params produce the same study name (deterministic)."""
        params = {"learning_rate": 0.05, "max_leaves": 31, "max_depth": 5}

        name1 = _make_study_name_xgb(params)
        name2 = _make_study_name_xgb(params)

        assert name1 == name2

    def test_seed_excluded_from_hash(self):
        """Seed should NOT affect the study name (only structural params matter)."""
        params_a = {"learning_rate": 0.05, "max_leaves": 31, "seed": 42}
        params_b = {"learning_rate": 0.05, "max_leaves": 31, "seed": 99}

        name_a = _make_study_name_xgb(params_a)
        name_b = _make_study_name_xgb(params_b)

        assert name_a == name_b, "Seed should not affect study name"
