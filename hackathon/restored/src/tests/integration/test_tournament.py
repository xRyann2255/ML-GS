"""Tests for the tournament runner module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

from volforecast.config import CVConfig
from volforecast.evaluation.tournament import (
    HAR_MODELS,
    _feature_layers_for_model,
    display_tournament,
    run_har_tournament,
    run_har_tournament_pooled,
)


class TestFeatureLayerMapping:
    """Tests for _feature_layers_for_model."""

    def test_har_uses_core_only(self):
        assert _feature_layers_for_model("har") == ["har_core"]

    def test_harq_uses_core_only(self):
        assert _feature_layers_for_model("harq") == ["har_core"]

    def test_shar_uses_core_and_asymmetry(self):
        assert _feature_layers_for_model("shar") == ["har_core", "asymmetry"]

    def test_har_j_uses_core_and_asymmetry(self):
        assert _feature_layers_for_model("har_j") == ["har_core", "asymmetry"]

    def test_har_cj_uses_core_and_asymmetry(self):
        assert _feature_layers_for_model("har_cj") == ["har_core", "asymmetry"]

    def test_ridge_uses_core_and_asymmetry(self):
        layers = _feature_layers_for_model("ridge_har")
        assert layers == ["har_core", "asymmetry"]

    def test_lasso_uses_core_and_asymmetry(self):
        layers = _feature_layers_for_model("lasso_har")
        assert layers == ["har_core", "asymmetry"]

    def test_all_har_models_covered(self):
        for m in HAR_MODELS:
            layers = _feature_layers_for_model(m)
            assert "har_core" in layers


class TestRunHarTournament:
    """Integration test with mocked pipeline."""

    def _mock_pipeline_run(self, config):
        """Create a mock Pipeline that returns synthetic results."""
        T = 200
        rng = np.random.default_rng(hash(config.model.name) % 2**31)
        results = {}
        dates = pd.date_range("2020-01-01", periods=T, freq="B")
        for h in config.horizons:
            model_idx = (
                HAR_MODELS.index(config.model.name) if config.model.name in HAR_MODELS else 0
            )
            noise_scale = 0.3 + 0.05 * model_idx
            y_true = rng.normal(-8.0, 0.5, T)
            preds = y_true + rng.normal(0, noise_scale, T)
            results[h] = {
                "metrics": {"qlike": 0.05, "mse": 0.1, "r_squared": 0.5},
                "predictions": pd.Series(preds, index=dates),
                "actuals": pd.Series(y_true, index=dates),
                "model": MagicMock(),
            }
        return results

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("volforecast.evaluation.tournament.Pipeline")
    @patch("pandas.read_parquet")
    def test_tournament_runs_all_models(self, mock_parquet, mock_pipeline_cls, mock_cache_path):
        """Tournament produces tables for all horizons with all models."""
        # Setup mocks
        mock_cache_path.return_value = MagicMock(exists=lambda: True)

        T = 200
        rng = np.random.default_rng(42)
        dates = pd.date_range("2020-01-01", periods=T + 22, freq="B")
        daily_data = pd.DataFrame(
            {
                "rv": np.exp(rng.normal(-8.0, 0.5, T + 22)),
            },
            index=dates,
        )
        mock_parquet.return_value = daily_data

        def pipeline_side_effect(config):
            mock_pipe = MagicMock()
            mock_pipe.run.return_value = self._mock_pipeline_run(config)
            return mock_pipe

        mock_pipeline_cls.side_effect = pipeline_side_effect

        results = run_har_tournament(
            symbols=["SPY", "AAPL"],
            horizons=[1, 5],
            models=["har", "harq", "shar"],
            mcs_bootstrap=200,
        )

        assert 1 in results
        assert 5 in results
        for h in [1, 5]:
            df = results[h]
            assert len(df) == 3
            assert "model" in df.columns
            assert "qlike" in df.columns
            assert "mcs_included" in df.columns
            # Sorted by QLIKE
            assert list(df["qlike"]) == sorted(df["qlike"])

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("volforecast.evaluation.tournament.Pipeline")
    @patch("pandas.read_parquet")
    def test_tournament_baseline_dm_zero(self, mock_parquet, mock_pipeline_cls, mock_cache_path):
        """Baseline model gets dm_stat=0."""
        mock_cache_path.return_value = MagicMock(exists=lambda: True)

        T = 200
        rng = np.random.default_rng(77)
        dates = pd.date_range("2020-01-01", periods=T + 22, freq="B")
        daily_data = pd.DataFrame(
            {
                "rv": np.exp(rng.normal(-8.0, 0.5, T + 22)),
            },
            index=dates,
        )
        mock_parquet.return_value = daily_data

        def pipeline_side_effect(config):
            mock_pipe = MagicMock()
            mock_pipe.run.return_value = self._mock_pipeline_run(config)
            return mock_pipe

        mock_pipeline_cls.side_effect = pipeline_side_effect

        results = run_har_tournament(
            symbols=["SPY"],
            horizons=[1],
            models=["har", "harq"],
            mcs_bootstrap=200,
        )

        df = results[1]
        har_row = df[df["model"] == "har"].iloc[0]
        assert har_row["dm_stat"] == 0.0
        assert har_row["dm_pvalue"] == 1.0


class TestDisplayTournament:
    """Test Rich display function (smoke test)."""

    def test_display_does_not_crash(self, capsys):
        """display_tournament runs without error on valid input."""
        df = pd.DataFrame(
            {
                "model": ["har", "harq"],
                "qlike": [0.05, 0.04],
                "qlike_bps": [0, 200],
                "mse": [0.1, 0.09],
                "r_squared": [0.5, 0.55],
                "mz_alpha": [0.0, 0.0],
                "mz_beta": [1.0, 1.0],
                "mz_f_pvalue": [0.5, 0.5],
                "dm_stat": [0.0, 1.5],
                "dm_pvalue": [1.0, 0.13],
                "mcs_included": [True, True],
                "mcs_pvalue": [1.0, 0.5],
            }
        )
        # Should not raise
        display_tournament({1: df, 5: df})


class TestRunHarTournamentPooled:
    """Tests for the pooled tournament runner."""

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("pandas.read_parquet")
    def test_pooled_tournament_produces_tables(self, mock_parquet, mock_cache_path):
        """Pooled tournament produces tables for all horizons."""
        mock_cache_path.return_value = MagicMock(exists=lambda: True)

        T = 300
        dates = pd.bdate_range("2020-01-02", periods=T)

        def make_data(seed):
            r = np.random.default_rng(seed)
            rv = np.exp(r.normal(-8.0, 0.5, T))
            rq = rv**2 * 3
            return pd.DataFrame({"rv": rv, "rq": rq}, index=dates)

        # Return different data per call to simulate distinct symbols
        call_count = [0]

        def parquet_side_effect(*args, **kwargs):
            call_count[0] += 1
            return make_data(call_count[0])

        mock_parquet.side_effect = parquet_side_effect

        # Use only models that need har_core (no asymmetry features needed)
        results = run_har_tournament_pooled(
            symbols=["SPY", "AAPL", "MSFT"],
            horizons=[1],
            models=["har", "harq", "ar1"],
            mcs_bootstrap=200,
            cv_config=CVConfig(
                method="expanding_window", purge_gap=5, train_size=100, test_size=30
            ),
        )

        assert 1 in results
        df = results[1]
        assert len(df) == 3
        assert "model" in df.columns
        assert "qlike" in df.columns
        assert "mcs_included" in df.columns

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("pandas.read_parquet")
    def test_pooled_requires_at_least_2_symbols(self, mock_parquet, mock_cache_path):
        """Pooled tournament raises if fewer than 2 symbols have data."""

        # Only one symbol has data
        def cache_side_effect(sym):
            m = MagicMock()
            m.exists.return_value = sym == "SPY"
            return m

        mock_cache_path.side_effect = cache_side_effect

        T = 200
        dates = pd.bdate_range("2020-01-02", periods=T)
        mock_parquet.return_value = pd.DataFrame(
            {"rv": np.exp(np.random.default_rng(1).normal(-8, 0.5, T))},
            index=dates,
        )

        with pytest.raises(ValueError, match="at least 2 symbols"):
            run_har_tournament_pooled(
                symbols=["SPY", "AAPL"],
                horizons=[1],
                models=["har", "harq"],
            )


class TestTournamentModelParams:
    """Tests for model params propagation in tournament."""

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("volforecast.evaluation._parallel.Pipeline")
    @patch("volforecast.evaluation.tournament.Pipeline")
    @patch("pandas.read_parquet")
    def test_primary_model_params_inherited(
        self, mock_parquet, mock_pipeline_cls, mock_parallel_pipeline_cls, mock_cache_path
    ):
        """When tournament model matches config.model.name, inherit model.params."""
        mock_cache_path.return_value = MagicMock(exists=lambda: True)

        T = 300
        dates = pd.bdate_range("2020-01-02", periods=T)
        mock_parquet.return_value = pd.DataFrame(
            {"rv": np.exp(np.random.default_rng(42).normal(-8, 0.5, T))},
            index=dates,
        )

        # Capture the configs passed to Pipeline
        created_configs = []

        def pipeline_side_effect(config):
            created_configs.append(config)
            mock_pipe = MagicMock()
            rng = np.random.default_rng(hash(config.model.name) % 2**31)
            results = {}
            for h in config.horizons:
                y = rng.normal(-8, 0.5, T - 22)
                idx = dates[: T - 22]
                results[h] = {
                    "predictions": pd.Series(y, index=idx),
                    "actuals": pd.Series(y + rng.normal(0, 0.1, len(y)), index=idx),
                }
            mock_pipe.run_pooled.return_value = results
            return mock_pipe

        mock_pipeline_cls.side_effect = pipeline_side_effect
        mock_parallel_pipeline_cls.side_effect = pipeline_side_effect

        # Run tournament with primary model params
        primary_params = {"num_leaves": 16, "max_depth": 4, "min_child_samples": 150}

        run_har_tournament(
            symbols=["SPY", "AAPL", "MSFT"],
            horizons=[1],
            models=["har", "lightgbm"],
            training_mode="pooled",
            cv_config=CVConfig(
                method="expanding_window", purge_gap=5, train_size=100, test_size=30
            ),
            mcs_bootstrap=200,
            model_params={"lightgbm": primary_params},
        )

        # Find the config created for lightgbm
        lgbm_configs = [c for c in created_configs if c.model.name == "lightgbm"]
        assert len(lgbm_configs) == 1
        assert lgbm_configs[0].model.params == primary_params

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("volforecast.evaluation._parallel.Pipeline")
    @patch("volforecast.evaluation.tournament.Pipeline")
    @patch("pandas.read_parquet")
    def test_model_configs_resolution(
        self, mock_parquet, mock_pipeline_cls, mock_parallel_pipeline_cls, mock_cache_path
    ):
        """Labels in model_configs resolve to correct registry name + params."""
        mock_cache_path.return_value = MagicMock(exists=lambda: True)

        T = 300
        dates = pd.bdate_range("2020-01-02", periods=T)
        mock_parquet.return_value = pd.DataFrame(
            {"rv": np.exp(np.random.default_rng(42).normal(-8, 0.5, T))},
            index=dates,
        )

        created_configs = []

        def pipeline_side_effect(config):
            created_configs.append(config)
            mock_pipe = MagicMock()
            rng = np.random.default_rng(hash(config.name) % 2**31)
            results = {}
            for h in config.horizons:
                y = rng.normal(-8, 0.5, T - 22)
                idx = dates[: T - 22]
                results[h] = {
                    "predictions": pd.Series(y, index=idx),
                    "actuals": pd.Series(y + rng.normal(0, 0.1, len(y)), index=idx),
                }
            mock_pipe.run_pooled.return_value = results
            return mock_pipe

        mock_pipeline_cls.side_effect = pipeline_side_effect
        mock_parallel_pipeline_cls.side_effect = pipeline_side_effect

        # model_configs maps alias labels -> {name, params}
        model_configs = {
            "lgbm_aggressive": {
                "name": "lightgbm",
                "params": {"num_leaves": 31, "max_depth": 6},
            },
        }

        run_har_tournament(
            symbols=["SPY", "AAPL", "MSFT"],
            horizons=[1],
            models=["har", "lgbm_aggressive"],
            training_mode="pooled",
            cv_config=CVConfig(
                method="expanding_window", purge_gap=5, train_size=100, test_size=30
            ),
            mcs_bootstrap=200,
            model_configs=model_configs,
        )

        # Verify the aliased model resolved to lightgbm with its params
        lgbm_configs = [c for c in created_configs if c.model.name == "lightgbm"]
        assert len(lgbm_configs) == 1
        assert lgbm_configs[0].model.params == {"num_leaves": 31, "max_depth": 6}

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("volforecast.evaluation._parallel.Pipeline")
    @patch("volforecast.evaluation.tournament.Pipeline")
    @patch("pandas.read_parquet")
    def test_two_lightgbm_configs_produce_distinct_results(
        self, mock_parquet, mock_pipeline_cls, mock_parallel_pipeline_cls, mock_cache_path
    ):
        """Two LightGBM entries with different params appear as separate models in results."""
        mock_cache_path.return_value = MagicMock(exists=lambda: True)

        T = 300
        dates = pd.bdate_range("2020-01-02", periods=T)
        mock_parquet.return_value = pd.DataFrame(
            {"rv": np.exp(np.random.default_rng(42).normal(-8, 0.5, T))},
            index=dates,
        )

        call_count = [0]

        def pipeline_side_effect(config):
            call_count[0] += 1
            mock_pipe = MagicMock()
            # Use call_count to produce different predictions per model
            rng = np.random.default_rng(call_count[0])
            results = {}
            for h in config.horizons:
                y = rng.normal(-8, 0.5, T - 22)
                idx = dates[: T - 22]
                results[h] = {
                    "predictions": pd.Series(y, index=idx),
                    "actuals": pd.Series(y + rng.normal(0, 0.1, len(y)), index=idx),
                }
            mock_pipe.run_pooled.return_value = results
            return mock_pipe

        mock_pipeline_cls.side_effect = pipeline_side_effect
        mock_parallel_pipeline_cls.side_effect = pipeline_side_effect

        model_configs = {
            "lgbm_locked": {
                "name": "lightgbm",
                "params": {"num_leaves": 16, "max_depth": 4},
            },
            "lgbm_aggressive": {
                "name": "lightgbm",
                "params": {"num_leaves": 31, "max_depth": 6},
            },
        }

        results = run_har_tournament(
            symbols=["SPY", "AAPL", "MSFT"],
            horizons=[1],
            models=["har", "lgbm_locked", "lgbm_aggressive"],
            training_mode="pooled",
            cv_config=CVConfig(
                method="expanding_window", purge_gap=5, train_size=100, test_size=30
            ),
            mcs_bootstrap=200,
            model_configs=model_configs,
        )

        # Both should appear in the results table
        df = results[1]
        model_names = df["model"].tolist()
        assert "lgbm_locked" in model_names
        assert "lgbm_aggressive" in model_names


class TestCrossAssetContextWiring:
    """Tests that _build_tournament_context loads cross-asset data when needed."""

    def test_context_includes_cross_asset_keys(self):
        """When feature_layers includes 'cross_asset', context contains the expected keys."""
        from volforecast.evaluation.tournament import _build_tournament_context

        # Mock load_cross_asset_context to return synthetic data
        fake_context = {
            "treasury": pd.DataFrame({"10y": [4.5], "2y": [4.0]}),
            "fx": pd.DataFrame({"USDJPY": [150.0]}),
            "commodity": pd.DataFrame({"CL": [75.0]}),
            "credit": pd.DataFrame({"cdx_iv": [60.0]}),
            "vix": pd.DataFrame({"vix": [20.0]}),
        }
        with patch(
            "volforecast.evaluation.tournament.load_cross_asset_context",
            return_value=fake_context,
        ):
            context = _build_tournament_context(
                ["har"], feature_layers=["iv_surface", "har_core", "cross_asset"]
            )

        assert context is not None
        assert "treasury" in context
        assert "fx" in context
        assert "commodity" in context
        assert "vix" in context

    def test_context_none_without_cross_asset_layer(self):
        """Without cross_asset in feature_layers, context is None (iv_surface path)."""
        from volforecast.evaluation.tournament import _build_tournament_context

        context = _build_tournament_context(
            ["har"], feature_layers=["iv_surface", "har_core", "options"]
        )
        # iv_surface present means no legacy options context needed
        assert context is None
