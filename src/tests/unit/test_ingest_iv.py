"""Tests for unified vol ingest-iv CLI.

TDD: Tests written first. Mocks all external API calls (TSDB, Marquee).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_iv_series(
    start: str = "2024-01-02",
    end: str = "2024-01-31",
    base: float = 20.0,
) -> pd.Series:
    """Create a synthetic IV series (vol points)."""
    idx = pd.DatetimeIndex(pd.bdate_range(start, end), name="date")
    rng = np.random.default_rng(42)
    return pd.Series(base + rng.normal(0, 2, len(idx)), index=idx)


def _make_iv_dataframe(
    start: str = "2024-01-02",
    end: str = "2024-01-31",
) -> pd.DataFrame:
    """Create a synthetic per-symbol IV DataFrame (4 raw columns)."""
    idx = pd.DatetimeIndex(pd.bdate_range(start, end), name="date")
    rng = np.random.default_rng(42)
    n = len(idx)
    return pd.DataFrame(
        {
            "iv_1m_atm": 20.0 + rng.normal(0, 2, n),
            "iv_3m_atm": 22.0 + rng.normal(0, 1.5, n),
            "iv_1m_25dp": 24.0 + rng.normal(0, 2.5, n),
            "iv_1m_25dc": 18.0 + rng.normal(0, 2, n),
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# Tests: unified CLI
# ---------------------------------------------------------------------------


class TestIngestIVCLI:
    """Test the unified ingest-iv command."""

    @patch("volforecast.data.edrvol.fetch_edrvol")
    @patch("volforecast.data.edrvol.fetch_vvix")
    @patch("volforecast.data.edrvol.fetch_vix_index")
    @patch("volforecast.data.edrvol.fetch_ovx")
    @patch("volforecast.data.edrvol.fetch_treasury_yields")
    @patch("volforecast.data.edrvol.load_iv_cache", return_value=None)
    def test_per_symbol_output_has_derived_columns(
        self,
        mock_load,
        mock_tsy,
        mock_ovx,
        mock_vix,
        mock_vvix,
        mock_fetch,
        tmp_path,
    ):
        """Output must include term_slope and skew_1m derived columns."""
        from volforecast.cli.ingest_iv import run

        raw_df = _make_iv_dataframe()
        mock_fetch.return_value = raw_df
        mock_vvix.return_value = _make_iv_series(base=100)
        mock_vix.return_value = _make_iv_series(base=20)
        mock_ovx.return_value = _make_iv_series(base=30)
        mock_tsy.return_value = pd.DataFrame(
            {
                "yield_2y": np.full(len(raw_df), 4.5),
                "yield_5y": np.full(len(raw_df), 4.2),
                "yield_10y": np.full(len(raw_df), 4.0),
                "yield_30y": np.full(len(raw_df), 4.3),
            },
            index=raw_df.index,
        )

        with patch("volforecast.data.edrvol.save_iv_cache") as mock_save:
            run(
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 31),
                symbols=["SPY"],
                force=True,
                cache_dir=tmp_path,
            )

            # Check that saved DataFrame has derived columns
            save_calls = [c for c in mock_save.call_args_list if c.args[0] == "SPY"]
            assert len(save_calls) >= 1
            saved_df = save_calls[0].args[1]
            assert "term_slope" in saved_df.columns
            assert "skew_1m" in saved_df.columns

    def test_term_slope_formula(self):
        """term_slope = iv_3m_atm - iv_1m_atm."""
        from volforecast.cli.ingest_iv import _add_derived_columns

        df = _make_iv_dataframe()
        result = _add_derived_columns(df)
        expected = df["iv_3m_atm"] - df["iv_1m_atm"]
        pd.testing.assert_series_equal(result["term_slope"], expected, check_names=False)

    def test_skew_formula(self):
        """skew_1m = iv_1m_25dp - iv_1m_25dc."""
        from volforecast.cli.ingest_iv import _add_derived_columns

        df = _make_iv_dataframe()
        result = _add_derived_columns(df)
        expected = df["iv_1m_25dp"] - df["iv_1m_25dc"]
        pd.testing.assert_series_equal(result["skew_1m"], expected, check_names=False)

    @patch("volforecast.data.edrvol.fetch_edrvol")
    @patch("volforecast.data.edrvol.load_iv_cache")
    def test_skip_cached_unless_force(self, mock_load, mock_fetch):
        """Cached symbols are skipped when force=False."""
        from volforecast.cli.ingest_iv import run

        # Pretend cache covers the range
        cached_df = _make_iv_dataframe()
        mock_load.return_value = cached_df

        with patch("volforecast.cli.ingest_iv._cache_covers_range", return_value=True):
            run(
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 31),
                symbols=["SPY"],
                force=False,
            )

        mock_fetch.assert_not_called()

    @patch("volforecast.data.edrvol.fetch_edrvol")
    @patch("volforecast.data.edrvol.load_iv_cache", return_value=None)
    @patch("volforecast.data.edrvol.save_iv_cache")
    @patch("volforecast.data.edrvol.fetch_vvix")
    @patch("volforecast.data.edrvol.fetch_vix_index")
    @patch("volforecast.data.edrvol.fetch_ovx")
    @patch("volforecast.data.edrvol.fetch_treasury_yields")
    def test_skip_market_wide_flag(
        self,
        mock_tsy,
        mock_ovx,
        mock_vix,
        mock_vvix,
        mock_save,
        mock_load,
        mock_fetch,
    ):
        """--skip-market-wide prevents VVIX/VIX/OVX/Treasury fetch."""
        from volforecast.cli.ingest_iv import run

        mock_fetch.return_value = _make_iv_dataframe()

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            symbols=["SPY"],
            force=True,
            skip_market_wide=True,
        )

        mock_vvix.assert_not_called()
        mock_vix.assert_not_called()
        mock_ovx.assert_not_called()
        mock_tsy.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: _cache_covers_range freshness logic
# ---------------------------------------------------------------------------


class TestCacheCoversRange:
    """Test cache range logic with tolerance for TSDB publication lag."""

    def test_exact_coverage_returns_true(self):
        """Cache covering exact requested range -> True."""
        from volforecast.cli.ingest_iv import _cache_covers_range

        idx = pd.DatetimeIndex(pd.bdate_range("2024-01-02", "2024-06-28"), name="date")
        cached = pd.DataFrame(
            {"iv_1w_atm": np.ones(len(idx)), "iv_1m_atm": np.ones(len(idx))}, index=idx
        )

        assert _cache_covers_range(cached, date(2024, 1, 2), date(2024, 6, 28)) is True

    def test_cache_ending_1_day_before_end_returns_true(self):
        """Cache ending 1 calendar day before requested end -> True (within tolerance)."""
        from volforecast.cli.ingest_iv import _cache_covers_range

        # Cache ends June 27, request ends June 28 (1 day gap)
        idx = pd.DatetimeIndex(pd.bdate_range("2024-01-02", "2024-06-27"), name="date")
        cached = pd.DataFrame(
            {"iv_1w_atm": np.ones(len(idx)), "iv_1m_atm": np.ones(len(idx))}, index=idx
        )

        assert _cache_covers_range(cached, date(2024, 1, 2), date(2024, 6, 28)) is True

    def test_cache_ending_3_days_before_end_returns_true(self):
        """Cache ending 3 calendar days before requested end -> True (within tolerance)."""
        from volforecast.cli.ingest_iv import _cache_covers_range

        # Cache ends June 25, request ends June 28 (3 day gap)
        idx = pd.DatetimeIndex(pd.bdate_range("2024-01-02", "2024-06-25"), name="date")
        cached = pd.DataFrame(
            {"iv_1w_atm": np.ones(len(idx)), "iv_1m_atm": np.ones(len(idx))}, index=idx
        )

        assert _cache_covers_range(cached, date(2024, 1, 2), date(2024, 6, 28)) is True

    def test_cache_ending_4_days_before_end_returns_false(self):
        """Cache ending 4+ calendar days before requested end -> False (stale)."""
        from volforecast.cli.ingest_iv import _cache_covers_range

        # Cache ends June 24, request ends June 28 (4 day gap)
        idx = pd.DatetimeIndex(pd.bdate_range("2024-01-02", "2024-06-24"), name="date")
        cached = pd.DataFrame(
            {"iv_1w_atm": np.ones(len(idx)), "iv_1m_atm": np.ones(len(idx))}, index=idx
        )

        assert _cache_covers_range(cached, date(2024, 1, 2), date(2024, 6, 28)) is False

    def test_empty_cache_returns_false(self):
        """Empty or None cache -> False."""
        from volforecast.cli.ingest_iv import _cache_covers_range

        assert _cache_covers_range(None, date(2024, 1, 2), date(2024, 6, 28)) is False
        assert _cache_covers_range(pd.DataFrame(), date(2024, 1, 2), date(2024, 6, 28)) is False

    def test_cache_not_covering_start_returns_false(self):
        """Cache starting after requested start -> False."""
        from volforecast.cli.ingest_iv import _cache_covers_range

        idx = pd.DatetimeIndex(pd.bdate_range("2024-03-01", "2024-06-28"), name="date")
        cached = pd.DataFrame({"iv_1m_atm": np.ones(len(idx))}, index=idx)

        assert _cache_covers_range(cached, date(2024, 1, 2), date(2024, 6, 28)) is False

    def test_cache_missing_required_column_returns_false(self):
        """Cache missing iv_1w_atm should return False even if dates cover range."""
        from volforecast.cli.ingest_iv import _cache_covers_range

        idx = pd.DatetimeIndex(pd.bdate_range("2024-01-02", "2024-06-28"), name="date")
        # Cache has iv_1m_atm but NOT iv_1w_atm
        cached = pd.DataFrame({"iv_1m_atm": np.ones(len(idx))}, index=idx)

        assert _cache_covers_range(cached, date(2024, 1, 2), date(2024, 6, 28)) is False

    def test_cache_with_all_required_columns_returns_true(self):
        """Cache with all required columns and valid date range -> True."""
        from volforecast.cli.ingest_iv import _cache_covers_range

        idx = pd.DatetimeIndex(pd.bdate_range("2024-01-02", "2024-06-28"), name="date")
        n = len(idx)
        cached = pd.DataFrame(
            {
                "iv_1w_atm": np.ones(n),
                "iv_1m_atm": np.ones(n),
                "iv_3m_atm": np.ones(n),
                "iv_1m_25dp": np.ones(n),
                "iv_1m_25dc": np.ones(n),
                "term_slope": np.ones(n),
                "skew_1m": np.ones(n),
            },
            index=idx,
        )

        assert _cache_covers_range(cached, date(2024, 1, 2), date(2024, 6, 28)) is True


# ---------------------------------------------------------------------------
# Tests: CLI --end defaults to today
# ---------------------------------------------------------------------------


class TestCLIEndDefault:
    """Test that --end defaults to today's date dynamically."""

    def test_end_default_is_today(self):
        """ingest-iv parser should default --end to None (resolved to today at dispatch)."""
        from volforecast.__main__ import _build_parser

        parser = _build_parser()
        # Parse with no --end argument
        args = parser.parse_args(["ingest-iv"])
        # Parser stores None; dispatch resolves to today
        assert args.end is None

    def test_end_explicit_value_preserved(self):
        """Explicit --end value is preserved."""
        from volforecast.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["ingest-iv", "--end", "2025-06-15"])
        assert args.end == "2025-06-15"

    def test_today_str_returns_iso_date(self):
        """_today_str() returns today in YYYY-MM-DD format."""
        from datetime import date as _date

        from volforecast.__main__ import _today_str

        result = _today_str()
        assert result == _date.today().isoformat()
        # Must be parseable as a date
        assert _date.fromisoformat(result) == _date.today()


