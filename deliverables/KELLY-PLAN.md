# Experiment Ladder for Variance-Strategy Position Sizing

## Goal

The core sizing rule can be written as:

\[
f_t
=
\operatorname{clip}
\left(
c\frac{\hat\mu_t}{D_t},
0,3
\right)
\]

where:

\[
\hat\mu_t = K_t-\widehat{RV}_t
\]

- \(K_t\): implied variance / variance-swap strike from the option strip
- \(\widehat{RV}_t\): ML forecast of future realized variance
- \(D_t\): denominator used to scale risk
- \(c\): calibration constant
- Position is clipped to \([0,3]\)

The main research question is:

> **What should \(D_t\) be?**

The current baseline is:

\[
D_t = K_t
\]

and this currently produces an out-of-sample Sharpe around 3.44.

The experiments below are designed to understand why implied variance works so well as the denominator, whether it is approximating true P&L risk, and whether a better denominator exists.

---

# Summary Table

| Experiment | Denominator \(D_t\) | Main Question |
|---|---|---|
| Baseline | \(K_t\) | Current benchmark |
| 1 | \(\operatorname{Var}(\epsilon)\) | Does literal residual-variance Kelly sizing work? |
| 2 | Rolling \(\operatorname{Var}(\epsilon)\) | Does recent forecast uncertainty matter? |
| 3 | EWMA of \(\epsilon^2\) | Does faster-changing conditional risk help? |
| 4 | \(\widehat{E[\epsilon_t^2\mid X_t]}\) | Can conditional residual variance improve sizing? |
| 5 | \(K_t^\alpha\) | What functional relationship makes implied variance useful? |
| 6 | \(K_t^\alpha(\hat\sigma_{\epsilon,t}^2)^\beta\) | Combine market-implied and model-implied uncertainty |
| 7 | Predicted P&L variance | Can we model strategy risk directly? |
| 8 | Tail-risk denominator | Does variance miss crash risk? |
| 9+ | Calibration, interactions, ensembles, distributional Kelly | Deeper structural understanding |

---

# Phase 1 — Literal Residual-Variance Denominator

Define the forecast residual:

\[
\epsilon_t = RV_t-\widehat{RV}_t.
\]

If the ML model approximately estimates:

\[
\widehat{RV}_t \approx E_t[RV_t],
\]

then all uncertainty in future realized variance comes from the residual.

For a short variance position:

\[
\Pi_t \approx K_t-RV_t.
\]

Since \(K_t\) is known when entering the trade:

\[
\operatorname{Var}_t(\Pi_t)
=
\operatorname{Var}_t(RV_t)
\approx
\operatorname{Var}_t(\epsilon_t).
\]

So the most literal approximate Kelly denominator is the variance of forecast errors.

## Experiment 1A — Constant Residual Variance

Estimate on training data only:

\[
\sigma_\epsilon^2
=
\operatorname{Var}(\epsilon_t).
\]

Then size with:

\[
f_t
=
\operatorname{clip}
\left(
c\frac{K_t-\widehat{RV}_t}
{\sigma_\epsilon^2},
0,3
\right).
\]

### Compare against

1. Sign-only short/flat
2. Raw predicted edge:
   \[
   K_t-\widehat{RV}_t
   \]
3. Current rule:
   \[
   \frac{K_t-\widehat{RV}_t}{K_t}
   \]
4. Constant residual-variance denominator

### What this tells you

Because the denominator is constant, this mostly tests whether the **magnitude of the predicted variance edge itself** is useful for sizing.

If the current implied-variance rule massively outperforms this, then the denominator \(K_t\) is adding meaningful state information.

---

# Phase 2 — Time-Varying Residual Risk

A single unconditional variance assumes the ML model is equally uncertain every day. That is unlikely.

## Experiment 2A — Rolling Residual Variance

Use:

\[
D_t
=
\operatorname{Var}
(
\epsilon_{t-1},\ldots,\epsilon_{t-L}
).
\]

Test several fixed windows, for example:

\[
L\in\{21,63,126,252\}.
\]

Do not select the final window using the final test sample.

### Interpretation

This asks:

> If the model has recently been making large errors, should the strategy automatically size down?

---

## Experiment 2B — EWMA Residual Variance

Estimate:

\[
D_t
=
(1-\lambda)\epsilon_{t-1}^2
+
\lambda D_{t-1}.
\]

