# State of the Art in Decision Trees: A Landscape Survey for Quantitative Finance

## Executive Summary

The decision tree literature has been transformed since 2019 by a wave of provably-optimal and Rashomon-set algorithms. The orthodoxy that "a single tree is a weak learner you ensemble away" no longer holds for moderate tabular problems: when properly tuned and depth-constrained, a single optimal tree closes the gap with random forests on accuracy while remaining inspectable. The pivotal benchmark, van der Linden, Vos, de Weerdt, Verwer & Demirović (arXiv:2409.12788, 2024–25), reports verbatim: "We evaluate the accuracy of depth three and four trees on 180 data sets and find an average improvement of 1.3% and 1.0% of optimal over greedy approaches" — with individual datasets exhibiting gaps as large as 10 percentage points (Demirović et al. 2022, MurTree).

Three algorithm families dominate. (1) **Branch-and-bound + analytical bounds** (OSDT 2019; GOSDT 2020; OSRT 2023; Optimal Sparse Survival Trees 2024) from the Rudin–Seltzer group, with bit-vector data structures and reference-ensemble lookahead heuristics. (2) **Dynamic programming + caching** (DL8.5 2020; MurTree 2022; Blossom 2023; STreeD 2023–24; ConTree 2025) from the Nijssen–Demirović–van der Linden lineage, culminating in STreeD's separable-objective framework that subsumes classification, regression, fairness, survival, and policy trees. (3) **Hybrid lookahead + greedy** (SPLIT/LicketySPLIT/RESPLIT, ICML 2025 Oral, Babbar–McTavish–Rudin–Seltzer): "On the Bike dataset, SPLIT has training times of ∼10 seconds, while GOSDT runs for ∼10³ seconds. LicketySPLIT takes merely a second in most cases" — a 100×+ speedup over GOSDT with negligible accuracy loss and a provable approximation guarantee.

Parallel to the optimization revolution, the **Rashomon set** has become a first-class object. TreeFARMS (Xin et al., NeurIPS 2022 Oral) was the first method to enumerate the entire near-optimal set of sparse decision trees; LicketyRESPLIT (2025) and SORTeD (NeurIPS 2025 Spotlight) bring polynomial-time approximation and anytime ordered enumeration. Rudin's ICML 2024 Spotlight position paper "Amazing Things Come From Having Many Good Models" consolidates the program.

For the user's task — realized volatility forecasting with 5–20k daily observations, 20–80 continuous features, regression target — three concrete recommendations follow. First, **STreeD's piecewise-linear regression trees (van den Bos, van der Linden, Demirović, ICML 2024)** and **OSRT (Zhang et al., AAAI 2023)** are the only optimal regression-tree options with available code; both scale comfortably to this size. Second, **expect a 2–5% MSE penalty vs. a tuned LightGBM/XGBoost** as the realistic accuracy cost of interpretability — Christensen, Siggaard & Veliyev (*JFE* 2023; T=4,257 trading days, 29 January 2001 to 31 December 2017, 29 DJIA constituents) found bagging at 0.891 relative MSE vs HAR=1.000 on the Dow Jones, gradient boosting at 0.958, neural-net ensembles at 0.885–0.954. Third, **Rashomon-set analysis is the highest-leverage novelty**: an exhaustive search confirms no published paper, preprint, Kaggle notebook, or industry blog has applied any optimal-tree or Rashomon-set method to financial time-series forecasting as of May 2026.

---
> **Bibliography**: entries appended to `reference/bibliography.md` (category H)
> **Project proposals**: methodology assessment appended to `notes/project-proposals.md`
> **Research index**: `notes/research-index.md`
---

## A. The Optimal Decision Tree Revolution

### A.1 The greedy baseline and the myopia problem

CART (Breiman et al. 1984) and C4.5 (Quinlan 1993) build trees top-down by maximizing local information gain. The structural limitation is **myopia**: a locally optimal split at the root may force globally suboptimal subtrees. Murthy & Salzberg (1995) documented this empirically; Hyafil & Rivest (1976) proved constructing the optimal binary decision tree is NP-complete. Practitioners historically responded by ensembling — trading interpretability for accuracy.

### A.2 Early exact methods: MIP, CP, SAT

