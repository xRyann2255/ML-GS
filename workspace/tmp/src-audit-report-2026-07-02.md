# `src/` Codebase Organisation & Quality Audit — volforecast

**Date:** 2026-07-02 · **Scope:** `src/volforecast` (~46,300 LOC, 130 files) + `src/tests` (~42,100 LOC, 146 files)
**Method:** Phase 0 measurement (wc/cloc-equivalent, jscpd, radon, vulture, AST import graph, git), then a 6-dimension multi-agent deep read (84 agents, 1,097 tool calls). **Every finding below was independently re-derived by an adversarial verifier that read the cited code; verdicts are CONFIRMED (evidence re-derived exactly) or ADJUSTED (real, with corrections noted). 0 of 77 raw findings were refuted; cross-dimension duplicates are merged here into 67 unique findings: 8 BLOCKER, 17 HIGH, 28 MEDIUM, 14 LOW.**

---

## 1. Executive summary

The codebase is structurally healthier than its worst files suggest — average cyclomatic complexity is A (4.9), layering is mostly clean (zero env reads, one config mechanism, disciplined error-handling conventions in ingest) — but the pain is highly concentrated and much of it is **correctness-grade, not cosmetic**. The three worst problems: (1) **copy-paste-with-drift in the model layer** — `lightgbm.py`/`xgboost.py` are ~2,400-LOC near-clones that have already drifted twice with silent research-corrupting consequences (LightGBM tuning drops init-only params; XGBoost sample-reweighting is an empirically-confirmed no-op), and the pipeline's parallel vs sequential fold paths are a second drifted pair that makes `n_gpus=1` vs `n_gpus>1` runs non-reproducible while sharing one fold cache; (2) **the experiment-integrity layer leaks** — the fold-cache fingerprint omits training-relevant config fields (silent stale cache hits), `cv_for_horizon` zeroes the embargo leakage control on any horizon override, and `to_yaml` archives a lossy config snapshot, so archived trials can neither be trusted nor reproduced; (3) **a 3,134-LOC god file** (`pipeline/runner.py`, 73% of its package, containing an F(90) 711-line method) that makes every one of these defects hard to test and easy to re-introduce. The single highest-leverage fix is unifying the fold-execution paths and the GBM twins behind shared implementations — it eliminates four BLOCKERs at their root rather than patching symptoms. The biggest ongoing maintenance risk is that this is a research codebase whose deliverable is trial comparisons, and several confirmed defects (stale cache hits, zeroed embargo, no-op reweighting, drifted symbol universe) corrupt those comparisons **without ever raising an error**. A dedicated quick-win pass (~2–3 hours, items in §5) retires 2 BLOCKERs and ~15 smaller findings with trivial diffs; the strategic work (§6) is 4 well-scoped packages, each with an incremental migration path gated on the existing `check-regressions.sh` baseline.

---

## 2. Table 0 — structural map

| Path | Role (inferred) | Files | LOC | Largest file (LOC) | Outbound deps | Inbound deps | Layout | Notes |
|---|---|---|---|---|---|---|---|---|
| `volforecast/cli` | CLI subcommands, console/progress UI | 27 | 6,957 | audit.py (887) | config, constants, data, evaluation, pipeline, registry, utils | \_\_main\_\_, **data (!)** | layer | 3 fully-stubbed modules; audit has drifted dual entry points |
| `volforecast/data` | Ingestion, caches, tick/IV/EDRVOL access | 19 | 9,149 | micro.py (1,286) | **cli (!)**, constants, **features (!)**, **models (!)**, registry, utils | cli, evaluation, features, models, pipeline | layer | iv_features trains a HAR model in the data layer |
| `volforecast/evaluation` | Tournament, economics, metrics | 16 | 7,869 | economic_value.py (1,362) | config, constants, data, models, pipeline, registry, utils, visualization | nearly everything | layer | metrics.py is a pure-numpy leaf misfiled here (causes 2 cycles) |
| `volforecast/features` | Registry-decorated feature layers | 16 | 2,969 | microstructure.py (435) | data, registry, utils | data, registry | layer | healthiest package; iv_surface does live network fetches |
| `volforecast/models` | Model implementations | 16 | 9,678 | lstm.py (1,928) | config, data, evaluation, **pipeline (!)**, registry, utils | data, evaluation, pipeline, registry | layer | GBM twin files; TCN clones LSTM in-file; 4 stub ensembles |
| `volforecast/pipeline` | CV orchestration, fold cache | 6 | 4,311 | **runner.py (3,134 = 73% of pkg)** | config, data, evaluation, models, registry, utils | cli, evaluation, models | layer | god file; two drifted fold-execution paths |
| `volforecast/reporting` | HTML report (stubs) + Jinja templates | 9 | 461 | sections/economic_value.py (211) | config, evaluation | **none** (but templates ARE live) | layer | dead Python, live template dir used by visualization |
| `volforecast/utils` | paths, manifest, cv splitters, persistence | 7 | 1,545 | manifest.py (438) | **config (!)** | everything | layer | persistence.py is experiment logic, not a utility |
| `volforecast/visualization` | Tournament dashboard HTML | 3 | 1,271 | dashboard.py (1,169) | evaluation, registry | evaluation | layer | one F(81) 520-LOC function |
| top-level modules | config (812), constants (385), registry (86), \_\_main\_\_ (771), \_\_init\_\_ (8) | 5 | 2,062 | config.py (812) | — | — | — | registry is lazy/sound; config has an upward deferred edge |
| `tests/unit` | unit tier | 129 | 36,895 | test_models.py (1,263) | — | — | mirrors src | 2,206 test functions total |
| `tests/integration` | integration tier | 16 | 5,087 | — | — | — | mirrors src | golden parquets under tests/data |
| `tests/{slow,research,golden}` | tiers | 3 | 131 | — | — | — | — | slow/ is empty scaffolding; 2 stray tests at tests/ top level |

Layout is **consistently layer-based**; the defects are misfiled files and wrong-direction edges, not a mixed paradigm.

### Phase 0 hotspots

**Biggest source files (LOC):** runner.py 3,134 · lstm.py 1,928 · har_family.py 1,702 · economic_value.py 1,362 · micro.py 1,286 · xgboost.py 1,230 · edrvol.py 1,223 · lightgbm.py 1,180 · dashboard.py 1,169 · tournament.py 977.

**Worst cyclomatic complexity (radon; 40 functions rate D or worse, project average A=4.94):**
`Pipeline._run_one_horizon_sequences` **F(90)** runner.py:2424 · `build_tournament_dashboard` **F(81)** dashboard.py:48 · `compute_gsvivs_stats` **F(79)** gsvivs.py:76 · `_run_tournament_per_symbol` **F(67)** tournament.py:322 · `LSTMVolModel.fit` **F(65)** lstm.py:821 · `ingest_iv.run` **F(62)** · `build_rv_panel` **F(60)** · `tune_hyperparameters_xgb` **F(57)** · `refresh_ohlcv.run` **F(46)** · `ingest_symbol_micro` **F(44)**.

**Most-depended-on modules (inbound importers):** registry (32) · utils/paths (28) · constants (17) · config (15) · data/edrvol (13) · cli/progress (12) · models/_base (11). *(Phase 0 counted cli/console at 15; deep read corrected this — outside cli/ only `__main__.py` and `data/rv_panel.py` import cli UI modules.)*

**Circular dependencies (AST):** one 26-module SCC (registry ↔ all models/features) — **verified benign**: registration is lazy, via function-local imports inside `ensure_registered()`, not import-time; `economic_value ↔ realistic_straddle` (5 deferred sites, L5) · `_parallel ↔ tournament` (drifted intent, M12) · `utils ↔ config` (annotation-only, M15) · directory-level `models↔evaluation` and `pipeline↔evaluation` exist **solely** because metrics.py is misfiled (H9).

**Duplication (jscpd, min-tokens 70):** 85 clones, 1,197 duplicated lines (2.6%), concentrated in lightgbm↔xgboost (5 clones), har_family internal (6 clones), tournament per-symbol vs pooled, dashboard internal.

**Change hotspots (git churn × complexity):** **unavailable** — the repo history is a single snapshot commit (tree restored from QR-code backup), so churn cannot be measured. Treat the complexity column alone as the risk proxy.

**Debt markers:** 26 TODO/FIXME sites — nearly all `raise NotImplementedError("TODO: implement")` stubs (reporting/, models/ensemble.py, 3 cli modules). Commented-out-code scan: clean.

---

## 3. Findings

Format: `[ID] — Dimension · Severity · Verifier verdict`. All paths relative to `src/`. Merged IDs note their duplicate-dimension origins.

### BLOCKER

#### [B1] LightGBM `tune_and_fit` silently drops init-only config params that XGBoost re-merges (drifted copy)
- Dimension: duplication · Severity: BLOCKER · CONFIRMED
- Location(s): `volforecast/models/lightgbm.py:242`, `lightgbm.py:1134-1137`, vs `volforecast/models/xgboost.py:622-626`
- Evidence: xgboost.py:622-626 has the fix: `# Merge init-only keys from base_params … best_params[k] = base_params[k]`. lightgbm.py has no such block — `tune_and_fit` does `model = cls(n_estimators=n_est, **best_params)` (242-243) and the tuning merge explicitly excludes them: `if k not in best and k not in _INIT_ONLY_KEYS` (1135-1137). lightgbm's `_INIT_ONLY_KEYS` (57-69) includes `drop_features`, `monotone_constraints_named`, `residual_scale`, `sample_reweight`, `val_fraction`.
- Why it matters: a YAML config that enables tuning for lightgbm **and** sets any of those keys trains the final model with all of them silently ignored — no warning; results just quietly differ from the untuned path where the same params are honored.
- Recommended fix: port xgboost.py:622-626 verbatim into `LightGBMVolModel.tune_and_fit` (after lightgbm.py:241); permanently, move the shared re-merge into the `_gbm_common` mixin (H1).
- Effort: small · Risk if changed: tuned-lightgbm benchmark numbers can shift — runs that set those keys were previously getting unconstrained models.

