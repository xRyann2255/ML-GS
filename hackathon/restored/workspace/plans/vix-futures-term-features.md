# Plan: VIX Futures Term Slope & Curvature Features

**Created:** 2026-07-07
**Status:** PLANNED
**Priority:** P2 (from implied-vol.md gap list)

---

## Brainstorm: What We Have vs What We Need

### Already Have
- `fetch_vix_futures()` in `tsdb.py` — fetches VX settle prices from TSDB
- `_resolve_vx_contracts(ref_date, n)` — resolves contract symbols (VX + monthCode + YY)
- TSDB pattern confirmed: `eqpad_VX{monthCode}{YY}@settle` (e.g., `eqpad_VXH24@settle`)
- VIX spot via `eqpad_.VIX@close` (already in IVSurfaceLayer as `vix` column)
- IV-based term slopes already shipped: `iv_term_slope_d` (3m-1m), `iv_term_slope_1w1m_d`, `iv_term_slope_0dte1w_d`

### The Blocker (from data-access.md)
- **No generic continuation symbols** — `VXc1`, `VX.001`, `UX1` all fail
- Must use explicit monthly contracts and stitch them ourselves
- **Expired contracts return HTTP 500**, not empty — must handle gracefully
- Current `fetch_vix_futures()` uses a single midpoint, only works for short date ranges

### What We Need to Build
1. **Rolling engine**: For each historical date, determine which contract is VX1/VX2/VX3
2. **Ingestion + cache**: Fetch all required monthly contracts, stitch, cache as parquet
3. **Features**: `vix_term_slope`, `vix_term_curvature`, `vix_basis` (+ rolling variants)
4. **Integration**: Wire into `IVSurfaceLayer` → `OptionsLayer` pipeline

### Feature Definitions (Literature)

| Feature | Formula | Interpretation |
|---------|---------|----------------|
| `vix_term_slope_d` | VX2 - VX1 | Contango (+) = normal, backwardation (-) = stress |
| `vix_term_curvature_d` | VX3 - 2*VX2 + VX1 | Convexity of term structure |
| `vix_basis_d` | VX1 - VIX_spot | Futures premium over spot (carry signal) |
| `vix_term_slope_w` | 5d rolling mean of slope | Smoothed regime signal |
| `vix_term_curvature_w` | 5d rolling mean of curvature | Smoothed curvature |
| `vix_basis_w` | 5d rolling mean of basis | Smoothed basis |

**Why these matter for vol forecasting:**
- VIX backwardation (negative slope) precedes/accompanies vol spikes — leading indicator
- VIX basis = pure carry signal; high basis → mean-reversion pressure on VIX
- Curvature measures whether stress is concentrated at front-end (negative curvature during stress unwind)
- These are DISTINCT from IV term slopes which capture options surface shape, not futures curve shape

---

## Acceptance Criteria

1. `data/raw/iv/_VIX_FUTURES.parquet` cached with columns `VX1`, `VX2`, `VX3` indexed by date (2015–present)
2. Roll logic produces continuous series: no gaps at month boundaries, no look-ahead in contract selection
3. `IVSurfaceLayer` loads VIX futures cache and provides `vx1`, `vx2`, `vx3` columns to daily_data
4. `OptionsLayer` computes `vix_term_slope_d`, `vix_term_slope_w`, `vix_term_curvature_d`, `vix_term_curvature_w`, `vix_basis_d`, `vix_basis_w`
5. All features pass causality check: shift(1) not required (VX settle is EOD, same as other features)
6. Unit tests: roll logic (boundary cases), feature computation (known values), integration (full pipeline)
7. `./vol test -k vix_futures` passes

---

## Implementation Plan

### Step 1: VIX Futures Roll Calendar & Ingestion Module

**Execution mode:** `subagent`

