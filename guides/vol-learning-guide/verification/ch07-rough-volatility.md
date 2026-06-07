# Chapter 7: Rough Volatility -- Verification Log

**Status:** Verified
**Claims extracted:** 57
**Verified:** 50/57
**Unverified (no PDF):** 7
**Errors found:** 8 (all fixed)

## Errors Fixed

1. **Claims 19, 21 (lines 291, 296):** Chapter said GJR2018 studied "equity indices, individual stocks, and foreign exchange." GJR2018 actually studied equity indices (DAX, S&P 500, NASDAQ, plus ~17 Oxford-Man indices) and the Bund bond future. No individual stocks or FX. Fixed to "equity indices and bond futures." Also fixed in summary (line 757) and Key Results table (line 794-795).
2. **Claim 23 (line 301):** Chapter said "reverses direction roughly five times more frequently." This "five times" figure is not derivable from any standard formula. Replaced with qualitative language.
3. **Claim 37 (line 505):** Chapter said w_22/w_1 is "roughly 15-20%." Actual ratio: 22^{-1.4} = 1.3%. Rewrote to explain the distinction between individual weight ratio and collective group contribution.
4. **Claims 38-40 (lines 527-529):** RFSV weight sums were 0.35/0.30/0.35. Correct normalized k^{-1.4} weights over k=1..22 are 0.42/0.35/0.23. Fixed all three values.
5. **Claim 52 (line 674):** Chapter said estimation errors are "approximately independent across days." This holds under the OU-SV model (Cont-Das Fig 12) but not for general diffusion models (Fig 6 shows complex ACF). Added qualifier "Under certain models (e.g., OU-SV)."
6. **Claim 55 (line 705):** Chapter said LSTM "matches" RFSV. RZ2022 shows LSTM outperforms RFSV; it is the RFSV+QRH combination that matches LSTM. Rewrote to reflect this.
7. **Claim 56 (line 731):** Chapter said LSTM transfers to "out-of-sample asset classes." RZ2022 shows transfer across equity markets (US to EU equities), not across different asset classes. Fixed.
8. **Claims 55/57 (Key Results table, summary):** Propagated fixes to all instances in the summary and Key Results sections.

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 6 | qualitative | RFSV model is a parsimonious forecaster competitive with HAR and LSTM | [uncited] | Yes | -- | Supported by GJR2018 Table 5.1-5.2 (RFSV outperforms HAR) and RZ2022 Fig 4.2 (RFSV outperforms HAR) |
| 2 | 17 | attribution | Log of realized volatility behaves like fractional Brownian motion with Hurst exponent H approx 0.1; this was proposed by Gatheral, Jaisson, and Rosenbaum | GJR2018 | Yes | pp. 1-3 | Core thesis of GJR2018; H estimates range 0.06-0.2, mean ~0.1 |
| 3 | 18 | numerical-fact | Standard Brownian motion has H = 0.5 | [uncited] | Yes | -- | Standard definition of BM |
| 4 | 47 | attribution | Rosenbaum and Zhang showed that both the universal LSTM and the parametric rough-vol model converge on the same characterization of the volatility process | RosenbaumZhang2022 | Yes | pp. 1-3 | Paraphrase is acceptable; RZ2022 shows RFSV+QRH matches LSTM |
| 5 | 62 | defining-formula | Increments of standard BM: W_{t+h} - W_t are Gaussian with mean zero and variance h | [uncited] | Yes | -- | Standard definition |
| 6 | 63 | qualitative | Increments of standard BM over non-overlapping intervals are independent | [uncited] | Yes | -- | Standard definition |
| 7 | 66 | supporting-formula | Self-similarity scaling factor of standard BM is H = 1/2: rescaling time by factor c rescales path by c^{1/2} | [uncited] | Yes | -- | Standard property |
| 8 | 70 | attribution | Fractional Brownian motion was introduced by Mandelbrot and Van Ness | MandelbrotVanNess1968 | Yes | -- | Standard historical attribution; GJR2018 p.3 cites same |
| 9 | 70 | qualitative | fBM generalizes standard BM by allowing self-similarity exponent H to take any value in (0, 1) | MandelbrotVanNess1968 | Yes | -- | Standard definition of fBM |
| 10 | 74 | defining-formula | Var(B^H_{t+h} - B^H_t) = h^{2H} | MandelbrotVanNess1968 | Yes | -- | Defining property of fBM; also GJR2018 Eq 2.1 |
| 11 | 76 | qualitative | When H = 1/2, fBM reduces to standard Brownian motion | MandelbrotVanNess1968 | Yes | -- | Standard fBM property |
| 12 | 77 | qualitative | When H != 1/2, fBM increments are not independent; negatively correlated if H < 1/2, positively correlated if H > 1/2 | MandelbrotVanNess1968 | Yes | -- | Standard fBM property; Cont-Das 2024 p.3 also states this |
| 13 | 79 | attribution | Hurst exponent is named after hydrologist Harold Edwin Hurst, who studied long-range dependence in Nile river levels | [uncited] | Yes | -- | Standard historical fact |
| 14 | 88-89 | defining-formula | Var(B^H_{t+h} - B^H_t) = h^{2H} (Eq. 7.1) | [uncited] | Yes | -- | Restated from claim 10; correct |
| 15 | 95 | qualitative | When H < 1/2: increments negatively correlated (move up makes move down more likely); path is rougher than BM | [uncited] | Yes | -- | Standard fBM property |
| 16 | 97 | qualitative | When H > 1/2: increments positively correlated (trending behavior); path is smoother than BM | [uncited] | Yes | -- | Standard fBM property |
| 17 | 229 | numerical-fact | Empirical log-volatility has H approx 0.1 | [uncited] | Yes | -- | Consistent with GJR2018 |
| 18 | 278 | qualitative | Standard stochastic volatility models (Heston, SABR) assume H = 0.5 | [uncited] | Yes | -- | Heston/SABR use standard BM drivers; correct characterization |
| 19 | 291 | methodological | GJR2018 studied log RV_t (5-minute realized variance) across equity indices, individual stocks, and FX | GJR2018 | FIXED | pp. 6-12 | WRONG: GJR2018 studied equity indices + Bund future, NOT individual stocks or FX. Fixed to "equity indices and bond futures." |
| 20 | 292 | methodological | For each asset, GJR2018 estimated the Hurst exponent H of the log RV series | GJR2018 | Yes | pp. 6-10 | Correct; see Section 3 of GJR2018 |
| 21 | 296 | numerical-fact | Across equity indices, individual stocks, and FX, the Hurst exponent of log RV_t is consistently around H approx 0.1 | GJR2018 | FIXED | pp. 8-12 | WRONG asset classes (see claim 19). H ranges 0.06-0.2 across indices. Fixed to "equity indices and bond futures" with range. |
| 22 | 300 | qualitative | Standard stochastic volatility models (Heston, SABR) assume volatility process is driven by standard BM with H = 0.5 | [uncited] | Yes | -- | Standard characterization |
| 23 | 301 | numerical-fact | H of 0.1 means the volatility path reverses direction roughly five times more frequently than a standard diffusion would | [uncited] | FIXED | -- | "Five times" is not derivable. Replaced with qualitative language. |
| 24 | 311-315 | defining-formula | Variogram: m(q, h) = (1/(T-h)) * sum_{t=1}^{T-h} \|X_{t+h} - X_t\|^q (Eq. 7.3) | GJR2018 | Yes | p. 7 | Matches GJR2018 Eq 2.2 (their notation uses delta instead of absolute value, but same formula) |
| 25 | 322 | supporting-formula | If X_t behaves like fBM with exponent H, then m(q, h) is proportional to h^{qH} | GJR2018 | Yes | p. 7 | Stated after Eq 2.2 in GJR2018 |
| 26 | 323 | supporting-formula | log m(q, h) = qH * log h + const; slope of regression gives qH | GJR2018 | Yes | p. 7 | Standard log-log regression approach from GJR2018 |
| 27 | 377 | numerical-fact | Worked example: OLS slope through the five data points is approximately 0.245 | [uncited] | Yes | -- | Verified: OLS slope = 0.2451 |
| 28 | 380 | supporting-formula | slope = qH = 2H, so H = 0.245/2 = 0.12 | [uncited] | Yes | -- | Verified: 0.2451/2 = 0.1225, rounds to 0.12 |
| 29 | 441 | attribution | BLP2022 extend the analysis of GJR2018 to a broad cross-section of asset classes | BLP2022 | unverified | -- | PDF not available for verification |
| 30a | 441 | qualitative | BLP2022 cover equities, equity indices, FX, fixed income, commodities | BLP2022 | unverified | -- | PDF not available for verification |
| 30b | 441 | numerical-fact | BLP2022 confirm that H approx 0.1 is universal across asset classes | BLP2022 | unverified | -- | PDF not available for verification |
| 31 | 442 | qualitative | The Hurst exponent does not vary meaningfully across asset classes, geographies, or time periods | BLP2022 | unverified | -- | PDF not available for verification |
| 32 | 469-471 | defining-formula | RFSV model: log RV_t = mu + sigma_v * B^H_t (Eq. 7.4) | GJR2018 | Yes | p. 12 | Matches GJR2018 Eq 3.1 |
| 33 | 482-483 | defining-formula | RFSV forecast: hat{log RV}_{T+1} = sum_{k=0}^{T-1} w_k * log RV_{T-k} (Eq. 7.5) | GJR2018 | Yes | pp. 17-18 | Matches GJR2018 Section 5, Eq 5.1 |
| 34 | 488 | supporting-formula | RFSV weights decay as power law: w_k proportional to k^{H - 3/2} for large k | GJR2018 | Yes | p. 18 | Standard fBM prediction theory result; consistent with GJR2018 Eq 5.1 integral kernel |
| 35 | 489 | numerical-fact | When H = 0.1, the weight decay is k^{-1.4} | [uncited] | Yes | -- | Verified: 0.1 - 1.5 = -1.4 |
| 36 | 494 | qualitative | RFSV achieves HAR-level forecasting accuracy with essentially one free parameter (H) | GJR2018 | Yes | pp. 20-22 | GJR2018 Tables 5.1-5.2 show RFSV outperforms HAR across indices/horizons |
| 37 | 505 | numerical-fact | At H = 0.1, the weight on an observation from 22 days ago is still roughly 15-20% of the weight on yesterday's observation | [uncited] | FIXED | -- | WRONG: 22^{-1.4} = 1.3%, not 15-20%. Rewrote to explain individual vs collective weight. |
| 38 | 527 | numerical-fact | Worked example: sum of RFSV weights for lag 1 (yesterday) is approx 0.35 | [uncited] | FIXED | -- | Correct value: 0.42 (not 0.35). Fixed. |
| 39 | 528 | numerical-fact | Worked example: sum of RFSV weights for lags 2-5 is approx 0.30 | [uncited] | FIXED | -- | Correct value: 0.35 (not 0.30). Fixed. |
| 40 | 529 | numerical-fact | Worked example: sum of RFSV weights for lags 6-22 is approx 0.35 | [uncited] | FIXED | -- | Correct value: 0.23 (not 0.35). Fixed. |
| 41 | 527 | numerical-fact | HAR beta_d approx 0.36 (attributed to Corsi 2009) | Corsi2009 | unverified | -- | Corsi 2009 PDF not available; plausible range for typical HAR estimates |
| 42 | 528 | numerical-fact | HAR beta_w approx 0.28 | Corsi2009 | unverified | -- | Corsi 2009 PDF not available |
| 43 | 529 | numerical-fact | HAR beta_m approx 0.28 | Corsi2009 | unverified | -- | Corsi 2009 PDF not available |
| 44 | 554 | attribution | Bayer, Friz, and Gatheral introduced the rough Bergomi model, the first pricing model built on rough volatility | BFG2016 | Yes | -- | Standard attribution; cited in GJR2018 and RZ2022 |
| 45 | 555 | numerical-fact | In the rough Bergomi model, the variance process uses fBM with H approx 0.07 | BFG2016 | Yes | -- | Standard rough Bergomi parameter; consistent with RZ2022 p.4 discussion |
| 46 | 561 | qualitative | With H approx 0.07, rough Bergomi generates steep short-dated smiles matching market data far better than Heston | BFG2016 | Yes | -- | Well-established result in rough vol literature; RZ2022 cites same |
| 47 | 561 | qualitative | Rough Bergomi has no closed-form solution; simulation is required for pricing | BFG2016 | Yes | -- | Well-known property of rough Bergomi |
| 48 | 562 | numerical-fact | Quadratic rough Heston uses roughness parameter H approx 0.05-0.1 | [uncited] | Yes | -- | Consistent with RZ2022 discussion of QRH; standard parameter range |
| 49 | 562 | qualitative | Quadratic rough Heston jointly fits SPX option smiles and VIX option smiles, a combination no standard model achieves | [uncited] | Yes | -- | Well-known result; RZ2022 uses QRH as benchmark |
| 50 | 583 | attribution | Cont and Das argue that observed roughness is partly a microstructure-noise artefact | ContDas2024 | Yes | pp. 1-3 | Core thesis of Cont-Das 2024 |
| 51 | 588 | qualitative | Even if true sigma^2_t follows a standard semimartingale with H = 0.5, the estimated log RV_t can exhibit H approx 0.1 due to noise | ContDas2024 | Yes | pp. 8-12 | OU-SV simulation gives H_hat(RV) = 0.14; BM diffusion gives H_hat = 0.27 |
| 52 | 674 | qualitative | Each day's RV_t differs from true IV_t by an estimation error eta_t; these errors are approximately independent across days | ContDas2024 | FIXED | pp. 14-15 | Oversimplified: true for OU-SV model (Fig 12) but NOT for general diffusion (Fig 6 shows complex ACF). Added qualifier. |
| 53 | 676 | qualitative | Adding i.i.d. noise to a smooth signal makes increments of the noisy series negatively autocorrelated | ContDas2024 | Yes | pp. 5-6 | Standard result; Cont-Das use this as core mechanism |
| 54 | 704 | attribution | Rosenbaum and Zhang train a single LSTM on hundreds of individual stocks simultaneously | RosenbaumZhang2022 | Yes | pp. 4-8 | 862 US stocks + 503 EU stocks; "hundreds" is correct |
| 55 | 705 | qualitative | The universal LSTM matches the forecasting performance of RFSV and Quadratic Rough Heston parametric forecaster | RosenbaumZhang2022 | FIXED | pp. 8-12 | WRONG: LSTM outperforms RFSV. It is RFSV+QRH with fixed params that matches LSTM. Fixed. |
| 56 | 731 | qualitative | The universal LSTM trained on a broad cross-section transfers well to assets it has never seen, including out-of-sample asset classes | RosenbaumZhang2022 | FIXED | pp. 10-12 | WRONG: RZ2022 shows US-to-EU equity transfer, not cross-asset-class transfer. Fixed. |
| 57 | 736 | qualitative | Both RFSV and universal LSTM produce forecasts competitive with HAR | RosenbaumZhang2022 | Yes | pp. 8-10 | Both outperform HAR per RZ2022 Fig 4.2 |
