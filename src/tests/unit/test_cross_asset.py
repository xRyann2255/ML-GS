"""Tests for Layer 4 cross-asset features."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.features.cross_asset import (
    CrossAssetLayer,
    compute_dy_spillover,
    compute_fx_vol,
    compute_treasury_slope,
    compute_vix_rv_ratio,
)


@pytest.fixture
def dates():
    return pd.bdate_range("2020-01-01", periods=300, freq="B")


@pytest.fixture
def context(dates):
    """Full cross-asset context for layer tests."""
    rng = np.random.default_rng(42)
    n = len(dates)
    treasury = pd.DataFrame(
        {"2y": 98.0 + rng.normal(0, 0.5, n), "10y": 95.0 + rng.normal(0, 1.0, n)},
        index=dates,
    )
    fx = pd.DataFrame(
        {"USDJPY": 110.0 + rng.normal(0, 1.0, n)},
        index=dates,
    )
    commodity = pd.DataFrame(
        {"CL": 60.0 + rng.normal(0, 2.0, n), "GC": 1800.0 + rng.normal(0, 20, n)},
        index=dates,
    )
    vix = pd.Series(20.0 + rng.normal(0, 3.0, n), index=dates, name="VIX")
    vix = vix.clip(lower=10.0)  # VIX always positive

    # RV panel for DY spillover (3 assets, small for speed)
    rv_panel = pd.DataFrame(
        {
            "SPY": 0.0002 + rng.exponential(0.0001, n),
            "AAPL": 0.0003 + rng.exponential(0.00015, n),
            "JPM": 0.0002 + rng.exponential(0.00012, n),
        },
        index=dates,
    )

    return {
        "treasury": treasury,
        "fx": fx,
        "commodity": commodity,
        "vix": vix,
        "rv_panel": rv_panel,
    }


class TestTreasurySlope:
    def test_treasury_slope_sign(self):
        """10y > 2y -> positive slope."""
        long_tenor = pd.Series([100.0, 95.0, 90.0])
        short_tenor = pd.Series([98.0, 96.0, 92.0])
        slope = compute_treasury_slope(long_tenor, short_tenor)
        assert slope.iloc[0] > 0  # 100 - 98 = 2
        assert slope.iloc[1] < 0  # 95 - 96 = -1

    def test_treasury_slope_formula(self):
        long_tenor = pd.Series([100.0])
        short_tenor = pd.Series([97.5])
        slope = compute_treasury_slope(long_tenor, short_tenor)
        assert slope.iloc[0] == pytest.approx(2.5)


class TestFXVol:
    def test_fx_vol_positive_and_reasonable(self, dates):
        """FX vol should be in reasonable range (5-25% annualized for majors)."""
        rng = np.random.default_rng(42)
        # Simulate USDJPY with ~10% annualized vol
        fx = pd.Series(110.0 + np.cumsum(rng.normal(0, 0.5, len(dates))), index=dates)
        vol = compute_fx_vol(fx, window=22)
        # Skip NaN warmup period
        valid = vol.dropna()
        assert (valid > 0).all()
        # Annualized vol should be in reasonable range
        assert valid.median() < 0.30  # Not crazy high
        assert valid.median() > 0.01  # Not zero


class TestVIXRVRatio:
    def test_vix_rv_ratio_above_one(self):
        """VIX > annualized RV -> ratio > 1."""
        vix = pd.Series([20.0])  # 20% IV
        rv = pd.Series([0.0001])  # annualized = 0.0252 -> (0.04 / 0.0252) ~ 1.59
        ratio = compute_vix_rv_ratio(vix, rv)
        assert ratio.iloc[0] > 1.0

    def test_vix_rv_ratio_below_one(self):
        """Low VIX, high RV -> ratio < 1."""
        vix = pd.Series([10.0])  # 10% IV
        rv = pd.Series([0.001])  # annualized = 0.252 -> (0.01 / 0.252) ~ 0.04
        ratio = compute_vix_rv_ratio(vix, rv)
        assert ratio.iloc[0] < 1.0


class TestDYSpillover:
    def test_dy_spillover_range(self):
        """Output should be in [0, 100]."""
        rng = np.random.default_rng(42)
        dates = pd.bdate_range("2018-01-01", periods=250, freq="B")
        rv_panel = pd.DataFrame(
            {
                "A": 0.0002 + rng.exponential(0.0001, 250),
                "B": 0.0003 + rng.exponential(0.00015, 250),
                "C": 0.0002 + rng.exponential(0.00012, 250),
            },
            index=dates,
        )
        spillover = compute_dy_spillover(rv_panel, h=10, p=2, window=200)
        valid = spillover.dropna()
        assert len(valid) > 0
        assert (valid >= 0).all()
        assert (valid <= 100).all()


class TestCrossAssetLayer:
    def test_cross_asset_layer_requires_context(self, dates):
        """ValueError without context."""
        layer = CrossAssetLayer()
        daily_data = pd.DataFrame({"rv": np.ones(len(dates)) * 0.0002}, index=dates)
        with pytest.raises(ValueError, match="context"):
            layer.compute(daily_data, context=None)

    def test_cross_asset_no_lookahead(self, dates, context):
        """Rolling-based features have appropriate NaN warmup."""
        layer = CrossAssetLayer()
        daily_data = pd.DataFrame({"rv": np.ones(len(dates)) * 0.0002}, index=dates)
        result = layer.compute(daily_data, context=context)
        # Weekly rolling columns should have NaN for warmup period
        if "treasury_slope_w" in result.columns:
            assert result["treasury_slope_w"].iloc[:4].isna().all()

    def test_cross_asset_column_names(self, dates, context):
        """Verify expected columns exist."""
        layer = CrossAssetLayer()
        daily_data = pd.DataFrame({"rv": np.ones(len(dates)) * 0.0002}, index=dates)
        result = layer.compute(daily_data, context=context)
        expected = [
            "treasury_slope_d",
            "treasury_slope_w",
            "log_fx_vol_d",
            "log_vix_d",
            "log_vix_w",
            "log_vix_m",
            "log_vix_rv_ratio_d",
            "log_commodity_vol_cl_d",
        ]
        for col in expected:
            assert col in result.columns, f"Missing column: {col}"

    def test_treasury_yield_path(self, dates, context):
        """When tsy_yield_* columns present in daily_data, use yield spread."""
        layer = CrossAssetLayer()
        rng = np.random.default_rng(42)
        n = len(dates)
        daily_data = pd.DataFrame(
            {
                "rv": np.ones(n) * 0.0002,
                "tsy_yield_5y": 4.0 + rng.normal(0, 0.1, n),
                "tsy_yield_10y": 4.5 + rng.normal(0, 0.1, n),
            },
            index=dates,
        )
        result = layer.compute(daily_data, context=context)
        # Treasury slope should be yield spread (10y - 5y)
        expected = daily_data["tsy_yield_10y"] - daily_data["tsy_yield_5y"]
        pd.testing.assert_series_equal(result["treasury_slope_d"], expected, check_names=False)

    def test_ovx_path(self, dates, context):
        """When ovx column present in daily_data, use OVX instead of realized CL vol."""
        layer = CrossAssetLayer()
        rng = np.random.default_rng(42)
        n = len(dates)
        daily_data = pd.DataFrame(
            {
                "rv": np.ones(n) * 0.0002,
                "ovx": 30.0 + rng.normal(0, 3, n),
            },
            index=dates,
        )
        result = layer.compute(daily_data, context=context)
        # Should use log(OVX) directly, not realized CL vol
        from volforecast.features.transforms import safe_log

        expected = safe_log(daily_data["ovx"])
        pd.testing.assert_series_equal(
            result["log_commodity_vol_cl_d"], expected, check_names=False
        )
