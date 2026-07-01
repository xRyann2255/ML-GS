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
from datetime import date, timedelta
from pathlib import Path

# Valid domain subfolder names (from meta/guide.md §File Naming).
VALID_DOMAINS = {
    "meta", "person", "slang", "ref", "sys", "domain",
    "ops", "instruments", "infra", "reg", "vendor",
    "decision", "project", "episodic", "research",
}

VALID_STATUSES = {"draft", "active", "stale", "archived"}
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
    "domain": 300,
    "decision": 150,
    "project": 150,
    "episodic": 200,
}

# ── P2 detection via INDEX.md ────────────────────────────────────────────
# Matches rows like: | [ref/foo.md](ref/foo.md) | Desc | P2 | 100 | trigger |
_INDEX_PRI = re.compile(
    r"\|\s*\[([^\]]+)\]\([^)]+\)\s*\|"  # linked path
    r"[^|]*\|"                           # description
    r"\s*(P\d)\s*\|",                    # priority
)


def _load_priority_map(memory_dir: Path) -> dict[str, str]:
    """Return {relative_path: priority} from INDEX.md."""
    index = memory_dir / "INDEX.md"
    if not index.is_file():
        return {}
    text = index.read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in _INDEX_PRI.finditer(text)}


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

    all_errors: list[str] = []
    all_warnings: list[str] = []
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

    # Loaded budget — P0+P1 only (always-loaded + per-task)
    tokens_p01 = total_lines_p01 * 5
    P01_BUDGET = 50_000
    if tokens_p01 > P01_BUDGET:
        all_warnings.append(
            f"loaded memory budget exceeded (P0+P1): ~{tokens_p01} tokens "
            f"({total_lines_p01} lines) > {P01_BUDGET} cap."
        )

    # On-demand budget — P2 (rarely loaded reference)
    tokens_p2 = total_lines_p2 * 5
    P2_BUDGET = 100_000
    if tokens_p2 > P2_BUDGET:
        all_warnings.append(
            f"on-demand memory budget exceeded (P2): ~{tokens_p2} tokens "
            f"({total_lines_p2} lines) > {P2_BUDGET} cap."
        )

    # Summary
    p3_tokens_est = total_lines_p3 * 5
    total_lines_all = total_lines_p01 + total_lines_p2 + total_lines_p3
    total_tokens_all = total_lines_all * 5
    print(f"Validated {len(md_files)} files in {memory_dir}")
    print(f"P0+P1 loaded: {total_lines_p01} lines, ~{tokens_p01} tokens (budget: {P01_BUDGET})")
    print(f"P2 on-demand: {total_lines_p2} lines, ~{tokens_p2} tokens (budget: {P2_BUDGET})")
    print(f"P3 archive: {total_lines_p3} lines, ~{p3_tokens_est} tokens (no cap)")
    print(f"Grand total: {total_lines_all} lines, ~{total_tokens_all} tokens")

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
