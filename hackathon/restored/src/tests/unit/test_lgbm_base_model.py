"""Tests for LightGBM base_model (init_score from fitted model) feature."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

lgb = pytest.importorskip("lightgbm")

from volforecast.models.lightgbm import LightGBMVolModel  # noqa: E402
from volforecast.registry import ensure_registered  # noqa: E402


@pytest.fixture(autouse=True)
def _register_models():
    """Ensure all models are registered before tests run."""
    ensure_registered()


@pytest.fixture
def synthetic_hariv_data():
    """Synthetic data where y = linear(HAR-IV features) + nonlinear residual.

    The DGP is designed so that:
    - HAR-IV captures the linear signal (70% of variance)
    - A nonlinear term (interaction + threshold) is learnable by trees (30%)
    """
    rng = np.random.default_rng(42)
    n = 2000

    log_rv_d = rng.normal(-8, 1, n)
    log_rv_w = rng.normal(-8, 0.5, n)
    log_rv_m = rng.normal(-8, 0.3, n)
    log_atm_iv_d = rng.normal(-3, 0.4, n)

    # Linear component (what HAR-IV captures)
    linear = 0.4 * log_rv_d + 0.2 * log_rv_w + 0.1 * log_rv_m + 0.3 * log_atm_iv_d

    # Nonlinear residual (what the tree should learn)
    nonlinear = (
        0.1 * (log_rv_d > -7.5).astype(float) * log_atm_iv_d  # threshold interaction
        + 0.05 * np.abs(log_rv_d - log_rv_w)  # asymmetric spread
    )

    noise = rng.normal(0, 0.2, n)
    y = linear + nonlinear + noise

    X = pd.DataFrame(
        {
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_w,
            "log_rv_m": log_rv_m,
            "log_atm_iv_d": log_atm_iv_d,
        }
    )
    return X, pd.Series(y, name="target")


class TestBaseModelInitScore:
    """Tests for base_model parameter in LightGBMVolModel."""

    def test_base_model_fitted_internally(self, synthetic_hariv_data):
        """When base_model='har_iv', a HARIVModel is fitted during fit()."""
        X, y = synthetic_hariv_data
        model = LightGBMVolModel(
            n_estimators=50,
            val_fraction=0,
            base_model="har_iv",
        )
        model.fit(X, y)

        assert model._base_model is not None
        assert model._base_model.coefficients_ is not None
        assert len(model._base_model.coefficients_) == 4  # HAR-IV has 4 features

    def test_predict_returns_base_plus_tree(self, synthetic_hariv_data):
        """predict() returns base_model predictions + tree corrections."""
        X, y = synthetic_hariv_data
        model = LightGBMVolModel(
            n_estimators=100,
            val_fraction=0,
            base_model="har_iv",
        )
        model.fit(X, y)

        full_pred = model.predict(X)
        base_pred = model._base_model.predict(X)
        tree_pred = model._model.predict(X[model._feature_names])

        np.testing.assert_allclose(full_pred, base_pred + tree_pred, rtol=1e-10)

    def test_base_model_improves_qlike_over_standalone(self, synthetic_hariv_data):
        """LightGBM with base_model=har_iv beats standalone LightGBM on HAR-IV DGP."""
        X, y = synthetic_hariv_data

        # Standalone LightGBM (scalar init_score)
        standalone = LightGBMVolModel(n_estimators=200, val_fraction=0)
        standalone.fit(X, y)
        pred_standalone = standalone.predict(X)

        # LightGBM with HAR-IV base
        with_base = LightGBMVolModel(n_estimators=200, val_fraction=0, base_model="har_iv")
        with_base.fit(X, y)
        pred_base = with_base.predict(X)

        # QLIKE: mean(exp(y)/exp(pred) - y + pred - 1) — lower is better
        def qlike(y_true, y_pred):
            ratio = np.exp(y_true - y_pred)
            return np.mean(ratio - (y_true - y_pred) - 1)

        qlike_standalone = qlike(y.values, pred_standalone)
        qlike_with_base = qlike(y.values, pred_base)

        # With base_model should be at least as good (on in-sample data)
        assert qlike_with_base <= qlike_standalone

    def test_no_base_model_preserves_scalar_init(self, synthetic_hariv_data):
        """Without base_model, behavior is unchanged (scalar mean init_score)."""
        X, y = synthetic_hariv_data
        model = LightGBMVolModel(n_estimators=50, val_fraction=0.15, val_purge_gap=5)
        model.fit(X, y)

        # Should still have scalar _init_score, no _base_model
        assert model._base_model is None
        assert isinstance(model._init_score, float)

    def test_base_model_with_validation_split(self, synthetic_hariv_data):
        """base_model works correctly with early stopping (val_fraction > 0)."""
        X, y = synthetic_hariv_data
        model = LightGBMVolModel(
            n_estimators=200,
            val_fraction=0.15,
            val_purge_gap=5,
            early_stopping_rounds=20,
            base_model="har_iv",
        )
        model.fit(X, y)

        # Should have fitted base model and produced valid predictions
        assert model._base_model is not None
        preds = model.predict(X)
        assert not np.any(np.isnan(preds))
        assert len(preds) == len(X)

    def test_base_model_nan_fallback(self):
        """When base_model returns NaN for some rows, fallback to scalar for those."""
        rng = np.random.default_rng(99)
        n = 500
        X = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-8, 1, n),
                "log_rv_w": rng.normal(-8, 0.5, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
                "log_atm_iv_d": rng.normal(-3, 0.4, n),
            }
        )
        y = pd.Series(rng.normal(-8, 1, n))

        # Inject NaN into IV column for some rows (simulates missing options data)
        X.loc[100:120, "log_atm_iv_d"] = np.nan

        model = LightGBMVolModel(
            n_estimators=50,
            val_fraction=0,
            base_model="har_iv",
        )
        model.fit(X, y)

        # Predictions should still be valid (NaN rows get scalar fallback)
        preds = model.predict(X)
        # LightGBM handles NaN features natively, so all preds should be finite
        # The key check: model doesn't crash, and rows with NaN IV still get predictions
        assert len(preds) == n

    def test_get_params_includes_base_model(self, synthetic_hariv_data):
        """get_params() includes base_model so model can be re-instantiated."""
        X, y = synthetic_hariv_data
        model = LightGBMVolModel(
            n_estimators=50,
            val_fraction=0,
            base_model="har_iv",
        )
        model.fit(X, y)

        params = model.get_params()
        assert params["base_model"] == "har_iv"

        # Re-instantiate from params and fit again
        model2 = LightGBMVolModel(**params)
        model2.fit(X, y)
        preds2 = model2.predict(X)
        assert len(preds2) == len(X)
