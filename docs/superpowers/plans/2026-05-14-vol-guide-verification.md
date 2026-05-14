# Vol-Learning-Guide Systematic Verification -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify every fact, formula, derivation, and qualitative claim in the 17-chapter vol-learning-guide against source papers, fixing any errors found.

**Architecture:** Two-pass pipeline. Pass 1 extracts all verifiable claims from each chapter into per-chapter markdown tracking files (parallelizable across chapters). Pass 2 verifies each claim against source papers in criticality order (parallelize 2-3 chapters at a time within tiers). Corrections are applied inline via Edit for small fixes or via write-chapter skill for structural issues.

**Tech Stack:** LaTeX source files, PDF reference papers, markdown tracking files. All subagents use Opus 4.6.

**Spec:** `docs/superpowers/specs/2026-05-14-vol-guide-verification-design.md`

---

## File Map

**Created:**
- `vol-learning-guide/verification/README.md` -- progress dashboard
- `vol-learning-guide/verification/ch01-returns-variance-volatility.md`
- `vol-learning-guide/verification/ch02-realized-volatility.md`
- `vol-learning-guide/verification/ch03-microstructure-noise.md`
- `vol-learning-guide/verification/ch04-jumps-continuous-variation.md`
- `vol-learning-guide/verification/ch05-garch-family.md`
- `vol-learning-guide/verification/ch06-har-model.md`
- `vol-learning-guide/verification/ch07-rough-volatility.md`
- `vol-learning-guide/verification/ch08-options-vol-surface.md`
- `vol-learning-guide/verification/ch09-variance-risk-premium.md`
- `vol-learning-guide/verification/ch10-feature-engineering.md`
- `vol-learning-guide/verification/ch11-tree-methods-vol.md`
- `vol-learning-guide/verification/ch12-deep-learning-vol.md`
- `vol-learning-guide/verification/ch12r-rashomon-interpretable-trees.md`
- `vol-learning-guide/verification/ch13-hybrid-ensemble.md`
- `vol-learning-guide/verification/ch14-multivariate-volatility.md`
- `vol-learning-guide/verification/ch15-spillovers-connectedness.md`
- `vol-learning-guide/verification/ch16-forecast-evaluation.md`
- `vol-learning-guide/verification/ch17-applications-projects.md`

**Modified (if errors found during Pass 2):**
- `vol-learning-guide/chapters/*.tex` -- any chapter where claims are incorrect
- `vol-learning-guide/references.bib` -- if new citations needed for `[uncited]` claims

---

## Claim Taxonomy Reference

Every verifiable statement falls into one of these types. Subagents must classify each claim during extraction.

| Type | Tag for tracking file | Verification standard |
|---|---|---|
| Key equation that defines a concept | `defining-formula` | Symbol-exact against source paper |
| Intermediate derivation or helper equation | `supporting-formula` | Semantically correct |
| Specific number, percentage, or statistic | `numerical-fact` | Exact match against source table/paragraph |
| Qualitative statement about properties/behavior | `qualitative` | Confirm statement appears in cited source |
| Statement about who proposed/introduced something | `attribution` | Confirm paper actually introduces the concept |
| Recommendation about methodology/best practices | `methodological` | Confirm cited source supports this |

**Exclude from extraction:** Pedagogical framing ("think of it like..."), pure notation definitions internal to the guide (e.g., "we use $\sigma$ to denote..."), chapter structure/flow text, TikZ diagram layout details.

---

## Task 1: Create Verification Infrastructure

**Files:**
- Create: `vol-learning-guide/verification/README.md`

- [ ] **Step 1: Create the verification directory and README**

