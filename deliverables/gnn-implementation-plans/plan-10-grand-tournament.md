# Plan 10 — The Grand GNN Tournament + Evaluation Hardening

> **For the Copilot orchestrator:** execute with `/execute` (§7). TDD hard gate for code tasks. Requires Plans 01–09 merged and trials 080/082 interpreted. This plan turns seven graph models into one defensible results chapter: turbulence-split metrics, graph diagnostics in the dashboard, the full tournament, and the skeptic's-checklist sign-off.

**Goal:** (1) Harden evaluation with the two conditional breakdowns the literature demands — **turbulence-split QLIKE** (top-decile SPY-RV dates, GNNHAR Table 2 protocol) and **median-split conditional DM** (Fang & Ślepaczuk Table 4 protocol); (2) surface **graph diagnostics** (density/Jaccard time series, attention-spillover heatmap, graph signal energy) in the tournament dashboard; (3) run the **grand tournament** — every model × the winning graph × h ∈ {1,5,22} on 8 GPUs; (4) close the program with the **skeptic's-checklist review** and capstone-ready artifacts.

**Research grounding:** The audit table's lesson (chapter §9): "the further a paper's headline gain is from the GNNHAR lineage's careful single digits, the thinner its evaluation." Our defense is to pre-commit to the full checklist: rolling re-estimated HAR bar, STID control in the same table, Patton-QLIKE + panel-DM + 5% MCS, unsmoothed intraday RV target (already the repo's), PIT graphs stated explicitly, and the honest expected-gains table (~3–4% QLIKE at h=1, ~8% at h=5, ≈0 at h=22) printed next to whatever we find.

## Global constraints

As 00-overview §4.1. Plan-specific:
- New metric columns are **additive** — existing `tournament_table` columns and `metrics.json` schema keep byte-compatible ordering (characterization tests on the golden files in `src/tests/data/tournament_golden/` must stay green).
- The turbulence split uses **SPY RV from the panel data** (top-decile of the pooled test-period dates), computed once per horizon table; dates without SPY fall back to the cross-sectional mean RV (logged).

## File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/volforecast/evaluation/statistical_tests.py` | `conditional_qlike_split`, conditional DM |
| Modify | `src/volforecast/evaluation/tournament.py` + `aggregate.py` | new columns → table + `metrics.json` |
| Modify | `src/volforecast/evaluation/tournament_dashboard.py` | graph-diagnostics + spillover panels |
| Create | `src/tests/unit/test_conditional_metrics.py` | unit tests |
| Create | `workspace/configs/trial_090_gnn_grand_tournament.yaml` | the headline run |
| Create | `workspace/research/gnn-program-review.md` | skeptic's-checklist sign-off |
| Modify | `workspace/docs/user-manual.md` | "Graph models" section |

---

## Task 1: Turbulence-split QLIKE + conditional DM

**Copilot context packet:**

```yaml
subtask_id: "gnn-10-1"
goal: "Add conditional_qlike_split (calm/turbulent QLIKE by top-decile market-RV dates) and conditional panel-DM (median-split and top-25% buckets) to statistical_tests.py; wire qlike_turb/qlike_calm/dm_p_turb columns into tournament_table and metrics.json additively; golden-file characterization stays green."
file_scope:
  - workspace/plans/gnn/plan-10-grand-tournament.md      # Task 1: protocol + signatures
  - src/volforecast/evaluation/statistical_tests.py      # tournament_table (465+), DM (21+)
  - src/volforecast/evaluation/tournament.py             # _compute_horizon_table (778+)
  - src/volforecast/evaluation/aggregate.py
  - src/tests/integration/test_tournament_characterization.py
write_scope:
  - src/volforecast/evaluation/statistical_tests.py
  - src/volforecast/evaluation/tournament.py
  - src/volforecast/evaluation/aggregate.py
  - src/tests/unit/test_conditional_metrics.py
acceptance_criteria:
  - "./vol test -k test_conditional_metrics -> pass"
  - "./vol test -k test_tournament_characterization -> STILL GREEN (columns appended, none reordered/renamed)"
  - "conditional_qlike_split on synthetic data with a planted turbulent-only edge: model A beats B in qlike_turb but not qlike_calm (the test constructs this)"
  - "Conditional DM uses the SAME panel-aware date-averaged HAC machinery as the unconditional test (n_cross_sections plumbed)"
constraints:
  - "TDD failing-first"
  - "Signatures: conditional_qlike_split(y_true, y_pred, dates, market_rv, quantile=0.9) -> {'qlike_calm', 'qlike_turb', 'n_turb'}; conditional_dm(loss_a, loss_b, dates, market_rv, split='median'|'q75', horizon=1, n_cross_sections=None) -> dict"
  - "market_rv is a date-indexed Series; bucket membership decided on DATES (all symbols of a date share a bucket)"
  - "Protocols cited in docstrings: Zhang et al. 2025 Table 2 (top-decile SPY-RV); Fang & Slepaczuk 2026 Table 4 (median + top-25% buckets)"
context_summary: |
  Two published conditional protocols become first-class outputs so every trial's 'is the gain
  turbulence-concentrated or broad-based?' question is answered mechanically. tournament.py
  already aligns per-date panels in _compute_horizon_table — pull SPY rv from the loaded panel
  there and pass it down. metrics.json gains the new keys per model/horizon (additive).
depends_on: []
```

