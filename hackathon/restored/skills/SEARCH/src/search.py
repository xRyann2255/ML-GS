"""
search.py — Fast skill & memory search with inverted index.

Builds a two-tier inverted index over skills/ and memory/ .md files.
Skills rank higher than memory; memory follows P0 > P1 > P2 > P3 priority.
Index is cached to disk with content hash; warm queries take ~5ms.

Usage:
    python search.py "trade booking lifecycle"
    python search.py "atlas clearing" --top 20
    python search.py "query" --json
    python search.py --rebuild
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import pickle
import re
import sys
import time
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

PRIORITY_BOOST = {"SKILL": 5.0, "P0": 4.0, "P1": 3.0, "P2": 2.0, "P3": 1.0}
FIELD_WEIGHT = {"name": 10, "tags": 8, "trigger": 8, "description": 6, "heading": 4, "body": 1}
DEFAULT_TOP = 10
CACHE_FILENAME = ".search_index.pkl"

# ── Tokenization ───────────────────────────────────────────────────────────────

_SPLIT_RE = re.compile(r"[^a-z0-9]+")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_RE = re.compile(r"^#{1,4}\s+(.+)", re.MULTILINE)
_INDEX_ROW_RE = re.compile(
    r"\|\s*\[([^\]]+)\]\([^)]+\)\s*\|"  # file path
    r"\s*([^|]*)\|"                       # description
    r"\s*(P\d)\s*\|"                      # priority
    r"\s*~?(\d+)\s*\|"                    # tokens
    r"\s*([^|]*)\|",                      # load trigger
)
_SKILL_NAME_RE = re.compile(r"\*\*Name\*\*\s*\|\s*`?([^`|]+)")
_SKILL_SCOPE_RE = re.compile(r"\*\*Scope\*\*\s*\|\s*([^|]+)")


def tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric tokens."""
    return [t for t in _SPLIT_RE.split(text.lower()) if len(t) >= 2]


def bigrams(tokens: list[str]) -> list[str]:
    """Generate underscore-joined bigrams."""
    return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]


# ── Parsing ────────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract YAML frontmatter fields as raw strings."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def parse_index_md(index_path: Path) -> dict[str, dict]:
    """Parse memory/INDEX.md → {file: {priority, tokens, description, trigger}}."""
    entries = {}
    text = index_path.read_text(encoding="utf-8", errors="replace")
    for m in _INDEX_ROW_RE.finditer(text):
        entries[m.group(1)] = {
            "priority": m.group(3),
            "tokens": int(m.group(4)),
            "description": m.group(2).strip(),
            "trigger": m.group(5).strip(),
        }
    return entries


def extract_skill_fields(text: str, path: Path) -> dict[str, list[str]]:
    """Extract structured fields from a SKILL.md file."""
    fields: dict[str, list[str]] = {"name": [], "tags": [], "description": [], "heading": [], "body": []}

    fm = parse_frontmatter(text)
    if fm.get("name"):
        fields["name"].extend(tokenize(fm["name"]))
    if fm.get("description"):
        fields["description"].extend(tokenize(fm["description"]))

    # Skill identity table
    nm = _SKILL_NAME_RE.search(text)
    if nm:
        fields["name"].extend(tokenize(nm.group(1)))
    scope = _SKILL_SCOPE_RE.search(text)
    if scope:
        fields["description"].extend(tokenize(scope.group(1)))

    # Headings
    for hm in _HEADING_RE.finditer(text):
        fields["heading"].extend(tokenize(hm.group(1)))

    # Body tokens (sampled — first 100 unique tokens for pickle size)
    body_tokens = tokenize(text)[:100]
    fields["body"] = list(dict.fromkeys(body_tokens))

    # Folder name as name token
    fields["name"].extend(tokenize(path.parent.name))

    return fields


def extract_memory_fields(text: str, rel_path: str, index_entry: dict | None) -> dict[str, list[str]]:
    """Extract structured fields from a memory .md file."""
    fields: dict[str, list[str]] = {
        "name": [], "tags": [], "trigger": [], "description": [], "heading": [], "body": [],
    }

    # Filename as name
    fields["name"].extend(tokenize(rel_path))

    fm = parse_frontmatter(text)
    if fm.get("tags"):
        # tags: [foo, bar, baz] or foo, bar, baz
        raw = fm["tags"].strip("[]")
        fields["tags"].extend(tokenize(raw))

    # INDEX.md metadata
    if index_entry:
        if index_entry.get("description"):
            fields["description"].extend(tokenize(index_entry["description"]))
        if index_entry.get("trigger"):
            fields["trigger"].extend(tokenize(index_entry["trigger"]))

    # Headings
    for hm in _HEADING_RE.finditer(text):
        fields["heading"].extend(tokenize(hm.group(1)))

    # Body (sampled — first 80 unique tokens)
    body_tokens = tokenize(text)[:80]
    fields["body"] = list(dict.fromkeys(body_tokens))

    return fields


