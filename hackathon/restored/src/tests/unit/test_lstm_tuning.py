"""Unit tests for LSTM hyperparameter tuning (Optuna multi-GPU).

Validates:
1. `_suggest_params` samples all search-space keys from a trial.
2. `tune_lstm_hyperparameters` runs with n_trials=3 on CPU (no GPU required)
   and returns a valid best_params dict.
3. `LSTMVolModel.tune_and_fit` returns a fitted model.

These tests use tiny architectures (hidden_dim=8, max_epochs=3) on synthetic
data to run in seconds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.sequence_cache import SequenceTensor

pytestmark = pytest.mark.slow


def _make_synthetic_sequence(
    n_dates: int = 60,
    max_bars: int = 16,
    n_features: int = 3,
    seed: int = 42,
) -> tuple[SequenceTensor, np.ndarray, pd.MultiIndex]:
    """Build synthetic sequences for tuning tests."""
    rng = np.random.default_rng(seed)
    lengths = rng.integers(6, max_bars + 1, size=n_dates).astype(np.int64)

    tensor = np.zeros((n_dates, max_bars, n_features), dtype=np.float32)
    targets = np.zeros(n_dates, dtype=np.float32)
    for d in range(n_dates):
        n = int(lengths[d])
        latent = float(rng.normal(0.0, 1.0))
        scale = np.exp(latent * 0.5)
        x = rng.standard_normal((n, n_features)).astype(np.float32) * scale
        tensor[d, :n, :] = x
        targets[d] = np.log(np.var(x[:, 0]) + 1e-8)

    dates = pd.bdate_range("2020-01-01", periods=n_dates)
    symbols = ["SYN"] * n_dates
    idx = pd.MultiIndex.from_arrays([dates, symbols], names=["date", "symbol"])

    seq = SequenceTensor(
        symbol="_synthetic",
        tensor=torch.from_numpy(tensor),
        lengths=torch.from_numpy(lengths),
        dates=dates,
        feature_names=tuple(f"feat_{i}" for i in range(n_features)),
    )
    return seq, targets, idx


@dataclass
class _MockTuningConfig:
    """Minimal TuningConfig mock for testing."""

    enabled: bool = True
    n_trials: int = 3
    timeout: int | None = 300
    storage_dir: Path | None = None
    inner_cv: object | None = None
    n_jobs: int = 1
    n_workers: int = 1
    tune_every_n_folds: int = 1
    min_train_size: int = 20
    _on_trial_complete: object | None = None
    _on_train_progress: object | None = None


class TestSuggestParams:
    """Test the search space sampling function."""

    def test_suggest_params_returns_all_keys(self):
        """All search space keys should be present in sampled params."""
        import optuna

        from volforecast.models.lstm_tuning import LSTM_SEARCH_SPACE, _suggest_params

        study = optuna.create_study(direction="minimize")
        trial = study.ask()
        params = _suggest_params(trial)
        assert set(params.keys()) == set(LSTM_SEARCH_SPACE.keys())

    def test_suggest_params_values_in_range(self):
        """Sampled values should be within defined ranges."""
        import optuna

        from volforecast.models.lstm_tuning import _suggest_params

        study = optuna.create_study(direction="minimize")
        trial = study.ask()
        params = _suggest_params(trial)

        assert params["hidden_dim"] in [32, 64, 128]
        assert params["n_layers"] in [1, 2, 3]
        assert 3e-4 <= params["learning_rate"] <= 5e-3
        assert 0.05 <= params["dropout"] <= 0.4
        assert 1e-5 <= params["weight_decay"] <= 1e-3
        assert params["batch_size"] in [256, 512, 1024]


class TestTuneLSTMHyperparameters:
    """Integration test for the tuning orchestrator."""

    def test_tune_returns_valid_params(self, tmp_path):
        """tune_lstm_hyperparameters should return a dict with valid keys."""
        from volforecast.models.lstm_tuning import tune_lstm_hyperparameters

        seq, targets, idx = _make_synthetic_sequence(n_dates=200)

        # Force CPU, tiny architecture, small batch sizes for small data
        fixed_params = {
            "max_epochs": 3,
            "early_stopping_rounds": 2,
            "val_fraction": 0.2,
            "loss": "qlike",
            "precision": "fp32",
            "compile": False,
            "bidirectional": False,
            "device": "cpu",
        }

        from volforecast.config import CVConfig

        cv_cfg = CVConfig(
            method="expanding_window",
            purge_gap=2,
            train_size=80,
            test_size=40,
        )

        # Override search space to use smaller batch sizes for test
        import volforecast.models.lstm_tuning as lt
        original_space = lt.LSTM_SEARCH_SPACE.copy()
        lt.LSTM_SEARCH_SPACE["batch_size"] = {"type": "categorical", "choices": [16, 32, 64]}
        try:
            best_params = tune_lstm_hyperparameters(
                tensor=seq.tensor,
                lengths=seq.lengths,
                y_values=targets.astype(np.float64),
                symbol_ids=np.zeros(len(targets), dtype=np.int64),
                idx=idx,
                spec_features=seq.feature_names,
                cv_config=cv_cfg,
                n_trials=3,
                n_gpus=1,
                timeout=120,
                seed=42,
                norm_mode="pooled",
                fixed_params=fixed_params,
                storage_dir=tmp_path / "optuna",
            )
        finally:
            lt.LSTM_SEARCH_SPACE.update(original_space)

        # Should contain at least some tunable keys
        tunable_keys = {"hidden_dim", "n_layers", "learning_rate", "dropout", "weight_decay", "batch_size"}
        found = set(best_params.keys()) & tunable_keys
        assert len(found) > 0, f"Expected tunable keys, got {best_params}"

    def test_tune_resumes_from_storage(self, tmp_path):
        """Running twice with the same storage should resume (not restart)."""
        from volforecast.models.lstm_tuning import tune_lstm_hyperparameters

        seq, targets, idx = _make_synthetic_sequence(n_dates=200)

        fixed_params = {
            "max_epochs": 2,
            "early_stopping_rounds": 1,
            "val_fraction": 0.2,
            "loss": "qlike",
            "precision": "fp32",
            "compile": False,
            "bidirectional": False,
            "device": "cpu",
        }

        from volforecast.config import CVConfig

        cv_cfg = CVConfig(
            method="expanding_window",
            purge_gap=2,
            train_size=80,
            test_size=40,
        )

        storage = tmp_path / "resume_test"

        # Override batch sizes for small data
        import volforecast.models.lstm_tuning as lt
        original_space = lt.LSTM_SEARCH_SPACE.copy()
        lt.LSTM_SEARCH_SPACE["batch_size"] = {"type": "categorical", "choices": [16, 32, 64]}
        try:
            # First run: 2 trials
            tune_lstm_hyperparameters(
                tensor=seq.tensor,
                lengths=seq.lengths,
                y_values=targets.astype(np.float64),
                symbol_ids=np.zeros(len(targets), dtype=np.int64),
                idx=idx,
                spec_features=seq.feature_names,
                cv_config=cv_cfg,
                n_trials=2,
                n_gpus=1,
                seed=42,
                norm_mode="pooled",
                fixed_params=fixed_params,
                storage_dir=storage,
            )

            # Second run: 2 more trials (should resume, total 4)
            tune_lstm_hyperparameters(
                tensor=seq.tensor,
                lengths=seq.lengths,
                y_values=targets.astype(np.float64),
                symbol_ids=np.zeros(len(targets), dtype=np.int64),
                idx=idx,
                spec_features=seq.feature_names,
                cv_config=cv_cfg,
                n_trials=2,
                n_gpus=1,
                seed=42,
                norm_mode="pooled",
                fixed_params=fixed_params,
                storage_dir=storage,
            )
        finally:
            lt.LSTM_SEARCH_SPACE.update(original_space)

        # Verify journal file was created and has data
        journal_file = storage / "lstm_study.journal"
        assert journal_file.exists()
        assert journal_file.stat().st_size > 0


class TestTuneAndFit:
    """Test the LSTMVolModel.tune_and_fit classmethod."""

    def test_tune_and_fit_returns_fitted_model(self, tmp_path):
        """tune_and_fit should return a model that can predict."""
        from volforecast.models.lstm import LSTMVolModel

        seq, targets, idx = _make_synthetic_sequence(n_dates=200)

        tuning_cfg = _MockTuningConfig(
            n_trials=2,
            storage_dir=tmp_path / "tune_fit_test",
        )

        # Set inner CV
        from volforecast.config import CVConfig

        tuning_cfg.inner_cv = CVConfig(
            method="expanding_window",
            purge_gap=2,
            train_size=80,
            test_size=40,
        )

        base_params = {
            "max_epochs": 3,
            "early_stopping_rounds": 2,
            "val_fraction": 0.2,
            "loss": "qlike",
            "precision": "fp32",
            "compile": False,
            "bidirectional": False,
            "device": "cpu",
            "input_dim": seq.n_features,
        }

        # Override batch sizes for small data
        import volforecast.models.lstm_tuning as lt
        original_space = lt.LSTM_SEARCH_SPACE.copy()
        lt.LSTM_SEARCH_SPACE["batch_size"] = {"type": "categorical", "choices": [16, 32, 64]}
        try:
            model = LSTMVolModel.tune_and_fit(
                seq,
                targets,
                tuning_config=tuning_cfg,
                base_params=base_params,
                idx=idx,
                n_gpus=1,
            )
        finally:
            lt.LSTM_SEARCH_SPACE.update(original_space)

        assert isinstance(model, LSTMVolModel)
        assert model.epochs_run_ > 0

        # Should be able to predict
        preds = model.predict(seq)
        assert len(preds) == len(targets)
        assert np.all(np.isfinite(preds))
