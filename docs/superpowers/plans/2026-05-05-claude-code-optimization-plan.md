# Claude Code Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up memory system, custom skills, and slim CLAUDE.md so Claude Code starts every session with full project context and can execute repeated workflows (chapter writing, research, status checks) via single commands.

**Architecture:** Files-only approach — no code, no dependencies. Memory uses Claude Code's built-in `~/.claude/projects/<project>/memory/` directory (3 markdown files with YAML frontmatter). Skills use `.claude/skills/*.md` (project-local, invoked via `/skill-name`). CLAUDE.md is trimmed to essentials; detailed context moves to memory.

**Tech Stack:** Markdown only. Claude Code memory system. Claude Code custom skills.

---

## File Structure

```
ML-GS/
├── .claude/
│   └── skills/
│       ├── write-chapter.md      # 4-pass chapter writing pipeline
│       ├── research.md           # 3-agent parallel research pipeline
│       └── status.md             # read-only project status surface
├── CLAUDE.md                     # slimmed to ~80-100 lines
└── docs/superpowers/
    ├── specs/
    │   └── 2026-05-05-claude-code-optimization-design.md  # (exists)
    └── plans/
        └── 2026-05-05-claude-code-optimization-plan.md    # this file

~/.claude/projects/C--Users-RyanPC-Documents-Projects-ML-GS/memory/
├── MEMORY.md                     # index file (pointers to memory files)
├── decisions.md                  # append-only decision log
├── project-status.md             # current phase, done, next
└── user.md                       # user profile and preferences
```

---

### Task 1: Delete stale Risk-as-Alpha files

**Files:**
- Delete: `docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md`
- Delete: `docs/superpowers/specs/2026-04-23-risk-as-alpha-learning-guide-design.md`
- Delete: `docs/superpowers/plans/2026-04-23-risk-as-alpha-plan.md`
- Delete: `docs/superpowers/plans/2026-04-23-risk-as-alpha-learning-guide-plan.md`

- [ ] **Step 1: Delete the four stale files**

```powershell
git rm "docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md"
git rm "docs/superpowers/specs/2026-04-23-risk-as-alpha-learning-guide-design.md"
git rm "docs/superpowers/plans/2026-04-23-risk-as-alpha-plan.md"
git rm "docs/superpowers/plans/2026-04-23-risk-as-alpha-learning-guide-plan.md"
```

- [ ] **Step 2: Commit**

```powershell
git commit -m "chore: remove stale Risk-as-Alpha spec and plan files"
```

---

### Task 2: Create memory index file (MEMORY.md)

**Files:**
- Create: `C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\MEMORY.md`

- [ ] **Step 1: Create MEMORY.md with initial index**

Write the following to `C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\MEMORY.md`:

```markdown
- [Decisions](decisions.md) — append-only log of project direction choices, scope narrowings, methodology decisions
- [Project Status](project-status.md) — current phase, recently completed items, next steps, open questions
- [User Profile](user.md) — work style, communication preferences, domain knowledge level
```

---

### Task 3: Create decisions.md memory file

**Files:**
- Create: `C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\decisions.md`

- [ ] **Step 1: Create decisions.md with frontmatter and seed content**

Write the following to `C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\decisions.md`:

```markdown
---
name: Project Decisions
description: Append-only log of ML vol project decisions — direction choices, scope narrowings, methodology selections
type: project
---

## Decision Log

2026-05-05: Pivoted from "Risk as Alpha" (broad ML finance) to ML for realized volatility forecasting — clearer scope, stronger literature, better fit for 10-12 week internship.

2026-05-05: Five candidate directions identified. Direction not yet finalized. Leading candidates: (1) HARQ-X + ML residual (safest, public data), (2) Intraday RV from LOB (medium, Optiver-style).

2026-05-05: Evaluation framework locked — QLIKE as primary loss, DM tests + MCS for model comparison, purged k-fold CV for hyperparameter selection. No random k-fold on time series.

2026-05-05: Success target defined — 30-80 bps QLIKE improvement over HAR family, on at least one regime/asset class, with economic-value test (vol-targeting Sharpe or VaR backtest).

2026-05-05: Presentation framing — honest "where ML helps and where HAR wins" decomposition. Rigour over R² claims.
```