#### [B2] XGBoost pass-2 sample reweight is a silent no-op under the custom objective (drifted copy; empirically confirmed)
- Dimension: duplication · Severity: BLOCKER · CONFIRMED (verifier reproduced it with xgboost 3.3.0 in a scratch venv: identical predictions with/without extreme weights)
- Location(s): `volforecast/models/xgboost.py:365-368`, `xgboost.py:414-417`, `xgboost.py:74-79` vs `volforecast/models/lightgbm.py:533-536`, `lightgbm.py:102-122`
- Evidence: lightgbm.py:533 documents and fixes the trap: `# LightGBM ignores Dataset weight= with custom objectives` → `_make_weighted_qlike_objective(weights)` multiplies grad/hess by weights. xgboost.py instead passes `weight=weights` via `xgb.DMatrix` and trains with `obj=qlike_objective_xgb`, whose grad/hess never read `dtrain.get_weight()`. `_compute_reweight` itself is byte-identical between the files (43-line jscpd clone).
- Why it matters: `sample_reweight.enabled: true` on xgboost retrains an identical model in pass 2 — doubled training cost, zero effect, and any experiment comparing "reweighted xgboost" vs baseline compared a model to itself.
- Recommended fix: mirror lightgbm — add a weighted-objective closure (grad/hess ×= weights) to both pass-2 `xgb.train` calls (xgboost.py:380-389, 419-425) and drop `weight=` from the DMatrix.
- Effort: small · Risk if changed: none beyond results legitimately changing; the double-apply concern was ruled out by the verifier's experiment.

