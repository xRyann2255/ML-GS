# Workflow: Team

Implements [_protocol.md](_protocol.md). Parallel subagent coordination for tasks with 3+ independent streams.

---

## Entry Conditions

Enter team when ANY hold:
1. Task has 3+ independent parallel work streams.
2. Task requires distinct specializations that cannot be time-shared by one agent.

---

## State Machine

```
DECOMPOSE → VALIDATE → ASSIGN → EXECUTE → INTEGRATE → VERIFY → REPORT → DONE
                                    ↑                     |
                                    └─────── FIX ←────────┘ (max 3 loops)

                         ABORT ← EXECUTE (critical failure / requirements change)
```

### DECOMPOSE

**Constraints:** Conservative fanout. Own final verification. Never delegate verification.
**Memory:** Load task-relevant files per `INDEX.md`.

**Actions:**
1. Decompose task into bounded subtasks with clear ownership.
2. For each subtask: scope boundary (files, modules), acceptance criteria, write-scope limits.
3. Checkpoint: record decomposition.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| Decomposition produced | → VALIDATE |
| Cannot decompose (task is sequential) | → Yield to `execute.md` |

### VALIDATE

**Constraints:** Conservative fanout. Own final verification.
**Memory:** No additional loads.

Validation gate — ALL four checks must pass:

| Check | Pass condition | Fail action |
|-------|---------------|-------------|
| **Collectively exhaustive** | Every part of original scope covered | Re-decompose |
| **Mutually exclusive** | No overlapping file/module ownership | Re-assign or split |
| **Concurrency fit** | Subtask count ≤ 6 | Batch or serialize excess |
| **Scope unchanged** | No AC added/removed/altered | Pause, present delta to user |
> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.
| Condition | Transition |
|-----------|-----------|
| All 4 pass | → ASSIGN |
| Any fail | → DECOMPOSE |

### ASSIGN

**Constraints:** Conservative fanout. Never delegate verification.
**Memory:** No additional loads.

**Actions:**
1. Assign each subtask to a worker with a context packet containing: subtask ID, file/module scope, acceptance criteria, write scope, relevant memory references, and subtask-specific constraints.
2. Persist workflow state.
3. Checkpoint: record assignments.

→ EXECUTE.

### EXECUTE

**Constraints (workers):** Stay in lane. Report blockers after 1 round. No scope creep.
**Memory:** Per worker context packet.

**Actions:**
1. Workers execute in parallel (max 6 concurrent per subagent protocol).
2. Workers report completion + evidence to leader.

**Inter-worker rules:**
- Workers are isolated — no direct worker-to-worker communication.
- Worker needs output from another → report dependency to leader.
- Worker discovers shared state outside scope → stop, report to leader.
- Worker needs cross-scope decision → escalate to leader.
- Workers MUST NOT share terminal sessions. Use `vol exec` or redirect output to uniquely-named files (include `$$` or `$(date +%s)` in path). See AGENTS.md "Terminal Isolation" section.
> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.
| Condition | Transition |
|-----------|-----------|
| All workers report complete | → INTEGRATE |
| Worker blocked or exceeds scope | → ABORT |
| No worker progress for 2 iterations | → ABORT |

### INTEGRATE

**Constraints:** Own final verification. Resolve conflicts deterministically.
**Memory:** No additional loads.

**Actions:**
1. Collect worker results.
2. Resolve conflicts (shared-file conflicts → serialize edits).
3. Merge into integrated state.
4. **Kill worker terminals.** Run `workbench.action.terminal.killAll` (or targeted kills if terminal IDs were tracked) to prevent orphaned terminals from accumulating across sessions.
5. Clean up `workspace/tmp/exec/` output files created by workers.
6. Checkpoint: record integration result.

→ VERIFY.

### VERIFY

**Persona:** — (verification mode)
**Memory:** No additional loads.

**Actions:**
1. Independent check against overall acceptance criteria.
2. Run tests, lint, typecheck on integrated result.
3. Checkpoint: record verification evidence.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| All AC met with evidence | → REPORT → DONE |
| Failures found, fix loop ≤3 | → FIX |
| Failures found, fix loop >3 | → REPORT (failed, with diagnosis) |

### FIX

**Constraints:** Targeted fixes only. Conservative fanout.
**Memory:** No additional loads.

**Actions:**
1. Leader assigns fix subtasks to original workers.
2. Workers apply targeted fixes.
3. Workers report evidence.

→ EXECUTE (for re-integration and re-verification).

### ABORT

**Constraints:** Conservative. Revert unsafe partial state.
**Memory:** No additional loads.

**Trigger:** Requirements change mid-execution, or critical failure invalidates decomposition.

**Sequence:**
1. Leader signals all workers to pause — finish atomic operation, start nothing new.
2. Leader collects worker status: `complete`, `partial`, or `not-started`.
3. Classify each partial result:
   - **Safe to keep** — independently correct, unaffected → preserve.
   - **Unsafe** — depends on invalidated assumptions → discard and revert.
4. Produce impact summary.
5. Re-entry decision:

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| Recoverable scope change, partial work valid | → DECOMPOSE (re-plan with preserved results) |
| Task provably sequential, coordination overhead unjustified | → Yield to `execute.md` (downscope) |
| Unrecoverable failure or repeated abort | → Exit with diagnosis (escalate to user) |

**Revert rule:** Partial output being discarded must be explicitly reverted. No half-applied state.

### REPORT

**Constraints:** Factual summary. List all subtask outcomes.
**Memory:** No additional loads.

**Actions:**
1. Summary: decomposition, execution outcomes, verification evidence.
2. List subtasks with final status.
3. Note any fixes applied and items that remain blocked.
4. Present numbered next-steps.
5. Exit per `_protocol.md` exit contract.

→ DONE.

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| DECOMPOSE | (inline constraints) |
| VALIDATE | (inline constraints) |
| ASSIGN | (inline constraints) |
| EXECUTE | MODEL-BUILDER (workers) |
| INTEGRATE | (inline constraints) |
| VERIFY | Any (verification mode) |
| FIX | (inline constraints) |
| ABORT | (inline constraints) |
| REPORT | (inline constraints) |

---

## State Persistence

Team workflow persists state on every phase transition. State includes: current workflow phase, subtask list with per-subtask status and evidence, fix loop count, integration status, and abort flag.

---

## Error Handling

Per `_protocol.md` error hooks (4-class model).
- Worker-level errors handled by worker first (retry), then escalated to leader.
- Leader-level errors → ABORT state.
- Cascading failure: if 3+ workers report errors on same integration → ABORT.

---

## Constraints

- Max 6 concurrent workers.
- Workers must NOT re-plan the global task, switch modes, or edit files outside assigned scope.
- Workers MAY spawn sub-workers only within the /team depth limit (max depth 2, leader → worker → sub-worker — see `policy/subagent_protocol.md`) and MUST report every sub-worker spawn to the leader.
- `worker` role label reserved for team workflow only — never used in solo.
- All worker output subject to leader integration and verification.
