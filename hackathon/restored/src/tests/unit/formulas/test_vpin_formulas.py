"""VPIN formula verification tests.

Reference: Easley, Lopez de Prado & O'Hara (2012) — "Flow Toxicity and
Liquidity in a High-frequency World", Review of Financial Studies.

VPIN = (1/n) * Σ_{i=1}^{n} |V^{B}_i - V^{S}_i| / V_bucket

Where:
- V^{B}_i = buyer-initiated volume in bucket i
- V^{S}_i = seller-initiated volume in bucket i
- V_bucket = total volume per bucket (fixed)
- n = number of buckets in the rolling window
"""

from __future__ import annotations

import numpy as np
import pytest


class TestVPINKnownValues:
    """Test VPIN against hand-computed values."""

    def test_vpin_all_buy(self):
        """All trades buyer-initiated → VPIN = 1.0 (maximum toxicity)."""
        from volforecast.data.micro import compute_vpin

        n_bars = 100
        buy_vols = np.full(n_bars, 100.0)
        sell_vols = np.zeros(n_bars)
        bucket_volume = 200  # 2 bars per bucket → 50 buckets
        result = compute_vpin(buy_vols, sell_vols, bucket_volume, n_buckets=50)
        assert result == pytest.approx(1.0, abs=1e-10)

    def test_vpin_all_sell(self):
        """All trades seller-initiated → VPIN = 1.0 (maximum toxicity)."""
        from volforecast.data.micro import compute_vpin

        n_bars = 100
        buy_vols = np.zeros(n_bars)
        sell_vols = np.full(n_bars, 100.0)
        bucket_volume = 200
        result = compute_vpin(buy_vols, sell_vols, bucket_volume, n_buckets=50)
        assert result == pytest.approx(1.0, abs=1e-10)

    def test_vpin_balanced_flow(self):
        """Equal buy and sell in every bucket → VPIN = 0.0 (no toxicity)."""
        from volforecast.data.micro import compute_vpin

        n_bars = 100
        buy_vols = np.full(n_bars, 50.0)
        sell_vols = np.full(n_bars, 50.0)
        bucket_volume = 200
        result = compute_vpin(buy_vols, sell_vols, bucket_volume, n_buckets=50)
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_vpin_hand_computed_50_buckets(self):
        """50 buckets with deterministic imbalance pattern → verify exact VPIN.

        Construct: bucket_volume=1000, 50 buckets.
        Bars: each bar has volume 100 (10 bars per bucket).
        Pattern: odd buckets are 70/30 buy/sell, even buckets are 30/70.
        Expected per-bucket |V_B - V_S| / V_bucket:
          odd:  |700 - 300| / 1000 = 0.4
          even: |300 - 700| / 1000 = 0.4
        VPIN = mean(0.4, 0.4, ...) = 0.4
        """
        from volforecast.data.micro import compute_vpin

        n_bars = 500  # 10 bars/bucket × 50 buckets
        buy_vols = np.empty(n_bars)
        sell_vols = np.empty(n_bars)

        for bucket_idx in range(50):
            start = bucket_idx * 10
            end = start + 10
            if bucket_idx % 2 == 0:  # even bucket: 70/30
                buy_vols[start:end] = 70.0
                sell_vols[start:end] = 30.0
            else:  # odd bucket: 30/70
                buy_vols[start:end] = 30.0
                sell_vols[start:end] = 70.0

        bucket_volume = 1000
        result = compute_vpin(buy_vols, sell_vols, bucket_volume, n_buckets=50)
        assert result == pytest.approx(0.4, abs=1e-10)

    def test_vpin_partial_bucket_split(self):
        """Bar volume crosses bucket boundary → proportional split.

        Setup: bucket_volume=150, bars of volume 100.
        Bar 1 (vol=100): fills bucket 0 to 100/150
        Bar 2 (vol=100): 50 goes to bucket 0 (fills it), 50 goes to bucket 1
        Bar 3 (vol=100): bucket 1 gets 100/150 → total 150 → fills bucket 1

        All buy: VPIN = 1.0 regardless of bucket boundaries.
        """
        from volforecast.data.micro import compute_vpin

        buy_vols = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
        sell_vols = np.zeros(6)
        bucket_volume = 150
        n_buckets = 4  # 600 total / 150 = 4 buckets
        result = compute_vpin(buy_vols, sell_vols, bucket_volume, n_buckets=n_buckets)
        assert result == pytest.approx(1.0, abs=1e-10)

    def test_vpin_partial_bucket_mixed(self):
        """Mixed bars crossing bucket boundaries.

        bucket_volume=200. Bars: [buy=120,sell=80], [buy=80,sell=120], repeat.
        Each bar total = 200 → exactly 1 bar per bucket.
        Bucket 0: |120-80|/200 = 0.2
        Bucket 1: |80-120|/200 = 0.2
        VPIN = 0.2
        """
        from volforecast.data.micro import compute_vpin

        buy_vols = np.array([120.0, 80.0, 120.0, 80.0])
        sell_vols = np.array([80.0, 120.0, 80.0, 120.0])
        bucket_volume = 200
        n_buckets = 4
        result = compute_vpin(buy_vols, sell_vols, bucket_volume, n_buckets=n_buckets)
        assert result == pytest.approx(0.2, abs=1e-10)

    def test_vpin_insufficient_volume_returns_nan(self):
        """If total volume < bucket_volume * n_buckets, return NaN."""
        from volforecast.data.micro import compute_vpin

        buy_vols = np.array([10.0, 10.0])
        sell_vols = np.array([10.0, 10.0])
        bucket_volume = 1000
        n_buckets = 50
        result = compute_vpin(buy_vols, sell_vols, bucket_volume, n_buckets=n_buckets)
        assert np.isnan(result)

    def test_vpin_zero_volume_returns_nan(self):
        """All-zero volume day → NaN (not crash)."""
        from volforecast.data.micro import compute_vpin

        buy_vols = np.zeros(100)
        sell_vols = np.zeros(100)
        bucket_volume = 200
        result = compute_vpin(buy_vols, sell_vols, bucket_volume, n_buckets=50)
        assert np.isnan(result)
