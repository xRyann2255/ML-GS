"""Lint: enforce skill folder structure conventions.

Checks every folder under skills/ against the canonical layout:

    <SKILL_NAME>/
    ├── SKILL.md          # required, exact case
    └── src/              # optional (only if skill has executable helpers)
        ├── *.py / *.sh / *.ps1 / *.json  (code files)
        └── __pycache__/  (ignored)

Rules enforced:
  1. SKILL.md required  — every skill folder must have a root-level SKILL.md.
  2. Exact case          — must be "SKILL.md", not "skill.md" or "Skill.md".
  3. No extra files      — only SKILL.md and src/ at the root level.
  4. Folder naming       — skill folders must be UPPER_SNAKE_CASE.
  5. INDEX.md present    — skills/ root must have an INDEX.md registry.
  6. No nested SKILL.md  — SKILL.md must not appear inside src/.
  7. src/ contents        — only code files and __pycache__ allowed.
  8. No empty src/        — if src/ exists, it must contain at least one file.

Usage:
    python workspace/lint/lint_skills_structure.py
    python workspace/lint/lint_skills_structure.py --root <path>

Returns exit code 0 on pass, 1 on violation.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"

# Allowed extensions inside src/
ALLOWED_SRC_EXTENSIONS = frozenset({
    ".py", ".sh", ".ps1", ".cmd", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".md",  # reference data co-located with scripts (e.g. epssp-fields.md)
})

# Ignored entries inside src/
IGNORED_SRC_ENTRIES = frozenset({"__pycache__", "__init__.py", ".gitkeep"})

# Ignored entries at skill root (not skill folders themselves)
ROOT_ONLY_FILES = frozenset({"INDEX.md"})

# Per-skill structural exceptions (e.g. Flask apps with extra dirs)
SKILL_ROOT_EXCEPTIONS: dict[str, frozenset[str]] = {
    "S3_DASHBOARD": frozenset({"cache"}),
}
SKILL_SRC_DIR_EXCEPTIONS: dict[str, frozenset[str]] = {
    "S3_DASHBOARD": frozenset({"templates"}),
}

# Folder name pattern: UPPER_SNAKE_CASE
RE_FOLDER_NAME = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")


# Non-skill directories under skills/ that should be excluded from scanning
EXCLUDED_DIRS = frozenset({"_shared"})


def _is_skill_folder(name: str) -> bool:
    """Return True if this looks like a skill folder (not INDEX.md etc.)."""
    return name not in ROOT_ONLY_FILES and name not in EXCLUDED_DIRS and not name.startswith(".")


def scan_skills(root: Path) -> list[tuple[str, str, str]]:
    """Return list of (skill_name, rule_id, message) violations."""
    violations: list[tuple[str, str, str]] = []

    if not root.is_dir():
        violations.append(("<root>", "E0", f"Skills root not found: {root}"))
        return violations

    # Rule 5: INDEX.md must exist
    if not (root / "INDEX.md").is_file():
        violations.append(("<root>", "E5", "Missing INDEX.md in skills root"))

    entries = sorted(os.listdir(root))
    for entry in entries:
        if not _is_skill_folder(entry):
            continue
        skill_path = root / entry
        if not skill_path.is_dir():
            continue

        # Rule 4: folder naming
        if not RE_FOLDER_NAME.match(entry):
            violations.append((entry, "E4", f"Folder name '{entry}' is not UPPER_SNAKE_CASE"))

        children = set(os.listdir(skill_path))

        # Rule 1 + 2: SKILL.md required, exact case
        has_skill_md = "SKILL.md" in children
        has_skill_md_wrong_case = False
        if not has_skill_md:
            for c in children:
                if c.lower() == "skill.md" and c != "SKILL.md":
                    has_skill_md_wrong_case = True
                    violations.append((entry, "E2", f"Found '{c}' — must be exactly 'SKILL.md'"))
                    break
            if not has_skill_md_wrong_case:
                violations.append((entry, "E1", "Missing SKILL.md"))

        # Rule 3: no extra files at root level
        allowed_root = {"SKILL.md", "src"} | SKILL_ROOT_EXCEPTIONS.get(entry, frozenset())
        extras = children - allowed_root
        # Also tolerate case-insensitive SKILL.md for reporting
        extras = {e for e in extras if e.lower() != "skill.md"}
        for extra in sorted(extras):
            extra_path = skill_path / extra
            if extra.startswith("."):
                continue  # dotfiles are fine
            violations.append((entry, "E3", f"Unexpected entry at skill root: '{extra}'"))

        # Check src/ if present
        src_path = skill_path / "src"
        if src_path.is_dir():
            src_entries = os.listdir(src_path)
            # Filter out ignored entries
            meaningful = [e for e in src_entries if e not in IGNORED_SRC_ENTRIES]

            # Rule 8: no empty src/
            if not meaningful:
                violations.append((entry, "E8", "src/ exists but is empty"))

            for src_entry in src_entries:
                if src_entry in IGNORED_SRC_ENTRIES:
                    continue
                src_entry_path = src_path / src_entry
                if src_entry_path.is_dir():
                    # Only __pycache__ allowed as subdirectory (plus per-skill exceptions)
                    if src_entry not in IGNORED_SRC_ENTRIES and src_entry not in SKILL_SRC_DIR_EXCEPTIONS.get(entry, frozenset()):
                        violations.append((entry, "E7", f"Unexpected directory in src/: '{src_entry}'"))
                    continue

                # Rule 6: no SKILL.md inside src/
                if src_entry.lower() == "skill.md":
                    violations.append((entry, "E6", "SKILL.md found inside src/ — must be at skill root"))
                    continue

                # Rule 7: only code files
                ext = Path(src_entry).suffix.lower()
                if ext not in ALLOWED_SRC_EXTENSIONS:
                    violations.append((entry, "E7", f"Unexpected file type in src/: '{src_entry}' ({ext})"))

    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=SKILLS_ROOT, help="Skills root directory")
    args = ap.parse_args()

    violations = scan_skills(args.root)

    for skill, rule, msg in violations:
        print(f"  [{rule}] {skill}: {msg}")

    print(f"\nScanned {args.root}")
    if violations:
        print(f"FAIL: {len(violations)} violation(s) found.")
        return 1
    else:
        print("PASS: all skill folders follow the canonical structure.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
