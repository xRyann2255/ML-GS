# Plan 096: GSVIVS01 Strategy Signal Features

## Objective

Add ~73 features from the GSVIVS01 strategy's feature set into our ML vol forecasting pipeline. Run a fair tournament comparing the enriched XGBoost model against the current champion (trial-063 config) and HAR baselines.

---

## TSDB Symbol Mapping (Inferred)

The user's `data` DataFrame has 15 columns. Here is the inferred TSDB mapping and current availability:

| `data[...]` column | Inferred TSDB symbol | Currently cached? | Pipeline column name |
|---|---|---|---|
| `SPX` | SPX close price (from daily data) | **Yes** | `close` |
| `VIX` | `eqpad_.VIX@close` | **Yes** | `vix` (via `_VIX.parquet`) |
| `VIX_Open` | `eqpad_.VIX@open` | **No** (not used in any feature formula — skip) | — |
| `VX_1M` | VIX front-month futures (roll engine) | **Yes** | `vx1` (via `vix_futures` cache) |
| `IG_5Y` | IG CDX 5Y spread — TSDB TBD (could be `midas_` or `cdslevels_` namespace) | **No** | `credit_ig_5y` |
| `HY_5Y` | HY CDX 5Y spread — TSDB TBD | **No** | `credit_hy_5y` |
| `VIX_1M_50dC` | `edrvol_vix.x@1matms` (50d call ≈ ATM) | **No** | `vix_iv_1m_atm` |
| `VIX_1M_25dC` | `edrvol_vix.x@1m25dc` | **No** | `vix_iv_1m_25dc` |
| `VIX_1M_5dC` | `edrvol_vix.x@1m5dc` | **No** | `vix_iv_1m_5dc` |
| `SPX_1M_50dP` | `edrvol_spx@1matms` (50d put ≈ ATM) | **Yes** | `iv_1m_atm` |
| `SPX_1M_25dP` | `edrvol_spx@1m25dp` | **Yes** | `iv_1m_25dp` |
| `SPX_1M_5dP` | `edrvol_spx@1m5dp` | **No** | `iv_1m_5dp` |
| `SPX_3M_50dP` | `edrvol_spx@3matms` (50d put ≈ ATM) | **Yes** | `iv_3m_atm` |
| `SPX_3M_25dP` | `edrvol_spx@3m25dp` | **No** | `iv_3m_25dp` |
| `SPX_3M_5dP` | `edrvol_spx@3m5dp` | **No** | `iv_3m_5dp` |

### New data to ingest (7 items)

