"""Tests for Layer 2 options-implied features."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.features.options import (
    OptionsLayer,
    compute_butterfly,
    compute_skew,
    compute_term_slope,
    compute_vrp,
)


@pytest.fixture
def synthetic_iv_data():
    """Synthetic IV surface data for testing."""
    dates = pd.bdate_range("2020-01-01", periods=500, freq="B")
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "atm_iv_1m": 18.0 + rng.normal(0, 2, 500),
            "atm_iv_3m": 19.5 + rng.normal(0, 2, 500),
            "skew_1m": 4.0 + rng.normal(0, 1, 500),
        },
        index=dates,
    )


@pytest.fixture
def daily_data(synthetic_iv_data):
    """Daily data with RV column aligned to IV data."""
    rng = np.random.default_rng(99)
    return pd.DataFrame(
        {"rv": 0.0002 + rng.exponential(0.0001, len(synthetic_iv_data))},
        index=synthetic_iv_data.index,
    )


class TestComputeVRP:
    """Tests for compute_vrp (ex-post VRP proxy per Carr & Wu 2009, RFS).

    This tests the simplified 'realized VRP' = IV^2 - RV_daily * 252.
    For the conditional VRP (Bollerslev et al. 2009), see test_iv_features.py.
    """

    def test_vrp_positive_when_iv_above_rv(self):
        """IV=30% annualized vol, daily RV=0.0003. VRP should be positive."""
        atm_iv = pd.Series([30.0])  # 30%
        rv = pd.Series([0.0003])  # daily RV, annualized = 0.0003*252 = 0.0756
        vrp = compute_vrp(atm_iv, rv)
        # VRP = (30/100)^2 - 0.0003*252 = 0.09 - 0.0756 = 0.0144
        assert vrp.iloc[0] > 0
        assert vrp.iloc[0] == pytest.approx(0.09 - 0.0756, abs=1e-10)

    def test_vrp_negative_when_rv_spikes(self):
        """High RV spike makes VRP negative."""
        atm_iv = pd.Series([20.0])  # 20% IV
        rv = pd.Series([0.002])  # daily RV, annualized = 0.504
        vrp = compute_vrp(atm_iv, rv)
        # VRP = (20/100)^2 - 0.002*252 = 0.04 - 0.504 = -0.464
        assert vrp.iloc[0] < 0

    def test_vrp_formula_exact(self):
        """Verify exact formula: (iv/100)^2 - rv*252."""
        atm_iv = pd.Series([25.0, 15.0])
        rv = pd.Series([0.0002, 0.0001])
        vrp = compute_vrp(atm_iv, rv)
        expected = (atm_iv / 100.0) ** 2 - rv * 252.0
        pd.testing.assert_series_equal(vrp, expected)


class TestComputeSkew:
    """Tests for compute_skew."""

    def test_skew_sign(self):
        """Put IV > call IV -> positive skew."""
        put_iv = pd.Series([25.0, 22.0])
        call_iv = pd.Series([18.0, 20.0])
        skew = compute_skew(put_iv, call_iv)
        assert skew.iloc[0] > 0  # 25 - 18 = 7
        assert skew.iloc[1] > 0  # 22 - 20 = 2

    def test_skew_negative(self):
        """Call IV > put IV -> negative skew (unusual)."""
        put_iv = pd.Series([15.0])
        call_iv = pd.Series([20.0])
        skew = compute_skew(put_iv, call_iv)
        assert skew.iloc[0] < 0


class TestComputeTermSlope:
    """Tests for compute_term_slope."""

    def test_term_slope_sign(self):
        """3m > 1m -> positive slope (contango)."""
        atm_short = pd.Series([18.0, 25.0])
        atm_long = pd.Series([20.0, 22.0])
        slope = compute_term_slope(atm_short, atm_long)
        assert slope.iloc[0] > 0  # 20 - 18 = 2
        assert slope.iloc[1] < 0  # 22 - 25 = -3 (backwardation)

    def test_term_slope_formula(self):
        """Verify: slope = long - short."""
        atm_short = pd.Series([18.0])
        atm_long = pd.Series([20.0])
        slope = compute_term_slope(atm_short, atm_long)
        assert slope.iloc[0] == pytest.approx(2.0)


class TestComputeButterfly:
    """Tests for compute_butterfly."""

    def test_butterfly_nonneg(self):
        """Well-behaved smile: butterfly >= 0."""
        # put and call both above ATM -> positive convexity
        put_iv = pd.Series([25.0, 22.0])
        call_iv = pd.Series([21.0, 20.0])
        atm_iv = pd.Series([20.0, 19.0])
        butterfly = compute_butterfly(put_iv, call_iv, atm_iv)
        # 0.5*(25+21) - 20 = 23 - 20 = 3
        assert butterfly.iloc[0] == pytest.approx(3.0)
        # 0.5*(22+20) - 19 = 21 - 19 = 2
        assert butterfly.iloc[1] == pytest.approx(2.0)
        assert (butterfly >= 0).all()

    def test_butterfly_formula(self):
        """Verify exact formula: 0.5*(put+call) - atm."""
        put_iv = pd.Series([30.0])
        call_iv = pd.Series([22.0])
        atm_iv = pd.Series([24.0])
        butterfly = compute_butterfly(put_iv, call_iv, atm_iv)
        # 0.5*(30+22) - 24 = 26 - 24 = 2
        assert butterfly.iloc[0] == pytest.approx(2.0)


class TestOptionsLayer:
    """Tests for OptionsLayer.compute()."""

    def test_graceful_degradation_no_context(self, daily_data):
        """context=None returns empty DataFrame (graceful degradation)."""
        layer = OptionsLayer()
        result = layer.compute(daily_data, context=None)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(daily_data)
        assert result.columns.tolist() == []

    def test_graceful_degradation_no_iv_key(self, daily_data):
        """context without 'iv_surface' key returns empty DataFrame."""
        layer = OptionsLayer()
        result = layer.compute(daily_data, context={"other_key": pd.DataFrame()})
        assert isinstance(result, pd.DataFrame)
        assert result.columns.tolist() == []

    def test_no_lookahead(self, daily_data, synthetic_iv_data):
        """Features at t use data available at end of day t. Rolling columns have warmup NaN."""
        layer = OptionsLayer()
        iv_data = synthetic_iv_data.copy()
        iv_data["iv_put_25d"] = iv_data["atm_iv_1m"] + iv_data["skew_1m"] / 2
        iv_data["iv_call_25d"] = iv_data["atm_iv_1m"] - iv_data["skew_1m"] / 2
        context = {"iv_surface": iv_data}
        result = layer.compute(daily_data, context=context)

        # Weekly rolling columns should be NaN for first 4 rows
        assert result["vrp_w"].iloc[:4].isna().all()
        assert not result["vrp_w"].iloc[4:].isna().all()

    def test_column_names(self, daily_data, synthetic_iv_data):
        """Verify expected output columns exist."""
        layer = OptionsLayer()
        iv_data = synthetic_iv_data.copy()
        iv_data["iv_put_25d"] = iv_data["atm_iv_1m"] + iv_data["skew_1m"] / 2
        iv_data["iv_call_25d"] = iv_data["atm_iv_1m"] - iv_data["skew_1m"] / 2
        iv_data["vts"] = iv_data["atm_iv_3m"] / iv_data["atm_iv_1m"]
        iv_data["forward_vol_1m3m"] = 0.17 + np.random.default_rng(1).normal(0, 0.01, len(iv_data))
        context = {"iv_surface": iv_data}
        result = layer.compute(daily_data, context=context)

        expected_cols = [
            "log_atm_iv_d",
            "log_atm_iv_w",
            "log_atm_iv_m",
            "vrp_d",
            "vrp_w",
            "vrp_m",
            "iv_skew_d",
            "iv_skew_w",
            "iv_term_slope_d",
            "iv_butterfly_d",
            "vts_d",
            "forward_vol_1m3m_d",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_vts_emitted(self, daily_data, synthetic_iv_data):
        """VTS column is emitted when present in iv_surface."""
        layer = OptionsLayer()
        iv_data = synthetic_iv_data.copy()
        iv_data["vts"] = iv_data["atm_iv_3m"] / iv_data["atm_iv_1m"]
        context = {"iv_surface": iv_data}
        result = layer.compute(daily_data, context=context)
        assert "vts_d" in result.columns
        # VTS values should pass through from iv_data
        pd.testing.assert_series_equal(
            result["vts_d"],
            iv_data["vts"].reindex(daily_data.index),
            check_names=False,
        )

    def test_forward_vol_emitted(self, daily_data, synthetic_iv_data):
        """Forward vol column is emitted when present in iv_surface."""
        layer = OptionsLayer()
        iv_data = synthetic_iv_data.copy()
        iv_data["forward_vol_1m3m"] = 0.17
        context = {"iv_surface": iv_data}
        result = layer.compute(daily_data, context=context)
        assert "forward_vol_1m3m_d" in result.columns
        assert (result["forward_vol_1m3m_d"] == 0.17).all()

    def test_vts_not_emitted_when_absent(self, daily_data, synthetic_iv_data):
        """VTS column is not emitted when absent from iv_surface."""
        layer = OptionsLayer()
        iv_data = synthetic_iv_data.copy()
        iv_data["iv_put_25d"] = iv_data["atm_iv_1m"] + iv_data["skew_1m"] / 2
        iv_data["iv_call_25d"] = iv_data["atm_iv_1m"] - iv_data["skew_1m"] / 2
        context = {"iv_surface": iv_data}
        result = layer.compute(daily_data, context=context)
        assert "vts_d" not in result.columns
        assert "forward_vol_1m3m_d" not in result.columns

    def test_vrp_values_correct(self, daily_data, synthetic_iv_data):
        """VRP features match manual computation."""
        layer = OptionsLayer()
        iv_data = synthetic_iv_data.copy()
        iv_data["iv_put_25d"] = iv_data["atm_iv_1m"] + iv_data["skew_1m"] / 2
        iv_data["iv_call_25d"] = iv_data["atm_iv_1m"] - iv_data["skew_1m"] / 2
        context = {"iv_surface": iv_data}
        result = layer.compute(daily_data, context=context)

        # Manual VRP computation: IV^2/annualized - RV*annualized
        vrp_manual = (iv_data["atm_iv_1m"] / 100.0) ** 2 - daily_data["rv"] * 252.0
        # vrp_d uses current-day data (no shift)
        expected_vrp_d = vrp_manual
        pd.testing.assert_series_equal(result["vrp_d"], expected_vrp_d, check_names=False)

    def test_output_shape(self, daily_data, synthetic_iv_data):
        """Output has same index as daily_data."""
        layer = OptionsLayer()
        iv_data = synthetic_iv_data.copy()
        iv_data["iv_put_25d"] = iv_data["atm_iv_1m"] + iv_data["skew_1m"] / 2
        iv_data["iv_call_25d"] = iv_data["atm_iv_1m"] - iv_data["skew_1m"] / 2
        context = {"iv_surface": iv_data}
        result = layer.compute(daily_data, context=context)

        assert len(result) == len(daily_data)
        assert result.index.equals(daily_data.index)


class TestOptionsLayerNewPath:
    """Tests for OptionsLayer.compute() using new per-symbol IV path.

    In the new path, IV columns are pre-merged into daily_data by IVSurfaceLayer.
    """

    @pytest.fixture
    def daily_data_with_iv(self):
        """Daily data with IV columns pre-merged (as IVSurfaceLayer would do)."""
        dates = pd.bdate_range("2020-01-01", periods=500, freq="B")
        rng = np.random.default_rng(42)
        return pd.DataFrame(
            {
                "rv": 0.0002 + rng.exponential(0.0001, 500),
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 500),
                "iv_3m_atm": 19.5 + rng.normal(0, 2, 500),
                "iv_1m_25dp": 22.0 + rng.normal(0, 2, 500),
                "vvix": 90.0 + rng.normal(0, 5, 500),
                "vix": 20.0 + rng.normal(0, 3, 500),
                "iv_dispersion": 8.0 + rng.normal(0, 1, 500),
            },
            index=dates,
        )

    def test_new_path_produces_features(self, daily_data_with_iv):
        """When iv_1m_atm is in daily_data, new path is used."""
        layer = OptionsLayer()
        result = layer.compute(daily_data_with_iv, context=None)

        assert not result.empty
        expected_cols = [
            "log_atm_iv_d",
            "log_atm_iv_w",
            "log_atm_iv_m",
            "vrp_d",
            "vrp_w",
            "vrp_m",
            "iv_rv_gap_d",
            "iv_term_slope_d",
            "iv_term_slope_w",
            "iv_skew_d",
            "iv_skew_w",
            "iv_momentum_d",
            "vvix_d",
            "vvix_innovation_d",
            "atm_iv_x_log_rv_d",
            "atm_iv_x_log_rv_w",
            "atm_iv_x_log_rv_m",
            "vix_x_log_rv_d",
            "vix_x_log_rv_w",
            "vix_x_log_rv_m",
            "iv_dispersion_d",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_new_path_vrp_formula(self, daily_data_with_iv):
        """VRP = (iv/100)^2 - rv*252 exact match."""
        layer = OptionsLayer()
        result = layer.compute(daily_data_with_iv)
        iv = daily_data_with_iv["iv_1m_atm"]
        expected_vrp = (iv / 100.0) ** 2 - daily_data_with_iv["rv"] * 252.0
        pd.testing.assert_series_equal(result["vrp_d"], expected_vrp, check_names=False)

    def test_new_path_skew_formula(self, daily_data_with_iv):
        """Skew fallback = iv_1m_25dp - iv_1m_atm when 25dc missing."""
        layer = OptionsLayer()
        result = layer.compute(daily_data_with_iv)
        expected_skew = daily_data_with_iv["iv_1m_25dp"] - daily_data_with_iv["iv_1m_atm"]
        pd.testing.assert_series_equal(result["iv_skew_d"], expected_skew, check_names=False)

    def test_new_path_term_slope(self, daily_data_with_iv):
        """Term slope = iv_3m_atm - iv_1m_atm."""
        layer = OptionsLayer()
        result = layer.compute(daily_data_with_iv)
        expected_slope = daily_data_with_iv["iv_3m_atm"] - daily_data_with_iv["iv_1m_atm"]
        pd.testing.assert_series_equal(result["iv_term_slope_d"], expected_slope, check_names=False)

    def test_new_path_vvix_decimal(self, daily_data_with_iv):
        """VVIX is converted to decimal (divide by 100)."""
        layer = OptionsLayer()
        result = layer.compute(daily_data_with_iv)
        expected_vvix_d = daily_data_with_iv["vvix"] / 100.0
        pd.testing.assert_series_equal(result["vvix_d"], expected_vvix_d, check_names=False)

    def test_new_path_dispersion_passthrough(self, daily_data_with_iv):
        """IV dispersion is passed through directly."""
        layer = OptionsLayer()
        result = layer.compute(daily_data_with_iv)
        pd.testing.assert_series_equal(
            result["iv_dispersion_d"],
            daily_data_with_iv["iv_dispersion"],
            check_names=False,
        )

    def test_new_path_output_shape(self, daily_data_with_iv):
        """Output has same index as input."""
        layer = OptionsLayer()
        result = layer.compute(daily_data_with_iv)
        assert len(result) == len(daily_data_with_iv)
        assert result.index.equals(daily_data_with_iv.index)

    def test_true_skew_with_call_wing(self):
        """True skew = iv_1m_25dp - iv_1m_25dc when both wings present."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        daily = pd.DataFrame(
            {
                "rv": 0.0002 + rng.exponential(0.0001, 100),
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 100),
                "iv_3m_atm": 19.5 + rng.normal(0, 2, 100),
                "iv_1m_25dp": 22.0 + rng.normal(0, 2, 100),
                "iv_1m_25dc": 16.0 + rng.normal(0, 2, 100),
                "vvix": 90.0 + rng.normal(0, 5, 100),
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        expected_skew = daily["iv_1m_25dp"] - daily["iv_1m_25dc"]
        pd.testing.assert_series_equal(result["iv_skew_d"], expected_skew, check_names=False)

    def test_butterfly_with_call_wing(self):
        """Butterfly = 0.5*(25dp + 25dc) - ATM."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        daily = pd.DataFrame(
            {
                "rv": 0.0002 + rng.exponential(0.0001, 100),
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 100),
                "iv_3m_atm": 19.5 + rng.normal(0, 2, 100),
                "iv_1m_25dp": 22.0 + rng.normal(0, 2, 100),
                "iv_1m_25dc": 16.0 + rng.normal(0, 2, 100),
                "vvix": 90.0 + rng.normal(0, 5, 100),
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        expected_bf = 0.5 * (daily["iv_1m_25dp"] + daily["iv_1m_25dc"]) - daily["iv_1m_atm"]
        pd.testing.assert_series_equal(result["iv_butterfly_d"], expected_bf, check_names=False)
        assert "iv_butterfly_w" in result.columns

    def test_no_butterfly_without_call_wing(self, daily_data_with_iv):
        """Butterfly not produced when iv_1m_25dc is absent."""
        layer = OptionsLayer()
        result = layer.compute(daily_data_with_iv, context=None)
        assert "iv_butterfly_d" not in result.columns

    def test_vix_based_realized_vol(self):
        """realized_vol_of_vix_d uses actual VIX log-returns, not ATM IV."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        vix_levels = 20.0 + rng.normal(0, 2, 100)
        daily = pd.DataFrame(
            {
                "rv": 0.0002 + rng.exponential(0.0001, 100),
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 100),
                "vvix": 90.0 + rng.normal(0, 5, 100),
                "vix": vix_levels,
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        # Verify realized_vol_of_vix uses VIX, not ATM IV
        vix = daily["vix"]
        log_ret_vix = np.log(vix / vix.shift(1))
        expected_rvol = np.sqrt(252 * (log_ret_vix**2).rolling(22).mean())
        pd.testing.assert_series_equal(
            result["realized_vol_of_vix_d"], expected_rvol, check_names=False
        )

    def test_vix_x_log_rv_uses_actual_vix(self):
        """vix_x_log_rv_d uses actual VIX when available."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        vix_levels = 20.0 + rng.normal(0, 2, 100)
        daily = pd.DataFrame(
            {
                "rv": 0.0002 + rng.exponential(0.0001, 100),
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 100),
                "vix": vix_levels,
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        log_rv = np.log(daily["rv"].clip(lower=1e-10))
        expected = daily["vix"] * log_rv
        pd.testing.assert_series_equal(result["vix_x_log_rv_d"], expected, check_names=False)

    def test_multi_horizon_iv_interactions(self):
        """Weekly/monthly IV x log(RV) interactions computed correctly."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        rv = 0.0002 + rng.exponential(0.0001, 100)
        atm_iv = 18.0 + rng.normal(0, 2, 100)
        vix = 20.0 + rng.normal(0, 2, 100)
        daily = pd.DataFrame(
            {"rv": rv, "iv_1m_atm": atm_iv, "vix": vix},
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        # Expected: compute log_rv_w and log_rv_m locally (no HAR columns)
        log_rv_w = np.log(daily["rv"].rolling(5).mean().clip(lower=1e-10))
        log_rv_m = np.log(daily["rv"].rolling(22).mean().clip(lower=1e-10))

        pd.testing.assert_series_equal(
            result["atm_iv_x_log_rv_w"], daily["iv_1m_atm"] * log_rv_w, check_names=False
        )
        pd.testing.assert_series_equal(
            result["atm_iv_x_log_rv_m"], daily["iv_1m_atm"] * log_rv_m, check_names=False
        )
        pd.testing.assert_series_equal(
            result["vix_x_log_rv_w"], daily["vix"] * log_rv_w, check_names=False
        )
        pd.testing.assert_series_equal(
            result["vix_x_log_rv_m"], daily["vix"] * log_rv_m, check_names=False
        )

    def test_multi_horizon_iv_interactions_uses_precomputed(self):
        """When log_rv_w/m from HAR layer exist, those are used directly."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        rv = 0.0002 + rng.exponential(0.0001, 100)
        atm_iv = 18.0 + rng.normal(0, 2, 100)
        # Pre-computed HAR columns (shifted differently to distinguish)
        log_rv_w_har = np.log(pd.Series(rv).rolling(5).mean().clip(lower=1e-10)).shift(1)
        log_rv_m_har = np.log(pd.Series(rv).rolling(22).mean().clip(lower=1e-10)).shift(1)
        daily = pd.DataFrame(
            {
                "rv": rv,
                "iv_1m_atm": atm_iv,
                "log_rv_w": log_rv_w_har.values,
                "log_rv_m": log_rv_m_har.values,
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        # Should use the pre-computed (shifted) versions, not recompute
        expected_w = daily["iv_1m_atm"] * daily["log_rv_w"]
        expected_m = daily["iv_1m_atm"] * daily["log_rv_m"]
        pd.testing.assert_series_equal(result["atm_iv_x_log_rv_w"], expected_w, check_names=False)
        pd.testing.assert_series_equal(result["atm_iv_x_log_rv_m"], expected_m, check_names=False)

    def test_1w_atm_iv_features_when_present(self):
        """When iv_1w_atm is in daily_data, produce log_atm_iv_1w_d and term_slope_1w1m."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        daily = pd.DataFrame(
            {
                "rv": 0.0002 + rng.exponential(0.0001, 100),
                "iv_1w_atm": 20.0 + rng.normal(0, 3, 100),
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 100),
                "iv_3m_atm": 19.5 + rng.normal(0, 2, 100),
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        # log_atm_iv_1w_d = log(iv_1w_atm)
        assert "log_atm_iv_1w_d" in result.columns
        expected_log = np.log(daily["iv_1w_atm"].clip(lower=1e-20))
        pd.testing.assert_series_equal(result["log_atm_iv_1w_d"], expected_log, check_names=False)

        # iv_term_slope_1w1m_d = iv_1m_atm - iv_1w_atm (positive in contango)
        assert "iv_term_slope_1w1m_d" in result.columns
        expected_slope = daily["iv_1m_atm"] - daily["iv_1w_atm"]
        pd.testing.assert_series_equal(
            result["iv_term_slope_1w1m_d"], expected_slope, check_names=False
        )

    def test_no_1w_features_when_absent(self):
        """When iv_1w_atm is NOT in daily_data, 1w features are not produced."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        daily = pd.DataFrame(
            {
                "rv": 0.0002 + rng.exponential(0.0001, 100),
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 100),
                "iv_3m_atm": 19.5 + rng.normal(0, 2, 100),
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        assert "log_atm_iv_1w_d" not in result.columns
        assert "iv_term_slope_1w1m_d" not in result.columns

    def test_0dte_log_ratio_feature(self):
        """log_iv_0dte_1w_ratio_d = log(iv_0dte_atm) - log(iv_1w_atm)."""
        dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        daily = pd.DataFrame(
            {
                "rv": 0.0002 + rng.exponential(0.0001, 100),
                "iv_1w_atm": 15.0 + rng.normal(0, 2, 100),
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 100),
                "iv_3m_atm": 19.5 + rng.normal(0, 2, 100),
                "iv_0dte_atm": 16.0 + rng.normal(0, 3, 100),
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        assert "log_iv_0dte_1w_ratio_d" in result.columns
        expected = np.log(daily["iv_0dte_atm"].clip(lower=1e-20)) - np.log(
            daily["iv_1w_atm"].clip(lower=1e-20)
        )
        pd.testing.assert_series_equal(
            result["log_iv_0dte_1w_ratio_d"], expected, check_names=False
        )

    def test_vix_futures_term_structure_features(self):
        """VIX futures term structure features: slope, curvature, basis."""
        dates = pd.bdate_range("2020-01-01", periods=30, freq="B")
        rng = np.random.default_rng(77)
        vx1 = 18.0 + rng.normal(0, 1, 30)
        vx2 = 20.0 + rng.normal(0, 1, 30)
        vx3 = 21.5 + rng.normal(0, 1, 30)
        vix = 17.0 + rng.normal(0, 1, 30)
        daily = pd.DataFrame(
            {
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 30),
                "rv": 0.0002 + rng.exponential(0.0001, 30),
                "vx1": vx1,
                "vx2": vx2,
                "vx3": vx3,
                "vix": vix,
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        # Daily features present
        assert "vix_term_slope_d" in result.columns
        assert "vix_term_curvature_d" in result.columns
        assert "vix_basis_d" in result.columns

        # Arithmetic correctness
        expected_slope = pd.Series(vx2 - vx1, index=dates)
        expected_curvature = pd.Series(vx3 - 2 * vx2 + vx1, index=dates)
        expected_basis = pd.Series(vx1 - vix, index=dates)
        pd.testing.assert_series_equal(
            result["vix_term_slope_d"], expected_slope, check_names=False
        )
        pd.testing.assert_series_equal(
            result["vix_term_curvature_d"], expected_curvature, check_names=False
        )
        pd.testing.assert_series_equal(
            result["vix_basis_d"], expected_basis, check_names=False
        )

        # Weekly variants are 5d rolling means
        assert "vix_term_slope_w" in result.columns
        assert "vix_term_curvature_w" in result.columns
        assert "vix_basis_w" in result.columns
        pd.testing.assert_series_equal(
            result["vix_term_slope_w"],
            expected_slope.rolling(5).mean(),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            result["vix_term_curvature_w"],
            expected_curvature.rolling(5).mean(),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            result["vix_basis_w"],
            expected_basis.rolling(5).mean(),
            check_names=False,
        )

    def test_vix_futures_graceful_skip(self):
        """No VIX futures features when vx1/vx2 not in daily_data."""
        dates = pd.bdate_range("2020-01-01", periods=30, freq="B")
        rng = np.random.default_rng(42)
        daily = pd.DataFrame(
            {
                "iv_1m_atm": 18.0 + rng.normal(0, 2, 30),
                "rv": 0.0002 + rng.exponential(0.0001, 30),
                "vix": 17.0 + rng.normal(0, 1, 30),
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily, context=None)

        vix_futures_cols = [
            "vix_term_slope_d",
            "vix_term_slope_w",
            "vix_term_curvature_d",
            "vix_term_curvature_w",
            "vix_basis_d",
            "vix_basis_w",
        ]
        for col in vix_futures_cols:
            assert col not in result.columns, f"Unexpected column: {col}"
