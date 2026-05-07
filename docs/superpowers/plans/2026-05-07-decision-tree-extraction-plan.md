# Decision Tree Deep Research Extraction -- Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose `notes/deep-research-decision-trees.md` into the repo's existing structure: enrich bibliography category H, append feature findings, update project proposals, update research index, trim source file.

**Architecture:** Content extraction, not code. Each task reads the source file and writes/appends to target files. The bibliography task is the largest (~50 new entries + 12 enrichments). The source file is trimmed last after all extractions are complete.

**Spec:** `docs/superpowers/specs/2026-05-07-decision-tree-extraction-design.md`

**Source file structure** (line ranges for reference):
- Lines 1-11: Executive Summary (KEEP)
- Line 13: Separator (KEEP)
- Lines 15-224: Sections A-H Landscape Survey (KEEP)
- Lines 226-309: Part 2 Applicability Assessment (EXTRACT to `notes/project-proposals.md`)
- Lines 312-322: Recommendations (EXTRACT to `notes/project-proposals.md`)
- Lines 326-336: Caveats (EXTRACT to `notes/project-proposals.md`)

---

## Chunk 1: Bibliography modifications

### Task 1: Enrich existing bibliography entries and split DL8.5/MurTree

**Files:**
- Modify: `reference/bibliography.md` (currently 1049 lines, category H at lines 635-780)

This task enriches 12 existing entries in category H with deeper detail from the decision tree research, and splits the combined `aglin-etal-2020-demirovic-2022` entry into two separate entries.

- [ ] **Step 1: Split `aglin-etal-2020-demirovic-2022` into two entries**

Read `reference/bibliography.md` lines 659-668. Replace the combined entry with two separate entries:

```markdown
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
```

- [ ] **Step 2: Enrich `lin-etal-2020-gosdt` (line 648)**

Update the Key finding and Relevance fields:

```markdown
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
```

- [ ] **Step 3: Enrich `van-der-linden-etal-2023-streed` (line 670)**

```markdown
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
```

- [ ] **Step 4: Enrich `babbar-etal-2025-split` (line 692)**

```markdown
### babbar-etal-2025-split
- **Title**: [KEEP EXISTING TITLE -- verify against ICML 2025 camera-ready before changing]
- **Authors**: Babbar, McTavish, Rudin, Seltzer
- **Year**: 2025
- **Venue**: ICML 2025 Oral (arXiv 2502.15988)
- **Quality**: essential
- **Topics**: rashomon, optimal-trees
- **PDF**: none
- **Key finding**: Hybrid lookahead+greedy: optimal near root, greedy near leaves. Provably at least as good as fully greedy (Theorem A.1). Saves O(k^((d-1)/2) * (d/2)!) over fully optimal (Corollary 6.3). There exist distributions where SPLIT achieves 1-epsilon while greedy achieves at most 1/2+epsilon (Theorem 6.5). LicketySPLIT: recursive depth-1 variant in polynomial time O(|R|*n*k^3*d^3). RESPLIT extends to Rashomon-set computation, ~74x faster than TreeFARMS on Bike, ~17x on Spambase. Over 100x faster than GOSDT. Code: github.com/VarunBabbar/SPLIT-ICML.
- **Relevance**: Fastest near-optimal solver; the tool for rapid iteration during research. RESPLIT is the scalable Rashomon-set alternative to TreeFARMS. Classification only currently.
```

- [ ] **Step 5: Enrich remaining entries**

Update the following entries in-place with enriched Key finding and Relevance fields. For each, read the current entry and update:

**`heile-etal-2025-licketyresplit` (line 703):** Add to Key finding: "Polynomial-time approximation to the Rashomon set, recursively finding near-optimal splits conditioned on easy-to-compute oracles. Orders-of-magnitude runtime and memory improvement over TreeFARMS and RESPLIT. Recovers nearly the full Rashomon set." Note: the specific speedup numbers (74x on Bike, 17x on Spambase) belong to RESPLIT (in `babbar-etal-2025-split`), not LicketyRESPLIT. LicketyRESPLIT's speedup over TreeFARMS/RESPLIT is described in the source Section B.5.

**`arslan-etal-2025-sorted` (line 714):** Fix title to "SORTeD: Anytime Enumeration of Rashomon Trees in Objective Order". Update Authors to "Arslan, van der Linden, Hoogendoorn, Rinaldi, Demirovic". Update Key finding: "Enumerates the Rashomon set in decreasing order of objective value -- best trees first. Anytime termination at any quality threshold. Up to two orders of magnitude speedup over TreeFARMS/RESPLIT. Supports any separable, totally ordered objective (works for regression and survival via STreeD)."

**`semenova-rudin-parr-2022` (line 725):** Fix title to "On the Existence of Simpler Machine Learning Models". Update Venue to "FAccT 2022 (arXiv 1908.01755)". Update Key finding: "Introduces the Rashomon ratio -- ratio of volume of Rashomon set to hypothesis space volume. When several different ML methods produce near-equal accuracy on a dataset, the Rashomon ratio is large, guaranteeing simpler models exist within the Rashomon set."

**`xin-etal-2022-treefarms` (line 681):** Update Key finding: "First complete enumeration of the Rashomon set for any non-trivial hypothesis class. Extends GOSDT with a specialized trie ('Trees FAst RashoMon Sets') supporting efficient query and sampling. Finds orders of magnitude more distinct near-optimal trees than BART/MCMC samplers. Applications: variable importance over entire Rashomon set, derived-metric Rashomon sets (balanced accuracy, F1), bootstrap Rashomon sets. Code: `pip install treefarms` (github.com/ubc-systopia/treeFarms, 47 stars)."

**`dong-rudin-2020` (line 736):** Update Key finding: "Variable Importance Clouds map every variable to its Model Reliance importance for every good model in the Rashomon set. Used with TreeFARMS, VIC reveals when one variable is interchangeable with another versus uniquely important. Shapley-VIC extension (Ning et al., Patterns 2022) extends to SHAP values across the Rashomon set."

**`rudin-etal-2024-position` (line 747):** Update Venue field to "ICML 2024 Spotlight (arXiv 2407.04846)". Update Key finding: "Position paper consolidating six benefits of computing the Rashomon set: (1) existence of simpler-yet-accurate models, (2) flexibility for fairness/monotonicity constraints, (3) uncertainty quantification, (4) reliable variable importance, (5) algorithm-choice diagnostics, (6) public-policy applications. Argues ML should reframe learning as a feasibility problem ('find all good models') rather than optimization."

**`mctavish-etal-2025` (line 758):** Update Key finding: "Defines predictive equivalence classes within decision tree Rashomon sets. Two trees can encode the same decision boundary while differing in evaluation order, affecting variable importance and missing-value handling. Proposes a boolean-logical canonicalization to identify truly distinct models." Add `interpretability` to Topics.

**`marx-calmon-ustun-2020` (line 769):** Update Key finding: "Formalizes predictive multiplicity -- the degree to which competing models disagree on individual predictions. Proposes metrics (ambiguity, discrepancy) to measure it. Shows that standard model selection ignores multiplicity, which can be large even when test accuracy is near-identical."

- [ ] **Step 6: Commit**

```bash
git add reference/bibliography.md
git commit -m "docs: enrich 12 existing bibliography entries, split aglin/demirovic combined entry"
```

