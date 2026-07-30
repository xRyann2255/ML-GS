"""Tests for registry contract compliance of models and feature layers.

Validates that all registered classes have the required interface methods
(duck-typing contract). No protocol classes needed — the registry + decorator
pattern IS the contract.
"""

from __future__ import annotations


class TestVolModelContract:
    """All registered models must have: name, fit(), predict()."""

    def test_all_registered_models_have_required_interface(self):
        from volforecast.models import MODEL_REGISTRY

        for name, cls in MODEL_REGISTRY.items():
            assert hasattr(cls, "name") or isinstance(getattr(cls, "name", None), property), (
                f"{name} ({cls.__name__}) missing 'name' attribute"
            )
            instance = cls.__new__(cls)
            assert callable(getattr(instance, "fit", None)), (
                f"{name} ({cls.__name__}) missing callable 'fit'"
            )
            assert callable(getattr(instance, "predict", None)), (
                f"{name} ({cls.__name__}) missing callable 'predict'"
            )

    def test_all_registered_models_have_summary(self):
        from volforecast.models import MODEL_REGISTRY

        for name, cls in MODEL_REGISTRY.items():
            # Check class-level definition (property or method) — avoids
            # triggering property code on uninitialized instances.
            has_summary = "summary" in dir(cls) or isinstance(
                getattr(cls, "summary", None), property
            )
            assert has_summary, f"{name} ({cls.__name__}) missing 'summary' property"


class TestFeatureLayerContract:
    """All registered layers must have: name, compute()."""

    def test_all_registered_layers_have_required_interface(self):
        from volforecast.features import FEATURE_REGISTRY

        for name, cls in FEATURE_REGISTRY.items():
            assert hasattr(cls, "name"), f"{name} ({cls.__name__}) missing 'name' attribute"
            instance = cls.__new__(cls)
            assert callable(getattr(instance, "compute", None)), (
                f"{name} ({cls.__name__}) missing callable 'compute'"
            )
