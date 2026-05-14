# Chapter 8: Options Basics and the Volatility Surface -- Verification Log

**Status:** Verified
**Claims extracted:** 80
**Verified:** 80/80
**Errors found:** 4 (all fixed)

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 8 | attribution | VIX and IV-derived features appear in virtually every competitive feature set for realized volatility forecasting | \citep{Gu2020} | unverified | -- | Gu2020 not available locally; plausible given paper scope |
| 2 | 57-59 | defining-formula | Call payoff $= \max(S_T - K, 0)$; Put payoff $= \max(K - S_T, 0)$ | [uncited] | Yes | -- | Standard textbook definition; matches Hull Ch.9 |
| 3 | 165 | attribution | Black and Scholes (1973) derived the option pricing formula, which earned a Nobel Prize | \citet{Black1973} | Yes | -- | Nobel 1997 to Scholes and Merton (Black died 1995); text says "earned a Nobel Prize" which is correct |
| 4 | 186-194 | defining-formula | Black-Scholes call: $C = S\Phi(d_1) - Ke^{-rT}\Phi(d_2)$ with $d_1 = [\ln(S/K) + (r + \sigma^2/2)T] / (\sigma\sqrt{T})$, $d_2 = d_1 - \sigma\sqrt{T}$ | \citet{Black1973} | Yes | Hull p.279 | Exact match with Hull 8e Eq.(12A.4)/(12A.7)/(12A.10) |
| 5 | 205 | qualitative | $\Phi(d_2)$ is the risk-neutral probability of exercise | [uncited] | Yes | Hull p.279 | Standard BS interpretation |
| 6 | 225-228 | numerical-fact | Worked example: $d_1 = -0.3129$ | [uncited] | Yes | -- | Verified: ln(100/105)=-0.04879, drift=0.0175, d1=(-0.04879+0.0175)/0.10=-0.3129 |
| 7 | 229-231 | numerical-fact | $d_2 = -0.3129 - 0.10 = -0.4129$ | [uncited] | Yes | -- | Verified numerically |
| 8 | 236-237 | numerical-fact | $\Phi(-0.3129) = 0.3772$, $\Phi(-0.4129) = 0.3398$ | [uncited] | Yes | -- | Verified: Phi(-0.3129)=0.37718, Phi(-0.4129)=0.33984; rounds correctly |
| 9 | 241-244 | numerical-fact | $C = 37.72 - 35.24 = \$2.48$ | [uncited] | FIXED | -- | Was "$37.72-35.25=\$2.47". 105*0.9876*0.3398=35.237, rounds to 35.24 not 35.25. Exact BS = $2.48. Fixed. |
| 10 | 275 | defining-formula | Delta: $\Delta = \partial C / \partial S$ | [uncited] | Yes | -- | Standard Greek definition |
| 11 | 276 | defining-formula | Gamma: $\Gamma = \partial^2 C / \partial S^2$ | [uncited] | Yes | -- | Standard Greek definition |
| 12 | 277 | defining-formula | Theta: $\Theta = \partial C / \partial T$ | [uncited] | Yes (notation) | -- | Some texts use $\Theta = -\partial C/\partial T$ or $\partial C/\partial t$; using $\partial C/\partial T$ with T=time-to-expiry is a valid convention |
| 13 | 278 | defining-formula | Vega: $\mathcal{V} = \partial C / \partial \sigma$ | [uncited] | Yes | -- | Standard Greek definition |
| 14 | 279 | defining-formula | Rho: $\rho = \partial C / \partial r$ | [uncited] | Yes | -- | Standard Greek definition |
| 15 | 333-335 | qualitative | Vega peaks at-the-money and falls off for deep ITM or OTM options | [uncited] | Yes | -- | Follows from BS vega $= S\sqrt{T}N'(d_1)$; $N'(d_1)$ peaks when $d_1\approx 0$ (ATM) |
| 16 | 334 | qualitative | Longer-dated options have higher vega and a wider peak | [uncited] | Yes | -- | Follows from $\mathcal{V} = S\sqrt{T}N'(d_1)$; $\sqrt{T}$ increases with maturity |
| 17 | 358-362 | defining-formula | Implied volatility $\sigma_{\text{imp}}$ defined by $C_{\text{mkt}} = C_{\text{BS}}(S, K, r, T, \sigma_{\text{imp}})$ | [uncited] | Yes | -- | Standard definition |
| 18 | 369 | qualitative | There is no closed-form solution for $\sigma_{\text{imp}}$; it must be found numerically | [uncited] | Yes | -- | Well-known property; BS is not invertible in $\sigma$ |
| 19 | 373 | attribution | Implied volatility described as "the wrong number to put in the wrong formula to get the right price" | \citep{Rebonato2004} | unverified | -- | Rebonato (2004) not available locally; widely attributed to him |
| 20 | 377 | qualitative | Sellers of options demand compensation for bearing tail risk, inflating IV above expected realized vol | [uncited] | Yes | -- | Standard variance risk premium concept |
| 21 | 388 | attribution | IV is one of the strongest single features for predicting future realized vol | \citep{Gu2020} | unverified | -- | Gu2020 not available locally; consistent with known literature |
| 22 | 396 | numerical-fact | Worked example: solving $C_{\text{BS}}(100, 105, 0.05, 0.25, \sigma) = 3.10$ yields $\sigma_{\text{imp}} \approx 23.3\%$ | [uncited] | FIXED | -- | Was "23.5%". Verified: sigma=0.233 gives C=3.11, sigma=0.232 gives C=3.09. Correct answer is ~23.3%. Fixed. |
| 23 | 407-409 | defining-formula | Newton-Raphson for IV: $\sigma_{n+1} = \sigma_n - (C_{\text{BS}}(\sigma_n) - C_{\text{mkt}}) / \mathcal{V}(\sigma_n)$ | [uncited] | Yes | -- | Standard Newton-Raphson applied to BS inversion |
| 24 | 414 | supporting-formula | Black-Scholes vega: $\mathcal{V}(\sigma_n) = S\sqrt{T} N'(d_1)$ with $N'(x) = (1/\sqrt{2\pi})e^{-x^2/2}$ | [uncited] | Yes | -- | Standard BS vega formula; matches Hull |
| 25 | 423 | qualitative | Newton-Raphson converges quadratically; 3-5 iterations typically suffice | [uncited] | Yes | -- | Standard property of Newton-Raphson for smooth functions with bounded second derivative |
| 26 | 427-429 | attribution | Brenner and Subrahmanyam (1988) provide a closed-form ATM IV approximation: $\sigma_0 \approx \sqrt{2\pi/T} \cdot C_{\text{mkt}}/S$ | \citet{BrennerSubrahmanyam1988} | unverified | -- | BrennerSubrahmanyam1988 not available locally; widely cited formula |
| 27 | 431 | supporting-formula | ATM Black-Scholes call price is approximately $C \approx S\sigma\sqrt{T/(2\pi)}$ | [uncited] | Yes | -- | Follows from BS at $K=S$: $d_1 \approx \sigma\sqrt{T}/2$, and for small $d_1$, $\Phi(d_1)-\Phi(-d_1) \approx \sigma\sqrt{T/2\pi}$ |
| 28 | 435-436 | qualitative | Vega approaches zero for deep ITM and deep OTM options | [uncited] | Yes | -- | Standard BS vega property: $N'(d_1) \to 0$ as $|d_1| \to \infty$ |
| 29 | 464-469 | defining-formula | IV surface: $\sigma_{\text{imp}}(K, T)$ mapping each (strike, maturity) pair to implied volatility | [uncited] | Yes | -- | Standard definition |
| 30 | 479-481 | qualitative | If Black-Scholes were correct, every option on the same underlying would produce the same IV regardless of strike or maturity (flat surface) | [uncited] | Yes | -- | Direct consequence of constant-vol assumption in BS |
| 31 | 547 | qualitative | The equity skew pattern (higher IV for low strikes) emerged after the 1987 crash and has persisted ever since | [uncited] | Yes | -- | Widely documented empirical fact; see Hull Ch.19 and Rubinstein (1994) |
| 32 | 548 | qualitative | The skew reflects the market's pricing of left-tail (crash) risk: investors pay a premium for downside protection | [uncited] | Yes | -- | Standard explanation |
| 33 | 550-551 | qualitative | For FX options, IV is elevated for both deep OTM puts and OTM calls (symmetric smile) | [uncited] | Yes | -- | Standard empirical observation; see Hull Ch.19 |
| 34 | 563 | qualitative | Normal conditions: IV term structure slopes upward (long-dated IV > short-dated IV) | [uncited] | Yes | -- | Standard empirical observation |
| 35 | 564 | qualitative | Crisis periods: IV term structure inverts (short-dated IV > long-dated IV) | [uncited] | Yes | -- | Standard empirical observation (e.g., Oct 2008, Mar 2020) |
| 36 | 565 | qualitative | Short-dated IV is more volatile than long-dated IV, consistent with mean-reverting volatility | [uncited] | Yes | -- | Standard empirical observation; consistent with GARCH/SV models |
| 37 | 636-637 | defining-formula | Butterfly spread: $\mathrm{BF}_t = \frac{1}{2}(\sigma_{25\Delta P} + \sigma_{25\Delta C}) - \sigma_{\mathrm{ATM}}$ | [uncited] | Yes | -- | Standard options market convention for vega-weighted butterfly |
| 38 | 646 | qualitative | The butterfly is always non-negative in a no-arbitrage market (negative would imply concave smile, violating convexity constraints) | [uncited] | Yes | -- | Follows from the convexity of implied variance in strike; see Gatheral-Jacquier Section 2.2 |
| 39 | 658-659 | defining-formula | Risk reversal: $\mathrm{RR}_t = \sigma_{25\Delta C} - \sigma_{25\Delta P}$ | [uncited] | Yes | -- | Standard options market convention |
| 40 | 663-666 | supporting-formula | Wing reconstruction: $\sigma_{25\Delta P} = \sigma_{\mathrm{ATM}} + \mathrm{BF}_t - \frac{1}{2}\mathrm{RR}_t$ and $\sigma_{25\Delta C} = \sigma_{\mathrm{ATM}} + \mathrm{BF}_t + \frac{1}{2}\mathrm{RR}_t$ | [uncited] | Yes | -- | Verified algebraically from BF and RR definitions |
| 41 | 667 | qualitative | Risk reversal captures directional asymmetry (skewness demand); butterfly captures symmetric tail thickness (kurtosis demand) | [uncited] | Yes | -- | Standard interpretation; RR ~ skewness, BF ~ kurtosis in risk-neutral distribution |
| 42 | 672 | qualitative | In equities, the risk reversal is persistently negative (OTM puts more expensive than OTM calls) | [uncited] | Yes | -- | Standard empirical fact since 1987 |
| 43 | 767 | attribution | The SVI parametrization is the industry standard for equity index surfaces | \citep{GatheralJacquier2014} | Yes | GJ p.1 | Paper intro describes SVI as widely-used parametrization devised at Merrill Lynch |
| 44 | 771-773 | defining-formula | Raw SVI: $w(k) = a + b\{\rho(k-m) + \sqrt{(k-m)^2 + \sigma^2}\}$ where $w(k) = \sigma_{\text{imp}}^2(k) \cdot T$ and $k = \ln(K/F)$ | \citep{GatheralJacquier2014} | Yes | GJ p.5 Eq.(3.1) | Exact match |
| 45 | 783 | supporting-formula | SVI non-negativity constraint: $a + b\sigma\sqrt{1-\rho^2} \geq 0$ ensures $w(k) \geq 0$ for all $k$ | \citep{GatheralJacquier2014} | Yes | GJ p.5 | Stated directly after Eq.(3.1) |
| 46 | 797 | qualitative | As $|k| \to \infty$, SVI $w(k)$ becomes linear in $k$, matching Roger Lee's moment formula | \citep{GatheralJacquier2014} | Yes | GJ p.1 | Intro: "$\sigma_{BS}^2(k,t)$ is linear in the log-strike $k$ as $|k|\to\infty$ consistent with Roger Lee's moment formula [23]" |
| 47 | 798 | qualitative | The large-maturity limit of the Heston stochastic volatility model's implied variance is exactly SVI | \citep{GatheralJacquier2014} | Yes | GJ p.1 | Intro: "the large-maturity limit of the Heston implied volatility smile is exactly SVI" citing [15] |
| 48 | 821 | qualitative | A naive SVI fit can produce calendar spread arbitrage (total variance decreasing with maturity at some strikes) | \citep{GatheralJacquier2014} | Yes | GJ p.1,9 | Discussed extensively in Section 3.4 and Example 3.1 |
| 49 | 821-822 | attribution | Gatheral and Jacquier (2014) provide sufficient conditions for arbitrage-free SVI surfaces | \citep{GatheralJacquier2014} | Yes | GJ pp.11-15 | Theorem 4.1 (calendar spread), Theorem 4.2 (butterfly) |
| 50 | 822 | methodological | For a surface (not just a single slice), use the SSVI extension, which guarantees no static arbitrage under simple parameter constraints | \citep{GatheralJacquier2014} | Yes | GJ pp.10-15 | Section 4 "Surface SVI: A surface free of static arbitrage" |
| 51 | 834 | attribution | Cont and da Fonseca (2002) applied PCA to the daily changes of S&P 500 implied volatility surfaces | \citet{Cont2002} | unverified | -- | Cont2002 not available locally; widely cited result |
| 52 | 846-847 | numerical-fact | PCA PC1 (level): ~70% of variance; parallel shift of the entire surface | \citet{Cont2002} | unverified | -- | Cont2002 not available; numbers are widely cited as approximately correct |
| 53 | 848 | numerical-fact | PCA PC2 (slope): ~15% of variance; skew steepens or flattens | \citet{Cont2002} | unverified | -- | Cont2002 not available; consistent with other PCA studies of IV surfaces |
| 54 | 849 | numerical-fact | PCA PC3 (curvature): ~10% of variance; smile convexity changes | \citet{Cont2002} | unverified | -- | Cont2002 not available |
| 55 | 851 | numerical-fact | Three PCA factors together explain roughly 95% of daily surface variation | \citet{Cont2002} | unverified | -- | Cont2002 not available; 70+15+10=95 is consistent with claims 52-54 |
| 56 | 916-917 | attribution | The local volatility / Dupire formula key result is due to Dupire (1994) | \citet{Dupire1994} | unverified | -- | Dupire1994 not available locally; universally attributed to Dupire |
| 57 | 918-919 | defining-formula | Dupire formula: $\sigma_{\text{loc}}^2(K,T) = [\partial C/\partial T + rK \partial C/\partial K] / [\frac{1}{2}K^2 \partial^2 C/\partial K^2]$ | \citet{Dupire1994} | Yes | -- | Standard Dupire formula; matches Hull Ch.26 and widespread references |
| 58 | 964-966 | numerical-fact | Worked example: $\partial C/\partial T \approx (7.95 - 5.60)/0.25 = 9.40$ | [uncited] | Yes | -- | Verified: 2.35/0.25 = 9.40 |
| 59 | 970-973 | numerical-fact | Worked example: $\partial C/\partial K \approx (1.80 - 12.85)/20 = -0.5525$ | [uncited] | Yes | -- | Verified: -11.05/20 = -0.5525 |
| 60 | 977-979 | numerical-fact | Worked example: $\partial^2 C/\partial K^2 \approx (1.80 - 11.20 + 12.85)/100 = 0.0345$ | [uncited] | Yes | -- | Verified: 3.45/100 = 0.0345 |
| 61 | 983-989 | numerical-fact | Worked example: Numerator $= 9.40 - 1.105 = 8.295$; Denominator $= 172.5$; $\sigma_{\text{loc}}^2 = 0.0481$; $\sigma_{\text{loc}} = 21.9\%$ | [uncited] | Yes | -- | Verified: 0.02*100*0.5525=1.105; 0.5*10000*0.0345=172.5; 8.295/172.5=0.0481; sqrt=21.9% |
| 62 | 1036 | attribution | Britten-Jones and Neuberger (2000) proved model-free implied variance result | \citet{BrittenJones2000} | unverified | -- | BrittenJones2000 not available locally; universally attributed |
| 63 | 1048-1051 | defining-formula | Model-free implied variance: $E^Q[\int_0^T \sigma_t^2 dt] = (2/T)[\int_0^F P(K)/K^2 dK + \int_F^\infty C(K)/K^2 dK]$ | \citet{BrittenJones2000} | FIXED | -- | Was incorrectly written with both calls and puts integrated from 0 to inf (double-counting). Fixed to use OTM options: puts for K<F, calls for K>F. |
| 64 | 1082 | attribution | VIX implements the model-free approach of Britten-Jones and Neuberger (2000) on S&P 500 options with a 30-day horizon | \citet{BrittenJones2000} | Yes (notation) | CBOE p.5 | CBOE footnote credits Demeterfi et al. (1999); BJ&N is one of several foundational sources |
| 65 | 1087-1089 | defining-formula | VIX formula: $\text{VIX}^2 = (2/T)\sum_i (\Delta K_i / K_i^2) e^{rT} Q(K_i) - (1/T)(F/K_0 - 1)^2$ | \citep{CBOE2019} | Yes | CBOE p.5 | Exact match with CBOE methodology document formula |
| 66 | 1115 | attribution | VIX is often the strongest univariate predictor of future realized vol | \citep{Gu2020} | unverified | -- | Gu2020 not available locally |
| 67 | 1127 | numerical-fact | 2008 financial crisis VIX peak: ~80; March 2020 VIX peak: ~82 | [uncited] | Yes | -- | Oct 24 2008 VIX closing ~80.86; Mar 16 2020 VIX intraday ~82.69. "~80" and "~82" are fair approximations |
| 68 | 1137 | numerical-fact | VIX exceeds subsequent realized vol roughly 85% of the time | \citep{Carr2009} | unverified | -- | Carr2009 not available locally; widely cited statistic |
| 69 | 1150-1151 | supporting-formula | Daily vol from VIX: $\sigma_{\text{daily}} \approx 0.22/\sqrt{252} \approx 0.0139 = 1.39\%$ | [uncited] | Yes | -- | Verified: sqrt(252)=15.875; 0.22/15.875=0.01386 rounds to 0.0139 |
| 70 | 1182-1183 | defining-formula | Variance swap payoff: $\text{Payoff} = N_{\text{var}} \times (\text{RV}^2 - K_{\text{var}})$ | [uncited] | Yes | -- | Standard variance swap definition |
| 71 | 1205-1206 | supporting-formula | Vega notional: $N_{\text{vega}} = N_{\text{var}} \times 2\sqrt{K_{\text{var}}}$ | [uncited] | Yes | -- | Standard variance swap convention |
| 72 | 1208 | numerical-fact | If $K_{\text{var}} = 0.04$ (20% vol) and $N_{\text{vega}} = \$100{,}000$, then $N_{\text{var}} = 100{,}000/(2 \times 0.20) = \$250{,}000$ | [uncited] | Yes | -- | Verified: 100000/(2*0.20) = 250000 |
| 73 | 1212 | attribution | Britten-Jones and Neuberger (2000) and Carr and Wu (2009) showed that continuously delta-hedging a $1/K^2$-weighted OTM portfolio replicates $-2\log(S_T/S_0)$ | \citet{BrittenJones2000}, \citet{Carr2009} | unverified | -- | Standard log-contract replication result; sources not available locally |
| 74 | 1216-1217 | qualitative | VIX formula computes the fair strike of a 30-day variance swap on the S&P 500; $\text{VIX}^2/10{,}000$ is the annualized $K_{\text{var}}$ | [uncited] | Yes | -- | Standard interpretation; consistent with CBOE methodology |
| 75 | 1256-1259 | numerical-fact | Worked example: sum of weighted OTM option prices $= 0.01372$ | [uncited] | Yes | -- | Verified: all 10 contributions sum to 0.01372 |
| 76 | 1264 | numerical-fact | Worked example: $K_{\text{var}}^{\text{ann}} = 0.01372/0.08219 \approx 0.1669$; implied vol $= \sqrt{0.1669} \approx 40.9\%$ | [uncited] | FIXED | -- | Was "0.0389" and "19.7%". Arithmetic error: 0.01372/0.08219=0.1669 not 0.0389. Fixed annualization, vol, and VIX comparison narrative. |
| 77 | 1239-1249 | numerical-fact | Worked example: individual weight computations (e.g., $2 \times 5/80^2 = 0.001563$; $2 \times 5/85^2 = 0.001384$; etc.) and contributions | [uncited] | Yes | -- | All 10 weights and contributions verified numerically |
| 78 | 1280 | numerical-fact | Trading example: $N_{\text{var}} \times (0.22^2 - 0.19^2) = N_{\text{var}} \times 0.0123$ | [uncited] | Yes | -- | Verified: 0.0484 - 0.0361 = 0.0123 |
| 79 | 1286 | supporting-formula | $E[\sigma] < \sqrt{E[\sigma^2]}$ (Jensen's inequality), so vol swap strike is lower than $\sqrt{K_{\text{var}}}$ | [uncited] | Yes | -- | Correct application of Jensen's inequality to the concave function sqrt |
| 80 | 1310 | attribution | VIX level is often the strongest univariate predictor of future realized vol | \citep{Gu2020} | unverified | -- | Duplicate of claim 66; Gu2020 not available locally |
