# Chapter 13: Hybrid and Ensemble Methods -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 47
**Verified:** 0/47
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 13-14 | qualitative | Hybrid models are "the safest bet in the volatility forecasting literature" | RahimikiaPoon2020 | | | Strong claim; verify paper says this or equivalent |
| 2 | 28-30 | qualitative | The resulting hybrid "almost always outperforms either component alone" with "lower variance and greater interpretability than a pure ML approach" | RahimikiaPoon2020 | | | Two sub-claims: (a) outperformance, (b) lower variance + greater interpretability |
| 3 | 41-42 | numerical-fact | A fitted HAR model typically explains 40--60% of next-day realized-volatility variation with just three coefficients | RahimikiaPoon2020 | | | Verify R-squared range in paper |
| 4 | 56-58 | qualitative | Combining two weakly correlated forecasters reduces overall forecast variance by the "standard diversification identity" | RahimikiaPoon2020 | | | Verify paper invokes diversification argument |
| 5 | 190-194 | qualitative | SVR is a natural first choice for the residual stage because its epsilon-insensitive loss function automatically ignores small residuals; SVR focuses capacity on days where HAR fails most, such as post-jump or regime-change dates | RahimikiaPoon2020 | | | Verify paper recommends SVR for residual stage specifically |
| 6 | 207-212 | defining-formula | HAR model for hybrid: $\widehat{HAR}_t = \hat{\beta}_0 + \hat{\beta}_d RV_t + \hat{\beta}_w RV_t^{(w)} + \hat{\beta}_m RV_t^{(m)}$ | [uncited] | | | Standard HAR specification; cross-check with Ch. 6 |
| 7 | 214-215 | defining-formula | HAR residual: $e_t = RV_{t+1} - \widehat{HAR}_t$ | [uncited] | | | Standard definition |
| 8 | 239-242 | defining-formula | SVR epsilon-insensitive loss: $\min_{w,b} \frac{1}{2}\|w\|^2 + C \sum_{t=1}^{T} \max(0, |e_t - f(X_t)| - \varepsilon)$ | [uncited] | | | Verify this is the standard SVR formulation (sometimes written with two slack variables xi, xi*) |
| 9 | 275-277 | defining-formula | Combined HAR-SVR forecast: $\hat{y}_{t+1} = \widehat{HAR}_t + \widehat{SVR}(X_t)$ | [uncited] | | | Additive combination; standard in residual-hybrid literature |
| 10 | 317-318 | qualitative | GINN hard-wires the GARCH recursion directly into the neural network architecture so the network learns corrections to GARCH parameters rather than learning entire volatility dynamics from scratch | GINN2024 | | | Verify this is the core GINN design |
| 11 | 331-332 | defining-formula | Standard GARCH(1,1) update: $\sigma^2_{t+1} = \omega + \alpha \epsilon_t^2 + \beta \sigma^2_t$ | [uncited] | | | Standard textbook formula |
| 12 | 345-349 | defining-formula | GINN equation: $\sigma^2_{t+1} = \omega_t + \alpha_t \epsilon_t^2 + \beta_t \sigma^2_t$ where $(\omega_t, \alpha_t, \beta_t) = g_\theta(X_t)$ | GINN2024 | | | Core GINN architecture equation |
| 13 | 353-354 | methodological | GINN uses a small feedforward network, typically 2 hidden layers, 32--64 units each | GINN2024 | | | Verify network size in paper |
| 14 | 357-359 | methodological | GINN constrains parameters via softmax and sigmoid output activations to satisfy $\omega_t > 0$, $\alpha_t \geq 0$, $\beta_t \geq 0$, and $\alpha_t + \beta_t < 1$ | GINN2024 | | | Verify specific activation functions and constraints in paper |
| 15 | 438-440 | qualitative | GINN matches or outperforms both standard GARCH and unconstrained LSTMs on equity index volatility | GINN2024 | | | Verify performance comparison in paper |
| 16 | 440 | qualitative | GINN uses substantially fewer parameters than the LSTM | GINN2024 | | | Verify parameter count comparison |
| 17 | 451-452 | qualitative | The effect of news on volatility is asymmetric: negative news amplifies RV far more than positive news calms it | [uncited] | | | Well-known stylized fact but uncited here; leverage effect literature |
| 18 | 453-454 | qualitative | Rahimikia, Zohren, and Poon ask whether a machine-readable news signal can improve HAR forecasts; the answer is yes, but modestly and conditionally | RahimikiaZohrenPoon2021NLP | | | Verify paper's main finding |
| 19 | 462-466 | methodological | The NLP pipeline uses Word2Vec on a financial corpus, represents each article as the average of its word vectors, then aggregates to a daily sentiment score via a shallow classifier trained on labeled sentiment data | RahimikiaZohrenPoon2021NLP | | | Verify: (a) Word2Vec specifically, (b) average word vectors, (c) shallow classifier |
| 20 | 469-473 | defining-formula | Augmented HAR-NLP equation: $RV_{t+1} = \beta_0 + \beta_d RV_t + \beta_w RV_t^{(w)} + \beta_m RV_t^{(m)} + \gamma s_t + \varepsilon_{t+1}$ | RahimikiaZohrenPoon2021NLP | | | Verify this is the specification in the paper |
| 21 | 495-496 | numerical-fact | Public NLP signals add only 1--3% QLIKE improvement | [uncited] | | | Stated without citation here; cited at lines 508-510 |
| 22 | 508-509 | numerical-fact | Rahimikia, Zohren, and Poon report 1--3% improvement in QLIKE on average | RahimikiaZohrenPoon2021NLP | | | Verify exact percentage range in paper |
| 23 | 509-511 | qualitative | NLP gains are concentrated during financial crises and earnings seasons | RahimikiaZohrenPoon2021NLP | | | Verify: (a) crises, (b) earnings seasons specifically |
| 24 | 511-513 | qualitative | During calm markets, the sentiment signal adds negligible information because lagged RV already captures the low-volatility regime | RahimikiaZohrenPoon2021NLP | | | Verify calm-market finding in paper |
| 25 | 519-521 | qualitative | The NLP improvement does not survive aggressive transaction costs in short-horizon strategies | RahimikiaZohrenPoon2021NLP | | | Verify transaction cost analysis in paper |
| 26 | 524-527 | qualitative | Hybrid models combining econometric baselines with text-derived features outperform pure text-based approaches | RahimikiaPoon2020 | | | Verify this specific comparison in paper |
| 27 | 545-546 | defining-formula | Fixed weighted average: $\hat{y}_{t+1} = w \widehat{HAR}_t + (1-w) \widehat{GBM}_t$ | [uncited] | | | Standard combination formula |
| 28 | 551 | numerical-fact | Default HAR weight $w = 0.7$ described as "a robust default" | [uncited] | | | No citation for 0.7 being robust; may be pedagogical suggestion |
| 29 | 593-595 | defining-formula | Stacking formula: $\hat{y}_{t+1} = \alpha_0 + \alpha_1 \widehat{HAR}_t^{OOS} + \alpha_2 \widehat{GBM}_t^{OOS}$ | [uncited] | | | Standard stacking/Breiman approach |
| 30 | 651 | numerical-fact | Worked example: ridge meta-learner yields weights $\hat{\alpha}_1 = 0.45$, $\hat{\alpha}_2 = 0.58$ | [uncited] | | | Pedagogical example; verify internal arithmetic consistency |
| 31 | 654-655 | numerical-fact | Worked example: $\hat{\alpha}_0 + 0.45 \times 25.4 + 0.58 \times 22.8 = \hat{\alpha}_0 + 24.65$ | [uncited] | | | Arithmetic: $0.45 \times 25.4 = 11.43$; $0.58 \times 22.8 = 13.224$; sum = 24.654. Rounds to 24.65. Correct. |
| 32 | 657 | numerical-fact | Worked example: HAR alone achieves MSE = 2.06 | [uncited] | | | Verify against the 5-day data: errors are (-0.9, -1.4, -0.5, 1.9, -0.2); MSE = (0.81+1.96+0.25+3.61+0.04)/5 = 6.67/5 = 1.334. Claimed 2.06 looks wrong. |
| 33 | 657-658 | numerical-fact | Worked example: LightGBM alone achieves MSE = 0.89 | [uncited] | | | Verify against the 5-day data: errors are (0.5, -0.9, 0.2, -0.7, 0.4); MSE = (0.25+0.81+0.04+0.49+0.16)/5 = 1.75/5 = 0.35. Claimed 0.89 looks wrong. |
| 34 | 658-659 | numerical-fact | Worked example: stacked combination achieves MSE = 0.52 | [uncited] | | | Cannot fully verify without knowing alpha_0, but base MSEs appear incorrect (see #32, #33) |
| 35 | 741-742 | defining-formula | Feature stacking concatenation: $\tilde{X}_t = [X_t^{tab} \| h_t^{LSTM}]$ | [uncited] | | | Standard feature concatenation notation |
| 36 | 768-770 | qualitative | Feature stacking has a fundamental flaw: gradient isolation. LightGBM cannot compute gradients w.r.t. its inputs, so the LSTM embedding is never optimized for the tree's QLIKE objective | [uncited] | | | Technically correct property of tree models; no external citation needed |
| 37 | 836-839 | defining-formula | Three-stage residual stacking: $\hat{y}_{t+1} = \widehat{HAR}_t + \widehat{GBM}(X_t) + \widehat{LSTM}(X_t^{seq})$ | [uncited] | | | Follows from the additive residual construction |
| 38 | 898-901 | defining-formula | General prediction blending: $\hat{y}_{t+1} = \sum_{k=1}^{K} w_k \hat{y}_{t+1}^{(k)}$ with $\sum w_k = 1$ | [uncited] | | | Standard ensemble combination formula |
| 39 | 927-929 | defining-formula | Inverse-QLIKE weighting: $w_k = QLIKE_k^{-1} / \sum_{j=1}^{K} QLIKE_j^{-1}$ | [uncited] | | | Standard inverse-loss weighting scheme |
| 40 | 957-960 | qualitative | Top-performing solutions in the Optiver Realized Volatility competition consistently chose prediction blending over feature stacking; winners trained LightGBM and neural network branches independently, then combined outputs with simple weighted averages | Optiver2021 | | | Verify competition solution descriptions |
| 41 | 960-963 | qualitative | The rationale for prediction blending in Optiver competition: easier to debug, easier to iterate on, provides a natural fallback strategy | Optiver2021 | | | Verify this is stated/implied in competition solutions |
| 42 | 1017-1018 | qualitative | Feature stacking has "weak" literature support -- "no RV paper demonstrates gains" | [uncited] | | | Strong negative claim; verify no such paper exists |
| 43 | 1047-1053 | defining-formula | Regime-dependent weights: $w_k(t) = w_k^{low}$ if $RV_t^{(w)} < \tau$, $w_k^{high}$ if $RV_t^{(w)} \geq \tau$ | [uncited] | | | Standard regime-switching weight scheme |
| 44 | 1059 | numerical-fact | Regime threshold example: 75th percentile of training-set weekly RV distribution | [uncited] | | | Pedagogical suggestion, not a literature claim |
| 45 | 1119 | numerical-fact | Pure HAR/HARQ is best when sample is small (<500 days) | [uncited] | | | Reasonable heuristic but uncited |
| 46 | 1129 | numerical-fact | Pure trees are best with large sample (>2000 days) | [uncited] | | | Reasonable heuristic but uncited |
| 47 | 1144 | qualitative | You "earn the right to go pure ML only when you have a large sample, rich features, and evidence that the linear baseline leaves substantial structure in the residuals" | RahimikiaPoon2020 | | | Verify paper makes this conditional recommendation |
