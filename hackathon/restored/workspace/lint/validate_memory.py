"""
validate_memory.py — Enforce CoALA memory schema rules.

Validates memory files stored in domain subfolders under memory/.
Rules from memory/meta/guide.md and memory/design.md:

  1. Required frontmatter fields: created, updated, tags, status
  2. Valid status: draft | active | stale | archived
  3. No broken relates: every relates: entry must exist under memory/
  4. Date ordering: updated >= created
  5. Naming: lowercase with hyphens, no spaces/underscores
  6. Domain subfolder must be a recognized domain
  7. Size limits per domain (soft caps, warnings only)
  8. Trust gates: agent-inferred → draft + low confidence
  9. Loaded budget: P0+P1 ≤ 50k tokens
 10. On-demand budget: P2 ≤ 100k tokens
 11. P3: no total budget (per-file caps only)
"""

import sys
import re
import math
from datetime import date, timedelta
from pathlib import Path

# The 10 domains of memory/meta/guide.md §Domains (7 active + 3 reserved).
# Single source of truth — design_lint.py mirrors this set (wfo-04-3).
VALID_DOMAINS = {
    "meta", "person", "slang", "ref", "sys", "research", "vendor",
    "decision", "project", "episodic",
}

VALID_STATUSES = {"draft", "active", "stale", "archived", "dormant"}
REQUIRED_FIELDS = {"created", "updated", "tags", "status"}

# Root-level files excluded from content validation.
GOVERNANCE_FILES = {"INDEX.md", "design.md", "README.md", "readme.md"}

# Size limits per domain (soft caps in lines).
DOMAIN_SIZE_LIMITS = {
    "meta": 200,
    "person": 100,
    "slang": 400,
    "ref": 250,
    "sys": 200,
    "research": 300,  # wfo-04-3: busiest domain finally capped (soft WARN, like ref)
    "decision": 150,
    "project": 150,
    "episodic": 200,
}

# ── P2 detection via INDEX.md ────────────────────────────────────────────
# Matches INDEX.md rows in either style (link OR raw path):
#   | [ref/foo.md](ref/foo.md) | Desc | P2 | 100 | trigger |
#   | workspace/research/trials.yaml | Desc | P1 | varies | trigger |
_INDEX_PRI = re.compile(
    r"\|\s*"
    r"(?:\[([^\]]+)\]\([^)]+\)|([A-Za-z0-9_\-./]+\.[A-Za-z0-9]+))"
    r"\s*\|"                       # path column (link OR raw)
    r"[^|]*\|"                     # description
    r"\s*(P\d)\s*\|",              # priority
)


def _load_priority_map(memory_dir: Path) -> dict[str, str]:
    """Return {relative_path: priority} from INDEX.md.

    Paths are recorded as INDEX prints them: memory-relative for local rows
    and `workspace/…`, `src/…`, `.github/…` for cross-tree rows.
    """
    index = memory_dir / "INDEX.md"
    if not index.is_file():
        return {}
    text = index.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for m in _INDEX_PRI.finditer(text):
        path_str = m.group(1) or m.group(2)
        result[path_str] = m.group(3)
    return result


# ── Grandfather + path resolution (shared with lint_memory_priority.py) ──
WHITELIST_DIR = Path(__file__).resolve().parent / "whitelists"


def _load_budget_grandfather() -> dict[str, int]:
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


def _resolve_entry_path(repo_root: Path, index_path_str: str) -> Path:
    """INDEX paths are memory/-relative unless they start with workspace/, src/, .github/."""
    if index_path_str.startswith(("workspace/", "src/", ".github/")):
        return repo_root / index_path_str
    return repo_root / "memory" / index_path_str


def _measured_tokens(p: Path) -> int:
    """bytes/4, the suite-wide heuristic (ledger row 'Memory-budget fix')."""
    return math.ceil(p.stat().st_size / 4)


def parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from markdown text. Returns dict or None."""
    text = text.lstrip("\ufeff")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    fm: dict = {}
    current_list_key = None
    for line in m.group(1).splitlines():
        kv = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip().strip('"').strip("'")
            if key in ("relates", "tags"):
                if val.startswith("["):
                    fm[key] = [t.strip().strip('"').strip("'")
                               for t in val.strip("[]").split(",") if t.strip()]
                else:
                    fm[key] = []
                current_list_key = key
            else:
                fm[key] = val
                current_list_key = None
        elif line.strip().startswith("- ") and current_list_key:
            item = line.strip()[2:].strip().strip('"').strip("'")
            fm.setdefault(current_list_key, []).append(item)
    return fm


def validate_file(
    path: Path, memory_dir: Path, priority_map: dict[str, str],
) -> tuple[list[str], list[str], int]:
    """Validate a single memory file. Returns (errors, warnings, line_count)."""
    errors: list[str] = []
    warnings: list[str] = []
    rel = str(path.relative_to(memory_dir)).replace("\\", "/")
    file_pri = priority_map.get(rel, "")
    is_p2 = file_pri == "P2"
    is_p3 = file_pri == "P3"

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{rel}: cannot read file: {e}"], [], 0

    # Domain = immediate parent folder name
    domain = path.parent.name if path.parent != memory_dir else None

    # Validate domain subfolder
    if domain and domain not in VALID_DOMAINS:
        errors.append(f"{rel}: unrecognized domain subfolder '{domain}' (valid: {sorted(VALID_DOMAINS)})")

    # No deeper than one subfolder
    depth = len(path.relative_to(memory_dir).parts)
    if depth > 2:
        errors.append(f"{rel}: nested too deep (max depth is memory/<domain>/<file>.md)")

    # Parse frontmatter
    fm = parse_frontmatter(text)
    line_count_early = text.rstrip("\n\r").count("\n") + 1
    if fm is None:
        return [f"{rel}: missing YAML frontmatter (no --- ... --- block)"] + errors, warnings, line_count_early

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in fm or not fm[field]:
            errors.append(f"{rel}: missing required field '{field}'")

    created = fm.get("created", "")
    updated = fm.get("updated", "")
    status = fm.get("status", "")

    # Valid status
    if status and status not in VALID_STATUSES:
        errors.append(f"{rel}: invalid status '{status}' (valid: {VALID_STATUSES})")

    # Date ordering
    if created and updated:
        c_str, u_str = str(created)[:10], str(updated)[:10]
        try:
            if u_str < c_str:
                errors.append(f"{rel}: updated ({u_str}) < created ({c_str})")
        except (TypeError, ValueError):
            errors.append(f"{rel}: cannot compare dates created='{created}' updated='{updated}'")

    # Date format
    if updated and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(updated)):
        errors.append(f"{rel}: 'updated' field is not a clean date: '{updated}'")
    if created and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(created)):
        errors.append(f"{rel}: 'created' field is not a clean date: '{created}'")

    # Naming: lowercase, hyphens, no spaces/underscores
    stem = path.stem
    if " " in stem:
        errors.append(f"{rel}: filename contains spaces")
    if "_" in stem:
        errors.append(f"{rel}: filename contains underscores (use hyphens)")

    # No broken relates
    relates = fm.get("relates", [])
    if isinstance(relates, list):
        for ref in relates:
            ref_clean = ref.split("#")[0].strip()
            if not ref_clean:
                continue
            # Try exact path first, then same-domain resolution (<domain>/<ref>.md)
            candidates = [memory_dir / ref_clean]
            if domain:
                candidates.append(memory_dir / domain / f"{ref_clean}.md")
                candidates.append(memory_dir / domain / ref_clean)
            if not any(c.exists() for c in candidates):
                errors.append(f"{rel}: broken relates reference '{ref_clean}'")

    # Trust gates
    source = fm.get("source", "")
    confidence = fm.get("confidence", "")
    if source == "agent-inferred":
        if status != "draft":
            errors.append(f"{rel}: source=agent-inferred requires status=draft (got '{status}')")
        if confidence and confidence != "low":
            errors.append(f"{rel}: source=agent-inferred requires confidence=low (got '{confidence}')")

    # Size limits (warn only, skip P2 and P3; immutable files use 1000-line cap)
    line_count = text.rstrip("\n\r").count("\n") + 1
    is_immutable = str(fm.get("immutable", "")).lower() == "true"
    if domain and not is_p2 and not is_p3:
        if is_immutable:
            cap = 1000
            if line_count > cap:
                warnings.append(f"{rel}: {line_count} lines exceeds immutable cap of {cap}")
        elif domain in DOMAIN_SIZE_LIMITS:
            cap = DOMAIN_SIZE_LIMITS[domain]
            if line_count > cap:
                warnings.append(f"{rel}: {line_count} lines exceeds {domain} soft cap of {cap}")

    return errors, warnings, line_count


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    memory_dir = repo_root / "memory"

    if not memory_dir.is_dir():
        print(f"ERROR: memory directory not found at {memory_dir}")
        return 2

    # Collect all .md files in domain subfolders (skip root governance files)
    # Skip _archived/ and _dormant/ — these are intentionally parked outside active domains
    SKIP_PREFIXES = {"_archived", "_dormant"}
    md_files: list[Path] = []
    for p in sorted(memory_dir.rglob("*.md")):
        rel = p.relative_to(memory_dir)
        # Skip files under _archived/ or _dormant/
        if rel.parts[0] in SKIP_PREFIXES:
            continue
        # Skip root-level governance files
        if len(rel.parts) == 1 and rel.name in GOVERNANCE_FILES:
            continue
        # Skip governance files in domain subfolders (e.g., research/README.md)
        if len(rel.parts) == 2 and rel.name in GOVERNANCE_FILES:
            continue
        # Skip root-level INDEX.md (not a content file)
        if len(rel.parts) == 1:
            continue
        md_files.append(p)

    if not md_files:
        print(f"No content .md files found in {memory_dir}")
        return 0

    priority_map = _load_priority_map(memory_dir)
    repo_root = memory_dir.parent
    grandfather = _load_budget_grandfather()

    all_errors: list[str] = []
    all_warnings: list[str] = []

    # ── Per-file frontmatter/schema/naming validation (memory/**.md only) ──
    # The line-count-based totals here are informational only; the enforced
    # budget below re-measures every INDEX-listed file (memory + workspace/…)
    # in bytes/4 tokens per the ledger row 'Memory-budget fix'.
    total_lines_p01 = 0
    total_lines_p2 = 0
    total_lines_p3 = 0

    for path in md_files:
        errs, warns, lc = validate_file(path, memory_dir, priority_map)
        all_errors.extend(errs)
        all_warnings.extend(warns)
        rel = str(path.relative_to(memory_dir)).replace("\\", "/")
        pri = priority_map.get(rel, "")
        if pri == "P3":
            total_lines_p3 += lc
        elif pri == "P2":
            total_lines_p2 += lc
        else:
            total_lines_p01 += lc

    # ── Enforced budgets: measured bytes/4 across every INDEX-listed file ──
    # (includes non-.md rows such as workspace/research/trials.yaml and any
    # INDEX rows resolving under workspace/, src/, or .github/).
    p01_honest = 0            # sum of measured tokens (all P0+P1 rows)
    p01_counted = 0           # honest minus grandfathered (the enforced number)
    p2_honest = 0
    p2_counted = 0
    gf_excess: list[tuple[str, int, int]] = []
    for entry_path_str, pri in priority_map.items():
        if pri not in {"P0", "P1", "P2"}:
            continue
        p = _resolve_entry_path(repo_root, entry_path_str)
        if not p.is_file():
            continue  # missing files reported by lint_memory_index_completeness.py G3
        t = _measured_tokens(p)
        gf_key = str(p.relative_to(repo_root)).replace("\\", "/")
        bucket_honest = t
        bucket_counted = t
        if gf_key in grandfather:
            if t > grandfather[gf_key]:
                gf_excess.append((gf_key, t, grandfather[gf_key]))
            bucket_counted = 0
        if pri in {"P0", "P1"}:
            p01_honest += bucket_honest
            p01_counted += bucket_counted
        else:  # P2
            p2_honest += bucket_honest
            p2_counted += bucket_counted

    P01_BUDGET = 50_000
    P2_BUDGET = 100_000

    if p01_counted > P01_BUDGET:
        all_errors.append(
            f"loaded memory budget exceeded (P0+P1): measured (bytes/4) ~{p01_honest} tokens; "
            f"enforced (non-grandfathered) ~{p01_counted} > {P01_BUDGET} cap."
        )
    if p2_counted > P2_BUDGET:
        all_errors.append(
            f"on-demand memory budget exceeded (P2): measured (bytes/4) ~{p2_honest} tokens; "
            f"enforced (non-grandfathered) ~{p2_counted} > {P2_BUDGET} cap."
        )
    for gf_path, meas, cap in gf_excess:
        all_errors.append(
            f"grandfathered `{gf_path}` grew: measured ~{meas} > recorded ceiling {cap}."
        )

    # Summary
    total_lines_all = total_lines_p01 + total_lines_p2 + total_lines_p3
    print(f"Validated {len(md_files)} files in {memory_dir}")
    print(
        f"P0+P1 measured (bytes/4): ~{p01_honest} tokens; "
        f"enforced (non-grandfathered): ~{p01_counted} (budget: {P01_BUDGET})"
    )
    print(
        f"P2 measured (bytes/4): ~{p2_honest} tokens; "
        f"enforced (non-grandfathered): ~{p2_counted} (budget: {P2_BUDGET})"
    )
    print(f"P3 (memory-local .md only): {total_lines_p3} lines (no cap)")
    print(f"memory/**.md lines total: {total_lines_all}")

    if all_warnings:
        print(f"\n{len(all_warnings)} warning(s):\n")
        for w in all_warnings:
            print(f"  WARN  {w}")

    if all_errors:
        print(f"\n{len(all_errors)} error(s):\n")
        for e in all_errors:
            print(f"  ERROR {e}")
        return 1
    else:
        print("PASS: All files pass validation.")
        return 0


def _entry_point():
    sys.exit(main())


if __name__ == "__main__":
    _entry_point()
