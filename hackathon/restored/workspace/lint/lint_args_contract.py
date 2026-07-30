"""
lint_args_contract.py — Enforce the fixed args-file contract (Plan 03 / AW-04).

Rules:
  A1. Every --args-file value in .vscode/tasks.json and the .code-workspace
      tasks array matches ^workspace/tmp/[a-z0-9_-]+_args\\.json$.
  A2. No templated args filenames ({run_id}, {name}, $RUN_ID …) anywhere in
      skills/**/SKILL.md, .github/prompts/*.prompt.md, memory/ref/vscode-tasks.md.
  A3. create_and_run_task is retired — zero mentions in the same scan set.
  A4. Every workspace/tmp/*_args.json path documented in a SKILL.md must also
      appear in a task definition (no phantom contracts).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARGS_FIXED = re.compile(r"^workspace/tmp/[a-z0-9_-]+_args\.json$")
ARGS_ANY = re.compile(r"workspace/tmp/[^\s`\"')\]]*_args\.json")
TEMPLATED = re.compile(r"workspace/tmp/[^\s`\"')\]]*[{$][^\s`\"')\]]*_args\.json")
DOC_SCAN = ["memory/ref/vscode-tasks.md"]


def task_args_values() -> list[tuple[str, str]]:
    """(source, value) for every --args-file in task definitions."""
    out: list[tuple[str, str]] = []
    for rel in [".vscode/tasks.json"] + [
        p.name for p in REPO_ROOT.glob("*.code-workspace")
    ]:
        p = REPO_ROOT / rel
        if not p.is_file():
            continue
        # tolerate comments in VS Code JSON
        text = re.sub(r"^\s*//.*$", "", p.read_text(encoding="utf-8", errors="replace"),
                      flags=re.MULTILINE)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            out.append((rel, "__UNPARSEABLE__"))
            continue
        tasks = data.get("tasks", {})
        task_list = tasks.get("tasks", tasks) if isinstance(tasks, dict) else tasks
        for t in task_list if isinstance(task_list, list) else []:
            args = t.get("args", [])
            for i, a in enumerate(args):
                if a == "--args-file" and i + 1 < len(args):
                    out.append((f"{rel}#{t.get('label', '?')}", args[i + 1]))
    return out


def doc_files() -> list[Path]:
    files = [REPO_ROOT / d for d in DOC_SCAN if (REPO_ROOT / d).is_file()]
    files += sorted((REPO_ROOT / "skills").rglob("SKILL.md"))
    files += sorted((REPO_ROOT / ".github" / "prompts").glob("*.prompt.md"))
    return files


def main() -> int:
    errors: list[str] = []
    task_vals = task_args_values()
    for src, val in task_vals:
        if val == "__UNPARSEABLE__":
            errors.append(f"[args-parse] {src}: tasks JSON unparseable")
        elif not ARGS_FIXED.match(val.replace("\\", "/")):
            errors.append(f"[args-fixed] {src}: '{val}' violates the fixed-path "
                          f"contract workspace/tmp/<task-name>_args.json")
    task_set = {v.replace("\\", "/") for _, v in task_vals}
    for f in doc_files():
        rel = f.relative_to(REPO_ROOT).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in TEMPLATED.finditer(text):
            errors.append(f"[args-template] {rel}: templated args filename "
                          f"'{m.group(0)}' — run_id belongs INSIDE the JSON body")
        if "create_and_run_task" in text:
            errors.append(f"[retired-tool] {rel}: create_and_run_task is retired "
                          f"(Plan 03 / AW-09) — use run_task with the fixed args file")
        if rel.startswith("skills/") and rel.endswith("SKILL.md"):
            for m in ARGS_ANY.finditer(text):
                val = m.group(0)
                if ARGS_FIXED.match(val) and val not in task_set and task_set:
                    errors.append(f"[args-phantom] {rel}: documents '{val}' but no "
                                  f"task definition uses it")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {len(task_vals)} task args-file values and "
          f"{len(doc_files())} docs honor the fixed args contract.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
