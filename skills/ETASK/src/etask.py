"""eTask Workflow Engine REST API client.

Uses GSSSO auth with:
  - OPS gateway aggregation (faceted poll / task list) via gateway.workflow.ep
  - Gateway WFE proxy for engine operations (works from devtools for all envs)
  - Direct WFE engine endpoints as fallback (requires network access)

Usage:
    python etask.py list --kerberos <kerb> [--status OPEN] [--app "Auto Refactors"]
    python etask.py inspect --piid <id> --engine <engine>
    python etask.py actions --piid <id> --engine <engine> --kerberos <kerb>
    python etask.py task-actions --task-id <id> --engine <engine> --kerberos <kerb>
    python etask.py task-detail --task-id <id> --engine <engine>
    python etask.py create --engine <engine> --bpmn <process-def-id> --payload-file <path>
    python etask.py complete --task-id <id> --engine <engine> --kerberos <kerb> [--reason ...]
    python etask.py cancel --piid <id> --engine <engine> --kerberos <kerb> --message-name <name>
    python etask.py message --piid <id> --engine <engine> --kerberos <kerb> --message-name <name>
    python etask.py search --engine <engine> --field <key> --value <val>
    python etask.py definitions --engine <engine> [--active]
    python etask.py archive --task-id <id> --engine <engine> --kerberos <kerb>
    python etask.py bulk-archive --kerberos <kerb> --app "PACT Next" --engine <engine> --region non-latam [--dry-run]
    python etask.py restore --task-id <id> --engine <engine> --kerberos <kerb>
    python etask.py engines [--env prod|dev|qa]
    python etask.py open [--piid <id>]

Engine names:
    From faceted poll --verbose, the Type/Engine Ref facet shows:
      TASK_TYPE#engine-name  (e.g. APPROVE_TMD_ORDER#prod-11262-004)
    Gateway proxy:       https://gateway.workflow.ep.site.gs.com/wfe/{engine}
    Direct URL pattern:  https://{engine}.engine.workflow.ep.site.gs.com:11101

Reference:
    Slang: _LIB Etask Query, _Const Etask Query (reporting service, GSSSO)
    OpenAPI: https://{engine}.engine.workflow.ep.site.gs.com:11101/openapi.json
"""

import argparse
import atexit
import io
import json
import os
import re
import subprocess
import sys
import time
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402

SSO_URL = "https://authn.web.gs.com/desktopsso/Login"

# Direct WFE engine URL pattern — requires direct network access (not from devtools)
ENGINE_URL_TEMPLATE = "https://{engine}.engine.workflow.ep.site.gs.com:11101"

# Gateway WFE proxy — routes to engines, works from devtools for ALL envs
GATEWAY_WFE_TEMPLATE = "https://gateway.workflow.ep.site.gs.com/wfe/{engine}"

# OPS aggregation gateway — faceted poll / task list (GSSSO auth)
OPS_GATEWAY_TEMPLATE = "https://gateway.workflow.ep.site.gs.com/aggr/{env}/rs/wis/v1"

# Commonly known engines per environment
KNOWN_ENGINES = {
    "prod": [
        "autprd1-001", "autprd1-002", "autprd1-003",
        "autprd1-004", "autprd1-005", "autprd1-006",
        "autprd2-001", "autprd2-002", "autprd2-003",
        "autprd2-004", "autprd2-005", "autprd2-006",
    ],
    "dev": [
        "autint1-001", "autint1-002", "autint1-003",
        "autint1-004", "autint1-005", "autint1-006",
    ],
    "qa": [
        "autint1-001", "autint1-002", "autint1-003",
    ],
}

# eTask web UI base URLs
ETASK_UI = {
    "prod": "https://etask.gs.com",
    "dev": "https://dev.etask.gs.com",
    "qa": "https://qa.etask.gs.com",
}

# EPSSP DirGet for person location lookups
DIRGET_URL_TEMPLATE = "https://www.epssp.site.gs.com/ssps/ProdSource/Dirget?K={kerberos}"

# Countries considered LatAm for PACT filtering
LATAM_COUNTRIES = {"Brazil", "Argentina", "Chile", "Colombia", "Mexico", "Peru"}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "workspace", "tmp")


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


