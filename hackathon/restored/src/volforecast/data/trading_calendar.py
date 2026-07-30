"""NYSE trading calendar — holidays and trading days.

Provides accurate NYSE trading days (excludes weekends + NYSE holidays).
Used by rv_panel.py to determine which dates to fetch tick data for.

Note: This is distinct from features/calendar.py which computes
calendar-based predictive features (FOMC proximity, OpEx, etc.).
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from pandas.tseries.holiday import (
    AbstractHolidayCalendar,
    GoodFriday,
    Holiday,
    USLaborDay,
    USMartinLutherKingJr,
    USMemorialDay,
    USPresidentsDay,
    USThanksgivingDay,
    nearest_workday,
)


class _NYSEHolidayCalendar(AbstractHolidayCalendar):
    """NYSE holiday calendar.

    NYSE closes for:
    - New Year's Day (Jan 1, observed Fri/Mon if weekend)
    - MLK Day (3rd Monday Jan)
    - Presidents' Day (3rd Monday Feb)
    - Good Friday
    - Memorial Day (last Monday May)
    - Juneteenth (Jun 19, since 2022, observed Fri/Mon if weekend)
    - Independence Day (Jul 4, observed Fri/Mon if weekend)
    - Labor Day (1st Monday Sep)
    - Thanksgiving (4th Thursday Nov)
    - Christmas (Dec 25, observed Fri/Mon if weekend)

    NYSE does NOT close for Columbus Day or Veterans Day.
    """

    rules = [
        Holiday("New Year's Day", month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        Holiday(
            "Juneteenth",
            month=6,
            day=19,
            start_date="2022-01-01",
            observance=nearest_workday,
        ),
        Holiday(
            "Independence Day",
            month=7,
            day=4,
            observance=nearest_workday,
        ),
        USLaborDay,
        USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
    ]


# Module-level singleton (calendar instances are cached by pandas internally)
_NYSE_CALENDAR = _NYSEHolidayCalendar()


def get_trading_days(start_date: date, end_date: date) -> list[date]:
    """Return NYSE trading days between start_date and end_date (inclusive).

    Parameters
    ----------
    start_date : date
        First date of range (inclusive).
    end_date : date
        Last date of range (inclusive).

    Returns
    -------
    list[date]
        Sorted list of trading days (excludes weekends and NYSE holidays).
    """
    if end_date < start_date:
        return []

    # Generate business days then remove holidays
    holidays = _NYSE_CALENDAR.holidays(
        start=pd.Timestamp(start_date),
        end=pd.Timestamp(end_date),
    )

    bdays = pd.bdate_range(start=start_date, end=end_date)
    trading_days = bdays.difference(holidays)

    return [ts.date() for ts in trading_days]
