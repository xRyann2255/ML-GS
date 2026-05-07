# Vol Project Reference Guide Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 14-chapter LaTeX reference guide (`guides/vol-project-ref/`) that covers every piece of the realized volatility forecasting project in plain English -- features, models, pipeline, evaluation.

**Architecture:** 14 `.tex` chapter files loaded by `main.tex`, using a preamble adapted from the vol learning guide. Each chapter goes through a 4-pass quality pipeline (write, brevity agent, visual diagram check, cross-referencer). Content is drawn primarily from `notes/features/optimal-feature-set.md` and the feature notes in `notes/features/`.

**Tech Stack:** LaTeX (`report` class), `tcolorbox`, `tikz`/`pgfplots`, `natbib`, `booktabs`

**Spec:** `docs/superpowers/specs/2026-05-07-vol-project-ref-guide-design.md`

---

## Writing Rules (apply to every chapter task)

These rules are non-negotiable. Every chapter agent must follow them:

1. **State decisions, not arguments.** "We use LightGBM" not "Here's why trees beat neural networks."
2. **Every feature gets:** name, what it is (one sentence), what it does for our forecast, which data source it uses, which horizon it matters for.
3. **No general background.** Assume the reader understands returns, variance, regression, gradient boosting, LSTMs.
4. **Tables over prose** for reference information.
5. **Diagrams** for any data flow or architecture.
6. **`warning` boxes** for pitfalls that could waste weeks.
7. **`keyidea` boxes** for the single most important takeaway per section.
8. **`workedexample` boxes** for concrete feature computation examples only (sparingly).
9. **Do NOT use** `projectconnection`, `prereq`, or `intuition` boxes.
10. **No em dashes.** Use commas, semicolons, or restructure the sentence.
11. **Citations inline:** `\citep{}` parenthetical, `\citet{}` textual. Every claim cites its source.
12. **Sentence test:** Does this sentence help build or defend a specific piece of the project? If not, cut it.

---

## Per-Chapter Quality Pipeline (apply after every chapter draft)

After writing each chapter, run these passes:

### Pass A: Brevity Agent (sub-agent)

Dispatch sub-agent with prompt:

```
Read the draft chapter at [chapter path]. This is a condensed project reference,
not a textbook. Every sentence must be directly applicable to building or defending
the vol forecasting project.

Flag and suggest cuts for:
- Theory creep: sentences explaining WHY something is true in general
- Justification bloat: sentences arguing for a decision rather than stating it
- Redundancy: same fact stated twice, or table entry repeated in prose
- Hedge words: "It is worth noting," "Interestingly," "In particular"
- Scope creep: true and interesting but not needed to build THIS project

For each flag: location, the offending text, a tightened replacement (or "cut entirely").
```

### Pass B: Cross-referencer (sub-agent, parallel with Pass A)

Dispatch sub-agent with prompt:

```
Read the draft chapter at [chapter path]. Search reference/project-papers/ and
reference/papers/ for papers relevant to claims in the chapter. For each paper found:
- Identify which passage it supports
- Suggest the citation command (\citep{} or \citet{})
- Flag any factual errors the paper contradicts

Output a numbered list of suggested citations with line locations.
```

### Pass C: Consolidation (main agent)

1. Apply brevity edits from Pass A
2. Apply citation suggestions from Pass B (add `\citep{}`/`\citet{}` commands, add entries to `references.bib`)
3. Compile the full document: `cd guides/vol-project-ref && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex`
4. Fix any LaTeX compilation errors

### Pass D: Visual Diagram Check (sub-agent, after compilation)

Dispatch sub-agent with prompt:

```
The guide at guides/vol-project-ref/main.pdf has been compiled. Read the PDF and
inspect every diagram and figure in the most recently added chapter. Check for:
- Overlapping text: labels, arrows, or annotations that collide
- Readability: text too small, cramped spacing
- Missing labels: arrows or boxes without labels
- Layout: diagrams too wide for margins, or too tall for content
- Flow clarity: is data flow direction unambiguous?
- Consistency: consistent styling (arrow types, box shapes, colors) with other chapters

For each issue: figure description, what the problem is, suggested fix.
```

Fix any visual issues and recompile. Iterate until clean.

### Pass E: Commit

```bash
git add guides/vol-project-ref/chapters/chXX-name.tex guides/vol-project-ref/references.bib
git commit -m "docs(vol-project-ref): add chapter XX -- topic name"
```

---

## Chunk 1: Scaffold

### Task 1: Create directory structure

