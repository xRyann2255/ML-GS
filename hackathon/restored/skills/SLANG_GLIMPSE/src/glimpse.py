"""Search Slang scripts and other GS codebases via ELPS (Elastic ProdSource)
or the traditional Glimpse text-search infrastructure.

**Default:** Uses ELPS (Elasticsearch) for Slang script indices -- faster and
supports field searches (source, references, defines, comments, name).
Falls back to Glimpse if ELPS returns no results or is unavailable.
Non-Slang indices (e.g. ``jsi``, ``procmon``) always use Glimpse.

Based on:
- ``_LIB ELPS Search Fns`` / ``_LIB ELPS Config`` (Elasticsearch)
- ``_LIB Glimpse Client Fns`` (Glimpse socket protocol)
Both in ``!NYC EqVol Source``.

Usage examples::

    # Simple search (uses ELPS by default for slangprod)
    python glimpse.py --index slangprod --query "Glimpse::Find"

    # Force Glimpse backend
    python glimpse.py --index slangprod --query "Glimpse::Find" --backend glimpse

    # ELPS field search (references, defines, comments, name)
    python glimpse.py --index slangprod --query "Array::Diff" --field references

    # File list only
    python glimpse.py --index slangprod --query "Glimpse::Find" --files-only

    # JSON output, no comments
    python glimpse.py --index slangprod --query "Glimpse::Find" --json --no-comments

    # Search non-slang index (auto-uses Glimpse)
    python glimpse.py --index jsi --query "some pattern" --files-only

    # List available indices
    python glimpse.py --list-indices
"""
from __future__ import annotations

import argparse
import json
import os
import re
import select
import socket
import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402


# ---------------------------------------------------------------------------
# Constants -- Glimpse
# ---------------------------------------------------------------------------

QUERY_HOST = "glimpsequeryhost.stratinfra.services.gs.com"
QUERY_PORT = 2002

# Sorted list of known Glimpse indices (from _LIB Glimpse Client Fns)
KNOWN_INDICES = sorted([
    "aigdev", "aigpre", "bus", "configdb", "datascope", "dev",
    "eqdev", "eqpre", "eqver",
    "eqtechdev", "eqtechpre", "eqtechver",
    "exchange", "faq",
    "ficcdev", "ficcins", "ficcpre", "ficcver",
    "fiitdev", "fiitpre", "fiitver",
    "fossscripts",
    "gdtechdev", "gdtechpre", "gdtechver",
    "gsatdev", "gsdev", "gsver", "gspre",
    "html", "infra",
    "jfree_modules_dev", "jfree_modules_prod",
    "jsi",
    "linkagedev", "linkagepre", "linkagever",
    "mdpest", "metadir", "ocf", "pre", "procmon",
    "secdb", "secserv64_pre", "sheets",
    "slangarch", "slangdev", "slangprod", "slanguser",
    "symsdev", "symspre", "symsver",
    "truc", "tsdb", "tsdbfunc", "ver", "yams",
])

# Indices where ELPS can be used instead of Glimpse
ELPS_ELIGIBLE_INDICES = {"slangprod", "slangdev", "slanguser", "slangarch"}

# Repo root for default output paths
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_SKILL_DIR, "..", "..", ".."))

# ---------------------------------------------------------------------------
# Constants -- ELPS (Elastic ProdSource)
# ---------------------------------------------------------------------------

ELPS_HOST = "prod.es.elps-core.url.gs.com"
ELPS_PORT = 9200
ELPS_INDEX = "elps_ps_index_frontline"
ELPS_SEARCH_URL = f"http://{ELPS_HOST}:{ELPS_PORT}/{ELPS_INDEX}/_search?pretty=false"

ELPS_FIELDS = ["source", "references", "defines", "comments", "name",
               "links", "scripttype", "length"]
ELPS_DEFAULT_FIELD = "source"

# ---------------------------------------------------------------------------
# Constants -- shared
# ---------------------------------------------------------------------------

# Regex patterns for parsing Glimpse result lines
RX_SCRIPT_LINENUM = re.compile(r"^(.*?) \(([^:]*)\): (\d+): (.*)$")
RX_SCRIPT_NOLINE = re.compile(r"^(.*?) \(([^:]*)\): (.*)$")
RX_FILE_LINENUM = re.compile(r"^([^:]*): (\d+): (.*)$")
RX_FILE_NOLINE = re.compile(r"^([^:]*): (.*)$")

