# Microstructure Features

What we've learned about noise, spreads, and LOB features.

## Findings

**From Optiver Kaggle analysis (2026-05-06):**
- Price acceleration (log-return-of-log-return, i.e., second differences of log prices) was one of the single most predictive features for short-horizon RV prediction across top solutions. Sum of squared accelerations over a window captures instability in price momentum.
- Market urgency = price_spread x liquidity_imbalance was a strong composite microstructure feature.
- Volume-weighted sub-window aggregations (first half vs second half, or minute-by-minute RV) outperformed whole-window aggregations. The temporal structure within the observation window matters.
- Exponential decay weighting (recent observations weighted more) consistently improved aggregations over simple means.
- Cross-stock aggregations (mean/std of features across all stocks at the same time) captured market-wide microstructure state.

**For our E-mini L2 data specifically:**
- Order flow imbalance (Cont, Kukanov, Stoikov 2014) is the canonical signal: (bid_size - ask_size)/(bid_size + ask_size). We can compute this at both levels since we have L2 depth.
- Depth ratio (bid depth / ask depth) at various levels captures supply/demand asymmetry.
- With 4M ticks/day, we have enough data for an LSTM/TCN to learn intraday patterns that are hard to hand-engineer. This is a key differentiator vs Optiver (which had only 600-second windows per sample).

## Questions to Answer

- How much does microstructure noise bias our RV estimates at different sampling frequencies?
- What does the bid-ask spread look like across our universe? How variable?
- ~~If we have L2 data (E-mini), what order book features carry signal?~~ Partially answered above from Optiver; need to verify on our specific data.
- Does the noise level itself predict future volatility?
- Does price acceleration (log-return-of-log-return) carry signal for daily RV prediction, not just intraday?

## Deep Research Findings (2026-05-06)

**LOB features -- strongest empirical evidence:**
- Rahimikia & Poon (2020): ML models with LOB features outperform HAR in 90% of OOS days for 23 NASDAQ tickers (2007-2016). Dominant features: mid prices, mean bids, and mean asks (`rahimikia-poon-2020` in bibliography)
- Exception: performance degrades during extreme volatility days
- Cont, Kukanov & Stoikov (2014): order flow imbalance as a predictor -- captures the information content of order arrivals

**Key microstructure features identified empirically:**
- Bid-ask spread, top-of-book depth imbalance, trade-arrival intensity
- Weighted-average price (WAP) volatility -- used heavily in Optiver Kaggle top solutions
- Amihud (2002) illiquidity, Kyle's lambda, microprice, queue imbalance

**Sentiment / NLP (brief note -- out of main project scope):**
- Rahimikia, Zohren & Poon (2024): FinText word embeddings on Dow Jones Newswires helpful especially on jump days (`rahimikia-zohren-poon-2024` in bibliography)
