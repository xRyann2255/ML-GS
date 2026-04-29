# Risk as Alpha — ML Learning Guide Design Spec

> **Companion learning document for the Risk-as-Alpha internship project.**
> Teaches everything needed to execute and defend the 20-week project plan,
> from asset pricing foundations through applied ML methodology.

**Target reader:** Strong math/stats background, some ML experience, no finance theory. Building finance knowledge from scratch.

**Format:** LaTeX document modeled on the dl-notes revision notes — same visual language (colored boxes, term-by-term explanations, worked numerical examples), adapted for project-driven learning instead of exam preparation.

**Project spec:** `docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md`
**Implementation plan:** `docs/superpowers/plans/2026-04-23-risk-as-alpha-plan.md`

---

## 1. Document Structure

### Two-Part Hybrid: 14 Chapters

**Part I — Foundations** (Chapters 1–8): Finance theory built from scratch + ML/statistical methods with finance-specific twists. Each chapter ends with a **Project Connection** box tying the material to a specific project phase and task.

**Part II — Applied Methodology** (Chapters 9–14): How to actually do the work. Assumes Part I knowledge. Dense with worked numerical examples and less expository text.

### Chapter Plan

#### Part I — Foundations

**Chapter 1: Asset Pricing Foundations**

- Stochastic discount factor (SDF) / pricing kernel
- No-arbitrage ↔ existence of positive SDF (fundamental theorem)
- Risk premia: returns as compensation for bearing risk
- Factor models: CAPM → Fama-French 3-factor → APT
- Cross-sectional vs. time-series tests of factor models
- Alpha, beta, information ratio — what these terms mean precisely
- **Papers woven in:** Cochrane (2005) *Asset Pricing*, Fama-French (1993)
- **Project Connection:** Why risk signals *should* predict returns — the theoretical license for the entire project

**Chapter 2: Intermediary Asset Pricing**

- Classical vs. intermediary asset pricing — why dealers matter
- He-Krishnamurthy (2013): capital constraints → risk premia; the intermediary SDF
- Adrian-Etula-Muir (2014): single intermediary-leverage factor, R²=77% cross-section of returns
- He-Kelly-Manela (2017): single pricing kernel across ALL asset classes (equities, bonds, FX, commodities, credit, options)
- Adrian-Shin (2010): dealer repo growth forecasts VIX innovations
- Adrian-Brunnermeier (2016): CoVaR as systemic-risk measure
- The data bottleneck: all academic work uses stale quarterly Fed Z.1 data; SecDB provides daily, correct-dealer-sign, cross-asset risk outputs
- **Project Connection:** This IS the core thesis. Every feature in Phase 2 is a proxy for intermediary constraints.

**Chapter 3: Risk Systems and Value-at-Risk**

- What VaR measures: the loss threshold at a given confidence level over a given horizon
- Computation methods: historical simulation, parametric (variance-covariance), Monte Carlo
- Component VaR: marginal contribution of each position/asset class to total VaR
- Factor-VaR decomposition: which risk factors drive the total VaR
- Scenario analysis and stress testing: what-if P&L under specified market moves
- VaR utilization: usage as percentage of risk limit — the constraint that matters
- Risk-model methodology changes: why they create spurious features (historical sim → Monte Carlo transitions, window-length changes)
- **Papers woven in:** Basel framework, Jorion (2006) *Value at Risk*
- **Project Connection:** Phase 0 data audit — understanding what each SecDB output actually measures before engineering features

**Chapter 4: Market Microstructure and Dealer Positioning**

