# Data Ingestion Architecture

**Date:** 2026-05-28
**Approach:** Source-based storage with Dask parallelism + YAML manifest

---

## Principle

Storage is organized by **data source** (what you fetch and from where). Feature layer isolation happens at **compute time** (train), not at storage time. This avoids the desync problem: tick-derived features (L0 RV, L1 semivariances, noise_robust RK) all come from the same ChunkStore fetch. Storing them in one file per symbol guarantees they are always computed together and never inconsistent.

---

## Commands

```
vol ingest-ticks     # ChunkStore L1 bars → RV, RQ, BPV, semivariances, jumps, RK (one pass)
vol ingest-iv        # TSDB edrvol_ + Marquee → per-symbol IV surface + VVIX/VIX
vol ingest-ohlcv     # TSDB eqpad_ → split-adjusted daily OHLCV
vol ingest-micro     # ChunkStore LeeReady → signed volume, VPIN, OFI + 10s bar sequences
vol ingest-xasset    # TSDB + Marquee → treasury yields, FX vol, credit vol, commodity vol
vol ingest-corr      # Marquee EDR_INDEX → SPX implied/realized correlation, dispersion
vol ingest-all       # Orchestrator: runs all above in dependency order
```

L5 (calendar) and L6 (long-memory/return-activity) have no ingest commands — they are pure derivations computed at train time from dates and existing columns.

### Common Flags

All commands accept:

| Flag | Default | Description |
|------|---------|-------------|
| `--symbols` | Full universe (34) | Comma-separated symbol list |
| `--start` | `2015-01-02` | Start date |
| `--end` | `2024-12-31` | End date |
| `--workers` | `34` | Dask worker count (tick sources only) |
| `--force` | `false` | Re-ingest even if data exists |
| `--recompute` | `false` | Re-derive features from cached ticks without re-fetching |
| `--bar-size` | `10s` | Bar resolution (micro sequences only) |

---

## Output Structure

```
data/raw/
├── ticks/                      # L0 + L1 + noise_robust (one tick pass)
│   ├── AAPL.parquet            # 22 columns: rv, rq, bpv, semivar, jumps, rk, ...
│   ├── MSFT.parquet
│   └── ...
├── iv/                         # L2: per-symbol IV + market-wide
│   ├── AAPL.parquet            # iv_1m_atm, iv_3m_atm, skew, term_slope, ...
│   ├── MSFT.parquet
│   ├── _VVIX.parquet           # Market-wide
│   ├── _VIX.parquet
│   ├── _OVX.parquet
│   ├── _TREASURY_YIELDS.parquet
│   └── _MARKET.parquet         # IV dispersion (cross-sectional)
├── ohlcv/                      # L6 source: daily OHLCV
│   ├── AAPL.parquet
│   └── ...
├── micro/                      # L3: per-symbol microstructure
│   ├── AAPL.parquet            # Daily aggregates (signed_vol_ratio, vpin, ofi)
│   └── sequences/              # 10-second bar sequences for LSTM/TCN
│       ├── AAPL.parquet        # (date × bar_idx × channels)
│       └── ...
├── cross_asset/                # L4: market-wide (not per-symbol)
│   ├── rates.parquet           # yield_2y, yield_5y, yield_10y, yield_30y, slope
│   ├── fx_vol.parquet          # fx_vol_usdjpy, fx_vol_eurusd
│   ├── credit.parquet          # hyg_iv, cdx_vol
│   └── commodity.parquet       # gld_iv, uso_iv
└── correlation/                # L7: market-wide
    └── spx_correlation.parquet # implied_corr, realized_corr, crp, dispersion
```

Each parquet file is self-contained with a DatetimeIndex (trading days, ascending). No cross-file dependencies at the raw layer.

---

## Source-to-Layer Mapping

| Source Dir | CLI Command | Layers Served | Per-Symbol? |
|-----------|-------------|---------------|-------------|
| `data/raw/ticks/` | `vol ingest-ticks` | L0 (HAR core), L1 (asymmetry), noise_robust | Yes |
| `data/raw/iv/` | `vol ingest-iv` | L2 (options-implied) | Yes + market-wide |
| `data/raw/ohlcv/` | `vol ingest-ohlcv` | L6 (return-activity features) | Yes |
| `data/raw/micro/` | `vol ingest-micro` | L3 (microstructure) | Yes |
| `data/raw/cross_asset/` | `vol ingest-xasset` | L4 (cross-asset spillovers) | No (market-wide) |
| `data/raw/correlation/` | `vol ingest-corr` | L7 (correlation/dispersion) | No (market-wide) |
| *(train time)* | *(no ingest)* | L5 (calendar), L6 (long-memory) | Derived |

