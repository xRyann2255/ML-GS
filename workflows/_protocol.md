# Workflow Protocol

Shared contract for all workflows. Keep it simple.

---

## Entry

1. Load memory files listed in the workflow's first phase.
2. Do the work described in each state, in order.
3. When a state's transition condition is met, move to the next state.

If unclear which workflow applies: follow the `/prompt` attachment. No prompt? Use keywords from `INDEX.md`. Still unclear? Default to `plan.md`.

---

## Exit

1. Verify the work is done (evidence, not assumption).
2. **State updates** (if experiment results changed or milestone shifted):
   - Update `memory/research/project-state.md` with new QLIKE numbers or milestone status.
   - Update `workspace/research/trials.yaml` if a trial was proposed, started, or completed.
3. Offer numbered next-steps.

---

## Errors

- If something fails: retry once.
- If it fails again: escalate to the user with what you tried and what went wrong.

---

## Composition

A workflow can hand off to another (e.g., `plan.md` hands to `execute.md`). When doing so, state where you came from so you can return if needed. Max nesting: 2.

---

## Persona Quick-Reference

When a workflow state names a persona, apply that persona's key constraint without loading the full file:

| Persona | Key Constraint |
|---------|---------------|
| MODEL-BUILDER | Can write code, must verify, no replanning |
| TRACEHOUND | Diagnosis only, no fixes, handoff required |
| EVAL-SENTINEL | Review only, no auto-apply |
| BUDGETEER | No memory loads, no persona swaps |
| VOL-RESEARCHER | Exploration only, no code, no model training |

Other personas have been inlined as constraint blocks directly in their target workflows.

**Rule:** A workflow cannot yield to itself. Circular composition is a design error.

---

## Constraints

- Workflows must NOT contain domain knowledge, language rules, or skill logic.
- Workflows define orchestration only — the *how to run*, not *what to know*.
- Each workflow must define a state machine with unambiguous transitions.
- Memory loading is explicit per phase — no implicit "load what you need".
- All workflows reference this protocol for shared behavior.
