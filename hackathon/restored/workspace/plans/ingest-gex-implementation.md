# Implementation Plan: `vol ingest-gex` — Batch GEX Backfill

**Date:** 2026-07-07
**Status:** Ready for `/execute`
**Estimated subagents:** 5 (sequential, depth=1)

---

## Overview

Build `vol ingest-gex` CLI command that fetches per-strike SPX option chain data from QSP OptionPrices API, computes daily GEX aggregates, and stores as parquet. Uses SPX (securityId=108105, European-style, cash-settled, institutional GEX).

## Architecture

| Layer | File | Responsibility |
|-------|------|----------------|
| **CLI** | `src/volforecast/cli/ingest_gex.py` | Args, date range, StageProgress, calls data layer |
| **Data** | `src/volforecast/data/gex_ingest.py` | QSP API client, pagination, cookie mgmt, raw→aggregate |
| **Existing** | `src/volforecast/data/options_oi.py` | `compute_gex()` / `build_gex_features()` — reuse as-is |
| **Registration** | `src/volforecast/__main__.py` | Register `ingest-gex` subcommand |

## Output Schema

```
data/raw/options_oi/spx_gex_daily.parquet
```

| Column | Type | Description |
|--------|------|-------------|
| `date` | date | Observation date |
| `spot` | float64 | SPX close from SecurityTimeseries |
| `gex_net` | float64 | Net dealer GEX ($ notional) |
| `gex_call` | float64 | Dealer GEX from calls (negative = short gamma) |
| `gex_put` | float64 | Dealer GEX from puts (positive = long gamma) |
| `gex_sign` | int8 | +1 if net > 0 (long gamma), -1 otherwise |
| `oi_total` | int64 | Total open interest (calls + puts) |
| `oi_call` | int64 | Call open interest |
| `oi_put` | int64 | Put open interest |
| `oi_pcr` | float64 | Put/Call OI ratio |
| `n_valid` | int32 | Contracts with valid gamma + OI > 0 |
| `n_total` | int32 | Total contracts returned |

---

## Execution Sequence

```
Subagent 1: Data layer tests (TDD)
     ↓
Subagent 2: Data layer implementation (gex_ingest.py)
     ↓
Subagent 3: CLI tests (TDD)
     ↓
Subagent 4: CLI implementation (ingest_gex.py) + registration
     ↓
Subagent 5: Integration verification (full test suite)
```

---

## Subagent 1: Data Layer Tests (TDD)

### Context Packet

```yaml
subtask_id: execute-1
goal: "Write comprehensive unit tests for gex_ingest.py covering QSP response parsing, GEX aggregation, cache logic, and auth session creation."
file_scope:
  - src/volforecast/data/options_oi.py           # existing GEX computation API
  - src/tests/unit/test_options_oi.py            # existing test patterns
  - workspace/tmp/query_gex.py                   # verified API response structure
  - workspace/tmp/session-handoff.md             # API details (lines 85-120)
write_scope:
  - src/tests/unit/test_gex_ingest.py
acceptance_criteria:
  - "File exists at src/tests/unit/test_gex_ingest.py"
  - "All tests FAIL when run (no implementation yet) — ImportError from gex_ingest is acceptable"
  - "Tests cover: (1) parse_option_chain_response, (2) aggregate_gex_from_contracts, (3) load/save cache, (4) incremental date skip logic, (5) invalid gamma filtering (-99.99), (6) strike milli-dollar conversion"
constraints:
  - "TDD: tests define the interface — implementation comes later"
  - "Use pytest fixtures with synthetic data (no live API calls)"
  - "Import from volforecast.data.gex_ingest (does not exist yet — tests will ImportError)"
  - "ALL terminal commands use isBackground=true and ./vol exec or ./vol bg"
  - "Kill all terminals before returning"
context_summary: |
  We are building a GEX (Gamma Exposure) ingestion pipeline that fetches per-strike
  SPX option chain data from the Quantum QSP REST API (base URL: 
  https://pwm.qsp.url.gs.com:7070/quantumServicePortal/rest/api/{endpoint}/4).
  SPX securityId=108105. The API returns ~14K contracts per day with fields: gamma, 
  openInterest, contractSize, strike (milli-dollars, e.g. 5500000=$5500), callPut ("C"/"P"),
  expiration. Invalid gamma is marked -99.99. Pagination via scrollId cursor.
  Auth is GSSSO cookie obtained via curl --negotiate to authn.web.gs.com.
  
  The data layer (gex_ingest.py) will expose:
  - fetch_gex_daily(date, security_id, session) -> dict | None
  - backfill_gex(start, end, security_id, force, on_progress) -> DataFrame
  - get_qsp_session() -> requests.Session
  - load_gex_cache() -> DataFrame
  - save_gex_cache(df) -> None
  
  GEX formula (dealer perspective):
    GEX_call = -OI_call × gamma × contractSize × spot × 0.01
    GEX_put  = +OI_put × gamma × contractSize × spot × 0.01
    net_gex  = GEX_call + GEX_put
  
  Cache path: data/raw/options_oi/spx_gex_daily.parquet
  Existing test style: see src/tests/unit/test_options_oi.py for patterns.
```

