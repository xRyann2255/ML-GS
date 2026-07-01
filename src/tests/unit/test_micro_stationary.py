"""Unit tests for v2 stationary micro features.

Tests the _build_sequences_df v2 output: log_ret, vol_share, buy_ratio,
log_n_trades, abs_ret — stationary, split-invariant features for LSTM.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from volforecast.data.micro import _build_sequences_df


def _make_bars(
    n: int = 100,
    *,
    buy_vol: np.ndarray | None = None,
    sell_vol: np.ndarray | None = None,
    vwap: np.ndarray | None = None,
    n_trades: np.ndarray | None = None,
) -> pd.DataFrame:
    """Helper to create a single day's bar DataFrame."""
    rng = np.random.default_rng(42)
    if buy_vol is None:
        buy_vol = rng.uniform(100, 10000, n)
    if sell_vol is None:
        sell_vol = rng.uniform(100, 10000, n)
    if vwap is None:
        # Random walk midprice starting at 100
        vwap = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    if n_trades is None:
        n_trades = rng.integers(10, 500, n).astype(float)
    return pd.DataFrame({
        "buy_vol": buy_vol,
        "sell_vol": sell_vol,
        "vwap": vwap,
        "n_trades": n_trades,
    })


class TestV2FeaturesComputed:
    """_build_sequences_df output contains all v2 columns."""

    def test_v2_columns_present(self):
        bars = _make_bars(50)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        expected_v2 = {"log_ret", "vol_share", "buy_ratio", "log_n_trades", "abs_ret"}
        assert expected_v2.issubset(set(result.columns))

    def test_v1_columns_preserved(self):
        """V1 columns kept for backward compat."""
        bars = _make_bars(50)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        expected_v1 = {"date", "bar_idx", "buy_vol", "sell_vol", "vwap", "n_trades"}
        assert expected_v1.issubset(set(result.columns))

    def test_net_flow_preserved(self):
        """net_flow kept for downstream discrete_straddle compat."""
        bars = _make_bars(50)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        assert "net_flow" in result.columns
        expected = bars["buy_vol"].values - bars["sell_vol"].values
        np.testing.assert_allclose(result["net_flow"].values, expected)

    def test_empty_input(self):
        result = _build_sequences_df({})
        assert len(result) == 0
        assert "log_ret" in result.columns


class TestFirstBarLogRetZero:
    """First bar of each day has log_ret = 0 (no prior bar reference)."""

    def test_single_day(self):
        bars = _make_bars(100)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        assert result.iloc[0]["log_ret"] == 0.0

    def test_multi_day(self):
        bars1 = _make_bars(50)
        bars2 = _make_bars(60)
        result = _build_sequences_df({
            date(2024, 1, 2): bars1,
            date(2024, 1, 3): bars2,
        })
        # First bar of each day should be 0
        day1 = result[result["date"] == date(2024, 1, 2)]
        day2 = result[result["date"] == date(2024, 1, 3)]
        assert day1.iloc[0]["log_ret"] == 0.0
        assert day2.iloc[0]["log_ret"] == 0.0


class TestVolShareSumsToOne:
    """vol_share across all bars in a day should sum to ~1.0."""

    def test_single_day(self):
        bars = _make_bars(100)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        assert result["vol_share"].sum() == pytest.approx(1.0, abs=1e-8)

    def test_multi_day(self):
        bars1 = _make_bars(50)
        bars2 = _make_bars(60)
        result = _build_sequences_df({
            date(2024, 1, 2): bars1,
            date(2024, 1, 3): bars2,
        })
        day1 = result[result["date"] == date(2024, 1, 2)]
        day2 = result[result["date"] == date(2024, 1, 3)]
        assert day1["vol_share"].sum() == pytest.approx(1.0, abs=1e-8)
        assert day2["vol_share"].sum() == pytest.approx(1.0, abs=1e-8)


