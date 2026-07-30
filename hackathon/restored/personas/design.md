# Personas — Design

Subordinate to `workspace/design.md`. Section-specific rules for the persona primitive.

---

## 1. Purpose

Personas own **reasoning style and defaults** — how the agent thinks, not what it knows or executes. Each persona defines cognitive approach, output shape, and behavioral constraints for a specific role. See `design.md` §Core Model: *Persona → Reasoning style and defaults*.

---

## 2. Boundaries

| Defines | Must NOT Define |
|---------|-----------------|
| Reasoning approach and cognitive style | Domain knowledge (move to `memory/`) |
| Output format and structure | Tool execution logic (move to `skills/`) |
| Behavioral constraints (read-only, no-fix, etc.) | Orchestration or routing (move to `workflows/`) |
| Default effort level and ask gates | Memory content or loading rules |

---

## 3. Structure

Flat directory — no subdirectories.

| File | Role | Required |
|------|------|----------|
| `INDEX.md` | Capabilities matrix + conflict rules | Yes |
| `<name>.md` | Individual persona definition (lowercase) | Per persona |

Standard persona sections (XML-tagged):
- `<identity>` — role statement, responsibilities, non-goals
- `<constraints>` — scope guard, ask gate, effort gate (all three required), hard rules
- `<execution_loop>` — success criteria, verification checklist
- `<style>` — output contract, anti-patterns, scenario handling, final checklist

Frontmatter: `description` (required), `argument-hint` (optional).

---

## 4. Rules

1. Every persona must have an entry in `INDEX.md` with Role, Outputs, and Cannot Do columns.
2. Personas must not embed domain knowledge — reference `memory/` files instead.
3. Personas must not reference `skills/*/src/` paths (tool implementation detail).
4. Code blocks in persona files must be ≤10 lines (output templates, not runnable code).
5. Read-only personas (ANALYST, ORACLE, DOCTOR, SENTINEL, SCRIBE, PATHFINDER, AUDITOR, PRESCRIBER, TRACEHOUND, QUARTERMASTER) must declare write tools blocked.
6. Mutually exclusive personas must be documented in `INDEX.md` §Role Conflict Rules.
7. New personas must be added to `INDEX.md` and relevant workflow allowed-persona lists.
8. Persona names in filenames must be lowercase; display names in content are UPPER_CASE.
9. Inline HTML comment annotations (`<!-- <--- label -->`) are optional, reserved for hard behavioral constraints (read-only enforcement, hard stops, circuit breakers). Do not annotate XML section tags or structural headings. `GUIDANCE` markers are not used.

---

## 5. Interfaces

| Direction | What | Counterpart |
|-----------|------|-------------|
| **Selected by** | Workflow phases (allowed persona per phase) | `workflows/*.md` |
| **Activated by** | `/prompt` commands or keyword dispatch | `workflows/INDEX.md` |
| **Consumes** | Memory files (loaded per workflow phase spec) | `memory/` |
| **Exposes** | Capabilities and constraints matrix | `personas/INDEX.md` |

Ordering: Personas activate **after** workflow selection — `design.md` §Execution Order: *Workflow → Persona → Skills → Memory*.

---

## 6. Anti-Patterns

1. **Persona as knowledge base.** Embedding Slang syntax, API schemas, or pricing rules inside a persona. That's memory content.
2. **Tool logic in persona.** Persona embeds a direct path to a skill helper script. Name the skill; let the skill own its tools.
3. **Unbounded persona.** No scope guard or ask gate — persona can do anything. Every persona needs explicit constraints.
4. **Overlapping roles.** Two personas with identical capabilities differing only in name. Consolidate or differentiate by constraint.
5. **Persona with orchestration.** "If task is type A, switch to persona B" — that's workflow logic, not persona logic.

---

## 7. Lint

| Check | What It Validates | Severity | Source |
|-------|-------------------|----------|--------|
| `persona-purity` | No code blocks >10 lines | WARN | `design_lint.py` check 5 |
| `persona-purity` | No skill `src/` path references | WARN | `design_lint.py` check 5 |
| `section-design` | Required headings present, ≤120 lines | WARN | `design_lint.py` check 8 |

### Gaps

| Rule | Gap | Verification Today |
|------|-----|-------------------|
| §4.1 — INDEX.md entry | Not checked | Manual |
| §4.2 — No domain knowledge | Not checked (only code blocks + src paths) | Manual |
| §4.5 — Write-tool blocking declared | Not checked | Manual |
| §4.6 — Conflict rules documented | Not checked | Manual |

---

## Extension Protocol

To add a new persona:

1. Create `personas/<name>.md` (lowercase) with `<identity>`, `<constraints>`, `<execution_loop>`, `<style>` sections.
2. Add entry to `personas/INDEX.md` (Role, Outputs, Cannot Do).
3. If mutually exclusive with existing persona, add to §Role Conflict Rules.
4. Add to allowed-persona lists in relevant `workflows/*.md` phases.
5. If directly invocable, add `/prompt` entry in `workspace/.github/prompts/`.
6. Run `design_lint.py` — zero new violations.
