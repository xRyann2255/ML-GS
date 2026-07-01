# Skills — Design

Subordinate to `workspace/design.md`. Section-specific rules for the skill primitive.

---

## 1. Purpose

Skills own **narrow executable capabilities** — each skill encapsulates one tool or API with clear inputs, outputs, and authority bounds. They are the "what to do" layer. See `design.md` §Core Model: *Skill → Narrow executable capability*.

---

## 2. Boundaries

| Defines | Must NOT Define |
|---------|-----------------|
| Tool execution logic and CLI wrappers | Persistent knowledge (move to `memory/`) |
| Input/output contracts per skill | Reasoning style (that's a persona concern) |
| Authority bounds (read-only, write-scoped) | Orchestration logic (that's a workflow concern) |
| Trigger keywords for dispatch | Policy constraints (those live in `policy/`) |

---

## 3. Structure

```
skills/
  INDEX.md                    # Required — registry + decision guide
  <SKILL_NAME>/               # UPPER_SNAKE_CASE directory
    SKILL.md                  # Required — skill guide
    src/                      # Optional — runnable helper scripts
      <script>.py|.sh|.ps1
```

- One directory per skill. Name: UPPER_SNAKE_CASE.
- `SKILL.md` is the single entry point. Required sections: frontmatter (`name`, `description`), Skill Identity table, When to Use, Procedures.
- `src/` holds helper scripts. Scripts write output to `workspace/tmp/`.
- Max nesting: `skills/<NAME>/src/` — no deeper.

---

## 4. Rules

1. Every skill directory must contain a `SKILL.md`.
2. `SKILL.md` must include YAML frontmatter with `name` and `description` fields.
3. `SKILL.md` must include a Skill Identity table (Name, Scope, Inputs, Outputs, Authority).
4. Skills must be stateless — no persistent state across invocations.
5. Skills must reference `memory/` for domain knowledge rather than embedding it inline.
6. `SKILL.md` files ≥250 lines trigger a WARN; ≥400 lines is an ERROR → extract to memory.
7. Skills must not link upward to `personas/` or `policy/`.
8. Helper scripts in `src/` must write outputs to `workspace/tmp/`, not `memory/`.
9. New skills must be added to `INDEX.md` registry and `workflows/INDEX.md`.
10. Dependency skills (e.g., GSSSO_AUTH) must declare they are called by other skills, not directly.

---

## 5. Interfaces

| Direction | What | Counterpart |
|-----------|------|-------------|
| **Consumes** | Domain knowledge files | `memory/ref/*`, `memory/sys/*` |
| **Consumes** | User identity (DB paths, kerberos) | `memory/person/user.md` |
| **Exposes** | Trigger keywords | `workflows/INDEX.md` |
| **Exposes** | Capability registry | `skills/INDEX.md` |
| **Called by** | Workflow phases (via persona) | `workflows/*.md` |

Ordering: Skills are invoked **after** workflow selects persona — `design.md` §Execution Order: *Workflow → Persona → Skills → Memory*.

---

## 6. Anti-Patterns

1. **Skill as knowledge store.** A SKILL.md that's 80% reference tables and 20% procedure. Move knowledge to `memory/ref/`; keep the skill procedural.
2. **Upward dependency.** Skill references a persona file or a policy file by path. Skills are lower-layer; they must not depend on higher-layer primitives.
3. **Hardcoded identifiers.** Embedding kerberos, DB paths, or Object DB names. Use placeholders; resolve at runtime from `person/user.md`.
4. **God skill.** One skill handling unrelated capabilities. Split into focused skills with distinct scopes.
5. **Script without SKILL.md.** Runnable code in `src/` with no governing SKILL.md. Every `src/` must have a parent SKILL.md.

---

## 7. Lint

| Check | What It Validates | Severity | Source |
|-------|-------------------|----------|--------|
| `skill-size` | SKILL.md WARN ≥250 lines, ERROR ≥400 | WARN/ERROR | `design_lint.py` check 2 |
| `skill-memory-ref` | SKILL.md >80 lines must link to `memory/` | WARN | `design_lint.py` check 3 |
| `dependency-direction` | Skills must not link to `personas/` or `policy/` | WARN | `design_lint.py` check 7 |
| `section-design` | Required headings present, ≤120 lines | WARN | `design_lint.py` check 8 |

### Gaps

| Rule | Gap | Verification Today |
|------|-----|-------------------|
| §4.1 — SKILL.md exists | Not checked by design_lint | Manual |
| §4.2 — Frontmatter fields | Not checked by design_lint | `validate_skills.py` |
| §4.9 — INDEX.md listing | Not checked | Manual |

---

## Extension Protocol

To add a new skill:

1. Create `skills/<NAME>/SKILL.md` with required frontmatter and Skill Identity table.
2. Optionally add `src/` with helper scripts.
3. Add entry to `skills/INDEX.md` registry under the appropriate section.
4. Add trigger keywords to `workflows/INDEX.md`.
5. Update implementation boundary: increment skill count and append name to roster.
6. If skill needs domain knowledge, create a `memory/` file and register in `memory/INDEX.md`.
7. Run `design_lint.py` -- zero new violations.

To remove a skill:

1. Delete `skills/<NAME>/` directory.
2. Remove from `skills/INDEX.md`, `workflows/INDEX.md`, implementation boundary.
3. Search for remaining references (`grep -r <NAME> --include="*.md"`) and clean up.

## Related Memory

- memory/ref/skill-scripts.md — Skill script conventions
- workspace/docs/data-audit.md — Comprehensive data query cookbook. Any skill that fetches or processes market data should reference this doc for runnable query patterns.
