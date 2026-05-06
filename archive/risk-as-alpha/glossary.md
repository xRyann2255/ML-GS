# Glossary

---

# Part 1: Core Concepts

Terms you must understand to work on this project. These appear in daily conversations, the spec, and the implementation plan.

---

## A

**Alpha**
Risk-adjusted excess return above a benchmark or factor model. In this project, the core question is whether risk-system outputs contain alpha — predictive information about future returns that isn't explained by known public factors. Distinct from raw return; a strategy can have positive returns but zero alpha if those returns are fully explained by market beta or other exposures.

**Asset Class**
A category of financial instruments with similar characteristics. The main asset classes in this project: equities, rates/fixed income, FX (foreign exchange), credit, and commodities. The cross-asset (XA) desk trades across all of these, which is why intermediary asset pricing theory — which predicts cross-asset effects — is a natural fit.

## B

**Backtesting**
Simulating a trading strategy on historical data to evaluate its performance. Critical pitfalls include lookahead bias, survivorship bias, ignoring transaction costs, and overfitting to the in-sample period. This project uses transaction-cost-aware backtesting with purged cross-validation and deflated Sharpe ratios to mitigate these issues.

**Balance Sheet Constraints**
Limits on a financial institution's capacity to hold risk, arising from regulatory capital requirements, internal risk limits (VaR limits), and leverage constraints. The central thesis of intermediary asset pricing: when these constraints bind (e.g., VaR utilization near 100%), dealers are forced to reduce positions, creating predictable price pressure across asset classes.

**Beta**
The sensitivity of an asset's returns to a benchmark or factor. Market beta measures sensitivity to the broad market. In this project, controlling for beta is essential — a signal that just predicts "market goes up" is capturing market beta, not alpha.

**Bi-Temporal**
A data modeling approach where every record has two time dimensions: (1) the time the event occurred in the real world (value-time or valid-time) and (2) the time the record was entered or known in the system (transaction-time). SecDB objects are bi-temporal, which is critical for point-in-time correctness — you can query "what did we know about this position as of date X?" without lookahead bias.

**Book (Trading Book)**
The collection of positions held by a specific trading desk or trader. "Book-level Greeks" means the risk sensitivities (delta, gamma, etc.) computed for a specific desk's positions, as opposed to firm-level aggregates. SecDB's advantage is providing book-level data with correct dealer sign.

## C

**Capacity (Strategy Capacity)**
The maximum capital a strategy can deploy before market impact degrades returns to the point where the strategy is no longer profitable. A critical practical concern: a Sharpe 2.0 strategy with $1M capacity is an interesting research finding but not a tradeable strategy for a bank. This project includes explicit capacity analysis in Phase 4A.

**Combinatorial Purged Cross-Validation (CPCV)**
An extension of purged K-fold CV (Lopez de Prado, AFML) that generates all C(N, k) combinatorial train/test partitions from N groups, producing a *distribution* of Sharpe ratios from a single backtest history rather than a single point estimate. More informative than standard CV because you can assess the variance of performance, not just the mean.

**Component VaR**
The contribution of a specific asset, desk, or asset class to the total portfolio VaR. If a firm's total VaR is $100M and rates contribute $45M, the rates component VaR is $45M. Changes in component VaR over time reveal capital reallocation across asset classes — a key feature family in this project.

**Confound Check**
Testing whether a signal's predictive power is genuinely novel or simply correlated with a known public factor. In this project: if VaR utilization predicts returns, does it still predict after controlling for VIX, credit spreads, and term slope? If not, the signal is redundant with publicly available information.

**Cross-Validation (CV)**
A resampling technique for evaluating model performance by splitting data into training and testing subsets. Standard K-fold CV randomly splits data, which is invalid for time series (future data leaks into training). This project uses purged K-fold CV with embargo, which respects temporal ordering.

**Crowding**
When many market participants hold similar positions, creating hidden concentration risk. If everyone is long the same factor, an adverse shock triggers simultaneous selling, amplifying the drawdown. Factor-VaR Herfindahl index measures this: high concentration in a few factors = high crowding risk.

## D

**Data Snooping**
The practice of repeatedly testing hypotheses on the same dataset until finding a statistically significant result by chance. With enough trials, you'll always find something that "works" in-sample. The Deflated Sharpe Ratio and Probability of Backtest Overfitting are designed to detect and adjust for this.

**Deflated Sharpe Ratio (DSR)**
Bailey-Lopez de Prado (2014) adjustment that accounts for the number of trials conducted, the sample length, and the non-normality (skewness, kurtosis) of returns. A raw Sharpe of 1.5 might deflate to 0.3 after adjusting for 50 trials on 5 years of data. Non-negotiable in this project — applied to every reported Sharpe number.

