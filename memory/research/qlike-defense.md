---
created: 2026-05-19
updated: 2026-05-19
tags: [qlike, loss-function, evaluation, patton, mse, volatility]
status: active
priority: P1
relates: [evaluation-framework, volatility]
---

# Why QLIKE Instead of MSE — Full Defense

## Prompt 1: "Why QLIKE instead of MSE? Help me understand the asymmetry. If we want to predict the value of an option as closely as possible, then surely we want a symmetric loss function? Or is the mean of QLIKE and MSE the same? And it's just skewed?"

---

## The short answer

QLIKE is **not** just a skewed MSE. It's a fundamentally different loss function that measures **relative** (proportional) forecast error rather than **absolute** error. And critically: Patton (2011) proved that QLIKE produces **consistent model rankings** even when the true volatility is measured with noise — MSE does not.

---

## Why MSE fails for variance forecasting

### Problem 1: Heteroskedasticity of errors

Suppose true daily variance is σ². Forecast errors for variance scale with the level of variance. In a crisis (σ² = 0.04, i.e. 20% annualized vol), absolute errors are naturally 10× larger than in calm markets (σ² = 0.004).

MSE = (σ̂² - σ²)²

This means **a few extreme observations (COVID, GFC) dominate the entire MSE**. Your "best model by MSE" is just the one that got lucky in March 2020. That's not useful.

### Problem 2: Variance is multiplicative, not additive

Think about it economically. If true vol is 10% and you forecast 12%, you're off by 20% relatively. If true vol is 40% and you forecast 42%, you're off by 5% relatively. MSE treats both as the same (error = 2%). But the first error is far more consequential for trading.

---

## What QLIKE actually does

QLIKE = σ²/σ̂² − log(σ²/σ̂²) − 1

This is the **ratio** of realized to forecast, minus the log of that ratio, minus 1. It's minimized when σ²/σ̂² = 1 (perfect calibration).

Key properties:
- **Scale-invariant.** A 2× overestimate at vol = 10% is penalized identically to a 2× overestimate at vol = 40%.
- **Equivalent to MSE in log-space.** If you think of log(σ²) as the quantity being forecast, QLIKE is approximately MSE on log-variance. Since RV is approximately log-normal, this is the natural metric.

---

## Now your option pricing question

> "If we want to predict the value of an option as closely as possible, then surely we want a symmetric loss function?"

Here's where the intuition breaks down. For an ATM option:

Option price ≈ 0.4 × S × σ × √T

The option price is **proportional** to σ. So a 10% relative error in σ causes a 10% relative error in option price, **regardless of the vol level**.

- σ = 10%, error = ±1% vol → ~10% mispricing
- σ = 40%, error = ±4% vol → ~10% mispricing

**MSE says the second error (4% vol) is 16× worse. But the economic impact is identical.** QLIKE correctly treats them as equally bad, because it measures the relative error.

So QLIKE IS the correct symmetric loss for option pricing — it's symmetric in **proportional** terms. MSE is symmetric in absolute terms, which is the wrong scale for prices that are proportional to vol.

---

## The asymmetry in QLIKE (and why it's economically correct)

QLIKE does have a mild asymmetry in how it treats over- vs under-prediction. Let's quantify:

| Forecast error | QLIKE penalty |
|---|---|
| Overpredict by 2× (σ̂² = 2σ²) | 0.5 - log(0.5) - 1 ≈ 0.19 |
| Underpredict by 2× (σ̂² = 0.5σ²) | 2 - log(2) - 1 ≈ 0.31 |

**Underprediction is penalized ~60% more than overprediction** for the same multiplicative error.

Is this economically sensible? **Yes:**
- Underpredicting vol → you sell options too cheaply → unlimited downside
- Overpredicting vol → you buy options too expensively → limited loss (premium paid)
- Underpredicting vol → you underestimate risk → portfolio blows up
- Overpredicting vol → you hold extra hedges → small drag on returns

The downside of underestimating volatility is categorically worse than overestimating it. QLIKE's mild asymmetry captures this natural asymmetry of the problem.

---

## The killer argument: Patton (2011) proxy robustness

Even if you didn't buy the economic arguments above, there's a mathematical reason that's unassailable:

**We never observe true integrated variance.** We observe realized variance, which is a noisy proxy. Patton (2011) proved:

- **QLIKE:** Rankings are *invariant* to the noise in the proxy. If model A is truly better than model B, QLIKE will rank A above B regardless of how noisy RV is as a proxy.
- **MSE:** Rankings *can flip* depending on the noise level. You might declare model B the winner simply because the proxy happened to be measured a certain way.

This is the theorem: QLIKE belongs to the class of "robust" loss functions whose expected ranking is preserved under imperfect proxies. MSE does not.

---

## Summary table

| Property | MSE | QLIKE |
|----------|-----|-------|
| Symmetric in... | Absolute (σ̂² - σ²) | Proportional (σ̂²/σ²) |
| Dominated by extremes? | Yes (COVID = 90% of loss) | No (scale-invariant) |
| Same mean? | No — different answer for "best model" | — |
| Proxy-robust? (Patton 2011) | **No** — rankings can flip | **Yes** — consistent |
| Underprediction penalty | Same as over | ~60% higher — correct |
| Natural for log-normal RV? | No | Yes (≈ MSE in log-space) |
| Option pricing relevance | Wrong scale | Right scale (proportional) |

---

**Bottom line:** QLIKE isn't "MSE but skewed." It's the loss function that matches the multiplicative nature of volatility and produces reliable model rankings despite measurement noise. MSE on raw variance is essentially meaningless for model selection in vol forecasting.

---
---

## Prompt 2: "But if we predict realised vol instead of realised variance, would MSE work?"

---

Closer, but still no. Here's why:

---

## Taking the square root helps but doesn't fix it

If σ² ~ LogNormal, then σ ~ LogNormal^(1/2) — still right-skewed, still heteroskedastic. The proportional error problem is reduced but not eliminated:

| True vol | Forecast | Absolute error | Relative error | MSE contribution |
|----------|----------|---------------|----------------|-----------------|
| 10% | 12% | 2% | 20% | 4 bps² |
| 40% | 48% | 8% | 20% | 64 bps² |

Same 20% relative error → 16× different MSE penalty. Crisis observations still dominate.

---

## The real fix: MSE in log-space ≈ QLIKE

Here's the punchline. If you take logs first:

MSE on log(σ²) = (1/T) × Σ (log σ̂²_t - log σ²_t)²

This IS (approximately) QLIKE. A second-order Taylor expansion of QLIKE around perfect calibration gives you MSE in log-space.

So the "fix" to MSE isn't switching from σ² to σ — it's switching to log(σ²). That's exactly why the project trains in log-RV space. When we train with MSE loss on log(RV), we're approximately optimizing QLIKE.

---

## Hierarchy of "how broken is MSE"

| Target | Heteroskedasticity | Proxy-robust? | Equivalent to... |
|--------|-------------------|---------------|-------------------|
| σ² (variance) | Severe | No | Nothing useful |
| σ (vol) | Moderate | No | Slightly better, still wrong |
| log(σ²) (log-variance) | Minimal | ≈ Yes | ≈ QLIKE |

---

## Why not just use MSE on log-RV and call it a day?

We mostly do! For **training** (gradient descent, OLS), MSE on log-RV is the practical objective. LightGBM can do this natively.

QLIKE proper matters for **evaluation and model comparison** because:

1. The exact QLIKE formula preserves Patton's proxy-robustness guarantee. The MSE-on-log approximation is close but loses the formal invariance proof at the tails.
2. QLIKE's asymmetry (underprediction penalized more) isn't captured by symmetric MSE on log-RV.
3. The literature reports QLIKE, so we need it for apples-to-apples comparison with published results.

---

**TL;DR:** MSE on vol (σ) is better than MSE on variance (σ²), but the correct answer is MSE on log(σ²), which is approximately QLIKE. That's what we actually train on. We use exact QLIKE for model ranking because of the formal robustness guarantee and the economically-correct asymmetry.

---
---

## Prompt 3: "I still don't understand, if option pricing is proportional to vol, will the asymmetry of QLIKE mean that we will misprice option pricing compared to another loss function that is like qlike but is symmetric?"

---

This is a really sharp question. The answer is **no** — QLIKE's asymmetry does NOT bias your forecasts or misprice options. Here's why:

---

## The optimal forecast under QLIKE is the same as under MSE

Take the QLIKE loss and find the forecast $h$ that minimizes expected loss:

$$L(h, \sigma^2) = \frac{\sigma^2}{h} - \log\frac{\sigma^2}{h} - 1$$

First-order condition:

$$\frac{\partial}{\partial h} \mathbb{E}[L] = -\frac{\mathbb{E}[\sigma^2]}{h^2} + \frac{1}{h} = 0$$

Solving: $h^* = \mathbb{E}[\sigma^2]$

**The optimal point forecast under QLIKE is the conditional mean** — exactly the same target as MSE. The asymmetry doesn't shift where you're aiming.

---

## So what does the asymmetry actually do?

It doesn't affect the **target** — it affects how you **rank imperfect models** that all miss the target.

Think of it this way:
- Model A systematically underpredicts by 10% (relative)
- Model B systematically overpredicts by 10% (relative)

Under MSE on log-RV (symmetric): both equally bad.
Under QLIKE: Model A is worse.

But **neither model is the one you'd choose** if you could find an unbiased model C. The asymmetry doesn't make you "aim high" — it makes you prefer the less dangerous kind of miscalibration *when forced to choose between two bad models*.

---

## The key distinction: loss for OPTIMIZATION vs loss for SELECTION

| Purpose | What we use | Why |
|---------|-------------|-----|
| **Training** (finding optimal parameters) | MSE on log-RV | Targets E[σ²], symmetric, LightGBM-native |
| **Selection** (which model to deploy) | QLIKE | Same target, but ranks imperfect models by economic consequence |

Your forecast itself doesn't "know" it was selected by QLIKE. It's still targeting the conditional mean. QLIKE just helps you pick which forecasting approach produces the best-calibrated conditional means.

---

## Analogy

Imagine hiring between two candidates:
- Candidate A sometimes shows up 2 hours late, sometimes 2 hours early
- Candidate B sometimes shows up 2 hours early, sometimes 4 hours late

If "lateness has worse consequences than earliness" (like missing meetings), you prefer Candidate A. But this doesn't mean you're now "aiming for early" — you still want someone who arrives on time. Your preference criterion just reflects that one failure mode is costlier.

---

## Would a symmetric log-space loss give different pricing?

A symmetric alternative would be MSE on log(σ²):

$$\text{MSE}_{\log} = (\log \hat{\sigma}^2 - \log \sigma^2)^2$$

This targets $\exp(\mathbb{E}[\log \sigma^2])$ — the **geometric mean** of variance, which is *lower* than the arithmetic mean due to Jensen's inequality.

So if anything, the symmetric loss function would produce **lower forecasts** than QLIKE — and you'd underprice options more often. QLIKE targeting the arithmetic mean is actually the correct target for pricing (since option value is linear in σ at first order).

---

**Bottom line:** QLIKE's asymmetry doesn't make you overshoot. It targets the same conditional mean as any other proper loss function. It just tells you which *direction of miss* is more costly when selecting between imperfect models — and it's right: underestimating vol is more expensive than overestimating it.
