# Workflow: Cure

Implements [_protocol.md](_protocol.md). Design-compliance healthcheck and remediation.

---

## Entry Conditions

Enter when:
- User explicitly uses `/cure`.
- Task pattern matches: "cure", "fix design violations", "audit and fix", "healthcheck".

---

## State Machine

```
DIAGNOSE → TRIAGE → FIX → VERIFY → DONE
```

### DIAGNOSE

**Persona:** — (read-only)
**Memory:** Load target design docs (`personas/design.md`, `workflows/design.md`, `skills/design.md`, `memory/design.md`) as needed for scope.

**Actions:**
1. Determine scope from user message (all, personas only, workflows only, specific file).
2. Audit each target against its design spec. Rate findings: CRITICAL / HIGH / MEDIUM / LOW.
3. Apply pragmatism filter: skip findings where the fix adds ceremony without behavioral improvement (e.g., state machines for inherently linear 5-line procedures).

| Condition | Transition |
|-----------|-----------|
| Findings produced | → TRIAGE |
| No findings | → DONE (clean) |

### TRIAGE

**Actions:**
1. Present findings grouped by severity with file counts.
2. Separate actionable (broken references, wrong persona names, missing index entries) from cosmetic (missing boilerplate that doesn't affect behavior).
3. Give honest assessment: which fixes matter, which are context bloat.
4. Ask user which to fix. Never auto-proceed on CRITICAL/HIGH without approval.

| Condition | Transition |
|-----------|-----------|
| User approves fix list | → FIX |
| User says report-only | → DONE |

### FIX

**Persona:** MODEL-BUILDER
**Memory:** Load per finding as needed.

**Actions:**
1. Apply approved fixes, severity order, small diffs.
2. Skip unfixable items (note reason).

| Condition | Transition |
|-----------|-----------|
| All approved items addressed | → VERIFY |

### VERIFY

**Persona:** — (read-only)

**Actions:**
1. Re-run `design_lint.py` on modified files.
2. Spot-check that fixed findings no longer appear.
3. Max 2 FIX↔VERIFY loops if new issues introduced.

| Condition | Transition |
|-----------|-----------|
| Clean or pre-existing LOW only | → DONE |
| New violations from fixes | → FIX (max 2 loops) |

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| DIAGNOSE | — (read-only, inline) |
| TRIAGE | — (lightweight) |
| FIX | MODEL-BUILDER |
| VERIFY | — (read-only, inline) |

---

## Error Handling

Per `_protocol.md` 4-class model:
- Audit tool failure: retry once, then report partial.
- Fix failure: try alternative (max 2), then skip.
- Max 2 FIX↔VERIFY cycles.

---

## Constraints

- DIAGNOSE and VERIFY are read-only. No file writes.
- Findings must cite design doc rule (§ number).
- All fixes require user approval at TRIAGE.
- Small, reversible diffs only.
- **Pragmatism gate:** Do not prescribe fixes that add structural ceremony without behavioral improvement. A 5-line checklist workflow does not need a state machine just because `design.md §4.2` says so.
- **Boundary with `housekeep.md`:** Housekeep owns lint/schema/broken-link fixes. Cure owns design-compliance (rule violations in personas, workflows, skills, memory structure).

