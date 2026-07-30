# `design.md` — Agent Framework Design Document

> Single source of truth for system-wide architecture. Section-specific rules live in each section's `design.md`.

---

## Goal

Build a lean agent framework that:

- Minimizes token usage
- Remains predictable and debuggable
- Scales via layered specialization
- Enforces structure through lintable rules

---

## Core Model

The system is composed of **five primitives**:

| Primitive | Purpose | Section Design |
|-----------|---------|----------------|
| **Persona** | Reasoning style and defaults | `personas/design.md` |
| **Skill** | Narrow executable capability | `skills/design.md` |
| **Memory (CoALA)** | Structured, distilled knowledge | `memory/design.md` |
| **Workflow** | Orchestration logic | `workflows/design.md` |
| **Policy** | Global constraints and guardrails | `policy/design.md` |

---

## Hard Boundaries

| Primitive | **Defines** | **Must NOT Define** |
|-----------|-------------|---------------------|
| Persona | How to think | What to know or execute |
| Skill | What to do | What to store |
| Memory | What to know | Raw or verbose information |
| Workflow | How to run | Domain reasoning |
| Policy | What is allowed | Execution or reasoning |

> **Violations are design errors.** Section-level design.md files refine these boundaries.

---

## Execution Order

Workflow → Persona → Skills → Memory

**Policy is orthogonal:**

- Always enforced
- Not part of execution flow

---

## Repo Shape (Strict)

```
/workspace          — Build artifacts, config, lint, governance, tmp
  /plan             — Plans files (agent working area)
  /config           — App configuration
  /governance       — AI governance docs
  /lint             — Lint scripts (design_lint, validate_memory, etc.)
  /tests            — Test suite
  /raw              — Unprocessed data inputs
  /tmp              — Ephemeral outputs (TTL-managed, not committed)
/workflows          — Orchestration state machines
/skills             — Executable capabilities (SKILL.md + src/)
/memory             — CoALA knowledge files (flat, frontmatter-validated)
/personas           — Reasoning styles and defaults
/policy             — Global constraints and guardrails
/design.md          — This file (system-wide SSoT)
```

### Rules

- `design.md` is the **single source of truth** for system-wide rules
- Section-level `design.md` files are **subordinate** — on conflict, this file wins
- No new top-level directories without justification
- All files must live in the correct layer

---

## Workspace Structure

`workspace/` is infrastructure, not a primitive. It holds build tooling, config, and ephemeral state.

| Directory | Purpose | Committed |
|-----------|---------|-----------|
| `plan/` | Agent plans and team state files | Yes |
| `config/` | Application settings | Yes |
| `governance/` | AI model cards, inventory entries | Yes |
| `lint/` | Lint scripts enforcing design rules | Yes |
| `tests/` | Test suite | Yes |
| `raw/` | Unprocessed data inputs | Yes |
| `tmp/` | Ephemeral outputs, logs, extracts | No (TTL-managed) |

### Workspace Rules

1. `tmp/` is for persisted data artifacts only — no throwaway scripts (use inline execution).
2. `tmp/` files follow TTL: 7 days (logs), 14 days (extracts), 30 days (data).
3. `plans/` files are read-only to executor personas.
4. Lint scripts must exit 0 on pass, 1 on violations.

---

## Layering Model

| Layer | Scope |
|-------|-------|
| 1. **Base** | Language fundamentals |
| 2. **Domain** | Abstractions and conventions |
| 3. **Specialist** | System-specific knowledge |

### Rules

- Higher layers **may** depend on lower layers
- Lower layers **must not** depend on higher layers
- Only load the **minimum required** layer

---

## Invocation Model

```
/persona:  /skills:  /workflow:
```

> Policy is **not** directly invoked.

---

## Design Bias

| Prefer | Over |
|--------|------|
| Explicit | Implicit |
| Small | General |
| Layered | Flat |
| Distilled | Exhaustive |
| Enforceable rules | Convention |

---

## Design Lint (Enforcement)

Enforced via **`design_lint.py`**. Full check details in each section's `design.md` §7.

| Category | What It Validates |
|----------|-------------------|
| **Structural** | Valid directories, required dirs present, misplaced files |
| **Skills** | Size limits, memory references, no upward dependencies |
| **Memory (CoALA)** | Required sections present |
| **Personas** | No large code blocks, no tool path embeds |
| **Policy** | No large code blocks, no tool path references |
| **Dependencies** | No upward dependencies, no workflow→skill src paths |

---

## Enforcement Model

- Runs in **CI** and **pre-commit**
- Violations **block merges**
- Validates structure, schema, size, duplication, dependencies

---

## Summary

**System properties:** Minimal structure · Explicit execution · Layered knowledge · Enforced constraints · Token-efficient

**Memory follows CoALA:** compressed, atomic, linked, actionable

> **This is a constraint system, not a guideline.**

