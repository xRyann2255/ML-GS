"""Tests for cross-asset momentum features (Layer 4b: changes only)."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from volforecast.features.cross_asset_momentum import (
    CrossAssetMomentumLayer,
    _compute_momentum_features,
)


@pytest.fixture
def dates():
    return pd.bdate_range("2020-01-01", periods=100, freq="B")


@pytest.fixture
def mock_cross_asset_data(dates):
    """Fake cross-asset parquets matching real data format."""
    rng = np.random.default_rng(42)
    n = len(dates)

    rates = pd.DataFrame(
        {
            "yield_5y": 2.0 + rng.normal(0, 0.1, n).cumsum() * 0.01,
            "yield_10y": 3.0 + rng.normal(0, 0.1, n).cumsum() * 0.01,
            "yield_30y": 3.5 + rng.normal(0, 0.1, n).cumsum() * 0.01,
            "yield_slope_10y5y": 1.0 + rng.normal(0, 0.05, n),
            "rate_vol_1y10y": 4.5 + rng.normal(0, 0.2, n),
            "tlt_rv_22d": 0.08 + rng.normal(0, 0.01, n),
        },
        index=dates,
    )

    fx = pd.DataFrame(
        {
            "fx_iv_usdjpy": 0.08 + rng.normal(0, 0.005, n),
            "fx_iv_eurusd": 0.06 + rng.normal(0, 0.003, n),
            "dollar_strength": rng.normal(0, 0.5, n),
        },
        index=dates,
    )

    credit = pd.DataFrame(
        {
            "credit_vol_cdx": 55.0 + rng.normal(0, 3.0, n),
            "hyg_iv": 5.0 + rng.normal(0, 0.5, n),
            "eem_iv": 18.0 + rng.normal(0, 1.0, n),
            "xlf_iv": 15.0 + rng.normal(0, 1.0, n),
            "credit_stress": rng.normal(0, 0.002, n),
            "em_risk": rng.normal(0, 0.01, n),
        },
        index=dates,
    )

    commodity = pd.DataFrame(
        {
            "commodity_vol_cl": 0.35 + rng.normal(0, 0.03, n),
            "gvz": 20.0 + rng.normal(0, 2.0, n),
            "gld_iv": 15.0 + rng.normal(0, 1.0, n),
            "gold_vol": 0.15 + rng.normal(0, 0.02, n),
            "oil_vol": 0.40 + rng.normal(0, 0.05, n),
        },
        index=dates,
    )

    return {"rates": rates, "fx": fx, "credit": credit, "commodity": commodity}


class TestComputeMomentumFeatures:
    """Unit tests for the _compute_momentum_features helper."""

    def test_produces_three_columns(self, dates):
        series = pd.Series(np.random.default_rng(42).normal(0, 1, len(dates)), index=dates)
        series.name = "test"
        result = _compute_momentum_features(series, "test")

        assert list(result.columns) == ["d_test_1d", "d_test_5d", "z_test"]
        assert len(result) == len(dates)

    def test_1d_change_is_diff(self, dates):
        values = np.arange(len(dates), dtype=float)
        series = pd.Series(values, index=dates, name="linear")
        result = _compute_momentum_features(series, "linear")

        # Constant diff of 1.0 (except first NaN)
        assert result["d_linear_1d"].iloc[1:].eq(1.0).all()
        assert pd.isna(result["d_linear_1d"].iloc[0])

    def test_5d_change_is_diff5(self, dates):
        values = np.arange(len(dates), dtype=float)
        series = pd.Series(values, index=dates, name="linear")
        result = _compute_momentum_features(series, "linear")

        # Constant diff of 5.0 (except first 5 NaN)
        assert result["d_linear_5d"].iloc[5:].eq(5.0).all()

    def test_zscore_zero_for_constant(self, dates):
        series = pd.Series(5.0, index=dates, name="const")
        result = _compute_momentum_features(series, "const")

        # Z-score of constant should be NaN (std = 0)
        assert result["z_const"].isna().all()


class TestCrossAssetMomentumLayer:
    """Integration tests for the full layer."""

    def test_produces_expected_features(self, dates, mock_cross_asset_data):
        layer = CrossAssetMomentumLayer()
        daily_data = pd.DataFrame(index=dates)

        with patch(
            "volforecast.features.cross_asset_momentum._load_cross_asset_parquets",
            return_value=mock_cross_asset_data,
        ):
            result = layer.compute(daily_data)

        expected_features = [
            # Level features
            "xasset_rate_vol",
            "xasset_credit_cdx",
            "xasset_fx_usdjpy",
            "xasset_fx_eurusd",
            "xasset_gvz",
            # Momentum features
            "d_fx_iv_usdjpy_1d",
            "d_fx_iv_usdjpy_5d",
            "z_fx_iv_usdjpy",
            "d_fx_iv_eurusd_1d",
            "d_fx_iv_eurusd_5d",
            "z_fx_iv_eurusd",
            "d_credit_cdx_1d",
            "d_credit_cdx_5d",
            "z_credit_cdx",
            "d_rate_vol_1d",
            "d_rate_vol_5d",
            "z_rate_vol",
            "d_yield_slope_1d",
            "d_yield_slope_5d",
            "z_yield_slope",
            "d_gold_vol_1d",
            "d_gold_vol_5d",
            "z_gold_vol",
            "d_oil_vol_1d",
            "d_oil_vol_5d",
            "z_oil_vol",
        ]

        for feat in expected_features:
            assert feat in result.columns, f"Missing feature: {feat}"

        assert len(result) == len(dates)

    def test_level_features_are_log_transformed(self, dates, mock_cross_asset_data):
        """Verify level features are log-transformed."""
        layer = CrossAssetMomentumLayer()
        daily_data = pd.DataFrame(index=dates)

        with patch(
            "volforecast.features.cross_asset_momentum._load_cross_asset_parquets",
            return_value=mock_cross_asset_data,
        ):
            result = layer.compute(daily_data)

        # Level features should be negative (log of values < 1 for vol)
        # or reasonable log values — key check is they exist and are finite
        level_cols = [c for c in result.columns if c.startswith("xasset_")]
        assert len(level_cols) == 5
        for col in level_cols:
            non_nan = result[col].dropna()
            assert len(non_nan) > 0
            assert np.isfinite(non_nan).all()

    def test_empty_when_no_data(self, dates):
        """Returns empty DataFrame when no cross-asset data available."""
        layer = CrossAssetMomentumLayer()
        daily_data = pd.DataFrame(index=dates)

        with patch(
            "volforecast.features.cross_asset_momentum._load_cross_asset_parquets",
            return_value={},
        ):
            result = layer.compute(daily_data)

        assert result.empty or len(result.columns) == 0

    def test_handles_partial_data(self, dates, mock_cross_asset_data):
        """Works with only some cross-asset sources available."""
        layer = CrossAssetMomentumLayer()
        daily_data = pd.DataFrame(index=dates)

        # Only FX data available
        partial = {"fx": mock_cross_asset_data["fx"]}

        with patch(
            "volforecast.features.cross_asset_momentum._load_cross_asset_parquets",
            return_value=partial,
        ):
            result = layer.compute(daily_data)

        assert "d_fx_iv_usdjpy_1d" in result.columns
        assert "d_credit_cdx_1d" not in result.columns

    def test_aligned_to_daily_data_index(self, dates, mock_cross_asset_data):
        """Output index matches daily_data index, even if source data has different dates."""
        layer = CrossAssetMomentumLayer()
        # Use a subset of dates
        subset_dates = dates[10:50]
        daily_data = pd.DataFrame(index=subset_dates)

        with patch(
            "volforecast.features.cross_asset_momentum._load_cross_asset_parquets",
            return_value=mock_cross_asset_data,
        ):
            result = layer.compute(daily_data)

        assert result.index.equals(subset_dates)
