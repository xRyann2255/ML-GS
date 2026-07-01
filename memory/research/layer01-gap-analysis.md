---
created: 2026-05-08
updated: 2026-05-11
tags: [gap-analysis, layers, features, implementation, resolved]
status: archived
priority: P2
source: PDF cross-reference (vol-project-ref.pdf Ch.3-4, vol-learning-guide.pdf Ch.4,6,10)
relates: [research-journal, har-components, jump-detection, leverage-effect]
---

# Layer 0-1 Gap Analysis — PDF Cross-Reference

> **Archived 2026-05-11:** All 9 gaps below are now implemented and tested (370 tests passing). See `workspace/research/feature-engineering-status.md` for current state.

Cross-referenced our `features/har.py` and `features/asymmetry.py` implementations against both project PDFs. Below: what's correct, what's missing, and prioritized next steps.

---

## What's Correctly Implemented

| Code | Paper Reference | Verdict |
|------|----------------|---------|
| `compute_realized_variance`: sum(r^2) no mean subtraction | Andersen et al. 2003 | Correct |
| `compute_log_rv_features`: 1/5/22 day windows in log-space | HAR (Corsi 2009), vol-project-ref Ch. 3 | Correct |
| `compute_rq`: (N/3)*sum(r^4) | Bollerslev-Patton-Quaedvlieg 2016 | Correct |
| `rq_rv_interaction_d`: log_rv_d * sqrt(rq_d) | HARQ Eq. 3.2 in project-ref | Correct |
| `compute_semivariances`: RS+, RS- with indicator functions | Patton-Sheppard 2015 | Correct |
| `compute_bpv`: (pi/2) * sum(abs(r_i)*abs(r_{i-1})) | BNS 2004 | Correct |
| `detect_jumps`: BNS z-test with theta = 0.6090 | BNS 2006 | Correct |
| `compute_jump_variation`: max(RV-BPV, 0) * indicator | Andersen et al. 2007 | Correct |
| `compute_continuous_variation`: max(RV - J^2, 0) | HAR-CJ decomposition | Correct |

---

## Missing Features (Prioritized)

### HIGH PRIORITY — Implement Next

#### 1. Signed Negative Jump J- (Intraday Decomposition)

**Paper source:** Vol-project-ref Table 4.1: "J-(signed neg. jump): Large negative moves beyond threshold. 1-3% QLIKE gain beyond unsigned jumps (Andersen et al., 2007). Horizon: 1d-5d."

**Learning guide Eq. 10.7:**
```
J+ = sum(r^2 * I(r > 0, |r| > theta))
J- = sum(r^2 * I(r < 0, |r| > theta))
```
where theta is an intraday jump threshold from Lee-Mykland (Ch. 4).

**Current state:** We only have unsigned jump variation (J = max(RV-BPV, 0) * indicator). No signed decomposition.

**Why it matters:** "Negative jumps predict higher future volatility than positive jumps of the same magnitude" (Patton-Sheppard 2015, Bollerslev et al. 2009). The 1-3% QLIKE gain is explicitly called out in the project-ref paper.

**Implementation needed:**
- Lee-Mykland intraday jump detection (tests each return against local vol estimate)
- Split detected jumps into J+ and J- by sign
- Add as features alongside existing unsigned J

---

#### 2. Triple Expansion: {level, change, z-score} for All Base Features

**Paper source:** Vol-project-ref Ch. 6.3 + Ch. 8.4: "For each base quantity, compute {level, change, z-score} systematically. This triples the feature count and captures state, direction, and unusualness in a single pass."

**Vol-project-ref Table 6.2:**
| Variant | Definition | Purpose |
|---------|-----------|---------|
| Level | x_t | Current state |
| Change | x_t - x_{t-1} | Directional momentum |
| Z-score | (x_t - mean_20) / std_20 | Deviation from recent norm |

**Current state:** We only compute level values. No change or z-score variants.

**Why it matters:** "Trees handle redundancy naturally via split selection; no manual decorrelation needed." This turns our 11 Layer 0+1 features into 33 for LightGBM at zero data cost. The project-ref explicitly calls this the standard engineering principle.

**Implementation needed:**
- Generic `triple_expand(series, window=20)` utility
- Apply to: log_rv_d, log_rv_w, log_rv_m, sqrt_rq, rs_positive, rs_negative, bpv, continuous_variation, jump_variation, signed_jump, noise_gap

