"""Lint: validate SKILL.md content structure and link integrity.

Complements lint_skills_structure.py (folder layout) and design_lint.py
(size/memory-ref) by validating the *content* of each SKILL.md:

  1. Frontmatter     — YAML fence with required keys (name, description).
  2. Title format    — H1 heading matches "# NAME — Title".
  3. Purpose quote   — Blockquote starting with "> **Purpose:**".
  4. Out of scope    — "**Out of scope:**" line present.
  5. Skill Identity  — "## Skill Identity" section with required table fields.
  6. Required sections — "## When to Use" and "## Links" present.
  7. Link depth      — No `../../../memory/` (over-traversal); should be `../../memory/`.
  8. Link targets    — Every `](../../memory/<file>)` link resolves to a real file.
  9. Phantom paths   — No references to deleted paths like `instructions/skills/`.
 10. Double fences   — No double code-fence wrappers (````skill wrapping ```).

Usage:
    python workspace/lint/validate_skills.py
    python workspace/lint/validate_skills.py --fix   # auto-fix link depth issues

Exit code: 0 if pass, 1 on violations.
"""

from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MAX_WORKERS = 4

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
MEMORY_ROOT = REPO_ROOT / "memory"

# ── Required frontmatter keys ─────────────────────────────────────────────
REQUIRED_FM_KEYS = {"name", "description"}

# ── Required Skill Identity table fields ──────────────────────────────────
REQUIRED_IDENTITY_FIELDS = {"Name", "Scope", "Inputs", "Outputs", "Authority"}

# ── Required sections (## headings) ──────────────────────────────────────
REQUIRED_SECTIONS = {"Skill Identity", "When to Use", "Links"}

# Advisory sections — warn if missing but don't error
ADVISORY_SECTIONS = {"Troubleshooting"}

# ── Forbidden patterns ──────────────────────────────────────────────────────
RE_OVERDEEP_LINK = re.compile(r"\]\(\.\./\.\./\.\./memory/")
RE_CORRECT_LINK = re.compile(r"\]\(\.\./\.\./memory/([^)]+)\)")
RE_PHANTOM_PATH = re.compile(r"instructions/skills/")
RE_DOUBLE_FENCE = re.compile(r"^````+\s*skill", re.MULTILINE)

# ── Frontmatter parsing ─────────────────────────────────────────────────────
RE_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class Violation:
    __slots__ = ("severity", "rule", "skill", "message")

    def __init__(self, severity: str, rule: str, skill: str, message: str):
        self.severity = severity  # "ERROR" | "WARN"
        self.rule = rule
        self.skill = skill
        self.message = message

    def __str__(self) -> str:
        return f"  [{self.severity}] {self.rule}: {self.skill}\n         {self.message}"


def _parse_frontmatter(text: str) -> dict[str, str] | None:
    """Extract YAML frontmatter key-value pairs. Returns None if no frontmatter."""
    m = RE_FRONTMATTER.match(text)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def _extract_h2_headings(text: str) -> set[str]:
    """Return all ## heading names (stripped)."""
    return {m.group(1).strip() for m in re.finditer(r"^## (.+)", text, re.MULTILINE)}


def _extract_table_bold_fields(text: str, section: str) -> set[str]:
    """Extract bold field names from a Markdown table under a given ## section."""
    fields: set[str] = set()
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            in_section = heading == section
            continue
        if in_section:
            # Table row: | **Name** | value |
            m = re.match(r"\|\s*\*\*(.+?)\*\*\s*\|", line)
            if m:
                fields.add(m.group(1).strip())
            # Stop at next section
            if line.startswith("# "):
                break
    return fields


