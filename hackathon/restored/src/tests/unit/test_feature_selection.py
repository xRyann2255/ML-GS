"""Unit tests for SHAP-based feature selection."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from volforecast.pipeline.feature_selection import (
    SelectionResult,
    aggregate_fold_selections,
    select_features,
)


@pytest.fixture
def synthetic_data():
    """Create synthetic data with 3 informative + 3 noisy features."""
    rng = np.random.default_rng(42)
    n = 500
    # Informative features (correlated with target)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    x3 = rng.normal(0, 1, n)
    # Noisy features (pure random)
    noise1 = rng.normal(0, 1, n)
    noise2 = rng.normal(0, 1, n)
    noise3 = rng.normal(0, 1, n)

    y = 0.5 * x1 + 0.3 * x2 + 0.2 * x3 + rng.normal(0, 0.1, n)

    X = pd.DataFrame({
        "signal_1": x1,
        "signal_2": x2,
        "signal_3": x3,
        "noise_1": noise1,
        "noise_2": noise2,
        "noise_3": noise3,
    })
    return X, pd.Series(y, name="target")


@pytest.fixture
def mock_config():
    """Create a mock FeatureSelectionConfig."""
    from volforecast.config import FeatureSelectionConfig
    return FeatureSelectionConfig(
        enabled=True,
        method="shap_rfe",
        shadow_features=3,
        threshold_multiplier=1.0,
        min_features=2,
        max_rounds=2,
        shap_samples=100,
        stability_threshold=0.8,
    )


class TestAggregation:
    """Tests for aggregate_fold_selections."""

    def test_empty_input(self):
        result = aggregate_fold_selections([])
        assert result["stable_features"] == []
        assert result["n_folds"] == 0

    def test_all_folds_agree(self):
        results = [
            SelectionResult(
                selected_features=["a", "b", "c"],
                dropped_features=["d", "e"],
                feature_importances={"a": 0.5, "b": 0.3, "c": 0.2, "d": 0.01, "e": 0.005},
                shadow_threshold=0.05,
                n_rounds=1,
            )
            for _ in range(5)
        ]
        agg = aggregate_fold_selections(results, stability_threshold=0.8)
        assert set(agg["stable_features"]) == {"a", "b", "c"}
        assert set(agg["always_dropped"]) == {"d", "e"}
        assert agg["n_folds"] == 5

    def test_partial_agreement(self):
        results = [
            SelectionResult(
                selected_features=["a", "b", "c"],
                dropped_features=["d"],
                feature_importances={"a": 0.5, "b": 0.3, "c": 0.2, "d": 0.01},
                shadow_threshold=0.05,
                n_rounds=1,
            ),
            SelectionResult(
                selected_features=["a", "b"],
                dropped_features=["c", "d"],
                feature_importances={"a": 0.5, "b": 0.3, "c": 0.04, "d": 0.01},
                shadow_threshold=0.05,
                n_rounds=1,
            ),
        ]
        agg = aggregate_fold_selections(results, stability_threshold=0.8)
        # "a" and "b" selected in both folds (100%), "c" in 1/2 (50%)
        assert set(agg["stable_features"]) == {"a", "b"}
        assert "c" in agg["unstable_features"]
        assert "d" in agg["always_dropped"]

    def test_mean_importances(self):
        results = [
            SelectionResult(
                selected_features=["a"],
                dropped_features=[],
                feature_importances={"a": 0.4},
                shadow_threshold=0.05,
                n_rounds=1,
            ),
            SelectionResult(
                selected_features=["a"],
                dropped_features=[],
                feature_importances={"a": 0.6},
                shadow_threshold=0.05,
                n_rounds=1,
            ),
        ]
        agg = aggregate_fold_selections(results)
        assert abs(agg["mean_importances"]["a"] - 0.5) < 1e-10


class TestSelectFeatures:
    """Tests for the select_features function (mocked SHAP)."""

    def test_min_features_floor(self, synthetic_data, mock_config):
        """Ensure min_features floor is respected even if threshold drops everything."""
        X, y = synthetic_data
        mock_config.min_features = 4
        mock_config.max_rounds = 1

        # Mock SHAP to return very low values (below any threshold)
        low_shap = np.full((100, 6), 0.001)

        with patch("volforecast.pipeline.feature_selection._compute_shap") as mock_shap, \
             patch("volforecast.pipeline.feature_selection._compute_shadow_threshold") as mock_thresh:
            mock_shap.return_value = low_shap
            mock_thresh.return_value = 0.01  # Higher than all features

            # Use a mock model class
            mock_model = MagicMock()
            mock_model.return_value = mock_model
            mock_model._feature_names = list(X.columns)

            result = select_features(mock_model, {}, X, y, mock_config, seed=42)
            assert len(result.selected_features) >= mock_config.min_features

    def test_no_drop_when_all_important(self, synthetic_data, mock_config):
        """If all features beat the threshold, nothing is dropped."""
        X, y = synthetic_data
        mock_config.max_rounds = 1

        # Mock SHAP: all features have high importance
        high_shap = np.random.default_rng(42).normal(0, 1, (100, 6))
        high_shap = np.abs(high_shap) + 0.5  # All positive and high

        with patch("volforecast.pipeline.feature_selection._compute_shap") as mock_shap, \
             patch("volforecast.pipeline.feature_selection._compute_shadow_threshold") as mock_thresh:
            mock_shap.return_value = high_shap
            mock_thresh.return_value = 0.01  # Very low threshold

            mock_model = MagicMock()
            mock_model.return_value = mock_model
            mock_model._feature_names = list(X.columns)

            result = select_features(mock_model, {}, X, y, mock_config, seed=42)
            assert len(result.selected_features) == 6
            assert len(result.dropped_features) == 0

    def test_result_dataclass_fields(self, synthetic_data, mock_config):
        """Verify SelectionResult has all expected fields."""
        X, y = synthetic_data
        mock_config.max_rounds = 1

        shap_vals = np.random.default_rng(42).normal(0, 0.5, (100, 6))

        with patch("volforecast.pipeline.feature_selection._compute_shap") as mock_shap, \
             patch("volforecast.pipeline.feature_selection._compute_shadow_threshold") as mock_thresh:
            mock_shap.return_value = shap_vals
            mock_thresh.return_value = 0.3

            mock_model = MagicMock()
            mock_model.return_value = mock_model
            mock_model._feature_names = list(X.columns)

            result = select_features(mock_model, {}, X, y, mock_config, seed=42)
            assert isinstance(result, SelectionResult)
            assert isinstance(result.selected_features, list)
            assert isinstance(result.dropped_features, list)
            assert isinstance(result.feature_importances, dict)
            assert isinstance(result.shadow_threshold, float)
            assert isinstance(result.n_rounds, int)
            assert isinstance(result.round_history, list)
            # All features accounted for
            assert set(result.selected_features + result.dropped_features) == set(X.columns)