**Delta**
The rate of change of an option's price with respect to the underlying asset's price. A delta of 0.5 means the option price moves $0.50 for every $1 move in the underlying. Aggregate dealer delta across all positions determines how much hedging activity occurs when markets move.

**Delta-Hedging**
Trading the underlying asset to offset the delta exposure of an options position, making the position delta-neutral. When dealers are net short gamma, delta-hedging amplifies market moves (they buy as markets rise, sell as markets fall). When net long gamma, hedging dampens moves. This is the core mechanism behind the book-gamma signal (Project 2).

**Drawdown**
The peak-to-trough decline in cumulative returns before a new peak is reached. Maximum drawdown is the worst such decline in the backtest. A key risk metric because it measures the worst pain a strategy holder would experience. Reported alongside Sharpe in all results.

## E

**Embargo**
In purged cross-validation, the buffer period after the test set that is excluded from the training set. Prevents information leakage through autocorrelated labels — if your label is a 5-day forward return and the test set ends on day T, training data from days T+1 through T+5 would contain overlapping information. The embargo removes these observations.

**Entitlements**
Access permissions within SecDB that determine which data a user can read or write. Entitlements are typically desk-scoped — an XA desk intern may not automatically have access to every desk's risk cubes. Phase 0 of this project includes an entitlements audit to confirm data access before building infrastructure.

**Experiment Tracker**
A system for logging every model configuration, hyperparameter choice, and result tried during research. In this project, implemented as a simple CSV logging every experiment's ID, description, features, target, model type, CV method, raw Sharpe, DSR-adjusted Sharpe, and IC. The total trial count feeds directly into the DSR adjustment — honest tracking prevents data-snooping.

## F

**Factor (Risk Factor)**
A systematic driver of returns across multiple assets. Common factors include market (beta), size, value, momentum, quality, and volatility. Factor models decompose returns into factor exposures (betas) times factor returns plus an idiosyncratic residual. This project uses Barra-style factor decompositions from SecDB.

**Factor-VaR Decomposition**
Breaking down total VaR into contributions from individual risk factors (interest rates, equity markets, credit spreads, FX, etc.). Shows which factors are driving the firm's risk. The Herfindahl index of factor-VaR shares measures concentration — high HHI means the firm's risk is dominated by a few factors (crowding signal).

**False Strategy Theorem**
Lopez de Prado (MLAM 2020) proves that with 1,000 skill-less strategies, the expected maximum Sharpe is approximately 3.26. In other words, even random strategies will produce impressive-looking Sharpes if you try enough of them. This is why the DSR and experiment tracking are non-negotiable.

**Feature Engineering**
The process of creating input variables (features) for ML models from raw data. In this project, raw risk cube outputs (VaR, scenario P&L) are transformed into features like rate-of-change, z-scores, Herfindahl indices, and rolling correlations. Feature engineering is where domain knowledge matters most — theory-motivated features outperform data-mined ones.

**Feature Importance**
Measures of how much each input feature contributes to model predictions. Three main methods: MDI (Mean Decrease in Impurity — built into trees, biased toward high-cardinality features), MDA (Mean Decrease in Accuracy — permutation-based, more reliable), and SHAP (game-theoretic, most interpretable). This project uses SHAP for presentation and MDA across CV folds for stability checks.

**Fire Sale**
Forced selling of assets at below-fundamental-value prices, typically driven by balance-sheet constraints (margin calls, VaR limit breaches, redemptions). Coval-Stafford (2007 JFE) show mutual-fund fire sales predict 5-day price pressure with subsequent reversals. The VaR utilization signal in this project is designed to capture the same dynamic at the dealer level.

**Fixed Effects**
In panel regression, fixed effects are intercepts that vary by group (e.g., asset class). They control for time-invariant differences between groups, isolating the within-group variation. In this project, asset-class fixed effects in the cross-asset panel ensure that results aren't driven by permanent differences between, say, rates and equities.

**Forced Deleveraging**
When a dealer is forced to reduce positions due to hitting risk limits (VaR limit, leverage constraint, capital requirement). Creates predictable selling pressure in the positions being unwound. High VaR utilization (usage near limit) is a leading indicator of forced deleveraging — the core theoretical mechanism behind the VaR utilization signal.

**Forward Return**
The return of an asset over a future period. A 5-day forward return starting from today is the return from today to 5 business days later. Used as labels (prediction targets) in ML models. Point-in-time discipline is critical: you must not use forward returns that overlap with your features' knowledge dates.

## G

