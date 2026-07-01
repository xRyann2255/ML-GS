"""Lint: find broken cross-references in Markdown files.

Detects reference patterns and checks that targets exist on disk:
  1. Markdown links:     [text](relative/path.md)     [text](path.md#anchor)
  2. #file: directives:  #file:../../../path/to/file.md   (GitHub Copilot prompt refs)
  3. Backtick file refs: `filename.md`  in tables/prose  (memory index, copilot-instructions)
  4. Prompt cross-refs:  [text](foo.prompt.md) inside .prompt.md — always broken
                         (VS Code prompts-diagnostics-provider can't resolve markdown links
                         to peer .prompt.md files; must use backtick-text format instead)

Scope:
  - memory/, skills/, policy/, personas/, workflows/
  - workspace/.github/copilot-instructions.md
  - workspace/.github/prompts/*.prompt.md
  - workspace/README.md  (if present)

Excludes: __pycache__, .git, node_modules, archive, tmp, knowledge, raw, enghub

Usage:
    python workspace/lint/lint_broken_refs.py
    python workspace/lint/lint_broken_refs.py --verbose

Exit code: 0 if all refs resolve, 1 if any broken.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterator

MAX_WORKERS = 4

# ── UTF-8 safety ─────────────────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ── Configuration ────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories to walk recursively for .md files.
SCAN_ROOTS = [
    REPO_ROOT / "memory",
    REPO_ROOT / "skills",
    REPO_ROOT / "policy",
    REPO_ROOT / "personas",
    REPO_ROOT / "workflows",
    REPO_ROOT / ".github" / "prompts",
    REPO_ROOT / ".github" / "instructions",
]

# Individual files to scan (outside the walked trees).
SCAN_FILES = [
    REPO_ROOT / "workspace" / "docs" / "slang" / "copilot-instructions.md",
    REPO_ROOT / "workspace" / "README.md",
    REPO_ROOT / "AGENTS.md",
]

SKIP_DIRS = frozenset({
    "__pycache__", ".git", "node_modules", "archive",
    "tmp", "knowledge", "raw", "enghub",
    "_archived", "_dormant",
})

# Directories whose .md files are cloned from external repos — skip backtick
# validation (internal cross-refs use the upstream repo's directory layout).
EXTERNAL_DOC_DIRS = frozenset({
    "docs",
})

# ── Regex patterns ───────────────────────────────────────────────────────

# Standard Markdown link: [text](target) — skip http/https/mailto/# anchors
_MD_LINK = re.compile(
    r"""\[(?P<text>[^\]]*)\]\((?P<target>[^)]+)\)""",
)

# #file: directive (GitHub Copilot prompt files)
_FILE_DIRECTIVE = re.compile(
    r"""^#file:(?P<target>\S+)""", re.MULTILINE,
)

# Backtick file reference: `something.md` — only match .md extensions
_BACKTICK_REF = re.compile(
    r"""`(?P<target>[A-Za-z0-9_\-./]+\.md)`""",
)

# Targets that are not file references — skip these.
_NON_FILE_PREFIX = re.compile(r"""^(https?://|mailto:|#|<|data:)""", re.I)

# Anchors: strip #fragment from path.
_ANCHOR = re.compile(r"""#.*$""")

# Inline code spans — used to strip before scanning for links/directives.
_INLINE_CODE = re.compile(r"""`[^`]+`""")


# ── Data ─────────────────────────────────────────────────────────────────

class BrokenRef:
    __slots__ = ("source", "lineno", "kind", "raw_target", "resolved")

    def __init__(self, source: Path, lineno: int, kind: str, raw_target: str, resolved: Path):
        self.source = source
        self.lineno = lineno
        self.kind = kind
        self.raw_target = raw_target
        self.resolved = resolved

    def __str__(self) -> str:
        rel_src = _rel(self.source)
        rel_tgt = _rel(self.resolved)
        return f"  [{self.kind}] {rel_src}:{self.lineno}  → {self.raw_target}  (resolved: {rel_tgt})"


def _rel(p: Path) -> Path:
    try:
        return p.relative_to(REPO_ROOT)
    except ValueError:
        return p


