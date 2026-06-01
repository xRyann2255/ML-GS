# Hybrid and Ensemble Models

## Why This Chapter Matters

> **Application: From Components to Combinations**
>
> [Chapter 11](ch11-tree-methods-vol.md) and [Chapter 12b](ch12b-deep-learning-vol.md) showed that ML models
> improve on HAR primarily through richer features and nonlinear interactions,
> not by replacing the linear structure that HAR captures well. This chapter
> asks: why not let HAR handle the linear part and train ML only on the
> residual? Hybrid models do this, and they are the safest bet in the
> volatility forecasting literature (Rahimikia and Poon, 2020). Project 1
> (HARQ-X with ML Residual Augmentation) is a hybrid by design.

You already have two powerful toolkits: the econometric models of
[Chapter 5](ch05-garch-family.md)--[Chapter 6](ch06-har-model.md) and the machine-learning models of
[Chapter 11](ch11-tree-methods-vol.md)--[Chapter 12b](ch12b-deep-learning-vol.md). Each has blind spots.
HAR is parsimonious but linear; gradient-boosted trees are flexible but
hungry for signal. This chapter shows you how to combine them so that
each component operates where it is strongest.

The core philosophy is simple: *decompose*, then *specialize*.
Let a well-understood econometric model absorb the predictable structure,
then aim the full power of ML at whatever remains. The resulting hybrid
almost always outperforms either component alone, and it does so with
lower variance and greater interpretability than a pure ML
approach (Rahimikia and Poon, 2020).


## Why Hybrids Win

### The Variance Budget Argument

Consider a forecast target $\operatorname{RV}_{t+1}$. A fitted HAR model typically
explains 40--60% of next-day realized-volatility variation with just three
coefficients (Rahimikia and Poon, 2020). That leaves 40--60% in the
residual $e_t = \operatorname{RV}_{t+1} - \widehat{\mathrm{HAR}}_t$. If you train an ML model
directly on $\operatorname{RV}_{t+1}$, it must rediscover the linear structure that HAR
already captures perfectly, wasting model capacity and inviting overfitting.
If instead you train on $e_t$, three things change for the better:

1. **HAR never overfits.** Three coefficients on lagged
   averages cannot memorize noise, so the linear component is
   rock-solid out of sample.
2. **Residual targets have lower variance.** The signal-to-noise
   ratio for the ML component improves because you have removed the
   dominant low-frequency trend.
3. **Ensemble diversification.** Even if the ML model adds only
   modest accuracy, combining two weakly correlated forecasters reduces
   overall forecast variance by the standard diversification
   identity (Rahimikia and Poon, 2020).

> **Key Idea: Let HAR Do the Heavy Lifting**
>
> If HAR explains 60% of next-day $\operatorname{RV}$ with 3 coefficients, let it.
> Train ML on the residual. You get the reliability of HAR plus the
> flexibility of ML, without asking either model to do the other's job.

### Variance Decomposition

The figure below illustrates the variance budget argument visually. The total variance of next-day RV is split into what HAR explains, what ML can capture from the residual, and irreducible noise.

```mermaid
block-beta
  columns 13
  har["HAR explains (55%)"]
  har
  har
  har
  har
  har
  har
  har["HAR explains (55%)"]
  ml["ML captures (28%)"]
  ml
  ml
  ml
  noise["Noise (17%)"]
  noise
  noise
```

**Figure:** Variance budget for next-day RV forecasting. HAR absorbs the dominant linear signal cheaply; ML targets only the residual variance, where the signal-to-noise ratio is lower but nonlinear patterns exist. Noise is irreducible regardless of model complexity.

### Architecture Diagram

The figure below illustrates the two-stage hybrid pipeline that recurs throughout this chapter. The key insight is that the ML model never sees the raw target; it only sees the residual that HAR could not explain.

```mermaid
flowchart LR
    rv["RV lags"]
    har["HAR Model"]
    harhat["$\widehat{\mathrm{HAR}}_t$"]
    resid["Compute residual\n$e_t = \operatorname{RV}_{t+1} - \widehat{\mathrm{HAR}}_t$"]
    feat["Rich features\n(Ch. 10)"]
    ml["ML Model\n(SVR / GBM / NN)"]
    plus(("$+$"))
    final["$\hat{y}_{t+1}$"]

    rv --> har
    har --> harhat
    harhat --> resid
    resid --> ml
    feat --> ml
    ml --> plus
    harhat --> plus
    plus --> final
```

**Figure:** Two-stage hybrid pipeline. HAR absorbs the linear trend; ML targets only the residual. The final forecast sums both components.


## HAR-SVR: Support Vector Regression on HAR Residuals

### Intuition

Support vector regression (SVR) is a natural first choice for the residual
stage because its $\varepsilon$-insensitive loss function automatically
ignores small residuals. If the HAR fit is already good for most days,
many residuals will be near zero. SVR treats those as "correct enough"
and focuses capacity on the days where HAR fails most, such as
post-jump or regime-change dates (Rahimikia and Poon, 2020).

> **Intuition: Why SVR Suits Residuals**
>
> SVR's $\varepsilon$-tube acts as a built-in noise filter. Days where HAR
> is close enough (residual inside the tube) contribute zero loss. SVR
> concentrates its support vectors on the hard cases, which is exactly what
> you want when most of the signal has already been removed.

### Procedure

1. Fit HAR on the training set:

   $$\widehat{\mathrm{HAR}}_t = \hat{\beta}_0
     + \hat{\beta}_d\,\operatorname{RV}_{t}
     + \hat{\beta}_w\,\operatorname{RV}_{t}^{(w)}
     + \hat{\beta}_m\,\operatorname{RV}_{t}^{(m)}.$$

2. Compute training residuals:

   $$e_t = \operatorname{RV}_{t+1} - \widehat{\mathrm{HAR}}_t.$$

   > **Intuition: In Plain English**
   >
   > Steps 1--2 are the "let HAR go first" principle in action.
   > You fit a standard HAR model, record its predictions, and then
   > subtract those predictions from the actual realized volatility.
   > The residual $e_t$ is everything HAR could not explain: jump
   > effects, leverage asymmetry, regime shifts, and noise. The ML
   > model in the next step will see only this leftover signal.

   > **Project Connection: Why This Matters**
   >
   > This two-step decomposition underpins your project's model comparison.
   > HAR and HARQ serve as econometric baselines; LightGBM then learns
   > nonlinear patterns from the full feature set (Layers 0-7). Because
   > HARQ already adapts its coefficients to measurement-error regimes,
   > comparing LightGBM's QLIKE against HARQ tells you exactly how much
   > the ML model's nonlinearity adds beyond what the noise-adaptive
   > linear baseline already captures.

3. Construct a feature matrix $\mathbf{X}_t$ from the feature engineering
   toolkit of [Chapter 10](ch10-feature-engineering.md) (jump indicators, leverage,
   signed volatility, VIX basis, microstructure noise proxies).

4. Fit SVR with radial basis function (RBF) kernel on $(e_t, \mathbf{X}_t)$:

   $$\min_{w,b}\;\frac{1}{2}\|w\|^2
     + C\sum_{t=1}^{T}\max\!\bigl(0,\,|e_t - f(\mathbf{X}_t)| - \varepsilon\bigr),$$

   where each term is:
   - $\frac{1}{2}\|w\|^2$ -- the regularization penalty that controls model complexity,
   - $C$ -- the trade-off parameter between margin width and training error,
   - $\varepsilon$ -- the tube width; residuals smaller than $\varepsilon$ in absolute value incur zero loss,
   - $f(\mathbf{X}_t) = w^\top \phi(\mathbf{X}_t) + b$ -- the SVR prediction in the kernel-induced feature space.

   > **Intuition: In Plain English**
   >
   > The SVR loss function says: "If my prediction is within
   > $\varepsilon$ of the true residual, call it good enough and move
   > on. Only penalize me for the amount I miss by beyond that
   > tolerance." The regularization term $\frac{1}{2}\|w\|^2$ keeps
   > the model simple, and $C$ controls how aggressively you chase
   > the outlier residuals versus keeping the model smooth.

   > **Project Connection: Why This Matters**
   >
   > In a HARQ-X + ML residual pipeline, most residuals will be small
   > because HARQ already captures the dominant linear dynamics. The
   > $\varepsilon$-tube ensures the SVR does not waste capacity fitting
   > noise on those easy days. Instead, it concentrates support
   > vectors on post-jump and regime-shift days where HARQ
   > underperforms, which is exactly where forecasting gains translate
   > into economic value.

5. Produce the combined forecast:

   $$\hat{y}_{t+1} = \widehat{\mathrm{HAR}}_t + \widehat{\text{SVR}}(\mathbf{X}_t).$$

   > **Intuition: In Plain English**
   >
   > The final forecast is simply the HAR prediction plus the SVR
   > correction. On days where HAR is already accurate, SVR's
   > correction is near zero (inside the $\varepsilon$-tube). On days
   > where HAR struggles, SVR adds a nonlinear adjustment. You never
   > discard the HAR forecast; you only add to it.

   > **Project Connection: Why This Matters**
   >
   > This additive structure means you can always decompose your final
   > forecast into "what HAR said" and "what ML corrected." That
   > decomposition is critical for interpretability at Goldman Sachs:
   > you can explain the linear component with HAR coefficients and
   > use SHAP values to explain the ML correction, giving the desk a
   > complete audit trail.

