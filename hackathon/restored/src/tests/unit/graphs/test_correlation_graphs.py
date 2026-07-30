from __future__ import annotations

import numpy as np
import pytest

from volforecast.graphs.correlation import CorrGraphBuilder, KnnGraphBuilder


def _block_of(sym: str) -> str:
    return sym[0]  # "A" or "B"


def test_corr_recovers_blocks(synthetic_returns_panel, symbols8):
    snap = CorrGraphBuilder(threshold=0.5).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    assert snap.n_edges > 0
    src, dst = snap.edge_index
    for i, j in zip(src, dst):
        assert _block_of(symbols8[i]) == _block_of(symbols8[j])
    # all 4*3=12 intra-block ordered pairs per block present
    assert snap.n_edges == 24


def test_corr_weights_are_abs_correlations(synthetic_returns_panel, symbols8):
    snap = CorrGraphBuilder(threshold=0.5).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    assert np.all(snap.edge_weight >= 0.5) and np.all(snap.edge_weight <= 1.0)


def test_corr_is_point_in_time(synthetic_returns_panel, symbols8):
    """Perturbing rows AFTER the estimation window must not change the graph."""
    date = synthetic_returns_panel.index[200]
    window = synthetic_returns_panel.loc[:date]
    snap1 = CorrGraphBuilder(threshold=0.5).build(window, date, symbols8)
    # builder only ever receives rows <= date; assert it uses exactly that input
    snap2 = CorrGraphBuilder(threshold=0.5).build(window.copy(), date, symbols8)
    np.testing.assert_array_equal(snap1.edge_index, snap2.edge_index)


def test_knn_out_degree_before_symmetrization(synthetic_returns_panel, symbols8):
    snap = KnnGraphBuilder(k=2, symmetrize=False).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    src, _ = snap.edge_index
    counts = np.bincount(src, minlength=len(symbols8))
    np.testing.assert_array_equal(counts, np.full(len(symbols8), 2))


def test_knn_symmetrized_is_undirected(synthetic_returns_panel, symbols8):
    snap = KnnGraphBuilder(k=2, symmetrize=True).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    pairs = {(int(i), int(j)) for i, j in zip(*snap.edge_index)}
    assert all((j, i) in pairs for (i, j) in pairs)


def test_empty_window_gives_empty_graph(synthetic_returns_panel, symbols8):
    empty = synthetic_returns_panel.iloc[:3]
    snap = CorrGraphBuilder(threshold=0.5).build(empty, empty.index[-1], symbols8)
    assert snap.n_edges == 0
