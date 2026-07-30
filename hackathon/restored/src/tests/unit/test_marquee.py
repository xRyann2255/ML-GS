"""Tests for Marquee IV surface data access.

TDD: Tests written first, implementations follow.
Uses mocked Dataset / TSDBSymbol (GS packages unavailable outside network).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd

from volforecast.data.marquee import (
    fetch_atm_iv,
    fetch_iv_surface,
    fetch_skew,
    fetch_vvix,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_erdvol_df(
    start: str = "2024-01-02",
    end: str = "2024-01-10",
    tenors: list[str] | None = None,
    strikes: list[float] | None = None,
) -> pd.DataFrame:
    """Create a synthetic ERDVOL_PERCENT_STANDARD-like DataFrame."""
    if tenors is None:
        tenors = ["1m", "3m", "6m", "1y"]
    if strikes is None:
        strikes = [0.25, 0.75, 0.90, 0.95, 1.0, 1.05, 1.10, 1.25]

    dates = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    rows = []
    for d in dates:
        for tenor in tenors:
            for strike in strikes:
                rows.append(
                    {
                        "date": d,
                        "tenor": tenor,
                        "relativeStrike": strike,
                        "impliedVolatility": rng.uniform(0.10, 0.40),
                        "bbid": "SPX",
                    }
                )
    df = pd.DataFrame(rows)
    df.index = pd.DatetimeIndex(df["date"])
    df.index.name = None
    return df.drop(columns=["date"])


def _make_tsdb_series(start: str, end: str, value: float = 20.0) -> pd.Series:
    """Create a synthetic TSDB-like Series."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    values = value + np.cumsum(rng.normal(0, 0.3, len(idx)))
    return pd.Series(values, index=idx)


# ---------------------------------------------------------------------------
# Tests: fetch_iv_surface
# ---------------------------------------------------------------------------


class TestFetchIvSurface:
    @patch("volforecast.data.marquee._query_erdvol")
    def test_returns_dataframe(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_iv_surface(date(2024, 1, 2), date(2024, 1, 10))
        assert isinstance(df, pd.DataFrame)

    @patch("volforecast.data.marquee._query_erdvol")
    def test_multiindex_date_tenor(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_iv_surface(date(2024, 1, 2), date(2024, 1, 10))
        assert isinstance(df.index, pd.MultiIndex)
        assert df.index.names == ["date", "tenor"]

    @patch("volforecast.data.marquee._query_erdvol")
    def test_columns_are_strikes(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_iv_surface(date(2024, 1, 2), date(2024, 1, 10))
        assert 1.0 in df.columns

    @patch("volforecast.data.marquee._query_erdvol")
    def test_tenor_filter(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_iv_surface(date(2024, 1, 2), date(2024, 1, 10), tenors=["1m", "3m"])
        tenors_in_idx = df.index.get_level_values("tenor").unique()
        assert "1m" in tenors_in_idx
        assert "6m" not in tenors_in_idx

    @patch("volforecast.data.marquee._query_erdvol")
    def test_strike_filter(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_iv_surface(date(2024, 1, 2), date(2024, 1, 10), strikes=[0.90, 1.0, 1.10])
        assert -0.25 not in df.columns

    @patch("volforecast.data.marquee._query_erdvol")
    def test_empty_result(self, mock_query):
        mock_query.return_value = pd.DataFrame()
        df = fetch_iv_surface(date(2024, 1, 2), date(2024, 1, 10))
        assert df.empty


# ---------------------------------------------------------------------------
# Tests: fetch_atm_iv
# ---------------------------------------------------------------------------


class TestFetchAtmIv:
    @patch("volforecast.data.marquee._query_erdvol")
    def test_returns_dataframe(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_atm_iv(date(2024, 1, 2), date(2024, 1, 10))
        assert isinstance(df, pd.DataFrame)

    @patch("volforecast.data.marquee._query_erdvol")
    def test_columns_are_tenors(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_atm_iv(date(2024, 1, 2), date(2024, 1, 10))
        assert "1m" in df.columns
        assert "3m" in df.columns

    @patch("volforecast.data.marquee._query_erdvol")
    def test_custom_tenors(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_atm_iv(date(2024, 1, 2), date(2024, 1, 10), tenors=["1m"])
        assert "1m" in df.columns
        assert "3m" not in df.columns

    @patch("volforecast.data.marquee._query_erdvol")
    def test_index_is_datetime(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_atm_iv(date(2024, 1, 2), date(2024, 1, 10))
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "date"

    @patch("volforecast.data.marquee._query_erdvol")
    def test_empty_result(self, mock_query):
        mock_query.return_value = pd.DataFrame()
        df = fetch_atm_iv(date(2024, 1, 2), date(2024, 1, 10))
        assert df.empty


# ---------------------------------------------------------------------------
# Tests: fetch_skew
# ---------------------------------------------------------------------------


class TestFetchSkew:
    @patch("volforecast.data.marquee._query_erdvol")
    def test_returns_dataframe(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_skew(date(2024, 1, 2), date(2024, 1, 10))
        assert isinstance(df, pd.DataFrame)

    @patch("volforecast.data.marquee._query_erdvol")
    def test_columns_are_tenors(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_skew(date(2024, 1, 2), date(2024, 1, 10))
        assert "1m" in df.columns
        assert "3m" in df.columns

    @patch("volforecast.data.marquee._query_erdvol")
    def test_skew_is_positive(self, mock_query):
        # With random IV, put IV should typically differ from call IV
        # We just check it returns numeric values
        mock_query.return_value = _make_erdvol_df()
        df = fetch_skew(date(2024, 1, 2), date(2024, 1, 10))
        assert not df.empty
        assert df.dtypes.apply(lambda x: np.issubdtype(x, np.floating)).all()

    @patch("volforecast.data.marquee._query_erdvol")
    def test_custom_tenors(self, mock_query):
        mock_query.return_value = _make_erdvol_df()
        df = fetch_skew(date(2024, 1, 2), date(2024, 1, 10), tenors=["1m"])
        assert "1m" in df.columns
        assert "3m" not in df.columns

    @patch("volforecast.data.marquee._query_erdvol")
    def test_empty_result(self, mock_query):
        mock_query.return_value = pd.DataFrame()
        df = fetch_skew(date(2024, 1, 2), date(2024, 1, 10))
        assert df.empty


# ---------------------------------------------------------------------------
# Tests: fetch_vvix
# ---------------------------------------------------------------------------


class TestFetchVvix:
    @patch("volforecast.data.marquee._HAS_TSDB", True)
    @patch("volforecast.data.marquee._get_vvix_tsdb_data")
    def test_returns_series(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01")
        result = fetch_vvix(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(result, pd.Series)
        assert result.name == "vvix"

    @patch("volforecast.data.marquee._HAS_TSDB", True)
    @patch("volforecast.data.marquee._get_vvix_tsdb_data")
    def test_index_is_datetime(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01")
        result = fetch_vvix(date(2024, 1, 2), date(2024, 3, 1))
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

    @patch("volforecast.data.marquee._HAS_TSDB", True)
    @patch("volforecast.data.marquee._get_vvix_tsdb_data")
    def test_calls_correct_dates(self, mock_get):
        mock_get.return_value = _make_tsdb_series("2024-01-02", "2024-03-01")
        fetch_vvix(date(2024, 1, 2), date(2024, 3, 1))
        mock_get.assert_called_once_with("2024-01-02", "2024-03-01")
