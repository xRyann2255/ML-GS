---
created: 2026-05-07
updated: 2026-06-01
tags: [evaluation, QLIKE, DM-test, MCS, CV, walk-forward, purged-kfold, covid-confound]
status: active
priority: P1
source: workspace/research/evaluation-framework.md (archived)
relates: [project-design, complete-pipeline, project-scope-and-data]
---

# Evaluation Framework — Summary

## Primary Metric: QLIKE

```
QLIKE = (1/T) × Σ ( σ̂²_t / σ²_t  −  log(σ̂²_t / σ²_t)  −  1 )
```

- Penalizes **relative** forecast errors (not absolute)
- Robust to imperfect volatility proxies (Patton 2011)
- Ranks forecasters consistently regardless of vol regime
- **The only loss that matters for model selection/comparison**

**Critical:** LightGBM has no built-in QLIKE. Must implement custom objective returning gradient and Hessian. Training with MSE and evaluating with QLIKE = optimizing the wrong surface.

## Secondary Metrics

| Metric | Role |
|--------|------|
| MSE (on log-RV) | Secondary diagnostic |
| MAE (on log-RV) | Robustness check |
| Mincer-Zarnowitz regression | Assess unbiasedness |

## Statistical Tests

**Diebold-Mariano (1995):** Pairwise test — "Is model A statistically better than B?" Require p < 0.05 vs each baseline. IMPLEMENTED: `diebold_mariano_test(loss_1, loss_2, horizon)` with Newey-West HAC (bandwidth=h-1). Sign: positive DM stat = model 2 better.

**Mincer-Zarnowitz:** Efficiency regression (alpha=0, beta=1 joint F-test). IMPLEMENTED: `mincer_zarnowitz(y_true, y_pred, horizon=1)` — inputs must be variance space. Uses Newey-West HAC standard errors (bandwidth = max(horizon, T^{1/3})). When calling from log-space predictions, apply Duan (1995) retransformation: `h_level = exp(pred_log + sigma2_resid/2)` before converting to variance space. Without Duan, beta is inflated by Jensen's inequality; without HAC, F-test over-rejects due to ARCH-clustered residuals.

**Model Confidence Set (Hansen, Lunde, Nason 2011):** Returns the set of models not significantly worse than the best at a given confidence level. IMPLEMENTED: `model_confidence_set(losses, alpha=0.10, n_bootstrap=10000, block_length=None, seed=42)`. Block bootstrap, range statistic T_R, sequential elimination. Returns included, excluded, p_values, elimination_order.

**Tournament Table:** `tournament_table(predictions, y_true, baseline="har", horizon=1, mcs_alpha=0.10, mcs_bootstrap=10000)` — combines QLIKE, MSE, R², DM, MZ, MCS into one DataFrame sorted by QLIKE. All inputs in LOG space. MZ internally applies Duan retransformation (using OOS residual variance) before converting to variance space.

**Tournament Runner:** `evaluation/tournament.py` — `run_har_tournament()` orchestrates 7 HAR models × N symbols × multiple horizons. `display_tournament()` renders Rich tables.

## COVID Period Confound (2026-06-01)

COVID (Feb-Jun 2020) is the dominant difficulty confound in 2015-2024 equity vol data.

**Quantified impact:**
- COVID period QLIKE: 0.1815 (vs 0.1393 non-COVID) for h=1 LightGBM
- Inflation: +51.8 bps on full-OOS QLIKE when COVID is in the test set
- Transition: train_size >= 1512 completely excludes COVID from expanding-window test sets

**Mandatory rules:**
1. When comparing configs with different `train_size`, restrict both to **common test dates**. Raw QLIKE is NOT comparable across configs with non-overlapping OOS periods.
2. Report QLIKE both including and excluding COVID (dual metric) when COVID falls in the test set.
3. Never interpret QLIKE improvements that coincide with COVID falling out of the test set as model quality gains.
4. For apples-to-apples comparisons: use a fixed holdout period (e.g., 2022-2024) evaluated for ALL configs.

**Evidence:** train_size scaling from 504d to 1764d showed "236 bps improvement" at h=1. On the common 2022-2024 period, the delta was exactly 0.0 bps. The entire "improvement" was COVID exclusion.

---

## Validation Protocol

**Purged k-Fold CV (hyperparameter tuning):**
```
|--- Train ---|== Purge ==|== Embargo ==|--- Test ---|== Purge ==|
```
- 5 folds; purge window = longest feature lookback (22 days)
- Embargo = forecast horizon (1 or 5 days)
- Never random k-fold — catastrophic look-ahead bias

**Walk-Forward (primary OOS evaluation):**
```
Iter 1:  |--- Train (5yr) ---|Test|
Iter 2:   |--- Train (5yr) ---|Test|
         → roll forward
```
- All reported QLIKE from walk-forward, never from in-sample or CV scores
- Retrain weekly on rolling 5-year window

## Success Targets

1. **QLIKE improvement:** 30–80 bps over HARQ baseline, averaged across universe
2. **Statistical significance:** DM p < 0.05 vs each baseline (HAR, HARQ, SHAR, Realized GARCH)
3. **Economic value:** Positive OOS utility gain in vol-targeting portfolio (Moreira-Muir 2017)

## Deflated Sharpe Ratio (DSR)

Every model variant/hyperparameter search counts as a trial. Report DSR (Bailey-Lopez de Prado 2014) to account for multiple testing. Keep trial count low — don't hyperparameter-search neural networks.

## Reporting

Interactive HTML report (per-experiment, generated after EVALUATE stage): Plotly dashboard with predicted vs actual log-RV time series. Implementation lives in `src/volforecast/reporting/`.
