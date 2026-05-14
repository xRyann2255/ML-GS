# Chapter 17: Practical Applications and Project Roadmaps -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 31
**Verified:** 0/31
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 25 | qualitative | Volatility targeting is the simplest and most widely used application of a vol forecast in systematic investing | [uncited] | | | Industry-practice claim; verifiable via practitioner surveys or AQR/Man Group publications |
| 2 | 26 | methodological | Vol-targeting sizes positions inversely proportional to forecast vol so portfolio risk stays roughly constant over time | [uncited] | | | Standard vol-targeting description |
| 3 | 33 | qualitative | The workhorse volatility estimate used by the vast majority of systematic funds for position sizing is EWMA, not GARCH or HAR | [uncited] | | | Industry-practice claim; verifiable via practitioner literature |
| 4 | 34-37 | defining-formula | EWMA: $\hat\sigma^2_t = (1-\delta) r_{t-1}^2 + \delta \hat\sigma^2_{t-1}$ | [uncited] | | | Standard EWMA formula; appears in RiskMetrics (1996), Hull textbook |
| 5 | 38 | numerical-fact | EWMA half-life parameter delta is chosen to match approximately 20 to 60 trading days | [uncited] | | | Practitioner convention; verifiable via RiskMetrics or fund literature |
| 6 | 40 | qualitative | EWMA's popularity stems from simplicity, low latency, and requiring exactly one parameter | [uncited] | | | |
| 7 | 59-61 | defining-formula | Volatility-targeted weight: $w_t = \sigma_{\text{target}} / \hat\sigma_t$ | [uncited] | | | Standard vol-targeting formula; appears in Moreira and Muir (2017), Moskowitz et al. (2012) |
| 8 | 63 | supporting-formula | Vol-targeted portfolio return: $r_t^{\text{VT}} = w_t \cdot r_t$ | [uncited] | | | Direct consequence of the weight definition |
| 9 | 69 | attribution | Moreira and Muir (2017) showed that vol-targeting adds approximately 0.3 Sharpe ratio across equity indices, currencies, and commodities | MoreiraMuir2017 | | | Key quantitative claim -- verify the 0.3 Sharpe figure and asset class coverage |
| 10 | 70 | qualitative | The mechanism of vol-targeting Sharpe improvement: reducing exposure before drawdowns truncates the left tail | MoreiraMuir2017 | | | Verify this is the mechanism described by Moreira and Muir |
| 11 | 103 | numerical-fact | Worked example day 13: w_EWMA = 10/12.0 = 0.83 | [uncited] | | | Arithmetic check: 10/12.0 = 0.833, rounds to 0.83. Correct |
| 12 | 103 | numerical-fact | Worked example day 13: w_ML = 10/12.2 = 0.82 | [uncited] | | | Arithmetic check: 10/12.2 = 0.820, rounds to 0.82. Correct |
| 13 | 105 | numerical-fact | Worked example day 15: w_EWMA = 10/12.1 = 0.83 | [uncited] | | | Arithmetic check: 10/12.1 = 0.826, rounds to 0.83. Borderline -- 0.83 vs more precise 0.827 |
| 14 | 108 | numerical-fact | Worked example day 18: w_EWMA = 10/19.4 = 0.52 | [uncited] | | | Arithmetic check: 10/19.4 = 0.5155, text shows 0.52. Rounds to 0.52 at 2 decimal places. Correct |
| 15 | 109 | numerical-fact | Worked example day 19: w_ML = 10/33.8 = 0.30 | [uncited] | | | Arithmetic check: 10/33.8 = 0.2959, text shows 0.30. Rounds to 0.30 at 2dp. Correct |
| 16 | 127 | numerical-fact | Worked example summary: EWMA ann. return 8.2%, HAR 8.5%, ML 8.9% | [uncited] | | | Hypothetical backtest values -- illustrative, not empirically sourced |
| 17 | 128 | numerical-fact | Worked example summary: EWMA ann. vol 10.8%, HAR 10.3%, ML 10.1% | [uncited] | | | Hypothetical backtest values -- illustrative |
| 18 | 129 | numerical-fact | Worked example summary: EWMA Sharpe 0.76, HAR 0.82, ML 0.88 | [uncited] | | | Hypothetical; verify internal consistency: 8.2/10.8=0.759 (rounds 0.76), 8.5/10.3=0.825 (rounds 0.82/0.83), 8.9/10.1=0.881 (rounds 0.88). HAR Sharpe 0.825 displayed as 0.82 -- borderline |
| 19 | 130 | numerical-fact | Worked example summary: EWMA max drawdown -12.4%, HAR -9.8%, ML -7.1% | [uncited] | | | Hypothetical backtest values -- illustrative |
| 20 | 131 | numerical-fact | Worked example summary: EWMA Calmar 0.66, HAR 0.87, ML 1.25 | [uncited] | | | Arithmetic check: 8.2/12.4=0.661 (0.66 OK), 8.5/9.8=0.867 (0.87 OK), 8.9/7.1=1.254 (1.25 OK). All correct |
| 21 | 136 | numerical-fact | ML model adds 0.12 Sharpe over the baseline | [uncited] | | | Arithmetic check: 0.88 - 0.76 = 0.12. Correct |
| 22 | 136 | qualitative | ML model "nearly halves" the maximum drawdown | [uncited] | | | Check: -12.4% to -7.1% is a 43% reduction. "Nearly halves" is a stretch -- 43% is closer to "reduces by over 40%". Borderline characterization |
| 23 | 144 | attribution | Moskowitz, Ooi, Pedersen (2012) use time-series momentum across 58 futures | MoskowitzOoiPedersen2012 | | | Verify the number 58 futures |
| 24 | 144 | methodological | TSMOM signal = sign of 12-month return, position size = 40%/sigma_hat_t | MoskowitzOoiPedersen2012 | | | Verify the 40% scaling factor and 12-month lookback |
| 25 | 176-177 | qualitative | When dealers are long gamma, they delta-hedge by selling into rallies and buying dips, which suppresses realized vol below what pure news flow would generate | [uncited] | | | Standard dealer-hedging mechanism; verifiable via options market structure references |
| 26 | 178 | qualitative | When dealers are short gamma (common after selling structured products like autocallables), they hedge by buying into rallies and selling into dips, amplifying moves and increasing realized vol | [uncited] | | | Standard dealer-hedging mechanism |
| 27 | 183-185 | defining-formula | GEX formula: $\text{GEX} \approx \sum_K \text{OI}_K \times \Gamma_K \times 100 \times S$ | Bennett2014 | | | Verify this specific GEX formula and whether Bennett (2014) is the correct source |
| 28 | 190 | attribution | Adding sign(GEX) or GEX-quintile as a feature to HAR-X is a novel extension not yet thoroughly explored in the academic literature | Bennett2014 | | | Verify what Bennett (2014) actually covers re: GEX and whether the "novel" claim is warranted |
| 29 | 200 | qualitative | The primary source of dealer short-gamma exposure is structured products (autocallables, barrier options, worst-of notes) | [uncited] | | | Industry-knowledge claim; verifiable via structured products literature |
| 30 | 203 | numerical-fact | Systematic issuance of structured products estimated at hundreds of billions of notional globally | [uncited] | | | Verify order of magnitude -- uncited numerical estimate |
| 31 | 207 | qualitative | Near options expiry, large open interest at specific strikes creates pinning effects: stock gravitates toward the strike as dealers' gamma hedging intensifies | [uncited] | | | Well-known effect; verifiable via Ni, Pearson, Poteshman (2005) or similar pinning literature |