```markdown
# Verification Progress

Last updated: 2026-05-14

## Tier 1: Pipeline-critical

| Chapter | File | Claims | Verified | Errors | Status |
|---|---|---|---|---|---|
| Ch 10: Feature Engineering | ch10-feature-engineering.md | -- | -- | -- | Pending |
| Ch 6: HAR Model | ch06-har-model.md | -- | -- | -- | Pending |
| Ch 4: Jumps & Continuous Variation | ch04-jumps-continuous-variation.md | -- | -- | -- | Pending |
| Ch 16: Forecast Evaluation | ch16-forecast-evaluation.md | -- | -- | -- | Pending |

## Tier 2: Model-critical

| Chapter | File | Claims | Verified | Errors | Status |
|---|---|---|---|---|---|
| Ch 3: Microstructure Noise | ch03-microstructure-noise.md | -- | -- | -- | Pending |
| Ch 5: GARCH Family | ch05-garch-family.md | -- | -- | -- | Pending |
| Ch 11: Tree Methods | ch11-tree-methods-vol.md | -- | -- | -- | Pending |
| Ch 2: Realized Volatility | ch02-realized-volatility.md | -- | -- | -- | Pending |
| Ch 12-R: Rashomon Trees | ch12r-rashomon-interpretable-trees.md | -- | -- | -- | Pending |

## Tier 3: Context and enrichment

| Chapter | File | Claims | Verified | Errors | Status |
|---|---|---|---|---|---|
| Ch 8: Options & Vol Surface | ch08-options-vol-surface.md | -- | -- | -- | Pending |
| Ch 9: Variance Risk Premium | ch09-variance-risk-premium.md | -- | -- | -- | Pending |
| Ch 7: Rough Volatility | ch07-rough-volatility.md | -- | -- | -- | Pending |
| Ch 12-DL: Deep Learning | ch12-deep-learning-vol.md | -- | -- | -- | Pending |
| Ch 13: Hybrid/Ensemble | ch13-hybrid-ensemble.md | -- | -- | -- | Pending |
| Ch 14: Multivariate Volatility | ch14-multivariate-volatility.md | -- | -- | -- | Pending |
| Ch 15: Spillovers | ch15-spillovers-connectedness.md | -- | -- | -- | Pending |
| Ch 1: Returns/Variance | ch01-returns-variance-volatility.md | -- | -- | -- | Pending |
| Ch 17: Applications | ch17-applications-projects.md | -- | -- | -- | Pending |
```

- [ ] **Step 2: Commit infrastructure**

```bash
git add vol-learning-guide/verification/README.md
git commit -m "chore(verification): create tracking infrastructure for systematic fact-checking"
```

---

## Task 2: Pass 1 -- Extract Claims from Tier 1 Chapters

**Files:**
- Create: `vol-learning-guide/verification/ch10-feature-engineering.md`
- Create: `vol-learning-guide/verification/ch06-har-model.md`
- Create: `vol-learning-guide/verification/ch04-jumps-continuous-variation.md`
- Create: `vol-learning-guide/verification/ch16-forecast-evaluation.md`

**Dispatch 4 parallel subagents (all Opus 4.6), one per chapter.** Each subagent receives the instructions below with its specific chapter file path substituted.

### Subagent prompt template for Pass 1 extraction:

> You are extracting verifiable claims from a LaTeX chapter for a systematic fact-checking audit. Do NOT read any papers or verify anything -- just extract and catalog.
>
> **Read** the chapter file at `vol-learning-guide/chapters/{CHAPTER_FILE}`.
>
> Walk through the chapter linearly, line by line. For every verifiable statement, create a row in a tracking table. A "verifiable statement" is any:
> - **defining-formula**: Key equation that defines a concept (e.g., the HAR-RV equation, GARCH recursion, bipower variation formula). These are the equations an LLM would grab to implement the concept.
> - **supporting-formula**: Intermediate derivation step, variance expression, asymptotic result, or helper equation.
> - **numerical-fact**: A specific number, percentage, or statistic (e.g., "jumps contribute ~7% of total QV", "QLIKE improvement of 5-12%").
> - **qualitative**: A qualitative statement about properties or behavior (e.g., "TSRV converges at rate n^{-1/6}", "volatility clusters").
> - **attribution**: A statement about who proposed or introduced something (e.g., "Corsi (2009) proposed the HAR model").
> - **methodological**: A recommendation about methodology or best practices (e.g., "5-minute sampling is the standard frequency").
>
> **Exclude:** Pedagogical framing ("think of it like..."), pure notation definitions internal to the guide (e.g., "we use $\sigma$ to denote..."), chapter structure/flow text, TikZ diagram layout, text inside `\begin{application}` or `\begin{prereq}` environments that is purely structural.
>
> **For the "Cited source" column:** Look for `\citep{}` or `\citet{}` near the claim. If the claim has no explicit citation, write `[uncited]`. If a claim cites multiple papers, create one row per paper with suffixed claim numbers (e.g., 12a, 12b).
>
> **For the "Claim/Formula" column:** For formulas, write the LaTeX math (abbreviated if very long, but keep the key structure). For text claims, quote the key phrase in double quotes.
>
> **Write** the result to `vol-learning-guide/verification/{TRACKING_FILE}` using this exact format:
>
> ```markdown
> # Chapter {NUM}: {NAME} -- Verification Log
>
> **Status:** Extraction complete
> **Claims extracted:** {N}
> **Verified:** 0/{N}
> **Errors found:** 0
>
> ## Claims
>
> | # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
> |---|---|---|---|---|---|---|---|
> | 1 | {line} | {type} | {claim} | {source} | | | |
> ```
>
> Be thorough. Every formula, every cited fact, every attributed result. It is better to extract too many claims than to miss one. The verification pass will filter out false positives, but it cannot catch claims you missed.