**Files:**
- Create: `guides/vol-project-ref/`
- Create: `guides/vol-project-ref/chapters/`

- [ ] **Step 1: Create directories**

```bash
mkdir -p guides/vol-project-ref/chapters
```

- [ ] **Step 2: Verify**

```bash
ls -la guides/vol-project-ref/
```

Expected: empty directory with `chapters/` subdirectory.

---

### Task 2: Create preamble.tex

**Files:**
- Read: `vol-learning-guide/preamble.tex`
- Create: `guides/vol-project-ref/preamble.tex`

Copy the vol learning guide preamble with one change: the header text.

- [ ] **Step 1: Copy preamble**

```bash
cp vol-learning-guide/preamble.tex guides/vol-project-ref/preamble.tex
```

- [ ] **Step 2: Change header text**

In `guides/vol-project-ref/preamble.tex`, find the string `\fancyhead[R]{\small Volatility Learning Guide}` and replace with:

```latex
\fancyhead[R]{\small Vol Project Reference}
```

- [ ] **Step 3: Verify edit**

Read `guides/vol-project-ref/preamble.tex` and confirm the header line changed.

---

### Task 3: Create references.bib

**Files:**
- Read: `vol-learning-guide/references.bib`
- Create: `guides/vol-project-ref/references.bib`

Copy the existing references.bib (1203 lines, already has most relevant citations). New entries will be added per-chapter by the cross-referencer agent.

- [ ] **Step 1: Copy references**

```bash
cp vol-learning-guide/references.bib guides/vol-project-ref/references.bib
```

- [ ] **Step 2: Update header comment**

Change the first comment lines in `guides/vol-project-ref/references.bib`:

```latex
% FROM:
% Realized Volatility Learning Guide — Bibliography
% TO:
% Vol Project Reference Guide — Bibliography
```

---

### Task 4: Create main.tex

**Files:**
- Create: `guides/vol-project-ref/main.tex`

- [ ] **Step 1: Write main.tex**

```latex
\documentclass[11pt,a4paper]{report}
\input{preamble}

\begin{document}

% Title page
\begin{titlepage}
\centering
\vspace*{3cm}
{\Huge\bfseries Realized Volatility Forecasting\\[0.4cm]
A Project Reference\par}
\vspace{1.5cm}
{\Large Everything needed to build and defend\\[0.3cm]
the vol forecasting system\par}
\vspace{1cm}
{\Large Ryan Vincent\par}
\vfill
{\small Last compiled: \today\par}
\end{titlepage}

\tableofcontents
\newpage

% ══════════════════════════════════════════════════════════════
% Part I — The Project
% ══════════════════════════════════════════════════════════════

\part{The Project}

\input{chapters/ch01-what-we-forecast}
\input{chapters/ch02-our-data}

% ══════════════════════════════════════════════════════════════
% Part II — The Feature Set
% ══════════════════════════════════════════════════════════════

\part{The Feature Set}

\input{chapters/ch03-har-core}
\input{chapters/ch04-asymmetry-jumps}
\input{chapters/ch05-options-implied}
\input{chapters/ch06-microstructure}
\input{chapters/ch07-cross-asset}
\input{chapters/ch08-feature-composition}

% ══════════════════════════════════════════════════════════════
% Part III — Models
% ══════════════════════════════════════════════════════════════

\part{Models}

\input{chapters/ch09-lightgbm}
\input{chapters/ch10-lstm-intraday}
\input{chapters/ch11-ensemble}
\input{chapters/ch12-rashomon}

% ══════════════════════════════════════════════════════════════
% Part IV — Making It Work
% ══════════════════════════════════════════════════════════════

\part{Making It Work}

\input{chapters/ch13-evaluation}
\input{chapters/ch14-complete-pipeline}

\bibliographystyle{plainnat}
\bibliography{references}

\end{document}
```

- [ ] **Step 2: Verify compilation scaffolding**

Create placeholder chapter files so main.tex compiles:

```bash
for ch in ch01-what-we-forecast ch02-our-data ch03-har-core ch04-asymmetry-jumps ch05-options-implied ch06-microstructure ch07-cross-asset ch08-feature-composition ch09-lightgbm ch10-lstm-intraday ch11-ensemble ch12-rashomon ch13-evaluation ch14-complete-pipeline; do
  echo "\\chapter{Placeholder}" > "guides/vol-project-ref/chapters/${ch}.tex"
done
```

- [ ] **Step 3: Test compilation**