# ── Helpers ──────────────────────────────────────────────────────────────

def _strip_anchor(target: str) -> str:
    """Remove #fragment from a link target."""
    return _ANCHOR.sub("", target)


def _is_file_ref(target: str) -> bool:
    """Return True if target looks like a file path (not URL, anchor, etc.)."""
    if not target or _NON_FILE_PREFIX.match(target):
        return False
    # Pure anchors (#something) already excluded by prefix check.
    return True


def _is_external_doc(path: Path) -> bool:
    """True if *path* is inside a cloned external-docs tree (backtick refs not ours)."""
    try:
        rel = path.relative_to(REPO_ROOT / "workspace")
    except ValueError:
        return False
    return rel.parts[0] in EXTERNAL_DOC_DIRS if rel.parts else False


def _resolve(source_file: Path, target: str) -> Path:
    """Resolve a relative target path against the source file's directory."""
    return (source_file.parent / target).resolve()


# Patterns that indicate the backtick content is a description, not a file ref.
# e.g. `meta.guide.md` in a sentence is a ref; `example usage` is not.
_BACKTICK_KNOWN_EXTENSIONS = {".md"}

# Template / example patterns — not real file references.
_TEMPLATE_PATTERNS = re.compile(
    r"""(YYYY|XX|<[^>]+>|\bX\b)"""
)

# Bare-name exclusions: backtick references that look like file patterns
# but are templates, naming examples, or partial suffixes.
_BACKTICK_EXCLUSIONS = frozenset({
    ".prompt.md",       # suffix pattern, not a filename
    "domain.subject.md",  # CoALA naming template
})

# Lines containing these words discuss deleted/historical files or examples — suppress backtick checks.
_HISTORY_LINE = re.compile(
    r"""\b(Deleted|Removed|Archived|Deprecated|Absorbed|Migrated)\b|\bR\d+\s+found\b|(?:^|[\s,])e\.g\.""", re.I
)

# Lines that are naming examples / conventions — not real file references.
_NAMING_EXAMPLE_LINE = re.compile(
    r"""(naming|convention|example|specificity|date-stamped|format|multi-word|lowercase|\bWrong\b|\bCorrect\b)\b""", re.I
)

# Lines in documentation tables that contain *example* paths.
# Only suppress backtick-ref checks when the table row also contains template
# indicators (angle-bracket placeholders, naming examples, wildcards).
_EXAMPLE_TABLE_LINE = re.compile(
    r"""^\s*\|.*\|.*\|\s*$"""
)
_EXAMPLE_TABLE_INDICATOR = re.compile(
    r"""<[^>]+>|\bExample\b|\btemplate\b|\*\.md|domain\.subject|\bSame\s+template\b|\breserved\b|\bfuture\b|\bRepo\b|\bContent\b|\bOutput\b""", re.I
)


def _is_plausible_backtick_ref(target: str, source_file: Path) -> bool:
    """Heuristic: is this backtick content a plausible file reference?

    We only consider .md files.  Skip bare filenames that look like code
    identifiers (no dots, no slashes).  Also skip references that contain
    spaces — likely prose, not file paths.  Skip template patterns.
    Skip ephemeral workspace/tmp/ paths (created at runtime).
    """
    if " " in target:
        return False
    if _TEMPLATE_PATTERNS.search(target):
        return False
    if target in _BACKTICK_EXCLUSIONS:
        return False
    # Ephemeral paths — workspace/tmp/ files are created at runtime
    if target.startswith("workspace/tmp/"):
        return False
    if "/" in target or "\\" in target:
        return True  # Explicit path
    # Bare name — must end with .md
    suffix = Path(target).suffix
    return suffix in _BACKTICK_KNOWN_EXTENSIONS


# ── YAML frontmatter: relates field ──────────────────────────────────────

_FRONTMATTER_FENCE = re.compile(r"^---\s*$")


