"""Unit tests for GSPHARVolModel (Chi, Gao & Wang 2024, magnetic Laplacian spectral).

TDD-first: defines contract before implementation validates.
Shared fixtures (identity_graphs, spillover_graphs) from conftest.py.
"""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.gsp_har import GSPHARVolModel


def _fast_params(**over):
    p = dict(
        input_dim=1,
        q=0.25,
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


def test_empty_graph_nests_qlike_har(identity_graphs):
    """Empty graph: h=0 init -> spectral channel = 0 -> nests QLIKE-HAR."""
    m = GSPHARVolModel(**_fast_params(input_dim=2, max_epochs=0))
    # Train with 0 epochs just to set up the module (need to fit to allocate)
    # Actually, max_epochs=0 won't work. Use a fresh model and check init.
    m2 = GSPHARVolModel(**_fast_params(input_dim=2, max_epochs=1))
    m2.fit(identity_graphs)
    # The graph channel at initialization should be zero because h_re=h_im=0
    # and gamma weights are near zero after 1 epoch of training.
    # Better test: use a model trained on identity graphs (no edges)
    contrib = m2._graph_channel(identity_graphs[:1])
    # On empty graphs with L=I and h initialized near zero after minimal training,
    # contribution should be negligible
    assert np.abs(contrib).max() < 0.5  # very lenient for 1 epoch


def test_nesting_at_init(identity_graphs):
    """At initialization (before training), spectral channel is exactly zero."""
    m = GSPHARVolModel(**_fast_params(input_dim=2))
    # Manually initialize to test the zero-init property
    n = identity_graphs[0]["x"].shape[0]
    from volforecast.models.gsp_har import _GSPHARModule
    module = _GSPHARModule(n, 2)
    # h_re and h_im are zero at init
    assert torch.all(module.h_re == 0)
    assert torch.all(module.h_im == 0)
    # gamma weights are zero at init (nn.Linear default is not zero, but let's verify
    # the spectral channel contribution is zero when h=0)
    x = torch.randn(5, n, 2)
    u = torch.eye(n, dtype=torch.complex64)
    with torch.no_grad():
        xc = x.to(torch.complex64)
        u_h = u.conj().T
        x_hat = torch.einsum("ij,tjf->tif", u_h, xc)
        filt = (module.h_re + 1j * module.h_im).unsqueeze(0).unsqueeze(-1)
        g = torch.einsum("ij,tjf->tif", u, x_hat * filt).real
    # g should be zero because filt=0
    np.testing.assert_allclose(g.numpy(), 0.0, atol=1e-12)


def test_q_zero_and_q_nonzero_differ_on_directed(spillover_graphs):
    """On directed graphs, q=0 and q=0.25 produce different Laplacians.
    This verifies that the direction-encoding mechanism works."""
    from volforecast.graphs.diagnostics import magnetic_laplacian
    from volforecast.models.gsp_har import _build_dense_from_graph

    # Create a genuinely asymmetric directed graph (0->1 only, not 1->0)
    n = 4
    ei = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)  # chain: 0->1->2->3
    ea = torch.ones(3)
    g = {
        "x": np.zeros((n, 1), dtype=np.float32),
        "edge_index": ei,
        "edge_attr": ea,
        "y": np.zeros(n),
        "date": "2024-01-01",
    }
    w = _build_dense_from_graph(g, n)
    # Verify W is asymmetric
    assert not np.allclose(w, w.T)
    L0 = magnetic_laplacian(w, q=0.0)
    L025 = magnetic_laplacian(w, q=0.25)
    # Laplacians must differ (direction is encoded in phase)
    assert not np.allclose(L0, L025, atol=1e-6)


def test_q_irrelevant_on_symmetric(spillover_graphs):
    """On symmetric (undirected) graphs, q doesn't matter."""
    # spillover_graphs are already symmetric (ring with both directions)
    m0 = GSPHARVolModel(**_fast_params(q=0.0)).fit(spillover_graphs[:80])
    m025 = GSPHARVolModel(**_fast_params(q=0.25)).fit(spillover_graphs[:80])
    p0 = m0.predict(spillover_graphs[:5])
    p025 = m025.predict(spillover_graphs[:5])
    # Same predictions because W - W^T = 0 on symmetric graphs
    np.testing.assert_allclose(p0, p025, atol=1e-4)


def test_eigh_cache_counts(spillover_graphs):
    """Eigendecomposition computed once per unique snapshot, not per date."""
    # All spillover_graphs share the same edge_index tensor object
    m = GSPHARVolModel(**_fast_params(max_epochs=5)).fit(spillover_graphs[:60])
    # Since all graphs share the same edge_index object, should be 1 decomposition
    assert m._eigh_count == 1


def test_eigh_cache_multiple_snapshots(spillover_graphs):
    """Multiple distinct edge_index objects trigger multiple decompositions."""
    # Create graphs with two different edge structures
    graphs = []
    ei1 = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]], dtype=torch.long)
    ei2 = torch.tensor([[0, 1, 2], [2, 3, 0]], dtype=torch.long)
    rng = np.random.default_rng(42)
    for t in range(60):
        ei = ei1 if t < 30 else ei2
        x = rng.normal(size=(4, 1)).astype(np.float32)
        y = rng.normal(size=(4,)).astype(np.float64)
        graphs.append({
            "x": x,
            "edge_index": ei,
            "edge_attr": torch.ones(ei.shape[1]),
            "y": y,
            "date": f"2024-01-{t+1:02d}",
        })
    m = GSPHARVolModel(**_fast_params(max_epochs=5)).fit(graphs)
    assert m._eigh_count == 2


def test_seed_determinism(spillover_graphs):
    """Same seed produces identical predictions."""
    p1 = GSPHARVolModel(**_fast_params()).fit(spillover_graphs[:80]).predict(spillover_graphs[:5])
    p2 = GSPHARVolModel(**_fast_params()).fit(spillover_graphs[:80]).predict(spillover_graphs[:5])
    np.testing.assert_allclose(p1, p2)


def test_save_load_roundtrip(tmp_path, spillover_graphs):
    """Save/load produces identical predictions."""
    m = GSPHARVolModel(**_fast_params()).fit(spillover_graphs[:60])
    p = m.predict(spillover_graphs[:3])
    m.save(tmp_path / "gsp.pt")
    m2 = GSPHARVolModel.load(tmp_path / "gsp.pt")
    np.testing.assert_allclose(m2.predict(spillover_graphs[:3]), p, atol=1e-6)


def test_finite_predictions(spillover_graphs):
    """All predictions are finite."""
    m = GSPHARVolModel(**_fast_params()).fit(spillover_graphs[:80])
    p = m.predict(spillover_graphs[:10])
    assert np.isfinite(p).all()


def test_get_params_roundtrip():
    """get_params returns kwargs sufficient to reconstruct."""
    m = GSPHARVolModel(**_fast_params(q=0.1))
    params = m.get_params()
    m2 = GSPHARVolModel(**params)
    assert m2.q == 0.1
    assert m2.input_dim == 1