---

### Task 2: Add ~50 new bibliography entries to category H

**Files:**
- Modify: `reference/bibliography.md`

Add new entries after the existing category H entries (after `marx-calmon-ustun-2020`, before the `---` separator and `## I.` heading). Group them with sub-comments for readability. Source: inline citations from `notes/deep-research-decision-trees.md` sections A-H and Part 2.

**Deduplication checklist before adding:** Do NOT add entries for papers that already exist in the bibliography: `breiman-2001`, `christensen-siggaard-veliyev-2023` (category D), `lopez-de-prado-2018` (category G), or any of the 12 entries enriched in Task 1.

- [ ] **Step 1: Add greedy baselines and NP-hardness entries**

Insert after the last line of `marx-calmon-ustun-2020` (its Relevance field), BEFORE the `---` separator at line 780 (which separates category H from `## I.`). Do NOT insert after the separator -- that would place entries outside category H.

```markdown
### hyafil-rivest-1976
- **Title**: Constructing Optimal Binary Decision Trees is NP-Complete
- **Authors**: Hyafil, Rivest
- **Year**: 1976
- **Venue**: Information Processing Letters 5(1):15-17
- **Quality**: essential
- **Topics**: optimal-trees, np-hardness, foundational
- **PDF**: none
- **Key finding**: Proved that constructing the optimal binary decision tree is NP-complete, establishing the theoretical barrier that motivated greedy heuristics (CART, C4.5) and ensembling for decades.
- **Relevance**: The foundational hardness result that the modern optimal-tree revolution overcomes via practical algorithms with exponential worst-case but tractable average-case behavior.

### breiman-etal-1984-cart
- **Title**: Classification and Regression Trees
- **Authors**: Breiman, Friedman, Olshen, Stone
- **Year**: 1984
- **Venue**: Wadsworth (book)
- **Quality**: essential
- **Topics**: optimal-trees, regression-trees, foundational
- **PDF**: none
- **Key finding**: Introduced CART: top-down greedy recursive partitioning with cost-complexity pruning. The structural limitation is myopia -- each split is locally optimal but globally suboptimal.
- **Relevance**: The greedy baseline that all optimal tree methods improve upon. CART regression trees (mean prediction in leaves) remain the default sklearn implementation.

### quinlan-1993-c45
- **Title**: C4.5: Programs for Machine Learning
- **Authors**: Quinlan
- **Year**: 1993
- **Venue**: Morgan Kaufmann (book)
- **Quality**: recommended
- **Topics**: optimal-trees, foundational
- **PDF**: none
- **Key finding**: Extended ID3 with information gain ratio, handling of continuous attributes, missing values, and pruning. Dominant academic tree learner through the 1990s-2000s.
- **Relevance**: Historical context for understanding what greedy tree learning provides and where it falls short.

### murthy-salzberg-1995
- **Title**: Lookahead and Pathology in Decision Tree Induction
- **Authors**: Murthy, Salzberg
- **Year**: 1995
- **Venue**: IJCAI [verify venue -- source does not specify]
- **Quality**: optional
- **Topics**: optimal-trees, foundational
- **PDF**: none
- **Key finding**: Empirically documented that greedy top-down induction is myopic: locally optimal splits at the root can force globally suboptimal subtrees.
- **Relevance**: Motivates the optimal tree approach; shows empirically where greedy fails.
```

- [ ] **Step 2: Add early exact methods**

```markdown
### bertsimas-dunn-2017
- **Title**: Optimal Classification Trees
- **Authors**: Bertsimas, Dunn
- **Year**: 2017
- **Venue**: Machine Learning 106(7):1039-1082
- **Quality**: recommended
- **Topics**: optimal-trees, np-hardness
- **PDF**: none
- **Key finding**: MIP formulation for optimal classification trees with oblique splits. First modern attempt at exact optimization, but limited to depth <= 4 on small datasets due to MIP scaling.
- **Relevance**: Pioneered the MIP approach; surpassed by DP/BnB methods (GOSDT, MurTree, STreeD) which scale better for axis-aligned trees.

### verwer-zhang-2019
- **Title**: BinOCT: Learning Optimal Binary Classification Trees
- **Authors**: Verwer, Zhang
- **Year**: 2019
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness
- **PDF**: none
- **Key finding**: Binary linear program where decision thresholds are encoded via binary search with big-M constraints, making the formulation independent of row count. Best on datasets up to ~5000 rows. Always produces complete binary trees of given depth.
- **Relevance**: Historical step toward practical optimal trees; superseded by GOSDT/MurTree/STreeD.

### verhaeghe-etal-2020
- **Title**: Learning Optimal Decision Trees Using Constraint Programming
- **Authors**: Verhaeghe, Nijssen, Pesant, Quimper, Schaus
- **Year**: 2020
- **Venue**: Constraints 25(3-4):226-250
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness
- **PDF**: none
- **Key finding**: Constraint programming formulation for optimal decision trees; demonstrates CP as a viable alternative to MIP for tree optimization.
- **Relevance**: Part of the algorithmic pluralism in optimal trees; DP+BnB methods empirically dominate CP for axis-aligned trees.

### narodytska-etal-2018
- **Title**: Learning Optimal Classification Trees Using a Binary Linear Program Formulation
- **Authors**: Narodytska, Ignatiev, Pereira, Marques-Silva
- **Year**: 2018
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness
- **PDF**: none
- **Key finding**: MaxSAT-based approach to optimal decision trees; finds minimum-size trees for perfect classification.
- **Relevance**: Part of the SAT/MaxSAT lineage; limited to perfect-classification objective, superseded by more flexible methods.

### hu-siala-etal-2020
- **Title**: Learning Optimal Decision Trees with MaxSAT and Its Integration into AdaBoost
- **Authors**: Hu, Siala, Hebrard, Huguet
- **Year**: 2020
- **Venue**: IJCAI
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness, ensemble
- **PDF**: none
- **Key finding**: MaxSAT variant with AdaBoost integration; extends SAT-based optimal trees to ensemble settings.
- **Relevance**: Shows SAT-based methods can integrate with boosting; not directly applicable to regression.
```

- [ ] **Step 3: Add modern optimal-tree algorithms**

