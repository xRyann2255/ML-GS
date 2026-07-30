"""Tests for sequential fold seed divergence fix.

Validates that the sequential CV fold path in Pipeline._run_horizon applies
a per-fold seed offset (base_seed + fold_num), matching the parallel path.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def simple_panel():
    """Minimal panel data for 3-fold CV."""
    rng = np.random.default_rng(99)
    n = 300
    dates = pd.bdate_range("2020-01-01", periods=n)
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
        },
        index=dates,
    )
    y = pd.Series(rng.normal(-8, 1, n), index=dates)
    return X, y


class TestSequentialFoldSeedOffset:
    """Each sequential fold must get a unique seed = base_seed + fold_num."""

    def test_normal_branch_seeds_differ_per_fold(self, simple_panel):
        """The else branch (no tuning, no cached_params) should offset seed per fold."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig, TuningConfig
        from volforecast.pipeline.runner import Pipeline, _build_cv_splitter

        X, y = simple_panel

        # Track seeds received by model constructor
        constructed_seeds: list[int] = []

        class FakeModel:
            supports_tuning = False
            family = "fake"

            def __init__(self, **kwargs):
                constructed_seeds.append(kwargs.get("seed"))

            def fit(self, X, y, **kw):
                pass

            def predict(self, X):
                return np.zeros(len(X))

        config = ExperimentConfig(
            name="seed_test",
            universe=["SPY"],
            date_range=("2020-01-01", "2021-06-01"),
            model=ModelConfig(name="fake", params={"seed": 42}),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=50, purge_gap=1),
            tuning=TuningConfig(enabled=False),
            horizons=[1],
            feature_layers=[],
            seed=42,
        )
        pipeline = Pipeline(config)

        # Patch the model registry so our FakeModel is used
        with patch("volforecast.registry.MODEL_REGISTRY", {"fake": FakeModel}):
            cv = _build_cv_splitter(config.cv, purge_gap_override=1)
            pipeline._run_horizon(X, y, cv, FakeModel, h=1)

        # Should have constructed 3+ models with different seeds
        assert len(constructed_seeds) >= 3, f"Expected >=3 folds, got {len(constructed_seeds)}"
        # Each fold should get base_seed + fold_num (1-indexed)
        for i, seed in enumerate(constructed_seeds):
            expected = 42 + (i + 1)
            assert seed == expected, (
                f"Fold {i+1}: expected seed={expected}, got seed={seed}"
            )

    def test_cached_params_branch_seeds_differ(self, simple_panel):
        """When cached_params is used (after tuning), seed still offsets per fold."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig, TuningConfig
        from volforecast.pipeline.runner import Pipeline, _build_cv_splitter

        X, y = simple_panel

        constructed_seeds: list[int] = []
        tune_call_count = [0]

        class FakeModelTunable:
            supports_tuning = True
            family = "fake"

            def __init__(self, **kwargs):
                constructed_seeds.append(kwargs.get("seed"))
                self._params = kwargs

            def fit(self, X, y, **kw):
                pass

            def predict(self, X):
                return np.zeros(len(X))

            def get_params(self):
                return dict(self._params)

            @classmethod
            def tune_and_fit(cls, X, y, tuning_config, base_params=None):
                tune_call_count[0] += 1
                params = dict(base_params) if base_params else {}
                inst = cls(**params)
                inst.fit(X, y)
                return inst

        config = ExperimentConfig(
            name="seed_cached_test",
            universe=["SPY"],
            date_range=("2020-01-01", "2021-06-01"),
            model=ModelConfig(name="fake_tunable", params={"seed": 42}),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=50, purge_gap=1),
            tuning=TuningConfig(enabled=True, n_trials=1, tune_every_n_folds=1, min_train_size=50),
            horizons=[1],
            feature_layers=[],
            seed=42,
        )
        pipeline = Pipeline(config)

        with patch("volforecast.registry.MODEL_REGISTRY", {"fake_tunable": FakeModelTunable}):
            cv = _build_cv_splitter(config.cv, purge_gap_override=1)
            pipeline._run_horizon(X, y, cv, FakeModelTunable, h=1)

        # tune_and_fit is called for fold 1, then cached_params for subsequent folds
        # All constructed seeds should still be unique per fold
        assert len(constructed_seeds) >= 3
        expected_seeds = [42 + (i + 1) for i in range(len(constructed_seeds))]
        assert constructed_seeds == expected_seeds, (
            f"Expected seeds {expected_seeds}, got {constructed_seeds}"
        )
