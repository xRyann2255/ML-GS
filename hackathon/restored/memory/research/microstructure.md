---
created: 2026-05-07
updated: 2026-05-07
tags: [microstructure, LOB, E-mini, L2, OBI, price-acceleration, Optiver, VPIN]
status: active
priority: P2
source: workspace/research/microstructure.md (archived)
relates: [optimal-feature-set, data-access, project-design]
---

# Microstructure Features — Summary

## Optiver Kaggle Evidence (Competition Meta-Analysis)

**Top features across solutions:**
- **Price acceleration** (log-return-of-log-return, i.e., second differences of log prices): single most predictive feature for short-horizon RV
- Market urgency = spread × liquidity_imbalance: strong composite
- Volume-weighted sub-window aggregations (first half vs second half): temporal structure matters
- Exponential decay weighting > simple means for aggregations
- Cross-stock aggregations (mean/std across all stocks at same time): market-wide state

**Competition outcome:** LightGBM dominated (~4:1 over NNs). Feature engineering > model choice.

## E-mini L2 Specific Features

| Feature | Construction |
|---------|-------------|
| Order Book Imbalance | (bid_size − ask_size)/(bid_size + ask_size) at L1-L5 |
| Depth Ratio | Σ(bid depths) / Σ(ask depths) at multiple levels |
| VPIN | Volume-synchronized probability of informed trading |
| Signed volume flow | Σ volume_i × sign(trade direction) |

With 4M ticks/day: enough data for LSTM/TCN to learn intraday patterns hard to hand-engineer.

## Academic Evidence

- Rahimikia-Poon (2020): ML + LOB features outperform HAR in **90% of OOS days** on 23 NASDAQ tickers
- Exception: performance degrades on extreme volatility days
- Cont-Kukanov-Stoikov (2014): OFI captures info content of order arrivals

## Constraints

- **L2 depth is E-mini ONLY** — equities get L1 features only (spread, price acceleration, WAP)
- For equities: spread dynamics, signed volume, trade-arrival intensity still available from L1
- Price acceleration is worth testing on daily frequency too (not just intraday)
