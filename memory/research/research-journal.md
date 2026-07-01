---
created: 2026-05-07
updated: 2026-06-03
tags: [journal, sessions, findings, decisions, exploration]
status: active
priority: P3
source: workspace/research/weekly-progress.md
relates: [optimal-feature-set, microstructure, project-design, lgbm-pooled-lessons]
---

# Research Journal — Summary

Append-only log of exploration sessions. Read at start of every session for continuity.

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
