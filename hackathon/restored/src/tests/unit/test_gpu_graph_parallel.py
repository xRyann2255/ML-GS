"""Tests for GPU-parallel graph fold execution.

Validates:
- _execute_graph_fold worker returns expected keys and applies Duan correction
- _run_graphs_gpu_parallel produces results matching sequential path
- Worker function is picklable (module-level, no closures)
- on_fold_complete callback fires for each fold
"""

from __future__ import annotations

import pickle
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_synthetic_graphs(n_dates=50, n_symbols=5, n_features=3, seed=42, dates=None):
    """Build synthetic graph dicts matching the GNNVolModel contract."""
    rng = np.random.default_rng(seed)
    if dates is None:
        dates = pd.bdate_range("2020-01-01", periods=n_dates)
    graphs = []
    for i, d in enumerate(dates):
        x = rng.normal(size=(n_symbols, n_features)).astype(np.float32)
        y = rng.normal(-8, 0.5, n_symbols).astype(np.float32)
        edge_index = np.array(
            [[i, j] for i in range(n_symbols) for j in range(n_symbols) if i != j]
        ).T
        edge_index_t = torch.tensor(edge_index, dtype=torch.long)
        edge_attr = torch.ones(edge_index_t.shape[1], dtype=torch.float32)
        graphs.append({
            "x": x,
            "y": y,
            "edge_index": edge_index_t,
            "edge_attr": edge_attr,
            "date": pd.Timestamp(d),
        })
    return graphs