**Chapter-specific substitutions:**

| Subagent | CHAPTER_FILE | TRACKING_FILE | NUM | NAME |
|---|---|---|---|---|
| 1 | `10-feature-engineering.tex` | `ch10-feature-engineering.md` | 10 | Feature Engineering for Volatility |
| 2 | `06-har-model.tex` | `ch06-har-model.md` | 6 | The HAR Model and Its Extensions |
| 3 | `04-jumps-continuous-variation.tex` | `ch04-jumps-continuous-variation.md` | 4 | Jumps and Continuous Variation |
| 4 | `16-forecast-evaluation.tex` | `ch16-forecast-evaluation.md` | 16 | Forecast Evaluation |

- [ ] **Step 1: Dispatch 4 parallel Opus 4.6 subagents** using the prompt template above with the chapter-specific substitutions
- [ ] **Step 2: Review each subagent's output** -- spot-check that claims are properly classified, line numbers are correct, and no obvious claims were missed
- [ ] **Step 3: Commit all 4 tracking files**

```bash
git add vol-learning-guide/verification/ch10-feature-engineering.md \
       vol-learning-guide/verification/ch06-har-model.md \
       vol-learning-guide/verification/ch04-jumps-continuous-variation.md \
       vol-learning-guide/verification/ch16-forecast-evaluation.md
git commit -m "chore(verification): extract claims from Tier 1 chapters (Pass 1)"
```

---

## Task 3: Pass 1 -- Extract Claims from Tier 2 Chapters

**Files:**
- Create: `vol-learning-guide/verification/ch03-microstructure-noise.md`
- Create: `vol-learning-guide/verification/ch05-garch-family.md`
- Create: `vol-learning-guide/verification/ch11-tree-methods-vol.md`
- Create: `vol-learning-guide/verification/ch02-realized-volatility.md`
- Create: `vol-learning-guide/verification/ch12r-rashomon-interpretable-trees.md`

**Dispatch 5 parallel Opus 4.6 subagents** using the same prompt template from Task 2.

**Chapter-specific substitutions:**

| Subagent | CHAPTER_FILE | TRACKING_FILE | NUM | NAME |
|---|---|---|---|---|
| 1 | `03-microstructure-noise.tex` | `ch03-microstructure-noise.md` | 3 | Microstructure Noise and Robust Estimators |
| 2 | `05-garch-family.tex` | `ch05-garch-family.md` | 5 | The GARCH Family |
| 3 | `11-tree-methods-vol.tex` | `ch11-tree-methods-vol.md` | 11 | Tree-Based Methods for Volatility |
| 4 | `02-realized-volatility.tex` | `ch02-realized-volatility.md` | 2 | Realized Volatility |
| 5 | `12-rashomon-interpretable-trees.tex` | `ch12r-rashomon-interpretable-trees.md` | 12-R | Rashomon Sets and Interpretable Trees |

- [ ] **Step 1: Dispatch 5 parallel Opus 4.6 subagents**
- [ ] **Step 2: Review each subagent's output**
- [ ] **Step 3: Commit all 5 tracking files**

```bash
git add vol-learning-guide/verification/ch03-microstructure-noise.md \
       vol-learning-guide/verification/ch05-garch-family.md \
       vol-learning-guide/verification/ch11-tree-methods-vol.md \
       vol-learning-guide/verification/ch02-realized-volatility.md \
       vol-learning-guide/verification/ch12r-rashomon-interpretable-trees.md
git commit -m "chore(verification): extract claims from Tier 2 chapters (Pass 1)"
```

---

## Task 4: Pass 1 -- Extract Claims from Tier 3 Chapters

**Files:**
- Create: `vol-learning-guide/verification/ch08-options-vol-surface.md`
- Create: `vol-learning-guide/verification/ch09-variance-risk-premium.md`
- Create: `vol-learning-guide/verification/ch07-rough-volatility.md`
- Create: `vol-learning-guide/verification/ch12-deep-learning-vol.md`
- Create: `vol-learning-guide/verification/ch13-hybrid-ensemble.md`
- Create: `vol-learning-guide/verification/ch14-multivariate-volatility.md`
- Create: `vol-learning-guide/verification/ch15-spillovers-connectedness.md`
- Create: `vol-learning-guide/verification/ch01-returns-variance-volatility.md`
- Create: `vol-learning-guide/verification/ch17-applications-projects.md`

**Dispatch 9 parallel Opus 4.6 subagents** using the same prompt template from Task 2.

**Chapter-specific substitutions:**

