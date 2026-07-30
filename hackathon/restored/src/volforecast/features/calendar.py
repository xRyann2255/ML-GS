"""Calendar and event features (Layer 5).

Captures scheduled macro events and calendar effects on volatility:
- FOMC meeting proximity
- Non-Farm Payrolls (NFP) proximity
- Options expiration (OpEx) effects
- Day-of-week and month effects

Calendar features are KNOWN IN ADVANCE — no .shift(1) applied.
day_of_week and month are CATEGORICAL (integer dtype for LightGBM).

Key functions:
    compute_fomc_proximity     — Days to next FOMC, fomc_week, fomc_day
    compute_nfp_proximity      — Days to next NFP, nfp_week
    compute_opex_proximity     — Days to next OpEx, opex_week
    compute_calendar_dummies   — Day-of-week, month, quarter_end, year_end
"""

from __future__ import annotations

import calendar as cal
from datetime import date

import numpy as np
import pandas as pd

from volforecast.registry import register_feature_layer

# ---------------------------------------------------------------------------
# FOMC dates 2015-2026 (statement release day)
# ---------------------------------------------------------------------------

_FOMC_DATES: list[date] = [
    # 2015
    date(2015, 1, 28),
    date(2015, 3, 18),
    date(2015, 4, 29),
    date(2015, 6, 17),
    date(2015, 7, 29),
    date(2015, 9, 17),
    date(2015, 10, 28),
    date(2015, 12, 16),
    # 2016
    date(2016, 1, 27),
    date(2016, 3, 16),
    date(2016, 4, 27),
    date(2016, 6, 15),
    date(2016, 7, 27),
    date(2016, 9, 21),
    date(2016, 11, 2),
    date(2016, 12, 14),
    # 2017
    date(2017, 2, 1),
    date(2017, 3, 15),
    date(2017, 5, 3),
    date(2017, 6, 14),
    date(2017, 7, 26),
    date(2017, 9, 20),
    date(2017, 11, 1),
    date(2017, 12, 13),
    # 2018
    date(2018, 1, 31),
    date(2018, 3, 21),
    date(2018, 5, 2),
    date(2018, 6, 13),
    date(2018, 8, 1),
    date(2018, 9, 26),
    date(2018, 11, 8),
    date(2018, 12, 19),
    # 2019
    date(2019, 1, 30),
    date(2019, 3, 20),
    date(2019, 5, 1),
    date(2019, 6, 19),
    date(2019, 7, 31),
    date(2019, 9, 18),
    date(2019, 10, 30),
    date(2019, 12, 11),
    # 2020
    date(2020, 1, 29),
    date(2020, 3, 3),
    date(2020, 3, 15),
    date(2020, 4, 29),
    date(2020, 6, 10),
    date(2020, 7, 29),
    date(2020, 9, 16),
    date(2020, 11, 5),
    date(2020, 12, 16),
    # 2021
    date(2021, 1, 27),
    date(2021, 3, 17),
    date(2021, 4, 28),
    date(2021, 6, 16),
    date(2021, 7, 28),
    date(2021, 9, 22),
    date(2021, 11, 3),
    date(2021, 12, 15),
    # 2022
    date(2022, 1, 26),
    date(2022, 3, 16),
    date(2022, 5, 4),
    date(2022, 6, 15),
    date(2022, 7, 27),
    date(2022, 9, 21),
    date(2022, 11, 2),
    date(2022, 12, 14),
    # 2023
    date(2023, 2, 1),
    date(2023, 3, 22),
    date(2023, 5, 3),
    date(2023, 6, 14),
    date(2023, 7, 26),
    date(2023, 9, 20),
    date(2023, 11, 1),
    date(2023, 12, 13),
    # 2024
    date(2024, 1, 31),
    date(2024, 3, 20),
    date(2024, 5, 1),
    date(2024, 6, 12),
    date(2024, 7, 31),
    date(2024, 9, 18),
    date(2024, 11, 7),
    date(2024, 12, 18),
    # 2025
    date(2025, 1, 29),
    date(2025, 3, 19),
    date(2025, 5, 7),
    date(2025, 6, 18),
    date(2025, 7, 30),
    date(2025, 9, 17),
    date(2025, 10, 29),
    date(2025, 12, 17),
    # 2026
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 16),
]

