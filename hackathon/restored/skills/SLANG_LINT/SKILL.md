---
name: SLANG_LINT
description: Run native Slang lint via Python wrapper over secexpr
---

# SLANG_LINT — Run Native Lint via Python

> **Purpose:** Run native Slang lint (`@LIBSlang::Lint`) or precommit lint (`@ScriptVal::PreCommit Check Lint`) through a Python wrapper over `secexpr --safe`.

**Out of scope:** Fixing lint errors, editing scripts, or running RegTests.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_LINT` |
| **Scope** | Run native Slang lint and report results |
| **Inputs** | Script name(s), DB path, optional --precommit flag |
| **Outputs** | Lint results (Status 1/2/3/3.75) to stdout |
| **Authority** | Read-only (secexpr --safe) |

## When to Use

- After any edit to a Slang script (mandatory lint gate).
- To validate scripts before code review submission.
- To check for type, return, and resolution issues.

---

Run native Slang lint via Python wrapper around `secexpr --safe`.

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## Quick Start

```cmd
# Default lint (@LIBSlang::Lint)
PYTHON skills/SLANG_LINT/src/lint.py ^
    --db "~{kerberos}!clean" --scripts "_LIB Foo"

# Multiple scripts
--scripts "_LIB Foo" "Test: Foo" "_TYPE Foo"

# Precommit (full ScriptVal pipeline — slower, matches ScriptReview)
--scripts "Test: Foo" --precommit

# Custom source chain
--scripts "_LIB Foo" --source "!NYC_EqVol_Source;PS"
```

## Arguments

| Argument | Req | Description |
| --- | --- | --- |
| `--db` | Yes | SecDB database path |
| `--scripts` | Yes | One or more script names |
| `--precommit` | No | Use `@ScriptVal::PreCommit Check Lint` instead |
| `--source` | No | secexpr `--source` override (default: `PS`) |
| `--timeout` | No | secexpr timeout in seconds (default: 300) |
| `--output-json` | No | Write JSON results to PATH (default: `workspace/tmp/slang_lint_results.json`) |

## Backends

- **`@LIBSlang::Lint`** (default): Fast. Type mismatches, return violations, collisions, unused vars.
- **`@ScriptVal::PreCommit Check Lint`** (`--precommit`): Full pipeline (same as ScriptReview). Also catches unused `Link()`, unused args. Slower.

Both run via `secexpr --safe` (read-only).

## Parallel Execution

2+ scripts with default backend → distributed across up to **4 parallel queues** (one secexpr per queue, round-robin). `--precommit` always single process.

## Interpreting Results

| Status | Severity | Action |
| --- | --- | --- |
| 1 | Error | Must fix |
| 2 | Warning | Must fix |
| 3 | Info | No action |
| 3.75 | OK | Script metrics — no action |

**Gate:** Fix all Status-1 and Status-2 before declaring done. Status-3+ are informational.

## Common Fixes

| Issue | Fix |
| --- | --- |
| `Function must not return a value` | Add proper return type |
| `uses return value of X, which returns nothing` | Fix return type of called function |
| `Possible typo - unregistered vt X` | Replace with method call, or add `LintPragma` |
| `SomeConst apparently used without definition` | Missing `Link()` — add the constant's script |
| `Links "_LIB X" but uses no functions` | Remove unused `Link()` |
| `Argument "X" apparently unused` | Remove or add `LintPragma("Ignore apparently unused X")` |

Exit code: 0 = PASS, 1 = FAIL. Logs: `workspace/tmp/slang_lint_logs/`

## Task-Based Execution (Zero Allow — Preferred)

Use `run_task("lint-slang")` instead of `run_in_terminal` to avoid the Copilot "Allow" prompt. **The entire workflow uses zero terminal calls.**

### Concurrency-Safe Workflow

Multiple VS Code windows may run lint concurrently on the same workspace. The args file
path is fixed per task — two concurrent agents writing it race (last writer wins). Result
files stay collision-free because lint.py derives `slang_lint_results_{run_id}.json` from
the `run_id` field inside the JSON body (`lint.py` writes it via
`slang_lint_results_{run_id}.json`).

1. **Write args file** to the fixed path `workspace/tmp/slang_lint_args.json` (this is the literal `--args-file` value in the `lint-slang` task definition — see `ml-vol-estimator.code-workspace`). Include `run_id` (pattern `[a-z0-9-]+`) inside the body — the script uses it to derive a unique results filename. Use `create_file` (no terminal):

```json
// workspace/tmp/slang_lint_args.json
{
  "db": "~{kerberos}!{sub_db}",
  "scripts": ["_LIB Foo", "Test: Foo"],
  "run_id": "smm-metrics-20260429"
}
```

Generate `run_id` as a short descriptive slug matching `[a-z0-9-]+` (e.g. `smm-metrics-20260429`).
The script auto-derives the results filename as `slang_lint_results_{run_id}.json`.

2. **Launch via the predefined task**:

```
run_task("lint-slang")
```

The task reads `workspace/tmp/slang_lint_args.json` (fixed path in the task definition).

3. **Read results** from `workspace/tmp/slang_lint_results_{run_id}.json`:
   - On launch, lint.py writes `{"status": "running", "run_id": "..."}`.
   - On completion, lint.py overwrites with `{"status": "done", "run_id": "...", "gate": "...", ...}`.
   - `run_task` blocks until done — no polling needed.

```json
{
  "status": "done",
  "run_id": "<unique-id>",
  "gate": "PASS",
  "status_1": 0,
  "status_2": 0,
  "total": 3,
  "issues": [{"script": "_LIB Foo", "status": 3.0, "text": "..."}]
}
```

4. **Evaluate gate**: `gate == "PASS"` → done. `gate == "FAIL"` → fix Status-1/2 issues.

### CRITICAL: No `run_in_terminal` anywhere

| Step | Tool | Allow? |
|---|---|---|
| Write args JSON | `create_file` | No |
| Launch task | `run_task` | No |
| Poll results | `read_file` | No |
| Read results | `read_file` | No |

Do NOT use `run_in_terminal` to delete old results, poll, or check — all of those trigger Allow prompts.

### Args File Keys

| Key | Type | Description |
|---|---|---|
| `db` | string | SecDB database path (e.g. `~jdoe!commit`) |
| `scripts` | string[] | Script names to lint |
| `run_id` | string | Slug (`[a-z0-9-]+`); lives inside the JSON body; used to derive the unique results filename `slang_lint_results_{run_id}.json`. |
| `precommit` | bool | Use precommit lint (optional) |
| `source` | string | Source chain override (optional) |
| `timeout` | int | Timeout in seconds (optional) |
| `output_json` | string | Custom output path (optional) |

### Notes

- `lint_task.cmd` is a thin wrapper that sets up env and calls `lint.py`.
- The Python path in `lint_task.cmd` may need updating if the venv changes — check PYTHON_PATH skill.
- JSON is always written to `workspace/tmp/slang_lint_results.json` by default.
- The task terminal output is visible in VS Code's Task Output panel.
- Parallel execution (multiple queues) works identically in task mode.
- ProdSource scripts: add `"source": "!NYC_Source;PS"` to the args file.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Lint hangs | secexpr process stuck | Kill orphan secexpr processes; retry |
| Status-1 on valid code | Missing `Link()` for referenced library | Add the missing `Link()` statement |
| Lint output empty | Script load error | Check `--db` path and script name spelling |

## Links

- memory/slang/lint-edit.md — lint patterns and edit workflows
