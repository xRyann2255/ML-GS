# Workflow: Execute

Implements ML pipeline tasks — feature engineering, model training, and evaluation.

---

## Entry Conditions

Enter when:
- User explicitly uses `/execute`.
- `plan.md` yields here after producing a plan.
- Trivial task routed directly (single-file, <20 lines, clear intent).

---

## State Machine

```
DECOMPOSE → IMPLEMENT → VERIFY → DONE
              ↑ (inline mode: skip DECOMPOSE)
```

### DECOMPOSE

**Purpose:** Decide whether to orchestrate via subagents or execute inline.
**Memory:** Reload plan context from `plan.md` (includes execution mode tags).

**Actions:**
1. Check if the plan has `subagent`-tagged steps (from `/plan` DESIGN phase).
2. If yes → enter **orchestration mode**: spawn one subagent per `subagent`-tagged step.
3. If no (all steps are `inline`) → skip to IMPLEMENT directly.

**Orchestration mode:**
- For each `subagent`-tagged step, spawn via `runSubagent` with the context packet from the plan.
- All subagents MUST use Claude Opus 4.6 (see `policy/subagent_protocol.md`).
- **Use `depends_on` to determine spawn order:**
  - Steps with `depends_on: []` → spawn immediately, in parallel with other independent steps.
  - Steps with dependencies → wait until all listed steps complete, then spawn.
  - Example: if steps 1,2,3 have no deps and step 4 depends on [1,2,3], spawn 1-3 in parallel, wait for all, then spawn 4.
- Max 6 concurrent subagents.
- Collect return reports from each subagent.
- If a subagent returns `blocked` or `partial`: retry ONCE with refined context, then escalate.

| Condition | Transition |
|-----------|------------|
| All subagent-tagged steps complete | → VERIFY (skip IMPLEMENT) |
| Plan has no subagent tags | → IMPLEMENT |
| Subagent failure after retry | → DONE (report blocked with evidence) |

### IMPLEMENT

**Persona:** MODEL-BUILDER
**Memory:** If entering from `plan.md`, reload the plan context. Load relevant memory per `INDEX.md` lookup tables matching the task domain. For ML tasks, load relevant feature layer cards from `memory/research/`.

**When entered:** Only for `inline`-tagged steps, OR when DECOMPOSE is skipped (trivial tasks, no plan).

**Actions:**
1. **TEST-FIRST gate** — for each code change:
   a. Write a failing test that defines expected behavior.
   b. Confirm it fails (red).
   c. Skip for non-code files (config, docs, memory).
2. Per todo item: implement to make the test pass (green) → lint → checkpoint.
3. **CONFORM** — for each changed code file, audit against domain-specific conventions. Fix violations. Skip for non-code files.
4. Mark todos complete as each finishes.

**Scope Drift Detection:**
- 1-2 new files beyond scope: note, continue.
- 3+ new files or new dependency: pause, report drift, ask user.
- Remaining work >2x estimate: stop and re-scope with user.

| Condition | Transition |
|-----------|------------|
| All implementation steps complete | → VERIFY |
| Scope drift detected (3+ files) | → DONE (report blocked with drift diagnosis) |
| Error after 3 approaches | → DONE (report blocked) |
| Scope unclear mid-execution | → Yield to `plan.md`, resume on return |

### VERIFY

**Actions:**
1. Run tests on modified files. Capture output to file when parsing needed.
2. Run lint/typecheck/build when applicable.
3. Scan for debug leftovers.

| Condition | Transition |
|-----------|-----------|
| All checks pass | → DONE |
| Failures found, attempt ≤3 | → IMPLEMENT (targeted fix) |
| Failures found, attempt >3 | → DONE (report blocked with diagnosis) |

### DONE

1. List files changed with line ranges and verification evidence.
2. Update weekly progress log if work was shipped.
3. Present numbered next-steps.

---

## Constraints

- TEST-FIRST: every code change needs a failing test first.
- CONFORM: re-read changed files and verify domain conventions before VERIFY.
- Small diffs, no new deps without permission.
- Max 1 yield to `plan.md`. No circular yields.
- If task decomposes into 3+ independent streams → escalate to `team.md`.
- **Subagent model pinning:** all spawned subagents MUST use Claude Opus 4.6 (see `policy/subagent_protocol.md`).
- **Subagent depth = 1:** subagents spawned from /execute do NOT spawn further subagents.
- **Context isolation:** see `policy/context-isolation.md` for spawn thresholds and packet schema.
