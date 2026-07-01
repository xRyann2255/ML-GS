# Chapter 4: Asymmetric Volatility

Layer 1 decomposes realized variance into signed components and jump variation.
Six features, all computed from tick-level 5-minute returns.

## Features

**Layer 1 feature set: asymmetric volatility and jump decomposition.**

| Feature | What It Is | What It Does | Horizon |
|---------|-----------|--------------|---------|
| $\mathrm{RS}_t^{-}$ (daily) | $\displaystyle\sum_{i=1}^{M} r_{t,i}^{2}\,\mathbf{1}(r_{t,i} < 0)$ | Carries ${\sim}2\times$ predictive weight of $\mathrm{RS}^{+}$; dominant asymmetric signal (Patton and Sheppard, 2015) | 1d |
| $\mathrm{RS}_t^{+}$ (daily) | $\displaystyle\sum_{i=1}^{M} r_{t,i}^{2}\,\mathbf{1}(r_{t,i} \geq 0)$ | Weaker predictor; provides the contrast that identifies asymmetry | 1d |
| $\mathrm{RS}_t^{-(w)}$ (weekly) | $\displaystyle\frac{1}{5}\sum_{j=0}^{4} \mathrm{RS}_{t-j}^{-}$ | Persistent downside memory; smooths daily noise in the negative semivariance | 1d--5d |
| $J_t^{-}$ (signed neg. jump) | Large negative moves beyond threshold | 1--3% QLIKE gain beyond unsigned jumps (Andersen et al., 2007) | 1d--5d |
| $C_t$ (continuous variation) | $\max(\operatorname{BPV}_t,\; 0)$ | Highly persistent (ACF ${\sim}0.6$--$0.7$); workhorse of the decomposition (Barndorff-Nielsen and Shephard, 2004) | All |
| $J_t$ (jump variation) | $\max(\operatorname{RV}_t - \operatorname{BPV}_t,\; 0)$ | Nearly unpredictable (ACF ${\sim}0.0$--$0.1$); signals regime breaks | Event |

## The Leverage Effect

Negative returns increase future volatility more than positive returns of equal magnitude.
The effect is strongest for equity indices and E-mini futures, where $\mathrm{RS}^{-}$ carries roughly twice the predictive weight of $\mathrm{RS}^{+}$ in HAR-type regressions (Patton and Sheppard, 2015).
The SHAR model exploits this directly by replacing $\operatorname{RV}$ with separate $\mathrm{RS}^{+}$ and $\mathrm{RS}^{-}$ regressors at each horizon.

## Continuous vs. Jump Variation

Continuous variation $C_t$ is highly persistent and drives the bulk of out-of-sample forecast accuracy; it behaves like a smoothed version of $\operatorname{RV}$ with jump contamination removed.
Jump variation $J_t$ is nearly unpredictable day-to-day, but large positive values flag regime transitions (macro announcements, flash crashes) where the conditional distribution shifts.
In practice, $C_t$ is the forecasting workhorse and $J_t$ is the alarm: $C$ enters the model as a persistent regressor at all horizons, while $J$ triggers recalibration or regime-switch logic.
The HAR-CJ model of Andersen et al. (2007) formalizes this split and shows that separating $C$ from $J$ yields 1--3% QLIKE improvement over models that use total $\operatorname{RV}$ alone.

## Cumulative Performance

Layers 0+1 together (11 features: 5 from HAR/HARQ, 6 from this chapter) achieve approximately 70% of the total attainable QLIKE improvement, per literature benchmarks.
All semivariances and jump components are computed from tick-level data at 5-minute frequency.
Jump significance is assessed via the Lee-Mykland test, which flags individual intraday returns exceeding a time-varying threshold calibrated to local bipower variation.

> **Key Idea: Signed Semivariances: The Cheapest Upgrade**
>
> Replacing $\operatorname{RV}$ with $\mathrm{RS}^{+}$ and $\mathrm{RS}^{-}$ in a HAR regression (the SHAR model) costs zero additional data and yields 3--8% QLIKE improvement (Patton and Sheppard, 2015).
> This is the single cheapest feature upgrade after the RQ interaction from Layer 0.

> **Warning: Jumps Are Not Predictors**
>
> $J_t$ has near-zero autocorrelation.
> Do not include lagged jump variation as a standard regressor expecting it to forecast future $\operatorname{RV}$.
> Its value is as a conditioning variable: when $J_t$ is large, shrink the daily coefficient or trigger a regime indicator.
> Treating $J_t$ as a regular feature wastes a degree of freedom and can degrade forecast accuracy.
