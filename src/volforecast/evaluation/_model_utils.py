"""Model resolution utilities for tournament evaluation.

Shared between tournament.py (orchestrate) and _parallel.py to avoid
circular imports. Contains:
- Model name constants (HAR_MODELS, NAIVE_MODELS, ML_MODELS, ALL_MODELS)
- resolve_model: resolves label -> (registry_name, display_label, params)
- feature_layers_for_model: returns required feature layers for a model
"""

from __future__ import annotations

from typing import Any

HAR_MODELS = ["har", "harq", "shar", "har_j", "har_cj", "ridge_har", "lasso_har"]

NAIVE_MODELS = [
    "random_walk",
    "historical_mean",
    "rolling_mean",
    "median_rv",
    "ewma",
    "ar1",
    "vix_implied",
]

ML_MODELS = ["lightgbm"]

ALL_MODELS = NAIVE_MODELS + HAR_MODELS + ML_MODELS


def feature_layers_for_model(model_name: str) -> list[str]:
    """Return required feature layers for a given model (from class attribute)."""
    from volforecast.models import MODEL_REGISTRY
    from volforecast.registry import ensure_registered

    ensure_registered()
    model_cls = MODEL_REGISTRY.get(model_name)
    if model_cls is not None:
        return getattr(model_cls, "REQUIRED_LAYERS", ["har_core"])
    return ["har_core"]


def resolve_model(
    label: str,
    model_params: dict[str, dict] | None = None,
    model_configs: dict[str, dict] | None = None,
) -> tuple[str, str, dict]:
    """Resolve a tournament model label to (registry_name, display_label, params).

    Resolution order:
    1. label is in model_configs -> use entry's 'name' + 'params'
    2. label is in model_params -> use label as registry name + those params
    3. Otherwise -> (label, label, {})
    """
    if model_configs and label in model_configs:
        entry = model_configs[label]
        return entry["name"], label, entry.get("params", {})
    if model_params and label in model_params:
        return label, label, model_params[label]
    return label, label, {}
