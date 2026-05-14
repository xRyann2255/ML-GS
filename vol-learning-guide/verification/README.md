# Verification Progress

Last updated: 2026-05-14

**Total claims: 1,126 | Verified: 545/580 (Tiers 1-2) | Errors found: 16 (all fixed) | Unverified: 35 (missing papers)**

## Tier 1: Pipeline-critical -- VERIFIED

| Chapter | File | Claims | Verified | Errors | Status |
|---|---|---|---|---|---|
| Ch 10: Feature Engineering | ch10-feature-engineering.md | 89 | 85/89 | 1 | Verified |
| Ch 6: HAR Model | ch06-har-model.md | 52 | 46/52 | 3 | Verified |
| Ch 4: Jumps & Continuous Variation | ch04-jumps-continuous-variation.md | 50 | 50/50 | 1 | Verified |
| Ch 16: Forecast Evaluation | ch16-forecast-evaluation.md | 62 | 55/62 | 0 | Verified |
| **Tier 1 subtotal** | | **253** | **236** | **5** | |

### Errors Fixed in Tier 1

1. **Ch 10, Claim 34**: Amihud illiquidity scaling factor was $10^6$, should be $10^5$ per Amihud (2002) fn.6
2. **Ch 6, Claims 12-13**: Corsi coefficient values 0.36/0.28/0.28 were simulation calibration, not empirical. Empirical S&P 500 estimates: 0.37/0.34/0.22; sample period 1990-2007 not 1990-2003
3. **Ch 6, Claim 16**: Monthly RV sum was 32.70, correct value is 33.70; monthly avg 1.532 not 1.486
4. **Ch 6, Claims 17-18**: Cascading arithmetic from claim 16: forecast 1.740 not 1.727, vol 1.32% not 1.31%
5. **Ch 4, Claim 16**: RQ formula conflated standard RQ ($n/3 \sum r^4$) with tripower quarticity. Fixed to standard formula with note about jump-robust alternative

### Known Issue

- `reference/project-papers/easley-lopezdeprado-ohara-2012-vpin.pdf` contains wrong paper (Sherlock et al., not VPIN). VPIN claims (26-28) unverified pending correct PDF.

## Tier 2: Model-critical -- VERIFIED

| Chapter | File | Claims | Verified | Errors | Status |
|---|---|---|---|---|---|
| Ch 3: Microstructure Noise | ch03-microstructure-noise.md | 74 | 72/74 | 2 | Verified |
| Ch 5: GARCH Family | ch05-garch-family.md | 62 | 59/62 | 2 | Verified |
| Ch 11: Tree Methods | ch11-tree-methods-vol.md | 62 | 62/62 | 5 | Verified |
| Ch 2: Realized Volatility | ch02-realized-volatility.md | 42 | 37/42 | 1 | Verified |
| Ch 12-R: Rashomon Trees | ch12r-rashomon-interpretable-trees.md | 87 | 79/87 | 1 | Verified |
| **Tier 2 subtotal** | | **327** | **309** | **11** | |

### Errors Fixed in Tier 2

6. **Ch 3, Claim 7-8**: Roll (1984) misattributed to Kyle (1985) for bid-ask autocovariance formula $\text{Cov}(\Delta p_t, \Delta p_{t+1}) = -s^2/4$
7. **Ch 3, Claim 52**: Arithmetic $23{,}400^{3/5} \approx 400$ corrected to $\approx 418$
8. **Ch 5, Claim (half-life)**: Mean lag $1/(1-0.98) = 50$ confused with half-life $\ln(0.5)/\ln(0.98) \approx 34$ days
9. **Ch 5, Claim (leverage)**: 3% loss "roughly doubles" news contribution corrected to "triples" ($0.000108/0.000036 = 3.0$)
10. **Ch 11, Claims (CSV2023)**: 5 corrections to CSV2023 characterization: feature set, horizons (added monthly), 5-15% QLIKE → 4-10% MSE, XGBoost → gradient-boosted trees, rolling-window → 70/10/20 split
11. **Ch 2, Claim 42**: BNS2002 misattributed for introducing BPV (actually BNS2004/2006); corrected to asymptotic theory for RV
12. **Ch 12-R, Claim 46**: RESPLIT lookahead depth was 3, Babbar et al. 2025 Section 7 specifies 2

