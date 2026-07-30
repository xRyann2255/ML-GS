"""
lint_vol_parity.py — ./vol dispatch arms <-> memory/ref/vol-cli.md parity (AW-55/G6/G16).

Rules:
  V1. Every case arm in vol's dispatch block has a row in vol-cli.md.
  V2. Every command documented in vol-cli.md is a real case arm.
  V3. Every case arm also appears in vol's help heredoc (self-consistency).
vol is parsed as TEXT (never executed — it exits 2 off-Linux by design, Plan 03).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VOL = REPO_ROOT / "vol"
DOC = REPO_ROOT / "memory" / "ref" / "vol-cli.md"
# case arms:   two spaces/tab indent, token(s), ')' — e.g. "  test|testlf)"
CASE_ARM = re.compile(r"^\s{2,}([a-z][a-z0-9_|-]*)\)\s*(?:#.*)?$", re.MULTILINE)
# doc rows:    | `vol <command> ...` | description |
# NOTE (anchor delta vs Plan 04 §5 Task 7 Step 1 spec): live vol-cli.md rows carry
# the `vol ` prefix inside the backticks (e.g. "| `vol test-all [args]` | …"). The
# spec's `^\|\s*`([a-z][a-z0-9-]*)` would capture "vol" for every row and produce
# spurious [doc-phantom] noise. Anchor the regex on the literal `vol ` prefix and
# capture the subcommand token that follows.
DOC_CMD = re.compile(r"^\|\s*`vol\s+([a-z][a-z0-9-]*)", re.MULTILINE)
IGNORE_ARMS = {"help", "-h", "--help"}  # help documents itself


def vol_case_arms(text: str) -> set[str]:
    arms: set[str] = set()
    for m in CASE_ARM.finditer(text):
        for tok in m.group(1).split("|"):
            if tok and tok not in IGNORE_ARMS and not tok.startswith("-"):
                arms.add(tok)
    return arms


def help_commands(text: str) -> set[str]:
    # help heredoc lines look like "  test [args]      Run pytest …"
    out: set[str] = set()
    m = re.search(r"<<\s*'?EOF'?\s*\n(.*?)\nEOF", text, re.DOTALL)
    block = m.group(1) if m else text
    for line in block.splitlines():
        lm = re.match(r"^\s{2}([a-z][a-z0-9-]*)\b", line)
        if lm:
            out.add(lm.group(1))
    return out


def main() -> int:
    if not VOL.is_file() or not DOC.is_file():
        print("  ERROR [missing] vol or vol-cli.md not found")
        return 1
    vol_text = VOL.read_text(encoding="utf-8", errors="replace")
    doc_text = DOC.read_text(encoding="utf-8", errors="replace")
    arms = vol_case_arms(vol_text)
    doc_cmds = {c for c in (m.group(1) for m in DOC_CMD.finditer(doc_text))
                if c not in IGNORE_ARMS}
    help_cmds = help_commands(vol_text)
    if len(arms) < 20:
        print(f"  ERROR [parse] only {len(arms)} case arms parsed from vol — "
              f"the dispatch-block regex anchor has drifted; fix CASE_ARM")
        return 1
    errors: list[str] = []
    for c in sorted(arms - doc_cmds):
        errors.append(f"[doc-missing] vol arm '{c}' has no row in memory/ref/vol-cli.md")
    for c in sorted(doc_cmds - arms):
        errors.append(f"[doc-phantom] vol-cli.md documents '{c}' but vol has no such arm")
    for c in sorted(arms - help_cmds):
        errors.append(f"[help-missing] vol arm '{c}' absent from vol's own help heredoc")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {len(arms)} vol commands in full parity with vol-cli.md and vol help.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
