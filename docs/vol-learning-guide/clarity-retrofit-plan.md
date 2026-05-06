# Vol Guide Clarity Retrofit — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retrofit all equations in the vol-learning-guide with plain English translations, project connections, setup sentences, and selective geometric diagrams so the reader builds theory intuitively.

**Architecture:** Chapter-by-chapter editing of existing LaTeX files. Each chapter goes through: audit existing equations, add missing clarity elements, add diagrams for key concepts, verify with naive reader pass. No new files created except diagrams if externalized.

**Tech Stack:** LaTeX (tcolorbox environments), TikZ/pgfplots for diagrams, pdflatex for compilation verification.

**Spec:** `docs/vol-learning-guide/clarity-retrofit-design.md`

---

## Reference: Mandatory Equation Pattern

Every labeled equation must have this structure after retrofit:

```latex
% Setup: 1-2 sentences explaining what we're trying to capture
[Setup sentences here]

\begin{equation}
  [formula]
  \label{eq:name}
\end{equation}
\begin{itemize}[nosep]
  \item $X$: description
\end{itemize}

\begin{intuition}[In Plain English]
  2-3 sentences: what the equation DOES conceptually as a unit.
\end{intuition}

\begin{projectconnection}[Why This Matters]
  1-2 sentences: link to vol forecasting project.
\end{projectconnection}
```

**Exceptions:**
- Multi-line `align` environments: one intuition + projectconnection for the final result, not each line
- Existing `keyidea` boxes that already serve the plain English role: keep them, don't duplicate
- Trivial definitional equations: may share a combined box with adjacent equations

---

## Chunk 1: P0 — Foundation Chapters (Ch 1-4)

### Task 1: Retrofit Chapter 1 — Returns, Variance, and Why Volatility Matters

**Files:**
- Modify: `vol-learning-guide/chapters/01-returns-variance-volatility.tex`

**Current state:** 9 equations, 2 intuition boxes, 2 project connections. ~7 equations missing plain English, ~7 missing project connection.

- [ ] **Step 1: Read and audit the chapter**

Read the full chapter. For each of the 9 equations, note:
- Does it have a setup sentence before it? (Y/N)
- Does it have an intuition/keyidea box after it? (Y/N)
- Does it have a projectconnection box after it? (Y/N)
- Would a geometric diagram help? (Y/N)

Record findings as a checklist for the remaining steps.

- [ ] **Step 2: Add setup sentences**

For each equation missing a setup sentence, add 1-2 sentences before the equation explaining what concept we're trying to formalize. Example for the simple return equation:

```latex
% BEFORE (just jumps into equation):
The simple (arithmetic) return over one period measures the fractional price change:

% AFTER (sets up WHY we need this):
To compare price movements across different assets and time periods, we need to
express changes as fractions rather than absolute dollar amounts. The simple return
does exactly this — it measures what fraction of your investment you gained or lost:
```

- [ ] **Step 3: Add plain English intuition boxes**