### Subagent Prompt

```
You are implementing Step 1 of a 5-step plan to build `vol ingest-gex`.
Your task is to write FAILING unit tests that define the interface for 
src/volforecast/data/gex_ingest.py (which does not exist yet).

CONTEXT PACKET:
subtask_id: execute-1
goal: Write comprehensive unit tests for gex_ingest.py covering QSP response parsing, GEX aggregation, cache logic, and auth session creation.

file_scope:
  - src/volforecast/data/options_oi.py
  - src/tests/unit/test_options_oi.py
  - workspace/tmp/query_gex.py
  - workspace/tmp/session-handoff.md (lines 85-120 for API details)

write_scope:
  - src/tests/unit/test_gex_ingest.py

CONTEXT SUMMARY:
We are building a GEX (Gamma Exposure) ingestion pipeline that fetches per-strike
SPX option chain data from the Quantum QSP REST API (base URL: 
https://pwm.qsp.url.gs.com:7070/quantumServicePortal/rest/api/{endpoint}/4).
SPX securityId=108105. The API returns ~14K contracts per day with fields: gamma, 
openInterest, contractSize, strike (milli-dollars, e.g. 5500000=$5500), callPut ("C"/"P"),
expiration. Invalid gamma is marked -99.99. Pagination via scrollId cursor.
Auth is GSSSO cookie obtained via curl --negotiate to authn.web.gs.com.

The data layer (gex_ingest.py) will expose:
- parse_option_prices_response(json_data: dict) -> list[dict]
  Extracts flat list of option contracts from nested QSP response structure.
- aggregate_gex(contracts: list[dict], spot: float) -> dict
  Filters invalid gamma, converts strikes, computes GEX aggregates.
- fetch_spot_price(session, security_id, target_date) -> float | None
  Gets underlying spot from SecurityTimeseries endpoint.
- fetch_option_chain(session, security_id, target_date) -> list[dict]
  Fetches full chain with scrollId pagination.
- fetch_gex_daily(target_date, security_id, session) -> dict | None
  Orchestrates spot + chain fetch + aggregation for one day.
- get_qsp_session() -> requests.Session
  Creates session with GSSSO cookie from Kerberos negotiate.
- load_gex_cache() -> pd.DataFrame
  Loads existing parquet (empty DF if missing).
- save_gex_cache(df: pd.DataFrame) -> None
  Atomic write (tempfile + os.replace).

GEX formula (dealer perspective):
  GEX_call = -OI_call × gamma × contractSize × spot × 0.01
  GEX_put  = +OI_put × gamma × contractSize × spot × 0.01
  net_gex  = GEX_call + GEX_put

Cache path: data/raw/options_oi/spx_gex_daily.parquet

ACCEPTANCE CRITERIA:
1. File exists at src/tests/unit/test_gex_ingest.py
2. Tests import from volforecast.data.gex_ingest (will fail with ImportError — that's expected)
3. Tests cover: parse_option_prices_response, aggregate_gex, fetch_option_chain (mocked),
   load/save cache, incremental skip logic, invalid gamma filtering, milli-dollar strike conversion
4. Use pytest fixtures with synthetic data — no live API calls
5. Follow existing test patterns from src/tests/unit/test_options_oi.py

CONSTRAINTS:
- TDD: tests define the interface
- ALL terminal commands use isBackground=true and ./vol exec or ./vol bg
- Kill all spawned terminals before returning your final response
- Do NOT modify any file outside write_scope

Read the file_scope files first to understand existing patterns, then write the tests.
Return: status, files_changed, verification evidence.
```

