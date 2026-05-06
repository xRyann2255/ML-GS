# Design Spec: ML Realized Volatility Forecasting with Tradeable Signal Output

**Date:** 2026-05-06
**Author:** Ryan Vincent
**Status:** Active
**Primary reference:** Christensen, Siggaard & Veliyev (2023, *J. Financial Econometrics*)
**Chapter references:** All "Ch N" citations refer to the vol-learning-guide unless otherwise noted.
**Observation count:** ~2,800 daily obs per symbol (11.3 years x 252 trading days/year = 2,848).

---

## 1. Project Identity

**Title:** Layered Information and Realized Volatility: Where ML Adds Value Beyond HAR

**Thesis:** Progressively enriching HAR-family baselines with microstructure, options-implied, and cross-asset features via gradient boosting produces statistically significant QLIKE improvements that translate into a tradeable IV-RV gap signal with economic value.

**Audiences:**
- Academic: QLIKE tournament tables, MCS membership, DM significance tests, purged k-fold CV
- Trading desk: IV-RV gap signal with P&L backtest, vol-targeting Sharpe improvement, honest regime decomposition

**Final presentation at end of internship (~August/September 2026).** Everything builds toward a ~20-minute capstone presentation covering both the academic results and trading-desk relevance.

### 1.1 What This Extends

CSV (2023) used 29 DJIA stocks (2001-2017) with public data and showed tree-based models beat HAR when feature sets are rich and horizons are long. This project extends CSV with:

- GS-internal tick data for 34 symbols (30 mega-cap equities + 4 ETFs + E-mini), 11.3 years
- IV surface features from Marquee ERDVOL (CSV had no options-implied features)
- E-mini L2 microstructure features (CSV had no intraday LOB data)
- Cross-asset macro conditioning from Marquee (Treasury curve, FX, commodities)
- Economic value translation (vol targeting + straddle P&L) that CSV did not perform

This is not a direct replication -- the universe and time period differ. It is "in the spirit of CSV" with richer data and an economic-value dimension.

### 1.2 Paper Backing by Layer

| Layer | Features | Primary papers |
|---|---|---|
| 0. RV baselines | HAR, SHAR, HARQ, HAR-J, HAR-CJ | Corsi (2009), BPQ (2016), Patton-Sheppard (2015), Corsi-Pirino-Reno (2010) |
| 1. Index microstructure | OFI, depth ratio, signed volume (E-mini) | Cartea-Jaimungal-Penalva (2015) |
| 2. Options-implied | ATM IV, skew, term slope, VRP, VVIX | BTZ (2009), Bekaert-Hoerova (2014), Bollerslev-Todorov (2015), Fouhy (2024) |
| 3. Cross-asset | Treasury curve, FX/commodity vol, DY spillover | Diebold-Yilmaz (2012, 2014) |
| ML models | LightGBM with QLIKE loss, HAR+Tree ensemble | CSV (2023), Audrino-Knaus (2016), Rahimikia-Poon (2020) |
| Signal | IV-RV gap, vol targeting, straddle P&L | Moreira-Muir (2017), Carr-Wu (2009) |
| Evaluation | QLIKE, DM, MCS, DSR, purged CV | Patton (2011), Hansen-Lunde-Nason (2011), Bailey-LdP (2014), LdP (2018) |

### 1.3 Universe and Data

**Symbols:** 30 mega-cap equities + 4 ETFs + E-mini S&P 500 futures (34 total)
**History:** 11.3 years of daily OHLCV + tick-level RV
**Forecast horizons:** h = 1 day (primary), h = 5 days, h = 22 days

Note: E-mini is a futures contract with different microstructure, tick sizes, and trading hours than equities. ETFs also differ from single stocks. The panel study must account for this heterogeneity (see Section 2.2 on pooling).

**Data sources:**

