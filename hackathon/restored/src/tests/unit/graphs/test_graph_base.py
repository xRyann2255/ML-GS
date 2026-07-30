from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.base import GraphBuilder, GraphSnapshot, build_graph_schedule
from volforecast.registry import GRAPH_REGISTRY, register_graph


def _triangle_snapshot() -> GraphSnapshot:
    # 3 nodes; undirected edges (0,1) and (1,2), weight 1.0, stored both directions
    edge_index = np.array([[0, 1, 1, 2], [1, 0, 2, 1]], dtype=np.int64)
    edge_weight = np.ones(4, dtype=np.float32)
    return GraphSnapshot(
        edge_index=edge_index, edge_weight=edge_weight,
        symbols=("X", "Y", "Z"), date=pd.Timestamp("2024-01-02"), method="test",
    )


def test_snapshot_shape_properties():
    s = _triangle_snapshot()
    assert s.n_nodes == 3
    assert s.n_edges == 4
    # density counts undirected pairs: 2 of 3 possible -> 2/3
    assert s.density() == pytest.approx(2.0 / 3.0)


def test_dense_adjacency_unnormalized_binary():
    s = _triangle_snapshot()
    a = s.dense_adjacency(binary=True)
    expected = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.float64)
    np.testing.assert_allclose(a, expected)


def test_dense_adjacency_sym_normalized():
    # D = diag(1, 2, 1); W = D^-1/2 A D^-1/2
    s = _triangle_snapshot()
    w = s.dense_adjacency(norm="sym", binary=True)
    r2 = 1.0 / np.sqrt(2.0)
    expected = np.array([[0, r2, 0], [r2, 0, r2], [0, r2, 0]])
    np.testing.assert_allclose(w, expected, atol=1e-12)


def test_dense_adjacency_row_normalized():
    s = _triangle_snapshot()
    w = s.dense_adjacency(norm="row", binary=True)
    assert w[1].sum() == pytest.approx(1.0)
    assert w[0, 1] == pytest.approx(1.0)


def test_to_torch_roundtrip():
    torch = pytest.importorskip("torch")
    s = _triangle_snapshot()
    ei, ew = s.to_torch()
    assert ei.dtype == torch.long and ei.shape == (2, 4)
    assert ew.dtype == torch.float32 and ew.shape == (4,)


def test_register_graph_decorator_registers_and_rejects_duplicates():
    @register_graph("_test_graph")
    class _Dummy:
        name = "_test_graph"
        directed = False

        def build(self, returns, date, symbols):
            return _triangle_snapshot()

    try:
        assert GRAPH_REGISTRY["_test_graph"] is _Dummy
        assert isinstance(_Dummy(), GraphBuilder)
        with pytest.raises(ValueError, match="Duplicate graph name"):
            register_graph("_test_graph")(_Dummy)
    finally:
        GRAPH_REGISTRY.pop("_test_graph", None)


def test_schedule_refits_on_grid_and_freezes_between(synthetic_returns_panel, symbols8):
    calls: list[pd.Timestamp] = []

    class _Spy:
        name = "_spy"
        directed = False

        def build(self, returns, date, symbols):
            calls.append(date)
            assert returns.index.max() <= date  # PIT: window ends at estimation date
            return GraphSnapshot(
                edge_index=np.zeros((2, 0), dtype=np.int64),
                edge_weight=np.zeros(0, dtype=np.float32),
                symbols=tuple(symbols), date=date, method="_spy",
            )

    dates = list(synthetic_returns_panel.index[100:160])  # 60 forecast dates
    sched = build_graph_schedule(
        synthetic_returns_panel, dates, _Spy(), window=90, refit_every=21, min_history=60,
    )
    assert len(sched) == len(dates)
    # ceil(60/21) = 3 refits
    assert len(calls) == 3
    # frozen between refits: same object identity
    assert sched[dates[0]] is sched[dates[1]]
    assert sched[dates[0]] is not sched[dates[21]]


def test_schedule_skips_insufficient_history(synthetic_returns_panel, symbols8):
    class _Spy:
        name = "_spy"
        directed = False

        def build(self, returns, date, symbols):  # pragma: no cover
            raise AssertionError("must not be called with < min_history rows")

    dates = list(synthetic_returns_panel.index[:5])  # only 1..5 rows of history
    sched = build_graph_schedule(
        synthetic_returns_panel, dates, _Spy(), window=90, refit_every=21, min_history=60,
    )
    assert all(s.n_edges == 0 for s in sched.values())  # empty fallback snapshots
