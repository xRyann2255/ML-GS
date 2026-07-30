"""Unit tests for GNN attention upgrades: conv_type, edge_dim, spillover_matrix."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from volforecast.models.gnn import GNNVolModel


@pytest.fixture
def spillover_graphs():
    """Small synthetic graphs for attention testing. 4 symbols, 80 dates."""
    np.random.seed(123)
    n_symbols = 4
    n_features = 3
    graphs = []
    for t in range(80):
        x = np.random.randn(n_symbols, n_features).astype(np.float32)
        # Ring graph: 0->1->2->3->0
        src = [0, 1, 2, 3]
        dst = [1, 2, 3, 0]
        edge_index = torch.tensor([src, dst], dtype=torch.long)
        edge_attr = torch.tensor([0.5, 0.6, 0.7, 0.8], dtype=torch.float32)
        y = np.random.randn(n_symbols).astype(np.float32) * 0.3 - 8.0
        graphs.append(
            {
                "x": x,
                "edge_index": edge_index,
                "edge_attr": edge_attr,
                "y": y,
                "date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=t),
            }
        )
    return graphs


@pytest.fixture
def spillover_graphs_3d_edges(spillover_graphs):
    """Same graphs but with 3D edge_attr: [weight, vov_src, vov_dst]."""
    out = []
    for g in spillover_graphs:
        ea = g["edge_attr"]
        # Stack: [weight, 0.1, 0.2] for each edge
        attr_3d = torch.stack([ea, torch.full_like(ea, 0.1), torch.full_like(ea, 0.2)], dim=1)
        out.append({**g, "edge_attr": attr_3d})
    return out


@pytest.fixture
def directed_graphs():
    """Directed (non-symmetric) graphs to test directed attention."""
    np.random.seed(456)
    n_symbols = 4
    n_features = 3
    graphs = []
    for t in range(60):
        x = np.random.randn(n_symbols, n_features).astype(np.float32)
        # Asymmetric: only 0->1, 0->2, 1->3 (no reverse)
        edge_index = torch.tensor([[0, 0, 1], [1, 2, 3]], dtype=torch.long)
        edge_attr = torch.tensor([0.9, 0.8, 0.7], dtype=torch.float32)
        y = np.random.randn(n_symbols).astype(np.float32) * 0.3 - 8.0
        graphs.append({"x": x, "edge_index": edge_index, "edge_attr": edge_attr, "y": y})
    return graphs


class TestCharacterization:
    def test_default_gatv2_predictions_deterministic(self, spillover_graphs):
        """Fixed-seed GATv2 predictions must be deterministic across runs."""
        m1 = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
            dropout=0.0,
            use_scheduler=False,
        )
        m1.fit(spillover_graphs[:60])
        preds1 = m1.predict(spillover_graphs[60:65])

        m2 = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
            dropout=0.0,
            use_scheduler=False,
        )
        m2.fit(spillover_graphs[:60])
        preds2 = m2.predict(spillover_graphs[60:65])

        np.testing.assert_allclose(preds1, preds2, atol=1e-6)


class TestConvType:
    def test_transformer_conv_trains(self, spillover_graphs):
        """conv_type='transformer' trains and produces predictions."""
        m = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
            conv_type="transformer",
        )
        m.fit(spillover_graphs[:60])
        preds = m.predict(spillover_graphs[60:65])
        assert preds.shape == (5 * 4,)  # 5 dates × 4 nodes
        assert np.all(np.isfinite(preds))

    def test_transformer_directed_graph(self, directed_graphs):
        """TransformerConv works with directed (asymmetric) graphs."""
        m = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
            conv_type="transformer",
        )
        m.fit(directed_graphs[:45])
        preds = m.predict(directed_graphs[45:50])
        assert np.all(np.isfinite(preds))

    def test_gatv2_directed_graph(self, directed_graphs):
        """GATv2 works with directed graphs."""
        m = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
            conv_type="gatv2",
        )
        m.fit(directed_graphs[:45])
        preds = m.predict(directed_graphs[45:50])
        assert np.all(np.isfinite(preds))

    def test_unknown_conv_type_raises(self):
        """Invalid conv_type raises ValueError."""
        with pytest.raises(ValueError, match="conv_type"):
            GNNVolModel(input_dim=3, conv_type="invalid")


class TestEdgeDim:
    def test_3d_edge_attr_accepted(self, spillover_graphs_3d_edges):
        """Model accepts (E, 3) edge attributes without error."""
        m = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
        )
        m.fit(spillover_graphs_3d_edges[:60])
        preds = m.predict(spillover_graphs_3d_edges[60:65])
        assert preds.shape == (5 * 4,)
        assert np.all(np.isfinite(preds))

    def test_3d_edge_transformer(self, spillover_graphs_3d_edges):
        """TransformerConv accepts 3D edge attrs."""
        m = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
            conv_type="transformer",
        )
        m.fit(spillover_graphs_3d_edges[:60])
        preds = m.predict(spillover_graphs_3d_edges[60:65])
        assert np.all(np.isfinite(preds))


class TestSpilloverMatrix:
    def test_shape_and_row_norm(self, spillover_graphs):
        """spillover_matrix returns (N,N) DataFrame with rows summing to ~1."""
        m = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=10,
            device="cpu",
            precision="fp32",
            seed=42,
            dropout=0.0,
        )
        m.fit(spillover_graphs[:60])
        sm = m.spillover_matrix(spillover_graphs[60:70], symbols=["A", "B", "C", "D"])
        assert sm.shape == (4, 4)
        assert list(sm.index) == ["A", "B", "C", "D"]
        assert list(sm.columns) == ["A", "B", "C", "D"]
        # Diagonal should be zero
        assert (np.diag(sm.values) == 0).all()
        # Rows should sum to ~1 for connected nodes
        row_sums = sm.values.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-6)

    def test_integer_labels_default(self, spillover_graphs):
        """Without symbols kwarg, uses integer labels."""
        m = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
        )
        m.fit(spillover_graphs[:60])
        sm = m.spillover_matrix(spillover_graphs[60:65])
        assert list(sm.index) == ["0", "1", "2", "3"]

    def test_before_fit_raises(self):
        """spillover_matrix before fit raises."""
        m = GNNVolModel(input_dim=3)
        with pytest.raises(RuntimeError, match="spillover_matrix called before fit"):
            m.spillover_matrix([])

    def test_transformer_spillover(self, spillover_graphs):
        """spillover_matrix works with TransformerConv."""
        m = GNNVolModel(
            input_dim=3,
            hidden_dim=8,
            n_heads=2,
            max_epochs=5,
            device="cpu",
            precision="fp32",
            seed=42,
            conv_type="transformer",
        )
        m.fit(spillover_graphs[:60])
        sm = m.spillover_matrix(spillover_graphs[60:65], symbols=["A", "B", "C", "D"])
        assert sm.shape == (4, 4)
        assert (np.diag(sm.values) == 0).all()
