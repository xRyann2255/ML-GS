---
name: KILL_ORPHANS
description: Kill orphaned PowerShell, conhost, Python, and Code processes left behind by VS Code terminals
---

# KILL_ORPHANS — Kill Orphaned Processes

> **Purpose:** Clean up orphaned `powershell.exe`, `conhost.exe`, `python.exe`/`pythonw.exe`, `secexpr.exe`/`perl.exe`, and `Code.exe` processes left behind by VS Code terminals and sessions.

**Out of scope:** Managing services or cleaning up processes on remote machines.

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `KILL_ORPHANS` |
| **Scope** | Kill orphaned PowerShell, conhost, Python, secexpr, and Code processes on the local machine |
| **Inputs** | `--dry-run` (default via the `kill-orphans` task), `--out-file <path>` (sentinel summary file, terminated by `EXIT_CODE=<rc>`) |
| **Tool** | `skills/KILL_ORPHANS/src/cleanup.py` |
| **Outputs** | Console summary of killed processes; mirrored to `--out-file` when supplied (tasks default to `workspace/tmp/kill_orphans_out.txt`) |
| **Auth** | None — local process management only |
| **Authority** | Destructive — kills processes |

---

## When to Use

- VS Code shows many stale terminal instances.
- System memory is bloated by orphaned `conhost.exe`, `powershell.exe`, `python.exe`, `secexpr.exe`, or `Code.exe` processes.
- After a session with heavy terminal use where processes weren't properly cleaned up.
- Leftover Python interpreters from dead terminals or old VS Code extension hosts.
- Stale `secexpr.exe` / `perl.exe` processes from aborted Slang lint, edit, or RegTest runs.

---

## Prerequisites

- Python 3.8+ (auto-detected from H:\venv*).
- Uses `wmic` (Windows built-in) and `ctypes` — no external dependencies.

---

## Quick Start

```bash
# Preview what would be killed (no action taken)
python skills/KILL_ORPHANS/src/cleanup.py --dry-run

# Kill all orphans
python skills/KILL_ORPHANS/src/cleanup.py
```

---

## How It Works

1. **Global parent map:** Queries all process parent relationships via `wmic` for efficiency.
2. **VS Code tree protection:** Identifies all `Code.exe` processes belonging to active VS Code windows (via main window handle) and propagates protection to their child processes. These are never killed.
3. **PowerShell orphans:** Finds all `powershell.exe` processes except the current one and kills them.
4. **Conhost orphans:** Finds `conhost.exe` processes whose parent is dead — kills them while preserving those with a live parent.
5. **Python orphans:** Finds `python.exe`/`pythonw.exe` processes whose parent is dead. Python processes with a live parent (e.g., running in a VS Code terminal) are preserved.
5. **Secexpr orphans:** Finds `secexpr.exe` and `perl.exe` (secexpr's child) processes whose parent is dead. Those with live parents are preserved.
6. **Code.exe orphans:** Kills `Code.exe` processes that are **not** in any active VS Code window tree **and** whose parent is dead.
7. Reports a summary: counts killed, counts preserved, and estimated memory freed.

---

## Safety

- Always preserves the current PowerShell process (the one running the script).
- VS Code child processes are never killed — `Code.exe` processes in the active window tree, and `python.exe`/`conhost.exe` with live parents, are all protected.
- Conhost, Python, secexpr, and perl processes with a live parent are never killed.
- Use `--dry-run` / `-DryRun` to preview before acting.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No orphans found | All processes have live parents | Normal — nothing to clean |
| Wanted process killed | Process matched orphan heuristic | Use `--dry-run` first; add exclusion if needed |

## Task-Based Execution

Preferred — never invoke `cleanup.py` from a raw terminal.

| Task label | Args | Purpose |
|---|---|---|
| `kill-orphans` | `--dry-run --out-file workspace/tmp/kill_orphans_out.txt` | Preview (safe default) |
| `kill-orphans-force` | `--out-file workspace/tmp/kill_orphans_out.txt` | Kill (destructive — only after user confirms dry-run) |

Both tasks route through `_shared/_run.{sh,cmd}` and write a sentinel out-file whose last line is `EXIT_CODE=<rc>`. Read that file to obtain the summary and completion status. The two labels live in `.vscode/tasks.json` (mirrored in `ml-vol-estimator.code-workspace`).

## Links

- memory/ref/devtools.md — devtools environment (process runtime context)
