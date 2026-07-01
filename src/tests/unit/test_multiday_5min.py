"""Tests for build_multiday_5min_sequence_tensor — multi-day 5-min bar sequences.

The builder aggregates 10s bars to 5-min (78 bars/day), then concatenates
``lookback_days`` consecutive trading days into a single sequence per
prediction date.  E.g. lookback_days=20 → 20×78=1,560 timesteps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_10s_parquet(
    tmp_path,
    symbol: str = "TEST",
    n_days: int = 25,
    bars_per_day: int = 2340,
    start_date: str = "2023-01-03",
) -> tuple:
    """Create a fake 10s bar parquet and return (path, dates).

    Returns the parquet directory and sorted list of trading dates.
    """
    dates = pd.bdate_range(start_date, periods=n_days, freq="B")
    rows = []
    for d in dates:
        for bar_idx in range(bars_per_day):
            rows.append(
                {
                    "date": d,
                    "bar_idx": bar_idx,
                    "log_ret": np.random.default_rng(42 + bar_idx).normal(0, 0.0001),
                    "abs_ret": abs(np.random.default_rng(42 + bar_idx).normal(0, 0.0001)),
                }
            )
    df = pd.DataFrame(rows)
    seq_dir = tmp_path / "sequences"
    seq_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(seq_dir / f"{symbol}.parquet", index=False)
    return seq_dir, dates


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMultiday5minContract:
    """Contract tests: output shape, types, invariants."""

    def test_output_shape_20_day_lookback(self, tmp_path):
        """20-day lookback on 25-day dataset → 6 valid dates (dates 20-25)."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir, dates = _make_10s_parquet(tmp_path, n_days=25)
        spec = SequenceSpec(features=("log_ret",), max_bars=1560)
        result = build_multiday_5min_sequence_tensor(
            "TEST", spec, lookback_days=20, sequences_dir=seq_dir
        )

        # Dates 0..18 have < 20 days of history (they exist but with shorter sequences).
        # Date 19 is the first with exactly 20 days.  Total valid = 25 - 20 + 1 = 6.
        assert result.tensor.shape == (len(result.dates), 1560, 1)
        assert result.tensor.dtype == torch.float32
        assert result.lengths.dtype == torch.int64
        assert len(result.dates) > 0
        # Every date with full lookback should have lengths == 20*78
        full_lookback_mask = result.lengths == 20 * 78
        assert full_lookback_mask.sum() >= 1

    def test_output_shape_multi_feature(self, tmp_path):
        """Multi-feature: input_dim=3 (log_ret, abs_ret, rv_5min)."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir, dates = _make_10s_parquet(tmp_path, n_days=5)
        spec = SequenceSpec(features=("log_ret", "abs_ret", "rv_5min"), max_bars=5 * 78)
        result = build_multiday_5min_sequence_tensor(
            "TEST", spec, lookback_days=5, sequences_dir=seq_dir
        )

        assert result.tensor.shape[2] == 3  # 3 features
        assert result.feature_names == ("log_ret", "abs_ret", "rv_5min")

    def test_dates_chronological(self, tmp_path):
        """Output dates are in chronological order."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir, dates = _make_10s_parquet(tmp_path, n_days=25)
        spec = SequenceSpec(features=("log_ret",), max_bars=1560)
        result = build_multiday_5min_sequence_tensor(
            "TEST", spec, lookback_days=20, sequences_dir=seq_dir
        )

        for i in range(1, len(result.dates)):
            assert result.dates[i] > result.dates[i - 1]


