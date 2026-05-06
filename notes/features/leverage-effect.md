# Leverage Effect

What we've learned about return-volatility asymmetry.

## Findings

(To be filled as we explore data)

## Questions to Answer

- How asymmetric is the return-vol relationship on our assets?
- Do realized semivariances (RS+, RS-) diverge in predictive power?
- Is the leverage effect stronger intraday or at daily frequency?
- Does the signed jump variation add anything beyond semivariances?

## Deep Research Findings (2026-05-06)

**Signed semivariance asymmetry (key empirical result):**
- Patton & Sheppard (2015, RES): "Good Volatility, Bad Volatility" -- negative semivariance has substantially more predictive power than positive semivariance for future RV. Negative jumps raise future RV; positive jumps lower it. Models exploiting this asymmetry deliver "significantly better out-of-sample forecast performance" (`patton-sheppard-2015` in bibliography)
- This is one of the most robust and replicable findings in the vol forecasting literature -- 3-8% QLIKE improvement per the vol learning guide
- HAR with signed semivariances (SHAR) is a stronger baseline than plain HAR -- ML models should be benchmarked against SHAR, not just HAR
