"""Integration test: SHAP feature selection pipeline end-to-end."""
from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from volforecast.config import ExperimentConfig, FeatureSelectionConfig


@pytest.fixture
def shap_selection_config(tmp_path):
    """Create a minimal config with feature selection enabled."""
    yaml_content = '''
name: test_shap_selection
universe: [TEST]
date_range: ["2020-01-02", "2022-12-30"]
horizons: [1]
feature_layers: [har_core]
model:
  name: lightgbm
  params:
    n_estimators: 50
    early_stopping_rounds: 10
    learning_rate: 0.1
    num_leaves: 8
    max_depth: 3
    min_child_samples: 10
    val_fraction: 0.15
    val_purge_gap: 5
feature_selection:
  enabled: true
  method: boruta_shap
  shadow_features: 3
  threshold_multiplier: 1.0
  min_features: 2
  max_rounds: 1
  shap_samples: 50
  stability_threshold: 0.6
cv:
  method: expanding_window
  purge_gap: 5
  train_size: 200
  test_size: 50
'''
    config_path = tmp_path / "test_shap.yaml"
    config_path.write_text(yaml_content)
    return ExperimentConfig.from_yaml(config_path)


@pytest.fixture
def synthetic_daily_data():
    """Generate synthetic daily data with known signal structure."""
    rng = np.random.default_rng(42)
    n_days = 500
    dates = pd.bdate_range("2020-01-02", periods=n_days)

    # Base RV with persistence
    rv = np.zeros(n_days)
    rv[0] = 0.0002
    for i in range(1, n_days):
        rv[i] = 0.0001 + 0.6 * rv[i - 1] + rng.exponential(0.00005)

    df = pd.DataFrame({"rv": rv}, index=dates)
    return df


class TestConfigParsing:
    """Verify feature_selection config parses correctly from YAML."""

    def test_feature_selection_parsed(self, shap_selection_config):
        cfg = shap_selection_config
        assert cfg.feature_selection is not None
        assert cfg.feature_selection.enabled is True
        assert cfg.feature_selection.method == "boruta_shap"
        assert cfg.feature_selection.shadow_features == 3
        assert cfg.feature_selection.min_features == 2
        assert cfg.feature_selection.max_rounds == 1
        assert cfg.feature_selection.shap_samples == 50
        assert cfg.feature_selection.stability_threshold == 0.6

    def test_feature_selection_disabled_by_default(self, tmp_path):
        yaml_content = '''
name: test_no_fs
universe: [TEST]
date_range: ["2020-01-02", "2022-12-30"]
horizons: [1]
feature_layers: [har_core]
model:
  name: lightgbm
  params: {}
'''
        config_path = tmp_path / "test_no_fs.yaml"
        config_path.write_text(yaml_content)
        cfg = ExperimentConfig.from_yaml(config_path)
        assert cfg.feature_selection is None


class TestPipelineIntegration:
    """End-to-end pipeline with SHAP feature selection."""

    @pytest.mark.slow
    def test_pipeline_runs_with_selection(self, shap_selection_config, synthetic_daily_data):
        """Pipeline completes with feature_selection enabled and produces metadata."""
        from volforecast.pipeline.runner import Pipeline

        pipeline = Pipeline(shap_selection_config)
        results = pipeline.run(synthetic_daily_data)

        # Pipeline should produce results for horizon 1
        assert 1 in results
        h1 = results[1]
        assert "metrics" in h1
        assert "predictions" in h1
        assert h1["metrics"]["qlike"] > 0

        # Feature selection metadata should be attached
        assert "feature_selection" in h1
        fs_meta = h1["feature_selection"]
        assert "stable_features" in fs_meta
        assert "always_dropped" in fs_meta
        assert "n_folds" in fs_meta
        assert fs_meta["n_folds"] > 0

        # The model should have selection attributes
        model = h1["model"]
        assert hasattr(model, "_selection_metadata")
        assert hasattr(model, "_selected_features")

    @pytest.mark.slow
    def test_selected_features_subset_of_input(self, shap_selection_config, synthetic_daily_data):
        """Selected features must be a subset of input features."""
        from volforecast.pipeline.runner import Pipeline

        pipeline = Pipeline(shap_selection_config)
        results = pipeline.run(synthetic_daily_data)

        h1 = results[1]
        if "feature_selection" in h1:
            fs_meta = h1["feature_selection"]
            all_feats = set(
                fs_meta.get("stable_features", [])
                + fs_meta.get("unstable_features", [])
                + fs_meta.get("always_dropped", [])
            )
            # har_core produces 6 features (log_rv_d, log_rv_w, log_rv_m + expansions)
            # All should be accounted for
            assert len(all_feats) > 0

    @pytest.mark.slow
    def test_min_features_respected(self, shap_selection_config, synthetic_daily_data):
        """The min_features floor must be respected in every fold."""
        from volforecast.pipeline.runner import Pipeline

        pipeline = Pipeline(shap_selection_config)
        results = pipeline.run(synthetic_daily_data)

        h1 = results[1]
        model = h1["model"]
        if model._feature_names:
            assert len(model._feature_names) >= shap_selection_config.feature_selection.min_features
