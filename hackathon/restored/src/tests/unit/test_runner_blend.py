"""Tests for the runner's blend dispatch path.

These cover the new branch to be added to ``Pipeline.run_pooled`` for configs
with ``blend is not None``. The blend dispatch path (``_run_pooled_blend``)
does NOT exist yet — these tests are written TDD-style and will FAIL until
the implementation lands in Step 3.

Validates:
1. Dispatch — config with ``blend`` set triggers ``_run_pooled_blend``.
2. Feature union — runner builds features from the union of all sub-model
   feature layers.
3. CV — blend path works with expanding-window cross-validation.
4. OOS predictions — collected with correct shape (MultiIndex of date x symbol).
5. Metrics — QLIKE, MSE, R² are computed on blend output.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.config import (
    BlendConfig,
    BlendSubModelConfig,
    CVConfig,
    ExperimentConfig,
    ModelConfig,
)
from volforecast.models._base import _BaseModel
from volforecast.pipeline.runner import Pipeline
from volforecast.registry import register_model


# ---------------------------------------------------------------------------
# Fake sub-models for blend testing
# ---------------------------------------------------------------------------


@register_model("_fake_blend_tab_a")
class _FakeBlendTabA(_BaseModel):
    """Simple tabular model that predicts a constant offset from mean target."""

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = False
    supports_tuning: bool = False

    def __init__(self, **kwargs) -> None:
        self._mean: float = -10.0

    def fit(self, X, y, **kwargs) -> _FakeBlendTabA:
        self._mean = float(np.mean(y)) if len(y) > 0 else -10.0
        return self

    def predict(self, X, **kwargs) -> np.ndarray:
        n = X.shape[0] if hasattr(X, "shape") else len(X)
        return np.full(n, self._mean, dtype=np.float64)


@register_model("_fake_blend_tab_b")
class _FakeBlendTabB(_BaseModel):
    """Simple tabular model that predicts a noisy mean of target."""

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = False
    supports_tuning: bool = False

    def __init__(self, **kwargs) -> None:
        self._mean: float = -10.0

    def fit(self, X, y, **kwargs) -> _FakeBlendTabB:
        self._mean = float(np.mean(y)) + 0.01 if len(y) > 0 else -10.0
        return self

    def predict(self, X, **kwargs) -> np.ndarray:
        n = X.shape[0] if hasattr(X, "shape") else len(X)
        return np.full(n, self._mean, dtype=np.float64)


# ---------------------------------------------------------------------------
# Synthetic data
# ---------------------------------------------------------------------------


def _make_daily_panel(
    symbols: list[str], n_days: int, seed: int = 0
) -> dict[str, pd.DataFrame]:
    """Per-symbol daily DataFrame with 'rv' column (positive)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n_days)
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        rv = np.exp(-4.0 + 0.3 * rng.standard_normal(n_days))
        out[sym] = pd.DataFrame({"rv": rv}, index=dates)
    return out


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

BLEND_CFG = BlendConfig(
    models=[
        BlendSubModelConfig(name="_fake_blend_tab_a", feature_layers=["har_core"]),
        BlendSubModelConfig(name="_fake_blend_tab_b", feature_layers=["har_core"]),
    ],
    weight_method="inverse_qlike",
    val_fraction=0.20,
    val_purge_gap=5,
)


