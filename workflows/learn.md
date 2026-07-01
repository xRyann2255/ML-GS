# Workflow: Learn

Implements [_protocol.md](_protocol.md). Distills session knowledge into two distinct outputs: **memory items** (structured knowledge) and **workspace fixes** (stale tools, broken code, wrong paths).

---

## Entry Conditions

Enter when:
- User explicitly uses `/learn`.
- Task pattern matches: "learn this", "remember this", "save to memory", "distill session", "persist knowledge".
- Another workflow yields here after producing reusable findings (e.g., `research.md`, `debug.md`, `cure.md`).

---

## Item Kinds

Every candidate discovered by HARVEST is classified into exactly one **kind**:

| Kind | Target | Examples | Persisted To |
|------|--------|----------|-------------|
| **memory** | Knowledge files in `memory/` | New facts, patterns, preferences, environment details, procedural knowledge | `memory/*.md` |
| **fix** | Workspace files | Stale instructions, broken helper scripts, moved paths, wrong configuration values | `skills/**`, `workspace/**` |

**Disambiguation rule:** If a session discovered that something is broken *and* the correct value is worth remembering long-term, create **two items** — a fix (patch the broken file now) and a memory item (persist the knowledge for future sessions).

---

## State Machine

```
HARVEST → DISTILL → VALIDATE → PERSIST → REPORT → DONE
```

### HARVEST

**Persona:** — (lightweight scan)
**Memory:** Load `person/user.md` + `INDEX.md` + memory governance guide.

**Actions:**
1. Identify knowledge sources based on trigger:
   - **Explicit:** User says "learn this", "remember this", "save what we learned".
   - **Post-workflow:** Another workflow yields here with reusable findings.
   - **Session review:** User triggers end-of-session distillation.
2. Enumerate candidate items — both knowledge and breakage discovered in session:
   - **Knowledge:** corrections, discoveries, patterns, preferences.
   - **Breakage:** stale instructions, moved file paths, broken tool code, wrong configuration values.
3. Scan silent observations: check `[observed]` and `[inferred]` entries from current session for promotion candidates.
4. **Classify each item by kind** (`memory` or `fix`):
   - If the item describes a fact, pattern, or preference → `memory`.
   - If the item describes a concrete defect in a workspace file that should be patched → `fix`.
   - If both → create two items (one per kind).
5. For `memory` items: classify by memory domain per governance rules.
6. For `fix` items: identify the **target file(s)** and the **nature of the defect** (stale instruction, wrong path, broken code, missing config).
7. Cap at **5 candidates per kind** (10 total max) by impact. If more exist, note them for a follow-up run.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| Candidate items identified (either kind) | → DISTILL |
| No new knowledge or fixes worth persisting | → REPORT (nothing to learn) → DONE |
| Scope unclear (what should be remembered?) | → Yield to `interview.md`, resume HARVEST on return |

Checkpoint: record candidate items with source, kind, and (for memory) proposed domain.

### DISTILL

**Constraints:** Analysis and synthesis only. No implementation. Validate data constraints (L2=E-mini only, IV=SPX only, 34+1 symbols).
**Memory:** Load existing target files — memory files for `memory` items, workspace files for `fix` items.

**Actions:**

#### Memory items (kind: memory)
1. For each candidate:
   - Check against existing memory: duplicate? contradiction? extension?
   - If duplicate → drop (note in report).
   - If contradiction → flag for user validation at VALIDATE.
   - If extension → draft merge into existing file.
   - If new topic → draft new memory file (compliant frontmatter, `status: draft`, `confidence: low`).
2. Compress: apply memory governance principles per governance guide.

#### Fix items (kind: fix)
1. For each candidate:
   - Read the target file to confirm the defect still exists (it may have been fixed during the session already).
   - If already fixed → drop (note in report).
   - If still broken → draft a **patch** — the replacement(s) needed, or full file rewrite for small files.
   - Categorize the fix:
     - **Stale instruction** — documentation text that no longer matches reality.
     - **Broken code** — helper script with a bug or missing dependency.
     - **Config drift** — path moved, setting value changed, new required variable.
     - **Missing entry** — a step or config that should exist but doesn't.
2. For each patch, note the **evidence** — what happened in the session that proved the defect.

3. Produce **two draft changesets**:
   - **Memory changeset:** list of memory files to create/update with proposed content.
   - **Fix changeset:** list of workspace files to patch with proposed diffs.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| All items are duplicates or already fixed | → REPORT (no new knowledge or fixes) → DONE |
| Item requires external research first | → Yield to `research.md`, resume DISTILL on return |
| At least one changeset is non-empty | → VALIDATE |

Checkpoint: record both draft changesets.

### VALIDATE

**Persona:** — (lightweight, user-facing)
**Memory:** No additional loads.