**Gamma**
The rate of change of an option's delta with respect to the underlying asset's price. Measures the curvature of the option's payoff. Aggregate dealer gamma is the central variable in the book-gamma project: when dealers are net short gamma, their hedging activity amplifies market moves; when net long gamma, it dampens them.

**Gamma Exposure (GEX)**
The aggregate net gamma of all dealer option positions on a given underlying. Public GEX estimates (from services like SpotGamma) assume the dealer side of every trade, which is approximately 30% wrong. SecDB provides the real book-level gamma with correct sign — a clean competitive edge.

**Gaussian Mixture Model (GMM)**
A probabilistic model that assumes data is generated from a mixture of K Gaussian distributions with unknown parameters. Used in this project for regime detection: fit a GMM on macro features (VIX, credit spread, term slope, USD, realized correlation) to classify market states into 3-4 regimes (Crisis, Steady State, Inflation, Walking on Ice). Follows the Two Sigma regime-modeling template.

**Gradient-Boosted Trees (GBT)**
An ensemble method that builds decision trees sequentially, with each tree correcting the errors of the previous ones. LightGBM, XGBoost, and CatBoost are the dominant implementations. The Tier 1 workhorse for tabular financial data: handles mixed-type features, missing data, monotonic constraints, and asymmetric losses. Failure modes: extrapolates as constants (bad in regime shifts), overfits fast on low-SNR data, SHAP importance unstable under correlated features.

**Greeks**
The partial derivatives of an option's price with respect to various inputs. Named after Greek letters: delta (∂P/∂S), gamma (∂²P/∂S²), vega (∂P/∂σ), theta (∂P/∂t), rho (∂P/∂r). Cross-Greeks include vanna (∂²P/∂S∂σ) and volga/vomma (∂²P/∂σ²). In this project, aggregated book-level Greeks from SecDB are features for the book-gamma signal.

**gs-quant**
Goldman Sachs's open-source Python SDK (~9.9k GitHub stars, Apache 2.0). Exposes a subset of internal pricing models and risk measures with `PricingContext`, `HistoricalPricingContext`, `Portfolio`, 400+ datasets via `Dataset`/`DataApi`, a backtester, and REST API wrappers. The closest public proxy for SecDB's data model and the recommended way to practice SecDB-style workflows externally.

## H

**Haircut Sharpe**
Harvey-Liu (2015 JPM) methodology that applies multiple-testing corrections (Bonferroni, Holm, BHY-FDR) to reported Sharpe ratios. The industry rule-of-thumb "50% haircut" is wrong — marginal Sharpes need much larger haircuts, while exceptional ones barely need any. Used in this project as a cross-check alongside DSR.

**Herfindahl-Hirschman Index (HHI)**
A measure of concentration calculated as the sum of squared market shares. Ranges from 1/N (perfectly diversified across N equal components) to 1 (fully concentrated in one component). In this project, applied to factor-VaR shares: HHI of 0.8 means the firm's risk is dominated by one factor (crowding signal). An HHI that's rising signals increasing concentration.

**Holdout (True Out-of-Sample)**
A portion of data reserved at the start of the project and never touched until the final evaluation. Unlike cross-validation (which reuses data across folds), the holdout is a single-use, one-shot test. In this project, 3-6 months are reserved at project start and used only in Phase 5 for the walk-forward test. If you iterate on holdout results, it's no longer out-of-sample.

## I

**Information Coefficient (IC)**
The cross-sectional correlation between predicted returns and actual returns. IC of 0.05 is considered good in equity factor investing; IC of 0.10 is exceptional. More informative than accuracy because it captures the ranking quality of predictions, not just direction. The primary performance metric in this project, reported alongside Sharpe.

**Intermediary Asset Pricing**
A branch of financial theory (He-Krishnamurthy 2013, Adrian-Etula-Muir 2014) that models financial intermediaries (broker-dealers, banks) as the marginal price-setters in markets. When intermediary balance-sheet constraints bind, risk premia rise nonlinearly across all asset classes. The theoretical foundation of this entire project: SecDB's risk-system outputs are direct measurements of these constraints.

## L

**Label (ML Label)**
The target variable that a model is trained to predict. In this project, labels include: triple-barrier labels (+1/-1/0), forward returns (1d, 5d, 21d), VIX innovations, realized volatility, and drawdown indicators. Label construction is a critical design choice — overfitting the label definition is a common failure mode.

**Leverage**
The ratio of total assets (or exposure) to equity capital. Higher leverage means more assets supported by less capital — amplifying both gains and losses. Dealer leverage is the central variable in intermediary asset pricing: Adrian-Etula-Muir (2014) show a single-factor leverage SDF explains R²=77% of test portfolios. SecDB's VaR utilization is a more precise measure of effective leverage constraints than accounting leverage.