- Dealer balance sheets: how market-makers hold and hedge inventory
- Delta hedging: replicating options payoffs, mechanical buying/selling
- Gamma hedging and the gamma-flip level: net long gamma (stabilizing) vs. net short gamma (amplifying)
- Options Greeks in depth: delta, gamma, vega, vanna (dDelta/dVol), charm (dDelta/dTime)
- Forced selling / fire sales: Coval-Stafford (2007) — mutual fund fire sales predict 5-day reversals
- Dealer gamma and intraday momentum: Baltussen et al. (2021) — net gamma sign determines whether last-30-minute returns continue or reverse
- Gamma fragility: Barbon-Buraschi (2021) — how dealer positioning amplifies moves
- Public vs. proprietary gamma data: Muravyev-Pearson-Pollet (2022) caveat on IVS/skew proxying borrow fees
- **Papers woven in:** Coval-Stafford (2007), Baltussen-Da-Lammers-Martens (2021), Barbon-Buraschi (2021), Ni-Pearson-Poteshman (2005/2021), Muravyev-Pearson-Pollet (2022)
- **Project Connection:** Feature engineering for both projects — VaR/scenario features (Project 1) and dealer Greeks (Project 2 fallback)

**Chapter 5: Regularized Linear Models**

- Ridge regression: L2 penalty, closed-form solution, bias-variance tradeoff
- Lasso: L1 penalty, sparsity, why it selects features
- Elastic net: combining L1 and L2
- Ridge on principal components: Kozak-Nagel-Santosh (2020) — matches nonlinear ML on SDF estimation
- Why ridge is the baseline: in finance's low signal-to-noise regime, if GBM doesn't beat ridge, you haven't learned anything nonlinear
- Regularization path and cross-validation for alpha selection
- **Prereq boxes:** eigendecomposition, SVD, bias-variance decomposition (bridging from user's existing stats knowledge)
- **Papers woven in:** Kozak-Nagel-Santosh (2020), Hastie-Tibshirani-Friedman ESL
- **Project Connection:** Ridge baseline in Phase 1 infrastructure — appears on every chart in the final presentation

**Chapter 6: Tree-Based Methods for Finance**

- Decision trees → random forests → gradient boosting (the progression)
- Gradient boosting math: functional gradient descent, loss minimization
- LightGBM: histogram-based splitting, leaf-wise growth, GOSS, EFB
- XGBoost: level-wise growth, exact vs. approximate split finding
- Hyperparameter choices for financial data: low max_depth (3-5), high min_child_samples, subsampling, L1/L2 regularization — why aggressive regularization is critical in low-SNR settings
- The GKX horse race: Gu-Kelly-Xiu (2020) — 60-year US equity panel, tree methods competitive, deep learning mostly oversold for tabular financial data
- When trees fail: non-stationarity, regime changes, extrapolation beyond training range
- **Papers woven in:** Gu-Kelly-Xiu (2020 RFS), Chen-Guestrin XGBoost (2016), Ke et al. LightGBM (2017)
- **Project Connection:** Primary model in Phase 2 — LightGBM on risk-system features, always compared against ridge baseline

**Chapter 7: Model Interpretation**

- SHAP: from cooperative game theory (Shapley values) to TreeSHAP
- The Shapley axioms: efficiency, symmetry, dummy, additivity — why these properties matter
- TreeSHAP: exact Shapley computation for tree ensembles in polynomial time
- SHAP summary plots, dependence plots, waterfall plots — what each shows
- MDI (Mean Decrease Impurity) vs. MDA (Mean Decrease Accuracy / permutation importance)
- Feature importance stability: checking whether importance rankings hold across CV folds — unstable importance = unreliable signal
- Why interpretation builds credibility: SHAP waterfall in presentations converts "black box" into "here's what drives the prediction"
- **Papers woven in:** Lundberg-Lee (2017), Breiman MDI/MDA
- **Project Connection:** SHAP analysis in Phase 2 signal testing, feature stability checks, Phase 5 presentation

**Chapter 8: Panel Econometrics**

- Why cross-asset studies need panel methods: multiple asset classes × time increases effective sample size
- Fixed effects vs. random effects: within-estimator, the Hausman test
- Clustered standard errors: by time (cross-sectional correlation) and by entity (serial correlation) — Petersen (2009)
- Fama-MacBeth two-pass regressions: first cross-sectional, then time-series averaging
- The He-Kelly-Manela test with real data: testing whether a single pricing kernel spans all asset classes
- When to use panel regression vs. pooled ML: complementary tools, not substitutes
- **Papers woven in:** Petersen (2009), Fama-MacBeth (1973), He-Kelly-Manela (2017)
- **Project Connection:** Cross-asset panel extension in Phase 4A — within-class vs. cross-prediction tests

#### Part II — Applied Methodology

**Chapter 9: Feature Engineering from Risk Systems**

- Point-in-time discipline: stamp every feature with when it was *known*, not when it *applied*
- Lookahead bias: the single most common and most damaging error in financial ML
- Knowledge-date lagging: VaR for date T is known at T+1 morning (after nightly risk run)
- Feature families with worked construction examples:
  - VaR utilization: usage/limit, rate-of-change, z-score over rolling window
  - Factor concentration: Herfindahl index on factor-VaR shares, top-3 factor share
  - VaR dynamics: delta VaR, component VaR by asset class, VaR momentum
  - Scenario P&L: rank, dispersion, worst-case identity, skewness
  - Cross-asset flow: component VaR share shifts, rolling cross-asset VaR correlation
  - Dealer Greeks (Project 2): net gamma, vega, vanna, charm; gamma-flip level, distance-to-flip
- Confound checking: adding public factors (VIX, credit spread, term slope) as controls — if signal vanishes, it's redundant
- **Papers woven in:** AFML Ch. 2-3 on data structures
- **Project Connection:** Phase 0 data pipeline (point-in-time), Phase 2 feature engineering (all families)

**Chapter 10: Labeling and Target Construction**

- Why labeling matters as much as features — the label IS the hypothesis
- Standard forward returns (1d, 5d, 21d) — simple but noisy
- Triple-barrier labeling: profit-taking barrier, stop-loss barrier, vertical (time) barrier
  - Volatility-scaled thresholds: barriers adapt to asset-class-specific move sizes
  - Worked example: step-by-step label assignment for a price path
- Meta-labeling: primary model predicts side (+1/-1), secondary model predicts size/confidence (0 to 1)
  - Precision-recall tradeoff: meta-labeling converts recall-oriented primary into precision-oriented system
- Label uniqueness and concurrency: how overlapping labels create dependence
- Prediction targets for the project:
  - VIX innovations (Adrian-Shin: dealer repos forecast this)
  - Realized volatility (higher SNR than returns)
  - Drawdowns in most-concentrated asset class
  - Cross-asset momentum reversals
- **Papers woven in:** AFML Ch. 3 (triple-barrier), Ch. 3.6 (meta-labeling)
- **Project Connection:** Phase 1 label construction module

**Chapter 11: Validation Frameworks**

- Why standard K-fold CV fails for time series: temporal autocorrelation leaks information
- Purged K-fold CV with embargo (AFML Ch. 7):
  - Purging: remove training observations whose labels overlap with test period
  - Embargo: additional buffer after test period excluded from training
  - Worked example: constructing 5 purged folds from 1,250 daily observations with 2% embargo
- Combinatorial Purged CV (CPCV, AFML Ch. 12):
  - Generate C(N, k) combinatorial test/train partitions
  - Produce a distribution of Sharpe ratios from a single history
  - Worked example: CPCV with 6 splits, 2 test groups → 15 paths
- Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014):
  - The problem: selection bias from multiple testing
  - Expected maximum Sharpe under null: E[max(SR)] grows with number of trials
  - DSR formula: probability that observed Sharpe exceeds expected max under null
  - Adjustments for skewness and kurtosis of returns
  - Worked example: computing DSR for Sharpe=1.2 with 30 trials on 5 years of data