def api_request(method: str, url: str, cookie: str, json_body=None, params=None, extra_headers=None) -> dict:
    """Make an authenticated request to the eTask API."""
    import urllib.request
    import urllib.error
    import urllib.parse
    import ssl

    if params:
        url = url + "?" + urllib.parse.urlencode(params)

    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")

    ctx = ssl.create_default_context()

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Cookie", f"GSSSO={cookie}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            headers = dict(resp.headers)
            if body:
                try:
                    return {"status": resp.status, "headers": headers, "data": json.loads(body)}
                except json.JSONDecodeError:
                    return {"status": resp.status, "headers": headers, "data": body}
            return {"status": resp.status, "headers": headers, "data": None}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {e.reason}", file=sys.stderr)
        if body:
            print(body[:1000], file=sys.stderr)
        return {"status": e.code, "error": e.reason, "body": body}
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        return {"status": 0, "error": str(e.reason)}


def engine_url(engine: str, use_gateway: bool = True) -> str:
    """Build the WFE engine base URL.

    Uses the gateway proxy by default (works from devtools for all envs).
    Falls back to direct engine URL if use_gateway=False.
    """
    if use_gateway:
        return GATEWAY_WFE_TEMPLATE.format(engine=engine)
    return ENGINE_URL_TEMPLATE.format(engine=engine)


def save_output(data, label: str) -> str:
    """Save JSON output to workspace/tmp."""
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = int(time.time())
    path = os.path.join(OUT_DIR, f"etask-{label}-{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nJSON saved to {path}")
    return path


def ops_gateway_url(env: str) -> str:
    """Build the OPS aggregation gateway base URL."""
    return OPS_GATEWAY_TEMPLATE.format(env=env)


# --- Commands ---

def cmd_list(args):
    """List tasks via OPS aggregation gateway (faceted poll)."""
    cookie = get_gssso_cookie()
    base = ops_gateway_url(args.env)

    # Build selected facets
    selected = []
    statuses = [s.strip() for s in args.status.split(",")] if args.status else ["OPEN", "IN_PROGRESS"]
    for s in statuses:
        selected.append({"selectedFacet": "status", "selectedValue": s})
    if args.app:
        selected.append({"selectedFacet": "applicationname", "selectedValue": args.app + "|"})
    if args.priority:
        selected.append({"selectedFacet": "priority", "selectedValue": args.priority})

    body = {
        "selectedFacets": selected,
        "numberOfRecords": args.limit,
        "processView": False,
        "excludeCompleted": True,
        "timezone": "America/New_York",
        "onlyWorkflowEngineTypes": True,
    }

    url = f"{base}/facetedpoll/{args.kerberos}"
    result = api_request("POST", url, cookie, json_body=body)

    if result.get("status") != 200:
        print(f"Failed to fetch task list (HTTP {result.get('status', '?')})", file=sys.stderr)
        save_output(result, "list-error")
        return

    data = result["data"]
    total = data.get("totalNumberOfRecords", 0)
    ids = data.get("ids", [])
    facets = data.get("facets", [])
    app_summary = data.get("applicationSummary", {})

    print(f"\neTask Summary for {args.kerberos} ({args.env})")
    print(f"{'=' * 60}")
    print(f"Total tasks: {total}")

    # Facets to show (ordered), with display names
    show_facets = [
        ("status", "Status"),
        ("priority", "Priority"),
        ("duedate", "Due Date"),
        ("createdate", "Created"),
    ]
    if args.verbose:
        show_facets.extend([
            ("workitemenv", "Engine"),
            ("individual", "Assignee"),
            ("updatedate", "Updated"),
            ("typeenginereference", "Type/Engine Ref"),
        ])

    # Build facet lookup
    facet_map = {}
    for f in facets:
        name = f.get("searchParameter", "")
        if name:
            facet_map[name] = f.get("facetBuckets", [])

    for facet_key, display in show_facets:
        buckets = facet_map.get(facet_key, [])
        if not buckets:
            continue
        # Skip buckets with zero count
        active = [b for b in buckets if b.get("facetCount", b.get("totalFacetCount", 0)) > 0]
        if not active:
            continue
        print(f"\n  {display}:")
        for b in active:
            label = b.get("displayLabel") or b.get("label", "?")
            count = b.get("facetCount", b.get("totalFacetCount", 0))
            print(f"    {label:<40} {count:>4}")

    # Application summary (shows task sources with counts)
    if isinstance(app_summary, dict) and app_summary.get("facetBuckets"):
        active = [b for b in app_summary["facetBuckets"]
                  if b.get("facetCount", b.get("totalFacetCount", 0)) > 0]
        if active:
            print(f"\n  Application:")
            for b in active:
                label = b.get("displayLabel") or b.get("label", "?")
                count = b.get("facetCount", b.get("totalFacetCount", 0))
                print(f"    {label:<40} {count:>4}")

    # Type breakdown (from workitemtype facet — shows task names)
    type_buckets = facet_map.get("workitemtype", [])
    if type_buckets:
        active = [b for b in type_buckets
                  if b.get("facetCount", b.get("totalFacetCount", 0)) > 0]
        if active:
            print(f"\n  Task Type:")
            for b in active:
                label = b.get("displayLabel") or b.get("label", "?")
                count = b.get("facetCount", b.get("totalFacetCount", 0))
                print(f"    {label:<40} {count:>4}")

    # IDs listing (if verbose)
    if args.verbose and ids:
        print(f"\n  Work Item IDs ({len(ids)} of {total}):")
        for item in ids:
            wid = item.get("workItemVersionId", {})
            print(f"    {wid.get('id', '?')} (v{wid.get('version', '?')})")

    save_output(data, "list")


