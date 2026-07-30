# XGBoost Champion Deep Dive: Is 0.129 Real, What Is Broken Around It, and Where the Headroom Is

**Date:** 2026-07-02
**Scope:** full audit of the XGBoost champion (trial-063 lineage), mirroring the LSTM deep dive: implementation correctness, pipeline integration, experiment record, and literature benchmarking. All file:line citations refer to the tracked GS snapshot at `src/volforecast/` (the dev copy predates `xgboost.py` entirely and cannot exercise these paths).
**Companion audit files (working artifacts):** `workspace/tmp/xgb-audit-implementation.md`, `xgb-audit-pipeline.md`, `xgb-audit-record.md`, `xgb-audit-literature.md`.

---

## 1. Executive summary

**Is the champion number trustworthy?** Yes, with one uncomfortable nuance and several corrections to the record:

- The headline h=1 QLIKE ~0.129 is real and validated: XGBoost 5-seed mean **0.1292** (trial-067), +76 bps over the LightGBM 5-seed mean 0.13679, +206 bps over har_iv. The QLIKE custom objective, early stopping, purge discipline, and target construction all verify clean.
- The nuance: **every raw XGBoost prediction is +0.5 too high in log-RV space** (Bug 1). With a custom objective, XGBoost never estimates its intercept and silently adds the default `base_score = 0.5` at predict; the code comment claiming otherwise is false. The reported QLIKE survives ONLY because the per-fold Duan smearing correction cancels a constant bias exactly (the logs fingerprint it: Duan ~ -0.48 for XGBoost vs ~0 for LightGBM). The tournament number is valid; anything consuming raw predictions is not. Trials 069a/b/c (conditional sample reweighting) computed their weights 0.5 off-center and their conclusions are contaminated; any reuse of a saved model outside the pipeline returns levels ~65% too high in variance terms.
- Corrections to the circulating record: the trial-036 LightGBM numbers (0.1289/0.1067/0.1628) are formally rejected (below the 5-seed envelope minimum: parallel-fit nondeterminism); trials 068/068b (conditional Duan) were **no-ops** because the flag never reaches tournament-mode configs; and the champion's provenance is muddled: trial-063 trained 16 leaves/depth 4 (single seed, 0.12895) while the trial-067 reseed that produced the definitive 0.1292 trained **32 leaves/depth 8**. Two different architectures landing on the same number is reassuring about robustness and embarrassing about bookkeeping; the canonical champion config should be settled explicitly.
- One likely free win: through a horizon-override asymmetry (Bug 3), the tournament champion label ran **h=5 with the 0-DTE init instead of har_iv_1w**. Its h=5 number (0.11055, loses to har_iv_1w) was produced with the wrong tenor. Rerunning h=5 correctly tenor-matched may flip that verdict at zero research cost. h=22's single-seed +11 bps tree win (0.16731) also awaits its queued reseed.

**Literature verdict:** the construction is ahead of print. No peer-reviewed work combines GBM + QLIKE objective + boosting from a HAR-IV base; nothing published in 2024-26 beats an IV-augmented linear baseline at h=1 by more than ~1.5% QLIKE, while this champion sits ~15% below tenor-matched HAR-IV. The implication cuts both ways: there is no external recipe to copy, and the remaining headroom is in identified levers (cross-stock spillovers, overnight decomposition, richer surface functionals, combinations), not in swapping learners.

---

## 2. What the champion actually is (as built)

