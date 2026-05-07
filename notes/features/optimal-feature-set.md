# The Absolute Best Feature Set for Realized Volatility Forecasting

*Synthesized from: vol learning guide chapters, 19 project papers, research journal, feature notes, Optiver competition evidence, and broader literature. Assumes unlimited GS internal data access.*

---

## Layer 0: The Non-Negotiable Core (HAR + Measurement Quality)

These features alone explain 40-60% of next-day log-RV variation. Everything else is marginal improvement on top of this foundation.

| Feature | Formula | Why It Matters | Source |
|---------|---------|----------------|--------|
| log RV daily | log(RV_t) | Strongest single predictor; log transform gaussianizes | Corsi 2009 |
| log RV weekly | log(1/5 * sum RV_{t-i}, i=0..4) | Medium-memory component | Corsi 2009 |
| log RV monthly | log(1/22 * sum RV_{t-i}, i=0..21) | Long-memory, regime anchor | Corsi 2009 |
| Realized Quarticity | RQ_t = (n/3) * sum r_{t,i}^4 | Measures *how noisy* today's RV estimate is | BPQ 2016 |
| RQ interaction | sqrt(RQ_t) * RV_t^(d) | Shrinks daily weight on noisy days; **single most impactful HAR extension** (5-15% QLIKE gain) | BPQ 2016 |

**Why this is non-negotiable:** HARQ with 5 features consistently beats ML models that use dozens of features without this noise-awareness mechanism. The vol learning guide calls RQ "the single most important extension beyond baseline HAR." The mechanism is elegant: on days where RV is estimated with high noise (large RQ), the model automatically trusts the weekly/monthly averages more.

**GS advantage:** Tick-level data for 34 symbols lets you compute RQ precisely. Public data often only provides 5-min returns, making RQ noisy itself.

---

## Layer 1: Asymmetric Volatility (Leverage + Signed Jumps)

The leverage effect -- negative returns increase future vol more than positive returns -- is one of the most robust empirical facts in finance. The vol learning guide documents 3-8% QLIKE improvement from this layer alone.

| Feature | Formula | Why | Source |
|---------|---------|-----|--------|
| Negative semivariance (daily) | RS_t^- = sum r_{t,i}^2 * 1(r_{t,i} < 0) | Carries **2x the predictive weight** of RS+ | Patton-Sheppard 2015 |
| Positive semivariance (daily) | RS_t^+ = sum r_{t,i}^2 * 1(r_{t,i} > 0) | Much weaker but provides contrast | Patton-Sheppard 2015 |
| Negative semivariance (weekly) | (1/5) * sum RS_{t-i}^-, i=0..4 | Persistent downside memory | SHAR |
| Signed negative jumps | J_t^- = sum r_{t,i}^2 * 1(r_{t,i} < 0, abs(r_{t,i}) > theta_t) | Large downside moves predict vol increases by 1-3% QLIKE beyond unsigned jumps | ABD 2007 |
| Continuous variation | C_t = max(BPV_t, 0) where BPV_t = (pi/2) * sum abs(r_{t,i}) * abs(r_{t,i-1}) | Highly persistent (ACF ~0.6-0.7), drives forecasts | BNS 2004 |
| Jump variation | J_t = max(RV_t - BPV_t, 0) | Nearly unpredictable (ACF ~0.0-0.1) but signals regime breaks | BNS 2004 |

**Key insight from the vol learning guide:** The asymmetry is strongest for equity indices (where the leverage effect is most pronounced). For individual stocks, the effect varies by sector -- financials show it more than tech. Since we have 30 mega-caps + E-mini, expect strong asymmetry signal on the index and moderate on names.

**GS advantage:** Tick-level data lets you compute semivariances and jumps at optimal frequency (5-min for RV, variable for jumps via Lee-Mykland test), rather than being stuck with daily OHLC proxies.

---

## Layer 2: Options-Implied Features (Forward-Looking Information)

The vol learning guide calls this "the only family that reflects the market's consensus about the future" and documents **5-10% QLIKE improvement at horizons beyond 1 day**. This is the layer where GS data gives the biggest edge over academic research.

