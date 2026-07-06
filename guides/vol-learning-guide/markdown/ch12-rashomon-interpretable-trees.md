# Chapter 12. Rashomon Sets and Interpretable Trees

You have built a volatility model, run SHAP, and found that VIX is the most important feature. You refit on a slightly different training window and now ATM implied volatility takes over. A third refit: lagged $\operatorname{RV}_{t-1}$ wins. Which feature is *actually* important? The unsettling answer is that any single model's feature importance is a sample of size one from a large population of equally-good models. Drawing conclusions from that single sample is exactly the kind of reasoning we would reject in any other statistical context.

This chapter introduces a principled alternative. Instead of asking "what does *my* model say is important?" we ask "what do *all* near-optimal models agree is important?" The set of all such models is called the **Rashomon set**, and the tools for analyzing it give us something SHAP cannot: provably stable feature importance that does not change when you perturb the training window by a few days.

> **Prereq: What You Need Before This Chapter**
>
> - **[Chapter 11](ch11-tree-methods-vol.md)**. Decision tree fundamentals: how splits are chosen, how CART grows a tree, what makes a tree "optimal." The distinction between greedy (top-down) and globally optimal (branch-and-bound) tree construction.
> - **SHAP basics**. The idea that SHAP assigns each feature a contribution to each individual prediction, and that global SHAP importance is obtained by averaging $|\phi_i|$ across predictions. You should know what a SHAP summary plot looks like, but you do *not* need to understand the Shapley value derivation in detail.
> - **Feature importance concepts**. Permutation importance (shuffle a feature, measure how much loss increases) and split-count importance (how often a feature appears in tree splits). Both are covered in [Chapter 11](ch11-tree-methods-vol.md).


## The Problem with Single-Model Explanations

Feature importance from a single model is not a fact about the data. It is a fact about *one model fit to the data*. If there are many models that fit the data almost equally well, each may assign very different importances, and the one we happen to report is determined by arbitrary choices: the random seed, the exact train/test split boundary, the hyperparameter grid, even the order in which features are processed.

### Why SHAP Importance Is Unreliable with Near-Substitute Features

Consider two features that are highly correlated: VIX (the CBOE volatility index) and the ATM implied volatility from the SPX options surface. Both carry similar information about the market's forward-looking volatility expectation. A tree model must choose one or the other at each split. If the model happens to split on VIX first, VIX gets credit for the variance it explains, and ATM IV gets little credit because the residual information it adds is small. Reverse the split order and ATM IV gets the credit.

SHAP values (Lundberg and Lee, 2017) partially address this by considering all feature orderings. For a model $f$ and a prediction at input $x$, the SHAP value for feature $i$ is the unique additive attribution satisfying local accuracy, missingness, and consistency:

$$
  \phi_i(f, x) = \sum_{S \subseteq F \setminus \{i\}}
    \frac{|S|!\,(|F| - |S| - 1)!}{|F|!}
    \bigl[f_x(S \cup \{i\}) - f_x(S)\bigr],
$$

where:

- $F$ is the full feature set, $|F| = M$
- $S$ is a subset of features *excluding* feature $i$
- $f_x(S) = \mathbb{E}[f(z) \mid z_S = x_S]$ is the expected prediction when only features in $S$ are observed

> **Intuition: Why SHAP Doesn't Fully Solve the Problem**
>
> SHAP computes importances for all feature orderings, but it does so for a *single fixed model* $f$. The problem is upstream: the model $f$ itself is just one of many near-optimal models. A different near-optimal model $f'$ with the same predictive accuracy may produce entirely different SHAP values, especially for correlated features. Averaging over orderings within one model does not average over the space of *models*.

### Importance Instability in Practice

The instability is not hypothetical. In volatility forecasting, features like VIX, $\operatorname{VVIX}$, ATM $\operatorname{IV}$, the 25-delta skew, and lagged $\operatorname{RV}_{t-1}$ are all moderately to highly correlated. A gradient-boosted tree fit on 2017--2021 data might rank VIX as the top feature, while the same model fit on 2017--2022 data (just one extra year) might rank $\operatorname{RV}_{t-1}$ first and demote VIX to third. The model's accuracy barely changes between these two fits, but the "feature importance story" changes completely.

This creates a serious practical problem. In an internship setting, you will present your model's feature importance to a desk or to a portfolio manager. If the ranking shuffles every time you retrain, your explanation is not credible. What you need is a statement like: "Across *all* models within 2% of optimal accuracy, VIX and ATM IV are interchangeable substitutes, but lagged RV is always important." That statement requires looking at all good models, not just one.


## The Rashomon Set

The idea of many equally-good models was articulated by Leo Breiman, who called it the **Rashomon effect**, a reference to the Akutagawa story (and Kurosawa film) in which multiple witnesses give contradictory but individually plausible accounts of the same event. The **Rashomon set** formalizes this: it is the collection of all models whose loss is close to the best achievable loss.

