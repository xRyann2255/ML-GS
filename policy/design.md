# Policy — Design

Subordinate to `workspace/design.md`. Section-specific rules for the policy primitive.

---

## 1. Purpose

Policy owns **global constraints and guardrails** — what is allowed and what is not, independent of execution flow. Policy is orthogonal to the execution order; it is always enforced. See `design.md` §Core Model: *Policy → Global constraints and guardrails*.

---

## 2. Boundaries

| Defines | Must NOT Define |
|---------|-----------------|
| Safety rules and hard limits | Domain knowledge (move to `memory/`) |
| Architectural invariants | Execution logic or control flow (move to `workflows/`) |
| Task classification and routing rules | Reasoning style (move to `personas/`) |
| Implementation boundaries and gates | Tool implementation (move to `skills/`) |
| Output format contracts | |

---

## 3. Structure

Flat directory — no subdirectories.

| File | Role | Required |
|------|------|----------|
| `index.md` | Policy index — lists all policy docs | Yes |
| `execution_protocol.md` | Default execution flow, verification, continuation | Yes |
| `output_contract.md` | Response format by task type | Yes |
| `<topic>.md` | Individual policy document | Per policy |

Naming: lowercase, hyphenated. One concern per file.

---

## 4. Rules

1. Every policy file must be listed in `index.md`.
2. Policy files must not contain domain knowledge (Slang, pricing, etc.).
3. Policy files must not contain executable code or tool invocation logic.
4. Code blocks in policy files must be ≤10 lines (format examples, not runnable code).
5. Policy files must not reference `skills/*/src/` paths (implementation detail).
6. Policy is never directly invoked — it's always-on. No `/policy` prompt command.
7. Constraints must be testable: each rule should have a verifiable yes/no condition.
8. New policy files must be added to `index.md` with a one-line description.

---

## 5. Interfaces

| Direction | What | Counterpart |
|-----------|------|-------------|
| **Governs** | All other primitives (always enforced) | System-wide |
| **Referenced by** | `copilot-instructions.md` (boot protocol) | `workspace/docs/slang/copilot-instructions.md` |
| **Referenced by** | Workflow error hooks | `workflows/_protocol.md` |
| **References** | Master design rules | `workspace/design.md` |

Ordering: Policy is **orthogonal** — not part of the execution order. Always active regardless of workflow, persona, or skill. See `design.md` §Execution Order.

---

## 6. Anti-Patterns

1. **Policy as execution guide.** "When debugging, first run X then Y" — that's a workflow or procedural memory file.
2. **Domain knowledge in policy.** "Swaps use…" — that belongs in `memory/ref/`.
3. **Large code examples.** Policy shows a 20-line script as an example. Keep to ≤10 lines; move examples to skills or memory.
4. **Tool path references.** Policy embeds a direct path to a skill helper script. Name the capability; let the skill own the path.
5. **Duplicate constraints.** Same rule stated in `policy/` and `workspace/design.md`. Reference the master; don't restate.

---

## 7. Lint

| Check | What It Validates | Severity | Source |
|-------|-------------------|----------|--------|
| `policy-purity` | No code blocks >10 lines | WARN | `design_lint.py` check 6 |
| `policy-purity` | No skill `src/` path references | WARN | `design_lint.py` check 6 |
| `section-design` | Required headings present, ≤120 lines | WARN | `design_lint.py` check 8 |

### Gaps

| Rule | Gap | Verification Today |
|------|-----|-------------------|
| §4.1 — index.md listing | Not checked | Manual |
| §4.2 — No domain knowledge | Not checked (only code blocks + src paths) | Manual |
| §4.3 — No executable code | Partially covered by code-block check | Manual |

---

## Extension Protocol

To add a new policy:

1. Create `policy/<topic>.md` with the constraint or guardrail.
2. Add entry to `policy/index.md` with one-line description.
3. If the policy introduces a new hard rule, add to `workspace/design.md` §Hard Boundaries or §Hard Rules as appropriate.
4. Run `design_lint.py` — zero new violations.
