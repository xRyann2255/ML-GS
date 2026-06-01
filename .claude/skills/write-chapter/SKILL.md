---
name: write-chapter
description: Multi-pass pipeline for writing LaTeX learning guide chapters: source extraction → contract → write → verify → condense → naive-reader review. The contract fixes notation, labels, and citations before drafting; every formula verified against source papers.
---

# Write Chapter

Write a complete LaTeX chapter using a staged quality pipeline: source extraction → contract → write → verify → condense → naive-reader review.

## Input

The user specifies:
- **Topic**: what the chapter covers
- **Guide**: which guide it belongs to (`vol-learning-guide`, `quant-trading`, `vol-project-ref`, or a new one)
- **Source papers**: specific papers from `reference/` to read in Pass 0. For each paper, specify which pages/sections to extract (e.g., "Xin et al. 2022 pp.3-7: Rashomon set definition, enumeration algorithm")

## Learning Style Requirements

These apply throughout ALL passes. The reader needs to build theory intuitively from the ground up:

### Equation Pattern (mandatory for every equation)

1. **Setup sentence** (1-2 sentences before the equation): explain what we're trying to capture or formalize — what problem this equation solves
2. **The equation itself**
3. **Symbol definitions** (itemized list): what each variable/symbol represents
4. **Plain English translation** (use `\begin{intuition}[In Plain English]` box): 2-3 sentences explaining what the whole equation DOES conceptually, as a unit — not what the parts are, but what it MEANS
5. **Project connection** (use `\begin{projectconnection}` box): explicit link to vol forecasting — why this matters for the project, what it feeds into, or what would break without it

### Diagrams

Add geometric/graphical TikZ illustrations for important concepts — especially when:
- An equation describes a geometric or dynamic relationship (e.g., a price path, convergence, accumulation)
- A concept involves a process or flow that's easier to SEE than read
- The relationship between quantities is spatial or temporal

Do NOT add a diagram for every equation. Use judgment — only when a visual genuinely unlocks understanding.

**After writing any TikZ diagram, invoke the `verify-diagram` skill.** Pass it: the guide root, a unique caption/label substring on the figure's page, a one-line **concept** (what the diagram should teach), and the intended **relationships** (the arrows/dependencies it should encode -- this enables the correctness lens). The engine crops the figure to high resolution, runs deterministic geometric checks plus two blind reviewers (legibility + learning-clarity), and loops fix->re-verify until both gates pass. If it returns a **`needs-human`** result (it hit the iteration cap), do NOT proceed -- surface the remaining defects to the user and resolve them before submitting the chapter. Never submit a chapter with an unverified diagram.

### Worked Examples

Only include worked numerical examples when they serve theory comprehension (e.g., showing WHY a formula produces a surprising result, or building intuition about magnitudes). Do NOT include computation-practice examples.

### Tone

- Write as if explaining to a smart person building intuition from scratch
- Every term defined on first use (bold)
- Verbose definitions are good — err on the side of over-explaining concepts
- Before introducing complexity, make sure the simpler version is fully internalized

## Pass 0 -- Source Extraction (runs before Pass 1)

Before writing begins, the agent reads the specified source papers and produces a structured extraction. For each paper:

1. Read only the specific pages/sections relevant to the chapter's topics (not full papers)
2. For each formula, definition, claim, or threshold found, record:

```
PAPER: [Author Year] ([short title])
PAGE: [page number]
TYPE: FORMULA | DEFINITION | CLAIM | THRESHOLD
CONTENT: [exact content from paper]
NOTATION: [symbol definitions as used in the paper]
GUIDE_NOTATION: [how to adapt notation to match learning guide conventions]
```

Rules:
- Every formula must include the exact equation number and page from the source
- Every quantitative claim (e.g., "5-15% QLIKE improvement") must have a paper source
- If a claim appears in the spec or vol-project-ref but has no paper backing it, flag it and do not include it in the chapter
- The extraction stays in the agent's context as ground truth for Pass 1. Do not save it as a file.

## Chapter Contract (after Pass 0, before Pass 1)

Before writing a single line of prose, fix the chapter's structural decisions in one place. A chapter's value is its connective tissue — one voice, consistent notation, a dense web of cross-references — and that is exactly what drifts over a long file: notation gets redefined, labels collide or dangle, claims wander from their sources. The contract is the guardrail. Like the Pass 0 extraction, it stays in the agent's context as ground truth for Pass 1; do not save it as a file.

1. Read the target guide's `preamble.tex` or `conventions.tex` for the available box types and the exact macro set, and read `main.tex` for the chapter's place in the structure and the label prefixes existing chapters already use.
2. Record the contract:

```
SECTIONS: ordered list, simplest-first so each section builds on the last
  - [section title] — covers [subtopics]; assumes only [earlier sections/chapters]
NOTATION: every quantity → the exact preamble macro to use (never redefine inline)
  - realized variance → \RV ; bipower variation → \BPV ; QLIKE loss → \QLIKE ; ...
LABELS: this chapter's unique prefix scheme (no collisions with existing chapters)
  - sections sec:<ch>:<slug> ; equations eq:<ch>:<slug> ; figures fig:<ch>:<slug> ; definitions def:<ch>:<slug>
CITATIONS: which Pass 0 source anchors which claim/section
  - [claim or section] ← [Author Year], p.[page], eq.[n]
```