### Formal Definition

We need three ingredients: a model class $\mathcal{F}$ (e.g., all decision trees of depth $\leq d$), a dataset $(\mathbf{X}, \mathbf{y})$, and a reference model $f^*$ that achieves the best loss within $\mathcal{F}$.

> **Definition: $\epsilon$-Rashomon Set (Xin et al., 2022)**
>
> Given a model class $\mathcal{F}$, a benchmark model $f^* \in \mathcal{F}$, and a tolerance $\epsilon > 0$, the **$\epsilon$-Rashomon set** is
>
> $$
>   \mathcal{R}(\epsilon, f^*, \mathcal{F})
>     = \bigl\{f \in \mathcal{F} \;\big|\;
>       L(f) \leq (1 + \epsilon)\,L(f^*)\bigr\},
> $$
>
> where $L(f)$ is the loss (e.g., misclassification rate, squared error) of model $f$ evaluated on the training data.

The symbols:

- $\epsilon$: the tolerance parameter. Setting $\epsilon = 0.02$ means we accept models within 2% of the best loss. Typical values in the literature range from $0.01$ to $0.10$ (Xin et al., 2022).
- $f^*$: the reference model, usually the empirical risk minimizer within $\mathcal{F}$ (e.g., found by GOSDT for optimal sparse trees).
- $L(f^*)$: the best achievable loss in the class.

For decision trees specifically, Xin et al. (2022) define the objective function as the misclassification loss plus a sparsity penalty:

$$
  \operatorname{Obj}(t, \mathbf{X}, \mathbf{y}) =
    \underbrace{\frac{1}{n}\sum_{i=1}^{n} \mathbb{1}[\hat{y}_i \neq y_i]}_{\text{misclassification loss}}
    + \underbrace{\lambda \, H_t}_{\text{sparsity penalty}},
$$

where:

- $\hat{y}_i$ is the prediction of tree $t$ for observation $i$
- $H_t$ is the number of leaves in tree $t$
- $\lambda > 0$ is a regularization parameter penalizing complexity

The Rashomon set threshold then becomes $\theta_\epsilon = (1 + \epsilon) \times \operatorname{Obj}(t_{\text{ref}}, \mathbf{X}, \mathbf{y})$, and any tree $t$ with $\operatorname{Obj}(t, \mathbf{X}, \mathbf{y}) \leq \theta_\epsilon$ is in the set (Xin et al., 2022).

> **Project Connection: Rashomon Sets for Regression**
>
> Our volatility project uses squared-error loss (or QLIKE), not misclassification. The Rashomon set concept applies identically: replace $L(f)$ with $\operatorname{QLIKE}$ or MSE and everything carries through. The computational algorithms (TreeFARMS, SPLIT) currently target classification trees, but the conceptual framework (and the VIC/RID analysis tools) is loss-function agnostic.

### How Large Is the Rashomon Set?

The hypothesis space of sparse trees is enormous. For trees of depth at most 4 with only 10 binary features, the number of possible trees exceeds $9.3 \times 10^{20}$ (Xin et al., 2022). The Rashomon set, fortunately, is usually a tiny fraction of this space, but "tiny fraction" can still be a very large number in absolute terms.

Xin et al. (2022) report that on the COMPAS dataset with $\lambda = 0.005$ and a 15% Rashomon threshold, the set contains approximately $10^{12}$ trees. On smaller datasets (Monk2, Bar), sets of $10^5$ to $10^8$ trees are typical. The key insight from their experiments is that *natural baselines (BART, Random Forest, CART + sampling) find at best a tiny sliver of the Rashomon set*: they recover only hundreds to thousands of trees when the true set contains millions or more.


## Optimal Sparse Decision Trees

Before we can enumerate *all* near-optimal trees, we must be able to find *one* provably optimal tree.

### Why Not Just Use CART?

CART (Breiman et al., 1984) and other greedy algorithms build trees top-down, choosing the best split at each node independently. This is fast ($O(npd)$ for $n$ samples, $p$ features, depth $d$), but greedy splits can be suboptimal. Babbar et al. (2025) show that greedy methods exhibit an average gap of 1--2 percentage points from the optimum, and on some datasets (e.g., COMPAS) the gap can reach 10 percentage points.

The problem with greedy construction is that a split that looks best at the root may set up poor options downstream. Global optimization avoids this by searching the *entire* space of trees up to a given depth.

### Branch-and-Bound with Dynamic Programming

Modern optimal tree algorithms (GOSDT, MurTree) solve the optimization problem exactly:

$$
  \mathcal{L}^*(D, d, \lambda) = \min_{T \in \mathcal{T}}
    L(T, D, \lambda) \quad \text{s.t. } \operatorname{depth}(T) \leq d,
$$

where $L(T, D, \lambda) = \frac{1}{N}\sum_{i=1}^{N} \ell(T(\mathbf{x}_i), y_i) + \lambda\,S(T)$ is the regularized loss and $S(T)$ is the number of leaves (Babbar et al., 2025).

