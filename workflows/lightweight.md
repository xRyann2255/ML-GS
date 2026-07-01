
# Workflow: Lightweight

Implements [_protocol.md](_protocol.md). Budget-mode execution — minimal context, no persona loading, collapsed pipeline. Trades depth for speed and token efficiency.

---

## Entry Conditions

Enter when:
- User explicitly uses `/lightweight` or `/lite`.
- Message contains "lightweight", "budget mode", "quick mode", "fast mode", "low context", "lite mode".
- Another workflow explicitly downgrades here (e.g., trivial task detected in `plan.md` SCOPE).

---

## Design Rationale

Normal workflows load personas, P1/P2 memory, write checkpoints, and yield between plan→execute. This is correct for non-trivial work but expensive for:
- Simple file edits, one-liner answers, quick lookups.
- Tasks where the agent's base knowledge suffices.
- Sessions where the user is budget-conscious.

Lightweight strips all optional ceremony while preserving the `_protocol.md` interface so it composes like any other workflow.

---

## Context Budget Rules

These rules override the normal loading behavior:

| Category | Normal | Lightweight |
|----------|--------|-------------|
| Boot files (P0) | Always | Always (already loaded) |
| Persona files | Per phase spec | **BUDGETEER only** — loaded once at entry, no swaps |
| P1 memory | Per task type | **Only on explicit ESCALATE** |
| P2 memory | On reference | **Never** |
| Skill SKILL.md | Per keyword | **Header + procedure only** (skip examples, references) |
| Checkpoint recording | Every phase | **Skip** — no checkpoints |
| Task tracking tool | Multi-step work | **Only if ≥4 steps** |
| Plan artifacts | `plan.md` writes to `plans/` | **Never** — plan is inline or skipped |
| Session state tracking | Full schema | **Minimal** — `active_workflow` + `error_count` only |
| Subagent delegation | Per `subagent_protocol.md` | **Never** — single-thread only |

**Memory ceiling:** ≤20% of context window (vs. normal 60% cap). If a task would require more, escalate.

---

## State Machine

```
TRIAGE → ACT → DONE
         ↓
      ESCALATE → (normal workflow)
```

### TRIAGE

**Persona:** BUDGETEER
**Memory:** P0 only (already loaded at boot). No additional loads.

**Actions:**
1. Classify task feasibility for lightweight execution:
   - Can this be done with base agent knowledge + workspace inspection?
   - Does it require domain-specific memory or specialist validation context?
   - Is it a single logical change or a bounded set of changes?
2. If a skill keyword matches, load only the skill's top-level procedure (not full SKILL.md).
3. State any assumptions made due to skipped context.
> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.
| Condition | Transition |
|-----------|-----------|
| Task is feasible without deep context | → ACT |
| Task requires domain memory, persona reasoning, or 3+ files of unfamiliar code | → ESCALATE |
| Intent is ambiguous and cannot be reasonably inferred | → ESCALATE |

No checkpoint recorded.

### ACT

**Persona:** BUDGETEER
**Memory:** No additional loads. Read files on demand via tools only.

**Actions:**
1. Execute the task directly — implement, edit, answer, or look up.
2. Self-check the result (re-read edited files, check for errors).
3. If errors found and fix is obvious: fix inline (max 2 retries).
4. If errors found and fix is non-obvious: → ESCALATE.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| Task complete, self-check passes | → DONE |
| Scope unexpectedly expands (3+ new files) | → ESCALATE |
| Error after 2 retries | → ESCALATE |

No checkpoint recorded.

### DONE

**Persona:** BUDGETEER
**Memory:** No loads. No unloads.

**Actions:**
1. Brief completion summary (1–3 sentences).
2. List files changed (if any).
3. Skip numbered next-steps unless follow-up is non-obvious.

Exit per `_protocol.md` exit contract (minimal variant).

### ESCALATE

**Persona:** — (none; handoff clears BUDGETEER)
**Memory:** No loads at escalation point.

**Actions:**
1. State why lightweight mode is insufficient (what context is needed).
2. Recommend the appropriate normal workflow (`plan.md`, `execute.md`, `research.md`, etc.).
3. Yield to that workflow at its entry state, passing collected context.

| Condition | Transition |
|-----------|-----------|
| Always | → Selected normal workflow's entry state |

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| TRIAGE | BUDGETEER |
| ACT | BUDGETEER |
| DONE | BUDGETEER |
| ESCALATE | None (handoff to normal workflow loads appropriate persona) |

---

## Error Handling

Simplified from `_protocol.md` 4-class model:

| Error Class | Behavior |
|-------------|----------|
| **Transient** | Retry once. |
| **Deterministic** | → ESCALATE immediately. |
| **Ambiguous** | → ESCALATE immediately. |
| **Destructive** | → ESCALATE immediately (rollback handled by receiving workflow). |

No retry loops beyond phase-level max of 2. Fail fast, escalate early.

---

## Anti-Patterns

1. **Loading additional persona files.** BUDGETEER is the only persona. If you need MODEL-BUILDER/EVAL-SENTINEL/etc., escalate.
2. **Loading P1/P2 memory proactively.** Read workspace files with tools instead. Only escalate if domain memory is truly needed.
3. **Writing plan artifacts.** Lightweight doesn't plan — it acts. If planning is needed, escalate to `plan.md`.
4. **Staying in lightweight when stuck.** After 2 retries, escalate. Don't burn tokens spinning.
5. **Using lightweight for tasks requiring domain-specific memory.** If the task needs syntax memory, validation memory, or a specialist persona, escalate to `execute.md`.

---

## Suitability Guide

| Task Type | Lightweight? | Why |
|-----------|-------------|-----|
| Simple file edit (<20 lines, clear intent) | Yes | Base knowledge sufficient |
| Quick lookup / explain code | Yes | Tool inspection sufficient |
| One-liner question | Yes | No memory needed |
| Memory file maintenance (schema-valid edits) | Maybe | Escalate if governance rules unclear |
| Domain read-only (find, read, explain) | Maybe | May need skill procedure only |
| Domain write/edit (requires specialist memory) | No | Requires domain-specific memory |
| Multi-file refactor | No | Requires planning + scope tracking |
| Domain question | No | Requires semantic memory |
| New feature implementation | No | Requires planning workflow |

---

## Constraints

- This workflow never yields to `interview.md` — if intent is unclear, escalate to a normal workflow that can interview.
- Max 1 persona load (BUDGETEER, at entry). No persona swaps.
- Max 0 P1/P2 memory loads (unless via ESCALATE, which exits lightweight).
- No composition depth — lightweight does not yield to other workflows. ESCALATE hands off entirely (the receiving workflow runs independently, not as a child).
