# Plan: Trial-097 GSVIVS Signals — Data Gap Remediation

**Date:** 2026-07-28  
**Triggered by:** Analysis showing 48 of 73 `gsvivs_signals` features are silently NaN due to missing upstream data.  
**Goal:** Wire all missing data ingestion pipelines so that trial-097's `xgboost_enriched` variant trains on the full 73-feature set.

---

## Problem Statement

The `GsvivsSignalsLayer` at `src/volforecast/features/gsvivs_signals.py` gracefully degrades missing columns to NaN via `_series()`. Three upstream data sources were never ingested:

| Gap | Required column(s) | Features affected | Root cause |
|-----|---------------------|-------------------|------------|
| **Credit CDS levels** | `credit_ig_5y`, `credit_hy_5y` | 6 features (Group 9) | `_CREDIT_CDS.parquet` never created; `fetch_credit_cds()` exists but has no CLI caller; TSDB symbols are unconfirmed placeholders |
| **VIX option surface** | `vix_iv_1m_atm`, `vix_iv_1m_25dc`, `vix_iv_1m_5dc` | 18 features (Groups 4+5) | `_VIX_OPTIONS.parquet` never created; `fetch_vix_options()` exists but no CLI caller |
| **SPX deep-OTM strikes** | `iv_1m_5dp`, `iv_3m_25dp`, `iv_3m_5dp` | ~24 features (Groups 7+8 skew TS) | Fields are in `_DEFAULT_FIELDS` but SPX cache has only 15 rows for these columns — cache was built before fields were added and never force-refreshed |

**Additionally:** `VIX_Open` appears in the user's TSDB symbol list but is not used by `gsvivs_signals.py` nor referenced in the layer code. We ignore it (no action needed).

---

## Acceptance Criteria

1. `_CREDIT_CDS.parquet` exists in `data/raw/iv/` with columns `[credit_ig_5y, credit_hy_5y]` and >2500 rows (2015–2026).
2. `_VIX_OPTIONS.parquet` exists in `data/raw/iv/` with columns `[vix_iv_1m_atm, vix_iv_1m_25dc, vix_iv_1m_5dc]` and >2500 rows.
3. `data/raw/iv/SPX.parquet` has >2500 non-null rows for each of `iv_1m_5dp`, `iv_3m_25dp`, `iv_3m_5dp`.
4. All three new ingestion steps are wired to a CLI command so they can be repeated.
5. Tests pass (`./vol test -x -q`).
6. No new dependencies added.

---

## Execution Plan

### Step 1: Probe credit CDS TSDB symbols (subagent)

```yaml
subtask_id: "execute-1"
goal: "Probe TSDB for the correct CDX IG/HY 5Y CDS spread symbols and report which symbol + field works."
file_scope:
  - src/volforecast/data/edrvol.py        # current placeholder symbols
  - src/volforecast/data/tsdb.py          # _get_tsdb_data implementation
  - memory/ref/vol-cli.md                 # ./vol reference
write_scope: []                           # research only — no writes
acceptance_criteria:
  - "Returns the working TSDB symbol string for IG 5Y CDS (or reports 'not available')"
  - "Returns the working TSDB symbol string for HY 5Y CDS (or reports 'not available')"
  - "Provides sample data (5 rows) to confirm units"
memory_refs: []
constraints:
  - "Use ./vol exec for all commands"
  - "Try candidates: midas_.CDXIG5Y@close, cdslevels_CDX.NA.IG.5Y@close, midas_.CDX.NA.IG.5Y@close, cdslevels_CDX.IG.5Y@close"
  - "Try HY equivalents for each"
context_summary: |
  The fetch_credit_cds function in edrvol.py uses placeholder TSDB symbols
  (midas_.CDXIG5Y@close, midas_.CDXHY5Y@close) that have never been tested.
  We need to probe TSDB to find the correct symbols before wiring ingestion.
depends_on: []
```

### Step 2: Probe VIX option surface TSDB RIC (subagent)

```yaml
subtask_id: "execute-2"
goal: "Confirm edrvol_vix@{1matms,1m25dc,1m5dc} symbols work and return data."
file_scope:
  - src/volforecast/data/edrvol.py        # _VIX_OPTION_FIELD_MAP, fetch_vix_options
  - src/volforecast/data/tsdb.py
write_scope: []
acceptance_criteria:
  - "Returns sample of 5 rows for each of the 3 fields (or reports which fail)"
  - "Confirms correct value scale (vol points vs decimal)"
memory_refs: []
constraints:
  - "Use ./vol exec for all commands"
  - "Fetch 2024-01-02 to 2024-01-10 range as test"
context_summary: |
  fetch_vix_options() in edrvol.py builds symbols edrvol_vix@{1matms,1m25dc,1m5dc}.
  The RIC "vix" was marked verified 2026-07-28 in a comment, but the function
  has never been called end-to-end. We confirm it works before building the
  ingestion CLI.
depends_on: []
```

