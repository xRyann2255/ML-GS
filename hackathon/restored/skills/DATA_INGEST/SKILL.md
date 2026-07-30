---
name: DATA_INGEST
description: "Fetch tick data (Chunk Store), daily data (TSDB), IV surface (Marquee ERDVOL). USE FOR: bulk data downloads, symbol universe ingestion, date range fetches, data quality checks. DO NOT USE FOR: feature computation (use FEATURE_BUILD), model training (use MODEL_TRAIN), ad-hoc price checks (use PYTHON_MARKET_DATA)."
---

# DATA_INGEST — Market Data Ingestion

> **Purpose:** Fetch raw market data from GS internal sources — Chunk Store tick data (L1/L2), TSDB daily OHLCV, and Marquee IV surface (ERDVOL_PERCENT_STANDARD) — and persist to `workspace/tmp/` as Parquet/CSV for downstream feature computation.

**Out of scope:** Feature computation (use FEATURE_BUILD), model training (use MODEL_TRAIN), quick single-symbol price checks (use PYTHON_MARKET_DATA).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `DATA_INGEST` |
| **Scope** | Bulk market data retrieval and persistence |
| **Inputs** | JSON args: symbol list, date range, data type (tick/daily/iv) |
| **Outputs** | Parquet/CSV files to `workspace/tmp/` |
| **Authority** | Read-only data access — no DB writes |

## When to Use

- Fetching tick data for a set of symbols over a date range
- Downloading daily OHLCV for the 34-symbol universe
- Pulling SPX IV surface data from Marquee ERDVOL
- Initial data setup for a new experiment or research session
- Data quality validation (gap checks, stale quote detection, timezone consistency)

## When NOT to Use

- Single-symbol quick price check — use PYTHON_MARKET_DATA
- Computing features from raw data — use FEATURE_BUILD
- Training models — use MODEL_TRAIN

## Memory References

Load these before executing:

| File | Content |
|------|---------|
| `memory/research/data-access.md` | 34-symbol universe, L1/L2 constraints, Marquee ERDVOL, feasibility matrix |
| `memory/ref/python-chunk.md` | Chunk Store tick data patterns, L1/L2 fields, timezone handling |
| `memory/ref/python-tsdb.md` | TSDB daily/RT wrappers, field dictionary |
| `workspace/docs/data-audit.md` | Comprehensive query cookbook — runnable snippets for every data element by feature layer |

## Args File Format

The wrapper is a thin adapter over `skills/_shared/vf_entry.py`, which invokes
`python -m volforecast.cli.ingest <argv>` (see `parse_args` in
`src/volforecast/cli/ingest.py` for the full flag list).

Write JSON to `workspace/tmp/ingest_args.json` (the exact `--args-file` value in
the `data-ingest` task definition):

```json
{
  "argv": ["--config", "workspace/configs/<trial>.yaml", "--symbols", "SPY"],
  "out_file": "workspace/tmp/data_ingest_out.txt"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `argv` | Yes | Argument vector passed verbatim to `volforecast.cli.ingest.main`. `--config` is required; other flags (`--symbols`, `--workers`, `--batch-size`, `--checkpoint-interval`, `--compute-workers`, `--symbol-workers`) are optional overrides of the YAML. |
| `out_file` | Yes | Path where captured stdout+stderr will be written. Final line will be `EXIT_CODE=<rc>`; success iff `EXIT_CODE=0`. |

> **Concurrency caveat (last-writer-wins):** The args file path is fixed per task —
> two concurrent agents writing it race (last writer wins). Keep `out_file` unique
> per run (put a `run_id` slug in its name, e.g. `workspace/tmp/data_ingest_out_<run_id>.txt`
> where `run_id` matches `[a-z0-9-]+`); the args file itself is not collision-safe.

**Reading results:** `read_file(out_file)`; the run succeeded iff its final line is `EXIT_CODE=0`.

## Data Type Details

### `tick` — Chunk Store L1/L2

- **Source:** Chunk Store via `pytickclient`
- **Fields:** Trade price, size, BBO, timestamps
- **L2 depth:** Available for E-mini (ES) only — append `m` suffix for depth book
- **Output:** One Parquet file per symbol per day
- **Timezone:** All timestamps in US/Eastern

### `daily` — TSDB OHLCV

- **Source:** TSDB daily wrappers or GS Quant TSDBSymbol
- **Fields:** Open, High, Low, Close, Volume, adjusted close
- **Output:** Single Parquet file per symbol (full date range)

### `iv` — TSDB edrvol_ + Marquee ERDVOL

- **Source:** Marquee API `ERDVOL_PERCENT_STANDARD`
- **Limitation:** SPX only
- **Fields:** ATM IV, skew (25d), term structure, butterfly
- **Output:** Parquet with date × tenor × moneyness grid

## Task-Based Execution

### Workflow

1. **Write args file:**
```json
{
  "argv": ["--config", "workspace/configs/<trial>.yaml", "--symbols", "SPY"],
  "out_file": "workspace/tmp/data_ingest_out.txt"
}
```

2. **Run task:**
```
run_task("data-ingest")
```

3. **Read output:** `read_file("workspace/tmp/data_ingest_out.txt")` — success iff last line is `EXIT_CODE=0`.

## Validation Checks

Before returning data as "ingested," verify:

1. **No gaps:** Missing trading days flagged (exclude weekends/holidays)
2. **Timezone consistency:** All timestamps in US/Eastern
3. **Stale quotes:** Flag days where BBO spread > 5× median
4. **Corporate actions:** Adjusted close aligns with unadjusted + split/div schedule
5. **Row counts:** Each trading day has expected tick count (flag if < 50% of median)

## Symbol Universe Reference

- **30 mega-cap equities:** AAPL, MSFT, AMZN, GOOGL, META, NVDA, TSLA, BRK.B, JPM, JNJ, V, PG, UNH, HD, MA, DIS, PYPL, BAC, CMCSA, XOM, NFLX, ADBE, CRM, PFE, TMO, CSCO, ABT, AVGO, ACN, NKE
- **4 ETFs:** SPY, QQQ, IWM, DIA
- **E-mini S&P 500:** ES (L2 depth available)
- **SPX IV surface:** Via Marquee ERDVOL only

## Links

- memory/research/data-access.md — data source inventory and constraints
- memory/ref/python-chunk.md — Chunk Store tick data reference
- memory/ref/python-tsdb.md — TSDB daily/RT wrappers