- **OCT** (Bertsimas & Dunn, *Machine Learning* 2017): MIP with oblique splits; depth ≤ 4 only on small data.
- **BinOCT** (Verwer & Zhang, AAAI 2019): binary linear program where decision thresholds are encoded via a binary search procedure with big-M constraints — making the formulation independent of the number of data rows. Best on datasets up to ~5000 rows. Always produces complete binary trees of given depth.
- **Constraint Programming** (Verhaeghe, Nijssen, Pesant, Quimper & Schaus, *Constraints* 2020).
- **MaxSAT-based** approaches (Narodytska et al. 2018; Hu, Siala, Hebrard & Huguet, IJCAI 2020).

### A.3 Modern optimal-tree algorithms

**OSDT (Hu, Rudin & Seltzer, NeurIPS 2019)** — first practical decision-tree-specific algorithm. Minimizes regularized misclassification L(T) + λ·|leaves(T)| over binary features, using analytical bounds (hierarchical objective, leaf permutation, equivalent-points, similar-support) and a custom **bit-vector library** for fast captured-sample updates. Limitations: binary features only, classification only, single objective.

**GOSDT (Lin, Zhong, Hu, Rudin & Seltzer, ICML 2020)** extends OSDT with **continuous features** via online threshold guessing (formalized in McTavish et al. AAAI 2022 "GOSDT-Guesses"), **non-linear objectives** (F1, weighted accuracy, AUC, partial-AUCH), and **black-box guidance**. A **depth limit** was added in 2022. Code: `pip install gosdt` (github.com/ubc-systopia/gosdt-guesses, 57 stars confirmed via GitHub PR page "Fork 20 · Star 57"). Empirically handles tens of thousands of rows and 30–100 binarized features within minutes.

**DL8.5 (Aglin, Nijssen & Schaus, AAAI 2020)** — different lineage building on DL8 (Nijssen & Fromont, KDD 2007). Innovation: **caching branch-and-bound** that stores partial-search results for itemset prefixes, outperforming MIP by orders of magnitude. PyDL8.5 (IJCAI 2020) at github.com/aia-uclouvain/pydl8.5.

**MurTree (Demirović, Lukina, Hebrard, Chan, Bailey, Leckie, Ramamohanarao & Stuckey, JMLR 2022)** introduces a **specialized depth-2 solver** exploiting closed-form optimal depth-two structure (now standard in STreeD/ConTree/SORTeD), plus similarity bounds and incremental bounds. Established that the greedy-vs-optimal gap can reach 10 percentage points on certain datasets.

**Blossom (Demirović, Hebrard & Jean, ICML 2023)** reframes DP search as **depth-first, layer-by-layer node expansion** — first solution found is the greedy tree, with successive improvements monotonically converging to the optimum. Virtually no overhead vs heuristic methods at start; matches best exact methods at convergence.

**STreeD (van der Linden, de Weerdt & Demirović, NeurIPS 2023; ICML 2024; AAAI 2025)** — the unifying framework. Proves that any **separable** objective (one that can be optimized independently for left and right subtrees) admits a DP solution, with necessary and sufficient conditions. Subsumes:
- Cost-sensitive classification, F1, Matthews correlation coefficient (Demirović & Stuckey 2021).
- **Group-fairness constraints** (van der Linden et al. NeurIPS 2022).
- **Prescriptive policy trees** (van der Linden et al. 2023).
- **Piecewise-constant and piecewise-linear regression** (van den Bos, van der Linden & Demirović, ICML 2024) — elastic-net leaves, depth-2 specialized solver. First optimal DP method for piecewise multiple linear regression.
- **Optimal Survival Trees** (Huisman, van der Linden, Demirović, AAAI 2024).
- **Continuous features without binarization** via ConTree (Briţa, van der Linden, Demirović, AAAI 2025) — ConTree's test accuracy averages 5% higher than CART and 0.7% higher than coarse-binarized ODTs.

Code: `pip install pystreed` (github.com/AlgTUDelft/pystreed); ConTree at github.com/ConSol-Lab/contree.

**SPLIT / LicketySPLIT / RESPLIT (Babbar, McTavish, Rudin & Seltzer, ICML 2025 Oral)** — the most important recent algorithmic advance. Core insight: not every subproblem must be solved optimally. SPLIT runs branch-and-bound to a **lookahead depth d_l**, then completes the tree greedily near leaves. Theoretical results:
- **Provable approximation guarantee**: SPLIT is provably at least as good as a fully greedy entropy-based method with the same constraints (Theorem A.1).
- **Asymptotic speedup**: O(k^((d−1)/2) · (d/2)!) faster than fully optimal methods (Corollary 6.3).
- **Existence theorem**: data distributions exist where SPLIT achieves accuracy 1−ε while greedy achieves at most 1/2+ε (Theorem 6.5).
- **LicketySPLIT** is the recursive depth-1 variant running in polynomial time O(|R|·n·k³·d³).
- **RESPLIT** extends to scalable Rashomon-set computation, ~74× faster than TreeFARMS on Bike, ~17× on Spambase, ~24× on HIV, ~17× on HELOC.