This allows risk estimates to react faster after volatility shocks.

Test a small pre-specified set of decay rates using validation data only.

### Compare

- Rolling 21-day
- Rolling 63-day
- Rolling 126-day
- Rolling 252-day
- EWMA
- Current implied-variance denominator

---

# Phase 3 — Does Implied Variance Predict ML Forecast Uncertainty?

This is one of the most important diagnostic experiments.

For every out-of-sample date save:

\[
K_t,\qquad
\widehat{RV}_t,\qquad
RV_t,\qquad
\epsilon_t,\qquad
\epsilon_t^2.
\]

## Experiment 3A — Implied-Variance Buckets

Sort observations by \(K_t\).

Create quintiles or deciles.

For each bucket calculate:

\[
E[\epsilon_t^2\mid K_t\text{ bucket}].
\]

Example table:

| Implied variance bucket | Mean squared RV forecast error |
|---|---:|
| Lowest 20% | ? |
| 20–40% | ? |
| 40–60% | ? |
| 60–80% | ? |
| Highest 20% | ? |

### Desired diagnostic

If residual variance increases strongly and monotonically with implied variance, that directly explains why \(K_t\) works as a risk denominator.

---

## Experiment 3B — Correlation

Calculate:

\[
\operatorname{corr}(K_t,\epsilon_t^2).
\]

Also consider rank correlation:

\[
\operatorname{SpearmanCorr}(K_t,\epsilon_t^2).
\]

This is a simple first diagnostic, although the relationship may be nonlinear.

---

## Experiment 3C — Power-Law Relationship

Estimate:

\[
\log \epsilon_t^2
=
a+\alpha\log K_t+u_t.
\]

This tests whether:

\[
E[\epsilon_t^2\mid K_t]
\propto K_t^\alpha.
\]

Your current denominator implicitly resembles:

\[
\alpha=1.
\]

But the empirical relationship may be closer to:

\[
\alpha=1.5
\]

or:

\[
\alpha=2.
\]

Then test:

\[
D_t=K_t^\alpha.
\]

Crucially, estimate \(\alpha\) using only training/past data.

---

# Phase 4 — Predict Conditional Residual Variance Directly

Turn risk estimation into a second ML problem.

Your first model predicts:

\[
\widehat{RV}_t.
\]

Now train another model with target:

\[
\epsilon_t^2
=
(RV_t-\widehat{RV}_t)^2.
\]

Call its prediction:

\[
\widehat{\sigma}_{\epsilon,t}^2.
\]

Then size using:

\[
f_t
=
\operatorname{clip}
\left(
c
\frac{K_t-\widehat{RV}_t}
{\widehat{\sigma}_{\epsilon,t}^2},
0,3
\right).
\]

This is much closer to true conditional Kelly sizing.

## Potential Features

Possible inputs for the uncertainty model include:

- Current implied variance
- Recent realized variance
- VIX-style term structure
- Volatility skew
- Recent SPX returns
- Recent absolute SPX returns
- Recent residual magnitudes
- Recent residual variance
- VIX changes
- Implied vol-of-vol proxies
- Option-skew measures
- Features already used by the RV model
- Ensemble disagreement, if available

All features must be known at time \(t\).

---

# Phase 5 — Does Implied Variance Contain Information Beyond Residual Variance?

Suppose the conditional residual-risk model works well, but the original \(K_t\) denominator still performs better.

Then implied variance is likely doing more than merely proxying ML forecast uncertainty.

## Experiment 5A — Hybrid Power Denominator

Try:

\[
D_t
=
K_t^\alpha
\left(
\widehat{\sigma}_{\epsilon,t}^2
\right)^\beta.
\]

Equivalently:

\[
\log D_t
=
\alpha\log K_t
+
\beta\log \widehat{\sigma}_{\epsilon,t}^2.
\]

Estimate \(\alpha\) and \(\beta\) strictly on training data.

### Interpretation

If both terms improve out-of-sample performance, implied variance contains information not fully captured by estimated residual variance.

Possible explanations:

- Jump risk
- Tail risk
- Liquidity stress
- Risk-neutral information
- Volatility-regime information
- Imperfections in the residual-risk model

---

# Phase 6 — Predict Strategy P&L Variance Directly

The ultimate object is not realized variance itself. It is strategy P&L.

Approximately:

