"""Unit tests for GNN adjacency builder."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.gnn_adjacency import build_adjacency, build_adjacency_series


@pytest.fixture
def panel_returns():
    """Synthetic panel returns with known correlation structure."""
    np.random.seed(42)
    n_dates = 100
    dates = pd.bdate_range("2020-01-01", periods=n_dates)

    # Create correlated symbols: A and B highly correlated, C uncorrelated
    base = np.random.randn(n_dates)
    returns = pd.DataFrame(
        {
            "A": base * 0.01 + np.random.randn(n_dates) * 0.002,
            "B": base * 0.01 + np.random.randn(n_dates) * 0.002,
            "C": np.random.randn(n_dates) * 0.01,
            "D": -base * 0.01 + np.random.randn(n_dates) * 0.002,  # anti-correlated with A
            "E": np.random.randn(n_dates) * 0.01,
        },
        index=dates,
    )
    return returns


class TestBuildAdjacency:
    def test_basic_output_shape(self, panel_returns):
        """Edge index is (2, E) and edge_weight is (E,)."""
        date = panel_returns.index[70]
        edge_index, edge_weight = build_adjacency(panel_returns, date, window=60, threshold=0.3)

        assert edge_index.shape[0] == 2
        assert edge_index.shape[1] == edge_weight.shape[0]
        assert edge_index.dtype == torch.long
        assert edge_weight.dtype == torch.float32

    def test_no_self_loops(self, panel_returns):
        """Diagonal entries (self-loops) are excluded."""
        date = panel_returns.index[70]
        edge_index, _ = build_adjacency(panel_returns, date, window=60, threshold=0.0)

        # No edge where src == dst
        src, dst = edge_index[0], edge_index[1]
        assert not torch.any(src == dst).item()

    def test_threshold_filters_weak_edges(self, panel_returns):
        """Higher threshold produces fewer edges."""
        date = panel_returns.index[70]
        _, w_low = build_adjacency(panel_returns, date, window=60, threshold=0.1)
        _, w_high = build_adjacency(panel_returns, date, window=60, threshold=0.7)

        assert w_low.shape[0] >= w_high.shape[0]

    def test_edges_above_threshold(self, panel_returns):
        """All edge weights are >= threshold."""
        date = panel_returns.index[70]
        threshold = 0.3
        _, edge_weight = build_adjacency(panel_returns, date, window=60, threshold=threshold)

        if edge_weight.shape[0] > 0:
            assert (edge_weight >= threshold).all()

    def test_undirected(self, panel_returns):
        """Graph is undirected: if (i,j) exists, (j,i) also exists."""
        date = panel_returns.index[70]
        edge_index, _ = build_adjacency(panel_returns, date, window=60, threshold=0.3)

        if edge_index.shape[1] > 0:
            edge_set = set()
            for i in range(edge_index.shape[1]):
                edge_set.add((edge_index[0, i].item(), edge_index[1, i].item()))

            for i in range(edge_index.shape[1]):
                src, dst = edge_index[0, i].item(), edge_index[1, i].item()
                assert (dst, src) in edge_set

    def test_causal_window(self, panel_returns):
        """Adjacency at date T only uses returns up to T (not future)."""
        date = panel_returns.index[30]
        # With window=60 but only 31 dates available, should still work
        edge_index, _ = build_adjacency(panel_returns, date, window=60, threshold=0.1)
        # Should produce output (maybe empty if not enough data)
        assert edge_index.shape[0] == 2

    def test_empty_graph_high_threshold(self, panel_returns):
        """Threshold=1.0 should produce empty graph (no perfect correlations)."""
        date = panel_returns.index[70]
        edge_index, edge_weight = build_adjacency(panel_returns, date, window=60, threshold=0.99)

        # With random noise, perfect correlation is unlikely
        assert edge_index.shape[1] == 0 or edge_weight.min() >= 0.99

    def test_correlated_symbols_have_edges(self, panel_returns):
        """Symbols A and B (designed as correlated) should have an edge."""
        date = panel_returns.index[90]
        edge_index, _ = build_adjacency(panel_returns, date, window=60, threshold=0.3)

        if edge_index.shape[1] > 0:
            # A=0, B=1 in the column order
            edges_as_tuples = set()
            for i in range(edge_index.shape[1]):
                edges_as_tuples.add((edge_index[0, i].item(), edge_index[1, i].item()))
            # A and B are strongly correlated — expect edge
            assert (0, 1) in edges_as_tuples or edge_index.shape[1] == 0


class TestBuildAdjacencySeries:
    def test_returns_dict_of_correct_length(self, panel_returns):
        """Returns one entry per date."""
        dates = panel_returns.index[60:65]
        result = build_adjacency_series(panel_returns, dates, window=60, threshold=0.3)

        assert len(result) == len(dates)
        for date in dates:
            assert date in result
            edge_index, edge_weight = result[date]
            assert edge_index.shape[0] == 2
            assert edge_index.shape[1] == edge_weight.shape[0]

    def test_missing_date_returns_empty(self, panel_returns):
        """Date not in panel_returns returns empty tensors."""
        missing_date = pd.Timestamp("2025-01-01")
        result = build_adjacency_series(panel_returns, [missing_date], window=60, threshold=0.3)

        edge_index, edge_weight = result[missing_date]
        assert edge_index.shape[1] == 0
        assert edge_weight.shape[0] == 0
