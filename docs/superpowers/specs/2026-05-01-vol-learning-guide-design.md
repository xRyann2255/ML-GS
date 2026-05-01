# Volatility Learning Guide Design Spec

> **Comprehensive LaTeX learning guide for realized volatility estimation, forecasting, and ML.**
> Teaches everything needed to understand and execute any of the 5 project directions in VOL.md.

**Target reader:** Strong math/stats background, some ML experience, no volatility or options knowledge. Building volatility knowledge from scratch. Visual learner who needs diagrams before equations.

**Format:** LaTeX document using the same visual language as the ml-learning-guide (colored boxes, TikZ, worked examples), with three key improvements: (1) intuition-first/math-second sequencing, (2) significantly more diagrams, (3) shorter sections with one idea each.

**Source material:** `VOL.md` (788-line scoping document covering RV estimators, forecasting models, ML methods, feature engineering, VRP, multivariate volatility, 5 project directions, and ~45 annotated references)

---

## 1. Design Principles

Three problems with the ml-learning-guide that this document fixes:

### Problem 1: Too dense, too much at once

**Fix:** Bottom-up pedagogical structure. Every concept builds strictly on what came before. Chapters are shorter and more focused. Each `\section` or `\subsection` introduces exactly one concept. A "where we are" connector sentence at the start of each section ties back to the chapter thread.

### Problem 2: Equations without enough intuition

**Fix:** Intuition-first, math-second sequencing. Every major concept follows this exact sequence:

1. **Plain English**: one sentence saying what this thing does and why you care
2. **Visual**: a diagram showing the mechanism, geometry, or data
3. **Equation**: the formal math
4. **Term-by-term explanation**: bulleted list beneath the equation
5. **Worked example**: actual numbers flowing through the formula

The diagram comes *before* the math so the reader has a mental picture when the symbols arrive.

### Problem 3: Not enough diagrams

**Fix:** Diagrams as first-class content. Target: 40-60 TikZ/pgfplots diagrams across the guide (at least 2-3 per chapter, more for visual-heavy chapters). Types:

- **Process diagrams**: how RV is constructed from tick data, how HAR components combine
- **Geometric diagrams**: bias-variance curves, L1 vs L2 constraint sets
- **Data visualizations**: return distributions with fat tails, volatility clustering, IV surface wireframes, VIX vs RV time series
- **Architecture diagrams**: LSTM cell, TCN dilated convolutions, graph transformer
- **Comparison diagrams**: smooth vs rough paths at different H, HAR vs ML forecast overlays

---

## 2. Chapter Structure

### Part I: What Is Volatility and How Do You Measure It?

**Chapter 1: Returns, Variance, and Why Volatility Matters**

- What returns are (simple vs log), what variance captures
- Why volatility is central: options pricing, risk management, portfolio construction, execution
- Volatility clustering, fat tails, the stylized facts of financial returns
- Heavy on diagrams: return distributions, QQ plots, autocorrelation of returns vs squared returns
- No assumed finance knowledge; build from scratch

**Chapter 2: Realized Volatility**

- The core quantity: integrated variance of a continuous semimartingale
- RV as sum of squared intraday returns; convergence to quadratic variation as frequency increases
- Andersen-Bollerslev-Diebold-Labys (2001/2003) foundations
- 5-minute RV as the practical workhorse
- Liu-Patton-Sheppard (2015): "Does Anything Beat 5-Minute RV?" (across ~400 estimators, 31 assets, 5 asset classes: not really)
- Diagrams: constructing RV from intraday returns, convergence illustration

**Chapter 3: Microstructure Noise and Robust Estimators**

- Why naive high-frequency RV breaks: bid-ask bounce, discrete tick size, price staleness
- Hansen-Lunde (2006), Ait-Sahalia-Mykland-Zhang (2005): bias dominates signal as frequency increases
- Diagram: the "volatility signature plot" showing RV vs sampling frequency
- Noise-robust estimator families, each with a diagram of the mechanism:
  - TSRV (Zhang-Mykland-Ait-Sahalia 2005): two time scales, n^{-1/6} rate
  - MSRV (Zhang 2006): multiple scales, optimal n^{-1/4} rate
  - Realized kernel (Barndorff-Nielsen-Hansen-Lunde-Shephard 2008): flat-top kernel weighting
  - Pre-averaging (Jacod-Li-Mykland-Podolskij-Vetter 2009): local block averaging
  - Subsampling / averaging RV (Zhang-Mykland-Ait-Sahalia): related to TSRV
  - Fourier estimator (Malliavin-Mancino): covariation as Fourier coefficients
  - Quasi-MLE under noise (Xiu 2010): likelihood-based approach
