# Plan: Dealer Gamma (GEX) Integration Into XGBoost Champion

**Status:** DESIGN complete, ready for /execute
**Owner:** vincry
**Baseline:** [trial_063_xgboost_champion.yaml](../configs/trial_063_xgboost_champion.yaml)
**Target trial:** trial-096 (next unused ID after trial-095)
**Created:** 2026-07-27
**Workflow:** /plan → /execute

---

## 1. Scope

Wire the newly-ingested dealer gamma (GEX) parquet cache into the ML feature pipeline as a new feature layer, produce a champion+GEX config, and register the resulting trial. This plan does NOT include model training or interpretation — those follow via `/experiment` after the code is landed and historical GEX is backfilled.

### In scope

- New feature layer `dealer_gamma` registered via `@register_feature_layer`
- Test file mirroring existing feature-layer test patterns (TDD)
- New config `trial_096_xgboost_champion_plus_dealer_gamma.yaml` (copy of trial_063 + `dealer_gamma` in `feature_layers`)
- Historical GEX backfill task (long-running, can run in parallel with code work)
- Trial-096 registration in [trials.yaml](../research/trials.yaml)
- Integration smoke test (small date range) confirming GEX columns land in the training matrix

### Out of scope (deferred)

- Multi-seed training of trial-096 (post-`/execute`, via `/experiment`)
- QLIKE comparison and DM significance vs trial-067 (post-training)
- GEX × IV interaction features (would go in `options` layer or `tree_expansion` — evaluate after main effect measured)
- Per-symbol GEX for single names (this plan is SPX-only, broadcast across the panel; matches how IV is handled)

---

## 2. Architectural Decision: Separate Layer, Not Part of `options`

**Decision:** GEX gets its own layer `dealer_gamma`, NOT added to `options`.

**Reasoning:**

| Consideration | `options` layer | new `dealer_gamma` layer |
|---|---|---|
| Data source | Consumes already-enriched IV columns from `iv_surface` — does no file I/O itself | Would need to load [spx_gex_daily.parquet](../../data/raw/options_oi/spx_gex_daily.parquet) directly |
| Cohesion | Layer is pure transforms (VRP, term slope, skew) on IV | GEX is a raw signal from a different pipeline (QSP OptionPrices) |
| Analog in codebase | Matches the split: `iv_surface` LOADS, `options` TRANSFORMS | `dealer_gamma` mirrors `iv_surface` (LOADS + broadcasts) |
| Ablation control | Can't turn GEX on/off without also toggling all IV transforms | Clean toggle via `feature_layers` list |
| Sparse-history handling | Would force early-return logic into `options` | Isolated to one layer, easier to gate |

The layer split in this repo is loader-layer vs transform-layer, not "topic bucket". `iv_surface` = loader, `options` = transformer. `dealer_gamma` fits the loader mold and should live alongside `iv_surface`.

---

## 3. Acceptance Criteria

**Code:**
- `dealer_gamma` appears in `FEATURE_REGISTRY` and is dispatched by the runner when listed in `feature_layers`
- All new tests pass; no existing test regresses
- `./vol lint` clean on new files (only run at end)

**Data wiring:**
- Running the new config on a 2-week window (e.g. `2025-01-02` to `2025-01-15`) produces a training matrix whose column list includes at least: `gex_sign_d`, `gex_zscore_d`, `gex_quintile_d`, `gex_regime_d`, `gex_momentum_d`
- Dates outside the GEX cache coverage produce NaN in `gex_*` columns (no crash, no leakage)
- SPX-only broadcast: every symbol in the pooled panel sees the same `gex_*` values for a given date (index-based reindex, same pattern as VVIX/VIX)

**Config:**
- [trial_096_xgboost_champion_plus_dealer_gamma.yaml](../configs/trial_096_xgboost_champion_plus_dealer_gamma.yaml) is identical to trial_063 except for `name`, `feature_layers` list, and a header comment
- Config parses via existing config loader (schema-valid)

**Trial registry:**
- [trials.yaml](../research/trials.yaml) has a new `trial-096` entry with `status: NOT_STARTED`, `hypothesis`, `motivation`, `gate`, `depends_on: trial-067`, `baseline_config: trial_063_xgboost_champion.yaml`

**NOT part of AC (post-execute):**
- Trial-096 QLIKE result — that lives in `/experiment interpret` after training

---

## 4. Dependency Graph

