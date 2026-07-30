"""Tests for EDRVS_EXPIRY_INTRADAY variance swap strike ingestion.

Covers fetch_edrvs_0dte() — the fetcher that retrieves SPX prev-close
1-DTE variance swap fair vol from the Marquee EDRVS_EXPIRY_INTRADAY
dataset. The semantic: for each trade date T, return yesterday's close
(~16:00 ET) snapshot of the varswap expiring today. This avoids
lookahead for the 09:10 ET GSVIVS01 signal decision.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture
def _mock_gs_session():
    """Patch GsSession so tests don't need real auth."""
    with patch("volforecast.data.edrvol.GsSession", create=True) as mock_gs:
        mock_gs.use = MagicMock()
        mock_gs.current = MagicMock()
        yield mock_gs


def _intraday_row(
    obs_ts: str,
    expiry: str,
    fair_vol: float,
    fair_variance: float | None = None,
) -> dict:
    """Build a synthetic EDRVS_EXPIRY_INTRADAY row."""
    return {
        "expirationDate": pd.Timestamp(expiry),
        "fairVariance": fair_variance if fair_variance is not None else fair_vol**2,
        "fairVolatility": fair_vol,
        "bbid": "SPX",
        "_index": pd.Timestamp(obs_ts, tz="UTC"),
    }


def _intraday_df(rows: list[dict]) -> pd.DataFrame:
    """Build a DataFrame with the UTC DatetimeIndex layout returned by Marquee."""
    df = pd.DataFrame(rows)
    df.index = pd.DatetimeIndex(df.pop("_index"))
    return df


@pytest.fixture
def sample_intraday_response():
    """Multi-day EDRVS_EXPIRY_INTRADAY response: close-of-day snapshots
    of each session's next-business-day expiry."""
    rows = [
        # Mon 2024-06-03 close: snapshot for Tue 2024-06-04 expiry
        _intraday_row("2024-06-03 19:55:00", "2024-06-04", 13.42),
        _intraday_row("2024-06-03 20:00:00", "2024-06-04", 13.50),
        # Tue 2024-06-04 close: snapshot for Wed 2024-06-05 expiry
        _intraday_row("2024-06-04 19:55:00", "2024-06-05", 13.78),
        _intraday_row("2024-06-04 20:00:00", "2024-06-05", 13.80),
        # Wed 2024-06-05 close: snapshot for Thu 2024-06-06 expiry
        _intraday_row("2024-06-05 19:55:00", "2024-06-06", 14.05),
        _intraday_row("2024-06-05 20:00:00", "2024-06-06", 14.10),
    ]
    return _intraday_df(rows)


