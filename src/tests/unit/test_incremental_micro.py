"""Unit tests for incremental micro ingestion (date-level delta).

Tests:
  - _get_cached_dates extracts dates from existing sequences parquet
  - Incremental ingestion only fetches missing dates (not full range)
  - _consolidate_staging merges with existing sequences (no data loss)
  - Explicit skip/gap logging
  - --detect-gaps dry-run mode
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


def _make_bars_for_dates(dates: list[date], n_bars: int = 100) -> dict[date, pd.DataFrame]:
    """Create synthetic 10s bar data for specific dates."""
    rng = np.random.default_rng(42)
    result = {}
    for d in dates:
        result[d] = pd.DataFrame(
            {
                "buy_vol": rng.uniform(50, 500, size=n_bars),
                "sell_vol": rng.uniform(50, 500, size=n_bars),
                "neutral_vol": rng.uniform(0, 50, size=n_bars),
                "vwap": rng.uniform(190, 210, size=n_bars),
                "n_trades": rng.integers(10, 200, size=n_bars),
            }
        )
    return result


class TestGetCachedDates:
    """Test _get_cached_dates extracts dates from existing sequences parquet."""

    def test_returns_empty_when_no_cache(self, tmp_path):
        from volforecast.data.micro import _get_cached_dates

        result = _get_cached_dates("SPY", sequences_dir=tmp_path)
        assert result == set()

    def test_extracts_dates_from_sequences_parquet(self, tmp_path):
        from volforecast.data.micro import _get_cached_dates, save_sequences_cache

        # Create a sequences parquet with known dates
        dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        rows = []
        for d in dates:
            for i in range(10):
                rows.append({"date": d, "bar_idx": i, "buy_vol": 100.0, "sell_vol": 50.0})
        df = pd.DataFrame(rows)
        save_sequences_cache("SPY", df, sequences_dir=tmp_path)

        result = _get_cached_dates("SPY", sequences_dir=tmp_path)
        assert result == set(dates)

    def test_handles_string_dates_in_parquet(self, tmp_path):
        from volforecast.data.micro import _get_cached_dates, save_sequences_cache

        # Create parquet where dates are stored as strings (edge case)
        rows = [
            {"date": "2024-01-02", "bar_idx": 0, "buy_vol": 100.0, "sell_vol": 50.0},
            {"date": "2024-01-03", "bar_idx": 0, "buy_vol": 100.0, "sell_vol": 50.0},
        ]
        df = pd.DataFrame(rows)
        save_sequences_cache("SPY", df, sequences_dir=tmp_path)

        result = _get_cached_dates("SPY", sequences_dir=tmp_path)
        assert date(2024, 1, 2) in result
        assert date(2024, 1, 3) in result


class TestIncrementalFetch:
    """Incremental ingestion only fetches dates not already cached."""

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_only_fetches_missing_dates(self, mock_fetch, tmp_path):
        """If 2024-01-02 through 2024-01-04 are cached, only 2024-01-05 is fetched."""
        from volforecast.data.micro import (
            _build_sequences_df,
            ingest_symbol_micro,
            save_sequences_cache,
        )

        # Pre-populate sequences cache with 3 days
        cached_dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        # Mock fetch returns data for the new day
        new_date = date(2024, 1, 5)
        mock_fetch.return_value = _make_bars_for_dates([new_date])

        daily_df, result_seq_df = ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 5),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        # fetch_micro_bars should only be called with the missing date
        mock_fetch.assert_called_once()
        fetched_dates = mock_fetch.call_args[0][1]  # second positional arg
        assert date(2024, 1, 5) in fetched_dates
        assert date(2024, 1, 2) not in fetched_dates
        assert date(2024, 1, 3) not in fetched_dates
        assert date(2024, 1, 4) not in fetched_dates

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_skips_entirely_when_all_cached(self, mock_fetch, tmp_path):
        """If all requested dates are cached, fetch is not called."""
        from volforecast.data.micro import (
            _build_sequences_df,
            ingest_symbol_micro,
            save_sequences_cache,
        )

        # Pre-populate with all requested dates
        cached_dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        daily_df, result_seq = ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        mock_fetch.assert_not_called()
        # Should still return valid data from cache
        assert not daily_df.empty

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_fills_gaps_in_existing_range(self, mock_fetch, tmp_path):
        """With fill_gaps=True, fetches missing date 3 within cached range."""
        from volforecast.data.micro import (
            _build_sequences_df,
            ingest_symbol_micro,
            save_sequences_cache,
        )

        # Cache has a gap: day 3 missing
        cached_dates = [date(2024, 1, 2), date(2024, 1, 4)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        # Mock returns the gap day
        mock_fetch.return_value = _make_bars_for_dates([date(2024, 1, 3)])

        ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            fill_gaps=True,
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        fetched_dates = mock_fetch.call_args[0][1]
        assert date(2024, 1, 3) in fetched_dates
        assert date(2024, 1, 2) not in fetched_dates
        assert date(2024, 1, 4) not in fetched_dates

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_gaps_ignored_by_default(self, mock_fetch, tmp_path):
        """Without fill_gaps, historical gaps are not fetched (forward-only)."""
        from volforecast.data.micro import (
            _build_sequences_df,
            ingest_symbol_micro,
            save_sequences_cache,
        )

        # Cache: days 1, 2, 4 (gap at day 3, extension at day 5)
        cached_dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 5)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        # Request range includes gap (day 4) and extension (day 8)
        mock_fetch.return_value = _make_bars_for_dates([date(2024, 1, 8)])

        ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 8),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        # Only forward extension (after max cached = Jan 5) should be fetched
        # Day 4 (gap) should NOT be fetched
        mock_fetch.assert_called_once()
        fetched_dates = mock_fetch.call_args[0][1]
        assert date(2024, 1, 4) not in fetched_dates
        # Days after Jan 5 should be fetched
        assert all(d > date(2024, 1, 5) for d in fetched_dates)

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_force_ignores_cache(self, mock_fetch, tmp_path):
        """--force should re-fetch all dates regardless of cache."""
        from volforecast.data.micro import (
            _build_sequences_df,
            ingest_symbol_micro,
            save_sequences_cache,
        )

        # Pre-populate cache
        cached_dates = [date(2024, 1, 2), date(2024, 1, 3)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        mock_fetch.return_value = _make_bars_for_dates(cached_dates)

        ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 3),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
            force=True,
        )

        # With --force, all dates should be fetched
        mock_fetch.assert_called_once()
        fetched_dates = mock_fetch.call_args[0][1]
        assert date(2024, 1, 2) in fetched_dates
        assert date(2024, 1, 3) in fetched_dates


class TestConsolidationPreservesExisting:
    """_consolidate_staging merges new staging with existing sequences."""

    def test_existing_data_preserved_after_consolidation(self, tmp_path):
        """Existing sequences are not lost when consolidating new staging."""
        import volforecast.data.micro as micro_mod
        from volforecast.data.micro import (
            _build_sequences_df,
            _consolidate_staging,
            _write_staging_batch,
            save_sequences_cache,
        )

        orig_staging = micro_mod.micro_staging_dir
        micro_mod.micro_staging_dir = lambda sym: tmp_path / ".staging" / sym

        try:
            # Pre-existing sequences: days 1 and 2
            existing_dates = [date(2024, 1, 2), date(2024, 1, 3)]
            existing_bars = _make_bars_for_dates(existing_dates)
            existing_seq = _build_sequences_df(existing_bars)
            save_sequences_cache("SPY", existing_seq, sequences_dir=tmp_path / "sequences")

            # New staging: day 3
            new_bars = _make_bars_for_dates([date(2024, 1, 4)])
            _write_staging_batch("SPY", new_bars)

            # Consolidate should merge existing + new
            result = _consolidate_staging("SPY", sequences_dir=tmp_path / "sequences")

            result_dates = set(result["date"].unique())
            assert date(2024, 1, 2) in result_dates
            assert date(2024, 1, 3) in result_dates
            assert date(2024, 1, 4) in result_dates

        finally:
            micro_mod.micro_staging_dir = orig_staging

    def test_duplicate_dates_deduplicated(self, tmp_path):
        """If staging has same date as existing, staging wins (newer data)."""
        import volforecast.data.micro as micro_mod
        from volforecast.data.micro import (
            _build_sequences_df,
            _consolidate_staging,
            _write_staging_batch,
            save_sequences_cache,
        )

        orig_staging = micro_mod.micro_staging_dir
        micro_mod.micro_staging_dir = lambda sym: tmp_path / ".staging" / sym

        try:
            # Existing sequences: day 1 with 10 bars
            existing_bars = _make_bars_for_dates([date(2024, 1, 2)], n_bars=10)
            existing_seq = _build_sequences_df(existing_bars)
            save_sequences_cache("SPY", existing_seq, sequences_dir=tmp_path / "sequences")

            # Staging also has day 1 with 20 bars (newer/corrected data)
            new_bars = _make_bars_for_dates([date(2024, 1, 2)], n_bars=20)
            _write_staging_batch("SPY", new_bars)

            result = _consolidate_staging("SPY", sequences_dir=tmp_path / "sequences")

            # The staging version (20 bars) should win
            day1_bars = result[result["date"] == date(2024, 1, 2)]
            assert len(day1_bars) == 20

        finally:
            micro_mod.micro_staging_dir = orig_staging


class TestSkipLogging:
    """Verify explicit logging of skipped and fetched date ranges."""

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_logs_skipped_and_fetched_ranges(self, mock_fetch, tmp_path, caplog):
        """Should log which dates are skipped and which are fetched."""
        import logging

        from volforecast.data.micro import (
            _build_sequences_df,
            ingest_symbol_micro,
            save_sequences_cache,
        )

        # Cache 3 days, request 4 (one new)
        cached_dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        mock_fetch.return_value = _make_bars_for_dates([date(2024, 1, 5)])

        with caplog.at_level(logging.INFO, logger="volforecast.data.micro"):
            ingest_symbol_micro(
                "SPY",
                date(2024, 1, 2),
                date(2024, 1, 5),
                cache_dir=tmp_path,
                sequences_dir=tmp_path / "sequences",
            )

        log_text = caplog.text
        # Should mention skipping cached dates
        assert "skipping" in log_text.lower() or "cached" in log_text.lower()
        # Should mention fetching missing dates
        assert "missing" in log_text.lower() or "fetching" in log_text.lower()

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_logs_all_cached_skip(self, mock_fetch, tmp_path, caplog):
        """When all dates cached, should log that everything is skipped."""
        import logging

        from volforecast.data.micro import (
            _build_sequences_df,
            ingest_symbol_micro,
            save_sequences_cache,
        )

        cached_dates = [date(2024, 1, 2), date(2024, 1, 3)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        with caplog.at_level(logging.INFO, logger="volforecast.data.micro"):
            ingest_symbol_micro(
                "SPY",
                date(2024, 1, 2),
                date(2024, 1, 3),
                cache_dir=tmp_path,
                sequences_dir=tmp_path / "sequences",
            )

        mock_fetch.assert_not_called()
        log_text = caplog.text
        assert "cached" in log_text.lower() or "skip" in log_text.lower()


class TestDetectGaps:
    """Test --detect-gaps dry-run mode."""

    def test_detect_gaps_returns_missing_dates(self, tmp_path):
        from volforecast.data.micro import (
            _build_sequences_df,
            detect_gaps,
            save_sequences_cache,
        )

        # Cache has gap: days 1 and 3, missing day 2
        cached_dates = [date(2024, 1, 2), date(2024, 1, 4)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        gaps = detect_gaps(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            sequences_dir=tmp_path / "sequences",
        )

        assert date(2024, 1, 3) in gaps

    def test_detect_gaps_empty_when_complete(self, tmp_path):
        from volforecast.data.micro import (
            _build_sequences_df,
            detect_gaps,
            save_sequences_cache,
        )

        # All trading days cached
        cached_dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        bars = _make_bars_for_dates(cached_dates)
        seq_df = _build_sequences_df(bars)
        save_sequences_cache("SPY", seq_df, sequences_dir=tmp_path / "sequences")

        gaps = detect_gaps(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            sequences_dir=tmp_path / "sequences",
        )

        assert gaps == []