---

## Subagent 2: Data Layer Implementation

### Context Packet

```yaml
subtask_id: execute-2
goal: "Implement src/volforecast/data/gex_ingest.py — QSP API client with pagination, GSSSO auth, GEX aggregation, and parquet cache management. All tests from execute-1 must pass."
file_scope:
  - src/tests/unit/test_gex_ingest.py            # tests to satisfy
  - src/volforecast/data/options_oi.py           # existing patterns (lines 1-50 for imports/constants)
  - src/volforecast/data/ohlcv.py                # cache pattern reference
  - src/volforecast/utils/paths.py               # data_path() helper
  - src/volforecast/utils/manifest.py            # record_ingestion_yaml()
  - workspace/tmp/query_gex.py                   # working API code to adapt
  - workspace/tmp/session-handoff.md             # API quick reference (lines 85-120)
write_scope:
  - src/volforecast/data/gex_ingest.py
acceptance_criteria:
  - "All tests in src/tests/unit/test_gex_ingest.py pass"
  - "Functions: parse_option_prices_response, aggregate_gex, fetch_spot_price, fetch_option_chain, fetch_gex_daily, get_qsp_session, load_gex_cache, save_gex_cache all exist"
  - "No lint errors (run ./vol lint on the file)"
constraints:
  - "Do NOT modify tests — make implementation match the test expectations"
  - "Use requests library for HTTP (already in dependencies)"
  - "GSSSO cookie obtained via subprocess curl --negotiate (see memory/_dormant/ref/gssso-auth.md pattern)"
  - "Retry logic: 3 attempts with exponential backoff (2s, 4s, 8s)"
  - "On 401: refresh cookie, retry once"
  - "Filter contracts where gamma == -99.99 or openInterest <= 0"
  - "Strike conversion: divide by 1000 (milli-dollars)"
  - "Atomic write: tempfile + os.replace for parquet save"
  - "ALL terminal commands use isBackground=true and ./vol exec or ./vol bg"
  - "Kill all terminals before returning"
context_summary: |
  Step 2 of 5. Tests already exist at src/tests/unit/test_gex_ingest.py.
  Your job is to implement the module they test. The QSP API has been verified working
  (see workspace/tmp/query_gex.py for a proven script). Adapt that code into a clean
  module with proper error handling, retry logic, and caching.
  
  API details:
  - Base: https://pwm.qsp.url.gs.com:7070/quantumServicePortal/rest/api/{endpoint}/4
  - OptionPrices: returns optionsPriceData[].data[].price[] (nested 3 levels)
  - SecurityTimeseries: returns securities[].data[].securityPrices[].closePrice
  - scrollId pagination: pass scrollId param on subsequent pages until empty response
  - Auth: GSSSO cookie from `curl -s --negotiate -u : -L -c - "https://authn.web.gs.com/desktopsso/Login"`
  - SPX securityId: "108105"
  - Invalid markers: gamma=-99.99 means not computed
  - Strikes in milli-dollars: 5500000 = $5500.00
  
  GEX formula:
    For each contract with valid gamma and OI > 0:
      if callPut == "C": gex = -gamma * oi * contractSize * spot * 0.01
      if callPut == "P": gex = +gamma * oi * contractSize * spot * 0.01
    Aggregate: gex_net = sum(all gex), gex_call = sum(call gex), gex_put = sum(put gex)
    gex_sign = +1 if gex_net > 0 else -1
  
  Cache: data/raw/options_oi/spx_gex_daily.parquet
  Use volforecast.utils.paths.data_path("raw/options_oi", "spx_gex_daily.parquet")
```

