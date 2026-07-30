"""Query Prime security details from GS2ClassificationView.

Usage:
    python prime.py 1000294460                          # Single PrimeId lookup
    python prime.py 1000294460 1000123456                # Multiple PrimeIds
    python prime.py --sector Stocks PETR4                # Sector-specific lookup
    python prime.py --json 1000294460                    # JSON output
    python prime.py --fields Ticker,ISIN,Currency 1000294460  # Select fields
"""

import argparse
import atexit
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

SSO_URL = "https://authn.web.gs.com/desktopsso/Login"
PRIME_URL = (
    "https://strategy.eq.gs.com/ssps/ProdSource/GS2ClassificationView"
    "?Sector={sector}&Select={select}"
)

WORKSPACE_TMP = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "workspace", "tmp"
)

# Sectors that expect numeric PrimeId vs free-text YAQL selectors
NUMERIC_SECTORS = {"PrimeId"}
# Hint text for common sectors
SECTOR_HINTS = {
    "PrimeId": "numeric PrimeId (e.g. 1000294460)",
    "Stocks": "ticker symbol (e.g. PETR4, VALE3)",
    "StockOptions": "option identifier",
    "StockIndices": "index name (e.g. IBOV)",
    "Futures": "futures contract identifier",
    "FuturesOptions": "futures option identifier",
    "Currencies": "currency pair (e.g. USDBRL)",
}


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