**LightGBM**
Microsoft's gradient-boosted tree implementation optimized for speed and memory efficiency. Uses histogram-based splitting and leaf-wise tree growth. The default workhorse model in this project: handles tabular features, missing data, and categorical variables natively. Wins the vast majority of finance Kaggle competitions and the Gu-Kelly-Xiu (2020) horse-race.

**Lookahead Bias**
Using information that was not available at the time a decision would have been made. The most common and dangerous form of backtest bias. Examples: using restated financial data (not the originally reported values), using current index constituents (survivorship bias), or aligning features with labels using value-time instead of transaction-time. SecDB's bi-temporal design and this project's point-in-time stamping are specifically designed to prevent this.

## M

**MDA (Mean Decrease in Accuracy)**
A permutation-based feature importance method: shuffle one feature's values across all observations and measure how much model accuracy decreases. More reliable than MDI because it's model-agnostic and doesn't favor high-cardinality features. In this project, MDA stability across CV folds is the primary check for feature importance robustness — if a feature's MDA flips sign across folds, it's unreliable.

**Meta-Labeling**
A two-stage approach (Lopez de Prado AFML): a primary model predicts the *side* of a trade (long/short), and a secondary model predicts the *size* (confidence/probability of success). The secondary model's label is binary: 1 if the primary model was correct, 0 if not. This converts a low-precision primary model into a filtered, higher-precision ensemble. Infrastructure built in Phase 1 but used in later phases if needed.

## O

**Overfitting**
When a model learns noise in the training data rather than genuine patterns, performing well in-sample but poorly out-of-sample. The central methodological concern of this project. Mitigated by: purged CV, DSR adjustment, ridge baseline comparison, CPCV Sharpe distributions, experiment tracking, limiting total trials, and preferring theory-motivated features over data-mining.

## P

**Panel Data**
Data with both cross-sectional (multiple entities) and time-series dimensions. In this project: (asset class × date) observations. Panel structure is important because it increases effective sample size — instead of 1,250 firm-level daily observations, you have 1,250 × N asset classes. Panel regressions with fixed effects and clustered standard errors are the standard approach.

**P&L (Profit and Loss)**
The gain or loss on a position or strategy. Scenario P&L: the hypothetical P&L under a specific stress scenario (e.g., "rates up 100bps, equities down 20%"). In SecDB, nightly risk cubes compute scenario P&Ls at standard shock nodes for every position. The rank and dispersion of scenario P&Ls across scenarios are features in this project.

**Point-in-Time (PIT)**
Data accessed as it was known at a specific historical moment, not with the benefit of hindsight. If a company restated its earnings on March 15, a point-in-time database shows the original (incorrect) value for queries dated before March 15. Critical for preventing lookahead bias. This project stamps every feature with its "knowledge date" — the first date the information was available.

**Purged K-Fold CV**
A time-series-aware cross-validation method (Lopez de Prado AFML Ch. 7) that: (1) respects temporal ordering (train set always before test set), (2) purges training observations whose labels overlap temporally with the test set, and (3) adds an embargo buffer after the test set. The baseline validation method for every model in this project.

## R

**Realized Volatility (RV)**
The actual observed volatility of an asset, computed from historical returns (typically as the annualized standard deviation of daily returns over a rolling window). Contrasted with implied volatility (which is forward-looking). The variance risk premium (IV² - RV²) predicts returns at quarterly horizons (Bollerslev-Tauchen-Zhou 2009).

**Regime**
A distinct market state characterized by different statistical properties (mean, variance, correlations) of asset returns. Common regimes: crisis (high vol, high correlation, negative returns), steady state (low vol, normal correlations), inflation (rising rates, sector rotation). Regime detection is important because signals may work in some regimes but not others — and because the transition between regimes is often where the most money is made or lost.

**Regularization**
Adding a penalty to a model's objective function to prevent overfitting. L1 (Lasso) penalizes the sum of absolute coefficients (drives some to zero). L2 (Ridge) penalizes the sum of squared coefficients (shrinks all toward zero). Regularized linear models are the mandatory baseline in this project — if LightGBM doesn't beat ridge, the ML isn't adding value.

**Ridge Regression (L2 Regularization)**
Linear regression with an L2 penalty (sum of squared coefficients). Shrinks all coefficients toward zero without setting any exactly to zero. The mandatory baseline model in this project: Kozak-Nagel-Santosh (2020 JFE) show that ridge-shrunk SDFs on PCs of characteristics match nonlinear ML. If your GBM doesn't beat ridge on the same features, you haven't learned anything beyond linear relationships.

