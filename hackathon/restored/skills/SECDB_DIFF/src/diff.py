"""Compare instream (stored VT) values between two SecDB securities.

Reuses SECDB_INSPECT/src/inspect.py for the heavy lifting (secexpr calls,
trace parsing) and adds side-by-side diff logic on top.

Usage:
    python diff.py --sec1 "EqF ESM26" --sec2 "EqF ESU26"
    python diff.py --sec1 "EqF ESM26" --sec2 "EqF ESU26" --diff-only
    python diff.py --sec1 "EqF ESM26" --sec2 "EqF ESU26" --format table
    python diff.py --sec1 "Trade A" --book1 "BOOKX" --sec2 "Trade B" --book2 "BOOKY"
"""
import argparse
import datetime
import json
import math
import os
import sys

# ---------------------------------------------------------------------------
# Bootstrap: import from SECDB_INSPECT (avoid shadowing stdlib inspect)
# ---------------------------------------------------------------------------
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
INSPECT_SRC = os.path.join(SKILL_DIR, "..", "..", "SECDB_INSPECT", "src")

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "secdb_inspect", os.path.join(INSPECT_SRC, "inspect.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_log_dir = _mod._log_dir
_info = _mod._info
_parse_kv_from_trace = _mod._parse_kv_from_trace
_parse_meta = _mod._parse_meta
build_db_resolve_slang = _mod.build_db_resolve_slang
build_slang = _mod.build_slang
run_slang = _mod.run_slang
DEFAULT_DB = _mod.DEFAULT_DB
DEFAULT_SOURCE = _mod.DEFAULT_SOURCE

_REPO_ROOT = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))