```bash
cd guides/vol-project-ref && pdflatex -interaction=nonstopmode main.tex
```

Expected: Compiles with no errors. PDF has title page, TOC, and 14 placeholder chapters.

- [ ] **Step 4: Commit scaffold**

```bash
git add guides/vol-project-ref/
git commit -m "docs(vol-project-ref): scaffold guide structure with preamble and placeholders"
```

---

## Chunk 2: Part I -- The Project (Chapters 1-2)

These two chapters set context for everything else. Write them first.

### Task 5: Write Chapter 1 -- What We're Forecasting

**Files:**
- Create: `guides/vol-project-ref/chapters/ch01-what-we-forecast.tex`
- Read for content: `notes/features/optimal-feature-set.md` (architecture diagram, implementation order, success criteria)

**Target: ~3 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Opening paragraph:** One sentence defining RV (sum of squared intraday returns). State the target: log RV_{t+h} for h = 1, 5, 22 days.

2. **Section: The Universe.** Table with our 34 symbols (30 mega-caps + 4 ETFs + E-mini), 11.3 years of history.

3. **Section: Success Criteria.** 30-80 bps QLIKE improvement over HARQ baselines, plus economic-value test. State the QLIKE metric briefly (formal definition is in Ch 13).

4. **Section: The High-Level Pipeline.** TikZ flow diagram:
   ```
   Raw Data -> Feature Engineering -> [LightGBM branch / LSTM branch] -> Ensemble Blend -> Forecast -> Evaluation
   ```
   Use `flowblock` and `arrow` TikZ styles from the preamble.

5. **`keyidea` box:** "The feature set you choose matters more than the model you choose."

**Does NOT include:** Why vol matters to GS. History of vol modeling. General motivation.

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

Follow the per-chapter quality pipeline defined above.

---

### Task 6: Write Chapter 2 -- Our Data

**Files:**
- Create: `guides/vol-project-ref/chapters/ch02-our-data.tex`
- Read for content: `notes/data-access.md`, `notes/features/optimal-feature-set.md` (GS vs public data table)

**Target: ~4 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Data Sources.** `booktabs` table with 6 rows:

   | Data Source | Granularity | History | What It Enables | Key Constraint |
   |---|---|---|---|---|
   | Tick-level RV (34 symbols) | L1 tick | 11.3y | RV at any frequency, RQ, jumps, semivariances | -- |
   | Daily OHLCV (34 + VIX) | Daily | 11.3y | HAR baselines, ML training | No intraday structure |
   | E-mini L2 depth | L2 (~4M ticks/day) | 11.3y | OBI, depth ratio, VPIN, LSTM input | E-mini ONLY |
   | SPX IV surface (Marquee) | Full tenor x strike | 11.3y | VRP, skew, term structure, butterfly | SPX only |
   | VIX term structure | Daily | 11.3y | Regime detection, contango/backwardation | -- |
   | Cross-asset | Mixed | 11.3y | Spillover features, macro regime | Daily for some |

2. **Section: GS Edge vs. Public Data.** `booktabs` table:

   | Capability | Our Data | Public Alternative | Edge |
   |---|---|---|---|
   | RV estimation | Tick-level, 34 symbols | 5-min returns (TAQ/Oxford-Man) | Precise RQ, jump detection |
   | Options surface | Full SPX tenor x strike (Marquee) | VIX only | Full surface derivatives |
   | Microstructure depth | E-mini L2 | L1 quotes only | OBI at depth levels 2-5 |
   | Cross-asset sync | Same tick timestamp | Daily closes only | Intraday lead-lag detection |
   | Panel breadth | 30 mega-caps + 4 ETFs + E-mini | 1 index or 29 DJIA | Graph models, sector structure |

   Source: `optimal-feature-set.md` "What GS Data Uniquely Enables" section.

3. **Section: Constraints That Shape Decisions.** Short paragraph:
   - L2 is E-mini only -> microstructure depth features only for the index
   - IV surface is SPX only -> options features are market-wide regime signals, not stock-specific
   - These constraints directly determine which features apply to which assets

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

## Chunk 3: Part II -- Feature Layers (Chapters 3-7)

These 5 chapters are independent of each other. They can be written by parallel sub-agents. Each covers one feature layer from `optimal-feature-set.md`.

**Shared source files for all feature chapters:**
- `notes/features/optimal-feature-set.md` (primary)
- `notes/features/har-components.md` (Ch 3)
- `notes/features/leverage-effect.md` + `notes/features/jump-detection.md` (Ch 4)
- `notes/features/implied-vol.md` (Ch 5)
- `notes/features/microstructure.md` (Ch 6)
- `notes/features/cross-asset.md` (Ch 7)

