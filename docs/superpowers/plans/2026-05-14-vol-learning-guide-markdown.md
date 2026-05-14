# Vol Learning Guide -- Markdown Conversion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create faithful word-for-word markdown copies of all 18 vol-learning-guide LaTeX chapters for LLM consumption, with TikZ diagrams recreated as Mermaid and worked examples omitted.

**Architecture:** 18 independent `.tex` -> `.md` conversions plus an INDEX.md master file. Each chapter is read from `vol-learning-guide/chapters/`, converted following strict fidelity rules, and written to `vol-learning-guide/markdown/`. Chapters are grouped into 6 batches by part for parallel execution.

**Tech Stack:** Markdown (GitHub-flavored), Mermaid diagrams, LaTeX math notation

**Spec:** `docs/superpowers/specs/2026-05-14-vol-learning-guide-markdown-design.md`

---

## Conversion Rules (apply to every chapter task)

These rules are non-negotiable. Every chapter conversion must follow them:

1. **Word-for-word fidelity.** Every sentence in the LaTeX source appears in the markdown output, except worked examples and the two omitted Ch17 subsections.
2. **Math preserved exactly.** Inline `$...$`, display `$$...$$`. Expand `\RV` to `\operatorname{RV}`. Keep `\operatorname{}`, `\text{}`, `\mathbb{}`, `\boldsymbol{}`, `\bigl`, `\bigr`, `\tfrac`, `\dfrac` as-is.
3. **Box rendering.** All tcolorbox environments become blockquotes with bold type labels:
   - `\begin{prereq}[Title]` -> `> **Prereq: Title**`
   - `\begin{intuition}[Title]` -> `> **Intuition: Title**`
   - `\begin{keyidea}[Title]` -> `> **Key Idea: Title**`
   - `\begin{keyresult}[Title]` -> `> **Key Result: Title**`
   - `\begin{definition}[Title]` -> `> **Definition: Title**`
   - `\begin{warning}[Title]` -> `> **Warning: Title**`
   - `\begin{projectconnection}[Title]` -> `> **Project Connection: Title**`
   - `\begin{application}[Title]` -> `> **Application: Title**`
   - `\begin{workedexample}{Title}` -> **Omit entirely**
   - Multi-paragraph box content: `>` continuation on every line, including `$$` blocks inside boxes.