\[
\Pi_t=K_t-RV_t.
\]

Instead of predicting the uncertainty of \(RV_t\), directly estimate:

\[
\widehat{\mu}_{\Pi,t}
=
E_t[\Pi_t]
\]

and:

\[
\widehat{\sigma}_{\Pi,t}^2
=
\operatorname{Var}_t(\Pi_t).
\]

Then size:

\[
f_t
\propto
\frac{
\widehat{\mu}_{\Pi,t}
}{
\widehat{\sigma}_{\Pi,t}^2
}.
\]

This is cleaner once the backtest includes:

- Bid/ask spreads
- Transaction costs
- Slippage
- Replication imperfections
- Mark-to-market effects
- Changes in option liquidity

## Experiment 6A

Train the risk model against actual strategy P&L residuals rather than RV residuals.

Compare:

\[
D_t=\widehat{\operatorname{Var}}(RV-\widehat{RV})
\]

against:

\[
D_t=\widehat{\operatorname{Var}}(\Pi_t).
\]

---

# Phase 7 — Test Whether Variance Is the Right Risk Measure

Short variance has strongly non-Gaussian downside.

Two positions with identical variance may have very different crash exposure.

## Experiment 7A — Expected Shortfall Denominator

Try a sizing score such as:

\[
\frac{\hat\mu_t}
{\widehat{ES}_{95,t}}.
\]

Or use:

\[
\widehat{ES}_{99,t}.
\]

---

## Experiment 7B — Tail-Loss Probability

Model:

\[
P_t(\Pi_t<-L)
\]

for one or more economically meaningful loss thresholds \(L\).

Or equivalently:

\[
P_t(RV_t>K_t+x).
\]

This tests whether high-Sharpe sizing is accidentally concentrating risk immediately before rare volatility explosions.

---

# Phase 8 — Isolate the 31-Day Conviction Overlay

Define the raw sizing score:

\[
q_t=
\frac{\hat\mu_t}{D_t}.
\]

The current conviction factor is approximately:

\[
C_t
=
\frac{1}{31}
\sum_{j=1}^{31}|q_{t-j}|.
\]

Final exposure is roughly:

\[
f_t=q_tC_t.
\]

Run the strategy both with and without this factor.

## Experiment 8A — Does Conviction Predict Future Returns?

Bucket dates by \(C_t\).

For each bucket calculate:

\[
E[\Pi_t],
\]

\[
\operatorname{Var}(\Pi_t),
\]

and:

\[
\text{Sharpe}.
\]

This tests whether recent strong signals identify persistent high-opportunity regimes.

---

## Experiment 8B — Alternative Conviction Measures

Compare:

1. Mean absolute recent signal:
   \[
   \frac1L\sum |q|
   \]

2. Mean signed recent signal:
   \[
   \frac1L\sum q
   \]

3. Fraction of recent days agreeing in sign

4. EWMA conviction

5. Recent signal standard deviation

6. Current signal divided by recent signal volatility

7. Median absolute recent signal

If only one specific construction works, investigate whether it has a genuine economic interpretation.

---

# Phase 9 — Signal Calibration

Kelly sizing requires the magnitude of the numerator to mean something.

It is not enough for the model to predict direction correctly.

Define:

\[
\hat\mu_t=K_t-\widehat{RV}_t.
\]

Bucket \(\hat\mu_t\) into deciles.

For each decile calculate:

\[
E[\Pi_t\mid \hat\mu_t\text{ decile}].
\]

### Key Question

Does larger predicted edge actually correspond to larger realized average profit?

You want a reasonably monotonic relationship.

If only the sign works and signal magnitude is poorly calibrated, continuous Kelly-style sizing is less justified.

---

# Phase 10 — Two-Dimensional Interaction Maps

This is one of the best ways to understand why the current denominator works.

## Experiment 10A — Edge × Implied Variance

Create a 2-D grid.

Rows:

\[
K_t\text{ quintile}
\]

Columns:

\[
(K_t-\widehat{RV}_t)\text{ quintile}.
\]

For each cell calculate:

\[
E[\Pi],
\]

\[
\sigma(\Pi),
\]

\[
\frac{E[\Pi]}{\sigma(\Pi)},
\]

win rate, and tail losses.

This can show, for example, whether:

> A large predicted variance premium is highly attractive in calm markets but much less reliable when implied variance is already extremely elevated.

