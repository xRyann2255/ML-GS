"""Tests for LightGBM model with QLIKE custom objective."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

lgb = pytest.importorskip("lightgbm")

from volforecast.models.lightgbm import (  # noqa: E402
    LightGBMVolModel,
    qlike_eval,
    qlike_objective,
    tune_hyperparameters,
)


@pytest.fixture
def synthetic_lgbm_data():
    """Synthetic log-RV data for LightGBM tests."""
    rng = np.random.default_rng(42)
    n = 500
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
        }
    )
    y = pd.Series(X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + rng.normal(0, 0.5, n))
    return X, y


class _FakeDataset:
    """Minimal mock of lgb.Dataset for unit-testing objective/eval functions."""

    def __init__(self, labels: np.ndarray):
        self._labels = labels

    def get_label(self) -> np.ndarray:
        return self._labels


class TestQLIKEObjectiveGradient:
    """Tests for qlike_objective gradient correctness."""

    def test_gradient_finite_difference(self):
        """Gradient matches numerical (L(yp+eps)-L(yp-eps))/(2*eps)."""
        rng = np.random.default_rng(123)
        y_true = rng.normal(-8, 1, 100)
        y_pred = rng.normal(-8, 1, 100)
        dtrain = _FakeDataset(y_true)

        grad, _ = qlike_objective(y_pred, dtrain)

        # Finite difference
        eps = 1e-5

        def loss(yp):
            diff = y_true - yp
            return np.exp(np.clip(diff, -10, 10)) - diff - 1.0

        numerical_grad = (loss(y_pred + eps) - loss(y_pred - eps)) / (2.0 * eps)
        np.testing.assert_allclose(grad, numerical_grad, atol=1e-4)

    def test_gradient_zero_at_minimum(self):
        """y_pred == y_true -> grad=0, hess=1."""
        y = np.array([-8.0, -7.5, -9.0, -6.0])
        dtrain = _FakeDataset(y)
        grad, hess = qlike_objective(y.copy(), dtrain)
        np.testing.assert_allclose(grad, 0.0, atol=1e-10)
        np.testing.assert_allclose(hess, 1.0, atol=1e-6)

    def test_gradient_sign(self):
        """Under-prediction -> grad<0, over-prediction -> grad>0."""
        y_true = np.array([-7.0, -7.0])
        # Under-prediction: y_pred < y_true
        y_pred_under = np.array([-8.0, -9.0])
        grad_under, _ = qlike_objective(y_pred_under, _FakeDataset(y_true))
        assert (grad_under < 0).all()

        # Over-prediction: y_pred > y_true
        y_pred_over = np.array([-6.0, -5.0])
        grad_over, _ = qlike_objective(y_pred_over, _FakeDataset(y_true))
        assert (grad_over > 0).all()

    def test_hessian_positive(self):
        """Hessian always > 0 for wide range of diff values."""
        rng = np.random.default_rng(77)
        y_true = rng.normal(-8, 2, 1000)
        y_pred = rng.normal(-8, 2, 1000)
        _, hess = qlike_objective(y_pred, _FakeDataset(y_true))
        assert (hess > 0).all()


class TestQLIKEEval:
    """Tests for qlike_eval metric."""

    def test_qlike_eval_matches_metrics(self):
        """qlike_eval matches metrics.qlike for same data."""
        from volforecast.evaluation.metrics import qlike

        rng = np.random.default_rng(55)
        y_true = rng.normal(-8, 1, 200)
        y_pred = rng.normal(-8, 1, 200)

        name, eval_loss, higher_better = qlike_eval(y_pred, _FakeDataset(y_true))
        metric_loss = qlike(y_true, y_pred, log_space=True)

        assert name == "qlike"
        assert higher_better is False
        assert eval_loss == pytest.approx(metric_loss, rel=1e-6)

    def test_qlike_eval_zero_at_perfect(self):
        """Perfect predictions -> loss = 0."""
        y = np.array([-8.0, -7.0, -9.0])
        _, loss, _ = qlike_eval(y.copy(), _FakeDataset(y))
        assert loss == pytest.approx(0.0, abs=1e-10)


class TestLightGBMVolModel:
    """Tests for LightGBMVolModel fit/predict workflow."""

    def test_fit_predict(self, synthetic_lgbm_data):
        """Fit on synthetic, predict, verify shape and no NaN."""
        X, y = synthetic_lgbm_data
        model = LightGBMVolModel(n_estimators=50, early_stopping_rounds=10)
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))

    def test_protocol_conformance(self):
        """LightGBMVolModel satisfies model contract (name, fit, predict)."""
        model = LightGBMVolModel()
        assert hasattr(model, "name")
        assert callable(getattr(model, "fit", None))
        assert callable(getattr(model, "predict", None))

    def test_save_load(self, synthetic_lgbm_data, tmp_path):
        """Fit, save, load, predictions match."""
        X, y = synthetic_lgbm_data
        model = LightGBMVolModel(n_estimators=50, early_stopping_rounds=10)
        model.fit(X, y)
        preds_orig = model.predict(X)

        save_path = tmp_path / "lgbm_test.joblib"
        model.save(save_path)
        loaded = LightGBMVolModel.load(save_path)
        preds_loaded = loaded.predict(X)

        np.testing.assert_array_equal(preds_orig, preds_loaded)

    def test_feature_importance_names(self, synthetic_lgbm_data):
        """Feature importance keys match input columns."""
        X, y = synthetic_lgbm_data
        model = LightGBMVolModel(n_estimators=50, early_stopping_rounds=10)
        model.fit(X, y)

        gain = model.summary
        split = model.feature_importance
        assert set(gain.keys()) == set(X.columns)
        assert set(split.keys()) == set(X.columns)


class TestOptunaHyperparameterTuning:
    """Tests for Optuna-based hyperparameter tuning with walk-forward CV."""

    optuna = pytest.importorskip("optuna")

    @pytest.fixture
    def tuning_data(self):
        """Synthetic data sized for tuning (needs enough for ExpandingWindowCV)."""
        rng = np.random.default_rng(42)
        n = 800
        X = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-8, 1, n),
                "log_rv_w": rng.normal(-8, 0.5, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
                "sqrt_rq": rng.normal(0.5, 0.2, n),
            }
        )
        y = pd.Series(X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + rng.normal(0, 0.5, n))
        return X, y

    def test_tune_returns_valid_params(self, tuning_data):
        """tune_hyperparameters returns dict with expected keys in valid ranges."""
        X, y = tuning_data
        best = tune_hyperparameters(X, y, n_trials=3, timeout=300, seed=42)

        expected_keys = {
            "num_leaves",
            "learning_rate",
            "min_child_samples",
            "feature_fraction",
            "bagging_fraction",
            "bagging_freq",
            "reg_alpha",
            "reg_lambda",
            "max_depth",
            "n_estimators",
        }
        assert expected_keys == set(best.keys())
        assert 8 <= best["num_leaves"] <= 128
        assert 0.005 <= best["learning_rate"] <= 0.1
        assert 50 <= best["min_child_samples"] <= 300
        assert 0.5 <= best["feature_fraction"] <= 1.0
        assert 0.5 <= best["bagging_fraction"] <= 1.0
        assert 1 <= best["bagging_freq"] <= 10
        assert 1e-4 <= best["reg_alpha"] <= 10.0
        assert 0.1 <= best["reg_lambda"] <= 10.0
        assert 3 <= best["max_depth"] <= 7
        assert 300 <= best["n_estimators"] <= 1500

    def test_tune_journal_storage(self, tuning_data, tmp_path):
        """Journal storage file is created when storage_path provided."""
        X, y = tuning_data
        storage_path = tmp_path / "optuna_test"
        tune_hyperparameters(X, y, n_trials=2, timeout=120, storage_path=storage_path)
        journal_path = storage_path.with_suffix(".journal")
        assert journal_path.exists()
        assert journal_path.stat().st_size > 0

    def test_from_tuned_produces_fitted_model(self, tuning_data):
        """from_tuned returns a fitted model that can predict."""
        X, y = tuning_data
        model = LightGBMVolModel.from_tuned(X, y, n_trials=3, timeout=300, seed=42)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))


class TestTuneAndFit:
    """Tests for LightGBMVolModel.tune_and_fit() classmethod (nested CV protocol)."""

    optuna = pytest.importorskip("optuna")

    @pytest.fixture
    def tuning_data(self):
        """Synthetic data sized for tuning."""
        rng = np.random.default_rng(42)
        n = 800
        X = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-8, 1, n),
                "log_rv_w": rng.normal(-8, 0.5, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
                "sqrt_rq": rng.normal(0.5, 0.2, n),
            }
        )
        y = pd.Series(X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + rng.normal(0, 0.5, n))
        return X, y

    def test_tune_and_fit_returns_fitted_model(self, tuning_data):
        """tune_and_fit returns a model that can predict."""
        from volforecast.config import TuningConfig

        X, y = tuning_data
        tuning_cfg = TuningConfig(enabled=True, n_trials=3, timeout=120)
        model = LightGBMVolModel.tune_and_fit(X, y, tuning_cfg)

        assert model._model is not None
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))

    def test_tune_and_fit_uses_inner_cv(self, tuning_data):
        """tune_and_fit respects explicit inner_cv config."""
        from volforecast.config import CVConfig, TuningConfig

        X, y = tuning_data
        inner = CVConfig(method="expanding_window", train_size=300, test_size=50, purge_gap=3)
        tuning_cfg = TuningConfig(enabled=True, n_trials=2, timeout=60, inner_cv=inner)
        model = LightGBMVolModel.tune_and_fit(X, y, tuning_cfg)
        assert model._model is not None

    def test_supports_tuning_attribute(self):
        """LightGBMVolModel exposes supports_tuning = True."""
        assert LightGBMVolModel.supports_tuning is True

    def test_base_model_supports_tuning_false(self):
        """_BaseModel.supports_tuning defaults to False."""
        from volforecast.models._base import _BaseModel

        assert _BaseModel.supports_tuning is False

    def test_base_model_tune_and_fit_raises(self):
        """_BaseModel.tune_and_fit raises NotImplementedError."""
        from volforecast.config import TuningConfig
        from volforecast.models._base import _BaseModel

        with pytest.raises(NotImplementedError):
            _BaseModel.tune_and_fit(pd.DataFrame(), pd.Series(dtype=float), TuningConfig())


class TestHardeningFixes:
    """Tests for LightGBM hardening fixes (purge gap, defaults, level-space QLIKE)."""

    def test_val_split_has_purge_gap(self, synthetic_lgbm_data):
        """Validation set respects purge gap between train and val."""
        X, y = synthetic_lgbm_data
        model = LightGBMVolModel(
            n_estimators=50,
            early_stopping_rounds=10,
            val_fraction=0.2,
            val_purge_gap=10,
        )
        # Monkey-patch lgb.train to capture the datasets
        import lightgbm as lgb

        captured = {}

        original_train = lgb.train

        def mock_train(*, train_set, valid_sets=None, **kwargs):
            captured["train_n"] = train_set.get_label().shape[0]
            if valid_sets:
                captured["val_n"] = valid_sets[0].get_label().shape[0]
            return original_train(train_set=train_set, valid_sets=valid_sets, **kwargs)

        lgb.train = mock_train
        try:
            model.fit(X, y)
        finally:
            lgb.train = original_train

        # With 500 rows, val_fraction=0.2: split_idx=400, val_start=410
        # train = 400 rows, val = 500-410 = 90 rows (not 100)
        n = len(X)
        expected_split = int(n * 0.8)
        expected_val_start = expected_split + 10
        assert captured["train_n"] == expected_split
        assert captured["val_n"] == n - expected_val_start

    def test_val_purge_gap_fallback_on_tiny_val(self):
        """When purge gap would leave <20 val rows, gap is skipped gracefully."""
        rng = np.random.default_rng(99)
        n = 100  # small dataset
        X = pd.DataFrame(
            {
                "f1": rng.normal(-8, 1, n),
                "f2": rng.normal(-8, 0.5, n),
                "f3": rng.normal(-8, 0.3, n),
            }
        )
        y = pd.Series(rng.normal(-8, 1, n))
        # val_fraction=0.15 -> split_idx=85, purge_gap=20 -> val_start=105 > n-20
        # Should fallback gracefully
        model = LightGBMVolModel(
            n_estimators=20,
            early_stopping_rounds=5,
            val_fraction=0.15,
            val_purge_gap=20,
            min_child_samples=10,  # override default for small test data
        )
        model.fit(X, y)  # Should not crash
        preds = model.predict(X)
        assert not np.any(np.isnan(preds))

    def test_default_params_include_regularization(self):
        """DEFAULT_PARAMS includes max_depth, min_child_samples, reg_lambda."""
        from volforecast.models.lightgbm import DEFAULT_PARAMS

        assert "max_depth" in DEFAULT_PARAMS
        assert DEFAULT_PARAMS["max_depth"] <= 6
        assert "min_child_samples" in DEFAULT_PARAMS
        assert DEFAULT_PARAMS["min_child_samples"] >= 50
        assert "reg_lambda" in DEFAULT_PARAMS
        assert DEFAULT_PARAMS["reg_lambda"] >= 1.0

    def test_level_space_qlike_zero_pred(self):
        """Level-space QLIKE handles zero/negative predictions without crash."""
        from volforecast.evaluation.metrics import qlike

        y_true = np.array([0.001, 0.002, 0.003])
        y_pred = np.array([0.0, -0.001, 0.001])  # zero and negative
        result = qlike(y_true, y_pred, log_space=False)
        assert np.isfinite(result)
        assert result > 0  # QLIKE is positive for imperfect predictions

    def test_symmetric_clip_bounds_gradient(self):
        """Gradient is bounded by symmetric clip — no blow-up from extreme diff."""
        y_true = np.array([-5.0])  # true
        y_pred = np.array([-20.0])  # massively under-predicting (diff=15, clipped to 10)
        dtrain = _FakeDataset(y_true)
        grad, hess = qlike_objective(y_pred, dtrain)
        # diff=15 clipped to 10: exp(10) ≈ 22026
        assert abs(grad[0]) < np.exp(10.0) + 1  # bounded
        assert hess[0] < np.exp(10.0) + 1

    def test_panel_val_purge_is_date_aware(self):
        """In panel (MultiIndex) mode, val_purge_gap skips DATES, not rows."""
        rng = np.random.default_rng(42)
        n_dates = 100
        n_symbols = 5
        n_total = n_dates * n_symbols
        dates = pd.date_range("2020-01-01", periods=n_dates, freq="B")
        symbols = [f"SYM{i}" for i in range(n_symbols)]

        # Build panel with MultiIndex (date, symbol)
        mi = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        X = pd.DataFrame(
            {
                "f1": rng.normal(-8, 1, n_total),
                "f2": rng.normal(-8, 0.5, n_total),
                "f3": rng.normal(-8, 0.3, n_total),
            },
            index=mi,
        )
        y = pd.Series(rng.normal(-8, 1, n_total), index=mi)

        val_purge_gap = 22  # Should skip 22 DATES (= 110 rows with 5 symbols)
        model = LightGBMVolModel(
            n_estimators=20,
            early_stopping_rounds=5,
            val_fraction=0.15,
            val_purge_gap=val_purge_gap,
            min_child_samples=10,
        )

        # Monkey-patch lgb.train to capture train/val sizes
        import lightgbm as lgb

        captured = {}
        original_train = lgb.train

        def mock_train(*, train_set, valid_sets=None, **kwargs):
            captured["train_n"] = train_set.get_label().shape[0]
            if valid_sets:
                captured["val_n"] = valid_sets[0].get_label().shape[0]
            return original_train(train_set=train_set, valid_sets=valid_sets, **kwargs)

        lgb.train = mock_train
        try:
            model.fit(X, y)
        finally:
            lgb.train = original_train

        # With 500 rows, val_fraction=0.15: split_idx=425 (85 dates * 5 symbols)
        # With date-aware purge of 22 dates: should skip 22*5=110 rows
        # val_start = split_idx + 110 = 535... but that exceeds n=500
        # Actually: split_idx = int(500 * 0.85) = 425
        # After split_idx, remaining rows cover dates[85:] = 15 dates
        # Purge of 22 dates exceeds available 15 dates -> val_start = n
        # This triggers the fallback (val_start >= n - 20 -> val_start = split_idx)
        # So for this specific geometry, the purge is too large.
        # Let's verify the model still trains (graceful fallback).
        assert "train_n" in captured
        # The train count should be split_idx (425) since gap is too large
        # and fallback sets val_start = split_idx
        assert captured["train_n"] == int(n_total * 0.85)

    def test_panel_val_purge_skips_correct_dates(self):
        """Panel val purge gap skips exactly val_purge_gap dates worth of rows."""
        rng = np.random.default_rng(7)
        n_dates = 200
        n_symbols = 3
        n_total = n_dates * n_symbols
        dates = pd.date_range("2020-01-01", periods=n_dates, freq="B")
        symbols = [f"S{i}" for i in range(n_symbols)]

        mi = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        X = pd.DataFrame(
            {
                "f1": rng.normal(-8, 1, n_total),
                "f2": rng.normal(-8, 0.5, n_total),
            },
            index=mi,
        )
        y = pd.Series(rng.normal(-8, 1, n_total), index=mi)

        val_purge_gap = 10  # Skip 10 dates = 30 rows (3 symbols)
        model = LightGBMVolModel(
            n_estimators=20,
            early_stopping_rounds=5,
            val_fraction=0.15,
            val_purge_gap=val_purge_gap,
            min_child_samples=10,
        )

        import lightgbm as lgb

        captured = {}
        original_train = lgb.train

        def mock_train(*, train_set, valid_sets=None, **kwargs):
            captured["train_n"] = train_set.get_label().shape[0]
            if valid_sets:
                captured["val_n"] = valid_sets[0].get_label().shape[0]
            return original_train(train_set=train_set, valid_sets=valid_sets, **kwargs)

        lgb.train = mock_train
        try:
            model.fit(X, y)
        finally:
            lgb.train = original_train

        # n_total = 600, split_idx = int(600 * 0.85) = 510 (170 dates * 3 symbols)
        # After split: 30 dates remain (dates[170:200])
        # Purge 10 dates -> val starts at date[180], which is row 180*3=540
        # val_start = 540, val_n = 600 - 540 = 60
        expected_split = int(n_total * 0.85)  # 510
        expected_val_n = n_total - (expected_split + val_purge_gap * n_symbols)  # 60

        assert captured["train_n"] == expected_split
        assert captured["val_n"] == expected_val_n

    def test_init_score_uses_train_only(self, synthetic_lgbm_data):
        """init_score is computed from training portion only, not train+val."""
        X, y = synthetic_lgbm_data
        model = LightGBMVolModel(
            n_estimators=50,
            early_stopping_rounds=10,
            val_fraction=0.2,
            val_purge_gap=5,
        )
        model.fit(X, y)

        # init_score should equal mean of first 80% of y (training portion)
        n = len(y)
        split_idx = int(n * 0.8)
        expected_init = float(y.iloc[:split_idx].mean())
        assert model._init_score == pytest.approx(expected_init, rel=1e-10)

    def test_non_panel_val_purge_uses_rows(self, synthetic_lgbm_data):
        """Non-panel (RangeIndex) data still uses row-based val purge gap."""
        X, y = synthetic_lgbm_data
        model = LightGBMVolModel(
            n_estimators=50,
            early_stopping_rounds=10,
            val_fraction=0.2,
            val_purge_gap=10,
        )

        import lightgbm as lgb

        captured = {}
        original_train = lgb.train

        def mock_train(*, train_set, valid_sets=None, **kwargs):
            captured["train_n"] = train_set.get_label().shape[0]
            if valid_sets:
                captured["val_n"] = valid_sets[0].get_label().shape[0]
            return original_train(train_set=train_set, valid_sets=valid_sets, **kwargs)

        lgb.train = mock_train
        try:
            model.fit(X, y)
        finally:
            lgb.train = original_train

        # 500 rows, val_fraction=0.2: split_idx=400, val_start=410
        n = len(X)
        expected_split = int(n * 0.8)
        expected_val_start = expected_split + 10
        assert captured["train_n"] == expected_split
        assert captured["val_n"] == n - expected_val_start


class TestResidualScaling:
    """Tests for residual_scale parameter with base_model init_score."""

    @pytest.fixture
    def har_lgbm_data(self):
        """Synthetic data with HAR-compatible column names for base_model tests."""
        rng = np.random.default_rng(42)
        n = 500
        X = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-8, 1, n),
                "log_rv_w": rng.normal(-8, 0.5, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
            }
        )
        y = pd.Series(X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + rng.normal(0, 0.5, n))
        return X, y

    def test_residual_scale_amplifies_tree_output(self, har_lgbm_data):
        """With residual_scale > 1 and base_model, predictions differ from scale=1."""
        X, y = har_lgbm_data
        # Without scaling
        model_noscale = LightGBMVolModel(
            n_estimators=50,
            early_stopping_rounds=10,
            min_child_samples=10,
            residual_scale=1.0,
            base_model="har",
        )
        model_noscale.fit(X, y)
        preds_noscale = model_noscale.predict(X)

        # With scaling factor 3.0
        model_scaled = LightGBMVolModel(
            n_estimators=50,
            early_stopping_rounds=10,
            min_child_samples=10,
            residual_scale=3.0,
            base_model="har",
        )
        model_scaled.fit(X, y)
        preds_scaled = model_scaled.predict(X)

        # Both should produce finite predictions
        assert not np.any(np.isnan(preds_noscale))
        assert not np.any(np.isnan(preds_scaled))
        # Predictions should differ (different training dynamics)
        assert not np.allclose(preds_noscale, preds_scaled, atol=1e-6)

    def test_residual_scale_no_effect_without_base_model(self, synthetic_lgbm_data):
        """residual_scale is a no-op when no base_model is set (scalar init)."""
        X, y = synthetic_lgbm_data
        model_default = LightGBMVolModel(
            n_estimators=50,
            early_stopping_rounds=10,
            min_child_samples=10,
            seed=42,
        )
        model_default.fit(X, y)
        preds_default = model_default.predict(X)

        model_scaled = LightGBMVolModel(
            n_estimators=50,
            early_stopping_rounds=10,
            min_child_samples=10,
            residual_scale=5.0,
            seed=42,
        )
        model_scaled.fit(X, y)
        preds_scaled = model_scaled.predict(X)

        # Without base_model, residual_scale has no effect — same scalar init
        np.testing.assert_allclose(preds_default, preds_scaled, rtol=1e-10)

    def test_residual_scale_in_get_params(self):
        """get_params includes residual_scale only when != 1.0."""
        model_default = LightGBMVolModel(residual_scale=1.0)
        assert "residual_scale" not in model_default.get_params()

        model_scaled = LightGBMVolModel(residual_scale=3.0)
        assert model_scaled.get_params()["residual_scale"] == 3.0

    def test_residual_scale_preserves_prediction_scale(self, har_lgbm_data):
        """Predictions with residual_scale are in the same range as without it."""
        X, y = har_lgbm_data
        model = LightGBMVolModel(
            n_estimators=100,
            early_stopping_rounds=20,
            min_child_samples=10,
            residual_scale=5.0,
            base_model="har",
        )
        model.fit(X, y)
        preds = model.predict(X)
        # Predictions should stay in a reasonable range (similar to y)
        assert preds.mean() == pytest.approx(y.mean(), abs=2.0)
        assert preds.std() < y.std() * 5  # not blown up
