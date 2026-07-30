---
name: FEATURE_BUILD
description: "Compute feature layers (0-6) from raw market data. USE FOR: HAR components, semivariances, jumps, IV/VRP, microstructure, cross-asset spillovers, calendar features, feature validation. DO NOT USE FOR: raw data fetching (use DATA_INGEST), model training (use MODEL_TRAIN)."
---

# FEATURE_BUILD — Feature Layer Computation

> **Purpose:** Compute feature layers 0–6 from raw market data. Each layer corresponds to a distinct category of volatility predictors, from HAR core components to interaction/derived features.

**Out of scope:** Raw data fetching (use DATA_INGEST), model training (use MODEL_TRAIN), evaluation (use EVALUATE).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `FEATURE_BUILD` |
| **Scope** | Feature engineering for RV forecasting |
| **Inputs** | JSON args: feature layer, symbol, date range |
| **Outputs** | Feature DataFrame as Parquet in `workspace/tmp/` |
| **Authority** | Read-only — reads raw data, writes computed features |

## When to Use

- Computing any feature layer (0–6) for model training or exploration
- Validating feature distributions against paper-reported values
- Building the full feature matrix for a set of symbols
- Debugging feature computation (NANs, look-ahead bias, formula errors)

## When NOT to Use

- Fetching raw data — use DATA_INGEST first
- Training models — pass computed features to MODEL_TRAIN
- Ad-hoc exploration — use RESEARCH or NOTEBOOK

## Memory References

Load these before executing:

| File | Content |
|------|--------|
| `workspace/docs/vol-project-ref/INDEX.md` | Authoritative project spec — drill into ch03-ch08 for definitive feature formulas, layer definitions, and expansion rules |
| `workspace/docs/vol-learning-guide/INDEX.md` | Comprehensive theory & equations — Ch2 (RV), Ch3 (microstructure noise/RK/TSRV), Ch4 (jumps/BPV/BNS/Lee-Mykland), Ch6 (HAR/SHAR/HARQ), Ch9 (VRP), Ch10 (feature engineering layers) |
| `memory/research/optimal-feature-set.md` | 7-layer architecture, formulas, feature lists |
| `memory/research/har-components.md` | HAR decomposition, log RV, RQ |
| `memory/research/leverage-effect.md` | Semivariances, SHAR baseline |
| `memory/research/jump-detection.md` | BPV, BNS test, jump components |
| `memory/research/implied-vol.md` | VRP construction, Marquee features |
| `memory/research/microstructure.md` | E-mini L2 features, VPIN |
| `memory/research/cross-asset.md` | DY spillover, available instruments |
| `memory/research/calendar-events.md` | FOMC, earnings, OpEx |
| `memory/research/feature-composition.md` | Interaction layers, engineering principles |
| `workspace/docs/data-audit.md` | Raw data query recipes for every feature layer — use to look up how to fetch inputs |

## Args File Format

The wrapper is a thin adapter over `skills/_shared/vf_entry.py`, which invokes
`python -m volforecast <argv>`. Feature layers are built as part of a pipeline run:
declare the layers you want in the pipeline YAML's `feature_layers` block and run
the pipeline in feature-only mode (skip training/eval stages, or run only through
the feature stage — see the example configs in `workspace/configs/`).

Write JSON to `workspace/tmp/feature_args.json` (the exact `--args-file` value in
the `feature-build` task definition):

