# Open Questions

Running list of things to investigate. Add questions as they come up. Move to research-journal.md when explored.

## Data Understanding (Priority -- do these first)

- [ ] What does the distribution of daily RV look like for our 34 symbols? Heavy tails? Log-normal?
- [ ] How does 5-min RV compare to tick-level RV on the same asset? How much does microstructure noise matter in practice?
- [ ] What's the autocorrelation structure of RV on our data? Does the 1/5/22-day HAR decomposition actually fit?
- [ ] How do jumps show up in our data? How frequent, how large, which assets?
- [ ] What does the intraday volatility pattern look like? U-shape? How strong?
- [ ] How correlated is RV across our asset universe? Sector structure? Lead-lag?

## Feature Understanding (After data exploration)

- [ ] Does the leverage effect (negative return -> higher future vol) show up clearly in our data? How asymmetric?
- [ ] How much do realized semivariances (RS+, RS-) differ in predictive power? Patton-Sheppard say RS- dominates -- is that true for our assets?
- [ ] Does realized quarticity (RQ) actually predict HAR residual size, as HARQ assumes?
- [ ] What do VIX-RV gaps look like over time? Is the variance risk premium stable or regime-dependent?
- [ ] Do overnight returns predict next-day RV? How much information is in the close-to-open gap?

## Methodological Questions

- [ ] How sensitive are QLIKE rankings to the evaluation window? Does the "best" model change across regimes?
- [ ] How does purged k-fold CV compare to expanding-window in practice on our data?
- [ ] What's the right way to handle the COVID period -- include, exclude, or treat as a separate regime?

## Bigger Picture

- [ ] Where exactly does HAR fail? Regime transitions? High-vol periods? Specific assets?
- [ ] If we could only add ONE feature to HAR, what would give the biggest QLIKE improvement?
- [x] What features do the Optiver competition winners actually use, and which translate to daily forecasting? -- Answered 2026-05-06, see research-journal.md and features/microstructure.md