def cmd_inspect(args):
    """Inspect a process instance."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)

    url = f"{base}/processinstances/{args.piid}"
    result = api_request("GET", url, cookie)

    if result.get("status") != 200:
        print(f"Failed to inspect process {args.piid}", file=sys.stderr)
        save_output(result, "inspect-error")
        return

    data = result["data"]
    case = data.get("caseDetail") or data.get("caseSummary") or {}
    print(f"\nProcess Instance: {args.piid}")
    print(f"  Process ID:  {data.get('processId', '?')}")
    print(f"  Version:     {data.get('processVersion', '?')}")
    print(f"  Active:      {data.get('active', '?')}")
    print(f"  Status:      {case.get('status', '?')}")
    print(f"  Task ID:     {case.get('taskId', '?')}")
    print(f"  Created:     {case.get('createdDate', '?')}")
    print(f"  Assignee:    {case.get('assignee', '?')}")
    print(f"  Business Key: {data.get('businessKey', '?')}")

    tasks = data.get("taskSummaries", [])
    if tasks:
        print(f"\n  Child Tasks ({len(tasks)}):")
        for t in tasks:
            print(f"    - {t.get('taskId', '?')} [{t.get('type', '?')}] "
                  f"completed={t.get('completed', '?')}")

    output = {"processInstance": data}

    if args.data:
        data_url = f"{base}/processinstances/{args.piid}/data"
        data_result = api_request("GET", data_url, cookie)
        if data_result.get("status") == 200:
            output["data"] = data_result["data"]
            print(f"\n  Data: {json.dumps(data_result['data'], indent=2, default=str)[:2000]}")

    if args.activity:
        act_url = f"{base}/processinstances/{args.piid}/activity"
        act_result = api_request("GET", act_url, cookie)
        if act_result.get("status") == 200:
            output["activity"] = act_result["data"]
            node = act_result["data"]
            children = node.get("childActivities", [])
            print(f"\n  Activities ({len(children)}):")
            for a in children:
                print(f"    - [{a.get('activityType', '?')}] "
                      f"{a.get('activityId', '?')} status={a.get('status', '?')}")

    save_output(output, "inspect")


def cmd_actions(args):
    """Get available process actions for a user."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/processinstances/{args.piid}/actions/{args.kerberos}?includeTasks=true"
    result = api_request("GET", url, cookie)

    if result.get("status") == 200:
        data = result["data"]
        pi_actions = data.get("processInstanceActions", [])
        print(f"\nProcess actions for {args.kerberos} on {args.piid}:")
        for a in pi_actions:
            print(f"  - {a}")

        task_actions = data.get("taskActions", [])
        if task_actions:
            print(f"\n  Task actions:")
            for ta in task_actions:
                tid = ta.get("taskId", "?")
                acts = ta.get("actions", [])
                print(f"    Task {tid}: {', '.join(acts) if acts else 'none'}")

        save_output(data, "actions")
    else:
        print("Failed to get actions.", file=sys.stderr)
        save_output(result, "actions-error")


def cmd_task_actions(args):
    """Get available task actions for a user."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/tasks/{args.task_id}/actions/{args.kerberos}"
    result = api_request("GET", url, cookie)

    if result.get("status") == 200:
        data = result["data"]
        actions = data.get("actions", data if isinstance(data, list) else [])
        print(f"\nActions for {args.kerberos} on task {args.task_id}:")
        for a in actions:
            print(f"  - {a}")
        save_output(data, "task-actions")
    else:
        print("Failed to get task actions.", file=sys.stderr)
        save_output(result, "task-actions-error")


def cmd_task_detail(args):
    """Get task details."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/tasks/{args.task_id}"
    result = api_request("GET", url, cookie)

    if result.get("status") == 200:
        data = result["data"]
        print(f"\nTask: {args.task_id}")
        print(f"  Type:       {data.get('type', '?')}")
        print(f"  Completed:  {data.get('completed', '?')}")
        print(f"  Assignee:   {data.get('assignee', '?')}")
        print(f"  Process ID: {data.get('processId', '?')}")
        print(f"  PIID:       {data.get('processInstanceId', '?')}")
        save_output(data, "task-detail")
    else:
        print(f"Failed to get task detail.", file=sys.stderr)
        save_output(result, "task-detail-error")