| Data | Source | Frequency | Coverage |
|---|---|---|---|
| Tick-level prices | Chunk Store (L1) | Tick | 34 symbols, 11.3yr |
| E-mini order book | Chunk Store (L2) | Tick | E-mini only, ~4M ticks/day |
| OHLCV + returns | GS internal | Daily | 34 symbols + VIX + indices |
| SPX IV surface | Marquee ERDVOL_PERCENT_STANDARD | Daily | SPX, tenor x strike grid |
| VIX + 3m futures | GS internal | Daily | Full history |
| Treasury yields | GS internal / Marquee | Daily | 2y, 5y, 10y, 30y |
| Commodity futures | GS internal / Marquee | Daily | CL (crude), GC (gold) |
| Bond futures | GS internal / Marquee | Daily | TY (10y Treasury) |
| FX | Marquee | Daily | USD/JPY, EUR/USD |

---

## 2. Architecture

### 2.1 Package Structure

```
volforecast/
+-- config/                     # YAML experiment configs
|   +-- default.yaml            # base config (universe, dates, horizons)
|   +-- layer0_baselines.yaml
|   +-- layer1_micro.yaml
|   +-- layer2_implied.yaml
|   +-- layer3_crossasset.yaml
|   +-- signal.yaml              # signal generation + backtest params
|
+-- volforecast/                # importable library
|   +-- data/
|   |   +-- rv.py               # RV from ticks (5-min, bipower, kernel, quarticity)
|   |   +-- features.py         # feature registry + computation orchestrator
|   |   +-- loaders.py          # data source adapters (Marquee, Chunk Store, CSV)
|   |   +-- universe.py         # symbol lists, date ranges, train/test splits
|   |   +-- units.py            # annualization conventions (see Section 2.4)
|   |
|   +-- features/               # one module per feature layer
|   |   +-- base.py             # abstract FeatureLayer interface
|   |   +-- rv_features.py      # Layer 0: RV_d, RV_w, RV_m, RQ, signed RV, jumps
|   |   +-- micro_features.py   # Layer 1: E-mini index-level OFI, depth, signed vol
|   |   +-- implied_features.py # Layer 2: ATM IV, skew, term slope, VRP, VVIX
|   |   +-- cross_features.py   # Layer 3: Treasury curve, FX, commodity, DY spillover
|   |   +-- calendar.py         # FOMC, NFP, earnings, expiry dummies (Sprint 7+)
|   |
|   +-- models/
|   |   +-- base.py             # abstract VolModel interface
|   |   +-- har.py              # HAR, HAR-J, HAR-CJ, SHAR, HARQ
|   |   +-- garch.py            # GARCH(1,1), GJR-GARCH, Realized GARCH (Sprint 7+)
|   |   +-- trees.py            # LightGBM/XGBoost with custom QLIKE loss
|   |   +-- ensemble.py         # HAR+Tree blend, regime-switching ensemble
|   |   +-- lstm.py             # LSTM/GRU sequential baseline (optional, Sprint 7+)
|   |
|   +-- evaluation/
|   |   +-- losses.py           # QLIKE, MSE, Mincer-Zarnowitz
|   |   +-- tests.py            # Diebold-Mariano, Model Confidence Set
|   |   +-- cv.py               # purged k-fold CV with horizon-scaled purge
|   |   +-- economic.py         # vol-targeting Sharpe, DSR, straddle P&L
|   |
|   +-- signals/
|   |   +-- vrp.py              # IV-RV gap signal construction (3 variants)
|   |   +-- sizing.py           # vol-targeting position sizing
|   |   +-- backtest.py         # straddle P&L with daily gamma recomputation
|   |   +-- costs.py            # transaction cost modeling
|   |
|   +-- utils/
|       +-- plotting.py         # standardized figures
|       +-- logging.py          # experiment tracking, result serialization
|
+-- notebooks/                  # presentation story
|   +-- 01_data_and_rv.ipynb
|   +-- 02_baselines.ipynb
|   +-- 03_feature_layers.ipynb
|   +-- 04_model_tournament.ipynb
|   +-- 05_signal_and_pnl.ipynb
|   +-- 06_final_presentation.ipynb
|
+-- tests/                      # mirrors volforecast/ structure
|   +-- test_rv.py
|   +-- test_features.py
|   +-- test_models.py
|   +-- test_evaluation.py
|   +-- test_signals.py
|
+-- logs/
|   +-- progress.md             # daily progress log
|
+-- results/
    +-- tables/                 # QLIKE/MCS tables as CSV
    +-- figures/                # plots as PNG/PDF
```

