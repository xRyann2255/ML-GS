"""Unit tests for STIDVolModel (Shao et al. 2022 deflation control).

TDD-first: proves STID is graph-invariant and learns per-node identity effects.
Shared fixtures (identity_graphs, spillover_graphs) live in conftest.py.
"""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.stid import STIDVolModel


def _fast(**over):
    p = dict(
        input_dim=1,
        embed_dim=4,
        hidden_dim=16,
        max_epochs=60,
        early_stopping_rounds=60,
        device="cpu",
        learning_rate=0.05,
        seed=42,
    )
    p.update(over)
    return p


def test_graph_invariance(spillover_graphs):
    m = STIDVolModel(**_fast()).fit(spillover_graphs)
    stripped = [
        dict(g, edge_index=torch.zeros(2, 0, dtype=torch.long), edge_attr=torch.zeros(0))
        for g in spillover_graphs[:5]
    ]
    np.testing.assert_allclose(m.predict(spillover_graphs[:5]), m.predict(stripped), atol=1e-12)


def test_learns_per_node_bias(identity_graphs):
    """identity_graphs plant alphas (-1, 0, 1): node-mean preds must be ordered."""
    m = STIDVolModel(**_fast(input_dim=2)).fit(identity_graphs)
    preds = m.predict(identity_graphs).reshape(len(identity_graphs), 3)
    means = preds.mean(axis=0)
    assert means[0] < means[1] < means[2]


def test_seed_determinism(identity_graphs):
    a = STIDVolModel(**_fast(input_dim=2)).fit(identity_graphs).predict(identity_graphs[:3])
    b = STIDVolModel(**_fast(input_dim=2)).fit(identity_graphs).predict(identity_graphs[:3])
    np.testing.assert_allclose(a, b)


def test_save_load_roundtrip(tmp_path, spillover_graphs):
    m = STIDVolModel(**_fast()).fit(spillover_graphs[:50])
    p = m.predict(spillover_graphs[:3])
    m.save(tmp_path / "m.pt")
    m2 = STIDVolModel.load(tmp_path / "m.pt")
    np.testing.assert_allclose(m2.predict(spillover_graphs[:3]), p, atol=1e-6)


def test_registered_and_contract():
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()
    cls = MODEL_REGISTRY["stid"]
    assert cls.requires_graph is True and cls.family == "gnn"