### Task 7: Write Chapter 3 -- HAR Core and Measurement Quality (Layer 0)

**Files:**
- Create: `guides/vol-project-ref/chapters/ch03-har-core.tex`
- Read: `notes/features/optimal-feature-set.md` (Layer 0 section), `notes/features/har-components.md`

**Target: ~5 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: The Five Foundation Features.** `booktabs` table with columns: Feature, What It Is, What It Does. Rows: log RV daily, log RV weekly, log RV monthly, Realized Quarticity (RQ), RQ interaction. Content directly from optimal-feature-set.md Layer 0 table.

2. **Section: The HARQ Mechanism.** TikZ diagram showing the shrinkage: on a noisy day (high RQ), model trusts weekly/monthly more; on a clean day (low RQ), it trusts the daily reading. Use a simple flowchart or dual-panel illustration. Prose: 2-3 sentences explaining the mechanism. State that HARQ with 5 features beats ML models that skip noise-awareness.

3. **Section: Baseline Performance.** "These 5 features alone explain 40-60% of next-day log-RV variation." State what to compute from our data (RQ requires tick-level returns; we have them for all 34 symbols).

4. **`warning` box: "Work in log-RV space."** Raw RV is right-skewed with heavy tails; log-RV is approximately Gaussian. Affects loss functions, residual diagnostics, and model comparison.

5. **`keyidea` box:** "RQ interaction is the single most important extension beyond baseline HAR. 5-15% QLIKE gain from one feature."

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 8: Write Chapter 4 -- Asymmetric Volatility (Layer 1)

**Files:**
- Create: `guides/vol-project-ref/chapters/ch04-asymmetry-jumps.tex`
- Read: `notes/features/optimal-feature-set.md` (Layer 1), `notes/features/leverage-effect.md`, `notes/features/jump-detection.md`

**Target: ~4 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Features.** `booktabs` table with columns: Feature, What It Is, What It Does, Horizon. 6 rows: RS- daily, RS+ daily, RS- weekly, signed negative jumps (J-), continuous variation (C), jump variation (J). Content from optimal-feature-set.md Layer 1 table.

2. **Section: The Leverage Effect.** 2-3 factual sentences: negative returns increase future vol more than positive returns. Strongest for equity indices and E-mini. Varies by sector for individual stocks (financials > tech).

3. **Section: Continuous vs. Jump Variation.** Contrast: continuous variation is highly persistent (ACF ~0.6-0.7) and drives forecasts. Jump variation is nearly unpredictable (ACF ~0.0-0.1) but signals regime breaks. Different roles in the model.

4. **Section: Cumulative Performance.** Layers 0+1 = ~70% of achievable accuracy with 11 features. State what to compute: semivariances and jumps from tick-level data at 5-min frequency, jump threshold via Lee-Mykland test.

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 9: Write Chapter 5 -- Options-Implied Features (Layer 2)

**Files:**
- Create: `guides/vol-project-ref/chapters/ch05-options-implied.tex`
- Read: `notes/features/optimal-feature-set.md` (Layer 2), `notes/features/implied-vol.md`

**Target: ~5 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Features.** `booktabs` table with columns: Feature, What It Is, Horizon Impact. 9 rows: ATM IV (30-day), VRP, 25-delta Risk Reversal, Term Structure Slope, Butterfly, VVIX, VIX Term Structure, IV-RV Gap, Event-Implied Vol. Content from optimal-feature-set.md Layer 2 table.

2. **Section: Horizon Dependence.** This is the critical insight. TikZ bar chart or annotated diagram showing: at 1-day, options add 1-3% QLIKE; at 1w-1m, they add 5-10%. Prose: options embed forward-looking event information (FOMC, earnings, macro) that past RV cannot see.

3. **Section: What We Compute.** Full surface from Marquee ERDVOL_PERCENT_STANDARD. Can compute any surface-derived feature (arbitrary delta, tenor interpolation, curvature). Constraint: SPX surface only; for single-stock vol, these are market-wide regime signals.

4. **Section: Cumulative Performance.** Layers 0-2 = ~85% of achievable accuracy with 20 features.

5. **`keyidea` box:** "ML's genuine advantage over HAR grows with forecast horizon. At h=1, HAR ties ML. At h=5 and h=22, ML with options features gives 10-20% QLIKE improvement."

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 10: Write Chapter 6 -- Microstructure Features (Layer 3)

