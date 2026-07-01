"""
Fetch process list from the Procmon API.

Handles the OIDC auth flow:
1. GET ProcessList -> 302 -> capture state cookie + OIDC URL
2. curl.exe --negotiate to PingFederate -> form_post HTML with auth code
3. POST auth code back to Procmon -> session cookies
4. GET ProcessList with session cookies -> JSON result

Usage:
    python fetch_process_list.py [RUN_DATE] --master MASTER --process REGEX [--all-statuses]

    RUN_DATE      defaults to T-1 (yesterday). Format: YYYYMMDD
    --master      required: Procmon master (e.g. eq3, eq)
    --process     required: process name regex filter
    --all-statuses: show all statuses (default: Failed only)

Output:
    JSON to stdout: { "timestamp": "...", "run_date": "...", "count": N, "processes": [...] }
    Progress to stderr.

Exit codes:
    0 -- success
    1 -- auth failure or missing required argument
    2 -- no data / unexpected response
"""
import subprocess
import re
import sys
import os
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402


PROCMON_BASE_TEMPLATE = "https://{master}.procmon.services.gs.com"
PROCESSLIST_PATH = "/kerb/master/ProcessList.cgi"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))
TMP_DIR = os.path.join(WORKSPACE_ROOT, "workspace", "tmp", "procmon-jobs")


def previous_business_day():
    """Return the previous business day as YYYYMMDD (skips weekends)."""
    d = datetime.now() - timedelta(days=1)
    while d.weekday() >= 5:  # 5=Saturday, 6=Sunday
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def build_url(run_date, master, process_regex, failed_only=True):
    """Build the ProcessList URL with appropriate filters."""
    base = PROCMON_BASE_TEMPLATE.format(master=master)
    params = {
        "Master": master,
        "RunDate": run_date,
        "Process": process_regex,
        "Location": "NYC",
        "nolog": "0",
    }
    # Turn OFF all statuses except Failed when failed_only=True.
    always_off = [
        "Waiting", "Unrunnable", "Ready", "Queued", "Launched",
        "Running", "Done", "Succeeded", "Canceled",
        "Host Unreachable", "Unacknowledged", "Manual",
        "Inactive", "Skipped", "OtherMaster",
    ]
    if failed_only:
        for status in always_off:
            params[f"FILTER-{status}"] = "OFF"

    return f"{base}{PROCESSLIST_PATH}?{urlencode(params)}"


def curl(*args, capture_stderr=False):
    """Run curl.exe and return stdout (and optionally stderr)."""
    cmd = ["curl.exe"] + list(args)
    result = run_cmd(cmd, capture_output=True, text=True, timeout=30)
    if capture_stderr:
        return result.stdout, result.stderr
    return result.stdout


def authenticate(target_url):
    """
    Complete the OIDC auth flow and return path to a cookie jar file.

    Steps:
    1. GET target_url -> 302 -> capture state cookie + OIDC redirect
    2. curl --negotiate to PingFederate -> get form_post HTML
    3. POST auth code back -> session cookies
    """
    os.makedirs(TMP_DIR, exist_ok=True)
    cookie_jar = os.path.join(TMP_DIR, "procmon_cookies.txt")

    from urllib.parse import urlparse
    parsed = urlparse(target_url)
    base_url = f"{parsed.scheme}://{parsed.hostname}"

    # Step 1: Get the OIDC redirect
    print("  [auth] Step 1: Getting OIDC redirect...", file=sys.stderr)
    headers_out, _ = curl(
        "-s", "-D", "-", "-o", os.devnull, target_url,
        capture_stderr=True,
    )

    location = None
    state_cookie = None
    for line in headers_out.splitlines():
        if line.lower().startswith("location:"):
            location = line.split(":", 1)[1].strip()
        if line.lower().startswith("set-cookie: mod_auth_openidc_state"):
            state_cookie = line.split(":", 1)[1].strip().split(";")[0].strip()

    if not location:
        print("  [auth] ERROR: No OIDC redirect found", file=sys.stderr)
        sys.exit(1)

    print(f"  [auth] OIDC URL: {location[:80]}...", file=sys.stderr)

    # Step 2: Hit PingFederate with Kerberos negotiate
    print("  [auth] Step 2: Kerberos negotiate with PingFederate...", file=sys.stderr)
    form_html = curl(
        "-s", "-L", "--negotiate", "-u", ":",
        "-c", cookie_jar, "-b", cookie_jar,
        location,
    )

    code_match = re.search(r'name="code"\s+value="([^"]+)"', form_html)
    state_match = re.search(r'name="state"\s+value="([^"]+)"', form_html)

    if not code_match or not state_match:
        print("  [auth] ERROR: Could not parse OIDC form_post", file=sys.stderr)
        print(f"  [auth] Response (first 200 chars): {form_html[:200]}", file=sys.stderr)
        sys.exit(1)

    code = code_match.group(1)
    state = state_match.group(1)
    print(f"  [auth] Got auth code: {code[:20]}...", file=sys.stderr)

    # Step 3: POST auth code back to Procmon
    print("  [auth] Step 3: Posting auth code to Procmon...", file=sys.stderr)
    curl(
        "-s", "-L",
        "-c", cookie_jar,
        "-b", state_cookie,
        "-d", f"code={code}",
        "-d", f"state={state}",
        f"{base_url}:443/oidc_redirect",
    )

    if not os.path.exists(cookie_jar):
        print("  [auth] ERROR: No cookie jar created", file=sys.stderr)
        sys.exit(1)

    with open(cookie_jar) as f:
        content = f.read()
    if "mod_auth_openidc_session" not in content:
        print("  [auth] ERROR: No session cookies in jar", file=sys.stderr)
        sys.exit(1)

    print("  [auth] Authentication successful", file=sys.stderr)
    return cookie_jar


