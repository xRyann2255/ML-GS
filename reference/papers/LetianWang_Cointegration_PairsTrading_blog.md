# Cointegration and Pairs Trading — Letian Wang

**Source:** https://letianzj.github.io/cointegration-pairs-trading.html
**Used in:** Ch 9 (Mean reversion / OU), Ch 10 (Pairs trading and cointegration)

## Key concepts

**Cointegration ≠ correlation.** "Two stock prices follow two straight lines with different slopes, then they are positively correlated but not cointegrated." Cointegration means individually non-stationary series combine linearly to form a stationary series.

## Statistical tests

1. **CADF (Cointegrated Augmented Dickey–Fuller) test.** Linear-regress one series on the other to obtain a hedge ratio, then ADF-test the residuals for stationarity. For the classic EWA/EWC pair the test statistic was −3.667 with p-value 0.0046 → cointegrated.

2. **Johansen test.** Tests cointegration rank *simultaneously* while finding hedge ratios, avoiding the error accumulation of the Engle–Granger two-step procedure. Johansen's trace statistic reports one number per rank hypothesis.

## Trading implementation

- **Signal construction.** Compute the spread `y − βx`, then apply Bollinger bands (rolling mean ± k·rolling std) to the spread.
- **Entry rules.** Short the spread when it hits the upper band; go long the spread when it hits the lower band.
- **Exit rule.** Close when the spread crosses the centreline.
- **Walk-forward estimation.** Use a rolling window regression to avoid look-ahead bias; the hedge ratio updates each window.

## Mathematical foundation

The appendix treats error-correction models (ECM): cointegrated pairs share a common stochastic trend, and the ECM representation isolates the mean-reverting component. Engle–Granger's representation theorem guarantees cointegration ↔ ECM.

## Notes for the PDF

- Use this blog alongside Chan *Algorithmic Trading* Ch 2 as the Python-code companion.
- The EWA/EWC example is a canonical teaching pair; keep it as a worked example but flag that alpha has likely decayed since publication.
