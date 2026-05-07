# Deep Research Prompt: ML for Realized Volatility Forecasting

## Role

You are a research assistant helping me scope, design, and source material for an internship project at Goldman Sachs (Engineering division, quant dev). The project brief, stated broadly, is: use machine learning to improve the estimation or forecasting of realized volatility across asset classes, using publicly available market data (prices, volumes, options surfaces, order book data where available). My deliverable is a presentation at the end of the internship. Your job is to do exhaustive, high-quality web research and return:

1. A landscape survey of what approaches, techniques, and prior art exist for ML-based realized volatility estimation and forecasting -- so I can make an informed choice about which direction to take.
2. A curated, annotated bibliography of the best resources (papers, blog posts, talks, repos, textbooks) for each relevant sub-topic.
3. Concrete project-direction suggestions -- 3-5 well-scoped project ideas that would be feasible in an internship timeframe (~10-12 weeks), impressive to a trading floor audience, and genuinely useful rather than toy.

## Who I am

- Goldman Sachs quant dev intern, Engineering division. I sit near traders, strats, and quant researchers and need to produce something they would find credible and useful.
- Strong computer-science background: Python fluent, comfortable with C++ and Java, solid on data structures, algorithms, systems, and ML fundamentals (deep learning, classical ML, time-series methods). I have completed university coursework in deep learning and NLP at Imperial College London (MEng CS).
- Strong mathematical background: linear algebra, probability, statistics, stochastic processes, optimisation, real analysis at undergraduate level.
- Working knowledge of trading and markets -- I understand order books, market microstructure basics, options Greeks, market-making theory, stat-arb concepts, and have competed in algorithmic trading competitions (IMC Prosperity). I am not a domain expert but I am not starting from zero on finance.
- I have access to Goldman Sachs internal infrastructure but the project should not depend on proprietary data. I want to use publicly available or widely accessible market data (exchange data, options data, FRED, etc.) so the work is reproducible and avoids entitlement issues.

## What I need from you

### Part 1 -- Landscape survey: "What is the state of the art in realized volatility estimation and forecasting?"

Map out the space of what people have tried, what has worked, and what is known to be hard. Specifically:

#### A. Realized volatility -- definitions, estimators, and the estimation problem

- The evolution of RV estimators: from simple sum-of-squared-returns to modern approaches. Cover at minimum:
  - Classical realized variance (Andersen & Bollerslev 1998, Barndorff-Nielsen & Shephard 2002)
  - Bipower variation (BV) and its role in separating continuous and jump components
  - Kernel-based estimators (realized kernel -- Barndorff-Nielsen, Hansen, Lunde, Shephard 2008)
  - Multi-scale realized volatility (Zhang, Mykland, Ait-Sahalia 2005) and the two-scale/multi-scale estimators
  - Pre-averaging approaches (Jacod, Li, Mykland, Podolskij, Vetter 2009)
  - Subsampling methods and their efficiency properties
  - The Fourier method of estimating integrated volatility (Malliavin & Mancino)
- The core challenge: microstructure noise. What causes it (bid-ask bounce, discrete prices, latency), why naive high-frequency RV is biased, and the variance-bias tradeoff in sampling frequency.
- Jump detection and separation: how to disentangle continuous volatility from jumps (Barndorff-Nielsen & Shephard jump tests, Lee-Mykland test, Ait-Sahalia & Jacod)
- What does "more accurate" mean in this context? Metrics: QLIKE, MSE, MAE, Mincer-Zarnowitz regressions, model confidence sets (Hansen, Lunde, Nason 2011). Why QLIKE is preferred over MSE for volatility forecasting evaluation.

#### B. Volatility forecasting -- econometric baselines that ML must beat