### 2.2 Key Design Decisions

**Feature Layer Interface**

Every feature module implements:

```python
class FeatureLayer(ABC):
    name: str                           # "rv", "micro", "implied", "cross"
    requires: list[str]                 # data dependencies

    def compute(self, data: dict) -> pd.DataFrame:
        """Returns date x feature DataFrame, aligned to RV dates.
        All variance features in annualized decimal variance (see units.py).
        """

    def describe(self) -> dict[str, str]:
        """Returns {feature_name: paper_reference} for documentation."""
```

Adding a new layer (e.g. sentiment, alt data) means writing one module conforming to this interface and adding it to the config. The pipeline does not change.

**Model Interface**

```python
class VolModel(ABC):
    name: str

    def fit(self, X_train, y_train, X_val, y_val) -> None: ...
    def predict(self, X) -> np.ndarray: ...
    def feature_importance(self) -> pd.Series | None: ...
```

HAR models use `X = [RV_d, RV_w, RV_m]` and ignore other columns. Tree models use all columns. This makes "add a layer, re-run all models" comparisons trivial.

**Pooled vs Per-Symbol Training**

This is a first-class experimental variable, not a fixed choice:

- **HAR family:** per-symbol (low-parameter, 2,800 obs is sufficient)
- **Tree models:** pooled across all 34 symbols with symbol fixed effects (symbol dummies or symbol-level features like market cap, sector, average spread). This gives ~95,000 training observations vs 2,800 per-symbol. Sirignano-Cont (2019) showed pooling helps for neural nets; we test whether it helps for trees.
- **Comparison:** run per-symbol LightGBM alongside pooled LightGBM and report the difference. This is itself a result: "does cross-sectional pooling help for tree-based vol forecasting?"

The config specifies `training_mode: pooled | per_symbol | both`.

**E-mini as Market-Level Signal (Layer 1)**

E-mini L2 data produces index-level microstructure features (OFI, depth ratio, signed volume), not per-stock features. These enter the model as market-regime conditioning variables -- the same way VIX does. All 34 symbols receive the same E-mini features for a given date.

This is defensible: E-mini is the S&P 500 futures contract, so it captures market-level order flow dynamics that affect all large-caps. But the design is explicit: Layer 1 is "index microstructure," not "per-stock microstructure."

**Config-Driven Experiments**

```yaml
universe: [SPY, AAPL, MSFT, ...]
date_range: [2013-01-01, 2024-06-30]
horizons: [1, 5, 22]
feature_layers: [rv, micro, implied]
models: [har, harq, shar, lgbm_pooled, lgbm_persymbol]
training_mode: pooled
cv:
  method: purged_kfold
  n_splits: 5
  purge_days: auto         # auto = set to h for each horizon
  embargo_days: 25
```

Each experiment = one config + one pipeline call. Results serialized to `results/` as parquet + CSV. Configs are committed to git for full reproducibility.

### 2.3 Data Flow

```
Tick Data (Chunk Store)
    |
    v
rv.py --> Daily RV, BPV, RQ, Jumps per symbol --> parquet
    |
    v
features/ --> Layer 0-3 feature matrices (date x feature) --> parquet
    |
    v
models/ --> Forecasts y_hat_{t+h} per model/symbol/horizon --> parquet
    |
    |---> evaluation/ --> QLIKE, DM, MCS tables --> CSV + figures
    |
    \---> signals/ --> VRP signal --> backtest/ --> P&L tables --> CSV + figures
```

Each arrow is a saved intermediate artifact (parquet). If the tick pipeline takes hours, you run it once and everything downstream reads from parquet. No stage depends on upstream code at runtime -- only on the saved artifacts.

### 2.4 Unit Convention

All internal quantities in the package are **annualized decimal variance**.

| External format | Internal representation | Conversion |
|---|---|---|
| VIX = 18 (percentage vol) | 0.0324 (= (18/100)^2) | (VIX/100)^2 |
| Daily RV from 5-min returns | Multiply by 252 | RV_daily * 252 |
| ERDVOL IV = 20% at 30d tenor | 0.04 (= (20/100)^2) | (IV/100)^2 |

