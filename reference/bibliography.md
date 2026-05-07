# ML for Realized Volatility Forecasting -- Structured Bibliography

This bibliography contains ~80 entries relevant to the GS internship project on ML-based realized volatility forecasting. Each entry uses a machine-parseable format with slug IDs, controlled topic tags, and quality ratings (essential / recommended / optional). Entries are grouped by topic area (A-K) following the annotated bibliography in `notes/deep-research-vol-papers.md`. PDF paths are relative to the repository root.

---

## Table of Contents

- [A. Realized Volatility -- Estimators and Theory](#a-realized-volatility----estimators-and-theory)
- [B. HAR Family and Econometric Baselines](#b-har-family-and-econometric-baselines)
- [C. Rough Volatility](#c-rough-volatility)
- [D. ML for Volatility -- Empirical Studies](#d-ml-for-volatility----empirical-studies)
- [E. Limit-Order-Book Deep Learning](#e-limit-order-book-deep-learning)
- [F. Variance Risk Premium and Options](#f-variance-risk-premium-and-options)
- [G. Forecast Evaluation and Validation](#g-forecast-evaluation-and-validation)
- [H. Rashomon Sets and Optimal Sparse Decision Trees](#h-rashomon-sets-and-optimal-sparse-decision-trees)
- [I. Modern Deep Time-Series Forecasting](#i-modern-deep-time-series-forecasting)
- [J. Code Repositories and Data Sources](#j-code-repositories-and-data-sources)
- [K. Practitioner and Industry Resources](#k-practitioner-and-industry-resources)
- [Topic Tag Vocabulary](#topic-tag-vocabulary)

---

## A. Realized Volatility -- Estimators and Theory

### andersen-bollerslev-etal-2003
- **Title**: Modeling and Forecasting Realized Volatility
- **Authors**: Andersen, Bollerslev, Diebold, Labys
- **Year**: 2003
- **Venue**: Econometrica 71:579-625
- **Quality**: essential
- **Topics**: rv-estimators, foundational
- **PDF**: none
- **Key finding**: Canonical paper introducing daily RV-based forecasting from high-frequency returns. Established that realized variance converges to integrated variance and is approximately log-normal.
- **Relevance**: The paper that launched the modern RV forecasting literature; every baseline model builds on this.

### barndorff-nielsen-shephard-2002
- **Title**: Econometric Analysis of Realized Volatility and Its Use in Estimating Stochastic Volatility Models
- **Authors**: Barndorff-Nielsen, Shephard
- **Year**: 2002
- **Venue**: JRSS-B 64:253-280
- **Quality**: essential
- **Topics**: rv-estimators, jump-detection, foundational
- **PDF**: none
- **Key finding**: Theoretical foundation establishing CLT for realized volatility and introducing bipower variation (BV) for jump-robust integrated variance estimation.
- **Relevance**: BV and the jump decomposition QV = IV + sum(J^2) are used in HAR-J/CJ and every jump-aware model.

### barndorff-nielsen-etal-2008
- **Title**: Designing Realized Kernels to Measure the Ex Post Variation of Equity Prices in the Presence of Noise
- **Authors**: Barndorff-Nielsen, Hansen, Lunde, Shephard
- **Year**: 2008
- **Venue**: Econometrica 76:1481-1536 (SSRN 620203)
- **Quality**: essential
- **Topics**: rv-estimators, microstructure-noise, foundational
- **PDF**: none
- **Key finding**: Introduced realized kernels using flat-top kernel weights of autocovariances to neutralize i.i.d. and dependent microstructure noise, achieving optimal convergence rates.
- **Relevance**: Gold-standard noise-robust RV estimator; relevant if working with tick-level data.

### zhang-mykland-aitsahalia-2005
- **Title**: A Tale of Two Time Scales: Determining Integrated Volatility With Noisy High-Frequency Data
- **Authors**: Zhang, Mykland, Ait-Sahalia
- **Year**: 2005
- **Venue**: JASA 100:1394-1411
- **Quality**: recommended
- **Topics**: rv-estimators, microstructure-noise
- **PDF**: none
- **Key finding**: Two-scale realized volatility (TSRV) combines subsampled RV at fast and slow frequencies to remove noise bias while preserving efficiency.
- **Relevance**: Alternative to realized kernels for noise correction; simpler to implement.

### hansen-lunde-2006
- **Title**: Realized Variance and Market Microstructure Noise
- **Authors**: Hansen, Lunde
- **Year**: 2006
- **Venue**: JBES 24:127-161
- **Quality**: essential
- **Topics**: rv-estimators, microstructure-noise
- **PDF**: none
- **Key finding**: Formalized the bias-variance trade-off in RV estimation under microstructure noise. Introduced the volatility signature plot (RV vs. sampling frequency) as the key diagnostic.
- **Relevance**: The signature plot is step one of any HF data analysis; understanding this trade-off is prerequisite for choosing an estimator.

### liu-patton-sheppard-2015
- **Title**: Does Anything Beat 5-Minute RV? A Comparison of Realized Measures Across Multiple Asset Classes
- **Authors**: Liu, Patton, Sheppard
- **Year**: 2015
- **Venue**: J. Econometrics 187:293-311
- **Quality**: essential
- **Topics**: rv-estimators, evaluation, microstructure-noise
- **PDF**: none
- **Key finding**: Compared ~400 estimators across 31 assets in 5 asset classes. Concluded that 5-minute RV is very hard to beat; MCS contained ~40 estimators on average (~11% of universe).
- **Relevance**: Justifies using simple 5-min RV as the base realized measure rather than complex noise-robust alternatives.

### aitsahalia-jacod-2014
- **Title**: High-Frequency Financial Econometrics
- **Authors**: Ait-Sahalia, Jacod
- **Year**: 2014
- **Venue**: Princeton University Press (textbook)
- **Quality**: essential
- **Topics**: rv-estimators, microstructure-noise, jump-detection, foundational
- **PDF**: none
- **Key finding**: Definitive textbook covering the full theory of high-frequency financial econometrics: realized volatility, jump detection, microstructure noise, and semimartingale estimation.
- **Relevance**: The reference for anyone going deep on HF estimator theory and jump tests.

### lee-mykland-2008
- **Title**: Jumps in Financial Markets: A New Nonparametric Test and Jump Dynamics
- **Authors**: Lee, Mykland
- **Year**: 2008
- **Venue**: RFS 21:2535-2563
- **Quality**: recommended
- **Topics**: jump-detection, rv-estimators
- **PDF**: none
- **Key finding**: Workhorse intraday jump test based on comparing individual returns against local volatility estimates. Identifies exact jump times within the trading day.
- **Relevance**: Primary tool for constructing jump indicator features in HAR-J/CJ models.

### jacod-etal-2009
- **Title**: Microstructure Noise in the Continuous Case: The Pre-Averaging Approach
- **Authors**: Jacod, Li, Mykland, Podolskij, Vetter
- **Year**: 2009
- **Venue**: Stochastic Processes and Their Applications 119:2249-2276
- **Quality**: optional
- **Topics**: rv-estimators, microstructure-noise
- **PDF**: none
- **Key finding**: Pre-averaging approach to estimating integrated volatility under microstructure noise, extending to covariance estimation.
- **Relevance**: Relevant only if working heavily with HF data at sub-second frequencies.

---

## B. HAR Family and Econometric Baselines

### corsi-2009
- **Title**: A Simple Approximate Long-Memory Model of Realized Volatility
- **Authors**: Corsi
- **Year**: 2009
- **Venue**: J. Financial Econometrics 7:174-196
- **Quality**: essential
- **Topics**: har, long-memory, foundational
- **PDF**: reference/project-papers/corsi-2009-har-realized-volatility.pdf
- **Key finding**: The HAR model -- a three-component OLS regression of next-day RV on daily, weekly, and monthly RV averages -- captures the long-memory property of volatility with a simple, interpretable specification.
- **Relevance**: The benchmark every ML model must beat; 2,100+ citations as of 2021.

### andersen-bollerslev-diebold-2007
- **Title**: Roughing It Up: Including Jump Components in the Measurement, Modeling, and Forecasting of Return Volatility
- **Authors**: Andersen, Bollerslev, Diebold
- **Year**: 2007
- **Venue**: RES 89:701-720
- **Quality**: essential
- **Topics**: har, har-extensions, jump-detection
- **PDF**: none
- **Key finding**: HAR-J and HAR-CJ models separate continuous and jump components of realized volatility, showing that jumps have different predictive content from continuous variation.
- **Relevance**: The standard jump-augmented HAR baseline; jump features are among the first extensions to test.

### bollerslev-patton-quaedvlieg-2016
- **Title**: Exploiting the Errors: A Simple Approach for Improved Volatility Forecasting
- **Authors**: Bollerslev, Patton, Quaedvlieg
- **Year**: 2016
- **Venue**: J. Econometrics 192:1-18
- **Quality**: essential
- **Topics**: har, harq, har-extensions, rv-estimators
- **PDF**: reference/project-papers/bollerslev-patton-quaedvlieg-2016-harq.pdf
- **Key finding**: HARQ exploits time-varying measurement error in realized volatility by interacting HAR regressors with realized quarticity (RQ), delivering ~8% MSE / ~6% QLIKE improvement over HAR on S&P 500.
- **Relevance**: The most reliable single-feature HAR improvement; a must-have baseline and feature source.

### patton-sheppard-2015
- **Title**: Good Volatility, Bad Volatility: Signed Jumps and the Persistence of Volatility
- **Authors**: Patton, Sheppard
- **Year**: 2015
- **Venue**: RES 97:683-697
- **Quality**: essential
- **Topics**: har, har-extensions, jump-detection, leverage-effect
- **PDF**: reference/project-papers/patton-sheppard-2015-good-bad-volatility-shar.pdf
- **Key finding**: Signed semi-variances (SHAR) decompose RV into positive and negative components, capturing the leverage effect and improving forecasts by 2-4% QLIKE.
- **Relevance**: Signed decomposition features are cheap to compute and reliably improve HAR; essential baseline.

### hansen-huang-shek-2012
- **Title**: Realized GARCH: A Joint Model for Returns and Realized Measures of Volatility
- **Authors**: Hansen, Huang, Shek
- **Year**: 2012
- **Venue**: J. Applied Econometrics 27:877-906
- **Quality**: recommended
- **Topics**: realized-garch, garch, har-extensions
- **PDF**: none
- **Key finding**: Realized GARCH jointly models returns and realized measures in a GARCH framework with a measurement equation, allowing feedback between returns and RV.
- **Relevance**: Important parametric alternative to HAR; available in the `arch` Python package.

### shephard-sheppard-2010
- **Title**: Realising the Future: Forecasting with High-Frequency-Based Volatility (HEAVY) Models
- **Authors**: Shephard, Sheppard
- **Year**: 2010
- **Venue**: J. Applied Econometrics 25:197-231
- **Quality**: recommended
- **Topics**: har-extensions, realized-garch
- **PDF**: none
- **Key finding**: HEAVY models use realized measures to drive the conditional variance dynamics, capturing the faster response to volatility shocks that GARCH misses.
- **Relevance**: Bridges the gap between GARCH and HAR families; worth testing as a baseline.

### clements-preve-2021
- **Title**: Forecasting with the HAR Model
- **Authors**: Clements, Preve
- **Year**: 2021
- **Venue**: J. Banking & Finance 133:106285
- **Quality**: recommended
- **Topics**: har, har-extensions, evaluation
- **PDF**: none
- **Key finding**: Modern fitting guide showing that HAR implementation details (window estimation, log vs. level, intercept treatment) materially affect out-of-sample performance.
- **Relevance**: Critical for ensuring fair HAR baselines; implementation choices must be documented.

### wilms-etal-2024
- **Title**: HARd to Beat: The Overlooked Impact of Rolling Windows in the Era of Machine Learning
- **Authors**: Wilms, Rombouts, Croux, Boudt
- **Year**: 2024
- **Venue**: arXiv 2406.08041
- **Quality**: recommended
- **Topics**: har, har-extensions, ml-vol, evaluation
- **PDF**: reference/project-papers/hard-to-beat-2024-ml-vs-linear-rv.pdf
- **Key finding**: Fitting choices (rolling window length, log transform, lag structure) matter more than the choice between linear and ML models. A well-tuned HAR beats naively-applied ML.
- **Relevance**: Crucial methodological warning: must control for fitting choices before claiming ML superiority.

### bollerslev-patton-quaedvlieg-2018
- **Title**: Modeling and Forecasting (Un)Reliable Realized Covariances for More Reliable Financial Decisions
- **Authors**: Bollerslev, Patton, Quaedvlieg
- **Year**: 2018
- **Venue**: J. Econometrics 207:71-91
- **Quality**: essential
- **Topics**: harq, har-extensions, rv-estimators
- **PDF**: reference/project-papers/bollerslev-patton-quaedvlieg-2018-unreliable-realized-covariances.pdf
- **Key finding**: Extends HARQ to multivariate setting, modeling time-varying reliability of realized covariance matrices and improving portfolio allocation decisions.
- **Relevance**: Extends the measurement-error correction idea to covariances; relevant for multi-asset forecasting.

---

## C. Rough Volatility

### gatheral-jaisson-rosenbaum-2018
- **Title**: Volatility Is Rough
- **Authors**: Gatheral, Jaisson, Rosenbaum
- **Year**: 2018
- **Venue**: Quantitative Finance 18:933-949 (arXiv 1410.3394)
- **Quality**: essential
- **Topics**: rough-vol, long-memory, foundational
- **PDF**: reference/project-papers/gatheral-jaisson-rosenbaum-2018-volatility-is-rough.pdf
- **Key finding**: Log-volatility of equity indices behaves as fractional Brownian motion with Hurst parameter H ~ 0.1, much rougher than standard diffusion models predict.
- **Relevance**: Motivates roughness-aware feature engineering; the H estimate is a testable hypothesis on our data.

### bayer-friz-gatheral-2016
- **Title**: Pricing Under Rough Volatility
- **Authors**: Bayer, Friz, Gatheral
- **Year**: 2016
- **Venue**: Quantitative Finance 16:887-904
- **Quality**: recommended
- **Topics**: rough-vol, options-implied
- **PDF**: none
- **Key finding**: The rough Bergomi (rBergomi) model prices SPX options more accurately than standard stochastic vol models by using fractional Brownian motion for the variance process.
- **Relevance**: If incorporating implied vol features, understanding the pricing model family helps interpret IV surface shape.

### cont-das-2024
- **Title**: Rough Volatility: Fact or Artefact?
- **Authors**: Cont, Das
- **Year**: 2024
- **Venue**: Sankhya B 86:191-223 (arXiv 2203.13820)
- **Quality**: essential
- **Topics**: rough-vol, microstructure-noise, rv-estimators
- **PDF**: reference/project-papers/cont-das-2024-rough-volatility-fact-or-artefact.pdf
- **Key finding**: Critical re-examination arguing that the apparent roughness (H ~ 0.1) may be an artefact of microstructure noise in the estimation procedure rather than a genuine feature of the volatility process.
- **Relevance**: Directly challenges rough-vol features; must test whether roughness measures add forecasting value or just capture noise.

### bayer-etal-2023-roughvol-book
- **Title**: Rough Volatility
- **Authors**: Bayer, Friz, Gassiat, Gatheral, Horvath, Jacquier (eds.)
- **Year**: 2023
- **Venue**: SIAM (book)
- **Quality**: recommended
- **Topics**: rough-vol, foundational
- **PDF**: none
- **Key finding**: Comprehensive edited volume covering theory, estimation, pricing, and calibration of rough volatility models.
- **Relevance**: Reference for deep dives into rough vol; not needed for initial exploration.

### boj-rough-vol-survey-2024
- **Title**: Survey of Rough Volatility
- **Authors**: Bank of Japan IMES
- **Year**: 2024
- **Venue**: Bank of Japan IMES Discussion Paper
- **Quality**: recommended
- **Topics**: rough-vol, foundational
- **PDF**: none
- **Key finding**: Accessible survey of the rough volatility paradigm covering estimation, pricing implications, and open questions.
- **Relevance**: Good entry point for understanding the rough vol debate before diving into primary sources.

### rosenbaum-zhang-2022
- **Title**: On the Universality of the Volatility Formation Process: When Machine Learning and Rough Volatility Agree
- **Authors**: Rosenbaum, Zhang
- **Year**: 2022
- **Venue**: arXiv 2206.14114
- **Quality**: recommended
- **Topics**: rough-vol, ml-vol, deep-learning
- **PDF**: reference/project-papers/rosenbaum-zhang-2022-universality-volatility-formation.pdf
- **Key finding**: Demonstrates that machine learning models and rough volatility theory converge on similar volatility dynamics, suggesting universal features in the volatility formation process.
- **Relevance**: Bridges the rough-vol and ML-vol literatures; supports using roughness-related features in ML pipelines.

---

## D. ML for Volatility -- Empirical Studies

### christensen-siggaard-veliyev-2023
- **Title**: A Machine Learning Approach to Volatility Forecasting
- **Authors**: Christensen, Siggaard, Veliyev
- **Year**: 2023
- **Venue**: J. Financial Econometrics 21:1680-1727 (arXiv 2601.13014)
- **Quality**: essential
- **Topics**: ml-vol, gradient-boosting, neural-nets, har, evaluation, qlike
- **PDF**: reference/project-papers/christensen-siggaard-veliyev-2023-ml-volatility-forecasting.pdf
- **Key finding**: Cleanest demonstration that ML (random forests, gradient boosting, neural nets) beats HAR on DJIA constituents; gains rise with forecast horizon because ML better approximates long memory.
- **Relevance**: The primary reference for "ML beats HAR" claims; defines the empirical benchmark we target.

### branco-rubesam-zevallos-2024
- **Title**: Forecasting Realized Volatility: Does Anything Beat Linear Models?
- **Authors**: Branco, Rubesam, Zevallos
- **Year**: 2024
- **Venue**: J. Empirical Finance 78:101524
- **Quality**: essential
- **Topics**: ml-vol, har, evaluation, qlike, mcs
- **PDF**: none
- **Key finding**: Across 10 global equity indices, no nonlinear ML model statistically outperforms a properly fitted HAR-X in formal MCS tests, challenging the "ML wins" narrative.
- **Relevance**: The essential counterpoint; forces honest framing of ML contribution and careful baseline tuning.

### rahimikia-poon-2020
- **Title**: Machine Learning for Realised Volatility Forecasting
- **Authors**: Rahimikia, Poon
- **Year**: 2020
- **Venue**: SSRN 3707796
- **Quality**: essential
- **Topics**: ml-vol, lob, gradient-boosting, feature-engineering
- **PDF**: reference/project-papers/rahimikia-poon-2020-ml-rv-forecasting.pdf
- **Key finding**: ML with LOB features (mid prices, bid/ask means) beats HAR in 90% of out-of-sample days for 23 NASDAQ tickers. LOB features are the dominant information source.
- **Relevance**: Strongest evidence that richer information sets (not just better models) drive ML gains over HAR.

### rahimikia-zohren-poon-2024
- **Title**: Realised Volatility Forecasting: Machine Learning via Financial Word Embedding
- **Authors**: Rahimikia, Zohren, Poon
- **Year**: 2024
- **Venue**: arXiv 2108.00480
- **Quality**: recommended
- **Topics**: ml-vol, sentiment, feature-engineering
- **PDF**: none
- **Key finding**: FinText embeddings from financial news improve RV forecasts, with the greatest gains on jump days when text captures event-driven volatility.
- **Relevance**: Demonstrates value of text features as complement to quantitative inputs, especially for tail events.

### reisenhofer-bayer-hautsch-2022
- **Title**: HARNet: A Convolutional Neural Network for Realized Volatility Forecasting
- **Authors**: Reisenhofer, Bayer, Hautsch
- **Year**: 2022
- **Venue**: arXiv 2205.07719
- **Quality**: essential
- **Topics**: ml-vol, cnn-tcn, har, deep-learning
- **PDF**: none
- **Key finding**: HARNet embeds the HAR structure inside a CNN, achieving ~11.74% average reduction in median test MAE across SPX, FTSE 100, and DJI vs. OLS-HAR. Code available at github.com/mdsunivie/HARNet.
- **Relevance**: Best example of HAR-aware neural architecture; the code repo is directly usable.

### moreno-pino-zohren-2022
- **Title**: DeepVol: Volatility Forecasting from High-Frequency Data with Dilated Causal Convolutions
- **Authors**: Moreno-Pino, Zohren
- **Year**: 2022
- **Venue**: Quantitative Finance (arXiv 2210.04797)
- **Quality**: recommended
- **Topics**: ml-vol, cnn-tcn, deep-learning
- **PDF**: reference/project-papers/moreno-pino-zohren-2022-deepvol.pdf
- **Key finding**: DeepVol uses dilated causal convolutions on raw intraday returns, bypassing handcrafted realized measures entirely to forecast daily RV.
- **Relevance**: Demonstrates the "raw data in, forecast out" approach; relevant if exploring end-to-end deep learning.

### souto-moradi-2024
- **Title**: NBEATSx for Realized Volatility Forecasting
- **Authors**: Souto, Moradi
- **Year**: 2024
- **Venue**: Expert Systems with Applications 122802
- **Quality**: recommended
- **Topics**: ml-vol, deep-learning, neural-nets
- **PDF**: none
- **Key finding**: NBEATSx adapted for realized volatility forecasting on six stock indices achieves 13% and 8% gains at medium and long horizons respectively over baselines.
- **Relevance**: Shows time-series foundation architectures (N-BEATS family) transfer well to vol forecasting.

### taneva-angelova-granchev-2025
- **Title**: Transformer Architectures for Realized Volatility Forecasting
- **Authors**: Taneva-Angelova, Granchev
- **Year**: 2025
- **Venue**: J. Risk Financial Management 18(12):685
- **Quality**: recommended
- **Topics**: ml-vol, transformers, deep-learning
- **PDF**: none
- **Key finding**: Comprehensive comparison of transformer architectures for volatility forecasting on US equity indices (2000-2025), showing mixed results vs. simpler baselines.
- **Relevance**: Latest transformer benchmark for vol; useful for understanding where attention mechanisms help.

### zhang-pu-cucuringu-dong-2025
- **Title**: Realized Volatility Forecasting with Graph Neural Networks
- **Authors**: Zhang, Pu, Cucuringu, Dong
- **Year**: 2025
- **Venue**: Int. J. Forecasting 41:377-397 (arXiv 2308.01419)
- **Quality**: essential
- **Topics**: ml-vol, gnn, cross-asset, spillovers, deep-learning
- **PDF**: none
- **Key finding**: GNN captures cross-asset volatility spillovers through learned graph structures, outperforming univariate and simple multivariate models on multi-asset RV forecasting.
- **Relevance**: Primary reference for the cross-asset spillover project direction; demonstrates graph-based approaches for RV.

### brini-toscano-2025
- **Title**: SpotV2Net: Multivariate Intraday Spot Volatility Forecasting via Vol-of-Vol-Informed Graph Attention Networks
- **Authors**: Brini, Toscano
- **Year**: 2025
- **Venue**: Int. J. Forecasting 41:1093-1111
- **Quality**: recommended
- **Topics**: ml-vol, gnn, cross-asset, spillovers, deep-learning
- **PDF**: reference/project-papers/spotv2net-2024-intraday-vol-gat.pdf
- **Key finding**: SpotV2Net uses vol-of-vol informed graph attention networks for multivariate intraday spot volatility forecasting, capturing dynamic cross-asset relationships.
- **Relevance**: Complementary to Zhang et al. GNN; focuses on intraday time scale and attention-based graph learning.

### optiver-kaggle-2021
- **Title**: Optiver Realized Volatility Prediction (Kaggle Competition)
- **Authors**: Optiver (competition); top solutions by community
- **Year**: 2021
- **Venue**: kaggle.com/competitions/optiver-realized-volatility-prediction
- **Quality**: recommended
- **Topics**: ml-vol, gradient-boosting, feature-engineering, lob, data-source
- **PDF**: none
- **Key finding**: Top-10 solutions (e.g., 7th place public RMSPE 0.20013) demonstrate that gradient boosting + careful microstructure feature engineering from LOB data is the winning playbook for short-horizon RV prediction.
- **Relevance**: Feature-engineering goldmine; top writeups document exactly which LOB features matter most.

### bucci-2020
- **Title**: Realized Volatility Forecasting with Neural Networks
- **Authors**: Bucci
- **Year**: 2020
- **Venue**: J. Financial Econometrics
- **Quality**: essential
- **Topics**: ml-vol, neural-nets, deep-learning, har
- **PDF**: reference/project-papers/bucci-2020-rv-forecasting-neural-networks.pdf
- **Key finding**: Systematic evaluation of neural network architectures for RV forecasting, showing that feed-forward and recurrent networks can improve on HAR but gains are sensitive to architecture choices.
- **Relevance**: Early comprehensive neural net benchmark for RV; provides architectural lessons for deep learning approaches.

### fed-2025
- **Title**: Linear and Nonlinear Econometric Models Against Machine Learning for Realized Volatility Forecasting
- **Authors**: Federal Reserve (FEDS Working Paper)
- **Year**: 2025
- **Venue**: FEDS Working Paper
- **Quality**: essential
- **Topics**: ml-vol, har, evaluation, qlike
- **PDF**: reference/project-papers/fed-2025-linear-nonlinear-rv-forecasting.pdf
- **Key finding**: Fed staff comparison of econometric and ML models for RV forecasting, providing institutional perspective on the relative merits of each approach.
- **Relevance**: Authoritative institutional benchmark; useful for framing results in policy-relevant terms.

### foundation-model-rv-2025
- **Title**: Foundation Time-Series AI Model for Realized Volatility Forecasting
- **Authors**: (various)
- **Year**: 2025
- **Venue**: arXiv 2505.11163
- **Quality**: essential
- **Topics**: ml-vol, transformers, deep-learning
- **PDF**: reference/project-papers/foundation-model-rv-forecasting-2025.pdf
- **Key finding**: Applies pre-trained time-series foundation models to RV forecasting, testing whether general-purpose temporal representations transfer to financial volatility.
- **Relevance**: Tests the frontier question of whether foundation models can replace domain-specific feature engineering.

### vision-transformer-rv-2025
- **Title**: Data-Efficient Realized Volatility Forecasting with Vision Transformers
- **Authors**: (various)
- **Year**: 2025
- **Venue**: arXiv 2511.03046
- **Quality**: recommended
- **Topics**: ml-vol, transformers, deep-learning
- **PDF**: reference/project-papers/vision-transformer-rv-2025.pdf
- **Key finding**: Encodes time-series data as images and applies vision transformers for data-efficient RV forecasting, showing competitive performance with less training data.
- **Relevance**: Novel input representation approach; potentially useful for limited-data regimes.

### time-series-foundation-var-2024
- **Title**: Time-Series Foundation Model for Value-at-Risk
- **Authors**: (various)
- **Year**: 2024
- **Venue**: arXiv 2410.11773
- **Quality**: recommended
- **Topics**: ml-vol, transformers, deep-learning
- **PDF**: reference/project-papers/time-series-foundation-model-var-2024.pdf
- **Key finding**: Foundation time-series models applied to VaR estimation, demonstrating cross-task transfer from general forecasting to risk measurement.
- **Relevance**: VaR is a downstream application of RV forecasts; shows how vol models feed into risk management.

### transfer-learning-rv-2025
- **Title**: Transfer Learning for Realized Volatility of New Issues and Spin-Offs
- **Authors**: (various)
- **Year**: 2025
- **Venue**: arXiv 2503.12648
- **Quality**: recommended
- **Topics**: ml-vol, deep-learning
- **PDF**: reference/project-papers/transfer-learning-rv-new-issues-2025.pdf
- **Key finding**: Transfer learning enables RV forecasting for newly listed securities with limited history by leveraging patterns learned from mature assets.
- **Relevance**: Addresses the cold-start problem in vol forecasting; relevant for IPOs and spin-offs.

### chen-robert-2022
- **Title**: Multivariate Realized Volatility Forecasting with Graph Neural Network
- **Authors**: Chen, Robert
- **Year**: 2022
- **Venue**: ACM ICAIF
- **Quality**: essential
- **Topics**: ml-vol, gnn, cross-asset, spillovers
- **PDF**: reference/project-papers/chen-robert-2022-gnn-multivariate-rv.pdf
- **Key finding**: Early application of GNNs to multivariate RV forecasting, demonstrating that graph-based representations of cross-asset relationships improve forecast accuracy.
- **Relevance**: Precursor to Zhang et al. (2025); establishes the GNN-for-RV approach.

---

## E. Limit-Order-Book Deep Learning

### zhang-zohren-roberts-2019
- **Title**: DeepLOB: Deep Convolutional Neural Networks for Limit Order Books
- **Authors**: Zhang, Zohren, Roberts
- **Year**: 2019
- **Venue**: IEEE Transactions on Signal Processing (arXiv 1808.03668)
- **Quality**: recommended
- **Topics**: lob, deep-learning, cnn-tcn
- **PDF**: none
- **Key finding**: CNN architecture for mid-price prediction from raw limit order book data, establishing the deep learning baseline for LOB-based forecasting.
- **Relevance**: Foundation architecture for LOB feature extraction; relevant if incorporating order book data.

### sirignano-cont-2019
- **Title**: Universal Features of Price Formation in Financial Markets: Perspectives from Deep Learning
- **Authors**: Sirignano, Cont
- **Year**: 2019
- **Venue**: Quantitative Finance
- **Quality**: recommended
- **Topics**: lob, deep-learning, foundational
- **PDF**: none
- **Key finding**: Deep learning reveals universal features of price formation across different stocks, suggesting that order flow dynamics share common statistical structure.
- **Relevance**: Supports transferability of LOB-based features across assets; relevant for multi-asset vol models.

### briola-bartolucci-aste-2025
- **Title**: LiT: Limit-Order-Book Transformer
- **Authors**: Briola, Bartolucci, Aste
- **Year**: 2025
- **Venue**: PMC
- **Quality**: recommended
- **Topics**: lob, transformers, deep-learning
- **PDF**: none
- **Key finding**: Transformer architecture specifically designed for limit order book data, leveraging attention mechanisms to capture inter-level dependencies.
- **Relevance**: Latest LOB architecture; shows where transformers add value over CNNs for order book data.

### prata-etal-2025
- **Title**: LOB-Based Deep Learning Models for Stock Price Trend Prediction: A Benchmark Study
- **Authors**: Prata, Pereira, Moreira, Mendes-Moreira
- **Year**: 2025
- **Venue**: Quantitative Finance
- **Quality**: recommended
- **Topics**: lob, deep-learning, evaluation
- **PDF**: none
- **Key finding**: Sober assessment showing that high classification accuracy on LOB data does not translate directly to tradable signals; the gap between statistical and economic performance is significant.
- **Relevance**: Important reality check for any LOB-based approach; statistical significance is not economic significance.

---

## F. Variance Risk Premium and Options

### bollerslev-tauchen-zhou-2009
- **Title**: Expected Stock Returns and Variance Risk Premia
- **Authors**: Bollerslev, Tauchen, Zhou
- **Year**: 2009
- **Venue**: RFS 22:4463-4492
- **Quality**: essential
- **Topics**: vrp, options-implied, foundational
- **PDF**: none
- **Key finding**: The variance risk premium (VRP = implied variance - expected realized variance) is a strong predictor of future stock returns, with predictive power concentrated at quarterly horizons.
- **Relevance**: VRP is both a feature for vol models and a direct trading signal; connects RV forecasting to return prediction.

### bekaert-hoerova-2014
- **Title**: The VIX, the Variance Premium and Stock Market Volatility
- **Authors**: Bekaert, Hoerova
- **Year**: 2014
- **Venue**: J. Econometrics
- **Quality**: recommended
- **Topics**: vrp, options-implied
- **PDF**: none
- **Key finding**: Decomposes VIX into conditional variance and variance premium components, showing each has distinct forecasting power for returns and volatility.
- **Relevance**: Refines VRP features; the decomposition may improve feature engineering for vol models.

### carr-wu-2009
- **Title**: Variance Risk Premiums
- **Authors**: Carr, Wu
- **Year**: 2009
- **Venue**: RFS
- **Quality**: recommended
- **Topics**: vrp, options-implied, cross-asset
- **PDF**: none
- **Key finding**: Documents VRP across major US stock indices and individual stocks, showing that VRP is consistently negative (investors pay for variance insurance).
- **Relevance**: Cross-sectional VRP evidence; supports using VRP features across multiple assets.

---

## G. Forecast Evaluation and Validation

### patton-2011
- **Title**: Volatility Forecast Comparison Using Imperfect Volatility Proxies
- **Authors**: Patton
- **Year**: 2011
- **Venue**: J. Econometrics 160:246-256
- **Quality**: essential
- **Topics**: evaluation, qlike, foundational
- **PDF**: none
- **Key finding**: QLIKE and MSE loss functions are robust to noise in the volatility proxy (using RV as proxy for true integrated variance) -- other loss functions are not, meaning model rankings are preserved even though RV is measured with error.
- **Relevance**: Justifies QLIKE as the primary evaluation metric; any other loss function requires additional robustness arguments.

### hansen-lunde-nason-2011
- **Title**: The Model Confidence Set
- **Authors**: Hansen, Lunde, Nason
- **Year**: 2011
- **Venue**: Econometrica 79:453-497
- **Quality**: essential
- **Topics**: evaluation, mcs, foundational
- **PDF**: none
- **Key finding**: The Model Confidence Set (MCS) procedure identifies the set of models that are statistically indistinguishable from the best model at a given confidence level, controlling for multiple testing.
- **Relevance**: The standard method for reporting model comparison results; all papers in this literature use MCS.

### diebold-mariano-1995
- **Title**: Comparing Predictive Accuracy
- **Authors**: Diebold, Mariano
- **Year**: 1995
- **Venue**: JBES
- **Quality**: recommended
- **Topics**: evaluation, foundational
- **PDF**: none
- **Key finding**: The Diebold-Mariano test for equal predictive accuracy between two forecasts, applicable under general loss functions and non-nested models.
- **Relevance**: Pairwise complement to MCS; used for head-to-head model comparisons.

### lopez-de-prado-2018
- **Title**: Advances in Financial Machine Learning
- **Authors**: Lopez de Prado
- **Year**: 2018
- **Venue**: Wiley (book)
- **Quality**: essential
- **Topics**: validation, purged-cv, feature-engineering, foundational
- **PDF**: none
- **Key finding**: Introduces purged k-fold cross-validation (eliminating information leakage in time-series CV), fractional differentiation (preserving memory while achieving stationarity), and triple-barrier labeling for financial ML.
- **Relevance**: Ch. 7 (purged CV) is mandatory for validation methodology; Ch. 5 (fractional differencing) is relevant for feature stationarity.

---

## H. Rashomon Sets and Optimal Sparse Decision Trees

### breiman-2001
- **Title**: Statistical Modeling: The Two Cultures
- **Authors**: Breiman
- **Year**: 2001
- **Venue**: Statistical Science 16:199-231
- **Quality**: essential
- **Topics**: rashomon, ensemble, foundational
- **PDF**: none
- **Key finding**: Introduced the Rashomon effect: many very different models can achieve near-identical predictive accuracy, raising fundamental questions about model selection and interpretation.
- **Relevance**: Theoretical foundation for the Rashomon-set project direction; motivates exploring model multiplicity.

### lin-etal-2020-gosdt
- **Title**: Generalized and Scalable Optimal Sparse Decision Trees
- **Authors**: Lin, Zhong, Hu, Rudin, Seltzer
- **Year**: 2020
- **Venue**: ICML (arXiv 2006.08690)
- **Quality**: essential
- **Topics**: optimal-trees, rashomon
- **PDF**: none
- **Key finding**: Extends OSDT to continuous features via online threshold guessing (formalized in McTavish et al. AAAI 2022 "GOSDT-Guesses"), non-linear objectives (F1, weighted accuracy, AUC), and black-box guidance. Depth limit added in 2022. Handles tens of thousands of rows and 30-100 binarized features within minutes. Code: `pip install gosdt` (github.com/ubc-systopia/gosdt-guesses, 57 stars).
- **Relevance**: Foundation algorithm for the interpretable-trees project direction; PyGOSDT package is directly usable. GOSDT-Guesses effectively distills a gradient-boosted ensemble into an optimal sparse single tree.

### aglin-etal-2020-dl85
- **Title**: DL8.5: Optimal Decision Trees with Caching Branch-and-Bound
- **Authors**: Aglin, Nijssen, Schaus
- **Year**: 2020
- **Venue**: AAAI 2020 (PyDL8.5: IJCAI 2020)
- **Quality**: recommended
- **Topics**: optimal-trees, rashomon
- **PDF**: none
- **Key finding**: Caching branch-and-bound that stores partial-search results for itemset prefixes, building on DL8 (Nijssen & Fromont, KDD 2007). Outperforms MIP formulations by orders of magnitude. PyDL8.5 at github.com/aia-uclouvain/pydl8.5.
- **Relevance**: Alternative optimal tree solver to GOSDT; useful for benchmarking solver performance. Sklearn-compatible.

### demirovic-etal-2022-murtree
- **Title**: MurTree: Optimal Decision Trees via Dynamic Programming and Search
- **Authors**: Demirovic, Lukina, Hebrard, Chan, Bailey, Leckie, Ramamohanarao, Stuckey
- **Year**: 2022
- **Venue**: JMLR
- **Quality**: recommended
- **Topics**: optimal-trees, rashomon
- **PDF**: none
- **Key finding**: Introduces a specialized depth-2 solver exploiting closed-form optimal depth-two structure, plus similarity and incremental bounds. Established that the greedy-vs-optimal accuracy gap can reach 10 percentage points on certain datasets. State-of-the-art exact solver at time of publication.
- **Relevance**: Key benchmark; the depth-2 technique is now standard in STreeD/ConTree/SORTeD. pymurtree package available (partial sklearn compat).

### van-der-linden-etal-2023-streed
- **Title**: STreeD: Optimal Decision Trees via Separable Objectives
- **Authors**: van der Linden, de Weerdt, Demirovic
- **Year**: 2023-2024
- **Venue**: NeurIPS 2023, ICML 2024, AAAI 2025
- **Quality**: essential
- **Topics**: optimal-trees, rashomon, regression-trees, fairness, survival-trees
- **PDF**: none
- **Key finding**: Unifying DP framework proving that any separable objective (independently optimizable for left/right subtrees) admits a DP solution. Subsumes: cost-sensitive classification, F1, group-fairness constraints, prescriptive policy trees, piecewise-constant and piecewise-linear regression (elastic-net leaves), and survival trees. Code: `pip install pystreed` (github.com/AlgTUDelft/pystreed).
- **Relevance**: Directly relevant: STreeD piecewise-linear regression is the recommended primary method for the vol forecasting regression task. Handles continuous features natively in latest extensions.

### xin-etal-2022-treefarms
- **Title**: Exploring the Whole Rashomon Set of Sparse Decision Trees
- **Authors**: Xin, Zhong, Chen, Takagi, Seltzer, Rudin
- **Year**: 2022
- **Venue**: NeurIPS Oral (arXiv 2209.08040)
- **Quality**: essential
- **Topics**: rashomon, optimal-trees
- **PDF**: none
- **Key finding**: First complete enumeration of the Rashomon set for any non-trivial hypothesis class. Extends GOSDT with a specialized trie ('Trees FAst RashoMon Sets') supporting efficient query and sampling. Finds orders of magnitude more distinct near-optimal trees than BART/MCMC samplers. Applications: variable importance over entire Rashomon set, derived-metric Rashomon sets (balanced accuracy, F1), bootstrap Rashomon sets. Code: `pip install treefarms` (github.com/ubc-systopia/treeFarms, 47 stars).
- **Relevance**: Core tool for the Rashomon project direction; produces the set of competing models for analysis.

### babbar-etal-2025-split
- **Title**: SPLIT: Scalable Enumeration of the Full Rashomon Set of Optimal Decision Trees
- **Authors**: Babbar, McTavish, Rudin, Seltzer
- **Year**: 2025
- **Venue**: ICML 2025 Oral (arXiv 2502.15988)
- **Quality**: essential
- **Topics**: rashomon, optimal-trees
- **PDF**: none
- **Key finding**: Hybrid lookahead+greedy: optimal near root, greedy near leaves. Provably at least as good as fully greedy (Theorem A.1). Saves O(k^((d-1)/2) * (d/2)!) over fully optimal (Corollary 6.3). There exist distributions where SPLIT achieves 1-epsilon while greedy achieves at most 1/2+epsilon (Theorem 6.5). LicketySPLIT: recursive depth-1 variant in polynomial time O(|R|*n*k^3*d^3). RESPLIT extends to Rashomon-set computation, ~74x faster than TreeFARMS on Bike, ~17x on Spambase. Over 100x faster than GOSDT. Code: github.com/VarunBabbar/SPLIT-ICML.
- **Relevance**: Fastest near-optimal solver; the tool for rapid iteration during research. RESPLIT is the scalable Rashomon-set alternative to TreeFARMS. Classification only currently.

### heile-etal-2025-licketyresplit
- **Title**: LicketyRESPLIT
- **Authors**: Heile, Babbar, McTavish, Rudin
- **Year**: 2025
- **Venue**: (preprint)
- **Quality**: recommended
- **Topics**: rashomon, optimal-trees
- **PDF**: none
- **Key finding**: Polynomial-time approximation to the Rashomon set, recursively finding near-optimal splits conditioned on easy-to-compute oracles. Orders-of-magnitude runtime and memory improvement over TreeFARMS and RESPLIT. Recovers nearly the full Rashomon set.
- **Relevance**: Performance optimization of SPLIT; use if SPLIT is too slow on target dataset.

### arslan-etal-2025-sorted
- **Title**: SORTeD: Anytime Enumeration of Rashomon Trees in Objective Order
- **Authors**: Arslan, van der Linden, Hoogendoorn, Rinaldi, Demirovic
- **Year**: 2025
- **Venue**: NeurIPS Spotlight
- **Quality**: recommended
- **Topics**: optimal-trees, rashomon
- **PDF**: none
- **Key finding**: Enumerates the Rashomon set in decreasing order of objective value -- best trees first. Anytime termination at any quality threshold. Up to two orders of magnitude speedup over TreeFARMS/RESPLIT. Supports any separable, totally ordered objective (works for regression and survival via STreeD).
- **Relevance**: Alternative solver if exact methods are intractable at scale.

### semenova-rudin-parr-2022
- **Title**: On the Existence of Simpler Machine Learning Models
- **Authors**: Semenova, Rudin, Parr
- **Year**: 2022
- **Venue**: FAccT 2022 (arXiv 1908.01755)
- **Quality**: essential
- **Topics**: rashomon, evaluation
- **PDF**: none
- **Key finding**: Introduces the Rashomon ratio -- ratio of volume of Rashomon set to hypothesis space volume. When several different ML methods produce near-equal accuracy on a dataset, the Rashomon ratio is large, guaranteeing simpler models exist within the Rashomon set.
- **Relevance**: Theoretical backbone for interpreting Rashomon-set results; guides threshold selection for "near-optimal."

### dong-rudin-2020
- **Title**: Exploring the Cloud of Variable Importance for the Set of All Good Models
- **Authors**: Dong, Rudin
- **Year**: 2020
- **Venue**: (arXiv 1901.03209)
- **Quality**: essential
- **Topics**: rashomon, feature-engineering
- **PDF**: none
- **Key finding**: Variable Importance Clouds map every variable to its Model Reliance importance for every good model in the Rashomon set. Used with TreeFARMS, VIC reveals when one variable is interchangeable with another versus uniquely important. Shapley-VIC extension (Ning et al., Patterns 2022) extends to SHAP values across the Rashomon set.
- **Relevance**: The key deliverable for the Rashomon project: showing which vol features are genuinely important vs. substitutable.

### rudin-etal-2024-position
- **Title**: Amazing Things Come from Having Many Good Models
- **Authors**: Rudin et al.
- **Year**: 2024
- **Venue**: ICML 2024 Spotlight (arXiv 2407.04846)
- **Quality**: recommended
- **Topics**: rashomon, foundational
- **PDF**: none
- **Key finding**: Position paper consolidating six benefits of computing the Rashomon set: (1) existence of simpler-yet-accurate models, (2) flexibility for fairness/monotonicity constraints, (3) uncertainty quantification, (4) reliable variable importance, (5) algorithm-choice diagnostics, (6) public-policy applications. Argues ML should reframe learning as a feasibility problem ('find all good models') rather than optimization.
- **Relevance**: Motivational framing for the Rashomon project direction; useful for presentation and writeup.

### mctavish-etal-2025
- **Title**: Predictive Equivalence in Trees
- **Authors**: McTavish, Boner, Donnelly, Seltzer, Rudin
- **Year**: 2025
- **Venue**: ICML (arXiv 2506.14143)
- **Quality**: recommended
- **Topics**: rashomon, optimal-trees, interpretability
- **PDF**: none
- **Key finding**: Defines predictive equivalence classes within decision tree Rashomon sets. Two trees can encode the same decision boundary while differing in evaluation order, affecting variable importance and missing-value handling. Proposes a boolean-logical canonicalization to identify truly distinct models.
- **Relevance**: Reduces redundancy in Rashomon set analysis; identifies truly distinct models.

### marx-calmon-ustun-2020
- **Title**: Predictive Multiplicity in Classification
- **Authors**: Marx, Calmon, Ustun
- **Year**: 2020
- **Venue**: ICML
- **Quality**: recommended
- **Topics**: rashomon
- **PDF**: none
- **Key finding**: Formalizes predictive multiplicity -- the degree to which competing models disagree on individual predictions. Proposes metrics (ambiguity, discrepancy) to measure it. Shows that standard model selection ignores multiplicity, which can be large even when test accuracy is near-identical.
- **Relevance**: Useful for understanding prediction stability across the Rashomon set; complements Variable Importance Clouds.

---

## I. Modern Deep Time-Series Forecasting

### oreshkin-etal-2020-nbeats
- **Title**: N-BEATS: Neural Basis Expansion Analysis for Interpretable Time Series Forecasting
- **Authors**: Oreshkin, Carpov, Chapados, Bengio
- **Year**: 2020
- **Venue**: ICLR
- **Quality**: recommended
- **Topics**: deep-learning, neural-nets
- **PDF**: none
- **Key finding**: N-BEATS uses backward and forward residual links with basis expansion for interpretable time-series forecasting, achieving state-of-the-art on M4 competition without domain-specific features.
- **Relevance**: Base architecture for NBEATSx-vol (Souto & Moradi 2024); available in Nixtla's neuralforecast.

### challu-etal-2023-nhits
- **Title**: N-HiTS: Neural Hierarchical Interpolation for Time Series Forecasting
- **Authors**: Challu, Olivares, Oreshkin, Garza, Mergenthaler-Canseco, Dubrawski
- **Year**: 2023
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: deep-learning, neural-nets
- **PDF**: none
- **Key finding**: Hierarchical interpolation with multi-rate sampling improves long-horizon forecasting efficiency over N-BEATS with lower computational cost.
- **Relevance**: Potentially useful for long-horizon RV forecasting; available in neuralforecast.

### nie-etal-2023-patchtst
- **Title**: A Time Series is Worth 64 Words: Long-Term Forecasting with Transformers
- **Authors**: Nie, Nguyen, Siniukov, Kalagnanam
- **Year**: 2023
- **Venue**: ICLR
- **Quality**: recommended
- **Topics**: transformers, deep-learning
- **PDF**: none
- **Key finding**: PatchTST segments time series into patches (like NLP tokens), achieving strong long-horizon forecasting with channel independence and self-supervised pre-training.
- **Relevance**: Leading transformer architecture for time series; candidate for end-to-end vol forecasting.

### liu-etal-2022-tsmixer
- **Title**: TSMixer: An All-MLP Architecture for Time Series Forecasting
- **Authors**: Liu et al.
- **Year**: 2022
- **Venue**: (preprint)
- **Quality**: optional
- **Topics**: deep-learning, neural-nets
- **PDF**: none
- **Key finding**: Simple MLP-based mixing architecture matches or exceeds transformer performance on multivariate time-series benchmarks with lower complexity.
- **Relevance**: Lightweight alternative to transformers; worth benchmarking for computational efficiency.

### lim-etal-2021-tft
- **Title**: Temporal Fusion Transformers for Interpretable Multi-Horizon Time Series Forecasting
- **Authors**: Lim, Arik, Loeff, Pfister
- **Year**: 2021
- **Venue**: Int. J. Forecasting
- **Quality**: optional
- **Topics**: transformers, deep-learning
- **PDF**: none
- **Key finding**: TFT combines variable selection, gating, and temporal attention for interpretable multi-horizon forecasting with static covariate support.
- **Relevance**: Interpretability features could be useful for understanding which inputs drive vol forecasts.

---

## J. Code Repositories and Data Sources

### sheppard-arch
- **Title**: arch: ARCH and GARCH Models in Python
- **Authors**: Sheppard (Kevin)
- **Year**: ongoing
- **Venue**: github.com/bashtage/arch
- **Quality**: essential
- **Topics**: garch, har, evaluation, mcs, code-repo
- **PDF**: none
- **Key finding**: Comprehensive Python package implementing GARCH, HAR, ARCH, bootstrap, MCS, and SPA tests. The standard toolkit for volatility modeling in Python.
- **Relevance**: Primary implementation tool for baselines and evaluation; MCS implementation is critical.

### boudt-etal-highfrequency
- **Title**: highfrequency: Tools for Highfrequency Data Analysis
- **Authors**: Boudt et al.
- **Year**: ongoing
- **Venue**: CRAN (R package)
- **Quality**: recommended
- **Topics**: rv-estimators, jump-detection, code-repo
- **PDF**: none
- **Key finding**: R package implementing all major realized measures (RV, BV, RK, TSRV), jump tests (BNS, Lee-Mykland, ABD), and HEAVY estimation.
- **Relevance**: Reference implementation for realized measures; useful for cross-validating Python implementations.

### harnet-repo
- **Title**: HARNet: Convolutional Neural Network for Realized Volatility
- **Authors**: Reisenhofer, Bayer, Hautsch (mdsunivie)
- **Year**: 2022
- **Venue**: github.com/mdsunivie/HARNet
- **Quality**: essential
- **Topics**: ml-vol, cnn-tcn, code-repo
- **PDF**: none
- **Key finding**: Open-source PyTorch implementation of the HARNet architecture with pre-processing pipelines for RV data.
- **Relevance**: Directly usable code for HAR-aware neural networks; starting point for model development.

### split-icml-repo
- **Title**: SPLIT: Scalable Rashomon Set Enumeration
- **Authors**: Babbar, McTavish, Rudin, Seltzer
- **Year**: 2025
- **Venue**: github.com/VarunBabbar/SPLIT-ICML
- **Quality**: essential
- **Topics**: rashomon, optimal-trees, code-repo
- **PDF**: none
- **Key finding**: Production implementation of the SPLIT algorithm for enumerating the full Rashomon set of optimal decision trees.
- **Relevance**: Core tool for the Rashomon project direction; replaces TreeFARMS.

### treefarms-gosdt-repo
- **Title**: TreeFARMS / GOSDT
- **Authors**: UBC Systopia Lab
- **Year**: 2020-2022
- **Venue**: github.com/ubc-systopia/treeFarms; pygosdt
- **Quality**: essential
- **Topics**: rashomon, optimal-trees, code-repo
- **PDF**: none
- **Key finding**: Original implementations of TreeFARMS (Rashomon set enumeration) and GOSDT (optimal sparse decision trees).
- **Relevance**: Predecessor to SPLIT; useful for comparison and smaller-scale experiments.

### nixtla-neuralforecast
- **Title**: NeuralForecast: Neural Forecasting with PyTorch Lightning
- **Authors**: Nixtla
- **Year**: ongoing
- **Venue**: github.com/Nixtla/neuralforecast
- **Quality**: recommended
- **Topics**: deep-learning, neural-nets, code-repo
- **PDF**: none
- **Key finding**: Unified PyTorch Lightning framework implementing N-BEATS, N-HiTS, PatchTST, TFT, and other neural forecasting architectures.
- **Relevance**: Ready-to-use implementations of deep forecasting models; reduces engineering overhead for benchmarking.

### tsai-repo
- **Title**: tsai: State-of-the-Art Time Series Library for Deep Learning
- **Authors**: (community)
- **Year**: ongoing
- **Venue**: github.com/timeseriesAI/tsai
- **Quality**: optional
- **Topics**: deep-learning, code-repo
- **PDF**: none
- **Key finding**: PyTorch time-series deep learning toolkit with implementations of InceptionTime, ROCKET, and other architectures.
- **Relevance**: Additional model zoo for benchmarking; lower priority than neuralforecast.

### oxford-man-realized-library
- **Title**: Oxford-Man Institute Realized Library
- **Authors**: Oxford-Man Institute
- **Year**: 2009-2022 (discontinued)
- **Venue**: realized.oxford-man.ox.ac.uk/data/download
- **Quality**: essential
- **Topics**: rv-estimators, data-source
- **PDF**: none
- **Key finding**: Daily 5-min RV, BV, RK, and other realized measures for ~25 global equity indices. Discontinued ~2022 but archival data accessible via the `bvhar` R package.
- **Relevance**: Standard academic dataset for RV forecasting; most benchmark papers use this data.

### lobster-data
- **Title**: LOBSTER: Limit Order Book System -- The Efficient Reconstructor
- **Authors**: LOBSTER
- **Year**: ongoing
- **Venue**: lobsterdata.com
- **Quality**: essential
- **Topics**: lob, data-source
- **PDF**: none
- **Key finding**: Academic NASDAQ ITCH-reconstructed L2/L3 limit order book data with free sample datasets and paid academic subscriptions.
- **Relevance**: Primary data source for any LOB-based feature engineering or deep learning approach.

### fred-cboe-truefx
- **Title**: FRED / CBOE (VIX, VVIX, MOVE) / TrueFX
- **Authors**: Federal Reserve, CBOE, TrueFX
- **Year**: ongoing
- **Venue**: fred.stlouisfed.org; cboe.com; truefx.com
- **Quality**: essential
- **Topics**: data-source, options-implied, cross-asset
- **PDF**: none
- **Key finding**: Free macro data (FRED), implied vol indices (VIX/VVIX/MOVE from CBOE), and FX tick data (TrueFX) for cross-asset feature construction.
- **Relevance**: Essential supplementary data sources for cross-asset and options-implied features.

### optionmetrics-ivydb
- **Title**: OptionMetrics IvyDB
- **Authors**: OptionMetrics
- **Year**: ongoing
- **Venue**: optionmetrics.com (internal at GS in many cases)
- **Quality**: recommended
- **Topics**: options-implied, data-source
- **PDF**: none
- **Key finding**: Full implied volatility surface data for US equities and indices; the standard academic source for options-implied features.
- **Relevance**: IV surface features are among the most promising additions to RV models; may be available internally at GS.

---

## K. Practitioner and Industry Resources

### jpmorgan-quant-research
- **Title**: Big Data and AI Strategies Reports
- **Authors**: JP Morgan Quantitative Research
- **Year**: ongoing
- **Venue**: JP Morgan internal/client reports
- **Quality**: recommended
- **Topics**: ml-vol, feature-engineering
- **PDF**: none
- **Key finding**: Regular reports on ML applications in finance including volatility modeling, often with practical implementation details.
- **Relevance**: Industry benchmarks and feature ideas from a major sell-side desk.

### aqr-working-papers
- **Title**: AQR Working Papers (Volatility)
- **Authors**: AQR Capital Management
- **Year**: ongoing
- **Venue**: aqr.com/insights
- **Quality**: recommended
- **Topics**: vrp, cross-asset
- **PDF**: none
- **Key finding**: Frequent working papers on volatility, factor investing, and risk premia from a leading systematic fund.
- **Relevance**: Practitioner perspective on vol strategies; useful for feature ideas and economic motivation.

### two-sigma-blog
- **Title**: Two Sigma Blog (ML + Volatility)
- **Authors**: Two Sigma
- **Year**: ongoing
- **Venue**: twosigma.com/articles
- **Quality**: optional
- **Topics**: ml-vol
- **PDF**: none
- **Key finding**: Occasional pieces on ML applications including volatility modeling from a leading quant fund.
- **Relevance**: Industry perspective; lower priority than academic papers but useful for practical insights.

### gs-securities-research
- **Title**: Goldman Sachs Securities Research
- **Authors**: Goldman Sachs
- **Year**: ongoing
- **Venue**: Internal access
- **Quality**: recommended
- **Topics**: ml-vol, options-implied, cross-asset
- **PDF**: none
- **Key finding**: Proprietary research on volatility, derivatives, and systematic strategies available through internal GS access.
- **Relevance**: Directly relevant to the internship; check internal portals for vol-specific publications.

### sofie-quantminds-wilmott
- **Title**: SoFiE / QuantMinds / RiskMinds / Wilmott
- **Authors**: Various (conferences and forums)
- **Year**: ongoing
- **Venue**: SoFiE (Society for Financial Econometrics); QuantMinds/RiskMinds conferences; Wilmott magazine; Quantocracy
- **Quality**: optional
- **Topics**: evaluation, ml-vol
- **PDF**: none
- **Key finding**: Academic and practitioner conferences/forums covering latest developments in financial econometrics and quantitative finance.
- **Relevance**: Useful for tracking cutting-edge work and networking; conference papers often precede journal publication.

### bennett-2014
- **Title**: Trading Volatility: Correlation, Term Structure and Skew
- **Authors**: Bennett
- **Year**: 2014
- **Venue**: Free PDF (trading-volatility.com)
- **Quality**: essential
- **Topics**: options-implied, vrp, foundational
- **PDF**: none
- **Key finding**: Best single resource on volatility surface mechanics -- smile, skew, term structure, and correlation trading -- written by a former head of quant strategy at Banco Santander.
- **Relevance**: Essential for building intuition about IV surface features before using them as model inputs.

### cartea-jaimungal-penalva-2015
- **Title**: Algorithmic and High-Frequency Trading
- **Authors**: Cartea, Jaimungal, Penalva
- **Year**: 2015
- **Venue**: Cambridge University Press (textbook)
- **Quality**: essential
- **Topics**: microstructure-noise, lob, foundational
- **PDF**: none
- **Key finding**: Graduate textbook unifying microstructure, execution, and market making under a single stochastic control framework. Covers optimal execution, VWAP/POV targeting, and order imbalance with rigorous HJB derivations.
- **Relevance**: Essential framework for understanding microstructure features and execution context in which vol forecasts are consumed.

---

## Topic Tag Vocabulary

`rv-estimators`, `microstructure-noise`, `jump-detection`, `har`, `harq`, `har-extensions`, `garch`, `realized-garch`, `rough-vol`, `ml-vol`, `gradient-boosting`, `neural-nets`, `deep-learning`, `lstm`, `cnn-tcn`, `transformers`, `gnn`, `ensemble`, `rashomon`, `optimal-trees`, `regression-trees`, `survival-trees`, `lob`, `vrp`, `options-implied`, `cross-asset`, `spillovers`, `evaluation`, `qlike`, `mcs`, `validation`, `purged-cv`, `feature-engineering`, `interpretability`, `fairness`, `long-memory`, `sentiment`, `regime`, `data-source`, `code-repo`, `foundational`
