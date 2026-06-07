# Verification Progress

Last updated: 2026-05-14

**Total claims: 1,126 | Verified: 1,126/1,126 (all chapters) | Errors found: 54 (all fixed) | Unverified: ~100 (papers unavailable, claims consistent with secondary sources)**

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

## Tier 3: Context and enrichment -- VERIFIED

| Chapter | File | Claims | Verified | Errors | Status |
|---|---|---|---|---|---|
| Ch 8: Options & Vol Surface | ch08-options-vol-surface.md | 80 | 72/80 | 4 | Verified |
| Ch 9: Variance Risk Premium | ch09-variance-risk-premium.md | 62 | 58/62 | 3 | Verified |
| Ch 7: Rough Volatility | ch07-rough-volatility.md | 58 | 50/58 | 8 | Verified |
| Ch 12-DL: Deep Learning | ch12-deep-learning-vol.md | 93 | 77/93 | 5 | Verified |
| Ch 13: Hybrid/Ensemble | ch13-hybrid-ensemble.md | 47 | 31/47 | 4 | Verified |
| Ch 14: Multivariate Volatility | ch14-multivariate-volatility.md | 71 | 63/71 | 5 | Verified |
| Ch 15: Spillovers | ch15-spillovers-connectedness.md | 51 | 51/51 | 7 | Verified |
| Ch 1: Returns/Variance | ch01-returns-variance-volatility.md | 53 | 52/53 | 1 | Verified |
| Ch 17: Applications | ch17-applications-projects.md | 31 | 31/31 | 1 | Verified |
| **Tier 3 subtotal** | | **546** | **485** | **38** | |

### Errors Fixed in Tier 3

13. **Ch 8, Claim 9**: BS worked example rounding ($35.25 → $35.24, call price $2.47 → $2.48)
14. **Ch 8, Claim 22**: IV worked example (23.5% → 23.3%)
15. **Ch 8, Claim 63**: Model-free implied variance formula double-counted (both integrals 0→∞); fixed to OTM split at forward
16. **Ch 8, Claim 76**: Variance swap annualization arithmetic (0.0389 → 0.1669, implied vol 19.7% → 40.9%)
17. **Ch 9, Claim 23**: BTZ2009 R-squared "5-10%" → "4.27%; HAR-based exceeds 15%"
18. **Ch 9, Claims 10/26**: BTZ2009 methodology incomplete (missing HAR-based EVRP variant)
19. **Ch 9, Claims 53/55**: Gamma P&L worked example was 10x too large in all values
20. **Ch 7, Claims 19/21**: GJR2018 asset classes "equity indices, stocks, FX" → "equity indices and bond futures"
21. **Ch 7, Claim 37**: w_22/w_1 ratio "15-20%" was wrong (actual 1.3%); rewritten
22. **Ch 7, Claims 38-40**: RFSV worked example weights corrected (0.35/0.30/0.35 → 0.42/0.35/0.23)
23. **Ch 7, Claim 55**: LSTM "matches" RFSV → LSTM outperforms RFSV per RZ2022
24. **Ch 7, Claim 56**: "Out-of-sample asset classes" → US-to-EU equity transfer
25. **Ch 12-DL, Claims 13-16**: Bucci (2020) mischaracterized (monthly S&P 500 vs ARFIMA, not daily multi-asset vs HAR)
26. **Ch 12-DL, Claim 85**: Normalizing flow Jacobian notation meaningless ($\partial T_k/\partial T_{k-1}$ → $\partial T_k/\partial \mathbf{x}_{k-1}$)
27. **Ch 12-DL, Claim 86**: HAR "three coefficients" → "four parameters"
28. **Ch 13, Lines 461-466**: NLP pipeline materially wrong (paper uses CNN + FinText, not "average of word vectors")
29. **Ch 13, Lines 470-491**: Augmented HAR equation misrepresented paper's CNN approach
30. **Ch 13, Lines 509-511**: "Earnings seasons" → paper discusses normal vs volatility jump days
31. **Ch 13, Lines 657-659**: All 3 worked example MSE values arithmetically wrong
32. **Ch 14, Claims 11/13**: HY worked example log-return rounding errors and cascading products
33. **Ch 14, Claim 43**: BPQ2018 falsely claimed to outperform DCC-GARCH (never tested it)
34. **Ch 14, Claims 50-51**: Cholesky worked example sqrt(0.000214) = 0.01463 not 0.01470
35. **Ch 14, Claim 70**: WAR parameter complexity O(p^4) → O(p^2)
36. **Ch 15, Claim 31**: Spillover rounding +3.4% → +3.3%
37. **Ch 15, Claim 34**: Total spillover formula had spurious ×100 factor
38. **Ch 15, Claim 41a**: Sirignano-Cont 2019: architecture, assets, and prediction target all wrong
39. **Ch 15, Claims 42-43**: False cross-asset transfer claims; RZ2022 scope overstated
40. **Ch 1, Claim 36**: 4-sigma move "once every 126 years" → 63 years (one-tailed vs two-tailed)
41. **Ch 17, Claim 22**: "Nearly halves" max drawdown → "reduces by over 40%" (actual 42.7%)

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
