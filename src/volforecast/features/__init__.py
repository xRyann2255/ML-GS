"""Feature engineering layers 0-6 for realized volatility forecasting.

Access registered layers via ``FEATURE_REGISTRY`` dict.
Call ``volforecast.registry.ensure_registered()`` to populate registries.
"""

from volforecast.registry import FEATURE_REGISTRY, register_feature_layer

__all__ = ["FEATURE_REGISTRY", "register_feature_layer"]
