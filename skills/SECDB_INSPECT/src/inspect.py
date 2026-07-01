"""Inspect SecDB security details via @Instream::Values through secexpr --safe.

Retrieves the instream (stored VT) structure for a given security,
optionally recursing into nested securities (swap legs, components).

Uses _LIB Instream Values → @Instream::Values() and strips
non-serializable types before output.

Usage:
    # JSON output (default) for a trade
    python inspect.py --sec "EFA EUR 16Apr26 66JNJV 0"

    # Flat key=value output
    python inspect.py --sec "EFA EUR 16Apr26 66JNJV 0" --format flat

    # Recursive (follows swap legs, components)
    python inspect.py --sec "SWP EUR 24Jun26 H46WXH 0" --recurse

    # Custom database
    python inspect.py --sec "70359140" --db "!NYC_Equity_Prod"
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# Bootstrap: import slang_escape from SLANG_EDIT skill
# ---------------------------------------------------------------------------
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SLANG_EDIT_SRC = os.path.join(SKILL_DIR, "..", "..", "SLANG_EDIT", "src")
sys.path.insert(0, SLANG_EDIT_SRC)
from edit import slang_escape  # noqa: E402
sys.path.insert(0, os.path.join(SKILL_DIR, "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402

ENV_CMD = r"H:\all-languages-env.cmd"
DEFAULT_DB = "!NYC_Production"
DEFAULT_SOURCE = "PS"
FORMAT_JSON = "json"
FORMAT_FLAT = "flat"
VALID_FORMATS = (FORMAT_JSON, FORMAT_FLAT)

_REPO_ROOT = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_dir() -> str:
    p = os.path.join(_REPO_ROOT, "workspace", "tmp", "secdb_inspect_logs")
    os.makedirs(p, exist_ok=True)
    return p


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _info(msg: str) -> None:
    print(f"[{_ts()}] {msg}")


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)


def _cmd_preamble() -> str:
    # After calling the env script, resolve secexpr to its full path and
    # trim PATH to a minimal set.  secexpr.cmd internally builds a ~6K PATH;
    # if the pre-existing PATH from all-languages-env.cmd (~2K) is appended,
    # the total exceeds cmd.exe's 8191-char line limit → "The input line is
    # too long" (exit code 255).
    return (
        "@echo off\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        f"call {ENV_CMD} >nul 2>&1\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        'for /f "delims=" %%i in (\'where secexpr\') do set "SECEXPR_CMD=%%i"\r\n'
        'set "PATH=%SystemRoot%\\system32;%SystemRoot%"\r\n'
    )


def _slang_str(s: str) -> str:
    return f'"{slang_escape(s)}"'


# ---------------------------------------------------------------------------
# Slang code generator
# ---------------------------------------------------------------------------

def build_db_resolve_slang(book: str) -> str:
    """Build Slang that resolves a book name to its trade database string.

    Prints the DB string to stdout as ===TRADE_DB=<db>===.
    """
    book_lit = _slang_str(book)
    return (
        f'TDB = Trade Database( Group Names( {book_lit} )[ 0 ] );\n'
        r'Print( Sprintf( "===TRADE_DB=%s===\n", TDB ) );'
        "\n"
    )


def build_slang(sec: str, recurse: bool) -> str:
    """Build Slang that calls DiskInstreamValues (or @Instream::Values
    for recurse mode) and prints metadata markers.

    The actual instream data is captured from secexpr -t stderr trace,
    where DiskInstreamValues outputs each stored VT as a formatted
    'Key : Value' line.  This avoids Slang serialization issues
    (Jsonify crashes, ForEach(K,V,S) unsupported, .(K) parser error,
    String(Structure) returns empty).

    DiskInstreamValues MUST run at top level (not inside Eval/Try) for
    trace output to appear.  Book-based DB resolution is handled by a
    separate first-phase call that resolves the DB name, which is then
    passed as secexpr --db argument.

    IMPORTANT: secexpr stdin evaluates line-by-line.
    IMPORTANT: Print() needs Sprintf("...\\n") for newlines.
    """
    sec_lit = _slang_str(sec)
    lines = []

    if recurse:
        lines.append('Link( "_LIB Instream Values" );')
        iv_call = f'@Instream::Values( {sec_lit}, Recurse := True )'
    else:
        iv_call = f'DiskInstreamValues( {sec_lit} )'

    # Top-level statements — trace output only appears at top level
    lines.append(f'IV = {iv_call};')
    lines.append(
        r'Print( Sprintf( "===SEC_TYPE=%s===\n", Try( Security Type( '
        + sec_lit + r' ) ) : "Unknown" ) );'
    )
    lines.append(
        r'Print( Sprintf( "===SEC_DESC=%s===\n", Try( Description( '
        + sec_lit + r' ) ) : "Unknown" ) );'
    )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------

def run_slang(
    slang_code: str,
    db: str,
    source: str,
    log_dir: str,
    timeout: int = 120,
) -> tuple[int, str, str]:
    """Execute Slang code via secexpr --safe. Returns (rc, stdout, stderr)."""
    debug_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    slang_path = os.path.join(log_dir, f"{debug_id}__inspect.slang")
    _write_text(slang_path, slang_code)

    fd, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="insp_run_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(_cmd_preamble())
            f.write(f'"%SECEXPR_CMD%" "{db}" --safe --source "{source}" -t < "{slang_path}"\n')

        _info(f"slang  : {slang_path} ({os.path.getsize(slang_path)} B)")
        _info(f"db     : {db}")
        _info(f"source : {source}")
        _info(f"timeout: {timeout}s")

        t0 = time.time()
        try:
            proc = run_cmd(
                ["cmd", "/c", batch_path],
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.time() - t0
            stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
            stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
            _write_text(os.path.join(log_dir, f"{debug_id}__stdout.txt"), stdout)
            _write_text(os.path.join(log_dir, f"{debug_id}__stderr.txt"), stderr)
            _info(f"TIMED OUT after {elapsed:.0f}s")
            return -1, stdout, stderr

        elapsed = time.time() - t0
        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")

        _write_text(os.path.join(log_dir, f"{debug_id}__stdout.txt"), stdout)
        _write_text(os.path.join(log_dir, f"{debug_id}__stderr.txt"), stderr)

        _info(f"elapsed: {elapsed:.1f}s | rc: {proc.returncode}")
        _info(f"stdout : {len(stdout)} B  ->  {log_dir}/{debug_id}__stdout.txt")
        _info(f"stderr : {len(stderr)} B  ->  {log_dir}/{debug_id}__stderr.txt")
        return proc.returncode, stdout, stderr
    finally:
        try:
            os.unlink(batch_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------

def _extract_between(stdout: str, start_marker: str, end_marker: str) -> str:
    """Extract text between two markers in stdout."""
    lines = stdout.splitlines()
    collecting = False
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped == start_marker:
            collecting = True
            continue
        if stripped == end_marker:
            break
        if collecting:
            result.append(line)
    return "\n".join(result)


def _parse_kv_from_trace(stderr: str) -> list[tuple[str, str]]:
    """Parse DiskInstreamValues trace output from secexpr -t stderr.

    The trace format is:
        Key Name                   : Value
    Lines are padded and aligned with ': ' as delimiter.
    We ignore ERROR lines and Evaluating/Evaluated markers.
    """
    import re

    pairs = []
    # Match lines with the pattern: non-ERROR text, then   : value
    # The key-value lines have multiple spaces before the colon
    kv_re = re.compile(r'^([A-Za-z][A-Za-z0-9 ~_.*/-]*?)\s{2,}: ?(.*)$')

    for line in stderr.splitlines():
        stripped = line.strip()
        # Skip error lines, eval markers, and empty lines
        if not stripped:
            continue
        if stripped.startswith("ERROR:"):
            continue
        if stripped.startswith("Evaluating"):
            continue
        if stripped.startswith("Evaluated"):
            continue
        if stripped.startswith("Slang Expression"):
            continue

        m = kv_re.match(stripped)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()
            pairs.append((key, val))

    return pairs


def _parse_meta(stdout: str, prefix: str, suffix: str = "===") -> str:
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith(prefix) and line.endswith(suffix):
            return line[len(prefix):-len(suffix)]
    return "Unknown"


def format_json_output(stderr: str, sec: str, sec_type: str, sec_desc: str) -> str:
    """Build JSON from stderr trace KV lines."""
    pairs = _parse_kv_from_trace(stderr)
    if not pairs:
        return f"  Security: {sec} ({sec_type})\n  Description: {sec_desc}\n  (no instream data)\n"

    header = (
        f"  Security: {sec}\n"
        f"  Type: {sec_type}\n"
        f"  Description: {sec_desc}\n"
        f"  ---\n"
    )

    data = {}
    for k, v in pairs:
        if not v:
            data[k] = None
            continue
        try:
            data[k] = float(v) if "." in v else int(v)
        except ValueError:
            data[k] = v

    return header + json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def format_flat_output(stderr: str, sec: str, sec_type: str, sec_desc: str) -> str:
    """Build aligned key=value from stderr trace KV lines."""
    pairs = _parse_kv_from_trace(stderr)
    if not pairs:
        return f"  Security: {sec} ({sec_type})\n  Description: {sec_desc}\n  (no instream data)\n"

    header = (
        f"  Security: {sec}\n"
        f"  Type: {sec_type}\n"
        f"  Description: {sec_desc}\n"
        f"  ---\n"
    )

    max_key = max(len(p[0]) for p in pairs)
    aligned = "\n".join(f"  {k:<{max_key}}  = {v}" for k, v in pairs)
    return header + aligned + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect SecDB security details via @Instream::Values.",
    )
    parser.add_argument("--sec", required=False, default=None, help="Security name or object ID")
    parser.add_argument("--recurse", action="store_true", default=False,
                        help="Recurse into nested securities (swap legs, components)")
    parser.add_argument("--format", default=FORMAT_JSON, choices=VALID_FORMATS,
                        dest="output_format",
                        help=f"Output format: json (pretty-printed) or flat (key=value). Default: {FORMAT_JSON}")
    parser.add_argument("--book", default=None,
                        help="Book/portfolio name to resolve trade database (for securities not in default DB)")
    parser.add_argument("--db", default=DEFAULT_DB,
                        help=f"SecDB database for secexpr. Default: {DEFAULT_DB}")
    parser.add_argument("--source", default=DEFAULT_SOURCE,
                        help=f"Source chain. Default: {DEFAULT_SOURCE}")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Timeout in seconds (default: 120)")
    parser.add_argument("--args-file", default=None, metavar="PATH",
                        help="JSON file with arguments (keys mirror CLI flags)")

    args = parser.parse_args()

    # ---------- Load from args-file if provided ----------
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8") as af:
            af_data = json.load(af)
        if af_data.get("sec") and args.sec == parser.get_default("sec"):
            args.sec = af_data["sec"]
        if af_data.get("format"):
            args.output_format = af_data["format"]
        if af_data.get("book"):
            args.book = af_data["book"]
        if af_data.get("db") and args.db == DEFAULT_DB:
            args.db = af_data["db"]
        if af_data.get("source") and args.source == DEFAULT_SOURCE:
            args.source = af_data["source"]
        if af_data.get("timeout") and args.timeout == 120:
            args.timeout = af_data["timeout"]
        if af_data.get("recurse"):
            args.recurse = True
        if af_data.get("out_file"):
            args.out_file = af_data["out_file"]
        else:
            args.out_file = None
    else:
        args.out_file = None

    if not args.sec:
        parser.error("--sec is required (via CLI or args-file)")

    log_dir = _log_dir()

    _info(f"Security: {args.sec}")
    _info(f"Recurse : {args.recurse}")
    _info(f"Format  : {args.output_format}")
    if args.book:
        _info(f"Book    : {args.book}")

    db = args.db

    # Phase 1: resolve trade database from book name if --book given
    if args.book:
        db_slang = build_db_resolve_slang(args.book)
        rc, stdout, stderr = run_slang(
            slang_code=db_slang,
            db=args.db,
            source=args.source,
            log_dir=log_dir,
            timeout=args.timeout,
        )
        if rc == -1:
            print("\nERROR: secexpr timed out resolving trade DB.", file=sys.stderr)
            return 1
        resolved_db = _parse_meta(stdout, "===TRADE_DB=")
        if resolved_db == "Unknown" or not resolved_db:
            print(f"\nERROR: Could not resolve trade DB for book '{args.book}'.", file=sys.stderr)
            return 1
        _info(f"Resolved trade DB: {resolved_db}")
        db = resolved_db

    # Phase 2: run DiskInstreamValues at top level with resolved DB
    slang = build_slang(args.sec, args.recurse)

    rc, stdout, stderr = run_slang(
        slang_code=slang,
        db=db,
        source=args.source,
        log_dir=log_dir,
        timeout=args.timeout,
    )

    if rc == -1:
        print("\nERROR: secexpr timed out.", file=sys.stderr)
        return 1

    if rc != 0 and not stdout.strip():
        print(f"\nERROR: secexpr rc={rc}. Logs: {log_dir}", file=sys.stderr)
        for line in (stderr or "").strip().splitlines()[:20]:
            print(f"  stderr: {line}", file=sys.stderr)
        return 1

    sec_type = _parse_meta(stdout, "===SEC_TYPE=")
    sec_desc = _parse_meta(stdout, "===SEC_DESC=")

    if args.output_format == FORMAT_JSON:
        output_text = format_json_output(stderr, args.sec, sec_type, sec_desc)
    else:
        output_text = format_flat_output(stderr, args.sec, sec_type, sec_desc)

    print(output_text)

    if args.out_file:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_file)), exist_ok=True)
        with open(args.out_file, "w", encoding="utf-8") as f:
            f.write(output_text + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
