"""Tests for unified parallel model training (all models via ProcessPoolExecutor).

Validates:
1. ALL models (HAR + LightGBM) run in parallel when parallel_models > 1
2. Progress events are communicated via multiprocessing.Queue
3. Queue consumer dispatches callbacks correctly (on_model_start, on_fold_complete, etc.)
4. Graceful fallback for fewer models than workers
5. Sequential fallback when parallel_models=1
6. Default parallel_models=4 in TournamentConfig
"""

from __future__ import annotations

import multiprocessing as mp
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from volforecast.config import CVConfig, TournamentConfig


@pytest.fixture
def mock_panel_data():
    """Minimal panel data for testing (2 symbols, 50 days)."""
    dates = pd.bdate_range("2023-01-02", periods=50)
    rng = np.random.default_rng(42)
    data = {}
    for sym in ["SPY", "AAPL"]:
        data[sym] = pd.DataFrame(
            {
                "log_rv_d": -4.0 + 0.3 * rng.standard_normal(50),
                "log_rv_w": -4.0 + 0.2 * rng.standard_normal(50),
                "log_rv_m": -4.0 + 0.15 * rng.standard_normal(50),
            },
            index=dates,
        )
    return data


@pytest.fixture
def cv_config():
    return CVConfig(method="expanding_window", n_splits=2, train_size=30)


class TestDefaultParallelModels:
    """TournamentConfig should default to parallel_models=4."""

    def test_default_is_4(self):
        cfg = TournamentConfig()
        assert cfg.parallel_models == 4


class TestAllModelsParallel:
    """All models (including HAR) should run via ProcessPoolExecutor when parallel_models > 1."""

    def test_har_models_run_in_parallel(self, mock_panel_data, cv_config):
        """HAR models are no longer classified as 'sequential' — they go through parallel path."""
        on_start = MagicMock()
        on_complete = MagicMock()

        # Patch ProcessPoolExecutor where it's imported
        with (
            patch("concurrent.futures.ProcessPoolExecutor") as MockExecutor,
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                side_effect=[
                    ("har", "HAR", {}),  # called in on_model_start loop
                    ("harq", "HARQ", {}),  # called in on_model_start loop
                ],
            ),
        ):
            # Set up the mock executor to return results via futures
            mock_future_har = MagicMock()
            mock_future_har.result.return_value = (
                "HAR",
                {1: pd.Series([0.1, 0.2])},
                {1: pd.Series([0.11, 0.21])},
                {},
            )
            mock_future_harq = MagicMock()
            mock_future_harq.result.return_value = (
                "HARQ",
                {1: pd.Series([0.12, 0.22])},
                {1: pd.Series([0.11, 0.21])},
                {},
            )
            mock_executor_instance = MagicMock()
            mock_executor_instance.__enter__ = MagicMock(return_value=mock_executor_instance)
            mock_executor_instance.__exit__ = MagicMock(return_value=False)
            mock_executor_instance.submit.side_effect = [mock_future_har, mock_future_harq]
            MockExecutor.return_value = mock_executor_instance

            from volforecast.evaluation._parallel import run_models_pooled

            all_preds, all_actuals, _models, _test_data = run_models_pooled(
                models=["har", "harq"],
                ml_model_names=["lightgbm"],
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                context={},
                model_params=None,
                model_configs=None,
                parallel_models=2,
                horizon_overrides=None,
                on_model_start=on_start,
                on_model_complete=on_complete,
            )

        # ProcessPoolExecutor was used (not sequential path)
        MockExecutor.assert_called_once()
        # Both HAR models submitted to executor
        assert mock_executor_instance.submit.call_count == 2
        # Results collected correctly
        assert "HAR" in all_preds
        assert "HARQ" in all_preds
        # on_model_start called for each model
        assert on_start.call_count == 2

    def test_fewer_models_than_workers(self, mock_panel_data, cv_config):
        """Works correctly when model count < parallel_models (e.g., 1 model, 4 workers)."""
        mock_results = {
            1: {
                "predictions": pd.Series([0.1]),
                "actuals": pd.Series([0.11]),
            }
        }

        # With only 1 model, effective_parallel = min(4, 1) = 1 → sequential path
        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                return_value=("har", "HAR", {}),
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline,
        ):
            MockPipeline.return_value.run_pooled.return_value = mock_results

            from volforecast.evaluation._parallel import run_models_pooled

            all_preds, all_actuals, _models, _test_data = run_models_pooled(
                models=["har"],
                ml_model_names=["lightgbm"],
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                context={},
                model_params=None,
                model_configs=None,
                parallel_models=4,
                horizon_overrides=None,
            )

        # With only 1 model, falls back to sequential
        assert "HAR" in all_preds

    def test_sequential_fallback_parallel_1(self, mock_panel_data, cv_config):
        """parallel_models=1 should run sequentially with full callback support."""
        mock_results = {
            1: {
                "predictions": pd.Series([0.1, 0.2]),
                "actuals": pd.Series([0.11, 0.21]),
            }
        }
        on_fold = MagicMock()

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                return_value=("har", "HAR", {}),
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline,
        ):
            # Simulate pipeline calling the on_fold_complete callback
            def fake_run_pooled(
                panel,
                *,
                context=None,
                on_fold_complete=None,
                on_train_progress=None,
                **_,
            ):
                if on_fold_complete:
                    on_fold_complete(1, 1)
                    on_fold_complete(1, 2)
                return mock_results

            MockPipeline.return_value.run_pooled.side_effect = fake_run_pooled

            from volforecast.evaluation._parallel import run_models_pooled

            run_models_pooled(
                models=["har"],
                ml_model_names=["lightgbm"],
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                context={},
                model_params=None,
                model_configs=None,
                parallel_models=1,
                horizon_overrides=None,
                on_fold_complete=on_fold,
            )

        # In sequential mode, on_fold_complete is wrapped to include model_label
        # Verify it was called with (model_label, h, fold_num) signature
        assert on_fold.call_count == 2
        on_fold.assert_any_call("HAR", 1, 1)
        on_fold.assert_any_call("HAR", 1, 2)