**Files:**
- Create: `guides/vol-project-ref/chapters/ch06-microstructure.tex`
- Read: `notes/features/optimal-feature-set.md` (Layer 3), `notes/features/microstructure.md`

**Target: ~5 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Features.** `booktabs` table with columns: Feature, What It Is, Evidence. 9 rows: price acceleration, WAP log returns, OBI, depth ratio, market urgency, bid-ask spread dynamics, signed volume flow, sub-window RV ratio, VPIN. Content from optimal-feature-set.md Layer 3 table.

2. **Section: The Optiver Evidence.** What top Optiver solutions actually used. Price acceleration was the single most predictive micro feature. Sub-window aggregations (first 5 min vs last 5 min) outperformed whole-window. LightGBM dominated 4:1 over NNs on this data.

3. **Section: Engineering Principle.** For each base quantity, compute {level, change, z-score}. Trees handle redundancy via splits.

4. **Section: Data Constraints.** L2 depth is E-mini only. Equities + ETFs get L1 features only (price acceleration, WAP returns, spread dynamics). Connection to LSTM: this is the data that feeds the intraday deep learning module (Ch 10).

5. **`warning` box: "Lookahead Bias."** Microstructure features computed on the full day use information up to market close. Features for predicting RV_{t+1} must use only information available at time t. Timestamp alignment is critical.

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 11: Write Chapter 7 -- Cross-Asset Spillovers (Layer 4)

**Files:**
- Create: `guides/vol-project-ref/chapters/ch07-cross-asset.tex`
- Read: `notes/features/optimal-feature-set.md` (Layer 4), `notes/features/cross-asset.md`

**Target: ~4 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Features.** `booktabs` table with columns: Feature, What It Is, Mechanism. 8 rows: treasury slope change, credit spread momentum, FX vol (USD/JPY), commodity vol (CL, GC), DY Spillover Index, sector-mean RV, VIX-equity corr regime, cross-asset RV rank. Content from optimal-feature-set.md Layer 4 table.

2. **Section: Impact.** 1-5% QLIKE improvement, concentrated in regime transitions. These features matter most exactly when forecasts are most valuable and hardest to get right.

3. **Section: Graph-HAR.** Neighbor-weighted RV term: gamma * sum W_{jk} * RV_{k,t}. Captures how AAPL's vol tomorrow depends on MSFT's vol today. Weight matrix can be correlation-based (simple) or learned (GNN). TikZ diagram showing a small network of assets with weighted edges and RV flow.

4. **Section: GS Advantage.** Synchronized tick data across asset classes. Intraday lead-lag relationships invisible at daily frequency.

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

## Chunk 4: Part II Synthesis + Part III Models (Chapters 8-12)

### Task 12: Write Chapter 8 -- Feature Composition and Selection

**Files:**
- Create: `guides/vol-project-ref/chapters/ch08-feature-composition.tex`
- Read: `notes/features/optimal-feature-set.md` (Layers 5-7, diminishing returns, horizon table, implementation recommendations), `notes/features/calendar-events.md`

**Depends on:** Ch 3-7 (needs to reference cumulative layer performance).

**Target: ~6-7 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Calendar, Memory, and Sentiment (Layers 5-7).**
   - Calendar features: `booktabs` table with rows for FOMC indicator, NFP/CPI, OpEx, quarter-end, earnings proximity, event-implied vol, time-of-day, day-of-week. One column for "What It Is", one for "When It Matters."
   - Memory features: table with fractionally differenced RV (d ~ 0.35-0.45), rolling Hurst exponent, vol-of-vol, regime duration. Brief explanation of each.
   - Sentiment features: FinBERT news sentiment, negative news count. 1-3% QLIKE in crises only.
   - Summary: individually weak, collectively additive. Last 5% of achievable accuracy. Trees pick them up naturally.

2. **Section: The Diminishing Returns Curve.** TikZ bar chart or stacked area chart:
   - Layer 0 (5 features): ~55%
   - + Layer 1 (11 features): ~70%
   - + Layer 2 (20 features): ~85%
   - + Layers 3-4 (40 features): ~95%
   - + Layers 5-7 (80-120 features): 100%

