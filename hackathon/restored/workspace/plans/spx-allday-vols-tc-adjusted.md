# Plan: `spx_allday_vols_tc` — Mark Kvar with Rolling TC Adjustment

## Background

The existing `spx_allday_vols` IV source computes the gross (pre-friction) mark Kvar at 09:10 ET. The `exec_kvar` source is the true fill with all transaction costs. The difference (mark − exec) is the realized TC drag — mean 0.37 vol%, std 0.12 vol%, always positive.

This plan adds a new IV source that estimates the TC drag using a trailing 20-day rolling mean of the realized vol-% gap, then subtracts it from the mark Kvar. This gives a "what you'd actually capture" estimate without requiring forward-looking TC knowledge.

## Formula

$$\hat{d}_t = \frac{1}{20}\sum_{i=1}^{20}(\text{mark}_{t-i} - \text{exec}_{t-i})$$

$$\text{iv\_allday\_kvar\_tc}_t = \text{mark}_t - \hat{d}_t$$

Properties:
- Fully causal (only uses past data, no look-ahead)
- First 20 days are NaN (insufficient history)
- Adapts to regime changes in TC (wider spreads in high-vol periods)

## Design Decision

**Compute at load time, not ingest time.** Both `allday_cache` and `exec_kvar_cache` already exist. The TC-adjusted series is computed when `gsvivs.py` loads IV data. No new parquet file, no new CLI command.

---

## Acceptance Criteria

1. `spx_allday_vols_tc` is a valid IV source key in config YAML
2. Dashboard shows "SPX AllDay TC-adj Kvar (09:10)" with selector button when listed in `gsvivs_iv_sources`
3. The series equals `allday_mark − rolling_mean_20(allday_mark − exec_kvar)` with proper alignment
4. First 20 days of the series are NaN (rolling window warmup)
5. All existing tests pass unchanged
6. New unit tests verify the computation logic

---

## Steps

### Step 1: Registry + Config + Load Logic `[subagent]`

```yaml
subtask_id: "execute-1"
goal: "Register spx_allday_vols_tc as a new IV source and compute the TC-adjusted series at load time in gsvivs.py"
file_scope:
  - src/volforecast/evaluation/gsvivs.py          # IV_SOURCE_REGISTRY, compute_gsvivs_stats, load logic
  - src/volforecast/config.py                     # _VALID_IV_SOURCES
  - src/volforecast/data/spx_allday_vols.py       # load_allday_cache
  - src/volforecast/data/edrvol.py                # load_exec_kvar_cache
  - workspace/configs/_CANONICAL_EXAMPLE.yaml     # Config documentation
write_scope:
  - src/volforecast/evaluation/gsvivs.py          # ADD registry entry + load logic
  - src/volforecast/config.py                     # ADD to _VALID_IV_SOURCES
  - workspace/configs/_CANONICAL_EXAMPLE.yaml     # Document new option
acceptance_criteria:
  - "'spx_allday_vols_tc' in IV_SOURCE_REGISTRY with label='SPX AllDay TC-adj Kvar (09:10)', column='iv_allday_kvar_tc', is_calendar_ann=True"
  - "'spx_allday_vols_tc' in _VALID_IV_SOURCES"
  - "compute_gsvivs_stats loads both allday and exec_kvar caches, computes rolling_mean(allday - exec, window=20), subtracts from allday, stores as iv_allday_kvar_tc"
  - "First 20 days of iv_allday_kvar_tc are NaN (min_periods=20 on rolling)"
  - "When allday cache OR exec_kvar cache is missing, iv_allday_kvar_tc is all-NaN (graceful degradation)"
  - "Existing tests pass without modification"
memory_refs: []
constraints:
  - "Do NOT modify the existing spx_allday_vols load logic — it must continue to produce iv_allday_kvar unchanged"
  - "Use pandas rolling(20, min_periods=20).mean() for the TC estimate"
  - "The rolling mean is computed on the DIFFERENCE series (mark - exec), not on exec directly"
  - "Align both series on common dates before computing the difference"
  - "TDD: write failing test first for the TC-adjustment computation"
context_summary: |
  The project has an IV source registry in gsvivs.py mapping config keys to (label, column, is_calendar_ann).
  Two existing caches: allday_cache (data/raw/iv/SPX_allday_vols.parquet, column kvar_vol_pct = gross mark Kvar)
  and exec_kvar_cache (data/processed/gsvivs_exec_kvar.parquet, kvar_vol_pct = net Kvar with all TC).
  Both are loaded in compute_gsvivs_stats() and stored as iv_allday_kvar and iv_exec_kvar columns in iv_data.
  The new source subtracts a 20-day rolling mean of (mark - exec) from the mark, giving an estimated net Kvar.
  The existing config validation is in _VALID_IV_SOURCES set in config.py.
depends_on: []
```