The key insight behind branch-and-bound is that the optimal solution for a dataset $D$ at depth $d'$ depends on the solutions for subsets $D(f)$ and $D(\bar{f})$ at depth $d'-1$, where $f$ is the splitting feature. Starting from the root, the algorithm considers all candidate features, tracking upper and lower bounds on the objective at each split. When the lower bound of a subtree exceeds the current best upper bound, that entire subtree is pruned.

### SPLIT: Greedy Where It Doesn't Matter, Optimal Where It Does

A key empirical observation by Babbar et al. (2025) is that greedy splits near the *leaves* are almost always optimal, while greedy splits near the *root* often deviate from the optimum. This makes sense: near the leaves, there are only a few possible splits left, so the greedy choice among them is unlikely to be far from the best. Near the root, a bad split propagates errors through the entire tree.

SPLIT (Sparse Lookahead for Interpretable Trees) exploits this observation. It takes a **lookahead depth** parameter $d_l < d$ and performs full branch-and-bound optimization for splits up to depth $d_l$, then switches to greedy splitting for the remaining $d - d_l$ levels.

> **Key Result: SPLIT Runtime**
>
> For a dataset with $n$ samples, $k$ binary features, depth budget $d$, and lookahead depth $d_l$, SPLIT (Algorithm 2 in Babbar et al. (2025)) has runtime
>
> $$
>   \mathcal{O}\bigl(n(d - d_l)\,k^{d_l + 1} + n\,k^{d - d_l}\bigr).
> $$
>
> The polynomial-time variant, LicketySPLIT, achieves $O(nk^2 d^2)$, comfortably polynomial and dramatically faster than the $\mathcal{O}((2k)^d)$ worst case of fully optimal methods.

> **Project Connection: Interpretable Trees for Vol Forecasting**
>
> For our volatility project, a depth-5 tree with 10--15 features is a realistic interpretable baseline. An optimal tree of this size can be found in under a second with LicketySPLIT.

### STreeD: Piecewise-Linear Regression Trees

The optimal tree methods discussed so far assume each leaf predicts a *constant*: the mean of the training labels that fall into that leaf. This creates a staircase-shaped prediction function: the forecast jumps from one flat value to another at each split boundary. van den Bos et al. (2024) introduce **STreeD** (STreeD Regression Trees), a dynamic-programming framework that extends optimal regression trees to **piecewise-linear** leaf models. They develop three methods of increasing expressiveness:

1. **SRT-C** (piecewise-constant): An improved DP algorithm for constant-leaf regression trees with a specialized depth-two solver that achieves orders-of-magnitude speedups over previous optimal methods (e.g., 18$\times$ faster than OSRT on average).

2. **SRT-SL** (simple linear regression): The *first optimal method* for piecewise simple linear regression trees. Each leaf fits a one-variable linear model $y = \hat{\beta}_0 + \hat{\beta}_j x_j$, selecting the single best feature $j$ for that leaf. Ridge regularization prevents overfitting in small leaves.

3. **SRT-L** (multiple linear regression): The *first optimal method* for piecewise multiple linear regression trees. Each leaf fits a full linear model with elastic net regularization ($\ell_1 + \ell_2$ penalty), solved via coordinate descent.

The key idea behind SRT-SL is that each leaf selects *one* continuous feature and fits a simple linear regression with ridge regularization. The leaf-level objective for a leaf containing data subset $\mathcal{D}$ is:

$$
  \min_{j,\,\hat{\beta}_0,\,\hat{\beta}_j}
    \sum_{(x,\,b,\,y) \in \mathcal{D}}
    (y - \hat{\beta}_0 - x_j\,\hat{\beta}_j)^2
    + \gamma\,\hat{\beta}_j^2,
$$

where:

- $j$ is the index of the continuous feature selected for this leaf
- $\hat{\beta}_0$ is the intercept, $\hat{\beta}_j$ is the slope on feature $x_j$
- $\gamma > 0$ is the ridge regularization parameter
- The leaf selects whichever feature $j$ yields the smallest regularized SSE

The closed-form solutions for the optimal coefficients are:

$$
\begin{aligned}
  \hat{\beta}_j &= \frac{n\sum x_j y - \sum y \sum x_j}
    {n\sum x_j^2 - (\sum x_j)^2 + n\gamma},\\
  \hat{\beta}_0 &= \frac{\sum y}{n}
    - \hat{\beta}_j\,\frac{\sum x_j}{n},
\end{aligned}
$$

where all sums run over the instances in the leaf and $n = |\mathcal{D}|$.

> **Intuition: Why Piecewise-Linear Leaves Matter**
>
> A constant-leaf tree predicts $\bar{y}$ in each partition, creating a staircase function. A linear-leaf tree fits a slope within each partition, so it captures *local trends*. For volatility, this means a leaf can express "RV increases linearly with VIX within this regime" rather than just "RV is high in this regime." The tree handles the nonlinear regime boundaries (splits), and the linear models handle the smooth within-regime relationships.