3. **Section: Feature Priority by Forecast Horizon.** `booktabs` table:

   | Horizon | Dominant Features | Where ML Adds Value |
   |---|---|---|
   | Intraday (10min-1hr) | Microstructure (L3) | Trees with 600+ features |
   | 1 day | HAR core (L0) + RQ + asymmetry (L1) | HARQ nearly optimal; ML adds ~5% |
   | 1 week | Options (L2) + cross-asset (L4) | VRP + skew: 5-10% over pure RV |
   | 1 month | VRP (L2) + macro (L4) + Hurst (L6) | Options have max advantage |

4. **Section: Feature Engineering Principles.**
   - {level, change, z-score} for each base quantity. Triples feature count. Captures state, direction, unusualness.
   - Horizon-dependent selection: drop micro at monthly, drop calendar at intraday.
   - Trees handle redundancy via splits. No multicollinearity concern.

5. **`keyidea` box:** "The feature set matters more than the model. Layers 0-2 get 85% with 20 features and Ridge regression. The remaining 15% requires 60-100 more features and careful model architecture."

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 13: Write Chapter 9 -- LightGBM for Tabular Volatility

**Files:**
- Create: `guides/vol-project-ref/chapters/ch09-lightgbm.tex`
- Read: `notes/features/optimal-feature-set.md` (architecture section, Optiver config), `notes/research-journal.md` (model architecture decision section)

**Target: ~4 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: What Goes In.** ~80-120 engineered features from Layers 0-7. Brief recap table showing feature count per layer.

2. **Section: Configuration.** Reference config table from Optiver 91st place (well-documented):

   | Parameter | Value | Notes |
   |---|---|---|
   | Learning rate | 0.05 | |
   | Max leaves | 255 | |
   | Min data per leaf | 255 | |
   | Num estimators | 10,000 | With early stopping |
   | Early stopping rounds | 400 | |
   | Boosting type | DART | |
   | Objective | Custom QLIKE | Not built-in; requires custom objective + eval function |

3. **Section: SHAP Interpretability.** SHAP values for feature importance and interaction effects. Required for GS presentation and model defense. Note: single-model importance (gain, permutation, SHAP) is unstable across refits due to feature redundancy. This motivates the Rashomon analysis (Ch 12).

4. **`warning` box: "Baseline First."** Choice of fitting scheme for HAR matters more than ML model choice (Wilms et al. 2024). A properly-fitted HAR baseline (OLS with Newey-West standard errors) is essential before claiming ML improvement.

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 14: Write Chapter 10 -- LSTM for Intraday Sequences

**Files:**
- Create: `guides/vol-project-ref/chapters/ch10-lstm-intraday.tex`
- Read: `notes/features/optimal-feature-set.md` (architecture section), `notes/research-journal.md` (model architecture section), `notes/features/microstructure.md`

**Target: ~4 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Input.** Full-day E-mini L2 tick sequences. 5-min or 1-min return bars with LOB snapshots per bar. ~4M ticks/day compressed into structured sequences.

2. **Section: Architecture.** TikZ pipeline diagram:
   ```
   E-mini L2 ticks -> 5-min bars + LOB snapshots -> LSTM/TCN -> next-day RV forecast -> blend (Ch 11)
   ```
   Numbered steps:
   1. Small LSTM or TCN on intraday E-mini sequences
   2. Input: 5-min return bars within each trading day, with LOB snapshot features
   3. Output: independent next-day RV forecast
   4. Forecast blended with LightGBM at prediction level (Ch 11)
   5. Alternative to test: extract last-layer embedding into LightGBM as features. Competition evidence favors prediction-level blending, but compare both on our data.

3. **Section: Why DL Here.** 4M ticks/day is too rich for hand-engineered aggregations alone. Temporal order within the day matters (acceleration patterns, depth shifts). Optiver had 10-min windows (short sequences); we have full-day sequences for next-day prediction.

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 15: Write Chapter 11 -- The Ensemble

**Files:**
- Create: `guides/vol-project-ref/chapters/ch11-ensemble.tex`
- Read: `notes/features/optimal-feature-set.md` (architecture diagram)

**Depends on:** Ch 9, Ch 10 (references both branches).

**Target: ~3 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Architecture.** Reproduce the complete architecture diagram from optimal-feature-set.md as a TikZ figure:
   ```
   FINAL FORECAST: sigma^2_{t+h}
          |
   Ensemble: weighted blend
       /           \
   LightGBM        LSTM/TCN
   (Layers 0-7     (E-mini L2
    tabular)        intraday)
       |               |
   80-120 features   Raw 5-min bars
   ```
   Use `flowblock` and `arrow` styles. Show both branches converging.

