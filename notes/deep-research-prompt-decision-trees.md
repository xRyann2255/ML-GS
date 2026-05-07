# Deep Research Prompt: State of the Art in Decision Trees

## Role

You are a research assistant helping me build a comprehensive understanding of the current state of the art in decision tree algorithms. I am a quant dev intern at Goldman Sachs building an ML model for realized volatility forecasting on tabular financial data. I need to understand what has happened in the decision tree world in the last 5-10 years because the field has undergone a quiet revolution -- from "decision trees are weak learners you ensemble away" to "a single optimal tree can match ensemble accuracy on many tabular problems." I want to know what exists, what works, what scales, and what I should consider using.

My background: MEng CS from Imperial College London, strong in algorithms, optimization, ML fundamentals, and mathematical foundations (linear algebra, probability, statistics, stochastic processes, optimization). I am comfortable reading algorithmic papers with proofs. I do not need hand-holding on basics -- I need depth.

## What I need from you

Do exhaustive, high-quality web research and return a complete landscape of modern decision tree methods. This is not limited to finance -- I want the full picture of the field, because methods developed for healthcare interpretability or fairness-constrained classification may be exactly what I need for a financial application.

### Part 1 -- Landscape Survey

#### A. The optimal decision tree revolution

The classical view: learning an optimal decision tree is NP-hard (Hyafil & Rivest 1976), so we use greedy heuristics (CART, C4.5, ID3) and accept suboptimality, or we ensemble many weak trees (Random Forest, boosting). The modern view: practical algorithms now find provably optimal trees for realistic dataset sizes. Map out how we got here.

- **The greedy baseline and its limitations**: CART (Breiman et al. 1984), C4.5 (Quinlan 1993). Why greedy splitting is suboptimal -- the classic examples where greedy fails. The myopia problem: each split is locally optimal but globally suboptimal.
- **Early exact methods**: Why brute-force enumeration is intractable. Early constraint programming and integer programming approaches. BinOCT (Verwer & Zhang 2019). What made these too slow for practical use?
- **The modern optimal tree algorithms** -- cover each in detail (algorithm idea, complexity, scaling limits, what it optimizes, available code):
  - OSDT (Hu, Rudin, Seltzer 2019, NeurIPS) -- the breakthrough. Optimal sparse decision trees for binary features. Analytical bounds + custom bit-vector data structures to prune the search space.
  - GOSDT (Lin et al. 2020, ICML) -- generalizes OSDT to continuous features, imbalanced data, F-score/AUC objectives. Uses a black-box model to "guess" and accelerate search.
  - DL8.5 (Aglin, Nijssen, Schaus 2020, AAAI) -- itemset mining meets branch-and-bound. How does the caching strategy work? How does it compare to GOSDT in speed and scalability?
  - MurTree (Demirovic et al. 2022, JMLR) -- dynamic programming with a specialized depth-2 subtree technique. State-of-the-art exact solver at publication. Supports depth and node count constraints.
  - Blossom (Demirovic, Hebrard, Jean 2023, ICML) -- anytime algorithm. Depth-first expansion avoids unbalanced intermediate trees. Scales to deeper trees than prior exact methods. What does "anytime" buy you in practice?
  - STreeD (van der Linden, de Weerdt, Demirovic 2023-24, NeurIPS/ICML/AAAI) -- the unifying framework. Necessary and sufficient conditions for when DP works on tree objectives ("separable" objectives). Extends to regression trees, survival trees, fair trees. How general is the separability condition?
  - **SPLIT** (Babbar, McTavish, Rudin, Seltzer 2025, ICML Oral) -- "Near Optimal Decision Trees in a SPLIT Second." The hybrid insight: be optimal near the root (where decisions matter most), greedy near the leaves (where the exponential blowup lives). Orders of magnitude faster with negligible accuracy loss. What are the theoretical guarantees? When does near-optimal diverge from optimal?
  - Any other recent optimal tree methods I may have missed -- search thoroughly for 2024-2025 papers.
- **Scaling frontier**: What are the practical limits today? How large can the dataset be (rows, features) before these methods become intractable? How deep can the tree be? What is the current computational bottleneck? How do these compare to training a single XGBoost model in wall-clock time?
- **Optimal vs. greedy in practice**: On standard benchmarks (UCI, OpenML, Kaggle tabular), how often does the optimal tree match or beat the greedy tree? By how much? Are there problem types where optimality matters more?