### Subagent Prompt

```
You are implementing Step 2 of a 5-step plan to build `vol ingest-gex`.
Your task is to implement src/volforecast/data/gex_ingest.py so that all
existing tests in src/tests/unit/test_gex_ingest.py pass.

CONTEXT PACKET:
subtask_id: execute-2
goal: Implement src/volforecast/data/gex_ingest.py — QSP API client with pagination, GSSSO auth, GEX aggregation, and parquet cache management.

file_scope:
  - src/tests/unit/test_gex_ingest.py
  - src/volforecast/data/options_oi.py (lines 1-50)
  - src/volforecast/data/ohlcv.py (cache pattern)
  - src/volforecast/utils/paths.py
  - workspace/tmp/query_gex.py (working API code)
  - workspace/tmp/session-handoff.md (lines 85-120)

write_scope:
  - src/volforecast/data/gex_ingest.py

CONTEXT SUMMARY:
Tests already exist. Implement the module to make them pass. The QSP API is verified
working — adapt workspace/tmp/query_gex.py into a production module with:
- Proper GSSSO auth (curl --negotiate to authn.web.gs.com)
- scrollId pagination for large responses
- Retry with exponential backoff (3 attempts, 2s/4s/8s)
- Cookie refresh on 401
- Invalid gamma filtering (-99.99) and zero-OI filtering
- Strike milli-dollar conversion (÷1000)
- Atomic parquet writes (tempfile + os.replace)
- Logging via standard logging module

API structure:
- Base URL: https://pwm.qsp.url.gs.com:7070/quantumServicePortal/rest/api/{endpoint}/4
- OptionPrices response: {"optionsPriceData": [{"data": [{"price": [...]}]}], "scrollId": "..."}
- SecurityTimeseries response: {"securities": [{"data": [{"securityPrices": [{"closePrice": ...}]}]}]}
- SPX securityId: "108105"

GEX formula (dealer perspective):
  call contracts: gex = -gamma × OI × contractSize × spot × 0.01
  put contracts:  gex = +gamma × OI × contractSize × spot × 0.01
  net = sum_all, sign = +1 if net > 0 else -1

ACCEPTANCE CRITERIA:
1. All tests in test_gex_ingest.py pass (run: ./vol test -x -q -k test_gex_ingest)
2. No lint errors (run: ./vol lint src/volforecast/data/gex_ingest.py)
3. All public functions from the test imports exist and work correctly

CONSTRAINTS:
- Do NOT modify any test file
- Use requests for HTTP
- ALL terminal commands: isBackground=true, use ./vol exec or ./vol bg
- Kill all terminals before returning
- Return: status, files_changed, verification evidence (test output)
```

---

## Subagent 3: CLI Tests (TDD)

### Context Packet