- **Model:** XGBoost regressor, custom QLIKE objective in log-RV space: grad = 1 - exp(y - yhat), hess = exp(y - yhat), clipped at +/-10, algebraically identical to the evaluation metric (verified, finite-difference tested). Early stopping (150 rounds, 5000 cap) on a 15% date-aware validation tail with `val_purge_gap` clamped to >= h on the tabular path (`runner.py:509-511`).
- **Base injection:** per-fold HAR-IV linear model (tenor-matched per horizon) supplies `base_margin` on the train, validation, and HPO-test DMatrices (added exactly once during training, verified); at predict, tree output plus the base model's prediction, plus the unintended +0.5 (Bug 1).
- **Features:** 7 layers (`iv_surface, har_core, asymmetry, noise_robust, options, calendar, tree_expansion`), ~128 columns after the change/zscore expansion (trailing rolling-20, causal, no lookahead, verified `features/expansion.py:36-39`). Excluded layers: microstructure, cross_asset(_momentum), long_memory, realized_correlation, implied_correlation. Note: `drop_vrp_calendar` is a VARIANT config that removes 8 SHAP-bottom VRP/calendar features; it has **no recorded QLIKE result anywhere**, yet its dashboard is the one the desk-pitch presentation regenerates from. The champion proper keeps all 7 layers' features.
- **Training:** pooled 21 symbols, log-RV target `log((1/h) sum RV_{t+1..t+h})`, expanding-window CV 504/126 with 10-date purge, GPU-parallel folds (cuda:0-7), per-fold seeds `42 + fold_num` on the parallel path.
- **Evaluation:** pooled log-space QLIKE over concatenated OOS folds; per-fold Duan smearing constant added (which is what neutralizes Bug 1); DM tests and MCS in the tournament (with a caveat, Bug 7).
- **The measured local optimum:** every feature ADD failed (microstructure -86 bps, rate_vol -112 bps, realized correlation flat, 0DTE ratio zero) and every REMOVE failed (trials 045/046/059). The champion's edge is the tenor-matched linear init plus tree corrections on IV-family and expansion features (tree_expansion alone: +31.5 bps across 5 seeds).

### The scoreboard (definitive numbers after record reconciliation)

| Horizon | Champion | QLIKE | Status |
|---|---|---|---|
| h=1 | XGBoost, har_iv_0dte init | **0.1292** (5-seed mean, trial-067) | Validated; DM vs LightGBM p~0 (but see Bug 7 on DM inflation); per-seed envelope never recorded, only the aggregate |
| h=5 | LightGBM, har_iv_1w init | **0.10804 +/- 0.00012** (trial-047, 5-seed) | XGBoost's 0.11055 was run mis-tenored (Bug 3); rerun pending |
| h=22 | har_iv (4-parameter linear) | **0.16755** | XGBoost 0.16731 (+11 bps, first tree win here) is single-seed, reseed queued |
| Rejected | LightGBM trial-036 trio | 0.1289 / 0.1067 / 0.1628 | All below the 5-seed envelope minimum; do not cite |

---

## 3. Real errors found