def cmd_create(args):
    """Create a new eTask process instance."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/processdefinitions/{args.bpmn}"

    with open(args.payload_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    result = api_request("POST", url, cookie, json_body=payload)

    if result.get("status") in (200, 201):
        location = result.get("headers", {}).get("location",
                   result.get("headers", {}).get("Location", ""))
        piid = location.rsplit("/", 1)[-1] if location else "?"
        print(f"\neTask created successfully!")
        print(f"  Process Instance ID: {piid}")
        print(f"  Location: {location}")
        save_output({"piid": piid, "location": location, "status": result["status"]}, "create")
    else:
        print(f"Failed to create eTask (HTTP {result.get('status', '?')})", file=sys.stderr)
        save_output(result, "create-error")


def get_work_item_version(task_id: str, cookie: str, env: str = "prod") -> str | None:
    """Fetch work item version from OPS aggregation for If-Match header."""
    base = ops_gateway_url(env)
    url = f"{base}/facetedpoll/workitems/{task_id}"
    result = api_request("GET", url, cookie)
    if result.get("status") == 200:
        data = result.get("data", {})
        wivid = data.get("workItemVersionId", {})
        version = wivid.get("version")
        if version is not None:
            return str(version)
    return None


def cmd_complete(args):
    """Complete a task."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/tasks/{args.task_id}/complete"

    body = {
        "userId": args.kerberos,
        "reasonCode": args.reason,
        "comment": {
            "comment": args.comment or "",
            "categorized": False,
        },
        "params": {},
    }

    if args.params_file:
        with open(args.params_file, "r", encoding="utf-8") as f:
            body["params"] = json.load(f)

    extra_headers = {}
    if_match = args.if_match
    if not if_match:
        if_match = get_work_item_version(args.task_id, cookie)
        if if_match:
            print(f"Auto-fetched If-Match version: {if_match}")
    if if_match:
        extra_headers["If-Match"] = if_match

    result = api_request("POST", url, cookie, json_body=body, extra_headers=extra_headers)

    if result.get("status") in (200, 204):
        print(f"\nTask {args.task_id} completed with reason: {args.reason}")
        save_output(result, "complete")
    else:
        print(f"Failed to complete task (HTTP {result.get('status', '?')})", file=sys.stderr)
        save_output(result, "complete-error")


def dirget_location(kerberos: str, cookie: str) -> str:
    """Look up a person's office location via EPSSP DirGet.

    Returns full location string, e.g. 'Sao Paulo, 700M/017, 314A02 (Brazil, Americas)'
    or empty string on failure.
    """
    import urllib.request
    import ssl

    url = DIRGET_URL_TEMPLATE.format(kerberos=kerberos)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url)
    req.add_header("Cookie", f"GSSSO={cookie}")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            m = re.search(r"<DT>Location</DT>.*?<A[^>]*>([^<]+)</A>", html, re.DOTALL)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return ""


def location_country(location: str) -> str:
    """Extract country from DirGet location string.

    Location format: 'City, Floor/Seat, Zone (Country, Region)'
    Returns the country name or empty string.
    """
    m = re.search(r"\(([^,)]+)", location)
    return m.group(1).strip() if m else ""


def is_latam_location(location: str) -> bool:
    """Check if a DirGet location string indicates a LatAm office."""
    return location_country(location) in LATAM_COUNTRIES


def get_work_item_detail(task_id: str, cookie: str, env: str = "prod") -> dict | None:
    """Fetch full work item detail from OPS aggregation.

    Returns the work item dict with extensionData (kerberos, deptName, etc.)
    or None on failure.
    """
    base = ops_gateway_url(env)
    url = f"{base}/facetedpoll/workitems/{task_id}"
    result = api_request("GET", url, cookie)
    if result.get("status") == 200:
        return result.get("data", {})
    return None


