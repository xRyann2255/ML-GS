---
name: SYMPHONY
description: "Read messages from Symphony chat rooms and search rooms via the GS Bot Framework API Bridge. Read-only — no write operations without human approval."
---

# SYMPHONY — Symphony Chat Reader

> **Purpose:** Read messages from Symphony chat rooms, search rooms, and retrieve room info via the GS Bot Framework API Bridge 2.0.

**Out of scope:** Sending messages (requires human approval), bot registration, webhook management.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SYMPHONY` |
| **Scope** | Search rooms, read messages, get room info/members |
| **Inputs** | Room name or stream ID, optional time window |
| **Tool** | `skills/SYMPHONY/src/symphony.py` |
| **Outputs** | JSON files in `workspace/tmp/symphony-*.json` |
| **Auth** | GSSSO via `gs_auth` (Kerberos → SSO → Bot Framework) |
| **Authority** | Read-only |

## When to Use

- Read latest messages from a Symphony chat room.
- Search for a Symphony room by name.
- Get room info, metadata, or member list.
- Find a stream ID for a known room.

---

## Prerequisites

- **`gs-auth` package:** `pip install --trusted-host pypi.site.gs.com --index-url https://pypi.site.gs.com/simple gs-auth`
- **`requests` package:** `pip install requests`
- **Kerberos ticket:** `klist -s || kinit`
- **GS CA bundle:** `C:\ProgramData\certificates\cacerts.cer` must exist.

## Reference

Domain knowledge: memory/_dormant/ref/symphony-bot-framework.md

## Usage

```powershell
# Windows:
cmd /c "H:\uv-env.cmd && uv run python skills/SYMPHONY/src/symphony.py <command> [options]"

# Linux:
uv run python skills/SYMPHONY/src/symphony.py <command> [options]
```

### Commands

| Command | Description | Key args |
|---------|-------------|----------|
| `search` | Search rooms by name | `--query "room name"` |
| `info` | Get room info + members | `--stream-id ID` |
| `messages` | Fetch latest messages | `--stream-id ID` `--minutes N` (default 15) `--limit N` (default 50) |

### Examples

```powershell
# Windows:
cmd /c "H:\uv-env.cmd && uv run python skills/SYMPHONY/src/symphony.py search --query 'Vol Strats'"
cmd /c "H:\uv-env.cmd && uv run python skills/SYMPHONY/src/symphony.py info --stream-id O8sg4z7QIFyb3oj15oEmOH___oOiiQS3dA"
cmd /c "H:\uv-env.cmd && uv run python skills/SYMPHONY/src/symphony.py messages --stream-id O8sg4z7QIFyb3oj15oEmOH___oOiiQS3dA --minutes 30"

# Linux:
uv run python skills/SYMPHONY/src/symphony.py search --query 'Vol Strats'
uv run python skills/SYMPHONY/src/symphony.py messages --stream-id O8sg4z7QIFyb3oj15oEmOH___oOiiQS3dA --minutes 30
```

## Output

All commands write JSON to `workspace/tmp/symphony-<command>.json` and print a human-readable summary to stdout.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| SSL certificate errors | Missing GS CA bundle | Verify `C:\ProgramData\certificates\cacerts.cer` exists |
| `ImportError: gs_auth` | Package not installed | `pip install gs-auth` |
| "Latest messages" returns old msgs | `since` set too far back | Use `--minutes 15` (default) — don't set large windows with small limits |
| Bot Framework QA 500 errors | QA SKEY issue | Script uses PROD endpoint — no action needed |
| Empty room search results | Room name mismatch | Try shorter/partial query strings |

## Task-Based Execution

**Task label:** `symphony` | **Args file:** `workspace/tmp/symphony_args.json`

Preferred. Write args JSON, then `run_task("symphony")`. CLI args pass through via `%*`.

## Links

- memory/_dormant/ref/symphony-bot-framework.md — Symphony Bot Framework API Bridge
- memory/_dormant/ref/gssso-auth.md — GSSSO cookie auth
