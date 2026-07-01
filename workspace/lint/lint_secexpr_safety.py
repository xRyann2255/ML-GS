"""Static lint: enforce secexpr --safe-by-default rule.

Scans all .py files under skills/ for violations:
  1. Literal "--full" in secexpr command strings outside edit.py
  2. safe=False kwarg usage outside edit.py (and the util's docstring)
  3. secexpr_util default flip regression (safe= defaults must be True)

Usage:
    python workspace/lint/lint_secexpr_safety.py
    python workspace/lint/lint_secexpr_safety.py --strict   # non-zero exit on warn

Returns exit code 0 on pass, 1 on violation.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────

SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"

# Only these files may contain --full or safe=False in executable code.
FULL_MODE_WHITELIST = frozenset({"edit.py", "copy-script.py"})

# These files implement the safe/full enforcement mechanism itself and
# legitimately reference --full in the mode-selection logic.
FULL_IMPL_WHITELIST = frozenset({"secexpr_util.py"})

# Files/directories to skip entirely.
SKIP_DIRS = {"__pycache__", ".git", "node_modules"}

# Patterns that indicate a secexpr --full invocation.
# Must have 'secexpr' on same line or be a mode= assignment string.
RE_FULL_CMD = re.compile(
    r'secexpr\s.*--full'
    r'|mode\s*=\s*["\']--full["\']'
    r'|["\']\s*--full\s*["\'].*secexpr'
)

# safe=False as a keyword argument (not inside a comment or docstring — we
# handle docstrings heuristically by checking the surrounding context).
RE_SAFE_FALSE = re.compile(r"""\bsafe\s*=\s*False\b""")

# Default parameter regression: def run_secexpr_...(... safe: bool = False ...)
RE_UNSAFE_DEFAULT = re.compile(r"""def\s+run_secexpr\w*\(.*safe:\s*bool\s*=\s*False""")


def _is_docstring_or_comment(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''")


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, category, line_text) violations."""
    violations: list[tuple[int, str, str]] = []
    filename = path.name

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return violations

    in_docstring = False
    for i, line in enumerate(lines, start=1):
        # Rough docstring tracking (triple-quote toggle).
        count = line.count('"""') + line.count("'''")
        if count % 2 == 1:
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if _is_docstring_or_comment(line):
            continue

        # Rule 1: --full outside whitelist and implementation files
        if RE_FULL_CMD.search(line) and filename not in FULL_MODE_WHITELIST | FULL_IMPL_WHITELIST:
            violations.append((i, "--full", line.rstrip()))

        # Rule 2: safe=False outside whitelist (skip secexpr_util.py itself —
        # the guard function references safe=False in its logic, not as a default)
        if filename != "secexpr_util.py" and filename not in FULL_MODE_WHITELIST:
            if RE_SAFE_FALSE.search(line):
                violations.append((i, "safe=False", line.rstrip()))

        # Rule 3: unsafe default in util
        if filename == "secexpr_util.py" and RE_UNSAFE_DEFAULT.search(line):
            violations.append((i, "unsafe-default", line.rstrip()))

    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="Exit 1 on any warning")
    ap.add_argument("--root", type=Path, default=SKILLS_ROOT, help="Root to scan")
    args = ap.parse_args()

    root: Path = args.root
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    total_violations = 0
    total_files = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            fpath = Path(dirpath) / fname
            total_files += 1
            violations = scan_file(fpath)
            for lineno, category, text in violations:
                rel = fpath.relative_to(root)
                print(f"  VIOLATION [{category}] {rel}:{lineno}  {text}")
                total_violations += 1

    print(f"\nScanned {total_files} Python files under {root}")
    if total_violations:
        print(f"FAIL: {total_violations} violation(s) found.")
        return 1
    else:
        print("PASS: no secexpr safety violations.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