class TestProgressEvents:
    """Progress events communicate cross-process via multiprocessing.Queue."""

    def test_fold_complete_event_structure(self):
        """ProgressEvent for fold completion has expected fields."""
        from volforecast.evaluation._parallel import ProgressEvent

        event = ProgressEvent(
            event_type="fold_complete",
            model_label="HAR",
            horizon=1,
            fold_num=3,
        )
        assert event.event_type == "fold_complete"
        assert event.model_label == "HAR"
        assert event.horizon == 1
        assert event.fold_num == 3

    def test_train_progress_event_structure(self):
        """ProgressEvent for training progress has expected fields."""
        from volforecast.evaluation._parallel import ProgressEvent

        event = ProgressEvent(
            event_type="train_progress",
            model_label="LightGBM",
            current_round=100,
            total_rounds=500,
        )
        assert event.event_type == "train_progress"
        assert event.model_label == "LightGBM"
        assert event.current_round == 100
        assert event.total_rounds == 500

    def test_model_complete_event_structure(self):
        """ProgressEvent for model completion has expected fields."""
        from volforecast.evaluation._parallel import ProgressEvent

        event = ProgressEvent(
            event_type="model_complete",
            model_label="HAR",
        )
        assert event.event_type == "model_complete"
        assert event.model_label == "HAR"

    def test_run_single_model_posts_events_to_queue(self, mock_panel_data, cv_config):
        """_run_single_model_pooled should post fold_complete events to the queue."""
        mock_results = {
            1: {
                "predictions": pd.Series([0.1, 0.2]),
                "actuals": pd.Series([0.11, 0.21]),
            }
        }

        progress_queue = mp.Queue()

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                return_value=("har", "HAR", {}),
            ),
            patch(
                "volforecast.evaluation.tournament._build_tournament_context",
                return_value={},
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline,
        ):
            # Simulate fold_complete callback being called twice
            def fake_run_pooled(
                panel,
                *,
                context=None,
                on_fold_complete=None,
                on_train_progress=None,
                **_,
            ):
                if on_fold_complete:
                    on_fold_complete(1, 1)
                    on_fold_complete(1, 2)
                return mock_results

            MockPipeline.return_value.run_pooled.side_effect = fake_run_pooled

            from volforecast.evaluation._parallel import _run_single_model_pooled

            _run_single_model_pooled(
                model_label="har",
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                model_params=None,
                model_configs=None,
                progress_queue=progress_queue,
            )

        # Should have posted fold_complete events + model_complete sentinel
        events = []
        while not progress_queue.empty():
            events.append(progress_queue.get_nowait())
        fold_events = [e for e in events if e.event_type == "fold_complete"]
        complete_events = [e for e in events if e.event_type == "model_complete"]
        assert len(fold_events) == 2
        assert len(complete_events) == 1
        assert fold_events[0].model_label == "HAR"


