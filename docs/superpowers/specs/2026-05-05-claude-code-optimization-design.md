# Claude Code Optimization for ML-GS

**Date:** 2026-05-05
**Approach:** Full Agent Pipeline (Approach C)

---

## 1. CLAUDE.md Overhaul

Slim CLAUDE.md from ~280 lines to ~80-100 lines. Keep only what's needed every turn:

**Keep:**
- Project summary (internship scope, core goal, success target, presentation framing)
- Repo structure tree
- 5 candidate directions (one-liner each, not full paragraphs)
- Key baselines list (bullet names only)
- Guide-writing instructions (condensed — document setup, required box types table, style bullets)
- Conventions section

**Move to memory files:**
- Full ML methods discussion (ranked list with evidence notes)
- Feature engineering catalogue
- "What Doesn't Work" list
- Detailed paper context and evaluation methodology notes
- "The honest bottom line" paragraph (becomes part of project-status memory)

**Delete stale files:**
- `docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md`
- `docs/superpowers/specs/2026-04-23-risk-as-alpha-learning-guide-design.md`
- `docs/superpowers/plans/2026-04-23-risk-as-alpha-plan.md`
- `docs/superpowers/plans/2026-04-23-risk-as-alpha-learning-guide-plan.md`

---

## 2. Memory System

Three files in Claude Code's built-in memory directory (`~/.claude/projects/<project>/memory/`):

### `decisions.md`
- **Type:** project
- **Format:** Append-only log of project decisions with dates
- **Content:** Direction choices, tool selections, scope narrowings, methodology decisions
- **Example entry:** `2026-05-05: Narrowed to Direction 1 (HARQ-X + ML residual) — safest path, public data, clearest "where ML helps" decomposition`

### `project-status.md`
- **Type:** project
- **Format:** Overwritten each session (not append-only)
- **Content:** Current phase, what's done, what's next, blockers
- **Sections:** Phase, Completed, Next Steps, Open Questions

### `user.md`
- **Type:** user
- **Format:** Updated as preferences emerge
- **Content:** Work style preferences, communication preferences, domain knowledge level
- **Initial content:** GS ML intern, strong quantitative background, prefers rigour over hype, wants honest "where ML wins vs loses" framing, uses multi-pass chapter writing workflow

---

## 3. `write-chapter` Skill

**Location:** `.claude/skills/write-chapter.md`
**Trigger:** `/write-chapter` or "write chapter X about Y"

### Pipeline (4 passes)

**Pass 1 — Writer (sequential, main agent):**
- Reads chapter topic, target guide, and any source papers
- Writes full chapter following guide conventions (preamble boxes, worked examples, prereq box, motivating opening)
- Outputs complete `.tex` file

**Pass 2 — Cross-referencer (parallel agent):**
- Reads the draft chapter
- Searches `reference/project-papers/` and `reference/papers/` for relevant citations
- Identifies claims that need citations, concepts that could reference specific papers
- Outputs: list of suggested citations with locations, any factual corrections from papers

**Pass 3 — Condenser (parallel agent, runs simultaneously with Pass 2):**
- Reads the draft chapter
- Identifies: redundant explanations, overly verbose passages, filler text, repeated ideas
- Outputs: specific edit suggestions (cut X, merge Y and Z, tighten paragraph at line N)

**Consolidation (main agent):**
- Applies Pass 2 citations and Pass 3 cuts to produce revised draft

**Pass 4 — Naive reader (sequential agent):**
- Reads revised draft assuming zero domain knowledge
- Identifies: confusing jumps, undefined terms, missing intuition, steps that feel too fast
- Outputs: list of specific locations needing clarification

**Final (main agent):**
- Applies Pass 4 feedback
- Commits final chapter file
- Updates memory with chapter completion status

---

## 4. `research` Skill

**Location:** `.claude/skills/research.md`
**Trigger:** `/research` or "research X for the project"

### Pipeline (3 parallel agents + synthesizer)

**Agent 1 — Internal search:**
- Searches `notes/volatility.md`, `reference/project-papers/README.md`, existing guide chapters
- Finds: what we already know, what's already written, relevant sections

**Agent 2 — Paper search:**
- Searches PDFs in `reference/project-papers/` and `reference/papers/`
- Looks for: methodology details, results, relevant findings, contradictions

**Agent 3 — Web search:**
- Searches for recent papers, blog posts, implementations, datasets
- Focuses on: post-2023 developments, code repos, data availability

**Synthesizer (main agent, after all 3 complete):**
- Combines findings into structured brief:

```
## Topic: [query]

### What We Already Have
- [existing coverage in notes/guides]

### From Papers
- [key findings from reference PDFs]

### From Web
- [recent developments, repos, data sources]

### Synthesis
- [how findings connect, contradictions, confidence levels]

### Project Relevance
- [how this affects our direction/methodology choices]

### Suggested Next Steps
- [concrete actions based on findings]
```

---

## 5. `status` Skill

**Location:** `.claude/skills/status.md`
**Trigger:** `/status` or "where am I / what's next"

### Behaviour

1. Reads `memory/project-status.md` for current phase and progress
2. Reads `memory/decisions.md` for recent decisions constraining next steps
3. Checks `git log --oneline -10` for recent commits (what actually shipped)
4. Returns structured brief:

```
## Current Phase
[phase name and timeline]

## Recently Completed
- [items from memory + recent git history]

## Next Steps (priority order)
1. [highest priority]
2. [next]
3. [next]

## Open Decisions
- [unresolved choices from decisions.md]
```

**Key constraint:** This skill reads memory but never writes it. Memory updates happen naturally during work sessions.

---

## 6. Cleanup & Configuration

### Stale files to delete
- `docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md`
- `docs/superpowers/specs/2026-04-23-risk-as-alpha-learning-guide-design.md`
- `docs/superpowers/plans/2026-04-23-risk-as-alpha-plan.md`
- `docs/superpowers/plans/2026-04-23-risk-as-alpha-learning-guide-plan.md`

### `.claude/settings.json`
Not needed at this stage. Current setup works without custom permissions or hooks. Can add later if a repeated friction point emerges.

---

## Implementation Order

1. Delete stale files, commit
2. Create memory directory and seed 3 memory files
3. Slim CLAUDE.md (move content to memory)
4. Create `.claude/skills/write-chapter.md`
5. Create `.claude/skills/research.md`
6. Create `.claude/skills/status.md`
7. Commit all, verify skills load correctly
