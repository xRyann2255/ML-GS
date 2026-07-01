"""Inspect ScriptReview containers (load details + list scripts + CVS revs).

Example:
  python inspect.py --db "~{kerberos}!clean" --review "Review 20260406 6010-2216107S*"

This is read-only and meant to validate SLANG_REVIEW updates.
"""

from __future__ import annotations

import atexit
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402


ENV_CMD = r"H:\all-languages-env.cmd"
SCRIPT_REVIEW_BASE_URL = "https://www.epssp.site.gs.com/ssps/ProdSource/ScriptReview?Name="


def _script_review_url(review_name: str) -> str:
    return SCRIPT_REVIEW_BASE_URL + urllib.parse.quote_plus(review_name)


def _powershell_invoke_webrequest_content(url: str, timeout_s: int) -> tuple[bool, str, str]:
    """Fetch URL content using PowerShell with default credentials.

    Returns (ok, stdout, stderr). stdout is the page content when ok.
    """
    ps = (
        "$ErrorActionPreference='Stop';"
        "$ProgressPreference='SilentlyContinue';"
        # -UseBasicParsing avoids the interactive security prompt in Windows PowerShell.
        f"$r=Invoke-WebRequest -Uri '{url}' -UseDefaultCredentials -UseBasicParsing -MaximumRedirection 5 -TimeoutSec {int(max(5, timeout_s))};"
        "[Console]::Out.Write($r.Content)"
    )
    try:
        proc = run_cmd(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            timeout=max(5, timeout_s + 5),
        )
    except subprocess.TimeoutExpired as e:
        stdout = (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or "")
        return False, stdout, f"TimeoutExpired: {e}\n{stderr}".strip()

    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode == 0 and bool(stdout.strip()), stdout, stderr


def _extract_shame_signals(html: str) -> tuple[int | None, bool]:
    # There isn't a stable public HTML contract here. We treat this as best-effort.
    # Capture any integers that appear close to the word "Shame".
    shame_vals: list[int] = []
    for m in re.finditer(r"Shame[^0-9]{0,80}([0-9]{1,6})", html, flags=re.IGNORECASE):
        try:
            shame_vals.append(int(m.group(1)))
        except ValueError:
            pass
    shame_max = max(shame_vals) if shame_vals else None

    shame_increased = bool(
        re.search(r"shame\s+has\s+increased|increased\s+shame|shame\s+increased", html, flags=re.IGNORECASE)
    )
    return shame_max, shame_increased


def _extract_no_test_in_header_issues(html: str, max_items: int = 10) -> list[str]:
    issues: list[str] = []
    # Try a few patterns: sometimes HTML contains the full phrase, sometimes it is in a log-like block.
    patterns = [
        r"No\s+test\s+in\s+header\s+for\s+([^\r\n<]{1,200})",
        r"Test\s+Results\s*=\s*No\s+test\s+in\s+header\s+for\s+([^\r\n<]{1,200})",
    ]
    for pat in patterns:
        for m in re.finditer(pat, html, flags=re.IGNORECASE):
            item = m.group(0).strip()
            if item and item not in issues:
                issues.append(item)
            if len(issues) >= max_items:
                return issues
    return issues


def _repo_root_from_this_file() -> str:
    # .../skills/SLANG_REVIEW_INSPECT/src -> repo root
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def _workspace_tmp_dir() -> str:
    root = _repo_root_from_this_file()
    return os.path.join(root, "workspace", "tmp")


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _timestamp_id() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _cmd_wrapper_preamble() -> str:
    # Disable delayed expansion so DB paths containing '!' are not mangled by cmd.
    return (
        "@echo off\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        f"call {ENV_CMD} >nul 2>&1\r\n"
        "setlocal DisableDelayedExpansion\r\n"
    )


def _slang_escape(text: str) -> str:
    """Escape for embedding inside a Slang string literal."""
    return text.replace('"', '""')


