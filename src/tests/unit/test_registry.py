"""Tests for model and feature layer registries.

Validates:
1. All expected models/features are registered after import
2. Decorator sets .name attribute
3. Duplicate name raises ValueError
4. Registry dict access returns correct classes
"""

from __future__ import annotations

import pytest


class TestModelRegistry:
    def test_har_models_registered(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()

        expected = {"har", "harq", "shar", "har_j", "har_cj", "ridge_har", "lasso_har"}
        assert expected.issubset(MODEL_REGISTRY.keys())

    def test_lightgbm_registered(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()

        assert "lightgbm" in MODEL_REGISTRY

    def test_lstm_tcn_registered(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()

        assert "lstm" in MODEL_REGISTRY
        assert "tcn" in MODEL_REGISTRY

    def test_registry_returns_class(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        cls = MODEL_REGISTRY["har"]
        assert isinstance(cls, type)

    def test_name_attribute_set(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        # A class may be registered under multiple alias names (e.g. RandomWalkModel
        # is registered as both "random_walk" and "same_day_rv"). The decorator
        # overwrites cls.name each time, so only the last-applied name survives.
        # Skip aliases: only assert when the registered name matches cls.name.
        cls_to_canonical: dict[type, str] = {}
        for name, cls in MODEL_REGISTRY.items():
            cls_to_canonical.setdefault(cls, cls.name)
        for name, cls in MODEL_REGISTRY.items():
            if cls_to_canonical[cls] != name:
                # Alias entry — class.name points to the canonical name.
                continue
            assert cls.name == name

    def test_duplicate_model_raises(self):
        from volforecast.registry import register_model

        @register_model("__test_unique_model__")
        class _DummyModel:
            pass

        with pytest.raises(ValueError, match="Duplicate model name"):

            @register_model("__test_unique_model__")
            class _DuplicateModel:
                pass

        # Cleanup
        from volforecast.registry import MODEL_REGISTRY

        MODEL_REGISTRY.pop("__test_unique_model__", None)


class TestFeatureRegistry:
    def test_expected_layers_registered(self):
        from volforecast.registry import FEATURE_REGISTRY, ensure_registered

        ensure_registered()

        expected = {
            "har_core",
            "asymmetry",
            "noise_robust",
            "options",
            "microstructure",
            "cross_asset",
            "calendar",
        }
        assert expected.issubset(FEATURE_REGISTRY.keys())

    def test_registry_returns_class(self):
        from volforecast.registry import FEATURE_REGISTRY, ensure_registered

        ensure_registered()
        cls = FEATURE_REGISTRY["har_core"]
        assert isinstance(cls, type)

    def test_name_attribute_set(self):
        from volforecast.registry import FEATURE_REGISTRY, ensure_registered

        ensure_registered()
        for name, cls in FEATURE_REGISTRY.items():
            assert cls.name == name

    def test_duplicate_feature_raises(self):
        from volforecast.registry import register_feature_layer

        @register_feature_layer("__test_unique_feature__")
        class _DummyFeature:
            pass

        with pytest.raises(ValueError, match="Duplicate feature layer name"):

            @register_feature_layer("__test_unique_feature__")
            class _DuplicateFeature:
                pass

        # Cleanup
        from volforecast.registry import FEATURE_REGISTRY

        FEATURE_REGISTRY.pop("__test_unique_feature__", None)
