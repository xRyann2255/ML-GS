# Chapter 3: Microstructure Noise and Robust Estimators -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 72
**Verified:** 0/72
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 33 | numerical-fact | "A 6.5-hour U.S. equity trading day has $6.5 \times 3{,}600 = 23{,}400$ one-second intervals" | [uncited] | | | Arithmetic check: 6.5 * 3600 = 23400 |
| 2 | 43 | qualitative | "Bid-ask bounce is the dominant source of noise for most liquid assets" | HansenLunde2006 | | | |
| 3 | 108 | numerical-fact | "Prices on exchanges are quoted in discrete increments (one cent for U.S. equities)" | [uncited] | | | Factual claim about tick size |
| 4 | 118 | qualitative | Price staleness "creates spurious autocorrelation in returns" | AitSahaliaMyklandZhang2005 | | | |
| 5 | 129 | attribution | Glosten and Milgrom "showed that market makers widen spreads because some counterparties possess private information" | GlostenMilgrom1985 | | | |
| 6 | 132 | supporting-formula | Bid-ask spread proportionality: $s_t \propto \alpha \cdot \sigma_v$ where $\alpha$ is probability counterparty is informed and $\sigma_v$ is volatility of information signal | GlostenMilgrom1985 | | | Check if this simplified form accurately represents the GM85 model |
| 7 | 140 | attribution | "A related insight from Kyle (1985)" -- first-order autocovariance of price changes | Kyle1985 | | | |
| 8 | 140 | supporting-formula | $\Cov(\Delta p_t, \Delta p_{t+1}) = -s^2/4$ | Kyle1985 | | | Check whether this result is from Kyle1985 or Roll1984; Roll's model gives this exact expression |
| 9 | 147 | defining-formula | Standard noise model: $p^*_{t,i} = p_{t,i} + \varepsilon_{t,i}, \quad \varepsilon_{t,i} \overset{\text{iid}}{\sim} (0, \omega^2)$ | [uncited] | | | Standard in literature; referenced as from Ch2 |
| 10a | 151 | attribution | Hansen and Lunde showed that $\E[\RV_t^{(\text{noisy})}] = \IVol_t + 2n\omega^2$ | HansenLunde2006 | | | |
| 10b | 151 | attribution | Ait-Sahalia, Mykland, Zhang showed that $\E[\RV_t^{(\text{noisy})}] = \IVol_t + 2n\omega^2$ | AitSahaliaMyklandZhang2005 | | | |
| 11 | 154 | defining-formula | Noisy RV bias decomposition: $\E[\RV_t^{(\text{noisy})}] = \IVol_t + 2n\omega^2$ | HansenLunde2006, AitSahaliaMyklandZhang2005 | | | Core noise bias formula |
| 12 | 173 | numerical-fact | "At 5-minute frequency ($n \approx 78$ for U.S. equities)" | [uncited] | | | Check: 6.5 hrs * 60 min / 5 min = 78 |
| 13 | 178 | qualitative | "As $n \to \infty$ (tick-by-tick), the bias term dominates and $\RV_t^{(\text{noisy})} \to \infty$" | [uncited] | | | Direct consequence of claim 11 |
| 14 | 183 | qualitative | "the simple i.i.d. model is a useful first approximation for liquid stocks, but the actual noise structure is more complex" | HansenLunde2006 | | | |
| 15 | 199 | defining-formula | Volatility signature plot: $\bar{\RV}(\Delta) = \frac{1}{T} \sum_{t=1}^{T} \RV_t(\Delta)$ | [uncited] | | | Standard definition |
| 16 | 288 | methodological | "The 5-minute rule of thumb holds for liquid large-cap equities and major FX pairs" | [uncited] | | | Common practitioner knowledge |
| 17 | 289 | methodological | "For less liquid instruments (small-cap stocks, emerging-market currencies, corporate bonds), the noise-contaminated region can extend to 15 or even 30 minutes" | HansenLunde2006 | | | |
| 18 | 290 | qualitative | "For extremely liquid futures (e.g., E-mini S&P 500), the curve may flatten by 1 minute" | [uncited] | | | |
| 19 | 303 | attribution | "The Two-Scales Realized Volatility (TSRV) estimator, developed by Zhang, Mykland, and Ait-Sahalia (2005)" | ZhangMyklandAitSahalia2005 | | | |
| 20 | 329 | defining-formula | TSRV: $\widehat{\IVol}_t^{\text{TSRV}} = \RV^{(\text{avg}, K_{\text{slow}})}_t - \frac{\bar{n}_{K_\text{slow}}}{n}\, \RV^{(\text{all})}_t$ | ZhangMyklandAitSahalia2005 | | | Core TSRV formula |
| 21 | 335 | supporting-formula | $\bar{n}_{K_\text{slow}} = (n - K_{\text{slow}} + 1)/K_{\text{slow}}$: average number of returns per subsample at slow scale | ZhangMyklandAitSahalia2005 | | | |
| 22 | 431 | qualitative | "Under the i.i.d. noise model, the optimal choice of $K_{\text{slow}}$ yields a convergence rate of $n^{-1/6}$ for the TSRV estimator" | ZhangMyklandAitSahalia2005 | | | |
| 23 | 433 | supporting-formula | TSRV convergence: $\widehat{\IVol}_t^{\text{TSRV}} - \IVol_t = O_p(n^{-1/6})$ | ZhangMyklandAitSahalia2005 | | | |
| 24 | 435 | qualitative | "standard 5-minute RV (without noise correction) converges at rate $n^{-1/2}$ but only if you ignore noise" | [uncited] | | | Standard result for noise-free RV |
| 25 | 436 | qualitative | "With noise, standard RV does not converge at all" | [uncited] | | | Direct consequence of bias formula |
| 26 | 437 | qualitative | "TSRV is the first estimator that is consistent in the presence of noise" | ZhangMyklandAitSahalia2005 | | | Priority claim |
| 27 | 445 | numerical-fact | Worked example uses "$n = 23{,}400$ ticks (one per second over 6.5 hours)" | [uncited] | | | Consistent with claim 1 |
| 28 | 446 | numerical-fact | "$K_{\text{slow}} = 390$ (equivalent to spacing returns 390 seconds, or 6.5 minutes, apart)" | [uncited] | | | Arithmetic: 390 sec / 60 = 6.5 min |
| 29 | 454 | numerical-fact | "$23{,}400 / 390 = 60$ returns spaced 390 seconds apart" | [uncited] | | | Arithmetic check |
| 30 | 458 | numerical-fact | "$\bar{n}_{390} = (23{,}400 - 390 + 1)/390 \approx 59$" | [uncited] | | | Arithmetic: (23400 - 390 + 1)/390 = 23011/390 = 59.0026 |
| 31 | 459 | numerical-fact | "$\bar{n}_{390}/n = 59/23{,}400 \approx 0.00252$" | [uncited] | | | Arithmetic: 59/23400 = 0.002521 |
| 32 | 463 | numerical-fact | "$1.3 \times 10^{-4} - 0.00252 \times 3.2 \times 10^{-4} = 1.3 \times 10^{-4} - 0.008 \times 10^{-4} \approx 1.29 \times 10^{-4}$" | [uncited] | | | Arithmetic: 0.00252 * 3.2e-4 = 8.064e-7 = 0.008064e-4; 1.3e-4 - 0.008e-4 = 1.292e-4 |
| 33 | 468 | numerical-fact | "annualized volatility is $\sqrt{1.29 \times 10^{-4}} \times \sqrt{252} \approx 18.0\%$" | [uncited] | | | Arithmetic: sqrt(1.29e-4) * sqrt(252) = 0.01136 * 15.875 = 0.1803 = 18.0% |
| 34 | 479 | attribution | "Zhang (2006) developed the Multi-Scale Realized Volatility (MSRV) estimator" | Zhang2006 | | | |
| 35 | 490 | defining-formula | MSRV: $\widehat{\IVol}_t^{\text{MSRV}} = \sum_{j=1}^{J} a_j \, \RV^{(\text{avg}, K_j)}_t$ | Zhang2006 | | | Core MSRV formula |
| 36 | 496 | qualitative | "the optimal $J$ grows with $n$" | Zhang2006 | | | |
| 37 | 497 | supporting-formula | MSRV weights satisfy $\sum_j a_j = 1$ (targets $\IVol_t$) and a second constraint that cancels the $\omega^2$ bias | Zhang2006 | | | |
| 38 | 514 | qualitative | "The MSRV estimator achieves the convergence rate $n^{-1/4}$" | Zhang2006 | | | |
| 39 | 515 | supporting-formula | MSRV convergence: $\widehat{\IVol}_t^{\text{MSRV}} - \IVol_t = O_p(n^{-1/4})$ | Zhang2006 | | | |
| 40 | 517 | qualitative | "$n^{-1/4}$ is the best possible rate for any estimator under the i.i.d. noise model without knowing $\omega^2$" | Zhang2006 | | | Optimality claim |
| 41 | 518 | numerical-fact | "with $n = 23{,}400$ one-second observations, $n^{-1/4} \approx 0.081$" | [uncited] | | | Arithmetic: 23400^(-1/4) = 1/sqrt(sqrt(23400)) = 1/12.37 = 0.0808 |
| 42 | 518 | numerical-fact | "$n^{-1/6} \approx 0.188$ for TSRV" (with n = 23,400) | [uncited] | | | Arithmetic: 23400^(-1/6) = 1/5.326 = 0.1878 |
| 43 | 519 | numerical-fact | "MSRV is roughly 2.3 times more precise than TSRV for the same data" | [uncited] | | | Arithmetic: 0.188/0.081 = 2.32 |
| 44 | 532 | attribution | "The realized kernel, developed by Barndorff-Nielsen, Hansen, Lunde, and Shephard (2008)" | BNHLS2008 | | | |
| 45 | 533 | qualitative | Realized kernel "achieves the optimal $n^{-1/4}$ convergence rate (same as MSRV)" | BNHLS2008 | | | |
| 46 | 562 | defining-formula | Realized kernel: $\widehat{K}_t = \sum_{h=-H}^{H} k\!\left(\frac{h}{H+1}\right) \hat{\gamma}_h$ | BNHLS2008 | | | Core realized kernel formula |
| 47 | 566 | supporting-formula | Autocovariance of noisy returns: $\hat{\gamma}_h = \sum_{i=1}^{n-\lvert h\rvert} r^*_{t,i}\, r^*_{t,i+\lvert h\rvert}$; note $\hat{\gamma}_0 = \RV_t^{(\text{noisy})}$ | BNHLS2008 | | | Check: this is the un-centered autocovariance (no mean subtraction) |
| 48 | 587 | qualitative | "flat-top property ... $k'(0) = 0$ (the kernel is flat at the origin), which ensures that the noise bias is removed at the correct rate" | BNHLS2008 | | | |
| 49 | 588 | qualitative | "The Parzen kernel satisfies this [flat-top property]" | [uncited] | | | Standard kernel theory |
| 50 | 617 | supporting-formula | Parzen kernel: $k(x) = 1 - 6x^2 + 6\lvert x\rvert^3$ for $\lvert x\rvert \le 0.5$; $k(x) = 2(1 - \lvert x\rvert)^3$ for $0.5 < \lvert x\rvert \le 1$; $k(x) = 0$ for $\lvert x\rvert > 1$ | [uncited] | | | Standard Parzen kernel definition; verify piecewise formula |
| 51 | 663 | supporting-formula | Optimal realized kernel bandwidth: $H^* \propto n^{3/5}$ | BNHLS2008 | | | |
| 52 | 664 | numerical-fact | "For $n = 23{,}400$ one-second observations, this gives $H^* \approx 23{,}400^{3/5} \approx 400$" | [uncited] | | | Arithmetic: 23400^(3/5) = 23400^0.6; check value |
| 53 | 673 | attribution | "Pre-averaging, developed by Jacod, Li, Mykland, Podolskij, and Vetter (2009)" | JacodLiMyklandPodolskijVetter2009 | | | |
| 54 | 688 | defining-formula | Pre-averaged price: $\bar{p}^*_{t,i} = \sum_{j=1}^{L-1} g\!\left(\frac{j}{L}\right) \Delta p^*_{t,i+j}$ | JacodLiMyklandPodolskijVetter2009 | | | Core pre-averaging formula |
| 55 | 694 | defining-formula | Pre-averaged realized variance: $\widehat{\IVol}_t^{\text{PA}} = \frac{1}{L \psi_2} \sum_{i=0}^{n - L} (\bar{p}^*_{t,i})^2 - \frac{\psi_1}{2 L \psi_2}\, \RV^{(\text{all})}_t$ | JacodLiMyklandPodolskijVetter2009 | | | Core pre-averaging RV formula |
| 56 | 700 | supporting-formula | $\psi_1 = \int_0^1 [g'(x)]^2\,dx$ and $\psi_2 = \int_0^1 [g(x)]^2\,dx$: constants determined by the weight function | JacodLiMyklandPodolskijVetter2009 | | | |
| 57 | 702 | qualitative | "the optimal choice is $L \propto n^{1/2}$" for pre-averaging block length | JacodLiMyklandPodolskijVetter2009 | | | |
| 58 | 783 | qualitative | "With the optimal block length $L \propto n^{1/2}$, the pre-averaged estimator achieves the optimal convergence rate $n^{-1/4}$" | JacodLiMyklandPodolskijVetter2009 | | | |
| 59 | 784 | qualitative | "The pre-averaging approach also provides a feasible central limit theorem, enabling confidence intervals for integrated variance" | JacodLiMyklandPodolskijVetter2009 | | | |
| 60a | 803 | attribution | Fourier estimator proposed by Malliavin and Mancino (2002, 2009) | MalliavinMancino2002 | | | |
| 60b | 803 | attribution | Fourier estimator proposed by Malliavin and Mancino (2002, 2009) | MalliavinMancino2009 | | | |
| 61 | 809 | attribution | "Xiu (2010) proposed treating the noisy price observations as a state-space model" (QMLE) | Xiu2010 | | | |
| 62 | 811 | qualitative | "The QMLE achieves the optimal $n^{-1/4}$ rate and provides a natural estimate of $\omega^2$ as a byproduct" | Xiu2010 | | | |
| 63 | 814 | qualitative | "Under the standard i.i.d. noise model, the best possible convergence rate is $n^{-1/4}$" | [uncited] | | | Established by Zhang2006; reiterated as summary |
| 64 | 981 | qualitative | "noise-robust estimators rarely produce better forecasts of future volatility, even though they produce more accurate estimates of today's integrated variance" | LPS2015 | | | |
| 65 | 981 | methodological | LPS2015 "showed that noise-robust estimators rarely produce better forecasts of future volatility" | LPS2015 | | | Key practical finding |
| 66 | 913 | qualitative | 5-min RV convergence rate is $n^{-1/2}$ (no noise) | [uncited] | | | Standard result |
| 67 | 914 | qualitative | TSRV noise assumption is "i.i.d." | ZhangMyklandAitSahalia2005 | | | |
| 68 | 916 | qualitative | Realized kernel handles "Dependent [noise] OK" | BNHLS2008 | | | |
| 69 | 917 | qualitative | Pre-averaging handles "Dependent [noise] OK" and "provides feasible CLT" | JacodLiMyklandPodolskijVetter2009 | | | |
| 70 | 918 | qualitative | QMLE noise assumption is "Gaussian noise" | Xiu2010 | | | |
| 71 | 913 | methodological | 5-min RV is "Simple; hard to beat for forecasting" | LPS2015 | | | |
| 72 | 1067 | qualitative | LPS2015 "Compared ~400 estimators across 31 assets" | LPS2015 | | | Check if ~400 estimators and 31 assets are the correct numbers from the paper |