---

## Why Source-Based, Not Layer-Per-Directory

L0, L1, and noise_robust all derive from the same ChunkStore tick fetch (the expensive part: 4-12 hours I/O). Separating them into `layer_0/` and `layer_1/` would either:

1. **Fetch ticks twice** — doubling wall-clock time, or
2. **Share a fetch step** — introducing coupling that defeats the isolation goal

Additionally, desync is a real risk: if you fix BPV (L1) and re-run `ingest-layer-1` but forget L0, you now have inconsistent `jump_variation = RV - BPV` across files with no error raised.

One file per symbol guarantees all tick-derived features are always computed together and consistent by construction. Layer isolation exists at compute time (each `FeatureLayer` class picks its columns from the shared parquet).

---

## Parallelism Strategy

### Tick-Heavy Sources (ticks, micro) — Dask LocalCluster

These sources fetch from ChunkStore, which is I/O-bound. Dask parallelizes across symbols:

```python
from dask.distributed import Client, LocalCluster

cluster = LocalCluster(n_workers=34, threads_per_worker=2, memory_limit='40GB')
client = Client(cluster)

futures = [client.submit(ingest_symbol, sym, dates) for sym in UNIVERSE]
results = client.gather(futures)
```

- **One worker per symbol** — all 34 symbols process concurrently
- **Sequential dates within each worker** — streams in batches to bound memory
- **No cross-symbol coordination needed** — each worker writes its own parquet independently

Available compute: 208 cores, 1.8 TB RAM. Using 34 workers x 2 threads leaves ~140 cores free for the Dask scheduler, OS, and other processes.

### Recommended: ThreadPoolExecutor (stdlib, no extra deps)

After implementing `vol ingest-ticks`, the actual bottleneck is clear: **network I/O** (ChunkStore REST latency ~0.2-0.6s per day-batch), not CPU. In `bars` mode (server-side aggregation) and with `LeeReady` (server-side trade classification), the client-side compute per day is negligible (<1ms for VPIN, <0.1ms for RV measures).

Given this, `concurrent.futures.ThreadPoolExecutor` with 4-8 symbol workers is the recommended approach:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=symbol_workers) as executor:
    futures = {executor.submit(ingest_symbol, sym, dates): sym for sym in UNIVERSE}
    for future in as_completed(futures):
        sym = futures[future]
        result = future.result()  # per-symbol parquet written
```

This pattern is already implemented in `vol ingest-ticks` (via `--symbol-workers N`).

### Tradeoffs: ThreadPoolExecutor vs Dask

| Factor | ThreadPoolExecutor | Dask LocalCluster |
|--------|-------------------|-------------------|
| **Dependencies** | stdlib (zero) | `dask[distributed]` (~50 MB) |
| **Startup overhead** | None | 2-5s cluster boot + dashboard |
| **Scheduling** | Simple FIFO | Work-stealing, adaptive |
| **Monitoring** | Rich progress bars (already built) | Dask dashboard (port 8787) |
| **Memory management** | Manual (GC per symbol) | Automatic spilling to disk |
| **Max useful parallelism** | ~8-12 (ChunkStore server-side limit) | Same bottleneck applies |
| **Fault tolerance** | Try/except per symbol | Worker restart, task retry |
| **When it wins** | I/O-bound, <50 tasks, simple fan-out | CPU-bound, >1000 tasks, complex DAGs |

**Key insight:** With `bars` mode and `LeeReady` processor, ChunkStore does the heavy lifting server-side. The client is just a thin REST consumer. 8 parallel threads saturate the available bandwidth without overwhelming the server. More than ~12 concurrent connections to ChunkStore yields diminishing returns (server-side queuing).

### When to revisit Dask

Dask becomes worthwhile if:
1. **Full `mode=ticks` RK backfill** — kernel estimation is O(n^2) per day, genuinely CPU-bound across ~85K day-symbol pairs
2. **BMLL L2 processing** — 10-level depth snapshots at millisecond resolution, heavy local aggregation
3. **Cross-symbol DAGs** — if future features require symbol-to-symbol relationships computed at ingest time (currently none do)

For now, keep Dask as a documented option for P3 backfill tasks but use ThreadPoolExecutor for all standard `vol ingest-*` commands.

### API-Limited Sources (iv, xasset, corr) — Sequential or Light Async

These sources hit rate-limited APIs (TSDB, Marquee). Parallelism doesn't help because the bottleneck is the API, not compute. Use simple sequential loops or `asyncio` with a rate-limiter.

---

## Microstructure Dual Output

`vol ingest-micro` produces TWO outputs from the same tick pass:

1. **Daily aggregates** → `micro/{SYMBOL}.parquet` → feeds LightGBM (tabular model)
2. **10-second bar sequences** → `micro/sequences/{SYMBOL}.parquet` → feeds LSTM/TCN (sequence model)

```
Per symbol x date:
  fetch ticks from ChunkStore (LeeReady processor)
       |
       |-- Compute per-bar features (N channels x 2,340 bars/day)
       |       -> append to micro/sequences/{SYMBOL}.parquet
       |
       +-- Aggregate bar features to daily scalars
               -> append to micro/{SYMBOL}.parquet
