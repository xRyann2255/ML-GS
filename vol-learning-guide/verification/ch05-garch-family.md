# Chapter 5: The GARCH Family -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 51
**Verified:** 0/51
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 105 | attribution | Engle (1982) proposed the ARCH(q) model | \citet{Engle1982} | | | |
| 2 | 107-109 | defining-formula | ARCH(1): $\sigma^2_t = \omega + \alpha_1 r^2_{t-1}$ | \citet{Engle1982} | | | |
| 3 | 114 | qualitative | $\omega > 0$ ensures $\sigma^2_t$ stays positive even when $r_{t-1} = 0$ | [uncited] | | | Follows from model definition |
| 4 | 137-139 | defining-formula | ARCH(q): $\sigma^2_t = \omega + \sum_{i=1}^{q} \alpha_i r^2_{t-i}$ | \citet{Engle1982} | | | |
| 5 | 155 | qualitative | Capturing volatility persistence with ARCH requires many lags ($q = 10$ or more) | [uncited] | | | |
| 6 | 219 | attribution | Bollerslev (1986) introduced the GARCH(1,1) model | \citet{bollerslev1986} | | | |
| 7 | 221-223 | defining-formula | GARCH(1,1): $\sigma^2_t = \omega + \alpha r^2_{t-1} + \beta \sigma^2_{t-1}$ | \citet{bollerslev1986} | | | |
| 8 | 249 | numerical-fact | Typical $\alpha + \beta \approx 0.98$ for equity indices | [uncited] | | | Stated in projectconnection box |
| 9 | 256-257 | defining-formula | GARCH(1,1) is covariance-stationary if and only if $\alpha + \beta < 1$ | \citet{bollerslev1986} | | | Implicit citation from model definition |
| 10 | 259-261 | defining-formula | Unconditional (long-run) variance: $\bar{\sigma}^2 = \omega / (1 - \alpha - \beta)$ | [uncited] | | | Standard GARCH result |
| 11 | 270-272 | defining-formula | If $\alpha + \beta = 1$, the model becomes IGARCH: shocks never decay, unconditional variance undefined | \citep{engle1986} | | | |
| 12 | 270 | attribution | IGARCH attributed to Engle and Bollerslev (1986) | \citep{engle1986} | | | |
| 13 | 314-315 | supporting-formula | Worked example: $\sigma^2_t = 0.00001 + 0.000072 + 0.00036 = 0.000442$ (given $\omega=0.00001$, $\alpha=0.08$, $\beta=0.90$, $r_{t-1}=-0.03$, $\sigma^2_{t-1}=0.0004$) | [uncited] | | | Numerical check |
| 14 | 320 | supporting-formula | $\sigma_t = \sqrt{0.000442} \approx 0.0210 = 2.10\%$ | [uncited] | | | Numerical check |
| 15 | 324 | numerical-fact | The variance forecast increase from 0.0004 to 0.000442 is a 10.5% increase | [uncited] | | | Numerical check: $(0.000442 - 0.0004)/0.0004$ |
| 16 | 325 | numerical-fact | 81% of the forecast comes from the memory term $\beta \sigma^2_{t-1}$ | [uncited] | | | Numerical check: $0.00036/0.000442$ |
| 17 | 331-333 | supporting-formula | $\bar{\sigma}^2 = 0.00001/0.02 = 0.0005$, so $\bar{\sigma} \approx 2.24\%$ | [uncited] | | | Numerical check |
| 18 | 338 | numerical-fact | With $\alpha + \beta = 0.98$, it takes roughly $1/(1-0.98) = 50$ days for conditional variance to close half the gap to $\bar{\sigma}^2$ | [uncited] | | | Half-life claim; verify formula correctness |
| 19 | 344 | attribution | Hansen and Lunde (2005) compared 330 GARCH-type models on exchange rate and equity data | \citet{hansen2005forecast} | | | |
| 20 | 345 | qualitative | For exchange rates, no model significantly outperformed GARCH(1,1) | \citet{hansen2005forecast} | | | |
| 21 | 346 | qualitative | For equities, models with a leverage effect did better [than GARCH(1,1)] | \citet{hansen2005forecast} | | | |
| 22 | 347-348 | qualitative | Higher-order specifications like GARCH(2,1) or GARCH(1,2) provided negligible improvement | \citet{hansen2005forecast} | | | |
| 23 | 364-367 | attribution | Black (1976) documented the leverage asymmetry and proposed the debt-to-equity ratio explanation | \citet{Black1976} | | | |
| 24 | 365-367 | qualitative | When a stock drops, equity value falls while debt stays fixed, making equity riskier (leverage effect explanation) | \citet{Black1976} | | | |
| 25 | 427 | attribution | Glosten, Jagannathan, and Runkle (1993) proposed GJR-GARCH | \citet{gjr1993} | | | |
| 26 | 429-433 | defining-formula | GJR-GARCH: $\sigma^2_t = \omega + \alpha r^2_{t-1} + \gamma \mathbf{1}_{\{r_{t-1}<0\}} r^2_{t-1} + \beta \sigma^2_{t-1}$ | \citet{gjr1993} | | | |
| 27 | 446-449 | qualitative | After positive return, effective coefficient on $r^2_{t-1}$ is $\alpha$; after negative return, it is $\alpha + \gamma$ | [uncited] | | | Follows from GJR definition |
| 28 | 463 | numerical-fact | Adding an asymmetry term typically improves QLIKE by 5--15% | [uncited] | | | Stated in projectconnection; no citation |
| 29 | 474-476 | supporting-formula | GJR worked example Case A ($r_{t-1}=+0.03$): $\sigma^2_t = 0.00001 + 0.000036 + 0 + 0.00036 = 0.000406$ | [uncited] | | | Numerical check |
| 30 | 478 | supporting-formula | $\sigma_t = \sqrt{0.000406} \approx 2.01\%$ | [uncited] | | | Numerical check |
| 31 | 484-487 | supporting-formula | GJR worked example Case B ($r_{t-1}=-0.03$): $\sigma^2_t = 0.00001 + 0.000036 + 0.000072 + 0.00036 = 0.000478$ | [uncited] | | | Numerical check |
| 32 | 489 | supporting-formula | $\sigma_t = \sqrt{0.000478} \approx 2.19\%$ | [uncited] | | | Numerical check |
| 33 | 494 | numerical-fact | The 3% loss roughly doubles the news contribution to variance (from 0.000036 to 0.000108) | [uncited] | | | Numerical check: $0.000036 + 0.000072 = 0.000108$ |
| 34 | 498-501 | qualitative | GJR-GARCH most useful for equities where leverage effect is strong; for exchange rates, the effect is weaker and often statistically insignificant | \citep{hansen2005forecast} | | | |
| 35 | 510-511 | qualitative | GJR-GARCH requires parameter constraints ($\omega > 0$, $\alpha \geq 0$, $\alpha + \gamma \geq 0$, $\beta \geq 0$) to ensure $\sigma^2_t > 0$ | [uncited] | | | Standard result |
| 36 | 515 | attribution | Nelson (1991) proposed EGARCH | \citet{nelson1991} | | | |
| 37 | 515-516 | qualitative | EGARCH models the log of variance; since $\exp(\cdot)$ is always positive, variance is automatically positive regardless of parameter signs | \citet{nelson1991} | | | |
| 38 | 519-525 | defining-formula | EGARCH: $\ln \sigma^2_t = \omega + \beta \ln \sigma^2_{t-1} + \alpha(|r_{t-1}|/\sigma_{t-1} - \sqrt{2/\pi}) + \gamma \cdot r_{t-1}/\sigma_{t-1}$ | \citet{nelson1991} | | | |
| 39 | 531 | qualitative | $|\beta| < 1$ for stationarity in EGARCH | [uncited] | | | |
| 40 | 534 | numerical-fact | $\sqrt{2/\pi}$ is the expected value of $|z|$ when $z \sim N(0,1)$ | [uncited] | | | Mathematical fact |
| 41 | 562-564 | methodological | Multi-step forecasts from EGARCH require computing $E[\exp(\cdot)]$, which does not simplify cleanly; simulation-based forecasts used for horizons beyond one step | [uncited] | | | |
| 42 | 575-576 | qualitative | Volatility autocorrelations in financial data decay very slowly; autocorrelation is still positive at lag 100 | [uncited] | | | |
| 43 | 576 | qualitative | Standard GARCH(1,1) implies exponential decay of autocorrelations, which is too fast | [uncited] | | | |
| 44 | 586 | attribution | Baillie, Bollerslev, and Mikkelsen (1996) introduced FIGARCH | \citet{baillie1996} | | | |
| 45 | 606-609 | defining-formula | FIGARCH(1,d,1): $(1 - \beta L)\sigma^2_t = \omega + [1 - \beta L - (1 - \phi L)(1 - L)^d] r^2_t$ | \citet{baillie1996} | | | |
| 46 | 660-661 | numerical-fact | For $r^2_t$ as estimator of daily variance, the noise-to-signal ratio exceeds 5 on average | [uncited] | | | |
| 47 | 713 | attribution | Hansen, Huang, and Shek (2012) specified the Realized GARCH model | \citet{hansen2012realized} | | | |
| 48a | 717-718 | defining-formula | Realized GARCH return equation: $r_t = \sqrt{h_t} z_t$, $z_t \sim N(0,1)$ | \citet{hansen2012realized} | | | |
| 48b | 733-735 | defining-formula | Realized GARCH measurement equation: $\log RV_t = \xi + \delta \log h_t + \tau(z_t) + u_t$ | \citet{hansen2012realized} | | | |
| 48c | 751-752 | defining-formula | Realized GARCH GARCH equation: $\log h_{t+1} = \omega + \beta \log h_t + \gamma \log RV_t$ | \citet{hansen2012realized} | | | |
| 49a | 782-783 | qualitative | Realized GARCH with log-linear specification substantially outperforms standard GARCH(1,1) in both in-sample fit and out-of-sample forecasting on DJIA stocks | \citet{hansen2012realized} | | | |
| 49b | 784-785 | qualitative | Squared returns become statistically insignificant once a realized measure is included | \citet{hansen2012realized} | | | |
| 49c | 786 | qualitative | The leverage function $\tau(z_t)$ is highly significant in Realized GARCH | \citet{hansen2012realized} | | | |
| 50 | 796 | attribution | Shephard and Sheppard (2010) proposed the HEAVY model | \citet{shephard2010heavy} | | | |
| 51a | 805-806 | defining-formula | HEAVY return equation: $\sigma^2_{R,t} = \omega_R + \alpha_R RV_{t-1} + \beta_R \sigma^2_{R,t-1}$ | \citet{shephard2010heavy} | | | |
| 51b | 819-820 | defining-formula | HEAVY RV equation: $\mu_{M,t} = \omega_M + \alpha_M RV_{t-1} + \beta_M \mu_{M,t-1}$ | \citet{shephard2010heavy} | | | |
| 52a | 849 | qualitative | HEAVY model outperforms GARCH both in-sample and out-of-sample across a range of asset classes | \citet{shephard2010heavy} | | | |
| 52b | 850-851 | qualitative | HEAVY forecast gains are most pronounced at short horizons (one to five days) | \citet{shephard2010heavy} | | | |
| 52c | 851-853 | qualitative | HEAVY adjusts quickly to structural breaks because $RV_{t-1}$ responds immediately to intraday price variation | \citet{shephard2010heavy} | | | |
| 53 | 908-910 | qualitative | GARCH forecasts appear poor only when evaluated against noisy proxies like $r^2_t$; evaluated against $RV_t$, they perform respectably | \citet{andersen1998} | | | |
| 54 | 972 | qualitative | Engle's ARCH framework was Nobel Prize-winning | \citet{Engle1982} | | | Engle won 2003 Nobel; verify Prize was for ARCH specifically |
| 55 | 955 | qualitative | HAR often matches or beats Realized GARCH for RV forecasting | [uncited] | | | Stated in summary |
