# GSVIVS01: Daily Variance Swap Replication Strategy

## Overview

GSVIVS01 is a systematic short-volatility strategy that replicates selling a daily variance swap on the S&P 500 using 0DTE (zero days to expiry) SPX options. The strategy collects the Variance Risk Premium (VRP) by selling a weighted strip of out-of-the-money options whose combined payoff replicates a short variance swap position, delta-hedged with E-mini S&P 500 futures.

**Strategy tickers:** `.GSVIVSR1_DH`, `.GSVIVSR2_DH` (low-lag variant)

---

## 1. Variance Swap Mechanics

### 1.1 Continuous Variance Swap

A variance swap pays the difference between realized variance and a pre-agreed strike:

$$\text{Payoff} = N_{var} \left( \sigma^2_{\text{realized}} - K_{var}^2 \right)$$

where:
- $N_{var}$ = variance notional
- $\sigma^2_{\text{realized}}$ = annualized realized variance over the contract period
- $K_{var}$ = variance swap strike (the "fair" implied variance)

The party *short* the variance swap (GSVIVS01's position) profits when realized variance comes in below the strike.

### 1.2 Model-Free Implied Variance (Variance Swap Strike)

The fair strike of a variance swap is derived from the full option chain via the Breeden-Litzenberger result:

$$K_{var}^2 = \frac{2}{T} \int_0^{\infty} \frac{C(K) - \max(F - K, 0)}{K^2} \, dK$$

Equivalently, splitting at the forward price $F$:

$$K_{var}^2 = \frac{2 e^{rT}}{T} \left[ \int_0^{F} \frac{P(K)}{K^2} \, dK + \int_F^{\infty} \frac{C(K)}{K^2} \, dK \right]$$

where:
- $T$ = time to expiry (in years)
- $F$ = forward price of the underlying
- $P(K)$ = price of OTM put with strike $K$
- $C(K)$ = price of OTM call with strike $K$
- $r$ = risk-free rate

The $1/K^2$ weighting gives disproportionate weight to OTM puts, capturing the volatility skew. This is why the variance swap strike always exceeds ATM implied volatility.

### 1.3 CBOE VIX Discrete Formula (Numerical Implementation)

In practice, with a discrete set of traded strikes:

$$\sigma^2 = \frac{2}{T} \sum_i \frac{\Delta K_i}{K_i^2} \cdot e^{rT} \cdot Q(K_i) - \frac{1}{T} \left( \frac{F}{K_0} - 1 \right)^2$$

where:
- $\Delta K_i = \frac{K_{i+1} - K_{i-1}}{2}$ (half the distance between adjacent strikes; endpoints use single-sided difference)
- $Q(K_i)$ = midpoint price of the OTM option at strike $K_i$:
  - Put if $K_i < F$
  - Call if $K_i > F$
  - Average of put and call if $K_i = F$
- $K_0$ = first strike below (or equal to) the forward price
- The last term is the forward-price correction (negligible for 0DTE)

The variance swap strike in volatility units is then:

$$K_{var} = \sqrt{\sigma^2} \times 100 \quad \text{(in vol%)}$$

---

## 2. Trade Execution (from output.json)

### 2.1 Daily Schedule

| Time (ET) | Activity |
|-----------|----------|
| 13:10 | Trade generation (signal computed, orders created) |
| 13:30 - 14:00 | Option execution via TWAP |
| 14:00 - 14:15+ | Delta hedge via ES futures TWAP (5-min intervals) |
| EOD | All options expire worthless or settle (0DTE) |

### 2.2 Option Strip Structure

Each day, the strategy sells ~25 options (a mix of OTM puts and OTM calls) spanning strikes around the forward price:

**Example: 2022-05-26 (SPX forward = 4057.84)**

| Parameter | Value |
|-----------|-------|
| Total options sold | 25 (14 puts + 11 calls) |
| Strike range | 3875 - 4095 |
| Strike spacing | 10 pts (5 pts at edges) |
| Expiry type | "Daily Weekly" (0DTE) |
| Underlying | .SPX |
| Source | VSR 0b (Variance Swap Replication bucket 0) |

### 2.3 The 1/K^2 Weighting

Option quantities follow the variance swap replication formula. For each strike $K_i$:

$$q_i = \frac{w}{K_i^2} \cdot \Delta K_i$$

where $w$ is a constant scaling factor (the "variance notional"). This ensures:

$$|q_i| \times K_i^2 \approx \text{constant} \quad \forall \; K_i$$

**Verification from actual trades (2022-05-26):**

| Strike | Option Type | Quantity | |q| x K^2 |
|--------|-------------|----------|-----------|
| 3875 | Put | -0.00289 | 43,360 (edge: half-width) |
| 3880 | Put | -0.00576 | 86,718 |
| 3890 | Put | -0.00573 | 86,716 |
| ... | ... | ... | ~86,700 (constant) |
| 4000 | Put + Call | -0.00271 each | 43,346 (forward: split) |
| 4060 | Call | -0.00526 | 86,678 |
| 4090 | Call | -0.00518 | 86,672 |
| 4095 | Call | -0.00258 | 43,336 (edge: half-width) |

The edge strikes (3875, 4095) have half the weight because $\Delta K$ is halved at boundaries. Interior strikes maintain $|q| \times K^2 \approx 86,700$ (constant to within 0.05%).

### 2.4 Delta Hedging

After option execution, residual portfolio delta is neutralized via E-mini S&P 500 futures:

| Parameter | Value |
|-----------|-------|
| Instrument | ES (E-mini S&P 500), front month (e.g., ES M22) |
| Source | "Intraday Delta Hedge" |
| Timing | 5-minute TWAP intervals starting after options fill |
| Frequency | ~25 hedge trades per day |
| Typical quantity | ~0.00001 contracts per trade (micro-sized for index context) |

### 2.5 Trade Pairs (Open + Close)

Each option appears twice in the daily trade list:
1. **Open (short)**: Negative quantity, source "VSR 0b", TWAP 13:30-14:00
2. **Close (long)**: Positive quantity, matching at expiry (option expires/settles)

Net position at EOD is always flat (all options either expire worthless or settle in cash).

---

## 3. P&L and Index Construction

### 3.1 Daily P&L

The strategy collects the variance swap premium daily:

$$\text{P\&L}_t = \underbrace{\sum_i q_i \cdot (\text{premium collected})_i}_{\text{Option premium}} - \underbrace{\sum_j \Delta_j \cdot (S_{\text{close}} - S_{\text{exec},j})}_{\text{Delta hedge cost}} - \text{Transaction costs}$$

On days when realized intraday moves are small relative to the implied variance priced into the strip, the strategy profits. On large-move days (especially tail events), losses can be severe.

### 3.2 Index Values (from output.json)

| Date | Index Value | Daily Return (bps) |
|------|-------------|--------------------|
| 2022-05-25 | 100.0000 | -- (inception) |
| 2022-05-26 | 100.2675 | +26.75 |
| 2022-05-27 | 100.3723 | +10.46 |
| 2022-05-31 | 100.3517 | -2.05 |
| 2022-06-01 | 100.0738 | -27.69 |

### 3.3 Risk Characteristics

From the risk nodes in output.json, each option position carries:
- **Delta**: Neutralized via futures (target: portfolio delta = 0)
- **Vega**: Net short vega (short all options)
- **Gamma**: Net short gamma (the core risk - adverse moves cause losses)
- **Theta**: Net positive theta (time decay is the primary income source)

The strategy is structurally: **short gamma, short vega, long theta**.

---

## 4. Drawdown Prediction Signal

### 4.1 The Problem

GSVIVS01 has drawdowns when realized variance exceeds the variance swap strike (i.e., the market moves more than implied). We want to predict these drawdowns and go flat before they occur.

### 4.2 Signal: Variance Risk Premium Gap (IV-RV)

The core signal compares the variance swap strike (what the strategy sells) against our ML-predicted realized volatility (what we expect to actually occur):

$$\text{VRP Gap}_t = \underbrace{\left(\frac{\text{iv\_vs\_0dte}_t}{100}\right)^2}_{\text{Implied variance (annualized)}} - \underbrace{\hat{\sigma}^2_{\text{RV},t} \times 252}_{\text{Predicted RV (annualized)}}$$

where:
- $\text{iv\_vs\_0dte}_t$ = 0DTE variance swap strike from EDRVS_EXPIRY (in vol%, e.g., 15.0)
- $\hat{\sigma}^2_{\text{RV},t}$ = our ML model's predicted next-day realized variance (daily)
- The factor 252 annualizes daily variance to match IV units

### 4.3 Why Variance Swap Strike (Not ATM IV)

The original signal used ATM 0DTE IV. This was structurally wrong:

| Measure | Meaning | Relationship |
|---------|---------|--------------|
| ATM IV | Price of a single at-the-money option | Underestimates what GSVIVS sells |
| Variance Swap Strike | Fair value of the full OTM strip | **Exact match** to what GSVIVS sells |

The gap between them:
$$K_{var} - \sigma_{ATM} \approx 1\text{-}3 \text{ vol pts (skew premium)}$$

Using ATM IV systematically underestimates the premium collected, causing the VRP gap to appear artificially compressed. The signal fires too early (false positives) or too late (after the drawdown has already begun).

### 4.4 Signal Logic

$$\text{Signal}_t = \begin{cases} +1 \; (\text{sell vol / stay invested}) & \text{if VRP Gap}_t > \tau \\ -1 \; (\text{buy vol / go flat}) & \text{if VRP Gap}_t < -\tau_{\text{short}} \\ 0 \; (\text{flat / no position}) & \text{otherwise} \end{cases}$$

where:
- $\tau$ = sell-vol threshold (default: 0, i.e., any positive gap means "safe to be short vol")
- $\tau_{\text{short}}$ = buy-vol threshold (can be asymmetric, requiring stronger conviction to go flat)

### 4.5 Drawdown Prediction Mechanism

The signal predicts drawdowns through three channels:

**Channel 1: VRP Compression**

When the VRP gap approaches zero:
$$\text{VRP Gap}_t \to 0 \implies K_{var}^2 \approx \hat{\sigma}^2_{\text{RV}} \times 252$$

This means the market is pricing implied variance at roughly the same level as our model predicts will be realized. The "edge" of selling variance has disappeared, signaling elevated risk.

**Channel 2: VRP Inversion**

When the gap turns negative:
$$\text{VRP Gap}_t < 0 \implies \hat{\sigma}^2_{\text{RV}} \times 252 > K_{var}^2$$

Our model predicts higher realized vol than the market implies. This is a strong drawdown signal: the strategy is selling variance at a discount to expected realization.

**Channel 3: Sudden VRP Spike (Contrarian)**

A rapid increase in VRP gap after a period of compression often indicates a vol spike has already occurred and the market has overshot. This creates an opportunity to re-enter.

### 4.6 ML Model Inputs

The predicted realized variance $\hat{\sigma}^2_{\text{RV},t}$ comes from our HAR/LightGBM ensemble trained on:

| Feature Layer | Key Inputs |
|--------------|------------|
| 0: HAR Core | log RV daily/weekly/monthly, RQ, RQ interaction |
| 1: Asymmetric | Semivariances, BPV, jumps, continuous variation |
| 2: Options-Implied | iv_vs_0dte (variance swap strike), VRP, skew, term slope, VVIX |
| 3: Microstructure | E-mini L2 order flow, VPIN, depth ratio |
| 4: Cross-Asset | Treasury slope, FX vol, commodity vol |
| 5: Calendar | FOMC, NFP, OpEx, earnings proximity |

### 4.7 Economic Value Translation

The signal is translated into position sizing for GSVIVS01:

$$\text{Position}_t = \text{Signal}_t \times \text{Base Notional}$$

- Signal = +1: Full position in GSVIVS01 (collect VRP)
- Signal = 0: Flat (avoid drawdown)
- Signal = -1: Counter-trade (buy vol protection, used rarely)

**Performance target:** Avoid the 5-10 worst drawdown days per year (each costing 50-200 bps) while remaining invested on the 85-88% of days where VRP is safely positive.

---

## 5. Example output.json Entry

The strategy engine produces a daily JSON output with full trade-level detail. Below is a trimmed example for one day (3 of 77 trades shown):

```json
{
  "date": "2022-05-26",
  "value": {
    "divisor": 1,
    "index value": 100.2674547510181,
    "portfolio value": 100.2674547510181,
    "transaction cost": 0,
    "trades for date": [
      {
        "execution instructions": {
          "end time": "2022-05-26T14:00:00Z",
          "start time": "2022-05-26T13:30:00Z",
          "type": "TWAP"
        },
        "generation time": "2022-05-26T13:10:00Z",
        "instrument": {
          "ex": "2022-05-26",
          "expiry type": "Daily Weekly",
          "instrument type": "O",
          "k": 4040,
          "option type": "Call",
          "underlying asset": ".SPX"
        },
        "quantity": -0.005310912709241232,
        "source": "VSR 0b"
      },
      {
        "execution instructions": {
          "end time": "2022-05-26T14:00:00Z",
          "start time": "2022-05-26T13:30:00Z",
          "type": "TWAP"
        },
        "generation time": "2022-05-26T13:10:00Z",
        "instrument": {
          "ex": "2022-05-26",
          "expiry type": "Daily Weekly",
          "instrument type": "O",
          "k": 3940,
          "option type": "Put",
          "underlying asset": ".SPX"
        },
        "quantity": -0.005585333828770694,
        "source": "VSR 0b"
      },
      {
        "execution instructions": {
          "end time": "2022-05-26T14:05:00Z",
          "start time": "2022-05-26T14:00:00Z",
          "type": "TWAP"
        },
        "generation time": "2022-05-26T13:55:00Z",
        "instrument": {
          "future prefix": "EqSp",
          "instrument type": "F",
          "month": "M22",
          "symbol": "ES"
        },
        "quantity": 0.004969008398141798,
        "source": "Intraday Delta Hedge"
      }
    ],
    "risks for date": "[ ... 268 risk node entries with delta/vega/gamma per position ... ]",
    "pending trades": [],
    "portfolio": "[ ... current open positions ... ]",
    "portfolio weights": [
      { "instrument type": "C", "source": "" },
      1.0
    ]
  }
}
```

**Key fields:**

| Field | Description |
|-------|-------------|
| `index value` | Cumulative strategy index (base 100) |
| `trades for date` | Array of 77 trade objects: 50 options (25 short opens + 25 closes) + 25 futures delta hedges + 2 transaction cost entries |
| `instrument.k` | Strike price (absolute, e.g., 3940) |
| `instrument.ex` | Expiry date (same as trade date for 0DTE) |
| `quantity` | Negative = short (sell), positive = long (buy/close). Weighted by $1/K^2$ |
| `source` | `"VSR 0b"` = variance swap replication, `"Intraday Delta Hedge"` = ES futures |
| `execution instructions` | TWAP window for execution |
| `risks for date` | Per-position Greeks: delta, vega, gamma, theta, vol, forward, discount factor |

---

## 6. Data Sources

### 6.1 Variance Swap Strike (iv_vs_0dte)

| Source | Dataset | Description |
|--------|---------|-------------|
| Primary | EDRVS_EXPIRY (Marquee) | GS Equity Variance Swap Levels by Listed Expiry. Provides `fairVariance` and `fairVolatility` by specific SPX expiry date. |
| Fallback | EDRVOL_PERCENT_EXPIRY | Reconstruct from full IV strike grid using CBOE discrete formula |

**Processing:** $\text{iv\_vs\_0dte} = \sqrt{\text{fairVariance}} \times 100$ (convert from annualized variance to vol%)

### 6.2 Realized Volatility

5-minute realized variance computed from intraday returns:

$$RV_t = \sum_{j=1}^{M} r_{t,j}^2$$

where $r_{t,j}$ are intraday log-returns at 5-minute frequency ($M = 78$ intervals per day for US equity hours).

### 6.3 Strategy Index

GSVIVS01 index levels from TSDB (`gsvivs01` symbol), providing historical P&L for backtesting signal effectiveness.

---

## 7. Summary of Key Equations

| Equation | Purpose |
|----------|---------|
| $K_{var}^2 = \frac{2 e^{rT}}{T} \sum_i \frac{\Delta K_i}{K_i^2} Q(K_i)$ | Variance swap strike (what GSVIVS sells) |
| $q_i = \frac{w}{K_i^2} \cdot \Delta K_i$ | Option quantity weighting (replicates variance swap) |
| $\text{VRP Gap} = (K_{var}/100)^2 - \hat{\sigma}^2_{RV} \times 252$ | Drawdown prediction signal |
| $\hat{\sigma}^2_{RV} = f(\text{HAR features, microstructure, cross-asset, ...})$ | ML realized vol forecast |
| $\text{Signal} = \mathbb{1}[\text{VRP Gap} > \tau] - \mathbb{1}[\text{VRP Gap} < -\tau_s]$ | Position decision |