class TestQueueConsumer:
    """Queue consumer thread dispatches events to callbacks."""

    def test_dispatches_fold_complete(self):
        """Consumer dispatches fold_complete events to on_fold_complete callback."""
        from volforecast.evaluation._parallel import ProgressEvent, _consume_progress_queue

        q = mp.Queue()
        on_fold = MagicMock()
        on_model_complete = MagicMock()

        # Post events + sentinel
        q.put(ProgressEvent(event_type="fold_complete", model_label="HAR", horizon=1, fold_num=1))
        q.put(ProgressEvent(event_type="model_complete", model_label="HAR"))
        q.put(None)  # sentinel to stop consumer

        _consume_progress_queue(
            q,
            on_fold_complete=on_fold,
            on_model_complete=on_model_complete,
            on_train_progress=None,
            on_model_start=None,
        )

        on_fold.assert_called_once_with("HAR", 1, 1)
        on_model_complete.assert_called_once_with("HAR")

    def test_dispatches_train_progress(self):
        """Consumer dispatches train_progress events to on_train_progress callback."""
        from volforecast.evaluation._parallel import ProgressEvent, _consume_progress_queue

        q = mp.Queue()
        on_train = MagicMock()

        q.put(
            ProgressEvent(
                event_type="train_progress",
                model_label="LightGBM",
                current_round=100,
                total_rounds=500,
            )
        )
        q.put(None)  # sentinel

        _consume_progress_queue(
            q,
            on_fold_complete=None,
            on_model_complete=None,
            on_train_progress=on_train,
            on_model_start=None,
        )

        on_train.assert_called_once_with("LightGBM", 100, 500)


class TestHorizonOverridesStripping:
    """Horizon overrides with model.params must not leak to unrelated models."""

    def test_base_model_not_passed_to_ewma(self, mock_panel_data, cv_config):
        """EWMA must not receive base_model from horizon_overrides meant for xgboost.

        Regression test: horizon_overrides={1: {model: {params: {base_model: ...}}}}
        was passed to all tournament models, causing TypeError on EWMAModel.__init__().
        """
        from volforecast.evaluation._parallel import build_tournament_model_config

        _, _, config = build_tournament_model_config(
            model_label="ewma",
            universe=["SPY", "AAPL"],
            date_range=("2023-01-02", "2023-03-15"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_config,
            tuning_config=None,
            model_params=None,
            model_configs=None,
            horizon_overrides={1: {"model": {"params": {"base_model": "har_iv_0dte"}}}},
            sequences=None,
            base_model=None,
        )
        # The EWMA model's params should NOT include base_model
        params = config.model_params_for_horizon(1)
        assert "base_model" not in params

    def test_cv_overrides_preserved_for_baseline(self, mock_panel_data, cv_config):
        """CV-level horizon overrides should still apply to baseline models."""
        from volforecast.evaluation._parallel import build_tournament_model_config

        _, _, config = build_tournament_model_config(
            model_label="har",
            universe=["SPY", "AAPL"],
            date_range=("2023-01-02", "2023-03-15"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_config,
            tuning_config=None,
            model_params=None,
            model_configs=None,
            horizon_overrides={1: {"cv": {"train_size": 756}, "model": {"params": {"base_model": "har_iv_0dte"}}}},
            sequences=None,
            base_model=None,
        )
        # CV override should be preserved
        cv_for_h1 = config.cv_for_horizon(1)
        assert cv_for_h1.train_size == 756
        # But model.params override should be stripped
        params = config.model_params_for_horizon(1)
        assert "base_model" not in params

    def test_model_configs_model_keeps_overrides(self, mock_panel_data, cv_config):
        """Models explicitly in model_configs should still get horizon_overrides."""
        from volforecast.evaluation._parallel import build_tournament_model_config

        _, _, config = build_tournament_model_config(
            model_label="xgb_hariv0dte_init",
            universe=["SPY", "AAPL"],
            date_range=("2023-01-02", "2023-03-15"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_config,
            tuning_config=None,
            model_params=None,
            model_configs={"xgb_hariv0dte_init": {"name": "xgboost", "params": {"n_estimators": 100}}},
            horizon_overrides={1: {"model": {"params": {"base_model": "har_iv_0dte"}}}},
            sequences=None,
            base_model=None,
        )
        # Models in model_configs SHOULD get the horizon override
        params = config.model_params_for_horizon(1)
        assert params.get("base_model") == "har_iv_0dte"
