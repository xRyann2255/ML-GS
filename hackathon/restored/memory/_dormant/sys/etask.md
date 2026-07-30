---
created: 2026-04-15
updated: 2026-04-16
tags: [etask, workflow, api, reference, pact]
status: dormant
relates:
  - sys/enghub.md
---

# eTask — API Reference & Troubleshooting

## OPS Aggregation Gateway (task list)

| Item | Value |
|------|-------|
| **URL Pattern** | `https://gateway.workflow.ep.site.gs.com/aggr/{env}/rs/wis/v1/facetedpoll/{kerberos}` |
| **Auth** | GSSSO cookie (Kerberos/SPNEGO) |
| **Method** | `POST` with JSON body (selectedFacets, numberOfRecords, etc.) |
| **Returns** | Work item IDs + facet breakdowns (priority, status, due date, app, task type) |
| **Limitation** | No individual task detail enrichment — IDs + facets only |

## Gateway WFE Proxy (preferred for all operations)

The gateway at `gateway.workflow.ep.site.gs.com` proxies requests to WFE engines.
**This works from devtools for ALL environments** (prod, dev, qa) — no direct engine DNS needed.

| Item | Value |
|------|-------|
| **URL Pattern** | `https://gateway.workflow.ep.site.gs.com/wfe/{engine}` |
| **Auth** | GSSSO cookie |
| **Supports** | All WFE endpoints: `/tasks/...`, `/processinstances/...`, `/processdefinitions/...`, `/metadata/...` |
| **Engine names** | From faceted poll `--verbose` Type/Engine Ref facet: `TASK_TYPE#engine-name` |

Example engine names (from prod facets): `prod-11262-004`, `prod-55191-002`, `prod-ep-001`, `prod-ep-002`.

## API Endpoints (from OpenAPI spec)

### Process Instances

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/processinstances` | Find process instances (`?_queryType=KEY_VALUE&{field}={value}`) |
| `GET` | `/processinstances/{piid}` | Get process instance detail |
| `GET` | `/processinstances/{piid}/data` | Get process data |
| `GET` | `/processinstances/{piid}/activity` | Get activity log |
| `GET` | `/processinstances/{piid}/status` | Get process status |
| `GET` | `/processinstances/{piid}/actions/{userId}` | Get available actions for user |
| `POST` | `/processinstances/{piid}/message` | Send message to process |
| `POST` | `/processinstances/{piid}/delegate` | Delegate process |
| `POST` | `/processinstances/{piid}/comments` | Add comment |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/tasks/{taskId}` | Get task details |
| `GET` | `/tasks/{taskId}/actions/{userId}` | Get available task actions |
| `POST` | `/tasks/{taskId}/complete` | Complete a task |
| `POST` | `/tasks/{taskId}/claim` | Claim a task |
| `POST` | `/tasks/{taskId}/release` | Release a task |
| `POST` | `/tasks/{taskId}/delegate` | Delegate a task |
| `POST` | `/tasks/{taskId}/tags/add` | Add tags (used for archive) |
| `POST` | `/tasks/{taskId}/tags/remove` | Remove tags (used for restore/un-archive) |

### Process Definitions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/processdefinitions/{processId}` | Get process definition |
| `POST` | `/processdefinitions/{processId}` | Start new process instance |
| `GET` | `/management/processdefinitions/active` | List active definitions |

## Common Payload Patterns

### Create Task Payload

The `domainObject` structure varies by BPMN process. Common fields:

```json
{
    "domainObject": {
        "uid": "unique-id",
        "category": "task-category",
        "shortSummary": "Task title",
        "environmentDetails": {
            "supportResponsibility": "TEAM_NAME",
            "supportTeam": "team"
        },
        "formInfo": {
            "formId": "/path/to/form",
            "submitterKerberos": "kerberos",
            "workflowConfig": {
                "processId": "com.gs.designer.kata.processName",
                "stack": "EP"
            }
        }
    },
    "businessKey": "optional-business-key",
    "userId": "kerberos-or-system-id"
}
```

### Complete Task Body

```json
{
    "comment": {
        "comment": "Completion comment",
        "categories": null,
        "categorized": false
    },
    "params": {},
    "reasonCode": "CONFIRMED",
    "userId": "kerberos"
}
```

### Message Body (Cancel)

```json
{
    "userId": "kerberos",
    "messageName": "com.gs.designer.kata.processName.cancel_work"
}
```

### Message Body (Interim Update)