```markdown
### hu-rudin-seltzer-2019-osdt
- **Title**: Optimal Sparse Decision Trees
- **Authors**: Hu, Rudin, Seltzer
- **Year**: 2019
- **Venue**: NeurIPS
- **Quality**: essential
- **Topics**: optimal-trees, rashomon, foundational
- **PDF**: none
- **Key finding**: First practical decision-tree-specific optimal algorithm. Minimizes regularized misclassification L(T) + lambda*|leaves(T)| over binary features using analytical bounds (hierarchical objective, leaf permutation, equivalent-points, similar-support) and custom bit-vector library for fast captured-sample updates. The breakthrough paper.
- **Relevance**: Foundation for the entire GOSDT/TreeFARMS/SPLIT lineage. Binary features only, classification only -- extended by GOSDT.

### mctavish-etal-2022-gosdt-guesses
- **Title**: Fast Sparse Decision Tree Optimization via Reference Ensembles
- **Authors**: McTavish, Zhong, Hu, Rudin, Seltzer
- **Year**: 2022
- **Venue**: AAAI
- **Quality**: recommended
- **Topics**: optimal-trees, distillation, gradient-boosting
- **PDF**: none
- **Key finding**: Formalizes GOSDT's threshold guessing: trains a black-box model (LightGBM) to generate candidate split thresholds, then uses them to guide the optimal tree search. Effectively distills an ensemble into an optimal sparse single tree. Turns 80 continuous features into ~200-500 prioritized binary thresholds.
- **Relevance**: The binarization recipe for applying GOSDT/SPLIT to continuous-feature datasets like the vol panel. Critical preprocessing step.

### demirovic-hebrard-jean-2023-blossom
- **Title**: Blossom: Anytime Optimal Decision Trees
- **Authors**: Demirovic, Hebrard, Jean
- **Year**: 2023
- **Venue**: ICML
- **Quality**: recommended
- **Topics**: optimal-trees
- **PDF**: none
- **Key finding**: Depth-first, layer-by-layer node expansion. First solution found is the greedy tree; successive improvements converge monotonically to the optimum. Virtually no overhead vs heuristic methods at start; matches best exact methods at convergence. Anytime: interrupt at any point for best-so-far solution.
- **Relevance**: Useful when compute budget is uncertain; get a greedy tree immediately, improve toward optimal as time allows.

### mazumder-meng-wang-2022
- **Title**: Quant-BnB: Branch and Bound on Quantiles for Continuous-Feature Decision Trees
- **Authors**: Mazumder, Meng, Wang
- **Year**: 2022
- **Venue**: ICML
- **Quality**: optional
- **Topics**: optimal-trees, regression-trees
- **PDF**: none
- **Key finding**: First specialized continuous-feature optimal decision tree via BnB on quantiles. Handles regression natively. Practical limit: depth <= 3.
- **Relevance**: Depth limit too shallow for vol forecasting (need depth 4-5); use STreeD instead.

### zhang-xin-seltzer-rudin-2023-osrt
- **Title**: Optimal Sparse Regression Trees
- **Authors**: Zhang, Xin, Seltzer, Rudin
- **Year**: 2023
- **Venue**: AAAI
- **Quality**: essential
- **Topics**: optimal-trees, regression-trees
- **PDF**: none
- **Key finding**: First fully-optimal sparse regression tree algorithm. GOSDT-style branch-and-bound with a novel lower bound based on 1-D k-means equivalent points. Piecewise-constant predictions in leaves.
- **Relevance**: Second-priority method for vol forecasting (after STreeD piecewise-linear). Provides the provably optimal piecewise-constant regression baseline.

### zhang-xin-seltzer-rudin-2024-survival
- **Title**: Optimal Sparse Survival Trees
- **Authors**: Zhang, Xin, Seltzer, Rudin
- **Year**: 2024
- **Venue**: AISTATS
- **Quality**: optional
- **Topics**: optimal-trees, survival-trees
- **PDF**: none
- **Key finding**: Extends OSRT to survival analysis with concordance-index and IBS objectives. First provably optimal survival tree.
- **Relevance**: Not directly applicable to vol regression, but demonstrates the generality of the OSDT/GOSDT framework.

### sullivan-tiwari-thrun-2024
- **Title**: MAPTree: Beating Optimal Decision Trees with Bayesian Decision Trees
- **Authors**: Sullivan, Tiwari, Thrun
- **Year**: 2024
- **Venue**: AAAI
- **Quality**: recommended
- **Topics**: optimal-trees
- **PDF**: none
- **Key finding**: Bayesian MAP tree via AND/OR search; outperforms or matches GOSDT/MurTree with smaller trees on 16 datasets, with optimality certificate. Note: optimizes a Bayesian MAP objective (BCART prior), not regularized misclassification -- comparisons to GOSDT/MurTree are not strictly apples-to-apples.
- **Relevance**: Alternative solver producing compact trees; Bayesian framework provides natural uncertainty quantification.

### aghaei-gomez-vayanos-2024
- **Title**: Strong Optimal Classification Trees
- **Authors**: Aghaei, Gomez, Vayanos
- **Year**: 2024
- **Venue**: Operations Research
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness
- **PDF**: none
- **Key finding**: Strongest known max-flow MIP formulation for axis-aligned optimal trees. Stronger LP relaxation than OCT (Bertsimas-Dunn).
- **Relevance**: State-of-the-art MIP approach; but DP+BnB methods (STreeD, GOSDT) remain faster in practice for axis-aligned trees.

### van-der-linden-etal-2025-benchmark
- **Title**: Necessary and Sufficient Conditions for Optimal Decision Trees using Dynamic Programming [verify title -- may be a different paper than the benchmark; arXiv:2409.12788]
- **Authors**: van der Linden, Vos, de Weerdt, Verwer, Demirovic
- **Year**: 2025 (arXiv September 2024, using 2025 as canonical year pending publication)
- **Venue**: arXiv:2409.12788 (preprint)
- **Quality**: essential
- **Topics**: optimal-trees, tabular-ml
- **PDF**: none
- **Key finding**: Definitive 180-dataset benchmark. Verbatim: "average improvement of 1.3% and 1.0% of optimal over greedy approaches" at depth 3 and 4. For larger datasets (n>250), optimal vs CART gap is 1.6% +/- 0.2. Training ODTs feasible up to ~250 binary features for 100K instances and ~150 for 1M instances.
- **Relevance**: The empirical reference for setting expectations on optimal-vs-greedy accuracy gaps and computational scaling limits.

### brita-van-der-linden-demirovic-2025
- **Title**: ConTree: Optimal Decision Trees on Continuous Features
- **Authors**: Brita, van der Linden, Demirovic
- **Year**: 2025
- **Venue**: AAAI
- **Quality**: recommended
- **Topics**: optimal-trees, regression-trees
- **PDF**: none
- **Key finding**: Optimal trees directly on continuous features without binarization. Test accuracy averages 5% higher than CART and 0.7% higher than coarse-binarized ODTs. Code: github.com/ConSol-Lab/contree, `pip install pycontree`.
- **Relevance**: Use for classification framings (vol regime up/flat/down) on continuous features. Avoids the binarization preprocessing step entirely.
```

- [ ] **Step 4: Add STreeD extensions**