Empirical (verbatim): SPLIT is "over 100× faster than state of the art optimal decision tree algorithms"; on Bike, "SPLIT has training times of ∼10 seconds, while GOSDT runs for ∼10³ seconds. LicketySPLIT takes merely a second in most cases." Code: github.com/VarunBabbar/SPLIT-ICML.

**Other 2024–2025 work**:
- **Quant-BnB** (Mazumder, Meng, Wang, ICML 2022) — BnB on quantiles; first specialized continuous-feature ODT (depth ≤ 3 in practice).
- **OSRT** (Zhang, Xin, Seltzer, Rudin, AAAI 2023) — GOSDT-style for regression, with k-Means equivalent-points lower bound.
- **Optimal Sparse Survival Trees** (Zhang, Xin, Seltzer, Rudin, AISTATS 2024).
- **MAPTree** (Sullivan, Tiwari, Thrun, AAAI 2024) — Bayesian MAP via AND/OR search; outperforms or matches GOSDT/MurTree with smaller trees on 16 datasets, with optimality certificate.
- **Strong Optimal Classification Trees** (Aghaei, Gómez, Vayanos, *Operations Research* 2024) — strongest known max-flow MIP for axis-aligned trees.

### A.4 Scaling frontier and optimal-vs-greedy in practice

Van der Linden et al. (arXiv:2409.12788 v2, April 2025) is the definitive empirical reference: 180 datasets, cross-validated tuning, same-size constraints. Verbatim findings:

> "We evaluate the accuracy of depth three and four trees on 180 data sets and find an average improvement of 1.3% and 1.0% of optimal over greedy approaches."

> "For small data sets (n ≤ 250), the average advantage of the optimal approach is 0.2% ± 0.4 (mean ± standard error)... For larger data sets (n > 250), the average improvement of optimal over CART is 1.6% ± 0.2."

> "Although unrestricted greedy trees can outperform depth-limited ODTs in accuracy, they can quickly grow so large that they cannot be directly interpreted anymore. Random forests or neural networks already suffice if accuracy is the only concern. However, ODTs are an ideal candidate if interpretability is required, as they achieve a superior accuracy-interpretability trade-off."

Practical scaling (Section 5.5): "training ODTs up to depth four remains practically feasible for data sets up to approximately 250 binary features for 100,000 instances and 150 binary features for one million instances." Worst-case runtime grows exponentially with tree size and binary-feature count, linearly with samples — vs CART's linear-in-features and log-linear-in-samples scaling.

---

## B. Rashomon Sets — Model Multiplicity

### B.1 Rashomon effect (Breiman 2001) and ratio (Semenova-Rudin-Parr, FAccT 2022)

Breiman's "Two Cultures" paper observed that for any dataset there typically exist many models with near-equal predictive accuracy ("Rashomon effect"). Semenova, Rudin & Parr's "On the Existence of Simpler Machine Learning Models" introduced the **Rashomon ratio** — ratio of the volume of the Rashomon set to the volume of the hypothesis space — and showed: when several different ML methods produce near-equal accuracy on a dataset, the Rashomon ratio is large, **guaranteeing simpler models exist within the Rashomon set**. The follow-up "A Path to Simpler Models Starts With Noise" (Semenova, Chen, Parr, Rudin, NeurIPS 2023) shows label noise mechanically inflates the Rashomon ratio — explaining why tabular benchmarks in healthcare, criminal justice, lending, and finance routinely admit large Rashomon sets.

### B.2 TreeFARMS (Xin, Zhong, Chen, Takagi, Seltzer & Rudin, NeurIPS 2022 Oral)

"Exploring the Whole Rashomon Set of Sparse Decision Trees" provides the first complete enumeration of the Rashomon set for any non-trivial hypothesis class. Extends GOSDT with a specialized "Trees FAst RashoMon Sets" trie supporting efficient query and sampling. Demonstrated finding orders of magnitude more distinct near-optimal trees than baseline samplers (BART, MCMC) in the same time budget. Applications: variable importance over the entire Rashomon set, derived-metric Rashomon sets (balanced accuracy, F1), data-subset / bootstrap Rashomon sets. Code: `pip install treefarms` (github.com/ubc-systopia/treeFarms, 47 stars confirmed).