#### [B3] Drifted duplicate fold algorithm: `_execute_fold` (parallel) vs the inline sequential loop — seed, `symbol_to_id`, and context handling differ, and both feed one fold cache
- Dimension: optimisation + maintainability (merged #49/#59) · Severity: BLOCKER · CONFIRMED ×2 (two independent verifiers)
- Location(s): `volforecast/pipeline/runner.py:178-415` (worker) vs `runner.py:2828-3099` (sequential); drift at `:347` vs `:3012`, `:3016`, `:3009-3010`; `volforecast/models/lstm.py:1443`
- Evidence: both paths implement base-model fit + cache lookup + per-fold normalise + fit/predict + Duan correction + cache save (block-for-block correspondence verified). Drift: (1) worker sets `fold_model_params["seed"] = …get("seed", 42) + seed_offset` (:347); sequential constructs `model_cls(**model_params)` with no offset (:3012); (2) sequential sets `model.symbol_to_id = symbol_to_id` (:3016), worker never does — and `symbol_to_id` is persisted in the saved model payload (lstm.py:1443); (3) context tensors are threaded only in the sequential copy.
- Why it matters: the same config run at `n_gpus=1` vs `n_gpus>1` trains folds with **different seeds** → non-reproducible results; both modes share the same fold cache (key contains no seed/mode component), so a sequential run can silently consume folds trained under parallel-mode seeds; fold-cached models from multi-GPU runs persist `symbol_to_id=None`.
- Recommended fix: make the sequential branch call `_execute_fold(…, device_id=None, progress_queue=None)` directly (it is already self-contained), add the two missing behaviors (symbol_to_id, context) to `_execute_fold` once, delete ~250 duplicated lines, and decide the seed policy once.
- Effort: medium · Risk if changed: unifying seed policy changes sequential-mode numbers and invalidates fold caches — bump the fingerprint version (B4) in the same change; `on_train_progress` callbacks need re-plumbing.

#### [B4] Fold-cache / experiment fingerprint omits training-relevant config fields — silent stale cache hits can corrupt research results
- Dimension: maintainability · Severity: BLOCKER · CONFIRMED
- Location(s): `volforecast/utils/persistence.py:135-148`, `persistence.py:184-217`, `volforecast/pipeline/fold_cache.py:100-110`, `volforecast/config.py:325-335`
- Evidence: fold_cache.py's docstring claims the key covers "every input that affects the trained model's outputs", but `_canon_sequences` hashes only `features` + `max_bars` while `SequenceConfig` also carries `bar_interval`, `norm_mode`, `source`, `lookback_days`, `context_features`; `_config_fingerprint` additionally omits `cv.embargo`, `feature_stack`, `blend`, `conditional_duan`, `feature_selection`.
- Why it matters: change `sequences.norm_mode` pooled→per_symbol (or `source`, or `lookback_days`) and rerun — same fingerprint, cache HIT (runner.py:2900), and the run reports predictions from the OLD tensor pipeline as the NEW experiment's results. These are first-class experiment axes in a signal-discovery project.
- Recommended fix: extend `_canon_sequences` with the five missing fields; add the missing sections to `_config_fingerprint`'s `relevant` dict; add `"fp_version": 2` so all old entries miss; add a parametrized regression test asserting the fingerprint changes when each field changes.
- Effort: small · Risk if changed: one-time invalidation of every existing lstm_cache entry (forced retrain) — intended.

#### [B5] `ExperimentConfig.cv_for_horizon` silently drops `embargo` — leakage control zeroed for any horizon with a cv override
- Dimension: maintainability · Severity: BLOCKER · CONFIRMED
- Location(s): `volforecast/config.py:515-521`, `config.py:183`, consumers at `volforecast/pipeline/runner.py:422,1181,1374,2530`
- Evidence: the override branch rebuilds `CVConfig(method=…, n_splits=…, purge_gap=…, train_size=…, test_size=…)` — no `embargo=`, so the dataclass default `embargo: int = 0` (config.py:183, "Phase 2.8: post-test exclusion") wins. `to_yaml` also omits embargo. No test covers embargo through `cv_for_horizon`.
- Why it matters: top-level `cv.embargo: 10` plus any `horizon_overrides[h].cv` entry (even just a train_size tweak — the documented pattern) silently trains that horizon with embargo=0. Embargo is a leakage control; its silent loss inflates OOS metrics for exactly the horizons being tuned.
- Recommended fix: `embargo=cv_override.get("embargo", self.cv.embargo)` in the CVConfig construction; write embargo in `to_yaml`; include it in the fingerprint (B4); add the one-line unit test.
- Effort: trivial · Risk if changed: QLIKE numbers move for previously-overridden horizons — document in the trial log.

#### [B6] Experiment output location split-brain: CWD-relative `config.output_dir` (with two conflicting defaults) vs root-anchored `persistence.experiment_dir()`
- Dimension: consistency · Severity: BLOCKER · CONFIRMED
- Location(s): `volforecast/config.py:434` vs `config.py:667`; `volforecast/utils/persistence.py:21-23`; `volforecast/evaluation/tournament.py:435-436`; `volforecast/__main__.py:299`
- Evidence: dataclass default `Path("data/models")` (434) vs from_yaml default `Path(raw.get("output_dir", "workspace/tmp/results"))` (667); neither is anchored, and the `vol` launcher `cd`s into src/, so relative paths resolve under src/. Meanwhile persistence writes root-anchored via `models_dir()/config.name` (marker-based `resolve_project_root`). tournament.py:435-436 checks the output_dir flag then calls `save_experiment_results`, which ignores it.
- Why it matters: one experiment's artifacts land in two different trees — per-symbol models/metrics.json under `<root>/data/models/<name>`, dashboards/pooled metrics under `<cwd>/…`; the CLI's output summary then points at a directory that may not contain what persistence wrote, and `load_predictions` reads from the root tree regardless.
- Recommended fix: anchor `output_dir` against `resolve_project_root()` in `from_yaml` (it already imports it at config.py:599 for the YAML path); unify the two defaults; derive `experiment_dir()` from `config.output_dir`.
- Effort: medium · Risk if changed: existing artifact trees move; fingerprint.json lookups and scripts pointing at the old tree need a migration note.

#### [B7] Layering violation: `data/rv_panel.py` imports `volforecast.cli.progress` for isinstance dispatch, forced by two near-clone progress classes with divergent signatures
- Dimension: consistency + organisation (merged #39/#29) · Severity: BLOCKER · CONFIRMED (one verifier scored the underlying edge MEDIUM because it is function-local and load-bearing only for progress dispatch — the blast radius is modest, but as the tree's only inverted layer edge it gates on the severity model)
- Location(s): `volforecast/data/rv_panel.py:333-342`, `rv_panel.py:374-388`; `volforecast/cli/progress.py:190-197` vs `progress.py:350-356`; clone at `progress.py:137-148` vs `306-317`
- Evidence: `from volforecast.cli.progress import ExperimentProgress` exists purely because `ExperimentProgress.add_subtask(stage, total, description, *, indent)` takes a leading `stage` arg that `StageProgress.add_subtask(total, description, *, indent)` does not; rv_panel branches on `isinstance(progress, ExperimentProgress)`. The two classes' 12-line Progress column stacks are character-identical; their subtask key formats differ (`"{stage}:sub:{desc}"` vs `"sub:{desc}"`).
- Why it matters: data-layer code depends on CLI presentation classes; every new data module wanting progress must copy the isinstance dance; the clones drift independently.
- Recommended fix: unify `add_subtask` signatures (keyword-only `stage` with a default on ExperimentProgress), collapse rv_panel to one duck-typed call, delete both cli imports. Preserve key prefixes — `finish_stage` cleanup matches on `startswith`.
- Effort: medium · Risk if changed: stage-completion cleanup depends on subtask key prefixes; keep formats stable.

#### [B8] Drifted duplicate symbol universe: `constants.SYMBOL_UNIVERSE` (36) vs `cli/audit.FULL_UNIVERSE` (34) disagree on 12 symbols; ingest defaults and chunk-store validation use the stale copy
- Dimension: gap-sweep · Severity: BLOCKER · CONFIRMED
- Location(s): `volforecast/constants.py:51,54-95,159`; `volforecast/cli/audit.py:37-74`; `volforecast/cli/ingest_ticks.py:31`; `volforecast/cli/ingest_micro.py:32`; `volforecast/data/chunk_store.py:197`
- Evidence: constants.py:51 header says "(34 symbols)" but the sets sum to 36; symmetric difference vs audit's list is 12 symbols — constants-only {CMCSA, CSCO, DIS, NKE, PFE, PYPL, SPX}, audit-only {ABBV, COST, LLY, UNP, WMT}. The RIC maps (constants.py:159, :214) cover the audit-side set and lack the constants-only equities; the project's data-audit doc lists ABBV in the real tick dataset — the audit list is the true universe.
- Why it matters: default `vol ingest-ticks`/`ingest-micro` fetch 6 symbols not in the actual universe and never fetch ABBV/COST/LLY/UNP/WMT; `chunk_store.fetch_trades("ABBV", …)` raises ValueError even though the data exists — the code cannot re-ingest or backfill 5 of the 34 real symbols, and audit vs ingest report different "missing symbols" lists.
- Recommended fix: correct `EQUITY_SYMBOLS` in constants.py to the AGENTS.md list; delete `FULL_UNIVERSE` from cli/audit.py and import the constant; add a test asserting `SYMBOL_UNIVERSE` is consistent with the RIC maps to prevent re-drift.
- Effort: small · Risk if changed: any cached parquet/manifest data previously ingested for the 6 stale symbols becomes orphaned; tighten deliberately.

### HIGH

#### [H1] `lightgbm.py`/`xgboost.py` are ~2,400-LOC near-clones — the root cause of B1 and B2
- Dimension: duplication + maintainability (merged #2/#64) · Severity: HIGH · CONFIRMED+ADJUSTED
- Location(s): `models/lightgbm.py:247,285,363,403,603` ↔ `models/xgboost.py:129,167,204,243,429`; `models/lstm_tuning.py:320-338` ↔ `xgboost.py:812-830`; Optuna scaffolding `xgboost.py:833+` ↔ `lightgbm.py:831+`
- Evidence: verifier diffed extracted method bodies programmatically — `get_params` 0 diff lines; `_clean_inputs` differs only in comments and one exception string over ~40 lines; `_fit_base_model` and `_build_val_split` identical; `_compute_reweight` ~85% identical (60 lines); the two ~400-LOC Optuna journal/worker/polling loops have already drifted (sleep 0.5 vs 1.0s, progress-queue drain only in xgb, `n_warmup_steps` 1 vs 2, duplicated `except Exception: pass` journal reads at xgb:1066/1100, lgb:1047/1069); `_make_trial_done_callback` also cloned into lstm_tuning.py (rule-of-three satisfied).
- Why it matters: one algorithm (HAR-IV-residual GBM + QLIKE objective + multi-process Optuna) maintained twice; it has already drifted twice with BLOCKER consequences; every HPO/plumbing fix must be applied twice and provably is not.
- Recommended fix: `volforecast/models/_gbm_common.py` with a `_GBMCoreMixin`: `__init__` fields, `get_params`, `_clean_inputs` (error label from `cls.name`), `_fit_base_model`, `_build_val_split`, `_compute_reweight` (abstract `_predict_tree_output`), one shared trial-done callback, and the Optuna journal/worker scaffolding parameterized by an objective factory. Keep library-specific fit/predict/objective in each file; keep the NaN-handling differences (LightGBM native-NaN vs XGBoost base-margin) as injected strategies, not merged code.
- Effort: large (mixin core: medium) · Risk if changed: pickled fitted models must keep attribute names; regression-gate QLIKE outputs against the existing baseline.

#### [H2] Tournament option plumbing threaded through 4 near-identical 32–47-parameter signatures; the per-symbol path silently drops options the public API accepts
- Dimension: duplication · Severity: HIGH · CONFIRMED
- Location(s): `evaluation/tournament.py:152-200, 229-276, 277-310, 322-355, 621-668`
- Evidence: `run_har_tournament` (47 params) is mirrored by `_run_tournament_pooled` (46) and `_run_tournament_per_symbol` (32) plus two manual keyword-forwarding blocks; `gsvivs_short_threshold` alone appears 7× in this file. The per-symbol branch forwards none of `sequences`, `base_model`, `n_gpus`, `fold_cache_*`, `feature_stack`, `blend`, `parallel_models` — and its signature lacks them entirely.
- Why it matters: adding one tournament option requires 4–6 edits; miss one and it is silently dropped — already the observable state for `training_mode: per_symbol`, which accepts and ignores blend/base_model/fold-cache settings without error.
- Recommended fix: a frozen `TournamentOptions` dataclass (or extend the existing `TournamentConfig`, config.py:263) passed as one argument to both impls; per-symbol mode raises/warns on unsupported options. Keep the public kwargs signature for compatibility.
- Effort: medium · Risk if changed: wide call surface (`__main__`, dashboard, tests) — collapse only the internal forwarding.

#### [H3] Ingest-helper quadruplication with drifted cache-freshness logic: 4 versions of `_cache_covers_range`, only ingest_iv's knows about the T+1 publication lag
- Dimension: duplication · Severity: HIGH · ADJUSTED
- Location(s): `data/correlation_ingest.py:32-90` ↔ `data/cross_asset_ingest.py:38-100` (47L verbatim); `cli/ingest_edrvol.py:26-32`; `cli/ingest_iv.py:62-83`
- Evidence: three strict variants (`cached_start <= start and cached_end >= end`) vs ingest_iv's fixed variant (3-day end slack for TSDB publication lag + required-column validation). correlation/cross_asset default `end=yesterday` and have **no incremental-fetch path**, so against T+1 sources the strict check can never pass on a daily cadence → full re-fetch from 2010/2015 every run.
- Why it matters: a bug fixed in one copy (publication lag) was never ported; the strict copies force full re-downloads on every scheduled ingest.
- Recommended fix: `volforecast/data/_ingest_common.py` with `IngestResult`, `_normalize_index`, `_build_aligned_df`, and one `cache_covers_range(…, end_slack_days=0, required_columns=None)`; keep slack=0 defaults initially (behavior-preserving), then set per-source lag deliberately.
- Effort: medium · Risk if changed: changing slack changes when re-fetches happen; do it in two steps.

#### [H4] P&L summary metrics copy-pasted 6× across evaluation modules; annualization factor 252 hardcoded 123× in 19 files with no constant
- Dimension: duplication + maintainability (merged #5/#66) · Severity: HIGH · ADJUSTED ×2
- Location(s): `evaluation/economic_value.py:738,856,938,1148`; `evaluation/realistic_straddle.py:849`; `evaluation/tournament_economics.py:345`; `evaluation/phase3_experiments.py:353`; 252-literals across evaluation/, features/, models/ (123 occurrences / 19 files; `constants.py` has zero); CV defaults `or 252`/`or 63` repeated at 4+ runner sites (runner.py:427 etc.)
- Evidence: `peak = np.maximum.accumulate(cum_curve)` ×6; the ann-vol formula (`np.std(pnl_clean, ddof=1) * np.sqrt(252) * 100`) ×4 verbatim; the Sharpe formula with the `1e-12` floor ×4; `np.sqrt(252.0 * np.exp(log_rv_predictions))` ×5.
- Why it matters: these formulas encode reporting-critical choices (ddof, floor, scaling, day-count). Six copies mean a future convention change produces dashboards where Sharpe/ann_vol disagree between engines with no error.
- Recommended fix: in economic_value.py add `TRADING_DAYS = 252.0` (or put `TRADING_DAYS_PER_YEAR` in constants.py), `annualized_vol_from_log_rv()`, and `summarize_pnl() -> dict`; replace the six blocks mechanically (bit-identical extraction — no "while we're here" changes); sweep live-code 252s in evaluation/ and features/.
- Effort: medium · Risk if changed: golden-file dashboard tests compare exact floats — extraction must be mechanical.

#### [H5] 21 MB of generated artifacts tracked in git (67% of the HEAD tree)
- Dimension: bloat · Severity: HIGH · CONFIRMED
- Location(s): `src/.coverage`; `src/workspace/tmp/results/plots/tournament_dashboard.html` (19.6 MB); `src/workspace/tmp/trial_067_smoke/plots/tournament_dashboard.html` (1.3 MB); `src/workspace/tmp/count_flat_days.py`
- Evidence: `git ls-tree -r HEAD -l` blob sizes verified; `.coverage` is a SQLite db that churns on every test run; `count_flat_days.py` is a one-off scraper hardcoded to parse the committed HTML. No .gitignore rule covers them.
- Why it matters: every clone carries ~21 MB of regenerable output; `.coverage` produces noisy diffs; committed artifacts invite more artifact commits.
- Recommended fix: `git rm --cached` the four files; add `.coverage` and `src/workspace/tmp/` to the root `.gitignore`. Keep the two tiny metrics.json blobs if they serve as goldens.
- Effort: trivial · Risk if changed: anything linking to the committed dashboard 404s.

#### [H6] `TCNVolModel` duplicates ~170 LOC of `LSTMVolModel` training scaffolding inside the same 1,928-LOC lstm.py — already drifted in capability
- Dimension: bloat · Severity: HIGH · CONFIRMED
- Location(s): `models/lstm.py:1676-1847` vs `lstm.py:821-1190`; verbatim `_set_seed` 726-729 vs 1647-1650; `_align_targets` 771-788 vs 1660-1672
- Evidence: purge-gap block, index_select split, AdamW + ReduceLROnPlateau(factor=0.5, patience=2), early-stopping loop (`improved = val_loss + 1e-6 < best_val`, `batch_update_stride = max(1, total//20)`) — line-identical between the two fit methods. LSTM has since gained base_preds/symbol_ids/context/torch.compile support that TCN silently lacks.
- Why it matters: any fix to shared training semantics (val purge-gap leak guard, early-stopping tolerance) must be applied twice in one file, and history shows it lands once.
- Recommended fix: extract `models/_seq_train.py` (split_and_purge, select_train_val, run_training_loop) called by both; move the TCN classes (lstm.py:1500-1928, 428 LOC) to `models/tcn.py` and update `registry.ensure_registered`.
- Effort: medium · Risk if changed: the loop is seed-sensitive (`torch.randperm` order) — preserve exact op ordering or fold caches/baselines shift.

#### [H7] `pipeline/runner.py` is a 3,134-LOC god file; the feature-stack factories (782 LOC) and the sequence path (871 LOC incl. the F(90) method) are separable wholesale
- Dimension: bloat · Severity: HIGH · CONFIRMED
- Location(s): `pipeline/runner.py:1398-2179` (feature-stack block), `:2264-3134` (sequence block), `:458` (`_run_horizon` E(37)), `:445` (class Pipeline)
- Evidence: spans re-measured exactly (782 and 871 LOC); radon reproduces F(90) at :2424 and E(37) at :458; the only coupling back into Pipeline is the documented 3-arg callback `feature_stack_fn(train_idx, test_idx, h)` (:483, invoked :547).
- Why it matters: 73% of the pipeline package in one file; a 711-LOC F(90) method is untestable in units; every model-path change (tabular/blend/sequence/GNN) touches the same file.
- Recommended fix: extract `pipeline/feature_stack.py` (the three factory functions, parameterized by (config, panel_data) — closure shape already matches) and `pipeline/sequence_runner.py` (`_resolve_sequence_config`, `_run_pooled_sequences`, `_run_one_horizon_sequences`); runner.py drops to ~1,480 LOC. Do B3 first so the sequence module is 250 lines lighter.
- Effort: large · Risk if changed: closures capture many enclosing variables — convert with the integration tests as the gate.

#### [H8] torch is import-time mandatory on the core run path but declared only in optional extras
- Dimension: organisation · Severity: HIGH · ADJUSTED (evidence strengthened by verifier)
- Location(s): `data/sequence_cache.py:31` → `pipeline/runner.py:31-35` → `evaluation/tournament.py:30` → `__main__.py:287/754-756`; `registry.py:37` (unguarded `import volforecast.models.lstm`; only gnn is try/except-guarded at :43-46); `pyproject.toml` (torch only in `gpu`/`graph` extras, not base or `ml`)
- Evidence: `import torch` is top-level in sequence_cache.py, re-exported at module level in runner.py "for testability"; **all** non-ingest `vol run` modes route through tournament→runner→sequence_cache; `vol forecast` calls `ensure_registered()` which unconditionally imports lstm (top-level torch).
- Why it matters: a base or `[ml]` install crashes with ModuleNotFoundError on every `vol run`, even HAR-only configs; with torch installed, every command pays the multi-second torch import for tournaments that never touch LSTM.
- Recommended fix: (a) move `import torch` in sequence_cache.py and pipeline/norm.py into the functions that use it (TYPE_CHECKING for hints); (b) guard `import volforecast.models.lstm` in `ensure_registered()` like gnn; (c) replace runner.py's module-level re-export with a patch point in data.sequence_cache. Alternatively declare torch a base dep — but lazy imports still win the startup time back.
- Effort: medium · Risk if changed: tests monkeypatching `runner.SequenceTensor`/`fit_seq_normaliser` must be repointed; CUDA init moves to first fold.

#### [H9] `evaluation/metrics.py` is a pure-numpy leaf misfiled in the top evaluation layer — the sole cause of both `models↔evaluation` and `pipeline↔evaluation` cycles
- Dimension: organisation · Severity: HIGH · CONFIRMED
- Location(s): `evaluation/metrics.py:12` (only import: numpy); `pipeline/runner.py:19`; `pipeline/conditional_duan.py:34`; `models/blend.py:17`; deferred at `xgboost.py:731`, `lightgbm.py:766`, `lstm_tuning.py:109`; reverse edges `evaluation/tournament.py:30`, `evaluation/_parallel.py:28`
- Evidence: verifier confirmed pipeline→evaluation and models→evaluation exist **only** via metrics imports; 10 production + 8 test import sites; 3 of the 5 model-side imports were made function-local specifically to dodge the cycle.
- Why it matters: the two loudest cycles in the dependency matrix are caused by one 188-LOC file's address; model authors reach "upward" for loss functions, accumulating deferred-import noise.
- Recommended fix: move to `volforecast/metrics.py` (sibling of constants.py); keep `evaluation/metrics.py` as a re-export shim so all 18 sites keep working; migrate opportunistically.
- Effort: small · Risk if changed: monkeypatch targets `volforecast.evaluation.metrics.qlike` must keep working through the shim.

#### [H10] `reporting/` is dead scaffolding with zero production callers — but the live dashboard's Jinja template physically lives inside it
- Dimension: organisation + bloat (merged #28/#18) · Severity: HIGH · ADJUSTED
- Location(s): `reporting/html_report.py:34-46` (NotImplementedError stub); 5 of 6 section renderers stubbed (`sections/summary.py:28`, `forecast_vs_actual.py:45`, `qlike_analysis.py:33`, `statistical_tests.py:38`, `diagnostics.py:32`); the one implemented renderer (`sections/economic_value.py`, 211 LOC) unreachable; **`visualization/dashboard.py:443-447`**: `PackageLoader("volforecast", "reporting/templates")`
- Evidence: grep confirms zero production importers of reporting Python code; yet the production dashboard chain (tournament.py:138 → tournament_dashboard.py:78 → dashboard.py) loads its 2,509-line template set from `reporting/templates/`.
- Why it matters: anyone deleting the "orphaned" package (as the dependency matrix invites) silently breaks dashboard generation; meanwhile 461 LOC of stubs + a test file exercising NotImplementedError is pure weight.
- Recommended fix: move `reporting/templates/` to `visualization/templates/` and update the PackageLoader line; then either delete `reporting/{html_report.py, sections/}` + `tests/unit/test_reporting.py`, or actually implement per `workspace/plans/html-report.md` — decide, don't keep the stub.
- Effort: small · Risk if changed: hatchling wheel packaging must include the new template dir.

#### [H11] Atomic parquet-write idiom (`mkstemp` + `os.replace`) hand-copied 10× while other writers of the **same cache files** write non-atomically
- Dimension: consistency · Severity: HIGH · ADJUSTED
- Location(s): atomic copies: `data/ticks.py:162-172`, `data/ohlcv.py:181-191`, `data/micro.py:798/823/997`, `data/sequence_cache.py:539`, `pipeline/fold_cache.py:125-136`, `utils/manifest.py:186-200`, `models/lstm.py:1445`, `models/gnn.py:702`, `cli/gap_fixer.py:124`; non-atomic writers of the same files: `cli/backfill_rk.py:468` (per-batch checkpoint into the ticks cache — verified same directory via the deprecated `rv_cache_dir` alias), `data/rv_panel.py:734`, `cli/refresh_ohlcv.py:196`
- Evidence: backfill_rk's `panel.to_parquet(cache_dir / f"{symbol}.parquet")` under "# Checkpoint after each batch" writes the exact file ticks.py protects atomically.
- Why it matters: a Ctrl+C during backfill's checkpoint (its whole purpose is safe interruption) can truncate the cache parquet; next run's read raises and the merge logic silently discards history.
- Recommended fix: `atomic_to_parquet(df, path, **kwargs)` in a new `utils/io.py` (body = ticks.py:162-172 verbatim); replace the 10 copies; convert the shared-file direct writers first.
- Effort: small · Risk if changed: `os.replace` on Windows fails if the destination is open elsewhere — same as existing atomic writers.

#### [H12] No fit/predict contract in `models/_base.py`; divergent optional kwargs force 4-way fit and 2×2×2 predict dispatch in runner.py
- Dimension: consistency · Severity: HIGH · CONFIRMED
- Location(s): `models/_base.py:15-88`; `pipeline/runner.py:3031-3040` (fit dispatch), `:3042-3063` (predict dispatch, 12 occurrences of the inline `**({"context": …} if … else {})` hack); `models/lstm.py:821-831` vs `:1676-1685`
- Evidence: `_BaseModel` defines save/load/summary/tune_and_fit but no fit/predict; LSTM.fit accepts `context`, TCN.fit does not; runner branches combinatorially and guards by value, so a TCN config that supplies context dies with TypeError at fit time.
- Why it matters: every new optional kwarg doubles the branch count in an already-3,134-LOC file; capability errors surface at fit time instead of config validation.
- Recommended fix: adopt the fit-kwargs-dict pattern already used at runner.py:3020-3029 everywhere; add `context` to TCN.fit for parity; declare `fit`/`predict` in `_BaseModel` (or a Protocol) with explicit capability flags.
- Effort: medium · Risk if changed: passing previously-omitted kwargs must be a true no-op; prefer explicit keywords over `**kwargs` to keep misspellings failing fast.

#### [H13] Live Marquee network fetches (0DTE/1DTE SPX IV) inside `IVSurfaceLayer.compute`, re-executed per symbol × horizon × model process
- Dimension: optimisation · Severity: HIGH · CONFIRMED
- Location(s): `features/iv_surface.py:134,147`; `data/edrvol.py:398,458-494,513,633,655`; loop at `pipeline/runner.py:1063-1091`
- Evidence: both fetches are unconditional (before any cache fallback), always `"SPX"` + the full date range; `_EXPIRY_CHUNK_MONTHS = 3` → 44 requests per call, 88 per compute(); compute runs per symbol per horizon; zero memoization on the chain (repo-wide lru_cache grep: 2 hits, neither here). Champion configs enable the layer.
- Why it matters: hot path — 21 symbols × 3 horizons = 63 identical refetches ≈ 5,500 chunked requests per model process (× parallel_models); tens of minutes of pure redundant network per tournament; on non-GS machines, 63 swallowed session failures.
- Recommended fix: `@lru_cache(maxsize=8)` on `_fetch_expiry_iv` (hashable args) — the codebase's own convention (realized_correlation.py:141); better still, persist to the IV cache parquet like every other IV series. ~100× fewer calls.
- Effort: trivial · Risk if changed: staleness within one process — irrelevant for a single run.

#### [H14] Horizon-invariant per-symbol feature matrices rebuilt from scratch for every horizon in `run_pooled`
- Dimension: optimisation · Severity: HIGH · CONFIRMED
- Location(s): `pipeline/runner.py:1056-1094` (`_build_and_run_horizon`), invoked per horizon at `:1223-1225`; `_run_pooled_blend` repeats it at `:1289+`
- Evidence: every `FeatureLayer.compute` signature is `(daily_data, *, context)` — no horizon parameter (verified across features/); only `forward_log_rv(rv, h)` and the target mask depend on h; the hoisting precedent already exists at :1033-1052 (`_fs_sym_seqs`).
- Why it matters: hot path — with horizons [1,5,22] the full feature stack (including H13's network fetches and 7 parquet reads per symbol) computes 3× per model process; for tabular models with sub-second fold training, feature building is a comparable or dominant share of wall time. Eliminating 2 of 3 rebuilds is a direct ~3× cut of that phase.
- Recommended fix: hoist the per-symbol loop out of `_build_and_run_horizon`: build `{sym: X_sym}` once, per horizon compute only the target/mask/stack.
- Effort: medium · Risk if changed: peak memory holds all symbols' X_sym for the run (marginal); a hypothetical horizon-dependent layer would break — none exists.

#### [H15] `sequences.context_features` is dead-on-arrival: UnboundLocalError — `model_params` used 15 lines before assignment (and never plumbed to the parallel path)
- Dimension: maintainability + optimisation (merged #60/#53) · Severity: HIGH · CONFIRMED ×2
- Location(s): `pipeline/runner.py:2499-2520` vs first binding at `:2535`; `config.py:335`; parallel submit at `:2779-2803` (no context arg); also `_resolve_sequence_config` never copies the field to the spec, so the getattr at :2499 is always `[]` today
- Evidence: `model_params["context_dim"] = len(context_features)` at :2520; `model_params = dict(…)` first binds at :2535 → function-local name → UnboundLocalError whenever the list is non-empty (if the spec plumbing were fixed). Zero tests reference context_features; LSTM-side support exists and validates (lstm.py:896-902).
- Why it matters: a documented SequenceConfig field is a silent no-op today, and each of the two "fixes" a future dev would naturally make first (plumb the spec, or use the field) triggers the crash or a silent multi-GPU no-op.
- Recommended fix: move the model_params assignment above the context block (or defer the context_dim write); either plumb context_features through the spec + `_execute_fold`, or delete the block and the config field until supported; add one unit test.
- Effort: small · Risk if changed: none — enables a currently-crashing path.

#### [H16] `to_yaml` is a lossy snapshot: the archived reproducibility record drops horizon_overrides, base_model, sequences, feature_selection, conditional_duan, embargo
- Dimension: maintainability · Severity: HIGH · CONFIRMED
- Location(s): `config.py:688-812` (to_yaml, the D(21) hotspot) vs `from_yaml` at `:594-686`; snapshot written at `utils/persistence.py:56-59`
- Evidence: from_yaml reads horizon_overrides (:668), sequences (:669), base_model (:670-678), feature_selection (:680), fold_cache_* (:682-683), conditional_duan (:685), tuning.n_jobs/n_workers/tune_every_n_folds (:642-644), cv.embargo; to_yaml writes none of them.
- Why it matters: re-running an experiment from its saved `data/models/{name}/config.yaml` silently reproduces a *different* experiment — an LSTM+base_model residual run loses base_model and sequences entirely. For a project whose deliverable is trial comparisons, the archived configs are unreliable evidence.
- Recommended fix: replace the hand-rolled dict with `dataclasses.asdict` + a small exclude/transform table (Path→str), and add a round-trip property test `from_yaml(to_yaml(cfg)) == cfg` over a config exercising every optional section. Kills the D(21) complexity and the drift class at once.
- Effort: medium · Risk if changed: `cli/audit.py`'s YAML diff tooling may need key-order/None handling checks.

#### [H17] `evaluation/_parallel.py` annotations are provably stale (3-tuple declared, 4 returned; parameter shadowed) — the mypy gate is not enforced
- Dimension: maintainability · Severity: HIGH · CONFIRMED
- Location(s): `evaluation/_parallel.py:210` vs `:318`; `:349` vs `:388,575`; shadowing at `:481`; `pyproject.toml:72-76`; `../.pre-commit-config.yaml`
- Evidence: `_run_single_model_pooled` declares `tuple[str, dict, dict]` and returns 4 values; `run_models_pooled` declares a 2-tuple and returns 4; the loop at :481 rebinds the `models: list[str]` parameter to a dict. Default-strictness mypy flags wrong return arity; a mypy pre-commit hook exists — so it is being skipped or failing.
- Why it matters: anyone extending the pipeline's most concurrency-heavy module trusts the signature and unpacks wrong; mypy provides zero protection there.
- Recommended fix: correct both annotations (or a `PooledRunResult` NamedTuple), rename the loop target, and put `uv run mypy volforecast` in an enforced CI step.
- Effort: small · Risk if changed: enabling mypy in CI surfaces a pre-existing backlog to triage.

### MEDIUM

#### [M1] har_family.py: pipeline-builder helpers exist but 14 earlier model classes still inline identical sklearn pipelines (~250 removable lines)
- duplication · CONFIRMED · `models/har_family.py:918-959` (helpers) vs 10× `selection="random"` ElasticNet blocks (8 inline `__init__`s, the jscpd 27L×6 cluster)
- Why: helper-added-later, old-sites-never-migrated; a convergence fix to the helper misses 8 sites. Fix: mechanically route the inline pipes through `_make_{ridge,lasso,enet}_pipe` (move helpers above line 147). Effort: small · Risk: step-name stability for any pickled pipelines.

#### [M2] print_output_summary duplicated: `__main__.py` private copy is live; cli/console's "shared" copy has zero callers
- duplication + consistency (merged #7/#40) · CONFIRMED · `__main__.py:36-72` ↔ `cli/console.py:35-69` (identical 31 lines); calls at `__main__.py:661,694`
- Why: the copy that is dead is the documented canonical one — next restyle lands in the wrong file. Fix: delete the `__main__` copy, import from cli.console (edge already exists). Effort: trivial.

#### [M3] CVConfig manually serialized to dict in 3 files; all 3 field lists already drifted (missing `embargo`)
- duplication · ADJUSTED · `models/lightgbm.py:988-994`, `models/xgboost.py:994-1000`, `models/lstm_tuning.py:545-551` vs `config.py:183`
- Why: any CVConfig field added for tuning is silently zeroed in every HPO worker (latent today — inner-CV splitters don't read embargo yet). Fix: `dataclasses.asdict(cv_config)` ×3. Effort: trivial.

#### [M4] dashboard.py: 38-line GSVIVS row-styling loop duplicated inside one function
- duplication · CONFIRMED · `visualization/dashboard.py:345-381` ↔ `:399-435` (identical except final assignment target); the 16-key styled-row dict is the template contract
- Fix: extract `_style_gsvivs_rows(rows, model_colors, track_label)`. Effort: small.

#### [M5] Hand-rolled exponential-backoff fetch retry cloned 5× across data-fetch modules
- duplication · CONFIRMED · `data/marquee.py:160-196,474`, `data/edrvol.py:416-455,831`, `data/varswap_reconstruct.py:237` (leave `chunk_store._query_with_retry:289` — it adds timeout/thread logic)
- Why: retry policy (incl. blanket `except Exception` that retries bad-argument errors) must be fixed in five places. Fix: `data/_retry.py: fetch_with_retry(fn, *, retries, backoff, desc)`. Effort: small.

#### [M6] Test synthetic-data factories copy-pasted and drifting: `_make_synthetic_sequence` ×4, `_make_daily_panel` ×4, `synthetic_lgbm_data` ×3, plus a same-name fixture shadowed with different distributions
- duplication + consistency (merged #11/#46) · ADJUSTED ×2 · `tests/unit/test_lstm.py:36`, `test_tcn.py:46`, `test_lstm_tuning.py:28`, `test_lstm_optim.py:43`; `test_fold_cache.py:80`, `test_runner_blend.py:85`, `test_runner_residual.py:161`, `test_runner_sequences.py:74`; conftest fixture shadowing (`synthetic_rv_series` unit vs integration, different distributions)
- Why: SequenceTensor signature changes need 4 mechanical edits; the drifted epsilons (1e-3 vs 1e-4) mean "the same" synthetic regime subtly differs per file; the shadowed fixture changes meaning if a test moves tiers. Fix: promote parameterized factories into `tests/unit/conftest.py` (35 lines today); rename one of the shadowed fixtures; do NOT force the drifted defaults to converge blindly. Effort: medium.

#### [M7] Four hard dependencies (pypdf, plotly, tqdm, matplotlib) declared in pyproject with zero imports anywhere in src or tests
- bloat + consistency (merged #15/#47) · ADJUSTED ×2 · `pyproject.toml:16,18,21,24`; stale docstring at `visualization/__init__.py` claiming matplotlib output
- Why: ~85 MB of dead install per environment; the docstring misleads. Fix: delete the four dep lines, `uv lock`, fix the docstring (dashboard is Jinja2 HTML with embedded Plotly **JS**, not the plotly Python package). Effort: trivial.

#### [M8] 1,093 LOC of orphaned research modules kept alive only by 994 LOC of tests
- bloat · ADJUSTED · `evaluation/phase3_experiments.py` (511 LOC, 0 src importers), `data/varswap_reconstruct.py` (352), `data/gsvivs_kvar.py` (230-510, see M14)
- Why: unreachable from any shipped flow; their tests run on every CI pass; refactors must keep them compiling. Fix: per-module decision — wire gsvivs_kvar to a CLI (it produces a load-bearing cache), archive or delete the other two with their tests. Effort: medium.

#### [M9] Four stub ensemble classes (164 LOC) that only raise NotImplementedError, plus 113 LOC of tests asserting they don't work
- bloat · CONFIRMED · `models/ensemble.py:192-355` (7 raise sites), `tests/unit/test_ensemble.py`
- Why: unregistered landmines whose functionality now exists in blend.py/stacking.py under different names. Fix: delete lines 192-355 + the test file; keep `LightGBMBaggedSeeds` (real, registered); update the module docstring. Effort: small.

#### [M10] Three fully-stubbed CLI modules (155 LOC) never registered in the parser
- bloat · ADJUSTED · `cli/build_features.py`, `cli/notebook.py`, `cli/research.py`; `__main__._build_parser` registers 16 modules, none of these; `cli/__init__.py` docstring documents an obsolete "skills" architecture and nonexistent modules
- Fix: delete the three modules, fix the test import in `tests/unit/test_features.py:20`, rewrite the cli/__init__ docstring. Effort: trivial.

#### [M11] `build_tournament_dashboard` is a single 520-LOC function (F(81))
- bloat · CONFIRMED · `visualization/dashboard.py:48-567`
- Why: ~15 payload formats in one function; testable only via full-HTML string assertions. Fix: extract per-payload builders following the file's own existing pattern (`_build_stats:742`, `_build_vt_stats:802`, `_build_dh_stats:850`). Effort: medium.

#### [M12] `_parallel.py` bypasses `_model_utils` — the module created to break the tournament cycle — and re-creates the exact cycle via three deferred tournament imports
- organisation · ADJUSTED · `evaluation/_model_utils.py:3-4` (docstring names _parallel as consumer) vs `_parallel.py:115,217,378` (`import …tournament as _tournament`)
- Fix: import `resolve_model`/`feature_layers_for_model` from `_model_utils` top-level; move `_build_tournament_context` into _model_utils. Effort: small.

#### [M13] config.py depends upward on evaluation for `GsvivsSizingSpec`
- organisation · ADJUSTED · `config.py:21-27` (deferred, self-documented cycle dodge) ← `evaluation/economic_value.py:197,275`
- Why: config is imported by every layer; loading YAML can transitively import the 1,362-LOC economic_value. Fix: move the spec dataclass + parser into config.py (they are plain YAML parsing); economic_value imports them from config — edge flips to the correct direction. Effort: small.

#### [M14] `data/gsvivs_kvar.py` (510 LOC) — producer of a load-bearing cache — has zero production callers; reachable only from tests/REPL
- organisation · ADJUSTED · `data/gsvivs_kvar.py:402` produces what `data/edrvol.py:1080-1113` consumes (`gsvivs_kvar_daily.parquet`); `cli/kvar.py` doesn't import it
- Why: a fresh checkout cannot regenerate the cache without knowing to call a function from a REPL. Fix: add a `vol kvar-extract` subcommand in cli/kvar.py (verifier note: keep the two caches' naming straight — see its correction on cache conflation). Effort: small.

#### [M15] `utils/persistence.py` is experiment-artifact logic, not a utility; its annotation-only config import is all that makes utils non-leaf
- organisation · CONFIRMED · `utils/persistence.py:17` (top-level `from volforecast.config import ExperimentConfig`; file has `from __future__ import annotations`, all 11 uses annotation-only)
- Fix: wrap in `if TYPE_CHECKING:` (2-line change → utils becomes a true leaf); optional follow-up: move persistence.py to pipeline/ next to fold_cache (its only callers). Effort: trivial.

#### [M16] `data/iv_features.py` trains a HAR-CJ model inside the data layer
- organisation · CONFIRMED · `iv_features.py:29,55-62` (`ensure_registered()`, fits `HARCJModel`) — the data→models/registry edges
- Fix: move `_har_expected_rv` into features/ (options.py or a new vrp.py); `build_iv_feature_panel` accepts the expected-RV series as a parameter. Effort: medium.

#### [M17] Two console channels inside the CLI: shared rich stderr Console (35 calls/8 files) vs bare stdout `print()` (85 calls/12 files), plus a rogue second Console in evaluation
- consistency · ADJUSTED · `cli/console.py:15` (mandates the singleton) vs print()-heavy `cli/experiment.py` (28), `cli/audit.py`, `cli/cache.py`, `cli/forecast.py`; `evaluation/tournament_dashboard.py:316` builds its own Console
- Why: `vol audit > report.txt` captures half the output; raw stdout during live Progress garbles bars (the exact failure console.py's docstring warns about). Fix: convert CLI print() to `console.print`; route tournament_dashboard through the shared instance. Effort: small.

#### [M18] Deprecated path aliases (`rv_cache_*`, `macro_*`) still used at 16 call sites alongside canonical names
- consistency · ADJUSTED · `utils/paths.py:126-143` (deprecation notes) vs 16 non-definition call sites in 7 files incl. `utils/persistence.py:227`, `evaluation/tournament.py:387`
- Why: grep for the canonical name misses half the readers/writers; aliases can never be deleted. Fix: mechanical rename ×16, then delete paths.py:126-143. Effort: trivial.

#### [M19] Three competing root/dir-resolution mechanisms beside utils/paths.py
- consistency · CONFIRMED · `cli/experiment.py:16` (`parents[3]`), `cli/gap_detector.py:17-24` (hardcoded data/raw subdir map), `constants.py:385` (dead relative constant) vs `paths.resolve_project_root()`
- Why: the layout already migrated once (rv/→ticks/); gap detection keeps scanning old dirs because its map is independent. Fix: point both at paths helpers; delete the dead constant. Effort: small.

#### [M20] 5-min sequence tensors bypass the .pt cache and re-read + re-aggregate the full 10s parquet every run (plus a 40-line clone between the two builders)
- optimisation · ADJUSTED · `data/sequence_cache.py:582-636` (cache covers only the 10s path) vs `pipeline/runner.py:2353,2365` calling the two uncached 5-min builders (near-identical prologues at sequence_cache.py:360/468)
- Why: hot path — every sequence tournament and HPO worker re-reads ~6.3M rows/symbol at startup. Fix: extract `_load_5min_frame(…)` and route both builders through `load_sequence_tensor` dispatching on `source`. Effort: medium.

#### [M21] `vol ingest-micro` recomputes full-history daily aggregates and rewrites caches even when zero new days were fetched
- optimisation · CONFIRMED · `data/micro.py:1189-1193` (logs "…skipping" but does NOT return) → full parquet load + `groupby("date")` over ~2,700 days + cache rewrite (:1232-1264)
- Why: hot path — the CLI threads this over ~30 symbols; a refresh that fetched 0-1 days pays the full-history cost per symbol. Fix: early-return when `remaining_days` empty and caches exist; compute daily rows only for new days otherwise. Effort: small.

#### [M22] Per-symbol tournament mode serializes independent (model × symbol) training with no parallel dispatch at all
- optimisation · CONFIRMED · `evaluation/tournament.py:389→396→418` (nested serial loops); `_run_tournament_per_symbol` doesn't even accept `parallel_models`
- Why: hot when used — 10 models × 20 symbols = 200 independent CV training runs on one core-group. Fix: dispatch pairs through a ProcessPoolExecutor mirroring `_run_single_model_pooled`. Effort: medium.

#### [M23] Error handling: 118 broad `except Exception` sites; the worst silently degrade research outputs
- maintainability · ADJUSTED · census: 118 sites/42 files, 0 bare except, 6 `except Exception: pass`. Worst: `features/iv_surface.py:133-136,146-149` (0DTE/1DTE IV — "core signal for GSVIVS01" — vanish with NO logging); `models/xgboost.py:797` + `lightgbm.py:817` (every training exception relabeled `optuna.TrialPruned`, zero per-trial logging — a broken objective looks like "all trials pruned"); `evaluation/tournament_dashboard.py:304`; `tournament.py:815`
- Why: features/economics that silently disappear change conclusions without changing exit codes. Fix: log-before-fallback at the five cited sites; count consecutive pruned-by-exception trials and abort the study after N. (Verifier: most of the 118 are a legitimate log-and-continue ingest convention — do not blanket-change them.) Effort: small.

#### [M24] `_run_one_horizon_sequences` is a 711-line method mixing 6 concerns; only 3 end-to-end tests cover it
- maintainability · ADJUSTED · `pipeline/runner.py:2424-3134`: tensor assembly (2444-2496), context (2498-2520), Optuna HPO with its own mp.Manager + consumer thread (2603-2702), multi-GPU dispatch with another (2712-2824), sequential folds (2828-3099), aggregation
- Why: no unit is testable in isolation — which is exactly why H15's crash survived. Fix: covered by B3 + H7 (use `_execute_fold`, extract `_build_sequence_rows` and `_run_sequence_hpo`). Effort: medium (subsumed by strategic package 2).

#### [M25] `lru_cache` on parquet loaders caches a missing-file empty DataFrame for the process lifetime; module-global `_iv_context_cache` has no invalidation
- maintainability · CONFIRMED · `features/implied_correlation.py:44-63`, `features/realized_correlation.py:141`, `evaluation/tournament.py:34`
- Why: a tournament racing an ingest permanently disables the correlation feature layers for that process with a single warning. Fix: don't cache failure (exists() check outside the cached function, or key on (path, mtime_ns)). Effort: small.

#### [M26] `cli/audit.py` dual entry points drifted: registered `vol audit` always exits 0; the module path exits 1 on critical issues
- gap-sweep · CONFIRMED · `audit.py:828-833` (return discarded, `no_journal` not passed, unconditional `return 0` at :883) vs `main()` (:770-794)
- Why: automation gating on the documented CLI's exit code passes even on CRITICAL integrity violations. Fix: replicate main()'s has_critical check in handle(); reduce main() to argparse delegation. Effort: trivial.

#### [M27] `vol audit --fix` gap-detection window hardcoded to end 2025-01-03; project-root fallback is a foreign-machine absolute path
- gap-sweep · ADJUSTED · `audit.py:865-867` (comment promises manifest-based detection; literals hardcoded), `audit.py:94` (`Path("/home/developer/ml-vol-estimator")` — actually fires on this Windows copy)
- Why: ~18 months of recent missing days are invisible to the freshness tool. Fix: derive the range from the manifest, `end=date.today()`; replace `_find_project_root` with `utils.paths.resolve_project_root()`. Effort: small.

#### [M28] `GNNVolModel` accepts, stores, and persists `n_layers` but the network is hardcoded 2-layer; `batch_size`/`grad_accumulation_steps` are no-ops on the default path
- gap-sweep · CONFIRMED · `models/gnn.py:207,231` vs `_build_module:262-269` and `_GATModule.__init__:95-107` (conv1+conv2 unconditional); no-op params on the ≤10k-graphs path (:347); persisted arch summary lies (:696,727,750)
- Why: an n_layers sweep trains identical models per trial and the saved payload claims otherwise. Fix: implement n_layers or `raise ValueError` for ≠2; log that batch params are ignored on the pre-batched path. Effort: small.

### LOW

#### [L1] US equity session boundaries (9:30/16:00 ET) hardcoded 15+ times in 4 modules using 3 representations
- duplication · CONFIRMED · chunk_store.py, micro.py, backfill_rk.py (`TZ.localize(datetime(…, 9, 30, 0))` ×8), resample.py (`"09:30"` strings), dt_time filters — Fix: `MARKET_OPEN/MARKET_CLOSE` in constants.py + `session_bounds(day)` helper. Effort: small.

#### [L2] Smaller intra-module clones: resample.py 19-key RV-measure dict ×2 (documented same-keys contract), sequence_cache 45-line load prologue ×2, runner eval-tail ×2, progress Progress-ctor ×2
- duplication · CONFIRMED · `resample.py:159-179` vs `251-271` is the sharpest (a new measure added to one path breaks the documented contract). Fix: extract per-file helpers. Effort: small.

#### [L3] Confirmed dead-code cluster: unused import + two vestigial parameters
- bloat · ADJUSTED · `pipeline/conditional_duan.py:34` (unused `conditional_duan_correction` import), `evaluation/_parallel.py:323` (`ml_model_names` never read; caller computes it for nothing), `cli/backfill_rk.py:505`. Remaining vulture hits were verified false positives (stub signatures). Effort: trivial.

#### [L4] `tests/slow/` is empty scaffolding (6 LOC conftest, zero tests) contradicted by the marker-based mechanism that actually works
- bloat · CONFIRMED · Fix: delete the dir, drop `--ignore=tests/slow` from addopts. Effort: trivial.

#### [L5] `economic_value.py` ↔ `realistic_straddle.py` import each other at five deferred sites; `compute_sharpe` is trapped on one side
- organisation · CONFIRMED · ev:1037,1086 ↔ rs:587,694,835 — Fix: move compute_sharpe (+ symmetric primitives) to the relocated metrics leaf (H9) or `evaluation/pnl_stats.py`. Effort: small.

#### [L6] visualization imports underscore-private `evaluation._model_utils` cross-package
- organisation · ADJUSTED · `dashboard.py:952` — Fix: rename to `model_utils.py` (already de facto public), update 4 importers. Effort: trivial.

#### [L7] Stray top-level unit tests + stale cli/__init__ docstring
- organisation · ADJUSTED · `tests/test_gnn_adjacency.py`, `tests/test_gnn_model.py` (self-described unit tests outside the tier system) — Fix: `git mv` into tests/unit/; rewrite the docstring. Effort: trivial.

#### [L8] Market-wide IV/EDRVS parquet loaders un-memoized inside per-symbol × per-horizon loops
- optimisation · CONFIRMED · `tournament.py:509,517` (same EDRVS file read symbols×horizons times; also mutated in place at :521), `edrvol.py:1057,335` — Fix: `@lru_cache(maxsize=1)` on `load_edrvs_cache` + wrapper for market-wide symbols (respect M25's don't-cache-failure rule). Effort: trivial.

#### [L9] `fit_seq_normaliser` materializes ~4 full-size float64 temporaries of the training tensor every fold
- optimisation · CONFIRMED · `sequence_cache.py:684-689`, called per fold from both paths — ~6 GB transient for a 0.75 GB f32 train subset. Fix: masked_fill_ on one working copy + `sum(dtype=torch.float64)` accumulation. Effort: small.

#### [L10] Registry onboarding trap: hand-maintained import list; GNN ImportError silently passed
- maintainability · ADJUSTED · `registry.py:11-46` (23 imports; gnn's guard swallows the reason) — Fix: warn-level log in the ImportError handler; a test asserting every `@register_*`-decorated module is in the list. Effort: trivial.

#### [L11] `LSTMVolModel.fit` prints a stdout banner via a mutable class-level flag
- maintainability · ADJUSTED · `lstm.py:1040-1049` — corrupts stdout around the Rich UI; flag leaks across experiments in one process. Fix: `logger.info` once per instance. Effort: trivial.

#### [L12] Permanently-skipped test cites a bug that has since been fixed; the metrics.json output contract has zero coverage
- gap-sweep · ADJUSTED · `tests/integration/test_tournament_characterization.py:286-289` (skip message describes a TypeError that no longer exists — both call sites fixed) — Fix: un-skip and finish the body (decorators already in place), or delete. Effort: trivial.

#### [L13] test_models.py: 14 (+3) copy-pasted "uses N features" methods (~150 lines) that are one parametrized case
- gap-sweep · ADJUSTED · `tests/unit/test_models.py:185-403` — Fix: one `@pytest.mark.parametrize((model_cls, expected_features))`; keep the two behavioral tests. Effort: small.

#### [L14] FOMC calendar hardcoded through 2026-12-16 with a silent constant-30 fallback
- gap-sweep · CONFIRMED · `features/calendar.py:142,244-245` — six months from expiry; features degrade to constants with no warning. Fix: one-time warning on None; a test asserting the table covers the current year. Effort: trivial.

---

## 4. Quick-wins checklist (ROI-ordered; each ≤15 min)

1. **[B5]** `config.py:515-521`: add `embargo=cv_override.get("embargo", self.cv.embargo)` + the one-line to_yaml write + unit test — retires a BLOCKER with a 3-line diff.
2. **[B1]** Port `xgboost.py:622-626` (init-only re-merge) into `LightGBMVolModel.tune_and_fit` — retires a BLOCKER.
3. **[H5]** `git rm --cached` the 21 MB of artifacts; extend `.gitignore` (`.coverage`, `src/workspace/tmp/`).
4. **[H13]** `@lru_cache(maxsize=8)` on `edrvol._fetch_expiry_iv` — ~100× fewer Marquee calls per tournament.
5. **[H15]** Move the `model_params` assignment above the context block in `runner.py:2498-2535` (crash → working or explicit error).
6. **[M2]** Delete `__main__._print_output_summary`; import the cli/console version at the two call sites.
7. **[M7]** Delete pypdf/plotly/tqdm/matplotlib from `[project].dependencies`; `uv lock`; fix the visualization docstring.
8. **[M3]** Replace the three hand-rolled CVConfig dicts with `dataclasses.asdict(cv_config)`.
9. **[M15]** Wrap `persistence.py:17` in `if TYPE_CHECKING:` — utils becomes a true leaf.
10. **[M26]** `cli/audit.py handle()`: propagate `run_audit`'s result to the exit code; pass `no_journal` through.
11. **[chunk_store]** Delete the silently-ignored `exchange` param from `fetch_trades` (`data/chunk_store.py:208-273`) — a data-correctness trap for future callers *(from M-tier finding #23)*.
12. **[M18]** Mechanical rename of the 16 deprecated path-alias call sites; delete the aliases.
13. **[L8]** `@lru_cache(maxsize=1)` on `load_edrvs_cache`.
14. **[M10]** Delete the three stubbed CLI modules + fix the one test import.
15. **[L3]/[L4]** Dead-code cluster + `tests/slow/` removal.
16. **[H17]** Fix the two stale annotations + the shadowed variable in `_parallel.py`.
17. **[L14]/[L10]/[L11]/[L12]** One-line logging/warning/unskip fixes.

*(Not quick, but do before any refactor: bump the fold-cache `fp_version` (B4) — several fixes above legitimately change results, and stale cache hits would mask them.)*

---

## 5. Strategic recommendations

### Package 1 — Kill the drifted twins (B1, B2, B3, H1, H6) — highest leverage
**Rationale:** four BLOCKERs share one root cause: parallel implementations that drift. Fixing symptoms without unifying guarantees recurrence.
**Migration path (each step gated on `check-regressions.sh`):**
1. Land the two behavior fixes (B1, B2) as standalone diffs — results legitimately change; baseline them.
2. Unify fold execution (B3): sequential branch calls `_execute_fold`; add symbol_to_id/context to the worker; pick one seed policy; bump fold-cache `fp_version` in the same commit.
3. Extract `models/_gbm_common.py` mixin (H1) mechanically — keep attribute names for pickle compatibility; diff QLIKE outputs against baseline.
4. Extract `models/_seq_train.py` + move TCN to `models/tcn.py` (H6) — preserve op ordering (seed-sensitive).
**Risk if left alone:** every future model-layer fix has a coin-flip chance of landing in one copy; two research-corrupting no-ops already shipped this way.

### Package 2 — Experiment integrity (B4, B5, B6, H16, M3)
**Rationale:** the project's deliverable is trial comparisons; today the fingerprint, the embargo, the archived config, and the output tree can all silently lie.
**Migration path:** (1) B5 quick win; (2) fingerprint v2 with the missing fields + parametrized drift test (B4); (3) asdict-based `to_yaml` + round-trip test (H16, kills the D(21) function); (4) anchor `output_dir` at load time and derive `experiment_dir()` from it (B6) with a one-time artifact-tree migration note.
**Risk if left alone:** any past or future trial comparison involving sequence-config changes, horizon overrides, or archived-config re-runs is suspect.

### Package 3 — Dismember runner.py (H7, H12, M24; enables testing everything else)
**Migration path:** (1) after Package 1 step 2, the sequence path is ~250 lines lighter; (2) extract `pipeline/feature_stack.py` (three factories → free functions over (config, panel_data)); (3) extract `pipeline/sequence_runner.py`; (4) collapse the 8-way fit/predict dispatch into the kwargs-dict pattern and add fit/predict to `_BaseModel` (H12). runner.py lands at ~1,480 LOC; integration tests are the gate at each step.
**Risk if left alone:** the F(90) method keeps eating every new model path; defects like H15 keep shipping because nothing in it is unit-testable.

### Package 4 — Layering & single-sources (H8, H9, H10, B7, B8, M12–M19, H4, L1)
**Rationale:** the tree is one consistent layer architecture away from a clean DAG; every edge has a small, named cut.
**Migration path (all independent, do in any order):** metrics.py → `volforecast/metrics.py` + shim (H9) · templates → visualization/ + reporting decision (H10) · TYPE_CHECKING persistence (M15) · GsvivsSizingSpec → config (M13) · unified `add_subtask` (B7) · `_har_expected_rv` → features/ (M16) · lazy torch + guarded registry import (H8) · one symbol universe in constants + drift test (B8) · `TRADING_DAYS_PER_YEAR`, session bounds, `atomic_to_parquet`, `fetch_with_retry`, `cache_covers_range` single sources (H4, L1, H11, M5, H3).
**Risk if left alone:** each future feature pays the copy-tax; the dependency matrix keeps inviting someone to delete the package that holds the live dashboard template.

### Performance (opportunistic, after Package 3): H13/H14 (feature-build hoisting + fetch memoization: ~3× the feature phase and ~100× fewer network calls), M20 (5-min cache), M21 (ingest early-return), M22 (per-symbol parallelism), L8/L9.

### Proposed target tree

```
volforecast/
├── __main__.py            # arg parsing + dispatch only (no business logic, no cloned helpers)
├── config.py              # + GsvivsSizingSpec; asdict-based to_yaml; anchored output_dir
├── constants.py           # + TRADING_DAYS_PER_YEAR, MARKET_OPEN/CLOSE, THE symbol universe (only copy)
├── metrics.py             # ← moved from evaluation/ (pure-numpy leaf; qlike/mse/r2 + compute_sharpe)
├── registry.py            # unchanged pattern (lazy, sound); guarded heavy imports; warn on ImportError
├── utils/                 # true leaf: paths, cv, manifest, io.py (atomic_to_parquet)
├── data/                  # ingestion + caches only; _ingest_common.py, _retry.py; no cli/model imports
├── features/              # + vrp.py (HAR-expected-RV moved from data/iv_features)
├── models/                # _base.py (fit/predict contract), _gbm_common.py, _seq_train.py,
│                          #   lightgbm.py, xgboost.py, lstm.py, tcn.py (split), har_family.py (helpers used)
├── pipeline/              # runner.py (~1,480), feature_stack.py, sequence_runner.py, fold_cache.py,
│                          #   persistence.py (← from utils/)
├── evaluation/            # tournament (TournamentOptions), economics; model_utils.py (public)
├── visualization/         # dashboard.py (payload builders) + templates/ (← from reporting/)
└── reporting/             # DELETED or implemented — not a stub
tests/
├── unit/                  # + shared factories in conftest; stray GNN tests moved in; slow/ deleted
└── integration/
```

---

## 6. Coverage report

**Measured (tools run):** LOC via `wc`/`find` (full tree) · duplication via jscpd v-latest, min-tokens 70, 114 files scanned · complexity via radon cc (full volforecast) · dead code via vulture ≥80% confidence · import graph + SCCs via custom AST analysis (all 130 modules) · tracked-artifact sizes via `git ls-tree -l` · debt markers, error-handling census, print/console/parquet/type-hint counts via grep with spot-read verification. **Approximated/unavailable:** git churn × complexity (single-snapshot history — impossible); mypy/pytest execution (analysis-only constraint; mypy non-enforcement inferred from provably stale annotations + existing hook config); bundle analysis (n/a, no client).

**Deep-read coverage (6 finder agents + gap-sweep + 77 verifier passes; every cited line independently re-read):** read fully — lightgbm.py, xgboost.py (~90%), config.py, constants.py, registry.py, `_parallel.py`, fold_cache.py, persistence.py, paths.py, `_base.py`, `__main__.py`, ensemble/blend, reporting/*, console/progress, gnn.py, cli/audit.py, calendar.py, all `__init__`s, pyproject, both conftests; read in large targeted sections — runner.py (~1,300/3,134 directly + all cited ranges re-verified), lstm.py, har_family.py, tournament.py, sequence_cache.py, micro.py, edrvol.py, rv_panel.py, economic_value.py/realistic_straddle.py (function inventories + clone regions), dashboard.py, ingest modules, ~15 test files.

**Skipped / lower confidence:** features/ internals beyond grep hits and the cited layers (2,969 LOC — the healthiest package by every measure taken); `evaluation/gsvivs.py` internals beyond its clone region — **its F(79) `compute_gsvivs_stats` was never deep-read and remains the largest un-audited complexity hotspot**; chunk_store.py:400-800; tsdb/ohlcv ingest internals; most golden/research test bodies; HTML templates (except 252-grep). The `ml-vol-estimator/` and `qr-decode/` snapshot copies were out of scope (though one verifier cross-checked that B8's universe drift exists in all four copies — not a restore artifact).

**Hypotheses (stated as such, not findings):** micro.py `ingest_symbol_micro` F(44) and xgboost `tune_hyperparameters_xgb` F(57) god-function splits were flagged by radon but not independently deep-read by the bloat pass — treat the numbers as real, the split design as unvalidated. `compute_gsvivs_stats` F(79) likewise.

**Notable non-findings (checked, clean — reported so you don't re-audit them):** the registry's 26-module "cycle" is deferred-import-only and benign by design; CLI startup is clean (`__init__` is 8 lines, `__main__` defers everything); zero `os.environ` reads anywhere — config discipline is genuinely good; `sys.exit` confined to entry points; error handling in ingest follows a consistent log-and-continue convention; no commented-out code blocks; no `__init__.py` over-exports; type-hint coverage is uniform (mypy is configured loose but consistently so); economic_value vs realistic_straddle are distinct methodologies, not drifted duplicates; Phase 0's "cli/console has 15 non-CLI importers" claim did **not** survive verification (only 2).

**Verification integrity:** all 77 raw findings passed adversarial re-derivation (44 CONFIRMED exactly; 33 ADJUSTED — typically severity recalibration or line-drift corrections, folded in above; 0 REFUTED). B2's "no-op reweighting" was confirmed **empirically** (xgboost 3.3.0, scratch venv, extreme-weights experiment), not just from source.