- Haircut Sharpe (Harvey-Liu 2015):
  - Bonferroni correction: divide significance level by number of tests
  - Holm step-down: less conservative sequential rejection
  - BHY-FDR (Benjamini-Hochberg-Yekutieli): controls false discovery rate, even less conservative
  - Worked example: adjusting a Sharpe of 1.5 with 20 prior tests under each method
- Harvey-Liu-Zhu (2016) t > 3 hurdle: required t-statistic for new factor discovery given existing literature
- Probability of Backtest Overfitting (Bailey-Borwein-Lopez de Prado-Zhu 2014): probability that the best in-sample strategy underperforms OOS
- Experiment tracking for honest DSR: log every trial, even failed ones — the total count is the input to DSR
- The sample-size problem: 5 years of daily firm-level VaR = ~1,250 rows; Bailey et al. show ~45 independent trials exhaust Sharpe of 1.0 on this data
- **Papers woven in:** Bailey-Lopez de Prado (2014), Harvey-Liu (2015), Harvey-Liu-Zhu (2016), Bailey-Borwein-Lopez de Prado-Zhu (2014), AFML Ch. 7, 12
- **Project Connection:** Phase 1 validation stack — every number in the project runs through this gauntlet

**Chapter 12: Backtesting Methodology**

- Transaction-cost-aware P&L: parameterized spread/slippage per asset class
- Turnover as a first-class metric: a high-Sharpe signal with 200% daily turnover is worthless
- Capacity estimation: how much capital before market impact degrades returns
- Walk-forward out-of-sample testing: the holdout is sacred — one shot, no iteration
- Rolling-window stability: retrain on 6-month rolling windows, check feature importance consistency
- IC (Information Coefficient) and ICIR (IC Information Ratio): rank correlation between predictions and outcomes
- Sharpe, Sortino, hit rate, max drawdown — what each measures and when each matters
- P&L decomposition by regime: does the signal work in crisis, steady state, or both?
- Signal decay post-publication: McLean-Pontiff (2016) — published signals lose 30-50% efficacy
- Backtesting vs. paper trading vs. live: the gap between simulated and realized performance
- **Papers woven in:** McLean-Pontiff (2016), AFML Ch. 14-15
- **Project Connection:** Phase 1 backtester, Phase 5 walk-forward OOS, transaction cost sensitivity analysis

