# Vol Learning Guide -- Markdown Conversion Design Spec

**Date:** 2026-05-14
**Status:** Draft
**Location:** `vol-learning-guide/markdown/`

---

## Purpose

Faithful word-for-word markdown copies of all 18 vol-learning-guide LaTeX chapters, intended for LLM consumption on machines where the PDF is not easily readable (e.g., GitHub Copilot, restricted terminals). Mirrors the approach used for the vol-project-ref markdown conversion (`guides/vol-project-ref/markdown/`).

**Not a rewrite.** Every sentence, equation, citation, and table is preserved exactly. The only content omitted is worked examples and two specific subsections from Chapter 17.

## Constraints

- **Source:** `vol-learning-guide/chapters/*.tex` (18 files, ~17,857 lines)
- **Output:** `vol-learning-guide/markdown/` (18 chapter files + INDEX.md)
- **Audience:** LLMs and humans reading on restricted machines
- **Fidelity:** Word-for-word. No rewriting, summarizing, or reorganizing.
- **Math:** Preserved as LaTeX (`$...$` inline, `$$...$$` display)
- **Citations:** Converted to inline text, e.g., `Corsi (2009)` for `\citet{Corsi2009}`, `(Bollerslev et al., 2016)` for `\citep{Bollerslev2016}`
- **Tables:** GitHub-flavored markdown with `|` delimiters
- **No em dashes**

---

## Omissions

### Worked Examples (all chapters)

All 41 `\begin{workedexample}` blocks are omitted entirely. When a worked example appears mid-section, remove it cleanly with no gap, "[removed]" marker, or reference to its absence. The surrounding prose should read naturally without it.

If surrounding prose references the worked example directly (e.g., "as the worked example below shows"), rewrite the minimum necessary to remove the dangling reference while preserving the factual content of the sentence.

### Chapter 17 (Applications and Projects) -- Two Subsections

Omit:
- Section 18.2: Dealer Gamma (the project direction has already been decided)
- Section 18.3: Five Project Directions (same reason)

All other content in Chapter 17 is preserved.

---

## File Structure

```
vol-learning-guide/markdown/
  INDEX.md
  ch01-returns-variance-volatility.md
  ch02-realized-volatility.md
  ch03-microstructure-noise.md
  ch04-jumps-continuous-variation.md
  ch05-garch-family.md
  ch06-har-model.md
  ch07-rough-volatility.md
  ch08-options-vol-surface.md
  ch09-variance-risk-premium.md
  ch10-feature-engineering.md
  ch11-tree-methods-vol.md
  ch12-rashomon-interpretable-trees.md
  ch12b-deep-learning-vol.md
  ch13-hybrid-ensemble.md
  ch14-multivariate-volatility.md
  ch15-spillovers-connectedness.md
  ch16-forecast-evaluation.md
  ch17-applications-projects.md
```

Note: Two files share the `ch12` prefix (matching the LaTeX source). The deep-learning chapter uses `ch12b` to avoid filename collision.

---

## INDEX.md Structure

Master index file following the same format as `guides/vol-project-ref/markdown/INDEX.md`:

```markdown
# Realized Volatility: Estimation, Forecasting, and ML

**A Learning Guide**

Ryan Vincent

These markdown files are a faithful word-for-word conversion of
`vol-learning-guide/main.pdf`, with TikZ diagrams recreated as Mermaid.
Worked examples are omitted. Intended for LLM consumption on restricted machines.

---

## Part I: What Is Volatility and How Do You Measure It?

| Ch. | Title | Summary |
|-----|-------|---------|
| [1](ch01-...) | Returns, Variance, and Volatility | ... |
| ... | ... | ... |

## Part II: Forecasting Volatility with Classical Models
...
```

Each part header matches the LaTeX `\part{}` titles exactly. Each chapter row has a one-line summary.

---

## Box Type Rendering

All tcolorbox environments are rendered as blockquotes with bold type labels:

| LaTeX Environment | Markdown Rendering |
|---|---|
| `\begin{prereq}[Title]` | `> **Prereq: Title**` |
| `\begin{intuition}[Title]` | `> **Intuition: Title**` |
| `\begin{keyidea}[Title]` | `> **Key Idea: Title**` |
| `\begin{keyresult}[Title]` | `> **Key Result: Title**` |
| `\begin{definition}[Title]` | `> **Definition: Title**` |
| `\begin{warning}[Title]` | `> **Warning: Title**` |
| `\begin{projectconnection}[Title]` | `> **Project Connection: Title**` |
| `\begin{application}[Title]` | `> **Application: Title**` |
| `\begin{workedexample}{Title}` | **Omitted entirely** |

Multi-paragraph box content uses `>` continuation on each line. Equations inside boxes use `>` prefix on each line of the `$$` block.

---

## Diagram Conversion

78 TikZ diagrams recreated as Mermaid flowcharts, following the same conventions as the vol-project-ref conversion:

- **Format:** Fenced code blocks with ` ```mermaid ` language identifier
- **Direction:** `flowchart LR` for pipelines, `flowchart TD` for hierarchies
- **Color coding:** Blue for data/inputs, green for computation/processing, orange for models/outputs
- **Subgraph grouping:** For related components
- **Dashed lines:** For optional/alternative paths or feedback arrows
- **Thick arrows (`==>`):** For dominant/primary flows
- **Thin arrows (`-->`):** For secondary flows

Each Mermaid diagram is followed by a brief caption paragraph (matching the LaTeX `\caption{}`).

### Diagram types in the learning guide

The vol-learning-guide has more diverse diagram types than the vol-project-ref:

| Type | Count (approx) | Mermaid Strategy |
|---|---|---|
| Pipeline/flow diagrams | ~25 | `flowchart LR/TD` -- straightforward |
| Conceptual diagrams (e.g., HMH participant types) | ~15 | `flowchart TD` with subgraphs |
| Architecture diagrams (e.g., LSTM, ensemble) | ~10 | `flowchart TD/LR` with branching |
| Decision trees / splitting diagrams | ~8 | `flowchart TD` with diamond nodes |
| Comparison diagrams (e.g., GARCH vs HAR) | ~8 | `flowchart LR` with parallel subgraphs |
| Scatter/distribution plots (pgfplots) | ~12 | Described in prose with key values, NOT recreated as Mermaid |

**Important:** pgfplots charts (scatter plots, histograms, ACF plots, distribution curves) cannot be meaningfully recreated as Mermaid. These are described in a brief prose paragraph stating what the figure shows and the key numerical values. Format:

```markdown
*[Figure: ACF of daily realized variance for S&P 500 (2012--2023).
Autocorrelation at lag 1: 0.62. Decays hyperbolically, still significant at lag 100.
This slow decay is the signature of long memory.]*
```

---

## Mathematical Content

LaTeX math is preserved exactly as-is:

- **Inline:** `$\operatorname{RV}_t$`, `$\beta_d$`, etc.
- **Display:** `$$` blocks with the full equation
- **Equation labels:** Omitted (no `\label{}`/`\ref{}` equivalent in markdown)
- **Cross-references:** LaTeX `\ref{eq:har}` and `\eqref{}` replaced with descriptive text (e.g., "the HAR equation above" or "Equation 6.1")
- **`\operatorname{}`**, `\text{}`, `\mathbb{}`, `\boldsymbol{}` all preserved
- **`\RV` custom command:** Expanded to `\operatorname{RV}` everywhere

---

## Cross-References

LaTeX cross-references (`\ref{ch:garch}`, `Chapter~\ref{ch:trees}`) are converted to markdown links where possible:

- **Same chapter:** "Section 6.2 above" (descriptive text)
- **Other chapter:** "[Chapter 5](ch05-garch-family.md)" (relative link)
- **Equation refs:** Descriptive text ("the HAR equation" or "Equation 6.1")
- **Figure refs:** Descriptive text ("the diagram above")

---

## Per-Chapter Conversion Process

Each chapter follows this pipeline:

### Step 1: Convert

- Read the full `.tex` source
- Convert all prose word-for-word
- Convert all boxes to blockquote format (skip workedexamples)
- Convert all tables to GFM markdown
- Preserve all math exactly
- Convert citations to inline text
- Convert cross-references to links or descriptive text

### Step 2: Recreate Diagrams

- Identify each `\begin{tikzpicture}` block
- Classify as flowchart/conceptual/architecture/decision/comparison/plot
- Flowcharts and conceptual diagrams: recreate as Mermaid
- pgfplots: describe in italicized prose paragraph with key values

### Step 3: Verify

- No content dropped (except workedexamples and the two Ch17 subsections)
- No mangled math (check `$` pairing, `$$` blocks)
- All boxes converted with correct type labels
- Mermaid syntax is valid (no unclosed subgraphs, no unescaped special chars)
- Cross-references resolve (links to other chapter files use correct filenames)

---

## Parallelism

All 18 chapters are independent conversions. Batch by part for manageable parallelism:

| Batch | Part | Chapters | Diagrams | Lines (approx) |
|---|---|---|---|---|
| 1 | I: Measurement | Ch 1-4 | 19 | ~4,200 |
| 2 | II: Classical Models | Ch 5-7 | 12 | ~3,400 |
| 3 | III: Options | Ch 8-9 | 9 | ~2,200 |
| 4 | IV: ML Methods | Ch 10-13 (incl. both ch12) | 18 | ~4,800 |
| 5 | V: Multivariate | Ch 14-15 | 11 | ~2,100 |
| 6 | VI: Evaluation | Ch 16-17 | 4 | ~1,100 |
| 7 | Assembly | INDEX.md, sync-docs, CLAUDE.md | -- | -- |

Within each batch, chapters can run as parallel sub-agents.

---

## Infrastructure Updates

After all chapters are converted:

1. **CLAUDE.md:** Add `vol-learning-guide/markdown/` to the `docs-only` branch file list
2. **sync-docs skill:** Update to include `vol-learning-guide/markdown/` in branch sync
3. **settings.local.json hook (optional):** Warn when editing `vol-learning-guide/chapters/*.tex` to sync corresponding `markdown/` files

---

## Success Criteria

- Every sentence from the LaTeX source appears in the markdown (except worked examples and the two omitted Ch17 subsections)
- All 78 TikZ diagrams are either recreated as Mermaid (flowcharts/conceptual) or described in prose (plots)
- All ~671 boxes (712 minus 41 workedexamples) are rendered as labeled blockquotes
- All mathematical notation renders correctly in any markdown viewer that supports LaTeX math
- INDEX.md links to all 18 chapter files with correct relative paths
- Files sync to `docs-only` branch via the sync-docs workflow