Commit — `feat(eval): turbulence-split QLIKE and conditional DM (GNNHAR/Fang protocols)`

## Task 2: Graph diagnostics + spillover panels in the dashboard

**Copilot context packet:**

```yaml
subtask_id: "gnn-10-2"
goal: "Add two dashboard panels for graph experiments: (a) graph-quality time series (density, consecutive-refit Jaccard, graph signal energy) from the experiment's schedule; (b) attention-spillover heatmap from spillover_matrix when the winning model exposes it; plus persistence of both artifacts next to metrics.json."
file_scope:
  - workspace/plans/gnn/plan-10-grand-tournament.md
  - src/volforecast/evaluation/tournament_dashboard.py    # generate_dashboard structure
  - src/volforecast/graphs/diagnostics.py                 # schedule_stability, energy_series
  - src/volforecast/models/gnn.py                          # spillover_matrix (Plan 05)
  - src/volforecast/pipeline/runner.py                     # where the schedule lives (_run_one_horizon_graphs)
write_scope:
  - src/volforecast/evaluation/tournament_dashboard.py
  - src/volforecast/pipeline/runner.py                     # persist schedule stats to output_dir
  - src/tests/unit/test_dashboard_graph_panels.py
acceptance_criteria:
  - "./vol test -k test_dashboard_graph_panels -> pass"
  - "Runner writes {output_dir}/graph_diagnostics.parquet (schedule_stability + energy per refit) for graph experiments; dashboard renders it when present, silently skips when absent (non-graph experiments unchanged — characterization)"
  - "Spillover heatmap: NxN Plotly heatmap with symbol labels + the not-causal caveat in the subtitle"
constraints: ["TDD failing-first", "Dashboard tests assert on the Plotly figure dict structure, not rendered HTML", "No behavior change for non-graph experiments"]
context_summary: |
  Makes the two published failure modes visible per experiment: corr-graph crisis density
  explosion (Wade) and GLASSO refit instability (GNAR-HARX Jaccard < 0.8), plus GSP-HAR's
  energy diagnostic and the Plan-05 learned-spillover table. Runner persists the raw numbers;
  the dashboard only renders. The heatmap subtitle must carry: 'learned attention, co-moves
  with regimes — not identified causal spillovers'.
depends_on: []
```

Commit — `feat(eval): graph-quality and spillover panels in the tournament dashboard`

## Task 3: The grand tournament config

**Copilot context packet:**

```yaml
subtask_id: "gnn-10-3"
goal: "Create trial_090_gnn_grand_tournament.yaml — every graph model + controls + champions in one pooled tournament (winning graph, h=1/5/22, n_gpus 8, parallel_models 1, checkpointing on) — and register it with the honest expected-gains table in the hypothesis."
file_scope:
  - workspace/plans/gnn/plan-10-grand-tournament.md      # Task 3: full YAML
  - workspace/configs/trial_082_gnnhar_vs_ghar_stid.yaml
  - workspace/configs/trial_063_xgboost_champion.yaml
  - workspace/research/trials.yaml                        # winners of 080/082/083/084/085
write_scope:
  - workspace/configs/trial_090_gnn_grand_tournament.yaml
  - workspace/research/trials.yaml
acceptance_criteria: ["Config parses", "Model roster matches the registered winners (per-label params copied from their winning trial configs verbatim)", "trial-090 registered with the expected-gains table and COVID statement"]
constraints: ["Do NOT run vol run", "parallel_models: 1 (each GPU model owns all 8 GPUs via fold parallelism; HAR-family arms are instant)", "checkpoint_enabled: true and fold_cache_enabled: true — this run is long; resume must work", "baseline: har_iv (the strongest honest incumbent)"]
context_summary: |
  The headline table for the capstone. Roster: ewma, har, har_iv (baseline),
  ridge_har_cj_iv_0dte (best HAR-family from trial history), xgboost champion (trial_063
  params), lightgbm, ghar (winning graph), stid, gnnhar_1l, gnn (best attention arm from 083),
  dcrnn_har, gsp_har, gnn_learned. Interpretation: full tournament_table + turbulence split +
  MCS membership; the writeup contrasts findings against the expected-gains priors line by line.
depends_on: ["gnn-10-1"]
```

`trial_090_gnn_grand_tournament.yaml` core (scaffold as trial_082; universe/date_range/cv identical):