def get_pact_task_ids(kerberos: str, cookie: str, env: str = "prod",
                      app: str = "PACT Next", limit: int = 200) -> list[dict]:
    """List tasks filtered by application and return their IDs + versions."""
    base = ops_gateway_url(env)
    url = f"{base}/facetedpoll/{kerberos}"
    body = {
        "selectedFacets": [
            {"selectedFacet": "status", "selectedValue": "OPEN"},
            {"selectedFacet": "status", "selectedValue": "IN_PROGRESS"},
            {"selectedFacet": "applicationname", "selectedValue": app + "|"},
        ],
        "numberOfRecords": limit,
        "processView": False,
        "excludeCompleted": True,
        "timezone": "America/New_York",
        "onlyWorkflowEngineTypes": True,
    }
    result = api_request("POST", url, cookie, json_body=body)
    if result.get("status") != 200:
        return []
    ids = result.get("data", {}).get("ids", [])
    return [
        {
            "taskId": item["workItemVersionId"]["id"],
            "version": item["workItemVersionId"]["version"],
        }
        for item in ids
    ]


def archive_task(task_id: str, engine: str, kerberos: str, cookie: str) -> bool:
    """Archive a single task. Returns True on success."""
    base = engine_url(engine)
    url = f"{base}/tasks/{task_id}/tags/add"
    body = {
        "userId": kerberos,
        "tags": [f"@etask|archive|{kerberos}"],
    }
    result = api_request("POST", url, cookie, json_body=body)
    return result.get("status") in (200, 204)


def cmd_bulk_archive(args):
    """Bulk-archive tasks filtered by application + location.

    Fetches tasks for --app, resolves each reviewed user's office via DirGet,
    then archives tasks that match (or don't match) the --region filter.
    """
    cookie = get_gssso_cookie()
    app = args.app
    engine = args.engine
    region = args.region  # "latam" or "non-latam"
    dry_run = args.dry_run

    keep_latam = region == "non-latam"  # archive non-latam, keep latam
    if region == "latam":
        keep_latam = False  # archive latam, keep non-latam

    print(f"\n{'=' * 70}")
    print(f"Bulk Archive — app={app!r}, region filter={region}, engine={engine}")
    print(f"{'=' * 70}")

    # 1. Fetch task IDs
    print(f"\n[1/4] Fetching {app!r} tasks for {args.kerberos}...")
    tasks = get_pact_task_ids(args.kerberos, cookie, args.env, app=app)
    print(f"  Found {len(tasks)} tasks")

    if not tasks:
        print("No tasks found. Done.")
        return

    # 2. Classify by location
    print(f"\n[2/4] Resolving locations via DirGet...")
    to_archive = []
    to_keep = []
    unknown = []
    loc_cache: dict[str, str] = {}

    for i, task in enumerate(tasks):
        tid = task["taskId"]
        print(f"  [{i+1}/{len(tasks)}] {tid}...", end=" ", flush=True)

        wi = get_work_item_detail(tid, cookie, args.env)
        if not wi:
            print("SKIP (no work item)")
            unknown.append({**task, "reason": "no work item detail"})
            continue

        ext = wi.get("extensionData", {})
        kerb = ext.get("kerberos", "")
        dept = ext.get("deptName", "")
        wtype = wi.get("workItemType", "")

        if not kerb:
            print(f"SKIP (no kerberos, type={wtype})")
            unknown.append({**task, "type": wtype, "dept": dept, "reason": "no kerberos"})
            continue

        if kerb not in loc_cache:
            loc_cache[kerb] = dirget_location(kerb, cookie)
        loc = loc_cache[kerb]
        latam = is_latam_location(loc)
        country = location_country(loc)

        entry = {**task, "kerberos": kerb, "dept": dept, "location": loc,
                 "country": country, "type": wtype, "latam": latam}

        should_archive = (latam and region == "latam") or (not latam and region == "non-latam")

        if should_archive:
            to_archive.append(entry)
            print(f"ARCHIVE ({kerb}, {country}, {dept})")
        else:
            to_keep.append(entry)
            print(f"KEEP    ({kerb}, {country}, {dept})")

    # 3. Summary
    print(f"\n[3/4] Summary:")
    print(f"  To archive: {len(to_archive)}")
    print(f"  Keeping:    {len(to_keep)}")
    print(f"  Unknown:    {len(unknown)}")

    if to_archive:
        print(f"\n  Tasks to archive:")
        for t in to_archive:
            print(f"    {t['taskId']}  {t.get('kerberos','?'):<12} "
                  f"{t.get('country','?'):<16} {t.get('dept','?')}")

    if not to_archive:
        print("\nNothing to archive. Done.")
        return

    if dry_run:
        print(f"\n[4/4] DRY RUN — would archive {len(to_archive)} tasks. Use without --dry-run to execute.")
        report = _build_bulk_report(to_archive, to_keep, unknown, 0, 0, dry_run=True)
        save_output(report, "bulk-archive-dry")
        return

    # 4. Archive
    print(f"\n[4/4] Archiving {len(to_archive)} tasks...")
    success = 0
    failed = 0
    for i, t in enumerate(to_archive):
        tid = t["taskId"]
        print(f"  [{i+1}/{len(to_archive)}] {tid} ({t.get('kerberos','?')})...", end=" ", flush=True)
        if archive_task(tid, engine, args.kerberos, cookie):
            print("OK")
            success += 1
        else:
            print("FAILED")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"Done. Archived: {success}, Failed: {failed}, "
          f"Kept: {len(to_keep)}, Unknown: {len(unknown)}")

    report = _build_bulk_report(to_archive, to_keep, unknown, success, failed)
    save_output(report, "bulk-archive")


