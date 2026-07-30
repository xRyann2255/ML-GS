# Research Journal

Log of what was explored and learned each session. Read at session start for continuity.

**Rules:**
- Max 10 entries. When a new entry would exceed 10, move the oldest to [research-journal-archive.md](research-journal-archive.md) before appending.
- Keep entries concise: question, answer, key numbers, implications. Cut detail once a finding is acted on.
- Remove entries entirely once their content is fully superseded by code, config, or other docs.

---

## 2026-07-29 — project-state.md pruning (workflow-overhaul Plan 06, AW-16)

The following blocks were moved verbatim from memory/research/project-state.md (P0 boot file)
to keep the boot file operative-only. Original locations noted.

### Retracted results table (was project-state.md:41-52)

### Retracted / superseded (kept for reference)

| Horizon | Reported QLIKE | Trial | Reason rejected |
|---------|----------------|-------|-----------------|
| h=1 | 0.1289 | trial-036 | trial-047 reseed: 79 bps below 5-seed envelope min |
| h=5 | 0.1067 | trial-036 | trial-047 reseed: 13 bps below 5-seed envelope min |
| h=22 | 0.1628 | trial-036 | trial-047 reseed: 55 bps below 5-seed envelope min |
| h=1 | 0.1336 | trial-033 | never multi-seed validated |
| h=5 | 0.1077 | trial-033 | never multi-seed validated |
| h=22 | 0.1764 | trial-033 | never multi-seed validated |
| h=1 | 0.1155 | trial-030b | evaluated on 2022–2024 only (COVID exclusion artifact) |
| h=5 | 0.0700 | trial-030b | evaluated on 2022–2024 only (COVID exclusion artifact) |

### IV-sanity results (was project-state.md:54-61)

## IV Sanity Check Results (2026-05-27)

| Model | h=1 | h=5 | h=22 |
|-------|-----|-----|------|
| atm_iv_implied | 0.1997 | 0.1447 | 0.1925 |
| har | 0.1602 | 0.1359 | 0.2087 |
| **har_iv** | **0.1498** | **0.1187** | **0.1844** |
| lightgbm | 0.1489 | 0.1365 | 0.2079 |

### Key Decisions log, 22 dated entries (was project-state.md:63-86)

## Key Decisions Made

- Per-symbol features >> market-wide features in pooled training
- cross_asset layer removed (hurts when options layer has the interaction)
- VRP uses HAR h=22 forecast as E[RV] (Bollerslev 2009 spec)
- IV alignment: use IV[T] not IV[T-1] (prediction point = close T, same as rv[T])
- tree_expansion layer ADDED: +70 features (_change + _zscore), +31.5 bps robust over 5 seeds
- 128 features with min_child=150 works — expansion features get 8.8% of total gain, all 70 used
- VVIX is strongest h=22 signal (p=0.007 in ablation, trial-011)
- Calendar + IV interactions are noise at h=22 but signal at h=1/h=5 (trial-013 confirms)
- Horizon-specific feature sets required — cannot use single LOCKED config for all horizons
- val_purge_gap bug FIXED: date-aware purge in pooled mode (lightgbm.py:308-331), init_score train-only
- h=22 LightGBM is robust across seeds (+6 to +23 bps, 5 seeds) but NOT DM significant (trial-017)
- VVIX feature expansion HURTS at h=22 — more features = signal dilution (trial-016)
- interaction_constraints_named support added to lightgbm.py (usable but not yet beneficial)
- **ATM IV (zero-parameter) beats HAR and LightGBM at h=22 by ~800 bps** — models were not leveraging the forward-looking signal
- **HAR-IV (4 parameters) beats EVERYTHING** — linear combination of HAR memory + IV forward view dominates 128-feature LightGBM
- **IV tenor matching:** 1w ATM IV dominates 1m at h=1 (+97 bps) and h=5 (+115 bps); 1m dominates at h=22 (-107 bps). Optimal = per-horizon init
- **LightGBM init quality matters:** tenor-matched linear base partially carries through (+8/+46/-54 bps at h1/h5/h22)
- **LOCKED config:** per-horizon init (har_iv_1w for h=1/h=5, har_iv for h=22) in trial_033_lgbm_tenor_matched_LOCKED.yaml
- **GSVIVS01 long_flat signal: threshold=0 is walk-forward optimal.** Static sweep found t=-0.001 (Sharpe 3.29) but this was overfit to the test period. Walk-forward adaptive threshold (252d lookback) yields honest Sharpe 1.83 at h=1 with 65% position rate. The simple rule "flat when gap < 0, short otherwise" is the correct production policy. No threshold tuning needed.
- **Walk-forward mandatory for signal-layer hyperparams.** Any parameter that touches the trading decision (threshold, sizing leverage, lookback) MUST be validated via walk-forward or train/calibration/test split. In-sample or OOS-optimized numbers are inadmissible.
- **LSTM research line CLOSED (2026-06-22).** No integration mode (standalone, residual, embedding, feature stacking, daily-feature Rosenbaum, XGBoost-residual) produces improvement over tree models. Trials 051/053/054/061b/066/066b/066c all fail or add zero signal.
- **XGBoost is the new h=1 champion (trial-067, 0.1292).** XGBoost with mapped LightGBM hyperparams + custom QLIKE objective + har_iv_0dte init beats LightGBM 5-seed mean by +76 bps. Low seed variance (~2.5 bps from original single-seed). First tree model to also beat har_iv at h=22 (single-seed, unvalidated).
- **Generic HAR-X model (`harx` + ridge/lasso/elasticnet siblings) landed** — config-driven `extra_features` unlocks Layer-N-plus-HAR probes without new Python classes. Strict missing-column ValueError at fit surfaces YAML/data mismatches loudly. Runner requires no changes; kwargs flow through `Config.model_params_for_horizon`. See [workspace/configs/example_harx.yaml](../../workspace/configs/example_harx.yaml).

---

## 2026-07-28 -- Data Audit: 6/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 1/1 files | L7 | CRITICAL |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 110/111 | L2 | CRITICAL |
| microstructure | 101/111 | L3 | CRITICAL |
| ohlcv | 100/111 | L6 | CRITICAL |
| ticks | 101/111 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, L7, noise_robust

### Implications

- Pooled training with 101 symbols gives ~300,537 rows

---


## 2026-07-18 -- GNN Program Close-Out: Plans 01-10 Shipped, Trial-094 Registered, Graph Arms Null Within Envelope

**Question explored:** After building the full GNN roster (Plans 01–10), does graph structure deliver the ~3–4% QLIKE improvement at h=1 that the GNNHAR lineage prices in — and is the evaluation defensible under the skeptic's checklist?

### What shipped

