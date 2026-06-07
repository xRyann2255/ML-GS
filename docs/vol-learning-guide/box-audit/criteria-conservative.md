# Box & Fluff Audit — Criteria (vol-learning-guide)

This is the rubric for the conservative box/fluff sweep of `vol-learning-guide`.
Finder and Skeptic agents read this file as their authority. **When in doubt, KEEP.**

## Goal

The guide has ~940 boxes across 20 chapters (~47/chapter). It reads long and box-heavy.
We want a *conservative* reduction: remove only boxes that clearly do not earn their
place, shorten bloated ones, and trim clearly fluffy prose — **without losing any
genuine teaching value, math, definitions, citations, or factual claims.**

## Verdict model (three-way, not cut/keep)

- **KEEP** — earns its place. Leave untouched.
- **TRIM** — the box belongs, but is bloated. Keep the box, shorten its contents.
  This is the *default* fix for "too wordy." Prefer TRIM over CUT.
- **CUT** — remove the box entirely.

A box is a **CUT candidate only if** it clearly meets **≥1 failure test** AND triggers
**no keep-guard**. Otherwise it is KEEP or TRIM.

## Box failure tests (what makes a box not earn its place)

1. **Restatement** — merely repeats adjacent prose, a nearby equation, or another box,
   adding no new framing, example, analogy, or caution.
2. **Triviality** — explains something self-evident to the audience (a quant intern
   fluent in statistics and ML). E.g. an `intuition` box explaining what a mean is.
3. **Vacuous "why this matters"** — a `projectconnection` that asserts generic
   importance with no *specific* hook: no named dataset, model, metric, or decision.
4. **Empty worked example** — a `workedexample` that plugs trivial numbers into a
   just-stated formula and yields no insight beyond the formula itself.
5. **Cluster overlap** — two same-type boxes stacked together with heavy content
   overlap; one should be cut or merged into the other.

## Keep-guards (any one ⇒ never CUT; TRIM at most)

- It is a `prereq` chapter-opener — **protected type, never cut.**
- Explains something genuinely hard or counterintuitive in plain English
  (the high-value `intuition` boxes).
- Warns of a real, non-obvious pitfall (`warning`).
- Defines a key term that is used later.
- A `workedexample` that reveals a subtlety or builds real intuition.
- A `projectconnection` that names a *concrete* dataset, model, metric, or decision.
- States a headline empirical result (`keyresult`).

## Conservativeness rules

- Default to **KEEP**. Only escalate to **CUT** when the case is unambiguous.
- Most "too wordy" problems should resolve to **TRIM**, not CUT.
- `prereq` chapter-openers are exempt from CUT (TRIM-eligible only).
- Expected outcome per chapter: a handful of CUTs, more TRIMs, most boxes KEEP.
  Roughly 15–20% of boxes affected by CUT across the guide — not more.

## Prose-fluff tests (flag → propose a tightened rewrite or deletion)

Flag a prose passage only when the case is clear. **Never alter math, term definitions,
citations, numbers, or factual/empirical claims.** Preserve all meaning.

1. **Pseudo-intellectual / inflated wording** — fancy words where plain ones work;
   abstract throat-clearing ("in a deep sense, the fundamental nature of…").
2. **Filler & hedging** — "It is important to note that", "As we shall see",
   "in order to" (→ "to"), "the fact that", "It bears mentioning", "Needless to say".
3. **Restatement / repetition** — a sentence or paragraph repeating the prior one.
4. **Throat-clearing transitions & over-signposting** — excessive "Having established X,
   we now turn to Y, which as we will see is crucial…".

Each fluff finding proposes either a **tightened rewrite** (preserving every fact) or a
**deletion** of the redundant span.

## Locators (so Phase 2 can find each box reliably)

Line numbers shift as edits apply, so each finding records a robust locator:
`nearest \section/\subsection title` + `the box's optional title argument (if any)` +
`the first ~8 words of the box body`. For fluff: nearest heading + the verbatim snippet.

## Out of scope (do not touch)

- Equations, derivations, tables, figures, TikZ.
- Citations (`\citep`, `\citet`) and the bibliography.
- Definitions of terms (the `definition` boxes' core content) — TRIM-eligible only.
- `prereq` chapter-openers (CUT-exempt).
- Anything where removing/changing it would alter a factual or empirical claim.
