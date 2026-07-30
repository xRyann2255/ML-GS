"""Tests for LightGBMBaggedSeeds (K-seed bagging ensemble)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

lgb = pytest.importorskip("lightgbm")

from volforecast.models.ensemble import (  # noqa: E402
    _DEFAULT_SEED_POOL,
    LightGBMBaggedSeeds,
)
from volforecast.registry import MODEL_REGISTRY, ensure_registered  # noqa: E402


@pytest.fixture
def synthetic_lgbm_data():
    """Small synthetic log-RV panel."""
    rng = np.random.default_rng(42)
    n = 400
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
        }
    )
    y = pd.Series(X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + rng.normal(0, 0.5, n))
    return X, y


class TestRegistration:
    def test_registered_under_lightgbm_bagged(self):
        ensure_registered()
        assert "lightgbm_bagged" in MODEL_REGISTRY
        assert MODEL_REGISTRY["lightgbm_bagged"] is LightGBMBaggedSeeds

    def test_class_name_attribute(self):
        assert LightGBMBaggedSeeds.name == "lightgbm_bagged"


class TestConstructor:
    def test_default_uses_first_n_pool_seeds(self):
        model = LightGBMBaggedSeeds(n_seeds=3)
        assert model.seeds == _DEFAULT_SEED_POOL[:3]
        assert model.n_seeds == 3

    def test_default_5_matches_reseed_baseline(self):
        """First 5 default seeds must match trial-047 reseed baseline so
        bagged-5 is directly comparable against the per-seed envelope."""
        model = LightGBMBaggedSeeds(n_seeds=5)
        assert tuple(model.seeds) == (42, 123, 456, 789, 2026)

    def test_explicit_seeds_override_default(self):
        model = LightGBMBaggedSeeds(n_seeds=3, seeds=[1, 2, 3])
        assert model.seeds == (1, 2, 3)

    def test_n_seeds_mismatch_with_explicit_seeds_raises(self):
        with pytest.raises(ValueError, match="len.seeds"):
            LightGBMBaggedSeeds(n_seeds=3, seeds=[1, 2])

    def test_zero_seeds_raises(self):
        with pytest.raises(ValueError, match="n_seeds must be >= 1"):
            LightGBMBaggedSeeds(n_seeds=0)

    def test_too_many_seeds_raises_without_explicit_list(self):
        too_many = len(_DEFAULT_SEED_POOL) + 1
        with pytest.raises(ValueError, match="exceeds default pool"):
            LightGBMBaggedSeeds(n_seeds=too_many)

    def test_incoming_seed_kwarg_is_stripped(self):
        """User-supplied `seed=999` must be ignored — per-member seeds rule."""
        model = LightGBMBaggedSeeds(n_seeds=2, seed=999)
        assert "seed" not in model._member_kwargs


class TestFit:
    def test_fits_k_distinct_members(self, synthetic_lgbm_data):
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(n_seeds=3, n_estimators=20, val_fraction=0.0)
        model.fit(X, y)
        assert len(model._members) == 3
        # Each member is a real LightGBMVolModel
        from volforecast.models.lightgbm import LightGBMVolModel

        for m in model._members:
            assert isinstance(m, LightGBMVolModel)

    def test_member_seeds_are_distinct(self, synthetic_lgbm_data):
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(n_seeds=3, n_estimators=20, val_fraction=0.0)
        model.fit(X, y)
        member_seeds = [m.params["seed"] for m in model._members]
        assert member_seeds == list(_DEFAULT_SEED_POOL[:3])
        assert len(set(member_seeds)) == 3

    def test_member_predictions_differ(self, synthetic_lgbm_data):
        """Different seeds must produce non-identical predictions — otherwise
        averaging gives zero variance reduction and the whole point is moot."""
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(n_seeds=3, n_estimators=50, val_fraction=0.15)
        model.fit(X, y)
        preds = [m.predict(X) for m in model._members]
        # At least one pair must differ in some position.
        assert not np.allclose(preds[0], preds[1])
        assert not np.allclose(preds[0], preds[2])


class TestPredict:
    def test_predict_shape(self, synthetic_lgbm_data):
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(n_seeds=3, n_estimators=20, val_fraction=0.0)
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))

    def test_predict_is_mean_of_members(self, synthetic_lgbm_data):
        """predict() must equal np.mean(member_predictions, axis=0)."""
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(n_seeds=3, n_estimators=20, val_fraction=0.0)
        model.fit(X, y)
        ensemble_pred = model.predict(X)
        member_preds = np.stack([m.predict(X) for m in model._members], axis=0)
        expected = member_preds.mean(axis=0)
        np.testing.assert_array_almost_equal(ensemble_pred, expected)

    def test_predict_before_fit_raises(self):
        model = LightGBMBaggedSeeds(n_seeds=2)
        with pytest.raises(RuntimeError, match="not been fitted"):
            model.predict(pd.DataFrame({"x": [1.0]}))

    def test_variance_reduction_vs_single_member(self, synthetic_lgbm_data):
        """The ensemble's prediction variance across multiple bootstrap samples
        should be <= the average member's variance. This is the whole point.

        Use a deterministic check: bag-of-3 prediction at row i must lie in the
        convex hull of member predictions at row i, so |ensemble - true_mean|
        <= max member deviation.
        """
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(n_seeds=3, n_estimators=50, val_fraction=0.15)
        model.fit(X, y)
        ensemble_pred = model.predict(X)
        member_preds = np.stack([m.predict(X) for m in model._members], axis=0)
        per_row_min = member_preds.min(axis=0)
        per_row_max = member_preds.max(axis=0)
        # Average must always lie between min and max of members.
        assert np.all(ensemble_pred >= per_row_min - 1e-9)
        assert np.all(ensemble_pred <= per_row_max + 1e-9)


class TestSummary:
    def test_summary_averages_feature_importance(self, synthetic_lgbm_data):
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(n_seeds=2, n_estimators=20, val_fraction=0.0)
        model.fit(X, y)
        summary = model.summary
        assert set(summary.keys()) <= set(X.columns)  # subset (LightGBM may skip features)
        # Manually average and compare
        m0 = model._members[0].summary
        m1 = model._members[1].summary
        keys = set(m0.keys()) | set(m1.keys())
        for k in keys:
            expected = (m0.get(k, 0.0) + m1.get(k, 0.0)) / 2
            assert abs(summary[k] - expected) < 1e-9

    def test_summary_before_fit_returns_empty(self):
        model = LightGBMBaggedSeeds(n_seeds=2)
        assert model.summary == {}


class TestGetParams:
    def test_get_params_is_replayable(self, synthetic_lgbm_data):
        """get_params() output must reconstruct an equivalent model."""
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(
            n_seeds=3,
            n_estimators=20,
            val_fraction=0.0,
            num_leaves=8,
            learning_rate=0.1,
        )
        params = model.get_params()
        assert params["n_seeds"] == 3
        assert params["seeds"] == list(_DEFAULT_SEED_POOL[:3])
        assert params["n_estimators"] == 20
        assert params["num_leaves"] == 8

        # Round-trip: instantiate from params and verify same seeds.
        replayed = LightGBMBaggedSeeds(**params)
        assert tuple(replayed.seeds) == tuple(model.seeds)


class TestBaseModelInit:
    def test_works_with_har_iv_0dte_init_score(self, synthetic_lgbm_data):
        """Smoke-test that bagging works with a base linear model providing
        init_score (the trial-036 champion uses base_model=har_iv_0dte)."""
        X, y = synthetic_lgbm_data
        model = LightGBMBaggedSeeds(
            n_seeds=2,
            n_estimators=20,
            val_fraction=0.0,
            base_model="ewma",  # simplest base in the registry
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)
        assert not np.any(np.isnan(preds))