```markdown
### van-den-bos-van-der-linden-demirovic-2024
- **Title**: STreeD: Piecewise-Linear and Piecewise-Constant Regression Trees
- **Authors**: van den Bos, van der Linden, Demirovic
- **Year**: 2024
- **Venue**: ICML
- **Quality**: essential
- **Topics**: optimal-trees, regression-trees
- **PDF**: none
- **Key finding**: First provably optimal piecewise-linear regression tree algorithm. Elastic-net leaves with separately tunable lasso/ridge and cost-complexity. Piecewise-simple-linear variant: one univariate regressor per leaf. Depth-2 specialized solver. Scalability improvements of one or more orders of magnitude over OSRT.
- **Relevance**: Primary recommended method for the vol regression task. Elastic-net leaves capture local linear relationships within tree partitions -- more expressive than piecewise-constant OSRT.

### huisman-van-der-linden-demirovic-2024
- **Title**: Optimal Survival Trees
- **Authors**: Huisman, van der Linden, Demirovic
- **Year**: 2024
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees, survival-trees
- **PDF**: none
- **Key finding**: DP-based optimal survival trees via STreeD's separable-objective framework. Demonstrates the generality of the STreeD approach.
- **Relevance**: Not directly applicable to vol regression; relevant if modeling time-to-event (e.g., time until next vol spike).

### van-der-linden-etal-2022-fair
- **Title**: Fair and Optimal Decision Trees: A Dynamic Programming Approach
- **Authors**: van der Linden, de Weerdt, Demirovic
- **Year**: 2022
- **Venue**: NeurIPS
- **Quality**: optional
- **Topics**: optimal-trees, fairness
- **PDF**: none
- **Key finding**: DP-based fair optimal trees computing the full accuracy/fairness Pareto front. Several orders of magnitude faster than MIP-based FairTree.
- **Relevance**: Not directly needed for vol forecasting, but demonstrates STreeD's ability to optimize with constraints -- relevant if adding monotonicity constraints.

### van-der-linden-etal-2023-policy
- **Title**: Optimal Prescriptive Trees
- **Authors**: van der Linden, de Weerdt, Demirovic
- **Year**: 2023
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees
- **PDF**: none
- **Key finding**: Extends STreeD to prescriptive/policy tree optimization for treatment effect estimation.
- **Relevance**: Tangential; relevant if framing vol forecasting as a treatment-effect problem (e.g., optimal hedging decisions).

### demirovic-stuckey-2021
- **Title**: Optimal Decision Trees with Cost-Sensitive Objectives
- **Authors**: Demirovic, Stuckey
- **Year**: 2021
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees
- **PDF**: none
- **Key finding**: DP-based cost-sensitive classification including F1 and Matthews correlation coefficient. Part of the STreeD lineage.
- **Relevance**: Relevant if framing vol forecasting as classification (vol-up vs vol-down) with asymmetric costs.
```

- [ ] **Step 5: Add Rashomon additions**

```markdown
### semenova-chen-parr-rudin-2023
- **Title**: A Path to Simpler Models Starts With Noise
- **Authors**: Semenova, Chen, Parr, Rudin
- **Year**: 2023
- **Venue**: NeurIPS
- **Quality**: recommended
- **Topics**: rashomon
- **PDF**: none
- **Key finding**: Label noise mechanically inflates the Rashomon ratio, explaining why tabular benchmarks in healthcare, criminal justice, lending, and finance routinely admit large Rashomon sets. Noisier problems = larger Rashomon sets = more room for interpretable models.
- **Relevance**: Financial time-series targets are inherently noisy -- predicts that the Rashomon set for vol forecasting will be large, favoring the interpretable-tree approach.

### donnelly-katta-rudin-browne-2023
- **Title**: Rashomon Importance Distributions
- **Authors**: Donnelly, Katta, Rudin, Browne
- **Year**: 2023
- **Venue**: NeurIPS
- **Quality**: essential
- **Topics**: rashomon, feature-engineering
- **PDF**: none
- **Key finding**: RID: variable importance distribution over (Rashomon set x bootstrap), with consistency theorems and finite-sample error rates. Stably ranks variables when single-model importance fluctuates. More principled than VIC for hypothesis testing on feature importance.
- **Relevance**: Primary tool for stable feature ranking in the Rashomon project. More rigorous than single-model SHAP/permutation importance. Apply to vol features to identify robustly important vs. interchangeable predictors.

### ning-etal-2022
- **Title**: Shapley-VIC: Variable Importance Clouds via Shapley Values
- **Authors**: Ning, Jia, Gao, Seltzer, Rudin
- **Year**: 2022
- **Venue**: Patterns
- **Quality**: recommended
- **Topics**: rashomon, feature-engineering
- **PDF**: none
- **Key finding**: Extends Variable Importance Clouds to SHAP values, computing Shapley importance across every model in the Rashomon set.
- **Relevance**: If SHAP is preferred over Model Reliance for feature importance, Shapley-VIC provides the Rashomon-aware alternative.

### zhong-etal-2023-gam
- **Title**: Exploring and Interacting with the Set of Good Sparse Generalized Additive Models
- **Authors**: Zhong, Liu, Chen, Hu, Rudin
- **Year**: 2023
- **Venue**: NeurIPS
- **Quality**: optional
- **Topics**: rashomon, interpretability
- **PDF**: none
- **Key finding**: Rashomon set enumeration for sparse generalized additive models, extending the Rashomon framework beyond trees.
- **Relevance**: Shows Rashomon sets are computable for non-tree model classes; relevant if considering GAMs as interpretable alternatives.

### liu-etal-2022-fasterrisk
- **Title**: FasterRisk: Fast and Accurate Interpretable Risk Scores
- **Authors**: Liu, Zhong, Seltzer, Rudin
- **Year**: 2022
- **Venue**: NeurIPS
- **Quality**: optional
- **Topics**: rashomon, interpretability
- **PDF**: none
- **Key finding**: Rashomon-set-aware sparse integer risk scores optimized for clinical deployment. Produces near-optimal scoring systems in seconds.
- **Relevance**: Tangential to vol forecasting; demonstrates Rashomon methodology in a different interpretable model class.

### coker-rudin-king-2021
- **Title**: A Theory of Statistical Inference for Ensuring the Robustness of Scientific Results
- **Authors**: Coker, Rudin, King
- **Year**: 2021
- **Venue**: Management Science
- **Quality**: recommended
- **Topics**: rashomon, interpretability
- **PDF**: none
- **Key finding**: Rashomon sets for linear models; cross-Rashomon-set stability tests for scientific claims. Also early work connecting Rashomon sets to causal inference.
- **Relevance**: Methodological reference for using Rashomon sets to test robustness of findings; applicable to assessing stability of vol feature importance claims.

### donnelly-etal-2025-cvpr
- **Title**: Rashomon Sets for Prototype-Part Networks
- **Authors**: Donnelly, Semenova, Rudin, Browne
- **Year**: 2025
- **Venue**: CVPR
- **Quality**: optional
- **Topics**: rashomon, deep-learning
- **PDF**: none
- **Key finding**: Extends Rashomon set computation to prototype-part neural networks, showing the framework is not limited to simple model classes.
- **Relevance**: Demonstrates breadth of Rashomon framework; not directly applicable to tabular regression.

### hsu-calmon-2022
- **Title**: Rashomon Capacity: A Metric for Predictive Multiplicity in Classification
- **Authors**: Hsu, Calmon
- **Year**: 2022
- **Venue**: NeurIPS
- **Quality**: optional
- **Topics**: rashomon
- **PDF**: none
- **Key finding**: Proposes Rashomon Capacity as a metric for predictive multiplicity independent of a specific model class. Complements Marx et al. 2020's ambiguity/discrepancy metrics.
- **Relevance**: Useful if quantifying prediction disagreement across the Rashomon set for risk reporting.
```

- [ ] **Step 6: Add ensemble methods, interpretability, neural-tree hybrids, regression, theory, foundational**

