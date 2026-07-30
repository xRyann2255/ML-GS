# Comprehensive Q&A Card -- ML Realized Volatility Forecasting

**Purpose:** Exhaustive reference for any question during/after the presentation.  
**Model:** Trial-036 champion (LightGBM residual stack on HAR-IV with tenor-matched init_score)

---

## Table of Contents

1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [HAR Family Baselines](#2-har-family-baselines)
3. [LightGBM -- How It Works (Deep Dive)](#3-lightgbm--how-it-works-deep-dive)
4. [Residual Stacking & init_score](#4-residual-stacking--init_score)
5. [QLIKE -- Loss Function](#5-qlike--loss-function)
6. [Feature Engineering (All 7 Layers)](#6-feature-engineering-all-7-layers)
7. [SHAP -- How It Works (Deep Dive)](#7-shap--how-it-works-deep-dive)
8. [ALE Plots -- How They Work (Deep Dive)](#8-ale-plots--how-they-work-deep-dive)
9. [Cross-Validation & OOS Testing](#9-cross-validation--oos-testing)
10. [Statistical Tests (DM, MCS, MZ)](#10-statistical-tests-dm-mcs-mz)
11. [GSVIVS01 Signal Application](#11-gsvivs01-signal-application)
12. [Variance Swap Strike (Kvar)](#12-variance-swap-strike-kvar)
13. [Results & Key Numbers](#13-results--key-numbers)
14. [Common Challenges & Failure Modes](#14-common-challenges--failure-modes)
15. [Anticipated Questions](#15-anticipated-questions)

---

## 1. Project Overview & Architecture

### What is this project?

An ML system that forecasts next-day realized volatility (RV) for SPX/equities, producing a trading signal for GSVIVS01 -- a daily short-variance index on 0-DTE SPXW options.

### Architecture (one sentence)

**HAR-IV** (4-parameter linear model) provides the `init_score` prior → **LightGBM** (gradient-boosted trees with custom QLIKE objective) learns 128 nonlinear features' residual contribution → signal compares forecast RV to variance swap strike → go short variance or stay flat.

### Universe & Data

| Dimension | Detail |
|-----------|--------|
| Symbols | 21 (17 mega-cap equities + 4 ETFs) -- pooled training |
| History | 11.3 years (2015-01-02 to 2026-05-30) |
| Observations | ~58,800 total (21 × 2,800 per symbol) |
| Tick data | L1 for all symbols (5-min returns for RV) |
| IV surface | SPX only (Marquee EDRVOL_PERCENT) -- all tenors (0DTE through 3M) |
| Target | $\log(RV_{t+h})$ -- forward log realized variance at horizons h=1, 5, 22 |

### Why pooled training?

Cross-symbol learning. The VRP structure, leverage effect, and calendar patterns are shared across assets. Pooling gives 21× more data per fold. Per-symbol training works for SPY alone but fails for less-liquid names (insufficient data for 128 features). The model learns symbol-specific behavior through the per-symbol IV features.

---

## 2. HAR Family Baselines

### HAR (Corsi 2009) -- The Foundation

$$\log \widehat{RV}_{t+1} = \beta_0 + \beta_d \log RV_t + \beta_w \log \overline{RV}_{t-4:t} + \beta_m \log \overline{RV}_{t-21:t}$$

Three features, one linear regression. Captures the **heterogeneous market hypothesis**: different market participants operate on different timescales (day traders → daily, portfolio managers → weekly, pension funds → monthly).

### Why log-space?

- RV is approximately log-normally distributed → log-RV ≈ Gaussian
- Symmetric, well-behaved residuals
- Prevents negative variance forecasts by construction
- Retransformation uses Duan (1995) bias correction: $\hat{\sigma}^2 = \exp(\hat{y}) \cdot E[\exp(\epsilon)]$

### HAR Variants

| Model | Features | Key Insight |
|-------|----------|-------------|
| **HAR** | log_rv_{d,w,m} | Pure persistence across 3 timescales |
| **HARQ** | + $\sqrt{RQ_t} \times \log RV_t$ | Discount noisy RV observations (Bollerslev et al. 2016) |
| **SHAR** | Replace daily with RS⁺, RS⁻ | Leverage effect: down vol predicts future vol more (Patton & Sheppard 2015) |
| **HAR-J** | + log(jump component) | Jumps predict short-term vol spikes |
| **HAR-CJ** | + continuous + jump separately | Disentangle smooth and discontinuous vol |
| **HAR-IV** | + log(ATM IV) | Forward-looking info from options market -- **dominates all others** |
| **Ridge/Lasso-HAR** | Same features, regularized | Stabilize in pooled training |

### HAR-IV: Why It Dominates

Adding log ATM IV as a 4th regressor gives forward-looking information -- IV embeds the market's expectation of future vol. HAR-IV dominates pure HAR by **100+ basis points in QLIKE** at every horizon. The options market aggregates information from all participants; it's essentially a survey of future vol expectations.

### Tenor Matching (Trial-036 Key Innovation)

| Horizon | Base Model | IV Tenor | Why |
|---------|-----------|----------|-----|
| h=1 | `har_iv_0dte` | 0-DTE ATM IV | Prices exactly tomorrow's RV, zero term premium |
| h=5 | `har_iv_1w` | 1-week ATM IV | Exact match |
| h=22 | `har_iv` | 1-month ATM IV | Exact match |

Prior trials used 1-week IV for all horizons. The 0-DTE match for h=1 gained 8 bps by removing term premium contamination.

---

## 3. LightGBM -- How It Works (Deep Dive)

### Gradient Boosting Framework

The model is an additive ensemble of weak learners (shallow decision trees):

$$F_m(x) = F_{m-1}(x) + \eta \cdot h_m(x)$$

where $h_m$ is the tree fit at round $m$ and $\eta = 0.01$ is the learning rate (shrinkage).

### Newton Boosting (Second-Order)

LightGBM uses a second-order Taylor expansion of the loss:

$$\mathcal{L}(y_i, \hat{y}_i + \Delta) \approx \mathcal{L}(y_i, \hat{y}_i) + g_i \Delta + \frac{1}{2} h_i \Delta^2$$

where $g_i = \partial \mathcal{L}/\partial \hat{y}_i$ (gradient) and $h_i = \partial^2 \mathcal{L}/\partial \hat{y}_i^2$ (Hessian).

**Optimal leaf value:** For leaf $j$ containing samples $I_j$:

$$w_j^* = -\frac{\sum_{i \in I_j} g_i}{\sum_{i \in I_j} h_i + \lambda}$$

**Split gain formula** (decides whether to split a node):

$$\text{Gain} = \frac{1}{2}\left[\frac{\left(\sum_{i \in L} g_i\right)^2}{\sum_{i \in L} h_i + \lambda} + \frac{\left(\sum_{i \in R} g_i\right)^2}{\sum_{i \in R} h_i + \lambda} - \frac{\left(\sum_{i \in P} g_i\right)^2}{\sum_{i \in P} h_i + \lambda}\right] - \gamma$$

A split is only made if Gain > 0. The Hessian acts as per-sample adaptive learning rate.

### LightGBM-Specific Innovations (vs XGBoost)

**1. Gradient-Based One-Side Sampling (GOSS):**
- Keep all large-gradient samples (poorly fit), randomly subsample small-gradient ones
- Upweight the subsampled group by $(1-a)/b$ to preserve the gradient distribution
- Reduces data per split evaluation without losing information about hard-to-fit observations

**2. Exclusive Feature Bundling (EFB):**
- Bundle mutually exclusive features (never non-zero simultaneously) into single features
- Reduces effective feature count; particularly effective for sparse/one-hot features

**3. Histogram-based splits:**
- Discretize continuous features into 256 bins
- Split finding is O(#bins) not O(#data) -- cache-friendly
- Histogram subtraction: right_child = parent - left_child (halves cost)

**4. Leaf-wise (best-first) growth:**
- At each step, split the single leaf with highest gain (not all leaves at same depth)
- More efficient: fewer splits for same loss reduction
- Risk of overfitting → controlled by `num_leaves`, `max_depth`, `min_child_samples`

### Custom QLIKE Objective -- How It Integrates

LightGBM's split decisions depend entirely on gradients and Hessians. We provide:

$$g_i = 1 - \exp(y_i - \hat{y}_i) \quad\quad h_i = \exp(y_i - \hat{y}_i)$$

| Scenario | Gradient | Hessian | Behavior |
|----------|----------|---------|----------|
| Underprediction ($\hat{y} \ll y$) | Large negative | Large | Strong push up, tight Newton step |
| Perfect ($\hat{y} = y$) | 0 | 1 | No update |
| Overprediction ($\hat{y} \gg y$) | Approaches +1 | Near 0 | Weak push down |

**Key asymmetry:** Underprediction produces large gradients → dominates split gain → trees preferentially learn to correct underprediction. This matches the economic reality (underestimating vol = selling options too cheap = blowup risk).

### Trial-036 Hyperparameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `n_estimators` | 5000 | High ceiling; early stopping picks best |
| `early_stopping_rounds` | 150 | Patient -- 150 rounds × 0.01 lr = 1.5 "full trees" of exploration |
| `learning_rate` | 0.01 | Low rate + many trees = smooth generalization |
| `num_leaves` | 16 | Shallow trees -- prevents memorizing noise |
| `max_depth` | 4 | Hard limit; captures up to 4-way interactions |
| `min_child_samples` | 150 | Each leaf needs 150 obs (≥0.3% of training data) |
| `feature_fraction` | 0.8 | Column subsampling -- decorrelates sequential trees |
| `bagging_fraction` | 0.8 | Row subsampling every 3 rounds |
| `reg_lambda` | 5.0 | L2 on leaf weights: $w^* = -\sum g / (\sum h + 5.0)$ |
| `reg_alpha` | 0.1 | L1 -- mild feature selection within trees |

**Why these are conservative:** With 52,500 training rows and min_child_samples=150, each leaf represents ≥0.3% of data. Depth-4 trees model at most 4-way interactions. The model typically early-stops at ~800-1200 rounds (not 5000). This trades training fit for OOS stability.

### Why LightGBM (Not Deep Learning)?

- Handles mixed types + NaN natively (no imputation pipeline)
- Captures nonlinear interactions automatically via split cascades
- Custom QLIKE objective → splits optimize for actual trading loss
- Fast: ~3-5s per fit → 75 fits (15 folds × 5 seeds) in ~5 minutes
- TreeSHAP gives exact explainability for free
- **h=22 result proves the point:** at monthly horizon, 4-parameter HAR-IV beats 128-feature LightGBM. More parameters ≠ better. ML adds value only where nonlinear structure exists (short-term dynamics).

---

## 4. Residual Stacking & init_score

### How It Works

1. Fit HAR-IV on the training fold → baseline predictions $\hat{y}_{base}$
2. Feed $\hat{y}_{base}$ as `init_score` to the LightGBM dataset
3. LightGBM's QLIKE objective sees the full target but starts from the linear prediction
4. Trees learn: $f_{tree}(x)$ where final prediction = $\hat{y}_{base}(x) + f_{tree}(x)$

### Why init_score ≠ Training on Residuals

| Approach | Round-0 Gradient | Round-0 Hessian |
|----------|-----------------|-----------------|
| **init_score** | $g_i = 1 - \exp(y_i - \hat{y}_{HAR})$ -- full QLIKE relative to HAR | $h_i = \exp(y_i - \hat{y}_{HAR})$ -- adaptive per obs |
| **Explicit residuals** | Gradients relative to zero, not the base | Loses absolute-level information |

With init_score, the loss curvature accounts for the absolute prediction level. An observation where HAR-IV predicts 15% vol and realized is 20% gets a different Hessian than one where HAR-IV predicts 30% and realized is 35%, even though both have the same residual.

### Why It Helps

1. **HAR-IV already captures linear structure** -- trees don't waste capacity rediscovering persistence + IV
2. **Trees focus on nonlinear residuals** -- regime effects, interactions, calendar patterns
3. **Faster convergence** -- fewer rounds needed → less overfitting
4. **Interpretable decomposition** -- "linear base" vs "tree correction" QLIKE attribution

---

## 5. QLIKE -- Loss Function

### Formula

In variance space:
$$QLIKE = \frac{1}{T}\sum_{t=1}^{T} \left[\frac{RV_t}{\hat{h}_t} - \log\frac{RV_t}{\hat{h}_t} - 1\right]$$

In log-space (how we compute it):
$$QLIKE = \frac{1}{T}\sum_{t=1}^{T} \left[\exp(y_t - \hat{y}_t) - (y_t - \hat{y}_t) - 1\right]$$

Minimized when $RV_t / \hat{h}_t = 1$ for all $t$ (perfect forecast).

### Why Not MSE? (Three Reasons)

**1. Scale invariance.** A 2× overestimate at 10% vol = same QLIKE penalty as 2× overestimate at 40% vol. MSE penalizes absolute error → COVID observations dominate everything.

**2. Economic alignment.** QLIKE's natural asymmetry:
- 2× underestimate (forecast half of actual): QLIKE contribution = 0.31
- 2× overestimate (forecast double actual): QLIKE contribution = 0.19

Underpredicting vol is catastrophically worse economically (sell options too cheap, underestimate risk).

**3. Patton (2011) proxy robustness.** We never observe true integrated variance -- only RV (a noisy proxy). Patton proved that QLIKE produces **consistent model rankings** regardless of proxy noise. MSE rankings can **flip** depending on noise realization. This is a theorem, not a heuristic.

### QLIKE as Custom LightGBM Objective

Gradient: $g_i = 1 - \exp(y_i - \hat{y}_i)$  
Hessian: $h_i = \exp(y_i - \hat{y}_i)$

The gradient is asymmetric: underprediction ($\hat{y} < y$) produces gradients up to $-\infty$; overprediction saturates at +1. Trees trained with QLIKE produce different splits than MSE-trained trees.

### The MSE vs QLIKE Consequence

MSE-optimized model → Sharpe ~0.3 on GSVIVS signal.  
QLIKE-optimized model → Sharpe ~1.95 on GSVIVS signal.  
**The loss function choice is not academic -- it's the difference between noise and a tradeable signal.**

---

## 6. Feature Engineering (All 7 Layers)

### Layer 0: HAR Core (`har_core`)

| Feature | Formula | Purpose |
|---------|---------|---------|
| `log_rv_d` | $\log(RV_t)$ | Daily persistence |
| `log_rv_w` | $\log(\bar{RV}_{5d})$ | Weekly persistence |
| `log_rv_m` | $\log(\bar{RV}_{22d})$ | Monthly persistence |
| `sqrt_rq_d` | $\sqrt{RQ_t}$ where $RQ = \frac{n}{3}\sum r_i^4$ | Measurement quality |
| `rq_rv_interaction_d` | $\log(RV_t) \times \sqrt{RQ_t}$ | Discount noisy RV |
| `overnight_return` | $\log(Open_t / Close_{t-1})$ | Overnight gap information |

### Layer 1: Asymmetry (`asymmetry`)

| Feature | Formula | Purpose |
|---------|---------|---------|
| `log_rs_positive_d/w/m` | $\log(\sum r_i^2 \cdot \mathbf{1}_{r_i > 0})$ | Upside semivariance |
| `log_rs_negative_d/w/m` | $\log(\sum r_i^2 \cdot \mathbf{1}_{r_i < 0})$ | Downside semivariance (leverage effect) |
| `log_bpv_d/w` | $\log(\frac{\pi}{2}\frac{1}{n-1}\sum|r_i||r_{i+1}|)$ | Continuous variation (jump-robust) |
| `log_jump_d` | $\log(\max(RV - BPV, 0))$ | Jump component |
| `log_cont_d/w` | $\log(RV - J)$ if jump detected | Smooth volatility |
| `signed_return_d` | Daily log return | Leverage effect proxy |
| `abs_ret_d/w` | $|r_t|$, $MA_5(|r_t|)$ | Shock magnitude |

### Layer 2: IV Surface (`iv_surface`) + Options (`options`)

| Feature | Source | Purpose |
|---------|--------|---------|
| `log_atm_iv_d/w/m` | EDRVOL 1-month | IV level (primary forward signal) |
| `log_atm_iv_0dte_d` | EDRVOL 0-DTE | Exact next-day pricing |
| `log_atm_iv_1w_d` | EDRVOL 1-week | Short-term IV |
| `iv_term_slope_*` | Various tenor differences | Term structure shape |
| `vrp_d/w/m` | $(IV/100)^2 - RV \times 252$ | Variance risk premium |
| `iv_skew_d/w` | $IV_{25\delta P} - IV_{25\delta C}$ | Tail demand (risk reversal) |
| `iv_butterfly_d/w` | $\frac{1}{2}(IV_{25\delta P} + IV_{25\delta C}) - IV_{ATM}$ | Kurtosis premium |
| `vvix_d` | $VVIX/100$ | Vol-of-vol |
| `atm_iv_x_log_rv_d/w/m` | $IV_{ATM} \times \log(RV)$ | **#1 ML gain source** -- regime interaction |
| `iv_dispersion_d` | Cross-sectional std of IVs | Market dispersion |

**Why IV×RV interactions dominate:** The relationship between implied and realized vol is *regime-dependent*. In low-vol environments, VRP is stable and HAR-IV captures it linearly. In high-vol regimes, VRP compresses nonlinearly. The interaction term lets the tree learn this regime-dependence.

### Layer 3: Noise-Robust (`noise_robust`)

| Feature | Formula | Purpose |
|---------|---------|---------|
| `log_rk_d/w` | $\log(RK_t)$ -- realized kernel | Noise-corrected volatility (Barndorff-Nielsen 2008) |
| `noise_gap_d/w` | $RV_t - RK_t$ | Microstructure noise estimate |
| `vol_anomaly` | $\log(N_{ticks}) - MA_{22}(\log N_{ticks})$ | Unusual trading activity |

### Layer 4: Calendar (`calendar`)

| Feature | Type | Purpose |
|---------|------|---------|
| `days_to_fomc` | Integer [0, 45] | FOMC proximity (vol compression/spike) |
| `days_to_nfp` | Integer [0, 23] | Non-Farm Payrolls proximity |
| `days_to_opex` | Integer [0, 23] | Options expiration proximity |
| `day_of_week` | Categorical | Monday effect, Friday effect |
| `quarter_end` / `year_end` | Binary | Rebalancing periods |

Calendar features are known in advance -- no shift needed. FOMC proximity is a strong predictor: vol compresses before (dealers hedge by selling) then spikes on announcement.

### Layer 5: Tree Expansion (`tree_expansion`)

For every continuous feature from layers 0–4:

| Transform | Formula | Purpose |
|-----------|---------|---------|
| `{name}_change` | $x_t - x_{t-1}$ | Momentum/mean-reversion signal |
| `{name}_zscore` | $(x_t - MA_{20}(x)) / \sigma_{20}(x)$ | Standardized deviation from norm |

Doubles feature count (~65 → ~128). Z-score features tell the model "this isn't just the level of VRP, but whether VRP is *unusually* high relative to recent history." Collectively contribute ~9% of total importance.

### Total Feature Count: ~128

7 layers × various features, with tree expansion doubling continuous features. All 128 are used by the model (no feature selection -- LightGBM handles this internally via split gain).

---

## 7. SHAP -- How It Works (Deep Dive)

### Game-Theoretic Foundation: Shapley Values

SHAP is rooted in **cooperative game theory** (Shapley 1953). For a game with $N = \{1, \ldots, p\}$ players and value function $v$:

$$\phi_i = \sum_{S \subseteq N \setminus \{i\}} \frac{|S|! \cdot (|N| - |S| - 1)!}{|N|!} \left[v(S \cup \{i\}) - v(S)\right]$$

**Term-by-term:**
- $S \subseteq N \setminus \{i\}$ -- all coalitions NOT containing player $i$ (there are $2^{p-1}$ of them)
- $v(S \cup \{i\}) - v(S)$ -- **marginal contribution** of player $i$ when joining coalition $S$
- $\frac{|S|!(|N|-|S|-1)!}{|N|!}$ -- **weighting factor**: fraction of all player orderings where exactly $S$ arrives before $i$

**Equivalently:** the average marginal contribution across all possible arrival orderings:
$$\phi_i = \frac{1}{|N|!} \sum_{\pi \in \Pi(N)} \left[v(S_i^\pi \cup \{i\}) - v(S_i^\pi)\right]$$

### The Four Shapley Axioms (Uniqueness)

These are the UNIQUE values satisfying all four axioms simultaneously. No other allocation rule does this.

**1. Efficiency:**
$$\sum_{i=1}^{p} \phi_i = v(N) - v(\emptyset)$$
SHAP values sum exactly to prediction minus base value. Nothing unexplained.

**2. Symmetry:** If $v(S \cup \{i\}) = v(S \cup \{j\})$ for all $S$, then $\phi_i = \phi_j$.
Interchangeable features get equal credit.

**3. Dummy:** If $v(S \cup \{i\}) = v(S)$ for all $S$, then $\phi_i = 0$.
Uninformative features get zero attribution.

**4. Linearity:** $\phi_i^{v+w} = \phi_i^v + \phi_i^w$
For ensembles: SHAP of sum of trees = sum of per-tree SHAP values.

### From Game Theory to ML

**Players** = features. **Value function:**
$$v(S) = E[f(X) \mid X_S = x_S]$$

"If we only know features in $S$, what's our best prediction?" Unknown features are marginalized over their conditional distribution.

**For the full model:**
$$\hat{y}_i = \underbrace{E[f(X)]}_{\phi_0} + \sum_{j=1}^{p} \phi_{ij}$$

This decomposition is **exact** for tree models -- no approximation.

### TreeSHAP Algorithm (Lundberg et al. 2020)

**The problem:** Naive Shapley requires $2^p$ evaluations. With $p = 128$, that's $3.4 \times 10^{38}$ -- intractable.

**TreeSHAP:** Exact Shapley values in polynomial time: $O(T \cdot L \cdot D^2)$

For our model: $O(800 \times 16 \times 16) = O(204,800)$ per observation -- trivially fast.

**How it works:**
1. For each tree, traverse from root to leaves
2. At each internal node (split on feature $j$ at threshold $\tau$):
   - If feature $j$ is IN the coalition → follow the observed path
   - If feature $j$ is OUT → follow BOTH branches, weighted by training data proportions
3. At each leaf: weighted value contributes to $v(S)$
4. The **EXTEND/UNWIND recursion** maintains all $2^D$ coalition combinations simultaneously in $O(D^2)$ time per path

**Key insight:** Trees partition feature space into axis-aligned rectangles. The conditional expectation $E[f(X)|X_S = x_S]$ is a weighted average of leaf values where weights = fraction of training data consistent with the known features in $S$. The tree IS the efficient computation structure for its own Shapley values.

### Two Modes: Path-Dependent vs Interventional

- **`tree_path_dependent`** (our default): Uses the tree's internal data distribution. Conditions on observed features using the tree's learned splits.
- **`interventional`**: Marginalizes over the background data distribution (treats features as independent). Better for causal interpretation but overattributes to correlated features.

We use path-dependent because our features are highly correlated (log_rv_d, log_rv_w, log_rv_m share information).

### Implementation Details

```python
explainer = shap.TreeExplainer(booster)  # LightGBM Booster
shap_values = explainer.shap_values(X_test[:500])  # Subsample for speed
```

- Subsample 500 OOS observations (top-10 features converge by ~200 samples)
- Mean |SHAP| per feature gives global importance ranking
- Applied to RESIDUAL predictions only -- SHAP explains what trees add beyond HAR-IV
- Beeswarm: x = SHAP value (contribution), y = feature rank, color = feature value

### Interpreting SHAP for This Model

- Positive SHAP → trees predict MORE vol than HAR-IV alone
- The init_score is NOT included -- SHAP only explains the tree correction
- Top features: IV×RV interactions (regime-dependent VRP), calendar (nonlinear FOMC pattern), z-scores (mean-reversion at extremes)
- Per-observation decomposition enables debugging: "Why did the model get today wrong? Which feature was responsible?"

---

## 8. ALE Plots -- How They Work (Deep Dive)

### The Problem with Partial Dependence Plots (PDP)

PDP formula:
$$\hat{f}_j^{PDP}(x_j) = \frac{1}{n}\sum_{i=1}^n f(x_j, x_{-j}^{(i)})$$

PDP fixes feature $j$ at value $x_j$ and averages over ALL other feature values -- including **impossible combinations**. Example: setting VIX=10 while keeping log_rv_d=-2.5 (extremely high vol) never occurs in reality. PDP extrapolates into zero-density regions → biased effects.

### ALE Solution (Apley & Zhu, 2020)

ALE only evaluates within the **conditional distribution** $p(x_{-j}|x_j)$:
- **PDP asks:** "What if I SET $x_j = v$ for all observations?"
- **ALE asks:** "Among observations WHERE $x_j \approx v$, what is the LOCAL effect of changing $x_j$ slightly?"

### Mathematical Definition

$$\hat{f}_{j,ALE}(x_j) = \int_{x_{j,\min}}^{x_j} E_{x_{-j}|x_j=z}\left[\frac{\partial f(x)}{\partial x_j}\bigg|_{x_j=z}\right] dz - c$$

where $c$ centers the curve to zero mean. We integrate the **conditional expectation of the partial derivative** -- isolating the pure effect of $x_j$ from correlated features.

### Discrete Algorithm (What the Code Does)

**Step 1 -- Binning:** Divide $x_j$ into $K = 50$ quantile bins: $z_0 < z_1 < \cdots < z_K$

**Step 2 -- Local effects per bin:** For each bin $k$ with $n_k$ observations:
$$\hat{\Delta}_k = \frac{1}{n_k} \sum_{i: x_{ij} \in (z_{k-1}, z_k]} \left[f(z_k, x_{-j}^{(i)}) - f(z_{k-1}, x_{-j}^{(i)})\right]$$

Take all observations in the bin, move ONLY feature $j$ from lower edge to upper edge (keep everything else at observed values), compute average prediction change.

**Step 3 -- Accumulate:** $\hat{f}_{j,ALE}(x_j) = \sum_{k=1}^{K(x_j)} \hat{\Delta}_k$

**Step 4 -- Center:** Subtract weighted mean so ALE curve averages to zero.

### Why ALE Works for Correlated Features

Example: `log_atm_iv_0dte_d` and `log_rv_d` have $\rho > 0.8$.

| Method | At high IV (95th percentile) |
|--------|------------------------------|
| **PDP** | Averages over ALL RV values including low RV. Model sees impossible (high IV, low RV) → inflated effect |
| **ALE** | Only looks at observations WHERE IV is high (naturally co-occurs with high RV). Computes local IV effect at natural conditional RV values → unbiased |

### Reading ALE Plots

| Pattern | Meaning |
|---------|---------|
| Flat region | Model insensitive to feature here |
| Steep positive slope | Higher feature → higher vol prediction |
| Non-monotonic | Complex relationship (e.g., mean-reversion) |
| Step/kink | Threshold effect |
| Sparse rug | Don't trust -- few observations |

Y-axis units: log-RV. An ALE of +0.1 means the model predicts +0.1 higher log-RV (≈ +10.5% multiplicative increase in RV).

### ALE vs SHAP -- Complementary

| Dimension | SHAP | ALE |
|-----------|------|-----|
| Scope | Per-observation (local) | Global (across range) |
| Question | "Why THIS prediction?" | "HOW does model use this feature?" |
| Correlation | Splits attribution (can mislead) | Isolates pure local effect (unbiased) |
| Use case | Importance ranking, anomaly debugging | Sanity-checking functional form |

**Practical workflow:** SHAP ranks features → ALE reveals the shape of learned relationships → verify shapes are economically sensible.

---

## 9. Cross-Validation & OOS Testing

### Expanding Window Walk-Forward

```
Fold 1: [2015–2017 train] | purge | [2017 H1 test]
Fold 2: [2015–2017 H1 train] | purge | [2017 H2 test]
...
Fold 15: [2015–2025 train] | purge | [2025 H2–2026 test]
```

| Parameter | Value | Why |
|-----------|-------|-----|
| Initial train | 504 days (~2 years) | Minimum for stable estimates |
| Test window | 126 days (~6 months) | Meaningful OOS evaluation period |
| Purge gap | 10 trading days | Prevent target overlap leakage |
| Step | 126 days | Non-overlapping test periods |

### Why Not Random K-Fold?

**NEVER** random k-fold on time series. Randomly shuffling observations allows future information into training. The temporal ordering IS the signal -- autocorrelation means nearby observations share information. Random splits overestimate performance by 2-5× in our tests.

### Panel-Aware Date Splits

With 21 symbols sharing dates, the purge gap is computed in DATES, not row indices. All symbols' observations within 10 dates of the test boundary are purged.

### Purged Validation for Early Stopping

Within each training fold:
- Last 15% of training data → validation for early stopping
- 10-day purge gap between train and validation
- Even the stopping criterion has no leakage

### Multi-Seed Confirmation

Single-seed results can be lucky. After trial-036 reported h=1 QLIKE of 0.1289, the 5-seed reseed (trial-047) showed mean 0.13679 -- original was below the 5-seed minimum. **All champion claims require ≥3 seeds, report mean ± std.**

---

## 10. Statistical Tests (DM, MCS, MZ)

### Diebold-Mariano Test

Tests $H_0$: Model A and B have equal predictive accuracy.

$$DM = \frac{\bar{d}}{\sqrt{\hat{V}(d)/T}} \quad \text{where } d_t = L_A(t) - L_B(t)$$

- $\hat{V}(d)$ uses Newey-West HAC standard errors (Bartlett kernel, bandwidth = $h-1$)
- Accounts for serial correlation in multi-step forecast errors
- Under $H_0$: $DM \sim N(0,1)$
- **Sign convention:** Positive DM = model 2 (ours) is better
- DM > 2 with p < 0.05 → statistically significant improvement

### Model Confidence Set (Hansen, Lunde & Nason 2011)

Identifies the SET of models containing the true best with 90% confidence:

1. Start with all models
2. Compute range statistic $T_R = \max_{i,j}|t_{ij}|$
3. Bootstrap $T_R$ under null (block bootstrap, 10,000 replicates, block = $\sqrt{T}$)
4. If p < 0.10: eliminate worst model. Repeat.
5. Otherwise: remaining models form the MCS.

If only our LightGBM + HAR-IV are in the MCS → we can reject (at 90% confidence) that any other model is as good.

### Mincer-Zarnowitz Regression

Tests forecast efficiency:
$$RV_t = \alpha + \beta \cdot \hat{h}_t + \epsilon_t$$

- Efficient forecast: $\alpha = 0, \beta = 1$ jointly (Wald F-test with HAC SEs)
- $\beta < 1$: forecast is too volatile (needs shrinkage)
- $\beta > 1$: forecast underreacts
- Passing MZ = forecasts are unbiased and properly calibrated

---

## 11. GSVIVS01 Signal Application

### What GSVIVS01 Does

Daily variance swap replication on 0-DTE SPXW options:
- 09:30 ET: sell weighted strip of ~15 OTM options (95%–101% of forward) via 30-min TWAP
- Through day: delta-hedge with ES futures (5-min clips, ~27/day)
- 16:00 ET: all options settle at MOC. Portfolio → cash.

Strip weights: $q_i \propto \Delta K_i / K_i^2$ -- discrete variance swap replication.

**No signal.** Mechanically sells variance every day. Pure short-vol carry (positive mean from VRP, left-tail drawdowns when RV > IV).

### Our Signal: IV-RV Gap

- If $K_{var} > \widehat{RV}$: **go short** variance (sell the strip) -- variance is overpriced
- If $K_{var} < \widehat{RV}$: **go flat** (don't trade) -- variance is underpriced, don't sell

Signal fires at 09:10 ET using:
- $\widehat{RV}$: model forecast (made at previous close, no lookahead)
- $K_{var}$: previous close's variance swap strike from EDRVS

### Edge Concentration

- Only ~2% of days does model predict RV > Kvar (signal = go flat)
- Those days have 70% precision -- 7/10 correctly predicted GSVIVS drawdowns
- The improvement is concentrated: avoiding ~10 bad days/year → 22% Sharpe boost
- Zero additional transaction costs (we simply don't trade on flat days)

---

## 12. Variance Swap Strike (Kvar)

### Carr-Madan Model-Free Formula (1998)

$$K_{var} = \frac{2}{T}\left[\int_0^F \frac{P(K)}{K^2}dK + \int_F^\infty \frac{C(K)}{K^2}dK\right]$$

- $F$ = forward price, $P(K)$/$C(K)$ = OTM put/call prices
- $1/K^2$ weighting gives more weight to OTM puts (higher IV due to skew)
- → $K_{var} > ATM\;IV$ always
- **Model-free:** no parametric assumptions about the volatility surface
- Falls from the replication argument: a variance swap is statically replicated by options weighted by $1/K^2$

### Why Not Just Use ATM IV?

ATM IV prices at-the-money options. The variance swap payoff $\sigma^2_{realized} - K_{var}$ depends on the ENTIRE vol surface (all strikes). Kvar correctly integrates over the full smile -- it's what GSVIVS actually sells against.

### Our Proxy

Currently: cached from risk-node marks in the index JSON (`gsvivs_kvar_daily.parquet`). Correlates >0.99 with true EDRVS Kvar. Improvement plan: fetch EDRVS_EXPIRY_INTRADAY (previous close's Kvar for today's expiry).

---

## 13. Results & Key Numbers

### QLIKE Results (5-seed means, trial-047)

| Horizon | Champion | QLIKE | vs HAR-IV (bps) | DM p-value |
|---------|----------|-------|-----------------|------------|
| h=1 | LightGBM + har_iv_0dte | **0.13679** | +153 bps | < 0.01 |
| h=5 | LightGBM + har_iv_1w | **0.10804** | +138 bps | < 0.01 |
| h=22 | HAR-IV (4 params!) | **0.16755** | LightGBM is -7 bps WORSE | NS |

### GSVIVS01 Signal Performance (h=1)

| Model | Sharpe | vs Always-Short |
|-------|--------|-----------------|
| LightGBM (QLIKE) | ~1.95 | +22% |
| Always-short baseline | ~1.6 | -- |
| LightGBM (MSE) | ~0.3 | Worse than baseline |

### Critical Insights

1. **h=22: Linear wins.** Monthly ATM IV already contains so much forward information that trees cannot improve on 4 parameters.
2. **Loss function matters more than model.** MSE→QLIKE is the difference between Sharpe 0.3 and 1.95.
3. **Multi-seed matters.** Single-seed QLIKE (0.1289) was 79 bps below the 5-seed mean (0.13679).
4. **Tenor matching matters.** 0DTE IV for h=1 gained 8 bps over 1-week IV by removing term premium contamination.

---

## 14. Common Challenges & Failure Modes

### Overfitting Risks

| Risk | Mitigation |
|------|-----------|
| 128 features, finite data | Conservative hyperparams (min_child=150, depth=4) |
| Many CV folds | Multi-seed validation (5 seeds minimum) |
| Feature selection bias | No selection -- let LightGBM handle via gain |
| Look-ahead in features | All features use strictly past data; 10-day purge gap |

### Known Limitations

- **h=22:** ML adds no value. HAR-IV's monthly IV is essentially an oracle at this horizon.
- **COVID sensitivity:** Including COVID in early folds degrades Sharpe by 0.59 (model becomes too cautious about rare events). Current config starts with 504-day window from 2015, so COVID enters training after 2022.
- **Single market:** Only tested on SPX universe. Cross-asset signals (FX vol, rates) are features but the *signal* is SPX-specific.
- **Kvar proxy:** Using cached marks, not live EDRVS. Slight level bias possible.

### What I'd Do Differently

- Start with multi-seed from day 1 (wasted time on single-seed champion claims)
- Test QLIKE objective earlier (tried MSE first for 3 weeks)
- HAR-IV init_score should be the default starting architecture for any vol forecasting project

---

## 15. Anticipated Questions

### "Why not deep learning / neural networks?"

The h=22 result: a 4-parameter linear model beats 128-feature GBM at monthly horizon. More parameters ≠ better. Volatility forecasting has high noise-to-signal; overfitting is the primary risk, not underfitting.

However: LSTM on raw intraday sequences (trial-051/052) is in flight for h=1, where intraday tick patterns may add information above daily aggregates. Early results show marginal improvement for high-vol days.

### "How do you handle COVID?"

COVID (Feb–Jun 2020) is in training data starting from fold ~3 onwards. We tested explicitly:
- Including COVID in earlier folds: improves QLIKE slightly but degrades Sharpe by 0.59 at h=1 (model becomes too cautious about rare tail events)
- Current config: 504-day initial window starting 2015, so COVID enters training after 2022
- No special regime indicator -- the model treats COVID observations like any other high-vol period

### "What about transaction costs?"

The signal is binary (short or flat). On "flat" days we simply don't open the strip -- zero TC. On "short" days, TC is already embedded in the GSVIVS01 index (mean -0.0265/day). Signal transitions are rare (~10/year), so no meaningful turnover cost.

### "Why pooled training across 21 symbols?"

21× more data per fold. The VRP structure, leverage effect, and calendar patterns are shared across assets. Per-symbol training works for SPY alone but fails for less-liquid names (insufficient data for 128 features). The model learns symbol-specific behavior through per-symbol IV features.

### "How do you know features aren't forward-looking?"

Every feature is computed using ONLY data available at time $t$ (end of day):
- Realized quantities (RV, BPV, RQ) use intraday returns up to market close
- IV features use closing marks (16:00 ET snap)
- Calendar features are deterministic (known in advance)
- All rolling averages use backward-looking windows only
- 10-day purge gap additionally prevents ANY indirect leakage through overlapping targets

### "What if the VRP disappears / regime changes?"

The model would stop working. Specifically:
- If VRP → 0 permanently (variance always fairly priced), the signal fires "go flat" every day → performance = cash (no loss, no gain)
- If VRP inverts (realized consistently > implied), the model should learn to go long variance → but we haven't backtested this regime extensively
- The expanding window CV means the model continuously adapts to regime changes (each fold trains on more recent data)

### "Can this be applied to other indices?"

The framework generalizes to any market with a liquid options surface and tick data for RV computation. Requirements:
- Liquid options surface (for IV features, especially short-tenor)
- Intraday tick data (for RV, RQ, BPV, jumps)
- Sufficient history (≥5 years for stable CV)
- A variance swap or options strip to trade against

Candidates: SPX (done), QQQ, IWM, EEM, single-stock names with high options liquidity.

### "Why QLIKE and not other robust loss functions?"

Alternatives considered:
- **HMSE** (Heteroskedastic MSE): $\sum (1 - RV/\hat{h})^2$ -- similar asymmetry but no Patton proxy robustness guarantee
- **Log-likelihood** (Gaussian): equivalent to MSE in log-space -- no scale invariance
- **Huber loss**: robust to outliers but symmetric -- doesn't penalize underprediction harder

QLIKE uniquely satisfies: (1) scale invariance, (2) underprediction asymmetry, (3) proxy robustness (Patton 2011 theorem). No other loss has all three.

### "How sensitive is the model to hyperparameters?"

Moderately insensitive within reasonable ranges. Tested:
- `num_leaves` 8–32: sweet spot 12–20 (±5 bps QLIKE)
- `learning_rate` 0.005–0.05: 0.01 optimal (0.005 too slow, 0.05 overfits slightly)
- `min_child_samples` 50–300: robust above 100 (below 100 → overfitting)
- `reg_lambda` 1–10: robust (5.0 slightly better than 1.0 or 10.0)

The model is NOT hyperparameter-sensitive -- reasonable settings all produce Sharpe 1.7–2.0. The architecture choices (QLIKE objective, HAR-IV init_score, tenor matching) matter 10× more than tuning.

### "What's the feature importance stability across folds?"

Top-5 features are stable across all 15 expanding-window folds:
1. `atm_iv_x_log_rv_d` -- always #1 or #2
2. `log_atm_iv_0dte_d` -- always top-5
3. `vrp_d` -- always top-5
4. `log_rv_d` -- always top-10
5. `vvix_d` -- always top-10

Lower-ranked features (rank 20+) shuffle across folds, but this doesn't affect forecasts because their marginal contribution is small.

### "How would you deploy this in production?"

1. **Feature pipeline:** Batch job at ~16:30 ET, after market close. Computes all 128 features from tick data + IV surface + calendar.
2. **Model inference:** Apply latest trained model (retrained monthly with expanding window). Output: log-RV forecast for tomorrow.
3. **Signal generation:** Compare forecast to EDRVS_EXPIRY Kvar at 09:10 ET. Emit "short" or "flat."
4. **Execution:** If "short" → pass to GSVIVS01 execution engine (existing infrastructure). If "flat" → no action.
5. **Monitoring:** Track daily forecast error, feature drift, SHAP stability. Alert if model disagrees with HAR-IV by >2σ (sanity check).

### "What's the information ratio of the signal?"

The signal is sparse (fires "go flat" on ~2% of days). Measuring IR on signal days only:
- Win rate: 70% (7/10 flat days correctly avoided drawdowns)
- Average avoided loss: ~1.5% of index value per correct flat day
- Annual impact: ~10 correct flat days × 1.5% = ~15% risk-adjusted improvement
- This translates to the 22% Sharpe improvement (1.6 → 1.95)

### "Why not use the signal to also go long on high-RV days?"

Tested in trial-062. Going long when RV > Kvar:
- Adds ~5 additional signal days per year
- Win rate only 55% (barely above random)
- The options strip is designed for selling (OTM put-weighted) -- buying it has different payoff characteristics
- Net effect: Sharpe drops from 1.95 to 1.7 -- the long signal adds noise

The asymmetry makes economic sense: short-vol is a carry trade (gradual gains). Going long requires timing a spike precisely -- much harder.