| Subagent | CHAPTER_FILE | TRACKING_FILE | NUM | NAME |
|---|---|---|---|---|
| 1 | `08-options-vol-surface.tex` | `ch08-options-vol-surface.md` | 8 | Options Basics and the Volatility Surface |
| 2 | `09-variance-risk-premium.tex` | `ch09-variance-risk-premium.md` | 9 | The Variance Risk Premium |
| 3 | `07-rough-volatility.tex` | `ch07-rough-volatility.md` | 7 | Rough Volatility |
| 4 | `12-deep-learning-vol.tex` | `ch12-deep-learning-vol.md` | 12-DL | Deep Learning for Volatility |
| 5 | `13-hybrid-ensemble.tex` | `ch13-hybrid-ensemble.md` | 13 | Hybrid and Ensemble Methods |
| 6 | `14-multivariate-volatility.tex` | `ch14-multivariate-volatility.md` | 14 | Multivariate Volatility |
| 7 | `15-spillovers-connectedness.tex` | `ch15-spillovers-connectedness.md` | 15 | Volatility Spillovers and Connectedness |
| 8 | `01-returns-variance-volatility.tex` | `ch01-returns-variance-volatility.md` | 1 | Returns, Variance, and Why Volatility Matters |
| 9 | `17-applications-projects.tex` | `ch17-applications-projects.md` | 17 | Practical Applications and Project Roadmaps |

- [ ] **Step 1: Dispatch 9 parallel Opus 4.6 subagents**
- [ ] **Step 2: Review each subagent's output**
- [ ] **Step 3: Commit all 9 tracking files**

```bash
git add vol-learning-guide/verification/ch08-options-vol-surface.md \
       vol-learning-guide/verification/ch09-variance-risk-premium.md \
       vol-learning-guide/verification/ch07-rough-volatility.md \
       vol-learning-guide/verification/ch12-deep-learning-vol.md \
       vol-learning-guide/verification/ch13-hybrid-ensemble.md \
       vol-learning-guide/verification/ch14-multivariate-volatility.md \
       vol-learning-guide/verification/ch15-spillovers-connectedness.md \
       vol-learning-guide/verification/ch01-returns-variance-volatility.md \
       vol-learning-guide/verification/ch17-applications-projects.md
git commit -m "chore(verification): extract claims from Tier 3 chapters (Pass 1)"
```

---

## Task 5: Compile Extraction Summary and Paper Inventory

**Files:**
- Modify: `vol-learning-guide/verification/README.md`

After all 18 tracking files exist, update the README with actual claim counts and build a paper inventory.

- [ ] **Step 1: Count claims per chapter** -- read each tracking file, extract the "Claims extracted" number, update the README table

- [ ] **Step 2: Build paper inventory** -- grep all tracking files for unique source citations. For each cited paper:
  - Check if PDF exists in `reference/project-papers/`, `reference/papers/`, or `reference/books/`
  - List papers that are missing and need acquisition
  - List papers that are `[uncited]` claims (will need source identification during Pass 2)

