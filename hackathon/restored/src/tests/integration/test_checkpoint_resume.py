"""Integration tests for tournament checkpoint/resume with run_models_pooled."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig


def _make_panel_data(n_days: int = 300) -> dict[str, pd.DataFrame]:
    """Create minimal panel data for two symbols."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-02", periods=n_days)
    panel = {}
    for sym in ["SPY", "QQQ"]:
        log_rv_d = rng.standard_normal(n_days) * 0.1 - 8.0
        df = pd.DataFrame(
            {
                "rv": np.exp(log_rv_d),
                "log_rv_d": log_rv_d,
                "log_rv_w": rng.standard_normal(n_days) * 0.08 - 8.0,
                "log_rv_m": rng.standard_normal(n_days) * 0.06 - 8.0,
                "rq": rng.uniform(0.5, 1.5, n_days),
            },
            index=dates,
        )
        df.index.name = "date"
        panel[sym] = df
    return panel


@pytest.fixture
def experiment_config() -> ExperimentConfig:
    return ExperimentConfig(
        name="test_ckpt_resume",
        universe=["SPY", "QQQ"],
        date_range=("2020-01-02", "2021-03-01"),
        horizons=[1],
        feature_layers=["har_core"],
        model=ModelConfig(name="har"),
        cv=CVConfig(method="expanding_window", n_splits=2, purge_gap=5, train_size=100, test_size=50),
    )


class TestCheckpointResumeIntegration:
    """Verify that run_models_pooled resumes from checkpoints."""

    def test_resume_skips_completed_models(self, tmp_path, experiment_config):
        """Models loaded from checkpoint are NOT re-executed."""
        from volforecast.evaluation._parallel import run_models_pooled
        from volforecast.evaluation.checkpoint import save_model_checkpoint

        panel_data = _make_panel_data()

        # Run first model to get real predictions
        preds1, actuals1, _, _ = run_models_pooled(
            models=["har"],
            ml_model_names=[],
            panel_data=panel_data,
            date_range=("2020-01-02", "2021-03-01"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=experiment_config.cv,
            tuning_config=None,
            context=None,
            model_params=None,
            model_configs=None,
            parallel_models=1,
            horizon_overrides=None,
            output_dir=tmp_path,
            checkpoint_enabled=True,
            experiment_config=experiment_config,
        )

        # Verify it was checkpointed
        from volforecast.evaluation.checkpoint import list_completed_models

        completed = list_completed_models(tmp_path, experiment_config)
        assert "har" in completed

        # Now run again with har + harq — har should be loaded from checkpoint
        call_count = {"har_runs": 0}
        original_run_pooled = None

        from volforecast.pipeline.runner import Pipeline

        original_run_pooled = Pipeline.run_pooled

        def counting_run_pooled(self, *args, **kwargs):
            # Track which model labels are actually executed
            call_count["har_runs"] += 1
            return original_run_pooled(self, *args, **kwargs)

        with patch.object(Pipeline, "run_pooled", counting_run_pooled):
            preds2, actuals2, _, _ = run_models_pooled(
                models=["har", "harq"],
                ml_model_names=[],
                panel_data=panel_data,
                date_range=("2020-01-02", "2021-03-01"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=experiment_config.cv,
                tuning_config=None,
                context=None,
                model_params=None,
                model_configs=None,
                parallel_models=1,
                horizon_overrides=None,
                output_dir=tmp_path,
                checkpoint_enabled=True,
                experiment_config=experiment_config,
            )

        # Only harq should have been executed (har was loaded from checkpoint)
        assert call_count["har_runs"] == 1  # only harq ran

        # Both models should be in results
        assert "har" in preds2
        assert "harq" in preds2

        # HAR predictions should match the original run
        pd.testing.assert_series_equal(
            preds2["har"][1], preds1["har"][1], check_names=False
        )

    def test_checkpoint_disabled_runs_all(self, tmp_path, experiment_config):
        """When checkpoint_enabled=False, all models run even if checkpoint exists."""
        from volforecast.evaluation._parallel import run_models_pooled
        from volforecast.evaluation.checkpoint import save_model_checkpoint

        panel_data = _make_panel_data()

        # First run with checkpoint enabled
        run_models_pooled(
            models=["har"],
            ml_model_names=[],
            panel_data=panel_data,
            date_range=("2020-01-02", "2021-03-01"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=experiment_config.cv,
            tuning_config=None,
            context=None,
            model_params=None,
            model_configs=None,
            parallel_models=1,
            horizon_overrides=None,
            output_dir=tmp_path,
            checkpoint_enabled=True,
            experiment_config=experiment_config,
        )

        # Second run with checkpoint disabled — should run har again
        from volforecast.pipeline.runner import Pipeline

        original_run_pooled = Pipeline.run_pooled
        call_count = {"runs": 0}

        def counting_run_pooled(self, *args, **kwargs):
            call_count["runs"] += 1
            return original_run_pooled(self, *args, **kwargs)

        with patch.object(Pipeline, "run_pooled", counting_run_pooled):
            run_models_pooled(
                models=["har"],
                ml_model_names=[],
                panel_data=panel_data,
                date_range=("2020-01-02", "2021-03-01"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=experiment_config.cv,
                tuning_config=None,
                context=None,
                model_params=None,
                model_configs=None,
                parallel_models=1,
                horizon_overrides=None,
                output_dir=tmp_path,
                checkpoint_enabled=False,
                experiment_config=experiment_config,
            )

        # har should have been executed despite existing checkpoint
        assert call_count["runs"] == 1
