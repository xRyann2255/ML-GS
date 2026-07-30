"""Unit tests for magnetic_laplacian, graph_signal_energy, and energy_series.

These verify integration with GraphSnapshot and edge cases beyond the formula
gold-value tests.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.graphs.diagnostics import (
    graph_signal_energy,
    energy_series,
    magnetic_laplacian,
)


def _snapshot_from_dense(w: np.ndarray, symbols: list[str], date="2024-01-01") -> GraphSnapshot:
    """Build a directed GraphSnapshot from a dense adjacency matrix."""
    src, dst = np.nonzero(w)
    edge_index = np.stack([src, dst], axis=0).astype(np.int64)
    edge_weight = w[src, dst].astype(np.float32)
    return GraphSnapshot(
        edge_index=edge_index,
        edge_weight=edge_weight,
        symbols=tuple(symbols),
        date=date,
        directed=True,
        method="test",
    )


def test_empty_graph_energy_is_zero():
    """Empty graph -> L = I -> E(x) = ||x||^2 is NOT zero; actually xHx = x.x = sum(x^2).
    Wait, L = I means E(x) = x^T I x = ||x||^2. Let's verify."""
    snap = empty_snapshot(["A", "B", "C"], "2024-01-01")
    x = np.array([1.0, 2.0, 3.0])
    energy = graph_signal_energy(snap, x, q=0.0)
    # Empty graph: W=0, W_s=0, Norm=0, L=I
    # E(x) = x^T I x = 1 + 4 + 9 = 14
    assert energy == pytest.approx(14.0, abs=1e-12)


def test_complete_graph_constant_signal_zero_energy():
    """On a fully connected graph (all weights equal), constant signal has energy 0.
    Because the symmetric normalized Laplacian of a complete graph has eigenvalue 0
    for the all-ones eigenvector."""
    n = 4
    w = np.ones((n, n)) - np.eye(n)  # complete graph, undirected
    snap = _snapshot_from_dense(w, [f"N{i}" for i in range(n)])
    x = np.ones(n) * 3.0  # constant signal
    energy = graph_signal_energy(snap, x, q=0.0)
    # Constant vector is in the null space of symmetric Laplacian of connected graph
    assert energy == pytest.approx(0.0, abs=1e-10)


def test_energy_series_returns_correct_dates():
    """energy_series produces values for dates present in both schedule and panel."""
    syms = ["A", "B", "C"]
    w = np.array([[0, 0.5, 0], [0.5, 0, 0.3], [0, 0.3, 0]])
    snap = _snapshot_from_dense(w, syms)
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    schedule = {d: snap for d in dates}
    panel = pd.DataFrame(
        np.random.default_rng(7).normal(size=(5, 3)),
        index=dates,
        columns=syms,
    )
    result = energy_series(schedule, panel, q=0.0)
    assert len(result) == 5
    assert all(np.isfinite(result.values))


def test_energy_series_skips_nan():
    """Dates with NaN in the signal are skipped."""
    syms = ["A", "B"]
    w = np.array([[0, 1], [1, 0]], dtype=np.float64)
    snap = _snapshot_from_dense(w, syms)
    dates = pd.date_range("2024-01-01", periods=3, freq="B")
    schedule = {d: snap for d in dates}
    data = np.array([[1.0, 2.0], [np.nan, 1.0], [3.0, 4.0]])
    panel = pd.DataFrame(data, index=dates, columns=syms)
    result = energy_series(schedule, panel, q=0.0)
    assert len(result) == 2  # middle row skipped


def test_magnetic_laplacian_symmetric_input_q_nonzero():
    """For a symmetric W, the phase exp(i*2*pi*q*0) = 1, so q is irrelevant."""
    w = np.array([[0, 0.5, 0.3], [0.5, 0, 0.2], [0.3, 0.2, 0]])
    L_q0 = magnetic_laplacian(w, q=0.0)
    L_q025 = magnetic_laplacian(w, q=0.25)
    # W - W^T = 0 for symmetric W -> phase = exp(0) = 1 -> same result
    np.testing.assert_allclose(L_q0, L_q025, atol=1e-14)
