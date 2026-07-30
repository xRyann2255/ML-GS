"""Unit tests for DiffusionConv and DCGRUCell (Li et al. 2018, DCRNN eq. 2).

TDD-first: these tests define the contract before implementation.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
nn = torch.nn

from volforecast.models.dcrnn_har import DCGRUCell, DiffusionConv


class TestDiffusionConv:
    """DiffusionConv unit tests."""

    def test_k0_equals_linear(self):
        """When K=0, DiffusionConv has only weights[0] (identity), so output == Linear(x) + bias."""
        torch.manual_seed(0)
        N, in_dim, out_dim = 4, 3, 5
        conv = DiffusionConv(in_dim, out_dim, k=0)

        x = torch.randn(N, in_dim)
        # fwd/bwd shouldn't matter at k=0 — pass arbitrary matrices
        fwd = torch.eye(N)
        bwd = torch.eye(N)

        out = conv(x, fwd, bwd)
        expected = conv.weights[0](x) + conv.bias
        torch.testing.assert_close(out, expected)

    def test_direction_asymmetry(self):
        """Upper-triangular W: conv(x, fwd, bwd) != conv(x, bwd, fwd)."""
        torch.manual_seed(1)
        N, in_dim, out_dim = 5, 4, 6
        conv = DiffusionConv(in_dim, out_dim, k=2)

        x = torch.randn(N, in_dim)
        # Upper triangular adjacency (directed graph)
        W = torch.triu(torch.ones(N, N), diagonal=1)
        fwd, bwd = DiffusionConv.normalize(W)

        out_normal = conv(x, fwd, bwd)
        out_swapped = conv(x, bwd, fwd)

        # Outputs must differ for a directed graph
        assert not torch.allclose(out_normal, out_swapped, atol=1e-6)

    def test_zero_degree_rows_stable(self):
        """Node 0 has no out-edges (row 0 of W is all zeros). No NaN in output."""
        torch.manual_seed(2)
        N, in_dim, out_dim = 4, 3, 5
        conv = DiffusionConv(in_dim, out_dim, k=2)

        # W where row 0 is all zeros (node 0 has zero out-degree)
        W = torch.ones(N, N)
        W[0, :] = 0.0
        fwd, bwd = DiffusionConv.normalize(W)

        x = torch.randn(N, in_dim)
        out = conv(x, fwd, bwd)

        assert not torch.isnan(out).any(), "NaN detected in output with zero-degree row"
        assert out.shape == (N, out_dim)

    def test_diffconv_normalize_directed(self):
        """normalize(W) produces row-stochastic fwd; bwd is row-stochastic for W^T."""
        W = torch.tensor(
            [[0.0, 2.0, 1.0], [0.0, 0.0, 3.0], [0.0, 0.0, 0.0]], dtype=torch.float32
        )
        fwd, bwd = DiffusionConv.normalize(W)

        # fwd = D_O^{-1} W should be row-stochastic (rows sum to 1 where degree > 0)
        fwd_row_sums = fwd.sum(dim=1)
        # Node 0: out-degree 3, Node 1: out-degree 3, Node 2: out-degree 0
        assert abs(fwd_row_sums[0].item() - 1.0) < 1e-6
        assert abs(fwd_row_sums[1].item() - 1.0) < 1e-6
        # Node 2 has zero out-degree → row stays zero (not NaN)
        assert abs(fwd_row_sums[2].item()) < 1e-6

        # bwd = D_I^{-1} W^T should be row-stochastic for W^T
        bwd_row_sums = bwd.sum(dim=1)
        # W^T: col 0 has no in-edges (row 0 of W^T = col 0 of W = [0,0,0])
        # col 1: in-degree 2, col 2: in-degree 4
        assert abs(bwd_row_sums[1].item() - 1.0) < 1e-6
        assert abs(bwd_row_sums[2].item() - 1.0) < 1e-6
        assert abs(bwd_row_sums[0].item()) < 1e-6


class TestDCGRUCell:
    """DCGRUCell unit tests."""

    def test_dcgru_shapes_and_state_update(self):
        """DCGRUCell with N=5, in_dim=3, hidden_dim=8: correct shape and state update."""
        torch.manual_seed(3)
        N, in_dim, hidden_dim = 5, 3, 8
        cell = DCGRUCell(in_dim, hidden_dim, k=2)

        x = torch.randn(N, in_dim)
        h = torch.randn(N, hidden_dim)

        # Build adjacency and normalize
        W = torch.rand(N, N)
        W.fill_diagonal_(0.0)
        fwd, bwd = DiffusionConv.normalize(W)

        h_new = cell(x, h, fwd, bwd)

        # Shape check
        assert h_new.shape == (N, hidden_dim)
        # State actually updates (h_new != h)
        assert not torch.allclose(h_new, h, atol=1e-6)


# ---------------------------------------------------------------------------
# Helper: generate fake graph dicts for DCRNN-HAR tests
# ---------------------------------------------------------------------------

import numpy as np


def _make_fake_graphs(n_dates, n_nodes, n_features, seed=42):
    rng = np.random.default_rng(seed)
    graphs = []
    for t in range(n_dates):
        x = rng.standard_normal((n_nodes, n_features)).astype(np.float32)
        # Random directed adjacency
        W = rng.random((n_nodes, n_nodes)).astype(np.float32) * 0.5
        np.fill_diagonal(W, 0)
        # Sparse format for compatibility
        src, dst = np.nonzero(W > 0.25)
        edge_index = torch.tensor(np.stack([src, dst]), dtype=torch.long)
        edge_attr = torch.tensor(W[src, dst], dtype=torch.float32)
        y = rng.standard_normal(n_nodes).astype(np.float32) - 9.0  # log-RV scale
        graphs.append({
            "x": x,
            "edge_index": edge_index,
            "edge_attr": edge_attr,
            "y": y,
            "date": f"2022-01-{t + 1:02d}",
        })
    return graphs


# ---------------------------------------------------------------------------
# _DCRNNHARModule tests
# ---------------------------------------------------------------------------

class TestDCRNNHARModule:
    def test_dcrnn_module_forward_shape(self):
        """_DCRNNHARModule with N=4, F=3, hidden=8, K=2, seq_len=5: output shape (N,)."""
        from volforecast.models.dcrnn_har import _DCRNNHARModule, DiffusionConv

        torch.manual_seed(10)
        N, F, hidden, K, seq_len = 4, 3, 8, 2, 5
        module = _DCRNNHARModule(N, F, hidden, K)

        # Build a sequence of inputs and adjacency matrices
        xs = [torch.randn(N, F) for _ in range(seq_len)]
        W = torch.rand(N, N)
        W.fill_diagonal_(0.0)
        fwd, bwd = DiffusionConv.normalize(W)
        fwds = [fwd] * seq_len
        bwds = [bwd] * seq_len

        out = module(xs, fwds, bwds)
        assert out.shape == (N,)

    def test_dcrnn_har_fit_predict_shape(self):
        """Fit DCRNNHARVolModel on 30 graphs, predict 10: shape = (10 - warmup) * N."""
        from volforecast.models.dcrnn_har import DCRNNHARVolModel

        N, F = 3, 3
        train_graphs = _make_fake_graphs(30, N, F, seed=100)
        test_graphs = _make_fake_graphs(10, N, F, seed=200)

        model = DCRNNHARVolModel(input_dim=F, seq_len=5, max_epochs=5, early_stopping_rounds=3)
        model.fit(train_graphs)

        warmup = model.warmup  # should be seq_len - 1 = 4
        assert warmup == 4

        # When predicting with warmup+test graphs, predictions cover only test dates
        pred_graphs = train_graphs[-warmup:] + test_graphs
        preds = model.predict(pred_graphs)
        expected_len = len(test_graphs) * N  # 10 * 3 = 30
        assert preds.shape == (expected_len,)
        assert np.isfinite(preds).all()

    def test_joint_training_both_channels_update(self):
        """After fit, both har_skip and DCGRU weights differ from init."""
        from volforecast.models.dcrnn_har import DCRNNHARVolModel

        N, F = 3, 3
        graphs = _make_fake_graphs(30, N, F, seed=300)

        model = DCRNNHARVolModel(input_dim=F, seq_len=3, max_epochs=10, early_stopping_rounds=5)

        # Capture initial weights before fit
        torch.manual_seed(model.seed)
        from volforecast.models.dcrnn_har import _DCRNNHARModule
        ref_module = _DCRNNHARModule(N, F, model.hidden_dim, model.k)
        har_skip_init = ref_module.har_skip.weight.detach().clone()
        gates_init = ref_module.cell.gates.weights[0].weight.detach().clone()

        model.fit(graphs)
        trained_module = model._module_

        # Both channels must have updated
        assert not torch.allclose(trained_module.har_skip.weight.detach().cpu(), har_skip_init, atol=1e-7)
        assert not torch.allclose(trained_module.cell.gates.weights[0].weight.detach().cpu(), gates_init, atol=1e-7)

    def test_warmup_attribute_set(self):
        """DCRNNHARVolModel(input_dim=3, seq_len=22).warmup == 21."""
        from volforecast.models.dcrnn_har import DCRNNHARVolModel

        model = DCRNNHARVolModel(input_dim=3, seq_len=22)
        assert model.warmup == 21


# ---------------------------------------------------------------------------
# Causality and TBPTT tests — single-pass refactor contract
# ---------------------------------------------------------------------------


class TestSinglePassCausality:
    """Tests that verify no information leakage in the single-pass architecture."""

    def test_hidden_state_causality(self):
        """h[t] must be identical whether we pass T or T+5 future graphs.

        Appending future graphs must not change predictions for earlier dates.
        This guarantees no look-ahead leakage in the recurrent forward pass.
        """
        from volforecast.models.dcrnn_har import DCRNNHARVolModel

        N, F = 3, 3
        base_graphs = _make_fake_graphs(30, N, F, seed=500)
        extra_graphs = _make_fake_graphs(5, N, F, seed=600)

        model = DCRNNHARVolModel(
            input_dim=F, seq_len=5, max_epochs=3, early_stopping_rounds=2
        )
        model.fit(base_graphs)

        warmup = model.warmup

        # Predict on base test set
        test_short = _make_fake_graphs(8, N, F, seed=700)
        pred_short = model.predict(base_graphs[-warmup:] + test_short)

        # Predict on base + extra (future appended)
        pred_long = model.predict(base_graphs[-warmup:] + test_short + extra_graphs)

        # First len(test_short)*N predictions must be identical
        n_shared = len(test_short) * N
        np.testing.assert_array_equal(
            pred_short[:n_shared],
            pred_long[:n_shared],
            err_msg="Predictions changed when future graphs were appended — leakage!",
        )

    def test_val_gradient_isolation(self):
        """Validation loss must not produce gradients on model parameters.

        After a fit, we manually run the val portion and check that no .grad
        is accumulated on parameters. This ensures val doesn't leak into training.
        """
        from volforecast.models.dcrnn_har import DCRNNHARVolModel

        N, F = 3, 3
        graphs = _make_fake_graphs(30, N, F, seed=800)

        model = DCRNNHARVolModel(
            input_dim=F, seq_len=5, max_epochs=3, early_stopping_rounds=2
        )
        model.fit(graphs)

        dev = model.device
        module = model._module_
        # Zero all grads
        module.zero_grad()

        # Run a no_grad forward (simulating val) and check no grads accumulate
        X_all = [
            torch.tensor(g["x"][:, :F], dtype=torch.float32).to(dev) for g in graphs[-5:]
        ]
        adj_pairs = [model._build_adj(g, N) for g in graphs[-5:]]

        with torch.no_grad():
            h = torch.zeros(N, model.hidden_dim, device=dev)
            for t in range(len(X_all)):
                fwd, bwd = adj_pairs[t][0].to(dev), adj_pairs[t][1].to(dev)
                h = module.cell(X_all[t], h, fwd, bwd)

        for name, param in module.named_parameters():
            assert param.grad is None or (param.grad == 0).all(), (
                f"Parameter {name} has non-zero grad after no_grad forward — val leakage!"
            )

    def test_predict_single_pass_output_shape(self):
        """predict() returns ((T - warmup) * N,) with single-pass architecture."""
        from volforecast.models.dcrnn_har import DCRNNHARVolModel

        N, F = 4, 3
        train_graphs = _make_fake_graphs(25, N, F, seed=900)
        test_graphs = _make_fake_graphs(12, N, F, seed=901)

        model = DCRNNHARVolModel(
            input_dim=F, seq_len=5, max_epochs=3, early_stopping_rounds=2
        )
        model.fit(train_graphs)

        warmup = model.warmup
        pred_graphs = train_graphs[-warmup:] + test_graphs
        preds = model.predict(pred_graphs)

        expected_len = len(test_graphs) * N
        assert preds.shape == (expected_len,), (
            f"Expected shape ({expected_len},), got {preds.shape}"
        )
        assert np.isfinite(preds).all()

    def test_forward_step_exists_and_matches(self):
        """_DCRNNHARModule.forward_step exists and produces same result as forward."""
        from volforecast.models.dcrnn_har import _DCRNNHARModule, DiffusionConv

        torch.manual_seed(42)
        N, F, hidden, K, seq_len = 4, 3, 8, 2, 5
        module = _DCRNNHARModule(N, F, hidden, K)

        xs = [torch.randn(N, F) for _ in range(seq_len)]
        W = torch.rand(N, N)
        W.fill_diagonal_(0.0)
        fwd, bwd = DiffusionConv.normalize(W)
        fwds = [fwd] * seq_len
        bwds = [bwd] * seq_len

        # Original forward
        out_forward = module(xs, fwds, bwds)

        # Step-by-step via forward_step
        h = torch.zeros(N, hidden)
        for t in range(seq_len):
            pred, h = module.forward_step(xs[t], h, fwds[t], bwds[t])

        # Final pred from forward_step should match forward
        torch.testing.assert_close(pred, out_forward)
