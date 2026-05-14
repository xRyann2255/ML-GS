# Chapter 2: Realized Volatility -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 42
**Verified:** 0/42
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 30-31 | defining-formula | Log price follows $dp_t = \mu_t\,dt + \sigma_t\,dW_t$ (continuous-time diffusion for log prices) | [uncited] | | | Standard SDE for geometric Brownian motion with time-varying vol; presented as prereq |
| 2 | 37 | qualitative | At intraday horizons the drift $\mu_t\,dt$ is negligibly small | [uncited] | | | Widely accepted but no citation given |
| 3 | 61 | defining-formula | Integrated variance: $IV_t = \int_{t-1}^{t} \sigma^2_s\,ds$ | [uncited] | | | Standard definition; no specific attribution |
| 4 | 95 | attribution | Realized variance as estimator of integrated variance was developed by Andersen, Bollerslev, Diebold, Labys (2001) and Barndorff-Nielsen, Shephard (2002) | \citet{ABDL2001}, \citet{BNS2002} | | | |
| 5 | 107 | defining-formula | Realized variance: $RV_t = \sum_{i=1}^{n} r^2_{t,i}$ | [uncited] | | | Definition itself is standard; attributed generally to ABDL2001/BNS2002 on line 95 |
| 6 | 112 | defining-formula | Intraday log return: $r_{t,i} = p_{t,i} - p_{t,i-1}$ where $p_{t,i}$ is log price at end of $i$-th interval | [uncited] | | | Standard notation |
| 7 | 113 | numerical-fact | $n = 78$ for 5-minute intervals over a 6.5-hour U.S. equity trading day | [uncited] | | | 6.5 hours * 60 min / 5 min = 78. Arithmetic check needed. |
| 8 | 114 | methodological | No mean subtraction: the sample mean of intraday returns is so close to zero that omitting it improves finite-sample performance | \citet{ABDL2003} | | | |
| 9 | 125 | supporting-formula | Each small intraday return is approximately $r_{t,i} \approx \sigma_{t,i}\,\epsilon_i$ where $\epsilon_i$ has mean zero and variance one | [uncited] | | | Follows from the SDE discretization |
| 10 | 127 | supporting-formula | $E[\epsilon_i^2] = \text{Var}(\epsilon_i) + (E[\epsilon_i])^2 = 1 + 0 = 1$, so $E[r^2_{t,i}] \approx \sigma^2_{t,i}$ | [uncited] | | | Standard moment identity |
| 11 | 130 | qualitative | As intervals shrink ($n \to \infty$), the random fluctuations in each $\epsilon^2_i$ average out, and the sum converges to the integrated variance | [uncited] | | | Informal statement of consistency |
| 12 | 145 | qualitative | For processes like stock prices, the sum of squared increments converges to the quadratic variation, and this equals integrated variance (no jumps) | [uncited] | | | Informal restatement of key theorem |
| 13 | 150-153 | defining-formula | Quadratic variation: $[X]_t = \lim_{n \to \infty} \sum_{i=1}^{n} (X_{t_i} - X_{t_{i-1}})^2$ | [uncited] | | | Standard definition from stochastic calculus |
| 14 | 154 | defining-formula | For a continuous-path process (no jumps): $[X]_t = \int_0^t \sigma^2_s\,ds$ | [uncited] | | | Standard result |
| 15 | 155 | qualitative | If the process has jumps, the quadratic variation also captures the sum of squared jumps | [uncited] | | | Standard result |
| 16 | 161 | defining-formula | $RV_t \xrightarrow{p} [p]_t$ as $\Delta \to 0$ (RV converges in probability to quadratic variation) | \citet{ABDL2001}, \citet{BNS2002} | | | Core consistency result |
| 17 | 189-192 | defining-formula | No jumps: $[p]_t = IV_t$ | [uncited] | | | Standard; follows from claim 14 applied to log-price process |
| 18 | 201-205 | defining-formula | With jumps: $[p]_t = IV_t + \sum_{s \leq t} (J_s)^2$ | [uncited] | | | Standard decomposition of QV into continuous and jump components |
| 19 | 225-228 | qualitative | Under mild regularity conditions, RV is a consistent estimator of QV; in absence of jumps, RV consistently estimates IV; this holds regardless of the specific form of $\sigma_t$ (stochastic, path-dependent, or latent-factor driven) | \citet{ABDL2001}, \citet{BNS2002} | | | Key result box |
| 20 | 404 | numerical-fact | $\ln(100.30/100.00) = +0.003000$ | [uncited] | | | Worked example arithmetic; true value is $\ln(1.003) = 0.0029955...$ |
| 21 | 405 | numerical-fact | $\ln(100.10/100.30) = -0.001998$ | [uncited] | | | Worked example; true value is $\ln(100.10/100.30) = -0.001998...$ |
| 22 | 406 | numerical-fact | $\ln(100.50/100.10) = +0.003992$ | [uncited] | | | Worked example; true value is $\ln(100.50/100.10) = 0.003992...$ |
| 23 | 407 | numerical-fact | $\ln(100.20/100.50) = -0.002992$ | [uncited] | | | Worked example; true value is $\ln(100.20/100.50) = -0.002992...$ |
| 24 | 408 | numerical-fact | $\ln(100.60/100.20) = +0.003988$ | [uncited] | | | Worked example; true value is $\ln(100.60/100.20) = 0.003988...$ |
| 25 | 409 | numerical-fact | $\ln(100.45/100.60) = -0.001491$ | [uncited] | | | Worked example; true value is $\ln(100.45/100.60) = -0.001493...$ |
| 26 | 417 | numerical-fact | Sum of squared returns: $(9.000 + 3.992 + 15.936 + 8.952 + 15.904 + 2.223) \times 10^{-6} = 56.007 \times 10^{-6}$ | [uncited] | | | Worked example arithmetic |
| 27 | 422 | numerical-fact | $\sqrt{56.007 \times 10^{-6}} = 0.00748$ (0.75% daily) | [uncited] | | | Worked example arithmetic |
| 28 | 427 | numerical-fact | Annualized: $0.00748 \times \sqrt{252} = 0.119$ (11.9%) | [uncited] | | | Worked example arithmetic |
| 29 | 430 | numerical-fact | S&P 500 long-run average annualized volatility is roughly 15--20% | [uncited] | | | Widely cited ballpark figure |
| 30 | 432 | numerical-fact | Sampling every 5 minutes gives 78 intervals over a 6.5-hour day | [uncited] | | | Same as claim 7; arithmetic: 6.5*60/5 = 78 |
| 31 | 448-456 | defining-formula | CLT for RV: $\sqrt{n}\,(RV_t - IV_t) \xrightarrow{d} N(0,\; 2\int_{t-1}^{t}\sigma^4_s\,ds)$ | \citet{BNS2002} | | | Central limit theorem for realized variance |
| 32 | 460 | qualitative | The estimation error shrinks at rate $1/\sqrt{n}$ | [uncited] | | | Follows directly from the CLT (claim 31) |
| 33 | 467 | numerical-fact | Doubling the number of intervals cuts standard error by factor of $\sqrt{2} \approx 1.41$ | [uncited] | | | Follows from $1/\sqrt{n}$ rate |
| 34 | 498-501 | defining-formula | Microstructure noise model: $p^*_{t,i} = p_{t,i} + \varepsilon_{t,i}$, with $\varepsilon_{t,i}$ i.i.d., $E[\varepsilon_{t,i}] = 0$, $\text{Var}(\varepsilon_{t,i}) = \omega^2$ | \citet{ABDL2001}, \citet{BNS2002} | | | Standard additive noise model |
| 35 | 523-524 | supporting-formula | Observed return: $r^*_{t,i} = r_{t,i} + (\varepsilon_{t,i} - \varepsilon_{t,i-1})$; noise part has variance $2\omega^2$ | [uncited] | | | Follows from noise model (claim 34) |
| 36 | 527-529 | defining-formula | RV noise divergence: $RV_t^{(\text{noisy})} \to 2n\omega^2$ as $n \to \infty$ | [uncited] | | | Standard result from noise model |
| 37 | 655-658 | attribution | Liu, Patton, Sheppard (2015) compared approximately 400 RV estimators across 31 assets in 5 asset classes (equities, equity indices, exchange rates, bonds, commodities); conclusion: simple 5-minute RV is very hard to beat for forecasting | \citet{LPS2015} | | | Key empirical finding |
| 38 | 665 | numerical-fact | 5-minute sampling produces 78 intraday observations per day for U.S. equities (6.5 hours times 12 intervals per hour) | [uncited] | | | Same arithmetic as claims 7/30 |
| 39 | 687-689 | numerical-fact | S&P 500 typical daily realized variance is around $1 \times 10^{-4}$; typical daily realized volatility is $\sqrt{1 \times 10^{-4}} = 0.01$ (1%); annualized: $0.01 \times \sqrt{252} \approx 0.16$ | [uncited] | | | Ballpark figure for illustration |
| 40 | 700 | attribution | Conventions (RV for realized variance, $\sqrt{RV}$ for realized volatility) follow ABDL2003 and BNS2002 | \citet{ABDL2003}, \citet{BNS2002} | | | |
| 41 | 706 | qualitative | $\ln(RV_t)$ is approximately Gaussian | \citet{ABDL2001}, \citet{ABDL2003} | | | |
| 42 | 764-765 | attribution | BNS2002 introduced bipower variation (BPV) to separate jumps from continuous variation | \citet{BNS2002} | | | Stated in key results table |