```yaml
subtask_id: "execute-1"
goal: "Build VIX futures rolling engine and data ingestion that produces continuous VX1/VX2/VX3 parquet"
file_scope:
  - src/volforecast/data/tsdb.py  # existing fetch_vix_futures, _resolve_vx_contracts
  - src/volforecast/data/edrvol.py  # load_iv_cache pattern to replicate
  - src/volforecast/utils/paths.py  # iv_cache_dir()
  - memory/research/data-access.md  # VIX futures TSDB specifics
write_scope:
  - src/volforecast/data/vix_futures.py  # NEW: rolling engine + fetch + cache
  - src/tests/unit/test_vix_futures.py  # NEW: unit tests
acceptance_criteria:
  - "vix_futures_roll_calendar(start_date, end_date) returns DataFrame with columns [date, VX1_symbol, VX2_symbol, VX3_symbol] mapping each date to active contracts"
  - "Roll date = VIX futures settlement (Wednesday 30 days before 3rd Friday of next month)"
  - "fetch_vix_futures_continuous(start, end) iterates monthly windows, fetches each active contract, stitches into VX1/VX2/VX3 columns"
  - "Graceful handling of 500 errors from expired contracts (skip, log, continue)"
  - "save_vix_futures_cache() writes to data/raw/iv/_VIX_FUTURES.parquet"
  - "load_vix_futures_cache() reads cache, returns DataFrame or None"
  - "Unit tests cover: roll boundary (contract switch), expired contract error handling, calendar correctness for known dates"
memory_refs:
  - memory/research/data-access.md  # TSDB patterns, known-working contracts
  - memory/research/implied-vol.md  # VIX futures section
constraints:
  - "NO generic continuation symbols — must use explicit eqpad_VX{code}{YY}@settle"
  - "Roll calendar must be deterministic from dates alone (no network calls)"
  - "VIX settlement = 3rd Wednesday of each month (special open settlement)"
  - "Contract months: every month (VIX futures are monthly)"
  - "Keep fetch logic separate from roll logic for testability"
context_summary: "VIX futures have no generic continuation in TSDB. Individual contracts work (eqpad_VXH24@settle) but expire (return 500). Need to build a roll calendar that identifies which 3 contracts are front/second/third for each date, then fetch and stitch into continuous series. The existing _resolve_vx_contracts() in tsdb.py has the month-code logic but uses a single midpoint — need to iterate monthly."
depends_on: []
```

### Step 2: CLI Command for VIX Futures Ingestion

**Execution mode:** `subagent`

```yaml
subtask_id: "execute-2"
goal: "Add 'vol ingest-vix-futures' CLI command that runs the ingestion and caches the parquet"
file_scope:
  - src/volforecast/cli/ingest_edrvs.py  # pattern to follow for CLI command
  - src/volforecast/__main__.py  # command dispatch
  - src/volforecast/data/vix_futures.py  # from step 1
write_scope:
  - src/volforecast/cli/ingest_vix_futures.py  # NEW: CLI entry point
  - src/volforecast/__main__.py  # register new command
acceptance_criteria:
  - "'vol ingest-vix-futures' runs the full fetch+stitch+cache pipeline"
  - "Supports --start-date and --end-date flags (defaults: 2015-01-01 to today)"
  - "Prints progress (fetching month X of Y) since this will be many TSDB calls"
  - "Incremental mode: if cache exists, only fetches from last cached date forward"
memory_refs: []
constraints:
  - "Follow existing CLI patterns (see ingest_edrvs.py)"
  - "Must use ./vol exec for any manual testing"
context_summary: "Simple CLI wrapper around the ingestion module from step 1. Pattern matches existing ingest-edrvs command. Incremental fetch avoids re-downloading the full history on each run."
depends_on: ["execute-1"]
```

### Step 3: IVSurfaceLayer Integration

**Execution mode:** `subagent`

```yaml
subtask_id: "execute-3"
goal: "Wire VIX futures cache into IVSurfaceLayer so vx1/vx2/vx3 columns appear in daily_data"
file_scope:
  - src/volforecast/features/iv_surface.py  # where to add loading
  - src/volforecast/data/vix_futures.py  # load_vix_futures_cache()
  - src/volforecast/features/options.py  # downstream consumer (read-only, understand interface)
write_scope:
  - src/volforecast/features/iv_surface.py  # add VIX futures loading block
  - src/tests/unit/test_iv_surface.py  # add test for VIX futures columns
acceptance_criteria:
  - "IVSurfaceLayer.compute() adds vx1, vx2, vx3 columns to result when cache exists"
  - "Graceful degradation: if _VIX_FUTURES.parquet missing, no columns added, no error"
  - "Columns reindexed to daily_data.index (same pattern as VVIX loading)"
  - "Unit test mocks cache load and verifies columns appear in output"
memory_refs: []
constraints:
  - "No shift needed: VX settle is EOD, same observation time as VIX spot and rv"
  - "Market-wide signal (not per-symbol) — same pattern as VVIX/OVX loading"
context_summary: "IVSurfaceLayer already loads several market-wide caches (_VVIX, _VIX, _OVX, _MARKET, _TREASURY_YIELDS). Adding _VIX_FUTURES follows the exact same pattern: load parquet, reindex, assign columns."
depends_on: ["execute-1"]
```

