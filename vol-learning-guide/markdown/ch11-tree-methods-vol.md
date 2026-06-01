# Tree-Based Methods for Volatility

> **Application: **
> This chapter is where ML meets volatility forecasting for the first time.
> Tree-based methods (LightGBM, XGBoost) are the workhorse models for tabular
> volatility data, just as they dominate Kaggle competitions and quantitative
> finance pipelines. Projects 1, 2, and 5 all use tree ensembles as their
> primary model. The central question: when do trees beat HAR
> ([Chapter 6](ch06-har-model.md)), and when don't they?

## Why Trees for Volatility

[Chapter 10](ch10-feature-engineering.md) built a rich feature matrix: lagged RV transforms,
realized quarticity, signed semivariances, jumps, options-implied measures,
cross-asset signals, and calendar dummies. All of these live in a flat table
where each row is a date and each column is a number. No pixels, no word
tokens, no sequential structure that demands recurrence. This is *tabular
data*, and tree-based ensembles are the best off-the-shelf learners for
tabular data (Gu, Kelly, and Xiu, 2020).

Why? Four reasons, each directly relevant to volatility:

1. **Automatic nonlinear interactions.**
   HAR ([Chapter 6](ch06-har-model.md)) is linear in its three RV averages. If the
   effect of yesterday's RV depends on whether the VIX is above 25, you must
   hand-craft that interaction term for HAR. A tree discovers it
   automatically: one split on VIX, another on lagged RV, and the interaction
   is encoded in the tree structure.

2. **Threshold effects.**
   Volatility regimes change sharply. A tree split at
   $\operatorname{RV}_{t-1} = 0.0004$ captures a regime boundary that a linear model can
   only approximate with polynomial terms.

3. **Fast training.**
   A LightGBM model with 500 trees trains in seconds on 1,250 rows.
   This speed enables hundreds of purged cross-validation iterations
   ([Chapter 16](ch16-forecast-evaluation.md)), which is essential for honest evaluation on
   small samples.

4. **Built-in feature importance.**
   Split-count importance and SHAP values tell you *which* features
   drive predictions. This matters for interpretability, and it connects back
   to the feature selection discussion in [Chapter 10](ch10-feature-engineering.md).

> **Key Idea: Why Trees Win on Tabular Data**
> Trees excel at finding threshold effects and interactions in tabular data.
> Volatility data is tabular. The combination of automatic interaction
> detection, speed, and interpretability makes gradient-boosted trees the
> default first model for any volatility forecasting pipeline built on the
> features from [Chapter 10](ch10-feature-engineering.md).

The diagram below contrasts the two main tree ensemble strategies. A
**random forest** trains many independent trees on bootstrapped samples
and averages their predictions (variance reduction through decorrelation).
**Gradient boosting** trains trees sequentially, each one correcting the
errors of the ensemble so far (bias reduction through iterative refinement).
Both are used in volatility forecasting, but gradient boosting (LightGBM,
XGBoost) typically wins on tabular data.

```mermaid
flowchart TB
    subgraph RF["Random Forest (independent / parallel)"]
        direction TB
        T1["Tree 1"] --> AVG["Average"]
        T2["Tree 2"] --> AVG
        TB["Tree B"] --> AVG
        AVG --> RFOUT["ŷ = (1/B) Σ h_b(x)"]
    end

    subgraph GB["Gradient Boosting (sequential / corrective)"]
        direction LR
        G1["Tree 1\n(fit y)"] -->|"residual"| G2["Tree 2\n(fit r₁)"]
        G2 -->|"residual"| GM["Tree M\n(fit r_{M-1})"]
        G1 --> GBSUM["Sum (shrunk)"]
        G2 --> GBSUM
        GM --> GBSUM
        GBSUM --> GBOUT["ŷ = Σ η h_m(x)"]
    end
```

*Two tree ensemble strategies. Left: a random forest builds Tree 1, Tree 2, ..., Tree B independently (in parallel) on bootstrap samples and averages them, $\hat{y} = \frac{1}{B}\sum h_b(\mathbf{x})$. Right: gradient boosting builds Tree 1, Tree 2, ..., Tree M sequentially (correctively), each tree fitting the residual of the running ensemble, then sums the shrunk contributions, $\hat{y} = \sum \eta\, h_m(\mathbf{x})$.*

## Tree Foundations: From One Tree to a Forest

> **Prereq: What a Tree Actually Is**
> The last section claimed trees "discover threshold effects and interactions
> automatically." This section opens the box. You need only one idea from
> [Chapter 6](ch06-har-model.md): a forecast of tomorrow's $\operatorname{RV}$ is a function of
> today's feature vector $\mathbf{x}_t$ (lagged RV averages, realized quarticity,
> VIX, jumps). We ask: how does a tree turn that vector into a number, and
> why do we never use a single tree to do it?

The depth-2 tree drawn later in the LightGBM and XGBoost section (the one that
splits on $\operatorname{RV}_{t-1} = 0.0004$) is a finished object; the next three
subsections show how such a tree is built, why one tree is too unreliable to
forecast with, and how an ensemble of many trees fixes that.

### How a regression tree chooses its splits

A **regression tree** carves the feature space $\mathbb{R}^p$ (the space of all
possible feature vectors with $p$ features) into $J$
non-overlapping rectangular boxes $R_1, \ldots, R_J$, called **leaves**,
and predicts a single constant inside each box (Breiman et al., 1984). The
constant is just the average target of the training observations that landed
in that box:

$$\hat{f}(\mathbf{x}) \;=\; \sum_{j=1}^{J}
\underbrace{c_j}_{\text{leaf mean}}\,
\underbrace{\mathbf{1}(\mathbf{x} \in R_j)}_{\text{which box?}},
\qquad
c_j \;=\; \frac{1}{|R_j|}\sum_{t:\,\mathbf{x}_t \in R_j} \operatorname{RV}_t,$$

where:

- $R_j$ is the $j$-th rectangular leaf region,
- $c_j$ is the **leaf value**: the mean realized volatility of
  the training days that fall in $R_j$. Here $|R_j|$ is the count of
  training days inside box $R_j$ (the vertical bars mean "how many,"
  not absolute value), and the subscript $t:\,\mathbf{x}_t \in R_j$ means
  "take every day $t$ whose features land in this box,"
- $\mathbf{1}(\mathbf{x} \in R_j)$ is the indicator, an on/off switch that
  equals $1$ when the day's feature vector $\mathbf{x}$ lands inside box $R_j$
  and $0$ otherwise (the symbol $\in$ means "is inside"), so exactly
  one leaf fires per observation and only one term in the sum survives,
- $\sum_{j=1}^{J}$ means add up across all $J$ leaves, and the hat on
  $\hat{f}$ marks it as the model's estimate,
- $J$ is the number of leaves.

> **Intuition: In Plain English**
> A tree is a lookup table with smart boundaries. To forecast tomorrow's
> $\operatorname{RV}$, you walk down the tree answering yes/no questions about today's
> features ("is $\operatorname{RV}_{t-1}$ below $0.0004$?"), arrive at one leaf, and read
> off the average $\operatorname{RV}$ of all the historical days that ended up in that same
> leaf. The prediction is piecewise constant: every day inside a given box
> gets the identical forecast, no matter where in the box it sits. In symbols,
> that whole equation just says: find your one box, read off its stored
> average $c_j$.

The boxes are not handed to the tree; it builds them *greedily* (it
grabs the single best split available right now and never goes back to
reconsider it) by **recursive binary splitting** (it then repeats the
very same procedure inside each new child group). Start with all training
days in one root node. Consider every feature $j$ and every candidate
threshold $s$, and pick the single split $(j, s)$ that most reduces the sum
of squared residuals (SSR) across the two children that the split would
create. A **residual** is how far a day's actual $\operatorname{RV}$ sits from the
box's predicted average (actual minus predicted):