That would naturally justify a denominator involving \(K_t\).

---

## Experiment 10B — Edge × Estimated Model Uncertainty

Repeat with rows based on:

\[
\widehat{\sigma}_{\epsilon,t}^2.
\]

Now compare whether implied variance or direct model uncertainty better separates good and bad opportunities.

---

## Experiment 10C — Implied Variance × Model Uncertainty

Rows:

\[
K_t
\]

Columns:

\[
\widehat{\sigma}_{\epsilon,t}^2.
\]

This tells you whether the two variables carry redundant or complementary information.

---

# Phase 11 — Does Risk Depend on Signal Magnitude?

Large model disagreements with the market may themselves be less reliable.

Test:

\[
E[\epsilon_t^2\mid |\hat\mu_t|].
\]

If forecast error rises with signal magnitude, then the largest apparent opportunities should be damped.

Try:

\[
D_t
=
K_t^\alpha
|\hat\mu_t|^\gamma.
\]

Or use predicted residual variance as a function of both \(K_t\) and \(|\hat\mu_t|\).

This can prevent the strategy from treating the largest model-market disagreements as automatically the strongest bets.

---

# Phase 12 — Ensemble Uncertainty

Train multiple RV models.

For example:

\[
\widehat{RV}_t^{(1)},
\ldots,
\widehat{RV}_t^{(M)}.
\]

Measure model disagreement:

\[
U_t
=
\operatorname{Var}_m
\left(
\widehat{RV}_t^{(m)}
\right).
\]

Then try:

\[
D_t
=
\widehat{\sigma}_{\epsilon,t}^2
+
\lambda U_t.
\]

This separates two kinds of uncertainty:

### Aleatoric uncertainty

The market itself is inherently difficult to predict today.

### Epistemic uncertainty

Your models disagree because they are unsure about the regime or mapping.

This may be particularly useful around unusual regimes.

---

# Phase 13 — Distributional Realized-Variance Prediction

Instead of predicting only:

\[
E_t[RV],
\]

predict the entire conditional distribution.

For example:

\[
Q_{10}(RV),
\qquad
Q_{50}(RV),
\qquad
Q_{90}(RV).
\]

Two days can have the same expected realized variance but very different right-tail risk.

For a short-variance strategy, that distinction matters enormously.

Potential approaches:

- Quantile regression
- Distributional boosting
- Gaussian location-scale models
- Mixture models
- Bayesian models
- Neural distributional forecasts

Then derive sizing from the whole predicted payoff distribution.

---

# Phase 14 — Exact Kelly Instead of Gaussian Kelly

The common approximation:

\[
f^*\approx\frac{\mu}{\sigma^2}
\]

is based on a local/quadratic approximation.

Short-volatility returns are not Gaussian.

If you can estimate the full conditional return distribution \(R_t\), solve:

\[
f_t^*
=
\arg\max_f
E_t[
\log(1+fR_t)
].
\]

Then apply:

\[
f_t
=
\operatorname{clip}(f_t^*,0,3).
\]

This is a more theoretically faithful Kelly implementation.

You can evaluate the expectation using:

- Monte Carlo draws from the predicted conditional distribution
- Historical conditional resampling
- Quantile approximation
- Parametric distribution fitting

---

# Phase 15 — Directly Test the Functional Form of the Denominator

Instead of assuming a particular risk proxy, let the data tell you which transformation works.

Test a family:

\[
D_t
=
K_t^\alpha
\]

over a pre-specified grid of \(\alpha\).

Then:

\[
D_t
=
a+bK_t
\]

\[
D_t
=
a+bK_t+cK_t^2
\]

\[
D_t
=
\exp(a+b\log K_t)
\]

and potentially monotonic spline relationships.

The important part is to select the form using training/validation data, never the untouched final test set.

---

# Phase 16 — Residual Distribution by Volatility Regime

Do more than compare residual variance.

For each implied-variance bucket calculate:

- Mean residual
- Standard deviation
- MSE
- MAE
- Skew
- Kurtosis
- 95th percentile absolute error
- 99th percentile absolute error

Your ML model may become not only less precise in high-volatility regimes but also more right-tail-skewed.

That would strengthen the case for tail-risk-aware sizing.

---

# Phase 17 — Residual Autocorrelation

Test whether:

\[
\epsilon_t
\]

