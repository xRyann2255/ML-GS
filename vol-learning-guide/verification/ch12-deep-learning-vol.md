# Chapter 12-DL: Deep Learning for Volatility -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 93
**Verified:** 0/93
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 39 | qualitative | The LSTM cell solves the vanishing gradient problem that cripples simple recurrent networks | [uncited] | | | Standard DL textbook claim (Hochreiter & Schmidhuber 1997); verify original motivation |
| 2 | 40 | qualitative | LSTM uses three gates (forget, input, output) and a cell state that acts as a conveyor belt for information | [uncited] | | | Standard architecture description; some formulations count the candidate as a fourth component |
| 3 | 101-102 | defining-formula | Forget gate: $\mathbf{f}_t = \sigma(\mathbf{W}_f [\mathbf{h}_{t-1}; \mathbf{x}_t] + \mathbf{b}_f)$ | [uncited] | | | Standard LSTM equation; verify against Hochreiter & Schmidhuber (1997) or Graves (2013) |
| 4 | 103-104 | defining-formula | Input gate: $\mathbf{i}_t = \sigma(\mathbf{W}_i [\mathbf{h}_{t-1}; \mathbf{x}_t] + \mathbf{b}_i)$ | [uncited] | | | Standard LSTM equation |
| 5 | 105-106 | defining-formula | Candidate cell state: $\tilde{\mathbf{c}}_t = \tanh(\mathbf{W}_c [\mathbf{h}_{t-1}; \mathbf{x}_t] + \mathbf{b}_c)$ | [uncited] | | | Standard LSTM equation |
| 6 | 107-109 | defining-formula | Cell state update: $\mathbf{c}_t = \mathbf{f}_t \odot \mathbf{c}_{t-1} + \mathbf{i}_t \odot \tilde{\mathbf{c}}_t$ | [uncited] | | | Standard LSTM equation |
| 7 | 110-111 | defining-formula | Output gate: $\mathbf{o}_t = \sigma(\mathbf{W}_o [\mathbf{h}_{t-1}; \mathbf{x}_t] + \mathbf{b}_o)$ | [uncited] | | | Standard LSTM equation |
| 8 | 112-113 | defining-formula | Hidden state: $\mathbf{h}_t = \mathbf{o}_t \odot \tanh(\mathbf{c}_t)$ | [uncited] | | | Standard LSTM equation |
| 9 | 131-132 | qualitative | The cell state flows through the network with only linear interactions (multiply and add), so gradients flow back through many time steps without vanishing | [uncited] | | | Standard explanation; note the forget gate values are nonlinear functions but the cell state update is linear in c_{t-1} given f_t |
| 10 | 143 | qualitative | The GRU simplifies the LSTM by merging the forget and input gates into a single "update gate" and eliminating the separate cell state | [uncited] | | | Standard GRU description (Cho et al. 2014); verify structural differences |
| 11 | 144 | qualitative | GRUs have fewer parameters and train faster than LSTMs | [uncited] | | | Generally accepted; verify "fewer parameters" holds for same hidden size |
| 12 | 144 | qualitative | Performance differences between LSTM and GRU are small for volatility tasks | [uncited] | | | No citation given; needs a source comparing LSTM vs GRU on RV |
| 13 | 148 | attribution | Bucci (2020) provides the cleanest comparison of LSTM vs HAR | Bucci2020 | | | Verify paper scope and whether "cleanest" is justified vs other papers |
| 14 | 149 | attribution | Bucci (2020) tests LSTM and NARX networks against HAR for daily RV forecasting across multiple assets | Bucci2020 | | | Verify paper includes LSTM, NARX, HAR; multiple assets |
| 15 | 152-153 | qualitative | LSTM networks are competitive with HAR for daily RV forecasting, but they do not consistently dominate | Bucci2020 | | | Verify this is the paper's conclusion |
| 16 | 153 | qualitative | LSTM gains over HAR are asset-dependent and sensitive to hyperparameter tuning | Bucci2020 | | | Verify this finding |
| 17 | 154 | qualitative | The LSTM's advantage appears mainly during volatile periods when the relationship between past and future RV is nonlinear | Bucci2020 | | | Verify whether Bucci (2020) specifically identifies volatile periods as the source of LSTM gains |
| 18 | 160-161 | attribution | Sirignano and Cont (2019) train a single "universal" LSTM on all stocks simultaneously instead of one per stock | SirignanoCont2019 | | | Verify paper uses LSTM specifically and trains on pooled data |
| 19 | 164 | numerical-fact | The universal LSTM is trained on pooled data across 1,000+ stocks | SirignanoCont2019 | | | Verify the number of stocks in the paper |
| 20 | 164 | qualitative | The universal LSTM learns universal features of price formation | SirignanoCont2019 | | | Verify paper claims "universal features" specifically |
| 21 | 165 | qualitative | Pooling works because volatility dynamics are similar across assets | SirignanoCont2019 | | | Verify this is the paper's stated reason |
| 22 | 166 | qualitative | The pooled model outperforms asset-specific models, especially for assets with short histories | SirignanoCont2019 | | | Verify the "especially for short histories" finding |
| 23 | 172 | numerical-fact | Hurst exponent $H \approx 0.1$ across assets | [uncited] | | | Cross-reference with rough vol chapter; widely cited from Gatheral, Jaisson, Rosenbaum (2018) |
| 24 | 175-176 | attribution | Rosenbaum and Zhang (2022) connect LSTMs directly to rough volatility | RosenbaumZhang2022 | | | Verify paper topic |
| 25 | 176 | qualitative | A universal LSTM trained to forecast volatility learns a kernel that matches the fractional kernel of the RFSV model | RosenbaumZhang2022 | | | Verify paper shows kernel matching |
| 26 | 179 | qualitative | An LSTM learns the power-law kernel $K(t) \propto t^{H-1/2}$ with $H \approx 0.1$ that defines the RFSV model | RosenbaumZhang2022 | | | Verify the specific kernel form and H value recovered |
| 27 | 180 | qualitative | The LSTM and the RFSV forecast are nearly identical | RosenbaumZhang2022 | | | Verify whether the paper claims "nearly identical" forecasts or something weaker |
| 28 | 183 | qualitative | The LSTM was given no prior knowledge of rough volatility, fractional Brownian motion, or Hurst exponents -- it discovered roughness from data alone | RosenbaumZhang2022 | | | Verify the LSTM had no structural priors related to rough vol |
| 29 | 185-186 | attribution | Rahimikia and Poon (2020) add LOB features and news sentiment as inputs to LSTM alongside standard RV lags | RahimikiaPoon2020 | | | Verify paper uses LOB features AND news sentiment with LSTM |
| 30 | 188 | numerical-fact | LSTM incorporating LOB features and news sentiment beats HAR on approximately 90% of trading days | RahimikiaPoon2020 | | | Verify the 90% figure from the paper |
| 31 | 189 | qualitative | The model fails during extreme stress events, precisely when accurate forecasts matter most | RahimikiaPoon2020 | | | Verify the paper documents stress-period failure |
| 32 | 194 | qualitative | The LSTM in Rahimikia and Poon (2020) underperforms HAR during high-volatility episodes because the training data contains few such events | RahimikiaPoon2020 | | | Verify the specific mechanism (few training events) is stated in the paper |
| 33 | 253 | qualitative | LSTMs cannot parallelize across time steps because each step depends on the previous hidden state | [uncited] | | | Standard architectural property; correct by construction |
| 34 | 254 | qualitative | TCNs use causal convolutions: filters that only look backward in time, applied in parallel across the entire sequence | [uncited] | | | Standard TCN description (Bai, Kolter, Koltun 2018) |
| 35 | 260 | supporting-formula | A dilated convolution with dilation factor $d$ and kernel size $k$ covers a receptive field of $k + (k-1)(d-1)$ steps (single layer) | [uncited] | | | Verify this receptive field formula for a single dilated conv layer |
| 36 | 261 | qualitative | By doubling the dilation factor at each layer, the receptive field grows exponentially while the number of parameters grows only linearly | [uncited] | | | Standard TCN property; verify |
| 37 | 323-324 | defining-formula | Dilated causal convolution: $y_t = \sum_{j=0}^{k-1} w_j \cdot x_{t - j \cdot d}$ | [uncited] | | | Standard definition; verify against Bai et al. (2018) or van den Oord et al. (2016) |
| 38 | 329 | methodological | Layer $\ell$ uses dilation factor $d = 2^{\ell-1}$ | [uncited] | | | Standard convention; verify indexing (some use $d = 2^\ell$ from $\ell=0$) |
| 39 | 331 | supporting-formula | With $L$ layers and kernel size $k=2$, the receptive field is $2^L$ time steps | [uncited] | | | RF = 1 + sum_{l=0}^{L-1} (k-1)*2^l = 1 + (2^L - 1) = 2^L for k=2. Correct. |
| 40 | 340 | numerical-fact | With 8 layers and kernel size 2, you cover $2^8 = 256$ time steps | [uncited] | | | Arithmetic: $2^8 = 256$. Correct. |
| 41 | 341 | numerical-fact | One trading day has 78 bars at 5-minute sampling (6.5 hours x 12 bars/hour) | [uncited] | | | 6.5 * 12 = 78. Standard US equity trading day 9:30-16:00 = 6.5 hours. |
| 42 | 353-354 | attribution | Moreno-Pino and Zohren (2022) build DeepVol, a TCN that forecasts daily RV directly from raw intraday returns | MorenoPinoZohren2022DeepVol | | | Verify paper architecture is TCN and input is raw 5-min returns |
| 43 | 354 | methodological | DeepVol feeds raw 5-minute returns into a dilated causal convolution stack and predicts RV_{t+1} end-to-end, bypassing the RV aggregation step | MorenoPinoZohren2022DeepVol | | | Verify the "bypassing RV aggregation" claim |
| 44 | 357 | qualitative | DeepVol achieves state-of-the-art daily RV forecasting | MorenoPinoZohren2022DeepVol | | | Verify SOTA claim in the paper; what metrics and baselines? |
| 45 | 371-375 | supporting-formula | Worked example: $\text{RF} = 1 + \sum_{\ell=0}^{6} 2^\ell = 1 + 127 = 128$ for $L=7$, $k=2$ | [uncited] | | | sum_{l=0}^{6} 2^l = 2^7 - 1 = 127; 1 + 127 = 128. Correct. |
| 46 | 378 | numerical-fact | At 5-minute sampling, one trading day has 78 bars | [uncited] | | | Same as claim 41 |
| 47 | 379 | numerical-fact | 128 / 78 is approximately 1.6 trading days | [uncited] | | | 128/78 = 1.641; rounding to 1.6 is correct |
| 48 | 382-383 | numerical-fact | 5 trading days at 78 bars each = 390 bars | [uncited] | | | 5 * 78 = 390. Correct. |
| 49 | 384 | supporting-formula | $L = \lceil \log_2(390) \rceil = 9$ layers gives RF = 512 steps | [uncited] | | | log2(390) = 8.607; ceil = 9; 2^9 = 512. Correct. |
| 50 | 392 | qualitative | TCN has no vanishing gradient problem by construction (parallel paths through residual connections) | [uncited] | | | Verify: is it purely residual connections, or also the parallel convolution structure? |
| 51 | 393 | qualitative | LSTM is more flexible for variable-length sequences; TCN requires fixed-length input (or padding) | [uncited] | | | Generally accepted; verify TCN truly requires fixed-length input |
| 52 | 394 | qualitative | For fixed-length volatility sequences (e.g., one day of 5-min returns), TCN is generally preferred over LSTM | [uncited] | | | Qualitative preference claim; needs citation or empirical backing |
| 53 | 406 | attribution | Zhang, Zohren, Roberts (2019) ask whether a neural network can learn better features from raw LOB data | ZhangZohrenRoberts2019DeepLOB | | | Verify paper framing |
| 54 | 410 | qualitative | DeepLOB combines CNNs (for spatial features across price levels) with LSTMs (for temporal dynamics across snapshots) | ZhangZohrenRoberts2019DeepLOB | | | Verify DeepLOB architecture: CNN + inception module + LSTM |
| 55 | 462 | methodological | DeepLOB input tensor is $\mathbf{X}_t \in \mathbb{R}^{T \times 10 \times 4}$ with T time steps, 10 price levels, 4 features per level | ZhangZohrenRoberts2019DeepLOB | | | Verify exact input dimensions from the paper |
| 56 | 465 | numerical-fact | DeepLOB uses 10 price levels: 5 best bid and 5 best ask levels | ZhangZohrenRoberts2019DeepLOB | | | Verify number of levels |
| 57 | 466 | methodological | The 4 features per level are: price, volume, price difference from mid, volume difference from mid | ZhangZohrenRoberts2019DeepLOB | | | Verify these exact 4 features against the paper |
| 58 | 473 | qualitative | DeepLOB outperforms hand-crafted LOB features for short-horizon mid-price movement prediction | ZhangZohrenRoberts2019DeepLOB | | | Verify this result |
| 59 | 473 | numerical-fact | DeepLOB evaluated at prediction horizons $k = 10, 20, 50$ ticks | ZhangZohrenRoberts2019DeepLOB | | | Verify these specific horizon values from the paper |
| 60 | 474 | qualitative | The convolutional layers learn features that resemble but improve upon classical order imbalance measures | ZhangZohrenRoberts2019DeepLOB | | | Verify whether the paper performs feature interpretation analysis |
| 61 | 475 | qualitative | DeepLOB generalizes across stocks without retraining | ZhangZohrenRoberts2019DeepLOB | | | Verify cross-stock generalization claim |
| 62 | 479 | qualitative | DeepLOB was designed for mid-price direction prediction (classification), not volatility | ZhangZohrenRoberts2019DeepLOB | | | Verify the original paper's prediction target |
| 63 | 491 | numerical-fact | One trading day at 100ms intervals has $6.5 \times 3{,}600 \times 10 = 234{,}000$ snapshots | [uncited] | | | 6.5 * 3600 = 23,400 sec; * 10 per sec = 234,000. Correct. |
| 64 | 504 | qualitative | Transformers replaced LSTMs as the dominant sequence model in NLP | [uncited] | | | Widely accepted since Vaswani et al. (2017); no specific citation needed |
| 65 | 509-511 | defining-formula | Scaled dot-product attention: $\text{Attention}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{softmax}\left(\frac{\mathbf{Q}\mathbf{K}^\top}{\sqrt{d_k}}\right) \mathbf{V}$ | [uncited] | | | Standard formula from Vaswani et al. (2017) "Attention Is All You Need" |
| 66 | 572-573 | attribution | Chen and Robert (2022) extend the transformer with a graph structure over assets where attention weights define a learned graph | ChenRobert2022 | | | Verify paper uses graph transformer for cross-asset volatility |
| 67 | 581 | qualitative | Transformer variants have been applied to LOB data (TLOB), replacing the LSTM in DeepLOB with multi-head self-attention | [uncited] | | | Needs citation for TLOB; verify this variant exists |
| 68 | 582 | qualitative | TLOB early results are promising but not yet conclusive | [uncited] | | | Needs citation |
| 69 | 589 | numerical-fact | A daily RV series for one asset gives approximately 252 observations per year | [uncited] | | | Standard: ~252 trading days per year in US markets |
| 70 | 590 | numerical-fact | 20 years of daily data is only 5,000 observations | [uncited] | | | 252 * 20 = 5,040; rounding to 5,000 is reasonable |
| 71 | 600 | qualitative | N-BEATS, N-HiTS, TiDE, TSMixer, PatchTST were designed for general time-series forecasting and tested primarily on M4, M5, and Monash archive | [uncited] | | | Verify benchmark datasets for each architecture |
| 72 | 603-604 | qualitative | N-BEATS uses a stack of fully-connected blocks with residual connections, each producing a backcast and forecast, with interpretable basis functions (trend, seasonality) | [uncited] | | | Verify against Oreshkin et al. (2019); confirm backcast/forecast and interpretable basis description |
| 73 | 606 | qualitative | N-HiTS extends N-BEATS with hierarchical interpolation allowing different blocks at different temporal resolutions | [uncited] | | | Verify against Challu et al. (2023) |
| 74 | 608 | qualitative | PatchTST divides the input into non-overlapping patches and treats each as a token for a transformer | [uncited] | | | Verify against Nie et al. (2023); confirm patching mechanism |
| 75 | 611 | qualitative | TiDE and TSMixer use MLP-based architectures simpler and faster than transformers while achieving competitive performance | [uncited] | | | Verify against Das et al. (2023) for TiDE, Chen et al. (2023) for TSMixer |
| 76 | 631 | attribution | Kidger (2021) develops the mathematical framework for embedding SDEs into neural networks | Kidger2021NeuralSDE | | | Verify this is the correct reference (likely PhD thesis or NeurIPS paper) |
| 77 | 633-634 | defining-formula | Neural SDE: $dX_t = f_\theta(X_t, t)\,dt + g_\theta(X_t, t)\,dW_t$ | Kidger2021NeuralSDE | | | Standard neural SDE form; verify against Kidger (2021) |
| 78 | 662 | methodological | Training neural SDEs requires backpropagation through the SDE solver (adjoint method) | Kidger2021NeuralSDE | | | Verify adjoint method is the approach described in Kidger (2021) |
| 79 | 671 | attribution | Ding, Lu, Cheung (2025) use autoencoders to compress the IV surface into a low-dimensional latent space | DingLuCheung2025 | | | Verify paper topic and methodology |
| 80 | 681 | numerical-fact | Typical IV surface autoencoder latent dimensions are $d = 3$ to $8$, compressing surfaces of about $20 \times 10 = 200$ values to fewer than 10 numbers | DingLuCheung2025 | | | Verify latent dimension range from the paper |
| 81 | 685 | qualitative | Autoencoder latent dimensions often correspond to interpretable factors: level (parallel shift), slope (term structure tilt), and smile (convexity across strikes) | DingLuCheung2025 | | | Verify whether the paper identifies these specific factors, or if this is PCA/SSVI general knowledge being attributed |
| 82 | 692-693 | attribution | Xu and Chen (2021) propose a deep stochastic volatility model combining classical stochastic vol structure with neural networks, using variational (VAE-like) inference | XuChen2021 | | | Verify paper methodology |
| 83 | 698 | attribution | Du, Moriyama, Tanaka, Ishii (2023) use normalizing flows co-trained with a VAE to model the full distribution of future RV | DuMoriyamaTanakaIshii2023 | | | Verify paper uses normalizing flows + VAE for RV distribution |
| 84 | 702-703 | defining-formula | Normalizing flow forward: $\mathbf{x} = T_K \circ T_{K-1} \circ \cdots \circ T_1(\mathbf{z})$ where $\mathbf{z} \sim \mathcal{N}(\mathbf{0}, \mathbf{I})$ | [uncited] | | | Standard normalizing flow formula; verify against Rezende & Mohamed (2015) |
| 85 | 706-707 | defining-formula | Normalizing flow log-density: $\log p(\mathbf{x}) = \log p(\mathbf{z}) - \sum_{k=1}^{K} \log \lvert \det \frac{\partial T_k}{\partial T_{k-1}} \rvert$ | [uncited] | | | POTENTIAL ERROR: Standard form uses Jacobian $\partial T_k / \partial \mathbf{x}_{k-1}$ (derivative of transform w.r.t. its input), not $\partial T_k / \partial T_{k-1}$. The notation as written is ambiguous/incorrect. |
| 86 | 783 | numerical-fact | An LSTM has 50,000 parameters vs HAR's "three coefficients" | [uncited] | | | HAR has 4 parameters (intercept + 3 coefficients), not 3. Text says "three coefficients" which is technically the coefficient count excluding intercept, but potentially misleading. |
| 87 | 787 | qualitative | The "tabular data advantage" of gradient-boosted trees over neural networks is well-documented | [uncited] | | | Commonly cited (Grinsztajn et al. 2022, Borisov et al. 2022); no specific citation given in text |
| 88 | 807 | numerical-fact | 52 weekly observations per year | [uncited] | | | 52.14 weeks/year; 52 is correct approximation |
| 89 | 819 | numerical-fact | A 2-layer LSTM with 64 hidden units has approximately 50,000 parameters | [uncited] | | | Depends on input dimension. For input dim $d$: layer 1 = $4(64 \cdot d + 64^2 + 64)$, layer 2 = $4(64^2 + 64^2 + 64) = 33,024$. With small $d$ (say 1-10), total is roughly 33K-36K + 33K = 66K-69K. The 50K figure may be low. |
| 90 | 820 | numerical-fact | A HAR model has 4 parameters | [uncited] | | | Intercept + 3 RV lag coefficients = 4. Correct. |
| 91 | 821 | numerical-fact | A LightGBM with max_depth=4 and 200 trees has approximately 3,000 leaf values | [uncited] | | | Max leaves with depth 4 = $2^4 = 16$; $200 \times 16 = 3{,}200$. Approximation of 3,000 is reasonable. |
| 92 | 822 | numerical-fact | A daily RV series with 2,500 observations spans 10 years | [uncited] | | | 252 * 10 = 2,520; rounding to 2,500 is reasonable |
| 93 | 822 | numerical-fact | With 50,000 LSTM parameters and 2,500 observations, the ratio is 20 parameters per observation | [uncited] | | | 50,000 / 2,500 = 20. Arithmetically correct given the premises. |
