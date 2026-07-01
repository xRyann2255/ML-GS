# Workflow: Refactor

Implements [_protocol.md](_protocol.md). Structured refactoring pipeline — lock behavior with tests, restructure, verify equivalence.

---

## When to Invoke

Invoke the refactor workflow (`/refactor`) for these scenarios:

| Scenario | Example |
|----------|---------|
| Module restructuring | Splitting a large module into submodules |
| API redesign | Changing function signatures while preserving behavior |
| Pattern migration | Moving from inheritance to composition |
| Dependency reduction | Removing or replacing a library |
| Performance refactor | Algorithmic change that must preserve outputs |

---

## Entry Conditions

Enter when task pattern matches:
- "refactor", "restructure", "reorganize", "redesign API", "split module"
- User explicitly uses `/refactor`.
- Routing policy classified task as refactor.

---

## State Machine

```
SCOPE → LOCK → RESTRUCTURE → VERIFY → REPORT → DONE
```

### SCOPE

**Constraints:** Plan only, no code. Define boundaries and invariants.
**Memory:** Load `person/user.md` + domain-relevant P1 files per `INDEX.md` lookup tables.

**Actions:**
1. Identify what is being refactored and why.
2. Define the invariant: what behavior MUST NOT change.
3. Identify the boundary: which files are in scope, which are out.
4. Assess risk: how many call sites, how critical is the code.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| Scope clear, invariant defined | → LOCK |
| Scope unclear or high-risk | → Yield to `interview.md`, resume SCOPE on return |

Checkpoint: record scope, invariant, boundary, risk assessment.

### LOCK

**Persona:** MODEL-BUILDER
**Memory:** Load relevant test memory and feature documentation.

**Purpose:** Ensure current behavior is captured by tests BEFORE any structural change. This is the safety net.

**Actions:**
1. Run existing tests — confirm they pass (baseline).
2. Identify behavior not covered by existing tests.
3. Write characterization tests for uncovered behavior (tests that lock current output).
4. Run full test suite — confirm new + old tests pass.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| All critical paths covered by tests | → RESTRUCTURE |
| Cannot write tests (code too coupled) | → RESTRUCTURE with explicit risk acknowledgment |
| Test failures in existing code | → Yield to `debug.md`, resume LOCK on return |

Checkpoint: record test coverage baseline, new characterization tests added.

### RESTRUCTURE

**Persona:** MODEL-BUILDER
**Memory:** No additional loads beyond LOCK context.

**Subagent delegation:** When the refactor spans multiple modules, spawn one subagent per module:
- Each subagent receives: module scope (files to restructure), test file paths, invariant definition, write scope
- Orchestrator manages the sequence: spawn → collect → run integration tests
- Subagents execute RESTRUCTURE actions within their bounded module scope
- All subagents MUST use Claude Opus 4.6, depth = 1 (no further spawning)
- See `policy/context-isolation.md` for context packet schema

**Spawn threshold:** If RESTRUCTURE touches 2+ modules, spawn subagents (one per module). Single-module refactors stay inline.

**Actions:**
1. Apply structural changes incrementally (one logical change per step).
2. After each step, run tests to confirm invariant holds.
3. If a test fails mid-refactor, fix immediately before continuing.
4. **CONFORM** — for each changed code file, audit against domain conventions.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| All structural changes complete, tests pass | → VERIFY |
| Test failure after 3 fix attempts | → Revert to LOCK state, escalate |
| Scope drift detected (3+ unplanned files) | → Pause, report drift, ask user |

Checkpoint: record changes made, tests passing at each step.

### VERIFY

**Persona:** — (verification mode)
**Memory:** No additional loads.

**Actions:**
1. Run full test suite (not just affected tests).
2. Run lint and type checking.
3. Compare behavior: before vs. after (spot-check outputs if applicable).
4. Check for orphaned code (dead imports, unused functions).
5. Verify no public API breakage (unless intentional and documented).

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| All checks pass | → REPORT |
| Failures found | → RESTRUCTURE (fix, max 2 loops) |

Checkpoint: record verification evidence.

### REPORT

**Persona:** —
**Memory:** Unload task-specific memory.

**Actions:**
1. Produce refactoring summary: what changed, why, what's preserved.
2. List files changed with line ranges.
3. Include verification evidence (test results, lint output).
4. Numbered next-steps (e.g., update documentation, notify dependents).
5. Exit per `_protocol.md` exit contract.

→ DONE.

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| SCOPE | (inline constraints) |
| LOCK | MODEL-BUILDER |
| RESTRUCTURE | MODEL-BUILDER |
| VERIFY | Any (verification mode) |
| REPORT | Any |

---

## Error Handling

Per `_protocol.md` error hooks (4-class model).
- Test failures during LOCK: yield to `debug.md` for diagnosis.
- Test failures during RESTRUCTURE: revert last step, try alternative approach (max 3).
- Lint/type errors after restructure: fix in-place during VERIFY.
- Scope drift: pause and re-scope with user.

---

## Constraints

- NEVER restructure without tests locked first. The LOCK phase is mandatory.
- Keep diffs reviewable: one logical change per commit.
- Prefer deletion over addition: remove dead code after restructuring.
- The invariant (defined in SCOPE) is sacred — if tests fail, the refactor is wrong.
- Max 1 yield to `debug.md` from LOCK. If tests cannot be fixed, escalate to user.