or:

\[
\epsilon_t^2
\]

is serially correlated.

If squared errors cluster, recent residual variance should be informative.

Useful diagnostics:

- ACF of residuals
- ACF of squared residuals
- Ljung–Box tests
- Residual variance after large misses

If squared residuals are highly persistent, EWMA or GARCH-style risk estimation becomes more justified.

---

# Phase 18 — GARCH-Style Residual-Risk Model

Instead of rolling or EWMA variance, fit something like:

\[
\sigma_{\epsilon,t}^2
=
\omega
+
\alpha\epsilon_{t-1}^2
+
\beta\sigma_{\epsilon,t-1}^2.
\]

Then use:

\[
D_t=\sigma_{\epsilon,t}^2.
\]

You can also add implied variance as an exogenous variable:

\[
\sigma_{\epsilon,t}^2
=
\omega
+
\alpha\epsilon_{t-1}^2
+
\beta\sigma_{\epsilon,t-1}^2
+
\gamma K_t.
\]

This directly tests whether implied variance adds information beyond recent forecast-error clustering.

---

# Phase 19 — Regime-Specific Models

Split the market into regimes based on information known ex ante.

For example:

- Low implied variance
- Medium implied variance
- High implied variance
- Rising volatility
- Falling volatility
- Positive skew shock
- Negative skew shock

Estimate separate relationships between:

\[
\epsilon_t^2
\]

and risk variables in each regime.

The optimal denominator may differ significantly across regimes.

---

# Phase 20 — Compare With Standard Volatility Targeting

Use a very simple benchmark:

\[
f_t\propto\frac{1}{\sqrt{K_t}}
\]

or another conventional volatility-scaling rule.

Then compare it to:

\[
\frac{K_t-\widehat{RV}_t}{K_t}.
\]

This tells you how much value comes from:

1. Basic risk scaling
2. The ML expected-edge forecast
3. The interaction of the two

---

# Phase 21 — Numerator/Denominator Ablation

Run a clean ablation table.

Suggested rows:

| Variant | Description |
|---|---|
| A | Always short 1× |
| B | ML short/flat 1× |
| C | Raw edge sizing |
| D | Edge / constant residual variance |
| E | Edge / rolling residual variance |
| F | Edge / EWMA residual variance |
| G | Edge / implied variance |
| H | Edge / \(K^\alpha\) |
| I | Edge / predicted residual variance |
| J | Hybrid denominator |
| K | Direct P&L-risk sizing |
| L | Exact/distributional Kelly |
| M | Each of the above + conviction overlay |

This is probably the clearest way to identify where the 3.44 Sharpe is actually coming from.

---

# Phase 22 — Cap Sensitivity

Your current exposure is clipped at 3×.

Test:

\[
\text{cap}\in\{0.5,1,1.5,2,2.5,3,4,5\}.
\]

Do not choose the best cap on the final test set.

Track:

- Sharpe
- CAGR / average return
- Volatility
- Max drawdown
- Worst daily loss
- Expected shortfall
- Fraction of days at the cap
- P&L contribution from capped days

A robust sizing signal should not require one extremely specific cap to work.

---

# Phase 23 — Fractional Kelly

Test:

\[
0.25f^*,
\qquad
0.5f^*,
\qquad
0.75f^*,
\qquad
f^*.
\]

Because estimated Kelly inputs are noisy, fractional Kelly can materially improve robustness.

---

# Phase 24 — Stability Across Time

Evaluate every major variant separately across:

- Calendar years
- Volatility regimes
- Bull markets
- Bear markets
- Crisis periods
- Calm periods

A strategy with Sharpe 3.44 overall could still be coming from one unusually profitable sub-period.

Track both average performance and consistency.

---

# Phase 25 — Concentration of Returns

Calculate:

- Percentage of total P&L generated by best 1% of days
- Percentage generated by best 5%
- Percentage lost on worst 1%
- Sharpe excluding the best 5 days
- Sharpe excluding the worst 5 days

This is particularly important for short-volatility strategies.

---

# Phase 26 — Proper Overlap and Serial-Correlation Handling

If you initiate overlapping multi-day variance exposures every day, do not treat eventual trade outcomes as independent daily returns.

Evaluate:

1. Actual daily marked-to-market portfolio P&L
2. Autocorrelation of portfolio returns
3. HAC / Newey–West adjusted Sharpe where appropriate
4. Non-overlapping subsamples as a robustness check