- Comparison table: rate, assumptions, practical use case for each estimator
- When to use which: realized kernel as default workhorse, 5-min RV when simplicity matters

**Chapter 4: Jumps and Continuous Variation**

- Prices jump: continuous-time prices include a jump component beyond diffusion
- Bipower variation: BPV converges to integrated variance even with jumps
- BNS jump test (Barndorff-Nielsen-Shephard 2004, 2006): comparing RV minus BPV
- Lee-Mykland (2008, 2012): identifying jump times and sizes intraday
- Ait-Sahalia-Jacod (2009): power-variation-ratio test, robust to noise
- Threshold/truncation (Mancini; Corsi-Pirino-Reno 2010): continuous HAR-CJ decomposition
- Diagrams: price path with and without jumps, how BPV filters jumps, jump test decision flow
- Why the decomposition matters: jump vol and continuous vol have different persistence and predictability

### Part II: Forecasting Volatility with Classical Models

**Chapter 5: GARCH Family**

- Conditional variance from daily returns only (no intraday data needed)
- GARCH(1,1): the workhorse. $\sigma^2_t = \omega + \alpha r^2_{t-1} + \beta \sigma^2_{t-1}$
- Volatility clustering mechanism: large returns increase tomorrow's conditional variance
- EGARCH (Nelson 1991): log specification, captures leverage effect (negative returns increase vol more)
- GJR-GARCH (Glosten-Jagannathan-Runkle): asymmetric threshold
- FIGARCH (long memory)
- Realized GARCH (Hansen-Huang-Shek 2012): bridges GARCH and RV with a measurement equation
- HEAVY (Shephard-Sheppard 2010): joint daily-return / realized-measure model, closely related to Realized GARCH
- Diagrams: volatility clustering feedback loop, leverage effect asymmetry, GARCH vs Realized GARCH information flow

**Chapter 6: The HAR Model and Its Extensions**

- The benchmark that ML must beat. This chapter must be extremely clear.
- HAR (Corsi 2009): $RV_t = \beta_0 + \beta_d RV_{t-1} + \beta_w RV^{(w)}_{t-1} + \beta_m RV^{(m)}_{t-1} + \varepsilon_t$
- Heterogeneous market hypothesis: daily, weekly, monthly traders each contribute to vol dynamics
- Diagram: three trader horizons feeding into one forecast
- Extensions, each building on HAR:
  - HAR-J / HAR-CJ: split RV into continuous and jump parts (uses Ch. 4 knowledge)
  - SHAR (Patton-Sheppard 2015): realized semi-variances $RS^+$, $RS^-$; "bad volatility" persists more
  - HARQ (Bollerslev-Patton-Quaedvlieg 2016): attenuates noisy RV days using realized quarticity
  - HAR-X with leverage, VIX, macro variables
- Worked example: fit HAR on a small dataset, compute forecast, show how adding HARQ improves
- Why HAR is hard to beat at daily horizon with RV-only features (the honest baseline)

**Chapter 7: Rough Volatility**

- Gatheral-Jaisson-Rosenbaum (2018): log-RV across assets behaves like fractional Brownian motion with H ~ 0.1
- What the Hurst exponent means: H = 0.5 is Brownian motion, H < 0.5 is rougher (more jagged)
- Diagrams: sample paths at H = 0.1, 0.3, 0.5, 0.7 side by side (visual impact of roughness)
- RFSV one-step forecasting formula: parsimonious, competitive with HAR and LSTM
- Quadratic Rough Heston: first model to jointly fit SPX and VIX smiles
- The Cont-Das counterargument (Sankhya B 2024): observed roughness of *realized* vol is partly microstructure-noise artifact
- Practical implication: rough-vol features are useful but do not establish ground truth about the spot process
- Diagram: how noise creates apparent roughness in realized estimates even from a smooth spot process

### Part III: The Volatility Surface and Options-Implied Information

**Chapter 8: Options Basics and the Volatility Surface**

