---
domain: slang
subject: glimpse-reference
title: "SLANG_GLIMPSE — Backend & API Reference"
created: 2026-05-12
updated: 2026-05-12
tags: [slang, glimpse, elps, elasticsearch, search]
status: dormant
---

# SLANG_GLIMPSE Backend & API Reference

## Backends

### ELPS (Elasticsearch) — Default for Slang indices

- **Faster** than Glimpse for Slang script searches
- Supports **field-specific searches**: `source`, `references`, `defines`, `comments`, `name`, `links`
- Returns matched lines with line numbers
- Authenticated via GSSSO cookie (auto-obtained)
- Connects to `prod.es.elps-core.url.gs.com:9200`
- Index: `elps_ps_index_frontline`

**ELPS query syntax** (Elasticsearch query_string):
- `USD EUR BRL` — all terms must match (AND)
- `"USD EUR"` — phrase query (adjacent terms)
- `"USD EUR"~5` — phrase with slop (5 words apart)
- `usd OR (brl AND NOT eur)` — boolean (operators in UPPERCASE)
- Field-specific: `references:"Array::Diff"`, `defines:"My::Func"`, `comments:author`

### Glimpse (socket) — Default for non-Slang indices

- Traditional text search over all indexed codebases
- 57 available indices (Slang, JSI, Procmon, EQ, FICC, etc.)
- Connects to `glimpsequeryhost.stratinfra.services.gs.com:2002`
- Pattern auto-quoting for multi-word queries

## ELPS Searchable Fields

| Field        | Description |
| ------------ | ----------- |
| `source`     | Script source lines (default) |
| `references` | Function call references (`@Foo::Bar`) |
| `defines`    | Function definitions |
| `comments`   | Block and inline comments |
| `name`       | Script name |
| `links`      | `Link("...")` references |
| `scripttype` | Script type (Library, Type, etc.) |
| `length`     | Script length (numeric) |

## Available Glimpse Indices

Run `--list-indices` for the full list. Common ones:

| Index       | Description |
| ----------- | ----------- |
| `slangprod` | Production Slang scripts |
| `slangdev`  | Development Slang scripts |
| `slanguser` | User Slang scripts (home directories) |
| `slangarch` | Archived Slang scripts |
| `eqdev`     | Equity development |
| `jsi`       | JSI files |
| `procmon`   | Procmon configs |
| `secdb`     | SecDB scripts |

## Output Format

### Default (with line numbers)

```
ScriptName: linenum: matched line content
```

### Files-only (`--files-only`)

```
ScriptName
```

### JSON (`--json`)

```json
[
  {
    "script": "_LIB Foo",
    "file": "/sw/ficc/slang-PRODVER_REQ/lib/eq/Foo.s",
    "line_number": 42,
    "line": "    Results = @Glimpse::Find( Query, Index := \"slangprod\" );"
  }
]
```

## How It Works

### ELPS path
1. Obtains a GSSSO cookie via PowerShell (Kerberos auth)
2. Sends an Elasticsearch `query_string` query via HTTP POST to the ELPS cluster
3. Parses highlighted fragments (format: `linenum;content` with `<em>` tags)
4. Returns structured results

### Glimpse path
1. Opens a TCP socket to the Glimpse query gateway (port 2002)
2. Sends query: `~{user}~ -H /local/data/glimpse/indices/{index} -y {flags} {pattern}`
3. Parses `ScriptName (filepath): linenum: content` output
4. Returns structured results

### Auto fallback
When `--backend auto` (default), if ELPS returns 0 results the tool automatically
retries with Glimpse. This handles edge cases where ELPS indexing lags behind.

Based on the Slang libraries `_LIB ELPS Search Fns`, `_LIB ELPS Config`, and
`_LIB Glimpse Client Fns` (database `!NYC EqVol Source`).
