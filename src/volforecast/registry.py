"""Model and feature layer registries with decorator-based registration."""

from __future__ import annotations

MODEL_REGISTRY: dict[str, type] = {}
FEATURE_REGISTRY: dict[str, type] = {}

_registered = False


def ensure_registered() -> None:
    """Import feature and model modules to trigger decorator-based registration.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _registered  # noqa: PLW0603
    if _registered:
        return
    _registered = True
    import volforecast.features.asymmetry  # noqa: F401
    import volforecast.features.calendar  # noqa: F401
    import volforecast.features.cross_asset  # noqa: F401
    import volforecast.features.cross_asset_momentum  # noqa: F401
    import volforecast.features.har  # noqa: F401
    import volforecast.features.iv_surface  # noqa: F401
    import volforecast.features.long_memory  # noqa: F401
    import volforecast.features.microstructure  # noqa: F401
    import volforecast.features.noise_robust  # noqa: F401
    import volforecast.features.options  # noqa: F401
    import volforecast.features.realized_correlation  # noqa: F401
    import volforecast.features.implied_correlation  # noqa: F401
    import volforecast.features.tree_expansion  # noqa: F401
    import volforecast.models.calibrated  # noqa: F401
    import volforecast.models.ensemble  # noqa: F401
    import volforecast.models.har_family  # noqa: F401
    import volforecast.models.lightgbm  # noqa: F401
    import volforecast.models.lstm  # noqa: F401
    import volforecast.models.xgboost  # noqa: F401
    import volforecast.models.naive  # noqa: F401
    import volforecast.models.blend  # noqa: F401
    import volforecast.models.regime_blend  # noqa: F401
    import volforecast.models.stacking  # noqa: F401
    try:
        import volforecast.models.gnn  # noqa: F401
    except ImportError:
        pass  # torch-geometric not installed — GNN model unavailable


def register_model(name: str):
    """Class decorator that registers a model class in MODEL_REGISTRY.

    Usage::

        @register_model("har")
        class HARModel:
            ...
    """

    def decorator(cls: type) -> type:
        if name in MODEL_REGISTRY:
            raise ValueError(f"Duplicate model name: {name!r}")
        MODEL_REGISTRY[name] = cls
        cls.name = name  # type: ignore[attr-defined]
        return cls

    return decorator


def register_feature_layer(name: str):
    """Class decorator that registers a feature layer in FEATURE_REGISTRY.

    Usage::

        @register_feature_layer("har_core")
        class HARCoreLayer:
            ...
    """

    def decorator(cls: type) -> type:
        if name in FEATURE_REGISTRY:
            raise ValueError(f"Duplicate feature layer name: {name!r}")
        FEATURE_REGISTRY[name] = cls
        cls.name = name  # type: ignore[attr-defined]
        return cls

    return decorator
