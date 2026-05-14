# Chapter 6: The HAR Model and Its Extensions -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 52
**Verified:** 0/52
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 41 | attribution | "Muller et al. (1993) formalized this as the Heterogeneous Market Hypothesis (HMH)" | \citet{Muller1993} | | | |
| 2 | 41 | qualitative | The HMH states "the market is a superposition of participants operating at different time scales, and these participants interact" | \citet{Muller1993} | | | |
| 3 | 120 | attribution | Corsi (2009) turned the HMH insight directly into a regression (the HAR model) | \citet{Corsi2009} | | | |
| 4 | 127-128 | defining-formula | $\RV^{(w)}_{t} = \frac{1}{5}\sum_{i=0}^{4}\RV_{t-i}$ | [uncited] | | | Definition of weekly average RV |
| 5 | 131-132 | defining-formula | $\RV^{(m)}_{t} = \frac{1}{22}\sum_{i=0}^{21}\RV_{t-i}$ | [uncited] | | | Definition of monthly average RV |
| 6 | 138 | methodological | "5 trading days = 1 week; 22 trading days $\approx$ 1 month" | [uncited] | | | Convention used in HAR literature |
| 7 | 159-161 | defining-formula | $\RV_{t+1} = \beta_0 + \beta_d \, \RV_{t} + \beta_w \, \RV^{(w)}_{t} + \beta_m \, \RV^{(m)}_{t} + \varepsilon_{t+1}$ (the HAR-RV model) | \citet{Corsi2009} | | | |
| 8 | 183 | qualitative | HAR's autocorrelation decay "closely approximates a long-memory process, with none of the estimation complexity of FIGARCH" | \citet{Corsi2009} | | | |
| 9 | 194-195 | methodological | "Many papers estimate HAR on $\ln(\RV)$ rather than $\RV$ in levels"; "$\ln(\RV_t)$ is approximately Gaussian" | [uncited] | | | |
| 10 | 195 | qualitative | Log specification of HAR "guarantees positive forecasts (since $e^x > 0$)" | [uncited] | | | Mathematical fact |
| 11 | 196 | qualitative | "The log specification generally forecasts better" | [uncited] | | | |
| 12 | 203 | numerical-fact | Corsi (2009) estimates HAR on S&P 500 5-minute RV (1990--2003) and reports $\beta_d \approx 0.36$, $\beta_w \approx 0.28$, $\beta_m \approx 0.28$ | \citet{Corsi2009} | | | |
| 13 | 203 | methodological | Corsi (2009) uses S&P 500 5-minute RV with sample period 1990--2003 | \citet{Corsi2009} | | | |
| 14 | 207 | numerical-fact | "The in-sample $R^2$ is typically 0.40--0.60 for daily-horizon forecasts on equity index $\RV$" | [uncited] | | | Attributed generally to HAR literature |
| 15 | 240-241 | numerical-fact | Worked example: $\RV^{(w)}_{22} = \frac{1.90 + 1.70 + 2.00 + 2.50 + 2.20}{5} = \frac{10.30}{5} = 2.06$ | [uncited] | | | Arithmetic check needed |
| 16 | 246-247 | numerical-fact | Worked example: $\RV^{(m)}_{22} = \frac{0.80 + 0.90 + \cdots + 1.90}{22} = \frac{32.70}{22} = 1.486$ | [uncited] | | | Arithmetic check needed (sum of 22 values) |
| 17 | 251-255 | numerical-fact | Worked example: $\widehat{\RV}_{23} = 0.05 + 0.684 + 0.577 + 0.416 = 1.727$ | [uncited] | | | Arithmetic check needed |
| 18 | 257 | numerical-fact | Worked example: $\sqrt{1.727 \times 10^{-4}} = 1.31\%$ daily volatility | [uncited] | | | Arithmetic check needed |
| 19 | 337-339 | defining-formula | $\BPV_t = \frac{\pi}{2} \sum_{i=2}^{n} \|r_{t,i}\|\,\|r_{t,i-1}\|$ | [uncited] | | | BPV definition; attributed to BNS2004 on line 348 |
| 20 | 344 | qualitative | The $\pi/2$ scaling constant "ensures $\BPV_t$ converges to integrated variance $\IVol_t$ ... as sampling frequency increases" | [uncited] | | | |
| 21 | 346 | qualitative | "$\BPV_t \to \IVol_t$ even when jumps are present, whereas $\RV_t \to \IVol_t + \sum(\text{jumps})^2$" | [uncited] | | | Key property of BPV |
| 22 | 348 | attribution | "BPV was introduced by Barndorff-Nielsen and Shephard (2004)" | \citet{BNS2004} | | | |
| 23 | 363 | attribution | "Andersen, Bollerslev, and Diebold (2007) proposed the HAR-J model" | \citet{ABD2007} | | | |
| 24 | 366-367 | defining-formula | $\RV_{t+1} = \beta_0 + \beta_d \, \RV_{t} + \beta_w \, \RV^{(w)}_{t} + \beta_m \, \RV^{(m)}_{t} + \beta_J \, J_t + \varepsilon_{t+1}$ (HAR-J model) | \citet{ABD2007} | | | |
| 25 | 370 | defining-formula | $J_t = \max(\RV_t - \BPV_t, 0)$: the jump component estimator | [uncited] | | | Used in HAR-J and HAR-CJ |
| 26 | 371 | qualitative | $\beta_J$ is "typically estimated as negative and small, meaning jumps have a weak or transient effect on future volatility" | [uncited] | | | |
| 27 | 387-388 | qualitative | ABD (2007) find "the jump component $J_t$ is statistically significant but economically small in forecasting next-day $\RV$" | \citet{ABD2007} | | | |
| 28 | 389 | qualitative | "Most of the predictive power comes from the continuous component" | \citet{ABD2007} | | | |
| 29 | 389 | qualitative | "Jumps are largely transient: a jump on day $t$ does not meaningfully raise volatility on day $t+1$" | \citet{ABD2007} | | | |
| 30 | 394 | attribution | Corsi, Pirino, and Reno (2010) proposed the HAR-CJ model | \citet{CorsiPirinoReno2010} | | | |
| 31 | 397-399 | defining-formula | $\RV_{t+1} = \beta_0 + \beta^C_d C_t + \beta^C_w C^{(w)}_t + \beta^C_m C^{(m)}_t + \beta^J_d J_t + \beta^J_w J^{(w)}_t + \beta^J_m J^{(m)}_t + \varepsilon_{t+1}$ (HAR-CJ model) | \citet{CorsiPirinoReno2010} | | | |
| 32 | 402 | defining-formula | $C_t = \BPV_t$: continuous component definition in HAR-CJ | \citet{CorsiPirinoReno2010} | | | |
| 33 | 408 | numerical-fact | "The HAR-CJ model has six slope coefficients instead of three" | [uncited] | | | Can be verified by counting terms in eq |
| 34 | 409 | qualitative | "continuous coefficients ($\beta^C$) are large and significant; jump coefficients ($\beta^J$) are small and often insignificant at weekly and monthly horizons" | \citet{CorsiPirinoReno2010} | | | |
| 35 | 511-513 | defining-formula | $RS^+_t = \sum_{i=1}^{n} r^2_{t,i} \, \mathbf{1}_{\{r_{t,i} > 0\}}$, $RS^-_t = \sum_{i=1}^{n} r^2_{t,i} \, \mathbf{1}_{\{r_{t,i} < 0\}}$ | [uncited] | | | Realized semivariance definitions |
| 36 | 519 | supporting-formula | $RS^+_t + RS^-_t = \RV_t$: semivariances sum to total RV | [uncited] | | | |
| 37 | 530 | qualitative | "Decomposing realized variance into positive semivariance $RS^+$ and negative semivariance $RS^-$ substantially improves forecasts" | \citet{PSS2015} | | | |
| 38 | 531 | qualitative | "Bad volatility ($RS^-$, from downward price moves) is significantly more persistent than good volatility ($RS^+$, from upward moves)" | \citet{PSS2015} | | | |
| 39 | 537-539 | defining-formula | $\RV_{t+1} = \beta_0 + \beta^+_d \, RS^+_t + \beta^-_d \, RS^-_t + \beta_w \, \RV^{(w)}_t + \beta_m \, \RV^{(m)}_t + \varepsilon_{t+1}$ (SHAR model) | \citet{PSS2015} | | | |
| 40 | 544 | qualitative | "$\beta^-_d > \beta^+_d$ is the typical finding: negative semivariance has a larger coefficient" | [uncited] | | | Consistent with PSS2015 but no explicit citation on this line |
| 41 | 566 | qualitative | "SHAR improves forecast accuracy relative to HAR across multiple asset classes, with the largest gains on equity indices where the leverage effect is strongest" | \citet{PSS2015} | | | |
| 42 | 582-583 | defining-formula | $RQ_t = \frac{n}{3} \sum_{i=1}^{n} r^4_{t,i}$ (realized quarticity) | [uncited] | | | |
| 43 | 587 | qualitative | "$n/3$: a scaling constant that ensures consistency" for realized quarticity | [uncited] | | | |
| 44 | 588 | qualitative | "High $RQ_t$ means that volatility itself was volatile during the day, making $\RV_t$ a noisy estimate of $\IVol_t$" | [uncited] | | | |
| 45 | 609 | attribution | BPQ (2016) "allow the daily coefficient in the HAR model to vary with realized quarticity $RQ_t$" | \citet{BPQ2016} | | | |
| 46 | 610-611 | qualitative | "On noisy days (high $RQ$), the daily $\RV$ coefficient shrinks toward zero ... On precise days (low $RQ$), the coefficient is large" | \citet{BPQ2016} | | | |
| 47 | 616-618 | defining-formula | $\RV_{t+1} = \beta_0 + (\beta_d + \beta_{dQ}\sqrt{RQ_t})\,\RV_t + \beta_w \, \RV^{(w)}_t + \beta_m \, \RV^{(m)}_t + \varepsilon_{t+1}$ (HARQ model) | \citet{BPQ2016} | | | |
| 48 | 622 | qualitative | "$\beta_{dQ}$: the adjustment coefficient; typically estimated as negative" | \citet{BPQ2016} | | | |
| 49 | 686 | qualitative | "Among models that use only past RV and its measurement-error statistics, HARQ is the strongest in the literature" | \citet{BPQ2016} | | | |
| 50 | 734 | attribution | Bollerslev et al. (2018) constructed the "Risk Everywhere" paper with "a large cross-section of HAR-X type models with many macro and market predictors" | \citet{BollerslevEtAl2018} | | | |
| 51 | 737 | attribution | Audrino and Knaus (2016) propose the "Lassoing the HAR" approach, applying Lasso (L1 regularization) to HAR-X | \citet{AudrinoKnaus2016} | | | |
| 52 | 740-741 | defining-formula | $\min_{\beta, \gamma} \sum_{t} (\RV_{t+1} - \beta_0 - \beta_d \RV_t - \beta_w \RV^{(w)}_t - \beta_m \RV^{(m)}_t - \sum_j \gamma_j X_{j,t})^2 + \lambda \sum_j \|\gamma_j\|$ (Lasso-HAR) | \citet{AudrinoKnaus2016} | | | |
