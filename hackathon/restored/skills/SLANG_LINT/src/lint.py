"""Run native Slang lint on one or more scripts via secexpr --safe.

Supports two lint backends:
  1. @LIBSlang::Lint       — fast, covers type issues, collisions, unused vars
  2. @ScriptVal::PreCommit Check Lint — full precommit pipeline (unused links,
     deeper cross-library checks); slower but matches ScriptReview's lint

Usage examples:

  # Quick lint (default: @LIBSlang::Lint)
  python lint.py --db "~{kerberos}!clean" --scripts "_LIB EQ DA Bulk Update"

  # Lint multiple scripts
  python lint.py --db "~{kerberos}!clean" --scripts "_LIB Foo" "Test: Foo"

  # Precommit lint (ScriptVal pipeline)
  python lint.py --db "~{kerberos}!clean" --scripts "Test: Foo" --precommit

  # Custom source chain
  python lint.py --db "~{kerberos}!clean" --scripts "_LIB Foo" --source "!NYC_EqVol_Source;PS"
"""
import argparse
import concurrent.futures
import datetime
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
DEFAULT_SOURCE = "PS"

_REPO_ROOT = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _expand_db(db: str) -> str:
    m = re.match(r"^~(\w+)(!.*)?$", db)
    if m:
        return f"!NYC UserDBs!home!{m.group(1)}{m.group(2) or ''}"
    return db


def _log_dir() -> str:
    p = os.path.join(_REPO_ROOT, "workspace", "tmp", "slang_lint_logs")
    os.makedirs(p, exist_ok=True)
    return p


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _phase(label: str) -> None:
    print(f"\n[{_ts()}] ===== {label} =====")


def _info(msg: str) -> None:
    print(f"[{_ts()}]   {msg}")


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _cmd_preamble() -> str:
    # After calling the env script, resolve secexpr to its full path and
    # trim PATH to a minimal set.  secexpr.cmd internally builds a ~6K
    # PATH; if the pre-existing PATH from all-languages-env.cmd (~2K) is
    # appended, the total exceeds cmd.exe's 8191-char line limit.
    return (
        "@echo off\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        f"call {ENV_CMD} >nul 2>&1\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        'for /f "delims=" %%i in (\'where secexpr\') do set "SECEXPR_CMD=%%i"\r\n'
        'set "PATH=%SystemRoot%\\system32;%SystemRoot%"\r\n'
    )


def _slang_str(name: str) -> str:
    """Build a Slang string literal, using Chr(58) for colons."""
    if ":" in name:
        head, tail = name.split(":", 1)
        return f'Sprint( "{slang_escape(head)}", Chr( 58 ), "{slang_escape(tail)}" )'
    return f'"{slang_escape(name)}"'


def _add_newlines_to_prints(slang: str) -> str:
    """Prefix Print() calls with Chr(10) so markers land on separate lines."""
    slang = re.sub(r'Print\( Sprint\( ', 'Print( Sprint( Chr( 10 ), ', slang)
    slang = re.sub(r'Print\( ("[^"]*") \)', r'Print( Sprint( Chr( 10 ), \1 ) )', slang)
    return slang


# ---------------------------------------------------------------------------
# Slang code generators
# ---------------------------------------------------------------------------

def build_lint_slang(script_names: list[str]) -> str:
    """Build Slang for @LIBSlang::Lint on each script (by name, resolved from DB)."""
    lines = [
        'Link( "_LIB Slang Lint Fns" );',
        'Print( "PHASE=libs_linked" );',
    ]

    for name in script_names:
        name_expr = _slang_str(name)
        lines.append(
            f'Print( Sprint( "SCRIPT_START=", {name_expr} ) ); '
            f'Try( Ex ) {{ '
            f'Result = @LIBSlang::Lint( {name_expr}, '
            f'Cache Results := False, Use Cached Results := False, '
            f'Filter OK Status := True ); '
            f'Print( Sprint( "ISSUE_COUNT=", Size( Result ) ) ); '
            f'ForEach( Err, Result ) {{ '
            f'S = Sprintf( "%g", Err.Status ); '
            f'T = ""; '
            f'Try( X1 ) {{ T = Err.Text; }} : {{}}; '
            f'Print( Sprint( "ISSUE=", S, "|", T ) ); '
            f'}}; '
            f'Print( "SCRIPT_END=OK" ); '
            f'}} : {{ Print( Sprint( "SCRIPT_END=ERROR ", String( Ex ) ) ); }};'
        )

    slang = "\n".join(lines) + "\n"
    return _add_newlines_to_prints(slang)


