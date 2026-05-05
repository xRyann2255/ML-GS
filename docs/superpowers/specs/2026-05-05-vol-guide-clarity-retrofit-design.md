# Vol Learning Guide Clarity Retrofit

**Date**: 2026-05-05
**Status**: Approved

## Problem

The vol learning guide has 134 equations across 17 chapters. Currently, equations follow the pattern: equation, symbol definitions, then sometimes an intuition box. Two critical layers are missing:

1. **Conceptual translations**: what the equation DOES as a whole unit, in plain English
2. **Project relevance**: why this matters for vol forecasting specifically

The reader understands individual symbols (the bullet-list definitions work) but cannot grasp what equations mean conceptually or why they should care for the vol forecasting project. Worked numerical examples consume space without serving theory comprehension. Key concepts lack geometric visualizations that would unlock understanding.

### Specific Pain Points

- Equations are presented without explaining what we're trying to capture BEFORE the math
- No plain English "this equation says..." translation after the math
- No explicit link from theory back to vol forecasting relevance
- Worked examples focus on computation practice rather than theory comprehension
- Important concepts that are inherently visual (convergence, price paths, accumulation) lack diagrams

## Solution: The Clarity Retrofit

### Mandatory Equation Pattern

Every logically distinct equation (i.e., each `\label{eq:...}`) must follow this structure. Multi-line derivations (`align` environments) need one intuition + projectconnection block for the final result, not for each intermediate step. Trivial definitional equations (e.g., `\sigma^2 = \text{Var}(r)`) may share a combined box with adjacent equations.

Existing `keyidea` boxes that already serve the plain English role may remain in place; the mandatory `intuition[In Plain English]` box is required only when no equivalent explanation currently exists, or when the existing box focuses on something other than the equation's conceptual meaning.

```latex
% 1-2 setup sentences: what we're trying to capture
We need a way to express how [concept]. The following equation formalizes this:

\begin{equation}
  ... formula ...
  \label{eq:name}
\end{equation}
\begin{itemize}[nosep]
  \item $X$: what X represents
  \item $Y$: what Y represents
\end{itemize}

\begin{intuition}[In Plain English]
  2-3 sentences explaining what this equation MEANS as a whole unit.
  Not what the parts are, but what the equation is DOING conceptually.
\end{intuition}

\begin{projectconnection}[Why This Matters]
  1-2 sentences: how this connects to vol forecasting.
  What it feeds into, what depends on it, or what would break without it.
\end{projectconnection}

% (selectively) TikZ diagram for key concepts
```

### Diagram Policy

Add geometric/graphical TikZ illustrations when:
- An equation describes a geometric or dynamic relationship (price paths, convergence, accumulation)
- A concept involves a process or flow easier to SEE than read
- The relationship between quantities is spatial or temporal

Do NOT add diagrams for every equation. Target approximately 3-5 diagrams per chapter on average; individual chapters may have fewer or more based on content.

### Worked Example Policy

- **Keep**: worked examples that serve theory comprehension (e.g., showing that realized variance computed at 1-second vs. 5-minute sampling gives wildly different answers, demonstrating microstructure noise impact)
- **Remove**: worked examples that exist purely for computation practice (e.g., stepping through summing 10 squared returns to get a variance number -- pure arithmetic drill)

### Tone and Verbosity

- Write as if explaining to a smart person building intuition from scratch
- Err on the side of over-explaining concepts
- Before introducing complexity, ensure the simpler version is fully internalized
- Every term bold on first use with a verbose definition

## Scope and Ordering

All 17 chapters get retrofitted, processed in reading order:

| Priority | Chapters | Rationale |
|----------|----------|-----------|
| P0 | Ch 1-4 (Part 1: Foundations) | Reader is here now and struggling |
| P1 | Ch 5-7 (Part 2: Classical Models) | Next in reading order, HAR/GARCH are core to project |
| P2 | Ch 8-9 (Part 3: Vol Surface) | Options/VRP material |
| P3 | Ch 10-13 (Part 4: ML Methods) | Core ML content for the project |
| P4 | Ch 14-17 (Parts 5-6: Multivariate + Eval) | Later material |

### Per-Chapter Process

1. Read the chapter, identify every equation
2. Add setup sentences before equations that lack them
3. Add `\begin{intuition}[In Plain English]` boxes after every equation
4. Add `\begin{projectconnection}[Why This Matters]` boxes after every equation
5. Evaluate each worked example: serves theory? Keep. Pure computation? Remove.
6. Identify 3-5 key concepts that need geometric diagrams, add TikZ illustrations
7. Run updated naive reader pass to verify quality

## Quality Gate

Every retrofitted chapter passes through the write-chapter skill's Pass 4 (Naive Reader) before being considered done. The naive reader:

- Flags any equation missing a plain English translation as CRITICAL
- Flags any equation missing a project connection as CRITICAL
- Flags every moment of confusion, no matter how small
- Suggests where diagrams are needed but missing

The naive reader deliberately over-flags; the implementer uses judgment about which flags to address vs. defer based on the actual reader's quantitative background (strong in math/stats, building finance domain intuition).

A chapter is "done" when the naive reader finds zero CRITICAL issues and remaining flags are addressed or consciously deferred.

## Write-Chapter Skill Update

The `write-chapter` skill has been updated to encode these requirements so all future chapters are written in this style from the start. Changes:

- Added "Learning Style Requirements" section to Pass 1 (Writer)
- Updated Pass 3 (Condenser) to not flag plain English boxes as redundant
- Rewrote Pass 4 (Naive Reader) to be much more aggressive about flagging confusion
- Updated Final pass to verify every equation follows the mandatory pattern

## Success Criteria

- Every equation in the guide has a setup sentence, plain English translation, and project connection
- Key concepts have geometric TikZ diagrams (3-5 per chapter)
- Worked examples that don't serve theory have been removed
- Pass 4 (Naive Reader) finds zero CRITICAL issues per chapter
- Reader can explain what any equation means in their own words after reading the surrounding context