```json
{
    "userId": "kerberos",
    "messageName": "com.gs.designer.kata.processName.interim_update",
    "messagePayload": {
        "Send_Message": {
            "Interim_Response": "<p>Your message here</p>"
        }
    }
}
```

### Archive/Restore Tag Body

Archive is a tag operation, not a completion. The `@etask|archive|{kerberos}` tag hides the task from the user's inbox.

```json
{
    "userId": "kerberos",
    "tags": ["@etask|archive|kerberos"]
}
```

- **Archive:** `POST /tasks/{taskId}/tags/add` → HTTP 204 on success
- **Restore:** `POST /tasks/{taskId}/tags/remove` → HTTP 204 on success

## Person Location Lookup

PACT task process data includes `deptName` and `kerberos`, but **department name does NOT reliably indicate office location** (e.g. "EQ Flow Vol Eng - US" or "Eqs Securitised Deriv Strats" can have people in São Paulo).

**Always use EPSSP DirGet** to determine a person's actual office:

```
GET https://www.epssp.site.gs.com/ssps/ProdSource/Dirget?K={kerberos}
Auth: GSSSO cookie
```

Returns HTML. Extract location from: `<DT>Location</DT>` → next `<A>` tag text, e.g.:
- `Sao Paulo, 700M/017, 314A02 (Brazil, Americas)`
- `London, 25SL/004, 626A02 (United Kingdom, EMEA)`
- `New York, 200W/004, 316A07 (United States, Americas)`

Regex: `<DT>Location</DT>.*?<A[^>]*>([^<]+)</A>` (with `re.DOTALL`).

The parenthetical suffix `(Country, Region)` is the most reliable filter field.

**AppBank tasks:** Filter by `extensionData.deptName == "AppBank"`, NOT by `extensionData.appBankManaged != "NONE"`. Many non-AppBank departments (e.g. "EQ Flow Vol Eng - US", "Brazil Operations Technology") have sessions with `appBankManaged=ALL` because the accessed apps happen to be AppBank-managed. The department owns the review responsibility, not the app classification.

## PACT Work Item Fields (OPS)

`GET {ops}/facetedpoll/workitems/{taskId}` returns `extensionData` with:

| Field | Example | Use |
|-------|---------|-----|
| `kerberos` | figuvi | Reviewed user's kerberos |
| `deptName` | Eqs Strats | Reviewed user's department |
| `appBankManaged` | NONE / PARTIAL / ALL | Whether session apps are AppBank-managed |
| `appIds` | aid-64434 | AppBank application IDs |
| `hostname` | N/A | Host accessed |
| `reason` | Transaction in ProductionDb... | Session reason |
| `sessionId` | 643dcea5-... | PACT session UUID |
| `startDate` / `endDate` | ISO datetime | Session time window |
| `duration` | 125 | Session duration (minutes) |
| `actionContext` | JSON array | NOT a flat dict — see below |

**`actionContext`** is a JSON-encoded array, not a dict:
```json
["Change_Related_Review", {"kerberos": "...", "changeRelatedActionValid": "true", ...}]
```
First element is a string label, second is the context object. The `kerberos` for filtering is in `extensionData.kerberos` (top-level), not inside `actionContext`.

## PACT Task Completion (API)

PACT BPMN tasks can be completed via WFE REST API when the payload is correct:

```
POST {gateway}/wfe/{engine}/tasks/{taskId}/complete
Header: If-Match: {workItemVersion}
Header: Cookie: GSSSO={cookie}

{
    "userId": "{kerberos}",
    "reasonCode": "INCIDENT_RELATED",
    "comment": {"comment": "...", "categorized": false},
    "params": {
        "confirm_incident_related_form": {"comment": "..."}
    }
}
```

**Critical:** `reasonCode` must be the BPMN attribute (`INCIDENT_RELATED`), NOT the action name (`confirm_incident_related`). Form data goes in `params` under the `formId` key.

| Action Name | reasonCode | Form ID (in params) |
|-------------|-----------|---------------------|
| `confirm_incident_related` | `INCIDENT_RELATED` | `confirm_incident_related_form` |
| `change_related_complete` | `CHANGE_RELATED` | `change_related_comment_form` |
| `inappropriate_access_complete` | `POSSIBLY_INAPPROPRIATE` | `possible_inappropriate_access_form` |

**Entitlement:** User must be in `potentialAssignees` (from routing rules). Cannot review own session.

### PACT Lease Review (`com.gs.ep.workflow.PactLeaseReview`)

