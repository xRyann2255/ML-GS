"""Unit tests for sequence_cache.py — tensor builder + normaliser.

Validates:
1. build_sequence_tensor produces the expected (n_dates, max_bars, n_features) shape
2. lengths tensor matches the per-day valid bar count from the source parquet
3. Padding is applied where bar count < max_bars
4. Cache hash changes when spec (features or max_bars) changes
5. load_sequence_tensor round-trips: builds → saves → loads identical tensors
6. fit_seq_normaliser computes per-feature stats using ONLY training-date rows
   (no leakage from validation/test dates).
7. apply_normaliser transforms the tensor in-place without touching padded
   positions (padded positions remain finite and unchanged after later masking).
8. SequenceTensor.subset_by_dates returns a view with the requested dates
   in order.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.sequence_cache import (
    SequenceSpec,
    SequenceTensor,
    apply_normaliser,
    build_sequence_tensor,
    fit_seq_normaliser,
    load_sequence_tensor,
)

FEATURES = ("buy_vol", "sell_vol", "net_flow", "vwap", "n_trades")


def _write_synthetic_sequences_parquet(
    path: Path,
    *,
    dates: list[str],
    bars_per_day: list[int],
    seed: int = 7,
) -> None:
    """Build a sequences parquet with per-day variable bar counts."""
    rng = np.random.default_rng(seed)
    rows = []
    for d, n in zip(dates, bars_per_day):
        for b in range(n):
            buy = float(rng.integers(0, 1000))
            sell = float(rng.integers(0, 1000))
            rows.append(
                {
                    "date": d,
                    "bar_idx": b,
                    "buy_vol": buy,
                    "sell_vol": sell,
                    "net_flow": buy - sell,
                    "vwap": 200.0 + rng.standard_normal(),
                    "n_trades": float(rng.integers(1, 500)),
                }
            )
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


@pytest.fixture
def synth_sequences_dir(tmp_path: Path) -> Path:
    """Create a synthetic per-symbol sequences directory with two symbols."""
    sequences_dir = tmp_path / "sequences"
    _write_synthetic_sequences_parquet(
        sequences_dir / "SPY.parquet",
        dates=["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"],
        bars_per_day=[30, 30, 20, 30, 25],  # varying
    )
    _write_synthetic_sequences_parquet(
        sequences_dir / "AAPL.parquet",
        dates=["2024-01-02", "2024-01-03", "2024-01-04"],
        bars_per_day=[10, 10, 10],
    )
    return sequences_dir


class TestBuildSequenceTensor:
    def test_shape_matches_max_bars(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        assert seq.tensor.shape == (5, 30, 5)
        assert seq.lengths.shape == (5,)
        assert len(seq.dates) == 5
        assert seq.feature_names == FEATURES

    def test_lengths_match_source(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        # bars_per_day = [30, 30, 20, 30, 25]
        assert seq.lengths.tolist() == [30, 30, 20, 30, 25]

    def test_padding_zeros_beyond_valid_length(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        # Day index 2 has 20 valid bars → bars [20, 30) must be zero.
        assert torch.all(seq.tensor[2, 20:, :] == 0.0).item()
        # And bars [0, 20) must NOT all be zero (synthetic data is nonzero).
        assert not torch.all(seq.tensor[2, :20, :] == 0.0).item()

    def test_truncation_when_max_bars_too_small(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=15)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        # All days truncated to 15 bars; lengths capped at 15.
        assert seq.tensor.shape == (5, 15, 5)
        assert seq.lengths.tolist() == [15, 15, 15, 15, 15]

    def test_feature_subset(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=("buy_vol", "sell_vol"), max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        assert seq.tensor.shape == (5, 30, 2)
        assert seq.feature_names == ("buy_vol", "sell_vol")

    def test_dtype_is_float32(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        assert seq.tensor.dtype == torch.float32
        assert seq.lengths.dtype in (torch.int32, torch.int64)


class TestCacheRoundTrip:
    def test_load_writes_and_reads_identical(
        self, tmp_path: Path, synth_sequences_dir: Path, monkeypatch
    ):
        cache_dir = tmp_path / "processed_sequences"
        spec = SequenceSpec(features=FEATURES, max_bars=30)

        # First call: build + persist
        seq1 = load_sequence_tensor(
            "SPY", spec, sequences_dir=synth_sequences_dir, cache_dir=cache_dir
        )
        cached_files = list(cache_dir.glob("SPY_*.pt"))
        assert len(cached_files) == 1, "First load must write exactly one cache file"

        # Second call: must read from cache (no rebuild needed)
        seq2 = load_sequence_tensor(
            "SPY", spec, sequences_dir=synth_sequences_dir, cache_dir=cache_dir
        )
        assert torch.equal(seq1.tensor, seq2.tensor)
        assert torch.equal(seq1.lengths, seq2.lengths)
        assert list(seq1.dates) == list(seq2.dates)
        assert seq1.feature_names == seq2.feature_names

    def test_cache_hash_changes_with_max_bars(self, tmp_path: Path, synth_sequences_dir: Path):
        cache_dir = tmp_path / "cache"
        spec_a = SequenceSpec(features=FEATURES, max_bars=30)
        spec_b = SequenceSpec(features=FEATURES, max_bars=40)
        load_sequence_tensor("SPY", spec_a, sequences_dir=synth_sequences_dir, cache_dir=cache_dir)
        load_sequence_tensor("SPY", spec_b, sequences_dir=synth_sequences_dir, cache_dir=cache_dir)
        # Two distinct hash files.
        assert len(list(cache_dir.glob("SPY_*.pt"))) == 2

    def test_cache_hash_changes_with_features(self, tmp_path: Path, synth_sequences_dir: Path):
        cache_dir = tmp_path / "cache"
        spec_a = SequenceSpec(features=("buy_vol", "sell_vol"), max_bars=30)
        spec_b = SequenceSpec(features=("buy_vol", "sell_vol", "net_flow"), max_bars=30)
        load_sequence_tensor("SPY", spec_a, sequences_dir=synth_sequences_dir, cache_dir=cache_dir)
        load_sequence_tensor("SPY", spec_b, sequences_dir=synth_sequences_dir, cache_dir=cache_dir)
        assert len(list(cache_dir.glob("SPY_*.pt"))) == 2

    def test_force_rebuild_overwrites(self, tmp_path: Path, synth_sequences_dir: Path):
        cache_dir = tmp_path / "cache"
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        load_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir, cache_dir=cache_dir)
        cached = list(cache_dir.glob("SPY_*.pt"))[0]
        mtime_before = cached.stat().st_mtime_ns
        # Touch the source so it counts as newer (force_rebuild bypasses that check anyway).
        load_sequence_tensor(
            "SPY",
            spec,
            sequences_dir=synth_sequences_dir,
            cache_dir=cache_dir,
            force_rebuild=True,
        )
        mtime_after = cached.stat().st_mtime_ns
        assert mtime_after > mtime_before


class TestNormaliser:
    def test_fit_uses_only_train_dates(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        # Train dates = first three only.
        train_dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
        mean_train, std_train = fit_seq_normaliser(seq, train_dates)

        # Recompute by hand using just those date rows.
        train_mask = seq.dates.isin(train_dates)
        train_lens = seq.lengths[train_mask].tolist()
        # Concat valid bars across the three days.
        valid_rows = []
        train_idx = np.where(train_mask)[0].tolist()
        for di, n in zip(train_idx, train_lens):
            valid_rows.append(seq.tensor[di, :n, :].numpy())
        valid_concat = np.concatenate(valid_rows, axis=0)
        expected_mean = torch.tensor(valid_concat.mean(axis=0), dtype=torch.float32)
        expected_std = torch.tensor(valid_concat.std(axis=0), dtype=torch.float32).clamp_min(1e-6)

        assert torch.allclose(mean_train, expected_mean, atol=1e-4)
        assert torch.allclose(std_train, expected_std, atol=1e-4)

    def test_apply_normaliser_zero_mean_unit_std_on_train(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        train_dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
        mean_t, std_t = fit_seq_normaliser(seq, train_dates)
        normed = apply_normaliser(seq, mean_t, std_t)
        # Pull valid bars only on train dates.
        train_mask_np = np.array([d in set(train_dates) for d in seq.dates])
        train_rows = []
        for di in np.where(train_mask_np)[0]:
            n = int(seq.lengths[di].item())
            train_rows.append(normed.tensor[di, :n, :].numpy())
        block = np.concatenate(train_rows, axis=0)
        assert block.mean(axis=0) == pytest.approx(np.zeros(5), abs=1e-4)
        assert block.std(axis=0) == pytest.approx(np.ones(5), abs=1e-2)

    def test_apply_normaliser_pads_remain_zero(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        train_dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
        mean_t, std_t = fit_seq_normaliser(seq, train_dates)
        normed = apply_normaliser(seq, mean_t, std_t)
        # Day idx 2 has 20 valid bars; bars 20..30 must STILL be zero after norm
        # (we zero-out pads post-norm so masking downstream is trivial).
        assert torch.all(normed.tensor[2, 20:, :] == 0.0).item()


class TestSubsetByDates:
    def test_returns_only_requested_dates_in_order(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        subset_dates = pd.DatetimeIndex(["2024-01-04", "2024-01-08"])
        subset = seq.subset_by_dates(subset_dates)
        assert isinstance(subset, SequenceTensor)
        assert subset.tensor.shape == (2, 30, 5)
        assert list(subset.dates) == list(subset_dates)
        # Length tensor matches original at those positions.
        # Day 2024-01-04 was 20 bars; 2024-01-08 was 25 bars.
        assert subset.lengths.tolist() == [20, 25]

    def test_missing_date_raises(self, synth_sequences_dir: Path):
        spec = SequenceSpec(features=FEATURES, max_bars=30)
        seq = build_sequence_tensor("SPY", spec, sequences_dir=synth_sequences_dir)
        with pytest.raises(KeyError):
            seq.subset_by_dates(pd.DatetimeIndex(["2999-01-01"]))
