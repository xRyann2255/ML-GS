---
name: write-chapter
description: Multi-pass pipeline for writing LaTeX learning guide chapters. 4 passes: write → cross-reference → condense → naive-reader review.
---

# Write Chapter

Write a complete LaTeX chapter using a 4-pass quality pipeline.

## Input

The user specifies:
- **Topic**: what the chapter covers
- **Guide**: which guide it belongs to (`ml-finance`, `quant-trading`, or a new one)
- **Source papers** (optional): specific papers from `reference/` to draw on

## Pass 1 — Writer (main agent)

Write the full chapter `.tex` file following the guide's conventions:

1. Read the target guide's `preamble.tex` or `conventions.tex` to know available box types and macros
2. Read the guide's `main.tex` to understand structure and existing chapters
3. Write the chapter following CLAUDE.md guide-writing rules:
   - Opening paragraph: concrete question or problem, not abstract definition
   - Prerequisites box at the start
   - Worked examples for every hard concept (setup → computation → table → intuition callout)
   - `\underbrace{}` annotations on complex math
   - `booktabs` tables, `listings` for code
   - Define every term on first use (bold)
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
> Output specific edit suggestions: "Lines X-Y: cut/merge/tighten because [reason]"

## Consolidation (main agent)

After both Pass 2 and Pass 3 complete:
1. Apply citation suggestions from Pass 2 (add `\citep{}`/`\citet{}` commands, add entries to `references.bib` if needed)
2. Apply condensing edits from Pass 3 (cut redundancy, tighten prose)
3. Save the revised chapter

## Pass 4 — Naive reader (sequential sub-agent)

Dispatch a sub-agent with this prompt:

> Read the chapter at [path] assuming you have ZERO domain knowledge. You are a smart student encountering this material for the first time. Identify:
> - Confusing logical jumps (where did step X come from?)
> - Terms used without definition
> - Missing intuition (the math is there but WHY is unclear)
> - Steps that move too fast (needs an intermediate explanation)
> - Notation introduced without explanation
>
> For each issue, state the exact location and what's confusing. Be specific.

## Final (main agent)

1. Apply Pass 4 feedback — add clarifications, definitions, intuition where flagged
2. Final read-through for coherence
3. Commit the chapter file
4. Update memory (`project-status.md`) with chapter completion