def _build_bulk_report(archived, kept, unknown, success, failed, dry_run=False):
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dry_run": dry_run,
        "archived": archived,
        "kept": kept,
        "unknown": unknown,
        "stats": {
            "archived": success,
            "failed": failed,
            "kept": len(kept),
            "unknown": len(unknown),
        },
    }


def cmd_archive(args):
    """Archive a task by adding the @etask|archive tag."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/tasks/{args.task_id}/tags/add"

    body = {
        "userId": args.kerberos,
        "tags": [f"@etask|archive|{args.kerberos}"],
    }

    result = api_request("POST", url, cookie, json_body=body)

    if result.get("status") in (200, 204):
        print(f"\nTask {args.task_id} archived.")
        save_output(result, "archive")
    else:
        print(f"Failed to archive task (HTTP {result.get('status', '?')})", file=sys.stderr)
        save_output(result, "archive-error")


def cmd_restore(args):
    """Restore (un-archive) a task by removing the @etask|archive tag."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/tasks/{args.task_id}/tags/remove"

    body = {
        "userId": args.kerberos,
        "tags": [f"@etask|archive|{args.kerberos}"],
    }

    result = api_request("POST", url, cookie, json_body=body)

    if result.get("status") in (200, 204):
        print(f"\nTask {args.task_id} restored (un-archived).")
        save_output(result, "restore")
    else:
        print(f"Failed to restore task (HTTP {result.get('status', '?')})", file=sys.stderr)
        save_output(result, "restore-error")


def cmd_cancel(args):
    """Cancel a process instance via message."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/processinstances/{args.piid}/message"

    body = {
        "userId": args.kerberos,
        "messageName": args.message_name,
    }

    result = api_request("POST", url, cookie, json_body=body)

    if result.get("status") in (200, 204):
        print(f"\nCancel message sent to process {args.piid}")
        save_output(result, "cancel")
    else:
        print(f"Failed to cancel process (HTTP {result.get('status', '?')})", file=sys.stderr)
        save_output(result, "cancel-error")


def cmd_message(args):
    """Send a message to a process instance."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/processinstances/{args.piid}/message"

    body = {
        "userId": args.kerberos,
        "messageName": args.message_name,
    }

    if args.comment:
        body["messagePayload"] = {
            "Send_Message": {
                "Interim_Response": f"<p>{args.comment}</p>\n"
            }
        }

    if args.payload_file:
        with open(args.payload_file, "r", encoding="utf-8") as f:
            body["messagePayload"] = json.load(f)

    result = api_request("POST", url, cookie, json_body=body)

    if result.get("status") in (200, 204):
        print(f"\nMessage sent to process {args.piid}")
        save_output(result, "message")
    else:
        print(f"Failed to send message (HTTP {result.get('status', '?')})", file=sys.stderr)
        save_output(result, "message-error")


