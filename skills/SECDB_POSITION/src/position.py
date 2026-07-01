"""Source SecDB positions from books/portfolios/groups via secexpr --safe.

Retrieves position data (Children) for a given security and date,
using archive diddle for historical dates.

Pattern (from AHN: Get Position):
    Link( "_LIB EOD Archive Procedure" );
    Target   = "ISELANIM";
    Date     = Today() - 1;
    Database = Trade Database( Group Names( Target )[0] );
    UseDatabase( Database )
        Eval
        {
            If( Date != Today() )
                Check( @Archive::DiddlePositions( Target, Date ) );
            Print( Children( Target ) );
        };

Usage:
    # Current position for a book (default: name)
    python position.py --sec "ISELANIM"

    # Use Description instead of Name (resolves ticker for portfolios)
    python position.py --sec "NYC Eq Vol BZ Singles2" --fields description

    # Both name and description columns
    python position.py --sec "ISELANIM" --fields both

    # Historical position
    python position.py --sec "ISELANIM" --date "14Apr26"

    # Custom source chain
    python position.py --sec "ISELANIM" --source "~nunesa!clean;PS"
"""

FIELDS_NAME = "name"
FIELDS_DESC = "description"
FIELDS_BOTH = "both"
VALID_FIELDS = (FIELDS_NAME, FIELDS_DESC, FIELDS_BOTH)
import atexit
import argparse
import datetime
import io
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

_REPO_ROOT = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_dir() -> str:
    p = os.path.join(_REPO_ROOT, "workspace", "tmp", "secdb_position_logs")
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
    return (
        "@echo off\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        f"call {ENV_CMD} >nul 2>&1\r\n"
        "setlocal DisableDelayedExpansion\r\n"
    )


def _slang_str(s: str) -> str:
    return f'"{slang_escape(s)}"'


# ---------------------------------------------------------------------------
# Slang code generator
# ---------------------------------------------------------------------------

def build_slang(sec: str, date_str: str, fields: str = FIELDS_NAME) -> str:
    """Build Slang that retrieves position (Children) for a security.

    Follows the AHN: Get Position pattern:
      - Link _LIB EOD Archive Procedure
      - Resolve Trade Database via Group Names
      - UseDatabase + Eval scope
      - If historical date, DiddlePositions
      - Print Children

    fields controls what is printed per row:
      - "name":        Name only (raw SecDB name / numeric ID)
      - "description": Description() only (ticker / human-readable)
      - "both":        Name and Description columns

    IMPORTANT: secexpr stdin evaluates line-by-line — each line is an
    independent expression.  Blocks (Eval/If/ForEach) MUST NOT span
    multiple lines.  We emit the UseDatabase+Eval block as a single line.

    IMPORTANT: Print() does NOT emit newlines in secexpr. Use
    Sprintf("...\\n") to get line breaks in stdout.
    """
    sec_lit = _slang_str(sec)

    # Lines 1-4 are independent top-level statements (persist across lines)
    lines = [
        'Link( "_LIB EOD Archive Procedure" );',
        f'Target = {sec_lit};',
    ]

    if date_str:
        lines.append(f'Date = Date( "{slang_escape(date_str)}" );')
    else:
        lines.append('Date = Today();')

    lines.append('Database = Trade Database( Group Names( Target )[ 0 ] );')

    # Build the ForEachComponent print line based on fields choice
    if fields == FIELDS_BOTH:
        row_print = r'      Print( Sprintf( "%s|%s|%s\n", Name, Description( Name ), String( Qty ) ) );'
    elif fields == FIELDS_DESC:
        row_print = r'      Print( Sprintf( "%s|%s\n", Description( Name ), String( Qty ) ) );'
    else:
        row_print = r'      Print( Sprintf( "%s|%s\n", Name, String( Qty ) ) );'

    # The UseDatabase + Eval block MUST be a single line (secexpr stdin constraint)
    # Print() doesn't emit newlines — use Sprintf with \n
    eval_parts = [
        'UseDatabase( Database )',
        '  Eval {',
        '    If( Date != Today() )',
        '      Check( @Archive::DiddlePositions( Target, Date ) );',
        r'    Print( Sprintf( "===POSITION_START===\n" ) );',
        '    Pos = Children( Target );',
        '    ForEachComponent( Name, Qty, Pos )',
        row_print,
        r'    Print( Sprintf( "===POSITION_END===\n" ) );',
        r'    Print( Sprintf( "===SEC_TYPE=%s===\n", Security Type( Target ) ) );',
        '  };',
    ]
    lines.append(' '.join(eval_parts))

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

    slang_path = os.path.join(log_dir, f"{debug_id}__position.slang")
    _write_text(slang_path, slang_code)

    fd, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="pos_run_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(_cmd_preamble())
            f.write(f'secexpr "{db}" --safe --source "{source}" -t < "{slang_path}"\n')

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

