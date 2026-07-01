"""Tests for model family/description ClassVars and thin accessors."""

from __future__ import annotations

from volforecast.models._base import _BaseModel
from volforecast.registry import MODEL_REGISTRY, ensure_registered


def setup_module():
    ensure_registered()


def test_base_model_defaults():
    assert _BaseModel.family == "unknown"
    assert _BaseModel.description == ""


def test_har_family_attr():
    cls = MODEL_REGISTRY["har"]
    assert cls.family == "har"


def test_lightgbm_family_and_accessor():
    cls = MODEL_REGISTRY["lightgbm"]
    assert cls.family == "lightgbm"
    assert hasattr(cls, "get_feature_importance")


def test_lstm_family_and_accessor():
    cls = MODEL_REGISTRY["lstm"]
    assert cls.family == "lstm"
    assert hasattr(cls, "get_arch_summary")