- What an option is: payoff diagrams for calls and puts
- Black-Scholes in one page: just enough to define implied volatility (the "wrong number to put in the wrong formula to get the right price")
- Implied volatility: the vol that makes Black-Scholes match the market price
- The IV surface: strike (or moneyness) x maturity
- Smile, skew, term structure: what each shape means economically
  - Smile: fat tails (both directions)
  - Skew: crash risk (left tail heavier)
  - Term structure: mean reversion of vol
- 3D wireframe diagram of the IV surface
- Cont-Fonseca PCA: level, slope, curvature as the dominant factors
- ATM IV, IV skew, model-free implied variance (Britten-Jones-Neuberger 2000)
- VIX construction: model-free implied variance of S&P 500 over 30 days

**Chapter 9: Variance Risk Premium**

- VRP = $E^Q[RV] - E^P[RV]$, operationalized as $(VIX/100)^2$ minus a forecast of next-30-day RV
- Bollerslev-Tauchen-Zhou (2009): VRP predicts quarterly equity excess returns, R-squared beating dividend yield
- Why VRP exists: risk-averse investors overpay for downside protection
- Drechsler-Yaron (2011): long-run risk equilibrium account
- Bekaert-Hoerova (2014): VRP decomposed into uncertainty vs risk aversion
- VRP also forecasts future RV through mean reversion
- Vol-of-vol: VVIX, realized vol-of-vol, jumps in VIX
- Diagram: VIX vs realized vol over 20 years showing the persistent gap (the VRP)
- ML approaches: Fouhy (2024) hierarchical XGBoost for VIX to RV to VRP
- Bollerslev-Todorov (2015): normal vs jump-tail VRP decomposition

### Part IV: ML Methods for Volatility

**Chapter 10: Feature Engineering for Volatility**

- The single highest-leverage area for any vol project
- Feature families, each with concrete construction and a worked example:
  - **Lagged RV transforms**: daily/weekly/monthly RV (HAR inputs), log-RV, sqrt-RV, fractional differences (Lopez de Prado AFML Ch. 5)
  - **Realized quarticity**: $RQ = (n/3)\sum r^4_i$, measurement-error variance estimator (HARQ feature)
  - **Signed/asymmetric features**: realized semi-variances $RS^+$, $RS^-$, signed jumps, realized semi-covariances (Bollerslev-Li-Patton-Quaedvlieg 2020), leverage effect features
  - **Higher moments**: realized skewness, realized kurtosis
  - **Microstructure/LOB features** (for intraday projects): bid-ask spread, order book imbalance, WAP log returns, volume profiles, trade direction, VPIN, market urgency (price_spread x liquidity_imbalance)
  - **Options-implied features**: ATM IV, IV term structure, IV skew, VRP proxy, VIX/VIX9D/VIX1Y/VVIX, Heston spot vol estimators
  - **Cross-asset features**: equity/rates/FX/credit RV, Diebold-Yilmaz spillover indices as features, sector/index RV as common factor
  - **Long-memory features**: fractional differencing (AFML Ch. 5), rolling Hurst exponent
  - **Calendar/event features**: FOMC, NFP, CPI, earnings, options expiry, quarter-end, intraday seasonal
  - **Sentiment/text features**: Audrino-Sigrist-Ballinari (2020), Rahimikia-Zohren-Poon financial word embeddings (modest gains)
- Feature importance and interpretability: ALE plots (Christensen-Siggaard-Veliyev), SHAP for trees, Lopez de Prado MDA/MDI
- Top Optiver Kaggle features: WAP log returns, log-return-of-log-return ("price acceleration"), volume-weighted time-bucketed aggregations

**Chapter 11: Tree-Based Methods for Volatility**

- LightGBM and XGBoost applied to volatility forecasting
- Christensen-Siggaard-Veliyev (2023, J. Financial Econometrics): tree-based models among the best for daily RV on 29 DJIA stocks (2001-2017); gains strongest with rich features and longer horizons
- Optiver Kaggle (2021): 10-min-ahead RV from L2 LOB, won by LightGBM ensembles; feature engineering mattered more than model class
- Audrino-Knaus (2016): "Lassoing the HAR"; regularized linear ML competes well
- Hyperparameters for vol data: low max_depth, high min_child_samples, aggressive regularization
- The honest assessment:
  - With only past RV as input: gains over carefully fitted HAR are small and fragile
  - "HARd to Beat" (arXiv 2406.08041): rolling-window HAR matches off-the-shelf ML on QLIKE
  - Branco-Rubesam-Zevallos (2022/2024): "no evidence nonlinear models outperform statistically"
  - With rich exogenous features: ML wins meaningfully (5-20% QLIKE)
  - In stress regimes (COVID, GFC): ML underperforms HAR; ensembles needed
