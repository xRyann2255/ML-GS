# Ch13 Statistical Testing Expansion -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the `write-chapter` skill to write each section group. Use `verify-diagram` after each TikZ diagram is written. Use `convert-chapter-markdown` after the chapter is complete.

**Goal:** Expand `guides/vol-project-ref/chapters/ch13-evaluation.tex` with the statistical testing machinery needed to prove forecasting results are real -- not noise, not overfitting, not multiple-testing luck.

**Architecture:** Seven new sections appended after the existing content (Metrics, Validation Protocol, Success Target, QLIKE warning). Each section follows the project-ref style: terse opening, formula with variable definitions, 1-2 sentence interpretation, project-specific usage, warning/keyidea box where needed. No worked examples, no multi-paragraph intuition blocks.

**Tech Stack:** LaTeX (memoir class), tcolorbox environments, TikZ diagrams, natbib citations.

**Style reference:** Match the density and tone of existing project-ref chapters (ch04, ch09, ch12). One opening sentence per section. Tables and formulas dominate. Prose exists only to connect formulas to the project.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `guides/vol-project-ref/chapters/ch13-evaluation.tex` | **Modify** | Add 7 new sections after existing content |
| `guides/vol-project-ref/references.bib` | **Modify** | Add any missing citation keys (MincerZarnowitz1969, HarveyLeybourneNewbold1997, Bailey2014DSR, HarveyLiu2015) |
| `guides/vol-project-ref/main.tex` | No change | ch13 is already included |
| `guides/vol-project-ref/markdown/ch13-evaluation.md` | **Regenerate** | Convert updated chapter to markdown |

---

## Task 1: Add citation keys to references.bib

**Files:**
- Modify: `guides/vol-project-ref/references.bib`

- [ ] **Step 1:** Check which of these citation keys already exist in references.bib:
  - `MincerZarnowitz1969`
  - `HarveyLeybourneNewbold1997`
  - `Bailey2014DSR`
  - `HarveyLiu2015`
  - `DieboldMariano1995` (likely exists)
  - `HansenLundeNason2011` (likely exists)
  - `Patton2011` (likely exists)
  - `LopezdePrado2018` (likely exists)

- [ ] **Step 2:** Add any missing entries. The vol-learning-guide's `references.bib` has them all -- copy from there.

- [ ] **Step 3:** Commit: `chore: add statistical testing citations to vol-project-ref`

---

## Task 2: Write sections 13.4--13.5 (Forecast Calibration)

**Files:**
- Modify: `guides/vol-project-ref/chapters/ch13-evaluation.tex` (append after the existing `\begin{warning}[Train with $\QLIKE$...]...\end{warning}` block)

**Skill:** Invoke `write-chapter` with the specification below.

### Section 13.4: Retransformation Bias

**Opening line:** Models forecast in $\log$-$\RV$ space, but $\QLIKE$ evaluation and downstream applications (vol targeting, VaR) require level-space forecasts.

**Content:**
- The problem: naive exponentiation $\exp(\hat{y})$ is biased low due to Jensen's inequality.
- The correction formula:
  $$\widehat{\RV}_{t+1} = \exp\!\left(\widehat{\log \RV}_{t+1} + \frac{\hat{\sigma}^2_\varepsilon}{2}\right)$$
  where $\hat{\sigma}^2_\varepsilon$ is the variance of log-space forecast errors (estimate from rolling 60-day OOS window).
- Magnitude: ~4% at $h=1$, ~10% at $h=5$, ~19% at $h=22$.
- **keyidea box:** "Apply the correction before computing level-space $\QLIKE$. Without it, every forecast is systematically low, the bias grows with horizon, and MZ regression (Section~\ref{sec:mz}) will flag $a > 0$."

### Section 13.5: Mincer--Zarnowitz Regression

**Opening line:** $\QLIKE$ tells you which model wins; MZ tells you *why* a forecast is bad.