```

The sequence parquet stores one row per bar (not per day). Schema: `date | bar_idx | timestamp | channel_1 | channel_2 | ... | channel_N`.

At train time, the LSTM DataLoader groups by date and reshapes to `(seq_len=2340, channels=N)` tensors.

### Bar Resolution: 10 Seconds

- **2,340 bars per trading day** (6.5 hours x 360 bars/hour)
- Preserves spread dynamics, order flow momentum, and sub-minute liquidity events
- Each bar is computed FROM the raw ticks within that 10-second window
- The raw ticks themselves are never stored — only the computed bar-level features

---

## Idempotency and Incremental Ingestion

Each command checks what's already cached before fetching:

```python
def needs_ingestion(symbol: str, start: date, end: date) -> list[date]:
    """Return only the missing dates that need fetching."""
    existing = load_existing_dates(symbol)  # from parquet DatetimeIndex
    requested = trading_calendar.sessions_in_range(start, end)
    return sorted(set(requested) - set(existing))
```

- Default: skip dates already in the parquet (append-only)
- `--force`: re-fetch and overwrite everything
- `--recompute`: re-derive features from cached raw data without re-fetching from source (e.g., fix a BPV formula bug without re-downloading 11 years of ticks)
- Manifest updated atomically after each successful write

---

## Data Manifest (`data/manifest.yaml`)

### Design

The manifest serves two roles:

1. **Contract** — declares what data SHOULD exist: expected columns, value bounds, NaN budgets, symbol coverage
2. **State** — tracks what DOES exist: ingestion timestamps, lineage, row counts, integrity audit results

Ingest commands update state. `vol audit` validates state against contract.

### Schema

```yaml
meta:
  schema_version: 2
  last_full_audit: "2026-05-28T10:00:00Z"
  universe:
    symbols:
      - AAPL
      - ABBV
      # ... (34 total)
      - XOM
    count: 34
  date_range:
    start: "2015-01-02"
    end: "2024-12-31"
    trading_days: 2515