4. **Worked example omission.** Remove cleanly with no gap or marker. If surrounding prose references the worked example directly ("as the worked example below shows"), rewrite the minimum necessary to remove the dangling reference.
5. **Citations.** `\citet{Corsi2009}` -> `Corsi (2009)`. `\citep{Bollerslev2016}` -> `(Bollerslev et al., 2016)`. Look up the actual author names and year from the citation key or surrounding text.
6. **Cross-references.** `Chapter~\ref{ch:garch}` -> `[Chapter 5](ch05-garch-family.md)`. `Section~\ref{sec:har-model}` -> "Section 6.2" (descriptive). `Equation~\ref{eq:har}` -> "the HAR equation above" or "Equation 6.1". `Figure~\ref{fig:hmh-diagram}` -> "the diagram above".
7. **Tables.** `\begin{tabular}` -> GFM `|` tables. `booktabs` styling (toprule/midrule/bottomrule) -> header separator row. Preserve all data exactly.
8. **Lists.** `\begin{itemize}` -> `- ` bullet lists. `\begin{enumerate}` -> `1. ` numbered lists.
9. **Diagrams -- Mermaid.** TikZ flowcharts, conceptual diagrams, architecture diagrams, decision trees -> Mermaid fenced blocks. Use `flowchart LR` for pipelines, `flowchart TD` for hierarchies. Color: blue=data, green=computation, orange=models. Thick arrows (`==>`) for primary flows, thin (`-->`) for secondary, dashed (`-.->`) for optional/feedback.
10. **Diagrams -- Prose.** pgfplots (`\begin{axis}`) charts (scatter, histogram, ACF, distribution curves) -> italicized prose paragraph: `*[Figure: description. Key value 1. Key value 2.]*`
11. **No em dashes.** Use commas, semicolons, or "to" ranges (e.g., "40--60" stays as "40--60" in markdown since that's a number range, not an em dash).
12. **Chapter heading.** Each file starts with `# Chapter N: Title` matching the LaTeX `\chapter{}`.
13. **Section headings.** `\section{}` -> `## `, `\subsection{}` -> `### `, `\subsubsection{}` -> `#### `.
14. **`\emph{}` and `\textbf{}`** -> `*italic*` and `**bold**`.
15. **`\footnote{}`** -> inline parenthetical or appended as a note.

---

## Per-Chapter Conversion Pipeline

Each chapter goes through these steps:

### Step 1: Read and Inventory

Read the full `.tex` source. Count and list:
- Sections and subsections (these become the heading structure)
- Box environments by type (prereq, intuition, keyidea, etc.)
- TikZ diagrams (classify as Mermaid-convertible or pgfplots-prose)
- Worked examples to skip
- Cross-references to other chapters (need correct filenames)
- Any `\RV` or other custom commands to expand

### Step 2: Convert

Write the complete `.md` file following all conversion rules above. Work section by section through the LaTeX source. Do not skip, summarize, or reorganize any content.

### Step 3: Verify

Check the output for:
- **Completeness:** Every section heading from the LaTeX appears in the markdown. Every non-workedexample box is present with correct type label.
- **Math integrity:** All `$` and `$$` are properly paired. No bare backslashes or broken LaTeX commands.
- **Mermaid validity:** Every Mermaid block has matching ``` fences and valid syntax (no unclosed subgraphs, no unescaped special characters in node labels).
- **Cross-references:** Links to other chapter files use correct filenames from the file structure.
- **Clean omission:** No "[removed]" markers, no orphaned "as shown below" references to deleted worked examples.

### Step 4: Commit

```bash
git add vol-learning-guide/markdown/chNN-name.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter N -- Title"
```

---

## Chapter Reference Table

| Ch | Source File | Output File | Lines | TikZ | pgfplots | Boxes | WE (skip) |
|---|---|---|---|---|---|---|---|
| 1 | `01-returns-variance-volatility.tex` | `ch01-returns-variance-volatility.md` | 850 | 4 | 5 | 39 | 3 |
| 2 | `02-realized-volatility.tex` | `ch02-realized-volatility.md` | 773 | 4 | 3 | 34 | 1 |
| 3 | `03-microstructure-noise.tex` | `ch03-microstructure-noise.md` | 1070 | 7 | 7 | 37 | 1 |
| 4 | `04-jumps-continuous-variation.tex` | `ch04-jumps-continuous-variation.md` | 915 | 4 | 5 | 36 | 2 |
| 5 | `05-garch-family.tex` | `ch05-garch-family.md` | 1008 | 4 | 2 | 36 | 2 |
| 6 | `06-har-model.tex` | `ch06-har-model.md` | 918 | 4 | 1 | 45 | 1 |
| 7 | `07-rough-volatility.tex` | `ch07-rough-volatility.md` | 815 | 4 | 7 | 29 | 2 |
| 8 | `08-options-vol-surface.tex` | `ch08-options-vol-surface.md` | 1369 | 6 | 5 | 63 | 5 |
| 9 | `09-variance-risk-premium.tex` | `ch09-variance-risk-premium.md` | 899 | 3 | 2 | 37 | 3 |
| 10 | `10-feature-engineering.tex` | `ch10-feature-engineering.md` | 1568 | 7 | 2 | 86 | 4 |
| 11 | `11-tree-methods-vol.tex` | `ch11-tree-methods-vol.md` | 990 | 4 | 0 | 28 | 2 |
| 12a | `12-rashomon-interpretable-trees.tex` | `ch12-rashomon-interpretable-trees.md` | 1056 | 1 | 0 | 26 | 2 |
| 12b | `12-deep-learning-vol.tex` | `ch12b-deep-learning-vol.md` | 918 | 6 | 0 | 40 | 2 |
| 13 | `13-hybrid-ensemble.tex` | `ch13-hybrid-ensemble.md` | 1335 | 5 | 0 | 36 | 1 |
| 14 | `14-multivariate-volatility.tex` | `ch14-multivariate-volatility.md` | 1143 | 7 | 0 | 42 | 3 |
| 15 | `15-spillovers-connectedness.tex` | `ch15-spillovers-connectedness.md` | 804 | 4 | 1 | 25 | 1 |
| 16 | `16-forecast-evaluation.tex` | `ch16-forecast-evaluation.md` | 1212 | 4 | 1 | 61 | 5 |
| 17 | `17-applications-projects.tex` | `ch17-applications-projects.md` | 214 | 0 | 0 | 12 | 1 |
| **Total** | | | **17,857** | **78** | **41** | **712** | **41** |

**Note on pgfplots:** The `\begin{axis}` environment always lives inside a `\begin{tikzpicture}`. When a tikzpicture contains an axis, render it as a prose description (not Mermaid). When a tikzpicture has no axis, render it as Mermaid. Some tikzpictures may contain both flowchart elements and an axis; use judgment to pick the best representation.

---

## Chunk 1: Scaffold

### Task 1: Create directory and verify structure

**Files:**
- Create: `vol-learning-guide/markdown/`

- [ ] **Step 1: Create the markdown directory**

```bash
mkdir -p vol-learning-guide/markdown
```

- [ ] **Step 2: Verify the directory exists**

```bash
ls -la vol-learning-guide/markdown/
```

Expected: empty directory.

- [ ] **Step 3: Commit scaffold**

```bash
git add vol-learning-guide/markdown/.gitkeep
git commit -m "docs(vol-learning-guide): scaffold markdown directory"
```

Note: If git does not track empty directories, create the first chapter file instead and commit with it.

---

## Chunk 2: Part I -- What Is Volatility and How Do You Measure It? (Chapters 1-4)

These 4 chapters are independent. They can be converted by parallel sub-agents.

### Task 2: Convert Chapter 1 -- Returns, Variance, and Volatility

**Files:**
- Read: `vol-learning-guide/chapters/01-returns-variance-volatility.tex` (850 lines)
- Create: `vol-learning-guide/markdown/ch01-returns-variance-volatility.md`

**Inventory:** 4 TikZ diagrams (most contain pgfplots axes -- likely return distribution plots, variance illustration). 39 boxes (skip 3 workedexamples = 36 to convert). Heavy on definitions and intuition boxes for foundational concepts.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/01-returns-variance-volatility.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch01-returns-variance-volatility.md` following all conversion rules. This chapter introduces returns, variance, and volatility from first principles. Expect:
- Definitions of log returns, simple returns, variance, standard deviation, volatility
- pgfplots showing return distributions (convert to prose descriptions with key values)
- Many prereq, intuition, and definition boxes
- 3 worked examples to omit

- [ ] **Step 3: Verify output**

Run the verification checklist from the per-chapter pipeline above. Check that all 36 non-workedexample boxes are present, all diagrams are converted (Mermaid or prose), math is intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch01-returns-variance-volatility.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 1 -- Returns, Variance, and Volatility"
```

---

### Task 3: Convert Chapter 2 -- Realized Volatility

**Files:**
- Read: `vol-learning-guide/chapters/02-realized-volatility.tex` (773 lines)
- Create: `vol-learning-guide/markdown/ch02-realized-volatility.md`

**Inventory:** 4 TikZ diagrams (3 contain pgfplots -- likely RV time series, convergence plots). 34 boxes (skip 1 workedexample = 33 to convert). Core chapter defining RV, the target variable for the project.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/02-realized-volatility.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch02-realized-volatility.md`. Expect:
- Definition of realized variance (sum of squared intraday returns)
- Convergence of RV to integrated variance as sampling frequency increases
- pgfplots showing RV time series / convergence (prose descriptions)
- Definitions of RV, realized volatility, log-RV
- Cross-references to Chapter 1 (link to `ch01-returns-variance-volatility.md`)
- 1 worked example to omit

- [ ] **Step 3: Verify output**

Check all 33 boxes present, diagrams converted, math intact, cross-references use correct filenames.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch02-realized-volatility.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 2 -- Realized Volatility"
```

---

### Task 4: Convert Chapter 3 -- Microstructure Noise

**Files:**
- Read: `vol-learning-guide/chapters/03-microstructure-noise.tex` (1070 lines)
- Create: `vol-learning-guide/markdown/ch03-microstructure-noise.md`

**Inventory:** 7 TikZ diagrams (7 pgfplots axes -- this chapter is plot-heavy: signature plots, noise impact visualization, kernel estimator comparisons). 37 boxes (skip 1 workedexample = 36 to convert). Longest chapter in Part I.

**Special note:** All 7 diagrams likely contain pgfplots axes, so all will be prose descriptions rather than Mermaid. Pay attention to the signature plot description -- it's a key concept (RV plotted against sampling frequency showing the divergence at high frequencies).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/03-microstructure-noise.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch03-microstructure-noise.md`. Expect:
- Bid-ask bounce, tick-size discretization, stale quotes
- The volatility signature plot concept (key figure -- describe carefully in prose)
- Noise-robust estimators: two-scale, multi-scale, pre-averaging, realized kernel
- Heavy math content (kernel weights, pre-averaging functions)
- Cross-references to Chapter 2
- 1 worked example to omit

- [ ] **Step 3: Verify output**

Check all 36 boxes, all 7 diagrams described in prose with key values, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch03-microstructure-noise.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 3 -- Microstructure Noise"
```

---

### Task 5: Convert Chapter 4 -- Jumps and Continuous Variation

**Files:**
- Read: `vol-learning-guide/chapters/04-jumps-continuous-variation.tex` (915 lines)
- Create: `vol-learning-guide/markdown/ch04-jumps-continuous-variation.md`

**Inventory:** 4 TikZ diagrams (5 pgfplots axes -- jump detection visualization, BPV vs RV comparison, jump contribution plots). 36 boxes (skip 2 workedexamples = 34 to convert).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/04-jumps-continuous-variation.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch04-jumps-continuous-variation.md`. Expect:
- Bipower variation (BPV), continuous variation (C), jump variation (J)
- Jump detection tests (Barndorff-Nielsen & Shephard, Lee-Mykland)
- Signed jumps, truncated realized variance
- pgfplots showing jump detection output, BPV vs RV
- Cross-references to Chapters 2-3
- 2 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 34 boxes, diagrams described in prose, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch04-jumps-continuous-variation.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 4 -- Jumps and Continuous Variation"
```

---

## Chunk 3: Part II -- Forecasting Volatility with Classical Models (Chapters 5-7)

These 3 chapters are independent. Parallel sub-agents.

### Task 6: Convert Chapter 5 -- GARCH Family

**Files:**
- Read: `vol-learning-guide/chapters/05-garch-family.tex` (1008 lines)
- Create: `vol-learning-guide/markdown/ch05-garch-family.md`

**Inventory:** 4 TikZ diagrams (2 pgfplots -- likely conditional variance plots, news impact curves; 2 flowcharts). 36 boxes (skip 2 workedexamples = 34 to convert).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/05-garch-family.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch05-garch-family.md`. Expect:
- ARCH, GARCH(1,1), EGARCH, GJR-GARCH, FIGARCH
- News impact curves (likely pgfplots -- prose description)
- GARCH estimation (MLE), forecasting formulas
- Comparison diagrams (GARCH variants) -- these may be Mermaid-convertible
- Cross-references to Chapters 1-2
- 2 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 34 boxes, diagrams converted appropriately, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch05-garch-family.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 5 -- GARCH Family"
```

---

### Task 7: Convert Chapter 6 -- The HAR Model and Its Extensions

**Files:**
- Read: `vol-learning-guide/chapters/06-har-model.tex` (918 lines)
- Create: `vol-learning-guide/markdown/ch06-har-model.md`

**Inventory:** 4 TikZ diagrams (1 pgfplot; 3 conceptual/flow diagrams -- HMH diagram, HARQ mechanism, HAR extensions tree). 45 boxes (skip 1 workedexample = 44 to convert). Highest box density of any chapter.

**Special note:** The HMH diagram (Figure 6.1, three participant types feeding into market volatility) is a conceptual diagram that should convert well to Mermaid. The HARQ shrinkage mechanism diagram is similar to the one in the vol-project-ref ch03 -- use the same Mermaid pattern.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/06-har-model.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch06-har-model.md`. Expect:
- Heterogeneous Market Hypothesis
- HAR-RV model (the baseline equation)
- HAR extensions: HAR-J, HAR-CJ, SHAR, HARQ, HAR-RS
- The HARQ shrinkage mechanism (Mermaid diagram)
- HMH participant diagram (Mermaid)
- Many definition, intuition, and projectconnection boxes
- Cross-references to Chapters 2, 4, 5
- 1 worked example to omit

- [ ] **Step 3: Verify output**

Check all 44 boxes, at least 3 Mermaid diagrams, 1 prose plot description, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch06-har-model.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 6 -- The HAR Model and Its Extensions"
```

---

### Task 8: Convert Chapter 7 -- Rough Volatility

**Files:**
- Read: `vol-learning-guide/chapters/07-rough-volatility.tex` (815 lines)
- Create: `vol-learning-guide/markdown/ch07-rough-volatility.md`

**Inventory:** 4 TikZ diagrams (7 pgfplots axes -- this chapter is heavily plot-based: Hurst exponent estimation, fBM sample paths, roughness visualization, log-log regression plots). 29 boxes (skip 2 workedexamples = 27 to convert).

**Special note:** Like Ch 3, nearly all diagrams are pgfplots (sample paths, log-log regressions). All prose descriptions. Pay attention to the Hurst exponent estimation plots -- they need careful numerical descriptions.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/07-rough-volatility.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch07-rough-volatility.md`. Expect:
- Fractional Brownian motion, Hurst exponent
- The roughness finding (H ~ 0.1-0.15 for vol)
- RFSV model, rough Bergomi
- Fractional differencing for stationarity
- Many pgfplots (all prose descriptions with Hurst values, sample paths)
- Cross-references to Chapters 5-6
- 2 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 27 boxes, all diagrams described in prose with key numerical values, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch07-rough-volatility.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 7 -- Rough Volatility"
```

---

## Chunk 4: Part III -- The Volatility Surface and Options-Implied Information (Chapters 8-9)

These 2 chapters are independent. Parallel sub-agents.

### Task 9: Convert Chapter 8 -- Options and the Volatility Surface

**Files:**
- Read: `vol-learning-guide/chapters/08-options-vol-surface.tex` (1369 lines)
- Create: `vol-learning-guide/markdown/ch08-options-vol-surface.md`

**Inventory:** 6 TikZ diagrams (5 pgfplots -- volatility smile/skew plots, surface 3D, term structure; likely 1 conceptual diagram). 63 boxes (skip 5 workedexamples = 58 to convert). **Largest box count of any chapter.** Also the longest chapter outside Part IV.

**Special note:** This chapter has 5 worked examples to omit (the most of any chapter). Carefully check that prose around the omitted examples still reads naturally. The vol surface plots need careful prose descriptions (smile shape, skew steepness, term structure slope).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/08-options-vol-surface.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch08-options-vol-surface.md`. Expect:
- Black-Scholes basics (as context for IV)
- Implied volatility definition and extraction
- The volatility smile and skew
- Volatility surface (delta x tenor)
- Greeks relevant to vol trading
- Many definition and intuition boxes (58 total boxes)
- 5 pgfplots (smile, skew, surface, term structure) -- prose descriptions
- Cross-references to Chapters 1, 4, 5
- 5 worked examples to omit -- verify clean removal

- [ ] **Step 3: Verify output**

Check all 58 boxes, diagrams described in prose, math intact, no orphaned worked-example references.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch08-options-vol-surface.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 8 -- Options and the Volatility Surface"
```

---

### Task 10: Convert Chapter 9 -- Variance Risk Premium

**Files:**
- Read: `vol-learning-guide/chapters/09-variance-risk-premium.tex` (899 lines)
- Create: `vol-learning-guide/markdown/ch09-variance-risk-premium.md`

**Inventory:** 3 TikZ diagrams (2 pgfplots -- VRP time series, IV-RV gap; likely 1 conceptual diagram). 37 boxes (skip 3 workedexamples = 34 to convert).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/09-variance-risk-premium.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch09-variance-risk-premium.md`. Expect:
- VRP definition (IV^2 - realized variance)
- VRP as a forecasting feature
- Risk-neutral vs physical measure
- VIX as an IV proxy
- Cross-references to Chapters 2, 5, 8
- 3 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 34 boxes, diagrams converted, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch09-variance-risk-premium.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 9 -- Variance Risk Premium"
```

---

## Chunk 5: Part IV -- ML Methods for Volatility (Chapters 10-13, including both Ch 12 files)

5 chapters (4 tasks, since both ch12 files are separate tasks). These are independent. Parallel sub-agents.

### Task 11: Convert Chapter 10 -- Feature Engineering for Volatility

**Files:**
- Read: `vol-learning-guide/chapters/10-feature-engineering.tex` (1568 lines)
- Create: `vol-learning-guide/markdown/ch10-feature-engineering.md`

**Inventory:** 7 TikZ diagrams (2 pgfplots; 5 conceptual/flow diagrams -- feature pipeline, triple expansion, horizon selection). 86 boxes (skip 4 workedexamples = 82 to convert). **Highest box count AND longest chapter in the entire guide.**

**Special note:** This is the largest single conversion task. 82 boxes and 1568 lines require careful attention. The feature engineering pipeline diagrams should convert well to Mermaid. The triple expansion diagram ({level, change, z-score}) is an important conceptual diagram.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/10-feature-engineering.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch10-feature-engineering.md`. Expect:
- Feature engineering principles for vol forecasting
- The layer structure (Layers 0-7 from optimal-feature-set)
- Triple expansion: {level, change, z-score}
- Horizon-dependent feature selection
- Feature pipeline diagrams (Mermaid)
- pgfplots for feature importance / correlation (prose)
- Many projectconnection boxes tying to the GS project
- Cross-references to Chapters 2-9
- 4 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 82 boxes present with correct type labels, at least 5 Mermaid diagrams, 2 prose plot descriptions, math intact, cross-references correct.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch10-feature-engineering.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 10 -- Feature Engineering for Volatility"
```

---

### Task 12: Convert Chapter 11 -- Tree Methods for Volatility

**Files:**
- Read: `vol-learning-guide/chapters/11-tree-methods-vol.tex` (990 lines)
- Create: `vol-learning-guide/markdown/ch11-tree-methods-vol.md`

**Inventory:** 4 TikZ diagrams (0 pgfplots -- all are tree/architecture diagrams, perfect for Mermaid). 28 boxes (skip 2 workedexamples = 26 to convert).

**Special note:** All 4 diagrams are pure TikZ (no pgfplots), so all become Mermaid. Expect decision tree splitting diagrams, gradient boosting pipeline, LightGBM architecture.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/11-tree-methods-vol.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch11-tree-methods-vol.md`. Expect:
- Decision trees, random forests, gradient boosting
- LightGBM specifics (leaf-wise growth, DART)
- XGBoost vs LightGBM comparison
- Custom loss functions (QLIKE objective)
- SHAP interpretability
- 4 Mermaid diagrams (tree splits, boosting pipeline, architecture)
- Cross-references to Chapters 6, 10
- 2 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 26 boxes, 4 Mermaid diagrams with valid syntax, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch11-tree-methods-vol.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 11 -- Tree Methods for Volatility"
```

---

### Task 13: Convert Chapter 12a -- Rashomon and Interpretable Trees

**Files:**
- Read: `vol-learning-guide/chapters/12-rashomon-interpretable-trees.tex` (1056 lines)
- Create: `vol-learning-guide/markdown/ch12-rashomon-interpretable-trees.md`

**Inventory:** 1 TikZ diagram (0 pgfplots -- likely Rashomon pipeline flow, ideal for Mermaid). 26 boxes (skip 2 workedexamples = 24 to convert).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/12-rashomon-interpretable-trees.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch12-rashomon-interpretable-trees.md`. Expect:
- Optimal sparse decision trees (STreeD)
- Rashomon sets and the Rashomon effect
- TreeFARMS / RESPLIT enumeration
- Variable Importance Clouds, RID
- Rashomon pipeline diagram (Mermaid)
- Cross-references to Chapter 11
- 2 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 24 boxes, 1 Mermaid diagram, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch12-rashomon-interpretable-trees.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 12 -- Rashomon and Interpretable Trees"
```

---

### Task 14: Convert Chapter 12b -- Deep Learning for Volatility

**Files:**
- Read: `vol-learning-guide/chapters/12-deep-learning-vol.tex` (918 lines)
- Create: `vol-learning-guide/markdown/ch12b-deep-learning-vol.md`

**Inventory:** 6 TikZ diagrams (0 pgfplots -- all architecture/flow diagrams: LSTM cell, TCN, attention, encoder-decoder). 40 boxes (skip 2 workedexamples = 38 to convert).

**Special note:** All 6 diagrams are pure TikZ architecture diagrams. LSTM cell diagrams and TCN architectures may be complex to convert to Mermaid -- use subgraphs to represent gates and layers. If a diagram is too complex for Mermaid to represent faithfully, fall back to a detailed prose description.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/12-deep-learning-vol.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch12b-deep-learning-vol.md`. Expect:
- RNNs, LSTMs, GRUs
- LSTM cell diagram (complex -- Mermaid or detailed prose)
- Temporal Convolutional Networks (TCN)
- Attention mechanisms, transformers for time series
- Architecture diagrams (Mermaid with subgraphs)
- Cross-references to Chapters 10, 11
- 2 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 38 boxes, 6 diagrams converted (Mermaid or prose fallback), math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch12b-deep-learning-vol.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 12b -- Deep Learning for Volatility"
```

---

### Task 15: Convert Chapter 13 -- Hybrid and Ensemble Methods

**Files:**
- Read: `vol-learning-guide/chapters/13-hybrid-ensemble.tex` (1335 lines)
- Create: `vol-learning-guide/markdown/ch13-hybrid-ensemble.md`

**Inventory:** 5 TikZ diagrams (0 pgfplots -- all architecture diagrams: ensemble pipelines, stacking vs blending, two-branch architecture). 36 boxes (skip 1 workedexample = 35 to convert).

**Special note:** The ensemble architecture diagrams are similar to those in vol-project-ref ch11/ch16. Use the same Mermaid patterns (parallel branches converging to blend node).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/13-hybrid-ensemble.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch13-hybrid-ensemble.md`. Expect:
- Stacking vs blending vs bagging
- Feature-level vs prediction-level fusion
- The two-branch architecture (LightGBM + LSTM)
- Residual stacking
- Architecture diagrams (Mermaid -- parallel branches, convergence)
- Cross-references to Chapters 10, 11, 12a, 12b
- 1 worked example to omit

- [ ] **Step 3: Verify output**

Check all 35 boxes, 5 Mermaid diagrams, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch13-hybrid-ensemble.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 13 -- Hybrid and Ensemble Methods"
```

---

## Chunk 6: Part V -- Multivariate Volatility and Connectedness (Chapters 14-15)

These 2 chapters are independent. Parallel sub-agents.

### Task 16: Convert Chapter 14 -- Multivariate Volatility

**Files:**
- Read: `vol-learning-guide/chapters/14-multivariate-volatility.tex` (1143 lines)
- Create: `vol-learning-guide/markdown/ch14-multivariate-volatility.md`

**Inventory:** 7 TikZ diagrams (0 pgfplots -- all conceptual/architecture: covariance matrix structure, DCC pipeline, factor models). 42 boxes (skip 3 workedexamples = 39 to convert).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/14-multivariate-volatility.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch14-multivariate-volatility.md`. Expect:
- Realized covariance matrix
- DCC-GARCH, BEKK
- Factor models for covariance
- Curse of dimensionality in multivariate vol
- 7 Mermaid diagrams (covariance structure, DCC pipeline, factor decomposition)
- Cross-references to Chapters 2, 5, 6
- 3 worked examples to omit

- [ ] **Step 3: Verify output**

Check all 39 boxes, 7 Mermaid diagrams, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch14-multivariate-volatility.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 14 -- Multivariate Volatility"
```

---

### Task 17: Convert Chapter 15 -- Spillovers and Connectedness

**Files:**
- Read: `vol-learning-guide/chapters/15-spillovers-connectedness.tex` (804 lines)
- Create: `vol-learning-guide/markdown/ch15-spillovers-connectedness.md`

**Inventory:** 4 TikZ diagrams (1 pgfplot -- likely spillover index time series; 3 conceptual diagrams -- network graphs, VAR structure). 25 boxes (skip 1 workedexample = 24 to convert).

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/15-spillovers-connectedness.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch15-spillovers-connectedness.md`. Expect:
- Diebold-Yilmaz spillover index
- VAR-based variance decomposition
- Network connectedness measures
- Graph-HAR
- Network diagrams (Mermaid -- nodes with weighted edges)
- 1 pgfplot (spillover index time series -- prose)
- Cross-references to Chapters 6, 7, 14
- 1 worked example to omit

- [ ] **Step 3: Verify output**

Check all 24 boxes, 3 Mermaid diagrams + 1 prose plot, math intact.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch15-spillovers-connectedness.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 15 -- Spillovers and Connectedness"
```

---

## Chunk 7: Part VI -- Evaluation and Practice (Chapters 16-17)

These 2 chapters are independent. Parallel sub-agents.

### Task 18: Convert Chapter 16 -- Forecast Evaluation

**Files:**
- Read: `vol-learning-guide/chapters/16-forecast-evaluation.tex` (1212 lines)
- Create: `vol-learning-guide/markdown/ch16-forecast-evaluation.md`

**Inventory:** 4 TikZ diagrams (1 pgfplot -- likely loss function comparison; 3 conceptual/flow diagrams -- purged CV, walk-forward, MCS pipeline). 61 boxes (skip 5 workedexamples = 56 to convert). **Second-highest box count** (after Ch 10). **Ties with Ch 8 for most workedexamples to omit (5).**

**Special note:** 5 worked examples to omit. Carefully check that the evaluation methodology prose reads naturally without the computational walk-throughs.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/16-forecast-evaluation.tex`. List all sections, box environments, diagrams, and cross-references.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch16-forecast-evaluation.md`. Expect:
- Loss functions: MSE, MAE, QLIKE (formulas)
- Diebold-Mariano test
- Model Confidence Set (MCS)
- Purged k-fold CV with embargo (diagram -- Mermaid)
- Walk-forward evaluation (diagram -- Mermaid)
- Many definition and warning boxes
- Cross-references to Chapters 5, 6, 10, 11
- 5 worked examples to omit -- verify clean removal

- [ ] **Step 3: Verify output**

Check all 56 boxes, diagrams converted, math intact, no orphaned worked-example references.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch16-forecast-evaluation.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 16 -- Forecast Evaluation"
```

---

### Task 19: Convert Chapter 17 -- Applications and Projects

**Files:**
- Read: `vol-learning-guide/chapters/17-applications-projects.tex` (214 lines)
- Create: `vol-learning-guide/markdown/ch17-applications-projects.md`

**Inventory:** 0 TikZ diagrams. 12 boxes (skip 1 workedexample = 11 to convert). **Shortest chapter.** Two additional subsections to omit.

**Special note -- additional omissions:** Beyond the worked example, also omit:
- Section 18.2: Dealer Gamma
- Section 18.3: Five Project Directions

These are omitted because the project direction has already been decided. If surrounding prose references these sections, rewrite minimally to remove dangling references.

- [ ] **Step 1: Read and inventory the full chapter**

Read `vol-learning-guide/chapters/17-applications-projects.tex`. List all sections, identify sections 18.2 and 18.3 for omission.

- [ ] **Step 2: Convert to markdown**

Write `vol-learning-guide/markdown/ch17-applications-projects.md`. Expect:
- Remaining application content (whatever is not in the omitted sections)
- 11 boxes to convert
- No diagrams
- 1 worked example + 2 subsections to omit

- [ ] **Step 3: Verify output**

Check all 11 boxes, no omitted content leaking through, no orphaned cross-references.

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/markdown/ch17-applications-projects.md
git commit -m "docs(vol-learning-guide): markdown conversion of chapter 17 -- Applications and Projects"
```

---

## Chunk 8: Assembly

### Task 20: Write INDEX.md

**Files:**
- Create: `vol-learning-guide/markdown/INDEX.md`
- Read (for summaries): All 18 completed `.md` files in `vol-learning-guide/markdown/`

**Depends on:** All chapter tasks (Tasks 2-19) complete.

- [ ] **Step 1: Write INDEX.md**

Create `vol-learning-guide/markdown/INDEX.md` following the format from `guides/vol-project-ref/markdown/INDEX.md`:

```markdown
# Realized Volatility: Estimation, Forecasting, and ML

**A Learning Guide**

Ryan Vincent

These markdown files are a faithful word-for-word conversion of `vol-learning-guide/main.pdf`, with TikZ diagrams recreated as Mermaid. Worked examples are omitted. Intended for LLM consumption on restricted machines.

---

## Part I: What Is Volatility and How Do You Measure It?

| Ch. | Title | Summary |
|-----|-------|---------|
| [1](ch01-returns-variance-volatility.md) | Returns, Variance, and Volatility | [one-line summary from chapter content] |
| [2](ch02-realized-volatility.md) | Realized Volatility | [one-line summary] |
| [3](ch03-microstructure-noise.md) | Microstructure Noise | [one-line summary] |
| [4](ch04-jumps-continuous-variation.md) | Jumps and Continuous Variation | [one-line summary] |

## Part II: Forecasting Volatility with Classical Models

| Ch. | Title | Summary |
|-----|-------|---------|
| [5](ch05-garch-family.md) | The GARCH Family | [one-line summary] |
| [6](ch06-har-model.md) | The HAR Model and Its Extensions | [one-line summary] |
| [7](ch07-rough-volatility.md) | Rough Volatility | [one-line summary] |

## Part III: The Volatility Surface and Options-Implied Information

| Ch. | Title | Summary |
|-----|-------|---------|
| [8](ch08-options-vol-surface.md) | Options and the Volatility Surface | [one-line summary] |
| [9](ch09-variance-risk-premium.md) | The Variance Risk Premium | [one-line summary] |

## Part IV: ML Methods for Volatility

| Ch. | Title | Summary |
|-----|-------|---------|
| [10](ch10-feature-engineering.md) | Feature Engineering for Volatility | [one-line summary] |
| [11](ch11-tree-methods-vol.md) | Tree Methods for Volatility | [one-line summary] |
| [12](ch12-rashomon-interpretable-trees.md) | Rashomon and Interpretable Trees | [one-line summary] |
| [12b](ch12b-deep-learning-vol.md) | Deep Learning for Volatility | [one-line summary] |
| [13](ch13-hybrid-ensemble.md) | Hybrid and Ensemble Methods | [one-line summary] |

## Part V: Multivariate Volatility and Connectedness

| Ch. | Title | Summary |
|-----|-------|---------|
| [14](ch14-multivariate-volatility.md) | Multivariate Volatility | [one-line summary] |
| [15](ch15-spillovers-connectedness.md) | Spillovers and Connectedness | [one-line summary] |

## Part VI: Evaluation and Practice

| Ch. | Title | Summary |
|-----|-------|---------|
| [16](ch16-forecast-evaluation.md) | Forecast Evaluation | [one-line summary] |
| [17](ch17-applications-projects.md) | Applications and Projects | [one-line summary] |
```

Fill in each `[one-line summary]` by reading the opening paragraph or application box of each completed `.md` file. Each summary should be under 100 characters.

- [ ] **Step 2: Verify all links**

Check that every filename in the INDEX.md table matches an actual file in `vol-learning-guide/markdown/`. Check that chapter titles match the `# Chapter N:` headings in each file.

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/markdown/INDEX.md
git commit -m "docs(vol-learning-guide): add INDEX.md for markdown conversion"
```

---

### Task 21: Update infrastructure

**Files:**
- Modify: `CLAUDE.md` (docs-only branch section)
- Modify: `.claude/skills/sync-docs/SKILL.md`

**Depends on:** Task 20 complete.

- [ ] **Step 1: Update CLAUDE.md**

In `CLAUDE.md`, find the `docs-only` branch section. Add `vol-learning-guide/markdown/` to both the checkout command and the "What stays on docs-only" list.

In the checkout command, add:
```bash
git checkout main -- vol-learning-guide/main.pdf vol-learning-guide/markdown/ guides/ml-finance/main.pdf ...
```

In the "What stays" list, add:
```
- `vol-learning-guide/markdown/` (markdown conversion with Mermaid diagrams, for LLM consumption)
```

- [ ] **Step 2: Update sync-docs skill**

In `.claude/skills/sync-docs/SKILL.md`, find the file list that gets synced to the `docs-only` branch. Add `vol-learning-guide/markdown/` to the list.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md .claude/skills/sync-docs/SKILL.md
git commit -m "docs: add vol-learning-guide/markdown to docs-only branch sync"
```

---

## Parallelism Map

Tasks that can run as parallel sub-agents:

| Batch | Tasks | Chapters | Why Parallel |
|---|---|---|---|
| 0 | Task 1 | Scaffold | Must run first |
| 1 | Tasks 2, 3, 4, 5 | Ch 1-4 (Part I) | Independent conversions |
| 2 | Tasks 6, 7, 8 | Ch 5-7 (Part II) | Independent conversions |
| 3 | Tasks 9, 10 | Ch 8-9 (Part III) | Independent conversions |
| 4 | Tasks 11, 12, 13, 14, 15 | Ch 10-13 (Part IV) | Independent conversions |
| 5 | Tasks 16, 17 | Ch 14-15 (Part V) | Independent conversions |
| 6 | Tasks 18, 19 | Ch 16-17 (Part VI) | Independent conversions |
| 7 | Task 20 | INDEX.md | Depends on all chapter tasks |
| 8 | Task 21 | Infrastructure | Depends on Task 20 |

**All batches 1-6 are fully independent of each other.** With sufficient sub-agents, all 18 chapter conversions (Tasks 2-19) can run in a single parallel batch after the scaffold. The batching by part is for organizational clarity, not a dependency constraint.

Optimal execution: scaffold (1 task) -> all 18 chapters in parallel -> INDEX.md -> infrastructure updates. Total: 4 sequential steps with up to 18 parallel agents in the middle step.
