# ML for Realized Volatility Estimation & Forecasting — Internship Scoping Brief

## Executive Summary

Realized volatility (RV) — the ex-post quadratic-variation-based measure of return variability constructed from intraday data (Andersen & Bollerslev 1998; Barndorff-Nielsen & Shephard 2002) — is one of the cleanest forecasting targets in finance: directly observable, economically central (options pricing, VaR, risk parity, vol targeting), and supported by a deep, mature econometric literature. It is the right place to apply ML carefully.

The honest empirical bottom line, after reading widely: **the HAR family (Corsi 2009; HAR-J/CJ; HARQ Bollerslev-Patton-Quaedvlieg 2016; SHAR Patton-Sheppard 2015) is extremely hard to beat at daily horizons when only past RV is in the information set**. Christensen, Siggaard & Veliyev (2023, *J. Financial Econometrics*) show ML competes and modestly beats HAR — gains grow with horizon and with rich feature sets — but Branco, Rubesam & Zevallos (2022) and the recent "HARd to Beat" paper (arXiv 2406.08041) find that with proper rolling-window fitting, HAR matches or surpasses nonlinear ML on QLIKE. **Where ML demonstrably wins is (i) intraday/short-horizon RV from microstructure data (Optiver/LOBSTER-style), (ii) cross-sectional / multi-asset settings (graph and panel models), (iii) fusion of heterogeneous predictors (LOB + news + options + macro), and (iv) calibration of rough-vol pricing maps**. Rough-volatility (Gatheral-Jaisson-Rosenbaum 2018) provides an alternative parsimonious benchmark that itself is competitive with universal LSTMs (Rosenbaum-Zhang 2022), though Cont & Das (2024) show "roughness" of *realized* vol is partly a microstructure-noise artefact.

For a 10–12 week internship by a strong CS/MEng student, the most defensible projects are **scoped narrowly to settings where ML's structural advantages bite**: (1) intraday RV from LOB with a careful HAR-X / CHAR baseline (Rahimikia-Poon style), (2) multivariate/cross-sectional RV with graph or panel networks (Zhang et al., Chen-Robert), (3) options-implied + RV fusion using the variance risk premium and realized-semivariances as features, and (4) rough-vol vs ML head-to-head with proper Cont-Das robustness checks. Throughout, evaluation must use Patton (2011) robust losses (QLIKE/MSE), Diebold-Mariano tests, Hansen-Lunde-Nason model confidence sets, and López de Prado purged k-fold CV. **Aim for 30–80 bps QLIKE improvement, well-validated, on at least one regime and asset class**, plus an economic-value test (vol-targeting Sharpe, options-market-making PnL proxy, or VaR backtest). The "wow factor" is rigour, an economic-value translation, and an honest "where ML helps and where HAR wins" decomposition — a framing trading-floor managers respect more than another 0.5% R² claim.

---

## PART 1 — LANDSCAPE SURVEY

### A. Realized volatility — definitions, estimators, and the estimation problem

The core quantity is the **integrated variance** IV_t = ∫_{t-1}^t σ²_s ds of a continuous semimartingale log-price, with a possible jump component. Its consistent ex-post estimator from n equally spaced intra-day returns r_{t,i} is the **realized variance** RV_t = Σ_i r²_{t,i}, formalised by Andersen, Bollerslev, Diebold & Labys (1998–2003) and Barndorff-Nielsen & Shephard (*JRSS-B* 2002). RV converges to quadratic variation as Δt → 0 in the absence of microstructure noise.

**Microstructure noise** (bid-ask bounce, discrete tick size, asynchronous trades, price staleness) biases naive high-frequency RV: the bias dominates the signal as sampling frequency increases (Hansen-Lunde 2006; Aït-Sahalia, Mykland & Zhang 2005 "How often to sample"). The classic practical compromise is **5-minute RV**, and Liu, Patton & Sheppard (*J. Econometrics* 2015, "Does Anything Beat 5-Minute RV?") showed that across ~400 estimators applied to 31 assets in 5 asset classes, the simple 5-minute RV is hard to beat as a benchmark realized measure for forecasting purposes, though more sophisticated estimators sometimes win marginally on direct accuracy.

The major **noise-robust estimator** families, in approximate order of historical development:

- **Two-scales realized volatility (TSRV)** — Zhang, Mykland, Aït-Sahalia (*JASA* 2005); converges at rate n^{-1/6}.
- **Multi-scale realized volatility (MSRV)** — Zhang (*Bernoulli* 2006); attains the optimal n^{-1/4} rate.
- **Realized kernel** — Barndorff-Nielsen, Hansen, Lunde & Shephard (*Econometrica* 2008; "in practice" *Econometrics J.* 2009); flat-top kernel with optimal weighting; the practical workhorse for clean estimation.
- **Pre-averaging** — Jacod, Li, Mykland, Podolskij & Vetter (*SPA* 2009); averages local blocks to suppress noise.
- **Subsampling / averaging RV** — Zhang-Mykland-Aït-Sahalia.
- **Fourier estimator** — Malliavin & Mancino (covariation as Fourier coefficients).
- **Quasi-MLE under noise** — Xiu (*J. Econometrics* 2010).

**Jump detection**: continuous-time prices may jump, breaking the diffusion-only basis of RV. Tests:
- **Bipower variation** BPV_t = (π/2)Σ|r_{t,i}||r_{t,i-1}| → ∫σ²_s ds even with jumps; the BNS jump test (Barndorff-Nielsen & Shephard *J. Financial Econometrics* 2004, 2006) compares RV–BPV.
- **Lee-Mykland test** (*RFS* 2008; 2012 extension to MMS noise) — intra-day, identifies jump *times and sizes*.
- **Aït-Sahalia & Jacod** (*Annals of Statistics* 2009) — power-variation-ratio test, robust to noise.
- **Threshold/truncation** approach (Mancini; Corsi-Pirino-Renò *J. Econometrics* 2010) gives the *continuous* HAR-CJ decomposition.

**Forecast evaluation**:
- **MSE** is robust to imperfect proxies but heavy-outlier-sensitive in vol settings.
- **QLIKE** L(σ², h) = log h + σ²/h (Patton *J. Econometrics* 2011) is robust to noise in the proxy *and* less sensitive to extreme RV days; **QLIKE is the preferred loss** in modern empirical work.
- **Mincer-Zarnowitz** regressions of σ² on a constant and the forecast assess unbiasedness.
- **Diebold-Mariano** and Giacomini-White tests for pairwise predictive comparisons.
- **Model Confidence Set** (Hansen, Lunde & Nason *Econometrica* 2011) returns a set of statistically indistinguishable best models given a confidence level — the gold standard when comparing many models simultaneously.

### B. Volatility forecasting — econometric baselines that ML must beat

**HAR family** (Corsi 2009, *J. Financial Econometrics*) is the de facto benchmark:

RV_t = β_0 + β_d RV_{t-1} + β_w (1/5)Σ_{i=1..5}RV_{t-i} + β_m (1/22)Σ_{i=1..22}RV_{t-i} + ε_t

Heterogeneous market participants → mimics long memory with three components. Key extensions:
- **HAR-J / HAR-CJ** (Andersen-Bollerslev-Diebold 2007; Corsi-Pirino-Renò 2010): split RV into continuous and jump parts.
- **SHAR / semi-variance HAR** (Patton & Sheppard *RestStat* 2015): use realized semi-variances RS⁺, RS⁻ separately — *negative-return* RS⁻ has substantially more forecast power ("good vs bad volatility").
- **HARQ** (Bollerslev, Patton & Quaedvlieg *J. Econometrics* 2016): allows the daily AR coefficient to vary with realized quarticity (estimator of measurement-error variance), letting noisy RV days be down-weighted. Materially improves forecasts.
- **HARX with leverage**, signed returns, VIX, RQ, macro variables — Audrino-Knaus (Lasso-HAR), Bollerslev-Hood-Huss-Pedersen (*RFS* 2018, "Risk everywhere").
- **HEAVY** (Shephard & Sheppard 2010): joint daily-return / realized-measure model.

**GARCH family**: GARCH (Bollerslev 1986), EGARCH (Nelson 1991, leverage), GJR-GARCH (Glosten-Jagannathan-Runkle), FIGARCH (long-memory, Baillie-Bollerslev-Mikkelsen). **Realized GARCH** (Hansen, Huang, Shek *J. Applied Econometrics* 2012) augments GARCH with a measurement equation linking RV to conditional variance — much better empirical fit. Realized EGARCH and Realized HAR-GARCH extend this.

**Stochastic volatility**: Heston (1993) (mean-reverting CIR variance), Bates (jumps), SABR. Modern **rough volatility** revolution: Gatheral, Jaisson & Rosenbaum (*Quantitative Finance* 2018, "Volatility is rough") — log-RV across assets behaves like fractional Brownian motion with Hurst exponent H ≈ 0.1, far below ½. The RFSV (rough fractional stochastic volatility) model gives a near-universal one-parameter forecasting formula competitive with HAR and LSTMs (Bennedsen-Lunde-Pakkanen 2022 confirm cross-asset universality of H ≈ 0.1). Quadratic Rough Heston (Gatheral-Jusselin-Rosenbaum 2020) is the first model to *jointly* fit SPX and VIX smiles. **Roughness debate**: Cont & Das (*Sankhya B* 2024, "Rough Volatility: Fact or Artefact?") and Fukasawa et al. (2022) show that even diffusive spot vol with H = 0.5 produces *realized* vol estimates with apparent H < 0.5 — i.e. observed roughness is partly microstructure-noise artefact. Filtering approaches (e.g. *Quant. Finance* 2024 "Detecting rough volatility: a filtering approach") aim to disentangle. Practical implication: rough-vol features are useful but should not be treated as ground truth about the spot process.

