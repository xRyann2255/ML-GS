---
created: 2026-05-07
updated: 2026-05-28
tags: [data, chunk-store, TSDB, marquee, tick-data, universe, timezone, AggGroupBy, EDRVOL, layer2, per-symbol-iv, VVIX, EDRVS]
status: active
priority: P1
source: workspace/research/data-access.md (archived)
relates: [project-scope-and-data, project-design, optimal-feature-set]
---

# Data Access Inventory — Summary

## Universe & History

- **34 symbols**: 30 mega-cap equities + 4 ETFs (SPY, QQQ, IWM, DIA) + E-mini S&P 500 (ES)
- **History**: 11.3 years (~2,800 daily obs per symbol)
- **Tick data**: L1 for all 34 symbols; L2 depth for E-mini only (~4M ticks/day)

## Data Sources

| Source | Coverage | Enables |
|--------|----------|---------|
| Chunk Store (L1 tick) | 34 symbols, 11.3yr | RV at any frequency, RQ, jumps, semivariances |
| Chunk Store (L2 depth) | E-mini only | OBI, depth ratio, VPIN, LSTM input |
| TSDB (daily) | 34 + VIX + vol indices | HAR baselines, ML training |
| TSDB edrvol_ (per-symbol IV) | 25 symbols, 7 tenors x 5 strikes, 2010+ | Per-stock ATM IV, skew, term slope, butterfly |
| Marquee EDRVOL_PERCENT | 5935 symbols (use ric=), full tenor×strike (2013+) | Full surface analysis |
| Marquee EDRVS (per-symbol) | 25+ symbols, 31 tenors, via ric= | Per-stock clean VRP (variance swap) |
| TSDB VVIX | eqsp_s_.vvix@close, 2016+ | Direct vol-of-vol (replaces proxy) |
| VIX term structure | Daily | Regime detection, contango/backwardation |
| TSDB vol indices | RVX, VXN, GVZ, VXEEM, JNIV, 2015+ | Cross-asset vol regime signals |
| Cross-asset | Treasury 2y/5y/10y/30y, FX (USD/JPY, EUR/USD), CL, GC | Spillover features |

## Critical Constraints

1. **L2 depth = E-mini only** → microstructure depth features (OBI levels 2-5, depth ratio) are index-level only
2. **IV surface = SPX only** → options features are market-wide regime signals, not stock-specific
3. **Per-symbol IV surface is AVAILABLE** via TSDB edrvol_ (7 tenors x 5 strikes) and Marquee EDRVOL_PERCENT (ric= param, full 31x49 grid). Constraint 2 no longer applies.

## GS Edge vs Public Data

- Tick-level 34 symbols → precise RQ, kernel estimators (public has only 5-min TAQ)
- Full SPX tenor×strike grid → arbitrary surface derivatives (public has only VIX)
- **Per-symbol IV surfaces for 25 equities/ETFs** → stock-specific VRP, skew, term slope
- E-mini L2 → true depth imbalance at levels 2-5 (public has L1 only)
- Synchronized timestamps across asset classes → intraday lead-lag detection
- **Per-symbol variance swaps (EDRVS)** → clean VRP without jump premium contamination
- **Direct VVIX** via `eqsp_s_.vvix@close` → vol-of-vol without proxy noise

## Direction Feasibility

| Direction | Status |
|-----------|--------|
| HARQ-X + ML residual | Fully enabled (34-symbol panel, 11.3yr) |
| Intraday RV from LOB | E-mini only (single-asset) |
| Multivariate RC + GNNs | Fully enabled (34 symbols + cross-asset) |
| VRP ML trader | Fully enabled (per-symbol variance swaps + RV) |
| HAR panel + VRP/IV hybrid | Fully enabled (per-symbol IV + panel) |
| Per-stock IV predictors | **NEW: Fully enabled** (25 symbols, 35 fields each) |

## Chunk Store Ingestion Patterns

### Timezone Handling (Critical)