_FOMC_SET: set[date] = set(_FOMC_DATES)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the nth occurrence of weekday in month.

    Parameters
    ----------
    year : int
    month : int
    weekday : int
        0=Monday, 4=Friday.
    n : int
        1-indexed (1=first, 3=third).

    Returns
    -------
    date
    """
    # Find first occurrence of weekday in month
    first_day = date(year, month, 1)
    # Days until target weekday
    days_ahead = weekday - first_day.weekday()
    if days_ahead < 0:
        days_ahead += 7
    first_occurrence = first_day.replace(day=1 + days_ahead)
    # nth occurrence
    return first_occurrence.replace(day=first_occurrence.day + 7 * (n - 1))


def _next_fomc(target: date) -> date | None:
    """Find next FOMC date on or after target."""
    for d in _FOMC_DATES:
        if d >= target:
            return d
    return None


def _next_nfp(target: date) -> date:
    """Find next NFP date on or after target. NFP = first Friday of month."""
    year, month = target.year, target.month
    nfp = _nth_weekday(year, month, 4, 1)  # First Friday
    if nfp < target:
        # Move to next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        nfp = _nth_weekday(year, month, 4, 1)
    return nfp


def _next_opex(target: date) -> date:
    """Find next OpEx date on or after target. OpEx = third Friday of month."""
    year, month = target.year, target.month
    opex = _nth_weekday(year, month, 4, 3)  # Third Friday
    if opex < target:
        # Move to next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        opex = _nth_weekday(year, month, 4, 3)
    return opex


def _busday_count(start: date, end: date) -> int:
    """Count business days between start (exclusive) and end (inclusive)."""
    return int(np.busday_count(start, end))


# ---------------------------------------------------------------------------
# Public compute functions
# ---------------------------------------------------------------------------


def compute_fomc_proximity(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute FOMC proximity features for a date index.

    Returns
    -------
    pd.DataFrame
        Columns: days_to_fomc (trading days), fomc_week (bool->int), fomc_day (bool->int).
    """
    days_to = []
    fomc_week = []
    fomc_day = []

    for dt in dates:
        d = dt.date() if hasattr(dt, "date") else dt
        is_fomc = d in _FOMC_SET
        nxt = _next_fomc(d)
        if nxt is None:
            dist = 30  # fallback for dates beyond 2026
        elif nxt == d:
            dist = 0
        else:
            dist = _busday_count(d, nxt)

        days_to.append(dist)
        fomc_week.append(1 if dist <= 5 else 0)
        fomc_day.append(1 if is_fomc else 0)

    return pd.DataFrame(
        {"days_to_fomc": days_to, "fomc_week": fomc_week, "fomc_day": fomc_day},
        index=dates,
    )


def compute_nfp_proximity(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute NFP proximity features for a date index.

    Returns
    -------
    pd.DataFrame
        Columns: days_to_nfp (trading days), nfp_week (bool->int).
    """
    days_to = []
    nfp_week = []

    for dt in dates:
        d = dt.date() if hasattr(dt, "date") else dt
        nxt = _next_nfp(d)
        dist = _busday_count(d, nxt) if nxt != d else 0
        days_to.append(dist)
        nfp_week.append(1 if dist <= 5 else 0)

    return pd.DataFrame(
        {"days_to_nfp": days_to, "nfp_week": nfp_week},
        index=dates,
    )


def compute_opex_proximity(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute options expiration proximity features for a date index.

    Returns
    -------
    pd.DataFrame
        Columns: days_to_opex (trading days), opex_week (bool->int).
    """
    days_to = []
    opex_week = []

    for dt in dates:
        d = dt.date() if hasattr(dt, "date") else dt
        nxt = _next_opex(d)
        dist = _busday_count(d, nxt) if nxt != d else 0
        days_to.append(dist)
        opex_week.append(1 if dist <= 5 else 0)

    return pd.DataFrame(
        {"days_to_opex": days_to, "opex_week": opex_week},
        index=dates,
    )


def compute_calendar_dummies(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute calendar dummy features.

    Returns
    -------
    pd.DataFrame
        Columns: day_of_week (0-4, int), month (1-12, int),
        quarter_end (1 if in last 5 trading days of quarter),
        year_end (1 if in last 10 trading days of December).
    """
    dow = dates.dayofweek.astype(np.int32)
    month = dates.month.astype(np.int32)

    # Quarter end: last 5 trading days of quarter
    quarter_end = np.zeros(len(dates), dtype=np.int32)
    for i, dt in enumerate(dates):
        d = dt.date() if hasattr(dt, "date") else dt
        m = d.month
        # Quarter-end months: 3, 6, 9, 12
        if m in (3, 6, 9, 12):
            # Last day of month
            last_day = date(d.year, m, cal.monthrange(d.year, m)[1])
            # Trading days from d to end of month
            days_left = int(np.busday_count(d, last_day))
            if days_left < 5:
                quarter_end[i] = 1

    # Year end: last 10 trading days of December
    year_end = np.zeros(len(dates), dtype=np.int32)
    for i, dt in enumerate(dates):
        d = dt.date() if hasattr(dt, "date") else dt
        if d.month == 12:
            last_day = date(d.year, 12, 31)
            days_left = int(np.busday_count(d, last_day))
            if days_left < 10:
                year_end[i] = 1

    return pd.DataFrame(
        {
            "day_of_week": dow,
            "month": month,
            "quarter_end": quarter_end,
            "year_end": year_end,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# FeatureLayer wrapper
# ---------------------------------------------------------------------------


@register_feature_layer("calendar")
class CalendarLayer:
    """Calendar/event feature layer (Layer 5).

    Calendar features are known in advance — no shift(1) applied.
    Context is accepted but ignored.
    """

    name = "calendar"
    CATEGORICAL_FEATURES = ("day_of_week", "month")

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """Compute all calendar features."""
        dates = pd.DatetimeIndex(daily_data.index)

        fomc = compute_fomc_proximity(dates)
        nfp = compute_nfp_proximity(dates)
        opex = compute_opex_proximity(dates)
        dummies = compute_calendar_dummies(dates)

        result = pd.concat([fomc, nfp, opex, dummies], axis=1)
        # Restore original index type to avoid type mismatch when concatenating
        # with other feature layers (which use daily_data.index directly).
        result.index = daily_data.index
        return result
