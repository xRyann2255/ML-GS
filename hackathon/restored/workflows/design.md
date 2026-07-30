# Workflows — Design

Subordinate to `workspace/design.md`. Section-specific rules for the workflow primitive.

---

## 1. Purpose

Workflows own **orchestration logic** — how tasks are routed, sequenced, and verified. They are the control-flow layer that binds personas, skills, and memory into executable task pipelines. See `design.md` §Core Model: *Workflow → Orchestration logic*.

---

## 2. Boundaries

| Defines | Must NOT Define |
|---------|-----------------|
| State machines with named states and transitions | Domain knowledge (Slang, pricing) |
| Phase-level persona and memory loading | Language rules or syntax |
| Routing and dispatch logic | Skill implementation detail (no `src/` paths) |
| Entry/exit contracts and error hooks | Reasoning style (that's a persona concern) |
| Composition and handoff mechanics | Policy constraints (those live in `policy/`) |

---

## 3. Structure

Flat directory — no subdirectories.

| File | Role | Required |
|------|------|----------|
| `INDEX.md` | Decision router + quick-reference table | Yes |
| `_protocol.md` | Shared contract (entry/exit, errors, composition) | Yes |
| `<name>.md` | Individual workflow (one file per workflow) | Per workflow |

Naming: lowercase, hyphenated. One workflow per file. No code files.

---

## 4. Rules

1. Every workflow file must reference `_protocol.md` in its first paragraph.
2. Every workflow must define a state machine with named states and explicit transitions.
3. Given any state + input, exactly one transition must fire (deterministic).
4. Memory loading must be declared per phase — no implicit "load what you need". Parameterized declarations referencing `INDEX.md` lookup tables (e.g., "Load domain-relevant P1 files per INDEX.md") satisfy this rule.
5. Allowed personas must be listed per phase.
6. Workflows must not reference `skills/*/src/` paths (implementation detail).
7. Workflows must not embed domain knowledge, language rules, or tool logic.
8. Error handling must reference the 4-class model defined in `_protocol.md`. A single workflow-level error section satisfies this rule; per-phase error tables are optional.
9. Composition depth ≤ 3. No self-yielding (circular composition is a design error).
10. New workflows must be added to `INDEX.md` quick-reference and routing policy.

---

## 5. Interfaces

| Direction | What | Counterpart |
|-----------|------|-------------|
| **Consumes** | Persona definitions (allowed persona lists per phase) | `personas/` |
| **Consumes** | Memory index + loading priorities | `memory/INDEX.md` |
| **Consumes** | Error classification model | `workflows/_protocol.md` § Error Hooks |
| **Consumes** | Handoff protocol | `workflows/_protocol.md` § Handoff Integration |
| **Consumes** | Output contract (next-steps format) | `policy/output_contract.md` |
| **Exposes** | Active workflow + state to session | ephemeral session state |
| **Exposes** | Routing decisions to the agent | `INDEX.md` |

Ordering: Workflow selection happens **before** persona activation — `design.md` §Execution Order: *Workflow → Persona → Skills → Memory*.

---

## 6. Anti-Patterns

1. **Embedding domain knowledge in a workflow.** "If the script uses DRA, load X" — domain routing belongs in skill dispatch or memory, not workflow state logic.
2. **Implicit persona selection.** Phase says "act" without naming an allowed persona. Every ACT phase needs an explicit persona list.
3. **Ambiguous transitions.** Two transitions can fire from the same state+condition. Each row in a transition table must be mutually exclusive.
4. **Workflow as skill wrapper.** A workflow that just calls one skill with no state machine is a skill dispatch, not a workflow — use skill routing instead.
5. **`src/` path in workflow file.** Referencing a skill's `src/` script by path couples the workflow to tool implementation. Name the skill; the skill owns its tools.

---

## 7. Lint

| Check | What It Validates | Severity | Source |
|-------|-------------------|----------|--------|
| `dependency-direction` | Workflows must not reference skill `src/` paths | WARN | `design_lint.py` check 7 |
| `section-design` | Required headings present, ≤120 lines | WARN | `design_lint.py` check 8 |

### Gaps (rules in §4 not yet lint-enforced)

| Rule | Gap | Verification Today |
|------|-----|-------------------|
| §4.1 — `_protocol.md` reference | Not checked | Manual |
| §4.2 — State machine present | Not checked | Manual |
| §4.7 — No domain knowledge | Not checked (only `src/` paths checked) | Manual |
| §4.10 — INDEX.md listing | Not checked | Manual |

---

## Extension Protocol

To add a new workflow:

1. Create `workflows/<name>.md` implementing `_protocol.md`.
2. Define state machine, per-phase persona list, per-phase memory spec.
3. Add entry to `INDEX.md` quick-reference table.
4. Add keyword triggers to `INDEX.md` (if applicable).
5. Run `design_lint.py` — zero new violations.
