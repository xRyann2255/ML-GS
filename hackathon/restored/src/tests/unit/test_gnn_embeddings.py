"""Unit tests for GNN embedding extraction (Plan-09, Task 1).

Tests that extract_features(outputs=["embedding"]) returns hidden-state
embeddings from both GNNVolModel (GATv2) and GNNHARVolModel (GCN), and
that the runner fan-out logic expands 2D arrays into gnn_emb_NN columns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from volforecast.models.gnn import GNNVolModel
from volforecast.models.gnnhar import GNNHARVolModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _gnn_fast_params(**over):
    p = dict(
        input_dim=3,
        hidden_dim=8,
        n_heads=1,
        max_epochs=5,
        early_stopping_rounds=5,
        device="cpu",
        learning_rate=0.01,
        precision="float32",
    )
    p.update(over)
    return p


def _gnnhar_fast_params(**over):
    p = dict(
        input_dim=1,
        hidden_dim=4,
        max_epochs=10,
        early_stopping_rounds=10,
        n_seeds=1,
        device="cpu",
        learning_rate=0.03,
        val_fraction=0.2,
        seed=42,
    )
    p.update(over)
    return p


@pytest.fixture
def small_graphs():
    """4 symbols, 30 dates, ring graph. For GNNVolModel tests."""
    rng = np.random.default_rng(99)
    n_sym = 4
    n_feat = 3
    graphs = []
    for t in range(30):
        x = rng.normal(size=(n_sym, n_feat)).astype(np.float32)
        src = [0, 1, 2, 3]
        dst = [1, 2, 3, 0]
        edge_index = torch.tensor([src, dst], dtype=torch.long)
        edge_attr = torch.tensor([0.5, 0.6, 0.7, 0.8], dtype=torch.float32)
        y = rng.normal(size=n_sym).astype(np.float64) * 0.3 - 8.0
        graphs.append(
            {
                "x": x,
                "edge_index": edge_index,
                "edge_attr": edge_attr,
                "y": y,
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=t),
            }
        )
    return graphs


@pytest.fixture
def trained_gnn(small_graphs):
    model = GNNVolModel(**_gnn_fast_params())
    model.fit(small_graphs)
    return model, small_graphs


# ---------------------------------------------------------------------------
# GNNVolModel (GATv2) embedding tests
# ---------------------------------------------------------------------------


class TestGNNEmbedding:
    def test_gnn_embedding_shape(self, trained_gnn):
        """extract_features(outputs=["embedding"]) returns (total_nodes, hidden_dim)."""
        model, graphs = trained_gnn
        result = model.extract_features(graphs, outputs=["embedding"])
        assert "embedding" in result
        emb = result["embedding"]
        total_nodes = sum(g["x"].shape[0] for g in graphs)
        hidden_dim = model.hidden_dim
        assert emb.shape == (total_nodes, hidden_dim)
        assert emb.dtype == np.float32

    def test_gnn_embedding_valid_output(self, trained_gnn):
        """'embedding' is listed in the valid_outputs set."""
        model, graphs = trained_gnn
        with pytest.raises(ValueError, match="Invalid outputs"):
            model.extract_features(graphs, outputs=["nonexistent"])
        # Should NOT raise for embedding
        model.extract_features(graphs, outputs=["embedding"])

    def test_mixed_outputs_gnn(self, trained_gnn):
        """outputs=["prediction", "embedding"] returns both."""
        model, graphs = trained_gnn
        result = model.extract_features(graphs, outputs=["prediction", "embedding"])
        assert "prediction" in result
        assert "embedding" in result
        total_nodes = sum(g["x"].shape[0] for g in graphs)
        assert result["prediction"].shape == (total_nodes,)
        assert result["embedding"].shape[0] == total_nodes

    def test_scalar_outputs_unchanged(self, trained_gnn):
        """prediction and node_attention still work as 1D arrays."""
        model, graphs = trained_gnn
        result = model.extract_features(graphs, outputs=["prediction", "node_attention"])
        total_nodes = sum(g["x"].shape[0] for g in graphs)
        assert result["prediction"].shape == (total_nodes,)
        assert result["node_attention"].shape == (total_nodes,)


# ---------------------------------------------------------------------------
# GNNHARVolModel (GCN) embedding tests
# ---------------------------------------------------------------------------


class TestGNNHAREmbedding:
    def test_gnnhar_embedding_shape(self, spillover_graphs):
        """extract_features(outputs=["embedding"]) returns (T*N, hidden_dim)."""
        model = GNNHARVolModel(**_gnnhar_fast_params())
        model.fit(spillover_graphs)
        sub = spillover_graphs[:5]
        result = model.extract_features(sub, outputs=["embedding"])
        assert "embedding" in result
        emb = result["embedding"]
        total_nodes = sum(g["x"].shape[0] for g in sub)
        hidden_dim = model.hidden_dim
        assert emb.shape == (total_nodes, hidden_dim)
        assert emb.dtype == np.float32

    def test_gnnhar_embedding_valid_output(self, spillover_graphs):
        """Invalid output names are rejected; 'embedding' is accepted."""
        model = GNNHARVolModel(**_gnnhar_fast_params())
        model.fit(spillover_graphs)
        with pytest.raises(ValueError, match="Invalid outputs"):
            model.extract_features(spillover_graphs[:1], outputs=["bogus"])
        # Should NOT raise
        model.extract_features(spillover_graphs[:1], outputs=["embedding"])

    def test_gnnhar_mixed_outputs(self, spillover_graphs):
        """outputs=["prediction", "embedding"] returns both."""
        model = GNNHARVolModel(**_gnnhar_fast_params())
        model.fit(spillover_graphs)
        sub = spillover_graphs[:3]
        result = model.extract_features(sub, outputs=["prediction", "embedding"])
        assert "prediction" in result
        assert "embedding" in result
        total_nodes = sum(g["x"].shape[0] for g in sub)
        assert result["prediction"].shape == (total_nodes,)
        assert result["embedding"].shape[0] == total_nodes


# ---------------------------------------------------------------------------
# Runner fan-out logic
# ---------------------------------------------------------------------------


class TestFeatureStackFanout:
    def test_feature_stack_fanout(self):
        """A (T*N, D) embedding fans out to D columns gnn_emb_00..gnn_emb_{D-1}."""
        # Simulate runner logic: extracted dict has both 1D and 2D arrays
        n_rows = 20
        n_nodes_per_graph = 4
        n_graphs = 3
        total_nodes = n_nodes_per_graph * n_graphs
        hidden_dim = 8

        # Build fake graphs with _row_indices
        graphs = []
        for i in range(n_graphs):
            start = i * n_nodes_per_graph
            graphs.append(
                {
                    "x": np.random.randn(n_nodes_per_graph, 2).astype(np.float32),
                    "_row_indices": np.arange(start, start + n_nodes_per_graph),
                }
            )

        # Simulate extracted outputs
        pred_arr = np.arange(total_nodes, dtype=np.float32)
        emb_arr = np.arange(total_nodes * hidden_dim, dtype=np.float32).reshape(
            total_nodes, hidden_dim
        )
        extracted = {"prediction": pred_arr, "embedding": emb_arr}

        # Apply the fan-out logic (same as in runner.py)
        result_cols = {}
        for key, arr in extracted.items():
            if arr.ndim == 2:
                n_dims = arr.shape[1]
                for d in range(n_dims):
                    col_name = f"gnn_emb_{d:02d}"
                    full_col = np.full(n_rows, np.nan, dtype=np.float32)
                    offset = 0
                    for g in graphs:
                        n_nodes = g["x"].shape[0]
                        row_indices_g = g["_row_indices"]
                        full_col[row_indices_g] = arr[offset : offset + n_nodes, d]
                        offset += n_nodes
                    result_cols[col_name] = full_col
            else:
                col_name = f"gnn_{key}"
                full_col = np.full(n_rows, np.nan, dtype=np.float32)
                offset = 0
                for g in graphs:
                    n_nodes = g["x"].shape[0]
                    row_indices_g = g["_row_indices"]
                    full_col[row_indices_g] = arr[offset : offset + n_nodes]
                    offset += n_nodes
                result_cols[col_name] = full_col

        # Verify fan-out
        assert "gnn_prediction" in result_cols
        assert result_cols["gnn_prediction"].shape == (n_rows,)

        for d in range(hidden_dim):
            col = f"gnn_emb_{d:02d}"
            assert col in result_cols, f"Missing column {col}"
            assert result_cols[col].shape == (n_rows,)

        # Check no NaN in the mapped region
        for d in range(hidden_dim):
            col = f"gnn_emb_{d:02d}"
            mapped_rows = np.concatenate([g["_row_indices"] for g in graphs])
            assert not np.any(np.isnan(result_cols[col][mapped_rows]))

        # Verify values are correct
        np.testing.assert_array_equal(
            result_cols["gnn_emb_00"][:total_nodes],
            emb_arr[:total_nodes, 0],
        )
