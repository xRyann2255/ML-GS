"""Tests for _apply_graph_norm helper (plan-102 execute-2).

Per-fold z-score normalisation of node features on the NATIVE graph path.
Fits StandardScaler on the stacked train-fold node feature matrices, applies
to both train and test dicts (shallow copies), leaves other keys untouched.
"""
from __future__ import annotations

import numpy as np
import pytest
import torch

from volforecast.pipeline.runner import _apply_graph_norm


def _make_graph(x: np.ndarray, date: int) -> dict:
    n, _ = x.shape
    return {
        "x": x.astype(np.float32),
        "edge_index": torch.tensor([[0, 1], [1, 0]], dtype=torch.long),
        "edge_attr": torch.tensor([1.0, 1.0], dtype=torch.float32),
        "y": np.zeros(n, dtype=np.float64),
        "date": date,
    }


@pytest.fixture
def synthetic_graphs():
    rng = np.random.default_rng(0)
    # 3 train graphs, 2 test graphs, N=4 nodes, F=3 features
    train_graphs = [_make_graph(rng.normal(loc=5.0, scale=2.0, size=(4, 3)), d) for d in range(3)]
    # Test graphs drawn from a different distribution to check separation.
    test_graphs = [_make_graph(rng.normal(loc=10.0, scale=1.0, size=(4, 3)), 100 + d) for d in range(2)]
    return train_graphs, test_graphs


def test_per_fold_normalisation_zeroes_train_mean_and_unit_variance(synthetic_graphs):
    train_graphs, test_graphs = synthetic_graphs
    train_norm, test_norm = _apply_graph_norm(train_graphs, test_graphs, "per_fold")

    stacked_train = np.concatenate([g["x"] for g in train_norm], axis=0)
    assert np.allclose(stacked_train.mean(axis=0), 0.0, atol=1e-5)
    assert np.allclose(stacked_train.std(axis=0), 1.0, atol=1e-5)


def test_per_fold_test_scaled_by_train_scaler(synthetic_graphs):
    train_graphs, test_graphs = synthetic_graphs
    train_norm, test_norm = _apply_graph_norm(train_graphs, test_graphs, "per_fold")

    # Reconstruct the train-fitted scaler manually and verify it matches test outputs.
    stacked_train_raw = np.concatenate([g["x"] for g in train_graphs], axis=0)
    mu = stacked_train_raw.mean(axis=0)
    sigma = stacked_train_raw.std(axis=0)
    sigma_safe = np.where(sigma == 0.0, 1.0, sigma)

    for orig, scaled in zip(test_graphs, test_norm):
        expected = (orig["x"] - mu) / sigma_safe
        assert np.allclose(scaled["x"], expected, atol=1e-5)

    # Test-set mean should NOT be centred on zero (draws from a different distribution).
    stacked_test = np.concatenate([g["x"] for g in test_norm], axis=0)
    assert not np.allclose(stacked_test.mean(axis=0), 0.0, atol=0.5)


def test_none_mode_passes_through_unchanged(synthetic_graphs):
    train_graphs, test_graphs = synthetic_graphs
    train_norm, test_norm = _apply_graph_norm(train_graphs, test_graphs, "none")

    for orig, out in zip(train_graphs, train_norm):
        assert np.array_equal(orig["x"], out["x"])
    for orig, out in zip(test_graphs, test_norm):
        assert np.array_equal(orig["x"], out["x"])


def test_original_graphs_not_mutated(synthetic_graphs):
    train_graphs, test_graphs = synthetic_graphs
    train_raw_before = [g["x"].copy() for g in train_graphs]
    test_raw_before = [g["x"].copy() for g in test_graphs]

    _apply_graph_norm(train_graphs, test_graphs, "per_fold")

    for before, g in zip(train_raw_before, train_graphs):
        assert np.array_equal(before, g["x"])
    for before, g in zip(test_raw_before, test_graphs):
        assert np.array_equal(before, g["x"])


def test_other_keys_preserved(synthetic_graphs):
    train_graphs, test_graphs = synthetic_graphs
    train_norm, test_norm = _apply_graph_norm(train_graphs, test_graphs, "per_fold")

    for orig, out in zip(train_graphs, train_norm):
        assert out["edge_index"] is orig["edge_index"]
        assert out["edge_attr"] is orig["edge_attr"]
        assert out["y"] is orig["y"]
        assert out["date"] == orig["date"]


def test_constant_feature_produces_no_nans():
    """StandardScaler with with_std=True must not emit NaNs on zero-variance columns."""
    rng = np.random.default_rng(1)
    train_graphs = []
    for d in range(3):
        x = rng.normal(size=(4, 3)).astype(np.float32)
        x[:, 1] = 7.0  # constant column
        train_graphs.append(_make_graph(x, d))
    test_graphs = [_make_graph(rng.normal(size=(4, 3)).astype(np.float32), 100)]

    train_norm, test_norm = _apply_graph_norm(train_graphs, test_graphs, "per_fold")
    for g in train_norm + test_norm:
        assert np.isfinite(g["x"]).all()


def test_nan_input_handled():
    """NaN values in x are zeroed before fitting (defensive)."""
    rng = np.random.default_rng(2)
    train_graphs = []
    for d in range(3):
        x = rng.normal(size=(4, 3)).astype(np.float32)
        x[0, 0] = np.nan
        train_graphs.append(_make_graph(x, d))
    test_graphs = [_make_graph(rng.normal(size=(4, 3)).astype(np.float32), 100)]

    train_norm, test_norm = _apply_graph_norm(train_graphs, test_graphs, "per_fold")
    for g in train_norm + test_norm:
        assert np.isfinite(g["x"]).all()
