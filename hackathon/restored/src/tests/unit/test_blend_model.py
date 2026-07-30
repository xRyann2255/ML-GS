"""Tests for models/blend.py — PredictionBlendModel.

TDD: These tests are written BEFORE the implementation exists.
They will fail at import/collection time until blend.py is created.

Validates:
1. Registration in MODEL_REGISTRY as "blend"
2. fit() trains all sub-models (tabular and sequence)
3. predict() returns correct shape
4. Weight calibration: fixed, inverse_qlike, ridge_meta, regime_dependent
5. Fallback to equal weights when holdout is too small
6. summary() includes per-model weights and QLIKE scores
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.config import BlendConfig, BlendSubModelConfig
from volforecast.models._base import _BaseModel
from volforecast.models.blend import PredictionBlendModel
from volforecast.registry import MODEL_REGISTRY


# ---------------------------------------------------------------------------
# Mock sub-models — NOT registered in MODEL_REGISTRY
# ---------------------------------------------------------------------------

class MockTabularModel(_BaseModel):
    """Simple tabular model that predicts mean(y) + deterministic noise."""

    REQUIRED_LAYERS: list[str] = ["har_core"]
    family = "mock_tabular"

    def __init__(self, **kwargs):
        self.fitted = False
        self._mean = 0.0
        self._fit_calls: list[tuple] = []

    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> MockTabularModel:
        self.fitted = True
        self._mean = float(y.mean())
        self._fit_calls.append(("fit", len(X)))
        return self

    def predict(self, X: pd.DataFrame, **kwargs) -> np.ndarray:
        rng = np.random.RandomState(42)
        return np.full(len(X), self._mean) + rng.normal(0, 0.01, len(X))

    @property
    def summary(self) -> dict[str, float]:
        return {"mean": self._mean}


class MockSequenceModel(_BaseModel):
    """Simple sequence model that returns a constant prediction."""

    REQUIRED_LAYERS: list[str] = []
    requires_sequences = True
    family = "mock_sequence"

    def __init__(self, **kwargs):
        self.fitted = False
        self._fit_calls: list[tuple] = []

    def fit(self, X, y: pd.Series, *, sequence_data=None, **kwargs) -> MockSequenceModel:
        self.fitted = True
        self._fit_calls.append(("fit", len(y)))
        return self

    def predict(self, X, *, sequence_data=None, **kwargs) -> np.ndarray:
        n = len(X) if hasattr(X, "__len__") else sequence_data["length"]
        return np.full(n, -3.5)

    @property
    def summary(self) -> dict[str, float]:
        return {"constant": -3.5}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_synthetic_data(n: int = 200, seed: int = 0):
    """Create synthetic log-RV features and target."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-4.0, 0.5, n),
            "log_rv_w": rng.normal(-4.0, 0.3, n),
            "log_rv_m": rng.normal(-4.0, 0.2, n),
        },
        index=dates,
    )
    y = pd.Series(rng.normal(-4.0, 0.5, n), index=dates, name="log_rv_1d")
    return X, y


def _make_blend_config(
    weight_method: str = "inverse_qlike",
    fixed_weights: list[float] | None = None,
    regime_indicator: str | None = None,
    regime_threshold: float | None = None,
    val_fraction: float = 0.20,
) -> BlendConfig:
    """Build a BlendConfig with two mock sub-model entries."""
    models = [
        BlendSubModelConfig(name="mock_a", feature_layers=["har_core"]),
        BlendSubModelConfig(name="mock_b", feature_layers=["har_core"]),
    ]
    return BlendConfig(
        models=models,
        weight_method=weight_method,
        fixed_weights=fixed_weights,
        regime_indicator=regime_indicator,
        regime_threshold=regime_threshold,
        val_fraction=val_fraction,
    )


def _build_blend(blend_config: BlendConfig, sub_models=None) -> PredictionBlendModel:
    """Instantiate PredictionBlendModel with mock sub-models injected."""
    blend = PredictionBlendModel(blend_config=blend_config)
    # Inject mock sub-model instances so we don't rely on MODEL_REGISTRY lookups
    if sub_models is not None:
        blend._sub_models = sub_models
    else:
        blend._sub_models = [MockTabularModel(), MockTabularModel()]
    return blend


# ---------------------------------------------------------------------------
# TestPredictionBlendModel
# ---------------------------------------------------------------------------


