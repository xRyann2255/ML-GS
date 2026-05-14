# Chapter 7: Rough Volatility -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 57
**Verified:** 0/57
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 6 | qualitative | RFSV model is a parsimonious forecaster competitive with HAR and LSTM | [uncited] | | | Implicit from GJR2018 and RosenbaumZhang2022 |
| 2 | 17 | attribution | Log of realized volatility behaves like fractional Brownian motion with Hurst exponent H approx 0.1; this was proposed by Gatheral, Jaisson, and Rosenbaum | GJR2018 | | | |
| 3 | 18 | numerical-fact | Standard Brownian motion has H = 0.5 | [uncited] | | | Standard definition |
| 4 | 47 | attribution | Rosenbaum and Zhang showed that both the universal LSTM and the parametric rough-vol model converge on the same characterization of the volatility process | RosenbaumZhang2022 | | | |
| 5 | 62 | defining-formula | Increments of standard BM: W_{t+h} - W_t are Gaussian with mean zero and variance h | [uncited] | | | Standard definition |
| 6 | 63 | qualitative | Increments of standard BM over non-overlapping intervals are independent | [uncited] | | | Standard definition |
| 7 | 66 | supporting-formula | Self-similarity scaling factor of standard BM is H = 1/2: rescaling time by factor c rescales path by c^{1/2} | [uncited] | | | Standard property |
| 8 | 70 | attribution | Fractional Brownian motion was introduced by Mandelbrot and Van Ness | MandelbrotVanNess1968 | | | |
| 9 | 70 | qualitative | fBM generalizes standard BM by allowing self-similarity exponent H to take any value in (0, 1) | MandelbrotVanNess1968 | | | |
| 10 | 74 | defining-formula | Var(B^H_{t+h} - B^H_t) = h^{2H} | MandelbrotVanNess1968 | | | |
| 11 | 76 | qualitative | When H = 1/2, fBM reduces to standard Brownian motion | MandelbrotVanNess1968 | | | |
| 12 | 77 | qualitative | When H != 1/2, fBM increments are not independent; negatively correlated if H < 1/2, positively correlated if H > 1/2 | MandelbrotVanNess1968 | | | |
| 13 | 79 | attribution | Hurst exponent is named after hydrologist Harold Edwin Hurst, who studied long-range dependence in Nile river levels | [uncited] | | | Historical attribution |
| 14 | 88-89 | defining-formula | Var(B^H_{t+h} - B^H_t) = h^{2H} (Eq. 7.1) | [uncited] | | | Restated from fBM definition |
| 15 | 95 | qualitative | When H < 1/2: increments negatively correlated (move up makes move down more likely); path is rougher than BM | [uncited] | | | Standard fBM property |
| 16 | 97 | qualitative | When H > 1/2: increments positively correlated (trending behavior); path is smoother than BM | [uncited] | | | Standard fBM property |
| 17 | 229 | numerical-fact | Empirical log-volatility has H approx 0.1 | [uncited] | | | Consistent with GJR2018 claim |
| 18 | 278 | qualitative | Standard stochastic volatility models (Heston, SABR) assume H = 0.5 | [uncited] | | | |
| 19 | 291 | methodological | GJR2018 studied log RV_t (5-minute realized variance) across equity indices, individual stocks, and FX | GJR2018 | | | Verify asset classes studied |
| 20 | 292 | methodological | For each asset, GJR2018 estimated the Hurst exponent H of the log RV series | GJR2018 | | | |
| 21 | 296 | numerical-fact | Across equity indices, individual stocks, and FX, the Hurst exponent of log RV_t is consistently around H approx 0.1 | GJR2018 | | | Core empirical result |
| 22 | 300 | qualitative | Standard stochastic volatility models (Heston, SABR) assume volatility process is driven by standard BM with H = 0.5 | [uncited] | | | |
| 23 | 301 | numerical-fact | H of 0.1 means the volatility path reverses direction roughly five times more frequently than a standard diffusion would | [uncited] | | | Verify quantitative claim "five times" |
| 24 | 311-315 | defining-formula | Variogram: m(q, h) = (1/(T-h)) * sum_{t=1}^{T-h} \|X_{t+h} - X_t\|^q (Eq. 7.3) | GJR2018 | | | |
| 25 | 322 | supporting-formula | If X_t behaves like fBM with exponent H, then m(q, h) is proportional to h^{qH} | GJR2018 | | | |
| 26 | 323 | supporting-formula | log m(q, h) = qH * log h + const; slope of regression gives qH | GJR2018 | | | |
| 27 | 377 | numerical-fact | Worked example: OLS slope through the five data points is approximately 0.245 | [uncited] | | | Verify arithmetic of worked example |
| 28 | 380 | supporting-formula | slope = qH = 2H, so H = 0.245/2 = 0.12 | [uncited] | | | Arithmetic check |
| 29 | 441 | attribution | BLP2022 extend the analysis of GJR2018 to a broad cross-section of asset classes | BLP2022 | | | |
| 30a | 441 | qualitative | BLP2022 cover equities, equity indices, FX, fixed income, commodities | BLP2022 | | | Verify all asset classes listed |
| 30b | 441 | numerical-fact | BLP2022 confirm that H approx 0.1 is universal across asset classes | BLP2022 | | | |
| 31 | 442 | qualitative | The Hurst exponent does not vary meaningfully across asset classes, geographies, or time periods | BLP2022 | | | |
| 32 | 469-471 | defining-formula | RFSV model: log RV_t = mu + sigma_v * B^H_t (Eq. 7.4) | GJR2018 | | | |
| 33 | 482-483 | defining-formula | RFSV forecast: hat{log RV}_{T+1} = sum_{k=0}^{T-1} w_k * log RV_{T-k} (Eq. 7.5) | GJR2018 | | | |
| 34 | 488 | supporting-formula | RFSV weights decay as power law: w_k proportional to k^{H - 3/2} for large k | GJR2018 | | | Verify exponent H - 3/2 |
| 35 | 489 | numerical-fact | When H = 0.1, the weight decay is k^{-1.4} | [uncited] | | | Arithmetic: 0.1 - 1.5 = -1.4 |
| 36 | 494 | qualitative | RFSV achieves HAR-level forecasting accuracy with essentially one free parameter (H) | GJR2018 | | | |
| 37 | 505 | numerical-fact | At H = 0.1, the weight on an observation from 22 days ago is still roughly 15-20% of the weight on yesterday's observation | [uncited] | | | Verify: w_22/w_1 = 22^{-1.4}/1^{-1.4} = 22^{-1.4} |
| 38 | 527 | numerical-fact | Worked example: sum of RFSV weights for lag 1 (yesterday) is approx 0.35 | [uncited] | | | Verify normalization of k^{-1.4} weights over k=1..22 |
| 39 | 528 | numerical-fact | Worked example: sum of RFSV weights for lags 2-5 is approx 0.30 | [uncited] | | | |
| 40 | 529 | numerical-fact | Worked example: sum of RFSV weights for lags 6-22 is approx 0.35 | [uncited] | | | |
| 41 | 527 | numerical-fact | HAR beta_d approx 0.36 (attributed to Corsi 2009) | Corsi2009 | | | Verify Corsi's reported coefficients |
| 42 | 528 | numerical-fact | HAR beta_w approx 0.28 | Corsi2009 | | | |
| 43 | 529 | numerical-fact | HAR beta_m approx 0.28 | Corsi2009 | | | |
| 44 | 554 | attribution | Bayer, Friz, and Gatheral introduced the rough Bergomi model, the first pricing model built on rough volatility | BFG2016 | | | |
| 45 | 555 | numerical-fact | In the rough Bergomi model, the variance process uses fBM with H approx 0.07 | BFG2016 | | | |
| 46 | 561 | qualitative | With H approx 0.07, rough Bergomi generates steep short-dated smiles matching market data far better than Heston | BFG2016 | | | |
| 47 | 561 | qualitative | Rough Bergomi has no closed-form solution; simulation is required for pricing | BFG2016 | | | |
| 48 | 562 | numerical-fact | Quadratic rough Heston uses roughness parameter H approx 0.05-0.1 | [uncited] | | | No specific citation for QRH |
| 49 | 562 | qualitative | Quadratic rough Heston jointly fits SPX option smiles and VIX option smiles, a combination no standard model achieves | [uncited] | | | No specific citation for QRH |
| 50 | 583 | attribution | Cont and Das argue that observed roughness is partly a microstructure-noise artefact | ContDas2024 | | | |
| 51 | 588 | qualitative | Even if true sigma^2_t follows a standard semimartingale with H = 0.5, the estimated log RV_t can exhibit H approx 0.1 due to noise | ContDas2024 | | | Core Cont-Das result |
| 52 | 674 | qualitative | Each day's RV_t differs from true IV_t by an estimation error eta_t; these errors are approximately independent across days | ContDas2024 | | | |
| 53 | 676 | qualitative | Adding i.i.d. noise to a smooth signal makes increments of the noisy series negatively autocorrelated | ContDas2024 | | | |
| 54 | 704 | attribution | Rosenbaum and Zhang train a single LSTM on hundreds of individual stocks simultaneously | RosenbaumZhang2022 | | | |
| 55 | 705 | qualitative | The universal LSTM matches the forecasting performance of RFSV and Quadratic Rough Heston parametric forecaster | RosenbaumZhang2022 | | | |
| 56 | 731 | qualitative | The universal LSTM trained on a broad cross-section transfers well to assets it has never seen, including out-of-sample asset classes | RosenbaumZhang2022 | | | |
| 57 | 736 | qualitative | Both RFSV and universal LSTM produce forecasts competitive with HAR | RosenbaumZhang2022 | | | |
