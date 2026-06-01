# Deep Research Distill v2 — Design

**Date:** 2026-06-01
**Status:** Approved (design); ready for implementation plan
**Target:** `.claude/workflows/deep-research-distill.js`

## Problem

The current `deep-research-distill` workflow (Scope → Harvest → Verify → Distill) researches a
question, adversarially verifies sources, and writes a markdown brief into
`notes/deep-research/`. The brief ends with a *"Papers to Ingest"* list — but it only **names**
papers; it never downloads them. Three things are missing for the user's needs:

1. It cannot acquire the papers it recommends (manual download afterward).
2. It is not aggressively biased toward **state-of-the-art / current methodologies** or the latest sources.
3. Source attribution is good in the evidence table but not enforced everywhere; some numbers are stated without a precise location in the source.

## Goal

Upgrade the workflow so that, from one question, it:
- researches the **current state of the art and the methodologies actively used today** (the primary lens),
- **downloads the relevant open-access papers** into the existing `reference/project-papers/` folder, deduped against what we already hold, recovering open versions of paywalled journal papers where they exist,
- ranks and weights sources **peer-review-first**,
- writes a brief in which **every number, claim, and method statement is traced to its source** (author-year + link + section/table anchor),
- and updates the `reference/project-papers/README.md` index in place.

Non-goals: auto-committing downloads; building a citation graph; generating BibTeX; reorganizing the
flat papers folder into subdirectories; downloading paywalled PDFs we have no open route to.

## New flow

```
Scope  →  Harvest  →  Verify  →  Acquire (NEW)  →  Distill
```

### Phase 1 — Scope (modified)

- **Re-centered interpretation.** The default research lens becomes *"what is the current
  state of the art for this question, and which methodologies are actively used today"* — facets are
  organized around current method families and their newest results, not just a generic decomposition.
- **Existing-papers inventory (new first-class output).** The Scope agent explicitly inventories
  `reference/project-papers/`: every filename, arXiv ID (parsed from filename or README), and title,
  plus the README's "Papers Still Needed" list. This `alreadyHave` list flows downstream so Harvest
  never chases what we hold and Acquire never re-downloads it.
- **Mandatory `frontier` facet.** Scope must always emit a dedicated `frontier` facet aimed at the
  newest preprints / working papers (last ~18 months).
- `PLAN_SCHEMA` gains an `alreadyHave` array (filename, id, title per entry) distinct from the existing
  prose `alreadyKnown`.

### Phase 2 — Harvest (modified)

- **Date-biased queries.** Each facet's queries get date-qualified variants appended at harvest time:
  the target year, the prior year, "latest", and arXiv recent-listing-style searches. The target year
  is derived from the slug's `YYYY-MM-DD` prefix (no `Date.now()` — unavailable in workflow scripts);
  defaults to a recent baseline constant if the slug has no date prefix.
- Harvest agents are told the `alreadyHave` list and instructed **not** to spend effort re-finding
  those papers (they may still cite them as known baselines, but should not propose them for download).
- Existing `snippetEvidence` requirement retained.

### Phase 3 — Verify (modified)

- `VERIFY_SCHEMA` gains a **`claimLocation`** field: where in the source the load-bearing claim lives
  (e.g. "Table 4", "§4.1", "abstract", "p. 12"). Used so the brief can point precisely.
- Verify continues to set `grounded`, `credibility`, `correction`, `keep`.

### Top-N selection — peer-review-first (modified)

- Selection sort changes from `relevance` alone to a **credibility-weighted score**:
  `score = relevance × tierWeight`, where `tierWeight`: peer-reviewed > preprint > practitioner
  (e.g. 1.0 / 0.8 / 0.5). Applied after verification so credibility is known.
- This raises peer-reviewed primary sources to the top of both the dossier and the download queue.

### Phase 4 — Acquire (NEW)

Inserted between Verify and Distill so the brief reflects what was actually fetched.

