"""Tests for AggGroupBy bar-fetching and bar-based RV computation.

TDD: Tests written first, implementation follows.
Covers: fetch_bars(), compute_daily_rv_from_bars(), and rv_panel mode='bars'.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from tests.conftest import make_synthetic_ticks
from volforecast.constants import TZ

# ---------------------------------------------------------------------------
# Helpers: synthetic bar data
# ---------------------------------------------------------------------------


def make_synthetic_bars(
    trade_date: date = date(2024, 1, 2),
    n_bars: int = 78,
    price_start: float = 450.0,
    sigma: float = 0.001,
    seed: int = 42,
) -> pd.DataFrame:
    """Create synthetic 5-min bar DataFrame matching fetch_bars output format.

    Parameters
    ----------
    trade_date : date
        Trading day.
    n_bars : int
        Number of 5-min bars (78 = 6.5h / 5min).
    price_start : float
        Starting price.
    sigma : float
        Per-bar return volatility.
    seed : int
        Random seed.

    Returns
    -------
    pd.DataFrame
        Bar DataFrame with columns: time, open, high, low, close, volume, n_ticks.
    """
    rng = np.random.default_rng(seed)

    market_open = datetime(trade_date.year, trade_date.month, trade_date.day, 9, 30, 0)
    times = pd.date_range(start=TZ.localize(market_open), periods=n_bars, freq="5min")

    log_returns = rng.normal(0, sigma, n_bars)
    log_prices = np.log(price_start) + np.cumsum(log_returns)
    close_prices = np.exp(log_prices)

    # Synthetic OHLC: open=prev close, high=max(open,close)+noise, etc.
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = price_start
    high_prices = np.maximum(open_prices, close_prices) * (1 + rng.uniform(0, 0.001, n_bars))
    low_prices = np.minimum(open_prices, close_prices) * (1 - rng.uniform(0, 0.001, n_bars))
    volumes = rng.integers(10000, 500000, n_bars)
    tick_counts = rng.integers(500, 50000, n_bars)

    return pd.DataFrame(
        {
            "time": times,
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "volume": volumes,
            "n_ticks": tick_counts,
        }
    )


# ---------------------------------------------------------------------------
# Tests: fetch_bars response parsing
# ---------------------------------------------------------------------------


class TestFetchBars:
    """Tests for fetch_bars() function."""

    def _make_mock_chunk_response(self, trade_date: date, n_bars: int = 78):
        """Build a mock AggGroupBy response dict as chunk_query returns."""
        market_open = datetime(
            trade_date.year,
            trade_date.month,
            trade_date.day,
            14,
            30,
            0,  # UTC
        )
        times = pd.date_range(start=market_open, periods=n_bars, freq="5min")

        rng = np.random.default_rng(42)
        prices = 450.0 + np.cumsum(rng.normal(0, 0.05, n_bars))

        return {
            "Time": times.tolist(),
            "first_TRDPRC_1": (prices - rng.uniform(0, 0.1, n_bars)).tolist(),
            "max_TRDPRC_1": (prices + rng.uniform(0, 0.3, n_bars)).tolist(),
            "min_TRDPRC_1": (prices - rng.uniform(0, 0.3, n_bars)).tolist(),
            "last_TRDPRC_1": prices.tolist(),
            "sum_TRDVOL_1": rng.integers(10000, 500000, n_bars).tolist(),
            "count_TRDPRC_1": rng.integers(500, 50000, n_bars).tolist(),
        }

    @patch("volforecast.data.chunk_store._ensure_session")
    @patch("volforecast.data.chunk_store.query")
    def test_returns_dict_of_dataframes(self, mock_query_mod, mock_session):
        """fetch_bars returns dict[date, DataFrame] with correct columns."""
        from volforecast.data.chunk_store import fetch_bars

        test_date = date(2024, 1, 2)
        mock_query_mod.chunk_query.return_value = self._make_mock_chunk_response(test_date)

        result = fetch_bars("SPY", [test_date])

        assert isinstance(result, dict)
        assert test_date in result
        df = result[test_date]
        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {"time", "open", "high", "low", "close", "volume", "n_ticks"}
        assert len(df) == 78

    @patch("volforecast.data.chunk_store._ensure_session")
    @patch("volforecast.data.chunk_store.query")
    def test_correct_column_types(self, mock_query_mod, mock_session):
        """All price/volume columns are numeric."""
        from volforecast.data.chunk_store import fetch_bars

        test_date = date(2024, 1, 2)
        mock_query_mod.chunk_query.return_value = self._make_mock_chunk_response(test_date)

        result = fetch_bars("SPY", [test_date])
        df = result[test_date]

        assert df["close"].dtype == np.float64
        assert df["open"].dtype == np.float64
        assert df["volume"].dtype == np.float64 or np.issubdtype(df["volume"].dtype, np.integer)

    @patch("volforecast.data.chunk_store._ensure_session")
    @patch("volforecast.data.chunk_store.query")
    def test_empty_response(self, mock_query_mod, mock_session):
        """Empty chunk_query response returns empty dict."""
        from volforecast.data.chunk_store import fetch_bars

        mock_query_mod.chunk_query.return_value = {}

        result = fetch_bars("SPY", [date(2024, 1, 2)])
        assert result == {} or all(df.empty for df in result.values())

    @patch("volforecast.data.chunk_store._ensure_session")
    @patch("volforecast.data.chunk_store.query")
    def test_multi_day_batch(self, mock_query_mod, mock_session):
        """Multiple days are fetched and split correctly."""
        from volforecast.data.chunk_store import fetch_bars

        dates = [date(2024, 1, 2), date(2024, 1, 3)]

        # Build a two-day response (78 bars each day at UTC times)
        rng = np.random.default_rng(42)
        times_d1 = pd.date_range(start=datetime(2024, 1, 2, 14, 30), periods=78, freq="5min")
        times_d2 = pd.date_range(start=datetime(2024, 1, 3, 14, 30), periods=78, freq="5min")
        all_times = times_d1.tolist() + times_d2.tolist()
        n = 156
        prices = 450.0 + np.cumsum(rng.normal(0, 0.05, n))

        mock_query_mod.chunk_query.return_value = {
            "Time": all_times,
            "first_TRDPRC_1": prices.tolist(),
            "max_TRDPRC_1": (prices + 0.1).tolist(),
            "min_TRDPRC_1": (prices - 0.1).tolist(),
            "last_TRDPRC_1": prices.tolist(),
            "sum_TRDVOL_1": rng.integers(10000, 500000, n).tolist(),
            "count_TRDPRC_1": rng.integers(500, 50000, n).tolist(),
        }

        result = fetch_bars("SPY", dates, batch_size=20)

        assert date(2024, 1, 2) in result
        assert date(2024, 1, 3) in result
        assert len(result[date(2024, 1, 2)]) == 78
        assert len(result[date(2024, 1, 3)]) == 78

    @patch("volforecast.data.chunk_store._ensure_session")
    @patch("volforecast.data.chunk_store.query")
    def test_validates_symbol(self, mock_query_mod, mock_session):
        """Invalid symbol raises ValueError."""
        from volforecast.data.chunk_store import fetch_bars

        with pytest.raises(ValueError, match="not in the symbol universe"):
            fetch_bars("INVALID", [date(2024, 1, 2)])

    @patch("volforecast.data.chunk_store._ensure_session")
    @patch("volforecast.data.chunk_store.query")
    def test_uses_processor(self, mock_query_mod, mock_session):
        """fetch_bars passes an AggGroupBy processor to chunk_query."""
        from volforecast.data.chunk_store import fetch_bars

        test_date = date(2024, 1, 2)
        mock_query_mod.chunk_query.return_value = self._make_mock_chunk_response(test_date)

        fetch_bars("SPY", [test_date])

        # Verify chunk_query was called with processors kwarg
        call_kwargs = mock_query_mod.chunk_query.call_args
        assert "processors" in call_kwargs.kwargs or (len(call_kwargs.args) > 5)


# ---------------------------------------------------------------------------
# Tests: compute_daily_rv_from_bars
# ---------------------------------------------------------------------------


class TestComputeDailyRvFromBars:
    """Tests for compute_daily_rv_from_bars() function."""

    def test_returns_dict_with_expected_keys(self):
        """Output dict has all the standard RV measure keys."""
        from volforecast.data.resample import compute_daily_rv_from_bars

        bars = make_synthetic_bars()
        result = compute_daily_rv_from_bars(bars)

        expected_keys = {
            "rv",
            "log_rv",
            "rq",
            "rtq",
            "bpv",
            "rs_positive",
            "rs_negative",
            "jump_stat",
            "jump_indicator",
            "continuous_variation",
            "jump_variation",
            "j_positive",
            "j_negative",
            "realized_skewness",
            "realized_kurtosis",
            "rk",
            "noise_gap",
            "n_ticks",
            "n_bars",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_rk_and_noise_gap_are_nan(self):
        """RK and noise_gap require tick data; bars version returns NaN."""
        from volforecast.data.resample import compute_daily_rv_from_bars

        bars = make_synthetic_bars()
        result = compute_daily_rv_from_bars(bars)

        assert np.isnan(result["rk"])
        assert np.isnan(result["noise_gap"])

    def test_rv_is_positive(self):
        """Realized variance is always positive."""
        from volforecast.data.resample import compute_daily_rv_from_bars

        bars = make_synthetic_bars()
        result = compute_daily_rv_from_bars(bars)

        assert result["rv"] > 0

    def test_semivariances_sum_to_rv(self):
        """RS+ + RS- = RV (to machine precision)."""
        from volforecast.data.resample import compute_daily_rv_from_bars

        bars = make_synthetic_bars()
        result = compute_daily_rv_from_bars(bars)

        assert abs(result["rs_positive"] + result["rs_negative"] - result["rv"]) < 1e-15

    def test_n_bars_equals_returns_count(self):
        """n_bars should equal number of returns (n_bars_input - 1)."""
        from volforecast.data.resample import compute_daily_rv_from_bars

        bars = make_synthetic_bars(n_bars=78)
        result = compute_daily_rv_from_bars(bars)

        assert result["n_bars"] == 77  # 78 prices -> 77 returns

    def test_n_ticks_sums_bar_counts(self):
        """n_ticks is the sum of per-bar tick counts."""
        from volforecast.data.resample import compute_daily_rv_from_bars

        bars = make_synthetic_bars()
        result = compute_daily_rv_from_bars(bars)

        assert result["n_ticks"] == int(bars["n_ticks"].sum())

    def test_matches_tick_based_rv(self):
        """Bar-based RV should approximately match tick-based RV on the same data.

        We generate ticks, resample to bars manually, then verify both paths give
        similar RV (not identical due to different bar boundary handling).
        """
        from volforecast.data.resample import (
            compute_daily_rv_from_bars,
            compute_daily_rv_from_ticks,
        )

        # Generate synthetic ticks and compute via the tick path
        ticks = make_synthetic_ticks(n_ticks=50000, seed=123)
        tick_result = compute_daily_rv_from_ticks(ticks)

        # Now resample ticks to bars (mimicking what the server would return)
        from volforecast.data.resample import resample_trades_to_bars

        resampled = resample_trades_to_bars(ticks, freq="5min")
        # Build a bar DataFrame from the resampled data
        bars = pd.DataFrame(
            {
                "time": resampled.index,
                "open": resampled["price"].values,  # simplified
                "high": resampled["price"].values,
                "low": resampled["price"].values,
                "close": resampled["price"].values,
                "volume": np.ones(len(resampled)),
                "n_ticks": np.full(len(resampled), 50000 // len(resampled)),
            }
        )

        bar_result = compute_daily_rv_from_bars(bars)

        # RV from bars should match RV from ticks (same close prices)
        assert abs(bar_result["rv"] - tick_result["rv"]) / tick_result["rv"] < 0.01

    def test_log_rv_consistent(self):
        """log_rv = log(rv)."""
        from volforecast.data.resample import compute_daily_rv_from_bars

        bars = make_synthetic_bars()
        result = compute_daily_rv_from_bars(bars)

        assert abs(result["log_rv"] - np.log(result["rv"])) < 1e-10

    def test_empty_bars_raises_or_returns_nan(self):
        """Edge case: empty bar DataFrame."""
        from volforecast.data.resample import compute_daily_rv_from_bars

        empty_bars = pd.DataFrame(
            columns=["time", "open", "high", "low", "close", "volume", "n_ticks"]
        )
        # Should either raise or return NaN-filled dict
        with pytest.raises((ValueError, ZeroDivisionError)):
            compute_daily_rv_from_bars(empty_bars)


# ---------------------------------------------------------------------------
# Tests: rv_panel with mode='bars'
# ---------------------------------------------------------------------------


class TestRvPanelBarsMode:
    """Tests for build_rv_panel with mode='bars'."""

    _TEST_DAYS = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]

    def _mock_fetch_bars(self, symbol, dates, **kwargs):
        """Mock fetch_bars returning synthetic bars per day."""
        result = {}
        for d in dates:
            result[d] = make_synthetic_bars(d, seed=hash(d) % 2**31)
        return result

    @patch("volforecast.data.rv_panel.get_trading_days")
    @patch("volforecast.data.rv_panel.fetch_bars")
    def test_bars_mode_returns_panel(self, mock_fetch_bars, mock_cal):
        """mode='bars' produces a valid panel."""
        from volforecast.data.rv_panel import build_rv_panel

        mock_cal.return_value = self._TEST_DAYS
        mock_fetch_bars.side_effect = self._mock_fetch_bars

        panel = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            mode="bars",
            max_workers=1,
        )

        assert isinstance(panel, pd.DataFrame)
        assert len(panel) == 3
        assert "rv" in panel.columns
        assert "log_rv" in panel.columns

    @patch("volforecast.data.rv_panel.get_trading_days")
    @patch("volforecast.data.rv_panel.fetch_bars")
    def test_bars_mode_rk_is_nan(self, mock_fetch_bars, mock_cal):
        """mode='bars' produces NaN for rk and noise_gap."""
        from volforecast.data.rv_panel import build_rv_panel

        mock_cal.return_value = self._TEST_DAYS
        mock_fetch_bars.side_effect = self._mock_fetch_bars

        panel = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            mode="bars",
            max_workers=1,
        )

        assert panel["rk"].isna().all()
        assert panel["noise_gap"].isna().all()

    @patch("volforecast.data.rv_panel.get_trading_days")
    @patch("volforecast.data.rv_panel.fetch_trades_batch")
    def test_ticks_mode_still_works(self, mock_fetch, mock_cal):
        """mode='ticks' (legacy) still works as before."""
        from volforecast.data.rv_panel import build_rv_panel

        mock_cal.return_value = self._TEST_DAYS

        def _mock_batch(symbol, dates, **kwargs):
            return {d: make_synthetic_ticks(d, seed=hash(d) % 2**31) for d in dates}

        mock_fetch.side_effect = _mock_batch

        panel = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            mode="ticks",
            max_workers=1,
        )

        assert isinstance(panel, pd.DataFrame)
        assert len(panel) == 3
        assert not panel["rk"].isna().all()  # Ticks mode computes RK
