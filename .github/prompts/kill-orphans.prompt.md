---
description: "Kill orphaned PowerShell, conhost, Python, and Code processes left behind by VS Code"
model: Claude Opus 4.6
---

Kill orphaned `powershell.exe`, `conhost.exe`, `python.exe`/`pythonw.exe`, `secexpr.exe`/`perl.exe`, and `Code.exe` processes to free memory and reduce process clutter. VS Code child processes are protected.

- `skills/KILL_ORPHANS/SKILL.md`

## Execution

1. **Always preview first** — run with `-DryRun` so the user sees what would be killed before acting:

```powershell
& "skills/KILL_ORPHANS/src/cleanup.ps1" -DryRun
```

2. **If dry-run looks reasonable**, proceed to kill:

```powershell
& "skills/KILL_ORPHANS/src/cleanup.ps1"
```

3. **Report the summary**: processes killed, processes preserved, estimated memory freed.

## When to invoke automatically

- Before heavy terminal work (lint, FasTest, review) if the system feels sluggish.
- When `Get-Process powershell | Measure-Object` shows an unusually high count.
- When orphaned `python.exe` or `Code.exe` processes are consuming memory.
- User says "clean up", "kill orphans", "free memory", or similar.
