# Open Questions

Running list of things to investigate. Add questions as they come up. Move to research-journal.md when explored.

## Data Access (Resolved by data probe 2026-05-06)

- [x] Can we access L1 tick data for all 34 symbols? -- **Yes.** 34/34 confirmed via Chunk Store (pytickclient). Tick counts range from 679 (ABBV, 15-min window) to 281K (SPY). See `workspace/tmp/data_audit_sp500_rv_forecasting.md`.
- [x] Is TSDB daily OHLCV available with sufficient history? -- **Yes.** 11.3 years for all 30 equities + 4 ETFs. Fields: close, open, high, low, volume, return.log all confirmed.
- [x] Can we get L2 order book depth? -- **E-mini only.** 488K ticks/day via ESM26m suffix. Equities are L1 only.
- [x] Is VIX and VIX term structure available? -- **Yes.** VIX daily close + 3 VIX futures (front, 2nd, 3rd month) via TSDB.
- [x] Can we access Marquee implied vol surfaces? -- **Yes.** 3,549 rows SPX ERDVOL_PERCENT_STANDARD confirmed. FX IV also available (72 rows).
- [x] Is tick direction (uptick/downtick) available? -- **E-mini only** via PRCTCK_1 field. Not available for equities.
- [x] Cross-asset macro data? -- **Yes.** Treasury yields (2y/5y/10y/30y), USD/JPY, E-mini settle + open interest all confirmed via TSDB.
- [x] ML packages installed? -- **Yes.** arch 8.0, lightgbm 4.6, torch 2.11, shap 0.51, optuna 4.8, statsmodels, sklearn, scipy all in H:\venv312.
- [x] Which RV estimator should be primary target? -- **5-min RV.** Liu et al. (2015): noise-robust estimators rarely improve forecasts. Noise-robust estimators (RK, TSRV) computed as features, not targets. See research journal 2026-05-08.

## Data Understanding (Priority -- do these next, requires computing RV on real data)

- [x] **SPY ingest complete.** 1,695 rows (2015-01-02 to 2025-01-03) cached in `data/raw/rv/SPY.parquet`. Layer 3 microstructure features NOT included in this pass -- will require a separate compute step over the existing cached tick data (no re-fetch needed since ticks are already on disk).
- [ ] **Layer 3 single-pass extension:** Extend `compute_daily_rv_from_ticks()` to also emit microstructure aggregates (spread_mean, spread_std, price_accel, vpin, kyle_lambda). Can recompute from cached ticks without re-fetching from Chunk Store.
- [ ] **RK + noise_gap backfill (BLOCKING for noise_robust features and LightGBM):**
  All 25 cached symbols have `rk` and `noise_gap` at 100% NaN (~60,800 day-symbol pairs total). The `NoiseRobustLayer` requires >= 50% non-null `rk` to emit any features. Without backfill, LightGBM (which requires `noise_robust` layer) gets zero noise-robust features, and Lasso/Ridge never see `log_rk_d`/`log_rk_w`/`noise_gap_d`/`noise_gap_w`.
  - **Command:** `vol backfill-rk --symbol-workers 4 --workers 4 --batch-days 20`
  - **Scope:** 25 symbols x ~2,515 days each = ~60K raw-tick fetches from Chunk Store (TRDPRC_1 only)
  - **Dry run first:** `vol backfill-rk --dry-run` to see exact NaN counts
  - **Subset test:** `vol backfill-rk --symbols SPY --workers 2 --batch-days 5` to validate one symbol first
  - **Runtime estimate:** Each fetch is one trading day of raw ticks per symbol. With 4 threads, expect ~1-3 sec/day. Full backfill ~4-12 hours overnight.
  - **Checkpointing:** Writes to parquet after each batch (10 days default). Safe to kill and resume.
  - **Dependency:** Requires GS network (Chunk Store access via pytickclient). Must run on a GS desktop.
  - **After backfill:** Re-run tournament with `noise_robust` layer to verify Lasso/Ridge get additional features and check if QLIKE rankings change.
- [ ] What does the distribution of daily RV look like for our 34 symbols? Heavy tails? Log-normal?
- [ ] How does 5-min RV compare to tick-level RV on the same asset? How much does microstructure noise matter in practice?
  - Sub-question: Plot volatility signature plots for 3-5 symbols to validate the 5-min choice empirically
  - Sub-question: Is the (RK_tick - RV_5min) noise gap a predictive feature for future vol?
