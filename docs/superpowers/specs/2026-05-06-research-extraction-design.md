# Design: Deep Research Extraction Pipeline

**Date**: 2026-05-06
**Source**: Brainstorming session on extracting and organizing deep research output

---

## Problem

`notes/deep-research-vol-papers.md` is a 365-line deep research output doing triple duty: landscape survey, annotated bibliography (~80 entries), project proposals, and recommendations. The information needs to be decomposed into the repo's existing structure so that (a) papers are trackable and LLM-parseable, (b) feature findings reach the right `notes/features/*.md` files, (c) project proposals are accessible without reading 365 lines, and (d) a research index tracks what was extracted and where.

## Approach

**Approach 1 with index**: One-pass decomposition into existing structure, original file trimmed, plus a lightweight research index for tracking future extractions.

## Outputs

### 1. Bibliography -- `reference/bibliography.md`

**Purpose**: Master catalog of every paper/resource referenced in the project. Optimized for LLM consumption: consistent fields, greppable, no prose paragraphs.

**Preservation of existing content**: The current `reference/bibliography.md` contains a quant-trading canon (~330 lines). Before overwriting, archive it to `reference/bibliography-quant-trading-canon.md`. Any entries from the quant-trading canon that are also relevant to the vol project (e.g., Lopez de Prado AFML, Bennett volatility PDF) should be included in the new bibliography.

**Format**: One heading per entry using a kebab-case slug ID. Consistent metadata fields per entry. A table of contents with anchor links at the top of the file for navigability.

```markdown
### slug-id
- **Title**: Full title
- **Authors**: Last names
- **Year**: YYYY
- **Venue**: Journal/conference with volume/pages or arXiv ID
- **Quality**: essential / recommended / optional
- **Topics**: comma-separated tags from a controlled vocabulary
- **PDF**: relative path to `reference/project-papers/filename.pdf` or `none`
- **Key finding**: 1-2 sentences. What this paper shows.
- **Relevance**: 1 sentence. Why it matters for the project.
```

Quality tag normalization: The research file uses variants like "Essential if going deep", "Recommended for depth", "Optional unless using HF data heavily." Normalize to the three canonical values (`essential`, `recommended`, `optional`). Use the `Relevance` field to capture any qualifier (e.g., "Essential if going deep" becomes Quality: `essential`, Relevance: "Definitive textbook; most valuable if pursuing HF data path.").

**Categories** (top-level headings):
- A: RV estimators and theory
- B: HAR family and econometric baselines
- C: Rough volatility
- D: ML for volatility (empirical)
- E: LOB deep learning
- F: Variance risk premium and options
- G: Forecast evaluation and validation
- H: Rashomon sets and optimal decision trees
- I: Deep time-series architectures
- J: Code repos and data sources
- K: Practitioner and industry resources

**Topic tags** (controlled vocabulary, extensible): `rv-estimators`, `microstructure-noise`, `jump-detection`, `har`, `harq`, `har-extensions`, `garch`, `realized-garch`, `rough-vol`, `ml-vol`, `gradient-boosting`, `neural-nets`, `deep-learning`, `lstm`, `cnn-tcn`, `transformers`, `gnn`, `ensemble`, `rashomon`, `optimal-trees`, `lob`, `vrp`, `options-implied`, `cross-asset`, `spillovers`, `evaluation`, `qlike`, `mcs`, `validation`, `purged-cv`, `feature-engineering`, `long-memory`, `sentiment`, `regime`, `data-source`, `code-repo`, `foundational`

**Entry count**: ~80 entries extracted from the research file's Part 3 bibliography (sections A-K), plus entries from `reference/project-papers/README.md` not covered in the research file. Papers only in `README.md` get stub entries with fields populated from the README table columns, marked with `Relevance: stub -- enrich from paper abstract`.

**Cross-reference**: `reference/project-papers/README.md` stays as-is (tracks physical PDFs). The bibliography's `PDF` field links into it. Papers listed in README's "Papers Still Needed" section get `PDF: none` in the bibliography.

### 2. Feature findings -- append to `notes/features/*.md`

Each target file gets a new section appended at the bottom:

```markdown
## Deep Research Findings (2026-05-06)

- [finding with citation slug from bibliography]
```

