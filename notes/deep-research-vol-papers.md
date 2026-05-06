# ML for Realized Volatility Forecasting — Internship Project Landscape, Bibliography, and Direction Memo

## TL;DR
- **HAR-RV remains the benchmark you must beat, and beating it is genuinely hard**: in head-to-head comparisons on canonical equity indices, well-engineered ML usually delivers single-digit-percent QLIKE/MSE improvements at best, and on the 10-index Branco–Rubesam–Zevallos (2024) study no nonlinear ML model statistically outperforms a properly fitted HAR-X. The biggest, most replicable wins come from (i) measurement-error corrections (HARQ, Bollerslev-Patton-Quaedvlieg 2016), (ii) richer information sets (limit-order-book features per Rahimikia–Poon, options-implied features, cross-asset spillovers), and (iii) embedding the HAR structure inside a neural net rather than discarding it (HARNet, Reisenhofer-Bayer-Hautsch 2022; HEAVY/Realized GARCH families).
- **The most credible ML wins on RV are tabular**: gradient boosting (LightGBM/XGBoost) plus careful microstructure feature engineering — exactly the playbook that won the Optiver Realized Volatility Kaggle in 2021 — and Christensen–Siggaard–Veliyev (2023) show that even off-the-shelf ML beats HAR on DJIA constituents, with gains rising at longer horizons because ML approximates long memory better. Deep sequence models (LSTM/TCN/Transformer/N-BEATSx/PatchTST) are competitive but not consistently superior; their strongest case is on raw intraday signals (DeepVol, HARNet) where they bypass handcrafted realized measures.
- **Recommended internship path**: a hybrid HAR-augmented gradient-boosted model with options-implied + LOB + cross-asset features evaluated by Patton-robust QLIKE under Lopez-de-Prado purged CV, with one of two flagship "wow" extensions — either (a) a Rashomon-set analysis using TreeFARMS/SPLIT to enumerate near-optimal interpretable trees and produce *Variable Importance Clouds* (genuinely novel in finance, intellectually substantial, directly usable by a desk), or (b) a graph-neural-net cross-asset spillover forecaster (Zhang-Pu-Cucuringu-Dong 2025). See Project 3 in `notes/project-proposals.md`.

---

> **Bibliography**: extracted to `reference/bibliography.md`
> **Project proposals**: extracted to `notes/project-proposals.md`
> **Research index**: `notes/research-index.md`

---

# Key Findings (one-paragraph summary of the empirical state of play)

The HAR model of Corsi (2009) — a three-feature OLS regression of next-day RV on daily, weekly, and monthly RV averages — remains the dominant benchmark; per Clements & Preve (J. Banking & Finance 133:106285, 2021), Corsi (2009) had exceeded 2,100 Google Scholar citations as of July 2021. Among extensions, HARQ (Bollerslev-Patton-Quaedvlieg 2016) delivers the most reliable improvement (≈8% MSE / ≈6% QLIKE on S&P 500 vs HAR; ≈5% MSE on DJIA constituents) by exploiting time-varying measurement error in RV. Patton & Sheppard (2015) signed semi-variances and Andersen-Bollerslev-Diebold (2007) jump components add further marginal gains. ML evidence is mixed: Christensen-Siggaard-Veliyev (J. Financial Econometrics 2023) show ML beats HAR on DJIA constituents with gains rising at longer horizons, while Branco-Rubesam-Zevallos (J. Empirical Finance 2024) find no statistical outperformance of nonlinear ML over linear models on 10 global indices. The clearest wins come from richer information sets — Rahimikia-Poon (2020) report ML+LOB features beat HAR in 90% of out-of-sample days for 23 NASDAQ tickers — and from HAR-aware neural architectures: HARNet (Reisenhofer-Bayer-Hautsch 2022) reports an "average reduction of the median test MAE of about 11.74%" across SPX, FTSE 100, and DJI vs OLS-HAR baseline. Liu-Patton-Sheppard (2015) systematically show that 5-minute RV is "very hard to beat" as a benchmark realized measure across 31 assets and 5 asset classes. The rough-volatility paradigm of Gatheral-Jaisson-Rosenbaum (2018) — log-volatility behaving as fBm with H ≈ 0.1 — is now openly contested by Cont & Das (Sankhya B 86:191–223, 2024), who argue this roughness may be a microstructure-noise artefact.