2. **Section: Prediction-Level Blending.** Blend model outputs, NOT feature-level stacking (NN embeddings as tree inputs). Optiver and AmEx competition evidence confirms blending outputs beats feature-level fusion.

3. **Section: Why Two Branches.** LightGBM handles tabular features. LSTM handles sequential microstructure. Each model gets the data format it handles best. 2-3 sentences, no more.

4. **`keyidea` box:** "Blend predictions, not features. Each model gets the data format it handles best; combining their forecasts outperforms feeding one model's internals into the other."

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 16: Write Chapter 12 -- Interpretable Trees and Rashomon Analysis

**Files:**
- Create: `guides/vol-project-ref/chapters/ch12-rashomon.tex`
- Read: `notes/features/optimal-feature-set.md` (Rashomon findings sections)

**Target: ~4 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Optimal Decision Trees.** What to build: `STreeDPiecewiseLinearRegressor`, depth 4-5, elastic-net leaves, 8-32 leaves. Trained on same features as LightGBM. Expected accuracy: ~2-5% higher MSE than tuned LightGBM, but comfortably beats HAR (~10% better). A single inspectable tree.

2. **Section: Rashomon Analysis Pipeline.** TikZ flow diagram showing the 4 steps:
   1. TreeFARMS/RESPLIT: construct set of all near-optimal trees (within epsilon=2% MSE of optimum)
   2. RID (Donnelly et al. 2023): stable feature importance across the Rashomon set
   3. Variable Importance Clouds: classify features as essential, interchangeable, or useless
   4. Rolling-window Rashomon sets intersected across regimes for regime-stable selection

3. **Section: What This Tells Us.** Bullet list:
   - Which features are genuinely important vs. accidentally selected
   - Which features are substitutes (VIX, VVIX, ATM IV, IV-RV spread)
   - Prediction multiplicity: range of forecasts across defensible models (useful for risk reporting)
   - Post-hoc constraint satisfaction (monotone in VIX, exclude flagged features) without retraining

4. **Section: Evaluation.** Walk-forward MSE, QLIKE, MAE; DM tests vs HAR/HARQ/LightGBM; Rashomon prediction range during regime breaks (Mar-2020, Volmageddon). How to measure whether the interpretable tree's accuracy trade-off is acceptable.

5. **Section: Novelty.** No published paper has applied Rashomon methods to any financial time-series problem. Closest: credit risk (FICO HELOC) and criminal justice (COMPAS).

5. **`keyidea` box:** "Rashomon analysis answers: are my features robustly important, or did my model just pick one out of several interchangeable options? This is the novel research contribution."

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

## Chunk 5: Part IV -- Making It Work + Final Assembly (Chapters 13-14)

### Task 17: Write Chapter 13 -- Evaluation

**Files:**
- Create: `guides/vol-project-ref/chapters/ch13-evaluation.tex`
- Read: `notes/features/optimal-feature-set.md` (evaluation section)

**Target: ~4 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: Metrics.** `booktabs` table:

   | Metric | What It Measures | Role |
   |---|---|---|
   | QLIKE | Quasi-likelihood loss; penalizes under-prediction | Primary |
   | MSE | Mean squared error on log-RV | Secondary |
   | MAE | Mean absolute error on log-RV | Robustness check |
   | Diebold-Mariano test | Significance of pairwise forecast differences | "Is A better than B?" |
   | Model Confidence Set | Set of models not significantly worse than best | "Which models are top tier?" |

   Include the QLIKE formula: QLIKE = (1/T) * sum(sigma_hat^2 / sigma^2 - log(sigma_hat^2 / sigma^2) - 1). Brief: penalizes relative errors, not absolute.

2. **Section: Validation Protocol.**
   - Purged k-fold CV with embargo: standard CV leaks in time series. Purge removes observations near train/test boundary. Embargo adds a gap. TikZ diagram showing the purge + embargo zones on a time axis.
   - Walk-forward evaluation: train on rolling 5-year window, forecast next period, step forward.

3. **Section: Success Target.** 30-80 bps QLIKE improvement over HARQ baseline.

4. **`warning` box: "Train with QLIKE, Not MSE."** MSE is dominated by extreme vol days. QLIKE penalizes relative forecast errors. Zhang et al. (2025) confirms this matters substantially for model ranking. QLIKE requires custom LightGBM objective.

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 18: Write Chapter 14 -- The Complete Pipeline

**Files:**
- Create: `guides/vol-project-ref/chapters/ch14-complete-pipeline.tex`
- Read: `notes/features/optimal-feature-set.md` (implementation order, architecture), `notes/data-access.md`