This is essential for validating the 3.44 Sharpe.

---

# Phase 27 — Transaction-Cost Stress Tests

Stress:

- Bid/ask assumptions
- Slippage
- Option liquidity
- Tail-strike execution
- Fees
- Delayed execution
- Missing quotes

Run at:

- Base estimated costs
- 1.5× costs
- 2× costs
- 3× costs

A strategy this strong should ideally remain attractive under materially worse execution assumptions.

---

# Phase 28 — Prediction Timing / Lookahead Audit

Verify for every feature:

> Was this exact value genuinely observable at the moment the position would have been entered?

Audit:

- Option quotes
- Strike availability
- Expiry selection
- VIX-style strip construction
- SPX closing values
- Realized-volatility features
- ML features
- Corporate/calendar data
- Rolling normalizations
- Training-window boundaries

This is especially important when reconstructing option strips historically.

---

# Core Diagnostics to Report for Every Experiment

For every strategy variant, report the same metrics.

## Performance

- Annualized Sharpe
- Mean return
- Annualized volatility
- CAGR, if meaningful
- Sortino ratio
- Maximum drawdown

## Tail Risk

- Worst day
- Worst week
- Worst month
- 95% VaR
- 99% VaR
- 95% Expected Shortfall
- 99% Expected Shortfall
- Skew
- Kurtosis

## Exposure

- Mean position
- Median position
- Position standard deviation
- Fraction of flat days
- Fraction of days at 3× cap
- Turnover

## Robustness

- Performance by year
- Performance by implied-volatility regime
- Performance during volatility spikes
- Performance excluding best days
- Performance excluding worst days

## Signal Quality

- Correlation between predicted and realized RV
- Correlation between predicted edge and realized P&L
- Edge-decile calibration
- Residual MSE
- Conditional residual MSE

---

# Recommended Research Order

If starting from the current strategy, run the experiments in this order.

## Immediate Tests

1. **Constant residual variance denominator**
   \[
   D_t=\operatorname{Var}(\epsilon)
   \]

2. **Rolling residual variance**
   \[
   D_t=\operatorname{Var}_{t-L:t-1}(\epsilon)
   \]

3. **EWMA residual variance**

4. **Plot / bucket squared residuals against implied variance**

5. Calculate:
   \[
   \operatorname{corr}(K_t,\epsilon_t^2)
   \]

6. Estimate:
   \[
   \log\epsilon_t^2=a+\alpha\log K_t+u_t
   \]

7. Test:
   \[
   D_t=K_t^\alpha
   \]

## Second Wave

8. Train a model for:
   \[
   \widehat{\sigma}_{\epsilon,t}^2
   \]

9. Compare:
   \[
   K_t,
   \quad
   K_t^\alpha,
   \quad
   \widehat{\sigma}_{\epsilon,t}^2
   \]

10. Test hybrid:
   \[
   K_t^\alpha
   (\widehat{\sigma}_{\epsilon,t}^2)^\beta
   \]

11. Repeat using **actual strategy P&L variance** rather than RV residual variance.

12. Isolate the 31-day conviction factor.

## Deeper Research

13. Edge calibration

14. 2-D interaction maps

15. Residual risk versus signal magnitude

16. Ensemble uncertainty

17. GARCH-style residual-risk model

18. Tail-risk denominators

19. Distributional RV forecasting

20. Exact conditional Kelly

---

# The Two Most Important Initial Statistics

Before building anything complicated, calculate:

\[
\boxed{
\operatorname{corr}(K_t,\epsilon_t^2)
}
\]

and estimate:

\[
\boxed{
\log \epsilon_t^2
=
a+\alpha\log K_t+u_t
}
\]

where:

\[
\epsilon_t
=
RV_t-\widehat{RV}_t.
\]

These provide the simplest direct evidence for whether implied variance is acting as a proxy for the true conditional uncertainty of your realized-variance forecast.

If that relationship is strong out of sample, it gives a natural explanation for why:

\[
\frac{K_t-\widehat{RV}_t}{K_t}
\]

works so well as a sizing rule.

If a different power \(K_t^\alpha\), a learned residual-risk model, or a hybrid denominator works even better out of sample, that gives you a principled path toward improving the strategy while also making the mathematical interpretation much cleaner.