1. **SPX 5-delta put**: `edrvol_spx@1m5dp` → add `"1m5dp": "iv_1m_5dp"` to `_FIELD_MAP`
2. **SPX 3M 25-delta put**: `edrvol_spx@3m25dp` → add `"3m25dp": "iv_3m_25dp"`
3. **SPX 3M 5-delta put**: `edrvol_spx@3m5dp` → add `"3m5dp": "iv_3m_5dp"`
4. **VIX option ATM** (50dC ≈ ATM): `edrvol_vix.x@1matms` → new `_VIX_OPTIONS.parquet` cache
5. **VIX option 25dC**: `edrvol_vix.x@1m25dc` → same cache
6. **VIX option 5dC**: `edrvol_vix.x@1m5dc` → same cache
7. **Credit CDS** (`IG_5Y`, `HY_5Y`): → new `_CREDIT_CDS.parquet` cache (TSDB symbol TBD — user to confirm exact TSDB name if `cdslevels_CDX.NA.IG.5Y@close` doesn't work)

### Key insight: 50-delta ≈ ATM

In standard vol surface parameterization, a 50-delta option has strike ≈ forward price. The EDRVOL `1matms` field (ATM straddle = average of 50d put + 50d call) is used as the proxy for both `SPX_1M_50dP` and `SPX_3M_50dP`. These columns are **already cached** — no ingestion needed.

---

## Feature Inventory (73 features)

### Group 1: SPX Returns + Realized (6 features)

| Feature | Formula | Source |
|---|---|---|
| `spx_ret_1d` | `close.pct_change()` | `daily_data["close"]` |
| `spx_ret_3d` | `close.pct_change(3)` | `daily_data["close"]` |
| `spx_ret_5d` | `close.pct_change(5)` | `daily_data["close"]` |
| `spx_rea_1d` | `abs(spx_ret_1d) * sqrt(252)` | derived |
| `spx_rea_5d` | `spx_ret_1d.rolling(5).std() * sqrt(252)` | derived |
| `spx_rea_20d` | `spx_ret_1d.rolling(20).std() * sqrt(252)` | derived |

*Note: Our pipeline already has `signed_return_d` (log return), `abs_ret_d`, `ret_5d`, `log_rv_d/w/m` (intraday RV). These are DIFFERENT formulations (pct_change vs log, rolling std vs intraday 5-min RV) — keep both for the model to select.*

### Group 2: VIX Returns + Realized (6 features)

| Feature | Formula | Source |
|---|---|---|
| `vix_ret_1d` | `vix.pct_change()` | `enriched_data["vix"]` |
| `vix_ret_3d` | `vix.pct_change(3)` | `enriched_data["vix"]` |
| `vix_ret_5d` | `vix.pct_change(5)` | `enriched_data["vix"]` |
| `vix_rea_1d` | `abs(vix_ret_1d) * sqrt(252)` | derived |
| `vix_rea_5d` | `vix_ret_1d.rolling(5).std() * sqrt(252)` | derived |
| `vix_rea_20d` | `vix_ret_1d.rolling(20).std() * sqrt(252)` | derived |

### Group 3: VX_1M Returns + Realized (6 features)

| Feature | Formula | Source |
|---|---|---|
| `vx1_ret_1d` | `vx1.pct_change()` | `enriched_data["vx1"]` |
| `vx1_ret_3d` | `vx1.pct_change(3)` | `enriched_data["vx1"]` |
| `vx1_ret_5d` | `vx1.pct_change(5)` | `enriched_data["vx1"]` |
| `vx1_rea_1d` | `abs(vx1_ret_1d) * sqrt(252)` | derived |
| `vx1_rea_5d` | `vx1_ret_1d.rolling(5).std() * sqrt(252)` | derived |
| `vx1_rea_20d` | `vx1_ret_1d.rolling(20).std() * sqrt(252)` | derived |

### Group 4: VIX Vol (vol-of-vol) Dynamics (6 features)

Uses `VIX_1M_50dC` ≈ VIX ATM option IV. Cached as `vix_iv_1m_atm` in `_VIX_OPTIONS.parquet`.

| Feature | Formula | Source |
|---|---|---|
| `vix_vol_ret_1d` | `vix_iv_1m_atm.pct_change()` | `enriched_data["vix_iv_1m_atm"]` |
| `vix_vol_ret_3d` | `vix_iv_1m_atm.pct_change(3)` | " |
| `vix_vol_ret_5d` | `vix_iv_1m_atm.pct_change(5)` | " |
| `vix_vol_diff_1d` | `vix_iv_1m_atm.diff()` | " |
| `vix_vol_diff_3d` | `vix_iv_1m_atm.diff(3)` | " |
| `vix_vol_diff_5d` | `vix_iv_1m_atm.diff(5)` | " |

### Group 5: VIX Option Skew (12 features)

Three skew definitions from VIX option surface, each with level + 3 diffs:

| Feature | Formula | Source |
|---|---|---|
| `vix_skew_50d25d` | `vix_iv_1m_atm - vix_iv_1m_25dc` | enriched_data |
| `vix_skew_50d25d_diff_1d/3d/5d` | `.diff(1/3/5)` | derived |
| `vix_skew_50d5d` | `vix_iv_1m_atm - vix_iv_1m_5dc` | enriched_data |
| `vix_skew_50d5d_diff_1d/3d/5d` | `.diff(1/3/5)` | derived |
| `vix_skew_25d5d` | `vix_iv_1m_25dc - vix_iv_1m_5dc` | enriched_data |
| `vix_skew_25d5d_diff_1d/3d/5d` | `.diff(1/3/5)` | derived |

### Group 6: VIX Term Structure (4 features)

| Feature | Formula | Source |
|---|---|---|
| `vix_ts_level` | `vix / vx1 - 1` | `enriched_data["vix"]`, `enriched_data["vx1"]` |
| `vix_ts_diff_1d` | `vix_ts_level.diff()` | derived |
| `vix_ts_diff_3d` | `vix_ts_level.diff(3)` | derived |
| `vix_ts_diff_5d` | `vix_ts_level.diff(5)` | derived |

### Group 7: SPX 1M Skew (12 features)

Three skew definitions using SPX 1M put IV surface:
- 50d = ATM (`iv_1m_atm`), 25d = `iv_1m_25dp`, 5d = `iv_1m_5dp`

| Feature | Formula | Source |
|---|---|---|
| `spx_skew_50d25d_1m` | `iv_1m_atm - iv_1m_25dp` | enriched_data |
| `spx_skew_50d25d_1m_diff_1d/3d/5d` | `.diff(1/3/5)` | derived |
| `spx_skew_50d5d_1m` | `iv_1m_atm - iv_1m_5dp` | enriched_data |
| `spx_skew_50d5d_1m_diff_1d/3d/5d` | `.diff(1/3/5)` | derived |
| `spx_skew_25d5d_1m` | `iv_1m_25dp - iv_1m_5dp` | enriched_data |
| `spx_skew_25d5d_1m_diff_1d/3d/5d` | `.diff(1/3/5)` | derived |

### Group 8: SPX Skew Term Structure (15 features)

3M skew levels (intermediate), 1M/3M skew ratios + dynamics:

| Feature | Formula | Source |
|---|---|---|
| `spx_skew_50d25d_3m` | `iv_3m_atm - iv_3m_25dp` | enriched_data |
| `spx_skew_50d5d_3m` | `iv_3m_atm - iv_3m_5dp` | enriched_data |
| `spx_skew_25d5d_3m` | `iv_3m_25dp - iv_3m_5dp` | enriched_data |
| `spx_skew_ts_50d25d` | `spx_skew_50d25d_1m / spx_skew_50d25d_3m` | derived |
| `spx_skew_ts_50d25d_ret_1d/3d/5d` | `.pct_change(1/3/5)` | derived |
| `spx_skew_ts_50d5d` | `spx_skew_50d5d_1m / spx_skew_50d5d_3m` | derived |
| `spx_skew_ts_50d5d_ret_1d/3d/5d` | `.pct_change(1/3/5)` | derived |
| `spx_skew_ts_25d5d` | `spx_skew_25d5d_1m / spx_skew_25d5d_3m` | derived |
| `spx_skew_ts_25d5d_ret_1d/3d/5d` | `.pct_change(1/3/5)` | derived |

### Group 9: Credit CDS Returns (6 features)

| Feature | Formula | Source |
|---|---|---|
| `credit_ig_ret_1d` | `credit_ig_5y.pct_change()` | `enriched_data["credit_ig_5y"]` |
| `credit_ig_ret_3d` | `credit_ig_5y.pct_change(3)` | " |
| `credit_ig_ret_5d` | `credit_ig_5y.pct_change(5)` | " |
| `credit_hy_ret_1d` | `credit_hy_5y.pct_change()` | `enriched_data["credit_hy_5y"]` |
| `credit_hy_ret_3d` | `credit_hy_5y.pct_change(3)` | " |
| `credit_hy_ret_5d` | `credit_hy_5y.pct_change(5)` | " |

### Total: 73 features (6+6+6+6+12+4+12+15+6)

---

## Architecture Decisions

### 1. Single new feature layer: `gsvivs_signals`

All 73 features go into ONE new layer rather than scattering across existing layers. Rationale:
- Existing layers (`har_core`, `asymmetry`, `options`) have clear definitions and tested behavior — don't pollute
- The GSVIVS01 features are a cohesive set from a specific trading strategy
- Clean A/B test: the only config difference between "enriched" and "champion" is the presence of `gsvivs_signals` in `feature_layers`
- Easy to add/remove from tournaments

### 2. Data flow

```
iv_surface (enrichment) → loads new VIX option + SPX 5d/3M delta + credit CDS columns
                        ↓
gsvivs_signals (feature) → reads enriched_data → produces 73 feature columns
                        ↓
tree_expansion → generates _change/_zscore derivatives of eligible features
```

Config for enriched arm:
```yaml
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar, gsvivs_signals, tree_expansion]
```

### 3. Feature naming convention

Use descriptive snake_case matching the signal category:
- `spx_ret_1d`, `vix_rea_5d`, `vx1_ret_3d` — returns/realized
- `vix_vol_ret_1d`, `vix_vol_diff_3d` — vol-of-vol
- `vix_skew_50d25d`, `vix_skew_50d5d_diff_1d` — VIX option skew
- `vix_ts_level`, `vix_ts_diff_1d` — VIX term structure
- `spx_skew_50d25d_1m`, `spx_skew_ts_50d25d` — SPX skew + term structure
- `credit_ig_ret_1d`, `credit_hy_ret_3d` — credit CDS

### 4. Tree expansion eligibility

New prefixes to add to `_EXPANDABLE_PREFIXES`:
```python
"spx_ret_", "spx_rea_", "vix_ret_", "vix_rea_",
"vx1_ret_", "vx1_rea_", "vix_vol_", "vix_skew_",
"vix_ts_", "spx_skew_", "credit_ig_", "credit_hy_",
```

---

## Implementation Steps

### Dependency Graph

```
Step 1 (data ingestion) ──→ Step 2 (iv_surface extension) ──→ Step 3 (tests) ──→ Step 4 (implementation)
                                                                                         ↓
                                                              Step 5 (tree_expansion) ←──┘
                                                                                         ↓
                                                              Step 6 (trial config) ←────┘
                                                                                         ↓
                                                              Step 7 (trial registry) ←──┘
```

All steps are sequential — each depends on the prior.

---

### Step 1: Data Ingestion — Add New TSDB Fields + Ingest `[subagent]`

Add 7 new data sources to the ingestion pipeline and run ingestion.

```yaml
subtask_id: "execute-1"
goal: "Add SPX 5d/3M delta fields to edrvol.py, add VIX options ingestion, add credit CDS ingestion, and run ingestion to cache all new data"
file_scope:
  - src/volforecast/data/edrvol.py           # _FIELD_MAP, _DEFAULT_FIELDS, fetch_edrvol
  - src/volforecast/constants.py             # TICKER_TO_EDRVOL_RIC (need to add VIX)
  - src/volforecast/features/cross_asset_momentum.py  # pattern for parquet loading
  - memory/ref/python-tsdb.md                # TSDB query patterns
  - .github/instructions/python.instructions.md
write_scope:
  - src/volforecast/data/edrvol.py           # add fields to _FIELD_MAP, add VIX options fetch fn
  - src/volforecast/constants.py             # add "VIX": "vix.x" to TICKER_TO_EDRVOL_RIC
acceptance_criteria:
  - "_FIELD_MAP extended with '1m5dp' → 'iv_1m_5dp', '3m25dp' → 'iv_3m_25dp', '3m5dp' → 'iv_3m_5dp'"
  - "_DEFAULT_FIELDS updated to include new fields"
  - "New function fetch_vix_options(start_date, end_date) that fetches edrvol_vix.x@{1matms,1m25dc,1m5dc} and returns DataFrame with columns [vix_iv_1m_atm, vix_iv_1m_25dc, vix_iv_1m_5dc]"
  - "New function fetch_credit_cds(start_date, end_date) that fetches IG_5Y and HY_5Y from TSDB and returns DataFrame with columns [credit_ig_5y, credit_hy_5y]"
  - "save_iv_cache / load_iv_cache work for new '_VIX_OPTIONS' and '_CREDIT_CDS' cache keys"
  - "VIX added to TICKER_TO_EDRVOL_RIC as 'VIX': 'vix.x' (user to correct suffix if wrong)"
  - "Existing tests still pass"
memory_refs: [memory/ref/python-tsdb.md]
constraints:
  - "Use ./vol to run any Python — never bare python/pytest"
  - "Merge new columns into existing parquets (SPX.parquet) — never overwrite"
  - "VIX option TSDB symbol format is edrvol_vix.x@{field} — user confirmed access. If vix.x is wrong RIC suffix, the user will correct after the first run"
  - "Credit CDS TSDB symbols: try midas_.CDXIG5Y@close and midas_.CDXHY5Y@close first. If wrong, leave as configurable constants with a clear TODO for user to fill in exact symbol"
  - "Write output to workspace/tmp/ only"
  - "Do NOT run the actual ingestion yet — just add the code. Ingestion will be triggered by the user with ./vol ingest-iv or similar"
context_summary: "Our pipeline fetches IV data from TSDB edrvol_ namespace. _FIELD_MAP maps TSDB field suffixes to output column names. fetch_edrvol() builds edrvol_{ric}@{field} symbols and queries TSDB. We need 3 new SPX fields (5dp, 3m25dp, 3m5dp), 3 VIX option fields (VIX not currently in RIC map), and 2 credit CDS fields (different TSDB namespace). The user has confirmed all symbols exist and they have access."
depends_on: []
```

### Step 2: Extend `iv_surface.py` — Expose New Columns `[subagent]`

Add loading blocks for VIX options and credit CDS to the enrichment layer.

```yaml
subtask_id: "execute-2"
goal: "Extend IVSurfaceLayer.compute() to load VIX options IV and credit CDS data from new cache files and expose them as columns in enriched_data"
file_scope:
  - src/volforecast/features/iv_surface.py   # current enrichment layer (read full source)
  - src/volforecast/data/edrvol.py           # load_iv_cache, new fetch functions from Step 1
write_scope:
  - src/volforecast/features/iv_surface.py   # add VIX options + credit CDS loading blocks
acceptance_criteria:
  - "IVSurfaceLayer.compute() loads _VIX_OPTIONS.parquet and adds columns: vix_iv_1m_atm, vix_iv_1m_25dc, vix_iv_1m_5dc"
  - "IVSurfaceLayer.compute() loads _CREDIT_CDS.parquet and adds columns: credit_ig_5y, credit_hy_5y"
  - "SPX.parquet new columns (iv_1m_5dp, iv_3m_25dp, iv_3m_5dp) automatically loaded by existing per-symbol IV block — no code change needed for these"
  - "All loading is graceful — if cache file missing, log warning and skip (no crash)"
  - "Existing tests still pass"
constraints:
  - "Follow the exact same load-reindex-assign pattern used for VVIX, VIX, OVX, treasury yields"
  - "These are _enrichment_only columns — they enrich daily_data for downstream layers but do NOT appear in the feature matrix directly"
context_summary: "IVSurfaceLayer is the enrichment layer (_enrichment_only=True) that loads all market-wide data and per-symbol IV into enriched_data. Downstream layers (OptionsLayer, GsvivsSignalsLayer) read from enriched_data. We need to add 5 new enrichment columns: 3 VIX option IVs and 2 credit CDS spreads. The 3 new SPX delta fields (iv_1m_5dp, iv_3m_25dp, iv_3m_5dp) are already handled by the existing per-symbol IV loading block in lines 64-75 (it loads ALL columns from {symbol}.parquet)."
depends_on: ["execute-1"]
```

### Step 3: Write Failing Tests for `GsvivsSignalsLayer` `[subagent]`

TDD: define all 73 features, verify formulas, NaN handling.

```yaml
subtask_id: "execute-3"
goal: "Write comprehensive failing tests for GsvivsSignalsLayer — define expected feature names, verify formulas against the user's reference code, test edge cases"
file_scope:
  - src/tests/unit/features/test_options.py  # pattern for feature layer tests
  - src/volforecast/features/options.py      # pattern for how layers consume enriched_data
  - src/volforecast/registry.py              # registration mechanism
write_scope:
  - src/tests/unit/features/test_gsvivs_signals.py
acceptance_criteria:
  - "Test class with synthetic daily_data fixture containing all required enriched columns: close, vix, vx1, vix_iv_1m_atm, vix_iv_1m_25dc, vix_iv_1m_5dc, iv_1m_atm, iv_1m_25dp, iv_1m_5dp, iv_3m_atm, iv_3m_25dp, iv_3m_5dp, credit_ig_5y, credit_hy_5y"
  - "test_feature_count: layer produces exactly 73 features"
  - "test_feature_names: all 73 feature names match the specification in this plan"
  - "test_spx_returns: SPX_1Dret = close.pct_change(), SPX_3Dret = close.pct_change(3), etc."
  - "test_vix_returns: VIX_1Dret = vix.pct_change() etc."
  - "test_vx1_returns: VX_1M_1Dret = vx1.pct_change() etc."
  - "test_vix_vol_dynamics: pct_change and diff of vix_iv_1m_atm"
  - "test_vix_skew: 50d-25d, 50d-5d, 25d-5d from VIX option IVs"
  - "test_vix_ts: vix/vx1-1 and diffs"
  - "test_spx_1m_skew: using iv_1m_atm (50d), iv_1m_25dp, iv_1m_5dp"
  - "test_spx_skew_ts: 1M/3M ratios and pct_change"
  - "test_credit_returns: pct_change of credit_ig_5y and credit_hy_5y"
  - "test_missing_columns_graceful: when vix_iv columns missing, VIX skew features are NaN (not crash)"
  - "test_registration: 'gsvivs_signals' in FEATURE_REGISTRY after import"
  - "All tests FAIL (layer not yet implemented)"
memory_refs: []
constraints:
  - "Use synthetic data (np.random.RandomState(42) for reproducibility)"
  - "Fixture should have ~100 rows of daily data with realistic-ish values"
  - "Follow existing test patterns from test_options.py"
  - "Run tests with: ./vol test -x -q -k gsvivs"
context_summary: "We are building a new feature layer GsvivsSignalsLayer that produces 73 features from enriched_data columns. The features replicate the GSVIVS01 strategy's feature engineering: returns, realized vol, VIX option skew, VIX term structure, SPX skew dynamics, SPX skew term structure, and credit CDS returns. The user's reference code (in the chat history) defines the exact formulas using pct_change, diff, rolling std, and ratio operations."
depends_on: ["execute-2"]
```

### Step 4: Implement `GsvivsSignalsLayer` `[subagent]`

Build the layer, register it, make all tests pass.

```yaml
subtask_id: "execute-4"
goal: "Implement GsvivsSignalsLayer producing 73 features, register it, pass all tests"
file_scope:
  - src/volforecast/features/options.py              # pattern reference for consuming enriched_data
  - src/volforecast/features/cross_asset_momentum.py # pattern for loading cross_asset parquets
  - src/volforecast/registry.py                      # registration
  - src/tests/unit/features/test_gsvivs_signals.py   # tests to pass
write_scope:
  - src/volforecast/features/gsvivs_signals.py       # NEW layer implementation
  - src/volforecast/registry.py                      # add import line
acceptance_criteria:
  - "Layer class GsvivsSignalsLayer with @register_feature_layer('gsvivs_signals')"
  - "compute(daily_data, *, context=None) → pd.DataFrame with 73 columns"
  - "All 73 feature formulas match the user's reference code exactly"
  - "Graceful degradation: if enriched_data missing vix_iv_* columns, VIX skew features are NaN; if missing credit_* columns, credit features are NaN; if missing iv_1m_5dp/iv_3m_*, deep skew and term structure features are NaN"
  - "All tests in test_gsvivs_signals.py PASS"
  - "'gsvivs_signals' appears in FEATURE_REGISTRY"
  - "import volforecast.features.gsvivs_signals added to registry.py ensure_registered()"
memory_refs: []
constraints:
  - "Layer is NOT _enrichment_only (default False) — features go into X_all"
  - "Layer is NOT _needs_base_features — it reads from enriched_data (daily_data after iv_surface merge)"
  - "No external data loading in the layer — all data comes from enriched_data (loaded by iv_surface)"
  - "Use np.sqrt(252) for annualization, matching the user's reference code"
  - "pct_change and rolling operations must handle NaN gracefully (pandas default)"
  - "Run tests with: ./vol test -x -q -k gsvivs"
context_summary: "GsvivsSignalsLayer consumes enriched_data columns populated by IVSurfaceLayer (close, vix, vx1, vix_iv_1m_atm, vix_iv_1m_25dc, vix_iv_1m_5dc, iv_1m_atm, iv_1m_25dp, iv_1m_5dp, iv_3m_atm, iv_3m_25dp, iv_3m_5dp, credit_ig_5y, credit_hy_5y) and produces 73 feature columns organized into 9 groups: SPX returns (6), VIX returns (6), VX1 returns (6), VIX vol dynamics (6), VIX skew (12), VIX term structure (4), SPX 1M skew (12), SPX skew term structure (15), credit returns (6)."
depends_on: ["execute-3"]
```

### Step 5: Update `tree_expansion` Prefixes `[inline]`

Add new feature prefixes to `_EXPANDABLE_PREFIXES`.

```yaml
subtask_id: "execute-5"
goal: "Add gsvivs_signals feature prefixes to _EXPANDABLE_PREFIXES in tree_expansion.py"
file_scope:
  - src/volforecast/features/tree_expansion.py
write_scope:
  - src/volforecast/features/tree_expansion.py
acceptance_criteria:
  - "New prefixes added: 'spx_ret_', 'spx_rea_', 'vix_ret_', 'vix_rea_', 'vx1_ret_', 'vx1_rea_', 'vix_vol_', 'vix_skew_', 'vix_ts_', 'spx_skew_', 'credit_ig_', 'credit_hy_'"
  - "Existing prefixes unchanged"
  - "Tests still pass"
depends_on: ["execute-4"]
```

### Step 6: Create Trial Config `trial_096_gsvivs_signals.yaml` `[inline]`

Tournament config for fair A/B comparison.

```yaml
subtask_id: "execute-6"
goal: "Create YAML config with enriched XGBoost (old + gsvivs_signals) vs champion XGBoost (old features only) vs HAR baselines"
file_scope:
  - workspace/configs/trial_063_xgboost_champion.yaml  # champion config to clone
write_scope:
  - workspace/configs/trial_096_gsvivs_signals.yaml
acceptance_criteria:
  - "Top-level feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar, gsvivs_signals, tree_expansion]"
  - "Tournament models include:"
  - "  - ewma (naive baseline)"
  - "  - har (statistical baseline)"
  - "  - har_iv (strong linear baseline)"
  - "  - xgboost_champion: XGBoost with OLD feature_layers [iv_surface, har_core, asymmetry, noise_robust, options, calendar, tree_expansion] — SAME config as trial-063"
  - "  - xgboost_enriched: XGBoost with ALL feature_layers including gsvivs_signals"
  - "Same universe as trial-063 (21 symbols)"
  - "Same date_range, CV, hyperparams as trial-063"
  - "Per-horizon init preserved: har_iv_0dte for h=1, har_iv_1w for h=5, har_iv for h=22"
  - "gsvivs_enabled: true, baseline: har_iv"
  - "horizons: [1, 5, 22]"
depends_on: ["execute-5"]
```

**Tournament model config detail:**

```yaml
tournament:
  models:
    - ewma
    - har
    - har_iv
    - xgboost_champion
    - xgboost_enriched
  baseline: har_iv
  model_configs:
    xgboost_champion:
      name: xgboost
      feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar, tree_expansion]
      params:
        # exact same as trial-063
        n_estimators: 5000
        early_stopping_rounds: 150
        learning_rate: 0.01
        max_leaves: 16
        max_depth: 4
        min_child_weight: 150
        colsample_bytree: 0.8
        subsample: 0.8
        reg_lambda: 5.0
        reg_alpha: 0.1
        val_fraction: 0.15
        val_purge_gap: 10
        device: "cuda"
        base_model: har_iv_1w
    xgboost_enriched:
      name: xgboost
      # uses top-level feature_layers (includes gsvivs_signals)
      params:
        # same hyperparams — only features differ
        n_estimators: 5000
        early_stopping_rounds: 150
        learning_rate: 0.01
        max_leaves: 16
        max_depth: 4
        min_child_weight: 150
        colsample_bytree: 0.8
        subsample: 0.8
        reg_lambda: 5.0
        reg_alpha: 0.1
        val_fraction: 0.15
        val_purge_gap: 10
        device: "cuda"
        base_model: har_iv_1w
```

### Step 7: Register Trial in `trials.yaml` `[inline]`

```yaml
subtask_id: "execute-7"
goal: "Append trial-096 to workspace/research/trials.yaml with NOT_STARTED status"
file_scope:
  - workspace/research/trials.yaml
write_scope:
  - workspace/research/trials.yaml
acceptance_criteria:
  - "New entry appended with id: trial-096, date: '2026-07-27', status: NOT_STARTED"
  - "config: trial_096_gsvivs_signals.yaml"
  - "hypothesis: 'GSVIVS01-derived features (VIX/VX1 return dynamics, VIX option skew, SPX skew term structure, credit CDS returns — 73 features) improve QLIKE by 10-30 bps over the XGBoost champion when added to the existing 128-feature set. Prior: signal dilution is the main risk (trial-039 lost 86 bps adding 36 micro features), but these features are from an active trading strategy with demonstrated economic value, and the VIX option skew signals are completely novel to our pipeline.'"
  - "gate: 'DM of xgboost_enriched vs xgboost_champion at h=1/5/22. TreeSHAP feature importance share of gsvivs_signals columns. GSVIVS01 Sharpe comparison. If enriched loses at any horizon, ablate by feature group to find which group hurts.'"
depends_on: ["execute-6"]
```

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Signal dilution (trial-039 pattern) | +73 features overwhelm the IV/RV core, QLIKE degrades | Tournament includes old-features control; post-hoc group ablation via TreeSHAP |
| VIX EDRVOL RIC wrong (`vix.x`) | Ingestion fails for VIX options | User will correct RIC suffix; code is parameterized via TICKER_TO_EDRVOL_RIC |
| Credit TSDB symbol wrong | Credit ingestion fails | Credit features degrade gracefully to NaN; rest of layer still works |
| Feature overlap with existing pipeline | Redundancy wastes model capacity | XGBoost handles redundancy via feature importance; keep separate for clean ablation |
| 3M delta fields have shorter history | NaN for early dates reduces training rows | Pipeline already handles partial IV coverage; tree models handle NaN natively |

---

## Acceptance Criteria (Trial-Level)

1. `./vol test` passes (all existing + new tests)
2. `gsvivs_signals` layer produces exactly 73 features when all enrichment data available
3. Layer degrades gracefully (NaN, not crash) when any enrichment column is missing
4. Trial config runs end-to-end: `./vol run --config workspace/configs/trial_096_gsvivs_signals.yaml --skip-ingest`
5. Tournament table shows both `xgboost_champion` and `xgboost_enriched` with valid QLIKE scores
6. TreeSHAP feature importance available for the enriched model

---

## Execution Command

After all steps complete, run the trial:

```bash
./vol run --config workspace/configs/trial_096_gsvivs_signals.yaml --skip-ingest
```

(Assumes data ingestion was run separately to populate caches.)