- [ ] What's the autocorrelation structure of RV on our data? Does the 1/5/22-day HAR decomposition actually fit?
- [ ] How do jumps show up in our data? How frequent, how large, which assets?
- [ ] What does the intraday volatility pattern look like? U-shape? How strong?
- [ ] How correlated is RV across our asset universe? Sector structure? Lead-lag?
- [x] **Should ES (263 rows) and META (644 rows) be excluded from pooled training?** -- **ES: EXCLUDE.** Different asset class (futures, 23h trading, 0.997 correlation with SPY = zero unique signal, misses 4/6 key regimes). Belongs in Layer 3 microstructure work only. **META: KEEP.** Same asset class, valid data, 644 rows adds regime diversity (2022 crash + recovery). All active tournament configs already exclude ES.

## Tournament Baseline Verification (Priority -- verify before drawing conclusions)

- [x] **MZ rejecting all models -- bug, not model failure.** Root cause: (1) missing Newey-West HAC standard errors in F-test (OLS s.e. too small → over-rejection), (2) missing Duan retransformation (naive exp systematically underestimates → beta inflated to 1.54). Fixed: with Duan + HAC, HAR gets beta=1.25, p=0.166 (PASS). All prior MZ "Reject" verdicts were false positives.
- [x] **MZ rejecting all models in multi-symbol tournament (21 symbols) -- THREE root causes identified (2026-05-19):**
  1. **Data bug:** `overnight_return` is corrupted for ALL symbols because TSDB open is unadjusted but close is split-adjusted. Ridge/Lasso produce catastrophic predictions (QLIKE > 10K for GOOGL/AMZN/NVDA).
  2. **Duan correction bug:** Parametric `exp(sigma2/2)` underestimates by 5.3% because residuals are fat-tailed (kurtosis=1.29). Non-parametric smearing `mean(exp(residuals))` fixes beta from 1.18 to 1.12.
  3. **Overpowered test:** At N>20K, even beta=1.12 is significantly different from 1.0. This is expected behavior, not a bug. MZ beta should be reported as a diagnostic, not as a pass/fail gate at pooled scale.
- [ ] **Are all 10 models evaluated on exactly the same OOS dates and row count?** If rolling_mean has a different N than HAR, the comparison is invalid. Check per-horizon prediction alignment.
- [ ] **Does rolling_mean genuinely beat HAR at h=5, or is it an alignment artifact?** The rolling_mean uses log_rv_m (22-day MA shifted by 1). At h=5, this could overfit to the averaging window. Compare on a per-fold basis.
- [x] **SHAR worse than HAR -- verified, not a bug.** Features correct (RS+ + RS- = RV to machine precision). Root cause: 6-feature OLS with extreme multicollinearity (RS+_m/RS-_m rho=0.977) on single-stock SPY. beta_neg/beta_pos ratio is 0.88 (not ~2.0 as paper claims). Paper used pooled panel. Fix: multi-symbol pooling or Ridge-SHAR.
- [x] **HARQ worse than HAR -- verified, not a bug.** Interaction feature correctly computed (manual check: zero difference). Root cause: rq_rv_interaction_d is O(0.001) scale; beta_dQ stable negative at h=1 (+12.7 bps) but flips positive at h>=5 (overfits). Paper-spec 4-feature HARQ also fails at h>=5. Extra sqrt_rq_d (rho=-0.996 with interaction) makes 5-feature version strictly worse. Fix: remove sqrt_rq_d, restrict HARQ to h=1 or use Ridge.
- [ ] **Is Lasso/Ridge advantage fair?** They see har_core + asymmetry + noise_robust (many more features) while HAR sees only har_core (3 features). Is the improvement from regularization or from more features? Test: run Lasso on ONLY the 3 HAR features -- does it still beat OLS HAR?
- [ ] **QLIKE vs R-squared disagreement at h=5:** Is this the known calibration-vs-discrimination tradeoff, or does it indicate a data-leakage or evaluation bug in how naive models are scored?

## LightGBM Configuration (M3 -- researched 2026-05-19, updated 2026-05-22)