| Feature | Construction | Why | Horizon Impact |
|---------|-------------|-----|----------------|
| ATM IV (30-day) | SPX 50-delta put/call avg from Marquee ERDVOL | "Often the strongest single univariate predictor of future RV" (Gu 2020) | All horizons |
| Variance Risk Premium | VRP_t = IV_t^2 - E[RV_{t to t+30}] | Mean-reverts when abnormally high; **5-10% QLIKE at weekly-monthly** | 1w-1m (strongest) |
| 25-delta Risk Reversal | RR_25 = IV_{25D call} - IV_{25D put} | Sudden steepening predicts vol spikes **before ATM IV moves** | 1-5 days |
| Term Structure Slope | IV^{3m} - IV^{1m} | Inversion = near-term panic; upward slope = calm expectation | 1w-1m |
| Butterfly (Wing Premium) | IV_{25D put} + IV_{25D call} - 2*ATM IV | Prices tail risk separately from directional skew | Crisis detection |
| VVIX | Implied vol of VIX options | Uncertainty about uncertainty; high VVIX predicts fatter tails | 1-5 days |
| VIX Term Structure | VIX Futures_{3m} / VIX Spot | Contango = calm, backwardation = panic; regime indicator | Regime signal |
| IV-RV Gap | ATM IV - sqrt(RV_{last 22d} * 252) | Large gap = market pricing something RV hasn't shown yet | 1-5 days |
| Event-Implied Vol | sigma_event = sqrt((T2*sigma2^2 - T1*sigma1^2)/(T2 - T1)) | Isolates event-specific uncertainty from background vol | Pre-event |

**Critical nuance from the research:** At the 1-day horizon, options features add only 1-3% QLIKE. Their power explodes at weekly-to-monthly horizons (5-10%) because options embed information about future events (earnings, FOMC, macro releases) that past RV cannot see.

**GS advantage:** Full SPX vol surface history from Marquee ERDVOL_PERCENT_STANDARD. You can compute *any* surface-derived feature (arbitrary delta, tenor interpolation, surface curvature metrics). Academic papers typically only have VIX (model-free 30-day) -- you have the entire surface.

**What's missing:** Individual equity IV surfaces are not available (SPX only). For single-stock vol forecasting, you can't use stock-specific options features -- only the index-level surface as a market-wide regime signal.

---

## Layer 3: Microstructure Features (E-mini L2 Exclusive)

This is where having 4M ticks/day of E-mini L2 depth data puts you in Optiver-competition territory. The vol learning guide and the competition evidence converge: these features matter most at short horizons (intraday to 1-day).

| Feature | Construction | Why | Evidence |
|---------|-------------|-----|----------|
| **Price acceleration** | sum (D log P_{t,i} - D log P_{t,i-1})^2 | **Single most predictive micro feature** across top Optiver solutions | Optiver 2021 |
| WAP log returns | Returns computed from volume-weighted avg price | Less contaminated by bid-ask bounce than mid-price | Optiver 2021 |
| Order Book Imbalance (OBI) | (bid_size - ask_size)/(bid_size + ask_size) at L1-L5 | Directional pressure; extreme imbalance = one-sided flow | Cartea-Jaimungal-Penalva |
| Depth Ratio | sum(bid depths) / sum(ask depths) at multiple levels | Structural imbalance beyond best quote | L2 specific |
| Market Urgency | spread * OBI | Composite: wide spread + imbalanced book = imminent move | Optiver 91st place |
| Bid-Ask Spread dynamics | Level, volatility, and momentum of spread | Wider spread -> higher near-term vol; spread *increasing* is predictive | Vol guide Ch. 3 |
| Signed volume flow | sum volume_i * sign(trade direction) | Net buying/selling pressure at tick level | Lee-Ready classification |
| Sub-window RV ratio | RV_{last 5min} / RV_{first 5min} of session | Acceleration within window beats whole-window RV | Optiver top solutions |
| VPIN | Volume-synchronized prob of informed trading | Leading indicator of flash crashes, vol spikes | Easley-Lopez de Prado-O'Hara |