```
                   ┌─── execute-1: DealerGammaLayer + tests (subagent) ──┐
                   │                                                       │
[start] ──────────┼─── execute-2: Historical backfill (inline, long) ─────┼─── execute-4: Integration smoke test (subagent)
                   │                                                       │        (needs 1, 2, 3)
                   └─── execute-3: New config file (inline) ───────────────┤
                                                                           │
                                                                           └─── execute-5: Register trial-096 in trials.yaml (inline)
                                                                                    (needs 3)
```

**Parallel launch:** execute-1, execute-2, execute-3 can start immediately in parallel (no code-level dependency between them).
**Serial gate:** execute-4 requires all three; execute-5 requires only execute-3.

---

## 5. Subtask Decomposition

### execute-1: Implement `DealerGammaLayer` + tests (subagent)

```yaml
subtask_id: execute-1
mode: subagent
depends_on: []
goal: "Implement a new feature layer 'dealer_gamma' that loads the GEX parquet cache, produces the 5 GEX feature columns, aligns to the daily panel index, and handles missing-data gracefully. Follows TDD."
file_scope:
  - src/volforecast/features/iv_surface.py         # canonical loader-layer pattern
  - src/volforecast/features/options.py            # for OptionsLayer shape (compute signature)
  - src/volforecast/features/__init__.py           # to register the module import
  - src/volforecast/registry.py                    # to see @register_feature_layer decorator
  - src/volforecast/data/gex_ingest.py             # load_gex_cache signature
  - src/volforecast/data/options_oi.py             # build_gex_features signature
  - src/tests/unit/test_iv_surface_layer.py        # test template
  - src/tests/unit/test_options_oi.py              # existing GEX-related tests
write_scope:
  - src/volforecast/features/dealer_gamma.py       # NEW
  - src/tests/unit/test_dealer_gamma_layer.py      # NEW
  - src/volforecast/features/__init__.py           # add import line (or ensure_registered discovers it)
acceptance_criteria:
  - "DealerGammaLayer.compute(daily_data, context=None) returns a pd.DataFrame indexed by daily_data.index"
  - "Output columns include exactly: gex_sign_d, gex_zscore_d, gex_quintile_d, gex_regime_d, gex_momentum_d"
  - "When GEX cache is empty or missing dates, output has correct shape with NaN (never raises)"
  - "Layer is registered under the key 'dealer_gamma' in FEATURE_REGISTRY"
  - "Layer follows the IVSurfaceLayer broadcast pattern: reindex to daily_data.index, no forward-fill"
  - "All new tests pass; no existing test regresses"
memory_refs:
  - memory/research/optimal-feature-set.md   # feature layer design principles
constraints:
  - "Test-first: write the failing test file before the implementation."
  - "Do NOT add gex_* columns to OptionsLayer — keep the two layers cleanly separated."
  - "Load path: use load_gex_cache() from volforecast.data.gex_ingest — do not re-implement parquet reads."
  - "Use build_gex_features() from volforecast.data.options_oi for the actual feature computation."
  - "Match iv_surface.py's error handling: return empty/NaN DataFrame on missing data, do not raise."
  - "Do not add any new dependencies to pyproject.toml."
context_summary: |
  The user has just ingested GEX (dealer gamma exposure) data via ./vol ingest-gex. The parquet cache
  lives at data/raw/options_oi/spx_gex_daily.parquet with columns (gex_net, gex_call, gex_put,
  gex_sign, spot, n_valid_contracts, oi_total, oi_pcr, date). A helper build_gex_features() at
  src/volforecast/data/options_oi.py:397 converts this raw cache into 5 ML-ready columns
  (gex_sign_d, gex_zscore_d, gex_quintile_d, gex_regime_d, gex_momentum_d).

  The feature pipeline uses a registry pattern: layers register via @register_feature_layer and
  the runner iterates config.feature_layers, calling layer.compute() with the per-symbol
  daily_data frame. SPX-only signals (VIX, VVIX, EDRVS) are broadcast to every symbol by
  index-based reindex — this is the pattern DealerGammaLayer must follow. See IVSurfaceLayer.
```

---

### execute-2: Historical GEX backfill (inline, long-running)