**Scalability.** The depth-two algorithm from van den Bos et al. (2024) is the key to STreeD's performance advantage. By precomputing per-instance costs (the sums $\sum y$, $\sum y^2$, $\sum x_j$, $\sum x_j^2$, and $\sum x_j y$ for every feature $j$ and every data subset defined by pairs of binary splits), the depth-two solver avoids redundant traversals of the data. Remarkably, fitting a simple linear regression model per leaf (SRT-SL) costs almost nothing extra compared to fitting a constant (SRT-C), because the additional statistics ($\sum x_j$, $\sum x_j^2$, $\sum x_j y$) can be accumulated in the same pass.

**Interpretability.** Every SRT-SL prediction decomposes into two transparent components: (1) a root-to-leaf path of binary splits that determines which regime the input falls into, and (2) a one-variable linear formula in the leaf that produces the forecast. This is what the interpretability literature calls a **short linear formula**: the entire model is human-readable and can be written on a single page.

> **Project Connection: STreeD for Volatility Forecasting**
>
> SRT-SL is particularly appealing for our project. Imagine a depth-3 tree that splits on lagged-$\operatorname{RV}$ quintile at the root, then on a VIX threshold, creating 4--8 leaves. Within each leaf, a simple linear regression on one feature (e.g., $\operatorname{RV}_{t-1}$ or the VIX level) captures the local relationship. The result is an interpretable model that can express statements like: "In the high-vol, backwardated-VIX regime, tomorrow's RV increases by 0.15 for each unit increase in today's RV." This is far more informative than a constant prediction per regime, and every coefficient has a clear economic interpretation.


## Enumerating the Rashomon Set

Finding one optimal tree is step one. The real power comes from finding *all* near-optimal trees, the complete Rashomon set. This section covers three algorithms of increasing scalability.

### TreeFARMS: Exact Enumeration

TreeFARMS (Trees FAst RashoMon Sets) by Xin et al. (2022) was the first algorithm to *completely* enumerate the Rashomon set for sparse decision trees. It builds on the GOSDT branch-and-bound framework and modifies it in two key ways:

1. **Rashomon pruning.** Instead of pruning subproblems whose lower bound exceeds the optimal objective (as in standard GOSDT), TreeFARMS prunes those whose lower bound exceeds the *Rashomon threshold* $\theta_\epsilon$. This retains more of the search space: exactly the near-optimal region.

2. **Return all models.** Instead of returning only the single best tree, TreeFARMS returns every tree in the Rashomon set, stored in a compact **Model Set** data structure.

The Model Set representation is critical for scalability. A **Model Set Instance (MSI)** represents a subproblem paired with its objective value. Many trees share identical subtrees, and the Model Set exploits this by storing shared components once. The loss function for decision trees takes on a discrete set of values (approximately $n$ distinct values for $n$ training samples), while the number of trees in the Rashomon set can be orders of magnitude larger. By grouping trees with the same objective, TreeFARMS avoids massive data duplication.

> **Key Idea: TreeFARMS: From Optimization to Feasibility**
>
> Standard ML algorithms solve an *optimization* problem: find the single best model. TreeFARMS solves a *feasibility* problem: find all models within $\epsilon$ of the best. This reframing is the core contribution. Perhaps the tiny sacrifice in empirical risk makes the difference between a model that can be used (interpretable, fair, aligned with domain knowledge) and one that cannot.

**Limitations.** TreeFARMS provides exact enumeration but its runtime and memory scale exponentially with tree depth and the number of features. On the Bike dataset ($n \approx 17{,}000$, $k = 60$ binary features, depth 5), TreeFARMS requires approximately 700 seconds and over 50 GB of memory (Heile et al., 2025). On larger datasets, it runs out of memory entirely.

### RESPLIT: Fast Approximation via Greedy Leaves

Babbar et al. (2025) extend SPLIT to Rashomon set computation with the RESPLIT algorithm. The idea is simple: use SPLIT to find a set of "prefix trees" (partial trees optimized to the lookahead depth), then call TreeFARMS on each prefix to enumerate the near-optimal completions.

Because SPLIT uses greedy splits near the leaves, RESPLIT does not exhaustively search the full tree space. This makes it an *approximation*: it may miss some trees in the true Rashomon set. However, Babbar et al. (2025) show that the approximation is remarkably accurate. On six benchmark datasets, the Pearson correlation between variable importances computed from the RESPLIT-approximated Rashomon set and the full Rashomon set is nearly 1.0:

| Dataset | Full (s) | RESPLIT (s) | Speedup | $\tau$ (correlation) |
|---|---|---|---|---|
| COMPAS | 152 | 18 | $8\times$ | 1.000 |
| Spambase | 2,659 | 154 | $17\times$ | 0.930 |
| Netherlands | 4,255 | 216 | $20\times$ | 0.932 |
| HELOC | 5,564 | 337 | $17\times$ | 0.979 |
| HIV | 9,273 | 388 | $24\times$ | 0.959 |
| Bike | 14,330 | 194 | $74\times$ | 0.999 |

