# GNN Program — Skeptic's-Checklist Review

**Date:** 2026-07-18
**Scope:** Plans 01–10 of the GNN expansion for ml-vol-estimator (per [workspace/plans/gnn-implementation-plans/00-overview.md](../plans/gnn-implementation-plans/00-overview.md)).
**Audit source (§9 lesson):** *"the further a paper's headline gain is from GNNHAR lineage's careful single digits, the thinner its evaluation."* This document maps every skeptic-checklist item to concrete evidence in the repo (test path, config line, or [trials.yaml](trials.yaml) verdict). No claim without a citation.

**Program status:** Plans 01–10 shipped. Trial-094 (config: [trial_090_gnn_grand_tournament.yaml](../configs/trial_090_gnn_grand_tournament.yaml)) is registered as the headline pooled tournament (`status: NOT_STARTED`) — findings pending its run. The five graph-model gate trials that ran (trials 080–085) all landed inside the seed envelope of the `har_iv` baseline (1 bp at h=1, 0 bp at h=5, 1 bp at h=22). This review is the pre-run acceptance gate for the headline run.

---

## 1. Six skeptic's-checklist items — evidence table

Each subsection answers one item with **one file/test/config pointer per claim**.

### 1.1 Rolling re-estimated HAR bar (not a static fit)

The tournament's baseline is `har_iv`, re-estimated on every fold via an expanding-window walk-forward.

