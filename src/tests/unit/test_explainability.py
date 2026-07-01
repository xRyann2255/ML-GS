"""Tests for SHAP and ALE explainability computation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def tiny_lgbm_model():
    """Train a minimal LightGBM model for testing."""
    import lightgbm as lgb

    rng = np.random.default_rng(42)
    n_samples = 200
    n_features = 5

    X = pd.DataFrame(
        rng.standard_normal((n_samples, n_features)),
        columns=[f"feat_{i}" for i in range(n_features)],
    )
    # Target is a known function: feat_0 + 0.5*feat_1 + noise
    y = pd.Series(X["feat_0"] + 0.5 * X["feat_1"] + 0.1 * rng.standard_normal(n_samples))

    dtrain = lgb.Dataset(X, label=y)
    params = {"num_leaves": 8, "learning_rate": 0.1, "verbose": -1}
    booster = lgb.train(params, dtrain, num_boost_round=50)

    # Mock model object with the interface expected by compute_treeshap
    class MockModel:
        _model = booster
        _feature_names = list(X.columns)

        def predict(self, X_input):
            if isinstance(X_input, pd.DataFrame):
                return self._model.predict(X_input[self._feature_names])
            return self._model.predict(X_input)

    return MockModel(), X


@pytest.fixture
def monotone_lgbm_model():
    """Train a LightGBM model on a strictly monotone feature."""
    import lightgbm as lgb

    rng = np.random.default_rng(123)
    n_samples = 300

    X = pd.DataFrame({
        "monotone_feat": np.linspace(-3, 3, n_samples),
        "noise_feat": rng.standard_normal(n_samples),
    })
    # Target increases with monotone_feat
    y = pd.Series(2.0 * X["monotone_feat"] + 0.05 * rng.standard_normal(n_samples))

    dtrain = lgb.Dataset(X, label=y)
    params = {
        "num_leaves": 16,
        "learning_rate": 0.1,
        "verbose": -1,
        "monotone_constraints": [1, 0],
    }
    booster = lgb.train(params, dtrain, num_boost_round=100)

    class MockModel:
        _model = booster
        _feature_names = list(X.columns)

        def predict(self, X_input):
            if isinstance(X_input, pd.DataFrame):
                return self._model.predict(X_input[self._feature_names])
            return self._model.predict(X_input)

    return MockModel(), X


class TestComputeTreeSHAP:
    """Tests for compute_treeshap."""

    def test_output_shape(self, tiny_lgbm_model):
        """SHAP values shape = (n_samples, n_features)."""
        from volforecast.evaluation.explainability import compute_treeshap

        model, X = tiny_lgbm_model
        result = compute_treeshap(model, X, max_samples=50)
        assert result is not None
        assert result["shap_values"].shape == (50, 5)

    def test_base_value_type(self, tiny_lgbm_model):
        """base_value is a float."""
        from volforecast.evaluation.explainability import compute_treeshap

        model, X = tiny_lgbm_model
        result = compute_treeshap(model, X, max_samples=50)
        assert isinstance(result["base_value"], float)

    def test_feature_names_match(self, tiny_lgbm_model):
        """Feature names list matches input columns."""
        from volforecast.evaluation.explainability import compute_treeshap

        model, X = tiny_lgbm_model
        result = compute_treeshap(model, X, max_samples=50)
        assert result["feature_names"] == list(X.columns)

    def test_summary_sorted_descending(self, tiny_lgbm_model):
        """mean_abs_shap summary is sorted descending by value."""
        from volforecast.evaluation.explainability import compute_treeshap

        model, X = tiny_lgbm_model
        result = compute_treeshap(model, X, max_samples=100)
        values = [v for _, v in result["summary"]["mean_abs_shap"]]
        assert values == sorted(values, reverse=True)

    def test_shap_additivity(self, tiny_lgbm_model):
        """SHAP values + base_value ≈ model predictions."""
        from volforecast.evaluation.explainability import compute_treeshap

        model, X = tiny_lgbm_model
        # Use max_samples=None to get SHAP for all rows (avoids subsample mismatch)
        result = compute_treeshap(model, X, max_samples=None)
        reconstructed = result["shap_values"].sum(axis=1) + result["base_value"]
        predictions = model._model.predict(X)
        np.testing.assert_allclose(reconstructed, predictions, atol=1e-4)

    def test_max_samples_none_uses_all(self, tiny_lgbm_model):
        """max_samples=None uses all rows."""
        from volforecast.evaluation.explainability import compute_treeshap

        model, X = tiny_lgbm_model
        result = compute_treeshap(model, X, max_samples=None)
        assert result["shap_values"].shape[0] == len(X)

    def test_feature_values_included(self, tiny_lgbm_model):
        """Result contains feature_values matching shap_values shape."""
        from volforecast.evaluation.explainability import compute_treeshap

        model, X = tiny_lgbm_model
        result = compute_treeshap(model, X, max_samples=50)
        assert result["feature_values"].shape == result["shap_values"].shape

    def test_graceful_without_shap_package(self, tiny_lgbm_model, monkeypatch):
        """Returns None when shap package is not installed."""
        import volforecast.evaluation.explainability as mod

        # Simulate shap not available
        monkeypatch.setattr(mod, "_SHAP_AVAILABLE", False)
        model, X = tiny_lgbm_model
        result = mod.compute_treeshap(model, X, max_samples=50)
        assert result is None


class TestComputeALE:
    """Tests for compute_ale."""

    def test_grid_length(self, tiny_lgbm_model):
        """ALE grid has grid_size elements."""
        from volforecast.evaluation.explainability import compute_ale

        model, X = tiny_lgbm_model
        result = compute_ale(model, X, features=["feat_0"], grid_size=20)
        assert len(result["feat_0"]["grid"]) == 20

    def test_centered(self, tiny_lgbm_model):
        """ALE values are approximately zero-centered."""
        from volforecast.evaluation.explainability import compute_ale

        model, X = tiny_lgbm_model
        result = compute_ale(model, X, features=["feat_0"], grid_size=30)
        ale_vals = np.array(result["feat_0"]["ale"])
        # Weighted centering: mean(ALE * rug) ≈ 0
        rug = np.array(result["feat_0"]["rug"])
        if rug.sum() > 0:
            weighted_mean = np.average(ale_vals, weights=rug / rug.sum())
            assert abs(weighted_mean) < 0.5  # loose bound for small data

    def test_monotone_feature_produces_monotone_ale(self, monotone_lgbm_model):
        """A monotone-constrained feature produces roughly monotone ALE."""
        from volforecast.evaluation.explainability import compute_ale

        model, X = monotone_lgbm_model
        result = compute_ale(model, X, features=["monotone_feat"], grid_size=20)
        ale_vals = np.array(result["monotone_feat"]["ale"])
        # Check that ALE is mostly increasing (allow 1 violation for binning noise)
        diffs = np.diff(ale_vals)
        n_decreasing = (diffs < -0.01).sum()
        assert n_decreasing <= 2, f"ALE not monotone: {n_decreasing} decreases"

    def test_handles_nan(self, tiny_lgbm_model):
        """ALE handles NaN features gracefully."""
        from volforecast.evaluation.explainability import compute_ale

        model, X = tiny_lgbm_model
        X_with_nan = X.copy()
        X_with_nan.iloc[0:10, 0] = np.nan
        result = compute_ale(model, X_with_nan, features=["feat_0"], grid_size=20)
        assert result is not None
        assert "feat_0" in result
        assert len(result["feat_0"]["ale"]) == 20

    def test_no_external_deps(self):
        """ALE computation uses only numpy/pandas (no extra package)."""
        import inspect
        from volforecast.evaluation.explainability import compute_ale

        source = inspect.getsource(compute_ale)
        # Should not import shap, alibi, PyALE, etc.
        assert "import shap" not in source
        assert "import alibi" not in source
        assert "import PyALE" not in source

    def test_rug_sums_to_sample_count(self, tiny_lgbm_model):
        """Rug counts sum to number of non-NaN samples."""
        from volforecast.evaluation.explainability import compute_ale

        model, X = tiny_lgbm_model
        result = compute_ale(model, X, features=["feat_0"], grid_size=20)
        rug_sum = sum(result["feat_0"]["rug"])
        assert rug_sum == len(X)

    def test_multiple_features(self, tiny_lgbm_model):
        """ALE for multiple features returns all requested."""
        from volforecast.evaluation.explainability import compute_ale

        model, X = tiny_lgbm_model
        result = compute_ale(model, X, features=["feat_0", "feat_1", "feat_2"], grid_size=15)
        assert set(result.keys()) == {"feat_0", "feat_1", "feat_2"}
        for feat in result:
            assert len(result[feat]["grid"]) == 15
            assert len(result[feat]["ale"]) == 15
            assert len(result[feat]["rug"]) == 15