---

### Task 4: Create project-status.md memory file

**Files:**
- Create: `C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\project-status.md`

- [ ] **Step 1: Create project-status.md with frontmatter and current state**

Write the following to `C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\project-status.md`:

```markdown
---
name: Project Status
description: Current phase of the ML vol internship project — what's done, what's next, blockers
type: project
---

## Current Phase
Phase 0: Scoping & Infrastructure (weeks 1-2, ending ~2026-05-12)

## Completed
- Literature survey complete (notes/volatility.md — 45 papers reviewed)
- Paper reading list curated (reference/project-papers/README.md — 32 papers, 20 essential)
- Repo restructured for Claude Code efficiency
- Memory system and custom skills designed and implemented
- Two learning guides in progress (ml-finance: 14 chapters, quant-trading: 38 chapters)

## Next Steps
1. Finalize project direction (choose from 5 candidates in CLAUDE.md)
2. Begin baseline implementation: HAR, HARQ, SHAR on Oxford-Man or VOLARE data
3. Write realized volatility chapter for ml-finance guide (RV estimators, noise, sampling)
4. Source data: check VOLARE availability, download Oxford-Man archive

## Open Questions
- Which project direction? Leaning Direction 1 (HARQ-X + ML residual) but not committed
- Data source: VOLARE (2025, open-access) vs Oxford-Man (discontinued 2022, archival)
- Whether to include GNN/cross-sectional component or defer to extension
```

---

### Task 5: Create user.md memory file

**Files:**
- Create: `C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\user.md`

- [ ] **Step 1: Create user.md with frontmatter and profile**

Write the following to `C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\user.md`:

```markdown
---
name: User Profile
description: Ryan's work style, communication preferences, and domain knowledge — informs how Claude collaborates
type: user
---

## Role
Goldman Sachs ML intern (started May 2026, ~10-12 weeks). Working on realized volatility forecasting project.

## Domain Knowledge
- Strong quantitative background (comfortable with stochastic calculus, econometrics, ML theory)
- Deep familiarity with ML methods (gradient boosting, neural networks, transformers)
- Learning financial econometrics (HAR models, realized measures, VRP) — knows the concepts but building depth

## Work Style
- Prefers rigour over hype — wants honest "where ML wins vs loses" decomposition
- Uses multi-pass chapter writing: write → cross-reference papers → condense → zero-knowledge review
- Wants concise responses, not verbose explanations
- Asks "what's next?" frequently — needs clear project status tracking
- Iterates fast — prefers Claude to do the heavy lifting and present results for approval

## Communication Preferences
- No fluff, no hedging
- Direct recommendations over lists of options (unless explicitly exploring)
- Quantitative framing (bps improvement, Sharpe ratios) over qualitative
```

---

### Task 6: Slim CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (full rewrite, ~80-100 lines keeping only essentials)

- [ ] **Step 1: Rewrite CLAUDE.md to slim version**

Replace the entire contents of `CLAUDE.md` with the following (~95 lines):

```markdown
# ML for Realized Volatility Forecasting — Internship Project

## Purpose
Scratchpad for planning and executing a Goldman Sachs ML internship project (~10-12 weeks, active May 2026) focused on forecasting realized volatility. Not a production codebase.

## Repository Structure
```
ML-GS/
├── CLAUDE.md                    # this file
├── .claude/skills/              # custom skills (write-chapter, research, status)
├── deliverables/                # project deliverables (pitch, plans, scripts)
├── docs/superpowers/            # design specs and implementation plans
├── notes/                       # project notes
│   └── volatility.md            # main research/scoping document (~45 papers)
├── reference/                   # all reference materials
│   ├── books/                   # textbooks (Hull, AFML, Natenberg, etc.)
│   ├── papers/                  # general reference papers + course materials
│   ├── project-papers/          # papers specific to the vol project (32 curated)
│   └── bibliography.md
└── guides/                      # LaTeX learning guides
    ├── ml-finance/              # ML for finance (14 chapters)
    └── quant-trading/           # quant trading (38 chapters)