A single `units.py` module handles all conversions. Every function docstring states what units it expects and returns. Conversions happen at data loading boundaries and at final display -- never in the middle of a computation.

---

## 3. Evaluation Framework

### 3.1 Statistical Success (Academic)

**Primary metric:** QLIKE (Patton 2011)
```
QLIKE(sigma^2, h) = log(h) + sigma^2 / h
```
Proxy-robust. Penalizes underprediction more than overprediction -- the right asymmetry for risk.

**Targets:**
- h=1: 5-15% QLIKE improvement over HARQ (conservative; "HARd to Beat" 2024 suggests h=1 is the hardest horizon)
- h=5: 10-20% improvement (CSV 2023 found gains widen with horizon)
- h=22: 15-25% improvement (longest horizon, most room for rich features to help)

These are directional targets. If h=1 shows no improvement but h=5 and h=22 do, that confirms the CSV finding and is still a valid result.

**Significance testing:**
- **Diebold-Mariano test** at 5% with HAC (Newey-West) standard errors. Harvey-Leybourne-Newbold small-sample correction with t-distribution. Pairwise: each ML model vs HARQ baseline.
- **Model Confidence Set** (Hansen-Lunde-Nason 2011) at 10% elimination significance. Reports which models survive. Run both per-symbol (34 separate MCS, report survival frequency) and on pooled panel (one headline MCS table).
- **Mincer-Zarnowitz regression:** slope=1, intercept=0 under forecast efficiency. Diagnoses systematic bias.

**Final holdout test set:**
- Reserve the final 12 months of data as a held-out test set, locked before any modeling begins. No model sees this data during selection or tuning.
- Purged CV runs on the remaining ~10 years for hyperparameter tuning and model selection.
- All headline DM/MCS results reported on the holdout. CV results reported separately as "tuning performance."
- This follows the learning guide's evaluation workflow (Ch 16): "Step 1: Reserve holdout."

**Cross-validation (on non-holdout data):**
- Expanding-window purged CV, 5 folds. Folds are contiguous temporal blocks. For each test fold, only chronologically prior data (minus purge) is used for training. This is strictly more conservative than shuffled k-fold because it never trains on data after the test period. This addresses the "HARd to Beat" criticism that standard k-fold inflates results for time series.
- **Purge window = h days** (horizon-dependent, not fixed). At h=1: purge 1 day. At h=5: purge 5 days. At h=22: purge 22 days. This prevents label overlap leakage.
- Embargo = 25 days (fixed, captures serial correlation decay)
- **Data loss at h=22:** each fold boundary loses ~47 days (22 purge + 25 embargo). With 5 folds and ~2,500 obs per symbol (after holdout removal), total loss is ~188 obs (~7.5%). For pooled models (~85,000 obs), this is ~1.3%. Acceptable but reported. h=22 results will have wider confidence intervals.

**Secondary:** MSE (for comparability with older literature), R-squared from MZ regression.

### 3.2 Economic Success (Desk)

**Vol-targeting Sharpe:**
- w_t = sigma_target / sigma_hat_t (Moreira-Muir 2017)
- sigma_target = 10% annualized
- Compare: EWMA-targeted (baseline) vs HAR-targeted vs ML-targeted
- Target: +0.10-0.15 Sharpe over EWMA baseline
- Report: annualized return, annualized vol, Sharpe, max drawdown, Calmar ratio

**Straddle P&L:**
- Delta-hedged ATM straddle on SPX
- **Daily gamma recomputation** using Black-Scholes (not constant gamma approximation). The learning guide (Ch 9) explicitly warns that constant gamma breaks down when the underlying moves away from the strike. The backtest module computes Gamma_t from the Black-Scholes formula at each rebalance date.
- **Long-position P&L:** P&L_t = (1/2) * Gamma_t * S_t^2 * (sigma_realized_t^2 - sigma_implied^2) * dt
- **Sign convention:** the formula above gives long-position P&L. When Signal 1 > 0 (sell vol), the trade is a short straddle and the P&L is negated: P&L_short_t = -(1/2) * Gamma_t * S_t^2 * (sigma_realized_t^2 - sigma_implied^2) * dt. The `backtest.py` module takes a `direction` parameter (+1 long, -1 short) driven by the signal sign.
- Benchmark: always-short-vol (harvests VRP ~85% of months, Carr 2009)

