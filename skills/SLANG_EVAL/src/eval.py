"""Evaluate Slang expressions via the VS Code extension's SSP/REPL endpoint.

Connects to the running Slang extension's background secexpr process over
HTTP JSON-RPC — the same protocol the extension itself uses when you press F9.
~100x faster than cold-start secexpr because the SecDB session is already warm.

Requires the VS Code Slang extension to be running with an active REPL session.

Usage:
    # Inline expression
    python eval.py -e "1 + 1"

    # Multi-line expression from file
    python eval.py -f workspace/tmp/expr.slang

    # Run a named script
    python eval.py -s "_UT Some Script"

    # Custom port (default: auto-detect)
    python eval.py --port 8000 -e "Date()"

    # Raw JSON output (for piping)
    python eval.py --json -e "EnumFromTo(1,5)"

    # Timeout override (default: 30s)
    python eval.py --timeout 120 -e "SlowComputation()"
"""

import argparse
import atexit
import io
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import urllib.error

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(SKILL_DIR, "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402

SSP_PATH = "/ssp/Current/Slang_Virtual_Filesystem"
DEFAULT_TIMEOUT = 30
CONNECT_TIMEOUT = 5


# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

def discover_ssp_port() -> int:
    """Find the SSP REPL port by scanning secexpr processes for loopback listeners.

    The VS Code extension spawns secexpr processes that listen on 127.0.0.1.
    The REPL endpoint is the one accepting JSON-RPC on the SSP path.
    """
    # Use netstat to find secexpr loopback listeners (cross-platform-ish on Windows)
    try:
        result = run_cmd(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process secexpr -EA SilentlyContinue | ForEach-Object {"
             "  Get-NetTCPConnection -OwningProcess $_.Id -State Listen -EA SilentlyContinue"
             "} | Where-Object { $_.LocalAddress -eq '127.0.0.1' }"
             " | Select-Object -ExpandProperty LocalPort"],
            capture_output=True, timeout=10
        )
        ports_text = result.stdout.decode("utf-8", errors="replace").strip()
        if not ports_text:
            return 0
        ports = []
        for line in ports_text.splitlines():
            line = line.strip()
            if line.isdigit():
                ports.append(int(line))
        # Probe each port with a lightweight REPL ping
        # Prefer higher ports — the REPL session is typically started after VFS
        for port in sorted(ports, reverse=True):
            if _probe_ssp(port):
                return port
        return 0
    except Exception:
        return 0


def _probe_ssp(port: int) -> bool:
    """Send a trivial REPL request to check if this port hosts the SSP endpoint."""
    try:
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 0,
            "method": "REPL",
            "params": {"Expression": "1", "Script": ""}
        }).encode("latin-1")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{SSP_PATH}",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT)
        body = json.loads(resp.read().decode("latin-1"))
        # Must have a result (not an error) and the value should be "1"
        if "error" in body:
            return False
        try:
            inner = json.loads(body.get("result", "{}"))
            return inner.get("value") == "1"
        except Exception:
            return "result" in body
    except Exception:
        return False


# ---------------------------------------------------------------------------
# SSP JSON-RPC client
# ---------------------------------------------------------------------------

