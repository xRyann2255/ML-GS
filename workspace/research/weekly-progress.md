# Weekly Progress Log

**Project:** ML Realized Volatility Forecasting - Signal Discovery
**Team:** STS XA
**Format:** Reverse-chronological. Each week has four sections: Shipped, Decided, Learned, Next week. Written in plain language for manager readability.

## Milestones

<!-- Update status when a milestone completes. Source of truth: workspace/docs/vol-project-ref/ch18-development-plan.md -->
<!-- Multiple milestones can be ACTIVE simultaneously (DAG, not linear). -->

| Milestone | Description | Status |
|---|---|---|
| **M0** | Research and scoping | DONE |
| **M1** | Data infrastructure | DONE |
| **M2** | Feature engine and baselines | DONE |
| **M3** | LightGBM (custom QLIKE objective) | ACTIVE |
| **M4** | Tournament (8 models x 3 horizons, DM tests) | ACTIVE (linear tournament done, LightGBM + LSTM pending) |
| **M5** | Layer 2 options-implied features | DONE |
| **M6** | Layers 4-5 cross-asset and calendar | DONE |
| **M7** | Signal (IV-RV gap, OOS Sharpe) | ACTIVE |
| **M8** | Ensemble (stacking + blending) | ACTIVE (LSTM residual stacking built, awaits GPU run) |
| **M9** | Microstructure and sequences (L3, LSTM) | ACTIVE (v2 stationary features shipped, GPU run pending) |
| **M10** | Stretch (Rashomon, regime QLIKE, full universe) | NOT STARTED |

<!-- Critical path: M3 → M4 → M8 → M10. M5/M6/M9 branch from M2 in parallel. M7 requires M4 + M5. -->

<!--
TEMPLATE (copy for each new week):

## Week N: Mon DD - Fri DD, YYYY

**Shipped**
- [what was built, completed, or delivered - plain language, no jargon]

**Decided**
- [key decisions made and brief rationale]

**Learned**
- [insights, findings, surprises from research or implementation]

**Next week**
- [planned focus for the coming week]

STYLE: Write so a non-technical reader can follow. Avoid acronyms, library names,
function signatures, and statistical test names. Describe WHAT was done and WHY,
not the technical HOW.
-->

---

## Week 11: Jul 1, 2026

**Shipped**
- Restructured the capstone presentation to incorporate a rough draft of all slides, giving it a complete narrative arc from problem definition through results
- Researched and implemented XGBoost as a new decision tree model alongside the existing LightGBM: validated it across multiple random seeds and confirmed it as the new daily-horizon champion (beating LightGBM by 76 basis points)
- Diagnosed and solved the root cause of poor LSTM performance: the QLIKE loss function causes vanishing gradients when applied directly to long intraday sequences, making the network unable to learn meaningful patterns
- Built a new feature-stacking architecture that trains the LSTM independently on intraday sequences, then feeds its learned representations as additional features into XGBoost — achieving a new best QLIKE score with a trading Sharpe ratio of 2.81

**Decided**
- XGBoost replaces LightGBM as the primary tree model for the daily forecast horizon based on both single-seed and multi-seed validation
- The LSTM should never be trained end-to-end with QLIKE on raw sequences; instead it should be used as a feature extractor whose outputs are consumed by the tree model
- Feature stacking (LSTM outputs as XGBoost inputs) is the correct integration path, not residual learning or prediction blending — it lets XGBoost decide how much weight to give the sequence signal

**Learned**
- QLIKE loss applied directly to LSTM outputs causes vanishing gradients because the loss landscape is extremely flat near zero (where residuals live), starving the network of learning signal during backpropagation
- XGBoost has much lower seed variance than LightGBM on our dataset (2.5 basis points envelope vs 79 basis points), making it more reliable for single-run experiments
- The combination of a sequence model (captures intraday volatility shape) and a tree model (captures cross-sectional and daily feature interactions) produces orthogonal signals that genuinely stack — unlike previous attempts where LSTM outputs were redundant with existing features
- Sample reweighting schemes (up-weighting hard-to-predict days) did not improve XGBoost performance, suggesting the model already allocates its capacity efficiently across easy and hard samples

