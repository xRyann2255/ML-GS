"""Query SecDB transaction logs for a security via secexpr --safe.

Retrieves the change history (transaction log) for any SecDB security,
equivalent to the programmatic side of _UT Point Finger of Blame (PFOB).

Two modes:
  --mode list  (default) — uses Trans::List Transactions to list transaction headers
  --mode diffs           — uses PFOB::Get Transactions and Diffs to show changes

Usage:
    python translog.py --sec "MySecurityName"
    python translog.py --sec "MySecurityName" --db "!NYC_Equity_Prod"
    python translog.py --sec "MyTradeName" --book "ISELANIM"
    python translog.py --sec "MySecurityName" --max-trans 50 --format json
    python translog.py --sec "MySecurityName" --back-to "01Jan26"
    python translog.py --sec "MySecurityName" --mode diffs --cutoff "01Jan26"
"""
import argparse
import atexit
import datetime
import io
import json
import os
import re
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
DEFAULT_MAX_TRANS = 40
FORMAT_TABLE = "table"
FORMAT_JSON = "json"
MODE_LIST = "list"
MODE_DIFFS = "diffs"

_REPO_ROOT = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))

START_MARKER = "===TRANSLOG_START==="
END_MARKER = "===TRANSLOG_END==="
FIELD_SEP = "===FIELD==="
RECORD_SEP = "===TRANS_RECORD==="


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_dir() -> str:
    p = os.path.join(_REPO_ROOT, "workspace", "tmp", "secdb_translog_logs")
    os.makedirs(p, exist_ok=True)
    return p


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _info(msg: str) -> None:
    print(f"[{_ts()}] {msg}", file=sys.stderr)


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)


def _cmd_preamble() -> str:
    return (
        "@echo off\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        f"call {ENV_CMD} >nul 2>&1\r\n"
        "setlocal DisableDelayedExpansion\r\n"
    )


def _slang_str(s: str) -> str:
    return f'"{slang_escape(s)}"'


# ---------------------------------------------------------------------------
# Slang code generators
# ---------------------------------------------------------------------------

def build_db_resolve_slang(book: str) -> str:
    """Build Slang that resolves a book name to its trade database string."""
    book_lit = _slang_str(book)
    return (
        f"TDB = Trade Database( Group Names( {book_lit} )[ 0 ] );\n"
        f'Print( Sprintf( "===TRADE_DB=%s===\\n", TDB ) );\n'
    )


def build_resolve_inf_translog_slang() -> str:
    """Build Slang that resolves the InfiniteTransLogDb for the current database."""
    return (
        'InfDb = InfiniteTransLogDb( Database() );\n'
        'Print( Sprintf( "===INF_TRANSLOG_DB=%s===\\n", InfDb ) );\n'
    )


def build_translog_slang(
    sec: str,
    max_trans: int = DEFAULT_MAX_TRANS,
    back_to: str | None = None,
) -> str:
    """Build Slang that calls Trans::List Transactions and dumps all fields.

    TransLogHeader is a C++ internal type where ComponentNames() returns
    empty. Instead we print String(T) for each record which produces a
    well-formatted key: value text block, then parse on the Python side.
    """
    sec_lit = _slang_str(sec)
    lines = []

    lines.append('Link( "_LIB Transaction Fns" );')

    # Build call with optional BackTo time
    call_parts = [f"Trans = @Trans::List Transactions( {sec_lit}"]
    call_parts.append(f", Maximum Number of Transactions := {max_trans}")
    call_parts.append(", Show Progress := False")
    if back_to:
        call_parts.append(f', BackTo := DateParse( {_slang_str(back_to)} )')
    call_parts.append(" );")
    lines.append("".join(call_parts))

    # Metadata
    lines.append(f'Print( Sprintf( "===SEC_NAME=%s===\\n", {sec_lit} ) );')
    lines.append('Print( Sprintf( "===TRANS_COUNT=%d===\\n", Size( Trans ) ) );')

    # Start marker
    lines.append(f'Print( "{START_MARKER}\\n" );')

    # Iterate: print String(T) for each header (TransLogHeader is a C++
    # internal type; ComponentNames returns empty but String() works)
    lines.append("ForEach( T, Trans )")
    lines.append("{")
    lines.append(f'    Print( "{RECORD_SEP}\\n" );')
    lines.append('    Print( String( T ) );')
    lines.append('    Print( "\\n" );')
    lines.append("};")

    # End marker
    lines.append(f'Print( "{END_MARKER}\\n" );')

    return "\n".join(lines) + "\n"


