"""Unit tests for GNNHARVolModel (Zhang, Pu, Cucuringu & Dong 2025, eqs. 7-8).

TDD-first: these tests define the contract before implementation.
Shared fixtures (identity_graphs, spillover_graphs) live in conftest.py.
"""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.gnnhar import GNNHARVolModel, _build_w_batch


def _fast_params(**over):
    p = dict(
        input_dim=1,
        hidden_dim=4,
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


def test_w_has_zero_diagonal_even_with_self_loops():
    ei = torch.tensor([[0, 1, 0], [1, 0, 0]], dtype=torch.long)  # includes (0,0)
    ea = torch.ones(3)
    w = _build_w_batch([{"edge_index": ei, "edge_attr": ea}], n=2)[0]
    assert w[0, 0] == 0.0 and w[1, 1] == 0.0
    assert w[0, 1] > 0


def test_empty_graph_nests_qlike_har(identity_graphs):
    m = GNNHARVolModel(**_fast_params(input_dim=2)).fit(identity_graphs)
    # graph channel contribution must be exactly zero on empty graphs
    contrib = m._graph_channel(identity_graphs[:1])
    np.testing.assert_allclose(contrib, 0.0, atol=1e-12)
    assert np.isfinite(m.predict(identity_graphs[:1])).all()


def test_seed_determinism_and_ensemble_mean(spillover_graphs):
    p1 = GNNHARVolModel(**_fast_params()).fit(spillover_graphs).predict(spillover_graphs[:5])
    p2 = GNNHARVolModel(**_fast_params()).fit(spillover_graphs).predict(spillover_graphs[:5])
    np.testing.assert_allclose(p1, p2)  # same seed, bit-identical
    singles = [
        GNNHARVolModel(**_fast_params(seed=s)).fit(spillover_graphs).predict(spillover_graphs[:5])
        for s in (42, 43, 44)
    ]
    ens = GNNHARVolModel(**_fast_params(n_seeds=3)).fit(spillover_graphs).predict(
        spillover_graphs[:5]
    )
    np.testing.assert_allclose(ens, np.mean(singles, axis=0), atol=1e-6)


@pytest.mark.slow
def test_learns_planted_spillover_better_than_own_only(spillover_graphs):
    """QLIKE on data with true neighbor effect: gnnhar(graph) < gnnhar(empty graph)."""
    from volforecast.models.gnn import _qlike_loss

    train, test = spillover_graphs[:160], spillover_graphs[160:]
    with_g = GNNHARVolModel(**_fast_params(max_epochs=150)).fit(train)
    empty = [
        dict(g, edge_index=torch.zeros(2, 0, dtype=torch.long), edge_attr=torch.zeros(0))
        for g in train
    ]
    empty_test = [
        dict(g, edge_index=torch.zeros(2, 0, dtype=torch.long), edge_attr=torch.zeros(0))
        for g in test
    ]
    no_g = GNNHARVolModel(**_fast_params(max_epochs=150)).fit(empty)
    y = np.concatenate([g["y"] for g in test])
    q_with = float(_qlike_loss(torch.tensor(with_g.predict(test)), torch.tensor(y)))
    q_without = float(_qlike_loss(torch.tensor(no_g.predict(empty_test)), torch.tensor(y)))
    assert q_with < q_without


def test_n_layers_two_runs_and_param_count_small(spillover_graphs):
    m = GNNHARVolModel(**_fast_params(n_layers=2)).fit(spillover_graphs[:50])
    assert m.get_arch_summary()["param_count"] < 2000


def test_save_load_roundtrip(tmp_path, spillover_graphs):
    m = GNNHARVolModel(**_fast_params()).fit(spillover_graphs[:50])
    p = m.predict(spillover_graphs[:3])
    m.save(tmp_path / "m.pt")
    m2 = GNNHARVolModel.load(tmp_path / "m.pt")
    np.testing.assert_allclose(m2.predict(spillover_graphs[:3]), p, atol=1e-6)


def test_on_progress_counts_across_seeds(spillover_graphs):
    calls: list[tuple[int, int]] = []
    GNNHARVolModel(**_fast_params(n_seeds=2, max_epochs=10)).fit(
        spillover_graphs[:40], on_progress=lambda c, t: calls.append((c, t))
    )
    assert calls and calls[-1][1] == 2 * 10  # total = n_seeds * max_epochs
    assert calls[-1][0] <= calls[-1][1]


def test_registered():
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()
    assert "gnnhar" in MODEL_REGISTRY
    cls = MODEL_REGISTRY["gnnhar"]
    assert cls.requires_graph is True
    assert cls.family == "gnn"
