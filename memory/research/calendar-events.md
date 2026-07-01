---
created: 2026-05-07
updated: 2026-05-07
tags: [calendar, events, FOMC, earnings, OpEx, macro-releases]
status: active
priority: P2
source: workspace/research/calendar-events.md (archived)
relates: [feature-composition, optimal-feature-set]
---

# Calendar and Event Features — Summary

## Feature Layer 5 — Calendar/Event Structure

| Feature | Construction | Why |
|---------|-------------|-----|
| FOMC indicator | {-1, 0, +1, +2} days relative to announcement | Vol compression before, expansion after |
| NFP/CPI indicator | Same relative-day encoding | Macro release effect |
| Options expiry | Monthly/quarterly OpEx flag | Pinning + gamma unwind |
| Quarter-end rebalancing | Last 3 days of quarter | Forced portfolio flows |
| Earnings proximity | Days to next earnings (single names) | Mechanical vol run-up |
| Time-of-day (intraday only) | Session fraction 0-1 | U-shape: open+close highest |
| Day-of-week | One-hot Mon-Fri | Weakening over time |

## Key Findings

- Lee (2012): earnings announcements **almost always trigger jumps** — most reliable event-driven vol signal
- FOMC and NFP dominate for index vol (E-mini); earnings don't directly apply to index
- These features are "Layer 5" — individually weak but tree models pick them up naturally
- Collectively additive with other layers

## Design Decisions

- Binary calendar dummies vs distance-to-event features? (open question — test both)
- Event-implied vol (surface-derived σ_event) more informative than binary dummies
- Important for single-stock vol (earnings huge); less so for index

## Open Questions

- How much do FOMC/earnings/macro releases improve vol beyond HAR on our data?
- Simple binary dummy sufficient, or need distance features?
- How do monthly/quarterly OpEx affect next-day RV?