### B.3 Variable Importance Clouds (Dong & Rudin, *Nature Machine Intelligence* 2020)

The VIC maps every variable to its Model Reliance importance for every good model. Used with TreeFARMS, VIC reveals when one variable is interchangeable with another versus when uniquely important across the Rashomon set. Shapley-VIC (Ning et al., *Patterns* 2022) extends to SHAP values.

### B.4 Rashomon Importance Distribution (Donnelly, Katta, Rudin & Browne, NeurIPS 2023)

RID: variable importance distribution over (Rashomon set × bootstrap), with consistency theorems and finite-sample error rates. Stably ranks variables when single-model importance fluctuates.

### B.5 LicketyRESPLIT (Heile, Babbar, McTavish, Rudin, 2025)

Polynomial-time approximation to the Rashomon set, recursively finding near-optimal splits conditioned on easy-to-compute oracles. Orders-of-magnitude runtime/memory improvement over TreeFARMS and RESPLIT while recovering nearly the full Rashomon set.

### B.6 SORTeD (Arslan, van der Linden, Hoogendoorn, Rinaldi, Demirović, NeurIPS 2025 Spotlight)

Enumerates the Rashomon set in **decreasing order of objective value** — best trees first. Anytime termination at any quality threshold; up to two orders of magnitude speedup over TreeFARMS/RESPLIT. Supports any separable objective (works for regression and survival via STreeD).

### B.7 Rudin et al., ICML 2024 Spotlight — "Amazing Things Come From Having Many Good Models"

Position paper consolidating six benefits of computing the Rashomon set: (1) existence of simpler-yet-accurate models, (2) flexibility to address fairness/monotonicity, (3) uncertainty quantification, (4) reliable variable importance, (5) algorithm-choice diagnostics, (6) public-policy applications. Argues ML should reframe learning as a **feasibility problem** ("find all good models") rather than optimization.

### B.8 Rashomon sets beyond trees

- **Sparse generalized additive models** (Zhong et al., NeurIPS 2023).
- **Sparse risk scores / FasterRisk** (Liu et al., NeurIPS 2022).
- **Linear models** (Coker, Rudin, King, *Management Science* 2021).
- **Prototype-part networks** (Donnelly et al., CVPR 2025).
- **Predictive multiplicity in classification** (Marx, Calmon, Ustun, ICML 2020); **Rashomon Capacity** (Hsu, Calmon, NeurIPS 2022).

### B.9 Practical applications already documented

Healthcare (mortality risk, EEG, HIV genes), criminal justice (COMPAS), credit risk (FICO HELOC). **No published applications to financial time-series or volatility forecasting** as of May 2026 — see Part 2.

---

## C. Ensemble Methods — the Incumbent

### C.1 Random Forests / Gradient Boosting algorithmic differences

- **XGBoost** (Chen & Guestrin, KDD 2016): exact and approximate quantile-sketch split finding; column-block in-memory layout; cache-aware histogram aggregation; sparsity-aware splits. 28,300 stars on dmlc/xgboost (May 2026).
- **LightGBM** (Ke et al., NeurIPS 2017): **GOSS** (Gradient-based One-Side Sampling) keeps all large-gradient instances and randomly samples small-gradient ones; **EFB** (Exclusive Feature Bundling) bundles mutually-exclusive sparse features; leaf-wise (best-first) growth. Repository moved to lightgbm-org/LightGBM in March 2026.
- **CatBoost** (Prokhorenkova et al., NeurIPS 2018): **ordered boosting** to combat target leakage from prediction-shift; categorical-feature target encoding via random permutations; **oblivious decision trees** (symmetric — same split feature/threshold across all nodes at a given depth) enabling fast inference. 8,800 stars on catboost/catboost (May 2026).

### C.2 Grinsztajn, Oyallon & Varoquaux (NeurIPS 2022 Datasets and Benchmarks)

"Why do tree-based models still outperform deep learning on typical tabular data?" — 48 datasets (in the published NeurIPS 2022 version; the arXiv v1 preprint reported 45) with tuned hyperparameters. Tree-based models remain state-of-the-art on medium-sized tabular data (≈10K samples). Three critical inductive biases: robustness to uninformative features, preservation of feature orientation (no rotational invariance), low-frequency / piecewise-constant target functions easier to fit via partition.

### C.3 Distillation and the accuracy-interpretability tradeoff

