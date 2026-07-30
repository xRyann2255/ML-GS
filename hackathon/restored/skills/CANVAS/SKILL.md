---
name: CANVAS
description: Query the Canvas / AppDir 2.0 deployment API for infrastructure inventory — hosts, resources, beans, families, applications, and deployed applications (DIDs)
---

# CANVAS — Infrastructure Deployment API

> **Purpose:** Query the Canvas / AppDir 2.0 REST API (Sky Gateway and Canvas backends) for applications, deployments, hosts, resources, beans, system accounts, and org structure. Use whenever the user asks about Canvas deployments, server nodes, infrastructure inventory, deployment topology, host counts, core/memory sizing, DC vs EC classification, or mentions a DID.

**Out of scope:** Modifying AppDir records, provisioning deployments, or managing host configurations.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `CANVAS` |
| **Scope** | Read-only Canvas / AppDir 2.0 API queries (Sky Gateway + Canvas) |
| **Inputs** | Entity type, lookup key (DID, app name, hostname) |
| **Outputs** | JSON responses in `workspace/tmp/` |
| **Authority** | Read-only (GSSSO auth) |

## When to Use

- Look up deployment details by DID or name.
- Find hosts, system accounts, or org structure for an application.
- Investigate infrastructure topology or BU/family hierarchy.

---

Query AppDir REST API for applications, deployments, hosts, system accounts, and org structure.

> **Memory:** `memory/_dormant/ref/gssso-auth.md` (GSSSO cookie auth), `memory/ref/python-setup.md` (Python env).

## Connection

| Field | Value |
| --- | --- |
| Sky Gateway | `https://prod.gateway.sky.site.gs.com/skygateway/appdir2sg_prod/v1/appdir/api` (cloud-only) |
| Canvas Backend | `https://api.canvas.site.gs.com:7443/v1` (desktop-accessible, GSSSO auth) |
| Auth | GSSSO cookie (via `GSSSO_AUTH` skill) |
| Canvas GSRN | `gsrn.gscloud.apimgmt.publisher.43378.appdir2sg_prod_v1` |

## Canvas Backend Endpoints (Desktop-Accessible)

### Deployment

| Endpoint | Description |
| --- | --- |
| `/hierarchies/did-{did}` | **Full org chain** (BU→SBU→Family→App→DID) in one call — best starting point for unknown DIDs |
| `/deployed-application/{did}` | Summary: name, status, app/family/BU |
| `/deployments/{did}` | Full: configs, topologies, resources (servers in `data.model.resources[]`) |
| `/deployments/{did}/instantiated` | Full deployment model (topologies, availability groups) |
| `/deployments/{did}/hostTypes` | Hosts with type (VM/Physical) |
| `/deployments/{did}/hypervisors` | Hypervisor details |
| `/deployments/{did}/beans` | Bean IDs used by this deployment |
| `/deployments/{did}/legacynodes` | Legacy node list |
| `/deployed-application/{did}/locations` | Data center locations |
| `/deployed-application/{did}/systemAccounts` | System accounts |
| `/deployed-application/{did}/classifications` | Classifications |
| `/deployed-application/{did}/windows?type={type}` | Maintenance windows |
| `/deployments/{did}/history?maxresults=1000` | Deployment history |
| `/certificates/{did}` | TLS certificates |
| `/gscloud/audit/did/{did}?limit=100` | Audit trail |
| `/storages/by-deployment/{did}` | Storage allocations |

### Beans (Resource Templates)

| Endpoint | Description |
| --- | --- |
| `/beans/{id1},{id2},...,{idN}/versions` | Bean definitions — canonical templates for resource types |

Resources inherit attributes (especially `VMShape`) from their bean. If a resource's `attributes.VMShape` is absent, **fetch the bean** via `data["{id}"].beanDetails.bean.attributes`.

### Infrastructure & RBAC

| Endpoint | Description |
| --- | --- |
| `/hosts/{hostname}` | Host details: OS, location, owning deployment, associated deployments |
| `/hosts/{hostname}/status` | Host operational status (placement ping) |
| `/entitlements/deployment/{did}` | User RBAC permissions for a DID |
| `/appdir-entities/new/for-current-user` | Current user's family assignments and roles |
| `/lookup/...` | Reference data (regions, instance types, patching windows) |