**Next week**
- Run the feature-stacked model across all three forecast horizons (daily, weekly, monthly) to confirm the improvement generalizes
- Test whether richer LSTM input features (adding realized vol and volume profiles to the 5-minute sequences) further improve the stacked signal
- Begin integrating the new champion model into the trading signal pipeline to update the live Sharpe comparison against the baseline strategy

---

## Week 9: Jun 15-18, 2026

**Shipped**
- Redesigned the intraday bar features so they are immune to stock splits: instead of feeding raw prices into the sequence model, each ten-second bar is now described by five quantities (return, volume share, buy ratio, trade count, absolute return) that are unchanged when a stock splits
- Ingested the new split-safe bar features for all twenty-nine symbols, replacing the old raw-price bars that had ten-to-one jumps on split dates
- Built a per-stock normalisation option so the sequence model can standardise each stock's bars separately rather than lumping all stocks together; defaults to pooled for now but switchable via one config line
- Added regularised versions of the linear baseline models (ridge, lasso, elastic net) across all three forecast horizons and all implied-volatility tenors, creating over thirty new model variants for the linear tournament
- Ran a large linear model tournament (trial-055/056) testing forty-plus linear model variants to find whether a more complex linear starting point can improve the tree model: found that a five-parameter model including separate estimates for calm-day and jump-day volatility plus short-dated options prices beats the current four-parameter baseline at the daily horizon by about three basis points
- Used the tournament winners as new starting points for the tree model (trial-057 config): the daily and monthly horizons now have richer linear foundations while the weekly horizon keeps its current best
- Cleaned up the codebase: removed over 1,600 lines of obsolete scripts and archived memory files, deleted thirty old experiment configs that were completed or superseded
- Overhauled the experiment runner to execute cross-validation folds in parallel across processor cores, cutting wall-clock time for multi-fold experiments
- Enhanced the tournament dashboard with richer economic value reporting and side-by-side comparison tables
- Improved all data ingestion commands with incremental fetching and better error recovery so re-runs only download what changed
- Refreshed implied volatility surfaces and tick data for all symbols through the latest available dates

**Decided**
- Stock-split contamination in the raw sequence data is fully resolved by using return-based features rather than patching the underlying price files
- The regularised linear tournament showed that simple ridge or lasso does not meaningfully improve the four-parameter baseline at any horizon; the gains come from adding orthogonal decompositions (calm-day vs jump-day volatility, measurement quality) rather than from regularisation alone
- The sequence model should be validated with a standalone run first before layering it on top of the tree model as a residual corrector
- Per-stock normalisation is available but not the default; switch it on only if the model produces flat predictions for high-volatility stocks

**Learned**
- Raw tick-derived bar files stored unadjusted prices from the data vendor; every stock that split during the training window had a discontinuity that would corrupt any model using price levels directly
- The five return-based bar features are split-invariant by construction because they use ratios and fractions rather than absolute values
- Adding a continuous-versus-jump volatility decomposition to the linear baseline gives a small but real improvement at the daily horizon, confirming that separating calm-day persistence from jump-day spikes helps even a simple model
- Parallel fold execution uncovered a subtle issue where the graphics card compilation mode was re-compiling for every batch due to variable-length sequences; fixed by enabling dynamic shape support

**Next week**
- Run the LSTM sequence model on the graphics card (trial-057 LSTM residual or trial-052 v2 standalone) and compare against the current tree model champion
- Run the tree model with the new tournament-winning linear starting points (trial-057 LightGBM config) and check whether the richer base translates to better tree corrections
- Begin designing the economic-value-aware training objective that penalises missed profitable short trades more heavily than the current symmetric error metric

---

## Week 8: Jun 8-12, 2026

**Shipped**
- Added a new command that prints the side by side GSVIVS signal results for each available implied volatility source
- Reused the current cached data and signal logic so the new output stays aligned with the main research code instead of a separate scratch script
- Added two new summary columns showing the average implied volatility level and its day to day variation for each source
- Switched the execution-based implied volatility cache to a daily horizon so it now compares like for like against the daily realized volatility series

