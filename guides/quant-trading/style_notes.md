# NLP Notes Style Reference Observations

Reference file: `example-notes/NLP_NOTES.pdf` by Ryan Vincent (Imperial COMP70016, 2025–26).

## What the style looks like

**Document class:** Book-style with chapter/section/subsection/subsubsection hierarchy. Works fine as either `book` or `memoir`; this project uses `memoir` because it's more flexible for later customisation.

**Font:** Computer Modern (standard LaTeX default with `amsmath`). No custom font packages needed.

**Title page:** Centred title ("Natural Language Processing Exam Revision Notes"), author, institution, year, short blurb, `\today` date. Clean and minimal.

**Running headers:** Small-caps chapter name on the left, document title on the right. Page number at bottom centre. `memoir`'s `headstyles` options provide this.

**Chapter headings:** Numbered, large serif, generous vertical whitespace before and after. Standard `\chapter` behaviour.

**Section hierarchy used:** `\chapter` → `\section` → `\subsection` → `\subsubsection`. Occasionally `\paragraph` for tiny inline headings like "**State N:**".

## Theorem/definition/example environments

**Not boxed `amsthm` style.** The NLP notes don't use traditional boxed theorem environments. Instead, the document leans heavily on **tcolorbox callout boxes** for highlighting (see next section). Definitions and formal facts that need emphasis go in a coloured box; ordinary results sit in body prose.

This matches what I want: rigour-level-B prose with occasional "here's the precise statement" callouts rather than a forest of numbered theorems.

## Callout boxes (this is the core visual feature)

The NLP notes use four recurring coloured callout boxes, each with a coloured header bar containing bold white title text, a coloured border, and a light tinted background. The mapping of colour → purpose is:

| Colour | Purpose in NLP notes | My mapping |
|---|---|---|
| Red | "Don't Confuse..." / warnings / common mistakes | `pitfallbox` ✓ |
| Green | "Interpreting the Result" / "The Trellis as a Grid" — intuition, grounding | `intuitionbox` (note: my current colour is blue, but colour choice is arbitrary; keep blue for consistency with the rest of the file) |
| Blue | "Viterbi Complexity" — formal fact / complexity result | No direct equivalent — use `amsthm` theorem/proposition instead |
| Orange | "Why Viterbi Is Essential: Speedup Example" — motivation / worked example highlights | `prosperitybox` ✓ (orange for Prosperity examples matches) |

The `tcolorbox` style in `conventions.tex` (`enhanced`, light coloured background, `title=` at top) produces visually similar boxes. Matches the reference closely enough.

## Worked example style

The NLP notes' biggest strength: **every hard concept has a full step-by-step worked numerical example with real numbers**. The Viterbi algorithm worked example in §5.7 is a masterclass:

- Concrete setup (3 states, 4 words, specific transition/emission matrices with real probabilities)
- Step-by-step subsections (§5.7.1 Initialisation, §5.7.2 Recursion t=2, §5.7.3 Recursion t=3, ...)
- Every calculation shown as a numbered equation
- Underbraces (`\underbrace{...}_{\text{meaning}}`) annotate what each factor represents
- Bold italic **winner** arrows ("← winner") on the maximising term
- Final summary table with highlighted winning cells
- Closing "Interpreting the Result" intuition box

**Apply to this project:** Every hard chapter (Ch 5, 8, 15, 22, 29) should follow this pattern — concrete numerical setup → step-by-step computation → summary table → intuition callout.

## Pseudocode style

Algorithms appear in a horizontal-rule-framed block with a header label ("Viterbi Algorithm"), indented pseudocode, and `Input:`/`Output:`/`Initialisation:`/`Recursion:`/etc. sub-labels. This is probably `\begin{algorithm}` with a custom style, or a manual `tabular` environment.

For this project: use the standard `algorithm`/`algorithmic` packages or a simple bordered minipage. Not critical for infrastructure; can refine when the first chapter needing pseudocode is written.

## Math conventions

- **Underbraces** heavily used to label equation terms with their interpretation.
- Equations numbered within chapter (`(5.14)`, `(5.15)`, ...).
- **Aligned multi-line equations** for derivations.
- **Inline math** kept short; display math used liberally.

## Tables

Clean `booktabs` style: `\toprule`, `\midrule`, `\bottomrule`. No vertical rules. Small amount of whitespace between columns.

## Code listings

Not prominent in the NLP notes (it's a maths-heavy subject). This project will use more code listings than the NLP reference does — the `listings` package with the `pythonstyle` defined in `conventions.tex` is the right call.

## Decisions locked in for this project

1. **Document class:** `memoir` (more flexible than `book`, used in the plan). `openany` for continuous chapter starts (no blank pages between chapters).
2. **Theorem style:** Use `amsthm` for formal statements (theorem, proposition, lemma, definition, example, remark). Shared numbering within chapter via `\newtheorem{...}[theorem]{...}`.
3. **Callout boxes:** Five tcolorbox styles (intuitionbox, prosperitybox, gsbox, pitfallbox, historybox) — match the NLP style visually.
4. **Worked examples:** Use `\begin{example}...\end{example}` from amsthm for theorem-style examples, and step-by-step subsections for long worked examples (the Viterbi pattern).
5. **Fonts:** Computer Modern default. Add `lmodern` for better PDF font rendering.
6. **Equations:** `amsmath` `align`/`equation` with chapter-based numbering. Use `\underbrace{...}_{\text{...}}` liberally for annotated math.
7. **Tables:** `booktabs` only.
8. **Code:** `listings` with `pythonstyle` from `conventions.tex`.

No changes needed to the planned `conventions.tex` from Task 3 — the style matches well enough.
