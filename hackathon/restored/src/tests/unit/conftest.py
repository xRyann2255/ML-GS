"""Unit test configuration.

Autouse isolation fixtures keep unit tests from polluting the real workspace
(e.g. the per-fold LSTM training cache under ``data/models/lstm_cache``).

Also provides shared graph-dict fixtures for GNN model tests (Plans 03–07).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _isolate_fold_cache(tmp_path_factory, monkeypatch):
    """Redirect the fold-cache default root to a per-test tmp directory.

    Tests that don't explicitly set ``ExperimentConfig.fold_cache_dir`` would
    otherwise read/write under the real ``data/models/lstm_cache``. That
    causes flakiness: artifacts persist across runs and re-trigger cache HITs
    in tests that depend on ``model.fit`` being called.
    """
    tmp_root: Path = tmp_path_factory.mktemp("fold_cache_isolated")

    from volforecast.pipeline import fold_cache as _fc

    def _isolated_resolve(config=None, cache_root=None):
        if cache_root is not None:
            return Path(cache_root)
        if config is not None and getattr(config, "fold_cache_dir", None):
            return Path(config.fold_cache_dir)
        return tmp_root

    monkeypatch.setattr(_fc, "resolve_cache_root", _isolated_resolve)


# ---------------------------------------------------------------------------
# Shared graph-dict fixtures for GNN model tests (Plans 03–07)
# ---------------------------------------------------------------------------

torch = pytest.importorskip("torch")


def _mk_graph(x, y, edges, weights, date):
    """Build a single graph-dict in the Plan-02 format."""
    return {
        "x": np.asarray(x, dtype=np.float32),
        "edge_index": torch.tensor(edges, dtype=torch.long).reshape(2, -1),
        "edge_attr": torch.tensor(weights, dtype=torch.float32),
        "y": np.asarray(y, dtype=np.float64),
        "date": date,
    }


@pytest.fixture
def identity_graphs():
    """60 dates x 3 nodes, no edges; y = alpha_i + 0.6*x0 + 0.2*x1 + eps."""
    rng = np.random.default_rng(42)
    alphas = np.array([-1.0, 0.0, 1.0])
    graphs = []
    for t in range(60):
        x = rng.normal(size=(3, 2))
        y = alphas + 0.6 * x[:, 0] + 0.2 * x[:, 1] + rng.normal(0, 0.01, 3)
        graphs.append(
            _mk_graph(
                x, y, [[], []], [], pd.Timestamp("2024-01-01") + pd.Timedelta(days=t)
            )
        )
    return graphs


@pytest.fixture
def spillover_graphs():
    """Ring graph (4 nodes); y depends on own x AND neighbor aggregate with gamma=0.3."""
    rng = np.random.default_rng(7)
    n = 4
    edges = [[0, 1, 1, 2, 2, 3, 3, 0], [1, 0, 2, 1, 3, 2, 0, 3]]
    w = [1.0] * 8
    graphs = []
    for t in range(200):
        x = rng.normal(size=(n, 1))
        a = np.zeros((n, n))
        a[edges[0], edges[1]] = 1.0
        deg = a.sum(1)
        wn = (a / np.sqrt(deg)[:, None]) / np.sqrt(deg)[None, :]
        y = 0.5 * x[:, 0] + 0.3 * (wn @ x)[:, 0] + rng.normal(0, 0.01, n)
        graphs.append(
            _mk_graph(
                x, y, edges, w, pd.Timestamp("2024-01-01") + pd.Timedelta(days=t)
            )
        )
    return graphs
