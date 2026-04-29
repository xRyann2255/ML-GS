# Risk as Alpha — ML Learning Guide Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 14-chapter LaTeX learning guide (~220-270 pages) teaching everything needed for the Risk-as-Alpha ML internship project, modeled on the dl-notes revision notes style.

**Architecture:** Infrastructure first (preamble + main.tex cloned from dl-notes), then 14 chapters written by parallel subagents in 4 dependency waves. Each chapter agent downloads relevant papers, writes LaTeX, then runs 3 sequential review passes (factual accuracy, brevity, clarity) via subagents. Final assembly compiles all chapters into a single PDF.

**Tech Stack:** LaTeX (report class, tcolorbox, TikZ, amsmath), lualatex for compilation (Unicode-safe; fallback: pdflatex)

**Spec:** `docs/superpowers/specs/2026-04-23-risk-as-alpha-learning-guide-design.md`

---

## Chunk 1: Infrastructure

### Task 1: Create Directory Structure

**Files:**
- Create: `ml-learning-guide/main.tex`
- Create: `ml-learning-guide/preamble.tex`
- Create: `ml-learning-guide/chapters/` (directory)

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p ml-learning-guide/chapters
```

- [ ] **Step 2: Write preamble.tex**

Clone from `dl-notes/src/preamble.tex` with these changes:
1. Replace `examcontext` environment with `projectconnection` (same styling, default title changes to "Project Connection")
2. Replace `examquestion` environment with `workedexample` (same styling, title prefix changes to "Worked Example:")
3. Replace `memorise` environment with `keyresult` (same styling, default title changes to "Key Result")
4. Add new math shortcuts for finance domain
5. Change header right text to "Risk as Alpha Learning Guide"

Write this exact content to `ml-learning-guide/preamble.tex`:

```latex
% ══════════════════════════════════════════════════════════════
% Risk as Alpha — ML Learning Guide Preamble
% ══════════════════════════════════════════════════════════════

% ── Packages ──
\usepackage[margin=2.5cm, headheight=14pt]{geometry}
\usepackage{amsmath, amssymb, amsthm, mathtools, cancel}
\usepackage{bm}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{tcolorbox}
\usepackage{fancyhdr}
\usepackage{parskip}
\usepackage{tikz}
\usepackage{booktabs}
\usepackage{truncate}
\usepackage{multirow}
\usepackage{array}
\usepackage{longtable}
\usetikzlibrary{arrows.meta, positioning, fit, backgrounds, calc, decorations.pathreplacing}
\tcbuselibrary{breakable, skins}

% ── Colours ──
\definecolor{defblue}{HTML}{1a5276}
\definecolor{keyorange}{HTML}{e67e22}
\definecolor{intgreen}{HTML}{1e8449}
\definecolor{warnred}{HTML}{c0392b}
\definecolor{prereqpurple}{HTML}{6c3483}
\definecolor{examteal}{HTML}{117a65}
\definecolor{memgold}{HTML}{b7950b}

% ── Custom Environments ──
% definition          — blue box   — formal definitions
% keyidea             — orange box — important conceptual insights & algorithms
% intuition           — green box  — plain-English explanations and analogies
% warning             — red box    — common pitfalls and methodological errors
% prereq              — purple box — background knowledge (use LIBERALLY)
% projectconnection   — teal box   — ties chapter content to project phase/task
% workedexample       — teal box   — worked numerical walk-through
% keyresult           — gold box   — headline result from a paper

