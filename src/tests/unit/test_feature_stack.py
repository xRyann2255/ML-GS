"""Tests for LSTM feature stacking config and extraction.

Validates:
1. FeatureStackConfig dataclass construction and defaults
2. YAML round-trip of feature_stack field on ExperimentConfig
3. feature_stack_for_horizon() merge semantics with horizon_overrides
4. LSTM extract_features() returns correct shapes for all output modes
5. Attention entropy/peak computation correctness
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from volforecast.config import (
    ExperimentConfig,
    FeatureStackConfig,
    ModelConfig,
    SequenceConfig,
)


class TestFeatureStackConfig:
    def test_defaults(self):
        cfg = FeatureStackConfig(source_model="lstm")
        assert cfg.source_model == "lstm"
        assert cfg.outputs == ["prediction"]
        assert cfg.embedding_dim is None
        assert cfg.independent is True
        assert cfg.sequences is None
        assert cfg.model_params == {}

    def test_all_outputs(self):
        cfg = FeatureStackConfig(
            source_model="lstm",
            outputs=["prediction", "attention_entropy", "attention_peak_time", "embedding"],
            embedding_dim=16,
        )
        assert len(cfg.outputs) == 4
        assert cfg.embedding_dim == 16

    def test_independent_false(self):
        cfg = FeatureStackConfig(source_model="lstm", independent=False)
        assert cfg.independent is False

    def test_with_sequences_override(self):
        seq = SequenceConfig(
            features=["log_ret", "rolling_vpin", "price_accel"],
            max_bars=1000,
        )
        cfg = FeatureStackConfig(source_model="lstm", sequences=seq)
        assert cfg.sequences.features == ["log_ret", "rolling_vpin", "price_accel"]
        assert cfg.sequences.max_bars == 1000


class TestFeatureStackYAML:
    def test_round_trip_single(self, tmp_path):
        """feature_stack serializes and deserializes correctly."""
        cfg = ExperimentConfig(
            name="feature_stack_test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm"),
            feature_stack=FeatureStackConfig(
                source_model="lstm",
                outputs=["prediction", "attention_entropy"],
                model_params={"hidden_dim": 64, "n_layers": 1},
            ),
        )
        yaml_path = tmp_path / "fs.yaml"
        cfg.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.feature_stack is not None
        assert loaded.feature_stack.source_model == "lstm"
        assert loaded.feature_stack.outputs == ["prediction", "attention_entropy"]
        assert loaded.feature_stack.model_params["hidden_dim"] == 64
        assert loaded.feature_stack.independent is True

    def test_round_trip_with_sequences(self, tmp_path):
        """feature_stack with custom sequences round-trips."""
        cfg = ExperimentConfig(
            name="fs_seq_test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm"),
            feature_stack=FeatureStackConfig(
                source_model="lstm",
                outputs=["prediction"],
                sequences=SequenceConfig(
                    features=["log_ret", "rolling_vpin"],
                    max_bars=500,
                ),
            ),
        )
        yaml_path = tmp_path / "fs_seq.yaml"
        cfg.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.feature_stack.sequences is not None
        assert loaded.feature_stack.sequences.features == ["log_ret", "rolling_vpin"]
        assert loaded.feature_stack.sequences.max_bars == 500

    def test_none_by_default(self, tmp_path):
        """feature_stack is None when not specified in YAML."""
        cfg = ExperimentConfig(
            name="no_fs",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
        )
        yaml_path = tmp_path / "no_fs.yaml"
        cfg.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.feature_stack is None

    def test_from_yaml_bidirectional(self, tmp_path):
        """independent=false parses correctly."""
        yaml_content = """\
name: bidir_test
universe: [SPY]
date_range: ["2020-01-01", "2023-12-31"]
horizons: [1]
feature_layers: [har_core]
model:
  name: lightgbm
  params: {}
feature_stack:
  source_model: lstm
  outputs: [prediction, embedding]
  embedding_dim: 16
  independent: false
  model_params:
    hidden_dim: 128