*Source: Table 1 in Babbar et al. (2025). Parameters: 10 bootstrapped datasets, $\lambda = 0.02$, $\epsilon = 0.01$, depth 5, lookahead depth 2.*

### LicketyRESPLIT: Polynomial-Time Approximation

Heile et al. (2025) push the scalability further with LicketyRESPLIT, which replaces TreeFARMS entirely with a polynomial-time enumeration strategy. At each node, the algorithm considers all features and prunes splits whose LicketySPLIT-completed cost would exceed the Rashomon budget $B = (1 + \epsilon) \cdot \text{LicketySPLIT}(D, \lambda, d)$. It then recursively enumerates left and right subtrees, filtering by the remaining budget.

The key theoretical results are:

> **Key Result: LicketyRESPLIT Complexity (Heile et al., 2025)**
>
> Given a dataset $D$ of size $n$ with $k$ features and max depth $d$:
>
> - **Runtime:** $\mathcal{O}(|R|\,n\,k^3\,d^3)$, where $|R|$ is the size of the recovered Rashomon set. This is polynomial in $n$, $k$, and $d$, and linear in $|R|$.
> - **Memory:** $\mathcal{O}\bigl(nk + \sum_{f \in R} S(f)\bigr)$, proportional to the input size plus the output size.

In practice, LicketyRESPLIT achieves order-of-magnitude improvements over both TreeFARMS and RESPLIT:

| Dataset | LicketyRESPLIT (Time / RAM) | TreeFARMS (Time / RAM) | RESPLIT (Time / RAM) |
|---|---|---|---|
| Bike | **18.8 s / 438 MB** | 685 s / 51 GB | 184 s / 528 MB |
| Bank | **123 s / 776 MB** | OOM | 238 s / 2 GB |
| Covertype | **507 s / 1.8 GB** | 1819 s / 68 GB | 1295 s / 3 GB |
| Student | **1.7 s / 370 MB** | 351 s / 4.7 GB | 4.0 s / 382 MB |

*Source: Table 1 in Heile et al. (2025). Parameters: $\lambda = 0.01$, $\epsilon_{\text{mult}} = 0.01$, max depth = 5.*

Despite being an approximation, LicketyRESPLIT achieves near-perfect precision and recall relative to the true Rashomon set. On six benchmark datasets, precision is $\geq 0.91$ and recall is $\geq 0.90$ across all tested configurations (Heile et al., 2025).

> **Warning: Exact vs. Approximate Enumeration**
>
> TreeFARMS gives you the *exact* Rashomon set: every tree in the set, and no tree outside it. RESPLIT and LicketyRESPLIT are approximations: they may miss a few trees (recall $< 1$) and occasionally include a tree slightly outside the boundary (precision $< 1$). For downstream variable importance analysis, this distinction rarely matters: the approximate sets produce virtually identical importance rankings. But if you need a formal guarantee ("no tree in the Rashomon set uses feature $X_7$"), only exact enumeration suffices.

Rashomon set algorithms are developing rapidly. The figure below summarizes the three approaches and their trade-offs.

```mermaid
flowchart LR
  tf["<b>TreeFARMS</b><br/>Exact enumeration<br/>Exponential in d, k<br/><i>NeurIPS 2022</i>"]
  rs["<b>RESPLIT</b><br/>Greedy leaves + TreeFARMS<br/>10-20x faster<br/><i>ICML 2025</i>"]
  lr["<b>LicketyRESPLIT</b><br/>Polynomial-time<br/>100x less memory<br/><i>NeurIPS 2025 Workshop</i>"]
  tf -- "approximate" --> rs
  rs -- "remove TreeFARMS" --> lr
```

*Evolution of Rashomon set enumeration algorithms for sparse decision trees. Each generation trades a small amount of exactness for dramatic improvements in scalability.*


## What the Rashomon Set Reveals

Two complementary tools turn the raw set of models into concrete conclusions about feature importance.

### Model Class Reliance (MCR)

The simplest analysis is to ask: for each feature, what is the *range* of its importance across all models in the Rashomon set? This is **Model Class Reliance (MCR)**, introduced by Dong and Rudin (2020) (building on the concept from Fisher et al., 2019).

For a single model $f$, the **model reliance** of feature $j$ is defined as the ratio of the loss when feature $j$ is randomly permuted to the original loss:

$$
  mr_j^{\text{ratio}}(f) = \frac{L(f;\,[X_{\setminus j},\, \bar{X}_j],\, Y)}
    {L(f;\, X,\, Y)},
$$

where:

- $X_{\setminus j}$ denotes all features except feature $j$
- $\bar{X}_j$ is an independent copy of $X_j$ (i.e., feature $j$ is reshuffled)
- A reliance of 1.0 means the feature contributes nothing; larger values indicate greater importance

