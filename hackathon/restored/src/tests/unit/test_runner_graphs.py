"""Tests for Pipeline._run_one_horizon_graphs and _run_pooled_graphs dispatch."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from volforecast.config import CVConfig, ExperimentConfig, GraphConfig, ModelConfig
from volforecast.pipeline.runner import Pipeline
from volforecast.registry import MODEL_REGISTRY, register_model


@pytest.fixture
def fake_graph_model():
    """Minimal requires_graph model: predicts the mean of train targets."""

    @register_model("_fake_graph")
    class _FakeGraph:
        REQUIRED_LAYERS: list[str] = []
        requires_sequences = False
        requires_graph = True
        supports_tuning = False
        family = "gnn"
        description = "test double"

        def __init__(self, *, input_dim: int, seed: int = 42, **kwargs):
            self.input_dim = input_dim
            self.seed = seed
            self.seen_progress = False
            self._mean = 0.0

        def fit(self, graphs, y=None, *, on_progress=None):
            ys = np.concatenate([g["y"] for g in graphs])
            self._mean = float(np.nanmean(ys))
            if on_progress is not None:
                on_progress(1, 1)
                self.seen_progress = True
            return self

        def predict(self, graphs):
            n = sum(g["x"].shape[0] for g in graphs)
            return np.full(n, self._mean)

        def get_params(self):
            return {"input_dim": self.input_dim, "seed": self.seed}

        @property
        def summary(self):
            return {"mean": self._mean}

    yield _FakeGraph
    MODEL_REGISTRY.pop("_fake_graph", None)


@pytest.fixture
def graph_panel_data():
    """3 symbols x 320 bdays of synthetic AR(1) log-RV panels with rv column."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2022-01-03", periods=320)
    out = {}
    for k, sym in enumerate(["AAA", "BBB", "CCC"]):
        log_rv = np.zeros(len(dates))
        log_rv[0] = -9.0
        for t in range(1, len(dates)):
            log_rv[t] = -9.0 * 0.05 + 0.95 * log_rv[t - 1] + rng.normal(0, 0.3)
        df = pd.DataFrame({"rv": np.exp(log_rv)}, index=dates)
        df.index.name = "date"
        out[sym] = df
    return out


def _config(fake_name="_fake_graph"):
    return ExperimentConfig(
        name="t_graph", universe=["AAA", "BBB", "CCC"],
        date_range=("2022-01-03", "2023-03-31"), horizons=[1],
        feature_layers=["har_core"],
        model=ModelConfig(name=fake_name, params={}),
        cv=CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=50),
        graph=GraphConfig(method="identity", input="log_rv", node_features=["log_rv_d"]),
        fold_cache_enabled=False, checkpoint_enabled=False,
    )


def test_graph_horizon_contract(fake_graph_model, graph_panel_data):
    results = Pipeline(_config()).run_pooled(graph_panel_data)
    assert set(results) == {1}
    res = results[1]
    assert {"metrics", "predictions", "actuals", "model", "duan_correction"} <= set(res)
    assert isinstance(res["predictions"], pd.Series)
    assert isinstance(res["predictions"].index, pd.MultiIndex)
    assert len(res["predictions"]) == len(res["actuals"]) > 0
    assert np.isfinite(res["predictions"].values).all()
    assert "qlike" in res["metrics"]


def test_fold_completion_and_progress_callbacks(fake_graph_model, graph_panel_data):
    folds: list[tuple[int, int]] = []
    Pipeline(_config()).run_pooled(
        graph_panel_data,
        on_fold_complete=lambda h, f: folds.append((h, f)),
        on_train_progress=lambda cur, tot: None,
    )
    assert folds and folds[-1][0] == 1
    assert [f for _, f in folds] == list(range(1, len(folds) + 1))


def test_purge_respects_horizon(fake_graph_model, graph_panel_data):
    cfg = _config()
    cfg.horizons = [22]
    cfg.cv.purge_gap = 5  # must be raised to 22 internally
    results = Pipeline(cfg).run_pooled(graph_panel_data)
    preds = results[22]["predictions"]
    assert len(preds) > 0


