---
created: 2026-04-24
updated: 2026-04-24
tags: [meta, skill-usage, telemetry]
status: active
---

# Skill Usage Tracking

## Architecture

Two complementary mechanisms, no double-counting:

| Mechanism | Scope | How | Source tag |
|-----------|-------|-----|-----------|
| **Task auto-log** | 30 task-wrapped skills | `.cmd` wrapper appends to log after execution | `task` |
| **Manual log** | Non-task skills (ENGHUB, SLANG_CLEANUP, etc.) | Agent appends line to log file | `manual` |

## Log File

- **Path:** `workspace/tmp/skill_usage.log`
- **Format:** `YYYY-MM-DDTHH:MM:SS | SKILL_NAME | SOURCE`
- Append-only. Never truncate.

## Aggregation

Run `skills/_shared/usage_report.py` to print counts by skill:

```
python skills/_shared/usage_report.py
python skills/_shared/usage_report.py --since 2026-04-01
```

## Shared Logging Script

`skills/_shared/log_usage.cmd SKILL_NAME [SOURCE]` — appends one line to the log.

- SOURCE defaults to `task`. Use `manual` for non-task skills.
- Called automatically by all 30 task `.cmd` wrappers.

## Non-Task Skills (Manual Logging Required)

These skills have no task wrapper. Log manually by appending to the log file:

- SLANG_CLEANUP (agent-level workflow, no single executable to wrap)

## Anti-Patterns

- **Double counting:** Never manually log a task-wrapped skill — the `.cmd` handles it.
- **Truncation:** Never clear or overwrite the log file.