FORMAT_JSON = "json"
FORMAT_TABLE = "table"
VALID_FORMATS = (FORMAT_JSON, FORMAT_TABLE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _try_float(s: str) -> float | None:
    """Attempt to parse a string as float. Returns None if not numeric."""
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _values_match(v1: str, v2: str, tolerance: float | None) -> bool:
    """Compare two instream values. Uses numeric tolerance when both are floats."""
    if v1 == v2:
        return True
    if tolerance is not None:
        f1, f2 = _try_float(v1), _try_float(v2)
        if f1 is not None and f2 is not None:
            return math.isclose(f1, f2, abs_tol=tolerance)
    return False


# ---------------------------------------------------------------------------
# Fetch instream for one security → dict
# ---------------------------------------------------------------------------

def fetch_instream(
    sec: str,
    db: str,
    source: str,
    book: str | None,
    recurse: bool,
    timeout: int,
    log_dir: str,
) -> tuple[dict[str, str], str, str]:
    """Fetch instream KV pairs for a single security.

    Returns (fields_dict, sec_type, sec_desc).
    Raises SystemExit on fatal errors.
    """
    resolved_db = db

    # Phase 1: resolve trade DB from book if needed
    if book:
        db_slang = build_db_resolve_slang(book)
        rc, stdout, stderr = run_slang(
            slang_code=db_slang,
            db=db,
            source=source,
            log_dir=log_dir,
            timeout=timeout,
        )
        if rc == -1:
            print(f"\nERROR: secexpr timed out resolving trade DB for book '{book}'.", file=sys.stderr)
            sys.exit(1)
        resolved_db = _parse_meta(stdout, "===TRADE_DB=")
        if resolved_db == "Unknown" or not resolved_db:
            print(f"\nERROR: Could not resolve trade DB for book '{book}'.", file=sys.stderr)
            sys.exit(1)
        _info(f"Resolved trade DB for '{sec}': {resolved_db}")

    # Phase 2: DiskInstreamValues
    slang = build_slang(sec, recurse)
    rc, stdout, stderr = run_slang(
        slang_code=slang,
        db=resolved_db,
        source=source,
        log_dir=log_dir,
        timeout=timeout,
    )

    if rc == -1:
        print(f"\nERROR: secexpr timed out for '{sec}'.", file=sys.stderr)
        sys.exit(1)
    if rc != 0 and not stdout.strip():
        print(f"\nERROR: secexpr rc={rc} for '{sec}'. Check logs: {log_dir}", file=sys.stderr)
        sys.exit(1)

    sec_type = _parse_meta(stdout, "===SEC_TYPE=")
    sec_desc = _parse_meta(stdout, "===SEC_DESC=")

    pairs = _parse_kv_from_trace(stderr)
    fields: dict[str, str] = {}
    seen: dict[str, int] = {}
    for k, v in pairs:
        if k in fields:
            # Duplicate key from recursive trace — disambiguate with suffix
            seen.setdefault(k, 1)
            seen[k] += 1
            fields[f"{k} [{seen[k]}]"] = v
        else:
            fields[k] = v

    return fields, sec_type, sec_desc


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------

def compute_diff(
    fields1: dict[str, str],
    fields2: dict[str, str],
    tolerance: float | None = None,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Compare two field dicts. Returns (differences, only1, only2, matches)."""
    all_keys = sorted(set(fields1) | set(fields2))

    differences = []
    only_sec1 = []
    only_sec2 = []
    matches = []

    for k in all_keys:
        in1 = k in fields1
        in2 = k in fields2

        if in1 and in2:
            v1, v2 = fields1[k], fields2[k]
            if _values_match(v1, v2, tolerance):
                matches.append({"field": k, "value": v1})
            else:
                differences.append({"field": k, "sec1": v1, "sec2": v2, "status": "differ"})
        elif in1:
            only_sec1.append({"field": k, "sec1": fields1[k], "sec2": None, "status": "only_sec1"})
        else:
            only_sec2.append({"field": k, "sec1": None, "sec2": fields2[k], "status": "only_sec2"})

    return differences, only_sec1, only_sec2, matches


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_json(
    sec1: str, sec2: str,
    differences: list, only1: list, only2: list, matches: list,
    diff_only: bool,
) -> str:
    total = len(differences) + len(only1) + len(only2) + len(matches)
    result = {
        "sec1": sec1,
        "sec2": sec2,
        "summary": {
            "total": total,
            "match": len(matches),
            "differ": len(differences),
            "only_sec1": len(only1),
            "only_sec2": len(only2),
        },
        "differences": differences,
        "only_sec1": only1,
        "only_sec2": only2,
    }
    if not diff_only:
        result["matches"] = matches
    return json.dumps(result, indent=2, ensure_ascii=False)


def format_table(
    sec1: str, sec2: str,
    sec1_type: str, sec2_type: str,
    sec1_desc: str, sec2_desc: str,
    differences: list, only1: list, only2: list, matches: list,
    diff_only: bool,
) -> str:
    lines = []
    lines.append(f"  sec1: {sec1}  ({sec1_type})  {sec1_desc}")
    lines.append(f"  sec2: {sec2}  ({sec2_type})  {sec2_desc}")
    lines.append("")

    # Build rows
    rows = []
    for d in differences:
        rows.append((d["field"], d["sec1"], d["sec2"], "DIFFER"))
    for d in only1:
        rows.append((d["field"], d["sec1"], "\u2014", "ONLY sec1"))
    for d in only2:
        rows.append((d["field"], "\u2014", d["sec2"], "ONLY sec2"))
    if not diff_only:
        for m in matches:
            rows.append((m["field"], m["value"], m["value"], "match"))

    if not rows:
        lines.append("  (no fields to display)")
        return "\n".join(lines)

    # Column widths
    hdr = ("Field", f"sec1", f"sec2", "Status")
    col_w = [len(h) for h in hdr]
    for row in rows:
        for i, cell in enumerate(row):
            col_w[i] = max(col_w[i], len(str(cell or "")))

    # Cap column widths at 50 to keep readable
    col_w = [min(w, 50) for w in col_w]

    def fmt_row(cells):
        parts = []
        for i, c in enumerate(cells):
            s = str(c or "")
            if len(s) > col_w[i]:
                s = s[:col_w[i] - 1] + "\u2026"
            parts.append(s.ljust(col_w[i]))
        return "  " + " | ".join(parts)

    lines.append(fmt_row(hdr))
    lines.append("  " + "-+-".join("-" * w for w in col_w))
    for row in rows:
        lines.append(fmt_row(row))

    # Summary
    n_diff = len(differences) + len(only1) + len(only2)
    n_match = len(matches)
    lines.append("")
    lines.append(f"  Summary: {n_diff} difference(s), {n_match} match(es), {n_diff + n_match} total field(s)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare instream values between two SecDB securities.",
    )
    parser.add_argument("--sec1", required=False, default=None, help="First security name or object ID")
    parser.add_argument("--sec2", required=False, default=None, help="Second security name or object ID")
    parser.add_argument("--book1", default=None, help="Book for sec1 (trade DB resolution)")
    parser.add_argument("--book2", default=None, help="Book for sec2 (trade DB resolution)")
    parser.add_argument("--db1", default=DEFAULT_DB, help=f"DB for sec1 (default: {DEFAULT_DB})")
    parser.add_argument("--db2", default=DEFAULT_DB, help=f"DB for sec2 (default: {DEFAULT_DB})")
    parser.add_argument("--recurse", action="store_true", default=False,
                        help="Recurse into nested securities")
    parser.add_argument("--diff-only", action="store_true", default=False,
                        help="Show only differing/missing fields (suppress matches)")
    parser.add_argument("--format", default=FORMAT_JSON, choices=VALID_FORMATS,
                        dest="output_format", help=f"Output format (default: {FORMAT_JSON})")
    parser.add_argument("--tolerance", type=float, default=None,
                        help="Numeric tolerance for float comparison (e.g. 0.01). Default: exact string match")
    parser.add_argument("--output", default=None,
                        help="Write output to workspace/tmp/<name> instead of stdout")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help=f"Source chain (default: {DEFAULT_SOURCE})")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per secexpr call (default: 120)")
    parser.add_argument("--args-file", default=None, metavar="PATH",
                        help="JSON file with arguments (keys mirror CLI flags)")

    args = parser.parse_args()

    # ---------- Load from args-file if provided ----------
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8") as af:
            af_data = json.load(af)
        if af_data.get("sec1"):
            args.sec1 = af_data["sec1"]
        if af_data.get("sec2"):
            args.sec2 = af_data["sec2"]
        if af_data.get("book1"):
            args.book1 = af_data["book1"]
        if af_data.get("book2"):
            args.book2 = af_data["book2"]
        if af_data.get("db1") and args.db1 == DEFAULT_DB:
            args.db1 = af_data["db1"]
        if af_data.get("db2") and args.db2 == DEFAULT_DB:
            args.db2 = af_data["db2"]
        if af_data.get("recurse"):
            args.recurse = True
        if af_data.get("diff_only"):
            args.diff_only = True
        if af_data.get("format"):
            args.output_format = af_data["format"]
        if af_data.get("tolerance") is not None:
            args.tolerance = float(af_data["tolerance"])
        if af_data.get("output"):
            args.output = af_data["output"]
        if af_data.get("source") and args.source == DEFAULT_SOURCE:
            args.source = af_data["source"]
        if af_data.get("timeout") and args.timeout == 120:
            args.timeout = af_data["timeout"]
        if af_data.get("out_file"):
            args.out_file = af_data["out_file"]
        else:
            args.out_file = None
    else:
        args.out_file = None

    if not args.sec1 or not args.sec2:
        parser.error("--sec1 and --sec2 are required (via CLI or args-file)")

    log_dir = _log_dir()

    _info(f"sec1: {args.sec1}")
    _info(f"sec2: {args.sec2}")
    if args.tolerance is not None:
        _info(f"tolerance: {args.tolerance}")

    # Fetch instreams for both securities
    _info("--- Fetching sec1 ---")
    fields1, type1, desc1 = fetch_instream(
        sec=args.sec1, db=args.db1, source=args.source,
        book=args.book1, recurse=args.recurse,
        timeout=args.timeout, log_dir=log_dir,
    )
    _info(f"sec1: {len(fields1)} instream field(s)")

    _info("--- Fetching sec2 ---")
    fields2, type2, desc2 = fetch_instream(
        sec=args.sec2, db=args.db2, source=args.source,
        book=args.book2, recurse=args.recurse,
        timeout=args.timeout, log_dir=log_dir,
    )
    _info(f"sec2: {len(fields2)} instream field(s)")

    # Compute diff
    differences, only1, only2, matches = compute_diff(fields1, fields2, args.tolerance)

    _info(f"Diff: {len(differences)} differ, {len(only1)} only sec1, {len(only2)} only sec2, {len(matches)} match")

    # Format output
    if args.output_format == FORMAT_JSON:
        output_text = format_json(args.sec1, args.sec2, differences, only1, only2, matches, args.diff_only)
    else:
        output_text = format_table(
            args.sec1, args.sec2, type1, type2, desc1, desc2,
            differences, only1, only2, matches, args.diff_only,
        )

    # Write to file or stdout
    if args.output:
        out_dir = os.path.join(_REPO_ROOT, "workspace", "tmp")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, os.path.basename(args.output))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(output_text + "\n")
        _info(f"Output written to {out_path}")
    else:
        print()
        print(output_text)

    # Task-mode: also write to out_file if specified via args-file
    if args.out_file:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_file)), exist_ok=True)
        with open(args.out_file, "w", encoding="utf-8") as f:
            f.write(output_text + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
