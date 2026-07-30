"""TMD (Technology@MyDesk) ticket management CLI.

Actions:
  list                  List TMD items by kerberos
  detail                Get full order detail by order ID
  search                Search TMD catalog by keyword
  submit-firewall-delete Submit a Delete Firewall service request
"""
import argparse
import atexit
import io
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import ssl
import http.cookiejar

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_gssso_session():
    """Authenticate via Kerberos/SPNEGO and return GSSSO cookie value.

    Tries requests_negotiate_sspi first, falls back to PowerShell subprocess.
    """
    # Attempt 1: Python requests with SSPI
    try:
        from requests_negotiate_sspi import HttpNegotiateAuth
        import requests
        s = requests.Session()
        s.get("https://authn.web.gs.com/desktopsso/Login",
              auth=HttpNegotiateAuth(), timeout=15)
        for c in s.cookies:
            if c.name == "GSSSO":
                return c.value
    except Exception:
        pass

    # Attempt 2: PowerShell with UseDefaultCredentials (reliable Kerberos)
    try:
        import subprocess
        ps_script = (
            "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;"
            "$r = Invoke-WebRequest -Uri 'https://authn.web.gs.com/desktopsso/Login'"
            " -UseDefaultCredentials -SessionVariable s -UseBasicParsing;"
            "$s.Cookies.GetCookies('https://authn.web.gs.com') | "
            "Where-Object { $_.Name -eq 'GSSSO' } | "
            "Select-Object -ExpandProperty Value"
        )
        result = run_cmd(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        cookie = result.stdout.strip()
        if cookie:
            return cookie
    except Exception:
        pass

    print("ERROR: Could not obtain GSSSO cookie. Ensure Kerberos ticket is valid.",
          file=sys.stderr)
    sys.exit(1)


def _make_request(url, method="GET", body=None, gssso=None):
    """Make an HTTP request with GSSSO auth, return (status, body_str)."""
    ctx = ssl.create_default_context()

    headers = {
        "Accept": "application/json",
        "Cookie": f"GSSSO={gssso}",
    }
    if body is not None:
        headers["Content-Type"] = "application/json;charset=UTF-8"
        data = body.encode("utf-8") if isinstance(body, str) else body
    else:
        data = None

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        return e.code, err_body


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

TMD_BASE = "https://tmd.web.gs.com"
TMD_V1 = f"{TMD_BASE}/api/rest/v1"
SPINE_BASE = "https://spine.ose.url.gs.com/spine-engine-service-web/rest"


def action_list(args, gssso):
    """List TMD items for a kerberos user."""
    params = {"creatorKerberos": args.kerberos}
    if args.status:
        params["status"] = args.status
    if args.exclude_status:
        params["excludeStatus"] = args.exclude_status
    if args.days:
        params["createdDaysAgo"] = str(args.days)
    if args.order_id:
        params["orderId"] = args.order_id
    if args.service_code:
        params["catalogServiceCode"] = args.service_code
    if args.recipient:
        params["recipientKerberos"] = args.recipient
    params["sortBy"] = "createdOn"
    params["sortOrder"] = "DESC"

    qs = urllib.parse.urlencode(params)
    url = f"{TMD_V1}/items?{qs}"

    status, body = _make_request(url, gssso=gssso)
    if status != 200:
        print(f"ERROR: HTTP {status}", file=sys.stderr)
        print(body, file=sys.stderr)
        sys.exit(1)

    data = json.loads(body)
    items = data.get("data", [])

    if args.format == "json":
        print(json.dumps(data, indent=2))
        return

    # Table output
    print(f"Found {len(items)} items for {args.kerberos}")
    print(f"{'OrderID':>10} {'ItemID':>10} {'Status':<25} {'Name'}")
    print("-" * 80)
    for item in items:
        print(f"{item.get('orderId', ''):>10} {item.get('id', ''):>10} "
              f"{item.get('status', ''):<25} {item.get('name', '')[:60]}")


def action_detail(args, gssso):
    """Get detailed info for a TMD order."""
    url = f"{TMD_BASE}/rest/orderDetail/{args.order_id}"
    status, body = _make_request(url, gssso=gssso)
    if status != 200:
        print(f"ERROR: HTTP {status}", file=sys.stderr)
        print(body, file=sys.stderr)
        sys.exit(1)

    data = json.loads(body)

    if args.format == "json":
        print(json.dumps(data, indent=2))
        return

    # Table output
    creator = data.get("creatorUser", {})
    print(f"Order ID:    {data.get('id')}")
    print(f"Status:      {data.get('status')}")
    print(f"Creator:     {creator.get('displayName')} ({creator.get('kerberos')})")
    print(f"Department:  {creator.get('gsHrDeptName')}")
    print(f"Location:    {creator.get('l')}")
    print(f"Created:     {_format_epoch(data.get('createdOn'))}")
    print(f"Updated:     {_format_epoch(data.get('lastUpdatedOn'))}")
    print(f"Watchers:    {', '.join(data.get('watchers', [])) or 'none'}")

    items = data.get("items", [])
    print(f"\nItems ({len(items)}):")
    for item in items:
        print(f"  [{item.get('id')}] {item.get('name')} — {item.get('status')}")
        # Extract form data from attributes
        for attr in item.get("attributes", []):
            if attr["key"] == "EP_FORM_ENGINE_REQUEST_0":
                try:
                    form_data = json.loads(attr["value"])
                    _print_form_data(form_data)
                except json.JSONDecodeError:
                    pass


def action_search(args, gssso):
    """Search TMD catalog by keyword."""
    keyword = urllib.parse.quote(args.keyword, safe="")
    if args.filter_category and args.filter_value:
        cat = urllib.parse.quote(args.filter_category, safe="")
        val = urllib.parse.quote(args.filter_value, safe="")
        url = f"{TMD_BASE}/rest/tmdsearch/{keyword}/{cat}/{val}"
    else:
        url = f"{TMD_BASE}/rest/tmdsearch/{keyword}"

    status, body = _make_request(url, gssso=gssso)
    if status != 200:
        print(f"ERROR: HTTP {status}", file=sys.stderr)
        print(body, file=sys.stderr)
        sys.exit(1)

    data = json.loads(body)
    results = data.get("result", [])

    if args.format == "json":
        print(json.dumps(data, indent=2))
        return

    # Table output
    print(f"Found {data.get('resultCount', len(results))} results for '{args.keyword}'")
    print(f"{'ID':>12} {'Product':<30} {'Asset Name'}")
    print("-" * 80)
    for r in results:
        prod = r.get("product", {})
        prod_name = prod.get("productName", "")
        asset = r.get("assetName", "")
        sid = r.get("secondaryId", "")
        print(f"{sid:>12} {prod_name:<30} {asset[:50]}")


def action_submit_firewall_delete(args, gssso):
    """Submit a Delete Firewall service request."""
    payload = {
        "STAR_TITLE": args.title,
        "STAR_DESCRIPTION": args.description,
        "region": [args.region],
        "priority": args.priority,
        "ipToDelete": args.ip,
        "applicationName": args.app_name or "",
        "groupName": args.group_name or "",
        "projectScope": args.project,
        "emergencyRequest": args.emergency,
        "watchers": args.watchers.split(",") if args.watchers else [],
        "itemName": "Delete Firewall",
        "serviceCode": "1a3af2ca-d402-42a4-9813-936975c1e179",
        "productCode": "f48e30c2-ce69-412e-9067-0ea1e04a1152",
        "formInfo": {
            "formId": "com.gs.ti.ose.spine.network.firewallDeleteIP",
            "formVersion": 1,
            "submitterKerberos": args.kerberos,
            "submissionEndPoint": {
                "rootUrl": "https://spine.ose.url.gs.com",
                "resourcePath": "/spine-engine-service-web/rest/tmdGatewayService/createTMDOrder",
            },
            "workflowConfig": {
                "processId": "simple-storage-workflow",
            },
        },
    }

    # Add emergency fields if applicable
    if args.emergency == "Yes":
        if args.emergency_driver:
            payload["emergencyDriver"] = args.emergency_driver
        if args.business_impact:
            payload["businessImpact"] = args.business_impact
        if args.impact_comment:
            payload["addImpactOfImplementingThroughNormalSlt"] = args.impact_comment

    # Add project fields if applicable
    if args.project == "yes":
        if args.jira_link:
            payload["jiraLink"] = args.jira_link

    url = f"{SPINE_BASE}/tmdGatewayService/createTMDOrder"
    body_json = json.dumps(payload)

    if args.dry_run:
        print("DRY RUN — would submit:")
        print(json.dumps(payload, indent=2))
        return

    status, body = _make_request(url, method="POST", body=body_json, gssso=gssso)
    if status != 200:
        print(f"ERROR: HTTP {status}", file=sys.stderr)
        print(body, file=sys.stderr)
        sys.exit(1)

    result = json.loads(body)
    order_id = result.get("uniqueId", "unknown")
    print(f"TMD Order created: {result.get('message')}")
    print(f"Order ID: {order_id}")
    print(f"View at: https://ui.tmd.site.gs.com/#/orderDetail/{order_id}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_epoch(epoch_ms):
    """Format epoch millis to human-readable string."""
    if not epoch_ms:
        return "N/A"
    import datetime
    dt = datetime.datetime.fromtimestamp(epoch_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _print_form_data(form_data):
    """Pretty-print form submission data."""
    skip_keys = {"formInfo", "serviceCode", "productCode", "itemName"}
    for key, value in form_data.items():
        if key in skip_keys:
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        print(f"    {key}: {value}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _apply_args_file(positional_keys=None, parent_keys=None):
    """If --args-file in argv, load JSON and rebuild argv as CLI flags."""
    if "--args-file" not in sys.argv:
        return
    idx = sys.argv.index("--args-file")
    path = sys.argv[idx + 1]
    with open(path, "r", encoding="utf-8") as f:
        af = json.load(f)
    argv = [sys.argv[0]]
    # Parent-level flags must appear before subcommand positional
    for pk in (parent_keys or []):
        if pk in af:
            v = af.pop(pk)
            flag = f"--{pk.replace('_', '-')}"
            if isinstance(v, bool):
                if v:
                    argv.append(flag)
            elif v is not None:
                argv.extend([flag, str(v)])
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
    _apply_args_file(["action"], parent_keys=["out_file"])
    import warnings
    warnings.filterwarnings("ignore")

    parser = argparse.ArgumentParser(description="TMD ticket management")
    sub = parser.add_subparsers(dest="action", required=True)

    # list
    p_list = sub.add_parser("list", help="List TMD items by kerberos")
    p_list.add_argument("--kerberos", required=True, help="Kerberos ID")
    p_list.add_argument("--status", help="Filter by status (Open, Completed, etc.)")
    p_list.add_argument("--exclude-status", help="Exclude items with this status")
    p_list.add_argument("--days", type=int, help="Created within N days")
    p_list.add_argument("--order-id", help="Filter by order ID")
    p_list.add_argument("--service-code", help="Filter by catalog service code")
    p_list.add_argument("--recipient", help="Filter by recipient kerberos")
    p_list.add_argument("--format", choices=["table", "json"], default="table",
                         help="Output format (default: table)")

    # detail
    p_detail = sub.add_parser("detail", help="Get order detail")
    p_detail.add_argument("--order-id", required=True, help="TMD order ID")
    p_detail.add_argument("--format", choices=["table", "json"], default="table",
                         help="Output format (default: table)")

    # search
    p_search = sub.add_parser("search", help="Search TMD catalog by keyword")
    p_search.add_argument("--keyword", required=True, help="Search keyword")
    p_search.add_argument("--filter-category", help="Filter category (e.g. creatorKerberos)")
    p_search.add_argument("--filter-value", help="Filter value for the category")
    p_search.add_argument("--format", choices=["table", "json"], default="table",
                          help="Output format (default: table)")

    # submit-firewall-delete
    p_fw = sub.add_parser("submit-firewall-delete", help="Submit Delete Firewall request")
    p_fw.add_argument("--kerberos", required=True, help="Submitter kerberos")
    p_fw.add_argument("--title", required=True, help="Order title")
    p_fw.add_argument("--description", required=True, help="Brief description")
    p_fw.add_argument("--region", required=True,
                       choices=["Asia", "Americas", "EMEA", "Bangalore", "Global"])
    p_fw.add_argument("--priority", required=True,
                       choices=["Low", "Medium", "High", "Critical"])
    p_fw.add_argument("--ip", required=True, help="IP address to delete")
    p_fw.add_argument("--app-name", help="Application name (optional)")
    p_fw.add_argument("--group-name", help="Firewall group name (optional)")
    p_fw.add_argument("--project", default="no", choices=["yes", "no"],
                       help="Is this a project? (default: no)")
    p_fw.add_argument("--emergency", default="No", choices=["Yes", "No"],
                       help="Emergency request? (default: No)")
    p_fw.add_argument("--watchers", help="Comma-separated kerberos IDs")
    p_fw.add_argument("--jira-link", help="Project Jira link (required if --project=yes)")
    p_fw.add_argument("--emergency-driver",
                       choices=["Planning Issue", "Incident Remediation",
                                "Business Client Driven", "Tech Client Driven",
                                "Audit/Risk Remediation", "Vulnerability Management"],
                       help="Emergency driver (required if --emergency=Yes)")
    p_fw.add_argument("--business-impact",
                       choices=["Reputation Impact", "Financial Impact",
                                "UAT/Production Release Impact", "Client Impact",
                                "Infrastructure Impact"],
                       help="Business impact (required if --emergency=Yes)")
    p_fw.add_argument("--impact-comment", help="Impact comment (required if --emergency=Yes)")
    p_fw.add_argument("--dry-run", action="store_true",
                       help="Print payload without submitting")

    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")
    args = parser.parse_args()
    _setup_out_file(args.out_file)

    # Authenticate
    gssso = get_gssso_session()

    # Dispatch
    if args.action == "list":
        action_list(args, gssso)
    elif args.action == "detail":
        action_detail(args, gssso)
    elif args.action == "search":
        action_search(args, gssso)
    elif args.action == "submit-firewall-delete":
        action_submit_firewall_delete(args, gssso)


if __name__ == "__main__":
    main()
