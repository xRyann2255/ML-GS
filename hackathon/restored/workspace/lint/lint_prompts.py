"""
lint_prompts.py — Prompt-layer hygiene (AW-11/23/37/43 halves; Plan 07's gate).

Rules:
  P1. Filenames match ^[a-z0-9-]+\\.prompt\\.md$ (no spaces — AW-37).
  P2. If .github/prompts/INDEX.md exists: bijection — every prompt has a row,
      every row's prompt exists. (Activates when Plan 07 lands INDEX.md.)
  P3. Every prompt body (post-frontmatter) contains at least one instruction
      verb — bare backtick context paths alone are NOT auto-injected (AW-11).
  P4. Frontmatter 'model:' (when present) == lint_model_pins.EXPECTED_MODEL.
Whitelist: whitelists/prompts.txt grandfathers pre-Plan-07 violations (only shrinks).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Make the sibling module importable regardless of cwd (lint_all.py invokes as
# a subprocess with cwd=repo_root; direct invocation may not have this dir on
# sys.path). This mirrors the pattern needed by any script that imports peers.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lint_model_pins import EXPECTED_MODEL  # single source of truth (wfo-04-5)  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS = REPO_ROOT / ".github" / "prompts"
WHITELIST = Path(__file__).resolve().parent / "whitelists" / "prompts.txt"
FNAME = re.compile(r"^[a-z0-9-]+\.prompt\.md$")
VERB = re.compile(
    r"\b(read|run|load|execute|follow|use|apply|check|review|generate|write|"
    r"report|analyze|analyse|inspect|summarize|produce|update|create|fix|"
    r"validate|verify|list|search|open)\b", re.IGNORECASE)
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
FM_MODEL = re.compile(r"^model:\s*(.+?)\s*$", re.MULTILINE)
INDEX_ROW = re.compile(r"^\|\s*`?/?([a-z0-9 -]+?)`?\s*\|", re.MULTILINE)


def load_whitelist() -> set[str]:
    if not WHITELIST.is_file():
        return set()
    return {line.strip() for line in WHITELIST.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


def main() -> int:
    wl = load_whitelist()
    errors: list[str] = []
    notices: list[str] = []
    prompt_files = sorted(p for p in PROMPTS.glob("*.prompt.md"))
    stems: set[str] = set()
    for p in prompt_files:
        name = p.name
        stems.add(name[: -len(".prompt.md")])
        wl_hit = name in wl
        if not FNAME.match(name) and not wl_hit:
            errors.append(f"[filename] '{name}' violates ^[a-z0-9-]+\\.prompt\\.md$")
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = FRONTMATTER.match(text)
        body = text[fm.end():] if fm else text
        if fm:
            for m in FM_MODEL.finditer(fm.group(1)):
                val = m.group(1).strip().strip("'\"")
                if val != EXPECTED_MODEL:
                    errors.append(f"[pin-mismatch] {name}: model '{val}' != "
                                  f"'{EXPECTED_MODEL}'")  # never whitelisted
        if not VERB.search(body) and not wl_hit:
            errors.append(f"[no-verb] {name}: body has no instruction verb — "
                          f"backtick paths are not auto-injected (AW-11)")
    index = PROMPTS / "INDEX.md"
    if index.is_file():
        rows = {m.group(1).strip().replace(" ", "-")
                for m in INDEX_ROW.finditer(index.read_text(encoding="utf-8"))}
        rows.discard("prompt")  # header row
        for s in sorted(stems - rows):
            errors.append(f"[index-missing] {s}.prompt.md has no INDEX.md row")
        for r in sorted(rows - stems):
            errors.append(f"[index-phantom] INDEX.md row '{r}' has no prompt file")
    else:
        notices.append("[index] .github/prompts/INDEX.md absent — bijection check "
                       "activates when Plan 07 lands it")
    for n in notices:
        print(f"  NOTICE {n}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {len(prompt_files)} prompts hygienic "
          f"({len(wl)} grandfathered until Plan 07).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
