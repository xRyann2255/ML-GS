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

import math
import re
import sys
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

P0_TOKEN_CAP = 800  # hard limit for total P0 token estimate

WHITELIST_DIR = Path(__file__).resolve().parent / "whitelists"

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

# Matches INDEX.md rows in either style:
#   Link form:  | [path](path) | Description | P0 | ~690 | trigger |
#   Raw form:   | workspace/foo.md | Description | P1 | 1980 | trigger |
# The tokens column may be a number or the string "varies" (for e.g. trials.yaml).
_INDEX_ROW = re.compile(
    r"\|\s*"
    r"(?:\[([^\]]+)\]\([^)]+\)|([A-Za-z0-9_\-./]+\.[A-Za-z0-9]+))"
    r"\s*\|"                               # path column (link OR raw)
    r"[^|]*\|"                             # description
    r"\s*(P\d)\s*\|"                       # priority
    r"\s*~?([\d,]+|varies)\s*\|",          # token estimate (may be "varies")
)


def parse_index(index_path: Path) -> list[dict]:
    """Parse INDEX.md into a list of {file, priority, tokens}.

    `tokens` is the CLAIMED value from the ~Tokens column (0 if 'varies') —
    kept only for the Plan-06 before/after summary line. The enforced numbers
    come from `measured_tokens()` on the resolved file path.
    """
    entries = []
    text = index_path.read_text(encoding="utf-8")
    for m in _INDEX_ROW.finditer(text):
        path_str = m.group(1) or m.group(2)
        tokens_raw = m.group(4)
        try:
            claimed = int(tokens_raw.replace(",", ""))
        except ValueError:
            claimed = 0  # 'varies'
        entries.append({
            "file": path_str,
            "priority": m.group(3),
            "tokens": claimed,
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

def load_grandfather() -> dict[str, int]:
    """Path -> max_tokens ceiling. Plan 06 burns this file down to empty."""
    gf: dict[str, int] = {}
    p = WHITELIST_DIR / "budget_grandfather.txt"
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            path_str, cap = line.rsplit(" ", 1)
            gf[path_str.strip()] = int(cap)
    return gf


def resolve_entry_path(repo_root: Path, index_path_str: str) -> Path:
    """INDEX paths are memory/-relative unless they start with workspace/, src/, .github/."""
    if index_path_str.startswith(("workspace/", "src/", ".github/")):
        return repo_root / index_path_str
    return repo_root / "memory" / index_path_str


def measured_tokens(p: Path) -> int:
    """bytes/4, the suite-wide heuristic (ledger row 'Memory-budget fix')."""
    return math.ceil(p.stat().st_size / 4)


def _grandfather_key(repo_root: Path, index_path_str: str) -> str:
    """Grandfather entries are keyed by REPO-relative path (not INDEX-relative)."""
    return str(resolve_entry_path(repo_root, index_path_str).relative_to(repo_root)).replace("\\", "/")


def check_p0_budget(
    entries: list[dict],
    repo_root: Path,
    grandfather: dict[str, int],
) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    p0 = [e for e in entries if e["priority"] == "P0"]
    measured: dict[str, int] = {}
    counted = 0
    gf_excess: list[tuple[str, int, int]] = []
    for e in p0:
        p = resolve_entry_path(repo_root, e["file"])
        if not p.is_file():
            continue  # missing files are reported by lint_memory_index_completeness.py G3
        t = measured_tokens(p)
        measured[e["file"]] = t
        gf_key = _grandfather_key(repo_root, e["file"])
        if gf_key in grandfather:
            if t > grandfather[gf_key]:
                gf_excess.append((gf_key, t, grandfather[gf_key]))
        else:
            counted += t
    honest_total = sum(measured.values())
    results.append((
        "INFO", "p0-budget",
        f"P0 measured (bytes/4): ~{honest_total} tokens across {len(p0)} files; "
        f"non-grandfathered ~{counted} vs cap {P0_TOKEN_CAP}.",
    ))
    if counted > P0_TOKEN_CAP:
        over = ", ".join(
            f"`{f}` (~{t})" for f, t in measured.items()
            if _grandfather_key(repo_root, f) not in grandfather
        )
        results.append((
            "ERROR", "p0-budget",
            f"Non-grandfathered P0 total ~{counted} exceeds cap {P0_TOKEN_CAP}: {over}",
        ))
    for f, t, cap in gf_excess:
        results.append((
            "ERROR", "p0-budget",
            f"Grandfathered `{f}` grew: measured ~{t} > recorded ceiling {cap}.",
        ))
    return results


def check_p1_budget(
    entries: list[dict],
    repo_root: Path,
    grandfather: dict[str, int],
) -> list[tuple[str, str, str]]:
    """Analogous to check_p0_budget but INFO-only (no hard cap here — the combined
    P0+P1 budget lives in validate_memory.py)."""
    results: list[tuple[str, str, str]] = []
    p1 = [e for e in entries if e["priority"] == "P1"]
    measured: dict[str, int] = {}
    counted = 0
    gf_excess: list[tuple[str, int, int]] = []
    for e in p1:
        p = resolve_entry_path(repo_root, e["file"])
        if not p.is_file():
            continue
        t = measured_tokens(p)
        measured[e["file"]] = t
        gf_key = _grandfather_key(repo_root, e["file"])
        if gf_key in grandfather:
            if t > grandfather[gf_key]:
                gf_excess.append((gf_key, t, grandfather[gf_key]))
        else:
            counted += t
    honest_total = sum(measured.values())
    results.append((
        "INFO", "p1-budget",
        f"P1 measured (bytes/4): ~{honest_total} tokens across {len(p1)} files; "
        f"non-grandfathered ~{counted}.",
    ))
    for f, t, cap in gf_excess:
        results.append((
            "ERROR", "p1-budget",
            f"Grandfathered `{f}` grew: measured ~{t} > recorded ceiling {cap}.",
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
    grandfather = load_grandfather()

    all_results: list[tuple[str, str, str]] = []
    all_results.extend(check_p0_budget(entries, repo_root, grandfather))
    all_results.extend(check_p1_budget(entries, repo_root, grandfather))
    all_results.extend(check_reachability(entries, corpus))

    infos = [(s, c, m) for s, c, m in all_results if s == "INFO"]
    errors = [(s, c, m) for s, c, m in all_results if s == "ERROR"]
    warnings = [(s, c, m) for s, c, m in all_results if s == "WARN"]

    # Summary — both CLAIMED (from INDEX ~Tokens column) and MEASURED (bytes/4).
    p0_claimed = sum(e["tokens"] for e in entries if e["priority"] == "P0")
    p0_count = sum(1 for e in entries if e["priority"] == "P0")
    p1_count = sum(1 for e in entries if e["priority"] == "P1")
    p2_count = sum(1 for e in entries if e["priority"] == "P2")
    p3_count = sum(1 for e in entries if e["priority"] == "P3")

    print(f"P0: {p0_count} files, claimed ~{p0_claimed} tokens (cap: {P0_TOKEN_CAP})")
    print(f"P1: {p1_count} files | P2: {p2_count} files (exempt) | P3: {p3_count} files (exempt)")

    if infos:
        for _, check, msg in infos:
            print(f"  INFO  [{check}] {msg}")

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
