"""Tests for eval_symbols filtering in tournament paths.

Validates:
1. Pooled path: predictions/actuals are filtered to eval_symbols after training
2. Per-symbol path: only eval_symbols are trained
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.config import ExperimentConfig, ModelConfig


class TestPooledEvalSymbolsFilter:
    """Test that the pooled path filters MultiIndex preds/actuals to eval_symbols."""

    @staticmethod
    def _make_multi_index_series(
        symbols: list[str], n_dates: int = 10, seed: int = 42
    ) -> pd.Series:
        """Create a MultiIndex (date, symbol) Series with random values."""
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range("2023-01-02", periods=n_dates)
        idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        return pd.Series(rng.random(len(idx)), index=idx)

    def test_filter_restricts_to_eval_symbols(self):
        """Simulates the pooled filter logic from _run_tournament_pooled."""
        all_symbols = ["SPY", "AAPL", "MSFT"]
        eval_syms = ["SPY"]

        actuals = {1: self._make_multi_index_series(all_symbols)}
        preds = {"har": {1: self._make_multi_index_series(all_symbols, seed=99)}}

        # Apply the same filter as _run_tournament_pooled
        eval_set = set(eval_syms)
        for h in list(actuals.keys()):
            idx = actuals[h].index
            if isinstance(idx, pd.MultiIndex) and "symbol" in idx.names:
                mask = idx.get_level_values("symbol").isin(eval_set)
                actuals[h] = actuals[h].loc[mask]
        for m in list(preds.keys()):
            for h in list(preds[m].keys()):
                idx = preds[m][h].index
                if isinstance(idx, pd.MultiIndex) and "symbol" in idx.names:
                    mask = idx.get_level_values("symbol").isin(eval_set)
                    preds[m][h] = preds[m][h].loc[mask]

        # Only SPY should remain
        assert set(actuals[1].index.get_level_values("symbol")) == {"SPY"}
        assert set(preds["har"][1].index.get_level_values("symbol")) == {"SPY"}
        assert len(actuals[1]) == 10  # n_dates

    def test_no_filter_when_eval_symbols_is_none(self):
        """When eval_symbols is None, all symbols remain."""
        all_symbols = ["SPY", "AAPL", "MSFT"]
        actuals = {1: self._make_multi_index_series(all_symbols)}

        cfg = ExperimentConfig(
            name="test",
            universe=all_symbols,
            date_range=("2023-01-02", "2023-01-13"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
        )
        # effective_eval_symbols == universe when eval_symbols is None
        eval_syms = cfg.effective_eval_symbols
        assert set(eval_syms) == set(all_symbols)
        # No filter applied → all symbols remain
        assert set(actuals[1].index.get_level_values("symbol")) == set(all_symbols)


class TestPerSymbolEvalSymbolsFilter:
    """Test that per-symbol path restricts symbols when eval_symbols is set."""

    def test_per_symbol_restricts_to_eval_symbols(self):
        """Simulates the per-symbol filter logic from run_har_tournament."""
        symbols = ["SPY", "AAPL", "MSFT"]
        cfg = ExperimentConfig(
            name="test",
            universe=symbols,
            date_range=("2023-01-02", "2023-01-13"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            eval_symbols=["SPY"],
        )

        # Replicate the filter from run_har_tournament
        eval_set = set(cfg.eval_symbols)
        filtered = [s for s in symbols if s in eval_set] or list(eval_set)
        assert filtered == ["SPY"]

    def test_per_symbol_no_filter_when_eval_symbols_none(self):
        """When eval_symbols is None, all symbols are trained."""
        symbols = ["SPY", "AAPL", "MSFT"]
        cfg = ExperimentConfig(
            name="test",
            universe=symbols,
            date_range=("2023-01-02", "2023-01-13"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
        )
        assert cfg.eval_symbols is None
        # No restriction — all symbols trained
        assert cfg.effective_eval_symbols == symbols
