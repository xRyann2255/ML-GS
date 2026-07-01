# Workflow: Interview

Implements [_protocol.md](_protocol.md). Produces a clarified brief or approved plan — never code.

---

## Entry Conditions

Enter when ANY hold:
1. User explicitly uses `/plan` with ambiguous scope.
2. Request is broad with no clear acceptance criteria.
3. User says "don't assume", "let's discuss first", or equivalent.
4. Task involves irreversible side-effects and intent is not fully clear.
5. Multiple plausible interpretations exist and choosing wrong wastes >30 min.

---

## State Machine

```
OPEN → GATHER → CONVERGE → BRIEF → ROUTE → DONE
```

### OPEN

**Persona:** — (lightweight)
**Memory:** Load `person/user.md` only.

**Actions:**
1. Acknowledge interview mode entry.
2. Identify which question categories (see below) have gaps.

→ GATHER.

### GATHER

**Persona:** — (interviewer mode)
**Memory:** Load domain-relevant P1 memory per `INDEX.md` lookup tables.

**Question categories** — track coverage:

| Category | Purpose | Example |
|----------|---------|---------|
| **Scope** | What's in/out | "Does this include the batch path or just real-time?" |
| **Priority** | What matters most | "Speed or correctness first?" |
| **Constraint** | Hard limits | "Any files we can't touch?" |
| **Tradeoff** | Acceptable compromises | "Partial coverage now vs. full later?" |
| **Acceptance** | How to know it's done | "What does success look like?" |

**Rules:**
- Max 5 questions per round.
- Summarize understanding back to user after each round.
- Max 5 rounds total.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| All 5 categories have ≥1 answer | → CONVERGE |
| User says "just do it" | → BRIEF |
| 5 rounds exhausted without convergence | → CONVERGE (force with gaps noted) |

### CONVERGE

**Persona:** —
**Memory:** No additional loads.

**Convergence test:** All 5 question categories have at least one answer.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| All 5 categories answered | → BRIEF |
| Gaps remain | → BRIEF (with gaps flagged) |

### BRIEF

**Persona:** —
**Memory:** No additional loads.

**Actions:**
Produce a brief with these mandatory fields:

```
## Brief
- **Scope:** ≤3 sentences — what's in, what's out
- **Acceptance Criteria:** numbered list
- **Constraints:** hard limits discovered
- **Priority:** what matters most
- **Tradeoffs:** compromises accepted
- **Gaps:** unresolved questions (if any)
- **Recommended Workflow:** execute | plan | team
- **Recommended Persona:** model-builder | eval-sentinel | etc.
```

Present to user for approval.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| User approves brief | → ROUTE |
| User requests changes | → GATHER (targeted round) |
| User cancels | → DONE |

### ROUTE

**Persona:** —
**Memory:** No additional loads.

**Actions:**
1. Based on brief's recommended workflow, enter that workflow with the brief as input context.
2. Pass acceptance criteria as the workflow's AC.
3. Yield per `_protocol.md` composition interface.

→ DONE (interview complete, execution continues in target workflow).

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| OPEN | Any (lightweight) |
| GATHER | Any (interviewer mode) |
| CONVERGE | Any |
| BRIEF | Any |
| ROUTE | Any |

---

## Error Handling

Per `_protocol.md` error hooks (4-class model).
- Contradictory requirements → state the contradiction explicitly, ask user to choose.
- 3 rounds with no convergence → surface ambiguity, force a decision.

---

## Constraints

- This workflow is read-only with respect to workspace code.
- Output is artifacts (brief, plan) and conversation — never file edits.
- No implementation personas are active during interview.