# ── Index Building ─────────────────────────────────────────────────────────────

class SearchIndex:
    """Inverted index with priority-weighted scoring."""

    __slots__ = ("postings", "docs", "content_hash", "_sorted_tokens")

    def __init__(self) -> None:
        # postings: token → list of (doc_id, field_weight)
        self.postings: dict[str, list[tuple[int, int]]] = {}
        # docs: doc_id → {path, source, priority, description}
        self.docs: dict[int, dict] = {}
        self.content_hash: str = ""
        self._sorted_tokens: list[str] = []

    def finalize(self) -> None:
        """Call after all documents are added to enable fast prefix search."""
        self._sorted_tokens = sorted(self.postings.keys())

    def add_document(self, doc_id: int, meta: dict, fields: dict[str, list[str]]) -> None:
        self.docs[doc_id] = meta
        seen: set[tuple[str, int]] = set()
        for field_name, tokens in fields.items():
            w = FIELD_WEIGHT.get(field_name, 1)
            all_tokens = tokens + bigrams(tokens)
            for tok in all_tokens:
                key = (tok, w)
                if key not in seen:
                    seen.add(key)
                    self.postings.setdefault(tok, []).append((doc_id, w))

    def query(self, query_str: str, top_n: int = DEFAULT_TOP) -> list[dict]:
        qtokens = tokenize(query_str)
        qbigrams = bigrams(qtokens)
        all_qtokens = qtokens + qbigrams

        scores: dict[int, float] = {}
        matches: dict[int, list[str]] = {}

        for qt in all_qtokens:
            for doc_id, field_w in self.postings.get(qt, []):
                boost = PRIORITY_BOOST.get(self.docs[doc_id]["priority"], 1.0)
                scores[doc_id] = scores.get(doc_id, 0) + field_w * boost
                matches.setdefault(doc_id, [])
                if qt not in matches[doc_id]:
                    matches[doc_id].append(qt)

            # Prefix matching for single tokens (not bigrams) — bisect for speed
            if "_" not in qt and len(qt) >= 3:
                lo = bisect.bisect_left(self._sorted_tokens, qt)
                prefix_end = qt[:-1] + chr(ord(qt[-1]) + 1)
                hi = bisect.bisect_left(self._sorted_tokens, prefix_end)
                for i in range(lo, hi):
                    tok = self._sorted_tokens[i]
                    if tok == qt or "_" in tok:
                        continue
                    for doc_id, field_w in self.postings[tok]:
                        boost = PRIORITY_BOOST.get(self.docs[doc_id]["priority"], 1.0)
                        scores[doc_id] = scores.get(doc_id, 0) + field_w * boost * 0.5
                        matches.setdefault(doc_id, [])
                        if qt not in matches[doc_id]:
                            matches[doc_id].append(qt)

        results = []
        for doc_id, score in sorted(scores.items(), key=lambda x: -x[1])[:top_n]:
            doc = self.docs[doc_id]
            results.append({
                "rank": len(results) + 1,
                "score": round(score, 1),
                "priority": doc["priority"],
                "path": doc["path"],
                "matched": matches.get(doc_id, []),
                "description": doc.get("description", ""),
            })
        return results


def build_index(repo_root: Path) -> SearchIndex:
    """Build the full inverted index from skills/ and memory/."""
    idx = SearchIndex()
    doc_id = 0

    # ── Skills ─────────────────────────────────────────────────────────────
    skills_dir = repo_root / "skills"
    if skills_dir.is_dir():
        for skill_md in sorted(skills_dir.rglob("SKILL.md")):
            text = skill_md.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(text)
            fields = extract_skill_fields(text, skill_md)
            idx.add_document(doc_id, {
                "path": str(skill_md.relative_to(repo_root)).replace("\\", "/"),
                "source": "skill",
                "priority": "SKILL",
                "description": fm.get("description", skill_md.parent.name),
            }, fields)
            doc_id += 1

    # ── Memory ─────────────────────────────────────────────────────────────
    memory_dir = repo_root / "memory"
    index_path = memory_dir / "INDEX.md"
    index_entries = parse_index_md(index_path) if index_path.is_file() else {}

    if memory_dir.is_dir():
        for md_file in sorted(memory_dir.rglob("*.md")):
            if md_file.name == "INDEX.md":
                continue
            text = md_file.read_text(encoding="utf-8", errors="replace")

            rel = str(md_file.relative_to(memory_dir)).replace("\\", "/")
            ie = index_entries.get(rel)
            priority = ie["priority"] if ie else "P3"

            fields = extract_memory_fields(text, rel, ie)
            desc = ie["description"] if ie else md_file.stem.replace("-", " ")
            idx.add_document(doc_id, {
                "path": f"memory/{rel}",
                "source": "memory",
                "priority": priority,
                "description": desc,
            }, fields)
            doc_id += 1

    idx.content_hash = compute_content_hash(repo_root)
    idx.finalize()
    return idx