**Decided**
- The new comparison command should be a thin reporting layer over the existing implementation, not a second copy of the volatility logic
- The two day expiry variants are included only when the intraday raw variance swap file is available, while the core command still works from the normal caches alone
- The execution-based implied volatility series should use a full-day horizon by default because the signal compares implied and realized volatility on a daily basis

**Learned**
- The current command output is sensitive to which dates survive the shared overlap across all volatility sources, especially when the optional two day expiry variants are included
- The execution-based variance swap cache still materially changes the ranking, so refreshing that cache will directly change the comparison table without any code change
- Using the raw same-day option life makes the execution-based implied volatility look too high versus realized volatility even when the trade parsing is correct; the issue was horizon mismatch rather than stale data

**Next week**
- Refresh the execution-based variance swap cache so the new command reflects the corrected time to expiry values
- Decide whether the comparison table should also be embedded directly into the HTML dashboard
- Use the new command to compare signal behavior before and after any cache refreshes

### Update 2026-06-11

**Shipped**
- Ran a new experiment that trains the model on a much longer history including the early 2020 crisis to see if it would learn to recognize stressed market periods
- Pulled the actual Sharpe numbers and short-selling rates from the backtest dashboard for the new experiment and the previous champion side by side
- Recorded the full result in the trial registry and added a note in the research journal so future sessions do not re-test the same idea

**Decided**
- Reject the new long-history experiment as a replacement for the current champion: the simpler error metric got better but the dollar-and-cents trading result got worse
- Going forward, any experiment that changes how the training window is sliced must report the error metric on the same out-of-sample dates as the baseline; otherwise the comparison is misleading
- Shift the next round of experiments away from improving the statistical error metric and toward directly improving the trading Sharpe ratio

**Learned**
- A model that gets a better statistical score can still produce a worse trading outcome because the trading payoff is asymmetric: missing a profitable short on a quiet day costs the full premium, but the statistical score does not penalize that
- Training on the historical crisis period made the model more cautious about going short, which lowered the short-trade rate and skipped some of the most profitable days
- A large part of the apparent statistical improvement was a side effect of testing on a calmer market window rather than a true model improvement, the same artifact seen in an earlier experiment

**Next week**
- Design a training objective that directly penalizes missed profitable shorts instead of just minimizing the statistical error metric
- Test the untried features that have been queued (the short-dated to one-week implied vol ratio) using the new methodology rule about fixed evaluation windows

### Update 2026-06-12

**Shipped**
- Built a new model type that reads each trading day as a sequence of small ten-second bars (volume bought, volume sold, net flow, average price, trade count) instead of a single daily summary number
- Wired the new model into the existing experiment runner so the user can train it the same way as the linear and tree models, just by changing one line in a configuration file
- Added a caching layer that converts each symbol's raw ten-second bar file into a fast-loading tensor on first use so re-runs do not pay the conversion cost twice
- Built the model to automatically detect and use a graphics card when one is present, with all the speed optimizations enabled, but fall back gracefully to the regular processor when no card is available
- Added a full safety net of automated tests covering the new caching layer, the model itself, and the experiment runner; all 147 tests pass including everything that existed before
- Confirmed the full pipeline works end to end by running a tiny throwaway experiment on two symbols for one year that completed in a few minutes and produced a valid result in the dashboard
- Prepared a full production configuration ready to launch on the graphics card once access is confirmed, covering all twenty-one symbols and all three forecast horizons over ten years of history

**Decided**
- The new model is treated as a standalone competitor in the tournament rather than blended with the existing models, so its individual performance can be measured cleanly against the current champion
- Run the first serious experiment on the graphics card rather than the regular processor because the bars-per-day count is large and processor-only training would take too long to iterate on
- Use the same training and testing date windows as the previous champion experiment to keep the comparison fair and avoid the methodology pitfall identified last week

