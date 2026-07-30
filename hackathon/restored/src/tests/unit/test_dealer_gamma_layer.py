"""Tests for DealerGammaLayer — SPX GEX data loading and broadcasting."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from volforecast.features.dealer_gamma import DealerGammaLayer

EXPECTED_COLUMNS = {"gex_sign_d", "gex_zscore_d", "gex_quintile_d", "gex_regime_d", "gex_momentum_d"}


@pytest.fixture
def daily_data():
    """Minimal daily_data with 100 business days."""
    dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
    return pd.DataFrame(
        {"rv": np.random.default_rng(42).exponential(0.0002, 100)},
        index=dates,
    )


@pytest.fixture
def mock_gex_cache(daily_data):
    """Simulated GEX cache with matching dates."""
    n = len(daily_data)
    rng = np.random.default_rng(123)
    return pd.DataFrame(
        {
            "date": daily_data.index,
            "gex_net": rng.normal(0, 1e9, n),
            "gex_call": rng.normal(-5e8, 1e8, n),
            "gex_put": rng.normal(5e8, 1e8, n),
            "gex_sign": rng.choice([-1, 0, 1], n),
            "spot": 4500 + rng.normal(0, 50, n),
            "n_valid_contracts": rng.integers(1000, 5000, n),
            "oi_total": rng.integers(100000, 500000, n),
            "oi_pcr": rng.uniform(0.5, 1.5, n),
        }
    )


class TestDealerGammaLayerEmpty:
    """Tests for graceful degradation when GEX cache is missing."""

    @patch("volforecast.features.dealer_gamma.load_gex_cache")
    def test_empty_cache_returns_empty(self, mock_load, daily_data):
        mock_load.return_value = pd.DataFrame()
        layer = DealerGammaLayer()
        result = layer.compute(daily_data)
        assert len(result) == len(daily_data)
        assert result.index.equals(daily_data.index)

    @patch("volforecast.features.dealer_gamma.load_gex_cache")
    def test_empty_cache_no_exception(self, mock_load, daily_data):
        mock_load.return_value = pd.DataFrame()
        layer = DealerGammaLayer()
        # Should not raise
        result = layer.compute(daily_data, context={"symbol": "SPY"})
        assert isinstance(result, pd.DataFrame)


class TestDealerGammaLayerWithData:
    """Tests for DealerGammaLayer with mocked GEX cache."""

    @patch("volforecast.features.dealer_gamma.load_gex_cache")
    def test_produces_expected_columns(self, mock_load, daily_data, mock_gex_cache):
        mock_load.return_value = mock_gex_cache
        layer = DealerGammaLayer()
        result = layer.compute(daily_data)
        assert EXPECTED_COLUMNS.issubset(result.columns), f"Missing columns: {EXPECTED_COLUMNS - set(result.columns)}"

    @patch("volforecast.features.dealer_gamma.load_gex_cache")
    def test_result_aligned_to_input_index(self, mock_load, daily_data, mock_gex_cache):
        mock_load.return_value = mock_gex_cache
        layer = DealerGammaLayer()
        result = layer.compute(daily_data)
        assert result.index.equals(daily_data.index)

    @patch("volforecast.features.dealer_gamma.load_gex_cache")
    def test_broadcast_same_across_symbols(self, mock_load, daily_data, mock_gex_cache):
        """SPX-only signal: same GEX values regardless of symbol context."""
        mock_load.return_value = mock_gex_cache
        layer = DealerGammaLayer()
        result_spy = layer.compute(daily_data, context={"symbol": "SPY"})
        result_aapl = layer.compute(daily_data, context={"symbol": "AAPL"})
        pd.testing.assert_frame_equal(result_spy, result_aapl)

    @patch("volforecast.features.dealer_gamma.load_gex_cache")
    def test_partial_date_coverage(self, mock_load, daily_data):
        """When GEX cache covers only part of daily_data dates, uncovered dates are NaN."""
        # Create cache with only first 50 dates
        n = 50
        rng = np.random.default_rng(456)
        partial_cache = pd.DataFrame(
            {
                "date": daily_data.index[:n],
                "gex_net": rng.normal(0, 1e9, n),
                "gex_call": rng.normal(-5e8, 1e8, n),
                "gex_put": rng.normal(5e8, 1e8, n),
                "gex_sign": rng.choice([-1, 0, 1], n),
                "spot": 4500 + rng.normal(0, 50, n),
                "n_valid_contracts": rng.integers(1000, 5000, n),
                "oi_total": rng.integers(100000, 500000, n),
                "oi_pcr": rng.uniform(0.5, 1.5, n),
            }
        )
        mock_load.return_value = partial_cache
        layer = DealerGammaLayer()
        result = layer.compute(daily_data)
        assert len(result) == len(daily_data)
        # gex_sign_d should have NaN for uncovered dates
        assert result["gex_sign_d"].iloc[n:].isna().all()

    @patch("volforecast.features.dealer_gamma.load_gex_cache")
    def test_gex_sign_values(self, mock_load, daily_data, mock_gex_cache):
        """gex_sign_d should contain only {-1, 0, 1} values."""
        mock_load.return_value = mock_gex_cache
        layer = DealerGammaLayer()
        result = layer.compute(daily_data)
        valid_signs = result["gex_sign_d"].dropna()
        assert set(valid_signs.unique()).issubset({-1, 0, 1})

    @patch("volforecast.features.dealer_gamma.load_gex_cache")
    def test_gex_regime_binary(self, mock_load, daily_data, mock_gex_cache):
        """gex_regime_d should be binary (0 or 1)."""
        mock_load.return_value = mock_gex_cache
        layer = DealerGammaLayer()
        result = layer.compute(daily_data)
        valid_regime = result["gex_regime_d"].dropna()
        assert set(valid_regime.unique()).issubset({0.0, 1.0})
