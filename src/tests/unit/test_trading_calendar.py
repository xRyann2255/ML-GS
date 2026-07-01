"""Tests for NYSE trading calendar.

TDD: Tests written first, implementation follows.
Ground truth from NYSE's published 2024/2025 holiday schedules.
"""

from __future__ import annotations

from datetime import date

import pytest

from volforecast.data.trading_calendar import get_trading_days


class TestSkipsWeekends:
    """No Saturdays or Sundays in output."""

    def test_all_days_are_weekdays(self):
        days = get_trading_days(date(2024, 1, 1), date(2024, 12, 31))
        for d in days:
            assert d.weekday() < 5, f"{d} is a weekend"

    def test_week_has_at_most_five_days(self):
        # A normal week Mon-Fri
        days = get_trading_days(date(2024, 3, 4), date(2024, 3, 8))
        assert len(days) == 5


class TestNYSEHolidays2024:
    """NYSE was closed on these dates in 2024."""

    @pytest.mark.parametrize(
        "holiday_date,name",
        [
            (date(2024, 1, 1), "New Year's Day"),
            (date(2024, 1, 15), "MLK Day"),
            (date(2024, 2, 19), "Presidents' Day"),
            (date(2024, 3, 29), "Good Friday"),
            (date(2024, 5, 27), "Memorial Day"),
            (date(2024, 6, 19), "Juneteenth"),
            (date(2024, 7, 4), "Independence Day"),
            (date(2024, 9, 2), "Labor Day"),
            (date(2024, 11, 28), "Thanksgiving"),
            (date(2024, 12, 25), "Christmas"),
        ],
    )
    def test_holiday_excluded(self, holiday_date, name):
        days = get_trading_days(holiday_date, holiday_date)
        assert holiday_date not in days, f"{name} ({holiday_date}) should be excluded"


class TestNYSEHolidays2025:
    """NYSE was closed on these dates in 2025."""

    @pytest.mark.parametrize(
        "holiday_date,name",
        [
            (date(2025, 1, 1), "New Year's Day"),
            (date(2025, 1, 20), "MLK Day"),
            (date(2025, 2, 17), "Presidents' Day"),
            (date(2025, 4, 18), "Good Friday"),
            (date(2025, 5, 26), "Memorial Day"),
            (date(2025, 6, 19), "Juneteenth"),
            (date(2025, 7, 4), "Independence Day"),
            (date(2025, 9, 1), "Labor Day"),
            (date(2025, 11, 27), "Thanksgiving"),
            (date(2025, 12, 25), "Christmas"),
        ],
    )
    def test_holiday_excluded(self, holiday_date, name):
        days = get_trading_days(holiday_date, holiday_date)
        assert holiday_date not in days, f"{name} ({holiday_date}) should be excluded"


class TestNYSENotClosed:
    """Days that are federal holidays but NYSE is OPEN."""

    @pytest.mark.parametrize(
        "open_date,name",
        [
            (date(2024, 10, 14), "Columbus Day 2024"),
            (date(2024, 11, 11), "Veterans Day 2024"),
            (date(2025, 10, 13), "Columbus Day 2025"),
            (date(2025, 11, 11), "Veterans Day 2025"),
        ],
    )
    def test_open_day_included(self, open_date, name):
        days = get_trading_days(open_date, open_date)
        assert open_date in days, f"{name} ({open_date}) — NYSE is open"


class TestPartialRanges:
    """Edge cases: empty ranges, single day, partial years."""

    def test_empty_range(self):
        # End before start
        days = get_trading_days(date(2024, 3, 10), date(2024, 3, 5))
        assert days == []

    def test_single_trading_day(self):
        # A known Tuesday
        days = get_trading_days(date(2024, 3, 5), date(2024, 3, 5))
        assert days == [date(2024, 3, 5)]

    def test_single_weekend_day(self):
        days = get_trading_days(date(2024, 3, 9), date(2024, 3, 9))
        assert days == []

    def test_returns_sorted_list_of_dates(self):
        days = get_trading_days(date(2024, 1, 1), date(2024, 1, 31))
        assert days == sorted(days)
        assert all(isinstance(d, date) for d in days)

    def test_approximate_trading_days_per_year(self):
        """NYSE has ~252 trading days per year."""
        days = get_trading_days(date(2024, 1, 1), date(2024, 12, 31))
        assert 250 <= len(days) <= 253