- The HAR-RV model (Corsi 2009) and why it is the benchmark everyone compares against. Its extensions:
  - HAR-RV-J (adding jump components)
  - HAR-RV-CJ (continuous vs. jump decomposition)
  - HARQ (Bollerslev, Patton, Quaedvlieg 2016 -- measurement-error-adjusted HAR)
  - HAR with leverage effects, signed returns, semi-variances
  - HEAVY models (Shephard & Sheppard 2010)
- GARCH family for lower-frequency settings: GARCH, EGARCH, GJR-GARCH, FIGARCH (long memory), Realized GARCH (Hansen, Huang, Shek 2012)
- Stochastic volatility models: Heston, rough volatility (Gatheral, Jaisson, Rosenbaum 2018 -- this is crucial), fractional Brownian motion approaches
- The rough volatility revolution: evidence that log-volatility behaves like fBM with H ~ 0.1, implications for forecasting, the roughness debate (Cont & Das 2024, Fukasawa et al. 2022)
- What is the current consensus on forecast horizons? (Intraday vs. daily vs. weekly vs. monthly -- where do different methods shine?)

#### C. ML methods for volatility -- what actually works

Survey of which ML methods have been applied to vol estimation/forecasting and with what results. Distinguish between: methods with rigorous published evidence, practitioner reports, and theoretical proposals without strong empirical backing.

Cover at minimum:

- Tree-based methods for tabular volatility features -- often the quiet winners:
  - Ensemble methods: XGBoost, LightGBM, Random Forests, CatBoost -- standard workhorses. How do they compare to HAR on vol?
  - **Optimal decision trees** -- a rapidly maturing field that has moved from NP-hard intractability to practical algorithms. The key insight: for many tabular problems, a single interpretable tree can match ensemble accuracy. Cover:
    - GOSDT (Lin et al. 2020) -- provably optimal sparse decision trees via dynamic programming with guessing from black-box models
    - MurTree (Demirovic et al. 2022) -- state-of-the-art exact solver using specialized depth-2 subtree technique
    - DL8.5 (Aglin et al. 2020) -- itemset mining + branch-and-bound
    - Blossom (Demirovic et al. 2023) -- anytime algorithm with essentially no overhead vs. heuristics
    - STreeD (van der Linden et al. 2023-24) -- generic DP framework with necessary and sufficient conditions for separable objectives; extends to optimal regression trees and survival trees
    - **SPLIT** (Babbar, McTavish, Rudin, Seltzer 2025, ICML 2025 Oral) -- "Near Optimal Decision Trees in a SPLIT Second." Hybrid: optimal near root, greedy near leaves. Orders of magnitude faster than fully optimal methods with negligible accuracy loss. This is the current speed frontier.
  - **Rashomon sets for decision trees** -- enumerating all near-optimal models, not just one. This is potentially the most important conceptual advance for interpretable ML:
    - Breiman 2001 coins the Rashomon effect: many models give similar error but wildly different explanations
    - Semenova, Rudin, Parr 2022 -- Rashomon ratio theory: when many good models exist, simpler ones are likely among them
    - TreeFARMS (Xin et al. 2022, NeurIPS Oral) -- first complete enumeration of Rashomon sets for decision trees
    - Dong & Rudin 2020 -- Variable Importance Clouds: mapping feature importance across every model in the Rashomon set. Shows single-model importance can be misleading.
    - **LicketyRESPLIT** (Heile, Babbar, McTavish, Rudin 2025) -- "Efficient Rashomon Set Approximation for Decision Trees." Polynomial-time, 100x less memory than TreeFARMS, recovers nearly full Rashomon set. Makes Rashomon analysis practical at scale.
    - SORTeD (Arslan et al. 2025, NeurIPS Spotlight) -- enumerates Rashomon trees in order of objective value, 100x faster than TreeFARMS
    - Rudin et al. 2024 (ICML position paper) -- "Amazing Things Come From Having Many Good Models." The manifesto for why Rashomon sets matter.
  - The key question for vol: can a single optimal decision tree match or approach XGBoost/LightGBM on tabular RV features? If the Rashomon set is large, what does that tell us about which volatility features are genuinely load-bearing vs. interchangeable?
