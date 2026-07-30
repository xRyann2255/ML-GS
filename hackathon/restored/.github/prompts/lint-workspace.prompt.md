---
description: "Workspace lint and housekeeping — structural checks, schema fixes, cleanup, and safety validation"
argument-hint: "optional: --quick, --cleanup, or check name"
model: Claude Opus 4.6
---

Run the **workspace lint** suite on the ml-vol-estimator repo, **auto-fix** all findings, and report results.

For broader **housekeeping** (schema migrations, dead file cleanup, dependency updates): add `--cleanup` to expand scope beyond lint checks.

- `workflows/housekeep.md`
- `personas/model-builder.md`

## How to invoke

1. Write the args JSON to the fixed path `workspace/tmp/lint_args.json` using a file-edit tool (never terminal). This is the literal `--args-file` value in the `lint-workspace` task definition (`ml-vol-estimator.code-workspace`). The args file path is fixed per task — two concurrent agents writing it race (last writer wins); keep `out_file` unique per run (put a `run_id` slug in its name), the args file itself is not collision-safe.
2. Run the `lint-workspace` task via `run_task`.
3. Read results from the `out_file`.

**Args JSON format (default — fix enabled):**
```json
{ "out_file": "workspace/tmp/lint_out_{run_id}.txt", "fix": true }
```

Optional fields:
- `"quick": true` — skip slow checks
- `"fix": false` — report-only mode (override default)
- `"check": "memory"` — run only `validate_memory.py` instead of the full suite

## What it checks

- `secexpr safety` — no `--full` flags, safe mode enforced
- `hardcoded env` — no hardcoded kerberos, DB paths, Object DB names
- `memory schema` — frontmatter, tags, status, structure compliance
- `skills structure` — SKILL.md presence, required sections
- `forbidden patterns` — banned patterns across repo files
- `skills content` — skill file content validation
- `memory priority` — P0–P3 tier assignments
- `design rules` — structural design-lint checks
- `broken refs` — cross-reference integrity
- `memory index completeness` — all memory files listed in INDEX.md
- `doc safety` — documentation safety checks
- `registry drift` — skill/persona registries match files on disk
- `vscode md compat` — markdown compatibility
- `vscode tasks` — tasks.json validity

## Interpreting results

- **PASS**: all checks green — no action needed.
- **FAIL**: one or more checks failed — read the output, fix violations, re-run lint to confirm.
- If `--fix` was used, review what changed and re-run without `--fix` to verify.

## Rules

- **Never use `run_in_terminal`** for lint. Always `run_task("lint-workspace")`.
- **Never invent an ad-hoc task definition.** Use the predefined `lint-workspace` label only (the ad-hoc-task API was retired 2026-07 as a permission-gate bypass — see `memory/ref/vscode-tasks.md` rule E3).
- Write args JSON with `create_file` or file-edit tools, never PowerShell.
- After fixing violations, always re-run lint to confirm 0 failures.
- Present a numbered summary of remaining issues (if any) and next-steps.
