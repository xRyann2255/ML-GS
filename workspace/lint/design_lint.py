"""Design Lint — enforce design.md architectural rules.

Implements the check categories defined in design.md §Design Lint:

  1. Structural   — valid root dirs, required dirs present, no misplaced files
  2. Skill size   — SKILL.md files: WARN ≥250 lines, ERROR ≥400 lines
  3. Skill refs   — SKILL.md files >80 lines must have ≥1 link to memory/
  4. CoALA shape  — memory files must have all 6 required sections (WARN)
  5. Persona purity — no large inline code blocks, no src/ path embeds
  6. Policy purity  — no code blocks >10 lines, no skills/src/ references
  7. Dependency dir — skills/ never links to personas/ or policy/
  8. Section design — section design.md files have required headings + line budget
  9. Memory domains — every memory/ subfolder is a recognized domain from meta/guide.md
 10. Memory INDEX coverage — every memory file on disk has an INDEX.md entry, and vice versa
 11. Workflow transition precedence — §4.2: transition tables with overlapping conditions must declare precedence
 12. Persona INDEX entry — personas/design.md §4.1: every persona file has an INDEX.md row
 13. Persona read-only decl — personas/design.md §4.5: read-only personas declare write tools blocked
 14. Persona effort gate — personas/design.md §3: every persona has <effort_gate>
 15. Persona verification loop — personas/design.md §3: every <execution_loop> has <verification_loop>
 16. Persona cross-dispatch — personas/design.md §4: no "route to X" dispatch in persona files
 17. Persona read-only tools — personas/design.md §4.5: read-only persona tool lists exclude write tools
 18. Workflow protocol ref — workflows/design.md §4.1: first paragraph references _protocol.md
 19. Workflow state machine — workflows/design.md §4.2: state machine with named states present
 20. Workflow INDEX entry — workflows/design.md §4.10: every workflow in INDEX.md quick-ref table
 21. Session-state enum — session-state.md active_workflow enum matches workflow file list
 22. Workflow skill names — workflows/design.md §4.7: no concrete skill names in workflow phases
 23. Workflow tool flags — workflows/design.md §4.7: no tool flags/CLI details in workflows
 24. Persona frontmatter — personas/design.md §3: frontmatter 'description' required
 25. Broken links — cross-primitive: relative markdown links resolve to actual files
 26. Workspace structure — design.md §Workspace Structure: required workspace/ subdirs present

Usage:
    python workspace/lint/design_lint.py
    python workspace/lint/design_lint.py --strict              # treat WARNs as ERRORs
    python workspace/lint/design_lint.py --category structural  # maintain-safe checks only
    python workspace/lint/design_lint.py --category compliance  # cure-domain checks only

Categories:
    structural  — mechanical format/structure checks (safe for housekeep.md to act on)
    compliance  — design-boundary and purity checks (require cure.md DOCTOR + TRIAGE)

Exit code: 0 if no ERRORs, 1 on any violation.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading
import time

# Ensure UTF-8 output on Windows consoles (avoids cp1252 encode errors)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass  # older Python or non-reconfigurable stream

MAX_WORKERS = 4


# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent          # workspace/lint/
REPO_ROOT   = SCRIPT_DIR.parents[1]                   # repo root

# ── File / directory cache ────────────────────────────────────────────────────
# All .md files are read once during warm-up; checks use in-memory data only.
_file_cache: dict[Path, str] = {}
_glob_cache: dict[tuple[Path, str, bool], list[Path]] = {}


def _read_cached(p: Path) -> str:
    """Return file text from cache (populated during warm-up)."""
    if p not in _file_cache:
        _file_cache[p] = p.read_text(encoding="utf-8", errors="replace")
    return _file_cache[p]


def _glob_cached(root: Path, pattern: str, *, recursive: bool = False) -> list[Path]:
    """Return sorted glob results from cache."""
    key = (root, pattern, recursive)
    if key not in _glob_cache:
        _glob_cache[key] = sorted(root.rglob(pattern) if recursive else root.glob(pattern))
    return _glob_cache[key]


def _warm_cache() -> None:
    """Pre-read all .md files in the five primitives + workspace/lint.

    Runs single-threaded so filesystem I/O is sequential (no contention on
    network drives).  After this, every check function hits only in-memory data.
    """
    scan_dirs = ["personas", "workflows", "policy", "skills", "memory"]
    for d in scan_dirs:
        root = REPO_ROOT / d
        if not root.is_dir():
            continue
        for md in _glob_cached(root, "*.md", recursive=True):
            _read_cached(md)

REQUIRED_ROOT_DIRS = {"skills", "memory", "personas", "workflows", "policy", "workspace"}
ALLOWED_ROOT_ENTRIES = REQUIRED_ROOT_DIRS | {
    # dot dirs / infra
    "plan", ".git", ".github", ".githooks", ".pytest_cache", ".vscode",
    # dot files
    ".gitignore", ".gitlab-ci.yml", ".gs-project.yml", ".gs-project",
    # named files
    "agent.md", "AGENTS.md", "CLAUDE.md", "README.md", "readme.md", "ai.code-workspace",
    "ml-vol-estimator.code-workspace",
    # Likely CI/config files
    "pyproject.toml", "uv.lock", ".python-version",
    # ML vol estimator source package
    "src",
    # CLI wrapper and data directory
    "vol", "vol.cmd", "data",
    # Coder workspace binary (not tracked, but present on disk)
    "H:coder.exe",
}

# ── Valid memory domains (from meta/guide.md §Domains — updated 2026-04-16) ────
VALID_MEMORY_DOMAINS = {
    "meta", "person", "slang", "ref", "sys", "domain",
    "ops", "instruments", "infra", "reg", "vendor",
    "research",
}

# ── CoALA section requirements ─────────────────────────────────────────────────
COALA_SECTIONS = {"Concepts", "Rules", "Patterns", "Edge Cases", "Anti-patterns", "Links"}

# Skip domains that don't follow CoALA knowledge structure
# meta/person = structural; ref/slang/domain = reference/topic material
# infra/instruments/ops/reg/vendor = bulk-imported reference docs (PDFs, manuals)
COALA_SKIP_PREFIXES = {
    "meta/", "person/", "ref/", "slang/", "domain/",
    "infra/", "instruments/", "ops/", "reg/", "vendor/",
}
COALA_SKIP_NAMES = {"design.md", "INDEX.md"}

# ── Thresholds ─────────────────────────────────────────────────────────────────
SKILL_WARN_LINES  = 250
SKILL_ERROR_LINES = 400
SKILL_MIN_LINES_FOR_MEMORY_REF = 80   # smaller skills are fine without explicit ref
PERSONA_MAX_CODE_BLOCK_LINES = 10     # flag code blocks longer than this
POLICY_MAX_CODE_BLOCK_LINES  = 10
SECTION_DESIGN_MAX_LINES     = 120    # section design.md line budget

# ── Persona compliance constants ───────────────────────────────────────────────
# personas/design.md §4.5: the definitive read-only persona list
READ_ONLY_PERSONAS = {
    "analyst", "oracle", "doctor", "sentinel", "scribe",
    "pathfinder", "auditor", "prescriber", "tracehound",
    "quartermaster",
}
# Write/execute tools that should not appear in read-only persona <tools> sections
WRITE_TOOLS = {
    "run_in_terminal", "create_file", "replace_string_in_file",
    "multi_replace_string_in_file", "edit_notebook_file",
}
# Cross-persona dispatch patterns (Pattern 8/12 from design-cure-patterns.md)
RE_CROSS_DISPATCH = re.compile(
    r"(?:[Rr]oute\s+to|[Hh]and(?:s|off)\s+to|[Ee]scalate\s+(?:[Uu]pward\s+)?to|[Dd]elegate\s+to|[Ss]witch\s+to)"
    r"\s+[A-Z][A-Z_]+",
)

# ── Workflow definition files (excludes support files) ─────────────────────────
WORKFLOW_DEF_FILES = {
    "cure.md", "debug.md", "execute.md", "fix.md", "housekeep.md",
    "interview.md", "investigate.md", "learn.md", "lightweight.md",
    "plan.md", "review.md", "support.md", "team.md",
}

# ── Workspace required subdirs (from design.md §Workspace Structure) ──────────
WORKSPACE_REQUIRED_SUBDIRS = {"plan", "config", "governance", "lint", "tests", "raw", "tmp"}

# ── Concrete skill identifiers that should not appear in workflow phases ───────
# keyword-dispatch.md and session-state.md are exempt (dispatch tables)
RE_CONCRETE_SKILL = re.compile(
    r"\b(?:SLANG_EDIT|SLANG_LINT|SLANG_GLIMPSE|SLANG_REVIEW|SLANG_CLEANUP|"
    r"SLANG_REGTEST_FIX|SLANG_COPILOT|SLANG_EVAL|"
    r"CVS|ENGHUB|CANVAS|DIRGET|PRIME_QUERY|FORWARD_NETWORK|FIREWALL_REVIEW|"
    r"GITLAB_PIPELINES|GITLAB_SEARCH|GSSSO_AUTH|PROCMON_LOGS|PDF_READER|"
    r"PYTHON_MARKET_DATA|OUTLOOK|AI_SLOP_CLEANER|ETI_TRADE|SECDB_INSPECT|"
    r"HTML_SUMMARY|CONFLUENCE)\b",
)
# Tool flags/CLI details that belong in policy/memory, not workflows
RE_TOOL_FLAG = re.compile(
    r"(?:secexpr\s+--(?:safe|full))|"
    r"(?:--check-ascii)|"
    r"(?:\bedit\.py\b)|"
    r"(?:\blint\.py\b)|"
    r"(?:Status-[12]\b)",
)

# ── Section design.md validation ───────────────────────────────────────────────
# Sections that should have a design.md file, and the 7 required headings.
SECTION_DESIGN_DIRS = {"workflows", "skills", "memory", "personas", "policy"}
SECTION_DESIGN_REQUIRED_HEADINGS = {
    "1. Purpose",
    "2. Boundaries",
    "3. Structure",
    "4. Rules",
    "5. Interfaces",
    "6. Anti-Patterns",
    "7. Lint",
}

# ── Violation ──────────────────────────────────────────────────────────────────

class Violation:
    __slots__ = ("severity", "check", "path", "message")

    def __init__(self, severity: str, check: str, path: str, message: str):
        self.severity = severity  # "ERROR" | "WARN"
        self.check    = check
        self.path     = path
        self.message  = message

    def __str__(self) -> str:
        rel = self.path
        return f"  [{self.severity}] {self.check}: {rel}\n         {self.message}"


def _relpath(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _code_block_lengths(text: str) -> list[int]:
    """Return list of line-counts for each fenced code block in text."""
    lengths: list[int] = []
    in_block = False
    length   = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if in_block:
                lengths.append(length)
                in_block = False
                length   = 0
            else:
                in_block = True
                length   = 0
        elif in_block:
            length += 1
    return lengths


# ── Check 1: Structural ────────────────────────────────────────────────────────

def check_structural() -> list[Violation]:
    vs: list[Violation] = []

    # 1a. Required dirs exist
    for d in sorted(REQUIRED_ROOT_DIRS):
        if not (REPO_ROOT / d).is_dir():
            vs.append(Violation(
                "ERROR", "structural",
                str(REPO_ROOT / d),
                f"Required top-level directory missing: {d}/",
            ))

    # 1b. No unrecognised top-level entries
    for entry in sorted(REPO_ROOT.iterdir()):
        name = entry.name
        if name in ALLOWED_ROOT_ENTRIES:
            continue
        # Tolerate unknown dot-files/dirs (CI tooling, etc.) with a warn
        if name.startswith("."):
            vs.append(Violation(
                "WARN", "structural",
                _relpath(entry),
                f"Unexpected top-level dot entry: {name}  (consider adding to ALLOWED_ROOT_ENTRIES)",
            ))
        elif entry.is_dir() and next(entry.iterdir(), None) is None:
            # Empty legacy directory — warn only, it can be removed
            vs.append(Violation(
                "WARN", "structural",
                _relpath(entry),
                f"Empty legacy directory: {name}/  (safe to delete)",
            ))
        else:
            vs.append(Violation(
                "ERROR", "structural",
                _relpath(entry),
                f"Unrecognised top-level entry: {name}  (must live under one of the five primitives or workspace/)",
            ))

    return vs


# ── Check 2: Skill size ────────────────────────────────────────────────────────

def check_skill_sizes() -> list[Violation]:
    vs: list[Violation] = []
    skills_root = REPO_ROOT / "skills"
    if not skills_root.is_dir():
        return vs

    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue

        lines = _read_cached(skill_md).splitlines()
        n = len(lines)
        if n >= SKILL_ERROR_LINES:
            vs.append(Violation(
                "ERROR", "skill-size",
                _relpath(skill_md),
                f"{n} lines — exceeds hard limit ({SKILL_ERROR_LINES}). Move knowledge to memory/.",
            ))
        elif n >= SKILL_WARN_LINES:
            vs.append(Violation(
                "WARN", "skill-size",
                _relpath(skill_md),
                f"{n} lines — above warning threshold ({SKILL_WARN_LINES}). Consider moving static knowledge to memory/.",
            ))

    return vs


# ── Check 3: Skill → memory references ────────────────────────────────────────

def check_skill_memory_refs() -> list[Violation]:
    vs: list[Violation] = []
    skills_root = REPO_ROOT / "skills"
    if not skills_root.is_dir():
        return vs

    re_memory_link = re.compile(r"memory/", re.IGNORECASE)

    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue

        text  = _read_cached(skill_md)
        lines = text.splitlines()
        if len(lines) < SKILL_MIN_LINES_FOR_MEMORY_REF:
            continue  # small skills are fine without a ref

        if not re_memory_link.search(text):
            vs.append(Violation(
                "WARN", "skill-memory-ref",
                _relpath(skill_md),
                f"{len(lines)} lines but no link to memory/ — consider extracting domain knowledge.",
            ))

    return vs


# ── Check 4: Memory CoALA sections ────────────────────────────────────────────

def check_memory_coala_sections() -> list[Violation]:
    vs: list[Violation] = []
    memory_root = REPO_ROOT / "memory"
    if not memory_root.is_dir():
        return vs

    # Load P2 set — exempt from CoALA section requirements
    _idx_row = re.compile(
        r"\|\s*\[([^\]]+)\]\([^)]+\)\s*\|"
        r"[^|]*\|"
        r"\s*(P\d)\s*\|",
    )
    p2_files: set[str] = set()
    index_path = memory_root / "INDEX.md"
    if index_path.is_file():
        idx_text = _read_cached(index_path)
        p2_files = {m.group(1) for m in _idx_row.finditer(idx_text) if m.group(2) == "P2"}

    for md in _glob_cached(memory_root, "*.md", recursive=True):
        rel = str(md.relative_to(memory_root)).replace("\\", "/")
        # Skip structural/governance files by prefix or name
        if any(rel.startswith(pfx) for pfx in COALA_SKIP_PREFIXES):
            continue
        if md.name in COALA_SKIP_NAMES:
            continue
        # Skip template files
        if "template" in md.name:
            continue
        # Skip P2 files — relaxed constraints
        if rel in p2_files:
            continue

        text = _read_cached(md)
        # Find all ## headings
        headings = {m.group(1).strip() for m in re.finditer(r"^## (.+)", text, re.MULTILINE)}

        missing = COALA_SECTIONS - headings
        if missing:
            vs.append(Violation(
                "WARN", "coala-sections",
                _relpath(md),
                f"Missing CoALA sections: {', '.join(sorted(missing))}",
            ))

    return vs


# ── Check 5: Persona purity ────────────────────────────────────────────────────

def check_persona_purity() -> list[Violation]:
    vs: list[Violation] = []
    personas_root = REPO_ROOT / "personas"
    if not personas_root.is_dir():
        return vs

    # Pattern: persona embeds a skills/src/ reference (tool logic)
    re_src_path = re.compile(r"\bskills/[A-Z_]+/src/", re.IGNORECASE)

    for md in _glob_cached(personas_root, "*.md"):
        if md.name == "INDEX.md":
            continue

        text = _read_cached(md)

        # 5a. Large inline code blocks
        for length in _code_block_lengths(text):
            if length > PERSONA_MAX_CODE_BLOCK_LINES:
                vs.append(Violation(
                    "WARN", "persona-purity",
                    _relpath(md),
                    f"Code block of {length} lines — personas should not embed runnable examples (move to skills/).",
                ))
                break  # one violation per file is enough

        # 5b. Direct tool/script path references
        if re_src_path.search(text):
            vs.append(Violation(
                "WARN", "persona-purity",
                _relpath(md),
                "Persona references skills/*/src/ path — tool logic belongs in skills/, not personas.",
            ))

    return vs


# ── Check 6: Policy purity ─────────────────────────────────────────────────────

def check_policy_purity() -> list[Violation]:
    vs: list[Violation] = []
    policy_root = REPO_ROOT / "policy"
    if not policy_root.is_dir():
        return vs

    re_skills_src = re.compile(r"\bskills/[A-Z_]+/src/", re.IGNORECASE)

    for md in _glob_cached(policy_root, "*.md"):
        if md.name in ("index.md", "INDEX.md"):
            continue

        text = _read_cached(md)

        # 6a. Code blocks too large for a policy doc
        for length in _code_block_lengths(text):
            if length > POLICY_MAX_CODE_BLOCK_LINES:
                vs.append(Violation(
                    "WARN", "policy-purity",
                    _relpath(md),
                    f"Code block of {length} lines — policy documents should contain constraints, not executable examples.",
                ))
                break

        # 6b. Direct skill tool references in policy
        if re_skills_src.search(text):
            vs.append(Violation(
                "WARN", "policy-purity",
                _relpath(md),
                "Policy file references skills/src/ paths — execution detail belongs in skills/ or workflows/.",
            ))

    return vs


# ── Check 7: Dependency direction ──────────────────────────────────────────────

def check_dependency_direction() -> list[Violation]:
    """
    Enforced rules:
      - skills/  must NOT link upward to personas/ or policy/
      - workflows/ must NOT link to skills/*/src/ (implementation detail)
    """
    vs: list[Violation] = []

    re_persona_link  = re.compile(r"\bpersona[s]?/\w", re.IGNORECASE)
    re_policy_link   = re.compile(r"\bpolic[y]?/\w", re.IGNORECASE)
    re_skills_src    = re.compile(r"\bskills/[A-Z_]+/src/", re.IGNORECASE)

    # skills/ → personas/ or skills/ → policy/ is an upward dependency
    skills_root = REPO_ROOT / "skills"
    if skills_root.is_dir():
        for md in _glob_cached(skills_root, "*.md", recursive=True):
            text = _read_cached(md)
            if re_persona_link.search(text):
                vs.append(Violation(
                    "WARN", "dependency-direction",
                    _relpath(md),
                    "Skill links to personas/ — skills are lower-layer and must not depend on personas.",
                ))
            if re_policy_link.search(text):
                vs.append(Violation(
                    "WARN", "dependency-direction",
                    _relpath(md),
                    "Skill links to policy/ — skills are lower-layer and must not depend on policy.",
                ))

    # workflows/ should orchestrate, not embed tool-level src/ paths
    workflows_root = REPO_ROOT / "workflows"
    if workflows_root.is_dir():
        for md in _glob_cached(workflows_root, "*.md"):
            text = _read_cached(md)
            if re_skills_src.search(text):
                vs.append(Violation(
                    "WARN", "dependency-direction",
                    _relpath(md),
                    "Workflow embeds skills/src/ reference — execution paths belong in skills/, not workflows/.",
                ))

    return vs


# ── Check 8: Section design.md headings + line budget ──────────────────────────

def check_section_design() -> list[Violation]:
    vs: list[Violation] = []

    for section in sorted(SECTION_DESIGN_DIRS):
        design_path = REPO_ROOT / section / "design.md"
        if not design_path.is_file():
            vs.append(Violation(
                "WARN", "section-design",
                _relpath(design_path),
                f"Missing section design.md — expected per workspace/design.md.",
            ))
            continue

        text  = _read_cached(design_path)
        lines = text.splitlines()

        # 8a. Line budget
        if len(lines) > SECTION_DESIGN_MAX_LINES:
            vs.append(Violation(
                "WARN", "section-design",
                _relpath(design_path),
                f"{len(lines)} lines — exceeds {SECTION_DESIGN_MAX_LINES}-line budget per workspace/design.md.",
            ))

        # 8b. Required headings (match ## N. or ### N. prefixed headings)
        headings = set()
        for line in lines:
            m = re.match(r"^#{2,3}\s+(\d+\.\s+\S+.*)", line)
            if m:
                headings.add(m.group(1).strip())

        missing = SECTION_DESIGN_REQUIRED_HEADINGS - headings
        if missing:
            vs.append(Violation(
                "WARN", "section-design",
                _relpath(design_path),
                f"Missing required headings: {', '.join(sorted(missing))}",
            ))

    return vs


# ── Check 9: Memory domain validation ──────────────────────────────────────────

def check_memory_domains() -> list[Violation]:
    """Every subdirectory under memory/ must be a recognized domain from meta/guide.md."""
    vs: list[Violation] = []
    memory_root = REPO_ROOT / "memory"
    if not memory_root.is_dir():
        return vs

    # Skip special infrastructure directories (not active domains)
    SKIP_DIRS = {"_archived", "_dormant"}

    for entry in sorted(memory_root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in SKIP_DIRS:
            continue
        if entry.name not in VALID_MEMORY_DOMAINS:
            vs.append(Violation(
                "ERROR", "memory-domain",
                _relpath(entry),
                f"Unrecognized memory domain '{entry.name}/' — "
                f"valid domains: {sorted(VALID_MEMORY_DOMAINS)}. "
                f"Move files to a recognized domain or add to meta/guide.md.",
            ))

    return vs


# ── Check 10: Memory INDEX.md coverage ─────────────────────────────────────────

def check_memory_index_coverage() -> list[Violation]:
    """Every .md file under memory/<domain>/ should have an INDEX.md entry, and vice versa."""
    vs: list[Violation] = []
    memory_root = REPO_ROOT / "memory"
    index_path = memory_root / "INDEX.md"
    if not index_path.is_file():
        return vs

    # Parse all linked paths from INDEX.md table rows
    idx_text = _read_cached(index_path)
    re_idx_row = re.compile(r"\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|")
    indexed_paths: set[str] = set()
    # Cross-references to files outside memory/ (link target starts with ../)
    cross_ref_targets: dict[str, str] = {}  # display_text -> resolved target
    for m in re_idx_row.finditer(idx_text):
        display_text = m.group(1)
        link_target = m.group(2)
        if link_target.startswith("../"):
            # Cross-reference to a file outside memory/ — resolve against repo root
            cross_ref_targets[display_text] = link_target
        else:
            indexed_paths.add(display_text)

    # Collect all .md files under memory/<domain>/ (skip root-level files and governance)
    governance = {"INDEX.md", "design.md", "README.md"}
    # Also skip governance files referenced in INDEX but not domain content
    index_governance = {"design.md", "meta/guide.md"}
    disk_paths: set[str] = set()
    for md in _glob_cached(memory_root, "*.md", recursive=True):
        rel = str(md.relative_to(memory_root)).replace("\\", "/")
        parts = rel.split("/")
        # Skip root-level files
        if len(parts) < 2:
            continue
        # Skip meta/guide.md (governance, not content)
        if rel == "meta/guide.md":
            continue
        disk_paths.add(rel)

    # Files on disk but missing from INDEX
    for rel in sorted(disk_paths - indexed_paths):
        vs.append(Violation(
            "WARN", "memory-index-coverage",
            f"memory/{rel}",
            f"File exists on disk but has no INDEX.md entry.",
        ))

    # Files in INDEX but missing from disk (exclude governance entries)
    for rel in sorted(indexed_paths - disk_paths - index_governance):
        vs.append(Violation(
            "ERROR", "memory-index-coverage",
            f"memory/{rel}",
            f"INDEX.md references this file but it does not exist on disk.",
        ))

    # Cross-references to files outside memory/ — verify they exist at repo root
    for display_text, link_target in sorted(cross_ref_targets.items()):
        resolved = (memory_root / link_target).resolve()
        if not resolved.exists():
            vs.append(Violation(
                "ERROR", "memory-index-coverage",
                f"memory/INDEX.md",
                f"Cross-reference [{display_text}]({link_target}) — target does not exist.",
            ))

    return vs


# ── Check 11: Workflow transition-table precedence (§4.2) ──────────────────────

def check_workflow_transition_precedence() -> list[Violation]:
    """Every transition table with 2+ conditions must declare precedence ordering."""
    vs: list[Violation] = []
    workflows_root = REPO_ROOT / "workflows"
    if not workflows_root.is_dir():
        return vs

    # Only audit the 13 workflow definition files, not support files
    workflow_files = {
        "cure.md", "debug.md", "execute.md", "fix.md", "housekeep.md",
        "interview.md", "investigate.md", "learn.md", "lightweight.md",
        "plan.md", "review.md", "support.md", "team.md",
    }

    re_precedence = re.compile(r"\*\*Precedence[:\*]", re.IGNORECASE)

    for md in _glob_cached(workflows_root, "*.md"):
        if md.name not in workflow_files:
            continue

        text = _read_cached(md)
        lines = text.splitlines()

        # Find transition tables: a header row, separator row, then data rows.
        # Pure string ops — no regex on table content to avoid catastrophic
        # backtracking on malformed/concatenated lines.
        i = 0
        n = len(lines)
        while i < n - 2:
            line = lines[i].strip()
            # Header must be exactly 2-column: "| Condition | Transition |"
            if (line.startswith("|")
                and line.endswith("|")
                and line.count("|") == 3
                and "condition" in line.lower()
                and "transition" in line.lower()):
                # Separator: only dashes, colons, pipes, spaces (no regex)
                sep = lines[i + 1].strip()
                is_sep = (sep.startswith("|")
                          and sep.endswith("|")
                          and sep.count("|") >= 3
                          and all(c in "-:| " for c in sep))
                if is_sep:
                    row_count = 0
                    j = i + 2
                    while j < n:
                        row = lines[j].strip()
                        if row.startswith("|") and row.endswith("|") and row.count("|") >= 3:
                            row_count += 1
                        else:
                            break
                        j += 1

                    if row_count >= 2:
                        # Check for precedence note in the 5 lines before the table
                        context_start = max(0, i - 5)
                        context = "\n".join(lines[context_start:i])
                        if not re_precedence.search(context):
                            vs.append(Violation(
                                "WARN", "transition-precedence",
                                _relpath(md),
                                f"Transition table at line {i + 1} has {row_count} conditions "
                                f"but no precedence declaration.",
                            ))
            i += 1

    return vs


# ── Check 12: Persona INDEX entry (§4.1) ──────────────────────────────────────

def check_persona_index_entry() -> list[Violation]:
    """Every persona .md file (except design.md, INDEX.md) must have a row in INDEX.md."""
    vs: list[Violation] = []
    personas_root = REPO_ROOT / "personas"
    if not personas_root.is_dir():
        return vs

    index_path = personas_root / "INDEX.md"
    if not index_path.is_file():
        vs.append(Violation("ERROR", "persona-index", _relpath(index_path),
                            "personas/INDEX.md missing."))
        return vs

    idx_text = _read_cached(index_path).lower()

    for md in _glob_cached(personas_root, "*.md"):
        if md.name in ("INDEX.md", "design.md"):
            continue
        persona_name = md.stem.upper()
        # Check if the persona name appears as a link or in a table row
        if persona_name.lower() not in idx_text and f"[{persona_name}" not in _read_cached(index_path):
            vs.append(Violation(
                "WARN", "persona-index",
                _relpath(md),
                f"Persona '{persona_name}' has no entry in personas/INDEX.md (§4.1).",
            ))

    return vs


# ── Check 13: Persona read-only declaration (§4.5) ────────────────────────────

def check_persona_readonly_decl() -> list[Violation]:
    """Read-only personas must declare 'Write and Edit tools are blocked' or equivalent."""
    vs: list[Violation] = []
    personas_root = REPO_ROOT / "personas"
    if not personas_root.is_dir():
        return vs

    re_write_blocked = re.compile(
        r"(?:write\s+and\s+edit\s+tools\s+are\s+blocked|read[\s-]*only.*tools?\s+(?:are\s+)?blocked)",
        re.IGNORECASE,
    )

    for md in _glob_cached(personas_root, "*.md"):
        if md.name in ("INDEX.md", "design.md"):
            continue
        if md.stem not in READ_ONLY_PERSONAS:
            continue

        text = _read_cached(md)
        if not re_write_blocked.search(text):
            vs.append(Violation(
                "WARN", "persona-readonly",
                _relpath(md),
                f"Read-only persona '{md.stem.upper()}' does not declare write tools blocked (§4.5).",
            ))

    return vs


# ── Check 14: Persona <effort_gate> (§3) ──────────────────────────────────────

def check_persona_effort_gate() -> list[Violation]:
    """Every persona must include an <effort_gate> within <constraints>."""
    vs: list[Violation] = []
    personas_root = REPO_ROOT / "personas"
    if not personas_root.is_dir():
        return vs

    for md in _glob_cached(personas_root, "*.md"):
        if md.name in ("INDEX.md", "design.md"):
            continue

        text = _read_cached(md)
        if "<effort_gate>" not in text:
            vs.append(Violation(
                "WARN", "persona-effort-gate",
                _relpath(md),
                f"Persona missing <effort_gate> section within <constraints> (§3).",
            ))

    return vs


# ── Check 15: Persona <verification_loop> (§3) ────────────────────────────────

def check_persona_verification_loop() -> list[Violation]:
    """Every persona with <execution_loop> must also have <verification_loop>."""
    vs: list[Violation] = []
    personas_root = REPO_ROOT / "personas"
    if not personas_root.is_dir():
        return vs

    for md in _glob_cached(personas_root, "*.md"):
        if md.name in ("INDEX.md", "design.md"):
            continue

        text = _read_cached(md)
        if "<execution_loop>" in text and "<verification_loop>" not in text:
            vs.append(Violation(
                "WARN", "persona-verification-loop",
                _relpath(md),
                "Persona has <execution_loop> but no <verification_loop> (§3).",
            ))

    return vs


# ── Check 16: Persona cross-dispatch (Pattern 8/12) ───────────────────────────

def check_persona_cross_dispatch() -> list[Violation]:
    """Personas must not embed 'route to X' dispatch instructions."""
    vs: list[Violation] = []
    personas_root = REPO_ROOT / "personas"
    if not personas_root.is_dir():
        return vs

    for md in _glob_cached(personas_root, "*.md"):
        if md.name in ("INDEX.md", "design.md"):
            continue

        text = _read_cached(md)
        # Skip HTML comments (design exception annotations)
        text_no_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        match = RE_CROSS_DISPATCH.search(text_no_comments)
        if match:
            vs.append(Violation(
                "WARN", "persona-cross-dispatch",
                _relpath(md),
                f"Cross-persona dispatch found: '{match.group().strip()}'. "
                f"Use generic language ('escalate upward') instead (Pattern 8/12).",
            ))

    return vs


# ── Check 17: Persona read-only tool lists (Pattern 14) ───────────────────────

def check_persona_readonly_tools() -> list[Violation]:
    """Read-only persona <tools> sections must not list write/execute tools."""
    vs: list[Violation] = []
    personas_root = REPO_ROOT / "personas"
    if not personas_root.is_dir():
        return vs

    for md in _glob_cached(personas_root, "*.md"):
        if md.name in ("INDEX.md", "design.md"):
            continue
        if md.stem not in READ_ONLY_PERSONAS:
            continue

        text = _read_cached(md)
        # Extract <tools> section content
        tools_match = re.search(r"<tools>(.*?)</tools>", text, re.DOTALL)
        if not tools_match:
            continue

        tools_text = tools_match.group(1)
        for tool in WRITE_TOOLS:
            if tool in tools_text:
                vs.append(Violation(
                    "WARN", "persona-readonly-tools",
                    _relpath(md),
                    f"Read-only persona '{md.stem.upper()}' lists write tool "
                    f"'{tool}' in <tools> section (Pattern 14).",
                ))

    return vs


# ── Check 18: Workflow _protocol.md reference (§4.1) ──────────────────────────

def check_workflow_protocol_ref() -> list[Violation]:
    """Every workflow must reference _protocol.md in its first paragraph."""
    vs: list[Violation] = []
    workflows_root = REPO_ROOT / "workflows"
    if not workflows_root.is_dir():
        return vs

    for md in _glob_cached(workflows_root, "*.md"):
        if md.name not in WORKFLOW_DEF_FILES:
            continue

        text = _read_cached(md)
        # Check first ~10 non-empty lines for _protocol.md reference
        lines = [l for l in text.splitlines()[:15] if l.strip()]
        first_para = "\n".join(lines[:5])
        if "_protocol.md" not in first_para:
            vs.append(Violation(
                "WARN", "workflow-protocol-ref",
                _relpath(md),
                "Workflow does not reference _protocol.md in its first paragraph (§4.1).",
            ))

    return vs


# ── Check 19: Workflow state machine (§4.2) ───────────────────────────────────

def check_workflow_state_machine() -> list[Violation]:
    """Every workflow must define a state machine with named states."""
    vs: list[Violation] = []
    workflows_root = REPO_ROOT / "workflows"
    if not workflows_root.is_dir():
        return vs

    re_state_machine = re.compile(r"##\s+State Machine|```\n.*→.*\n.*```", re.DOTALL)
    re_arrow_chain = re.compile(r"[A-Z]+\s*→\s*[A-Z]+")

    for md in _glob_cached(workflows_root, "*.md"):
        if md.name not in WORKFLOW_DEF_FILES:
            continue

        text = _read_cached(md)
        has_heading = "## State Machine" in text or "## state machine" in text.lower()
        has_arrows = re_arrow_chain.search(text)

        if not has_heading and not has_arrows:
            vs.append(Violation(
                "WARN", "workflow-state-machine",
                _relpath(md),
                "Workflow has no 'State Machine' section or state transition arrows (§4.2).",
            ))

    return vs


# ── Check 20: Workflow INDEX entry (§4.10) ─────────────────────────────────────

def check_workflow_index_entry() -> list[Violation]:
    """Every workflow file must appear in INDEX.md Quick Reference table."""
    vs: list[Violation] = []
    workflows_root = REPO_ROOT / "workflows"
    if not workflows_root.is_dir():
        return vs

    index_path = workflows_root / "INDEX.md"
    if not index_path.is_file():
        vs.append(Violation("ERROR", "workflow-index", _relpath(index_path),
                            "workflows/INDEX.md missing."))
        return vs

    idx_text = _read_cached(index_path)

    for name in sorted(WORKFLOW_DEF_FILES):
        md = workflows_root / name
        if not md.is_file():
            continue
        # Check the filename appears in a markdown link in INDEX.md
        if name not in idx_text:
            vs.append(Violation(
                "WARN", "workflow-index",
                _relpath(md),
                f"Workflow '{name}' not found in workflows/INDEX.md Quick Reference (§4.10).",
            ))

    return vs


# ── Check 21: Session-state active_workflow enum ───────────────────────────────

def check_session_state_enum() -> list[Violation]:
    """session-state.md active_workflow enum must list every workflow file."""
    vs: list[Violation] = []
    workflows_root = REPO_ROOT / "workflows"
    ss_path = workflows_root / "session-state.md"
    if not ss_path.is_file():
        return vs

    ss_text = _read_cached(ss_path)
    # Extract the active_workflow enum values from the table row
    m = re.search(r"`active_workflow`[^|]*\|[^|]*\|\s*[^(]*\(([^)]+)\)", ss_text)
    if not m:
        return vs

    raw_enum = m.group(1)
    enum_values = {v.strip().strip("`") for v in raw_enum.split(",")}

    # Expected: stem of each workflow definition file
    expected = {Path(f).stem for f in WORKFLOW_DEF_FILES}

    missing_from_enum = expected - enum_values
    extra_in_enum = enum_values - expected

    for name in sorted(missing_from_enum):
        vs.append(Violation(
            "WARN", "session-state-enum",
            _relpath(ss_path),
            f"Workflow '{name}' exists as a file but is missing from "
            f"active_workflow enum in session-state.md.",
        ))

    for name in sorted(extra_in_enum):
        vs.append(Violation(
            "WARN", "session-state-enum",
            _relpath(ss_path),
            f"active_workflow enum lists '{name}' but no matching workflow file exists.",
        ))

    return vs


# ── Check 22+23: Workflow skill names & tool flags (§4.7) ─────────────────────

def check_workflow_domain_leakage() -> list[Violation]:
    """Workflows must not embed concrete skill identifiers or tool flags/CLI details."""
    vs: list[Violation] = []
    workflows_root = REPO_ROOT / "workflows"
    if not workflows_root.is_dir():
        return vs

    # Files exempt from skill-name checks (dispatch tables use them by design)
    exempt_files = {"keyword-dispatch.md", "session-state.md", "INDEX.md", "_protocol.md", "design.md"}

    for md in _glob_cached(workflows_root, "*.md"):
        if md.name in exempt_files:
            continue
        if md.name not in WORKFLOW_DEF_FILES:
            continue

        text = _read_cached(md)
        # Strip HTML comments (design exception annotations)
        text_no_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        # Check 22: concrete skill names
        skill_match = RE_CONCRETE_SKILL.search(text_no_comments)
        if skill_match:
            vs.append(Violation(
                "WARN", "workflow-skill-names",
                _relpath(md),
                f"Concrete skill identifier '{skill_match.group()}' found in workflow. "
                f"Use generic descriptions instead (§4.7).",
            ))

        # Check 23: tool flags/CLI details
        flag_match = RE_TOOL_FLAG.search(text_no_comments)
        if flag_match:
            vs.append(Violation(
                "WARN", "workflow-tool-flags",
                _relpath(md),
                f"Tool flag/CLI detail '{flag_match.group()}' found in workflow. "
                f"These belong in policy or memory, not orchestration (§4.7).",
            ))

    return vs


# ── Check 24: Persona frontmatter (§3) ────────────────────────────────────────

def check_persona_frontmatter() -> list[Violation]:
    """Every persona file must have frontmatter with 'description' field."""
    vs: list[Violation] = []
    personas_root = REPO_ROOT / "personas"
    if not personas_root.is_dir():
        return vs

    for md in _glob_cached(personas_root, "*.md"):
        if md.name in ("INDEX.md", "design.md"):
            continue

        text = _read_cached(md)
        # Check for YAML frontmatter
        if not text.startswith("---"):
            vs.append(Violation(
                "WARN", "persona-frontmatter",
                _relpath(md),
                "Persona file has no YAML frontmatter (§3: 'description' required).",
            ))
            continue

        # Extract frontmatter
        fm_end = text.find("---", 3)
        if fm_end == -1:
            vs.append(Violation(
                "WARN", "persona-frontmatter",
                _relpath(md),
                "Persona file has unclosed YAML frontmatter.",
            ))
            continue

        frontmatter = text[3:fm_end]
        if "description:" not in frontmatter and "description :" not in frontmatter:
            vs.append(Violation(
                "WARN", "persona-frontmatter",
                _relpath(md),
                "Persona frontmatter missing 'description' field (§3).",
            ))

    return vs


# ── Check 25: Broken links ────────────────────────────────────────────────────

def check_broken_links() -> list[Violation]:
    """Relative markdown links in .md files must resolve to actual files."""
    vs: list[Violation] = []

    # Scan the five primitives + .github/instructions, .github/prompts, AGENTS.md
    scan_dirs = [
        "personas", "workflows", "policy", "skills", "memory",
        os.path.join(".github", "instructions"),
        os.path.join(".github", "prompts"),
    ]
    scan_extra_files = [
        REPO_ROOT / "AGENTS.md",
    ]
    re_md_link = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

    seen: set[tuple[str, str]] = set()  # (source_relpath, target) to dedupe

    # Also scan individual extra files
    for extra_file in scan_extra_files:
        if extra_file.is_file():
            text = _read_cached(extra_file)
            text_no_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
            text_no_code = re.sub(r"``.*?``", "", text_no_code)
            text_no_code = re.sub(r"`[^`]+`", "", text_no_code)
            for m in re_md_link.finditer(text_no_code):
                target = m.group(2).strip()
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if "://" in target:
                    continue
                target_path = target.split("#")[0]
                if not target_path:
                    continue
                resolved = (extra_file.parent / target_path).resolve()
                source_rel = _relpath(extra_file)
                key = (source_rel, target_path)
                if key in seen:
                    continue
                seen.add(key)
                if not resolved.exists():
                    vs.append(Violation(
                        "WARN", "broken-link",
                        source_rel,
                        f"Broken link: [{m.group(1)}]({target}) — target does not exist.",
                    ))

    for scan_dir in scan_dirs:
        root = REPO_ROOT / scan_dir
        if not root.is_dir():
            continue

        for md in _glob_cached(root, "*.md", recursive=True):
            text = _read_cached(md)
            # Strip fenced code blocks and inline code spans so example links aren't flagged
            text_no_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
            text_no_code = re.sub(r"``.*?``", "", text_no_code)
            text_no_code = re.sub(r"`[^`]+`", "", text_no_code)
            for m in re_md_link.finditer(text_no_code):
                target = m.group(2).strip()

                # Skip external URLs
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                # Skip URI schemes (file://, copilot-skill://, etc.)
                if "://" in target:
                    continue

                # Strip fragment (#section)
                target_path = target.split("#")[0]
                if not target_path:
                    continue

                # Resolve relative to the file's directory
                resolved = (md.parent / target_path).resolve()
                source_rel = _relpath(md)
                key = (source_rel, target_path)
                if key in seen:
                    continue
                seen.add(key)

                if not resolved.exists():
                    vs.append(Violation(
                        "WARN", "broken-link",
                        source_rel,
                        f"Broken link: [{m.group(1)}]({target}) — target does not exist.",
                    ))

    return vs


# ── Check 26: Workspace structure ─────────────────────────────────────────────

def check_workspace_structure() -> list[Violation]:
    """workspace/ must contain required subdirectories per design.md §Workspace Structure."""
    vs: list[Violation] = []
    ws_root = REPO_ROOT / "workspace"
    if not ws_root.is_dir():
        return vs

    for subdir in sorted(WORKSPACE_REQUIRED_SUBDIRS):
        if not (ws_root / subdir).is_dir():
            vs.append(Violation(
                "WARN", "workspace-structure",
                f"workspace/{subdir}",
                f"Required workspace subdirectory '{subdir}/' missing "
                f"(design.md §Workspace Structure).",
            ))

    return vs


# ── Runner ─────────────────────────────────────────────────────────────────────

# (check-name, function, category)
# Categories:
#   structural  — mechanical checks (dirs, sizes, sections, headings)
#   compliance  — design-boundary / purity checks (dependency direction, content rules)
CHECKS: list[tuple[str, object, str]] = [
    ("structural",          check_structural,            "structural"),
    ("skill-size",          check_skill_sizes,           "structural"),
    ("skill-memory-ref",    check_skill_memory_refs,     "structural"),
    ("coala-sections",      check_memory_coala_sections, "structural"),
    ("persona-purity",      check_persona_purity,        "compliance"),
    ("policy-purity",       check_policy_purity,         "compliance"),
    ("dependency-direction",check_dependency_direction,  "compliance"),
    ("section-design",      check_section_design,        "structural"),
    ("memory-domain",       check_memory_domains,        "structural"),
    ("memory-index-coverage", check_memory_index_coverage, "structural"),
    ("transition-precedence", check_workflow_transition_precedence, "compliance"),
    ("persona-index",       check_persona_index_entry,    "compliance"),
    ("persona-readonly",    check_persona_readonly_decl,  "compliance"),
    ("persona-effort-gate", check_persona_effort_gate,    "compliance"),
    ("persona-verification-loop", check_persona_verification_loop, "compliance"),
    ("persona-cross-dispatch", check_persona_cross_dispatch, "compliance"),
    ("persona-readonly-tools", check_persona_readonly_tools, "compliance"),
    ("workflow-protocol-ref", check_workflow_protocol_ref, "compliance"),
    ("workflow-state-machine", check_workflow_state_machine, "compliance"),
    ("workflow-index",      check_workflow_index_entry,   "structural"),
    ("session-state-enum",  check_session_state_enum,     "structural"),
    ("workflow-domain-leakage", check_workflow_domain_leakage, "compliance"),
    ("persona-frontmatter", check_persona_frontmatter,    "structural"),
    ("broken-links",        check_broken_links,           "structural"),
    ("workspace-structure", check_workspace_structure,     "structural"),
]


def _print_progress(done: int, total: int, label: str, *, final: bool = False) -> None:
    """Print progress: [####....] 5/26 persona-index"""
    width = 20
    filled = int(width * done / total) if total else width
    bar = "#" * filled + "." * (width - filled)
    print(f"  [{bar}] {done}/{total} {label}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="Treat WARNs as ERRORs")
    ap.add_argument("--sequential", action="store_true", help="Run checks sequentially (debug)")
    ap.add_argument(
        "--category",
        choices=["structural", "compliance"],
        default=None,
        help="Run only checks in this category (default: all)",
    )
    args = ap.parse_args()

    eligible = [(name, fn) for name, fn, cat in CHECKS
                 if not args.category or cat == args.category]

    # Pre-read all .md files into memory (single-threaded, sequential I/O).
    # After this, every check function operates on cached data only.
    _warm_cache()

    total = len(eligible)
    all_violations: list[Violation] = []
    if args.sequential:
        for idx, (name, fn) in enumerate(eligible, 1):
            _print_progress(idx, total, name)
            all_violations.extend(fn())
        _print_progress(total, total, "done", final=True)
    else:
        completed = 0
        lock = threading.Lock()
        def _run(fn: object, name: str) -> list[Violation]:
            nonlocal completed
            result = fn()
            with lock:
                completed += 1
                _print_progress(completed, total, name)
            return result
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(eligible))) as pool:
            futures = {pool.submit(_run, fn, name): name for name, fn in eligible}
            done_map: dict[str, list[Violation]] = {}
            for future in as_completed(futures):
                done_map[futures[future]] = future.result()
        _print_progress(total, total, "done", final=True)
        for name, _fn in eligible:
            all_violations.extend(done_map[name])

    errors   = [v for v in all_violations if v.severity == "ERROR"]
    warnings = [v for v in all_violations if v.severity == "WARN"]

    if args.strict:
        errors += warnings
        warnings = []

    if not all_violations:
        print("PASS: All design rules satisfied.")
        return 0

    if warnings:
        print(f"WARN: {len(warnings)} warning(s):")
        for v in warnings:
            print(v)

    if errors:
        print(f"FAIL: {len(errors)} error(s):")
        for v in errors:
            print(v)
        return 1

    # Warnings only → pass
    print(f"PASS (with {len(warnings)} warning(s) — run --strict to treat as errors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