```yaml
subtask_id: execute-3
goal: "Write unit tests for src/volforecast/cli/ingest_gex.py covering register(), handle(), and run() with mocked data layer."
file_scope:
  - src/volforecast/cli/ingest_ohlcv.py          # CLI pattern reference
  - src/volforecast/cli/progress.py              # StageProgress API (lines 260-340)
  - src/volforecast/data/gex_ingest.py           # data layer API to mock
write_scope:
  - src/tests/unit/test_ingest_gex_cli.py
acceptance_criteria:
  - "File exists at src/tests/unit/test_ingest_gex_cli.py"
  - "Tests FAIL with ImportError (module not yet created)"
  - "Tests cover: (1) register adds 'ingest-gex' parser, (2) handle parses dates correctly, (3) run calls backfill_gex with correct args, (4) run returns 0 on success / 1 on failure, (5) --force flag passes through"
constraints:
  - "TDD: tests define the CLI interface"
  - "Mock volforecast.data.gex_ingest.backfill_gex and related functions"
  - "Do NOT test progress bar rendering (that's integration-level)"
  - "ALL terminal commands use isBackground=true and ./vol exec or ./vol bg"
  - "Kill all terminals before returning"
context_summary: |
  Step 3 of 5. The data layer (gex_ingest.py) is implemented. Now write tests
  for the CLI wrapper that will call it. Follow the exact pattern from 
  src/volforecast/cli/ingest_ohlcv.py:
  
  - register(subparsers): adds "ingest-gex" with args --start, --end, --security-id, --force
  - handle(args): parses ISO dates, calls run()
  - run(start_date, end_date, security_id, force): uses StageProgress, iterates trading days,
    calls fetch_gex_daily per day, saves cache, records manifest, returns exit code
  
  Default: --start 2015-01-02, --end yesterday, --security-id 108105
```

### Subagent Prompt

```
You are implementing Step 3 of a 5-step plan to build `vol ingest-gex`.
Your task is to write FAILING unit tests for the CLI layer (ingest_gex.py).

CONTEXT PACKET:
subtask_id: execute-3
goal: Write unit tests for src/volforecast/cli/ingest_gex.py covering register(), handle(), and run().

file_scope:
  - src/volforecast/cli/ingest_ohlcv.py (CLI pattern to mirror)
  - src/volforecast/cli/progress.py (lines 260-340 for StageProgress API)
  - src/volforecast/data/gex_ingest.py (data layer to mock)

write_scope:
  - src/tests/unit/test_ingest_gex_cli.py

CONTEXT SUMMARY:
The data layer (gex_ingest.py) exists with functions:
- fetch_gex_daily(date, security_id, session) -> dict | None
- backfill_gex(start, end, security_id, force, on_progress) -> DataFrame
- get_qsp_session() -> requests.Session
- load_gex_cache() -> DataFrame
- save_gex_cache(df) -> None

The CLI module (not yet written) will follow ingest_ohlcv.py pattern:
- register(subparsers): add_parser("ingest-gex") with --start, --end, --security-id, --force
- handle(args): parse dates, call run(), return exit code
- run(start_date, end_date, security_id="108105", force=False) -> int:
    Uses StageProgress("ingest", "gex", ["SPX"])
    Loads cache, determines which dates to fetch
    Iterates trading days, calls fetch_gex_daily for each
    Saves updated cache
    Calls record_ingestion_yaml
    Returns 0 on success, 1 on partial failure

ACCEPTANCE CRITERIA:
1. File exists at src/tests/unit/test_ingest_gex_cli.py
2. Tests import from volforecast.cli.ingest_gex (will fail with ImportError)
3. Tests mock the data layer (no live API calls)
4. Tests cover: register, handle, run success path, run failure path, --force

CONSTRAINTS:
- TDD: tests define CLI interface
- Mock all data layer calls
- ALL terminal commands: isBackground=true
- Kill all terminals before returning
- Return: status, files_changed, verification evidence
```

---

## Subagent 4: CLI Implementation + Registration

### Context Packet