$$\min_{j,\,s}\;
\Bigg[\;
\underbrace{\sum_{t:\,x_{tj}\le s}(\operatorname{RV}_t - c_L)^2}_{\text{left-child SSR}}
\;+\;
\underbrace{\sum_{t:\,x_{tj}> s}(\operatorname{RV}_t - c_R)^2}_{\text{right-child SSR}}
\;\Bigg],$$

where:

- $x_{tj}$ is the value of feature $j$ on day $t$ (e.g. $\operatorname{RV}_{t-1}$),
- $s$ is the split threshold being tested,
- $c_L,\,c_R$ are the means of the left and right children that the
  split produces.

The $\min_{j,\,s}[\cdots]$ means: try every feature $j$ and every cut-point
$s$, and pick the single pair that makes the total spread in the bracket as
small as possible. The winning split becomes a node; the algorithm then recurses into each
child and repeats, stopping when a child is too small
(`min_child_samples`), too deep (`max_depth`), or no split
reduces SSR enough. Minimising the SSR is identical to maximising the
**variance reduction** of the target, which is why this rule is often
called the variance-reduction (or MSE-reduction) criterion. (You can skip
the next sentence: volatility forecasting is regression, so SSR is the
criterion throughout this chapter.) For a classification target the same
machinery swaps SSR for an impurity measure such as **Gini impurity**
$G = \sum_k \hat{p}_k(1-\hat{p}_k)$ or **entropy**
$H = -\sum_k \hat{p}_k \log_2 \hat{p}_k$, where $k$ indexes the classes and
$\hat{p}_k$ is the estimated share of a node's days in class $k$.

> **Intuition: In Plain English**
> The tree is a relentless optimiser with one move: "which yes/no question,
> asked right now, splits the remaining days into two groups whose $\operatorname{RV}$
> values are each as tightly clustered as possible?" It tries every feature
> at every threshold, keeps the best, and then asks the same question again
> inside each resulting group. This is exactly how the
> $\operatorname{RV}_{t-1} = 0.0004$ boundary in the LightGBM and XGBoost diagram was
> chosen: it was the single threshold that most reduced the spread of next-day
> $\operatorname{RV}$ at the root.

> **Project Connection: Why This Matters**
> The split-selection equation above is where a tree's two headline strengths
> from the Why Trees for Volatility section come from. A split on VIX followed by a
> split on $\operatorname{RV}_{t-1}$ inside one branch encodes the lagged-RV$\,\times\,$VIX
> interaction that HAR ([Chapter 6](ch06-har-model.md)) can only capture by hand-crafting
> a product term, and a split at $\operatorname{RV}_{t-1} = 0.0004$ encodes a volatility
> regime boundary that a linear model can only approximate. No interaction
> term is specified; the SSR criterion finds it.

### Why one fully grown tree is too unreliable

Let the tree grow with no stopping rule and it will keep splitting until each
leaf holds a single training day. Training error is then exactly zero: the
tree has memorised the sample. But the structure it learned is a fragile
accident of *this* particular sample. A single tree is a
**high-variance estimator** (its output swings wildly if the training
data changes even a little, an instability unrelated to the volatility we are
forecasting): perturb the training data slightly
(drop a week, add a month) and the chosen thresholds, and even which feature
splits at the root, can change completely, producing a different forecast
function.

> **Warning: A Single Tree Will Memorise Volatility Noise**
> Volatility data is short ($\sim$1,250 daily rows), heavy-tailed, and highly
> autocorrelated (see the Hyperparameters for Volatility Data section). An unconstrained tree
> will carve a dedicated leaf around a single crisis week and predict that
> week's $\operatorname{RV}$ perfectly in-sample while generalising terribly out-of-sample.
> This is why nobody forecasts $\operatorname{RV}$ with one tree, and why every result in
> this chapter uses an *ensemble* of trees.

There are two ways to tame this variance: average many independent trees
(bagging and random forests, below) or add small trees sequentially
(gradient boosting, the LightGBM and XGBoost section).

### Bagging: averaging away the variance

**Bagging** (bootstrap aggregating) reduces variance by training many
trees on resampled copies of the data and averaging them. A
**bootstrap sample** draws $n$ rows from the $n$ training days
*with replacement*, so some days appear several times and others not at
all. The fraction of *unique* original days that land in a given
bootstrap sample converges to

$$1 - \underbrace{\left(1 - \tfrac{1}{n}\right)^{n}}_{\substack{\text{prob. a row is}\\\text{never drawn}}}
\;\xrightarrow[\;n\to\infty\;]{}\;
1 - e^{-1} \;\approx\; 0.632,$$

where:

- $n$ is the number of training observations,
- $(1-\tfrac{1}{n})^n$ is the probability that a specific day is
  missed by all $n$ draws,
- the arrow with $n\to\infty$ underneath means "as the dataset grows,
  this fraction settles at the value on the right"; $e$ is Euler's
  constant ($\approx 2.718$), so $e^{-1}\approx 0.368$,
- $0.632$ is the limiting **in-bag** fraction; the remaining
  $\approx 36.8\%$ are the **out-of-bag** (OOB) days for that tree,
  which become the free validation set used in the OOB subsection below.

Bagging then fits a tree $h_b$ to each of $B$ bootstrap samples and averages:
$\hat{f}_{\text{bag}}(\mathbf{x}) = \tfrac{1}{B}\sum_{b=1}^{B} h_b(\mathbf{x})$, i.e. just
take the plain average of the forecasts of all $B$ trees, where $h_b(\mathbf{x})$ is
tree $b$'s forecast.

> **Intuition: In Plain English**
> Drawing $n$ rows with replacement is like building each tree from a slightly
> different reshuffling of history: roughly two-thirds of the real days appear
> (some duplicated), one-third sit out. Each tree is still high-variance on
> its own, but their errors are partly independent, so averaging them cancels
> much of the noise, the same reason an average of noisy measurements is more
> precise than any single reading. That two-thirds/one-third split is exactly
> what the $0.632$ formula above says.

The catch: averaging only helps to the extent the trees disagree. If one
feature dominates, every bagged tree splits on it first and the trees end up
nearly identical, so the variance barely falls.

### Random forests: decorrelating the trees

A **random forest** adds one decisive twist to bagging: at *each*
split, the tree may only consider a random subset of $m$ of the $p$ features
as split candidates. This forces different trees to build around different
features, breaking the correlation that limits bagging. The variance of the
forest average makes the payoff precise:

> **Key Idea: Random Feature Subsets Decorrelate the Forest**
> For a forest of $B$ trees, each with single-tree variance $\sigma^2$ and
> average pairwise correlation $\rho$ between trees, the variance of the
> averaged forecast is
>
> $$\operatorname{Var}\!\big(\hat{f}_{\text{RF}}\big)
> \;=\;
> \underbrace{\rho\,\sigma^2}_{\text{irreducible floor}}
> \;+\;
> \underbrace{\frac{1-\rho}{B}\,\sigma^2}_{\text{vanishes as }B\to\infty}.$$
>
> - $\operatorname{Var}(\cdots)$: how much the forecast wobbles from sample to sample,
> - $\sigma^2$: that wobble for a single tree (this $\sigma$ is the
>   spread of tree forecasts, *not* the volatility we are
>   forecasting),
> - $\rho$: how similar the trees' answers are
>   ($0=$ totally different, $1=$ identical copies),
> - $B$: the number of trees in the forest.
>
> Adding trees ($B\to\infty$) kills the second term but never the first: the
> variance floor is $\rho\sigma^2$. The only way below that floor is to lower
> $\rho$ itself, which is exactly what the random $m$-feature restriction does.
> Smaller $m$ means more decorrelated trees (lower $\rho$) at the price of
> slightly higher individual-tree bias. The standard defaults are
> $m = \lfloor p/3 \rfloor$ for regression and $m = \lfloor \sqrt{p}\,\rfloor$
> for classification, where the $\lfloor\,\cdot\,\rfloor$ brackets mean "round
> down to a whole number" (so with $p = 45$ features you try about $15$ at
> each split).