**Transaction costs:**
- ERDVOL provides implied vols, not bid-ask spreads. Direct option bid-ask data may not be available.
- **Default approach:** conservative flat cost assumption of 0.5 vol points per ATM option leg (standard in VRP literature). Cost is applied per-leg at trade initiation (entry and exit). For a straddle (2 legs), total entry cost = 2 * 0.5 = 1.0 vol points, amortized over the holding period (22 trading days for Signal 1). Run sensitivity at 0.25, 0.5, and 1.0 vol points per leg to show break-even cost.
- If option tick data with bid/ask becomes available, substitute actual spreads.
- For delta-hedging costs: futures bid-ask spread for E-mini (typically <1 tick, negligible for daily rebalancing).
- All P&L reported net of costs. No result without costs.

**Multiple testing correction:**
- Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014)
- With ~20 model/signal variants tested, the null threshold is SR_0 = sqrt(2 * ln(20)) = 2.45
- Note: model variants are not fully independent (shared features, data, structure), so the effective number of tests is lower. Report both the raw DSR and a conservative version assuming all 20 are independent.

### 3.3 Honest Failure Modes

| Outcome | Interpretation | Deliverable |
|---|---|---|
| ML in same MCS as HARQ at h=1, wins at h=5/22 | CSV (2023) confirmed with GS data | Feature layer attribution at longer horizons |
| IV surface features don't improve QLIKE but improve signal P&L | Bekaert-Hoerova (2014) result: VRP matters for trading, not point forecasting | Separate "forecast value" vs "signal value" analysis |
| No layer beats HARQ on QLIKE at any horizon | "HARd to Beat" replicated with internal data | Report which layers came closest; decompose by regime |
| Signal has no economic value after costs | Break-even cost analysis | Report the cost threshold; lean on vol-targeting Sharpe instead |

---

## 4. Signal Specification

### 4.1 Three Signal Variants

**Signal 1: Raw VRP Gap (simplest, requires only VIX)**
```
S1_t = (VIX_t / 100)^2 - RV_forecast_{t,t+22}
```
Both terms in annualized decimal variance. Positive = options expensive, sell vol. Negative = options cheap, buy vol. Monthly horizon to match VIX tenor (30 calendar days ~ 22 trading days).

Paper: BTZ (2009). The improvement over BTZ is replacing their backward-looking RV with an ML forecast.

**Signal 2: Term-Structure-Aware Gap (requires ERDVOL surface)**
```
S2_t^(h) = IV_t^(h)^2 - RV_forecast_{t,t+h}    for h in {5, 22}
```
Computed at both forecast tenors using the ERDVOL tenor dimension. The term structure slope of the gap (5-day vs 22-day) captures whether the market prices a near-term event (steep short-dated gap) or structural shift (flat across tenors). Uses only h=5 and h=22, which align with the forecast horizons defined in Section 1.3.

Paper: Bekaert-Hoerova (2014) showed the VRP component at different horizons has different predictive content.

**Signal 3: Regime-Conditional Gap (richest)**
```
Position_t = (S2_t / vol(S2)) * w(regime_t)
```
Same gap as Signal 2, but position size modulated by regime. w(regime_t) scales down when forecast uncertainty is high. Regime indicators (all trailing to avoid lookahead):
- VVIX > trailing 252-day 80th percentile (1-year rolling window)
- VIX term structure in backwardation (front-month VIX > 3-month VIX futures)
- Model disagreement: |HAR_forecast - ML_forecast| / HAR_forecast > 0.3 (30% divergence threshold)

Paper: Rahimikia-Poon (2020) showed ML beats HAR 90% of days but fails in stress. Regime conditioning addresses exactly this.

### 4.2 Signal-to-Trade Mapping

| Signal state | Trade | P&L driver |
|---|---|---|
| S1 > 0 (options expensive) | Sell ATM straddle, delta-hedge daily | Gamma P&L from IV > RV |
| S1 < 0 (options cheap) | Buy ATM straddle, delta-hedge daily | Gamma P&L from RV > IV |
| S2 term slope steep | Calendar spread (sell short, buy long) | Differential realization across tenors |
| S3 regime = high uncertainty | Reduce position size or flatten | Avoided drawdown |