**Content:**
- Formula: $\sigma^2_t = a + b \cdot h_t + \varepsilon_t$
- Variable definitions (brief inline list, not itemize)
- Interpretation table (small, 4 rows):

  | Pattern | Diagnosis | Fix |
  |---------|-----------|-----|
  | $a > 0$, $b \approx 1$ | Systematic under-prediction | Check retransformation bias |
  | $a \approx 0$, $b < 1$ | Forecast too smooth | Increase reactivity to recent RV |
  | $a \approx 0$, $b > 1$ | Forecast too volatile | Regularize / increase shrinkage |
  | $a = 0$, $b = 1$ | Efficient forecast | Report $R^2$ as explanatory power |

- Joint F-test: $H_0: a = 0, b = 1$.
- **warning box:** "Use Newey--West (HAC) standard errors. Vol forecast errors are serially correlated; OLS standard errors are too small and reject $H_0$ too often."
- Project use: "Run MZ on every model before reporting $\QLIKE$. If $b = 0.7$, the model is too smooth -- it needs to react more aggressively to recent variance. MZ is the diagnostic; $\QLIKE$ is the grade."

---

## Task 3: Write sections 13.6--13.7 (Statistical Significance)

**Files:**
- Modify: `guides/vol-project-ref/chapters/ch13-evaluation.tex` (append after Task 2 content)

**Skill:** Invoke `write-chapter` with the specification below.

### Section 13.6: Diebold--Mariano Test

**Opening line:** A $\QLIKE$ improvement means nothing without a $p$-value.

**Content:**
- Loss differential: $d_t = L(\sigma^2_t, h^A_t) - L(\sigma^2_t, h^B_t)$ where $L = \QLIKE$.
- Test statistic:
  $$\mathrm{DM} = \frac{\bar{d}}{\sqrt{\widehat{\mathrm{Var}}(\bar{d})}} \;\xrightarrow{d}\; \N(0,1)$$
  where $\widehat{\mathrm{Var}}(\bar{d})$ uses Newey--West HAC with lag $\ell = \lfloor T^{1/3} \rfloor$.
- Decision rule: reject $H_0$ (equal predictive ability) if $|\mathrm{DM}| > 1.96$ at 5% level.
- **keyidea box:** "Every $\QLIKE$ comparison in the project must have a DM $p$-value next to it. Run pairwise: ML vs HAR, ML vs HARQ, ML vs SHAR, ML vs Realized GARCH. If $p > 0.05$, the improvement is not credible."
- **warning box -- small-sample correction:** "With $T < 100$ OOS days, use the Harvey--Leybourne--Newbold correction \citep{HarveyLeybourneNewbold1997}: replace $\N(0,1)$ critical values with $t_{T-1}$ and apply the finite-sample correction factor."

### Section 13.7: Model Confidence Set

**Opening line:** DM compares two models. The MCS compares all of them simultaneously without inflating the false-positive rate.

**Content:**
- Procedure (numbered list, 4 steps -- keep it tight):
  1. Start with full model set $\mathcal{M}_0$.
  2. Test $H_0$: all models in current set have equal expected loss.
  3. If rejected, remove the worst model (highest avg loss).
  4. Repeat until $H_0$ not rejected. Survivors = $\widehat{\mathcal{M}}^*_\alpha$.

- MCS $p$-value: the smallest $\alpha$ at which a model would be excluded. Report for every model.
- Reporting table template (this is key -- shows readers exactly how to present results):

  | Model | $\QLIKE$ | DM vs HARQ | MCS $p$ | In MCS$_{90\%}$? |
  |-------|----------|------------|---------|-------------------|
  | LightGBM (L0--2) | -- | -- | -- | -- |
  | HARQ | -- | -- | 1.000 | Yes |
  | HAR | -- | -- | -- | -- |
  | SHAR | -- | -- | -- | -- |
  | Realized GARCH | -- | -- | -- | -- |
  | ... | | | | |

- **keyidea box:** "The MCS is the credibility device for the GS presentation. If LightGBM and plain HAR both survive in the 90% MCS, you cannot claim ML superiority. If HAR is *excluded* and LightGBM survives, that is a defensible result. Use `arch.bootstrap.MCS` in Python or the `MCS` package in R."