**Forecast horizons** — where each method shines:
- **Intraday (≤ 30 min)**: microstructure features dominate; LOB-driven LSTM/CNN/transformers; Optiver-Kaggle-style LightGBM with order-flow features.
- **Daily**: HAR family is the benchmark; HARQ + signed RV + VIX is very strong; ML wins meaningfully only with rich exogenous features.
- **Weekly to monthly**: ML gains widen, especially deep nets; macro variables and VRP add value (Bollerslev-Tauchen-Zhou 2009 found VRP predicts returns most strongly at quarterly horizons).
- **Spillover / cross-asset**: graph models and Diebold-Yilmaz frameworks.

### C. ML methods for volatility — what actually works (deep dive)

#### C.1 Tree-based gradient boosting (XGBoost, LightGBM, RandomForest)

The most consistently effective ML class for tabular RV problems. Christensen-Siggaard-Veliyev (*JFE* 2023) found tree-based models among the best performers for daily RV on 29 DJIA stocks 2001–2017, beating HAR even with only daily/weekly/monthly RV lags as features, and decisively when adding firm- and macro-level predictors. The **2021 Kaggle Optiver Realized Volatility Prediction** competition (predicting 10-min ahead RV from L2 LOB and trade data on ~112 stocks) was won by LightGBM ensembles, often blended with shallow MLPs/transformers, with the bulk of value coming from feature engineering (WAP-based log returns, bid-ask spread, order book imbalance, trade size, micro-price, log-return-of-log-return, time-bucketed aggregations) rather than model class. Top-7 solutions are open-source on GitHub (e.g. `michaelpoluektov/orvp`). Audrino-Knaus (*Econometric Reviews* 2016) "Lassoing the HAR" shows even regularised linear ML competes well.

**What works**: rich tabular features, ~10²–10³ predictors, careful cross-validation; out-of-the-box sklearn/LightGBM hyperparameters often suffice. **Failure modes**: extrapolation to high-volatility regimes outside training distribution, e.g. COVID-19 — Rahimikia & Poon (SSRN 3707796) note ML beats HAR ~90% of OOS days but fails in extreme stress; ensembling ML *with* HAR mitigates this.

#### C.2 RNNs (LSTMs, GRUs)

Bucci (*J. Financial Econometrics* 2020) compared feed-forward, Elman, Jordan, NARX and LSTM nets on S&P 500 monthly RV — LSTMs and NARX beat ARFIMA/HAR on MSE and QLIKE, especially in the 2008 crisis. Sirignano & Cont (*Quantitative Finance* 2019, "Universal features of price formation") showed pooled LSTMs across ~500 NASDAQ stocks generalise to held-out tickers — first demonstration of universal features in LOB data. Rosenbaum & Zhang (arXiv 2206.14114, 2022) trained a **universal LSTM** on hundreds of liquid stocks for next-day RV: it outperforms asset-specific HARs and matches the parsimonious RFSV+QRH parametric forecaster — empirical support for a universal volatility-formation mechanism. Rahimikia & Poon (2020, SSRN 3707796 / 3684040) feed CHAR variables + LOB depth + news counts into LSTMs and find statistically significant gains on 23 NASDAQ tickers.

**What works**: pooling across many tickers, sequential data with longer-than-22-day memory, regimes with non-linear persistence. **Failure modes**: brittle on small samples, often outperformed by simple HAR after careful rolling-window fitting (HARd to Beat, arXiv 2406.08041).

#### C.3 Temporal convolutional networks / WaveNet-style

**DeepVol** (Moreno-Pino & Zohren, arXiv 2210.04797, 2022) uses dilated causal convolutions on 1-minute returns to produce day-ahead RV forecasts. It beats HAR and LSTM on a wide cross-section, with an interpretable receptive field showing which intra-day windows matter most. TCN's parameter efficiency vs LSTM and ability to learn multi-scale patterns from raw HF data make it a strong fit for intraday → daily RV.

#### C.4 Transformers and attention

A flurry of recent papers but evidence is mixed. Ramos-Pérez et al. (2021), Liu et al.'s "Multi-Transformer" (arXiv 2109.12621), and several MDPI papers (e.g. *J. Risk Financial Mgmt* 2025, "Deep Learning and Transformer Architectures for Volatility Forecasting") report Transformer/Multi-Transformer hybrids improve over GARCH and LSTM on RMSE and VaR backtests for equity indices — but these papers often use loose baselines and lack MCS testing. **Graph Transformer Network for Volatility Forecasting** (Chen-Robert, ACM ICAIF 2022, arXiv 2112.09015) tackles the multivariate Optiver-style task on ~500 S&P 500 stocks and outperforms LightGBM and graph-only baselines by combining LOB features with cross-sectional sector graphs. **TLOB** (arXiv 2502.15757, 2025) introduces dual temporal/feature attention for LOB price-trend prediction.

**What works (so far)**: tasks with cross-sectional structure, LOB inputs, and large training sets. **Caution**: long-horizon transformer benchmarks (PatchTST, Informer, Autoformer) have *not* been definitively shown to beat HAR on standard daily RV benchmarks; recent literature (Zheng et al. 2022) suggests simple linear models match transformer performance for many TS tasks.

#### C.5 Modern time-series architectures (N-BEATS, N-HiTS, TiDE, TSMixer, PatchTST)

Limited published rigorous evidence on RV specifically. The MDPI paper "Stock Market Volatility Forecasting" (2025) found TiDE best at 1-day-ahead and DeepAR best at longer horizons on 22+ years of S&P/DJIA/Nasdaq 5-min RV — but only when macro features (DXY, VIX, US10Y) are included; with only RV lags, HAR matches DL. NeuralForecast (Nixtla) provides clean reference implementations of all of these. Likely a productive but not yet thoroughly explored avenue.

#### C.6 Neural SDEs / Neural CDEs / Neural ODEs

Kidger et al. (NeurIPS 2020 Neural CDEs; ICML 2021 "Neural SDEs as Infinite-Dimensional GANs") provide generic architectures for irregularly-sampled, continuous-time data. Direct application to forecasting daily RV is rare and unconvincing — the comparative advantage is in *scenario generation* and *pricing*: Cuchiero-Khosrawi-Teichmann's GAN approach to local-stochastic-vol calibration; Gierjatowicz et al. (arXiv 2007.04154) "Robust pricing and hedging via neural SDEs". For an internship this is more an *option-pricing-side* tool than a forecasting tool.

#### C.7 Gaussian processes

Wu, Lobato & Ghahramani (2014) used GPs for vol; Ensemble-GP for asset pricing (arXiv 2212.01048). Strength: principled uncertainty quantification; weakness: O(n³) scaling makes them awkward beyond a few thousand observations. Useful for *small-sample* settings (e.g. crypto, illiquid commodities).

#### C.8 Reservoir computing / echo state networks

Niche; some papers report competitive results vs LSTM at much lower training cost. Not a mainstream RV technique.

#### C.9 Autoencoders / VAEs for latent vol state

Variational autoencoders for IV-surface compression (e.g. Ding-Lu-Cheung 2025, arXiv 2509.05911 — VAE compresses S&P 500 daily IV surfaces 2018–2023 into a 10-D latent for fast option pricing). Deep Stochastic Volatility Model (Xu-Chen, AAAI 2021, arXiv 2102.12658) uses VAE-style latent dynamics. Co-training with normalising flows (Du-Moriyama-Tanaka-Ishii, arXiv 2310.14536) jointly learns RV transformation + forecast.

#### C.10 Hybrid econometric + ML

Almost universally, the strongest published results combine HAR/GARCH structure with ML residuals or features:
- HAR-SVR (MDPI Risks 2024) — SVR on HAR residuals.
- GARCH-Informed Neural Net (GINN, arXiv 2410.00288).
- "From financial word embeddings" (Rahimikia-Zohren-Poon, arXiv 2108.00480) — NLP vol forecaster combined with HAR.
- Ensemble HAR + LightGBM consistently the safest performer in Rahimikia-Poon and on Optiver leaderboards.

#### C.11 Honest assessment — does ML consistently beat HAR?

Pulling the evidence together:

1. **At daily horizon, with only past RV as input**: ML's gains over a *carefully fitted* HAR are small and fragile. "HARd to Beat" (arXiv 2406.08041) shows rolling-window HAR with proper window selection often *beats* off-the-shelf ML on QLIKE. Branco-Rubesam-Zevallos (SSRN 4228131): "no evidence nonlinear models outperform statistically".
2. **At daily horizon, with rich exogenous features**: ML wins meaningfully (Christensen-Siggaard-Veliyev 2023; Rahimikia-Poon 2020). Gains 5–20% QLIKE on average.
3. **At intraday horizon with LOB data**: ML is necessary — HAR is not directly applicable. LightGBM/transformers on LOB beat trivial baselines by a wide margin (Optiver Kaggle).
4. **At weekly–monthly horizon**: ML gains widen.
5. **In multi-asset / cross-sectional**: graph/panel networks beat asset-specific HAR (Chen-Robert; Zhang-Pu-Cucuringu-Dong 2022/2023).
6. **In stress regimes (COVID, GFC)**: ML *under-performs* HAR — heavy-tailed and out-of-distribution; ensembles needed.

### D. Feature engineering for volatility prediction

The single highest-leverage area for an internship.