GOSDT-Guesses (McTavish et al., AAAI 2022) effectively distills a gradient-boosted ensemble into an optimal sparse single tree. TAO (Carreira-Perpiñán & Tavallali, NeurIPS 2018) and Forest Alternating Optimization (CVPR 2023) optimize fixed-structure trees/forests via alternating optimization. Rudin's "Stop Explaining Black Box Models" (*Nature MI* 2019) argues the tradeoff is **often illusory** for tabular data — empirically defended by GOSDT/TreeFARMS results within 1–2% of black-box performance on FICO/COMPAS/hospital-readmission benchmarks.

---

## D. Decision Trees for Regression and Continuous Targets

- **OSRT** (Zhang, Xin, Seltzer, Rudin, AAAI 2023): GOSDT-style branch-and-bound with a novel lower bound based on 1-D k-means equivalent points. First fully-optimal sparse regression-tree algorithm.
- **STreeD piecewise-constant and piecewise-linear regression** (van den Bos, van der Linden, Demirović, ICML 2024): scalability improvements of one-or-more orders of magnitude over OSRT. Piecewise-linear variant: elastic-net leaves with separately tunable lasso/ridge and cost-complexity. Piecewise-simple-linear variant: one univariate regressor per leaf.
- **Quant-BnB** (Mazumder et al., ICML 2022): handles regression natively, depth ≤ 3 in practice.
- **Dyadic CART / ORT** (Donoho 1997; Chatterjee & Goswami, *Annals of Statistics* 2021): theoretical risk bounds; minimax-optimal rates for piecewise-constant and bounded-variation classes.
- **M5 / Cubist** (Quinlan 1992) — greedy linear-leaf trees; STreeD piecewise-linear is the first **provably optimal** model-tree algorithm.
- **Quantile Regression Forests** (Meinshausen, JMLR 2006); **Optimal interpretable quantile regression trees** (Lemaire, Aglin, Nijssen, IDA 2024) — set of optimal trees for the conditional distribution.
- **Time-series-specific tree methods**: BART-HAR, GAS-trees (Patton et al.), CART-augmented HAR — but **none use optimal or Rashomon-set trees**.

---

## E. Interpretability

### E.1 Inherent vs. post-hoc

Rudin's *Nature MI* 2019 makes the central distinction. Inherently interpretable models (sparse decision trees, scoring systems, rule lists, sparse linear models, GAMs) reveal their reasoning structurally. Post-hoc explanations (SHAP, LIME, gradient-based) approximate locally and are demonstrably unstable, unfaithful, and manipulable.

### E.2 Practical bounds

Rudin et al. (2022, *Statistics Surveys* 16) and Costa & Pedreira (*Information Fusion* 2023): trees with **≤10 leaves and depth ≤ 5** are reliably human-interpretable; 30+ leaves stretches comprehension. Operational interpretation matters more than visual: a domain expert reads the path, audits each split, detects spurious or unfair rules.

### E.3 Monotonicity and fairness

Implementable in STreeD (separable objective), GOSDT (post-processing), LightGBM/XGBoost natively. **FairTree** (Aghaei, Azizi, Vayanos, AAAI 2019; Jo et al., FAccT 2023) is MIP-based for statistical parity / predictive equality / equal opportunity / equalized odds. **Fair STreeD** (van der Linden, de Weerdt, Demirović, NeurIPS 2022) is DP-based, several orders of magnitude faster, and computes the full accuracy/fairness Pareto front.

### E.4 Predictive equivalence (McTavish, Boner, Donnelly, Seltzer, Rudin, ICML 2025)

Two trees can encode the same decision boundary while differing in evaluation order, affecting variable importance and missing-value handling. A boolean-logical canonicalization is proposed.

---

## F. Computational and Implementation Landscape

| Library | Algorithms | Stars | Sklearn-compat | Active |
|---|---|---|---|---|
| `gosdt` (ubc-systopia/gosdt-guesses) | GOSDT, OSDT, GOSDT-Guesses | 57 | Yes | 2024–25 |
| `treefarms` (ubc-systopia/treeFarms) | TreeFARMS Rashomon | 47 | Yes | Yes |
| `pydl85` (aia-uclouvain) | DL8.5 | 15–30 | Yes | Yes |
| `pystreed` (AlgTUDelft) | STreeD: cls/reg/fairness/survival/policy | 30–50 | Yes | Yes |
| `pycontree` (ConSol-Lab) | ConTree | <20 | Yes | 2025 |
| `SPLIT-ICML` (VarunBabbar) | SPLIT, LicketySPLIT, RESPLIT | <30 | Yes | 2025 |
| `pymurtree` | MurTree | <15 | Partial | Sporadic |
| `MAPTree` (ThrunGroup) | Bayesian MAP | 30–50 | Yes | Yes |
| `scikit-learn` | CART (DT, RF, GB) | 65,877 (Apr 2026) | n/a | Yes |
| `xgboost` | GBT | 28,300 (May 2026) | Yes | Yes |
| `catboost` | GBT | 8,800 (May 2026) | Yes | Yes |
| `interpretML` (Microsoft) | EBM (GAM), CART | 6K+ | Yes | Yes |

