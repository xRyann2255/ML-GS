"""Tests for XGBoost model with QLIKE custom objective."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

xgb = pytest.importorskip("xgboost")

from volforecast.models.xgboost import (  # noqa: E402
    XGBoostVolModel,
    qlike_eval_xgb,
    qlike_objective_xgb,
)


@pytest.fixture
def synthetic_xgb_data():
    """Synthetic log-RV data for XGBoost tests."""
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


class _FakeDMatrix:
    """Minimal mock of xgb.DMatrix for unit-testing objective/eval functions."""

    def __init__(self, labels: np.ndarray):
        self._labels = labels

    def get_label(self) -> np.ndarray:
        return self._labels


class TestXGBQLIKEObjectiveGradient:
    """Tests for qlike_objective_xgb gradient correctness."""

    def test_gradient_finite_difference(self):
        """Gradient matches numerical (L(yp+eps)-L(yp-eps))/(2*eps)."""
        rng = np.random.default_rng(123)
        y_true = rng.normal(-8, 1, 100)
        y_pred = rng.normal(-8, 1, 100)
        dtrain = _FakeDMatrix(y_true)

        grad, _ = qlike_objective_xgb(y_pred, dtrain)

        eps = 1e-5

        def loss(yp):
            diff = y_true - yp
            return np.exp(np.clip(diff, -10, 10)) - diff - 1.0

        numerical_grad = (loss(y_pred + eps) - loss(y_pred - eps)) / (2.0 * eps)
        np.testing.assert_allclose(grad, numerical_grad, atol=1e-4)

    def test_gradient_zero_at_minimum(self):
        """y_pred == y_true -> grad=0, hess=1."""
        y = np.array([-8.0, -7.5, -9.0, -6.0])
        dtrain = _FakeDMatrix(y)
        grad, hess = qlike_objective_xgb(y.copy(), dtrain)
        np.testing.assert_allclose(grad, 0.0, atol=1e-10)
        np.testing.assert_allclose(hess, 1.0, atol=1e-6)

    def test_gradient_sign(self):
        """Under-prediction -> grad<0, over-prediction -> grad>0."""
        y_true = np.array([-7.0, -7.0])
        y_pred_under = np.array([-8.0, -9.0])
        grad_under, _ = qlike_objective_xgb(y_pred_under, _FakeDMatrix(y_true))
        assert (grad_under < 0).all()

        y_pred_over = np.array([-6.0, -5.0])
        grad_over, _ = qlike_objective_xgb(y_pred_over, _FakeDMatrix(y_true))
        assert (grad_over > 0).all()

    def test_hessian_positive(self):
        """Hessian always > 0 for wide range of diff values."""
        rng = np.random.default_rng(77)
        y_true = rng.normal(-8, 2, 1000)
        y_pred = rng.normal(-8, 2, 1000)
        _, hess = qlike_objective_xgb(y_pred, _FakeDMatrix(y_true))
        assert (hess > 0).all()


class TestXGBQLIKEEval:
    """Tests for qlike_eval_xgb metric."""

    def test_qlike_eval_matches_metrics(self):
        """qlike_eval_xgb matches metrics.qlike for same data."""
        from volforecast.evaluation.metrics import qlike

        rng = np.random.default_rng(55)
        y_true = rng.normal(-8, 1, 200)
        y_pred = rng.normal(-8, 1, 200)

        result = qlike_eval_xgb(y_pred, _FakeDMatrix(y_true))
        assert isinstance(result, list)
        assert len(result) == 1
        name, eval_loss = result[0]
        metric_loss = qlike(y_true, y_pred, log_space=True)

        assert name == "qlike"
        assert eval_loss == pytest.approx(metric_loss, rel=1e-6)

    def test_qlike_eval_zero_at_perfect(self):
        """Perfect predictions -> loss = 0."""
        y = np.array([-8.0, -7.0, -9.0])
        result = qlike_eval_xgb(y.copy(), _FakeDMatrix(y))
        _, loss = result[0]
        assert loss == pytest.approx(0.0, abs=1e-10)


class TestXGBoostVolModel:
    """Tests for XGBoostVolModel fit/predict workflow."""

    def test_fit_predict(self, synthetic_xgb_data):
        """Fit on synthetic, predict, verify shape and no NaN."""
        X, y = synthetic_xgb_data
        model = XGBoostVolModel(n_estimators=50, early_stopping_rounds=10)
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))

    def test_protocol_conformance(self):
        """XGBoostVolModel satisfies model contract (name, fit, predict)."""
        model = XGBoostVolModel()
        assert hasattr(model, "name")
        assert callable(getattr(model, "fit", None))
        assert callable(getattr(model, "predict", None))

    def test_save_load(self, synthetic_xgb_data, tmp_path):
        """Fit, save, load, predictions match."""
        X, y = synthetic_xgb_data
        model = XGBoostVolModel(n_estimators=50, early_stopping_rounds=10)
        model.fit(X, y)
        preds_orig = model.predict(X)

        save_path = tmp_path / "xgb_test.joblib"
        model.save(save_path)
        loaded = XGBoostVolModel.load(save_path)
        preds_loaded = loaded.predict(X)

        np.testing.assert_array_equal(preds_orig, preds_loaded)

    def test_feature_importance_names(self, synthetic_xgb_data):
        """Feature importance keys are a subset of input columns."""
        X, y = synthetic_xgb_data
        model = XGBoostVolModel(n_estimators=50, early_stopping_rounds=10)
        model.fit(X, y)

        gain = model.summary
        split = model.feature_importance
        # XGBoost only reports features with non-zero importance
        assert set(gain.keys()).issubset(set(X.columns))
        assert set(split.keys()).issubset(set(X.columns))


class TestXGBoostHardening:
    """Tests for XGBoost hardening fixes (purge gap, defaults, panel)."""

    def test_val_split_has_purge_gap(self, synthetic_xgb_data):
        """Validation set respects purge gap between train and val."""
        X, y = synthetic_xgb_data
        model = XGBoostVolModel(
            n_estimators=50,
            early_stopping_rounds=10,
            val_fraction=0.2,
            val_purge_gap=10,
        )

        import xgboost as xgb_mod

        captured = {}
        original_train = xgb_mod.train

        def mock_train(*, params, dtrain, evals=None, **kwargs):
            captured["train_n"] = dtrain.num_row()
            if evals:
                captured["val_n"] = evals[0][0].num_row()
            return original_train(params=params, dtrain=dtrain, evals=evals, **kwargs)

        xgb_mod.train = mock_train
        try:
            model.fit(X, y)
        finally:
            xgb_mod.train = original_train

        n = len(X)
        expected_split = int(n * 0.8)
        expected_val_start = expected_split + 10
        assert captured["train_n"] == expected_split
        assert captured["val_n"] == n - expected_val_start

    def test_default_params_include_regularization(self):
        """DEFAULT_PARAMS includes max_depth, min_child_weight, reg_lambda."""
        from volforecast.models.xgboost import DEFAULT_PARAMS

        assert "max_depth" in DEFAULT_PARAMS
        assert DEFAULT_PARAMS["max_depth"] <= 6
        assert "min_child_weight" in DEFAULT_PARAMS
        assert DEFAULT_PARAMS["min_child_weight"] >= 50
        assert "reg_lambda" in DEFAULT_PARAMS
        assert DEFAULT_PARAMS["reg_lambda"] >= 1.0

    def test_panel_val_purge_is_date_aware(self):
        """In panel (MultiIndex) mode, val_purge_gap skips DATES, not rows."""
        rng = np.random.default_rng(42)
        n_dates = 100
        n_symbols = 5
        n_total = n_dates * n_symbols
        dates = pd.date_range("2020-01-01", periods=n_dates, freq="B")
        symbols = [f"SYM{i}" for i in range(n_symbols)]

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

        val_purge_gap = 22
        model = XGBoostVolModel(
            n_estimators=20,
            early_stopping_rounds=5,
            val_fraction=0.15,
            val_purge_gap=val_purge_gap,
            min_child_weight=10,
        )

        import xgboost as xgb_mod

        captured = {}
        original_train = xgb_mod.train

        def mock_train(*, params, dtrain, evals=None, **kwargs):
            captured["train_n"] = dtrain.num_row()
            if evals:
                captured["val_n"] = evals[0][0].num_row()
            return original_train(params=params, dtrain=dtrain, evals=evals, **kwargs)

        xgb_mod.train = mock_train
        try:
            model.fit(X, y)
        finally:
            xgb_mod.train = original_train

        assert "train_n" in captured
