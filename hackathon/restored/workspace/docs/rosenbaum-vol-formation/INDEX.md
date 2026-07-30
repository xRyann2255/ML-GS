# On the Universality of the Volatility Formation Process

**When Machine Learning and Rough Volatility Agree**

Mathieu Rosenbaum, Jianfei Zhang

arXiv:2206.14114v1 [q-fin.ST] 28 Jun 2022

These markdown files are a faithful word-for-word conversion of `Rosenbaum_Vol_Formation (2).pdf`. All equations are reproduced in KaTeX. Figure descriptions replace embedded images. Intended for LLM consumption.

---

## Abstract

We train an LSTM network based on a pooled dataset made of hundreds of liquid stocks aiming to forecast the next daily realized volatility for all stocks. Showing the consistent outperformance of this universal LSTM relative to other asset-specific parametric models, we uncover nonparametric evidences of a universal volatility formation mechanism across assets relating past market realizations, including daily returns and volatilities, to current volatilities. A parsimonious parametric forecasting device combining the rough fractional stochastic volatility and quadratic rough Heston models with fixed parameters results in the same level of performance as the universal LSTM, which confirms the universality of the volatility formation process from a parametric perspective.

**Keywords:** Volatility formation, universality, forecast, LSTM, HAR, rough volatility, quadratic rough Heston, Zumbach

---

## Chapters

| § | Title | File | Summary |
|---|-------|------|---------|
| 1 | Introduction | [ch01-introduction.md](ch01-introduction.md) | Motivation, rough volatility paradigm, universality hypothesis, paper outline. |
| 2 | Description of the Forecasting Devices | [ch02-forecasting-devices.md](ch02-forecasting-devices.md) | AR, HAR, RFSV parametric models (§2.1). LSTM architecture and training (§2.2). |
| 3 | Data and Evaluation Metrics | [ch03-data-evaluation.md](ch03-data-evaluation.md) | Russell 1000 + STOXX 600 dataset, RV/return definitions, scaling, MSE metric. |
| 4 | Capturing Universality with LSTM | [ch04-universality-lstm.md](ch04-universality-lstm.md) | Parametric vs nonparametric (§4.1). Network inspection: sensitivity, sector tests, fine-tuning, cross-market, stability (§4.2). |
| 5 | Uncovering the Universal Volatility Formation Process | [ch05-parametric-universality.md](ch05-parametric-universality.md) | RFSV universality, QRH forecasting device, RFSV+QRH blend matching LSTM performance. |
| 6 | Conclusion | [ch06-conclusion.md](ch06-conclusion.md) | Summary of findings. |
| — | References | [references.md](references.md) | All 31 cited works. |