**Learned**
- Running this kind of sequence model on a regular processor with all available cores actually slows it down because the many cores compete for cache, so future processor runs should restrict the thread count manually
- The cache files for two symbols over three years take about 230 megabytes; for the full universe and full history this will need a few gigabytes of disk space
- The model can be trained, saved, and reloaded between sessions, so partial training runs can be resumed without starting over

**Next week**
- Run the full production experiment on the graphics card once access is available and compare the result against the current champion
- If the result is competitive, explore richer per-bar features and longer per-day sequences (currently capped at the standard trading day length)
- If the result is weak, decide whether to invest in tuning the sequence model further or shelve it and return to the planned economic-value-aware experiments

## Week 7: Jun 2-6, 2026

**Shipped**
- Added 1-week implied volatility tenor to the data pipeline (38 of 39 symbols covered)
- Built a new linear baseline that uses short-dated options prices matched to the forecast window
- Ran two experiments comparing the new approach against the existing monthly options approach
- Created a locked production configuration that uses the best approach per forecast horizon

**Decided**
- Short forecast windows (1 day, 1 week) should use 1-week options prices; monthly forecasts keep the existing 1-month options prices
- Created a locked configuration file that applies the best approach per forecast horizon
- New best scores across all three horizons, improving by 55 to 71 basis points over the previous best

**Learned**
- Matching the options expiry to the forecast window is a free improvement requiring no extra model complexity
- The machine learning model can partially compensate for using the wrong options tenor, but not fully (97 bps linear gap shrinks to 8-46 bps for trees)
- All three forecast horizons now have new best scores: daily improved by 55 points, weekly by 71, monthly by 69

**Next week**
- Validate the locked configuration with a full run
- Test robustness across multiple random seeds
- Consider adding the options term slope as a direct input feature (not just through the baseline)

---

## Week 7: Jun 1, 2026

**Shipped**
- Built per-horizon training window support: each forecast horizon (daily, weekly, monthly) now uses its own independently tuned training window length
- Expanded the model training universe from 21 to 23 stocks (added JPM and QQQ)
- Ran 8 experiments testing different training window and universe combinations
- Discovered and documented a critical measurement bias: the apparent improvements from longer training windows were entirely caused by excluding the volatile early-2020 period from the test set
- Three unit tests covering the new per-horizon feature

**Decided**
- The default training window remains 2 years (504 days) for all horizons. Longer windows do NOT improve forecast quality when measured on the same test period
- Excluded META from the expanded universe due to a data quality mismatch (trading data covers a different date range than options data). JPM and QQQ are clean
- All future experiment comparisons must evaluate on a common test period, or report results both with and without the early-2020 crisis period. This prevents false conclusions from non-overlapping evaluation windows

**Learned**
- RETRACTED: the earlier claim of "monotonic improvement with longer windows" was a measurement artifact. The volatile period of early 2020 inflates forecast error by about 52 basis points. Longer training windows push the start of the test period past this crisis, making results look better without actually improving the model
- On the same test period (January 2022 through July 2024), a 2-year training window and a 7-year training window produce identical forecast accuracy (zero difference)
- When using expanding-window cross-validation, different training window lengths produce non-overlapping test sets. This makes raw accuracy numbers incomparable across configurations unless restricted to common dates
- Monthly volatility forecasting has an optimal window of exactly 2 years. Both shorter (less data) and longer (regime confusion) windows produce worse results
- Adding more stocks to the training pool helps cross-sectional variation but the benefit is modest and confounded with test-period changes

**Next week**
- Explore new feature layers (microstructure data from order books, cross-asset spillovers) since training window optimization is now a dead end
- Design a fixed holdout protocol that avoids the test-period comparability trap
- Consider explicit crisis-period handling (separate regime model, or exclusion flag) as a feature rather than ignoring it

---

## Week 6: May 26-30, 2026

**Shipped**
- Fixed the automated hyperparameter search that was freezing on the high-performance computing node (208-core server with 2 GPUs)
- The search now completes 10 trials in 4 minutes (previously: infinite hang, zero trials completed)
- Removed all GPU code from the training pipeline (proven unnecessary for our approach)
- Documented root causes and optimal settings in research notes to prevent recurrence

