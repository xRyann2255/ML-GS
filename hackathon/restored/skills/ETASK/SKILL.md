---
name: ETASK
description: Query and manage eTask workflow tasks via the Workflow Engine REST API — inspect, create, complete, cancel, search, and message tasks
---

# ETASK — eTask Workflow Task Management

> **Purpose:** Interact with the eTask Workflow Engine REST API to list, inspect, create, complete, cancel, search, and message workflow tasks. Uses GSSSO authentication with both the OPS aggregation gateway (task list) and direct WFE engine endpoints (task operations).

**Out of scope:** BPMN design, form customization, Workflow Designer configuration, individual task detail enrichment (gateway only returns IDs + facet summaries — use etask.gs.com for full detail view).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `ETASK` |
| **Scope** | Read + write eTask Workflow Engine REST API |
| **Inputs** | Command, engine name, process/task IDs, kerberos, payload |
| **Outputs** | Console summary + JSON in `workspace/tmp/etask-*.json` |
| **Authority** | Read + limited write (create tasks, complete tasks, send messages) |

## When to Use

- **List open tasks** across all engines (aggregated view with facet breakdowns by app, priority, due date).
- **Bulk-archive** tasks by app + location region (e.g., archive all non-latam PACT reviews).
- Inspect a specific task or process instance (details, data, activity, actions).
- Create a new eTask via a BPMN process definition.
- Complete or cancel an eTask.
- Search for processes by key-value index fields on a specific engine.
- Send messages (interim updates, cancel) to a process.
- List process definitions on an engine.
- Open eTask web UI for full task detail view.

Do **not** use for:
- Individual task detail enrichment (names, descriptions, form data) — the gateway API returns IDs + facet summaries only. Use `open` command for the browser view.
- Slang-based workflows → use SecDB/Slang skills.
- Pipeline/job inspection → use **GITLAB_PIPELINES**.
- AppDir / Canvas lookups → use **CANVAS**.

## Prerequisites

- **GSSSO cookie** — obtained via Windows integrated auth (Kerberos/SPNEGO).
- **Engine name** — e.g., `autint1-001`, `autprd1-001`. Found in eTask task details.
- **Python 3.11+** with `requests` (available via `H:\venv311` or `uv run`).

## Architecture

See memory/_dormant/sys/etask.md for gateway URLs, WFE proxy, direct engine access, engine-name discovery, and eTask web UI links.

## API Endpoints, Payloads & Reference

See `memory/_dormant/sys/etask.md` for full API endpoint tables, payload patterns, troubleshooting, network constraints, links, and reference implementations.

## CList Open Tasks (Aggregated)

```bash
uv run python skills/ETASK/src/etask.py list --kerberos jdoe                    # All open + in-progress
uv run python skills/ETASK/src/etask.py list --kerberos jdoe --app "Auto Refactors"  # Filter by app
uv run python skills/ETASK/src/etask.py list --kerberos jdoe --status OPEN      # Only OPEN
uv run python skills/ETASK/src/etask.py list --kerberos jdoe --priority 4       # Only Critical
uv run python skills/ETASK/src/etask.py list --kerberos jdoe --verbose          # Include IDs and engine refs
```

Returns task counts broken down by status, priority, due date, application, and task type.

### LI Commands

### Inspect a Process Instance

```bash
uv run python skills/ETASK/src/etask.py inspect --piid <piid> --engine autint1-001
uv run python skills/ETASK/src/etask.py inspect --piid <piid> --engine autint1-001 --data      # Include data
uv run python skills/ETASK/src/etask.py inspect --piid <piid> --engine autint1-001 --activity   # Activity log
```

### Get Actions

```bash
uv run python skills/ETASK/src/etask.py actions --piid <piid> --engine autint1-001 --kerberos jdoe
uv run python skills/ETASK/src/etask.py task-actions --task-id <taskId> --engine autint1-001 --kerberos jdoe
```

### Get Task Details

```bash
uv run python skills/ETASK/src/etask.py task-detail --task-id <taskId> --engine autint1-001
```

### Create a Task

```bash
uv run python skills/ETASK/src/etask.py create --engine autint1-001 --bpmn <process-definition-id> --payload-file workspace/tmp/etask-payload.json
```

### Approve / Reject / Complete a Task

First, discover the available actions for a task:

```bash
uv run python skills/ETASK/src/etask.py task-actions --task-id <taskId> --engine <engine> --kerberos jdoe
```

This returns action names (e.g., `approve_tmd`, `reject_tmd`, `confirm_incident_related`).
Then complete with the appropriate **reason code**:

```bash
# Standard tasks — action name IS the reason code
uv run python skills/ETASK/src/etask.py complete --task-id <taskId> --engine <engine> --kerberos jdoe --reason approve_tmd
uv run python skills/ETASK/src/etask.py complete --task-id <taskId> --engine <engine> --kerberos jdoe --reason CONFIRMED

# PACT tasks — action name != reason code. Use BPMN reasonCode + --params-file for form data
uv run python skills/ETASK/src/etask.py complete --task-id <taskId> --engine <engine> --kerberos jdoe --reason INCIDENT_RELATED --params-file workspace/tmp/pact-params.json
```

