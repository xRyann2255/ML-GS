"""Tests for TSDB data access: daily OHLCV, treasury, FX, commodity fetching.

TDD: Tests written first, implementations follow.
Uses mocked TSDBSymbol (gs_quant_internal not available outside GS network).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

import volforecast.data.tsdb as tsdb_module
from volforecast.data.tsdb import (
    _get_tsdb_data,
    _ticker_to_ric,
    _tsdb_symbol,
    fetch_commodity_prices,
    fetch_daily_ohlcv,
    fetch_fx_rates,
    fetch_spx_index,
    fetch_treasury_yields,
    fetch_vix,
    fetch_vix_futures,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tsdb_series(start: str, end: str, value: float = 100.0) -> pd.Series:
    """Create a synthetic TSDB-like Series indexed by business dates."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    values = value + np.cumsum(rng.normal(0, 0.5, len(idx)))
    return pd.Series(values, index=idx)


# ---------------------------------------------------------------------------
# Tests: Ticker-to-RIC mapping
# ---------------------------------------------------------------------------


class TestTickerToRic:
    def test_nasdaq_equity(self):
        assert _ticker_to_ric("AAPL") == "AAPL.OQ"
        assert _ticker_to_ric("MSFT") == "MSFT.OQ"
        assert _ticker_to_ric("NVDA") == "NVDA.OQ"

    def test_nyse_equity(self):
        assert _ticker_to_ric("JPM") == "JPM.N"
        assert _ticker_to_ric("XOM") == "XOM.N"

    def test_arca_etf(self):
        assert _ticker_to_ric("SPY") == "SPY.P"
        assert _ticker_to_ric("QQQ") == "QQQ.P"
        assert _ticker_to_ric("IWM") == "IWM.P"
        assert _ticker_to_ric("DIA") == "DIA.P"

    def test_brk_b_special_case(self):
        ric = _ticker_to_ric("BRK.B")
        assert ric == "BRKb.N"

    def test_unknown_ticker_raises(self):
        with pytest.raises(ValueError, match="not in.*universe"):
            _ticker_to_ric("FAKE_TICKER")


class TestTsdbSymbol:
    def test_unadjusted_close(self):
        assert _tsdb_symbol("AAPL.OQ", "close", adjusted=False) == "eqpad_AAPL.OQ@close"

    def test_adjusted_close(self):
        assert (
            _tsdb_symbol("AAPL.OQ", "close", adjusted=True) == "eqpad_AAPL.OQ@close.adj.allincdiv"
        )

    def test_adjusted_open(self):
        assert _tsdb_symbol("AAPL.OQ", "open", adjusted=True) == "eqpad_AAPL.OQ@open.adj.allincdiv"

    def test_adjusted_high(self):
        assert _tsdb_symbol("JPM.N", "high", adjusted=True) == "eqpad_JPM.N@high.adj.allincdiv"

    def test_adjusted_low(self):
        assert _tsdb_symbol("JPM.N", "low", adjusted=True) == "eqpad_JPM.N@low.adj.allincdiv"

    def test_volume_never_adjusted(self):
        assert _tsdb_symbol("SPY.P", "volume", adjusted=False) == "eqpad_SPY.P@volume"
        assert _tsdb_symbol("SPY.P", "volume", adjusted=True) == "eqpad_SPY.P@volume"

    def test_open_high_low_unadjusted(self):
        assert _tsdb_symbol("JPM.N", "open", adjusted=False) == "eqpad_JPM.N@open"
        assert _tsdb_symbol("JPM.N", "high", adjusted=False) == "eqpad_JPM.N@high"
        assert _tsdb_symbol("JPM.N", "low", adjusted=False) == "eqpad_JPM.N@low"


# ---------------------------------------------------------------------------
# Tests: fetch_daily_ohlcv
# ---------------------------------------------------------------------------