**Depends on:** All previous chapters.

**Target: ~4 pages.**

- [ ] **Step 1: Write the chapter**

Sections:

1. **Section: End-to-End System Diagram.** Full TikZ pipeline diagram (largest diagram in the guide):
   ```
   Raw data sources (6 boxes: tick RV, OHLCV, E-mini L2, IV surface, VIX, cross-asset)
       |
   Feature computation (tick-level, daily, surface, cross-asset)
       |
   Feature store (~80-120 features)
       |
   ┌─────────────────┬──────────────────┐
   LightGBM branch   LSTM branch        Optimal tree branch
       |                  |                   |
   ┌───┴──────────────────┴───────────────────┘
   Ensemble blend
       |
   Forecast: log RV_{t+h}
       |
   Evaluation (QLIKE, DM, MCS)
   ```

2. **Section: Implementation Order.** Numbered steps (each independently reportable):
   1. HARQ + SHAR baseline (Layers 0-1, 11 features, OLS/Ridge)
   2. Add options layer (Layer 2, 20 total features, LightGBM)
   3. Add cross-asset + spillover (Layer 4, 30 features)
   4. E-mini microstructure LSTM module (Layer 3, separate component)
   5. Polish: calendar + roughness + sentiment (Layers 5-7, full 80-120 features)
   6. Rashomon analysis on final feature set

3. **Section: Re-training and Monitoring.** Weekly on rolling 5-year window. Monitor Rashomon-set drift.

4. **Section: Lookahead Bias Checklist.** `booktabs` table:

   | Source | Pitfall | Rule |
   |---|---|---|
   | Realized measures | Use intraday returns up to time t | Features for RV_{t+1} use only info <= t |
   | Microstructure | Full-day features include close | Careful timestamp alignment |
   | Options surface | Intraday surface changes | Use end-of-day surface for next-day prediction |
   | Cross-asset | Mixed frequencies | Ensure synchronization |

5. **`warning` box: "Lookahead Bias."** The single most common error in financial ML research. Every feature must be computable strictly before the forecast target period begins. When in doubt, add a one-day lag.

- [ ] **Step 2: Run quality pipeline (Passes A-E)**

---

### Task 19: Final Compilation and Full-Document Review

**Depends on:** All chapters complete (Tasks 5-18).

- [ ] **Step 1: Full compilation**

```bash
cd guides/vol-project-ref && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
```

Fix any compilation errors (undefined references, missing bib entries, etc.).

- [ ] **Step 2: Full-document visual review**

Dispatch sub-agent to read the complete PDF and check:
- Table of contents is correct and complete
- Part/chapter numbering is sequential
- All cross-references resolve (no "??" in the PDF)
- Consistent formatting across chapters (table styles, box usage, diagram styles)
- No orphaned pages or awkward page breaks
- Diagrams render correctly throughout

- [ ] **Step 3: Full-document brevity review**

Dispatch sub-agent to read the complete PDF end-to-end and flag:
- Any remaining theory creep or justification bloat across the full document
- Repetition between chapters (e.g., same fact stated in Ch 3 and Ch 8)
- Inconsistent terminology (same concept called different names in different chapters)

- [ ] **Step 4: Fix issues and recompile**

Apply all fixes. Recompile. Verify clean.

- [ ] **Step 5: Final commit**

```bash
git add guides/vol-project-ref/
git commit -m "docs(vol-project-ref): complete 14-chapter project reference guide"
```

---

## Parallelism Map

Tasks that can run as parallel sub-agents:

| Batch | Tasks | Why Parallel |
|---|---|---|
| 1 | Task 5, Task 6 | Ch 1 and Ch 2 are independent |
| 2 | Tasks 7, 8, 9, 10, 11 | Ch 3-7 are independent feature layers |
| 3 | Task 12, Task 13, Task 14 | Ch 8 depends on Ch 3-7. Ch 9 and Ch 10 are independent of Ch 8. All three can start once Batch 2 completes. |
| 4 | Task 15, Task 16, Task 17 | Ch 11 depends on Ch 9-10 (Batch 3). Ch 12 and Ch 13 are independent of each other and of Ch 11. All three can start once Batch 3 completes. |
| 5 | Task 18 | Ch 14 depends on all previous chapters |
| 6 | Task 19 | Final assembly depends on all |

Optimal execution with sub-agents: 6 sequential batches, with up to 5 parallel agents in Batch 2.