def fetch_process_list(run_date, master, process_regex, failed_only=True):
    """
    Fetch the process list from Procmon.

    Returns parsed JSON: [timestamp, [process_dicts]].
    """
    url = build_url(run_date, master=master, process_regex=process_regex, failed_only=failed_only)
    mode = "Failed only" if failed_only else "All statuses"
    print(f"Fetching processes for {run_date} ({mode}) on master={master}...", file=sys.stderr)

    os.makedirs(TMP_DIR, exist_ok=True)
    cookie_jar = os.path.join(TMP_DIR, "procmon_cookies.txt")
    if os.path.exists(cookie_jar):
        result = curl("-s", "-b", cookie_jar, url)
        if result.strip().startswith("["):
            return json.loads(result)

    print("  Session expired or missing, authenticating...", file=sys.stderr)
    cookie_jar = authenticate(url)

    result = curl("-s", "-b", cookie_jar, url)
    if not result.strip().startswith("["):
        print(f"ERROR: Unexpected response: {result[:200]}", file=sys.stderr)
        sys.exit(2)

    return json.loads(result)


def main():
    # --args-file support: load JSON and rebuild argv as CLI flags
    if "--args-file" in sys.argv:
        idx = sys.argv.index("--args-file")
        with open(sys.argv[idx + 1], "r", encoding="utf-8") as _f:
            _af = json.load(_f)
        _argv = [sys.argv[0]]
        if "run_date" in _af and _af["run_date"]:
            _argv.append(str(_af["run_date"]))
        for _k, _v in _af.items():
            if _k in ("args_file", "run_date", "out_file"):
                continue
            _flag = f"--{_k.replace('_', '-')}"
            if isinstance(_v, bool):
                if _v:
                    _argv.append(_flag)
            elif _v is not None:
                _argv.extend([_flag, str(_v)])
        sys.argv = _argv
        _out_file = _af.get("out_file")
    else:
        _out_file = None

    run_date = None
    failed_only = True
    process_regex = None
    master = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--all-statuses":
            failed_only = False
        elif arg == "--process" and i + 1 < len(sys.argv):
            i += 1
            process_regex = sys.argv[i]
        elif arg == "--master" and i + 1 < len(sys.argv):
            i += 1
            master = sys.argv[i]
        elif not arg.startswith("-"):
            run_date = arg
        i += 1

    if not master:
        print("ERROR: --master is required", file=sys.stderr)
        sys.exit(1)
    if not process_regex:
        print("ERROR: --process is required", file=sys.stderr)
        sys.exit(1)
    if not run_date:
        run_date = previous_business_day()

    data = fetch_process_list(run_date, master=master, process_regex=process_regex, failed_only=failed_only)

    timestamp = data[0] if data else "?"
    processes = data[1] if len(data) > 1 else []

    output = {
        "timestamp": timestamp,
        "run_date": run_date,
        "failed_only": failed_only,
        "count": len(processes),
        "processes": processes,
    }

    json.dump(output, sys.stdout, indent=2)
    print()

    if _out_file:
        os.makedirs(os.path.dirname(os.path.abspath(_out_file)), exist_ok=True)
        with open(_out_file, "w", encoding="utf-8") as _f:
            json.dump(output, _f, indent=2)

    print(f"\nTimestamp: {timestamp}", file=sys.stderr)
    print(f"Processes found: {len(processes)}", file=sys.stderr)
    for i, proc in enumerate(processes):
        name = proc.get("ProcessName", "?")
        status = proc.get("Status", "?")
        print(f"  [{i+1}] status={status} {name}", file=sys.stderr)


if __name__ == "__main__":
    main()