def validate_skill(skill_dir: Path, fix: bool = False) -> list[Violation]:
    """Validate a single SKILL.md. Returns list of violations."""
    vs: list[Violation] = []
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        return vs  # lint_skills_structure.py catches this

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    original_text = text  # for fix comparison

    # ── Rule 1: Frontmatter ──────────────────────────────────────────────
    fm = _parse_frontmatter(text)
    if fm is None:
        vs.append(Violation("ERROR", "frontmatter", skill_name,
                            "Missing YAML frontmatter (---/--- block)."))
    else:
        missing_keys = REQUIRED_FM_KEYS - set(fm.keys())
        if missing_keys:
            vs.append(Violation("ERROR", "frontmatter", skill_name,
                                f"Missing frontmatter keys: {', '.join(sorted(missing_keys))}"))

        # Check skill name matches folder
        if "name" in fm and fm["name"].upper() != skill_name:
            vs.append(Violation("WARN", "frontmatter", skill_name,
                                f"Frontmatter name: '{fm['name']}' doesn't match folder '{skill_name}'"))

    # ── Rule 2: H1 title ────────────────────────────────────────────────
    h1_match = re.search(r"^# (.+)", text, re.MULTILINE)
    if not h1_match:
        vs.append(Violation("ERROR", "title", skill_name,
                            "Missing H1 title heading."))
    elif " — " not in h1_match.group(1) and " - " not in h1_match.group(1):
        vs.append(Violation("WARN", "title", skill_name,
                            f"H1 '{h1_match.group(1)}' — expected format: '# NAME — Description'"))

    # ── Rule 3: Purpose quote ────────────────────────────────────────────
    if "> **Purpose:**" not in text:
        vs.append(Violation("ERROR", "purpose", skill_name,
                            "Missing purpose blockquote (> **Purpose:** ...)."))

    # ── Rule 4: Out of scope ────────────────────────────────────────────
    if "**Out of scope:**" not in text:
        vs.append(Violation("WARN", "out-of-scope", skill_name,
                            "Missing **Out of scope:** declaration."))

    # ── Rule 5: Skill Identity table ────────────────────────────────────
    headings = _extract_h2_headings(text)
    if "Skill Identity" in headings:
        fields = _extract_table_bold_fields(text, "Skill Identity")
        missing_fields = REQUIRED_IDENTITY_FIELDS - fields
        if missing_fields:
            vs.append(Violation("WARN", "identity-table", skill_name,
                                f"Skill Identity table missing fields: {', '.join(sorted(missing_fields))}"))
    # Absence of the section is caught by Rule 6

    # ── Rule 6: Required sections ──────────────────────────────────────
    for section in sorted(REQUIRED_SECTIONS):
        if section not in headings:
            vs.append(Violation("ERROR", "required-section", skill_name,
                                f"Missing required section: ## {section}"))

    for section in sorted(ADVISORY_SECTIONS):
        if section not in headings:
            vs.append(Violation("WARN", "advisory-section", skill_name,
                                f"Missing advisory section: ## {section}"))

    # ── Rule 7: Link depth ──────────────────────────────────────────────
    overdeep_matches = RE_OVERDEEP_LINK.findall(text)
    if overdeep_matches:
        if fix:
            text = RE_OVERDEEP_LINK.sub("](../../memory/", text)
            vs.append(Violation("WARN", "link-depth", skill_name,
                                f"Fixed {len(overdeep_matches)} over-deep memory link(s) (../../../ → ../../)."))
        else:
            vs.append(Violation("ERROR", "link-depth", skill_name,
                                f"{len(overdeep_matches)} over-deep memory link(s) — use ../../memory/ not ../../../memory/"))

    # ── Rule 8: Link targets ─────────────────────────────────────────────
    for m in RE_CORRECT_LINK.finditer(text):
        target_file = m.group(1).split("#")[0]  # strip any anchor
        target_path = MEMORY_ROOT / target_file
        if not target_path.is_file():
            vs.append(Violation("ERROR", "broken-link", skill_name,
                                f"Broken link: memory/{target_file} does not exist."))

    # ── Rule 9: Phantom paths ───────────────────────────────────────────
    phantom_matches = RE_PHANTOM_PATH.findall(text)
    if phantom_matches:
        if fix:
            text = text.replace("instructions/skills/", "skills/")
            vs.append(Violation("WARN", "phantom-path", skill_name,
                                f"Fixed {len(phantom_matches)} phantom 'instructions/skills/' path(s)."))
        else:
            vs.append(Violation("ERROR", "phantom-path", skill_name,
                                f"{len(phantom_matches)} reference(s) to deleted 'instructions/skills/' path."))

    # ── Rule 10: Double code-fence wrappers ─────────────────────────────
    if RE_DOUBLE_FENCE.search(text):
        vs.append(Violation("WARN", "double-fence", skill_name,
                            "Double code-fence wrapper detected (````skill). Remove outer fence."))

    # ── Write back if fixed ──────────────────────────────────────────────
    if fix and text != original_text:
        skill_md.write_text(text, encoding="utf-8")

    return vs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=SKILLS_ROOT,
                    help="Skills root directory")
    ap.add_argument("--fix", action="store_true",
                    help="Auto-fix link depth and phantom path issues")
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"Skills root not found: {args.root}")
        return 1

    skill_dirs = sorted(
        entry for entry in args.root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".") and (entry / "SKILL.md").is_file()
    )
    skill_count = len(skill_dirs)
    all_violations: list[Violation] = []

    if args.fix:
        # --fix writes files, run sequentially to avoid races
        for d in skill_dirs:
            all_violations.extend(validate_skill(d, fix=True))
    else:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            results = pool.map(validate_skill, skill_dirs)
            for violations in results:
                all_violations.extend(violations)

    # ── Report ─────────────────────────────────────────────────────────
    errors = [v for v in all_violations if v.severity == "ERROR"]
    warns = [v for v in all_violations if v.severity == "WARN"]

    for v in all_violations:
        print(v)

    print(f"\nScanned {skill_count} skill(s) in {args.root}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warns)} warning(s).")
        return 1
    elif warns:
        print(f"PASS (with {len(warns)} warning(s) — run --strict to treat as errors)")
        return 0
    else:
        print("PASS: all skill files follow the standard structure.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