def build_precommit_lint_slang(script_names: list[str]) -> str:
    """Build Slang for @ScriptVal::PreCommit Check Lint (full precommit pipeline)."""
    array_items = ", ".join(_slang_str(n) for n in script_names)
    lines = [
        'Link( "_LIB Script Validation Fns" );',
        'Link( "_LIB Security Fns" );',
        'Link( "_Const Slang Lint" );',
        'Print( "PHASE=libs_linked" );',
        (
            f'Try( TopEx ) {{ '
            f'All Scripts = [ {array_items} ]; '
            f'Arr = @SecFns::Get Many Securities( All Scripts ); '
            f'Ptrs = Security List( Arr ); '
            f'Print( Sprint( "STEP=resolved count=", Size( Ptrs ) ) ); '
            f'R = @ScriptVal::PreCommit Check Lint( Ptrs, '
            f'Commit Verb := "submit", '
            f'Worst Lint State To Record := LINT::INFORMATIONAL, '
            f'Scripts With Uncommitted Edits := Structure(), '
            f'Scripts Being Deleted := Structure(), '
            f'Suppress Lint SourceDb Check := True ); '
            f'Print( Sprint( "PRECOMMIT_RESULT=", String( R."Lint Results" ) ) ); '
            f'}} : {{ Print( Sprint( "FATAL_EXCEPTION=", String( TopEx ) ) ); }};'
        ),
    ]
    slang = "\n".join(lines) + "\n"
    return _add_newlines_to_prints(slang)


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------

