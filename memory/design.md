# Memory — Design

Subordinate to `workspace/design.md`. Section-specific rules for the memory (CoALA) primitive.

---

## 1. Purpose

Memory owns **structured, distilled knowledge** — what the agent knows, persisted across sessions. Follows the CoALA framework: compressed, atomic, linked, actionable. See `design.md` §Core Model: *Memory (CoALA) → Structured, distilled knowledge*.

---

## 2. Boundaries

| Defines | Must NOT Define |
|---------|-----------------|
| Persistent facts, patterns, references | Raw or verbose information (distill first) |
| Domain knowledge (Slang, systems, processes) | Execution logic (move to `skills/`) |
| User identity and preferences | Reasoning style (move to `personas/`) |
| Structural metadata and governance | Orchestration (move to `workflows/`) |

---

## 3. Structure

Domain subfolders — see `meta/guide.md` §File Naming for the full domain list.

| File | Role | Required |
|------|------|----------|
| `INDEX.md` | Master index of all memory files | Yes |
| `meta/guide.md` | Governance rules, naming, frontmatter spec | Yes |
| `person/user.md` | User identity and preferences | Yes |
| `<domain>/<subject>.md` | Individual memory file | Per topic |

Naming: `{domain}/{subject}.md`, lowercase with hyphens. Frontmatter required on all content files.

---

## 4. Rules

1. Every memory file must be listed in `INDEX.md` (priority, ~tokens, load trigger) in the same changeset it's added.
2. Content files require valid YAML frontmatter: `created`, `updated`, `tags`, `status`.
3. Domain knowledge files (e.g. `sys/`) must include CoALA sections: Concepts, Rules, Patterns, Edge Cases, Anti-patterns, Links. Exempt: `meta/`, `person/`, `ref/`, `slang/`, `domain/` (structural or reference material), P2 files, and P3 files.
4. Distilled only — no verbose dumps, raw API output, or full transcripts. Code blocks ≤10 lines. **P3 exception:** P3 files may retain longer reference material, verbatim extracts, and extended tables. Distillation preferred but not mandatory.
5. No append-only growth — adding content requires removing/compressing equal amount. **P3 exception:** balanced-growth rule does not apply to P3 archive files.
6. Agent-inferred content starts as `status: draft`, `confidence: low`.
7. No execution logic (→ `skills/`) or orchestration (→ `workflows/`).
8. Disk (`memory/`) is the primary and mandatory destination for all persistent knowledge.
9. Size caps — slang ≤400, ref ≤250, domain ≤300, sys ≤200, meta ≤200, person ≤100, episodic ≤200, decision ≤150, project ≤150 lines. **P2 and P3 files have no per-file line cap.** Loaded budget: P0+P1 ≤50k tokens. On-demand budget: P2 ≤100k tokens. P3 has no total budget (per-file caps only).
10. Staleness: P3 files auto-flagged `stale` after 90 days without update. Quarterly review recommended.

---

## 5. Interfaces

| Direction | What | Counterpart |
|-----------|------|-------------|
| **Consumed by** | All other primitives (knowledge source) | System-wide |
| **Loaded per** | Workflow phase memory specs | `workflows/*.md` |
| **Governed by** | Naming and frontmatter rules | `memory/meta/guide.md` |
| **Validated by** | Memory validation script | `workspace/lint/validate_memory.py` |
| **Indexed in** | Master index | `memory/INDEX.md` |

Ordering: Memory is accessed **after** skills in execution flow — `design.md` §Execution Order: *Workflow → Persona → Skills → Memory*.

---

## 6. Anti-Patterns

1. **Verbose dump.** Pasting raw API output or full conversation transcript into memory. Distill to atomic facts.
2. **Execution in memory.** Memory file contains tool commands or procedural scripts. Move to `skills/`.
3. **Orphan file.** Memory file exists but is not listed in `INDEX.md`. Always update the index.
4. **Missing frontmatter.** Content file without `created`, `updated`, `tags`, `status`. Required by `meta/guide.md`.
5. **Stale knowledge.** Facts that were true months ago but never re-validated. Set `confidence` and review periodically.

---

## 7. Lint

| Check | What It Validates | Severity | Source |
|-------|-------------------|----------|--------|
| `coala-sections` | Content files have required CoALA sections | WARN | `design_lint.py` check 4 |
| `section-design` | `memory/design.md` exists with required headings | WARN | `design_lint.py` check 8 |
| `validate_memory` | Frontmatter fields, naming, domain validity | ERROR | `validate_memory.py` |

### Gaps

| Rule | Gap | Verification Today |
|------|-----|-------------------|
| §4.4 — Distilled only | Not automatable | Manual review |
| §4.7 — No execution logic | Not checked | Manual |
