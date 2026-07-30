"""Formula tests for the magnetic Laplacian (Chi, Gao & Wang 2024, eqs. 6-9).

Gold values: hand-computed 3-node directed example with q=0.25.
Verifies Hermitian PSD property, q=0 reduction, and graph signal energy.
"""
from __future__ import annotations

import numpy as np
import pytest

from volforecast.graphs.diagnostics import magnetic_laplacian, graph_signal_energy
from volforecast.graphs.base import GraphSnapshot

pytestmark = pytest.mark.formula


def test_magnetic_laplacian_3node_gold(load_gold):
    """L matches hand-derived 3-node directed example (q=0.25)."""
    gold = load_gold("magnetic_laplacian_3node.json")
    W = np.array(gold["inputs"]["W"], dtype=np.float64)
    q = gold["inputs"]["q"]

    L = magnetic_laplacian(W, q)
    expected_real = np.array(gold["expected"]["L_real"], dtype=np.float64)
    expected_imag = np.array(gold["expected"]["L_imag"], dtype=np.float64)

    np.testing.assert_allclose(L.real, expected_real, atol=1e-14)
    np.testing.assert_allclose(L.imag, expected_imag, atol=1e-14)


def test_magnetic_laplacian_eigenvalues_gold(load_gold):
    """Eigenvalues match gold: [0, 1, 2] for the 3-node example."""
    gold = load_gold("magnetic_laplacian_3node.json")
    W = np.array(gold["inputs"]["W"], dtype=np.float64)
    q = gold["inputs"]["q"]

    L = magnetic_laplacian(W, q)
    eigvals = np.linalg.eigvalsh(L)
    expected = np.array(gold["expected"]["eigenvalues_sorted"], dtype=np.float64)
    np.testing.assert_allclose(np.sort(eigvals), expected, atol=1e-12)


def test_graph_signal_energy_gold(load_gold):
    """Energy E(x) for x=[1,1,0] matches gold value 2.0."""
    gold = load_gold("magnetic_laplacian_3node.json")
    W = np.array(gold["inputs"]["W"], dtype=np.float64)
    q = gold["inputs"]["q"]

    # Build a snapshot with the gold adjacency
    edge_index = np.array([[0], [1]], dtype=np.int64)
    edge_weight = np.array([1.0], dtype=np.float32)
    snap = GraphSnapshot(
        edge_index=edge_index,
        edge_weight=edge_weight,
        symbols=("A", "B", "C"),
        date="2024-01-01",
        directed=True,
        method="test",
    )

    x = np.array([1.0, 1.0, 0.0])
    # graph_signal_energy uses q=0 by default; pass q explicitly for gold test
    energy = graph_signal_energy(snap, x, q=q)
    assert energy == pytest.approx(gold["expected"]["energy_x_1_1_0"], abs=1e-12)


def test_q_zero_reduces_to_symmetric_laplacian(load_gold):
    """q=0 magnetic Laplacian == standard symmetric normalized Laplacian on W_s."""
    gold = load_gold("magnetic_laplacian_3node.json")
    W = np.array(gold["q_zero_case"]["inputs"]["W"], dtype=np.float64)

    L = magnetic_laplacian(W, q=0.0)
    expected_real = np.array(gold["q_zero_case"]["expected"]["L_real"], dtype=np.float64)
    expected_imag = np.array(gold["q_zero_case"]["expected"]["L_imag"], dtype=np.float64)

    np.testing.assert_allclose(L.real, expected_real, atol=1e-14)
    np.testing.assert_allclose(L.imag, expected_imag, atol=1e-14)
    # All imaginary parts zero when q=0
    np.testing.assert_allclose(L.imag, 0.0, atol=1e-14)


def test_magnetic_laplacian_hermitian_psd_random():
    """L is Hermitian and PSD for a random directed W."""
    rng = np.random.default_rng(123)
    W = rng.uniform(0, 1, size=(5, 5))
    np.fill_diagonal(W, 0)

    for q in [0.0, 0.1, 0.25, 0.5]:
        L = magnetic_laplacian(W, q)
        # Hermitian: L == L^H
        np.testing.assert_allclose(L, L.conj().T, atol=1e-12)
        # PSD: min eigenvalue >= -eps
        eigvals = np.linalg.eigvalsh(L)
        assert eigvals.min() >= -1e-10, f"q={q}: min eigenvalue = {eigvals.min()}"


def test_q_zero_equals_standard_laplacian_general():
    """For any W, L(q=0) == I - D_s^{-1/2} W_s D_s^{-1/2} (no complex part)."""
    rng = np.random.default_rng(456)
    W = rng.uniform(0, 1, size=(4, 4))
    np.fill_diagonal(W, 0)

    L = magnetic_laplacian(W, q=0.0)
    # Build standard symmetric normalized Laplacian manually
    ws = 0.5 * (W + W.T)
    d = ws.sum(axis=1)
    inv_sqrt = np.where(d > 0, 1.0 / np.sqrt(d), 0.0)
    norm = inv_sqrt[:, None] * ws * inv_sqrt[None, :]
    expected = np.eye(4) - norm

    np.testing.assert_allclose(L.real, expected, atol=1e-12)
    np.testing.assert_allclose(L.imag, 0.0, atol=1e-14)