```

## Project Directions (one to be finalized)
1. **HARQ-X + ML residual** (Safest) — public data, clearest "where ML adds value" story
2. **Intraday RV from LOB** (Medium) — Optiver-style, options MM relevance
3. **Multivariate RC with GNNs** (Medium-Ambitious) — covariance forecasting, portfolio backtest
4. **Rough vol vs deep learning** (Ambitious) — Rosenbaum-Zhang replication + extension
5. **VRP ML trader** (Highest Wow) — variance risk premium signal, end-to-end PnL

## Key Baselines
HAR, HAR-J/CJ, SHAR, HARQ, Realized GARCH, Ridge/Lasso-HAR

## Evaluation
QLIKE (primary), MSE, Diebold-Mariano tests, Model Confidence Set, purged k-fold CV. Target: 30-80 bps QLIKE improvement + economic-value test.

---

## Writing Learning Guides

New guides go in `guides/<guide-name>/`. Follow existing conventions from `guides/quant-trading/` and `guides/ml-finance/`.

### Setup
- **Class**: `memoir` `[11pt, openany, a4paper, oneside]` or `report` `[11pt, a4paper]`
- **Preamble**: Shared file (`preamble.tex`) loaded via `\input{}`. No packages in chapter files
- **Structure**: `main.tex` → `\input{chapters/chXX_name.tex}`, grouped into `\part{}`
- **Citations**: `natbib` `[round, authoryear]`, `references.bib` at guide root

### Required Box Types (tcolorbox)
| Box | Colour | Purpose |
|---|---|---|
| `intuition` | Green | Plain-English explanations, analogies |
| `keyidea` | Blue/Orange | Important concepts, algorithms |
| `warning` | Red | Common mistakes, methodological errors |
| `workedexample` | Teal | Step-by-step numerical walk-throughs |
| `projectconnection` | Teal | Ties content to the GS project |
| `prereq` | Purple | Background knowledge and prerequisites |

### Style Rules
- Open with a concrete question, not an abstract definition
- Every chapter starts with a prereq box
- Worked examples mandatory for hard concepts (setup → computation → table → intuition)
- `booktabs` tables only. No vertical rules
- Cite papers from `reference/` liberally (`\citep{}` parenthetical, `\citet{}` textual)
- Teach from first principles — define every term on first use (bold it)

---

## Conventions
- `docs/superpowers/specs/` for design documents
- `docs/superpowers/plans/` for implementation plans
- `notes/` for project notes
- `reference/project-papers/` for ML vol papers, `reference/papers/` for general
- All code follows TDD: failing test → implement → pass → commit
```

---

### Task 7: Create `.claude/skills/` directory and `write-chapter.md` skill

**Files:**
- Create: `.claude/skills/write-chapter.md`

- [ ] **Step 1: Create the .claude/skills/ directory**

```powershell
New-Item -ItemType Directory -Path ".claude/skills" -Force
```

- [ ] **Step 2: Create write-chapter.md**

Write the following to `.claude/skills/write-chapter.md`:

```markdown
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
```

---

### Task 8: Create `research.md` skill

**Files:**
- Create: `.claude/skills/research.md`

- [ ] **Step 1: Create research.md**

Write the following to `.claude/skills/research.md`:

```markdown
---
name: research
description: Parallel 3-agent research pipeline for the ML vol project. Searches internal notes, reference papers, and web simultaneously, then synthesizes findings.
---

# Research

Run a parallel research pipeline on a given topic, combining internal knowledge, paper references, and web sources.

## Input

The user specifies a research query, e.g.:
- "research QLIKE loss function properties"
- "research Oxford-Man vs VOLARE data availability"
- "research GNN approaches to covariance forecasting"

## Execution

Dispatch three sub-agents in parallel (single message, three Agent tool calls):

### Agent 1 — Internal Search

Prompt:

> Search the ML-GS repository for existing coverage of "[query]". Check:
> - `notes/volatility.md` — the main scoping document
> - `reference/project-papers/README.md` — the paper index
> - Any existing guide chapters in `guides/ml-finance/chapters/` and `guides/quant-trading/chapters/`
> - `notes/` for any other relevant files
>
> Report what we already know about this topic, with file paths and line numbers. Be specific — quote relevant passages. Under 300 words.

### Agent 2 — Paper Search

Prompt:

> Search PDF files in `reference/project-papers/` and `reference/papers/` for content related to "[query]". Read relevant papers and extract:
> - Key methodology details
> - Empirical results and findings
> - Contradictions between papers
> - Specific numbers, tables, or formulas relevant to the query
>
> Report findings with paper names and specific details. Under 400 words.

### Agent 3 — Web Search

Prompt:

> Search the web for recent information (post-2023) about "[query]" in the context of realized volatility forecasting and financial ML. Look for:
> - Recent papers (arXiv, SSRN)
> - Open-source implementations (GitHub repos)
> - Data sources and availability
> - Blog posts or tutorials from practitioners
>
> Focus on actionable information: things we could use, cite, or build on. Under 300 words.

## Synthesis (main agent, after all 3 complete)

Combine the three reports into a single structured brief:

```
## Topic: [query]