Lease tasks use a different BPMN process and different reasonCodes:

| Action Name | reasonCode | Display Name | Task Type | Comment |
|-------------|-----------|--------------|-----------|---------|
| `complete_task` | `approve` | Approve | `PACT_LEASE_REVIEW_TASK` | Approves the lease request |
| `deny_lease` | `deny` | Deny | `PACT_LEASE_REVIEW_TASK` | Denies the lease request |
| `revoke_lease` | `revoke` | Revoke | `PACT_LEASE_REVOKE_TASK` | Revokes an already-running lease (optional task, auto-expires at lease end) |
| `complete_task` | `release` | Release | (lease management) | Releases a lease management task |

**No claim required** — lease tasks can be completed directly. No `params` or form data needed; `commentType="NOT_REQUIRED"`.

**BPMN source:** GitLab `iam/pact/pact-next-workflow` → `bpmn/com.gs.ep.workflow.PactLeaseReview.bpmn` (project ID 85172)

**Get full work item** (with `wfEngineReference`): `GET {ops}/facetedpoll/workitems/{taskId}`

**BPMN source (session reviews):** GitLab `iam/pact/pact-next-workflow` → `bpmn/com.gs.ep.workflow.PactAccessReview.bpmn`

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 Unauthorized | GSSSO cookie expired — script auto-obtains it, retry |
| 404 on process instance | Wrong engine — the PIID lives on a different engine |
| 404 on task via gateway | Wrong engine name — use `list --verbose` to find Type/Engine Ref |
| DNS resolution failure on direct engine | Expected from devtools — use gateway proxy (default) |
| 503 on aggregation URL | Gateway healthy, but engine-specific endpoint may route wrong |
| Empty search results | Try different engines; processes are sharded across engines |
| Connection refused on :11101 | Direct engine URL — use gateway proxy instead |

## Direct WFE Engine (fallback)

| Item | Value |
|------|-------|
| **URL Pattern** | `https://{engine}.engine.workflow.ep.site.gs.com:11101` |
| **OpenAPI** | `https://{engine}.engine.workflow.ep.site.gs.com:11101/openapi.json` |
| **Limitation** | Prod engines do NOT resolve from devtools — use gateway proxy instead |

## eTask Web UI

| Environment | URL |
|-------------|-----|
| **Prod** | `https://etask.gs.com` |
| **Dev** | `https://dev.etask.gs.com` |
| **QA** | `https://qa.etask.gs.com` |

## Network Constraints

From **devtools** (H: drive environment):
- **Gateway proxy** (`gateway.workflow.ep.site.gs.com/wfe/{engine}`) → **works for ALL environments** (prod, dev, qa)
- **Direct engine** (`{engine}.engine.workflow.ep.site.gs.com:11101`) → DNS does NOT resolve for prod engines
- **OPS aggregation** (`gateway.workflow.ep.site.gs.com/aggr/prod/...`) → works for faceted poll/task list

Always use the gateway proxy (default in `etask.py`).

## Links

- [eTask EngHub Docs](https://enghub.gs.com/workflow-platform/etask)
- [eTask Web UI](https://etask.gs.com/)
- [Workflow Designer](https://developer.workflow.site.gs.com/)
- [eTask Using Guide](https://enghub.gs.com/workflow-platform/etask/docs/etask-using)
- [eTask Features](https://enghub.gs.com/workflow-platform/etask/docs/etask-features-and-customization)
- [eTask Workspaces](https://enghub.gs.com/workflow-platform/etask/docs/etask-workspaces)
- [eTask Search](https://enghub.gs.com/workflow-platform/etask/docs/etask-search-for-tasks)

## Reference Implementations

These GitLab repos have working eTask client code:

| Repo | File | Language | Notes |
|------|------|----------|-------|
| `prime/sl-production-engineering/sl-genie` | `genie_workspace/interfaces/etask.py` | Python | Full CRUD — create, inspect, complete, cancel, message, search |
| `derun/sky/skyfinance-tools` | `common/etask.py` | Python | SIF-based cloud client with GSSSO |
| `fineng/assets-liability-management/signoff` | `server/signoff/microservice/computation/etask.py` | Python | Simple create+send pattern |
| `developer-experience/workflow/etask-server` | (multiple) | TypeScript | Official eTask UI server |
| `eq-tech/core-post-trade-platforms/xact-server` | `src/main/resources/apiSpec/etask.yaml` | OpenAPI | Eq-Tech eTask endpoints |