- [ ] **Step 3: Update README** with actual numbers and append a "Papers Needed" section listing missing PDFs

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/verification/README.md
git commit -m "chore(verification): compile extraction summary with claim counts and paper inventory"
```

---

## Task 6: Paper Acquisition

**Files:**
- Create: new PDFs in `reference/project-papers/`

Acquire missing papers identified in Task 5. This task may span multiple sessions.

- [ ] **Step 1: For each missing paper, search in this order:**
  1. arXiv (search by title + author)
  2. SSRN (search by title)
  3. Author's personal/institutional webpage
  4. Google Scholar (look for PDF links)

- [ ] **Step 2: Download to `reference/project-papers/`** using naming convention `lastname-year-short-description.pdf`

- [ ] **Step 3: For papers that cannot be found freely**, check if the claim can be verified against a textbook in `reference/books/` (Hull, AFML, Cartea et al.). Note which textbook in the tracking file.

- [ ] **Step 4: Update README** -- mark acquired papers, flag remaining unavailable ones

- [ ] **Step 5: Commit**

```bash
git add reference/project-papers/*.pdf
git commit -m "chore(verification): acquire missing reference papers for fact-checking"
```

---

## Task 7: Pass 2 -- Verify Ch 10 (Feature Engineering)

**Priority:** Tier 1, #1 -- most critical chapter, defines every feature the model ingests.

**Files:**
- Modify: `vol-learning-guide/verification/ch10-feature-engineering.md`
- Modify (if errors): `vol-learning-guide/chapters/10-feature-engineering.tex`
- Modify (if new citations): `vol-learning-guide/references.bib`

**Dispatch 1 Opus 4.6 subagent** with the following prompt:

> You are verifying claims in a LaTeX chapter against source papers. This is Chapter 10 (Feature Engineering) of a realized volatility learning guide. This chapter is the most critical because it defines every feature that ML models will ingest -- a wrong formula here means wrong features in the pipeline.
>
> **Read** the tracking file at `vol-learning-guide/verification/ch10-feature-engineering.md`. This contains all extracted claims with their cited sources.
>
> **Read** the chapter file at `vol-learning-guide/chapters/10-feature-engineering.tex` for full context.
>
> **Process claims grouped by source paper** (to minimize re-reading papers). For each source paper:
>
> 1. Check if the PDF exists in `reference/project-papers/` or `reference/papers/` or `reference/books/`
> 2. If missing: use WebSearch to find a free version (arXiv, SSRN, author page), then WebFetch to download it to `reference/project-papers/` using naming convention `lastname-year-short-description.pdf`
> 3. If still missing: check textbooks in `reference/books/` for canonical results
> 4. If neither works: mark the claim `unverified` with note `paper unavailable`
>
> 5. **Read the paper** (use the Read tool on the PDF). Find the specific page/equation/table for each claim.
>
> 6. **Verify each claim** according to its type:
>    - `defining-formula`: Symbol-exact comparison. Check every subscript, superscript, sign, summation bound, and constant. If the guide uses different notation than the paper, note the exact mapping.
>    - `supporting-formula`: Confirm it computes the correct thing. Notational differences are acceptable if internally consistent.
>    - `numerical-fact`: Find the exact number in the source. Must match.
>    - `qualitative` / `attribution` / `methodological`: Confirm the paper actually says this.
>
> 7. **Mark each claim** in the tracking file:
>    - `Yes` -- verified correct
>    - `Yes (notation)` -- correct but uses different notation; explain the mapping in Notes
>    - `FIXED` -- was wrong, you corrected it. In Notes, write `was: {old} -> now: {new}`
>    - `unverified` -- couldn't access source
>
> 8. **For `[uncited]` claims**: Identify the correct source paper, verify against it, and note the citation key that should be added.
>
> 9. **Fix errors directly:**
>    - For a single wrong sign/subscript/constant: use the Edit tool on the `.tex` file
>    - Add the paper page reference in the "Paper page" column (e.g., "p.12, Eq.4")
>    - If you need to add a new bib entry, append it to `vol-learning-guide/references.bib`
>
> 10. **Update the tracking file header**: change Status, update Verified count, update Errors found count.
>
> Be meticulous. A wrong subscript in a defining formula will cause the LLM to write incorrect code. When in doubt, flag it rather than assuming it's correct.

- [ ] **Step 1: Dispatch Opus 4.6 subagent** with the prompt above
- [ ] **Step 2: Review the subagent's changes** -- check the tracking file for any `FIXED` claims and verify the `.tex` edits are correct
- [ ] **Step 3: If structural rewrites were needed**, invoke the write-chapter skill for affected sections
- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/verification/ch10-feature-engineering.md \
       vol-learning-guide/chapters/10-feature-engineering.tex \
       vol-learning-guide/references.bib
git commit -m "verify(ch10): fact-check feature engineering chapter against source papers"
```

- [ ] **Step 5: Update README.md** with Ch 10's final numbers

---

## Task 8: Pass 2 -- Verify Ch 6 (HAR Model)

**Priority:** Tier 1, #2 -- primary baseline model.

**Files:**
- Modify: `vol-learning-guide/verification/ch06-har-model.md`
- Modify (if errors): `vol-learning-guide/chapters/06-har-model.tex`
- Modify (if new citations): `vol-learning-guide/references.bib`

**Dispatch 1 Opus 4.6 subagent** using the same verification prompt template from Task 7, substituting:
- Tracking file: `vol-learning-guide/verification/ch06-har-model.md`
- Chapter file: `vol-learning-guide/chapters/06-har-model.tex`
- Context note: "This is Chapter 6 (The HAR Model). It defines the HAR-RV baseline and its extensions (HAR-J, HAR-CJ, SHAR, HARQ). The HAR equation and its variants are the most important defining formulas in the entire guide -- they are the benchmarks every ML model must beat."

- [ ] **Step 1: Dispatch Opus 4.6 subagent**
- [ ] **Step 2: Review changes**
- [ ] **Step 3: Structural rewrites if needed (write-chapter skill)**
- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/verification/ch06-har-model.md \
       vol-learning-guide/chapters/06-har-model.tex \
       vol-learning-guide/references.bib
git commit -m "verify(ch06): fact-check HAR model chapter against source papers"
```

- [ ] **Step 5: Update README.md**

---

## Task 9: Pass 2 -- Verify Ch 4 (Jumps & Continuous Variation)

**Priority:** Tier 1, #3 -- jump features feed HAR-J, HAR-CJ, SHAR.

**Files:**
- Modify: `vol-learning-guide/verification/ch04-jumps-continuous-variation.md`
- Modify (if errors): `vol-learning-guide/chapters/04-jumps-continuous-variation.tex`
- Modify (if new citations): `vol-learning-guide/references.bib`

**Dispatch 1 Opus 4.6 subagent** using the same verification prompt template from Task 7, substituting:
- Tracking file: `vol-learning-guide/verification/ch04-jumps-continuous-variation.md`
- Chapter file: `vol-learning-guide/chapters/04-jumps-continuous-variation.tex`
- Context note: "This is Chapter 4 (Jumps and Continuous Variation). It defines bipower variation, jump test statistics (BNS z-test, ratio test, Lee-Mykland), and the continuous/jump decomposition. These formulas feed directly into HAR-J, HAR-CJ, and SHAR features."

- [ ] **Step 1: Dispatch Opus 4.6 subagent**
- [ ] **Step 2: Review changes**
- [ ] **Step 3: Structural rewrites if needed**
- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/verification/ch04-jumps-continuous-variation.md \
       vol-learning-guide/chapters/04-jumps-continuous-variation.tex \
       vol-learning-guide/references.bib
git commit -m "verify(ch04): fact-check jumps chapter against source papers"
```

- [ ] **Step 5: Update README.md**

---

## Task 10: Pass 2 -- Verify Ch 16 (Forecast Evaluation)

**Priority:** Tier 1, #4 -- wrong loss function = wrong model selection.

**Files:**
- Modify: `vol-learning-guide/verification/ch16-forecast-evaluation.md`
- Modify (if errors): `vol-learning-guide/chapters/16-forecast-evaluation.tex`
- Modify (if new citations): `vol-learning-guide/references.bib`

**Dispatch 1 Opus 4.6 subagent** using the same verification prompt template from Task 7, substituting:
- Tracking file: `vol-learning-guide/verification/ch16-forecast-evaluation.md`
- Chapter file: `vol-learning-guide/chapters/16-forecast-evaluation.tex`
- Context note: "This is Chapter 16 (Forecast Evaluation). It defines QLIKE, MSE, Diebold-Mariano test, Model Confidence Set, Mincer-Zarnowitz regression, and purged k-fold CV. The QLIKE formula and DM test statistic are the most critical defining formulas -- these will be used to select the final model."

- [ ] **Step 1: Dispatch Opus 4.6 subagent**
- [ ] **Step 2: Review changes**
- [ ] **Step 3: Structural rewrites if needed**
- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/verification/ch16-forecast-evaluation.md \
       vol-learning-guide/chapters/16-forecast-evaluation.tex \
       vol-learning-guide/references.bib
git commit -m "verify(ch16): fact-check forecast evaluation chapter against source papers"
```

- [ ] **Step 5: Update README.md**

---

## Task 11: Pass 2 -- Verify Tier 2 Chapters (Ch 3, 5, 11, 2, 12-R)

**Priority:** Tier 2, model-critical. Dispatch 2-3 parallel subagents at a time to avoid merge conflicts on `references.bib`.

**Files:**
- Modify: 5 tracking files in `vol-learning-guide/verification/`
- Modify (if errors): 5 chapter `.tex` files
- Modify (if new citations): `vol-learning-guide/references.bib`

### Batch A: Ch 3 + Ch 5 (parallel)

**Dispatch 2 parallel Opus 4.6 subagents** using the verification prompt from Task 7, substituting:

**Subagent 1 -- Ch 3 (Microstructure Noise):**
- Tracking: `vol-learning-guide/verification/ch03-microstructure-noise.md`
- Chapter: `vol-learning-guide/chapters/03-microstructure-noise.tex`
- Context: "Chapter 3 defines TSRV, MSRV, Realized Kernels, pre-averaging, and QMLE. These estimator formulas determine how RV is computed from noisy tick data."

**Subagent 2 -- Ch 5 (GARCH Family):**
- Tracking: `vol-learning-guide/verification/ch05-garch-family.md`
- Chapter: `vol-learning-guide/chapters/05-garch-family.tex`
- Context: "Chapter 5 defines GARCH(1,1), EGARCH, GJR-GARCH, FIGARCH, Realized GARCH, and HEAVY models. The Realized GARCH measurement equation is a key defining formula."

- [ ] **Step 1: Dispatch 2 parallel subagents for Ch 3 + Ch 5**
- [ ] **Step 2: Review changes, merge any bib additions**
- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/verification/ch03-microstructure-noise.md \
       vol-learning-guide/verification/ch05-garch-family.md \
       vol-learning-guide/chapters/03-microstructure-noise.tex \
       vol-learning-guide/chapters/05-garch-family.tex \
       vol-learning-guide/references.bib
git commit -m "verify(ch03,ch05): fact-check microstructure noise and GARCH chapters"
```

### Batch B: Ch 11 + Ch 2 (parallel)

**Subagent 1 -- Ch 11 (Tree Methods):**
- Tracking: `vol-learning-guide/verification/ch11-tree-methods-vol.md`
- Chapter: `vol-learning-guide/chapters/11-tree-methods-vol.tex`
- Context: "Chapter 11 covers random forests, gradient boosting (XGBoost/LightGBM), and DART for volatility forecasting. Key claims are about feature importance rankings and benchmark results from CSV2023 and HARd-to-Beat papers."

**Subagent 2 -- Ch 2 (Realized Volatility):**
- Tracking: `vol-learning-guide/verification/ch02-realized-volatility.md`
- Chapter: `vol-learning-guide/chapters/02-realized-volatility.tex`
- Context: "Chapter 2 defines realized variance, realized volatility, and the theory of quadratic variation. The RV definition formula is foundational to the entire guide."

- [ ] **Step 4: Dispatch 2 parallel subagents for Ch 11 + Ch 2**
- [ ] **Step 5: Review changes, merge bib additions**
- [ ] **Step 6: Commit**

```bash
git add vol-learning-guide/verification/ch11-tree-methods-vol.md \
       vol-learning-guide/verification/ch02-realized-volatility.md \
       vol-learning-guide/chapters/11-tree-methods-vol.tex \
       vol-learning-guide/chapters/02-realized-volatility.tex \
       vol-learning-guide/references.bib
git commit -m "verify(ch11,ch02): fact-check tree methods and realized volatility chapters"
```

### Batch C: Ch 12-R (sequential, single agent)

**Subagent -- Ch 12-R (Rashomon/Interpretable Trees):**
- Tracking: `vol-learning-guide/verification/ch12r-rashomon-interpretable-trees.md`
- Chapter: `vol-learning-guide/chapters/12-rashomon-interpretable-trees.tex`
- Context: "Chapter 12-R covers Rashomon sets, TreeFARMS, RID, VRIC, and STreeD. Key papers are Xin et al. 2022, Donnelly et al. 2023, Dong & Rudin 2020, Van den Bos et al. 2024. These are recently added and particularly need verification."

- [ ] **Step 7: Dispatch 1 subagent for Ch 12-R**
- [ ] **Step 8: Review changes**
- [ ] **Step 9: Commit**

```bash
git add vol-learning-guide/verification/ch12r-rashomon-interpretable-trees.md \
       vol-learning-guide/chapters/12-rashomon-interpretable-trees.tex \
       vol-learning-guide/references.bib
git commit -m "verify(ch12r): fact-check Rashomon interpretable trees chapter"
```

- [ ] **Step 10: Update README.md with all Tier 2 results**

---

## Task 12: Pass 2 -- Verify Tier 3 Chapters (Ch 8, 9, 7, 12-DL, 13, 14, 15, 1, 17)

**Priority:** Tier 3, context and enrichment. Batch into groups of 3 parallel subagents.

**Files:**
- Modify: 9 tracking files in `vol-learning-guide/verification/`
- Modify (if errors): 9 chapter `.tex` files
- Modify (if new citations): `vol-learning-guide/references.bib`

### Batch A: Ch 8 + Ch 9 + Ch 7 (parallel)

**Dispatch 3 parallel Opus 4.6 subagents** using the verification prompt from Task 7, substituting:

**Subagent 1 -- Ch 8 (Options & Vol Surface):**
- Tracking: `vol-learning-guide/verification/ch08-options-vol-surface.md`
- Chapter: `vol-learning-guide/chapters/08-options-vol-surface.tex`
- Context: "Chapter 8 covers Black-Scholes, implied volatility, the volatility smile/skew, SVI parameterization, and VIX. The Black-Scholes formula, SVI parameterization (Gatheral & Jacquier 2014), and VIX formula (CBOE 2019) are key defining formulas."

**Subagent 2 -- Ch 9 (Variance Risk Premium):**
- Tracking: `vol-learning-guide/verification/ch09-variance-risk-premium.md`
- Chapter: `vol-learning-guide/chapters/09-variance-risk-premium.tex`
- Context: "Chapter 9 defines the variance risk premium (VRP = IV^2 - RV), variance swaps, and VRP as a predictor. Key sources: Carr & Wu 2009, Bollerslev-Tauchen-Zhou 2009, Bekaert & Hoerova 2014."

**Subagent 3 -- Ch 7 (Rough Volatility):**
- Tracking: `vol-learning-guide/verification/ch07-rough-volatility.md`
- Chapter: `vol-learning-guide/chapters/07-rough-volatility.tex`
- Context: "Chapter 7 covers fractional Brownian motion, the rough Heston model, the Hurst exponent, and the GJR 2018 / Cont-Das 2024 debate. The fBm variogram, rough volatility scaling law, and Hurst estimation formulas are key."

- [ ] **Step 1: Dispatch 3 parallel subagents**
- [ ] **Step 2: Review, merge bib, commit**

```bash
git commit -m "verify(ch08,ch09,ch07): fact-check options, VRP, and rough vol chapters"
```

### Batch B: Ch 12-DL + Ch 13 + Ch 14 (parallel)

**Subagent 1 -- Ch 12-DL (Deep Learning):**
- Tracking: `vol-learning-guide/verification/ch12-deep-learning-vol.md`
- Chapter: `vol-learning-guide/chapters/12-deep-learning-vol.tex`
- Context: "Chapter 12-DL covers LSTMs, TCN/WaveNet, DeepVol, DeepLOB, GNNs, and neural SDEs for volatility. Key papers: Bucci 2020, Moreno-Pino & Zohren 2022."

**Subagent 2 -- Ch 13 (Hybrid/Ensemble):**
- Tracking: `vol-learning-guide/verification/ch13-hybrid-ensemble.md`
- Chapter: `vol-learning-guide/chapters/13-hybrid-ensemble.tex`
- Context: "Chapter 13 covers residual boosting on HAR, GARCH-informed neural networks (GINN), NLP augmentation, stacking, and model combination. Key papers: Rahimikia-Zohren-Poon 2021, GINN 2024."

**Subagent 3 -- Ch 14 (Multivariate Volatility):**
- Tracking: `vol-learning-guide/verification/ch14-multivariate-volatility.md`
- Chapter: `vol-learning-guide/chapters/14-multivariate-volatility.tex`
- Context: "Chapter 14 covers realized covariance, DCC, Cholesky/vech HAR, multivariate realized kernels, and graph neural networks for covariance. Key papers: Engle 2002 DCC, Barndorff-Nielsen et al. 2011, Chiriac & Voev 2011."

- [ ] **Step 3: Dispatch 3 parallel subagents**
- [ ] **Step 4: Review, merge bib, commit**

```bash
git commit -m "verify(ch12dl,ch13,ch14): fact-check deep learning, hybrid, and multivariate chapters"
```

### Batch C: Ch 15 + Ch 1 + Ch 17 (parallel)

**Subagent 1 -- Ch 15 (Spillovers):**
- Tracking: `vol-learning-guide/verification/ch15-spillovers-connectedness.md`
- Chapter: `vol-learning-guide/chapters/15-spillovers-connectedness.tex`
- Context: "Chapter 15 covers Diebold-Yilmaz spillover index, generalized variance decomposition, TVP-VAR connectedness. Key papers: Diebold & Yilmaz 2009, 2012, 2014."

**Subagent 2 -- Ch 1 (Returns/Variance):**
- Tracking: `vol-learning-guide/verification/ch01-returns-variance-volatility.md`
- Chapter: `vol-learning-guide/chapters/01-returns-variance-volatility.tex`
- Context: "Chapter 1 covers log returns, variance, stylized facts (fat tails, volatility clustering, leverage effect). Foundational and well-established -- errors unlikely but verify."

**Subagent 3 -- Ch 17 (Applications):**
- Tracking: `vol-learning-guide/verification/ch17-applications-projects.md`
- Chapter: `vol-learning-guide/chapters/17-applications-projects.tex`
- Context: "Chapter 17 is short (214 lines) and covers practical applications. Light verification -- mostly methodological claims."

- [ ] **Step 5: Dispatch 3 parallel subagents**
- [ ] **Step 6: Review, merge bib, commit**

```bash
git commit -m "verify(ch15,ch01,ch17): fact-check spillovers, returns, and applications chapters"
```

- [ ] **Step 7: Update README.md with all Tier 3 results**

---

## Task 13: Final Compilation and Recompile

**Files:**
- Modify: `vol-learning-guide/verification/README.md`

- [ ] **Step 1: Update README.md** with final totals across all chapters -- total claims, total verified, total errors found, total unverified

- [ ] **Step 2: List all `FIXED` claims across all tracking files** -- create a summary of every correction made

- [ ] **Step 3: List all `unverified` claims** -- these are the remaining gaps where source papers couldn't be found

- [ ] **Step 4: Recompile the PDF** if any `.tex` files were modified:

```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && cd ..
```

- [ ] **Step 5: Commit final state**

```bash
git add vol-learning-guide/verification/README.md vol-learning-guide/main.pdf
git commit -m "chore(verification): final compilation -- all chapters verified"
```
