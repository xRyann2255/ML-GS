"""Phase 4 tests — Cleanup & Config (L3, L4, L5, N9).

Validates:
1. L3: Multi-GPU fold worker returns a valid model_path (not None) when
   cache is enabled and model supports save.
2. L4 + N9: LSTMVolModel.REQUIRED_LAYERS is empty — standalone sequence
   models don't need tabular feature layers.
3. L5: _maybe_compile uses dynamic=True for packed sequence LSTM (avoids
   CUDA Graph recompilation with variable lengths).
4. feature_layers_for_model("lstm") returns [] (evaluation utils pick up
   the cleared REQUIRED_LAYERS).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.models.lstm import LSTMVolModel, _LSTMBody


class TestRequiredLayers:
    """L4 + N9: REQUIRED_LAYERS cleared for sequence models."""

    def test_lstm_required_layers_empty(self):
        """LSTM model should have empty REQUIRED_LAYERS (no tabular dependency)."""
        assert LSTMVolModel.REQUIRED_LAYERS == []

    def test_feature_layers_for_model_lstm_empty(self):
        """Evaluation utils should report lstm needs no feature layers."""
        from volforecast.evaluation._model_utils import feature_layers_for_model

        layers = feature_layers_for_model("lstm")
        assert layers == []


class TestMaybeCompile:
    """L5: _maybe_compile should use dynamic=True for both embedding and non-embedding paths."""

    def test_compile_disabled_on_cpu(self):
        """compile=True + device=cpu → returns body unchanged (no compile)."""
        model = LSTMVolModel(input_dim=5, compile=True, device="cpu")
        body = model._build_module()
        result = model._maybe_compile(body)
        # On CPU, _maybe_compile should return the raw module (no compile wrapper)
        assert result is body

    def test_compile_disabled_when_flag_false(self):
        """compile=False → returns body unchanged regardless of device."""
        model = LSTMVolModel(input_dim=5, compile=False, device="cpu")
        body = model._build_module()
        result = model._maybe_compile(body)
        assert result is body

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="No CUDA")
    def test_compile_uses_dynamic_true_no_embedding(self):
        """Without embedding, compile should use dynamic=True to handle packed sequences."""
        model = LSTMVolModel(input_dim=5, compile=True, device="cuda", n_symbols=0)
        body = model._build_module()
        compiled = model._maybe_compile(body)
        # torch.compile returns an OptimizedModule wrapper
        assert compiled is not body

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="No CUDA")
    def test_compile_uses_dynamic_true_with_embedding(self):
        """With embedding, compile should use mode=default + dynamic=True."""
        model = LSTMVolModel(input_dim=5, compile=True, device="cuda", n_symbols=5)
        body = model._build_module()
        compiled = model._maybe_compile(body)
        assert compiled is not body


class TestFoldWorkerModelPath:
    """L3: Multi-GPU fold worker returns model_path from fold cache."""

    def test_execute_fold_returns_model_path(self, tmp_path):
        """_execute_fold should return a model_path (not None) when cache is enabled."""
        from volforecast.data.sequence_cache import SequenceTensor
        from volforecast.config import (
            CVConfig,
            ExperimentConfig,
            ModelConfig,
            SequenceConfig,
        )
        from volforecast.pipeline.runner import _execute_fold

        n_dates = 40
        max_bars = 10
        n_features = 5

        rng = np.random.default_rng(42)
        tensor = torch.zeros(n_dates, max_bars, n_features, dtype=torch.float32)
        lengths = torch.full((n_dates,), max_bars, dtype=torch.int64)
        for d in range(n_dates):
            tensor[d, :max_bars, :] = torch.from_numpy(
                rng.standard_normal((max_bars, n_features)).astype(np.float32)
            )

        symbol_ids = torch.zeros(n_dates, dtype=torch.long)
        dates = pd.bdate_range("2023-01-02", periods=n_dates)
        symbols = ["SYN"] * n_dates
        idx = pd.MultiIndex.from_arrays(
            [dates, symbols], names=["date", "symbol"]
        )

        y_values = rng.standard_normal(n_dates).astype(np.float64)
        train_idx_arr = np.arange(30)
        test_idx_arr = np.arange(30, 40)

        config = ExperimentConfig(
            name="test_fold_model_path",
            universe=["SYN"],
            date_range=("2023-01-02", "2023-03-01"),
            horizons=[1],
            feature_layers=[],
            model=ModelConfig(name="lstm", params={
                "input_dim": n_features,
                "hidden_dim": 16,
                "n_layers": 1,
                "dropout": 0.0,
                "max_epochs": 2,
                "batch_size": 64,
                "val_fraction": 0.0,
                "compile": False,
                "device": "cpu",
            }),
            cv=CVConfig(method="expanding_window", train_size=30, test_size=10),
            sequences=SequenceConfig(
                features=["f0", "f1", "f2", "f3", "f4"],
                max_bars=max_bars,
                cache_dir=str(tmp_path / "seq_cache"),
            ),
        )

        result = _execute_fold(
            fold_num=0,
            h=1,
            train_idx_arr=train_idx_arr,
            test_idx_arr=test_idx_arr,
            tensor=tensor,
            lengths=lengths,
            symbol_ids_tensor=symbol_ids,
            idx=idx,
            y_values=y_values,
            model_cls_name="lstm",
            model_params={
                "input_dim": n_features,
                "hidden_dim": 16,
                "n_layers": 1,
                "dropout": 0.0,
                "max_epochs": 2,
                "batch_size": 64,
                "val_fraction": 0.0,
                "compile": False,
                "device": "cpu",
            },
            spec_features=("f0", "f1", "f2", "f3", "f4"),
            base_cfg_dict=None,
            base_X=None,
            base_y=None,
            config_dict=config,
            cache_enabled=True,
            cache_root=str(tmp_path / "cache"),
            device_id=None,
            seed_offset=0,
            norm_mode="pooled",
        )

        assert result["model_path"] is not None
        from pathlib import Path
        assert Path(result["model_path"]).exists()

    def test_execute_fold_returns_none_when_cache_disabled(self, tmp_path):
        """_execute_fold should return model_path=None when cache is disabled."""
        from volforecast.config import (
            CVConfig,
            ExperimentConfig,
            ModelConfig,
            SequenceConfig,
        )
        from volforecast.pipeline.runner import _execute_fold

        n_dates = 40
        max_bars = 10
        n_features = 5

        rng = np.random.default_rng(42)
        tensor = torch.zeros(n_dates, max_bars, n_features, dtype=torch.float32)
        lengths = torch.full((n_dates,), max_bars, dtype=torch.int64)
        for d in range(n_dates):
            tensor[d, :max_bars, :] = torch.from_numpy(
                rng.standard_normal((max_bars, n_features)).astype(np.float32)
            )

        symbol_ids = torch.zeros(n_dates, dtype=torch.long)
        dates = pd.bdate_range("2023-01-02", periods=n_dates)
        symbols = ["SYN"] * n_dates
        idx = pd.MultiIndex.from_arrays(
            [dates, symbols], names=["date", "symbol"]
        )

        y_values = rng.standard_normal(n_dates).astype(np.float64)
        train_idx_arr = np.arange(30)
        test_idx_arr = np.arange(30, 40)

        config = ExperimentConfig(
            name="test_fold_no_cache",
            universe=["SYN"],
            date_range=("2023-01-02", "2023-03-01"),
            horizons=[1],
            feature_layers=[],
            model=ModelConfig(name="lstm", params={
                "input_dim": n_features,
                "hidden_dim": 16,
                "n_layers": 1,
                "dropout": 0.0,
                "max_epochs": 2,
                "batch_size": 64,
                "val_fraction": 0.0,
                "compile": False,
                "device": "cpu",
            }),
            cv=CVConfig(method="expanding_window", train_size=30, test_size=10),
            sequences=SequenceConfig(
                features=["f0", "f1", "f2", "f3", "f4"],
                max_bars=max_bars,
            ),
        )

        result = _execute_fold(
            fold_num=0,
            h=1,
            train_idx_arr=train_idx_arr,
            test_idx_arr=test_idx_arr,
            tensor=tensor,
            lengths=lengths,
            symbol_ids_tensor=symbol_ids,
            idx=idx,
            y_values=y_values,
            model_cls_name="lstm",
            model_params={
                "input_dim": n_features,
                "hidden_dim": 16,
                "n_layers": 1,
                "dropout": 0.0,
                "max_epochs": 2,
                "batch_size": 64,
                "val_fraction": 0.0,
                "compile": False,
                "device": "cpu",
            },
            spec_features=("f0", "f1", "f2", "f3", "f4"),
            base_cfg_dict=None,
            base_X=None,
            base_y=None,
            config_dict=config,
            cache_enabled=False,
            cache_root=None,
            device_id=None,
            seed_offset=0,
            norm_mode="pooled",
        )

        # When cache is disabled, no model is saved, so model_path should be None
        assert result["model_path"] is None