class TestMultiday5minLookback:
    """Lookback window logic."""

    def test_single_day_lookback_matches_single_day_builder(self, tmp_path):
        """lookback_days=1 should produce same shape as build_5min_sequence_tensor."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_5min_sequence_tensor,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir, dates = _make_10s_parquet(tmp_path, n_days=5)
        spec = SequenceSpec(features=("log_ret",), max_bars=78)

        single = build_5min_sequence_tensor("TEST", spec, sequences_dir=seq_dir)
        multi = build_multiday_5min_sequence_tensor(
            "TEST", spec, lookback_days=1, sequences_dir=seq_dir
        )

        assert len(multi.dates) == len(single.dates)
        assert multi.tensor.shape == single.tensor.shape

    def test_early_dates_have_shorter_lengths(self, tmp_path):
        """Dates before full lookback have proportionally shorter sequences."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir, dates = _make_10s_parquet(tmp_path, n_days=10)
        spec = SequenceSpec(features=("log_ret",), max_bars=5 * 78)
        result = build_multiday_5min_sequence_tensor(
            "TEST", spec, lookback_days=5, sequences_dir=seq_dir
        )

        # All dates are included, but early dates have fewer bars.
        # Date 0: 1 day = 78 bars, Date 1: 2 days = 156 bars, etc.
        # Date 4+: 5 days = 390 bars
        assert len(result.dates) == 10
        # First date should have exactly 78 bars (1 day only)
        assert result.lengths[0].item() == 78
        # Last date should have 5*78 = 390 bars
        assert result.lengths[-1].item() == 5 * 78

    def test_sequence_ordering_oldest_to_newest(self, tmp_path):
        """Within each sequence, bars are ordered oldest→newest (chronological)."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir, dates = _make_10s_parquet(tmp_path, n_days=5, bars_per_day=300)
        # 300 10s bars → 10 5-min bars per day (300 // 30 = 10)
        spec = SequenceSpec(features=("log_ret",), max_bars=50)  # 5 * 10
        result = build_multiday_5min_sequence_tensor(
            "TEST", spec, lookback_days=5, sequences_dir=seq_dir
        )

        # For the last date (full lookback): sequence should have 5 * 10 = 50 bars
        last_idx = len(result.dates) - 1
        length = result.lengths[last_idx].item()
        assert length == 50
        # The tensor should be filled with non-zero values in valid positions
        valid_slice = result.tensor[last_idx, :length, 0]
        assert (valid_slice != 0).any()


class TestMultiday5minEdgeCases:
    """Edge cases and error handling."""

    def test_missing_parquet_raises(self, tmp_path):
        """Missing source parquet should raise FileNotFoundError."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir = tmp_path / "sequences"
        seq_dir.mkdir()
        spec = SequenceSpec(features=("log_ret",), max_bars=78)

        with pytest.raises(FileNotFoundError):
            build_multiday_5min_sequence_tensor(
                "NOSYMBOL", spec, lookback_days=1, sequences_dir=seq_dir
            )

    def test_missing_feature_raises(self, tmp_path):
        """Requesting unavailable feature should raise KeyError."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir, dates = _make_10s_parquet(tmp_path, n_days=3)
        spec = SequenceSpec(features=("nonexistent_feature",), max_bars=78)

        with pytest.raises(KeyError):
            build_multiday_5min_sequence_tensor(
                "TEST", spec, lookback_days=1, sequences_dir=seq_dir
            )

    def test_zero_padding_beyond_length(self, tmp_path):
        """Positions beyond lengths[i] should be zero-padded."""
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_multiday_5min_sequence_tensor,
        )

        seq_dir, dates = _make_10s_parquet(tmp_path, n_days=5)
        spec = SequenceSpec(features=("log_ret",), max_bars=10 * 78)  # 10 days, but only 5 exist
        result = build_multiday_5min_sequence_tensor(
            "TEST", spec, lookback_days=10, sequences_dir=seq_dir
        )

        # max_bars = 780, but max available is 5*78 = 390
        for i in range(len(result.dates)):
            length = result.lengths[i].item()
            if length < result.tensor.shape[1]:
                padding = result.tensor[i, length:, :]
                assert (padding == 0).all(), f"Non-zero padding at date index {i}"
