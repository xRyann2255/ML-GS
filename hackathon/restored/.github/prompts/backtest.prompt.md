---
description: "Backtest — economic value testing of IV-RV gap signal or vol-targeting strategy"
argument-hint: "signal type (iv-rv-gap or vol-targeting) and backtest window"
model: Claude Opus 4.6
---

You are in **backtest mode**. Translate statistical forecast improvements into economic value via P&L simulation.

- `personas/eval-sentinel.md`
- `memory/research/evaluation-framework.md`
- `memory/research/complete-pipeline.md`

**Signal types:**
- **IV-RV gap:** Sell vol when IV > predicted RV (overpriced protection), buy when IV < predicted RV.
- **Vol-targeting:** Scale equity exposure inversely with predicted vol to maintain constant portfolio volatility.

**Workflow:**

1. Confirm signal type, backtest window, and which model's forecasts to use.
2. Load model predictions and market data (IV surface, spot prices, daily returns).
3. Generate trading signals from IV-RV gap or vol-targeting weights.
4. Simulate P&L with transaction costs (default: 5 bps round-trip).
5. Compute performance metrics:
   - Annualized Sharpe ratio
   - Maximum drawdown
   - Hit rate (% profitable trades)
   - Average P&L per trade
6. Compare to benchmark (buy-and-hold for vol-targeting, zero-signal for IV-RV gap).
7. Report: is the statistical QLIKE improvement economically meaningful?

**Expected outputs:** P&L time series, Sharpe ratio, max drawdown, comparison vs benchmark.
