# Practical Applications and Project Directions

> **Application: Why This Chapter**
> The preceding chapters built a toolkit: estimators, forecasters, features, and evaluation methods.
> This chapter answers the question every trading desk asks: "so what?"
> It translates statistical forecast accuracy into economic value: the language that gets a model deployed.

A model that beats HAR by 8% on QLIKE is scientifically interesting.
But a desk head wants to know: how much Sharpe does that buy me?
How much P&L does it add to my book?
This chapter provides the frameworks for answering those questions.

## Volatility Targeting: The Simplest Economic Value Test

> **Prereq: Background**
> This section requires familiarity with portfolio returns and the Sharpe ratio (any introductory finance text),
> as well as realized volatility forecasts from Chapters [6](ch06-har-model.md)--[13](ch13-hybrid-ensemble.md).

**Volatility targeting** is the simplest and most widely used application of a vol forecast in systematic investing.
The idea: size your position inversely proportional to forecast vol, so that portfolio risk stays roughly constant over time.

### The EWMA Baseline

The workhorse volatility estimate used by the vast majority of systematic funds for position sizing is not GARCH, not HAR, but plain **exponentially weighted moving average (EWMA)** smoothing:

$$\hat\sigma^2_t = (1-\delta)\,r_{t-1}^2 + \delta\,\hat\sigma^2_{t-1},$$

where $\delta$ is chosen so the half-life matches approximately 20 to 60 trading days.
This is what most funds actually use for position sizing: not GARCH, not HAR, just exponential smoothing.
Its popularity stems from simplicity, low latency, and the fact that it requires exactly one parameter.

> **Intuition: In Plain English**
> Tomorrow's variance estimate is a weighted blend of today's squared return (the "news") and today's variance estimate (the "memory").
> A high $\delta$ means slow adaptation: the estimate barely moves day-to-day.
> A low $\delta$ means the estimate jumps quickly with every new return, reacting fast but also picking up noise.

> **Project Connection: Why This Matters**
> EWMA is the baseline your vol-targeting backtest must beat.
> If your HAR or ML forecast cannot outperform this one-parameter smoother in a position-sizing test, the model adds no economic value regardless of its QLIKE score.

### The Volatility-Targeting Formula

Given a forecast $\hat\sigma_t$ (annualized), the **volatility-targeted weight** is:

$$w_t = \frac{\sigma_{\text{target}}}{\hat\sigma_t}.$$

The portfolio return is then $r_t^{\text{VT}} = w_t \cdot r_t$.
When forecast vol is high, $w_t < 1$ (reduce position).
When forecast vol is low, $w_t > 1$ (lever up).
The result is a return stream with approximately constant realized volatility equal to $\sigma_{\text{target}}$.

> **Intuition: Why Vol-Targeting Adds Sharpe**
> Moreira and Muir (2017) showed that vol-targeting adds approximately 0.3 Sharpe ratio across equity indices, currencies, and commodities.
> The mechanism: by reducing exposure before drawdowns, vol-targeting truncates the left tail.
> A better vol forecast means you cut exposure earlier and more precisely.

> **Project Connection: Why This Matters**
> This formula is the direct economic-value test for your internship project (Project Direction 1: HARQ-X + ML residual).
> Every QLIKE improvement in your forecast translates into a tighter $\hat\sigma_t$, which means more precise position sizing and higher Sharpe.
> The vol-targeting backtest is your primary deliverable for demonstrating that statistical accuracy creates real P&L.

### Connection to Time-Series Momentum

Moskowitz, Ooi, and Pedersen (2012) use a related framework for time-series momentum across 58 futures: signal $=$ sign of 12-month return, position size $= 40\%/\hat\sigma_t$.
The vol forecast enters the denominator.
Every percentage improvement in your forecast precision tightens the position-sizing, reducing both crash risk and unnecessary leverage.
This is the mechanism by which better QLIKE translates to better risk-adjusted returns in a TSMOM book.

> **Warning: Forecast Failure in Crises**
> Vol targeting assumes volatility is predictable but returns are not.
> If your forecast systematically underpredicts during crises (all ML models trained on normal data underpredict COVID-style jumps), vol targeting will keep positions too large going into the drawdown.
> Mitigation: ensemble your ML forecast with a simple $\max(\text{ML},\; 1.5 \times \text{EWMA})$ floor during high-uncertainty regimes, or cap $w_t$ at a maximum leverage ratio (e.g., $w_t \leq 2.0$).

> **Application: The Key Deliverable Table**
> For your internship deliverable, the key table is:
>
> 1. Run vol-targeted long-SPX using each model.
> 2. Report annualized return, vol, Sharpe, max drawdown, and Calmar ratio.
> 3. Compute Sharpe improvement per 1% QLIKE improvement.
>
> This single table communicates economic value in the language every systematic desk speaks.
