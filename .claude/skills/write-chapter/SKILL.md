---
name: write-chapter
description: Multi-pass pipeline for writing LaTeX learning guide chapters. 4 passes: write → cross-reference → condense → naive-reader review. Tuned for intuition-first learning.
---

# Write Chapter

Write a complete LaTeX chapter using a 4-pass quality pipeline.

## Input

The user specifies:
- **Topic**: what the chapter covers
- **Guide**: which guide it belongs to (`ml-finance`, `quant-trading`, or a new one)
- **Source papers** (optional): specific papers from `reference/` to draw on

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

**After writing any TikZ diagram, invoke the `verify-diagram` skill to visually inspect the rendered output.** The skill compiles the LaTeX, renders the diagram page to a PNG, and checks for arrows going through boxes, overlapping paths, broken routing, and dependency accuracy. Fix any issues found and re-verify until the diagram is clean. Never submit a chapter with an unverified diagram.

### Worked Examples

Only include worked numerical examples when they serve theory comprehension (e.g., showing WHY a formula produces a surprising result, or building intuition about magnitudes). Do NOT include computation-practice examples.

### Tone

- Write as if explaining to a smart person building intuition from scratch
- Every term defined on first use (bold)
- Verbose definitions are good — err on the side of over-explaining concepts
- Before introducing complexity, make sure the simpler version is fully internalized

## Pass 1 — Writer (main agent)

Write the full chapter `.tex` file following the guide's conventions:

1. Read the target guide's `preamble.tex` or `conventions.tex` to know available box types and macros
2. Read the guide's `main.tex` to understand structure and existing chapters
3. Write the chapter following CLAUDE.md guide-writing rules AND the Learning Style Requirements above:
   - Opening paragraph: concrete question or problem, not abstract definition
   - Prerequisites box at the start
   - Every equation follows the mandatory pattern (setup → equation → symbols → plain English → project connection)
   - `\underbrace{}` annotations on complex math
   - `booktabs` tables, `listings` for code
   - Define every term on first use (bold)
   - Geometric diagrams for key concepts
4. Save as `guides/<guide>/chapters/<filename>.tex`

## Pass 2 — Cross-referencer (parallel sub-agent)

Dispatch a sub-agent with this prompt:

> Read the draft chapter at [path]. Search `reference/project-papers/` and `reference/papers/` for papers relevant to claims, methods, or concepts in the chapter. For each paper found:
> - Identify which passage in the chapter it supports
> - Suggest the citation command (`\citep{}` or `\citet{}`)
> - Flag any factual errors the paper contradicts
>
> Output a numbered list of suggested citations with line locations.

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
