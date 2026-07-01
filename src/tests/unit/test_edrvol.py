"""Tests for per-symbol EDRVOL implied volatility ingestion.

Mocks all external TSDB calls. Validates RIC mapping, fetch/save/load
roundtrips, VVIX fetch, and IV dispersion computation.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest  # noqa: I001

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_iv_series(
    start: str = "2024-01-02",
    end: str = "2024-03-29",
    base_val: float = 0.20,
) -> pd.Series:
    """Create synthetic TSDB IV series (decimal, e.g. 0.20 = 20%)."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    values = base_val + rng.uniform(-0.03, 0.03, len(idx))
    return pd.Series(values, index=idx, name="value")


def _make_vvix_series(
    start: str = "2024-01-02",
    end: str = "2024-03-29",
) -> pd.Series:
    """Create synthetic VVIX series (index points, e.g. 95.0)."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(123)
    values = 90.0 + rng.uniform(-10, 20, len(idx))
    return pd.Series(values, index=idx, name="close")


# ---------------------------------------------------------------------------
# Tests: TICKER_TO_EDRVOL_RIC mapping
# ---------------------------------------------------------------------------


class TestEdrvolMapping:
    """Verify the TICKER_TO_EDRVOL_RIC mapping is correct."""

    def test_all_40_symbols_present(self):
        from volforecast.constants import TICKER_TO_EDRVOL_RIC

        # 39 equities/ETFs/indexes + 1 futures alias (ES → spx)
        assert len(TICKER_TO_EDRVOL_RIC) == 40

    def test_rics_are_lowercase(self):
        from volforecast.constants import TICKER_TO_EDRVOL_RIC

        for ticker, ric in TICKER_TO_EDRVOL_RIC.items():
            assert ric == ric.lower(), f"{ticker} RIC should be lowercase: {ric}"

    def test_known_symbols_have_correct_rics(self):
        from volforecast.constants import TICKER_TO_EDRVOL_RIC

        assert TICKER_TO_EDRVOL_RIC["AAPL"] == "aapl.oq"
        assert TICKER_TO_EDRVOL_RIC["SPY"] == "spy.p"
        assert TICKER_TO_EDRVOL_RIC["JPM"] == "jpm.n"
        assert TICKER_TO_EDRVOL_RIC["SPX"] == "spx"
        assert TICKER_TO_EDRVOL_RIC["QQQ"] == "qqq.oq"
        # New symbols added for full universe coverage
        assert TICKER_TO_EDRVOL_RIC["ABBV"] == "abbv.n"
        assert TICKER_TO_EDRVOL_RIC["COST"] == "cost.oq"
        assert TICKER_TO_EDRVOL_RIC["LLY"] == "lly.n"
        assert TICKER_TO_EDRVOL_RIC["WMT"] == "wmt.n"
        assert TICKER_TO_EDRVOL_RIC["UNP"] == "unp.n"

    def test_es_futures_mapped_to_spx_surface(self):
        """ES (E-mini S&P 500) uses the SPX vol surface as its IV proxy."""
        from volforecast.constants import TICKER_TO_EDRVOL_RIC

        assert TICKER_TO_EDRVOL_RIC.get("ES") == "spx"


# ---------------------------------------------------------------------------
# Tests: fetch_edrvol
# ---------------------------------------------------------------------------


class TestFetchEdrvol:
    """Test per-symbol IV fetching."""

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_returns_dataframe_with_expected_columns(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_edrvol

        mock_tsdb.return_value = _make_iv_series()

        result = fetch_edrvol("SPY", date(2024, 1, 2), date(2024, 3, 29))

        assert isinstance(result, pd.DataFrame)
        assert "iv_1w_atm" in result.columns
        assert "iv_1m_atm" in result.columns
        assert "iv_3m_atm" in result.columns
        assert "iv_1m_25dp" in result.columns
        assert "iv_1m_25dc" in result.columns

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_1w_tenor_queried_by_default(self, mock_tsdb):
        """1w ATM IV should be fetched by default for horizon-matched forecasting."""
        from volforecast.data.edrvol import fetch_edrvol

        mock_tsdb.return_value = _make_iv_series()

        fetch_edrvol("SPY", date(2024, 1, 2), date(2024, 3, 29))

        calls = [c.args[0] for c in mock_tsdb.call_args_list]
        assert "edrvol_spy.p@1watms" in calls

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_values_in_vol_points(self, mock_tsdb):
        """IV should be in vol points (e.g. 20.0 = 20%), passed through as-is."""
        from volforecast.data.edrvol import fetch_edrvol

        # TSDB edrvol_ returns vol points directly: 20.0 = 20%
        mock_tsdb.return_value = pd.Series(
            [20.0, 21.0, 19.0],
            index=pd.bdate_range("2024-01-02", periods=3),
        )

        result = fetch_edrvol("SPY", date(2024, 1, 2), date(2024, 1, 4))

        # Should pass through as-is (no multiplication)
        assert result["iv_1m_atm"].iloc[0] == pytest.approx(20.0, abs=0.01)

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_correct_tsdb_symbols_queried(self, mock_tsdb):
        """Verify correct edrvol_ TSDB symbol strings are constructed."""
        from volforecast.data.edrvol import fetch_edrvol

        mock_tsdb.return_value = _make_iv_series()

        fetch_edrvol("AAPL", date(2024, 1, 2), date(2024, 3, 29))

        # Should query edrvol_aapl.oq@1watms, @1matms, @3matms, @1m25dp, @1m25dc
        calls = [c.args[0] for c in mock_tsdb.call_args_list]
        assert "edrvol_aapl.oq@1watms" in calls
        assert "edrvol_aapl.oq@1matms" in calls
        assert "edrvol_aapl.oq@3matms" in calls
        assert "edrvol_aapl.oq@1m25dp" in calls
        assert "edrvol_aapl.oq@1m25dc" in calls

    def test_raises_on_unknown_symbol(self):
        from volforecast.data.edrvol import fetch_edrvol

        with pytest.raises(ValueError, match="No EDRVOL RIC mapping"):
            fetch_edrvol("INVALID", date(2024, 1, 2), date(2024, 3, 29))

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_handles_partial_field_failure(self, mock_tsdb):
        """If one field fails, others should still be returned."""
        from volforecast.data.edrvol import fetch_edrvol

        def _side_effect(symbol, start, end):
            if "1m25dp" in symbol:
                raise ConnectionError("timeout")
            return _make_iv_series()

        mock_tsdb.side_effect = _side_effect

        result = fetch_edrvol("SPY", date(2024, 1, 2), date(2024, 3, 29))

        assert "iv_1m_atm" in result.columns
        assert "iv_3m_atm" in result.columns
        # 25dp failed but the rest returned
        assert not result.empty

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_returns_empty_on_total_failure(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_edrvol

        mock_tsdb.side_effect = ConnectionError("no network")

        result = fetch_edrvol("SPY", date(2024, 1, 2), date(2024, 3, 29))

        assert result.empty


# ---------------------------------------------------------------------------
# Tests: fetch_vvix
# ---------------------------------------------------------------------------


class TestFetchVvix:
    """Test VVIX index fetching."""

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_returns_series_named_vvix(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_vvix

        mock_tsdb.return_value = _make_vvix_series()

        result = fetch_vvix(date(2024, 1, 2), date(2024, 3, 29))

        assert isinstance(result, pd.Series)
        assert result.name == "vvix"

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_queries_correct_symbol(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_vvix

        mock_tsdb.return_value = _make_vvix_series()

        fetch_vvix(date(2024, 1, 2), date(2024, 3, 29))

        mock_tsdb.assert_called_once_with("eqsp_s_.vvix@close", "2024-01-02", "2024-03-29")

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_values_in_index_points(self, mock_tsdb):
        """VVIX should be in index points (e.g. 95.0), not divided by 100."""
        from volforecast.data.edrvol import fetch_vvix

        mock_tsdb.return_value = pd.Series(
            [95.0, 100.0, 88.0],
            index=pd.bdate_range("2024-01-02", periods=3),
        )

        result = fetch_vvix(date(2024, 1, 2), date(2024, 1, 4))

        assert result.iloc[0] == pytest.approx(95.0)


# ---------------------------------------------------------------------------
# Tests: fetch_vix_index
# ---------------------------------------------------------------------------


class TestFetchVixIndex:
    """Test VIX index fetching."""

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_returns_series_named_vix(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_vix_index

        mock_tsdb.return_value = pd.Series(
            [20.0, 21.5, 19.0],
            index=pd.bdate_range("2024-01-02", periods=3),
        )

        result = fetch_vix_index(date(2024, 1, 2), date(2024, 3, 29))

        assert isinstance(result, pd.Series)
        assert result.name == "vix"

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_queries_correct_symbol(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_vix_index

        mock_tsdb.return_value = pd.Series([20.0], index=pd.bdate_range("2024-01-02", periods=1))

        fetch_vix_index(date(2024, 1, 2), date(2024, 3, 29))

        mock_tsdb.assert_called_once_with("eqpad_.VIX@close", "2024-01-02", "2024-03-29")


# ---------------------------------------------------------------------------
# Tests: fetch_ovx
# ---------------------------------------------------------------------------


class TestFetchOvx:
    """Test OVX index fetching."""

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_returns_series_named_ovx(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_ovx

        mock_tsdb.return_value = pd.Series(
            [30.0, 32.5, 28.0],
            index=pd.bdate_range("2024-01-02", periods=3),
        )

        result = fetch_ovx(date(2024, 1, 2), date(2024, 3, 29))

        assert isinstance(result, pd.Series)
        assert result.name == "ovx"

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_queries_correct_symbol(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_ovx

        mock_tsdb.return_value = pd.Series([30.0], index=pd.bdate_range("2024-01-02", periods=1))

        fetch_ovx(date(2024, 1, 2), date(2024, 3, 29))

        mock_tsdb.assert_called_once_with("edrvol_uso.p@1matms", "2024-01-02", "2024-03-29")


# ---------------------------------------------------------------------------
# Tests: fetch_treasury_yields
# ---------------------------------------------------------------------------


class TestFetchTreasuryYields:
    """Test treasury yield fetching."""

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_returns_dataframe_with_tenor_columns(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_treasury_yields

        # CBOE yield indices return yield*10 (e.g., 45.0 = 4.5%)
        mock_tsdb.return_value = pd.Series(
            [45.0, 46.0, 44.0],
            index=pd.bdate_range("2024-01-02", periods=3),
        )

        result = fetch_treasury_yields(date(2024, 1, 2), date(2024, 3, 29))

        assert isinstance(result, pd.DataFrame)
        assert "5y" in result.columns
        assert "10y" in result.columns
        assert "30y" in result.columns
        # 2y not available (no working TSDB symbol)
        assert "2y" not in result.columns

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_divides_by_10(self, mock_tsdb):
        """CBOE yield indices store yield*10; should divide by 10."""
        from volforecast.data.edrvol import fetch_treasury_yields

        mock_tsdb.return_value = pd.Series([45.0], index=pd.bdate_range("2024-01-02", periods=1))

        result = fetch_treasury_yields(date(2024, 1, 2), date(2024, 3, 29), tenors=["10y"])

        # 45.0 / 10 = 4.5%
        assert result["10y"].iloc[0] == pytest.approx(4.5)

    @patch("volforecast.data.edrvol._get_tsdb_data")
    def test_queries_eqsp_symbol(self, mock_tsdb):
        from volforecast.data.edrvol import fetch_treasury_yields

        mock_tsdb.return_value = pd.Series([45.0], index=pd.bdate_range("2024-01-02", periods=1))

        fetch_treasury_yields(date(2024, 1, 2), date(2024, 3, 29), tenors=["10y"])

        mock_tsdb.assert_called_once_with("eqsp_s_.tnx", "2024-01-02", "2024-03-29")


# ---------------------------------------------------------------------------
# Tests: save/load roundtrip
# ---------------------------------------------------------------------------


class TestCacheRoundtrip:
    """Test save_iv_cache -> load_iv_cache roundtrip."""

    def test_save_and_load_dataframe(self, tmp_path):
        with patch("volforecast.data.edrvol.iv_cache_dir", return_value=tmp_path):
            from volforecast.data.edrvol import load_iv_cache, save_iv_cache

            df = pd.DataFrame(
                {"iv_1m_atm": [20.0, 21.0, 19.5], "iv_3m_atm": [22.0, 23.0, 21.5]},
                index=pd.bdate_range("2024-01-02", periods=3),
            )
            df.index.name = "date"

            save_iv_cache("SPY", df)
            loaded = load_iv_cache("SPY")

            assert loaded is not None
            assert len(loaded) == 3
            pd.testing.assert_frame_equal(loaded, df, check_freq=False)

    def test_save_and_load_series(self, tmp_path):
        with patch("volforecast.data.edrvol.iv_cache_dir", return_value=tmp_path):
            from volforecast.data.edrvol import load_iv_cache, save_iv_cache

            s = pd.Series(
                [95.0, 100.0, 88.0],
                index=pd.bdate_range("2024-01-02", periods=3),
                name="vvix",
            )

            save_iv_cache("_VVIX", s)
            loaded = load_iv_cache("_VVIX")

            assert loaded is not None
            assert len(loaded) == 3

    def test_load_returns_none_when_missing(self, tmp_path):
        with patch("volforecast.data.edrvol.iv_cache_dir", return_value=tmp_path):
            from volforecast.data.edrvol import load_iv_cache

            result = load_iv_cache("NONEXISTENT")
            assert result is None


class TestExecKvarCache:
    """Test loading the execution-Kvar cache."""

    def test_save_exec_kvar_roundtrip_preserves_trade_dates(self, tmp_path):
        with patch("volforecast.data.edrvol.processed_dir", return_value=tmp_path):
            from volforecast.data.edrvol import load_exec_kvar_cache, save_exec_kvar_cache

            series = pd.Series(
                [12.0, 13.5, 14.0],
                index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
                name="kvar_vol_pct",
            )
            series.index.name = "date"

            path = save_exec_kvar_cache(series)
            raw = pd.read_parquet(path)
            loaded = load_exec_kvar_cache()

            assert path.name == "gsvivs_exec_kvar.parquet"
            assert "trade_date" in raw.columns
            assert raw.index.name is None
            assert list(pd.to_datetime(raw["trade_date"])) == list(series.index)
            assert loaded is not None
            pd.testing.assert_series_equal(loaded, series, check_freq=False)

    def test_load_exec_kvar_uses_trade_date_column_and_deduplicates(self, tmp_path):
        with patch("volforecast.data.edrvol.processed_dir", return_value=tmp_path):
            from volforecast.data.edrvol import load_exec_kvar_cache

            df = pd.DataFrame(
                {
                    "trade_date": [
                        "2024-01-02 09:30:00",
                        "2024-01-02 15:45:00",
                        "2024-01-03 09:30:00",
                    ],
                    "kvar_vol_pct": [12.0, 13.5, 14.0],
                },
                index=pd.RangeIndex(start=0, stop=3),
            )
            df.to_parquet(tmp_path / "gsvivs_exec_kvar.parquet")

            result = load_exec_kvar_cache()

            assert result is not None
            assert list(result.index) == [
                pd.Timestamp("2024-01-02"),
                pd.Timestamp("2024-01-03"),
            ]
            assert result.name == "kvar_vol_pct"
            assert result.loc[pd.Timestamp("2024-01-02")] == pytest.approx(13.5)
            assert result.loc[pd.Timestamp("2024-01-03")] == pytest.approx(14.0)


# ---------------------------------------------------------------------------
# Tests: IV dispersion
# ---------------------------------------------------------------------------


class TestIvDispersion:
    """Test cross-sectional IV dispersion computation."""

    def test_computes_std_across_symbols(self, tmp_path):
        with patch("volforecast.data.edrvol.iv_cache_dir", return_value=tmp_path):
            from volforecast.data.edrvol import compute_iv_dispersion, save_iv_cache

            idx = pd.bdate_range("2024-01-02", periods=5)

            # Create two symbols with different IV levels
            df1 = pd.DataFrame({"iv_1m_atm": [20.0, 21.0, 22.0, 20.5, 21.5]}, index=idx)
            df2 = pd.DataFrame({"iv_1m_atm": [30.0, 31.0, 32.0, 30.5, 31.5]}, index=idx)

            save_iv_cache("AAPL", df1)
            save_iv_cache("MSFT", df2)

            result = compute_iv_dispersion(["AAPL", "MSFT"])

            assert isinstance(result, pd.Series)
            assert result.name == "iv_dispersion"
            assert len(result) == 5
            # std of [20, 30] with ddof=1 = 7.07
            assert result.iloc[0] == pytest.approx(7.07, abs=0.1)

    def test_returns_empty_with_single_symbol(self, tmp_path):
        with patch("volforecast.data.edrvol.iv_cache_dir", return_value=tmp_path):
            from volforecast.data.edrvol import compute_iv_dispersion, save_iv_cache

            idx = pd.bdate_range("2024-01-02", periods=3)
            df = pd.DataFrame({"iv_1m_atm": [20.0, 21.0, 22.0]}, index=idx)
            save_iv_cache("AAPL", df)

            result = compute_iv_dispersion(["AAPL"])

            assert result.empty


# ---------------------------------------------------------------------------
# Tests: CLI ingest-edrvol
# ---------------------------------------------------------------------------


class TestCliIngestEdrvol:
    """Test the CLI entry point dispatches correctly."""

    def test_parser_accepts_ingest_edrvol(self):
        from volforecast.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["ingest-edrvol", "--symbols", "SPY,AAPL"])
        assert args.command == "ingest-edrvol"
        assert args.symbols == "SPY,AAPL"

    def test_parser_defaults(self):
        from volforecast.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["ingest-edrvol"])
        assert args.command == "ingest-edrvol"
        assert args.start == "2013-01-02"
        assert args.end is None  # defaults to None (resolved to today at runtime)
        assert args.symbols is None
        assert args.force is False