- [x] **Custom QLIKE objective correct?** Yes. Log-space formulation matches ch11/ch16 derivations. Gradient/hessian verified by finite-difference tests (2026-05-12).
- [x] **Default hyperparameters reasonable?** Yes. Aligned with vol-learning-guide ch11. num_leaves=31, max_depth=5, min_child_samples=50, lr=0.05, feature/bagging_fraction=0.8 all within recommended range for ~1,700 rows.
- [x] **Optuna search space covers correct ranges?** Yes. All parameter ranges match academic recommendations.
- [x] **Does LightGBM beat Ridge-HAR at h=1 with default params (no tuning)?** **NO.** Tested 8 tree configurations (depth 1-5, leaves 2-31, min_child 50-200, lr 0.01-0.05). ALL lose catastrophically (+2700 to +7700 bps vs Ridge). Root cause: insufficient training data (500-1500 rows) for ~60 features. LightGBM requires pooled multi-symbol data (~30K rows) to compete.
- [x] **Does LightGBM beat Ridge-HAR in the POOLED 21-symbol setting?** **YES at h=1 only.** QLIKE 0.1574 vs HAR 0.1601 (DM stat 2.85, p=0.004). **NO at h=5** (0.1527 vs 0.1359, +1237 bps worse) and **NO at h=22** (0.2420 vs 0.2086, +1601 bps worse). Root causes: short train window (504 days), no horizon-specific features, missing monthly IV interactions.
- [ ] **Does dropping tree_expansion (keeping only 20 raw L0+L1 features) help LightGBM on single SPY?** The ~60-feature expanded set overwhelms the small sample. Test with raw features only.
- [ ] **Does adding VIX as a standalone feature improve QLIKE more than tree_expansion?** CSV (2023) identifies VIX x lagged RV interaction as #1 ML source of gains. Test: add `vix_close` from TSDB to feature matrix directly.
- [ ] **DART vs GBDT comparison:** DEPRIORITIZED until pooled LightGBM beats Ridge-HAR at h=5/h=22.
- [ ] **Should early_stopping_rounds scale with n_estimators?** Currently fixed at 150. DEPRIORITIZED.
- [x] **Noise-robust layer contribution:** RK is fully populated (0% NaN). noise_robust layer is active and contributing features (log_rk_d, log_rk_w, noise_gap_d, noise_gap_w). No longer blocked.
- [x] **Is VIX alone (one TSDB feature, no IV surface) enough to give LightGBM a decisive split?** Answered indirectly: per-symbol ATM IV x log_rv was the key feature, not market-wide VIX. Per-symbol IV provides 21x more signal variation in pooled training.
- [ ] **Horizon-specific configs:** Does train_size=1260 + horizon-specific feature selection fix h=5 and h=22? KEY NEXT EXPERIMENT.
- [ ] **Multi-horizon IV interactions:** Add atm_iv_x_log_rv_w, atm_iv_x_log_rv_m. Does this unlock h=22?
- [ ] **Feature reduction at h=22:** Test with only ~20 selected features (log_rv d/w/m, VRP d/w/m, term_slope, atm_iv, vix, iv_x_rv interactions, calendar dummies). Does fewer features + more data fix h=22?
- [ ] **FREE OPT: Add `path_smooth` param (0.1-10.0).** Pure regularization that smooths leaf values toward parent. Especially useful with our shallow trees (depth 4, min_child 150). Add to DEFAULT_PARAMS (~1.0) and Optuna search space. Zero risk. (Audit 2026-05-27)
- [ ] **FREE OPT: Test `linear_tree=True`.** Fits linear model at each leaf instead of constant. Could capture HAR-like linear relationship within tree-defined regimes, potentially subsuming stacking gains in a single model. Risk: 3x training time, may interact poorly with custom QLIKE objective. Test as separate experiment. (Audit 2026-05-27)
- [ ] **FREE OPT: `bagging_freq=1` (subsample every round).** LOCKED uses 3, defaults use 5. `bagging_freq=1` gives maximum stochastic regularization. Standard in most winning Kaggle configs, negligible overhead. Add to Optuna search space. (Audit 2026-05-27)
- [ ] **FREE OPT: Selective `tree_expansion` for h=1 only.** LOCKED config does NOT include tree_expansion layer (~51 features vs ~111-128 with it). Expand only har_core + options columns (not all layers) to add _change/_zscore features where daily momentum matters. Skip for h=22 where fewer features is better. (Audit 2026-05-27)

## Feature Understanding (After data exploration)

- [ ] Does the leverage effect (negative return -> higher future vol) show up clearly in our data? How asymmetric?
- [x] How much do realized semivariances (RS+, RS-) differ in predictive power? -- **Resolved.** On SPY alone with OLS, RS- does NOT dominate (beta ratio 0.88, not 2.0). Multicollinearity at monthly horizon (rho=0.977) makes coefficients meaningless. Need pooled panel or regularization to surface the asymmetry.
- [x] Does realized quarticity (RQ) actually predict HAR residual size, as HARQ assumes? -- **Resolved.** Yes at h=1 only (beta_dQ negative, +12.7 bps). No at h>=5 (coefficient flips sign, overfits). The noise-correction mechanism is genuine but too weak in single-stock SPY to be useful beyond next-day forecasting.
- [ ] What do VIX-RV gaps look like over time? Is the variance risk premium stable or regime-dependent?
- [ ] Do overnight returns predict next-day RV? How much information is in the close-to-open gap?

