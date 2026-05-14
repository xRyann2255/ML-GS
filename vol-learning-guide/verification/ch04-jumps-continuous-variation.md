# Chapter 4: Jumps and Continuous Variation -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 50
**Verified:** 0/50
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 51 | defining-formula | Jump-diffusion log-price process: $dp_t = \mu_t\,dt + \sigma_t\,dW_t + J_t\,dN_t$ | [uncited] | | | Standard textbook form; prereq box |
| 2 | 57 | defining-formula | Quadratic variation decomposition: $[p]_t = \int_{t-1}^{t}\sigma^2_s\,ds + \sum_{s\in(t-1,t]} J^2_s$ | [uncited] | | | Continuous + jump components |
| 3 | 35 | numerical-fact | "The May 6, 2010 flash crash sent the Dow down nearly 1,000 points (roughly 9%) in minutes before recovering" | [uncited] | | | Historical event claim |
| 4 | 36 | numerical-fact | "The Swiss National Bank abandoned its EUR/CHF floor on January 15, 2015. EUR/CHF dropped roughly 30% in seconds" | [uncited] | | | Historical event claim |
| 5 | 161 | attribution | Bipower variation key idea "due to \citet{BNS2004}" | BNS2004 | | | Attribution of BPV |
| 6 | 176 | defining-formula | Bipower variation: $\BPV_t = \frac{\pi}{2}\sum_{i=2}^{n}\lvert r_{t,i}\rvert\,\lvert r_{t,i-1}\rvert$ | BNS2004 | | | Core BPV formula |
| 7 | 184 | supporting-formula | Scaling constant rationale: $\frac{\pi}{2} \approx 1.5708$ corrects for $\E[\lvert Z\rvert] = \sqrt{2/\pi}$ when $Z \sim \N(0,1)$ | [uncited] | | | Standard result |
| 8 | 198 | supporting-formula | $\E[\lvert Z\rvert] = \sqrt{2/\pi} \approx 0.7979$ for $Z \sim \N(0,1)$ | [uncited] | | | Folded normal mean |
| 9 | 200 | supporting-formula | $\E[\lvert Z\rvert]^2 = 2/\pi$ and $\E[Z^2] = 1$ | [uncited] | | | Consequence of claim 8 |
| 10 | 213 | supporting-formula | $\E[\lvert r_{t,i}\rvert\,\lvert r_{t,i-1}\rvert] \approx \sigma_{t,i}\,\sigma_{t,i-1}\cdot\frac{2}{\pi}$ | [uncited] | | | Derivation of BPV bias factor |
| 11 | 221 | qualitative | BPV consistency: $\BPV_t \xrightarrow{p} \IVol_t = \int_{t-1}^{t}\sigma^2_s\,ds$ as $n \to \infty$, even with finite-activity jumps | BNS2004 | | | Key convergence result |
| 12 | 225 | qualitative | "$\RV_t$ converges to integrated variance plus the sum of squared jumps" (in contrast to BPV) | [uncited] | | | Implied by BNS2004 |
| 13 | 406 | attribution | "\citet{BNS2006} proposed the following test" (BNS jump test) | BNS2006 | | | Attribution of jump test |
| 14 | 414 | defining-formula | BNS jump test statistic: $Z_{\text{BNS},t} = \frac{\RV_t - \BPV_t}{\sqrt{\vartheta\,\max\!\left(\frac{1}{n}\,\operatorname{RQ}_t,\; 10^{-10}\right)}}$ | BNS2006 | | | Core test statistic formula |
| 15 | 420 | numerical-fact | $\vartheta = (\pi^2/4) + \pi - 5 \approx 0.6090$ | BNS2006 | | | Constant from asymptotic theory |
| 16 | 421 | defining-formula | Realized quarticity: $\operatorname{RQ}_t = n\frac{\pi^2}{4}\frac{1}{3}\sum_{i=3}^{n}\lvert r_{t,i}\rvert\,\lvert r_{t,i-1}\rvert\,\lvert r_{t,i-2}\rvert$ | BNS2006 | | | Tripower-based RQ estimator |
| 17 | 424 | qualitative | Under the null of no jumps, $Z_{\text{BNS},t} \xrightarrow{d} \N(0,1)$ as $n \to \infty$ | BNS2006 | | | Asymptotic distribution |
| 18 | 443 | methodological | "At the 5% level (one-sided), declare a jump day if $Z_{\text{BNS},t} > 1.645$" | [uncited] | | | Standard normal critical value |
| 19 | 444 | methodological | "At the 1% level, use 2.326" | [uncited] | | | Standard normal critical value |
| 20 | 493 | qualitative | "The BNS test has known size distortions in finite samples: with 78 returns per day, it can over-reject the null (detect jumps that are not there) or under-reject (miss small jumps)" | HuangTauchen2005 | | | Finite-sample properties |
| 21 | 494 | attribution | "\citet{HuangTauchen2005} documented these problems and proposed a ratio form of the test statistic that has better finite-sample properties" | HuangTauchen2005 | | | Attribution of ratio variant |
| 22 | 507 | attribution | "\citet{LeeMykland2008}" proposed intraday jump detection test | LeeMykland2008 | | | Attribution |
| 23 | 524 | defining-formula | Lee-Mykland test statistic: $\mathcal{L}_{t,i} = \frac{\lvert r_{t,i}\rvert}{\hat{\sigma}_{t,i}}$ | LeeMykland2008 | | | Core LM statistic |
| 24 | 530 | methodological | Local volatility estimate computed as $\hat{\sigma}_{t,i} = \sqrt{\BPV_K / K}$ where $\BPV_K$ is bipower variation over the $K$-return window | LeeMykland2008 | | | Local vol estimation method |
| 25 | 534 | defining-formula | Lee-Mykland rejection rule: $\frac{\mathcal{L}_{t,i} - C_n}{S_n} > \beta_\alpha$ | LeeMykland2008 | | | Jump detection criterion |
| 26 | 537 | qualitative | $\beta_\alpha$ is the $(1-\alpha)$ quantile of the standard Gumbel distribution | LeeMykland2008 | | | Critical value distribution |
| 27 | 555 | qualitative | "The Lee-Mykland test provides both jump detection and jump timing at intraday frequency" | LeeMykland2008 | | | Key property of LM test |
| 28 | 557 | qualitative | "the test correctly identifies large jumps (those exceeding roughly 3--5 local standard deviations) with high power, while maintaining reasonable size control" | LeeMykland2008 | | | Power/size claim |
| 29 | 649 | attribution | "\citet{AitSahaliaJacod2009} proposed an alternative that is robust to microstructure noise" | AitSahaliaJacod2009 | | | Attribution of ASJ test |
| 30 | 663 | defining-formula | Power variation: $V_t^{(p)} = \sum_{i=1}^{n} \lvert r_{t,i}\rvert^p$ | [uncited] | | | General power variation formula |
| 31 | 667 | qualitative | "$p = 2$: this reduces to $\RV_t$ (realized variance)" | [uncited] | | | Power variation special case |
| 32 | 669 | qualitative | "for $p < 2$, the power variation is dominated by diffusion (jumps contribute negligibly). For $p = 2$, jumps contribute fully. For $p > 2$, jumps dominate" | [uncited] | | | Power variation sensitivity to jumps |
| 33 | 687 | qualitative | "Under the null of no jumps, the ratio converges to a constant $k^{p/2-1}$" | AitSahaliaJacod2009 | | | Null-hypothesis ratio limit |
| 34 | 693 | defining-formula | ASJ test statistic: $S_t = \frac{V_t^{(p)}(\Delta)}{V_t^{(p)}(k\Delta)}$ | AitSahaliaJacod2009 | | | Power-variation ratio |
| 35 | 695 | qualitative | $S_t$ converges to $k^{p/2-1}$ under the null of no jumps | AitSahaliaJacod2009 | | | Convergence result |
| 36 | 697 | qualitative | "microstructure noise affects numerator and denominator similarly, making the test more robust than BNS in noisy settings" | AitSahaliaJacod2009 | | | Noise robustness claim |
| 37 | 723 | defining-formula | Threshold realized variance: $\operatorname{TRV}_t = \sum_{i=1}^{n} r_{t,i}^2 \cdot \mathbf{1}\!\left\{\lvert r_{t,i}\rvert \leq \vartheta_i\right\}$ | [uncited] | | | Core TRV formula |
| 38 | 730 | methodological | Threshold typically set as $\vartheta_i = c\,\hat{\sigma}_i\,\Delta^{\varpi}$ where $c$ is a constant (e.g., $c = 3$), $\varpi \in (0, 1/2)$ | [uncited] | | | Threshold calibration |
| 39 | 748 | attribution | "\citet{Mancini2009} established the theoretical foundation for threshold estimators" | Mancini2009 | | | Attribution |
| 40 | 749 | attribution | "\citet{CorsiPirinoReno2010} combined the threshold approach with the HAR forecasting model to produce the HAR-CJ decomposition" | CorsiPirinoReno2010 | | | Attribution |
| 41 | 750 | qualitative | "threshold-based continuous and jump components improve forecasting performance when entered separately into the HAR model, because they have different persistence" | CorsiPirinoReno2010 | | | Key finding |
| 42 | 753 | qualitative | "Splitting $\RV_t$ into $C_t = \operatorname{TRV}_t$ and $J_t = \RV_t - \operatorname{TRV}_t$ ...produces significantly better volatility forecasts than the baseline HAR" | CorsiPirinoReno2010 | | | Forecasting improvement claim |
| 43 | 754 | qualitative | "The improvement comes from allowing the model to assign different persistence parameters to continuous and jump variation" | CorsiPirinoReno2010 | | | Mechanism of improvement |
| 44 | 802 | numerical-fact | Continuous variation autocorrelation $\approx 0.6$--$0.7$ | [uncited] | | | In decomposition pipeline diagram |
| 45 | 803 | numerical-fact | Jump variation autocorrelation $\approx 0.0$--$0.1$ | [uncited] | | | In decomposition pipeline diagram |
| 46 | 826 | qualitative | "the forecasting improvement comes from the continuous side: by removing jump contamination, you get a cleaner, more persistent signal" | ABD2007 | | | Key forecasting insight |
| 47 | 831a | qualitative | "bad jumps (large negative returns) are more informative for future volatility than good jumps (large positive returns)" | BKT2015 | | | Asymmetric jump effect |
| 48 | 831b | qualitative | "bad jumps (large negative returns) are more informative for future volatility than good jumps (large positive returns)" | PSS2015 | | | Asymmetric jump effect |
| 49 | 911 | qualitative | "Jump component of $\RV$ has near-zero persistence; forecasting improves when continuous and jump components are modeled separately" | ABD2007 | | | In key results table |
| 50 | 421 | qualitative | Realized quarticity $\operatorname{RQ}_t$ is "a consistent estimator of integrated quarticity $\int\sigma^4_s\,ds$" | BNS2006 | | | RQ consistency claim |
