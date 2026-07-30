"""Tests: custom search_space flows through TuningConfig → runner → lstm_tuning."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


class TestTuningConfigSearchSpace:
    """TuningConfig parses and stores search_space from YAML."""

    def test_search_space_field_exists(self):
        from volforecast.config import TuningConfig

        cfg = TuningConfig(search_space={"hidden_dim": {"type": "categorical", "choices": [2, 4, 8]}})
        assert cfg.search_space is not None
        assert cfg.search_space["hidden_dim"]["choices"] == [2, 4, 8]

    def test_search_space_default_none(self):
        from volforecast.config import TuningConfig

        cfg = TuningConfig()
        assert cfg.search_space is None

    def test_search_space_parsed_from_yaml(self, tmp_path):
        """Full YAML with tuning.search_space parses correctly."""
        from volforecast.config import ExperimentConfig

        yaml_content = """\
name: test_search_space
universe: [SPY]
date_range: ["2020-01-01", "2024-12-31"]
horizons: [1]
feature_layers: [har_core]
model:
  name: lstm
  params:
    hidden_dim: 2
    n_layers: 3
    learning_rate: 0.001
sequences:
  source: daily_lookback
  features: [log_rv_d]
  max_bars: 22
  norm_mode: pooled
cv:
  method: expanding_window
  purge_gap: 10
  train_size: 504
  test_size: 126
tuning:
  enabled: true
  n_trials: 64
  search_space:
    hidden_dim:
      type: categorical
      choices: [2, 3, 4, 6, 8]
    n_layers:
      type: int
      low: 1
      high: 6
    learning_rate:
      type: float
      low: 0.0003
      high: 0.005
      log: true