**Chapter 13: Regime Modeling**

- Why regime-awareness: signals that work in steady state may fail in crisis (and vice versa)
- Gaussian Mixture Models (GMM) for regime classification:
  - EM algorithm for fitting
  - Model selection: BIC for number of components
  - Feature choice: VIX, credit spread, term slope, USD, realized cross-asset correlation
- Two Sigma regime template: Crisis, Steady State, Inflation, Walking on Ice
- Regime-conditional signal analysis: decompose IC and Sharpe by regime
- ADWIN (Adaptive Windowing) for concept drift detection: automatic regime-change detection on prediction errors
- Factor timing caveat: Asness et al. (2017) — "Contrarian Factor Timing is Deceptively Difficult"; timing net of existing exposures often subtracts value
- Hamilton (1989) Markov-switching models — the classical alternative to GMM
- When regime-awareness helps: signals that are structurally different across regimes. When it hurts: overfitting to small in-regime samples
- **Papers woven in:** Asness et al. (2017), Hamilton (1989)
- **Project Connection:** Phase 4A regime overlay — decompose Project 1 signal performance by macro regime

**Chapter 14: Presenting Quantitative Research**

- Framing: "Causal hypothesis + ML testing" not "black box found alpha"
  - Lead with the theory (He-Krishnamurthy predicts X), show the test, present results
- Primary metrics: IC, Sharpe, turnover — always report all three together
- Ridge baseline on every chart: one line for your model, one dashed line for ridge
- SHAP waterfall plots for top predictions: converts "trust me" into "here's why"
- One slide per claim, one chart per slide
- What-didn't-work as a credibility tool: documented negative results show rigor
- Handling desk questions:
  - "What's the capacity?" → transaction cost sensitivity curve, breakeven cost
  - "What happens in a crisis?" → regime-decomposed P&L
  - "Why not just a linear model?" → ridge-vs-GBM comparison with marginal lift
  - "How is this different from [public factor]?" → confound check results
