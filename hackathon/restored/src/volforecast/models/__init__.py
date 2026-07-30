"""Volatility forecasting models: HAR baselines, LightGBM, LSTM, ensemble.

Access registered models via ``MODEL_REGISTRY`` dict.
Call ``volforecast.registry.ensure_registered()`` to populate registries.
"""

from volforecast.registry import MODEL_REGISTRY, register_model

__all__ = ["MODEL_REGISTRY", "register_model"]