Chunk Store returns timestamps in **UTC**. The correct conversion:
```python
df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)
```
**Never** use `tz_localize(TZ)` directly -- that incorrectly treats UTC as Eastern, shifting data by 4-5 hours and losing ~60% of the trading day in EST months (Nov-Mar).

Evidence: Validated on 2020-01-02 (EST date). Raw query returns timestamps starting at 14:30:00 UTC = 09:30 ET. With the bug, only the 14:30-16:00 ET window was captured (1.5 hours instead of 6.5 hours). RV was ~60% too low.

### AggGroupBy Fast Path (fetch_bars)

Server-side aggregation via `processor.AggGroupBy`:
- Returns 78 bars/day (vs ~1.2M ticks) -- 14x faster
- Produces identical RV to corrected tick path (0.00% difference validated 2026-05-14)
- API: `processor.AggGroupBy(groupByOperations=["first(TRDPRC_1)", "max(TRDPRC_1)", "min(TRDPRC_1)", "last(TRDPRC_1)", "sum(TRDVOL_1)", "count(TRDPRC_1)"], interval=300.0)`
- Query window: supply Eastern-localized start/end times; server handles UTC conversion
- Batch multiple days in one call (up to 20 days safely)
- Import: `from pytickclient import processor`

### Mode Tradeoffs (build_rv_panel)

| Mode | Speed | Features | Use When |
|------|-------|----------|----------|
| `bars` (default) | ~1.5s/day | All Layer 0-1 (RV, BPV, RQ, jumps, moments) -- rk=NaN, noise_gap=NaN | Standard ingestion, tournament runs |
| `ticks` (legacy) | ~5-120s/day | All features including RK, noise_gap | Layer 3 microstructure research |

## Marquee ERDVOL — Layer 2 IV Surface Ingestion (verified 2026-05-18)

### Two Datasets (critical distinction)

| Dataset | History | Tenors | Strikes | StrikeRef | Rows/day |
|---------|---------|--------|---------|-----------|----------|
| `EDRVOL_PERCENT_STANDARD` | 2023-05-22+ | 13 (1m-2y) | 28 (0.25-1.5) | `delta`, `forward` | ~507 |
| `EDRVOL_PERCENT` | 2013-01-02+ (full) | 31 (1w-10y) | 49 (mixed) | `delta`, `forward`, `normalized`, `spot` | ~2,852 |

**USE `EDRVOL_PERCENT`** — covers full 2015-2025 RV period. `STANDARD` is too short.

### Strike Semantics (EDRVOL_PERCENT — VERIFIED 2026-05-18)

**Columns returned:** `assetId`, `strikeReference`, `tenor`, `relativeStrike`, `absoluteStrike`, `impliedVolatility`, `updateTime`, `bbid`

**strikeReference values:** `delta`, `forward`, `normalized`, `spot`

**relativeStrike values (49 total):**
- Negative (10): -4.0, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.75, -0.5, **-0.25**
- Zero-to-one (22): 0.0, 0.05, 0.1, ..., 0.95, 0.975, **1.0**
- Above-one (17): 1.025, 1.05, 1.1, ..., 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0

**Layer 2 extraction mapping (for SPX, strikeReference="forward"):**

| Feature Need | Filter | Example IV |
|---|---|---|
| ATM IV (1m) | `relativeStrike=1.0, tenor="1m", strikeReference="forward"` | 0.1110 (11.1%) |
| ATM IV (3m) | `relativeStrike=1.0, tenor="3m", strikeReference="forward"` | verify |
| 25d put IV | `relativeStrike=-0.25, tenor="1m", strikeReference="delta"` | verify delta rows |
| 25d call IV | **NO direct 25d call in delta convention** — use `relativeStrike=1.25, strikeReference="forward"` as proxy | verify |

**CRITICAL:** ATM has 3 rows per day per tenor (from 3 different strikeReferences: forward, normalized, spot). Filter to `strikeReference="forward"` for consistent ATM IV.

