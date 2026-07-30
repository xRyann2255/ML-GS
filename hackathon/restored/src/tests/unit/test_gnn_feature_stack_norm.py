"""Tests for per-fold graph normalisation in _make_gnn_feature_stack_fn (plan-102 execute-3).

The feature-stack GNN path pre-builds graph snapshots once and returns a callable
fn(train_idx, test_idx, h) that trains a GNN per fold. This test asserts the
callable routes train/test graphs through _apply_graph_norm before training,
using config.graph.graph_norm_mode. Both sequential and parallel dispatch
branches should honour the setting; here we exercise the sequential branch
(n_gpus=1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.config import (
    ExperimentConfig,
    FeatureStackConfig,
    GraphConfig,
    ModelConfig,
)
from volforecast.pipeline import runner as runner_module
from volforecast.pipeline.runner import Pipeline
from volforecast.registry import MODEL_REGISTRY


class _StubGNN:
    """Minimal stand-in for a graph model.

    Records the graphs it saw during fit()/extract_features() so tests can
    inspect the node features that reached the model.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.fit_graphs: list = []
        self.extract_graphs: list = []

    def fit(self, graphs, **kwargs):
        self.fit_graphs = list(graphs)

    def extract_features(self, graphs, outputs=None):
        self.extract_graphs = list(graphs)
        n_total = sum(g["x"].shape[0] for g in graphs)
        # Return one column per requested output.
        return {(outputs or ["prediction"])[0]: np.zeros(n_total, dtype=np.float32)}


@pytest.fixture
def stub_scaffolding(monkeypatch):
    """Register a stub GNN model + neuter external panel-returns/OHLCV I/O."""
    monkeypatch.setitem(MODEL_REGISTRY, "stub_gnn", _StubGNN)

    # panel_returns_from_ohlcv is imported inside _make_gnn_feature_stack_fn
    # via `from volforecast.models.gnn_adjacency import ...`, so patch at source.
    monkeypatch.setattr(
        "volforecast.models.gnn_adjacency.panel_returns_from_ohlcv",
        lambda *args, **kwargs: pd.DataFrame(),
    )


def _build_synthetic_panel(seed: int = 0):
    """3 dates × 2 symbols × 3 features — cheap enough for CI, big enough to fit a scaler."""
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    symbols = ["AAA", "BBB"]
    mi = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    rng = np.random.default_rng(seed)
    features = ["log_rv_d", "log_rv_w", "log_rv_m"]
    X_panel = pd.DataFrame(
        rng.normal(size=(len(mi), len(features))).astype(np.float32),
        index=mi,
        columns=features,
    )
    y_panel = pd.Series(
        rng.normal(size=len(mi)).astype(np.float32),
        index=mi,
        name="target",
    )
    return X_panel, y_panel


def _make_pipeline(graph_norm_mode: str) -> Pipeline:
    config = ExperimentConfig(
        name="gnn-feature-stack-norm-test",
        universe=["AAA", "BBB"],
        date_range=("2024-01-01", "2024-01-31"),
        horizons=[1],
        feature_layers=[],
        model=ModelConfig(name="stub_gnn", params={}),
        graph=GraphConfig(graph_norm_mode=graph_norm_mode),
    )
    return Pipeline(config)


def _make_fs_cfg() -> FeatureStackConfig:
    return FeatureStackConfig(
        source_model="stub_gnn",
        outputs=["prediction"],
        model_params={},
    )


