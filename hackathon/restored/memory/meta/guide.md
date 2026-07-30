---
created: 2026-04-08
updated: 2026-04-16
tags: [meta, governance, memory, schema, naming, domains]
status: active
---

# Memory System — Governance Guide

This is the authoritative specification for the memory system. All naming conventions, structure rules, and maintenance behaviors are defined here.

## File Naming

Files are organized into domain subfolders: `{domain}/{subject}.{specificity}.md`

### Domains

| Domain        | Use For                                                         | Example                       |
| ------------- | --------------------------------------------------------------- | ----------------------------- |
| `meta`        | Memory system governance and structure                          | `meta/guide.md`               |
| `person`      | People — their role, relationship, context                      | `person/user.md`              |
| `slang`       | Slang language, tooling, formatting, lint, secexpr              | `slang/best-practices.md`     |
| `ref`         | Technical reference (non-Slang): SecDB, setup, auth, tools      | `ref/python-setup.md`         |
| `sys`         | GS internal systems, platforms, teams, registries               | `sys/enghub.md`               |
| `research`    | ML vol forecasting: literature, features, models, evaluation    | `research/volatility.md`      |
| `vendor`      | Third-party vendor systems, contracts, market data              | `vendor/atg.md`               |

**Decision tree:** meta → person → Slang? `slang/` → GS system/platform? `sys/` → tech reference? `ref/` → ML vol research? `research/` → vendor? `vendor/`

**Reserved domains** — defined for future use, create the subfolder when first needed:

| Domain     | Use For                                        | Example                    |
| ---------- | ---------------------------------------------- | -------------------------- |
| `decision` | Architectural decisions, ADRs                  | `decision/feed-design.md`  |
| `project`  | Projects — goals, status, architecture         | `project/strucd.md`        |
| `episodic` | Past events — incidents, postmortems           | `episodic/outage-2026-03.md` |

### Naming Rules

- Use lowercase with hyphens for multi-word subjects: `ref/goldman-sachs.md`
- Add specificity when needed: `sys/origami.md`, `sys/origami.dra.md`
- Date-stamped files use ISO format: `incident/origami-outage.2026-02.md`
- Keep names concise but descriptive

## Frontmatter

Every file MUST have YAML frontmatter:

```yaml
---
created: 2026-02-28
updated: 2026-02-28
tags: [systems, origami, platform]
status: active
relates:
  - sys/charon.md
  - ref/goldman-sachs.md
---
```

### Required Fields

| Field     | Type   | Description                                                 |
| --------- | ------ | ----------------------------------------------------------- |
| `created` | date   | When the file was first written                             |
| `updated` | date   | When the file was last modified — update this on every edit |
| `tags`    | list   | Lowercase descriptive tags for discovery                    |
| `status`  | string | Trust level — see Status Lifecycle below                    |

### Optional Fields

| Field     | Type | Description                       |
| --------- | ---- | --------------------------------- |
| `relates` | list | Filenames of related memory files |

## Status Lifecycle

Status indicates how much to trust the content:

| Status     | Meaning                                              | When to Use                                          |
| ---------- | ---------------------------------------------------- | ---------------------------------------------------- |
| `draft`    | Unconfirmed by the user. Working document.           | Agent-inferred or researched information             |
| `active`   | Confirmed, trusted. Real memory.                     | Information directly from the user                   |
| `stale`    | Old, possibly outdated. Verify before relying on it. | Files not updated in months, or known to be drifting |
| `archived` | Historical only. Not for current use.                | Superseded decisions, old incidents                  |
| `dormant`  | Parked but load-bearing. Lives under `_dormant/`.    | Content still referenced but not part of active flow |

### Dormant files (`_dormant/`)

Parked-but-load-bearing content (Slang/SecDB/sys) lives under `memory/_dormant/<domain>/`,
keeping its domain subpath. Rules: frontmatter `status: dormant`; every dormant file referenced
by an active skill or memory file gets an INDEX.md row (P3, Status dormant); lints scan
`_dormant` as a source tree and validate refs INTO it (per the lint policy landed in Plan 04).
**Park:** move `memory/<domain>/x.md` → `memory/_dormant/<domain>/x.md`, set `status: dormant`,
rewrite inbound refs, update INDEX. **Restore:** reverse the same four steps.

### Status Rules

- Information the user tells you directly → `active`
- Information you infer from data or context → `draft`
- Always update `status` when confidence changes
- When you touch a stale file and verify it's still accurate, change to `active` and update the date

## Structure Rules

1. **One topic per file.** Always. If a file is growing to cover multiple topics, split it.
2. **Include frontmatter on every file.** No exceptions.
3. **Flag stale or unverified information.** Don't silently rely on old content.
4. **Cross-reference actively.** When creating or editing a file, ask: what else relates to this? Link it — both inline and in `relates:` frontmatter.
5. **Folders are welcome.** The memory system may include arbitrary folder structures for organization. Use subdirectories to group related files when flat naming becomes unwieldy (e.g. `pipg-support-wiki/`, `incidents/`). Folders don't need frontmatter — only files do.

## Maintenance

- **Refactor when needed.** Split unwieldy files. Rename for clarity. The memory is alive.
- **Rewrite when understanding changes.** Don't just append corrections — rewrite the file to reflect current understanding.
- **Update `updated` on every edit.** Always.
- **Remove dead cross-references.** If a related file was deleted or renamed, update the links.

## Writing Style

- Write from my (the agent's) first-person perspective — this is **my** memory. Say "I use", "I clone", "my skill guide", not "the agent does" or "we use".
- Write concise, factual content.
- Use headers to structure longer files.
- Keep every line intentional — this is my brain, not a dump.
- Capture context that flies past — system names, roles, patterns. Knowledge left on the table is knowledge lost.