- Rahimikia-Poon (2020): ML beats HAR ~90% of OOS days but fails in extreme stress; ensembling ML with HAR mitigates this

**Chapter 12: Deep Learning for Volatility**

Each method gets: what it does, architecture diagram, when it wins, when it doesn't.

- **LSTMs/GRUs**:
  - Bucci (2020): LSTM and NARX beat ARFIMA/HAR on MSE and QLIKE for S&P 500 monthly RV, especially 2008 crisis
  - Sirignano-Cont (2019): pooled LSTMs across ~500 NASDAQ stocks generalize to held-out tickers (universal features of price formation)
  - Rosenbaum-Zhang (2022): universal LSTM trained on hundreds of stocks matches RFSV+QRH parametric forecaster; empirical support for universal vol formation
  - Rahimikia-Poon (2020): LSTM + LOB + news, statistically significant gains on 23 NASDAQ tickers
- **TCN / DeepVol**:
  - Moreno-Pino-Zohren (2022): dilated causal convolutions on 1-min returns for day-ahead RV; beats HAR and LSTM; interpretable receptive field
  - Parameter efficiency vs LSTM; learns multi-scale patterns from raw HF data
- **CNN-LSTM / DeepLOB**:
  - DeepLOB (Zhang-Zohren-Roberts 2019, IEEE Trans. Signal Processing): the canonical LOB deep-learning paper; CNN-LSTM on raw LOB data
- **Transformers and attention**:
  - Mixed evidence. Chen-Robert (ACM ICAIF 2022) graph transformer for multivariate Optiver-style task outperforms LightGBM; combines LOB features with cross-sectional sector graphs
  - TLOB (2025): dual temporal/feature attention for LOB
  - Caution: long-horizon transformer benchmarks (PatchTST, Informer) have not beaten HAR on standard daily RV benchmarks
- **Modern TS architectures** (N-BEATS, N-HiTS, TiDE, TSMixer, PatchTST): limited rigorous evidence on RV; TiDE and DeepAR show promise with macro features but HAR matches DL with RV-only lags
- **Neural SDEs/CDEs/ODEs**: more for scenario generation and pricing than forecasting; Kidger (NeurIPS 2020, ICML 2021); direct RV forecasting applications rare
- **GPs**: principled uncertainty quantification, O(n^3) scaling limits to small samples
- **Reservoir computing / echo state networks**: niche; occasionally competitive with LSTM at much lower training cost; not mainstream for RV
- **Autoencoders/VAEs**: IV-surface compression (Ding-Lu-Cheung 2025), deep stochastic vol model (Xu-Chen AAAI 2021), co-training with normalizing flows (Du-Moriyama-Tanaka-Ishii 2023) for joint RV transformation + forecast
- The honest bottom line: at daily horizon with RV-only lags, carefully fitted HAR often matches DL

**Chapter 13: Hybrid and Ensemble Models**

- Almost universally, the strongest results combine econometric structure with ML flexibility
- HAR-SVR: SVR on HAR residuals
- GARCH-Informed Neural Net (GINN)
- Financial word embeddings + HAR (Rahimikia-Zohren-Poon)
- Ensemble HAR + LightGBM: consistently the safest performer across Rahimikia-Poon and Optiver leaderboards
- Why hybrids work: HAR captures the known linear structure; ML picks up the residual nonlinearity
- When to use pure ML vs hybrid: if HAR explains 80% of variance, let it; train ML on the remaining 20%

### Part V: Multivariate Volatility and Connectedness

**Chapter 14: Realized Covariance and Multivariate Forecasting**

