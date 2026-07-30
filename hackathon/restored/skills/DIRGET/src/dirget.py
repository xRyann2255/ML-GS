"""Look up employee details from the GS directory by kerberos ID or name.

Usage:
    python dirget.py silfel                            # Single kerberos lookup
    python dirget.py silfel heldtp tadesa               # Multiple lookups
    python dirget.py --json silfel heldtp               # JSON output
    python dirget.py --country brazil silfel heldtp      # Filter by country
    python dirget.py --search "andre souza"              # Search by name
    python dirget.py --search "Guo, Yifei" --resolve     # Search + full details
    python dirget.py --search "souza" --resolve --json   # Search + details as JSON
"""

import argparse
import atexit
import io
import json
import os
import re
import subprocess
import sys

import urllib.parse
import urllib.request
import urllib.error
import ssl

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402

SSO_URL = "https://authn.web.gs.com/desktopsso/Login"
DIRGET_URL = "https://www.epssp.site.gs.com/ssps/ProdSource/Dirget?K={kerberos}"
DIRGET_SEARCH_URL = (
    "https://www.epssp.site.gs.com/ssps/ProdSource/Dirget"
    "?ajax=true&action=HeaderSearch&term={term}"
)

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
        print("Ensure you have a valid Kerberos ticket.", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr[:500], file=sys.stderr)
        sys.exit(1)

    return cookie


