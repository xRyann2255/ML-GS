---
name: SECDB_TRANSLOG
description: Query SecDB transaction logs (change history) for any security in a database. Based on _UT Point Finger Of Blame (PFOB). USE FOR listing who/what modified a security, viewing transaction diffs, auditing security changes, debugging unexpected mutations.
---

# SECDB_TRANSLOG — Security Transaction Log Query

> **Purpose:** Retrieve the transaction log (change audit trail) for any SecDB security in a database — the programmatic equivalent of `_UT Point Finger of Blame` (PFOB).

**Out of scope:** Modifying securities, running the interactive PFOB UI, trade booking/deletion.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SECDB_TRANSLOG` |
| **Scope** | Read transaction history via `Trans::List Transactions` and `PFOB::Get Transactions and Diffs` through secexpr |
| **Inputs** | Security name, mode (list/diffs), optional database, back-to/cutoff time, max transactions |
| **Outputs** | Transaction records (JSON or table) or diffs text to stdout |
| **Authority** | Read-only (`secexpr --safe`, no DB writes) |

## When to Use

- View who/what last modified a security and when.
- List all transactions (changes) for a security in a database.
- Show transaction **diffs** (what changed between transactions).
- Audit the change history of a security (e.g., a book, config, trade).
- Debug unexpected mutations or stale data by inspecting the transaction log.
- Equivalent of running `_UT Point Finger of Blame` interactively.

---

## Background: _UT Point Finger Of Blame (PFOB)

The firm-wide PFOB tool (`_LIB Point Finger Of Blame`, namespace `PFOB::`) provides:

- **`PFOB::Get Transactions and Diffs(SecurityName, Database, CutoffTime, ...)`** — Programmatic: retrieves transaction list and diffs for a security.
- **`PFOB::PFOB([SecurityNames], ...)`** — Interactive: launches the PFOB UI window.
- **`Trans::List Transactions(SecurityName, ...)`** — Low-level: returns raw transaction array from `_LIB Transaction Fns`.

This skill wraps **both** `Trans::List Transactions` (list mode) and `PFOB::Get Transactions and Diffs` (diffs mode).

> **Memory:** memory/_dormant/ref/secdb-trade-model.md — trades, tradeables, positions, books.

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## How to Use

### 1. List transaction headers (default mode)

```powershell
& PYTHON skills/SECDB_TRANSLOG/src/translog.py --sec "MySecurityName"
```

### 2. With specific database

```powershell
& PYTHON skills/SECDB_TRANSLOG/src/translog.py --sec "MySecurityName" --db "!NYC_Equity_Prod"
```

### 3. Limit number of transactions

```powershell
& PYTHON skills/SECDB_TRANSLOG/src/translog.py --sec "MySecurityName" --max-trans 50
```

### 4. Show only transactions after a given time (BackTo)

```powershell
& PYTHON skills/SECDB_TRANSLOG/src/translog.py --sec "MySecurityName" --back-to "01Jan26"
```

### 5. Transaction diffs (show what changed)

```powershell
& PYTHON skills/SECDB_TRANSLOG/src/translog.py --sec "MySecurityName" --mode diffs
```

### 6. Diffs with cutoff time and Slang format

```powershell
& PYTHON skills/SECDB_TRANSLOG/src/translog.py --sec "MySecurityName" --mode diffs --cutoff "01Jan26 18:00:00" --var-to-slang
```

### 7. JSON output (for downstream processing)

```powershell
& PYTHON skills/SECDB_TRANSLOG/src/translog.py --sec "MySecurityName" --format json
```

### 8. With book (resolves trade database automatically)

```powershell
& PYTHON skills/SECDB_TRANSLOG/src/translog.py --sec "MyTradeName" --book "EXAMPLEBOOK"
```

## Modes

| Mode | API | Output |
|------|-----|--------|
| `list` (default) | `Trans::List Transactions` | Transaction headers with all fields (table or JSON) |
| `diffs` | `PFOB::Get Transactions and Diffs` | Transaction headers **plus** value changes between each pair |

## Arguments

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `--sec` | Yes | — | Security name to query transaction log for |
| `--db` | No | `!NYC_Production` | SecDB database to query |
| `--source` | No | `PS` | SecDB source chain |
| `--book` | No | — | Book name to resolve trade database (for trade securities) |
| `--mode` | No | `list` | `list` = transaction headers, `diffs` = headers + value changes |
| `--max-trans` | No | 40 | Maximum number of transactions to return (list mode) |
| `--back-to` | No | — | Oldest transaction time for list mode (Slang date format, e.g. `"01Jan26"`) |
| `--cutoff` | No | — | Cutoff time for diffs mode (Slang date format, e.g. `"01Jan26 18:00:00"`) |
| `--var-to-slang` | No | — | (diffs mode) Show diffs as Slang variable assignments |
| `--diff-lossless` | No | — | (diffs mode) Use lossless diff format |
| `--infinite-translog` | No | — | Force InfiniteTransLogDb resolution (auto for non-default DBs) |
| `--format` | No | `table` | Output format for list mode: `table` (human-readable) or `json` |
| `--timeout` | No | 120 | secexpr timeout in seconds |

## Output

### List mode

Transaction records printed to stdout. Fields are **dynamically discovered** from each `TransLogHeader` structure (via `ComponentNames`). Common fields include:

| Field | Description |
|-------|-------------|
| `Trans ID` | Transaction number |
| `GM Time` | Timestamp of the transaction (GM time) |
| `Login Name` | Kerberos ID of who made the change |
| `User Name` | Human-readable user name |
| `SecName` | Security that was modified |
| `Database` | Database where the change occurred |
| `Application Name` | Application that made the change |
| `Source Trans Id` | Source transaction ID |
| `DbId` | Database ID |

Columns are displayed in preferred order: Trans ID, GM Time, Login Name, User Name, SecName, Database, Application Name, then remaining fields alphabetically.

### Diffs mode

PFOB-formatted text showing transaction headers interleaved with the actual field-level differences between consecutive transactions.

Logs written to `workspace/tmp/secdb_translog_logs/`.

## How It Works

1. **List mode:** Builds Slang that calls `Trans::List Transactions(sec, BackTo, MaxTrans)` from `_LIB Transaction Fns`. Iterates each returned `TransLogHeader` and dumps all fields dynamically via `ComponentNames(Header)`.
2. **Diffs mode:** Builds Slang that calls `PFOB::Get Transactions and Diffs(sec, db, cutoff)` from `_LIB Point Finger Of Blame`. PFOB prints formatted output directly.
3. **InfiniteTransLogDb auto-resolution:** For any non-default database, the skill automatically resolves the `InfiniteTransLogDb` (e.g. `SPG Trade NYC` → `!NYC_SPG_Trade_NYC_Log`). Most DB rings store transaction log headers in a separate `_Log` database that must be used for `Trans::List Transactions` to deserialize headers.
3. Pipes the Slang to `secexpr "{db}" --safe --source "{source}" -t` via batch file.
4. Parses the marker-delimited output from stdout.
5. Formats output as table, JSON, or raw PFOB text.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Security not found | Check name spelling; use `--db` to specify the correct database |
| No transactions | Security may be new or in a different database |
| Timeout | Increase `--timeout`; large transaction logs take longer |
| Book resolution fails | Check book name; book must exist in the default DB |
| Diffs mode empty | Check `--cutoff` — if too recent, there may be no transactions after it |

## Task-Based Execution

**Task label:** `secdb-translog` | **Args file:** `workspace/tmp/secdb_translog_args.json`

Preferred. Write args JSON, then `run_task("secdb-translog")`. CLI args pass through via `%*`.

## Links

- memory/_dormant/ref/secdb-ufo-diddles.md — SecDB UFO/diddle inspection patterns
- memory/_dormant/ref/secdb-trade-model.md — SecDB trade model reference