**Engineering principle from Optiver competition meta-analysis:** For each base quantity, compute {level, change, z-score} systematically. This triples feature count. Trees handle the redundancy naturally via splits -- you don't need to worry about multicollinearity.

**GS advantage:** L2 depth for E-mini (not just L1 quotes). Most academic work uses L1 mid-price only. Depth imbalance at levels 2-5 provides lead time that L1 misses.

**Constraint:** L2 depth is E-mini ONLY. For the 30 equities + 4 ETFs, you have L1 tick data -- enough for price acceleration, WAP returns, and spread dynamics, but not depth-based features.

---

## Layer 4: Cross-Asset Spillovers & Macro Regime

Volatility is contagious. The vol learning guide documents 1-5% QLIKE improvement from cross-asset features, concentrated in regime transitions (where they matter most -- exactly when forecasts are most valuable).

| Feature | Construction | Why | Source |
|---------|-------------|-----|--------|
| Treasury slope change | D(10y - 2y) yield | Rate curve inversion precedes equity vol spikes by days | Cross-asset notes |
| Credit spread momentum | D IG/HY spread (if available) or TY futures vol | Credit stress leads equity vol | Diebold-Yilmaz |
| FX vol (USD/JPY) | RV of USD/JPY | Yen carry unwind = global risk-off = equity vol spike | Data inventory |
| Commodity vol (CL, GC) | RV of crude + gold | Oil vol -> macro uncertainty; gold vol -> flight-to-safety intensity | Data inventory |
| DY Spillover Index | VAR(5) on 34-asset RV panel -> variance decomposition | Fraction of vol driven by cross-asset contagion (spikes in crises) | Diebold-Yilmaz 2012/2014 |
| Sector-mean RV | Average RV across same-sector names | Sector co-movement filters idiosyncratic noise | Graph-HAR (vol guide Ch. 14) |
| VIX-equity corr regime | Rolling 20-day corr(VIX changes, SPX returns) | Near -1 in normal markets; breaks during regime shifts | Empirical |
| Cross-asset RV rank | Where each asset's RV sits relative to its peers today | Detects outlier dispersion regimes | Panel structure |

**Key mechanism from the vol guide (Ch. 14):** Graph-HAR adds a neighbor-weighted RV term: gamma * sum W_{jk} * RV_{k,t}. This captures how AAPL's vol tomorrow depends partly on MSFT's vol today. The weight matrix W can be learned (GNN) or fixed (correlation-based).

**GS advantage:** Synchronized tick data across 34 symbols + treasuries + FX + commodities. Academic papers typically use daily closes. Intraday lead-lag relationships (e.g., E-mini leading individual stocks by seconds) are invisible at daily frequency but very real.

---

## Layer 5: Calendar & Event Structure

Individually weak but collectively additive. The vol guide calls these "incremental" but notes that tree models pick them up naturally.

| Feature | Construction | Why |
|---------|-------------|-----|
| FOMC indicator | {-1, 0, +1, +2} days relative to announcement | Vol compression before, expansion after |
| NFP/CPI indicator | Same relative-day encoding | Macro release effect |
| Options expiry | Monthly/quarterly OpEx flag | Pinning + gamma unwind |
| Quarter-end rebalancing | Last 3 days of quarter | Forced rebalancing flows |
| Earnings proximity | Days to next earnings for single names | Vol run-up is mechanical |
| Event-implied vol | Surface-derived sigma_event for dated events | More informative than binary dummies |
| Intraday time-of-day | Session fraction (0-1) | U-shape pattern; open and close are highest vol |
| Day-of-week | One-hot Mon-Fri | Weakening over time but still detectable |

**Important caveat:** These features matter for *single-stock* vol (earnings are huge) more than index vol. For E-mini, FOMC and NFP dominate; earnings don't directly apply.

---

## Layer 6: Long-Memory & Roughness Features

These capture the fractal/long-memory nature of volatility that HAR approximates but doesn't fully exploit.

