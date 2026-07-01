---
created: 2026-05-07
updated: 2026-05-07
tags: [jumps, BPV, continuous-variation, HAR-J, HAR-CJ, Lee-Mykland]
status: active
priority: P2
source: workspace/research/jump-detection.md (archived)
relates: [har-components, optimal-feature-set, leverage-effect]
---

# Jump Detection — Summary

## Key Concepts

- **Bipower Variation:** BPV_t = (π/2) × Σ|r_{t,i}|×|r_{t,i-1}| → converges to integrated variance even with jumps
- **Jump component:** J_t = max(RV_t − BPV_t, 0)
- **Continuous variation:** C_t = min(RV_t, BPV_t) = max(BPV_t, 0)
- **Jump test (BNS):** Compare RV−BPV, standardized by quarticity

## Research Findings

**Jump persistence and forecasting:**
- Andersen-Bollerslev-Diebold (2007, "Roughing It Up"): jump component less persistent than continuous
- Implication: jump features help short-horizon forecasts more than long
- Continuous variation (ACF ~0.6-0.7) drives forecasts; jumps (ACF ~0.0-0.1) signal regime breaks

**Earnings and event-driven jumps:**
- Lee (2012): earnings announcements almost always trigger jumps — most reliable event-driven vol signal
- Lee-Mykland (2008, RFS): intraday jump test identifies exact jump times within day

**Standard tools for our project:**
- BNS bipower variation test (daily frequency)
- Lee-Mykland (2008) intraday test (if needed at tick level)
- Ait-Sahalia & Jacod (2009) power-variation-ratio tests (alternative)

## Questions for Our Data

- How frequent are jumps across 34 symbols? Daily? Weekly?
- How large relative to continuous variation?
- Does separating C and J actually help QLIKE on our panel?
- Which test works best at our tick frequency?
