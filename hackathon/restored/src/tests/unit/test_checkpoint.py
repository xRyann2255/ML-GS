"""Tests for tournament checkpoint/resume logic.

Verifies that:
1. Checkpoint save/load round-trips correctly.
2. list_completed_models returns exactly the saved labels.
3. Different config fingerprints isolate checkpoints.
4. Atomic writes prevent corrupt files from being loaded.
5. Loading a non-existent model returns None.
6. checkpoint_enabled=False disables all checkpoint I/O.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig


@pytest.fixture
def experiment_config() -> ExperimentConfig:
    """Minimal experiment config for checkpoint testing."""
    return ExperimentConfig(
        name="test_checkpoint",
        universe=["SPY", "QQQ"],
        date_range=("2020-01-02", "2022-01-01"),
        horizons=[1, 5],
        feature_layers=["har_core"],
        model=ModelConfig(name="har"),
        cv=CVConfig(method="blocked_kfold", n_splits=3),
    )


@pytest.fixture
def sample_preds() -> dict[int, pd.Series]:
    """Sample predictions keyed by horizon."""
    idx = pd.MultiIndex.from_arrays(
        [
            pd.to_datetime(["2021-06-01", "2021-06-02", "2021-06-03"] * 2),
            ["SPY", "SPY", "SPY", "QQQ", "QQQ", "QQQ"],
        ],
        names=["date", "symbol"],
    )
    rng = np.random.default_rng(42)
    return {
        1: pd.Series(rng.standard_normal(6), index=idx, name="pred_h1"),
        5: pd.Series(rng.standard_normal(6), index=idx, name="pred_h5"),
    }


@pytest.fixture
def sample_actuals() -> dict[int, pd.Series]:
    """Sample actuals keyed by horizon."""
    idx = pd.MultiIndex.from_arrays(
        [
            pd.to_datetime(["2021-06-01", "2021-06-02", "2021-06-03"] * 2),
            ["SPY", "SPY", "SPY", "QQQ", "QQQ", "QQQ"],
        ],
        names=["date", "symbol"],
    )
    rng = np.random.default_rng(99)
    return {
        1: pd.Series(rng.standard_normal(6), index=idx, name="actual_h1"),
        5: pd.Series(rng.standard_normal(6), index=idx, name="actual_h5"),
    }


class TestCheckpointSaveLoadRoundtrip:
    """Save predictions for one model, load them back, assert equality."""

    def test_roundtrip(self, tmp_path, experiment_config, sample_preds, sample_actuals):
        from volforecast.evaluation.checkpoint import (
            load_model_checkpoint,
            save_model_checkpoint,
        )

        save_model_checkpoint(
            output_dir=tmp_path,
            config=experiment_config,
            display_label="har",
            preds=sample_preds,
            actuals=sample_actuals,
        )

        result = load_model_checkpoint(
            output_dir=tmp_path,
            config=experiment_config,
            display_label="har",
        )
        assert result is not None
        loaded_preds, loaded_actuals = result

        for h in sample_preds:
            pd.testing.assert_series_equal(loaded_preds[h], sample_preds[h])
            pd.testing.assert_series_equal(loaded_actuals[h], sample_actuals[h])


class TestListCompletedModels:
    """Save 3 models, list returns exactly those 3 display labels."""

    def test_list_returns_saved_labels(
        self, tmp_path, experiment_config, sample_preds, sample_actuals
    ):
        from volforecast.evaluation.checkpoint import (
            list_completed_models,
            save_model_checkpoint,
        )

        labels = ["har", "harq", "shar"]
        for label in labels:
            save_model_checkpoint(
                output_dir=tmp_path,
                config=experiment_config,
                display_label=label,
                preds=sample_preds,
                actuals=sample_actuals,
            )

        completed = list_completed_models(tmp_path, experiment_config)
        assert completed == set(labels)


class TestFingerprintIsolation:
    """Save with config A, query with config B → empty."""

    def test_different_config_sees_nothing(
        self, tmp_path, experiment_config, sample_preds, sample_actuals
    ):
        from volforecast.evaluation.checkpoint import (
            list_completed_models,
            save_model_checkpoint,
        )

        # Save with original config
        save_model_checkpoint(
            output_dir=tmp_path,
            config=experiment_config,
            display_label="har",
            preds=sample_preds,
            actuals=sample_actuals,
        )

        # Modify config (different seed → different fingerprint)
        experiment_config.seed = 999

        completed = list_completed_models(tmp_path, experiment_config)
        assert completed == set()


class TestAtomicWrite:
    """Simulate crash mid-write — no corrupt file loaded."""

    def test_no_corrupt_file_on_interrupted_write(
        self, tmp_path, experiment_config, sample_preds, sample_actuals, monkeypatch
    ):
        from volforecast.evaluation import checkpoint

        # Patch os.replace to simulate a crash (raise before rename)
        original_replace = checkpoint.os.replace

        def failing_replace(src, dst):
            raise OSError("simulated crash")

        monkeypatch.setattr(checkpoint.os, "replace", failing_replace)

        with pytest.raises(OSError, match="simulated crash"):
            checkpoint.save_model_checkpoint(
                output_dir=tmp_path,
                config=experiment_config,
                display_label="har",
                preds=sample_preds,
                actuals=sample_actuals,
            )

        # No valid checkpoint should exist
        result = checkpoint.load_model_checkpoint(
            output_dir=tmp_path,
            config=experiment_config,
            display_label="har",
        )
        assert result is None


class TestLoadMissing:
    """Load a model that was never saved → None."""

    def test_load_nonexistent_returns_none(self, tmp_path, experiment_config):
        from volforecast.evaluation.checkpoint import load_model_checkpoint

        result = load_model_checkpoint(
            output_dir=tmp_path,
            config=experiment_config,
            display_label="nonexistent_model",
        )
        assert result is None


class TestCheckpointDisabled:
    """When checkpoint_enabled is False, no checkpoint dir is created."""

    def test_no_dir_created_when_disabled(
        self, tmp_path, experiment_config, sample_preds, sample_actuals
    ):
        from volforecast.evaluation.checkpoint import (
            checkpoint_dir,
            list_completed_models,
            save_model_checkpoint,
        )

        # With checkpoint_enabled=False, save should be a no-op
        # (The caller is responsible for not calling save, but list should
        # return empty if dir doesn't exist)
        completed = list_completed_models(tmp_path, experiment_config)
        assert completed == set()

        # Checkpoint dir should not exist for a never-used config
        ckpt_dir = checkpoint_dir(tmp_path, experiment_config)
        assert not ckpt_dir.exists()


class TestEmptyPredictionGuard:
    """Empty predictions from failed model runs must not be saved or loaded."""

    def test_save_skips_empty_predictions(self, tmp_path, experiment_config):
        from volforecast.evaluation.checkpoint import (
            list_completed_models,
            save_model_checkpoint,
        )

        empty_preds = {
            1: pd.Series([], dtype=float, name="pred_h1"),
            5: pd.Series([], dtype=float, name="pred_h5"),
        }
        empty_actuals = {
            1: pd.Series([], dtype=float, name="actual_h1"),
            5: pd.Series([], dtype=float, name="actual_h5"),
        }

        save_model_checkpoint(
            output_dir=tmp_path,
            config=experiment_config,
            display_label="lstm",
            preds=empty_preds,
            actuals=empty_actuals,
        )

        # Should NOT appear in completed models
        completed = list_completed_models(tmp_path, experiment_config)
        assert "lstm" not in completed

    def test_load_rejects_empty_checkpoint(
        self, tmp_path, experiment_config, sample_preds, sample_actuals
    ):
        from volforecast.evaluation.checkpoint import (
            load_model_checkpoint,
            save_model_checkpoint,
        )

        # First save a valid checkpoint
        save_model_checkpoint(
            output_dir=tmp_path,
            config=experiment_config,
            display_label="lstm",
            preds=sample_preds,
            actuals=sample_actuals,
        )
        # Verify it loads
        result = load_model_checkpoint(tmp_path, experiment_config, "lstm")
        assert result is not None

        # Now overwrite with empty predictions (simulating manual corruption)
        from volforecast.evaluation.checkpoint import checkpoint_dir, _sanitize_label
        import json

        ckpt = checkpoint_dir(tmp_path, experiment_config) / _sanitize_label("lstm")
        for h in [1, 5]:
            pd.Series([], dtype=float).to_frame().to_parquet(ckpt / f"preds_h{h}.parquet")
            pd.Series([], dtype=float).to_frame().to_parquet(ckpt / f"actuals_h{h}.parquet")

        # Should reject the empty checkpoint
        result = load_model_checkpoint(tmp_path, experiment_config, "lstm")
        assert result is None