- **TikZ diagram:** A simple flowchart showing the MCS elimination loop. Style: match the Rashomon pipeline diagram in ch12 (vertical flowblocks with arrows). 4 nodes:
  1. "Start: all $M$ candidate models"
  2. "Test $H_0$: equal predictive ability"
  3. Decision diamond: "$H_0$ rejected?"
  4. Yes -> "Remove worst model" (arrow back to step 2)
  5. No -> "Survivors = MCS$_\alpha$"

---

## Task 4: Write sections 13.8--13.9 (Multiple Testing & Strategy Validation)

**Files:**
- Modify: `guides/vol-project-ref/chapters/ch13-evaluation.tex` (append after Task 3 content)

**Skill:** Invoke `write-chapter` with the specification below.

### Section 13.8: Deflated Sharpe Ratio

**Opening line:** If the vol forecast feeds a trading strategy, the backtest Sharpe must survive correction for the number of configurations tested.

**Content:**
- The problem (2 sentences max): testing $N$ strategies inflates the expected best Sharpe. Under pure luck, $\E[\max_i \SR_i] \approx \sqrt{2 \ln N}$. For $N = 20$, this is $\approx 2.45$.
- DSR formula:
  $$\DSR = \Phi\!\left(\frac{(\widehat{\SR} - \SR_0)\sqrt{T-1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{\SR} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{\SR}^2}}\right)$$
  where: $\widehat{\SR}$ = observed annualized Sharpe, $\SR_0 = \sqrt{2\ln N}$ = null benchmark, $T$ = number of return observations, $\hat{\gamma}_3$ = skewness, $\hat{\gamma}_4$ = kurtosis.
- Decision rule: $\DSR > 0.95$ = credible. Below that, the Sharpe could be multiple-testing luck.
- **warning box:** "Every experiment counts as a trial. Every hyperparameter grid point, every feature set, every 'quick look' that influenced the final choice increments $N$. If you do not log experiments from day one, you cannot compute an honest DSR."
- Project use: "If the vol-targeting portfolio (success criterion 3) reports a Sharpe of 1.5 but you tested 20 configurations, the DSR will be near zero. Log every experiment. DSR $> 0.95$ is the bar."

### Section 13.9: Evaluation Pitfalls

**Opening line:** Six errors that invalidate results.

**Content:** A single `warning` box titled "What Invalidates Your Results" containing a numbered list:

1. **Random k-fold on time series.** Shuffling observations before splitting trains on the future. Reported accuracy collapses out of sample. Always purged CV or walk-forward.
2. **$\QLIKE$ improvement without DM test.** A 3% $\QLIKE$ gain with $p = 0.12$ is noise. Report the $p$-value.
3. **Sharpe without DSR.** A Sharpe of 1.5 from 20 experiments is below the luck threshold ($\SR_0 = 2.45$).
4. **Training on one regime, testing on another.** Training 2015--2019 (calm), testing 2020 (COVID) is a stress test, not a general evaluation.
5. **Lookahead in features.** Day-$t$ VIX close used to predict day-$t$ RV is look-ahead bias. All features must precede the forecast cutoff (see Chapter~\ref{ch:pipeline}, Section~\ref{sec:lookahead}).
6. **Tiny improvements without economic significance.** Beating HAR by 0.5% $\QLIKE$ with DM $p = 0.04$ is statistically real but economically meaningless after transaction costs. Pair DM with the vol-targeting backtest.

---

## Task 5: Write section 13.10 (Evaluation Workflow)

**Files:**
- Modify: `guides/vol-project-ref/chapters/ch13-evaluation.tex` (append after Task 4 content)

**Skill:** Invoke `write-chapter` with the specification below.

### Section 13.10: Evaluation Workflow

**Opening line:** Every forecasting experiment follows this pipeline.