| # | Severity | Bug | Mechanism | Fix |
|---|---|---|---|---|
| 1 | HIGH (latent for the headline, live elsewhere) | **+0.5 base_score bias on every raw prediction** | With a custom objective XGBoost 3.x never estimates the intercept and `DefaultBaseScore()=0.5`; predict's DMatrix carries no `base_margin` (`models/xgboost.py:512-524`), so tree output arrives +0.5 in log-RV. The line-513 comment ("tree output only") is false. Per-fold Duan correction (`runner.py:99-110, 615-630`) computes residuals through the same biased predict and cancels the constant exactly, so tournament QLIKE is valid. Live damage: `_compute_reweight(source="conditional")` (`xgboost.py:461-468`) weighted samples 0.5 off-center, contaminating trials 069a/b/c; saved-model reuse returns biased levels; any future consumer of raw predictions inherits the bias. | Set `base_score: 0.0` in params at construction; add a prediction-level round-trip test (fit on synthetic data with known target level, assert unbiased). Re-run 069 afterward: the reweighting hypothesis has never actually been tested. |
| 2 | HIGH (already fired) | **`conditional_duan` is a no-op in tournament mode** | The tournament label builder (`evaluation/_parallel.py:83-187`) constructs synthetic ExperimentConfigs that drop `seed` and `conditional_duan`. Trials 068/068b trained plain champions; their "conditional Duan adds nothing" reading is void because conditional Duan never ran. | Forward the flag through the synthetic config; rerun 068/068b (expected +10-40 bps at h=1 per the original design note, and it also becomes more interesting post-Bug-1 fix). |
| 3 | HIGH (mis-measured results) | **Horizon-override asymmetry** | `_parallel.py:151-166` strips `model:` horizon overrides for bare tournament labels but leaves them unsanitized for `model_configs` labels. Consequences: the champion label `xgb_hariv0dte_init` ran h=5 with the 0-DTE init (not har_iv_1w) and h=22 with har_iv; `trial_063_xgboost_hpo_8gpu` ran h=1 with the wrong `har_iv_1w` init; the truncated `trial_067_xgb_29sym` lost tenor matching entirely. | Make override handling uniform (explicit per-horizon `model_configs`, or sanitize nothing and validate params per model class). Rerun XGB h=5 correctly tenor-matched: possible free win vs 0.11055. |
| 4 | DATA INTEGRITY | **Two trial-067 configs truncated mid-key** | `trial_067_xgb_29sym.yaml` and `trial_067_xgb_gsvivs01_eval.yaml` end mid-`explainability:`; empty `tournament.models` silently degrades runs to the bare model with no baselines. Likely QR-video transfer damage. | Restore from GS HEAD before any rerun; add a config-completeness lint (every config parses and has non-empty tournament.models when tournament is enabled). |
| 5 | MODERATE | **Seed divergence, sequential vs parallel** | Parallel folds use `seed + fold_num` (`runner.py:92`); the sequential loop uses constant seed (`runner.py:607`). The champion ran parallel (seeds 43+); trial-067's reseed config has no `n_gpus` so its arms ran sequential constant-seed; LightGBM is excluded from the parallel gate so 036 ran constant-seed while 063 ran offset-seed. The 067 5-seed mean caps practical impact, but no two of these runs are bit-comparable. The seed test asserts nothing (`test_xgboost_gpu_folds.py:149-191`). | Unify on `seed + fold_num` everywhere; make the test assert actual per-fold seeds. |
| 6 | MODERATE | **HPO tunes a different model than production** | The tabular HPO plumbing itself is sound (sampled params reach the final fit, `xgboost.py:603-629`, unlike the LSTM tuner), but the inner objective uses a constant-mean init instead of the HAR-IV base (`xgboost.py:693`) and row-based inner CV where purge_gap=10 means 10 ROWS (~half a day on a 21-symbol panel): leaky, optimistic, and mis-specified relative to the production model. Plus stale-study risk: fixed Optuna study name with `load_if_exists` reuses old trials after config edits (`xgboost.py:872-882`). | Give the inner objective the real base model and date-based inner CV with purge in dates; key the study name on a config hash. |
| 7 | MODERATE (statistics) | **DM/MCS treat the pooled panel as one series** | Loss differentials are computed over stacked (date, symbol) rows (`evaluation/tournament.py:567, 828`), treating 21 same-date observations as independent: cross-sectionally inflated t-stats. The +76 bps XGB-vs-LGBM gap is likely still significant, but "DM p=0.0" overstates certainty. Also the YAML `baseline:` key is parsed nowhere; DM is always vs plain `har`. | Aggregate loss diffs per date (mean across symbols) before DM; wire or delete the `baseline:` key. |
| 8 | MODERATE (product) | **Explainability silently dead on GPU-parallel runs** | Parallel folds return `model=None` (`runner.py:808`) and the dashboard's SHAP/ALE tabs require trained models (`visualization/tournament_dashboard.py:259`). Any champion dashboard produced by an 8-GPU run has empty explainability, which matters because the desk-pitch presentation toggles to exactly those tabs. | Retain the final fold's booster (or refit once post-run) for explainability; verify the presentation's dashboard actually has SHAP/ALE content on GS. |
| 9 | MILD | **HAR-IV base fit includes the early-stopping val rows** (`xgboost.py:216`) | Optimistic val margins bias the stopping round; identical in LightGBM so the 063-vs-036 comparison stays fair; outer test predictions clean. | Fit the base on the pre-val split only. |
| 10 | MILD | **`params.pop("drop_features")` corrupts refits** | Popping during fit mutates `get_params()`, so the runner's cached-params refit (`runner.py:599-601`) silently drops the feature-drop on folds 2+ under tuning (and shifts LightGBM's positional monotone constraints). | Read without popping. |

Also latent, inherited from the shared config layer: `cv_for_horizon` drops `embargo` on horizon overrides (`config.py:515-521`); no tree trial currently sets embargo, but trial-063 does use horizon_overrides. And trial-069's implied-correlation A/B is invalid for a different reason: `feature_layers_override` is unimplemented, so the control arm saw treatment features.

**Verified clean (do not re-audit):** QLIKE objective math and metric identity; base_margin present on train/val/HPO-test DMatrices during training; date-aware early-stopping split with `val_purge_gap >= h` clamp on the tabular path; outer CV purge on unique dates; tree_expansion causality; target index math; prediction/actual alignment; har_iv_0dte input timing (IV observed at close t for target t+1; note it is SPX market-wide IV applied to all 21 symbols, and har_iv_0dte silently degrades to plain HAR where IV is all-NaN).

