---
name: BACKTEST
description: "Economic value testing of volatility signals. USE FOR: IV-RV gap trading signal, delta-hedged straddle P&L, vol-targeting Sharpe, drawdown analysis, transaction cost modeling. DO NOT USE FOR: statistical evaluation (use EVALUATE), model training (use MODEL_TRAIN), data fetching (use DATA_INGEST)."
---

# BACKTEST — Economic Value Testing

> **Purpose:** Test the economic value of volatility forecasting signals through P&L backtests. Implements IV-RV gap trading signals and vol-targeting portfolio strategies with realistic transaction costs.

**Out of scope:** Statistical evaluation (use EVALUATE), model training (use MODEL_TRAIN), feature computation (use FEATURE_BUILD).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `BACKTEST` |
| **Scope** | Economic value testing and P&L backtesting |
| **Inputs** | JSON args: signal type, backtest window, transaction cost model |
| **Outputs** | P&L series, Sharpe ratio, drawdown statistics in `workspace/tmp/` |
| **Authority** | Read-only — reads model signals, writes backtest results |

## When to Use

- Testing whether a vol forecast translates into tradeable economic value
- Running IV-RV gap signal backtest (long/short vol based on IV vs predicted RV)
- Running vol-targeting portfolio strategy (scale exposure by inverse predicted vol)
- Analyzing P&L characteristics: Sharpe, max drawdown, turnover, hit rate
- Comparing strategies against buy-and-hold benchmark

## When NOT to Use

- Statistical model evaluation (QLIKE, DM tests) — use EVALUATE
- Training models — use MODEL_TRAIN
- Exploring features or data — use RESEARCH

## Memory References

| File | Content |
|------|--------|
| `workspace/docs/vol-project-ref/INDEX.md` | Authoritative project spec — ch18 milestone M7 defines signal acceptance criteria; ch13 has economic value methodology |
| `workspace/docs/vol-learning-guide/INDEX.md` | Comprehensive theory & equations — Ch9 (VRP derivation, variance swaps), Ch17 (vol-targeting, risk parity, momentum scaling applications) |
| `memory/research/evaluation-framework.md` | Economic value test methodology |
| `memory/research/implied-vol.md` | VRP construction, IV-RV relationship |
| `memory/research/complete-pipeline.md` | Where backtest fits in the pipeline |
| `workspace/docs/data-audit.md` | IV surface and cross-asset query recipes needed for economic value tests |

## Args File Format

The wrapper is a passthrough to `volforecast.evaluation.economic_value.main`,
which reads a predictions CSV and returns an economic-value summary as JSON
into `out_file`.

Write JSON to `workspace/tmp/backtest_args.json` (the exact `--args-file` value
in the `backtest` task definition):

```json
{
  "csv": "workspace/tmp/models/lgbm_preds.csv",
  "columns": {
    "vol_forecast": "vol_forecast",
    "daily_returns": "daily_returns",
    "realized_vol": "realized_vol",
    "implied_vol": "implied_vol",
    "spot": "spot",
    "signal": "signal"
  },
  "model_name": "LightGBM_L012",
  "out_file": "workspace/tmp/backtest_out.txt"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `csv` | Yes | Path to a predictions/actuals CSV, one row per date. |
| `columns` | Yes | Mapping from the schema keys below to actual CSV column names. |
| `columns.vol_forecast` | Yes | Column name for the model's vol forecast (annualized decimal). |
| `columns.daily_returns` | Yes | Column name for realized daily returns of the underlying. |
| `columns.realized_vol` | Optional | Column name for realized vol (annualized decimal). |
| `columns.implied_vol` | Optional | Column name for implied vol (annualized decimal). |
| `columns.spot` | Optional | Column name for underlying spot / close price. |
| `columns.signal` | Optional | Column name for a pre-computed trading signal. |
| `model_name` | No | Label for the row in the summary (default: `""`). |
| `out_file` | Yes | Path where the JSON summary + `EXIT_CODE=<rc>` sentinel are written. |

> **Concurrency caveat (last-writer-wins):** The args file path is fixed per task —
> two concurrent agents writing it race (last writer wins). Keep `out_file` unique
> per run (put a `run_id` slug in its name, e.g. `workspace/tmp/backtest_out_<run_id>.txt`
> where `run_id` matches `[a-z0-9-]+`); the args file itself is not collision-safe.

**Reading results:** `read_file(out_file)`; the run succeeded iff its final line is `EXIT_CODE=0`.

## Signal Types

### `iv_rv_gap` — IV minus Predicted RV

**Logic:**
- If $IV_t > \hat{RV}_{t+1}$: implied vol is "rich" → sell vol (short straddle/strangle)
- If $IV_t < \hat{RV}_{t+1}$: implied vol is "cheap" → buy vol (long straddle/strangle)
- Position size proportional to $|IV_t - \hat{RV}_{t+1}|$

**P&L computation:** Delta-hedged straddle returns

### `vol_targeting` — Volatility-Scaled Portfolio

**Logic:**
- Target a constant annualized volatility (e.g., 10%)
- Scale equity exposure by $\sigma_{target} / \hat{\sigma}_{t+1}$
- Lower exposure when predicted vol is high; higher when low

**P&L computation:** Scaled SPY/ES returns

## Task-Based Execution

1. **Write args file** to `workspace/tmp/backtest_args.json`
2. **Run task:** `run_task("backtest")`
3. **Read output:** `read_file("workspace/tmp/backtest_out.txt")` — JSON summary; success iff last line is `EXIT_CODE=0`.

## Links

- memory/research/complete-pipeline.md — end-to-end system and implementation order