**Lagged RV transforms**: daily/weekly/monthly RV (HAR), log-RV, √RV, fractional differences (López de Prado 2018, Ch. 5).

**Realized quarticity** RQ = (n/3)Σ r⁴_i — measurement-error variance estimator; key HARQ feature.

**Signed / asymmetric features**:
- Realized **semi-variances** RS⁺ = Σ r²_i 1{r>0}, RS⁻ = Σ r²_i 1{r<0} (Barndorff-Nielsen, Kinnebrock & Shephard 2010).
- **Signed jumps** ΔJ² = RS⁺ − RS⁻ (Patton-Sheppard 2015) — strong predictor; bad volatility persists more.
- Realized **semi-covariances** (Bollerslev, Li, Patton, Quaedvlieg *Econometrica* 2020).
- **Realized partial (co)variances** (Bollerslev-Medeiros-Patton-Quaedvlieg 2022).
- Leverage effect features: lagged signed returns × |return|.

**Higher moments**: realized skewness Σr³_i / RV^{3/2}, realized kurtosis. These add modest forecasting power and large risk-management value.

**Microstructure / order-flow features** (esp. for intraday RV):
- Bid-ask spread (effective and quoted), micro-price, weighted average price (WAP).
- Order-book imbalance OBI = (B−A)/(B+A), log-OBI; multi-level imbalance.
- Order arrival rates (Hawkes-style), trade-to-quote ratios.
- Volume profile (intraday U-shape), abnormal volume.
- Amihud illiquidity = |r|/$volume.
- Trade direction (Lee-Ready), order flow toxicity (VPIN).
- Top Optiver-Kaggle features: WAP log returns, log-return-of-log-return ("price acceleration"), volume-weighted aggregations over multiple time buckets, market urgency = price_spread × liquidity_imbalance.

**Options-implied features**:
- ATM IV, IV term structure, IV skew, model-free implied variance (Britten-Jones-Neuberger 2000).
- VIX, VIX9D, VIX1Y, VVIX.
- **Variance Risk Premium** VRP_t = IV²_t − E_t[RV_{t,t+30}] (or a proxy with lagged RV; Bollerslev-Tauchen-Zhou *RFS* 2009 — strongly predicts equity returns at 3–6m horizons; predicts future RV via mean reversion).
- Heston/Bates/Rough-Heston model-extracted spot vol estimators (Todorov-Zhang 2022, Michael et al. 2025) augmenting HAR.

**Cross-asset**:
- Equity, rates, FX, credit RV cross-features; CDS spreads.
- Diebold-Yilmaz spillover indices computed in rolling windows as features.
- Sector/index RV as common factor.

**Long-memory**:
- Fractional differencing (Hosking 1981; López de Prado AFML Ch. 5).
- Hurst-exponent rolling estimate.

**Calendar / event**:
- FOMC dummies, macro release dates (BLS NFP, CPI), earnings, options expiry (3rd Friday), quarter-end, holidays.
- Time-of-day, day-of-week, intraday seasonal.

**Sentiment / text** (gains modest but real):
- Audrino, Sigrist & Ballinari (2020): news sentiment marginally improves HAR.
- Rahimikia-Zohren-Poon (arXiv 2108.00480): financial word embeddings used as direct vol predictor; modest economic gains.

**Feature importance / interpretability**:
- ALE (accumulated local effects) plots — Christensen-Siggaard-Veliyev use these to identify dominant predictors.
- SHAP for tree models; widely used in Optiver-Kaggle solutions.
- López de Prado MDA / MDI / single-feature importance with substitution effects (AFML Ch. 8).

### E. Variance risk premium and vol-of-vol

**VRP** = E^Q[RV] − E^P[RV], operationalised as (VIX/100)² − a forecast of next-30-day RV. Bollerslev-Tauchen-Zhou (2009) proved the VRP predicts S&P 500 quarterly excess returns with R² beating dividend yield/CAY at this horizon. Drechsler-Yaron (*RFS* 2011) provide a long-run-risk equilibrium account; Bekaert-Hoerova (*J. Econometrics* 2014) decompose VRP into uncertainty vs risk aversion. The VRP also forecasts *future RV* through mean reversion, making (IV²−lagged RV) a useful HAR-X regressor.

**Vol-of-vol**: VVIX (CBOE), realized vol-of-vol RVoV = realized variance of intraday RV, jumps in VIX. Cont-Fonseca shapes-of-IV-surface PCA factors (level, slope, curvature) provide a tractable encoding.

**ML approaches**:
- Fouhy (SSRN 6570380, 2024) hierarchical XGBoost for VIX → RV → VRP, with explicit error decomposition for systematic VRP harvesting.
- Bollerslev et al. extensions decompose VRP into normal vs jump-tail components (Bollerslev-Todorov *J. Financial Economics* 2015 "Tail risk premia").
- Rough-vol-driven VRP studies (arXiv 2604.02743, 2025).

### F. Multi-asset and cross-asset volatility

**Realized covariance estimators**:
- **Multivariate realized kernel** (Barndorff-Nielsen, Hansen, Lunde, Shephard *J. Econometrics* 2011) — PSD estimator under noise & non-synchronous trading.
- **Refresh-time** sampling for synchronisation; Hayashi-Yoshida estimator.
- **Composite likelihood** approaches for high dimensions.

**Forecasting models**:
- **DCC-GARCH** (Engle 2002) for low-dim conditional correlation.
- **Wishart Autoregressive** (Gouriéroux-Jasiak-Sufana).
- **HAR-DRD** (Diebold-Demirer-Liu-Yilmaz / Bollerslev-Patton-Quaedvlieg 2018 *J. Econometrics*) — separately HAR-models variances and correlations; multivariate HARQ extension.
- **Cholesky-HAR** (Chiriac & Voev 2011); log-matrix HAR (Bauer-Vorkink 2011).
- **CNN-RCOV** (arXiv 2107.10602) — convolutional LSTM on RC matrices.
- **Geometric Deep Learning for RC** (arXiv 2412.09517) — SPDNet on the SPD-matrix manifold preserves positive-definiteness.
- **Graph methods** — Zhang-Pu-Cucuringu-Dong (*J. Financial Econometrics* 2024 nbae026, "Graph-Based Methods for Forecasting Realized Covariances") show graph-Lasso adjacency + HAR features beats DCC and HAR-DRD; Zhang-Cucuringu-Dong (2023, "GNNs with nonlinear spillover effects") extends with GNN nonlinearities.

**Volatility spillovers / connectedness**:
- **Diebold-Yilmaz** indices (*Economic Journal* 2009; *IJF* 2012; *J. Econometrics* 2014) — VAR + variance decomposition; total/directional connectedness; widely used in macro-finance and trading desks.
- TVP-VAR Diebold-Yilmaz (Antonakakis et al.).
- Network/graph approaches (Demirer-Diebold-Liu-Yilmaz *J. Applied Econometrics* 2018).

**Universal LSTM / cross-asset universality** (Sirignano-Cont 2019; Rosenbaum-Zhang 2022) — pooled training across assets gives transfer to held-out instruments and confirms universal H ≈ 0.1.

### G. What doesn't work and why

- **Random k-fold CV on TS data**: catastrophic look-ahead. Use López de Prado purged k-fold CV with embargo (AFML Ch. 7) or expanding rolling-window OOS.
- **Naive OOS R² without DM/MCS**: tiny improvements on a small test set are noise. Require DM tests and MCS membership.
- **Beating HAR by 0.5%**: unlikely to translate to PnL; aim for genuine OOS QLIKE wins of 3–10% with economic-value translation.
- **Overfitting to one regime**: train on 2015–2019, test on 2020 → COVID shock invalidates models. Either include stress regimes in training or report regime-conditional performance.
- **Long-memory train/test mismatch**: persistent series make recent training data quasi-correlated with test set; embargo helps.
- **Look-ahead in feature construction**: VIX of day t, macro releases, earnings flags must use only-known-by-EOD t-1 information.
- **Mis-specified loss**: MSE penalises overprediction in low-vol regimes; QLIKE is asymmetric and proxy-robust (Patton 2011).
- **Volatility of the volatility forecast**: a model with great mean QLIKE but high forecast variance can be useless for risk parity / vol targeting.
- **Deflated Sharpe / multiple-testing inflation**: López de Prado Deflated Sharpe Ratio (2018) — strongly recommended when comparing many models.

### H. Practical applications — why traders care

- **Options market-making** (Goldman flow desks, Optiver, Citadel Securities): accurate short-horizon RV forecasts feed directly into theoretical vol → option price quotes; even 1% RV improvement is a measurable edge in spreads quoted.
- **Vol trading / variance swaps / VIX futures**: VRP-based signals.
- **Risk management**: VaR, ES, FRTB Internal Model Approach. Better RV → better VaR.
- **Vol targeting / risk parity**: position-sizing from forecast vol; lower forecast error → higher Sharpe (Moreira-Muir 2017 "Volatility-Managed Portfolios").
- **Execution**: intraday vol forecasts shape participation rates in VWAP/TWAP and aggressive-vs-passive trade-off.
- **Stress testing & capital**: realized covariance forecasts → portfolio variance forecasts.

For a Goldman Sachs Engineering / quant-dev internship, the most relevant applications are: options market-making vol surfaces, intraday vol for execution/SOR, vol targeting for systematic strategies, and risk-system VaR/ES inputs.

---

## PART 2 — PROJECT DIRECTION SUGGESTIONS

### Project 1 — *Safer*: HARQ-X with ML residual augmentation and rigorous MCS evaluation