```yaml
subtask_id: execute-4
goal: "Implement src/volforecast/cli/ingest_gex.py and register it in __main__.py. All CLI tests from execute-3 must pass."
file_scope:
  - src/tests/unit/test_ingest_gex_cli.py        # tests to satisfy
  - src/volforecast/cli/ingest_ohlcv.py          # pattern to follow exactly
  - src/volforecast/cli/progress.py              # StageProgress usage (lines 260-340)
  - src/volforecast/__main__.py                  # registration point (lines 186-200)
  - src/volforecast/data/gex_ingest.py           # data layer to call
  - src/volforecast/data/trading_calendar.py     # for trading day enumeration
  - src/volforecast/utils/manifest.py            # record_ingestion_yaml signature
write_scope:
  - src/volforecast/cli/ingest_gex.py
  - src/volforecast/__main__.py
acceptance_criteria:
  - "All tests in test_ingest_gex_cli.py pass"
  - "ingest-gex appears in vol help output"
  - "No lint errors on new/modified files"
constraints:
  - "Do NOT modify tests"
  - "Follow ingest_ohlcv.py pattern exactly for structure"
  - "StageProgress with outer bar = trading days, log lines per day"
  - "Registration in __main__.py follows the same import+register pattern as other ingest commands"
  - "ALL terminal commands use isBackground=true and ./vol exec or ./vol bg"
  - "Kill all terminals before returning"
context_summary: |
  Step 4 of 5. Tests exist for the CLI. Implement the module and register it.
  
  The CLI should:
  1. register(): add_parser("ingest-gex") with --start (default 2015-01-02), 
     --end (default yesterday), --security-id (default 108105), --force flag
  2. handle(args): parse ISO date strings, call run()
  3. run(start_date, end_date, security_id, force):
     - Import and use StageProgress("ingest", "gex", [f"SPX ({security_id})"])
     - Load existing cache via load_gex_cache()
     - Determine trading days in range (use pandas bdate_range or trading_calendar)
     - Skip dates already in cache unless --force
     - Create QSP session via get_qsp_session()
     - For each date: fetch_gex_daily, log result, advance progress
     - After loop: save_gex_cache, record_ingestion_yaml
     - Return 0 if all succeed, 1 if any failures
  
  Registration in __main__.py: add after ingest-micro block (line ~196):
    from volforecast.cli.ingest_gex import register as _reg_ingest_gex
    _reg_ingest_gex(subparsers)
```

### Subagent Prompt

```
You are implementing Step 4 of a 5-step plan to build `vol ingest-gex`.
Your task is to implement the CLI module and register it in __main__.py.

CONTEXT PACKET:
subtask_id: execute-4
goal: Implement src/volforecast/cli/ingest_gex.py and register it in __main__.py so all CLI tests pass.

file_scope:
  - src/tests/unit/test_ingest_gex_cli.py (tests to satisfy)
  - src/volforecast/cli/ingest_ohlcv.py (pattern to follow)
  - src/volforecast/cli/progress.py (StageProgress API, lines 260-340)
  - src/volforecast/__main__.py (registration point, lines 186-200)
  - src/volforecast/data/gex_ingest.py (data layer)
  - src/volforecast/utils/manifest.py (record_ingestion_yaml)

write_scope:
  - src/volforecast/cli/ingest_gex.py
  - src/volforecast/__main__.py

CONTEXT SUMMARY:
Tests exist at src/tests/unit/test_ingest_gex_cli.py. Implement the CLI to pass them.

Pattern from ingest_ohlcv.py:
- register(subparsers): add "ingest-gex" parser with --start, --end, --security-id, --force
- handle(args): parse dates, delegate to run()
- run(start, end, security_id, force) -> int:
    Uses StageProgress for rich progress display
    Loads cache, skips cached dates (unless --force)
    Fetches each trading day via fetch_gex_daily
    Saves cache atomically, records manifest
    Returns 0/1 exit code

Registration: Add import + register call in __main__.py after the ingest-micro block.

ACCEPTANCE CRITERIA:
1. All tests in test_ingest_gex_cli.py pass
2. `./vol exec python -m volforecast ingest-gex --help` shows usage
3. No lint errors on ingest_gex.py and __main__.py

CONSTRAINTS:
- Do NOT modify test files
- Follow ingest_ohlcv.py structure exactly
- ALL terminal commands: isBackground=true, ./vol exec or ./vol bg
- Kill all terminals before returning
- Return: status, files_changed, verification evidence (test output + help output)
```

