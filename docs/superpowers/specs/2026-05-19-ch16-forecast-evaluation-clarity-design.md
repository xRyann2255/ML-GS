# Chapter 16 (Forecast Evaluation) Clarity Improvements

**Date:** 2026-05-19
**Chapter:** `vol-learning-guide/chapters/16-forecast-evaluation.tex`
**Approach:** Fix in Place + Add Connective Tissue (Approach B)
**Goal:** Fix six comprehension gaps identified by naive-reader analysis, without restructuring or removing existing content.

---

## Problem Statement

Chapter 16 introduces seven evaluation tools (QLIKE, MSE, MZ regression, DM test, MCS, purged CV, DSR) but has six comprehension gaps:

1. **QLIKE bias misunderstanding:** The chapter's emphasis on asymmetric penalties actively suggests QLIKE-optimal forecasts are biased high. It never states that QLIKE is minimized at the true variance.
2. **Worked examples show math, not meaning:** Every example computes a number but stops before explaining what it means practically or what action it implies.
3. **MZ diagnosis without prescription:** b = 0.85 means "too smooth" but the chapter never says what you'd change in your model.
4. **Tool connections are implicit:** Why both DM and MCS? When QLIKE vs MZ? Never stated directly.
5. **"This matters" without "do this":** Project connection boxes say things matter but stop short of concrete actions.
6. **MSE vs QLIKE example doesn't show a ranking reversal** despite claiming one can happen.

---

## Change Group 1: QLIKE Optimality Fix

### 1a. New intuition box after existing "In Plain English" box (after line 149)

Add a new intuition box titled "QLIKE Is Still Minimized at the True Value" immediately after the existing "In Plain English" box on lines 144-149. Contents:

- Show the one-line derivation: d/dh(ln h + sigma^2/h) = 1/h - sigma^2/h^2 = 0 at h = sigma^2.
- State explicitly: "The optimal forecast under QLIKE is the true variance, not a padded-up version of it. The asymmetry means errors on the low side are more costly, but the target is still dead center."
- Speed limit analogy: "Think of a speed limit. The best speed is exactly the limit. Getting caught going 20 over is worse than going 20 under, but that does not make 20-under the target. QLIKE works the same way: the best forecast is the true value, but being wrong on the low side hurts more."

### 1b. Reword existing "In Plain English" box (lines 144-149)

The current text ends with "underestimating volatility gets you fired; overestimating it merely costs some opportunity." Add a qualifier sentence: "This does not mean the optimal forecast is biased upward. It means that among two equally wrong forecasts, the one that errs low is more costly. The target is still the true variance."

### 1c. Reword QLIKE vs MSE figure caption (lines 366-370)

The caption currently says "QLIKE penalizes under-prediction much more harshly than over-prediction, matching the asymmetric risk preferences in volatility forecasting." Add: "Despite this asymmetry, QLIKE is minimized at the perfect forecast (ratio = 1), not at a ratio above 1."

---

## Change Group 2: Worked Example Improvements

### 2a. Replace MSE vs QLIKE example (lines 166-209)

Replace the current example with one where MSE and QLIKE actually disagree on rankings. Design:

- Model A: slightly worse on normal days, much better on the crisis day (reactive model).
- Model B: consistently accurate on normal days, terrible on the crisis day (stable model).
- MSE picks Model A (driven by the crisis day improvement).
- QLIKE picks Model B (because it values consistent accuracy across normal days).

Add an interpretation paragraph: "What this tells you: MSE picked Model A because it happened to be closer on the one extreme day. QLIKE picked Model B because it was more consistently accurate across normal days. For daily risk management, where you care about forecast quality on typical days, QLIKE's ranking is more useful. When MSE and QLIKE disagree, check whether the MSE ranking is driven by a handful of extreme days."

### 2b. DM test -- add interpretation after worked example (after line 526)

Add a paragraph:

- "What this tells you: DM = 2.09, p = 0.037 means you can credibly claim LightGBM beats HAR at the 5% level. This p-value goes in your results table next to the QLIKE numbers. If p had been 0.15, the improvement would be real in your sample but you could not rule out that a different sample would reverse it -- you would need more data or a larger improvement before claiming victory."
- "If you have a directional hypothesis (ML should beat HAR, not vice versa), a one-sided test is appropriate, halving the p-value to 0.018."

### 2c. MCS -- add guidance on survivors (after line 643)

Add a new intuition box or keyidea box:

- "When multiple models survive the MCS, you cannot rank among them statistically. Choose among survivors using secondary criteria: simplicity (HAR is easier to explain than LightGBM), computational cost (GARCH fits in seconds vs. minutes), interpretability, or economic value in a downstream application. The MCS does not pick your model -- it eliminates the ones you should not pick."
- "The MCS p-values for surviving models (1.000, 0.482, 0.312, 0.551) are not a ranking. They indicate how far each model is from elimination. A p-value of 0.312 means GARCH would be eliminated at alpha = 0.30 but survives at alpha = 0.10. Do not treat these as confidence scores."

### 2d. DSR -- add recovery path (after line 902)

