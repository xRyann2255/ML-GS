# Workflow: Plan

Implements [_protocol.md](_protocol.md). Scopes and designs a task — produces a plan, not code. For ML vol forecasting, this covers research planning, experiment design, and paper review sessions.

---

## Entry Conditions

Enter when:
- User explicitly uses `/plan`.
- Default routing: all single-thread tasks enter here at SCOPE (step 5 fallback).
- Another workflow yields here for scope resolution (e.g., from `execute.md` when scope is unclear).

**Common ML planning scenarios:**
- Exploration session design (one topic deep per session)
- Experiment design (hypothesis, data subset, method, success criterion, evaluation metric)
- Paper review sessions (identify relevant papers, extract applicable techniques)
- Feature layer implementation planning (which features, which data sources, validation approach)

Yield-in inputs carry the yielding workflow's context. SCOPE evaluates them identically to direct invocations. ROUTE handles the return-to-yielder transition.

---

## State Machine

```
SCOPE → DESIGN → ROUTE → DONE
```

### SCOPE

**Persona:** — (lightweight assessment)
**Memory:** Load task-relevant files per `INDEX.md` P0 + P1 matching task type.

**Actions:**
1. Assess task scope — what files, what changes, what acceptance criteria.
2. If acceptance criteria not provided, draft them.
3. If scope is ambiguous, run a **clarification round** using the 5-category framework:

| Category | Purpose | Example |
|----------|---------|---------|
| **Scope** | What's in/out | "Does this include X or just Y?" |
| **Priority** | What matters most | "Speed or correctness first?" |
| **Constraint** | Hard limits | "Any files we can't touch?" |
| **Tradeoff** | Acceptable compromises | "Partial now vs. full later?" |
| **Acceptance** | Done criteria | "What does success look like?" |

Rules: max 5 questions per round, summarize understanding back, max 3 rounds.

| Condition | Transition |
|-----------|-----------|
| Trivial task (single-file, <20 lines, clear intent) | → ROUTE (skip DESIGN) |
| Scope unclear after assessment | → Run clarification round, then re-assess |
| Scope clear, non-trivial | → DESIGN |

Checkpoint: record scope assessment and AC.

### DESIGN

**Constraints:** Plan to workspace/plans/. Right-size steps. Interview for preferences, inspect for facts. No code writes.
**Memory:** Load task-relevant memory per `INDEX.md` lookup tables. For ML experiments, load relevant feature layer cards and evaluation framework from `memory/research/`. Also load `workspace/docs/vol-project-ref/INDEX.md` for milestone acceptance criteria and authoritative specs when planning implementation work. Load `workspace/docs/vol-learning-guide/INDEX.md` for comprehensive equations and derivations when the plan involves implementing mathematical formulas or verifying existing implementations.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| Decomposes into 3+ independent streams | → Escalate to `team.md` |
| Plan produced | → ROUTE |

**Actions:**
1. Produce a file-level implementation plan.
2. If the plan involves an architectural decision, create or reference an ADR in `workspace/docs/decisions/`.
3. Create task-tracking items for multi-step work.
4. **DECOMPOSE for subagents** — for each step in the plan, tag execution mode:
   - `inline` — trivial task, orchestrator executes directly (single file, <50 lines)
   - `subagent` — task reads 3+ files, touches 2+ modules, or would accumulate >200 lines of context
   - For each `subagent`-tagged step, write a context packet (see `policy/context-isolation.md`) inline in the plan:
     ```yaml
     subtask_id: "execute-N"
     goal: "<one sentence>"
     file_scope: [<files to read>]
     write_scope: [<files to modify>]
     acceptance_criteria: [<testable assertions>]
     memory_refs: [<memory files if needed>]
     constraints: [<hard limits>]
     context_summary: "<2-5 sentence background>"
     depends_on: []  # list of subtask_ids that must complete first
     ```
   - If ALL steps are `inline`, skip context packets (small task, no decomposition needed)
5. **Dependency graph** — for each step, declare `depends_on` (list of step IDs that must finish before this step can start). Steps with no dependencies (or whose dependencies are all satisfied) can be spawned in parallel. The execute phase uses this to determine parallel vs sequential spawning:
   - `depends_on: []` → can run immediately / in parallel with other independent steps
   - `depends_on: ["execute-1", "execute-2"]` → waits for both to complete before spawning
   - Visualize as a brief summary: "Steps 1,2,3 parallel → Step 4 (needs 1-3) → Step 5 (needs 4)"
6. Checkpoint: record plan with execution mode tags and dependency graph.

**Scope Drift Detection** (checked at each step):
- 1–2 new files beyond original scope: note in progress update, continue.
- 3+ new files OR any new external dependency: pause, report drift, ask user.
- Remaining work >2× original estimate: stop and re-scope with user.

### ROUTE

**Persona:** —
**Memory:** No additional loads.
> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.
| Condition | Transition |
|-----------|----------|
| Yield-in from another workflow (scope resolution) | → Return plan to yielding workflow, resume caller |
| Invoked via `/plan` (planning-only mode) | → Deliver plan artifact, DONE |
| Default routing (plan + execute) | → Yield to `execute.md` with plan as context |

**Actions:**
1. If planning-only: produce plan artifact with scope, AC, decomposition, and recommended persona.
2. If default flow: pass plan + AC to `execute.md` as input context.
3. **Update weekly progress log** (`workspace/research/weekly-progress.md`): if a significant decision or architectural plan was produced, append a bullet under the current week's Decided section.

→ DONE (planning complete; execution continues in `execute.md` if routed).

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| SCOPE | Any (lightweight) |
| DESIGN | (inline constraints), VOL-RESEARCHER (gap analysis) |
| ROUTE | Any |

---

## Error Handling

Per `_protocol.md` error hooks (4-class model).
- Unclear scope after interview: surface ambiguity, force a decision.
- Design phase deadlock: after 3 distinct approaches, escalate to user with options.

---

## Common Sequences

Document the standard workflow chains that this plan feeds into:

| Sequence | Flow | When |
|----------|------|------|
| Default | plan → execute | Standard task: scope, plan, implement, verify |
| Research-first | investigate → plan → execute | Unknown domain: research before committing to a design |
| Bug lifecycle | debug → fix → review | Bug found: diagnose, fix, validate quality |
| ML experiment | research → plan → execute → review | New feature or model: explore data, plan, implement, review |
| Refactor | plan → refactor → review | Structural change: plan scope, lock tests, restructure, validate |

These sequences are not enforced by the system. They document the *intended* flow so operators know which workflow to invoke next.

---

## Constraints

- This workflow produces plans and artifacts — never file edits to workspace code.
- Max 1 workflow yield (to `interview.md` for scope resolution).
- Max composition depth: `plan → execute → plan` is not allowed. If `execute.md` needs re-scoping, it must escalate to the user.
- Plans for multi-step work must use the task-tracking tool for visibility.