RX_STATUS = re.compile(r"^(Executing: |Warning: |Incorrectly built binary)")
RX_ERROR = re.compile(r"^[A-Za-z/]*glimpse: (.*)")

COMMENT_PREFIXES = ("//", "**", "/*", "#")
RX_SAFE_UNQUOTED = re.compile(r"^[A-Za-z0-9:]+$")

# ELPS highlight tag regex
RX_EM_TAG = re.compile(r"</?em>")
RX_ELPS_LINENUM = re.compile(r"^(\d+);(.*)$")

# ELPS :: escaping regex (matches word:: not inside quotes/field specs)
# Mirrors ELPS Search::Escape Query String from Slang
RX_ELPS_DOUBLE_COLON = re.compile(r"^((?:\w+:)?\w+)::")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GlimpseResult:
    """One parsed search result."""
    script: Optional[str]
    file: str
    line_number: Optional[int]
    line: Optional[str]


# ===========================================================================
# ELPS (Elasticsearch) backend
# ===========================================================================

def _elps_escape_query(query: str) -> str:
    """Prepare a query for ELPS Elasticsearch.

    - Wraps bare terms containing ``::`` in double quotes (phrase query)
      to avoid ES field-syntax errors. Same effect as ELPS Auto Phrase.
    - Leaves already-quoted phrases and field-prefixed terms unchanged.
    """
    # Split preserving quoted strings
    parts = re.split(r'("(?:[^"\\]|\\.)*")', query)
    result_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Inside quotes -- leave as-is
            result_parts.append(part)
        else:
            # Outside quotes -- handle bare :: terms
            tokens = part.split(" ")
            escaped = []
            for token in tokens:
                if "::" in token and not token.startswith('"'):
                    # Check if this is a field:value pattern (single colon prefix)
                    # e.g. references:"Foo::Bar" -- the field part is fine
                    if re.match(r"^\w+:", token) and not token.startswith(token.split(":")[0] + "::"):
                        escaped.append(token)
                    else:
                        # Bare Foo::Bar -- wrap in quotes for phrase match
                        escaped.append(f'"{token}"')
                else:
                    escaped.append(token)
            result_parts.append(" ".join(escaped))
    return "".join(result_parts)


def _get_gssso_cookie() -> str:
    """Obtain a GSSSO cookie via PowerShell Invoke-WebRequest."""
    ps_cmd = (
        '$r = Invoke-WebRequest -Uri "https://authn.web.gs.com/desktopsso/Login" '
        '-UseDefaultCredentials -UseBasicParsing -SessionVariable s; '
        '$c = $s.Cookies.GetCookies("https://authn.web.gs.com") | '
        'Where-Object { $_.Name -eq "GSSSO" }; '
        'if ($c) { $c.Value } else { "NOCOOKIE" }'
    )
    result = run_cmd(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=30,
    )
    cookie = result.stdout.strip()
    if not cookie or cookie == "NOCOOKIE":
        raise RuntimeError(f"Failed to get GSSSO cookie: {result.stderr.strip()}")
    return cookie


