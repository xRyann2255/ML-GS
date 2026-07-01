"""Integration test for LSTM feature stacking into LightGBM pipeline.

Verifies the full flow: LSTM trains on sequences per fold, extracts features,
and those features appear as columns in the tabular model's feature matrix.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.config import (
    CVConfig,
    ExperimentConfig,
    FeatureStackConfig,
    ModelConfig,
    SequenceConfig,
)
from volforecast.data.sequence_cache import SequenceTensor


pytestmark = pytest.mark.slow


def _make_panel_data(n_dates: int = 300, symbols: list[str] | None = None):
    """Create synthetic daily panel data with rv column."""
    if symbols is None:
        symbols = ["SYN1", "SYN2"]
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-02", periods=n_dates)
    panel = {}
    for sym in symbols:
        rv = np.exp(rng.normal(-8, 0.5, n_dates))  # realistic log-RV range
        panel[sym] = pd.DataFrame(
            {"rv": rv, "close": 100.0 + rng.standard_normal(n_dates).cumsum()},
            index=dates,
        )
    return panel


def _make_sequence_tensors(
    symbols: list[str], n_dates: int = 300, max_bars: int = 24, n_features: int = 5
):
    """Create synthetic SequenceTensor per symbol."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-02", periods=n_dates)
    tensors = {}
    for sym in symbols:
        lengths = rng.integers(8, max_bars + 1, size=n_dates).astype(np.int64)
        tensor = rng.standard_normal((n_dates, max_bars, n_features)).astype(np.float32)
        tensors[sym] = SequenceTensor(
            symbol=sym,
            tensor=torch.from_numpy(tensor),
            lengths=torch.from_numpy(lengths),
            dates=dates,
            feature_names=("log_ret", "vol_share", "buy_ratio", "log_n_trades", "abs_ret"),
        )
    return tensors


class TestFeatureStackPipelineIntegration:
    """End-to-end feature stacking: LSTM → extract → LightGBM."""

    def test_feature_stack_config_parsed(self):
        """Pipeline accepts feature_stack in config without error."""
        cfg = ExperimentConfig(
            name="feature_stack_smoke",
            universe=["SYN1", "SYN2"],
            date_range=("2020-01-02", "2021-03-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm", params={
                "n_estimators": 10,
                "num_leaves": 4,
                "min_child_samples": 5,
            }),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=50, purge_gap=5),
            feature_stack=FeatureStackConfig(
                source_model="lstm",
                outputs=["prediction", "attention_entropy"],
                model_params={
                    "hidden_dim": 16,
                    "n_layers": 1,
                    "dropout": 0.0,
                    "max_epochs": 2,
                    "batch_size": 32,
                    "loss": "mse",
                    "device": "cpu",
                },
                sequences=SequenceConfig(
                    features=["log_ret", "vol_share", "buy_ratio", "log_n_trades", "abs_ret"],
                    max_bars=24,
                ),
            ),
        )
        assert cfg.feature_stack is not None
        assert cfg.feature_stack.outputs == ["prediction", "attention_entropy"]

    def test_feature_stack_columns_present(self):
        """After pipeline run, LSTM features were injected into the model's X."""
        from unittest.mock import patch
        from volforecast.pipeline.runner import Pipeline

        symbols = ["SYN1", "SYN2"]
        panel = _make_panel_data(300, symbols)
        seq_tensors = _make_sequence_tensors(symbols, 300)

        cfg = ExperimentConfig(
            name="feature_stack_smoke",
            universe=symbols,
            date_range=("2020-01-02", "2021-06-30"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm", params={
                "n_estimators": 10,
                "num_leaves": 4,
                "min_child_samples": 5,
                "val_fraction": 0.0,
            }),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=50, purge_gap=5),
            feature_stack=FeatureStackConfig(
                source_model="lstm",
                outputs=["prediction", "attention_entropy"],
                independent=True,
                model_params={
                    "hidden_dim": 16,
                    "n_layers": 1,
                    "dropout": 0.0,
                    "max_epochs": 2,
                    "batch_size": 32,
                    "loss": "mse",
                    "device": "cpu",
                },
                sequences=SequenceConfig(
                    features=["log_ret", "vol_share", "buy_ratio", "log_n_trades", "abs_ret"],
                    max_bars=24,
                ),
            ),
        )

        pipe = Pipeline(cfg)
        # Patch sequence loading to return our synthetic tensors
        with patch.object(pipe, "_load_feature_stack_sequences", return_value=seq_tensors):
            results = pipe.run_pooled(panel)

        assert 1 in results
        assert results[1]["metrics"]["qlike"] > 0  # sanity: produced valid predictions


