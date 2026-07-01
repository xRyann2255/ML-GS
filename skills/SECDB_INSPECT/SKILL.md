---
name: SECDB_INSPECT
description: Inspect SecDB security instream (stored VT) values via DiskInstreamValues trace parsing
---

# SECDB_INSPECT — Inspect SecDB Security Details

> **Purpose:** Retrieve the instream (stored VT) structure for a SecDB security — the disk-stored value type fields that define a security's terms and parameters.

**Out of scope:** Derived/computed values (Greeks, PnL, market data), trade booking, position queries, security creation.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SECDB_INSPECT` |
| **Scope** | Read instream VTs via `DiskInstreamValues` / `@Instream::Values` |
| **Inputs** | Security name, optional book (for trade DB resolution), optional recurse flag |
| **Outputs** | Instream fields as JSON or flat key=value to stdout |
| **Authority** | Read-only (`secexpr --safe`, no DB writes) |

## When to Use

- Inspect what instream values define a security (contract terms, dates, rates, etc.).
- Examine a trade's stored parameters (use `--book` for securities in trade databases).
- Compare instream fields across securities.
- Debug security setup or configuration issues.

---

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## How to Use

### 1. Basic inspection (JSON output, default)

```powershell
& PYTHON skills/SECDB_INSPECT/src/inspect.py --sec "EqF ESM26"
```

### 2. Flat key=value output

```powershell
& PYTHON skills/SECDB_INSPECT/src/inspect.py --sec "EqF ESM26" --format flat
```

### 3. Trade security (requires book for DB resolution)

```powershell
& PYTHON skills/SECDB_INSPECT/src/inspect.py --sec "EFA EUR 16Apr26 66JNJV 0" --book "ISELANIM"
```

### 4. Recursive inspection (follows nested securities — swap legs, components)

```powershell
& PYTHON skills/SECDB_INSPECT/src/inspect.py --sec "EqF ESM26" --recurse
```

### 5. Custom database and timeout

```powershell
& PYTHON skills/SECDB_INSPECT/src/inspect.py --sec "70359140" --db "!NYC_Equity_Prod" --timeout 180
```

## Arguments

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `--sec` | Yes | — | Security name or Object ID |
| `--format` | No | `json` | Output format: `json` (pretty-printed) or `flat` (aligned key=value) |
| `--book` | No | — | Book name to resolve trade database (for securities not in default DB) |
| `--recurse` | No | False | Recurse into nested securities (swap legs, components) via `@Instream::Values` |
| `--db` | No | `!NYC_Production` | SecDB database |
| `--source` | No | `PS` | SecDB source chain |
| `--timeout` | No | 120 | secexpr timeout in seconds |

## Output

Instream fields printed to stdout as JSON or flat key=value. Logs written to `workspace/tmp/secdb_inspect_logs/`.

### Book Mode (two-phase)

When `--book` is provided, the script runs two secexpr calls:
1. **Phase 1:** Resolves the trade database from the book name via `Trade Database(Group Names(book)[0])`
2. **Phase 2:** Runs `DiskInstreamValues` against the resolved DB at top level

This two-phase approach is necessary because `DiskInstreamValues` trace output only appears when called at top level — not inside `UseDatabase()+Eval{}` wrappers.

### Recurse Mode

Uses `@Instream::Values` from `_LIB Instream Values` with `Recurse := True`, which follows nested securities (swap legs, components) and may return additional fields not present in the base security.

## How It Works

1. Builds Slang code that calls `DiskInstreamValues(sec)` at top level (or `@Instream::Values` for recurse)
2. Pipes the Slang to `secexpr "{db}" --safe --source "{source}" -t` via batch file
3. The `-t` (trace) flag causes `DiskInstreamValues` to emit each stored VT as `Key : Value` lines to stderr
4. Python parses the stderr trace with regex, extracting key-value pairs
5. Formats output as JSON or aligned flat text

### Why Trace Parsing?

Direct Slang serialization of instream structures fails in `secexpr --safe`:
- `Jsonify(Structure)` — C++ exception crash on non-serializable types
- `ForEach(K, V, Structure)` — "Too many arguments" (unsupported 3-variable form)
- `Structure.(K)` — Parser error (dynamic member access unsupported)
- `String(Structure)` / `Print(Structure)` — Returns empty / no output

Parsing the `-t` trace output from stderr is the only reliable method.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Security not found | Use `--book` to resolve trade DB, or `--db` to specify DB directly |
| Empty instream | Security may not have disk-stored VTs (e.g. computed-only securities) |
| Timeout | Increase `--timeout`; complex securities take longer |
| Phase 1 fails (book resolution) | Check book name spelling; book must exist in the default DB |

## Task-Based Execution

**Task label:** `secdb-inspect` | **Args file:** `workspace/tmp/secdb_inspect_args.json`

Write the args JSON with `create_file` or `replace_string_in_file`, then `run_task("secdb-inspect")`. Read results from `out_file`.

"Task started but no terminal was found" is normal — `close: true` auto-dismisses the terminal.

### Args JSON schema

```json
{
  "sec": "EqF ESM26",
  "format": "json",
  "book": null,
  "db": "!NYC_Production",
  "source": "PS",
  "timeout": 120,
  "recurse": false,
  "out_file": "workspace/tmp/secdb_inspect_out.txt"
}
```

Only `sec` is required. All other keys are optional (defaults apply).

## Links

- memory/ref/secdb-ufo-diddles.md — SecDB UFO/diddle inspection patterns
- memory/ref/secdb-trade-model.md — SecDB trade model reference