```markdown
### chen-guestrin-2016
- **Title**: XGBoost: A Scalable Tree Boosting System
- **Authors**: Chen, Guestrin
- **Year**: 2016
- **Venue**: KDD
- **Quality**: essential
- **Topics**: gradient-boosting, ensemble, tabular-ml
- **PDF**: none
- **Key finding**: Exact and approximate quantile-sketch split finding; column-block in-memory layout; cache-aware histogram aggregation; sparsity-aware splits. 28,300 stars on dmlc/xgboost (May 2026). The benchmark ensemble method for tabular data.
- **Relevance**: Primary ensemble baseline to compare against optimal trees. If optimal tree accuracy is within 2-5% MSE, interpretability justifies the tradeoff.

### ke-etal-2017
- **Title**: LightGBM: A Highly Efficient Gradient Boosting Decision Tree
- **Authors**: Ke, Meng, Finley, Wang, Chen, Ma, Ye, Liu
- **Year**: 2017
- **Venue**: NeurIPS
- **Quality**: essential
- **Topics**: gradient-boosting, ensemble, tabular-ml
- **PDF**: none
- **Key finding**: GOSS (Gradient-based One-Side Sampling) keeps large-gradient instances, randomly samples small-gradient ones. EFB (Exclusive Feature Bundling) bundles mutually-exclusive sparse features. Leaf-wise (best-first) growth. Faster training than XGBoost on large datasets.
- **Relevance**: The ensemble to use for GOSDT-Guesses threshold generation (binarization recipe). Also the primary accuracy benchmark.

### prokhorenkova-etal-2018
- **Title**: CatBoost: Unbiased Boosting with Categorical Features
- **Authors**: Prokhorenkova, Gorishniy, Shcherbakov, Filimonov
- **Year**: 2018
- **Venue**: NeurIPS
- **Quality**: recommended
- **Topics**: gradient-boosting, ensemble, tabular-ml
- **PDF**: none
- **Key finding**: Ordered boosting to combat target leakage from prediction-shift. Categorical-feature target encoding via random permutations. Oblivious (symmetric) trees enabling fast inference. 8,800 stars on catboost/catboost (May 2026).
- **Relevance**: Alternative ensemble baseline; oblivious trees are an interesting intermediate between full trees and optimal trees.

### grinsztajn-oyallon-varoquaux-2022
- **Title**: Why Do Tree-Based Models Still Outperform Deep Learning on Typical Tabular Data?
- **Authors**: Grinsztajn, Oyallon, Varoquaux
- **Year**: 2022
- **Venue**: NeurIPS Datasets and Benchmarks
- **Quality**: essential
- **Topics**: tabular-ml, ensemble, deep-learning
- **PDF**: none
- **Key finding**: 48 datasets with tuned hyperparameters. Tree-based models remain state-of-the-art on medium-sized tabular data (~10K samples). Three critical inductive biases: robustness to uninformative features, preservation of feature orientation (no rotational invariance), piecewise-constant targets easier to fit via partition.
- **Relevance**: Justifies tree-based approaches for the vol panel (tabular, ~5-20K rows, mixed informative/uninformative features). Deep learning not expected to beat trees here.

### carreira-perpinnan-tavallali-2018
- **Title**: TAO: Tree Alternating Optimization
- **Authors**: Carreira-Perpinnan, Tavallali
- **Year**: 2018
- **Venue**: NeurIPS
- **Quality**: recommended
- **Topics**: optimal-trees, distillation
- **PDF**: none
- **Key finding**: Alternating optimization with differentiable surrogates for fixed-structure tree optimization. Produces sparser, more accurate single trees and small forests than CART.
- **Relevance**: Alternative to exact optimal methods; useful if exact optimization is too slow and you want a middle ground between greedy and exact.

### carreira-perpinnan-tavallali-2023-fao
- **Title**: Forest Alternating Optimization
- **Authors**: Carreira-Perpinnan, Tavallali
- **Year**: 2023
- **Venue**: CVPR
- **Quality**: optional
- **Topics**: optimal-trees, ensemble, distillation
- **PDF**: none
- **Key finding**: Extends TAO to forest optimization; optimizes each tree in a fixed-structure forest via alternating optimization. Smaller forests with competitive accuracy.
- **Relevance**: Relevant if building small, interpretable forests rather than single trees.

### rudin-2019
- **Title**: Stop Explaining Black Box Machine Learning Models for High Stakes Decisions and Use Interpretable Models Instead
- **Authors**: Rudin
- **Year**: 2019
- **Venue**: Nature Machine Intelligence 1:206-215
- **Quality**: essential
- **Topics**: interpretability, rashomon, foundational
- **PDF**: none
- **Key finding**: The foundational argument: for structured/tabular data, the accuracy-interpretability tradeoff is often illusory. Post-hoc explanations (SHAP, LIME) are unstable, unfaithful, and manipulable. Inherently interpretable models should be preferred for high-stakes decisions.
- **Relevance**: Motivational framework for the entire Rashomon/optimal-tree project direction. Cite in any writeup.

### rudin-etal-2022-survey
- **Title**: Interpretable Machine Learning: Fundamental Principles and 10 Grand Challenges
- **Authors**: Rudin, Chen, Chen, Huang, Semenova, Zhong
- **Year**: 2022
- **Venue**: Statistics Surveys 16:1-85
- **Quality**: recommended
- **Topics**: interpretability, rashomon
- **PDF**: none
- **Key finding**: Comprehensive survey establishing interpretability principles. Trees with <=10 leaves and depth <=5 are reliably human-interpretable; 30+ leaves stretches comprehension.
- **Relevance**: Sets the interpretability target: depth 4-5, 8-32 leaves for the vol tree. Reference for operationalizing "interpretable" in a financial context.

### costa-pedreira-2023
- **Title**: Recent Advances in Decision Trees: An Updated Survey
- **Authors**: Costa, Pedreira
- **Year**: 2023
- **Venue**: Information Fusion
- **Quality**: recommended
- **Topics**: optimal-trees, interpretability, tabular-ml
- **PDF**: none
- **Key finding**: Survey confirming that DP+BnB with specialized depth-2 solvers and analytical bounds dominate for axis-aligned optimal trees. Trees with <=10 leaves are reliably human-interpretable.
- **Relevance**: Literature survey reference; confirms the STreeD/MurTree lineage as state-of-the-art for axis-aligned trees.

### aghaei-azizi-vayanos-2019
- **Title**: Fair Classification via Mixed-Integer Programming
- **Authors**: Aghaei, Azizi, Vayanos
- **Year**: 2019
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees, fairness
- **PDF**: none
- **Key finding**: MIP-based FairTree for statistical parity, predictive equality, equal opportunity, equalized odds. First formal fairness-constrained optimal tree.
- **Relevance**: Shows optimal trees can incorporate constraints; relevant methodology if adding monotonicity constraints to vol trees.

### jo-etal-2023
- **Title**: Learning Optimal Fair Classification Trees
- **Authors**: Jo, Aghaei, Benson, Gomez, Vayanos
- **Year**: 2023
- **Venue**: FAccT
- **Quality**: optional
- **Topics**: optimal-trees, fairness
- **PDF**: none
- **Key finding**: Extends fair optimal trees with stronger MIP formulations.
- **Relevance**: Tangential; demonstrates the flexibility of constrained tree optimization.

### popov-morozov-babenko-2020
- **Title**: Neural Oblivious Decision Ensembles for Deep Learning on Tabular Data
- **Authors**: Popov, Morozov, Babenko
- **Year**: 2020
- **Venue**: ICLR
- **Quality**: recommended
- **Topics**: deep-learning, ensemble, tabular-ml
- **PDF**: none
- **Key finding**: NODE generalizes CatBoost's oblivious decision trees with end-to-end gradient training. Each "tree" uses the same split feature/threshold across all nodes at a given depth, enabling differentiable training.
- **Relevance**: Neural-tree hybrid baseline; not interpretable but shows how tree structure can be embedded in deep learning. Comparison point for the accuracy-interpretability tradeoff.

### arik-pfister-2021
- **Title**: TabNet: Attentive Interpretable Tabular Learning
- **Authors**: Arik, Pfister
- **Year**: 2021
- **Venue**: AAAI
- **Quality**: recommended
- **Topics**: deep-learning, tabular-ml, interpretability
- **PDF**: none
- **Key finding**: Sequential attention-based feature selection; tree-inspired but actually a neural architecture. Claims interpretability via attention masks.
- **Relevance**: Neural "tree-like" baseline; attention masks provide some interpretability but are not truly inherent like decision tree paths.

### quinlan-1992-m5
- **Title**: Learning with Continuous Classes
- **Authors**: Quinlan
- **Year**: 1992
- **Venue**: Australian Joint Conference on AI
- **Quality**: optional
- **Topics**: regression-trees, foundational
- **PDF**: none
- **Key finding**: M5 model trees: greedy trees with linear models in the leaves. Cubist is the refined commercial version. First practical linear-leaf tree algorithm.
- **Relevance**: Historical predecessor to STreeD piecewise-linear regression. STreeD is the first provably optimal model-tree algorithm.

### meinshausen-2006
- **Title**: Quantile Regression Forests
- **Authors**: Meinshausen
- **Year**: 2006
- **Venue**: JMLR 7:983-999
- **Quality**: recommended
- **Topics**: regression-trees, ensemble, quantile-trees
- **PDF**: none
- **Key finding**: Random forests extended to predict conditional quantiles rather than means. Uses the distribution of training observations in each leaf.
- **Relevance**: Relevant for risk-sensitive vol forecasting (predicting high quantiles of future RV). Non-optimal baseline for quantile prediction.

### lemaire-aglin-nijssen-2024
- **Title**: Optimal Interpretable Quantile Regression Trees
- **Authors**: Lemaire, Aglin, Nijssen
- **Year**: 2024
- **Venue**: IDA
- **Quality**: recommended
- **Topics**: optimal-trees, regression-trees, quantile-trees
- **PDF**: none
- **Key finding**: Optimal decision trees for quantile regression. Produces interpretable trees predicting specific quantiles of the conditional distribution.
- **Relevance**: Directly applicable if predicting tail quantiles of RV (e.g., P(RV > threshold)) rather than mean RV.

### chatterjee-goswami-2021
- **Title**: Adaptive Estimation of Multivariate Piecewise Polynomials and Bounded Variation Functions by Optimal Decision Trees
- **Authors**: Chatterjee, Goswami
- **Year**: 2021
- **Venue**: Annals of Statistics
- **Quality**: optional
- **Topics**: regression-trees, np-hardness
- **PDF**: none
- **Key finding**: Theoretical risk bounds for dyadic CART; minimax-optimal rates for piecewise-constant and bounded-variation function classes.
- **Relevance**: Theoretical justification for regression tree approximation quality; not directly practical.

### donoho-1997
- **Title**: CART and Best-Ortho-Basis: A Connection
- **Authors**: Donoho
- **Year**: 1997
- **Venue**: Annals of Statistics 25(5):1870-1911
- **Quality**: optional
- **Topics**: regression-trees, foundational
- **PDF**: none
- **Key finding**: Connects dyadic CART to wavelet bases; theoretical risk bounds for piecewise-constant tree approximation.
- **Relevance**: Foundational theory for regression tree approximation; not directly applicable to the project.

### nijssen-fromont-2007
- **Title**: Mining Optimal Decision Trees from Itemset Lattices
- **Authors**: Nijssen, Fromont
- **Year**: 2007
- **Venue**: KDD
- **Quality**: optional
- **Topics**: optimal-trees, foundational
- **PDF**: none
- **Key finding**: DL8: optimal decision trees via itemset mining. Ancestor of DL8.5; established the connection between frequent itemset mining and optimal tree construction.
- **Relevance**: Historical context for the DL8.5/MurTree/STreeD lineage.

### komusiewicz-etal-2023
- **Title**: Optimal Decision Tree Ensembles via Fixed-Parameter Tractability [verify exact title against ICML 2023 proceedings]
- **Authors**: Komusiewicz, Kunz, Sommer, Sorge
- **Year**: 2023
- **Venue**: ICML
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness, ensemble
- **PDF**: none
- **Key finding**: Optimal tree ensembles computable in O((6*delta*D*S)^S * poly), where S is number of cuts, D largest domain size, delta max feature differences between examples. First FPT result for optimal tree ensembles.
- **Relevance**: Theoretical foundation for optimal ensemble construction; not yet practical but shows optimal ensembles are tractable in principle.

### ordyniak-szeider-2021
- **Title**: Parameterized Complexity of Small Decision Tree Learning
- **Authors**: Ordyniak, Szeider
- **Year**: 2021
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness
- **PDF**: none
- **Key finding**: FPT and W-hardness results for decision tree learning parameterized by tree size, number of features, and other structural parameters.
- **Relevance**: Theoretical context; confirms that practical tractability depends on specific parameter combinations.

### eiben-etal-2023
- **Title**: On the Parameterized Complexity of Learning Decision Trees
- **Authors**: Eiben, Ganian, Koana, Ordyniak, Suchy
- **Year**: 2023
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness
- **PDF**: none
- **Key finding**: Refined parameterized complexity landscape for decision tree learning; establishes tighter FPT/W[1]-hard boundaries.
- **Relevance**: Theoretical context for understanding which problem parameters make optimal trees tractable.

### gahlawat-zehavi-2024
- **Title**: On the Parameterized Complexity of Learning Optimal Decision Trees
- **Authors**: Gahlawat, Zehavi
- **Year**: 2024
- **Venue**: AAAI
- **Quality**: optional
- **Topics**: optimal-trees, np-hardness
- **PDF**: none
- **Key finding**: Additional W-hardness results closing gaps in the parameterized complexity map for optimal decision trees.
- **Relevance**: Completes the theoretical picture; confirms that depth and feature count are the key complexity drivers.
```