# ---------------------------------------------------------------------------
# Tests: incremental fetch (append missing tail)
# ---------------------------------------------------------------------------


class TestIncrementalFetch:
    """Test that stale cache triggers incremental fetch (only the gap)."""

    @patch("volforecast.data.edrvol.fetch_edrvol")
    @patch("volforecast.data.edrvol.load_iv_cache")
    @patch("volforecast.data.edrvol.save_iv_cache")
    @patch("volforecast.data.edrvol.fetch_vvix")
    @patch("volforecast.data.edrvol.fetch_vix_index")
    @patch("volforecast.data.edrvol.fetch_ovx")
    @patch("volforecast.data.edrvol.fetch_treasury_yields")
    def test_incremental_fetch_only_fetches_gap(
        self,
        mock_tsy,
        mock_ovx,
        mock_vix,
        mock_vvix,
        mock_save,
        mock_load,
        mock_fetch,
    ):
        """With stale cache, fetch_edrvol is called with start = day after cached end."""
        from volforecast.cli.ingest_iv import run

        # Cached data: 2024-01-02 to 2024-03-29
        cached = _make_iv_dataframe(start="2024-01-02", end="2024-03-29")
        cached = cached.copy()
        cached["term_slope"] = cached["iv_3m_atm"] - cached["iv_1m_atm"]
        cached["skew_1m"] = cached["iv_1m_25dp"] - cached["iv_1m_25dc"]
        mock_load.return_value = cached

        # New data that TSDB returns for the gap
        new_data = _make_iv_dataframe(start="2024-04-01", end="2024-06-28")
        mock_fetch.return_value = new_data

        # Market-wide: pretend all cached
        mock_vvix.return_value = _make_iv_series(start="2024-04-01", end="2024-06-28", base=100)
        mock_vix.return_value = _make_iv_series(start="2024-04-01", end="2024-06-28", base=20)
        mock_ovx.return_value = _make_iv_series(start="2024-04-01", end="2024-06-28", base=30)
        mock_tsy.return_value = pd.DataFrame(index=pd.DatetimeIndex([], name="date"))

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 6, 28),
            symbols=["SPY"],
            force=False,
            skip_market_wide=True,
        )

        # fetch_edrvol should be called with start = day AFTER cached end
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        fetch_start = (
            call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("start_date")
        )
        # The fetch should start from 2024-04-01 (day after 2024-03-29, next bday)
        # Accept any date after cached end but before requested end
        assert fetch_start > date(2024, 3, 29), (
            f"Expected fetch after cached end, got {fetch_start}"
        )
        assert fetch_start <= date(2024, 4, 2), f"Expected fetch near gap start, got {fetch_start}"

    @patch("volforecast.data.edrvol.fetch_edrvol")
    @patch("volforecast.data.edrvol.load_iv_cache")
    @patch("volforecast.data.edrvol.save_iv_cache")
    @patch("volforecast.data.edrvol.fetch_vvix")
    @patch("volforecast.data.edrvol.fetch_vix_index")
    @patch("volforecast.data.edrvol.fetch_ovx")
    @patch("volforecast.data.edrvol.fetch_treasury_yields")
    def test_incremental_fetch_concats_and_saves(
        self,
        mock_tsy,
        mock_ovx,
        mock_vix,
        mock_vvix,
        mock_save,
        mock_load,
        mock_fetch,
    ):
        """Saved DataFrame should contain both cached + new data (concatenated)."""
        from volforecast.cli.ingest_iv import run

        # Cached: Jan-Mar
        cached = _make_iv_dataframe(start="2024-01-02", end="2024-03-29")
        cached = cached.copy()
        cached["term_slope"] = cached["iv_3m_atm"] - cached["iv_1m_atm"]
        cached["skew_1m"] = cached["iv_1m_25dp"] - cached["iv_1m_25dc"]
        mock_load.return_value = cached

        # New: Apr-Jun
        new_data = _make_iv_dataframe(start="2024-04-01", end="2024-06-28")
        mock_fetch.return_value = new_data

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 6, 28),
            symbols=["SPY"],
            force=False,
            skip_market_wide=True,
        )

        # Saved DataFrame should cover full range
        save_calls = [c for c in mock_save.call_args_list if c.args[0] == "SPY"]
        assert len(save_calls) == 1
        saved_df = save_calls[0].args[1]
        # Should have rows from both cached and new data
        assert saved_df.index.min().date() == date(2024, 1, 2)
        assert saved_df.index.max().date() >= date(2024, 6, 27)
        # Should have more rows than either part alone
        assert len(saved_df) > len(cached)
        assert len(saved_df) > len(new_data)

    @patch("volforecast.data.edrvol.fetch_edrvol")
    @patch("volforecast.data.edrvol.load_iv_cache", return_value=None)
    @patch("volforecast.data.edrvol.save_iv_cache")
    @patch("volforecast.data.edrvol.fetch_vvix")
    @patch("volforecast.data.edrvol.fetch_vix_index")
    @patch("volforecast.data.edrvol.fetch_ovx")
    @patch("volforecast.data.edrvol.fetch_treasury_yields")
    def test_no_cache_fetches_full_range(
        self,
        mock_tsy,
        mock_ovx,
        mock_vix,
        mock_vvix,
        mock_save,
        mock_load,
        mock_fetch,
    ):
        """With no existing cache, fetches the full requested range."""
        from volforecast.cli.ingest_iv import run

        full_data = _make_iv_dataframe(start="2024-01-02", end="2024-06-28")
        mock_fetch.return_value = full_data

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 6, 28),
            symbols=["SPY"],
            force=False,
            skip_market_wide=True,
        )

        # fetch_edrvol called with the full start date
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        fetch_start = (
            call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("start_date")
        )
        assert fetch_start == date(2024, 1, 2)
