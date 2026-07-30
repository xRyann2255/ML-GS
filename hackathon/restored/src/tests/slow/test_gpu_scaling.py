"""Slow GPU scaling tests — require real CUDA devices.

Skipped entirely without >=2 CUDA-capable GPUs.
Run explicitly with: ./vol test tests/slow/test_gpu_scaling.py -x
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

pytestmark = pytest.mark.slow


def _make_synthetic_graphs(n_dates=200, n_symbols=10, n_features=5, seed=42):
    """Build a moderately sized synthetic graph dataset for scaling tests."""
    rng = np.random.default_rng(seed)
    graphs = []
    for t in range(n_dates):
        x = rng.normal(size=(n_symbols, n_features)).astype(np.float32)
        y = 0.5 * x[:, 0] + 0.2 * x[:, 1] + rng.normal(0, 0.1, n_symbols)
        edges = [[i, j] for i in range(n_symbols) for j in range(n_symbols) if i != j]
        ei = np.array(edges).T
        graphs.append({
            "x": x,
            "y": y.astype(np.float64),
            "edge_index": torch.tensor(ei, dtype=torch.long),
            "edge_attr": torch.ones(ei.shape[1], dtype=torch.float32),
            "date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=t),
        })
    return graphs


@pytest.mark.skipif(
    not torch.cuda.is_available() or torch.cuda.device_count() < 2,
    reason="Requires >=2 CUDA devices",
)
class TestGPUScaling:
    """Verify multi-GPU parallel path is faster than sequential."""

    def test_parallel_faster_than_sequential(self):
        """n_gpus=4 wall time < 0.6x of n_gpus=1 on a synthetic multi-fold run."""
        from unittest.mock import MagicMock

        from volforecast.pipeline.runner import Pipeline

        n_symbols = 10
        n_features = 5
        n_dates = 200
        graphs = _make_synthetic_graphs(n_dates=n_dates, n_symbols=n_symbols, n_features=n_features)

        dates = [g["date"] for g in graphs]
        by_date = dict(zip(dates, graphs))

        # Build panel
        symbols = [f"SYM{i}" for i in range(n_symbols)]
        idx = pd.MultiIndex.from_product(
            [pd.DatetimeIndex(dates), symbols], names=["date", "symbol"]
        )
        rng = np.random.default_rng(99)
        X = pd.DataFrame(
            rng.normal(size=(len(idx), n_features)).astype(np.float32),
            index=idx,
            columns=[f"feat_{i}" for i in range(n_features)],
        )
        y = pd.Series(rng.normal(-8, 0.5, len(idx)).astype(np.float64), index=idx)

        model_params = {
            "input_dim": n_features,
            "hidden_dim": 16,
            "n_heads": 2,
            "n_layers": 2,
            "max_epochs": 20,
            "device": "auto",
            "seed": 42,
        }

        # 12-fold CV splits
        n_per_date = n_symbols
        fold_splits = []
        fold_size = (n_dates - 50) // 12
        for i in range(12):
            train_end = (50 + i * fold_size) * n_per_date
            test_end = min((50 + (i + 1) * fold_size) * n_per_date, n_dates * n_per_date)
            fold_splits.append(
                (np.arange(0, train_end), np.arange(train_end, test_end))
            )

        def _make_pipeline(n_gpus):
            pipeline = object.__new__(Pipeline)
            pipeline.config = MagicMock()
            pipeline.config.fold_cache_enabled = False
            pipeline.config.fold_cache_dir = None
            pipeline.config.seed = 42
            pipeline.config.n_gpus = n_gpus
            pipeline.config.universe = symbols
            pipeline.config.model = MagicMock()
            pipeline.config.model.name = "gnn"
            pipeline.config.tuning = None
            pipeline.config.model_params_for_horizon = MagicMock(return_value=model_params)
            return pipeline

        def _make_cv():
            cv = MagicMock()
            cv.split = MagicMock(return_value=list(fold_splits))
            return cv

        # Sequential (n_gpus=1)
        pipeline_seq = _make_pipeline(n_gpus=1)
        t0 = time.perf_counter()
        pipeline_seq._run_graphs_gpu_parallel(
            graphs_all=graphs,
            dates=dates,
            by_date=by_date,
            X_panel=X,
            y_panel=y,
            cv=_make_cv(),
            model_params=model_params,
            symbols=symbols,
            h=1,
        )
        seq_time = time.perf_counter() - t0

        # Parallel (n_gpus=4)
        n_gpus = min(4, torch.cuda.device_count())
        pipeline_par = _make_pipeline(n_gpus=n_gpus)
        t0 = time.perf_counter()
        pipeline_par._run_graphs_gpu_parallel(
            graphs_all=graphs,
            dates=dates,
            by_date=by_date,
            X_panel=X,
            y_panel=y,
            cv=_make_cv(),
            model_params=model_params,
            symbols=symbols,
            h=1,
        )
        par_time = time.perf_counter() - t0

        # Parallel should be meaningfully faster
        assert par_time < 0.6 * seq_time, (
            f"Parallel ({n_gpus} GPUs) took {par_time:.1f}s, "
            f"sequential took {seq_time:.1f}s — expected <60% ratio"
        )
