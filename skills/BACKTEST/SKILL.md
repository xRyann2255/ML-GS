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

Write JSON to `workspace/tmp/backtest_args.json`:

```json
{
  "signal_type": "iv_rv_gap",
  "signal_file": "workspace/tmp/models/lgbm_preds.parquet",
  "iv_file": "workspace/tmp/features/iv_surface.parquet",
  "actuals_file": "workspace/tmp/features/test_actuals.parquet",
  "backtest_window": {
    "start_date": "2022-01-01",
    "end_date": "2024-12-31"
  },
  "transaction_costs": {
    "spread_bps": 5,
    "commission_per_contract": 1.25,
    "slippage_bps": 2
  },
  "benchmark": "buy_and_hold",
  "out_dir": "workspace/tmp/backtest",
  "out_file": "workspace/tmp/backtest_out.txt"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `signal_type` | Yes | One of: `iv_rv_gap`, `vol_targeting` |
| `signal_file` | Yes | Path to model predictions (Parquet) |
| `iv_file` | Conditional | IV surface data (required for `iv_rv_gap`) |
| `actuals_file` | Yes | Path to realized vol actuals |
| `backtest_window` | Yes | Start and end dates for backtest period |
| `transaction_costs` | No | Cost model parameters (defaults provided) |
| `benchmark` | No | Benchmark strategy (default: `buy_and_hold`) |
| `out_dir` | No | Output directory (default: `workspace/tmp/backtest`) |
| `out_file` | No | Path for backtest log |

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

## Transaction Cost Model

| Parameter | Default | Description |
|-----------|---------|-------------|
| `spread_bps` | 5 | Bid-ask spread in basis points |
| `commission_per_contract` | 1.25 | Per-contract commission (futures) |
| `slippage_bps` | 2 | Execution slippage |

## Output Artifacts

| File | Content |
|------|---------|
| `pnl_series.parquet` | Daily P&L time series |
| `backtest_metrics.json` | Sharpe, max drawdown, Calmar, turnover, hit rate |
| `backtest_out.txt` | Human-readable backtest summary |

### Key Metrics Reported

| Metric | Description |
|--------|-------------|
| **Annualized Sharpe** | Risk-adjusted return (target: > 0.5) |
| **Max Drawdown** | Worst peak-to-trough loss |
| **Calmar Ratio** | Return / max drawdown |
| **Daily Hit Rate** | Fraction of profitable days |
| **Annual Turnover** | Portfolio turnover (for transaction cost analysis) |
| **P&L vs Benchmark** | Cumulative excess return over buy-and-hold |

## Task-Based Execution

1. **Write args file** to `workspace/tmp/backtest_args.json`
2. **Run task:** `run_task("backtest", workspaceFolder: "h:\ml-vol-estimator")`
3. **Read output:** Check `workspace/tmp/backtest_out.txt` for results

## Links

- memory/research/complete-pipeline.md — end-to-end system and implementation order