### Step 3: Wire credit CDS ingestion into `ingest-edrvol` CLI (subagent)

```yaml
subtask_id: "execute-3"
goal: "Add credit CDS ingestion step to ingest_edrvol.py CLI, calling fetch_credit_cds() and saving via save_iv_cache('_CREDIT_CDS', df). Update TSDB symbols per Step 1 findings."
file_scope:
  - src/volforecast/cli/ingest_edrvol.py  # existing pattern (VVIX, VIX, OVX blocks)
  - src/volforecast/data/edrvol.py        # fetch_credit_cds, _CREDIT_IG_SYMBOL, _CREDIT_HY_SYMBOL
  - src/tests/unit/test_gsvivs_signals.py # understand test fixtures
write_scope:
  - src/volforecast/cli/ingest_edrvol.py  # add CDS block
  - src/volforecast/data/edrvol.py        # update TSDB symbol constants
  - src/tests/unit/test_ingest_credit_cds.py  # new test (TDD)
acceptance_criteria:
  - "New test file exists with a test that mocks TSDB and asserts save_iv_cache is called with '_CREDIT_CDS'"
  - "ingest_edrvol.py run() fetches and caches _CREDIT_CDS.parquet in the same pattern as VVIX/VIX/OVX"
  - "_CREDIT_IG_SYMBOL and _CREDIT_HY_SYMBOL updated to confirmed symbols from Step 1"
  - "total_steps counter incremented by 1"
  - "./vol test -x -q -k credit passes"
memory_refs: []
constraints:
  - "TDD: write failing test first"
  - "Follow existing pattern (cache check → fetch → save) exactly"
  - "If Step 1 found no working symbols, use best-guess and add a clear TODO + warning log"
context_summary: |
  The ingest_edrvol.py CLI fetches multiple market-wide data in sequence: VVIX, VIX, OVX,
  treasury yields, IV dispersion, GSVIVS01. We add a credit CDS block in the same style.
  fetch_credit_cds() already exists in edrvol.py. We just need to call it and persist output.
depends_on: ["execute-1"]
```

### Step 4: Wire VIX options ingestion into `ingest-edrvol` CLI (subagent)

```yaml
subtask_id: "execute-4"
goal: "Add VIX options ingestion step to ingest_edrvol.py CLI, calling fetch_vix_options() and saving via save_iv_cache('_VIX_OPTIONS', df)."
file_scope:
  - src/volforecast/cli/ingest_edrvol.py  # existing pattern
  - src/volforecast/data/edrvol.py        # fetch_vix_options
write_scope:
  - src/volforecast/cli/ingest_edrvol.py  # add VIX options block
  - src/tests/unit/test_ingest_vix_options.py  # new test (TDD)
acceptance_criteria:
  - "New test file mocks TSDB and asserts save_iv_cache is called with '_VIX_OPTIONS'"
  - "ingest_edrvol.py run() fetches and caches _VIX_OPTIONS.parquet"
  - "total_steps counter incremented by 1"
  - "./vol test -x -q -k vix_options passes"
memory_refs: []
constraints:
  - "TDD: write failing test first"
  - "Insert AFTER the existing VVIX block (natural grouping: VIX-related caches together)"
context_summary: |
  fetch_vix_options() already exists in edrvol.py and returns a DataFrame with columns
  [vix_iv_1m_atm, vix_iv_1m_25dc, vix_iv_1m_5dc]. The IVSurfaceLayer already loads
  _VIX_OPTIONS.parquet if it exists. We just need to wire the fetch → save in the CLI.
depends_on: ["execute-2"]
```

### Step 5: Force-refresh SPX IV cache to backfill deep-OTM strikes (inline)

```yaml
subtask_id: "execute-5"
goal: "Delete and re-fetch SPX IV cache so iv_1m_5dp, iv_3m_25dp, iv_3m_5dp have full history."
file_scope: []
write_scope: []  # runtime data only (parquet caches)
acceptance_criteria:
  - "After re-fetch, SPX.parquet has >2500 non-null rows for iv_1m_5dp, iv_3m_25dp, iv_3m_5dp"
memory_refs: []
constraints:
  - "This is a DATA operation, not a code change"
  - "Use the existing ingest-edrvol CLI with --symbols SPX --force"
context_summary: |
  _DEFAULT_FIELDS in edrvol.py already includes 1m5dp, 3m25dp, 3m5dp. The SPX cache
  was built before these were added. A --force re-fetch will pull all 8 fields for
  the full date range, populating the missing columns.
depends_on: []
```

### Step 6: Integration verification (inline)

