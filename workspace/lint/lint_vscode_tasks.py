"""Lint: validate VS Code task definitions against the task policy.

Checks ml-vol-estimator.code-workspace task definitions and wrapper .cmd scripts
against the rules in memory/ref/vscode-tasks.md.

Rules checked:
  T1  presentation.close must be true
  T2  presentation.showReuseMessage must be false
  T3  type must be "shell"
  T4  command must use relative backslash paths (no absolute, no forward slash)
  T5  args must use --args-file or --out-file pattern
  T6  label must be lowercase kebab-case
  T7  no duplicate labels
  T8  presentation must include reveal: always, panel: new
  T8b background tasks exempt from T1/T8 panel checks (isBackground: true)
  W1  standard-python wrapper must call all-languages-env.cmd
  W2  standard-python wrapper must have batch venv auto-detect loop
  W3  standard-python wrapper must use %~dp0 for script path
  W4  standard-python wrapper must passthrough args via %*
  W5  standard-python wrapper must have PY error guard
  W6  wrapper .cmd must not hardcode a specific venv (e.g. H:\\venv311)
  B1  bootstrap wrapper must call _run.cmd
  B2  bootstrap wrapper must set _PY_SCRIPT and _SKILL
  P1  inline-ps wrapper must use -NoProfile -ExecutionPolicy Bypass

Usage:
    python workspace/lint/lint_vscode_tasks.py

Exit code: 0 if pass, 1 on violations.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_FILE = REPO_ROOT / "ml-vol-estimator.code-workspace"

RE_KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
RE_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")
RE_HARDCODED_VENV = re.compile(r"H:\\venv\d{2,3}", re.IGNORECASE)


def load_workspace_tasks() -> list[dict]:
    """Load task definitions from ml-vol-estimator.code-workspace."""
    if not WORKSPACE_FILE.is_file():
        return []
    with open(WORKSPACE_FILE, "r", encoding="utf-8") as f:
        ws = json.load(f)
    tasks_block = ws.get("tasks", {})
    return tasks_block.get("tasks", [])


def check_task_definitions(tasks: list[dict]) -> list[str]:
    """Validate task definitions against T1-T8 rules."""
    errors: list[str] = []
    labels_seen: dict[str, int] = {}

    for i, task in enumerate(tasks):
        label = task.get("label", f"<unnamed-{i}>")
        pres = task.get("presentation", {})
        is_bg = task.get("isBackground", False)

        # T3: type must be shell
        if task.get("type") != "shell":
            errors.append(f"T3: task '{label}' type is '{task.get('type')}', expected 'shell'")

        # T6: label must be lowercase kebab-case
        if not RE_KEBAB.match(label):
            errors.append(f"T6: task '{label}' is not lowercase kebab-case")

        # T7: no duplicate labels
        if label in labels_seen:
            errors.append(f"T7: duplicate label '{label}' (tasks {labels_seen[label]} and {i})")
        labels_seen[label] = i

        # T4: command must be relative backslash path (unless a windows override exists,
        # in which case the primary command is the Linux variant with forward slashes)
        cmd = task.get("command", "")
        has_windows_override = "windows" in task
        if RE_ABSOLUTE.match(cmd):
            errors.append(f"T4: task '{label}' command uses absolute path: {cmd}")
        if "/" in cmd and not has_windows_override:
            errors.append(f"T4: task '{label}' command uses forward slashes: {cmd}")

        # T1: presentation.close must be true (background tasks exempt)
        if not is_bg and pres.get("close") is not True:
            errors.append(f"T1: task '{label}' missing presentation.close: true")

        # T2: presentation.showReuseMessage must be false
        if pres.get("showReuseMessage") is not False:
            errors.append(f"T2: task '{label}' missing presentation.showReuseMessage: false")

        # T8: reveal: always, panel: new (background tasks and runOn tasks exempt)
        is_auto = bool(task.get("runOptions", {}).get("runOn"))
        if not is_auto and pres.get("reveal") != "always":
            errors.append(f"T8: task '{label}' missing presentation.reveal: 'always'")
        if not is_bg and not is_auto and pres.get("panel") != "new":
            errors.append(f"T8: task '{label}' missing presentation.panel: 'new'")

        # T5: args must use --args-file or --out-file pattern
        args = task.get("args", [])
        if args and not any(a in ("--args-file", "--out-file") for a in args):
            errors.append(f"T5: task '{label}' args don't use --args-file or --out-file pattern")

    return errors


def check_wrapper_scripts(tasks: list[dict]) -> list[str]:
    """Check wrapper .cmd files against W1-W5, W6, B1-B2, P1 rules by architecture."""
    errors: list[str] = []
    checked: set[str] = set()
    # Build set of background task commands for exemptions
    bg_cmds = {task.get("command", "").replace("\\", "/") for task in tasks if task.get("isBackground")}

    for task in tasks:
        cmd_path = task.get("command", "")
        if not cmd_path.endswith(".cmd"):
            continue
        # Resolve relative to repo root
        full_path = REPO_ROOT / cmd_path.replace("\\", os.sep)
        if not full_path.is_file():
            continue
        rel = cmd_path.replace("\\", "/")
        if rel in checked:
            continue
        checked.add(rel)

        content = full_path.read_text(encoding="utf-8", errors="replace")

        # Classify architecture
        has_bootstrap = "_run.cmd" in content
        has_batch_py = '"%PY%"' in content and "%~dp0" in content
        has_ps = "powershell" in content.lower() and "-noprofile" in content.lower()

        if has_bootstrap:
            arch = "bootstrap"
        elif has_batch_py and not has_ps:
            arch = "standard-python"
        elif has_ps:
            arch = "inline-ps"
        else:
            arch = "unknown"

        # W6: no hardcoded venv (all types)
        matches = RE_HARDCODED_VENV.findall(content)
        if matches:
            errors.append(f"W6: {rel} hardcodes venv: {', '.join(set(matches))}")

        if arch == "standard-python":
            # W1: must source env
            if "all-languages-env.cmd" not in content:
                errors.append(f"W1: {rel} missing call to all-languages-env.cmd")
            # W2: must have batch venv auto-detect loop
            if "for %%V in (" not in content:
                errors.append(f"W2: {rel} missing batch venv auto-detect loop")
            # W3: must use %~dp0 for script path
            if "%~dp0" not in content:
                errors.append(f"W3: {rel} missing %~dp0 script path")
            # W4: must passthrough args via %* (background tasks exempt)
            if "%*" not in content and rel not in bg_cmds:
                errors.append(f"W4: {rel} missing %* args passthrough")
            # W5: must have PY error guard
            if "if not defined PY" not in content:
                errors.append(f"W5: {rel} missing PY error guard")

        elif arch == "bootstrap":
            # B1: must call _run.cmd
            if "_shared\\_run.cmd" not in content and "_shared/_run.cmd" not in content:
                errors.append(f"B1: {rel} calls _run.cmd but path is non-standard")
            # B2: must set _PY_SCRIPT and _SKILL
            if "_PY_SCRIPT" not in content:
                errors.append(f"B2: {rel} missing _PY_SCRIPT variable")
            if "_SKILL" not in content:
                errors.append(f"B2: {rel} missing _SKILL variable")

        elif arch == "inline-ps":
            # P1: must use -NoProfile -ExecutionPolicy Bypass
            if "-ExecutionPolicy Bypass" not in content:
                errors.append(f"P1: {rel} missing -ExecutionPolicy Bypass")

    return errors


def main() -> int:
    tasks = load_workspace_tasks()
    if not tasks:
        print("WARN: No tasks found in ml-vol-estimator.code-workspace")
        return 0

    errors: list[str] = []
    errors.extend(check_task_definitions(tasks))
    errors.extend(check_wrapper_scripts(tasks))

    print(f"Scanned {len(tasks)} task(s) in {WORKSPACE_FILE.name}")

    if errors:
        print(f"FAIL: {len(errors)} violation(s):")
        for e in sorted(errors):
            print(f"  - {e}")
        return 1

    print(f"PASS: all {len(tasks)} tasks comply with VS Code task policy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
