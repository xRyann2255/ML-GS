"""Tests for 0DTE IV fetch chunking and retry logic.

Verifies that _query_marquee_expiry uses chunked requests with retry
to avoid timeouts on large date ranges (e.g., SPX with daily expirations).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _make_expiry_df(start: str, end: str, ric: str = "spx") -> pd.DataFrame:
    """Create synthetic EDRVOL_PERCENT_EXPIRY response.

    Mimics Marquee Dataset.get_data() which returns a DatetimeIndex named 'date'.
    """
    dates = pd.bdate_range(start, end)
    rows = []
    for d in dates:
        rows.append(
            {
                "ric": ric,
                "expirationDate": d,  # 0DTE
                "relativeStrike": 1.0,
                "strikeReference": "forward",
                "impliedVolatility": 20.0,
            }
        )
    df = pd.DataFrame(rows, index=dates)
    df.index.name = "date"
    return df


class TestQueryMarqueeExpiryChunking:
    """Verify _query_marquee_expiry chunks large date ranges."""

    @patch("volforecast.data.edrvol._ensure_expiry_session")
    @patch("volforecast.data.edrvol._fetch_expiry_chunk")
    def test_short_range_single_request(self, mock_chunk, mock_session):
        """Date range <= 3 months should make a single request."""
        from volforecast.data.edrvol import _query_marquee_expiry

        mock_chunk.return_value = _make_expiry_df("2024-01-02", "2024-03-29")

        result = _query_marquee_expiry("spx", date(2024, 1, 2), date(2024, 3, 29))

        assert mock_chunk.call_count == 1
        assert not result.empty

    @patch("volforecast.data.edrvol._ensure_expiry_session")
    @patch("volforecast.data.edrvol._fetch_expiry_chunk")
    def test_long_range_chunked(self, mock_chunk, mock_session):
        """Date range > 3 months should be split into multiple chunks."""
        from volforecast.data.edrvol import _query_marquee_expiry

        # 12-month range should be split into ~4 chunks of 3 months
        mock_chunk.return_value = _make_expiry_df("2024-01-02", "2024-03-29")

        result = _query_marquee_expiry("spx", date(2024, 1, 1), date(2024, 12, 31))

        # Should have at least 4 chunk calls for 12 months
        assert mock_chunk.call_count >= 4

    @patch("volforecast.data.edrvol._ensure_expiry_session")
    @patch("volforecast.data.edrvol._fetch_expiry_chunk")
    def test_empty_chunks_handled(self, mock_chunk, mock_session):
        """If all chunks return empty, result should be empty DataFrame."""
        from volforecast.data.edrvol import _query_marquee_expiry

        mock_chunk.return_value = pd.DataFrame()

        result = _query_marquee_expiry("spx", date(2024, 1, 1), date(2024, 6, 30))

        assert result.empty

    @patch("volforecast.data.edrvol._ensure_expiry_session")
    @patch("volforecast.data.edrvol._fetch_expiry_chunk")
    def test_concat_preserves_date_index(self, mock_chunk, mock_session):
        """Concatenated chunks must preserve DatetimeIndex (not ignore_index)."""
        from volforecast.data.edrvol import _query_marquee_expiry

        mock_chunk.return_value = _make_expiry_df("2024-01-02", "2024-03-29")

        result = _query_marquee_expiry("spx", date(2024, 1, 1), date(2024, 12, 31))

        # Index must be DatetimeIndex named 'date' (as Marquee returns)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"


class TestFetchExpiryChunkRetry:
    """Verify per-chunk retry logic with backoff."""

    @patch("volforecast.data.edrvol._ensure_expiry_session")
    @patch("volforecast.data.edrvol.time.sleep")
    def test_retries_on_timeout(self, mock_sleep, mock_session):
        """Should retry up to 3 times on transient failure."""
        from volforecast.data.edrvol import _fetch_expiry_chunk

        mock_ds = MagicMock()
        # Fail twice, succeed on third
        mock_ds.get_data.side_effect = [
            ConnectionError("Read timed out"),
            ConnectionError("Read timed out"),
            _make_expiry_df("2024-01-02", "2024-03-29"),
        ]

        result = _fetch_expiry_chunk(mock_ds, "spx", date(2024, 1, 2), date(2024, 3, 29))

        assert mock_ds.get_data.call_count == 3
        assert not result.empty
        # Should have slept between retries
        assert mock_sleep.call_count == 2

    @patch("volforecast.data.edrvol._ensure_expiry_session")
    @patch("volforecast.data.edrvol.time.sleep")
    def test_returns_none_after_exhausted_retries(self, mock_sleep, mock_session):
        """Should return None after all retries fail."""
        from volforecast.data.edrvol import _fetch_expiry_chunk

        mock_ds = MagicMock()
        mock_ds.get_data.side_effect = ConnectionError("Read timed out")

        result = _fetch_expiry_chunk(mock_ds, "spx", date(2024, 1, 2), date(2024, 3, 29))

        assert result is None
        assert mock_ds.get_data.call_count == 3

    @patch("volforecast.data.edrvol._ensure_expiry_session")
    @patch("volforecast.data.edrvol.time.sleep")
    def test_no_retry_on_success(self, mock_sleep, mock_session):
        """Should not retry if first attempt succeeds."""
        from volforecast.data.edrvol import _fetch_expiry_chunk

        mock_ds = MagicMock()
        mock_ds.get_data.return_value = _make_expiry_df("2024-01-02", "2024-03-29")

        result = _fetch_expiry_chunk(mock_ds, "spx", date(2024, 1, 2), date(2024, 3, 29))

        assert mock_ds.get_data.call_count == 1
        assert mock_sleep.call_count == 0
        assert not result.empty


class TestFetch0dteIvIntegration:
    """Integration test: fetch_0dte_iv uses chunked query."""

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_long_range_returns_series(self, mock_query):
        """fetch_0dte_iv with 2-year range should return proper series."""
        from volforecast.data.edrvol import fetch_0dte_iv

        # Simulate multi-year fetch returning stitched data
        df = _make_expiry_df("2023-01-02", "2024-12-31")
        mock_query.return_value = df

        result = fetch_0dte_iv("SPX", date(2023, 1, 2), date(2024, 12, 31))

        assert isinstance(result, pd.Series)
        assert result.name == "iv_0dte"
        assert len(result) > 0


class TestFetchExpiryIvOutlierGuard:
    """Sanitizer: Marquee EDRVOL_PERCENT_EXPIRY occasionally returns
    near-zero impliedVolatility values (e.g. SPY 2017-09-13 returned
    1e-05). Such values are clearly broken — real ATM IV never goes
    below ~1% annualized. They must be filtered at ingest, not
    propagated into log_atm_iv_*_d features (where log(1e-5) ≈ -11.5
    destroys downstream linear baselines like har_iv_0dte).
    """

    # Minimum plausible impliedVolatility (in whatever units Marquee returns
    # for the symbol — decimal or percent). 0.005 is below ALL realistic
    # ATM IV values (0.5% annualized vol is not a real market state).
    MIN_PLAUSIBLE_IV = 0.005

    def _make_df_with_outlier(self, outlier_value: float) -> pd.DataFrame:
        """Build a 3-day fixture where the middle row has a corrupted IV."""
        rows = [
            {
                "ric": "spy",
                "expirationDate": pd.Timestamp("2024-01-02"),
                "relativeStrike": 1.0,
                "strikeReference": "forward",
                "impliedVolatility": 0.18,
            },
            {
                "ric": "spy",
                "expirationDate": pd.Timestamp("2024-01-03"),
                "relativeStrike": 1.0,
                "strikeReference": "forward",
                "impliedVolatility": outlier_value,
            },
            {
                "ric": "spy",
                "expirationDate": pd.Timestamp("2024-01-04"),
                "relativeStrike": 1.0,
                "strikeReference": "forward",
                "impliedVolatility": 0.17,
            },
        ]
        idx = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"], name="date")
        return pd.DataFrame(rows, index=idx)

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_near_zero_iv_replaced_with_nan(self, mock_query):
        """Corrupted value (1e-05) must be dropped, not returned as-is."""
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.return_value = self._make_df_with_outlier(1e-05)

        result = fetch_0dte_iv("SPY", date(2024, 1, 2), date(2024, 1, 4))

        # The corrupt row must NOT appear as a finite low value.
        # Either dropped from index, or NaN.
        bad_day = pd.Timestamp("2024-01-03")
        assert bad_day not in result.index or pd.isna(result.loc[bad_day]), (
            f"iv_0dte=1e-5 was not filtered: result[2024-01-03]={result.get(bad_day)}"
        )
        # Healthy values must still be present.
        assert result.loc[pd.Timestamp("2024-01-02")] == pytest.approx(0.18)
        assert result.loc[pd.Timestamp("2024-01-04")] == pytest.approx(0.17)

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_threshold_boundary_below_filtered(self, mock_query):
        """Value just below MIN_PLAUSIBLE_IV must be filtered."""
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.return_value = self._make_df_with_outlier(self.MIN_PLAUSIBLE_IV - 1e-6)
        result = fetch_0dte_iv("SPY", date(2024, 1, 2), date(2024, 1, 4))

        bad_day = pd.Timestamp("2024-01-03")
        assert bad_day not in result.index or pd.isna(result.loc[bad_day])

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_threshold_boundary_above_kept(self, mock_query):
        """Value just above MIN_PLAUSIBLE_IV must be preserved."""
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.return_value = self._make_df_with_outlier(self.MIN_PLAUSIBLE_IV + 1e-6)
        result = fetch_0dte_iv("SPY", date(2024, 1, 2), date(2024, 1, 4))

        kept_val = result.loc[pd.Timestamp("2024-01-03")]
        assert kept_val == pytest.approx(self.MIN_PLAUSIBLE_IV + 1e-6)

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_normal_range_preserved(self, mock_query):
        """All-healthy fixture must come through untouched."""
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.return_value = self._make_df_with_outlier(0.12)
        result = fetch_0dte_iv("SPY", date(2024, 1, 2), date(2024, 1, 4))

        assert len(result) == 3
        assert result.loc[pd.Timestamp("2024-01-03")] == pytest.approx(0.12)
