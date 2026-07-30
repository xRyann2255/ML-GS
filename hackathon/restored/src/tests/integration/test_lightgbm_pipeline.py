"""Integration tests: LightGBM through full Pipeline CV loop.

Validates that LightGBM can be run end-to-end through the Pipeline class
with expanding-window CV, tree_expansion layer, and QLIKE custom objective.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

lgb = pytest.importorskip("lightgbm")

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig  # noqa: E402
from volforecast.pipeline.runner import Pipeline  # noqa: E402


@pytest.fixture
def synthetic_daily_for_lgbm() -> pd.DataFrame:
    """Synthetic daily data with all columns needed for LightGBM layers.

    Includes rv, rq, rs_positive, rs_negative, bpv, jump_variation,
    continuous_variation, rk, noise_gap, open, close — everything that
    har_core + asymmetry + noise_robust + tree_expansion layers need.
    """
    rng = np.random.default_rng(42)
    n = 600
    dates = pd.bdate_range("2020-01-02", periods=n)

    # AR(1) log-RV with mean-reversion
    log_rv = np.zeros(n)
    log_rv[0] = np.log(1e-4)
    for t in range(1, n):
        log_rv[t] = -0.5 + 0.6 * log_rv[t - 1] + 0.3 * rng.standard_normal()

    rv = np.exp(log_rv)
    rq = rv**2 * (3 + rng.uniform(0, 1, n))
    bpv = rv * (0.8 + 0.1 * rng.standard_normal(n))
    bpv = np.clip(bpv, 1e-12, None)

    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    open_price = close * np.exp(rng.normal(0, 0.002, n))

    df = pd.DataFrame(
        {
            "rv": rv,
            "rq": rq,
            "bpv": bpv,
            "rs_positive": np.clip(rv * 0.5 * (1 + 0.1 * rng.standard_normal(n)), 1e-12, None),
            "rs_negative": np.clip(rv * 0.5 * (1 - 0.1 * rng.standard_normal(n)), 1e-12, None),
            "jump_variation": np.clip(rv - bpv * 0.95, 0, None),
            "continuous_variation": np.clip(bpv * 0.95, 1e-12, None),
            "rk": rv * (1 + 0.05 * rng.standard_normal(n)),
            "noise_gap": 0.05 * rng.standard_normal(n),
            "open": open_price,
            "close": close,
        },
        index=dates,
    )
    return df


@pytest.fixture
def lgbm_pipeline_config() -> ExperimentConfig:
    """Config for LightGBM through pipeline with expanding-window CV."""
    return ExperimentConfig(
        name="lgbm_integration_test",
        universe=["SYNTHETIC"],
        date_range=("2020-01-02", "2022-06-01"),
        horizons=[1, 5],
        feature_layers=["har_core", "asymmetry", "noise_robust", "tree_expansion"],
        model=ModelConfig(
            name="lightgbm",
            params={"n_estimators": 50, "num_leaves": 15},
        ),
        cv=CVConfig(method="expanding_window", purge_gap=5, train_size=252, test_size=63),
    )


class TestLightGBMPipelineIntegration:
    """Full end-to-end LightGBM integration through Pipeline."""

    def test_lightgbm_pipeline_runs_end_to_end(
        self, lgbm_pipeline_config, synthetic_daily_for_lgbm
    ):
        """LightGBM completes Pipeline.run() with valid metrics."""
        results = Pipeline(lgbm_pipeline_config).run(synthetic_daily_for_lgbm)

        assert 1 in results
        assert 5 in results
        assert "metrics" in results[1]
        assert "predictions" in results[1]
        assert results[1]["metrics"]["qlike"] > 0
        assert np.isfinite(results[1]["metrics"]["qlike"])
        assert np.isfinite(results[5]["metrics"]["qlike"])

    def test_lightgbm_predictions_finite(self, lgbm_pipeline_config, synthetic_daily_for_lgbm):
        """All LightGBM predictions are finite (no NaN/inf)."""
        results = Pipeline(lgbm_pipeline_config).run(synthetic_daily_for_lgbm)
        for h in [1, 5]:
            preds = results[h]["predictions"]
            assert np.all(np.isfinite(preds.values)), f"h={h} has non-finite predictions"

    def test_lightgbm_has_feature_importance(self, lgbm_pipeline_config, synthetic_daily_for_lgbm):
        """Fitted model exposes feature importance dict."""
        results = Pipeline(lgbm_pipeline_config).run(synthetic_daily_for_lgbm)
        model = results[1]["model"]
        assert model.summary, "summary (gain importance) should be non-empty"
        assert model.feature_importance, "split importance should be non-empty"

    def test_lightgbm_tree_expansion_adds_features(
        self, lgbm_pipeline_config, synthetic_daily_for_lgbm
    ):
        """tree_expansion layer adds _change and _zscore columns beyond base."""
        results = Pipeline(lgbm_pipeline_config).run(synthetic_daily_for_lgbm)
        model = results[1]["model"]
        feature_names = list(model.summary.keys())
        # Should have expansion columns (_change, _zscore)
        change_cols = [f for f in feature_names if f.endswith("_change")]
        zscore_cols = [f for f in feature_names if f.endswith("_zscore")]
        assert len(change_cols) > 0, "No _change features from tree_expansion"
        assert len(zscore_cols) > 0, "No _zscore features from tree_expansion"

    def test_lightgbm_val_fraction_early_stopping(self, synthetic_daily_for_lgbm):
        """val_fraction > 0 enables early stopping without error."""
        cfg = ExperimentConfig(
            name="lgbm_early_stop_test",
            universe=["SYNTHETIC"],
            date_range=("2020-01-02", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core", "asymmetry", "noise_robust", "tree_expansion"],
            model=ModelConfig(
                name="lightgbm",
                params={
                    "n_estimators": 200,
                    "num_leaves": 15,
                    "val_fraction": 0.2,
                    "early_stopping_rounds": 10,
                },
            ),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )
        results = Pipeline(cfg).run(synthetic_daily_for_lgbm)
        assert 1 in results
        assert results[1]["metrics"]["qlike"] > 0

    def test_lightgbm_no_val_fraction_uses_all_data(self, synthetic_daily_for_lgbm):
        """val_fraction=0 (default) trains on full training fold."""
        cfg = ExperimentConfig(
            name="lgbm_no_val_test",
            universe=["SYNTHETIC"],
            date_range=("2020-01-02", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core", "asymmetry", "noise_robust", "tree_expansion"],
            model=ModelConfig(
                name="lightgbm",
                params={"n_estimators": 50, "num_leaves": 15},
            ),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )
        results = Pipeline(cfg).run(synthetic_daily_for_lgbm)
        assert 1 in results
        assert np.isfinite(results[1]["metrics"]["qlike"])