```yaml
subtask_id: execute-2
mode: inline
depends_on: []
goal: "Run ./vol ingest-gex to backfill historical GEX data over the training window (2015-01-02 to today-1)."
acceptance_criteria:
  - "data/raw/options_oi/spx_gex_daily.parquet contains rows covering at least 2018-01-02 through 2026-07-25"
  - "No date range gaps > 1 week (weekends/holidays excepted)"
  - "load_gex_cache() returns a DataFrame with n_rows > 2000"
command: |
  ./vol exec ./vol ingest-gex --start 2015-01-02 --end 2026-07-25
constraints:
  - "This is expected to take a long time (potentially hours) — QSP paginates ~17k contracts per day."
  - "Run in background via ./vol exec so it survives session end."
  - "Confirm start date coverage with the user before launching — QSP may not have SPX option chain history back to 2015."
  - "If the ingest fails on a specific date, log and continue (the current CLI already skips per-date failures)."
notes: |
  This subtask is independent of code changes. It can be launched immediately and run in the
  background while execute-1 and execute-3 proceed. The integration smoke test (execute-4)
  only requires the 2 dates already ingested; the full backfill is what makes trial-096 a
  fair comparison against trial-067.
```

---

### execute-3: New config file (inline)

```yaml
subtask_id: execute-3
mode: inline
depends_on: []
goal: "Create trial_096_xgboost_champion_plus_dealer_gamma.yaml as a byte-for-byte copy of trial_063 with two changes: name field and feature_layers list."
write_scope:
  - workspace/configs/trial_096_xgboost_champion_plus_dealer_gamma.yaml   # NEW
acceptance_criteria:
  - "File exists and diffs against trial_063 show ONLY: header comment block, `name:` line, `feature_layers:` line"
  - "feature_layers list is [iv_surface, har_core, asymmetry, noise_robust, options, dealer_gamma, calendar, tree_expansion] (dealer_gamma inserted after options)"
  - "name: trial_096_xgboost_champion_plus_dealer_gamma"
  - "Header comment records: motivation (add GEX as feature), baseline (trial_063), expected data-availability caveat (backfill dependency)"
constraints:
  - "Preserve indentation, ordering, all other fields verbatim from trial_063."
  - "Do NOT change hyperparameters, universe, date_range, horizons, or tournament block — the whole point is a clean feature ablation."
```

---

### execute-4: Integration smoke test (subagent)

```yaml
subtask_id: execute-4
mode: subagent
depends_on: [execute-1, execute-3]
goal: "Verify end-to-end wiring: run the new config on a tiny date range (dates covered by the 2-row cache from earlier ingestion) and confirm the 5 GEX feature columns land in the training matrix with sensible dtypes."
file_scope:
  - workspace/configs/trial_096_xgboost_champion_plus_dealer_gamma.yaml
  - src/volforecast/features/dealer_gamma.py
  - src/volforecast/pipeline/runner.py                # runner dispatch loop (line ~1298)
  - src/volforecast/__main__.py                       # to see the vol run entry point
write_scope:
  - workspace/tmp/dealer_gamma_smoke_test.py           # temp script (delete after)
acceptance_criteria:
  - "Smoke script constructs the pipeline programmatically for date range 2025-01-02 to 2025-01-03"
  - "Print statement confirms {'gex_sign_d', 'gex_zscore_d', 'gex_quintile_d', 'gex_regime_d', 'gex_momentum_d'}.issubset(training_matrix.columns) is True"
  - "For those two dates, at least gex_sign_d has non-NaN values (the 2 ingested rows cover them)"
  - "No exceptions raised during runner dispatch of the dealer_gamma layer"
constraints:
  - "Do NOT run the full trial (5000-tree XGBoost training) — this is a wiring test only."
  - "Use ./vol exec for the smoke script; delete it after passing."
  - "If the smoke test fails, report the exact traceback — do not attempt to patch execute-1 code from within this subtask."
context_summary: |
  This subtask validates that execute-1's layer implementation is discoverable by the runner
  and produces valid columns. Depends on execute-2 (backfill) NOT being complete — the two
  cached dates (2025-01-02, 2025-01-03) are sufficient for a wiring smoke test. A full-history
  training run happens later via /experiment after execute-2 completes.
```

---

### execute-5: Register trial-096 in trials.yaml (inline)