---

# PART 1 — LANDSCAPE SURVEY

## A. Realized volatility — definitions, estimators, and the estimation problem

The story is one of progressively refined estimators of the *integrated variance* IV_t = ∫_{t-1}^t σ²_s ds of an Itô semimartingale, observed via discrete, noisy log-prices.

**Foundational estimators**
- **Classical realized variance (RV)**: RV_t^(Δ) = Σ r²_{t,i}. Andersen & Bollerslev (1998, *IER*) and Andersen, Bollerslev, Diebold & Labys (2001, 2003 *Econometrica*) plus Barndorff-Nielsen & Shephard (2002, *JRSS-B*) established that as Δ → 0, RV → IV in probability.
- **Bipower variation (BV)**: Σ |r_{t,i}||r_{t,i-1}| / μ_1². Barndorff-Nielsen & Shephard (2004, 2006) — robust to jumps, allowing decomposition QV = IV + Σ J². The bipower-variation jump test and the **Lee–Mykland (2008, *RFS*)** intraday jump test are the two standard tools; Aït-Sahalia & Jacod (2009, 2012) provide alternative tests based on power variation ratios.
- **Realized kernel (RK)**: Barndorff-Nielsen, Hansen, Lunde & Shephard (2008, *Econometrica* 76:1481–1536) introduced flat-top kernel weights of autocovariances of HF returns to neutralise i.i.d. and dependent noise. Multivariate version BNHLS (2011, *J. Econometrics*) for synchronised positive-semidefinite covariance estimation.
- **Two-scale and multi-scale estimators (TSRV/MSRV)**: Zhang, Mykland & Aït-Sahalia (2005, *JASA*); Zhang (2006). Combine subsampled RV at fast and slow frequencies to remove noise bias; MSRV achieves the optimal n^{-1/4} rate.
- **Pre-averaging**: Jacod, Li, Mykland, Podolskij & Vetter (2009); Christensen, Kinnebrock, Podolskij (2010) extend to covariances.
- **Fourier estimator**: Malliavin & Mancino (2009, *Annals of Statistics*) — works directly in frequency domain.

**Microstructure noise**: high-frequency mid-quotes contain bid-ask bounce, discreteness, and latency noise. Naive RV at very high frequency is upward-biased (sum of squared noise dominates). Hansen & Lunde (2006, *JBES*) "Realized Variance and Market Microstructure Noise" formalises the bias-variance trade-off; the volatility signature plot (RV vs. sampling frequency) is the diagnostic. Bandi & Russell (2008) study the optimal sampling frequency. **Liu, Patton & Sheppard (2015, *J. Econometrics* 187:293–311)** compare nearly 400 estimators across 31 assets and conclude in their abstract: "When 5-minute RV is taken as the benchmark realized measure, we find little evidence that it is outperformed by any of the other measures." For forecasting they find "a low frequency 'truncated' RV outperforms most other realized measures. Overall, we conclude that it is difficult to significantly beat 5-minute RV." Their MCS contained 40 estimators on average (≈11% of the universe).

**Jump detection / decomposition**: BNS bipower test, Lee–Mykland (2008) intraday test (the workhorse for academic event studies), Aït-Sahalia & Jacod (2009, *Annals of Statistics*); Andersen, Bollerslev & Diebold (2007 *RES*) "Roughing It Up…" decompose RV = continuous + jump and show the jump component is highly important and less persistent — driving HAR-RV-J / HAR-RV-CJ extensions.

**Forecast evaluation metrics**
- **QLIKE** (L(h, σ²) = σ²/h − log(σ²/h) − 1) and **MSE** are the only loss functions Patton (2011, *J. Econometrics* 160:246–256) shows are robust to noise in the volatility proxy — meaning the ranking of forecasters is preserved under unbiased proxies. **QLIKE is preferred** because it is much less sensitive to outliers (extreme volatility days) than MSE. MAE, MAPE, and HMSE are non-robust under imperfect proxies.
- **Mincer–Zarnowitz regressions**: regress RV_{t+1} on forecast; check intercept = 0, slope = 1.
- **Diebold–Mariano (1995)** and **Giacomini–White (2006)** for pairwise predictive-ability tests.
- **Model Confidence Set (MCS)** of Hansen, Lunde & Nason (2011, *Econometrica* 79:453–497): given a set of forecast losses, returns the smallest set that contains the best model with given confidence — the right tool when comparing many ML models.

