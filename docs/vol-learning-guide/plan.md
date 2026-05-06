# Volatility Learning Guide Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 17-chapter LaTeX learning guide (~300-400 pages) teaching realized volatility estimation, forecasting, and ML from first principles, with intuition-first sequencing and 40-60 diagrams.

**Architecture:** Infrastructure first (preamble + main.tex + placeholders), then 17 chapters written by parallel Opus 4.6 subagents in 6 dependency waves. Each chapter agent researches papers, writes LaTeX, then two review agents run sequentially: a fluff reviewer strips padding, then a clarity reviewer reads from zero prior knowledge and iterates until all gaps are closed. Final assembly compiles all chapters into a single PDF.

**Tech Stack:** LaTeX (report class, tcolorbox, TikZ, pgfplots, natbib, amsmath), pdflatex for compilation

**Spec:** `docs/vol-learning-guide/design.md`

---

## Chunk 1: Infrastructure

### Task 1: Create Directory Structure, Preamble, and main.tex

**Files:**
- Create: `vol-learning-guide/main.tex`
- Create: `vol-learning-guide/preamble.tex`
- Create: `vol-learning-guide/references.bib`
- Create: `vol-learning-guide/chapters/` (17 placeholder files)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p vol-learning-guide/chapters
```

- [ ] **Step 2: Write preamble.tex**

Clone from `ml-learning-guide/preamble.tex` with these changes:
1. Replace `projectconnection` environment with `application` (default title "Application" instead of "Project Connection")
2. Add `pgfplots` package and `\pgfplotsset{compat=1.18}`
3. Add `natbib` package: `\usepackage[round]{natbib}`
4. Add vol-specific math shortcuts
5. Change header right text to "Volatility Learning Guide"

Write this exact content to `vol-learning-guide/preamble.tex`:

```latex
% ══════════════════════════════════════════════════════════════
% Realized Volatility — Learning Guide Preamble
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
\usepackage{pgfplots}
\usepackage{booktabs}
\usepackage{truncate}
\usepackage{multirow}
\usepackage{array}
\usepackage{longtable}
\usepackage[round]{natbib}
\usetikzlibrary{arrows.meta, positioning, fit, backgrounds, calc, decorations.pathreplacing, shapes.geometric}
\tcbuselibrary{breakable, skins}
\pgfplotsset{compat=1.18}

% ── Colours ──
\definecolor{defblue}{HTML}{1a5276}
\definecolor{keyorange}{HTML}{e67e22}
\definecolor{intgreen}{HTML}{1e8449}
\definecolor{warnred}{HTML}{c0392b}
\definecolor{prereqpurple}{HTML}{6c3483}
\definecolor{examteal}{HTML}{117a65}
\definecolor{memgold}{HTML}{b7950b}