#### B. Rashomon sets -- the multiplicity of good models

This may be the most important conceptual development in interpretable ML. Instead of returning one model, return the set of all models within epsilon of optimal. Cover thoroughly:

- **The Rashomon effect**: Breiman 2001 ("Statistical Modeling: The Two Cultures") coins the term. Many models give similar predictive accuracy but wildly different structure and interpretation. Why this matters for any application where you care about *why* the model predicts what it predicts.
- **Rashomon ratio theory**: Semenova, Rudin, Parr 2022 (ACM FAccT) -- "On the Existence of Simpler Machine Learning Models." When the Rashomon set is large, simpler models are likely to exist within it. What determines the size of the Rashomon set? What properties of the data/problem make it large vs. small?
- **TreeFARMS** (Xin et al. 2022, NeurIPS Oral) -- first complete enumeration of the Rashomon set for sparse decision trees. How does the data structure work? What can you do once you have the full set? How does it scale?
- **Variable Importance Clouds** (Dong & Rudin 2020, Nature Machine Intelligence) -- mapping feature importance across every model in the Rashomon set. Why single-model feature importance (SHAP, permutation) can be misleading when the Rashomon set is large. What does a VIC look like in practice?
- **LicketyRESPLIT** (Heile, Babbar, McTavish, Rudin 2025) -- polynomial-time Rashomon set approximation. 100x less memory than TreeFARMS. How close is the approximation to the full set? When is approximation good enough?
- **SORTeD** (Arslan et al. 2025, NeurIPS Spotlight) -- anytime enumeration of Rashomon trees in order of objective value. 100x faster than TreeFARMS. Works with any separable, totally ordered objective. What does ordered enumeration enable that unordered enumeration doesn't?
- **Rudin et al. 2024 ICML position paper** -- "Amazing Things Come From Having Many Good Models." The six implications: existence of simple models, flexibility for constraints, uncertainty quantification, reliable variable importance, algorithm choice, public policy. Which of these translate to a financial/forecasting context?
- **Rashomon sets beyond trees**: Has anyone computed Rashomon sets for other model classes (linear models, rule lists, GAMs)? How do tree Rashomon sets compare?
- **Practical applications of Rashomon sets**: Where have people actually used this? Healthcare, criminal justice, credit scoring? What did the Rashomon analysis reveal that a single model would have missed?

#### C. Ensemble methods -- the incumbent to beat

Since optimal trees aim to replace or complement ensembles, understand what they're competing against:

- **Random Forests** (Breiman 2001): the original. Bagging + random feature subsets. Why it works (bias-variance decomposition, decorrelation). Known strengths: robust, hard to overfit, good OOB estimates. Known weaknesses: not great on high-cardinality categorical features, slow inference, not interpretable.
- **Gradient Boosting**: XGBoost (Chen & Guestrin 2016), LightGBM (Ke et al. 2017), CatBoost (Prokhorenkova et al. 2018). What are the actual algorithmic differences that matter in practice (histogram-based splitting, GOSS, ordered boosting, native categorical handling)?
- **The "tabular data" result**: Grinsztajn, Oyallon, Varoquaux 2022 -- "Why do tree-based models still outperform deep learning on typical tabular data?" What properties of tabular data favor trees? Irregular feature distributions, uninformative features, heterogeneous feature types.
- **Ensemble distillation**: Can you distill an ensemble into a single interpretable tree without losing too much accuracy? Born-again trees (Breiman & Shang 1996, revived recently). Knowledge distillation from XGBoost to optimal tree.
- **The accuracy-interpretability tradeoff -- is it real?** Rudin's central claim: for structured/tabular data, the tradeoff is often illusory. A single well-optimized tree or small tree can match ensemble accuracy. What is the empirical evidence for and against this claim? On which dataset types does it hold, and where does it break down?

#### D. Decision trees for regression and continuous targets

Most optimal tree literature focuses on classification. My use case is regression (forecasting a continuous quantity -- realized volatility). What exists?

- **Optimal regression trees**: STreeD extensions to regression (van der Linden et al., ICML 2024). What objective do they optimize? MSE? How does the DP decomposition work for continuous targets?
- **CART regression trees**: the standard. Mean prediction in leaf nodes. How suboptimal are greedy regression trees compared to optimal ones?
- **Model trees**: trees with linear models in the leaves (M5, Cubist). Do these exist in optimal-tree form?
- **Regression-specific Rashomon sets**: Can you enumerate near-optimal regression trees? What does the Rashomon set look like when the objective is MSE or MAE rather than misclassification?
- **Quantile regression trees**: predicting quantiles rather than means. Relevant for risk-sensitive applications. Any optimal versions?
- **Time-series-specific tree methods**: Are there tree algorithms designed for temporal data? Lag feature construction, temporal splitting constraints, etc.

