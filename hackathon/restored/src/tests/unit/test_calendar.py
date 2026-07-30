"""Tests for Layer 5 calendar/event features."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from volforecast.features.calendar import (
    CalendarLayer,
    _nth_weekday,
    compute_calendar_dummies,
    compute_fomc_proximity,
    compute_nfp_proximity,
    compute_opex_proximity,
)


class TestNthWeekday:
    def test_first_friday_jan_2024(self):
        """First Friday of January 2024 = Jan 5."""
        result = _nth_weekday(2024, 1, 4, 1)  # weekday 4 = Friday
        assert result == date(2024, 1, 5)

    def test_first_friday_feb_2024(self):
        """First Friday of February 2024 = Feb 2."""
        result = _nth_weekday(2024, 2, 4, 1)
        assert result == date(2024, 2, 2)

    def test_third_friday_jan_2024(self):
        """Third Friday of January 2024 = Jan 19."""
        result = _nth_weekday(2024, 1, 4, 3)
        assert result == date(2024, 1, 19)

    def test_third_friday_mar_2024(self):
        """Third Friday of March 2024 = Mar 15."""
        result = _nth_weekday(2024, 3, 4, 3)
        assert result == date(2024, 3, 15)


class TestFOMCProximity:
    def test_fomc_on_fomc_day(self):
        """On an FOMC day: days_to_fomc==0, fomc_day==1."""
        # Jan 31, 2024 is an FOMC date
        dates = pd.DatetimeIndex([pd.Timestamp("2024-01-31")])
        result = compute_fomc_proximity(dates)
        assert result["days_to_fomc"].iloc[0] == 0
        assert result["fomc_day"].iloc[0] == 1
        assert result["fomc_week"].iloc[0] == 1

    def test_fomc_days_before(self):
        """A few days before FOMC: positive days_to_fomc, fomc_week=1."""
        # Jan 29, 2024 is 2 business days before Jan 31 FOMC
        dates = pd.DatetimeIndex([pd.Timestamp("2024-01-29")])
        result = compute_fomc_proximity(dates)
        assert result["days_to_fomc"].iloc[0] == 2
        assert result["fomc_week"].iloc[0] == 1
        assert result["fomc_day"].iloc[0] == 0

    def test_fomc_far_away(self):
        """Far from FOMC: fomc_week=0."""
        # Feb 15, 2024: next FOMC is Mar 20
        dates = pd.DatetimeIndex([pd.Timestamp("2024-02-15")])
        result = compute_fomc_proximity(dates)
        assert result["days_to_fomc"].iloc[0] > 5
        assert result["fomc_week"].iloc[0] == 0


class TestNFPProximity:
    def test_nfp_rolls_to_next_month(self):
        """Day after NFP -> next month's first Friday."""
        # First Friday of Jan 2024 = Jan 5. On Jan 8 (Monday after), next NFP = Feb 2.
        dates = pd.DatetimeIndex([pd.Timestamp("2024-01-08")])
        result = compute_nfp_proximity(dates)
        # Feb 2 is first Friday of Feb 2024. Jan 8 -> Feb 2 = 19 business days
        assert result["days_to_nfp"].iloc[0] > 0

    def test_nfp_on_nfp_day(self):
        """On NFP day: days_to_nfp == 0."""
        # First Friday of Jan 2024 = Jan 5
        dates = pd.DatetimeIndex([pd.Timestamp("2024-01-05")])
        result = compute_nfp_proximity(dates)
        assert result["days_to_nfp"].iloc[0] == 0


class TestOpexProximity:
    def test_opex_on_opex_day(self):
        """On OpEx day: days_to_opex == 0."""
        # Third Friday of Jan 2024 = Jan 19
        dates = pd.DatetimeIndex([pd.Timestamp("2024-01-19")])
        result = compute_opex_proximity(dates)
        assert result["days_to_opex"].iloc[0] == 0

    def test_opex_week_before(self):
        """Within a week of OpEx -> opex_week=1."""
        # Jan 16, 2024 is Tuesday. OpEx Jan 19 (Fri) = 3 bdays away
        dates = pd.DatetimeIndex([pd.Timestamp("2024-01-16")])
        result = compute_opex_proximity(dates)
        assert result["days_to_opex"].iloc[0] == 3
        assert result["opex_week"].iloc[0] == 1


class TestCalendarDummies:
    def test_calendar_dummies_types(self):
        """day_of_week and month are int, not float."""
        dates = pd.bdate_range("2024-01-01", periods=50, freq="B")
        result = compute_calendar_dummies(dates)
        assert result["day_of_week"].dtype in (np.int32, np.int64, int)
        assert result["month"].dtype in (np.int32, np.int64, int)

    def test_day_of_week_range(self):
        """day_of_week in [0, 4] for business days."""
        dates = pd.bdate_range("2024-01-01", periods=100, freq="B")
        result = compute_calendar_dummies(dates)
        assert result["day_of_week"].min() >= 0
        assert result["day_of_week"].max() <= 4

    def test_month_range(self):
        """month in [1, 12]."""
        dates = pd.bdate_range("2024-01-01", periods=252, freq="B")
        result = compute_calendar_dummies(dates)
        assert result["month"].min() >= 1
        assert result["month"].max() <= 12


class TestCalendarLayer:
    def test_calendar_no_shift(self):
        """Calendar features at date t reflect t's own position (no shift)."""
        # Wednesday Jan 3, 2024 -> day_of_week = 2
        dates = pd.DatetimeIndex([pd.Timestamp("2024-01-03")])
        daily_data = pd.DataFrame({"rv": [0.0001]}, index=dates)
        layer = CalendarLayer()
        result = layer.compute(daily_data)
        assert result["day_of_week"].iloc[0] == 2  # Wednesday

    def test_calendar_ignores_context(self):
        """Context is accepted but ignored."""
        dates = pd.bdate_range("2024-01-01", periods=10, freq="B")
        daily_data = pd.DataFrame({"rv": np.ones(10) * 0.0001}, index=dates)
        layer = CalendarLayer()
        # Should not raise with context=None or context={"anything": ...}
        result1 = layer.compute(daily_data, context=None)
        result2 = layer.compute(daily_data, context={"foo": pd.DataFrame()})
        pd.testing.assert_frame_equal(result1, result2)

    def test_categorical_features_attribute(self):
        """Layer declares CATEGORICAL_FEATURES."""
        assert CalendarLayer.CATEGORICAL_FEATURES == ("day_of_week", "month")
