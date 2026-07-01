---
created: 2026-03-01
updated: 2026-05-19
tags: [setup, devtools, environment, tooling]
status: active
relates:
  - ref/python-setup.md
---

# devtools — GS Developer Tooling

GS-wide CLI for installing dev tools to `H:\` drive. Each tool gets `H:\<tool>\` (binaries) and `H:\<tool>-env.cmd` (env script).

## Commands

```bash
devtools ls <tool>        # Check if installed / list versions
devtools install <tool>   # Install (latest default) — slow, check ls first
```

## Environment

- **Linux (Coder workspace)**: Tools installed via nix (`nix-env -iA nixpkgs.<tool>`). No `H:\` drive, no env scripts needed. `uv`, `python3`, `node` are on PATH directly.
- **Windows**: NOT on PATH. Wrap every call: `cmd /c "H:\<tool>-env.cmd && <command>"`
  - `H:\all-languages-env.cmd` chains all env scripts
  - `H:\profile.ps1` defines `Set-MyEnv` (imports all into PowerShell)

## Quick Patterns

```powershell
# Windows
cmd /c "H:\uv-env.cmd && uv run python script.py"
cmd /c "H:\javascript-env.cmd && npm install"
Set-MyEnv   # if H:\profile.ps1 is loaded

# Linux
uv run python script.py
./vol test
```
