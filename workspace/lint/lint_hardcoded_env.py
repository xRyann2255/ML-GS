"""Static lint: detect hardcoded environment values in skill scripts.

Catches:
  1. Hardcoded kerberos IDs (e.g. literal 'piresm' outside examples/help text)
  2. Hardcoded DB names  (e.g. 'SPGProdNYC RO', '!NYC_CoreData')
  3. Hardcoded DB paths  (e.g. '!NYC UserDBs!home!piresm')

These should come from entity.user.md or CLI arguments, never from literals.

Usage:
    python workspace/lint/lint_hardcoded_env.py
    python workspace/lint/lint_hardcoded_env.py --strict   # non-zero exit on warn
    python workspace/lint/lint_hardcoded_env.py --fix       # show suggested fixes

Returns exit code 0 on pass, 1 on violation.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


# ── Configuration ────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO_ROOT / "skills"
LINT_ROOT = REPO_ROOT / "workspace" / "lint"
SCAN_ROOTS = [SKILLS_ROOT, LINT_ROOT]

# Directories to skip.
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "archive"}

# This lint tool's own config patterns should not flag themselves.
SELF_SKIP = {"lint_hardcoded_env.py", "lint_doc_safety.py"}

# ── Violation definitions ────────────────────────────────────────────────

# Kerberos IDs that should never appear as hardcoded literals.
# Read from entity.user.md at scan time; fallback to this list.
_KNOWN_KERBEROS = {"piresm"}

# Hardcoded DB names / paths.  Keys = pattern, Values = description.
HARDCODED_DB_PATTERNS: dict[re.Pattern, str] = {
    re.compile(r"""['"]!NYC_CoreData['"]"""): "hardcoded session DB '!NYC_CoreData'",
    re.compile(r"""['"]SPGProdNYC\s+RO['"]"""): "hardcoded object DB 'SPGProdNYC RO'",
    re.compile(r"""['"]!NYC UserDBs!home!\w+['"]"""): "hardcoded user DB path",
    re.compile(r"""['"]RegTest Scratch['"]"""): "hardcoded scratch DB 'RegTest Scratch'",
}

# ── Context-aware suppressions ───────────────────────────────────────────

# Single combined regex for suppression (avoids per-line any() iteration).
RE_SUPPRESSED = re.compile(
    r"^\s*#"              # comments
    r"|^\s*['\"]"         # docstring/string boundaries (start of line)
    r"|\bhelp\s*="        # argparse help strings
    r"|\be\.g\."          # "e.g." examples
    r"|\bExample"         # Example text
    r"|\bDEFAULT_",       # DEFAULT_FOO = "..." (named defaults are OK)
    re.I,
)


class Violation:
    __slots__ = ("path", "lineno", "category", "text", "suggestion")

    def __init__(self, path: Path, lineno: int, category: str, text: str, suggestion: str = ""):
        self.path = path
        self.lineno = lineno
        self.category = category
        self.text = text
        self.suggestion = suggestion

    def __str__(self) -> str:
        rel = self.path
        try:
            rel = self.path.relative_to(REPO_ROOT)
        except ValueError:
            pass
        s = f"  [{self.category}] {rel}:{self.lineno}  {self.text.strip()}"
        if self.suggestion:
            s += f"\n    FIX: {self.suggestion}"
        return s


def _load_kerberos_ids() -> set[str]:
    """Try to read kerberos from person/user.md or the USERNAME env var."""
    ids = set(_KNOWN_KERBEROS)
    user_path = REPO_ROOT / "memory" / "person" / "user.md"
    if user_path.is_file():
        content = user_path.read_text(encoding="utf-8", errors="replace")
        # Try table format:  kerberos | value
        m = re.search(r"kerberos\s*\|\s*(\w+)", content)
        if m:
            ids.add(m.group(1))
        # Try YAML frontmatter: kerberos: value
        m = re.search(r"^kerberos:\s*(\w+)", content, re.MULTILINE)
        if m:
            ids.add(m.group(1))
    # Also pick up the Windows username (often matches kerberos)
    username = os.environ.get("USERNAME", "").lower()
    if username and len(username) >= 3:
        ids.add(username)
    return ids