- **Plans 01–02 (foundation):** Point-in-time graph library (`identity`, `full`, `corr`, `knn`, `glasso`, `dy`, `sector`, `factor_residual`) with per-builder PIT tests in [src/tests/unit/graphs/](../../src/tests/unit/graphs/); standalone `_run_pooled_graphs` runner path so any `requires_graph` model is a first-class tournament arm.
- **Plans 03–07 (models):** `ghar`, `gnnhar`, `stid`, `gnn` (GATv2 + SpotV2Net edge features + UniMP), `dcrnn_har`, `gsp_har`, `gnn_learned` — seven graph architectures through one harness.
- **Plan 08 (infrastructure):** Fold×GPU + seed×GPU parallelism, multi-GPU Optuna HPO, nested Rich progress with `mp.Manager().Queue()` daemon consumer.
- **Plan 09 (hybrids):** GNN embedding stacking arms + `RegimeLayer` (filtered Markov-switching, PIT-frozen) + `RegimeBlendGraphBuilder`.
- **Plan 10 (evaluation hardening):** turbulence-split `qlike_calm` / `qlike_turb` / `dm_p_turb` columns wired into `_METRIC_COLUMNS` at [aggregate.py#L22-L33](../../src/volforecast/evaluation/aggregate.py#L22-L33); dashboard graph-quality + spillover panels ([test_dashboard_graph_panels.py](../../src/tests/unit/test_dashboard_graph_panels.py)); trial-094 headline config at [trial_090_gnn_grand_tournament.yaml](../configs/trial_090_gnn_grand_tournament.yaml); skeptic's-checklist review at [gnn-program-review.md](gnn-program-review.md).

### Key null findings from trials 080–085

All five completed graph trials landed **within 1 bp of `har_iv` at every horizon** (per [trials.yaml#L2997-L3200](trials.yaml#L2997-L3200)):

| Trial | Arm | h=1 vs har_iv | h=5 | h=22 | Verdict |
|---|---|---|---|---|---|
| 080 | GATv2 native | 0.1607 QLIKE | 0.1349 | 0.1839 | COMPLETED (harness sanity) |
| 081 | GHAR (best of identity/full/glasso/dy) | −1 bp | 0 | −1 | FAIL |
| 082 | GHAR factor-residual | +1 bp | 0 | +1 | FAIL |
| 083 | GNNHAR-1L vs GHAR + STID | +1 bp | 0 | +1 | FAIL (Gate 2: STID ties — pooling + identity suffices) |
| 084 | GATv2 / SpotV2Net / UniMP attention | +1 bp | 0 | +1 | FAIL (attention does not beat fixed weights under DM — thesis-grade null) |
| 085 | DCRNN-HAR dynamic DY | +1 bp | 0 | +1 | FAIL (paper's MSE h=22 blowout does not survive under QLIKE) |

### Skeptic's-checklist sign-off (per [gnn-program-review.md](gnn-program-review.md))

1. Rolling re-estimated HAR bar ✅ — expanding-window `har_iv` at [trial_090_gnn_grand_tournament.yaml#L88](../configs/trial_090_gnn_grand_tournament.yaml#L88)
2. STID identity-embedding control ✅ — in the trial-094 roster at [line 82](../configs/trial_090_gnn_grand_tournament.yaml#L82)
3. Patton-QLIKE + panel-DM + 5% MCS ✅ — all three per row in `tournament_table` ([statistical_tests.py#L468](../../src/volforecast/evaluation/statistical_tests.py#L468))
4. Unsmoothed intraday RV target ✅ — `forward_log_rv` at [targets.py#L35](../../src/volforecast/utils/targets.py#L35), used in every runner path
5. PIT graph/scaler information sets ✅ — [test_corr_is_point_in_time](../../src/tests/unit/graphs/test_correlation_graphs.py#L32), [TestRegimeLayerPIT](../../src/tests/unit/test_regime_layer.py#L134), [test_per_symbol_norm_train_only_leakage](../../src/tests/unit/test_per_symbol_norm.py#L431)
6. Economics ⏸ — infrastructure exists (`dh_enabled`, `vt_enabled`, `gsvivs_enabled` toggles at [__main__.py#L724-L726](../../src/volforecast/__main__.py#L724-L726) + [tournament_economics.py](../../src/volforecast/evaluation/tournament_economics.py)); headline claims **deferred to a follow-up program** — explicit non-claim rather than paperwork-hidden

### Implications

- The pre-registered priors (~3–4% h=1, ~8% h=5, ~0% h=22 from Zhang et al. 2025) were **not** hit on our 21-symbol pooled universe. The honest result — graph structure does not help beyond `har_iv` at 1-bp resolution here — is the capstone finding to present, not a bug to fix.
- STID tying the graph arms (trial-083 Gate 2) is the strongest single evidence: pooling + asset identity captures whatever cross-sectional structure a graph would add, on this universe.
- The 20% rule (§5 of the review) applies to trial-094 interpretation: any single-arm gain >~600 bps triggers a mandatory PIT / scaler / regime / target audit before it counts.

### Next step (blocks the capstone table)

User launches the headline pooled tournament — 13 arms × 3 horizons on 8 GPUs, checkpoint-resume enabled:

```bash
./vol run --config workspace/configs/trial_090_gnn_grand_tournament.yaml --skip-ingest
```

Then `/experiment interpret` fills the trial-094 verdict row in [trials.yaml#L3329](trials.yaml#L3329) and the findings column of §2 in [gnn-program-review.md](gnn-program-review.md).

### Deferred follow-up program

Economic-value enrichment of the winner (`dh_enabled: true`, `vt_enabled: true`, `gsvivs_enabled: true`), EMGNN evolving adjacency, covariance-forecasting recast per the JFEC lineage, and cross-asset ETF nodes with asynchronicity discipline. See [gnn-program-review.md](gnn-program-review.md) §4 for the full backlog.

---

## 2026-07-10 -- Data Audit: 6/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 1/1 files | L7 | CRITICAL |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 110/111 | L2 | CRITICAL |
| microstructure | 101/111 | L3 | CRITICAL |
| ohlcv | 100/111 | L6 | CRITICAL |
| ticks | 101/111 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, L7, noise_robust

### Implications

- Pooled training with 101 symbols gives ~299,346 rows

---


## 2026-07-10 -- Data Audit: 6/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 1/1 files | L7 | CRITICAL |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 110/111 | L2 | CRITICAL |
| microstructure | 101/111 | L3 | CRITICAL |
| ohlcv | 100/111 | L6 | CRITICAL |
| ticks | 101/111 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, L7, noise_robust

### Implications

- Pooled training with 101 symbols gives ~298,910 rows

---


## 2026-07-10 -- Data Audit: 6/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 1/1 files | L7 | CRITICAL |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 33/34 | L2 | CRITICAL |
| microstructure | 34/34 | L3 | CRITICAL |
| ohlcv | 33/34 | L6 | OK |
| ticks | 34/34 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, L7, noise_robust

### Implications

- Pooled training with 34 symbols gives ~101,947 rows

---


## 2026-07-01 -- Prediction Blending: LSTM + XGBoost Residual Decorrelation

**Hypothesis card:**
- Question: Does blending LSTM and XGBoost predictions improve QLIKE despite LSTM being worse standalone?
- Feature layer: N/A (model-level ensemble)
- Data needed: 21 symbols, 2015-2026, h=1 OOS predictions from both models on identical test window
- Method: (1) Compute residual correlation; (2) Grid-search optimal blend weight; (3) Per-symbol and conditional analysis
- Success criterion: Blend QLIKE < XGBoost-only QLIKE by ≥1 bps
- Null hypothesis: Correlation ≥ 0.8 → blend adds nothing
- Pitfalls: In-sample weight optimization overfits; need walk-forward validation for production

**Result:** Marginal improvement — below significance threshold

**Key statistics:**
- QLIKE loss correlation: **0.34** (low — models disagree on 2/3 of hard observations)
- Optimal blend weight: **80% XGB + 20% LSTM** (exp-space)
- Blend QLIKE: 0.001833 vs XGBoost 0.001895 → **+0.62 bps improvement**
- LSTM standalone win rate: 40.3% of individual observations

**Per-regime breakdown:**
- High-vol days: LSTM gap = +8.4 bps (worse)
- Low-vol days: LSTM gap = +11.1 bps (worse)
- Spike days (top 10%): LSTM catastrophically worse (+22 bps)
- Blend adds 0-5 bps per symbol (XOM, PG benefit most; AMZN, MSFT, V gain nothing)

**Implication:** The 0.62 bps blend improvement is real but economically negligible — below measurement noise for a single-seed result. The low residual correlation (0.34) confirms the models see different things, but LSTM's absolute quality is too poor for even low-weight inclusion to matter. A stronger intraday model (TCN, or LSTM with IV features) is needed before blending becomes worthwhile.

**Verdict:** LSTM blending NOT worth pursuing at current quality level. The research question is answered: decorrelation exists but the weaker model needs to be closer in absolute quality for blending to produce meaningful gains. The theoretical lower bound for blend improvement with corr=0.34 and QLIKE gap of ~10 bps is ~0.6 bps — which is exactly what we observe.

---

## 2026-07-01 -- Data Audit: 6/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 1/1 files | L7 | CRITICAL |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 33/34 | L2 | CRITICAL |
| microstructure | 29/34 | L3 | CRITICAL |
| ohlcv | 29/34 | L6 | OK |
| ticks | 29/34 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, L7, noise_robust

### Implications

- Pooled training with 29 symbols gives ~86,294 rows

---


## 2026-06-19 -- Data Audit: 5/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 0/1 files | L7 | OK |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 33/34 | L2 | CRITICAL |
| microstructure | 29/34 | L3 | CRITICAL |
| ohlcv | 29/34 | L6 | OK |
| ticks | 29/34 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, noise_robust
- **L7 BLOCKED:** run `vol ingest-corr`

### Implications

- Pooled training with 29 symbols gives ~85,432 rows
- 1 feature layers blocked pending ingestion

---


## 2026-06-19 -- Trial-059: Feature Removal Hurts, 0DTE Ratio Adds Nothing

**Question:** Does removing "useless" features (calendar dummies, manual interactions, weak-signal expansions) improve LightGBM QLIKE? Does adding `log_iv_0dte_1w_ratio_d` help?

### Results

| Model | Features | h=1 QLIKE | h=5 QLIKE | h=22 QLIKE |
|-------|----------|-----------|-----------|------------|
| lgbm_full (champion) | 128 | **0.1299** | **0.1104** | 0.1699 |
| lgbm_add_0dte_ratio | ~132 | 0.1299 | 0.1104 | 0.1699 |
| lgbm_drop_calendar (-12) | 116 | 0.1306 | 0.1108 | **0.1696** |
| lgbm_drop_tier123 (-32) | 96 | 0.1315 | 0.1118 | 0.1714 |
| har_iv (linear) | 4 | 0.1517 | 0.1216 | **0.1691** |

### Deltas vs lgbm_full (bps, positive = improvement)

| Model | h=1 | h=5 | h=22 |
|-------|-----|-----|------|
| lgbm_add_0dte_ratio | 0 | 0 | 0 |
| lgbm_drop_calendar | **-7** | **-4** | +3 |
| lgbm_drop_tier123 | **-16** | **-14** | **-15** |

### Key Findings

1. **0DTE ratio feature added ZERO value** — `lgbm_add_0dte_ratio` produced identical QLIKE to `lgbm_full` at every horizon. Either `iv_0dte_atm` column is absent from the training data (feature is NaN → never split on), or the feature is already present in `lgbm_full` via current codebase (making them identical runs). Need to inspect actual feature count in model output to diagnose.

2. **Calendar dummies ARE useful at h=1/h=5** — Dropping `day_of_week`, `month`, `quarter_end`, `year_end` hurt by 7 bps (h=1) and 4 bps (h=5). Calendar dummies help at short horizons (event proximity matters for vol). At h=22 the drop was neutral-to-positive (+3 bps) — monthly seasonality noise at long horizons.

3. **Tier 2+3 features ARE useful** — Dropping manual interactions (`atm_iv_x_log_rv`, `vix_x_log_rv`) + weak-signal expansions caused -16/-14/-15 bps degradation. The "redundant for trees" logic was wrong: pre-computed products may help LightGBM with its limited depth (4) by providing explicit signal at shallow splits.

4. **Self-regularization confirmed but NOT perfect** — Trial-046 earlier showed drops are neutral; here they hurt. The tree doesn't waste many splits on these features, but occasionally uses them beneficially.

5. **h=22: har_iv (0.1691) still beats all LightGBM variants** — Confirmed again: 4-param linear > 128-feature tree at monthly horizon.

### Implications

- **Do NOT remove features from the champion.** LightGBM's `min_child_samples=150` + regularization handles noise features better than manual pruning.
- **0DTE ratio needs investigation:** either the data column is missing (ingest issue) or the feature is already included. Check model booster's `feature_name()` output.
- **The "redundant interaction" theory is wrong:** `atm_iv_x_log_rv` products DO help trees with depth=4 by providing a pre-computed signal accessible in a single split that would otherwise require 2 correlated splits.
- **Path forward for improvement:** Adding good features > removing bad features. Focus on new signal sources (0DTE data availability, cross-asset momentum, economic-value-aware loss).

---

## 2026-06-18 -- Data Audit: 5/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 0/1 files | L7 | OK |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 33/34 | L2 | CRITICAL |
| microstructure | 29/34 | L3 | CRITICAL |
| ohlcv | 29/34 | L6 | OK |
| ticks | 29/34 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, noise_robust
- **L7 BLOCKED:** run `vol ingest-corr`

### Implications

- Pooled training with 29 symbols gives ~85,432 rows
- 1 feature layers blocked pending ingestion

---


## 2026-06-11 -- Trial-049: COVID-in-Train Improves QLIKE but Hurts GSVIVS01 Sharpe (Statistical-Loss vs Economic-Loss Divergence)

**Question:** Does training on longer folds that include the COVID period (Feb-Jun 2020) help the model learn regime detection and improve both QLIKE and GSVIVS01 Sharpe?

### Setup

Trial-049 is identical to trial-036 in every parameter except `cv.train_size: 504 -> 1843`. First fold trains 2015-01-02 -> 2022-04-29 (covers 2015-16 EM scare, 2018 Volmageddon, COVID, 2022 inflation), then 4 OOS test windows of 126 days each through 2024-12-31. Test starts 2022-05.

### Results (sharpe_0rf from gsvivsStatsByHorizon, default Exec Kvar)

| Horizon | QLIKE 036 -> 049 | LGBM Sharpe 036 -> 049 | always_long Sharpe 036 -> 049 |
|---|---|---|---|
| h=1 | 0.1289 -> 0.1129 (-160 bps) | **1.95 -> 1.37 (-0.59)** | 1.95 -> 2.01 (+0.07) |
| h=5 | 0.1067 -> 0.0867 (-200 bps) | 1.10 -> 0.76 (-0.35) | 1.89 -> 1.95 (+0.06) |
| h=22 | 0.1628 -> 0.0881 (-747 bps) | 0.06 -> -0.07 (-0.12) | 1.74 -> 1.91 (+0.17) |

After subtracting the always_long lift, LGBM degradation is approximately -0.65 / -0.41 / -0.29 Sharpe.

Position rate at h=1: 56.7% short -> 54.4% short. Model became more conservative; it skipped profitable short days.

### Why QLIKE improved but Sharpe dropped

1. **Test window shift.** Trial-049 only tests 2022-05 -> 2024 (post-COVID, calmer). Lower-magnitude RV is numerically easier for QLIKE. Same artifact as trial-030b retraction. The QLIKE improvement is not directly comparable to trial-036's 2017-2024 test.
2. **COVID training teaches caution.** Seeing March 2020 tails biases RV forecasts upward, makes the IV-RV gap less positive, suppresses short signals.
3. **All linear baselines also degrade** (har_iv_1w h=1: -0.43, har_iv: -0.29, har: -0.16). Rules out model-specific overfitting; this is a regime effect on the test window itself.
4. **QLIKE is symmetric in log-error; the variance-swap P&L is asymmetric.** A missed short on a calm day costs the entire premium. QLIKE does not penalize that asymmetry.

### Implications

- **REJECT trial-049 as champion replacement.** Keep trial-036 spec (or trial-047 reseed envelope) as production.
- **Methodology rule:** any trial that changes train_size or date_range must report QLIKE on the SAME OOS dates as the baseline to be valid. Future trials should pin a fixed evaluation window in addition to the natural per-fold OOS.
- **Strategic lesson:** regime-rich training does NOT automatically improve economic value. The next economic-value experiments should optimize directly on Sharpe or on a P&L-aware loss, not on QLIKE.

### Persisted to

[workspace/research/trials.yaml](workspace/research/trials.yaml) trial-049 entry.

---

## 2026-06-11 -- Trial-047: Multi-Seed Re-Baseline Confirms Trial-036 Numbers Were Cherry-Picked

**Question:** Are trial-036's published champion QLIKE numbers (h1=0.1289, h5=0.1067, h22=0.1628) reproducible? Trial-046 flagged that the same-config control re-ran at h1=0.1366 (-77 bps), suggesting parallel-fit nondeterminism.

**Method:** Single tournament run, 5 identical LightGBM tournament variants differing ONLY in `seed` (42, 123, 456, 789, 2026). Shared data, features, CV splits. trial-036 spec unchanged. har, har_iv as linear baselines.

### Reseeded QLIKE Envelope (5 seeds)

| Horizon | Mean    | Std    | Min     | Max     | Range (bps) | Trial-036 reported | Gap (bps) |
|---------|---------|--------|---------|---------|-------------|-------------------|-----------|
| h=1     | 0.13679 | 0.0003 | 0.13658 | 0.13724 | 6.6         | 0.12890           | **-78.9** |
| h=5     | 0.10804 | 0.0001 | 0.10790 | 0.10822 | 3.2         | 0.10670           | **-13.4** |
| h=22    | 0.16826 | 0.0003 | 0.16784 | 0.16849 | 6.4         | 0.16280           | **-54.6** |

Gap = reseeded_mean - reported. Negative means reported was BETTER. At all three horizons, the reported number sits OUTSIDE the seed envelope (below min). Trial-036's numbers are not reproducible — they reflect a single lucky seed/process-pool order, not model quality.

### LightGBM Mean vs har_iv Linear Baseline

| Horizon | lgbm mean | har_iv  | Delta (bps) |
|---------|-----------|---------|-------------|
| h=1     | 0.13679   | 0.15211 | **+153**    |
| h=5     | 0.10804   | 0.12180 | **+138**    |
| h=22    | 0.16826   | 0.16755 | **-7**      |

### Implications

1. **Project-state.md scorecard is wrong.** Stale single-seed numbers from trial-033/036 should be replaced with reseeded means.
2. **h=22 champion is har_iv, NOT LightGBM.** A 4-parameter linear model beats the 128-feature LightGBM across ALL 5 seeds. The LGBM "win" reported in trial-033 (0.1764) and trial-036 (0.1628) was seed luck. Consistent with trial-045 conclusion that h=22 LightGBM gains are marginal.
3. **h=1 and h=5 LightGBM still beat har_iv robustly** (+153 / +138 bps with tiny envelope) — those wins are real.
4. **Reporting protocol going forward:** report mean ± std across ≥3 seeds, not single-seed numbers. Any "new champion" claim needs multi-seed confirmation before being entered in project-state.md.

**Persisted:** [memory/research/project-state.md](memory/research/project-state.md) scorecard updated; trial-047 added to [workspace/research/trials.yaml](workspace/research/trials.yaml).

---

## 2026-06-08 -- GSVIVS01 Daily Lifecycle Audit: Complete Mechanics Documented

**Question explored:** What exactly does the GSVIVS01 strategy do each day? When does it buy/sell, what instruments, how much, and how is it sized?

### Confirmed Lifecycle (from output.json, 1011 days)

1. **13:10 ET:** Signal generation fires (algo, no discretion)
2. **13:30-14:00 ET:** SELL two SPX option strips via 30-min TWAP:
   - 0DTE strip (expires today ~16:00): ~9-18 OTM options
   - 1DTE strip (expires tomorrow): ~15 OTM options (main P&L driver)
3. **13:30-17:15 ET:** Delta hedge with ES futures (~52 clips/day, 5-min TWAPs)
4. **16:00 ET:** 0DTE expires at intrinsic; 1DTE carries overnight
5. **MOC:** Close (buy back) yesterday's expired strip at settlement price (0 if OTM)
6. **22:00 UTC:** Index mark

### Critical Sizing Detail: Variance-Swap Weighting

Quantities follow $\text{qty}_i = c / K_i^2 \cdot \Delta K_i$. Verified: `qty * K^2 = 96,860` (constant). ATM strike has both put + call at half qty. This makes P&L proportional to (RV^2 - IV^2), i.e., a variance swap payoff.

### P&L: 37 bps gross premium/day, -14 bps TC = +3.2 bps net = 8.4% ann.

### Persisted to: `memory/repo/gsvivs-daily-lifecycle.md`

---

## 2026-06-08 -- Cross-Asset Lead-Lag at h=5/h=22: rate_vol Dominates, credit_cdx HURTS

**Question:** Do rate_vol_1y10y and credit_vol_cdx carry forward-looking signal at h=5 and h=22? At h=1 the ablation showed +139/+85 bps respectively. Why was h=5 previously "negligible"?

### Method

SPY-only, OLS expanding window (504d min train), 2015-2026. Tested: point-in-time levels (lag 0-5), multi-day averages (5d/10d/22d/44d/63d), momentum (1d/5d changes), z-scores, and combinations. Compared against HAR and HAR-IV baselines. Granger block F-tests for lags 1-5.

### Key Results

**rate_vol is a powerhouse at ALL horizons:**

| Signal variant | h=5 (bps vs HAR) | h=22 (bps vs HAR) |
|---|---|---|
| rate_vol z-score (20d) | **+266** | **+354** |
| rate_vol 5d change | +224 | +211 |
| rate_vol 22d mean | +144 | +174 |
| rate_vol level (t=0) | +134 | +55 |
| rate_vol level (t=5) | +129 | +112 |

vs HAR-IV (stronger baseline):
| Signal | h=5 (bps vs HAR-IV) | h=22 (bps vs HAR-IV) |
|---|---|---|
| rate_vol level | **+232** | **+261** |
| rate_vol 22d avg | +212 | **+286** |
| credit_cdx 22d avg | +45 | -500 |

**credit_cdx HURTS at h=5 and h=22** (unlike h=1 where it helped +85 bps). Every credit_cdx variant produces negative bps at longer horizons. Likely: credit spread level is contemporaneously correlated (rho=0.78) but reflects REACTIVE comovement, not predictive signal.

**Granger tests significant** (p<0.02) for both signals in-sample, but credit_cdx does not translate OOS.

### Cross-correlation structure

credit_cdx has HIGHER raw correlation than rate_vol (0.70 vs 0.22 at lag 0, h=5) but LOWER OOS utility. Classic "spurious regression": both credit and equity vol driven by same regime. rate_vol's lower but consistent OOS gain suggests genuine LEAD.

### Lag structure

For rate_vol at h=22, lagged signals are BETTER than t=0 (t5: +112 vs t0: +55 bps). Rate vol leads equity vol by multiple days at monthly horizon.

### Implications for trial-039

1. **KEEP rate_vol** -- massive signal at all horizons, even above HAR-IV
2. **DROP credit_cdx** from level features -- hurts OOS at h=5/h=22
3. **Best representation:** z-score (20d) or 5d change, not raw level
4. **For h=22:** 22d average of rate_vol (+286 bps vs HAR-IV) better than point-in-time (+261 bps)
5. **2026-06-05 "h=5 negligible" was WRONG** -- that tested only raw levels without z-score transform

### Next

- Update trial-039: keep rate_vol (z-score + level), drop credit_cdx, keep fx_iv/gvz
- Test if rate_vol signal persists in pooled LightGBM (23 symbols)

### UPDATE (same session): Tournament FAILED — trial-043

Ran full tournament with cross_asset_momentum layer + tree_expansion. LightGBM results:
- h=1: 0.1401 (WORSE by 112 bps vs trial-036's 0.1289)
- h=5: 0.1136 (WORSE by 69 bps vs trial-036's 0.1067)
- h=22: 0.1676 (WORSE by 48 bps vs trial-036's 0.1628)

Same pattern as microstructure: signal is real in OLS but adding 26+ features to LightGBM dilutes splits. The model has limited tree capacity (num_leaves=16) and the extra features steal splits from proven IV/RV core.

**Fix options (next experiments):**
1. Add rate_vol to init_score (HAR-IV-RateVol: 5 params linear model as base)
2. Use ONLY rate_vol z-score (single feature) without full cross-asset layer
3. Drop tree_expansion when xasset is used (fewer features competing)
4. Increase num_leaves to 32 (more capacity for additional features)

### UPDATE 2 (same session): Trial-044 — init_score + single feature ALSO FAILS

Implemented HAR-IV-RateVol (5-param OLS/Ridge/Lasso) and used as LightGBM init with only z_rate_vol surviving as tree feature. Results:
- LightGBM: h1=0.1340 (-51 bps), h5=0.1097 (-30 bps), h22=0.1674 (-46 bps) vs trial-036
- **Better than trial-043** (single feature vs 26) but still fails

**CRITICAL FINDING:** har_iv_ratevol (OLS 5-param) is WORSE than har_iv (4-param) in pooled training:
- h5: 0.1271 vs 0.1210 (rate_vol hurts -61 bps)
- h22: 0.1737 vs 0.1666 (rate_vol hurts -71 bps)

**Root cause:** The rate_vol signal is **SPY/index-specific**. The OLS ablation was SPY-only (+232 bps). In pooled training with 21 symbols, swaption rate_vol predicts market-wide vol (SPY, QQQ) but NOT individual stock vol (AAPL, NVDA, etc.) which has idiosyncratic components. When you train a pooled linear model, the noisy stock-level rate_vol relationship overwhelms the clean index-level one.

**Conclusion:** Cross-asset signals require **symbol-type conditioning**: useful for index ETFs, harmful for single stocks. To leverage rate_vol, need either:
1. Index-only model (SPY/QQQ/IWM subset)
2. LightGBM interaction: rate_vol x beta (let tree learn which symbols benefit)
3. Two-tier architecture: separate models for index vs single-name

---

## 2026-06-05 -- Cross-Asset Per-Feature Ablation: LEVELS Beat CHANGES

**Question:** Which cross-asset signals carry forward-looking information for equity RV? Do daily CHANGES (momentum) beat LEVELS?

### Method

SPY-only, OLS expanding window (504d train, 126d test), HAR-IV baseline. Added each signal one at a time in three variants: (1) 1-day change only, (2) all momentum (1d + 5d + z-score), (3) level only.

### Results: h=1

| Signal | 1d-change (bps) | All momentum (bps) | Level only (bps) | Best |
|--------|-----------------|--------------------|--------------------|------|
| rate_vol | +96 | +74 | **+139** | Level |
| credit_cdx | +31 | +47 | **+85** | Level |
| fx_iv_eurusd | -1 | +23 | **+65** | Level |
| fx_iv_usdjpy | -13 | -5 | **+65** | Level |
| gvz | -1 | -12 | **+24** | Level |
| oil_vol | +1 | -14 | -3 | Marginal |
| gold_vol | -4 | -26 | -10 | Hurts |

### Results: h=5

Effects negligible (all <5 bps). Baseline QLIKE already very low (0.01275). Only credit_cdx momentum shows +4 bps forward signal.

### Key Insight: LEVELS dominate, CHANGES hurt

**The forward-looking hypothesis was WRONG for this setup.** Cross-asset implied vol LEVELS (rate_vol, credit_cdx, fx_iv) massively help at h=1 (+65-139 bps). But adding their CHANGES/momentum REDUCES the benefit. The level already contains the forward signal (options prices ARE forward-looking). Changes add noise.

**Why trial-031b/031c found levels hurt:** those trials used the old `CrossAssetLayer` which applied `compute_rolling_vol()` (backward RV) to what's already implied vol data — essentially computing vol-of-vol. The RAW implied vol levels (fx_iv_usdjpy, rate_vol_1y10y, credit_vol_cdx) were never properly tested as direct features.

### Implications

1. The `cross_asset_momentum` layer (changes only) is NOT the right approach
2. Need a layer that passes through RAW cross-asset implied vol LEVELS directly
3. rate_vol (+139 bps), credit_cdx (+85 bps), fx_iv (+65 bps each) are huge signals — together could be 100+ bps in LightGBM
4. The SPY OLS result may inflate vs pooled LightGBM (need full tournament to confirm)

### Next

- Design trial with raw cross-asset IV levels as direct LightGBM features (not `compute_rolling_vol` transform)
- Focus on: rate_vol_1y10y, credit_vol_cdx, fx_iv_usdjpy, fx_iv_eurusd, gvz

---

## 2026-06-05 -- Prediction Lag Diagnostic: Why Models Miss Vol Spikes

**Question:** The model achieves good QLIKE but systematically lags: it cannot predict big moves before they happen. What causes this and what forward-looking signals could fix it?

### Empirical Evidence (SPY, HAR-IV, 2017-2026 OOS)

**Spike days (>2std above 63d rolling mean) = 3.9% of days but 22% of total QLIKE loss.**

Event study (mean prediction error = actual - predicted, in log-RV):
| Window | T-5 | T-4 | T-3 | T-2 | T-1 | **T (spike)** | T+1 | T+2 |
|--------|-----|-----|-----|-----|-----|---------------|-----|-----|
| Error  | 0.32 | 0.31 | 0.29 | 0.42 | **0.64** | **1.02** | 0.28 | 0.21 |

Model underestimates for 5 days leading into a spike. The error at T-1 (0.64) shows the model is ALREADY wrong the day before the spike hits.

**IV carries forward signal the model partially ignores:**
- IV rises 0.65 std the day BEFORE spikes (t-stat = 3.85)
- corr(dIV_today, RV_tomorrow) = 0.12
- Q5 of IV changes (biggest rises): mean next-day log_rv = -10.00 vs Q1 (biggest drops): -10.39
- Spread: 0.39 log-RV units between extreme IV change quintiles

**Structural limitation:**
- HAR uses 3 backward RV averages (d/w/m) + 1 IV level
- IV LEVEL correlates with RV level (both track the regime) but does not capture the DIRECTION of change
- The model never sees: "IV just jumped 2% today" as a feature separate from "IV is at 15%"

### Root Cause: Wrong Features, Not Wrong Model

The model has ~128 features but almost all are **contemporaneous or lagged** transformations of RV:
- log_rv_d/w/m, rs_positive/negative, bpv, jumps, cont, rk, noise_gap
- tree_expansion adds _change and _zscore of these (still backward RV transforms)

The ONLY forward-looking feature used: IV level (log_atm_iv_1w_d).
Missing forward-looking signals that are available in our data:

| Signal | Mechanism | Data Available? | Expected Impact |
|--------|-----------|-----------------|-----------------|
| IV daily change (dIV) | Market pricing in future vol | YES (iv_1w_atm) | High (corr 0.12 with fwd RV) |
| IV 5d momentum | Sustained hedging demand | YES (iv_1w_atm) | High |
| IV term slope CHANGE | Rebalancing expectations | YES (term_slope) | Medium |
| Skew change | Tail risk re-pricing | YES (skew_1m) | Medium |
| FX vol spike (USD/JPY) | Carry unwind precedes equity vol | YES (fx_iv_usdjpy) | High for regime changes |
| Credit spread change | Risk-off contagion | YES (credit_vol_cdx) | Medium |
| Treasury slope change | Macro regime | YES (yield_slope_10y5y) | Low-medium |
| Microstructure OFI | Informed flow detection | YES (order_flow_imbalance) | High for h=1 |
| VPIN level/change | Toxicity indicator | Partial (NaN in recent data) | High for h=1 |

### Key Insight

Trial-035 already tested VIX level, VIX innovation, and VRP as LightGBM features and found NO improvement. But those are LEVELS. The forward-looking signal is in CHANGES and CROSS-ASSET CONTAGION:

1. **dIV (IV daily change)** = "the market just repriced risk" -- this IS already in tree_expansion as iv_change but only if options layer is included
2. **Cross-asset CHANGES** (FX vol spike, credit widening, rate vol) are NOT in the model at all
3. **Microstructure signals** (OFI, signed volume) capture informed trading BEFORE public news

### Proposed Experiments (priority order)

1. **Trial-037: Cross-asset change features for h=1** -- Add dFX_vol, dCredit, dRate_slope as LightGBM features. These lead equity vol by 1-2 days (contagion).
2. **Trial-038: Microstructure + IV acceleration** -- Add order_flow_imbalance, signed_volume_ratio, and iv_0dte_accel (already computed!) for h=1.
3. **Trial-039: Asymmetric loss / spike-aware training** -- Weight spike-day observations higher in QLIKE objective (asymmetric penalty for underestimation).
4. **Trial-040: Conditional regime model** -- Separate LightGBM for high-VRP regime (when IV >> RV, a spike is being priced in).

### Why This Matters for Trading

A model that lags is USELESS for:
- Buying protection before a move (you buy AFTER the spike, when IV is already high)
- Selling vol into calm (you sell too late, when RV has already compressed)
- The IV-RV gap strategy specifically needs to predict WHEN RV will catch up to IV

The fix is not better QLIKE on average -- it's better CONDITIONAL QLIKE on the 4% of days that matter.

---

## 2026-07-01 -- LSTM Integration: Why It Failed and What Could Work

**Question:** Can we find a way to make LSTM feature stacking work, given that all previous integration modes (standalone, residual, feature stacking, daily Rosenbaum) failed across 10+ trials?

### Complete Trial History

| Trial | Mode | QLIKE h=1 | vs Champion | Verdict |
|-------|------|-----------|-------------|---------|
| 051 | Standalone intraday | 0.4332 | catastrophic | FAIL |
| 053 | Residual on LightGBM | 0.12878 | +0.9 bps | NEUTRAL |
| 054 | Single-fold residual | 0.12053 | strong | NOT ROBUST |
| 054b | Residual + symbol emb | 0.12883 | +1.9 bps | NEUTRAL |
| 057 | Residual retuned | 0.12353 | -16.5 bps | FAIL |
| 058 | Residual + v3 channels | 0.12255 | -16.9 bps | FAIL |
| 061b | Feature stack → LightGBM | 0.12869 | 0 bps (identical) | FAIL |
| 066 | Daily Rosenbaum LSTM | 0.16205 | -330 bps vs xgb | FAIL |
| 066b | LSTM residual on XGBoost | 0.12940 | +0.2 bps | NEUTRAL |
| 066c | LSTM residual on XGBoost v2 | 0.12989 | -4.9 bps | FAIL |

### Root Cause Analysis: Three Distinct Failure Modes

**Failure 1: Wrong input data for standalone LSTM (trial-051)**
- Fed 2,340 x 5-feature sequences (10s bars). Far too long for LSTM — gradient vanishing, padding overhead.
- 5 features (log_ret, vol_share, buy_ratio, log_n_trades, abs_ret) are all contemporaneous microstructure. None contain forward-looking information about *next-day* vol.
- LSTM has ~50K params on ~50K training samples — massively overparameterized relative to signal.

**Failure 2: Residual is noise after good tree model (trials 053-058, 066b/c)**
- After XGBoost/LightGBM with 128 features + har_iv init, residual $e_t$ is near-white-noise.
- Tree already captures nonlinear interactions between IV, RV lags, and options features.
- LSTM on residual is trying to predict noise — mathematically equivalent to fitting noise.
- Adding richer intraday channels (v3: price_accel, rolling_vpin, cum_rv) didn't help because the *target* is noise, not because the *features* are bad.

**Failure 3: Feature stacking — gradient isolation + no incremental information (trial-061b)**
- LSTM embedding, attention entropy, attention peak time, prediction — tree ignored ALL of them.
- Gradient isolation: LSTM was optimized for its own QLIKE, not for producing features useful to the tree. The embedding space encodes information in linear combinations that tree splits can't efficiently access.
- More fundamentally: the LSTM had the same 5 weak intraday features. If the LSTM can't beat HAR standalone, its embedding carries no information the tree doesn't already have.

### Key Insight: The Problem Is the LSTM's Input, Not the Architecture

The learning guide (ch12b) is explicit: **LSTMs become useful when you change what you feed them.** On RV lags alone, HAR matches LSTM (Christensen et al. 2023). On raw sequential data (LOB, high-frequency returns), LSTM adds genuine value.

Current LSTM inputs — 5 simple bar statistics from 10-second aggregation — are weak next-day predictors because:
1. **Contemporaneous, not forward-looking.** `log_ret`, `abs_ret`, `vol_share` describe today's microstructure, not tomorrow's volatility.
2. **No cross-asset dimension.** The LSTM sees one symbol's bars in isolation. Cross-asset lead-lag (Treasury/FX moves preceding equity vol) is invisible.
3. **No options-market information.** The richest forward-looking signals (IV surface dynamics, 0DTE pricing, put/call flow) are absent from sequences.
4. **Too granular, too long.** 2,340 bars of 10-second data create padding and vanishing gradient issues. The useful signal is in the *shape* of intraday vol (U-shape deviation, event clustering), not in individual ticks.

### What the Literature Says Could Work

1. **DeepVol approach (Moreno-Pino & Zohren 2022):** Feed raw 5-minute returns directly into a TCN (not LSTM). 78 bars/day instead of 2,340. TCN is parallelizable, has explicit receptive field, no vanishing gradient. The model learns to predict $RV_{t+1}$ end-to-end from raw intraday returns, bypassing RV computation entirely.

2. **Richer intraday features at coarser granularity:** Aggregate 10-second bars to 5-minute bars. Add LOB-derived channels per bar: order imbalance delta, spread dynamics, volume acceleration. 78 bars x 10+ features is more manageable than 2,340 x 5.

3. **Multi-scale sequence architecture:** Hierarchical model — 5-min bars within the day, then daily features across days. Captures both intraday patterns (U-shape, event clustering) and multi-day memory (HAR-like persistence).

4. **Prediction blending instead of feature stacking:** Train LSTM independently on different input data than the tree. Blend predictions with regime-dependent weights. Competition evidence (Optiver 2021) shows blending beats stacking.

### Proposed Path Forward: Three Concrete Experiments

**Experiment A: TCN on 5-minute returns (DeepVol-style)**
- Input: 78 bars of raw 5-min log returns per day, pooled across 21 symbols
- Architecture: Dilated causal TCN, 8 layers, receptive field = 256 (covers full day)
- Target: next-day log-RV (h=1)
- Why it might work: TCN handles fixed-length sequences better than LSTM; raw returns let the model discover its own volatility features; DeepVol achieved SOTA in the literature
- Requires: 5-min bar aggregation from existing 10-second data (trivial)

**Experiment B: LSTM with enriched 5-min features**
- Input: 78 bars x 12+ features: log_ret, abs_ret, vol_share, buy_ratio, order_flow_imbalance, rolling_vpin, cum_rv, session_frac, spread_proxy (if available), price_accel, log_n_trades, volume_surprise (bar_vol / rolling_avg)
- Architecture: 2-layer LSTM, hidden=64, attention pool
- Target: next-day log-RV (h=1)
- Why it might work: the current 2,340-bar sequence is too long; 78 bars with richer features is the right tradeoff. More features per bar means more signal per timestep.

**Experiment C: Prediction blending (LSTM + XGBoost)**
- Train XGBoost champion independently (as-is, trial-067 config)
- Train LSTM/TCN independently on intraday sequences (Experiment A or B)
- Blend: $\hat{y} = w \cdot \hat{y}_{XGB} + (1-w) \cdot \hat{y}_{LSTM}$
- Weight $w$ calibrated on expanding-window validation, possibly regime-dependent
- Why it might work: avoids gradient isolation; each model operates on data suited to its architecture; LSTM sees intraday dynamics the tree can't access; tree handles tabular features the LSTM can't use. Competition evidence strongly favors this over stacking.

### Priority Order

1. **Experiment A first** (TCN on raw 5-min returns) — cheapest to try, closest to proven DeepVol approach, tests whether the problem is architecture (LSTM vs TCN) or data (10s bars vs 5-min returns)
2. **Experiment C next** (blend) — if TCN/LSTM produces even a mediocre standalone forecast, blending with XGBoost can extract value without stacking's gradient isolation
3. **Experiment B only if A fails** — enriched features are more engineering work, and if raw returns don't work at 5-min, enriched features probably won't either

### Requirements Before Running

- [ ] Implement 5-minute bar aggregation from 10-second sequence parquets (trivial groupby)
- [ ] Implement TCN model class (currently stub with `NotImplementedError`)
- [ ] Add prediction blending infrastructure to the pipeline runner
- [ ] Test on SPY single-symbol first, then pooled 21-symbol

---

<!-- Backfilled from memory/research/research-journal.md by Plan 06 wfo-06-2 (2026-07-29) — entries older than 2026-06-05 that only existed in the memory copy pre-conversion. -->

## 2026-06-03 — IV Tenor Matching: 1w ATM IV for Short Horizons

**Hypothesis:** HAR-IV with 1w ATM IV (7 days) should outperform 1m ATM IV (30 days) at short forecast horizons (h=1, h=5) because the option tenor matches the forecast window more closely.

**Implementation:**
- Added `1watms -> iv_1w_atm` to edrvol.py ingestion (38/39 symbols have data, XOM missing)
- Computed `log_atm_iv_1w_d` and `iv_term_slope_1w1m_d` in options.py
- Registered `har_iv_1w` model in har_family.py (4 features: log_rv_d/w/m + log_atm_iv_1w_d)

**Trial-032 (linear models):** Hypothesis confirmed.
- h=1: har_iv_1w QLIKE 0.1403 vs har_iv 0.1500 (+97 bps, DM p=0.0)
- h=5: har_iv_1w QLIKE 0.1072 vs har_iv 0.1188 (+115 bps, DM p=0.0)
- h=22: har_iv_1w QLIKE 0.1843 vs har_iv 0.1737 (-107 bps) — 1m tenor wins as expected

**Trial-033 (LightGBM init_score):** Partial carrythrough.
- h=1: lgbm w/ 1w init 0.1336 vs 1m init 0.1344 (+8 bps, marginal)
- h=5: lgbm w/ 1w init 0.1077 vs 1m init 0.1123 (+46 bps, meaningful)
- h=22: lgbm w/ 1m init 0.1764 vs 1w init 0.1818 (+54 bps for 1m)

**Key insight:** Trees can partially compensate for suboptimal init (97 bps linear gap shrinks to 8 bps for LightGBM at h=1), but init quality still matters at h=5 where the gap is larger (115 bps linear, 46 bps LightGBM).

**NEW ALL-TIME BESTs:** h1=0.1336, h5=0.1077, h22=0.1764 (all trial-033, per-horizon optimal init).

**LOCKED config created:** `trial_033_lgbm_tenor_matched_LOCKED.yaml` (per-horizon init: har_iv_1w for h=1/h=5, har_iv for h=22). Not yet validated with a run.

---

## 2026-06-01 — train_size Scaling Law RETRACTED (COVID Exclusion Artifact)

**CRITICAL FINDING:** The "monotonic scaling law" (504d < 756d < ... < 1764d) was entirely a COVID exclusion artifact. Longer train_size pushes the first OOS test date past Feb 2020, excluding the high-error COVID period from evaluation. On the common test period (2022-01-20 to 2024-07-24), 504d and 1764d produce IDENTICAL QLIKE (0.1155 for h=1).

**Evidence:**
- 504d full OOS (2017-2024, includes COVID): QLIKE 0.1445
- 1764d full OOS (2022-2024, excludes COVID): QLIKE 0.1155
- 504d restricted to 2022-2024 only: QLIKE 0.1155 (MATCHES 1764d exactly)
- COVID period (Feb-Dec 2020) QLIKE: 0.1815 (5335 rows)
- COVID inflates 504d full-OOS by: 51.8 bps

**Transition point:** train_size >= 1512 completely excludes COVID from test set.

**Retracted claims:**
- "Total improvement from scaling alone: h=1 +236 bps, h=5 +448 bps" — FALSE, was measuring COVID removal
- "train_size=1764 is optimal for h=1/h=5" — FALSE, no improvement over 504d on common period
- "With init_score, longer windows help because residuals more stable" — WRONG rationalization

**Corrected scorecard:** h=1 best = 0.1391 (trial-023, 504d, full OOS incl COVID), h=5 = 0.1148.

**CV audit addendum:** Pipeline is mechanically correct (no lookahead), but cross-config comparisons with different train_sizes are invalid because they evaluate on different time periods. This was NOT caught by the code-level audit — it's a study design flaw, not a code bug.

**Lesson:** When using expanding-window CV, configs with different min_train_size produce non-overlapping test sets. Any QLIKE comparison across such configs MUST restrict to common dates. COVID is the dominant confound in 2015-2024 equity vol data.

---

*(Previous entry preserved below for audit trail)*

### 2026-06-01 (original, RETRACTED) — Per-Horizon CV + Expanded Universe

**Discovery:** h=1/h=5 benefit monotonically from longer train windows. Full scaling sweep: 504d < 756d < 1008d < 1260d < 1512d < 1764d. Plateau at 1764d (7yr) — h=1 reverses at 2016d (8yr), h=5 gains <1 bps. h=22 collapses with windows >504d.

**RETRACTED:** See corrected entry above. The "scaling law" was a measurement artifact.

**CV audit passed:** Mechanically correct (no lookahead). But missed the test-period comparability issue.

**Implementation:** `cv_for_horizon(h)` in ExperimentConfig + 3 call sites in runner.py. Universe: 23 symbols (added JPM, QQQ; excluded META). These code changes remain valid and useful.

## 2026-05-22 — LightGBM Beats HAR (Per-Symbol Interaction Root Cause)

**Root cause found:** Commit `4cb070f` ("replace proxy features with actual market data") replaced per-symbol `atm_iv * log_rv_d` with market-wide `VIX * log_rv_d`. In pooled training (21 symbols stacked), market-wide VIX is identical for all symbols on the same date, eliminating 21x cross-sectional variation. This degraded QLIKE from 0.1556 to >0.16.

**Fix:** Added `atm_iv_x_log_rv_d` (per-symbol ATM IV * log(RV)) alongside market-wide `vix_x_log_rv_d` in OptionsLayer. Kept all new actual-data features (butterfly, risk-reversal, treasury yields, VIX). Removed cross_asset layer (market-wide VIX levels hurt performance when options layer already provides the interaction).

**Results (h=1):** QLIKE 0.1574, DM stat 2.85, p=0.0044. LightGBM is #1 in tournament, statistically significant improvement over HAR. Best R-squared (0.7629) and MSE (0.2867) among all models.

**h=5/h=22:** Still underperform HAR. Likely needs horizon-specific config (longer train_size, different features).

**Key lesson:** In pooled training, per-symbol features >> market-wide features. Design all interactions to vary across the cross-section.

## 2026-05-21 — LightGBM Underperformance Diagnosis

**Root cause found:** Calendar layer index type mismatch caused pd.concat to double rows (2516 -> 5032). LightGBM was training on half-NaN data. Fixed by restoring original index after DatetimeIndex conversion.

**Secondary weakness:** VRP uses backward-looking RV instead of HAR-forecast expected RV (Bollerslev 2009 spec). Fixed: now uses HAR h=22 forecast.

**Data audit results:**
- All 21 symbols use consistent datetime.date index (no other mismatches)
- SPY has 333 NaN in rk from 2023-09-08 onward (tail data gap, not a bug)
- Cross-symbol date differences are 1-3 boundary dates (negligible)
- IV features have 2515/2516 valid rows (excellent coverage)
- Pooled mode handles per-feature NaN gracefully (LightGBM tree routing)

**Actionable improvements identified:**
1. Fix VRP to use HAR h=22 forecast as E[RV] (done)
2. Add `_w` rolling variants for iv_rv_gap, butterfly, term_slope
3. Event-implied vol is P3 (needs term structure math)

## 2026-05-06 — Approach Reset

**Decision:** Shift from sprint/task planning to research-first exploration.
- 8 days went from kickoff to 27-task plan without touching real data
- Plan built from literature, not from actual RV exploration
- Feature engineering is core value-add; need hands-on data exploration first
- Each session focuses on understanding one thing deeply

## 2026-05-06 — Feature Engineering & Optiver Deep Dive

**Optiver 2021 Competition (10-min RV, ~112 stocks):**
- LightGBM dominated; NNs never beat well-tuned trees
- 1st place won via competition-specific leakage (chronological order recovery)
- Top honest features: price acceleration, volume-weighted sub-windows, spread dynamics, OBI
- 91st place (well-documented): 600 features, LightGBM DART, lr=0.05, max_leaves=255

**Model Architecture Decision:**
- Start: LightGBM on engineered tabular features (data is fundamentally tabular at daily frequency)
- DL value-add: LSTM/TCN on full-day E-mini tick sequences (richer than Optiver's 600sec windows)
- Hybrid: LSTM embedding fed to LightGBM (prediction-level blend, NOT feature-level)
- Critical: don't hyperparameter-search the NN; pick one architecture, train once per DSR

**Progression:** HAR baselines → Ridge on expanded features → LightGBM (nonlinear?) → LightGBM + LSTM

**Open threads for next sessions:**
- What does RV actually look like on tick data?
- Compute HAR and see where it fails
- Test price acceleration at daily frequency

## 2026-05-08 — RV Estimation Strategy

**Question:** Which RV estimator(s) to compute from our tick data?

**Key finding:** Liu et al. (2015) — 400 estimators, 31 assets: noise-robust estimators rarely beat 5-min RV for *forecasting*, even though they improve *estimation* accuracy. This is decisive.

**Decision:**
- **Primary target:** 5-min RV (n=78, log-space, no mean subtraction)
- **Compute alongside:** BPV (jumps), RQ (measurement quality), RV⁺/RV⁻ (semivariances), BNS jump test
- **Noise-robust estimators as features:** Realized Kernel from ticks → (RK-RV5min) gap is a liquidity/noise proxy feature
- **NOT as target replacement:** MSRV/RK/pre-averaging are not worth using as the dependent variable

**Computation order:** vol signature plot (validate 5-min) → 5-min RV → BPV/RQ/semivariances → BNS test → RK for subset → HAR baseline

**Open threads:**
- Plot volatility signature plot on our data
- Check RV distribution across 34 symbols
- E-mini RK vs 5-min RV as feature

## 2026-05-08 — Core Implementation Complete

**Implemented all computation modules with 56 passing tests:**

| Module | Functions | Status |
|--------|-----------|--------|
| `features/har.py` | RV, log-RV d/w/m, RQ, HARQ, design matrix | ✅ |
| `features/asymmetry.py` | Semivariances, BPV, TPQ, BNS z-test, C/J decomposition | ✅ |
| `features/noise_robust.py` | Realized Kernel (Parzen), TSRV, Pre-averaged RV, vol sig plot, noise gap | ✅ |
| `models/baselines.py` | HAR, HARQ, SHAR, HAR-J, HAR-CJ, Ridge-HAR, Lasso-HAR | ✅ |
| `evaluation/metrics.py` | QLIKE (log+var space), MSE, MAE, R², improvement bps | ✅ |

**Key implementation findings:**
- BNS jump test needs tri-power quarticity (not standard RQ) in denominator — RQ is inflated by jumps
- `build_har_design_matrix` handles lag-1 shift internally — don't double-shift the target
- NumPy 2.x removed `np.math.gamma` — use `math.gamma` from stdlib
- HAR on AR(1) synthetic log-RV with ρ=0.93 achieves R² > 0.3 (as expected)
- RK correctly removes noise bias vs naive tick-level RV (verified with synthetic noise injection)

**Still unimplemented (waiting for GS data access):**
- Data layer: tsdb.py, marquee.py, ingest.py (chunk_store.py now done)
- Feature layers 2-5: microstructure, options, calendar, cross-asset
- Ensemble models

## 2026-05-08 — Data Pipeline Implemented + PDF Cross-Reference Gap Analysis

**Shipped (data pipeline, 90 tests passing):**
- `data/chunk_store.py`: L1 trades/quotes, L2 depth for E-mini, 34-symbol universe, contract rolling
- `data/resample.py`: tick-to-bar resampling + full daily RV pipeline (14 output fields)
- All tests passing: 56 (core math) + 34 (data pipeline) = 90 total

**PDF cross-reference: Layer 0-1 gaps identified against vol-project-ref.pdf and vol-learning-guide.pdf:**

See `memory/research/layer01-gap-analysis.md` for the full detailed gap analysis with paper citations and priority rankings.
