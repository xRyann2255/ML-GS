---
created: 2026-05-07
updated: 2026-05-07
tags: [decision-trees, Rashomon, optimal-trees, GOSDT, STreeD, interpretability]
status: active
priority: P3
source: workspace/research/deep-research-decision-trees.md (archived)
relates: [volatility, har-components, bibliography]
---

# Decision Trees Landscape Survey — Summary

## Three Algorithm Families

1. **Branch-and-bound (Rudin-Seltzer group):** OSDT (2019), GOSDT (2020), OSRT regression (2023), Optimal Sparse Survival Trees (2024)
2. **DP + caching (Nijssen-Demirović):** DL8.5, MurTree, Blossom, STreeD (2023-24), ConTree (2025)
3. **Hybrid lookahead + greedy:** SPLIT/LicketySPLIT/RESPLIT (ICML 2025 Oral) — 100×+ faster than GOSDT

## Key Finding for Our Project

**STreeD piecewise-linear regression trees** (van den Bos, ICML 2024) and **OSRT** (Zhang, AAAI 2023) are the only optimal regression-tree options with code; both scale to our data size (5-20k obs, 20-80 features).

**Expected accuracy cost of interpretability:** ~2-5% MSE penalty vs tuned LightGBM — the tradeoff may be acceptable for desk presentation.

## Rashomon Sets — Novelty Opportunity

- **TreeFARMS (NeurIPS 2022 Oral):** First complete enumeration of near-optimal sparse decision trees
- **Variable Importance Clouds** (Dong-Rudin 2020): min/max importance per feature across R(ε)
- **No published application to financial time-series** as of May 2026 — genuine novelty
- Large Rashomon sets typical for noisy financial data (Semenova-Rudin-Parr 2022)

## Benchmark (van der Linden et al. 2025, 180 Datasets)

- Optimal vs greedy: avg 1.3% improvement (depth 3), 1.0% (depth 4)
- Individual datasets: gaps up to 10 percentage points
- Practical scaling: depth 4 feasible up to ~250 binary features for 100K instances

## Relevance to Project

**Project Proposal 3 (Rashomon Volatility)** was the recommended flagship:
- Enumerate all near-optimal trees for RV forecasting
- Compute Variable Importance Clouds → essential vs redundant features
- Highest-leverage novelty: first finance application of formal Rashomon analysis
- Risk: computational scaling at depth ≥5 with 50+ binarized features