- [ ] **Step 7: Add new topic tags to controlled vocabulary**

Append these tags to the existing vocabulary line at the bottom of the file (currently line 1049):

Add: `regression-trees`, `interpretability`, `tabular-ml`, `fairness`, `distillation`, `survival-trees`, `quantile-trees`, `np-hardness`

- [ ] **Step 8: Verify and commit**

Count `###` headings in category H. Should be ~63-65 entries (12 enriched originals, net +1 from the DL8.5/MurTree split, plus ~50 new). Verify no duplicate slugs exist.

```bash
git add reference/bibliography.md
git commit -m "feat: add ~50 decision tree bibliography entries, enrich 12 existing, add topic tags"
```

---

## Chunk 2: Feature file appends and project proposals

### Task 3: Append to `notes/features/optimal-feature-set.md`

**Files:**
- Read + Append: `notes/features/optimal-feature-set.md` (currently 281 lines, existing `## Deep Research Findings (2026-05-06)` at line 267)
- Source: `notes/deep-research-decision-trees.md` Part 2 sections 2.2, 2.4, 2.5

Check for overlap: the 2026-05-06 section covers VIC basics and feature construction pitfalls. The new content is more detailed on Rashomon applications, pipeline design, and novelty. No overlap in specific content -- append as a new dated section.