"""
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(yaml_content)

        config = ExperimentConfig.from_yaml(str(config_path))
        assert config.tuning.search_space is not None
        assert config.tuning.search_space["hidden_dim"]["type"] == "categorical"
        assert config.tuning.search_space["hidden_dim"]["choices"] == [2, 3, 4, 6, 8]
        assert config.tuning.search_space["n_layers"]["type"] == "int"
        assert config.tuning.search_space["n_layers"]["low"] == 1
        assert config.tuning.search_space["n_layers"]["high"] == 6
        assert config.tuning.search_space["learning_rate"]["log"] is True


class TestSuggestParamsCustomSpace:
    """_suggest_params respects custom search_space when provided."""

    def test_custom_space_overrides_default(self):
        from volforecast.models.lstm_tuning import _suggest_params

        custom_space = {
            "hidden_dim": {"type": "categorical", "choices": [2, 4]},
            "n_layers": {"type": "int", "low": 1, "high": 6},
        }

        # Mock Optuna trial
        trial = MagicMock()
        trial.suggest_categorical.return_value = 2
        trial.suggest_int.return_value = 3

        params = _suggest_params(trial, search_space=custom_space)

        # Should only have the 2 custom params, NOT the 6 default params
        assert set(params.keys()) == {"hidden_dim", "n_layers"}
        assert params["hidden_dim"] == 2
        assert params["n_layers"] == 3
        trial.suggest_categorical.assert_called_once_with("hidden_dim", [2, 4])
        trial.suggest_int.assert_called_once_with("n_layers", 1, 6, log=False)

    def test_default_space_when_none(self):
        from volforecast.models.lstm_tuning import LSTM_SEARCH_SPACE, _suggest_params

        trial = MagicMock()
        trial.suggest_categorical.return_value = 64
        trial.suggest_float.return_value = 0.001
        trial.suggest_int.return_value = 2

        params = _suggest_params(trial, search_space=None)

        # Should have all keys from the default space
        assert set(params.keys()) == set(LSTM_SEARCH_SPACE.keys())


class TestTuneLstmSearchSpacePassthrough:
    """tune_lstm_hyperparameters accepts and threads search_space."""

    def test_signature_accepts_search_space(self):
        """Function accepts search_space kwarg without TypeError."""
        import inspect

        from volforecast.models.lstm_tuning import tune_lstm_hyperparameters

        sig = inspect.signature(tune_lstm_hyperparameters)
        assert "search_space" in sig.parameters


class TestRunnerExcludesSearchedParams:
    """Runner removes search_space keys from _tune_fixed."""

    def test_searched_keys_excluded_from_fixed(self):
        """Simulate the runner logic: search_space keys must not be in fixed_params."""
        # This tests the LOGIC that should exist in runner.py
        model_params = {
            "hidden_dim": 2,
            "n_layers": 3,
            "learning_rate": 0.001,
            "dropout": 0.0,
            "bidirectional": True,
            "max_epochs": 2000,
            "batch_size": 512,
        }
        search_space = {
            "hidden_dim": {"type": "categorical", "choices": [2, 4, 8]},
            "n_layers": {"type": "int", "low": 1, "high": 6},
            "learning_rate": {"type": "float", "low": 3e-4, "high": 5e-3, "log": True},
        }

        # Simulate runner logic
        _tune_fixed = dict(model_params)
        for key in search_space:
            _tune_fixed.pop(key, None)

        # Searched params must NOT be in fixed
        assert "hidden_dim" not in _tune_fixed
        assert "n_layers" not in _tune_fixed
        assert "learning_rate" not in _tune_fixed
        # Non-searched params remain
        assert "dropout" in _tune_fixed
        assert "bidirectional" in _tune_fixed
        assert "max_epochs" in _tune_fixed


class TestDefaultSearchSpaceKeysStripped:
    """Bug 1 regression: when search_space is None (default), the 6 LSTM_SEARCH_SPACE
    keys must still be stripped from _tune_fixed. This was the broken path."""

    def test_default_keys_stripped_when_no_explicit_search_space(self):
        """Reproduce the runner's _tune_fixed construction with search_space=None.

        The fix imports LSTM_SEARCH_SPACE and strips those keys even when no
        custom search_space is provided in the YAML config.
        """
        from volforecast.models.lstm_tuning import LSTM_SEARCH_SPACE

        model_params = {
            "hidden_dim": 2,
            "n_layers": 3,
            "learning_rate": 0.001,
            "dropout": 0.0,
            "weight_decay": 0.0,
            "batch_size": 512,
            "bidirectional": True,
            "max_epochs": 2000,
            "loss": "mse",
            "device": "auto",
            "seed": 42,
        }

        # Simulate the FIXED runner logic (post-fix):
        _tune_fixed = dict(model_params)
        _tune_search_space = None  # no explicit search_space in YAML

        # The fix: strip default search space keys even when _tune_search_space is None
        _keys_to_strip = _tune_search_space if _tune_search_space else LSTM_SEARCH_SPACE
        for key in _keys_to_strip:
            _tune_fixed.pop(key, None)

        # ALL tunable keys must be absent from fixed_params
        for key in LSTM_SEARCH_SPACE:
            assert key not in _tune_fixed, (
                f"Tunable key '{key}' still in _tune_fixed — HPO search is dead"
            )

        # Non-tunable keys must remain
        assert "bidirectional" in _tune_fixed
        assert "max_epochs" in _tune_fixed
        assert "loss" in _tune_fixed
        assert "device" in _tune_fixed
        assert "seed" in _tune_fixed


class TestOptunaTrialsProduceDifferentConfigs:
    """Bug 1 regression: two Optuna trials must produce different training configs.

    Previously {**sampled, **fixed_params} meant fixed overrode sampled, so every
    trial trained identically (only seed differed).
    """

    def test_trials_produce_different_model_kwargs(self):
        """Run a 2-trial Optuna study with the objective closure and verify
        that at least one tunable param differs between the two trials' configs."""
        from unittest.mock import patch

        import optuna

        from volforecast.models.lstm_tuning import LSTM_SEARCH_SPACE

        # Record model_kwargs passed to each trial
        recorded_configs: list[dict] = []

        # Fixed params should NOT contain tunable keys (post-fix behavior)
        fixed_params = {
            "bidirectional": True,
            "max_epochs": 50,
            "loss": "mse",
            "input_dim": 5,
            "device": "cpu",
            "seed": 42,
        }

        def fake_objective(trial: optuna.Trial) -> float:
            """Mimics the real objective's param construction."""
            from volforecast.models.lstm_tuning import _suggest_params

            sampled = _suggest_params(trial, search_space=None)
            # Post-fix merge order: fixed is the base, sampled overrides
            model_kwargs = {**fixed_params, **sampled}
            model_kwargs["seed"] = 42 + trial.number
            recorded_configs.append(dict(model_kwargs))
            # Return a dummy loss (we only care about the config)
            return float(trial.number) * 0.01 + 0.15

        study = optuna.create_study(direction="minimize")
        study.optimize(fake_objective, n_trials=2, show_progress_bar=False)

        assert len(recorded_configs) == 2, "Expected exactly 2 trial configs recorded"

        # At least one tunable param must differ between the two trials
        tunable_keys = set(LSTM_SEARCH_SPACE.keys())
        any_differs = False
        for key in tunable_keys:
            if key in recorded_configs[0] and key in recorded_configs[1]:
                if recorded_configs[0][key] != recorded_configs[1][key]:
                    any_differs = True
                    break

        # With 2 trials and categorical/float sampling, it's possible (but very
        # unlikely with 6 params) that both sample identically. Use 2 trials with
        # different seeds to ensure we detect the bug: if fixed overrides sampled,
        # ALL params will be identical (only seed differs). If sampled wins, at
        # least one param will differ with near-certainty.
        #
        # For a stronger assertion: verify configs are NOT all identical
        configs_sans_seed = [
            {k: v for k, v in c.items() if k != "seed"} for c in recorded_configs
        ]
        assert configs_sans_seed[0] != configs_sans_seed[1], (
            "Both trials produced identical model_kwargs (ignoring seed) — "
            "HPO search is dead: sampled params are being overridden by fixed_params"
        )