\newtcolorbox{definition}[1][]{
  colback=blue!3, colframe=defblue, fonttitle=\bfseries,
  title={#1}, breakable, boxrule=0.6pt
}
\newtcolorbox{keyidea}[1][]{
  colback=orange!4, colframe=keyorange, fonttitle=\bfseries,
  title={#1}, breakable, boxrule=0.6pt
}
\newtcolorbox{intuition}[1][]{
  colback=green!3, colframe=intgreen, fonttitle=\bfseries,
  title={#1}, breakable, boxrule=0.6pt
}
\newtcolorbox{warning}[1][]{
  colback=red!3, colframe=warnred, fonttitle=\bfseries,
  title={#1}, breakable, boxrule=0.6pt
}
\newtcolorbox{prereq}[1][]{
  colback=purple!3, colframe=prereqpurple, fonttitle=\bfseries,
  title={#1}, breakable, boxrule=0.6pt
}
\newtcolorbox{projectconnection}[1][Project Connection]{
  colback=teal!3, colframe=examteal, fonttitle=\bfseries,
  title={#1}, breakable, boxrule=0.6pt,
  colbacktitle=examteal!15
}
\newtcolorbox{workedexample}[1][]{
  colback=teal!2, colframe=examteal, fonttitle=\bfseries,
  title={Worked Example: #1}, breakable, boxrule=0.6pt,
  colbacktitle=examteal!10
}
\newtcolorbox{keyresult}[1][Key Result]{
  colback=yellow!4, colframe=memgold, fonttitle=\bfseries,
  title={#1}, breakable, boxrule=0.6pt,
  colbacktitle=memgold!15
}

% ── Math Shortcuts (carried over from dl-notes) ──
\newcommand{\E}{\mathbb{E}}
\newcommand{\R}{\mathbb{R}}
\newcommand{\bx}{\mathbf{x}}
\newcommand{\bz}{\mathbf{z}}
\newcommand{\bw}{\mathbf{w}}
\newcommand{\bh}{\mathbf{h}}
\newcommand{\bW}{\mathbf{W}}
\newcommand{\btheta}{\bm{\theta}}
\newcommand{\softmax}{\operatorname{softmax}}
\newcommand{\sigmoid}{\sigma}
\newcommand{\KL}{\mathrm{KL}}
\newcommand{\N}{\mathcal{N}}
\newcommand{\tr}{\operatorname{tr}}
\newcommand{\diag}{\operatorname{diag}}
\newcommand{\relu}{\operatorname{ReLU}}

% ── Math Shortcuts (finance-specific) ──
\newcommand{\SDF}{\mathcal{M}}
\newcommand{\VaR}{\operatorname{VaR}}
\newcommand{\CVaR}{\operatorname{CVaR}}
\newcommand{\ES}{\operatorname{ES}}
\newcommand{\IC}{\operatorname{IC}}
\newcommand{\SR}{\operatorname{SR}}
\newcommand{\DSR}{\operatorname{DSR}}
\newcommand{\HHI}{\operatorname{HHI}}
\newcommand{\SHAP}{\operatorname{SHAP}}
\newcommand{\bGamma}{\boldsymbol{\Gamma}}
\newcommand{\loss}{\mathcal{L}}
\newcommand{\by}{\mathbf{y}}
\newcommand{\bX}{\mathbf{X}}
\newcommand{\bbeta}{\bm{\beta}}

% ── TikZ Styles ──
\tikzset{
  obs/.style={circle, draw, fill=gray!30, minimum size=1cm, inner sep=0pt},
  latent/.style={circle, draw, minimum size=1cm, inner sep=0pt},
  param/.style={rectangle, draw, fill=black, text=white, minimum size=0.7cm, inner sep=2pt},
  plate/.style={draw, rectangle, rounded corners, inner sep=12pt, dashed},
  arrow/.style={-{Stealth[length=2.5mm]}, thick},
  block/.style={draw, rounded corners, minimum height=1cm, minimum width=1.6cm, align=center, font=\small},
  flowblock/.style={draw, rounded corners, minimum height=0.8cm, minimum width=2cm, align=center, font=\small, fill=blue!5},
  decisionblock/.style={draw, diamond, aspect=2, minimum height=0.8cm, align=center, font=\small, fill=orange!5},
}

% ── Header / Footer ──
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\chaptermark}[1]{\markboth{\MakeUppercase{\thechapter.\ #1}}{}}
\fancyhead[L]{\small\truncate{0.55\textwidth}{\leftmark}}
\fancyhead[R]{\small Risk as Alpha Learning Guide}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% ── Hyperref setup ──
\hypersetup{
  colorlinks=true,
  linkcolor=defblue,
  urlcolor=defblue,
  citecolor=defblue,
}
```

- [ ] **Step 3: Write main.tex**

Write this exact content to `ml-learning-guide/main.tex`:

```latex
\documentclass[11pt,a4paper]{report}
\input{preamble}

\begin{document}

% ── Title Page ──
\begin{titlepage}
\centering
\vspace*{3cm}
{\Huge\bfseries Risk as Alpha\\[0.4cm]
ML for Cross-Asset Signal Discovery\par}
\vspace{1.5cm}
{\Large A Learning Guide for the\\[0.3cm]
SecDB Signal Discovery Project\par}
\vspace{1cm}
{\Large Ryan Vincent\par}
\vspace{1.5cm}
{\normalsize
This document teaches the theory, methods, and methodology needed to\\
execute and defend the Risk-as-Alpha internship project.\\[0.5cm]
\textbf{Part I} covers foundations: asset pricing, risk systems, ML methods.\\
\textbf{Part II} covers applied methodology: features, validation, backtesting.\\[0.5cm]
Every chapter connects to a specific project phase.\par}
\vfill
{\small Last compiled: \today\par}
\end{titlepage}

% ── Table of Contents ──
\tableofcontents
\newpage

% ══════════════════════════════════════════════════════════════
% Part I — Foundations
% ══════════════════════════════════════════════════════════════

\part{Foundations}

\input{chapters/01-asset-pricing-foundations}
\input{chapters/02-intermediary-asset-pricing}
\input{chapters/03-risk-systems-var}
\input{chapters/04-market-microstructure}
\input{chapters/05-regularized-linear-models}
\input{chapters/06-tree-methods-finance}
\input{chapters/07-model-interpretation}
\input{chapters/08-panel-econometrics}

% ══════════════════════════════════════════════════════════════
% Part II — Applied Methodology
% ══════════════════════════════════════════════════════════════

\part{Applied Methodology}

\input{chapters/09-feature-engineering}
\input{chapters/10-labeling-targets}
\input{chapters/11-validation-frameworks}
\input{chapters/12-backtesting-methodology}
\input{chapters/13-regime-modeling}
\input{chapters/14-presenting-research}

\end{document}
```

- [ ] **Step 4: Create placeholder chapter files**

Create placeholder .tex files for all 14 chapters so the document structure compiles. Each must contain the chapter command and label:

```bash
declare -A chapters=(
  ["01-asset-pricing-foundations"]="Asset Pricing Foundations|asset-pricing"
  ["02-intermediary-asset-pricing"]="Intermediary Asset Pricing|intermediary"
  ["03-risk-systems-var"]="Risk Systems and Value-at-Risk|risk-systems"
  ["04-market-microstructure"]="Market Microstructure and Dealer Positioning|microstructure"
  ["05-regularized-linear-models"]="Regularized Linear Models|regularized"
  ["06-tree-methods-finance"]="Tree-Based Methods for Finance|trees"
  ["07-model-interpretation"]="Model Interpretation|interpretation"
  ["08-panel-econometrics"]="Panel Econometrics|panel"
  ["09-feature-engineering"]="Feature Engineering from Risk Systems|features"
  ["10-labeling-targets"]="Labeling and Target Construction|labeling"
  ["11-validation-frameworks"]="Validation Frameworks|validation"
  ["12-backtesting-methodology"]="Backtesting Methodology|backtesting"
  ["13-regime-modeling"]="Regime Modeling|regimes"
  ["14-presenting-research"]="Presenting Quantitative Research|presenting"
)
for f in "${!chapters[@]}"; do
  IFS='|' read -r title label <<< "${chapters[$f]}"
  printf '\\chapter{%s}\n\\label{ch:%s}\n\n%% TODO: Write this chapter\n' "$title" "$label" > "ml-learning-guide/chapters/$f.tex"
done
```

- [ ] **Step 5: Test compilation**

```bash
cd ml-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

Expected: compiles with warnings about empty chapters but no errors. Produces main.pdf with title page and TOC.

- [ ] **Step 6: Commit**

```bash
git add ml-learning-guide/
git commit -m "feat: learning guide infrastructure — preamble, main.tex, chapter placeholders"
```

---

## Chunk 2: Common Chapter Workflow + Wave 1 Chapters

### Common Chapter-Writing Workflow

Every chapter-writing subagent follows this exact workflow. The per-chapter tasks below specify only the chapter-specific content (topics, papers, structure). The workflow is the same for all.

**Subagent workflow (per chapter):**

1. **Research phase:** Use WebSearch and WebFetch to download or fetch abstracts/key sections of papers listed for that chapter. Extract the specific statistics, theorems, and results needed. Store these findings for reference while writing.

2. **Writing phase:** Write the full chapter `.tex` file following this mandatory structure:
   - `\chapter{Title}` and `\label{ch:label}`
   - `\begin{projectconnection}[...]` box (always first) — ties to project phase
   - Introduction (2-3 sentences)
   - Numbered sections, each containing as appropriate:
     - `definition` boxes for formal concepts
     - `prereq` boxes for background (use aggressively — reader has strong math, no finance)
     - `keyidea` boxes for core insights
     - `intuition` boxes for plain-English understanding
     - `warning` boxes for common pitfalls
     - `keyresult` boxes for paper findings (with actual reported statistics)
     - `workedexample` boxes for numerical walk-throughs
     - Term-by-term explanation after every equation
     - TikZ diagrams where they clarify
   - Summary section (8-15 bullet points)
   - Key Results recap table (paper → result → project relevance)

3. **Review phase:** Dispatch 3 sequential review subagents:

   **Pass 1 — Factual Accuracy:** "Review this LaTeX chapter for factual accuracy. Check every `keyresult` box against the paper it cites. Verify all formulas against standard references. Confirm worked examples produce correct numerical results. Flag any claim without a source. Return a numbered list of corrections needed."

   **Pass 2 — Brevity:** "Review this LaTeX chapter for brevity. Identify: (a) sentences that repeat earlier information, (b) throat-clearing phrases, (c) multi-sentence explanations collapsible to one sentence, (d) prereq boxes exceeding 5-10 lines, (e) any paragraph that doesn't help the reader execute or defend the project. Return a numbered list of cuts."

   **Pass 3 — Clarity:** "Review this LaTeX chapter for clarity. The reader has strong math/stats but NO finance background. Identify: (a) topics needing a TikZ diagram, (b) concept jumps that need a bridging sentence or prereq box, (c) worked examples needing more intermediate steps, (d) intuition boxes that are just restatements rather than genuine insight. Return a numbered list of improvements."

4. **Finalize:** Apply all corrections from the 3 passes. Write the final `.tex` file.

**Writing conventions (all chapters):**
- Concise: if sayable in 1 sentence, use 1
- Concrete examples with actual numbers — no hand-waving
- Term-by-term explanation after every equation (bulleted list)
- Cross-reference other chapters with `\ref{}` — don't repeat content
- Every claim sourced to a specific paper; mark uncertain claims with `[VERIFY]`
- Tone: direct, confident, slightly informal; address reader as "you"
- No padding prose — every sentence earns its place
- Target length per chapter: 15-25 pages (roughly 500-900 lines of LaTeX)

---

### Task 2: Chapter 1 — Asset Pricing Foundations

**File:** `ml-learning-guide/chapters/01-asset-pricing-foundations.tex`

**Papers to fetch and reference:**
- Cochrane (2005) "Asset Pricing" — Chapter 1 (SDF basics), Chapter 6 (factor models)
- Fama & French (1993) "Common risk factors in the returns on stocks and bonds" — the 3-factor model
- Sharpe (1964) "Capital Asset Prices" — original CAPM
- Ross (1976) "The Arbitrage Theory of Capital Asset Pricing" — APT

**Sections to write:**

1. **Project Connection box:** "This chapter provides the theoretical foundation for why risk signals should predict returns. Understanding the SDF framework is essential for framing your project thesis (Phase 0 pitch) and interpreting results (Phase 5 presentation). Every feature you engineer in Phase 2 is, at its core, a proxy for a component of the pricing kernel."

2. **Section: The Stochastic Discount Factor**
   - Definition: SDF $\SDF$ as a random variable that prices all assets: $\E[\SDF \cdot R_i] = 1$
   - Term-by-term explanation
   - Intuition box: "The SDF is a single number that tells you how much the market 'dislikes' each state of the world. States where you're already losing money get high SDF values — so assets that pay off in those states are valuable."
   - No-arbitrage ↔ existence of positive SDF (fundamental theorem of asset pricing)
   - Prereq box: conditional expectation, law of one price

3. **Section: Risk Premia**
   - Why expected returns differ across assets: $\E[R_i] - R_f = -\text{Cov}(\SDF, R_i) / \E[\SDF]$
   - Term-by-term explanation
   - Worked example: two assets, one that pays in recessions, one that pays in booms — show which has higher expected return and why
   - Key idea: returns are compensation for bearing risk the market dislikes

4. **Section: Factor Models**
   - CAPM: $\E[R_i] - R_f = \beta_i (\E[R_m] - R_f)$
   - Fama-French 3-factor: market, size (SMB), value (HML)
   - APT: multiple factors, no assumption about which factors
   - Prereq box: linear regression, OLS, $R^2$
   - Key Result box: Fama-French (1993) — 3 factors explain cross-section of stock returns much better than CAPM alone
   - Comparison table: CAPM vs. Fama-French vs. APT (assumptions, factors, testability)

5. **Section: Alpha, Beta, and Information Ratio**
   - Definition boxes for each term
   - Alpha as the intercept in a factor regression — return unexplained by known factors
   - Information ratio: $\text{IR} = \alpha / \sigma(\epsilon)$
   - Warning box: "Alpha is always relative to a factor model. A strategy has alpha relative to CAPM but might have zero alpha relative to Fama-French. Always specify the benchmark."

6. **Section: Cross-Sectional vs. Time-Series Tests**
   - Cross-sectional: do expected returns line up with betas? (Fama-MacBeth)
   - Time-series: does an asset's beta explain its return over time?
   - Why this distinction matters for the project (you're doing time-series prediction)

7. **Summary** (8-15 bullets)
8. **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 3: Chapter 3 — Risk Systems and Value-at-Risk

**File:** `ml-learning-guide/chapters/03-risk-systems-var.tex`

**Papers to fetch and reference:**
- Jorion (2006) "Value at Risk" — standard reference for VaR computation methods
- Basel Committee (2019) "Minimum capital requirements for market risk" — FRTB framework
- McNeil, Frey, Embrechts (2015) "Quantitative Risk Management" — component VaR, factor decomposition

**Sections to write:**

1. **Project Connection box:** "This chapter teaches you what every SecDB risk output actually measures. In Phase 0 you'll audit which risk cube nodes are accessible; this chapter ensures you understand the data before engineering features. In Phase 2, every feature family (VaR dynamics, factor concentration, scenario P&L, VaR utilization) maps directly to concepts here."

2. **Section: What VaR Measures**
   - Definition: $\VaR_\alpha$ as the loss threshold at confidence level $\alpha$ over horizon $h$
   - $\Pr(L > \VaR_\alpha) = 1 - \alpha$
   - Term-by-term explanation
   - Worked example: portfolio with normal P&L, compute 99% 1-day VaR
   - Intuition box: "VaR answers: 'What's the most I could lose on a normal bad day?' The 99% VaR says 'On 99 out of 100 days, my loss will be less than this number.'"
   - Prereq box: quantiles of a distribution, normal distribution properties

3. **Section: VaR Computation Methods**
   - Historical simulation: re-price portfolio under past scenarios
   - Parametric (variance-covariance): assume normal returns, use portfolio variance
   - Monte Carlo: simulate thousands of scenarios from a fitted model
   - Comparison table: accuracy, speed, assumptions, limitations of each
   - Warning box: "Historical sim VaR has a cliff: if the lookback window is 500 days, the 99% VaR is the 5th-worst day. Add or remove one extreme day and VaR jumps discontinuously. This creates spurious features if not handled."

4. **Section: Component VaR and Marginal VaR**
   - Component VaR: how much each position contributes to total VaR
   - $\text{CVaR}_i = w_i \cdot \frac{\partial \VaR}{\partial w_i}$
   - Property: component VaRs sum to total VaR (Euler decomposition)
   - Worked example: 3-asset portfolio, compute component VaR for each

5. **Section: Factor-VaR Decomposition**
   - Factor model for returns: $r_p = \sum_k \beta_k f_k + \epsilon$
   - Factor-VaR: which risk factors (rates, credit, equity, FX) drive the total VaR
   - Herfindahl index on factor shares as a concentration metric
   - Key idea: low HHI = diversified risk; high HHI = concentrated in one factor = hidden crowding

6. **Section: Scenario Analysis and Stress Testing**
   - Standard stress scenarios: what-if P&L under specified market moves
   - Scenario P&L rank: which scenario is worst for the portfolio
   - Dispersion across scenarios: high dispersion = sensitive to shock direction
   - Historical vs. hypothetical scenarios

7. **Section: VaR Utilization**
   - Definition: VaR usage as percentage of risk limit
   - Why this is the constraint that matters for intermediary asset pricing
   - When utilization hits limits → forced deleveraging → fire sales (Coval-Stafford channel)

8. **Section: Risk-Model Methodology Changes**
   - Historical sim → Monte Carlo transitions
   - Window-length changes
   - Why these create spurious features (VaR jumps not from market moves but from model changes)
   - Warning box: "If VaR methodology changed during your lookback period, your VaR features will have structural breaks. Interview the risk team about dates of methodology changes — document in the data audit."

9. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 4: Chapter 5 — Regularized Linear Models

**File:** `ml-learning-guide/chapters/05-regularized-linear-models.tex`

**Papers to fetch and reference:**
- Kozak, Nagel, Santosh (2020) "Shrinking the Cross-Section" JFE — ridge on PCs matches nonlinear ML
- Hastie, Tibshirani, Friedman "Elements of Statistical Learning" — Ch. 3 (ridge/lasso theory)
- Hoerl & Kennard (1970) "Ridge Regression" — original ridge paper

**Sections to write:**

1. **Project Connection box:** "Ridge regression is your baseline model throughout the project. In Phase 1 you build a ridge baseline that appears on every chart in Phases 2-5. If LightGBM doesn't beat ridge on identical features, you haven't learned anything nonlinear — Kozak-Nagel-Santosh (2020) showed ridge on PCs matches nonlinear ML for SDF estimation. This chapter teaches why."

2. **Section: Ridge Regression**
   - Objective: $\min_\bbeta \| \by - \bX\bbeta \|^2 + \lambda \|\bbeta\|^2$
   - Closed-form: $\hat{\bbeta} = (\bX^\top\bX + \lambda \mathbf{I})^{-1}\bX^\top\by$
   - Term-by-term explanation
   - Prereq box: matrix calculus, positive definite matrices
   - Bias-variance tradeoff: $\lambda$ increases bias, decreases variance
   - Worked example: 2-feature regression, show how ridge shrinks coefficients toward zero
   - TikZ diagram: contour plot of OLS loss + circular L2 constraint showing how the optimum differs from OLS

3. **Section: Lasso Regression**
   - Objective: $\min_\bbeta \| \by - \bX\bbeta \|^2 + \lambda \|\bbeta\|_1$
   - No closed form — requires coordinate descent or LARS
   - Why L1 produces sparsity: diamond constraint touches axes
   - Comparison table: ridge vs. lasso (sparsity, uniqueness, correlated features, closed form)
   - Prereq box: L1 vs. L2 norms geometrically

4. **Section: Elastic Net**
   - Combines L1 and L2: $\lambda_1 \|\bbeta\|_1 + \lambda_2 \|\bbeta\|^2$
   - When to use: correlated features where lasso picks one arbitrarily

5. **Section: Ridge on Principal Components**
   - Key Result box: Kozak-Nagel-Santosh (2020) — "ridge on PCs of asset returns matches or beats nonlinear ML methods (random forests, neural networks) for SDF estimation across 50 anomaly portfolios. The cross-section of expected returns is approximately linear in a few dominant PCs."
   - Why this matters: if the signal is linear, adding nonlinear ML is overfitting
   - Implication for your project: ridge is the bar that LightGBM must clear

6. **Section: Regularization Path and Alpha Selection**
   - Cross-validation for $\lambda$: leave-one-out shortcut for ridge (GCV)
   - Regularization path plot
   - Prereq box: cross-validation basics (will be expanded in Ch. 11 for purged CV)

7. **Section: Why Ridge is the Baseline in Finance**
   - Finance's low signal-to-noise regime: $R^2$ of 0.01-0.05 is typical for return prediction
   - Key idea: "If GBM doesn't beat ridge, you haven't learned nonlinear interactions — you've just overfit noise."
   - Warning box: "Many published ML results in finance don't report a ridge baseline. Without it, you can't distinguish genuine nonlinear signal from overfitting."

8. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 5: Chapter 8 — Panel Econometrics

**File:** `ml-learning-guide/chapters/08-panel-econometrics.tex`

**Papers to fetch and reference:**
- Petersen (2009) "Estimating Standard Errors in Finance Panel Data Sets" RFS — clustered SEs
- Fama & MacBeth (1973) "Risk, Return, and Equilibrium: Empirical Tests" — two-pass regression
- He, Kelly, Manela (2017) "Intermediary Asset Pricing: New Evidence from Many Asset Classes" JFE
- Wooldridge (2010) "Econometric Analysis of Cross Section and Panel Data" — FE/RE theory

**Sections to write:**

1. **Project Connection box:** "In Phase 4A you move from firm-level aggregates to asset-class-level risk outputs and test within-class vs. cross-class prediction using panel data. This chapter teaches the econometric methods needed: fixed effects, clustered standard errors, and Fama-MacBeth regressions. The panel structure is also how you increase your effective sample size — a critical concern when firm-level VaR gives only ~1,250 daily observations."

2. **Section: Why Panel Data**
   - Definition: panel = multiple entities (asset classes) observed over time
   - Advantage: more observations, can control for unobserved entity-specific effects
   - Your data: (date × asset_class) with asset-class-specific risk outputs and returns

3. **Section: Fixed Effects**
   - Definition: $y_{it} = \alpha_i + \bx_{it}'\bbeta + \epsilon_{it}$
   - Each entity gets its own intercept $\alpha_i$
   - Within-estimator: demean by entity, then OLS
   - Prereq box: dummy variables, degrees of freedom
   - Worked example: 4 asset classes × 252 days, fit FE model

4. **Section: Random Effects and the Hausman Test**
   - RE assumption: $\alpha_i$ uncorrelated with regressors
   - Hausman test: if rejected, use FE
   - Intuition box: "FE says 'I don't care why asset classes differ in levels, I just want to control for it.' RE says 'the differences are random draws from a distribution.' If the asset-class-specific effects correlate with your features — which is likely in finance — FE is safer."

5. **Section: Clustered Standard Errors**
   - Key Result box: Petersen (2009) — "Finance panels have both cross-sectional correlation (all assets move together on crisis days) and time-series correlation (individual assets are autocorrelated). Standard errors that ignore this are 3-7x too small. Cluster by time for cross-sectional correlation, by entity for serial correlation, or double-cluster for both."
   - Worked example: show how unclustered vs. clustered SEs differ on a small panel
   - Warning box: "Unclustered standard errors in finance panels produce t-statistics that are too large by a factor of 3-7x. Never report unclustered SEs from a panel regression."

6. **Section: Fama-MacBeth Regressions**
   - Two-pass procedure: (1) cross-sectional regression at each date, (2) average coefficients over time
   - Standard errors from time-series variation of the cross-sectional estimates
   - Naturally handles cross-sectional correlation (each regression is a single date)
   - When to use FM vs. FE: FM for pricing tests, FE for prediction

7. **Section: Panel ML vs. Panel Regression**
   - Complementary tools: panel regression gives interpretable coefficients with proper SEs; ML gives flexible predictions
   - Your project uses both: panel FE for the He-Kelly-Manela test (Phase 4A), LightGBM with asset-class dummy features for prediction

8. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 6: Chapter 10 — Labeling and Target Construction

**File:** `ml-learning-guide/chapters/10-labeling-targets.tex`

**Papers to fetch and reference:**
- Lopez de Prado (2018) "Advances in Financial Machine Learning" — Ch. 3 (triple-barrier), Ch. 3.6 (meta-labeling)
- Adrian & Shin (2010) "Liquidity and Leverage" — dealer repos forecast VIX innovations

**Sections to write:**

1. **Project Connection box:** "In Phase 1 you build the label construction module (Task 6 in the implementation plan). The choice of label is as important as the choice of features — the label IS your hypothesis. Triple-barrier labeling with volatility-scaled thresholds is the primary labeling method; meta-labeling adds a precision filter. Your prediction targets (VIX innovations, realized vol, drawdowns) come from the theoretical foundations in Chapters 1-2."

2. **Section: Why Labeling Matters**
   - The label defines what you're predicting — it encodes your hypothesis
   - Standard return labels (1d, 5d, 21d): simple, interpretable, but noisy and path-dependent
   - Fixed thresholds fail across asset classes (equity moves ≠ FX moves ≠ rates moves)

3. **Section: Triple-Barrier Labeling**
   - Three barriers: upper (profit-taking), lower (stop-loss), vertical (time)
   - Volatility-scaled thresholds: multiply barrier width by rolling volatility
   - Label = which barrier was hit first: +1 (upper), -1 (lower), 0 (vertical with ~zero return)
   - TikZ diagram: price path with 3 barriers drawn, showing which barrier is hit
   - Worked example: price path of 10 daily observations, $\sigma_{rolling}$ = 1%, profit-taking multiplier = 2, stop-loss multiplier = 2, max holding = 5 days — step through label assignment
   - Key idea: "Triple-barrier labeling aligns the label with how a trading strategy would actually behave — it acknowledges that real trades have stops and take-profit levels."

4. **Section: Meta-Labeling**
   - Primary model predicts side (+1 or -1)
   - Secondary model predicts whether the primary model is correct (0 or 1) — this is the meta-label
   - Precision-recall tradeoff: the primary model has high recall (catches many opportunities), meta-labeling adds precision (filters out bad ones)
   - Betting size: the meta-model's probability output becomes the position size
   - Warning box: "Meta-labeling requires a reasonable primary model. If the primary model is random, meta-labeling has nothing to filter."

5. **Section: Label Uniqueness and Concurrency**
   - When labels overlap in time, they create sample dependence
   - Uniqueness: what fraction of the label's return window is non-overlapping?
   - Average uniqueness per label — used for sample weighting in training
   - Prereq box: why i.i.d. assumptions fail for overlapping time-series labels

6. **Section: Prediction Targets for the Project**
   - VIX innovations: $\Delta \text{VIX}_t = \text{VIX}_{t+h} - \text{VIX}_t$. Adrian-Shin (2010) shows dealer repos forecast this.
   - Realized volatility: $\text{RV}_t = \sqrt{\sum_{i=1}^{n} r_{t,i}^2}$. Higher SNR than returns.
   - Drawdowns in most-concentrated asset class: if factor concentration high in rates, do rates draw down next?
   - Cross-asset momentum reversals: does VaR utilization spike predict mean-reversion in crowded factors?
   - Key idea: "Start with VIX innovations (cleanest single target per Adrian-Shin) and realized vol (higher SNR). Narrow based on evidence."

7. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 7: Chapter 11 — Validation Frameworks

**File:** `ml-learning-guide/chapters/11-validation-frameworks.tex`

**Papers to fetch and reference:**
- Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio" — DSR formula and derivation
- Harvey & Liu (2015) "Backtesting" — Haircut Sharpe methodology
- Harvey, Liu, Zhu (2016) "...and the Cross-Section of Expected Returns" RFS — t > 3 hurdle
- Bailey, Borwein, Lopez de Prado, Zhu (2014) "Pseudo-Mathematics and Financial Charlatanism" — Probability of Backtest Overfitting
- Lopez de Prado (2018) AFML — Ch. 7 (purged K-fold CV), Ch. 12 (CPCV)

**Sections to write:**

1. **Project Connection box:** "This chapter is the validation stack from Phase 1 (Task 7 in the implementation plan). Every number in your project runs through this gauntlet: purged CV, DSR, CPCV, ridge baseline. This is what separates credible work from 'intern ran a GBM.' Master this chapter and you can defend your results against any methodological challenge."

2. **Section: Why Standard K-Fold CV Fails for Time Series**
   - Standard K-fold: randomly partition data into K folds
   - Problem: temporal autocorrelation means train/test aren't independent
   - A model trained on January and March, tested on February, leaks information
   - TikZ diagram: timeline showing how standard CV creates train-test leakage

3. **Section: Purged K-Fold CV with Embargo**
   - Purging: if a test observation's label window overlaps with any training observation, remove that training observation
   - Embargo: additional buffer after the test period — no training observations within embargo_pct of sample size after the test end
   - TikZ diagram: 5 folds on a timeline, showing purged and embargoed regions shaded out
   - Worked example: 1,250 daily observations, K=5, embargo=2% (25 days). Walk through which observations are removed from training when testing fold 3.
   - Warning box: "Even with purging, if your features have long memory (e.g., 21-day rolling statistics), the embargo must be at least as long as the longest feature lookback window."

4. **Section: Combinatorial Purged CV (CPCV)**
   - Problem CPCV solves: standard K-fold gives K Sharpe estimates; with only K=5, the distribution is too thin to draw conclusions
   - CPCV: partition into N groups, choose k as test → C(N,k) combinations → C(N,k) × (backtest paths) Sharpe estimates
   - Worked example: N=6, k=2 → C(6,2)=15 paths. Show how one combination is constructed.
   - Key idea: "CPCV gives you a distribution of Sharpe ratios from a single history. If the median is positive but the 5th percentile is negative, your signal is fragile."

5. **Section: Deflated Sharpe Ratio**
   - The problem: you tried 30 feature sets; the best has Sharpe 1.2. Is it real?
   - Expected maximum Sharpe under the null: $\E[\max(\SR)] \approx \sqrt{2 \ln N}$ for N independent trials (simplified)
   - Full DSR formula: $\DSR = \Phi\left(\frac{\hat{\SR} - \E[\max(\SR_0)]}{\hat{\sigma}(\SR)}\right)$
   - Term-by-term explanation
   - Adjustments for non-normal returns: skewness and kurtosis terms in $\hat{\sigma}(\SR)$
   - $\hat{\sigma}(\SR) = \sqrt{\frac{1 - \hat{\gamma}_3 \hat{\SR} + \frac{\hat{\gamma}_4 - 1}{4} \hat{\SR}^2}{T}}$
   - Worked example: Sharpe=1.2, 30 trials, T=1250, skewness=-0.5, kurtosis=4. Compute DSR step by step.
   - Key Result box: Bailey-Lopez de Prado (2014) — "With 45 independent trials on 5 years of daily data, the expected maximum Sharpe under the null is ~1.87. A reported Sharpe of 1.0 has DSR ≈ 0.02 — almost certainly noise."
   - Warning box: "Every experiment you run counts as a trial, even the failures. If you don't log failed experiments, your DSR is dishonestly high."

6. **Section: Haircut Sharpe**
   - Multiple-testing corrections applied to the Sharpe ratio
   - Bonferroni: $\alpha_{adj} = \alpha / N$ — most conservative
   - Holm step-down: sequential rejection, less conservative
   - BHY-FDR (Benjamini-Hochberg-Yekutieli): controls false discovery rate
   - Worked example: Sharpe=1.5, 20 tests. Show the adjusted Sharpe under all three methods.
   - Key Result box: Harvey-Liu (2015) — provides the framework; Harvey-Liu-Zhu (2016) — "Given the hundreds of factors published in finance, a new factor needs t > 3.0 to be credible."

7. **Section: Probability of Backtest Overfitting (PBO)**
   - Use CPCV paths: what fraction of paths have negative OOS Sharpe when the IS Sharpe was positive?
   - PBO = fraction of paths that overfit
   - If PBO > 50%, the backtest is more likely overfit than not

8. **Section: Experiment Tracking for Honest DSR**
   - Every model configuration logged: features, target, model type, CV method, raw Sharpe, DSR
   - The total trial count is the input to DSR — honest tracking is not optional
   - Key idea: "The experiment log is as important as the model code. Without it, you cannot compute an honest DSR."

9. **Section: The Sample-Size Problem**
   - 5 years daily firm-level VaR = ~1,250 rows
   - Bailey et al.: ~45 independent trials exhaust Sharpe of 1.0 on this data
   - Mitigation: panel structure (multiple asset classes × time), theory-motivated features (fewer tests), pre-registration of hypotheses

10. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 8: Chapter 13 — Regime Modeling

**File:** `ml-learning-guide/chapters/13-regime-modeling.tex`

**Papers to fetch and reference:**
- Asness, Chandra, Ilmanen, Israel (2017) "Contrarian Factor Timing is Deceptively Difficult" — factor timing caveat
- Hamilton (1989) "A New Approach to the Economic Analysis of Nonstationary Time Series" — Markov-switching
- Dempster, Laird, Rubin (1977) "Maximum Likelihood from Incomplete Data via the EM Algorithm" — EM for GMM

**Sections to write:**

1. **Project Connection box:** "In Phase 4A (Task 17), you fit a GMM on macro features to classify market regimes and decompose your signal's performance by regime. This chapter teaches GMM regime classification, the Two Sigma template, and — critically — the Asness et al. caveat on why regime-conditional strategies often disappoint."

2. **Section: Why Regime-Awareness**
   - Signals that work in steady state may fail in crisis
   - Regime decomposition: is your signal's Sharpe driven by one regime or broad?
   - If one regime only → fragile; if broad → robust

3. **Section: GMM for Regime Classification**
   - Gaussian Mixture Model: $p(\bx) = \sum_{k=1}^K \pi_k \N(\bx | \bm{\mu}_k, \bm{\Sigma}_k)$
   - Term-by-term explanation
   - EM algorithm: E-step (assign soft labels), M-step (update parameters)
   - Model selection: BIC for number of components
   - Feature choice for macro regimes: VIX, credit spread, term slope, USD, realized cross-asset correlation
   - Worked example: 2D GMM with VIX and credit spread, 3 components. Show one EM iteration.
   - Prereq box: multivariate Gaussian, mixture models

4. **Section: Two Sigma Regime Template**
   - 4 regimes: Crisis, Steady State, Inflation, Walking on Ice
   - Characterize each by macro feature ranges
   - Regime-conditional Sharpe: compute Sharpe for each regime separately

5. **Section: ADWIN for Concept Drift Detection**
   - Adaptive Windowing: maintains two sub-windows, detects when their means differ significantly
   - Use on prediction errors: if error distribution shifts → regime change
   - Can trigger model retraining

6. **Section: Markov-Switching Models**
   - Hamilton (1989): hidden Markov model for economic regimes
   - Transition probabilities: $\Pr(s_t = j | s_{t-1} = i)$
   - Comparison table: GMM vs. Markov-switching (temporal structure, estimation, complexity)
   - Key idea: "GMM treats each observation independently; Markov-switching models regime persistence. For your project, GMM is simpler and sufficient — but know Markov-switching exists."

7. **Section: The Factor Timing Caveat**
   - Key Result box: Asness et al. (2017) — "Contrarian factor timing (buying factors after drawdowns) is 'deceptively difficult.' Net of existing factor exposures, timing strategies often subtract value. Timing that looks profitable in-sample typically reflects inadvertent factor exposure, not genuine timing skill."
   - Implication: if you condition on regime, document honestly whether the conditional strategy outperforms the unconditional one after accounting for what you already hold
   - Warning box: "Regime-conditional strategies look better in backtests than they are in practice. The regime is only known with certainty in hindsight. Your GMM assigns probabilities, not labels — account for classification uncertainty."

8. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

## Chunk 3: Wave 2 Chapters

Wave 2 chapters depend on Wave 1 chapters. Each agent is given the completed .tex files of its dependency chapters so it can: (1) use `\ref{}` to cross-reference existing labels, (2) avoid re-explaining concepts already taught, and (3) maintain consistent notation.

### Task 9: Chapter 2 — Intermediary Asset Pricing

**File:** `ml-learning-guide/chapters/02-intermediary-asset-pricing.tex`
**Depends on:** Chapter 1 (SDF framework, factor models, alpha/beta definitions)

**Papers to fetch and reference:**
- He & Krishnamurthy (2013) "Intermediary Asset Pricing" AER
- Adrian, Etula, Muir (2014) "Financial Intermediaries and the Cross-Section of Asset Returns" JF
- He, Kelly, Manela (2017) "Intermediary Asset Pricing: New Evidence from Many Asset Classes" JFE
- Adrian & Shin (2010) "Liquidity and Leverage" JFI
- Adrian & Brunnermeier (2016) "CoVaR" AER

**Sections to write:**

1. **Project Connection box:** "This IS the core thesis of your project. Every feature you engineer in Phase 2 is a proxy for the intermediary constraints described here. He-Krishnamurthy predicts that dealer capital constraints drive risk premia; Adrian-Etula-Muir shows a single intermediary-leverage factor prices the cross-section with R²=77%; He-Kelly-Manela extends this across all asset classes. Your project tests this theory with proprietary daily data — the data the academics wished they had."

2. **Section: Classical vs. Intermediary Asset Pricing**
   - Classical: representative household's SDF prices all assets (Ch. 1 framework)
   - Problem: household consumption is too smooth to explain return volatility ("equity premium puzzle")
   - Intermediary approach: dealers/financial intermediaries are the marginal investors; their constraints drive prices
   - Key idea: "When dealers are constrained (high VaR utilization, capital losses), they pull back from risk-taking. This raises risk premia on the assets they step back from."

3. **Section: He-Krishnamurthy (2013)**
   - Model: intermediary with equity capital manages household savings; capital constraint $W_t \geq \underline{W}$
   - When capital is ample: intermediary SDF ≈ household SDF; prices close to fundamentals
   - When capital is scarce: intermediary's marginal utility spikes; risk premia rise sharply
   - The intermediary capital ratio as a state variable
   - Key Result box: exact result from paper (fetch and cite)
   - Intuition box: "Think of the dealer as a fire department. When they have capacity, they suppress fires (price shocks) and markets stay calm. When they're stretched thin, fires burn unchecked and risk premia explode."

4. **Section: Adrian-Etula-Muir (2014)**
   - Single-factor model: intermediary leverage growth as the SDF factor
   - Key Result box: "A single factor — broker-dealer leverage growth — prices the cross-section of 25 equity portfolios (size × value) with R² = 77%, vs. 24% for CAPM and 73% for Fama-French 3-factor. The leverage factor subsumes the market factor."
   - Why leverage works: it captures the state of dealer balance-sheet constraints
   - Data source: aggregate broker-dealer leverage from Fed Flow of Funds (Z.1), quarterly

5. **Section: He-Kelly-Manela (2017)**
   - Extension: does the intermediary pricing kernel span ALL asset classes?
   - Key Result box: "Using the capital ratio of primary dealers, a single intermediary factor prices equities, bonds, FX, commodities, credit, and options — 7 asset classes, 68 test portfolios. Pricing errors are economically small."
   - Implication for your project: if one factor works across all assets, your cross-asset panel approach (Phase 4A) is theoretically motivated

6. **Section: Adrian-Shin (2010)**
   - Dealer repos as a measure of balance-sheet expansion/contraction
   - Key Result box: "Growth in broker-dealer repos forecasts next-quarter VIX innovations." **[AGENT MUST EXTRACT EXACT COEFFICIENT FROM PAPER — check Table 2 or equivalent regression table in Adrian-Shin 2010]**
   - This is why VIX innovations are your cleanest prediction target

7. **Section: Adrian-Brunnermeier (2016): CoVaR**
   - CoVaR: VaR of the system conditional on one institution being in distress
   - $\Delta\text{CoVaR}$: contribution of an institution to systemic risk
   - Why this matters: your firm-level VaR features capture a version of this at the desk level

8. **Section: The Data Bottleneck — Why Your Project Has an Edge**
   - All academic work uses quarterly Fed Z.1 data (published with 2-month lag)
   - You have daily, cross-asset, correct-dealer-sign risk outputs from SecDB
   - This is the data the academics wished they had — your project tests the theory with real data
   - Warning box: "Having better data doesn't guarantee better results. The academics' quarterly data might be sufficient if the signal is low-frequency. Your advantage is testing whether higher-frequency data adds value."

9. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX (cross-referencing Ch. 1 concepts via \ref{})**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 10: Chapter 4 — Market Microstructure and Dealer Positioning

**File:** `ml-learning-guide/chapters/04-market-microstructure.tex`
**Depends on:** Chapter 3 (VaR, risk systems, component VaR)

**Papers to fetch and reference:**
- Coval & Stafford (2007) "Asset Fire Sales (and Purchases) in Equity Markets" JFE
- Baltussen, Da, Lammers, Martens (2021) "Hedging Demand and Market Intraday Momentum" JFE
- Barbon & Buraschi (2021) "Gamma Fragility"
- Ni, Pearson, Poteshman (2005) "Stock Price Clustering on Option Expiration Dates" JFE
- Muravyev, Pearson, Pollet (2022) — IVS/skew proxying borrow fees caveat

**Sections to write:**

1. **Project Connection box:** "This chapter teaches the mechanics of dealer positioning that create your features. VaR utilization and factor concentration (Phase 2, Project 1) reflect dealer constraints from Ch. 2's theory. Dealer Greeks — gamma, vanna, charm (Phase 4B, Project 2) — create mechanical hedging flows that move prices. Understanding these mechanics is necessary to engineer features that capture real economic signals rather than noise."

2. **Section: Dealer Balance Sheets**
   - How market-makers take and hold inventory
   - The link between inventory and VaR: holding inventory consumes risk capital
   - Prereq box: long vs. short positions, bid-ask spread

3. **Section: Delta Hedging**
   - Options dealers must hedge their delta exposure
   - $\Delta = \partial V / \partial S$: sensitivity of option value to underlying price
   - Delta hedging creates mechanical buying/selling of the underlying
   - Prereq box: what an option is, payoff diagrams, Black-Scholes basics (just the delta formula, not the full derivation)

4. **Section: Gamma and the Gamma-Flip Level**
   - $\Gamma = \partial^2 V / \partial S^2 = \partial \Delta / \partial S$
   - Net long gamma (dealer sold puts): stabilizing — as price drops, dealer buys more stock (rebalances delta upward)
   - Net short gamma (dealer sold calls): amplifying — as price drops, dealer sells more stock (rebalances delta downward)
   - Gamma-flip level: the price where aggregate dealer gamma crosses from positive to negative
   - TikZ diagram: dealer hedging flow under long-gamma vs. short-gamma, showing stabilizing vs. amplifying effect
   - Intuition box: "Long gamma dealers are shock absorbers — they buy dips and sell rallies. Short gamma dealers are shock amplifiers — they sell dips and buy rallies. The gamma-flip level is where the market switches from stable to fragile."

5. **Section: Higher-Order Greeks**
   - Vega ($\partial V / \partial \sigma$): sensitivity to implied vol — drives hedging when vol moves
   - Vanna ($\partial \Delta / \partial \sigma = \partial^2 V / \partial S \partial \sigma$): how delta changes with vol — drives hedging on FOMC/CPI days when vol jumps
   - Charm ($\partial \Delta / \partial t$): how delta changes with time — drives end-of-day flows as options decay
   - Key idea: "For your project, gamma is the primary feature (predicts intraday momentum). Vanna matters on event days. Charm matters at end-of-day."

6. **Section: Fire Sales — Coval-Stafford (2007)**
   - Key Result box: "Mutual funds experiencing large outflows are forced to sell their holdings, creating predictable price pressure and subsequent reversals." **[AGENT MUST EXTRACT EXACT RETURN MAGNITUDES FROM PAPER — check Tables 3-4 in Coval-Stafford 2007 for fire-sale return and reversal percentages]**
   - Mechanism: forced selling pushes prices below fundamental value; prices revert when selling pressure stops
   - Analogy to your project: when VaR utilization hits limits, dealers are forced to deleverage — same mechanism, different actors

7. **Section: Dealer Gamma and Intraday Momentum — Baltussen et al. (2021)**
   - Key Result box: "Aggregate net dealer gamma determines whether intraday returns in the last 30 minutes continue or reverse. When gamma is negative, intraday momentum persists (dealer hedging amplifies); when gamma is positive, momentum reverses (dealer hedging dampens)."
   - Why proprietary data is better: public GEX (gamma exposure) estimates use option open interest × Black-Scholes gamma — approximately 30% wrong on sign due to incomplete data on who holds which side

8. **Section: Caveats**
   - Muravyev-Pearson-Pollet (2022): IVS/skew partly proxy borrow fees; control for short interest
   - Barbon-Buraschi (2021): gamma fragility can flip quickly; yesterday's gamma sign may not apply today
   - Warning box: "Dealer gamma changes intraday as the underlying moves. A morning estimate may be stale by close. For Project 2, you need as-fresh-as-possible estimates from SecDB, not EOD snapshots."

9. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 11: Chapter 6 — Tree-Based Methods for Finance

**File:** `ml-learning-guide/chapters/06-tree-methods-finance.tex`
**Depends on:** Chapter 5 (ridge as baseline, bias-variance tradeoff, regularization)

**Papers to fetch and reference:**
- Gu, Kelly, Xiu (2020) "Empirical Asset Pricing via Machine Learning" RFS — the horse race
- Chen & Guestrin (2016) "XGBoost" — algorithm details
- Ke et al. (2017) "LightGBM" — histogram-based, leaf-wise, GOSS, EFB

**Sections to write:**

1. **Project Connection box:** "LightGBM is your primary model in Phase 2. This chapter teaches the algorithm, the hyperparameter choices specific to financial data, and the GKX evidence that tree methods are competitive with — and often beat — deep learning for tabular financial data. The key insight: aggressive regularization (low depth, high min_child_samples) is critical in finance's low-SNR regime."

2. **Section: Decision Trees**
   - CART: recursive binary splitting on features
   - Splitting criteria: MSE reduction (regression), Gini/entropy (classification)
   - Why single trees overfit: they memorize noise
   - Prereq box: information gain, Gini impurity

3. **Section: Random Forests**
   - Bagging + random feature subsets → decorrelated trees → lower variance
   - Out-of-bag error as built-in validation
   - Why forests are better than single trees but still limited

4. **Section: Gradient Boosting**
   - Functional gradient descent: each tree corrects the residuals of the ensemble
   - Learning rate shrinkage: $F_m(\bx) = F_{m-1}(\bx) + \eta \cdot h_m(\bx)$
   - Term-by-term explanation
   - Intuition box: "Boosting is like iterative refinement. The first tree captures the big patterns. Each subsequent tree focuses on what the ensemble still gets wrong. The learning rate controls how aggressively each new tree corrects."

5. **Section: LightGBM**
   - Histogram-based splitting: bin continuous features → faster split finding
   - Leaf-wise growth (vs. level-wise): grows the leaf with highest loss reduction → deeper, more targeted trees
   - GOSS (Gradient-based One-Side Sampling): keep all high-gradient samples, subsample low-gradient
   - EFB (Exclusive Feature Bundling): bundles mutually exclusive features to reduce dimensionality
   - Why LightGBM is preferred for financial data: speed (enables more CV iterations) and built-in regularization

6. **Section: XGBoost**
   - Level-wise growth: all leaves at same depth → more balanced trees
   - Exact vs. approximate split finding
   - Built-in L1/L2 regularization on leaf weights
   - Comparison table: LightGBM vs. XGBoost (splitting strategy, speed, regularization, use case)

7. **Section: Hyperparameters for Financial Data**
   - Low `max_depth` (3-5): prevents memorizing noise in low-SNR data
   - High `min_child_samples` (50-200): ensures each leaf has enough observations
   - `subsample` (0.6-0.8): reduces overfitting by using subset of data per tree
   - `colsample_bytree` (0.6-0.8): random feature subsets per tree (like RF)
   - `reg_alpha` and `reg_lambda`: L1/L2 regularization on leaf weights
   - `n_estimators` with early stopping: use validation loss to stop adding trees
   - Key idea: "In finance, the default LightGBM parameters overfit catastrophically. max_depth=3, min_child_samples=100, subsample=0.7 is a reasonable starting point."
   - Warning box: "Never use default LightGBM parameters on financial data. The defaults (max_depth=-1, min_child_samples=20) are designed for high-SNR problems like click prediction, not for return prediction with R²=0.01."

8. **Section: The GKX Horse Race**
   - Key Result box: Gu-Kelly-Xiu (2020) — "On a 60-year US equity panel (30,000+ stocks × 900+ months, 94 characteristics), gradient-boosted trees achieve OOS R² of [cite exact] for monthly returns, competitive with neural networks ([cite exact]) and substantially better than linear models ([cite exact]). Deep learning's advantage is marginal and comes with much higher computational cost and instability."
   - Implication: tree methods are the right default for your project — only consider deep learning if trees clearly fail

9. **Section: When Trees Fail**
   - Non-stationarity: trees trained on one regime may fail in another
   - Extrapolation: trees cannot predict outside the range of training data
   - Regime changes: abrupt shifts in data distribution degrade all ML methods, but trees are especially brittle at boundaries
   - Mitigation: rolling-window retraining, regime conditioning (Ch. 13)

10. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 12: Chapter 9 — Feature Engineering from Risk Systems (MOVED TO WAVE 3)

**NOTE:** Ch 9 depends on Ch 4 (Wave 2). Moved to Chunk 4, Task 12B. See Task 12B for full section content.

---

## Chunk 4: Waves 3-4 + Assembly

Wave 3 chapters depend on Wave 2 chapters. Ch 9 depends on both Ch 3 (Wave 1) and Ch 4 (Wave 2), so it runs here.

### Task 12B: Chapter 9 — Feature Engineering from Risk Systems

**File:** `ml-learning-guide/chapters/09-feature-engineering.tex`
**Depends on:** Chapter 3 (VaR, component VaR, factor decomposition — Wave 1), Chapter 4 (dealer Greeks — Wave 2)

**NOTE:** This task was originally in Chunk 3 (Wave 2) but Ch 9 depends on Ch 4 which is also Wave 2. Moved here to Wave 3 to respect the dependency. The section content is identical to the Task 12 definition in Chunk 3 — execute that specification here.

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX (using completed Ch 3 and Ch 4 .tex files for cross-references)**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 13: Chapter 7 — Model Interpretation

**File:** `ml-learning-guide/chapters/07-model-interpretation.tex`
**Depends on:** Chapter 6 (tree-based methods, LightGBM)

**Papers to fetch and reference:**
- Lundberg & Lee (2017) "A Unified Approach to Interpreting Model Predictions" NeurIPS — SHAP
- Lundberg et al. (2020) "From local explanations to global understanding with explainable AI for trees" — TreeSHAP details
- Breiman (2001) "Random Forests" — MDI and permutation importance (MDA)

**Sections to write:**

1. **Project Connection box:** "SHAP analysis appears throughout your project: in Phase 2 for identifying which feature families drive predictions, in Phase 3 for the checkpoint assessment (is feature importance stable?), and in Phase 5 for the presentation (SHAP waterfall plots convert 'trust me' into 'here's what drives this prediction'). MDI/MDA stability across CV folds is your test for whether importance rankings are reliable."

2. **Section: Why Interpretation Matters in Finance**
   - Regulatory and compliance: "black box" models face scrutiny
   - Trust: your sponsor needs to understand what drives predictions
   - Debugging: interpretation reveals when a model is using spurious features
   - Presentation: SHAP waterfalls are the most convincing chart in your arsenal

3. **Section: SHAP from Game Theory**
   - Shapley values: from cooperative game theory — fair allocation of total payoff among players
   - The 4 axioms: efficiency ($\sum_i \phi_i = f(\bx) - \E[f]$), symmetry, dummy, additivity
   - SHAP value for feature $j$: $\phi_j = \sum_{S \subseteq N \setminus \{j\}} \frac{|S|!(|N|-|S|-1)!}{|N|!} [f(S \cup \{j\}) - f(S)]$
   - Term-by-term explanation
   - Prereq box: cooperative games, marginal contribution
   - Worked example: 3-feature model, compute SHAP values by enumeration (8 coalitions)
   - Intuition box: "SHAP asks: 'For each prediction, how much did each feature contribute relative to the average prediction?' It's the only method that satisfies all four fairness axioms from game theory."

4. **Section: TreeSHAP**
   - Problem: exact SHAP requires $2^p$ evaluations for $p$ features — exponential
   - TreeSHAP: exact Shapley computation for tree ensembles in $O(TLD^2)$ time (T trees, L leaves, D depth)
   - Why it works: tree structure allows efficient path-based computation
   - Key Result box: Lundberg et al. — TreeSHAP gives exact (not approximate) Shapley values for tree ensembles, making it the gold standard for interpreting LightGBM/XGBoost.

5. **Section: SHAP Plots**
   - Summary plot: feature importance ranking + direction of effect (beeswarm)
   - Dependence plot: one feature vs. SHAP value, colored by interaction feature
   - Waterfall plot: breakdown of a single prediction into feature contributions
   - Force plot: horizontal version of waterfall
   - Key idea: "For your presentation (Phase 5), the waterfall plot is the money chart. Show the top 3 predictions and their feature breakdowns."

6. **Section: MDI vs. MDA**
   - MDI (Mean Decrease Impurity): average reduction in splitting criterion across all trees when splitting on feature $j$
   - MDA (Mean Decrease Accuracy / permutation importance): drop in performance when feature $j$ is randomly permuted
   - MDI is biased toward high-cardinality features; MDA is more reliable but slower
   - Comparison table: MDI vs. MDA (speed, bias, reliability, correlation handling)

7. **Section: Feature Importance Stability**
   - Compute MDA for each CV fold separately
   - If a feature ranks #1 in one fold and #10 in another → unstable → unreliable signal
   - Stability metric: rank correlation of feature importances across folds
   - Warning box: "If your top feature flips across CV folds, the model is fitting noise in different parts of the data. Drop unstable features — they hurt OOS performance."

8. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 14: Chapter 12 — Backtesting Methodology

**File:** `ml-learning-guide/chapters/12-backtesting-methodology.tex`
**Depends on:** Chapter 11 (validation frameworks, purged CV, DSR)

**Papers to fetch and reference:**
- McLean & Pontiff (2016) "Does Academic Research Destroy Stock Return Predictability?" RFS
- Lopez de Prado (2018) AFML — Ch. 14-15 on backtesting
- Bailey, Borwein, Lopez de Prado, Zhu (2014) — backtest overfitting

**Sections to write:**

1. **Project Connection box:** "This chapter covers the backtesting engine from Phase 1 (Task 8) and the walk-forward OOS test in Phase 5 (Task 22). Transaction-cost-aware P&L, turnover, and capacity estimation are 'what the trading floor asks about first' — the practical questions that determine whether a signal is tradeable."

2. **Section: Transaction-Cost-Aware P&L**
   - Gross P&L: $\text{PnL}_t = \hat{y}_t \cdot r_{t+1}$ (signal × next-period return)
   - Net P&L: $\text{PnL}_t^{net} = \text{PnL}_t - |\Delta\hat{y}_t| \cdot c$ where $c$ is cost per unit turnover
   - Parameterized spread/slippage per asset class (rates < FX < equities < credit)
   - Worked example: 5 days of signals and returns, cost = 5 bps, compute gross vs. net P&L

3. **Section: Turnover**
   - Definition: $\text{turnover}_t = |\hat{y}_t - \hat{y}_{t-1}|$
   - Average daily turnover: key metric — a signal with 200% daily turnover is impractical
   - Sharpe decay under turnover: how Sharpe erodes as turnover × cost increases
   - Key idea: "Report Sharpe at multiple cost levels. The breakeven cost — where Sharpe hits zero — is the number the desk cares about."

4. **Section: Capacity Estimation**
   - How much capital can the signal absorb before market impact degrades returns?
   - Market impact models: square-root impact $\Delta P \propto \sigma \sqrt{V/\text{ADV}}$
   - Order-of-magnitude reasoning: if ADV is $1B and you're trading 1% of that, impact is ~[estimate] bps
   - Warning box: "Capacity estimates are inherently rough. Use order-of-magnitude reasoning, not false precision. A signal that works for $10M but not $1B is still interesting — just be honest about it."

5. **Section: Walk-Forward Out-of-Sample Testing**
   - The holdout is sacred: reserved since Phase 1, never touched until Phase 5
   - One-shot test: train on all pre-holdout data, predict into holdout, report metrics
   - DO NOT iterate on the holdout — if it fails, that IS the result
   - Rolling-window variant: retrain on 6-month rolling windows, stitch predictions together

6. **Section: IC, ICIR, and Performance Metrics**
   - IC (Information Coefficient): Spearman rank correlation between predictions and outcomes
   - ICIR (IC Information Ratio): $\text{ICIR} = \text{mean}(\IC) / \text{std}(\IC)$
   - Sharpe ratio: $\SR = \frac{\E[r^{net}]}{\sigma(r^{net})} \cdot \sqrt{252}$
   - Sortino ratio: like Sharpe but uses downside deviation only
   - Hit rate: fraction of predictions with correct sign
   - Max drawdown: worst peak-to-trough decline
   - Comparison table: when to use each metric

7. **Section: P&L Decomposition by Regime**
   - Split your cumulative P&L by regime (cross-ref Ch. 13)
   - If 90% of P&L comes from crisis periods: the signal works but only in rare events
   - If P&L is distributed across regimes: robust signal

8. **Section: Signal Decay Post-Publication**
   - Key Result box: McLean-Pontiff (2016) — "Anomaly returns decline by about 32% out-of-sample after portfolio sorting, and by 58% post-publication. The decline is concentrated in anomalies with high arbitrage activity, consistent with market participants learning from published research."
   - Why proprietary data may be more durable: competitors can't replicate signals from internal risk systems
   - But: if the signal is correlated with a published factor, it will decay with that factor

9. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 15: Chapter 14 — Presenting Quantitative Research

**File:** `ml-learning-guide/chapters/14-presenting-research.tex`
**Depends on:** All other chapters (synthesis)

**Papers to fetch and reference:**
- Kelly & Xiu (2023) "Financial Machine Learning" NBER WP 31502 — survey framing conventions

**Sections to write:**

1. **Project Connection box:** "This is preparation for Week 20 — the final presentation. Everything in this chapter maps directly to Phase 5 deliverables: the research report (Task 23) and the presentation itself (Task 24). The framing advice here draws on how the best academic papers and desk presentations communicate quantitative results."

2. **Section: Framing — Causal Hypothesis + ML Testing**
   - Lead with theory: "He-Krishnamurthy predicts X. We tested this with daily SecDB data."
   - NOT: "We fed features into a GBM and it predicted returns."
   - The first framing invites engagement; the second invites skepticism
   - Key idea: "Frame your work as testing a well-grounded economic hypothesis with modern statistical tools. The ML is the test, not the story."

3. **Section: The Primary Metrics Triad**
   - IC: does the signal predict direction? Report mean and std across time.
   - Sharpe: does the signal make money? Report both raw and DSR-adjusted.
   - Turnover: is it tradeable? Report average daily turnover and breakeven cost.
   - Always report all three together — cherry-picking one is misleading

4. **Section: Ridge Baseline on Every Chart**
   - Every performance chart has two lines: your model (solid) and ridge baseline (dashed)
   - If the lines overlap → ML didn't add value → say so honestly
   - If the model clearly separates → show where and explain why (SHAP)

5. **Section: SHAP Waterfall Plots**
   - For the top 3 most interesting predictions: show what drove each one
   - These convert "trust me" into "here's the mechanism"
   - How to read and explain a waterfall plot to a non-technical audience

6. **Section: One Slide Per Claim**
   - Slide structure: title = claim, body = one chart, footer = metric
   - Avoid multi-chart slides — they dilute focus
   - Suggested deck outline (10 slides):
     1. Title + thesis
     2. Theory (He-Krishnamurthy, Adrian-Etula-Muir)
     3. Data and methodology
     4-6. Results per surviving signal family
     7. Ridge vs. GBM comparison
     8. Regime decomposition
     9. Capacity and cost
     10. Next steps

7. **Section: What-Didn't-Work as Credibility**
   - Documented negative results show intellectual honesty
   - "Feature family X showed no predictive power for target Y after purged CV" is a valuable result
   - Include one slide on negative results — it builds trust

8. **Section: Handling Desk Questions**
   - "What's the capacity?" → cost sensitivity curve, breakeven cost
   - "What happens in a crisis?" → regime-decomposed P&L
   - "Why not just a linear model?" → ridge-vs-GBM comparison
   - "How is this different from [public factor]?" → confound check results
   - "Is this overfit?" → DSR, CPCV distribution, walk-forward OOS
   - Prepare 2-sentence answers for each; have backup slides with detail

9. **Section: Signal Decay and Durability**
   - Mention McLean-Pontiff: published signals lose 30-50% efficacy
   - Argument for proprietary data: competitors can't replicate internal risk signals
   - But acknowledge: if the signal is correlated with a published factor, it shares that factor's decay
   - Key idea: "Be honest about durability. A signal that decays is still valuable if you're the first to trade it."

10. **Summary** + **Key Results recap table**

- [ ] **Step 1: Fetch papers and extract key results**
- [ ] **Step 2: Write full chapter LaTeX**
- [ ] **Step 3: Run Pass 1 (factual accuracy review)**
- [ ] **Step 4: Apply factual corrections**
- [ ] **Step 5: Run Pass 2 (brevity review)**
- [ ] **Step 6: Apply cuts**
- [ ] **Step 7: Run Pass 3 (clarity review)**
- [ ] **Step 8: Apply clarity improvements**
- [ ] **Step 9: Write final chapter file**

---

### Task 16: Final Assembly and Compilation

**Files:**
- Modify: all 14 chapter files (final check)
- Output: `ml-learning-guide/main.pdf`

- [ ] **Step 1: Verify all 14 chapter files exist and are non-empty**

```bash
for f in ml-learning-guide/chapters/*.tex; do echo "$f: $(wc -l < $f) lines"; done
```

Expected: all 14 files with 400+ lines each.

- [ ] **Step 2: Cross-reference consistency check**

Dispatch a subagent to verify:
- Every `\label{}` referenced by `\ref{}` in other chapters exists
- No duplicate labels
- All `\ref{}` calls point to valid labels
- Part I/Part II boundary is correct

- [ ] **Step 3: Compile the full document**

```bash
cd ml-learning-guide
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex  # twice for TOC/refs
```

Expected: compiles with no errors. Warnings about overfull hboxes are acceptable. Output is main.pdf.

- [ ] **Step 4: Page count check**

```bash
# Check PDF page count
pdfinfo ml-learning-guide/main.pdf | grep Pages
```

Expected: 200-300 pages. If significantly outside this range, flag for review.

- [ ] **Step 5: Commit the complete document**

```bash
git add ml-learning-guide/
git commit -m "feat: complete Risk-as-Alpha ML Learning Guide — 14 chapters, ~250 pages"
```

---

## Execution Summary

| Wave | Chapters | Parallel Agents | Dependencies |
|------|----------|----------------|--------------|
| Infrastructure | preamble, main.tex | 1 | None |
| Wave 1 | Ch 1, 3, 5, 8, 10, 11, 13 | 7 | Infrastructure only |
| Wave 2 | Ch 2, 4, 6 | 3 | Wave 1 |
| Wave 3 | Ch 7, 9, 12 | 3 | Wave 2 (Ch 9 needs Ch 4) |
| Wave 4 | Ch 14 | 1 | All |
| Assembly | Final compile | 1 | All chapters |

**Total chapter-writing agents:** 14 (across 4 waves)
**Total review subagents:** 42 (3 per chapter × 14 chapters)
**Estimated output:** ~220-270 pages of LaTeX

## Chapter Label Convention

Every chapter uses `\label{ch:<shortname>}`. Subagents MUST use these exact labels for cross-references:

| Chapter | Label | Shortname |
|---------|-------|-----------|
| Ch 1 | `\label{ch:asset-pricing}` | asset-pricing |
| Ch 2 | `\label{ch:intermediary}` | intermediary |
| Ch 3 | `\label{ch:risk-systems}` | risk-systems |
| Ch 4 | `\label{ch:microstructure}` | microstructure |
| Ch 5 | `\label{ch:regularized}` | regularized |
| Ch 6 | `\label{ch:trees}` | trees |
| Ch 7 | `\label{ch:interpretation}` | interpretation |
| Ch 8 | `\label{ch:panel}` | panel |
| Ch 9 | `\label{ch:features}` | features |
| Ch 10 | `\label{ch:labeling}` | labeling |
| Ch 11 | `\label{ch:validation}` | validation |
| Ch 12 | `\label{ch:backtesting}` | backtesting |
| Ch 13 | `\label{ch:regimes}` | regimes |
| Ch 14 | `\label{ch:presenting}` | presenting |

When cross-referencing, use `Chapter~\ref{ch:shortname}` (e.g., `Chapter~\ref{ch:asset-pricing}`).