def build_inspect_review_slang(review_name: str) -> str:
    # Avoid any fancy dependencies: use only the load fns + basic utils.
    # Use Chr(58) for colons just in case.
    if ":" in review_name:
        left, right = review_name.split(":", 1)
        review_expr = f'Sprint( "{_slang_escape(left)}", Chr( 58 ), "{_slang_escape(right)}" )'
    else:
        review_expr = f'"{_slang_escape(review_name)}"'

    return f'''Link( "_LIB Script Review Load Fns" );
Link( "_LIB CVS Script Functions" );
Link( "_LIB Security Fns" );

Review Name = {review_expr};
Diffs = @Script Review::Load Review( Review Name, Use RW Db := False, Refresh := True );

// Some environments return an error-like value that still has useful fields.
Container = "";
Try() Container = Diffs.ContainerName : Container = "";

If( !Size( Container ) )
{{
    Print( Sprint( "INSPECT_LOAD_FAILED=1", Chr( 10 ) ) );
    Print( Sprint( "REVIEW_CONTAINER=", "", Chr( 10 ) ) );
}}
:
{{
    Print( Sprint( "INSPECT_LOAD_FAILED=0", Chr( 10 ) ) );
    Print( Sprint( "REVIEW_CONTAINER=", Container, Chr( 10 ) ) );
    Try() Print( Sprint( "LATEST_VERSION=", String( Diffs.Latest Version Number() ), Chr( 10 ) ) ) : Print( Sprint( "LATEST_VERSION=?", Chr( 10 ) ) );

    Scripts = Diffs.Submission Names( Code Type := ScriptReviewCodeType::Slang );
    Print( Sprint( "NUM_SCRIPTS=", String( Size( Scripts ) ), Chr( 10 ) ) );

    ForEach( S, Scripts )
    {{
        ScriptName = String( S );
        Print( Sprint( "SCRIPT=", ScriptName, Chr( 10 ) ) );

        Sec = GetSecurity( ScriptName );
        RevS = "?";
        Try() RevS = String( @CVS::Script Revision( Sec ) ) : RevS = "?";
        Print( Sprint( "SCRIPT_CVS_REV=", ScriptName, Chr( 9 ), RevS, Chr( 10 ) ) );

        // Best-effort: inspect the script header to detect RegTest/Test Script header fields.
        // (Used to interpret certain ScriptReview web page warnings.)
        Expr = "";
        Try() Expr = String( GetValue( "Expression", Sec ) ) : Expr = "";
        IsRegTest = 0;
        HasTestScriptHdr = 0;
        If( Size( Expr ) )
        {{
            If( StrContains( Expr, "Script Type : RegTest" ) ) IsRegTest = 1;
            If( StrContains( Expr, "Test Script :" ) ) HasTestScriptHdr = 1;
        }};
        Print( Sprint( "SCRIPT_HEADER_REGTEST=", ScriptName, Chr( 9 ), String( IsRegTest ), Chr( 10 ) ) );
        Print( Sprint( "SCRIPT_HEADER_TESTSCRIPT=", ScriptName, Chr( 9 ), String( HasTestScriptHdr ), Chr( 10 ) ) );
    }};

    Print( Sprint( "REVIEW_URL=", Container, Chr( 10 ) ) );
}};
'''


