# Unverified Claims -- Papers Needed

**Total unverified: 105 claims across 13 chapters**

Claims below could not be verified because the cited source paper is not available locally. All are consistent with secondary sources and standard results.

---

## By Missing Paper

### ABDL2001 -- Andersen, Bollerslev, Diebold, Labys (2001) (2 claims)
- Ch 2, Claim 34: Noise model $p^*_{t,i} = p_{t,i} + \varepsilon_{t,i}$ (attribution to ABDL2001 for the additive noise model)
- Ch 2, Claim 40: Convention that RV denotes realized variance, $\sqrt{RV}$ realized volatility (attribution to ABDL2001)

### ABDL2003 -- Andersen, Bollerslev, Diebold, Labys (2003) (3 claims)
- Ch 2, Claim 8: No mean subtraction in RV: omitting the sample mean of intraday returns improves finite-sample performance
- Ch 2, Claim 40: Convention that RV denotes realized variance (joint attribution with ABDL2001)
- Ch 2, Claim 41: $\ln(RV_t)$ is approximately Gaussian (attribution to ABDL2001/ABDL2003)

### BNS2002 -- Barndorff-Nielsen, Shephard (2002) (2 claims)
- Ch 2, Claim 34: Noise model attribution (joint with ABDL2001)
- Ch 2, Claim 40: RV convention attribution (joint with ABDL2001/ABDL2003)

### LPS2015 -- Liu, Patton, Sheppard (2015) (1 claim)
- Ch 2, Claim 37: Compared ~400 RV estimators across 31 assets in 5 asset classes; conclusion that simple 5-minute RV is very hard to beat for forecasting

### HansenLunde2006 -- Hansen, Lunde (2006) (4 claims)
- Ch 3, Claim 2: Bid-ask bounce is the dominant source of noise for most liquid assets
- Ch 3, Claim 10a: $E[RV_t^{(\text{noisy})}] = IV_t + 2n\omega^2$ (attribution)
- Ch 3, Claim 14: The simple i.i.d. noise model is a useful first approximation for liquid stocks
- Ch 3, Claim 17: For less liquid instruments, the noise-contaminated region can extend to 15 or even 30 minutes

### AitSahaliaMyklandZhang2005 -- Ait-Sahalia, Mykland, Zhang (2005) (1 claim)
- Ch 3, Claim 4: Price staleness creates spurious autocorrelation in returns

### ZhangMyklandAitSahalia2005 -- Zhang, Mykland, Ait-Sahalia (2005) (2 claims)
- Ch 3, Claim 20: TSRV formula: $\widehat{IV}_t^{TSRV} = RV^{(\text{avg},K)}_t - (\bar{n}_K / n) RV^{(\text{all})}_t$
- Ch 3, Claim 21: $\bar{n}_{K} = (n - K + 1)/K$ (averaging formula for TSRV)

### Zhang2006 -- Zhang (2006) (3 claims)
- Ch 3, Claim 35: MSRV formula: $\widehat{IV}_t^{MSRV} = \sum_{j=1}^{J} a_j RV^{(\text{avg},K_j)}_t$
- Ch 3, Claim 36: The optimal $J$ grows with $n$
- Ch 3, Claim 37: MSRV weights satisfy $\sum_j a_j = 1$ and a second constraint that cancels the $\omega^2$ bias

### BNHLS2008 -- Barndorff-Nielsen, Hansen, Lunde, Shephard (2008) (1 claim)
- Ch 3, Claim 46: Realized kernel formula: $\widehat{K}_t = \sum_{h=-H}^{H} k(h/(H+1)) \hat{\gamma}_h$

