---
name: PROCMON_JOBS
description: Query the Procmon ProcessList API to discover failed/running jobs by master, date, and process regex
---

# PROCMON_JOBS — Procmon Process List Query

> **Purpose:** Query the Procmon ProcessList API to discover failed/running jobs by master, date, and process regex. Dependency skill called by support skills (CPNL_SUPPORT, etc.).

**Out of scope:** Fetching log content (use PROCMON_LOGS), restarting or modifying processes.

## When to Use

- Called by `CPNL_SUPPORT` to identify failed overnight CPNL jobs.
- Called by other support skills to discover processes by master/date/regex.
- Not typically invoked directly by users.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `PROCMON_JOBS` |
| **Scope** | Query ProcessList API -- discover process statuses for a master/date/regex |
| **Inputs** | `--master`, `--process`, `RUN_DATE`, `--all-statuses` |
| **Outputs** | JSON `{ timestamp, run_date, count, processes: [...] }` to `workspace/tmp/procmon-jobs/` |
| **Authority** | Read-only (OIDC + Kerberos auth) |

## Prerequisites

- **Kerberos ticket** -- OIDC auth uses SPNEGO. If auth fails, tell the user to run `kinit`.
- **curl.exe** -- required for the 3-round-trip OIDC flow.
- **Python** -- resolve via PYTHON_PATH skill; `H:\venv\Scripts\python.exe` (stdlib only).

## Usage

```powershell
& python skills/PROCMON_JOBS/src/fetch_process_list.py [RUN_DATE] --master MASTER --process REGEX [--all-statuses]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `RUN_DATE` | No | T-1 business day | `YYYYMMDD` format |
| `--master` | **Yes** | -- | Procmon master (e.g. `eq3`, `eq`) |
| `--process` | **Yes** | -- | Process name regex (e.g. `^eqvol/NYC/risk/cpnl/`) |
| `--all-statuses` | No | off | Show all statuses; default shows Failed only |

**Output JSON** (stdout):
```json
{ "timestamp": "...", "run_date": "20260408", "failed_only": true, "count": 5, "processes": [...] }
```

Each process dict includes: `ProcessName`, `Status`, `ExitStatus`, `Err`, `Log` (plus 19 other fields).

Cookie jar cached at `workspace/tmp/procmon-jobs/procmon_cookies.txt`.

## Auth Flow

Three-round-trip OIDC via Kerberos/SPNEGO:
1. GET ProcessList -> 302 redirect + state cookie
2. `curl --negotiate` to PingFederate -> HTML form_post with auth code
3. POST code + state to `{base_url}/oidc_redirect` -> session cookies

Session cookies are cached and reused; re-auth only on expiry.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No OIDC redirect in step 1 | Procmon API unreachable | Check network / VPN |
| No auth code in step 2 | Kerberos ticket missing or expired | Run `kinit` |
| Session cookie not created | OIDC redirect mismatch | Delete cookie file and retry |
| Empty process list | Wrong `--master` or `--process` | Verify against Procmon UI |
| Stale auth error | Cached cookies expired mid-session | `del workspace\tmp\procmon-jobs\procmon_cookies.txt` |

## Task-Based Execution

**Task label:** `procmon-jobs` | **Args file:** `workspace/tmp/procmon_jobs_args.json`

Preferred. Write args JSON, then `run_task("procmon-jobs")`. CLI args pass through via `%*`.

## Links

- `PROCMON_LOGS` -- fetch `.out`/`.err` log content for a known process name (separate skill, SPNEGO)
