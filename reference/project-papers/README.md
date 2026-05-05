# ML for Realized Volatility — Essential Papers

Papers marked **Essential** are required reading for the project. **Recommended** papers provide useful extensions.

## A. Foundational RV Econometrics

| # | Paper | Status |
|---|---|---|
| 1 | Andersen, Bollerslev, Diebold & Labys (2003), "Modeling and Forecasting Realized Volatility" — *Econometrica* | **Essential** |
| 2 | Barndorff-Nielsen, Hansen, Lunde & Shephard (2008), "Designing Realized Kernels" — *Econometrica* 76 | **Essential** |
| 3 | Zhang, Mykland & Aït-Sahalia (2005), "A Tale of Two Time Scales" — *JASA* | Recommended |
| 4 | Liu, Patton & Sheppard (2015), "Does Anything Beat 5-Minute RV?" — *J. Econometrics* | **Essential** |
| 5 | Patton (2011), "Volatility Forecast Comparison Using Imperfect Volatility Proxies" — *J. Econometrics* | **Essential** |
| 6 | Hansen, Lunde & Nason (2011), "The Model Confidence Set" — *Econometrica* | **Essential** |
| 7 | Lee & Mykland (2008), "Jumps in Financial Markets" — *RFS* | Recommended |

## B. HAR Family (Baselines to Beat)

| # | Paper | Status |
|---|---|---|
| 8 | Corsi (2009), "A Simple Approximate Long-Memory Model of Realized Volatility" — *J. Financial Econometrics* | **Essential** |
| 9 | Bollerslev, Patton & Quaedvlieg (2016), "Exploiting the Errors" (HARQ) — *J. Econometrics* | **Essential** |
| 10 | Patton & Sheppard (2015), "Good Volatility, Bad Volatility" (SHAR) — *RestStat* | **Essential** |
| 11 | Hansen, Huang & Shek (2012), "Realized GARCH" — *J. Applied Econometrics* | Recommended |
| 12 | Barndorff-Nielsen, Kinnebrock & Shephard (2010), "Measuring Downside Risk — Realized Semi-variance" | Recommended |

## C. Rough Volatility

| # | Paper | Status |
|---|---|---|
| 13 | Gatheral, Jaisson & Rosenbaum (2018), "Volatility Is Rough" — *Quantitative Finance* | **Essential** |
| 14 | Cont & Das (2024), "Rough Volatility: Fact or Artefact?" — *Sankhya B* | **Essential** |
| 15 | Rosenbaum & Zhang (2022), "On the universality of the volatility formation process" — arXiv 2206.14114 | **Essential** |
| 16 | Horvath, Muguruza & Tomas (2021), "Deep Learning Volatility" — *Quantitative Finance* | Recommended |

## D. ML for RV — Core Empirical Evidence

| # | Paper | Status |
|---|---|---|
| 17 | Christensen, Siggaard & Veliyev (2023), "A Machine Learning Approach to Volatility Forecasting" — *J. Financial Econometrics* | **Essential** |
| 18 | Rahimikia & Poon (2020), "Machine Learning for Realised Volatility Forecasting" — SSRN 3707796 | **Essential** |
| 19 | Branco, Rubesam & Zevallos (2024), "Forecasting RV: Does Anything Beat Linear Models?" — *J. Empirical Finance* | **Essential** |
| 20 | "HARd to Beat" (2024) — arXiv 2406.08041 | **Essential** |
| 21 | Bucci (2020), "Realized Volatility Forecasting with Neural Networks" — *J. Financial Econometrics* | Recommended |
| 22 | Moreno-Pino & Zohren (2022), "DeepVol" — arXiv 2210.04797 | Recommended |
| 23 | Sirignano & Cont (2019), "Universal features of price formation" — *Quantitative Finance* | Recommended |
| 24 | Chen & Robert (2022), "Multivariate RV Forecasting with Graph Neural Network" — ACM ICAIF | **Essential** |
| 25 | Zhang, Cucuringu & Dong (2024), "Graph-Based Methods for Forecasting Realized Covariances" — *J. Financial Econometrics* | **Essential** |
| 26 | Audrino & Knaus (2016), "Lassoing the HAR Model" — *Econometric Reviews* | Recommended |

## E. VRP and Options-Implied

| # | Paper | Status |
|---|---|---|
| 27 | Bollerslev, Tauchen & Zhou (2009), "Expected Stock Returns and Variance Risk Premia" — *RFS* | **Essential** |
| 28 | Bollerslev, Li & Todorov (2015), "Tail Risk Premia and Return Predictability" — *JFE* | Recommended |

## F. Multivariate / Cross-Asset

| # | Paper | Status |
|---|---|---|
| 29 | Bollerslev, Patton & Quaedvlieg (2018), "Modeling and Forecasting (Un)Reliable Realized Covariances" — *J. Econometrics* | **Essential** |
| 30 | Bollerslev, Li, Patton & Quaedvlieg (2020), "Realized Semicovariances" — *Econometrica* | **Essential** |
| 31 | Diebold & Yilmaz (2009/2012/2014), Connectedness/Spillovers — *Econ. Journal*, *IJF*, *J. Econometrics* | Recommended |

## G. Methodology

| # | Paper | Status |
|---|---|---|
| 32 | López de Prado (2018), *Advances in Financial Machine Learning* — Wiley | **Essential** |

## H. Code & Data

| Resource | Notes |
|---|---|
| Oxford-Man Realized Library | Daily 5-min RV for ~25 indices (discontinued 2022, archival mirrors exist) |
| VOLARE (2025) | Open-access successor to Oxford-Man |
| Optiver Kaggle (2021) | Free LOB data for intraday RV |
| LOBSTER | L2/L3 NASDAQ LOB (paid academic subscription, free sample) |
| Kevin Sheppard's `arch` | Python: GARCH, HAR, MCS, bootstrap. Essential code resource |
| Nixtla NeuralForecast | N-BEATS, N-HiTS, PatchTST, TFT implementations |
| `highfrequency` R package | All major realized estimators, jump tests, multivariate kernels |