- Signal decay awareness: mention McLean-Pontiff, explain why proprietary data may be more durable
- **Papers woven in:** Kelly-Xiu (2023) survey for framing conventions
- **Project Connection:** Phase 5 presentation — the entire chapter is preparation for Week 20

---

## 2. LaTeX Design

### Preamble

Clone the dl-notes `src/preamble.tex` directly. Same packages, same TikZ node styles, same header/footer layout, same font (11pt report class, 2.5cm margins). Change only:

- **Title:** "Risk as Alpha — ML for Cross-Asset Signal Discovery"
- **Subtitle:** "A Learning Guide for the SecDB Signal Discovery Project"
- **Header right:** "Risk as Alpha Learning Guide"

### Color Scheme

Identical to dl-notes:
```
defblue      #1a5276
keyorange    #e67e22
intgreen     #1e8449
warnred      #c0392b
prereqpurple #6c3483
examteal     #117a65
memgold      #b7950b
```

### Box Environments (8 types)

Five carried over unchanged from dl-notes:

| Environment | Color | Purpose |
|---|---|---|
| `definition` | Blue | Formal definitions (VaR, SDF, Sharpe ratio, etc.) |
| `keyidea` | Orange | Core conceptual insights and algorithms |
| `intuition` | Green | Plain-English explanations bridging math/stats to finance |
| `warning` | Red | Common pitfalls (lookahead bias, overfitting traps, methodological errors) |
| `prereq` | Purple | Background knowledge — used aggressively mid-chapter |

Two adapted from dl-notes exam-specific boxes:

| Environment | Color | dl-notes Original | Adaptation |
|---|---|---|---|
| `projectconnection` | Teal | `examcontext` | Ties chapter content to specific project phase and task number |
| `workedexample` | Teal | `examquestion` | Worked numerical walk-through with step-by-step solution |

One adapted with renamed purpose:

| Environment | Color | dl-notes Original | Adaptation |
|---|---|---|---|
| `keyresult` | Gold | `memorise` | Headline result from a paper — the one-sentence finding to internalize |

### Math Shortcuts

Carry over all dl-notes math shortcuts (`\E`, `\R`, `\bx`, `\bW`, `\KL`, `\ELBO`, `\N`, `\tr`, `\diag`, `\softmax`, `\sigmoid`, `\relu`) and add:

```latex
\SDF         → \mathcal{M}  (stochastic discount factor)
\VaR         → \operatorname{VaR}
\CVaR        → \operatorname{CVaR}
\ES          → \operatorname{ES}  (expected shortfall)
\IC          → \operatorname{IC}  (information coefficient)
\SR          → \operatorname{SR}  (Sharpe ratio)
\DSR         → \operatorname{DSR} (deflated Sharpe ratio)
\HHI         → \operatorname{HHI} (Herfindahl-Hirschman index)
\SHAP        → \operatorname{SHAP}
\bGamma      → \boldsymbol{\Gamma} (gamma matrix)
\loss        → \mathcal{L} (loss function)
```

### Writing Conventions

Adapted from dl-notes CLAUDE.md:

1. **Project-first design:** every section must connect to a project phase. If a paragraph doesn't help the reader execute or defend the project, cut it.
2. **Concise:** if sayable in 1 sentence, use 1.
3. **Concrete examples:** always include actual numbers. No hand-waving.
4. **Term-by-term explanations:** every equation followed by a bulleted list explaining each term.
5. **Prereq boxes used aggressively:** mid-chapter, not just at start. The reader has strong math but no finance — bridge continuously.
6. **Cross-reference, don't repeat:** use `\ref{}` to reference earlier chapters.
7. **Factual accuracy is non-negotiable:** every claim sourced to a specific paper. Mark uncertain claims with `[VERIFY]`.
8. **Tone:** direct, confident, slightly informal. Address reader as "you."
9. **No padding prose:** every sentence earns its place.