### 4.3 Backtest Structure

1. **Primary:** Signal 1 on SPX, long/short straddle, daily delta-hedge with daily gamma recomputation, net of costs (0.5 vol point default). Benchmark: always-short-vol.
2. **Vol-targeting:** RV forecast for position sizing on long-SPX. Benchmark: EWMA-targeted. Tests forecast quality independent of the signal.
3. **Signal 3 robustness:** does regime conditioning improve Sharpe vs Signal 1? Does it reduce max drawdown?

**Headline deliverable table:**

| Strategy | Ann. Return | Ann. Vol | Sharpe | Max DD | Calmar | DSR |
|---|---|---|---|---|---|---|
| Buy & hold SPX | ... | ... | ... | ... | ... | -- |
| EWMA vol-target | ... | ... | ... | ... | ... | -- |
| ML vol-target | ... | ... | ... | ... | ... | ... |
| Always short vol | ... | ... | ... | ... | ... | -- |
| Signal 1 (raw gap) | ... | ... | ... | ... | ... | ... |
| Signal 3 (regime) | ... | ... | ... | ... | ... | ... |

### 4.4 Modularity

Signal 1 needs only the forecast + VIX. Signal 2 needs the ERDVOL surface. Signal 3 needs regime indicators. Each is a separate function in `signals/vrp.py`. If a future user only has VIX access, they use Signal 1. If they get ERDVOL, they upgrade.

---

## 5. Timeline and Phasing

### 5.1 Sprint Structure

Two-week sprints. Each produces a standalone deliverable. You can stop at any sprint boundary and have something presentable.

**Sprint 1 -- Data Pipeline (Weeks 3-4, now through ~May 19)**

Split into two explicit milestones due to tick-processing risk:

- **Week 3:** Data pipeline only. RV, BPV, RQ, jumps computed from tick data and saved to parquet for all 34 symbols. Cross-validate against a known source if any symbols overlap with Oxford-Man RV library. Also: verify package availability (LightGBM, SHAP, etc.) on GS machines. Set up `volforecast/` package skeleton, progress-log skill, and hooks.
- **Week 4:** HAR, SHAR, HARQ baselines implemented. QLIKE/MSE evaluation on simple 70/30 train/test split. First results table.
- **Deliverable:** baseline QLIKE table across 34 symbols at h=1, 5, 22. Parquet pipeline verified.
- **If week 3 overruns:** baselines slip to week 5; Sprint 2 absorbs the delay.

**Sprint 2 -- First ML Comparison (Weeks 5-6)**

- Layer 0 feature set: RV_d, RV_w, RV_m, RQ, signed semivariances, jumps, log transforms, ratios
- LightGBM with custom QLIKE loss (gradient: -RV/y_hat^2 + 1/y_hat, hessian: 2*RV/y_hat^3 - 1/y_hat^2). Constrained hyperparameters per Ch 11: max_depth 3-5, min_child_samples 50-200, learning_rate 0.01-0.05, early stopping.
- First DM test: does LightGBM beat HARQ?
- Test pooled vs per-symbol training. Report both.
- **Deliverable:** first ML vs HAR comparison with DM significance. Pooled vs per-symbol result.

**Sprint 3 -- Feature Layers (Weeks 7-8)**

- Layer 1: E-mini index microstructure features (OFI, depth ratio, signed volume)
- Layer 2: IV surface features from ERDVOL (ATM IV, 25-delta skew, term slope, VRP proxy, VVIX)
- Marginal QLIKE contribution from each layer (run models with Layer 0 only, then 0+1, then 0+2, then 0+1+2)
- **Deliverable:** feature layer value attribution table. "Layer X adds Y% QLIKE at horizon h."

**Sprint 4 -- Full Evaluation (Weeks 9-10)**