## Tier 3: Context and enrichment

| Chapter | File | Claims | Verified | Errors | Status |
|---|---|---|---|---|---|
| Ch 8: Options & Vol Surface | ch08-options-vol-surface.md | 80 | 0 | 0 | Extracted |
| Ch 9: Variance Risk Premium | ch09-variance-risk-premium.md | 62 | 0 | 0 | Extracted |
| Ch 7: Rough Volatility | ch07-rough-volatility.md | 58 | 0 | 0 | Extracted |
| Ch 12-DL: Deep Learning | ch12-deep-learning-vol.md | 93 | 0 | 0 | Extracted |
| Ch 13: Hybrid/Ensemble | ch13-hybrid-ensemble.md | 47 | 0 | 0 | Extracted |
| Ch 14: Multivariate Volatility | ch14-multivariate-volatility.md | 71 | 0 | 0 | Extracted |
| Ch 15: Spillovers | ch15-spillovers-connectedness.md | 51 | 0 | 0 | Extracted |
| Ch 1: Returns/Variance | ch01-returns-variance-volatility.md | 53 | 0 | 0 | Extracted |
| Ch 17: Applications | ch17-applications-projects.md | 31 | 0 | 0 | Extracted |
| **Tier 3 subtotal** | | **546** | **0** | **0** | |

## Unique Citation Keys Referenced (51 papers)

ABD2007, ABDL2001, ABDL2003, AitSahaliaJacod2009, andersen1998, AudrinoKnaus2016, BabbarEtAl2025, baillie1996, BekaertHoerova2014, Black1973, Black1976, BNS2002, BNS2004, BNS2006, bollerslev1986, BollerslevEtAl2018, BollerslevTodorov2015, BPQ2016, Breiman1984, BrennerSubrahmanyam1988, BrittenJones2000, BTZ2009, Carr2009, CBOE2019, Cont2002, Corsi2009, CorsiPirinoReno2010, DongRudin2020, DonnellyEtAl2023, DrechslerYaron2011, Dupire1994, Engle1982, engle1986, GatheralJacquier2014, gjr1993, Gu2020, hansen2005forecast, hansen2012realized, HeileBabbar2025, HuangTauchen2005, LeeMykland2008, LPS2015, Lundberg2017, Mancini2009, Muller1993, nelson1991, PSS2015, Rebonato2004, shephard2010heavy, VanDenBosEtAl2024, XinEtAl2022

## Papers Available Locally (35)

See `reference/project-papers/` for PDFs. Key papers with local copies:
corsi-2009, bollerslev-patton-quaedvlieg-2016-harq, patton-sheppard-2015, gatheral-jaisson-rosenbaum-2018, cont-das-2024, moreno-pino-zohren-2022-deepvol, christensen-siggaard-veliyev-2023, donnelly-et-al-2023, xin-et-al-2022, vandenbos-et-al-2024, heile-babbar-2025, and others.

## Papers Still Needed

Many of the 51 cited papers are foundational (Engle 1982, Bollerslev 1986, Black-Scholes 1973, etc.) and may be verifiable via textbooks in `reference/books/`. Papers specifically needed for verification that are not yet local:
- ABDL2003 (Econometrica) -- paywalled
- BNHLS2008 (Econometrica) -- paywalled
- LPS2015 (J. Econometrics) -- paywalled
- HansenLundeNason2011 (Econometrica) -- paywalled
- BTZ2009 (RFS) -- paywalled
- Cont2001 (Quantitative Finance) -- cited heavily in Ch 1