### Chapter Template

Each chapter follows this structure:

1. **Project Connection box** (always first) — what project phase this chapter serves, which tasks it enables
2. **Introduction** — 2-3 sentences: what this chapter covers and why it matters
3. **Numbered sections** — one concept per section, building logically
4. **Within sections:**
   - Definition box for formal concepts
   - Term-by-term explanation after every equation
   - Worked numerical example where applicable
   - Key Result box for paper findings
   - Prereq boxes wherever new background is needed
   - Warning boxes for common pitfalls
   - Intuition boxes for plain-English understanding
5. **Summary** — 8-15 bullet points: "If you read nothing else"
6. **Key Results recap** — table of paper → result → project relevance

---

## 3. Paper Reference Methodology

### Requirement

Every factual claim about a paper's findings must be verified by downloading and reading the actual paper (or a reliable summary from the paper's abstract/introduction). No hallucinated statistics, no fabricated results.

### Process per Chapter

1. **Before writing:** download PDFs or fetch abstracts for all papers referenced in that chapter
2. **While writing:** cite specific results with page numbers or theorem numbers where possible
3. **Key Result boxes:** each must include the paper's actual reported statistic (e.g., "R²=77%" from Adrian-Etula-Muir Table 3)
4. **Verification pass:** after writing, a review agent re-checks every Key Result box against the source paper

### Paper Sources

- Academic papers: fetch from SSRN, NBER, journal websites, arXiv
- The Signal Discovery PDF in this repo contains an annotated bibliography of ~80 papers — use as an index
- AFML (Lopez de Prado 2018): reference by chapter number

---

## 4. Quality Assurance: Three-Pass Review per Chapter

Every chapter goes through three sequential review passes after initial drafting:

### Pass 1: Factual Accuracy Review

- Verify every Key Result box against the source paper
- Check all formulas against authoritative sources (textbooks, original papers)
- Confirm numerical worked examples produce correct results (re-derive by hand)
- Flag any claim without a clear source
- **Outcome:** list of corrections; apply before Pass 2

### Pass 2: Brevity Review

- Identify sentences that repeat information already stated
- Remove throat-clearing phrases ("It is important to note that...", "As mentioned earlier...")
- Collapse multi-sentence explanations into single sentences where possible
- Check that prereq boxes stay 5-10 lines
- Verify "every sentence earns its place" — if removing a sentence doesn't reduce understanding, remove it
- **Outcome:** list of cuts and condensations; apply before Pass 3

### Pass 3: Clarity Review

- Identify topics where a TikZ diagram would clarify (e.g., purged CV fold structure, triple-barrier labeling on a price path, SHAP waterfall anatomy, dealer gamma hedging flow)
- Flag passages where the jump from concept A to concept B is too large — add a bridging sentence or prereq box
- Check that worked examples have enough intermediate steps for the target reader (strong math, no finance)
- Verify intuition boxes actually provide intuition, not just restatements
- **Outcome:** list of diagrams to add, passages to expand; apply and finalize

---

## 5. Execution Strategy: Subagent-Driven Parallel Writing

### Chapter Dependencies

```
Part I (Chapters 1-8):
  Ch 1 (Asset Pricing)      ← standalone, no deps
  Ch 2 (Intermediary AP)     ← depends on Ch 1
  Ch 3 (Risk Systems/VaR)   ← standalone (finance, but independent of Ch 1-2)
  Ch 4 (Microstructure)     ← depends on Ch 3 (Greek concepts build on risk)
  Ch 5 (Regularized Linear) ← standalone (ML, no finance deps)
  Ch 6 (Tree Methods)       ← depends on Ch 5 (builds on linear baseline concept)
  Ch 7 (Interpretation)     ← depends on Ch 6 (SHAP applied to trees)
  Ch 8 (Panel Econometrics) ← standalone (stats, no deps on other chapters)

Part II (Chapters 9-14):
  Ch 9  (Feature Eng.)      ← depends on Ch 3, 4 (risk system knowledge)
  Ch 10 (Labeling)           ← standalone within Part II
  Ch 11 (Validation)         ← standalone within Part II
  Ch 12 (Backtesting)        ← depends on Ch 11 (uses validation concepts)
  Ch 13 (Regime Modeling)    ← standalone within Part II
  Ch 14 (Presenting)         ← depends on all others (synthesis chapter)
```