def test_feature_stack_gnn_invokes_apply_graph_norm_with_per_fold(stub_scaffolding, monkeypatch):
    """When graph_norm_mode='per_fold', the fold callback must call _apply_graph_norm('per_fold')."""
    X_panel, y_panel = _build_synthetic_panel()
    pipeline = _make_pipeline(graph_norm_mode="per_fold")
    fs_cfg = _make_fs_cfg()

    calls: list[tuple[int, int, str]] = []
    orig = runner_module._apply_graph_norm

    def recorder(train_graphs, test_graphs, mode):
        calls.append((len(train_graphs), len(test_graphs), mode))
        return orig(train_graphs, test_graphs, mode)

    monkeypatch.setattr(runner_module, "_apply_graph_norm", recorder)

    fold_fn = pipeline._make_gnn_feature_stack_fn(
        X_panel=X_panel,
        y_panel=y_panel,
        sym_seqs={},
        h=1,
        fs_cfg=fs_cfg,
    )
    assert fold_fn is not None

    # 2 dates train, 1 date test — indices are (date, symbol) row order.
    train_idx = np.array([0, 1, 2, 3])
    test_idx = np.array([4, 5])
    result = fold_fn(train_idx, test_idx, 1)

    assert result is not None, "fold callback returned None with valid inputs"
    assert len(calls) == 1, f"expected exactly one _apply_graph_norm call, got {len(calls)}"
    n_train, n_test, mode = calls[0]
    assert mode == "per_fold"
    assert n_train == 2, f"expected 2 train graphs (2 dates), got {n_train}"
    assert n_test == 1, f"expected 1 test graph (1 date), got {n_test}"


def test_feature_stack_gnn_invokes_apply_graph_norm_with_none(stub_scaffolding, monkeypatch):
    """When graph_norm_mode='none', the fold callback must still route through the helper (which is a no-op in that mode)."""
    X_panel, y_panel = _build_synthetic_panel(seed=1)
    pipeline = _make_pipeline(graph_norm_mode="none")
    fs_cfg = _make_fs_cfg()

    calls: list[str] = []
    orig = runner_module._apply_graph_norm

    def recorder(train_graphs, test_graphs, mode):
        calls.append(mode)
        return orig(train_graphs, test_graphs, mode)

    monkeypatch.setattr(runner_module, "_apply_graph_norm", recorder)

    fold_fn = pipeline._make_gnn_feature_stack_fn(
        X_panel=X_panel,
        y_panel=y_panel,
        sym_seqs={},
        h=1,
        fs_cfg=fs_cfg,
    )
    assert fold_fn is not None

    train_idx = np.array([0, 1, 2, 3])
    test_idx = np.array([4, 5])
    fold_fn(train_idx, test_idx, 1)

    assert calls == ["none"], f"expected single 'none' call, got {calls}"


def test_feature_stack_gnn_train_node_features_zero_mean_under_per_fold(stub_scaffolding):
    """End-to-end: the model actually receives z-scored train graphs when per_fold is on."""
    X_panel, y_panel = _build_synthetic_panel(seed=2)
    # Shift features so raw mean is clearly nonzero (so passing test isn't trivial).
    X_panel = X_panel + 5.0

    # Capture the model instance the fold uses so we can inspect its fit_graphs.
    captured: dict[str, _StubGNN] = {}

    class _CapturingStubGNN(_StubGNN):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            captured["last"] = self

    import volforecast.pipeline.runner as _rm
    from volforecast.registry import MODEL_REGISTRY as _REG
    _REG["stub_gnn"] = _CapturingStubGNN
    try:
        pipeline = _make_pipeline(graph_norm_mode="per_fold")
        fs_cfg = _make_fs_cfg()

        fold_fn = pipeline._make_gnn_feature_stack_fn(
            X_panel=X_panel,
            y_panel=y_panel,
            sym_seqs={},
            h=1,
            fs_cfg=fs_cfg,
        )
        assert fold_fn is not None

        train_idx = np.array([0, 1, 2, 3])
        test_idx = np.array([4, 5])
        fold_fn(train_idx, test_idx, 1)

        model = captured["last"]
        assert model.fit_graphs, "stub model was never called with train graphs"
        stacked_train = np.concatenate([g["x"] for g in model.fit_graphs], axis=0)
        # After z-scoring, per-feature mean ≈ 0 across the train graphs.
        assert np.allclose(stacked_train.mean(axis=0), 0.0, atol=1e-4), (
            f"train node features not centred: mean={stacked_train.mean(axis=0)}"
        )
    finally:
        _REG.pop("stub_gnn", None)
        _ = _rm  # silence unused
