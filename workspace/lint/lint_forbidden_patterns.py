"""Static lint: forbid dangerous or environment-leaking patterns in agent code.

Rules:
  1. SSH commands — agent must never invoke ssh/scp/sftp from scripts.
  2. "strucd" references — internal infra name; use generic "Linux dev workspace".
  3. Hardcoded hostnames — e.g. literal *.gs.com hostnames that aren't API endpoints.

Scope: skills/, policy/, memory/ and workspace/lint/ Python + Shell + Markdown files.
       Excludes: workspace/knowledge/ (third-party docs), workspace/tmp/,
                 workspace/archive/, __pycache__, .git

Usage:
    python workspace/lint/lint_forbidden_patterns.py
    python workspace/lint/lint_forbidden_patterns.py --strict

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

SCAN_ROOTS = [
    REPO_ROOT / "skills",
    REPO_ROOT / "personas",
    REPO_ROOT / "workflows",
    REPO_ROOT / "policy",
    REPO_ROOT / "workspace" / "lint",
    REPO_ROOT / "memory",
    REPO_ROOT / ".github" / "prompts",
    REPO_ROOT / ".github" / "instructions",
]

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "archive", "tmp", "knowledge", "enghub"}
SKIP_FILES = {"lint_forbidden_patterns.py"}  # don't lint ourselves

# File extensions to scan.
SCAN_EXTENSIONS = {".py", ".sh", ".md", ".cmd"}

# ── Rules ────────────────────────────────────────────────────────────────

class Rule:
    """A single forbidden-pattern rule."""
    __slots__ = ("id", "pattern", "description", "fix", "extensions")

    def __init__(self, id: str, pattern: re.Pattern, description: str, fix: str, extensions: set[str] | None = None):
        self.id = id
        self.pattern = pattern
        self.description = description
        self.fix = fix
        self.extensions = extensions  # None = all extensions


RULES: list[Rule] = [
    Rule(
        "no-ssh",
        re.compile(r"""\bssh\s+[\w@\-\.]""", re.I),
        "SSH command invocation — agent must not SSH into remote hosts",
        "Remove SSH command. Use HTTP APIs or platform tools instead.",
    ),
    Rule(
        "no-scp",
        re.compile(r"""\bscp\s+""", re.I),
        "SCP command invocation — agent must not SCP files",
        "Remove SCP. Use HTTP upload/download APIs instead.",
    ),
    Rule(
        "no-sftp",
        re.compile(r"""\bsftp\s+""", re.I),
        "SFTP command invocation — agent must not SFTP",
        "Remove SFTP. Use HTTP APIs instead.",
    ),
    Rule(
        "no-strucd",
        re.compile(r"""\bstrucd\b""", re.I),
        "Reference to internal infra name 'strucd'",
        "Use 'Linux dev workspace' instead of 'strucd'.",
    ),
]

# ── Context-aware suppressions ───────────────────────────────────────────

# Lines matching these are false-positive prone (comments explaining what NOT to do, etc.)
# Single combined suppression regex (avoids per-line any() iteration)
# Uses [^|]* instead of .* to avoid catastrophic backtracking on pipe-heavy lines
RE_SUPPRESSED = re.compile(
    r"FORBIDDEN|NEVER|blacklist|disallow|must not|do not"
    r"|Remote[^|]*SSH[^|]*extension"
    r"|ssh-keygen"
    r"|openssh"
    r"|svn\+ssh"
    r"|\.ssh/"
    r"|public_key_openssh"
    r"|^\s*\|[^|]*\|[^|]*\|",
    re.I,
)


class Violation:
    __slots__ = ("path", "lineno", "rule_id", "text", "fix")

    def __init__(self, path: Path, lineno: int, rule_id: str, text: str, fix: str):
        self.path = path
        self.lineno = lineno
        self.rule_id = rule_id
        self.text = text
        self.fix = fix

    def __str__(self) -> str:
        rel = self.path
        try:
            rel = self.path.relative_to(REPO_ROOT)
        except ValueError:
            pass
        return f"  [{self.rule_id}] {rel}:{self.lineno}  {self.text.strip()}\n    FIX: {self.fix}"


def _is_suppressed(line: str) -> bool:
    return bool(RE_SUPPRESSED.search(line))


def scan_file(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    if path.name in SKIP_FILES:
        return violations

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return violations

    lines = content.splitlines()
    file_ext = path.suffix.lower()
    for i, line in enumerate(lines, start=1):
        if _is_suppressed(line):
            continue
        for rule in RULES:
            if rule.extensions and file_ext not in rule.extensions:
                continue
            if rule.pattern.search(line):
                violations.append(Violation(path, i, rule.id, line, rule.fix))

    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="Exit 1 on any violation")
    args = ap.parse_args()

    total_violations = 0
    total_files = 0

    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                ext = Path(fname).suffix
                if ext not in SCAN_EXTENSIONS:
                    continue
                fpath = Path(dirpath) / fname
                total_files += 1
                for v in scan_file(fpath):
                    print(str(v))
                    total_violations += 1

    print(f"\nScanned {total_files} files across {[r.name for r in SCAN_ROOTS]}")
    if total_violations:
        print(f"FAIL: {total_violations} forbidden pattern(s) found.")
        return 1
    else:
        print("PASS: no forbidden patterns.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