---

### Step 2: Tests `[subagent]`

```yaml
subtask_id: "execute-2"
goal: "Write unit tests for the TC-adjusted IV source computation and verify integration with dashboard/config"
file_scope:
  - src/volforecast/evaluation/gsvivs.py          # The new load logic from execute-1
  - src/volforecast/config.py                     # _VALID_IV_SOURCES
  - src/tests/unit/test_spx_allday_vols.py        # Existing tests (add to this file)
  - src/tests/unit/test_dashboard.py              # Dashboard test patterns
write_scope:
  - src/tests/unit/test_spx_allday_vols.py        # ADD: TC-adjusted tests
acceptance_criteria:
  - "Test: given known allday and exec series, TC-adjusted series equals allday - rolling_mean(allday - exec)"
  - "Test: first 20 values are NaN due to rolling window warmup"
  - "Test: when exec cache is None, TC-adjusted series is all-NaN"
  - "Test: when allday cache is None, TC-adjusted series is all-NaN"
  - "Test: 'spx_allday_vols_tc' is accepted in config validation"
  - "Test: IV_SOURCE_REGISTRY contains the new entry with correct label/column"
  - "All tests pass: ./vol test -x -q -k 'allday'"
memory_refs: []
constraints:
  - "Use pytest with mock patches for load_allday_cache and load_exec_kvar_cache"
  - "Do NOT call real data — mock everything"
  - "Follow existing test patterns in test_spx_allday_vols.py"
  - "TDD: these tests should be written BEFORE execute-1 ideally, but since the registration is simple, write them to verify execute-1's output"
context_summary: |
  Execute-1 added spx_allday_vols_tc to the IV_SOURCE_REGISTRY and _VALID_IV_SOURCES,
  and added load logic in compute_gsvivs_stats that computes:
    tc_drag = (allday - exec).rolling(20, min_periods=20).mean()
    iv_allday_kvar_tc = allday - tc_drag
  Tests should verify the math, edge cases (missing data, warmup period), and config acceptance.
depends_on: ["execute-1"]
```

---

### Step 3: Config Update + Integration Verification `[inline]`

Add `spx_allday_vols_tc` to trial configs for testing:

- Add to `trial_063_xgboost_champion.yaml` → `gsvivs_iv_sources` list
- Add to `trial_067_xgb_reseed_h1.yaml` → `gsvivs_iv_sources` list
- Run full test suite to verify no regressions

This is a trivial config edit (< 10 lines total) so it executes inline.

---

## Execution Order

```
execute-1 (registry + load logic)
    ↓
execute-2 (tests)
    ↓
step-3 inline (config updates + integration test)
```

## Risk Assessment

- **Low risk:** No new data pipeline, no new CLI, no new parquet. Pure computation at load time.
- **Graceful degradation:** If either cache is missing, the column is NaN and the dashboard just won't show data for this variant.
- **No breaking change:** Existing `spx_allday_vols` and `exec_kvar` are untouched.