**Decided**
- GPU acceleration is permanently abandoned for this project. Our custom loss function forces a data transfer between CPU and GPU every training iteration, making GPU slower than CPU-only
- Fixed the thread count at 8 (was incorrectly set to "use all 208 cores"). Benchmarks showed 8 threads is optimal across all data sizes
- Set parallel trials to 4 (higher causes memory crashes). This uses 32 of 208 cores but completes faster due to reduced contention

**Learned**
- The training library (LightGBM) with a custom loss function and 208 threads on 2,000 rows takes 4+ minutes per fit. The exact same fit with 8 threads takes 0.4 seconds. The 600x slowdown is caused by thread synchronization overhead: 208 threads coordinating to process 10 rows each is slower than 8 threads processing 250 rows each
- GPU training with custom loss functions is counterproductive because gradients are computed in Python on CPU, then transferred to GPU for tree building, then predictions come back. The transfer cost per iteration (which happens thousands of times) eliminates any GPU speedup
- The training library has a fatal bug where aggressive parameter combinations cause an uncatchable crash that silently kills worker threads. The automated search then hangs forever waiting for dead workers. Fixed by validating parameters before training and capping parallelism
- The thread count vs performance relationship is inverse-U shaped: performance peaks at 4-8 threads regardless of how many CPU cores are available. This is a universal property of tree-based methods on small-to-medium datasets (under 50K rows)

**Next week**
- Launch the full 200-trial hyperparameter search now that it actually works
- Evaluate whether tuned parameters beat the hand-tuned configuration that currently holds the best score (0.1574)
- Begin horizon-specific configurations for the weekly and monthly forecasts that still lag behind simple baselines

---

## Week 5: May 19-23, 2026

**Shipped**
- Ran the first gradient-boosted tree model experiment against the baseline volatility forecasters
- Tested 8 different tree complexity configurations ranging from maximally simple (single-split stumps) to moderately complex (depth 5, 31 leaf nodes)
- Built a reusable comparison framework that evaluates any number of model variants on matched out-of-sample data
- Ran a full data integrity audit of all cached files: confirmed 25 of 34 symbols available, identified a stale options-derived feature cache, and mapped which data layers are ready for experiments
- Diagnosed why the previous overnight tuning run appeared stuck (nested optimization was doing 48,000 model fits, would take 7-13 hours)
- Killed orphaned processes consuming 2.6 GB of memory from stuck prior sessions

**Decided**
- Single-stock tree model experiments are a dead end: with only 500-1500 training rows and 60 features, no tree configuration can compete with simple regularized linear models
- The correct test for tree models requires pooling all 21 available symbols together (giving 30,000+ training rows)
- Paused tree-specific hyperparameter tuning and boosting variant tests until pooled experiments show the model can compete at all
- Downgraded model tuning complexity: the first priority is proving trees add value with enough data, not optimizing tree architecture on insufficient data

**Learned**
- Tree-based models fail catastrophically on small volatility datasets regardless of configuration. Even a depth-1 stump ensemble (the simplest possible tree) loses by 5,400+ basis points against a regularized linear model. The issue is not overfitting from complex trees - it is that trees cannot find meaningful conditional splits with so few observations per feature
- The feature expansion step (which triples the feature count from 20 to 60 by adding change and z-score variants) makes the problem worse by diluting the useful signal across more columns. This expansion is designed for large datasets
- At longer forecast horizons (weekly, monthly), even the mildest complexity beyond a 3-parameter baseline hurts on single-stock data. The simplest model wins when data is scarce
- The stale options feature cache (3 corrupted columns, 2 missing) can be regenerated from existing raw data without any network connectivity

**Next week**
- Run the tree model in pooled mode across all 21 symbols to test if more training data unlocks the expected improvement
- Regenerate the stale options feature cache to unblock the implied volatility feature layer
- Test whether adding a single market-wide fear indicator (VIX) gives the tree model enough signal to beat linear baselines even on small data

---

## Week 4: May 12-16, 2026