Add a paragraph:

- "DSR near zero means your best strategy does not survive multiple-testing correction. This does not mean volatility forecasting is hopeless -- it means you tested too many strategies relative to your sample size. Your options: (1) get more data (longer backtest period reduces the luck threshold), (2) reduce the number of experiments by using stronger priors about which feature sets to test, (3) pre-register a single strategy before backtesting to set N = 1, or (4) accept that you cannot make a statistical Sharpe claim and justify the strategy on economic grounds instead."

### 2e. MZ regression -- add concrete prescriptions (after line 429)

Add a new intuition or keyidea box titled "What to Fix Based on MZ Results":

- "When b < 1 (forecast too smooth): your model over-relies on long-horizon averages. Try adding shorter-lag features, reducing regularization strength, or increasing model capacity."
- "When b > 1 (forecast too reactive): your model is chasing noise. Try increasing regularization, using a longer lookback, or smoothing the forecast with an exponential moving average."
- "When a > 0 (systematic under-prediction): check for retransformation bias if you forecast in log space (Section 16.3.1), or add a bias correction term."

---

## Change Group 3: Connective Tissue

### 3a. Tool roles summary box (after line 46, end of "Why Evaluation Methodology Matters")

Add a keyidea box titled "Seven Tools, Seven Questions":

"This chapter introduces seven tools. Each answers one question:
1. QLIKE: which model has lower loss? (Primary metric.)
2. MSE: does the ranking hold under a different loss? (Secondary check.)
3. MZ regression: is my forecast biased or too smooth? (Diagnostic.)
4. DM test: is the loss difference between two models statistically significant? (Pairwise test.)
5. MCS: given all candidate models, which ones survive? (Multi-model filter.)
6. Purged CV: how do I tune hyperparameters without leaking future data? (Training procedure.)
7. DSR: is my backtest Sharpe real after accounting for all experiments? (Multiple-testing correction.)
You will use all seven, in roughly this order."

### 3b. Explicit DM vs MCS relationship (start of MCS section, around line 539)

The current opening "The Diebold-Mariano test compares models in pairs" is a good start. Expand it:

"Use DM when you have a specific pairwise claim to make ('my ML model beats HAR'). Use MCS when you have a model zoo and need to know which ones to keep and which to discard. They are complementary: DM is your scalpel for targeted claims, MCS is your filter for the full candidate set."

### 3c. Reinforce QLIKE vs MZ relationship (MZ section, around line 379)

The existing sentence "QLIKE tells you which model has lower average loss, but it does not tell you why a forecast is bad" is good but easy to miss. Add after it:

"Think of QLIKE as the scoreboard and MZ as the film review. QLIKE tells you who won; MZ tells you what to fix."

### 3d. Strengthen transition before "What Doesn't Work" (line 921)

Add: "You now have the full evaluation toolkit. This section catalogs the mistakes these tools are designed to prevent, so you can recognize them in other people's work and avoid them in your own."

---

## Change Group 4: Smaller Fixes

### 4a. Embargo sizing justification (purged CV section, after line 755)

Add 1-2 sentences: "The embargo length should cover the autocorrelation decay of your features. For HAR features (which use lags up to 22 days), the serial correlation in RV drops below 0.05 within about 5-10 days, so 1-2% of a typical 1,000-2,500 day sample (10-50 days) is conservative. If you use features with longer memory, increase the embargo accordingly."

### 4b. Retransformation bias -- connect to QLIKE/MZ (end of worked example, around line 301)

Add: "Without this correction, the 10.5% systematic under-prediction on a typical sample inflates QLIKE loss by roughly 3-5% and shows up as a > 0 in the MZ regression. Applying the correction is often the single cheapest QLIKE improvement available."

### 4c. Project connection boxes -- add concrete actions

Review each project connection box and ensure it ends with a concrete verb. Examples of changes:

- Line 220 box: after "the headline number is the percentage reduction in QLIKE," add "Target a 30-80 bps improvement. Report the number to two decimal places in your results table."
- Line 647 box: after "you cannot honestly claim superiority," add "If your model and HAR both survive, report them as statistically equivalent and justify your model choice on secondary criteria (interpretability, computational cost, economic value)."
- Line 860 box: after "you will need to report DSR alongside the raw Sharpe," add "If DSR < 0.95, do not claim the strategy has skill. Report the DSR value and the number of trials N alongside the raw Sharpe."

---

## Out of Scope

- No restructuring of sections or reordering of content.
- No deletion of existing sections (lookahead taxonomy, retransformation bias stay as-is).
- No changes to TikZ diagrams or figures (except the figure caption fix in 1c).
- No changes to the bibliography or citation style.

## Success Criteria

After these changes, a reader should be able to:

1. Explain why QLIKE-optimal forecasts are NOT biased upward.
2. State what each worked example result means in practical terms and what action it implies.
3. Know when to use DM vs MCS and when to use QLIKE vs MZ.
4. Know what to do when b < 1 in the MZ regression.
5. Know what to do when multiple models survive the MCS.
6. Know what to do when DSR is near zero.
