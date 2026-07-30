"""Unit tests for microstructure daily aggregate computation.

Tests the pure computation functions that transform 10-second signed-volume
bars into daily scalar features (signed_volume_ratio, vpin, ofi, volumes).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from volforecast.constants import MICRO_DAILY_COLUMNS


class TestSignedVolumeRatio:
    """Tests for signed_volume_ratio = abs(buy - sell) / (buy + sell)."""

    def test_all_buy(self):
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [100.0] * 10,
                "sell_vol": [0.0] * 10,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=500)
        assert result.loc[date(2024, 1, 2), "signed_volume_ratio"] == pytest.approx(1.0)

    def test_all_sell(self):
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [0.0] * 10,
                "sell_vol": [100.0] * 10,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=500)
        assert result.loc[date(2024, 1, 2), "signed_volume_ratio"] == pytest.approx(1.0)

    def test_balanced(self):
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [50.0] * 10,
                "sell_vol": [50.0] * 10,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=500)
        assert result.loc[date(2024, 1, 2), "signed_volume_ratio"] == pytest.approx(0.0)

    def test_bounds_always_0_to_1(self):
        """signed_volume_ratio must be in [0, 1]."""
        from volforecast.data.micro import compute_daily_micro

        rng = np.random.default_rng(42)
        bars = pd.DataFrame(
            {
                "buy_vol": rng.uniform(0, 1000, size=2340),
                "sell_vol": rng.uniform(0, 1000, size=2340),
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=50000)
        svr = result.loc[date(2024, 1, 2), "signed_volume_ratio"]
        assert 0.0 <= svr <= 1.0


class TestOrderFlowImbalance:
    """Tests for order_flow_imbalance = (buy - sell) / (buy + sell)."""

    def test_all_buy(self):
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [100.0] * 10,
                "sell_vol": [0.0] * 10,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=500)
        assert result.loc[date(2024, 1, 2), "order_flow_imbalance"] == pytest.approx(1.0)

    def test_all_sell(self):
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [0.0] * 10,
                "sell_vol": [100.0] * 10,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=500)
        assert result.loc[date(2024, 1, 2), "order_flow_imbalance"] == pytest.approx(-1.0)

    def test_bounds_always_neg1_to_1(self):
        """order_flow_imbalance must be in [-1, 1]."""
        from volforecast.data.micro import compute_daily_micro

        rng = np.random.default_rng(123)
        bars = pd.DataFrame(
            {
                "buy_vol": rng.uniform(0, 1000, size=2340),
                "sell_vol": rng.uniform(0, 1000, size=2340),
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=50000)
        ofi = result.loc[date(2024, 1, 2), "order_flow_imbalance"]
        assert -1.0 <= ofi <= 1.0


class TestDailyAggregationSchema:
    """Test that daily aggregation produces correct schema."""

    def test_output_columns(self):
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [50.0] * 2340,
                "sell_vol": [50.0] * 2340,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=2340)
        assert list(result.columns) == MICRO_DAILY_COLUMNS

    def test_output_index_is_date(self):
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [50.0] * 100,
                "sell_vol": [50.0] * 100,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=500)
        assert result.index[0] == date(2024, 1, 2)

    def test_multiple_days(self):
        from volforecast.data.micro import compute_daily_micro

        bars1 = pd.DataFrame(
            {
                "buy_vol": [80.0] * 100,
                "sell_vol": [20.0] * 100,
            }
        )
        bars2 = pd.DataFrame(
            {
                "buy_vol": [20.0] * 100,
                "sell_vol": [80.0] * 100,
            }
        )
        result = compute_daily_micro(
            {date(2024, 1, 2): bars1, date(2024, 1, 3): bars2},
            bucket_volume=500,
        )
        assert len(result) == 2
        assert result.loc[date(2024, 1, 2), "order_flow_imbalance"] > 0
        assert result.loc[date(2024, 1, 3), "order_flow_imbalance"] < 0

    def test_volume_totals(self):
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [30.0] * 100,
                "sell_vol": [70.0] * 100,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=500)
        assert result.loc[date(2024, 1, 2), "buy_volume"] == pytest.approx(3000.0)
        assert result.loc[date(2024, 1, 2), "sell_volume"] == pytest.approx(7000.0)
        assert result.loc[date(2024, 1, 2), "total_volume"] == pytest.approx(10000.0)

    def test_zero_volume_day_produces_nan(self):
        """A day with zero volume should produce NaN for ratio fields."""
        from volforecast.data.micro import compute_daily_micro

        bars = pd.DataFrame(
            {
                "buy_vol": [0.0] * 10,
                "sell_vol": [0.0] * 10,
            }
        )
        result = compute_daily_micro({date(2024, 1, 2): bars}, bucket_volume=500)
        assert np.isnan(result.loc[date(2024, 1, 2), "signed_volume_ratio"])
        assert np.isnan(result.loc[date(2024, 1, 2), "order_flow_imbalance"])
        assert np.isnan(result.loc[date(2024, 1, 2), "vpin"])


class TestCacheCoversRange:
    """Test cache coverage check logic."""

    def test_no_cache_returns_false(self, tmp_path):
        from volforecast.data.micro import cache_covers_range

        # No file exists
        result = cache_covers_range(
            "AAPL", date(2024, 1, 2), date(2024, 12, 31), cache_dir=tmp_path
        )
        assert result is False

    def test_full_coverage_returns_true(self, tmp_path):
        from volforecast.data.micro import cache_covers_range

        # Create a parquet with dates covering the range
        dates = pd.date_range("2024-01-02", "2024-12-31", freq="B")
        df = pd.DataFrame(
            {"signed_volume_ratio": np.random.rand(len(dates))},
            index=dates,
        )
        path = tmp_path / "AAPL.parquet"
        df.to_parquet(path)

        result = cache_covers_range("AAPL", date(2024, 1, 2), date(2024, 6, 30), cache_dir=tmp_path)
        assert result is True

    def test_partial_coverage_returns_false(self, tmp_path):
        from volforecast.data.micro import cache_covers_range

        dates = pd.date_range("2024-01-02", "2024-06-30", freq="B")
        df = pd.DataFrame(
            {"signed_volume_ratio": np.random.rand(len(dates))},
            index=dates,
        )
        path = tmp_path / "AAPL.parquet"
        df.to_parquet(path)

        # Request extends beyond cached range
        result = cache_covers_range(
            "AAPL", date(2024, 1, 2), date(2024, 12, 31), cache_dir=tmp_path
        )
        assert result is False
