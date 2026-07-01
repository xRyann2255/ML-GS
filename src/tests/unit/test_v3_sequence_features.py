"""Tests for v3 enriched sequence features in _build_sequences_df.

Validates price_accel, rolling_vpin, cum_rv, and session_frac columns
are correctly computed from the raw 10s bar data.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest


def _make_bars(n_bars: int = 100, seed: int = 42) -> dict[date, pd.DataFrame]:
    """Create 1-day synthetic 10s bar data."""
    rng = np.random.default_rng(seed)
    d = date(2024, 6, 1)
    return {
        d: pd.DataFrame(
            {
                "buy_vol": rng.uniform(50, 500, size=n_bars),
                "sell_vol": rng.uniform(50, 500, size=n_bars),
                "neutral_vol": rng.uniform(0, 50, size=n_bars),
                "vwap": 200.0 + np.cumsum(rng.normal(0, 0.1, size=n_bars)),
                "n_trades": rng.integers(10, 200, size=n_bars),
            }
        )
    }


class TestPriceAccel:
    """price_accel = log_ret[t] - log_ret[t-1], first two bars = 0."""

    def test_column_exists(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(50)
        df = _build_sequences_df(bars)
        assert "price_accel" in df.columns

    def test_first_bar_zero(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(50)
        df = _build_sequences_df(bars)
        assert df["price_accel"].iloc[0] == 0.0

    def test_values_equal_diff_of_log_ret(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100)
        df = _build_sequences_df(bars)
        log_ret = df["log_ret"].values
        expected = np.diff(log_ret, prepend=0.0)
        expected[0] = 0.0  # first bar log_ret is already 0, diff is 0
        np.testing.assert_allclose(df["price_accel"].values, expected, atol=1e-12)

    def test_no_nans(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(200)
        df = _build_sequences_df(bars)
        assert not df["price_accel"].isna().any()


class TestRollingVpin:
    """rolling_vpin = rolling |buy-sell|/(buy+sell) over 50-bar window."""

    def test_column_exists(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100)
        df = _build_sequences_df(bars)
        assert "rolling_vpin" in df.columns

    def test_bounded_zero_one(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(200)
        df = _build_sequences_df(bars)
        vals = df["rolling_vpin"].values
        assert (vals >= 0.0).all()
        assert (vals <= 1.0 + 1e-10).all()

    def test_no_nans(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(200)
        df = _build_sequences_df(bars)
        assert not df["rolling_vpin"].isna().any()

    def test_manual_computation_matches(self):
        """Verify rolling_vpin matches manual rolling computation."""
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100, seed=99)
        df = _build_sequences_df(bars)
        buy = bars[date(2024, 6, 1)]["buy_vol"].values
        sell = bars[date(2024, 6, 1)]["sell_vol"].values
        imbalance = np.abs(buy - sell)
        total = buy + sell
        # Expanding window for first 50 bars, then rolling 50
        window = 50
        expected = np.empty(len(buy))
        for i in range(len(buy)):
            start = max(0, i - window + 1)
            expected[i] = imbalance[start : i + 1].sum() / (total[start : i + 1].sum() + 1e-10)
        np.testing.assert_allclose(df["rolling_vpin"].values, expected, atol=1e-8)

    def test_rolling_vpin_matches_naive_loop(self):
        """Step 1.4 vectorised path must match the original Python loop to
        machine precision (1e-12) — pure numerical equivalence on random
        buy/sell arrays of length 200.
        """
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(200, seed=12345)
        df = _build_sequences_df(bars)
        buy = bars[date(2024, 6, 1)]["buy_vol"].values
        sell = bars[date(2024, 6, 1)]["sell_vol"].values
        imbalance = np.abs(buy - sell)
        bar_total = buy + sell
        cum_imbalance = np.cumsum(imbalance)
        cum_total = np.cumsum(bar_total)
        # Original naive-loop reference (pre-Step-1.4 implementation).
        vpin_window = 50
        n_bars = len(buy)
        naive = np.empty(n_bars)
        for i in range(n_bars):
            start = max(0, i - vpin_window + 1)
            if start == 0:
                num = cum_imbalance[i]
                den = cum_total[i]
            else:
                num = cum_imbalance[i] - cum_imbalance[start - 1]
                den = cum_total[i] - cum_total[start - 1]
            naive[i] = num / (den + 1e-10)
        np.testing.assert_allclose(df["rolling_vpin"].values, naive, rtol=1e-12, atol=1e-12)

    def test_rolling_vpin_first_window_expanding(self):
        """Bars 0..(W-1) must use an expanding window. The first bar's value
        must equal |buy[0] - sell[0]| / (buy[0] + sell[0] + 1e-10)."""
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100, seed=314)
        df = _build_sequences_df(bars)
        buy = bars[date(2024, 6, 1)]["buy_vol"].values
        sell = bars[date(2024, 6, 1)]["sell_vol"].values
        expected_first = abs(buy[0] - sell[0]) / (buy[0] + sell[0] + 1e-10)
        np.testing.assert_allclose(df["rolling_vpin"].iloc[0], expected_first, rtol=1e-12)

    def test_rolling_vpin_constant_input_zero(self):
        """When buy == sell on every bar, |buy - sell| = 0 → rolling_vpin == 0."""
        from volforecast.data.micro import _build_sequences_df

        d = date(2024, 6, 1)
        n = 100
        bars = {
            d: pd.DataFrame(
                {
                    "buy_vol": np.full(n, 100.0),
                    "sell_vol": np.full(n, 100.0),
                    "neutral_vol": np.zeros(n),
                    "vwap": 200.0 + np.arange(n) * 0.01,
                    "n_trades": np.full(n, 50, dtype=int),
                }
            )
        }
        df = _build_sequences_df(bars)
        np.testing.assert_allclose(df["rolling_vpin"].values, 0.0, atol=1e-12)


class TestCumRv:
    """cum_rv = cumulative sum of log_ret² within the day."""

    def test_column_exists(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(50)
        df = _build_sequences_df(bars)
        assert "cum_rv" in df.columns

    def test_monotonically_increasing(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100)
        df = _build_sequences_df(bars)
        vals = df["cum_rv"].values
        diffs = np.diff(vals)
        assert (diffs >= -1e-15).all()  # monotonically non-decreasing

    def test_first_bar_zero(self):
        """First bar log_ret is 0, so cum_rv[0] = 0."""
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(50)
        df = _build_sequences_df(bars)
        assert df["cum_rv"].iloc[0] == pytest.approx(0.0)

    def test_values_equal_cumsum_log_ret_squared(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100)
        df = _build_sequences_df(bars)
        expected = np.cumsum(df["log_ret"].values ** 2)
        np.testing.assert_allclose(df["cum_rv"].values, expected, atol=1e-12)

    def test_no_nans(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(200)
        df = _build_sequences_df(bars)
        assert not df["cum_rv"].isna().any()


class TestSessionFrac:
    """session_frac = bar_idx / max(bar_idx) within day, in [0, 1]."""

    def test_column_exists(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100)
        df = _build_sequences_df(bars)
        assert "session_frac" in df.columns

    def test_first_bar_zero(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100)
        df = _build_sequences_df(bars)
        assert df["session_frac"].iloc[0] == pytest.approx(0.0)

    def test_last_bar_one(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(100)
        df = _build_sequences_df(bars)
        assert df["session_frac"].iloc[-1] == pytest.approx(1.0)

    def test_bounded_zero_one(self):
        from volforecast.data.micro import _build_sequences_df

        bars = _make_bars(200)
        df = _build_sequences_df(bars)
        vals = df["session_frac"].values
        assert (vals >= 0.0).all()
        assert (vals <= 1.0 + 1e-10).all()

    def test_values_for_known_bars(self):
        from volforecast.data.micro import _build_sequences_df

        n = 100
        bars = _make_bars(n)
        df = _build_sequences_df(bars)
        expected = np.arange(n) / (n - 1)
        np.testing.assert_allclose(df["session_frac"].values, expected, atol=1e-12)


class TestMultiDay:
    """Verify new features reset correctly across day boundaries."""

    def test_cum_rv_resets_per_day(self):
        from volforecast.data.micro import _build_sequences_df

        rng = np.random.default_rng(42)
        bars = {}
        for i, d in enumerate([date(2024, 6, 1), date(2024, 6, 2)]):
            bars[d] = pd.DataFrame(
                {
                    "buy_vol": rng.uniform(50, 500, size=50),
                    "sell_vol": rng.uniform(50, 500, size=50),
                    "neutral_vol": rng.uniform(0, 50, size=50),
                    "vwap": 200.0 + np.cumsum(rng.normal(0, 0.1, size=50)),
                    "n_trades": rng.integers(10, 200, size=50),
                }
            )

        df = _build_sequences_df(bars)
        day1 = df[df["date"] == date(2024, 6, 1)]
        day2 = df[df["date"] == date(2024, 6, 2)]

        # cum_rv should start at 0 for each day
        assert day1["cum_rv"].iloc[0] == pytest.approx(0.0)
        assert day2["cum_rv"].iloc[0] == pytest.approx(0.0)

        # session_frac should start at 0 for each day
        assert day1["session_frac"].iloc[0] == pytest.approx(0.0)
        assert day2["session_frac"].iloc[0] == pytest.approx(0.0)

        # price_accel should be 0 for first bar of each day
        assert day1["price_accel"].iloc[0] == 0.0
        assert day2["price_accel"].iloc[0] == 0.0