### JacodLiMyklandPodolskijVetter2009 -- Jacod, Li, Mykland, Podolskij, Vetter (2009) (3 claims)
- Ch 3, Claim 54: Pre-averaged price formula: $\bar{p}^*_{t,i} = \sum_{j=1}^{L-1} g(j/L) \Delta p^*_{t,i+j}$
- Ch 3, Claim 55: Pre-averaged realized variance formula
- Ch 3, Claim 56: $\psi_1 = \int_0^1 [g'(x)]^2 dx$ and $\psi_2 = \int_0^1 [g(x)]^2 dx$

### MalliavinMancino2002/2009 -- Malliavin, Mancino (2002, 2009) (2 claims)
- Ch 3, Claim 60a: Fourier estimator attribution (2002 paper)
- Ch 3, Claim 60b: Fourier estimator attribution (2009 paper)

### CorsiPirinoReno2010 -- Corsi, Pirino, Reno (2010) (3 claims)
- Ch 6, Claim 30: HAR-CJ model attribution
- Ch 6, Claim 31: HAR-CJ model formula (six-coefficient decomposition of continuous and jump components at three horizons)
- Ch 6, Claim 34: Continuous coefficients are large/significant; jump coefficients are small/often insignificant at weekly and monthly horizons

### AudrinoKnaus2016 -- Audrino, Knaus (2016) (2 claims)
- Ch 6, Claim 51: "Lassoing the HAR" approach (attribution and Lasso-HAR applied to HAR-X)
- Ch 6, Claim 52: Lasso-HAR formula with $\lambda$ penalty on exogenous coefficients only

### BollerslevEtAl2018 -- Bollerslev, Li, Xue (2018) (1 claim)
- Ch 6, Claim 50: "Risk Everywhere" paper with large cross-section of HAR-X type models

### BLP2022 -- Bollerslev, Li, Patton (2022) (3 claims)
- Ch 7, Claim 29: BLP2022 extend GJR2018 analysis to a broad cross-section of asset classes
- Ch 7, Claim 30a/30b: BLP2022 cover equities, indices, FX, fixed income, commodities; confirm H ~ 0.1 is universal
- Ch 7, Claim 31: Hurst exponent does not vary meaningfully across asset classes, geographies, or time periods

### Corsi2009 -- Corsi (2009) (3 claims)
- Ch 7, Claim 41: HAR $\beta_d \approx 0.36$
- Ch 7, Claim 42: HAR $\beta_w \approx 0.28$
- Ch 7, Claim 43: HAR $\beta_m \approx 0.28$

### Gu2020 -- Gu, Kelly, Xiu (2020) (3 claims)
- Ch 8, Claim 1: VIX and IV-derived features appear in virtually every competitive feature set for RV forecasting
- Ch 8, Claim 21: IV is one of the strongest single features for predicting future realized vol
- Ch 8, Claim 66/80: VIX level is often the strongest univariate predictor of future realized vol

### Rebonato2004 -- Rebonato (2004) (1 claim)
- Ch 8, Claim 19: IV described as "the wrong number to put in the wrong formula to get the right price"

### BrennerSubrahmanyam1988 -- Brenner, Subrahmanyam (1988) (1 claim)
- Ch 8, Claim 26: ATM IV approximation: $\sigma_0 \approx \sqrt{2\pi/T} \cdot C_{mkt}/S$

### Cont2002 -- Cont, da Fonseca (2002) (5 claims)
- Ch 8, Claim 51: PCA applied to daily changes of S&P 500 IV surfaces (attribution)
- Ch 8, Claim 52: PC1 (level): ~70% of variance
- Ch 8, Claim 53: PC2 (slope): ~15% of variance
- Ch 8, Claim 54: PC3 (curvature): ~10% of variance
- Ch 8, Claim 55: Three PCA factors together explain ~95% of daily surface variation

### Dupire1994 -- Dupire (1994) (1 claim)
- Ch 8, Claim 56: Local volatility / Dupire formula attribution

### BrittenJones2000 -- Britten-Jones, Neuberger (2000) (2 claims)
- Ch 8, Claim 62: Model-free implied variance result (attribution)
- Ch 8, Claim 73: Replication of $-2\log(S_T/S_0)$ via delta-hedging a $1/K^2$-weighted OTM portfolio (joint with Carr2009)

### Carr2009 -- Carr, Wu (2009) (3 claims)
- Ch 8, Claim 68: VIX exceeds subsequent realized vol roughly 85% of the time
- Ch 8, Claim 73: Log-contract replication result (joint with BrittenJones2000)
- Ch 9, Claim 61: VIX exceeds subsequent realized vol ~85% of the time (duplicate)

### BTZ2009 -- Bollerslev, Tauchen, Zhou (2009) (1 claim)
- Ch 9, Claim 22: One-standard-deviation VRP increase predicts ~3-4% higher quarterly excess returns (specific magnitude could not be confirmed)

### Bennett2014 -- Bennett (2014) "Trading Volatility" (2 claims)
- Ch 10, Claim 50: Front-month VIX future has ~90% delta to spot VIX; 6-month future has ~55%
- Ch 10, Claim 51: When VIX spikes above 40, the 6-month future barely moves

### EasleyLopezOHara2012 -- Easley, Lopez de Prado, O'Hara (2012) VPIN (3 claims)
- Ch 10, Claim 26: VPIN attribution (PDF in reference directory is wrong file)
- Ch 10, Claim 27: VPIN formula
- Ch 10, Claim 28: $n = 50$ volume buckets per estimation window

### RahimikiaZohrenPoon2021 -- Rahimikia, Zohren, Poon (2021) (1 claim)
- Ch 10, Claim 73: Transformer-based NLP models (FinBERT) for sentiment extraction (attribution)

### AudrinoSignristBallinari2020 + RahimikiaZohrenPoon2021 (1 claim)
- Ch 10, Claim 74: Text-derived sentiment adds 1-3% QLIKE improvement over HAR-family baselines

### SirignanoCont2019 -- Sirignano, Cont (2019) (4 claims)
- Ch 12, Claim 19: Universal LSTM trained on pooled data across 1,000+ stocks
- Ch 12, Claim 21: Pooling works because volatility dynamics are similar across assets
- Ch 12, Claim 22: Pooled model outperforms asset-specific models, especially for assets with short histories
- Ch 15, Claim 41a-42b: (Fixed claims about asset classes/features -- but underlying paper still unavailable for direct verification)

### RosenbaumZhang2022 -- Rosenbaum, Zhang (2022) (6 claims)
- Ch 12, Claim 24: LSTMs connected directly to rough volatility (attribution)
- Ch 12, Claim 25: Universal LSTM learns a kernel matching the RFSV fractional kernel
- Ch 12, Claim 26: LSTM learns the power-law kernel $K(t) \propto t^{H-1/2}$ with $H \approx 0.1$
- Ch 12, Claim 27: LSTM and RFSV forecast are nearly identical
- Ch 12, Claim 28: LSTM discovers roughness from data alone with no prior knowledge
- Ch 12, Claim 30: LSTM incorporating LOB features and news sentiment beats HAR on ~90% of trading days (attributed to RahimikiaPoon2020)

### RahimikiaPoon2020 -- Rahimikia, Poon (2020) (8 claims)
- Ch 12, Claim 30: LSTM beats HAR on ~90% of trading days
- Ch 12, Claim 31: Model fails during extreme stress events
- Ch 12, Claim 32: Underperforms HAR during high-vol episodes due to few training events
- Ch 13, Claim 1: Hybrid models are "the safest bet" in vol forecasting
- Ch 13, Claim 2: Hybrid "almost always outperforms either component alone"
- Ch 13, Claim 3: Fitted HAR explains 40-60% of next-day RV with three coefficients
- Ch 13, Claim 4: Combining weakly correlated forecasters reduces variance
- Ch 13, Claim 5: SVR focuses on days where HAR fails most

### ZhangZohrenRoberts2019DeepLOB -- Zhang, Zohren, Roberts (2019) (4 claims)
- Ch 12, Claim 57: 4 features per level (price, volume, price diff from mid, volume diff from mid)
- Ch 12, Claim 59: Prediction horizons k = 10, 20, 50 ticks
- Ch 12, Claim 60: Convolutional layers learn features resembling but improving on classical order imbalance
- Ch 12, Claim 61: DeepLOB generalizes across stocks without retraining

### DingLuCheung2025 -- Ding, Lu, Cheung (2025) (2 claims)
- Ch 12, Claim 79: Autoencoders to compress IV surface into latent space (attribution)
- Ch 12, Claim 80: Typical latent dimensions $d = 3$ to $8$, compressing $20 \times 10 = 200$ values

### XuChen2021 -- Xu, Chen (2021) (1 claim)
- Ch 12, Claim 82: Deep stochastic volatility model combining SV with neural networks, VAE-like inference

### DuMoriyamaTanakaIshii2023 -- Du, Moriyama, Tanaka, Ishii (2023) (1 claim)
- Ch 12, Claim 83: Normalizing flows co-trained with VAE to model full RV distribution

### GINN2024 -- GINN (2024) (5 claims)
- Ch 13, Claim 10: GINN hard-wires GARCH recursion into neural network architecture
- Ch 13, Claim 12: GINN time-varying parameter equation
- Ch 13, Claim 13: Small feedforward network, 2 hidden layers, 32-64 units
- Ch 13, Claim 14: Parameter constraints via softmax and sigmoid output activations
- Ch 13, Claim 15: GINN matches or outperforms GARCH and LSTMs on equity index vol

### GINN2024 (continued) (1 claim)
- Ch 13, Claim 16: GINN uses substantially fewer parameters than LSTM

### RahimikiaZohrenPoon2021NLP (1 claim)
- Ch 13, Claim 25: NLP improvement does not survive aggressive transaction costs

### Optiver2021 -- Optiver Kaggle Competition (2021) (2 claims)
- Ch 13, Claim 40: Top solutions consistently chose prediction blending over feature stacking
- Ch 13, Claim 41: Rationale: easier to debug, iterate, natural fallback

### HayashiYoshida2005 -- Hayashi, Yoshida (2005) (1 claim)
- Ch 14, Claim 9: HY estimator is unbiased and consistent under mild conditions

### BarndorffNielsenHansenLundeShephard2011 -- BNHLS (2011) (4 claims)
- Ch 14, Claim 17: Multivariate realized kernel formula
- Ch 14, Claim 18: Cross-autocovariance matrix definition
- Ch 14, Claim 19: Kernel function conditions $k(0)=1$, $k(1)=0$
- Ch 14, Claim 20: PSD guarantee with non-negative kernel; handles noise and non-synchronous trading

### BarndorffNielsenHansenLundeShephard2011 (continued) (1 claim)
- Ch 14, Claim 21: Rate of convergence $M^{-1/5}$

### Engle2002DCC -- Engle (2002) (2 claims)
- Ch 14, Claim 24: DCC quasi-correlation dynamics formula
- Ch 14, Claim 26: Stationarity condition $\alpha + \beta < 1$

### ZhangPuCucuringuDong2024 -- Zhang, Pu, Cucuringu, Dong (2024) (2 claims)
- Ch 14, Claim 54: Graph-HAR formula with graph-weighted spillover term
- Ch 14, Claim 56: Adjacency matrix $W$ typically from thresholded correlation or LASSO partial correlation

### HansenLundeNason2011 -- Hansen, Lunde, Nason (2011) (2 claims)
- Ch 16, Claim 41: MCS coverage property: $\Pr(\mathcal{M}^* \subseteq \widehat{\mathcal{M}}^*_\alpha) \geq 1 - \alpha$
- Ch 16, Claim 42: MCS controls familywise error rate

### HarveyLeybourneNewbold1997 -- Harvey, Leybourne, Newbold (1997) (1 claim)
- Ch 16, Claim 38: Modified DM statistic with $t$-distribution and finite-sample correction

### HarveyLiu2015 -- Harvey, Liu (2015) (1 claim)
- Ch 16, Claim 62: Haircut Sharpe ratio correction for multiple testing

### Ch 5 uncited claims (3 claims)
- Ch 5, Claim 28: Adding an asymmetry term typically improves QLIKE by 5-15% (no citation given)
- Ch 5, Claim 46: Noise-to-signal ratio for $r^2_t$ as daily variance estimator exceeds 5 (no citation given)
- Ch 5, Claim 55: HAR often matches or beats Realized GARCH for RV forecasting (no citation given)

### Ch 9 uncited claims (2 claims)
- Ch 9, Claim 34: VRP gap closes from both sides, with realized vol doing more of the adjustment
- Ch 9, Claim 62: 15% of months where realized vol exceeds VIX are concentrated in sudden-onset crises

---

## By Chapter

### Ch 1: Returns, Variance, and Why Volatility Matters (0 unverified)

All 52 claims verified.

---

### Ch 2: Realized Volatility (5 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 8 | methodological | No mean subtraction in RV improves finite-sample performance | ABDL2003 | Consistent with all four available papers using same convention |
| 34 | defining-formula | Additive noise model $p^* = p + \varepsilon$ | ABDL2001, BNS2002 | Canonical model used universally |
| 37 | attribution | LPS2015: ~400 estimators, 31 assets, 5-min RV hard to beat | LPS2015 | Widely cited finding; title confirms |
| 40 | attribution | RV/sqrt(RV) convention follows ABDL2003, BNS2002 | ABDL2003, BNS2002 | Standard convention confirmed indirectly |
| 41 | qualitative | $\ln(RV_t)$ is approximately Gaussian | ABDL2001, ABDL2003 | Foundation of LogHAR; universally cited |

---

### Ch 3: Microstructure Noise and Robust Estimators (14 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 2 | qualitative | Bid-ask bounce is the dominant noise source for liquid assets | HansenLunde2006 | Standard microstructure knowledge |
| 4 | qualitative | Price staleness creates spurious return autocorrelation | AitSahaliaMyklandZhang2005 | Standard result |
| 10a | attribution | $E[RV^{noisy}] = IV + 2n\omega^2$ (HL06 attribution) | HansenLunde2006 | Derivable from first principles |
| 10b | attribution | Same formula (AMZ05 attribution) | AitSahaliaMyklandZhang2005 | Derivable from first principles |
| 14 | qualitative | i.i.d. noise model is useful first approximation | HansenLunde2006 | Widely accepted |
| 17 | methodological | Noise-contaminated region extends to 15-30 min for illiquid instruments | HansenLunde2006 | Standard practitioner knowledge |
| 20 | defining-formula | TSRV formula | ZhangMyklandAitSahalia2005 | Consistent with secondary sources |
| 21 | supporting-formula | TSRV averaging formula | ZhangMyklandAitSahalia2005 | Consistent with secondary sources |
| 35 | defining-formula | MSRV formula | Zhang2006 | Consistent with standard presentations |
| 36 | qualitative | Optimal $J$ grows with $n$ | Zhang2006 | Consistent with multi-scale construction |
| 37 | supporting-formula | MSRV weight constraints | Zhang2006 | Standard descriptions confirm |
| 46 | defining-formula | Realized kernel formula | BNHLS2008 | Consistent with standard presentations |
| 54 | defining-formula | Pre-averaged price formula | JLMPV2009 | Consistent with standard presentations |
| 55 | defining-formula | Pre-averaged realized variance formula | JLMPV2009 | Consistent with standard presentations |
| 56 | supporting-formula | Weight-function normalization constants $\psi_1$, $\psi_2$ | JLMPV2009 | Consistent with standard presentations |
| 60a | attribution | Fourier estimator (2002) | MalliavinMancino2002 | Standard attribution |
| 60b | attribution | Fourier estimator (2009) | MalliavinMancino2009 | Standard attribution |

---

### Ch 4: Jumps and Continuous Variation (0 unverified)

All 50 claims verified.

---

### Ch 5: The GARCH Family (3 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 28 | numerical-fact | Adding asymmetry term improves QLIKE by 5-15% | [uncited] | Plausible range but no empirical source |
| 46 | numerical-fact | Noise-to-signal ratio for $r^2_t$ exceeds 5 on average | [uncited] | General point well-established but specific threshold unconfirmed |
| 55 | qualitative | HAR often matches or beats Realized GARCH for RV forecasting | [uncited] | Plausible but no specific citation |

---

### Ch 6: The HAR Model and Its Extensions (6 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 30 | attribution | HAR-CJ model attribution | CorsiPirinoReno2010 | Corsi2009 p.193 references working paper version |
| 31 | defining-formula | HAR-CJ six-coefficient formula | CorsiPirinoReno2010 | Structure consistent with BPQ2016 |
| 34 | qualitative | Continuous coefficients large; jump coefficients small/insignificant | CorsiPirinoReno2010 | Consistent with BPQ2016, PSS2015 |
| 50 | attribution | "Risk Everywhere" paper | BollerslevEtAl2018 | CSV2023 cites this paper |
| 51 | attribution | "Lassoing the HAR" approach | AudrinoKnaus2016 | CSV2023 cites this paper |
| 52 | defining-formula | Lasso-HAR formula | AudrinoKnaus2016 | Standard Lasso applied to HAR-X |

---

### Ch 7: Rough Volatility (3 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 29 | attribution | BLP2022 extend GJR2018 to broad cross-section of asset classes | BLP2022 | PDF not available |
| 30a/30b | numerical-fact | BLP2022 cover equities, FX, fixed income, commodities; H ~ 0.1 universal | BLP2022 | PDF not available |
| 31 | qualitative | H does not vary meaningfully across asset classes/geographies/time | BLP2022 | PDF not available |
| 41 | numerical-fact | HAR $\beta_d \approx 0.36$ | Corsi2009 | PDF not available locally (used in Ch 7 context) |
| 42 | numerical-fact | HAR $\beta_w \approx 0.28$ | Corsi2009 | PDF not available locally (used in Ch 7 context) |
| 43 | numerical-fact | HAR $\beta_m \approx 0.28$ | Corsi2009 | PDF not available locally (used in Ch 7 context) |

---

### Ch 8: Options Basics and the Volatility Surface (12 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 1 | attribution | VIX and IV-derived features in virtually every competitive feature set | Gu2020 | Plausible given paper scope |
| 19 | attribution | "Wrong number in wrong formula to get right price" quote | Rebonato2004 | Widely attributed |
| 21 | attribution | IV is one of the strongest single features for predicting future RV | Gu2020 | Consistent with known literature |
| 26 | attribution | ATM IV approximation formula | BrennerSubrahmanyam1988 | Widely cited formula |
| 51 | attribution | PCA applied to S&P 500 IV surface changes | Cont2002 | Widely cited result |
| 52 | numerical-fact | PC1 (level): ~70% of variance | Cont2002 | Widely cited |
| 53 | numerical-fact | PC2 (slope): ~15% of variance | Cont2002 | Widely cited |
| 54 | numerical-fact | PC3 (curvature): ~10% of variance | Cont2002 | Widely cited |
| 55 | numerical-fact | Three factors explain ~95% of daily surface variation | Cont2002 | 70+15+10=95 |
| 56 | attribution | Local volatility / Dupire formula | Dupire1994 | Universally attributed |
| 62 | attribution | Model-free implied variance result | BrittenJones2000 | Universally attributed |
| 66/80 | attribution | VIX is strongest univariate predictor of future RV | Gu2020 | Consistent with literature |
| 68 | numerical-fact | VIX exceeds subsequent realized vol ~85% of time | Carr2009 | Widely cited statistic |
| 73 | attribution | Log-contract replication via delta-hedging | BrittenJones2000, Carr2009 | Standard replication result |

---

### Ch 9: The Variance Risk Premium (4 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 22 | numerical-fact | 1-SD VRP increase predicts ~3-4% higher quarterly excess returns | BTZ2009 | Could not locate exact magnitude |
| 34 | qualitative | VRP gap closes from both sides, realized vol adjusts more | [uncited] | Reasonable but no specific source |
| 61 | numerical-fact | VIX exceeds realized vol ~85% of the time | Carr2009 | Widely cited |
| 62 | qualitative | 15% of negative-VRP months concentrated in sudden-onset crises | Carr2009 | Cannot verify characterization |

---

### Ch 10: Feature Engineering for Volatility (6 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 26 | attribution | VPIN proposal (note: PDF in reference dir is wrong file) | EasleyLopezOHara2012 | Attribution correct; wrong PDF in reference |
| 27 | defining-formula | VPIN formula | EasleyLopezOHara2012 | Consistent with standard definition |
| 28 | numerical-fact | $n = 50$ volume buckets per VPIN estimation window | EasleyLopezOHara2012 | Commonly cited |
| 50 | numerical-fact | Front-month VIX future ~90% delta; 6-month ~55% | Bennett2014 | Widely cited in vol trading literature |
| 51 | qualitative | 6-month VIX future barely moves when VIX > 40 | Bennett2014 | Consistent with term structure dynamics |
| 73 | attribution | FinBERT for financial sentiment extraction | RahimikiaZohrenPoon2021 | Cannot verify against source |
| 74 | numerical-fact | Text sentiment adds 1-3% QLIKE improvement over HAR | Various | Neither paper available locally |

---

### Ch 11: Tree-Based Methods for Volatility (0 unverified)

All 62 claims verified.

---

### Ch 12: Deep Learning for Volatility (15 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 19 | numerical-fact | Universal LSTM trained on 1,000+ pooled stocks | SirignanoCont2019 | Number unconfirmable |
| 21 | qualitative | Pooling works because vol dynamics are similar across assets | SirignanoCont2019 | Plausible but unconfirmed |
| 22 | qualitative | Pooled model outperforms asset-specific, especially short histories | SirignanoCont2019 | Cannot verify |
| 24 | attribution | LSTMs connected to rough volatility | RosenbaumZhang2022 | Widely cited |
| 25 | qualitative | Universal LSTM learns kernel matching RFSV fractional kernel | RosenbaumZhang2022 | Widely cited |
| 26 | qualitative | LSTM learns power-law kernel $t^{H-1/2}$ with $H \approx 0.1$ | RosenbaumZhang2022 | Widely cited |
| 27 | qualitative | LSTM and RFSV forecast are nearly identical | RosenbaumZhang2022 | Cannot confirm strength |
| 28 | qualitative | LSTM discovers roughness from data alone | RosenbaumZhang2022 | Consistent with framing |
| 30 | numerical-fact | LSTM beats HAR on ~90% of trading days | RahimikiaPoon2020 | Cannot verify exact figure |
| 31 | qualitative | Model fails during extreme stress events | RahimikiaPoon2020 | Plausible, commonly observed |
| 32 | qualitative | Underperforms HAR in high-vol due to few training events | RahimikiaPoon2020 | Standard reasoning |
| 57 | methodological | DeepLOB 4 features per level (price, volume, diffs from mid) | ZhangZohrenRoberts2019 | Commonly cited but unconfirmed |
| 59 | numerical-fact | DeepLOB horizons k = 10, 20, 50 ticks | ZhangZohrenRoberts2019 | Cannot confirm exact set |
| 60 | qualitative | Conv layers learn features resembling classical order imbalance | ZhangZohrenRoberts2019 | Cannot confirm from primary |
| 61 | qualitative | DeepLOB generalizes across stocks without retraining | ZhangZohrenRoberts2019 | Cannot confirm |
| 79 | attribution | IV surface autoencoders | DingLuCheung2025 | 2025 paper not available |
| 80 | numerical-fact | Typical latent dims d = 3 to 8 | DingLuCheung2025 | Not available |
| 82 | attribution | Deep stochastic vol model with VAE inference | XuChen2021 | Not available |
| 83 | attribution | Normalizing flows for full RV distribution | DuMoriyamaTanakaIshii2023 | Not available |

---

### Ch 12-R: Rashomon Sets and Interpretable Trees (0 unverified)

All 79 claims verified.

---

### Ch 13: Hybrid and Ensemble Methods (16 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 1 | qualitative | Hybrid models are "the safest bet" in vol forecasting | RahimikiaPoon2020 | Paper not available |
| 2 | qualitative | Hybrid "almost always outperforms either component alone" | RahimikiaPoon2020 | Paper not available |
| 3 | numerical-fact | Fitted HAR explains 40-60% of next-day RV with three coefficients | RahimikiaPoon2020 | Not available; consistent with literature |
| 4 | qualitative | Combining weakly correlated forecasters reduces variance | RahimikiaPoon2020 | Mathematically standard |
| 5 | qualitative | SVR focuses on days where HAR fails most | RahimikiaPoon2020 | Paper not available |
| 10 | qualitative | GINN hard-wires GARCH recursion into neural network | GINN2024 | Paper not available |
| 12 | defining-formula | GINN time-varying parameter equation | GINN2024 | Not available |
| 13 | methodological | GINN: 2 hidden layers, 32-64 units | GINN2024 | Not available |
| 14 | methodological | GINN parameter constraints via softmax/sigmoid | GINN2024 | Not available |
| 15 | qualitative | GINN matches or outperforms GARCH and LSTMs | GINN2024 | Not available |
| 16 | qualitative | GINN uses fewer parameters than LSTM | GINN2024 | Not available |
| 25 | qualitative | NLP improvement does not survive transaction costs | RahimikiaZohrenPoon2021NLP | No transaction cost analysis in paper |
| 26 | qualitative | Hybrid econometric+text outperforms pure text | RahimikiaPoon2020 | Not available |
| 40 | qualitative | Optiver winners chose prediction blending | Optiver2021 | Kaggle solutions not available |
| 41 | qualitative | Rationale: easier to debug, iterate, natural fallback | Optiver2021 | Kaggle solutions not available |
| 47 | qualitative | "Earn the right to go pure ML" conditional recommendation | RahimikiaPoon2020 | Not available |

---

### Ch 14: Multivariate Volatility (9 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 9 | qualitative | HY estimator is unbiased and consistent under mild conditions | HayashiYoshida2005 | Standard result in HF literature |
| 17 | defining-formula | Multivariate realized kernel formula | BNHLS2011 | Standard formula |
| 18 | supporting-formula | Cross-autocovariance matrix definition | BNHLS2011 | Standard definition |
| 19 | qualitative | Kernel conditions $k(0)=1$, $k(1)=0$ | BNHLS2011 | Standard conditions |
| 20 | qualitative | PSD guarantee with non-negative kernel | BNHLS2011 | Key theoretical result |
| 21 | qualitative | Convergence rate $M^{-1/5}$ | BNHLS2011 | Standard rate |
| 24 | defining-formula | DCC quasi-correlation dynamics formula | Engle2002DCC | Standard DCC equation |
| 26 | qualitative | DCC stationarity condition $\alpha + \beta < 1$ | Engle2002DCC | Analogous to GARCH |
| 54 | defining-formula | Graph-HAR formula | ZhangPuCucuringuDong2024 | Cannot verify without paper |
| 56 | methodological | Adjacency matrix from thresholded correlation or LASSO | ZhangPuCucuringuDong2024 | Cannot verify |

---

### Ch 15: Volatility Spillovers and Connectedness (0 unverified)

All 51 claims verified.

---

### Ch 16: Forecast Evaluation (4 unverified)

| # | Type | Claim | Missing source | Notes |
|---|---|---|---|---|
| 38 | methodological | Modified DM statistic with $t$-distribution, finite-sample correction | HarveyLeybourneNewbold1997 | Standard attribution |
| 41 | defining-formula | MCS coverage property | HansenLundeNason2011 | Standard characterization |
| 42 | qualitative | MCS controls familywise error rate | HansenLundeNason2011 | Follows from coverage property |
| 62 | attribution | Haircut Sharpe ratio for multiple testing | HarveyLiu2015 | Standard attribution |

---

### Ch 17: Practical Applications and Project Roadmaps (0 unverified)

All 31 claims verified.

---

## Paper Acquisition Priority

Papers ranked by number of unverified claims they would resolve:

| Rank | Paper | Claims resolved | Chapters affected |
|---|---|---|---|
| 1 | RahimikiaPoon2020 | 8 | Ch 12, Ch 13 |
| 2 | GINN2024 | 6 | Ch 13 |
| 3 | SirignanoCont2019 | 4+ | Ch 12, Ch 15 |
| 4 | RosenbaumZhang2022 | 6 | Ch 7, Ch 12 |
| 5 | Cont2002 (Cont & da Fonseca) | 5 | Ch 8 |
| 6 | BNHLS2011 (multivariate) | 5 | Ch 14 |
| 7 | HansenLunde2006 | 4 | Ch 3 |
| 8 | ZhangZohrenRoberts2019 (DeepLOB) | 4 | Ch 12 |
| 9 | Gu2020 (Gu, Kelly, Xiu) | 3 | Ch 8 |
| 10 | BLP2022 | 3 | Ch 7 |
| 11 | Zhang2006 (MSRV) | 3 | Ch 3 |
| 12 | ABDL2003 | 3 | Ch 2 |
| 13 | CorsiPirinoReno2010 | 3 | Ch 6 |
| 14 | EasleyLopezOHara2012 (VPIN) | 3 | Ch 10 |
| 15 | JacodLiMyklandPodolskijVetter2009 | 3 | Ch 3 |
| 16 | Carr2009 (Carr & Wu) | 3 | Ch 8, Ch 9 |
| 17 | Engle2002DCC | 2 | Ch 14 |
| 18 | ZhangPuCucuringuDong2024 | 2 | Ch 14 |
| 19 | ABDL2001 | 2 | Ch 2 |
| 20 | BNS2002 | 2 | Ch 2 |
| 21 | AudrinoKnaus2016 | 2 | Ch 6 |
| 22 | Bennett2014 | 2 | Ch 10 |
| 23 | BrittenJones2000 | 2 | Ch 8 |
| 24 | DingLuCheung2025 | 2 | Ch 12 |
| 25 | MalliavinMancino2002/2009 | 2 | Ch 3 |
| 26 | Optiver2021 (Kaggle solutions) | 2 | Ch 13 |
| 27 | ZhangMyklandAitSahalia2005 (TSRV) | 2 | Ch 3 |
| 28 | AitSahaliaMyklandZhang2005 | 1 | Ch 3 |
| 29 | BNHLS2008 (univariate) | 1 | Ch 3 |
| 30 | BollerslevEtAl2018 | 1 | Ch 6 |
| 31 | BrennerSubrahmanyam1988 | 1 | Ch 8 |
| 32 | BTZ2009 | 1 | Ch 9 |
| 33 | Dupire1994 | 1 | Ch 8 |
| 34 | DuMoriyamaTanakaIshii2023 | 1 | Ch 12 |
| 35 | HarveyLeybourneNewbold1997 | 1 | Ch 16 |
| 36 | HarveyLiu2015 | 1 | Ch 16 |
| 37 | HansenLundeNason2011 (MCS) | 2 | Ch 16 |
| 38 | HayashiYoshida2005 | 1 | Ch 14 |
| 39 | LPS2015 | 1 | Ch 2 |
| 40 | Rebonato2004 | 1 | Ch 8 |
| 41 | RahimikiaZohrenPoon2021 | 1 | Ch 10 |
| 42 | XuChen2021 | 1 | Ch 12 |
