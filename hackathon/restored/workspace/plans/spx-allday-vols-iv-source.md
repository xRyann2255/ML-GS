# Plan: SPXAllDayVols as IV Source (Strike-Level 09:10 ET Extraction)

## Clarified Data Requirement

SPXAllDayVols is a **vol mark surface** in ChunkStore — it contains IV readings across many strikes throughout the day. We need:

- **Time:** 09:10 ET snapshot each day (the GSVIVS01 decision time)
- **Strikes:** The specific ~7–25 strikes that were actually used in that day's variance swap strip (from `output.json` via `parse_day_opening_legs`)
- **Output:** Per-strike IV at 09:10 → compute Kvar using the same CBOE-style formula as `compute_kvar_from_legs`, but with **mark vols** instead of execution prices

This gives us a "morning mark Kvar" — the fair variance swap level at signal decision time, without execution slippage. This is the ideal IV source for the signal.

---

## Acceptance Criteria

1. `vol ingest-allday` fetches SPXAllDayVols at 09:10 ET for each trading day, extracting IV for the strikes in that day's output.json strip
2. Computes a daily Kvar (vol %) from mark IVs + output.json strikes using CBOE formula
3. Caches result to `data/raw/iv/SPX_allday_vols.parquet` (date-indexed, columns: `kvar_vol_pct`, `n_strikes`, `forward`, plus per-strike raw data)
4. New IV source key `spx_allday_vols` registered everywhere, made default
5. `vol kvar` displays the new source
6. Tests pass

---

## Steps

### Step 1: Data Probe + Strike Extraction Utility `[subagent]`

```yaml
subtask_id: "execute-1"
goal: "Probe SPXAllDayVols schema via ChunkStore, build utility to extract date→strikes from output.json"
file_scope:
  - src/volforecast/data/gsvivs_kvar.py          # parse_day_opening_legs, extract_all_exec_kvar
  - src/volforecast/data/chunk_store.py           # Session management patterns
  - src/volforecast/constants.py                  # TZ
  - data/external/output.json                     # Strike source (read only)
  - memory/ref/python-chunk.md                    # ChunkStore API
write_scope:
  - src/volforecast/data/spx_allday_vols.py       # NEW: fetch + parse + cache
  - src/volforecast/utils/paths.py                # ADD: allday_vols_cache_path()
  - workspace/tmp/allday_probe_output.txt         # Probe results (ephemeral)
acceptance_criteria:
  - "extract_daily_strike_map(json_path) returns dict[date, list[dict]] — per-day strike+option_type from output.json"
  - "fetch_allday_vols_snapshot(date, strikes) queries SPXAllDayVols at 09:10 ET for given strikes and returns per-strike IV"
  - "compute_mark_kvar(strike_ivs, forward, T, r) computes Kvar from mark IVs (same CBOE formula as compute_kvar_from_legs but using IV marks instead of exec prices)"
  - "Probe script confirms SPXAllDayVols schema: what columns exist, how strikes are identified, what 'IV' field to use"
memory_refs:
  - memory/ref/python-chunk.md
constraints:
  - "Use libpytkdb.chunk_query with chunk_db='_CFG Arctic NYC Eq Flow::nyc_eq_vol_vmrk', symbol='SPXAllDayVols'"
  - "Query window: 09:10:00 ET ± small buffer (e.g. 09:09:30 to 09:10:30) to get nearest mark"
  - "Reuse parse_day_opening_legs from gsvivs_kvar.py for strike list extraction — wrap it, don't duplicate"
  - "Forward: extract from output.json same-day (already available via _find_forward_for_day)"
  - "TDD: write failing test first for the strike extraction utility"
context_summary: "SPXAllDayVols is a vol mark surface in ChunkStore (nyc_eq_vol_vmrk library). It contains IV readings at various strikes/expiries throughout the trading day. We need the 09:10 ET reading for the specific strikes that output.json says were used in that day's variance swap. The output.json parsing already exists in gsvivs_kvar.py — parse_day_opening_legs returns [{strike, option_type, exec_price, quantity}] per day. We need to build: (1) date→strikes mapping from output.json, (2) ChunkStore query for those strikes at 09:10, (3) Kvar computation from mark IVs."
depends_on: []
```

---

### Step 2: Batch Ingestion + Cache `[subagent]`

```yaml
subtask_id: "execute-2"
goal: "Build the full ingestion loop: for each day in output.json, query SPXAllDayVols at 09:10 for that day's strikes, compute mark Kvar, cache result"
file_scope:
  - src/volforecast/data/spx_allday_vols.py       # From execute-1
  - src/volforecast/cli/ingest_edrvs.py           # CLI pattern reference
  - src/volforecast/__main__.py                   # Registration point
  - vol                                           # Shell dispatch
write_scope:
  - src/volforecast/cli/ingest_allday.py          # NEW: CLI command
  - src/volforecast/__main__.py                   # ADD: register
  - vol                                           # ADD: dispatch case
acceptance_criteria:
  - "vol ingest-allday loops through all output.json dates, queries ChunkStore per day, computes mark Kvar"
  - "Incremental: skips dates already in cache unless --force"
  - "Supports --start, --end, --force flags"
  - "Saves to data/raw/iv/SPX_allday_vols.parquet with columns: kvar_vol_pct, n_strikes, forward, kvar_variance_ann"
  - "Handles missing data gracefully (log warning, skip day)"
  - "Progress display (date counter)"
  - "TDD: write failing test first"
memory_refs: []
constraints:
  - "Day-at-a-time ChunkStore queries (cannot span multiple days in one call for this store)"
  - "If a strike is not found in the 09:10 snapshot, log warning and use available strikes"
  - "Match forward from output.json for that day (needed for Kvar formula)"
  - "Follow ingest_edrvs.py register/handle/run pattern"
context_summary: "The ingestion loop iterates output.json days, extracts each day's strike list, queries SPXAllDayVols at 09:10 ET for those strikes, computes Kvar from mark IVs using the CBOE formula, and caches the daily series. This is conceptually: exec_kvar (from actual fills) vs mark_kvar (from 09:10 vol marks) — same formula, different inputs."
depends_on: ["execute-1"]
```

