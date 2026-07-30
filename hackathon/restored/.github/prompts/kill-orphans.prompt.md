---
description: "Kill orphaned PowerShell, conhost, Python, and Code processes left behind by VS Code"
model: Claude Opus 4.6
---

Kill orphaned `powershell.exe`, `conhost.exe`, `python.exe`/`pythonw.exe`, `secexpr.exe`/`perl.exe`, and `Code.exe` processes to free memory and reduce process clutter. VS Code child processes are protected.

- `skills/KILL_ORPHANS/SKILL.md`

## Execution

**Never invoke `cleanup.py` from a raw terminal.** Route through the tracked VS Code tasks so the sentinel out-file is written and the destructive step is gated on explicit user confirmation.

1. **Always dry-run first.** The `kill-orphans` task is preconfigured with `--dry-run --out-file workspace/tmp/kill_orphans_out.txt`:

    ```
    run_task("kill-orphans")
    ```

    Then read `workspace/tmp/kill_orphans_out.txt`; the final line is `EXIT_CODE=0`.

2. **Show the summary to the user and STOP.** Do not proceed without an explicit "yes, kill them" (or equivalent) confirmation. The kill step is destructive.

3. **Only on explicit confirmation, run the sibling task:**

    ```
    run_task("kill-orphans-force")
    ```

    This is the same script without `--dry-run`; it writes the post-kill summary to the same out-file.

4. **Report the summary**: processes killed, processes preserved, estimated memory freed.

Both task labels live in `.vscode/tasks.json` (and its mirror in `ml-vol-estimator.code-workspace`).

## When to invoke automatically

- Before heavy terminal work (lint, FasTest, review) if the system feels sluggish.
- When `Get-Process powershell | Measure-Object` shows an unusually high count.
- When orphaned `python.exe` or `Code.exe` processes are consuming memory.
- User says "clean up", "kill orphans", "free memory", or similar.

Even for automatic invocation, the dry-run → confirm → force sequence is mandatory.
