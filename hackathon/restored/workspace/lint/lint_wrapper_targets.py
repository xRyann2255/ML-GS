"""
lint_wrapper_targets.py — Every skill/lint task wrapper must target real code (AW-05 guard).

Rules:
  W-T1. Each *_task.cmd / *_task.sh under skills/**/src/ and workspace/lint/
        declaring _PY_SCRIPT must point at an existing .py file (after resolving
        %~dp0 / ${SCRIPT_DIR} / $(dirname …) to the wrapper's directory).
  W-T2. That file must be syntactically valid Python (ast.parse — we never
        import: skill code targets GS services and heavy optional deps).
  W-T3. Any 'python -m volforecast.<mod>' in a wrapper must map to an existing
        src/volforecast/<mod>.py or <mod>/__init__.py that parses.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PY_SCRIPT_CMD = re.compile(r'_PY_SCRIPT=(?:%~dp0)?([^"&\r\n]+\.py)')
# ${_SHARED}/ is the Plan-03 shared-dispatcher prefix (skills/_shared/vf_entry.py)
PY_SCRIPT_SH = re.compile(r'_PY_SCRIPT="?(?:\$\{?SCRIPT_DIR\}?/|\$\{?_SHARED\}?/|\$\(dirname[^)]*\)/)?([^"\s]+\.py)')
MODULE_TARGET = re.compile(r"python[3]?\s+-m\s+(volforecast[\w.]*)")


def wrappers() -> list[Path]:
    out: list[Path] = []
    for root in [REPO_ROOT / "skills", REPO_ROOT / "workspace" / "lint"]:
        if root.is_dir():
            out += sorted(root.rglob("*_task.cmd")) + sorted(root.rglob("*_task.sh"))
    return out


def check_parses(p: Path) -> str | None:
    try:
        ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return f"line {exc.lineno}: {exc.msg}"
    return None


def module_to_path(mod: str) -> Path | None:
    base = REPO_ROOT / "src" / Path(*mod.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def main() -> int:
    errors: list[str] = []
    checked = 0
    for w in wrappers():
        rel = w.relative_to(REPO_ROOT).as_posix()
        text = w.read_text(encoding="utf-8", errors="replace")
        pat = PY_SCRIPT_CMD if w.suffix == ".cmd" else PY_SCRIPT_SH
        for m in pat.finditer(text):
            checked += 1
            # ${_SHARED} resolves to skills/_shared/ (Plan-03 shared dispatcher),
            # not the wrapper's own directory.
            if "_SHARED" in m.group(0):
                base_dir = REPO_ROOT / "skills" / "_shared"
            else:
                base_dir = w.parent
            target = (base_dir / m.group(1).strip().replace("\\", "/")).resolve()
            if not target.is_file():
                errors.append(f"[target-missing] {rel}: _PY_SCRIPT → "
                              f"'{m.group(1).strip()}' does not exist")
            else:
                err = check_parses(target)
                if err:
                    errors.append(f"[target-syntax] {rel}: {target.name} — {err}")
        for m in MODULE_TARGET.finditer(text):
            checked += 1
            mod_path = module_to_path(m.group(1))
            if mod_path is None:
                errors.append(f"[module-missing] {rel}: python -m {m.group(1)} — "
                              f"no such module under src/volforecast/")
            else:
                err = check_parses(mod_path)
                if err:
                    errors.append(f"[module-syntax] {rel}: {mod_path.name} — {err}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {checked} wrapper targets across {len(wrappers())} wrappers "
          f"exist and parse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