**One-line pitch**: Take HARQ as the gold-standard linear baseline, add ML-residual modelling with engineered features, and document precisely where ML adds value vs where HARQ is unbeatable.

**What it does**: For 30 liquid US large-caps (DJIA constituents, daily), implement HAR, HAR-J, HAR-CJ, SHAR, HARQ as econometric baselines. Then train (a) LightGBM, (b) LSTM, (c) HARQ + LightGBM-on-residuals using a feature set including realized semi-variances, realized quarticity, signed jumps, VIX/VIX-RV spread (VRP proxy), realized skew/kurt, and macro/calendar dummies. Compare on QLIKE and MSE at h = 1, 5, 22 days; run full Diebold-Mariano pairwise and Hansen-Lunde-Nason MCS at 5%/10%. Translate into a vol-targeted long-S&P portfolio and compute realised utility / Sharpe ratio gains (Bollerslev-Hood-Huss-Pedersen 2018 framework).

**Trading floor relevance**: HAR is what desks already use; quantifying when ML adds 5–10% QLIKE and when it doesn't is genuinely actionable. The vol-targeting Sharpe metric speaks the language of the floor.

**Data**: Free Oxford-Man (archival mirrors / bvhar R package) for daily 5-min RV until 2022 + manual extension via Yahoo/free intraday (e.g. Polygon free tier, Alpaca, FirstRate Data sample) for 2022–2025. VIX from CBOE/FRED. FRED for macro. Calendar: FOMC dates, earnings (Wikipedia, EarningsCalendar API). **No paid data needed for the core**; for the extension, ~$300 of FirstRate or use Goldman's internal feed if available.

**ML methods**: LightGBM (tabular), LSTM (sequential), and HARQ-residual stacking. Explainability via SHAP/ALE.

**Baselines**: HAR, HAR-J, HAR-CJ, SHAR, HARQ, HEAVY, GARCH(1,1), Realized GARCH.

**Feasibility (10–12 wk)**: Very high. Weeks 1–2 data + baselines via `arch` (Sheppard); 3–4 features; 5–7 ML; 8–9 evaluation incl. MCS; 10–11 economic translation; 12 writeup.

**Risks**: HAR is hard to beat, so the *narrative* is the deliverable: "ML adds X% in regime Y, not in regime Z" with proper MCS membership statements.

**Wow factor**: Honest, rigorous, MCS- and DM-validated story. Vol-target Sharpe translation. Public-data reproducibility.

**Novelty**: Moderate; the rigour is the contribution. Mirrors Christensen-Siggaard-Veliyev (2023) and "HARd to Beat" (2024) but with added VRP and vol-targeting.

### Project 2 — *Medium*: Intraday RV from LOB with deep learning, Optiver-style + extensions

**One-line pitch**: Predict 10-minute-ahead realized vol per stock from raw L2 LOB data using a hybrid LightGBM + temporal-convolution / transformer stack, beat the public Optiver leaderboard, and add realistic OOS validation absent in Kaggle.

**What it does**: Use the public Optiver Realized Volatility Prediction dataset (~112 stocks, 10-minute windows of LOB and trade data). Engineer state-of-the-art features (WAP, log-returns, OBI, micro-price, market urgency, etc.). Build (a) baseline 5-min naive RV, (b) HAR on intraday RV (Zhang-Cucuringu-Dong 2022 "Volatility forecasting with ML and intraday commonality" arXiv 2202.08962 — first systematic HAR for intraday), (c) LightGBM with full features, (d) DeepVol-style dilated TCN, (e) Graph Transformer (Chen-Robert) using sector / correlation graphs across the 112 stocks. Evaluate with RMSPE (Optiver native), QLIKE, and a *temporal* OOS split (the Kaggle competition used randomised time-IDs which leaked; correct this and re-evaluate top public solutions).

**Trading floor relevance**: Direct analogue to options market-making short-horizon vol estimation. The Optiver contest itself is from a market-maker.

**Data**: Free Optiver Kaggle data. Optionally augment with LOBSTER (free academic sample data; full subscription expensive). News from public APIs if extending.

**ML methods**: LightGBM, dilated TCN (DeepVol), graph transformer (Chen-Robert), Temporal Fusion Transformer. PyTorch.

**Baselines**: Naive 5-min RV; HAR-intraday (Zhang-Cucuringu-Dong); top-7 Optiver Kaggle solutions (open-sourced). Reverse-engineering tricks should be excluded for honesty.

**Feasibility**: High. Weeks 1–2 data + Kaggle replication; 3–4 feature library; 5–7 model zoo; 8–9 graph component; 10–11 honest temporal OOS split + MCS; 12 writeup.

**Risks**: Optiver data is anonymised (no real time-IDs without leakage tricks); the corrected temporal split will lower scores. That's fine — the deliverable is methodological honesty plus genuine MCS-level wins of the multivariate graph model over univariate baselines.

**Wow factor**: Cross-sectional graph model with attention; honest re-evaluation of the public leaderboard; the connection to options market-making.

**Novelty**: Moderate-high — Chen-Robert's graph transformer is recent (ACM ICAIF 2022) and reproducing + improving it on a clean OOS split is a genuine contribution.

### Project 3 — *Medium-ambitious*: Multivariate RC forecasting with graph neural networks, with vol-targeted portfolio backtest

**One-line pitch**: Forecast the realized covariance matrix of 50 large-cap stocks using a graph neural network on the SPD manifold, evaluate via minimum-variance portfolio out-of-sample variance and tracking error, and compare against DCC, HAR-DRD, BPQ-multivariate-HARQ, and Cholesky-HAR.

**What it does**: Build daily RC matrices from 5-min returns for top-50 S&P 500 names 2010–2024. Implement (a) DCC-GARCH (low-dim baseline), (b) HAR-DRD / BPQ multivariate-HARQ (Bollerslev-Patton-Quaedvlieg 2018) — strongest econometric, (c) Cholesky-HAR-NN (Bucci 2020), (d) Graph-HAR with Graphical Lasso adjacency (Zhang-Pu-Cucuringu-Dong 2024), (e) GNN with nonlinear spillover. Build minimum-variance and risk-parity portfolios from each forecast, measure realised portfolio variance, turnover and net-of-cost Sharpe. Use realised quarticity-adjusted MCS and Diebold-Mariano on Frobenius / log-Frobenius / QLIKE losses.

**Trading floor relevance**: Risk systems, portfolio construction, factor risk model overlay — all GS quant strategies / portfolio analytics roles use exactly these forecasts.

**Data**: 50 tickers' daily 5-min RV/RC from a free intraday source (Alpaca, Polygon free, or paid FirstRate ~$200) — feasible for 50 names. Or use Oxford-Man + simulated cross-asset from S&P sectors only (ETF data is free).

**ML methods**: GNN (PyTorch Geometric or DGL); SPDNet for covariance manifold (geometric DL).

**Baselines**: DCC, HAR-DRD, multivariate HARQ (BPQ), Cholesky-HAR.

**Feasibility**: Medium. The main risk is data construction — 5-min RC for 50 stocks across 14 years is non-trivial (refresh-time, cleaning).

**Risks**: Data plumbing is the bottleneck; budget 3 weeks for it. Graph topology choice (sector vs Graphical-Lasso vs full) materially affects results.

**Wow factor**: Geometric deep learning on the SPD manifold + economic value via min-var portfolio Sharpe. Direct connection to Goldman's risk systems and portfolio-construction services.

**Novelty**: High — recent Oxford / Cucuringu work on graph-based RC forecasting (2022–2024) is at the frontier; SPDNet for finance is barely explored.

### Project 4 — *Ambitious*: Rough volatility vs deep learning — universal forecaster with VRP-aware ML correction

**One-line pitch**: Replicate the Rosenbaum-Zhang universal LSTM, build a parsimonious RFSV+QRH parametric forecaster, and combine them via residual ML using options-implied (VRP) and microstructure features — explicitly testing the Cont-Das "fact-or-artefact" question on the data.