| Feature | Construction | Why | Source |
|---------|-------------|-----|--------|
| Fractionally differenced RV | (1-L)^d RV_t with d ~ 0.35-0.45 | Preserves long memory while achieving stationarity; optimal for NNs | Lopez de Prado 2018 |
| Rolling Hurst exponent | Rescaled range or DFA on 60-day window | Low H < 0.15 = rough/fast mean-reversion; high H > 0.3 = trending | Gatheral-Jaisson-Rosenbaum 2018 |
| Vol-of-vol | std(RV_{t-22:t}) | Measures instability of the vol process itself | Empirical |
| RV regime duration | Days since last 2-sigma RV spike | Mean-reversion clock; models "how long has it been calm?" | Practical |

**The roughness debate (from project papers):** Gatheral-Jaisson-Rosenbaum (2018) found universal H ~ 0.1 across assets. But Cont-Das (2024) argues this is partly a microstructure noise artifact. The practical implication: use Hurst as a *feature* (let the model decide if it's informative) rather than hard-coding a rough-vol model structure.

---

## Layer 7: Sentiment & Alternative Data (If Accessible)

The vol guide rates this as "nice to have" -- 1-3% QLIKE improvement concentrated in crisis periods. Only include if the data pipeline effort is justified.

| Feature | Source | Improvement |
|---------|--------|-------------|
| News sentiment (FinBERT) | GS news feeds or third-party NLP | 1-3% QLIKE in crises (Audrino 2020) |
| Negative news count | Daily negative-sentiment article count | Simpler proxy; crisis-specific |
| Analyst revision momentum | Consensus estimate changes | Forward-looking fundamental signal |
| Social media vol mentions | Twitter/Reddit vol keywords | Extremely noisy but can lead VIX by hours |

---

## The Complete Architecture: How Features Compose

Based on the full research picture, here's how the layers interact in the best possible model:

```
                          +-----------------------------------+
                          |   FINAL FORECAST: sigma^2_{t+h}   |
                          +-----------------+-----------------+
                                            |
                    +-------------------------------------------+
                    |  Ensemble: LightGBM + LSTM blend          |
                    |  (prediction-level, NOT feature-level)    |
                    +-------------------+-----------------------+
                                        |               
              +-------------------------+               +----------------------------+
              |                                                                      |
    +---------+------------+                           +-----------------------------+
    |  LightGBM/XGBoost   |                           |   LSTM / TCN (DeepVol)      |
    |  Tabular features   |                           |   Intraday sequences        |
    |  (Layers 0-6)       |                           |   (E-mini L2 raw ticks)     |
    +---------------------+                           +-----------------------------+
              |                                                    |
    +---------+------------------------------------------+        |
    |  ~80-120 engineered features                       |   Raw 5-min or 1-min
    |                                                    |   return sequences
    |  HAR core (5) + Asymmetry (6) + Options (9)       |   with LOB snapshots
    |  + Microstructure (9) + Cross-asset (8)           |
    |  + Calendar (8) + Memory (4) + Sentiment (4)      |
    +----------------------------------------------------+
```

**Why this architecture (from research journal + Optiver evidence):**
- LightGBM dominates tabular features 4:1 over NNs (Optiver meta-analysis)
- LSTMs/TCNs add value specifically on *sequential* microstructure data where temporal order matters
- Prediction-level ensembling (blending outputs) beats feature-level fusion (NN embeddings into trees)
- This matches the "hybrid that actually works" pattern from Optiver analysis

---

## Feature Priority by Forecast Horizon

Different features dominate at different horizons:

| Horizon | Dominant Features | Marginal Improvement Source |
|---------|-------------------|----------------------------|
| **Intraday** (10min-1hr) | Microstructure (L3): price acceleration, OBI, spread | Trees with 600+ features (Optiver pattern) |
| **1 day** | HAR core (L0) + RQ (L0) + asymmetry (L1) | HARQ alone nearly optimal; ML adds ~5% |
| **1 week** | Options (L2) + cross-asset (L4) eclipse micro (L3) | VRP + skew give 5-10% over pure RV models |
| **1 month** | VRP (L2) + macro regime (L4) + Hurst (L6) | Options have maximum informational advantage |

**The critical insight the vol guide emphasizes:** ML's genuine advantage over HAR *grows with horizon*. At h=1, "HARd to Beat" (2024) shows properly-fitted HAR ties ML. At h=5 and h=22, CSV (2023) shows 10-20% QLIKE improvement from ML with rich features. **If you're only forecasting 1 day ahead, the feature set matters less. If you're forecasting 1 week+, Layers 2-4 are where the money is.**

---

## What GS Data Uniquely Enables vs. Public Data

| Capability | GS Data | Public Alternative | Edge |
|------------|---------|-------------------|------|
| RV estimation quality | Tick-level, 34 symbols, 11.3 years | 5-min returns from TAQ/Oxford-Man | Precise RQ, jump detection, kernel-based estimators |
| Options surface features | Full SPX tenor x strike grid (Marquee) | VIX only (model-free 30-day) | Full surface derivatives: skew, butterfly, slope, event-implied |
| Microstructure depth | E-mini L2 (4M ticks/day) | L1 quotes only (TAQ) | OBI at depth levels 2-5, true depth imbalance |
| Cross-asset synchronization | Same tick timestamp across asset classes | Daily closes only | Intraday lead-lag detection, spillover timing |
| Panel breadth | 30 mega-caps + 4 ETFs + E-mini | Typically 1 index or 29 DJIA (CSV 2023) | Graph-based models, sector structure, cross-sectional features |

---

## The Diminishing Returns Curve

1. **Layer 0 alone (5 features, HARQ):** ~55% of achievable forecast accuracy
2. **+ Layer 1 (11 features, HARQ + asymmetry):** ~70% of achievable accuracy
3. **+ Layer 2 (20 features, + options):** ~85% of achievable accuracy
4. **+ Layer 3-4 (40 features, + micro + cross-asset):** ~95% of achievable accuracy
5. **+ Layers 5-7 (80-120 features, full set):** 100% -- last 5% from calendar, memory, sentiment

The vol guide's final verdict (Ch. 10): **"The feature set you choose matters more than the model you choose."**

The *absolute best* feature set is all seven layers, engineering {level, change, z-score} variants of each base quantity, with horizon-appropriate feature selection (drop micro features at monthly horizon, drop calendar at intraday). But layers 0-2 get you 85% of the way there with 20 features and a Ridge regression.

---

## Key Papers Behind Each Layer

| Layer | Primary Citations |
|-------|-------------------|
| 0 (HAR + RQ) | Corsi 2009, Bollerslev-Patton-Quaedvlieg 2016 |
| 1 (Asymmetry) | Patton-Sheppard 2015, Barndorff-Nielsen-Shephard 2004, ABD 2007 |
| 2 (Options) | Bollerslev-Tauchen-Zhou 2009, Gu-Kelly-Xiu 2020, Bekaert-Hoerova 2014 |
| 3 (Microstructure) | Optiver 2021 competition, Cartea-Jaimungal-Penalva 2015, Easley-LdP-O'Hara |
| 4 (Cross-asset) | Diebold-Yilmaz 2012/2014, Zhang-Cucuringu-Dong 2024 |
| 5 (Calendar) | Patton-Verardo 2012, Savor-Wilson 2014 |
| 6 (Memory) | Lopez de Prado 2018, Gatheral-Jaisson-Rosenbaum 2018, Cont-Das 2024 |
| 7 (Sentiment) | Audrino et al. 2020, Rahimikia-Poon 2021 |

---

## Practical Recommendations for Implementation Order

Based on diminishing returns + data complexity:

1. **Start here:** HARQ + SHAR baseline (Layers 0-1, 11 features, OLS/Ridge)
2. **First ML step:** Add options layer (Layer 2, 20 total features, LightGBM)
3. **Panel extension:** Cross-asset + spillover (Layer 4, 30 features)
4. **Intraday module:** E-mini microstructure (Layer 3, separate LSTM component)
5. **Polish:** Calendar + roughness + sentiment (Layers 5-7, full 80-120 features)

Each step has a clear scientific question and is independently reportable as a result.

## Deep Research Findings (2026-05-06)

**Rashomon-aware feature analysis (novel for finance):**
- With TreeFARMS/SPLIT, construct the Rashomon set of all near-optimal interpretable trees on the vol feature panel, then compute Variable Importance Clouds (Dong & Rudin 2020, Nature Machine Intelligence) (`dong-rudin-2020` in bibliography)
- VIC gives an interval [min, max] of importance for each feature across the Rashomon set
- Features with non-overlapping clouds = robustly important vs. accidentally selected by a single greedy CART
- Financial features are heavily redundant (RV-d, BV-d, RQ-d, WAP-vol-d are near-collinear) -- Rashomon analysis would reveal which are essential (appear in every near-optimal tree), interchangeable (substitutable), or useless (in no near-optimal tree)
- To our knowledge, this analysis has not been published for any financial time series problem

**Feature construction pitfalls (from Section G):**
- Lookahead bias: realized measures use intraday returns up to time t; features for predicting RV_{t+1} must use only information <= t. Microstructure features computed on the full day require careful timestamp alignment
- Model in log-RV space: log-RV is near-unit-root; differencing destroys signal. Use fractional differencing or model in log-RV directly
- Train with QLIKE loss, not MSE: Zhang et al. (2025 GNN paper) report this matters substantially; MSE is dominated by extreme vol days (`zhang-pu-cucuringu-dong-2025` in bibliography)
- Choice of fitting scheme for HAR matters more than ML model choice per Wilms et al. 2024 "HARd to Beat" (`wilms-etal-2024` in bibliography)

## Deep Research Findings (2026-05-07)

**Rashomon-set value for feature analysis (decision tree deep research):**
- Feature interchangeability detection: VIX, V2X, VVIX, MOVE, RV lags, ATM IV, IV-RV spread, term-structure slope are all near-substitutes. Single-model importance (gain, permutation, SHAP) is unstable across refits because of this redundancy
- RID (Donnelly et al. 2023, NeurIPS) delivers a stable importance distribution over (Rashomon set x bootstrap) with consistency theorems and finite-sample error rates (`donnelly-katta-rudin-browne-2023` in bibliography)
- VIC (Dong & Rudin 2020) visualizes substitution structure directly: features with non-overlapping importance clouds are robustly distinct
- Regime-stable model selection: train TreeFARMS/RESPLIT on rolling-window data; intersect Rashomon sets across regimes to find trees near-optimal in every regime -- robust to non-stationarity
- Ex-ante stress testing: prediction multiplicity at any input quantifies the range of predictions across all defensible models -- useful for risk reporting
- Constraint satisfaction post-hoc: prefer trees in the Rashomon set that are monotone in VIX (VIX up -> RV up), do not split on a flagged feature, or satisfy any other constraint -- without retraining

**Interpretable vol forecasting pipeline (from decision tree applicability assessment):**
1. Feature engineering: HAR lags, HARQ realized-quarticity, signed semivariances, BNS jumps, VIX/VVIX, volume/spread, macro (ADS, EPU), cross-asset (SPY corr, sector RV)
2. Binarization (for GOSDT/SPLIT family only): GOSDT-Guesses LightGBM threshold guesser, cap ~300 binary features
3. Target: log(RV_{t+1}) or RV_{t+1:t+5} for weekly (ML gains larger at longer horizons)
4. Train: STreeDPiecewiseLinearRegressor depth <=5, elastic-net leaves, cost-complexity tuned via purged blocked k-fold CV
5. Rashomon analysis: TreeFARMS/RESPLIT within epsilon=2% MSE of optimum; compute RID per feature; filter for monotonicity and sparsity (<=12 leaves)
6. Evaluate: walk-forward MSE, QLIKE, MAE; DM tests vs HAR/HARQ/LightGBM; Rashomon prediction range during regime breaks (Mar-2020, Volmageddon)
7. Production: pickle tree + feature pipeline, re-train weekly on rolling 5-yr window, monitor Rashomon-set drift

**Novelty (May 2026):**
- No peer-reviewed paper, preprint, Kaggle notebook, or industry blog has applied any optimal-tree or Rashomon-set method to realized-volatility forecasting, return prediction, or any financial time-series
- Closest published applications are to cross-sectional credit risk (FICO HELOC) and criminal justice (COMPAS)
