---
name: AI_SLOP_CLEANER
description: "Regression-tests-first, smell-by-smell cleanup of AI-generated code."
---

# AI_SLOP_CLEANER — AI Code Cleanup

> **Purpose:** Reduce AI-generated slop through a regression-tests-first, smell-by-smell cleanup workflow that preserves behavior and raises signal quality.

**Out of scope:** Architectural rewrites; greenfield refactors not tied to existing behavior; deployment or release workflows; cleanup of files outside the provided scope list.

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `AI_SLOP_CLEANER` |
| **Scope** | AI-generated code cleanup, smell-by-smell refactoring, regression-locked editing |
| **Inputs** | Changed-file lists, feature-area scope, existing test suites, user cleanup requests |
| **Outputs** | Cleaned files, regression tests, evidence-dense cleanup reports |
| **Authority** | Read and edit scoped source files; write to `workspace/tmp/`; update `memory/_dormant/ref/slop-smells.md`; does NOT expand scope beyond provided file list without user approval |

---

## When to Use

- User says "ai slop", "slop cleanup", "clean up slop", "smell scan", "dead code cleanup".
- AI-generated code needs quality pass before review/merge.

---

## Procedure

### Phase 0 — Scope Lock

1. Identify the **target file set** — either user-provided or from `get_changed_files`.
2. If more than 10 files, ask the user to narrow scope or confirm batch mode.
3. List target files in the todo list. No file outside this set is touched.

### Phase 1 — Regression Lock

Before any edit, lock existing behavior:

1. **Find existing tests.** Search for test files covering the target modules.
2. **Run existing tests.** If they pass → continue. If they fail → stop and report.
3. **If no tests exist**, write minimal regression tests that capture current I/O behavior.
4. **Run the new regression tests.** All must pass before proceeding.

> **Gate:** Do not proceed to Phase 2 until all regression tests pass.

### Phase 2 — Smell Scan

Read each target file and catalog every smell instance. Produce a **Smell Report** before editing:

```
## Smell Report: <file>

| # | Line(s) | Smell ID | Description | Risk | Auto-fixable |
|---|---------|----------|-------------|------|-------------|
| 1 | 12-18   | DEAD-IMPORT | `import os` unused | low | yes |
| 2 | 34-50   | WRAPPER-CLASS | Class wraps a single function, no state | med | yes |
| 3 | 72      | CARGO-EXCEPT | bare `except Exception: pass` | high | manual |
```

Present the report to the user. Wait for confirmation before fixing (unless user pre-approved batch mode).

### Phase 3 — Fix (smell by smell)

For each approved smell:

1. Apply the minimal fix (prefer deletion over rewrite).
2. Run regression tests after each fix.
3. If tests fail → revert the fix, mark as `[blocked]`, move on.
4. If tests pass → mark as `[fixed]`, commit logical unit.

Order: fix low-risk smells first, escalate to high-risk.

### Phase 4 — Final Verification

1. Run the full regression suite one final time.
2. Run lint / typecheck if applicable.
3. Produce the cleanup report.

---

## Output: Cleanup Report

```
## Cleanup Report: <scope>

**Files scanned:** N
**Smells found:** N (N auto-fixed, N manual, N blocked, N rejected)
**Regression tests:** N passed, N added

### Changes by File
| File | Smells Fixed | Lines Removed | Lines Added | Net |
|------|-------------|---------------|-------------|-----|

### Blocked Smells
| File | Smell | Reason |
|------|-------|--------|

### Remaining Risks
- ...
```

When no smells are found, say so in one line and move on. No ceremonial filler.

---

## Limitations

- Does not expand scope beyond the provided file list without explicit user approval.
- Does not perform architectural rewrites — only localised, behavior-preserving cleanup.
- Cannot verify runtime behavior beyond what regression tests cover.
- Language-specific lint rules (e.g., Slang formatting) defer to the relevant language skill (`SLANG` skill — Cleanup Sub-Skill).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| False positive on idiomatic pattern | Smell rule too broad | Add to false-positive exceptions in `memory/_dormant/ref/slop-smells.md` |
| No smells detected in obviously sloppy file | File not in scan list | Pass file explicitly via `--files` arg |

## Links

- memory/ref/slop-smells.md — full smell ID table, fix guidance, confidence hierarchy, learned patterns, and false-positive exceptions