> **Warning: Tune $\varepsilon$ Carefully**
>
> Setting $\varepsilon$ too large makes the SVR ignore all residuals.
> Setting it too small turns SVR into standard squared-loss regression and
> removes the noise-filtering benefit. Cross-validate $\varepsilon$ on
> $\operatorname{QLIKE}$ or MSE, not on the number of support vectors.


## GARCH-Informed Neural Networks

### Motivation

The models in earlier sections use a two-stage pipeline: fit an econometric model, then correct its errors. GARCH-Informed Neural Networks (GINN) take a different approach. They hard-wire the GARCH recursion directly into the neural network architecture so that the network learns corrections to the GARCH parameters rather than learning the entire volatility dynamics from scratch (Cuchiero, Heiss, Khosrawi, and Spoida, 2024).

> **Key Idea: GINN = Residual Learning for GARCH**
>
> GINN is to GARCH what a residual network is to a feedforward net.
> Instead of asking the network to learn $\sigma^2_{t+1}$ from raw data,
> you give it the GARCH update equation as a scaffold and let the network
> learn only the deviations. This dramatically reduces the function space
> the network must search.

### Architecture

The standard GARCH(1,1) update is

$$\sigma^2_{t+1} = \omega + \alpha\,\epsilon_t^2 + \beta\,\sigma^2_t.$$

> **Intuition: In Plain English**
>
> Tomorrow's variance equals a long-run average ($\omega$) plus a fraction
> of today's squared shock ($\alpha\,\epsilon_t^2$) plus a fraction of
> today's variance ($\beta\,\sigma^2_t$). The parameters $\alpha$ and
> $\beta$ are fixed for all time, which means the model treats calm
> markets and crisis markets with the same update rule.

GINN replaces the fixed parameters $(\omega, \alpha, \beta)$ with
time-varying outputs of a neural network $g_{\boldsymbol{\theta}}$:

$$\sigma^2_{t+1} = \omega_t + \alpha_t\,\epsilon_t^2
  + \beta_t\,\sigma^2_t,
  \qquad
  (\omega_t, \alpha_t, \beta_t) = g_{\boldsymbol{\theta}}(\mathbf{X}_t),$$

where each term is:
- $g_{\boldsymbol{\theta}}(\mathbf{X}_t)$ -- a small feedforward network (typically 2 hidden layers, 32--64 units each) that maps auxiliary features $\mathbf{X}_t$ to time-varying GARCH parameters,
- $\omega_t, \alpha_t, \beta_t$ -- the GARCH coefficients at time $t$, constrained to satisfy $\omega_t > 0$, $\alpha_t \geq 0$, $\beta_t \geq 0$, and $\alpha_t + \beta_t < 1$ via softmax and sigmoid output activations (Cuchiero, Heiss, Khosrawi, and Spoida, 2024),
- $\epsilon_t^2$ -- the squared innovation (return shock),
- $\sigma^2_t$ -- the previous conditional variance, fed back recurrently.

> **Intuition: In Plain English**
>
> GINN keeps the GARCH update rule but lets a neural network adjust the
> knobs ($\omega$, $\alpha$, $\beta$) at each time step based on auxiliary
> features. During calm markets the network can set $\beta$ high (strong
> persistence); after a jump it can raise $\alpha$ (more reactive to
> shocks). The GARCH skeleton is never discarded, so the model
> automatically inherits volatility clustering and mean reversion.

> **Project Connection: Why This Matters**
>
> GINN's time-varying parameters are conceptually parallel to HARQ's
> measurement-error-weighted coefficients. Both models ask: "What if
> the parameters themselves depend on the current regime?" If you
> extend HARQ with a neural network that modulates $\beta_d$, $\beta_w$,
> $\beta_m$ based on jump intensity or microstructure noise, you are
> building a HAR analogue of GINN, and the GINN literature provides the
> architectural blueprint.

```mermaid
flowchart LR
    feat["Features $\mathbf{X}_t$"]
    nn["Neural net $g_{\boldsymbol{\theta}}$\n(2 layers, 32 units)"]
    params["$(\omega_t, \alpha_t, \beta_t)$\ntime-varying"]
    shocks["$\epsilon_t^2,\;\sigma^2_t$"]
    garch["GARCH recursion\n$\sigma^2_{t+1} = \omega_t + \alpha_t\epsilon_t^2 + \beta_t\sigma^2_t$"]
    out["$\sigma^2_{t+1}$"]

    feat --> nn
    nn --> params
    params --> garch
    shocks --> garch
    garch --> out
    out -. "recurrence" .-> shocks
```

**Figure:** GINN architecture. A neural network produces time-varying GARCH parameters; the GARCH recursion itself is hard-wired, not learned.

### Why This Works

The key advantage is that GINN preserves the inductive bias of GARCH:
volatility clusters, shocks decay exponentially, and the unconditional
variance is finite. The neural network modulates these dynamics based on
auxiliary information (sentiment, jump indicators, cross-asset signals)
without having to discover the clustering structure itself.
Cuchiero, Heiss, Khosrawi, and Spoida (2024) show that GINN matches or outperforms both standard
GARCH and unconstrained LSTMs on equity index volatility, with
substantially fewer parameters than the LSTM.


## NLP-Augmented Volatility Models

### Motivation

News moves volatility, and the effect is asymmetric: negative news
amplifies $\operatorname{RV}$ far more than positive news calms it.
Rahimikia, Zohren, and Poon (2021) ask whether a machine-readable
news signal can improve HAR forecasts. The answer is yes, but modestly
and conditionally.

### The Rahimikia-Zohren-Poon Pipeline

The procedure has three stages:

1. **Text embedding.** Collect financial news headlines
   (e.g., from Dow Jones Newswires) for each trading day. Train
   a Word2Vec skip-gram model on a financial corpus to obtain
   300-dimensional word vectors (*FinText*). Arrange each
   day's tokens into a $500 \times 300$ sentence matrix (padding
   shorter sequences), then feed it through a convolutional neural
   network (CNN) with multiple filter sizes that learns to map
   the text directly to a volatility
   forecast (Rahimikia, Zohren, and Poon, 2021).

2. **Augmented HAR (simplified view).** The simplest way to
   incorporate a text signal is to append a summary sentiment score
   $s_t$ to the standard HAR regression:

   $$\operatorname{RV}_{t+1} = \beta_0 + \beta_d\,\operatorname{RV}_t
     + \beta_w\,\operatorname{RV}_t^{(w)} + \beta_m\,\operatorname{RV}_t^{(m)}
     + \gamma\,s_t + \varepsilon_{t+1},$$

   where:
   - $s_t$ -- the daily text-derived signal (negative values indicate bearish tone),
   - $\gamma$ -- the text loading; if news carries incremental information beyond lagged $\operatorname{RV}$, then $\gamma \neq 0$.

   In practice, Rahimikia, Zohren, and Poon (2021) go further:
   their NLP-ML model feeds the $500 \times 300$ sentence matrix
   directly into the CNN, bypassing the sentiment-score bottleneck.
   The linear augmented-HAR equation above is a useful pedagogical
   simplification that captures the same core idea: text provides
   an exogenous signal beyond lagged $\operatorname{RV}$.

   > **Intuition: In Plain English**
   >
   > The key insight is that news text can carry information about
   > tomorrow's volatility that lagged RV alone does not capture.
   > Whether you inject that signal as a single sentiment score in
   > a linear regression or let a CNN learn a richer representation,
   > the principle is the same: combine text with the HAR baseline.

   > **Project Connection: Why This Matters**
   >
   > At Goldman Sachs you may have access to proprietary news feeds
   > or internal research sentiment. Public NLP signals show modest
   > and conditional improvements, primarily on volatility jump
   > days, but a curated internal signal could do better. More
   > importantly, this equation shows the general template for
   > augmenting HAR with any exogenous feature: just add it as an
   > extra regressor and test whether $\gamma \neq 0$.

3. **Evaluation.** Compare $\operatorname{QLIKE}$ loss of HAR vs.
   HAR+NLP across the full sample and conditional on high-volatility
   periods.

### What the Literature Finds

Rahimikia, Zohren, and Poon (2021) find that NLP-ML models
strongly outperform HAR-family models on *volatility jump days*
(roughly the top 10% of RV observations) but underperform on normal
volatility days. During calm markets, the text signal adds
negligible information because lagged $\operatorname{RV}$ already captures the
low-volatility regime; the gains are concentrated in high-volatility
episodes where news carries incremental content.

> **Warning: NLP Gains Are Small and Fragile**
>
> A 1--3% $\operatorname{QLIKE}$ improvement is economically meaningful only if you
> trade on volatility forecasts at scale. The improvement is
> sample-dependent, sensitive to the choice of news source, and does not
> survive aggressive transaction costs in short-horizon
> strategies (Rahimikia, Zohren, and Poon, 2021). Do not overfit to the
> headline number.

