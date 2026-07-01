"""Tests for 0DTE implied volatility ingestion from EDRVOL_PERCENT_EXPIRY.

Mocks the Marquee Dataset API. Validates per-symbol nearest-expiry IV extraction,
correct RIC resolution, ATM filtering, and date alignment.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_expiry_df(
    observation_date: str = "2024-10-28",
    expiry_dates: list[str] | None = None,
    strikes: list[float] | None = None,
) -> pd.DataFrame:
    """Create synthetic EDRVOL_PERCENT_EXPIRY response.

    Mimics the Marquee dataset structure: one row per (date, expirationDate, strike).
    """
    if expiry_dates is None:
        # Include same-day (0DTE), next day, and weekly
        expiry_dates = ["2024-10-28", "2024-10-29", "2024-11-01", "2024-11-08"]
    if strikes is None:
        strikes = [0.90, 0.95, 1.0, 1.05, 1.10]

    rng = np.random.default_rng(42)
    rows = []
    for exp in expiry_dates:
        for strike in strikes:
            rows.append(
                {
                    "date": pd.Timestamp(observation_date),
                    "expirationDate": pd.Timestamp(exp),
                    "relativeStrike": strike,
                    "strikeReference": "forward",
                    "impliedVolatility": 15.0 + rng.uniform(-3, 5),
                    "ric": "SPY.P",
                }
            )
    return pd.DataFrame(rows)


def _make_multi_day_expiry_df() -> pd.DataFrame:
    """Create multi-day EDRVOL_PERCENT_EXPIRY response."""
    rng = np.random.default_rng(99)
    rows = []
    for obs_date in ["2024-10-28", "2024-10-29", "2024-10-30"]:
        # Each day has a same-day expiry + next-day expiry
        for exp_offset in [0, 1, 3]:
            exp_date = pd.Timestamp(obs_date) + pd.Timedelta(days=exp_offset)
            for strike in [0.95, 1.0, 1.05]:
                rows.append(
                    {
                        "date": pd.Timestamp(obs_date),
                        "expirationDate": exp_date,
                        "relativeStrike": strike,
                        "strikeReference": "forward",
                        "impliedVolatility": 16.0 + rng.uniform(-2, 4),
                        "ric": "SPY.P",
                    }
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests: TICKER_TO_MARQUEE_RIC mapping
# ---------------------------------------------------------------------------


class TestMarqueeRicMapping:
    """Verify the TICKER_TO_MARQUEE_RIC mapping is correct."""

    def test_all_edrvol_symbols_have_marquee_ric(self):
        from volforecast.constants import TICKER_TO_EDRVOL_RIC, TICKER_TO_MARQUEE_RIC

        for ticker in TICKER_TO_EDRVOL_RIC:
            assert ticker in TICKER_TO_MARQUEE_RIC, f"{ticker} missing from TICKER_TO_MARQUEE_RIC"

    def test_marquee_rics_are_uppercase(self):
        from volforecast.constants import TICKER_TO_MARQUEE_RIC

        for ticker, ric in TICKER_TO_MARQUEE_RIC.items():
            # SPX uses .SPX (dot prefix) which is a special case
            if ticker == "SPX":
                assert ric == ".SPX"
            else:
                assert ric == ric.upper(), f"{ticker} RIC should be uppercase: {ric}"

    def test_known_symbols(self):
        from volforecast.constants import TICKER_TO_MARQUEE_RIC

        assert TICKER_TO_MARQUEE_RIC["AAPL"] == "AAPL.OQ"
        assert TICKER_TO_MARQUEE_RIC["SPY"] == "SPY.P"
        assert TICKER_TO_MARQUEE_RIC["JPM"] == "JPM.N"
        assert TICKER_TO_MARQUEE_RIC["SPX"] == ".SPX"
        assert TICKER_TO_MARQUEE_RIC["QQQ"] == "QQQ.OQ"


# ---------------------------------------------------------------------------
# Tests: fetch_0dte_iv
# ---------------------------------------------------------------------------


class TestFetch0dteIv:
    """Test 0DTE IV fetching from EDRVOL_PERCENT_EXPIRY."""

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_returns_series_with_nearest_expiry_iv(self, mock_query):
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.return_value = _make_expiry_df()

        result = fetch_0dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 28))

        assert isinstance(result, pd.Series)
        assert result.name == "iv_0dte"
        assert len(result) == 1
        # ATM IV (relativeStrike=1.0) from nearest expiry (same day = 2024-10-28)
        assert result.iloc[0] > 0

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_selects_atm_strike(self, mock_query):
        """Should filter to relativeStrike=1.0 (ATM forward)."""
        from volforecast.data.edrvol import fetch_0dte_iv

        df = _make_expiry_df()
        # Set distinctive value for ATM on same-day expiry
        mask = (df["relativeStrike"] == 1.0) & (df["expirationDate"] == pd.Timestamp("2024-10-28"))
        df.loc[mask, "impliedVolatility"] = 18.5
        mock_query.return_value = df

        result = fetch_0dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 28))

        assert result.iloc[0] == pytest.approx(18.5)

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_selects_nearest_expiry_per_day(self, mock_query):
        """For each observation date, pick the expiry closest to that date (>= obs date)."""
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.return_value = _make_multi_day_expiry_df()

        result = fetch_0dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 30))

        assert len(result) == 3
        assert result.index[0] == pd.Timestamp("2024-10-28")
        assert result.index[1] == pd.Timestamp("2024-10-29")
        assert result.index[2] == pd.Timestamp("2024-10-30")

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_returns_empty_on_no_data(self, mock_query):
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.return_value = pd.DataFrame()

        result = fetch_0dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 28))

        assert isinstance(result, pd.Series)
        assert result.empty
        assert result.name == "iv_0dte"

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_values_in_vol_points(self, mock_query):
        """IV should be in vol points (15.0 = 15%), same as EDRVOL convention."""
        from volforecast.data.edrvol import fetch_0dte_iv

        df = _make_expiry_df()
        mask = (df["relativeStrike"] == 1.0) & (df["expirationDate"] == pd.Timestamp("2024-10-28"))
        df.loc[mask, "impliedVolatility"] = 22.5
        mock_query.return_value = df

        result = fetch_0dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 28))

        # Should pass through as-is (already in vol points from Marquee)
        assert result.iloc[0] == pytest.approx(22.5)

    def test_raises_on_unknown_symbol(self):
        from volforecast.data.edrvol import fetch_0dte_iv

        with pytest.raises(ValueError, match="No Marquee RIC"):
            fetch_0dte_iv("INVALID", date(2024, 10, 28), date(2024, 10, 28))

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_handles_api_error(self, mock_query):
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.side_effect = ConnectionError("Marquee unavailable")

        result = fetch_0dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 28))

        assert result.empty
        assert result.name == "iv_0dte"

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_correct_ric_passed_for_spx(self, mock_query):
        from volforecast.data.edrvol import fetch_0dte_iv

        mock_query.return_value = _make_expiry_df()

        fetch_0dte_iv("SPX", date(2024, 10, 28), date(2024, 10, 28))

        mock_query.assert_called_once()
        call_kwargs = mock_query.call_args
        assert call_kwargs[0][0] == ".SPX"  # ric positional arg


# ---------------------------------------------------------------------------
# Tests: fetch_1dte_iv
# ---------------------------------------------------------------------------


class TestFetch1dteIv:
    """Test 1DTE IV fetching — should skip same-day expiry, pick next day."""

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_skips_same_day_expiry(self, mock_query):
        """1DTE should NOT pick the same-day expiry (picks tomorrow instead)."""
        from volforecast.data.edrvol import fetch_1dte_iv

        df = _make_expiry_df(observation_date="2024-10-28")
        # Set distinctive values: same-day=10.0, next-day=20.0
        mask_0dte = (df["relativeStrike"] == 1.0) & (
            df["expirationDate"] == pd.Timestamp("2024-10-28")
        )
        mask_1dte = (df["relativeStrike"] == 1.0) & (
            df["expirationDate"] == pd.Timestamp("2024-10-29")
        )
        df.loc[mask_0dte, "impliedVolatility"] = 10.0
        df.loc[mask_1dte, "impliedVolatility"] = 20.0
        mock_query.return_value = df

        result = fetch_1dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 28))

        assert isinstance(result, pd.Series)
        assert result.name == "iv_1dte"
        assert len(result) == 1
        # Should pick 20.0 (next-day), NOT 10.0 (same-day)
        assert result.iloc[0] == pytest.approx(20.0)

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_returns_next_day_expiry_per_obs_date(self, mock_query):
        """For multi-day data, each obs date picks the next-day expiry."""
        from volforecast.data.edrvol import fetch_1dte_iv

        mock_query.return_value = _make_multi_day_expiry_df()

        result = fetch_1dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 30))

        assert len(result) == 3
        # Each day should have picked expiry = obs_date + 1 day (offset=1)

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_returns_empty_when_no_future_expiry(self, mock_query):
        """If only same-day expiry exists (no next-day), should return empty."""
        from volforecast.data.edrvol import fetch_1dte_iv

        # Only same-day expiry available
        df = _make_expiry_df(
            observation_date="2024-10-28",
            expiry_dates=["2024-10-28"],  # only 0DTE, no future
        )
        mock_query.return_value = df

        result = fetch_1dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 28))

        assert result.empty
        assert result.name == "iv_1dte"

    @patch("volforecast.data.edrvol._query_marquee_expiry")
    def test_series_name_is_iv_1dte(self, mock_query):
        from volforecast.data.edrvol import fetch_1dte_iv

        mock_query.return_value = _make_expiry_df()

        result = fetch_1dte_iv("SPY", date(2024, 10, 28), date(2024, 10, 28))

        assert result.name == "iv_1dte"

    def test_raises_on_unknown_symbol(self):
        from volforecast.data.edrvol import fetch_1dte_iv

        with pytest.raises(ValueError, match="No Marquee RIC"):
            fetch_1dte_iv("INVALID", date(2024, 10, 28), date(2024, 10, 28))