def search_by_name(term: str, cookie: str) -> list[dict]:
    """Search the directory by name via EPSSP HeaderSearch.

    Returns a list of matches, each with keys: display, kerberos.
    The API returns JSON like ["LastName, FirstName [Division] {kerberos}", ...].
    """
    url = DIRGET_SEARCH_URL.format(term=urllib.parse.quote(term))
    ctx = ssl.create_default_context()

    req = urllib.request.Request(url, headers={
        "Cookie": f"GSSSO={cookie}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    entries = json.loads(raw)
    results = []
    for entry in entries:
        m = re.search(r"\{(\w+)\}\s*$", entry)
        kerb = m.group(1) if m else ""
        results.append({"display": entry.strip(), "kerberos": kerb})
    return results


def fetch_dirget(kerberos: str, cookie: str) -> str:
    """Fetch the DirGet HTML page for a kerberos ID."""
    url = DIRGET_URL.format(kerberos=kerberos)
    ctx = ssl.create_default_context()

    req = urllib.request.Request(url, headers={
        "Cookie": f"GSSSO={cookie}",
        "Accept": "text/html",
    })
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_field(html: str, label: str) -> str:
    """Extract a DT/DD field value from DirGet HTML.

    Structure: <DT>Label</DT> <DD> <SPAN class='lead'> [<A>]text[</A>] </SPAN> </DD>
    """
    # Primary: find <DT>Label</DT> then grab text from the next <SPAN class='lead'> > optional <A>
    pattern = (
        rf"<DT>{re.escape(label)}</DT>"
        r"\s*<DD>\s*<SPAN[^>]*>\s*(?:<[Aa][^>]*>)?\s*([^<]+)"
    )
    m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def parse_location(location_str: str) -> dict:
    """Parse location string like 'Sao Paulo, 700M/017, 314A02 (Brazil, Americas)'."""
    result = {"city": "", "country": "", "region": ""}
    if not location_str:
        return result

    # Extract parenthetical (Country, Region)
    paren = re.search(r"\(([^,]+),\s*([^)]+)\)", location_str)
    if paren:
        result["country"] = paren.group(1).strip()
        result["region"] = paren.group(2).strip()

    # City is the first comma-separated token
    parts = location_str.split(",")
    if parts:
        result["city"] = parts[0].strip()

    return result


def parse_employee(html: str, kerberos: str) -> dict:
    """Parse all relevant fields from a DirGet HTML response."""
    # Name from title tag
    name = ""
    title_match = re.search(r"<TITLE>DirGet:\s*([^<]+)</TITLE>", html, re.IGNORECASE)
    if title_match:
        name = title_match.group(1).strip()

    location = parse_field(html, "Location")
    loc_parts = parse_location(location)

    # GS City Code
    city_code = parse_field(html, "GS City Code")

    # Department
    department = parse_field(html, "Department")

    # Title/Grade
    grade = parse_field(html, "Title")
    if not grade:
        grade = parse_field(html, "Grade")

    # Division - from the title tooltip or Company area rather than name
    division = parse_field(html, "Division")

    # Business Unit
    business_unit = parse_field(html, "Business Unit")

    # Manager
    manager = parse_field(html, "Manager")

    # Kerberos confirmation
    kerb_field = parse_field(html, "Kerberos")
    if not kerb_field:
        kerb_field = kerberos

    return {
        "kerberos": kerb_field or kerberos,
        "name": name,
        "title": grade,
        "location": location,
        "city": loc_parts["city"],
        "country": loc_parts["country"],
        "region": loc_parts["region"],
        "cityCode": city_code,
        "department": department,
        "businessUnit": business_unit,
        "division": division,
        "manager": manager,
    }


def lookup(kerberos_ids: list[str], cookie: str) -> list[dict]:
    """Look up multiple kerberos IDs and return parsed results."""
    results = []
    for kerb in kerberos_ids:
        try:
            html = fetch_dirget(kerb, cookie)
            info = parse_employee(html, kerb)
            results.append(info)
        except urllib.error.HTTPError as e:
            print(f"ERROR: {kerb} → HTTP {e.code}", file=sys.stderr)
            results.append({"kerberos": kerb, "error": f"HTTP {e.code}"})
        except Exception as e:
            print(f"ERROR: {kerb} → {e}", file=sys.stderr)
            results.append({"kerberos": kerb, "error": str(e)})
    return results


def print_table(results: list[dict], country_filter: str = None):
    """Print results as a formatted table."""
    filtered = results
    if country_filter:
        cf = country_filter.lower()
        filtered = [r for r in results if cf in r.get("country", "").lower()]

    if not filtered:
        print("No results match the filter.")
        return

    # Header
    print(f"{'Kerberos':<10} {'Name':<30} {'City':<16} {'Country':<16} {'Department':<30} {'Title':<20}")
    print("-" * 122)
    for r in filtered:
        if "error" in r:
            print(f"{r['kerberos']:<10} ERROR: {r['error']}")
        else:
            print(
                f"{r.get('kerberos',''):<10} "
                f"{r.get('name',''):<30} "
                f"{r.get('city',''):<16} "
                f"{r.get('country',''):<16} "
                f"{r.get('department',''):<30} "
                f"{r.get('title',''):<20}"
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
    _apply_args_file(["kerberos"])
    parser = argparse.ArgumentParser(
        description="Look up employee details from the GS directory by kerberos ID or name."
    )
    parser.add_argument("kerberos", nargs="*", default=[], help="One or more kerberos IDs")
    parser.add_argument("--search", type=str, default=None, metavar="NAME",
                        help="Search by name (e.g. 'Guo, Yifei' or 'andre souza')")
    parser.add_argument("--resolve", action="store_true",
                        help="With --search: also fetch full DirGet details for each match")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--country", type=str, default=None,
        help="Filter results by country (case-insensitive substring match)"
    )
    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")
    args = parser.parse_args()
    if not args.kerberos and not args.search:
        parser.error("Provide kerberos IDs or --search NAME")
    _setup_out_file(args.out_file)

    cookie = get_gssso_cookie()

    # --- Name search mode ---
    if args.search:
        matches = search_by_name(args.search, cookie)
        if not matches:
            print(f"No matches for '{args.search}'.")
            sys.exit(0)

        if args.resolve:
            # Resolve full details for every match that has a kerberos
            kerb_ids = [m["kerberos"] for m in matches if m["kerberos"]]
            results = lookup(kerb_ids, cookie) if kerb_ids else []
        else:
            results = matches

        os.makedirs(WORKSPACE_TMP, exist_ok=True)
        out_path = os.path.join(WORKSPACE_TMP, "dirget-results.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        if args.resolve:
            if args.json:
                if args.country:
                    cf = args.country.lower()
                    results = [r for r in results if cf in r.get("country", "").lower()]
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                print_table(results, args.country)
        else:
            # Just print the search matches
            if args.json:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                print(f"Found {len(results)} match(es) for '{args.search}':")
                print(f"{'#':<4} {'Display':<60} {'Kerberos':<12}")
                print("-" * 76)
                for i, m in enumerate(results, 1):
                    print(f"{i:<4} {m['display']:<60} {m['kerberos']:<12}")

        print(f"\nJSON saved to {out_path}", file=sys.stderr)
        return

    # --- Kerberos lookup mode ---
    results = lookup(args.kerberos, cookie)

    os.makedirs(WORKSPACE_TMP, exist_ok=True)
    out_path = os.path.join(WORKSPACE_TMP, "dirget-results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if args.json:
        if args.country:
            cf = args.country.lower()
            results = [r for r in results if cf in r.get("country", "").lower()]
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_table(results, args.country)

    print(f"\nJSON saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
