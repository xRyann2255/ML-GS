# Vol-Learning-Guide Systematic Verification

**Date:** 2026-05-14
**Status:** Approved
**Scope:** Verify every fact, formula, derivation, and qualitative claim in the vol-learning-guide against source papers

## Motivation

The vol-learning-guide serves as the source of truth for LLMs operating on the codebase. Any incorrect formula, wrong sign, or misattributed claim will silently propagate into the implementation. This verification pass ensures every verifiable statement traces back to a confirmed source.

## Claim Taxonomy

| Type | Example | Verification standard |
|---|---|---|
| **Defining formula** | HAR-RV equation, GARCH(1,1) recursion, bipower variation | Symbol-exact against source paper |
| **Supporting formula** | Intermediate derivation steps, variance of estimator expressions | Semantically correct |
| **Numerical fact** | "jumps contribute ~7% of total QV" | Exact number against source paper/table |
| **Qualitative claim** | "TSRV converges at rate n^{-1/6}" | Confirm statement appears in the cited source |
| **Attribution** | "Corsi (2009) proposed the HAR model" | Confirm the paper actually introduces the concept |
| **Methodological claim** | "5-minute sampling is the standard frequency" | Confirm cited source supports this recommendation |

**Excluded:** Pedagogical framing ("think of it like..."), pure notation definitions internal to the guide, chapter structure/flow.

## Chapter Priority Ordering

### Tier 1: Pipeline-critical
1. Ch 10: Feature Engineering (1,568 lines, 264 math, 28 citations)
2. Ch 6: HAR Model (918 lines, 159 math, 35 citations)
3. Ch 4: Jumps & Continuous Variation (915 lines, 148 math, 29 citations)
4. Ch 16: Forecast Evaluation (1,212 lines, 191 math, 29 citations)

### Tier 2: Model-critical
5. Ch 3: Microstructure Noise (1,070 lines, 160 math, 36 citations)
6. Ch 5: GARCH Family (1,008 lines, 192 math, 32 citations)
7. Ch 11: Tree Methods (990 lines, 108 math, 21 citations)
8. Ch 2: Realized Volatility (773 lines, 130 math, 17 citations)
9. Ch 12-R: Rashomon/Interpretable Trees (1,056 lines, 174 math, 35 citations)

### Tier 3: Context and enrichment
10. Ch 8: Options & Vol Surface (1,369 lines, 231 math, 24 citations)
11. Ch 9: Variance Risk Premium (899 lines, 123 math, 32 citations)
12. Ch 7: Rough Volatility (814 lines, 182 math, 30 citations)
13. Ch 12-DL: Deep Learning (919 lines, 124 math, 35 citations)
14. Ch 13: Hybrid/Ensemble (1,324 lines, 152 math, 22 citations)
15. Ch 14: Multivariate Volatility (1,143 lines, 183 math, 16 citations)
16. Ch 15: Spillovers (801 lines, 109 math, 18 citations)
17. Ch 1: Returns/Variance (850 lines, 90 math, 21 citations)
18. Ch 17: Applications (214 lines, 20 math, 3 citations)

## Approach: Two-Pass Pipeline

### Pass 1: Claim Extraction

Scan each chapter and produce a structured tracking file without reading any papers.

**Process per chapter:**
1. Read the full chapter `.tex` file
2. Walk through linearly, identifying every verifiable claim using the taxonomy
3. Write a tracking file `vol-learning-guide/verification/chXX-name.md`:

```markdown
# Chapter XX: Name -- Verification Log

**Status:** Extraction complete / Verification in progress / Verified
**Claims extracted:** N
**Verified:** 0/N
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 45 | defining-formula | $RV_t = \sum r_{t,i}^2$ | Corsi (2009) | | | |
| 2 | 52 | qualitative | "weekly RV averages 5 daily values" | Corsi (2009) | | | |
```

4. Claims without explicit citation get marked `[uncited]` in the source column -- these need a source identified during Pass 2
5. Claims citing multiple papers (e.g., "building on X and Y") get one row per source paper, linked by a shared claim number suffix (e.g., 12a, 12b)

**Parallelization:** Embarrassingly parallel. Multiple subagents can extract from different chapters simultaneously since each writes to its own file.

### Pass 2: Verification

For each claim in the tracking files, open the source paper, find the exact location, verify, and mark the result.

**Process per chapter (in priority order):**
1. Open the chapter's tracking file
2. Sort claims by source paper to minimize re-reading
3. For each source paper:
   - Check if PDF exists in `reference/project-papers/`
   - If missing: web search for free version (arXiv, SSRN, author page), download locally
   - If still missing: verify against textbooks in `reference/books/`
   - If neither works: mark `unverified: paper unavailable`
4. Read the relevant pages of the paper
5. Verify each claim:
   - **Defining formula:** symbol-exact comparison (subscripts, superscripts, signs, bounds)
   - **Supporting formula:** semantically correct, notational differences noted
   - **Numerical fact:** exact match against source table/paragraph
   - **Qualitative/attribution/methodological:** confirm paper actually says this
6. Mark each claim:
   - `Yes` -- verified correct
   - `Yes (notation)` -- correct with different notation; mapping noted
   - `FIXED` -- was wrong, corrected (note what changed)
   - `unverified` -- couldn't access source
7. For `[uncited]` claims: identify the correct source paper, verify the claim against it, and add the `\citep{}`/`\citet{}` reference to the `.tex` file

**Error correction protocol:**
- Single wrong sign/subscript/constant: fix directly via Edit
- Multiple related errors or structural issues: invoke write-chapter skill to rewrite the section
- Track every fix in the tracking file Notes column with before/after

**Parallelization:** Chapters can be verified in parallel by subagents, but corrections via write-chapter should be serialized to avoid merge conflicts. Verify 2-3 chapters in parallel, apply fixes, then next batch.

## Paper Acquisition Strategy

**Priority order:**
1. **Already local** -- 35 PDFs in `reference/project-papers/`, also check `reference/papers/` and `reference/books/`
2. **arXiv/SSRN** -- web search for freely available preprints, download to `reference/project-papers/`
3. **Textbook cross-reference** -- for canonical results (GARCH formula, Black-Scholes, bipower variation), verify against textbooks in `reference/books/`
4. **Author websites** -- many academics host PDFs on personal pages
5. **Flag as unavailable** -- last resort, mark `unverified: paywalled`

Only acquire papers actually cited for claims we're verifying.

**Naming convention:** `lastname-year-short-description.pdf` (matches existing convention).

## Session Management and Resumability

**State lives in the tracking files.** Each `vol-learning-guide/verification/chXX-name.md` is the single source of truth for that chapter's progress.

**Progress summary in `vol-learning-guide/verification/README.md`:**

```markdown
# Verification Progress

Last updated: YYYY-MM-DD

| Chapter | Claims | Verified | Errors | Status |
|---|---|---|---|---|
| Ch 10: Feature Engineering | 87 | 0/87 | 0 | Extraction complete |
| Ch 6: HAR Model | 52 | 52/52 | 3 | Verified |
| **Total** | **~500** | **52/500** | **3** | |
```

**Session workflow:**
1. Read `vol-learning-guide/verification/README.md` for overall progress
2. Pick next chapter in priority order that isn't fully verified
3. Open its tracking file, find first unverified claim
4. Verify claims until session ends
5. Commit updated tracking file (even partial progress)
6. Update README.md totals

**Commit cadence:** After completing each source paper's batch of claims within a chapter.
