---
created: 2026-04-14
updated: 2026-04-14
tags: [sys, secdb, ecosystem, inform, zebra, pyslang, jsi, slangai, vs-code, extension, slam, ssp, plex, procmon]
status: dormant
relates:
  - ref/secdb-graph.md
  - slang/language.md
  - slang/run.md
  - sys/enghub.md
---

# SecDB Ecosystem — Tools & Integrations

Distilled from EngHub `secdb-platform-docs` — all 9 products.

---

## VS Code Slang Extension

Official IDE for Slang/SecDB, replacing SecView. Extension speaks SecDB VFS, CVS, ScriptReview, FasTest, Zebra Farm.

### Key Shortcuts

| Action | Shortcut |
|--------|----------|
| Run script | F9 |
| Run selection | Shift+F9 |
| Scratch Pad | Alt+V |
| Lint | Alt+L |
| Toggle breakpoint | Shift+F1 |
| Conditional breakpoint | Shift+F4 |
| Continue / Step Over / Into / Out | F5 / F10 / F11 / Shift+F11 |
| CPU profiler | F8 |
| Go to definition | F12 |
| Peek definition | Alt+F12 |
| Go to references | Shift+F12 |
| Find all references | Shift+Alt+F12 |
| Find in all scripts (ELPS) | Ctrl+Shift+F12 |
| Go to symbol | Ctrl+Shift+O |
| Change source DB | Alt+Z |
| Search front source DB | Alt+S / Alt+E |
| Register scope in Variable Explorer | Alt+F3 |

### Features

- **IntelliSense**: auto-completes C++ addins and cross-script functions.
- **Snippets**: `#script header`, `Func`, `#boilerplate`, `#boilerplate RegTest`.
- **Custom commands**: `Ctrl+Shift+P` → `Slang: Execute custom command` (e.g. `Declare New Class`, `Glimpse`).
- **Glimpse indexes**: `slangprod`, `ficcdev`, `ficcpre`, `jsi`, `procmon`.
- **Testing**: `Slang: Run FasTest` — same session, background (up to 5 parallel), or Zebra Farm.
- **Graph Explorer**: Security View (VT panels), Node View (value/state/debug), Graph Browser.
- **UFO Breakpoints**: GetValue, SetValue, SetDiddle, ChangeDiddle, InvalidateValue, NodeSplit. Conditions: security match, node match, lambda.
- **Safe/Full mode**: toggle via status bar. Safe = no Production writes.
- **Transaction Log Viewer**: browse, search by ID/time.

---

## Inform — SecDB Event Streaming

A Slang framework for subscribing to transaction notifications from SecDB databases. Change-data-capture layer.

### Key Concepts

- **Transactions**: `Transaction("name")`, `TransactionAbort("msg")`, `TransactionCommit()`.
- Optimal size: 32KB / 300 parts / 30,000 bytes. Hard warning at 100KB. Soft limit at 20MB.
- Each transaction gets a unique monotonic ID per database.

### Failover

- **Server failover**: client reconnects to backup key. No missed, no duplicates.
- **Database failover**: client fails over to backup DB. Transaction IDs may differ (eventual consistency). Internally handled — may be out of order during transition.

### Filters (Two-stage pipeline)

1. **Header filters (fast)**: DB mask, SecType mask, headers to retrieve/ignore. Transaction rejected if any fail.
2. **Detail filters**: `FilterFunc` per part. Returns a **filter-specific data structure**, not raw transaction.

Header filter types: Database Header Mask, Headers to Retrieve, Headers to Ignore, Ignore P Transactions, Ignore BaseRef Rollback Txns, SecType Header Mask.

---

## Zebra Farm — Testing as a Service

GS-hosted test execution platform. Successor to RAMS (only Slang test harness since Nov 2022). Each test script = separate ProcMon job.

### Capabilities

- Runs Slang, JSI, GitLab, JUnit, Fitnesse, Cypress, TfWeb, TestNg tests.
- Hardware: DC/Windows + PSRP on-prem + PSRP public cloud (GCP).
- Parallelizes tests; supports different OS/browsers.
- Results stored in **Etch** (5-year retention) and RAMS DB.
- APIs: JSON-RPC and Slang APIs. UI: `ui.zebra.url.gs.com`.
- Config: `_CFG Zebra Defaults`.

### RAMS vs Zebra

| Feature | RAMS | Zebra |
|---------|------|-------|
| Test registry | RegTE/RegTS/RegTG in SecPick | Own registry (hourly import) |
| Default account | p2sdbqa (many perms) | p2qa (no perms; use own p2) |
| Default hardware | DC | PSRP (preferred) |
| Cloud | No | GCP |

---

## pyslang — Python → Slang Bridge

GS PyPI package. Call Slang functions from Python. Slang datatypes auto-translated (e.g. TDS → DataFrame-like). Core-supported.

---

## JSI — Java Slang Integration

Integrates Slang into JVM processes. Call Slang from Java, expose Java to Slang. Core Engineering supported. Uses SecDB deployment for fast binary deploy.

---

## Slang AI — AI Assistant for SecDB

Wraps GitHub Copilot with Slang-specific context. Available in SecView, wxSecView, VS Code.

### Capabilities

- Answers Slang/SecDB questions. Writes functions, tests, documentation.
- **Agent mode**: reads/edits scripts, searches code, lints, files reviews, interacts with IssueTrack, Jira, Symphony, CVS history.

### VS Code Agent Mode

- Requires VS Code ≥ 1.110.1, active `slang:` session, Copilot Agent mode, Claude Opus 4.6+.
- One-time setup: run `_UT Gen Copilot Slang Memory` → generates a Slang memory file → load into Copilot memories.
- Bootstrap auto-detects `slang:` FS → starts Slang Context Server → reads `/health` → registers tools from `/registry`.
- First message: 15-20s (server startup). Subsequent messages fast.
- **Limitation**: Scripts with `:` in name cannot be directly edited on Windows in agent mode.

---

## SSP — Slang Server Pages

Keep front-end and back-end together in SecDB. Feature deployed as a unit.

### App Structure

- `_LIB` script for rendering/logic
- `_RES JS` / `_RES CSS` for resources
- `_SSP` script for the page (uses `<%@Auth%>`, links lib)
- `Test:` script for tests
- DashUI = recommended shared UI framework.
- AJAX handler pattern: Lambda switch + `SSP::AJAX Handling`.
- Test: F9 evaluates SSP demo page.

---

## SLAM — Documentation Markup

Native markup system for script/function headers, ScriptReview, IssueTrack, FAQs. See slang/language.md § SLAM Markup table for full syntax.

---

## Deployment Stack

| Tool | Purpose |
|------|---------|
| CVS | Script version control |
| ScriptReview | Code review (required) |
| FasTest | Test runner |
| Zebra Farm | Remote test platform |
| Procmon | Scheduled `_PROCM` runtime |
| PLEX | Distributed SSP serving |
| SecExpr | CLI Slang evaluator |
| TOPS | SecDB entitlements |
| Safe / Full mode | Operational safety toggle |
| Managed Slang | Onboarding for managed runtime |
