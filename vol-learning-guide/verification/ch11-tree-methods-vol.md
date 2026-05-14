# Chapter 11: Tree-Based Methods for Volatility -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 62
**Verified:** 0/62
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 25-26 | qualitative | Tree-based ensembles are the best off-the-shelf learners for tabular data | GuKellyXiu2020 | | | Gu, Kelly, Xiu (2020) is about asset pricing; verify it makes this general claim about tabular data |
| 2 | 44 | numerical-fact | A LightGBM model with 500 trees trains in seconds on 1,250 rows | [uncited] | | | Plausible but verify order-of-magnitude timing |
| 3 | 65-66 | qualitative | A random forest trains many independent trees on bootstrapped samples and averages their predictions (variance reduction through decorrelation) | [uncited] | | | Standard textbook definition; verify "decorrelation" framing |
| 4 | 67-69 | qualitative | Gradient boosting trains trees sequentially, each one correcting the errors of the ensemble so far (bias reduction through iterative refinement) | [uncited] | | | Standard textbook definition |
| 5 | 68-69 | qualitative | Gradient boosting (LightGBM, XGBoost) typically wins on tabular data over random forests | [uncited] | | | General claim; verify against benchmarks |
| 6 | 139 | methodological | Gradient boosting starts with a constant prediction (the training-set mean of RV) | [uncited] | | | Standard GBM init; verify this is the default for regression |
| 7 | 143-145 | qualitative | The residuals are the negative gradient of the loss function with respect to the current prediction, so gradient boosting is gradient descent in function space | [uncited] | | | Friedman (2001) formulation; verify attribution |
| 8 | 216 | defining-formula | $\hat{y}_t = \sum_{m=1}^{M} \eta \, h_m(\bx_t)$ (gradient boosting ensemble prediction) | [uncited] | | | Standard formulation but typically includes an initial constant $F_0$; verify completeness |
| 9 | 246 | defining-formula | $\mathcal{L}_{\text{MSE}} = \frac{1}{N}\sum_t (\text{RV}_t - \hat{y}_t)^2$ | [uncited] | | | Standard MSE definition |
| 10 | 248 | attribution | QLIKE is the preferred loss for volatility forecasting | AudrinoKnaus2016 | | | Verify Audrino & Knaus (2016) specifically make this recommendation |
| 11 | 249-252 | defining-formula | $\mathcal{L}_{\text{QLIKE}} = \frac{1}{N}\sum_{t=1}^{N}\left(\frac{\text{RV}_t}{\hat{y}_t} - \ln\frac{\text{RV}_t}{\hat{y}_t} - 1\right)$ | AudrinoKnaus2016 | | | Verify this exact QLIKE formula matches source; note some formulations omit the -1 |
| 12 | 256-257 | qualitative | The QLIKE summand equals zero when $\hat{y}_t = \text{RV}_t$ and is strictly positive otherwise | [uncited] | | | Mathematical property; verify by substitution |
| 13 | 261-263 | qualitative | QLIKE penalizes under-predicting volatility more harshly than over-predicting it by the same amount | [uncited] | | | Verify asymmetry property of QLIKE |
| 14 | 272-275 | qualitative | QLIKE-optimized trees outperform MSE-optimized trees for realized volatility | AudrinoKnaus2016 | | | Verify this is a finding in Audrino & Knaus (2016) |
| 15 | 278-279 | qualitative | Neither LightGBM nor XGBoost provides QLIKE natively, but both accept custom objective functions | [uncited] | | | Verify both frameworks support custom objectives via gradient/Hessian |
| 16 | 281-282 | supporting-formula | $g_t = \frac{\partial \mathcal{L}_{\text{QLIKE}}}{\partial \hat{y}_t} = -\frac{\text{RV}_t}{\hat{y}_t^2} + \frac{1}{\hat{y}_t}$ (QLIKE gradient) | [uncited] | | | Verify by differentiating the QLIKE formula |
| 17 | 283-284 | supporting-formula | $h_t = \frac{\partial^2 \mathcal{L}_{\text{QLIKE}}}{\partial \hat{y}_t^2} = \frac{2\,\text{RV}_t}{\hat{y}_t^3} - \frac{1}{\hat{y}_t^2}$ (QLIKE Hessian) | [uncited] | | | Verify by differentiating the gradient |
| 18 | 319-320 | qualitative | Finance intuition says higher recent volatility predicts higher future volatility | [uncited] | | | Standard volatility clustering / persistence claim |
| 19 | 320-321 | qualitative | Monotone constraints can encode that prediction must be non-decreasing in $\text{RV}_{t-1}$ | [uncited] | | | Verify LightGBM/XGBoost support per-feature monotone constraints |
| 20 | 337 | numerical-fact | Five years of daily data gives roughly 1,250 observations | [uncited] | | | ~252 trading days/year x 5 = 1,260; verify approximation |
| 21 | 351-352 | methodological | Default LightGBM/XGBoost settings (max_depth=6+, min_child_samples=20) were designed for datasets with 100K+ rows | [uncited] | | | Verify actual LightGBM defaults: max_depth=-1 (no limit), min_child_samples=20 |
| 22 | 363 | numerical-fact | LightGBM default max_depth is 6-8 | [uncited] | | | LightGBM actual default is -1 (unlimited); XGBoost default is 6. Verify |
| 23 | 364 | numerical-fact | LightGBM default min_child_samples is 20 | [uncited] | | | Verify against LightGBM documentation |
| 24 | 365 | numerical-fact | LightGBM default subsample is 1.0 | [uncited] | | | Verify against LightGBM documentation (param is `bagging_fraction`) |
| 25 | 366 | numerical-fact | LightGBM default colsample_bytree is 1.0 | [uncited] | | | Verify against LightGBM documentation (param is `feature_fraction`) |
| 26 | 367 | numerical-fact | LightGBM default learning_rate is 0.1 | [uncited] | | | Verify against LightGBM documentation |
| 27 | 368 | numerical-fact | LightGBM default num_iterations is 100 | [uncited] | | | Verify against LightGBM documentation |
| 28 | 363 | methodological | Recommended max_depth for volatility data is 3-5 | [uncited] | | | Pedagogical recommendation; check if CSV2023 or other sources corroborate |
| 29 | 364 | methodological | Recommended min_child_samples for volatility data is 50-200 | [uncited] | | | Pedagogical recommendation |
| 30 | 365 | methodological | Recommended subsample for volatility data is 0.6-0.8 | [uncited] | | | Pedagogical recommendation |
| 31 | 366 | methodological | Recommended colsample_bytree for volatility data is 0.6-0.8 | [uncited] | | | Pedagogical recommendation |
| 32 | 367 | methodological | Recommended learning_rate for volatility data is 0.01-0.05 | [uncited] | | | Pedagogical recommendation |
| 33 | 368 | methodological | Recommended num_iterations for volatility data is 500-2000 | [uncited] | | | Pedagogical recommendation |
| 34 | 369 | methodological | Recommended reg_lambda for volatility data is 1-10 (default 0) | [uncited] | | | Verify LightGBM default reg_lambda is 0 |
| 35 | 375 | numerical-fact | Worked example uses 1,258 daily observations of RV for SPY with 45 features | [uncited] | | | Illustrative example; internal consistency check |
| 36 | 376-378 | methodological | Reserve last 6 months (126 days) as holdout; remaining 1,132 days for purged 5-fold CV with 5-day embargo | [uncited] | | | Check arithmetic: 1258-126=1132. Also 6 months ~ 126 trading days |
| 37 | 382 | numerical-fact | Worked example: HAR baseline QLIKE = 0.142 averaged across folds | [uncited] | | | Illustrative number in worked example |
| 38 | 385 | numerical-fact | Worked example: LightGBM with defaults gives QLIKE = 0.158 (validation), 0.041 (training) | [uncited] | | | Illustrative; but training/validation gap flags overfitting |
| 39 | 393 | numerical-fact | Worked example: Constrained LightGBM gives QLIKE = 0.131, training QLIKE = 0.098 | [uncited] | | | Illustrative number |
| 40 | 393 | numerical-fact | Worked example: Constrained LightGBM improves over HAR by 7.7% | [uncited] | | | Check arithmetic: (0.142-0.131)/0.142 = 0.0775 ~ 7.7% |
| 41 | 417-420 | attribution | Christensen, Siggaard, and Veliyev (2023) is the most comprehensive academic horse-race of ML methods for realized volatility forecasting | ChristensenSiggaardVeliyev2023 | | | Subjective "most comprehensive" claim; verify scope |
| 42 | 418-420 | methodological | CSV2023 setup: 29 DJIA stocks, daily and weekly RV forecasting, with features spanning RV lags, jumps, leverage effects, volume, and options-implied volatility | ChristensenSiggaardVeliyev2023 | | | Verify stock universe size (29 DJIA), horizons, and feature set |
| 43 | 424 | qualitative | Gradient-boosted trees (XGBoost) are among the top-performing models for daily RV forecasting across 29 DJIA stocks | ChristensenSiggaardVeliyev2023 | | | Verify XGBoost ranking in their results |
| 44 | 428-431 | qualitative | When feature set includes only RV lags, trees offer minimal improvement; when expanded to include jumps, leverage, volume, and implied vol, trees pull ahead by 5-15% in QLIKE | ChristensenSiggaardVeliyev2023 | | | Verify the 5-15% magnitude and the feature-richness interaction |
| 45 | 433-435 | qualitative | The gap between tree models and HAR is larger for weekly RV prediction than for daily | ChristensenSiggaardVeliyev2023 | | | Verify horizon effect in their results |
| 46 | 438-443 | qualitative | ALE plots show tree models primarily exploit the interaction between lagged RV and implied volatility | ChristensenSiggaardVeliyev2023 | | | Verify they use ALE plots and this specific finding |
| 47 | 447-449 | methodological | CSV2023 uses rolling-window evaluation (not purged CV); model re-estimated monthly | ChristensenSiggaardVeliyev2023 | | | Verify evaluation methodology and re-estimation frequency |
| 48 | 458-460 | attribution | The Optiver Realized Volatility Prediction competition was on Kaggle in 2021 | [uncited] | | | Verify year and platform |
| 49 | 460-462 | numerical-fact | Optiver competition: predict 10-minute-ahead realized volatility from limit order book data across over 100 stocks | [uncited] | | | Verify prediction horizon, data type, and number of stocks |
| 50 | 466 | qualitative | LightGBM ensembles dominated the Optiver leaderboard | [uncited] | | | Verify from competition results |
| 51 | 471-472 | qualitative | Optiver winners spent 80% of effort on features and 20% on modeling | [uncited] | | | Anecdotal claim; verify if any top solutions state this |
| 52 | 475-476 | qualitative | Transformer and LSTM models did not beat well-tuned LightGBM on the Optiver public or private leaderboard | [uncited] | | | Verify from top solution write-ups |
| 53 | 479-480 | numerical-fact | Optiver top solutions blended 3-5 LightGBM models with gains from blending of 1-3% | [uncited] | | | Verify blend count and marginal gain from top solution write-ups |
| 54 | 543-547 | numerical-fact | With RV-only features, tree improvement over HAR is 0-5% in QLIKE, often not statistically significant by Diebold-Mariano test | [uncited] | | | Aggregate claim from literature; verify against CSV2023 and others |
| 55 | 549-552 | qualitative | A rolling-window HAR with properly selected window length matches or beats off-the-shelf ML models | HARdToBeat2024 | | | Verify this is the main finding of the paper |
| 56 | 552-553 | qualitative | HAR's advantage comes from its parsimonious structure (3 parameters), well-suited to small, noisy, autocorrelated data | HARdToBeat2024 | | | Verify this interpretation matches the paper |
| 57 | 558 | numerical-fact | With rich features, trees pull ahead by 5-20% in QLIKE | ChristensenSiggaardVeliyev2023 | | | Verify magnitude range; note overlap with claim 44 |
| 58 | 580-584 | qualitative | ML models tend to underperform HAR during extreme events (VIX spikes, flash crashes, pandemic onset) because trees are piecewise-constant and extrapolate poorly | [uncited] | | | General claim; partially supported by RahimikiaPoon2020 |
| 59 | 580-581 | numerical-fact | Rahimikia and Poon's ML model beats HAR on 90% of out-of-sample days but fails catastrophically on the remaining 10% | RahimikiaPoon2020 | | | Verify the 90%/10% split and characterization |
| 60 | 589-593 | qualitative | Many published ML-beats-HAR results use default hyperparameters for HAR while giving the ML model a full tuning budget; when both receive equal care, the gap shrinks or disappears | BrancoRubesamZevallos2024 | | | Verify this is the main argument of Branco, Rubesam, Zevallos (2024) |
| 61 | 763-764 | attribution | DART (Dropouts meet Multiple Additive Regression Trees) was proposed by Vinayak and Gilad-Bachrach | VinayakGilad2015 | | | Verify authors and year; full ref is Rashmi & Gilad-Bachrach (2015) -- check first name |
| 62 | 807-813 | defining-formula | DART normalization: $\hat{y}_t = \sum_{k \notin \mathcal{D}} h_k(\bx_t) + \frac{|\mathcal{D}|}{|\mathcal{D}|+1}\sum_{k \in \mathcal{D}} h_k(\bx_t) + \frac{1}{|\mathcal{D}|+1} h_m(\bx_t)$ | VinayakGilad2015 | | | Verify this normalization formula matches the original DART paper |
