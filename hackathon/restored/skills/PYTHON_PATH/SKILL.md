---
name: PYTHON_PATH
description: Resolve the Python interpreter path from user config with auto-detection fallback
---

# PYTHON_PATH — Resolve Python Interpreter

> **Purpose:** Centralized resolution of the Python executable path. All skills that invoke Python use this skill instead of hardcoding paths or repeating resolution logic.

**Out of scope:** Installing Python, managing virtual environments, or running Python code. See `memory/ref/python-setup.md` for environment setup and uv configuration.

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `PYTHON_PATH` |
| **Scope** | Resolve a valid `python.exe` path for skill script execution |
| **Inputs** | None |
| **Tool** | `skills/PYTHON_PATH/src/resolve.ps1` |
| **Outputs** | Absolute path to `python.exe` (stdout) |
| **Auth** | None — local file read only |
| **Authority** | Read-only (writes only to `workspace/config/user.json` on auto-fix) |

---

## When to Use

- **Before every Python skill invocation.** Any skill that runs a `*.py` script must resolve the interpreter through this skill first.
- **After a Python execution fails with "not recognized" or "not found".** Run `resolve.ps1` to auto-detect and update `user.json`.

---

## Resolution Order

1. Read `workspace/config/user.json` → `python_path` field.
2. If missing or file doesn't exist → fall back to `H:\venv311\Scripts\python.exe`.
3. Validate the path exists on disk.
4. If invalid → scan `H:\venv*\Scripts\python.exe`, pick highest version, update `user.json`.

---

## Procedures

### Resolve Python path (inline — preferred)

When constructing a Python command, resolve the path first:

```powershell
$py = & skills/PYTHON_PATH/src/resolve.ps1
& $py skills/SOME_SKILL/src/script.py --arg value
```

### Resolve and run in one line

```powershell
& (& skills/PYTHON_PATH/src/resolve.ps1) skills/SOME_SKILL/src/script.py --arg value
```

### Recovery after failure

If a Python command fails with a path error, run the resolver to auto-detect and update config:

```powershell
# This scans H:\venv* and updates user.json automatically
& skills/PYTHON_PATH/src/resolve.ps1
```

Then retry the original command.

---

## Agent Instructions

When you need to run any Python skill script:

1. Read `workspace/config/user.json` → use the `python_path` value.
2. If the file is missing or has no `python_path`, use `H:\venv311\Scripts\python.exe`.
3. If execution fails with "not recognized", "not found", or exit code 9009:
   - Run `skills/PYTHON_PATH/src/resolve.ps1` — it will scan, fix `user.json`, and output the correct path.
   - Retry with the new path.
4. **Never hardcode a Python path in commands.** Always resolve first.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `python` not recognized | Not on PATH, no `user.json` | Run `resolve.ps1` to auto-detect and update config |
| Wrong Python version resolved | Multiple venvs on disk | Check `user.json` and update `python_path` manually |

## Links

- memory/ref/python-setup.md — Python environment setup and uv configuration

