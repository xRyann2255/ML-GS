---
name: SECDB_DIFF
description: Compare instream (stored VT) values between two SecDB securities and output the differences
---

# SECDB_DIFF — Compare SecDB Security Instreams

> **Purpose:** Fetch the instream (stored VT) fields for two SecDB securities side-by-side and output a structured diff showing fields that differ, are missing from one side, or match.

**Out of scope:** Derived/computed values (Greeks, PnL, market data), trade booking, position queries, security creation.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SECDB_DIFF` |
| **Scope** | Compare instream VTs for two securities via SECDB_INSPECT |
| **Inputs** | Two security names, optional books/DBs per security, output format |
| **Outputs** | Side-by-side diff to stdout (JSON or table). Logs in `workspace/tmp/secdb_inspect_logs/` |
| **Authority** | Read-only (`secexpr --safe`, no DB writes) |
| **Depends on** | `SECDB_INSPECT` (reuses inspect.py parser), `PYTHON_PATH` |

## When to Use

- Compare contract terms between two securities (e.g. two options on the same underlying with different strikes/expiries).
- Debug why two securities that should be identical have different instreams.
- Verify a re-booked or cloned security matches the original.
- Audit differences between a trade security and its template.

---

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## How to Use

### 1. Basic diff (two securities in the same DB)

```powershell
& PYTHON skills/SECDB_DIFF/src/diff.py --sec1 "EqF ESM26" --sec2 "EqF ESU26"
```

### 2. Show only differences (suppress matching fields)

```powershell
& PYTHON skills/SECDB_DIFF/src/diff.py --sec1 "EqF ESM26" --sec2 "EqF ESU26" --diff-only
```

### 3. Trade securities with book resolution

```powershell
& PYTHON skills/SECDB_DIFF/src/diff.py \
  --sec1 "EFA EUR 16Apr26 66JNJV 0" --book1 "ISELANIM" \
  --sec2 "EFA EUR 16Apr26 77ABCD 0" --book2 "ISELANIM"
```

### 4. Cross-database comparison

```powershell
& PYTHON skills/SECDB_DIFF/src/diff.py \
  --sec1 "70359140" --db1 "!NYC_Equity_Prod" \
  --sec2 "70359141" --db2 "!NYC_Production"
```

### 5. Recursive comparison (follows swap legs, components)

```powershell
& PYTHON skills/SECDB_DIFF/src/diff.py --sec1 "SWP A" --sec2 "SWP B" --recurse
```

### 6. Table output format

```powershell
& PYTHON skills/SECDB_DIFF/src/diff.py --sec1 "EqF ESM26" --sec2 "EqF ESU26" --format table
```

### 7. Numeric tolerance (treat close floats as equal)

```powershell
& PYTHON skills/SECDB_DIFF/src/diff.py --sec1 "EqF ESM26" --sec2 "EqF ESU26" --tolerance 0.01
```

### 8. Write output to file

```powershell
& PYTHON skills/SECDB_DIFF/src/diff.py --sec1 "EqF ESM26" --sec2 "EqF ESU26" --output diff-result.json
```

## Arguments

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `--sec1` | Yes | — | First security name or Object ID |
| `--sec2` | Yes | — | Second security name or Object ID |
| `--book1` | No | — | Book name for sec1 (trade DB resolution) |
| `--book2` | No | — | Book name for sec2 (trade DB resolution) |
| `--db1` | No | `!NYC_Production` | SecDB database for sec1 |
| `--db2` | No | `!NYC_Production` | SecDB database for sec2 |
| `--recurse` | No | False | Recurse into nested securities |
| `--diff-only` | No | False | Show only differing/missing fields (suppress matches) |
| `--format` | No | `json` | Output format: `json` or `table` |
| `--tolerance` | No | — | Numeric tolerance for float comparison (e.g. `0.01`). When set, two values that parse as floats and differ by less than this are treated as matching. Default: exact string match |
| `--output` | No | — | Filename to write to `workspace/tmp/` instead of stdout (e.g. `diff-result.json`) |
| `--source` | No | `PS` | SecDB source chain (shared by both) |
| `--timeout` | No | 120 | secexpr timeout per call (seconds) |

## Output

### JSON format (default)

```json
{
  "sec1": "EqF ESM26",
  "sec2": "EqF ESU26",
  "summary": { "total": 15, "match": 12, "differ": 2, "only_sec1": 0, "only_sec2": 1 },
  "differences": [
    { "field": "Expiration Date", "sec1": "20260620", "sec2": "20260919", "status": "differ" },
    { "field": "Contract Month", "sec1": "M", "sec2": "U", "status": "differ" }
  ],
  "only_sec1": [],
  "only_sec2": [
    { "field": "Roll Date", "sec1": null, "sec2": "20260815", "status": "only_sec2" }
  ],
  "matches": [
    { "field": "Underlying", "value": "SPX" }
  ]
}
```

### Table format

```
Field                  | sec1 (EqF ESM26)       | sec2 (EqF ESU26)       | Status
-----------------------|------------------------|------------------------|----------
Expiration Date        | 20260620               | 20260919               | DIFFER
Contract Month         | M                      | U                      | DIFFER
Roll Date              | —                      | 20260815               | ONLY sec2
Underlying             | SPX                    | SPX                    | match
```

Logs written to `workspace/tmp/secdb_inspect_logs/`.

## How It Works

1. Calls `SECDB_INSPECT/src/inspect.py` logic twice (once per security) to fetch instream KV pairs via `DiskInstreamValues` trace parsing.
2. When `--recurse` is used, duplicate keys from nested securities (swap legs, components) are disambiguated with a `[N]` suffix to avoid silent overwrites.
3. Builds a union of all field keys from both securities.
4. Categorizes each field: **match**, **differ**, **only_sec1**, **only_sec2**. When `--tolerance` is set, numeric values within the tolerance are treated as matching.
5. Formats and prints the result (or writes to file if `--output` is given).

## Troubleshooting

| Issue | Solution |
|-------|----------|
| One security has no instream data | Security may not have disk-stored VTs; try `--recurse` |
| Fields differ only by formatting | Use `--tolerance` for numeric rounding differences (e.g. `1.0` vs `1.00`) |
| Timeout on complex securities | Increase `--timeout`; each security runs separately |
| Duplicate key names in recursive mode | Keys from nested components get `[N]` suffix automatically |

## Task-Based Execution

**Task label:** `secdb-diff` | **Args file:** `workspace/tmp/secdb_diff_args.json`

Write the args JSON with `create_file` or `replace_string_in_file`, then `run_task("secdb-diff")`. Read results from `out_file`.

"Task started but no terminal was found" is normal — `close: true` auto-dismisses the terminal.

### Args JSON schema

```json
{
  "sec1": "EqF ESM26",
  "sec2": "EqF ESU26",
  "book1": null,
  "book2": null,
  "db1": "!NYC_Production",
  "db2": "!NYC_Production",
  "recurse": false,
  "diff_only": false,
  "format": "json",
  "tolerance": null,
  "output": null,
  "source": "PS",
  "timeout": 120,
  "out_file": "workspace/tmp/secdb_diff_out.txt"
}
```

Only `sec1` and `sec2` are required. All other keys are optional (defaults apply).

## Links

- SECDB_INSPECT — single-security instream inspection (dependency)
- memory/ref/secdb-ufo-diddles.md — SecDB UFO/VT context