- Recurrent networks (LSTMs, GRUs) for sequential vol forecasting -- widely tried, mixed results vs. HAR
- Temporal convolutional networks (TCN, WaveNet-style architectures) -- do they capture long memory in vol?
- Transformers and attention mechanisms for time-series volatility -- recent explosion of papers, but do they actually beat simpler models on vol?
- N-BEATS, N-HiTS, TiDE, TSMixer, PatchTST -- the modern time-series forecasting architectures. Have any been applied to vol specifically?
- Neural SDEs and neural ODEs -- continuous-time neural network approaches to volatility modeling (Kidger, Morrill, et al.)
- Gaussian processes for volatility -- uncertainty quantification angle
- Reservoir computing / echo state networks -- niche but some vol results
- Autoencoders and VAEs -- latent volatility state extraction
- Hybrid models -- combining econometric structure (HAR, GARCH) with ML (e.g., neural network residuals on top of HAR, attention-augmented HAR)
- For each method class: what features does it use? What forecast horizon? Does it beat HAR-RV? By how much? On which assets? What are the failure modes?
- The key question: does any ML method consistently and significantly outperform HAR-RV for realized volatility forecasting? Be honest -- the answer may be "barely" or "only in certain regimes."

#### D. Feature engineering for volatility prediction

This is critical. What features beyond past RV are predictive of future volatility? Think:

- Intraday patterns: intraday vol signatures, time-of-day effects, overnight vs. intraday decomposition
- Options-implied information: implied volatility, IV-RV spread (variance risk premium), implied vol surface features (skew, term structure, smile shape), VIX and its term structure
- Microstructure features: bid-ask spreads, order flow imbalance, trade arrival rates, volume profiles, Amihud illiquidity
- Cross-asset features: what do rates vol, FX vol, and credit spreads tell you about equity vol? Volatility spillovers across asset classes
- Signed volatility components: realized semi-variance (Barndorff-Nielsen, Kinnebrock, Shephard 2010), good vs. bad volatility, downside vs. upside realized vol
- Higher moments: realized skewness, realized kurtosis as predictors
- Volume and turnover: volume-volatility relationship (Tauchen-Pitts, MDH), abnormal volume
- Leverage effect features: asymmetric response of vol to returns
- Long memory features: fractional differencing of vol series (Lopez de Prado AFML Ch. 5)
- Calendar and event features: earnings, FOMC, macro releases, expiration dates
- Sentiment / text features: news sentiment, earnings call NLP (probably out of scope, but mention if strong results exist)
- **Rashomon-aware feature analysis**: If we construct the Rashomon set of near-optimal trees for vol forecasting, which features appear in all good models (truly important) vs. which are interchangeable (Variable Importance Clouds framework)? This is a fundamentally different question from SHAP/permutation importance on a single model and may reveal that the vol feature space has significant redundancy -- many combinations of features yield equivalent forecasting power.
- Any papers specifically on feature importance for vol forecasting -- what features matter most empirically?

#### E. The variance risk premium and vol-of-vol

- The variance risk premium (VRP): IV^2 - RV^2 as a signal. Bollerslev, Tauchen, Zhou (2009). Is it predictive of returns, of future vol, or both?
- Vol-of-vol: estimating the volatility of volatility. VVIX. Why it matters for options trading.
- Rough vol and the VRP -- how does the roughness of vol affect the VRP and its predictability?
- Any ML approaches to VRP estimation or VRP-based forecasting.

#### F. Multi-asset and cross-asset volatility

- Realized covariance and correlation estimation -- the multivariate extension of RV. Composite realized kernel, multivariate realized kernel, DCC models.
- Volatility spillovers and connectedness: Diebold-Yilmaz framework, network approaches to vol transmission
- Cross-asset vol forecasting: does equity vol predict rates vol? Does FX vol predict commodity vol? What are the lead-lag relationships?
- Factor models for volatility: can you decompose realized vol into systematic and idiosyncratic components?