**Mapping** (source references use fully qualified Part/Section labels from the research file):

| Source (research file) | Target | Content |
|---|---|---|
| Part 1 Section D "Feature engineering", item 1 (RV history, BV, RQ, semivariances, realized skew/kurtosis) | `notes/features/har-components.md` | Amaya et al. 2015 realized higher moments; signed jump variation J = RS+ - RS- |
| Part 1 Section D item 2 + Part 1 Section E "VRP and vol-of-vol" | `notes/features/implied-vol.md` | Bollerslev-Tauchen-Zhou 2009 VRP quarterly return prediction (>15% quarterly excess return variation); VIX term structure slope/curvature; Bakshi-Kapadia-Madan 2003 risk-neutral skewness; VRP = IV^2 - RV^2 construction; VVIX as vol-of-vol signal |
| Part 1 Section D item 3 (bid-ask, order flow, Amihud, microprice) | `notes/features/microstructure.md` | Rahimikia-Poon 2020 ML+LOB beats HAR 90% OOS days, mid prices/bids/asks dominant; Cont-Kukanov-Stoikov 2014 order flow imbalance |
| Part 1 Section D item 4 + Part 1 Section F "Multi-asset and cross-asset" | `notes/features/cross-asset.md` | Diebold-Yilmaz spillover framework; Zhang et al. 2025 GNN: nonlinear one-hop helps, multi-hop doesn't; MOVE, CDX, DXY vol; Herskovic-Kelly-Lustig-Van Nieuwerburgh 2016 common idiosyncratic volatility |
| Part 1 Section D item 7 (leverage) | `notes/features/leverage-effect.md` | Patton-Sheppard 2015: negative semivariance >> positive for future RV prediction |
| Part 1 Section D item 5 (jump findings) | `notes/features/jump-detection.md` | Andersen-Bollerslev-Diebold 2007: jumps important but less persistent; Lee 2012: earnings trigger jumps |
| Part 1 Section D "Rashomon-aware feature analysis" bullet | `notes/features/optimal-feature-set.md` | Append only if not already covered. Check existing content first -- the file already has 265 lines with Rashomon-adjacent concepts. Only add the specific Variable Importance Clouds citation (Dong-Rudin 2020) and the "essential vs. interchangeable" framing if absent. |
| Part 1 Section D item 5 (calendar/event features) | `notes/features/calendar-events.md` **NEW** | FOMC, earnings, macro releases, expiration dates; Lee 2012 earnings-trigger-jumps finding |
| Part 1 Section D item 6 (long memory) | `notes/features/har-components.md` | Fractional differencing (Lopez de Prado AFML Ch. 5) preserves memory while ensuring stationarity. Append to existing HAR components since long memory is the core HAR mechanism. |
| Part 1 Section D item 7 (sentiment/NLP) | `notes/features/microstructure.md` | Rahimikia-Zohren-Poon 2024 FinText embeddings helpful on jump days. Append as a brief note since this is LOB-adjacent and out of main project scope. |
| Part 1 Section C (ML methods) -- horizon findings | `notes/features/har-components.md` | Section C6 honest verdict: ML wins at longer horizons (weekly/monthly) per Christensen et al. 2023; daily is hard to beat HARQ by more than a few percent QLIKE |
| Part 1 Section G (pitfalls) -- feature construction warnings | `notes/features/optimal-feature-set.md` | Append only if absent: lookahead bias in smoothed estimators; log-RV space modeling; QLIKE > MSE for training (Zhang et al. 2025 GNN) |

### 3. Project proposals -- `notes/project-proposals.md`

**New file** containing:
- Recommendation summary (which project and why)
- Project 1: HAR-X-Boost (safe) -- full proposal
- Project 2: Neural HAR with Rough-Vol Prior (moderate) -- full proposal
- Project 3: Rashomon Volatility (recommended flagship) -- full proposal
- Project 4: Cross-Asset Volatility GNN (ambitious) -- full proposal
- Decision benchmarks (the "what would change the recommendation" thresholds)
- Caveats (all 8 from the research file)

Content is extracted from the research file with light editing to fix internal cross-references (e.g., "See Project 3 in Part 2" becomes "See Project 3 below" since the proposals are now in a standalone file).

