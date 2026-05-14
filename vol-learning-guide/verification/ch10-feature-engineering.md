# Chapter 10: Feature Engineering for Volatility -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 89
**Verified:** 0/89
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 102-107 | defining-formula | Triple expansion: $x_t^{\text{level}} = x_t$, $x_t^{\text{change}} = x_t - x_{t-k}$, $x_t^{\text{z-score}} = (x_t - \bar{x}_{t,w}) / \hat{\sigma}_{x,t,w}$ with lookback $w$ (typically 22 days), $k \in \{1,5\}$ | [uncited] | | | Guide-internal definition; verify convention against vol-project-ref ch8 |
| 2 | 147 | numerical-fact | "triple expansion is identified as a core engineering principle: it captures state, direction, and unusualness...feature counts grow from ~20 base features to ~80 model inputs" | [uncited] | | | Check vol-project-ref ch8 feature composition |
| 3 | 157-161 | defining-formula | HAR RV components: $\RV_t^{(d)} = \RV_t$, $\RV_t^{(w)} = \frac{1}{5}\sum_{i=0}^{4} \RV_{t-i}$, $\RV_t^{(m)} = \frac{1}{22}\sum_{i=0}^{21} \RV_{t-i}$ | [uncited] | | | Standard HAR definition from Corsi (2009); check ch6 for consistency |
| 4 | 176 | numerical-fact | "These three variables alone explain roughly 40--60% of the variation in next-day log-RV for equity indices" | [uncited] | | | Widely cited range; verify against Corsi (2009) or Christensen et al. (2023) |
| 5 | 218-219 | defining-formula | Realized quarticity: $\operatorname{RQ}_t = \frac{n}{3} \sum_{i=1}^{n} r_{t,i}^4$ | [uncited] | | | Check scaling factor $n/3$ against BPQ2016 or Barndorff-Nielsen & Shephard |
| 6 | 221 | qualitative | "Under standard diffusion assumptions, $\operatorname{RQ}_t \xrightarrow{p} \int_0^1 \sigma_s^4 \, ds$ as $n \to \infty$" | [uncited] | | | Asymptotic result; verify against Barndorff-Nielsen & Shephard (2002) |
| 7 | 225 | numerical-fact | "$n$ is the number of intraday returns (e.g., 78 for 5-minute bars in a 6.5-hour session)" | [uncited] | | | Arithmetic check: 6.5 hours * 60 min / 5 min = 78 |
| 8 | 239 | qualitative | "The asymptotic variance of $\RV_t$ is proportional to $\operatorname{RQ}_t$" | [uncited] | | | Verify against Barndorff-Nielsen & Shephard (2002) |
| 9 | 241 | attribution | "Bollerslev, Patton, and Quaedvlieg (2016) exploit this insight in the HARQ model: they interact the daily RV component with $\sqrt{\operatorname{RQ}_t}$, allowing the model to down-weight noisy days" | BollerslevPattonQuaedvlieg2016HARQ | | | |
| 10 | 247 | defining-formula | HARQ state-dependent coefficient: $\beta_{d,t} = \beta_d + \beta_{dQ} \sqrt{\operatorname{RQ}_t}$ | BollerslevPattonQuaedvlieg2016HARQ | | | |
| 11 | 254 | numerical-fact | "HARQ interaction feature...improves QLIKE by 5--15% across equity indices" | BollerslevPattonQuaedvlieg2016HARQ | | | Verify range 5--15% in BPQ2016 |
| 12 | 279-282 | defining-formula | Realized semivariances: $\RV_t^+ = \sum_{i=1}^{n} r_{t,i}^2 \mathbf{1}(r_{t,i} > 0)$, $\RV_t^- = \sum_{i=1}^{n} r_{t,i}^2 \mathbf{1}(r_{t,i} < 0)$ | [uncited] | | | Standard definition; check Barndorff-Nielsen, Kinnebrock, Shephard (2010) or Patton & Sheppard (2015) |
| 13 | 297 | qualitative | "By construction, $\RV_t = \RV_t^+ + \RV_t^-$ (ignoring zero returns)" | [uncited] | | | Mathematical identity |
| 14 | 302 | numerical-fact | "Replacing total RV with the signed pair ($\RV_t^+$, $\RV_t^-$) in the HAR framework reduces out-of-sample QLIKE loss by 3--8% for equity index volatility" | PattonSheppard2015 | | | |
| 15 | 303 | numerical-fact | "The coefficient on $\RV_t^-$ is roughly twice that on $\RV_t^+$, confirming the leverage effect at intraday frequency" | PattonSheppard2015 | | | |
| 16 | 307 | defining-formula | Jump component: $J_t = \max(\RV_t - \BPV_t, 0)$ | [uncited] | | | Standard from Andersen, Bollerslev, Diebold (2007); check ch4 consistency |
| 17 | 309-311 | defining-formula | Signed jumps: $J_t^+ = \sum_{i} r_{t,i}^2 \mathbf{1}(r_{t,i} > 0, |r_{t,i}| > \theta_t)$, $J_t^- = \sum_{i} r_{t,i}^2 \mathbf{1}(r_{t,i} < 0, |r_{t,i}| > \theta_t)$ | [uncited] | | | Verify formula structure against literature |
| 18 | 325 | numerical-fact | "Negative jumps...In HAR-CJ extensions, including $J_t^-$ separately improves QLIKE by 1--3%" | [uncited] | | | No citation; verify source |
| 19 | 329 | attribution | "Bollerslev, Li, Patton, and Quaedvlieg (2020) extend semivariances to the multivariate case, computing covariances conditional on the sign of the market return" | BollerslevLiPattonQuaedvlieg2020 | | | |
| 20 | 330 | qualitative | "the downside component of any cross-asset covariance feature carries more information than the upside component" | BollerslevLiPattonQuaedvlieg2020 | | | |
| 21 | 348-351 | defining-formula | Realized skewness: $\operatorname{RSkew}_t = \frac{\frac{1}{n}\sum r_{t,i}^3}{(\frac{1}{n}\sum r_{t,i}^2)^{3/2}}$; Realized kurtosis: $\operatorname{RKurt}_t = \frac{\frac{1}{n}\sum r_{t,i}^4}{(\frac{1}{n}\sum r_{t,i}^2)^{2}}$ | [uncited] | | | Standard formulas; verify normalization convention |
| 22 | 367-369 | qualitative | "Realized skewness and kurtosis are noisy estimators and have shown only modest incremental forecasting power for next-day RV in most studies" | [uncited] | | | Verify against empirical literature |
| 23 | 385-387 | defining-formula | Order book imbalance: $\text{OBI}_t = \frac{V_t^{\text{bid}} - V_t^{\text{ask}}}{V_t^{\text{bid}} + V_t^{\text{ask}}}$ | [uncited] | | | Standard microstructure definition |
| 24 | 404-406 | defining-formula | Weighted average price: $\text{WAP}_t = \frac{p_t^{\text{bid}} \cdot V_t^{\text{ask}} + p_t^{\text{ask}} \cdot V_t^{\text{bid}}}{V_t^{\text{bid}} + V_t^{\text{ask}}}$ | [uncited] | | | Standard LOB definition |
| 25 | 468-469 | defining-formula | Price acceleration: $a_{t,i} = \Delta \log(\text{WAP}_{t,i}) - \Delta \log(\text{WAP}_{t,i-1})$ | [uncited] | | | |
| 26 | 496 | attribution | "Easley, Lopez de Prado, and O'Hara (2012) propose an alternative: partition the trading day into volume buckets" (VPIN) | EasleyLopezOHara2012 | | | |
| 27 | 502-503 | defining-formula | VPIN: $\text{VPIN}_t = \frac{1}{n} \sum_{\tau=1}^{n} \frac{|V_\tau^B - V_\tau^S|}{V_{\text{bucket}}}$ | EasleyLopezOHara2012 | | | Verify formula matches ELO2012 |
| 28 | 508 | numerical-fact | "n: number of volume buckets per estimation window (typically 50)" | EasleyLopezOHara2012 | | | Verify n=50 is the recommended value |
| 29 | 509 | qualitative | "VPIN ranges from 0 (perfectly balanced flow) to 1 (completely one-sided flow)" | EasleyLopezOHara2012 | | | Mathematical property |
| 30 | 528 | attribution | "Kyle (1985) shows that in a market with a single informed trader and competitive market makers, the equilibrium pricing rule is linear in aggregate order flow" | Kyle1985 | | | |
| 31 | 531-533 | defining-formula | Kyle's lambda regression: $\Delta p_t = \alpha + \lambda \cdot (\text{signed volume})_t + \varepsilon_t$ | Kyle1985 | | | |
| 32 | 542-544 | supporting-formula | Rolling Kyle's lambda estimation: $\Delta p_{t,i} = \hat{\alpha} + \hat{\lambda}_t \cdot (V_{t,i}^B - V_{t,i}^S) + \hat{\varepsilon}_{t,i}$ | Kyle1985 | | | |
| 33 | 570 | attribution | "The Amihud illiquidity ratio (Amihud, 2002) provides a liquidity measure that requires only daily returns and dollar volume" | Amihud2002 | | | |
| 34 | 575-576 | defining-formula | Amihud illiquidity: $\text{ILLIQ}_{i,t} = \frac{1}{D_t}\sum_{d=1}^{D_t} \frac{|r_{i,d}|}{\text{DVOL}_{i,d}} \times 10^6$ | Amihud2002 | | | Verify formula and scaling factor match Amihud (2002) |
| 35 | 606 | attribution | "The microprice (Cartea, Jaimungal, and Penalva, 2015) corrects for order-book imbalance by shifting the estimated fair value toward the thinner side of the book" | CarteaJaimungalPenalva2015 | | | |
| 36 | 608-609 | defining-formula | Microprice: $S^*_t = \frac{V_t^{\text{ask}} \cdot P_t^{\text{bid}} + V_t^{\text{bid}} \cdot P_t^{\text{ask}}}{V_t^{\text{bid}} + V_t^{\text{ask}}}$ | CarteaJaimungalPenalva2015 | | | Note: identical formula structure to WAP (claim 24) |
| 37 | 647 | attribution | "Order flow imbalance (OFI), Cont, Kukanov, and Stoikov (2014), tracks how the book changes over time, capturing the dynamic pressure of order arrivals and cancellations" | ContKukanovStoikov2014 | | | |
| 38 | 652-654 | defining-formula | OFI event contribution: $e_n = \mathbf{1}_{P_n^B \geq P_{n-1}^B} q_n^B - \mathbf{1}_{P_n^B \leq P_{n-1}^B} q_{n-1}^B - \mathbf{1}_{P_n^A \leq P_{n-1}^A} q_n^A + \mathbf{1}_{P_n^A \geq P_{n-1}^A} q_{n-1}^A$ | ContKukanovStoikov2014 | | | Verify exact indicator structure against CKS2014 |
| 39 | 666-668 | defining-formula | Interval OFI: $\text{OFI}_k = \sum_{n \in [t_{k-1}, t_k]} e_n$ | ContKukanovStoikov2014 | | | |
| 40 | 672-673 | defining-formula | OFI price impact regression: $\Delta P_k = \beta \cdot \text{OFI}_k + \varepsilon_k$ | ContKukanovStoikov2014 | | | |
| 41 | 676 | numerical-fact | "Estimated on 10-second intervals for 50 US equities, this simple regression achieves $R^2 \approx 65\%$" | ContKukanovStoikov2014 | | | |
| 42 | 676-677 | numerical-fact | "far higher than trade-based measures ($R^2 \approx 32\%$ for signed trade imbalance)" | ContKukanovStoikov2014 | | | |
| 43 | 677 | qualitative | "When both OFI and trade imbalance are included, trade imbalance becomes insignificant: OFI subsumes its information" | ContKukanovStoikov2014 | | | |
| 44 | 695-697 | defining-formula | Depth ratio: $\text{DR}_t^{(L)} = \frac{\sum_{\ell=1}^{L} V_t^{\text{bid},\ell}}{\sum_{\ell=1}^{L} V_t^{\text{ask},\ell}}$ | [uncited] | | | |
| 45 | 705-706 | defining-formula | Market urgency: $\text{Urgency}_t = s_t \times |\text{OBI}_t|$ | [uncited] | | | |
| 46 | 738-739 | defining-formula | Risk reversal: $\text{RR}_{25} = \IVol_{25\Delta\text{call}} - \IVol_{25\Delta\text{put}}$ | [uncited] | | | Standard convention; verify sign convention (some sources define put minus call) |
| 47 | 756-758 | defining-formula | IV term structure slope: $\text{TS}_t = \IVol_t^{(3\text{m})} - \IVol_t^{(1\text{m})}$ | [uncited] | | | |
| 48 | 774-776 | defining-formula | VRP proxy: $\VRP_t = \frac{\text{VIX}_t^2}{10{,}000} - \E_t[\RV_{t+30}]$ | [uncited] | | | Verify scaling factor and sign convention; check ch9 consistency |
| 49 | 798-799 | defining-formula | VIX futures term structure ratio: $\text{VTS}_t = F_t^{(3\text{m})}(\text{VIX}) / \text{VIX}_t$ | [uncited] | | | |
| 50 | 809 | numerical-fact | "the front-month VIX future has roughly 90% sensitivity (delta) to spot VIX, while the 6-month future has only 55%" | Bennett2014 | | | |
| 51 | 810 | numerical-fact | "When VIX spikes above 40, the 6-month future barely moves because the market does not expect the high-volatility environment to persist that long" | Bennett2014 | | | Qualitative claim attributed to Bennett |
| 52 | 815-816 | defining-formula | Forward implied volatility: $\sigma_{T_1 \to T_2} = \sqrt{\frac{\sigma_2^2 T_2 - \sigma_1^2 T_1}{T_2 - T_1}}$ | [uncited] | | | Standard result from additive variance rule |
| 53 | 846 | numerical-fact | "At the 1-day horizon, the gain is modest (1--3% QLIKE). At the 1-week and 1-month horizons, the gain can reach 5--10%" (options features vs HAR baselines) | [uncited] | | | Verify against Christensen et al. (2023) or other source |
| 54 | 862 | attribution | "Diebold and Yilmaz (2012) propose a variance decomposition of a VAR on a panel of volatilities, producing a total spillover index" | DieboldYilmaz2012 | | | |
| 55 | 867-869 | defining-formula | Diebold-Yilmaz spillover index: $S^H = \frac{\sum_{i \neq j} \theta_{ij}^H}{\sum_{i,j} \theta_{ij}^H} \times 100$ | DieboldYilmaz2012 | | | |
| 56 | 886 | methodological | "you compute the spillover index on a rolling window (200 trading days is typical)" | [uncited] | | | Check DY2012 for recommended window size |
| 57 | 898 | qualitative | "Volatility has long memory: the autocorrelation of log-RV decays hyperbolically, not exponentially" | [uncited] | | | Well-established stylized fact; see ch7 |
| 58 | 903 | attribution | "Following Lopez de Prado (2018, AFML) (Chapter 5), define the fractional difference operator" | LopezdePrado2018AFML | | | Verify it is Chapter 5 of AFML |
| 59 | 904-906 | defining-formula | Fractional differencing: $(1 - L)^d x_t = \sum_{k=0}^{\infty} \binom{d}{k} (-1)^k x_{t-k}$ | LopezdePrado2018AFML | | | |
| 60 | 921-923 | supporting-formula | Generalized binomial coefficients: $\binom{d}{k} = \frac{d(d-1)(d-2)\cdots(d-k+1)}{k!}$ | [uncited] | | | Standard mathematical definition |
| 61 | 925 | methodological | "In practice, you truncate the infinite sum at a lag $k^*$ where $|\binom{d}{k^*}|$ falls below a threshold (e.g., $10^{-4}$)" | LopezdePrado2018AFML | | | Verify threshold value against AFML |
| 62 | 967 | numerical-fact | "At $d \approx 0.35$--$0.45$: the series passes the ADF test for stationarity while retaining most of its autocorrelation structure" | [uncited] | | | Verify sweet-spot range; may be data-dependent |
| 63 | 975 | numerical-fact | "When $H$ drops below 0.1, the vol-of-vol process is particularly rough, and mean-reversion is fast" | [uncited] | | | Verify Hurst exponent threshold against rough vol literature |
| 64 | 976 | numerical-fact | "When $H$ rises toward 0.3--0.4, persistence is higher and trends in volatility last longer" | [uncited] | | | Verify range |
| 65 | 1000-1001 | defining-formula | Vol-of-vol: $\text{VoV}_t = \sqrt{\frac{1}{21}\sum_{i=0}^{21} (\RV_{t-i} - \bar{\RV}_{t,22})^2}$ | [uncited] | | | Guide-internal definition |
| 66 | 1026-1027 | defining-formula | Regime duration: $D_t = t - \max\{\tau \leq t : \RV_\tau > \bar{\RV}_{\tau,66} + 2\hat{\sigma}_{\RV,\tau,66}\}$ | [uncited] | | | Guide-internal definition; 66-day = 3-month convention |
| 67 | 1089-1091 | defining-formula | Event-implied vol: $\sigma_{\text{event}} = \sqrt{\frac{T_2 \sigma_2^2 - T_1 \sigma_1^2}{T_2 - T_1}}$ | [uncited] | | | Same structure as forward vol formula (claim 52); standard result |
| 68 | 1108 | numerical-fact | "FOMC days typically show 1.5--2x normal RV; NFP days show 1.3--1.5x" | [uncited] | | | Verify against empirical literature |
| 69 | 1124-1125 | defining-formula | Calendar proximity feature: $\text{prox}_{e,t} = \max(0, W_e - |t - t_e^{\text{next}}|)$ | [uncited] | | | Guide-internal definition |
| 70 | 1162 | numerical-fact | "Proximity features provide 1--2% incremental QLIKE improvement over binary dummies alone at the 1-day horizon" | [uncited] | | | Verify source |
| 71 | 1220 | attribution | "Audrino, Signrist, and Ballinari (2020) construct daily sentiment indices from financial news articles and show that adding a negative-sentiment variable to the HAR model improves volatility forecasts, particularly during crisis periods" | AudrinoSignristBallinari2020 | | | |
| 72 | 1221 | qualitative | "negative sentiment matters more than positive sentiment" for vol forecasting | AudrinoSignristBallinari2020 | | | |
| 73 | 1223 | attribution | "Rahimikia, Zohren, and Poon (2021) apply transformer-based NLP models (FinBERT) to extract sentiment from financial text" | RahimikiaZohrenPoon2021 | | | Verify they use FinBERT specifically |
| 74 | 1226 | numerical-fact | "text-derived sentiment adds 1--3% improvement in QLIKE loss over HAR-family baselines, with gains concentrated in high-volatility periods" | AudrinoSignristBallinari2020, RahimikiaZohrenPoon2021 | | | Verify range against both papers |
| 75 | 1335 | attribution | "Christensen, Siggaard, and Veliyev (2023) advocate ALE plots over partial dependence plots (PDPs) for volatility models" | ChristensenSiggaardVeliyev2023 | | | |
| 76 | 1341-1342 | defining-formula | ALE plot: $\widehat{\text{ALE}}_j(x) = \sum_{k=1}^{k_x} \frac{1}{n_k} \sum_{i: x_j^{(i)} \in [z_{k-1}, z_k]} [\hat{f}(z_k, \bx_{-j}^{(i)}) - \hat{f}(z_{k-1}, \bx_{-j}^{(i)})]$ | ChristensenSiggaardVeliyev2023 | | | ALE formula is from Apley & Zhu (2020); CSV2023 advocates its use |
| 77a | 1488 | qualitative | "a properly fitted HAR model with daily re-estimation and a 630-day training window is 'hard to beat' even with gradient-boosted trees and neural networks, when the feature set is restricted to lagged RV and VIX" | HARdToBeat2024 | | | Verify 630-day window specifically |
| 77b | 1492-1493 | qualitative | "ML models gain the most from additional features at longer horizons, where the informational advantage of options-implied and macroeconomic variables over lagged RV is greatest" | ChristensenSiggaardVeliyev2023 | | | |
| 77c | 1493 | qualitative | "At $h = 22$, ML models with the full feature set ($\mathcal{M}_{\text{ALL}}$) consistently outperform all HAR variants, and the Diebold-Mariano test frequently rejects equal predictive accuracy" | ChristensenSiggaardVeliyev2023 | | | |
| 78 | 1310-1311 | defining-formula | SHAP decomposition: $\hat{y}_i = \phi_0 + \sum_{j=1}^{p} \phi_j^{(i)}$ | [uncited] | | | Standard SHAP from Lundberg & Lee (2017); no citation in text |
| 79 | 1450 | attribution | "Exact percentages are illustrative and based on findings in Christensen, Siggaard, and Veliyev (2023) and the vol-project-ref feature composition analysis" (diminishing returns staircase) | ChristensenSiggaardVeliyev2023 | | | Verify which specific numbers come from CSV2023 |
| 80 | 1458 | numerical-fact | "Layer 0 (HAR core): $\RV_t^{(d)}$, $\RV_t^{(w)}$, $\RV_t^{(m)}$ alone achieve roughly 55% of attainable accuracy" | ChristensenSiggaardVeliyev2023 | | | Verify 55% figure |
| 81 | 1460 | numerical-fact | "Layer 1 (Noise + Asymmetry): Adding $\sqrt{\operatorname{RQ}_t}$, $\RV_t^-$, $\RV_t^+$, and jump components pushes accuracy to roughly 70%" | ChristensenSiggaardVeliyev2023 | | | Verify 70% figure |
| 82 | 1462 | numerical-fact | "Layer 2 (Options): ATM IV, skew, VRP, and term structure slope bring the total to roughly 85%" | ChristensenSiggaardVeliyev2023 | | | Verify 85% figure |
| 83 | 1464 | numerical-fact | "Layers 3--7 collectively contribute the final 15%, with each individual layer adding 2--5 percentage points" | ChristensenSiggaardVeliyev2023 | | | |
| 84 | 1480 | numerical-fact | "h=1 day: ML vs linear gap is Small (~5%); HARQ nearly optimal" | ChristensenSiggaardVeliyev2023, HARdToBeat2024 | | | |
| 85 | 1481 | numerical-fact | "h=5 days: ML vs linear gap is Moderate (~10%); VRP begins to matter" | ChristensenSiggaardVeliyev2023, HARdToBeat2024 | | | |
| 86 | 1482 | numerical-fact | "h=22 days: ML vs linear gap is Large (~15%); Options have max advantage" | ChristensenSiggaardVeliyev2023, HARdToBeat2024 | | | |
| 87 | 1499 | methodological | "Get the HAR baseline correct: daily re-estimation, 500--800 day training window, log-RV target" | HARdToBeat2024 | | | Verify 500--800 day range; claim 77a says 630-day |