---

## 4. Literature verdict (full citations in `xgb-audit-literature.md`)

- **The construction is validated and ahead of print.** Christensen-Siggaard-Veliyev (2023, JFEC) is the closest published analogue (trees/NNs beat HAR by ~10-11% daily, gains concentrated in ordinary regimes, IV among the dominant features), but it trains and evaluates on MSE only, per stock, with 12 features. HARNet's finding that HAR-consistent initialization is what stabilizes QLIKE training is the published justification for the init_score/base_margin design. Puke & Schweikert (2026) note QLIKE is the gamma deviance: cross-checking the custom objective against the built-in gamma objective is a free correctness test.
- **Nothing published beats an IV-armed baseline by much at h=1.** Best verified: rough-Heston spot-vol extraction ~1.5% QLIKE over HAR-RV-VIX; GNAR-HARX ties HARX-IV; Branco et al. (2024) find nonlinear ML indistinguishable from linear once IV is included. The in-house ~15% edge over tenor-matched HAR-IV exceeds the published frontier (pooling + residual boosting are the differentiators). Expect diminishing returns and treat any large claimed improvement with suspicion.
- **Top evidence-backed levers, ranked:** (1) cross-stock spillover/commonality features (peer/sector/market RV aggregates; GHAR ~1.8% QLIKE at single-name h=1, the only quantified lever absent from the current 128); (2) equal-weight or MCS-weighted combination of champion + HAR family + seed bagging (combination-puzzle literature; near-free); (3) richer options-surface functionals (BKM risk-neutral skew, IV-surface PCA); (4) overnight/session decomposition plus overnight news counts (Bodilsen-Lunde 2025, significant single-name h=1 QLIKE gains); (5) explicit FOMC/CPI/NFP event dummies if the calendar layer lacks them. **Skip list (evidence negative or misaligned):** VIX futures basis, quantile/distributional heads for point QLIKE, more jump/tail extensions, learner swaps to NNs/transformers.

---

## 5. Improvement plan

### Tier 0: Fix the code (days)
0.1 `base_score: 0.0` + prediction-level round-trip test (Bug 1). Then rerun trials 069a/b/c: the reweighting idea was never actually tested.
0.2 Forward `conditional_duan` into tournament configs (Bug 2); rerun 068/068b.
0.3 Uniform horizon-override handling (Bug 3); restore the two truncated 067 configs from GS HEAD (Bug 4); config-completeness lint.
0.4 Unify fold seeding (Bug 5); make the seed test assert.
0.5 HPO: real base model in the inner objective, date-based purged inner CV, hashed study names (Bug 6).
0.6 Panel-aware DM (per-date aggregation) and wire/delete `baseline:` (Bug 7). Re-quote the headline DM p-values once.
0.7 Keep a final booster for explainability on parallel runs (Bug 8); confirm the presentation dashboard has live SHAP/ALE.