### 4. Research index -- `notes/research-index.md`

**New file** tracking what was extracted from which research prompt and where it went. One entry per deep research run:

```markdown
# Research Index

## 2026-05-06: ML for Realized Volatility Forecasting
- **Source prompt**: notes/deep-research-prompt.md
- **Raw output**: notes/deep-research-vol-papers.md (trimmed to landscape survey)
- **Extracted to**:
  - reference/bibliography.md -- ~80 entries, categories A-K
  - notes/project-proposals.md -- 4 directions + recommendations + caveats
  - notes/features/har-components.md -- realized higher moments, signed jump variation
  - notes/features/implied-vol.md -- VRP, VIX term structure, risk-neutral skewness
  - [etc. for each feature file]
  - notes/features/calendar-events.md -- NEW
```

Grows with each future deep research run (e.g., the decision tree prompt).

### 5. Original file trimming -- `notes/deep-research-vol-papers.md`

**Kept**: TL;DR, Key Findings paragraph, Part 1 landscape survey (sections A-H titled "A. Realized volatility" through "H. Practical applications").

**Removed**: Part 2 "PROJECT DIRECTION PROPOSALS" (heading "Details -- PART 2"), Part 3 "ANNOTATED BIBLIOGRAPHY" (heading "Details -- PART 3"), "Recommendations" section, "Caveats" section.

**Added** at the top, after the TL;DR:

```markdown
---
> **Bibliography**: extracted to `reference/bibliography.md`
> **Project proposals**: extracted to `notes/project-proposals.md`
> **Research index**: `notes/research-index.md`
---
```

## Files created or modified

| File | Action |
|---|---|
| `reference/bibliography-quant-trading-canon.md` | **Create** (archive of current bibliography.md before overwrite) |
| `reference/bibliography.md` | **Rewrite** (vol-project bibliography, after archiving current content) |
| `notes/project-proposals.md` | **Create** |
| `notes/research-index.md` | **Create** |
| `notes/features/calendar-events.md` | **Create** |
| `notes/features/har-components.md` | **Append** |
| `notes/features/implied-vol.md` | **Append** |
| `notes/features/microstructure.md` | **Append** |
| `notes/features/cross-asset.md` | **Append** |
| `notes/features/leverage-effect.md` | **Append** |
| `notes/features/jump-detection.md` | **Append** |
| `notes/features/optimal-feature-set.md` | **Append** |
| `notes/deep-research-vol-papers.md` | **Trim** (remove extracted sections, add cross-references) |
| `reference/project-papers/README.md` | **No change** |

## Execution order

1. Archive `reference/bibliography.md` to `reference/bibliography-quant-trading-canon.md` (must happen before step 2)
2. Create `reference/bibliography.md` (largest piece, independent after step 1)
3. Create `notes/project-proposals.md` (independent)
4. Create `notes/research-index.md` (independent)
5. Create `notes/features/calendar-events.md` (independent)
6. Append to each existing `notes/features/*.md` (independent of each other; read each file first to check for overlap before appending)
7. Trim `notes/deep-research-vol-papers.md` (last, after everything is extracted)

Steps 2-6 are independent and can be parallelized (after step 1 completes).

## Decisions

- `reference/bibliography.md` current content is archived to `reference/bibliography-quant-trading-canon.md` before overwrite. Vol-relevant entries from the quant-trading canon (Lopez de Prado AFML, Bennett volatility PDF, Avellaneda-Stoikov, Cartea-Jaimungal-Penalva) are included in the new bibliography.
- Slug IDs use `authorlist-year` format with up to 3 author last names, then truncate with "etal" (e.g., `corsi-2009`, `bollerslev-patton-quaedvlieg-2016`, `andersen-bollerslev-diebold-etal-2003`). If two papers share the same slug, append a dash and the first distinctive word from the title (e.g., `andersen-bollerslev-diebold-2007-roughing`).
- The controlled topic tag vocabulary is extensible -- new tags can be added as future research prompts cover new areas.
- Feature file appends must check for existing overlap before writing. If the finding is already covered (especially `optimal-feature-set.md` which has 265 lines of detailed content), only add the specific new citation or framing that is absent.