sources:
  ticks:
    description: "Daily RV panel from ChunkStore L1 tick bars (5min RTH)"
    directory: "data/raw/ticks"
    serves_layers: [L0, L1, noise_robust]
    file_pattern: "{symbol}.parquet"
    index_dtype: "datetime64[ns]"
    expected_columns:
      - rv
      - log_rv
      - rq
      - rtq
      - bpv
      - rs_positive
      - rs_negative
      - jump_stat
      - jump_indicator
      - continuous_variation
      - jump_variation
      - j_positive
      - j_negative
      - realized_skewness
      - realized_kurtosis
      - rk
      - noise_gap
      - n_ticks
      - n_bars
      - open
      - close
    value_bounds:
      rv: {min: 0.0, max: 0.25}
      bpv: {min: 0.0}
      rk: {min: 0.0}
      rs_positive: {min: 0.0}
      rs_negative: {min: 0.0}
      n_ticks: {min: 1}
      n_bars: {min: 1}
    invariants:
      - "rs_positive + rs_negative ~ rv (within 1%)"
      - "bpv <= rv * 1.5"
    nan_budget_pct: 1.0
    formula_version: "v1.0"
    formula_changelog:
      v1.0: "5min bars RTH, RK flat-top kernel, BNS jump test"
    symbols:
      AAPL:
        status: complete
        rows: 2515
        start_date: "2015-01-02"
        end_date: "2024-12-31"
        file_size_bytes: 420756
        last_ingested: "2026-05-22T10:27:33Z"
        lineage:
          code_version: "git:a1b2c3d"
          formula_version: "v1.0"
          source_query: "ChunkStore EQ db=tickDB, 5min bars, 09:30-16:00 ET"
        integrity:
          nan_pct_max: 0.0
          nan_columns: {}
          date_gaps: []
          issues: []
          last_validated: "2026-05-22T10:27:33Z"
      ABBV:
        status: missing

  iv:
    description: "Per-symbol IV surface from TSDB edrvol_ + market-wide VVIX/VIX"
    directory: "data/raw/iv"
    serves_layers: [L2]
    file_pattern: "{symbol}.parquet"
    index_dtype: "datetime64[ns]"
    expected_columns_per_symbol:
      - iv_1m_atm
      - iv_3m_atm
      - iv_1m_25dp
      - iv_1m_25dc
      - term_slope
    expected_columns_market_wide:
      _VVIX: [vvix]
      _VIX: [vix]
      _OVX: [ovx]
      _TREASURY_YIELDS: [yield_2y, yield_5y, yield_10y, yield_30y]
      _MARKET: [iv_dispersion]
    value_bounds:
      iv_1m_atm: {min: 0.0, max: 3.0}
      vvix: {min: 0.0, max: 200.0}
      vix: {min: 0.0, max: 100.0}
    nan_budget_pct: 5.0
    formula_version: "v1.0"
    formula_changelog:
      v1.0: "Direct TSDB read, no shift. IV[T] aligned with rv[T] at close."
    symbols: {}
    market_wide_files: {}

  ohlcv:
    description: "Split-adjusted daily OHLCV from TSDB eqpad_"
    directory: "data/raw/ohlcv"
    serves_layers: [L6]
    file_pattern: "{symbol}.parquet"
    index_dtype: "datetime64[ns]"
    expected_columns: [open, high, low, close, volume]
    value_bounds:
      open: {min: 0.01}
      close: {min: 0.01}
      volume: {min: 0}
    nan_budget_pct: 0.0
    formula_version: "v1.0"
    formula_changelog:
      v1.0: "Split-adjusted via TSDB eqpad_ adj fields"
    symbols: {}

  microstructure:
    description: "LeeReady daily aggregates + 10s bar sequences from ChunkStore"
    directory: "data/raw/micro"
    serves_layers: [L3]
    file_pattern: "{symbol}.parquet"
    index_dtype: "datetime64[ns]"
    expected_columns:
      - signed_volume_ratio
      - vpin
      - order_flow_imbalance
      - buy_volume
      - sell_volume
      - total_volume
    value_bounds:
      signed_volume_ratio: {min: 0.0, max: 1.0}
      vpin: {min: 0.0, max: 1.0}
      order_flow_imbalance: {min: -1.0, max: 1.0}
    nan_budget_pct: 5.0
    formula_version: "v1.0"
    formula_changelog:
      v1.0: "LeeReady tick classification, 50-bucket VPIN"
    symbols: {}

  cross_asset:
    description: "Cross-asset: yields, FX vol, credit vol, commodity vol"
    directory: "data/raw/cross_asset"
    serves_layers: [L4]
    file_pattern: "*.parquet"
    index_dtype: "datetime64[ns]"
    files:
      rates.parquet:
        expected_columns: [yield_2y, yield_5y, yield_10y, yield_30y, yield_slope_10y2y]
        status: missing
      fx_vol.parquet:
        expected_columns: [fx_vol_usdjpy, fx_vol_eurusd]
        status: missing
      credit.parquet:
        expected_columns: [hyg_iv, cdx_vol]
        status: missing
      commodity.parquet:
        expected_columns: [gld_iv, uso_iv]
        status: missing
    nan_budget_pct: 5.0
    formula_version: "v1.0"
    formula_changelog:
      v1.0: "ATM 1m IV from edrvol_ for ETF proxies; TSDB yields direct"

  correlation:
    description: "SPX implied/realized correlation from Marquee EDR_INDEX"
    directory: "data/raw/correlation"
    serves_layers: [L7]
    file_pattern: "*.parquet"
    index_dtype: "datetime64[ns]"
    files:
      spx_correlation.parquet:
        expected_columns: [implied_corr_spx_1m, realized_corr_spx_1m, corr_risk_premium]
        status: missing
    nan_budget_pct: 5.0
    formula_version: "v1.0"
    formula_changelog:
      v1.0: "Direct Marquee dataset read, CRP = implied - realized"
