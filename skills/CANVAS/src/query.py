"""Query the AppDir 2.0 Sky Gateway API.

Usage (desktop — Canvas backend):
    python query.py did 155218              # Deployment summary
    python query.py did 155218 --full       # Full deployment (configs, resources)
    python query.py did 155218 --hosts      # Host list
    python query.py did 155218 --classify   # Resources with DC/EC + VMShape (resolves beans)
    python query.py did 155218 --sysaccounts # System accounts
    python query.py hierarchy 155218        # Full org chain (BU->SBU->Family->App->DID)
    python query.py beans 12345,67890       # Bean definitions (resource templates)
    python query.py roles                   # Current user's Canvas family roles
    python query.py host-info k8sbm-1497039.k8s.gs.com  # Host details + owning app
    python query.py host-status d176618.ny.corp.gs.com  # Host operational status
    python query.py search-did "Vol Strats"  # Search deployments by name
    python query.py businessunits           # List all BUs

Usage (cloud — Sky Gateway):
    python query.py application name "SecDb"
    python query.py deployment ext 12345
    python query.py host hostname "d176618.ny.corp.gs.com"
    python query.py application deployments 9876 --status ACTIVE
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402

SERVER = "https://prod.gateway.sky.site.gs.com"
BASE = "/skygateway/appdir2sg_prod/v1/appdir/api"
SSO_URL = "https://authn.web.gs.com/desktopsso/Login"
CANVAS_API = "https://api.canvas.site.gs.com:7443/v1"
GSRN = "gsrn.gscloud.apimgmt.publisher.43378.appdir2sg_prod_v1"

# Map of (entity, lookup) -> URL path template
# {0} = the positional value, {1} = second positional (for tagref entity)
ROUTES = {
    ("application", "id"): "/application/{0}",
    ("application", "ext"): "/application/ext/{0}",
    ("application", "name"): "/application/name/{0}",
    ("application", "deployments"): "/application/{0}/deployments",
    ("application", "classifications"): "/application/{0}/classifications",
    ("deployment", "ext"): "/deployment/ext/{0}",
    ("deployment", "name"): "/deployment/name/{0}",
    ("deployment", "hosts"): "/deployment/{0}/hosts",
    ("deployment", "systemaccounts"): "/deployment/{0}/systemAccounts",
    ("deployment", "classifications"): "/deployment/{0}/classifications",
    ("host", "hostname"): "/host/hostname/{0}",
    ("family", "id"): "/family/{0}",
    ("family", "applications"): "/family/{0}/applications",
    ("businessunit", "id"): "/businessUnit/{0}",
    ("businessunit", "subbusinessunits"): "/businessUnit/{0}/subBusinessUnits",
    ("subbusinessunit", "id"): "/subBusinessUnit/{0}",
    ("subbusinessunit", "families"): "/subBusinessUnit/{0}/families",
    ("bcp", "id"): "/bcp/{0}",
    ("systemaccount", "deployment"): "/systemAccount/deploymentId/{0}",
    ("tag", "tag"): "/tag/{0}",
    ("tag", "prefix"): "/tag/tagPrefix/{0}",
    ("tagref", "tag"): "/tagRef/tag/{0}",
    ("tagref", "entity"): "/tagRef/entityType/{0}/entityId/{1}",
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
        print("Ensure you have a valid Kerberos ticket (run 'kinit').", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr[:300], file=sys.stderr)
        sys.exit(1)

    return cookie


def fetch(cookie: str, path: str, status: str = None) -> dict:
    """Fetch a JSON response from the AppDir API.

    Tries the direct Sky Gateway URL first. If DNS doesn't resolve
    (desktop environment), returns an error with instructions.
    """
    url = SERVER + BASE + path
    if status:
        url += "?status=" + status

    ps_cmd = (
        "$ws = New-Object Microsoft.PowerShell.Commands.WebRequestSession; "
        "$c = New-Object System.Net.Cookie('GSSSO', '{}', '/', '.gs.com'); "
        "$ws.Cookies.Add($c); "
        "try {{ "
        "  $r = Invoke-WebRequest -Uri '{}' -WebSession $ws -UseBasicParsing -TimeoutSec 30; "
        "  $r.Content "
        "}} catch {{ "
        "  Write-Host \"ERROR:$($_.Exception.Message)\" "
        "}}"
    ).format(cookie, url)

    result = run_cmd(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=45,
    )

    body = result.stdout.strip()

    if not body or body.startswith("ERROR:"):
        err = body.replace("ERROR:", "") if body else result.stderr[:300]
        if "could not be resolved" in err.lower():
            print(
                "ERROR: Sky Gateway DNS not reachable from desktop.\n"
                "The AppDir API is only directly accessible from GS cloud hosts.\n"
                "Use --info to query the API definition from Canvas instead,\n"
                "or run this script from a cloud-hosted machine.",
                file=sys.stderr,
            )
        else:
            print(f"ERROR: Request failed for {url}", file=sys.stderr)
            print(err, file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(f"ERROR: Non-JSON response from {url}", file=sys.stderr)
        print(f"Response: {body[:500]}", file=sys.stderr)
        sys.exit(1)


def fetch_canvas(cookie: str, endpoint: str) -> dict:
    """Fetch from the Canvas API backend (accessible from desktop).

    Uses GSSSO session via -UseDefaultCredentials for auth.
    The cookie parameter is accepted for API compat but not used;
    auth happens via Windows integrated auth.
    """
    url = CANVAS_API + endpoint

    ps_cmd = (
        "$ProgressPreference = 'SilentlyContinue'; "
        "$ErrorActionPreference = 'Stop'; "
        "$null = Invoke-WebRequest -Uri '{}' "
        "-UseDefaultCredentials -UseBasicParsing -SessionVariable s; "
        "$r = Invoke-WebRequest -Uri '{}' -WebSession $s "
        "-UseBasicParsing -TimeoutSec 30 "
        "-Headers @{{Accept='application/json'}}; "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "[Console]::Out.Write($r.Content)"
    ).format(SSO_URL, url)

    result = run_cmd(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=60,
    )

    body = result.stdout.strip()
    if not body or result.returncode != 0:
        err = result.stderr.strip()[:500] if result.stderr else "Empty response"
        print(f"ERROR: Canvas request failed for {url}", file=sys.stderr)
        print(err, file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(f"ERROR: Non-JSON response from {url}", file=sys.stderr)
        print(f"Response: {body[:500]}", file=sys.stderr)
        sys.exit(1)


# Canvas backend endpoints (desktop-accessible)
CANVAS_DID_ENDPOINTS = {
    "summary": "/deployed-application/{0}",
    "full": "/deployments/{0}",
    "instantiated": "/deployments/{0}/instantiated",
    "hosts": "/deployments/{0}/hostTypes",
    "hypervisors": "/deployments/{0}/hypervisors",
    "beans": "/deployments/{0}/beans",
    "legacynodes": "/deployments/{0}/legacynodes",
    "locations": "/deployed-application/{0}/locations",
    "sysaccounts": "/deployed-application/{0}/systemAccounts",
    "classifications": "/deployed-application/{0}/classifications",
    "history": "/deployments/{0}/history?maxresults=1000&include-tmd-info=false",
    "terraform": "/deployments/{0}/terraform/status",
    "certificates": "/certificates/{0}",
    "audit": "/gscloud/audit/did/{0}?limit=100",
    "windows": "/deployed-application/{0}/windows?type=ALL",
    "storages": "/storages/by-deployment/{0}",
    "entitlements": "/entitlements/deployment/{0}",
}

CANVAS_ORG_ENDPOINTS = {
    "businessunits": "/businessunits",
    "subbusinessunits": "/subbusinessunits/by-buid/{0}",
    "families": "/families/by-sbuid/{0}",
    "applications": "/applications/by-familyid/{0}",
    "deployments-by-app": "/deployed-application/by-appid/{0}",
    "search-did": "/deployed-application/by-name/{0}",
}


def classify_resources(cookie: str, did: str) -> dict:
    """Fetch deployment resources, resolve bean VMShape, classify DC/EC.

    Returns a dict with 'hierarchy', 'resources' (enriched list), and 'summary'.
    """
    # 1. Fetch hierarchy for context
    hierarchy = fetch_canvas(cookie, f"/hierarchies/did-{did}")

    # 2. Fetch full deployment (contains resources)
    deployment = fetch_canvas(cookie, f"/deployments/{did}")
    raw_resources = []
    model = deployment.get("data", {}).get("model", {})
    for r in model.get("resources", []):
        raw_resources.append(r)

    # 3. Collect bean IDs where VMShape is missing
    bean_ids_needed = set()
    for r in raw_resources:
        attrs = r.get("attributes", {})
        if not attrs.get("VMShape"):
            product = r.get("product", {})
            if product.get("id"):
                bean_ids_needed.add(str(product["id"]))

    # 4. Fetch bean definitions if needed
    bean_shapes = {}
    if bean_ids_needed:
        bean_ids_str = ",".join(sorted(bean_ids_needed))
        beans_data = fetch_canvas(cookie, f"/beans/{bean_ids_str}/versions")
        bd = beans_data.get("data", beans_data)
        for bid, info in (bd.items() if isinstance(bd, dict) else []):
            bean_attrs = (info.get("beanDetails", {}).get("bean", {})
                          .get("attributes", {}))
            if bean_attrs.get("VMShape"):
                bean_shapes[bid] = bean_attrs["VMShape"]

    # 5. Enrich resources
    enriched = []
    totals = {"dc": 0, "ec": 0, "other": 0, "total_cores": 0, "total_mem_gb": 0}
    for r in raw_resources:
        attrs = r.get("attributes", {})
        name = r.get("name", "")
        product = r.get("product", {})

        # Resolve VMShape: resource-level first, then bean fallback
        vm_shape = attrs.get("VMShape")
        if not vm_shape and str(product.get("id", "")) in bean_shapes:
            vm_shape = bean_shapes[str(product["id"])]

        # Parse shape
        cores = 0
        mem_gb = 0
        size_label = ""
        if isinstance(vm_shape, dict):
            cores = int(vm_shape.get("core", 0))
            mem_gb = int(vm_shape.get("memory", 0))
            size_label = vm_shape.get("size", "")
        elif isinstance(vm_shape, str):
            try:
                shape_d = json.loads(vm_shape)
                cores = int(shape_d.get("core", 0))
                mem_gb = int(shape_d.get("memory", 0))
                size_label = shape_d.get("size", "")
            except (json.JSONDecodeError, ValueError):
                pass

        # Classify DC vs EC
        elasticity = attrs.get("Elasticity", {})
        if isinstance(elasticity, str):
            try:
                elasticity = json.loads(elasticity)
            except (json.JSONDecodeError, ValueError):
                elasticity = {}
        is_elastic = str(elasticity.get("isElastic", "False")).lower() == "true"
        res_type = "EC" if is_elastic else "DC"
        if not name or "storage" in name.lower():
            res_type = "Storage"

        if res_type == "DC":
            totals["dc"] += 1
        elif res_type == "EC":
            totals["ec"] += 1
        else:
            totals["other"] += 1
        totals["total_cores"] += cores
        totals["total_mem_gb"] += mem_gb

        enriched.append({
            "name": name,
            "type": res_type,
            "cores": cores,
            "memory_gb": mem_gb,
            "size": size_label,
            "bean_id": product.get("id"),
            "bean_name": product.get("name", ""),
        })

    # Build hierarchy summary
    hdata = hierarchy.get("data", hierarchy)
    if isinstance(hdata, list) and hdata:
        hdata = hdata[0]

    return {
        "deployment": {
            "did": did,
            "name": hdata.get("deploymentName", ""),
            "environment": hdata.get("deploymentEnvironment", ""),
            "application": hdata.get("applicationName", ""),
            "application_id": hdata.get("applicationId", ""),
            "family": hdata.get("familyName", ""),
            "family_id": hdata.get("familyId", ""),
            "sub_bu": hdata.get("subBusinessUnitName", ""),
            "bu": hdata.get("businessUnitName", ""),
        },
        "resources": enriched,
        "summary": totals,
    }


def output_json(data, output_path=None, out_file=None):
    """Format and output JSON data."""
    formatted = json.dumps(data, indent=2)
    target = output_path or out_file
    if target:
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(formatted)
        print(f"Saved to {target} ({len(formatted)} bytes)", file=sys.stderr)
    else:
        print(formatted)


def main():
    parser = argparse.ArgumentParser(
        description="Query AppDir 2.0 API (Canvas backend or Sky Gateway)"
    )
    sub = parser.add_subparsers(dest="command")

    # ---- Canvas backend: did <id> ----
    did_p = sub.add_parser("did", help="Get deployment details by DID (desktop-accessible)")
    did_p.add_argument("did_value", help="Deployment ID (e.g. 155218)")
    did_p.add_argument("--full", action="store_true", help="Full deployment (configs, resources, topologies)")
    did_p.add_argument("--instantiated", action="store_true", help="Full model (topologies, availability groups)")
    did_p.add_argument("--hosts", action="store_true", help="List hosts with type")
    did_p.add_argument("--hypervisors", action="store_true", help="Hypervisor details per host")
    did_p.add_argument("--beans", action="store_true", help="Bean IDs used by deployment")
    did_p.add_argument("--legacynodes", action="store_true", help="Legacy node list")
    did_p.add_argument("--locations", action="store_true", help="Data center locations")
    did_p.add_argument("--sysaccounts", action="store_true", help="System accounts")
    did_p.add_argument("--classifications", action="store_true", help="Classifications")
    did_p.add_argument("--history", action="store_true", help="Deployment history")
    did_p.add_argument("--terraform", action="store_true", help="Terraform status")
    did_p.add_argument("--certificates", action="store_true", help="TLS certificates")
    did_p.add_argument("--audit", action="store_true", help="Audit trail")
    did_p.add_argument("--windows", action="store_true", help="Maintenance windows")
    did_p.add_argument("--storages", action="store_true", help="Storage allocations")
    did_p.add_argument("--entitlements", action="store_true", help="User RBAC permissions")
    did_p.add_argument("--classify", action="store_true", help="Resources with DC/EC classification + VMShape (resolves beans)")
    did_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas backend: search-did <name> ----
    sdid_p = sub.add_parser("search-did", help="Search deployments by name (desktop-accessible)")
    sdid_p.add_argument("name", help="Deployment name to search")
    sdid_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas backend: businessunits ----
    bu_p = sub.add_parser("businessunits", help="List all business units (desktop-accessible)")
    bu_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas backend: hierarchy <did> ----
    hier_p = sub.add_parser("hierarchy", help="Full org chain for a DID (BU->SBU->Family->App->DID)")
    hier_p.add_argument("did_value", help="Deployment ID")
    hier_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas backend: beans <id1,id2,...> ----
    beans_p = sub.add_parser("beans", help="Bean definitions (resource templates)")
    beans_p.add_argument("bean_ids", help="Comma-separated bean IDs")
    beans_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas backend: roles (current user) ----
    roles_p = sub.add_parser("roles", help="Current user's Canvas family assignments and roles")
    roles_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas backend: host-info <hostname> ----
    hi_p = sub.add_parser("host-info", help="Host details and owning application (works for K8s nodes)")
    hi_p.add_argument("hostname", help="Fully qualified hostname")
    hi_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas backend: host-status <hostname> ----
    hs_p = sub.add_parser("host-status", help="Host operational status (placement ping)")
    hs_p.add_argument("hostname", help="Fully qualified hostname")
    hs_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas backend: org <type> <parentId> ----
    org_p = sub.add_parser("org", help="Browse org structure (desktop-accessible)")
    org_p.add_argument("org_type", choices=["subbusinessunits", "families", "applications", "deployments-by-app"])
    org_p.add_argument("parent_id", help="Parent entity ID")
    org_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Canvas discovery: --info / --openapi ----
    info_p = sub.add_parser("info", help="Show API definition from Canvas")
    info_p.add_argument("--openapi", action="store_true", help="Fetch OpenAPI spec instead")
    info_p.add_argument("--output", "-o", help="Write JSON to file")

    # ---- Sky Gateway: <entity> <lookup> <value> ----
    sky_p = sub.add_parser("sky", help="Query Sky Gateway directly (cloud-only)")
    sky_p.add_argument("entity", help="Entity type (application, deployment, host, etc.)")
    sky_p.add_argument("lookup", help="Lookup method (id, name, ext, hostname, etc.)")
    sky_p.add_argument("value", help="Lookup value")
    sky_p.add_argument("value2", nargs="?", help="Second value (for tagref entity lookups)")
    sky_p.add_argument("--status", help="Filter: ACTIVE, DECOMMISSIONED, IN_DEVELOPMENT")
    sky_p.add_argument("--output", "-o", help="Write JSON to file")

    # Legacy positional (backward compat): entity lookup value
    parser.add_argument("entity", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("lookup", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("value", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("value2", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--status", help=argparse.SUPPRESS)
    parser.add_argument("--output", "-o", help=argparse.SUPPRESS, dest="output_legacy")
    parser.add_argument("--info", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--openapi", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--args-file", default=None, metavar="PATH",
                        help="JSON file with args array or object (keys mirror CLI flags)")

    args = parser.parse_args()

    # ---------- Load from args-file if provided ----------
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8") as af:
            af_data = json.load(af)
        if isinstance(af_data, dict):
            # Object form: {"command": "did", "args": ["155218", "--classify"], "out_file": "..."}
            out_file = af_data.get("out_file")
            cli_args = af_data.get("args", [])
            if af_data.get("command"):
                cli_args = [af_data["command"]] + cli_args
            args = parser.parse_args(cli_args)
            args.out_file = out_file
        else:
            # Array form: ["did", "155218", "--classify"]
            args = parser.parse_args(af_data)
            args.out_file = None
    else:
        args.out_file = None

    # If out_file from args-file and no explicit -o, wire it into the output path
    if getattr(args, "out_file", None):
        if hasattr(args, "output") and not args.output:
            args.output = args.out_file
        if hasattr(args, "output_legacy") and not args.output_legacy:
            args.output_legacy = args.out_file

    # -- Legacy --info/--openapi --
    if getattr(args, "info", False) or getattr(args, "openapi", False):
        cookie = get_gssso_cookie()
        if getattr(args, "openapi", False):
            data = fetch_canvas(cookie, f"/api-definitions/{GSRN}/openapi")
        else:
            data = fetch_canvas(cookie, f"/api-definitions/{GSRN}")
        output_json(data, getattr(args, "output_legacy", None))
        return

    # -- Canvas: did --
    if args.command == "did":
        # Determine which endpoint(s) to call
        # --classify is a special mode that runs the enrichment pipeline
        if args.classify:
            cookie = get_gssso_cookie()
            data = classify_resources(cookie, args.did_value)
            output_json(data, args.output)
            return

        flags = {
            "full": args.full, "instantiated": args.instantiated,
            "hosts": args.hosts,
            "hypervisors": args.hypervisors, "beans": args.beans,
            "legacynodes": args.legacynodes,
            "locations": args.locations,
            "sysaccounts": args.sysaccounts, "classifications": args.classifications,
            "history": args.history, "terraform": args.terraform,
            "certificates": args.certificates, "audit": args.audit,
            "windows": args.windows, "storages": args.storages,
            "entitlements": args.entitlements,
        }
        selected = [k for k, v in flags.items() if v]
        if not selected:
            selected = ["summary"]

        cookie = get_gssso_cookie()
        results = {}
        for key in selected:
            endpoint = CANVAS_DID_ENDPOINTS[key].format(args.did_value)
            print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
            results[key] = fetch_canvas(cookie, endpoint)

        data = results if len(results) > 1 else results[selected[0]]
        output_json(data, args.output)
        return

    if args.command == "search-did":
        cookie = get_gssso_cookie()
        endpoint = CANVAS_ORG_ENDPOINTS["search-did"].format(args.name)
        print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
        data = fetch_canvas(cookie, endpoint)
        output_json(data, args.output)
        return

    if args.command == "businessunits":
        cookie = get_gssso_cookie()
        endpoint = CANVAS_ORG_ENDPOINTS["businessunits"]
        print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
        data = fetch_canvas(cookie, endpoint)
        output_json(data, args.output)
        return

    if args.command == "hierarchy":
        cookie = get_gssso_cookie()
        endpoint = f"/hierarchies/did-{args.did_value}"
        print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
        data = fetch_canvas(cookie, endpoint)
        output_json(data, args.output)
        return

    if args.command == "beans":
        cookie = get_gssso_cookie()
        endpoint = f"/beans/{args.bean_ids}/versions"
        print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
        data = fetch_canvas(cookie, endpoint)
        output_json(data, args.output)
        return

    if args.command == "roles":
        cookie = get_gssso_cookie()
        endpoint = "/appdir-entities/new/for-current-user"
        print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
        data = fetch_canvas(cookie, endpoint)
        output_json(data, args.output)
        return

    if args.command == "host-info":
        cookie = get_gssso_cookie()
        endpoint = f"/hosts/{args.hostname}"
        print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
        host_data = fetch_canvas(cookie, endpoint)
        host = host_data.get("data") or {}
        if not host:
            print(f"ERROR: No host data found for {args.hostname}", file=sys.stderr)
            output_json(host_data, args.output)
            return
        owning = host.get("owningDeployment") or {}
        did = owning.get("id")
        result = {"host": host_data}
        if did:
            hier_ep = f"/hierarchies/did-{did}"
            print(f"GET {CANVAS_API}{hier_ep}", file=sys.stderr)
            hier_data = fetch_canvas(cookie, hier_ep)
            result["hierarchy"] = hier_data
            h = hier_data.get("data", {})
            print(f"\nHost: {host.get('hostName')}", file=sys.stderr)
            print(f"Application: {h.get('applicationName')} (id {h.get('applicationId')})", file=sys.stderr)
            print(f"Deployment: {h.get('deploymentName')} (DID {h.get('deploymentId')})", file=sys.stderr)
            print(f"Family: {h.get('familyName')} | BU: {h.get('businessUnitName')}", file=sys.stderr)
        output_json(result, args.output)
        return

    if args.command == "host-status":
        cookie = get_gssso_cookie()
        endpoint = f"/hosts/{args.hostname}/status"
        print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
        data = fetch_canvas(cookie, endpoint)
        output_json(data, args.output)
        return

    if args.command == "org":
        cookie = get_gssso_cookie()
        endpoint = CANVAS_ORG_ENDPOINTS[args.org_type].format(args.parent_id)
        print(f"GET {CANVAS_API}{endpoint}", file=sys.stderr)
        data = fetch_canvas(cookie, endpoint)
        output_json(data, args.output)
        return

    if args.command == "info":
        cookie = get_gssso_cookie()
        if args.openapi:
            data = fetch_canvas(cookie, f"/api-definitions/{GSRN}/openapi")
        else:
            data = fetch_canvas(cookie, f"/api-definitions/{GSRN}")
        output_json(data, args.output)
        return

    if args.command == "sky":
        entity = args.entity.lower()
        lookup = args.lookup.lower()
        key = (entity, lookup)
        if key not in ROUTES:
            print(f"ERROR: Unknown route '{entity} {lookup}'", file=sys.stderr)
            for (e, l) in sorted(ROUTES):
                if e == entity:
                    print(f"  {e} {l}", file=sys.stderr)
            if not any(e == entity for e, _ in ROUTES):
                print(f"Available entities: {', '.join(sorted(set(e for e, _ in ROUTES)))}", file=sys.stderr)
            sys.exit(1)

        template = ROUTES[key]
        if "{1}" in template:
            if not args.value2:
                print(f"ERROR: '{entity} {lookup}' requires two values", file=sys.stderr)
                sys.exit(1)
            path = template.format(args.value, args.value2)
        else:
            path = template.format(args.value)

        cookie = get_gssso_cookie()
        print(f"GET {SERVER}{BASE}{path}", file=sys.stderr)
        data = fetch(cookie, path, status=args.status)
        output_json(data, args.output)
        return

    # -- Legacy positional: entity lookup value --
    if args.entity and args.lookup and args.value is not None:
        entity = args.entity.lower()
        lookup = args.lookup.lower()
        key = (entity, lookup)

        if key not in ROUTES:
            print(f"ERROR: Unknown route '{entity} {lookup}'", file=sys.stderr)
            print("Hint: Use 'did <id>' for desktop queries or 'sky <entity> <lookup> <value>' for cloud.", file=sys.stderr)
            for (e, l) in sorted(ROUTES):
                if e == entity:
                    print(f"  {e} {l}", file=sys.stderr)
            sys.exit(1)

        template = ROUTES[key]
        if "{1}" in template:
            if not args.value2:
                print(f"ERROR: '{entity} {lookup}' requires two values", file=sys.stderr)
                sys.exit(1)
            path = template.format(args.value, args.value2)
        else:
            path = template.format(args.value)

        cookie = get_gssso_cookie()
        print(f"GET {SERVER}{BASE}{path}", file=sys.stderr)
        data = fetch(cookie, path, status=getattr(args, "status", None))
        output_json(data, getattr(args, "output_legacy", None))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