**Actions:**
1. Present draft changesets to user **in two clearly labeled sections**:

   **§ Memory Items** (persisted to `memory/`):
   - New files: show proposed frontmatter + content summary.
   - Updated files: show diff (what's added/changed).
   - Contradictions: present both sides, ask user to resolve.

   **§ Fix Items** (patched in workspace):
   - For each fix: show target file, defect description, evidence, and proposed patch diff.
   - Flag fixes that touch executable code — these carry execution risk.

2. User approves, adjusts, or rejects each item independently.
3. For memory items marked with `confidence: low` or contradictions, user confirmation is **mandatory** before proceeding.
4. For fix items touching executable code, user confirmation is **mandatory**.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| User approved at least one item (either kind) | → PERSIST |
| User wants adjustments | → DISTILL (re-draft, max 2 DISTILL↔VALIDATE loops) |
| User rejected all items | → REPORT (nothing persisted) → DONE |

Checkpoint: record user decisions per item (approved / adjusted / rejected), by kind.

### PERSIST

**Persona:** MODEL-BUILDER
**Memory:** Load memory governance guide (hard gates).

**Actions:**

#### Phase A — Memory writes
For each approved `memory` item:
1. Pre-flight: verify memory governance hard gates per governance guide.
2. Create new files or update existing files.
3. Update the memory index for any new files.
4. Update cross-references and timestamps on modified files.
5. Run memory schema validation to confirm compliance.

#### Phase B — Workspace fixes
For each approved `fix` item:
1. Read the target file to confirm it hasn't changed since DISTILL (guard against mid-session edits).
2. Apply the patch.
3. Post-fix validation: run the appropriate validation for the target file type.
4. If validation fails → revert the patch, note in report.

Mark each item complete in todo list.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| All approved items persisted/patched, validation passes | → REPORT |
| Memory or patch validation fails (max 2 retries) | → REPORT (with skipped items noted) |
| Memory governance hard gate fails | → REPORT (with skipped items noted) |

Checkpoint: record files created/updated/patched.

### REPORT

**Persona:** —
**Memory:** Unload task-specific memory.

**Actions:**
1. Summary in two sections:

   **§ Memory** — what was learned and persisted to `memory/`.
   **§ Fixes** — what was patched in the workspace.

2. List files created/updated/patched with change description.
3. Note contradictions resolved, items rejected, patches reverted.
4. If any fix was reverted due to validation failure, flag it as a **manual follow-up**.
5. Present numbered next-steps.
6. Exit per `_protocol.md` exit contract.

→ DONE.

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| HARVEST | Any (lightweight) |
| DISTILL | (inline constraints) |
| VALIDATE | Any (user-facing) |
| PERSIST | MODEL-BUILDER |
| REPORT | Any |

---

## Error Handling

Per `_protocol.md` error hooks (4-class model).
- Memory validation failure: fix and retry (max 2), then skip item.
- Memory governance hard gate failure: do not create file, report blocker.
- Fix patch validation failure: revert patch, report as manual follow-up.
- Fix target file changed since DISTILL: re-read and re-draft patch (max 1 retry), then skip.
- DISTILL produces nothing after 2 passes: → REPORT with "no extractable knowledge".
- VALIDATE loop limit: max 2 DISTILL↔VALIDATE cycles.

---

## Composition Interface

Learn can be entered as a **child workflow** from other workflows:

| Parent Workflow | Yield Point | Context Passed |
|---|---|---|
| `research.md` | After REPORT (findings worth persisting) | Research findings + source citations |
| `debug.md` | After VERIFY (root cause pattern) | Root cause + fix pattern |
| `cure.md` | After REPORT (design violation patterns) | Recurring violation patterns |

These workflows include "persist findings to memory" as a **numbered next-step** in their REPORT/terminal phase. User opts in; not auto-triggered.

**Fix-yielding convention:** When a parent workflow discovers tool breakage (e.g., `debug.md` finds a skill helper script is broken), it should pass the context with `kind: fix` annotation so HARVEST can fast-track classification.

---

## Fix Examples

Common fix patterns this workflow handles:

| Scenario | Target File | Fix Type |
|----------|------------|----------|
| Config file moved to a new directory | Skill procedure doc | Stale instruction — update path reference |
| Helper script uses an outdated API argument | Skill helper script | Broken code — fix function call |
| Procedure doc references a CLI flag that was renamed | Skill procedure doc | Stale instruction — update flag name |
| New required env var not documented | Skill procedure doc | Missing entry — add env var to prerequisites |
| Config file has wrong default for a property | Workspace config file | Config drift — fix default value |
| Script output path changed | Skill procedure doc | Stale instruction — update output path |

---

## Constraints

- User approval is mandatory at VALIDATE before any memory write or workspace fix.
- Agent-inferred content starts as `status: draft`, `confidence: low` per memory governance rules.
- Memory governance hard gates are non-negotiable — no file created if gates fail.
- No verbose dumps to memory — distilled, atomic, linked facts only.
- `INDEX.md` must be updated for every new memory file.
- HARVEST caps at **5 candidates per kind** (10 total max) per invocation. User can run learn again for additional items.
- Max 1 workflow yield (to `plan.md` for scope or `research.md` for research).
- Max 2 DISTILL↔VALIDATE cycles to prevent churn.
- Fix patches must pass validation before commit. Reverted patches are flagged as manual follow-ups.
- Fixes must **not** introduce new dependencies — only correct existing code/config/docs in place.
