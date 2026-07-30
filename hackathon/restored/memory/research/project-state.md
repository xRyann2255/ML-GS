---
created: 2026-05-26
updated: 2026-07-29
tags: [project-state, boot, continuity]
status: active
priority: P0
source: workspace/research/trials.yaml
relates: [research-journal]
---

# Project State

## Current State

- **Milestone:** Dealer gamma (GEX) confirmed as new h=22 champion (trial-098, 2026-07-28). XGBoost+GEX 5-seed mean 0.16071 beats HAR_IV by +68 bps. First tree model to reproducibly beat linear at h=22.
- **Reproducible champion:**
  - **h=1:** QLIKE **0.1292** (xgboost + har_iv_0dte init, trial-067 reseed) — +76 bps vs lgbm 5-seed mean, +206 bps vs har_iv
  - **h=5:** QLIKE **0.10804** (lgbm + har_iv_1w init, 5-seed mean, trial-047) — +138 bps vs har_iv. XGBoost single-seed 0.11055 needs multi-seed validation.
  - **h=22:** QLIKE **0.16071** (xgboost + dealer_gamma + har_iv init, 5-seed mean, trial-098) — **+68 bps vs har_iv**. std=0.3 bps. All 5 seeds DM p < 5e-06 vs har_iv.
- **CHAMPION config:** h=1: `trial_063_xgboost_champion.yaml` (xgboost, har_iv_0dte init). h=5: `trial_036_CHAMPION.yaml` (lgbm, har_iv_1w init). h=22: `trial_098_gex_reseed_h22.yaml` (xgboost + dealer_gamma, har_iv init).
- **Blocker:** None for the champion (tree-model) track; data-ingestion BLOCKER for L3-L7 feature layers (see Data Ingestion Infrastructure below).
- **Recent successes:** Dealer gamma (GEX) — first new feature since tree_expansion to improve any horizon. +68 bps at h=22, -42 bps at h=1 (signal dilution at short horizon).
- **Recent failed extensions:** microstructure (039), cross-asset momentum (043), rate_vol (044), surgical drops (046), COVID-in-train (049), feature removal (059), LSTM 10s-bar (051-066c) — all fail on QLIKE or Sharpe or both.
- **LSTM research line reopened 2026-07-01 via trial-073** (previously closed 2026-06-22; closure entry moved to the research journal). 5-min enriched sequences (78×12) with bidirectional LSTM achieve QLIKE 0.1998 OOS — 11 bps below HAR, in MCS, DM p=0.076.
- **Critical methodology rule (from trial-049):** any trial that changes train_size or date_range MUST report QLIKE on the SAME OOS dates as the baseline. Pin a fixed evaluation window in addition to per-fold OOS.
- **Operative methodology (present-tense; full history in research-journal.md):** per-symbol > market-wide features in pooled training; VRP uses HAR h=22 forecast as E[RV] (Bollerslev 2009); IV alignment uses IV[T], not IV[T-1]; tree_expansion stays on (+70 `_change`/`_zscore`, +31.5 bps); 128 features + min_child=150; horizon-specific feature sets required (per-horizon init: har_iv_1w for h=1/h=5, har_iv for h=22, per trial_033_lgbm_tenor_matched_LOCKED.yaml); HAR-IV is the reference to beat; GSVIVS01 long_flat uses threshold=0 (walk-forward optimal), and walk-forward is mandatory for any signal-layer hyperparam; `harx` + siblings are the config-driven path for Layer-N-plus-HAR probes.
- **Next:** (1) GEX interaction features (gex × iv_term_slope, gex × vrp) for h=22. (2) Horizon-specific feature set (GEX only at h=22, exclude from h=1/h=5). (3) LSTM stacking with XGBoost champion.

## QLIKE Scorecard

| Horizon | Champion model | QLIKE | Trial | Validation | vs har_iv (bps) |
|---------|----------------|-------|-------|------------|------------------|
| h=1     | **xgboost** (har_iv_0dte init) | **0.1292** | trial-067 | reseed (per-seed breakdown pending) | +206 |
| h=5     | lgbm (har_iv_1w init)   | **0.10804** | trial-047 | 5-seed mean, std=1.2 bps | +138 |
| h=22    | **xgboost + dealer_gamma** (har_iv init) | **0.16071** | trial-098 | 5-seed mean, std=0.3 bps | +68 |

**XGBoost single-seed candidates (need multi-seed):** h=5 0.11055 (trial-063).
**LightGBM 5-seed reference:** h=1 0.13679, h=5 0.10804, h=22 0.16826 (trial-047).

> **Reporting protocol:** New champion claims REQUIRE multi-seed confirmation (≥3 seeds, report mean ± std) before being recorded here. Single-seed numbers are not admissible.

> **Retracted results, IV sanity table, and full Key Decisions log** — moved verbatim to `workspace/research/research-journal.md` under the 2026-07-29 pruning entry (Plan 06, AW-16).

## Next Actions

### Data Ingestion Infrastructure (BLOCKER — blocks L3-L7 feature layers)

1. **Step 1: Manifest system** -- DONE. ManifestManager with typed dataclasses, atomic writes, stale detection. 29 tests. YAML manifest seeded from JSON. audit.py bridged, ingest.py wired, `vol status` reads YAML.
2. **Step 2: Directory rename** -- DONE. `rv/` -> `ticks/`, `iv_surface/` -> `iv/`, `macro/` -> `cross_asset/`. paths.py has canonical names + deprecated aliases. All 883 tests pass, lint clean.
3. **Step 3: New sources** — Implement one at a time: `vol ingest-ohlcv`, `vol ingest-xasset`, `vol ingest-micro`, `vol ingest-corr`

Reference files: `workspace/research/data-ingestion-architecture.md` (architecture plan), `workspace/research/final_optimal_feature_set.md` (feature catalog + priorities), `src/volforecast/utils/{manifest.py,paths.py}`, `src/volforecast/cli/audit.py`.

### Experiment Track (can proceed in parallel with infra)

4. ~~**Trial-048:** Same config as trial-036, train_size=1843 (COVID in train)~~ **DONE as trial-049 (2026-06-11). REJECTED — QLIKE improved but Sharpe degraded -0.59 at h=1. See research-journal.md entry.**
5. **Trial-037:** 0DTE/1w IV log-ratio as LightGBM feature (partial corr 0.24, de-biased per-event signal). **Run multi-seed.**
6. ~~Multi-seed robustness on trial-036 champion~~ **DONE — trial-047 (2026-06-11).**
7. Symbol-type conditioning for cross-asset signals (separate index/single-name models, or LightGBM `rate_vol x beta` interaction)
8. **HIGH PRIORITY (from trial-049 insight):** Pivot to economic-value-aware training. P&L-aware LightGBM custom loss that asymmetrically penalizes missed shorts on calm days. Hypothesis: QLIKE-trained models systematically under-shoot on the dimension that matters for variance-swap P&L.
9. **Trial-037 alternative path:** train a binary classifier directly on `sign(realized_premium)` instead of forecasting RV, then use the classifier output as the GSVIVS01 long/short decision.
10. Investigate why h=22 LightGBM cannot beat the 4-param har_iv linear model. Either (a) accept har_iv as the h=22 champion and focus signal-discovery on h=1/h=5, or (b) test structural alternatives (two-stage: linear core + nonlinear residual on subset features only).
