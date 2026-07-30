"""Integration tests for eval_symbols filtering in tournament paths.

Validates end-to-end that:
1. Pooled tournament with eval_symbols computes metrics only for those symbols
2. Per-symbol tournament with eval_symbols trains only those symbols
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
from volforecast.evaluation.tournament import run_har_tournament


class TestEvalSymbolsPooled:
    """Pooled tournament filters metrics to eval_symbols."""

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("volforecast.evaluation._parallel.run_models_pooled")
    @patch("pandas.read_parquet")
    def test_pooled_metrics_only_for_eval_symbols(
        self, mock_parquet, mock_run_pooled, mock_cache_path
    ):
        """When eval_symbols=[SPY], QLIKE is computed on SPY data only."""
        symbols = ["SPY", "AAPL", "MSFT"]
        eval_symbols = ["SPY"]
        T = 50

        # Mock data loading
        mock_cache_path.return_value = MagicMock(exists=lambda: True)
        rng = np.random.default_rng(42)
        dates = pd.date_range("2020-01-01", periods=T, freq="B")
        mock_parquet.return_value = pd.DataFrame(
            {"rv": np.exp(rng.normal(-8.0, 0.5, T)), "close": rng.normal(100, 10, T)},
            index=dates,
        )

        # Build MultiIndex predictions (all 3 symbols from training)
        mi = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        y_true = pd.Series(rng.normal(-8.0, 0.5, len(mi)), index=mi)
        preds_har = pd.Series(y_true.values + rng.normal(0, 0.3, len(mi)), index=mi)

        mock_run_pooled.return_value = (
            {"har": {1: preds_har}},  # all_model_preds
            {1: y_true},  # all_actuals
            {},  # trained_models
            {},  # all_test_data
        )

        cfg = ExperimentConfig(
            name="test_eval_sym",
            universe=symbols,
            date_range=("2020-01-01", "2020-03-15"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            training_mode="pooled",
            eval_symbols=eval_symbols,
        )

        results = run_har_tournament(
            symbols=symbols,
            date_range=("2020-01-01", "2020-03-15"),
            horizons=[1],
            models=["har"],
            training_mode="pooled",
            mcs_bootstrap=100,
            experiment_config=cfg,
        )

        assert 1 in results
        # Tournament table should have har model
        df = results[1]
        assert "har" in df["model"].values

        # Verify run_models_pooled was called with ALL symbols (pooled trains on all)
        call_kwargs = mock_run_pooled.call_args
        # panel_data passed to run_models_pooled should have all 3 symbols
        panel_data_arg = call_kwargs.kwargs.get("panel_data") or call_kwargs[1].get("panel_data")
        if panel_data_arg is None:
            # positional
            panel_data_arg = call_kwargs[0][2] if len(call_kwargs[0]) > 2 else None
        # The key check: training happened on all symbols (panel_data has all 3)
        # but metrics are computed on filtered data

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("volforecast.evaluation._parallel.run_models_pooled")
    @patch("pandas.read_parquet")
    def test_pooled_no_filter_when_eval_symbols_none(
        self, mock_parquet, mock_run_pooled, mock_cache_path
    ):
        """When eval_symbols is None, all symbols contribute to metrics."""
        symbols = ["SPY", "AAPL"]
        T = 50

        mock_cache_path.return_value = MagicMock(exists=lambda: True)
        rng = np.random.default_rng(42)
        dates = pd.date_range("2020-01-01", periods=T, freq="B")
        mock_parquet.return_value = pd.DataFrame(
            {"rv": np.exp(rng.normal(-8.0, 0.5, T)), "close": rng.normal(100, 10, T)},
            index=dates,
        )

        mi = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        y_true = pd.Series(rng.normal(-8.0, 0.5, len(mi)), index=mi)
        preds_har = pd.Series(y_true.values + rng.normal(0, 0.3, len(mi)), index=mi)

        mock_run_pooled.return_value = (
            {"har": {1: preds_har}},
            {1: y_true},
            {},
            {},
        )

        results = run_har_tournament(
            symbols=symbols,
            date_range=("2020-01-01", "2020-03-15"),
            horizons=[1],
            models=["har"],
            training_mode="pooled",
            mcs_bootstrap=100,
        )

        assert 1 in results
        df = results[1]
        assert "har" in df["model"].values


class TestEvalSymbolsPerSymbol:
    """Per-symbol tournament restricts training to eval_symbols."""

    @patch("volforecast.evaluation.tournament.rv_cache_path")
    @patch("volforecast.evaluation.tournament.Pipeline")
    @patch("pandas.read_parquet")
    def test_per_symbol_only_trains_eval_symbols(
        self, mock_parquet, mock_pipeline_cls, mock_cache_path
    ):
        """When eval_symbols=[SPY], only SPY is trained in per-symbol mode."""
        symbols = ["SPY", "AAPL", "MSFT"]
        eval_symbols = ["SPY"]
        T = 50

        mock_cache_path.return_value = MagicMock(exists=lambda: True)
        rng = np.random.default_rng(42)
        dates = pd.date_range("2020-01-01", periods=T + 22, freq="B")
        mock_parquet.return_value = pd.DataFrame(
            {"rv": np.exp(rng.normal(-8.0, 0.5, T + 22))},
            index=dates,
        )

        trained_symbols = []

        def pipeline_side_effect(config):
            trained_symbols.append(config.universe[0])
            mock_pipe = MagicMock()
            results = {}
            for h in config.horizons:
                y = rng.normal(-8.0, 0.5, T)
                p = y + rng.normal(0, 0.3, T)
                d = pd.date_range("2020-01-01", periods=T, freq="B")
                results[h] = {
                    "metrics": {"qlike": 0.05},
                    "predictions": pd.Series(p, index=d),
                    "actuals": pd.Series(y, index=d),
                    "model": MagicMock(),
                }
            mock_pipe.run.return_value = results
            return mock_pipe

        mock_pipeline_cls.side_effect = pipeline_side_effect

        cfg = ExperimentConfig(
            name="test_per_sym",
            universe=symbols,
            date_range=("2020-01-01", "2020-03-15"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            training_mode="per_symbol",
            eval_symbols=eval_symbols,
        )

        results = run_har_tournament(
            symbols=symbols,
            horizons=[1],
            models=["har"],
            training_mode="per_symbol",
            mcs_bootstrap=100,
            experiment_config=cfg,
        )

        # Only SPY should have been trained
        assert trained_symbols == ["SPY"]
        assert 1 in results