- Realized covariance matrices from intraday data
- Non-synchronous trading problem: refresh-time sampling, Hayashi-Yoshida estimator
- Multivariate realized kernel (Barndorff-Nielsen-Hansen-Lunde-Shephard 2011): PSD estimator under noise
- Forecasting models:
  - DCC-GARCH (Engle 2002): low-dimensional conditional correlation
  - Wishart Autoregressive (Gourieroux-Jasiak-Sufana): matrix-variate autoregression
  - HAR-DRD (Bollerslev-Patton-Quaedvlieg 2018): separately HAR-model variances and correlations
  - Cholesky-HAR (Chiriac-Voev 2011)
  - Graph-HAR (Zhang-Pu-Cucuringu-Dong 2024): graphical-lasso adjacency + HAR, beats DCC and HAR-DRD
  - GNN with nonlinear spillover (Zhang-Cucuringu-Dong 2023)
  - CNN-RCOV on covariance matrices
  - SPDNet: geometric deep learning on the SPD manifold (preserves positive-definiteness)
- The positive-definiteness constraint: why forecasted covariance matrices must be PSD and how each method handles it
- Diagram: the SPD manifold and why Euclidean operations break PSD structure

**Chapter 15: Volatility Spillovers and Connectedness**

- Diebold-Yilmaz indices (2009, 2012, 2014): VAR + variance decomposition for total/directional connectedness
- TVP-VAR extensions (Antonakakis et al.)
- Network/graph approaches (Demirer-Diebold-Liu-Yilmaz 2018)
- Diagrams: network visualization of vol connectedness across asset classes
- Universal LSTM / cross-asset universality: Sirignano-Cont (2019), Rosenbaum-Zhang (2022); pooled training across assets, transfer to held-out instruments, universal H ~ 0.1
- Practical use: spillover indices as features for forecasting (cross-reference Ch. 10)

### Part VI: Evaluation and Practice

**Chapter 16: Forecast Evaluation**

- MSE: robust to imperfect proxies but outlier-sensitive in vol settings
- QLIKE: $L(\sigma^2, h) = \log h + \sigma^2/h$ (Patton 2011); robust to proxy noise AND less sensitive to extreme RV days; the preferred loss
- Mincer-Zarnowitz regressions for unbiasedness
- Diebold-Mariano test for pairwise predictive comparison
- Model Confidence Set (Hansen-Lunde-Nason 2011): returns a set of statistically indistinguishable best models at a given confidence level
- Purged K-fold CV with embargo (Lopez de Prado AFML Ch. 7): why standard K-fold fails for time series
- Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014): adjusting for multiple testing
- What doesn't work and why:
  - Random K-fold on time series data (catastrophic look-ahead)
  - Naive OOS R-squared without DM/MCS (tiny improvements are noise)
  - Overfitting to one regime (train 2015-2019, test 2020, COVID invalidates)
  - Look-ahead in feature construction (using day-t VIX to predict day-t vol)
  - Beating HAR by 0.5% (unlikely to translate to PnL)
  - Volatility of the forecast (high mean QLIKE but high forecast variance is useless for vol targeting)

**Chapter 17: Practical Applications and Project Directions**

- Where vol forecasts are used:
  - Options market-making: short-horizon RV feeds theoretical vol for option quotes
  - Vol trading / variance swaps / VIX futures: VRP-based signals
  - Risk management: VaR, ES, FRTB Internal Model Approach
  - Vol targeting / risk parity: position-sizing from forecast vol (Moreira-Muir 2017)
  - Execution: intraday vol forecasts shape VWAP/TWAP participation rates
  - Stress testing and capital
- Forecast horizons and which methods shine where:
  - Intraday (up to 30 min): microstructure features, LOB-driven ML
  - Daily: HAR family is the benchmark; ML wins only with rich features
  - Weekly to monthly: ML gains widen, macro/VRP adds value
  - Spillover / cross-asset: graph models and Diebold-Yilmaz
- The 5 project directions from VOL.md:
  1. **HARQ-X with ML residual augmentation** (safest): rigorous HAR baseline + ML, MCS evaluation, vol-targeting backtest
  2. **Intraday RV from LOB, Optiver-style** (medium): 10-min RV from L2 LOB, LightGBM + TCN + graph transformer
  3. **Multivariate realized covariance with GNNs** (medium-ambitious): graph-based RC forecasting, min-variance portfolio backtest
  4. **Rough vol vs deep learning** (ambitious): RFSV vs universal LSTM, Cont-Das robustness, VRP correction
  5. **VRP ML trader** (highest novelty): ML-forecasted VRP, delta-hedged straddle backtest, sector-level
- For each project direction, cover:
  - One-line pitch
  - Which chapters provide the required background
  - Data requirements
  - ML methods used
  - Baselines to beat
  - Feasibility assessment
  - What makes it impressive
