"""
lint_memory_priority.py — Enforce memory priority tier rules.

Rules:
  1. P0 budget cap: total estimated tokens for P0 files must not exceed P0_TOKEN_CAP.
  2. P1 reachability: every P1 memory file must be referenced by at least one
     skill, persona, workflow, prompt, AGENTS.md, or copilot-instructions.md.
  3. P2/P3 exempt from reachability — P2 files are loaded via INDEX.md triggers,
     P3 files are archive-tier. Neither requires explicit skill/prompt references.

Input: reads memory/meta.index.md for the priority table, then scans the codebase.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

P0_TOKEN_CAP = 800  # hard limit for total P0 token estimate

# Directories to scan for references to memory files
# (relative to repo root)
REACHABILITY_SCAN_DIRS = ["skills", "personas", "workflows", ".github/prompts", ".github/instructions"]
REACHABILITY_SCAN_FILES = [
    "AGENTS.md",
    "workspace/docs/slang/copilot-instructions.md",
]
REACHABILITY_SCAN_GLOBS = [
    (".github/prompts", "*.prompt.md"),
    (".github/instructions", "*.instructions.md"),
]

# Files exempt from reachability checks (loaded by convention, not explicit ref)
REACHABILITY_EXEMPT = {
    "design.md",              # memory design doc, governance
    "meta/guide.md",          # schema ref, loaded when writing memory
    "person/user.md",         # P0 — always loaded at boot
}

# ── Parsing ────────────────────────────────────────────────────────────────────

# Matches INDEX.md rows: | [path](path) | Description | P0 | ~690 | trigger |
_INDEX_ROW = re.compile(
    r"\|\s*\[([^\]]+)\]\([^)]+\)\s*\|"  # linked path
    r"[^|]*\|"                           # description
    r"\s*(P\d)\s*\|"                     # priority
    r"\s*~?(\d+)\s*\|",                  # token estimate
)


def parse_index(index_path: Path) -> list[dict]:
    """Parse INDEX.md into a list of {file, priority, tokens}."""
    entries = []
    text = index_path.read_text(encoding="utf-8")
    for m in _INDEX_ROW.finditer(text):
        entries.append({
            "file": m.group(1),
            "priority": m.group(2),
            "tokens": int(m.group(3)),
        })
    return entries


def gather_reference_corpus(repo_root: Path) -> str:
    """Read all files that could reference memory files; return concatenated text."""
    parts: list[str] = []

    for d in REACHABILITY_SCAN_DIRS:
        scan_root = repo_root / d
        if scan_root.is_dir():
            for md in scan_root.rglob("*.md"):
                parts.append(md.read_text(encoding="utf-8", errors="replace"))

    for rel in REACHABILITY_SCAN_FILES:
        p = repo_root / rel
        if p.is_file():
            parts.append(p.read_text(encoding="utf-8", errors="replace"))

    for rel_dir, glob_pat in REACHABILITY_SCAN_GLOBS:
        d = repo_root / rel_dir
        if d.is_dir():
            for f in d.glob(glob_pat):
                parts.append(f.read_text(encoding="utf-8", errors="replace"))

    return "\n".join(parts)


def is_referenced(filename: str, corpus: str) -> bool:
    """Check if a memory file path or its basename appears in the reference corpus."""
    # Direct path match (e.g. "ref/devtools.md")
    if filename in corpus:
        return True
    # Basename match (e.g. "devtools.md" or "devtools")
    basename = filename.rsplit("/", 1)[-1] if "/" in filename else filename
    if basename in corpus:
        return True
    stem = basename.removesuffix(".md")
    if stem in corpus:
        return True
    return False


# ── Checks ─────────────────────────────────────────────────────────────────────

def check_p0_budget(entries: list[dict]) -> list[tuple[str, str, str]]:
    """Returns list of (severity, check, message) tuples."""
    results = []
    p0_entries = [e for e in entries if e["priority"] == "P0"]
    total = sum(e["tokens"] for e in p0_entries)
    files_str = ", ".join(f"`{e['file']}` (~{e['tokens']})" for e in p0_entries)

    if total > P0_TOKEN_CAP:
        results.append((
            "ERROR",
            "p0-budget",
            f"P0 total ~{total} tokens exceeds cap of {P0_TOKEN_CAP}. "
            f"Files: {files_str}. Downgrade or trim P0 files.",
        ))
    else:
        headroom = P0_TOKEN_CAP - total
        if headroom < 100:
            results.append((
                "WARN",
                "p0-budget",
                f"P0 total ~{total} tokens — only ~{headroom} headroom before cap ({P0_TOKEN_CAP}).",
            ))

    return results


def check_reachability(entries: list[dict], corpus: str) -> list[tuple[str, str, str]]:
    """Check that P1 files are referenced somewhere in skills/personas/workflows/prompts/AGENTS.md."""
    results = []
    for e in entries:
        if e["priority"] != "P1":
            continue
        fname = e["file"]
        if fname in REACHABILITY_EXEMPT:
            continue
        if not is_referenced(fname, corpus):
            results.append((
                "WARN",
                "reachability",
                f"{fname} ({e['priority']}) is orphaned — not referenced by any "
                f"skill, persona, workflow, or prompt. Add a reference or downgrade/remove.",
            ))
    return results


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent  # workspace/lint/ → workspace/ → repo root
    memory_dir = repo_root / "memory"
    index_path = memory_dir / "INDEX.md"

    if not index_path.is_file():
        print("ERROR: memory/INDEX.md not found")
        return 2

    entries = parse_index(index_path)
    if not entries:
        print("WARN: no entries parsed from INDEX.md")
        return 0

    # Gather reference corpus once (cheaper than per-file grep)
    corpus = gather_reference_corpus(repo_root)

    all_results: list[tuple[str, str, str]] = []
    all_results.extend(check_p0_budget(entries))
    all_results.extend(check_reachability(entries, corpus))

    errors = [(s, c, m) for s, c, m in all_results if s == "ERROR"]
    warnings = [(s, c, m) for s, c, m in all_results if s == "WARN"]

    # Summary
    p0_total = sum(e["tokens"] for e in entries if e["priority"] == "P0")
    p0_count = sum(1 for e in entries if e["priority"] == "P0")
    p1_count = sum(1 for e in entries if e["priority"] == "P1")
    p2_count = sum(1 for e in entries if e["priority"] == "P2")
    p3_count = sum(1 for e in entries if e["priority"] == "P3")

    print(f"P0: {p0_count} files, ~{p0_total} tokens (cap: {P0_TOKEN_CAP})")
    print(f"P1: {p1_count} files | P2: {p2_count} files (exempt) | P3: {p3_count} files (exempt)")

    if warnings:
        for _, check, msg in warnings:
            print(f"  WARN  [{check}] {msg}")

    if errors:
        for _, check, msg in errors:
            print(f"  ERROR [{check}] {msg}")
        return 1

    if not warnings:
        print("PASS: All priority tier rules satisfied.")
    else:
        print(f"PASS (with {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