MCR defines two key quantities for each feature $j$:

$$
\begin{aligned}
  \text{MCR}_{-}(j) &= \min_{f \in \mathcal{R}} mr_j(f),\\
  \text{MCR}_{+}(j) &= \max_{f \in \mathcal{R}} mr_j(f).
\end{aligned}
$$

The interpretation is clean:

- A feature with large $\text{MCR}_{-}$ is important in *every* well-performing model. It is robustly important.
- A feature with small $\text{MCR}_{+}$ is unimportant in every well-performing model. It can be safely excluded.
- A feature with small $\text{MCR}_{-}$ but large $\text{MCR}_{+}$ is a *substitute*: important in some models, not in others. It can be swapped for a correlated alternative without loss of accuracy.

Xin et al. (2022) showed that TreeFARMS enables *exact* MCR computation for decision trees by directly calculating variable importance for every tree in the set and then finding the min and max.

### Variable Importance Clouds (VIC)

MCR gives a one-dimensional summary (min and max importance) for each feature independently. **Variable Importance Clouds (VIC)** (Dong and Rudin, 2020) capture the full joint structure.

> **Definition: Variable Importance Cloud (Dong and Rudin, 2020)**
>
> The **model reliance function** $MR : \mathcal{F} \to \mathbb{R}^p$ maps each model to a vector of its reliances on all $p$ features:
>
> $$
>   MR(f) = \bigl(mr_1(f),\; mr_2(f),\; \ldots,\; mr_p(f)\bigr).
> $$
>
> The **Variable Importance Cloud** of the Rashomon set $\mathcal{R}$ is the set of all such vectors:
>
> $$
>   \operatorname{VIC}(\mathcal{R}) = \bigl\{MR(f) : f \in \mathcal{R}\bigr\}.
> $$

The VIC lives in $p$-dimensional space, where each axis represents the importance of one feature. To visualize it, Dong and Rudin (2020) project the VIC onto all pairs of features, producing **Variable Importance Diagrams (VIDs)**, 2D scatter plots that reveal substitution patterns:

- **Non-overlapping projections** along one axis: the two features have robustly distinct importance levels. One is always more important than the other, regardless of model choice.
- **Overlapping projections**: the features are substitutes. Some near-optimal models rely on one, some on the other.
- **Negative slope** in the 2D projection: the features are direct substitutes; as one's importance increases, the other's decreases. This is the signature of correlated features competing for the same splits.

> **Key Idea: VIC vs. Bootstrapped SHAP**
>
> A natural reaction is: "I could just bootstrap the data, refit SHAP each time, and get a distribution of importances." This is fundamentally different from VIC. Bootstrapped SHAP resamples the *data* but always uses the same model class and always reports the importance of the single best model within that class. VIC holds the data fixed and varies the *model*: it considers every near-optimal model, not just the best one.
>
> The distinction matters because bootstrap variability conflates data uncertainty with model uncertainty. VIC isolates model uncertainty: "given this exact dataset, how much does the importance depend on which near-optimal model we happened to pick?" This is the right question when your concern is the stability of your explanations, not the variability of your data.

### Rashomon Importance Distributions (RID)

MCR and VIC answer the question "what is the range of importances across all near-optimal models *for this dataset*?" But this answer is fragile: the Rashomon set itself changes when the dataset is perturbed. Donnelly et al. (2023) show that both the Rashomon set size and the MCR range can vary wildly across bootstrap resamples of the *same* data, making MCR and VIC unstable summaries of feature importance.

The **Rashomon Importance Distribution (RID)** proposed by Donnelly et al. (2023) addresses this by combining bootstrap resampling *with* Rashomon set analysis in a two-level procedure that captures both sources of uncertainty simultaneously.

**The five-step RID pipeline** (illustrated in Figure 2 of Donnelly et al., 2023):

1. **Bootstrap.** Draw $B$ bootstrap datasets $\mathcal{D}_1^{(n)}, \ldots, \mathcal{D}_B^{(n)}$ from the original data $\mathcal{D}^{(n)}$ (sampling $n$ observations with replacement).
2. **Find Rashomon set.** For each bootstrap dataset $\mathcal{D}_b^{(n)}$, compute the Rashomon set $\mathcal{R}_{\mathcal{D}_b}^{\varepsilon}$: all models in $\mathcal{F}$ whose loss is within $\varepsilon$ of the best model *on that bootstrap sample*.
3. **Find importances.** For each model $f$ in each Rashomon set, compute the variable importance $\phi_j(f, \mathcal{D}_b^{(n)})$ using any importance metric (permutation importance, SHAP, model reliance, etc.).
4. **Find CDF.** For each bootstrap $b$, compute the empirical CDF of importances across the Rashomon set for that bootstrap.
5. **Find PDF.** Average the CDFs across all $B$ bootstraps to obtain the RID, then differentiate to get the marginal density.

