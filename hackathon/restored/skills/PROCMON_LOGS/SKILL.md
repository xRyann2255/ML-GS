---
name: PROCMON_LOGS
description: Fetch stdout/stderr logs from Procmon for a given process
---

# PROCMON_LOGS — Fetch Process Monitor Logs

> **Purpose:** Fetch stdout/stderr logs from Procmon for a given process, date, and master. Pulls logs into `workspace/tmp/` for analysis.

**Out of scope:** Restarting processes, modifying Procmon configuration, or real-time log tailing.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `PROCMON_LOGS` |
| **Scope** | Download stdout/stderr logs for Procmon-managed processes |
| **Inputs** | Process name, optional date/master/log type |
| **Outputs** | Log files in `workspace/tmp/procmon-logs/` |
| **Authority** | Read-only (SPNEGO auth) |

## When to Use

- Diagnose production process failures or unexpected behavior.
- Investigate error logs for scheduled jobs.
- Retrieve historical logs for a specific date.

---

Fetch stdout/stderr logs from Procmon for a given process, date, and master.

## Prerequisites

**Kerberos ticket** — log server uses SPNEGO. `klist -s || echo "Run kinit"`

## Usage

```bash
skills/PROCMON_LOGS/src/fetch.sh <PROC_NAME> [DATE] [MASTER] [LOG_TYPE] [TAIL_LINES]
```

| Arg | Req | Default | Description |
| --- | --- | --- | --- |
| `PROC_NAME` | Yes | — | Full process path (e.g. `pipgit/ldn/intra/ise/prod/RFQ_ISE_Workflow_Server_SDS_Clone~0`) |
| `DATE` | No | today | `yyyymmdd` |
| `MASTER` | No | `eq` | Procmon master |
| `LOG_TYPE` | No | `both` | `out`, `err`, or `both` |
| `TAIL_LINES` | No | — | Keep last N lines only |

Output: `workspace/tmp/procmon-logs/<sanitized_name>-<date>.{out,err}`

## URL Pattern

```
http://{master}-log.procmon.services.gs.com:10702/procmonlogs/log/master/{master}/{yyyymmdd}/procs/{proc_name}.{out|err}
```

## Analysis Tips

- Start with `.err` log — errors surface problems faster
- Use `grep -i 'error\|exception\|fail\|warn'`
- Use `tail` — end of log has most recent activity
- Don't read entire large files — use targeted `read_file` with line ranges

## Finding the Process Name

- **GET_ISSUANCE_TASKS** `Stripe` → `pipgit/ldn/intra/ise/prod/RFQ_ISE_Workflow_Server_SDS_Clone~<Stripe>`
- **Procmon UI** — process name in URL/list

Common masters: `eq` (Equities)

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No logs returned | Wrong process name or date | Verify process name in Procmon UI |
| 404 on log fetch | Process not run on that date | Check valid date range |

## Links

- memory/ref/devtools.md — devtools environment (process runtime)
