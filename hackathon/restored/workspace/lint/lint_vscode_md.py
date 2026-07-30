"""Lint: validate all workspace .md files for VS Code compatibility.

Scans every .md file in the repo (excluding workspace/tmp, workspace/docs,
workspace/knowledge) for issues that trigger VS Code warnings or indicate
encoding corruption:

  1. Mojibake           — double/triple-encoded UTF-8 via CP1252 (garbled chars).
  2. #file references   — #file: directives pointing to non-existent paths, or
                          #file: usage in .prompt.md files (must use backtick text).
  3. Broken links       — markdown links [text](path) where path doesn't exist.
  4. Non-UTF-8          — files that can't be read as UTF-8 at all.
  5. Relative links     — [text](../path) that VS Code can't resolve in SKILL.md
                          or .prompt.md (diagnostics provider can't verify traversal).
  6. Anchor fragments   — [text](path.md#anchor) where VS Code treats # as filename.
  7. SKILL.md frontmatter — unsupported YAML attributes (SKILL.md files only).
  8. Prompt cross-refs  — [text](foo.prompt.md) in .prompt.md files; must use backtick text.

Usage:
    python workspace/lint/lint_vscode_md.py
    python workspace/lint/lint_vscode_md.py --fix   # auto-fix mojibake, relative links, anchors

Exit code: 0 if pass, 1 on violations.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Ensure UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

# Directory names to skip entirely during walk (set for O(1) lookup)
SKIP_DIRS = frozenset({"tmp", "docs", "knowledge", "node_modules", ".git"})

# ── Pre-compiled patterns ─────────────────────────────────────────────────
# Mojibake: double/triple-encoded UTF-8 read through CP1252.
#
# When a UTF-8 byte sequence is misread as CP1252, each byte becomes a
# separate Unicode character.  The continuation bytes 0x80-0xBF map to
# a known set of Unicode codepoints via CP1252.  We compute this set
# generically from the codec so it's always complete.
#
# We detect: â + CONT + CONT  (3-byte mojibake, e.g. â—„ = U+25C4)
#            â + CONT          (partial 3-byte or split sequence)
#            Â/Ã + CONT        (2-byte mojibake, e.g. Ã© = é misread)
#            bare C1 controls  (U+0080-U+009F, never valid in text)

def _build_cp1252_charclass() -> str:
    """Compute chars that CP1252 maps bytes 0x80-0xBF to, for regex [...]."""
    chars: list[str] = []
    for b in range(0x80, 0xC0):
        try:
            chars.append(bytes([b]).decode("cp1252"))
        except UnicodeDecodeError:
            pass  # 0x81, 0x8D, 0x8F, 0x90, 0x9D are undefined in CP1252
    return "".join(chars)

_C = _build_cp1252_charclass()

RE_MOJIBAKE = re.compile(
    rf"\u00e2[{_C}][{_C}]"     # 3-byte: â + cont + cont  (e.g. â€" â€ž â—„)
    rf"|\u00e2[{_C}]"          # partial 3-byte: â + cont  (e.g. â€ from split seq)
    rf"|[\u00c2\u00c3][{_C}]"  # 2-byte: Â/Ã + cont       (e.g. Ã© Â© Ã¼)
    r"|[\u0080-\u009f]"         # bare C1 control characters
)

# #file: directive (applied per-line, anchored)
RE_FILE_DIRECTIVE = re.compile(r"^#file:(.+)$")

# Markdown link: [text](path) — reject http/https/mailto early via negative lookahead
RE_MD_LINK = re.compile(r"\[([^\]]*)\]\((?!https?://|mailto:)([^)]+)\)")

# Relative-path link: [text](../something) — VS Code can't resolve these
RE_RELATIVE_LINK = re.compile(r"\[([^\]]*)\]\((\.\./[^)]+)\)")

# Anchor fragment in any markdown link: [text](path.md#anchor)
RE_ANCHOR_LINK = re.compile(r"\[([^\]]*)]\(([^)]*\.md)#([^)]+)\)")

# Inline code spans — pre-compiled for stripping
RE_INLINE_CODE = re.compile(r"`[^`]+`")

# YAML frontmatter block
RE_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Absolute path prefixes to skip in link checking (tuple for str.startswith)
_ABS_PREFIXES = ("/", "h:", "H:", "C:", "c:")

# ── SKILL.md-specific constants ───────────────────────────────────────────
# Supported frontmatter attributes (from VS Code SKILL.md validator)
SUPPORTED_SKILL_ATTRS = {
    "argument-hint",
    "compatibility",
    "description",
    "disable-model-invocation",
    "license",
    "metadata",
    "name",
    "user-invocable",
}

MAX_WORKERS = 4
MAX_MOJIBAKE_REPORTED = 5


class Violation:
    __slots__ = ("severity", "rule", "file", "line", "message")

    def __init__(self, severity: str, rule: str, file: str, line: int, message: str):
        self.severity = severity
        self.rule = rule
        self.file = file
        self.line = line
        self.message = message

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"  [{self.severity}] {self.rule}: {loc}\n         {self.message}"


def _collect_md_files(root: Path) -> list[Path]:
    """Walk the tree with os.walk for speed, pruning skip dirs in-place."""
    root_str = str(root)
    result: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root_str):
        # Prune skipped directories in-place (prevents os.walk from descending)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if fname.endswith(".md"):
                result.append(Path(dirpath, fname))
    result.sort()
    return result


def _parse_fm_keys(text: str) -> list[tuple[int, str]]:
    """Return list of (line_number, key_name) from YAML frontmatter."""
    m = RE_FRONTMATTER.match(text)
    if not m:
        return []
    fm_text = m.group(1)
    keys: list[tuple[int, str]] = []
    for i, raw_line in enumerate(fm_text.splitlines(), start=2):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Indented line = continuation of previous multi-line value
        if raw_line[0:1] in (" ", "\t"):
            continue
        if ":" in line:
            key = line.partition(":")[0].strip()
            keys.append((i, key))
    return keys


def _fix_mojibake_line(line: str) -> str:
    """Try to reverse one layer of cp1252 double-encoding on a line."""
    try:
        return line.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return line


def validate_file(md_path: Path, fix: bool = False) -> list[Violation]:
    """Validate a single .md file in a single pass over all lines."""
    vs: list[Violation] = []
    rel_str = md_path.relative_to(REPO_ROOT).as_posix()
    parent = md_path.parent
    is_skill_md = md_path.name == "SKILL.md"
    is_prompt_md = md_path.name.endswith(".prompt.md")

    # ── Read file ────────────────────────────────────────────────────────
    try:
        text = md_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        vs.append(Violation("ERROR", "encoding", rel_str, 0,
                            "File is not valid UTF-8."))
        return vs

    # ── Rule 7: SKILL.md frontmatter (before line scan) ─────────────────
    if is_skill_md:
        for line_no, key in _parse_fm_keys(text):
            if key not in SUPPORTED_SKILL_ATTRS:
                vs.append(Violation("ERROR", "unsupported-attr", rel_str, line_no,
                                    f"Unsupported frontmatter attribute '{key}'. "
                                    f"Supported: {', '.join(sorted(SUPPORTED_SKILL_ATTRS))}."))

    lines = text.split("\n")
    in_code_block = False
    mojibake_lines: list[int] = []

    # ── Single pass over all lines ───────────────────────────────────────
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track fenced code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        # Rule 1: Mojibake — check every line (even inside code blocks,
        # mojibake is never intentional)
        if RE_MOJIBAKE.search(line):
            if len(mojibake_lines) < MAX_MOJIBAKE_REPORTED:
                m = RE_MOJIBAKE.search(line)
                assert m is not None
                snippet = m.group()
                s = max(0, m.start() - 15)
                e = min(len(line), m.end() + 15)
                vs.append(Violation("ERROR", "mojibake", rel_str, i,
                                    f"Garbled character(s) {snippet!r} -- context: {line[s:e]!r}"))
            mojibake_lines.append(i)

        if in_code_block:
            continue

        # Rule 2: #file: directives
        # VS Code's prompts-diagnostics-provider cannot reliably resolve
        # #file: paths in .prompt.md files (it resolves file-relative but
        # then fails existence checks for ../traversal paths).
        # Use markdown links [text](../../path) instead, which VS Code
        # also treats as context references in prompt files.
        if stripped.startswith("#file:"):
            m_dir = RE_FILE_DIRECTIVE.match(stripped)
            if m_dir:
                ref_path = m_dir.group(1).strip()
                if is_prompt_md:
                    # Prompt files must NOT use #file: — use markdown links
                    vs.append(Violation("ERROR", "file-ref-in-prompt", rel_str, i,
                                        f"#file:{ref_path} -- .prompt.md files must use "
                                        f"markdown links [text](../../path) instead of "
                                        f"#file: to avoid prompts-diagnostics-provider warnings."))
                else:
                    # Non-prompt files: resolve from file's parent dir
                    target = parent / ref_path
                    if not target.resolve().is_file():
                        vs.append(Violation("ERROR", "file-ref", rel_str, i,
                                            f"#file:{ref_path} -- target not found"))

        # Rule 5: Relative-path links — only in SKILL.md (VS Code skill limitation)
        if is_skill_md and "../" in line:
            for m_rel in RE_RELATIVE_LINK.finditer(line):
                display, target = m_rel.group(1), m_rel.group(2)
                vs.append(Violation("ERROR", "relative-link", rel_str, i,
                                    f"Relative-path link [{display}]({target}) -- "
                                    f"VS Code can't resolve '../' paths. Use plain text."))

        # Rule 5b: Traversal links in .prompt.md — provider can't verify them
        if is_prompt_md and "../" in line:
            for m_rel in RE_RELATIVE_LINK.finditer(line):
                display, target = m_rel.group(1), m_rel.group(2)
                vs.append(Violation("ERROR", "traversal-link-in-prompt", rel_str, i,
                                    f"Traversal link [{display}]({target}) -- "
                                    f"prompts-diagnostics-provider can't verify ../. "
                                    f"Use backtick text: - `{display}`."))

        # Rule 5c: Markdown links to .prompt.md files inside .prompt.md
        # The diagnostics provider may fail to resolve peer prompt refs
        # via markdown links. Use backtick-text format instead.
        if is_prompt_md and ".prompt.md" in line and "](" in line:
            check_prompt_line = RE_INLINE_CODE.sub("", line)
            for m_pr in RE_MD_LINK.finditer(check_prompt_line):
                pr_target = m_pr.group(2)
                if pr_target.endswith(".prompt.md"):
                    vs.append(Violation("ERROR", "prompt-link-in-prompt", rel_str, i,
                                        f"Markdown link to prompt file [{m_pr.group(1)}]"
                                        f"({pr_target}) -- use backtick-text format: "
                                        f"- `{pr_target}`."))

        # Rule 6: Anchor fragments — only in SKILL.md (VS Code skill limitation)
        if is_skill_md and ".md#" in line:
            for m_anc in RE_ANCHOR_LINK.finditer(line):
                display, path, anchor = m_anc.group(1), m_anc.group(2), m_anc.group(3)
                vs.append(Violation("ERROR", "anchor-fragment", rel_str, i,
                                    f"Anchor fragment [{display}]({path}#{anchor}) -- "
                                    f"VS Code treats '#' as part of filename. Remove anchor."))

        # Rule 3: Broken markdown links
        # Quick reject: skip lines without ]( to avoid regex on most lines
        if "](" not in line:
            continue
        check_line = RE_INLINE_CODE.sub("", line)
        for m_link in RE_MD_LINK.finditer(check_line):
            target_raw = m_link.group(2)
            if target_raw.startswith(_ABS_PREFIXES):
                continue
            target_path_str = target_raw.split("#")[0]
            if not target_path_str:
                continue
            target = parent / target_path_str
            try:
                resolved = target.resolve()
            except (OSError, ValueError):
                continue
            if not resolved.is_file() and not resolved.is_dir():
                vs.append(Violation("WARN", "broken-link", rel_str, i,
                                    f"Link [{m_link.group(1)}]({target_raw}) -- "
                                    f"target not found: {resolved}"))

    # Mojibake overflow summary
    if len(mojibake_lines) > MAX_MOJIBAKE_REPORTED:
        vs.append(Violation("ERROR", "mojibake", rel_str, 0,
                            f"... and {len(mojibake_lines) - MAX_MOJIBAKE_REPORTED} "
                            f"more line(s) with mojibake."))

    # ── Auto-fix: mojibake ───────────────────────────────────────────────
    if fix and mojibake_lines:
        mojibake_set = frozenset(mojibake_lines)
        new_lines = []
        fixed_count = 0
        for idx, line in enumerate(lines):
            if (idx + 1) in mojibake_set:
                new_line = _fix_mojibake_line(line)
                if new_line != line:
                    fixed_count += 1
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        if fixed_count > 0:
            md_path.write_text("\n".join(new_lines), encoding="utf-8")
            vs.append(Violation("WARN", "auto-fix", rel_str, 0,
                                f"Fixed mojibake on {fixed_count} line(s) via cp1252 reversal."))
            # Re-read for subsequent fixes
            text = md_path.read_text(encoding="utf-8")

    # ── Auto-fix: relative links & anchor fragments ──────────────────────
    if fix:
        new_text = text
        link_fixes = 0

        # [display](../path) → display (plain text)
        def _strip_rel_link(m: re.Match[str]) -> str:
            return m.group(1)
        new_text, n = RE_RELATIVE_LINK.subn(_strip_rel_link, new_text)
        link_fixes += n

        # [text](path.md#anchor) → [text](path.md)
        def _strip_anchor(m: re.Match[str]) -> str:
            return f"[{m.group(1)}]({m.group(2)})"
        new_text, n = RE_ANCHOR_LINK.subn(_strip_anchor, new_text)
        link_fixes += n

        if new_text != text:
            md_path.write_text(new_text, encoding="utf-8")
            vs.append(Violation("WARN", "auto-fix", rel_str, 0,
                                f"Fixed {link_fixes} link issue(s)."))

    return vs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=REPO_ROOT,
                    help="Repository root directory")
    ap.add_argument("--fix", action="store_true",
                    help="Auto-fix mojibake via cp1252 reversal")
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"Root not found: {args.root}")
        return 1

    md_files = _collect_md_files(args.root)

    all_violations: list[Violation] = []
    files_with_errors = 0

    if args.fix:
        # Sequential when writing files
        for md in md_files:
            file_vs = validate_file(md, fix=True)
            if file_vs:
                files_with_errors += 1
                all_violations.extend(file_vs)
    else:
        # Parallel read-only validation
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            for file_vs in pool.map(validate_file, md_files):
                if file_vs:
                    files_with_errors += 1
                    all_violations.extend(file_vs)

    errors = [v for v in all_violations if v.severity == "ERROR"]
    warns = [v for v in all_violations if v.severity == "WARN"]

    for v in all_violations:
        print(v)

    print(f"\nScanned {len(md_files)} .md file(s) in {args.root}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warns)} warning(s) "
              f"across {files_with_errors} file(s).")
        return 1
    if warns:
        print(f"PASS (with {len(warns)} warning(s))")
        return 0
    print("PASS: all .md files are clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