```

### Per-Symbol Entry Schema

```yaml
AAPL:
  status: complete         # complete | partial | missing | stale
  rows: 2515
  start_date: "2015-01-02"
  end_date: "2024-12-31"
  file_size_bytes: 420756
  last_ingested: "2026-05-22T10:27:33Z"
  lineage:
    code_version: "git:a1b2c3d"      # Short SHA of commit that produced data
    formula_version: "v1.0"          # Must match source-level formula_version
    source_query: "ChunkStore EQ db=tickDB, 5min bars, 09:30-16:00 ET"
  integrity:                          # Written by vol audit, not ingest
    nan_pct_max: 0.0
    nan_columns: {}                   # {col: pct} for any col with NaN > 0
    date_gaps: []                     # [{from, to, calendar_days}]
    issues: []                        # ["negative_rv", "extreme_rv_gt_25pct"]
    last_validated: "2026-05-22T10:27:33Z"
```

### Status Semantics

| Status | Meaning |
|--------|---------|
| `complete` | File exists, covers full date range, passes integrity checks |
| `partial` | File exists but date range is shorter than expected, or NaN > budget |
| `missing` | Symbol is in universe but no file on disk |
| `stale` | File exists but `lineage.formula_version` < source's current `formula_version` |

### Manifest Operations

- **Ingest commands** call `ManifestManager.update_symbol()` after each successful parquet write
- **`vol audit`** validates disk against manifest contract, updates only `integrity` sub-dicts
- **`vol status`** reads manifest and prints human-readable summary
- **Atomic writes** via tempfile + `os.replace()` to prevent corruption on crash
- **Stale detection** triggers automatically when source `formula_version` advances past a symbol's `lineage.formula_version`

---

## Data Integrity (Enforced Per Source)

Every ingest command applies these checks before writing output:

| Check | What | Fail Action |
|-------|------|-------------|
| Schema validation | Output columns match expected schema exactly (names, dtypes) | Abort, log mismatch |
| Date continuity | No gaps in trading day sequence (accounting for holidays) | Warn + flag in manifest |
| NaN budget | NaN fraction per column < `nan_budget_pct` | Abort if exceeded |
| Value bounds | Values within declared `value_bounds` per column | Abort + log outliers |
| Invariants | Cross-column relationships hold (e.g., `rs_pos + rs_neg ~ rv`) | Warn + flag |
| Cross-symbol consistency | Same date range for all symbols within a source | Warn + fill or truncate |

### `vol audit` Behavior

```
vol audit [--source ticks|iv|...] [--fix]
  1. Load data/manifest.yaml
  2. For each declared source: scan directory, check columns/dtypes/bounds/NaNs/gaps
  3. Update ONLY integrity sub-dicts (never touch lineage or ingest metadata)
  4. Flag: schema drift, NaN budget exceeded, missing files, stale formula versions
  5. Set meta.last_full_audit timestamp
  6. Save manifest (atomic write)
  7. Print report to stdout
  8. Exit 0 if no critical issues, exit 1 if any critical issue found