## B. Volatility forecasting — econometric baselines that ML must beat

- **HAR-RV (Corsi 2009, *J. Financial Econometrics* 7:174–196)**: RV_{t+1} = β₀ + β_d RV_t + β_w RV_{t,t-5} + β_m RV_{t,t-22} + ε. Per Clements & Preve (J. Banking & Finance 133:106285, 2021), Corsi (2009) had exceeded 2,100 Google Scholar citations as of July 2021 — it is the universal benchmark.
- **HAR-J / HAR-CJ**: Andersen, Bollerslev & Diebold (2007). Adds jump component or fully decomposes continuous + jump.
- **HARQ (Bollerslev, Patton, Quaedvlieg 2016, *J. Econometrics* 192:1–18)**: parameters vary with realized quarticity (measurement-error proxy). Empirically, on the S&P 500 (their Table 3), HARQ achieves R² = 0.5624 vs HAR's 0.5224, MSE 2.3570 vs 2.5722 (–8.4%), and QLIKE 0.1358 vs 0.1438 (–5.6%). On the 27 DJIA constituents (averaged): HARQ R² 0.509 vs HAR 0.485, MSE −5.4%, QLIKE −1.7%. HARQ is the *current state-of-the-art HAR variant*.
- **HAR with leverage / signed semi-variances**: Patton & Sheppard (2015 *RES* 97:683–697) "Good Volatility, Bad Volatility": negative semivariance has substantially more predictive power than positive semivariance for future RV. Negative jumps → higher future RV; positive jumps → lower. Models exploiting this lead to "significantly better out-of-sample forecast performance."
- **HEAVY models**: Shephard & Sheppard (2010, *J. Applied Econometrics* 25:197–231); Noureldin, Shephard & Sheppard (2012) for multivariate. Two-equation system jointly modelling daily returns and realized measures.
- **GARCH family**: GARCH (Bollerslev 1986), EGARCH (Nelson 1991), GJR (1993), FIGARCH (long memory). Largely superseded for daily RV by HAR but still common at lower frequencies and for risk-neutralisation.
- **Realized GARCH (Hansen, Huang, Shek 2012, *J. Applied Econometrics* 27:877–906)** and Realized EGARCH (Hansen & Huang 2016): joint model with measurement equation linking RV to latent conditional variance — substantial empirical fit improvement over GARCH using realized measures.
- **Stochastic volatility / rough volatility**: Heston (1993), and the **rough volatility revolution** of Gatheral, Jaisson & Rosenbaum (2018, *Quantitative Finance* 18:933–949) "Volatility is Rough": log-RV behaves "as a fractional Brownian motion with Hurst exponent H of order 0.1, at any reasonable timescale." The **RFSV model** delivers improved RV forecasts via a one-parameter formula. **Bayer, Friz & Gatheral (2016 QF)** rBergomi pricing model. Open debate: **Cont & Das (2024, *Sankhya B* 86:191–223)** "Rough Volatility: Fact or Artefact?" argue that microstructure noise alone, applied to a Brownian-roughness instantaneous volatility, generates apparent H ≈ 0.1 in RV — i.e. observed roughness may be a measurement artefact rather than a property of true volatility. Important caveat for any rough-vol-based forecasting.

## C. ML methods for volatility — what actually works

**Honest verdict before details**: on equity-index daily RV with HAR-style information sets, ML's advantage over HAR is small and often statistically insignificant. ML wins decisively only when (a) the information set genuinely expands beyond HAR's three lags (LOB, options, cross-asset, sentiment), (b) horizons are longer (week/month) where long-memory matters, or (c) you stay in the *tabular* regime with disciplined feature engineering and gradient boosting.