- [ ] **Step 1: Append findings**

Append to the end of `notes/features/optimal-feature-set.md`:

```markdown

## Deep Research Findings (2026-05-07)

**Rashomon-set value for feature analysis (decision tree deep research):**
- Feature interchangeability detection: VIX, V2X, VVIX, MOVE, RV lags, ATM IV, IV-RV spread, term-structure slope are all near-substitutes. Single-model importance (gain, permutation, SHAP) is unstable across refits because of this redundancy
- RID (Donnelly et al. 2023, NeurIPS) delivers a stable importance distribution over (Rashomon set x bootstrap) with consistency theorems and finite-sample error rates (`donnelly-katta-rudin-browne-2023` in bibliography)
- VIC (Dong & Rudin 2020) visualizes substitution structure directly: features with non-overlapping importance clouds are robustly distinct
- Regime-stable model selection: train TreeFARMS/RESPLIT on rolling-window data; intersect Rashomon sets across regimes to find trees near-optimal in every regime -- robust to non-stationarity
- Ex-ante stress testing: prediction multiplicity at any input quantifies the range of predictions across all defensible models -- useful for risk reporting
- Constraint satisfaction post-hoc: prefer trees in the Rashomon set that are monotone in VIX (VIX up -> RV up), do not split on a flagged feature, or satisfy any other constraint -- without retraining

**Interpretable vol forecasting pipeline (from decision tree applicability assessment):**
1. Feature engineering: HAR lags, HARQ realized-quarticity, signed semivariances, BNS jumps, VIX/VVIX, volume/spread, macro (ADS, EPU), cross-asset (SPY corr, sector RV)
2. Binarization (for GOSDT/SPLIT family only): GOSDT-Guesses LightGBM threshold guesser, cap ~300 binary features
3. Target: log(RV_{t+1}) or RV_{t+1:t+5} for weekly (ML gains larger at longer horizons)
4. Train: STreeDPiecewiseLinearRegressor depth <=5, elastic-net leaves, cost-complexity tuned via purged blocked k-fold CV
5. Rashomon analysis: TreeFARMS/RESPLIT within epsilon=2% MSE of optimum; compute RID per feature; filter for monotonicity and sparsity (<=12 leaves)
6. Evaluate: walk-forward MSE, QLIKE, MAE; DM tests vs HAR/HARQ/LightGBM; Rashomon prediction range during regime breaks (Mar-2020, Volmageddon)
7. Production: pickle tree + feature pipeline, re-train weekly on rolling 5-yr window, monitor Rashomon-set drift

**Novelty (May 2026):**
- No peer-reviewed paper, preprint, Kaggle notebook, or industry blog has applied any optimal-tree or Rashomon-set method to realized-volatility forecasting, return prediction, or any financial time-series
- Closest published applications are to cross-sectional credit risk (FICO HELOC) and criminal justice (COMPAS)
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/optimal-feature-set.md
git commit -m "docs: append Rashomon pipeline and novelty findings to optimal-feature-set"
```

---

### Task 4: Append to `notes/features/har-components.md`

**Files:**
- Read + Append: `notes/features/har-components.md` (currently 28 lines, existing `## Deep Research Findings (2026-05-06)` at line 15)
- Source: `notes/deep-research-decision-trees.md` Part 2 section 2.3

- [ ] **Step 1: Append findings**

Append to the end of `notes/features/har-components.md`:

```markdown

## Deep Research Findings (2026-05-07)

**Accuracy comparison: optimal trees vs HAR vs ensembles (decision tree research):**
- Christensen, Siggaard & Veliyev (Journal of Financial Econometrics 2023; T=4,257 trading days, 29 Jan 2001 to 31 Dec 2017, 29 DJIA constituents): relative MSE vs HAR=1.000 baseline -- bagging 0.891, gradient boosting 0.958, RF 0.986, NN ensembles 0.954-0.990. With full features (IV, EA, VIX, HSI): RF 0.901, GB 0.962, NN 0.885-0.944, bagging 0.961 (`christensen-siggaard-veliyev-2023` in bibliography)
- Best estimate for interpretable optimal trees: depth-4-5 STreeD piecewise-linear should achieve ~2-5% higher MSE than a tuned LightGBM, while remaining a single inspectable tree with 8-32 leaves (extrapolated -- not yet measured, must verify on own data)
- An interpretable optimal tree should comfortably beat HAR: bagging alone beats HAR by ~10% on 5-min RV
- Van der Linden et al. 2025 (180 datasets): optimal trees ~1-2 percentage points accuracy improvement vs greedy CART at depth 3-4 (`van-der-linden-etal-2025-benchmark` in bibliography)
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/har-components.md
git commit -m "docs: append optimal tree accuracy comparison to har-components"
```

---

### Task 5: Append to `notes/project-proposals.md`

**Files:**
- Read + Append: `notes/project-proposals.md` (currently 120 lines, ends with Caveat 8 at line 120)
- Source: `notes/deep-research-decision-trees.md` Part 2 sections 2.1, 2.4, Recommendations, Caveats

- [ ] **Step 1: Append methodology assessment**

Append to the end of `notes/project-proposals.md`:

```markdown

---

## Decision Tree Methodology Assessment (2026-05-07)

> Source: decision tree deep research survey
> Full landscape survey: `notes/deep-research-decision-trees.md`
> Bibliography: `reference/bibliography.md` (category H)

### Recommended Methods for Vol Regression (5K-20K daily obs x 20-80 features)

In priority:
1. **STreeD piecewise-linear regression** (`pystreed`, ICML 2024) -- native continuous features, elastic-net leaves, depth-2 specialized solver. Closest fit to the vol task.
2. **OSRT** (`gosdt` regression mode, AAAI 2023) -- fully provably-optimal piecewise-constant baseline.
3. **STreeD piecewise-constant** (`pystreed`) -- provably optimal, scalable to >=100K rows.
4. **ConTree** (`pycontree`, AAAI 2025) -- for classification framings (vol regime, sign-of-return, vol-up/down) on continuous features without binarization.
5. **SPLIT / LicketySPLIT** (ICML 2025) -- fast iteration during research; classification only currently.

**Avoid**: pure MIP (too slow for 20K rows), pure SAT (perfect-classification only), Quant-BnB beyond depth 3.

**Binarization recipe** (only for GOSDT/SPLIT family): GOSDT-Guesses LightGBM threshold guesser turns 80 continuous features into ~200-500 binary thresholds prioritized by gradient-boosted importance. Cap at ~300 binary features.

### Implementation Roadmap

**Stage 1 (week 1-2): Baseline & feasibility.** Implement HAR / HAR-X / HARQ baselines and a tuned LightGBM regressor. Compute walk-forward MSE/QLIKE. This sets the lower and upper accuracy bounds.

**Stage 2 (week 2-4): Optimal-tree drop-in.** Install `pystreed` and fit `STreeDPiecewiseLinearRegressor` at depths 3, 4, 5 with cost-complexity tuned via purged blocked k-fold CV. Compare to depth-matched CART and to OSRT. Report MSE, QLIKE, and tree size. **Threshold**: if STreeD MSE is within 5% of LightGBM at <=16 leaves, proceed to Stage 3; if it lags by >10%, fall back to GOSDT-Guesses on a binarized representation or accept the LightGBM/explanation pipeline.

**Stage 3 (week 4-8): Rashomon-set analysis.** For a classification framing (volatility-up vs. flat vs. down), enumerate the TreeFARMS or RESPLIT Rashomon set within epsilon=2% of optimum. Compute the Rashomon Importance Distribution. Identify trees that are monotone in VIX and split on at most 8 unique features. Report the prediction range across the Rashomon set during COVID-March-2020 and Volmageddon regime breaks. **Threshold**: if RID is materially more stable than LightGBM SHAP across rolling windows (Spearman rank correlation ≥ 0.8 between adjacent windows for top features), this is paper-worthy material.

**Stage 4 (paper / production).** Draft a paper for ICAIF, NeurIPS Finance Workshop, or Journal of Financial Econometrics showing the interpretable-optimal-tree-with-Rashomon-set methodology beats HAR economically and is robust across regimes.

**Default if research time is constrained:** use STreeD piecewise-linear regression at depth 4 with monotonicity constraints + a TreeFARMS-derived RID for variable importance. This delivers 80% of the value of the full pipeline at <20% of the effort.

### Caveats (Decision Tree Research)

9. **Speculative claims marked**: the 2-5% MSE penalty estimate vs. LightGBM is extrapolated, not measured -- verify on own data.
10. **No regression-Rashomon library is yet production-ready**: SORTeD's regression extension is anticipated but not released as of May 2026; regression Rashomon-set work requires custom code on top of STreeD.
11. **Binarization caveat**: GOSDT/SPLIT/MurTree/TreeFARMS require binary features; the threshold-guessing preprocessor introduces a (typically small) optimality gap. ConTree and STreeD piecewise-linear are the only continuous-native optimal methods.
12. **Time-series leakage**: standard k-fold CV is invalid; use purged blocked k-fold or walk-forward. None of the optimal-tree libraries enforce this -- the user must wrap them.
13. **GitHub star counts** are May 2026 snapshots: GOSDT (57), TreeFARMS (47), scikit-learn (65,877), XGBoost (28,300), CatBoost (8,800).
14. **The "no financial-time-series application" finding is a negative result** based on thorough search; publications may appear during the project -- periodic re-check of arXiv cs.LG and SSRN q-fin.ST is advised.
15. **Grinsztajn-Oyallon-Varoquaux dataset count**: arXiv v1 says 45 datasets; published NeurIPS 2022 says 48. Either is correct depending on version cited.
16. **Van der Linden et al. (arXiv:2409.12788) is still a preprint** as of May 2026, not yet peer-reviewed, though widely cited.
17. **MAPTree's claim to "beat optimal trees"** is on Bayesian MAP with a BCART prior -- a different objective than regularized-misclassification, so comparisons to GOSDT/MurTree are not apples-to-apples.
18. **No GPU acceleration** for any optimal-tree library -- CPU-bound training. For 5-20K rows this is not limiting; at 1M+ rows expect overnight runs at depth 4.
```

- [ ] **Step 2: Verify**

Confirm the file now has: original 4 proposals + recommendations + 8 vol caveats (from 2026-05-06) + decision tree methodology section + implementation roadmap + 10 new caveats (numbered 9-18 continuing from the vol caveats).

- [ ] **Step 3: Commit**

```bash
git add notes/project-proposals.md
git commit -m "docs: append decision tree methodology assessment and roadmap to project proposals"
```

---

### Task 6: Append to `notes/research-index.md`

**Files:**
- Append: `notes/research-index.md` (currently 20 lines)

- [ ] **Step 1: Append new entry**

Append to the end of `notes/research-index.md`:

```markdown

## 2026-05-07: State of the Art in Decision Trees

- **Source prompt**: `notes/deep-research-prompt-decision-trees.md`
- **Raw output**: `notes/deep-research-decision-trees.md` (trimmed to landscape survey after extraction)
- **Extracted to**:
  - `reference/bibliography.md` -- ~50 new entries in category H, 12 existing entries enriched, 8 new topic tags
  - `notes/project-proposals.md` -- decision tree methodology assessment, implementation roadmap, 10 caveats
  - `notes/features/optimal-feature-set.md` -- Rashomon pipeline design, feature interchangeability, novelty confirmation
  - `notes/features/har-components.md` -- accuracy comparison (optimal trees vs HAR vs LightGBM)
```

- [ ] **Step 2: Commit**

```bash
git add notes/research-index.md
git commit -m "docs: add decision tree extraction to research index"
```

---

## Chunk 3: Source file trimming

### Task 7: Trim `notes/deep-research-decision-trees.md`

**Files:**
- Modify: `notes/deep-research-decision-trees.md` (currently 336 lines)

This is the final task. All content has been extracted to its target locations. Now trim the source file.

- [ ] **Step 1: Add cross-reference block after Executive Summary**

After line 11 (end of Executive Summary, before the `---` separator at line 13), insert:

```markdown

---
> **Bibliography**: entries appended to `reference/bibliography.md` (category H)
> **Project proposals**: methodology assessment appended to `notes/project-proposals.md`
> **Research index**: `notes/research-index.md`
---
```

- [ ] **Step 2: Remove extracted sections**

Delete everything from the `---` separator before Part 2 onwards (starting at line 226 in the original file, which shifts to ~232 after the cross-reference block insertion). This removes:
1. Part 2 "Applicability Assessment" (now in `notes/project-proposals.md` and `notes/features/optimal-feature-set.md`)
2. "Recommendations" section (now in `notes/project-proposals.md`)
3. "Caveats" section (now in `notes/project-proposals.md`)

What remains: Executive Summary (with cross-reference block) + Sections A-H landscape survey.

- [ ] **Step 3: Verify the trimmed file**

The file should now contain:
- Line 1: Title
- Lines 3-11: Executive Summary
- Cross-reference block (inserted)
- `---` separator
- Sections A-H landscape survey (## A through ## H)
- Nothing after Section H

Total: ~230 lines (down from 336).

- [ ] **Step 4: Commit**

```bash
git add notes/deep-research-decision-trees.md
git commit -m "refactor: trim extracted sections from decision tree research, add cross-references"
```

---

## Execution Notes

**Parallelization:** Tasks 1-2 must run sequentially (Task 2 adds new entries after Task 1 enriches existing ones -- both modify the same file section). Tasks 3-6 are all independent of each other and of Tasks 1-2. Task 7 (trim) must run last.

**Recommended parallel groups:**
- Group A: Tasks 1+2 (bibliography, sequential)
- Group B: Tasks 3+4+5+6 (feature files, proposals, index -- all independent)
- Group C: Task 7 (trim, after A+B complete)

Groups A and B can run in parallel since they touch different files.

**No tests:** This is a content extraction task. Verification is done by checking entry counts (Task 2 Step 8), confirming no content falls through the cracks, and reading the trimmed source file to confirm it's coherent.

**Largest risk:** Task 2 (new bibliography entries) is by far the most labor-intensive (~50 entries to format). Budget most of the time there.