def _extract_relates(content: str) -> Iterator[tuple[int, str]]:
    """Yield (lineno, path) for each entry in a YAML `relates:` frontmatter field.

    Only parses the `---` fenced frontmatter block at the top of the file.
    Expects the simple list format::

        relates:
          - domain/foo.md
          - ref/bar.md
    """
    lines = content.splitlines()
    if not lines or not _FRONTMATTER_FENCE.match(lines[0]):
        return
    in_relates = False
    for i, line in enumerate(lines[1:], start=2):  # 1-indexed, skip opening ---
        if _FRONTMATTER_FENCE.match(line):
            break  # end of frontmatter
        stripped = line.strip()
        if stripped.startswith("relates:"):
            in_relates = True
            continue
        if in_relates:
            if stripped.startswith("- "):
                path_str = stripped[2:].strip()
                if path_str:
                    yield (i, path_str)
            elif stripped and not stripped.startswith("#"):
                in_relates = False  # new key started


# ── Scanning ─────────────────────────────────────────────────────────────

def _scan_file(path: Path) -> list[BrokenRef]:
    """Scan a single .md file for broken references."""
    broken: list[BrokenRef] = []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return broken

    # 0. YAML frontmatter: relates field (memory files only)
    if path.parts and "memory" in str(path):
        memory_root = REPO_ROOT / "memory"
        for lineno, rel_path in _extract_relates(content):
            resolved = (memory_root / rel_path).resolve()
            if not resolved.exists():
                broken.append(BrokenRef(path, lineno, "relates", rel_path, resolved))

    lines = content.splitlines()
    in_fence = False
    table_header = ""   # Current table's header row text
    prev_pipe_line = "" # Previous pipe-delimited line (candidate header)

    for i, line in enumerate(lines, start=1):
        # Track fenced code blocks — skip references inside them.
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # Track table context: when we see a separator row (|---|---|),
        # the previous pipe line was the header.
        if stripped.startswith("|"):
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                table_header = prev_pipe_line  # confirm header
            prev_pipe_line = stripped
        else:
            table_header = ""
            prev_pipe_line = ""

        # Quick reject: skip lines with no link-like characters
        has_md_link = "](" in line
        has_directive = line.lstrip().startswith("#file:")
        has_backtick = "`" in line
        if not (has_md_link or has_directive or has_backtick):
            continue

        # Strip inline code spans so examples like `[foo](path)` or
        # `#file:path` inside backticks are not treated as real refs.
        # Backtick-ref scanning (section 3) uses _BACKTICK_REF on the
        # original line, so we create a stripped copy for sections 1 & 2.
        scan_line = _INLINE_CODE.sub("", line) if has_backtick else line

        # 1. Markdown links
        is_prompt = path.name.endswith(".prompt.md")
        if "](" in scan_line:
            for m in _MD_LINK.finditer(scan_line):
                raw = m.group("target")
                target = _strip_anchor(raw).strip()
                if not _is_file_ref(target):
                    continue
                # Prompt files must not use markdown links to other .prompt.md files;
                # VS Code's prompts-diagnostics-provider can't resolve them.
                if is_prompt and target.endswith(".prompt.md"):
                    broken.append(BrokenRef(path, i, "prompt-link-in-prompt", raw,
                                            _resolve(path, target)))
                    continue
                # Decode percent-encoded spaces
                target = target.replace("%20", " ")
                resolved = _resolve(path, target)
                if not resolved.exists():
                    broken.append(BrokenRef(path, i, "md-link", raw, resolved))

        # 2. #file: directives
        #    Prompt files (.prompt.md) must NOT use #file: — use markdown links.
        #    Other files: resolve from file's parent dir.
        if scan_line.lstrip().startswith("#file:"):
            for m in _FILE_DIRECTIVE.finditer(scan_line):
                raw = m.group("target")
                target = _strip_anchor(raw).strip()
                if not _is_file_ref(target):
                    continue
                if is_prompt:
                    broken.append(BrokenRef(path, i, "#file-in-prompt", raw,
                                            path.parent / target))
                else:
                    resolved = _resolve(path, target)
                    if not resolved.exists():
                        broken.append(BrokenRef(path, i, "#file", raw, resolved))

        # 3. Backtick file refs — skip history/changelog lines, example table rows,
        #    and files inside cloned external doc trees.
        if has_backtick:
            if _is_external_doc(path):
                continue
            if _HISTORY_LINE.search(line) or _NAMING_EXAMPLE_LINE.search(line):
                continue
            # Skip table rows that are clearly examples/templates:
            # - Row itself has template indicators, OR
            # - Table header contains "Example" (reserved-domain example tables)
            if (_EXAMPLE_TABLE_LINE.match(line)
                    and line.count('|') >= 3
                    and (_EXAMPLE_TABLE_INDICATOR.search(line)
                         or _EXAMPLE_TABLE_INDICATOR.search(table_header))):
                continue
            for m in _BACKTICK_REF.finditer(line):
                raw = m.group("target")
                target = _strip_anchor(raw).strip()
                if not _is_plausible_backtick_ref(target, path):
                    continue
                # For bare filenames (no path separator), search in known locations
                if "/" not in target and "\\" not in target:
                    if not _resolve_bare_name(target):
                        broken.append(BrokenRef(path, i, "backtick", raw, _resolve(path, target)))
                else:
                    # Try relative to source file first, then repo root,
                    # then memory/ (cross-primitive shorthand like "person/user.md").
                    resolved = _resolve(path, target)
                    resolved_root = (REPO_ROOT / target).resolve()
                    resolved_memory = (REPO_ROOT / "memory" / target).resolve()
                    if not resolved.exists() and not resolved_root.exists() and not resolved_memory.exists():
                        broken.append(BrokenRef(path, i, "backtick", raw, resolved))

    return broken