def ssp_evaluate(port: int, expression: str, timeout: int) -> dict:
    """Send a REPL evaluation request and return the parsed response.

    Returns dict with keys:
        ok      - bool
        value   - str (Slang result as string) if ok
        error   - str (error message) if not ok
        elapsed - float (seconds)
    """
    url = f"http://127.0.0.1:{port}{SSP_PATH}"
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "REPL",
        "params": {"Expression": expression, "Script": ""}
    }).encode("latin-1")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode("latin-1")
        elapsed = time.perf_counter() - t0
    except urllib.error.URLError as e:
        elapsed = time.perf_counter() - t0
        return {"ok": False, "error": f"Connection failed: {e}", "elapsed": elapsed}
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {"ok": False, "error": str(e), "elapsed": elapsed}

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"Invalid JSON response: {body[:200]}", "elapsed": elapsed}

    if "error" in data:
        err = data["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return {"ok": False, "error": msg, "elapsed": elapsed}

    # The result field is itself a JSON string: {"value": "..."}
    result_str = data.get("result", "{}")
    try:
        inner = json.loads(result_str)
        value = inner.get("value", result_str)
    except (json.JSONDecodeError, TypeError):
        value = result_str

    return {"ok": True, "value": value, "elapsed": elapsed}


def ssp_run_script(port: int, script_name: str, timeout: int) -> dict:
    """Evaluate a named script via the REPL."""
    # Running a named script = evaluating it by name as an expression
    # The extension does: method=REPL, params={Expression: expr, Script: scriptName}
    url = f"http://127.0.0.1:{port}{SSP_PATH}"
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "REPL",
        "params": {"Expression": "", "Script": script_name}
    }).encode("latin-1")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode("latin-1")
        elapsed = time.perf_counter() - t0
    except urllib.error.URLError as e:
        elapsed = time.perf_counter() - t0
        return {"ok": False, "error": f"Connection failed: {e}", "elapsed": elapsed}
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {"ok": False, "error": str(e), "elapsed": elapsed}

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"Invalid JSON response: {body[:200]}", "elapsed": elapsed}

    if "error" in data:
        err = data["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return {"ok": False, "error": msg, "elapsed": elapsed}

    result_str = data.get("result", "{}")
    try:
        inner = json.loads(result_str)
        value = inner.get("value", result_str)
    except (json.JSONDecodeError, TypeError):
        value = result_str

    return {"ok": True, "value": value, "elapsed": elapsed}


# ---------------------------------------------------------------------------
# CLI
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


def main():
    _apply_args_file()
    parser = argparse.ArgumentParser(
        description="Evaluate Slang via VS Code extension SSP/REPL endpoint"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-e", "--expression", help="Slang expression to evaluate")
    group.add_argument("-f", "--file", help="File containing Slang expression(s)")
    group.add_argument("-s", "--script", help="Named script to run")
    parser.add_argument("--port", type=int, default=0,
                        help="SSP port (default: auto-detect)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON (for piping to other tools)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress timing info, only print result")
    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")
    args = parser.parse_args()
    _setup_out_file(args.out_file)

    # Resolve port
    port = args.port
    if port == 0:
        if not args.quiet:
            print("[eval] Auto-detecting SSP port...", file=sys.stderr)
        port = discover_ssp_port()
        if port == 0:
            print("ERROR: Could not find VS Code extension SSP endpoint.\n"
                  "Is the Slang extension running with an active REPL session?\n"
                  "Try: Ctrl+Shift+P -> 'Slang: Show REPL'", file=sys.stderr)
            sys.exit(1)
        if not args.quiet:
            print(f"[eval] Found SSP on port {port}", file=sys.stderr)

    # Build expression
    if args.expression:
        expr = args.expression
    elif args.file:
        if not os.path.isfile(args.file):
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as fh:
            expr = fh.read()
    else:
        expr = None

    # Execute
    if args.script:
        result = ssp_run_script(port, args.script, args.timeout)
    elif args.file:
        # File mode: evaluate each non-empty line separately (like secexpr stdin).
        # Variables assigned at top-level persist across lines within the session.
        lines = [ln.strip() for ln in expr.splitlines() if ln.strip()]
        result = {"ok": True, "value": "", "elapsed": 0.0}
        for i, line in enumerate(lines):
            r = ssp_evaluate(port, line, args.timeout)
            result["elapsed"] += r["elapsed"]
            if not r["ok"]:
                result = r
                if not args.quiet:
                    print(f"[eval] Line {i+1} failed: {line}", file=sys.stderr)
                break
            result = r
    else:
        result = ssp_evaluate(port, expr, args.timeout)

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["ok"]:
        if not args.quiet:
            print(f"[eval] OK ({result['elapsed']*1000:.0f}ms)", file=sys.stderr)
        print(result["value"])
    else:
        if not args.quiet:
            print(f"[eval] ERROR ({result['elapsed']*1000:.0f}ms)", file=sys.stderr)
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