class TestPredictionBlendModel:
    """Core behavior tests for PredictionBlendModel."""

    def test_registered_as_blend(self):
        """MODEL_REGISTRY contains 'blend' after importing blend.py."""
        assert "blend" in MODEL_REGISTRY
        assert MODEL_REGISTRY["blend"] is PredictionBlendModel

    def test_fit_trains_all_sub_models(self):
        """fit() calls fit on every sub-model."""
        X, y = _make_synthetic_data(n=200)
        cfg = _make_blend_config(weight_method="inverse_qlike")
        m1, m2 = MockTabularModel(), MockTabularModel()
        blend = _build_blend(cfg, sub_models=[m1, m2])

        blend.fit(X, y)

        assert m1.fitted, "sub-model 1 was not fitted"
        assert m2.fitted, "sub-model 2 was not fitted"

    def test_predict_returns_correct_shape(self):
        """predict() returns array with same length as input."""
        X, y = _make_synthetic_data(n=200)
        cfg = _make_blend_config(weight_method="inverse_qlike")
        blend = _build_blend(cfg)
        blend.fit(X, y)

        preds = blend.predict(X)

        assert isinstance(preds, np.ndarray)
        assert preds.shape == (len(X),)

    def test_fixed_weights(self):
        """With weight_method='fixed', predictions are the specified weighted average."""
        X, y = _make_synthetic_data(n=200)
        cfg = _make_blend_config(
            weight_method="fixed",
            fixed_weights=[0.7, 0.3],
        )
        m1, m2 = MockTabularModel(), MockTabularModel()
        blend = _build_blend(cfg, sub_models=[m1, m2])
        blend.fit(X, y)

        preds = blend.predict(X)
        p1 = m1.predict(X)
        p2 = m2.predict(X)
        expected = 0.7 * p1 + 0.3 * p2

        np.testing.assert_allclose(preds, expected, atol=1e-10)

    def test_inverse_qlike_better_model_gets_higher_weight(self):
        """The sub-model with lower QLIKE gets more weight under inverse_qlike."""
        X, y = _make_synthetic_data(n=200, seed=0)
        cfg = _make_blend_config(weight_method="inverse_qlike")

        # m_good predicts close to y; m_bad predicts a constant far from y
        m_good = MockTabularModel()
        m_bad = MockTabularModel()

        # Override predict so m_good is clearly better
        m_good.predict = lambda X, **kw: y.values + np.random.RandomState(1).normal(0, 0.01, len(X))
        m_bad.predict = lambda X, **kw: np.full(len(X), y.mean() + 2.0)

        blend = _build_blend(cfg, sub_models=[m_good, m_bad])
        blend.fit(X, y)

        weights = blend._weights
        assert weights[0] > weights[1], (
            f"Better model should get higher weight: {weights}"
        )

    def test_ridge_meta_learner(self):
        """Ridge method produces valid predictions without error."""
        X, y = _make_synthetic_data(n=200)
        cfg = _make_blend_config(weight_method="ridge_meta")
        blend = _build_blend(cfg)
        blend.fit(X, y)

        preds = blend.predict(X)
        assert preds.shape == (len(X),)
        assert np.all(np.isfinite(preds))

    def test_regime_dependent_weights(self):
        """Regime-dependent weighting produces different weights per regime."""
        X, y = _make_synthetic_data(n=300, seed=7)
        # Add a regime indicator column
        X["vol_regime"] = np.where(
            np.abs(X["log_rv_d"]) > X["log_rv_d"].quantile(0.75), 1.0, 0.0
        )
        cfg = _make_blend_config(
            weight_method="regime_dependent",
            regime_indicator="vol_regime",
            regime_threshold=0.5,
        )
        blend = _build_blend(cfg)
        blend.fit(X, y)

        # Should store separate weight vectors for high/low regime
        assert hasattr(blend, "_regime_weights")
        assert "high" in blend._regime_weights
        assert "low" in blend._regime_weights
        # Weights can differ between regimes
        w_high = blend._regime_weights["high"]
        w_low = blend._regime_weights["low"]
        assert len(w_high) == 2
        assert len(w_low) == 2

    def test_fallback_equal_weights_small_holdout(self):
        """When data is too small for a holdout split, fall back to equal weights."""
        X, y = _make_synthetic_data(n=30)  # Too small for 20% holdout + purge
        cfg = _make_blend_config(weight_method="inverse_qlike", val_fraction=0.20)
        blend = _build_blend(cfg)
        blend.fit(X, y)

        weights = blend._weights
        np.testing.assert_allclose(weights, [0.5, 0.5], atol=1e-10)

    def test_summary_includes_weights(self):
        """summary dict contains per-model weight info."""
        X, y = _make_synthetic_data(n=200)
        cfg = _make_blend_config(weight_method="inverse_qlike")
        blend = _build_blend(cfg)
        blend.fit(X, y)

        s = blend.summary
        assert isinstance(s, dict)
        assert "weights" in s or any("weight" in k for k in s)


# ---------------------------------------------------------------------------
# TestWeightCalibration
# ---------------------------------------------------------------------------


class TestWeightCalibration:
    """Focused tests on weight computation correctness."""

    def test_inverse_qlike_weights_sum_to_one(self):
        """Weights from inverse_qlike method sum to 1.0."""
        X, y = _make_synthetic_data(n=200)
        cfg = _make_blend_config(weight_method="inverse_qlike")
        blend = _build_blend(cfg)
        blend.fit(X, y)

        weights = blend._weights
        assert len(weights) == 2
        assert abs(sum(weights) - 1.0) < 1e-10

    def test_fixed_weights_preserved(self):
        """Fixed weights appear exactly as specified in the config."""
        X, y = _make_synthetic_data(n=200)
        cfg = _make_blend_config(
            weight_method="fixed",
            fixed_weights=[0.6, 0.4],
        )
        blend = _build_blend(cfg)
        blend.fit(X, y)

        np.testing.assert_allclose(blend._weights, [0.6, 0.4])

    def test_ridge_learns_intercept(self):
        """Ridge meta-model stores an intercept term."""
        X, y = _make_synthetic_data(n=200)
        cfg = _make_blend_config(weight_method="ridge_meta")
        blend = _build_blend(cfg)
        blend.fit(X, y)

        assert hasattr(blend, "_meta_intercept") or hasattr(blend, "_ridge_model")
        # The intercept should be a finite number
        if hasattr(blend, "_meta_intercept"):
            assert np.isfinite(blend._meta_intercept)
        else:
            assert np.isfinite(blend._ridge_model.intercept_)
