# HAR Components

What we've learned hands-on about the daily/weekly/monthly RV decomposition.

## Findings

(To be filled as we explore data)

## Questions to Answer

- Does the 1/5/22-day split actually match the autocorrelation structure of our data?
- Which component (daily, weekly, monthly) carries the most predictive weight for each asset?
- How stable are HAR coefficients over time? Do they shift during regimes?

## Deep Research Findings (2026-05-06)

**Realized higher moments as predictors:**
- Amaya, Christoffersen, Jacobs & Vasquez (2015, JFE): realized skewness and realized kurtosis have predictive power for future RV beyond the standard HAR components (`amaya-christoffersen-jacobs-etal-2015` in bibliography)
- Signed jump variation J = RS+ - RS- provides a directional decomposition of jump activity

**Long memory and fractional differencing:**
- Lopez de Prado (AFML Ch. 5): fractional differencing of RV series preserves long memory while ensuring stationarity -- important preprocessing step for ML models that assume stationarity (`lopez-de-prado-2018` in bibliography)
- Long memory is the core mechanism HAR exploits; ML models that approximate long memory well (gradient boosting, deep nets with dilated convolutions) show the largest gains at longer horizons

**ML horizon findings (Section C6 honest verdict):**
- Daily: HARQ + signed semivariances is very hard to beat by more than a few percent QLIKE
- Weekly/monthly: ML models with long memory start to show meaningful gains per Christensen-Siggaard-Veliyev 2023 (`christensen-siggaard-veliyev-2023` in bibliography)
- Intraday (10-30 min): ML + LOB features can produce real gains; this is the Optiver-Kaggle / DeepLOB regime

## Deep Research Findings (2026-05-07)

**Accuracy comparison: optimal trees vs HAR vs ensembles (decision tree research):**
- Christensen, Siggaard & Veliyev (Journal of Financial Econometrics 2023; T=4,257 trading days, 29 Jan 2001 to 31 Dec 2017, 29 DJIA constituents): relative MSE vs HAR=1.000 baseline -- bagging 0.891, gradient boosting 0.958, RF 0.986, NN ensembles 0.954-0.990. With full features (IV, EA, VIX, HSI): RF 0.901, GB 0.962, NN 0.885-0.944, bagging 0.961 (`christensen-siggaard-veliyev-2023` in bibliography)
- Best estimate for interpretable optimal trees: depth-4-5 STreeD piecewise-linear should achieve ~2-5% higher MSE than a tuned LightGBM, while remaining a single inspectable tree with 8-32 leaves (extrapolated -- not yet measured, must verify on own data)
- An interpretable optimal tree should comfortably beat HAR: bagging alone beats HAR by ~10% on 5-min RV
- Van der Linden et al. 2025 (180 datasets): optimal trees ~1-2 percentage points accuracy improvement vs greedy CART at depth 3-4 (`van-der-linden-etal-2025-benchmark` in bibliography)