def fetch_page(select: str, sector: str, cookie: str) -> str:
    """Fetch the GS2ClassificationView HTML page."""
    url = PRIME_URL.format(sector=sector, select=select)
    ctx = ssl.create_default_context()

    req = urllib.request.Request(url, headers={
        "Cookie": f"GSSSO={cookie}",
        "Accept": "text/html",
    })
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _find_table_block(html: str, summary_attr: str, title_text: str) -> str | None:
    """Find a table block by summary attribute, falling back to title text match."""
    # Primary: match by summary attribute
    m = re.search(
        rf'summary="{re.escape(summary_attr)}"(.*?)</table>',
        html, re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # Fallback: find title row containing the text, then grab the next sibling table
    title_pat = re.escape(title_text)
    # Title is in a preceding table; the data table immediately follows
    m = re.search(
        rf'class=tableTitle[^>]*>{title_pat}</td>.*?</table>\s*<table[^>]*>(.*?)</table>',
        html, re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1)

    return None


def _clean_html_value(raw: str) -> str:
    """Strip HTML tags and entities from a cell value."""
    val = raw.replace('<BR>', '\n').replace('<br>', '\n')
    val = re.sub(r'<[^>]+>', '', val).strip()
    val = val.replace('&nbsp;', '').replace('&lt;null&gt;', '').strip()
    return val


def _parse_cell_value(val: str):
    """Parse a cleaned cell value, converting array patterns to lists."""
    if re.match(r'\[0\]\s*-\s*', val):
        items = re.findall(r'\[\d+\]\s*-\s*(.+)', val)
        return [i.strip() for i in items]
    return val


def parse_builder(html: str) -> str:
    """Extract the Builder value."""
    block = _find_table_block(html, "table1", "Builder")
    if not block:
        return ""
    m = re.search(r'<td[^>]*>([^<]+)</td>', block, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def parse_classification_map(html: str) -> dict:
    """Extract the classification map row (headers + values)."""
    block = _find_table_block(html, "table3", "Row that matched in usf_classification_map")
    if not block:
        return {}

    headers = re.findall(r'<th[^>]*>([^<]+)</th>', block, re.IGNORECASE)
    cells = re.findall(r'<td[^>]*>(.*?)</td>', block, re.DOTALL | re.IGNORECASE)

    cleaned = [_clean_html_value(c) for c in cells]

    result = {}
    for i, h in enumerate(headers):
        if i < len(cleaned):
            result[h.strip()] = cleaned[i]
    return result


def parse_data_frame(html: str) -> dict:
    """Extract all Slot Name / Data Value pairs from the Prime data frame."""
    block = _find_table_block(html, "table7", "Data Frame from Prime Security")
    if not block:
        return {}

    rows = re.findall(
        r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>',
        block, re.DOTALL | re.IGNORECASE,
    )

    result = {}
    for name_raw, val_raw in rows:
        name = re.sub(r'<[^>]+>', '', name_raw).strip()
        if not name:
            continue
        val = _clean_html_value(val_raw)
        result[name] = _parse_cell_value(val)

    return result


def validate_selector(select: str, sector: str) -> None:
    """Warn if selector format looks wrong for the given sector."""
    if sector in NUMERIC_SECTORS and not select.isdigit():
        hint = SECTOR_HINTS.get(sector, "numeric ID")
        print(
            f"WARNING: Sector '{sector}' expects a {hint}, "
            f"but got '{select}'. Results may be empty.",
            file=sys.stderr,
        )
    elif sector not in NUMERIC_SECTORS and select.isdigit():
        hint = SECTOR_HINTS.get(sector, "non-numeric identifier")
        print(
            f"HINT: Sector '{sector}' typically expects a {hint}. "
            f"Got numeric '{select}' — if this is a PrimeId, use --sector PrimeId.",
            file=sys.stderr,
        )


def parse_disambiguation(html: str) -> list[dict] | None:
    """Detect and parse a disambiguation page (multiple product matches).

    Returns a list of {primeId, description, cusip} dicts, or None if not a
    disambiguation page.
    """
    if "Select a product" not in html:
        return None

    block = _find_table_block(html, "table1", "Select a product")
    if not block:
        return None

    rows = re.findall(
        r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>",
        block, re.DOTALL | re.IGNORECASE,
    )
    if not rows:
        return None

    results = []
    for pid_raw, desc_raw, cusip_raw in rows:
        # Extract PrimeId from link href or text
        pid_match = re.search(r'Select=(\d+)', pid_raw)
        pid = pid_match.group(1) if pid_match else _clean_html_value(pid_raw)
        results.append({
            "primeId": pid,
            "description": _clean_html_value(desc_raw),
            "cusip": _clean_html_value(cusip_raw),
        })
    return results


def query_prime(select: str, sector: str, cookie: str, follow: bool = True) -> dict | list[dict]:
    """Fetch and parse a single Prime query.

    If the result is a disambiguation page and follow=True, auto-follows all
    PrimeId links and returns a list of full results.
    """
    validate_selector(select, sector)

    try:
        html = fetch_page(select, sector, cookie)
    except urllib.error.HTTPError as e:
        return {"select": select, "sector": sector, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"select": select, "sector": sector, "error": str(e)}

    # Check for disambiguation page
    candidates = parse_disambiguation(html)
    if candidates is not None:
        if not follow:
            return {
                "select": select,
                "sector": sector,
                "disambiguation": candidates,
            }
        # Auto-follow each PrimeId link
        print(
            f"  {select} → {len(candidates)} matches, following each PrimeId...",
            file=sys.stderr,
        )
        followed = []
        for c in candidates:
            r = query_prime(c["primeId"], "PrimeId", cookie, follow=False)
            followed.append(r)
        return {
            "select": select,
            "sector": sector,
            "disambiguation": candidates,
            "resolved": followed,
        }

    builder = parse_builder(html)
    classification = parse_classification_map(html)
    data_frame = parse_data_frame(html)

    return {
        "select": select,
        "sector": sector,
        "builder": builder,
        "classification": classification,
        "dataFrame": data_frame,
    }


def print_summary(result: dict, fields: list[str] | None = None):
    """Print a human-readable summary of a Prime query result."""
    if "error" in result:
        print(f"ERROR [{result['sector']}:{result['select']}]: {result['error']}")
        return

    # Disambiguation result with resolved sub-results
    if "disambiguation" in result:
        disamb = result["disambiguation"]
        resolved = result.get("resolved", [])
        if resolved:
            # Print each resolved sub-result
            print(f"=== {result['sector']}:{result['select']} → {len(resolved)} resolved ===")
            for r in resolved:
                print_summary(r, fields)
            return
        else:
            # List-only (--no-follow)
            print(f"=== {result['sector']}:{result['select']} → {len(disamb)} matches ===")
            for c in disamb:
                print(f"  PrimeId={c['primeId']:>12}  {c['description']:<50}  CUSIP={c['cusip']}")
            print()
            return

    df = result.get("dataFrame", {})
    print(f"=== {result['sector']}:{result['select']} ===")
    print(f"  Builder: {result.get('builder', 'N/A')}")

    if fields:
        for f in fields:
            val = df.get(f, "N/A")
            if isinstance(val, list):
                val = ", ".join(val)
            print(f"  {f}: {val}")
    else:
        # Default summary: key identifiers + classification
        key_fields = [
            "Ticker", "ISIN", "CUSIP", "GSSymbol", "GSNumber",
            "PrimaryExchangeRIC", "PrimaryExchangeBID",
            "Currency", "Country", "instrumentType", "InstrumentSubType",
            "MarketType", "IssuerLegalName", "IssueStatus",
            "IssueStatusDescription", "settlementCurrency",
            "TradeToSettleDelay", "PrimeID",
        ]
        for f in key_fields:
            val = df.get(f)
            if val:
                if isinstance(val, list):
                    val = ", ".join(val)
                print(f"  {f}: {val}")

    cls = result.get("classification", {})
    if cls:
        print(f"  Classification: {cls}")

    print()


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
    _apply_args_file(["selectors"])
    parser = argparse.ArgumentParser(
        description="Query Prime security details from GS2ClassificationView."
    )
    parser.add_argument("selectors", nargs="*", default=[], help="PrimeId(s) or YAQL selector(s)")
    parser.add_argument(
        "--sector", type=str, default="PrimeId",
        help="Sector to query (default: PrimeId). E.g. Stocks, StockOptions, Futures",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--fields", type=str, default=None,
        help="Comma-separated list of fields to display (e.g. Ticker,ISIN,Currency)",
    )
    parser.add_argument(
        "--no-follow", action="store_true",
        help="Don't auto-follow disambiguation links; just list matches",
    )
    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")
    args = parser.parse_args()
    if not args.selectors:
        parser.error("selectors required (via CLI or --args-file)")
    _setup_out_file(args.out_file)

    field_list = [f.strip() for f in args.fields.split(",")] if args.fields else None
    follow = not args.no_follow

    cookie = get_gssso_cookie()

    results = []
    for sel in args.selectors:
        result = query_prime(sel, args.sector, cookie, follow=follow)
        results.append(result)

    # Save JSON
    os.makedirs(WORKSPACE_TMP, exist_ok=True)
    out_path = os.path.join(WORKSPACE_TMP, "prime-query-results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print_summary(r, field_list)

    print(f"JSON saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