**Shipped**
- Built the command-line interface so experiments can run end-to-end from a single command: fetch data, train model, evaluate results
  - Three composable steps (fetch data, train, evaluate) that also work individually for debugging
  - One-shot mode chains all three steps automatically
  - Model artifacts and predictions saved to disk so you can re-evaluate without retraining
- Added model persistence (save/load trained models) so results are reproducible across sessions
- Created a path resolution layer that makes all file paths work correctly regardless of which directory you run from
- Fixed a wiring bug where the model and feature registries were empty (import ordering issue)
- Fixed the pipeline return type annotation (was string-keyed, actually integer-keyed)
- Created the first example experiment configuration file (baseline volatility model on SPY)
- 15 new automated tests covering the full CLI flow (now 342 total passing)
- Completed all remaining Layer 0-1 features (8 implementation gaps closed, 28 new tests, now 370 total):
  - Triple expansion utility that systematically produces level/change/z-score variants for tree models
  - Intraday jump detection that identifies specific price jumps within each trading day (Lee-Mykland test)
  - Signed jump features that separate positive jumps from negative jumps (negative jumps predict higher future volatility)
  - Realized skewness and kurtosis from intraday returns (higher moments for crash-risk detection)
  - Overnight return and lagged daily return as standard predictors
  - Standalone measurement-quality feature always available for tree model splits
  - Bias correction for converting log-space forecasts back to variance levels
- Fixed a failure in the data-loading step where the main fetch could succeed but the command still stopped before finishing because an optional daily-price lookup had not been initialized
- Fixed a major performance bottleneck in the noise-correction calculation so one full trading day of high-volume market data now finishes quickly enough to cache locally
- Completed the full model comparison and evaluation toolkit (32 new tests, now ~420 total):
  - Pairwise statistical test that determines whether one forecast significantly outperforms another
  - Forecast efficiency test that checks whether predictions are unbiased (slope=1, intercept=0)
  - Model Confidence Set that identifies the group of models statistically tied for best performance
  - Tournament table that combines all metrics and tests into a single ranked comparison
  - Tournament runner that orchestrates all seven baseline models across the development universe and three forecast horizons
  - Pretty-print display that highlights which models survive the statistical cut
- Ran the first real-data tournament: all 7 baseline models on SPY across 3 forecast horizons with statistical significance tests and model confidence sets
- Fixed a bug where all models were using the same full feature matrix instead of their own theoretical feature sets, causing several models to produce identical predictions
- Added a dedicated tournament command that runs all models in one go and produces a ranked comparison table with statistical tests
- Added three zero-parameter naive baselines (yesterdays value, monthly average, historical mean) to the tournament for context on how much value the models actually add
- 13 new automated tests (now ~440 total passing)

**Decided**
- CLI requires live data connectivity for fetching (no synthetic fallback mode) since the goal is real experiments, not demos
- All experiment output grouped by experiment name in a structured directory (models, predictions, metrics all together)
- Deprecated the standalone feature-building command since the pipeline already handles feature construction internally
- Resolved the ensemble architecture debate: feature stacking (feeding deep learning outputs into tree models) preferred at short horizons, simple averaging at long horizons
- Treat the daily-price add-on during ingestion as best-effort enrichment rather than a hard requirement to finish the command
- The next ingestion optimization pass should be staged: first stream fetch and compute by batch, then parallelize compute, then expose tuning knobs, and only then add cross-symbol concurrency

