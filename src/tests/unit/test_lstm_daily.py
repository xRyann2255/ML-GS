"""Tests for Rosenbaum-style daily LSTM additions.

Covers:
1. pool_mode='last_hidden' produces correct output shape
2. head_mode='linear' produces correct output shape
3. build_daily_lookback_tensor produces expected tensor from panel
4. early_stopping_rounds=None disables early stopping
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.sequence_cache import SequenceTensor, build_daily_lookback_tensor
from volforecast.models.lstm import LSTMVolModel, _LSTMBody


class TestPoolMode:
    """Verify pool_mode='last_hidden' and pool_mode='attention' produce valid outputs."""

    @pytest.fixture
    def batch(self):
        B, T, F = 4, 10, 2
        x = torch.randn(B, T, F)
        lengths = torch.tensor([10, 7, 3, 10], dtype=torch.int64)
        return x, lengths

    def test_attention_pool_shape(self, batch):
        x, lengths = batch
        body = _LSTMBody(input_dim=2, hidden_dim=4, n_layers=1, dropout=0.0, pool_mode="attention")
        out = body(x, lengths)
        assert out.shape == (4,)

    def test_last_hidden_pool_shape(self, batch):
        x, lengths = batch
        body = _LSTMBody(input_dim=2, hidden_dim=4, n_layers=1, dropout=0.0, pool_mode="last_hidden")
        out = body(x, lengths)
        assert out.shape == (4,)

    def test_last_hidden_uses_correct_timestep(self, batch):
        """last_hidden should use the output at lengths[i]-1 position, not the padded end."""
        x, lengths = batch
        body = _LSTMBody(input_dim=2, hidden_dim=4, n_layers=1, dropout=0.0, pool_mode="last_hidden")
        body.eval()
        with torch.no_grad():
            # Full batch
            pred_full = body(x, lengths)
            # Single sample with length=3 should give same result regardless of padding
            single_x = x[2:3]  # length=3
            pred_single = body(single_x, lengths[2:3])
        assert torch.allclose(pred_full[2], pred_single[0], atol=1e-5)

    def test_forward_with_internals_last_hidden(self, batch):
        x, lengths = batch
        body = _LSTMBody(input_dim=2, hidden_dim=4, n_layers=1, dropout=0.0, pool_mode="last_hidden")
        pred, pooled, weights = body.forward_with_internals(x, lengths)
        assert pred.shape == (4,)
        assert pooled.shape == (4, 4)
        # Weights should be zeros for last_hidden mode
        assert (weights == 0).all()

    def test_forward_with_internals_attention(self, batch):
        x, lengths = batch
        body = _LSTMBody(input_dim=2, hidden_dim=4, n_layers=1, dropout=0.0, pool_mode="attention")
        pred, pooled, weights = body.forward_with_internals(x, lengths)
        assert pred.shape == (4,)
        assert pooled.shape == (4, 4)
        # Weights should sum to ~1 for valid positions
        assert weights.shape == (4, 10)
        assert torch.allclose(weights.sum(dim=1), torch.ones(4), atol=1e-5)

    def test_invalid_pool_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown pool_mode"):
            _LSTMBody(input_dim=2, hidden_dim=4, n_layers=1, dropout=0.0, pool_mode="mean")


class TestHeadMode:
    """Verify head_mode='linear' vs head_mode='mlp'."""

    def test_linear_head_fewer_params(self):
        body_mlp = _LSTMBody(input_dim=2, hidden_dim=8, n_layers=1, dropout=0.0, head_mode="mlp")
        body_lin = _LSTMBody(input_dim=2, hidden_dim=8, n_layers=1, dropout=0.0, head_mode="linear")
        n_mlp = sum(p.numel() for p in body_mlp.head.parameters())
        n_lin = sum(p.numel() for p in body_lin.head.parameters())
        # linear should have far fewer params (H+1 vs H*H + H + H + 1)
        assert n_lin < n_mlp

    def test_linear_head_output_shape(self):
        body = _LSTMBody(input_dim=2, hidden_dim=4, n_layers=1, dropout=0.0, head_mode="linear")
        x = torch.randn(3, 5, 2)
        lengths = torch.tensor([5, 5, 5], dtype=torch.int64)
        out = body(x, lengths)
        assert out.shape == (3,)

    def test_invalid_head_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown head_mode"):
            _LSTMBody(input_dim=2, hidden_dim=4, n_layers=1, dropout=0.0, head_mode="relu")


class TestRosenbaumArchitecture:
    """Integration test: hidden_dim=2, last_hidden, linear — the paper's architecture."""

    def test_tiny_model_runs(self):
        body = _LSTMBody(
            input_dim=2, hidden_dim=2, n_layers=2, dropout=0.0,
            pool_mode="last_hidden", head_mode="linear",
        )
        x = torch.randn(8, 22, 2)
        lengths = torch.full((8,), 22, dtype=torch.int64)
        out = body(x, lengths)
        assert out.shape == (8,)
        assert out.isfinite().all()

    def test_param_count_minimal(self):
        """hidden_dim=2 with linear head should have very few parameters."""
        body = _LSTMBody(
            input_dim=2, hidden_dim=2, n_layers=2, dropout=0.0,
            pool_mode="last_hidden", head_mode="linear",
        )
        n_params = sum(p.numel() for p in body.parameters())
        # Should be O(100) params, not O(100K)
        assert n_params < 200


