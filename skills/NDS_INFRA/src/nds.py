"""Query NDS Infrastructure Services for user desktops and desktop details.

Usage:
    python nds.py user nunesa                          # NDS assignments for a user
    python nds.py user nunesa silfel --json             # Multiple users, JSON output
    python nds.py desktop DCNDS0432561                  # Desktop machine details
    python nds.py desktop DCNDS0432561 DCNDS0123456     # Multiple desktops
    python nds.py dialtone DCNDS0432561                 # Dialtone health history
    python nds.py dialtone DCNDS0432561 --last 5        # Last 5 scans only
"""

import argparse
import atexit
import html as html_mod
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
import ssl

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402

BASE_URL = "http://iws.web.gs.com/NdsInfraServices/Home"
SSO_URL = "https://authn.web.gs.com/desktopsso/Login"

WORKSPACE_TMP = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "workspace", "tmp"
)


def get_gssso_cookie() -> str:
    """Get GSSSO cookie using PowerShell Windows integrated auth."""
    ps_cmd = (
        "$null = Invoke-WebRequest -Uri '{}' "
        "-UseDefaultCredentials -UseBasicParsing "
        "-SessionVariable s -MaximumRedirection 10 "
        "-ErrorAction Stop; "
        "$s.Cookies.GetCookies('https://gs.com') "
        "| Where-Object {{ $_.Name -eq 'GSSSO' }} "
        "| Select-Object -ExpandProperty Value"
    ).format(SSO_URL)

    result = run_cmd(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=30,
    )

    cookie = result.stdout.strip()
    if not cookie:
        print("ERROR: Could not obtain GSSSO cookie.", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr[:500], file=sys.stderr)
        sys.exit(1)

    return cookie


def fetch_page(url: str, cookie: str) -> str:
    """Fetch an HTML page with GSSSO auth using PowerShell session."""
    ps_cmd = (
        "$ProgressPreference = 'SilentlyContinue'; "
        "$null = Invoke-WebRequest -Uri '{}' "
        "-UseDefaultCredentials -UseBasicParsing "
        "-SessionVariable s -MaximumRedirection 10 -ErrorAction Stop; "
        "$r = Invoke-WebRequest -Uri '{}' "
        "-WebSession $s -UseBasicParsing -TimeoutSec 30; "
        "$r.Content"
    ).format(SSO_URL, url)

    result = run_cmd(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=45,
    )

    if result.returncode != 0 or not result.stdout.strip():
        err = result.stderr[:500] if result.stderr else "Empty response"
        print(f"ERROR: Failed to fetch {url}", file=sys.stderr)
        print(err, file=sys.stderr)
        raise RuntimeError(f"Failed to fetch {url}: {err[:200]}")

    return result.stdout


# ---------------------------------------------------------------------------
# HTML parsers — itemtable (TH/TD key-value) and gridtable (columnar)
# ---------------------------------------------------------------------------

def parse_itemtable(html: str, label: str) -> str:
    """Extract a value from a <th>Label</th><td>Value</td> pair."""
    pattern = rf"<th>{re.escape(label)}</th>\s*<td>(.*?)</td>"
    m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if m:
        raw = m.group(1)
        # strip HTML tags
        text = re.sub(r"<[^>]+>", " ", raw)
        # collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return html_mod.unescape(text)
    return ""


