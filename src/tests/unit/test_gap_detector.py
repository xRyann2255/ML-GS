"""Tests for gap_detector module — NYSE-calendar-aware interior gap detection.

TDD: these tests define expected behavior for detect_gaps() and coalesce_dates().
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.cli.gap_detector import coalesce_dates, detect_gaps

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create temporary data directories."""
    for subdir in ("ticks", "iv", "ohlcv", "micro", "cross_asset"):
        (tmp_path / "data" / "raw" / subdir).mkdir(parents=True)
    return tmp_path


def _make_parquet(path: Path, dates: list[date], columns: list[str] | None = None) -> None:
    """Write a parquet with given dates as index and dummy columns."""
    cols = columns or ["rv", "bpv"]
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates], name="date")
    df = pd.DataFrame(
        np.random.default_rng(42).random((len(dates), len(cols))), index=idx, columns=cols
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


# ── coalesce_dates tests ──────────────────────────────────────────────────


class TestCoalesceDates:
    def test_empty_list(self) -> None:
        assert coalesce_dates([]) == []

    def test_single_day(self) -> None:
        result = coalesce_dates([date(2024, 3, 15)])
        assert result == [(date(2024, 3, 15), date(2024, 3, 15))]

    def test_consecutive_trading_days_merged(self) -> None:
        # Mon-Fri consecutive
        days = [
            date(2024, 3, 11),
            date(2024, 3, 12),
            date(2024, 3, 13),
            date(2024, 3, 14),
            date(2024, 3, 15),
        ]
        result = coalesce_dates(days)
        assert result == [(date(2024, 3, 11), date(2024, 3, 15))]

    def test_weekend_break_splits_ranges(self) -> None:
        # Fri + next Mon — these are consecutive TRADING days (no weekend gap in calendar terms)
        # coalesce_dates works on calendar adjacency: gap > 3 calendar days = new range
        fri = date(2024, 3, 15)
        mon = date(2024, 3, 18)
        result = coalesce_dates([fri, mon])
        # 3 calendar days apart (Sat, Sun) — should still merge (weekend is expected gap)
        assert result == [(fri, mon)]

    def test_true_gap_splits_ranges(self) -> None:
        # Two days with a real gap between them (> 3 calendar days apart)
        day1 = date(2024, 3, 11)  # Monday
        day2 = date(2024, 3, 18)  # Next Monday (7 calendar days apart)
        result = coalesce_dates([day1, day2])
        # 7 calendar days apart — split into two ranges
        assert result == [(day1, day1), (day2, day2)]

    def test_multiple_groups(self) -> None:
        days = [
            date(2024, 3, 11),
            date(2024, 3, 12),  # Mon-Tue
            # gap of a week
            date(2024, 3, 25),
            date(2024, 3, 26),
            date(2024, 3, 27),  # Mon-Tue-Wed
        ]
        result = coalesce_dates(days)
        assert len(result) == 2
        assert result[0] == (date(2024, 3, 11), date(2024, 3, 12))
        assert result[1] == (date(2024, 3, 25), date(2024, 3, 27))


# ── detect_gaps tests ─────────────────────────────────────────────────────


class TestDetectGaps:
    def test_complete_cache_returns_empty(self, project_root: Path) -> None:
        """Cache with all trading days → no gaps."""
        from volforecast.data.trading_calendar import get_trading_days

        start, end = date(2024, 1, 2), date(2024, 1, 31)
        all_days = get_trading_days(start, end)
        parquet_path = project_root / "data" / "raw" / "ohlcv" / "AAPL.parquet"
        _make_parquet(parquet_path, all_days, columns=["open", "high", "low", "close", "volume"])

        missing = detect_gaps("ohlcv", "AAPL", start, end, project_root=project_root)
        assert missing == []

    def test_missing_days_detected(self, project_root: Path) -> None:
        """Cache with 3 days removed → those days reported as missing."""
        from volforecast.data.trading_calendar import get_trading_days

        start, end = date(2024, 1, 2), date(2024, 1, 31)
        all_days = get_trading_days(start, end)
        # Remove 3 specific days
        removed = {all_days[5], all_days[10], all_days[15]}
        cached_days = [d for d in all_days if d not in removed]

        parquet_path = project_root / "data" / "raw" / "ohlcv" / "AAPL.parquet"
        _make_parquet(parquet_path, cached_days, columns=["open", "high", "low", "close", "volume"])

        missing = detect_gaps("ohlcv", "AAPL", start, end, project_root=project_root)
        assert set(missing) == removed

    def test_weekends_not_reported_as_missing(self, project_root: Path) -> None:
        """Weekends and holidays are NOT reported as gaps."""
        from volforecast.data.trading_calendar import get_trading_days

        # Full month — all trading days present
        start, end = date(2024, 7, 1), date(2024, 7, 31)
        all_days = get_trading_days(start, end)
        # July 4 2024 is Thursday (NYSE closed) — should NOT be in expected
        assert date(2024, 7, 4) not in all_days

        parquet_path = project_root / "data" / "raw" / "ohlcv" / "AAPL.parquet"
        _make_parquet(parquet_path, all_days, columns=["open", "high", "low", "close", "volume"])

        missing = detect_gaps("ohlcv", "AAPL", start, end, project_root=project_root)
        assert missing == []

    def test_empty_cache_returns_all_trading_days(self, project_root: Path) -> None:
        """Non-existent parquet → all trading days are missing."""
        from volforecast.data.trading_calendar import get_trading_days

        start, end = date(2024, 1, 2), date(2024, 1, 10)
        expected = get_trading_days(start, end)

        missing = detect_gaps("ohlcv", "AAPL", start, end, project_root=project_root)
        assert missing == expected

    def test_ticks_source(self, project_root: Path) -> None:
        """Works for ticks source (different directory)."""
        from volforecast.data.trading_calendar import get_trading_days

        start, end = date(2024, 3, 1), date(2024, 3, 15)
        all_days = get_trading_days(start, end)
        # Remove 2 days
        removed = {all_days[2], all_days[7]}
        cached_days = [d for d in all_days if d not in removed]

        parquet_path = project_root / "data" / "raw" / "ticks" / "SPY.parquet"
        _make_parquet(
            parquet_path, cached_days, columns=["rv", "bpv", "rs_positive", "rs_negative"]
        )

        missing = detect_gaps("ticks", "SPY", start, end, project_root=project_root)
        assert set(missing) == removed

    def test_iv_source(self, project_root: Path) -> None:
        """Works for IV source."""
        from volforecast.data.trading_calendar import get_trading_days

        start, end = date(2024, 2, 1), date(2024, 2, 15)
        all_days = get_trading_days(start, end)
        removed = {all_days[3]}
        cached_days = [d for d in all_days if d not in removed]

        parquet_path = project_root / "data" / "raw" / "iv" / "AAPL.parquet"
        _make_parquet(parquet_path, cached_days, columns=["iv_1m_atm", "iv_3m_atm"])

        missing = detect_gaps("iv", "AAPL", start, end, project_root=project_root)
        assert set(missing) == removed

    def test_cross_asset_group_file(self, project_root: Path) -> None:
        """Cross-asset uses group-level files (rates.parquet, not per-symbol)."""
        from volforecast.data.trading_calendar import get_trading_days

        start, end = date(2024, 4, 1), date(2024, 4, 30)
        all_days = get_trading_days(start, end)
        removed = {all_days[5], all_days[6]}
        cached_days = [d for d in all_days if d not in removed]

        parquet_path = project_root / "data" / "raw" / "cross_asset" / "rates.parquet"
        _make_parquet(parquet_path, cached_days, columns=["yield_5y", "yield_10y"])

        # For cross_asset, "symbol" is the group file name (e.g., "rates")
        missing = detect_gaps("cross_asset", "rates", start, end, project_root=project_root)
        assert set(missing) == removed

    def test_date_index_as_date_objects(self, project_root: Path) -> None:
        """Parquets with date index (not DatetimeIndex) are handled correctly."""
        from volforecast.data.trading_calendar import get_trading_days

        start, end = date(2024, 1, 2), date(2024, 1, 15)
        all_days = get_trading_days(start, end)
        removed = {all_days[3]}
        cached_days = [d for d in all_days if d not in removed]

        # Write with plain date index (some parquets use this)
        path = project_root / "data" / "raw" / "ohlcv" / "TEST.parquet"
        idx = pd.Index(cached_days, name="date")
        df = pd.DataFrame({"close": range(len(cached_days))}, index=idx)
        df.to_parquet(path)

        missing = detect_gaps("ohlcv", "TEST", start, end, project_root=project_root)
        assert set(missing) == removed