```

**Critical issues (exit 1):** schema mismatch, NaN > budget, negative RV, file declared complete but missing.
**Warnings (exit 0):** date gaps, partial coverage, stale formula versions.

---

## Formula Verification Gate

**Before implementing ANY source's feature computation, the following MUST be completed:**

1. **Locate the source paper(s)** — Find the exact equation/definition in the original academic paper (not a secondary source, not a blog post, not memory).
2. **Cross-reference our implementation** — Compare the paper's formula character-by-character against the code in `src/volforecast/features/` and `src/volforecast/data/`. Check: scaling factors, annualization constants, log vs level, summation bounds, time alignment.
3. **Validate on synthetic data** — Construct a minimal synthetic tick/bar dataset where the correct answer is known analytically. Run our code on it. Does it match?
4. **Validate on real data** — Spot-check 3-5 random symbol x date pairs against a manual calculation (e.g., in a notebook cell-by-cell).
5. **Document the verification** — Record which paper, which equation number, any discrepancies found, and the resolution.

**Why this is non-negotiable:** Trial-002 failed entirely because a `pd.concat` index mismatch doubled rows silently. Trial-019 revealed our IV alignment was using T-1 instead of T. These were NOT caught by tests — they were caught by anomalous QLIKE results AFTER training. Formula errors compound silently in ML pipelines because the model "adapts" to wrong inputs and still produces plausible loss numbers.

**Known verification debt (existing code):**
- [ ] RQ formula: paper uses `(n/3) * sum(r^4)` — verify our scaling factor matches Barndorff-Nielsen & Shephard (2002)
- [ ] BPV: verify `(pi/2)` constant and whether we use overlapping or non-overlapping products
- [ ] Semivariances: verify indicator function handles r=0 correctly
- [ ] VRP construction: Bollerslev (2009) uses realized vs implied over SAME horizon — verify alignment
- [ ] Realized kernel: verify bandwidth selection matches Barndorff-Nielsen et al. (2008) flat-top kernel
- [ ] Jump test statistic: verify BNS (2006) vs ABD (2010) — which are we using?

---

## Pipeline Integration (Train Time)

At train time, the feature pipeline loads from source directories. Each `FeatureLayer` class picks its columns from the appropriate source file:

```python
class HARCoreLayer(FeatureLayer):
    """Uses rv, rq from ticks/{symbol}.parquet."""
    def compute(self, daily_data: pd.DataFrame, *, context=None) -> pd.DataFrame:
        # daily_data already has rv, rq, etc. from the ticks parquet
        return pd.DataFrame({
            "log_rv_d": np.log(daily_data["rv"]),
            "log_rv_w": np.log(daily_data["rv"].rolling(5).mean()),
            ...
        })

class AsymmetryLayer(FeatureLayer):
    """Uses rs_positive, rs_negative, bpv from SAME ticks/{symbol}.parquet."""
    ...