---

#### 3. Weekly Semivariances (RS-(w), RS+(w))

**Paper source:** Vol-project-ref Table 4.1: "RS-(w) (weekly): Persistent downside memory; smooths daily noise in the negative semivariance. Horizon: 1d-5d."

**Learning guide Ch. 6.4:** The SHAR model uses weekly rolling semivariances. The full specification:
```
RV_{t+1} = b0 + b+_d * RS+_t + b-_d * RS-_t + b_w * RV(w)_t + b_m * RV(m)_t + e
```
But a richer SHAR uses `RS-(w)` and `RS+(w)` at the weekly horizon too.

**Current state:** We compute daily RS+/RS- only. No 5-day rolling semivariance averages.

**Why it matters:** The weekly negative semivariance is "persistent downside memory" -- it smooths the daily RS- noise and captures sustained selling pressure over a week, which is a stronger predictor than daily RS- alone.

**Implementation needed:**
- Rolling 5-day average of RS+ and RS- series
- Add RS-(w), RS+(w) to the SHAR design matrix builder

---

### MEDIUM PRIORITY

#### 4. Lee-Mykland Intraday Jump Detection

**Paper source:** Learning guide Ch. 4.4: "The Lee-Mykland test provides both jump detection and jump timing at intraday frequency. It identifies the specific returns within the day that are jumps, along with their sizes."

**Vol-project-ref Ch. 4.4:** "Jump significance is assessed via the Lee-Mykland test, which flags individual intraday returns exceeding a time-varying threshold calibrated to local bipower variation."

**Current state:** Only BNS (daily-level binary: "did a jump occur today?"). No intraday jump timing.

**Why it matters:** Required to construct the signed jump features (J+/J-) correctly. Also enables richer jump features like jump count, average jump size, largest jump magnitude. The project-ref paper uses Lee-Mykland as the *primary* jump test, not BNS.

**Implementation:**
- For each return r_{t,i}: compute local volatility from window of K=156 recent returns (excluding current)
- Standardize: L_i = r_i / sigma_local
- Flag as jump if |L_i| exceeds extreme-value-theory threshold (Gumbel distribution)
- Return: jump times, sizes, signs

---

#### 5. Lagged Signed Daily Return

**Paper source:** Learning guide Ch. 6.6, HAR-X: "Common choices for X_j,t: ... lagged daily return r_t (signed, to capture leverage)."

**Current state:** Not computed. We have semivariances but not the simple signed return.

**Why it matters:** Standard HAR-X regressor that captures the leverage effect directly. Yesterday's return sign and magnitude predict tomorrow's RV. Free data -- just close-to-close log return.

**Implementation:** `r_t = log(P_close_t / P_close_{t-1})`, include as feature.

---

#### 6. Standalone sqrt(RQ) as Feature Column

**Paper source:** Learning guide Ch. 10.3: "Include sqrt(RQ) as a standalone feature column. It serves double duty: (1) tree models can learn to down-weight noisy RV days; (2) it measures intraday volatility-of-volatility."

**Current state:** sqrt_rq_d exists in `compute_harq_features()` and is used in `build_har_design_matrix` only when `include_rq_interaction=True`. It's always bundled with the interaction term.

**Why it matters:** Tree models benefit from having sqrt(RQ) as a standalone split variable even without the interaction. Currently if you don't request the interaction, you don't get sqrt(RQ) at all.

**Implementation:** Always include `sqrt_rq_d` in the design matrix as a standalone column.

---

#### 7. Log-Normal Retransformation Bias Correction

**Paper source:** Vol-project-ref Ch. 3 callout box: "When computing QLIKE, convert back to levels: RV_hat = exp(log_RV_hat + sigma^2/2), where sigma^2 is the residual variance (bias correction for the log-normal retransformation)."

**Current state:** Our `metrics.py` QLIKE works in log-space directly. No bias correction applied when converting predictions back to level-space.

**Why it matters:** Without the bias correction, exp(log_RV_hat) systematically underestimates E[RV]. This affects any QLIKE evaluation done in variance space and the economic-value backtests.

**Implementation:** Add `retransform_log_to_level(log_rv_pred, residual_variance)` utility that applies exp(x + s^2/2).

---

#### 8. Realized Skewness

