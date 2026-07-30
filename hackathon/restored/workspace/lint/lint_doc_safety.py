"""Lint: detect hardcoded env values and secexpr --full in documentation files.

Rules (from implementation_boundary.md and preflight-gates.md):
  G3. Hardcoded DB names/paths must not appear in .md files (SKILL.md, memory, policy).
  G4. secexpr --full examples must not appear in .md files outside known safe locations.

Usage:
    python workspace/lint/lint_doc_safety.py

Exit code: 0 if pass, 1 on violations.
"""

from __future__ import annotations

import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MAX_WORKERS = 4

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_ROOTS = [
    REPO_ROOT / "skills",
    REPO_ROOT / "memory",
    REPO_ROOT / "policy",
    REPO_ROOT / "personas",
    REPO_ROOT / "workflows",
]

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "archive", "tmp", "knowledge", "enghub", "raw"}
# _dormant/_archived are DELIBERATELY scanned here: safety checks apply to parked content (policy: memory/meta/guide.md §Dormant files, wfo-04-3).

# Files where --full is legitimately documented (the SLANG_EDIT skill guide,
# implementation_boundary.md explaining the rule, preflight-gates.md, etc.)
SECEXPR_FULL_WHITELIST = frozenset({
    "implementation_boundary.md",
    "preflight-gates.md",
    "working-agreements.md",
    "lint-edit.md",
    "secexpr-gotchas.md",
    "operating-principles.md",
    "index.md",
})

# Files where DB names are legitimately documented (user profile, the hardcoded-env
# lint itself references them, person/user.md has actual values, etc.)
HARDCODED_DB_WHITELIST = frozenset({
    "user.md",
    "lint-edit.md",
    "run.md",
})

# ── Patterns ─────────────────────────────────────────────────────────────────

# G3: Hardcoded DB patterns in Markdown (looser than the .py lint — catches
# unquoted references too, e.g. in tables and prose)
HARDCODED_DB_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"!NYC_CoreData", re.I),            "hardcoded session DB '!NYC_CoreData'"),
    (re.compile(r"SPGProdNYC\s+RO", re.I),          "hardcoded object DB 'SPGProdNYC RO'"),
    (re.compile(r"!NYC UserDBs!home!\w+", re.I),     "hardcoded user DB path"),
    (re.compile(r"RegTest Scratch", re.I),            "hardcoded scratch DB 'RegTest Scratch'"),
]

# G4: secexpr --full outside whitelisted docs
RE_SECEXPR_FULL = re.compile(r"secexpr\s.*--full|--full\s.*secexpr", re.I)

# Combined suppression regex (single match instead of iterating a list)
RE_SUPPRESSED = re.compile(
    r"NEVER|MUST NOT|FORBIDDEN|must always|do not|ONLY exception"
    r"|--safe"
    r"|^\s*>",
    re.I,
)

# Quick-reject: combined DB pattern for fast skip on most lines
RE_ANY_DB = re.compile(r"NYC_CoreData|SPGProdNYC|NYC UserDBs|RegTest Scratch", re.I)


class Violation:
    __slots__ = ("path", "lineno", "category", "text")

    def __init__(self, path: Path, lineno: int, category: str, text: str):
        self.path = path
        self.lineno = lineno
        self.category = category
        self.text = text

    def __str__(self) -> str:
        rel = self.path
        try:
            rel = self.path.relative_to(REPO_ROOT)
        except ValueError:
            pass
        return f"  [{self.category}] {rel}:{self.lineno}  {self.text.strip()}"


def _is_suppressed(line: str) -> bool:
    return bool(RE_SUPPRESSED.search(line))


def scan_file(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return violations

    lines = content.splitlines()
    in_fence = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        # Skip fenced code blocks — they're often literal examples
        if in_fence:
            continue
        if _is_suppressed(line):
            continue

        # G3: hardcoded DB names — quick reject on combined pattern
        if path.name not in HARDCODED_DB_WHITELIST and RE_ANY_DB.search(line):
            for pat, desc in HARDCODED_DB_PATTERNS:
                if pat.search(line):
                    violations.append(Violation(path, i, "hardcoded-db-doc", line))

        # G4: secexpr --full
        if path.name not in SECEXPR_FULL_WHITELIST:
            # Only in SLANG_EDIT SKILL.md is --full legitimate
            if path.name == "SKILL.md" and "SLANG_EDIT" in str(path):
                continue
            if RE_SECEXPR_FULL.search(line):
                violations.append(Violation(path, i, "secexpr-full-doc", line))

    return violations


def main() -> int:
    total_files = 0
    all_violations: list[Violation] = []

    # Collect files first, then scan in parallel
    md_files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if fname.endswith(".md"):
                    md_files.append(Path(dirpath) / fname)
    total_files = len(md_files)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for file_vs in pool.map(scan_file, md_files):
            all_violations.extend(file_vs)

    for v in all_violations:
        print(str(v))

    print(f"\nScanned {total_files} Markdown files")
    if all_violations:
        print(f"FAIL: {len(all_violations)} violation(s) found.")
        return 1
    else:
        print("PASS: no hardcoded env or secexpr --full in documentation.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