"""
        yaml_path = tmp_path / "bidir.yaml"
        yaml_path.write_text(yaml_content)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.feature_stack.independent is False
        assert loaded.feature_stack.embedding_dim == 16
        assert loaded.feature_stack.outputs == ["prediction", "embedding"]


class TestFeatureStackHorizonOverride:
    def test_feature_stack_for_horizon_default(self):
        """Without override, returns top-level feature_stack."""
        cfg = ExperimentConfig(
            name="test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1, 5],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm"),
            feature_stack=FeatureStackConfig(
                source_model="lstm",
                outputs=["prediction"],
            ),
        )
        fs = cfg.feature_stack_for_horizon(1)
        assert fs is not None
        assert fs.outputs == ["prediction"]

    def test_feature_stack_for_horizon_override(self):
        """Horizon override replaces outputs."""
        cfg = ExperimentConfig(
            name="test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1, 22],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm"),
            feature_stack=FeatureStackConfig(
                source_model="lstm",
                outputs=["prediction"],
                model_params={"hidden_dim": 128},
            ),
            horizon_overrides={
                22: {
                    "feature_stack": {
                        "outputs": ["prediction", "attention_entropy"],
                    },
                },
            },
        )
        # h=1 uses default
        fs1 = cfg.feature_stack_for_horizon(1)
        assert fs1.outputs == ["prediction"]
        # h=22 uses override
        fs22 = cfg.feature_stack_for_horizon(22)
        assert fs22.outputs == ["prediction", "attention_entropy"]
        # model_params inherited from base
        assert fs22.model_params["hidden_dim"] == 128

    def test_feature_stack_for_horizon_none(self):
        """Returns None when no feature_stack configured."""
        cfg = ExperimentConfig(
            name="test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm"),
        )
        assert cfg.feature_stack_for_horizon(1) is None


class TestLSTMExtractFeatures:
    """Tests for LSTMVolModel.extract_features()."""

    pytestmark = pytest.mark.slow

    @pytest.fixture
    def fitted_model(self):
        """A tiny LSTM trained on synthetic data for testing extraction."""
        from volforecast.data.sequence_cache import SequenceTensor
        from volforecast.models.lstm import LSTMVolModel

        n_dates, max_bars, n_features = 40, 24, 3
        rng = np.random.default_rng(42)
        lengths = rng.integers(8, max_bars + 1, size=n_dates).astype(np.int64)
        tensor = rng.standard_normal((n_dates, max_bars, n_features)).astype(np.float32)
        targets = rng.standard_normal(n_dates).astype(np.float32)

        import pandas as pd
        dates = pd.bdate_range("2020-01-02", periods=n_dates)
        seq = SequenceTensor(
            symbol="SYN",
            tensor=torch.from_numpy(tensor),
            lengths=torch.from_numpy(lengths),
            dates=dates,
            feature_names=tuple(f"f{i}" for i in range(n_features)),
        )

        model = LSTMVolModel(
            input_dim=n_features,
            hidden_dim=16,
            n_layers=1,
            dropout=0.0,
            learning_rate=1e-3,
            max_epochs=3,
            batch_size=20,
            device="cpu",
        )
        model.fit(seq, targets)
        return model, seq

    def test_extract_prediction(self, fitted_model):
        model, seq = fitted_model
        result = model.extract_features(seq, outputs=["prediction"])
        assert "prediction" in result
        assert result["prediction"].shape == (len(seq.dates),)
        assert result["prediction"].dtype == np.float64 or result["prediction"].dtype == np.float32

    def test_extract_attention_entropy(self, fitted_model):
        model, seq = fitted_model
        result = model.extract_features(seq, outputs=["attention_entropy"])
        assert "attention_entropy" in result
        assert result["attention_entropy"].shape == (len(seq.dates),)
        # Entropy must be non-negative
        assert (result["attention_entropy"] >= 0).all()

    def test_extract_attention_peak_time(self, fitted_model):
        model, seq = fitted_model
        result = model.extract_features(seq, outputs=["attention_peak_time"])
        assert "attention_peak_time" in result
        assert result["attention_peak_time"].shape == (len(seq.dates),)
        # Peak time normalized to [0, 1]
        assert (result["attention_peak_time"] >= 0).all()
        assert (result["attention_peak_time"] <= 1).all()

    def test_extract_embedding(self, fitted_model):
        model, seq = fitted_model
        result = model.extract_features(seq, outputs=["embedding"])
        assert "embedding" in result
        # hidden_dim=16, unidirectional by default → embedding is (N, 16)
        assert result["embedding"].shape == (len(seq.dates), 16)

    def test_extract_all_outputs(self, fitted_model):
        model, seq = fitted_model
        result = model.extract_features(
            seq,
            outputs=["prediction", "attention_entropy", "attention_peak_time", "embedding"],
        )
        assert len(result) == 4
        n = len(seq.dates)
        assert result["prediction"].shape == (n,)
        assert result["attention_entropy"].shape == (n,)
        assert result["attention_peak_time"].shape == (n,)
        assert result["embedding"].shape == (n, 16)

    def test_extract_with_base_preds(self):
        """When model was fit with base_preds, extract_features can use them."""
        from volforecast.data.sequence_cache import SequenceTensor
        from volforecast.models.lstm import LSTMVolModel

        n_dates, max_bars, n_features = 40, 24, 3
        rng = np.random.default_rng(42)
        lengths = rng.integers(8, max_bars + 1, size=n_dates).astype(np.int64)
        tensor = rng.standard_normal((n_dates, max_bars, n_features)).astype(np.float32)
        targets = rng.standard_normal(n_dates).astype(np.float32)
        base_preds = rng.standard_normal(n_dates).astype(np.float32)

        import pandas as pd
        dates = pd.bdate_range("2020-01-02", periods=n_dates)
        seq = SequenceTensor(
            symbol="SYN",
            tensor=torch.from_numpy(tensor),
            lengths=torch.from_numpy(lengths),
            dates=dates,
            feature_names=tuple(f"f{i}" for i in range(n_features)),
        )

        model = LSTMVolModel(
            input_dim=n_features,
            hidden_dim=16, n_layers=1, dropout=0.0,
            learning_rate=1e-3, max_epochs=3, batch_size=20, device="cpu",
        )
        model.fit(seq, targets, base_preds=base_preds)
        result = model.extract_features(seq, outputs=["prediction"], base_preds=base_preds)
        assert "prediction" in result
        assert result["prediction"].shape == (n_dates,)


class TestAttentionUtils:
    """Tests for attention entropy/peak utility functions."""

    def test_attention_entropy_uniform(self):
        """Uniform attention → maximum entropy = log(T)."""
        from volforecast.models.lstm import compute_attention_entropy

        T = 10
        weights = torch.ones(2, T) / T
        mask = torch.ones(2, T, dtype=torch.bool)
        entropy = compute_attention_entropy(weights, mask)
        expected = np.log(T)
        np.testing.assert_allclose(entropy.numpy(), expected, atol=1e-5)

    def test_attention_entropy_peaked(self):
        """One-hot attention → zero entropy."""
        from volforecast.models.lstm import compute_attention_entropy

        weights = torch.zeros(1, 10)
        weights[0, 3] = 1.0
        mask = torch.ones(1, 10, dtype=torch.bool)
        entropy = compute_attention_entropy(weights, mask)
        np.testing.assert_allclose(entropy.numpy(), 0.0, atol=1e-7)

    def test_attention_entropy_masked(self):
        """Masked positions don't contribute to entropy."""
        from volforecast.models.lstm import compute_attention_entropy

        weights = torch.zeros(1, 10)
        weights[0, :5] = 0.2  # uniform over 5 valid positions
        mask = torch.zeros(1, 10, dtype=torch.bool)
        mask[0, :5] = True
        entropy = compute_attention_entropy(weights, mask)
        expected = np.log(5)
        np.testing.assert_allclose(entropy.numpy(), expected, atol=1e-5)

    def test_attention_peak_time(self):
        """Peak time returns normalized argmax position."""
        from volforecast.models.lstm import compute_attention_peak_time

        weights = torch.zeros(2, 100)
        weights[0, 75] = 1.0  # peak at 75 / 99 (max_bars-1)
        weights[1, 25] = 1.0  # peak at 25 / 99
        max_bars = 100
        peak = compute_attention_peak_time(weights, max_bars)
        np.testing.assert_allclose(peak.numpy(), [75 / 99, 25 / 99], atol=1e-5)