For each equation missing a plain English translation (that isn't already covered by an existing keyidea box), add an `\begin{intuition}[In Plain English]` box. Example:

```latex
\begin{intuition}[In Plain English]
This equation says: ``take today's price, subtract yesterday's price, and divide by
yesterday's price.'' The result tells you what percentage your investment moved in
one period. A result of 0.02 means your investment grew by 2\% that day.
\end{intuition}
```

- [ ] **Step 4: Add project connection boxes**

For each equation missing a project connection, add a `\begin{projectconnection}[Why This Matters]` box. Example:

```latex
\begin{projectconnection}[Why This Matters]
Returns are the raw input to everything in this project. Realized volatility is
computed by summing squared returns, so if you don't understand what a return
measures, the entire RV pipeline built in later chapters won't make sense.
\end{projectconnection}
```

- [ ] **Step 5: Add geometric diagrams for key concepts**

Chapter 1 key candidates for diagrams:
- A price path annotated with returns (showing what returns "look like" on a chart)
- Variance as the "spread" of a return distribution (histogram with variance highlighted)
- The relationship between variance and volatility (sqrt transformation visualized)

Add 2-3 TikZ diagrams at appropriate locations. Use pgfplots for data visualizations and tikzpicture for schematic diagrams.

- [ ] **Step 6: Evaluate worked examples**

Review any existing worked examples. Keep those that build theoretical intuition. Remove pure computation drills. (Current count suggests 0 workedexample boxes, but check for inline computation walk-throughs that could be trimmed.)

- [ ] **Step 7: Compile and verify**

```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

Fix any LaTeX errors. Verify the new boxes render correctly.

- [ ] **Step 8: Naive reader pass**

Dispatch a sub-agent with the Pass 4 prompt from the write-chapter skill against the retrofitted chapter. Fix all CRITICAL issues flagged.

- [ ] **Step 9: Commit**

```bash
git add vol-learning-guide/chapters/01-returns-variance-volatility.tex
git commit -m "docs(vol-guide): retrofit ch01 with plain English translations and project connections"
```

---

### Task 2: Retrofit Chapter 2 — Realized Volatility

**Files:**
- Modify: `vol-learning-guide/chapters/02-realized-volatility.tex`

**Current state:** 8 equations, 1 intuition box, 1 project connection. ~7 equations missing plain English, ~7 missing project connection. This is the chapter with the convergence to quadratic variation section (2.2.2) that the reader specifically flagged as hard.

- [ ] **Step 1: Read and audit the chapter**

Same audit as Task 1. Pay special attention to Section 2.2.2 (convergence to QV) — this was called out as particularly confusing.

- [ ] **Step 2: Add setup sentences**

Priority: the quadratic variation convergence equation needs a particularly strong setup. Example approach:

```latex
% Setup for QV convergence:
Here is the central insight of realized volatility: if you take a price path,
chop it into tiny intervals, compute the return over each interval, square each
return, and add them all up — as you make the intervals smaller and smaller,
that sum converges to a specific quantity called the \textbf{quadratic variation}.
This is not obvious, and it is the entire theoretical foundation for measuring
volatility from high-frequency data.
```

- [ ] **Step 3: Add plain English intuition boxes**

The QV convergence equation needs an especially clear translation:

```latex
\begin{intuition}[In Plain English]
This equation says: ``sum up all the squared returns over tiny intervals, and as
those intervals shrink to zero, the sum converges to the quadratic variation.''
Think of it like measuring the total distance a drunk person wobbles — you're not
measuring where they end up, but how much total back-and-forth movement happened.
The more finely you measure, the more wobble you capture, until you converge on
the true total wobble (quadratic variation).
\end{intuition}
```

- [ ] **Step 4: Add project connection boxes**

```latex
\begin{projectconnection}[Why This Matters]
This convergence result is WHY realized volatility works as a volatility
measure. Your entire project computes RV from high-frequency returns and then
tries to forecast it. This equation tells you that what you're computing
(sum of squared returns) is a consistent estimator of the true underlying
volatility of the price process. Without this result, RV would just be an
arbitrary statistic with no theoretical grounding.
\end{projectconnection}
```

- [ ] **Step 5: Add geometric diagrams for key concepts**

Chapter 2 key candidates:
- A price path partitioned into intervals, with squared returns shown as areas (visualizing what "sum of squared returns" physically measures)
- Convergence diagram: show RV computed at different sampling frequencies converging to QV
- The relationship: price process → returns → squared returns → sum → RV ≈ QV (flow diagram)

- [ ] **Step 6: Evaluate worked examples**

Same as Task 1.

- [ ] **Step 7: Compile and verify**

```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 8: Naive reader pass**

Dispatch sub-agent. Fix all CRITICAL issues.

- [ ] **Step 9: Commit**

```bash
git add vol-learning-guide/chapters/02-realized-volatility.tex
git commit -m "docs(vol-guide): retrofit ch02 with plain English translations and project connections"
```

---

### Task 3: Retrofit Chapter 3 — Microstructure Noise and Robust Estimators

**Files:**
- Modify: `vol-learning-guide/chapters/03-microstructure-noise.tex`

**Current state:** 6 equations, 6 intuition boxes, 1 project connection. Intuition coverage is good; project connections are the main gap (~5 missing).

- [ ] **Step 1: Read and audit the chapter**

This chapter already has good intuition coverage. Focus audit on: which equations lack project connections, and which need stronger setup sentences.

- [ ] **Step 2: Add setup sentences where missing**

Focus on equations for noise-robust estimators (kernel estimators, subsampling). Setup should explain: "The naive RV estimator breaks when you sample too frequently because of X. We need an estimator that..."

- [ ] **Step 3: Verify existing intuition boxes**

Since 6 already exist for 6 equations, check whether each one actually serves the "plain English translation" role per the spec. If any focus on something else (e.g., a warning or a tangent), add a dedicated translation box.

- [ ] **Step 4: Add project connection boxes**

5 equations need project connections. These should explain how noise-robust estimators relate to the RV pipeline: "In practice, you'll be computing RV from tick data. Without a noise-robust estimator, your RV signal would be dominated by bid-ask bounce..."

- [ ] **Step 5: Add geometric diagrams**

Key candidates:
- The "volatility signature plot" showing RV vs. sampling frequency (the U-shape that motivates robust estimators)
- Bid-ask bounce illustrated on a price path (showing how microstructure noise looks physically)

- [ ] **Step 6: Evaluate worked examples**

Same process.

- [ ] **Step 7: Compile and verify**

```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 8: Naive reader pass**

Dispatch sub-agent. Fix all CRITICAL issues.

- [ ] **Step 9: Commit**

```bash
git add vol-learning-guide/chapters/03-microstructure-noise.tex
git commit -m "docs(vol-guide): retrofit ch03 with project connections and diagrams"
```

---

### Task 4: Retrofit Chapter 4 — Jumps and Continuous Variation

**Files:**
- Modify: `vol-learning-guide/chapters/04-jumps-continuous-variation.tex`

**Current state:** 6 equations, 6 intuition boxes, 2 project connections. Similar to Ch 3 — intuition is covered, project connections are the gap (~4 missing).

- [ ] **Step 1: Read and audit the chapter**

Focus on: which equations lack project connections, whether jump detection test statistics have adequate setup sentences explaining WHY we need to separate jumps from continuous variation.

- [ ] **Step 2: Add setup sentences where missing**

The key setup needed: "Price movements have two components — smooth continuous variation and sudden jumps. For vol forecasting, these behave differently and should be modeled separately. We need a way to detect and separate them..."

- [ ] **Step 3: Verify existing intuition boxes**

Check the 6 existing boxes serve the plain English role adequately.

- [ ] **Step 4: Add project connection boxes**

4 equations need connections. Focus: "Jump-robust variance (bipower variation) is a key feature in HAR-J models you'll build in Chapter 6. Separating jump and continuous components lets your model treat persistent vol differently from one-off shocks..."

- [ ] **Step 5: Add geometric diagrams**

Key candidates:
- A price path with a visible jump, annotated to show "this part is continuous variation" vs. "this is a jump"
- Bipower variation vs. realized variance: what each one captures from the same price path

- [ ] **Step 6: Evaluate worked examples**

Same process.

- [ ] **Step 7: Compile and verify**

```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 8: Naive reader pass**

Dispatch sub-agent. Fix all CRITICAL issues.

- [ ] **Step 9: Commit**

```bash
git add vol-learning-guide/chapters/04-jumps-continuous-variation.tex
git commit -m "docs(vol-guide): retrofit ch04 with project connections and jump diagrams"
```

---

## Chunk 2: P1 — Classical Models (Ch 5-7)

### Task 5: Retrofit Chapter 5 — The GARCH Family

**Files:**
- Modify: `vol-learning-guide/chapters/05-garch-family.tex`

**Current state:** 12 equations, 5 intuition boxes, 2 project connections. Largest equation count in P1. ~7 equations missing plain English, ~10 missing project connections.

- [ ] **Step 1: Read and audit**
- [ ] **Step 2: Add setup sentences** — especially for GARCH(1,1) variance equation, EGARCH, GJR-GARCH. Each variant needs "the previous model couldn't handle X, so we add..."
- [ ] **Step 3: Add plain English intuition boxes** — 7 needed. GARCH(1,1) needs: "tomorrow's variance is a weighted average of three things: a long-run average, today's squared return (the news), and today's variance (the persistence)"
- [ ] **Step 4: Add project connection boxes** — 10 needed. Connect to: "GARCH is your simplest baseline model. HAR beats it for daily RV forecasting, but GARCH captures the key insight: vol clusters"
- [ ] **Step 5: Diagrams** — GARCH feedback loop (may already exist), leverage effect illustration, vol clustering annotated on real-looking price path
- [ ] **Step 6: Evaluate worked examples**
- [ ] **Step 7: Compile and verify**
- [ ] **Step 8: Naive reader pass**
- [ ] **Step 9: Commit**

```bash
git add vol-learning-guide/chapters/05-garch-family.tex
git commit -m "docs(vol-guide): retrofit ch05 GARCH with full clarity treatment"
```

---

### Task 6: Retrofit Chapter 6 — The HAR Model and Its Extensions

**Files:**
- Modify: `vol-learning-guide/chapters/06-har-model.tex`

**Current state:** 12 equations, 3 intuition boxes, 1 project connection. This is the most project-critical chapter (HAR is the primary baseline). Major gaps: ~9 equations missing plain English, ~11 missing project connections.

- [ ] **Step 1: Read and audit**
- [ ] **Step 2: Add setup sentences** — HAR's key setup: "volatility has memory at multiple timescales. Yesterday's vol, last week's average vol, and last month's average vol each predict tomorrow differently. HAR captures this with one simple regression..."
- [ ] **Step 3: Add plain English intuition boxes** — 9 needed. Core HAR equation: "tomorrow's vol is predicted by a weighted combination of yesterday's vol, last week's average vol, and last month's average vol. That's it. This simple idea beats GARCH."
- [ ] **Step 4: Add project connection boxes** — 11 needed. Critical: "HAR is YOUR primary baseline. Every ML model you build must beat HAR to be worth anything. The HARQ extension adds estimation uncertainty as a feature — this is the paper you're building on."
- [ ] **Step 5: Diagrams** — The HAR cascade (daily → weekly → monthly components), HARQ confidence bands
- [ ] **Step 6: Evaluate worked examples**
- [ ] **Step 7: Compile and verify**
- [ ] **Step 8: Naive reader pass**
- [ ] **Step 9: Commit**

```bash
git add vol-learning-guide/chapters/06-har-model.tex
git commit -m "docs(vol-guide): retrofit ch06 HAR with full clarity treatment"
```

---

### Task 7: Retrofit Chapter 7 — Rough Volatility

**Files:**
- Modify: `vol-learning-guide/chapters/07-rough-volatility.tex`

**Current state:** 4 equations, 4 intuition boxes, 2 project connections. Best coverage ratio in the guide. Likely needs only ~2 project connections and setup sentence verification.

- [ ] **Step 1: Read and audit**
- [ ] **Step 2: Add setup sentences where missing**
- [ ] **Step 3: Verify existing intuition boxes** — all 4 equations are covered
- [ ] **Step 4: Add project connection boxes** — ~2 needed. Connect fractional Brownian motion to: "rough vol explains WHY HAR works — the long memory in vol is a consequence of the roughness property"
- [ ] **Step 5: Diagrams** — Hurst exponent visualization (smooth vs rough paths), comparison of H=0.5 (Brownian) vs H=0.1 (rough) sample paths
- [ ] **Step 6: Evaluate worked examples**
- [ ] **Step 7: Compile and verify**
- [ ] **Step 8: Naive reader pass**
- [ ] **Step 9: Commit**

```bash
git add vol-learning-guide/chapters/07-rough-volatility.tex
git commit -m "docs(vol-guide): retrofit ch07 rough vol with project connections and Hurst diagrams"
```

---

## Chunk 3: P2 — Vol Surface (Ch 8-9)

### Task 8: Retrofit Chapter 8 — Options Basics and the Volatility Surface

**Files:**
- Modify: `vol-learning-guide/chapters/08-options-vol-surface.tex`

**Current state:** 9 equations + 1 align, 6 intuition boxes, 5 project connections. Decent coverage. ~4 equations need plain English, ~5 need project connections.

- [ ] **Step 1-9:** Same process as above. Key focus: Black-Scholes equation needs a clear "this equation tells you the fair price of an option given a fixed volatility assumption — but vol ISN'T fixed, which is the whole point of the vol surface." Diagrams: 3D volatility surface, implied vol smile with annotations.

```bash
git commit -m "docs(vol-guide): retrofit ch08 options/vol surface with clarity treatment"
```

---

### Task 9: Retrofit Chapter 9 — The Variance Risk Premium

**Files:**
- Modify: `vol-learning-guide/chapters/09-variance-risk-premium.tex`

**Current state:** 10 equations, 2 intuition boxes, 3 project connections. Large gap: ~8 need plain English, ~7 need project connections.

- [ ] **Step 1-9:** Same process. Key focus: VRP = implied vol - realized vol. "The market systematically OVERPAYS for vol protection. This gap is a tradeable signal." Diagrams: VRP time series showing it's mostly positive, payoff diagram of variance swap.

```bash
git commit -m "docs(vol-guide): retrofit ch09 VRP with clarity treatment"
```

---

## Chunk 4: P3 — ML Methods (Ch 10-13)

### Task 10: Retrofit Chapter 10 — Feature Engineering for Volatility

**Files:**
- Modify: `vol-learning-guide/chapters/10-feature-engineering.tex`

**Current state:** 14 equations + 3 aligns, 1 intuition box, 3 project connections. Largest equation count. Major gap: ~16 need plain English, ~14 need project connections.

- [ ] **Step 1-9:** Same process. This is the most work-intensive chapter. Focus: every feature formula needs "this captures X aspect of vol behavior, and feeds into your model as input column Y." Diagrams: feature importance heatmap schematic, temporal feature alignment diagram.

```bash
git commit -m "docs(vol-guide): retrofit ch10 feature engineering with full clarity treatment"
```

---

### Task 11: Retrofit Chapter 11 — Tree-Based Methods for Volatility

**Files:**
- Modify: `vol-learning-guide/chapters/11-tree-methods-vol.tex`

**Current state:** 4 equations + 1 align, 1 intuition box, 2 project connections. Small chapter. ~4 need plain English, ~3 need project connections.

- [ ] **Step 1-9:** Same process. Focus: "a tree splits your data by asking yes/no questions about features. Random forests average many trees. Gradient boosting builds trees that fix previous trees' mistakes."

```bash
git commit -m "docs(vol-guide): retrofit ch11 tree methods with clarity treatment"
```

---

### Task 12: Retrofit Chapter 12 — Deep Learning for Volatility

**Files:**
- Modify: `vol-learning-guide/chapters/12-deep-learning-vol.tex`

**Current state:** 5 equations + 1 align, 4 intuition boxes, 2 project connections. Moderate gaps.

- [ ] **Step 1-9:** Same process. Focus: LSTM gates need "the forget gate decides what to remember from yesterday's hidden state — for vol, this is the model learning persistence."

```bash
git commit -m "docs(vol-guide): retrofit ch12 deep learning with clarity treatment"
```

---

### Task 13: Retrofit Chapter 13 — Hybrid and Ensemble Models

**Files:**
- Modify: `vol-learning-guide/chapters/13-hybrid-ensemble.tex`

**Current state:** 9 equations, 1 intuition box, 1 project connection. Large gap relative to equation count.

- [ ] **Step 1-9:** Same process. Focus: "hybrid models use HAR as the backbone and ML to model the residuals — you get the interpretability of HAR plus the flexibility of ML."

```bash
git commit -m "docs(vol-guide): retrofit ch13 hybrid/ensemble with clarity treatment"
```

---

## Chunk 5: P4 — Multivariate and Evaluation (Ch 14-17)

### Task 14: Retrofit Chapter 14 — Realized Covariance and Multivariate Forecasting

**Files:**
- Modify: `vol-learning-guide/chapters/14-multivariate-volatility.tex`

**Current state:** 7 equations, 4 intuition boxes, 3 project connections. Moderate gaps.

- [ ] **Step 1-9:** Same process. Focus: "you're not just forecasting one stock's vol — you need the whole covariance matrix for portfolio construction."

```bash
git commit -m "docs(vol-guide): retrofit ch14 multivariate vol with clarity treatment"
```

---

### Task 15: Retrofit Chapter 15 — Volatility Spillovers and Connectedness

**Files:**
- Modify: `vol-learning-guide/chapters/15-spillovers-connectedness.tex`

**Current state:** 9 equations, 2 intuition boxes, 1 project connection. Large gap.

- [ ] **Step 1-9:** Same process.

```bash
git commit -m "docs(vol-guide): retrofit ch15 spillovers with clarity treatment"
```

---

### Task 16: Retrofit Chapter 16 — Forecast Evaluation

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex`

**Current state:** 7 equations, 5 intuition boxes, 4 project connections. Good coverage, small gaps.

- [ ] **Step 1-9:** Same process. Focus: QLIKE needs "this loss function penalizes you MORE for underestimating vol than overestimating it — which matches real-world risk management priorities."

```bash
git commit -m "docs(vol-guide): retrofit ch16 forecast evaluation with clarity treatment"
```

---

### Task 17: Retrofit Chapter 17 — Practical Applications and Project Directions

**Files:**
- Modify: `vol-learning-guide/chapters/17-applications-projects.tex`

**Current state:** 3 equations, 1 intuition box, 1 project connection. Smallest chapter (12KB). Minimal work.

- [ ] **Step 1-9:** Same process.

```bash
git commit -m "docs(vol-guide): retrofit ch17 applications with clarity treatment"
```

---

## Execution Notes

- **Process each task sequentially within a chunk** (chapter N's project connections may reference chapter N+1, so reading order matters)
- **Chunks are independent** and can be executed in separate sessions
- **Start with Chunk 1 (P0)** since the reader is currently on these chapters
- **The naive reader pass (Step 8) is non-negotiable** — every chapter must pass before commit
- **Compilation (Step 7) catches LaTeX errors** — fix before running naive reader
- **Invoke the write-chapter skill's Learning Style Requirements** as the reference for what each box should contain
