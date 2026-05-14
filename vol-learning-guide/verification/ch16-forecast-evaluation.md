# Chapter 16: Forecast Evaluation -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 62
**Verified:** 0/62
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 64-67 | defining-formula | MSE $= \frac{1}{T}\sum_{t=1}^{T}(\sigma^2_t - h_t)^2$ | [uncited] | | | Standard definition |
| 2 | 87 | qualitative | "MSE produces correct model rankings even when using a noisy proxy, as long as the noise is independent of the forecast" | Patton2011 | | | Robustness to noise in proxy |
| 3 | 88 | qualitative | "If model A has lower MSE than model B when evaluated against $\RV_t$, the same ranking holds against true $\sigma^2_t$" | Patton2011 | | | Consequence of proxy robustness |
| 4 | 125-126 | qualitative | "QLIKE (quasi-likelihood loss) comes from the negative log-likelihood of a Gaussian distribution with variance $h_t$" | [uncited] | | | Origin of QLIKE |
| 5 | 131-134 | defining-formula | QLIKE $= \frac{1}{T}\sum_{t=1}^{T}\left(\ln h_t + \frac{\sigma^2_t}{h_t}\right)$ | [uncited] | | | Core QLIKE formula |
| 6 | 152 | numerical-fact | "When true variance spikes to $\sigma^2_t = 10$ and your forecast is $h_t = 1$, the QLIKE contribution is $\ln(1) + 10/1 = 10$" | [uncited] | | | Numerical example |
| 7 | 153 | numerical-fact | "Under MSE, the same day contributes $(10 - 1)^2 = 81$" | [uncited] | | | Numerical example |
| 8 | 154 | qualitative | "QLIKE penalizes the error linearly (through the ratio $\sigma^2_t / h_t$) rather than quadratically" | [uncited] | | | Characterization of QLIKE penalty |
| 9 | 159 | attribution | Patton (2011) "proves that QLIKE and MSE are the only two members of the standard loss function family that produce correct model rankings even when the volatility proxy is noisy" | Patton2011 | | | Key result: only two robust losses |
| 10 | 160-161 | qualitative | "Other common losses (MAE, HMSE, heteroskedasticity-adjusted MSE) can reverse the true ranking when evaluated against $\RV_t$ instead of $\sigma^2_t$" | Patton2011 | | | Non-robust losses named |
| 11 | 161 | qualitative | "Of the two robust losses, QLIKE is less sensitive to extreme $\RV$ days and is therefore preferred as the primary evaluation metric" | Patton2011 | | | QLIKE preference justification |
| 12 | 190-193 | numerical-fact | Worked example MSE_A = 9.812; MSE_B = 5.008 (from provided data table) | [uncited] | | | Verify arithmetic |
| 13 | 200-204 | numerical-fact | Worked example QLIKE_A = 2.440; QLIKE_B = 1.591 (from provided data table) | [uncited] | | | Verify arithmetic; intermediate QLIKE_B terms: 1.185, 0.902, 1.100, 1.004, 3.766 |
| 14 | 207 | numerical-fact | "Model B wins by 35% under QLIKE versus 49% under MSE" | [uncited] | | | Verify percentages from computed values |
| 15 | 237-240 | defining-formula | Jensen's inequality: $\E[g(X)] > g(\E[X])$ for convex $g$ and non-degenerate $X$ | [uncited] | | | Standard mathematical result |
| 16 | 263-267 | defining-formula | Retransformation correction: $\widehat{\RV}_{t+1} = \exp\!\left(\widehat{\log \RV}_{t+1} + \frac{\hat{\sigma}^2_\varepsilon}{2}\right)$ | [uncited] | | | Bias correction formula |
| 17 | 275 | supporting-formula | "if $\varepsilon \sim \N(0, \sigma^2_\varepsilon)$, then $\E[\exp(\varepsilon)] = \exp(\sigma^2_\varepsilon / 2)$" | [uncited] | | | MGF of Gaussian, justifies correction |
| 18 | 289 | numerical-fact | "$\hat{\sigma}^2_\varepsilon = 0.20$ (a realistic value for 5-day-ahead forecasts of log daily $\RV$ on equity indices)" | [uncited] | | | Claimed typical value |
| 19 | 293-294 | numerical-fact | "$\exp(0.10) \approx 1.105$" | [uncited] | | | Verify arithmetic |
| 20 | 296 | numerical-fact | "the naive forecast underestimates the true conditional mean by about 10.5%" | [uncited] | | | Follows from claim 19 |
| 21 | 297 | numerical-fact | "$\exp(-4.0) = 0.0183$" and "corrected forecast is $0.0183 \times 1.105 = 0.0202$" | [uncited] | | | Verify arithmetic |
| 22 | 299 | numerical-fact | "For 1-day-ahead forecasts with $\hat{\sigma}^2_\varepsilon \approx 0.08$, the correction factor is $\exp(0.04) \approx 1.04$, a 4% adjustment" | [uncited] | | | Verify arithmetic and claimed typical value |
| 23 | 300 | numerical-fact | "For 22-day-ahead forecasts with $\hat{\sigma}^2_\varepsilon \approx 0.35$, it reaches $\exp(0.175) \approx 1.19$, nearly a 20% adjustment" | [uncited] | | | Verify arithmetic and claimed typical value |
| 24 | 386-388 | defining-formula | Mincer-Zarnowitz regression: $\sigma^2_t = a + b \cdot h_t + \varepsilon_t$ | MincerZarnowitz1969 | | | Standard MZ regression |
| 25 | 411-412 | qualitative | "A forecast is unbiased if $a = 0$ ... and efficient if $b = 1$" | [uncited] | | | MZ interpretation |
| 26 | 412 | methodological | "Test the joint hypothesis $H_0: a = 0, b = 1$ with a standard F-test" | MincerZarnowitz1969 | | | Testing procedure |
| 27 | 432-433 | qualitative | "Volatility forecast errors are serially correlated ... because volatility clusters" | [uncited] | | | Justification for HAC |
| 28 | 433-434 | methodological | "Use Newey-West (HAC) standard errors in the MZ regression. OLS standard errors will be too small, leading you to reject $H_0$ too often" | [uncited] | | | HAC recommendation |
| 29 | 450-453 | defining-formula | Loss differential: $d_t = L(\sigma^2_t, h^A_t) - L(\sigma^2_t, h^B_t)$ | [uncited] | | | DM test setup |
| 30 | 472-474 | defining-formula | DM statistic: $\text{DM} = \frac{\bar{d}}{\sqrt{\widehat{\text{Var}}(\bar{d})}}$ | DieboldMariano1995 | | | Core DM formula |
| 31 | 480 | qualitative | "Under $H_0: \E[d_t] = 0$, the DM statistic is asymptotically standard normal" | DieboldMariano1995 | | | Asymptotic distribution |
| 32 | 497-498 | qualitative | "When observations are serially correlated, the usual variance estimator $\widehat{\text{Var}}(\bar{d}) = s^2_d / T$ is biased downward" | [uncited] | | | Motivates HAC |
| 33 | 499 | methodological | "A common rule of thumb is $\ell = \lfloor T^{1/3} \rfloor$" for Newey-West lag | [uncited] | | | Bandwidth selection rule |
| 34 | 500 | numerical-fact | "For $T = 1{,}000$ days, this gives $\ell = 10$" | [uncited] | | | Verify: floor(1000^(1/3)) = floor(10) = 10 |
| 35 | 515-517 | numerical-fact | Worked example: DM = 0.023/0.011 = 2.09 | [uncited] | | | Verify arithmetic |
| 36 | 521 | numerical-fact | "two-sided $p$-value is $2 \times \Phi(-2.09) \approx 0.037$" | [uncited] | | | Verify p-value |
| 37 | 529 | attribution | "Diebold and Mariano (1995) derived the test for large samples" | DieboldMariano1995 | | | Attribution |
| 38 | 530 | methodological | "With fewer than 100 observations, use the modified DM statistic from Harvey, Leybourne, and Newbold (1997), which uses a $t$-distribution with $T-1$ degrees of freedom and applies a finite-sample correction factor" | HarveyLeybourneNewbold1997 | | | Small-sample modification |
| 39 | 553 | attribution | "The MCS algorithm of Hansen, Lunde, and Nason (2011)" | HansenLundeNason2011 | | | Attribution |
| 40 | 556-560 | methodological | MCS procedure: (1) start with full set $\mathcal{M}_0$; (2) test $H_0$ equal expected loss; (3) if rejected, remove worst model; (4) repeat until not rejected; (5) survivors = MCS $\widehat{\mathcal{M}}^*_\alpha$ | HansenLundeNason2011 | | | Algorithmic description |
| 41 | 566-569 | defining-formula | MCS definition: $\Pr(\mathcal{M}^* \subseteq \widehat{\mathcal{M}}^*_\alpha) \geq 1 - \alpha$ | HansenLundeNason2011 | | | Formal coverage property |
| 42 | 573 | qualitative | "the MCS controls the familywise error rate: the probability of incorrectly excluding any truly best model is at most $\alpha$" | HansenLundeNason2011 | | | FWER control |
| 43 | 635 | qualitative | "The MCS $p$-value for each model is the smallest $\alpha$ at which that model would be excluded" | [uncited] | | | Interpretation of MCS p-value |
| 44 | 744 | attribution | Lopez de Prado (2018) "introduces two modifications to standard K-fold CV" (purging and embargo) | LopezdePrado2018 | | | Attribution of purging and embargo |
| 45 | 748-749 | methodological | "Purging removes from the training set any observations whose label windows overlap with the test period. If labels are constructed from $\tau$-day forward returns, remove training observations within $\tau$ days before the start of the test fold" | LopezdePrado2018 | | | Purging definition |
| 46 | 753-755 | methodological | "Embargo removes an additional buffer of training observations after the end of the test fold ... guards against serial correlation in features" | LopezdePrado2018 | | | Embargo definition |
| 47 | 755 | methodological | "A typical embargo is 1-2% of total sample size" | [uncited] | | | Embargo size recommendation |
| 48 | 764-769 | numerical-fact | Worked example: $T=1250$, $K=5$, 5-day labels, embargo=2%=25 days. After purging (remove days 246-250, lose 5 days) and embargo (remove days 501-525, lose 25 days), final training = 970 days | [uncited] | | | Verify arithmetic: 1000 - 5 - 25 = 970 |
| 49 | 771 | numerical-fact | "You lose 30 training observations per fold (3% of the total)" | [uncited] | | | Verify: 30/1000 = 3% |
| 50 | 808 | attribution | Bailey and Lopez de Prado (2014) "derive the expected maximum Sharpe ratio under the null when $N$ independent strategies are tested" | Bailey2014DSR | | | Attribution |
| 51 | 811 | defining-formula | Expected max Sharpe: $\E[\max_{i=1,\ldots,N} \SR_i] \approx \sqrt{2 \ln N}$ | Bailey2014DSR | | | Key formula |
| 52 | 817 | qualitative | "The approximation comes from extreme value theory for Gaussian maxima" | Bailey2014DSR | | | Justification for formula |
| 53 | 820 | numerical-fact | "For $N = 30$, this gives $\E[\max \SR] \approx \sqrt{2 \ln 30} \approx 2.61$" | Bailey2014DSR | | | Verify: sqrt(2*ln(30)) = sqrt(2*3.401) = sqrt(6.802) ~ 2.608 |
| 54 | 821 | qualitative | "A reported Sharpe of 1.5 after 30 trials is below what you would expect from pure luck" | Bailey2014DSR | | | Follows from claim 53 |
| 55 | 830 | numerical-fact | "the expected maximum Sharpe under pure luck is $\sqrt{2 \ln 20} \approx 2.45$" | [uncited] | | | Verify: sqrt(2*ln(20)) = sqrt(2*2.996) = sqrt(5.991) ~ 2.448 |
| 56 | 839-841 | defining-formula | DSR $= \Phi\!\left(\frac{(\widehat{\SR} - \SR_0)\sqrt{T-1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{\SR} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{\SR}^2}}\right)$ | Bailey2014DSR | | | Core DSR formula |
| 57 | 846 | defining-formula | $\SR_0 = \sqrt{2 \ln N}$ | Bailey2014DSR | | | Null benchmark for DSR |
| 58 | 880-881 | numerical-fact | Worked example: $\SR_0 = \sqrt{2 \ln 20} \approx \sqrt{5.99} \approx 2.45$ | [uncited] | | | Verify arithmetic |
| 59 | 885 | numerical-fact | Worked example: DSR numerator $= (1.8 - 2.45)\sqrt{1259} = (-0.65)(35.48) = -23.06$ | [uncited] | | | Verify: sqrt(1259)=35.48, product=-23.06 |
| 60 | 890-891 | numerical-fact | Worked example: DSR denominator $= \sqrt{1 + 0.54 + 2.592} = \sqrt{4.132} \approx 2.033$ | [uncited] | | | Verify: 1-(-0.3)(1.8)=1.54, (4.2-1)/4*(1.8)^2=2.592, sum=4.132 |
| 61 | 895-896 | numerical-fact | Worked example: $\DSR = \Phi(-23.06/2.033) = \Phi(-11.35) \approx 0.000$ | [uncited] | | | Verify division and CDF value |
| 62 | 912-916 | attribution | "Harvey and Liu (2015) propose a complementary correction ... they haircut the Sharpe ratio by the amount attributable to multiple testing. The haircut depends on the number of trials and the correlation among strategies" | HarveyLiu2015 | | | Attribution and description of Haircut Sharpe |