- Layer 3: cross-asset signals (Treasury curve, FX/commodity vol, DY spillover index). DY spillover computed via VAR(1) on daily RV of 34 symbols with 200-day rolling window, generalized FEVD at H=10 step horizon (Diebold-Yilmaz 2012). Extract: total spillover index, directional FROM for each symbol, and 5-day change.
- Full MCS across all models and feature combinations
- Replace simple train/test with purged k-fold CV (horizon-scaled purge)
- SHAP/ALE interpretability on best-performing model (Ch 10 importance stability protocol)
- **Deliverable:** MCS membership table (the academic headline), SHAP feature importance, per-symbol vs pooled MCS comparison

**Sprint 5 -- Economic Value (Weeks 11-12)**

- Signal 1 (raw VRP gap) construction and straddle backtest with daily gamma recomputation
- Vol-targeting backtest (EWMA vs HAR vs ML)
- Transaction cost sensitivity (0.25, 0.5, 1.0 vol points)
- **Deliverable:** P&L table (the desk headline), cost sensitivity analysis

**Sprint 6 -- Signal Refinement (Weeks 13-14)**

- Signal 2 (term-structure-aware) and Signal 3 (regime-conditional)
- Compare all three signal variants
- Regime decomposition: when does the signal work, when does it fail?
- **Deliverable:** full signal comparison table, regime analysis

**Sprints 7-10 (Weeks 15-20) -- Deliberately Unplanned**

By week 14 you know which layers and signals work. Options for the remaining time:

- Double down on the strongest result (deeper analysis, more symbols, robustness checks)
- Add LSTM sequential baseline (Ch 12, Bucci 2020, Rosenbaum-Zhang 2022)
- Extend to multivariate forecasting (Ch 14, Graph-HAR from Zhang-Pu-Cucuringu-Dong 2024)
- HAR+Tree ensemble with regime switching (Ch 13, Rahimikia-Poon 2020)
- SHAP/ALE deep dive and interpretability paper (Ch 10, CSV 2023)
- Polish presentation notebooks and final presentation
- Write up results as a research note

### 5.2 Pivot Points

- **After Sprint 2:** if LightGBM does not beat HARQ, investigate before adding features. Is it overfitting (check train vs validation QLIKE)? Wrong hyperparameters? Or genuinely HARd to Beat? If the latter, the project narrative shifts to "confirming the literature with GS data + economic value test."
- **After Sprint 4:** if no feature layer adds statistically significant QLIKE improvement at any horizon, pivot to "honest replication of HARd to Beat with internal data." Document which layers came closest and decompose by regime/symbol.
- **After Sprint 5:** if the signal has no economic value after costs, the project becomes purely academic (QLIKE tables) and the presentation narrative pivots accordingly. The vol-targeting result (which only needs a good forecast, not a signal) may still hold.

---

## 6. Documentation System

### 6.1 Daily Progress Log

A single markdown file (`logs/progress.md`), reverse-chronological. Each entry:

```markdown
## 2026-05-06

**Sprint:** 1 -- Data Pipeline
**Focus:** [what was worked on]

- [bullet points of what was done, linking to commits/files]
- [decisions made and why]
- [blockers or open questions]

**Next:** [what's planned for tomorrow]
```

For the first two weeks (before this system existed), entries are backfilled from git history and conversation records to maintain a continuous record from internship day one.

### 6.2 Auto-Updating Hooks

Two hooks with deduplication:

**Post-commit hook:** fires after every `git commit`. Invokes the `progress-log` skill to append a granular bullet to today's entry based on the commit diff. Small commits (typo fixes, formatting) get one-line entries. Meaningful commits get fuller entries.

**Post-session hook:** fires when a Claude Code session ends. Invokes the `progress-log` skill to consolidate today's granular bullets into a clean daily summary. Deduplicates with existing entries by checking today's date in the log.

The `progress-log` skill:
- Reads current `logs/progress.md`
- Determines whether to append (post-commit) or consolidate (post-session)
- Writes the updated log
- Keeps entries concise: 3-5 bullets per day for granular, 1-2 paragraph summary for consolidated

### 6.3 Presentation Notebooks

Written at sprint boundaries, not daily. Each notebook:
- Imports from `volforecast/` -- no raw computation in the notebook itself
- Tells the narrative: question, data, result, why it matters
- Produces publication-quality figures saved to `results/figures/`
- Has markdown cells explaining methodology for a reader who has not seen the code

