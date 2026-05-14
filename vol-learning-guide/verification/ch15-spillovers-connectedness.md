# Chapter 15: Volatility Spillovers and Connectedness -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 48
**Verified:** 0/48
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 35-38 | defining-formula | VAR($p$) on RV vector: $\by_t = \bm{c} + \sum_{\ell=1}^{p} \bm{A}_\ell \by_{t-\ell} + \bm{u}_t$, $\bm{u}_t \sim (0, \bm{\Sigma})$ | [uncited] | | | Standard VAR specification; verify notation matches DY papers |
| 2 | 68 | supporting-formula | MA representation: $\by_t = \bm{\mu} + \sum_{h=0}^{\infty} \bm{\Phi}_h \bm{u}_{t-h}$ | [uncited] | | | Standard Wold representation of VAR; verify form |
| 3 | 93-94 | attribution | GFEVD introduced by Pesaran and Shin (1998) | PesaranShin1998 | | | Verify GFEVD attribution |
| 4 | 94 | attribution | GFEVD adopted by Diebold and Yilmaz (2012) for spillover framework | DieboldYilmaz2012 | | | Verify DY2012 uses Pesaran-Shin GFEVD |
| 5 | 95 | qualitative | GFEVD "does not depend on variable ordering (unlike Cholesky decompositions)" | PesaranShin1998 | | | Key advantage of generalized approach; verify in PS1998 |
| 6 | 100-109 | defining-formula | GFEVD formula: $\theta_{jk}^{(H)} = \frac{\sigma_{kk}^{-1} \sum_{h=0}^{H-1} (\bm{e}_j' \bm{\Phi}_h \bm{\Sigma} \bm{e}_k)^2}{\sum_{h=0}^{H-1} \bm{e}_j' \bm{\Phi}_h \bm{\Sigma} \bm{\Phi}_h' \bm{e}_j}$ | PesaranShin1998, DieboldYilmaz2012 | | | Core GFEVD formula; verify exact form matches PS1998 or DY2012 |
| 7 | 115 | methodological | Forecast horizon $H$ "typically 10 days" | [uncited] | | | Verify DY papers use H=10 as default |
| 8 | 135 | qualitative | "GFEVD rows do not sum to one in general" | PesaranShin1998 | | | Verify this is a known property of GFEVD |
| 9 | 137-139 | supporting-formula | Row normalization: $\widetilde{\theta}_{jk}^{(H)} = \theta_{jk}^{(H)} / \sum_{k=1}^{N} \theta_{jk}^{(H)}$ so rows sum to 1 | DieboldYilmaz2012 | | | Verify normalization convention matches DY2012 |
| 10 | 165-168 | defining-formula | Total spillover index: $S^{(H)} = \frac{1}{N} \sum_{j \neq k} \widetilde{\theta}_{jk}^{(H)} \times 100$ | DieboldYilmaz2012 | | | Verify exact formula matches DY2012 |
| 11 | 172-176 | defining-formula | Directional FROM spillover: $S_{j \leftarrow \bullet}^{(H)} = \frac{1}{N} \sum_{k \neq j} \widetilde{\theta}_{jk}^{(H)} \times 100$ | DieboldYilmaz2012 | | | Verify exact formula matches DY2012 |
| 12 | 180-184 | defining-formula | Directional TO spillover: $S_{j \rightarrow \bullet}^{(H)} = \frac{1}{N} \sum_{k \neq j} \widetilde{\theta}_{kj}^{(H)} \times 100$ | DieboldYilmaz2012 | | | Verify exact formula matches DY2012 |
| 13 | 188-189 | defining-formula | Net spillover: $S_j^{\text{net},(H)} = S_{j \rightarrow \bullet}^{(H)} - S_{j \leftarrow \bullet}^{(H)}$ | DieboldYilmaz2012 | | | Verify definition matches DY2012 |
| 14 | 191-192 | qualitative | "A positive net spillover means asset $j$ is a net transmitter of volatility; negative means net receiver" | DieboldYilmaz2012 | | | Verify interpretation |
| 15 | 206 | attribution | Diebold and Yilmaz (2009) "introduced the total index using a Cholesky decomposition" | DieboldYilmaz2009 | | | Verify DY2009 used Cholesky, not GFEVD |
| 16 | 207 | attribution | Diebold and Yilmaz (2012) "added directional measures and switched to GFEVD" | DieboldYilmaz2012 | | | Verify DY2012 introduced directional measures and adopted GFEVD |
| 17 | 208-209 | attribution | Diebold and Yilmaz (2014) "refined the generalized VAR approach and applied it to a broader set of markets" | DieboldYilmaz2014 | | | Verify DY2014 scope and contribution |
| 18 | 269-270 | numerical-fact | Worked example: 3-asset GFEVD table with Equity row = (60, 25, 15), Bonds row = (30, 55, 15), FX row = (20, 10, 70) | [uncited] | | | Self-consistent example; verify rows sum to 100 |
| 19 | 278 | numerical-fact | FROM others: Equity = 40 (i.e., 25 + 15 = 40) | [uncited] | | | Verify arithmetic: 25+15=40 |
| 20 | 279 | numerical-fact | FROM others: Bonds = 45 (i.e., 30 + 15 = 45) | [uncited] | | | Verify arithmetic: 30+15=45 |
| 21 | 280 | numerical-fact | FROM others: FX = 30 (i.e., 20 + 10 = 30) | [uncited] | | | Verify arithmetic: 20+10=30 |
| 22 | 282 | numerical-fact | TO others: Equity = 50 (i.e., 30 + 20 = 50) | [uncited] | | | Verify arithmetic: 30+20=50 |
| 23 | 282 | numerical-fact | TO others: Bonds = 35 (i.e., 25 + 10 = 35) | [uncited] | | | Verify arithmetic: 25+10=35 |
| 24 | 282 | numerical-fact | TO others: FX = 30 (i.e., 15 + 15 = 30) | [uncited] | | | Verify arithmetic: 15+15=30 |
| 25 | 290 | numerical-fact | $S_{\text{Equity} \leftarrow \bullet} = (25 + 15)/3 = 13.3\%$ | [uncited] | | | Verify arithmetic: 40/3 = 13.333... |
| 26 | 291 | numerical-fact | $S_{\text{Bonds} \leftarrow \bullet} = (30 + 15)/3 = 15.0\%$ | [uncited] | | | Verify arithmetic: 45/3 = 15.0 |
| 27 | 292 | numerical-fact | $S_{\text{FX} \leftarrow \bullet} = (20 + 10)/3 = 10.0\%$ | [uncited] | | | Verify arithmetic: 30/3 = 10.0 |
| 28 | 298 | numerical-fact | $S_{\text{Equity} \rightarrow \bullet} = (30 + 20)/3 = 16.7\%$ | [uncited] | | | Verify arithmetic: 50/3 = 16.667... |
| 29 | 299 | numerical-fact | $S_{\text{Bonds} \rightarrow \bullet} = (25 + 10)/3 = 11.7\%$ | [uncited] | | | Verify arithmetic: 35/3 = 11.667... |
| 30 | 300 | numerical-fact | $S_{\text{FX} \rightarrow \bullet} = (15 + 15)/3 = 10.0\%$ | [uncited] | | | Verify arithmetic: 30/3 = 10.0 |
| 31 | 305 | numerical-fact | $S_{\text{Equity}}^{\text{net}} = 16.7 - 13.3 = +3.4\%$ (net transmitter) | [uncited] | | | Verify arithmetic: 16.667-13.333=3.333 (rounds to 3.3, text says 3.4) |
| 32 | 306 | numerical-fact | $S_{\text{Bonds}}^{\text{net}} = 11.7 - 15.0 = -3.3\%$ (net receiver) | [uncited] | | | Verify arithmetic: 11.667-15.0=-3.333 (rounds to -3.3) |
| 33 | 307 | numerical-fact | $S_{\text{FX}}^{\text{net}} = 10.0 - 10.0 = 0.0\%$ (neutral) | [uncited] | | | Verify arithmetic: 10.0-10.0=0.0 |
| 34 | 312-315 | numerical-fact | Total spillover $S^{(10)} = \frac{25+15+30+15+20+10}{3 \times 3} \times 100 = \frac{115}{9} \times 100 \approx 38.3\%$ | [uncited] | | | Verify arithmetic: 115/9=12.778, times 100=1277.8 -- formula appears inconsistent with $\times 100$ factor; check against DY2012 definition |
| 35 | 381 | methodological | Rolling window "typically $w = 200$" days | DieboldYilmaz2012 | | | Verify DY2012 uses 200-day window |
| 36 | 387-389 | numerical-fact | "Calm periods: $S^{(H)}_t \approx 30$--$40\%$" and "Crises (2008 GFC, 2020 COVID): $S^{(H)}_t$ spikes to 70--$85\%$" | [uncited] | | | Verify typical ranges against DY2012 empirical results |
| 37 | 395-396 | methodological | "Too short ($w < 100$): noisy, unstable VAR estimates. Too long ($w > 300$): sluggish, crises get averaged out" | DieboldYilmaz2012 | | | Verify DY2012 discusses window length sensitivity |
| 38 | 450-451 | attribution | Antonakakis, Chatziantoniou, and Gabauer (2020) "replace the rolling-window VAR with a time-varying parameter VAR (TVP-VAR) estimated via the Kalman filter" | AntonakakisChatziantoniouGabauer2020 | | | Verify ACG2020 contribution |
| 39 | 492-496 | qualitative | "TVP-VAR connectedness is smoother than rolling-window estimates, avoids the abrupt entry/exit artifacts when extreme observations enter or leave the window, and responds faster to genuine structural breaks" | AntonakakisChatziantoniouGabauer2020 | | | Verify these specific advantages claimed in ACG2020 |
| 40 | 527 | attribution | Demirer, Diebold, Liu, and Yilmaz (2018) documented calm vs. crisis network structural shift | DemirerDieboldLiuYilmaz2018 | | | Verify DDLY2018 shows calm-to-crisis topology change |
| 41a | 629-632 | attribution | Sirignano and Cont (2019) "train a single feedforward network to predict returns and volatility by pooling data across all assets (stocks, currencies, commodities)" | SirignanoCont2019 | | | Verify model type (feedforward), pooling approach, and asset classes |
| 41b | 632-633 | qualitative | "The pooled ('universal') model performs comparably to individual asset-specific models" | SirignanoCont2019 | | | Verify performance comparison claim |
| 42a | 635-636 | qualitative | Sirignano and Cont (2019) show "a model trained on one asset class transfers well to others with minimal fine-tuning" | SirignanoCont2019 | | | Verify transferability claim |
| 42b | 637-638 | qualitative | "universality holds for features based on returns, realized volatility, and order-flow imbalance" | SirignanoCont2019 | | | Verify which features show universality |
| 43a | 643-644 | attribution | Rosenbaum and Zhang (2022) estimate the Hurst exponent across assets "using a universal LSTM" | RosenbaumZhang2022 | | | Verify method is LSTM-based |
| 43b | 644-645 | numerical-fact | "$H \approx 0.1$ everywhere (equities, FX, rates, commodities)" | RosenbaumZhang2022 | | | Verify Hurst exponent value and asset classes covered |
| 44 | 608-610 | qualitative | "Calm periods: within-sector connectedness dominates. Equity shocks stay in equities; bond shocks stay in bonds. Total spillover index is low (30--40%)" | [uncited] | | | Stylized fact from DY literature; verify against DY2012/DY2014 |
| 45 | 611-613 | qualitative | "Crises: cross-sector connectedness surges. The network topology shifts from clustered to nearly fully connected. Total spillover jumps to 70--85%" | [uncited] | | | Verify crisis-period topology claim |
| 46 | 614-616 | qualitative | "in calm markets, commodity shocks are often isolated; during crises, equity and credit become dominant transmitters" | DieboldYilmaz2014 | | | Verify transmitter identity shift in DY2014 |
| 47 | 754-756 | attribution | Demirer, Diebold, Liu, and Yilmaz (2018) "applied the DY framework to a global network of banks and sovereigns" | DemirerDieboldLiuYilmaz2018 | | | Verify application scope (banks and sovereigns) |
| 48 | 773-774 | qualitative | "GFEVD approach generalizes the Cholesky decomposition and does not depend on variable ordering, making it suitable for large cross-sections" | [uncited] | | | Verify ordering-invariance claim for GFEVD |
