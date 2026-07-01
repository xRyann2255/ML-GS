"""Cross-module integration tests.

These tests verify that module boundaries communicate correctly:
- Ingest output schema matches what train expects
- Registry cold-start populates all models/layers
- External feature layers (options, cross_asset) work inside Pipeline.run
- Multi-symbol panel flows through the pipeline
- Persistence round-trip preserves model and metric fidelity

All tests use synthetic data and mocks — no network, fast execution.
Run with: pytest -m integration
Exclude with: pytest -m "not integration"
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_rv_panel() -> pd.DataFrame:
    """Synthetic RV panel matching compute_daily_rv_from_ticks output schema.

    This is the exact column set that ingest writes to parquet.
    """
    rng = np.random.default_rng(42)
    n = 300
    dates = pd.bdate_range("2021-01-04", periods=n)

    rv = np.exp(-9.0 + 0.5 * rng.standard_normal(n))
    rq = rv**2 * (3 + rng.uniform(0, 1, n))
    bpv = rv * (0.8 + 0.1 * np.abs(rng.standard_normal(n)))
    bpv = np.clip(bpv, 1e-12, None)

    return pd.DataFrame(
        {
            "rv": rv,
            "log_rv": np.log(rv),
            "rq": rq,
            "rtq": rq * 0.8,
            "bpv": bpv,
            "rs_positive": rv * 0.5 * (1 + 0.1 * np.abs(rng.standard_normal(n))),
            "rs_negative": rv * 0.5 * (1 + 0.1 * np.abs(rng.standard_normal(n))),
            "jump_stat": rng.standard_normal(n),
            "jump_indicator": rng.integers(0, 2, n),
            "continuous_variation": bpv * 0.95,
            "jump_variation": np.clip(rv - bpv * 0.95, 0, None),
            "j_positive": np.abs(rng.standard_normal(n)) * 1e-5,
            "j_negative": np.abs(rng.standard_normal(n)) * 1e-5,
            "realized_skewness": rng.standard_normal(n) * 0.5,
            "realized_kurtosis": 3.0 + rng.exponential(1.0, n),
            "rk": rv * (1 + 0.05 * rng.standard_normal(n)),
            "noise_gap": 0.05 * rng.standard_normal(n),
            "n_ticks": rng.integers(3000, 8000, n),
            "n_bars": np.full(n, 78),
            # OHLCV enrichment columns (added by enrich_panel_with_ohlcv)
            "open": 450.0 + np.cumsum(rng.standard_normal(n) * 2),
            "close": 450.0 + np.cumsum(rng.standard_normal(n) * 2),
            "symbol": "SPY",
        },
        index=dates,
    )


@pytest.fixture
def synthetic_rv_panel_aapl(synthetic_rv_panel) -> pd.DataFrame:
    """Second symbol panel with same schema for multi-symbol tests."""
    panel = synthetic_rv_panel.copy()
    panel["symbol"] = "AAPL"
    # Slightly different RV for differentiation
    panel["rv"] = panel["rv"] * 1.2
    panel["log_rv"] = np.log(panel["rv"])
    return panel


# ---------------------------------------------------------------------------
# Test 1: Schema contract — ingest output matches train input
# ---------------------------------------------------------------------------


class TestSchemaContract:
    """Verify that the parquet schema produced by ingest is consumable by train."""

    def test_ingest_schema_loadable_by_train(self, synthetic_rv_panel, tmp_path):
        """Write a panel to parquet (as ingest does), load it (as train does),
        and verify Pipeline.run accepts it without error."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
        from volforecast.pipeline.runner import Pipeline

        # Write panel as ingest would
        cache_path = tmp_path / "SPY_rv_daily.parquet"
        synthetic_rv_panel.to_parquet(cache_path)

        # Load panel as train does: pd.read_parquet
        panel = pd.read_parquet(cache_path)

        # Verify the panel is accepted by Pipeline.run
        cfg = ExperimentConfig(
            name="schema_test",
            universe=["SPY"],
            date_range=("2021-01-04", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )
        results = Pipeline(cfg).run(panel)
        assert 1 in results
        assert np.isfinite(results[1]["metrics"]["qlike"])

    def test_schema_columns_present(self, synthetic_rv_panel):
        """The RV panel has all columns expected by har_core and asymmetry layers."""

        # These are the columns compute_daily_rv_from_ticks produces
        expected_rv_cols = {
            "rv",
            "log_rv",
            "rq",
            "rtq",
            "bpv",
            "rs_positive",
            "rs_negative",
            "jump_stat",
            "jump_indicator",
            "continuous_variation",
            "jump_variation",
            "j_positive",
            "j_negative",
            "realized_skewness",
            "realized_kurtosis",
            "rk",
            "noise_gap",
            "n_ticks",
            "n_bars",
        }
        assert expected_rv_cols.issubset(set(synthetic_rv_panel.columns))

    def test_schema_dtypes_numeric(self, synthetic_rv_panel):
        """All RV measurement columns are numeric (not object/string)."""
        numeric_cols = [
            "rv",
            "rq",
            "bpv",
            "rs_positive",
            "rs_negative",
            "rk",
            "noise_gap",
            "continuous_variation",
            "jump_variation",
        ]
        for col in numeric_cols:
            assert pd.api.types.is_numeric_dtype(synthetic_rv_panel[col]), (
                f"Column {col} is not numeric: {synthetic_rv_panel[col].dtype}"
            )


# ---------------------------------------------------------------------------
# Test 2: Registry cold-start
# ---------------------------------------------------------------------------


class TestRegistryColdStart:
    """Verify ensure_registered() populates all expected models and layers."""

    def test_all_har_models_registered(self):
        """After ensure_registered(), all 7 HAR-family models are present."""
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        expected_models = {"har", "harq", "shar", "har_j", "har_cj", "ridge_har", "lasso_har"}
        registered = set(MODEL_REGISTRY.keys())
        assert expected_models.issubset(registered), (
            f"Missing models: {expected_models - registered}"
        )

    def test_all_feature_layers_registered(self):
        """After ensure_registered(), core feature layers are present."""
        from volforecast.registry import FEATURE_REGISTRY, ensure_registered

        ensure_registered()
        expected_layers = {"har_core", "asymmetry", "options", "cross_asset"}
        registered = set(FEATURE_REGISTRY.keys())
        assert expected_layers.issubset(registered), (
            f"Missing layers: {expected_layers - registered}"
        )

    @pytest.mark.slow
    def test_registry_subprocess_cold_start(self):
        """In a fresh subprocess, ensure_registered populates everything."""
        code = (
            "from volforecast.registry import ensure_registered, MODEL_REGISTRY, FEATURE_REGISTRY; "
            "ensure_registered(); "
            "models = sorted(MODEL_REGISTRY.keys()); "
            "layers = sorted(FEATURE_REGISTRY.keys()); "
            "print(f'models={models}'); "
            "print(f'layers={layers}'); "
            "assert len(models) >= 7, f'Only {len(models)} models'; "
            "assert len(layers) >= 4, f'Only {len(layers)} layers'"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0, (
            f"Registry cold-start failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Test 3: Pipeline + external feature layers (options, cross_asset)
# ---------------------------------------------------------------------------


class TestExternalLayersInPipeline:
    """Verify options and cross_asset layers work inside Pipeline.run via context."""

    def test_options_layer_in_pipeline(self, synthetic_rv_panel):
        """OptionsLayer integrates with Pipeline.run when context has iv_surface."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
        from volforecast.pipeline.runner import Pipeline

        rng = np.random.default_rng(99)
        n = len(synthetic_rv_panel)

        # Build IV surface context matching OptionsLayer expectations
        iv_surface = pd.DataFrame(
            {
                "atm_iv_1m": 20.0 + rng.standard_normal(n) * 3,
                "atm_iv_3m": 22.0 + rng.standard_normal(n) * 2,
                "skew_1m": -2.0 + rng.standard_normal(n) * 0.5,
            },
            index=synthetic_rv_panel.index,
        )

        cfg = ExperimentConfig(
            name="options_integration",
            universe=["SPY"],
            date_range=("2021-01-04", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core", "options"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )

        results = Pipeline(cfg).run(
            synthetic_rv_panel,
            context={"iv_surface": iv_surface},
        )
        assert 1 in results
        assert np.isfinite(results[1]["metrics"]["qlike"])
        assert results[1]["metrics"]["qlike"] > 0

    def test_cross_asset_layer_in_pipeline(self, synthetic_rv_panel):
        """CrossAssetLayer integrates with Pipeline.run when context has treasury/vix."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
        from volforecast.pipeline.runner import Pipeline

        rng = np.random.default_rng(77)
        n = len(synthetic_rv_panel)
        idx = synthetic_rv_panel.index

        # Build cross-asset context
        treasury = pd.DataFrame(
            {"2y": 4.0 + rng.standard_normal(n) * 0.2, "10y": 4.5 + rng.standard_normal(n) * 0.3},
            index=idx,
        )
        fx = pd.DataFrame({"USDJPY": 150.0 + np.cumsum(rng.standard_normal(n) * 0.3)}, index=idx)
        commodity = pd.DataFrame({"CL": 75.0 + np.cumsum(rng.standard_normal(n) * 0.5)}, index=idx)
        vix = pd.Series(20.0 + rng.standard_normal(n) * 3, index=idx, name="vix").clip(lower=9)

        cfg = ExperimentConfig(
            name="cross_asset_integration",
            universe=["SPY"],
            date_range=("2021-01-04", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core", "cross_asset"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )

        results = Pipeline(cfg).run(
            synthetic_rv_panel,
            context={"treasury": treasury, "fx": fx, "commodity": commodity, "vix": vix},
        )
        assert 1 in results
        assert np.isfinite(results[1]["metrics"]["qlike"])


# ---------------------------------------------------------------------------
# Test 4: Multi-symbol panel
# ---------------------------------------------------------------------------


class TestMultiSymbolPipeline:
    """Verify pipeline handles multiple symbols without cross-contamination."""

    def test_two_symbols_produce_independent_results(
        self, synthetic_rv_panel, synthetic_rv_panel_aapl
    ):
        """Pipeline.run on two different symbols produces distinct metrics."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
        from volforecast.pipeline.runner import Pipeline

        cfg = ExperimentConfig(
            name="multi_symbol_test",
            universe=["SPY", "AAPL"],
            date_range=("2021-01-04", "2022-06-01"),
            horizons=[1, 5],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )

        pipeline = Pipeline(cfg)
        results_spy = pipeline.run(synthetic_rv_panel)
        results_aapl = pipeline.run(synthetic_rv_panel_aapl)

        # Both produce valid results for both horizons
        for h in [1, 5]:
            assert h in results_spy
            assert h in results_aapl
            assert np.isfinite(results_spy[h]["metrics"]["qlike"])
            assert np.isfinite(results_aapl[h]["metrics"]["qlike"])

        # Results should differ (different RV series)
        assert results_spy[1]["metrics"]["qlike"] != results_aapl[1]["metrics"]["qlike"]

    def test_multi_symbol_persistence_isolated(
        self, synthetic_rv_panel, synthetic_rv_panel_aapl, tmp_path
    ):
        """Persisting results for two symbols keeps them separate on disk."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
        from volforecast.pipeline.runner import Pipeline
        from volforecast.utils.persistence import (
            load_all_metrics,
            save_experiment_results,
        )

        cfg = ExperimentConfig(
            name="multi_sym_persist",
            universe=["SPY", "AAPL"],
            date_range=("2021-01-04", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )

        pipeline = Pipeline(cfg)
        results_spy = pipeline.run(synthetic_rv_panel)
        results_aapl = pipeline.run(synthetic_rv_panel_aapl)

        # Patch models_dir to tmp_path
        with patch("volforecast.utils.persistence.models_dir", return_value=tmp_path):
            save_experiment_results(results_spy, cfg, "SPY")
            save_experiment_results(results_aapl, cfg, "AAPL")

            metrics = load_all_metrics(cfg)

        assert "SPY" in metrics
        assert "AAPL" in metrics
        assert metrics["SPY"]["1"]["qlike"] != metrics["AAPL"]["1"]["qlike"]


# ---------------------------------------------------------------------------
# Test 5: Persistence round-trip
# ---------------------------------------------------------------------------


class TestPersistenceRoundTrip:
    """Verify train output survives save/load and metrics remain consistent."""

    def test_predictions_survive_round_trip(self, synthetic_rv_panel, tmp_path):
        """Pipeline predictions saved by train can be loaded and match."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
        from volforecast.pipeline.runner import Pipeline
        from volforecast.utils.persistence import (
            load_predictions,
            save_experiment_results,
        )

        cfg = ExperimentConfig(
            name="roundtrip_test",
            universe=["SPY"],
            date_range=("2021-01-04", "2022-06-01"),
            horizons=[1, 5],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )

        results = Pipeline(cfg).run(synthetic_rv_panel)

        with patch("volforecast.utils.persistence.models_dir", return_value=tmp_path):
            save_experiment_results(results, cfg, "SPY")

            for h in [1, 5]:
                loaded = load_predictions(cfg, "SPY", h)
                original_preds = results[h]["predictions"]

                # Values match to float precision
                valid = original_preds.notna()
                np.testing.assert_allclose(
                    loaded["prediction"].values,
                    original_preds[valid].values,
                    rtol=1e-10,
                )

    def test_metrics_survive_round_trip(self, synthetic_rv_panel, tmp_path):
        """Metrics saved to JSON can be loaded and match original."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
        from volforecast.pipeline.runner import Pipeline
        from volforecast.utils.persistence import (
            load_all_metrics,
            save_experiment_results,
        )

        cfg = ExperimentConfig(
            name="metrics_roundtrip",
            universe=["SPY"],
            date_range=("2021-01-04", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )

        results = Pipeline(cfg).run(synthetic_rv_panel)
        original_qlike = results[1]["metrics"]["qlike"]
        original_mse = results[1]["metrics"]["mse"]

        with patch("volforecast.utils.persistence.models_dir", return_value=tmp_path):
            save_experiment_results(results, cfg, "SPY")
            loaded = load_all_metrics(cfg)

        assert abs(loaded["SPY"]["1"]["qlike"] - original_qlike) < 1e-10
        assert abs(loaded["SPY"]["1"]["mse"] - original_mse) < 1e-10

    def test_config_snapshot_written(self, synthetic_rv_panel, tmp_path):
        """save_experiment_results writes a config.yaml snapshot."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
        from volforecast.pipeline.runner import Pipeline
        from volforecast.utils.persistence import save_experiment_results

        cfg = ExperimentConfig(
            name="config_snapshot_test",
            universe=["SPY"],
            date_range=("2021-01-04", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )

        results = Pipeline(cfg).run(synthetic_rv_panel)

        with patch("volforecast.utils.persistence.models_dir", return_value=tmp_path):
            save_experiment_results(results, cfg, "SPY")

        config_path = tmp_path / "config_snapshot_test" / "config.yaml"
        assert config_path.exists()
        # Verify it's valid YAML that can be re-loaded
        reloaded = ExperimentConfig.from_yaml(config_path)
        assert reloaded.name == "config_snapshot_test"
        assert reloaded.model.name == "har"
