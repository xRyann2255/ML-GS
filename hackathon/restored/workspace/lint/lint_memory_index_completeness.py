"""Lint: memory INDEX.md completeness and naming rules.

Rules (from memory/design.md §4 and meta/guide.md):
  G1. Every .md file in memory/<domain>/ must be listed in INDEX.md.
  G2. Filenames must be fully lowercase (no uppercase characters in stem).
  G3. Every INDEX.md entry must have a corresponding file on disk (no phantom entries).

Usage:
    python workspace/lint/lint_memory_index_completeness.py

Exit code: 0 if pass, 1 on violations.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = REPO_ROOT / "memory"

# Top-level governance files that don't need INDEX listing
GOVERNANCE_FILES = {"INDEX.md", "design.md", "README.md", "readme.md"}

# Regex to extract file paths from INDEX.md table rows:
#   | [ref/foo.md](ref/foo.md) | ... |
_INDEX_ENTRY = re.compile(
    r"\|\s*\[([^\]]+)\]\([^)]+\)\s*\|",
)


def _collect_content_files(memory_dir: Path) -> list[str]:
    """Return relative paths (forward-slash) of all content .md files."""
    # Skip _archived/ and _dormant/ — intentionally parked outside active domains
    SKIP_PREFIXES = {"_archived", "_dormant"}
    files: list[str] = []
    for md in sorted(memory_dir.rglob("*.md")):
        rel = md.relative_to(memory_dir)
        # Skip files under _archived/ or _dormant/
        if rel.parts[0] in SKIP_PREFIXES:
            continue
        # Skip root-level governance files
        if len(rel.parts) == 1 and rel.name in GOVERNANCE_FILES:
            continue
        # Skip governance files in domain subfolders (e.g., research/README.md)
        if len(rel.parts) == 2 and rel.name in GOVERNANCE_FILES:
            continue
        # Must be in a domain subfolder
        if len(rel.parts) < 2:
            continue
        files.append(str(rel).replace("\\", "/"))
    return files


def _parse_index_entries(memory_dir: Path) -> set[str]:
    """Return set of file paths listed in INDEX.md."""
    index_path = memory_dir / "INDEX.md"
    if not index_path.is_file():
        return set()
    text = index_path.read_text(encoding="utf-8")
    return {m.group(1) for m in _INDEX_ENTRY.finditer(text)}


def main() -> int:
    if not MEMORY_DIR.is_dir():
        print(f"ERROR: {MEMORY_DIR} not found")
        return 2

    content_files = _collect_content_files(MEMORY_DIR)
    index_entries = _parse_index_entries(MEMORY_DIR)
    violations: list[str] = []

    content_set = set(content_files)

    # G1: files on disk not in INDEX.md
    for rel in content_files:
        if rel not in index_entries:
            violations.append(f"  [missing-from-index] {rel} exists on disk but is not listed in INDEX.md")

    # G2: uppercase in filename stem
    for rel in content_files:
        stem = Path(rel).stem
        if stem != stem.lower():
            violations.append(f"  [uppercase-filename] {rel} — stem '{stem}' contains uppercase (must be lowercase)")

    # G3: INDEX.md entries with no corresponding file on disk (phantom entries)
    for entry in sorted(index_entries):
        if entry not in content_set:
            # Root-level governance files (design.md, INDEX.md) are excluded from
            # content_set but legitimately appear in INDEX — check disk directly.
            entry_path = MEMORY_DIR / entry.replace("/", os.sep)
            if entry_path.is_file():
                continue
            # Cross-tree entries reference files at repo root, not under memory/.
            # workspace/, src/, .github/ are the recognized cross-tree prefixes.
            if entry.startswith(("workspace/", "src/", ".github/")):
                repo_path = REPO_ROOT / entry.replace("/", os.sep)
                if repo_path.is_file():
                    continue
            violations.append(f"  [phantom-index-entry] {entry} is listed in INDEX.md but does not exist on disk")

    for v in violations:
        print(v)

    print(f"\nScanned {len(content_files)} memory content files, {len(index_entries)} INDEX.md entries")
    if violations:
        print(f"FAIL: {len(violations)} violation(s) found.")
        return 1
    else:
        print("PASS: all memory files are indexed and correctly named.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