```

The tournament loader reads `ticks/{symbol}.parquet` once per symbol; all tick-derived layers operate on the same DataFrame. This is unchanged from the current architecture — the source file is the same `data/raw/rv/{symbol}.parquet` (renamed to `ticks/` in migration).

---

## Data Source Details

| Source | System | Access Method | Rate Limited? | Wall-Clock Estimate |
|--------|--------|---------------|---------------|---------------------|
| ticks | ChunkStore (L1 tick bars) | `pytickclient` / `fetch_bars()` | No (I/O bound) | 4-12 hrs (full) |
| iv | TSDB `edrvol_` namespace | HTTP API | Yes (~1/sec) | 30-60 min |
| ohlcv | TSDB `eqpad_` | HTTP API | Yes (~1/sec) | 15-30 min |
| micro | ChunkStore (LeeReady processor) | `pytickclient` | No (I/O bound) | 4-12 hrs (full) |
| cross_asset | TSDB `eqpad_`/`eqsp_s_` + Marquee | HTTP API | Yes | 10-20 min |
| correlation | Marquee `EDR_INDEX_*` datasets | HTTP API | Yes (~5/sec) | 5-10 min |

---

## Implementation Order

### Step 1: Manifest System (Foundation)

Build the `ManifestManager` and seed `data/manifest.yaml` from existing data. No directory moves.

| Task | Description |
|------|-------------|
| Tests | `src/tests/test_manifest.py` — TDD: load, save, update, validate |
| ManifestManager | `src/volforecast/utils/manifest.py` — YAML I/O, typed models, atomic writes |
| Audit refactor | `src/volforecast/cli/audit.py` — validate-against-manifest mode |
| Seed | Migrate `data/manifest.json` content into `data/manifest.yaml` |
| Wire up | Existing ingest commands call `update_symbol()` after writes |
| Delete | Remove `data/manifest.json` and old JSON code paths |

### Step 2: Directory Rename + Path Migration

Hard cutover: rename directories, update `paths.py`, verify all tests pass.

| Task | Description |
|------|-------------|
| Rename dirs | `rv/` -> `ticks/`, `iv_surface/` -> `iv/` |
| Update paths.py | New helpers: `ticks_cache_dir()`, `ticks_cache_path()` |
| Update references | `IVSurfaceLayer`, `load_iv_cache()`, tournament loader, CLI commands |
| Update manifest | Change `directory` fields to new paths |
| Verify | `vol run --skip-ingest` with LOCKED config still produces same QLIKE |

### Step 3: New Source Ingestion (one at a time)

Each new source follows the same pattern: implement fetcher, add manifest schema, write tests, verify on real data.

| Priority | Source | Effort | Dependency |
|----------|--------|--------|------------|
| P0 | `vol ingest-ohlcv` | Low | Step 2 complete |
| P1 | `vol ingest-xasset` | Low-Medium | Step 2 complete |
| P1 | `vol ingest-micro` | High | Step 2 complete, LeeReady validation |
| P1 | `vol ingest-corr` | Low | Step 2 complete, Marquee access |
| P2 | Expand `vol ingest-iv` (skew, butterfly, varswap VRP) | Medium | Step 2 complete |

---

## Migration Plan (Current State -> Target State)

### Current Directory Mapping

| Current Path | Target Path | Change |
|-------------|-------------|--------|
| `data/raw/rv/{SYM}.parquet` | `data/raw/ticks/{SYM}.parquet` | Rename dir |
| `data/raw/iv_surface/{SYM}.parquet` | `data/raw/iv/{SYM}.parquet` | Rename dir |
| `data/raw/iv_surface/_VVIX.parquet` | `data/raw/iv/_VVIX.parquet` | Rename dir |
| `data/raw/iv_surface/_VIX.parquet` | `data/raw/iv/_VIX.parquet` | Rename dir |
| `data/raw/iv_surface/_OVX.parquet` | `data/raw/iv/_OVX.parquet` | Rename dir |
| `data/raw/iv_surface/_TREASURY_YIELDS.parquet` | `data/raw/iv/_TREASURY_YIELDS.parquet` | Rename dir |
| `data/raw/iv_surface/_MARKET.parquet` | `data/raw/iv/_MARKET.parquet` | Rename dir |
| `data/raw/ohlcv/` | `data/raw/ohlcv/` | No change |
| `data/raw/micro/` | `data/raw/micro/` | No change |
| `data/raw/macro/` | `data/raw/cross_asset/` | Rename dir |
| *(new)* | `data/raw/correlation/` | Create |
| `data/manifest.json` | `data/manifest.yaml` | Format change |
| `data/processed/iv_features_spx.parquet` | *(delete)* | Legacy, replaced by per-symbol IV |

### Code Files Requiring Updates (Step 2)

| File | Change |
|------|--------|
| `src/volforecast/utils/paths.py` | Rename functions: `rv_cache_dir` -> `ticks_cache_dir`, add new source helpers |
| `src/volforecast/features/iv_surface.py` | Update `load_iv_cache()` call to use new path |
| `src/volforecast/data/edrvol.py` | Update `iv_cache_dir()` reference |
| `src/volforecast/evaluation/tournament.py` | Update `rv_cache_path()` calls |
| `src/volforecast/cli/backfill_rk.py` | Update output path |
| `src/volforecast/cli/ingest_edrvol.py` | Update output path |
| `src/volforecast/__main__.py` | Update CLI dispatch |
| `data/README.md` | Update directory layout documentation |

---

## Lessons Learned (from Feature Set Audit)

1. **SPX-only assumption for IV features was wrong.** We have per-symbol IV for all 25 equities — 25x more signal density for pooled training.
2. **Microstructure assumed E-mini only.** LeeReady processor gives signed volume for all 34 symbols at zero marginal cost. BMLL gives full depth for 2023+.
3. **Cross-asset features were theoretical.** Most original symbols (fx/rates/credit via dedicated TSDB prefixes) don't work. But ETF proxies + Marquee datasets DO work.
4. **Correlation layer completely missing.** EDR_INDEX_IMPLIEDCORR is verified with 10+ years of history — a known h=22 regime predictor never in the original spec.
5. **Variance swap VRP not considered.** Per-symbol market-implied VRP (from EDRVS) is strictly superior to the model-dependent HAR-based VRP currently used.
6. **Earnings proximity was a placeholder.** EDRVOL_PERCENT_EXPIRY provides a data-driven, per-symbol, no-static-file-needed earnings proximity signal via IV term structure kinks.
7. **~9 "dead" features in original spec.** Several original features referenced data sources that return 500/404 errors. The original set was partly aspirational, not empirical.