```json
{
  "argv": ["run", "--config", "workspace/configs/<feature_only_trial>.yaml", "--stages", "features"],
  "out_file": "workspace/tmp/feature_build_out.txt"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `argv` | Yes | Argument vector passed verbatim to `volforecast.__main__.main`. Layer selection lives in the YAML's `feature_layers` list. |
| `out_file` | Yes | Path where captured stdout+stderr will be written. Final line will be `EXIT_CODE=<rc>`; success iff `EXIT_CODE=0`. |

> **Concurrency caveat (last-writer-wins):** The args file path is fixed per task —
> two concurrent agents writing it race (last writer wins). Keep `out_file` unique
> per run (put a `run_id` slug in its name, e.g. `workspace/tmp/feature_build_out_<run_id>.txt`
> where `run_id` matches `[a-z0-9-]+`); the args file itself is not collision-safe.

**Reading results:** `read_file(out_file)`; the run succeeded iff its final line is `EXIT_CODE=0`.

## Feature Layers

### Layer 0 — HAR Core + Measurement Quality

| Feature | Formula | Source |
|---------|---------|--------|
| `log_rv_d` | $\log(RV_t^{(d)})$ — daily log realized variance | 5-min returns |
| `log_rv_w` | $\log(RV_t^{(w)})$ — weekly average (5 days) | 5-min returns |
| `log_rv_m` | $\log(RV_t^{(m)})$ — monthly average (22 days) | 5-min returns |
| `rq` | $RQ_t = \frac{N}{3} \sum r_{t,i}^4$ — realized quarticity | 5-min returns |
| `rq_interaction` | $RQ_t \times \log(RV_t^{(d)})$ | Derived |

### Layer 1 — Asymmetric Volatility

| Feature | Formula |
|---------|---------|
| `rs_minus` | $RS_t^- = \sum r_{t,i}^2 \cdot \mathbb{1}(r_{t,i} < 0)$ — negative semivariance |
| `rs_plus` | $RS_t^+ = \sum r_{t,i}^2 \cdot \mathbb{1}(r_{t,i} > 0)$ — positive semivariance |
| `bpv` | $BPV_t = \mu_1^{-2} \sum |r_{t,i}| \cdot |r_{t,i-1}|$ — bipower variation |
| `jump` | $J_t = \max(RV_t - BPV_t, 0)$ — jump component |
| `continuous` | $C_t = RV_t - J_t$ — continuous variation |

### Layer 2 — Options-Implied (SPX only)

| Feature | Source |
|---------|--------|
| `atm_iv` | Marquee ERDVOL ATM implied vol |
| `vrp` | $VRP_t = IV_t^2 - RV_t$ — variance risk premium |
| `skew_25d` | 25-delta put-call skew |
| `term_slope` | $(IV_{3m} - IV_{1m}) / IV_{1m}$ |
| `butterfly` | 25-delta butterfly spread |
| `vvix` | CBOE VVIX (vol of vol) |

### Layer 3 — Microstructure (E-mini L2 only)

| Feature | Description |
|---------|-------------|
| `price_accel` | Second derivative of mid-price |
| `obi` | Order book imbalance (bid-ask volume ratio) |
| `depth_ratio` | Top-3 vs top-10 depth ratio |
| `spread` | Quoted bid-ask spread |
| `vpin` | Volume-synchronized probability of informed trading |

### Layer 4 — Cross-Asset Spillovers

| Feature | Description |
|---------|-------------|
| `treasury_slope` | 10y − 2y yield spread |
| `fx_vol` | USD/JPY and EUR/USD realized vol |
| `commodity_vol` | CL (crude) and GC (gold) realized vol |
| `dy_index` | Diebold-Yilmaz connectedness index |

### Layer 5 — Calendar/Event

| Feature | Description |
|---------|-------------|
| `fomc_proximity` | Days to next FOMC meeting |
| `nfp_proximity` | Days to next NFP release |
| `opex_proximity` | Days to next options expiration |
| `earnings_proximity` | Days to next earnings announcement |

### Layer 6 — Interaction/Derived

| Feature | Description |
|---------|-------------|
| Cross-layer interactions | VRP × jump, OBI × RS⁻, etc. |
| Regime indicators | High/low vol regime classification |

## Validation Checks

After computing features:

1. **No NaNs:** Flag and report any NaN rows (expected at series boundaries only)
2. **No look-ahead bias:** Feature at time $t$ uses only data from $t$ and before
3. **Distribution sanity:** Log RV should be approximately Gaussian with mean ≈ −9 to −7
4. **Temporal alignment:** All features align on the same date index
5. **Scale check:** Semivariances sum to total RV within floating-point tolerance

## Task-Based Execution

1. **Write args file** to `workspace/tmp/feature_args.json`
2. **Run task:** `run_task("feature-build")`
3. **Read output:** `read_file("workspace/tmp/feature_build_out.txt")` — success iff last line is `EXIT_CODE=0`.

## Links

- memory/research/optimal-feature-set.md — 7-layer feature architecture
- memory/research/feature-composition.md — layer composition and diminishing returns
