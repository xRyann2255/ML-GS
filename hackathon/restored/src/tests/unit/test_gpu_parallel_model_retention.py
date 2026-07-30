"""Tests for GPU-parallel model retention.

Validates that _run_horizon_gpu_parallel returns a non-None model
(the last fold's trained booster) so explainability tabs can compute SHAP/ALE.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def simple_panel():
    """Minimal synthetic data for testing GPU parallel aggregation."""
    rng = np.random.default_rng(99)
    n = 300
    dates = pd.bdate_range("2020-01-01", periods=n)
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
        },
        index=dates,
    )
    y = pd.Series(rng.normal(-8, 0.5, n), index=dates)
    return X, y


class TestExecuteTabularFoldModelRetention:
    """_execute_tabular_fold must include 'model' in its return dict."""

    def test_fold_returns_trained_model(self, simple_panel):
        """The fold worker returns a fitted model with a predict method."""
        from volforecast.pipeline.runner import _execute_tabular_fold

        X, y = simple_panel
        n = len(X)
        train_idx = np.arange(0, int(n * 0.7))
        test_idx = np.arange(int(n * 0.7), n)

        result = _execute_tabular_fold(
            fold_num=1,
            X_train=X.iloc[train_idx],
            y_train=y.iloc[train_idx],
            X_test=X.iloc[test_idx],
            model_cls_name="xgboost",
            model_params={
                "n_estimators": 20,
                "early_stopping_rounds": 5,
                "min_child_weight": 10,
                "device": "cpu",
            },
            device_id=None,
        )

        assert "model" in result, "_execute_tabular_fold must return 'model' key"
        assert result["model"] is not None, "model must not be None"
        assert hasattr(result["model"], "predict"), "model must have predict method"


class TestGpuParallelModelRetention:
    """_run_horizon_gpu_parallel must return the last fold's model."""

    def test_parallel_returns_last_fold_model(self, simple_panel):
        """The GPU parallel path should retain the last fold's model."""
        from volforecast.pipeline.runner import _execute_tabular_fold

        X, y = simple_panel

        # Simulate what _run_horizon_gpu_parallel does:
        # 3 folds, pick model from last fold (fold_num=3)
        n = len(X)
        splits = [
            (np.arange(0, 200), np.arange(200, 250)),
            (np.arange(0, 250), np.arange(250, 280)),
            (np.arange(0, 280), np.arange(280, n)),
        ]

        results = []
        for fold_num_0, (train_idx, test_idx) in enumerate(splits):
            r = _execute_tabular_fold(
                fold_num=fold_num_0 + 1,
                X_train=X.iloc[train_idx],
                y_train=y.iloc[train_idx],
                X_test=X.iloc[test_idx],
                model_cls_name="xgboost",
                model_params={
                    "n_estimators": 20,
                    "early_stopping_rounds": 5,
                    "min_child_weight": 10,
                    "device": "cpu",
                },
                device_id=None,
            )
            results.append(r)

        # Aggregation logic: pick model from last fold (highest fold_num)
        last_fold_result = max(results, key=lambda r: r["fold_num"])
        model = last_fold_result.get("model")

        assert model is not None, "Last fold must provide a trained model"
        assert hasattr(model, "predict"), "Model must have predict method"
        # Verify it can actually predict
        preds = model.predict(X.iloc[:5])
        assert len(preds) == 5

    @patch("volforecast.pipeline.runner._execute_tabular_fold")
    def test_run_horizon_gpu_parallel_picks_last_fold(self, mock_fold, simple_panel):
        """Integration: _run_horizon_gpu_parallel selects the last fold's model."""
        from concurrent.futures import ThreadPoolExecutor

        from volforecast.pipeline.runner import Pipeline

        X, y = simple_panel

        # Create mock models — fold 3 has the "best" model (most data)
        mock_models = {}
        for fold_num in range(1, 4):
            m = MagicMock()
            m.predict = MagicMock(return_value=np.zeros(20))
            mock_models[fold_num] = m

        def side_effect(fold_num, X_train, y_train, X_test, model_cls_name, model_params, device_id=None):
            preds = np.zeros(len(X_test))
            return {
                "fold_num": fold_num,
                "preds": preds,
                "duan_correction": 0.0,
                "model": mock_models[fold_num],
            }

        mock_fold.side_effect = side_effect

        # Create pipeline with mocked config (avoid ExperimentConfig construction)
        pipeline = object.__new__(Pipeline)
        pipeline.config = MagicMock()
        pipeline.config.conditional_duan = None

        # Mock model_cls
        model_cls = MagicMock()
        model_cls.name = "xgboost"

        # Mock cv that returns 3 splits
        cv = MagicMock()
        cv.split = MagicMock(return_value=[
            (np.arange(0, 200), np.arange(200, 220)),
            (np.arange(0, 220), np.arange(220, 260)),
            (np.arange(0, 260), np.arange(260, 280)),
        ])

        # ThreadPoolExecutor subclass that accepts (and ignores) mp_context
        class _TestExecutor(ThreadPoolExecutor):
            def __init__(self, max_workers=None, **kwargs):
                super().__init__(max_workers=max_workers)

        # Patch both the local import of ProcessPoolExecutor and mp
        with patch("concurrent.futures.ProcessPoolExecutor", _TestExecutor):
            # Also need to patch the local 'from concurrent.futures import' —
            # the function does a local import, so patch the module it resolves to.
            import concurrent.futures
            orig = concurrent.futures.ProcessPoolExecutor
            concurrent.futures.ProcessPoolExecutor = _TestExecutor
            try:
                result = pipeline._run_horizon_gpu_parallel(
                    X=X.iloc[:280],
                    y=y.iloc[:280],
                    cv=cv,
                    model_cls=model_cls,
                    h=1,
                    model_params={"n_estimators": 10, "device": "cpu"},
                    n_gpus=2,
                )
            finally:
                concurrent.futures.ProcessPoolExecutor = orig

        assert result["model"] is not None, "GPU parallel must return a model"
        # Should be fold 3's model (last fold = most data)
        assert result["model"] is mock_models[3]