**What it does**: For 100+ liquid US stocks plus 5–10 cross-asset indices (S&P, Nasdaq, FTSE, DAX, USD/EUR, gold, oil), 2005–2024:
1. Estimate Hurst exponent per asset using both GJR-style log-RV regression *and* Cont-Das normalised p-variation; document the gap.
2. Implement RFSV one-step forecasting formula (single-parameter prediction).
3. Train Rosenbaum-Zhang universal LSTM on pooled data; verify universality by holding out stocks.
4. Build a residual-correcting LightGBM/MLP using VRP, IV term structure, signed jumps, intraday-commonality features (Zhang-Cucuringu-Dong 2022).
5. Full QLIKE/MSE comparison vs HARQ, with MCS at 1- and 22-day horizons; cross-asset universality test.
6. Honest narrative: which Hurst exponent is "true"; whether the LSTM and rough-vol parametric model essentially learn the same thing (Rosenbaum-Zhang's central finding); where ML adds genuine information beyond the universal kernel.

**Trading floor relevance**: Rough volatility models are now used in vol-trading desks (Risk Awards 2021); the empirical question of universality and the role of options info is live and relevant to vol arbitrage and volatility-of-volatility products.

**Data**: Free archival Oxford-Man; CBOE for VIX/IV; OptionMetrics if available via institutional GS access (otherwise just SPX VIX-style proxies for ETFs). FRED for macro.

**ML methods**: LSTM (universal, pooled); LightGBM residual; RFSV closed-form; QRH simulation only if very ambitious.

**Baselines**: HAR, HARQ, SHAR, RFSV, RFSV+QRH, universal LSTM.

**Feasibility**: Medium-low (ambitious for 12 weeks). The Hurst-estimation diagnostic + Cont-Das robustness check + universal LSTM replication is already 8 weeks. Cut QRH if pressed.

**Risks**: Time pressure. Rough-vol simulation is heavy. Mitigation: use the *forecasting* form of RFSV (closed-form one-step prediction) without full SDE simulation.

**Wow factor**: Engages directly with the most active current debate in volatility theory; combines pure-stats rough-vol with deep learning; produces an honest answer to "is it just universal log-vol persistence?"

**Novelty**: High. Replicates and extends Rosenbaum-Zhang (2022) plus Cont-Das (2024) in one coherent framework — there is no published paper combining these.

### Project 5 — *Highest novelty / wow*: Variance Risk Premium machine-learning trader with options-replication backtest

**One-line pitch**: Build an ML system that forecasts the variance risk premium (VRP) per stock and translates it into a delta-hedged-straddle / variance-swap-replication trading signal, rigorously backtested with transaction costs.

**What it does**: For S&P 500 sector ETFs (SPY, XLF, XLE, XLK, etc.) plus VIX/VVIX (most liquid options chains, free data via CBOE / Yahoo / Polygon):
1. Construct daily VRP_t = IV²_t − E_t[RV_{t+30}] using VIX-style model-free implied variance (Britten-Jones-Neuberger 2000) for the IV side and an ML forecast E_t[RV_{t+30}] for the physical side.
2. Decompose VRP into normal vs jump-tail components (Bollerslev-Todorov 2015).
3. Use VRP, term-structure of VRP, and lagged returns to predict 1-month-ahead realised variance — a hierarchical ML model (Fouhy SSRN 6570380 framework but cross-sectional).
4. Translate signal into a sector-level short-vol overlay (delta-hedged-straddle proxy or variance swap synthesis), with realistic bid-ask costs and rebalancing frequency.
5. Compare net-of-cost Sharpe vs naive short-VIX-futures and vs always-on short-vol carry.

**Trading floor relevance**: Direct relevance to GS systematic vol-trading and macro-strategies desks. VRP-driven trading is a real-world strategy.

**Data**: All free — CBOE for VIX/sector VIX, Yahoo / Polygon free tier for ETF options, FRED for risk-free rate.

**ML methods**: Gradient boosting for VRP-physical-RV; LSTM for term-structure dynamics; SHAP for interpretation.

**Baselines**: BTZ-style linear regression (Bollerslev-Tauchen-Zhou 2009); always-short-vol carry.

**Feasibility**: Medium. Options-replication mechanics are the technical risk; using sector VIX-style indices simplifies materially.

**Risks**: VRP is a noisy signal at the daily level; gains accrue over multi-month holding periods, so drawdown and t-stat need care. Transaction-cost realism is critical — a sloppy backtest produces inflated Sharpes.

**Wow factor**: End-to-end PnL story, rigorous economic translation, options-market relevance — exactly the language of a vol-trading desk.

**Novelty**: High; there are few public ML-VRP papers and none with a clean sector-decomposed strategy backtest.

**Recommended portfolio**: Project 1 (safety) as a backbone deliverable + Project 2 *or* Project 3 as the "main impressive thing", with Project 4 or 5 elements grafted on if time permits. The user's IMC Prosperity 3rd-place UK background and quant-trading literacy make Project 5 genuinely tractable; Project 4 leverages Imperial deep-learning training plus Imperial connections to rough-vol researchers (Jacquier, Muguruza, Pakkanen).

---

## PART 3 — ANNOTATED BIBLIOGRAPHY (curated, ~30 essential resources)

### A. Foundational realized-volatility econometrics

1. **Andersen, Bollerslev, Diebold & Labys (2001/2003), "The Distribution of Realized Exchange Rate Volatility / Modeling and Forecasting Realized Volatility"** — *JASA* / *Econometrica*. https://www.bis.org/cgfs/Diebold-et-al.pdf — Foundational papers introducing RV from high-frequency returns. **Essential** background; read the *Econometrica* paper.

2. **Barndorff-Nielsen, Hansen, Lunde & Shephard (2008), "Designing Realized Kernels…"** — *Econometrica* 76. https://onlinelibrary.wiley.com/doi/abs/10.3982/ECTA6495 — Defines the realized kernel, the noise-robust workhorse. **Essential** for any HF data pipeline.

3. **Zhang, Mykland & Aït-Sahalia (2005), "A Tale of Two Time Scales"** — *JASA*; **Zhang (2006), "Multi-scale realized vol"** — *Bernoulli*. https://arxiv.org/pdf/math/0411397 — Two-scale and multi-scale estimators; n^{−1/4} rate. **Recommended**.

4. **Liu, Patton & Sheppard (2015), "Does Anything Beat 5-Minute RV?"** — *J. Econometrics*. https://public.econ.duke.edu/~ap172/Patton_realized_measures_pres_oct12a.pdf — Comprehensive comparison of ~400 estimators across 31 assets. **Essential** practical guidance: 5-min RV is the right default.

5. **Patton (2011), "Volatility Forecast Comparison Using Imperfect Volatility Proxies"** — *J. Econometrics*. https://public.econ.duke.edu/~ap172/Patton_robust_JoE_forthcoming.pdf — Why QLIKE (and MSE) are robust to proxy noise. **Essential** for evaluation methodology.

6. **Hansen, Lunde & Nason (2011), "The Model Confidence Set"** — *Econometrica*. https://onlinelibrary.wiley.com/doi/10.3982/ECTA5771 — MCS procedure. **Essential** for proper multi-model comparison. R package: MCS.

7. **Lee & Mykland (2008/2012), "Jumps in Financial Markets" / "Jumps in Equilibrium Prices and MMS Noise"** — *RFS*. https://galton.uchicago.edu/~mykland/paperlinks/LeeMykland-2535.pdf — Nonparametric jump detection at intraday level. **Recommended**. Code: github.com/QuantLet/JumpDetectR.

### B. HAR family and econometric baselines

8. **Corsi (2009), "A Simple Approximate Long-Memory Model of Realized Volatility"** — *J. Financial Econometrics*. https://academic.oup.com/jfec/article-abstract/7/2/174/801493 — The HAR model. **Essential**.

9. **Bollerslev, Patton & Quaedvlieg (2016), "Exploiting the Errors: A Simple Approach for Improved Volatility Forecasting" (HARQ)** — *J. Econometrics*. https://public.econ.duke.edu/~ap172/BPQ_HARQ.pdf — HARQ uses RQ to attenuate. **Essential** baseline.

10. **Patton & Sheppard (2015), "Good Volatility, Bad Volatility: Signed Jumps and the Persistence of Volatility"** — *RestStat*. https://public.econ.duke.edu/~ap172/Patton_Sheppard_REStat_2015.pdf — Realized semi-variances and SHAR. **Essential** for feature engineering.

11. **Hansen, Huang & Shek (2012), "Realized GARCH"** — *J. Applied Econometrics*. https://onlinelibrary.wiley.com/doi/abs/10.1002/jae.1234 — Joint return / RV GARCH. **Recommended**.

12. **Barndorff-Nielsen, Kinnebrock & Shephard (2010), "Measuring Downside Risk — Realized Semi-variance"** — Engle Festschrift. https://www.nuffield.ox.ac.uk/economics/papers/2008/w2/downside.pdf — Defines RS⁺/RS⁻. **Recommended**.

13. **Kevin Sheppard's `arch` Python package** — github.com/bashtage/arch + https://www.kevinsheppard.com/ — GARCH, HAR, MCS, bootstrap inference; the standard library. **Essential** code resource. Free, open-source.

### C. Rough volatility

14. **Gatheral, Jaisson & Rosenbaum (2018), "Volatility Is Rough"** — *Quantitative Finance*. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2509457 — RFSV model; H ≈ 0.1. **Essential**.

15. **Bayer, Friz & Gatheral (2016), "Pricing under Rough Volatility"** — *Quantitative Finance* — rough Bergomi. **Recommended**.

16. **Cont & Das (2024), "Rough Volatility: Fact or Artefact?"** — *Sankhya B*. https://link.springer.com/article/10.1007/s13571-024-00322-2 — Critical methodological response: realized-vol roughness is partly noise. **Essential** for honest framing.

17. **Rosenbaum & Zhang (2022), "On the universality of the volatility formation process: when machine learning and rough volatility agree"** — arXiv 2206.14114. https://arxiv.org/abs/2206.14114 — Universal LSTM matches RFSV+QRH. **Essential** if attempting Project 4.

18. **Horvath, Muguruza & Tomas (2021), "Deep Learning Volatility"** — *Quantitative Finance*. https://arxiv.org/abs/1901.09647. Code: github.com/amuguruza/NN-StochVol-Calibrations — Neural-net calibration of rough-vol pricing maps. **Recommended**, especially for options-side projects.

### D. ML for RV — core empirical evidence

19. **Christensen, Siggaard & Veliyev (2023), "A Machine Learning Approach to Volatility Forecasting"** — *J. Financial Econometrics*. https://academic.oup.com/jfec/article-abstract/21/5/1680/6612759 + https://arxiv.org/abs/2601.13014 (corrected version). Honest, careful comparison: ML beats HAR modestly with rich features, more at longer horizons. **Essential**.

20. **Rahimikia & Poon (2020), "Machine Learning for Realised Volatility Forecasting" + "Alternative Data: LOB and News"** — SSRN 3707796 / 3684040. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3707796 — LSTM + LOB + news; CHAR baseline. **Essential** for Project 1/2.

21. **Bucci (2020), "Realized Volatility Forecasting with Neural Networks"** — *J. Financial Econometrics*. https://academic.oup.com/jfec/article-abstract/18/3/502/5856840 — RNN/LSTM/NARX vs ARFIMA/HAR. **Recommended**.

22. **Branco, Rubesam & Zevallos (2022/2024), "Forecasting Realized Volatility: Does Anything Beat Linear Models?"** — SSRN 4228131 / *J. Empirical Finance*. https://www.sciencedirect.com/science/article/abs/pii/S0927539824000598 — Honest counterweight: nonlinear ML may *not* statistically beat linear HAR-X. **Essential**.

23. **"HARd to Beat: The Overlooked Impact of Rolling Windows in the Era of Machine Learning" (2024)** — https://arxiv.org/pdf/2406.08041 — Properly fitted HAR matches/beats off-the-shelf ML. **Essential** for honesty narrative.

24. **Audrino & Knaus (2016), "Lassoing the HAR Model"** — *Econometric Reviews* — regularised linear HAR. **Recommended**.

25. **Moreno-Pino & Zohren (2022), "DeepVol: Volatility Forecasting from High-Frequency Data with Dilated Causal Convolutions"** — arXiv 2210.04797. https://arxiv.org/abs/2210.04797 — TCN approach. **Recommended** for Project 2.

26. **Sirignano & Cont (2019), "Universal features of price formation: Perspectives from deep learning"** — *Quantitative Finance*. https://www.tandfonline.com/doi/abs/10.1080/14697688.2019.1622295 — Pooled LSTM on LOB, ~500 NASDAQ stocks. **Recommended**.

27. **Zhang, Zohren & Roberts (2019), "DeepLOB"** — *IEEE Trans. Signal Processing*. https://arxiv.org/abs/1808.03668 — CNN-LSTM on LOB; the canonical LOB deep-learning paper. **Recommended**.

28. **Chen & Robert (2022), "Multivariate Realized Volatility Forecasting with Graph Neural Network"** — ACM ICAIF. https://arxiv.org/abs/2112.09015 — Graph Transformer on Optiver-style data. **Essential** for Project 2/3.

29. **Zhang, Cucuringu & Dong (2024), "Graph-Based Methods for Forecasting Realized Covariances"** — *J. Financial Econometrics* nbae026. https://academic.oup.com/jfec/article/23/2/nbae026/7889003 — Graphical-Lasso + HAR; beats DCC and HAR-DRD. **Essential** for Project 3.

30. **Zhang, Cucuringu & Dong (2022), "Volatility forecasting with ML and intraday commonality"** — arXiv 2202.08962 — HAR for intraday commonality. **Recommended** for Project 2.

### E. VRP and options-implied

31. **Bollerslev, Tauchen & Zhou (2009), "Expected Stock Returns and Variance Risk Premia"** — *RFS*. https://academic.oup.com/rfs/article-abstract/22/11/4463/1565787 — Foundational VRP paper. **Essential** for Project 5.

32. **Bollerslev, Li & Todorov (2015), "Tail Risk Premia and Return Predictability"** — *J. Financial Economics* — VRP decomposition. **Recommended**.

### F. Multivariate

33. **Bollerslev, Patton & Quaedvlieg (2018), "Modeling and Forecasting (Un)Reliable Realized Covariances…"** — *J. Econometrics*. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2759388 — Multivariate HARQ. **Essential** for Project 3.

34. **Bollerslev, Li, Patton & Quaedvlieg (2020), "Realized Semicovariances"** — *Econometrica*. https://public.econ.duke.edu/~boller/Papers/Realized_Semicovariances.pdf — **Essential** for Project 3.

35. **Diebold & Yilmaz (2009/2012/2014), "Connectedness/Spillovers"** — *Economic Journal*, *IJF*, *J. Econometrics*. https://financialconnectedness.org/research.html — Volatility spillover indices via VAR. **Recommended**.

### G. Methodology, validation and practice

36. **López de Prado, "Advances in Financial Machine Learning" (Wiley 2018)** — Especially Ch. 5 (fractional differencing), 7 (purged k-fold + embargo), 8 (feature importance), 14 (Deflated Sharpe). **Essential** textbook. ~$60.

37. **Tsay, "Analysis of Financial Time Series" (Wiley 3rd ed., 2010)** — Standard textbook GARCH/SV. **Recommended**. ~$120.

### H. Code & data resources

38. **Oxford-Man Realized Library** — https://realized.oxford-man.ox.ac.uk/data — Daily 5-min RV, kernels, etc. for ~25 indices; **discontinued mid-2022**, but archival mirrors exist (R packages `bvhar`, `highfrequency`). Free.

39. **VOLARE (2025), VOLatility Archive for Realized Estimates** — https://arxiv.org/pdf/2602.19732 — Open-access successor to Oxford-Man. **Essential** if it's released by start date.

40. **LOBSTER** — https://lobsterdata.com — Reconstructed L2/L3 NASDAQ LOB from ITCH; sample data free, full historical data is a paid academic subscription. **Recommended** for Project 2 extension.

41. **Optiver Realized Volatility Prediction (Kaggle 2021)** — https://www.kaggle.com/c/optiver-realized-volatility-prediction — Free LOB data + ~3000 published solutions. **Essential** for Project 2.

42. **Nixtla NeuralForecast** — https://nixtlaverse.nixtla.io/neuralforecast — Reference implementations of N-BEATS, N-HiTS, PatchTST, TFT. Free, MIT licensed.

43. **`highfrequency` R package** — https://cran.r-project.org/package=highfrequency — All major realized estimators, jump tests, multivariate kernels. Free.

### I. Surveys and reviews

44. **Springer Financial Innovation (2025), "Advances in Forecasting Realized Volatility: A Review of Methodologies"** — https://link.springer.com/article/10.1186/s40854-025-00809-5 — Recent survey; useful map. **Recommended**.

45. **Worldscientific, "A Survey of Rough Volatility" (2025)** — https://www.worldscientific.com/doi/10.1142/S0219024925300021 — Comprehensive survey including the roughness debate. **Recommended**.

---

## PART 4 — GAPS AND HONEST UNKNOWNS / QUESTIONS FOR MANAGER

1. **Data access**: Does the user have GS-internal access to OptionMetrics, TAQ, internal LOB / aggregated trade tape? The choice between Project 1 (Oxford-Man / public) and Projects 2–5 (LOBSTER/internal LOB, OptionMetrics) hinges on this.
2. **Compute**: Will GPU training be available? DeepVol/Graph-Transformer/LSTM-pooled training benefits materially from GPU.
3. **Floor audience**: Vol-trading desk vs systematic-strategies vs risk-management vs market-making-engineering — each cares about a different metric. Confirm the audience to right-size the economic-value translation (PnL vs VaR backtest vs Sharpe).
4. **Forecast horizon priorities**: 10-min (market-making), 1-day (risk), 1-month (vol carry / VRP)? Different projects suit different horizons.
5. **Asset class scope**: Single-name equities vs index vs FX vs rates vs commodities? Cross-asset universality is a publishable angle but expands scope significantly.
6. **Production constraints**: Is there a latency budget? If the desk wants to deploy, transformers/GNNs may be too slow at decision time; LightGBM is more deployable.
7. **Existing internal baselines**: GS likely has an internal HAR/HEAVY production model. What's the in-house benchmark to beat?
8. **Realised "truth" definition**: Some desks use 5-min RV, some use realized kernels, some prefer truncated RV. Get the desk's preferred target before starting.
9. **Open empirical questions where public info runs out**:
   - How much do internal proprietary microstructure features (e.g. internal client-flow, GS execution data) add to public LOB features?
   - What is the actual PnL improvement from a 5–10% QLIKE win in a real options-market-making book? (Theory says ~bps in spread; concrete number is firm-specific.)
   - What is the baseline an internal "production" LSTM/GBM is achieving? Beating GS internal models is a much higher bar than beating HAR.
10. **Rough-vol calibration speed in production**: Is rough-vol-based pricing in live use at GS, or research only? (Public: BNP, Bloomberg do; GS unclear.)

Ask these questions in week 1, before scoping is locked.

---

## PART 5 — RAW SOURCE LOG (URLs consulted)

- https://ideas.repec.org/p/aah/create/2021-03.html
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3707796
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4228131
- https://arxiv.org/pdf/2406.08041
- https://arxiv.org/html/2108.00480v6 (and v4)
- https://academic.oup.com/jfec/article-abstract/21/5/1680/6612759
- https://www.tandfonline.com/doi/full/10.1080/13504851.2024.2401512
- https://www.sciencedirect.com/science/article/abs/pii/S0927539824000598
- https://www.mdpi.com/1911-8074/18/12/685
- https://arxiv.org/pdf/2112.09015
- https://arxiv.org/abs/2112.09015
- https://ideas.repec.org/p/arx/papers/2112.09015.html
- https://arxiv.org/pdf/2310.14536
- https://www.sciencedirect.com/science/article/abs/pii/S1568494625003278
- https://arxiv.org/pdf/2109.12621
- https://dl.acm.org/doi/10.1016/j.engappai.2024.108223
- https://arxiv.org/html/2604.02743v3
- https://arxiv.org/html/2311.04727
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2509457
- https://www.tandfonline.com/doi/abs/10.1080/14697688.2017.1393551
- https://arxiv.org/pdf/2312.01426
- https://arxiv.org/pdf/2206.14114
- https://arxiv.org/pdf/1710.07481
- https://arxiv.org/pdf/2407.10659
- https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1616485/full
- https://www.researchgate.net/publication/329173050_Deep_learning_for_limit_order_books
- https://github.com/jessgess/deep-learning-for-order-book-price-and-movement-predictions
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12315853/
- https://arxiv.org/html/2308.14235
- https://arxiv.org/html/2502.15757v1
- https://www.mdpi.com/2227-9091/12/1/12
- https://dergipark.org.tr/en/pub/erciyesiibd/article/1499398
- https://arxiv.org/html/2601.13014 (and v1)
- https://www.semanticscholar.org/paper/Exploiting-the-errors:-A-simple-approach-for-Bollerslev-Patton/348420be931aa69493f2164a54363dce0aa2ebec
- https://public.econ.duke.edu/~ap172/BPQ_MV_HARQ_apr16.pdf
- https://link.springer.com/article/10.1007/s10614-024-10674-6
- https://www.researchgate.net/publication/283686848_Exploiting_the_errors:_A_simple_approach_for_improved_volatility_forecasting
- https://ideas.repec.org/p/aah/create/2015-14.html
- https://github.com/michaelpoluektov/orvp
- https://koeusiss.medium.com/optiver-realized-volatility-prediction-cb7da76fbd3f
- https://www.kaggle.com/competitions/optiver-realized-volatility-prediction
- https://www.kaggle.com/competitions/optiver-sjtu-realized-volatility-prediction
- https://github.com/Mrutyunjay01/Optiver-realized-volatility-prediction-kaggle21
- https://github.com/taher-software/Optiver-Realized-Volatility-Prediction
- https://chrisrichardmiles.github.io/chrisrichardmiles/projects/optiver/index_optiver.html
- https://kclpure.kcl.ac.uk/portal/en/publications/rough-volatility-fact-or-artefact/
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4065951
- https://www.tandfonline.com/doi/full/10.1080/14697688.2024.2399284
- https://link.springer.com/article/10.1007/s13571-024-00322-2
- https://www.worldscientific.com/doi/10.1142/S0219024925300021
- https://arxiv.org/pdf/2203.13820
- https://arxiv.org/pdf/2507.00575
- https://ideas.repec.org/p/fip/fedgif/1035.html
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=948309
- https://academic.oup.com/rfs/article-abstract/22/11/4463/1565787
- https://www.nber.org/system/files/working_papers/w27108/w27108.pdf
- https://public.econ.duke.edu/~boller/Published_Papers/rfs_09.pdf
- https://www.sciencedirect.com/science/article/abs/pii/S0304405X15001269
- https://arxiv.org/pdf/2211.04184
- https://www.financialconnectedness.org/research.html
- https://financialconnectedness.org/book/research.html
- https://academic.oup.com/ej/article-abstract/119/534/158/5089555
- https://www.tandfonline.com/doi/full/10.1080/23322039.2023.2254560
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10159833/
- https://arxiv.org/pdf/2602.19740
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7920753/
- https://realized.oxford-man.ox.ac.uk/
- https://realized.oxford-man.ox.ac.uk/data
- https://realized.oxford-man.ox.ac.uk/tag/data
- https://oxford-man.ox.ac.uk/research/realized-library/
- https://rdrr.io/rforge/highfrequency/man/realized_library.html
- https://search.r-project.org/CRAN/refmans/bvhar/html/oxfordman.html
- https://github.com/andymogul/SpilloverVolPrediction
- https://arxiv.org/pdf/2412.14353
- https://arxiv.org/pdf/2602.19732
- https://academic.oup.com/book/5659/chapter/148715572
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1262194
- https://ideas.repec.org/p/oxf/wpaper/382.html
- https://repub.eur.nl/pub/129249/Repub_129249.pdf
- https://icmaif.soc.uoc.gr/Year/2014/papers/paper_3_65.pdf
- https://www.nuffield.ox.ac.uk/economics/papers/2008/w2/downside.pdf
- https://public.econ.duke.edu/~boller/Papers/Realized_Semicovariances.pdf
- https://public.econ.duke.edu/~ap172/Patton_Sheppard_REStat_2015.pdf
- https://arxiv.org/pdf/2006.00158
- https://arxiv.org/pdf/1908.08806
- https://ideas.repec.org/a/taf/quantf/v21y2021i1p11-27.html
- https://arxiv.org/pdf/2412.02135
- https://arxiv.org/pdf/2306.11061
- https://www.tandfonline.com/doi/full/10.1080/14697688.2020.1817974
- https://arxiv.org/pdf/1901.09647
- https://arxiv.org/pdf/2309.14784
- https://github.com/amuguruza/NN-StochVol-Calibrations
- https://antonio-velazquez-bustamante.medium.com/kfold-cross-validation-with-purging-and-embargo-...
- https://en.wikipedia.org/wiki/Purged_cross-validation
- https://toc.library.ethz.ch/objects/pdf03/e01_978-1-119-48208-6_01.pdf
- https://towardsai.net/p/l/the-combinatorial-purged-cross-validation-method
- https://www.smallake.kr/wp-content/uploads/2018/07/SSRN-id3104847.pdf
- https://reasonabledeviations.com/notes/adv_fin_ml/
- https://philpapers.org/rec/LPEAIF
- https://arxiv.org/pdf/2401.16407
- https://zenodo.org/records/15681
- https://pypi.org/project/arch/
- https://github.com/bashtage/arch
- https://github.com/bashtage/arch/blob/main/arch/univariate/volatility.py
- https://www.kevinsheppard.com/
- https://goldinlocks.github.io/ARCH_GARCH-Volatility-Forecasting/
- https://arch.readthedocs.io/en/stable/univariate/univariate_volatility_forecasting.html
- https://arxiv.org/pdf/0901.2275
- https://link.springer.com/article/10.1186/s40854-025-00809-5
- https://link.springer.com/article/10.1007/s10690-024-09510-6
- https://ieeexplore.ieee.org/document/9543438/
- https://www.scribd.com/document/858633963/LightGBM-Based-Optiver-Realized-Volatility-Prediction
- https://machinelearningmastery.com/xgboost-for-time-series-forecasting/
- https://arxiv.org/pdf/2501.07580
- https://dl.acm.org/doi/10.1145/3708036.3708234
- https://www.scribd.com/document/696305583/125971589
- https://ssrn.com/abstract=3707796
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3684040
- https://research.manchester.ac.uk/en/publications/alternative-data-for-realised-volatility-forecasting-limit-order-/
- http://wp.lancs.ac.uk/finec2023/files/2023/01/FEC-2023-033-Ser-huang-Poon.pdf
- https://www.semanticscholar.org/paper/Big-Data-Approach-to-Realised-Volatility-Using-HAR-Rahimikia-Poon/fec8b17e38670acdb901f9fbb613b70c08170bf4
- https://www.researchgate.net/publication/344306043_Alternative_Data_for_Realised_Volatility_Forecasting_Limit_Order_Book_and_News_Stories
- https://arxiv.org/pdf/2402.14989
- https://dl.acm.org/doi/10.5555/3495724.3496286
- https://global-sci.com/jml/article/view/23893
- https://arxiv.org/html/2402.14989v2
- https://scispace.com/pdf/on-neural-differential-equations-1kltl88t.pdf
- https://openreview.net/pdf?id=padYzanQNbg
- https://arxiv.org/pdf/2007.04154
- https://ideas.repec.org/a/eee/intfor/v34y2018i4p622-635.html
- https://www.rdocumentation.org/packages/MCS/versions/0.1.3/topics/LossVol
- https://www.researchgate.net/publication/4994565_Choosing_the_Best_Volatility_Models_The_Model_Confidence_Set_Approach
- https://www.sciencedirect.com/science/article/abs/pii/S2452306222000764
- https://www.researchgate.net/publication/227349721_The_Model_Confidence_Set
- https://cran.r-project.org/web/packages/MCS/MCS.pdf
- https://ideas.repec.org/a/bla/obuest/v65y2003is1p839-861.html
- https://academic.oup.com/jfec/article/23/2/nbae026/7889003
- https://arxiv.org/pdf/1906.05065
- https://arxiv.org/html/2509.05911
- https://arxiv.org/pdf/2509.05911
- https://arxiv.org/pdf/1904.12834
- https://arxiv.org/pdf/2405.11730
- https://arxiv.org/pdf/2509.11928
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1533475
- https://www.researchgate.net/publication/239804642_Realized_GARCH_A_Complete_Model_of_Returns_and_Realized_Measures_of_Volatility
- https://ideas.repec.org/p/aah/create/2010-13.html
- https://www.scirp.org/(S(lz5mqp453edsnp55rrgjct55))/reference/referencespapers.aspx?referenceid=1703059
- https://pure.au.dk/ws/files/41577306/rp10_13.pdf
- https://www.eief.it/files/2010/01/peter-hansens-paper.pdf
- https://onlinelibrary.wiley.com/doi/abs/10.1002/jae.1234
- https://nsd.pku.edu.cn/attachments/2ae2f86baaa248d7b5d6db3f50157938.pdf
- https://pure.au.dk/ws/files/50927447/rp12_44.pdf
- https://academic.oup.com/rfs/article-abstract/21/6/2535/1574138
- https://github.com/QuantLet/JumpDetectR
- https://github.com/YalDan/JumpDetectR
- https://www.sciencedirect.com/science/article/pii/S1544612323011868
- https://galton.uchicago.edu/~mykland/paperlinks/LeeMykland-2535.pdf
- https://rdrr.io/github/YalDan/hf.econometrics/man/LM_JumpTest.html
- https://arxiv.org/pdf/2403.00819
- https://www.bayes.citystgeorges.ac.uk/__data/assets/pdf_file/0020/67025/Abstracts.pdf
- https://arxiv.org/pdf/1708.09520
- https://thesis.eur.nl/pub/38661/Li-X.-422186-.pdf
- https://ideas.repec.org/a/eee/econom/v160y2011i1p246-256.html
- https://www.sciencedirect.com/science/article/pii/S0169207025000743
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=932890
- https://www.sciencedirect.com/science/article/abs/pii/S030440761000076X
- https://public.econ.duke.edu/~ap172/Patton_robust_JoE_forthcoming.pdf
- https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054xGMUAY.pdf
- https://public.econ.duke.edu/~ap172/Patton_robust_forecast_eval_11dec08.pdf
- https://arxiv.org/pdf/2110.01189
- https://medium.com/the-forecaster/patchtst-a-breakthrough-in-time-series-forecasting-e02d48869ccc
- https://www.datasciencewithmarco.com/blog/patchtst-a-breakthrough-in-time-series-forecasting
- https://arxiv.org/html/2512.22326
- https://arxiv.org/html/2601.20448v1
- https://arxiv.org/pdf/2408.16707
- https://arxiv.org/html/2501.08620v3
- https://nixtlaverse.nixtla.io/neuralforecast/models.patchtst.html
- https://github.com/aditya-saxena-7/Optiver-Realized-Volatility-Prediction/blob/main/codeBase/BaseCode.ipynb
- https://ideas.repec.org/a/oup/jfinec/v18y2020i3p502-531..html
- https://www.mdpi.com/2674-1032/4/4/61
- https://www.sciencedirect.com/science/article/abs/pii/S0927539823000683
- https://academic.oup.com/jfec/article-abstract/18/3/502/5856840
- https://onlinelibrary.wiley.com/doi/10.1002/fut.70046
- https://dl.acm.org/doi/10.1145/3533271.3561663
- https://www.semanticscholar.org/paper/Realized-Volatility-Forecasting-with-Neural-Bucci/38c4979da79f68e38c566e9b04c435deb3660aec
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3159577
- https://community.portfolio123.com/uploads/short-url/VxrHQ9WWYyZ2rNJ59rTtb9wtLK.pdf
- https://www.nber.org/papers/w25398
- https://www.tidy-finance.org/blog/gu-kelly-xiu-replication/
- https://www.scirp.org/reference/referencespapers?referenceid=3895984
- https://academic.oup.com/rfs/article/33/5/2223/5758276
- https://www.aqr.com/Insights/Research/Journal-Article/Empirical-Asset-Pricing-via-Machine-Learning
- https://www.nber.org/system/files/working_papers/w25398/w25398.pdf
- https://arxiv.org/pdf/2403.06779
- https://arxiv.org/pdf/2212.01048
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=620203
- https://shephard.scholars.harvard.edu/sites/g/files/omnuum7741/files/2025-06/olebernoulli.pdf
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1138418
- https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1368-423X.2008.00275.x
- https://onlinelibrary.wiley.com/doi/abs/10.3982/ECTA6495
- https://academic.oup.com/ectj/article-abstract/12/3/C1/5061260
- https://www.researchgate.net/publication/23525675_Designing_Realised_Kernels_to_Measure_Ex-Post_Variation_of_Equity_Prices_in_the_Presence_of_Noise
- https://arxiv.org/pdf/math/0411397
- https://projecteuclid.org/journals/bernoulli/volume-12/issue-6/Efficient-estimation-of-stochastic-volatility-using-noisy-observations--a/10.3150/bj/1165269149.full
- https://digitalcommons.usu.edu/cgi/viewcontent.cgi?article=1836&context=gradreports
- https://ideas.repec.org/p/nbr/nberwo/11380.html
- https://www.sciencedirect.com/science/article/abs/pii/S0304407617302294
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=731035
- https://link.springer.com/chapter/10.1007/978-3-540-71297-8_25
- https://galton.uchicago.edu/~mykland/paperlinks/JKScales103108.pdf
- https://www.maths.ox.ac.uk/node/63972
- https://arxiv.org/html/2412.09517v1
- https://ideas.repec.org/p/arx/papers/2308.01419.html
- https://link.springer.com/article/10.1007/s00521-023-08862-w
- https://arxiv.org/pdf/2107.10602
- https://arxiv.org/pdf/2412.09517
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1977207
- https://homepage.univie.ac.at/nikolaus.hautsch/lobster.html
- https://data.lobsterdata.com/info/DataStructure.php
- https://thalesians.com/resources/resources-datasets/
- https://www.researchgate.net/publication/228294842_LOBSTER_Limit_Order_Book_Reconstruction_System
- https://arxiv.org/pdf/1511.04116
- https://arxiv.org/html/2403.09267v1
- https://www.tandfonline.com/doi/abs/10.1080/14697688.2023.2203844
- https://www.tandfonline.com/doi/full/10.1080/14697688.2023.2203844
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6570380
- https://alphaarchitect.com/forecast-equity-risk-premium/
- https://arxiv.org/pdf/2410.11773
- https://arxiv.org/pdf/2503.00549
- https://ideas.repec.org/a/eee/econom/v187y2015i1p293-311.html
- https://books.google.com/books/about/Does_Anything_Beat_5_minute_RV.html?id=Wx_EvQEACAAJ
- https://agris.fao.org/agris-search/search.do?recordID=US201900028142
- https://scholars.duke.edu/publication/1075761
- https://economics.web.ox.ac.uk/publication/1143774/manual
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2214997
- https://scholars.duke.edu/display/pub1075761
- https://public.econ.duke.edu/~ap172/Patton_realized_measures_pres_oct12a.pdf
- https://www.researchgate.net/publication/256046801_Does_Anything_Beat_5-Minute_RV_A_Comparison_of_Realized_Measures_Across_Multiple_Asset_Classes
- https://ora.ox.ac.uk/objects/uuid:4a291238-52f0-44d2-9002-9047482df6e8
- https://ideas.repec.org/p/arx/papers/1808.03668.html
- https://ui.adsabs.harvard.edu/abs/2019ITSP...67.3001Z/abstract
- https://arxiv.org/pdf/1808.03668
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3519855
- https://www.researchgate.net/publication/327011035_DeepLOB_Deep_Convolutional_Neural_Networks_for_Limit_Order_Books
- https://www.oxford-man.ox.ac.uk/wp-content/uploads/2020/03/DeepLOB-Deep-Convolutional-Neural-Networks-for-Limit-Order-Books.pdf
- https://www.semanticscholar.org/paper/DeepLOB:-Deep-Convolutional-Neural-Networks-for-Zhang-Zohren/085870597c8a8421390d6590425003a13deefdd4
- https://arxiv.org/abs/1808.03668
- https://arxiv.org/pdf/2505.02139
- https://arxiv.org/pdf/2210.04797
- https://arxiv.org/pdf/2102.12658
- https://arxiv.org/pdf/2306.12446
- https://arxiv.org/pdf/2410.00288
- https://arxiv.org/pdf/1811.03711
- https://arxiv.org/pdf/2202.08962
- https://arxiv.org/pdf/2504.15985
- https://www.sciencedirect.com/science/article/abs/pii/S0304407621002517
- https://public.econ.duke.edu/~boller/Papers/BMPQ.pdf
- https://public.econ.duke.edu/~boller/Papers/Semi_JFEC_2022.pdf
- https://www.bis.org/cgfs/Diebold-et-al.pdf
- https://arxiv.org/pdf/2412.10791
- https://mpra.ub.uni-muenchen.de/95137/1/MPRA_paper_95137.pdf
- https://link.springer.com/article/10.1007/s11222-022-10157-4
- https://d-nb.info/1095666908/34
- https://arxiv.org/pdf/2002.08849
- https://arxiv.org/abs/2601.13014
- https://arxiv.org/html/2601.13014v1
- https://academic.oup.com/jfec/article/23/1/nbac032/6674615
- https://pure.au.dk/portal/en/publications/a-machine-learning-approach-to-volatility-forecasting/
- https://www.researchgate.net/publication/363007775_A_Machine_Learning_Approach_to_Volatility_Forecasting
- https://econpapers.repec.org/paper/aahcreate/2021-03.htm
- https://sites.google.com/site/rogierquaedvlieg/research
- https://www.sciencedirect.com/science/article/abs/pii/S1062976917303976
- https://arxiv.org/html/2506.07928v1
- https://www.aeaweb.org/conference/2024/program/paper/hiTeT8SE
- https://www.federalreserve.gov/pubs/feds/2010/201014/index.html
- https://www.bis.org/publ/work619.pdf
- https://onlinelibrary.wiley.com/doi/full/10.1002/fut.22589
- https://github.com/liyiyan128/optiver-trading-at-the-close
- https://fan2goa1.github.io/mkdocs-material/blog/2023/12/24/kaggle-optiver---trading-at-the-close/
- https://medium.com/@joehbridges/gauging-the-market-optivers-trading-at-the-close-kaggle-competition-27b73f7789c0
- https://developer.nvidia.com/blog/grandmaster-pro-tip-winning-first-place-in-kaggle-competition-with-feature-engineering-using-nvidia-cudf-pandas/
- https://www.kaggle.com/competitions/optiver-trading-at-the-close/writeups/hyd-1st-place-solution
- https://www.cmegroup.com/articles/whitepapers/was-2024-a-year-of-volatility.html
- https://data.lobsterdata.com/info/docs/LobsterReport.pdf

End of report.