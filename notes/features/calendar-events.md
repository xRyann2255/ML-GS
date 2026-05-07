# Calendar and Event Features

Features related to scheduled events, macro releases, and their impact on volatility.

## Questions to Answer

- How much do FOMC dates, earnings, and macro releases improve vol forecasts beyond HAR?
- Is a simple binary calendar dummy sufficient, or do you need distance-to-event features?
- How do expiration dates (monthly/quarterly opex) affect next-day RV?

## Deep Research Findings (2026-05-06)

- Calendar/event features include: day of week, holiday proximity, FOMC dates, earnings announcement dates, macro release calendars
- Lee 2012 shows earnings announcements almost always trigger jumps -- earnings dates are among the most reliable event-driven vol signals
- These features are "Layer 5" in the optimal feature set -- important for regime-aware models but secondary to HAR core, asymmetry, and implied-vol features