**Notebook sequence:**

| Notebook | Sprint | Content |
|---|---|---|
| 01_data_and_rv.ipynb | 1 | Universe, RV computation, data quality checks |
| 02_baselines.ipynb | 1-2 | HAR family results, first ML comparison |
| 03_feature_layers.ipynb | 3-4 | Layer-by-layer QLIKE attribution, SHAP |
| 04_model_tournament.ipynb | 4 | Full MCS table, per-symbol analysis |
| 05_signal_and_pnl.ipynb | 5-6 | Signal construction, P&L backtest, cost sensitivity |
| 06_final_presentation.ipynb | 7-10 | Stitches key results into ~20 min capstone arc |

### 6.4 What Gets Committed When

- `logs/progress.md`: updated same-day, committed alongside related code changes
- `results/`: tables and figures committed alongside the notebook that produced them
- Notebooks: committed at sprint boundaries when results are stable
- Configs: committed whenever a new experiment is defined

---

## 7. Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Pivot |
|---|---|---|---|---|---|
| 1 | **HAR unbeatable at h=1** | High | Medium | Focus on h=5, h=22 where CSV (2023) showed gains widen. Report h=1 honestly. | If all horizons fail, "replication with GS data" narrative |
| 2 | **ERDVOL access breaks** | Low-Med | High | Build Signal 1 (VIX-only) first. Layer 2 is additive, not load-bearing. | VIX-only VRP proxy (BTZ 2009 style) |
| 3 | **LightGBM overfits** | Medium | High | Purged CV with embargo. Constrained hyperparams (Ch 11). Early stopping on purged validation. | HAR+Tree ensemble (Ch 13) where HAR anchors prediction |
| 4 | **E-mini features don't help equities** | Medium | Low | They're market-level signals, not per-stock. If no transfer, document and drop Layer 1. | 3-layer project. Negative result reported honestly. |
| 5 | **VRP signal no value after costs** | Medium | High | Break-even cost analysis. Vol-targeting works independently of signal. | Lean on vol-targeting Sharpe as economic value story |
| 6 | **Tick pipeline takes >2 weeks** | High | High | Sprint 1 split into pipeline (wk 3) + baselines (wk 4). Buffer in Sprints 7-10. Save parquet intermediates. | Fall back to pre-computed daily RV from internal GS dataset if available |
| 7 | **GS environment package constraints** | Medium | High | Verify LightGBM, SHAP, PyTorch availability in week 3. | scikit-learn GradientBoostingRegressor as fallback (slower, fewer features, always available) |
| 8 | **Presentation doesn't come together** | Low | Very High | Daily log + sprint notebooks = raw material always exists. Budget entire last sprint for polish. | Start final notebook skeleton at Sprint 4 (week 10) |
| 9 | **Compliance review delays** | Low-Med | Medium | Factor 1-2 weeks for compliance review of final presentation. Internal-only results may have lighter review. | Submit for review at Sprint 6 (week 14), leaving buffer |

**Meta-mitigation:** every sprint produces a standalone deliverable:

| If project stops after... | You have |
|---|---|
| Sprint 1 (week 4) | Baseline QLIKE table for 34 symbols, validated RV pipeline |
| Sprint 2 (week 6) | ML vs HAR comparison with DM significance, pooled vs per-symbol |
| Sprint 3 (week 8) | Feature layer attribution (which data source adds value) |
| Sprint 4 (week 10) | Full MCS membership table, SHAP interpretability -- complete academic result |
| Sprint 5 (week 12) | P&L backtest, vol-targeting Sharpe -- complete desk result |
| Sprint 6 (week 14) | Signal comparison, regime analysis -- full project |

---

## 8. Out of Scope

- Individual equity IV surfaces (only SPX available via ERDVOL)
- Real-time / streaming implementation (this is a research project, not production)
- Neural SDE / rough vol calibration (interesting but doesn't fit the layered-feature thesis)
- Sentiment / NLP features (no data source identified; could be a Sprint 7+ extension)
- Multi-asset signal portfolio (signal is SPX-only due to IV surface constraint)
