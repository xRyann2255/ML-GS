# Chapter 1: Returns, Variance, and Why Volatility Matters -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 52
**Verified:** 0/52
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 28 | supporting-formula | $\ln(e^x) = x$ (natural log is inverse of exponential) | [uncited] | | | Standard math identity |
| 2 | 31 | supporting-formula | $\ln(A/B) = \ln A - \ln B$ | [uncited] | | | Standard log property |
| 3 | 32 | supporting-formula | $\ln(AB) = \ln A + \ln B$ | [uncited] | | | Standard log property |
| 4 | 33 | supporting-formula | For small $x$: $\ln(1+x) \approx x$ (log returns approx equal simple returns when returns are small) | [uncited] | | | First-order Taylor expansion |
| 5 | 43-46 | defining-formula | Simple return: $R_t = \frac{P_t - P_{t-1}}{P_{t-1}}$ | [uncited] | | | Standard textbook definition |
| 6 | 73-76 | defining-formula | Log return: $r_t = \ln(P_t / P_{t-1}) = \ln P_t - \ln P_{t-1}$ | [uncited] | | | Standard textbook definition |
| 7 | 98-99 | supporting-formula | Multi-period log return is the sum of single-period log returns: $r_{1:T} = r_1 + r_2 + \cdots + r_T$ (time additivity) | [uncited] | | | Follows from log properties |
| 8 | 103 | supporting-formula | Two-day simple return is $(1+R_1)(1+R_2) - 1$, not $R_1 + R_2$ (multiplicative compounding) | [uncited] | | | Standard textbook result |
| 9 | 106-107 | numerical-fact | Symmetry example: $+0.05$ then $-0.05$ log return yields exact round-trip ($P_{\text{final}} = P_{\text{start}}$), but simple returns: $\$100 \times 1.05 \times 0.95 = \$99.75 \neq \$100$ | [uncited] | | | Verify arithmetic: $100 \times 1.05 = 105$; $105 \times 0.95 = 99.75$. Correct. |
| 10 | 117 | numerical-fact | Worked example: $R_{\text{Tue}} = (105-100)/100 = 0.0500$ (+5.00%) | [uncited] | | | Verify: $(105-100)/100 = 5/100 = 0.05$. Correct. |
| 11 | 118 | numerical-fact | Worked example: $r_{\text{Tue}} = \ln(105/100) = \ln(1.05) = 0.0488$ (+4.88%) | [uncited] | | | Verify: $\ln(1.05) = 0.04879\ldots \approx 0.0488$. Correct. |
| 12 | 122 | numerical-fact | Worked example: $R_{\text{Wed}} = (102-105)/105 = -0.0286$ (-2.86%) | [uncited] | | | Verify: $(102-105)/105 = -3/105 = -0.02857\ldots \approx -0.0286$. Correct. |
| 13 | 124 | numerical-fact | Worked example: $r_{\text{Wed}} = \ln(102/105) = \ln(0.9714) = -0.0290$ (-2.90%) | [uncited] | | | Verify: $102/105 = 0.97143$; $\ln(0.97143) = -0.02899\ldots \approx -0.0290$. Correct. |
| 14 | 129 | numerical-fact | Two-day log return: $0.0488 + (-0.0290) = 0.0198$ | [uncited] | | | Verify: $0.0488 - 0.0290 = 0.0198$. Correct. |
| 15 | 131 | numerical-fact | Direct check: $\ln(102/100) = \ln(1.02) = 0.0198$ | [uncited] | | | Verify: $\ln(1.02) = 0.01980\ldots \approx 0.0198$. Correct. |
| 16 | 155-158 | defining-formula | Sample variance: $\hat{\sigma}^2 = \frac{1}{T-1}\sum_{t=1}^{T}(r_t - \bar{r})^2$ | [uncited] | | | Standard textbook definition with Bessel's correction |
| 17 | 164 | methodological | Dividing by $T-1$ instead of $T$ gives an unbiased estimate of variance (Bessel's correction) | [uncited] | | | Standard statistical result |
| 18 | 192 | qualitative | Raw daily standard deviations are around 0.01 for a typical equity index | [uncited] | | | Approximate empirical claim; 0.01 = 1% daily vol |
| 19 | 194 | supporting-formula | For independent returns: $\operatorname{Var}(r_1 + \cdots + r_n) = n\sigma^2$; standard deviation scales as $\sqrt{n}\,\sigma$ | [uncited] | | | Standard probability result for independent RVs |
| 20 | 197-200 | defining-formula | Annualized volatility: $\hat{\sigma}_{\text{annual}} = \hat{\sigma}_{\text{daily}} \times \sqrt{252}$ | [uncited] | | | Standard convention |
| 21 | 202 | numerical-fact | 252 is the approximate number of trading days per year in U.S. equity markets | [uncited] | | | Industry convention; verify against NYSE calendar |
| 22 | 203 | numerical-fact | $\sqrt{252} \approx 15.87$ | [uncited] | | | Verify: $\sqrt{252} = 15.8745\ldots \approx 15.87$. Correct. |
| 23 | 209 | numerical-fact | A stock with 1% daily volatility has roughly 16% annual volatility | [uncited] | | | Follows from $0.01 \times 15.87 \approx 0.159 \approx 16\%$. Correct. |
| 24 | 226 | numerical-fact | Worked example: $0.50\% \times \sqrt{252} = 0.50\% \times 15.87 = 7.9\%$ | [uncited] | | | Verify: $0.005 \times 15.87 = 0.07937 \approx 7.9\%$. Correct. |
| 25 | 228 | qualitative | The S&P 500's long-run annualized volatility is roughly 15--20% | [uncited] | | | Well-known empirical range; verify against historical data |
| 26 | 249 | attribution | The Black-Scholes model takes volatility as an input and produces an option price as output | Black1973 | | | Core claim about BS model structure |
| 27 | 256 | numerical-fact | For a 99% daily VaR under normality, the worst expected loss is about 2.33 times daily volatility | [uncited] | | | Verify: $\Phi^{-1}(0.99) = 2.326\ldots \approx 2.33$. Correct. |
| 28 | 259 | attribution | Mean-variance optimization requires a covariance matrix as input | Markowitz1952 | | | Core claim about Markowitz framework |
| 29 | 275 | numerical-fact | 78 five-minute returns per trading day (as example of $M$ for RV) | [uncited] | | | Verify: 6.5 hours $\times$ 12 intervals/hour = 78. Correct. |
| 30 | 287 | attribution | Cont catalogued "stylized facts": statistical regularities observed across equities, FX, and commodities, across decades and geographies | Cont2001 | | | Core claim about paper scope |
| 31 | 298 | qualitative | Daily return autocorrelations are statistically indistinguishable from zero for lags beyond a few minutes | Cont2001 | | | Check: Cont2001 discusses this at daily frequency, "a few minutes" framing needs verification |
| 32 | 311 | attribution | Squared returns and absolute returns show strong, slowly decaying positive autocorrelation | Cont2001, Mandelbrot1963 | | | Dual attribution; verify both sources discuss this |
| 33 | 314 | attribution | Engle formalized volatility clustering with the ARCH model: variance of next period's return depends on recent squared returns | Engle1982 | | | Core claim about ARCH specification |
| 34 | 318 | qualitative | Autocorrelation of absolute returns decays approximately as a power law with exponent $\beta \in [0.2, 0.4]$ | Cont2001 | | | Verify specific exponent range in Cont 2001 |
| 35 | 323 | numerical-fact | With $\beta \approx 0.3$, autocorrelation at lag 100 is about $100^{-0.3} \approx 0.25$ | [uncited] | | | Verify: $100^{-0.3} = 10^{-0.6} = 0.2512\ldots \approx 0.25$. Correct. |
| 36 | 494 | numerical-fact | If returns were normally distributed, a daily move of 4 standard deviations would occur about once every 126 years | [uncited] | | | Verify: two-tailed $P(|Z|>4) = 2 \times (1-\Phi(4)) = 2 \times 3.167 \times 10^{-5} = 6.334 \times 10^{-5}$; at 252 days/yr, expected interval = $1/(252 \times 6.334 \times 10^{-5}) \approx 62.6$ years. Claimed 126 years -- needs checking; may use one-tailed probability |
| 37 | 498 | attribution | Mandelbrot first documented fat tails for cotton prices, proposing returns follow a stable Paretian distribution | Mandelbrot1963 | | | Verify: cotton prices and stable Paretian proposal |
| 38 | 499 | attribution | Fama confirmed fat tails for stock returns, observing leptokurtic distributions across U.S. equities | Fama1965 | | | Verify: leptokurtosis finding in Fama 1965 |
| 39 | 504-507 | defining-formula | Kurtosis: $\kappa = \frac{E[(r_t - \mu)^4]}{(E[(r_t - \mu)^2])^2}$ | [uncited] | | | Standard definition of kurtosis |
| 40 | 511 | numerical-fact | For a normal distribution, $\kappa = 3$ | [uncited] | | | Standard statistical result |
| 41 | 527 | numerical-fact | Typical daily equity index returns have excess kurtosis in the range 5--10 | Cont2001 | | | Verify specific range in Cont 2001 |
| 42a | 601 | attribution | Black first noted the leverage effect: negative returns increase future volatility more than positive returns of same magnitude | Black1976 | | | Verify priority claim and mechanism description |
| 42b | 601-602 | qualitative | Proposed mechanism: when stock price falls, equity shrinks relative to debt, leverage (debt/equity) rises, making stock riskier and more volatile | Black1976 | | | Verify this is Black's stated mechanism |
| 43 | 629 | qualitative | In FX and commodity markets, the leverage effect (asymmetry) is weaker or sometimes reversed | Cont2001 | | | Verify in Cont 2001 |
| 44 | 694 | numerical-fact | Worked example: S&P 500 annualized volatility was about 16% over 2024 (unconditional estimate) | [uncited] | | | Verify against actual 2024 SPX realized vol |
| 45 | 694 | numerical-fact | Worked example: during a turbulent week in August [2024], realized daily vol spiked to 35% annualized | [uncited] | | | Verify against actual Aug 2024 SPX vol (likely refers to Aug 5 yen-carry unwind) |
| 46 | 694 | numerical-fact | Worked example: during a calm stretch in November [2024], vol dropped to 9% annualized | [uncited] | | | Verify against actual Nov 2024 SPX vol |
| 47 | 701-704 | defining-formula | Law of total variance: $\sigma^2 = E[\sigma_t^2] + \operatorname{Var}(E[r_t \mid \mathcal{F}_{t-1}])$ | [uncited] | | | Standard probability identity |
| 48 | 830-831 | attribution | Mandelbrot 1963: daily commodity returns follow a stable Paretian distribution; sample variance does not converge | Mandelbrot1963 | | | Key results table: verify "sample variance does not converge" claim |
| 49 | 833-834 | attribution | Fama 1965: confirmed fat tails via S-shaped Q-Q departures from normality; supported stable distribution hypothesis | Fama1965 | | | Key results table |
| 50 | 838-839 | attribution | Black 1976: documented negative correlation between stock returns and subsequent volatility changes | Black1976 | | | Key results table |
| 51 | 841-842 | attribution | Engle 1982: introduced ARCH where conditional variance is function of past squared residuals; applied to UK inflation | Engle1982 | | | Key results table: verify application to UK inflation |
| 52 | 845-847 | attribution | Cont 2001: canonical enumeration of stylized facts (absence of return autocorrelation, volatility clustering with slow power-law decay, fat tails, leverage effect) across equities, FX, and commodities | Cont2001 | | | Key results table |