> **Intuition: In Plain English**
> The random-forest variance equation says you cannot average your way to zero
> variance if all the trees agree. Restricting each split to a random handful
> of features is a deliberate sabotage: it stops every tree from leaning on the
> same dominant predictor, so the trees make *different* mistakes, and
> different mistakes average out. More trees help only up to the correlation
> floor; decorrelation is what lowers the floor.

> **Project Connection: Why This Matters**
> In $\operatorname{RV}$ forecasting the dominant predictor is overwhelmingly the lagged
> daily $\operatorname{RV}$ ([Chapter 6](ch06-har-model.md)), so an unrestricted forest would split on
> it in nearly every tree and decorrelate poorly. The random-feature trick is
> what lets the other feature families from [Chapter 10](ch10-feature-engineering.md) (RQ,
> signed semivariances, VIX, jumps) actually enter the ensemble. The same
> logic reappears as `colsample_bytree` for gradient boosting in
> the Hyperparameters for Volatility Data section: feature subsampling there decorrelates
> boosted trees for precisely this reason.

### Out-of-bag error, and why it lies on time series

Because each tree omits its $\approx 36.8\%$ out-of-bag days
(see the bootstrap fraction equation above), a forest comes with a free,
built-in validation set: score each day using only the trees that did
*not* see it, and the resulting **out-of-bag (OOB) error**
approximates leave-one-out cross-validation (test on each day in turn while
training on all the others) with no separate holdout needed.
That is genuinely useful, for cross-sectional, exchangeable data.

> **Warning: OOB Error Is Invalid for Volatility Time Series**
> OOB error assumes the observations are **exchangeable**
> (i.i.d., independent and identically distributed; the order of the rows
> does not matter).
> Volatility is not: if day $t{+}1$ is in a tree's bootstrap sample while day
> $t$ is out-of-bag, scoring day $t$ on that tree lets it "predict the past
> from the future," because adjacent $\operatorname{RV}$ values are nearly identical
> (see the Hyperparameters for Volatility Data section). OOB error therefore looks far better
> than true out-of-sample performance. Use it only as a quick development
> sanity check, never as your selection metric. For honest model selection,
> use purged $K$-fold cross-validation with an embargo
> (the Purged Cross-Validation section of [Chapter 16](ch16-forecast-evaluation.md)), which
> removes the leakage that breaks OOB.

## LightGBM and XGBoost

This section reviews gradient boosting at a level sufficient for volatility
work. If you want the full algorithmic treatment (histogram binning,
leaf-wise vs. level-wise growth, GOSS sampling), see a dedicated ML
reference. Here we focus on the choices that matter for forecasting $\operatorname{RV}$.

> **Prereq: Gradient Boosting in One Paragraph**
> You start with a constant prediction (the training-set mean of $\operatorname{RV}$).
> You compute the residuals. You fit a shallow decision tree to those
> residuals. You add a shrunken version of that tree's predictions to the
> running forecast. You repeat. Each new tree corrects the mistakes of the
> ensemble so far. The "gradient" part: the residuals are the negative
> gradient of the loss function with respect to the current prediction,
> so this procedure is gradient descent in function space.

### A single tree on lagged RV

Before ensembles, consider one tree. The diagram below shows a depth-2 tree
predicting tomorrow's $\operatorname{RV}$ from yesterday's value.

```mermaid
flowchart TD
    ROOT["RV_{t-1} < 0.0004?"]
    ROOT -->|Yes| L1["RV_{t-1} < 0.0001?"]
    ROOT -->|No| R1["RV_{t-1} < 0.0012?"]
    L1 -->|Yes| LL["Predict 0.00007"]
    L1 -->|No| LR["Predict 0.00022"]
    R1 -->|Yes| RL["Predict 0.00065"]
    R1 -->|No| RR["Predict 0.0018"]
```

*A depth-2 regression tree. The root splits on $\operatorname{RV}_{t-1} < 0.0004$. The left child splits again on $\operatorname{RV}_{t-1} < 0.0001$ (leaves predict $0.00007$ for Yes, $0.00022$ for No); the right child splits on $\operatorname{RV}_{t-1} < 0.0012$ (leaves predict $0.00065$ for Yes, $0.0018$ for No).*

The tree partitions the feature space into four leaves, each returning a
constant prediction. This is piecewise-constant approximation. A single
shallow tree is a weak learner; boosting combines hundreds of them.

### The boosting ensemble

The diagram below shows how gradient boosting builds its forecast
sequentially. Each tree fits the residual errors of the ensemble so far.

```mermaid
flowchart LR
    T1["Tree 1\n(fit y)"] -->|"η·h₁(x)"| S1("+")
    S1 -->|"residual r₁"| T2["Tree 2\n(fit r₁)"]
    T2 -->|"η·h₂(x)"| S2("+")
    S2 -->|"···"| TM["Tree M\n(fit r_{M-1})"]
    TM --> OUT["ŷ = Σ_{m=1}^{M} η h_m(x)"]
```

*Gradient boosting builds its forecast sequentially. Tree 1 fits $y$ and contributes $\eta \cdot h_1(\mathbf{x})$ to a running sum; the residual $r_1$ is passed to Tree 2, which fits it and contributes $\eta \cdot h_2(\mathbf{x})$; and so on through Tree M (fitting $r_{M-1}$). The final forecast is $\hat{y} = \sum_{m=1}^{M} \eta\, h_m(\mathbf{x})$.*

The ensemble prediction is:

$$\hat{y}_t \;=\; \sum_{m=1}^{M} \eta \, h_m(\mathbf{x}_t),$$

where:

- $h_m(\mathbf{x}_t)$ is the prediction of the $m$-th tree given feature
  vector $\mathbf{x}_t$,
- $\eta \in (0,1]$ is the learning rate (shrinkage),
- $M$ is the number of boosting iterations (trees).

> **Intuition: In Plain English**
> The final prediction is a team vote: each tree contributes a small correction,
> and you add up all the corrections. The learning rate $\eta$ shrinks each
> tree's voice so that no single tree dominates. More trees with a smaller
> learning rate generally gives a smoother, more reliable forecast than fewer
> trees with a larger rate.

> **Project Connection: Why This Matters**
> This additive structure is how LightGBM and XGBoost produce your daily
> $\operatorname{RV}$ forecast. Every tree in the ensemble sees the same feature vector
> $\mathbf{x}_t$ (lagged RV, VIX, jumps, etc. from [Chapter 10](ch10-feature-engineering.md))
> and contributes a correction. Tuning $\eta$ and $M$ together (with early
> stopping) is the primary way to control overfitting on 1,250-row
> volatility samples.

### Loss function choice

The standard loss for regression is MSE:
$\mathcal{L}_{\text{MSE}} = \frac{1}{N}\sum_t (\operatorname{RV}_t - \hat{y}_t)^2$.
But [Chapter 16](ch16-forecast-evaluation.md) showed that $\operatorname{QLIKE}$ is the preferred loss
for volatility forecasting (Audrino and Knaus, 2016):

$$\mathcal{L}_{\operatorname{QLIKE}} \;=\; \frac{1}{N}\sum_{t=1}^{N}
\left(\frac{\operatorname{RV}_t}{\hat{y}_t} - \ln\frac{\operatorname{RV}_t}{\hat{y}_t} - 1\right).$$

- $\operatorname{RV}_t$: the realized volatility actually observed on day $t$,
- $\hat{y}_t$: the model's forecast for day $t$,
- the summand equals zero when $\hat{y}_t = \operatorname{RV}_t$ and is strictly
  positive otherwise.