def elps_query(
    query_text: str,
    *,
    field: str = ELPS_DEFAULT_FIELD,
    max_docs: int = 500,
    files_only: bool = False,
    timeout: int = 30,
) -> tuple[list[GlimpseResult], list[str]]:
    """Search ELPS and return (results, errors).

    Parameters
    ----------
    query_text : str
        Elasticsearch query_string syntax query.
    field : str
        Field to search (source, references, defines, comments, name, etc.).
    max_docs : int
        Maximum number of documents to return.
    files_only : bool
        If True, don't request highlights -- just return script names.
    timeout : int
        HTTP request timeout in seconds.
    """
    errors: list[str] = []

    try:
        cookie = _get_gssso_cookie()
    except Exception as e:
        return [], [f"GSSSO auth failed: {e}"]

    # Escape :: to avoid ES field-syntax confusion
    escaped_query = _elps_escape_query(query_text)

    body: dict = {
        "size": max_docs,
        "from": 0,
        "query": {
            "query_string": {
                "query": escaped_query,
                "default_field": field,
                "default_operator": "AND",
            }
        },
        "_source": False,
        "sort": [{"_id": "asc"}],
        "track_total_hits": True,
    }

    if not files_only:
        body["highlight"] = {
            "require_field_match": True,
            "number_of_fragments": 2097152,
            "fragment_size": 2097152,
            "fields": {
                "*": {
                    "type": "fvh",
                    "highlight_query": {
                        "query_string": {
                            "query": escaped_query,
                            "default_field": field,
                            "default_operator": "AND",
                        }
                    },
                }
            },
        }

    body_bytes = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        ELPS_SEARCH_URL,
        data=body_bytes,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": f"GSSSO={cookie}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return [], [f"ELPS HTTP {e.code}: {e.reason}"]
    except Exception as e:
        return [], [f"ELPS request failed: {e}"]

    # Parse ES response into GlimpseResult list
    hits_obj = data.get("hits", {})
    total = hits_obj.get("total", {}).get("value", 0)
    hits = hits_obj.get("hits", [])

    results: list[GlimpseResult] = []

    for hit in hits:
        script_name = hit.get("_id", "unknown")

        if files_only:
            results.append(GlimpseResult(
                script=script_name, file="", line_number=None, line=None,
            ))
            continue

        # Extract highlighted fragments
        highlight = hit.get("highlight", {})
        frags: list[str] = []
        for hl_field in [field, "source", "references", "defines", "comments"]:
            if hl_field in highlight:
                frags = highlight[hl_field]
                break
        if not frags:
            for v in highlight.values():
                frags = v
                break

        if not frags:
            results.append(GlimpseResult(
                script=script_name, file="", line_number=None, line=None,
            ))
            continue

        # Parse fragments: format is "linenum;content" with <em> tags
        for frag in frags:
            clean_frag = RX_EM_TAG.sub("", frag)
            for sub_line in clean_frag.split("\n"):
                m = RX_ELPS_LINENUM.match(sub_line)
                if m:
                    line_num = int(m.group(1))
                    content = m.group(2)
                    results.append(GlimpseResult(
                        script=script_name,
                        file="",
                        line_number=line_num,
                        line=content,
                    ))

    print(f"[ELPS] {total} total matches, {len(results)} result lines", file=sys.stderr)
    return results, errors


# ===========================================================================
# Glimpse (socket) backend
# ===========================================================================

def glimpse_protect(pattern: str) -> str:
    """Quote a pattern for glimpse if it contains special characters or spaces."""
    if RX_SAFE_UNQUOTED.match(pattern):
        return pattern
    if (pattern.startswith('"') and pattern.endswith('"')) or \
       (pattern.startswith("'") and pattern.endswith("'")):
        return pattern
    escaped = pattern.replace('"', '\\"')
    return f'"{escaped}"'


def glimpse_query(
    index: str,
    pattern: str,
    *,
    files_only: bool = False,
    case_sensitive: bool = False,
    extra_flags: str = "",
    username: Optional[str] = None,
    timeout: int = 30,
) -> tuple[list[str], list[str]]:
    """Send a query to the Glimpse server and return (result_lines, errors)."""
    if username is None:
        username = os.environ.get("USERNAME", "unknown").lower()

    flags_parts = []
    if not case_sensitive:
        flags_parts.append("-i")
    if files_only:
        flags_parts.append("-l")
    else:
        flags_parts.append("-n")
    if extra_flags:
        flags_parts.append(extra_flags)

    flags = " ".join(flags_parts)
    protected_pattern = glimpse_protect(pattern)
    query_str = (
        f"~{username}~ -H /local/data/glimpse/indices/{index} -y "
        f"{flags} {protected_pattern}"
    )

    sock = socket.create_connection((QUERY_HOST, QUERY_PORT), timeout=timeout)
    try:
        sock.sendall(query_str.encode("ascii"))
        sock.shutdown(socket.SHUT_WR)

        data = b""
        while True:
            ready, _, _ = select.select([sock], [], [], timeout)
            if not ready:
                break
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
    finally:
        sock.close()

    raw_lines = data.decode("ascii", errors="replace").splitlines()

    results: list[str] = []
    errors: list[str] = []
    for raw in raw_lines:
        if RX_STATUS.match(raw):
            continue
        m = RX_ERROR.match(raw)
        if m:
            errors.append(m.group(1))
            continue
        results.append(raw)

    return results, errors