def _build_blend_config(
    *,
    horizons: list[int] | None = None,
    blend: BlendConfig | None = None,
) -> ExperimentConfig:
    return ExperimentConfig(
        name="test_blend_dispatch",
        universe=["SPY", "AAPL"],
        date_range=("2022-01-03", "2022-12-31"),
        horizons=horizons or [1],
        feature_layers=["har_core"],
        model=ModelConfig(name="blend", params={}),
        cv=CVConfig(
            method="expanding_window",
            train_size=80,
            test_size=20,
            purge_gap=1,
        ),
        blend=blend or BLEND_CFG,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunnerDetectsBlendConfig:
    """Config with blend set should trigger _run_pooled_blend dispatch."""

    def test_runner_detects_blend_config(self):
        panel = _make_daily_panel(["SPY", "AAPL"], n_days=160, seed=42)
        cfg = _build_blend_config()
        pipe = Pipeline(cfg)

        # The blend dispatch method must exist
        assert hasattr(pipe, "_run_pooled_blend"), (
            "Pipeline must have _run_pooled_blend method"
        )

        # Running should succeed (currently it will fail because dispatch
        # doesn't exist or falls through to incompatible tabular path)
        results = pipe.run_pooled(panel)
        assert 1 in results


class TestRunnerBlendBuildsUnionFeatureLayers:
    """Runner should build features from the union of all sub-model layers."""

    def test_runner_blend_builds_union_feature_layers(self):
        blend_cfg = BlendConfig(
            models=[
                BlendSubModelConfig(
                    name="_fake_blend_tab_a", feature_layers=["har_core"]
                ),
                BlendSubModelConfig(
                    name="_fake_blend_tab_b", feature_layers=["har_core"]
                ),
            ],
            weight_method="inverse_qlike",
        )
        cfg = _build_blend_config(blend=blend_cfg)
        panel = _make_daily_panel(["SPY", "AAPL"], n_days=160, seed=42)

        results = Pipeline(cfg).run_pooled(panel)
        # If union feature building works, we get a valid result
        assert 1 in results
        assert "predictions" in results[1]
        assert len(results[1]["predictions"]) > 0


class TestRunnerBlendExpandingWindowCV:
    """Blend path should work with expanding-window CV."""

    def test_runner_blend_expanding_window_cv(self):
        panel = _make_daily_panel(["SPY", "AAPL"], n_days=200, seed=7)
        cfg = _build_blend_config(horizons=[1])

        results = Pipeline(cfg).run_pooled(panel)
        assert 1 in results
        # OOS predictions cover multiple folds (expanding window)
        preds = results[1]["predictions"]
        assert len(preds) > 20, "Expected multiple folds of OOS predictions"
        # All predictions are finite
        assert preds.notna().all()
        assert np.isfinite(preds.values).all()


class TestRunnerBlendCollectsOOSPredictions:
    """OOS predictions are collected with correct shape (MultiIndex)."""

    def test_runner_blend_collects_oos_predictions(self):
        panel = _make_daily_panel(["SPY", "AAPL"], n_days=160, seed=11)
        cfg = _build_blend_config()

        results = Pipeline(cfg).run_pooled(panel)
        assert 1 in results

        preds = results[1]["predictions"]
        actuals = results[1]["actuals"]

        # Predictions and actuals have same length
        assert len(preds) == len(actuals)
        # Both are pd.Series with MultiIndex (date, symbol)
        assert isinstance(preds, pd.Series)
        assert isinstance(actuals, pd.Series)
        assert preds.index.nlevels == 2, "Expected MultiIndex (date, symbol)"
        # Symbols present in predictions
        symbols_in_preds = preds.index.get_level_values(1).unique()
        assert set(symbols_in_preds) == {"SPY", "AAPL"}


class TestRunnerBlendMetricsComputed:
    """QLIKE, MSE, R² metrics are computed on blend output."""

    def test_runner_blend_metrics_computed(self):
        panel = _make_daily_panel(["SPY", "AAPL"], n_days=160, seed=99)
        cfg = _build_blend_config()

        results = Pipeline(cfg).run_pooled(panel)
        assert 1 in results

        metrics = results[1]["metrics"]
        # Required metric keys
        assert "qlike" in metrics
        assert "mse" in metrics
        assert "r_squared" in metrics
        # All metrics are finite
        assert np.isfinite(metrics["qlike"])
        assert np.isfinite(metrics["mse"])
        assert np.isfinite(metrics["r_squared"])
        # QLIKE should be positive (it's a loss)
        assert metrics["qlike"] > 0
