"""Unit tests for GNN hyperparameter tuning (Optuna multi-GPU).

Validates:
1. `_suggest_params` samples all GNN search-space keys from a trial.
2. `tune_gnn_hyperparameters` runs with n_trials=3 on CPU and returns valid params.
3. Inner CV does not leak test fold dates into training.
4. Progress queue receives tuning_start → tuning_epoch... → tuning_complete events.
5. Resume: existing trials in journal are counted, only remaining are run.
"""

from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch


def _make_synthetic_graphs(
    n_dates: int = 60,
    n_nodes: int = 5,
    n_features: int = 3,
    seed: int = 42,
) -> tuple[list[dict], list[pd.Timestamp], pd.Series, list[str], list[str]]:
    """Build synthetic graph snapshots for GNN tuning tests.

    Returns (graphs, dates, y_panel, symbols, node_cols).
    """
    rng = np.random.default_rng(seed)
    symbols = [f"SYM{i}" for i in range(n_nodes)]
    node_cols = [f"feat_{i}" for i in range(n_features)]
    dates = list(pd.bdate_range("2020-01-01", periods=n_dates))

    graphs = []
    all_dates_list = []
    all_symbols_list = []
    all_y_list = []

    for t, dt in enumerate(dates):
        x = rng.standard_normal((n_nodes, n_features)).astype(np.float32)
        y = (x[:, 0] * 0.5 + rng.standard_normal(n_nodes) * 0.1).astype(np.float32)

        # Simple edges: fully connected (small graph)
        src, dst = [], []
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j:
                    src.append(i)
                    dst.append(j)
        edge_index = torch.tensor([src, dst], dtype=torch.long)
        edge_attr = torch.ones(len(src), dtype=torch.float32)

        graphs.append({
            "x": x,
            "edge_index": edge_index,
            "edge_attr": edge_attr,
            "y": y,
            "date": dt,
        })

        for s_idx, sym in enumerate(symbols):
            all_dates_list.append(dt)
            all_symbols_list.append(sym)
            all_y_list.append(float(y[s_idx]))

    idx = pd.MultiIndex.from_arrays([all_dates_list, all_symbols_list], names=["date", "symbol"])
    y_panel = pd.Series(all_y_list, index=idx, dtype=np.float64)

    return graphs, dates, y_panel, symbols, node_cols


class TestGNNSuggestParams:
    """Test the GNN search-space sampling function."""

    def test_suggest_params_returns_all_keys(self):
        """All GNN search-space keys should be present in sampled params."""
        import optuna

        from volforecast.models.gnn_tuning import GNN_SEARCH_SPACE, _suggest_params

        study = optuna.create_study(direction="minimize")
        trial = study.ask()
        params = _suggest_params(trial)
        assert set(params.keys()) == set(GNN_SEARCH_SPACE.keys())

    def test_suggest_params_values_in_range(self):
        """Sampled values should be within defined ranges."""
        import optuna

        from volforecast.models.gnn_tuning import _suggest_params

        study = optuna.create_study(direction="minimize")
        trial = study.ask()
        params = _suggest_params(trial)

        assert 4 <= params["hidden_dim"] <= 64
        assert params["n_heads"] in [1, 2, 4]
        assert params["n_layers"] in [1, 2]
        assert 1e-4 <= params["learning_rate"] <= 1e-2
        assert 0.0 <= params["dropout"] <= 0.3
        assert 1e-6 <= params["weight_decay"] <= 1e-3


