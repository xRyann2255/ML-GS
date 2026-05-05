# ML for Realized Volatility Forecasting -- Project Papers

Papers curated for the GS internship project: ML-based forecasting of realized volatility.

## A. Foundational RV & HAR Baselines

| # | Paper | File | Status |
|---|---|---|---|
| 1 | Corsi (2009), "A Simple Approximate Long-Memory Model of Realized Volatility" (HAR) -- *J. Financial Econometrics* | `corsi-2009-har-realized-volatility.pdf` | **Essential** |
| 2 | Bollerslev, Patton & Quaedvlieg (2016), "Exploiting the Errors" (HARQ) -- *J. Econometrics* | `bollerslev-patton-quaedvlieg-2016-harq.pdf` | **Essential** |
| 3 | Patton & Sheppard (2015), "Good Volatility, Bad Volatility" (SHAR) -- *RestStat* | `patton-sheppard-2015-good-bad-volatility-shar.pdf` | **Essential** |
| 4 | Bollerslev, Patton & Quaedvlieg (2018), "Modeling and Forecasting (Un)Reliable Realized Covariances" -- *J. Econometrics* | `bollerslev-patton-quaedvlieg-2018-unreliable-realized-covariances.pdf` | **Essential** |

## B. ML for RV -- Core Empirical Evidence

| # | Paper | File | Status |
|---|---|---|---|
| 5 | Christensen, Siggaard & Veliyev (2023), "A Machine Learning Approach to Volatility Forecasting" -- *J. Financial Econometrics* | `christensen-siggaard-veliyev-2023-ml-volatility-forecasting.pdf` | **Essential** |
| 6 | "HARd to Beat" (2024), "The Overlooked Impact of Rolling Windows in the Era of Machine Learning" -- arXiv 2406.08041 | `hard-to-beat-2024-ml-vs-linear-rv.pdf` | **Essential** |
| 7 | Bucci (2020), "Realized Volatility Forecasting with Neural Networks" -- *J. Financial Econometrics* | `bucci-2020-rv-forecasting-neural-networks.pdf` | **Essential** |
| 8 | Rahimikia & Poon (2020), "Machine Learning for Realised Volatility Forecasting" -- SSRN/presentation | `rahimikia-poon-2020-ml-rv-forecasting.pdf` | **Essential** |
| 9 | Fed (2025), "Linear and Nonlinear Econometric Models Against Machine Learning" -- FEDS Working Paper | `fed-2025-linear-nonlinear-rv-forecasting.pdf` | **Essential** |

## C. Deep Learning & Foundation Models for RV

| # | Paper | File | Status |
|---|---|---|---|
| 10 | Moreno-Pino & Zohren (2022), "DeepVol" -- arXiv 2210.04797 | `moreno-pino-zohren-2022-deepvol.pdf` | **Essential** |
| 11 | Foundation Time-Series AI Model for RV Forecasting (2025) -- arXiv 2505.11163 | `foundation-model-rv-forecasting-2025.pdf` | **Essential** |
| 12 | Data-Efficient RV Forecasting with Vision Transformers (2025) -- arXiv 2511.03046 | `vision-transformer-rv-2025.pdf` | Recommended |
| 13 | Time-Series Foundation Model for VaR (2024) -- arXiv 2410.11773 | `time-series-foundation-model-var-2024.pdf` | Recommended |
| 14 | Transfer Learning for RV of New Issues & Spin-Offs (2025) -- arXiv 2503.12648 | `transfer-learning-rv-new-issues-2025.pdf` | Recommended |

## D. Multivariate / Graph-Based RV

| # | Paper | File | Status |
|---|---|---|---|
| 15 | Chen & Robert (2022), "Multivariate Realized Volatility Forecasting with Graph Neural Network" -- ACM ICAIF | `chen-robert-2022-gnn-multivariate-rv.pdf` | **Essential** |
| 16 | SpotV2Net (2024), "Multivariate Intraday Spot Volatility via Vol-of-Vol GATs" -- arXiv 2401.06249 | `spotv2net-2024-intraday-vol-gat.pdf` | **Essential** |

## E. Rough Volatility

| # | Paper | File | Status |
|---|---|---|---|
| 17 | Gatheral, Jaisson & Rosenbaum (2018), "Volatility Is Rough" -- *Quantitative Finance* | `gatheral-jaisson-rosenbaum-2018-volatility-is-rough.pdf` | **Essential** |
| 18 | Cont & Das (2024), "Rough Volatility: Fact or Artefact?" -- *Sankhya B* | `cont-das-2024-rough-volatility-fact-or-artefact.pdf` | **Essential** |
| 19 | Rosenbaum & Zhang (2022), "On the Universality of the Volatility Formation Process" -- arXiv 2206.14114 | `rosenbaum-zhang-2022-universality-volatility-formation.pdf` | Recommended |

## Papers Still Needed (paywalled)

- Branco, Rubesam & Zevallos (2024), "Forecasting RV: Does Anything Beat Linear Models?" -- *J. Empirical Finance*
- Andersen, Bollerslev, Diebold & Labys (2003), "Modeling and Forecasting Realized Volatility" -- *Econometrica*
- Barndorff-Nielsen, Hansen, Lunde & Shephard (2008), "Designing Realized Kernels" -- *Econometrica*
- Liu, Patton & Sheppard (2015), "Does Anything Beat 5-Minute RV?" -- *J. Econometrics*
- Hansen, Lunde & Nason (2011), "The Model Confidence Set" -- *Econometrica*
- Bollerslev, Tauchen & Zhou (2009), "Expected Stock Returns and Variance Risk Premia" -- *RFS*

## Data Resources

| Resource | Notes |
|---|---|
| Oxford-Man Realized Library | Daily 5-min RV for ~25 indices (discontinued 2022, archival mirrors exist) |
| VOLARE (2025) | Open-access successor to Oxford-Man |
| Optiver Kaggle (2021) | Free LOB data for intraday RV |
| LOBSTER | L2/L3 NASDAQ LOB (paid academic subscription, free sample) |
| Kevin Sheppard's `arch` | Python: GARCH, HAR, MCS, bootstrap |
| Nixtla NeuralForecast | N-BEATS, N-HiTS, PatchTST, TFT implementations |
| `highfrequency` R package | All major realized estimators, jump tests, multivariate kernels |
