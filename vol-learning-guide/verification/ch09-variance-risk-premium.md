# Chapter 9: The Variance Risk Premium -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 62
**Verified:** 0/62
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 6 | attribution | VRP "predicts equity returns" | \citep{BTZ2009} | | | |
| 2 | 40 | qualitative | "Option prices reflect Q-expectations, not P-expectations" | [uncited] | | | Standard asset pricing result |
| 3 | 41 | qualitative | "VIX is a Q-measure of expected variance" | [uncited] | | | Standard; follows from CBOE VIX construction |
| 4 | 47 | methodological | VRP horizon h is "typically 30 calendar days (~22 trading days) to match VIX" | [uncited] | | | Convention in VRP literature |
| 5 | 52 | defining-formula | $\VRP_t = \E^{\mathbb{Q}}_t[\RV_{t,t+h}] - \E^{\mathbb{P}}_t[\RV_{t,t+h}]$ | [uncited] | | | Standard theoretical VRP definition |
| 6 | 74-77 | defining-formula | $\widehat{\VRP}_t = (\text{VIX}_t/100)^2 - \hat{\RV}^{\mathbb{P}}_{t,t+h}$ (operationalized VRP) | [uncited] | | | Standard operational measure used in BTZ2009 and others |
| 7 | 80 | qualitative | VIX squared "equals the model-free risk-neutral expected variance over 30 days" | [uncited] | | | Follows from VIX construction |
| 8 | 86 | qualitative | VRP is "positive on average" | [uncited] | | | Established empirical fact; quantified by Carr2009 on line 729 |
| 9 | 87 | qualitative | Negative VRP is "rare, but occurs when realized vol spikes above what was priced in (e.g., crash events)" | [uncited] | | | |
| 10 | 105 | attribution | BTZ2009 "use the ex-ante version with backward-looking RV" | \citet{BTZ2009} | | | Verify which P-measure proxy BTZ use |
| 11 | 106 | attribution | Bekaert and Hoerova (2014) "show that the choice of P-measure proxy matters for return predictability" | \citet{BekaertHoerova2014} | | | |
| 12 | 111 | numerical-fact | Worked example: VIX = 13.5, RV = 0.0105, annualized realized vol = sqrt(0.0105) ~ 10.2% | [uncited] | | | Arithmetic: sqrt(0.0105) = 0.10247... ~ 10.2%. Check. |
| 13 | 115 | numerical-fact | Worked example: VIX^2 = (13.5/100)^2 = 0.018225 | [uncited] | | | Arithmetic: 0.135^2 = 0.018225. Check. |
| 14 | 126 | numerical-fact | Worked example: VRP = 0.018225 - 0.0105 = 0.007725 | [uncited] | | | Arithmetic check needed |
| 15 | 131 | numerical-fact | Worked example: "VRP is 0.0077, or about 42% of the implied variance" | [uncited] | | | Check: 0.007725/0.018225 = 0.4238... ~ 42%. |
| 16 | 130 | numerical-fact | Worked example: "the gap is about 3.3 percentage points" (13.5% - 10.2%) | [uncited] | | | Arithmetic: 13.5 - 10.2 = 3.3 |
| 17 | 143 | qualitative | "If markets were risk-neutral (if investors did not care about risk), then Q = P and VRP would be zero" | [uncited] | | | Standard theoretical result |
| 18 | 176 | attribution | Drechsler and Yaron (2011) model uses "Epstein-Zin preferences (a generalization of standard utility that separates risk aversion from the willingness to substitute consumption over time)" | \citet{DrechslerYaron2011} | | | Verify EZ preferences are the mechanism in this paper |
| 19 | 177-179 | attribution | In the DY2011 model, "volatility of volatility in the real economy generates a variance risk premium in asset markets" | \citet{DrechslerYaron2011} | | | Verify vol-of-vol mechanism |
| 20 | 199 | attribution | VRP predicting returns is "the central empirical finding of" Bollerslev, Tauchen, and Zhou (2009) | \citet{BTZ2009} | | | |
| 21 | 208 | qualitative | BTZ2009 find "the VRP coefficient is positive and statistically significant: higher VRP today predicts higher equity returns over the next quarter" | \citet{BTZ2009} | | | |
| 22 | 211 | numerical-fact | BTZ2009: "a one-standard-deviation increase in VRP predicts approximately 3-4% higher quarterly excess returns" | \citet{BTZ2009} | | | Verify exact magnitude |
| 23 | 212 | numerical-fact | BTZ2009: "the R^2 for quarterly return prediction is 5-10%" | \citet{BTZ2009} | | | Verify R^2 range |
| 24 | 212 | qualitative | BTZ2009: quarterly R^2 "substantially exceeding the dividend yield (the previous best-known predictor at the quarterly horizon)" | \citet{BTZ2009} | | | Verify comparison to dividend yield |
| 25 | 213 | qualitative | BTZ2009: "the predictability is concentrated at the 1-6 month horizon and fades at longer horizons" | \citet{BTZ2009} | | | Verify horizon structure |
| 26 | 215 | methodological | BTZ2009 "operationalize VRP as VIX^2_t - RV_{t-22,t}, using backward-looking monthly RV as the P-measure proxy" | \citet{BTZ2009} | | | Verify operational definition used |
| 27 | 223 | numerical-fact | Worked example: VIX^2 = (14.0/100)^2 = 0.0196 | [uncited] | | | Arithmetic: 0.14^2 = 0.0196. Check. |
| 28 | 224 | numerical-fact | Worked example: RV_past_month = (9.5/100)^2 = 0.009025 | [uncited] | | | Arithmetic: 0.095^2 = 0.009025. Check. |
| 29 | 225 | numerical-fact | Worked example: VRP = 0.0196 - 0.009025 = 0.010575 | [uncited] | | | Arithmetic check needed |
| 30 | 233 | numerical-fact | "In March 2020, VIX hit 82.7" | [uncited] | | | Verify: VIX intraday high was 82.69 on March 16, 2020 |
| 31 | 233 | numerical-fact | In March 2020, "trailing realized vol was around 30%" | [uncited] | | | Approximate; verify order of magnitude |
| 32 | 234 | numerical-fact | Worked example: VRP ~ (0.827)^2 - (0.30)^2 = 0.684 - 0.090 = 0.594 | [uncited] | | | Arithmetic: 0.827^2 = 0.683929, 0.30^2 = 0.09, diff = 0.593929. Check. |
| 33 | 235 | numerical-fact | "the S&P 500 rallied over 40% in the subsequent two quarters" after March 2020 | [uncited] | | | Verify: S&P 500 low ~2237 (Mar 23), 6 months later ~3580 (Sep 23) = ~60% rally |
| 34 | 262 | qualitative | When VRP is large, "the gap closes from both sides, but with realized vol doing more of the adjustment" | [uncited] | | | Mean-reversion claim; no specific citation |
| 35 | 273 | qualitative | "Including VIX (or VIX-squared) alongside lagged RV in a HAR-type model improves out-of-sample forecasts" | [uncited] | | | Widely documented but uncited here |
| 36 | 288 | attribution | Bekaert and Hoerova (2014) "decompose the VIX-squared into two pieces" (expected variance + VRP) | \citet{BekaertHoerova2014} | | | |
| 37 | 290-291 | supporting-formula | $\text{VIX}^2_t = \E^{\mathbb{P}}_t[\RV_{t,t+h}] + \VRP_t$ (Bekaert-Hoerova decomposition) | \citet{BekaertHoerova2014} | | | Rearrangement of eq:vrp-theoretical |
| 38 | 312 | qualitative | BH2014: "The VRP component significantly predicts future equity returns" | \citet{BekaertHoerova2014} | | | |
| 39 | 313 | qualitative | BH2014: "The expected-variance component does not predict returns" | \citet{BekaertHoerova2014} | | | |
| 40 | 314 | qualitative | BH2014: "The expected-variance component predicts future realized volatility" | \citet{BekaertHoerova2014} | | | |
| 41 | 315-316 | qualitative | BH2014: "Different P-measure proxies (backward-looking RV, GARCH forecasts, HAR forecasts) yield materially different VRP estimates and different predictive power" | \citet{BekaertHoerova2014} | | | |
| 42 | 321-322 | attribution | Bollerslev and Todorov (2015) "decompose the VRP along a different dimension: the portion attributable to normal continuous fluctuations vs. the portion attributable to rare, large jumps (tail events)" | \citet{BollerslevTodorov2015} | | | |
| 43 | 325-326 | defining-formula | $\VRP_t = \VRP^{\text{diffusive}}_t + \VRP^{\text{tail}}_t$ (Bollerslev-Todorov decomposition) | \citet{BollerslevTodorov2015} | | | Verify this is the decomposition form used in the paper |
| 44 | 329 | qualitative | The diffusive VRP component "is relatively stable and modest" | \citet{BollerslevTodorov2015} | | | |
| 45 | 330-331 | qualitative | The tail VRP component "is highly time-varying and spikes during stress" | \citet{BollerslevTodorov2015} | | | |
| 46 | 334 | qualitative | BT2015: "the tail component drives most of the time-variation in the aggregate VRP" | \citet{BollerslevTodorov2015} | | | Key finding |
| 47 | 373-374 | defining-formula | Black-Scholes PDE: $\Theta + \frac{1}{2}\Gamma S^2 \sigma_i^2 = rV$ | [uncited] | | | Standard BS PDE; verify form is correct for delta-hedged context |
| 48 | 388-389 | defining-formula | Delta-hedged P&L per infinitesimal step: $d(\text{P\&L}) = \frac{1}{2}\Gamma S^2 (r_t^2 - \sigma_i^2 dt)$ | [uncited] | | | Standard result from options pricing theory |
| 49 | 399-400 | supporting-formula | Cumulative hedging P&L: $\text{Total P\&L} = \sum_{t=1}^{N} \frac{1}{2}\Gamma_t S_t^2 (\sigma_{r,t}^2 - \sigma_i^2) \Delta t$ | [uncited] | | | Discrete-time version of gamma P&L |
| 50 | 418-419 | supporting-formula | Simplified ATM gamma P&L: $\text{P\&L} \approx \frac{1}{2}\Gamma S^2 (\text{RV}^2 - \text{IV}^2) T$ | [uncited] | | | Constant-gamma approximation |
| 51 | 484-485 | numerical-fact | Figure caption states "VRP is positive roughly 85% of the time" | [uncited] | | | Consistent with Carr2009 claim (#56) |
| 52 | 498-499 | numerical-fact | Worked example: daily implied variance = (0.18)^2/252 = 0.0324/252 = 0.0001286 | [uncited] | | | Arithmetic: 0.0324/252 = 0.00012857... ~ 0.0001286. Check. |
| 53 | 512-518 | numerical-fact | Worked example: 5-day gamma P&L table (Day 1: r=+1.19%, r^2=1.423e-4, P&L=+0.028; Day 2: r=-1.39%, r^2=1.941e-4, P&L=+0.130; Day 3: r=+0.70%, r^2=0.489e-4, P&L=-0.161; Day 4: r=+1.58%, r^2=2.495e-4, P&L=+0.252; Day 5: r=-1.08%, r^2=1.173e-4, P&L=-0.023; cumulative=+0.227) | [uncited] | | | All log returns, squared returns, and P&L values need arithmetic verification |
| 54 | 524 | numerical-fact | Worked example: "annualized realized volatility over these 5 days was approximately 19.5%" | [uncited] | | | Verify: avg daily variance * 252, then sqrt |
| 55 | 525 | numerical-fact | Worked example: "$0.227 per share, or $22.70 per standard 100-share contract" | [uncited] | | | Arithmetic: 0.227 * 100 = 22.70. Check. |
| 56 | 573 | attribution | VVIX is "the model-free implied volatility of VIX, computed from VIX options using the same methodology as VIX itself" | \citep{CBOE2019} | | | Verify CBOE white paper confirms identical methodology |
| 57 | 575-576 | numerical-fact | VVIX "typical range: 80-120 in calm markets, spiking to 150+ during stress" | [uncited] | | | Verify typical VVIX range |
| 58 | 587-589 | defining-formula | VVIX single-term variance: $\sigma_j^2 = \frac{2}{T_j}\sum_{i}\frac{\Delta K_i}{K_i^2} e^{R_j T_j} Q_j(K_i) - \frac{1}{T_j}(\frac{F_j}{K_{0,j}} - 1)^2$ | \citep{CBOE2019} | | | Verify against CBOE VVIX white paper formula |
| 59 | 603-607 | defining-formula | VVIX interpolation: $\text{VVIX} = 100 \times \sqrt{[T_1 \sigma_1^2 \frac{N_{T_2}-N_{30}}{N_{T_2}-N_{T_1}} + T_2 \sigma_2^2 \frac{N_{30}-N_{T_1}}{N_{T_2}-N_{T_1}}] \times \frac{N_{365}}{N_{30}}}$ | \citep{CBOE2019} | | | Verify against CBOE VVIX white paper formula |
| 60 | 608 | numerical-fact | "$N_{30} = 43{,}200$ (minutes in 30 days), and $N_{365} = 525{,}600$ (minutes in 365 days)" | \citep{CBOE2019} | | | Arithmetic: 30*24*60=43200, 365*24*60=525600. Check. |
| 61 | 729 | numerical-fact | "VIX exceeds subsequent realized vol roughly 85% of the time" | \citet{Carr2009} | | | Verify exact percentage from Carr and Wu (2009) |
| 62 | 729-730 | qualitative | "The 15% of months where realized vol exceeds VIX are concentrated in sudden-onset crises, when realized vol spikes before the options market fully adjusts" | \citet{Carr2009} | | | Verify characterization of negative-VRP episodes |