## Methodological Questions

- [ ] How sensitive are QLIKE rankings to the evaluation window? Does the "best" model change across regimes?
- [ ] How does purged k-fold CV compare to expanding-window in practice on our data?
- [ ] What's the right way to handle the COVID period -- include, exclude, or treat as a separate regime?

## Ensemble Architecture

- [x] Feature stacking (LSTM embeddings -> LightGBM) vs prediction blending (average LSTM + LightGBM outputs): which gives lower QLIKE at each horizon?
  - **ANSWERED 2026-05-27:** For HAR+LightGBM (no LSTM), prediction blending beats feature stacking at h=22. Blend_opt (+1108 bps vs HAR) > feature_stack_har (+789 bps). Feature stacking works but the tree doesn't optimally weight the HAR prediction as just another column. The LSTM question remains open (requires LSTM implementation first).
- [x] Does dynamic regime-dependent weighting help? -- **YES.** Massively. Low-vol optimal w=0.05 (LightGBM); High-vol optimal w=0.80 (HAR). 2-regime model is viable. See research journal 2026-05-27.
- [x] Should we add regime-conditional evaluation? -- **YES.** Already demonstrated: LightGBM degenerates in high-vol (-2227 bps) while excelling in low-vol (+1764 bps). Critical for any ensemble design.
- [ ] Does the LSTM embedding add information beyond Layer 6 features (vol-of-vol, regime duration, Hurst exponent)? If L6 subsumes the regime information, stacking adds complexity without value.
- [ ] How stable are LSTM embeddings across walk-forward retraining windows? Measure cosine similarity of embeddings from consecutive LSTM retrains. If embedding space rotates, tree features become unstable.
- [ ] Optimal embedding dimensionality: 16 vs 32 vs 64 vs PCA-reduced. Trade-off between information preservation and overfitting at each horizon.
- [ ] **NEW:** Does using HAR prediction as init_score (LightGBM starts from HAR level) outperform both standalone LightGBM and prediction blending? This forces the tree to learn only the correction, not the baseline level.
- [ ] **NEW:** What regime indicator works best for switching blend weights? Candidates: log_rv_w > threshold, VIX level, rolling 22d vol-of-vol, HMM state.

## Bigger Picture

- [ ] Where exactly does HAR fail? Regime transitions? High-vol periods? Specific assets?
- [ ] If we could only add ONE feature to HAR, what would give the biggest QLIKE improvement?
- [x] What features do the Optiver competition winners actually use, and which translate to daily forecasting? -- Answered 2026-05-06, see research-journal.md and features/microstructure.md

## Evaluation & Reporting (Inventoried 2026-05-11)

- [x] What should an end-of-experiment report contain? -- **Answered partially.** See research journal 2026-05-11 for full proposed structure (6 sections). Implementation needed.
- [ ] Should reports generate HTML, PDF, or Markdown? -- Current plot scripts output PNG at 150 dpi. EVALUATE SKILL.md writes Markdown tables. Need to decide on a unified report format.
- [x] How to implement a reusable walk-forward evaluation module? -- **Done.** Pipeline uses expanding-window CV with purge_gap enforcement per horizon. tournament.py orchestrates multi-model comparisons.
- [x] How to implement QLIKE custom objective for LightGBM? -- Gradient: 1 - exp(y_true - y_pred), Hessian: exp(y_true - y_pred). Verified by finite-difference tests.
- [ ] Should we add regime-conditional evaluation (split QLIKE by low/mid/high vol regimes)? -- Literature says ML underperforms HAR in stress regimes (Rahimikia-Poon). Regime-conditional reporting would expose this.
- [ ] Missing bibliography entries: Moreira-Muir (2017), Bailey-Lopez de Prado (2014) DSR. Referenced in memory cards but not in bibliography.md.
- [x] **Fix `overnight_return` data corruption:** **FIXED (May 19-21).** Option (b) implemented: `refresh-ohlcv` command derives adj_open = raw_open * (adj_close / raw_close), all 25 symbols refreshed. Code guard added: |overnight| > 0.5 auto-masked to NaN. Manifest confirms 0 corrupt symbols.
- [ ] **Switch to non-parametric Duan smearing in `tournament_table()`:** Replace `h_level = exp(pred + resid_var/2)` with `h_level = exp(pred) * mean(exp(y_true - pred))`. This is the correct distribution-free retransformation. 5 lines of code.
- [ ] **Per-symbol MZ reporting for pooled tournaments:** Run MZ per-symbol, report median beta and fraction of symbols passing. This avoids the overpowered-test problem at large N and provides more interpretable diagnostics.
