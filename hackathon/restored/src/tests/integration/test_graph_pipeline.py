"""End-to-end integration test: native GNN model through run_pooled."""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from volforecast.config import CVConfig, ExperimentConfig, GraphConfig, ModelConfig
from volforecast.pipeline.runner import Pipeline

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_real_gnn_end_to_end(graph_panel_data_module):
    """Run the real GATv2 GNNVolModel end-to-end through the native graph path."""
    cfg = ExperimentConfig(
        name="it_gnn_native", universe=["AAA", "BBB", "CCC"],
        date_range=("2022-01-03", "2023-03-31"), horizons=[1],
        feature_layers=["har_core", "asymmetry"],
        model=ModelConfig(name="gnn", params={
            "hidden_dim": 8, "n_heads": 2, "max_epochs": 3,
            "early_stopping_rounds": 3, "device": "cpu", "loss": "qlike",
        }),
        cv=CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=60),
        graph=GraphConfig(method="corr", input="log_rv", window=60,
                          refit_every=21, params={"threshold": 0.2}),
        fold_cache_enabled=False, checkpoint_enabled=False,
    )
    results = Pipeline(cfg).run_pooled(graph_panel_data_module)
    res = results[1]
    assert np.isfinite(res["metrics"]["qlike"])
    assert len(res["predictions"]) > 100
    assert res["predictions"].std() > 0  # not a constant predictor