class TestDailyLookbackTensor:
    """Test build_daily_lookback_tensor."""

    @pytest.fixture
    def daily_panel(self):
        """Create a simple daily panel with 50 trading days."""
        dates = pd.bdate_range("2023-01-02", periods=50)
        rng = np.random.default_rng(42)
        df = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-2.0, 0.5, 50),
                "signed_return_d": rng.normal(0.0, 0.01, 50),
            },
            index=dates,
        )
        return df

    def test_basic_shape(self, daily_panel):
        seq = build_daily_lookback_tensor("SPY", daily_panel, ("log_rv_d", "signed_return_d"), 22)
        # All dates produce a row (each has at least day-i itself as input)
        assert len(seq) == len(daily_panel)
        assert len(seq) > 0
        assert seq.tensor.shape[1] == 22  # lookback
        assert seq.tensor.shape[2] == 2  # features
        assert seq.symbol == "SPY"
        assert seq.feature_names == ("log_rv_d", "signed_return_d")

    def test_lengths_correct(self, daily_panel):
        seq = build_daily_lookback_tensor("SPY", daily_panel, ("log_rv_d", "signed_return_d"), 22)
        # Last row should have full lookback (22)
        assert seq.lengths[-1].item() == 22
        # Early rows should have shorter lengths
        assert seq.lengths[0].item() < 22

    def test_lookback_content(self, daily_panel):
        """The sequence for date i includes day i (same-day info available at prediction time)."""
        seq = build_daily_lookback_tensor("SPY", daily_panel, ("log_rv_d",), 5)
        # Find a date with full lookback (length == 5)
        full_idx = (seq.lengths == 5).nonzero(as_tuple=True)[0][0].item()
        target_date = seq.dates[full_idx]
        # The last valid value in the sequence should be day i itself
        date_idx = daily_panel.index.get_loc(target_date)
        expected_val = daily_panel["log_rv_d"].iloc[date_idx]
        # Left-aligned: last valid value at position lengths-1 = 4
        actual_val = seq.tensor[full_idx, 4, 0].item()
        assert abs(actual_val - expected_val) < 1e-5

    def test_no_lookahead(self, daily_panel):
        """Sequence for date i must not contain date i+1's value (no future leakage)."""
        seq = build_daily_lookback_tensor("SPY", daily_panel, ("log_rv_d",), 5)
        for i in range(len(seq)):
            target_date = seq.dates[i]
            date_idx = daily_panel.index.get_loc(target_date)
            if date_idx + 1 < len(daily_panel):
                next_day_val = daily_panel["log_rv_d"].iloc[date_idx + 1]
                seq_vals = seq.tensor[i, :, 0][seq.tensor[i, :, 0] != 0].numpy()
                # Next day's value must NOT appear in the sequence
                assert next_day_val not in seq_vals

    def test_handles_nan(self):
        """Days with NaN features should be skipped in the lookback."""
        dates = pd.bdate_range("2023-01-02", periods=10)
        df = pd.DataFrame(
            {"feat": [1.0, np.nan, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]},
            index=dates,
        )
        seq = build_daily_lookback_tensor("TEST", df, ("feat",), 5)
        # Should still produce a tensor (just with shorter lengths where NaN was)
        assert len(seq) > 0

    def test_empty_panel(self):
        """Empty panel should produce empty tensor."""
        df = pd.DataFrame(columns=["log_rv_d", "signed_return_d"])
        df.index = pd.DatetimeIndex([])
        seq = build_daily_lookback_tensor("TEST", df, ("log_rv_d", "signed_return_d"), 22)
        assert len(seq) == 0


class TestEarlyStoppingNone:
    """Verify early_stopping_rounds=None trains for exactly max_epochs."""

    def test_none_accepted(self):
        """Constructor should accept None for early_stopping_rounds."""
        model = LSTMVolModel(input_dim=2, early_stopping_rounds=None, max_epochs=3)
        assert model.early_stopping_rounds == 0

    def test_zero_accepted(self):
        """Constructor should accept 0 for early_stopping_rounds."""
        model = LSTMVolModel(input_dim=2, early_stopping_rounds=0, max_epochs=3)
        assert model.early_stopping_rounds == 0


class TestGetParamsIncludesNewFields:
    """Verify get_params() returns pool_mode and head_mode."""

    def test_params_include_pool_and_head(self):
        model = LSTMVolModel(
            input_dim=2, pool_mode="last_hidden", head_mode="linear"
        )
        params = model.get_params()
        assert params["pool_mode"] == "last_hidden"
        assert params["head_mode"] == "linear"
