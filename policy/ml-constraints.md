# ML Volatility Forecasting — Non-Negotiable Constraints

These rules govern all ML vol forecasting work. They are always active and cannot be overridden without explicit user approval.

---

## 1. Never use random k-fold CV on time-series data

Always use purged/blocked k-fold or expanding-window walk-forward. Random k-fold causes catastrophic look-ahead bias in time-series forecasting — future information leaks into training folds, producing inflated performance metrics that do not generalize.

**Acceptable CV strategies:**
- Purged k-fold with gap parameter (purge window ≥ forecast horizon)
- Blocked k-fold (contiguous temporal blocks, no shuffling)
- Expanding-window walk-forward (train on all prior data, test on next block)

**Never acceptable:** `sklearn.model_selection.KFold(shuffle=True)` or any random split on time-indexed data.

---

## 2. QLIKE is the primary loss function, not MSE

QLIKE (quasi-likelihood loss) penalizes underestimation of volatility more severely than overestimation, which aligns with the economic asymmetry of vol forecasting — underestimating vol is more costly than overestimating it.

$$\text{QLIKE} = \frac{1}{T} \sum_{t=1}^{T} \left( \frac{\sigma_t^2}{\hat{\sigma}_t^2} - \ln\frac{\sigma_t^2}{\hat{\sigma}_t^2} - 1 \right)$$

- QLIKE is the primary optimization target for all models (including LightGBM custom objective).
- MSE is reported as a secondary metric only, never optimized directly.
- Model comparisons use QLIKE first; MSE as a tie-breaker only.

---

## 3. No model architecture proposals before features are understood

Research features first. The model choice follows from understanding what the features look like. Do not jump to "let's try a transformer" before demonstrating that the feature set is well-characterized.

**Sequence:** Data → Features → Validate features → Then choose model.

---

## 4. Research-first: verify on data before building

Do not jump from "paper says X works" to "let's implement X." First verify X on our data. Academic results may not replicate on our specific universe, frequency, or time period.

**Required steps:**
1. Read the paper's methodology.
2. Compute the relevant statistic/feature on our data.
3. Confirm the effect exists (or document that it doesn't).
4. Only then propose implementation.

---

## 5. Feature engineering > model complexity

A simple model with good features beats a complex model with bad features. HARQ with 5 well-chosen features often beats ML with dozens of noisy features.

- Prioritize feature quality, interpretability, and economic motivation.
- Add complexity only when simpler models demonstrably plateau.
- Every feature must have an economic or statistical justification — no "kitchen sink."

---

## 6. Every experiment must be independently reportable

Full methodology, data description, results, and statistical tests. No "I tried X and it worked" without documentation.

**Minimum documentation per experiment:**
- Hypothesis (what are we testing?)
- Data subset (symbols, date range, frequency)
- Method (model, features, CV strategy, hyperparameters)
- Results (QLIKE, MSE, DM test vs. baseline)
- Conclusion (does it improve? by how much? is it significant?)
- COVID handling (included/excluded/separate regime)

---

## 7. Train in log-RV space, not raw RV

Log transform gaussianizes the RV distribution and stabilizes variance. All models operate on $\log(\text{RV})$; predictions are exponentiated only for final evaluation and reporting.

$$y_t = \log(\text{RV}_t), \quad \hat{y}_t = \text{model}(x_t), \quad \widehat{\text{RV}}_t = \exp(\hat{y}_t)$$

- Features based on RV (daily, weekly, monthly) are also in log space.
- QLIKE evaluation uses exponentiated predictions vs. realized values.
- Never train a model on raw RV — the heavy-tailed distribution causes instability.

---

## 8. COVID period requires explicit regime handling

Feb–Jun 2020 is an extreme outlier that distorts model training and evaluation. Every experiment must state whether COVID is:
- **Included** — model must handle extreme values (justify why)
- **Excluded** — removed from train and test (state date range removed)
- **Separate regime** — handled via regime indicator or separate model

There is no default. The choice must be justified per experiment. Results with and without COVID should be compared when feasible.