class TestBuyRatioBounded:
    """buy_ratio should always be in [0, 1]."""

    def test_bounds(self):
        bars = _make_bars(200)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        assert (result["buy_ratio"] >= 0.0).all()
        assert (result["buy_ratio"] <= 1.0).all()

    def test_all_buy(self):
        bars = _make_bars(10, buy_vol=np.ones(10) * 100, sell_vol=np.zeros(10))
        result = _build_sequences_df({date(2024, 1, 2): bars})
        assert result["buy_ratio"].max() == pytest.approx(1.0, abs=1e-8)

    def test_all_sell(self):
        bars = _make_bars(10, buy_vol=np.zeros(10), sell_vol=np.ones(10) * 100)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        assert result["buy_ratio"].max() == pytest.approx(0.0, abs=1e-8)


class TestAbsRetEqualsAbsLogRet:
    """abs_ret should be |log_ret|."""

    def test_identity(self):
        bars = _make_bars(100)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        np.testing.assert_allclose(
            result["abs_ret"].values,
            np.abs(result["log_ret"].values),
        )


class TestSplitInvariance:
    """Multiplying vwap by 1/10 (simulating split) should not change v2 features."""

    def test_log_ret_invariant(self):
        bars_pre = _make_bars(100)
        bars_post = bars_pre.copy()
        bars_post["vwap"] = bars_post["vwap"] / 10.0  # simulate 10:1 split

        result_pre = _build_sequences_df({date(2024, 1, 2): bars_pre})
        result_post = _build_sequences_df({date(2024, 1, 2): bars_post})

        np.testing.assert_allclose(
            result_pre["log_ret"].values,
            result_post["log_ret"].values,
            atol=1e-12,
        )

    def test_vol_share_invariant(self):
        """vol_share depends on buy_vol/sell_vol, not price — trivially invariant."""
        bars_pre = _make_bars(100)
        bars_post = bars_pre.copy()
        bars_post["vwap"] = bars_post["vwap"] / 10.0

        result_pre = _build_sequences_df({date(2024, 1, 2): bars_pre})
        result_post = _build_sequences_df({date(2024, 1, 2): bars_post})

        np.testing.assert_allclose(
            result_pre["vol_share"].values,
            result_post["vol_share"].values,
            atol=1e-12,
        )

    def test_buy_ratio_invariant(self):
        bars_pre = _make_bars(100)
        bars_post = bars_pre.copy()
        bars_post["vwap"] = bars_post["vwap"] / 10.0

        result_pre = _build_sequences_df({date(2024, 1, 2): bars_pre})
        result_post = _build_sequences_df({date(2024, 1, 2): bars_post})

        np.testing.assert_allclose(
            result_pre["buy_ratio"].values,
            result_post["buy_ratio"].values,
            atol=1e-12,
        )

    def test_abs_ret_invariant(self):
        bars_pre = _make_bars(100)
        bars_post = bars_pre.copy()
        bars_post["vwap"] = bars_post["vwap"] / 10.0

        result_pre = _build_sequences_df({date(2024, 1, 2): bars_pre})
        result_post = _build_sequences_df({date(2024, 1, 2): bars_post})

        np.testing.assert_allclose(
            result_pre["abs_ret"].values,
            result_post["abs_ret"].values,
            atol=1e-12,
        )


class TestNoNaNsInV2Features:
    """V2 features should never produce NaN for valid input."""

    def test_no_nans(self):
        bars = _make_bars(200)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        for col in ["log_ret", "vol_share", "buy_ratio", "log_n_trades", "abs_ret"]:
            assert not result[col].isna().any(), f"NaN found in {col}"

    def test_zero_volume_day(self):
        """Even if all volume is zero, no NaN (eps guard)."""
        bars = _make_bars(10, buy_vol=np.zeros(10), sell_vol=np.zeros(10))
        result = _build_sequences_df({date(2024, 1, 2): bars})
        for col in ["vol_share", "buy_ratio"]:
            assert not result[col].isna().any(), f"NaN in {col} with zero volume"

    def test_constant_price(self):
        """Constant price → log_ret = 0 everywhere (no division issues)."""
        vwap = np.ones(50) * 150.0
        bars = _make_bars(50, vwap=vwap)
        result = _build_sequences_df({date(2024, 1, 2): bars})
        assert (result["log_ret"] == 0.0).all()