```yaml
subtask_id: "execute-6"
goal: "Run a quick feature-build smoke test confirming all 73 gsvivs_signals features produce non-NaN data."
file_scope:
  - src/volforecast/features/gsvivs_signals.py
  - src/tests/unit/test_gsvivs_signals.py
write_scope: []
acceptance_criteria:
  - "A one-off script loads SPX daily_data from IVSurfaceLayer, calls GsvivsSignalsLayer.compute(), and asserts <10% NaN across all 73 columns"
  - "All unit tests pass"
memory_refs: []
constraints:
  - "Run AFTER Steps 3-5 complete and data is ingested"
context_summary: |
  After all data gaps are filled, we verify end-to-end that the feature layer
  produces usable data rather than NaN columns.
depends_on: ["execute-3", "execute-4", "execute-5"]
```

---

## Dependency Graph

```
Step 1 (probe credit) ──┐
                         ├── Step 3 (wire credit CLI)──┐
                         │                              │
Step 2 (probe VIX opt) ──┤                              ├── Step 6 (integration verify)
                         ├── Step 4 (wire VIX opt CLI)──┤
                         │                              │
Step 5 (force SPX) ──────┴──────────────────────────────┘
```

**Parallelism:** Steps 1, 2, 5 can run in parallel → then Steps 3, 4 in parallel → Step 6 last.

---

## Ingestion Commands (post-implementation)

After Steps 3 and 4 are implemented, run the following commands to populate all missing data:

```bash
# 1. Force-refresh SPX IV cache (backfills iv_1m_5dp, iv_3m_25dp, iv_3m_5dp)
./vol exec python -m volforecast.cli.ingest_edrvol --symbols SPX --force --start 2013-01-02 --end 2026-07-28

# 2. Ingest VIX options surface (_VIX_OPTIONS.parquet)
#    (This is now part of ingest-edrvol after Step 4 lands)
./vol exec python -m volforecast.cli.ingest_edrvol --force --start 2013-01-02 --end 2026-07-28

# 3. Ingest credit CDS levels (_CREDIT_CDS.parquet)
#    (Also part of ingest-edrvol after Step 3 lands)
#    The --force flag above covers it, OR run targeted:
./vol exec python -m volforecast.cli.ingest_edrvol --force --start 2015-01-02 --end 2026-07-28

# Combined single command (fetches everything including the new steps):
./vol exec python -m volforecast.cli.ingest_edrvol --force --start 2013-01-02 --end 2026-07-28
```

**Alternatively**, if the credit/VIX-options steps are wired as flags or separate subcommands, the calls would be:

```bash
# Force-refresh all EDRVOL data (per-symbol + market-wide caches)
./vol shell -m volforecast.cli.ingest_edrvol -- --force --start 2013-01-02 --end 2026-07-28
```

After ingestion completes, verify with:

```bash
# Confirm caches exist and are populated
./vol exec python -c "
import pandas as pd
from volforecast.utils.paths import iv_cache_dir

# Credit CDS
cds = pd.read_parquet(iv_cache_dir() / '_CREDIT_CDS.parquet')
print(f'Credit CDS: {len(cds)} rows, cols={list(cds.columns)}')
print(cds.notna().sum())

# VIX Options
vix_opt = pd.read_parquet(iv_cache_dir() / '_VIX_OPTIONS.parquet')
print(f'VIX Options: {len(vix_opt)} rows, cols={list(vix_opt.columns)}')
print(vix_opt.notna().sum())

# SPX deep-OTM
spx = pd.read_parquet(iv_cache_dir() / 'SPX.parquet')
print(f'SPX iv_1m_5dp non-null: {spx[\"iv_1m_5dp\"].notna().sum()}')
print(f'SPX iv_3m_25dp non-null: {spx[\"iv_3m_25dp\"].notna().sum()}')
print(f'SPX iv_3m_5dp non-null: {spx[\"iv_3m_5dp\"].notna().sum()}')
"
```

---

## Risk Notes

1. **Credit CDS symbols may not exist in TSDB.** If Step 1 finds no working symbol, we either:
   - Use the `cross_asset/credit.parquet` data (which has `credit_vol_cdx` — CDX implied vol from Marquee, ~2528 rows). This is a vol measure, not a spread level, so pct_change semantics differ. Would need a small column mapping in `IVSurfaceLayer`.
   - Or accept credit features as unavailable and document the gap.

2. **VIX option 5-delta call** (`1m5dc`) is an unusual strike. TSDB may not have it. If unavailable, the VIX 25d-5d skew features (4 of 73) will remain NaN. Acceptable — the ATM and 25d features (14 of 18) are higher value.

3. **Trial-097 results will change** after data is populated. The `xgboost_enriched` model may perform differently with 73 real features vs ~25 real + 48 NaN. A full tournament re-run is needed.

---

## Post-Execution

After all steps complete, re-run trial-097 tournament to get a fair A/B comparison:

```bash
./vol exec python -m volforecast.cli.forecast --config workspace/configs/trial_097_gsvivs_signals.yaml --force
```
