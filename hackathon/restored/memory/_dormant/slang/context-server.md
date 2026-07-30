---
created: 2026-04-26
updated: 2026-04-26
tags: [slang, context-server, repl, ai-sdk, vfs, tooling]
status: dormant
relates:
  - slang/run.md
  - slang/lint-edit.md
  - slang/secexpr-gotchas.md
  - slang/research.md
---

# Slang Context Server

The Context Server (`_UT AI SDK REPL Server`) is an HTTP service I use to
navigate SecDB, read scripts, search code, look up docs, and lint — all via
HTTP from VS Code Copilot agentic mode. It also exposes tools for Jira,
IssueTrack, CVS history, reviews, Procmon, and Symphony.

## Auto-Bootstrap

If the workspace has `slang:` VFS files and I have NOT run the Session
Bootstrap in this conversation, I must run it **before answering** — even for
non-Slang questions. I cannot know what tools are available until I complete
bootstrap, read `/registry`, and run `help`.

## Context Freshness (Every Turn)

Before answering any user turn, I verify `## Architecture`,
`## Discovery Guide`, `## Creating and Editing Scripts` are in context.
If missing, I call `/health?refresh=true` and `/registry` immediately.

## Rules (Context-Server-Specific)

Rules already covered elsewhere are cross-referenced, not repeated here.

| # | Rule | Notes |
|---|------|-------|
| 1 | ASCII-only in `.s` files | See `slang/best-practices.md` |
| 2 | `slang:` VFS for all `.s` files | See `slang/run.md` |
| 3 | Never write Slang from memory | Discover real patterns via Context Server first |
| 4 | Never use VS Code search on `slang:` VFS | `grep_search`, `semantic_search`, `file_search` fail silently — use Context Server: `cat`, `grep`, `ls`, `locate`, `man`/`apropos` via `/tool` (name=bash) |
| 5 | Load syntax reference before writing code | Call `slang_syntax_guide` tool |
| 6 | Include `query_id` on every `/tool` call | One UUID per user turn, shared across all calls in that turn |
| 7 | Describe every terminal command | Include short command + reason in `explanation` field |
| 8 | Open-ended queries — ask, don't guess | Present options when discovery returns many directions |
| 9 | Lint after every edit | See `slang/lint-edit.md` |

### Script Create/Edit Decision Table

| Scenario | Action |
|---|---|
| New file | `create_file` with `// placeholder`, then `replace_string_in_file` |
| File open in editor | `replace_string_in_file` directly |
| ProdSrc not in branch | `/touch` → refresh explorer → `read_file` → edit |
| Already in branch | `replace_string_in_file` directly |
| Name has `:` | Create temp without colon, edit temp, ask user to copy back |

## Per-Turn Preamble

At the start of every user turn, before answering or making any `/tool` call:

1. Generate one UUID for this turn
2. `list_dir("slang:/")` — discover current SubDB
3. Compare with SubDB in session memory
4. **Same SubDB** → continue, reuse existing port
5. **Changed SubDB** (or first turn with no server):
   - Shut down old server (`cmd=shutdown`), wait ~2s
   - Start new server on same port (Step 2 of bootstrap)
   - Health-check; retry every 3–4s up to ~1 min; if port stuck, pick new free port
   - Fetch `/health` instructions, `/registry`, `help`
   - Update session memory (SubDB, port, VFS prefix)
6. **Context freshness**: verify `/health` headings are in context; if missing after compaction, call `/health?refresh=true` + `/registry`

## Quick Reference

| Topic | Detail |
|---|---|
| `man` vs `cat` | `man` = builtins/SLAM only. For `_LIB`/`_UT`/`UFO`/`_TYPE` use `cat` |
| URL encoding | `!`=`%21` space=`%20` (VFS) or `+` `{`=`%7B` `}`=`%7D` `"`=`%22` `:`=`%3A` `*`=`%2A` `\|`=`%7C` `&`=`%26` |
| Batch calls | `cmd=batch&calls=[{"name":"...","args":{...}},...]` — one request for 2+ independent tools |
| Skills | `cmd=registry` → `skills` array. Load: `cmd=load_skill&name=<name>`. Lazy — reload after compaction |

## Session Bootstrap (Once Per Session)

### Step 1 — Discover SubDB

```
list_dir( path = "slang:/" )
```

| Result | SubDB | Source arg | VFS prefix |
|--------|-------|-----------|------------|
| `!NYC Source/` | `ps` | `--source "ps"` | `slang:/%21NYC%20Source/` |
| `!NYC UserDBs!home!<user>!<branch>/` | `~<user>!<branch>` | `--source "~<user>!<branch>;ps"` | `slang:/%21NYC%20UserDBs%21home%21<user>%21<branch>/` |

Store user, branch, SubDB, VFS prefix in session memory.

### Step 2 — Find or Start Server

If session memory has a port for this SubDB, health-check it:
```powershell
(curl -UseBasicParsing http://localhost:<PORT>/ssp/current/AISDKRepl?cmd=health).Content
```

If no port or health check fails:
1. **Find free port** — .NET TcpListener on `[System.Net.IPAddress]::Loopback` port 0 → `.Start()` → `.LocalEndpoint.Port` → `.Stop()`. Write port to temp file (`Out-File`) and read back (`Get-Content`) — terminal truncates output. PowerShell/.NET only, no Python.
2. **Start server**:
   ```powershell
   Start-Process -WindowStyle Hidden -FilePath "runmapsecenv" `
     -ArgumentList 'prod 64 -- secexpr --source "<SUBDB>;ps" --safe -l "Port=<PORT>" -s "_UT AI SDK REPL Server"'
   ```
3. Wait ~15s, then health-check. On failure, retry every 3–4s.
4. Store SubDB → port in session memory.

### Step 3 — Read Instructions

```powershell
(curl -UseBasicParsing "http://localhost:<PORT>/ssp/current/AISDKRepl?cmd=health&refresh=true").Content
```

Response may include `instructions` (first call, every 24h, or `refresh=true`).
Use as session reference (Architecture, Discovery, etc.). Do NOT save to this file.

### Step 4 — Complete Startup

```powershell
(curl -UseBasicParsing "http://localhost:<PORT>/ssp/current/AISDKRepl?cmd=registry").Content
(curl -UseBasicParsing "http://localhost:<PORT>/ssp/current/AISDKRepl?cmd=tool&name=bash&args=%7B%22command%22%3A%22help%22%7D&query_id=<UUID>").Content
```

Registry has `tools` + optional `skills` arrays. Skills are lazy-loaded via
`cmd=load_skill&name=<name>`. Reload after context compaction.
