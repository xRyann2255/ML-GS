"""Tests for IVSurfaceLayer — per-symbol IV data loading and merging."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from volforecast.features.iv_surface import IVSurfaceLayer


@pytest.fixture
def daily_data():
    """Minimal daily_data with 100 business days."""
    dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
    return pd.DataFrame(
        {"rv": np.random.default_rng(42).exponential(0.0002, 100)},
        index=dates,
    )


@pytest.fixture
def mock_iv_parquet(daily_data):
    """Simulated per-symbol IV parquet content."""
    return pd.DataFrame(
        {
            "iv_1m_atm": 20.0 + np.arange(100) * 0.1,
            "iv_3m_atm": 21.0 + np.arange(100) * 0.05,
            "iv_1m_25dp": 24.0 + np.arange(100) * 0.12,
        },
        index=daily_data.index,
    )


@pytest.fixture
def mock_vvix(daily_data):
    """Simulated VVIX data."""
    return pd.DataFrame({"close": 90.0 + np.arange(100) * 0.1}, index=daily_data.index)


@pytest.fixture
def mock_market(daily_data):
    """Simulated market dispersion data."""
    return pd.DataFrame({"dispersion": 8.0 + np.arange(100) * 0.01}, index=daily_data.index)


class TestIVSurfaceLayerNoContext:
    """Tests for graceful degradation when context is missing."""

    def test_no_context_returns_empty(self, daily_data):
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context=None)
        assert result.empty
        assert len(result) == len(daily_data)

    def test_no_symbol_in_context_returns_empty(self, daily_data):
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context={})
        assert result.empty
        assert len(result) == len(daily_data)

    def test_empty_context_preserves_index(self, daily_data):
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context=None)
        assert result.index.equals(daily_data.index)


class TestIVSurfaceLayerWithData:
    """Tests for IVSurfaceLayer with mocked data loading."""

    @pytest.fixture(autouse=True)
    def _mock_0dte(self, monkeypatch):
        """Prevent fetch_0dte_iv and load_edrvs_cache from hitting real data in unit tests."""
        monkeypatch.setattr(
            "volforecast.data.edrvol.fetch_0dte_iv",
            lambda *a, **kw: pd.Series(dtype=float, name="iv_0dte"),
        )
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_edrvs_cache",
            lambda: None,
        )

    @patch("volforecast.features.iv_surface.load_iv_cache")
    def test_loads_correct_symbol(self, mock_load, daily_data, mock_iv_parquet):
        mock_load.return_value = mock_iv_parquet
        layer = IVSurfaceLayer()
        layer.compute(daily_data, context={"symbol": "SPY"})

        # First call should be for the symbol
        calls = [c[0][0] for c in mock_load.call_args_list]
        assert "SPY" in calls

    @patch("volforecast.features.iv_surface.load_iv_cache")
    def test_no_shift_same_day_alignment(
        self, mock_load, daily_data, mock_iv_parquet, mock_vvix, mock_market
    ):
        """IV data uses same-day values (no shift) — IV[T] aligns with rv[T]."""

        def side_effect(symbol):
            if symbol == "SPY":
                return mock_iv_parquet
            elif symbol == "_VVIX":
                return mock_vvix
            elif symbol == "_MARKET":
                return mock_market
            return None

        mock_load.side_effect = side_effect
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context={"symbol": "SPY"})

        # First row should have data (no shift applied)
        assert result["iv_1m_atm"].iloc[0] == mock_iv_parquet["iv_1m_atm"].iloc[0]
        # Second row should equal second row of original data
        assert result["iv_1m_atm"].iloc[1] == mock_iv_parquet["iv_1m_atm"].iloc[1]

    @patch("volforecast.features.iv_surface.load_iv_cache")
    def test_output_columns(self, mock_load, daily_data, mock_iv_parquet, mock_vvix, mock_market):
        """Output contains expected columns."""

        def side_effect(symbol):
            if symbol == "SPY":
                return mock_iv_parquet
            elif symbol == "_VVIX":
                return mock_vvix
            elif symbol == "_MARKET":
                return mock_market
            return None

        mock_load.side_effect = side_effect
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context={"symbol": "SPY"})

        expected = {"iv_1m_atm", "iv_3m_atm", "iv_1m_25dp", "vvix", "iv_dispersion"}
        assert expected == set(result.columns)

    @patch("volforecast.features.iv_surface.load_iv_cache")
    def test_symbol_not_found_returns_partial(self, mock_load, daily_data, mock_vvix, mock_market):
        """When symbol has no IV data but VVIX/market exist, returns partial."""

        def side_effect(symbol):
            if symbol == "_VVIX":
                return mock_vvix
            elif symbol == "_MARKET":
                return mock_market
            return None

        mock_load.side_effect = side_effect
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context={"symbol": "UNKNOWN"})

        # Should still have vvix and dispersion
        assert "vvix" in result.columns
        assert "iv_dispersion" in result.columns
        # But no per-symbol IV columns
        assert "iv_1m_atm" not in result.columns

    @patch("volforecast.features.iv_surface.load_iv_cache")
    def test_all_data_missing_returns_empty(self, mock_load, daily_data):
        """When all caches return None, returns empty DataFrame."""
        mock_load.return_value = None
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context={"symbol": "SPY"})
        assert result.empty
        assert len(result) == len(daily_data)

    @patch("volforecast.features.iv_surface.load_iv_cache")
    def test_index_preserved(self, mock_load, daily_data, mock_iv_parquet, mock_vvix, mock_market):
        """Output index matches daily_data index."""

        def side_effect(symbol):
            if symbol == "SPY":
                return mock_iv_parquet
            elif symbol == "_VVIX":
                return mock_vvix
            elif symbol == "_MARKET":
                return mock_market
            return None

        mock_load.side_effect = side_effect
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context={"symbol": "SPY"})
        assert result.index.equals(daily_data.index)

    @patch("volforecast.features.iv_surface.load_iv_cache")
    def test_vvix_no_shift(self, mock_load, daily_data, mock_vvix):
        """VVIX uses same-day value (no shift) — consistent with IV[T] alignment."""

        def side_effect(symbol):
            if symbol == "_VVIX":
                return mock_vvix
            return None

        mock_load.side_effect = side_effect
        layer = IVSurfaceLayer()
        result = layer.compute(daily_data, context={"symbol": "SPY"})

        assert result["vvix"].iloc[0] == mock_vvix.iloc[0, 0]
        assert result["vvix"].iloc[1] == mock_vvix.iloc[1, 0]
