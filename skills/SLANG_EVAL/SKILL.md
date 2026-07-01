---
name: SLANG_EVAL
description: "Evaluate Slang expressions and run scripts via the VS Code extension's SSP/REPL endpoint. ~100x faster than cold-start secexpr. USE FOR: quick Slang evaluation, data queries, prototyping expressions, running scripts interactively. REQUIRES: VS Code Slang extension with active REPL session."
---

# SLANG_EVAL — Execute Slang via VS Code Extension

> **Purpose:** Evaluate Slang expressions and run named scripts through the VS Code Slang extension's persistent SSP/REPL endpoint. Uses the same JSON-RPC protocol the extension uses internally when you press F9.

**Out of scope:** Script editing, lint, code review, FasTest. Use SLANG_EDIT, SLANG_LINT, SLANG_REVIEW for those. This skill is for **evaluation only**.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_EVAL` |
| **Scope** | Evaluate Slang expressions and run scripts via extension REPL |
| **Inputs** | Expression string, file path, or script name |
| **Outputs** | Evaluation result (text or JSON) to stdout |
| **Authority** | Inherits extension's safety mode (SAFE/FULL toggle in VS Code) |
| **Prerequisite** | VS Code Slang extension running with active REPL |

## When to Use

- **Quick evaluation** of Slang expressions (data lookups, computations, prototyping).
- **Running scripts** interactively without cold-start overhead.
- **Chaining** Slang calls from Python workflows where ~10s secexpr startup per call is too slow.
- Anytime you need a Slang result and the VS Code extension is running.

## When NOT to Use

- **Script edits** — use SLANG_EDIT (writes require secexpr's `UpdateSecurity`).
- **Lint** — use SLANG_LINT (needs isolated secexpr for deterministic output).
- **FasTest / RegTest** — use the extension's built-in FasTest commands.
- **CI / headless automation** — extension is not available; use secexpr directly.

---

## Architecture

```
┌──────────────────┐   JSON-RPC/HTTP    ┌─────────────────────────────┐
│  eval.py         │ ────────────────── │  secexpr (background)       │
│  (this skill)    │  127.0.0.1:<port>  │  _UT Slang Virtual FS       │
│                  │ ◄──────────────────│  (persistent SecDB session) │
└──────────────────┘   JSON response    └─────────────────────────────┘
```

The extension spawns long-lived `secexpr` processes at startup. One of them runs `_UT Slang Virtual Filesystem` and exposes an SSP endpoint on localhost. This skill sends JSON-RPC POST requests to that endpoint — the same way the extension's own REPL panel works.

**Why ~100x faster:** No process spawn, no SecDB init, no DB connection setup. The session is already warm.

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## Quick Start

```powershell
# Evaluate an expression
PYTHON skills/SLANG_EVAL/src/eval.py -e "1 + 1"

# Evaluate from a file
PYTHON skills/SLANG_EVAL/src/eval.py -f workspace/tmp/expr.slang

# Run a named script
PYTHON skills/SLANG_EVAL/src/eval.py -s "_UT Some Script"

# JSON output for piping
PYTHON skills/SLANG_EVAL/src/eval.py --json -e "EnumFromTo(1,5)"

# Quiet mode (result only, no timing)
PYTHON skills/SLANG_EVAL/src/eval.py --quiet -e "Date()"
```

## Arguments

| Argument | Req | Description |
|----------|-----|-------------|
| `-e` / `--expression` | One of -e/-f/-s | Inline Slang expression |
| `-f` / `--file` | One of -e/-f/-s | File containing Slang expression(s) |
| `-s` / `--script` | One of -e/-f/-s | Named script to run |
| `--port` | No | SSP port (default: auto-detect from running secexpr processes) |
| `--timeout` | No | Request timeout in seconds (default: 30) |
| `--json` | No | Output full JSON response `{ok, value/error, elapsed}` |
| `--quiet` | No | Suppress timing/status to stderr, print only the result |

## Port Discovery

By default, the script auto-detects the SSP port by:
1. Finding all running `secexpr` processes
2. Checking their TCP listen sockets on `127.0.0.1`
3. Probing each with a trivial REPL request

If auto-detection fails, pass `--port` explicitly. To find it manually:

```powershell
Get-Process secexpr | ForEach-Object {
    Get-NetTCPConnection -OwningProcess $_.Id -State Listen -EA SilentlyContinue
} | Where-Object { $_.LocalAddress -eq '127.0.0.1' }
```

## Output

- **Normal mode:** Result printed to stdout, timing/status to stderr.
- **`--json` mode:** Full response as JSON to stdout:
  ```json
  {"ok": true, "value": "2", "elapsed": 0.031}
  ```
- **`--quiet` mode:** Only the value to stdout (no stderr output).
- **Errors:** Error message to stderr, exit code 1.

## Session Context

The REPL session inherits the extension's current state:
- **Database:** The ObjDb configured at extension startup (`slang.startUpDb`).
- **Source:** The SourceDatabase set in the extension (visible in status bar).
- **Variables:** Top-level variables assigned in previous REPL evaluations persist within the same session.
- **Links:** Libraries linked in previous evaluations remain loaded.

This means you can build up state across multiple `eval.py` calls:

```powershell
# Call 1: set up
PYTHON skills/SLANG_EVAL/src/eval.py -e 'Link( "_LIB Eq Brazil Fns" )'

# Call 2: use it (library already linked)
PYTHON skills/SLANG_EVAL/src/eval.py -e '@Eq Brazil::Get Trade Count( "GSBR" )'
```

## Comparison with secexpr CLI

| Dimension | SLANG_EVAL (this skill) | secexpr CLI (SLANG_EDIT, etc.) |
|-----------|-------------------------|--------------------------------|
| **Latency** | ~25-50ms per call | ~8-10s per call (cold start) |
| **Session** | Persistent (vars, Links survive) | Stateless per invocation |
| **Safety** | Inherits extension toggle | Explicit `--safe`/`--full` |
| **Writes** | Evaluation only (no UpdateSecurity) | Full CRUD via edit.py |
| **Headless** | Requires VS Code running | Works anywhere |
| **Output** | JSON structure | Raw stdout/stderr |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Could not find SSP endpoint` | Extension not running or no REPL session | Start VS Code, ensure Slang extension is active |
| `Connection refused` | REPL process crashed | Restart VS Code or reload Slang extension |
| `SLANG_ERROR` in result | Slang evaluation error | Check expression syntax; error message from Slang is returned |
| Wrong port detected | Multiple SSP endpoints (REPL + VFS) | Use `--port` to specify the correct one |
| Timeout | Long-running expression | Increase `--timeout` value |
| Stale session state | Extension restarted | Variables from previous session are lost; re-link libraries |

## Importing from Python

The module can be imported directly for programmatic use:

```python
from skills.SLANG_EVAL.src.eval import discover_ssp_port, ssp_evaluate

port = discover_ssp_port()
result = ssp_evaluate(port, 'Date()', timeout=30)
if result["ok"]:
    print(result["value"])   # e.g. "17Apr2026"
else:
    print(result["error"])
```

## Task-Based Execution

**Task label:** `slang-eval` | **Args file:** `workspace/tmp/slang_eval_args.json`

Preferred. Write args JSON, then `run_task("slang-eval")`. CLI args pass through via `%*`.

## Links

- memory/slang/run.md — Slang execution methods and SSP/REPL setup