| Claim | Evidence |
|---|---|
| Baseline is `har_iv` (the strongest honest incumbent) | [trial_090_gnn_grand_tournament.yaml#L88](../configs/trial_090_gnn_grand_tournament.yaml#L88) — `baseline: har_iv` |
| CV is expanding-window walk-forward (never random k-fold) | [trial_090_gnn_grand_tournament.yaml#L71-L75](../configs/trial_090_gnn_grand_tournament.yaml#L71-L75) — `method: expanding_window`, `train_size: 504`, `test_size: 126`, `purge_gap: 10` |
| CV splits on unique dates with horizon-aware purge | Per [00-overview.md](../plans/gnn-implementation-plans/00-overview.md) §2 — `utils/cv.py::PanelExpandingWindowCV` splits on unique dates; `effective_purge = max(purge_gap, h)` |
| Every arm (HAR-family included) is retrained per fold | Runner refits per-fold before each test block: [src/volforecast/pipeline/runner.py#L1118](../../src/volforecast/pipeline/runner.py#L1118), [runner.py#L1323](../../src/volforecast/pipeline/runner.py#L1323), [runner.py#L1554](../../src/volforecast/pipeline/runner.py#L1554) |

**Verdict:** ✅ The HAR bar is rolling, not stale.

---

### 1.2 STID identity-embedding control in the same table

The "graph earns its keep" claim is stress-tested against pooling + asset identity alone. STID is a first-class tournament arm at every horizon.

| Claim | Evidence |
|---|---|
| STID is in the trial-094 roster | [trial_090_gnn_grand_tournament.yaml#L82](../configs/trial_090_gnn_grand_tournament.yaml#L82) — `stid` listed alongside every graph arm |
| STID is registered with `requires_graph = True` for harness parity | [00-overview.md](../plans/gnn-implementation-plans/00-overview.md) §4.4 interface ledger: `STIDVolModel` in `models/stid.py`, edges ignored, same fold loop |
| STID params match trial-083 gate run | [trial_090_gnn_grand_tournament.yaml#L132-L141](../configs/trial_090_gnn_grand_tournament.yaml#L132-L141) — `embed_dim: 16`, `hidden_dim: 64`, `loss: qlike` |
| Prior gate (trial-083) showed GNNHAR did not beat STID at 1 bp resolution | [trials.yaml#L3095-L3103](trials.yaml#L3095-L3103) — trial-083 `verdict: FAIL` at h=1/5/22 vs `har_iv` (baseline); the graph arms and STID tied inside seed noise |

**Verdict:** ✅ Deflation control is in the same table as the graph arms.

---

### 1.3 Patton-QLIKE + panel-DM + 5% MCS

All three headline stats are computed on every tournament table — no cherry-picking possible.

| Claim | Evidence |
|---|---|
| Primary metric is Patton-QLIKE (log space) | [src/volforecast/evaluation/statistical_tests.py#L540-L548](../../src/volforecast/evaluation/statistical_tests.py#L540-L548) — `qlike_fn(y_true, pred, log_space=True)` per model in `tournament_table` |
| Panel-aware Diebold-Mariano vs baseline is a per-row column | [statistical_tests.py#L468](../../src/volforecast/evaluation/statistical_tests.py#L468) — `tournament_table(...)` returns `dm_stat`, `dm_pvalue` per model; docstring at L504-L509 |
| DM uses date-averaged HAC with panel-aware n_cross_sections | [statistical_tests.py#L717-L811](../../src/volforecast/evaluation/statistical_tests.py#L717-L811) — `conditional_dm` reuses `diebold_mariano_test` with `n_cross_sections`, `panel_order` |
| MCS membership at 10% and 5% is a per-row column | [statistical_tests.py](../../src/volforecast/evaluation/statistical_tests.py) — `tournament_table` docstring lists `mcs_included`, `mcs_pvalue`; trial-094 runs `mcs_bootstrap: 10000` at [trial_090_gnn_grand_tournament.yaml#L89](../configs/trial_090_gnn_grand_tournament.yaml#L89) |
| Metric schema is append-only (goldens protect existing columns) | [src/volforecast/evaluation/aggregate.py#L22-L33](../../src/volforecast/evaluation/aggregate.py#L22-L33) — `_METRIC_COLUMNS` header explicitly annotated `APPEND-ONLY` |
| Turbulence-split additions (`qlike_calm`, `qlike_turb`, `dm_p_turb`) wired into every table | [aggregate.py#L29-L32](../../src/volforecast/evaluation/aggregate.py#L29-L32); [src/volforecast/evaluation/tournament.py#L944-L987](../../src/volforecast/evaluation/tournament.py#L944-L987) |
| Conditional metrics have unit coverage on synthetic planted-effect data | [src/tests/unit/test_conditional_metrics.py#L48-L167](../../src/tests/unit/test_conditional_metrics.py#L48-L167) — 8 tests including `test_planted_turbulent_only_edge`, `test_n_cross_sections_plumbed_to_hac` |

**Verdict:** ✅ QLIKE + panel-DM + MCS all present in the same row per model, plus conditional splits for calm/turbulent regime attribution.

---

### 1.4 Unsmoothed intraday RV target

The forecast target is `forward_log_rv` computed on the repo's 5-minute realized-variance series — not a smoothed/annualized proxy.

| Claim | Evidence |
|---|---|
| Target definition is `log(mean(rv over next h days))` | [src/volforecast/utils/targets.py#L35](../../src/volforecast/utils/targets.py#L35) — `def forward_log_rv(rv, h)` |
| Every runner path uses this exact target | [src/volforecast/pipeline/runner.py#L28](../../src/volforecast/pipeline/runner.py#L28) import; call sites at [runner.py#L1118](../../src/volforecast/pipeline/runner.py#L1118), [runner.py#L1323](../../src/volforecast/pipeline/runner.py#L1323), [runner.py#L1554](../../src/volforecast/pipeline/runner.py#L1554), [runner.py#L2470](../../src/volforecast/pipeline/runner.py#L2470), [runner.py#L3479](../../src/volforecast/pipeline/runner.py#L3479) |
| Same target flows into IV feature construction (no target drift) | [src/volforecast/data/iv_features.py#L69](../../src/volforecast/data/iv_features.py#L69) — `target = forward_log_rv(rv_panel["rv"], h)` |
| Underlying `rv` column is per-day realized variance from 5-min log returns | Per [AGENTS.md](../../AGENTS.md) Data Access section: per-symbol RV parquets under `data/raw/ticks/` with the daily RV column; no smoothing applied |

**Verdict:** ✅ Target is the raw daily RV panel, not a Kalman-smoothed or MA-filtered surrogate.

---

### 1.5 Graph / scaler information sets stated (Point-In-Time discipline)

Every graph builder is estimated on `data ≤ estimation_date`; scalers are train-only. Both are unit-tested.

| Claim | Evidence |
|---|---|
| Global PIT constraint declared for graph construction | [workspace/plans/gnn-implementation-plans/plan-01-graph-construction.md#L17](../plans/gnn-implementation-plans/plan-01-graph-construction.md#L17) — *"Graph estimation must use only data ≤ estimation date (PIT). Every builder gets a leakage test."* |
| Pipeline PIT contract stated for the schedule | [plan-02-graph-pipeline-path.md#L17-L18](../plans/gnn-implementation-plans/plan-02-graph-pipeline-path.md#L17-L18) — schedule built once over all dates from `data ≤ each refit date` |
| Correlation graph has an explicit PIT unit test | [src/tests/unit/graphs/test_correlation_graphs.py#L32](../../src/tests/unit/graphs/test_correlation_graphs.py#L32) — `test_corr_is_point_in_time` |
| Regime-blend graph classifies calm/stress only from in-window data | [src/tests/unit/graphs/test_regime_blend_graph.py#L117](../../src/tests/unit/graphs/test_regime_blend_graph.py#L117) — `test_pit_classification` |
| Markov-switching regime layer has both filtered-only and frozen-parameter PIT tests | [src/tests/unit/test_regime_layer.py#L134-L206](../../src/tests/unit/test_regime_layer.py#L134-L206) — `TestRegimeLayerPIT` covers filtered-vs-smoothed leak (item 4 in file header) and frozen-parameter forward filtering (item 5) |
| Per-symbol scaler leakage test blocks train/test bleed | [src/tests/unit/test_per_symbol_norm.py#L431-L523](../../src/tests/unit/test_per_symbol_norm.py#L431-L523) — `test_per_symbol_norm_train_only_leakage` (injects extreme test-date stats; asserts train stats unaffected) |
| Runner honors the `min_history` warmup contract before first refit | [src/volforecast/pipeline/runner.py#L2830-L2831](../../src/volforecast/pipeline/runner.py#L2830-L2831) — `refit_every`, `min_history` passed to `build_graph_schedule`; warmup splice at [runner.py#L285](../../src/volforecast/pipeline/runner.py#L285), [runner.py#L3038](../../src/volforecast/pipeline/runner.py#L3038) |
| Adjacency/scalers PIT explicitly reiterated per experiment | [00-overview.md](../plans/gnn-implementation-plans/00-overview.md) §3 item 6 and §4.1 constraints |
| Regime hybrid arms carry the two published leakage traps in test form | [plan-09-hybrids-regime-fusion.md#L16-L18](../plans/gnn-implementation-plans/plan-09-hybrids-regime-fusion.md#L16-L18) — filtered-vs-smoothed and frozen-parameter leaks both tested |

**Verdict:** ✅ Graph, scaler, and regime information sets are all point-in-time by construction and covered by explicit unit tests.

---

### 1.6 Economics (deferred to follow-up)

Delta-hedged straddle P&L, vol-targeting Sharpe, and GSVIVS signal enrichment infrastructure exist and are toggle-driven — but headline economics claims are **not** made in this program.

| Claim | Evidence |
|---|---|
| Enrichment module exists | [src/volforecast/evaluation/tournament_economics.py](../../src/volforecast/evaluation/tournament_economics.py) — `enrich_tournament_economics(...)` composed onto `tournament_table` per docstring at [statistical_tests.py#L482-L485](../../src/volforecast/evaluation/statistical_tests.py#L482-L485) |
| Config toggles are wired end-to-end | [src/volforecast/__main__.py#L724-L726](../../src/volforecast/__main__.py#L724-L726) — `dh_enabled`, `vt_enabled`, `gsvivs_enabled` piped from `config.tournament` into `run_pooled_tournament` at [src/volforecast/evaluation/tournament.py#L182-L184](../../src/volforecast/evaluation/tournament.py#L182-L184) |
| Trial-094 headline run has economics **off** on purpose | [trial_090_gnn_grand_tournament.yaml#L93-L95](../configs/trial_090_gnn_grand_tournament.yaml#L93-L95) — `dh_enabled: false`, `vt_enabled: false`, `gsvivs_enabled: false` |
| Follow-up program tracked in plan-10 acceptance gate | [plan-10-grand-tournament.md](../plans/gnn-implementation-plans/plan-10-grand-tournament.md) — closing paragraph lists "economic-value enrichment of the GNN winner (dh straddle/vol-targeting)" as a next-phase item |

**Verdict:** ✅ Infrastructure ships; **economics claims are deliberately deferred** to a follow-up program. This is called out honestly rather than paperwork-hidden.

---

## 2. Expected-gains-vs-found table

Priors from the GNNHAR lineage ([00-overview.md](../plans/gnn-implementation-plans/00-overview.md) §3):

| Component | Prior QLIKE gain vs rolling HAR (h=1) | Found (trials 080–085) | Trial-094 (pending) |
|---|---|---|---|
| QLIKE-trained HAR | ~1–2% | Absorbed in baseline `har_iv` | — |
| GHAR spillover terms | ~1–2% (h=1) | −1 bp vs `har_iv` (inside seed envelope) | pending |
| GNNHAR-1L (QLIKE-trained) | ~3–4% (h=1), ~8% (h=5), ~0% (h=22) | −1 bp (h=1), 0 bp (h=5), −1 bp (h=22) | pending |
| Attention over fixed weights (GATv2/UniMP) | unproven under QLIKE+DM anywhere | Null (all attention arms tied) | pending |
| Dynamic DY graphs (DCRNN-HAR) | h=1 low single digits, h=22 gains claimed under MSE | Null under QLIKE at all horizons | pending |
| Spectral / learned adjacency (GSP-HAR, MTGNN-style) | unproven for equities | Not run (trial-086 `NOT_STARTED`) | pending |
| Regime-blended graphs | unknown; no credible incumbent | Not run (trial-091 `NOT_STARTED`) | pending |
| Hybrid stacking vs blending | ≈ 0 until proven | Confirmed null: A ≈ B-8 ≈ B-32 at h=1/5/22 (trials 089/092/093) | pending |

**Pending row:** the trial-094 findings column will be filled after `./vol run --config workspace/configs/trial_090_gnn_grand_tournament.yaml --skip-ingest` completes and the interpretation writeup lands. Priors above are the acceptance targets — anything within ±2 bp of `har_iv` is a null result, not a bug.

---

## 3. Findings from trials 080–085 — one line each

Read the `horizons` blocks in [trials.yaml#L2997-L3200](trials.yaml#L2997-L3200) for the numeric evidence.

- **trial-080 (`gnn_native`, 2026-07-10):** Standalone GATv2 harness reproduces trial-068's stack — QLIKE 0.1607 (h=1) / 0.1349 (h=5) / 0.1839 (h=22). `verdict: COMPLETED` (validation, not a horse race).
- **trial-081 (`ghar_graph_ablation`, 2026-07-10):** Best of {full, glasso, dy} vs identity — 0.1606 (h=1) / 0.1348 (h=5) / 0.1837 (h=22). Winning graph = `glasso` placeholder. Gate result: within 1 bp of `har_iv` (baseline), not DM-significant at the 5% level; ships anyway as the trial-094 default graph.
- **trial-082 (`ghar_factor_residual`, 2026-07-10):** Factor-residual edges vs raw correlation — +1 bp at h=1, 0 bp at h=5, +1 bp at h=22 vs `har_iv`. **All horizons `verdict: FAIL`.**
- **trial-083 (`gnnhar_vs_ghar_stid`, 2026-07-10):** Gate 1 (nonlinearity earns keep) + Gate 2 (graph beats identity via STID deflation) — +1 bp / 0 bp / +1 bp vs `har_iv`. **All horizons `verdict: FAIL`.** Honest reading: pooling + asset identity suffices at this universe size.
- **trial-084 (`attention_upgrades`, 2026-07-10):** GATv2 / SpotV2Net edge features / UniMP vs fixed weights — +1 / 0 / +1 bp vs `har_iv`. **All horizons `verdict: FAIL`.** Attention did not beat fixed weights under DM. This is a thesis-grade null finding.
- **trial-085 (`dcrnn_har`, 2026-07-16):** Dynamic daily DY graphs + diffusion GRU + HAR skip — +1 / 0 / +1 bp vs `har_iv`. **All horizons `verdict: FAIL`.** The paper's MSE-optimized h=22 blowout does not survive under QLIKE.

**Summary:** every graph arm ran through the gate landed inside the seed envelope of `har_iv` at every horizon. This is the outcome the priors table warned about, not a surprise.

---

## 4. Deferred follow-ups

Called out explicitly so future sessions can pick them up without re-deriving the reasoning.

1. **Economic-value enrichment of the trial-094 winner.** Rerun the winning arm with `dh_enabled: true` and `vt_enabled: true` in [trial_090_gnn_grand_tournament.yaml](../configs/trial_090_gnn_grand_tournament.yaml). Report delta-hedged straddle P&L and vol-targeting Sharpe against `har_iv` on the same OOS window. GSVIVS-gap signal enrichment (`gsvivs_enabled: true`) is the natural follow-up — it converts a statistical QLIKE win into the tradeable IV-RV signal upgrade the project is chartered to deliver.
2. **EMGNN evolving adjacency (Zhou et al. 2025).** The MTGNN-style learned adjacency in trial-086 is static-per-epoch. EMGNN evolves adjacency across time inside the model — worth a controlled arm on the trial-094 harness once trial-086 lands.
3. **Covariance-forecasting recast (GHAR JFEC lineage — Zhang et al. 2024).** The strategic fork the program deferred: score the graph arms on realized covariance forecasting (portfolio Frobenius loss) instead of per-symbol RV. This is where GNNs have shown their biggest published gains and where our universe (34 mega-caps + ETFs) is well positioned.
4. **Cross-asset ETF nodes with asynchronicity discipline.** Extend the node set to {HYG, GLD, EEM, XLF, TLT, USO} + {rates, FX, commodities}. The [00-overview.md](../plans/gnn-implementation-plans/00-overview.md) §3 item 8 warning applies: lag foreign legs one day when in doubt. Blocks: cross-asset ingestion is done (Layer 4 in [AGENTS.md](../../AGENTS.md)); graph builder needs an asynchronicity-safe adapter.

---

## 5. The 20% rule (sanity note)

From [00-overview.md](../plans/gnn-implementation-plans/00-overview.md) §3: *"If a run of ours shows 20%, the first hypothesis is a bug or a leak, not brilliance."*

**Our observed gains are well inside this envelope.** Every completed graph trial (080–085) sits within ±1 bp of `har_iv` — i.e. within noise, orders of magnitude below 20%. There is no gain to audit. If trial-094 comes back with any single-arm QLIKE improvement larger than ~600 bps (~5%) vs `har_iv`, the interpretation writeup **must** audit for:

- Adjacency built on data past the estimation date (see the [test_corr_is_point_in_time](../../src/tests/unit/graphs/test_correlation_graphs.py#L32) template);
- Scalers fit including test rows (see the [test_per_symbol_norm_train_only_leakage](../../src/tests/unit/test_per_symbol_norm.py#L431) template);
- Regime probabilities pulled from a smoothed instead of filtered pass (see the [TestRegimeLayerPIT](../../src/tests/unit/test_regime_layer.py#L134) template);
- Target definition drift (see [forward_log_rv](../../src/volforecast/utils/targets.py#L35) — this is the only accepted target).

Only after those four checks come back clean does the gain get to be called a finding.

---

## Sign-off gate for the GNN program

- [x] Conditional metrics wired (Plan 10 Task 1) — `qlike_calm`, `qlike_turb`, `dm_p_turb` at [aggregate.py#L29-L32](../../src/volforecast/evaluation/aggregate.py#L29-L32); unit tests at [test_conditional_metrics.py](../../src/tests/unit/test_conditional_metrics.py).
- [x] Dashboard graph panels + spillover heatmap wired (Plan 10 Task 2) — persistence at [runner.py#L2670-L2744](../../src/volforecast/pipeline/runner.py#L2670-L2744); unit tests at [test_dashboard_graph_panels.py](../../src/tests/unit/test_dashboard_graph_panels.py).
- [x] Headline config registered (Plan 10 Task 3) — [trial_090_gnn_grand_tournament.yaml](../configs/trial_090_gnn_grand_tournament.yaml); trial-094 in [trials.yaml#L3329](trials.yaml#L3329).
- [x] Skeptic's-checklist review (Plan 10 Task 4) — this document.
- [ ] **Next step:** user launches `./vol run --config workspace/configs/trial_090_gnn_grand_tournament.yaml --skip-ingest` (8-GPU, checkpoint-resume enabled). Then `/experiment interpret` fills the findings column of §2 and appends verdicts to [trials.yaml](trials.yaml).
- [ ] **Follow-up program:** economic-value enrichment of the winner (§4 item 1).
