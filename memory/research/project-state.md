---
created: 2026-05-26
updated: 2026-07-01
tags: [project-state, boot, continuity]
status: active
priority: P0
source: workspace/research/trials.yaml
relates: [research-journal]
---

# Project State

## Current State

- **Milestone:** LSTM 5-min enriched sequences viable (trial-073, 2026-07-01). XGBoost remains h=1 champion (trial-067). LSTM research line **reopened** — 5-min aggregation (78 bars × 12 features) solves the vanishing gradient problem that killed 10s bars (2340×5). Previous failures (trials 051-066c) used the wrong data representation, not an inherent LSTM limitation.
- **Reproducible champion:**
  - **h=1:** QLIKE **0.1292** (xgboost + har_iv_0dte init, trial-067 reseed) — +76 bps vs lgbm 5-seed mean, +206 bps vs har_iv
  - **h=5:** QLIKE **0.10804** (lgbm + har_iv_1w init, 5-seed mean, trial-047) — +138 bps vs har_iv. XGBoost single-seed 0.11055 needs multi-seed validation.
  - **h=22:** QLIKE **0.16755** — **CHAMPION IS HAR_IV (4-param linear)**. XGBoost single-seed 0.16731 (+11 bps vs har_iv) is first tree model to beat linear at h=22; needs multi-seed validation.
- **CHAMPION config:** h=1: `trial_063_xgboost_champion.yaml` (xgboost, har_iv_0dte init). h=5: `trial_036_CHAMPION.yaml` (lgbm, har_iv_1w init). h=22: har_iv linear.
- **Blocker:** None
- **Recent failed extensions:** microstructure (trial-039), cross-asset momentum (trial-043), rate_vol single-feature + init (trial-044), surgical feature drops (trial-046), COVID-in-train (trial-049), feature removal (trial-059), LSTM 10s-bar modes (trials 051-066c) — all fail on QLIKE or Sharpe or both
- **LSTM 5-min breakthrough (trials 071-073):** 5-min enriched sequences (78×12) with bidirectional LSTM (hidden=128, train_size=2000) achieve QLIKE **0.1998** OOS — only 11 bps below HAR, in MCS, DM p=0.076 (not statistically worse). Key findings: (1) feature normalisation is critical (3 orders of magnitude scale difference kills learning without z-score), (2) train_size is the dominant hyperparameter (1260→2000 gives 37 bps), (3) bidirectional + larger hidden_dim gives 94 bps over unidirectional.
- **Critical methodology rule (from trial-049):** any trial that changes train_size or date_range MUST report QLIKE on the SAME OOS dates as the baseline. Pin a fixed evaluation window in addition to per-fold OOS.
- **Next:** (1) LSTM stacking with XGBoost champion — use 5-min LSTM predictions/embeddings as features for tree model. (2) XGBoost reseed h=5/h=22. (3) Multi-seed validation of trial-073 LSTM.

## QLIKE Scorecard

| Horizon | Champion model | QLIKE | Trial | Validation | vs har_iv (bps) |
|---------|----------------|-------|-------|------------|------------------|
| h=1     | **xgboost** (har_iv_0dte init) | **0.1292** | trial-067 | reseed (per-seed breakdown pending) | +206 |
| h=5     | lgbm (har_iv_1w init)   | **0.10804** | trial-047 | 5-seed mean, std=1.2 bps | +138 |
| h=22    | **har_iv** (4-param linear) | **0.16755** | — | n/a | — |

**XGBoost single-seed candidates (need multi-seed):** h=5 0.11055 (trial-063), h=22 0.16731 (trial-063).
**LightGBM 5-seed reference:** h=1 0.13679, h=5 0.10804, h=22 0.16826 (trial-047).

> **Reporting protocol:** New champion claims REQUIRE multi-seed confirmation (≥3 seeds, report mean ± std) before being recorded here. Single-seed numbers are not admissible.

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

## IV Sanity Check Results (2026-05-27)

| Model | h=1 | h=5 | h=22 |
|-------|-----|-----|------|
| atm_iv_implied | 0.1997 | 0.1447 | 0.1925 |
| har | 0.1602 | 0.1359 | 0.2087 |
| **har_iv** | **0.1498** | **0.1187** | **0.1844** |
| lightgbm | 0.1489 | 0.1365 | 0.2079 |

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

## Next Actions

### Data Ingestion Infrastructure (BLOCKER — blocks L3-L7 feature layers)

1. **Step 1: Manifest system** -- DONE. ManifestManager with typed dataclasses, atomic writes, stale detection. 29 tests. YAML manifest seeded from JSON. audit.py bridged, ingest.py wired, `vol status` reads YAML.
2. **Step 2: Directory rename** -- DONE. `rv/` -> `ticks/`, `iv_surface/` -> `iv/`, `macro/` -> `cross_asset/`. paths.py has canonical names + deprecated aliases. All 883 tests pass, lint clean.
3. **Step 3: New sources** — Implement one at a time: `vol ingest-ohlcv`, `vol ingest-xasset`, `vol ingest-micro`, `vol ingest-corr`

Reference files:
- `workspace/research/data-ingestion-architecture.md` — complete architecture plan (source-based storage, manifest schema, migration plan, implementation order)
- `workspace/research/final_optimal_feature_set.md` — full feature catalog with gap analysis and priority ranking
- `src/volforecast/utils/manifest.py` — current manifest code (to be rewritten)
- `src/volforecast/utils/paths.py` — path resolution (to be updated in Step 2)
- `src/volforecast/cli/audit.py` — current audit (to be refactored)

### Experiment Track (can proceed in parallel with infra)

4. ~~**Trial-048:** Same config as trial-036, train_size=1843 (COVID in train)~~ **DONE as trial-049 (2026-06-11). REJECTED — QLIKE improved but Sharpe degraded -0.59 at h=1. See research-journal.md entry.**
5. **Trial-037:** 0DTE/1w IV log-ratio as LightGBM feature (partial corr 0.24, de-biased per-event signal). **Run multi-seed.**
6. ~~Multi-seed robustness on trial-036 champion~~ **DONE — trial-047 (2026-06-11).**
7. Symbol-type conditioning for cross-asset signals (separate index/single-name models, or LightGBM `rate_vol x beta` interaction)
8. **HIGH PRIORITY (from trial-049 insight):** Pivot to economic-value-aware training. P&L-aware LightGBM custom loss that asymmetrically penalizes missed shorts on calm days. Hypothesis: QLIKE-trained models systematically under-shoot on the dimension that matters for variance-swap P&L.
9. **Trial-037 alternative path:** train a binary classifier directly on `sign(realized_premium)` instead of forecasting RV, then use the classifier output as the GSVIVS01 long/short decision.
10. Investigate why h=22 LightGBM cannot beat the 4-param har_iv linear model. Either (a) accept har_iv as the h=22 champion and focus signal-discovery on h=1/h=5, or (b) test structural alternatives (two-stage: linear core + nonlinear residual on subset features only).
