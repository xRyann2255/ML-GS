---
created: 2026-04-24
updated: 2026-04-29
tags: [ref, vscode, tasks, policy, lint]
status: active
confidence: high
---

# VS Code Task Policy

Canonical rules for VS Code task definitions and task wrapper scripts.
All tasks run via `run_task` with predefined labels from `ml-vol-estimator.code-workspace`.

## Task Definition Rules (ml-vol-estimator.code-workspace)

| ID | Rule | Rationale |
|----|------|-----------|
| T1 | Every task MUST have `"close": true` in `presentation` | Prevents terminal hang after process exits |
| T2 | Every task MUST have `"showReuseMessage": false` in `presentation` | Suppresses "press any key" noise |
| T3 | Every task MUST have `"type": "shell"` | Consistent execution model |
| T4 | Task `command` MUST use backslash-separated relative paths from workspace root | Portable across machines; no absolute paths |
| T5 | Task `args` MUST use `["--args-file", "workspace\\tmp\\<skill>_args.json"]` pattern | Standardized args flow; exception: `gssso-auth` uses `--out-file` |
| T6 | Task labels MUST be lowercase kebab-case | Consistent naming: `lint-workspace`, `secdb-diff` |
| T7 | No duplicate task labels | Each label must be unique across all task definitions |
| T8 | `presentation` MUST include `"reveal": "always"` and `"panel": "new"` | Prevents stuck terminals from stale terminal reuse. `"shared"` and `"dedicated"` cause `run_task` to return stale output from previous runs |
| T9 | Task wrapper `.cmd` MUST `exit /b 0` unconditionally | VS Code only honors `close: true` on exit code 0. Non-zero exit leaves terminal open for inspection, causing terminal accumulation. Success/failure is communicated via `out_file` content, not exit code |

## Wrapper Script Rules (_task.cmd files)

### Python-based wrappers (standard pattern)

| ID | Rule | Rationale |
|----|------|-----------|
| W1 | First executable line: `call H:\all-languages-env.cmd >nul 2>&1` | Ensures PATH includes all GS tools |
| W2 | Python auto-detect via descending venv loop (315→38) | Survives Python upgrades without edits |
| W3 | Script path via `%~dp0<script>.py` | CWD-independent; works from any directory |
| W4 | Args passthrough via `%*` | Clean forwarding; no arg re-parsing in .cmd |
| W5 | Error guard: `if not defined PY ... exit /b 1` | Fails fast with clear message |
| W6 | NEVER hardcode a specific venv (e.g. `H:\venv311`) | Breaks on Python upgrade |

### Standard Python wrapper template

```bat
@echo off
REM Wrapper for <script>.py. Sets up env and auto-detects Python.
REM Usage: <name>_task.cmd --args-file path\to\args.json
call H:\all-languages-env.cmd >nul 2>&1
set "PY="
for %%V in (315 314 313 312 311 310 39 38) do (
    if not defined PY if exist "H:\venv%%V\Scripts\python.exe" set "PY=H:\venv%%V\Scripts\python.exe"
)
if not defined PY (
    echo ERROR: No Python venv found in H:\venv*
    exit /b 1
)
"%PY%" "%~dp0<script>.py" %*
```

### PowerShell-based wrappers

For scripts that need inline PS (GIT, GITLAB_SEARCH, GSSSO_AUTH) or dispatch to
multiple Python scripts with JSON→arg mapping (SEARCH, workspace lint):

| ID | Rule | Rationale |
|----|------|-----------|
| P1 | Use `powershell -NoProfile -ExecutionPolicy Bypass` | Fast startup, no profile interference |
| P2 | Parse `--args-file` JSON via `ConvertFrom-Json` | Native JSON support in PS |
| P3 | Write output to `out_file` from args JSON when specified | Enables `read_file` consumption |
| P4 | Use venv auto-detect loop in PS, NEVER hardcode `H:\venv311` | Same resilience as W2/W6 |

### PS venv auto-detect snippet

```powershell
$PY = $null; foreach ($v in 315,314,313,312,311,310,39,38) {
  $p = \"H:\\venv$v\\Scripts\\python.exe\";
  if (Test-Path $p) { $PY = $p; break }
};
if (-not $PY) { Write-Error 'No Python venv found'; exit 1 };
```

## Python Script --args-file Contract

| ID | Rule | Rationale |
|----|------|-----------|
| A1 | Every task Python script MUST accept `--args-file PATH` | Enables the `create_file → run_task → read_file` workflow |
| A2 | `--args-file` loads a JSON file that mirrors CLI flags | Consistent across all skills |
| A3 | If `out_file` key is present in args JSON, write output there | Enables `read_file` consumption without terminal scraping |
| A4 | CLI flags MUST still work without `--args-file` | Backward compat for direct invocation |

## Agent Execution Rules

| ID | Rule | Rationale |
|----|------|-----------|
| E1 | ALWAYS use `run_task` with predefined label | Avoids Allow prompts; uses `close: true` |
| E2 | NEVER use `run_in_terminal` for tasks with a predefined wrapper | Triggers Allow prompt |
| E3 | Use `create_and_run_task` when `run_task` can't find predefined tasks | Fallback for multi-workspace `.code-workspace` task definitions |
| E4 | Write args JSON via `create_file` or `replace_string_in_file` | Avoid PowerShell terminal for JSON writing |
| E5 | Read output from `out_file`, not terminal buffer | Terminal auto-closes (`close: true`) |
| E6 | "Task started but no terminal was found" is NORMAL | `close: true` dismisses terminal; read `out_file` |
| E7 | `run_task` **BLOCKS** until the task process exits | No polling needed; output file is ready when `run_task` returns |
| E8 | NEVER use `get_task_output` | Returns same data as `run_task`; adds nothing, wastes a tool call |
| E9 | For tasks without `out_file`, read auto-generated JSON from `workspace/tmp/` | See output file lookup table in `/memories/repo/task-execution.md` |
| E10 | `run_task` id = the bare `label` from `ml-vol-estimator.code-workspace` (e.g. `git`, `gitlab-mr`). **NEVER** prefix with `shell: ` | VS Code context shows `shell: <label>` but `run_task` needs bare label. Using `shell: git` → `Task not found` |

## Common Args JSON Pitfalls

| Pitfall | Wrong | Correct | Affected Task |
|---------|-------|---------|---------------|
| Inventing a `command` field for git | `{"command": "log", "args": ["--oneline"]}` | `{"args": ["log", "--oneline"]}` | `git` |
| Forgetting `out_file` (output lost) | `{"args": ["status"]}` | `{"args": ["status"], "out_file": "workspace/tmp/git_out.txt"}` | All tasks with optional `out_file` |

## Concurrency Rules (Multi-Window)

Multiple VS Code windows may share the same workspace. To prevent file collisions:

| ID | Rule | Rationale |
|----|------|-----------|
| C1 | Include `run_id` in args filename: `slang_lint_args_{run_id}.json` | Prevents concurrent windows from overwriting each other's args |
| C2 | Include `run_id` in args JSON body | Scripts auto-derive unique results filenames: `slang_lint_results_{run_id}.json` |
| C3 | Read results from `slang_lint_results_{run_id}.json` or `slang_review_results_{run_id}.json` | Matches the auto-derived filename |
| C4 | Generate `run_id` as a short descriptive slug | e.g. `smm-metrics-20260429`, `boxes-lint-20260429` |
