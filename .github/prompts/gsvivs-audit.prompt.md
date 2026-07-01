---
description: "GSVIVS01 output.json full daily-lifecycle audit"
model: Claude Opus 4.6
---

# GSVIVS01 output.json Full Audit

## Objective

Parse and document the complete GSVIVS01 strategy history in `data/external/output.json`. This is a ~73k-line JSON file containing the full daily trade lifecycle of a short variance-swap replication strategy on SPX 0DTE options. The goal is to:

1. **Confirm the daily structure** across the entire history
2. **Extract the exact $K_{\text{var}}$ (variance-swap strike)** the strategy sold each day
3. **Document what IV data is available** for building a backtester overlay signal

---

## Context: What We Already Know (from 5 sample days)

From a preliminary analysis of the first 5 days (2022-05-25 to 2022-06-01), we observed:

### Daily Pattern
- Each afternoon at **13:10 ET**, the signal fires
- At **13:30–14:00 ET**, TWO strips are sold simultaneously:
  - **0DTE strip** (26 options, expiring today at close) — contributes to today's P&L
  - **1DTE strip** (26 options, expiring tomorrow at close) — contributes to TOMORROW's P&L
- Delta hedges via ES futures in 5-minute TWAP intervals from 14:00–14:35
- Index close time: 22:00 UTC (= 18:00 ET, after settlement)

### Key Structural Finding
- The **1DTE strip dominates next-day exposure**: its gamma runs from 9:30–16:00 the following day
- The $K_{\text{var}}$ of that 1DTE strip is **known at T-1 13:30** (execution time)
- This means a **pre-open signal** (before T's open) can compare the known sold $K_{\text{var}}$ against a next-day RV forecast — clean lookahead-free design

### Per-Strike Data Available
Each option has in its `baseline risks`:
- `vol`: the implied vol at that strike (strike-specific, from SecDB model)
- `price`: option mid price
- `delta`, `vega`: Greeks
- `fwd`, `spotref`, `df`: forward, spot reference, discount factor
- `k`: strike price
- `option type`: Put or Call
- `ex`: expiry date

### Hunch / Hypothesis

**The per-strike execution prices in this file give us the EXACT $K_{\text{var}}$ the strategy sold each day** — reconstructable via the CBOE discrete formula:

$$K_{\text{var}}^2 = \frac{2}{T} \sum_i \frac{\Delta K_i}{K_i^2} \cdot e^{rT} \cdot Q(K_i)$$

where $Q(K_i)$ is the mid price of each OTM option (put if $K < F$, call if $K > F$). This is better than any Marquee data source because it's the ACTUAL execution, not a model estimate. If the full history covers 2022-05-25 through present (~600+ trading days), we have a complete daily $K_{\text{var}}$ time series for the signal.

---

## Tasks

### 1. Parse the Full File Structure

- Count total trading days
- Confirm date range (start to end)
- Verify every day has the same structure (or document exceptions)
- Check for missing days, holidays, half-days, anomalies

### 2. Confirm the Two-Strip Pattern

For a random sample of ~20 days spread across the history:
- Confirm each day has expiries for TODAY and TOMORROW (or next biz day)
- Confirm ~26 options per strip
- Confirm generation times always come from the PRIOR day's afternoon
- Document any exceptions (e.g., does the pattern change around holidays, triple witching, market half-days?)

### 3. Extract Per-Day Summary

For the full history, extract a table with:
- Date
- Index value (open/close or just close)
- Daily return (bps)
- Number of options in 0DTE strip
- Number of options in 1DTE strip
- Forward price (from `fwd` in baseline risks)
- Strike range (min K to max K, as % of forward)
- Sum of execution prices × quantities (total premium collected)

### 4. Reconstruct $K_{\text{var}}$ Daily

For each day's 1DTE strip:
- Apply the CBOE discrete formula to compute $K_{\text{var}}$
- Use the `price` field from `baseline risks` as $Q(K_i)$
- Use `fwd` as the forward $F$
- Use `df` for the discount factor
- Compute the annualized implied variance and express as vol (%)
- Output: daily time series of $K_{\text{var}}$ (the exact variance-swap strike sold)

### 5. Compare Against ATM IV

- From the strike grid, identify the ATM strike (closest to forward)
- Extract its `vol` field — this is the ATM implied vol
- Compute the ratio: $K_{\text{var}} / \sigma_{\text{ATM}}$ across all days
- Document the mean, std, min, max of this ratio (expected: 1.02–1.15, i.e., $K_{\text{var}}$ is 2–15% above ATM)

### 6. Identify Drawdown Days

- Find all days where index return < -20 bps
- For those days: what was the realized variance? What was $K_{\text{var}}$?
- Is the drawdown always an RV > $K_{\text{var}}$ event?
- Are drawdown days concentrated (clustering)?

### 7. Document the P&L Decomposition

For each day, identify how P&L breaks down:
- `Execution Cash`: premium collected
- `Transaction Costs O`: option transaction costs
- `Transactions Costs Fw`: futures hedge transaction costs
- `Initial`: base capital (should be 100 at start)
- `portfolio value`: end-of-day portfolio value

### 8. Weekend/Holiday Handling

- Friday strips: do they sell Monday-expiry (1DTE = 3 calendar days)?
- How does the strategy handle long weekends?
- Is there ever a 2DTE or 3DTE strip?

---

## Output Requirements

Write all findings to `workspace/tmp/gsvivs_audit_results.md` with:
1. Summary statistics table
2. The confirmed daily lifecycle diagram
3. Any anomalies or exceptions found
4. The full daily $K_{\text{var}}$ time series (as a table or reference to a parquet/CSV)
5. Recommendation for which IV source to use in the backtester

Also save the computed $K_{\text{var}}$ time series as `workspace/tmp/gsvivs_kvar_daily.csv` with columns: `date, kvar_0dte, kvar_1dte, atm_vol_0dte, atm_vol_1dte, forward, index_value, daily_return_bps`.

---

## Technical Notes

- The file is `data/external/output.json` (full strategy history)
- Use `python3` for parsing (the file may be large)
- The JSON structure is an array of daily entries: `[{"date": "...", "value": {...}}, ...]`
- Within each day: `value.risks for date` contains the trade array
- Instruments alternate with their risk data in the array (not nested cleanly — iterate carefully)
- Times are UTC (ET = UTC - 4 in summer, UTC - 5 in winter)
- Use `./vol exec` or `./vol bg` for any compute commands (never run python directly)
- Write intermediate scripts to `workspace/tmp/` if needed
- Read `.github/copilot-instructions.md` before starting

---

## Reference Files

- `workspace/docs/vol-learning-guide/ch19-gsvivs01.md` — theory + signal design
- `workspace/docs/gsvivs_iv_improvement_plan.md` — IV data source options
- `workspace/docs/gsvivs_audit_results.md` — prior audit findings
- `workspace/tmp/output.json` — the OLD 5-day sample (for reference, ignore for this audit)