def run_slang(
    db: str,
    slang_path: str,
    source: str,
    log_dir: str,
    debug_id: str,
    timeout: int = 300,
) -> tuple[int, str, str]:
    """Pipe a Slang file to secexpr --safe via stdin. Returns (rc, stdout, stderr)."""
    fd, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="lint_run_")
    try:
        user_db = _expand_db(db)
        full_source = f"{user_db};{source}"
        with os.fdopen(fd, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(_cmd_preamble())
            f.write(f'"%SECEXPR_CMD%" "{user_db}" --safe --source "{full_source}" -t < "{slang_path}"\n')

        _info(f"batch       : {batch_path}")
        _info(f"slang       : {slang_path} ({os.path.getsize(slang_path)} B)")
        _info(f"db          : {user_db}")
        _info(f"source      : {full_source}")
        _info(f"timeout     : {timeout}s")

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

        _info(f"elapsed : {elapsed:.1f}s")
        _info(f"exit_rc : {proc.returncode}")
        _info(f"stdout  : {len(stdout)} B  ->  {log_dir}/{debug_id}__stdout.txt")
        _info(f"stderr  : {len(stderr)} B  ->  {log_dir}/{debug_id}__stderr.txt")
        return proc.returncode, stdout, stderr
    finally:
        try:
            os.unlink(batch_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Parallel lint runner (queue-based)
# ---------------------------------------------------------------------------

MAX_PARALLEL_QUEUES = 4


def _lint_batch(
    batch: list[str],
    queue_id: int,
    db: str,
    source: str,
    log_dir: str,
    debug_id: str,
    timeout: int,
) -> tuple[int, int, str, str]:
    """Lint a batch of scripts in a single secexpr process.

    Returns (queue_id, rc, stdout, stderr).
    One secexpr startup cost covers all scripts in the batch.
    """
    slang = build_lint_slang(batch)
    slang_path = os.path.join(log_dir, f"{debug_id}__q{queue_id}.slang")
    _write_text(slang_path, slang)

    rc, stdout, stderr = run_slang(
        db=db,
        slang_path=slang_path,
        source=source,
        log_dir=log_dir,
        debug_id=f"{debug_id}__q{queue_id}",
        timeout=timeout,
    )
    return queue_id, rc, stdout, stderr


def _distribute_scripts(scripts: list[str], num_queues: int) -> list[list[str]]:
    """Round-robin distribute scripts across queues."""
    queues: list[list[str]] = [[] for _ in range(num_queues)]
    for i, name in enumerate(scripts):
        queues[i % num_queues].append(name)
    return queues


def run_lint_parallel(
    scripts: list[str],
    db: str,
    source: str,
    log_dir: str,
    debug_id: str,
    timeout: int,
) -> list[dict]:
    """Lint multiple scripts using parallel queues.

    Distributes scripts across up to MAX_PARALLEL_QUEUES queues. Each queue
    runs a single secexpr process that lints its scripts sequentially. This
    minimizes startup overhead (one secexpr startup per queue, not per script).
    """
    num_queues = min(len(scripts), MAX_PARALLEL_QUEUES)
    queues = _distribute_scripts(scripts, num_queues)

    _phase(f"Running {len(scripts)} scripts across {num_queues} parallel queues")
    for i, q in enumerate(queues):
        _info(f"Queue {i}: {q}")

    all_issues: list[dict] = []
    t0 = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_queues) as pool:
        futures = {
            pool.submit(
                _lint_batch, batch, i, db, source, log_dir, debug_id, timeout
            ): (i, batch)
            for i, batch in enumerate(queues)
        }

        for future in concurrent.futures.as_completed(futures):
            queue_id, batch = futures[future]
            try:
                _, rc, stdout, stderr = future.result()
            except Exception as exc:
                _info(f"ERROR in queue {queue_id} ({batch}): {exc}")
                continue

            if "FATAL_EXCEPTION=" in stdout:
                _info(f"FATAL_EXCEPTION in queue {queue_id}")
                tokens = re.split(r"(?=FATAL_EXCEPTION=)", stdout)
                for t in tokens:
                    if t.startswith("FATAL_EXCEPTION="):
                        _info(t[:500])
                continue

            issues = parse_lint_issues(stdout)
            all_issues.extend(issues)
            s1 = sum(1 for i in issues if i["status"] == 1)
            s2 = sum(1 for i in issues if i["status"] == 2)
            _info(f"Queue {queue_id} done: {len(issues)} issues (S1={s1}, S2={s2})")

    elapsed = time.time() - t0
    _info(f"Total parallel elapsed: {elapsed:.1f}s")
    return all_issues


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

def parse_lint_issues(stdout: str) -> list[dict]:
    """Parse ISSUE= markers from @LIBSlang::Lint output.

    Returns a list of dicts: {"script": str, "status": float, "text": str}
    """
    issues = []
    current_script = ""

    # Split on markers
    tokens = re.split(
        r"(?=PHASE=|SCRIPT_START=|SCRIPT_END=|ISSUE_COUNT=|ISSUE=|STEP=|FATAL_EXCEPTION=)",
        stdout,
    )

    for t in tokens:
        t = t.strip()
        if t.startswith("SCRIPT_START="):
            current_script = t[len("SCRIPT_START="):].strip()
        elif t.startswith("ISSUE="):
            val = t[len("ISSUE="):].strip()
            pipe_idx = val.find("|")
            if pipe_idx >= 0:
                status_str = val[:pipe_idx].strip()
                text = val[pipe_idx + 1:].strip()
                # Strip trailing NOTE: hints that Slang appends after newlines
                note_idx = text.find("\nNOTE:")
                if note_idx >= 0:
                    text = text[:note_idx].strip()
            else:
                status_str = val
                text = ""
            try:
                status = float(status_str)
            except ValueError:
                status = -1
            issues.append({
                "script": current_script,
                "status": status,
                "text": text,
            })

    return issues


def parse_precommit_result(stdout: str) -> str:
    """Extract the raw PRECOMMIT_RESULT= string from stdout."""
    tokens = re.split(
        r"(?=PHASE=|STEP=|PRECOMMIT_RESULT=|FATAL_EXCEPTION=)",
        stdout,
    )
    for t in tokens:
        t = t.strip()
        if t.startswith("PRECOMMIT_RESULT="):
            return t[len("PRECOMMIT_RESULT="):].strip()
    return ""


def _report_stdout_markers(stdout: str) -> None:
    tokens = re.split(
        r"(?=PHASE=|SCRIPT_START=|SCRIPT_END=|ISSUE_COUNT=|ISSUE=|STEP=|"
        r"PRECOMMIT_RESULT=|FATAL_EXCEPTION=)",
        stdout,
    )
    for t in tokens:
        t = t.strip()
        if t:
            _info(f">> {t[:300]}")


def severity_label(status: float) -> str:
    if status <= 0:
        return "Suggestion"
    elif status == 1:
        return "Error"
    elif status == 2:
        return "Warning"
    elif status < 3.75:
        return "Info"
    else:
        return "OK"


def format_issues_table(issues: list[dict]) -> str:
    """Format lint issues as a readable table."""
    if not issues:
        return "No issues found."

    # Count by severity
    s1 = sum(1 for i in issues if i["status"] == 1)
    s2 = sum(1 for i in issues if i["status"] == 2)
    s0 = sum(1 for i in issues if i["status"] <= 0)
    s3 = sum(1 for i in issues if i["status"] >= 3)

    lines = []
    lines.append(f"Total: {len(issues)} issues  (Status-1: {s1}, Status-2: {s2}, Status-0: {s0}, Status-3+: {s3})")
    lines.append("")
    lines.append(f"{'Status':<8} {'Severity':<12} {'Script':<40} {'Issue'}")
    lines.append(f"{'------':<8} {'--------':<12} {'------':<40} {'-----'}")

    for issue in sorted(issues, key=lambda x: x["status"]):
        s = f"{issue['status']:g}"
        sev = severity_label(issue["status"])
        script = issue["script"][:38]
        text = issue["text"][:120]
        lines.append(f"{s:<8} {sev:<12} {script:<40} {text}")

    lines.append("")
    gate = "PASS" if s1 == 0 and s2 == 0 else "FAIL"
    lines.append(f"Gate: {gate}  (Status-1: {s1}, Status-2: {s2})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run native Slang lint via secexpr --safe (read-only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--db", required=False, default="",
                    help='SecDB database path (e.g. "~{kerberos}!clean")')
    ap.add_argument("--scripts", nargs="+", required=False, default=None,
                    help="Script name(s) to lint")
    ap.add_argument("--args-file", default=None, metavar="PATH",
                    help="JSON file with lint arguments (keys: db, scripts, precommit, source, timeout)")
    ap.add_argument("--precommit", action="store_true",
                    help="Use @ScriptVal::PreCommit Check Lint instead of @LIBSlang::Lint")
    ap.add_argument("--source", default=None,
                    help=f"secexpr --source override (default: {DEFAULT_SOURCE})")
    ap.add_argument("--timeout", type=int, default=300,
                    help="secexpr timeout in seconds (default: 300)")
    ap.add_argument("--output-json", default=None, metavar="PATH",
                    help="Write machine-readable JSON results to PATH")
    args = ap.parse_args()

    # ---------- Load from args-file if provided ----------
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8") as af:
            af_data = json.load(af)
        if not args.scripts:
            args.scripts = af_data.get("scripts", [])
        if af_data.get("db"):
            args.db = af_data["db"]
        if af_data.get("precommit"):
            args.precommit = True
        if af_data.get("source") and not args.source:
            args.source = af_data["source"]
        if af_data.get("timeout") and args.timeout == 300:
            args.timeout = af_data["timeout"]
        if af_data.get("output_json") and not args.output_json:
            args.output_json = af_data["output_json"]
        if af_data.get("run_id"):
            args.run_id = af_data["run_id"]

    if not args.scripts:
        ap.error("--scripts is required (either via CLI or --args-file)")
    if not args.db:
        ap.error("--db is required (either via CLI or --args-file)")

    source = args.source or DEFAULT_SOURCE
    run_id = getattr(args, "run_id", None) or ""
    debug_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ld = _log_dir()

    # ---------- Write sentinel (signals "running") ----------
    json_path = args.output_json
    if not json_path:
        # Use run_id in filename to avoid collisions between concurrent sessions
        suffix = f"_{run_id}" if run_id else ""
        json_path = os.path.join(_REPO_ROOT, "workspace", "tmp",
                                  f"slang_lint_results{suffix}.json")
    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump({"status": "running", "run_id": run_id,
                   "scripts": args.scripts}, jf, indent=2)

    # ---------- Startup ----------
    _phase("lint.py — startup")
    user_db_expanded = _expand_db(args.db)
    _info(f"db          : {args.db}  (expanded: {user_db_expanded})")
    _info(f"source      : {user_db_expanded};{source}")
    _info(f"mode        : {'precommit' if args.precommit else 'lint'}")
    _info(f"scripts     : {args.scripts}")
    _info(f"debug_id    : {debug_id}")
    _info(f"log_dir     : {ld}")

    # ---------- Build & Execute ----------
    if args.precommit or len(args.scripts) == 1:
        # Single process: precommit batches all scripts in one call,
        # and single-script lint doesn't benefit from parallelism.
        _phase("Building Slang expression")
        if args.precommit:
            slang = build_precommit_lint_slang(args.scripts)
        else:
            slang = build_lint_slang(args.scripts)

        slang_path = os.path.join(ld, f"{debug_id}__lint_slang.slang")
        _write_text(slang_path, slang)
        _info(f"saved: {slang_path} ({len(slang)} B)")

        _phase("Running secexpr --safe (read-only)")
        rc, stdout, stderr = run_slang(
            db=args.db,
            slang_path=slang_path,
            source=source,
            log_dir=ld,
            debug_id=debug_id,
            timeout=args.timeout,
        )

        _phase("Parsing lint output")
        _report_stdout_markers(stdout)

        if "FATAL_EXCEPTION=" in stdout:
            _phase("FAILURE — fatal exception in lint")
            tokens = re.split(r"(?=FATAL_EXCEPTION=)", stdout)
            for t in tokens:
                if t.startswith("FATAL_EXCEPTION="):
                    _info(t[:500])
            sys.exit(1)

        if args.precommit:
            raw = parse_precommit_result(stdout)
            _phase("Precommit Lint Result (raw)")
            issues = []
            script_name = args.scripts[0] if len(args.scripts) == 1 else "(all)"
            for m in re.finditer(r'Status\s*:\s*([\d.]+)\s*,\s*Text\s*:\s*"([^"]*)"', raw):
                issues.append({
                    "script": script_name,
                    "status": float(m.group(1)),
                    "text": m.group(2),
                })
            if issues:
                print(format_issues_table(issues))
            else:
                print(raw[:2000] if raw else "(no result)")
        else:
            issues = parse_lint_issues(stdout)
            _phase("Lint Results")
            print(format_issues_table(issues))
    else:
        # Parallel: lint each script in its own secexpr process concurrently.
        issues = run_lint_parallel(
            scripts=args.scripts,
            db=args.db,
            source=source,
            log_dir=ld,
            debug_id=debug_id,
            timeout=args.timeout,
        )
        _phase("Lint Results (parallel)")
        print(format_issues_table(issues))

    # ---------- JSON output ----------
    s1 = sum(1 for i in issues if i["status"] == 1)
    s2 = sum(1 for i in issues if i["status"] == 2)
    gate = "PASS" if s1 == 0 and s2 == 0 else "FAIL"

    result_obj = {
        "status": "done",
        "run_id": run_id,
        "gate": gate,
        "status_1": s1,
        "status_2": s2,
        "total": len(issues),
        "issues": issues,
    }
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(result_obj, jf, indent=2)
    _info(f"JSON results: {json_path}")

    # ---------- Gate ----------
    sys.exit(1 if (s1 > 0 or s2 > 0) else 0)


if __name__ == "__main__":
    main()