#### G. Avoiding the graveyard -- what doesn't work and why

- The known failure modes of ML in finance applied specifically to volatility:
  - Overfitting on vol regimes that don't repeat
  - Non-stationarity of the vol process
  - The roughness problem -- long memory makes train/test splits tricky
  - Lookahead bias in vol feature construction (especially with smoothed estimators)
  - The "HAR is surprisingly hard to beat" phenomenon
- Lopez de Prado's validation framework applied to vol: purged K-fold CV with embargo, triple barrier labeling (less relevant for vol forecasting but meta-labeling may apply), Deflated Sharpe Ratio for vol-timing strategies
- How do you evaluate a vol forecast honestly? Out-of-sample R^2, QLIKE, model confidence sets, Diebold-Mariano tests
- What does "better" mean practically? A 2% improvement in QLIKE -- does a trader care? When does a better vol forecast translate into real PnL?

#### H. Practical applications -- why traders care about better vol estimates

- Options pricing and market-making: better vol -> better theoretical values -> tighter spreads, fewer adverse fills
- Risk management: more accurate VaR, expected shortfall, stress testing
- Volatility trading: variance swaps, vol swaps, straddles/strangles, dispersion trading -- all depend on vol forecasts
- Portfolio construction: vol-targeting strategies, risk parity, minimum variance portfolios
- Execution: optimal execution algorithms that adapt to vol conditions
- Which of these applications would be most impressive and relevant to a GS trading floor?

### Part 2 -- Concrete project direction suggestions

Based on the landscape survey, propose 3-5 well-scoped project directions I could pursue. For each:

- Title and one-line pitch (what I'd put on a slide).
- What it does (2-3 sentences).
- Why it's interesting to a trading floor (what problem does it solve or what edge does it give?).
- Data requirements (what publicly available data would I need? Be specific -- TAQ, LOBSTER, Oxford-Man RV library, OptionMetrics, FRED, etc.).
- ML methods involved (be specific -- not just "deep learning" but which architecture and why).
- Econometric baseline (what non-ML model must the ML approach beat to be credible?).
- Feasibility in 10-12 weeks -- honest assessment. Can I get a credible proof-of-concept, or is this a multi-quarter project?
- Risk factors (data access, compute, domain knowledge gaps).
- "Wow factor" -- how impressive would this be in a final presentation if executed well?
- Novelty assessment -- is this incremental (HAR + neural net, done 50 times) or does it bring a genuinely new angle?

Aim for a mix: one safer/more conventional project, one ambitious/novel project, and one or two in between. Prioritize ideas where the ML adds genuine value over the econometric baseline, not just marginal QLIKE improvements that don't matter in practice.

Consider whether one project direction should involve using Rashomon sets of optimal decision trees for volatility feature importance analysis -- i.e., rather than forecasting vol with a single model, enumerate all near-optimal interpretable trees and analyze which features are truly essential vs. interchangeable across the Rashomon set. This would be novel (no one has applied Rashomon sets to financial time-series), intellectually substantial, and directly useful to a trading desk (understanding *which* features drive vol forecasts and *how robust* those feature choices are). Assess feasibility given the computational scaling of LicketyRESPLIT/SORTeD on typical vol forecasting dataset sizes.

### Part 3 -- Annotated bibliography

For each resource you reference, include:

- Title, author(s), year, format (paper / book / blog / talk / repo / course), URL, cost.
- What it covers (2-4 sentences).
- Relevance to my project (1-2 sentences on why I should read this specifically).
- Quality tag: essential / recommended / optional / skim-for-ideas.

## What "deep research" means for this task

Go well beyond the first page of Google. Specifically search across:

- **Academic**: arXiv (q-fin, stat.ML, cs.LG), SSRN, Journal of Financial Economics, Journal of Econometrics, Econometrica, Journal of the American Statistical Association, Quantitative Finance, Journal of Financial Econometrics, Review of Financial Studies, Bernoulli.
- **Practitioner**: blog posts by quants at top firms, talks from QuantMinds/RiskMinds/IAQF/SoFiE conferences, Quantocracy aggregator, Wilmott forums, Quant Stack Exchange.
- **Industry**: Goldman Sachs research publications, Two Sigma / Citadel / DE Shaw / AQR / Man AHL research publications, JP Morgan quantitative research, Barclays quantitative research.
- **Key researchers to specifically search for**: Torben Andersen, Tim Bollerslev, Neil Shephard, Per Mykland, Yacine Ait-Sahalia, Jim Gatheral, Mathieu Rosenbaum, Andrew Patton, Kevin Sheppard, Dacheng Xiu, Bryan Kelly, Viktor Todorov, Jean Jacod, Almut Veraart, Mikko Pakkanen, Rama Cont, Cynthia Rudin, Emir Demirovic, Margo Seltzer, Jacobus van der Linden, Varun Babbar, Hayden McTavish, Lesia Semenova, Chudi Zhong.
- **Code**: GitHub repos for realized vol estimation, arch (Kevin Sheppard), roughvol, Oxford-Man Institute Realized Library, statsmodels, any neural SDE libraries, neuralforecast, tsai. Optimal decision tree libraries: GOSDT (PyPI), PyDL8.5, pystreed (github.com/AlgTUDelft/pystreed), TreeFARMS (github.com/ubc-systopia/treeFarms), SPLIT (github.com/VarunBabbar/SPLIT-ICML).
- **Community**: Reddit (r/quant, r/algotrading), Hacker News, Twitter/X threads from known practitioners and researchers.

## Quality bar and filtering rules

- No hype. If a resource claims ML can trivially predict volatility, skip it. I want honest, calibrated material.
- Prefer rigorous work over incremental "we beat HAR by 0.5%" papers. I want papers that bring new ideas, not just new architectures on the same benchmark.
- Prefer practitioners over content marketers. People who have actually built vol models at real firms over people selling courses.
- Academic papers are the backbone here -- this is a more established academic field than signal discovery, so lean heavily on the econometrics and statistics literature.
- Be honest about what ML adds vs. what it doesn't. The vol forecasting literature has a replication crisis of its own -- many papers claim to beat HAR but use different evaluation protocols, different data periods, or in-sample tuning disguised as out-of-sample testing.
- No affiliate-spam listicles, no "predict stock volatility with LSTM in 10 lines" tutorials.
- When two resources substantially overlap, pick the better one and say why.

## Output format

1. **Executive summary** (<=400 words) -- the landscape in a nutshell: what's promising, what's overhyped, and where the opportunity lies for an intern project.
2. **Landscape survey** (sections A-H above) -- the main body. Be thorough but curated.
3. **Project direction proposals** (3-5 concrete ideas as specified above).
4. **Annotated bibliography** -- grouped by topic, with tags.
5. **Gaps and honest unknowns** -- where public information runs out, what I should ask my manager/mentor about early.
6. **Raw source log** -- every URL consulted, even ones that didn't make the cut.

## Scope and emphasis

- **Spend heavily on**: sections C (ML methods -- what actually beats HAR?), D (feature engineering for vol), and B (econometric baselines that define the bar). These determine whether the project is novel or redundant.
- **Spend moderately on**: sections A (RV estimators -- foundational but well-trodden), E (VRP), F (cross-asset vol), and the project proposals.
- **Spend lightly on**: section G (pitfalls -- important but I'm already familiar with Lopez de Prado's framework) and H (applications -- useful framing but I understand why traders care about vol).
- Aim for a document that is genuinely useful as a project-scoping reference, not padded with obvious material. I would rather have 25 excellent resources than 150 mediocre ones.