class TestTournamentFeatureStackOutputs:
    """Tests for per-model feature_stack_outputs override in tournament."""

    def test_model_with_feature_stack_outputs_override(self):
        """model_configs entry with feature_stack_outputs overrides outputs."""
        from volforecast.config import CVConfig, FeatureStackConfig
        from volforecast.evaluation._parallel import build_tournament_model_config

        fs = FeatureStackConfig(
            source_model="lstm",
            outputs=["prediction", "attention_entropy", "embedding"],
            model_params={"hidden_dim": 64},
        )
        model_configs = {
            "lgbm_pred_only": {
                "name": "lightgbm",
                "params": {"num_leaves": 31},
                "feature_stack_outputs": ["prediction"],
            }
        }
        _, _, config = build_tournament_model_config(
            model_label="lgbm_pred_only",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=CVConfig(),
            tuning_config=None,
            model_params=None,
            model_configs=model_configs,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=fs,
        )
        assert config.feature_stack is not None
        assert config.feature_stack.outputs == ["prediction"]
        # Other fields preserved
        assert config.feature_stack.source_model == "lstm"
        assert config.feature_stack.model_params["hidden_dim"] == 64

    def test_model_in_model_configs_without_override_gets_full_stack(self):
        """model_configs entry without feature_stack_outputs gets full feature_stack."""
        from volforecast.config import CVConfig, FeatureStackConfig
        from volforecast.evaluation._parallel import build_tournament_model_config

        fs = FeatureStackConfig(
            source_model="lstm",
            outputs=["prediction", "attention_entropy"],
        )
        model_configs = {
            "lgbm_all": {
                "name": "lightgbm",
                "params": {},
            }
        }
        _, _, config = build_tournament_model_config(
            model_label="lgbm_all",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=CVConfig(),
            tuning_config=None,
            model_params=None,
            model_configs=model_configs,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=fs,
        )
        assert config.feature_stack is not None
        assert config.feature_stack.outputs == ["prediction", "attention_entropy"]

    def test_baseline_model_not_in_model_configs_gets_no_stack(self):
        """Models not in model_configs (bare labels) get no feature_stack."""
        from volforecast.config import CVConfig, FeatureStackConfig
        from volforecast.evaluation._parallel import build_tournament_model_config

        fs = FeatureStackConfig(
            source_model="lstm",
            outputs=["prediction", "attention_entropy"],
        )
        _, _, config = build_tournament_model_config(
            model_label="har",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=CVConfig(),
            tuning_config=None,
            model_params=None,
            model_configs=None,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=fs,
        )
        assert config.feature_stack is None

    def test_empty_feature_stack_outputs_means_no_stack(self):
        """feature_stack_outputs: [] explicitly disables LSTM features for model."""
        from volforecast.config import CVConfig, FeatureStackConfig
        from volforecast.evaluation._parallel import build_tournament_model_config

        fs = FeatureStackConfig(
            source_model="lstm",
            outputs=["prediction", "attention_entropy"],
        )
        model_configs = {
            "lgbm_control": {
                "name": "lightgbm",
                "params": {},
                "feature_stack_outputs": [],
            }
        }
        _, _, config = build_tournament_model_config(
            model_label="lgbm_control",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=CVConfig(),
            tuning_config=None,
            model_params=None,
            model_configs=model_configs,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=fs,
        )
        assert config.feature_stack is None

    def test_no_feature_stack_passed_results_in_none(self):
        """When feature_stack is None, all models get None."""
        from volforecast.config import CVConfig
        from volforecast.evaluation._parallel import build_tournament_model_config

        model_configs = {
            "lgbm_test": {
                "name": "lightgbm",
                "params": {},
                "feature_stack_outputs": ["prediction"],
            }
        }
        _, _, config = build_tournament_model_config(
            model_label="lgbm_test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=CVConfig(),
            tuning_config=None,
            model_params=None,
            model_configs=model_configs,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=None,
        )
        assert config.feature_stack is None