**Risk Cube**
A structured output from the nightly risk computation that contains VaR, scenario P&Ls, factor decompositions, and Greeks for every position across the firm. Organized by desk, asset class, and risk measure. The primary data source for this project.

## S

**Scenario P&L**
The hypothetical profit or loss of a portfolio under a specific stress scenario. Standard scenarios include "rates up 100bps," "equities down 20%," "credit spreads widen 200bps," etc. In this project, features extracted from scenario P&L include: rank (which scenario is worst), dispersion (standard deviation of P&Ls across scenarios), and worst-case scenario identity (categorical feature indicating directional exposure).

**SecDB (Securities Database)**
Goldman Sachs's proprietary in-memory object store, in operation for 30+ years. Organized into eventually-consistent replication groups (rings) synchronized by SecSync. Key properties: bi-temporal (value-time and transaction-time), dependency graph for lazy recomputation, >10,000 globally distributed object databases, 2.5 billion connections, 164 TB of messages, 8 PB of data served. The "one price" principle ensures every desk sees consistent valuations.

**SHAP (SHapley Additive exPlanations)**
A game-theoretic approach to feature importance (Lundberg-Lee 2017) that computes each feature's marginal contribution to each prediction. Produces both global importance rankings and local explanations (why did the model predict X for this specific observation?). The preferred interpretation method in this project — SHAP waterfall plots are included in the final presentation. Caveat: SHAP importance can be unstable when features are highly correlated.

**Sharpe Ratio**
The ratio of excess return to volatility: (mean return - risk-free rate) / standard deviation of returns, annualized by multiplying by √252 for daily data. The primary performance metric. In this project, never reported without DSR or Haircut adjustment. A raw Sharpe of 1.0 means the strategy earns its risk (one unit of return per unit of volatility per year).

**Signal**
A quantitative variable used to predict future returns or risk. In this project, "signal" refers to the processed features derived from risk-system outputs (e.g., VaR utilization z-score, factor concentration Herfindahl) that are tested for predictive power. A signal that survives DSR adjustment, confound checks, and transaction costs is a credible alpha source.

**Slang**
Goldman Sachs's proprietary C-like interpreted DSL (domain-specific language) created in 1992 with tight SecDB integration. The codebase has >200 million lines, written by ~3,000 developers over 30 years, powering ~160 million daily jobs and >300 million compute-hours per week. Currently transitioning from tree-walker interpreter to bytecode+JIT. Built by Dubno/Gribble/Lundeen under Armen Avanessians in J. Aron; Martin Chavez drove firm-wide adoption.

**Sortino Ratio**
Similar to Sharpe but uses downside deviation (standard deviation of negative returns only) instead of total volatility. Penalizes downside risk only, not upside volatility. Reported alongside Sharpe in this project's results.

## T

**Transaction Costs**
The costs of executing trades: bid-ask spread, market impact, commissions, and slippage. Ignoring transaction costs is a major failure mode in backtesting — a signal with Sharpe 2.0 gross may have Sharpe 0.2 net of costs if turnover is high. This project parameterizes costs per asset class (different spreads for rates futures vs. single-name equities) and reports the Sharpe-vs-cost curve.

**Triple-Barrier Labeling**
Lopez de Prado (AFML Ch. 3) method for constructing ML labels. Three barriers: upper (take-profit), lower (stop-loss), and vertical (maximum holding period). The label is determined by which barrier is hit first: +1 (upper), -1 (lower), or the sign of the return at the vertical barrier. Barriers are scaled by rolling volatility so they adapt to market conditions. Superior to fixed-threshold labels because it handles varying volatility regimes.

**Turnover**
The rate at which a strategy's positions change. High turnover means frequent trading, which incurs more transaction costs. A signal that flips direction daily has much higher turnover (and cost drag) than one that holds for weeks. Turnover is a first-class metric in this project, reported alongside Sharpe and IC.

## V

**Value at Risk (VaR)**
A risk measure that estimates the maximum loss a portfolio could experience over a given time horizon at a given confidence level. "1-day 99% VaR of $50M" means there is a 1% chance of losing more than $50M in one day. Computed from SecDB nightly risk cubes. In this project, VaR and its derivatives (component VaR, factor-VaR, VaR utilization) are the primary feature source.

**VaR Utilization**
VaR usage as a percentage of the VaR limit. If a desk's VaR is $80M against a $100M limit, utilization is 80%. High utilization (approaching 100%) signals balance-sheet constraints are binding — the desk cannot take on more risk and may be forced to reduce positions. Rate of change of utilization is also informative: rapidly rising utilization suggests stress. This is the single most theory-grounded feature in this project, directly measuring the binding constraint that intermediary asset pricing theory says drives risk premia.

