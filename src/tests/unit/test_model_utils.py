"""Unit tests for evaluation._model_utils — model resolution and feature layers."""

from __future__ import annotations

import pytest


class TestResolveModel:
    """Test _resolve_model function."""

    def test_plain_label_returns_identity(self):
        from volforecast.evaluation._model_utils import resolve_model

        registry_name, display_label, params = resolve_model("har")
        assert registry_name == "har"
        assert display_label == "har"
        assert params == {}

    def test_model_params_override(self):
        from volforecast.evaluation._model_utils import resolve_model

        model_params = {"lightgbm": {"n_estimators": 500, "learning_rate": 0.05}}
        registry_name, display_label, params = resolve_model(
            "lightgbm", model_params=model_params
        )
        assert registry_name == "lightgbm"
        assert display_label == "lightgbm"
        assert params == {"n_estimators": 500, "learning_rate": 0.05}

    def test_model_configs_override(self):
        from volforecast.evaluation._model_utils import resolve_model

        model_configs = {
            "lgbm_locked": {"name": "lightgbm", "params": {"n_estimators": 1000}}
        }
        registry_name, display_label, params = resolve_model(
            "lgbm_locked", model_configs=model_configs
        )
        assert registry_name == "lightgbm"
        assert display_label == "lgbm_locked"
        assert params == {"n_estimators": 1000}

    def test_model_configs_precedence_over_params(self):
        from volforecast.evaluation._model_utils import resolve_model

        model_params = {"lgbm_locked": {"n_estimators": 100}}
        model_configs = {
            "lgbm_locked": {"name": "lightgbm", "params": {"n_estimators": 1000}}
        }
        _, _, params = resolve_model(
            "lgbm_locked", model_params=model_params, model_configs=model_configs
        )
        assert params == {"n_estimators": 1000}

    def test_unknown_label_with_no_overrides(self):
        from volforecast.evaluation._model_utils import resolve_model

        registry_name, display_label, params = resolve_model("nonexistent")
        assert registry_name == "nonexistent"
        assert display_label == "nonexistent"
        assert params == {}


class TestFeatureLayersForModel:
    """Test feature_layers_for_model function."""

    def test_har_returns_core(self):
        from volforecast.evaluation._model_utils import feature_layers_for_model

        assert feature_layers_for_model("har") == ["har_core"]

    def test_shar_returns_core_and_asymmetry(self):
        from volforecast.evaluation._model_utils import feature_layers_for_model

        result = feature_layers_for_model("shar")
        assert "har_core" in result
        assert "asymmetry" in result

    def test_unknown_model_returns_core(self):
        from volforecast.evaluation._model_utils import feature_layers_for_model

        assert feature_layers_for_model("nonexistent_xyz") == ["har_core"]

    def test_all_har_models_have_core(self):
        from volforecast.evaluation._model_utils import HAR_MODELS, feature_layers_for_model

        for model_name in HAR_MODELS:
            layers = feature_layers_for_model(model_name)
            assert "har_core" in layers


class TestConstants:
    """Test model constants are accessible."""

    def test_all_models_includes_har_and_ml(self):
        from volforecast.evaluation._model_utils import ALL_MODELS, HAR_MODELS, ML_MODELS

        for m in HAR_MODELS:
            assert m in ALL_MODELS
        for m in ML_MODELS:
            assert m in ALL_MODELS

    def test_har_models_list(self):
        from volforecast.evaluation._model_utils import HAR_MODELS

        assert "har" in HAR_MODELS
        assert "harq" in HAR_MODELS
        assert "shar" in HAR_MODELS
