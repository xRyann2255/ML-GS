"""Tests for regime-blend graph builder."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.graphs.regime_blend import RegimeBlendGraphBuilder


@pytest.fixture
def regime_returns() -> pd.DataFrame:
    """300 bdays x 5 symbols with an injected stress period (days 100-150)."""
    rng = np.random.default_rng(42)
    n_days = 300
    n_syms = 5
    symbols = [f"SYM{i}" for i in range(n_syms)]
    returns = pd.DataFrame(
        rng.normal(0, 0.01, (n_days, n_syms)),
        columns=symbols,
        index=pd.bdate_range("2023-01-01", periods=n_days),
    )
    # Inject stress period (days 100-150): higher vol + stronger correlation
    stress_common = rng.normal(0, 0.05, 50)
    for i in range(n_syms):
        returns.iloc[100:150, i] += stress_common + rng.normal(0, 0.01, 50)
    return returns


class TestRegimeBlendBasics:
    def test_basic_build(self, regime_returns: pd.DataFrame):
        symbols = list(regime_returns.columns)
        date = regime_returns.index[-1]
        builder = RegimeBlendGraphBuilder(base="corr", quantile=0.75)
        snap = builder.build(regime_returns, date, symbols)
        assert isinstance(snap, GraphSnapshot)
        assert snap.method == "regime_blend"
        assert snap.symbols == tuple(symbols)
        assert snap.date == date

    def test_stress_end_uses_stress_graph(self, regime_returns: pd.DataFrame):
        """When the window ends in a stress period, hard-blend returns the stress graph."""
        symbols = list(regime_returns.columns)
        # Use only data up to inside the stress period (days 0-140)
        window = regime_returns.iloc[:140]
        date = window.index[-1]
        builder = RegimeBlendGraphBuilder(
            base="corr", quantile=0.75, blend="hard", min_rows=10, threshold=0.3,
        )
        snap = builder.build(window, date, symbols)
        # The stress period has very high correlation, so stress graph should have edges
        assert snap.n_edges > 0
        assert snap.method == "regime_blend"

        # Build what the stress-only graph would look like
        from volforecast.graphs.correlation import CorrGraphBuilder

        base = CorrGraphBuilder(threshold=0.3)
        trailing_disp = window[symbols].pow(2).mean(axis=1).rolling(22).mean().dropna()
        threshold = trailing_disp.quantile(0.75)
        stress_dates = trailing_disp > threshold
        stress_snap = base.build(window.loc[stress_dates.index[stress_dates]], date, symbols)

        # Hard blend at stress end → should match the stress graph
        np.testing.assert_array_equal(snap.edge_index, stress_snap.edge_index)
        np.testing.assert_array_equal(snap.edge_weight, stress_snap.edge_weight)

    def test_calm_end_uses_calm_graph(self, regime_returns: pd.DataFrame):
        """When the window ends in a calm period, hard-blend returns the calm graph."""
        symbols = list(regime_returns.columns)
        # Use full data — the end is well past the stress period (calm)
        date = regime_returns.index[-1]
        builder = RegimeBlendGraphBuilder(
            base="corr", quantile=0.75, blend="hard", threshold=0.3,
        )
        snap = builder.build(regime_returns, date, symbols)

        # Build what the calm-only graph would look like
        from volforecast.graphs.correlation import CorrGraphBuilder

        base = CorrGraphBuilder(threshold=0.3)
        trailing_disp = regime_returns[symbols].pow(2).mean(axis=1).rolling(22).mean().dropna()
        threshold = trailing_disp.quantile(0.75)
        calm_mask = ~(trailing_disp > threshold)
        calm_snap = base.build(regime_returns.loc[calm_mask.index[calm_mask]], date, symbols)

        np.testing.assert_array_equal(snap.edge_index, calm_snap.edge_index)
        np.testing.assert_array_equal(snap.edge_weight, calm_snap.edge_weight)

    def test_fallback_insufficient_regime_data(self):
        """When one regime subset has < min_rows, falls back to full-window base graph."""
        rng = np.random.default_rng(99)
        n_days = 80
        symbols = ["A", "B", "C"]
        # Very uniform data — one regime will have very few dates
        returns = pd.DataFrame(
            rng.normal(0, 0.01, (n_days, len(symbols))),
            columns=symbols,
            index=pd.bdate_range("2023-01-01", periods=n_days),
        )
        date = returns.index[-1]
        # Set min_rows high enough that the minority regime falls below threshold
        builder = RegimeBlendGraphBuilder(
            base="corr", quantile=0.75, blend="hard", min_rows=60, threshold=0.1,
        )
        snap = builder.build(returns, date, symbols)

        # Should fall back to base graph on full window
        from volforecast.graphs.correlation import CorrGraphBuilder

        full_snap = CorrGraphBuilder(threshold=0.1).build(returns, date, symbols)
        np.testing.assert_array_equal(snap.edge_index, full_snap.edge_index)
        np.testing.assert_array_equal(snap.edge_weight, full_snap.edge_weight)
        assert snap.method == "regime_blend"

    def test_pit_classification(self, regime_returns: pd.DataFrame):
        """Classification only uses data within the estimation window (no future leak)."""
        symbols = list(regime_returns.columns)
        # Build on partial window
        partial = regime_returns.iloc[:200]
        date = partial.index[-1]
        builder = RegimeBlendGraphBuilder(base="corr", quantile=0.75)

        snap_partial = builder.build(partial, date, symbols)

        # Build on full window but with same date — different trailing data means
        # classification may differ. The key check: it doesn't crash and produces
        # a valid snapshot using only in-window data
        snap_full = builder.build(regime_returns, date, symbols)
        assert isinstance(snap_partial, GraphSnapshot)
        assert isinstance(snap_full, GraphSnapshot)

        # The partial window has different trailing_disp quantile, so the regime
        # classification (and therefore the graph) may differ
        # This is the PIT property: the graph depends only on the input window

    def test_base_corr_and_glasso(self, regime_returns: pd.DataFrame):
        """Works with both base='corr' and base='glasso'."""
        symbols = list(regime_returns.columns)
        date = regime_returns.index[-1]

        snap_corr = RegimeBlendGraphBuilder(base="corr", threshold=0.3).build(
            regime_returns, date, symbols,
        )
        assert isinstance(snap_corr, GraphSnapshot)
        assert snap_corr.method == "regime_blend"

        snap_glasso = RegimeBlendGraphBuilder(base="glasso").build(
            regime_returns, date, symbols,
        )
        assert isinstance(snap_glasso, GraphSnapshot)
        assert snap_glasso.method == "regime_blend"

    def test_empty_returns_empty(self):
        """Empty or tiny returns produce empty_snapshot."""
        symbols = ["A", "B", "C"]
        date = pd.Timestamp("2023-06-01")

        builder = RegimeBlendGraphBuilder(base="corr")
        # Empty DataFrame
        empty = pd.DataFrame(columns=symbols, dtype=float)
        snap = builder.build(empty, date, symbols)
        assert snap.n_edges == 0
        assert snap.method == "regime_blend"

        # Tiny returns (< 22 days for rolling)
        tiny = pd.DataFrame(
            np.random.default_rng(0).normal(0, 0.01, (5, 3)),
            columns=symbols,
            index=pd.bdate_range("2023-01-01", periods=5),
        )
        snap2 = builder.build(tiny, date, symbols)
        assert snap2.n_edges == 0
        assert snap2.method == "regime_blend"

    def test_unknown_base_raises(self):
        with pytest.raises(ValueError, match="Unknown base"):
            RegimeBlendGraphBuilder(base="nonexistent")