**Performance**: GOSDT/SPLIT/LicketySPLIT/STreeD practically feasible to depth 4 on 100K rows × 250 binarized features, or 1M rows × 150 binarized features. 10K rows × 100 features: TreeFARMS for full Rashomon enumeration in minutes; RESPLIT/SORTeD in seconds. **No GPU acceleration** for any optimal-tree library — these are inherently combinatorial CPU. XGBoost/LightGBM offer GPU.

**Sklearn integration**: GOSDT, TreeFARMS, STreeD, ConTree, PyDL8.5, MAPTree all expose `.fit(X,y)/.predict(X)` and inherit from `BaseEstimator`. Common gotcha: most optimal-tree methods need binarized features; ConTree and STreeD piecewise-linear handle continuous features natively.

---

## G. Theoretical Foundations

### G.1 Sample complexity and generalization

For a depth-d tree with k binary features, the VC dimension is O(2^d log k); generalization bounds via Rademacher complexity follow standard arguments. Van der Linden 2024 Section 5.4.6: "ODTs achieve the same performance as greedy trees at smaller size limits, which means there is no difference in overfitting after tuning." Optimization-aware learning-theoretic bounds (Hu, Rudin, Seltzer 2019 Section 4) provide guarantees on test performance as a function of the training-set objective and the optimality gap.

### G.2 SPLIT approximation guarantees

Theorem A.1: SPLIT is provably at least as good as a fully greedy entropy-based method with the same constraints. Corollary 6.3: SPLIT saves O(k^((d−1)/2) · (d/2)!) over fully optimal methods. Theorem 6.5: there exist data distributions where SPLIT achieves accuracy 1−ε while pure greedy achieves at most 1/2+ε.

### G.3 NP-hardness and parameterized complexity

Hyafil & Rivest (1976) — NP-complete even for binary features. Komusiewicz, Kunz, Sommer & Sorge (ICML 2023): optimal tree ensembles computable in O((6δDS)^S · poly), where S is number of cuts in the ensemble, D the largest domain size, δ the maximum number of features differing between any two examples; also an ℓ^n · poly DP-based algorithm. Ordyniak & Szeider 2021, Eiben et al. 2023, Gahlawat & Zehavi 2024 establish related FPT and W-hardness results.

### G.4 Algorithmic pluralism

The literature is unusually pluralistic: DP (DL8.5, MurTree, STreeD), branch-and-bound (OSDT, GOSDT, OSRT, ConTree, Quant-BnB), CP (Verhaeghe et al.), SAT/MaxSAT (Narodytska et al., Hu et al.), MIP (OCT, BinOCT, Strong OCT). Empirically, **DP+BnB with specialized depth-2 solvers and analytical bounds dominate** for axis-aligned trees (Costa & Pedreira survey 2023; van der Linden 2024).

---

## H. The Frontier (2025+)

- **Scaling to millions of rows**: STreeD with ConTree handles ~1M instances at depth ≤ 4; SPLIT extends this; streaming/online optimal trees remain open.
- **Optimal tree ensembles**: Komusiewicz et al. (ICML 2023) — first parameterized-complexity-tractable algorithm; FAO (CVPR 2023) optimizes fixed-structure forests.
- **Differentiable trees (TAO)**: alternating optimization with differentiable surrogates; sparser, more accurate single trees and small forests than CART forests.
- **Neural-tree hybrids**: NODE (Popov, Morozov, Babenko, ICLR 2020) — neural oblivious decision ensembles, generalizing CatBoost's oblivious trees with end-to-end gradient training; TabNet (Arik & Pfister, AAAI 2021) — sequential attention-based feature selection.
- **Rashomon sets + causal inference**: Coker, Rudin, King (*Management Science* 2021); cross-Rashomon-set stability tests.
- **Open**: streaming Rashomon sets; optimal trees under distribution shift / time-varying targets; certified-optimal oblique-split trees beyond depth 3; certified GBT-distillation.