def run_slang_via_secexpr_stdin(
    db: str,
    source: str | None,
    slang: str,
    log_dir: str,
    debug_id: str,
) -> tuple[int, str, str]:
    fd_slang, slang_path = tempfile.mkstemp(suffix=".slang", prefix="inspect_review_")
    try:
        with os.fdopen(fd_slang, "w", encoding="utf-8", newline="\n") as f:
            f.write(slang)

        fd_bat, bat_path = tempfile.mkstemp(suffix=".cmd", prefix="inspect_review_")
        try:
            with os.fdopen(fd_bat, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(_cmd_wrapper_preamble())
                source_flag = f'--source "{source}" ' if source else ""
                f.write(f'secexpr "{db}" --safe {source_flag}-t < "{slang_path}"\n')

            proc = run_cmd(["cmd", "/c", bat_path], capture_output=True, timeout=600)
            stdout = proc.stdout.decode("utf-8", errors="replace")
            stderr = proc.stderr.decode("utf-8", errors="replace")

            _ensure_dir(log_dir)
            _write_text(os.path.join(log_dir, f"{debug_id}__stdout.txt"), stdout)
            _write_text(os.path.join(log_dir, f"{debug_id}__stderr.txt"), stderr)

            return proc.returncode, stdout, stderr
        finally:
            try:
                os.unlink(bat_path)
            except OSError:
                pass
    finally:
        try:
            os.unlink(slang_path)
        except OSError:
            pass


def parse_scripts_from_stdout(stdout: str) -> list[str]:
    scripts: list[str] = []
    for line in stdout.splitlines():
        if line.startswith("SCRIPT="):
            scripts.append(line[len("SCRIPT=") :].strip())
    return scripts


def _print_final_marker_block(stdout: str) -> None:
    """Print only the final machine-parseable marker block.

    In some secexpr sessions we can see multiple marker blocks appear in one run
    (e.g. a transient load failure followed by success). For validation, we want
    the *last* block.
    """
    prefixes = (
        "INSPECT_LOAD_FAILED=",
        "REVIEW_CONTAINER=",
        "LATEST_VERSION=",
        "NUM_SCRIPTS=",
        "SCRIPT=",
        "SCRIPT_CVS_REV=",
        "SCRIPT_HEADER_REGTEST=",
        "SCRIPT_HEADER_TESTSCRIPT=",
        "REVIEW_URL=",
    )

    lines = stdout.splitlines()
    marker_idxs = [i for i, ln in enumerate(lines) if ln.startswith("INSPECT_LOAD_FAILED=")]
    start = marker_idxs[-1] if marker_idxs else 0

    for ln in lines[start:]:
        if ln.startswith(prefixes):
            print(ln)


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
    ap = argparse.ArgumentParser(description="Inspect ScriptReview container details")
    ap.add_argument("--db", required=True, help='Object DB (e.g. "~{kerberos}!clean")')
    ap.add_argument("--review", required=True, help='Review container name (e.g. "Review 20260406 6010-2216107S*")')
    ap.add_argument("--source", default=None, help="Optional secexpr --source chain override")
    ap.add_argument(
        "--no-web-check",
        action="store_true",
        help="Skip fetching/parsing the ScriptReview web page (SSO/default-cred fetch can fail in some environments)",
    )
    ap.add_argument(
        "--web-timeout",
        type=int,
        default=30,
        help="Timeout in seconds for the web page fetch (default: 30)",
    )
    ap.add_argument("--out-file", default=None, metavar="PATH",
                    help="Write output to this file")
    args = ap.parse_args()
    _setup_out_file(args.out_file)

    debug_id = _timestamp_id()
    log_dir = _ensure_dir(os.path.join(_workspace_tmp_dir(), "slang_review_inspect_logs"))
    print(f"Logs: {log_dir}")

    slang = build_inspect_review_slang(args.review)
    aux_path = os.path.join(log_dir, f"{debug_id}__aux_inspect_slang.slang")
    _write_text(aux_path, slang)
    print(f"Aux Slang saved: {aux_path}")

    rc, stdout, stderr = run_slang_via_secexpr_stdin(
        db=args.db,
        source=args.source,
        slang=slang,
        log_dir=log_dir,
        debug_id=debug_id,
    )

    # Echo only the final marker block to console (this is what callers parse)
    if stdout.strip():
        _print_final_marker_block(stdout)

    # Be conservative: stderr is often noisy, but still useful
    if stderr.strip():
        # Print only a short tail
        tail = "\n".join(stderr.splitlines()[-40:])
        print("--- STDERR (tail) ---", file=sys.stderr)
        print(tail, file=sys.stderr)

    # Exit status follows secexpr; but if we got a REVIEW_CONTAINER marker, treat as success.
    ok = any(line.startswith("REVIEW_CONTAINER=") for line in stdout.splitlines())
    if not ok:
        return 1 if rc == 0 else rc

    # Optional: fetch ScriptReview web page and flag known problem indicators.
    # This is a best-effort extra validation layer (complements the Slang load markers).
    scripts = parse_scripts_from_stdout(stdout)
    has_test_script_name = any(s.startswith("Test:") for s in scripts)

    header_regtest: set[str] = set()
    header_testscript: set[str] = set()
    for line in stdout.splitlines():
        if line.startswith("SCRIPT_HEADER_REGTEST="):
            payload = line[len("SCRIPT_HEADER_REGTEST=") :]
            parts = payload.split("\t", 1)
            if len(parts) == 2 and parts[1].strip() == "1":
                header_regtest.add(parts[0].strip())
        elif line.startswith("SCRIPT_HEADER_TESTSCRIPT="):
            payload = line[len("SCRIPT_HEADER_TESTSCRIPT=") :]
            parts = payload.split("\t", 1)
            if len(parts) == 2 and parts[1].strip() == "1":
                header_testscript.add(parts[0].strip())

    # Prefer header-based detection (more precise): RegTest + has Test Script header.
    header_based = header_regtest.intersection(header_testscript)
    has_test_script_header = bool(header_based)
    has_test_script = has_test_script_header if (header_regtest or header_testscript) else has_test_script_name

    print(f"HAS_TEST_SCRIPT={1 if has_test_script else 0}")
    print(f"HAS_TEST_SCRIPT_NAME={1 if has_test_script_name else 0}")
    print(f"HAS_TEST_SCRIPT_HEADER={1 if has_test_script_header else 0}")

    if args.no_web_check:
        print("WEB_FETCH_SKIPPED=1")
    else:
        url = _script_review_url(args.review)
        web_ok, html, web_err = _powershell_invoke_webrequest_content(url, timeout_s=args.web_timeout)
        web_log_path = os.path.join(log_dir, f"{debug_id}__scriptreview_web.html")
        if web_ok:
            _write_text(web_log_path, html)
            print("WEB_FETCH_FAILED=0")
            shame_max, shame_increased = _extract_shame_signals(html)
            no_test_issues = _extract_no_test_in_header_issues(html)

            print(f"WEB_SHAME_MAX={shame_max if shame_max is not None else '?'}")
            print(f"WEB_SHAME_INCREASED={1 if shame_increased else 0}")
            print(f"WEB_NO_TEST_IN_HEADER_COUNT={len(no_test_issues)}")
            for issue in no_test_issues:
                # Keep this parseable and bounded.
                print(f"WEB_NO_TEST_IN_HEADER={issue}")

            web_problem = False
            if shame_increased:
                web_problem = True
            if has_test_script and no_test_issues:
                web_problem = True
            print(f"WEB_PROBLEM={1 if web_problem else 0}")
        else:
            # Save whatever we got for debugging; but do not spam console.
            if html.strip():
                _write_text(web_log_path, html)
            err_path = os.path.join(log_dir, f"{debug_id}__scriptreview_web.stderr.txt")
            if web_err.strip():
                _write_text(err_path, web_err)
            print("WEB_FETCH_FAILED=1")
            print("WEB_PROBLEM=?")

    # Prefer REVIEW_URL marker if present
    review_name = None
    for line in stdout.splitlines():
        if line.startswith("REVIEW_URL="):
            review_name = line[len("REVIEW_URL=") :].strip()
    if review_name:
        print(f"BROWSER_URL={_script_review_url(review_name)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
