# Workflow: Debug

Structured debugging for ML pipeline issues: data problems, convergence failures, feature bugs, and model issues.

---

## Entry Conditions

Enter when:
- User explicitly uses `/debug`.
- Task pattern matches: "debug", "root cause", "why is X broken"
- ML pipeline failures: data issues, convergence problems, feature bugs

---

## State Machine

```
DIAGNOSE → FIX → VERIFY → DONE
   ↑                |
   └── (persists) ──┘  (max 2 loops)
```

### DIAGNOSE

**Persona:** TRACEHOUND
**Memory:** Load `person/user.md` + domain-relevant P1 files per `INDEX.md` lookup tables.

**Constraints:** Reproduce first. One hypothesis at a time. 3-failure circuit breaker.

**Actions:**
1. **Capture symptom** — exact error, reproduction steps, context.
2. **Reproduce** — run failing command, confirm consistent failure.
3. **Hypothesize** — generate 2-3 ranked root cause hypotheses.
4. **Gather evidence** — for each hypothesis, read code/logs/diagnostics. Mark: confirmed, refuted, inconclusive.
5. **Narrow** — identify confirmed root cause with minimal fix scope.

**Circuit breaker:** After 3 refuted hypotheses with no progress, escalate to user with all evidence gathered.

| Condition | Transition |
|-----------|-----------|
| Root cause confirmed, fix is straightforward | → FIX |
| Root cause confirmed, fix is outside scope | → DONE (report diagnosis only) |
| Cannot reproduce after 2 attempts | → DONE (report unable to reproduce) |
| 3-failure circuit breaker triggered | → DONE (escalate with evidence) |

Checkpoint: symptom, root cause, affected files, fix plan.

### FIX

**Persona:** MODEL-BUILDER
**Memory:** Load relevant memory per `INDEX.md` lookup tables matching the fix domain.

**Actions:**
1. Apply minimal fix targeting the diagnosed root cause.
2. Run lint on changed files.
3. Self-check: does the fix address the root cause (not just the symptom)?

| Condition | Transition |
|-----------|-----------|
| Fix applied, lint passes | → VERIFY |
| 3 fix approaches exhausted | → DONE (report blocked with approaches tried) |

Checkpoint: files changed, fix description.

### VERIFY

**Actions:**
1. Re-run the failing reproduction from DIAGNOSE — confirm it passes.
2. Run existing tests to check for regressions.
3. If ML code: check for look-ahead bias in the fix.

| Condition | Transition |
|-----------|-----------|
| Symptom resolved, no regressions | → DONE |
| New regression introduced | → FIX (fix regression, counts toward 3-approach limit) |
| Original symptom persists | → DIAGNOSE (refine, max 2 DIAGNOSE↔VERIFY loops) |

Checkpoint: verification evidence.

---

## Constraints

- Reproduce BEFORE diagnosing. No repro = find conditions first.
- Evidence eliminates hypotheses one by one — no guess-and-fix.
- For data pipeline bugs, validate L2=E-mini only, IV=SPX only constraints first.
- For feature bugs, check for look-ahead bias first (most common ML bug).
- CONFORM gate: re-read changed code files and verify domain conventions before VERIFY.
- Max 2 DIAGNOSE↔VERIFY loops, max 3 fix approaches. Then escalate.
- Present numbered next-steps in final report. Include `/learn` if root cause reveals a recurring pattern.