### Step 4: OptionsLayer Feature Computation

**Execution mode:** `subagent`

```yaml
subtask_id: "execute-4"
goal: "Add vix_term_slope, vix_term_curvature, vix_basis features to OptionsLayer"
file_scope:
  - src/volforecast/features/options.py  # target file (read existing pattern)
  - src/volforecast/features/iv_surface.py  # understand what columns it provides
write_scope:
  - src/volforecast/features/options.py  # add VIX futures feature block
  - src/tests/unit/test_options.py  # add tests for new features
acceptance_criteria:
  - "OptionsLayer._compute_from_daily_data() produces: vix_term_slope_d, vix_term_slope_w, vix_term_curvature_d, vix_term_curvature_w, vix_basis_d, vix_basis_w"
  - "slope = vx2 - vx1, curvature = vx3 - 2*vx2 + vx1, basis = vx1 - vix"
  - "Weekly variants = 5d rolling mean of daily"
  - "Features only computed when vx1/vx2/vx3 columns exist in daily_data (graceful skip)"
  - "Unit test with synthetic data verifies arithmetic correctness"
  - "Docstring updated to list new output columns"
memory_refs:
  - memory/research/implied-vol.md  # feature definitions
constraints:
  - "Guard with 'if vx1 in daily_data.columns' — feature is optional"
  - "Follow existing pattern: compute daily, then rolling(5).mean() for weekly"
  - "No monthly variant needed (VIX futures curve is a short-term signal)"
context_summary: "OptionsLayer already computes IV term slopes (3m-1m). VIX futures term slope is conceptually similar but uses actual tradeable futures prices, not IV model output. The signal is distinct: IV slope = options surface shape; VIX futures slope = term premium in volatility derivatives market."
depends_on: ["execute-3"]
```

### Step 5: Integration Test & Smoke Run

**Execution mode:** `inline`

```yaml
subtask_id: "execute-5"
goal: "Run full test suite and verify features appear end-to-end"
acceptance_criteria:
  - "./vol test -k vix_futures passes"
  - "./vol test -k test_options passes (no regression)"
  - "./vol test -k test_iv_surface passes (no regression)"
depends_on: ["execute-4"]
```

---

## Dependency Graph

```
execute-1 (roll engine + data module)
├─→ execute-2 (CLI command) [sequential after 1]
├─→ execute-3 (IVSurfaceLayer integration) [parallel with 2]
│     └─→ execute-4 (OptionsLayer features) [sequential after 3]
│           └─→ execute-5 (integration test) [sequential after 4]
```

**Parallelism:** Steps 2 and 3 can run in parallel after Step 1 completes.

---

## Risk & Mitigations

| Risk | Mitigation |
|------|------------|
| Expired contracts return 500, losing early history | Catch per-contract errors; log gaps; backfill with VIX spot + historical contango estimate if needed |
| TSDB rate limits on 120+ monthly contract fetches | Batch by year, add sleep between batches, cache aggressively |
| Roll date calculation slightly off | Unit test against known VIX settlement dates (CBOE publishes calendar) |
| Data starts later than 2015 for older contracts | Accept shorter history; VIX futures have been liquid since ~2007, TSDB may have 2015+ |
| Feature adds noise at h=1 (VIX futures more relevant at weekly+) | Include in tournament; QLIKE will tell us; can gate by horizon in config |

---

## Open Questions (non-blocking)

1. **Roll method**: Simple "switch at expiry" or "weighted blend in final N days"? Start with hard switch (simpler, no look-ahead). Can upgrade to blend later if gaps appear.
2. **Additional features**: `vix_carry = (VX1 - VIX) / days_to_expiry` (annualized carry). Defer to follow-up unless trivial to add in Step 4.
3. **VX4+**: Only need VX1-VX3 for slope/curvature. More contracts = diminishing returns + more TSDB calls.