Formally, RID is defined as a cumulative distribution function. For feature $j$, the RID at threshold $k$ measures the expected fraction of near-optimal models whose importance for feature $j$ is at most $k$, where the expectation is over the data distribution:

$$
  \text{RID}_j(k)
    = \mathbb{E}_{\mathcal{D}_b^{(n)} \sim \mathcal{P}_n}\!\left[
      \frac{|\{f \in \mathcal{R}_{\mathcal{D}_b}^{\varepsilon}
        : \phi_j(f, \mathcal{D}_b^{(n)}) \leq k\}|}
        {|\mathcal{R}_{\mathcal{D}_b}^{\varepsilon}|}
    \right],
$$

where:

- $\mathcal{P}_n$ is the empirical distribution of the data (i.e., the bootstrap distribution)
- $\mathcal{R}_{\mathcal{D}_b}^{\varepsilon}$ is the Rashomon set for bootstrap sample $\mathcal{D}_b^{(n)}$
- $\phi_j(f, \mathcal{D}_b^{(n)})$ is the importance of feature $j$ for model $f$ evaluated on $\mathcal{D}_b^{(n)}$
- $k$ ranges over $[\phi_{\min}, \phi_{\max}]$, the support of the importance metric

In practice, we estimate RID by replacing the expectation with a sample average over $B$ bootstrap replicates:

$$
  \widehat{\text{RID}}_j(k)
    = \frac{1}{B}\sum_{b=1}^{B}
      \frac{|\{f \in \mathcal{R}_{\mathcal{D}_b}^{\varepsilon}
        : \phi_j(f, \mathcal{D}_b^{(n)}) \leq k\}|}
        {|\mathcal{R}_{\mathcal{D}_b}^{\varepsilon}|}.
$$

> **Intuition: In Plain English**
>
> RID asks: "If I drew a new dataset from the same population, computed all near-optimal models on it, and measured feature $j$'s importance in each of those models, what distribution of importances would I see?" The bootstrap handles the "new dataset" part; the Rashomon set handles the "all near-optimal models" part. The result is a CDF that captures *both* data uncertainty and model-choice uncertainty in a single object.

> **Warning: Additive vs. Multiplicative Rashomon Threshold**
>
> Donnelly et al. (2023) define the Rashomon set using an **additive** threshold: $\mathcal{R}^{\varepsilon} = \{f \in \mathcal{F} : \ell(f) \leq \min_{f'}\ell(f') + \varepsilon\}$. This contrasts with the **multiplicative** threshold used by Xin et al. (2022) earlier in this chapter: $L(f) \leq (1 + \epsilon) L(f^*)$. The two formulations are equivalent when rescaled appropriately, but be careful not to mix them: an additive $\varepsilon = 0.05$ and a multiplicative $\epsilon = 0.05$ define different sets.

**Why not just bootstrap?** A natural alternative is naive bootstrap importance: draw $B$ bootstrap samples, fit the best model on each, and collect the importances. This captures data uncertainty but uses only *one* model per resample (the best one), ignoring the many near-optimal alternatives. RID considers *all* near-optimal models per resample, capturing model-choice uncertainty that naive bootstrapping misses entirely.

**Why not just MCR/VIC?** MCR and VIC analyze the Rashomon set of a *single* dataset. They capture model-choice uncertainty but are blind to data uncertainty. Donnelly et al. (2023) demonstrate that MCR ranges are unstable across bootstrap resamples: for one variable on the Monk 3 dataset, the MCR range is $[-0.1, 0.33]$ on one resample and $[0.33, 0.36]$ on another: contradictory conclusions from the same underlying data.

> **Key Idea: RID = Bootstrap $\times$ Rashomon**
>
> RID is the only method that captures *both* sources of uncertainty simultaneously:
>
> | **Method** | **Data uncertainty** | **Model uncertainty** | **Stable?** |
> |---|---|---|---|
> | Single-model SHAP | No | No | No |
> | Bootstrap importance | Yes | No | Partially |
> | MCR / VIC | No | Yes | No |
> | **RID** | **Yes** | **Yes** | **Yes** |

**Finite-sample guarantees.** Donnelly et al. (2023) prove (Theorem 2) that the estimated $\widehat{\text{RID}}_j$ converges to the true $\text{RID}_j$ at a rate controlled by the number of bootstraps: with probability at least $1 - \delta$,

$$
  \bigl|\widehat{\text{RID}}_j(k) - \text{RID}_j(k)\bigr| \leq t
  \quad \text{for all } k,
  \quad \text{when } B \geq \frac{1}{2t^2}\ln\frac{2}{\delta}.
$$

For example, $B = 471$ bootstraps guarantees that the estimated RID is within $t = 0.075$ of the true value with 90% confidence. This is a practical guarantee: a few hundred bootstraps suffice for reliable results.