def parse_glimpse_results(
    lines: list[str],
    *,
    files_only: bool = False,
) -> list[GlimpseResult]:
    """Parse raw Glimpse output lines into structured results."""
    results: list[GlimpseResult] = []

    for line in lines:
        if not line.strip():
            continue

        if files_only:
            results.append(GlimpseResult(
                script=None, file=line.strip(), line_number=None, line=None,
            ))
            continue

        m = RX_SCRIPT_LINENUM.match(line)
        if m:
            results.append(GlimpseResult(
                script=m.group(1), file=m.group(2),
                line_number=int(m.group(3)), line=m.group(4),
            ))
            continue

        m = RX_SCRIPT_NOLINE.match(line)
        if m:
            results.append(GlimpseResult(
                script=m.group(1), file=m.group(2),
                line_number=None, line=m.group(3),
            ))
            continue

        m = RX_FILE_LINENUM.match(line)
        if m:
            results.append(GlimpseResult(
                script=None, file=m.group(1),
                line_number=int(m.group(2)), line=m.group(3),
            ))
            continue

        m = RX_FILE_NOLINE.match(line)
        if m:
            results.append(GlimpseResult(
                script=None, file=m.group(1),
                line_number=None, line=m.group(2),
            ))
            continue

        results.append(GlimpseResult(
            script=None, file=line, line_number=None, line=None,
        ))

    return results


# ===========================================================================
# Shared helpers
# ===========================================================================

def filter_comments(results: list[GlimpseResult]) -> list[GlimpseResult]:
    """Remove results where the matched line is a comment."""
    filtered = []
    for r in results:
        if r.line is not None:
            stripped = r.line.lstrip()
            if any(stripped.startswith(p) for p in COMMENT_PREFIXES):
                continue
        filtered.append(r)
    return filtered


def format_text(results: list[GlimpseResult], *, files_only: bool = False) -> str:
    """Format results as human-readable text."""
    lines: list[str] = []
    for r in results:
        if files_only:
            if r.script:
                if r.file:
                    lines.append(f"{r.script} ({r.file})")
                else:
                    lines.append(r.script)
            else:
                lines.append(r.file)
        elif r.line_number is not None:
            if r.script and r.file:
                prefix = f"{r.script} ({r.file})"
            elif r.script:
                prefix = r.script
            else:
                prefix = r.file
            lines.append(f"{prefix}: {r.line_number}: {r.line}")
        else:
            if r.script and r.file:
                prefix = f"{r.script} ({r.file})"
            elif r.script:
                prefix = r.script
            else:
                prefix = r.file
            if r.line:
                lines.append(f"{prefix}: {r.line}")
            else:
                lines.append(prefix)
    return "\n".join(lines)


def format_json(results: list[GlimpseResult]) -> str:
    """Format results as JSON."""
    return json.dumps([asdict(r) for r in results], indent=2)


# ===========================================================================
# CLI
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Search GS codebases via ELPS (Elasticsearch) or Glimpse.",
    )
    p.add_argument("--index", type=str,
                   help="Glimpse index name (e.g. slangprod)")
    p.add_argument("--query", type=str,
                   help="Search pattern")
    p.add_argument("--backend", type=str, choices=["auto", "elps", "glimpse"],
                   default="auto",
                   help="Search backend: auto (default), elps, or glimpse")
    p.add_argument("--field", type=str, default=ELPS_DEFAULT_FIELD,
                   choices=ELPS_FIELDS,
                   help="ELPS field to search (default: source)")
    p.add_argument("--files-only", action="store_true",
                   help="Return only file/script names, not matched lines")
    p.add_argument("--case-sensitive", action="store_true",
                   help="Case-sensitive search (default: case-insensitive)")
    p.add_argument("--no-comments", action="store_true",
                   help="Filter out comment lines from results")
    p.add_argument("--flags", type=str, default="",
                   help="Additional raw glimpse flags (e.g. -w for whole word)")
    p.add_argument("--max-results", type=int, default=0,
                   help="Maximum number of results to return (0 = unlimited)")
    p.add_argument("--max-docs", type=int, default=500,
                   help="ELPS: max documents to return (default: 500)")
    p.add_argument("--username", type=str, default=None,
                   help="Override login name sent to Glimpse")
    p.add_argument("--list-indices", action="store_true",
                   help="List all known Glimpse index names and exit")
    p.add_argument("--json", action="store_true",
                   help="Output results as JSON")
    p.add_argument("--timeout", type=int, default=30,
                   help="Request timeout in seconds (default: 30)")
    p.add_argument("--args-file", default=None, metavar="PATH",
                   help="JSON file with search arguments (keys mirror CLI flags)")
    p.add_argument("--output-json", default=None, metavar="PATH",
                   help="Write machine-readable JSON results to PATH (with sentinel)")
    return p