---

## Subagent 5: Integration Verification

### Context Packet

```yaml
subtask_id: execute-5
goal: "Run the full test suite to verify no regressions, lint all new files, and confirm vol ingest-gex --help works end-to-end."
file_scope:
  - src/tests/unit/test_gex_ingest.py
  - src/tests/unit/test_ingest_gex_cli.py
  - src/volforecast/data/gex_ingest.py
  - src/volforecast/cli/ingest_gex.py
  - src/volforecast/__main__.py
write_scope: []
acceptance_criteria:
  - "All unit tests pass (./vol test -x -q)"
  - "Lint clean on new files (./vol lint src/volforecast/data/gex_ingest.py src/volforecast/cli/ingest_gex.py)"
  - "vol ingest-gex --help produces expected output"
  - "No import errors when loading the module"
constraints:
  - "Read-only — do NOT modify any files. If tests fail, report the failure details for the orchestrator to fix."
  - "ALL terminal commands use isBackground=true and ./vol exec or ./vol bg"
  - "Kill all terminals before returning"
context_summary: |
  Step 5 of 5. All implementation is done. Run verification:
  1. ./vol test -x -q (full suite, expect 880+ tests pass)
  2. ./vol lint src/volforecast/data/gex_ingest.py src/volforecast/cli/ingest_gex.py
  3. ./vol exec python -m volforecast ingest-gex --help
  
  Report any failures with full output so the orchestrator can fix inline.
```

### Subagent Prompt

```
You are implementing Step 5 of a 5-step plan to build `vol ingest-gex`.
Your task is VERIFICATION ONLY — run tests, lint, and confirm the command works.
Do NOT modify any files.

CONTEXT PACKET:
subtask_id: execute-5
goal: Run full test suite, lint new files, confirm vol ingest-gex --help works.

file_scope:
  - src/tests/unit/test_gex_ingest.py
  - src/tests/unit/test_ingest_gex_cli.py
  - src/volforecast/data/gex_ingest.py
  - src/volforecast/cli/ingest_gex.py
  - src/volforecast/__main__.py

write_scope: [] (READ-ONLY — no modifications allowed)

VERIFICATION STEPS:
1. Run: ./vol test -x -q
   Expected: All tests pass (800+ tests including new ones)
2. Run: ./vol lint src/volforecast/data/gex_ingest.py src/volforecast/cli/ingest_gex.py
   Expected: No errors
3. Run: ./vol exec python -m volforecast ingest-gex --help
   Expected: Shows usage with --start, --end, --security-id, --force options

ACCEPTANCE CRITERIA:
1. Full test suite passes
2. Lint clean
3. Help output correct

CONSTRAINTS:
- Do NOT modify any files
- If anything fails, report FULL error output — do not attempt fixes
- ALL terminal commands: isBackground=true, ./vol exec or ./vol bg
- Kill all terminals before returning
- Return: status (complete if all pass, blocked if failures), verification evidence
```

---

## Orchestrator Responsibilities

After all subagents complete:

1. **Collect results** — verify each returned `status: complete`
2. **If any blocked** — fix inline (small fixes) or re-spawn with refined context
3. **Final todo update** — mark all steps complete
4. **Do NOT re-read files** — trust subagent verification + Subagent 5's integration test

---

## Post-Implementation Next Steps

After successful execution of this plan:

1. `/execute` — Run `vol ingest-gex --start 2015-01-02` to backfill ~2800 trading days
2. `/execute` — Wire GEX features into feature builder (Layer 2 or new Layer 7)
3. `/experiment` — Trial with GEX sign + z-score as XGBoost features (expect +10-30 bps QLIKE)