**Content:**
- **TikZ diagram:** Vertical pipeline (like the Rashomon pipeline in ch12). Use `flowblock` style. 8 nodes:

  1. "Reserve holdout (final 6 months)" -- fill=prereqpurple!10
  2. "Initialize experiment log ($N = 0$)" -- fill=blue!8
  3. "Tune hyperparameters: purged $k$-fold CV" -- fill=blue!8
  4. "Walk-forward OOS: $\QLIKE$ (primary), MSE (secondary)" -- fill=blue!8
  5. "MZ regression: check $a = 0$, $b = 1$" -- fill=blue!8
  6. "DM test: pairwise vs each baseline" -- fill=blue!8
  7. "MCS: identify top-tier model set" -- fill=keyorange!10
  8. Decision diamond: "Strategy?" -- Yes -> "DSR on backtest Sharpe" (fill=memgold!15), No -> "Report" (fill=intgreen!10). Both lead to final "Report with all metrics" node.

  Side annotation on step 3: "Every experiment increments $N$. Log feature set, hyperparameters, $\QLIKE$."

- Below the diagram, a **keyidea box:** "This workflow is the minimum standard for credible results. Skip any step and the results do not survive review. The workflow does not guarantee you will find a good forecast. It guarantees that if you do, the evidence is honest."

- Summary reference table (compact, one row per tool):

  | Tool | Question It Answers | Key Reference |
  |------|-------------------|---------------|
  | $\QLIKE$ | Which forecast has lower loss? | \citet{Patton2011} |
  | Retransformation | Is my level-space forecast biased? | \citet{Patton2011} |
  | Mincer--Zarnowitz | Is the forecast calibrated? | \citet{MincerZarnowitz1969} |
  | Diebold--Mariano | Is the improvement statistically significant? | \citet{DieboldMariano1995} |
  | Model Confidence Set | Which models are top tier? | \citet{HansenLundeNason2011} |
  | Purged $k$-fold CV | Am I leaking future information? | \citet{LopezdePrado2018} |
  | Deflated Sharpe Ratio | Is the backtest Sharpe real? | \citet{Bailey2014DSR} |

---

## Task 6: Verify TikZ diagrams

**Skill:** Invoke `verify-diagram` for each TikZ diagram written in Tasks 3 and 5.

- [ ] **Step 1:** Compile the guide: `cd guides/vol-project-ref && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex`
- [ ] **Step 2:** Use `verify-diagram` to visually check:
  - The MCS elimination flowchart (Task 3)
  - The evaluation workflow pipeline (Task 5)
- [ ] **Step 3:** Fix any rendering issues and recompile.

---

## Task 7: Convert to markdown and commit

**Skill:** Invoke `convert-chapter-markdown` for ch13.

- [ ] **Step 1:** Run `convert-chapter-markdown` on `guides/vol-project-ref/chapters/ch13-evaluation.tex` to regenerate `guides/vol-project-ref/markdown/ch13-evaluation.md`.
- [ ] **Step 2:** Compile final PDF: `cd guides/vol-project-ref && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex`
- [ ] **Step 3:** Commit all changes:
  ```
  git add guides/vol-project-ref/chapters/ch13-evaluation.tex \
          guides/vol-project-ref/references.bib \
          guides/vol-project-ref/markdown/ch13-evaluation.md \
          guides/vol-project-ref/main.pdf
  git commit -m "feat(vol-project-ref): expand ch13 with statistical testing machinery

  Add retransformation bias, Mincer-Zarnowitz, Diebold-Mariano,
  Model Confidence Set, Deflated Sharpe Ratio, evaluation pitfalls,
  and complete evaluation workflow pipeline."
  ```

---

## Dependency Graph

```
Task 1 (bib entries)
  └─> Task 2 (sections 13.4--13.5)
        └─> Task 3 (sections 13.6--13.7 + MCS diagram)
              └─> Task 4 (sections 13.8--13.9)
                    └─> Task 5 (section 13.10 + workflow diagram)
                          └─> Task 6 (verify diagrams)
                                └─> Task 7 (markdown + commit)
```

Tasks 2--5 are sequential because each appends to the same file. Task 1 can run first independently. Tasks 6--7 are post-writing verification.