> **Intuition: In Plain English**
> QLIKE penalizes you more harshly for under-predicting volatility than for
> over-predicting it by the same amount. If realized vol is 20% and you
> forecast 10%, the penalty is much larger than if you forecast 30%. This
> asymmetry matches real risk management needs: underestimating volatility is
> more dangerous than overestimating it. MSE, by contrast, penalizes both
> directions equally.

> **Project Connection: Why This Matters**
> QLIKE is the primary evaluation metric for the GS project. Training your
> tree model directly on QLIKE (rather than MSE) aligns the optimization
> objective with the evaluation criterion.
> Audrino and Knaus (2016) show that QLIKE-optimized trees outperform
> MSE-optimized trees for realized volatility, so this custom loss is not
> optional; it is a core part of the pipeline.

Neither LightGBM nor XGBoost provides $\operatorname{QLIKE}$ natively, but both accept
custom objective functions. You supply the gradient and Hessian:

$$g_t = \frac{\partial \mathcal{L}_{\operatorname{QLIKE}}}{\partial \hat{y}_t}
       = -\frac{\operatorname{RV}_t}{\hat{y}_t^2} + \frac{1}{\hat{y}_t},$$

$$h_t = \frac{\partial^2 \mathcal{L}_{\operatorname{QLIKE}}}{\partial \hat{y}_t^2}
       = \frac{2\,\operatorname{RV}_t}{\hat{y}_t^3} - \frac{1}{\hat{y}_t^2}.$$

- $g_t$: the gradient tells each tree which direction to adjust
  predictions,
- $h_t$: the Hessian tells each tree how aggressively to adjust
  (curvature information).

> **Intuition: In Plain English**
> The gradient $g_t$ answers: "for observation $t$, should the next tree push
> the prediction up or down?" The Hessian $h_t$ answers: "how confident
> should that push be?" Together, they let the boosting algorithm do
> Newton-step optimization in function space, which converges faster than
> using the gradient alone.

> **Project Connection: Why This Matters**
> Implementing these two formulas as a custom objective function in LightGBM
> or XGBoost is a 10-line code change, but it is the single most impactful
> modification you can make to the default pipeline. Without it, the tree
> model optimizes MSE, which does not match the QLIKE evaluation metric and
> systematically under-penalizes low forecasts in high-vol regimes.

> **Warning: Enforce Positive Predictions**
> $\operatorname{QLIKE}$ requires $\hat{y}_t > 0$. Clip predictions to a small positive
> floor (e.g., $10^{-8}$) inside the custom objective, or the gradient
> explodes. Also apply the floor when evaluating the metric, not just during
> training.

### Monotone constraints

Finance intuition says "higher recent volatility predicts higher future
volatility." You can encode this as a monotone constraint on lagged-RV
features: the prediction must be non-decreasing in $\operatorname{RV}_{t-1}$. Both
LightGBM and XGBoost support per-feature monotone constraints. Use them
sparingly (only for features where the monotone relationship is
theoretically unambiguous), but when appropriate, they reduce overfitting
and improve interpretability.

## Hyperparameters for Volatility Data

This section is the most practically important in the chapter. Volatility
data has three properties that make default hyperparameters dangerous:

1. **Small samples.**
   Five years of daily data gives you roughly 1,250 observations. This is
   orders of magnitude smaller than the datasets LightGBM and XGBoost were
   optimized for.

2. **High autocorrelation.**
   $\operatorname{RV}$ is strongly persistent ([Chapter 6](ch06-har-model.md)). Nearby observations
   are nearly identical, so effective sample size is smaller than the row
   count suggests.

3. **Heavy tails.**
   Volatility spikes create influential observations. A single crisis week
   can dominate the loss function.

> **Warning: Default Settings Will Overfit**
> Default LightGBM/XGBoost settings (`max_depth`=6+,
> `min_child_samples`=20) were designed for datasets with 100K+ rows.
> With 1,250 daily observations, defaults will memorize noise. The table below
> gives recommended ranges calibrated for volatility forecasting.

| **Parameter** | **Default** | **Vol Range** | **Rationale** |
|---|---|---|---|
| `max_depth` | 6--8 | 3--5 | Shallow trees limit memorization |
| `min_child_samples` | 20 | 50--200 | Forces each leaf to generalize |
| `subsample` | 1.0 | 0.6--0.8 | Row subsampling adds regularization |
| `colsample_bytree` | 1.0 | 0.6--0.8 | Feature subsampling decorrelates trees |
| `learning_rate` | 0.1 | 0.01--0.05 | Slow learning + early stopping |
| `num_iterations` | 100 | 500--2000 | More trees at lower rate; early stop |
| `reg_lambda` | 0 | 1--10 | L2 leaf regularization |

> **Key Idea: Early Stopping on Purged Validation**
> Early stopping is the single most important regularization technique for
> tree ensembles on small volatility data. But the validation set used for
> early stopping must respect the purged CV structure: no overlap between
> training and validation dates, with an embargo gap. If you use a random
> validation split, early stopping will stop too late because the validation
> set is contaminated by lookahead.

## Interpreting Tree Models: TreeSHAP and the SHAP Plot Toolkit

> **Prereq: SHAP, MDA, and MDI from Chapter 10**
> The feature-importance section of [Chapter 10](ch10-feature-engineering.md) introduced three feature-importance ideas
> you will reuse here: **SHAP** values, which decompose a single
> prediction additively into per-feature contributions
> (the SHAP equation); **MDA** (mean decrease in accuracy), the
> permutation-based global importance; and **MDI** (mean decrease in
> impurity), the fast-but-biased split-based importance. It also introduced
> **ALE** plots (the ALE equation). This section answers the
> question that section left open: *how* do you compute SHAP for a tree
> ensemble cheaply, and *which* plot do you reach for when?

You have a tuned LightGBM forecasting next-day log-$\operatorname{RV}$ on the feature
matrix from [Chapter 10](ch10-feature-engineering.md) (lagged RV transforms, realized
quarticity, VIX, jumps). It beats HAR by 7.7% in $\operatorname{QLIKE}$
(see the Hyperparameters for Volatility Data section). Your sponsor's first question is not
"what is the $\operatorname{QLIKE}$?" but "*why* did the model forecast a vol spike
for next Tuesday?" The SHAP equation promises an exact additive answer
per day, but computing it honestly looks hopeless.

### The exponential cost that TreeSHAP defeats