```yaml
name: trial_090_gnn_grand_tournament
n_gpus: 8
horizons: [1, 5, 22]
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar, vol_of_vol]
model: {name: gnnhar, params: {}}
graph:                        # trial_080 winner — placeholder glasso
  method: glasso
  input: returns
  window: 1000
  refit_every: 21
  min_history: 252
  node_features: [log_rv_d, log_rv_w, log_rv_m, signed_return_d, abs_ret_d,
                  log_rs_negative_d, log_jump_d, log_bpv_d, log_cont_d]
cv: {method: expanding_window, purge_gap: 10, train_size: 504, test_size: 126}
tournament:
  models: [ewma, har, har_iv, ridge_har_cj_iv_0dte, xgboost, lightgbm,
           ghar, stid, gnnhar_1l, gnn_best, dcrnn_har, gsp_har, gnn_learned]
  baseline: har_iv
  mcs_bootstrap: 10000
  parallel_models: 1
  model_configs:
    # per-label params copied VERBATIM from each model's winning trial config;
    # graph overrides per Plans 03-07 where the arm's graph differs from the default
    ...
checkpoint_enabled: true
fold_cache_enabled: true
training_mode: pooled
seed: 42
output_dir: data/models/trial_090_gnn_grand_tournament
```

Commit — `chore(config): trial_090 grand GNN tournament`

## Task 4: Skeptic's-checklist review + docs + program close-out

**Copilot context packet:**

```yaml
subtask_id: "gnn-10-4"
goal: "Write workspace/research/gnn-program-review.md mapping every skeptic's-checklist item to concrete evidence (test names, config lines, trial verdicts), add a 'Graph models' section to workspace/docs/user-manual.md, and append the program summary to research-journal.md + weekly-progress.md."
file_scope:
  - workspace/plans/gnn/plan-10-grand-tournament.md      # Task 4: checklist template
  - workspace/plans/gnn/00-overview.md
  - workspace/research/trials.yaml
  - workspace/research/research-journal.md
  - workspace/docs/user-manual.md
write_scope:
  - workspace/research/gnn-program-review.md
  - workspace/docs/user-manual.md
  - workspace/research/research-journal.md
  - workspace/research/weekly-progress.md
acceptance_criteria:
  - "Review answers all six checklist items with file/test/trial pointers (no vague claims)"
  - "User-manual section documents: how to add a graph model, the graph: config block, per-label overrides, GPU knobs, warmup contract"
  - "Weekly-progress entry in plain language (no acronyms/function names)"
constraints: ["Docs task: TDD exempt", "Every claim in the review must cite its evidence (test path, config line, or trials.yaml verdict) — 'evidence over assumption' is the whole point of this document"]
context_summary: |
  The chapter's acceptance gate, item by item: (1) rolling re-estimated HAR bar - trial_090
  baseline har_iv + rolling folds; (2) STID control in the same table; (3) QLIKE + DM + 5% MCS
  - tournament_table columns; (4) unsmoothed intraday RV target - forward_log_rv over 5-min RV;
  (5) graph/scaler information sets stated - PIT tests in Plans 01/02/09 + this review's table;
  (6) economics - dh/vt enrichments exist for a follow-up (note as next-phase, not claimed).
  Close with the expected-vs-found table and the 20%-rule sanity note.
depends_on: ["gnn-10-3"]
```

Commit — `docs(research): GNN program skeptic's-checklist review + user-manual graph section`

## 7. Orchestrator prompt

```
/execute Implement Plan 10 (grand tournament + evaluation hardening) from workspace/plans/gnn/plan-10-grand-tournament.md
Precondition: Plans 01-09 merged; trials 080 and 082 have verdicts in trials.yaml (if not,
stop and report — this plan interprets winners).
Waves: (gnn-10-1, gnn-10-2 in parallel, max 2) -> gnn-10-3 -> gnn-10-4.
Golden-file characterization (test_tournament_characterization) must be green after every
eval-layer change — treat a golden diff as a defect, never regenerate goldens without
explicit user approval.
TDD; ./vol only; return contracts. Integration: ./vol test-all, lint, typecheck.
Print the trial_090 launch command with a wall-clock warning; do NOT run.
Final report: the program-close summary with numbered next steps (run 090, interpret,
economics follow-up).
```

## Acceptance gate (program close)

- Conditional metrics + dashboard panels shipped without golden regressions.
- trial_090 registered and launchable; checkpoint-resume verified on a small dry slice.
- `gnn-program-review.md` answers all six checklist items with evidence pointers.
- The user runs trial_090 (`./vol run --config workspace/configs/trial_090_gnn_grand_tournament.yaml --skip-ingest`), then `/experiment interpret` logs verdicts. Follow-ups queued for a future program: economic-value enrichment of the GNN winner (dh straddle/vol-targeting), covariance-forecasting recast (GHAR JFEC lineage — the strategic fork), evolving adjacency (EMGNN), cross-asset ETF nodes with asynchronicity discipline.
