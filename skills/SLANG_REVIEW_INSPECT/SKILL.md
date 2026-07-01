---
name: SLANG_REVIEW_INSPECT
description: Read-only validator for ScriptReview objects
---

# SLANG_REVIEW_INSPECT — Inspect ScriptReview Objects

> **Purpose:** Load and validate ScriptReview details including version, scripts, CVS revisions, and web-derived checks (shame, missing testing headers).

**Out of scope:** Creating or modifying reviews, approving changes, or editing scripts.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_REVIEW_INSPECT` |
| **Scope** | Read-only ScriptReview inspection and validation |
| **Inputs** | Review name, DB path, source DBs |
| **Outputs** | Review metadata, script list, CVS revision info |
| **Authority** | Read-only (secexpr --safe) |

## When to Use

- Verify a ScriptReview was created correctly.
- Check delta shame is zero before declaring review done.
- Inspect which scripts and CVS revisions are in a review.

---

Load and print ScriptReview details (version, scripts, CVS revisions) for validation.

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## Usage

```powershell
PYTHON skills/SLANG_REVIEW_INSPECT/src/inspect.py ^
    --db "~{kerberos}!clean" ^
    --review "Review 20260406 6010-2216107S*" ^
    --source "~{kerberos}!clean;!NYC_EqVol_Source;PS"
```

## Output Markers

- `INSPECT_LOAD_FAILED=0|1` — load success/failure
- `REVIEW_CONTAINER=<Review ...>`, `LATEST_VERSION=<n>`, `NUM_SCRIPTS=<n>`
- `SCRIPT=<name>` (one per line), `SCRIPT_CVS_REV=<name>\t<rev>`
- `HAS_TEST_SCRIPT=0|1` — review contains a RegTest (header + name heuristic)
- `WEB_SHAME_MAX=<n|?>`, `WEB_SHAME_INCREASED=0|1` — shame detection
- `WEB_NO_TEST_IN_HEADER_COUNT=<n>`, `WEB_NO_TEST_IN_HEADER=<text>` — missing test headers
- `WEB_PROBLEM=0|1|?` — combined flag (shame increased or test header issues)

Use `--no-web-check` to skip web page fetch. Artifacts: `workspace/tmp/slang_review_inspect_logs/`

## Notes

- Read-only (no SecDB writes). `--source` optional but often needed for library resolution.
- On load failure: prints `INSPECT_LOAD_FAILED=1`, keeps output parseable.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `INSPECT_LOAD_FAILED=1` | Script not found or load error | Verify review name and `--source` DB path |
| Missing CVS diff | Script not under version control | Ensure script is CVSed before review |

## Task-Based Execution

**Task label:** `slang-review-inspect` | **Args file:** `workspace/tmp/review_inspect_args.json`

Preferred. Write args JSON, then `run_task("slang-review-inspect")`. CLI args pass through via `%*`.

## Links

- memory/slang/review.md — ScriptReview conventions