class TestFetchDailyOhlcv:
    def test_rejects_unknown_symbol(self):
        with pytest.raises(ValueError, match="not in.*universe"):
            fetch_daily_ohlcv(["FAKE"], date(2024, 1, 2), date(2024, 3, 1))

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_returns_multiindex_dataframe(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01")
        df = fetch_daily_ohlcv(["AAPL"], date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.MultiIndex)
        assert df.index.names == ["date", "symbol"]

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_has_ohlcv_columns(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01")
        df = fetch_daily_ohlcv(["AAPL"], date(2024, 1, 2), date(2024, 3, 1))
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_multiple_symbols(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01")
        df = fetch_daily_ohlcv(["AAPL", "SPY"], date(2024, 1, 2), date(2024, 3, 1))
        symbols_in_index = df.index.get_level_values("symbol").unique()
        assert "AAPL" in symbols_in_index
        assert "SPY" in symbols_in_index

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_adjusted_vs_unadjusted(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01")
        # Should call with adjusted=True by default
        fetch_daily_ohlcv(["AAPL"], date(2024, 1, 2), date(2024, 3, 1), adjusted=True)
        # Verify all price fields (open/high/low/close) use adj suffix
        calls = mock_get.call_args_list
        symbols_called = [c[0][0] for c in calls]
        adj_calls = [s for s in symbols_called if "adj" in s]
        # open, high, low, close all adjusted = 4 adjusted calls
        assert len(adj_calls) == 4
        assert any("open.adj" in s for s in adj_calls)
        assert any("high.adj" in s for s in adj_calls)
        assert any("low.adj" in s for s in adj_calls)
        assert any("close.adj" in s for s in adj_calls)
        # volume should NOT be adjusted
        vol_calls = [s for s in symbols_called if "volume" in s]
        assert all("adj" not in s for s in vol_calls)

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_unadjusted_no_adj_suffix(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01")
        fetch_daily_ohlcv(["AAPL"], date(2024, 1, 2), date(2024, 3, 1), adjusted=False)
        calls = mock_get.call_args_list
        close_calls = [c[0][0] for c in calls if "close" in c[0][0]]
        assert all("adj" not in s for s in close_calls)

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_empty_symbols_list(self, mock_get):
        df = fetch_daily_ohlcv([], date(2024, 1, 2), date(2024, 3, 1))
        assert df.empty


class TestGetTsdbData:
    def test_retries_after_initializing_gs_session(self, monkeypatch):
        class FakeSessionError(Exception):
            pass

        class FakeTsdbSymbol:
            def __init__(self, symbol):
                self.symbol = symbol

            def get_data(self, start, end):
                call_count["get_data"] += 1
                if call_count["get_data"] == 1:
                    raise FakeSessionError("GsSession is not initialised")
                return expected

        class _SessionMeta(type):
            @property
            def current(cls):
                if not cls._initialized:
                    raise FakeSessionError("not init")
                return "active"

        class FakeGsSession(metaclass=_SessionMeta):
            _initialized = False

            @staticmethod
            def use():
                call_count["use"] += 1
                FakeGsSession._initialized = True

        call_count = {"get_data": 0, "use": 0}
        expected = _make_tsdb_series("2024-01-02", "2024-01-05")

        monkeypatch.setattr(tsdb_module, "_HAS_GS_QUANT", True)
        monkeypatch.setattr(tsdb_module, "TSDBSymbol", FakeTsdbSymbol, raising=False)
        monkeypatch.setattr(tsdb_module, "GsSession", FakeGsSession, raising=False)
        monkeypatch.setattr(tsdb_module, "_GS_SESSION_ERRORS", (FakeSessionError,))

        result = _get_tsdb_data("eqpad_AAPL.OQ@close", "2024-01-02", "2024-01-05")

        pd.testing.assert_series_equal(result, expected)
        assert call_count["get_data"] == 2
        assert call_count["use"] >= 1

    def test_raises_connection_error_if_session_init_fails(self, monkeypatch):
        class FakeSessionError(Exception):
            pass

        class FakeTsdbSymbol:
            def __init__(self, symbol):
                self.symbol = symbol

            def get_data(self, start, end):
                raise FakeSessionError("GsSession is not initialised")

        class _SessionMeta(type):
            @property
            def current(cls):
                raise FakeSessionError("not init")

        class FakeGsSession(metaclass=_SessionMeta):
            @staticmethod
            def use():
                raise FakeSessionError("auth unavailable")

        monkeypatch.setattr(tsdb_module, "_HAS_GS_QUANT", True)
        monkeypatch.setattr(tsdb_module, "TSDBSymbol", FakeTsdbSymbol, raising=False)
        monkeypatch.setattr(tsdb_module, "GsSession", FakeGsSession, raising=False)
        monkeypatch.setattr(tsdb_module, "_GS_SESSION_ERRORS", (FakeSessionError,))

        with pytest.raises(ConnectionError, match="TSDB unavailable|could not initialize"):
            _get_tsdb_data("eqpad_AAPL.OQ@close", "2024-01-02", "2024-01-05")


# ---------------------------------------------------------------------------
# Tests: fetch_treasury_yields
# ---------------------------------------------------------------------------


class TestFetchTreasuryYields:
    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_returns_dataframe_with_tenor_columns(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=4.5)
        df = fetch_treasury_yields(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(df, pd.DataFrame)
        for tenor in ["2y", "5y", "10y", "30y"]:
            assert tenor in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_custom_tenors(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=4.5)
        df = fetch_treasury_yields(date(2024, 1, 2), date(2024, 3, 1), tenors=["2y", "10y"])
        assert "2y" in df.columns
        assert "10y" in df.columns
        assert "5y" not in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_index_is_datetime(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=4.5)
        df = fetch_treasury_yields(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(df.index, pd.DatetimeIndex)


# ---------------------------------------------------------------------------
# Tests: fetch_fx_rates
# ---------------------------------------------------------------------------


class TestFetchFxRates:
    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_returns_dataframe_with_pair_columns(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=150.0)
        df = fetch_fx_rates(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(df, pd.DataFrame)
        assert "USD/JPY" in df.columns
        assert "EUR/USD" in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_custom_pairs(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=150.0)
        df = fetch_fx_rates(date(2024, 1, 2), date(2024, 3, 1), pairs=["USD/JPY"])
        assert "USD/JPY" in df.columns
        assert "EUR/USD" not in df.columns


# ---------------------------------------------------------------------------
# Tests: fetch_commodity_prices
# ---------------------------------------------------------------------------


class TestFetchCommodityPrices:
    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_returns_dataframe_with_symbol_columns(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=70.0)
        df = fetch_commodity_prices(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(df, pd.DataFrame)
        assert "CL" in df.columns
        assert "GC" in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_custom_symbols(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=70.0)
        df = fetch_commodity_prices(date(2024, 1, 2), date(2024, 3, 1), symbols=["CL"])
        assert "CL" in df.columns
        assert "GC" not in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_index_is_datetime(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=70.0)
        df = fetch_commodity_prices(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(df.index, pd.DatetimeIndex)


# ---------------------------------------------------------------------------
# Tests: fetch_vix
# ---------------------------------------------------------------------------


class TestFetchVix:
    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_returns_series(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=18.0)
        result = fetch_vix(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(result, pd.Series)
        assert result.name == "vix"

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_index_is_datetime(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=18.0)
        result = fetch_vix(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_calls_correct_symbol(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=18.0)
        fetch_vix(date(2024, 1, 2), date(2024, 3, 1))
        mock_get.assert_called_once_with("eqpad_.VIX@close", "2024-01-02", "2024-03-01")


# ---------------------------------------------------------------------------
# Tests: fetch_vix_futures
# ---------------------------------------------------------------------------


class TestFetchVixFutures:
    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_returns_dataframe(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-06-01", "2024-08-01", value=20.0)
        df = fetch_vix_futures(date(2024, 6, 1), date(2024, 8, 1))
        assert isinstance(df, pd.DataFrame)

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_has_vx_columns(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-06-01", "2024-08-01", value=20.0)
        df = fetch_vix_futures(date(2024, 6, 1), date(2024, 8, 1), n_contracts=3)
        assert "VX1" in df.columns
        assert "VX2" in df.columns
        assert "VX3" in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_index_is_datetime(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-06-01", "2024-08-01", value=20.0)
        df = fetch_vix_futures(date(2024, 6, 1), date(2024, 8, 1))
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "date"

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_custom_n_contracts(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-06-01", "2024-08-01", value=20.0)
        df = fetch_vix_futures(date(2024, 6, 1), date(2024, 8, 1), n_contracts=2)
        assert len(df.columns) == 2
        assert "VX1" in df.columns
        assert "VX2" in df.columns


# ---------------------------------------------------------------------------
# Tests: fetch_spx_index
# ---------------------------------------------------------------------------


class TestFetchSpxIndex:
    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_returns_dataframe(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=4800.0)
        df = fetch_spx_index(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(df, pd.DataFrame)

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_default_fields(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=4800.0)
        df = fetch_spx_index(date(2024, 1, 2), date(2024, 3, 1))
        for col in ["open", "high", "low", "close"]:
            assert col in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_custom_fields(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=4800.0)
        df = fetch_spx_index(date(2024, 1, 2), date(2024, 3, 1), fields=["close"])
        assert "close" in df.columns
        assert "open" not in df.columns

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_index_is_datetime(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=4800.0)
        df = fetch_spx_index(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "date"

    @patch("volforecast.data.tsdb._get_tsdb_data")
    def test_calls_spx_symbols(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01", value=4800.0)
        fetch_spx_index(date(2024, 1, 2), date(2024, 3, 1), fields=["close"])
        mock_get.assert_called_once_with("eqpad_.SPX@close", "2024-01-02", "2024-03-01")