#### E. Interpretability, explainability, and why it matters

- **Inherent vs. post-hoc interpretability**: Why Rudin argues we should prefer inherently interpretable models (like optimal trees) over post-hoc explanations (SHAP, LIME) of black boxes. The "Rashomon effect" argument: SHAP values are model-specific, but if many models are equally good, which model's SHAP values should you trust?
- **Rudin 2019** -- "Stop Explaining Black Box Machine Learning Models for High Stakes Decisions and Use Interpretable Models Instead" (Nature Machine Intelligence). The foundational argument.
- **Practical interpretability of trees**: What tree depth/size is actually interpretable to a human? 3-5 levels? 10 leaves? What does the research say about cognitive limits?
- **Monotonicity constraints**: Can you enforce that the tree's prediction is monotonically increasing/decreasing in a feature? Important for financial applications where domain knowledge imposes ordering constraints (e.g., higher implied vol should predict higher realized vol, all else equal). Do optimal tree algorithms support this?
- **Fairness constraints**: Building trees that satisfy group fairness criteria. FairTree, fair STreeD. Not directly relevant to my application but shows the flexibility of the framework.

#### F. Computational and implementation landscape

- **Available libraries and their maturity**:
  - GOSDT -- PyPI package, scikit-learn compatible. How production-ready is it?
  - PyDL8.5 -- scikit-learn compatible. Still maintained?
  - pystreed (github.com/AlgTUDelft/pystreed) -- the STreeD implementation. What objectives does it support?
  - TreeFARMS (github.com/ubc-systopia/treeFarms) -- Rashomon set enumeration.
  - SPLIT (github.com/VarunBabbar/SPLIT-ICML) -- the fastest near-optimal solver.
  - scikit-learn DecisionTreeClassifier/Regressor -- the greedy baseline.
  - interpretML -- Microsoft's library. Does it include optimal trees?
  - dtreeviz, supertree -- visualization tools.
- **Language and performance**: Most are Python wrappers around C/C++ cores. What are the actual performance characteristics? Can they handle 100K rows? 1M rows? 100 features?
- **Integration with standard ML pipelines**: Do these work with scikit-learn cross-validation, pipelines, GridSearchCV? Can I use them as drop-in replacements for sklearn trees?
- **GPU acceleration**: Any of these methods GPU-accelerated? Likely not, but check.

#### G. Theoretical foundations

- **Sample complexity**: How many samples does an optimal tree need vs. a greedy tree? Does optimality help or hurt generalization?
- **Approximation guarantees**: SPLIT gives near-optimal. What are the formal bounds? How does the gap scale with tree depth?
- **Connections to other fields**: Optimal trees use DP, branch-and-bound, constraint programming, SAT solvers, mixed-integer programming. Which formulation works best for which problem structure?
- **NP-hardness results**: What exactly is NP-hard? Finding the minimum-size tree? The minimum-error tree at fixed depth? What parameterized complexity results exist (FPT in depth, number of features, etc.)?
- **Generalization bounds for trees**: VC dimension, Rademacher complexity of tree hypothesis classes. How do sparsity constraints (fewer leaves, shallower depth) affect generalization guarantees?

#### H. The frontier -- what's next (2025 and beyond)

- **Scaling to larger datasets**: What are the active research directions for making optimal trees work on datasets with millions of rows?
- **Online/streaming optimal trees**: Can you update an optimal tree incrementally as new data arrives? Important for financial applications where data is non-stationary.
- **Optimal tree ensembles**: Can you build an ensemble where each tree is individually optimal? Would this give you the best of both worlds (ensemble accuracy + per-tree interpretability)?
- **Differentiable decision trees**: Soft/smooth trees that can be trained with gradient descent. TAO (Tree Alternating Optimization, Carreira-Perpinan & Tavallali 2018). How do these relate to optimal trees?
- **Neural-tree hybrids**: NODE (Neural Oblivious Decision Ensembles, Popov et al. 2020), TabNet (Arik & Pfister 2021). Are these actually trees or just tree-inspired neural architectures?
- **Rashomon sets + causal inference**: Using model multiplicity to reason about causal structure. Any work here?
- **Open problems**: What unsolved problems would be most impactful if cracked?