- **Inputs:** verified, kept sources of type `paper`/`preprint` only (blogs/docs/datasets are never
  downloaded), ordered by the credibility-weighted score; plus the `alreadyHave` inventory.
- **Per-paper procedure (one agent, or a small parallel set, with Bash + WebSearch + WebFetch):**
  1. Re-confirm the paper is not already in `reference/project-papers/` (match by arXiv ID and by
     fuzzy author-year-title). Skip with outcome `already-present` if held.
  2. Resolve an **open-access PDF URL**: arXiv `/pdf/<id>` first; otherwise a direct open publisher /
     working-paper PDF.
  3. If the only known source is **paywalled** (journal DOI, locked SSRN, etc.), actively **hunt for an
     open-access equivalent**: arXiv/SSRN/RePEc/NBER working-paper version, author homepage PDF, or a
     Semantic Scholar / OpenReview open PDF. Download that instead.
  4. Download via `curl -L -o` into `reference/project-papers/` using the existing
     `firstauthor-year-shorttitle.pdf` naming convention.
  5. Verify the download is a real PDF (non-trivial byte size, `%PDF` header) — else mark `failed`.
- **Outcome per paper:** `downloaded` / `already-present` / `paywalled` (no open route found) /
  `failed`. The set of outcomes is the **download manifest**.
- **No auto-commit.** New PDFs and README edits are left staged for user review.

### README auto-update (within Acquire, after downloads)

- For each **newly downloaded** paper, append a row to the correct category section (A–E) of
  `reference/project-papers/README.md`, matching the existing table format, with a Status
  (`Recommended` by default; `Essential` only if clearly foundational).
- For papers with **no open route**, add them to the "Papers Still Needed (paywalled)" section.
- Idempotent: skip if the filename already appears in the README.

### Phase 5 — Distill (modified)

- **Full source traceability (hard rule).** Every number, claim, and methodology statement in the
  brief must carry an explicit inline source reference: author-year + link, plus the `claimLocation`
  anchor (table/section/page) where the verifier captured one. If a figure cannot be traced to fetched
  text, it does not appear. Practitioner sources are explicitly tagged context-only.
- **SOTA framing.** The Direct Answer and Key Insights lead with the current state of the art and the
  methodologies in active use, then caveats.
- **New section: "What's new since our last sweep"** — the freshest sources and what they add beyond
  the repo's existing notes.
- **New section: "Papers Acquired"** — reports the download manifest: which PDFs were downloaded
  (with final filename), which were already present, which remain paywalled/still-needed, and for any
  open-access-equivalent recovery, a note that the open version was used.
- Existing sections retained: Evidence Table, Code to Study, Contradictions & Open Threads,
  New vs Already Known.

## Return value (modified)

The workflow's return object gains: `downloaded` (filenames), `alreadyPresent`, `paywalledStillNeeded`,
and the `readmeUpdated` flag, alongside the existing summary fields.

## Constraints / notes

- Workflow scripts are plain JS; `Date.now()`/`Math.random()`/argless `new Date()` are unavailable —
  derive the year from the slug.
- Downloads use the Bash tool's `curl` (available on the Windows box). Validate the `%PDF` header.
- Respect repo norm: never auto-commit; leave changes staged.
- Keep the flat folder layout; do not reorganize existing PDFs.

## Acceptance

- A run on a real question downloads ≥1 new open-access PDF into `reference/project-papers/` with a
  correct `author-year-shorttitle.pdf` name, with no duplicate of an existing file.
- At least one paywalled-in-README paper is recovered via an open-access equivalent (when one exists).
- The README gains correctly-placed rows for new downloads; paywalled-without-route papers land in
  "Papers Still Needed".
- The brief contains no untraceable number; each carries a source + location anchor.
- The brief leads with SOTA / current methodologies and includes the "What's new" and "Papers Acquired"
  sections.
- Nothing is committed automatically.
