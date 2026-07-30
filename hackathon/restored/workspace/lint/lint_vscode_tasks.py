"""Lint: validate VS Code task definitions against the task policy.

Checks .vscode/tasks.json (primary; Plan 03, AW-G10) and ml-vol-estimator.code-workspace
task definitions and wrapper .cmd scripts against the rules in memory/ref/vscode-tasks.md.

Rules checked:
  T1  presentation.close must be true
  T2  presentation.showReuseMessage must be false
  T3  type must be "shell"
  T4  command must use relative backslash paths (no absolute, no forward slash)
  T5  args must use --args-file or --out-file pattern
        (T5 exemption: tasks whose command is in T5_CLI_COMMANDS = {'./vol', 'vol.cmd'}
         are CLI passthrough tasks — they carry subcommand args by design and skip T5)
  T6  label must be lowercase kebab-case
  T7  no duplicate labels
  T8  presentation must include reveal: always, panel: new
  T8b background tasks exempt from T1/T8 panel checks (isBackground: true)
  V1  .vscode/tasks.json and the ml-vol-estimator.code-workspace tasks array must be identical
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
TASKS_JSON = REPO_ROOT / ".vscode" / "tasks.json"

RE_KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
RE_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")
RE_HARDCODED_VENV = re.compile(r"H:\\venv\d{2,3}", re.IGNORECASE)

# T5 exemption: CLI passthrough tasks (subcommand args are the payload, not an args-file path).
T5_CLI_COMMANDS = {"./vol", "vol.cmd"}


def load_workspace_tasks() -> list[dict]:
    """Load task definitions from ml-vol-estimator.code-workspace."""
    if not WORKSPACE_FILE.is_file():
        return []
    with open(WORKSPACE_FILE, "r", encoding="utf-8") as f:
        ws = json.load(f)
    tasks_block = ws.get("tasks", {})
    return tasks_block.get("tasks", [])


def load_tasks_json() -> list[dict]:
    """Primary task source: tracked .vscode/tasks.json (Plan 03, AW-G10)."""
    if not TASKS_JSON.is_file():
        return []
    with open(TASKS_JSON, "r", encoding="utf-8") as f:
        return json.load(f).get("tasks", [])


def check_divergence(primary: list[dict], mirror: list[dict]) -> list[str]:
    """V1: .vscode/tasks.json and the .code-workspace tasks array must be identical."""
    errors: list[str] = []
    p = {t.get("label"): t for t in primary}
    m = {t.get("label"): t for t in mirror}
    for label in sorted(set(p) | set(m)):
        if label not in p:
            errors.append(f"V1: task '{label}' only in ml-vol-estimator.code-workspace (add to .vscode/tasks.json)")
        elif label not in m:
            errors.append(f"V1: task '{label}' only in .vscode/tasks.json (mirror into ml-vol-estimator.code-workspace)")
        elif p[label] != m[label]:
            errors.append(f"V1: task '{label}' diverges between .vscode/tasks.json and the .code-workspace copy")
    return errors


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
        # T5 exemption: CLI passthrough tasks (./vol, vol.cmd) carry subcommand args by design.
        args = task.get("args", [])
        if args and cmd not in T5_CLI_COMMANDS and not any(a in ("--args-file", "--out-file") for a in args):
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


# ── wfo-04-11: rule T9 (AW-41 regression guard) ──────────────────────────
_T9_CMD_EXIT0 = re.compile(r"^\s*exit\s*/b\s*0\s*$", re.IGNORECASE | re.MULTILINE)
_T9_SH_EXIT0 = re.compile(r"^\s*exit\s+0\s*$", re.MULTILINE)


def check_t9_exit_propagation(repo_root: Path) -> list[str]:
    """T9: no wrapper ends in an unconditional exit-0 that swallows _EC/rc.

    Sanctioned patterns (any one is enough to clear a given exit-0 site):
      1. AW-41 out_file sentinel: wrapper writes 'EXIT_CODE=' to the args-file
         out_file — status communicated via a documented side channel.
      2. Wrapper captures the exit code via `set _EC=%ERRORLEVEL%` /
         `_EC=$?` and writes the payload's out_file itself — the deliberate
         'always exit 0 so VS Code close:true fires' pattern.
      3. Wrapper writes any out_file/OUT_FILE payload — success/failure is
         communicated by the out_file content (empty = failure) per the
         VS Code close:true / side-channel contract.
      4. Defensive-error-bail: wrapper printed an ERROR: message to stderr
         (`>&2`) immediately above the exit-0 — the caller detects failure by
         inspecting stderr or the (empty) out_file.
    Semantics: check every exit-0 occurrence in every wrapper. The preceding
    context extends up to 500 chars back BUT is bounded at the previous
    exit-0's line-end. This ensures each exit-0 must carry its own sanctioning
    context and cannot borrow markers from a compliant sibling — so an
    appended dangling exit-0 (a "swallow" regression) is caught even when the
    file already has a compliant terminating exit above it.
    """
    errors: list[str] = []
    roots = [repo_root / "skills", repo_root / "workspace" / "lint"]
    cmd_markers = ("EXIT_CODE=", "%_EC%", "_EC=", "OUT_FILE", "out_file",
                   ">&2", "ERROR:")
    sh_markers = ("EXIT_CODE=", "$_EC", "_EC=", "$rc", "OUT_FILE", "out_file",
                  ">&2", "ERROR:")

    def _scan(wrappers: list[Path], regex: re.Pattern, markers: tuple[str, ...],
              exit_form: str) -> None:
        for w in wrappers:
            text = w.read_text(encoding="utf-8", errors="replace")
            matches = list(regex.finditer(text))
            for i, m in enumerate(matches):
                prev_line_end = (text.find("\n", matches[i - 1].start()) + 1
                                 if i > 0 else 0)
                start = max(m.start() - 500, prev_line_end)
                preceding = text[start:m.start()]
                if any(mk in preceding for mk in markers):
                    continue
                line = text[:m.start()].count("\n") + 1
                errors.append(
                    f"T9: {w.relative_to(repo_root).as_posix()}:{line}: "
                    f"unconditional '{exit_form}' swallows the exit code "
                    f"— capture _EC / write EXIT_CODE= sentinel / write "
                    f"out_file / print ERROR: to stderr (AW-41, Plan 03)")

    for root in roots:
        if not root.is_dir():
            continue
        _scan(sorted(root.rglob("_run.cmd")) + sorted(root.rglob("*_task.cmd")),
              _T9_CMD_EXIT0, cmd_markers, "exit /b 0")
        _scan(sorted(root.rglob("_run.sh")) + sorted(root.rglob("*_task.sh")),
              _T9_SH_EXIT0, sh_markers, "exit 0")
    return errors


def main() -> int:
    primary = load_tasks_json()
    mirror = load_workspace_tasks()
    tasks = primary or mirror
    if not tasks:
        print("WARN: No tasks found in .vscode/tasks.json or ml-vol-estimator.code-workspace")
        return 0

    errors: list[str] = []
    errors.extend(check_task_definitions(tasks))
    errors.extend(check_wrapper_scripts(tasks))
    errors.extend(check_t9_exit_propagation(REPO_ROOT))
    if primary and mirror:
        errors.extend(check_divergence(primary, mirror))

    source = TASKS_JSON.name if primary else WORKSPACE_FILE.name
    print(f"Scanned {len(tasks)} task(s) in {source}")

    if errors:
        print(f"FAIL: {len(errors)} violation(s):")
        for e in sorted(errors):
            print(f"  - {e}")
        return 1

    print(f"PASS: all {len(tasks)} tasks comply with VS Code task policy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