Rules:
- Every macro listed must already exist in the guide's preamble. If a needed macro is missing, note it so it can be added to the preamble — never silently redefine notation inside the chapter
- Every label uses this chapter's prefix; check `main.tex` and sibling chapters so no label is reused
- Every claim in the SECTIONS plan must trace to a CITATIONS entry drawn from the Pass 0 extraction — if it has no source, it does not go in the plan
- Surface the SECTIONS outline to the user for a quick sanity check before drafting. Reordering or rescoping is cheap now and expensive once the prose exists

## Pass 1 — Writer (main agent)

Write the full chapter `.tex` file following the guide's conventions:

1. Follow the Chapter Contract — its section order, notation macros, label scheme, and citation map are now fixed. Do not improvise new notation or labels mid-draft; if you genuinely need something the contract lacks, amend the contract first, then write
2. Write the chapter following CLAUDE.md guide-writing rules AND the Learning Style Requirements above:
   - Opening paragraph: concrete question or problem, not abstract definition
   - Prerequisites box at the start
   - Every equation follows the mandatory pattern (setup → equation → symbols → plain English → project connection)
   - `\underbrace{}` annotations on complex math
   - `booktabs` tables, `listings` for code
   - Define every term on first use (bold)
   - Geometric diagrams for key concepts
3. Save as `guides/<guide>/chapters/<filename>.tex`
4. **Mid-write paper discovery:** If you encounter a concept that needs a citation or formula not in the Pass 0 extraction:
   a. Search `reference/project-papers/` and `reference/papers/` for relevant papers
   b. If found, read the relevant pages and extract the needed material
   c. If not found in the repo, search the web for the paper (arXiv, open-access proceedings, author websites)
   d. If available, download it to `reference/project-papers/` and extract the needed material
   e. If behind a paywall, note it as a gap and write around it -- never guess a formula
   f. Add the new source to the contract's CITATIONS map so provenance stays complete

## Pass 2 — Verifier (parallel sub-agent)

Dispatch a sub-agent with this prompt:

> Read the draft chapter at [path]. For every `\citep{}` and `\citet{}` command in the chapter:
> 1. Find the cited paper in `reference/project-papers/` or `reference/papers/`
> 2. Read the specific pages referenced (or search for the relevant content)
> 3. Verify that every formula in the chapter matches the source paper (correct signs, terms, notation)
> 4. Verify that every quantitative claim matches what the paper actually reports
> 5. Flag any discrepancy as CRITICAL with: [chapter line, what it says, what the paper says, page in paper]
>
> Also search for papers NOT yet cited that are relevant to claims in the chapter, and suggest additional citations.
>
> Output:
> - A numbered list of verification results (PASS or CRITICAL for each citation)
> - A numbered list of suggested additional citations with line locations

## Pass 3 — Condenser (parallel sub-agent, simultaneous with Pass 2)

Dispatch a sub-agent with this prompt:

> Read the draft chapter at [path]. Identify:
> - Redundant explanations (same idea said twice in different words)
> - Overly verbose passages that can be tightened without losing meaning
> - Filler phrases and hedge words that add no information
> - Paragraphs that repeat earlier content
>
> IMPORTANT: Do NOT flag "plain English" intuition boxes or project connection boxes as redundant — these are intentional and serve the reader's learning style. Only flag TRUE redundancy where the same idea appears twice with no added value.
>
> Output specific edit suggestions: "Lines X-Y: cut/merge/tighten because [reason]"

## Consolidation (main agent)

After both Pass 2 and Pass 3 complete:
1. Apply citation suggestions from Pass 2 (add `\citep{}`/`\citet{}` commands, add entries to `references.bib` if needed)
2. Apply condensing edits from Pass 3 (cut redundancy, tighten prose)
3. Save the revised chapter

## Pass 4 — Naive Reader (sequential sub-agent)

Dispatch a sub-agent with this prompt:

> You are NOT a smart student. You are someone with ZERO quantitative background trying to understand this material for the absolute first time. You struggle with abstraction. You need everything spelled out. You panic when you see an equation you don't understand.
>
> Read the chapter at [path] and flag EVERY single moment where you feel lost, confused, or unsure. Be extremely aggressive — if there is even 1% doubt, flag it. Specifically look for:
>
> - Equations without a plain English "what this means as a whole" translation — flag these as CRITICAL
> - Equations without an explicit connection to vol forecasting — flag as CRITICAL
> - Confusing logical jumps (where did step X come from? Why are we suddenly talking about this?)
> - Terms used before being defined, or defined too briefly
> - Missing intuition (the math is there but you have NO IDEA why you should care)
> - Steps that move too fast (you need an intermediate explanation to follow)
> - Notation introduced without explanation
> - Places where a diagram would help you "see" what's happening but none exists
> - Concepts that feel important but you can't explain WHY they're important to vol forecasting
> - Moments where you understand the individual symbols but not what the equation is DOING
>
> For EVERY issue found, output:
> - Exact location (section, equation number, or line)
> - What specifically confused you
> - What you WISH was there instead
>
> Be merciless. Flag everything. The goal is to catch every possible point of confusion.

## Final (main agent)

1. Apply ALL Pass 4 feedback — add clarifications, plain English translations, project connections, and diagrams where flagged
2. Verify every equation follows the mandatory pattern (setup → equation → symbols → plain English → project connection)
3. Final read-through for coherence
4. Commit the chapter file
5. Update memory (`project-status.md`) with chapter completion