Rahimikia and Poon (2020) provide additional evidence that hybrid models
combining econometric baselines with text-derived features outperform
pure text-based approaches, reinforcing the "let the baseline work
first" principle of this chapter.


## Ensemble: HAR + LightGBM

### The Safest Performer

If you must choose one approach from this chapter for a production
volatility forecast, choose a weighted average of HAR and LightGBM.
It is simple, robust, and remarkably hard to beat. Two combination
strategies dominate practice.

#### Strategy A: Fixed Weighted Average

Choose a fixed weight $w \in [0,1]$ and combine:

$$\hat{y}_{t+1} = w\,\widehat{\mathrm{HAR}}_t + (1-w)\,\widehat{\text{GBM}}_t,$$

where:
- $w$ -- the HAR weight, typically calibrated on a validation set or set to $w = 0.7$ as a robust default,
- $\widehat{\mathrm{HAR}}_t$ -- the HAR forecast from the HAR fit equation above,
- $\widehat{\text{GBM}}_t$ -- the LightGBM forecast trained on the full feature set of [Chapter 10](ch10-feature-engineering.md).

> **Intuition: In Plain English**
>
> The combined forecast is a simple weighted average of two models. With
> $w = 0.7$, you are saying "I trust HAR for 70% of the forecast and
> let LightGBM contribute the remaining 30%." This is the forecast
> analogue of portfolio diversification: even if LightGBM is noisier than
> HAR, blending the two reduces overall forecast variance as long as their
> errors are not perfectly correlated.

> **Project Connection: Why This Matters**
>
> A fixed 70/30 blend is the simplest credible baseline for the internship
> project. Before investing time in stacking or neural residual models,
> demonstrate that this blend already beats standalone HAR on QLIKE.
> The weight $w$ can be optimized by minimizing QLIKE on a validation set,
> which directly aligns the combination with the project's primary
> evaluation metric.

> **Key Idea: The 70/30 Rule**
>
> A 70/30 HAR/LightGBM blend is remarkably hard to beat. It inherits HAR's
> stability in calm markets and LightGBM's ability to capture nonlinear
> effects during crises. You can optimize $w$ on validation data, but the
> gain over a fixed 70/30 split is usually small.

#### Strategy B: Stacking with Ridge Meta-Learner

Instead of fixing $w$, learn the combination weights via ridge regression
on out-of-sample predictions:

1. Generate OOS predictions from HAR and LightGBM using
   time-series cross-validation (expanding or rolling window).

2. Stack these predictions as features and fit a ridge regression:

   $$\hat{y}_{t+1} = \alpha_0 + \alpha_1\,\widehat{\mathrm{HAR}}_t^{\text{OOS}}
     + \alpha_2\,\widehat{\text{GBM}}_t^{\text{OOS}},$$

   where:
   - $\widehat{\mathrm{HAR}}_t^{\text{OOS}}$ and $\widehat{\text{GBM}}_t^{\text{OOS}}$ are out-of-sample predictions from the base models,
   - $\alpha_0, \alpha_1, \alpha_2$ are learned by ridge regression with penalty $\lambda$ chosen by cross-validation,
   - the ridge penalty prevents the meta-learner from overfitting to the small differences between base models.

   > **Intuition: In Plain English**
   >
   > Instead of fixing the blend weights by hand, you let the data
   > decide. You generate out-of-sample predictions from each base
   > model (so the meta-learner never sees in-sample fits), then run
   > a simple ridge regression that learns how much to trust each
   > model. The intercept $\alpha_0$ corrects any systematic bias,
   > and the ridge penalty prevents the meta-learner from overfitting
   > to noise in the small differences between HAR and LightGBM.

   > **Project Connection: Why This Matters**
   >
   > Stacking is the natural upgrade path from a fixed 70/30 blend.
   > If your project has multiple candidate models (HARQ, HARQ-X,
   > LightGBM, SVR), stacking lets you combine all of them in a
   > principled way. Critically, the meta-learner can be trained by
   > minimizing QLIKE rather than MSE, ensuring the combination
   > weights are aligned with the project's primary loss function.

### Architecture Diagram

```mermaid
flowchart LR
    data["Training data\n$(\mathbf{X}_t, \operatorname{RV}_{t+1})$"]
    har["HAR"]
    gbm["LightGBM"]
    haroos["$\widehat{\mathrm{HAR}}_t^{\text{OOS}}$"]
    gbmoos["$\widehat{\text{GBM}}_t^{\text{OOS}}$"]
    meta["Ridge\nmeta-learner"]
    out["$\hat{y}_{t+1}$"]

    data --> har
    data --> gbm
    har --> haroos
    gbm --> gbmoos
    haroos --> meta
    gbmoos --> meta
    meta --> out
```

**Figure:** Stacking architecture. Base models produce OOS predictions; a ridge meta-learner learns the optimal combination.


## Comparing Ensemble Architectures

So far this chapter has presented two combination strategies for HAR and
LightGBM: a fixed weighted average and a ridge meta-learner on OOS
predictions. Both are instances of a broader design choice: how do you
wire multiple models together? Three architectures dominate the ensemble
literature, and each answers that question differently. Understanding
their tradeoffs is essential before committing to one for a production
volatility pipeline.


### Architecture A: Feature Stacking

**Feature stacking** concatenates the internal representation of one
model with the input features of another, training a single downstream
model on the combined feature set. In the volatility context, this
typically means training an LSTM on intraday sequences (e.g., 5-minute
E-mini bars) to produce a $k$-dimensional **embedding vector**,
then appending that embedding to the tabular feature matrix before
training LightGBM.

The combined feature vector fed to LightGBM becomes:

$$\tilde{\mathbf{X}}_t = \bigl[\,\mathbf{X}_t^{\text{tab}} \;\|\;
  \mathbf{h}_t^{\text{LSTM}}\,\bigr],$$

where each term is:
- $\mathbf{X}_t^{\text{tab}}$ -- the tabular feature matrix (RV lags, jump indicators, leverage, microstructure proxies, cross-asset signals) from [Chapter 10](ch10-feature-engineering.md),
- $\mathbf{h}_t^{\text{LSTM}}$ -- the $k$-dimensional embedding vector extracted from the LSTM's final hidden state after processing the intraday sequence,
- $\|$ -- concatenation along the feature axis.

> **Intuition: In Plain English**
>
> Think of the LSTM as a feature extractor: it reads a day's worth of
> 5-minute bars and compresses them into a short summary vector.
> LightGBM then treats that summary as additional columns alongside the
> usual tabular features. The hope is that the LSTM captures intraday
> dynamics (order flow imbalances, microstructure noise patterns) that
> tabular statistics miss, and the tree can exploit those dynamics
> alongside everything else.

#### The Gradient Isolation Problem

Feature stacking has a fundamental flaw: **gradient isolation**.
LightGBM is a tree-based model, so it cannot compute gradients with
respect to its inputs. This means the LSTM embedding
$\mathbf{h}_t^{\text{LSTM}}$ is never optimized for the tree's $\operatorname{QLIKE}$
objective. The LSTM learns representations that minimize its own loss
function (typically MSE on log-RV), and the tree uses that
representation as-is, whether or not it is what the tree needs.

Contrast this with an end-to-end neural architecture where you could
backpropagate from the final loss through both components. In feature
stacking, the two models live in separate optimization worlds:

1. The LSTM is trained to minimize $\mathcal{L}_{\text{LSTM}}$ on intraday sequences.
2. The embedding $\mathbf{h}_t$ is frozen and appended to $\mathbf{X}_t$.
3. LightGBM is trained to minimize $\mathcal{L}_{\text{GBM}}$ on $\tilde{\mathbf{X}}_t$, treating $\mathbf{h}_t$ as fixed columns.

If the embedding encodes information in a format that tree splits
cannot exploit efficiently (e.g., information spread across multiple
embedding dimensions in a way that requires linear combinations),
LightGBM will underuse it. Worse, you cannot tell from the final
forecast error whether a bad prediction came from a bad embedding or
bad tree splits.

> **Warning: Gradient Isolation Breaks Joint Optimization**
>
> Because LightGBM cannot backpropagate into the LSTM, the embedding is
> optimized for the wrong objective. The LSTM minimizes its own loss;
> the tree minimizes a different loss on fixed embeddings. There is no
> mechanism to align the two. This is not a theoretical concern: it
> means the LSTM may learn to encode information that is useful for its
> own predictions but redundant or inaccessible to the tree.


### Architecture B: Residual Stacking (Three-Stage Pipeline)

The HAR-SVR section introduced the two-stage residual
hybrid: HAR first, then SVR on the residuals. **Residual
stacking** generalizes this to three or more stages, where each model
trains on the residuals left by all prior stages. The canonical
three-stage pipeline for volatility forecasting is:

1. **Stage 1 -- HAR (linear baseline).** Fit HAR on the
   training set exactly as in the HAR fit equation above. HAR captures the dominant
   multi-scale autoregressive structure of realized volatility.
   Compute residuals: $e_t^{(1)} = \operatorname{RV}_{t+1} -
   \widehat{\mathrm{HAR}}_t$.

