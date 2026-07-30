---
name: SECDB_POSITION
description: Source SecDB positions from books/portfolios/groups with correct diddle patterns for historical dates
---

# SECDB_POSITION — Position Sourcing from SecDB

> **Purpose:** Retrieve positions (`Children()`) from SecDB books/portfolios/groups, handling historical (EOD archive) diddle patterns automatically.

**Out of scope:** PnL decomposition, Dollar Price valuation, trade booking, UFO class creation.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SECDB_POSITION` |
| **Scope** | Read positions via `Children()` inside `UseDatabase(Trade Database(...))` |
| **Inputs** | Security name (book/portfolio/group), date (optional) |
| **Outputs** | Position table to stdout |
| **Authority** | Read-only (diddles are temporary, no DB writes) |

## When to Use

- Retrieve the current or historical position of a book/portfolio/group.
- List what securities a book holds and quantities.

---

> **Memory:** memory/_dormant/ref/secdb-position-pnl.md — diddle patterns, library reference, pitfalls.

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## Reference Script

Learned from `JDOE: Get Position` in `~{kerberos}!utils`.

## How to Use

### 1. Current position (today)

```powershell
& PYTHON skills/SECDB_POSITION/src/position.py --sec "EXAMPLEBOOK"
```

### 2. Historical position

```powershell
& PYTHON skills/SECDB_POSITION/src/position.py --sec "EXAMPLEBOOK" --date "14Apr26"
```

### 3. Portfolio positions (show ticker via description)

```powershell
& PYTHON skills/SECDB_POSITION/src/position.py --sec "NYC Example Portfolio" --fields description
```

### 4. Both name and description columns

```powershell
& PYTHON skills/SECDB_POSITION/src/position.py --sec "EXAMPLEBOOK" --fields both
```

### 5. Custom source chain and timeout

```powershell
& PYTHON skills/SECDB_POSITION/src/position.py --sec "EXAMPLEBOOK" --source "~jdoe!clean;PS" --timeout 180
```

## Arguments

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `--sec` | Yes | — | Security name (book, portfolio, or group) |
| `--date` | No | Today | Date string (e.g. `14Apr26`). Omit for today |
| `--fields` | No | `name` | Columns: `name` (raw SecDB name), `description` (ticker/human-readable), `both` |
| `--db` | No | `!NYC_Production` | SecDB database (1st positional arg to secexpr) |
| `--source` | No | `PS` | SecDB source chain (script loading) |
| `--timeout` | No | 120 | secexpr timeout in seconds |

## Output

Position table printed to stdout. Logs written to `workspace/tmp/secdb_position_logs/`.

### Fields: Name vs Description

| Security Type | `--fields name` | `--fields description` | Recommendation |
|---------------|-----------------|------------------------|----------------|
| **Book Alias** (e.g. EXAMPLEBOOK) | Human-readable (e.g. `EXAMPLE 16Apr26 T0000000 0`) | Usually empty | Use `name` (default) |
| **Portfolio** (e.g. NYC Example Portfolio) | Numeric Object ID (e.g. `T0000000`) | Ticker (e.g. `EXMPL3`) | Use `description` |

Use `--fields both` to see both columns side by side.

### Historical vs Today (automatic)

| `--date` | Position Source |
|-----------|----------------|
| Omitted (today) | Live `Children()` |
| Past date | `@Archive::DiddlePositions()` then `Children()` |

The script branches automatically based on whether the date equals today.

## How It Works

1. Builds Slang code following the `JDOE: Get Position` pattern
2. Pipes the Slang to `secexpr "{db}" --safe --source "{source}" -t` via stdin (batch file approach)
3. Parses structured markers from stdout (`===POSITION_START===`, `===POSITION_END===`)
4. Displays formatted position table

Key Slang pattern:
```slang
Link( "_LIB EOD Archive Procedure" );
Target   = "EXAMPLEBOOK";
Date     = Today() - 1;
Database = Trade Database( Group Names( Target )[ 0 ] );
UseDatabase( Database )
    Eval
    {
        If( Date != Today() )
            Check( @Archive::DiddlePositions( Target, Date ) );
        Print( Children( Target ) );
    };
```

### secexpr Notes

- **Database param** (`--db`): Controls security name resolution. Must be a production DB (e.g. `!NYC_Production`) to resolve real securities. `NullDb` cannot resolve real security names.
- **Source param** (`--source`): Controls where linked scripts are loaded from. Separate from the database param.
- **stdin line-by-line**: secexpr evaluates each stdin line as an independent expression. Blocks (`Eval`/`If`/`ForEach`) must NOT span multiple lines.
- **Print() has no newlines**: `Print()` does not emit newlines. Use `Sprintf("...\n")` to get line breaks.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Position query returns empty | Wrong source param or database | Verify `--source` and `--db` match the target environment |

## Task-Based Execution

**Task label:** `secdb-position` | **Args file:** `workspace/tmp/secdb_position_args.json`

Preferred. Write args JSON, then `run_task("secdb-position")`. CLI args pass through via `%*`.

## Links

- memory/_dormant/ref/secdb-position-pnl.md — SecDB Position & PnL reference
- memory/_dormant/ref/secdb-trade-model.md — SecDB trade model reference