## W

**Walk-Forward Test**
An out-of-sample validation method where the model is trained on all data up to time T and tested on data from T to T+h. The key distinction from cross-validation: walk-forward uses a truly held-out future period that was never part of any training or validation. In this project, the Phase 5 walk-forward test uses the 3-6 months reserved at project start — a single, one-shot evaluation with no iteration allowed.

## Z

**Z-Score**
A standardized value measuring how many standard deviations an observation is from the mean. Computed as (x - mean) / std, typically over a rolling window. In this project, VaR utilization z-score over a 21-day rolling window captures whether current utilization is abnormally high relative to recent history — a more informative feature than raw utilization level.

**Z.1 Tables**
See the FAQ entry on Fed Z.1 tables. The Federal Reserve's Financial Accounts of the United States, published quarterly with ~3 month lag. Contains aggregate broker-dealer balance sheet data used by academics to proxy dealer leverage constraints. The data bottleneck that SecDB's internal risk outputs directly address.

---

# Part 2: Supplementary Terms

Terms that provide additional context, are relevant to fallback projects, or represent concepts you'll encounter in the literature but won't use daily.

---

## A

**ADWIN (Adaptive Windowing)**
A concept-drift detection algorithm (Bifet-Gavaldà 2007) that maintains a variable-length window of recent observations and flags when the statistical properties of the data change significantly. Used in this project as an optional trigger to retrain models when prediction errors shift distribution.

**Alphalens**
Open-source Python library (originally by Quantopian) for factor analysis and evaluation. Computes IC, quantile returns, turnover, and factor-weighted return tear sheets. A tooling dependency, not a concept you need to internalize.

**Arbitrage**
Simultaneously buying and selling related instruments to profit from price discrepancies with zero net risk. Relevant to this project because no-arbitrage constraints inform vol-surface modeling (Project 5 fallback) and factor structures.

**Autoencoder**
A neural network trained to compress input data into a lower-dimensional representation and then reconstruct the original. In asset pricing, Gu-Kelly-Xiu (2021 JEcon) show autoencoders add value as upstream feature extractors when embedded in a no-arbitrage factor structure. In this project's ML hierarchy, autoencoders sit in Tier 2: useful as feature extractors, not as standalone predictors.

## B

**Barra-Style Factors**
A risk model framework (originally from MSCI Barra) that decomposes asset returns into systematic factor exposures (market, size, value, momentum, etc.) plus an idiosyncratic residual. Relevant primarily to the Project 4 fallback (factor-neutral ML residual strategy).

**Basis (Cross-Currency)**
The difference between the FX-implied interest rate and the actual interest rate between two currencies. Du-Tepper-Verdelhan (2018 JF) show this basis widens at quarter-ends due to G-SIB balance-sheet constraints — a potential feature or validation target.

**Bayesian Online Change-Point Detection (BOCPD)**
An algorithm (Adams-MacKay 2007) for detecting change-points in streaming data. More sophisticated than CUSUM/PELT but also more computationally expensive. Classified as "not realistic" for a 12-week project but potentially feasible with 20 weeks.

**Broker-Dealer**
A financial institution that trades securities both on behalf of clients (broker) and for its own account (dealer). Goldman Sachs, JPMorgan, Morgan Stanley are broker-dealers. The intermediary asset pricing literature models these as the key intermediaries whose constraints drive asset prices.

## C

**Calibration (Model Calibration)**
The process of fitting a model's parameters to match observed market prices. In options, calibrating SVI/SABR/Nelson-Siegel to match quoted option prices. Calibration residuals are the core feature of Project 3 (fallback).

**CatBoost**
A gradient-boosted tree algorithm (from Yandex) with native categorical feature handling and ordered boosting. An alternative to LightGBM — both are valid Tier 1 choices.

**Change-Point Detection**
Statistical methods for identifying where a time series' underlying distribution changes. CUSUM for online, PELT for offline. Used in regime transition detection.

**Charm**
The rate of change of delta with respect to time (∂delta/∂time). In the book-gamma project (Project 2), aggregate dealer charm predicts end-of-day drift as options approach expiry.

**Compstat**
Compustat — a database of financial statement data. External researchers use it to compute leverage proxies. Much coarser than internal risk-system data.

**Correlation Regime**
A market state where cross-asset correlations are unusually high. The top eigenvalue share (λ₁/Σλ) of the rolling correlation matrix rises during drawdowns. A potential feature from SecDB's cross-asset data.

**CoVaR (Conditional Value at Risk)**
Adrian-Brunnermeier (2016 AER): VaR of the financial system conditional on a specific institution being in distress. A potential feature if constructible from SecDB.

