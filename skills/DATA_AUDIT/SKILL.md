---
name: DATA_AUDIT
description: "Manifest-driven data integrity audit for the vol forecasting pipeline. USE FOR: validating all data sources (ticks, iv, ohlcv, micro, cross_asset, correlation) against their manifest contracts, detecting schema drift, NaN budget violations, value bounds errors, date gaps, layer readiness assessment, and updating data/manifest.yaml + data/manifest.json. DO NOT USE FOR: data fetching (use DATA_INGEST), feature computation (use FEATURE_BUILD), model evaluation (use EVALUATE)."
---

# DATA_AUDIT — Manifest-Driven Data Integrity Audit

> **Purpose:** Validate all cached parquet files against their contracts declared in `data/manifest.yaml`, assess per-layer readiness, identify blockers, and produce actionable reports.

**Out of scope:** Fetching new data (use DATA_INGEST), computing features (use FEATURE_BUILD), running models (use MODEL_TRAIN).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `DATA_AUDIT` |
| **Scope** | Multi-source contract validation and readiness reporting |
| **Inputs** | `data/manifest.yaml` (contract), parquet files on disk (state) |
| **Outputs** | Updated `data/manifest.yaml` (integrity fields), `data/manifest.json` (legacy), report in `workspace/tmp/data_audit_report.md`, journal entry |
| **Authority** | Read-only on parquets, writes manifest + report + journal |

## Architecture

The audit is **manifest-driven**: it iterates all sources declared in `data/manifest.yaml` and validates each against its contract (expected columns, value bounds, NaN budget, invariants). This means:

- Adding a new source to the manifest automatically includes it in audits
- No code changes needed to audit new data types
- Contract violations are detected generically (schema drift, bounds, NaN)

### Source Validation Flow

```
data/manifest.yaml → for each source:
  1. Read contract (expected_columns, value_bounds, nan_budget_pct)
  2. Scan directory for parquet files
  3. Validate each file against contract
  4. Aggregate results → SourceAuditResult
→ derive_layer_readiness() → per-layer blocked/ready status
→ generate_report() → Markdown report
→ _sync_audit_to_yaml() → update integrity fields in manifest
```

## When to Use

- After any data ingestion (`vol ingest-*` commands)
- Before running a tournament or experiment (pre-flight data check)
- When diagnosing model failures (check if input data is corrupt/missing)
- When onboarding (understand what data is available and its quality)
- After adding a new source to the manifest

## What It Checks (All Sources)

| Check | Severity | Description |
|-------|----------|-------------|
| **Schema match** | CRITICAL | All `expected_columns` present in parquet |
| **Value bounds** | CRITICAL | Values within declared `min`/`max` bounds |
| **NaN budget** | CRITICAL | Per-column NaN % below `nan_budget_pct` |
| **Date gaps** | WARNING | Calendar gaps > 5 days between rows |
| **Missing symbols** | INFO | Symbols in universe but no file on disk |
| **Stale formula** | INFO | Symbol's `lineage.formula_version` < source's current |

### Sources Audited

| Source | Directory | Pattern | Layers |
|--------|-----------|---------|--------|
| ticks | `data/raw/ticks/` | `{symbol}.parquet` | L0, L1, noise_robust |
| iv | `data/raw/iv/` | `{symbol}.parquet` + market-wide | L2 |
| ohlcv | `data/raw/ohlcv/` | `{symbol}.parquet` | L6 |
| microstructure | `data/raw/micro/` | `{symbol}.parquet` | L3 |
| cross_asset | `data/raw/cross_asset/` | Named files | L4 |
| correlation | `data/raw/correlation/` | Named files | L7 |

## Memory References

| File | Content |
|------|---------|
| `memory/research/data-access.md` | Data sources, constraints, GS edge |
| `workspace/research/data-ingestion-architecture.md` | Full architecture + manifest schema |
| `data/manifest.yaml` | Source contracts + per-symbol state |

## Execution

### CLI (recommended)

```bash
./vol audit
```

### Key Files

| File | Role |
|------|------|
| `src/volforecast/cli/audit.py` | Main entry point, report generation, YAML sync |
| `src/volforecast/cli/validators.py` | Generic `validate_source()` + `derive_layer_readiness()` |
| `src/volforecast/utils/manifest_schema.py` | Typed dataclasses (SourceContract, SourceAuditResult, Violation) |
| `src/volforecast/utils/manifest.py` | ManifestManager (YAML I/O) |

## Output Format

### Console Output

```
Running data audit...
  Auditing ticks...
  Auditing iv...
  Auditing ohlcv...
  Auditing microstructure...
  Auditing cross_asset...
  Auditing correlation...

============================================================
SOURCE STATUS
============================================================
  correlation      [L7] 0/1 files  OK
  cross_asset      [L4] 0/4 files  OK
  iv               [L2] 25/34 symbols  OK
  microstructure   [L3] 0/34 symbols  OK
  ohlcv            [L6] 1/34 symbols  OK
  ticks            [L0, L1, noise_robust] 25/34 symbols  OK

============================================================
LAYER READINESS
============================================================
  L0      25 symbols ready
  L1      25 symbols ready
  L2      25 symbols ready
  L3       0 symbols ready BLOCKED -> vol ingest-micro
  L4       0 symbols ready BLOCKED -> vol ingest-xasset
  L6       1 symbols ready
  L7       0 symbols ready BLOCKED -> vol ingest-corr
```

### `workspace/tmp/data_audit_report.md`

Markdown report with:
- Source Status Matrix (all 6 sources at a glance)
- Layer Readiness table (blocked/ready + action commands)
- Per-source detail (symbol table, named file table)
- Critical violations list
- Recommended actions (prioritized)

## Links

- `workspace/research/data-ingestion-architecture.md` — manifest schema spec, source layout
- `memory/research/data-access.md` — data sources, constraints