The SHAP value of feature $i$ (recall from [Chapter 10](ch10-feature-engineering.md): feature
$i$'s fair share of the forecast) averages its *marginal contribution*
(how much adding $i$ changes the prediction) over *every* subset of the
other features. With $p$ features that is $2^p$ **coalitions** to
evaluate, *for every observation* ("coalition" and "subset of
features" mean the same thing here). The notation $2^p$ means $2$
multiplied by itself $p$ times, so every extra feature *doubles* the
number of subsets. On the [Chapter 10](ch10-feature-engineering.md) matrix with, say,
$p = 20$ features, that already gives $2^{20} \approx 10^6$ (about a million)
model evaluations per day, times $\sim$1,250 days,
far too slow for a generic model. This exponential wall is exactly why
Lundberg and Lee (2017) introduced model-specific shortcuts.

**TreeSHAP** (Lundberg et al., 2020) exploits the structure of decision
trees to compute the *exact* same Shapley values in polynomial time. In
the cost formula below, $O(\cdots)$ is shorthand for how fast the computation
time grows as the inputs grow: bigger inside the parentheses means slower.

$$\underbrace{O\!\big(T \, L \, D^2\big)}_{\text{TreeSHAP}}
\quad\text{instead of}\quad
\underbrace{O\!\big(T \, L \, 2^{p}\big)}_{\text{naive Shapley}},$$

where:

- $T$ is the number of trees in the ensemble,
- $L$ is the maximum number of leaves per tree,
- $D$ is the maximum tree depth,
- $p$ is the number of features.

In plain terms: TreeSHAP's cost grows with trees $\times$ leaves $\times$
depth-squared (manageable), while the naive method's cost grows with $2^p$,
which doubles every time you add one feature (hopeless), so TreeSHAP is fast
enough to run and the naive method is not.

> **Intuition: In Plain English**
> The naive method asks "what happens to the prediction under all $2^p$
> ways of hiding features?" TreeSHAP notices that a depth-$D$ tree only ever
> splits on at most $D$ features along any root-to-leaf path, so the only
> subsets that can possibly change a leaf's reachability number $O(2^D)$, not
> $O(2^p)$. It pushes probability mass down the tree once and reads off the
> exact attributions, turning an exponential count over *features* into a
> polynomial count over *tree depth*. Because of the additivity axiom
> (a guarantee that the per-tree contributions add up cleanly), the ensemble's
> SHAP value for a feature is simply the sum of its values across all trees.

> **Project Connection: Why This Matters**
> TreeSHAP makes the SHAP feature-importance plot in the feature-importance figure of
> [Chapter 10](ch10-feature-engineering.md) a one-line,
> seconds-long computation on your LightGBM forecaster:
> `shap.TreeExplainer(model).shap_values(X)`. Because it is exact, it
> removes a confound when you compare importance across purged-CV folds for
> stability, any ranking changes you see are real instability, not Monte-Carlo
> noise from the explainer.

> **Warning: TreeSHAP: Interventional vs. Path-Dependent**
> TreeSHAP ships in two modes. The default **path-dependent** mode is
> faster but uses the tree's internal node-coverage counts to marginalise
> missing features, which can assign small nonzero SHAP values to features the
> model never split on. The **interventional** mode marginalises against
> a background dataset, which is theoretically cleaner but slower. Both are
> still TreeSHAP (exact for their respective games) and differ from
> **KernelSHAP**, a model-agnostic *sampling* approximation usable on
> any model but noisy and orders of magnitude slower. For $\operatorname{RV}$ work: use
> path-dependent mode for fast exploration, switch to interventional with an
> $\operatorname{RV}$-feature background sample for the numbers you put on a slide.

### The four SHAP plots: a read-and-use taxonomy

The `shap` library produces four core plot types. Each answers a
different question about your $\operatorname{RV}$ forecaster; the table is your
lookup for which to reach for.

| **Plot** | **Scope** | **What it shows** | **Use it to...** |
|---|---|---|---|
| **Beeswarm** (summary) | Global, all days | One dot per day per feature; $x$ = SHAP value, colour = feature value (red high, blue low); features sorted by mean $\|\phi_j\|$ | See which features drive forecasts overall and in which direction (does high lagged $\operatorname{RV}$ push the forecast up?) |
| **Dependence** | Per-observation scatter | One feature's value ($x$) vs. its SHAP value ($y$), coloured by the most-interacting feature | Reveal nonlinearity/thresholds in a feature's effect and two-way interactions (e.g. lagged $\operatorname{RV}$ $\times$ implied vol) |
| **Waterfall** | Single day | Bars walking from the base value $\mathbb{E}[f(\mathbf{x})]$ to the day's forecast, red up / blue down | Explain *one* prediction as an additive story; the presentation chart |
| **Force** | Single day | The same decomposition as the waterfall, in a compact horizontal bar | Embed a one-line explanation in a dashboard or monitor |

Two symbols in the table: $\mathbb{E}[f(\mathbf{x})]$ is the **base value**, the model's
average prediction over all days, i.e. its starting guess before any feature
nudges it up or down; and $\phi_j$ is the SHAP contribution of feature $j$
(from [Chapter 10](ch10-feature-engineering.md)), so $|\phi_j|$ is its size ignoring whether
it pushed the forecast up or down.

> **Key Idea: Dependence Plot vs. ALE: Two Views of the Same Feature**
> The SHAP **dependence** plot and the **ALE** (Accumulated Local
> Effects) plot
> (the ALE equation, [Chapter 10](ch10-feature-engineering.md)) answer related but
> distinct questions about, say, lagged $\operatorname{RV}$. ALE gives the
> *marginal shape* (the average effect of this feature once you average
> over all the other features): a single smooth curve summarising "as lagged
> $\operatorname{RV}$ rises, does the forecast rise, fall, or flatten?", averaged within the
> observed data range. The dependence plot gives the *per-observation
> scatter*: every day is a dot, exposing the spread around that average shape,
> and its colour axis surfaces the dominant *interaction* (e.g. the
> lagged-$\operatorname{RV}$ effect is amplified on high-VIX days). Read ALE for the
> functional form; read the dependence plot for heterogeneity and
> interactions. They are complements, not substitutes.

### SHAP vs. MDI vs. MDA: when to use which

All three measures answer "which features matter?" but at different
granularity, and they occasionally disagree. The reconciliation rule below
is what you actually apply during $\operatorname{RV}$ model development.

| **Measure** | **Granularity** | **Strength / weakness** | **When to use** |
|---|---|---|---|
| **SHAP** | Local (per day), sums to the prediction | Richest information; exact via TreeSHAP; can be unstable across correlated features (the feature-importance section of [Chapter 10](ch10-feature-engineering.md)) | Presentation charts, debugging single forecasts, detecting nonlinearity |
| **MDA** | Global, in units of $\operatorname{QLIKE}$/MSE drop | Model-agnostic, unbiased under independence (gives the right ranking when features are not correlated with each other); costs $p$ extra passes; *must* use held-out data | Primary aggregate importance and cross-fold stability checks |
| **MDI** | Global, free byproduct of training | Biased toward high-cardinality features (those with many distinct values, hence many possible split points, a continuous $\operatorname{RV}$ vs. a yes/no jump flag) (Strobl et al., 2007) | Quick sanity check only; never a reported result |

In practice you compute all three on your $\operatorname{RV}$ model and reconcile:

- **All three agree** on the top features (typically lagged
  $\operatorname{RV}$ then $\sqrt{\operatorname{RQ}}$): robust evidence, proceed.
- **SHAP and MDA agree but MDI disagrees**: trust SHAP/MDA, this
  is the MDI cardinality bias (see the warning below); ignore MDI.
- **SHAP and MDA disagree**: the importance is likely driven by a
  few extreme days (vol spikes) that SHAP attributes per-observation
  but MDA averages away, inspect a SHAP dependence plot to locate
  them.

> **Warning: Do Not Report MDI as a Final Importance Result**
> MDI systematically over-credits features with many possible split points.
> A continuous feature such as lagged $\operatorname{RV}$ or VIX has hundreds of candidate
> thresholds, so the tree has more chances to split on it by luck alone, while
> a binary jump-day dummy has one. Strobl et al. (2007)
> show this rigorously: in simulations MDI assigned nonzero importance to
> continuous *noise* features. Use MDI to glance during development; use
> SHAP or MDA for anything you write down.

### Presenting SHAP to the desk

The interpretation work only pays off if a non-technical audience believes
it. Three rules, all of which trade rigor for being understood:

1. **Read the bars, not the math.** Say "this chart breaks the
   forecast into the contribution of each input; red bars pushed the
   predicted vol up, blue bars pushed it down, and the biggest bar is what
   mattered most that day." Do not say "Shapley" unless asked, then
   explain the fair-credit game-theory idea
   (the SHAP equation, [Chapter 10](ch10-feature-engineering.md)).
2. **Show exactly three waterfalls,** each illustrating a different
   mechanism, never twenty.
3. **Keep the global beeswarm in an appendix.** The summary plot is
   methodology, not a result; lead with the three stories and have the
   beeswarm as backup.

The three waterfalls to pick for an $\operatorname{RV}$ forecaster:

1. **A correct vol-spike forecast.** "The model predicted
   next-day $\operatorname{RV}$ roughly double its average. The drivers were a high
   lagged daily $\operatorname{RV}$ ($+$), a detected jump the prior session ($+$),
   and an elevated VIX ($+$). Realized vol spiked as forecast."
2. **A missed forecast from an unseen event.** "The model
   predicted a calm day from low lagged $\operatorname{RV}$ and a flat VIX, but an
   unscheduled macro announcement triggered a spike. SHAP shows the
   forecast rested entirely on backward-looking RV features, the model
   cannot see a surprise that is not in its inputs."
3. **A tree-vs-HAR disagreement.** "HAR forecast a mild rise;
   the tree forecast a sharp one. SHAP shows the gap came from an
   interaction between lagged $\operatorname{RV}$ and implied volatility, the
   HARQ-type effect ([Chapter 6](ch06-har-model.md)) the tree captures but linear
   HAR cannot, motivating the HAR$+$tree blend in
   the Ensemble with HAR section."

> **Project Connection: Why This Matters**
> The waterfall is the single most persuasive chart in a volatility-model
> review because it mirrors the additive P&L attribution risk committees
> already use. "Lagged $\operatorname{RV}$ contributed $+$X, the jump term $+$Y, VIX $+$Z"
> is a sentence a portfolio manager can challenge on economic grounds, which is
> exactly the scrutiny that separates a real signal from an overfit one. The
> disagreement waterfall does double duty: it is both an explanation and the
> argument for the ensemble of the Ensemble with HAR section.

## The Christensen--Siggaard--Veliyev Evidence

The most comprehensive academic horse-race of ML methods for realized
volatility forecasting is Christensen, Siggaard, and Veliyev (2023). Their
setup: 29 DJIA stocks, daily, weekly, and monthly RV forecasting, with a
feature set spanning RV lags, implied volatility, VIX, momentum, volume,
earnings announcements, and macroeconomic indicators.

> **Key Result: Christensen, Siggaard, and Veliyev (2023)**
> Gradient-boosted trees are among the top-performing models for
> daily RV forecasting across 29 DJIA stocks. Three findings matter most:
>
> 1. **Rich features amplify the ML advantage.**
>    When the feature set includes only RV lags (what HAR uses), trees offer
>    minimal improvement. When the feature set expands to include implied
>    volatility, VIX, volume, and macroeconomic indicators, trees pull ahead
>    by 4--10% in MSE at the daily horizon, and by substantially more at
>    longer horizons.
>
> 2. **Longer horizons favor ML.**
>    The gap between tree models and HAR is larger for weekly and monthly RV
>    prediction than for daily. At longer horizons, nonlinear feature
>    interactions matter more because the direct autoregressive signal decays.
>
> 3. **Accumulated Local Effects (ALE) plots reveal drivers.**
>    ALE plots (a model-agnostic alternative to partial dependence) show that
>    the tree models primarily exploit the interaction between lagged RV and
>    implied volatility, exactly the HARQ-type interaction from
>    [Chapter 6](ch06-har-model.md), but estimated nonparametrically rather than
>    imposed by hand.

The study uses a static 70/10/20 train-validation-test split for the ML
models, while the non-regularized HAR benchmarks use a rolling-window
scheme. The out-of-sample test period spans several years, covering both
calm and crisis regimes.

## The Optiver Kaggle Evidence

Academic papers evaluate models carefully but on relatively simple feature
sets. The Optiver Realized Volatility Prediction competition (Kaggle, 2021)
provides the complementary experiment: thousands of teams competing to
predict 10-minute-ahead realized volatility from limit order book data
across over 100 stocks.

> **Key Result: Optiver Kaggle Competition (2021)**
> LightGBM ensembles dominated the leaderboard. The top solutions shared
> three characteristics:
>
> 1. **Feature engineering dominated.**
>    WAP (weighted average price) returns, price acceleration, volume
>    imbalance profiles, bid-ask spread dynamics, trade-flow toxicity
>    ([Chapter 10](ch10-feature-engineering.md)). Winners spent 80% of their effort on
>    features and 20% on modeling.
>
> 2. **Trees beat deep learning.**
>    Transformer and LSTM models were tried extensively. They did not
>    beat well-tuned LightGBM on the public or private leaderboard.
>
> 3. **Blending helped, but only modestly.**
>    Top solutions blended 3--5 LightGBM models (different feature subsets or
>    random seeds). Gains from blending were 1--3%, far smaller than gains
>    from better features.

> **Key Idea: Features Over Architecture**
> The Optiver competition reinforces the lesson from [Chapter 10](ch10-feature-engineering.md):
> feature choice matters more than model choice. Trees plus good features
> consistently outperform deep learning plus raw data. If you are deciding
> where to spend your next hour of research time, spend it engineering a new
> feature, not tuning a neural network.

The Optiver setting differs from academic setups in two ways. First, the
prediction horizon is 10 minutes, not one day, so HAR is not a natural
benchmark (it was designed for daily or longer horizons). Second, the
feature space includes tick-level order book data, which is far richer than
what most academic studies use. The lesson about feature engineering
transfers directly to the daily setting, but the absolute performance
numbers do not.

## The Honest Assessment

This is the most important section in the chapter. The evidence above might
suggest that trees always win. They do not. Here is a regime-by-regime
summary of when ML adds value, grounded in the literature.

*A 2x2 matrix of when ML adds value, with feature richness on the horizontal axis (Sparse to Rich) and horizon on the vertical axis (Daily on top, Intraday on bottom). Top-left (RV lags only + daily horizon): **HAR wins or ties**, 0--5% QLIKE gain, often not significant. Top-right (Rich features + daily horizon): **Trees win**, 5--20% QLIKE gain, significant by DM test. Bottom-left (RV lags only + intraday horizon): **Trees help**, HAR not designed for intraday. Bottom-right (Rich features + intraday horizon): **Trees dominate**, Optiver evidence, clear winner.*

### Daily horizon, RV-only features: HAR is extremely competitive

When you give a tree ensemble the same three features HAR uses ($\operatorname{RV}_{t-1}$,
$\operatorname{RV}^{(w)}_{t-1}$, $\operatorname{RV}^{(m)}_{t-1}$), the improvement over HAR is 0--5%
in $\operatorname{QLIKE}$, and it is often not statistically significant by the
Diebold--Mariano test ([Chapter 16](ch16-forecast-evaluation.md)). HAR already captures
the dominant autoregressive structure. Trees can only add nonlinear kinks,
which are small and unstable on 1,250 observations.

Bollerslev, Medeiros, Patton, and Quaedvlieg (2024) demonstrate that a rolling-window HAR with properly
selected window length matches or beats off-the-shelf ML models. The key
insight: HAR's advantage comes from its parsimonious structure (3 parameters),
which is well-suited to small, noisy, autocorrelated data.

### Daily horizon, rich features: trees win

When you add the full feature set from [Chapter 10](ch10-feature-engineering.md) (implied
volatility, jumps, signed semivariances, cross-asset, sentiment), trees pull
ahead by 5--20% in $\operatorname{QLIKE}$. The reason: these features contain nonlinear
interactions that HAR cannot exploit without hand-crafting interaction terms.
The tree ensemble discovers these interactions automatically.

Christensen, Siggaard, and Veliyev (2023) confirm this pattern: the ML
advantage grows with feature-set richness.

### Intraday horizons: trees are necessary

HAR was designed for daily (or longer) horizons. For 10-minute or 1-hour
ahead prediction from order book data, HAR has no natural formulation.
Trees operate on any feature matrix, regardless of the time scale, and the
Optiver evidence shows they dominate at short horizons.

### Stress regimes: ML stumbles

Here is the uncomfortable finding. ML models, including trees, tend to
underperform HAR during extreme events (VIX spikes, flash crashes, pandemic
onset). The reason: tree ensembles trained predominantly on calm-regime
data have never seen the patterns that emerge during crises. They
extrapolate poorly because trees are piecewise-constant; predictions in
extreme leaves are based on very few training observations.

Rahimikia and Poon (2020) document this explicitly: their ML model beats HAR
on 90% of out-of-sample days, but fails catastrophically on the remaining
10%, which are precisely the days that matter most for risk management.
The Ensemble with HAR section addresses this.

### Does anything beat linear models?

Branco, Rubesam, and Zevallos (2024) ask this question directly and find that
the answer is "often no, when the comparison is fair." Their main point:
many published ML-beats-HAR results use default hyperparameters for HAR
(fixed window, OLS) while giving the ML model a full tuning budget. When
both models receive equal care (rolling windows, feature selection, proper
tuning), the gap shrinks or disappears for daily RV with standard features.

> **Key Idea: Where the ML Gains Come From**
> The gains from ML come from richer features and longer horizons, not from
> nonlinear modeling of the same three RV lags that HAR uses. If your tree
> model does not beat HAR on the same features, you have overfit noise
> ([Chapter 6](ch06-har-model.md)). If it does beat HAR, check whether the gain
> survives the Diebold--Mariano test and Deflated Sharpe Ratio
> ([Chapter 16](ch16-forecast-evaluation.md)).

## Ensemble with HAR

The Honest Assessment section revealed a tension: trees win most days but
fail in stress. HAR is robust in stress but misses nonlinear patterns in
calm periods. The natural solution: combine them.

Rahimikia and Poon (2020) propose exactly this. Their ML model (a
random forest, but the logic extends to any tree ensemble) beats HAR on
roughly 90% of out-of-sample days. On the remaining 10% (concentrated
during stress), HAR wins decisively. The combined forecast outperforms both
standalone models.

### Simple weighted average

The simplest combination:

$$\hat{\sigma}^2_{\text{combo},t}
  = w \cdot \hat{\sigma}^2_{\text{HAR},t}
  + (1-w) \cdot \hat{\sigma}^2_{\text{tree},t},$$

where $w \in [0,1]$ is estimated by minimizing $\operatorname{QLIKE}$ on a purged
validation set. Typical values: $w \in [0.2, 0.4]$, giving the tree model
majority weight but retaining HAR's stabilizing influence.

- $\hat{\sigma}^2_{\text{HAR},t}$ is the HAR forecast from
  [Chapter 6](ch06-har-model.md).
- $\hat{\sigma}^2_{\text{tree},t}$ is the LightGBM or XGBoost
  forecast.
- $w$ is the HAR weight, estimated on the validation set.

> **Intuition: In Plain English**
> This is a weighted average of two forecasts. When $w = 0.3$, the combined
> forecast is 30% HAR and 70% tree. The weight is not a guess; you pick the
> $w$ that minimizes QLIKE on a held-out validation set. The result inherits
> the tree's ability to capture nonlinear patterns while retaining HAR's
> stability during extreme events.

> **Project Connection: Why This Matters**
> The HAR + tree combination is a strong candidate for the final model in the
> GS project. It addresses the key weakness of standalone tree models
> (poor extrapolation in stress regimes) while preserving the QLIKE gains
> that trees deliver in normal markets. Tuning $w$ on a purged validation
> set takes seconds, and the resulting ensemble is simple to explain to
> stakeholders.

### Regime-switching combination

A more sophisticated version: let $w$ depend on the current regime. Define
a "stress indicator" $s_t$ (e.g., $s_t = \mathbf{1}[\text{VIX}_t > 30]$ or
a GMM-based regime probability). Then:

$$\hat{\sigma}^2_{\text{combo},t}
  = w(s_t) \cdot \hat{\sigma}^2_{\text{HAR},t}
  + [1 - w(s_t)] \cdot \hat{\sigma}^2_{\text{tree},t},$$

with $w(s_t)$ increasing during stress (rely more on HAR when volatility is
elevated). This connects directly to the regime overlay in
[Chapter 13](ch13-hybrid-ensemble.md).

> **Intuition: In Plain English**
> Instead of using a fixed blend, the regime-switching version asks: "are
> markets calm or stressed right now?" In calm markets, it trusts the tree
> model more. In stressed markets, it shifts weight toward HAR, which
> extrapolates more reliably when volatility spikes to levels unseen in
> training data. The stress indicator $s_t$ acts as a dial that adjusts the
> blend in real time.

> **Project Connection: Why This Matters**
> The regime-switching combination is the bridge to [Chapter 13](ch13-hybrid-ensemble.md)'s
> full hybrid architecture. If your holdout period includes a volatility
> spike (e.g., a VIX jump above 30), this adaptive weighting can recover
> QLIKE losses that a fixed-weight blend would miss. It also provides a
> natural way to incorporate the VIX regime indicator from
> [Chapter 10](ch10-feature-engineering.md) into the forecast combination step.

> **Intuition: Why Combining Works**
> HAR and tree ensembles make different types of errors. HAR's errors are
> small and unbiased in calm periods, large but mean-reverting in stress.
> Tree errors are small in calm periods but can be persistently biased during
> regimes unseen in training. Averaging diversifies the error, the same
> principle behind portfolio diversification.

## DART: Dropout Regularization for Boosted Trees

The Hyperparameters for Volatility Data section covered the standard regularization
toolkit for gradient boosting: shallow trees, subsampling, and slow learning
rates. There is one more technique worth understanding, and it addresses a
subtle failure mode that the standard controls do not.

### The over-specialization problem

Recall from the ensemble prediction equation that standard gradient boosting
shrinks every tree's contribution by the same learning rate $\eta$. Early
trees see large residuals (the raw signal), so they learn the dominant
pattern: the strong autoregressive relationship between lagged $\operatorname{RV}$ and
future $\operatorname{RV}$. Later trees see only the leftover residuals after those early
trees have already captured the bulk of the variance. Shrinkage treats every
tree identically, so the early trees permanently dominate the ensemble's
output.

This creates a problem called **over-specialization**: later trees
become highly specialized to the narrow residual signal left by the first
few trees. If those early trees overfit to noise in the training data, every
subsequent tree inherits that bias. The ensemble's predictions become overly
dependent on a small number of early trees.

> **Intuition: In Plain English**
> Imagine a group project where one person does most of the work in the first
> week. Everyone else spends the remaining weeks patching small gaps in that
> person's draft. If the first person made a fundamental error, the entire
> project is built on a flawed foundation, and no amount of patching fixes it.
> Standard shrinkage is like asking everyone to speak more quietly; it does not
> change the fact that the first speaker set the direction.

### Dropout applied to trees

**DART** (Dropouts meet Multiple Additive Regression Trees) solves
over-specialization by borrowing the dropout idea from neural networks
(Vinayak and Gilad-Bachrach, 2015). In each boosting round, instead of computing
residuals from the full ensemble, DART randomly **drops** (removes) a
subset of the previously built trees. The new tree is then trained on the
residuals of the *reduced* ensemble, the one with the dropped trees
removed.

Concretely, let $\mathcal{D} \subset \{1, \ldots, m-1\}$ denote the set of
tree indices dropped at round $m$, chosen by including each tree
independently with **drop rate** $p$. The prediction used to compute
residuals becomes:

$$\hat{y}^{(\text{drop})}_t
  \;=\; \sum_{k \notin \mathcal{D}} h_k(\mathbf{x}_t),$$

where:

- $h_k(\mathbf{x}_t)$ is the prediction of tree $k$ for observation $t$
  (already including its learned weight),
- $\mathcal{D}$ is the random dropout set for this boosting round,
- $\hat{y}^{(\text{drop})}_t$ is the reduced ensemble prediction
  (with dropped trees excluded).

The new tree $h_m$ is fitted to the residuals
$r_t = y_t - \hat{y}^{(\text{drop})}_t$. Because some trees were dropped,
these residuals are larger than they would be under the full ensemble, so the
new tree must learn to compensate for the missing trees. This forces it to
capture general patterns rather than narrow residual corrections.

> **Intuition: In Plain English**
> Dropout randomly benches some of the existing team members during each
> training round. The new recruit (tree) has to pick up their slack, which
> means learning broadly useful patterns rather than hyper-specialized
> corrections. After training, all trees are brought back for the final
> prediction. The result is an ensemble where each tree carries more
> independent information.

### Prediction normalization

After fitting the new tree $h_m$, DART must normalize the ensemble so that
adding the new tree does not inflate predictions. The dropped trees and the
new tree are rescaled so the ensemble stays calibrated:

$$\hat{y}_t
  \;=\; \sum_{k \notin \mathcal{D}} h_k(\mathbf{x}_t)
  \;+\; \frac{|\mathcal{D}|}{|\mathcal{D}| + 1}\,
  \sum_{k \in \mathcal{D}} h_k(\mathbf{x}_t)
  \;+\; \frac{1}{|\mathcal{D}| + 1}\, h_m(\mathbf{x}_t),$$

where:

- $|\mathcal{D}|$ is the number of dropped trees,
- the factor $\frac{|\mathcal{D}|}{|\mathcal{D}|+1}$ rescales the
  dropped trees down to make room for the new tree,
- the factor $\frac{1}{|\mathcal{D}|+1}$ rescales the new tree so it
  contributes an "equal share" alongside the dropped trees.

> **Intuition: In Plain English**
> Without normalization, the new tree would be trained against a gap left by
> the dropped trees (large residuals), so its raw predictions would be too
> large. The normalization splits the "budget" of the dropped trees evenly
> between the returning dropped trees and the new tree. Think of it as
> redistributing playing time: the dropped players come back at slightly
> reduced minutes, and the new player gets a fair share.

### DART versus standard shrinkage

The key difference from the learning rate $\eta$ in standard boosting:

| | **Shrinkage** ($\eta$) | **DART** (drop rate $p$) |
|---|---|---|
| **Mechanism** | Scales *every* tree by the same constant $\eta$ | Randomly removes *entire trees* each round |
| **Effect on early trees** | Reduced proportionally but still dominant | May be dropped, forcing later trees to learn independently |
| **Diversity** | All trees see residuals from the same full ensemble | Each tree sees residuals from a different random subset |
| **Analogy** | Turning down everyone's volume equally | Randomly muting some speakers so others must step up |

Shrinkage and DART are not mutually exclusive. In LightGBM, you can set
`boosting_type='dart'` and still specify a learning rate, though in
practice the learning rate is often set higher with DART (e.g., 0.05--0.1)
because the dropout itself provides regularization.

> **Project Connection: DART for Volatility Forecasting**
> Over-specialization is particularly relevant for $\operatorname{RV}$ forecasting. The
> dominant signal in volatility data is the autoregressive persistence captured
> by HAR's three lagged averages ([Chapter 6](ch06-har-model.md)). In standard
> boosting, the first few trees learn this persistence, and all subsequent
> trees become narrowly specialized to small residual patterns that may not
> generalize. DART forces later trees to occasionally reconstruct the
> autoregressive signal on their own, building redundancy into the ensemble
> and reducing dependence on any single tree's overfitting.
>
> In LightGBM, enable DART by setting `boosting_type='dart'`. The key
> hyperparameter is the drop rate: start with
> `drop_rate` $\in [0.05, 0.15]$ and tune via purged CV
> (the Hyperparameters for Volatility Data section). Higher drop rates increase diversity
> but slow convergence; lower rates approach standard GBDT behavior. Note that
> DART disables early stopping (because the loss is non-monotone due to random
> dropping), so you must set `num_iterations` explicitly rather than
> relying on patience-based stopping.

> **Warning: DART Disables Early Stopping**
> With standard GBDT, you monitor validation loss and stop when it plateaus.
> DART's random dropout makes the validation loss noisy and non-monotone from
> round to round, so early stopping triggers prematurely. When using DART,
> fix the number of boosting rounds via cross-validation rather than relying
> on early stopping. This increases tuning cost, but the regularization
> benefit of dropout often compensates.

## Summary

1. Tree-based ensembles (LightGBM, XGBoost) are the default ML model for
   tabular volatility data because they automatically discover nonlinear
   interactions and threshold effects.

2. Gradient boosting builds the forecast sequentially: each tree corrects
   the residual errors of the ensemble so far (the ensemble prediction equation).

3. For volatility forecasting, use a custom $\operatorname{QLIKE}$ loss
   (the QLIKE loss and its gradient/Hessian equations), not the
   default MSE loss.

4. Default hyperparameters overfit on small volatility samples. Use
   shallow trees (`max_depth` 3--5), large minimum leaf sizes
   (50--200), aggressive subsampling (0.6--0.8), and slow learning rates
   (0.01--0.05) with early stopping on a purged validation set.

5. Christensen, Siggaard, and Veliyev (2023): trees are among the best for
   daily RV forecasting, with gains amplified by richer feature sets and
   longer horizons.

6. The Optiver Kaggle competition confirms that feature engineering
   matters far more than model architecture: trees plus good features beat
   deep learning plus raw data.

7. With RV-only features at daily horizons, HAR is extremely competitive.
   Trees offer 0--5% $\operatorname{QLIKE}$ improvement, often not significant.

8. With rich features (implied vol, jumps, cross-asset) at daily
   horizons, trees win by 5--20% in $\operatorname{QLIKE}$.

9. At intraday horizons, trees are clearly necessary; HAR was not
   designed for this regime.

10. During extreme stress, tree models tend to underperform HAR because
    they extrapolate poorly from calm-period training data.

11. Combining HAR and tree forecasts (the weighted-average combination equation)
    captures the best of both: the tree's nonlinear skill in calm markets
    and HAR's robustness in stress (Rahimikia and Poon, 2020).

12. Branco, Rubesam, and Zevallos (2024) and Bollerslev, Medeiros, Patton, and Quaedvlieg (2024) caution
    that many ML-beats-HAR claims reflect unfair comparisons. When both
    models are properly tuned, the gap is smaller than headline numbers
    suggest.

13. DART (Vinayak and Gilad-Bachrach, 2015) applies dropout to boosted trees:
    randomly dropping previous trees during each boosting round prevents
    over-specialization, where later trees become overly dependent on early
    trees that captured the dominant autoregressive signal. Use
    `drop_rate` $\in [0.05, 0.15]$; note that DART disables early
    stopping.

14. The gains from ML come from richer features and longer horizons, not
    from nonlinear modeling of the same three RV lags. [Chapter 12b](ch12b-deep-learning-vol.md)
    explores whether deep learning changes this conclusion.

---

| **Paper** | **Key Result** | **Relevance** |
|---|---|---|
| Christensen, Siggaard, and Veliyev (2023) | Trees among best for daily RV; gains grow with feature richness and horizon length | Primary evidence for the CSV Evidence and Honest Assessment sections |
| Branco, Rubesam, and Zevallos (2024) | Linear models competitive when comparison is fair | Calibrates expectations in the Honest Assessment section |
| Bollerslev, Medeiros, Patton, and Quaedvlieg (2024) | Rolling-window HAR with proper window matches off-the-shelf ML | Strongest HAR defense |
| Rahimikia and Poon (2020) | ML beats HAR 90% of days, fails in stress; ensemble solves it | Motivates the Ensemble with HAR section |
| Audrino and Knaus (2016) | QLIKE-optimized trees outperform MSE-optimized trees for RV | Justifies custom loss in the LightGBM and XGBoost section |
| Gu, Kelly, and Xiu (2020) | Trees and neural nets dominate linear models in cross-sectional return prediction with rich features | Canonical ML horse-race; context for tree methods |
| Vinayak and Gilad-Bachrach (2015) | Dropout for boosted trees reduces over-specialization; each tree learns more independently | Regularization technique in the DART section |