2. **Stage 2 -- LightGBM (nonlinear interactions).** Train
   LightGBM on Stage 1 residuals $e_t^{(1)}$ using the full
   tabular feature set. The tree captures nonlinear patterns that
   HAR misses: regime interactions, jump-asymmetry effects,
   cross-asset spillovers. Compute residuals:
   $e_t^{(2)} = e_t^{(1)} - \widehat{\text{GBM}}(e_t^{(1)},
   \mathbf{X}_t)$.

3. **Stage 3 -- LSTM (sequential dynamics).** Train an
   LSTM on Stage 2 residuals $e_t^{(2)}$ using intraday sequences.
   If any temporal structure remains after the tree has operated,
   the recurrent network can capture it. This stage is optional:
   if Stage 2 residuals are indistinguishable from white noise, the
   LSTM adds nothing and should be dropped.

The final forecast sums all stage contributions:

$$\hat{y}_{t+1} = \widehat{\mathrm{HAR}}_t
  + \widehat{\text{GBM}}(\mathbf{X}_t)
  + \widehat{\text{LSTM}}(\mathbf{X}_t^{\text{seq}}),$$

where each term is:
- $\widehat{\mathrm{HAR}}_t$ -- the HAR baseline forecast (from the HAR fit equation above),
- $\widehat{\text{GBM}}(\mathbf{X}_t)$ -- the LightGBM correction trained on HAR residuals with tabular features,
- $\widehat{\text{LSTM}}(\mathbf{X}_t^{\text{seq}})$ -- the LSTM correction trained on Stage 2 residuals with intraday sequences (set to zero if Stage 3 is dropped).

> **Intuition: In Plain English**
>
> Residual stacking is like a relay race. HAR runs the first leg and
> explains everything it can with three coefficients. LightGBM picks up
> what HAR dropped, the nonlinear, interaction-driven patterns in the
> leftover signal. If there is still structure remaining (temporal
> dependencies in the second-stage residuals), an LSTM runs the final
> leg. Each runner is specialized by construction: you never ask a model
> to redo work that a prior stage already handled. This is the
> three-stage extension of the HAR-SVR pipeline from the HAR-SVR section,
> replacing SVR with LightGBM and adding an optional LSTM stage.

> **Project Connection: Residual Stacking Is Your Default Architecture**
>
> This three-stage pipeline maps directly onto the HARQ-X + ML residual
> direction. HARQ-X replaces plain HAR in Stage 1, giving even cleaner
> residuals because measurement-error adaptation removes a source of
> variation before the tree ever sees the data. Stage 2 (LightGBM on
> residuals) is where most of the incremental $\operatorname{QLIKE}$ improvement will
> come from. Stage 3 (LSTM on intraday sequences) is the optional
> upgrade path: add it only if you have evidence that Stage 2 residuals
> contain exploitable temporal structure.

Why does residual stacking avoid the gradient isolation problem?
Because each model trains directly on a well-defined target (the
residuals from the prior stage), using a loss function that is directly
aligned with that target. There are no frozen embeddings, no
cross-model feature coupling. If Stage 2 performs poorly, you know it
is because LightGBM cannot explain the HAR residuals, not because some
upstream embedding was misaligned.


### Architecture C: Prediction Blending

**Prediction blending** is the simplest ensemble architecture:
train each model independently, then combine their final predictions
with a weighted average. This is what the HAR + LightGBM ensemble section already covers with the fixed 70/30
blend and the ridge meta-learner. The key distinction from the other
architectures is that models never share information during training.
Each model sees the original target $\operatorname{RV}_{t+1}$ (not a residual) and
the features best suited to its architecture.

The general blending formula for $K$ models is:

$$\hat{y}_{t+1} = \sum_{k=1}^{K} w_k\,\hat{y}_{t+1}^{(k)},
  \qquad \sum_{k=1}^{K} w_k = 1,$$

where each term is:
- $\hat{y}_{t+1}^{(k)}$ -- the independent forecast from model $k$,
- $w_k$ -- the blend weight for model $k$, constrained to sum to one (though a ridge meta-learner as in the stacking equation above relaxes this constraint).

> **Intuition: In Plain English**
>
> Prediction blending is forecast-level diversification. Each model
> makes its best guess independently, and you take a weighted average.
> No model sees what the others are doing during training. This is the
> ensemble equivalent of portfolio diversification: even if individual
> forecasters are noisy, their weighted average has lower variance as
> long as errors are imperfectly correlated.

#### Weight Schemes

Two approaches to setting blend weights:

**Static weights.**
Choose weights once on a validation set and hold them fixed. The
simplest principled choice is **inverse-$\operatorname{QLIKE}$ weighting**:

$$w_k = \frac{\operatorname{QLIKE}_k^{-1}}{\sum_{j=1}^{K}\operatorname{QLIKE}_j^{-1}},$$

where each term is:
- $\operatorname{QLIKE}_k$ -- the $\operatorname{QLIKE}$ loss of model $k$ on the validation set,
- $\operatorname{QLIKE}_k^{-1}$ -- the inverse loss; models with lower (better) $\operatorname{QLIKE}$ receive higher weight.

> **Intuition: In Plain English**
>
> Inverse-$\operatorname{QLIKE}$ weighting says: "Trust each model in proportion to
> how well it performed on validation data." A model with half the
> $\operatorname{QLIKE}$ loss of another gets twice the weight. This is a one-line
> formula that requires no optimization and aligns directly with the
> project's primary evaluation metric.

**Regime-dependent weights.**
Use different blend weights in different volatility regimes. For
example, give more weight to LightGBM during high-volatility periods
(where nonlinear effects dominate) and more weight to HAR during calm
periods (where the linear structure is sufficient). The section on static vs. regime-dependent weights below discusses when this helps and when it does not.

#### Competition Evidence

Top-performing solutions in the Optiver Realized Volatility
competition (Optiver, 2021) consistently chose prediction blending
over feature stacking. Winners trained LightGBM and neural network
branches independently, then combined outputs with simple weighted
averages. The rationale: prediction blending is easier to debug
(each branch can be evaluated in isolation), easier to iterate on
(swap one branch without retraining others), and provides a natural
fallback strategy (if one branch degrades, drop it and reweight).

> **Key Idea: Prediction Blending: Simplest and Often Best**
>
> Prediction blending requires no cross-model coupling, no shared
> training, and no sequential dependencies. Each model can be
> developed, validated, and debugged in isolation. Despite its
> simplicity, competition evidence from Optiver (2021)
> shows it matches or outperforms more complex architectures. It should
> be the default ensemble strategy unless you have specific evidence that
> residual stacking improves $\operatorname{QLIKE}$.


### Architecture Comparison

The table below summarizes the tradeoffs across the three architectures on five dimensions that matter for a production volatility pipeline.

**Table: Three-way ensemble architecture comparison for volatility forecasting.**