**Credit Default Swap (CDS)**
A derivative providing protection against default of a reference entity. CDS spreads measure credit risk. CDS-bond basis can signal market stress.

**CUSUM (Cumulative Sum)**
A sequential analysis technique (Page 1954) for detecting mean shifts. Used in AFML Ch. 17 for event-driven sampling.

## D

**Deep Learning**
Neural networks with multiple hidden layers. For tabular financial data, largely oversold — DLinear beats Transformers on 9/9 benchmarks (Zeng et al. 2023), and ~95% of M5 top-50 used LightGBM. Real edge only in order-book microstructure, text, representation learning, and derivatives hedging.

**Dependency Graph**
In SecDB, objects form a DAG. When a market input changes, downstream prices, Greeks, and scenarios are lazily invalidated and recomputed. The machinery behind "one price."

**DLinear**
A one-layer linear model (Zeng et al. 2023 AAAI) that beats Transformer-based time series models on 9/9 benchmarks. Evidence that complexity doesn't help for most financial time series.

## E

**Elastic Net**
Regularized regression combining L1 (Lasso) and L2 (Ridge) penalties. Useful with correlated features. Part of the baseline toolkit.

## F

**Fractional Differentiation**
A technique (AFML Ch. 5) for making price series stationary while preserving memory. Finds the minimum differencing order d (0 < d < 1) that passes ADF tests. Implemented via `fracdiff`.

## G

**Gamma-Flip Level**
The underlying price where aggregate dealer gamma switches sign. Acts as a regime boundary in the book-gamma project. Distance-to-flip is a continuous feature.

## H

**Hidden Markov Model (HMM)**
The industry default for regime detection (2-3 states on returns + volatility). Cheap (2 days with `hmmlearn`), interpretable, but limited: confirms regime changes rather than predicting them. Random Forests on macro features often outperform for next-period classification.

## I

**Idiosyncratic Return**
The return component not explained by systematic factors — the residual ε from a factor decomposition. Mean-reverts over 1-5 days in stat-arb frameworks. Relevant to Project 4 fallback.

**Implied Volatility (IV)**
The volatility implied by an option's market price via Black-Scholes inversion. Varies by strike (smile/skew) and expiry (term structure), forming the IV surface.

**Implied Volatility Surface (IVS)**
The 3D surface of IVs across strikes and expirations. Rich in information but caveat from Muravyev-Pearson-Pollet (2022): IVS and skew partly proxy for stock-borrow fees.

**IPCA (Instrumented Principal Components Analysis)**
Kelly-Pruitt-Su (2019 JFE): latent factors with characteristic-instrumented loadings. A unified cross-asset factor framework. Alternative to Barra-style decomposition.

## K

**K-Fold Cross-Validation**
See Cross-Validation in Part 1. Standard K-fold is invalid for time series. This project uses purged K-fold.

## L

**Lasso (L1 Regularization)**
Linear regression with L1 penalty — drives coefficients to zero for feature selection. Unstable with correlated features. Part of the baseline toolkit.

**Liquidity**
The ease of buying/selling without price impact. Relevant to transaction costs and forced-deleveraging dynamics.

## M

**Market Impact**
Price movement caused by executing a trade. Limits strategy capacity. Addressed in Phase 4A.

**Marquee**
GS's client-facing analytics platform. The external projection of SecDB: 400+ datasets, pricing/risk, backtester.

**Maximum Drawdown**
Largest peak-to-trough decline in cumulative returns. Captures worst-case experience. Reported alongside Sharpe.

**MDI (Mean Decrease in Impurity)**
Tree-based feature importance measuring total impurity reduction per feature. Biased toward high-cardinality features. Use MDA and SHAP instead.

**Mean Reversion**
The tendency to return toward historical average. VaR utilization spikes may predict mean-reversion in concentrated asset classes.

**mlfinlab**
Python library (Hudson & Thames) implementing AFML methods. Production-ready but has had bugs — double-check.

**MLflow**
Open-source ML lifecycle platform. Used for experiment tracking alongside W&B.

**Momentum**
The tendency for recent winners to keep winning. Cross-asset momentum reversals (when forced deleveraging breaks momentum) are a prediction target.

**Monotonic Constraints**
Tree-model constraint forcing monotonic feature-prediction relationships. Encodes domain knowledge. LightGBM supports natively.

## N

**Nelson-Siegel Model**
Parametric model for yield/vol curves using level, slope, curvature. Diebold-Li (2006) show these predict returns. Calibration residuals are features in Project 3.

**N-HiTS**
Neural time series architecture (Challu et al. 2022). Strong MLP baseline if deep learning is attempted. Not the default approach.

