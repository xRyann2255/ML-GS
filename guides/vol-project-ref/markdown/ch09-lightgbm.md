# Chapter 9: LightGBM for Tabular Volatility

LightGBM (Ke et al., 2017) is the primary ML model in the pipeline.
It ingests the full engineered feature set from Layers 0--7 and optimizes a custom $\operatorname{QLIKE}$ objective.

## What Goes In

The table below summarizes the raw feature counts per layer before expansion.
After applying {level, change, z-score} transformations to each base feature, the final input dimensionality is approximately 80--120.

**Feature layers feeding the LightGBM model.**

| Layer | Features | Count |
|-------|----------|-------|
| 0 | $\log \operatorname{RV}$ (d/w/m), RQ, RQ interaction | 5 |
| 1 | $\operatorname{RV}^+$, $\operatorname{RV}^-$, signed jumps, $C$, $J$ | 6 |
| 2 | ATM IV, $\operatorname{VRP}$, skew, term structure, $\operatorname{VVIX}$, butterfly, IV--RV gap, stock IV, stock VRP | 9 |
| 3 | Price acceleration, OBI, spread, VPIN, Kyle $\lambda$ | 9 |
| 4 | Treasury slope, FX vol, commodity vol, VIX, VIX futures slope, DY spillover | 6 |
| 5 | Calendar: FOMC, OpEx, month/weekday dummies | ~15 |
| 6 | Memory: Hurst exponent, fractional $d$, ACF features | ~10 |
| 7 | Sentiment: FinBERT scores, attention proxies | ~15--55 |
| | **Raw total** | **~37--57** |
| | **After {level, change, z-score} expansion** | **~80--120** |

## Configuration

The table below gives the reference configuration, adapted from the Optiver Kaggle competition (91st-percentile solution).

**LightGBM reference configuration.**

| Parameter | Value | Notes |
|-----------|-------|-------|
| `learning_rate` | 0.05 | |
| `num_leaves` | 255 | |
| `min_data_in_leaf` | 255 | Prevents overfitting on rare regimes |
| `n_estimators` | 10,000 | With early stopping |
| `early_stopping_rounds` | 400 | |
| `boosting_type` | `dart` | Dropout regularization |
| `objective` | Custom | $\operatorname{QLIKE}$ loss; not a built-in objective |
| `metric` | Custom | $\operatorname{QLIKE}$ evaluation for early stopping |

## Custom QLIKE Objective

$\operatorname{QLIKE}$ is not a built-in LightGBM loss.
Training requires a custom objective function that returns the gradient and Hessian of the $\operatorname{QLIKE}$ loss with respect to the predicted value, plus a separate custom evaluation metric for early stopping.
$\operatorname{QLIKE}$ is robust to noise in the volatility proxy: it ranks forecasts consistently even when $\operatorname{RV}$ is measured with error, unlike MSE (Patton, 2011).
All training and prediction operate in $\log$-$\operatorname{RV}$ space; convert back to levels only for final $\operatorname{QLIKE}$ evaluation.

## SHAP Interpretability

$\operatorname{SHAP}$ values (Lundberg and Lee, 2017) provide feature importance and interaction effects for each prediction.
They are required for the GS presentation and for defending model behavior under scrutiny.
However, single-model importance measures (gain, permutation, $\operatorname{SHAP}$) are unstable across refits when features are near-substitutes (e.g., VIX, $\operatorname{VVIX}$, ATM IV all proxy for the same latent factor).
This instability motivates the Rashomon analysis in Chapter 12, which quantifies importance across the set of near-optimal models rather than relying on a single fit.

> **Warning: Baseline First**
>
> The fitting scheme for the $\operatorname{HAR}$ baseline matters more than the choice of ML model (Borner et al., 2024).
> A properly fitted $\operatorname{HAR}$ using OLS with Newey--West standard errors and an expanding or rolling window is essential before claiming ML improvement.
> Without this baseline, apparent ML gains may reflect a weak benchmark, not genuine forecasting ability.

> **Key Idea: Why LightGBM**
>
> Gradient-boosted trees dominate tabular volatility forecasting benchmarks (Christensen, Siggaard, and Veliyev, 2023; Branco, Rubesam, and Zevallos, 2024).
> They handle mixed feature types (continuous RV lags, categorical calendar dummies, ordinal sentiment scores) without preprocessing, capture nonlinear interactions automatically, and train in seconds on datasets of this size (~5,000 rows x 120 features).