| Dimension | Feature Stacking | Residual Stacking | Prediction Blending |
|---|---|---|---|
| Complexity | High (joint training, embedding pipeline) | Moderate (sequential stages) | Low (independent models) |
| Gradient flow | Broken (tree cannot backprop into LSTM) | Clean (each stage has its own target) | N/A (no cross-model coupling) |
| Interpretability | Opaque (embedding dimensions lack semantics) | Clear (each stage's contribution is additive and measurable) | Clear (individual model forecasts are directly comparable) |
| Fallback strategy | Must retrain tree without embedding | Drop later stages; keep HAR + LightGBM | Drop one model; reweight the rest |
| Literature support | Weak (no RV paper demonstrates gains) | Strong (HARQ-X residual literature) | Strong (Optiver, 2021); Kaggle competition evidence |

> **Intuition: Reading the Comparison Table**
>
> The table reveals a clear pattern: moving from left to right (feature
> stacking to residual stacking to prediction blending), complexity
> decreases, debuggability increases, and literature support strengthens.
> Feature stacking sounds appealing in theory, richer input to the
> tree, but gradient isolation undermines the premise. Residual
> stacking gives each model a distinct role by construction. Prediction
> blending is the simplest and most robust, requiring no architectural
> coupling between models at all.


## Identifying Regimes: GMM, EM, and BIC

The regime-dependent weighting scheme of the next subsection, and the
regime-switching combination of [Chapter 11](ch11-tree-methods-vol.md)
(the regime-switching combination equation), both rely on a single ingredient
we have so far left undefined: a *regime indicator*. Until now we
have used ad-hoc thresholds, $\operatorname{RV}_t^{(w)}$ above its 75th percentile,
or $\operatorname{IV}_t > 30$ for the VIX, to declare a market "stressed." Those
rules are easy to state and easy to defend, but they raise an obvious
question: *why $75$th and not $80$th?* This section replaces the
hand-picked threshold with a probabilistic model that lets the data decide
both how many regimes exist and which one each day belongs to, the
"GMM-based regime probability" that [Chapter 11](ch11-tree-methods-vol.md) promised when
it defined the stress indicator $s_t$.

> **Prereq: Multivariate Gaussian and Mixture Models**
>
> A $d$-dimensional Gaussian density is
> $$\mathcal{N}(\mathbf{x} \mid \bm{\mu}, \bm{\Sigma})
>   = \frac{1}{(2\pi)^{d/2} |\bm{\Sigma}|^{1/2}}
>     \exp\!\Bigl(-\tfrac{1}{2}(\mathbf{x} - \bm{\mu})^\top \bm{\Sigma}^{-1}
>     (\mathbf{x} - \bm{\mu})\Bigr),$$
> where $\bm{\mu} \in \mathbb{R}^d$ is the mean and
> $\bm{\Sigma} \in \mathbb{R}^{d \times d}$ is the covariance matrix (symmetric
> positive-definite, a square table recording each feature's spread on
> its diagonal and how every pair of features co-moves off it). A
> **mixture model** says the data come from several such Gaussians,
> each chosen with some probability. If this is unfamiliar, review
> Bishop (2006), Ch. 2 and 9.
>
> *You do not need to understand every symbol above.* The key idea is
> *distance from the center*: this is the ordinary bell curve
> generalized to $d$ features at once. The $\exp(\cdots)$ term is large when
> $\mathbf{x}$ sits close to the center $\bm{\mu}$ and shrinks as $\mathbf{x}$ moves away;
> the quadratic $(\mathbf{x}-\bm{\mu})^\top \bm{\Sigma}^{-1}(\mathbf{x}-\bm{\mu})$ measures
> that distance while accounting for how the features spread and co-move. The
> fraction in front is just a normalizing constant that makes the total
> probability sum to one, you never compute it by hand. Notationally,
> $|\bm{\Sigma}|$ is the **determinant** (a single number summarizing
> the overall spread), the superscript $^\top$ is the **transpose**
> (turn a column into a row so the multiplication works), and
> $\bm{\Sigma}^{-1}$ is the **matrix inverse**.

### The GMM Density Model for Soft Regime Clustering

The idea is to treat each trading day as a point in a low-dimensional
space of volatility descriptors and ask: *which cluster of historical
days does today most resemble?* A **Gaussian Mixture Model (GMM)**
formalizes "cluster" as a Gaussian blob and "which one" as a
probability. We first state what the model is, then how to fit it.

> **Definition: Gaussian Mixture Model**
>
> A $K$-component Gaussian Mixture Model models the density of observations
> $\mathbf{x} \in \mathbb{R}^d$ as
> $$p(\mathbf{x}) = \sum_{k=1}^{K}
>     \underbrace{\pi_k}_{\text{how common regime }k\text{ is}}\;
>     \underbrace{\mathcal{N}(\mathbf{x} \mid \bm{\mu}_k, \bm{\Sigma}_k)}_{\text{regime-}k\text{ shape}},$$
> where each term is:
> - $K$ -- the number of mixture components, interpreted here as the number of **volatility regimes**,
> - $\pi_k \geq 0$ -- the **mixing weight** (prior probability) of regime $k$, with $\sum_{k=1}^K \pi_k = 1$; the long-run fraction of days spent in regime $k$,
> - $\bm{\mu}_k \in \mathbb{R}^d$ -- the **mean** feature vector of regime $k$ (e.g., the typical $(\operatorname{RV}, \text{jump}, \operatorname{IV})$ profile of a crisis),
> - $\bm{\Sigma}_k \in \mathbb{R}^{d \times d}$ -- the **covariance** of regime $k$, describing how tightly days cluster around $\bm{\mu}_k$ and how the features co-move within the regime.
>
> > **Intuition: In Plain English**
> >
> > The GMM density equation says: "Pretend volatility days are drawn
> > from $K$ different bell-shaped clouds. Each cloud has its own center
> > (typical RV, jump size, VIX) and its own spread. A calm cloud sits at low
> > RV and low VIX; a crisis cloud sits at high RV, large jumps, and a
> > blown-out VIX." Rather than slicing the data with a single hard line at
> > the 75th percentile, the GMM draws soft, possibly overlapping blobs and
> > lets a day belong partly to several of them.
>
> > **Project Connection: Why This Matters**
> >
> > The regime descriptors we feed the GMM are precisely the quantities this
> > guide has spent chapters building: the HAR components $\operatorname{RV}_t$,
> > $\operatorname{RV}_t^{(w)}$, $\operatorname{RV}_t^{(m)}$ ([Chapter 6](ch06-har-model.md)), the signed jump
> > variation that separates good from bad volatility
> > ([Chapter 4](ch04-jumps-continuous-variation.md)), and the option-implied $\operatorname{IV}_t$ with its
> > variance risk premium $\operatorname{VRP}_t$ ([Chapter 9](ch09-variance-risk-premium.md)). A fitted GMM turns
> > these into a soft regime label per day, which becomes the
> > stress-indicator $s_t$ that drives the regime-dependent blend weights in
> > the section on static vs. regime-dependent weights below, replacing the arbitrary
> > "$\operatorname{RV}^{(w)} > 75$th percentile" rule with a data-driven one.

**What goes into $\mathbf{x}_t$.**
The regime model takes *volatility-state descriptors*, not your full
prediction feature set. A compact, defensible choice for daily
RV forecasting is

$$\mathbf{x}_t = \bigl(\,\operatorname{RV}_t,\;\operatorname{RV}_t^{(w)},\;\operatorname{RV}_t^{(m)},\;
    J_t^{+},\;J_t^{-},\;\operatorname{IV}_t,\;\operatorname{VRP}_t\,\bigr)^\top,$$

where each term is:
- $\operatorname{RV}_t,\,\operatorname{RV}_t^{(w)},\,\operatorname{RV}_t^{(m)}$ -- the daily, weekly, and monthly HAR components, capturing the level and slope of the volatility term structure,
- $J_t^{+},\,J_t^{-}$ -- the signed (positive and negative) jump variation, separating "good" upside jumps from "bad" downside jumps ([Chapter 4](ch04-jumps-continuous-variation.md)),
- $\operatorname{IV}_t$ -- the option-implied volatility (VIX), a forward-looking risk gauge,
- $\operatorname{VRP}_t = \operatorname{IV}_t^2 - \mathbb{E}_t[\operatorname{RV}_{t+1}]$ -- the variance risk premium. Here $\mathbb{E}_t[\operatorname{RV}_{t+1}]$ is the market's *expected* next-day realized variance given everything known by day $t$ (the subscript $t$ means "conditional on information up to today"; in practice this is a forecast such as the HAR prediction itself). The VRP is then how much more the option market is charging ($\operatorname{IV}_t^2$) than that expected realized amount, large when investors are paying up for crash protection ([Chapter 9](ch09-variance-risk-premium.md), which uses the full multi-day horizon).

> **Warning: Standardize Before You Fit**
>
> $\operatorname{RV}$ lives near $10^{-4}$ in variance units while the VIX lives near
> $20$. Left raw, the GMM's distances would be dominated entirely by the
> VIX and would ignore $\operatorname{RV}$ altogether. (**Euclidean distance** just
> means straight-line distance in feature space; a feature measured in
> $20$s swamps one measured in $0.0001$s, so the model would only ever
> "see" the VIX.) Apply the z-score leg of the **Triple Expansion**
> from [Chapter 10](ch10-feature-engineering.md) (the Triple Expansion section) to every
> input. **Z-scoring** means subtract each feature's mean and divide
> by its standard deviation, so it is recentred to a mean of $0$ and
> rescaled to a typical size of $1$, putting every feature on the same
> footing. Use only a trailing window to compute the standardization
> moments, so the regime label for day $t$ uses no future information.

### The EM Algorithm: Soft Labels, Then Updated Blobs

How do we find the $\pi_k$, $\bm{\mu}_k$, $\bm{\Sigma}_k$ that best explain
the data? By **maximum likelihood**, pick the parameters that make
the data we actually observed as probable as possible. The log-likelihood
of the parameters
$\bm{\theta} = \{\pi_k, \bm{\mu}_k, \bm{\Sigma}_k\}_{k=1}^K$ is

$$\ell(\bm{\theta}) = \sum_{t=1}^{T} \log
    \underbrace{\sum_{k=1}^{K} \pi_k\,\mathcal{N}(\mathbf{x}_t \mid \bm{\mu}_k, \bm{\Sigma}_k)}_{\text{mixture density at day } t},$$

where each term is:
- $T$ -- the number of trading days in the fitting window,
- the inner sum -- the GMM density (from the GMM density equation above) evaluated at day $t$'s descriptor $\mathbf{x}_t$,
- the outer $\log$-sum -- the total log-probability the model assigns to the observed history.

> **Intuition: In Plain English**
>
> The log-likelihood equation scores a candidate set of regime
> blobs by asking "how likely is the actual volatility history under these
> blobs?" We want the blobs that make the data look most ordinary. The
> trouble is the $\log$ wraps a *sum* over regimes, so there is no
> *closed form*, a direct formula you could just plug numbers into.
> Taking the log of a single bell curve simplifies nicely (the $\exp$
> cancels), but taking the log of a *sum* of bell curves does not
> simplify, so we have to iterate instead: knowing the best blobs requires
> knowing which regime each day belongs to, and knowing each day's regime
> requires the blobs. This chicken-and-egg structure is exactly what the EM
> algorithm untangles.

The **Expectation-Maximization (EM)** algorithm
(Dempster, Laird, and Rubin, 1977) breaks the deadlock by alternating two
steps until the log-likelihood stops increasing.

> **Key Idea: EM for Gaussian Mixtures**
>
> **E-step (soft labels).** Given the current blobs, compute the
> **responsibility** of regime $k$ for day $t$:
> $$\gamma_{tk} = \frac{\pi_k\,\mathcal{N}(\mathbf{x}_t \mid \bm{\mu}_k, \bm{\Sigma}_k)}
>     {\sum_{j=1}^{K} \pi_j\,\mathcal{N}(\mathbf{x}_t \mid \bm{\mu}_j, \bm{\Sigma}_j)},$$
> where $\gamma_{tk}$ is how strongly regime $k$ claims day $t$,
> literally regime $k$'s share of the total density at that day, a number
> between $0$ and $1$ (top divided by the sum of all the tops). In words:
> what fraction of today belongs to the calm cloud, the crisis cloud, the
> elevated cloud. Statisticians write this as the *posterior
> probability* $\Pr(\text{regime}=k \mid \mathbf{x}_t)$, read "the probability the
> regime is $k$, given that we observed today's descriptor $\mathbf{x}_t$" (the
> vertical bar means "given").
>
> **M-step (update blobs).** Treating the responsibilities as soft
> counts, re-estimate each regime:
> $$N_k = \sum_{t=1}^{T} \gamma_{tk},$$
> $$\bm{\mu}_k^{\text{new}} = \frac{1}{N_k}
>     \sum_{t=1}^{T} \gamma_{tk}\,\mathbf{x}_t,$$
> $$\bm{\Sigma}_k^{\text{new}} = \frac{1}{N_k}
>     \sum_{t=1}^{T} \gamma_{tk}\,(\mathbf{x}_t - \bm{\mu}_k^{\text{new}})
>     (\mathbf{x}_t - \bm{\mu}_k^{\text{new}})^\top,$$
> $$\pi_k^{\text{new}} = \frac{N_k}{T},$$
> where $N_k$ is the **effective number of days** assigned to regime
> $k$. The mean update is just a weighted average
> of the days (each day weighted by how much it claims to belong). The
> covariance update is the weighted average
> *squared spread* of the days around the new center, it measures how
> wide and what shape each cloud is. The outer product
> $(\mathbf{x}_t - \bm{\mu}_k^{\text{new}})(\mathbf{x}_t - \bm{\mu}_k^{\text{new}})^\top$ is
> the multi-feature version of squaring a deviation: the second factor is
> written as a row (that is the $^\top$ transpose), so a column times a row
> produces a $d\times d$ *matrix*, not a single number, capturing both
> how much each feature varies and how the features move together.
> Iterate the E-step and M-step updates until
> $|\ell^{(i+1)} - \ell^{(i)}| < \tau_{\text{EM}}$, where $\ell^{(i)}$ is the
> log-likelihood after iteration $i$ (the parenthesized superscript is an
> iteration counter, not a power) and $\tau_{\text{EM}}$ is a small stopping
> threshold (e.g. $10^{-6}$), stop when the log-likelihood barely changes.
> EM guarantees $\ell(\bm{\theta})$ never decreases
> (Dempster, Laird, and Rubin, 1977).