**Learned**
- The wrapper script changes the working directory before invoking Python, which breaks any relative path constants. Discovered this during compatibility audit before implementation, avoided a subtle bug
- Python's "from X import Y" inside a function creates a local variable that testing frameworks cannot override. Must use "import X; X.Y()" pattern instead for testability
- The feature and model registries rely on import side-effects (decorators that fire on module load). If you import the pipeline runner without importing the models package first, everything looks empty. Fixed by ensuring the top-level package always triggers registration
- The locally cached daily volatility files were being written correctly even when the command later failed during the optional daily-price step. The visible failure masked a successful cache write
- Each forecasting model was blindly regressing on all available features instead of selecting its own theoretical feature set. This caused models that should differ (plain versus jump-aware versus semivariance-based) to produce identical predictions. Fixed by adding per-model feature selection
- Ran the first real tournament on SPY data (1,695 days, 10 years). Regularized models (Lasso, Ridge) clearly dominate unregularized OLS baselines. Simple naive forecasts (yesterday's value, monthly average) are surprisingly competitive at certain horizons, raising questions about how much value linear models actually add beyond capturing mean reversion

**Next week**
- Investigate whether the semivariance and RQ-interaction models are truly underperforming or have implementation bugs
- Verify that all models in the tournament are evaluated on exactly the same out-of-sample dates
- Begin LightGBM experiments if baseline results hold up after verification

---

## Week 3: May 5-9, 2026

**Shipped**
- Built the core math engine for computing and forecasting daily stock volatility (56 automated tests, all passing)
  - Module for breaking down volatility into daily, weekly, and monthly components
  - Module for detecting sudden price jumps vs. normal market fluctuations
  - Module for filtering out microstructure noise from raw tick data
  - 7 baseline forecasting models of increasing complexity
  - Scoring functions to measure how accurate each forecast is
- Converted the repo from a prior project into the vol forecasting framework
- Set up the AI-assisted development workflow (17 reasoning personas, 7 pipeline skills)
- Imported 22 research summary cards from the literature survey

**Decided**
- Shifted to a research-first approach instead of planning sprints upfront (spent 8 days planning without touching real data, which was the wrong approach)
- Will use 5-minute sampling intervals to measure daily volatility (academic research shows fancier methods don't actually improve forecasts)
- Gradient-boosted trees (LightGBM) as the main model since it consistently beats neural networks on tabular financial data
- Deep learning reserved only for processing raw intraday tick sequences from E-mini futures

**Learned**
- Looked at past ML competitions for volatility prediction. Tree-based models dominated. Neural networks never beat well-tuned tree models on this type of data
- The top predictive features were things like price acceleration (how fast prices are speeding up), volume patterns, and bid-ask spread behavior
- Found and fixed a subtle bug pattern in how the forecasting model aligns yesterday's data with tomorrow's target

**Next week**
- Connect to live tick data for the first time
- Plot how volatility estimates change at different sampling frequencies to validate our 5-minute choice
- Run the first baseline forecast on real equity data

---

## Week 2: Apr 28 - May 2, 2026

**Shipped**
- Reviewed ~80 academic papers on volatility forecasting across 11 topic areas
- Defined the project scope: 34 stocks/ETFs, 11+ years of market history
- Designed the feature architecture: 7 layers of predictive signals, from basic price patterns up to cross-market indicators
- Wrote the evaluation plan: how to measure forecast quality and statistically compare models
- Wrote the project design document: code structure, data flow, and implementation order

**Decided**
- Chose a loss function (QLIKE) that penalizes underestimating volatility more heavily, which is important for risk management
- Organized features into 7 layers from simple to complex (price patterns, jump detection, options market signals, microstructure, cross-asset, calendar events, interaction effects)
- Will use time-aware cross-validation (not random splits) to avoid lookahead bias when testing models
- COVID period (Feb-Jun 2020) needs special handling since it represents an extreme regime

**Learned**
- Good features matter more than fancy models for this problem
- Downside price moves are much more predictive of future volatility than upside moves
- Volatility spills over across asset classes (e.g., bond market stress predicts stock volatility)

**Next week**
- Start building the computation modules
- Get hands on real data before going further with the pipeline

---

## Week 1: Apr 21-25, 2026

**Shipped**
- Set up the project repository
- Wrote a volatility learning guide covering the key concepts
- Configured the development environment (Python, VS Code, tooling)
- Evaluated 4 candidate directions for the internship project

**Decided**
- Selected ML Realized Volatility Forecasting as the internship project
- Adopted an AI-assisted development workflow for faster iteration

**Learned**
- Fundamentals of realized volatility: how it's measured, why it has long memory, and the standard forecasting approaches
- Mapped out the available data sources at GS: tick-level trades, daily time series, and options-implied volatility surfaces

**Next week**
- Deep literature survey across all feature layers
- Define project scope, stock universe, and success criteria