### Tier 1: Fix the record (days, in parallel)
1.1 Declare ONE canonical champion config (recommend: trial-067 architecture, since 0.1292 is its 5-seed number) and retire the ambiguity with trial-063's 16/4 mapping; document that both land ~0.129 (flat optimum).
1.2 Record per-seed envelopes for XGBoost (mean/std/min/max), matching the trial-047 LightGBM protocol.
1.3 Rerun XGB h=5 correctly tenor-matched (har_iv_1w): possible free win vs 0.11055 and vs LightGBM's 0.10804. Reseed the h=22 single-seed +11 bps result.
1.4 Run `drop_vrp_calendar` to a recorded QLIKE (the presentation's dashboard config currently has no registered number), or repoint the presentation at the canonical champion's dashboard.
1.5 Rerun the 29-symbol universe test on the repaired config.

### Tier 2: Evidence-backed feature levers (1-2 weeks, one at a time, 5-seed + panel-aware DM each)
2.1 Cross-stock commonality: market/sector RV aggregates and lagged peer spillovers as new columns (GHAR-style; the strongest published lever missing from the set; note plain realized_correlation already failed, this is different: level aggregates, not pairwise correlations).
2.2 Overnight decomposition: separate overnight-gap variance and session RV channels (currently only an overnight return feature exists in har_core).
2.3 Surface functionals: BKM skew, IV-surface PCA factors (level/slope/curvature already partially covered; test the residual value), EDRVS variance-swap-strike VRP (already P0 on the books).
2.4 Verify calendar layer has explicit FOMC/CPI/NFP dummies (it has distances; dummies for announcement DAYS are the published lever).

### Tier 3: Combination and regime (cheap, high-probability small wins)
3.1 Seed bagging the champion (average 5 seeds' predictions rather than reporting the mean QLIKE of separate models; near-free, typically a few bps).
3.2 Equal-weight or inverse-QLIKE combination of champion + har_iv + har_iv_1w per horizon; the ensemble classes exist as stubs (`models/ensemble.py`), implement SimpleAverage first.
3.3 Regime-aware handling of spike days (3.9% of days = 22% of QLIKE loss, model already wrong at T-1): spike classifier gate (already on the books) or a crisis-shrunk blend toward har_iv, mirroring the h=22 crisis finding (-2227 bps crisis vs +1889 calm for trees).
3.4 Conditional Duan (068 rerun post-fix) is also in this family: per-regime variance correction.

### Tier 4: Discipline
4.1 Every claimed improvement: 5 seeds, same-OOS dates, panel-aware DM, and a GSVIVS01 Sharpe check (trial-049's lesson: QLIKE up does not imply P&L up).
4.2 Cross-check the custom objective against LightGBM/XGBoost built-in gamma deviance once (free correctness audit).
4.3 Do not pursue: learner swaps, distributional heads, VIX basis, more jump features (Section 4 skip list, plus the in-house add/remove history says the tabular set is at a local optimum).

---

## 6. Ready-to-config experiments

| ID | What | Key deltas | Success bar |
|---|---|---|---|
| 076x | Bug-fix validation | base_score=0.0, uniform overrides, panel-aware DM; rerun canonical champion, 5 seeds | reproduces ~0.1292 with honest stats; new canonical baseline |
| 077x | h=5 tenor fix | champion label with har_iv_1w init at h=5, 5 seeds | beat 0.11055; challenge LightGBM 0.10804 |
| 078x | h=22 reseed | trial-063 h=22 arm, 5 seeds | confirm or retire the +11 bps tree win |
| 079x | Conditional Duan, actually on | 068/068b rerun post Tier-0 | +10-40 bps h=1 or bury it |
| 080x | Commonality features | market/sector RV aggregates + lagged peer RV columns | +10-25 bps, DM-significant |
| 081x | Overnight decomposition | overnight-gap RV + session RV as separate channels | any DM-significant gain |
| 082x | Seed-bagged champion + SimpleAverage ensemble | implement stub, bag 5 seeds, blend with har_iv family | +3-10 bps, near-free |
| 083x | Spike-day gate | classifier gate or crisis shrink toward har_iv | spike-day QLIKE improves without calm-day cost; GSVIVS Sharpe check |

---

## 7. Expected impact summary

| Intervention | Expected h=1 QLIKE effect | Cost | Confidence |
|---|---|---|---|
| Tier 0 fixes | 0 direct on the headline; unblocks 069/068, fixes stats, protects downstream consumers | days | High (correctness) |
| h=5 tenor rerun | h=5 only; possibly takes the h=5 crown | trivial | Medium-high |
| Seed bagging + ensemble | +3 to +10 bps | trivial | High |
| Commonality features | +10 to +25 bps | small | Medium (best published lever) |
| Overnight decomposition | +5 to +15 bps | small | Medium |
| Surface functionals / EDRVS VRP | +5 to +20 bps | medium | Medium |
| Conditional Duan (real run) | +10 to +40 bps | small | Unknown (never tested) |
| Spike-day regime handling | small QLIKE, larger GSVIVS Sharpe | medium | Medium |
| Everything compounding | 0.1292 toward ~0.125 is realistic; below 0.12 would exceed anything in print | weeks | Medium |

---

## 8. Appendix

Full audit detail with line-by-line citations: `xgb-audit-implementation.md` (sections B/C/D), `xgb-audit-pipeline.md` (10 integration risks, trial table, unexercised knobs), `xgb-audit-record.md` (chronological results, quotes, feature-set story, open questions), `xgb-audit-literature.md` (9 sections, all URLs). Related: `lstm-performance-deep-dive.md` (the LSTM side of this pair; its feature-stack and blend leads land on top of whatever this plan produces).
