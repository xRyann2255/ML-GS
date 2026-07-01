---
name: SLANG_GLIMPSE
description: Search Slang codebases via ELPS (Elasticsearch) or Glimpse
---

# SLANG_GLIMPSE — Search Slang Scripts via ELPS or Glimpse

> **Purpose:** Search GS Slang codebases (and other indexed repositories) using ELPS (Elasticsearch) or traditional Glimpse text search.

**Out of scope:** Modifying scripts, running scripts, or searching non-indexed codebases.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_GLIMPSE` |
| **Scope** | Search Slang script text, references, definitions, comments |
| **Inputs** | Search pattern, optional field/index/count filters |
| **Outputs** | Matching script names, lines, and context |
| **Authority** | Read-only |

## When to Use

- Find function definitions, call sites, or usage examples in Slang.
- Discover which scripts use a particular pattern or library.
- Search for Link statements, RegTest stubs, or comments.

---

Search GS Slang codebases (and other indexed repositories) using **ELPS**
(Elastic ProdSource / Elasticsearch) or the traditional **Glimpse** text-search
infrastructure.

**Default behavior:** For Slang indices (`slangprod`, `slangdev`, `slanguser`,
`slangarch`), uses ELPS (faster, richer field searches). Falls back to Glimpse
automatically if ELPS returns no results or is unavailable. Non-Slang indices
always use Glimpse.

> **Memory:** `memory/_dormant/slang/research.md` (search strategy), `memory/_dormant/slang/utility-libs.md` (known library names).

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## Quick Start

```powershell
# Simple search (ELPS by default for slangprod)
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "Glimpse::Find"

# Force Glimpse backend
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "Glimpse::Find" --backend glimpse

# ELPS field search: find callers of a function
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "Array::Diff" --field references

# ELPS field search: find function definitions
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "Array::Diff" --field defines

# Search in comments only
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "goodfj" --field comments --files-only

# Search by script name
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "Glimpse" --field name --files-only

# File-list only (no matched lines)
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "Glimpse::Find" --files-only

# Filter out comments from results
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "Glimpse::Find" --no-comments

# JSON output
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index slangprod --query "Glimpse::Find" --json --max-results 20

# Search non-Slang index (auto-uses Glimpse)
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --index jsi --query "some_function" --files-only

# List available indices
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py ^
    --list-indices
```

## Arguments

| Argument           | Required | Description |
| ------------------ | -------- | ----------- |
| `--index`          | Yes*     | Glimpse index to search (e.g. `slangprod`, `slangdev`, `slanguser`, `eqdev`) |
| `--query`          | Yes*     | Search pattern (text, phrase, or ES query_string syntax) |
| `--backend`        | No       | `auto` (default), `elps`, or `glimpse`. Auto uses ELPS for Slang indices |
| `--field`          | No       | ELPS field to search: `source` (default), `references`, `defines`, `comments`, `name`, `links`, `scripttype`, `length` |
| `--files-only`     | No       | Return only script/file names, not matched lines |
| `--case-sensitive` | No       | Case-sensitive search (Glimpse only; ELPS is always case-insensitive) |
| `--no-comments`    | No       | Filter out lines that are comments (`//`, `**`, `/*`, `#`) |
| `--flags`          | No       | Additional raw glimpse flags (e.g. `-w` for whole word) |
| `--max-results`    | No       | Maximum number of result lines to return |
| `--max-docs`       | No       | ELPS: max documents to return (default: 500) |
| `--username`       | No       | Override login name sent to Glimpse (default: current user) |
| `--list-indices`   | No       | List all known Glimpse index names and exit |
| `--json`           | No       | Output results as JSON |
| `--timeout`        | No       | Request timeout in seconds (default: 30) |

\* Not required when `--list-indices` is used.

## Backends, Fields & Indices

See memory/slang/glimpse-reference.md for ELPS/Glimpse backend details, query syntax, searchable fields, available indices, output formats, and protocol internals.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 0 results from ELPS | Query too specific or index lag | Try broader query; tool auto-falls back to Glimpse |
| Glimpse connection refused | TCP socket unavailable | Check network; use `--backend elps` to force ELPS |
| Too many results | Query too broad | Use `--field defines` or `--field references` to narrow |

## Task-Based Execution (Zero Allow — Preferred)

Use `run_task("glimpse")` instead of `run_in_terminal` to avoid the Copilot "Allow" prompt.

### Workflow

1. **Write args file** (use `create_file` — no terminal):

```json
{
  "index": "slangprod",
  "query": "Array::Diff",
  "field": "references",
  "files_only": true,
  "output_json": "workspace/tmp/glimpse_results.json",
  "max_results": 50
}
```

Args file keys mirror CLI flags: `index`, `query`, `backend`, `field`, `files_only`, `case_sensitive`, `no_comments`, `flags`, `max_results`, `max_docs`, `json`, `output_json`, `timeout`.

2. **Launch via predefined VS Code Task** (no Allow):

```
run_task("glimpse", workspaceFolder: "h:\ml-vol-estimator")
```

The task reads `workspace/tmp/glimpse_args.json` automatically.
```

3. **Read results** with `read_file` on `workspace/tmp/glimpse_results.json` (no terminal).

### No `run_in_terminal` anywhere

| Step | Tool | Allow? |
|---|---|---|
| Write args JSON | `create_file` | No |
| Launch task | `run_task` | No |
| Read results | `read_file` | No |

## Links

- memory/slang/research.md — search strategy
- memory/slang/utility-libs.md — known library names
