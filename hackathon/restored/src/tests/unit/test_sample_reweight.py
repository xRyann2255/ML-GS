"""Tests for QLIKE-importance sample reweighting in XGBoost and LightGBM."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

xgb = pytest.importorskip("xgboost")
lgb = pytest.importorskip("lightgbm")

from volforecast.models.xgboost import XGBoostVolModel  # noqa: E402
from volforecast.models.lightgbm import LightGBMVolModel  # noqa: E402


@pytest.fixture
def synthetic_data():
    """Synthetic log-RV data with heterogeneous difficulty.

    Creates data where some samples are deliberately harder to predict
    (higher variance noise) to exercise the reweighting logic.
    """
    rng = np.random.default_rng(42)
    n = 400
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
            "feature_a": rng.normal(0, 1, n),
            "feature_b": rng.normal(0, 1, n),
        }
    )
    # Target with heterogeneous noise: first half = easy, second half = hard
    noise = np.concatenate([
        rng.normal(0, 0.2, n // 2),  # easy samples
        rng.normal(0, 1.5, n // 2),  # hard samples (high QLIKE)
    ])
    y = pd.Series(X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + noise)
    return X, y


class TestXGBoostReweight:
    """Tests for XGBoost sample reweighting."""

    def test_disabled_by_default(self, synthetic_data):
        """Without sample_reweight config, model trains normally (single pass)."""
        X, y = synthetic_data
        model = XGBoostVolModel(
            n_estimators=50, val_fraction=0.15, early_stopping_rounds=10,
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))

    def test_reweight_changes_predictions(self, synthetic_data):
        """Reweight enabled produces different predictions than disabled."""
        X, y = synthetic_data

        # Model without reweight
        model_no_rw = XGBoostVolModel(
            n_estimators=50, val_fraction=0.15, early_stopping_rounds=10,
            seed=42,
        )
        model_no_rw.fit(X, y)
        preds_no_rw = model_no_rw.predict(X)

        # Model with reweight
        model_rw = XGBoostVolModel(
            n_estimators=50, val_fraction=0.15, early_stopping_rounds=10,
            seed=42,
            sample_reweight={
                "enabled": True,
                "alpha": 1.0,
                "source": "conditional",
                "clip_max": 10.0,
                "normalize": True,
            },
        )
        model_rw.fit(X, y)
        preds_rw = model_rw.predict(X)

        # Predictions should differ (weights changed the tree structure)
        assert not np.allclose(preds_no_rw, preds_rw, atol=1e-6)

    def test_reweight_disabled_explicit(self, synthetic_data):
        """enabled=False in config produces same as no config."""
        X, y = synthetic_data

        model_none = XGBoostVolModel(
            n_estimators=30, val_fraction=0.0, seed=42,
        )
        model_none.fit(X, y)
        preds_none = model_none.predict(X)

        model_disabled = XGBoostVolModel(
            n_estimators=30, val_fraction=0.0, seed=42,
            sample_reweight={"enabled": False, "alpha": 1.0},
        )
        model_disabled.fit(X, y)
        preds_disabled = model_disabled.predict(X)

        np.testing.assert_allclose(preds_none, preds_disabled, atol=1e-6)

    def test_reweight_no_val_path(self, synthetic_data):
        """Reweight works in the no-validation (val_fraction=0) path."""
        X, y = synthetic_data
        model = XGBoostVolModel(
            n_estimators=30, val_fraction=0.0,
            sample_reweight={
                "enabled": True,
                "alpha": 0.5,
                "source": "conditional",
                "clip_max": 10.0,
                "normalize": True,
            },
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))

    def test_raw_source_mode(self, synthetic_data):
        """source='raw' uses init-only residuals (no pass-1 tree correction)."""
        X, y = synthetic_data
        model = XGBoostVolModel(
            n_estimators=30, val_fraction=0.15, early_stopping_rounds=10,
            sample_reweight={
                "enabled": True,
                "alpha": 1.0,
                "source": "raw",
                "clip_max": 10.0,
                "normalize": True,
            },
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))


class TestLightGBMReweight:
    """Tests for LightGBM sample reweighting."""

    def test_disabled_by_default(self, synthetic_data):
        """Without sample_reweight config, model trains normally."""
        X, y = synthetic_data
        model = LightGBMVolModel(
            n_estimators=50, val_fraction=0.15, early_stopping_rounds=10,
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))

    def test_reweight_changes_predictions(self, synthetic_data):
        """Reweight enabled produces different predictions than disabled."""
        X, y = synthetic_data

        # Use constrained model (high min_child_samples, few rounds) so the
        # model can't perfectly fit and weights actually change OOS behavior.
        model_no_rw = LightGBMVolModel(
            n_estimators=20, val_fraction=0.0,
            seed=42, num_leaves=4, min_child_samples=50,
            learning_rate=0.1,
        )
        model_no_rw.fit(X, y)
        preds_no_rw = model_no_rw.predict(X)

        model_rw = LightGBMVolModel(
            n_estimators=20, val_fraction=0.0,
            seed=42, num_leaves=4, min_child_samples=50,
            learning_rate=0.1,
            sample_reweight={
                "enabled": True,
                "alpha": 2.0,
                "source": "raw",
                "clip_max": 10.0,
                "normalize": True,
            },
        )
        model_rw.fit(X, y)
        preds_rw = model_rw.predict(X)

        # Predictions should differ (weights changed the tree structure)
        assert not np.allclose(preds_no_rw, preds_rw, atol=1e-6)

    def test_reweight_no_val_path(self, synthetic_data):
        """Reweight works in the no-validation path."""
        X, y = synthetic_data
        model = LightGBMVolModel(
            n_estimators=30, val_fraction=0.0,
            sample_reweight={
                "enabled": True,
                "alpha": 0.5,
                "source": "conditional",
                "clip_max": 10.0,
                "normalize": True,
            },
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))

    def test_raw_source_mode(self, synthetic_data):
        """source='raw' uses init-only residuals."""
        X, y = synthetic_data
        model = LightGBMVolModel(
            n_estimators=30, val_fraction=0.15, early_stopping_rounds=10,
            sample_reweight={
                "enabled": True,
                "alpha": 1.0,
                "source": "raw",
                "clip_max": 10.0,
                "normalize": True,
            },
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)


class TestReweightComputation:
    """Tests for weight computation logic (normalization, clipping)."""

    def test_weights_normalized_to_mean_one(self, synthetic_data):
        """When normalize=True, weights should have mean ~1."""
        X, y = synthetic_data
        model = XGBoostVolModel(
            n_estimators=30, val_fraction=0.0,
            sample_reweight={
                "enabled": True,
                "alpha": 1.0,
                "source": "conditional",
                "clip_max": 100.0,  # high ceiling to avoid interference
                "normalize": True,
            },
        )
        # Fit pass 1 manually to test _compute_reweight
        import xgboost as xgb_mod

        X_clean, y_clean, _ = model._clean_inputs(X.copy(), y.copy())
        y_clean = model._fit_base_model(X_clean, y_clean)
        init = np.full(len(X_clean), float(y_clean.mean()))
        model._init_score = float(y_clean.mean())

        train_params = {k: v for k, v in model.params.items()
                        if k not in {"val_fraction", "val_purge_gap",
                                     "early_stopping_rounds", "n_estimators",
                                     "drop_features", "residual_scale",
                                     "sample_reweight"}}
        from volforecast.models.xgboost import qlike_objective_xgb, _INIT_ONLY_KEYS

        dtrain = xgb_mod.DMatrix(X_clean, label=y_clean, feature_names=model._feature_names)
        dtrain.set_base_margin(init)
        model._model = xgb_mod.train(
            params=train_params, dtrain=dtrain, num_boost_round=30,
            obj=qlike_objective_xgb, verbose_eval=False,
        )

        weights = model._compute_reweight(X_clean, y_clean, init, {
            "alpha": 1.0, "source": "conditional",
            "clip_max": 100.0, "normalize": True,
        })

        assert abs(weights.mean() - 1.0) < 0.01

    def test_weights_clipped_at_ceiling(self, synthetic_data):
        """Weights should not exceed clip_max."""
        X, y = synthetic_data
        model = XGBoostVolModel(
            n_estimators=30, val_fraction=0.0,
            sample_reweight={
                "enabled": True,
                "alpha": 2.0,
                "source": "conditional",
                "clip_max": 5.0,
                "normalize": False,
            },
        )
        import xgboost as xgb_mod
        from volforecast.models.xgboost import qlike_objective_xgb

        X_clean, y_clean, _ = model._clean_inputs(X.copy(), y.copy())
        y_clean = model._fit_base_model(X_clean, y_clean)
        init = np.full(len(X_clean), float(y_clean.mean()))
        model._init_score = float(y_clean.mean())

        train_params = {k: v for k, v in model.params.items()
                        if k not in {"val_fraction", "val_purge_gap",
                                     "early_stopping_rounds", "n_estimators",
                                     "drop_features", "residual_scale",
                                     "sample_reweight"}}
        dtrain = xgb_mod.DMatrix(X_clean, label=y_clean, feature_names=model._feature_names)
        dtrain.set_base_margin(init)
        model._model = xgb_mod.train(
            params=train_params, dtrain=dtrain, num_boost_round=30,
            obj=qlike_objective_xgb, verbose_eval=False,
        )

        weights = model._compute_reweight(X_clean, y_clean, init, {
            "alpha": 2.0, "source": "conditional",
            "clip_max": 5.0, "normalize": False,
        })

        assert weights.max() <= 5.0 + 1e-10

    def test_weights_floored(self, synthetic_data):
        """Weights should never be zero (floor at 1e-4 before alpha)."""
        X, y = synthetic_data
        # Make y = prediction exactly for some samples (zero QLIKE)
        model = XGBoostVolModel(n_estimators=5, val_fraction=0.0)
        import xgboost as xgb_mod
        from volforecast.models.xgboost import qlike_objective_xgb

        X_clean, y_clean, _ = model._clean_inputs(X.copy(), y.copy())
        y_clean = model._fit_base_model(X_clean, y_clean)
        init = np.full(len(X_clean), float(y_clean.mean()))
        model._init_score = float(y_clean.mean())

        train_params = {k: v for k, v in model.params.items()
                        if k not in {"val_fraction", "val_purge_gap",
                                     "early_stopping_rounds", "n_estimators",
                                     "drop_features", "residual_scale",
                                     "sample_reweight"}}
        dtrain = xgb_mod.DMatrix(X_clean, label=y_clean, feature_names=model._feature_names)
        dtrain.set_base_margin(init)
        model._model = xgb_mod.train(
            params=train_params, dtrain=dtrain, num_boost_round=5,
            obj=qlike_objective_xgb, verbose_eval=False,
        )

        weights = model._compute_reweight(X_clean, y_clean, init, {
            "alpha": 1.0, "source": "conditional",
            "clip_max": 10.0, "normalize": False,
        })

        assert (weights > 0).all()
        assert weights.min() >= 1e-4
