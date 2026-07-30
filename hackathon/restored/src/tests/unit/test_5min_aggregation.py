"""Unit tests for 10s → 5min bar aggregation.

Tests the aggregate_to_5min() function that groups 30 consecutive 10-second
bars into one 5-minute bar. TDD: these tests are written before the
implementation and should fail with ImportError initially.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.data.resample import aggregate_to_5min

EXPECTED_COLUMNS = ["date", "bar_idx", "log_ret", "abs_ret", "rv_5min"]


def _make_synthetic_10s_bars(
    n_bars: int, n_dates: int = 1, seed: int = 42
) -> pd.DataFrame:
    """Create synthetic 10s bar DataFrame matching the real parquet schema."""
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        date = pd.Timestamp("2023-01-02") + pd.Timedelta(days=d)
        log_rets = rng.normal(0, 0.001, size=n_bars).astype(np.float32)
        for i in range(n_bars):
            rows.append({
                "date": date,
                "bar_idx": i,
                "log_ret": log_rets[i],
                "abs_ret": abs(log_rets[i]),
                "vol_share": rng.uniform(0, 1),
                "buy_ratio": rng.uniform(0, 1),
                "log_n_trades": rng.uniform(0, 5),
            })
    return pd.DataFrame(rows)


class TestFullDay:
    """2340 10s bars → 78 5-min bars."""

    def test_full_day_bar_count(self):
        df = _make_synthetic_10s_bars(2340)
        result = aggregate_to_5min(df)
        assert len(result) == 78

    def test_full_day_log_ret_is_sum(self):
        df = _make_synthetic_10s_bars(2340)
        result = aggregate_to_5min(df)
        # First 5-min bar should be the sum of bars 0..29
        expected = df.loc[df["bar_idx"].isin(range(30)), "log_ret"].sum()
        np.testing.assert_allclose(result.iloc[0]["log_ret"], expected, atol=1e-5)


class TestPartialDay:
    """Incomplete trailing groups are dropped."""

    def test_1800_bars_gives_60_5min_bars(self):
        df = _make_synthetic_10s_bars(1800)
        result = aggregate_to_5min(df)
        assert len(result) == 60

    def test_2350_bars_drops_trailing_10(self):
        """2350 = 78*30 + 10 → last 10 bars dropped, still 78 5-min bars."""
        df = _make_synthetic_10s_bars(2350)
        result = aggregate_to_5min(df)
        assert len(result) == 78


class TestMultipleDates:
    """Each date processed independently."""

    def test_two_dates_independent(self):
        df = _make_synthetic_10s_bars(2340, n_dates=2)
        result = aggregate_to_5min(df)
        dates = result["date"].unique()
        assert len(dates) == 2
        for date in dates:
            day = result[result["date"] == date]
            assert len(day) == 78

    def test_three_dates_different_bar_counts(self):
        """Simulate dates with different bar counts via concatenation."""
        d1 = _make_synthetic_10s_bars(2340, n_dates=1, seed=1)
        d2 = _make_synthetic_10s_bars(1800, n_dates=1, seed=2)
        d2["date"] = pd.Timestamp("2023-01-03")
        df = pd.concat([d1, d2], ignore_index=True)
        result = aggregate_to_5min(df)
        day1 = result[result["date"] == pd.Timestamp("2023-01-02")]
        day2 = result[result["date"] == pd.Timestamp("2023-01-03")]
        assert len(day1) == 78
        assert len(day2) == 60


class TestOutputColumns:
    """Output has exactly the expected columns."""

    def test_columns_match(self):
        df = _make_synthetic_10s_bars(2340)
        result = aggregate_to_5min(df)
        assert sorted(result.columns.tolist()) == sorted(EXPECTED_COLUMNS)

    def test_no_extra_columns(self):
        df = _make_synthetic_10s_bars(2340)
        result = aggregate_to_5min(df)
        assert set(result.columns) == set(EXPECTED_COLUMNS)


class TestEmptyInput:
    """Empty DataFrame → empty DataFrame."""

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["date", "bar_idx", "log_ret", "abs_ret"])
        result = aggregate_to_5min(df)
        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)

    def test_fewer_than_30_bars(self):
        """If the entire input has < 30 bars, result is empty."""
        df = _make_synthetic_10s_bars(20)
        result = aggregate_to_5min(df)
        assert len(result) == 0


class TestRV5minCorrectness:
    """rv_5min = sum(log_ret²) within each 5-min group."""

    def test_known_values(self):
        """Hand-craft a small example with known log_ret values."""
        log_rets = np.array([0.001, -0.002, 0.003] + [0.0] * 27, dtype=np.float32)
        df = pd.DataFrame({
            "date": pd.Timestamp("2023-01-02"),
            "bar_idx": range(30),
            "log_ret": log_rets,
            "abs_ret": np.abs(log_rets),
        })
        result = aggregate_to_5min(df)
        expected_rv = float(np.sum(log_rets ** 2))
        np.testing.assert_allclose(result.iloc[0]["rv_5min"], expected_rv, atol=1e-8)

    def test_rv_is_sum_of_squares(self):
        """For a full day, rv_5min of bar k = sum(log_ret² for sub-bars 30k..30k+29)."""
        df = _make_synthetic_10s_bars(2340, seed=99)
        result = aggregate_to_5min(df)
        for k in [0, 5, 50, 77]:
            sub = df[(df["bar_idx"] >= k * 30) & (df["bar_idx"] < (k + 1) * 30)]
            expected_rv = float((sub["log_ret"] ** 2).sum())
            np.testing.assert_allclose(
                result.iloc[k]["rv_5min"], expected_rv, atol=1e-6,
                err_msg=f"rv_5min mismatch at 5-min bar {k}",
            )


class TestAbsRetCorrectness:
    """abs_ret = |sum(log_ret)| within each 5-min group."""

    def test_abs_ret_is_abs_of_sum(self):
        df = _make_synthetic_10s_bars(2340, seed=77)
        result = aggregate_to_5min(df)
        for k in [0, 10, 77]:
            sub = df[(df["bar_idx"] >= k * 30) & (df["bar_idx"] < (k + 1) * 30)]
            expected_abs_ret = float(abs(sub["log_ret"].sum()))
            np.testing.assert_allclose(
                result.iloc[k]["abs_ret"], expected_abs_ret, atol=1e-5,
                err_msg=f"abs_ret mismatch at 5-min bar {k}",
            )


class TestSequentialBarIdx:
    """Output bar_idx runs 0..N-1 per date."""

    def test_single_date_sequential(self):
        df = _make_synthetic_10s_bars(2340)
        result = aggregate_to_5min(df)
        np.testing.assert_array_equal(result["bar_idx"].values, np.arange(78))

    def test_multi_date_sequential(self):
        df = _make_synthetic_10s_bars(2340, n_dates=2)
        result = aggregate_to_5min(df)
        for date in result["date"].unique():
            day = result[result["date"] == date].reset_index(drop=True)
            np.testing.assert_array_equal(day["bar_idx"].values, np.arange(78))


class TestCustomIntervals:
    """Verify the bar_interval_s / target_interval_s parameters."""

    def test_5s_to_60s(self):
        """5-second bars → 60-second bars: groups of 12."""
        n_bars = 120  # 10 output bars
        df = _make_synthetic_10s_bars(n_bars)
        result = aggregate_to_5min(df, bar_interval_s=5, target_interval_s=60)
        assert len(result) == 10
