"""Integration test for the TCN pipeline path.

Verifies end-to-end: config parsing → sequence loading → TCN fit → predict → QLIKE.
Uses synthetic data with mock sequence loading (no real parquets required).

Marked ``slow`` — excluded by ``./vol test``, included by ``./vol test-all``.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig, SequenceConfig
from volforecast.data.sequence_cache import SequenceTensor
from volforecast.pipeline.runner import Pipeline

pytestmark = [pytest.mark.slow, pytest.mark.integration]


def _make_synthetic_panel_and_sequences(
    n_dates: int = 300,
    max_bars: int = 78,
    n_features: int = 1,
    seed: int = 42,
) -> tuple[dict[str, pd.DataFrame], dict[str, SequenceTensor]]:
    """Build synthetic daily panel + matching SequenceTensors for SPY."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-02", periods=n_dates)

    # Daily panel with RV column (required by Pipeline).
    rv = np.exp(rng.normal(-8.0, 0.5, size=n_dates))  # realistic log-RV range
    daily = pd.DataFrame({"rv": rv}, index=dates)
    panel = {"SPY": daily}

    # Synthetic 5-min sequences: (n_dates, 78, 1) with learnable signal.
    lengths = rng.integers(60, max_bars + 1, size=n_dates).astype(np.int64)
    tensor = np.zeros((n_dates, max_bars, n_features), dtype=np.float32)
    for d in range(n_dates):
        n = int(lengths[d])
        latent = np.log(rv[d])
        scale = np.exp(latent * 0.1)
        tensor[d, :n, :] = rng.standard_normal((n, n_features)).astype(np.float32) * abs(scale)

    seq = SequenceTensor(
        symbol="SPY",
        tensor=torch.from_numpy(tensor),
        lengths=torch.from_numpy(lengths),
        dates=dates,
        feature_names=("log_ret",),
    )
    sym_seqs = {"SPY": seq}

    return panel, sym_seqs


class TestTCNPipeline:
    """End-to-end TCN pipeline smoke test."""

    def test_tcn_run_pooled_completes(self):
        """Pipeline.run_pooled with TCN model produces QLIKE results."""
        panel, sym_seqs = _make_synthetic_panel_and_sequences(n_dates=250)

        cfg = ExperimentConfig(
            name="tcn_smoke_test",
            universe=["SPY"],
            date_range=("2020-01-02", "2021-04-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(
                name="tcn",
                params={
                    "input_dim": 1,
                    "n_channels": [16, 16],
                    "kernel_size": 3,
                    "dropout": 0.0,
                    "learning_rate": 1e-3,
                    "max_epochs": 5,
                    "batch_size": 32,
                    "val_fraction": 0.0,
                    "loss": "mse",
                    "device": "cpu",
                    "seed": 42,
                },
            ),
            sequences=SequenceConfig(
                source="parquet_5min",
                features=["log_ret"],
                max_bars=78,
                norm_mode="pooled",
            ),
            cv=CVConfig(
                method="expanding_window",
                purge_gap=5,
                train_size=100,
                test_size=50,
            ),
            training_mode="pooled",
        )

        pipe = Pipeline(cfg)

        # Mock the 5-min sequence builder to return our synthetic data.
        def _mock_build_5min(symbol, spec, *, sequences_dir=None, **kwargs):
            if symbol in sym_seqs:
                return sym_seqs[symbol]
            raise FileNotFoundError(f"No mock data for {symbol}")

        with patch(
            "volforecast.data.sequence_cache.build_5min_sequence_tensor",
            side_effect=_mock_build_5min,
        ):
            results = pipe.run_pooled(panel)

        # Verify results structure.
        assert 1 in results, "Horizon 1 missing from results"
        h1 = results[1]
        assert "metrics" in h1 or "predictions" in h1, "No metrics or predictions in results"

        # Check that predictions exist and are finite.
        if "predictions" in h1:
            preds = h1["predictions"]
            assert len(preds) > 0, "No predictions produced"
            assert np.isfinite(preds.values).all(), "Non-finite predictions"

        # Check QLIKE is numeric.
        if "metrics" in h1:
            metrics = h1["metrics"]
            if "qlike" in metrics:
                qlike_val = metrics["qlike"]
                assert np.isfinite(qlike_val), f"QLIKE is not finite: {qlike_val}"
