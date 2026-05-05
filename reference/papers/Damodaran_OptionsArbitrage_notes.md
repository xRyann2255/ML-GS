# Options Arbitrage — Aswath Damodaran (NYU Stern)

**Source:** https://pages.stern.nyu.edu/~adamodar/New_Home_Page/invfables/optionarb.htm
**Used in:** Ch 13 (Arbitrage zoo), Ch 14 (Options: payoffs, no-arb bounds, put-call parity)

## Overview

Options are *rights*, not obligations. Calls grant purchase rights; puts grant sale rights. Buyer losses are capped at the premium, enabling risk-free positions when combined with the underlying.

## Exercise arbitrage — the bounds

**Basic no-arbitrage bounds (intrinsic value):**
- Call: `C > max(0, S − K)`
- Put: `P > max(0, K − S)`

**Tightened bounds (with time value, continuous-compounding):**
- Call: `C > max(0, S − K·e^{−rT})`
- Put: `P > max(0, K·e^{−rT} − S)`

**Worked example.** A $30-strike European call on a $40 stock with one-year expiry at r = 11%:
- Lower bound = `S − K·e^{−rT} = 40 − 30·e^{−0.11} ≈ 40 − 26.88 ≈ 13.12`
- (Damodaran uses a simpler `40 − 27.27 = 12.73` with discrete discounting.)
- If the call trades below this, the arbitrage is: **buy the call**, **short the stock** (receive S), **invest proceeds at riskless rate**. At expiry, cover the short with the call or market. Positive P&L guaranteed with zero initial capital.

## Replicating portfolio (binomial sketch)

A portfolio of `Δ` shares + riskless bond can replicate an option payoff exactly. If the option's market price differs from its replicating-portfolio cost, buy the cheap side and sell the expensive side → locked-in risk-free profit.

Requirements:
- Simultaneous trading in both markets (execution risk)
- Low transaction costs
- Access to riskless borrowing and short-selling

This is the *same* no-arbitrage argument that drives Black–Scholes in continuous time.

## Put–call parity

`C − P = S − K·e^{−rT}` (for European options, no dividends)

**Construction of the identity.** Consider the portfolio: long call, short put, short stock, long `K·e^{−rT}` in bonds.
- At expiry T, the bond pays K.
- If S_T > K: call pays S_T − K, put = 0, stock owed costs S_T. Net: (S_T − K) − S_T + K = 0.
- If S_T < K: call = 0, put costs K − S_T, stock owed costs S_T. Net: −(K − S_T) − S_T + K = 0.

Since the portfolio pays zero in every state, it must be worth zero today → the identity.

**Arbitrage on violation.** If the LHS < RHS, buy the LHS, sell the RHS, pocket the difference, carry to expiry → zero payoff, locked-in profit.

## Relative pricing rules

For options on the same underlying:
- Lower-strike calls ≥ higher-strike calls (same maturity)
- Higher-strike puts ≥ lower-strike puts (same maturity)
- Longer-dated options ≥ shorter-dated options (same strike)

Violations enable spread arbitrages.

## Notes for the PDF

- Use Damodaran's *derivation style* — every bound proved by exhibiting an explicit arbitrage portfolio — as the template for Ch 14.
- The discrete-discounting example can be upgraded to continuous in the PDF without loss.