```yaml
subtask_id: execute-5
mode: inline
depends_on: [execute-3]
goal: "Append a NOT_STARTED trial-096 entry to workspace/research/trials.yaml."
write_scope:
  - workspace/research/trials.yaml
acceptance_criteria:
  - "New entry appended after trial-095 with fields: id, date, config, name, hypothesis, motivation, gate, covid_handling, horizons: null, baseline_config, status: NOT_STARTED, priority, depends_on: trial-067"
  - "hypothesis references expected direction and magnitude (see below)"
  - "motivation mentions this is a feature ablation on the XGBoost champion (single-seed first, multi-seed if promising)"
constraints:
  - "Do NOT run the trial — status must be NOT_STARTED."
  - "Do NOT modify any existing trial entries."
suggested_content: |
  - id: trial-096
    date: '2026-07-27'
    config: trial_096_xgboost_champion_plus_dealer_gamma.yaml
    name: xgboost_champion_plus_dealer_gamma
    hypothesis: "Adding dealer gamma exposure (5 GEX features: gex_sign_d, gex_zscore_d,
      gex_quintile_d, gex_regime_d, gex_momentum_d) to the XGBoost champion feature set
      improves QLIKE at h=1 by 10-30 bps. GEX is a well-documented microstructure signal:
      dealer short-gamma regimes are associated with intraday mean reversion and dampened
      realized variance; dealer long-gamma regimes with trending price action and amplified
      variance. This SPX-only signal broadcasts across the 21-symbol pooled panel via
      index reindex (same pattern as VIX/VVIX). Prior: any measurable gain > 10 bps at
      h=1 is the bar; h=22 tie or slight loss is expected (dealer positioning is a
      short-horizon signal)."
    motivation: "First trial to consume the newly-ingested QSP GEX data. Clean ablation
      on trial_063 champion — identical hyperparameters, identical universe, identical
      CV, only feature_layers changes (add dealer_gamma). Result determines whether GEX
      warrants (a) multi-seed validation, (b) interaction features with IV/RV, or
      (c) rejection."
    gate: "Single-seed panel-DM of trial-096 vs trial-067 at h=1/5/22. If h=1 delta >
      10 bps AND direction consistent at h=5, promote to 5-seed multi-seed validation.
      Otherwise reject and document as null finding."
    covid_handling: included (expanding window)
    horizons: null
    baseline_config: trial_063_xgboost_champion.yaml
    status: NOT_STARTED
    priority: 2
    depends_on: trial-067
```

---

## 6. Execution Sequencing (for /execute)

The DECOMPOSE phase of `/execute` should spawn:

1. **Wave 1 (parallel, immediately):** execute-1, execute-2, execute-3
   - execute-1: subagent (context packet above)
   - execute-2: inline bash launch, backgrounded via `./vol exec`
   - execute-3: inline file copy + edit
2. **Wave 2 (parallel, after Wave 1 code steps):** execute-4, execute-5
   - execute-4: subagent (needs execute-1 + execute-3 done — does NOT wait for execute-2 backfill)
   - execute-5: inline (needs execute-3 done)

Wave 2 does not wait for the backfill (execute-2) to finish. The smoke test uses the 2 already-cached dates; the trial cannot be run until backfill completes, but that's post-plan work.

---

## 7. Post-Plan (out of this plan's scope, but noted for continuity)

Once all 5 subtasks complete AND execute-2 backfill finishes:
1. Run `./vol run --config workspace/configs/trial_096_xgboost_champion_plus_dealer_gamma.yaml` (single seed)
2. Compare panel-DM at h=1/5/22 against trial-067
3. If h=1 gain > 10 bps → promote to multi-seed via `/experiment`
4. Update [project-state.md](../../memory/research/project-state.md) with verdict
5. If verdict is a champion, add GEX interaction features as a follow-up trial

---

## 8. Scope-Drift Guardrails

**1-2 new files beyond scope:** note and continue
**3+ new files OR new pyproject dep:** stop, report, ask user
**Any change to existing feature layers other than the __init__ import:** stop, report, ask user
**Runtime > 2× estimate for backfill:** report progress, decide whether to shrink date range

---

## 9. References

- Champion baseline: [trial_063_xgboost_champion.yaml](../configs/trial_063_xgboost_champion.yaml)
- GEX ingestion (just fixed): [src/volforecast/data/gex_ingest.py](../../src/volforecast/data/gex_ingest.py)
- GEX feature builder: [src/volforecast/data/options_oi.py#L397](../../src/volforecast/data/options_oi.py#L397)
- Loader-layer pattern to mirror: [src/volforecast/features/iv_surface.py](../../src/volforecast/features/iv_surface.py)
- Registry mechanism: [src/volforecast/registry.py](../../src/volforecast/registry.py)
- Runner dispatch loop: [src/volforecast/pipeline/runner.py#L1298](../../src/volforecast/pipeline/runner.py#L1298)
- Trials log format: [workspace/research/trials.yaml](../research/trials.yaml)
