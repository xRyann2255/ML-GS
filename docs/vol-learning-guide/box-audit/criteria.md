# Box & Fluff Audit — Criteria (vol-learning-guide) — MODERATE PASS

This is the rubric for the **moderate** box/fluff sweep of `vol-learning-guide`.
Finder and Skeptic agents read this file as their authority.

> A first **conservative** pass cut only 6 of 942 boxes — far too timid for a guide the
> author finds box-heavy and over-padded. This pass raises the bar: **every box must
> actively earn its place.** The default is no longer "keep when in doubt." The default
> is: *if a box does not give the reader something they would not already get from the
> surrounding prose, equations, and neighbouring boxes, it goes.*

## Goal

Reduce box count by roughly **30–40% guide-wide** (a substantial share of that as CUT,
not just TRIM), and tighten clearly fluffy prose — **without removing any genuine
teaching value, math, definitions, citations, or factual/empirical claims.**

## Verdict model (three-way)

- **KEEP** — earns its place; adds something not available nearby. Leave it.
- **TRIM** — has a real kernel of value but is bloated; keep the box, cut the dead weight.
- **CUT** — remove the box entirely; the reader loses nothing they need.

The bar for CUT is **"does not clearly earn its place,"** not "clearly fails." If a box
only restates, only motivates generically, or only explains the obvious — CUT it.

## Box failure tests (any one ⇒ CUT candidate)

1. **Restatement** — repeats adjacent prose, a nearby equation, or another box, even with
   only *heavy partial* overlap. The box adds no new framing, example, analogy, or caution.
2. **Triviality** — explains something a quant intern fluent in statistics and ML already
   knows, or merely narrates an equation in words.
3. **Generic "why this matters"** — a `projectconnection` that motivates in the abstract.
   Under this pass a `projectconnection` survives **only** if it (a) names a *concrete*
   dataset / model / metric / decision **and** (b) that specific point is not already made
   nearby. Generic "this is important because volatility matters" boxes are CUT.
4. **Low-value worked example** — a `workedexample` that plugs numbers into a just-stated
   formula without revealing a subtlety, edge case, scaling gotcha, or building intuition
   the formula alone doesn't give. Mechanical arithmetic walk-throughs are CUT.
5. **Cluster fragmentation** — several boxes packed into a short span breaking the
   narrative. Collapse to the single strongest box; CUT or merge the rest.
6. **Marginal aid** — even an `intuition` box is CUT when the concept is not actually hard
   for the audience. Intuition boxes are for *genuinely hard or counterintuitive* ideas only.

## Keep-guards (protect from CUT; TRIM at most)

- `prereq` chapter-openers — **protected type, never CUT** (TRIM-eligible only).
- Explains genuinely **hard or counterintuitive** material in plain English.
- Warns of a **real, non-obvious** pitfall.
- Defines a key term used later (if the definition is standard/trivial, TRIM not KEEP).
- A `workedexample` that reveals a real subtlety or builds non-obvious intuition.
- A `projectconnection` with a **specific, non-redundant** concrete hook.
- States a **headline empirical result** (`keyresult`).

## Calibration

- Default is **earn-or-go**, not keep. When a box is borderline between TRIM and CUT and
  has no distinct kernel of value, prefer **CUT**.
- Expect a meaningful number of CUTs per chapter — especially among `projectconnection`
  ("why this matters") boxes and mechanical `workedexample`s, the author's named pain points.
- Do **not** cut into the bone: keep-guard boxes and `prereq` openers stay. The aim is a
  leaner guide, not a stripped one.

## Prose-fluff tests (flag → tightened rewrite or deletion)

**Never alter math, term definitions, citations, numbers, or factual/empirical claims.**
Preserve all meaning.

1. **Pseudo-intellectual / inflated wording** — fancy words where plain ones work; abstract
   throat-clearing ("in a deep sense, the fundamental nature of…").
2. **Filler & hedging** — "It is important to note that", "As we shall see", "in order to"
   (→ "to"), "the fact that", "It bears mentioning", "Needless to say".
3. **Restatement / repetition** — a sentence or paragraph repeating the prior one.
4. **Throat-clearing transitions & over-signposting** — excessive "Having established X,
   we now turn to Y, which as we will see is crucial…".

Each fluff finding proposes a **tightened rewrite** (preserving every fact) or a **deletion**.

## Out of scope (do not touch)

- Equations, derivations, tables, figures, TikZ.
- Citations (`\citep`, `\citet`) and the bibliography.
- The core content of term definitions (TRIM-eligible only).
- `prereq` chapter-openers (CUT-exempt).
- Anything whose removal/change would alter a factual or empirical claim.
