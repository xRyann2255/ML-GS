# Chapter 6: Microstructure Features

Layer 3 extracts predictive signal from the limit order book and trade flow.
These features capture information arrival that daily aggregates cannot see.

## Features

**Layer 3 microstructure features.**

| Feature | What It Is | Evidence |
|---------|-----------|----------|
| Price acceleration | $\sum_i (\Delta \log P_i - \Delta \log P_{i-1})^2$ | Single most predictive micro feature (Optiver competition) |
| WAP log returns | Returns computed from volume-weighted average price | Less bid-ask bounce than midprice returns |
| Order-book imbalance (OBI) | $\dfrac{\text{bid\_size} - \text{ask\_size}}{\text{bid\_size} + \text{ask\_size}}$ at L1--L5 | (Cartea et al., 2015) |
| Depth ratio | $\sum \text{bid depths}\; / \;\sum \text{ask depths}$ | Structural imbalance across book levels |
| Market urgency | $\text{spread} \times \text{OBI}$ | Wide spread + imbalanced book signals imminent move |
| Spread dynamics | Level, volatility, and momentum of the bid-ask spread | Increasing spread is predictive of near-term vol |
| Signed volume flow | $\text{volume} \times \operatorname{sign}(\text{trade direction})$ | Net buying/selling pressure |
| Sub-window RV ratio | $\operatorname{RV}_{\text{last 5min}}\; / \;\operatorname{RV}_{\text{first 5min}}$ | Within-window acceleration; captures intraday regime shifts |
| VPIN | Volume-synced probability of informed trading | (Easley et al., 2012) |

## The Optiver Evidence

The Kaggle Optiver Realized Volatility competition (2021) produced the largest public benchmark for microstructure-driven vol forecasting.
LightGBM solutions dominated neural networks by roughly 4:1 on the leaderboard.
Price acceleration was the single highest-importance feature across top solutions, and sub-window aggregations (e.g., last-5-minute vs. first-5-minute statistics) consistently outperformed whole-window summaries.
A representative top-100 solution (91st place) used approximately 600 features, with each base quantity expanded via {level, change, z-score} engineering.

## Engineering Principle

For each base quantity in the features table above, compute three variants:

**Feature triple expansion.**

| Variant | Definition | Purpose |
|---------|-----------|---------|
| Level | $x_t$ | Current state |
| Change | $x_t - x_{t-1}$ | Directional momentum |
| Z-score | $(x_t - \bar{x}_{20}) / s_{20}$ | Deviation from recent norm |

This triples the feature count from 9 base quantities to 27.
Tree-based models handle the resulting redundancy naturally via split selection; no manual decorrelation is needed.

## Data Constraints

L2 order-book depth (five levels of bid/ask size) is available only for the E-mini S&P 500 (ES) via SecDB.
Equities receive L1 features only: spread, OBI at best bid/ask, and signed volume flow.
Features requiring multi-level depth (depth ratio, market urgency with L2--L5 OBI) are ES-only.

The raw intraday sequences that produce these features also feed the LSTM module (Chapter 10), which consumes them as time-ordered input rather than daily aggregates.

> **Warning: Lookahead Bias in Microstructure Features**
>
> Features for $\operatorname{RV}_{t+1}$ must use only information available at the close of period $t$.
> Timestamp alignment is critical: if $\operatorname{RV}_{t+1}$ covers trading day $t+1$, then features must be computed from data up to and including the close of day $t$.
> A single misaligned sub-window statistic will inflate backtest performance and produce unreproducible results in production.

> **Key Idea: Microstructure Features Add Most Value for Trees**
>
> Microstructure features are high-cardinality, noisy, and partially redundant.
> LightGBM exploits them effectively via greedy splits; linear models and shallow networks gain less.
> The Optiver evidence confirms this: tree ensembles dominated when the feature set was microstructure-heavy.