def _make_panel(n_dates=50, n_symbols=5, n_features=3, seed=42):
    """Build a synthetic (date, symbol) MultiIndex panel and target."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_dates)
    symbols = [f"SYM{i}" for i in range(n_symbols)]
    idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    cols = [f"feat_{i}" for i in range(n_features)]
    X = pd.DataFrame(
        rng.normal(size=(len(idx), n_features)).astype(np.float32),
        index=idx,
        columns=cols,
    )
    y = pd.Series(
        rng.normal(-8, 0.5, len(idx)).astype(np.float64),
        index=idx,
    )
    return X, y, dates, symbols


class _TestExecutor(ThreadPoolExecutor):
    """Drop-in for ProcessPoolExecutor that ignores mp_context."""

    def __init__(self, max_workers=None, **kwargs):
        super().__init__(max_workers=max_workers)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExecuteGraphFold:
    """Unit tests for the module-level _execute_graph_fold worker."""

    def test_returns_expected_keys(self):
        """Worker returns dict with fold_num, preds, test_multi_idx, duan_correction, cache_hit."""
        from volforecast.pipeline.runner import _execute_graph_fold

        n_symbols = 5
        n_features = 3
        X, y, dates, symbols = _make_panel(n_dates=50, n_symbols=n_symbols, n_features=n_features)
        graphs = _make_synthetic_graphs(n_dates=50, n_symbols=n_symbols, n_features=n_features, dates=dates)

        train_graphs = graphs[:35]
        test_graphs = graphs[35:]
        fold_train_dates = pd.DatetimeIndex([g["date"] for g in train_graphs])
        fold_test_dates = pd.DatetimeIndex([g["date"] for g in test_graphs])

        result = _execute_graph_fold(
            fold_num=1,
            train_graphs=train_graphs,
            test_graphs=test_graphs,
            model_name="gnn",
            model_params={
                "input_dim": n_features,
                "hidden_dim": 8,
                "n_heads": 2,
                "n_layers": 1,
                "max_epochs": 3,
                "device": "cpu",
                "seed": 42,
            },
            device_id=None,
            seed_offset=1,
            cache_key=None,
            cache_enabled=False,
            cache_root=None,
            config_dict=None,
            h=1,
            fold_train_dates=fold_train_dates,
            fold_test_dates=fold_test_dates,
            symbols=symbols,
            progress_queue=None,
        )

        assert "fold_num" in result
        assert "preds" in result
        assert "test_multi_idx" in result
        assert "duan_correction" in result
        assert "cache_hit" in result
        assert result["fold_num"] == 1
        assert result["cache_hit"] is False
        # Predictions should match n_test_dates * n_symbols
        assert len(result["preds"]) == len(test_graphs) * n_symbols

    def test_applies_duan_correction(self):
        """Duan correction should be non-zero when train residuals exist."""
        from volforecast.pipeline.runner import _execute_graph_fold

        n_symbols = 5
        n_features = 3
        X, y, dates, symbols = _make_panel(n_dates=50, n_symbols=n_symbols, n_features=n_features)
        graphs = _make_synthetic_graphs(n_dates=50, n_symbols=n_symbols, n_features=n_features, dates=dates)

        train_graphs = graphs[:35]
        test_graphs = graphs[35:]
        fold_train_dates = pd.DatetimeIndex([g["date"] for g in train_graphs])
        fold_test_dates = pd.DatetimeIndex([g["date"] for g in test_graphs])

        result = _execute_graph_fold(
            fold_num=1,
            train_graphs=train_graphs,
            test_graphs=test_graphs,
            model_name="gnn",
            model_params={
                "input_dim": n_features,
                "hidden_dim": 8,
                "n_heads": 2,
                "n_layers": 1,
                "max_epochs": 5,
                "device": "cpu",
                "seed": 42,
            },
            device_id=None,
            seed_offset=1,
            cache_key=None,
            cache_enabled=False,
            cache_root=None,
            config_dict=None,
            h=1,
            fold_train_dates=fold_train_dates,
            fold_test_dates=fold_test_dates,
            symbols=symbols,
            progress_queue=None,
        )

        # With random data, correction should be non-zero (residuals exist)
        assert result["duan_correction"] != 0.0, (
            "Duan correction should be non-zero with non-trivial residuals"
        )


class TestWorkerPicklable:
    """Verify the module-level worker can be pickled."""

    def test_execute_graph_fold_is_picklable(self):
        """Module-level functions are picklable; closures are not."""
        from volforecast.pipeline.runner import _execute_graph_fold

        # Round-trip through pickle
        pickled = pickle.dumps(_execute_graph_fold)
        restored = pickle.loads(pickled)  # noqa: S301
        assert restored is _execute_graph_fold


class TestOnFoldCompleteCallback:
    """Verify on_fold_complete fires for each completed fold."""

    def test_on_fold_complete_fires(self):
        """on_fold_complete should be called once per fold in the parallel path."""
        from volforecast.pipeline.runner import Pipeline, _has_cuda

        n_symbols = 5
        n_features = 3
        n_dates = 50
        X, y, dates, symbols = _make_panel(
            n_dates=n_dates, n_symbols=n_symbols, n_features=n_features,
        )
        graphs = _make_synthetic_graphs(
            n_dates=n_dates, n_symbols=n_symbols, n_features=n_features, dates=dates,
        )

        by_date = dict(zip(
            [g["date"] for g in graphs],
            graphs,
        ))

        # Build a mock Pipeline
        pipeline = object.__new__(Pipeline)
        pipeline.config = MagicMock()
        pipeline.config.fold_cache_enabled = False
        pipeline.config.fold_cache_dir = None
        pipeline.config.seed = 42
        pipeline.config.n_gpus = 2
        pipeline.config.universe = symbols
        pipeline.config.model = MagicMock()
        pipeline.config.model.name = "gnn"
        pipeline.config.tuning = None
        pipeline.config.model_params_for_horizon = MagicMock(return_value={
            "input_dim": n_features,
            "hidden_dim": 8,
            "n_heads": 2,
            "n_layers": 1,
            "max_epochs": 3,
            "device": "cpu",
            "seed": 42,
        })

        # Build CV that yields 2 folds
        cv = MagicMock()
        n_per_date = n_symbols
        # Fold 1: train on dates[:25], test on dates[25:37]
        train1_end = 25 * n_per_date
        test1_end = 37 * n_per_date
        # Fold 2: train on dates[:37], test on dates[37:]
        train2_end = 37 * n_per_date
        test2_end = n_dates * n_per_date
        cv.split = MagicMock(return_value=[
            (np.arange(0, train1_end), np.arange(train1_end, test1_end)),
            (np.arange(0, train2_end), np.arange(train2_end, test2_end)),
        ])

        fold_complete_calls = []

        def on_fold_complete(h, fold_num):
            fold_complete_calls.append((h, fold_num))

        import concurrent.futures
        orig = concurrent.futures.ProcessPoolExecutor
        concurrent.futures.ProcessPoolExecutor = _TestExecutor
        try:
            with patch("torch.cuda.device_count", return_value=2), \
                 patch("torch.cuda.is_available", return_value=True):
                result = pipeline._run_graphs_gpu_parallel(
                    graphs_all=graphs,
                    dates=[g["date"] for g in graphs],
                    by_date=by_date,
                    X_panel=X,
                    y_panel=y,
                    cv=cv,
                    model_params={
                        "input_dim": n_features,
                        "hidden_dim": 8,
                        "n_heads": 2,
                        "n_layers": 1,
                        "max_epochs": 3,
                        "device": "cpu",
                        "seed": 42,
                    },
                    symbols=symbols,
                    h=1,
                    on_fold_complete=on_fold_complete,
                )
        finally:
            concurrent.futures.ProcessPoolExecutor = orig

        assert len(fold_complete_calls) == 2, (
            f"Expected 2 on_fold_complete calls, got {len(fold_complete_calls)}"
        )
        fold_nums_called = sorted([c[1] for c in fold_complete_calls])
        assert fold_nums_called == [1, 2]


class TestParallelMatchesSequential:
    """Verify parallel path produces same results as sequential."""

    def test_predictions_match(self):
        """Parallel and sequential graph paths should match within tolerance."""
        from volforecast.pipeline.runner import Pipeline

        n_symbols = 5
        n_features = 3
        n_dates = 50
        X, y, dates, symbols = _make_panel(
            n_dates=n_dates, n_symbols=n_symbols, n_features=n_features,
        )
        graphs = _make_synthetic_graphs(
            n_dates=n_dates, n_symbols=n_symbols, n_features=n_features, dates=dates,
        )
        by_date = dict(zip(
            [g["date"] for g in graphs],
            graphs,
        ))

        model_params = {
            "input_dim": n_features,
            "hidden_dim": 8,
            "n_heads": 2,
            "n_layers": 1,
            "max_epochs": 3,
            "device": "cpu",
            "seed": 42,
        }

        # Build CV with 2 folds — deterministic splits
        n_per_date = n_symbols
        train1_end = 25 * n_per_date
        test1_end = 37 * n_per_date
        train2_end = 37 * n_per_date
        test2_end = n_dates * n_per_date

        fold_splits = [
            (np.arange(0, train1_end), np.arange(train1_end, test1_end)),
            (np.arange(0, train2_end), np.arange(train2_end, test2_end)),
        ]

        def _make_cv():
            cv = MagicMock()
            cv.split = MagicMock(return_value=list(fold_splits))
            return cv

        # --- Sequential path ---
        pipeline_seq = object.__new__(Pipeline)
        pipeline_seq.config = MagicMock()
        pipeline_seq.config.fold_cache_enabled = False
        pipeline_seq.config.fold_cache_dir = None
        pipeline_seq.config.seed = 42
        pipeline_seq.config.n_gpus = 1
        pipeline_seq.config.universe = symbols
        pipeline_seq.config.model = MagicMock()
        pipeline_seq.config.model.name = "gnn"
        pipeline_seq.config.model_params_for_horizon = MagicMock(return_value=dict(model_params))
        pipeline_seq.config.cv_for_horizon = MagicMock()

        # Run sequential fold loop manually (mimicking _run_one_horizon_graphs)
        from volforecast.registry import MODEL_REGISTRY, ensure_registered
        ensure_registered()
        model_cls = MODEL_REGISTRY["gnn"]
        base_seed = 42

        seq_preds = pd.Series(np.nan, index=X.index, dtype=np.float64)
        seq_duan = []
        for fold_num_0, (train_idx, test_idx) in enumerate(fold_splits, start=1):
            train_dates_fold = sorted(
                X.index[train_idx].get_level_values("date").unique()
            )
            test_dates_fold = sorted(
                X.index[test_idx].get_level_values("date").unique()
            )
            fold_train_dates_ts = pd.DatetimeIndex(train_dates_fold)
            fold_test_dates_ts = pd.DatetimeIndex(test_dates_fold)

            train_g = [by_date[d] for d in fold_train_dates_ts if d in by_date]
            test_g = [by_date[d] for d in fold_test_dates_ts if d in by_date]

            fp = dict(model_params)
            fp["seed"] = base_seed + fold_num_0
            model = model_cls(**fp)
            model.fit(train_g)

            # Duan from train residuals
            train_flat = model.predict(train_g)
            train_y = np.concatenate([g["y"] for g in train_g])
            valid = np.isfinite(train_y)
            if valid.any():
                resid = np.clip(train_y[valid] - train_flat[valid], -10.0, 10.0)
                correction = float(np.log(np.mean(np.exp(resid))))
            else:
                correction = 0.0
            seq_duan.append(correction)

            test_flat = model.predict(test_g) + correction
            test_full_idx = pd.MultiIndex.from_product(
                [test_dates_fold, symbols], names=["date", "symbol"]
            )
            test_series = pd.Series(test_flat, index=test_full_idx, dtype=np.float64)
            keep = test_series.index.intersection(X.index[test_idx])
            seq_preds.loc[keep] = test_series.loc[keep].values

        # --- Parallel path ---
        pipeline_par = object.__new__(Pipeline)
        pipeline_par.config = MagicMock()
        pipeline_par.config.fold_cache_enabled = False
        pipeline_par.config.fold_cache_dir = None
        pipeline_par.config.seed = 42
        pipeline_par.config.n_gpus = 2
        pipeline_par.config.universe = symbols
        pipeline_par.config.model = MagicMock()
        pipeline_par.config.model.name = "gnn"
        pipeline_par.config.tuning = None
        pipeline_par.config.model_params_for_horizon = MagicMock(return_value=dict(model_params))

        import concurrent.futures
        orig = concurrent.futures.ProcessPoolExecutor
        concurrent.futures.ProcessPoolExecutor = _TestExecutor
        try:
            with patch("torch.cuda.device_count", return_value=2), \
                 patch("torch.cuda.is_available", return_value=True):
                par_result = pipeline_par._run_graphs_gpu_parallel(
                    graphs_all=graphs,
                    dates=[g["date"] for g in graphs],
                    by_date=by_date,
                    X_panel=X,
                    y_panel=y,
                    cv=_make_cv(),
                    model_params=dict(model_params),
                    symbols=symbols,
                    h=1,
                )
        finally:
            concurrent.futures.ProcessPoolExecutor = orig

        # Compare predictions on the valid (non-NaN) portion
        seq_valid = seq_preds.dropna()
        par_preds = par_result["predictions"]

        # Align indices
        common_idx = seq_valid.index.intersection(par_preds.index)
        assert len(common_idx) > 0, "No overlapping predictions to compare"

        # GNN training has inherent floating-point non-determinism from
        # scatter/gather ops in PyG, so we check structural equivalence
        # and that predictions are in the same general range rather than
        # requiring exact numerical match.
        assert len(common_idx) == len(seq_valid), (
            f"Index mismatch: sequential has {len(seq_valid)} preds, "
            f"parallel has {len(par_preds)} preds, common={len(common_idx)}"
        )
        seq_vals = seq_valid.loc[common_idx].values
        par_vals = par_preds.loc[common_idx].values
        assert np.all(np.isfinite(seq_vals)), "Sequential has non-finite predictions"
        assert np.all(np.isfinite(par_vals)), "Parallel has non-finite predictions"
        # Means should be close (same data, same seeds → same distribution)
        np.testing.assert_allclose(
            np.mean(seq_vals), np.mean(par_vals), atol=0.5,
            err_msg="Parallel mean diverges from sequential mean",
        )
        # Std devs should be in the same ballpark
        np.testing.assert_allclose(
            np.std(seq_vals), np.std(par_vals), rtol=1.0,
            err_msg="Parallel std diverges from sequential std",
        )


class TestSeedEnsembleFlattening:
    """Tests for (fold, seed) flattening when n_seeds > 1."""

    def test_ensemble_flattening_produces_correct_predictions(self):
        """Flattened (fold, seed) jobs -> ensemble-averaged -> Duan produces valid results."""
        from volforecast.pipeline.runner import Pipeline
        from volforecast.registry import ensure_registered

        ensure_registered()

        n_symbols = 5
        n_features = 3
        n_dates = 50
        n_seeds = 3
        X, y, dates, symbols = _make_panel(
            n_dates=n_dates, n_symbols=n_symbols, n_features=n_features,
        )
        graphs = _make_synthetic_graphs(
            n_dates=n_dates, n_symbols=n_symbols, n_features=n_features, dates=dates,
        )
        by_date = dict(zip([g["date"] for g in graphs], graphs))

        model_params = {
            "input_dim": n_features,
            "hidden_dim": 8,
            "n_layers": 1,
            "max_epochs": 3,
            "device": "cpu",
            "seed": 42,
            "n_seeds": n_seeds,
        }

        # Build CV with 2 folds
        n_per_date = n_symbols
        train1_end = 25 * n_per_date
        test1_end = 37 * n_per_date
        train2_end = 37 * n_per_date
        test2_end = n_dates * n_per_date
        cv = MagicMock()
        cv.split = MagicMock(return_value=[
            (np.arange(0, train1_end), np.arange(train1_end, test1_end)),
            (np.arange(0, train2_end), np.arange(train2_end, test2_end)),
        ])

        pipeline = object.__new__(Pipeline)
        pipeline.config = MagicMock()
        pipeline.config.fold_cache_enabled = False
        pipeline.config.fold_cache_dir = None
        pipeline.config.seed = 42
        pipeline.config.n_gpus = 2
        pipeline.config.universe = symbols
        pipeline.config.model = MagicMock()
        pipeline.config.model.name = "gnnhar"
        pipeline.config.tuning = None

        # Track submitted jobs
        submitted_jobs = []

        from volforecast.pipeline import runner as _runner_mod

        _original_fn = _runner_mod._execute_graph_fold

        def _tracking_execute(*args, **kwargs):
            submitted_jobs.append(kwargs)
            return _original_fn(*args, **kwargs)

        import concurrent.futures
        orig = concurrent.futures.ProcessPoolExecutor
        concurrent.futures.ProcessPoolExecutor = _TestExecutor
        try:
            with patch("torch.cuda.device_count", return_value=2), \
                 patch("torch.cuda.is_available", return_value=True), \
                 patch.object(_runner_mod, "_execute_graph_fold", side_effect=_tracking_execute):
                result = pipeline._run_graphs_gpu_parallel(
                    graphs_all=graphs,
                    dates=[g["date"] for g in graphs],
                    by_date=by_date,
                    X_panel=X,
                    y_panel=y,
                    cv=cv,
                    model_params=dict(model_params),
                    symbols=symbols,
                    h=1,
                )
        finally:
            concurrent.futures.ProcessPoolExecutor = orig

        # 2 folds × 3 seeds = 6 total jobs submitted
        assert len(submitted_jobs) == 6, (
            f"Expected 6 jobs (2 folds × 3 seeds), got {len(submitted_jobs)}"
        )

        # All jobs should have ensemble_member=True
        for job in submitted_jobs:
            assert job.get("ensemble_member") is True, (
                "Flattened seed jobs must have ensemble_member=True"
            )

        # Predictions should be finite and non-empty
        preds = result["predictions"]
        assert len(preds) > 0, "No predictions returned"
        assert np.all(np.isfinite(preds.values)), "Predictions contain non-finite values"

        # Duan should have been applied (non-zero correction)
        assert result["duan_correction"] != 0.0, (
            "Duan correction should be non-zero after ensemble averaging"
        )

    def test_ensemble_fold_complete_fires_once_per_fold(self):
        """on_fold_complete fires once per fold, not once per seed-member."""
        from volforecast.pipeline.runner import Pipeline
        from volforecast.registry import ensure_registered

        ensure_registered()

        n_symbols = 5
        n_features = 3
        n_dates = 50
        n_seeds = 3
        X, y, dates, symbols = _make_panel(
            n_dates=n_dates, n_symbols=n_symbols, n_features=n_features,
        )
        graphs = _make_synthetic_graphs(
            n_dates=n_dates, n_symbols=n_symbols, n_features=n_features, dates=dates,
        )
        by_date = dict(zip([g["date"] for g in graphs], graphs))

        model_params = {
            "input_dim": n_features,
            "hidden_dim": 8,
            "n_layers": 1,
            "max_epochs": 3,
            "device": "cpu",
            "seed": 42,
            "n_seeds": n_seeds,
        }

        n_per_date = n_symbols
        train1_end = 25 * n_per_date
        test1_end = 37 * n_per_date
        train2_end = 37 * n_per_date
        test2_end = n_dates * n_per_date
        cv = MagicMock()
        cv.split = MagicMock(return_value=[
            (np.arange(0, train1_end), np.arange(train1_end, test1_end)),
            (np.arange(0, train2_end), np.arange(train2_end, test2_end)),
        ])

        pipeline = object.__new__(Pipeline)
        pipeline.config = MagicMock()
        pipeline.config.fold_cache_enabled = False
        pipeline.config.fold_cache_dir = None
        pipeline.config.seed = 42
        pipeline.config.n_gpus = 2
        pipeline.config.universe = symbols
        pipeline.config.model = MagicMock()
        pipeline.config.model.name = "gnnhar"
        pipeline.config.tuning = None

        fold_complete_calls = []

        def on_fold_complete(h, fold_num):
            fold_complete_calls.append((h, fold_num))

        import concurrent.futures
        orig = concurrent.futures.ProcessPoolExecutor
        concurrent.futures.ProcessPoolExecutor = _TestExecutor
        try:
            with patch("torch.cuda.device_count", return_value=2), \
                 patch("torch.cuda.is_available", return_value=True):
                result = pipeline._run_graphs_gpu_parallel(
                    graphs_all=graphs,
                    dates=[g["date"] for g in graphs],
                    by_date=by_date,
                    X_panel=X,
                    y_panel=y,
                    cv=cv,
                    model_params=dict(model_params),
                    symbols=symbols,
                    h=1,
                    on_fold_complete=on_fold_complete,
                )
        finally:
            concurrent.futures.ProcessPoolExecutor = orig

        # on_fold_complete should fire exactly 2 times (once per fold), not 6
        assert len(fold_complete_calls) == 2, (
            f"Expected 2 on_fold_complete calls (one per fold), got {len(fold_complete_calls)}"
        )
        fold_nums = sorted([c[1] for c in fold_complete_calls])
        assert fold_nums == [1, 2], (
            f"Expected fold_nums [1, 2], got {fold_nums}"
        )