- Recommended combinations and the "portfolio" approach

---

## 3. LaTeX Infrastructure

### Preamble

Clone the ml-learning-guide `preamble.tex` with these changes:

1. **Title**: "Realized Volatility: Estimation, Forecasting, and ML"
2. **Header right**: "Volatility Learning Guide"
3. **Rename `projectconnection`** to `application` with default title "Application"
4. **Add pgfplots** for data visualizations (IV surfaces, time series, distribution plots)
5. **Add vol-specific math shortcuts**:

```latex
\newcommand{\RV}{\operatorname{RV}}
\newcommand{\BPV}{\operatorname{BPV}}
\newcommand{\HAR}{\operatorname{HAR}}
\newcommand{\QLIKE}{\operatorname{QLIKE}}
\newcommand{\IVol}{\operatorname{IV}}  % \IV may conflict
\newcommand{\VRP}{\operatorname{VRP}}
\newcommand{\VVIX}{\operatorname{VVIX}}
```

Keep all existing ml-learning-guide shortcuts (they are still useful for the ML chapters).

### File Structure

```
vol-learning-guide/
├── main.tex
├── preamble.tex
├── references.bib
└── chapters/
    ├── 01-returns-variance-volatility.tex
    ├── 02-realized-volatility.tex
    ├── 03-microstructure-noise.tex
    ├── 04-jumps-continuous-variation.tex
    ├── 05-garch-family.tex
    ├── 06-har-model.tex
    ├── 07-rough-volatility.tex
    ├── 08-options-vol-surface.tex
    ├── 09-variance-risk-premium.tex
    ├── 10-feature-engineering.tex
    ├── 11-tree-methods-vol.tex
    ├── 12-deep-learning-vol.tex
    ├── 13-hybrid-ensemble.tex
    ├── 14-multivariate-volatility.tex
    ├── 15-spillovers-connectedness.tex
    ├── 16-forecast-evaluation.tex
    └── 17-applications-projects.tex
```

Location: `C:\Users\ryanv\Documents\Projects\ML\vol-learning-guide\`

**Diagrams:** TikZ and pgfplots diagrams are written inline within each chapter `.tex` file (no separate `figures/` directory). This keeps each chapter self-contained for the subagent workflow.

**Bibliography:** Use `natbib` with author-year style. All references go in `references.bib`. Cite with `\citep{}` for parenthetical and `\citet{}` for textual citations. The preamble includes `\usepackage[round]{natbib}` and `main.tex` ends with `\bibliographystyle{plainnat}` and `\bibliography{references}`.

**main.tex skeleton:**

```latex
\documentclass[11pt,a4paper]{report}
\input{preamble}

\begin{document}

% Title page
\begin{titlepage}
\centering
\vspace*{3cm}
{\Huge\bfseries Realized Volatility\\[0.4cm]
Estimation, Forecasting, and ML\par}
\vspace{1.5cm}
{\Large A Learning Guide\par}
\vspace{1cm}
{\Large Ryan Vincent\par}
\vfill
{\small Last compiled: \today\par}
\end{titlepage}

\tableofcontents
\newpage

\part{What Is Volatility and How Do You Measure It?}
\input{chapters/01-returns-variance-volatility}
\input{chapters/02-realized-volatility}
\input{chapters/03-microstructure-noise}
\input{chapters/04-jumps-continuous-variation}

\part{Forecasting Volatility with Classical Models}
\input{chapters/05-garch-family}
\input{chapters/06-har-model}
\input{chapters/07-rough-volatility}

\part{The Volatility Surface and Options-Implied Information}
\input{chapters/08-options-vol-surface}
\input{chapters/09-variance-risk-premium}

\part{ML Methods for Volatility}
\input{chapters/10-feature-engineering}
\input{chapters/11-tree-methods-vol}
\input{chapters/12-deep-learning-vol}
\input{chapters/13-hybrid-ensemble}

\part{Multivariate Volatility and Connectedness}
\input{chapters/14-multivariate-volatility}
\input{chapters/15-spillovers-connectedness}

\part{Evaluation and Practice}
\input{chapters/16-forecast-evaluation}
\input{chapters/17-applications-projects}

\bibliographystyle{plainnat}
\bibliography{references}

