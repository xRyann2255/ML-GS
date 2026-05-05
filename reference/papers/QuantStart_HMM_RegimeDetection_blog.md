# Market Regime Detection using Hidden Markov Models in QSTrader

**Source:** https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/
**Used in:** Ch 22 (Which strategy when — regime detection)

## Overview

Demonstrates Hidden Markov Models (HMMs) as a risk management / trade filtering tool inside a trend-following strategy. HMMs identify latent market states ("low vol" / "high vol") from observable returns, then a trend strategy trades only when the model predicts the favourable state.

## Core concept

HMMs are stochastic state-space models that assume the existence of *hidden* latent states driving the observable time series. In the trading application:
- Observations: daily returns
- Hidden states: regime 0 (low vol, favourable) vs regime 1 (high vol, unfavourable)
- The model learns transition probabilities and Gaussian emission distributions per state via EM.

## Strategy components

### 1. HMM training (`regime_hmm_train.py`)

Trains on SPY daily data from 1993-01-29 to 2004-12-31 using `hmmlearn.GaussianHMM`.

Parameters:
- `n_components=2` (two regimes)
- `covariance_type="full"`
- `n_iter=1000`

Serialised via `pickle` for reuse.

### 2. Moving-average crossover strategy (`regime_hmm_strategy.py`)

Classic trend-follower:
- Long entry: 10-day SMA > 30-day SMA
- Exit: 30-day SMA > 10-day SMA
- Position size: 10,000 shares

### 3. Regime-detection risk manager (`regime_hmm_risk_manager.py`)

Filters orders based on predicted regime:

**Regime 0 (low vol — desirable):**
- Allows new long entries
- Permits position closures

**Regime 1 (high vol — undesirable):**
- Blocks new entries
- Allows existing positions to close

Implementation: call `GaussianHMM.predict()` on the latest returns window → take last element → gate the OrderEvent accordingly.

## Backtest results (SPY, 2005–2014 out-of-sample)

| Metric | Without filter | With HMM filter |
|---|---|---|
| Sharpe | 0.37 | 0.48 |
| CAGR | 6.41% | 6.88% |
| Max daily drawdown | ~56% | ~24% |
| Trades | 41 | 31 |

The filter roughly halved the max drawdown while slightly improving Sharpe and CAGR — classic "fewer trades, better risk-adjusted" outcome.

## Notable behaviours

- The filtered strategy sat out early 2008 through mid-2009 (the financial crisis period) — a big reason for the drawdown improvement. It also stayed in drawdown from the previous high watermark through that period, because while it avoided losses, it also didn't participate in the recovery until the regime flipped.
- Training/backtest split: 1993–2004 train, 2005–2014 test. No retraining during the test period — a genuine out-of-sample evaluation.
- Production note: the HMM should be periodically retrained as return distributions shift.

## Notes for the PDF

- This is the cleanest, simplest HMM-as-filter example in the literature. Use it as the template worked example in Ch 22 (regime detection section).
- The two-regime (low vol / high vol) formulation is all we need for the "which strategy when" framework — it maps directly to the Meudt et al. (2020) finding that value works in high-vol regimes and momentum works in low-vol regimes.