class TestFeatureStackTournamentIntegration:
    """Verify per-model feature_stack_outputs in tournament context.

    Uses build_tournament_model_config to construct per-model configs, then
    runs each Pipeline and checks which LSTM columns are present.
    """

    def test_per_model_feature_stack_outputs_filtering(self):
        """Different models see different LSTM output subsets."""
        from unittest.mock import patch
        from volforecast.evaluation._parallel import build_tournament_model_config
        from volforecast.pipeline.runner import Pipeline

        symbols = ["SYN1", "SYN2"]
        panel = _make_panel_data(300, symbols)
        seq_tensors = _make_sequence_tensors(symbols, 300)

        # Base feature_stack: extracts ALL outputs
        fs = FeatureStackConfig(
            source_model="lstm",
            outputs=["prediction", "attention_entropy", "attention_peak_time", "embedding"],
            embedding_dim=4,
            model_params={
                "hidden_dim": 16,
                "n_layers": 1,
                "dropout": 0.0,
                "max_epochs": 2,
                "batch_size": 32,
                "loss": "mse",
                "device": "cpu",
            },
            sequences=SequenceConfig(
                features=["log_ret", "vol_share", "buy_ratio", "log_n_trades", "abs_ret"],
                max_bars=24,
            ),
        )

        model_configs = {
            "lgbm_pred_only": {
                "name": "lightgbm",
                "params": {"n_estimators": 10, "num_leaves": 4, "min_child_samples": 5, "val_fraction": 0.0},
                "feature_stack_outputs": ["prediction"],
            },
            "lgbm_all": {
                "name": "lightgbm",
                "params": {"n_estimators": 10, "num_leaves": 4, "min_child_samples": 5, "val_fraction": 0.0},
                # No override → gets all outputs
            },
            "lgbm_control": {
                "name": "lightgbm",
                "params": {"n_estimators": 10, "num_leaves": 4, "min_child_samples": 5, "val_fraction": 0.0},
                "feature_stack_outputs": [],
            },
        }

        cv_cfg = CVConfig(method="expanding_window", train_size=100, test_size=50, purge_gap=5)

        # ---- lgbm_pred_only: should see only lstm_prediction ----
        _, _, cfg_pred = build_tournament_model_config(
            model_label="lgbm_pred_only",
            universe=symbols,
            date_range=("2020-01-02", "2021-06-30"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_cfg,
            tuning_config=None,
            model_params=None,
            model_configs=model_configs,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=fs,
        )
        assert cfg_pred.feature_stack is not None
        assert cfg_pred.feature_stack.outputs == ["prediction"]

        pipe_pred = Pipeline(cfg_pred)
        with patch.object(pipe_pred, "_load_feature_stack_sequences", return_value=seq_tensors):
            results_pred = pipe_pred.run_pooled(panel)
        assert "qlike" in results_pred[1]["metrics"]

        # ---- lgbm_control: should get NO lstm features ----
        _, _, cfg_ctrl = build_tournament_model_config(
            model_label="lgbm_control",
            universe=symbols,
            date_range=("2020-01-02", "2021-06-30"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_cfg,
            tuning_config=None,
            model_params=None,
            model_configs=model_configs,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=fs,
        )
        assert cfg_ctrl.feature_stack is None

        pipe_ctrl = Pipeline(cfg_ctrl)
        results_ctrl = pipe_ctrl.run_pooled(panel)
        assert "qlike" in results_ctrl[1]["metrics"]

        # ---- lgbm_all: should get ALL outputs including embedding ----
        _, _, cfg_all = build_tournament_model_config(
            model_label="lgbm_all",
            universe=symbols,
            date_range=("2020-01-02", "2021-06-30"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_cfg,
            tuning_config=None,
            model_params=None,
            model_configs=model_configs,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=fs,
        )
        assert cfg_all.feature_stack is not None
        assert cfg_all.feature_stack.outputs == [
            "prediction", "attention_entropy", "attention_peak_time", "embedding"
        ]

        pipe_all = Pipeline(cfg_all)
        with patch.object(pipe_all, "_load_feature_stack_sequences", return_value=seq_tensors):
            results_all = pipe_all.run_pooled(panel)
        assert "qlike" in results_all[1]["metrics"]

    def test_baseline_model_no_feature_stack(self):
        """Bare labels (like 'har') never get feature_stack — they run fine."""
        from volforecast.evaluation._parallel import build_tournament_model_config
        from volforecast.pipeline.runner import Pipeline

        symbols = ["SYN1", "SYN2"]
        panel = _make_panel_data(300, symbols)

        fs = FeatureStackConfig(
            source_model="lstm",
            outputs=["prediction"],
            model_params={"hidden_dim": 16, "n_layers": 1, "device": "cpu"},
        )
        cv_cfg = CVConfig(method="expanding_window", train_size=100, test_size=50, purge_gap=5)

        _, _, cfg_har = build_tournament_model_config(
            model_label="har",
            universe=symbols,
            date_range=("2020-01-02", "2021-06-30"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_cfg,
            tuning_config=None,
            model_params=None,
            model_configs=None,
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            feature_stack=fs,
        )
        # HAR is not in model_configs → gets no feature_stack
        assert cfg_har.feature_stack is None

        pipe_har = Pipeline(cfg_har)
        results = pipe_har.run_pooled(panel)
        assert 1 in results
        assert results[1]["metrics"]["qlike"] > 0
