"""Lint: detect drift between documented counts and actual skill/persona folders.

Rules (from implementation_boundary.md):
  G5. The skill count and list in implementation_boundary.md must match skills/.
      The persona count in implementation_boundary.md must match personas/.

Usage:
    python workspace/lint/lint_registry_drift.py

Exit code: 0 if pass, 1 on violations.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SKILLS_ROOT = REPO_ROOT / "skills"
PERSONAS_ROOT = REPO_ROOT / "personas"
IMPL_BOUNDARY = REPO_ROOT / "policy" / "implementation_boundary.md"

# Pattern for the skill count + list row:
#   | Skill system (18 skills) | `skills/` | SLANG_EDIT, ... |
RE_SKILL_ROW = re.compile(
    r"\|\s*Skill system\s*\((\d+)\s*skills?\)\s*\|\s*`skills/`\s*\|\s*(.*?)\s*\|",
)

# Pattern for the persona count row:
#   | Persona registry (14 personas) | `personas/` | ... |
RE_PERSONA_ROW = re.compile(
    r"\|\s*Persona registry\s*\((\d+)\s*personas?\)\s*\|",
)

# INDEX.md is not a skill folder
NON_SKILL_ENTRIES = {"INDEX.md", "design.md", ".git", "__pycache__", ".gitkeep", "_shared"}
# INDEX.md and design.md are not personas
NON_PERSONA_FILES = {"INDEX.md", "design.md"}


def _get_actual_skills() -> list[str]:
    """Return sorted list of skill names (folders + guide-only .md files)."""
    if not SKILLS_ROOT.is_dir():
        return []
    skills: list[str] = []
    for e in os.listdir(SKILLS_ROOT):
        if e in NON_SKILL_ENTRIES or e.startswith("."):
            continue
        full = SKILLS_ROOT / e
        if full.is_dir():
            skills.append(e)
        elif e.endswith(".md"):
            # Guide-only skill files like ENGHUB.md → ENGHUB
            skills.append(e.removesuffix(".md"))
    return sorted(skills)


def _get_actual_personas() -> list[str]:
    """Return sorted list of persona .md files (stem only)."""
    if not PERSONAS_ROOT.is_dir():
        return []
    return sorted(
        f.stem for f in PERSONAS_ROOT.glob("*.md")
        if f.name not in NON_PERSONA_FILES
    )


def main() -> int:
    violations: list[str] = []

    actual_skills = _get_actual_skills()
    actual_personas = _get_actual_personas()

    if not IMPL_BOUNDARY.is_file():
        print(f"WARN: {IMPL_BOUNDARY} not found — skipping.")
        return 0

    text = IMPL_BOUNDARY.read_text(encoding="utf-8")

    # ── Skills ───────────────────────────────────────────────────────────────
    m_skill = RE_SKILL_ROW.search(text)
    if m_skill:
        doc_count = int(m_skill.group(1))
        doc_list = sorted(s.strip() for s in m_skill.group(2).split(",") if s.strip())

        if doc_count != len(actual_skills):
            violations.append(
                f"  [skill-count-drift] implementation_boundary.md says {doc_count} skills, "
                f"but skills/ has {len(actual_skills)}"
            )

        doc_set = set(doc_list)
        actual_set = set(actual_skills)
        missing_from_doc = actual_set - doc_set
        extra_in_doc = doc_set - actual_set
        if missing_from_doc:
            violations.append(
                f"  [skill-list-drift] Skills on disk but not in docs: {', '.join(sorted(missing_from_doc))}"
            )
        if extra_in_doc:
            violations.append(
                f"  [skill-list-drift] Skills in docs but not on disk: {', '.join(sorted(extra_in_doc))}"
            )
    else:
        violations.append(
            "  [skill-row-missing] Could not find skill count row in implementation_boundary.md"
        )

    # ── Personas ─────────────────────────────────────────────────────────────
    m_persona = RE_PERSONA_ROW.search(text)
    if m_persona:
        doc_count = int(m_persona.group(1))
        if doc_count != len(actual_personas):
            violations.append(
                f"  [persona-count-drift] implementation_boundary.md says {doc_count} personas, "
                f"but personas/ has {len(actual_personas)} ({', '.join(actual_personas)})"
            )
    else:
        violations.append(
            "  [persona-row-missing] Could not find persona count row in implementation_boundary.md"
        )

    for v in violations:
        print(v)

    print(f"\nActual: {len(actual_skills)} skills, {len(actual_personas)} personas")
    if violations:
        print(f"FAIL: {len(violations)} drift violation(s) found.")
        return 1
    else:
        print("PASS: documented counts match actual folders.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