class TestFetchEdrvs0dte:
    """Tests for fetch_edrvs_0dte() — prev-close 1-DTE extraction."""

    def test_returns_series_with_fair_volatility_for_next_day_expiry(
        self, sample_intraday_response
    ):
        """Output is a pd.Series indexed by trade date (the day the signal fires)."""
        from volforecast.data.edrvol import fetch_edrvs_0dte

        with patch(
            "volforecast.data.edrvol._query_edrvs_intraday",
            return_value=sample_intraday_response,
        ):
            result = fetch_edrvs_0dte(date(2024, 6, 4), date(2024, 6, 6))

        assert isinstance(result, pd.Series)
        assert result.name == "iv_vs_0dte"
        assert len(result) > 0
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

    def test_values_in_annualized_vol_percent(self, sample_intraday_response):
        """Values are fairVolatility directly — already in vol % (e.g. 13.5)."""
        from volforecast.data.edrvol import fetch_edrvs_0dte

        with patch(
            "volforecast.data.edrvol._query_edrvs_intraday",
            return_value=sample_intraday_response,
        ):
            result = fetch_edrvs_0dte(date(2024, 6, 4), date(2024, 6, 6))

        # Sane vol range; fairVolatility is already a percentage point value.
        assert (result > 5).all(), "Values should be > 5 vol%"
        assert (result < 80).all(), "Values should be < 80 vol%"
        assert result.max() < 50, "Should be vol% (not variance)"

    def test_uses_latest_close_window_snapshot(self):
        """For each obs day, the LAST 19h+ UTC snapshot (closest to close) wins."""
        from volforecast.data.edrvol import fetch_edrvs_0dte

        # Three snapshots on Mon: early (18h, ignored), late-19h, late-20h.
        # Expect the 20:00 row to win for the next bday (Tue).
        rows = [
            _intraday_row("2024-06-03 18:00:00", "2024-06-04", 99.0),
            _intraday_row("2024-06-03 19:30:00", "2024-06-04", 13.10),
            _intraday_row("2024-06-03 20:00:00", "2024-06-04", 13.50),
        ]
        mock_response = _intraday_df(rows)

        with patch(
            "volforecast.data.edrvol._query_edrvs_intraday",
            return_value=mock_response,
        ):
            result = fetch_edrvs_0dte(date(2024, 6, 4), date(2024, 6, 4))

        assert len(result) == 1
        assert abs(result.iloc[0] - 13.50) < 0.01

    def test_falls_back_to_18h_when_no_19h_snapshot(self):
        """If no 19h+ snapshot exists for the matching expiry, falls back to 18h+."""
        from volforecast.data.edrvol import fetch_edrvs_0dte

        # Only an 18h snapshot (no 19h close-window data)
        rows = [
            _intraday_row("2024-06-03 18:15:00", "2024-06-04", 13.95),
        ]
        mock_response = _intraday_df(rows)

        with patch(
            "volforecast.data.edrvol._query_edrvs_intraday",
            return_value=mock_response,
        ):
            result = fetch_edrvs_0dte(date(2024, 6, 4), date(2024, 6, 4))

        assert len(result) == 1
        assert abs(result.iloc[0] - 13.95) < 0.01

    def test_chunks_long_date_ranges(self):
        """Long date ranges are chunked weekly to avoid Marquee timeouts."""
        from volforecast.data.edrvol import fetch_edrvs_0dte

        single_row = _intraday_df(
            [_intraday_row("2024-06-03 20:00:00", "2024-06-04", 13.5)]
        )

        # Patch the intraday chunk fetcher AND the session bootstrap so the
        # public function exercises the chunk loop without touching network.
        with (
            patch(
                "volforecast.data.edrvol._fetch_edrvs_intraday_chunk",
                return_value=single_row,
            ) as mock_chunk,
            patch("volforecast.data.edrvol._ensure_expiry_session"),
            patch("volforecast.data.edrvol.Dataset", create=True),
        ):
            fetch_edrvs_0dte(date(2024, 1, 1), date(2024, 6, 30))

        # 6 months / 7-day chunks = many calls
        assert mock_chunk.call_count >= 2

    def test_returns_empty_on_no_data(self):
        """Returns empty Series when dataset returns no data."""
        from volforecast.data.edrvol import fetch_edrvs_0dte

        with patch(
            "volforecast.data.edrvol._query_edrvs_intraday",
            return_value=pd.DataFrame(),
        ):
            result = fetch_edrvs_0dte(date(2024, 6, 3), date(2024, 6, 7))

        assert isinstance(result, pd.Series)
        assert result.name == "iv_vs_0dte"
        assert len(result) == 0

    def test_returns_empty_on_connection_error(self):
        """Returns empty Series when Marquee connection fails."""
        from volforecast.data.edrvol import fetch_edrvs_0dte

        with patch(
            "volforecast.data.edrvol._query_edrvs_intraday",
            side_effect=ConnectionError("Marquee unavailable"),
        ):
            result = fetch_edrvs_0dte(date(2024, 6, 3), date(2024, 6, 7))

        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_returns_empty_when_fair_volatility_missing(self):
        """Returns empty Series when response lacks the fairVolatility column."""
        from volforecast.data.edrvol import fetch_edrvs_0dte

        bad_df = pd.DataFrame(
            {"expirationDate": [pd.Timestamp("2024-06-04")], "bbid": ["SPX"]},
            index=pd.DatetimeIndex([pd.Timestamp("2024-06-03 20:00", tz="UTC")]),
        )
        with patch(
            "volforecast.data.edrvol._query_edrvs_intraday",
            return_value=bad_df,
        ):
            result = fetch_edrvs_0dte(date(2024, 6, 4), date(2024, 6, 4))

        assert isinstance(result, pd.Series)
        assert len(result) == 0


class TestEdrvsCachePersistence:
    """Tests for save/load of EDRVS 0DTE cache."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Cache saves to parquet and loads back identically."""
        from volforecast.data.edrvol import load_edrvs_cache, save_edrvs_cache

        dates = pd.bdate_range("2024-06-03", periods=5)
        data = pd.Series(
            [13.42, 13.57, 12.76, 11.64, 14.02],
            index=pd.DatetimeIndex(dates, name="date"),
            name="iv_vs_0dte",
        )

        with patch("volforecast.data.edrvol.iv_cache_dir", return_value=tmp_path):
            save_edrvs_cache(data)
            loaded = load_edrvs_cache()

        assert loaded is not None
        pd.testing.assert_series_equal(loaded, data, check_freq=False)

    def test_load_returns_none_when_no_cache(self, tmp_path):
        """Returns None when cache file doesn't exist."""
        from volforecast.data.edrvol import load_edrvs_cache

        with patch("volforecast.data.edrvol.iv_cache_dir", return_value=tmp_path):
            result = load_edrvs_cache()

        assert result is None