### Parallel Execution Waves

**Wave 1 (7 parallel agents):** Ch 1, Ch 3, Ch 5, Ch 8, Ch 10, Ch 11, Ch 13
- All standalone chapters with no dependencies

**Wave 2 (3 parallel agents):** Ch 2, Ch 4, Ch 6
- Depend on Wave 1 chapters

**Wave 3 (3 parallel agents):** Ch 7, Ch 9, Ch 12
- Depend on Wave 2 chapters (Ch 9 needs Ch 4 from Wave 2)

**Wave 4 (1 agent):** Ch 14
- Synthesis chapter, depends on all others

### Per-Chapter Agent Workflow

Each chapter agent:
1. Downloads/fetches relevant papers for that chapter
2. Writes the full chapter LaTeX
3. Runs Pass 1 (factual accuracy) — separate review subagent
4. Applies corrections
5. Runs Pass 2 (brevity) — separate review subagent
6. Applies cuts
7. Runs Pass 3 (clarity) — separate review subagent
8. Applies additions (diagrams, expansions)
9. Returns final chapter .tex file

### Review Subagents

Each review pass is a separate subagent dispatched by the chapter-writing agent:
- **Factual reviewer:** given the chapter draft + source papers, checks every claim
- **Brevity reviewer:** given the chapter draft, identifies all cuttable content
- **Clarity reviewer:** given the chapter draft + target reader profile, identifies confusion points

---

## 6. File Structure

```
ml-learning-guide/
├── main.tex                    # Master document
├── preamble.tex                # Shared preamble (cloned from dl-notes, adapted)
└── chapters/
    ├── 01-asset-pricing-foundations.tex
    ├── 02-intermediary-asset-pricing.tex
    ├── 03-risk-systems-var.tex
    ├── 04-market-microstructure.tex
    ├── 05-regularized-linear-models.tex
    ├── 06-tree-methods-finance.tex
    ├── 07-model-interpretation.tex
    ├── 08-panel-econometrics.tex
    ├── 09-feature-engineering.tex
    ├── 10-labeling-targets.tex
    ├── 11-validation-frameworks.tex
    ├── 12-backtesting-methodology.tex
    ├── 13-regime-modeling.tex
    └── 14-presenting-research.tex
```

Location: `C:\Users\ryanv\Documents\Projects\ML\ml-learning-guide\`

---

## 7. Estimated Scale

- **Part I:** ~140-170 pages (finance chapters longer due to building from scratch)
- **Part II:** ~80-100 pages (denser, more worked examples, less exposition)
- **Total:** ~220-270 pages
- **TikZ diagrams:** ~15-25 across the document (purged CV folds, triple-barrier price paths, SHAP waterfalls, dealer hedging flows, GMM regime visualization, etc.)

---

## 8. Success Criteria

The document succeeds if, after reading it, you can:

1. **Explain the core thesis** to your sponsor in one paragraph (intermediary asset pricing → SecDB signals)
2. **Justify every methodological choice** (why purged CV, why DSR, why ridge baseline, why LightGBM over deep learning)
3. **Understand what each SecDB output measures** and how to engineer features from it
4. **Implement the validation stack** by describing the algorithm to Claude (purged CV, CPCV, DSR, Haircut Sharpe)
5. **Interpret results critically** — know when a Sharpe is inflated, when a signal is redundant, when feature importance is unstable
6. **Present confidently** — frame results as theory-testing, handle desk questions, show ridge baseline alongside GBM
7. **Cite the right paper for every claim** — not because citation matters, but because understanding the literature lets you place your work in context