def build_diffs_slang(
    sec: str,
    db_name: str,
    cutoff: str | None = None,
    use_var_to_slang: bool = False,
    use_diff_lossless: bool = False,
) -> str:
    """Build Slang that calls PFOB::Get Transactions and Diffs.

    This outputs formatted text with transaction headers and diffs
    directly to stdout (PFOB's native output format).
    """
    sec_lit = _slang_str(sec)
    db_lit = _slang_str(db_name)
    lines = []

    lines.append('Link( "_LIB Point Finger Of Blame" );')

    # Cutoff: use provided time or omit (let PFOB use its default)
    if cutoff:
        cutoff_expr = f'DateParse( {_slang_str(cutoff)} )'
    else:
        cutoff_expr = 'Time( Today() - 365 )'

    call = (
        f"@PFOB::Get Transactions and Diffs( {sec_lit}, {db_lit}, {cutoff_expr}"
    )
    if use_var_to_slang:
        call += ", Use Var to Slang := True"
    if use_diff_lossless:
        call += ", Use DiffLossless := True"
    call += " );"

    lines.append(call)

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
    label: str = "translog",
) -> tuple[int, str, str]:
    """Execute Slang code via secexpr --safe. Returns (rc, stdout, stderr)."""
    debug_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    slang_path = os.path.join(log_dir, f"{debug_id}__{label}.slang")
    _write_text(slang_path, slang_code)

    fd, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="tlog_run_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(_cmd_preamble())
            f.write(
                f'secexpr "{db}" --safe --source "{source}" -t '
                f'< "{slang_path}"\n'
            )

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
            _write_text(
                os.path.join(log_dir, f"{debug_id}__stdout.txt"), stdout
            )
            _write_text(
                os.path.join(log_dir, f"{debug_id}__stderr.txt"), stderr
            )
            _info(f"TIMED OUT after {elapsed:.0f}s")
            return -1, stdout, stderr

        elapsed = time.time() - t0
        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")

        _write_text(
            os.path.join(log_dir, f"{debug_id}__stdout.txt"), stdout
        )
        _write_text(
            os.path.join(log_dir, f"{debug_id}__stderr.txt"), stderr
        )

        _info(f"elapsed: {elapsed:.1f}s | rc: {proc.returncode}")
        _info(f"stdout : {len(stdout)} B")
        _info(f"stderr : {len(stderr)} B")
        return proc.returncode, stdout, stderr
    finally:
        try:
            os.unlink(batch_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

def parse_transactions(stdout: str) -> list[dict]:
    """Parse transaction records from secexpr stdout.

    Each record is delimited by RECORD_SEP. Records are String()
    representations of TransLogHeader C++ structures with "Key : value"
    lines. Sub-structures (indented deeper) are flattened with dotted keys.
    """
    records = []

    start = stdout.find(START_MARKER)
    end = stdout.find(END_MARKER)
    if start < 0 or end < 0:
        return records

    body = stdout[start + len(START_MARKER):end]
    raw_records = body.split(RECORD_SEP)

    for raw in raw_records:
        raw = raw.strip()
        if not raw:
            continue

        record = {}
        for line in raw.splitlines():
            # TransLogHeader String() format: "Key Name        : value"
            # Sub-fields are indented with 4 spaces: "    SubKey  : value"
            # Skip deeply nested or empty lines
            if ": " not in line:
                continue

            key_part, _, val_part = line.partition(": ")
            key = key_part.strip()
            value = val_part.strip()

            if not key:
                continue

            record[key] = value

        if record:
            records.append(record)

    return records


def parse_metadata(stdout: str) -> dict:
    """Extract metadata markers from stdout."""
    meta = {}
    for pattern, key in [
        (r"===SEC_NAME=(.+?)===", "security"),
        (r"===TRANS_COUNT=(\d+)===", "count"),
        (r"===TRADE_DB=(.+?)===", "trade_db"),
        (r"===INF_TRANSLOG_DB=(.+?)===", "inf_translog_db"),
    ]:
        m = re.search(pattern, stdout)
        if m:
            meta[key] = m.group(1)
    return meta


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

# Preferred column order for table display (others appended alphabetically)
_PREFERRED_ORDER = [
    "Trans ID", "GM Time", "Login Name", "User Name",
    "SecName", "Database", "Application Name",
    "Source Trans Id", "DbId",
]


def _ordered_columns(records: list[dict]) -> list[str]:
    """Return column names in preferred display order."""
    all_keys = set()
    for r in records:
        all_keys.update(r.keys())

    ordered = [k for k in _PREFERRED_ORDER if k in all_keys]
    remaining = sorted(all_keys - set(ordered))
    return ordered + remaining


def format_table(records: list[dict]) -> str:
    """Format transaction records as aligned table."""
    if not records:
        return "(no transactions found)"

    cols = _ordered_columns(records)

    widths = {}
    for col in cols:
        widths[col] = max(
            len(col),
            max((len(str(r.get(col, ""))) for r in records), default=0),
        )

    header = "  ".join(col.ljust(widths[col]) for col in cols)
    sep = "  ".join("-" * widths[col] for col in cols)
    lines = [header, sep]

    for r in records:
        row = "  ".join(
            str(r.get(col, "")).ljust(widths[col]) for col in cols
        )
        lines.append(row)

    return "\n".join(lines)


def format_json_output(records: list[dict]) -> str:
    """Format transaction records as JSON."""
    return json.dumps(records, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _apply_args_file(positional_keys=None):
    """If --args-file in argv, load JSON and rebuild argv as CLI flags."""
    if "--args-file" not in sys.argv:
        return
    idx = sys.argv.index("--args-file")
    path = sys.argv[idx + 1]
    with open(path, "r", encoding="utf-8") as f:
        af = json.load(f)
    argv = [sys.argv[0]]
    for pk in (positional_keys or []):
        if pk in af:
            v = af.pop(pk)
            if isinstance(v, list):
                argv.extend(str(x) for x in v)
            elif v is not None:
                argv.append(str(v))
    for k, v in af.items():
        if k == "args_file":
            continue
        flag = f"--{k.replace('_', '-')}"
        if isinstance(v, bool):
            if v:
                argv.append(flag)
        elif isinstance(v, list):
            for item in v:
                argv.extend([flag, str(item)])
        elif v is not None:
            argv.extend([flag, str(v)])
    sys.argv = argv


def _setup_out_file(out_path):
    """If out_path is set, tee stdout to a file (flushed on exit)."""
    if not out_path:
        return
    buf = io.StringIO()
    real = sys.stdout
    class _Tee:
        def write(self, s): real.write(s); buf.write(s)
        def flush(self): real.flush()
    sys.stdout = _Tee()
    def _flush():
        sys.stdout = real
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(buf.getvalue())
    atexit.register(_flush)


def main() -> int:
    _apply_args_file()
    parser = argparse.ArgumentParser(
        description="Query SecDB transaction log for a security"
    )
    parser.add_argument(
        "--sec", required=True, help="Security name to query"
    )
    parser.add_argument(
        "--db", default=DEFAULT_DB,
        help=f"SecDB database (default: {DEFAULT_DB})"
    )
    parser.add_argument(
        "--source", default=DEFAULT_SOURCE,
        help=f"SecDB source chain (default: {DEFAULT_SOURCE})"
    )
    parser.add_argument(
        "--book", default=None,
        help="Book name to resolve trade database"
    )
    parser.add_argument(
        "--max-trans", type=int, default=DEFAULT_MAX_TRANS,
        help=f"Max transactions to return (default: {DEFAULT_MAX_TRANS})"
    )
    parser.add_argument(
        "--back-to", default=None,
        help='Oldest transaction time, Slang date format (e.g. "01Jan26")'
    )
    parser.add_argument(
        "--mode", choices=[MODE_LIST, MODE_DIFFS], default=MODE_LIST,
        help="list = transaction headers (default), diffs = headers + value changes"
    )
    parser.add_argument(
        "--cutoff", default=None,
        help='Cutoff time for diffs mode, Slang date format (e.g. "01Jan26 18:00:00")'
    )
    parser.add_argument(
        "--var-to-slang", action="store_true",
        help="(diffs mode) Show diffs as Slang variable assignments"
    )
    parser.add_argument(
        "--diff-lossless", action="store_true",
        help="(diffs mode) Use lossless diff format"
    )
    parser.add_argument(
        "--infinite-translog", action="store_true",
        help="Use InfiniteTransLogDb for full history (required for some securities like BRL)"
    )
    parser.add_argument(
        "--format", choices=[FORMAT_TABLE, FORMAT_JSON],
        default=FORMAT_TABLE,
        help="Output format for list mode (default: table)"
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="secexpr timeout in seconds (default: 120)"
    )
    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")
    args = parser.parse_args()
    _setup_out_file(args.out_file)

    log_dir = _log_dir()
    db = args.db
    source = args.source

    # Phase 1: resolve trade DB from book if specified
    if args.book:
        _info(f"Resolving trade database for book '{args.book}' ...")
        slang = build_db_resolve_slang(args.book)
        rc, stdout, stderr = run_slang(
            slang, db, source, log_dir, args.timeout, label="db_resolve"
        )
        if rc != 0:
            print(
                f"ERROR: Failed to resolve trade database (rc={rc})",
                file=sys.stderr,
            )
            if stderr:
                for line in stderr.splitlines()[-5:]:
                    print(f"  {line}", file=sys.stderr)
            return 1

        meta = parse_metadata(stdout)
        if "trade_db" not in meta:
            print(
                "ERROR: Could not resolve trade database from book",
                file=sys.stderr,
            )
            return 1

        db = meta["trade_db"]
        _info(f"Resolved trade database: {db}")

    # Phase 1b: resolve InfiniteTransLogDb
    # Always try unless the DB is already a _Log DB or user's default.
    # The InfiniteTransLogDb holds the full transaction log headers that
    # the regular DB often can't deserialize.
    original_db = db
    if args.infinite_translog or db != DEFAULT_DB:
        _info(f"Resolving InfiniteTransLogDb for '{db}' ...")
        slang = build_resolve_inf_translog_slang()
        rc, stdout, stderr = run_slang(
            slang, db, source, log_dir, args.timeout, label="inf_resolve"
        )
        meta = parse_metadata(stdout)
        if "inf_translog_db" in meta:
            inf_db = meta["inf_translog_db"]
            if inf_db != db:
                db = inf_db
                _info(f"Using InfiniteTransLogDb: {db}")
            else:
                _info(f"InfiniteTransLogDb is same as db: {db}")
        else:
            _info("WARNING: Could not resolve InfiniteTransLogDb, using original db")

    # Phase 2: run the appropriate mode
    if args.mode == MODE_DIFFS:
        return _run_diffs(args, db, source, log_dir, original_db)
    else:
        return _run_list(args, db, source, log_dir)


def _run_list(args, db: str, source: str, log_dir: str) -> int:
    """List mode: Trans::List Transactions headers."""
    _info(f"Querying transaction log for '{args.sec}' ...")
    slang = build_translog_slang(args.sec, args.max_trans, args.back_to)
    rc, stdout, stderr = run_slang(
        slang, db, source, log_dir, args.timeout, label="list"
    )

    if rc == -1:
        print("ERROR: secexpr timed out", file=sys.stderr)
        return 1

    meta = parse_metadata(stdout)
    records = parse_transactions(stdout)

    if not records:
        # Check for genuine security-not-found errors (not Type bootstrap noise)
        sec_not_found = any(
            f'GetByName( "{args.sec}"' in l or
            f'SecSrvGetByName( "{args.sec}"' in l
            for l in stderr.splitlines()
        )
        deser_failed = "TransLogHeaderMsgDispatcher::deserialize" in stderr

        if sec_not_found:
            print(
                f"ERROR: Security '{args.sec}' not found in database '{db}'",
                file=sys.stderr,
            )
        elif deser_failed:
            print(
                f"ERROR: Transaction log headers could not be read. "
                f"Try --infinite-translog (the _Log DB may be needed).",
                file=sys.stderr,
            )
        else:
            print(
                f"No transactions found for '{args.sec}' in '{db}'",
                file=sys.stderr,
            )
            err_lines = [
                l for l in stderr.splitlines()
                if "ERROR" in l
                and "SecSrvIndex" not in l
                and "does not exist" not in l
            ]
            for line in err_lines[-5:]:
                print(f"  {line.strip()}", file=sys.stderr)
        return 1

    count = meta.get("count", str(len(records)))
    _info(f"Found {count} transaction(s)")

    if args.format == FORMAT_JSON:
        print(format_json_output(records))
    else:
        print(format_table(records))

    return 0


def _run_diffs(args, db: str, source: str, log_dir: str, original_db: str | None = None) -> int:
    """Diffs mode: PFOB::Get Transactions and Diffs output."""
    _info(f"Querying transaction diffs for '{args.sec}' ...")

    # PFOB expects the trade database name (not the _Log DB)
    pfob_db = original_db or db
    slang = build_diffs_slang(
        args.sec,
        db_name=pfob_db,
        cutoff=args.cutoff,
        use_var_to_slang=args.var_to_slang,
        use_diff_lossless=args.diff_lossless,
    )
    rc, stdout, stderr = run_slang(
        slang, db, source, log_dir, args.timeout, label="diffs"
    )

    if rc == -1:
        print("ERROR: secexpr timed out", file=sys.stderr)
        return 1

    # PFOB::Get Transactions and Diffs prints directly to stdout
    output = stdout.strip()
    if not output:
        # Check for genuine security-not-found errors
        sec_not_found = any(
            f'GetByName( "{args.sec}"' in l or
            f'SecSrvGetByName( "{args.sec}"' in l
            for l in stderr.splitlines()
        )
        if sec_not_found:
            print(
                f"ERROR: Security '{args.sec}' not found in database '{db}'",
                file=sys.stderr,
            )
        else:
            print(
                f"No transactions/diffs found for '{args.sec}' in '{db}'",
                file=sys.stderr,
            )
            err_lines = [
                l for l in stderr.splitlines()
                if "ERROR" in l
                and "SecSrvIndex" not in l
                and "UFO" not in l
                and "does not exist" not in l
            ]
            for line in err_lines[-5:]:
                print(f"  {line.strip()}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