def _parse_position(stdout: str, fields: str = FIELDS_NAME) -> list[tuple]:
    """Parse position rows. Returns tuples whose length depends on fields:
      - name:        (name, qty)
      - description: (desc, qty)
      - both:        (name, desc, qty)
    """
    rows = []
    in_section = False
    for line in stdout.splitlines():
        line = line.strip()
        if line == "===POSITION_START===":
            in_section = True
            continue
        if line == "===POSITION_END===":
            break
        if in_section and "|" in line:
            if fields == FIELDS_BOTH:
                parts = line.split("|", 2)
                if len(parts) == 3:
                    rows.append((parts[0], parts[1], parts[2]))
            else:
                parts = line.split("|", 1)
                rows.append((parts[0], parts[1]))
    return rows


def _parse_sec_type(stdout: str) -> str:
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("===SEC_TYPE=") and line.endswith("==="):
            return line[len("===SEC_TYPE="):-3]
    return "Unknown"


def format_position(rows: list[tuple], sec: str, date: str, sec_type: str, fields: str = FIELDS_NAME) -> str:
    if not rows:
        return f"  Security Type: {sec_type}\n  (no positions)\n"

    def _fmt_qty(q: str) -> str:
        try:
            return f"{float(q):>14,.2f}"
        except ValueError:
            return f"{q:>14}"

    header_lines = [
        f"  Position for: {sec}  ({sec_type})",
        f"  Date: {date}",
        f"  Count: {len(rows)}",
        "",
    ]

    if fields == FIELDS_BOTH:
        max_name = max(max(len(r[0]) for r in rows), 8)
        max_desc = max(max(len(r[1]) for r in rows), 11)
        header_lines.append(f"  {'Name':<{max_name}}  {'Description':<{max_desc}}  {'Quantity':>14}")
        header_lines.append(f"  {'-' * max_name}  {'-' * max_desc}  {'-' * 14}")
        for name, desc, qty in rows:
            header_lines.append(f"  {name:<{max_name}}  {desc:<{max_desc}}  {_fmt_qty(qty)}")
    else:
        col_label = "Description" if fields == FIELDS_DESC else "Security"
        max_col = max(max(len(r[0]) for r in rows), len(col_label))
        header_lines.append(f"  {col_label:<{max_col}}  {'Quantity':>14}")
        header_lines.append(f"  {'-' * max_col}  {'-' * 14}")
        for row_val, qty in rows:
            header_lines.append(f"  {row_val:<{max_col}}  {_fmt_qty(qty)}")

    return "\n".join(header_lines) + "\n"


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
        description="Source SecDB positions from books/portfolios/groups.",
    )
    parser.add_argument("--sec", required=True, help="Security name (book, portfolio, or group)")
    parser.add_argument("--date", default=None, help="Date string (e.g. 14Apr26). Default: today")
    parser.add_argument("--fields", default=FIELDS_NAME, choices=VALID_FIELDS,
                        help="Columns to show: name (raw SecDB name), description (ticker), both. Default: name")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"SecDB database. Default: {DEFAULT_DB}")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help=f"Source chain. Default: {DEFAULT_SOURCE}")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds (default: 120)")
    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")

    args = parser.parse_args()
    _setup_out_file(args.out_file)
    log_dir = _log_dir()

    _info(f"Security: {args.sec}")
    _info(f"Date    : {args.date or 'Today'}")
    _info(f"Fields  : {args.fields}")

    slang = build_slang(args.sec, args.date or "", fields=args.fields)

    rc, stdout, stderr = run_slang(
        slang_code=slang,
        db=args.db,
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

    sec_type = _parse_sec_type(stdout)
    position = _parse_position(stdout, fields=args.fields)

    print(format_position(position, args.sec, args.date or "Today", sec_type, fields=args.fields))
    return 0


if __name__ == "__main__":
    sys.exit(main())