**PACT reason code mapping** (action name → `--reason`):
- `confirm_incident_related` → `INCIDENT_RELATED` (form: `confirm_incident_related_form`)
- `change_related_complete` → `CHANGE_RELATED` (form: `change_related_comment_form`)
- `inappropriate_access_complete` → `POSSIBLY_INAPPROPRIATE` (form: `possible_inappropriate_access_form`)

PACT `--params-file` JSON example (`workspace/tmp/pact-params.json`):
```json
{"confirm_incident_related_form": {"comment": "Daily reg reporting"}}
```

**`--if-match`** (optional): Work item version for the `If-Match` header. Auto-fetched from OPS if omitted.

### Cancel a Process

```bash
uv run python skills/ETASK/src/etask.py cancel --piid <piid> --engine autint1-001 --kerberos jdoe --message-name "com.gs.designer.kata.process.cancel_work"
```

### Send a Message

```bash
uv run python skills/ETASK/src/etask.py message --piid <piid> --engine autint1-001 --kerberos jdoe --message-name "interim_update" --comment "Status update"
```

### Search by Key-Value

```bash
uv run python skills/ETASK/src/etask.py search --engine autint1-001 --field individual --value jdoe
```

### List Process Definitions

```bash
uv run python skills/ETASK/src/etask.py definitions --engine autint1-001
uv run python skills/ETASK/src/etask.py definitions --engine autint1-001 --bpmn com.gs.designer.kata.myProcess
```

### Test Engine Connectivity

```bash
uv run python skills/ETASK/src/etask.py --env dev engines    # Test dev engines
uv run python skills/ETASK/src/etask.py --env prod engines   # Test prod engines
```

### Archive a Task

Archive hides a task from the inbox without completing or rejecting it. Uses the tag system (`@etask|archive|kerberos`).

```bash
uv run python skills/ETASK/src/etask.py archive --task-id <taskId> --engine <engine> --kerberos jdoe
```

### Bulk-Archive by Location Region

Bulk-archive tasks filtered by application and reviewed user's office location. Uses DirGet to resolve each user's country, then archives tasks where the user is outside (or inside) the specified region.

Supported regions: `latam` (Brazil, Argentina, Chile, Colombia, Mexico, Peru), `non-latam` (everything else).

```bash
# Dry run — show what would be archived, without archiving
uv run python skills/ETASK/src/etask.py bulk-archive --kerberos jdoe --app "PACT Next" --engine prod-ep-002 --region non-latam --dry-run

# Archive all non-latam PACT tasks
uv run python skills/ETASK/src/etask.py bulk-archive --kerberos jdoe --app "PACT Next" --engine prod-ep-002 --region non-latam

# Archive all latam tasks for a different app
uv run python skills/ETASK/src/etask.py bulk-archive --kerberos jdoe --app "Auto Refactors" --engine prod-55191-002 --region latam
```

The command:
1. Fetches all open/in-progress tasks for the specified `--app`
2. For each task, fetches work item detail from OPS to get the reviewed user's kerberos
3. Resolves office location via EPSSP DirGet
4. Archives tasks matching the `--region` filter
5. Saves a JSON report to `workspace/tmp/etask-bulk-archive-*.json`

**Finding the engine:** Use `list --verbose` → Type/Engine Ref facet to find the engine for your app's task type.

### Restore (Un-archive) a Task

```bash
uv run python skills/ETASK/src/etask.py restore --task-id <taskId> --engine <engine> --kerberos jdoe
```

### Open eTask Web UI

```bash
uv run python skills/ETASK/src/etask.py open                          # Open etask.gs.com
uv run python skills/ETASK/src/etask.py open --piid <piid>            # Open specific task
uv run python skills/ETASK/src/etask.py --env dev open                # Open dev UI
```

## Output

- **Console:** Formatted summary with task IDs, statuses, dates, and actions.
- **JSON:** Raw results saved to `workspace/tmp/etask-{command}-{timestamp}.json`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 Unauthorized | GSSSO cookie expired | Re-authenticate via GSSSO skill |
| Empty task list | Wrong kerberos or no open tasks | Verify kerberos ID, try without filters |
| Engine connection refused | Wrong engine name or network | Use gateway proxy (default); engine names come from `--verbose` facets, not `autprd*` pattern |
| DNS resolution failure on direct engine | Direct engine URLs don't resolve from devtools | Gateway proxy is the default — this shouldn't happen unless `use_gateway=False` |

## Task-Based Execution

**Task label:** `etask` | **Args file:** `workspace/tmp/etask_args.json`

Preferred. Write args JSON, then `run_task("etask")`. CLI args pass through via `%*`.

## Links

- memory/_dormant/sys/etask.md — eTask API reference & troubleshooting
- memory/_dormant/ref/gssso-auth.md — GSSSO cookie auth