# Pre-compiled noqa check
RE_NOQA = re.compile(r"#\s*noqa\b")


def _is_suppressed(line: str) -> bool:
    return bool(RE_SUPPRESSED.search(line)) or bool(RE_NOQA.search(line))


def _build_kerberos_patterns(kerberos_ids: set[str]) -> list[tuple[re.Pattern, re.Pattern]]:
    """Pre-compile kerberos patterns once, not per-line."""
    pats = []
    for kid in kerberos_ids:
        escaped = re.escape(kid)
        string_pat = re.compile(rf"""(['"])(?:[^'"]*\b{escaped}\b[^'"]*)\1""")
        home_pat = re.compile(rf"""!home!{escaped}""")
        pats.append((string_pat, home_pat))
    return pats


# Pre-compile all DB patterns into a single combined regex for fast rejection
RE_ANY_DB = re.compile(
    r"!NYC_CoreData|SPGProdNYC\s+RO|!NYC UserDBs!home!\w+|RegTest Scratch",
    re.I,
)


def scan_file(path: Path, kerberos_ids: set[str],
              kerberos_pats: list[tuple[re.Pattern, re.Pattern]]) -> list[Violation]:
    violations: list[Violation] = []
    filename = path.name

    # Don't lint ourselves.
    if filename in SELF_SKIP:
        return violations

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return violations

    lines = content.splitlines()
    in_docstring = False

    for i, line in enumerate(lines, start=1):
        # Track docstring state (triple-quote toggle).
        count = line.count('"""') + line.count("'''")
        if count % 2 == 1:
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if _is_suppressed(line):
            continue

        # Rule 1: Hardcoded kerberos in string literals (pre-compiled patterns)
        for str_pat, home_pat in kerberos_pats:
            if str_pat.search(line) and home_pat.search(line):
                violations.append(Violation(
                    path, i, "hardcoded-kerberos",
                    line.rstrip(),
                    "Read kerberos from entity.user.md or accept via --db CLI arg",
                ))

        # Rule 2: Hardcoded DB names/paths — quick reject first
        if RE_ANY_DB.search(line):
            for pat, desc in HARDCODED_DB_PATTERNS.items():
                if pat.search(line):
                    violations.append(Violation(
                        path, i, "hardcoded-db",
                        line.rstrip(),
                        f"{desc} — use CLI arg or DEFAULT_ constant",
                    ))

    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="Exit 1 on any warning")
    ap.add_argument("--fix", action="store_true", help="Show suggested fixes")
    ap.add_argument("--root", type=Path, nargs="*", default=None,
                    help="Roots to scan (default: skills + tools)")
    args = ap.parse_args()

    roots = [Path(r) for r in args.root] if args.root else SCAN_ROOTS
    kerberos_ids = _load_kerberos_ids()
    kerberos_pats = _build_kerberos_patterns(kerberos_ids)

    total_violations = 0
    total_files = 0

    for root in roots:
        if not root.is_dir():
            print(f"WARN: {root} is not a directory, skipping", file=sys.stderr)
            continue

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                fpath = Path(dirpath) / fname
                total_files += 1
                violations = scan_file(fpath, kerberos_ids, kerberos_pats)
                for v in violations:
                    if args.fix:
                        print(str(v))
                    else:
                        # Suppress suggestion line
                        rel = fpath
                        try:
                            rel = fpath.relative_to(REPO_ROOT)
                        except ValueError:
                            pass
                        print(f"  VIOLATION [{v.category}] {rel}:{v.lineno}  {v.text.strip()}")
                    total_violations += 1

    print(f"\nScanned {total_files} Python files")
    print(f"Kerberos IDs checked: {sorted(kerberos_ids)}")
    if total_violations:
        print(f"FAIL: {total_violations} violation(s) found.")
        return 1
    else:
        print("PASS: no hardcoded environment values.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
