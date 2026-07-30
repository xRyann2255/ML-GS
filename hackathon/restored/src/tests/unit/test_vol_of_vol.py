"""Unit tests for vol_of_vol feature layer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.registry import FEATURE_REGISTRY, ensure_registered


@pytest.fixture
def daily_data():
    """Synthetic daily data with rv column."""
    np.random.seed(42)
    n = 100
    dates = pd.bdate_range("2020-01-01", periods=n)
    rv = np.exp(np.random.randn(n) * 0.5 - 8.0)  # realistic RV scale
    return pd.DataFrame({"rv": rv}, index=dates)


class TestVolOfVolLayer:
    def test_registered(self):
        """vol_of_vol is in FEATURE_REGISTRY."""
        ensure_registered()
        assert "vol_of_vol" in FEATURE_REGISTRY

    def test_output_columns(self, daily_data):
        """compute() returns DataFrame with vov_d and vov_w columns."""
        ensure_registered()
        layer = FEATURE_REGISTRY["vol_of_vol"]()
        result = layer.compute(daily_data)
        assert isinstance(result, pd.DataFrame)
        assert "vov_d" in result.columns
        assert "vov_w" in result.columns
        assert result.index.equals(daily_data.index)

    def test_initial_nans(self, daily_data):
        """First 22 rows of vov_d are NaN (shift(1) + rolling(22))."""
        ensure_registered()
        layer = FEATURE_REGISTRY["vol_of_vol"]()
        result = layer.compute(daily_data)
        # shift(1) makes row 0 NaN, rolling(22) needs 22 valid -> first 22 are NaN
        assert result["vov_d"].iloc[:22].isna().all()
        # Row 22 should be valid (window [1..22] has 22 non-NaN shifted values)
        assert result["vov_d"].iloc[22:].notna().all()

    def test_vov_w_more_nans(self, daily_data):
        """vov_w has more NaN than vov_d (extra rolling(5))."""
        ensure_registered()
        layer = FEATURE_REGISTRY["vol_of_vol"]()
        result = layer.compute(daily_data)
        # vov_w = vov_d.rolling(5).mean() -> needs 4 more valid vov_d rows
        # vov_d valid from index 22, so vov_w valid from index 26
        assert result["vov_w"].iloc[:26].isna().all()
        assert result["vov_w"].iloc[26:].notna().all()

    def test_no_lookahead(self, daily_data):
        """Perturbing future rv values does not change vov_d at earlier dates."""
        ensure_registered()
        layer = FEATURE_REGISTRY["vol_of_vol"]()

        # Compute baseline
        result_base = layer.compute(daily_data)

        # Perturb rv at dates > index 50
        perturbed = daily_data.copy()
        perturbed.iloc[51:, perturbed.columns.get_loc("rv")] = 999.0
        result_perturbed = layer.compute(perturbed)

        # vov_d at index 50 should be unchanged
        # (shift(1) means vov_d[50] uses rv[0:50], not rv[50] itself)
        np.testing.assert_equal(
            result_base["vov_d"].iloc[:51].values,
            result_perturbed["vov_d"].iloc[:51].values,
        )

    def test_compute_contract(self, daily_data):
        """compute() accepts context kwarg."""
        ensure_registered()
        layer = FEATURE_REGISTRY["vol_of_vol"]()
        # Should not raise
        result = layer.compute(daily_data, context=None)
        assert isinstance(result, pd.DataFrame)