### Part 2 -- Applicability assessment for tabular financial time-series

Based on the landscape survey, assess:

1. **Which optimal tree methods could I realistically use for a realized volatility forecasting model?** Consider: my dataset is ~5000-20000 daily observations, 20-80 engineered features (continuous), regression target. Which algorithms handle this scale and problem type?
2. **Where would Rashomon set analysis add genuine value over standard feature importance?** I have a feature space where many features are correlated (different RV estimators, overlapping window lengths, implied vs. realized measures). The Rashomon set might reveal which features are truly distinct vs. which are interchangeable.
3. **What is the realistic accuracy cost of using an optimal tree vs. XGBoost/LightGBM on this kind of data?** Is the interpretability-accuracy tradeoff real for financial tabular regression, or can a well-optimized tree close the gap?
4. **What would a "tree-based interpretable vol forecasting" pipeline look like?** Feature engineering -> optimal regression tree (or small Rashomon set of trees) -> analysis of which features are essential -> comparison to ensemble baseline.
5. **What is novel here?** Has anyone applied optimal decision trees or Rashomon sets to financial time-series forecasting? If not, this could be a genuine contribution.

### Part 3 -- Annotated bibliography

For each resource you reference, include:

- Title, author(s), year, venue, format (paper / book / blog / talk / repo / course), URL.
- What it covers (2-4 sentences).
- Relevance to my use case (1-2 sentences).
- Quality tag: essential / recommended / optional / skim-for-ideas.

Group by topic:
1. Optimal decision tree algorithms
2. Rashomon sets and model multiplicity
3. Ensemble methods and the tabular data debate
4. Regression trees and continuous targets
5. Interpretability theory and practice
6. Software and implementations
7. Theoretical foundations
8. Applications (especially any financial or time-series)

## Search strategy

Go deep. Specifically search across:

- **Academic**: arXiv (cs.LG, cs.AI, stat.ML), NeurIPS / ICML / AAAI / ICLR / KDD / JMLR / Machine Learning journal proceedings 2019-2025, ACM FAccT, Nature Machine Intelligence.
- **Key researchers to specifically search for**: Cynthia Rudin, Emir Demirovic, Margo Seltzer, Jacobus van der Linden, Varun Babbar, Hayden McTavish, Lesia Semenova, Chudi Zhong, Rui Xin, Gauthier Aglin, Siegfried Nijssen, Pierre Schaus, Xiyang Hu, Jimmy Lin, Peter Stuckey, Jiayun Dong, Ronald Parr, Takuya Takagi, Elif Arslan, Marco Rinaldi, Mathijs de Weerdt.
- **Code**: GitHub repos for all mentioned libraries. Check stars, recent commits, open issues, documentation quality. Are these research prototypes or production-ready tools?
- **Talks and tutorials**: NeurIPS/ICML oral/spotlight presentations, Cynthia Rudin's talks (she gives excellent ones), workshop papers.
- **Blog posts and practitioner accounts**: Has anyone tried using GOSDT/MurTree/SPLIT in production? Any Kaggle notebooks comparing optimal trees to XGBoost?
- **Benchmarks**: OpenML benchmarks for tree methods. Any standardized comparisons across optimal tree algorithms?

## Quality bar

- Prefer published venue papers (NeurIPS, ICML, AAAI, JMLR) over arXiv-only.
- Prefer papers with available code over theory-only.
- Prefer empirical comparisons that include multiple algorithms on the same benchmarks over isolated evaluations.
- Include negative results -- papers that show optimal trees don't help, or that the Rashomon set is uninformative, are just as valuable as positive ones.
- No tutorial-level content. I want the research frontier, not "what is a decision tree."

## Output format

1. **Executive summary** (<=400 words) -- the state of optimal decision trees in a nutshell: what's mature, what's emerging, what's hype, and what's most relevant to my tabular regression use case.
2. **Landscape survey** (sections A-H above) -- thorough and curated.
3. **Applicability assessment** (Part 2 above) -- honest evaluation for my specific use case.
4. **Annotated bibliography** -- grouped by topic, with quality tags.
5. **Gaps and open questions** -- what the literature doesn't answer that I'd need to figure out empirically.
6. **Raw source log** -- every URL consulted.