# ── Cache ──────────────────────────────────────────────────────────────────────

def get_cache_path(repo_root: Path) -> Path:
    return repo_root / "workspace" / "tmp" / CACHE_FILENAME


def load_or_build(repo_root: Path, force_rebuild: bool = False) -> tuple[SearchIndex, bool]:
    """Load cached index or build fresh. Returns (index, was_rebuilt)."""
    cache_path = get_cache_path(repo_root)

    if not force_rebuild and cache_path.is_file():
        try:
            with open(cache_path, "rb") as f:
                cached: SearchIndex = pickle.load(f)
            # Quick hash check — recompute from file mtimes for speed
            current_hash = compute_content_hash(repo_root)
            if cached.content_hash == current_hash:
                return cached, False
        except Exception:
            pass

    idx = build_index(repo_root)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(idx, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass
    return idx, True


def compute_content_hash(repo_root: Path) -> str:
    """Fast content hash from file sizes and mtimes (avoids reading all files)."""
    hasher = hashlib.md5()
    for d in ["skills", "memory"]:
        root = repo_root / d
        if root.is_dir():
            for md in sorted(root.rglob("*.md")):
                st = md.stat()
                hasher.update(f"{md}:{st.st_size}:{st.st_mtime_ns}".encode())
    return hasher.hexdigest()


# ── Output ─────────────────────────────────────────────────────────────────────

def format_table(results: list[dict], elapsed_ms: float, rebuilt: bool) -> str:
    lines = []
    status = "rebuilt" if rebuilt else "cached"
    lines.append(f"  ({len(results)} results, {elapsed_ms:.1f}ms, index {status})\n")
    lines.append(f"  {'#':>3}  {'Score':>6}  {'Pri':<6} {'Path':<45} Match")
    lines.append(f"  {'─'*3}  {'─'*6}  {'─'*6} {'─'*45} {'─'*20}")
    for r in results:
        matched = ", ".join(r["matched"][:5])
        lines.append(f"  {r['rank']:>3}  {r['score']:>6.1f}  {r['priority']:<6} {r['path']:<45} {matched}")
    return "\n".join(lines)


def format_json(results: list[dict], elapsed_ms: float, rebuilt: bool) -> str:
    return json.dumps({"elapsed_ms": round(elapsed_ms, 1), "rebuilt": rebuilt, "results": results}, indent=2)


# ── Main ───────────────────────────────────────────────────────────────────────

def _write_out(out_file: str | None, text: str) -> None:
    """Write text to out_file if specified."""
    if not out_file:
        return
    p = Path(out_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fast skill & memory search")
    parser.add_argument("query", nargs="?", default="", help="Search query")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help="Max results")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--rebuild", action="store_true", help="Force index rebuild")
    parser.add_argument("--args-file", help="Load args from JSON file")
    parser.add_argument("--out-file", help="Write output to file")
    args = parser.parse_args()

    # --args-file: load JSON and override defaults
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8") as f:
            fa = json.load(f)
        if fa.get("query") and not args.query:
            args.query = fa["query"]
        if "top" in fa:
            args.top = int(fa["top"])
        if fa.get("json"):
            args.json = True
        if fa.get("rebuild"):
            args.rebuild = True
        if fa.get("out_file") and not args.out_file:
            args.out_file = fa["out_file"]

    # Resolve repo root: script is at skills/SEARCH/src/search.py
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent.parent

    t0 = time.perf_counter()
    idx, rebuilt = load_or_build(repo_root, force_rebuild=args.rebuild)
    t_index = time.perf_counter()

    if not args.query:
        if args.rebuild:
            ms = (t_index - t0) * 1000
            output = f"Index rebuilt in {ms:.1f}ms ({len(idx.docs)} documents, {len(idx.postings)} tokens)"
            print(output)
            _write_out(args.out_file, output)
            return 0
        parser.print_help()
        return 0

    results = idx.query(args.query, top_n=args.top)
    t_query = time.perf_counter()
    elapsed_ms = (t_query - t0) * 1000

    if args.json:
        output = format_json(results, elapsed_ms, rebuilt)
    else:
        output = format_table(results, elapsed_ms, rebuilt)

    print(output)
    _write_out(args.out_file, output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