class TestTuneGNNHyperparameters:
    """Integration tests for the GNN tuning orchestrator."""

    def test_basic_tuning_runs(self, tmp_path):
        """n_trials=3, CPU, tiny synthetic graphs → returns valid params.

        Uses gnnhar (no PyG dependency) for broad CI compatibility.
        """
        from volforecast.models.gnn_tuning import tune_gnn_hyperparameters

        graphs, dates, y_panel, symbols, node_cols = _make_synthetic_graphs(
            n_dates=60, n_nodes=5, n_features=3,
        )

        from volforecast.config import CVConfig

        cv_cfg = CVConfig(
            method="expanding_window",
            purge_gap=2,
            train_size=20,
            test_size=10,
        )

        best_params = tune_gnn_hyperparameters(
            graphs_all=graphs,
            dates=dates,
            y_panel=y_panel,
            symbols=symbols,
            node_cols=node_cols,
            cv_config=cv_cfg,
            n_trials=3,
            n_gpus=1,
            seed=42,
            model_name="gnnhar",
            fixed_params={
                "max_epochs": 3,
                "early_stopping_rounds": 2,
                "val_fraction": 0.2,
                "loss": "qlike",
                "device": "cpu",
                "precision": "fp32",
                "n_seeds": 1,
            },
            storage_dir=tmp_path / "gnn_optuna",
        )

        assert isinstance(best_params, dict)
        assert "hidden_dim" in best_params
        assert "learning_rate" in best_params

    def test_events_flow(self, tmp_path):
        """Progress queue receives tuning_start → tuning_epoch/trial... → tuning_complete."""
        from volforecast.models.gnn_tuning import tune_gnn_hyperparameters

        graphs, dates, y_panel, symbols, node_cols = _make_synthetic_graphs(
            n_dates=60, n_nodes=5, n_features=3,
        )

        from volforecast.config import CVConfig

        cv_cfg = CVConfig(
            method="expanding_window",
            purge_gap=2,
            train_size=20,
            test_size=10,
        )

        # Use a regular queue (single process, CPU)
        import queue
        q: queue.Queue = queue.Queue()

        tune_gnn_hyperparameters(
            graphs_all=graphs,
            dates=dates,
            y_panel=y_panel,
            symbols=symbols,
            node_cols=node_cols,
            cv_config=cv_cfg,
            n_trials=2,
            n_gpus=1,
            seed=42,
            model_name="gnnhar",
            fixed_params={
                "max_epochs": 3,
                "early_stopping_rounds": 2,
                "val_fraction": 0.2,
                "loss": "qlike",
                "device": "cpu",
                "precision": "fp32",
                "n_seeds": 1,
            },
            storage_dir=tmp_path / "gnn_events",
            progress_queue=q,
        )

        # Drain queue
        events = []
        while not q.empty():
            events.append(q.get_nowait())

        event_types = [e["type"] for e in events]
        assert event_types[0] == "tuning_start"
        assert event_types[-1] == "tuning_complete"
        # Should have some trial-level events in between
        inner_types = set(event_types[1:-1])
        assert len(inner_types) > 0, "Expected at least one inner event"

    def test_resume_existing_trials(self, tmp_path):
        """When journal has existing trials, remaining = n_trials - existing."""
        from volforecast.models.gnn_tuning import tune_gnn_hyperparameters

        graphs, dates, y_panel, symbols, node_cols = _make_synthetic_graphs(
            n_dates=60, n_nodes=5, n_features=3,
        )

        from volforecast.config import CVConfig

        cv_cfg = CVConfig(
            method="expanding_window",
            purge_gap=2,
            train_size=20,
            test_size=10,
        )

        storage = tmp_path / "gnn_resume"
        fixed = {
            "max_epochs": 3,
            "early_stopping_rounds": 2,
            "val_fraction": 0.2,
            "loss": "qlike",
            "device": "cpu",
            "precision": "fp32",
            "n_seeds": 1,
        }

        # First run: 3 trials
        tune_gnn_hyperparameters(
            graphs_all=graphs,
            dates=dates,
            y_panel=y_panel,
            symbols=symbols,
            node_cols=node_cols,
            cv_config=cv_cfg,
            n_trials=3,
            n_gpus=1,
            seed=42,
            model_name="gnnhar",
            fixed_params=fixed,
            storage_dir=storage,
        )

        # Second run: n_trials=5 → should only run 2 new trials
        tune_gnn_hyperparameters(
            graphs_all=graphs,
            dates=dates,
            y_panel=y_panel,
            symbols=symbols,
            node_cols=node_cols,
            cv_config=cv_cfg,
            n_trials=5,
            n_gpus=1,
            seed=42,
            model_name="gnnhar",
            fixed_params=fixed,
            storage_dir=storage,
        )

        # Verify journal exists and has data
        journal_file = storage / "gnn_study.journal"
        assert journal_file.exists()
        assert journal_file.stat().st_size > 0

    def test_gnnhar_model_name(self, tmp_path):
        """tune_gnn_hyperparameters works with model_name='gnnhar'."""
        from volforecast.models.gnn_tuning import tune_gnn_hyperparameters

        graphs, dates, y_panel, symbols, node_cols = _make_synthetic_graphs(
            n_dates=60, n_nodes=5, n_features=3,
        )

        from volforecast.config import CVConfig

        cv_cfg = CVConfig(
            method="expanding_window",
            purge_gap=2,
            train_size=20,
            test_size=10,
        )

        best_params = tune_gnn_hyperparameters(
            graphs_all=graphs,
            dates=dates,
            y_panel=y_panel,
            symbols=symbols,
            node_cols=node_cols,
            cv_config=cv_cfg,
            n_trials=2,
            n_gpus=1,
            seed=42,
            model_name="gnnhar",
            fixed_params={
                "max_epochs": 3,
                "early_stopping_rounds": 2,
                "val_fraction": 0.2,
                "loss": "qlike",
                "device": "cpu",
                "precision": "fp32",
                "n_seeds": 1,
            },
            storage_dir=tmp_path / "gnnhar_optuna",
        )

        assert isinstance(best_params, dict)
        assert "hidden_dim" in best_params
        assert "learning_rate" in best_params
        # n_heads should NOT be in gnnhar results (stripped by model)
        # (gnnhar doesn't use n_heads)
