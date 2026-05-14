# Chapter 8: Options Basics and the Volatility Surface -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 80
**Verified:** 0/80
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 8 | attribution | VIX and IV-derived features appear in virtually every competitive feature set for realized volatility forecasting | \citep{Gu2020} | | | |
| 2 | 57-59 | defining-formula | Call payoff $= \max(S_T - K, 0)$; Put payoff $= \max(K - S_T, 0)$ | [uncited] | | | Standard textbook definition |
| 3 | 165 | attribution | Black and Scholes (1973) derived the option pricing formula, which earned a Nobel Prize | \citet{Black1973} | | | Nobel was 1997, awarded to Scholes and Merton (Black deceased 1995) |
| 4 | 186-194 | defining-formula | Black-Scholes call: $C = S\Phi(d_1) - Ke^{-rT}\Phi(d_2)$ with $d_1 = [\ln(S/K) + (r + \sigma^2/2)T] / (\sigma\sqrt{T})$, $d_2 = d_1 - \sigma\sqrt{T}$ | \citet{Black1973} | | | |
| 5 | 205 | qualitative | $\Phi(d_2)$ is the risk-neutral probability of exercise | [uncited] | | | Standard BS interpretation |
| 6 | 225-228 | numerical-fact | Worked example: $d_1 = (\ln(100/105) + (0.05 + 0.04/2)(0.25)) / (0.20\sqrt{0.25}) = (-0.04879 + 0.0175)/0.10 = -0.3129$ | [uncited] | | | Numerical check needed: $\ln(100/105) = -0.04879$; $(0.05+0.02)(0.25)=0.0175$ |
| 7 | 229-231 | numerical-fact | $d_2 = -0.3129 - 0.20\sqrt{0.25} = -0.3129 - 0.10 = -0.4129$ | [uncited] | | | Numerical check |
| 8 | 236-237 | numerical-fact | $\Phi(-0.3129) = 0.3772$, $\Phi(-0.4129) = 0.3398$ | [uncited] | | | Verify CDF values |
| 9 | 241-244 | numerical-fact | $C = 100 \times 0.3772 - 105 \times e^{-0.05 \times 0.25} \times 0.3398 = 37.72 - 35.25 = \$2.47$ | [uncited] | | | Verify: $e^{-0.0125} = 0.9876$; $105 \times 0.9876 \times 0.3398 = 35.25$ |
| 10 | 275 | defining-formula | Delta: $\Delta = \partial C / \partial S$ | [uncited] | | | Standard Greek definition |
| 11 | 276 | defining-formula | Gamma: $\Gamma = \partial^2 C / \partial S^2$ | [uncited] | | | Standard Greek definition |
| 12 | 277 | defining-formula | Theta: $\Theta = \partial C / \partial T$ | [uncited] | | | Standard Greek definition |
| 13 | 278 | defining-formula | Vega: $\mathcal{V} = \partial C / \partial \sigma$ | [uncited] | | | Standard Greek definition |
| 14 | 279 | defining-formula | Rho: $\rho = \partial C / \partial r$ | [uncited] | | | Standard Greek definition |
| 15 | 333-335 | qualitative | Vega peaks at-the-money and falls off for deep ITM or OTM options | [uncited] | | | Standard result from BS vega formula |
| 16 | 334 | qualitative | Longer-dated options have higher vega and a wider peak | [uncited] | | | Standard result |
| 17 | 358-362 | defining-formula | Implied volatility $\sigma_{\text{imp}}$ defined by $C_{\text{mkt}} = C_{\text{BS}}(S, K, r, T, \sigma_{\text{imp}})$ | [uncited] | | | Standard definition |
| 18 | 369 | qualitative | There is no closed-form solution for $\sigma_{\text{imp}}$; it must be found numerically | [uncited] | | | Well-known property |
| 19 | 373 | attribution | Implied volatility described as "the wrong number to put in the wrong formula to get the right price" | \citep{Rebonato2004} | | | Verify this is from Rebonato's 2004 book |
| 20 | 377 | qualitative | Sellers of options demand compensation for bearing tail risk, inflating IV above expected realized vol | [uncited] | | | Variance risk premium concept |
| 21 | 388 | attribution | IV is one of the strongest single features for predicting future realized vol | \citep{Gu2020} | | | |
| 22 | 396 | numerical-fact | Worked example: solving $C_{\text{BS}}(100, 105, 0.05, 0.25, \sigma) = 3.10$ yields $\sigma_{\text{imp}} \approx 23.5\%$ | [uncited] | | | Numerical check needed |
| 23 | 407-409 | defining-formula | Newton-Raphson for IV: $\sigma_{n+1} = \sigma_n - (C_{\text{BS}}(\sigma_n) - C_{\text{mkt}}) / \mathcal{V}(\sigma_n)$ | [uncited] | | | Standard numerical method |
| 24 | 414 | supporting-formula | Black-Scholes vega: $\mathcal{V}(\sigma_n) = S\sqrt{T} N'(d_1)$ with $N'(x) = (1/\sqrt{2\pi})e^{-x^2/2}$ | [uncited] | | | Standard BS vega formula |
| 25 | 423 | qualitative | Newton-Raphson converges quadratically; 3-5 iterations typically suffice | [uncited] | | | Standard property of Newton-Raphson |
| 26 | 427-429 | attribution | Brenner and Subrahmanyam (1988) provide a closed-form ATM IV approximation: $\sigma_0 \approx \sqrt{2\pi/T} \cdot C_{\text{mkt}}/S$ | \citet{BrennerSubrahmanyam1988} | | | |
| 27 | 431 | supporting-formula | ATM Black-Scholes call price is approximately $C \approx S\sigma\sqrt{T/(2\pi)}$ | [uncited] | | | The Brenner-Subrahmanyam approximation rearranged |
| 28 | 435-436 | qualitative | Vega approaches zero for deep ITM and deep OTM options | [uncited] | | | Standard BS vega property |
| 29 | 464-469 | defining-formula | IV surface: $\sigma_{\text{imp}}(K, T)$ mapping each (strike, maturity) pair to implied volatility | [uncited] | | | Standard definition |
| 30 | 479-481 | qualitative | If Black-Scholes were correct, every option on the same underlying would produce the same IV regardless of strike or maturity (flat surface) | [uncited] | | | Direct consequence of constant-vol assumption |
| 31 | 547 | qualitative | The equity skew pattern (higher IV for low strikes) emerged after the 1987 crash and has persisted ever since | [uncited] | | | Widely known empirical fact |
| 32 | 548 | qualitative | The skew reflects the market's pricing of left-tail (crash) risk: investors pay a premium for downside protection | [uncited] | | | Standard market microstructure explanation |
| 33 | 550-551 | qualitative | For FX options, IV is elevated for both deep OTM puts and OTM calls (symmetric smile) | [uncited] | | | Standard empirical observation |
| 34 | 563 | qualitative | Normal conditions: IV term structure slopes upward (long-dated IV > short-dated IV) | [uncited] | | | Standard empirical observation |
| 35 | 564 | qualitative | Crisis periods: IV term structure inverts (short-dated IV > long-dated IV) | [uncited] | | | Standard empirical observation |
| 36 | 565 | qualitative | Short-dated IV is more volatile than long-dated IV, consistent with mean-reverting volatility | [uncited] | | | Standard empirical observation |
| 37 | 636-637 | defining-formula | Butterfly spread: $\mathrm{BF}_t = \frac{1}{2}(\sigma_{25\Delta P} + \sigma_{25\Delta C}) - \sigma_{\mathrm{ATM}}$ | [uncited] | | | Standard options market convention |
| 38 | 646 | qualitative | The butterfly is always non-negative in a no-arbitrage market (negative would imply concave smile, violating convexity constraints) | [uncited] | | | Theoretical no-arbitrage constraint |
| 39 | 658-659 | defining-formula | Risk reversal: $\mathrm{RR}_t = \sigma_{25\Delta C} - \sigma_{25\Delta P}$ | [uncited] | | | Standard options market convention |
| 40 | 663-666 | supporting-formula | Wing reconstruction: $\sigma_{25\Delta P} = \sigma_{\mathrm{ATM}} + \mathrm{BF}_t - \frac{1}{2}\mathrm{RR}_t$ and $\sigma_{25\Delta C} = \sigma_{\mathrm{ATM}} + \mathrm{BF}_t + \frac{1}{2}\mathrm{RR}_t$ | [uncited] | | | Algebraic consequence of BF and RR definitions |
| 41 | 667 | qualitative | Risk reversal captures directional asymmetry (skewness demand); butterfly captures symmetric tail thickness (kurtosis demand) | [uncited] | | | Standard interpretation |
| 42 | 672 | qualitative | In equities, the risk reversal is persistently negative (OTM puts more expensive than OTM calls) | [uncited] | | | Standard empirical fact |
| 43 | 767 | attribution | The SVI parametrization is the industry standard for equity index surfaces | \citep{GatheralJacquier2014} | | | |
| 44 | 771-773 | defining-formula | Raw SVI: $w(k) = a + b\{\rho(k-m) + \sqrt{(k-m)^2 + \sigma^2}\}$ where $w(k) = \sigma_{\text{imp}}^2(k) \cdot T$ and $k = \ln(K/F)$ | \citep{GatheralJacquier2014} | | | |
| 45 | 783 | supporting-formula | SVI non-negativity constraint: $a + b\sigma\sqrt{1-\rho^2} \geq 0$ ensures $w(k) \geq 0$ for all $k$ | \citep{GatheralJacquier2014} | | | |
| 46 | 797 | qualitative | As $|k| \to \infty$, SVI $w(k)$ becomes linear in $k$, matching Roger Lee's moment formula | \citep{GatheralJacquier2014} | | | Verify Lee's moment formula reference |
| 47 | 798 | qualitative | The large-maturity limit of the Heston stochastic volatility model's implied variance is exactly SVI | \citep{GatheralJacquier2014} | | | |
| 48 | 821 | qualitative | A naive SVI fit can produce calendar spread arbitrage (total variance decreasing with maturity at some strikes) | \citep{GatheralJacquier2014} | | | |
| 49 | 821-822 | attribution | Gatheral and Jacquier (2014) provide sufficient conditions for arbitrage-free SVI surfaces | \citep{GatheralJacquier2014} | | | |
| 50 | 822 | methodological | For a surface (not just a single slice), use the SSVI extension, which guarantees no static arbitrage under simple parameter constraints | \citep{GatheralJacquier2014} | | | |
| 51 | 834 | attribution | Cont and da Fonseca (2002) applied PCA to the daily changes of S&P 500 implied volatility surfaces | \citet{Cont2002} | | | Verify this is Cont and da Fonseca 2002 |
| 52 | 846-847 | numerical-fact | PCA PC1 (level): ~70% of variance; parallel shift of the entire surface | \citet{Cont2002} | | | |
| 53 | 848 | numerical-fact | PCA PC2 (slope): ~15% of variance; skew steepens or flattens | \citet{Cont2002} | | | |
| 54 | 849 | numerical-fact | PCA PC3 (curvature): ~10% of variance; smile convexity changes | \citet{Cont2002} | | | |
| 55 | 851 | numerical-fact | Three PCA factors together explain roughly 95% of daily surface variation | \citet{Cont2002} | | | |
| 56 | 916-917 | attribution | The local volatility / Dupire formula key result is due to Dupire (1994) | \citet{Dupire1994} | | | |
| 57 | 918-919 | defining-formula | Dupire formula: $\sigma_{\text{loc}}^2(K,T) = [\partial C/\partial T + rK \partial C/\partial K] / [\frac{1}{2}K^2 \partial^2 C/\partial K^2]$ | \citet{Dupire1994} | | | |
| 58 | 964-966 | numerical-fact | Worked example: $\partial C/\partial T \approx (7.95 - 5.60)/0.25 = 9.40$ | [uncited] | | | Numerical check |
| 59 | 970-973 | numerical-fact | Worked example: $\partial C/\partial K \approx (1.80 - 12.85)/20 = -0.5525$ | [uncited] | | | Numerical check |
| 60 | 977-979 | numerical-fact | Worked example: $\partial^2 C/\partial K^2 \approx (1.80 - 11.20 + 12.85)/100 = 0.0345$ | [uncited] | | | Numerical check: $2 \times C(100,0.25) = 2 \times 5.60 = 11.20$ |
| 61 | 983-989 | numerical-fact | Worked example: Numerator $= 9.40 - 1.105 = 8.295$; Denominator $= 172.5$; $\sigma_{\text{loc}}^2 = 0.0481$; $\sigma_{\text{loc}} = 21.9\%$ | [uncited] | | | Numerical check: $0.02 \times 100 \times 0.5525 = 1.105$; $0.5 \times 10000 \times 0.0345 = 172.5$; $8.295/172.5 = 0.04809$; $\sqrt{0.04809}=0.2193$ |
| 62 | 1036 | attribution | Britten-Jones and Neuberger (2000) proved model-free implied variance result | \citet{BrittenJones2000} | | | |
| 63 | 1048-1051 | defining-formula | Model-free implied variance: $E^Q[\int_0^T \sigma_t^2 dt] = (2/T)\int_0^\infty C(K,T)/K^2 dK + (2/T)\int_0^\infty P(K,T)/K^2 dK$ | \citet{BrittenJones2000} | | | Verify exact form; some formulations use OTM options only |
| 64 | 1082 | attribution | VIX implements the model-free approach of Britten-Jones and Neuberger (2000) on S&P 500 options with a 30-day horizon | \citet{BrittenJones2000} | | | CBOE credits Demeterfi et al. (1999) and Carr-Madan more directly |
| 65 | 1087-1089 | defining-formula | VIX formula: $\text{VIX}^2 = (2/T)\sum_i (\Delta K_i / K_i^2) e^{rT} Q(K_i) - (1/T)(F/K_0 - 1)^2$ | \citep{CBOE2019} | | | |
| 66 | 1115 | attribution | VIX is often the strongest univariate predictor of future realized vol | \citep{Gu2020} | | | |
| 67 | 1127 | numerical-fact | 2008 financial crisis VIX peak: ~80; March 2020 VIX peak: ~82 | [uncited] | | | Verify exact peaks: Oct 2008 VIX intraday ~89.53, closing ~80.86; Mar 2020 intraday ~82.69 |
| 68 | 1137 | numerical-fact | VIX exceeds subsequent realized vol roughly 85% of the time | \citep{Carr2009} | | | |
| 69 | 1150-1151 | supporting-formula | Daily vol from VIX: $\sigma_{\text{daily}} \approx 0.22/\sqrt{252} \approx 0.0139 = 1.39\%$ | [uncited] | | | Numerical check: $\sqrt{252} \approx 15.875$; $0.22/15.875 \approx 0.01386$ |
| 70 | 1182-1183 | defining-formula | Variance swap payoff: $\text{Payoff} = N_{\text{var}} \times (\text{RV}^2 - K_{\text{var}})$ | [uncited] | | | Standard definition |
| 71 | 1205-1206 | supporting-formula | Vega notional: $N_{\text{vega}} = N_{\text{var}} \times 2\sqrt{K_{\text{var}}}$ | [uncited] | | | Standard variance swap convention |
| 72 | 1208 | numerical-fact | If $K_{\text{var}} = 0.04$ (20% vol) and $N_{\text{vega}} = \$100{,}000$, then $N_{\text{var}} = 100{,}000/(2 \times 0.20) = \$250{,}000$ | [uncited] | | | Numerical check |
| 73 | 1212 | attribution | Britten-Jones and Neuberger (2000) and Carr and Wu (2009) showed that continuously delta-hedging a $1/K^2$-weighted OTM portfolio replicates $-2\log(S_T/S_0)$ | \citet{BrittenJones2000}, \citet{Carr2009} | | | Log-contract replication |
| 74 | 1216-1217 | qualitative | VIX formula computes the fair strike of a 30-day variance swap on the S&P 500; $\text{VIX}^2/10{,}000$ is the annualized $K_{\text{var}}$ | [uncited] | | | Standard interpretation |
| 75 | 1256-1259 | numerical-fact | Worked example: sum of weighted OTM option prices $= 0.000344 + 0.000623 + 0.001173 + 0.002327 + 0.003539 + 0.003076 + 0.001678 + 0.000661 + 0.000227 + 0.000069 = 0.01372$ | [uncited] | | | Numerical check of sum |
| 76 | 1264 | numerical-fact | Worked example: $K_{\text{var}}^{\text{ann}} = 0.01372/0.08219 \approx 0.0389$; implied vol $= \sqrt{0.0389} \approx 19.7\%$ | [uncited] | | | Numerical check: $30/365 = 0.08219$; verify division and sqrt |
| 77 | 1239-1249 | numerical-fact | Worked example: individual weight computations (e.g., $2 \times 5/80^2 = 0.001563$; $2 \times 5/85^2 = 0.001384$; etc.) and contributions | [uncited] | | | Verify all 10 weight and contribution calculations |
| 78 | 1280 | numerical-fact | Trading example: $N_{\text{var}} \times (0.22^2 - 0.19^2) = N_{\text{var}} \times 0.0123$ | [uncited] | | | Numerical check: $0.0484 - 0.0361 = 0.0123$ |
| 79 | 1286 | supporting-formula | $E[\sigma] < \sqrt{E[\sigma^2]}$ (Jensen's inequality), so vol swap strike is lower than $\sqrt{K_{\text{var}}}$ | [uncited] | | | Standard application of Jensen's inequality |
| 80 | 1310 | attribution | VIX level is often the strongest univariate predictor of future realized vol | \citep{Gu2020} | | | Repeated claim from line 1115 |