class TestFeatureStackOutputFilter:
    """Tests for cache output filtering logic."""

    def test_filter_prediction_only(self):
        """Filtering to 'prediction' keeps only lstm_prediction column."""
        import pandas as pd

        df = pd.DataFrame({
            "lstm_prediction": [1.0, 2.0],
            "lstm_attention_entropy": [0.5, 0.6],
            "lstm_attention_peak_time": [0.3, 0.4],
            "lstm_embedding_0": [0.1, 0.2],
            "lstm_embedding_1": [0.3, 0.4],
        })
        requested = ["prediction"]
        keep_prefixes = set()
        for out in requested:
            if out == "embedding":
                keep_prefixes.add("lstm_embedding_")
            else:
                keep_prefixes.add(f"lstm_{out}")
        cols = [c for c in df.columns if any(c == p or c.startswith(p) for p in keep_prefixes)]
        result = df[cols]
        assert list(result.columns) == ["lstm_prediction"]

    def test_filter_embedding_only(self):
        """Filtering to 'embedding' keeps all lstm_embedding_* columns."""
        import pandas as pd

        df = pd.DataFrame({
            "lstm_prediction": [1.0, 2.0],
            "lstm_attention_entropy": [0.5, 0.6],
            "lstm_embedding_0": [0.1, 0.2],
            "lstm_embedding_1": [0.3, 0.4],
            "lstm_embedding_2": [0.5, 0.6],
        })
        requested = ["embedding"]
        keep_prefixes = set()
        for out in requested:
            if out == "embedding":
                keep_prefixes.add("lstm_embedding_")
            else:
                keep_prefixes.add(f"lstm_{out}")
        cols = [c for c in df.columns if any(c == p or c.startswith(p) for p in keep_prefixes)]
        result = df[cols]
        assert list(result.columns) == ["lstm_embedding_0", "lstm_embedding_1", "lstm_embedding_2"]

    def test_filter_multiple_outputs(self):
        """Filtering to multiple outputs keeps correct columns."""
        import pandas as pd

        df = pd.DataFrame({
            "lstm_prediction": [1.0],
            "lstm_attention_entropy": [0.5],
            "lstm_attention_peak_time": [0.3],
            "lstm_embedding_0": [0.1],
        })
        requested = ["prediction", "attention_entropy"]
        keep_prefixes = set()
        for out in requested:
            if out == "embedding":
                keep_prefixes.add("lstm_embedding_")
            else:
                keep_prefixes.add(f"lstm_{out}")
        cols = [c for c in df.columns if any(c == p or c.startswith(p) for p in keep_prefixes)]
        result = df[cols]
        assert list(result.columns) == ["lstm_prediction", "lstm_attention_entropy"]