% ── Custom Environments ──
% definition     — blue box   — formal definitions
% keyidea        — orange box — important conceptual insights & algorithms
% intuition      — green box  — plain-English explanations and analogies
% warning        — red box    — common pitfalls and methodological errors
% prereq         — purple box — background knowledge (use LIBERALLY)
% application    — teal box   — ties content to practical uses and project directions
% workedexample  — teal box   — worked numerical walk-through
% keyresult      — gold box   — headline result from a paper

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
\newtcolorbox{application}[1][Application]{
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

% ── Math Shortcuts (carried over from ml-learning-guide) ──
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

% ── Math Shortcuts (finance-specific, from ml-learning-guide) ──
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

% ── Math Shortcuts (volatility-specific) ──
\newcommand{\RV}{\operatorname{RV}}
\newcommand{\BPV}{\operatorname{BPV}}
\newcommand{\HAR}{\operatorname{HAR}}
\newcommand{\QLIKE}{\operatorname{QLIKE}}
\newcommand{\IVol}{\operatorname{IV}}
\newcommand{\VRP}{\operatorname{VRP}}
\newcommand{\VVIX}{\operatorname{VVIX}}

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
\fancyhead[R]{\small Volatility Learning Guide}
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

Write the exact content from the spec's main.tex skeleton to `vol-learning-guide/main.tex`:

```latex
\documentclass[11pt,a4paper]{report}
\input{preamble}

\begin{document}

% Title page
\begin{titlepage}
\centering
\vspace*{3cm}
{\Huge\bfseries Realized Volatility\\[0.4cm]
Estimation, Forecasting, and ML\par}
\vspace{1.5cm}
{\Large A Learning Guide\par}
\vspace{1cm}
{\Large Ryan Vincent\par}
\vfill
{\small Last compiled: \today\par}
\end{titlepage}

\tableofcontents
\newpage

\part{What Is Volatility and How Do You Measure It?}
\input{chapters/01-returns-variance-volatility}
\input{chapters/02-realized-volatility}
\input{chapters/03-microstructure-noise}
\input{chapters/04-jumps-continuous-variation}

\part{Forecasting Volatility with Classical Models}
\input{chapters/05-garch-family}
\input{chapters/06-har-model}
\input{chapters/07-rough-volatility}

\part{The Volatility Surface and Options-Implied Information}
\input{chapters/08-options-vol-surface}
\input{chapters/09-variance-risk-premium}

\part{ML Methods for Volatility}
\input{chapters/10-feature-engineering}
\input{chapters/11-tree-methods-vol}
\input{chapters/12-deep-learning-vol}
\input{chapters/13-hybrid-ensemble}

\part{Multivariate Volatility and Connectedness}
\input{chapters/14-multivariate-volatility}
\input{chapters/15-spillovers-connectedness}

\part{Evaluation and Practice}
\input{chapters/16-forecast-evaluation}
\input{chapters/17-applications-projects}

\bibliographystyle{plainnat}
\bibliography{references}

\end{document}
```

- [ ] **Step 4: Create empty references.bib**

Write an empty file with a header comment to `vol-learning-guide/references.bib`:

```bibtex
% ══════════════════════════════════════════════════════════════
% Realized Volatility Learning Guide — Bibliography
% ══════════════════════════════════════════════════════════════
% Each chapter-writing agent appends its references here.
% Use natbib author-year style: \citep{} and \citet{}.
```

- [ ] **Step 5: Create 17 placeholder chapter files**

Create placeholder `.tex` files so the document compiles. Each must contain `\chapter{Title}` and `\label{ch:label}`.

| File | Chapter Title | Label |
|---|---|---|
| `01-returns-variance-volatility.tex` | Returns, Variance, and Why Volatility Matters | `ch:returns` |
| `02-realized-volatility.tex` | Realized Volatility | `ch:rv` |
| `03-microstructure-noise.tex` | Microstructure Noise and Robust Estimators | `ch:noise` |
| `04-jumps-continuous-variation.tex` | Jumps and Continuous Variation | `ch:jumps` |
| `05-garch-family.tex` | The GARCH Family | `ch:garch` |
| `06-har-model.tex` | The HAR Model and Its Extensions | `ch:har` |
| `07-rough-volatility.tex` | Rough Volatility | `ch:rough` |
| `08-options-vol-surface.tex` | Options Basics and the Volatility Surface | `ch:volsurface` |
| `09-variance-risk-premium.tex` | The Variance Risk Premium | `ch:vrp` |
| `10-feature-engineering.tex` | Feature Engineering for Volatility | `ch:features` |
| `11-tree-methods-vol.tex` | Tree-Based Methods for Volatility | `ch:trees-vol` |
| `12-deep-learning-vol.tex` | Deep Learning for Volatility | `ch:dl-vol` |
| `13-hybrid-ensemble.tex` | Hybrid and Ensemble Models | `ch:hybrid` |
| `14-multivariate-volatility.tex` | Realized Covariance and Multivariate Forecasting | `ch:multivariate` |
| `15-spillovers-connectedness.tex` | Volatility Spillovers and Connectedness | `ch:spillovers` |
| `16-forecast-evaluation.tex` | Forecast Evaluation | `ch:evaluation` |
| `17-applications-projects.tex` | Practical Applications and Project Directions | `ch:applications` |

Each placeholder file should contain:

```latex
\chapter{<Title>}
\label{ch:<label>}

% TODO: Write this chapter
```

- [ ] **Step 6: Test compilation**

```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

Expected: compiles with warnings about empty chapters and missing `.bib` entries, but no errors. Produces `main.pdf` with title page and TOC.

- [ ] **Step 7: Commit**

```bash
git add vol-learning-guide/
git commit -m "feat: vol learning guide infrastructure -- preamble, main.tex, chapter placeholders"
```

---

## Chunk 2: Common Chapter Workflow + Wave 1 Chapters

### Common Chapter-Writing Workflow

Every chapter is written by dispatching subagents. The per-chapter tasks below specify only the chapter-specific content (topics, papers, sections). The workflow is identical for all 17 chapters:

**Subagent 1: Chapter writer (Opus 4.6)**

The writing agent receives:
- The chapter outline from this plan (topics, papers, sections)
- The spec's writing conventions (Section 4 of the design spec)
- The spec's chapter template (application box first, then intro, numbered sections, summary, key results table)
- The completed `.tex` files of all dependency chapters (for cross-referencing via `\ref{}`)
- The VOL.md source material for paper references and URLs
- The `references.bib` file (to append new bibliography entries)

The agent:
1. Uses WebSearch/WebFetch to fetch abstracts and key results from papers listed for the chapter. If web access is unavailable, uses VOL.md annotations and marks unverified statistics with `[VERIFY]`.
2. Writes the full chapter `.tex` file following the mandatory structure:
   - `\chapter{Title}` and `\label{ch:label}`
   - `\begin{application}[...]` box (always first)
   - Introduction (2-3 sentences)
   - Numbered sections, one concept per section, following the intuition-first sequence:
     - `prereq` boxes for background (used aggressively; reader has strong math, no vol knowledge)
     - `intuition` box, then TikZ/pgfplots diagram, then `definition` box for formal concepts
     - Term-by-term explanation (bulleted list) after every equation
     - `workedexample` boxes with actual financial numbers
     - `keyresult` boxes for paper findings (with actual reported statistics)
     - `warning` boxes for common pitfalls
     - `keyidea` boxes for core insights
     - "Where we are" connector sentence at start of each section
   - Summary section (8-15 bullet points)
   - Key Results recap table (paper, result, relevance)
3. Appends any new bibliography entries to `references.bib`.

**Subagent 2: Fluff reviewer (Opus 4.6)**

Receives the chapter `.tex` file. Strips:
- Throat-clearing phrases ("It is worth noting that...", "Importantly,...", "As we shall see...", "It should be mentioned that...")
- Redundant restatements of things already said in the chapter
- Filler sentences that do not teach anything new
- Overly verbose explanations that could be tighter
- Any em dashes (replace with commas, semicolons, colons, or parentheses)
- Any sentences starting with "Note that" or "Recall that" unless genuinely necessary

Returns the cleaned `.tex` file.

**Subagent 3: Clarity reviewer (Opus 4.6, iterative)**

Receives the cleaned `.tex` file and the `.tex` files of all preceding chapters (so it knows what has already been taught). Reads the chapter assuming **zero prior knowledge beyond what earlier chapters taught**. Works through every section, equation, and diagram as a first-time reader. Reports:

- Concepts used before they are defined (in this chapter or earlier ones)
- Logical jumps where a step is missing ("how did we get from A to C?")
- Equations where the preceding intuition or diagram does not actually prepare you for the math
- Diagrams referenced in text but not present as TikZ/pgfplots code
- Places where a diagram is clearly needed but missing
- Anywhere the reviewer cannot follow the logic without outside knowledge

If the reviewer reports gaps, those gaps are fixed and the reviewer runs again on the updated file. **This loop repeats until the reviewer reports zero gaps.** Capped at 5 iterations; if not converged, surface remaining issues to the user.

**After all 3 subagents complete:** Write the final `.tex` file and commit.

---

### Task 2: Chapter 1 -- Returns, Variance, and Why Volatility Matters

**File:** `vol-learning-guide/chapters/01-returns-variance-volatility.tex`
**Wave:** 1 (no dependencies)
**Bib entries to append:** `vol-learning-guide/references.bib`

**Papers to fetch and reference:**
- Mandelbrot (1963) "The Variation of Certain Speculative Prices" -- fat tails in financial returns
- Fama (1965) "The Behavior of Stock-Market Prices" -- distribution of returns
- Cont (2001) "Empirical properties of asset returns: stylized facts and statistical issues" -- canonical stylized facts reference
- Engle (1982) "Autoregressive Conditional Heteroscedasticity" -- volatility clustering (motivates GARCH in Ch. 5)

**Sections to write:**

1. **Application box:** "Volatility is the central quantity in quantitative finance. Options pricing, risk management, portfolio construction, and trade execution all depend on accurate volatility estimates. Every chapter in this guide builds on the concepts introduced here. All 5 project directions (Chapter~\ref{ch:applications}) start from the returns and variance foundations covered in this chapter."

2. **Section: What Are Returns?**
   - Simple returns: $R_t = (P_t - P_{t-1}) / P_{t-1}$
   - Log returns: $r_t = \ln(P_t / P_{t-1})$
   - Why log returns: additive over time, symmetric for gains/losses
   - Worked example: stock price from \$100 to \$105 to \$102, compute both return types
   - Prereq box: natural logarithm properties

3. **Section: Variance and Standard Deviation**
   - Sample variance: $\hat{\sigma}^2 = \frac{1}{T-1}\sum_{t=1}^T (r_t - \bar{r})^2$
   - Volatility = standard deviation of returns, typically annualized ($\times\sqrt{252}$ for daily)
   - Term-by-term explanation
   - Worked example: 5 daily returns, compute variance and annualized volatility

4. **Section: Why Volatility Matters**
   - Options pricing: Black-Scholes requires a volatility input (motivates Ch. 8)
   - Risk management: VaR scales with volatility
   - Portfolio construction: mean-variance optimization, risk parity
   - Execution: intraday vol determines participation rates
   - Key idea: "Volatility is one of the few quantities in finance that is directly observable (from intraday data), economically central, and forecastable. That combination makes it the right place to apply ML carefully."

5. **Section: Stylized Facts of Financial Returns**
   - Fact 1: Returns are approximately uncorrelated (no free lunch in means)
   - Fact 2: Squared/absolute returns are strongly autocorrelated (volatility clusters)
   - Fact 3: Return distributions have fat tails (kurtosis > 3)
   - Fact 4: Leverage effect: negative returns increase future volatility more than positive returns of the same magnitude
   - Key Result box: Cont (2001) -- canonical enumeration of stylized facts across equities, FX, and commodities
   - Diagrams:
     - Return distribution vs normal distribution (QQ plot or overlay histogram), showing fat tails
     - Autocorrelation of returns vs autocorrelation of squared returns (bar chart), showing clustering
     - Time series of returns showing volatility clustering visually (periods of calm vs turbulence)

6. **Section: Conditional vs Unconditional Volatility**
   - Unconditional: the overall standard deviation (a single number)
   - Conditional: volatility at time $t$ given information up to $t-1$ (a time-varying quantity)
   - The goal of this guide: forecasting conditional volatility
   - Intuition box: "Unconditional volatility is the average turbulence over the whole history. Conditional volatility is how turbulent the market is right now. The difference matters because traders need to know what volatility will be tomorrow, not what it has been on average."

7. **Summary** (8-15 bullets)
8. **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6)**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative until zero gaps)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 3: Chapter 5 -- The GARCH Family

**File:** `vol-learning-guide/chapters/05-garch-family.tex`
**Wave:** 1 (no dependencies)
**Bib entries to append:** `vol-learning-guide/references.bib`

**Papers to fetch and reference:**
- Engle (1982) "Autoregressive Conditional Heteroscedasticity" -- ARCH
- Bollerslev (1986) "Generalized Autoregressive Conditional Heteroscedasticity" -- GARCH
- Nelson (1991) "Conditional Heteroskedasticity in Asset Returns: A New Approach" -- EGARCH
- Glosten, Jagannathan, Runkle (1993) -- GJR-GARCH
- Baillie, Bollerslev, Mikkelsen (1996) -- FIGARCH
- Hansen, Huang, Shek (2012) "Realized GARCH" J. Applied Econometrics
- Shephard & Sheppard (2010) -- HEAVY model

**Sections to write:**

1. **Application box:** "GARCH models forecast volatility using only daily returns, without intraday data. They are the historical workhorse of volatility modeling and remain widely used in risk management systems. Understanding GARCH is necessary background for appreciating why the HAR model (Chapter~\ref{ch:har}), which uses realized volatility from intraday data, is a significant improvement. Realized GARCH and the HEAVY model bridge these two worlds. Project 1 (HARQ-X) uses GARCH as a comparison baseline."

2. **Section: The ARCH Model**
   - Engle (1982): conditional variance depends on past squared returns
   - $\sigma^2_t = \omega + \alpha_1 r^2_{t-1}$
   - Intuition: a big return yesterday means higher expected volatility today
   - Limitation: only one lag; need many parameters for long memory

3. **Section: GARCH(1,1)**
   - $\sigma^2_t = \omega + \alpha r^2_{t-1} + \beta \sigma^2_{t-1}$
   - Term-by-term: $\omega$ = long-run floor, $\alpha$ = reaction to new information, $\beta$ = persistence of old volatility
   - Stationarity: requires $\alpha + \beta < 1$
   - Diagram: feedback loop showing how today's variance feeds into tomorrow's
   - Worked example: given $\omega=0.00001$, $\alpha=0.08$, $\beta=0.90$, $r_{t-1}=-0.03$, $\sigma^2_{t-1}=0.0004$; compute $\sigma^2_t$ step by step
   - Key idea: "GARCH(1,1) captures 95\% of what GARCH models do. Higher-order GARCH(p,q) rarely helps in practice."

4. **Section: The Leverage Effect and EGARCH**
   - Negative returns increase future vol more than positive returns of the same size
   - EGARCH (Nelson 1991): $\ln \sigma^2_t = \omega + \beta \ln \sigma^2_{t-1} + \alpha\left(\frac{|r_{t-1}|}{\sigma_{t-1}} - \sqrt{2/\pi}\right) + \gamma \frac{r_{t-1}}{\sigma_{t-1}}$
   - The $\gamma$ term captures asymmetry; $\gamma < 0$ means negative returns increase vol
   - Diagram: asymmetric response curve showing vol response to positive vs negative returns
   - GJR-GARCH as a simpler alternative: $\sigma^2_t = \omega + (\alpha + \gamma \cdot \mathbf{1}_{r<0}) r^2_{t-1} + \beta \sigma^2_{t-1}$

5. **Section: Long Memory and FIGARCH**
   - Volatility autocorrelation decays slowly (quasi-long-memory behavior)
   - FIGARCH (Baillie-Bollerslev-Mikkelsen 1996): fractional integration parameter $d \in (0,1)$
   - Intuition: $d=0$ is GARCH (short memory), $d=1$ is IGARCH (unit root), $d$ in between captures slow decay
   - Brief treatment; rough volatility (Ch. 7) provides an alternative explanation for this slow decay

6. **Section: Realized GARCH**
   - Key idea: GARCH uses only daily returns; but intraday data is available. Why not use it?
   - Realized GARCH (Hansen-Huang-Shek 2012): adds a measurement equation linking RV to conditional variance
   - Return equation: $r_t = \sqrt{h_t} z_t$
   - Measurement equation: $\log \RV_t = \xi + \delta \log h_t + \tau(z_t) + u_t$
   - GARCH equation: $\log h_{t+1} = \omega + \beta \log h_t + \gamma \log \RV_t$
   - Key Result box: Hansen-Huang-Shek (2012) -- "Realized GARCH substantially outperforms standard GARCH(1,1) in both in-sample fit and out-of-sample forecasting."
   - Diagram: information flow showing how RV feeds back into the GARCH conditional variance

7. **Section: The HEAVY Model**
   - HEAVY (Shephard-Sheppard 2010): joint system for daily returns and realized measures
   - Similar motivation to Realized GARCH; models both the return and the RV as a system
   - Comparison table: GARCH vs Realized GARCH vs HEAVY (data used, equations, strengths)

8. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6)**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative until zero gaps)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 4: Chapter 8 -- Options Basics and the Volatility Surface

**File:** `vol-learning-guide/chapters/08-options-vol-surface.tex`
**Wave:** 1 (no dependencies)
**Bib entries to append:** `vol-learning-guide/references.bib`

**Papers to fetch and reference:**
- Black & Scholes (1973) "The Pricing of Options and Corporate Liabilities" -- just enough for IV definition
- Britten-Jones & Neuberger (2000) "Option Prices, Implied Price Processes, and Stochastic Volatility" -- model-free implied variance
- Cont & da Fonseca (2002) "Dynamics of Implied Volatility Surfaces" -- PCA of IV surface
- CBOE VIX White Paper -- VIX construction methodology

**Sections to write:**

1. **Application box:** "Options-implied information is a rich source of features for volatility forecasting (Chapter~\ref{ch:features}). The variance risk premium (Chapter~\ref{ch:vrp}) is defined using implied volatility from this chapter. Project 5 (VRP ML trader) directly trades the gap between implied and realized vol. Even for non-options projects, understanding the vol surface is necessary because VIX and IV-derived features appear in virtually every competitive feature set."

2. **Section: What Is an Option?**
   - Call option: right to buy at strike $K$ by expiry $T$
   - Put option: right to sell at strike $K$ by expiry $T$
   - Payoff at expiry: call = $\max(S_T - K, 0)$, put = $\max(K - S_T, 0)$
   - Diagram: payoff diagrams for long call, long put, short call, short put
   - Prereq box: basic probability concepts (expected value, distribution)
   - No assumed knowledge of options

3. **Section: Black-Scholes in One Page**
   - The formula: $C = S\Phi(d_1) - Ke^{-rT}\Phi(d_2)$
   - $d_1 = \frac{\ln(S/K) + (r + \sigma^2/2)T}{\sigma\sqrt{T}}$, $d_2 = d_1 - \sigma\sqrt{T}$
   - Term-by-term: $S$ = spot, $K$ = strike, $r$ = risk-free rate, $T$ = time to expiry, $\sigma$ = volatility, $\Phi$ = standard normal CDF
   - Key assumptions: constant vol, log-normal returns, no jumps, continuous trading
   - Warning box: "Black-Scholes is wrong in nearly all its assumptions. But it remains the market's common language for quoting option prices. When traders say 'this option is trading at 25 vol,' they mean the Black-Scholes implied volatility is 25\%."
   - Worked example: $S=100$, $K=105$, $r=0.05$, $T=0.25$, $\sigma=0.20$; compute call price step by step

4. **Section: Implied Volatility**
   - Definition: the $\sigma$ that makes Black-Scholes match the observed market price
   - $C_{market} = C_{BS}(S, K, r, T, \sigma_{implied})$; solve for $\sigma_{implied}$
   - Intuition box: "Implied volatility is the 'wrong number to put in the wrong formula to get the right price.' It is not a forecast of future volatility; it is the market's consensus price of uncertainty, contaminated by risk premia, supply/demand for options, and model error."
   - IV is strike- and maturity-dependent (not a single number)

5. **Section: The Implied Volatility Surface**
   - The IV surface: $\sigma_{implied}(K, T)$ across strikes and maturities
   - Smile: IV is higher for deep OTM puts and calls (fat tails in both directions)
   - Skew: IV is higher for low strikes than high strikes (crash risk; left tail heavier)
   - Term structure: short-dated IV is more volatile than long-dated (mean reversion)
   - Diagrams:
     - 2D: IV vs moneyness at fixed maturity (smile/skew shape)
     - 3D wireframe: IV surface across moneyness and maturity
   - Key idea: "If Black-Scholes were correct, the surface would be flat (same IV everywhere). The shape of the surface tells you what the market fears: skew = crash risk, smile = tail risk, steep term structure = short-term uncertainty."

6. **Section: PCA of the Volatility Surface**
   - Cont-Fonseca (2002): PCA on daily changes of the IV surface
   - 3 dominant factors: level (parallel shift), slope (skew change), curvature (smile change)
   - These 3 factors explain ~95% of daily surface variation
   - Practical use: compress the entire surface into 3 numbers for feature engineering

7. **Section: Model-Free Implied Variance and VIX**
   - Britten-Jones-Neuberger (2000): expected integrated variance under the risk-neutral measure, no model needed
   - VIX: the CBOE's implementation of model-free implied variance for S&P 500 over 30 days
   - $VIX^2 = \frac{2}{T}\int_0^\infty \frac{C(K) + P(K)}{K^2} dK$ (simplified)
   - VIX is NOT a forecast of realized vol; it is implied vol under the risk-neutral measure (includes risk premia)
   - Warning box: "VIX systematically overstates future realized volatility. The gap between VIX-squared and realized variance is the variance risk premium (Chapter~\ref{ch:vrp}). Using VIX as a direct vol forecast is a common and costly mistake."

8. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6)**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative until zero gaps)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 5: Chapter 16 -- Forecast Evaluation

**File:** `vol-learning-guide/chapters/16-forecast-evaluation.tex`
**Wave:** 1 (no dependencies)
**Bib entries to append:** `vol-learning-guide/references.bib`

**Papers to fetch and reference:**
- Patton (2011) "Volatility Forecast Comparison Using Imperfect Volatility Proxies" J. Econometrics
- Hansen, Lunde, Nason (2011) "The Model Confidence Set" Econometrica
- Diebold & Mariano (1995/2002) "Comparing Predictive Accuracy" -- DM test
- Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio"
- Lopez de Prado (2018) AFML Ch. 7 (purged K-fold CV with embargo)
- Harvey & Liu (2015) "Backtesting"

**Sections to write:**

1. **Application box:** "This chapter teaches the evaluation methodology used across all project directions. Every volatility forecast you produce must be evaluated with QLIKE (not MSE), compared with the Diebold-Mariano test, and placed in a Model Confidence Set. If you use cross-validation, it must be purged. If you report Sharpe ratios, they must be deflated. These are not optional extras; they are the minimum standard for credible work."

2. **Section: Why Evaluation Methodology Matters**
   - A 5% improvement in QLIKE that is not statistically significant is noise
   - A Sharpe ratio of 1.5 from 30 experiments may be pure luck
   - The evaluation framework IS the credibility of your results

3. **Section: MSE and Its Limitations for Volatility**
   - $MSE = \frac{1}{T}\sum_t (\sigma^2_t - h_t)^2$
   - Problem: we never observe true $\sigma^2_t$, we use a proxy (RV); MSE is robust to this
   - Bigger problem: MSE is symmetric and heavily penalizes extreme values; in vol, outlier days dominate

4. **Section: QLIKE -- The Preferred Loss**
   - $\QLIKE = \frac{1}{T}\sum_t \left(\ln h_t + \frac{\sigma^2_t}{h_t}\right)$
   - Term-by-term: $h_t$ = forecast, $\sigma^2_t$ = realized proxy
   - Key Result box: Patton (2011) -- "QLIKE is robust to noise in the volatility proxy AND less sensitive to extreme RV days than MSE. QLIKE and MSE are the only two loss functions that produce correct model rankings even when the proxy is noisy."
   - Worked example: 5 days of forecasts and realized values, compute both MSE and QLIKE, show how rankings can differ
   - Key idea: "Always report QLIKE as the primary loss. Report MSE as a secondary check."

5. **Section: Mincer-Zarnowitz Regressions**
   - Regress $\sigma^2_t = a + b \cdot h_t + \varepsilon_t$
   - Unbiased forecast: $a=0$, $b=1$; test jointly with F-test
   - Useful as a diagnostic; shows whether the forecast is systematically biased

6. **Section: Diebold-Mariano Test**
   - Pairwise comparison: is model A's loss significantly different from model B's?
   - $d_t = L(e^A_t) - L(e^B_t)$, test whether $\E[d_t] = 0$
   - Under serial correlation: HAC standard errors (Newey-West)
   - Worked example: two models, 100 days of losses, compute DM statistic

7. **Section: Model Confidence Set**
   - Hansen-Lunde-Nason (2011): given many models, return the set of statistically indistinguishable best models
   - MCS at 90% confidence: "these 4 models are equally good; the other 8 are significantly worse"
   - Key Result box: Hansen-Lunde-Nason (2011) -- "The Model Confidence Set is the gold standard for multi-model comparison. It controls the familywise error rate and produces a set, not a ranking."
   - Practical use: report which models are in the MCS at 5% and 10% significance

8. **Section: Purged K-Fold CV with Embargo**
   - Why standard K-fold fails for time series: temporal autocorrelation leaks information
   - Purging: remove training observations whose label windows overlap with the test period
   - Embargo: additional buffer after test period
   - Diagram: 5 folds on a timeline, showing purged and embargoed regions shaded out
   - Worked example: 1,250 daily observations, K=5, embargo=2% (25 days)
   - Warning box: "Random K-fold on time series data is catastrophic. A model trained on January and March, tested on February, has seen the future. Always use purged CV or expanding-window OOS."

9. **Section: Deflated Sharpe Ratio**
   - The problem: selection bias from multiple testing (you tried 30 feature sets)
   - Expected maximum Sharpe under the null: grows with number of trials
   - DSR formula and worked example (cross-reference ml-learning-guide Ch. 11 if reader wants full derivation)
   - Key idea: "Every experiment counts as a trial, even the failures. Log everything."

10. **Section: What Doesn't Work**
    - Random K-fold on time series (look-ahead)
    - Naive OOS R-squared without DM/MCS (tiny improvements are noise)
    - Overfitting to one regime (train 2015-2019, test 2020)
    - Look-ahead in feature construction (day-t VIX to predict day-t vol)
    - Beating HAR by 0.5% (unlikely to translate to PnL)
    - High forecast variance (useless for vol targeting)

11. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6)**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative until zero gaps)**
- [ ] **Step 4: Write final chapter file and commit**

---

## Chunk 3: Wave 2 Chapters

Wave 2 chapters depend on Wave 1 chapters. Each writing agent receives the completed `.tex` files of its dependency chapters for cross-referencing.

### Task 6: Chapter 2 -- Realized Volatility

**File:** `vol-learning-guide/chapters/02-realized-volatility.tex`
**Wave:** 2 (depends on Ch 1)
**Dependencies:** Chapter 1 completed `.tex`

**Papers to fetch and reference:**
- Andersen, Bollerslev, Diebold, Labys (2001/2003) "Modeling and Forecasting Realized Volatility" Econometrica
- Barndorff-Nielsen & Shephard (2002) "Econometric analysis of realized volatility" JRSS-B
- Liu, Patton, Sheppard (2015) "Does Anything Beat 5-Minute RV?" J. Econometrics

**Sections to write:**

1. **Application box:** "Realized volatility is the target variable for every project direction in this guide. Chapters 3-4 refine the estimator (handling noise and jumps), Chapter 6 builds the HAR forecasting model around it, and Chapter 10 uses RV-derived features. You need to understand RV at an intuitive level (what it measures, how it is constructed, why 5-minute sampling) before any of that."

2. **Section: Integrated Variance and Quadratic Variation**
   - The theoretical quantity: $IV_t = \int_{t-1}^{t} \sigma^2_s \, ds$ for a continuous semimartingale
   - Intuition: the total "energy" of price movements over the day
   - Prereq box: integral as area under a curve; semimartingale (informal: a price process with drift and diffusion)

3. **Section: Realized Variance as an Estimator**
   - $\RV_t = \sum_{i=1}^{n} r^2_{t,i}$ where $r_{t,i}$ are intraday returns
   - Convergence: as $\Delta t \to 0$ (more frequent sampling), $\RV_t \to QV_t$ (quadratic variation)
   - In the absence of microstructure noise, $QV_t = IV_t$ + jump component
   - Diagram: price path over one day, divided into intervals, showing how squared returns are summed
   - Worked example: 6 half-hourly returns over a day, compute RV step by step

4. **Section: How Frequently to Sample**
   - Theory: higher frequency = better estimator (more data points)
   - Practice: bid-ask bounce and other microstructure noise corrupt very high frequency returns
   - The tradeoff: more data vs more noise
   - Diagram: the "volatility signature plot" concept (preview; detailed in Ch. 3)
   - Key idea: "In theory, sample as fast as possible. In practice, noise wins beyond about 5-minute returns."

5. **Section: 5-Minute RV -- The Practical Workhorse**
   - Key Result box: Liu-Patton-Sheppard (2015) -- "Across ~400 realized estimators applied to 31 assets in 5 asset classes (equities, bonds, FX, commodities, equity indices), the simple 5-minute RV is hard to beat as a benchmark for forecasting purposes. More sophisticated noise-robust estimators sometimes win marginally on direct accuracy but rarely improve downstream forecasts."
   - Implication: for most practical work, 5-minute RV is the right default; use noise-robust estimators (Ch. 3) when estimation accuracy matters more than forecasting

6. **Section: Realized Volatility vs Realized Variance**
   - $\RV_t$ can refer to either the variance or its square root; convention varies by paper
   - This guide: $\RV_t$ = realized variance (sum of squared returns); $\sqrt{\RV_t}$ = realized volatility
   - Warning box: "Check whether a paper reports realized variance or realized volatility (standard deviation). Confusing the two is a factor-of-10 error for typical daily values."

7. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 1 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 7: Chapter 6 -- The HAR Model and Its Extensions

**File:** `vol-learning-guide/chapters/06-har-model.tex`
**Wave:** 2 (depends on Ch 2, Ch 5)
**Dependencies:** Chapter 2 and Chapter 5 completed `.tex`

**Papers to fetch and reference:**
- Corsi (2009) "A Simple Approximate Long-Memory Model of Realized Volatility" J. Financial Econometrics
- Bollerslev, Patton, Quaedvlieg (2016) "Exploiting the Errors: HARQ" J. Econometrics
- Patton & Sheppard (2015) "Good Volatility, Bad Volatility" RestStat
- Andersen, Bollerslev, Diebold (2007) -- HAR-J
- Corsi, Pirino, Reno (2010) -- HAR-CJ

**Sections to write:**

1. **Application box:** "HAR is THE benchmark for volatility forecasting. Every ML model in Chapters 11-13 must beat HAR to justify its complexity. This chapter must be crystal clear because every subsequent forecasting chapter references it. Projects 1, 4, and 5 all use HAR variants as their primary baseline."

2. **Section: The Heterogeneous Market Hypothesis**
   - Three types of market participants: daily traders, weekly rebalancers, monthly allocators
   - Each type responds to volatility at their own horizon
   - Observed volatility aggregates the behavior of all three
   - Diagram: three trader types at different horizons feeding into observed market volatility

3. **Section: The HAR Model**
   - $\RV_t = \beta_0 + \beta_d \RV_{t-1} + \beta_w \RV^{(w)}_{t-1} + \beta_m \RV^{(m)}_{t-1} + \varepsilon_t$
   - where $\RV^{(w)}_{t-1} = \frac{1}{5}\sum_{i=1}^{5}\RV_{t-i}$ and $\RV^{(m)}_{t-1} = \frac{1}{22}\sum_{i=1}^{22}\RV_{t-i}$
   - Term-by-term: daily, weekly average, monthly average
   - Intuition box: "HAR mimics long memory with just 3 OLS coefficients. The monthly term captures slow-moving persistence, the weekly term captures medium-term dynamics, the daily term captures short-term reactions. Together they reproduce the slow autocorrelation decay that FIGARCH models with fractional integration."
   - Worked example: 22 days of daily RV, compute $\RV^{(w)}$ and $\RV^{(m)}$, fit HAR by OLS (or show pre-fitted coefficients and compute the forecast for day 23)

4. **Section: HAR-J and HAR-CJ**
   - HAR-J: add the jump component $J_t = \max(\RV_t - \BPV_t, 0)$ as a predictor
   - Define BPV inline (brief: $\BPV_t = \frac{\pi}{2}\sum|r_i||r_{i-1}|$, converges to IV even with jumps) and note "covered in detail in Chapter~\ref{ch:jumps}." This is a forward reference; Chapter 4 has not been written at Wave 2, so the writing agent must provide enough BPV context for the reader here.
   - HAR-CJ: separately model continuous $C_t$ and jump $J_t$ components
   - When jumps matter: large jumps reduce persistence; separating them improves forecasts

5. **Section: SHAR -- Good Volatility, Bad Volatility**
   - Key Result box: Patton-Sheppard (2015) -- "Decomposing realized variance into positive semi-variance $RS^+$ and negative semi-variance $RS^-$ substantially improves forecasts. Bad volatility ($RS^-$, from negative returns) is significantly more persistent and informative than good volatility ($RS^+$)."
   - SHAR replaces daily RV with $RS^+_{t-1}$ and $RS^-_{t-1}$
   - Intuition box: "Downward moves tell you more about future volatility than upward moves of the same size. SHAR captures this by tracking 'good vol' and 'bad vol' separately."

6. **Section: HARQ -- Handling Measurement Error**
   - Key Result box: Bollerslev-Patton-Quaedvlieg (2016) -- "HARQ allows the daily AR coefficient to vary with realized quarticity $RQ_t$ (an estimator of the measurement-error variance of RV). On noisy days (high $RQ_t$), the daily RV coefficient shrinks, effectively down-weighting unreliable estimates."
   - $\RV_t = \beta_0 + (\beta_d + \beta_{dQ}\sqrt{RQ_{t-1}})\RV_{t-1} + \beta_w \RV^{(w)}_{t-1} + \beta_m \RV^{(m)}_{t-1} + \varepsilon_t$
   - Key idea: "HARQ is the strongest univariate RV forecast in the literature. It is the bar that ML must clear."

7. **Section: HAR-X and Beyond**
   - HAR-X: add exogenous regressors (VIX, macro variables, lagged signed returns)
   - Audrino-Knaus (2016) "Lassoing the HAR": regularized HAR with many predictors
   - Bollerslev-Hood-Huss-Pedersen (2018) "Risk Everywhere": HAR with rich covariate set
   - Transition to ML: "HAR-X with many predictors is effectively a linear ML model. Chapters 11-13 ask whether nonlinear models can improve on this."

8. **Section: Why HAR Is Hard to Beat**
   - Summary of the honest evidence:
     - Daily horizon, RV-only features: HAR is extremely competitive
     - The gains from ML come from richer features and longer horizons
     - Rolling-window HAR with proper window selection matches off-the-shelf ML (HARd to Beat)
   - Key idea: "If your ML model does not beat HAR on the same features, you have not learned nonlinear structure; you have overfit noise."

9. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 2, Ch 5 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

## Chunk 4: Wave 3 Chapters

### Task 8: Chapter 3 -- Microstructure Noise and Robust Estimators

**File:** `vol-learning-guide/chapters/03-microstructure-noise.tex`
**Wave:** 3 (depends on Ch 2)
**Dependencies:** Chapter 2 completed `.tex`

**Papers to fetch and reference:**
- Hansen & Lunde (2006) "Realized Variance and Market Microstructure Noise"
- Ait-Sahalia, Mykland, Zhang (2005) "How Often to Sample a Continuous-Time Process"
- Zhang, Mykland, Ait-Sahalia (2005) "A Tale of Two Time Scales" JASA -- TSRV
- Zhang (2006) "Efficient estimation of stochastic volatility" Bernoulli -- MSRV
- Barndorff-Nielsen, Hansen, Lunde, Shephard (2008) "Designing Realized Kernels" Econometrica
- Jacod, Li, Mykland, Podolskij, Vetter (2009) -- pre-averaging
- Xiu (2010) -- Quasi-MLE

**Sections to write:**

1. **Application box:** "Microstructure noise is the reason you cannot simply sample tick-by-tick and compute realized variance. This chapter teaches when noise matters, how it biases RV, and the family of robust estimators that correct for it. Chapter~\ref{ch:features} uses these estimators as features. Project 2 (LOB-based intraday) works directly in the high-frequency regime where noise is most severe."

2. **Section: The Microstructure Noise Problem**
   - Three sources: bid-ask bounce, discrete tick sizes, price staleness
   - Intuition box: "At very high frequencies, observed prices alternate between bid and ask. Squaring these back-and-forth moves inflates the sum far beyond the true volatility."
   - Hansen-Lunde (2006), Ait-Sahalia-Mykland-Zhang (2005): bias dominates signal as frequency increases
   - Prereq box: sampling frequency terminology (1-second, 1-minute, 5-minute returns)

3. **Section: The Volatility Signature Plot**
   - Diagram (pgfplots): RV on y-axis vs sampling frequency on x-axis; shows RV increasing sharply at very high frequency (noise bias) and becoming inefficient at very low frequency; the sweet spot around 5-min
   - Key idea: "This plot is the single most important diagnostic in high-frequency volatility estimation. If you build any RV-based system, plot this first."
   - Warning box: "If your volatility signature plot does not show the expected U-shape, either the data is pre-cleaned or there is a data issue. Investigate before proceeding."

4. **Section: Two-Scales Realized Volatility (TSRV)**
   - Zhang-Mykland-Ait-Sahalia (2005): combine a fast-sampled RV with a slow-sampled RV to cancel noise
   - Intuition box: "The fast-sampled RV contains both signal and noise. The slow-sampled RV contains only signal (but is inefficient). Subtracting a scaled version of the slow estimate removes the noise bias."
   - Convergence rate: $n^{-1/6}$ (slower than optimal)
   - Diagram: two time scales overlaid on the same price path
   - Worked example: 6.5-hour trading day, compute TSRV with 1-min (fast) and 30-min (slow) scales

5. **Section: Multi-Scale Realized Volatility (MSRV)**
   - Zhang (2006): extend TSRV to multiple scales; achieves the optimal $n^{-1/4}$ rate
   - Key result box: Zhang (2006): "MSRV achieves the optimal convergence rate $n^{-1/4}$ for integrated variance estimation under i.i.d. noise."
   - Intuition: averaging across many scales extracts more signal than just two

6. **Section: Realized Kernel**
   - Barndorff-Nielsen-Hansen-Lunde-Shephard (2008): flat-top kernel weighting of autocovariances
   - $\hat{K} = \sum_{h=-H}^{H} k(h/H) \hat{\gamma}_h$ where $\hat{\gamma}_h$ are realized autocovariances
   - Intuition box: "The kernel estimator treats the noise as creating spurious autocorrelation in returns. By summing weighted autocovariances with the right kernel shape, it removes the noise contribution."
   - Diagram: kernel weight function (flat near zero, tapering to zero at bandwidth $H$)
   - Key idea: "The realized kernel is the most widely used noise-robust estimator in practice. Use it when estimation accuracy matters more than simplicity."

7. **Section: Pre-Averaging**
   - Jacod-Li-Mykland-Podolskij-Vetter (2009): average returns over local blocks before computing RV
   - Intuition box: "Averaging nearby returns smooths out the bid-ask bounce. The smoothed returns have less noise, so their squared sum is closer to true IV."
   - Diagram: raw returns vs pre-averaged returns on same time axis

8. **Section: Other Estimators**
   - Subsampling/averaging RV (related to TSRV): brief
   - Fourier estimator (Malliavin-Mancino): computes covariation as Fourier coefficients; handles non-synchronous data naturally
   - Quasi-MLE under noise (Xiu 2010): likelihood-based approach; efficient but requires distributional assumptions
   - Brief treatment of each; table comparing assumptions

9. **Section: Which Estimator to Use**
   - Comparison table: estimator, convergence rate, noise assumption, PSD guarantee (for multivariate), practical use case
   - Diagram (TikZ flowchart): decision tree for choosing an estimator based on data characteristics (sampling frequency, asset class, univariate vs multivariate)
   - Key idea: "For daily RV forecasting, 5-minute RV is sufficient (Liu-Patton-Sheppard 2015, Chapter~\ref{ch:rv}). For estimation accuracy or intraday work, use the realized kernel. For multivariate estimation, see Chapter~\ref{ch:multivariate}."

10. **Summary** (8-15 bullets) + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 2 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 9: Chapter 4 -- Jumps and Continuous Variation

**File:** `vol-learning-guide/chapters/04-jumps-continuous-variation.tex`
**Wave:** 3 (depends on Ch 2; soft cross-ref to Ch 3)
**Dependencies:** Chapter 2 completed `.tex`; Chapter 3 for soft cross-reference only

**Papers to fetch and reference:**
- Barndorff-Nielsen & Shephard (2004, 2006) -- BPV and BNS jump test
- Lee & Mykland (2008, 2012) -- intraday jump detection
- Ait-Sahalia & Jacod (2009) -- power-variation-ratio test
- Corsi, Pirino, Reno (2010) -- threshold/truncation, HAR-CJ

**Sections to write:**

1. **Application box:** "Separating jump variation from continuous variation is critical for forecasting. The HAR-J and HAR-CJ extensions (Chapter~\ref{ch:har}) split the RV signal into components with different persistence and predictability. Signed jump features appear in Chapter~\ref{ch:features}. Projects 1 and 4 use jump-decomposed features."

2. **Section: Why Prices Jump**
   - Earnings announcements, macro releases (NFP, CPI, FOMC), flash crashes, geopolitical shocks
   - Intuition box: "Normal price movements are many small moves (diffusion). Jumps are sudden, large moves that cannot be explained by the smooth diffusion process. An earnings surprise that moves a stock 8\% in one tick is a jump."
   - Prereq box: continuous-time price process as drift + diffusion + jump component (informal)
   - Diagram (TikZ): two price paths over the same day, one continuous (smooth), one with a visible jump (sharp discontinuity)

3. **Section: Bipower Variation**
   - $\BPV_t = \frac{\pi}{2}\sum_{i=2}^{n}|r_{t,i}||r_{t,i-1}|$
   - Intuition box: "BPV multiplies consecutive absolute returns. A single large return (a jump) is multiplied by a normal-sized neighbor, keeping the product moderate. But RV squares the large return, amplifying it. This is why $\RV - \BPV$ isolates the jump component."
   - Key result box: Barndorff-Nielsen-Shephard (2004): "BPV converges to integrated variance even in the presence of finite-activity jumps."
   - Term-by-term explanation of the $\pi/2$ scaling factor
   - Diagram (TikZ): side-by-side comparison of how RV and BPV respond to a sequence of returns containing one jump

4. **Section: The BNS Jump Test**
   - Test statistic: $J_t = \frac{\RV_t - \BPV_t}{\sqrt{\theta \max(RQ_t, 0.01)}}$ (simplified)
   - Null hypothesis: no jumps (RV = BPV in probability)
   - Intuition: "If the difference between RV and BPV is too large relative to sampling noise, declare a jump day."
   - Worked example: given RV, BPV, and RQ for one day, compute test statistic and compare to critical value

5. **Section: Lee-Mykland Jump Test**
   - Identifies individual jump times and sizes within the day (not just "did a jump occur?")
   - Diagram (TikZ): intraday return path with detected jump returns highlighted in red, with jump size annotations
   - Key result box: Lee-Mykland (2008): "Provides both jump detection and jump timing at intraday frequency."

6. **Section: Ait-Sahalia-Jacod Test**
   - Power-variation ratio approach: compare realized power variation at two different powers
   - Advantage: robust to microstructure noise (unlike BNS, which can be distorted by noise)
   - Brief treatment; note when this matters (very high-frequency data)

7. **Section: Threshold/Truncation Methods**
   - Mancini; Corsi-Pirino-Reno (2010): truncate returns exceeding a threshold before computing RV
   - Result: continuous HAR-CJ decomposition where $C_t$ and $J_t$ are separately modeled
   - Key idea: "Truncation is the simplest approach: any return larger than a threshold is classified as a jump. The choice of threshold trades off jump detection sensitivity against false positives."

8. **Section: Why the Decomposition Matters**
   - Jump vol and continuous vol have different persistence: continuous vol is highly persistent (HAR captures this), jump vol is transient
   - "Bad jumps" (negative) are more informative for future vol than "good jumps" (positive), connecting to SHAR's $RS^-$ (cross-reference Chapter~\ref{ch:har})
   - Warning box: "Do not treat jump and continuous components as interchangeable. A model that ignores the decomposition (plain HAR) leaves predictability on the table."

9. **Summary** (8-15 bullets) + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 2 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 10: Chapter 7 -- Rough Volatility

**File:** `vol-learning-guide/chapters/07-rough-volatility.tex`
**Wave:** 3 (depends on Ch 2, Ch 6)
**Dependencies:** Chapters 2 and 6 completed `.tex`

**Papers to fetch and reference:**
- Gatheral, Jaisson, Rosenbaum (2018) "Volatility Is Rough" Quantitative Finance
- Bayer, Friz, Gatheral (2016) "Pricing under Rough Volatility" -- rough Bergomi
- Cont & Das (2024) "Rough Volatility: Fact or Artefact?" Sankhya B
- Rosenbaum & Zhang (2022) "On the universality of the volatility formation process" arXiv 2206.14114
- Bennedsen, Lunde, Pakkanen (2022) -- cross-asset universality of H ~ 0.1

**Sections to write:**

1. **Application box**
2. **Section: What Is Roughness?** -- Hurst exponent H; H=0.5 is standard Brownian motion, H<0.5 is rougher; diagrams of sample paths at H=0.1, 0.3, 0.5, 0.7 side by side
3. **Section: Volatility Is Rough** -- Gatheral-Jaisson-Rosenbaum (2018): log-RV empirically behaves like fBM with H~0.1 across assets; how to estimate H from data
4. **Section: The RFSV Forecasting Formula** -- parsimonious one-parameter forecast; competitive with HAR and LSTM
5. **Section: Rough Volatility for Pricing** -- Rough Bergomi (Bayer-Friz-Gatheral 2016); Quadratic Rough Heston (jointly fits SPX and VIX smiles); brief treatment, not the focus of this guide
6. **Section: Fact or Artefact?** -- Cont-Das (2024): observed roughness of realized vol estimates is partly microstructure-noise artefact; diagram showing how noise creates apparent roughness even from smooth spot vol
7. **Section: The Universal LSTM Connection** -- Rosenbaum-Zhang (2022): universal LSTM matches RFSV; both may be learning the same universal kernel (connects to Ch. 12)
8. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 2, Ch 6 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 11: Chapter 9 -- The Variance Risk Premium

**File:** `vol-learning-guide/chapters/09-variance-risk-premium.tex`
**Wave:** 3 (depends on Ch 2, Ch 8)
**Dependencies:** Chapters 2 and 8 completed `.tex`

**Papers to fetch and reference:**
- Bollerslev, Tauchen, Zhou (2009) "Expected Stock Returns and Variance Risk Premia" RFS
- Drechsler & Yaron (2011) -- long-run risk account
- Bekaert & Hoerova (2014) -- VRP = uncertainty + risk aversion
- Bollerslev & Todorov (2015) "Tail Risk Premia" JFE
- Fouhy (2024, SSRN 6570380) -- hierarchical XGBoost for VRP

**Sections to write:**

1. **Application box**
2. **Section: What Is the Variance Risk Premium?** -- $\VRP_t = \E^Q_t[\RV_{t,t+30}] - \E^P_t[\RV_{t,t+30}]$; operationalized as $(VIX/100)^2 - \hat{\RV}_{t+30}$
3. **Section: Why VRP Exists** -- risk-averse investors overpay for downside protection; insurance premium analogy
4. **Section: VRP Predicts Returns** -- BTZ (2009): VRP predicts quarterly equity excess returns with R-squared beating dividend yield; worked example
5. **Section: VRP Predicts Future Volatility** -- mean reversion: when VRP is high, realized vol tends to rise toward implied
6. **Section: Decomposing VRP** -- Bekaert-Hoerova: uncertainty vs risk aversion; Bollerslev-Todorov: normal vs jump-tail components
7. **Section: Vol-of-Vol** -- VVIX, realized vol-of-vol, jumps in VIX; diagram of VIX vs realized vol over time
8. **Section: ML Approaches to VRP** -- Fouhy (2024): hierarchical XGBoost; VRP as both a predictor feature and a trading signal
9. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 2, Ch 8 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

## Chunk 5: Wave 4 Chapters

### Task 12: Chapter 10 -- Feature Engineering for Volatility

**File:** `vol-learning-guide/chapters/10-feature-engineering.tex`
**Wave:** 4 (depends on Ch 4, Ch 6, Ch 7, Ch 9)
**Dependencies:** Chapters 4, 6, 7, 9 completed `.tex`

**Papers to fetch and reference:**
- Lopez de Prado (2018) AFML Ch. 5 (fractional differencing)
- Bollerslev, Li, Patton, Quaedvlieg (2020) "Realized Semicovariances" Econometrica
- Audrino, Sigrist, Ballinari (2020) -- news sentiment for vol
- Rahimikia, Zohren, Poon (2021) -- financial word embeddings
- Christensen, Siggaard, Veliyev (2023) -- ALE plots for feature importance
- Optiver Kaggle top solutions (open-source, github.com/michaelpoluektov/orvp)

**Sections to write:**

1. **Application box**
2. **Section: Lagged RV Transforms** -- daily/weekly/monthly RV, log-RV, sqrt-RV, fractional differences
3. **Section: Realized Quarticity** -- $RQ = (n/3)\sum r^4_i$; measurement-error variance estimator; the HARQ feature
4. **Section: Signed and Asymmetric Features** -- $RS^+$, $RS^-$, signed jumps, realized semi-covariances, leverage features
5. **Section: Higher Moments** -- realized skewness, kurtosis
6. **Section: Microstructure and LOB Features** -- bid-ask spread, OBI, WAP log returns, volume profiles, trade direction, VPIN, market urgency (price_spread x liquidity_imbalance); primarily for intraday projects. Include top Optiver Kaggle features explicitly: WAP log returns, log-return-of-log-return ("price acceleration"), volume-weighted time-bucketed aggregations
7. **Section: Options-Implied Features** -- ATM IV, skew, term structure, VRP proxy, VIX family, Heston spot vol
8. **Section: Cross-Asset Features** -- multi-asset RV, Diebold-Yilmaz spillover indices, sector/index RV
9. **Section: Long-Memory Features** -- fractional differencing (AFML Ch. 5), rolling Hurst exponent
10. **Section: Calendar and Event Features** -- FOMC, NFP, CPI, earnings, expiry, quarter-end, intraday seasonal
11. **Section: Sentiment and Text Features** -- brief; modest gains
12. **Section: Feature Importance** -- ALE plots, SHAP for trees, MDA/MDI
13. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 4, 6, 7, 9 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 13: Chapter 11 -- Tree-Based Methods for Volatility

**File:** `vol-learning-guide/chapters/11-tree-methods-vol.tex`
**Wave:** 4 (depends on Ch 6, Ch 10; Ch 16 available from Wave 1)
**Dependencies:** Chapters 6, 10, 16 completed `.tex`

**Papers to fetch and reference:**
- Christensen, Siggaard, Veliyev (2023) -- ML for vol forecasting
- Branco, Rubesam, Zevallos (2022/2024) -- "does anything beat linear models?"
- "HARd to Beat" (arXiv 2406.08041) -- rolling-window HAR matches ML
- Rahimikia & Poon (2020) -- ML beats HAR 90% of days but fails in stress
- Audrino & Knaus (2016) -- Lassoing the HAR
- Gu, Kelly, Xiu (2020) -- the horse race (for tree method context)

**Sections to write:**

1. **Application box**
2. **Section: Why Trees for Volatility** -- tabular features, automatic nonlinear interactions, fast training enabling more CV iterations
3. **Section: LightGBM and XGBoost** -- brief recap of algorithms (cross-ref ml-learning-guide if reader wants full treatment); focus on vol-specific hyperparameter choices
4. **Section: Hyperparameters for Vol Data** -- low max_depth (3-5), high min_child_samples (50-200), subsample 0.6-0.8, aggressive regularization; warning about defaults
5. **Section: Christensen-Siggaard-Veliyev (2023)** -- key result: trees among best for daily RV on 29 DJIA stocks; gains strongest with rich features and longer horizons
6. **Section: The Optiver Kaggle Evidence** -- 10-min RV from LOB; LightGBM ensembles won; feature engineering > model class
7. **Section: The Honest Assessment** -- daily+RV-only: HAR competitive; daily+rich features: ML wins 5-20% QLIKE; intraday: ML necessary; stress regimes: ML fails; the "HARd to Beat" and Branco-Rubesam-Zevallos results
8. **Section: Ensemble with HAR** -- Rahimikia-Poon: ML beats HAR 90% of OOS days but fails in extreme stress; ensemble mitigates
9. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 6, 10, 16 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

## Chunk 6: Wave 5 Chapters

### Task 14: Chapter 12 -- Deep Learning for Volatility

**File:** `vol-learning-guide/chapters/12-deep-learning-vol.tex`
**Wave:** 5 (depends on Ch 11)
**Dependencies:** Chapter 11 completed `.tex`

**Papers to fetch and reference:**
- Bucci (2020) -- LSTM/NARX for RV
- Sirignano & Cont (2019) -- universal features, pooled LSTM
- Rosenbaum & Zhang (2022) -- universal LSTM
- Moreno-Pino & Zohren (2022) -- DeepVol TCN
- Zhang, Zohren, Roberts (2019) -- DeepLOB
- Chen & Robert (2022) -- graph transformer
- Kidger (2020, 2021) -- neural SDEs/CDEs
- Ding, Lu, Cheung (2025) -- autoencoder for IV surface compression
- Xu & Chen (AAAI 2021) -- deep stochastic vol model
- Du, Moriyama, Tanaka, Ishii (2023) -- normalizing flows co-trained with VAE for RV
- Rahimikia & Poon (2020) -- LSTM + LOB + news

**Sections to write:**

1. **Application box**
2. **Section: LSTMs and GRUs** -- Bucci (2020), Sirignano-Cont (2019), Rosenbaum-Zhang (2022), Rahimikia-Poon (2020); architecture diagram of LSTM cell
3. **Section: Temporal Convolutional Networks** -- DeepVol (Moreno-Pino-Zohren 2022); dilated causal convolutions diagram; interpretable receptive field
4. **Section: DeepLOB** -- Zhang-Zohren-Roberts (2019); CNN-LSTM on raw LOB; the canonical LOB paper
5. **Section: Transformers and Attention** -- Chen-Robert graph transformer; TLOB; caution about long-horizon benchmarks
6. **Section: Modern TS Architectures** -- N-BEATS, N-HiTS, TiDE, TSMixer, PatchTST; limited evidence on RV
7. **Section: Other Approaches** -- neural SDEs/CDEs (Kidger), GPs, reservoir computing/echo state networks, autoencoders/VAEs (Ding-Lu-Cheung 2025 for IV surface compression, Xu-Chen AAAI 2021 deep stochastic vol), normalizing flows (Du-Moriyama-Tanaka-Ishii 2023 co-training with VAE for joint RV transformation + forecast)
8. **Section: The Honest Bottom Line** -- at daily horizon with RV-only lags, HAR often matches DL; ML wins with rich features and at intraday/longer horizons
9. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 11 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 15: Chapter 13 -- Hybrid and Ensemble Models

**File:** `vol-learning-guide/chapters/13-hybrid-ensemble.tex`
**Wave:** 5 (depends on Ch 11, Ch 12)
**Dependencies:** Chapters 11 and 12 completed `.tex`

**Papers to fetch and reference:**
- Rahimikia, Zohren, Poon (2021) -- financial word embeddings + HAR
- GINN (arXiv 2410.00288) -- GARCH-informed neural net
- HAR-SVR (MDPI Risks 2024)

**Sections to write:**

1. **Application box**
2. **Section: Why Hybrids Win** -- HAR captures known linear structure; ML captures residual nonlinearity; combining is almost always better than pure ML
3. **Section: HAR-SVR** -- SVR on HAR residuals
4. **Section: GARCH-Informed Neural Net (GINN)** -- embedding GARCH structure into NN architecture
5. **Section: NLP + HAR** -- Rahimikia-Zohren-Poon: financial word embeddings as vol predictor combined with HAR
6. **Section: Ensemble HAR + LightGBM** -- the safest performer; used in Optiver solutions and Rahimikia-Poon
7. **Section: When to Use Pure ML vs Hybrid** -- if HAR explains 80% of variance, let it handle that; train ML on the residual 20%
8. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 11, 12 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 16: Chapter 14 -- Realized Covariance and Multivariate Forecasting

**File:** `vol-learning-guide/chapters/14-multivariate-volatility.tex`
**Wave:** 5 (depends on Ch 3, Ch 6)
**Dependencies:** Chapters 3 and 6 completed `.tex`

**Papers to fetch and reference:**
- Barndorff-Nielsen, Hansen, Lunde, Shephard (2011) -- multivariate realized kernel
- Engle (2002) -- DCC-GARCH
- Bollerslev, Patton, Quaedvlieg (2018) -- multivariate HARQ / HAR-DRD
- Chiriac & Voev (2011) -- Cholesky-HAR
- Zhang, Pu, Cucuringu, Dong (2024) -- graph-HAR
- Zhang, Cucuringu, Dong (2023) -- GNN with nonlinear spillover
- arXiv 2412.09517 -- SPDNet geometric DL

**Sections to write:**

1. **Application box**
2. **Section: Realized Covariance** -- RC from intraday data; non-synchronous trading (refresh-time, Hayashi-Yoshida)
3. **Section: Multivariate Realized Kernel** -- PSD estimator under noise
4. **Section: DCC-GARCH** -- low-dimensional baseline
5. **Section: Wishart Autoregressive** -- matrix-variate autoregression
6. **Section: HAR-DRD and Multivariate HARQ** -- separately model variances and correlations; BPQ 2018
7. **Section: Cholesky-HAR** -- Cholesky decomposition ensures PSD
8. **Section: Graph-Based Methods** -- Graph-HAR (Zhang-Pu-Cucuringu-Dong 2024), GNN (Zhang-Cucuringu-Dong 2023)
9. **Section: CNN-RCOV** -- applying CNNs directly to realized covariance matrices; treating the RC matrix as an image-like input
10. **Section: Geometric Deep Learning on SPD Manifold** -- SPDNet; why Euclidean operations break PSD; diagram of manifold
11. **Section: The PSD Constraint** -- comparison table of how each method handles positive-definiteness
12. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 3, 6 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 17: Chapter 15 -- Volatility Spillovers and Connectedness

**File:** `vol-learning-guide/chapters/15-spillovers-connectedness.tex`
**Wave:** 5 (depends on Ch 14)
**Dependencies:** Chapter 14 completed `.tex`

**Papers to fetch and reference:**
- Diebold & Yilmaz (2009, 2012, 2014) -- spillover indices
- Antonakakis, Chatziantoniou, Gabauer (2020) -- TVP-VAR connectedness
- Demirer, Diebold, Liu, Yilmaz (2018) -- network approaches
- Sirignano & Cont (2019) -- universal features
- Rosenbaum & Zhang (2022) -- universal LSTM

**Sections to write:**

1. **Application box**
2. **Section: Diebold-Yilmaz Spillover Indices** -- VAR + variance decomposition; total/directional connectedness; diagram of network
3. **Section: TVP-VAR Extensions** -- time-varying spillover; rolling-window vs Bayesian
4. **Section: Network Visualization** -- vol connectedness across asset classes; graph diagram
5. **Section: Cross-Asset Universality** -- Sirignano-Cont (2019), Rosenbaum-Zhang (2022); pooled training, universal H~0.1
6. **Section: Spillover Indices as Features** -- cross-reference Ch. 10; using connectedness measures as predictors
7. **Summary** + **Key Results recap table**

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with Ch 14 .tex**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

## Chunk 7: Wave 6 + Final Assembly

### Task 18: Chapter 17 -- Practical Applications and Project Directions

**File:** `vol-learning-guide/chapters/17-applications-projects.tex`
**Wave:** 6 (depends on all previous chapters)
**Dependencies:** All 16 completed `.tex` files

**Papers to fetch and reference:**
- Moreira & Muir (2017) "Volatility-Managed Portfolios"
- All project-specific papers already cited in earlier chapters

**Sections to write:**

1. **Application box:** "This chapter ties together everything you have learned and maps it to real-world use cases and the 5 project directions from the VOL.md scoping document."

2. **Section: Options Market-Making** -- short-horizon RV feeds theoretical vol for quote pricing
3. **Section: Vol Trading and Variance Swaps** -- VRP-based signals (cross-ref Ch. 9)
4. **Section: Risk Management** -- VaR, ES, FRTB IMA; better RV forecasts yield better risk measures
5. **Section: Vol Targeting and Risk Parity** -- Moreira-Muir (2017): vol-managed portfolios improve Sharpe
6. **Section: Execution** -- intraday vol forecasts shape VWAP/TWAP participation
7. **Section: Stress Testing and Capital** -- better vol forecasts improve VaR/ES for stress testing; FRTB Internal Model Approach; capital allocation uses conditional vol estimates
8. **Section: Forecast Horizons** -- which methods for which horizon; comparison table (intraday, daily, weekly-monthly, cross-asset)
9. **Section: Project 1 -- HARQ-X with ML Residual Augmentation** -- chapters needed (2,5,6,10,11,16), data, methods, baselines, feasibility, wow factor
10. **Section: Project 2 -- Intraday RV from LOB** -- chapters needed (2,3,10,11,12,16), data (Optiver Kaggle), methods, baselines, feasibility
11. **Section: Project 3 -- Multivariate RC with GNNs** -- chapters needed (3,6,14,15,16), data, methods, baselines, feasibility
12. **Section: Project 4 -- Rough Vol vs Deep Learning** -- chapters needed (2,6,7,12,16), data, methods, baselines, feasibility
13. **Section: Project 5 -- VRP ML Trader** -- chapters needed (2,8,9,10,11,16), data, methods, baselines, feasibility
14. **Section: Recommended Combinations** -- portfolio approach; Project 1 as backbone + one ambitious project
15. **Summary** + **Key Results recap table** (project comparison table: scope, risk, wow factor, feasibility)

- [ ] **Step 1: Dispatch chapter writer agent (Opus 4.6) with all 16 chapter .tex files**
- [ ] **Step 2: Dispatch fluff reviewer agent (Opus 4.6)**
- [ ] **Step 3: Dispatch clarity reviewer agent (Opus 4.6, iterative)**
- [ ] **Step 4: Write final chapter file and commit**

---

### Task 19: Final Assembly and Compilation

**Files:**
- Verify: all 17 chapter files in `vol-learning-guide/chapters/`
- Verify: `vol-learning-guide/references.bib` (populated by chapter agents)
- Output: `vol-learning-guide/main.pdf`

- [ ] **Step 1: Verify all 17 chapter files exist and are non-empty**

```bash
for f in vol-learning-guide/chapters/*.tex; do echo "$f: $(wc -l < "$f") lines"; done
```

Expected: all 17 files with 400+ lines each.

- [ ] **Step 2: Cross-reference consistency check**

Dispatch a subagent to verify:
- Every `\label{}` referenced by `\ref{}` in other chapters exists
- No duplicate labels
- All `\ref{}` calls point to valid labels
- All `\citep{}`/`\citet{}` keys exist in `references.bib`

- [ ] **Step 3: Compile the full document**

```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
```

Expected: compiles with no errors. Warnings about overfull hboxes are acceptable. Output is `main.pdf`. Three passes needed for TOC, bibliography, and cross-references.

- [ ] **Step 4: Page count check**

Verify the PDF is in the 300-400 page range. If significantly outside, flag for review.

- [ ] **Step 5: Commit the complete document**

```bash
git add vol-learning-guide/
git commit -m "feat: complete Volatility Learning Guide -- 17 chapters, 40-60 diagrams"
```

---

## Execution Summary

| Wave | Chapters | Max Parallel Agents | Dependencies | Notes |
|------|----------|-------------------|--------------|-------|
| Infrastructure | preamble, main.tex | 1 | None | |
| Wave 1 | Ch 1, 5, 8, 16 | 4 | Infrastructure only | Fully parallel |
| Wave 2 | Ch 2, then Ch 6 | 1+1 sequential | Wave 1 | Ch 6 depends on Ch 2; must run Ch 2 first |
| Wave 3 | Ch 3, 4, 7, 9 | 4 | Wave 2 | Fully parallel |
| Wave 4 | Ch 10, 11 | 2 | Wave 3 | Fully parallel |
| Wave 5 | (Ch 12 ∥ Ch 14), then (Ch 13 ∥ Ch 15) | 2+2 | Wave 4 | Ch 13 depends on Ch 12; Ch 15 depends on Ch 14 |
| Wave 6 | Ch 17 | 1 | All | |
| Assembly | Final compile | 1 | All chapters | |

**Total chapter-writing agents:** 17 (across 6 waves)
**Total fluff review agents:** 17 (one per chapter)
**Total clarity review agents:** 17-85 (one per chapter, up to 5 iterations each)
**All agents:** Opus 4.6
**Estimated output:** ~300-400 pages of LaTeX, 40-60 TikZ/pgfplots diagrams
