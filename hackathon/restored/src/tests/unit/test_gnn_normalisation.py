"""Canonical unit tests for GNN per-fold z-score normalisation (plan-102 execute-4).

Tests the acceptance criteria named in plan-102:
    - test_graph_norm_train_mean_zero
    - test_graph_norm_train_std_one
    - test_graph_norm_no_leakage
    - test_graph_norm_mode_none
    - test_graph_norm_handles_constant_features

Selectable via ``./vol test -k gnn_norm``.

Full-coverage complementary suites already live in
:mod:`test_graph_norm_helper` (native path, 7 tests) and
:mod:`test_gnn_feature_stack_norm` (feature-stack path, 3 tests). This file
provides a compact, plan-named surface for quick verification of the five
canonical properties.
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
def graphs():
    """3 train + 2 test graphs, each 4 nodes × 3 features, drawn on different means."""
    rng = np.random.default_rng(0)
    train = [_make_graph(rng.normal(loc=5.0, scale=2.0, size=(4, 3)), d) for d in range(3)]
    test = [_make_graph(rng.normal(loc=10.0, scale=1.0, size=(4, 3)), 100 + d) for d in range(2)]
    return train, test


def test_gnn_norm_train_mean_zero(graphs):
    """After per-fold normalisation the stacked train x has ~zero mean per column."""
    train, test = graphs
    train_norm, _ = _apply_graph_norm(train, test, "per_fold")
    stacked = np.concatenate([g["x"] for g in train_norm], axis=0)
    assert np.allclose(stacked.mean(axis=0), 0.0, atol=1e-5)


def test_gnn_norm_train_std_one(graphs):
    """After per-fold normalisation the stacked train x has ~unit std per column."""
    train, test = graphs
    train_norm, _ = _apply_graph_norm(train, test, "per_fold")
    stacked = np.concatenate([g["x"] for g in train_norm], axis=0)
    assert np.allclose(stacked.std(axis=0), 1.0, atol=1e-5)


def test_gnn_norm_no_leakage(graphs):
    """Test graphs are transformed with train-fold statistics only (no fit on test).

    Verified by reconstructing the train-fitted scaler manually and matching outputs
    to what the helper emits for the test graphs.
    """
    train, test = graphs
    train_norm, test_norm = _apply_graph_norm(train, test, "per_fold")

    stacked_train_raw = np.concatenate([g["x"] for g in train], axis=0)
    mu = stacked_train_raw.mean(axis=0)
    sigma = stacked_train_raw.std(axis=0)
    sigma_safe = np.where(sigma == 0.0, 1.0, sigma)

    for orig, scaled in zip(test, test_norm):
        expected = (orig["x"] - mu) / sigma_safe
        assert np.allclose(scaled["x"], expected, atol=1e-5)

    # Sanity: test-set mean should not be centred (draws from a different distribution).
    stacked_test = np.concatenate([g["x"] for g in test_norm], axis=0)
    assert not np.allclose(stacked_test.mean(axis=0), 0.0, atol=0.5)


def test_gnn_norm_mode_none(graphs):
    """With mode='none' the helper is a pass-through — no rescaling."""
    train, test = graphs
    train_norm, test_norm = _apply_graph_norm(train, test, "none")
    for orig, out in zip(train, train_norm):
        assert np.array_equal(orig["x"], out["x"])
    for orig, out in zip(test, test_norm):
        assert np.array_equal(orig["x"], out["x"])


def test_gnn_norm_handles_constant_features():
    """Zero-variance columns must not produce NaNs after StandardScaler transform."""
    rng = np.random.default_rng(1)
    train = []
    for d in range(3):
        x = rng.normal(size=(4, 3)).astype(np.float32)
        x[:, 1] = 7.0  # constant column
        train.append(_make_graph(x, d))
    test = [_make_graph(rng.normal(size=(4, 3)).astype(np.float32), 100)]

    train_norm, test_norm = _apply_graph_norm(train, test, "per_fold")
    for g in train_norm + test_norm:
        assert np.isfinite(g["x"]).all()