### Org Structure

| Endpoint | Description |
| --- | --- |
| `/businessunits` | All BUs |
| `/subbusinessunits/by-buid/{buId}` | Sub-BUs for a BU |
| `/families/by-sbuid/{sbuId}` | Families for a Sub-BU |
| `/applications/by-familyid/{fId}` | Apps for a Family |
| `/deployed-application/by-appid/{appId}` | Deployments for an App |
| `/deployed-application/by-name/{name}` | Search deployments by name |

### Other

| Endpoint | Description |
| --- | --- |
| `/system-account/search/{text}` | Search system accounts |
| `/api-definitions/{gsrn}` | API definition |
| `/api-definitions/{gsrn}/openapi` | OpenAPI 3.0 spec |

## Helper Script

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

```powershell
PYTHON skills/CANVAS/src/query.py <entity> <lookup> [--status ACTIVE] [--output file.json]
```

### Common Examples

```powershell
python query.py did 155218                    # Deployment summary (Canvas)
python query.py did 155218 --full             # Full deployment details
python query.py did 155218 --hosts            # Hosts
python query.py did 155218 --classify         # Resources with DC/EC + VMShape (resolves beans)
python query.py did 155218 --sysaccounts      # System accounts
python query.py did 155218 --storages         # Storage allocations
python query.py did 155218 --entitlements     # User RBAC permissions
python query.py hierarchy 155218              # Full org chain (BU->SBU->Family->App->DID)
python query.py beans 12345,67890            # Bean definitions (resource templates)
python query.py roles                        # Current user's Canvas family roles
python query.py host-status d176618.ny.corp.gs.com  # Host operational status
python query.py host-info k8sbm-1497039.k8s.gs.com  # Host details + owning app (works for K8s nodes)
python query.py search-did "Vol Strats"        # Search by name
python query.py businessunits                 # All BUs
python query.py application name "SecDb"      # App by name (Sky Gateway)
python query.py host hostname "d176618.ny.corp.gs.com"  # Host lookup (Sky GW)
python query.py tag prefix "eq-strategy"      # Tag search (Sky GW)
```

## Entity Hierarchy

`BusinessUnit → SubBusinessUnit → Family → Application → Deployment → {Hosts, SystemAccounts, Classifications, BCP}`

## Sky Gateway Endpoints (Cloud-Only)

### application
`id {id}`, `ext {id}`, `name {name}`, `deployments {appId}`, `classifications {appId}`

### deployment
`ext {id}`, `name {name}`, `hosts {did}`, `systemaccounts {did}`, `classifications {did}`

### host
`hostname {hostname}`

### family
`id {id}`, `applications {id}`

### businessunit / subbusinessunit
`id {id}`, `subbusinessunits {id}` / `families {id}`

### bcp / tag / tagref
`bcp id {id}` | `tag tag {t}`, `prefix {p}` | `tagref tag {t}`, `entity {type} {id}`

`entityType`: `BUSINESS_UNIT`, `SUB_BUSINESS_UNIT`, `FAMILY`, `APPLICATION`, `DEPLOYMENT`

## Key Schemas

- **Application**: `id`, `name`, `description`, `statusType`, `familyId`
- **ExtApplication**: adds BU/SubBU/Family names and IDs
- **Deployment**: `id`, `name`, `statusType`, `applicationId`, `environmentType` (PRODUCTION/NON_PRODUCTION)
- **ExtDeployment**: adds app name, BU/family info, classifications[], hosts[], systemAccounts[]
- **Host**: `deploymentId`, `hostname`, `auid`, `hostOwnership`, `statusType`
- **SystemAccount**: `deploymentId`, `name`, `domain`, `platform` (UNIX/WINDOWS), `accountType`
- **Resource** (in `data.model.resources[]`): `id`, `guid`, `name` (hostname), `product.id` (bean ID), `product.name` (bean name), `attributes.Elasticity`, `attributes.VMShape`, `attributes.VMOS`

