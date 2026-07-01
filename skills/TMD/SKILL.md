---
name: TMD
description: "Manage Technology@MyDesk (TMD) tickets — list orders by kerberos, get order details, submit firewall delete requests. Use when user asks about TMD tickets, TMD orders, firewall requests, or technology@mydesk."
---

# TMD — Technology@MyDesk Ticket Management

> **Purpose:** Query and submit TMD service requests via the TMD REST API and Spine Gateway.

**Out of scope:** Approving/denying orders, managing tasks, TMAC server orders.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `TMD` |
| **Scope** | List, detail, search, and submit TMD orders |
| **Inputs** | Action type, order ID, kerberos, form fields |
| **Outputs** | JSON responses printed to stdout or saved to `workspace/tmp/` |
| **Authority** | Read + Write (GSSSO auth) |

## When to Use

- List the user's TMD tickets/orders.
- Get details of a specific TMD order by ID.
- Search the TMD catalog by keyword.
- Submit a "Delete Firewall" service request.
- Check status of a TMD order.

---

## Prerequisites

- GSSSO authentication (Kerberos ticket must be valid)
- Python 3.11+ with `requests` (available via `H:\venv311`)
- User kerberos from `memory/person/user.md`

## API Reference

### Base URLs

| Service | URL |
|---------|-----|
| TMD UI | `https://ui.tmd.site.gs.com/` |
| TMD REST | `https://tmd.web.gs.com/rest/` |
| TMD v1 API | `https://tmd.web.gs.com/api/rest/v1/` |
| Spine Gateway | `https://spine.ose.url.gs.com/spine-engine-service-web/rest/` |
| GSSSO Login | `https://authn.web.gs.com/desktopsso/Login` |
| Forms Metadata | `https://prod.forms.workflow.ep.site.gs.com/forms/metadata/` |
| WADL (full docs) | `https://tmd.web.gs.com/rest/application.wadl?detail=true` |

### Endpoints Used

| Action | Method | URL | Notes |
|--------|--------|-----|-------|
| **List items by kerberos** | GET | `/api/rest/v1/items?creatorKerberos={kerb}` | Returns all items created by user. Supports `status`, `createdDaysAgo`, `sortBy`, `sortOrder` query params. |
| **Order summary** | GET | `/rest/orderService/orderDetails/{orderId}` | Lightweight: orderId, status, items summary, creator |
| **Order detail** | GET | `/rest/orderDetail/{orderId}` | Full detail: creator info, watchers, items with attributes |
| **Order detail (v1)** | GET | `/rest/orders/{orderId}` | Returns order with links to items |
| **Items for order** | GET | `/api/rest/v1/items?orderId={orderId}` | All items in an order with full attributes |
| **Catalog keyword search** | GET | `/rest/tmdsearch/{keyword}` | Returns catalog products matching keyword. Supports `/{keyword}/{filterCategory}/{filterValue}` and `/{keyword}/{filterCategory}/{filterValue}/{offset}` for pagination. |
| **Submit order** | POST | `spine.ose.url.gs.com/.../tmdGatewayService/createTMDOrder` | Creates TMD order via Spine Gateway |

## Actions

### 1. List My Tickets

```
python skills/TMD/src/tmd.py list --kerberos nunesa
python skills/TMD/src/tmd.py list --kerberos nunesa --status Open
python skills/TMD/src/tmd.py list --kerberos nunesa --days 30
python skills/TMD/src/tmd.py list --kerberos nunesa --exclude-status Completed
python skills/TMD/src/tmd.py list --kerberos nunesa --format json
```

Additional filters: `--order-id`, `--service-code`, `--recipient`

### 2. Get Order Detail

```
python skills/TMD/src/tmd.py detail --order-id 22739166
python skills/TMD/src/tmd.py detail --order-id 22739166 --format json
```

### 3. Search TMD Catalog

```
python skills/TMD/src/tmd.py search --keyword firewall
python skills/TMD/src/tmd.py search --keyword firewall --format json
python skills/TMD/src/tmd.py search --keyword "email distribution" --filter-category creatorKerberos --filter-value nunesa
```

### 4. Submit Firewall Delete

```
python skills/TMD/src/tmd.py submit-firewall-delete \
  --kerberos nunesa \
  --title "Delete IP from firewall" \
  --description "Remove old IP no longer needed" \
  --region Americas \
  --priority Low \
  --ip 10.11.150.23 \
  --project no \
  --emergency no \
  --dry-run
```

Remove `--dry-run` to actually submit. Optional fields: `--app-name`, `--group-name`, `--watchers kerb1,kerb2`

## Execution

Run via:
```powershell
cmd /c "H:\all-languages-env.cmd >nul 2>&1 && H:\venv311\Scripts\python.exe skills/TMD/src/tmd.py <action> <args> 2>&1"
```

## Form Definitions

New form types can be added by fetching their metadata:
```
GET https://prod.forms.workflow.ep.site.gs.com/forms/metadata/{formId}
```

The form metadata contains: field names, types, required flags, dropdown options (`staticDataMap`), visibility rules (`dependencyRulesMap`), and the submission endpoint configuration.

### Known Form IDs

| Service | Form ID | Service Code | Product Code |
|---------|---------|-------------|--------------|
| Delete Firewall | `com.gs.ti.ose.spine.network.firewallDeleteIP` | `1a3af2ca-d402-42a4-9813-936975c1e179` | `f48e30c2-ce69-412e-9067-0ea1e04a1152` |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 Unauthorized | Kerberos ticket expired → `kdestroy && kinit` |
| 500 on submit | Check payload has `itemName`, `serviceCode`, `productCode` |
| Empty order list | Try removing `--status` filter, or increase `--days` |

## Task-Based Execution

**Task label:** `tmd` | **Args file:** `workspace/tmp/tmd_args.json`

Preferred. Write args JSON, then `run_task("tmd")`. CLI args pass through via `%*`.

## Links

- TMD API docs: `workspace/docs/tmd/` — cached API reference
- `GSSSO_AUTH` skill — authentication dependency