> **Intuition: In Plain English**
>
> EM is soft $k$-means. The E-step asks each day "what fraction of you
> belongs to the calm cloud, the crisis cloud, the elevated cloud?" and
> records those fractions. The M-step then redraws each cloud's center and
> spread using every day, but weighting each day by how much it claims to
> belong. A day that is 90% crisis pulls the crisis center hard and the
> calm center barely at all. Repeat, and the clouds drift until they settle
> on the natural groupings in the volatility data, no hand-labelling
> required.

> **Project Connection: Why This Matters**
>
> The responsibilities $\gamma_{tk}$ are the soft regime probabilities you
> want. Feed them in two ways. (1) As *features*: append
> $\gamma_{t,\text{crisis}}$ as an extra column to the LightGBM feature
> matrix of [Chapter 11](ch11-tree-methods-vol.md), letting the tree split on regime
> membership directly. (2) As a *blend dial*: set the stress indicator
> $s_t = \gamma_{t,\text{high-vol}}$ and let the regime-dependent weights of
> the section on static vs. regime-dependent weights below interpolate smoothly between the
> calm-market and stressed-market blends, instead of flipping abruptly at a
> threshold.

### Choosing the Number of Regimes: BIC

How many regimes should there be, two (calm/crisis), three, four? You
cannot read $K$ off the log-likelihood, because adding components always
improves in-sample fit: a GMM with one blob per day fits perfectly and
learns nothing. The **Bayesian Information Criterion (BIC)**
(Schwarz, 1978) penalizes that complexity.

$$\text{BIC}(K) = \underbrace{-2\,\ell(\hat{\bm{\theta}})}_{\text{misfit}}
    + \underbrace{p\,\log T}_{\text{complexity penalty}},$$

where each term is:
- $\ell(\hat{\bm{\theta}})$ -- the maximized log-likelihood from the log-likelihood equation above at the EM solution,
- $p$ -- the number of free parameters; for a $K$-component GMM in $d$ dimensions with full covariances, $p = K\bigl(1 + d + \tfrac{d(d+1)}{2}\bigr) - 1$. Reading the count: each regime needs $1$ mixing weight, $d$ numbers for its mean vector, and $\tfrac{d(d+1)}{2}$ numbers for its (symmetric) covariance matrix, times $K$ regimes, minus $1$ because the mixing weights must sum to one so the last one is determined by the rest. (For $K=2$ regimes and $d=7$ features, $p = 2(1+7+28) - 1 = 71$ parameters.)
- $T$ -- the sample size (trading days), so $\log T$ scales the per-parameter penalty.

> **Intuition: In Plain English**
>
> BIC scores a model as "how badly it fits" plus "how much it costs in
> parameters." Each extra regime buys a lower misfit term but pays the
> $p\log T$ tax. You pick the $K$ that *minimizes* BIC: the point where
> one more regime no longer explains enough new structure to justify its
> parameters. In volatility data, $K=2$ or $K=3$ usually wins, markets
> have a calm state, a crisis state, and sometimes an in-between "elevated
> but orderly" state.

> **Project Connection: Why This Matters**
>
> Fit a GMM for each $K \in \{2,3,4\}$, record BIC, and pick the minimum.
> Then *inspect* the regimes: do the cluster means in the regime-inputs
> equation correspond to recognizable market
> conditions (low-$\operatorname{RV}$/low-VIX calm, high-$\operatorname{RV}$/high-jump crisis)? If $K=2$
> and $K=3$ have near-tied BIC, prefer the smaller, more interpretable model,
> a two-regime calm/crisis split is the cleanest fit for the
> regime-dependent blend, and it maps directly onto the two states of the
> Markov-switching model in the section on adding persistence below.

### The sklearn Workflow

The entire fit is a few lines with `scikit-learn`. The one
non-obvious knob is `n_init`.

> **Key Idea: GMM in scikit-learn**
>
> 1. **Standardize** the inputs with a trailing-window z-score (see the warning above; the Triple Expansion section).
> 2. **Fit** for each candidate $K$:
>    `GaussianMixture(n_components=K, covariance_type='full', n_init=10, random_state=0).fit(X)`
> 3. **Select** $K$ by minimizing `gmm.bic(X)`.
> 4. **Label** each day with soft probabilities `gmm.predict_proba(X)` (the responsibilities $\gamma_{tk}$), *not* the hard `gmm.predict(X)`.

> **Warning: Always Use `n_init` Restarts**
>
> The GMM log-likelihood is **non-convex**:
> the likelihood surface has multiple hills, not one. EM always climbs
> uphill, so it can get stuck on a smaller hill (a *local* maximum)
> depending on where it starts, that is why we try several random starting
> points and keep the best. A single bad start can merge a crisis regime
> into the calm one. Set `n_init=10` (ten random restarts, keeping the
> highest-likelihood solution) so the regimes are stable across reruns. Use
> `covariance_type='full'` unless you are short on data, volatility
> features are correlated within a regime (high $\operatorname{RV}$ comes with high VIX),
> and a diagonal covariance would miss that.

### Adding Persistence: Markov-Switching and HMMs

The GMM has a blind spot that matters enormously for volatility:
*it has no memory*. It classifies each day independently, so its
labels can flicker calm-crisis-calm-crisis on consecutive days even though
we know volatility regimes are sticky, a crisis that starts today is
overwhelmingly likely to persist tomorrow. How do we bake that
stickiness into the regime model?

> **Prereq: Hidden Markov Models**
>
> A **Hidden Markov Model (HMM)** has two layers: (1) a latent state
> sequence $s_t \in \{1, \ldots, K\}$ that evolves as a Markov chain, and
> (2) observed emissions $\mathbf{x}_t$ whose distribution depends on $s_t$. The
> key assumption is that $s_t$ depends on $s_{t-1}$ only (the Markov
> property). A Markov-switching model is an HMM whose emission is a
> regression rather than a static Gaussian.

**Markov-switching regression** (Hamilton, 1989) adds exactly the
missing persistence. The latent state still indexes the regime, but now a
**transition matrix** governs how the state evolves over time:

$$\mathbf{P} = \begin{pmatrix}
    p_{00} & p_{01} \\
    p_{10} & p_{11}
  \end{pmatrix},
  \qquad
  p_{ij} = \underbrace{\Pr(s_t = j \mid s_{t-1} = i)}_{\text{regime } i \to j},
  \qquad p_{i0} + p_{i1} = 1,$$

where each term is:
- $s_t \in \{0,1\}$ -- the latent regime (here $0=$ low-vol, $1=$ high-vol, so the diagonal $p_{00}$ is the calm-regime persistence; this is the opposite of Hamilton's expansion$=1$ coding),
- $p_{ij}$ -- the probability of moving from regime $i$ today to regime $j$ tomorrow,
- the **diagonal** entries $p_{00}, p_{11}$ -- the **persistence** of each regime: how likely it is to stay put.

> **Intuition: In Plain English**
>
> The transition matrix is the memory the GMM lacked. Where the GMM treats
> today as a fresh draw, the transition matrix says "if you
> were calm yesterday, you are probably calm today" through a high $p_{00}$
> (rows are today's regime, columns are tomorrow's, so $p_{ij}$ reads "from
> $i$ to $j$"). If each day you stay with probability $p$, the average run
> length before you leave is $1/(1-p)$, the same arithmetic as "if a coin
> lands heads $98\%$ of the time, you wait about $50$ flips for a tail." So
> the expected length of a regime is $1/(1-p_{ii})$ days, and a persistence
> near $0.98$ implies spells of roughly $50$ days. Estimating the
> regime now requires running forward through the whole sequence with the
> **Hamilton filter** (Hamilton, 1989), which combines yesterday's
> regime belief, the transition matrix, and today's observation into
> today's filtered probability $\Pr(s_t = k \mid \mathbf{x}_{1:t})$, the
> probability of today's regime using only data up to and including today
> (days $1$ through $t$).

> **Project Connection: Why This Matters**
>
> Persistent regime labels are far more useful as a blend dial than
> flickering ones. If your stress indicator $s_t$ jumps in and out of
> "crisis" on alternate days, the regime-dependent blend of
> the section on static vs. regime-dependent weights below will whipsaw between the calm and
> stressed weight sets, churning the forecast for no reason. A
> Markov-switching filter smooths the indicator using the persistence it
> learned from history, giving a regime signal that turns on at the start of
> a crisis and stays on until it genuinely ends.

The canonical demonstration of Markov-switching is Hamilton (1989)'s
two-state model of U.S. GNP growth (expansion vs. recession). We rebuild
that example on the object we actually care about: realized volatility.

> **Key Result: Two-State Markov-Switching Model on RV**
>
> Fit a two-state Markov-switching model to daily (log) realized volatility,
> $$\log \operatorname{RV}_t = \mu_{s_t} + \phi\bigl(\log \operatorname{RV}_{t-1} - \mu_{s_{t-1}}\bigr)
>     + \varepsilon_t,
>   \qquad \varepsilon_t \sim \mathcal{N}(0, \sigma_{s_t}^2),$$
> where each term is:
> - $\mu_{s_t}$ -- the regime-dependent average level of log-$\operatorname{RV}$, which flips between a calm value and a crisis value as the latent state $s_t$ switches (the double subscript means "the mean for whichever regime applies on day $t$"),
> - $\phi$ -- the **persistence** (autoregressive) coefficient, between $-1$ and $1$, controlling how strongly yesterday's deviation carries into today,
> - $\bigl(\log \operatorname{RV}_{t-1} - \mu_{s_{t-1}}\bigr)$ -- yesterday's gap above or below *its* regime mean,
> - $\varepsilon_t \sim \mathcal{N}(0,\sigma_{s_t}^2)$ -- random noise (the "$\sim$" reads "is distributed as") whose size $\sigma_{s_t}$ is itself regime-dependent, bigger in a crisis,
>
> with $s_t \in \{\text{low},\text{high}\}$ and the transition
> matrix above. A representative equity-index fit
> yields two clearly separated regimes:
> - a **low-vol state** with a low mean log-$\operatorname{RV}$ level ($\mu_{\text{low}}$) and high persistence $p_{00} \approx 0.98$ (calm spells last $\approx 1/(1-0.98) = 50$ days),
> - a **high-vol state** with a markedly higher mean ($\mu_{\text{high}} \gg \mu_{\text{low}}$) and persistence $p_{11} \approx 0.95$ (crisis spells last $\approx 20$ days), confirming the well-documented asymmetry that calm regimes are stickier than turbulent ones.
>
> The filtered probability $\Pr(s_t = \text{high} \mid \mathbf{x}_{1:t})$ spikes
> during known stress episodes (2008, 2020) without those dates being
> supplied as inputs, the analogue of Hamilton's filtered recession
> probabilities tracking NBER dates.

> **Intuition: In Plain English**
>
> The Markov-switching RV equation is just an AR(1), autoregressive of
> order $1$, meaning today depends on yesterday plus noise, for
> log-volatility whose
> *level* $\mu_{s_t}$ flips between a calm value and a crisis value, with
> the flips governed by the transition matrix. The two estimated means tell
> you where calm and crisis volatility sit; the two persistences tell you how
> long each lasts. Because the level shifts discretely, the model captures
> the abrupt jump into a high-vol regime that a single smooth AR process
> would smear out.

> **Project Connection: Link to Markov-Switching GARCH**
>
> Replacing the regime-dependent *mean* in
> the Markov-switching RV equation with a regime-dependent *GARCH
> variance recursion* gives the **Markov-switching GARCH** model: the
> $(\omega, \alpha, \beta)$ parameters of the GARCH update from
> [Chapter 5](ch05-garch-family.md) themselves switch with the latent state. This is
> the econometric cousin of the GINN idea in
> the GARCH-Informed Neural Networks section, where a neural network, rather than a
> two-state Markov chain, supplies the time-varying GARCH parameters.
> Both answer the same question: "what if the volatility dynamics
> themselves depend on the current regime?"

#### GMM vs. Markov-Switching: Which to Use

The table below contrasts the two on the dimensions that
matter for a volatility-forecasting pipeline.

**Table: Choosing between GMM and Markov-switching for regime identification.**

| Dimension | GMM | Markov-Switching |
|---|---|---|
| Temporal structure / persistence | None, each day classified independently, so labels can flicker | Markov chain: $s_t$ depends on $s_{t-1}$; persistence explicit via transition matrix $\mathbf{P}$ |
| Estimation | EM on the mixture (fast, scales well) | Hamilton filter (forward recursion; slower) |
| Output | Responsibilities $\gamma_{tk}$ per day | Filtered $\Pr(s_t \mid \mathbf{x}_{1:t})$ and smoothed $\Pr(s_t \mid \mathbf{x}_{1:T})$ |
| Python | `sklearn.mixture.GaussianMixture` | `statsmodels.tsa.regime_switching` |
| Best for | Quick soft labels; a regime feature for LightGBM | When persistence matters; a smooth blend dial |

> **Key Idea: Start with GMM; Upgrade to Markov-Switching for Persistence**
>
> For a first regime feature, a column of soft probabilities to hand the
> LightGBM model or a quick blend dial, the GMM is simpler, faster, and
> sufficient. Reach for Markov-switching only when day-to-day flickering of
> the regime label is actively hurting the blend, or when you want a regime
> signal whose persistence is calibrated from the data. The two are
> complementary: GMM answers "what does today look like?"; Markov-switching
> answers "what does today look like, given the whole run-up to it?"

### Regime Backtesting Hygiene

Regime-conditional forecasts look better in backtests than in production
for one reason: *the regime is only known with certainty in
hindsight*. When you fit a GMM (or smooth a Markov-switching filter) on
the full sample and then condition on the resulting labels, you have leaked
future information into today's regime call.

> **Warning: Test Regimes the Way You Will Trade Them**
>
> Three disciplines keep a regime overlay honest:
> 1. **Use soft probabilities, not hard labels** (workflow step 4 above). A strategy that flips fully risk-on at a hard "calm" label implicitly assumes a perfect classification you do not have, today's responsibility might be only $60\%$ calm, $40\%$ elevated.
> 2. **Test with lagged regime labels.** Apply yesterday's regime classification to today's blend, never a label that used today's or future data. For Markov-switching, use the *filtered* probability $\Pr(s_t \mid \mathbf{x}_{1:t})$, which uses only data up to and including today (days $1$ through $t$), not the *smoothed* $\Pr(s_t \mid \mathbf{x}_{1:T})$, which uses the *entire* sample (days $1$ through the last day $T$) and so secretly looks into the future: fine for describing history, fatal for backtesting a tradable signal.
> 3. **Check label stability.** Measure how often the GMM revises its call on the most recent days when one new observation arrives. A regime indicator that keeps changing its mind about the recent past is not a tradable signal.
>
> Report the regime-conditional $\operatorname{QLIKE}$ improvement only after passing
> these checks; a gain that survives lagged, soft labels is real, one that
> needs full-sample hard labels is hindsight.


### Static vs. Regime-Dependent Weights

Static blend weights assume that the relative accuracy of each model is
stable over time. This is often a good approximation for realized
volatility: HAR's linear structure captures most of the signal in calm
and turbulent markets alike. But there are situations where model
performance varies systematically across regimes, and regime-dependent
weights can help.

**Regime-dependent weighting** assigns different blend weights
depending on the current volatility regime:

$$w_k(t) =
  \begin{cases}
    w_k^{\text{low}} & \text{if } \operatorname{RV}_t^{(w)} < \tau, \\
    w_k^{\text{high}} & \text{if } \operatorname{RV}_t^{(w)} \geq \tau,
  \end{cases}$$

where each term is:
- $\operatorname{RV}_t^{(w)}$ -- the weekly realized volatility, used as a regime indicator,
- $\tau$ -- the regime threshold (e.g., the 75th percentile of the training-set $\operatorname{RV}^{(w)}$ distribution),
- $w_k^{\text{low}}, w_k^{\text{high}}$ -- separate blend weights for the low-volatility and high-volatility regimes, each calibrated on the corresponding subset of the validation data.

> **Intuition: In Plain English**
>
> If LightGBM consistently outperforms HAR during high-volatility weeks
> but underperforms during calm weeks, it makes sense to shift weight
> toward LightGBM when volatility is elevated and toward HAR when
> markets are quiet. Regime-dependent weights let you exploit this
> pattern. But the key word is "consistently", if the performance
> difference across regimes is noisy or unstable, regime conditioning
> adds complexity without improving accuracy.

> **Warning: Regime Weights Require Stable Performance Differences**
>
> Regime-dependent weights help only when model accuracy varies
> *systematically* across regimes, not just randomly. If the
> performance gap between HAR and LightGBM in high-vol vs. low-vol
> periods is unstable across rolling windows, regime conditioning will
> overfit to historical patterns that do not persist out of sample.
> Test for systematic variation before adding this complexity: compute
> model $\operatorname{QLIKE}$ separately in each regime on multiple validation folds
> and check whether the ranking is consistent.

> **Project Connection: Start Static, Upgrade If Justified**
>
> For the internship project, begin with static inverse-$\operatorname{QLIKE}$
> weights. After establishing the baseline blend performance, split the
> validation set by volatility regime and compare per-regime $\operatorname{QLIKE}$ for
> each model. If you find that LightGBM's advantage over HARQ-X is
> concentrated in high-volatility weeks (as the leverage-effect
> literature suggests it should be), regime-dependent weights are a
> justified upgrade. Document the per-regime performance gap as evidence.


## When to Use Pure ML vs. Hybrid

The table below summarizes the practical decision you face when choosing
a forecasting architecture. The default should be hybrid; deviate only
with good reason.

**Table: Architecture decision guide for volatility forecasting.**

| Architecture | Best When | Feature Set | Typical Setting |
|---|---|---|---|
| Pure HAR / HARQ | Only RV lags available; small sample ($<500$ days) | RV lags only | Quick benchmark; limited data access |
| Hybrid (HAR + ML) | Rich features available; daily or weekly horizon; reliability matters | RV lags + engineered features | Production forecasts; research baseline |
| Pure trees (GBM/XGB) | Rich features; intraday horizons; large sample ($>2000$ days) | Full feature set | High-frequency desks; feature importance studies |
| Pure deep learning | Raw sequential data; cross-asset pooling; very large sample | Raw returns / order flow | Multi-asset platforms; representation learning |

> **Key Idea: Default to Hybrid**
>
> Your default architecture should be hybrid, not pure ML. Start with HAR
> as a backbone and add ML complexity only where the residuals justify it.
> You earn the right to go pure ML only when you have a large sample, rich
> features, and evidence that the linear baseline leaves substantial
> structure in the residuals (Rahimikia and Poon, 2020).

### Practical Checklist

Before committing to an architecture, answer these questions:

1. **How large is your sample?** Below 500 daily observations, pure HAR is hard to beat. ML needs data.
2. **Do you have features beyond RV lags?** If not, a hybrid adds nothing because the ML stage has no new information.
3. **What is your forecast horizon?** At weekly or monthly horizons, HAR's multi-scale structure dominates. ML gains concentrate at the daily horizon.
4. **How much do you value interpretability?** HAR coefficients are directly interpretable. A hybrid with SHAP on the ML component preserves partial interpretability. Pure deep learning sacrifices it.
5. **What is your retraining budget?** Hybrids are cheap: refit HAR monthly, retrain ML weekly. Pure deep learning demands more compute.


### Standalone vs. Hybrid: A Visual Comparison

The figure below contrasts the pure ML approach (left) with the hybrid approach (right). The key difference: in the hybrid, ML operates on a reduced-variance target, which yields lower estimation error and better out-of-sample stability.

```mermaid
flowchart LR
    subgraph pure["Pure ML Approach"]
        data1["Full feature set"]
        ml1["ML model\n(GBM / NN)"]
        out1["$\hat{y}_{t+1}$"]
        data1 --> ml1 --> out1
    end

    subgraph hybrid["Hybrid Approach"]
        rvlags["RV lags"]
        har2["HAR"]
        richfeat["Rich features"]
        ml2["ML on $e_t$"]
        plus2(("$+$"))
        out2["$\hat{y}_{t+1}$"]
        rvlags --> har2
        richfeat --> ml2
        har2 --> plus2
        ml2 --> plus2
        plus2 --> out2
    end
```

**Figure:** Pure ML (left) must rediscover the linear trend that HAR captures for free. The hybrid (right) lets HAR absorb the trend and focuses ML on the residual, reducing both model complexity and overfitting risk.


## Summary

- Hybrid models decompose the forecasting problem into a linear component (HAR, GARCH) and a nonlinear residual component (ML), allowing each method to operate where it is strongest.
- HAR explains 40--60% of next-day RV with three coefficients; training ML on the residual rather than the raw target improves signal-to-noise and prevents the ML model from wasting capacity on structure that a linear model already captures.
- HAR-SVR uses support vector regression with an $\varepsilon$-insensitive loss on HAR residuals, automatically ignoring days where HAR is "close enough" and focusing on the hard cases.
- GINN hard-wires the GARCH recursion into a neural network, letting the network learn time-varying corrections to GARCH parameters rather than learning volatility dynamics from scratch (Cuchiero, Heiss, Khosrawi, and Spoida, 2024).
- NLP-augmented HAR (Word2Vec sentiment) yields 1--3% $\operatorname{QLIKE}$ improvement concentrated in crisis periods, but gains are fragile and source-dependent (Rahimikia, Zohren, and Poon, 2021).
- A simple 70/30 HAR/LightGBM weighted average is the safest production choice and is remarkably hard to beat with more complex ensembles.
- Stacking via a ridge meta-learner on OOS predictions adapts the combination weights to the data while guarding against overfitting at the meta-level.
- Three ensemble architectures offer increasing simplicity: feature stacking (coupling via embeddings, broken gradient flow), residual stacking (sequential stages with distinct roles), and prediction blending (fully independent models, weighted average).
- Feature stacking suffers from gradient isolation: LightGBM cannot backpropagate into the LSTM, so the embedding is never optimized for the tree's objective.
- Residual stacking (HAR $\to$ LightGBM $\to$ LSTM) gives each model a specialized role by construction and avoids cross-model coupling.
- Prediction blending is the simplest, most debuggable architecture and is supported by Optiver competition evidence (Optiver, 2021).
- Static blend weights (e.g., inverse-$\operatorname{QLIKE}$ weighting) are the default; regime-dependent weights help only when model performance varies systematically across volatility regimes.
- Pure ML (trees or deep learning) earns its place only when you have large samples, rich features, and evidence that the linear baseline leaves exploitable structure in residuals.
- Your default architecture should be hybrid: let HAR do the heavy lifting, then train ML on what remains.
- When evaluating hybrids, always report the base model's standalone performance alongside the hybrid, so the reader can judge the marginal contribution of the ML component.
- Ensemble diversification provides error reduction even when the ML component is only modestly accurate, as long as its errors are weakly correlated with the base model's errors.
- All combination weights and meta-learner parameters must be tuned on out-of-sample data to avoid inflating the apparent benefit of the hybrid.

> **Key Result: Chapter 13 Takeaways**
>
> | Concept | Key Result |
> |---|---|
> | Hybrid principle | Decompose into linear (HAR/GARCH) + nonlinear (ML) components |
> | HAR-SVR | $\varepsilon$-insensitive loss filters small residuals automatically |
> | GINN | Hard-wired GARCH recursion with NN-learned time-varying parameters (Cuchiero, Heiss, Khosrawi, and Spoida, 2024) |
> | NLP + HAR | 1--3% $\operatorname{QLIKE}$ gain, concentrated in crises (Rahimikia, Zohren, and Poon, 2021) |
> | 70/30 blend | HAR/LightGBM weighted average: simple, robust, hard to beat |
> | Stacking | Ridge meta-learner on OOS predictions adapts weights safely |
> | Architecture comparison | Feature stacking $<$ residual stacking $<$ prediction blending in simplicity and debuggability |
> | Regime weights | Upgrade from static only with evidence of systematic per-regime performance differences |
> | Default rule | Start hybrid; earn the right to go pure ML with evidence |
