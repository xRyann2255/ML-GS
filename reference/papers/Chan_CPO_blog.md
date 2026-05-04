# Conditional Parameter Optimization — Ernest Chan

**Source:** https://predictnow-ai.medium.com/conditional-parameter-optimization-adapting-parameters-to-changing-market-regimes-b7158ab78ed4
**Used in:** Ch 22 (Which strategy when — parameter adaptation)

## Problem

Markets exhibit multiple regimes (bull/bear, calm/choppy, low/high vol, etc.), and a single fixed parameter set cannot remain optimal across all of them. Traditional parameter optimisation fails to adapt because:
- **Fixed train sets** cannot respond to regime changes.
- **Expanding train sets** dilute new information with old.
- **Rolling train sets** lose statistical significance and rarely deliver convincing evidence of improvement.

## The CPO solution

**Conditional Parameter Optimization** uses supervised ML — specifically random forest with boosting — to learn the conditional mapping

`(market features, parameters) → expected strategy performance`

Then, at each decision point:
1. Observe current market features.
2. For each candidate parameter combination, use the trained model to predict expected performance under those current features.
3. Select the parameter set with the highest predicted performance.
4. Re-do this as frequently as needed — daily, per-trade, whatever the strategy's natural cadence is.

This reframes parameter optimisation as a *conditional regression* problem rather than a static optimisation problem. The key insight: you don't need to identify regimes explicitly; the feature inputs represent them implicitly, and the model learns the mapping.

## Demonstrated application

Chan applies CPO to a Bollinger-band mean-reversion strategy on GLD (gold ETF), showing improved results versus fixed-parameter optimisation.

## Beyond finance

Chan notes the same technique generalises: optimising hospital emergency-room wait times given features like staffing, equipment, time-of-day, weather, etc.

## Notes for the PDF

- Ch 22 should present CPO as the **parameter-level** counterpart to López de Prado's **trade-level** meta-labeling. Both answer the "is now the right time?" question at different resolutions.
- The decision framework in Ch 22 combines: HMM regime detection (coarse) → diagnostic decision tree (strategy selection) → meta-labeling (trade-level filter) → CPO (parameter tuning). This is the synthesis Ch 22 builds; no single paper provides it.