### Resource Classification

| Attribute | Field | Values |
| --- | --- | --- |
| DC vs EC | `attributes.Elasticity.isElastic` | `"False"` = DC (data center), `"True"` = EC (elastic cloud) |
| VM sizing | `attributes.VMShape` | `core`, `memory`, `size` (e.g. `Jumbo_HighMem`), `storage` |
| OS | `attributes.VMOS` | OS image and update strategy |

> If `VMShape` is absent on a resource, it's inherited from the bean — fetch via `/beans/{product.id}/versions`.

### Role-Checking Pattern

To verify a user has a specific Canvas role (e.g., for authorization gates):

```
GET /v1/appdir-entities/new/for-current-user
```

Response contains `data[].familyId` and `data[].assignments[].rmsResponsibilityCode`. Match both family ID and responsibility code to authorize.

Example: SecDBA checks `familyId == 133257` + `rmsResponsibilityCode == "TECHNOLOGY_ROLES.PRODUCTION_ENGINEER.RESOLVE_OPERATIONAL_ISSUES"`.

Availability: **[HA]** = 99.9%, **[SA]** = 99.5%. Canvas endpoints are HA.

## Task-Based Execution (Preferred)

Use `run_task` with the predefined `canvas` task instead of `run_in_terminal` to avoid the Copilot "Allow" prompt.

### Workflow

1. **Write args JSON** to `workspace/tmp/canvas_args.json`:

```json
{
    "command": "did",
    "args": ["155218", "--classify"],
    "out_file": "workspace/tmp/canvas_out.json"
}
```

2. **Launch via predefined VS Code Task** (no Allow):

```
run_task("canvas", workspaceFolder: "h:\ml-vol-estimator")
```

The task reads `workspace/tmp/canvas_args.json` automatically.

3. **Read results** from `out_file` path.

### Args JSON Format

| Key | Type | Description |
|-----|------|-------------|
| `command` | string | Subcommand: `did`, `search-did`, `hierarchy`, `beans`, `roles`, `host-info`, `host-status`, `org`, `businessunits`, `sky`, `info` |
| `args` | string[] | Positional + flag arguments for the subcommand |
| `out_file` | string | (Optional) Write JSON output to this path instead of stdout |

### Examples

```json
{"command": "did", "args": ["155218", "--hosts"], "out_file": "workspace/tmp/canvas_out.json"}
{"command": "did", "args": ["155218", "--classify"], "out_file": "workspace/tmp/canvas_out.json"}
{"command": "hierarchy", "args": ["155218"], "out_file": "workspace/tmp/canvas_out.json"}
{"command": "search-did", "args": ["Vol Strats"], "out_file": "workspace/tmp/canvas_out.json"}
{"command": "host-info", "args": ["k8sbm-1497039.k8s.gs.com"], "out_file": "workspace/tmp/canvas_out.json"}
{"command": "host-status", "args": ["dcnds0309862.dc.gs.com"], "out_file": "workspace/tmp/canvas_out.json"}
{"command": "beans", "args": ["12345,67890"], "out_file": "workspace/tmp/canvas_out.json"}
```

### Step Reference

| Step | Tool | Allow prompt? |
|------|------|---------------|
| Write args JSON | `create_file` / `replace_string_in_file` | No |
| Launch task | `run_task` | No |
| Read output | `read_file` | No |

## Troubleshooting

| Problem | Fix |
| --- | --- |
| 401 Unauthorized | GSSSO expired — re-obtain via `GSSSO_AUTH` |
| 404 / empty response | Wrong entity ID or `--status` filter excludes it |
| DNS not resolved | Sky Gateway = cloud-only; use `did` subcommand (Canvas) from desktop |
| OpenAPI spec | `skills/CANVAS/src/openapi.json` (49KB) |

## Links

- memory/_dormant/ref/gssso-auth.md — GSSSO cookie auth
- memory/ref/python-setup.md — Python env setup
- memory/_dormant/sys/canvas-appdir.md — Canvas / AppDir platform reference