def _choose_backend(args) -> str:
    """Determine which backend to use."""
    if args.backend != "auto":
        return args.backend
    if args.index in ELPS_ELIGIBLE_INDICES:
        return "elps"
    return "glimpse"


def _run_elps(args) -> tuple[list[GlimpseResult], list[str]]:
    """Run ELPS search."""
    return elps_query(
        args.query,
        field=args.field,
        max_docs=args.max_docs,
        files_only=args.files_only,
        timeout=args.timeout,
    )


def _run_glimpse(args) -> tuple[list[GlimpseResult], list[str]]:
    """Run Glimpse search."""
    raw_lines, errors = glimpse_query(
        args.index,
        args.query,
        files_only=args.files_only,
        case_sensitive=args.case_sensitive,
        extra_flags=args.flags,
        username=args.username,
        timeout=args.timeout,
    )
    results = parse_glimpse_results(raw_lines, files_only=args.files_only)
    print(f"[Glimpse] {len(results)} result lines", file=sys.stderr)
    return results, errors


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # ---------- Load from args-file if provided ----------
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8") as af:
            af_data = json.load(af)
        if not args.index and af_data.get("index"):
            args.index = af_data["index"]
        if not args.query and af_data.get("query"):
            args.query = af_data["query"]
        if af_data.get("backend") and args.backend == "auto":
            args.backend = af_data["backend"]
        if af_data.get("field") and args.field == ELPS_DEFAULT_FIELD:
            args.field = af_data["field"]
        if af_data.get("files_only"):
            args.files_only = True
        if af_data.get("case_sensitive"):
            args.case_sensitive = True
        if af_data.get("no_comments"):
            args.no_comments = True
        if af_data.get("flags") and not args.flags:
            args.flags = af_data["flags"]
        if af_data.get("max_results") and args.max_results == 0:
            args.max_results = af_data["max_results"]
        if af_data.get("max_docs") and args.max_docs == 500:
            args.max_docs = af_data["max_docs"]
        if af_data.get("json"):
            args.json = True
        if af_data.get("output_json") and not args.output_json:
            args.output_json = af_data["output_json"]
        if af_data.get("timeout") and args.timeout == 30:
            args.timeout = af_data["timeout"]
        if af_data.get("run_id"):
            args.run_id = af_data["run_id"]

    run_id = getattr(args, "run_id", None) or ""

    # ---------- Write sentinel (signals "running") ----------
    json_path = args.output_json
    if not json_path:
        json_path = os.path.join(_REPO_ROOT, "workspace", "tmp",
                                 "slang_glimpse_results.json")
    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump({"status": "running", "run_id": run_id}, jf, indent=2)

    # --list-indices
    if args.list_indices:
        indices = list(KNOWN_INDICES)
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump({"status": "done", "run_id": run_id,
                        "indices": indices}, jf, indent=2)
        for idx in indices:
            print(idx)
        return 0

    # Validate
    if not args.index:
        parser.error("--index is required (use --list-indices to see options)")
    if not args.query:
        parser.error("--query is required")

    backend = _choose_backend(args)
    results: list[GlimpseResult] = []
    errors: list[str] = []

    if backend == "elps":
        results, errors = _run_elps(args)
        # Fallback to Glimpse if ELPS returned nothing or errored
        if not results and args.backend == "auto":
            print("[ELPS] No results -- falling back to Glimpse...", file=sys.stderr)
            results, errors = _run_glimpse(args)
    else:
        results, errors = _run_glimpse(args)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)

    # Filter comments
    if args.no_comments:
        results = filter_comments(results)

    # Limit
    if args.max_results > 0:
        results = results[:args.max_results]

    # Output
    if args.json:
        print(format_json(results))
    else:
        print(format_text(results, files_only=args.files_only))

    # Summary to stderr
    print(f"\n{len(results)} results", file=sys.stderr)

    # ---------- Write final sentinel (signals "done") ----------
    result_obj = {
        "status": "done",
        "run_id": run_id,
        "backend": backend,
        "count": len(results),
        "errors": errors,
        "results": [asdict(r) for r in results],
    }
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(result_obj, jf, indent=2)

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
