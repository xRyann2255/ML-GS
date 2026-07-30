"""
lint_model_pins.py — Single source of truth for the subagent model pin (AW-G3/AW-23).

EXPECTED_MODEL is THE constant. All other surfaces must point here, not restate it.
Rules:
  M1. In .github/prompts/*.prompt.md frontmatter, any 'model:' value must equal
      EXPECTED_MODEL exactly (frontmatter pins are allowed; mismatches never are).
  M2. Any other occurrence of a model literal (display name 'Claude Opus <ver>'
      or slug 'claude-opus…') in tracked text surfaces is an ERROR unless the
      file is grandfathered in whitelists/model_pins.txt (burned by Plans 05/07).
  M3. Files in SANCTIONED_SITES are skipped ENTIRELY — the raw literal is
      canonical there (the pin itself + the fallback clause). These are
      structurally exempt, NOT whitelist entries, so model_pins.txt burns EMPTY.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EXPECTED_MODEL = "Claude Opus 4.6"

# Sites where the raw display-name literal is CANONICAL and must remain —
# structurally exempt (NOT whitelisted): policy/subagent_protocol.md (the
# canonical pin) and .github/copilot-instructions.md Rule 9 (fallback clause).
# The lint skips these two paths entirely; every OTHER prose literal is an ERROR
# (grandfathered via model_pins.txt until Plans 05/07 burn it fully EMPTY).
SANCTIONED_SITES = frozenset({
    "policy/subagent_protocol.md",
    ".github/copilot-instructions.md",
})

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WHITELIST = Path(__file__).resolve().parent / "whitelists" / "model_pins.txt"
LITERAL = re.compile(r"Claude\s+Opus\s+[0-9][0-9.]*|claude-opus[\w.\-]*", re.IGNORECASE)
FRONTMATTER_MODEL = re.compile(r"^model:\s*(.+?)\s*$", re.MULTILINE)
SCAN_DIRS = [".github", "workflows", "policy", "personas", "skills", "memory"]
SCAN_FILES = ["AGENTS.md"]
SKIP_PARTS = {"_dormant", "_archived", "node_modules", "__pycache__", "enghub", "knowledge", "tmp"}
EXTS = {".md", ".yaml", ".yml", ".json"}


def load_whitelist() -> set[str]:
    if not WHITELIST.is_file():
        return set()
    return {
        line.strip() for line in WHITELIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def frontmatter_span(text: str) -> tuple[int, int]:
    m = re.match(r"^---\s*\n.*?\n---", text, re.DOTALL)
    return (m.start(), m.end()) if m else (0, 0)


def scan_files() -> list[Path]:
    files = [REPO_ROOT / f for f in SCAN_FILES if (REPO_ROOT / f).is_file()]
    for d in SCAN_DIRS:
        root = REPO_ROOT / d
        if root.is_dir():
            files += [
                p for p in sorted(root.rglob("*"))
                if p.suffix in EXTS and not (set(p.parts) & SKIP_PARTS)
            ]
    return files


def main() -> int:
    wl = load_whitelist()
    errors: list[str] = []
    for f in scan_files():
        rel = f.relative_to(REPO_ROOT).as_posix()
        if rel in SANCTIONED_SITES:
            continue  # canonical pin lives here — structurally exempt (not whitelisted)
        text = f.read_text(encoding="utf-8", errors="replace")
        is_prompt = rel.startswith(".github/prompts/") and rel.endswith(".prompt.md")
        fm_start, fm_end = frontmatter_span(text) if is_prompt else (0, 0)
        if is_prompt:
            for m in FRONTMATTER_MODEL.finditer(text[fm_start:fm_end]):
                if m.group(1).strip().strip("'\"") != EXPECTED_MODEL:
                    errors.append(f"[pin-mismatch] {rel}: frontmatter model "
                                  f"'{m.group(1).strip()}' != EXPECTED_MODEL "
                                  f"'{EXPECTED_MODEL}'")
        for m in LITERAL.finditer(text):
            if is_prompt and fm_start <= m.start() < fm_end:
                continue  # frontmatter pins handled by M1
            if rel in wl:
                break  # grandfathered file — Plans 05/07 burn it down
            line_no = text.count("\n", 0, m.start()) + 1
            errors.append(f"[raw-literal] {rel}:{line_no}: raw model literal "
                          f"'{m.group(0)}' — point at lint_model_pins.EXPECTED_MODEL "
                          f"or policy/subagent_protocol.md instead")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: model pin literals confined to prompt frontmatter (== "
          f"'{EXPECTED_MODEL}') and {len(wl)} grandfathered files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