### Rate Limits & Query Pattern

- Max 1 month per API call (~60k rows/chunk)
- Query: `Dataset("EDRVOL_PERCENT").get_data(start=..., end=..., bbid="SPX")`
- Requires `GsSession.use()` active
- Total for 10yr: ~120 API calls, ~20 min wall clock

### EDRVS Variance Swap Dataset (alternative VRP source)

`Dataset("EDRVS")` returns fair variance swap levels for SPX:
- **Columns:** `assetId`, `tenor`, `fairVariance`, `fairVolatility`, `updateTime`, `bbid`
- **31 tenors** (same as EDRVOL: 1w through 10y)
- **1 row per tenor per day** (31 rows/day for SPX)
- `fairVolatility` is annualized vol in PERCENTAGE (e.g., 13.57 = 13.57%)
- `fairVariance` is annualized variance (e.g., 184.08 = (13.57)^2)
- **USE FOR VRP:** `VRP = fairVariance_1m - RV_realized * 252 * 10000` (variance swap level incorporates jump risk premium, cleaner than IV^2)

### VVIX — CONFIRMED UNAVAILABLE (exhaustive probe 2026-05-18)

ALL TSDB variants return 500 Internal Server Error:
- `eqpad_.VVIX@close`, `eqpad_VVIX@close`, `eqpad_.VVIX@settle/last/open/high/low`
- `eqpad_VVIX.X@close`, `eqpad_.VVIX.X@close`, `cboe_.VVIX@close`
- `mqd_.VVIX@close` (403 Forbidden — different error, may need entitlement)
- `eqvol_vix@vvix`, `eqvolrt_vix@vvix` (return empty, not error)

**Workaround (CONFIRMED):** Compute realized vol-of-VIX from the working VIX series:
```python
rvol_vix = np.sqrt(252 * np.log(vix / vix.shift(1)).pow(2).rolling(22).mean())
```

**Alternative (from Confluence "Marquee Alert/Signal" page):** The Marquee alert framework uses "Vol-of-Vol" as a category metric. This confirms VVIX is not directly available as a dataset but is computed from VIX option chains. Our realized proxy is the best available path without VIX options data.

### VIX Futures — NO GENERIC CONTINUATION (verified 2026-05-18)

**Working:** Individual contracts by specific symbol (e.g., `eqpad_VXH24@settle`)
**NOT working:** All generic/continuation attempts (VX.001, VXc1, VX1, UX1, etc.)

**Confirmed working contracts (7 rows each for Jan 2-10 2024):**
- `eqpad_VXH24@settle` (Mar24: 15.25-16.16)
- `eqpad_VXJ24@settle` (Apr24: 15.98-16.93)
- `eqpad_VXK24@settle` (May24: 16.35-17.31)
- `eqpad_VXM24@settle` (Jun24: 16.73-17.65)

**Not working (expired by query date):** `eqpad_VXF24@settle`, `eqpad_VXG24@settle`

**Roll logic required:** Must resolve which 3 contracts are "active" for each historical date, then stitch. The existing `_resolve_vx_contracts()` approach is correct but needs to handle the full 10-year history by iterating monthly. Key insight: expired contracts return 500, NOT empty — must catch errors gracefully.

### Additional Datasets Discovered (from Confluence)

| Dataset ID | Name | Use Case |
|---|---|---|
| `EDRVOL_PERCENT_EXPIRY` | IV by Listed Expiry | Exact expiry dates instead of tenor labels |
| `EDRVOL_PERCENT_INTRADAY` | Intraday IV by Tenor | Intraday surface snapshots |
| `EDRVOL_DAILY_V2` | V2 native MDS dataset | Newer format, may have better coverage |
| `chronos_implied_vol_data_eq` | Chronos GCS dataset | Forward ref, strikes 0.5-1.5, tenors 1w/2w/3m, 2020+ |
| `chronos_implied_vol_data_eq_forward` | Chronos forward-only | Same but namespace-separated after bug fix |
