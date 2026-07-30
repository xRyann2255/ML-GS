"""Tests for GNN/GNNHAR OOM fallback behavior.

Validates:
- Mega-batch OOM → torch.cuda.empty_cache → fallback to DataLoader path → fit completes
- After 2 retries, OOM is re-raised
- GNNHAR OOM recovery works across seed ensemble
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from volforecast.models.gnn import GNNVolModel
from volforecast.models.gnnhar import GNNHARVolModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graphs(n_dates=60, n_symbols=3, n_features=2, seed=42):
    """Build synthetic graph dicts."""
    rng = np.random.default_rng(seed)
    graphs = []
    for t in range(n_dates):
        x = rng.normal(size=(n_symbols, n_features)).astype(np.float32)
        y = 0.5 * x[:, 0] + rng.normal(0, 0.1, n_symbols)
        # Full connectivity
        edges = [[i, j] for i in range(n_symbols) for j in range(n_symbols) if i != j]
        ei = np.array(edges).T if edges else np.zeros((2, 0), dtype=int)
        graphs.append({
            "x": x,
            "y": y.astype(np.float64),
            "edge_index": torch.tensor(ei, dtype=torch.long),
            "edge_attr": torch.ones(ei.shape[1], dtype=torch.float32),
            "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=t),
        })
    return graphs


def _fast_gnn_params(**over):
    p = dict(
        input_dim=2,
        hidden_dim=8,
        n_heads=2,
        n_layers=1,
        max_epochs=5,
        early_stopping_rounds=5,
        batch_size=16,
        device="cpu",
        seed=42,
        val_fraction=0.2,
    )
    p.update(over)
    return p


def _fast_gnnhar_params(**over):
    p = dict(
        input_dim=2,
        hidden_dim=4,
        max_epochs=5,
        early_stopping_rounds=5,
        n_seeds=2,
        device="cpu",
        seed=42,
        val_fraction=0.2,
    )
    p.update(over)
    return p


class _FakeOOM(torch.cuda.OutOfMemoryError):
    """Simulated CUDA OOM that we can raise on CPU."""
    pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGNNOOMFallback:
    """OOM fallback for GNNVolModel mega-batch path."""

    def test_oom_recovery_switches_to_dataloader(self):
        """OOM in mega-batch → empty_cache → retry with DataLoader succeeds."""
        graphs = _make_graphs(n_dates=30, n_symbols=3, n_features=2)
        model = GNNVolModel(**_fast_gnn_params())

        call_count = [0]
        original_forward = None

        def _oom_once(self, x, edge_index, edge_attr=None, return_attention=False):
            call_count[0] += 1
            if call_count[0] == 1:
                raise _FakeOOM("CUDA out of memory")
            return original_forward(x, edge_index, edge_attr=edge_attr, return_attention=return_attention)

        # Monkeypatch: first call to the model's forward raises OOM
        with patch("torch.cuda.empty_cache") as mock_empty:
            model.fit(graphs[:5])  # fit once to build module
            original_forward = model._module.forward

            # Now re-fit with OOM on first forward call
            call_count[0] = 0
            from volforecast.models.gnn import _GNNModule
            with patch.object(_GNNModule, "forward", _oom_once):
                model2 = GNNVolModel(**_fast_gnn_params())
                model2.fit(graphs)

            # empty_cache was called at least once
            assert mock_empty.called, "torch.cuda.empty_cache should be called on OOM"

        # Model should still be able to predict after recovery
        preds = model2.predict(graphs[:5])
        assert len(preds) == 5 * 3  # n_dates * n_symbols
        assert np.isfinite(preds).all()

    def test_oom_max_retries_raises(self):
        """After 2 retries, OOM is re-raised."""
        graphs = _make_graphs(n_dates=30, n_symbols=3, n_features=2)

        def _always_oom(self, x, edge_index, edge_attr=None, return_attention=False):
            raise _FakeOOM("CUDA out of memory")

        from volforecast.models.gnn import _GNNModule
        with patch.object(_GNNModule, "forward", _always_oom):
            with patch("torch.cuda.empty_cache"):
                model = GNNVolModel(**_fast_gnn_params())
                with pytest.raises(torch.cuda.OutOfMemoryError):
                    model.fit(graphs)


class TestGNNHAROOMFallback:
    """OOM fallback for GNNHARVolModel."""

    def test_gnnhar_oom_recovery(self):
        """GNNHAR OOM recovery works across seed ensemble."""
        graphs = _make_graphs(n_dates=60, n_symbols=3, n_features=2)
        model = GNNHARVolModel(**_fast_gnnhar_params())

        call_count = [0]

        def _oom_once_gnnhar(self, x, w):
            call_count[0] += 1
            if call_count[0] == 1:
                raise _FakeOOM("CUDA out of memory")
            # Call through to original
            h = x
            for theta in self.thetas:
                h = torch.relu(torch.bmm(w, theta(h)))
            return self.alpha[None, :] + self.beta(x).squeeze(-1) + self.gamma(h).squeeze(-1)

        from volforecast.models.gnnhar import _GNNHARModule
        with patch.object(_GNNHARModule, "forward", _oom_once_gnnhar):
            with patch("torch.cuda.empty_cache") as mock_empty:
                model.fit(graphs)

        assert mock_empty.called, "torch.cuda.empty_cache should be called on OOM"
        # Model should predict after recovery
        preds = model.predict(graphs[:5])
        assert len(preds) == 5 * 3
        assert np.isfinite(preds).all()

    def test_gnnhar_oom_max_retries_raises(self):
        """After 2 retries, GNNHAR OOM is re-raised."""
        graphs = _make_graphs(n_dates=60, n_symbols=3, n_features=2)

        def _always_oom(self, x, w):
            raise _FakeOOM("CUDA out of memory")

        from volforecast.models.gnnhar import _GNNHARModule
        with patch.object(_GNNHARModule, "forward", _always_oom):
            with patch("torch.cuda.empty_cache"):
                model = GNNHARVolModel(**_fast_gnnhar_params())
                with pytest.raises(torch.cuda.OutOfMemoryError):
                    model.fit(graphs)