def cmd_search(args):
    """Search for process instances by key-value."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)
    url = f"{base}/processinstances"

    params = {"_queryType": "KEY_VALUE", args.field: args.value}
    result = api_request("GET", url, cookie, params=params)

    if result.get("status") == 200:
        data = result["data"]
        if isinstance(data, list):
            active = [p for p in data if p.get("active")]
            print(f"\nFound {len(active)} active / {len(data)} total process(es) "
                  f"matching {args.field}={args.value}:")
            for p in active[:50]:
                piid = p.get("id", p.get("processInstanceId", "?"))
                proc_id = p.get("processId", "?")
                bkey = p.get("businessKey", "")
                print(f"  - {piid} [{proc_id}] {bkey}")
            save_output(data, "search")
        else:
            print(json.dumps(data, indent=2, default=str)[:3000])
            save_output(data, "search")
    else:
        print("Search failed.", file=sys.stderr)
        save_output(result, "search-error")


def cmd_definitions(args):
    """List or get a process definition."""
    cookie = get_gssso_cookie()
    base = engine_url(args.engine)

    if args.bpmn:
        url = f"{base}/processdefinitions/{args.bpmn}"
    else:
        url = f"{base}/management/processdefinitions/active"

    result = api_request("GET", url, cookie)

    if result.get("status") == 200:
        data = result["data"]
        if isinstance(data, list):
            print(f"\nProcess definitions on {args.engine} ({len(data)}):")
            for d in data[:100]:
                did = d.get("processId", d.get("id", "?"))
                ver = d.get("version", "?")
                print(f"  - {did} v{ver}")
        else:
            print(json.dumps(data, indent=2, default=str)[:3000])
        save_output(data, "definitions")
    else:
        print("Failed to get definitions.", file=sys.stderr)
        save_output(result, "definitions-error")


def cmd_engines(args):
    """Test connectivity to known engines."""
    cookie = get_gssso_cookie()
    engines = KNOWN_ENGINES.get(args.env, KNOWN_ENGINES["prod"])

    print(f"\nTesting {len(engines)} engine(s) ({args.env}):\n")
    for eng in engines:
        base = engine_url(eng)
        try:
            result = api_request("GET", f"{base}/management/processdefinitions/active", cookie)
            status = result.get("status", "?")
            count = len(result.get("data", [])) if isinstance(result.get("data"), list) else "?"
            print(f"  {eng}: HTTP {status} ({count} active definitions)")
        except Exception as exc:
            print(f"  {eng}: ERROR - {exc}")


def cmd_open(args):
    """Open eTask web UI in browser."""
    base = ETASK_UI.get(args.env, ETASK_UI["prod"])
    url = base
    if args.piid:
        url = f"{base}/task/{args.piid}"
    print(f"Opening {url}")
    webbrowser.open(url)


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
    _apply_args_file(["command"], parent_keys=["env", "out_file"])
    parser = argparse.ArgumentParser(description="eTask Workflow Engine CLI")
    parser.add_argument("--env", default="prod", choices=["prod", "dev", "qa"],
                        help="Environment (default: prod)")

    sub = parser.add_subparsers(dest="command", required=True)

    # list (aggregated task list via OPS gateway)
    p_list = sub.add_parser("list", help="List tasks via OPS aggregation gateway")
    p_list.add_argument("--kerberos", required=True, help="User kerberos ID")
    p_list.add_argument("--status", default="OPEN,IN_PROGRESS",
                        help="Comma-separated statuses (default: OPEN,IN_PROGRESS)")
    p_list.add_argument("--app", help="Filter by application name")
    p_list.add_argument("--priority", help="Filter by priority (1=Low, 2=Medium, 3=High, 4=Critical)")
    p_list.add_argument("--limit", type=int, default=50,
                        help="Max IDs to return (default: 50)")
    p_list.add_argument("--verbose", action="store_true",
                        help="Show work item IDs and type/engine details")

    # inspect
    p_inspect = sub.add_parser("inspect", help="Inspect a process instance")
    p_inspect.add_argument("--piid", required=True, help="Process instance ID")
    p_inspect.add_argument("--engine", required=True, help="Engine name (e.g. autprd1-001)")
    p_inspect.add_argument("--data", action="store_true", help="Include process data")
    p_inspect.add_argument("--activity", action="store_true", help="Include activity log")

    # actions
    p_actions = sub.add_parser("actions", help="Get process actions for a user")
    p_actions.add_argument("--piid", required=True, help="Process instance ID")
    p_actions.add_argument("--engine", required=True, help="Engine name")
    p_actions.add_argument("--kerberos", required=True, help="User kerberos ID")

    # task-actions
    p_ta = sub.add_parser("task-actions", help="Get task actions for a user")
    p_ta.add_argument("--task-id", required=True, help="Task ID")
    p_ta.add_argument("--engine", required=True, help="Engine name")
    p_ta.add_argument("--kerberos", required=True, help="User kerberos ID")

    # task-detail
    p_td = sub.add_parser("task-detail", help="Get task details")
    p_td.add_argument("--task-id", required=True, help="Task ID")
    p_td.add_argument("--engine", required=True, help="Engine name")

    # create
    p_create = sub.add_parser("create", help="Create a new eTask")
    p_create.add_argument("--engine", required=True, help="Engine name")
    p_create.add_argument("--bpmn", required=True, help="BPMN process definition ID")
    p_create.add_argument("--payload-file", required=True, help="JSON payload file")

    # complete
    p_complete = sub.add_parser("complete", help="Complete a task (approve/reject)")
    p_complete.add_argument("--task-id", required=True, help="Task ID")
    p_complete.add_argument("--engine", required=True, help="Engine name")
    p_complete.add_argument("--kerberos", required=True, help="User kerberos ID")
    p_complete.add_argument("--reason", required=True,
                            help="Reason code from task-actions (e.g. approve_tmd, reject_tmd, CONFIRMED, REJECTED)")
    p_complete.add_argument("--comment", default="", help="Completion comment")
    p_complete.add_argument("--params-file", help="JSON file with additional params")
    p_complete.add_argument("--if-match", help="Work item version for If-Match header (auto-fetched from OPS if omitted)")

    # cancel
    p_cancel = sub.add_parser("cancel", help="Cancel a process via message")
    p_cancel.add_argument("--piid", required=True, help="Process instance ID")
    p_cancel.add_argument("--engine", required=True, help="Engine name")
    p_cancel.add_argument("--kerberos", required=True, help="User kerberos ID")
    p_cancel.add_argument("--message-name", required=True,
                          help="Cancel message name")

    # message
    p_msg = sub.add_parser("message", help="Send a message to a process")
    p_msg.add_argument("--piid", required=True, help="Process instance ID")
    p_msg.add_argument("--engine", required=True, help="Engine name")
    p_msg.add_argument("--kerberos", required=True, help="User kerberos ID")
    p_msg.add_argument("--message-name", required=True, help="Message name")
    p_msg.add_argument("--comment", help="Comment text")
    p_msg.add_argument("--payload-file", help="JSON file with message payload")

    # search
    p_search = sub.add_parser("search", help="Search processes by key-value")
    p_search.add_argument("--engine", required=True, help="Engine name")
    p_search.add_argument("--field", required=True, help="Index field name")
    p_search.add_argument("--value", required=True, help="Field value to match")

    # definitions
    p_def = sub.add_parser("definitions", help="List process definitions on an engine")
    p_def.add_argument("--engine", required=True, help="Engine name")
    p_def.add_argument("--bpmn", help="Specific BPMN definition ID (optional)")

    # archive
    p_archive = sub.add_parser("archive", help="Archive a task (hide from inbox)")
    p_archive.add_argument("--task-id", required=True, help="Task ID")
    p_archive.add_argument("--engine", required=True, help="Engine name (from --verbose facets)")
    p_archive.add_argument("--kerberos", required=True, help="User kerberos ID")

    # bulk-archive
    p_ba = sub.add_parser("bulk-archive",
                          help="Bulk-archive tasks filtered by app + location region")
    p_ba.add_argument("--kerberos", required=True, help="User kerberos ID")
    p_ba.add_argument("--app", required=True,
                      help="Application name filter (e.g. 'PACT Next')")
    p_ba.add_argument("--engine", required=True,
                      help="Engine name for archive API (e.g. prod-ep-002)")
    p_ba.add_argument("--region", required=True, choices=["latam", "non-latam"],
                      help="Which tasks to archive: 'latam' or 'non-latam'")
    p_ba.add_argument("--dry-run", action="store_true",
                      help="List tasks without archiving")

    # restore
    p_restore = sub.add_parser("restore", help="Restore (un-archive) a task")
    p_restore.add_argument("--task-id", required=True, help="Task ID")
    p_restore.add_argument("--engine", required=True, help="Engine name")
    p_restore.add_argument("--kerberos", required=True, help="User kerberos ID")

    # engines
    p_eng = sub.add_parser("engines", help="Test connectivity to known engines")

    # open
    p_open = sub.add_parser("open", help="Open eTask web UI in browser")
    p_open.add_argument("--piid", help="Process instance ID to open directly")

    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")
    args = parser.parse_args()
    _setup_out_file(args.out_file)

    commands = {
        "list": cmd_list,
        "inspect": cmd_inspect,
        "actions": cmd_actions,
        "task-actions": cmd_task_actions,
        "task-detail": cmd_task_detail,
        "create": cmd_create,
        "complete": cmd_complete,
        "cancel": cmd_cancel,
        "message": cmd_message,
        "search": cmd_search,
        "definitions": cmd_definitions,
        "archive": cmd_archive,
        "bulk-archive": cmd_bulk_archive,
        "restore": cmd_restore,
        "engines": cmd_engines,
        "open": cmd_open,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