---

### Step 3: Kvar Table + Registry Integration `[subagent]`

```yaml
subtask_id: "execute-3"
goal: "Register spx_allday_vols as IV source, integrate into vol kvar display, make default"
file_scope:
  - src/volforecast/evaluation/kvar_table.py      # load_iv_variants
  - src/volforecast/evaluation/gsvivs.py          # IV_SOURCE_REGISTRY
  - src/volforecast/config.py                     # _VALID_IV_SOURCES, default
  - src/volforecast/data/spx_allday_vols.py       # Cache loader
  - workspace/configs/_CANONICAL_EXAMPLE.yaml     # Config docs
write_scope:
  - src/volforecast/evaluation/kvar_table.py      # ADD variant
  - src/volforecast/evaluation/gsvivs.py          # ADD to registry
  - src/volforecast/config.py                     # ADD to valid set, change default
  - workspace/configs/_CANONICAL_EXAMPLE.yaml     # Document new option
acceptance_criteria:
  - "'spx_allday_vols' in IV_SOURCE_REGISTRY with (label='SPX AllDay Mark Kvar (09:10)', column='iv_allday_kvar', is_calendar_ann=True)"
  - "'spx_allday_vols' in _VALID_IV_SOURCES"
  - "Default changes from ['exec_kvar'] to ['spx_allday_vols']"
  - "load_iv_variants() includes AllDay variant FIRST when cache exists"
  - "vol kvar displays the new variant row"
  - "TDD: write failing test first"
memory_refs: []
constraints:
  - "Additive — do NOT remove existing sources"
  - "Variant placed first in load_iv_variants() (best source)"
  - "Label clearly distinguishes from Exec Kvar: 'SPX AllDay Mark Kvar (09:10)'"
context_summary: "Three integration points: (1) IV_SOURCE_REGISTRY in gsvivs.py for tournament pipeline, (2) _VALID_IV_SOURCES in config.py for YAML validation + default, (3) load_iv_variants() in kvar_table.py for vol kvar display. All are simple additive changes."
depends_on: ["execute-1", "execute-2"]
```

---

### Step 4: Tests `[subagent]`

```yaml
subtask_id: "execute-4"
goal: "Comprehensive tests for strike extraction, mark Kvar computation, CLI, and registry"
file_scope:
  - src/tests/                                    # Existing test patterns
  - src/tests/unit/test_gsvivs_kvar.py            # Reference for output.json mock patterns
  - src/volforecast/data/spx_allday_vols.py       # Module under test
  - src/volforecast/cli/ingest_allday.py          # CLI under test
  - src/volforecast/evaluation/gsvivs.py          # Registry under test
  - src/volforecast/config.py                     # Config under test
write_scope:
  - src/tests/unit/test_spx_allday_vols.py        # NEW
acceptance_criteria:
  - "Test extract_daily_strike_map returns correct strikes per day (mock output.json)"
  - "Test compute_mark_kvar produces expected Kvar from synthetic IV marks"
  - "Test load cache returns None when missing, DataFrame when present"
  - "Test 'spx_allday_vols' resolves in resolve_iv_sources()"
  - "Test new default: _parse_gsvivs_iv_sources(None) == ['spx_allday_vols']"
  - "All existing tests still pass"
memory_refs: []
constraints:
  - "Mock ChunkStore calls — no network"
  - "Use tmp_path for cache file tests"
  - "Mock output.json with minimal 2-day fixture"
context_summary: "Tests validate: (1) strike extraction from output.json, (2) mark Kvar formula correctness, (3) cache I/O, (4) registry resolution, (5) config default change. Mock all external data sources."
depends_on: ["execute-1", "execute-2", "execute-3"]
```

---

## Execution Order

```
Phase 1: execute-1 (data probe + strike extraction + fetch/compute logic)
Phase 2: execute-2 (CLI ingestion command — needs execute-1)
Phase 3: execute-3 (registry + kvar integration — needs execute-1, execute-2)
Phase 4: execute-4 (tests — needs all above)
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Query at 09:10 ET (not close) | GSVIVS01 makes its signal decision at ~09:10 ET — this is the mark before execution |
| Use output.json for strike list | These are the exact strikes in that day's var swap strip — no guesswork |
| Reuse `compute_kvar_from_legs` formula | Same CBOE variance swap formula, just with mark IVs → option prices via BS instead of execution fills |
| One ChunkStore query per day | Store is intraday tick-level; can't span days efficiently |
| Mark Kvar vs Exec Kvar distinction | Mark Kvar = theoretical fair value at decision time; Exec Kvar = actual fills including slippage |

## Open Question (resolved during execute-1 probe)

The probe in execute-1 must answer: **How does SPXAllDayVols encode strikes?** Possible schemas:
- One row per timestamp×strike (long format) → filter by strike ∈ day's strip
- Columns per strike (wide format) → select columns by strike value
- A vol surface with moneyness/delta parameterization → map absolute strikes to moneyness

The probe query at 09:10 on a recent date will reveal this. The aggregation logic adapts accordingly.