### C1. Tree-based methods — quiet winners on tabular features

- **XGBoost / LightGBM / CatBoost / Random Forest**: dominant on Kaggle and in industry for tabular volatility tasks. The **Optiver Realized Volatility Prediction Kaggle (2021)** evaluated models on RMSPE across 112 NASDAQ stocks; the publicly documented top-10 solutions (e.g. michaelpoluektov's 7th-place finish at 0.20013 public RMSPE) are LightGBM-based ensembles built on hand-engineered microstructure features (book imbalance, weighted-average price (WAP) realized vol, microprice, time-decayed features). The independently-published IEEE benchmark (Wang et al. 2021) found LightGBM at RMSPE = 0.211, beating logistic regression, SVM, and XGBoost on the same data.
- **Christensen, Siggaard & Veliyev (2023, *J. Financial Econometrics* 21:1680–1727)**: regularised regression, regression trees, and neural networks on DJIA constituents. Their abstract states: "ML is competitive and beats the HAR lineage, even when the only predictors are the daily, weekly, and monthly lags of realized variance. The forecast gains are more pronounced at longer horizons. We attribute this to higher persistence in the ML models, which helps to approximate the long-memory of realized variance."
- **Branco, Rubesam & Zevallos (2024, *J. Empirical Finance* 78:101524)**: contrasting evidence on 10 global stock indices (2000–2021). Their conclusions: "(i) the additional predictors improve the out-of-sample forecasts at the daily and weekly forecast horizons; (ii) we find no evidence that nonlinear ML models can statistically outperform linear models in general." When the HAR baseline is given the *same* extended predictor set (HAR-X), nonlinear ML's marginal value is often inside the noise band.
- **HARd to Beat (Wilms et al. 2024)**: shows the choice of *fitting scheme* (training-window length, re-estimation frequency) for HAR matters more than ML model choice; properly fitted HAR is hard to beat.

**Optimal decision trees & Rashomon sets** (this branch is novel for finance):
- **GOSDT (Lin, Zhong, Hu, Rudin & Seltzer 2020, ICML)**: branch-and-bound DP for globally optimal sparse decision trees, jointly optimising accuracy + leaf penalty. Beats CART/BinOCT/DL8.5 on the accuracy-vs-sparsity Pareto frontier.
- **MurTree** (Demirović et al. 2022); **DL8.5** (Aglin, Nijssen & Schaus 2020); **Blossom** (Demirović et al. 2023); **STreeD** (van der Linden et al. 2023–24).
- **TreeFARMS (Xin, Zhong, Chen, Takagi, Seltzer & Rudin 2022, NeurIPS Oral)**: first algorithm enumerating the entire *Rashomon set* of sparse decision trees — all near-optimal trees within ε of the optimum. Handles depth-3 trees with ~10² features in seconds; depth-4 in minutes.
- **SPLIT (Babbar, McTavish, Rudin & Seltzer 2025, ICML Oral; arXiv 2502.15988)**: SParse Lookahead for Interpretable Trees — orders of magnitude faster than TreeFARMS via greedy near-leaf solving with negligible accuracy loss; includes RESPLIT for scalable Rashomon set enumeration.
- **Foundational Rashomon papers**: Breiman (2001) "Statistical Modeling: Two Cultures" identified the *Rashomon effect*; Semenova, Rudin & Parr (2022, FAccT) "On the Existence of Simpler Machine Learning Models" formalised the *Rashomon ratio* and showed many tabular tasks have large Rashomon sets, making simple-yet-accurate models attainable; Dong & Rudin (2020) "Variable Importance Clouds" — visualise importance ranges across the Rashomon set; Rudin et al. (2024 ICML position paper) "Amazing Things Come From Having Many Good Models."
- **Why this is interesting for vol forecasting**: financial features are heavily redundant (RV-d, BV-d, RQ-d, WAP-vol-d are all near-collinear). A Rashomon set of optimal trees on engineered RV features would tell you (i) which features are *essential* (appear in every near-optimal tree), (ii) which are *interchangeable* (substitutable for each other), (iii) which are *useless* (in no near-optimal tree). To my knowledge, this analysis has not been published for any financial time series problem.

### C2. Recurrent and convolutional networks
- **LSTMs/GRUs** for daily RV: results are mixed-to-disappointing. Bucci (2020), Liu (2019), and others find LSTMs comparable to or slightly worse than HAR on equity indices. They tend to over-smooth and under-react to vol jumps.
- **HARNet (Reisenhofer, Bayer & Hautsch 2022, arXiv 2205.07719)**: dilated causal convolutions whose receptive field ties to HAR's (1, 5, 22) days. Initialised so HARNet ≡ HAR pre-training. Reports an "average reduction of the median test MAE of about 11.74%" across SPX, FTSE 100, and DJI relative to OLS-HAR; QLIKE-trained boxplots show ~10–30% median QLIKE reductions. Excellent template for "neural HAR."
- **DeepVol (Moreno-Pino & Zohren 2024, *Quantitative Finance* / arXiv 2210.04797)**: dilated causal convolutions over *raw 1-min returns* of NASDAQ-100, bypassing handcrafted realized measures. Authors show consistent improvement over HAR baselines and over HARNet variants on intraday-rich settings.
- **TCN / WaveNet-style**: comparable performance to HARNet/DeepVol; the dilation pattern matters more than the precise architecture.

### C3. Transformers and modern time-series architectures
- **N-BEATSx applied to RV — Souto & Moradi (2024), "Introducing NBEATSx to Realized Volatility Forecasting," *Expert Systems with Applications* 122802**: state verbatim that "NBEATSx generates forecasts that are respectively 13% and 8% more accurate for medium-term and long-term forecasting" versus LSTM, TCN, HAR, GARCH, and GJR-GARCH across six stock indices. Single-paper claim — treat as suggestive evidence rather than settled.
- **N-HiTS, TiDE, TSMixer, PatchTST (Nie et al. 2023)**: in the most recent independent benchmark — Taneva-Angelova & Granchev (2025), "Deep Learning and Transformer Architectures for Volatility Forecasting: Evidence from U.S. Equity Indices," *J. Risk Financial Management* 18(12):685, covering S&P 500, NASDAQ 100, and DJIA over 2000–2025 — the authors find that "Transformer-based models achieve the lowest errors and strongest generalization, particularly at short horizons and during volatile periods." Performance is *dataset-dependent*.
- **Temporal Fusion Transformer (TFT)**: cited but underwhelming on daily RV.
- **TimesNet**: comparable RMSE/QLIKE but loses on MAE/MAPE versus HAR/N-BEATSx/N-HiTS in published comparisons.

### C4. Graph neural networks for cross-asset RV
- **Zhang, Pu, Cucuringu & Dong (2025, *Int. J. Forecasting* 41(1):377–397)**: graph attention networks for multivariate RV. Key empirical findings — multi-hop spillovers add little; *nonlinear* one-hop spillover effects do help short-horizon (≤1-week) forecasts; *training with QLIKE loss substantially outperforms MSE training*, especially because QLIKE handles heteroscedasticity better.
- **SpotV2Net (Brini & Toscano 2025, *Int. J. Forecasting* 41(3):1093–1111)**: vol-of-vol-informed graph attention for intraday spot vol.

### C5. Other ML / structural directions
- **Neural SDEs / Neural ODEs**: Kidger, Morrill et al. (NeurIPS 2020+); promising for continuous-time vol modelling; calibration is hard, papers are mostly methodological.
- **Gaussian processes for volatility**: Wilson, Adams (2013) GP-vol; computational cost limits scale.
- **Reservoir computing / echo state networks**: niche; small literature.
- **Variational autoencoders**: Buehler, Horvath, Lyons et al. for market generators / latent vol states.
- **Hybrid HAR-ML**: HARNet (above) is the cleanest example; broader idea is to parameterise the HAR coefficients as functions of state via a neural network, or to use HAR residuals as a target.
- **Rough-volatility-augmented ML**: Bayer & Stemper (2018) "Deep calibration of rough stochastic volatility models" applies neural nets to learn the rough Bergomi pricing functional.

### C6. Honest verdict on horizon
- **Intraday (next 10–30 min)**: ML/LOB-features can produce real gains; this is the Optiver-Kaggle / DeepLOB regime. Microstructure features dominate.
- **Daily**: HAR + measurement-error correction (HARQ) + signed semi-variances is very hard to beat by more than a few percent QLIKE.
- **Weekly/monthly**: ML models with long memory (gradient boosting, deep nets) start to show meaningful gains, per Christensen et al. (2023).

## D. Feature engineering for volatility prediction

**Feature families (in approximate order of empirical importance for daily RV forecasting)**:

1. **Realized-measure history**: RV-d, RV-w, RV-m (HAR core); BV, RQ (quarticity); realized semivariances RS+, RS- (Barndorff-Nielsen, Kinnebrock & Shephard 2010); signed jump variation J = RS+ − RS-; realized skewness & kurtosis (Amaya, Christoffersen, Jacobs & Vasquez 2015 *JFE*).
2. **Options-implied**: VIX / VVIX, IV at multiple strikes & maturities, IV–RV spread (variance risk premium per Bollerslev, Tauchen & Zhou 2009 *RFS* 22:4463–4492 — VRP "explain[s] a non-trivial fraction of the time-series variation in post 1990 aggregate stock market returns"), VIX term structure (slope, curvature), risk-neutral skewness (Bakshi-Kapadia-Madan 2003).
3. **Microstructure / LOB**: bid-ask spread, top-of-book depth imbalance, order flow imbalance (Cont, Kukanov & Stoikov 2014), trade-arrival intensity, weighted-average price (WAP) volatility, Amihud (2002) illiquidity, Kyle's λ, microprice, queue imbalance. Rahimikia & Poon (2020) explainable-AI analysis pinpoints "mid prices, mean bids, and mean asks" as dominant features. Their headline empirical claim: high-dimensional ML models with LOB features outperform HAR models in 90% of the out-of-sample period for 23 NASDAQ tickers (2007–2016), except during extreme volatility days.
4. **Cross-asset**: VIX, MOVE (rates vol), CDX/iTraxx credit spreads, USD index vol, gold vol; volatility spillover indices (Diebold-Yilmaz 2009/2012/2014).
5. **Calendar / event**: day of week, holiday proximity, FOMC dates, earnings announcement dates (Lee 2012 shows earnings almost always trigger jumps), macro release calendars.
6. **Long-memory features**: fractional differencing (Lopez de Prado AFML Ch. 5) — preserves memory while ensuring stationarity.
7. **Sentiment / NLP**: Rahimikia, Zohren & Poon (2024) FinText word embeddings on Dow Jones Newswires; helpful especially on jump days.

**Rashomon-aware feature analysis (novel for finance)**: with TreeFARMS/SPLIT one can construct the Rashomon set of all near-optimal interpretable trees on the above feature panel, then compute *Variable Importance Clouds* (Dong & Rudin 2020) — an interval [min, max] of importance for each feature across the Rashomon set. Features with non-overlapping clouds tell you which inputs are robustly important versus accidentally selected by a single greedy CART.

## E. The variance risk premium and vol-of-vol

- **VRP** = E^Q[RV] − E^P[RV] ≈ VIX² − E_t[RV_{t+1,t+30}]. Bollerslev, Tauchen & Zhou (2009): VRP predicts equity returns at quarterly horizons; explains >15% of S&P 500 quarterly excess return variation 1990–2005. Bekaert & Hoerova (2014, *J. Econometrics*) and Carr & Wu (2009 *RFS*) extend.
- **Vol-of-vol / VVIX**: Direct CBOE index. Bollerslev, Tauchen & Zhou's stylized model treats time-variation in vol-of-vol as a key state variable; matters for delta-neutral options strategies (gamma scalping P&L variance).
- **Rough vol and VRP**: rough volatility models naturally generate steep IV skew and large VRP; the Cont-Das (2024) critique is the current frontier.
- **ML on VRP**: relatively under-explored — Bali, Hu, Murray (2019) and various practitioner pieces use random forests / XGBoost on VRP-conditioned features for return prediction, but not for VRP forecasting itself.

## F. Multi-asset and cross-asset volatility
- **Realized covariance**: BNHLS (2011) multivariate realized kernels; refresh-time sampling (Hayashi-Yoshida 2005); composite realized kernels; HEAVY-MV (Noureldin et al. 2012).
- **Volatility spillovers / connectedness**: Diebold & Yilmaz (2009 EJ; 2012 *Int. J. Forecasting*; 2014 *J. Econometrics*) use generalised forecast-error variance decomposition from a VAR of realized vols. Total connectedness index spikes during crises.
- **Factor models for vol**: Andersen, Bollerslev, Diebold & Ebens (2001); Herskovic, Kelly, Lustig, Van Nieuwerburgh (2016 *JFE*) "common idiosyncratic volatility."
- **GNN approaches**: Zhang-Pu-Cucuringu-Dong (2025) and SpotV2Net (Brini-Toscano 2025) above.

## G. Avoiding the graveyard — what doesn't work and why

- **HAR is surprisingly hard to beat.** On daily equity index RV with HAR-style information set, the median ML "improvement" reported in the literature is small and often disappears when (i) HAR is properly fitted (Wilms et al. 2024 "HARd to Beat"), (ii) MCS rather than point comparisons is used, or (iii) loss is QLIKE rather than MSE.
- **Overfitting on vol regimes**: vol exhibits long, slow regimes (low-vol 2017, COVID 2020); train-test splits that don't cover crises or that contaminate test with crisis data give wildly misleading results.
- **Lookahead bias**: realized measures use intraday returns up to time t; ensure features for predicting RV_{t+1} use only information ≤ t. Microstructure features computed on the full day require careful timestamp alignment.
- **Non-stationarity & long memory**: log-RV is near-unit-root; differencing destroys signal. Use fractional differencing (Lopez de Prado AFML Ch. 5) or model in log-RV space.
- **Cross-validation done wrong**: Lopez de Prado (2018) "Advances in Financial Machine Learning" Ch. 7: standard k-fold CV leaks because labels overlap (RV_{t+1,t+5} for adjacent t's share intraday returns). Use **purged k-fold CV with embargo** (and ideally combinatorial purged CV for hyperparameter selection).
- **Choice of loss matters**: MSE is dominated by extreme vol days; QLIKE is the right default (Patton 2011). Train deep nets with QLIKE loss, not MSE — Zhang et al. (2025 GNN paper) report this matters substantially.
- **MCS, Diebold-Mariano, and Reality Check** are the right comparators — not raw averages.

**When does better vol forecast → real PnL?** The translation is not automatic. For variance swap MM, even a modest MSE improvement can be meaningful given large notionals. For options market-making, what matters is the *conditional bias* of the forecast at strikes/maturities being quoted. For risk management (VaR/ES), better vol forecasts only matter if combined with calibrated tail innovations. For statistical arbitrage, vol is usually a sizing input, not an alpha — small vol improvements rarely move Sharpe.

## H. Practical applications — why traders care

- **Options pricing & market-making**: implied vol from a vol forecast is a benchmark for whether market IV is rich/cheap; supports systematic vol-arb strategies (variance swaps, vol swaps, dispersion).
- **Risk management**: VaR and Expected Shortfall under historical simulation, filtered historical simulation, and parametric (Gaussian/Student-t) frameworks all need a conditional vol forecast.
- **Volatility trading**: VIX futures roll/term-structure trades, dispersion (long single-name vol vs. short index vol), short-vol carry, gamma scalping — all driven by RV vs IV expectations.
- **Portfolio construction**: vol targeting (constant-vol portfolios), risk parity, minimum variance, Black-Litterman covariance inputs.
- **Execution algorithms**: VWAP/TWAP slicing depends on intraday vol forecasts; participation-rate algos use vol to calibrate aggression.

**For a GS trading-floor audience**: the highest-impact applications are (1) options market-making on indices and ETF complexes (var-swap pricing, dispersion books, dealer hedging), (2) systematic macro / multi-asset vol-targeting strategies, and (3) execution-algo vol inputs. A single-name daily RV forecast that beats HAR by a few percent QLIKE is unlikely to move desk PnL. A robust intraday vol forecast that improves variance-swap markups by basis points is very valuable.
