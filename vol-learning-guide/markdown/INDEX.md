# Realized Volatility: Estimation, Forecasting, and ML

**A Learning Guide**

Ryan Vincent

These markdown files are a faithful word-for-word conversion of `vol-learning-guide/main.pdf`, with TikZ diagrams recreated as Mermaid. Worked examples are omitted. Intended for LLM consumption on restricted machines.

---

## Part I: What Is Volatility and How Do You Measure It?

| Ch. | Title | Summary |
|-----|-------|---------|
| [1](ch01-returns-variance-volatility.md) | Returns, Variance, and Volatility | Log vs simple returns, variance, conditional heteroskedasticity, stylized facts of volatility. |
| [2](ch02-realized-volatility.md) | Realized Volatility | Integrated variance, realized variance from intraday returns, sampling frequency, log-RV. |
| [3](ch03-microstructure-noise.md) | Microstructure Noise | Bid-ask bounce, signature plot, noise-robust estimators: TSRV, MSRV, pre-averaging, realized kernel. |
| [4](ch04-jumps-continuous-variation.md) | Jumps and Continuous Variation | BPV, C/J decomposition, jump detection tests (BNS, Lee-Mykland), signed jumps, truncated RV. |

## Part II: Forecasting Volatility with Classical Models

| Ch. | Title | Summary |
|-----|-------|---------|
| [5](ch05-garch-family.md) | The GARCH Family | ARCH, GARCH(1,1), EGARCH, GJR-GARCH, FIGARCH. MLE estimation, forecasting, news impact curves. |
| [6](ch06-har-model.md) | The HAR Model and Its Extensions | Heterogeneous Market Hypothesis. HAR-RV, HAR-J, HAR-CJ, SHAR, HARQ, HAR-RS. The primary baseline. |
| [7](ch07-rough-volatility.md) | Rough Volatility | Fractional Brownian motion, Hurst exponent (H~0.1), RFSV, rough Bergomi, fractional differencing. |

## Part III: The Volatility Surface and Options-Implied Information

| Ch. | Title | Summary |
|-----|-------|---------|
| [8](ch08-options-vol-surface.md) | Options and the Volatility Surface | Implied volatility, smile/skew, vol surface (delta x tenor), Greeks, local volatility. |
| [9](ch09-variance-risk-premium.md) | The Variance Risk Premium | VRP definition, risk-neutral vs physical measure, VIX, VRP as forecasting feature, variance swaps. |

## Part IV: ML Methods for Volatility

| Ch. | Title | Summary |
|-----|-------|---------|
| [10](ch10-feature-engineering.md) | Feature Engineering for Volatility | Layer structure (0-7), triple expansion, horizon-dependent selection, feature pipeline design. |
| [11](ch11-tree-methods-vol.md) | Tree Methods for Volatility | Decision trees, random forests, gradient boosting, LightGBM, custom QLIKE loss, SHAP. |
| [12](ch12-rashomon-interpretable-trees.md) | Rashomon and Interpretable Trees | Optimal sparse trees (STreeD), Rashomon sets, TreeFARMS/RESPLIT, Variable Importance Clouds, RID. |
| [12b](ch12b-deep-learning-vol.md) | Deep Learning for Volatility | RNNs, LSTMs, GRUs, TCN, attention/transformers, DeepVol, DeepLOB for vol forecasting. |
| [13](ch13-hybrid-ensemble.md) | Hybrid and Ensemble Methods | Stacking vs blending, feature- vs prediction-level fusion, LightGBM+LSTM architecture, GINN. |

## Part V: Multivariate Volatility and Connectedness

| Ch. | Title | Summary |
|-----|-------|---------|
| [14](ch14-multivariate-volatility.md) | Multivariate Volatility | Realized covariance, DCC-GARCH, BEKK, factor models, DRD, GNN for covariance forecasting. |
| [15](ch15-spillovers-connectedness.md) | Spillovers and Connectedness | Diebold-Yilmaz spillover index, VAR variance decomposition, network connectedness, Graph-HAR. |

## Part VI: Evaluation and Practice

| Ch. | Title | Summary |
|-----|-------|---------|
| [16](ch16-forecast-evaluation.md) | Forecast Evaluation | QLIKE, MSE, MAE loss functions. Diebold-Mariano test, Model Confidence Set. Purged CV, walk-forward. |
| [17](ch17-applications-projects.md) | Applications and Projects | Vol-targeting, risk parity, momentum scaling. Practical applications of vol forecasts. |
| [18](ch18-ivrv-straddle.md) | From Forecast to P&L: A Realistic, Evaluable IV--RV Straddle | Delta-hedged straddle on the IV-RV gap, gamma P&L identity, option/hedge transaction costs, Leland, discrete-hedging-error variance, realized kurtosis, deflated Sharpe. |
| [19](ch19-gsvivs01.md) | Predicting Drawdowns of a Daily Variance-Swap Seller: The GSVIVS01 Index | Variance-swap re-derivation (DDKZ log-contract, 1/K^2 strip, CBOE formula, skew premium), the real GSVIVS01 0DTE replication strategy, strike-based VRP-gap signal, down-jump cubic drawdown mechanism, cost-sensitive classification, flat/short overlay, deflated-Sharpe economic value. |

---

## Quick Reference

**Chapters:** 20 files (across 6 parts; numbered 1-19 with a 12b)

**Key progression:** Measurement (Ch 1-4) -> Classical forecasting (Ch 5-7) -> Options-implied info (Ch 8-9) -> ML methods (Ch 10-13) -> Multivariate/network (Ch 14-15) -> Evaluation and practice (Ch 16-19)

**Baseline model:** HAR-RV (Ch 6) -- every ML model must beat this

**Primary metric:** QLIKE (Ch 16) -- penalizes relative forecast errors, not absolute