\end{document}
```

### Box Environments (8 types)

| Environment | Color | Purpose |
|---|---|---|
| `definition` | Blue | Formal definitions |
| `keyidea` | Orange | Core conceptual insights |
| `intuition` | Green | Plain-English explanations |
| `warning` | Red | Common pitfalls |
| `prereq` | Purple | Background knowledge (used aggressively mid-chapter) |
| `application` | Teal | Ties content to practical uses and project directions |
| `workedexample` | Teal | Worked numerical walk-through |
| `keyresult` | Gold | Headline result from a paper |

### Chapter Label Convention

| Chapter | Label |
|---|---|
| Ch 1 | `\label{ch:returns}` |
| Ch 2 | `\label{ch:rv}` |
| Ch 3 | `\label{ch:noise}` |
| Ch 4 | `\label{ch:jumps}` |
| Ch 5 | `\label{ch:garch}` |
| Ch 6 | `\label{ch:har}` |
| Ch 7 | `\label{ch:rough}` |
| Ch 8 | `\label{ch:volsurface}` |
| Ch 9 | `\label{ch:vrp}` |
| Ch 10 | `\label{ch:features}` |
| Ch 11 | `\label{ch:trees-vol}` |
| Ch 12 | `\label{ch:dl-vol}` |
| Ch 13 | `\label{ch:hybrid}` |
| Ch 14 | `\label{ch:multivariate}` |
| Ch 15 | `\label{ch:spillovers}` |
| Ch 16 | `\label{ch:evaluation}` |
| Ch 17 | `\label{ch:applications}` |

---

## 4. Writing Conventions

1. **Intuition-first sequence**: plain English, then visual/diagram, then equation, then term-by-term explanation, then worked example. Never equation-first.
2. **One idea per section.** If a section introduces two concepts, split it.
3. **Term-by-term after every equation.** Bulleted list, no exceptions.
4. **Diagrams before the math they illustrate.** The reader has a mental picture before symbols arrive.
5. **No em dashes.** Use commas, semicolons, colons, or parentheses instead.
6. **Concise.** If sayable in one sentence, use one sentence.
7. **Concrete numbers.** Every worked example uses realistic financial data (actual index levels, actual volatility magnitudes, actual bid-ask spreads).
8. **"Where we are" connectors.** A single sentence at the start of each section connecting back to the chapter thread, so the reader never feels lost.
9. **Cross-reference, don't repeat.** Use `\ref{}` to point back to earlier chapters.
10. **Every claim sourced.** Paper, year, specific result. Mark uncertain claims with `[VERIFY]`.
11. **Tone:** direct, confident, slightly informal. Address reader as "you."
12. **No padding prose.** Every sentence earns its place.

### Chapter Template

Each chapter follows this structure:

1. **Application box** (always first): what practical use cases and project directions this chapter serves
2. **Introduction**: 2-3 sentences, what and why
3. **Numbered sections**: one concept per section, building logically
4. **Within sections** (as appropriate):
   - Prereq boxes for background (used aggressively; reader has strong math, no vol knowledge)
   - Intuition box, then diagram, then definition box for formal concepts
   - Term-by-term explanation after every equation
   - Worked examples with actual numbers
   - Key Result boxes for paper findings (with actual reported statistics)
   - Warning boxes for common pitfalls
5. **Summary**: 8-15 bullet points
6. **Key Results recap table**: paper, result, relevance

---

## 5. Execution Strategy

### Per-Chapter Agent Workflow

All agents use Opus 4.6.

**Step 1: Research and write.** A chapter-writing agent fetches papers (WebSearch/WebFetch), extracts specific statistics and results, then writes the full LaTeX chapter following the intuition-first sequence and chapter template. If web access is unavailable, use the URLs and annotations in VOL.md bibliography as the primary reference, and mark any statistics that could not be verified with `[VERIFY]`.

**Step 2: Fluff review.** A separate agent reads the chapter and strips:
- Throat-clearing phrases ("It is worth noting that...", "Importantly,...", "As we shall see...")
- Redundant restatements
- Filler sentences that do not teach anything
- Overly verbose explanations that could be tighter
- Any em dashes (replace with commas, semicolons, colons, or parentheses)

Returns a cleaned version.

**Step 3: Clarity review (iterative).** A separate agent reads the cleaned chapter assuming **zero prior knowledge**. It works through the material as a first-time reader trying to understand from first principles. It reports:
- Concepts used before they are defined
- Logical jumps where a step is missing ("how did we get from A to C?")
- Equations where the preceding intuition or diagram does not actually prepare you for the math
- Diagrams referenced but not present, or places where a diagram is clearly needed but missing
- Anywhere the agent cannot follow the logic without outside knowledge not provided in this chapter or earlier chapters

If gaps are found, they are fixed and the clarity agent runs again. **This loop repeats until the clarity agent reports zero gaps.** Capped at 5 iterations; if not converged, surface remaining issues to the user.

### Chapter Dependencies and Parallel Waves

```
Wave 1 (no deps):        Ch 1, 5, 8, 16
Wave 2 (needs Wave 1):   Ch 2, 6
Wave 3 (needs Wave 2):   Ch 3, 4, 7, 9
Wave 4 (needs Wave 3):   Ch 10, 11
Wave 5 (needs Wave 4):   Ch 12, 13, 14, 15
Wave 6 (needs all):      Ch 17
```

Rationale:
- Ch 1 (returns/variance) standalone: first principles, no deps
- Ch 5 (GARCH) standalone: uses returns/variance concepts but does not need RV
- Ch 8 (options/vol surface) standalone: builds from options basics
- Ch 16 (evaluation) standalone: self-contained methodology
- Ch 2 (RV) needs Ch 1 (returns/variance)
- Ch 6 (HAR) needs Ch 2 (RV) and Ch 5 (GARCH for comparison)
- Ch 3 (noise) needs Ch 2 (RV: the estimator being corrected)
- Ch 4 (jumps) needs Ch 2 (RV); soft cross-reference to Ch 3 for Lee-Mykland 2012 noise-robust extension (not a hard dependency; the core jump content only needs RV)
- Ch 7 (rough vol) needs Ch 2 (RV) and Ch 6 (HAR as baseline)
- Ch 9 (VRP) needs Ch 2 (RV definition) and Ch 8 (IV, VIX definitions)
- Ch 10 (features) needs Ch 4 (jump features, signed jumps), Ch 6 (HAR features), Ch 7 (Hurst exponent), Ch 9 (VRP features)
- Ch 11 (trees) needs Ch 6 (HAR baseline) and Ch 10 (features); Ch 16 (evaluation concepts) is available from Wave 1
- Ch 12 (deep learning) needs Ch 11 (tree results for comparison)
- Ch 13 (hybrid) needs Ch 11 and Ch 12
- Ch 14 (multivariate) needs Ch 3 (noise-robust estimation) and Ch 6 (HAR framework, extended to multivariate in this chapter)
- Ch 15 (spillovers) needs Ch 14
- Ch 17 (applications) needs all

### Estimated Scale

- ~300-400 pages (more than ml-learning-guide due to more diagrams and more breathing room per concept)
- 40-60 TikZ/pgfplots diagrams
- 17 chapters, each 15-25 pages

---

## 6. Paper Reference Methodology

Every factual claim about a paper's findings must be verified by fetching the actual paper or a reliable summary (abstract, introduction, key tables). No fabricated statistics.

**Process per chapter:**
1. Before writing: fetch PDFs or abstracts for all referenced papers
2. While writing: cite specific results with table/figure numbers where possible
3. Key Result boxes: each must include the paper's actual reported statistic
4. Verification happens during the clarity review loop

**Primary sources:**
- VOL.md bibliography (~45 annotated references with URLs)
- Academic papers: SSRN, NBER, journal websites, arXiv
- AFML (Lopez de Prado 2018): reference by chapter number

---

## 7. Success Criteria

The document succeeds if, after reading it, you can:

1. **Explain what realized volatility is** and why 5-minute RV is the default, without referencing any formula
2. **Draw the volatility signature plot** and explain what it shows about microstructure noise
3. **Write down the HAR equation from memory** and explain what each component captures
4. **Explain rough volatility to a non-quant** using the Hurst exponent and sample path diagrams
5. **Read an implied volatility surface** and identify smile, skew, and term structure
6. **Describe the variance risk premium** and why it exists
7. **Choose the right ML method** for a given vol problem (intraday LOB: LightGBM; daily with rich features: tree ensemble; multivariate: graph methods)
8. **Explain why QLIKE is preferred over MSE** for vol forecast evaluation
9. **Evaluate the 5 project directions** and choose one with an informed rationale
10. **Defend any methodological choice** in a desk conversation (why purged CV, why QLIKE, why HAR baseline, why not deep learning for daily RV)