**No-Arbitrage**
The condition of no risk-free profit opportunities. Enforced as constraints in factor models and vol-surface smoothing.

## P

**PatchTST**
Transformer-based time series model (Nie et al. 2023 ICLR). Credible deep learning baseline. Not the default approach.

**Principal Component Analysis (PCA)**
Dimensionality reduction finding orthogonal directions of max variance. Top eigenvalue share indicates correlation regime. Surface PCA compresses IV surfaces into ~3 factors.

**Probability of Backtest Overfitting (PBO)**
Bailey-Borwein-LdP-Zhu (2014, 2016): probability that the best in-sample strategy underperforms out-of-sample median. PBO > 0.5 = your selection process is overfitting.

**Pyfolio**
Python library for portfolio analytics tear-sheets. Generates standardized performance reports.

## Q

**Quantile Returns**
Returns of portfolios formed by sorting assets into quantiles by signal strength. Top-minus-bottom spread measures signal magnitude.

## R

**Random Matrix Theory (RMT)**
Theory describing eigenvalue distributions of large random matrices. Distinguishes real correlation structure from noise. Laloux-Cizeau-Bouchaud-Potters (1999) apply to financial correlations.

**Residual**
Difference between observed and model-predicted values. In factor models: idiosyncratic return. In calibration: demand/flow information per Gârleanu-Pedersen-Poteshman (2009).

**Ring (SecDB)**
A replication group of SecDB objects, synchronized by SecSync for eventual consistency.

**Risk-Neutral Skewness (RNS)**
Skewness of the risk-neutral return distribution. Its predictive sign is genuinely contested in the literature — treat with caution.

## S

**SABR Model**
Stochastic volatility model for IV interpolation, common for rates options. Calibration residuals are potential features in Project 3.

**Sample Uniqueness**
Lopez de Prado concept: degree to which a sample's label is determined by unique-to-that-sample observations. Weights by average uniqueness reduce effective weight of redundant observations.

**SecServ**
The server process hosting SecDB object databases.

**SecSync**
Synchronization mechanism for eventual consistency across SecDB rings.

**SFI (Single Feature Importance)**
Lopez de Prado method evaluating each feature independently. Avoids multicollinearity issues but misses interactions.

**Short Interest**
Total shares sold short. Muravyev-Pearson-Pollet (2022): IVS signals partly proxy for borrow fees. Must control for this.

**Smirk (Volatility Smirk)**
Asymmetry in IV across strikes. 25-delta smirk predicts single-stock returns (Xing-Zhang-Zhao 2010 JFQA). Relevant primarily to Project 3/4.

**Stationarity**
Property of unchanging statistical properties over time. Most ML models assume it. Achieved via differencing or fractional differentiation.

**Statistical Arbitrage (Stat Arb)**
Trading mean-reversion of factor residuals. Related to Project 4 fallback.

**Stress Test / Stress Scenario**
Hypothetical adverse scenarios for risk evaluation. SecDB computes these nightly. Scenario P&L features are derived from these.

**Survivorship Bias**
Error of only analyzing surviving entities. Mitigated by point-in-time constituent data.

**SVI (Stochastic Volatility Inspired)**
Parametric IV smile model (Gatheral 2004). SVI residuals are potential demand-pressure signals in Project 3.

## T

**t-Statistic**
Test statistic for coefficient significance. Harvey-Liu-Zhu (2016 RFS) argue new factors need t > 3 given 316+ already tested.

**Term Structure**
How a variable changes across horizons. Yield curve, vol term structure. Nelson-Siegel level/slope/curvature are features.

**Theta**
Option time decay (∂P/∂t). Not directly a feature in this project.

## V

**Vanna**
Cross-Greek: sensitivity of delta to vol changes (∂²P/∂S∂σ). Aggregate dealer vanna drives FOMC/CPI-day responses. Feature in Project 2.

**Variance Risk Premium (VRP)**
IV² minus RV². Predicts >15% of quarterly SPX returns (Bollerslev-Tauchen-Zhou 2009). Publicly computable — no SecDB advantage.

**Vega**
Sensitivity of option price to vol changes. Aggregate dealer vega = firm's vol exposure. Feature in Project 2.

**Volga (Vomma)**
Second derivative of option price w.r.t. vol (∂²P/∂σ²). Vol-of-vol sensitivity. Feature in Project 2.

**Volatility Surface**
See Implied Volatility Surface.

## W

**Weights & Biases (W&B)**
Cloud ML experiment tracking platform. Alternative to MLflow.

## X

**XGBoost**
Extreme Gradient Boosting (Chen-Guestrin 2016). Along with LightGBM and CatBoost, a Tier 1 method. LightGBM generally preferred for speed.