def parse_gridtable_rows(html: str, section_heading: str) -> list[dict]:
    """Parse a gridtable section into a list of dicts keyed by header names.

    Handles action columns (Edit/Unmap/Disable) that have empty (&nbsp;) headers
    by counting cells per row and aligning from the right when header count
    doesn't match cell count.
    """
    heading_pat = rf"<h2>{re.escape(section_heading)}</h2>"
    hm = re.search(heading_pat, html, re.IGNORECASE)
    if not hm:
        return []
    rest = html[hm.end():]
    table_m = re.search(r"<table>(.*?)</table>", rest, re.DOTALL | re.IGNORECASE)
    if not table_m:
        return []
    table_html = table_m.group(1)

    # Extract all headers (including empty ones)
    header_row = re.search(r"<tr>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
    if not header_row:
        return []
    raw_headers = [
        re.sub(r"<[^>]+>", "", h).replace("\xa0", "").strip()
        for h in re.findall(r"<th[^>]*>(.*?)</th>", header_row.group(1), re.DOTALL | re.IGNORECASE)
    ]
    # Build index of meaningful (non-empty) headers with their position
    named_cols = [(i, h) for i, h in enumerate(raw_headers) if h]

    # Extract data rows
    data_rows = re.findall(r"<tr>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)[1:]
    results = []
    for row_html in data_rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL | re.IGNORECASE)
        cell_values = []
        for c in cells:
            text = re.sub(r"<[^>]+>", " ", c)
            text = re.sub(r"\s+", " ", text).strip()
            cell_values.append(html_mod.unescape(text))

        row_dict = {}
        n_headers = len(raw_headers)
        n_cells = len(cell_values)

        if n_cells == n_headers:
            # Perfect alignment — use positional mapping
            for idx, name in named_cols:
                row_dict[name] = cell_values[idx]
        elif n_cells < n_headers:
            # Fewer cells than headers — action columns omitted; align from last column back
            offset = n_headers - n_cells
            for idx, name in named_cols:
                ci = idx - offset
                if 0 <= ci < n_cells:
                    row_dict[name] = cell_values[ci]
        else:
            # More cells than headers — take last n_headers cells
            offset = n_cells - n_headers
            for idx, name in named_cols:
                ci = idx + offset
                if ci < n_cells:
                    row_dict[name] = cell_values[ci]

        if row_dict:
            results.append(row_dict)

    return results


# ---------------------------------------------------------------------------
# User lookup
# ---------------------------------------------------------------------------

def parse_user_page(html: str, kerberos: str) -> dict:
    """Parse NDS user page into structured data."""
    # Display name from h1
    h1 = re.search(r"<h1>User:\s*(.*?)</h1>", html, re.IGNORECASE)
    display_name = h1.group(1).strip() if h1 else ""

    info = {
        "kerberos": kerberos,
        "name": display_name,
        "adUsername": parse_itemtable(html, "AD Username"),
        "accountType": parse_itemtable(html, "Account Type"),
        "title": parse_itemtable(html, "Title"),
        "location": parse_itemtable(html, "Location"),
        "division": parse_itemtable(html, "Division"),
        "department": parse_itemtable(html, "Department"),
        "deptCityCode": parse_itemtable(html, "Department &amp; City Code"),
        "email": parse_itemtable(html, "Email Address"),
        "telephone": parse_itemtable(html, "Telephone"),
        "accountDisabled": parse_itemtable(html, "Account Disabled?"),
        "accountLocked": parse_itemtable(html, "Account Locked?"),
    }

    # NDS Assignments table
    info["desktops"] = parse_gridtable_rows(html, "NDS Assignments")

    # Recent NDC clients
    info["ndcClients"] = parse_gridtable_rows(html, "Recent Network Desktop Clients")

    return info


def lookup_user(kerberos: str, cookie: str) -> dict:
    """Fetch and parse user NDS page."""
    url = f"{BASE_URL}/Users/Display/{kerberos}?domain=FIRMWIDE"
    html = fetch_page(url, cookie)
    return parse_user_page(html, kerberos)


# ---------------------------------------------------------------------------
# Desktop lookup
# ---------------------------------------------------------------------------

def parse_desktop_page(html: str, nds: str) -> dict:
    """Parse NDS desktop details page into structured data."""
    info = {
        "nds": nds,
        "fqdn": parse_itemtable(html, "Name"),
        "protocol": parse_itemtable(html, "Protocol"),
        "pool": parse_itemtable(html, "Pool"),
        "caliber": parse_itemtable(html, "Caliber"),
        "datacenter": parse_itemtable(html, "Datacenter"),
        "availableForProvisioning": parse_itemtable(html, "Available for Provisioning?"),
        "failedPendingRebuild": parse_itemtable(html, "Failed &amp; Pending Rebuild?"),
        "osVersion": parse_itemtable(html, "OS Version"),
        "deploymentPhase": parse_itemtable(html, "Deployment Phase"),
        "processors": parse_itemtable(html, "Processors"),
        "memory": parse_itemtable(html, "Memory"),
        "disk": parse_itemtable(html, "Disk"),
        "hypervisor": parse_itemtable(html, "Hypervisor"),
        "hardware": parse_itemtable(html, "Hardware"),
        "datacenterLocation": parse_itemtable(html, "Datacenter Location"),
        "buildDate": parse_itemtable(html, "Build Date"),
        "lastCheckin": parse_itemtable(html, "Last Iridium Check-In"),
        "lastIP": parse_itemtable(html, "Last IP Address"),
    }

    # Mapped users table
    info["mappedUsers"] = parse_gridtable_rows(html, "Mapped Users")

    return info


def lookup_desktop(nds: str, cookie: str) -> dict:
    """Fetch and parse desktop NDS page."""
    url = f"{BASE_URL}/Desktops/Display/{nds}"
    html = fetch_page(url, cookie)
    return parse_desktop_page(html, nds)


# ---------------------------------------------------------------------------
# Dialtone history
# ---------------------------------------------------------------------------

def parse_dialtone_table(html: str) -> list[dict]:
    """Parse the dialtone history table (no h2, uses itemtable class)."""
    # Headers: Scanned On, Health Check, Status
    rows = re.findall(r"<tr>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    results = []
    for row_html in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL | re.IGNORECASE)
        if len(cells) < 3:
            continue
        scanned = re.sub(r"<[^>]+>", "", cells[0]).strip()
        check = re.sub(r"<[^>]+>", "", cells[1]).strip()
        status = re.sub(r"<[^>]+>", "", cells[2]).strip()
        results.append({
            "scannedOn": scanned,
            "healthCheck": check,
            "status": status,
        })
    return results


def lookup_dialtone(nds: str, cookie: str, last: int = 0) -> dict:
    """Fetch and parse dialtone history for an NDS desktop."""
    url = f"{BASE_URL}/Desktops/DialtoneHistory/{nds}"
    html = fetch_page(url, cookie)
    rows = parse_dialtone_table(html)
    if last > 0:
        rows = rows[:last]
    return {"nds": nds, "history": rows}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_user(info: dict):
    """Print user info in a human-readable format."""
    print(f"User: {info['name']}")
    print(f"  Kerberos:   {info['kerberos']}")
    print(f"  Title:      {info['title']}")
    print(f"  Location:   {info['location']}")
    print(f"  Division:   {info['division']}")
    print(f"  Department: {info['department']}")
    print(f"  Email:      {info['email']}")
    print(f"  Telephone:  {info['telephone']}")
    print()

    desktops = info.get("desktops", [])
    if desktops:
        print("NDS Assignments:")
        print(f"  {'Desktop':<16} {'Datacenter':<12} {'Pool':<12} {'Caliber':<20} {'Disabled?':<10}")
        print("  " + "-" * 70)
        for d in desktops:
            print(
                f"  {d.get('Desktop',''):<16} "
                f"{d.get('Datacenter',''):<12} "
                f"{d.get('Pool',''):<12} "
                f"{d.get('Caliber',''):<20} "
                f"{d.get('Disabled?',''):<10}"
            )
        print()

    ndcs = info.get("ndcClients", [])
    if ndcs:
        print("Recent NDC Clients:")
        print(f"  {'Hostname':<16} {'Monitor Sig':<16} {'Last Check-In':<24}")
        print("  " + "-" * 56)
        for n in ndcs:
            print(
                f"  {n.get('NDC Hostname',''):<16} "
                f"{n.get('Monitor Signature',''):<16} "
                f"{n.get('Last Check-In',''):<24}"
            )


def print_desktop(info: dict):
    """Print desktop info in a human-readable format."""
    print(f"Desktop: {info['nds']}")
    print(f"  FQDN:           {info['fqdn']}")
    print(f"  OS:             {info['osVersion']}")
    print(f"  Processors:     {info['processors']}")
    print(f"  Memory:         {info['memory']}")
    print(f"  Disk:           {info['disk']}")
    print(f"  Hypervisor:     {info['hypervisor']}")
    print(f"  Hardware:       {info['hardware']}")
    print(f"  DC Location:    {info['datacenterLocation']}")
    print(f"  Last IP:        {info['lastIP']}")
    print(f"  Build Date:     {info['buildDate']}")
    print(f"  Last Check-In:  {info['lastCheckin']}")
    print(f"  Protocol:       {info['protocol']}")
    print(f"  Pool:           {info['pool']}")
    print(f"  Caliber:        {info['caliber']}")
    print()

    users = info.get("mappedUsers", [])
    if users:
        print("Mapped Users:")
        print(f"  {'Username':<24} {'Name':<36} {'Disabled?':<10} {'Expires':<10}")
        print("  " + "-" * 80)
        for u in users:
            print(
                f"  {u.get('Username',''):<24} "
                f"{u.get('Name',''):<36} "
                f"{u.get('Disabled?',''):<10} "
                f"{u.get('Expires',''):<10}"
            )


def save_json(data, filename: str):
    """Save JSON output to workspace/tmp/."""
    os.makedirs(WORKSPACE_TMP, exist_ok=True)
    path = os.path.join(WORKSPACE_TMP, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nJSON saved to: {path}", file=sys.stderr)


def print_dialtone(info: dict):
    """Print dialtone history in a human-readable format."""
    print(f"Dialtone History: {info['nds']}")
    rows = info.get("history", [])
    if not rows:
        print("  No dialtone history found.")
        return
    print(f"  {'Scanned On':<24} {'Health Check':<20} {'Status':<10}")
    print("  " + "-" * 54)
    for r in rows:
        print(
            f"  {r.get('scannedOn',''):<24} "
            f"{r.get('healthCheck',''):<20} "
            f"{r.get('status',''):<10}"
        )


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
    _apply_args_file(["command", "targets"])
    parser = argparse.ArgumentParser(description="Query NDS Infrastructure Services")
    parser.add_argument("command", choices=["user", "desktop", "dialtone"],
                        help="'user' for desktop assignments, 'desktop' for machine details, 'dialtone' for health history")
    parser.add_argument("targets", nargs="+",
                        help="One or more kerberos IDs (user) or NDS names (desktop/dialtone)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--last", type=int, default=0,
                        help="For dialtone: limit to last N scan entries")
    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")
    args = parser.parse_args()
    _setup_out_file(args.out_file)

    cookie = get_gssso_cookie()
    all_results = []

    for target in args.targets:
        try:
            if args.command == "user":
                info = lookup_user(target, cookie)
            elif args.command == "desktop":
                info = lookup_desktop(target, cookie)
            else:
                info = lookup_dialtone(target, cookie, last=args.last)
        except RuntimeError as e:
            info = {("kerberos" if args.command == "user" else "nds"): target, "error": str(e)}
        all_results.append(info)

    # Single target: unwrap from list
    output = all_results[0] if len(all_results) == 1 else all_results

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        for info in all_results:
            if "error" in info:
                key = info.get("kerberos") or info.get("nds", "?")
                print(f"ERROR: {key} → {info['error']}")
            elif args.command == "user":
                print_user(info)
            elif args.command == "desktop":
                print_desktop(info)
            else:
                print_dialtone(info)
            if len(all_results) > 1:
                print()

    # Save JSON
    if len(args.targets) == 1:
        fname = f"nds-{args.command}-{args.targets[0]}.json"
    else:
        fname = f"nds-{args.command}-batch.json"
    save_json(output, fname)


if __name__ == "__main__":
    main()