### What We Already Have
[Summary of Agent 1 findings — what's already in our repo]

### From Papers
[Summary of Agent 2 findings — key results from reference PDFs]

### From Web
[Summary of Agent 3 findings — recent developments, repos, data]

### Synthesis
[How findings connect. Contradictions. Confidence levels. What's settled vs uncertain.]

### Project Relevance
[How this affects our project direction, methodology, or implementation choices]

### Suggested Next Steps
[2-4 concrete actions based on findings]
```

Present the brief to the user. Do NOT automatically save it — let the user decide if it should go into notes.
```

---

### Task 9: Create `status.md` skill

**Files:**
- Create: `.claude/skills/status.md`

- [ ] **Step 1: Create status.md**

Write the following to `.claude/skills/status.md`:

```markdown
---
name: status
description: Surface current project status — reads memory files and recent git history to show phase, progress, next steps, and open decisions.
---

# Status

Show the current state of the ML vol internship project. This skill READS memory but never writes it.

## Execution

1. Read `memory/project-status.md` from the Claude Code memory directory
2. Read `memory/decisions.md` from the Claude Code memory directory
3. Run `git log --oneline -10` to see recent commits

## Output Format

Combine memory and git history into this structure:

```
## Current Phase
[Phase name and approximate timeline from project-status.md]

## Recently Completed
[Items from "Completed" section of project-status.md, cross-referenced with recent git commits]

## Next Steps (priority order)
1. [From "Next Steps" section of project-status.md]
2. [...]
3. [...]

## Open Decisions
[From "Open Questions" in project-status.md + any unresolved items in decisions.md]
```

## Important

- This skill is READ-ONLY. It surfaces information, it does not update memory.
- Memory updates happen naturally during work sessions (e.g., after completing a chapter, making a decision, finishing a task).
- If project-status.md looks stale relative to git history, mention this: "Note: status file may be outdated — last 3 commits suggest [X] has been completed since last update."
```

---

### Task 10: Commit all new files

- [ ] **Step 1: Stage and commit the skills and CLAUDE.md changes**

```powershell
git add ".claude/skills/write-chapter.md"
git add ".claude/skills/research.md"
git add ".claude/skills/status.md"
git add "CLAUDE.md"
git commit -m "feat: add custom skills (write-chapter, research, status) and slim CLAUDE.md"
```

- [ ] **Step 2: Verify skills directory exists and contains the three files**

```powershell
Get-ChildItem ".claude/skills/"
```

Expected output: three files — `write-chapter.md`, `research.md`, `status.md`

---

### Task 11: Verify end-to-end

- [ ] **Step 1: Confirm memory files exist**

```powershell
Get-ChildItem "C:\Users\RyanPC\.claude\projects\C--Users-RyanPC-Documents-Projects-ML-GS\memory\"
```

Expected: `MEMORY.md`, `decisions.md`, `project-status.md`, `user.md`

- [ ] **Step 2: Confirm stale files are gone**

```powershell
Test-Path "docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md"
Test-Path "docs/superpowers/plans/2026-04-23-risk-as-alpha-plan.md"
```

Expected: both return `False`

- [ ] **Step 3: Confirm CLAUDE.md is under 100 lines**

```powershell
(Get-Content "CLAUDE.md").Count
```

Expected: ~95 lines

- [ ] **Step 4: Check git status is clean**

```powershell
git status
```

Expected: working tree clean (except untracked `quant-learning-guide/` and `research/` from earlier)