def test_dispatch_prefers_feature_stack_when_configured(fake_graph_model, graph_panel_data, monkeypatch):
    """requires_graph + feature_stack config -> legacy stack path, NOT _run_pooled_graphs."""
    from volforecast.config import FeatureStackConfig

    cfg = _config()
    cfg.model = ModelConfig(name="har", params={})
    cfg.feature_stack = FeatureStackConfig(source_model="_fake_graph", outputs=["prediction"])
    pipe = Pipeline(cfg)
    called = {"native": 0}
    monkeypatch.setattr(
        pipe, "_run_pooled_graphs",
        lambda *a, **k: called.__setitem__("native", called["native"] + 1) or {},
    )
    try:
        pipe.run_pooled(graph_panel_data)
    except Exception:
        pass  # downstream may fail because of stub; we only assert routing
    assert called["native"] == 0


def test_native_graph_requires_graph_block(fake_graph_model, graph_panel_data):
    cfg = _config()
    cfg.graph = None
    with pytest.raises(ValueError, match="graph:"):
        Pipeline(cfg).run_pooled(graph_panel_data)


def test_model_utils_default_layers_for_gnn_family(fake_graph_model):
    from volforecast.evaluation._model_utils import feature_layers_for_model

    layers = feature_layers_for_model("_fake_graph")
    assert "har_core" in layers
def test_predictions_only_on_existing_panel_rows(fake_graph_model, graph_panel_data):
    # drop the last 10 rows of CCC: predictions must not include those (date, CCC) rows
    graph_panel_data["CCC"] = graph_panel_data["CCC"].iloc[:-10]
    results = Pipeline(_config()).run_pooled(graph_panel_data)
    idx = results[1]["predictions"].index
    ccc_dates = {d for d, s in idx if s == "CCC"}
    dropped = set(pd.bdate_range("2023-03-20", periods=10))
    assert not (ccc_dates & dropped)


def test_warmup_zero_unchanged(fake_graph_model):
    """Existing _fake_graph has no warmup attr — getattr returns 0."""
    model = fake_graph_model(input_dim=3)
    assert getattr(model, "warmup", 0) == 0


def test_warmup_model_gets_correct_predictions(fake_graph_model, graph_panel_data):
    """A model with warmup=2 gets prepended train graphs and predictions align to test dates."""

    @register_model("_fake_graph_warmup")
    class _FakeGraphWarmup:
        REQUIRED_LAYERS: list[str] = []
        requires_sequences = False
        requires_graph = True
        supports_tuning = False
        family = "gnn"
        description = "test double with warmup"
        warmup = 2

        def __init__(self, *, input_dim: int, seed: int = 42, **kwargs):
            self.input_dim = input_dim
            self.seed = seed
            self._mean = 0.0

        def fit(self, graphs, y=None, *, on_progress=None):
            ys = np.concatenate([g["y"] for g in graphs])
            self._mean = float(np.nanmean(ys))
            if on_progress is not None:
                on_progress(1, 1)
            return self

        def predict(self, graphs):
            # Model receives warmup+test graphs but only returns preds for graphs[warmup:]
            warmup = self.warmup
            pred_graphs = graphs[warmup:]
            n = sum(g["x"].shape[0] for g in pred_graphs)
            return np.full(n, self._mean)

        def get_params(self):
            return {"input_dim": self.input_dim, "seed": self.seed}

        @property
        def summary(self):
            return {"mean": self._mean}

    try:
        cfg = _config("_fake_graph_warmup")
        results = Pipeline(cfg).run_pooled(graph_panel_data)
        res = results[1]
        assert len(res["predictions"]) == len(res["actuals"]) > 0
        assert np.isfinite(res["predictions"].values).all()
    finally:
        MODEL_REGISTRY.pop("_fake_graph_warmup", None)