**Paper source:** Learning guide Ch. 10.5: "RSkew = (1/n) * sum(r^3) / ((1/n) * sum(r^2))^(3/2)"

**Amaya-Christoffersen-Jacobs-Vasquez (2015, JFE):** "Realized skewness and realized kurtosis have predictive power for future RV beyond the standard HAR components."

**Current state:** Not implemented.

**Why it matters:** Cheap to compute from existing intraday returns. Negative realized skewness signals crash risk and elevated future vol. Low standalone QLIKE gain but useful for regime detection in tree models.

**Implementation:** `realized_skewness = mean(r^3) / (mean(r^2))^(3/2)`

---

### LOWER PRIORITY

#### 9. Overnight Return (Close-to-Open)

**Paper source:** Learning guide Ch. 6.6: listed as standard HAR-X predictor.

**Current state:** Not computed. All features use intraday data only.

**Why it matters:** Overnight return captures information arrival during non-trading hours (earnings, macro, geopolitical). Moderate predictive power for next-day RV.

**Implementation:** `r_overnight = log(P_open_t / P_close_{t-1})`

---

#### 10. Realized Kurtosis

**Paper source:** Learning guide Ch. 10.5: "RKurt = (1/n)*sum(r^4) / ((1/n)*sum(r^2))^2"

**Current state:** Not implemented. (Note: RQ already captures the numerator information.)

**Why it matters:** Shape feature. High kurtosis days have fat-tailed intraday distribution and elevated future vol risk. Expect it to rank low in importance per the learning guide: "Include in initial feature set but expect them to rank low."

**Implementation:** `realized_kurtosis = mean(r^4) / (mean(r^2))^2`

---

#### 11. Threshold/Truncation Method (Corsi-Pirino-Reno 2010)

**Paper source:** Learning guide Ch. 4.6: alternative to BNS for C/J decomposition, more robust when noise is present.

**Current state:** Only BNS implemented.

**Why it matters:** May give cleaner C/J decomposition for high-frequency data. Lower priority because BNS works well at 5-min frequency for liquid assets.

---

## Design/Architecture Issues

| # | Issue | Paper Reference | Fix |
|---|---|---|---|
| 1 | `build_har_design_matrix` doesn't support SHAR horizon variants | Project-ref needs RS-(w), RS+(w) for full SHAR at weekly horizon | Add rolling semivariance features to design matrix builder |
| 2 | No standalone sqrt(RQ) as feature | Learning guide Ch. 10.3 says include it always | Expose as separate column in design matrix |
| 3 | BNS is sole jump test but project-ref expects Lee-Mykland as primary | Vol-project-ref Ch. 4.4: "Jump significance assessed via Lee-Mykland test" | Implement Lee-Mykland; keep BNS as fast daily indicator |

---

## Implementation Order (Recommended)

1. **Lee-Mykland intraday jump detection** (unlocks signed jumps J+/J-)
2. **Signed jump features J+/J-** using Lee-Mykland output
3. **Weekly semivariances RS-(w)/RS+(w)** + update design matrix builder
4. **Triple expansion utility** {level, change, z-score} for all base features
5. **Standalone sqrt(RQ)** in design matrix
6. **Lagged signed daily return** (trivial, free)
7. **Realized skewness + kurtosis** (cheap higher moments)
8. **Retransformation bias correction** in metrics.py
9. **Overnight return** (requires open price data)

---

## Key Insight from Papers

> "The first 20 features (Layers 0-2) achieve 85% of attainable accuracy. The remaining 60-100 features add 15%." -- Vol-project-ref Ch. 8.2

> "Replacing RV with RS+ and RS- in a HAR regression (the SHAR model) costs zero additional data and yields 3-8% QLIKE improvement. This is the single cheapest feature upgrade after the RQ interaction." -- Vol-project-ref Ch. 4.4 callout

> "Signed negative jump J-: 1-3% QLIKE gain beyond unsigned jumps." -- Vol-project-ref Table 4.1

> "For each base quantity, compute {level, change, z-score} systematically. Trees handle redundancy naturally." -- Vol-project-ref Ch. 8.4

The biggest single-feature gain still on the table is the **signed negative jump** using Lee-Mykland intraday detection. The biggest systemic gain is the **triple expansion** which turns 11 Layer 0+1 features into 33 for LightGBM at zero data cost.
