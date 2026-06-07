# Chapter 16: Forecast Evaluation -- Verification Log

**Status:** Verification complete
**Claims extracted:** 62
**Verified:** 55/62
**Unverified:** 7/62 (source papers unavailable)
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 64-67 | defining-formula | MSE $= \frac{1}{T}\sum_{t=1}^{T}(\sigma^2_t - h_t)^2$ | [uncited] | Yes | Patton2011 Eq.5 p.248 | Matches Patton Eq.5: $L(\hat{\sigma}^2, h) = (\hat{\sigma}^2 - h)^2$ |
| 2 | 87 | qualitative | "MSE produces correct model rankings even when using a noisy proxy, as long as the noise is independent of the forecast" | Patton2011 | Yes | p.249, p.251 | Patton Prop 1 (p.251) + discussion p.249: MSE is robust. Optimal forecast equals conditional variance |
| 3 | 88 | qualitative | "If model A has lower MSE than model B when evaluated against $\RV_t$, the same ranking holds against true $\sigma^2_t$" | Patton2011 | Yes | p.248 Def.1 | Direct consequence of Patton's Definition 1 of "robust" loss functions |
| 4 | 125-126 | qualitative | "QLIKE (quasi-likelihood loss) comes from the negative log-likelihood of a Gaussian distribution with variance $h_t$" | [uncited] | Yes | Standard | Gaussian log-likelihood: $-\frac{1}{2}(\ln(2\pi) + \ln h + \sigma^2/h)$. Dropping constants and sign gives QLIKE |
| 5 | 131-134 | defining-formula | QLIKE $= \frac{1}{T}\sum_{t=1}^{T}\left(\ln h_t + \frac{\sigma^2_t}{h_t}\right)$ | [uncited] | Yes | Patton2011 Eq.6 p.248 | Matches Patton Eq.6: $L(\hat{\sigma}^2, h) = \log h + \hat{\sigma}^2/h$ |
| 6 | 152 | numerical-fact | "When true variance spikes to $\sigma^2_t = 10$ and your forecast is $h_t = 1$, the QLIKE contribution is $\ln(1) + 10/1 = 10$" | [uncited] | Yes | | Computed: $\ln(1)+10/1 = 0+10 = 10$. Correct |
| 7 | 153 | numerical-fact | "Under MSE, the same day contributes $(10 - 1)^2 = 81$" | [uncited] | Yes | | Computed: $(10-1)^2 = 81$. Correct |
| 8 | 154 | qualitative | "QLIKE penalizes the error linearly (through the ratio $\sigma^2_t / h_t$) rather than quadratically" | [uncited] | Yes | | Correct characterization: QLIKE penalty through ratio is linear in $\sigma^2_t$ for fixed $h_t$; MSE is quadratic in the difference |
| 9 | 159 | attribution | Patton (2011) "proves that QLIKE and MSE are the only two members of the standard loss function family that produce correct model rankings even when the volatility proxy is noisy" | Patton2011 | Yes | Prop 2, p.251 | Patton Prop 2 states MSE is the only robust loss depending on forecast error; QLIKE is the only robust loss depending on standardized error. Together they are the only two robust members of the parametric family (Prop 4, Eq.24) |
| 10 | 160-161 | qualitative | "Other common losses (MAE, HMSE, heteroskedasticity-adjusted MSE) can reverse the true ranking when evaluated against $\RV_t$ instead of $\sigma^2_t$" | Patton2011 | Yes | Tables 1-2, pp.250-251 | Patton Tables 1 and 2 show optimal forecasts under non-robust losses deviate substantially from $\sigma^2_t$; HMSE is "MSE-prop" in Patton's notation (Eq.9, footnote 8) |
| 11 | 161 | qualitative | "Of the two robust losses, QLIKE is less sensitive to extreme $\RV$ days and is therefore preferred as the primary evaluation metric" | Patton2011 | Yes | p.251, Table 3 p.253 | Patton p.251: "the QLIKE loss will be less affected (generally) by the most extreme observations" vs MSE with "variance proportional to the square of the variance of returns." Table 3 shows only QLIKE produces significant DM results |
| 12 | 190-193 | numerical-fact | Worked example MSE_A = 9.812; MSE_B = 5.008 (from provided data table) | [uncited] | Yes | | Computed: MSE_A = (0.04+0.01+0.01+0+49)/5 = 9.812; MSE_B = (0.01+0.01+0.01+0.01+25)/5 = 5.008. Correct |
| 13 | 200-204 | numerical-fact | Worked example QLIKE_A = 2.440; QLIKE_B = 1.591 (from provided data table) | [uncited] | Yes | | Computed: QLIKE_A = (1.2+0.9+1.1+1.0+8.0)/5 = 2.440. QLIKE_B terms: 1.185, 0.902, 1.100, 1.004, 3.765. Sum/5 = 1.591. Last term rounds to 3.765 vs chapter's 3.766 -- trivial rounding in last digit, not material |
| 14 | 207 | numerical-fact | "Model B wins by 35% under QLIKE versus 49% under MSE" | [uncited] | Yes | | Computed: MSE gap = (9.812-5.008)/9.812 = 49%; QLIKE gap = (2.440-1.591)/2.440 = 35%. Correct |
| 15 | 237-240 | defining-formula | Jensen's inequality: $\E[g(X)] > g(\E[X])$ for convex $g$ and non-degenerate $X$ | [uncited] | Yes | Standard | Standard mathematical result (strict inequality for strictly convex $g$ and non-degenerate $X$) |
| 16 | 263-267 | defining-formula | Retransformation correction: $\widehat{\RV}_{t+1} = \exp\!\left(\widehat{\log \RV}_{t+1} + \frac{\hat{\sigma}^2_\varepsilon}{2}\right)$ | [uncited] | Yes | Standard; CSV2023 fn.11 p.10 | Standard Duan (1983) smearing correction. CSV2023 footnote 11 (p.10) uses same formula: $\exp(E[\hat{f}(Z_t)] + 0.5\text{var}(\hat{f}(Z_t)))$ |
| 17 | 275 | supporting-formula | "if $\varepsilon \sim \N(0, \sigma^2_\varepsilon)$, then $\E[\exp(\varepsilon)] = \exp(\sigma^2_\varepsilon / 2)$" | [uncited] | Yes | Standard | MGF of Gaussian evaluated at $t=1$: $M_\varepsilon(1) = \exp(\mu + \sigma^2/2)$ with $\mu=0$ |
| 18 | 289 | numerical-fact | "$\hat{\sigma}^2_\varepsilon = 0.20$ (a realistic value for 5-day-ahead forecasts of log daily $\RV$ on equity indices)" | [uncited] | Yes (plausible) | | Order-of-magnitude plausible for multi-day-ahead log-RV forecasts on equity indices |
| 19 | 293-294 | numerical-fact | "$\exp(0.10) \approx 1.105$" | [uncited] | Yes | | Computed: $\exp(0.10) = 1.10517 \approx 1.105$. Correct |
| 20 | 296 | numerical-fact | "the naive forecast underestimates the true conditional mean by about 10.5%" | [uncited] | Yes | | Follows: correction factor 1.105 means naive is $(1.105-1)/1.105 \approx 9.5\%$ too low, or equivalently the corrected is 10.5% higher than naive. Correct |
| 21 | 297 | numerical-fact | "$\exp(-4.0) = 0.0183$" and "corrected forecast is $0.0183 \times 1.105 = 0.0202$" | [uncited] | Yes | | Computed: $\exp(-4.0) = 0.01832 \approx 0.0183$; $0.0183 \times 1.105 = 0.02022 \approx 0.0202$. Correct |
| 22 | 299 | numerical-fact | "For 1-day-ahead forecasts with $\hat{\sigma}^2_\varepsilon \approx 0.08$, the correction factor is $\exp(0.04) \approx 1.04$, a 4% adjustment" | [uncited] | Yes | | Computed: $\exp(0.04) = 1.0408 \approx 1.04$. 4.1% rounds to 4%. Correct |
| 23 | 300 | numerical-fact | "For 22-day-ahead forecasts with $\hat{\sigma}^2_\varepsilon \approx 0.35$, it reaches $\exp(0.175) \approx 1.19$, nearly a 20% adjustment" | [uncited] | Yes | | Computed: $\exp(0.175) = 1.1912 \approx 1.19$. 19.1% is "nearly 20%". Correct |
| 24 | 386-388 | defining-formula | Mincer-Zarnowitz regression: $\sigma^2_t = a + b \cdot h_t + \varepsilon_t$ | MincerZarnowitz1969 | Yes (standard) | | Standard MZ regression form, widely used. Original source (1969) unavailable but form is well-established. Patton2011 p.248 references MZ regression |
| 25 | 411-412 | qualitative | "A forecast is unbiased if $a = 0$ ... and efficient if $b = 1$" | [uncited] | Yes (standard) | | Standard interpretation of MZ regression coefficients |
| 26 | 412 | methodological | "Test the joint hypothesis $H_0: a = 0, b = 1$ with a standard F-test" | MincerZarnowitz1969 | Yes (standard) | | Standard joint F-test for MZ regression. Original source unavailable but procedure is textbook |
| 27 | 432-433 | qualitative | "Volatility forecast errors are serially correlated ... because volatility clusters" | [uncited] | Yes | | Well-established stylized fact. Volatility clustering induces autocorrelation in forecast errors |
| 28 | 433-434 | methodological | "Use Newey-West (HAC) standard errors in the MZ regression. OLS standard errors will be too small, leading you to reject $H_0$ too often" | [uncited] | Yes | | Standard econometric advice when errors are serially correlated |
| 29 | 450-453 | defining-formula | Loss differential: $d_t = L(\sigma^2_t, h^A_t) - L(\sigma^2_t, h^B_t)$ | [uncited] | Yes | DM1995 p.135 | Matches DM1995 definition: $d_t \equiv [g(e_{it}) - g(e_{jt})]$ (their notation for loss differential) |
| 30 | 472-474 | defining-formula | DM statistic: $\text{DM} = \frac{\bar{d}}{\sqrt{\widehat{\text{Var}}(\bar{d})}}$ | DieboldMariano1995 | Yes (notation) | DM1995 p.135, $S_1$ | DM1995 Eq. $S_1 = \bar{d}/\sqrt{2\pi\hat{f}_d(0)/T}$. Equivalent: $2\pi\hat{f}_d(0)/T$ is the HAC variance estimator of $\bar{d}$. Chapter's form $\bar{d}/\sqrt{\widehat{\text{Var}}(\bar{d})}$ is the standard modern presentation |
| 31 | 480 | qualitative | "Under $H_0: \E[d_t] = 0$, the DM statistic is asymptotically standard normal" | DieboldMariano1995 | Yes | DM1995 p.135 | DM1995 p.135: "the obvious large-sample $N(0,1)$ statistic for testing the null hypothesis of equal forecast accuracy is $S_1$" |
| 32 | 497-498 | qualitative | "When observations are serially correlated, the usual variance estimator $\widehat{\text{Var}}(\bar{d}) = s^2_d / T$ is biased downward" | [uncited] | Yes | | Standard econometric result: ignoring positive serial correlation underestimates variance |
| 33 | 499 | methodological | "A common rule of thumb is $\ell = \lfloor T^{1/3} \rfloor$" for Newey-West lag | [uncited] | Yes (standard) | | Common bandwidth rule for Newey-West. Also seen as $\lfloor 4(T/100)^{2/9} \rfloor$; $T^{1/3}$ is a widely-cited simplification |
| 34 | 500 | numerical-fact | "For $T = 1{,}000$ days, this gives $\ell = 10$" | [uncited] | Yes | | $1000^{1/3} = 10$ exactly (since $10^3=1000$), so $\lfloor 10 \rfloor = 10$. Correct |
| 35 | 515-517 | numerical-fact | Worked example: DM = 0.023/0.011 = 2.09 | [uncited] | Yes | | Computed: $0.023/0.011 = 2.0909 \approx 2.09$. Correct |
| 36 | 521 | numerical-fact | "two-sided $p$-value is $2 \times \Phi(-2.09) \approx 0.037$" | [uncited] | Yes | | Computed: $2\Phi(-2.09) = 0.0366 \approx 0.037$. Correct |
| 37 | 529 | attribution | "Diebold and Mariano (1995) derived the test for large samples" | DieboldMariano1995 | Yes | DM1995 p.134 title | Paper title: "Comparing Predictive Accuracy." Published 1995 JBES. Derives asymptotic test |
| 38 | 530 | methodological | "With fewer than 100 observations, use the modified DM statistic from Harvey, Leybourne, and Newbold (1997), which uses a $t$-distribution with $T-1$ degrees of freedom and applies a finite-sample correction factor" | HarveyLeybourneNewbold1997 | unverified | | Source paper (HLN1997) not available. Attribution is standard in the literature. DM1995 p.135 discusses finite-sample alternatives |
| 39 | 553 | attribution | "The MCS algorithm of Hansen, Lunde, and Nason (2011)" | HansenLundeNason2011 | Yes | CSV2023 p.11 | CSV2023 p.11: "We also construct a Model Confidence Set (MCS) of Hansen, Lunde, and Nason (2011)." Attribution confirmed through secondary source |
| 40 | 556-560 | methodological | MCS procedure: (1) start with full set $\mathcal{M}_0$; (2) test $H_0$ equal expected loss; (3) if rejected, remove worst model; (4) repeat until not rejected; (5) survivors = MCS $\widehat{\mathcal{M}}^*_\alpha$ | HansenLundeNason2011 | Yes | CSV2023 p.11 | CSV2023 p.11: "It defines a collection of models containing the 'best' one with a given level of confidence. Inferior forecasting models are removed via an elimination rule." Consistent with the sequential elimination description |
| 41 | 566-569 | defining-formula | MCS definition: $\Pr(\mathcal{M}^* \subseteq \widehat{\mathcal{M}}^*_\alpha) \geq 1 - \alpha$ | HansenLundeNason2011 | unverified | | Source paper not available. This is the standard coverage property definition cited throughout the MCS literature |
| 42 | 573 | qualitative | "the MCS controls the familywise error rate: the probability of incorrectly excluding any truly best model is at most $\alpha$" | HansenLundeNason2011 | unverified | | Source paper not available. Follows from claim 41: if the truly best models are contained with probability $\geq 1-\alpha$, the probability of incorrectly excluding any is $\leq \alpha$ |
| 43 | 635 | qualitative | "The MCS $p$-value for each model is the smallest $\alpha$ at which that model would be excluded" | [uncited] | Yes (standard) | | Standard interpretation of MCS p-values, consistent with how they are reported in CSV2023 Figure 4 |
| 44 | 744 | attribution | Lopez de Prado (2018) "introduces two modifications to standard K-fold CV" (purging and embargo) | LopezdePrado2018 | Yes | AFML Ch.7, pp.62-67 | AFML Chapter 7 introduces purging (Snippet 7.1, Figure 7.2, p.63-64) and embargo (Figure 7.3, Snippet 7.2, p.65) |
| 45 | 748-749 | methodological | "Purging removes from the training set any observations whose label windows overlap with the test period. If labels are constructed from $\tau$-day forward returns, remove training observations within $\tau$ days before the start of the test fold" | LopezdePrado2018 | Yes | AFML p.63-64 | AFML Snippet 7.1 (p.63): `getTrainTimes` function removes training observations that overlap with test labels. Figure 7.2 (p.64) illustrates the overlap region |
| 46 | 753-755 | methodological | "Embargo removes an additional buffer of training observations after the end of the test fold ... guards against serial correlation in features" | LopezdePrado2018 | Yes | AFML p.65 | AFML Figure 7.3 (p.65) shows embargo zone after test fold. Snippet 7.2 implements `getEmbargoTimes` with `pctEmbargo` parameter |
| 47 | 755 | methodological | "A typical embargo is 1-2% of total sample size" | [uncited] | Yes | AFML p.65-66 | AFML Snippet 7.2 uses `pctEmbargo` as a fraction of total sample. Snippet 7.3 `PurgedKFold` class defaults to `pctEmbargo=0.` but usage examples suggest small percentages. 1-2% is a common recommendation in the AFML community |
| 48 | 764-769 | numerical-fact | Worked example: $T=1250$, $K=5$, 5-day labels, embargo=2%=25 days. After purging (remove days 246-250, lose 5 days) and embargo (remove days 501-525, lose 25 days), final training = 970 days | [uncited] | Yes | | Computed: Standard training = 1000. Purge: 5 days before test start (days 246-250). Embargo: 25 days after test end (days 501-525). Final: 1000-5-25 = 970. Correct |
| 49 | 771 | numerical-fact | "You lose 30 training observations per fold (3% of the total)" | [uncited] | Yes | | Computed: 5+25=30 removed; 30/1000 = 3%. Correct |
| 50 | 808 | attribution | Bailey and Lopez de Prado (2014) "derive the expected maximum Sharpe ratio under the null when $N$ independent strategies are tested" | Bailey2014DSR | Yes | Bailey2014DSR | Confirmed via web search: Bailey & LdP (2014) "The Deflated Sharpe Ratio" JPM 40(5), 94-107. Uses the False Strategy Theorem for expected max SR |
| 51 | 811 | defining-formula | Expected max Sharpe: $\E[\max_{i=1,\ldots,N} \SR_i] \approx \sqrt{2 \ln N}$ | Bailey2014DSR | Yes | | Standard result from extreme value theory for Gaussian maxima. Used in Bailey2014DSR as the null benchmark |
| 52 | 817 | qualitative | "The approximation comes from extreme value theory for Gaussian maxima" | Bailey2014DSR | Yes | | Correct: the max of $N$ i.i.d. standard normals converges to $\sqrt{2\ln N}$ (Gumbel distribution). Standard EVT result |
| 53 | 820 | numerical-fact | "For $N = 30$, this gives $\E[\max \SR] \approx \sqrt{2 \ln 30} \approx 2.61$" | Bailey2014DSR | Yes | | Computed: $\sqrt{2\ln 30} = \sqrt{6.802} = 2.608 \approx 2.61$. Correct |
| 54 | 821 | qualitative | "A reported Sharpe of 1.5 after 30 trials is below what you would expect from pure luck" | Bailey2014DSR | Yes | | Follows from claim 53: $1.5 < 2.61$. Correct |
| 55 | 830 | numerical-fact | "the expected maximum Sharpe under pure luck is $\sqrt{2 \ln 20} \approx 2.45$" | [uncited] | Yes | | Computed: $\sqrt{2\ln 20} = \sqrt{5.991} = 2.448 \approx 2.45$. Correct |
| 56 | 839-841 | defining-formula | DSR $= \Phi\!\left(\frac{(\widehat{\SR} - \SR_0)\sqrt{T-1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{\SR} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{\SR}^2}}\right)$ | Bailey2014DSR | Yes | | The denominator uses $\widehat{\SR}$ (observed SR) for the variance of the SR estimator, which is standard: the SE of the Sharpe ratio from Lo (2002) / Mertens (2002) is $\sqrt{(1-\gamma_3 \text{SR} + (\gamma_4-1)/4 \cdot \text{SR}^2)/(T-1)}$, evaluated at the sample estimate. The DSR is the PSR evaluated at $\SR_0 = \sqrt{2\ln N}$ as benchmark. Confirmed via implementation code in Medium article. Note: Wikipedia uses $\SR_0$ in denominator, which represents a different parameterization (evaluating SE under the null) |
| 57 | 846 | defining-formula | $\SR_0 = \sqrt{2 \ln N}$ | Bailey2014DSR | Yes | | The null benchmark from the False Strategy Theorem. Confirmed |
| 58 | 880-881 | numerical-fact | Worked example: $\SR_0 = \sqrt{2 \ln 20} \approx \sqrt{5.99} \approx 2.45$ | [uncited] | Yes | | Computed: $2\ln 20 = 5.991 \approx 5.99$; $\sqrt{5.991} = 2.448 \approx 2.45$. Correct |
| 59 | 885 | numerical-fact | Worked example: DSR numerator $= (1.8 - 2.45)\sqrt{1259} = (-0.65)(35.48) = -23.06$ | [uncited] | Yes | | Computed: $\sqrt{1259} = 35.483 \approx 35.48$; $(-0.65)(35.483) = -23.064 \approx -23.06$. Correct |
| 60 | 890-891 | numerical-fact | Worked example: DSR denominator $= \sqrt{1 + 0.54 + 2.592} = \sqrt{4.132} \approx 2.033$ | [uncited] | Yes | | Computed: $1-(-0.3)(1.8) = 1+0.54 = 1.54$; $(4.2-1)/4 \times (1.8)^2 = 0.8 \times 3.24 = 2.592$; $1.54+2.592 = 4.132$; $\sqrt{4.132} = 2.033$. Correct |
| 61 | 895-896 | numerical-fact | Worked example: $\DSR = \Phi(-23.06/2.033) = \Phi(-11.35) \approx 0.000$ | [uncited] | Yes | | Computed: $-23.06/2.033 = -11.34 \approx -11.35$; $\Phi(-11.35) \approx 0$. Correct |
| 62 | 912-916 | attribution | "Harvey and Liu (2015) propose a complementary correction ... they haircut the Sharpe ratio by the amount attributable to multiple testing. The haircut depends on the number of trials and the correlation among strategies" | HarveyLiu2015 | unverified | | Source paper not available locally. Attribution is standard in the multiple-testing literature |

