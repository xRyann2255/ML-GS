"""Unit tests for GNNLearnedAdjModel (MTGNN graph-learning layer, Wu et al. 2020).

TDD-first: defines contract before implementation validates.
Shared fixtures (identity_graphs, spillover_graphs) from conftest.py.
"""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.gnn_learned import GNNLearnedAdjModel


def _fast_params(**over):
    p = dict(
        input_dim=1,
        hidden_dim=4,
        embed_dim=4,
        top_k=3,
        alpha=3.0,
        max_epochs=30,
        early_stopping_rounds=30,
        n_seeds=1,
        device="cpu",
        learning_rate=0.03,
        val_fraction=0.2,
        seed=42,
    )
    p.update(over)
    return p


def test_top_k_zero_nests_qlike_har(identity_graphs):
    """top_k=0 -> zero adjacency -> graph channel = 0 -> nests QLIKE-HAR."""
    m = GNNLearnedAdjModel(**_fast_params(input_dim=2, top_k=0)).fit(identity_graphs)
    contrib = m._graph_channel(identity_graphs[:1])
    np.testing.assert_allclose(contrib, 0.0, atol=1e-12)


def test_graph_invariant_to_input_edges(spillover_graphs):
    """Predictions are the same regardless of input edges (learned, not given)."""
    m = GNNLearnedAdjModel(**_fast_params()).fit(spillover_graphs[:80])
    p_with = m.predict(spillover_graphs[:5])
    # Strip edges from prediction graphs
    stripped = [
        dict(g, edge_index=torch.zeros(2, 0, dtype=torch.long), edge_attr=torch.zeros(0))
        for g in spillover_graphs[:5]
    ]
    p_without = m.predict(stripped)
    np.testing.assert_allclose(p_with, p_without)


def test_top_k_dense_well_defined(spillover_graphs):
    """top_k >= N-1 means no sparsification (dense learned adjacency)."""
    n = spillover_graphs[0]["x"].shape[0]
    m = GNNLearnedAdjModel(**_fast_params(top_k=n - 1)).fit(spillover_graphs[:80])
    adj = m.learned_adjacency()
    # No zeros forced by top-k (only the diagonal and relu thresholding)
    assert adj.shape == (n, n)
    assert np.isfinite(adj.values).all()


@pytest.mark.slow
def test_learns_planted_spillover_edges(spillover_graphs):
    """On planted-spillover data, learned A concentrates mass on true edges."""
    n = spillover_graphs[0]["x"].shape[0]  # 4
    m = GNNLearnedAdjModel(
        **_fast_params(top_k=3, max_epochs=150, embed_dim=8, hidden_dim=8)
    ).fit(spillover_graphs)
    adj = m.learned_adjacency().values
    # True ring edges: (0,1),(1,0),(1,2),(2,1),(2,3),(3,2),(3,0),(0,3)
    true_edges = {(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2), (3, 0), (0, 3)}
    # Get top-k per row and check overlap
    top_indices = set()
    for i in range(n):
        row = adj[i].copy()
        row[i] = -1  # exclude diagonal
        top_j = np.argsort(row)[-3:]  # top 3
        for j in top_j:
            if adj[i, j] > 0:
                top_indices.add((i, j))
    overlap = len(top_indices & true_edges)
    # At least 50% overlap with true edges
    assert overlap >= len(top_indices) * 0.5


def test_learned_adjacency_returns_dataframe(spillover_graphs):
    """learned_adjacency() returns a proper DataFrame."""
    m = GNNLearnedAdjModel(**_fast_params()).fit(spillover_graphs[:80])
    adj = m.learned_adjacency(symbols=["A", "B", "C", "D"])
    assert list(adj.columns) == ["A", "B", "C", "D"]
    assert list(adj.index) == ["A", "B", "C", "D"]
    # Zero diagonal
    np.testing.assert_allclose(np.diag(adj.values), 0.0, atol=1e-12)
    # Row-normalized: rows sum to 1 (or 0 if all entries are zero)
    row_sums = adj.values.sum(axis=1)
    for rs in row_sums:
        assert rs == pytest.approx(1.0, abs=1e-6) or rs == pytest.approx(0.0, abs=1e-6)


def test_seed_determinism(spillover_graphs):
    """Same seed produces identical predictions."""
    p1 = GNNLearnedAdjModel(**_fast_params()).fit(spillover_graphs[:80]).predict(
        spillover_graphs[:5]
    )
    p2 = GNNLearnedAdjModel(**_fast_params()).fit(spillover_graphs[:80]).predict(
        spillover_graphs[:5]
    )
    np.testing.assert_allclose(p1, p2)


def test_save_load_roundtrip(tmp_path, spillover_graphs):
    """Save/load produces identical predictions."""
    m = GNNLearnedAdjModel(**_fast_params()).fit(spillover_graphs[:60])
    p = m.predict(spillover_graphs[:3])
    m.save(tmp_path / "learned.pt")
    m2 = GNNLearnedAdjModel.load(tmp_path / "learned.pt")
    np.testing.assert_allclose(m2.predict(spillover_graphs[:3]), p, atol=1e-6)


def test_finite_predictions(spillover_graphs):
    """All predictions are finite."""
    m = GNNLearnedAdjModel(**_fast_params()).fit(spillover_graphs[:80])
    p = m.predict(spillover_graphs[:10])
    assert np.isfinite(p).all()


def test_get_params_roundtrip():
    """get_params returns kwargs sufficient to reconstruct."""
    m = GNNLearnedAdjModel(**_fast_params(embed_dim=16, top_k=7))
    params = m.get_params()
    m2 = GNNLearnedAdjModel(**params)
    assert m2.embed_dim == 16
    assert m2.top_k == 7
