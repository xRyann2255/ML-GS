"""Unit tests for GNN (Graph Attention Network) volatility model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from volforecast.models.gnn import GNNVolModel


@pytest.fixture
def synthetic_graphs():
    """Build tiny synthetic graph snapshots for testing.

    5 symbols, 80 dates, random features + adjacency.
    """
    np.random.seed(42)
    n_symbols = 5
    n_features = 4
    n_dates = 80

    graphs = []
    for t in range(n_dates):
        # Node features: random
        x = np.random.randn(n_symbols, n_features).astype(np.float32)

        # Simple fully-connected graph (all pairs, no self-loops)
        src, dst = [], []
        for i in range(n_symbols):
            for j in range(n_symbols):
                if i != j:
                    src.append(i)
                    dst.append(j)
        edge_index = torch.tensor([src, dst], dtype=torch.long)
        edge_attr = torch.rand(len(src), dtype=torch.float32) * 0.5 + 0.3

        # Targets: log-RV with some structure (mean + noise)
        y = np.random.randn(n_symbols).astype(np.float32) * 0.3 - 8.0  # log-RV scale

        graphs.append({
            "x": x,
            "edge_index": edge_index,
            "edge_attr": edge_attr,
            "y": y,
            "date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=t),
        })

    return graphs


@pytest.fixture
def small_model_params():
    """Minimal model params for fast testing."""
    return {
        "input_dim": 4,
        "hidden_dim": 8,
        "n_heads": 2,
        "n_layers": 2,
        "dropout": 0.0,
        "learning_rate": 0.01,
        "weight_decay": 0.0,
        "max_epochs": 5,
        "batch_size": 16,
        "val_fraction": 0.2,
        "early_stopping_rounds": 3,
        "loss": "mse",
        "adj_window": 60,
        "adj_threshold": 0.3,
        "device": "cpu",
        "precision": "fp32",
        "seed": 42,
    }


class TestGNNVolModel:
    def test_init(self, small_model_params):
        """Model initializes without error."""
        model = GNNVolModel(**small_model_params)
        assert model.input_dim == 4
        assert model.hidden_dim == 8
        assert model.n_heads == 2
        assert model._module is None

    def test_fit_produces_finite_loss(self, synthetic_graphs, small_model_params):
        """Training produces a finite best validation loss."""
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)

        assert model._module is not None
        assert model.best_val_loss_ is not None
        assert np.isfinite(model.best_val_loss_)
        assert model.epochs_run_ > 0

    def test_predict_shape(self, synthetic_graphs, small_model_params):
        """Predict returns correct number of values (total nodes across all graphs)."""
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)

        # Predict on subset
        test_graphs = synthetic_graphs[:5]
        preds = model.predict(test_graphs)

        expected_n = sum(g["x"].shape[0] for g in test_graphs)
        assert preds.shape == (expected_n,)
        assert np.all(np.isfinite(preds))

    def test_predict_before_fit_raises(self, small_model_params):
        """predict() before fit() raises RuntimeError."""
        model = GNNVolModel(**small_model_params)
        with pytest.raises(RuntimeError, match="predict called before fit"):
            model.predict([{"x": np.zeros((3, 4)), "edge_index": torch.zeros(2, 0, dtype=torch.long), "edge_attr": torch.zeros(0)}])

    def test_qlike_loss_decreases(self, synthetic_graphs):
        """QLIKE loss decreases over training epochs."""
        params = {
            "input_dim": 4,
            "hidden_dim": 8,
            "n_heads": 2,
            "n_layers": 2,
            "dropout": 0.0,
            "learning_rate": 0.005,
            "weight_decay": 0.0,
            "max_epochs": 20,
            "batch_size": 32,
            "val_fraction": 0.2,
            "early_stopping_rounds": 20,  # disable early stopping
            "loss": "qlike",
            "adj_window": 60,
            "adj_threshold": 0.3,
            "device": "cpu",
            "precision": "fp32",
            "seed": 42,
        }
        model = GNNVolModel(**params)
        model.fit(synthetic_graphs)

        # Check that training loss decreased
        if len(model.history_) >= 2:
            first_loss = model.history_[0]["train_loss"]
            last_loss = model.history_[-1]["train_loss"]
            assert last_loss < first_loss

    def test_extract_features_prediction(self, synthetic_graphs, small_model_params):
        """extract_features returns prediction array."""
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)

        test_graphs = synthetic_graphs[:3]
        result = model.extract_features(test_graphs, outputs=["prediction"])

        assert "prediction" in result
        expected_n = sum(g["x"].shape[0] for g in test_graphs)
        assert result["prediction"].shape == (expected_n,)
        assert np.all(np.isfinite(result["prediction"]))

    def test_extract_features_node_attention(self, synthetic_graphs, small_model_params):
        """extract_features returns node_attention array."""
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)

        test_graphs = synthetic_graphs[:3]
        result = model.extract_features(test_graphs, outputs=["prediction", "node_attention"])

        assert "node_attention" in result
        expected_n = sum(g["x"].shape[0] for g in test_graphs)
        assert result["node_attention"].shape == (expected_n,)
        # Attention weights should be non-negative
        assert np.all(result["node_attention"] >= 0)

    def test_extract_features_before_fit_raises(self, small_model_params):
        """extract_features before fit raises RuntimeError."""
        model = GNNVolModel(**small_model_params)
        with pytest.raises(RuntimeError, match="extract_features called before fit"):
            model.extract_features([], outputs=["prediction"])

    def test_save_load_roundtrip(self, synthetic_graphs, small_model_params, tmp_path):
        """save/load produces identical predictions."""
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)

        test_graphs = synthetic_graphs[:3]
        preds_before = model.predict(test_graphs)

        # Save
        save_path = tmp_path / "gnn_model.pt"
        model.save(save_path)
        assert save_path.exists()

        # Load
        loaded = GNNVolModel.load(save_path)
        preds_after = loaded.predict(test_graphs)

        np.testing.assert_allclose(preds_before, preds_after, atol=1e-5)

    def test_get_params(self, small_model_params):
        """get_params returns all init kwargs."""
        model = GNNVolModel(**small_model_params)
        params = model.get_params()

        assert params["input_dim"] == 4
        assert params["hidden_dim"] == 8
        assert params["n_heads"] == 2
        assert params["loss"] == "mse"
        assert params["device"] == "cpu"

    def test_get_arch_summary(self, synthetic_graphs, small_model_params):
        """get_arch_summary includes param_count after fit."""
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)

        summary = model.get_arch_summary()
        assert summary["param_count"] is not None
        assert summary["param_count"] > 0
        assert summary["epochs_trained"] > 0

    def test_empty_edge_graphs_filtered(self, small_model_params):
        """Graphs with zero edges are filtered out during training."""
        # Create graphs: some with edges, some without
        graphs = []
        for i in range(20):
            x = np.random.randn(3, 4).astype(np.float32)
            y = np.random.randn(3).astype(np.float32) * 0.3 - 8.0
            if i % 2 == 0:
                # Has edges
                edge_index = torch.tensor([[0, 1, 1, 2], [1, 0, 2, 1]], dtype=torch.long)
                edge_attr = torch.tensor([0.5, 0.5, 0.4, 0.4], dtype=torch.float32)
            else:
                # No edges
                edge_index = torch.zeros(2, 0, dtype=torch.long)
                edge_attr = torch.zeros(0, dtype=torch.float32)
            graphs.append({"x": x, "edge_index": edge_index, "edge_attr": edge_attr, "y": y})

        model = GNNVolModel(**small_model_params)
        model.fit(graphs)
        assert model._module is not None

    def test_nan_targets_masked(self, small_model_params):
        """NaN targets in node-level y are masked during loss computation."""
        graphs = []
        for i in range(30):
            x = np.random.randn(5, 4).astype(np.float32)
            y = np.random.randn(5).astype(np.float32) * 0.3 - 8.0
            # Make some targets NaN
            y[0] = np.nan
            edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long)
            edge_attr = torch.tensor([0.5, 0.4, 0.6, 0.3], dtype=torch.float32)
            graphs.append({"x": x, "edge_index": edge_index, "edge_attr": edge_attr, "y": y})

        model = GNNVolModel(**small_model_params)
        # Should not raise despite NaN targets
        model.fit(graphs)
        assert model._module is not None

    # ------------------------------------------------------------------
    # Step 4 training-loop optimisation tests
    # ------------------------------------------------------------------

    def test_fit_accepts_prebuilt_data_objects(self, synthetic_graphs, small_model_params):
        """4a: fit() accepts list[Data] directly, skipping dict→Data conversion."""
        from torch_geometric.data import Data

        # Pre-convert to Data objects
        data_list = []
        for g in synthetic_graphs:
            x = torch.tensor(g["x"], dtype=torch.float32)
            edge_index = g["edge_index"].clone()
            edge_attr = g["edge_attr"].clone().unsqueeze(-1)
            y_t = torch.tensor(g["y"], dtype=torch.float32)
            mask = ~torch.isnan(y_t)
            data_list.append(Data(x=x, edge_index=edge_index, edge_attr=edge_attr, y=y_t, mask=mask))

        model = GNNVolModel(**small_model_params)
        model.fit(data_list)

        assert model._module is not None
        assert model.best_val_loss_ is not None
        assert np.isfinite(model.best_val_loss_)

    def test_predict_accepts_prebuilt_data_objects(self, synthetic_graphs, small_model_params):
        """4a: predict() accepts list[Data] directly."""
        from torch_geometric.data import Data

        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)

        # Pre-convert test graphs to Data
        test_graphs = synthetic_graphs[:3]
        data_list = []
        for g in test_graphs:
            x = torch.tensor(g["x"], dtype=torch.float32)
            edge_index = g["edge_index"].clone()
            edge_attr = g["edge_attr"].clone().unsqueeze(-1)
            data_list.append(Data(x=x, edge_index=edge_index, edge_attr=edge_attr))

        preds = model.predict(data_list)
        expected_n = sum(g["x"].shape[0] for g in test_graphs)
        assert preds.shape == (expected_n,)
        assert np.all(np.isfinite(preds))

    def test_new_params_in_get_params(self, small_model_params):
        """New params (use_scheduler, grad_accumulation_steps, compile) in get_params()."""
        model = GNNVolModel(**small_model_params)
        params = model.get_params()
        assert "use_scheduler" in params
        assert "grad_accumulation_steps" in params
        assert "compile" in params
        # Check defaults
        assert params["use_scheduler"] is True
        assert params["grad_accumulation_steps"] == 1
        assert params["compile"] is True

    def test_new_params_in_arch_summary(self, synthetic_graphs, small_model_params):
        """New params appear in get_arch_summary()."""
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)
        summary = model.get_arch_summary()
        assert "use_scheduler" in summary
        assert "grad_accumulation_steps" in summary
        assert "compile" in summary

    def test_scheduler_disabled(self, synthetic_graphs, small_model_params):
        """4c: use_scheduler=False trains without scheduler."""
        small_model_params["use_scheduler"] = False
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)
        assert model._module is not None
        assert np.isfinite(model.best_val_loss_)

    def test_grad_accumulation(self, synthetic_graphs, small_model_params):
        """4d: grad_accumulation_steps > 1 trains without error."""
        small_model_params["grad_accumulation_steps"] = 4
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)
        assert model._module is not None
        assert np.isfinite(model.best_val_loss_)

    def test_compile_cpu_skipped(self, synthetic_graphs, small_model_params):
        """4e: torch.compile is skipped on CPU (no error)."""
        small_model_params["compile"] = True
        small_model_params["device"] = "cpu"
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)
        assert model._module is not None

    def test_save_load_with_new_params(self, synthetic_graphs, small_model_params, tmp_path):
        """New params survive save/load roundtrip."""
        small_model_params["use_scheduler"] = False
        small_model_params["grad_accumulation_steps"] = 2
        small_model_params["compile"] = False
        model = GNNVolModel(**small_model_params)
        model.fit(synthetic_graphs)

        save_path = tmp_path / "gnn_new_params.pt"
        model.save(save_path)
        loaded = GNNVolModel.load(save_path)

        assert loaded.use_scheduler is False
        assert loaded.grad_accumulation_steps == 2
        assert loaded.compile is False

        preds_orig = model.predict(synthetic_graphs[:2])
        preds_loaded = loaded.predict(synthetic_graphs[:2])
        np.testing.assert_allclose(preds_orig, preds_loaded, atol=1e-5)