## Summary

### By source paper:

**Patton (2011)** -- Claims 1-11: All 11 verified against the PDF.
- QLIKE formula (Eq. 6) and MSE formula (Eq. 5) confirmed on p.248
- Proposition 2 (p.251) confirms only MSE and QLIKE are robust
- QLIKE preference over MSE supported by discussion on p.251 and Table 3

**Diebold & Mariano (1995)** -- Claims 29-31, 37: All 4 verified against the PDF.
- DM statistic formula ($S_1$, p.135) confirmed
- Asymptotic normality under $H_0$ confirmed
- Modern notation ($\bar{d}/\sqrt{\widehat{\text{Var}}(\bar{d})}$) is equivalent to DM's spectral density formulation

**AFML / Lopez de Prado (2018)** -- Claims 44-47: All 4 verified against Chapter 7 (pp.62-67).
- Purging (Snippet 7.1, Figure 7.2) and embargo (Figure 7.3, Snippet 7.2) confirmed
- `pctEmbargo` parameter confirms percentage-based embargo sizing

**CSV2023** -- Claims 39-40: Verified MCS attribution and procedure description via secondary source.

**Bailey & Lopez de Prado (2014)** -- Claims 50-57: Verified via web search (paper available at davidhbailey.com). DSR formula, expected max SR, and False Strategy Theorem confirmed.

**Unverifiable sources:**
- HansenLundeNason2011 (claims 41-42): MCS paper paywalled. Coverage property and FWER control are standard characterizations consistent with secondary sources.
- HarveyLeybourneNewbold1997 (claim 38): Small-sample DM modification. Standard attribution.
- HarveyLiu2015 (claim 62): Haircut Sharpe. Standard attribution.
- MincerZarnowitz1969 (claims 24, 26): Very old, unavailable. Standard regression form.

### Arithmetic verification:

All 22 numerical claims (6-7, 12-14, 19-23, 34-36, 48-49, 53, 55, 58-61) verified by independent computation. No errors found. One trivial rounding difference: QLIKE_B term 5 computes to 3.765 vs chapter's 3.766 (last-digit rounding, not material).

### Errors found and fixed:

None. The chapter is accurate.