# Cache of known .md files for bare-name resolution.
_KNOWN_MD_FILES: dict[str, Path] | None = None


def _build_known_md_index() -> dict[str, Path]:
    """Index all .md filenames under REPO_ROOT for bare-name lookup."""
    idx: dict[str, Path] = {}
    for root_dir in [
        REPO_ROOT / "memory",
        REPO_ROOT / "skills",
        REPO_ROOT / "policy",
        REPO_ROOT / "personas",
        REPO_ROOT / "workflows",
        REPO_ROOT / ".github",
        REPO_ROOT / "workspace",
    ]:
        if not root_dir.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if fname.endswith(".md"):
                    idx[fname] = Path(dirpath) / fname
    return idx


def _resolve_bare_name(name: str) -> bool:
    """Check if a bare filename like `meta.guide.md` exists anywhere in the repo."""
    global _KNOWN_MD_FILES
    if _KNOWN_MD_FILES is None:
        _KNOWN_MD_FILES = _build_known_md_index()
    return name in _KNOWN_MD_FILES


# ── Collect files ────────────────────────────────────────────────────────

def _collect_files() -> list[Path]:
    """Collect all .md files to scan."""
    files: list[Path] = []

    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if fname.endswith(".md"):
                    files.append(Path(dirpath) / fname)

    for f in SCAN_FILES:
        if f.is_file() and f not in files:
            files.append(f)

    return files


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--verbose", action="store_true", help="Show scanned file count and details")
    args = ap.parse_args()

    files = _collect_files()
    all_broken: list[BrokenRef] = []

    # Eagerly build the bare-name index before spawning threads
    global _KNOWN_MD_FILES
    if _KNOWN_MD_FILES is None:
        _KNOWN_MD_FILES = _build_known_md_index()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = pool.map(_scan_file, files)
        for broken in results:
            all_broken.extend(broken)
    total_broken = len(all_broken)

    # Print results
    if all_broken:
        # Group by source file for readability.
        by_file: dict[Path, list[BrokenRef]] = {}
        for b in all_broken:
            by_file.setdefault(b.source, []).append(b)

        for src in sorted(by_file):
            print(f"\n{_rel(src)}:")
            for b in sorted(by_file[src], key=lambda x: x.lineno):
                print(str(b))

    print(f"\nScanned {len(files)} Markdown files")
    if total_broken:
        print(f"FAIL: {total_broken} broken reference(s) found.")
        return 1
    else:
        print("PASS: all references resolve.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