**Metric-agnostic.** RID works with any variable importance metric $\phi_j$: permutation importance, SHAP, model reliance, conditional model reliance, or any other metric with a bounded range. The framework treats $\phi_j$ as a black box, making it immediately compatible with existing importance tools.

**Empirical stability.** On four synthetic data-generating processes, Donnelly et al. (2023) find that RID achieves a median Jaccard similarity of 0.69 across independently generated datasets, compared to below 0.55 for both MCR and VIC. RID is the only method whose importance intervals consistently overlap across independent datasets drawn from the same distribution.

> **Project Connection: RID for Volatility Feature Selection**
>
> For our project, RID would answer questions that neither SHAP nor MCR can: "Across bootstrap resamples of the training data *and* across all near-optimal models within each resample, what is the distribution of VIX's importance?" If the RID CDF for VIX rises steeply near zero, VIX is unimportant in most models across most resamples, and we can drop it. If the CDF rises steeply above 0.2, VIX is robustly important. If the CDF rises gradually from 0 to 0.4, VIX is a substitute: sometimes important, sometimes not, depending on both the data sample and the model chosen. Unlike MCR, this conclusion is *stable*: it will not flip if we add one more month of data.


## Rashomon Analysis for Volatility Forecasting

No published work has applied Rashomon set analysis to financial time-series forecasting. This is an open frontier, and it is directly relevant to our project. This section describes how the tools from the enumeration and analysis sections above could be deployed for realized volatility forecasting.

### Regime-Stable Feature Selection

Volatility features that matter in a low-vol regime (2017--2019) may not matter in a crisis regime (March 2020) or a post-crisis recovery (2021). Single-model SHAP run on the full sample averages over these regimes, potentially concluding that a feature is "moderately important" when it is actually critical in crises and irrelevant otherwise.

A Rashomon-based approach to regime-stable feature selection:

1. **Rolling-window Rashomon sets.** For each rolling window (e.g., 252-day training sets advanced by one month), compute the Rashomon set and the MCR for each feature.
2. **Intersection across regimes.** A feature that has $\text{MCR}_{-} > 1$ (i.e., minimum importance above the baseline) in *every* window is regime-stable. A feature whose MCR range includes 1.0 in some windows is regime-dependent.
3. **Feature selection rule.** Include only regime-stable features in the final model. For regime-dependent features, consider regime-conditional inclusion (e.g., add VIX term structure only when VIX $> 20$).

### Prediction Multiplicity: Quantifying Model-Choice Uncertainty

The Rashomon set also reveals **prediction multiplicity**: the range of forecasts that different near-optimal models produce for the same input. For a given feature vector $\mathbf{x}_t$ (today's features), we can compute $\{f(\mathbf{x}_t) : f \in \mathcal{R}\}$ and report the min, max, and spread.

If all near-optimal models agree that tomorrow's volatility will be high, that is a strong signal. If some predict high and others predict low, the forecast is sensitive to model choice, and we should report wider confidence intervals or flag the day as uncertain.

This is conceptually similar to the disagreement among models in an ensemble, but with one important difference: ensemble members are not guaranteed to be near-optimal, while Rashomon set members are.

### Defensible Presentations

In a Goldman Sachs internship, you will present model results to people who will ask hard questions: "Why did your model use VIX and not ATM IV?" or "Your SHAP plot from last month looked completely different."

Rashomon analysis gives you defensible answers:

- "I examined all 14,000 decision trees within 2% of optimal accuracy. Lagged RV is the top feature in every single one of them. VIX and ATM IV are interchangeable; the data supports either, so I chose VIX for simplicity."
- "The feature importance is *provably stable*: no near-optimal model exists that does not rely on lagged RV."
- "The prediction range across all near-optimal models for tomorrow is $[0.00012, 0.00018]$. The spread tells you how much of the forecast uncertainty comes from model choice rather than data noise."


## Summary and Connections

This chapter introduced a fundamentally different approach to model interpretability. Rather than explaining one model after the fact (SHAP), we examine the entire space of near-optimal models before committing to one.

| **Aspect** | **Single-Model (SHAP)** | **Rashomon Set** |
|---|---|---|
| What is explained | One model's predictions | All near-optimal models |
| Feature importance | Point estimate for one model | Range $[\text{MCR}_{-}, \text{MCR}_{+}]$ |
| Stability | Changes with refit | Provably stable within $\epsilon$ |
| Substitute detection | Not possible | Overlapping VIC projections |
| Model-choice uncertainty | Not quantified | Prediction multiplicity |
| Computational cost | Fast (one model) | Hours (enumeration needed) |

**Looking ahead.** [Chapter 12b (Deep Learning for Volatility)](ch12b-deep-learning-vol.md) will introduce deep learning methods for volatility, which are powerful but even harder to interpret than tree ensembles. The Rashomon perspective suggests a hybrid strategy: use deep models for raw predictive power, but use interpretable trees (and their Rashomon sets) to understand *which features matter and why*. The two approaches complement each other.
