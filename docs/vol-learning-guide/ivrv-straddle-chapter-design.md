# Design: Capstone Chapter — "From Forecast to P&L: A Realistic, Evaluable IV–RV Straddle"

**Date:** 2026-06-01
**Status:** Design (awaiting user review → writing-plans)
**Target:** `vol-learning-guide/chapters/18-ivrv-straddle.tex` (new), appended to Part 6 "Evaluation and Practice" after ch17.
**Source brief:** `notes/deep-research/2026-06-01-realistic-ivrv-straddle-backtest.md` (24 verified sources; page/section anchored).
**Chapter label:** `\label{ch:ivrv-straddle}`

---

## 1. Goal

Teach — from first principles, intuitively, and with every formula reproduced *exactly* as in its source paper — how to build the **most realistic version** of a delta-hedged straddle strategy driven by an IV–RV-gap (variance-risk-premium) signal, and how to evaluate it cleanly (pooled + deflated Sharpe) with an explicit link back to the QLIKE accuracy of the underlying realized-volatility forecast.

The chapter is the book's **capstone**: it threads the whole guide together — a realized-vol forecast (Parts 1–4) becomes a VRP signal (ch09), is traded through a cost-and-friction-aware backtest (new material + ch17), and is judged with the evaluation machinery of ch16. It answers the question every forecasting chapter implicitly raises: *"My model beats HAR by 40 bps of QLIKE — does that make money, and how would I prove it?"*

## 2. Teaching philosophy (load-bearing — the user explicitly asked for this)

This is **not** a formula dump. Every formula must be taught: *what it is in plain English*, *why it appears here*, *what each symbol means* (defined on first use, bolded), and *what it would feel like to get it wrong*. Concretely:

- **Naïve → realistic narrative spine.** Start from the textbook straddle backtest a student would write first. Each section adds one layer of realism and explicitly names what the naïve version got *standard*, *flawed/outdated*, or *missing* — mirroring the original research framing.
- **Intuition before algebra.** Every quantitative section opens with an `intuition` box (analogy / plain-English picture) *before* the formula, and closes with "what breaks if you ignore this."
- **Worked examples are mandatory** for the hard mechanics (gamma-P&L over a few days; a cost-band Sharpe; a hedging-error-variance number with a concrete κ).
- **Define every term on first use.** Vanna, volga, half-normal, χ², granularity, leptokurtic, deflation — each bolded and explained the first time, even if used loosely elsewhere.
- **Exact-formula fidelity.** Each displayed equation carries an inline source anchor in a comment and in prose (e.g., "Ahmad–Wilmott 2005, Eq. 1, p. 67"). Where the book already derives something, **cross-reference rather than repeat** (see §8).
- **Honesty boxes.** The chapter's signature intellectual content is *correcting* a common error (the Ahmad–Wilmott misattribution) and being honest about where borrowed results break on intraday data. Those are `warning`/`keyresult` boxes, not footnotes.

## 3. Placement and dependencies

- **Insert** in `main.tex` after `\input{chapters/17-applications-projects}`, still inside `\part{Evaluation and Practice}`.
- **Why end-of-book:** it consumes ch09 (gamma-P&L, VRP), ch16 (QLIKE, DM, MCS, deflated Sharpe), and ch17 (transaction costs, turnover, Sharpe drag). Placing it last means **zero forward references** — every tool it uses already exists behind it.
- **Prereq box** (chapter opener) points at: `\Cref{sec:greeks}`, `\Cref{sec:var-swap}` (ch08); `\Cref{sec:vrp-definition}`, `\Cref{sec:gamma-pnl}` (ch09); `\Cref{sec:eval-qlike}`, `\Cref{sec:eval-dsr}`, `\Cref{sec:eval-dm}` (ch16); `\Cref{sec:net-econ-value}` (ch17).

## 4. The strategy in plain English (so this spec is self-contained)

Hold a **straddle** (one call + one put, same strike/expiry) and continuously **delta-hedge** it with the underlying, so the position is a near-pure bet on *variance*: you make money if realized variance exceeds the variance implied by the option price, and lose if it falls short. The **signal** is the IV–RV gap: when lagged implied vol $\IVol_{t-1}$ exceeds the model's realized-vol forecast $\widehat{\RV}_t$, options look rich → **short** the straddle (harvest the variance risk premium); when implied is below the forecast, options look cheap → **long** it. The realism comes from charging honest option and hedging transaction costs, accounting for the variance the discrete hedge itself injects, and evaluating with a Sharpe that has been *deflated* for the number of strategy variants tried.

## 5. Section-by-section design

Each row: purpose → what is taught & why → exact formulas (with anchors) → boxes/figures/cross-refs. Component numbers map to the 7 facets of the research question.

### §18.1 The strategy in one picture *(intuition; no new formula)* — Component 1 framing
- **Teach:** the trade, why a *straddle* (delta-neutral ⇒ isolates vega/gamma ⇒ a clean variance bet), why *delta-hedged* (strip out direction), and the IV–RV-gap decision rule. Connect to VRP economics (`\Cref{ch:vrp}`): shorting the rich straddle = collecting the variance risk premium.
- **Rule (prose + keyidea):** short if $\IVol_{t-1} > \widehat{\RV}_t$, long if $\IVol_{t-1} < \widehat{\RV}_t$.
- **Boxes/figs:** `intuition` (insurance-seller analogy, reuse ch09's framing by reference); **Fig A** — pipeline flow diagram (forecast → signal → trade → hedge → daily MTM → evaluate).

### §18.2 The signal and the anti-lookahead protocol — Component 1
- **Teach:** how to turn two numbers into a tradeable, lookahead-safe signal; why the lag convention matters more than the functional form.
- **Formulas (exact):**
  - Signal: $X_{t-1} = f(\widehat{\RV}_t, \IVol_{t-1})$ with $f \in \{x-y,\ x/y,\ \ln(x/y)\}$ — Pollok 2025, §3.2–3.3, Eq. 17 (arXiv 2506.07928).
  - Unit alignment: de-annualize implied vol by $\IVol/\sqrt{250}$ to put it in daily RV units before differencing — Pollok 2025.
  - **Lookahead-safe timing protocol:** predictor measured in the information set up to 3:55 pm ET on day $t$ ($x_t \in \mathcal F_t^{3:55}$); execute before the 4 pm close on $t$; realize returns on $t+1$ — Pollok 2025, abstract + §3.
  - Sizing: graded/confidence-scaled position size dominates both binary delta-neutral and maximally-aggressive scaling — Li & Wu 2026 (FRL 87:109098). **Caveat box:** this is a *directional* single-ETF ML result, cite only for "moderate scaling > binary."
- **Cross-ref:** VRP operational definition `\Cref{eq:vrp-operational}` (don't redefine VRP); lookahead taxonomy `\Cref{sec:eval-lookahead-taxonomy}`, `\Cref{tab:lookahead-taxonomy}`.
- **Boxes:** `keyidea` (the protocol as a timeline), `warning` (the four lookahead traps, by reference).

### §18.3 The P&L engine: the gamma identity and its assumptions — Component 2
- **Teach:** *why* a delta-hedged option's daily P&L is a clean bet on realized-minus-implied variance, weighted by dollar gamma; *what* every symbol is; *when* the identity is exact.
- **Formulas (exact):**
  - Daily mark-to-market of an option hedged at *implied* vol: $\;d\Pi = \tfrac{1}{2}\,(\sigma^2 - \tilde\sigma^2)\,S^2\,\Gamma^{i}\,dt\;$ — **Ahmad–Wilmott 2005, Eq. 1, p. 67**, where $\sigma$ = realized (actual) vol, $\tilde\sigma$ = implied vol, $\Gamma^{i}$ = gamma evaluated at implied vol.
  - Total P&L (path integral): $\;\Pi = \tfrac{1}{2}\!\int_{t_0}^{T} e^{-r(t-t_0)} (\sigma^2-\tilde\sigma^2)\,S^2\,\Gamma^{i}\,dt\;$ — "always positive but highly path-dependent" (AW 2005, §4).
  - Dollar-gamma $(\sigma^2 - \sigma_h^2)$ identity — Carr (2005)/Henrard (2003), as reproduced in AW 2005, Eq. 2, p. 67.
  - The reader's discretized daily form: $\;\text{PnL}_t \approx \tfrac12\,\Gamma_t\,S_t^2\,\big(\RV_t - \IVol^2/252\big)\;$ where $\RV_t$ is day-$t$ realized **variance**.
- **Cross-ref + harmonize:** ch09 `\Cref{eq:gamma-pnl-simple}` ($\tfrac12\Gamma S^2(\RV^2-\IVol^2)T$, vol-form) and `\Cref{eq:daily-gamma-pnl}`. Explicitly reconcile ch09's vol notation ($\RV$ = vol so $\RV^2$ = variance) with the variance-form used here; one sentence + a footnote.
- **Boxes/figs:** `workedexample` (P&L over 3–5 days, building on ch09's example by reference); **Fig B** — dollar-gamma weight $S^2\Gamma$ vs spot (peaks ATM, decays in the wings) to make "path-dependent" visual.

### §18.4 Where the clean identity breaks: vanna, volga, jumps, discreteness — Component 2 (cont.)
- **Teach:** the identity above assumes a single near-ATM option on a continuous (no-jump) diffusion, hedged continuously. Name every assumption and what relaxing it costs.
- **Formulas (exact; vanna/volga are NEW to the guide — standard Black–Scholes Greeks):**
  - **Vanna** $= \dfrac{\partial^2 V}{\partial S\,\partial\sigma} = \dfrac{\partial\,\text{vega}}{\partial S} = -e^{-q\tau} N'(d_1)\,\dfrac{d_2}{\sigma}$ — sensitivity of delta to vol (skew/correlation exposure).
  - **Volga (vomma)** $= \dfrac{\partial^2 V}{\partial\sigma^2} = \text{vega}\cdot\dfrac{d_1 d_2}{\sigma}$ — convexity in vol (vol-of-vol exposure).
  - Variance-swap contrast: the *log contract* removes the $S^2\Gamma$ path-dependence via a static strip of OTM options weighted $1/K^2$ plus a dynamic $1/S$ position — Carr–Madan 2002, grounded in Carr–Lee 2009 (Annu. Rev. Fin. Econ.), Eqs. 9–10, pp. 323–328. Leading jump/discretization error is **third order in the daily return** (Carr–Lee 2009, Eq. 9). Cross-ref ch08 `\Cref{sec:var-swap}`, `\Cref{eq:model-free-var}`.
  - Continuous-vs-discrete hedging: RMSE of the tracking error $= g/\sqrt{N} + O(1/N)$, and $\sqrt{N}\cdot(\text{error}) \Rightarrow$ a mixed-normal (conditionally Gaussian) limit driven by the integrated squared dollar-gamma — **Bertsimas–Kogan–Lo 2000, Thm 1(c), Eq. 2.13, pp. 10–11; granularity $g$ in Eq. 2.18, p. 13.** Vanilla (piecewise-linear) straddle payoffs are governed by **their Theorem 2 (Eq. 2.17, p. 12)**, not Theorem 1 (which requires a 6×-differentiable payoff).
- **Boxes:** `keyidea` (vanna/volga as "the second-order exposures the single-straddle bet quietly carries"); `warning` ("a single straddle is NOT a clean variance bet off-strike — that's what the variance swap fixes").

### §18.5 Option transaction costs: bid–ask → vega, event-driven — Component 3
- **Teach:** how to charge the *option* spread honestly; why event-driven (entry/flip/exit) beats daily amortization but is still optimistic vs quoted; why this single assumption can flip the strategy's sign.
- **Formulas / facts (exact):**
  - Vol-point spread to premium via vega: $\;c_{\text{opt}} = \text{vega}\cdot \tfrac12(\sigma_{\text{ask}}-\sigma_{\text{bid}})\;$, charged only on entry, flip, and exit.
  - Cost levels — **Muravyev–Pearson 2015/RFS 2020** (intro, pp. 1–3): quoted 8.1¢, conventional effective 6.2¢, timing-aware effective 1.3¢ (= 21% of effective, 16% of quoted). Strategy-level: a long–short straddle decile collapses **22.7% → 3.9%/month** at the quoted spread (p. 6).
  - Maturity-resolved schedule — **Doshi–Pari–Shamsuddin 2025** (Table 2, p. 46; p. 19): effective spread ≈ 2% of premium at 21–48 DTE ATM SPX, ≈ 3.5% at 7–13 DTE, ≈ 9% at 0DTE; "up to 10%" is the stressed upper bound; 3rd-Friday roll-date spike; cross-venue routing helps single names but **not** CBOE-exclusive SPX.
  - Practitioner modeling — **François et al. 2025** (§4.1, Eq. 1; arXiv 2504.06208): option cost = a percentage $\kappa_2\in\{0.5,1,1.5,2\}\%$ per position change vs underlying $\kappa_1=0.05\%$. **Wysocki–Słepaczuk 2024** (§2.3, Table 1; arXiv 2407.13908): fill at midpoint + half the bid–ask on every execution, both legs.
- **Cross-ref:** ch17 `\Cref{sec:net-econ-value}` for the equity/futures cost mechanics (turnover, Sharpe drag) — don't repeat; extend to options.
- **Boxes/figs:** `warning` (make-or-break: report a cost *band*, not a point estimate); **Fig D** — Sharpe vs cost assumption (quoted / effective / timing-aware) sensitivity band.

### §18.6 Delta-hedge costs: Leland (1985) and its modern critique — Component 4
- **Teach:** the classic closed-form way to fold hedging costs into a single "modified volatility," its derivation logic (half-normal expected move), and why modern work demotes it from *optimal policy* to *baseline*.
- **Formulas (exact):**
  - **Leland 1985 modified volatility:** $\;\hat\sigma^2 = \sigma^2\!\left(1 + \sqrt{\tfrac{2}{\pi}}\,\dfrac{k}{\sigma\sqrt{dt}}\right)$ — reproduced in Zhao–Ziemba 2003, Eq. 5, p. 8; $\sqrt{2/\pi}\approx0.798$ is the mean of the half-normal (the expected absolute delta move $\E|\Delta H|$), $k$ = round-trip proportional cost, $dt$ = revision interval.
  - Hedge cost per day $\approx (\text{spread})\times \E|\Delta H| \times N$ hedges, with $\E|\Delta H|$ from the half-normal.
  - **Kabanov–Safarian 1997** (Finance Stoch. 1:239–250): under *constant* (n-independent) costs, the Leland portfolio does **not** converge to the payoff — the limiting hedging error is nonzero and negative (systematic under-hedging).
  - **Lepinette–Kabanov 2010** (Finance Stoch. 14(4):625–667, Thm 1.2 Eq. 1.11 / Thm 1.3 Eq. 1.16): with $k_n = k_0\,n^{-1/2}$, MSE → 0 at rate $n^{-1}$ (RMSE $n^{-1/2}$) for **convex** payoffs (a straddle is convex).
  - Frontier alternatives (state, brief): Whalley–Wilmott no-transaction band $\;h_{WW} = \big(\tfrac{3\lambda\,\delta\,S\,\Gamma^2}{2\gamma}\big)^{1/3}$ — Arzel–Lehdili 2026 (arXiv 2603.29994); NN hedger beats Leland at 0.5% cost, codes $\nu^2 = \sigma^2 + \alpha/\sqrt{dt}$, "costs do not apply at inception or maturity" — Brugière–Turinici 2025 (arXiv 2505.22836).
- **Cross-ref:** ch17 turnover `\Cref{eq:turnover-vt}`, Sharpe drag `\Cref{eq:sharpe-drag}`.
- **Boxes:** `warning` ("Leland is a deterministic cost-line inflator, not the optimal trading policy"); `keyidea` (why $\sqrt{2/\pi}$ shows up — the half-normal).

### §18.7 Discrete-hedging-error variance: an honest Sharpe denominator — Component 5 *(signature section)*
- **Teach:** the discrete hedge injects its own zero-mean noise; its *variance* must inflate the Sharpe denominator. Derive it cleanly, label exactly whose result each piece is, and correct a widespread misattribution.
- **Formulas (exact):**
  - **Boyle–Emanuel 1980** per-rebalance hedging error: $\;H_i = \tfrac12\,\Gamma\,S^2\,\sigma^2\,dt\,(x_i^2 - 1)\;$ with $x_i\sim\mathcal N(0,1)$ so $x_i^2 \sim \chi^2_1$ (skewed, leptokurtic *per step*; Gaussian only after aggregation). Total standard deviation over $N$ rebalances $\;\propto \tfrac12 S^2\sigma^2 (T-t)\,\Gamma\sqrt{1/N}\;$. (Reproduced in Anagnou–Hodges 2007, Eq. 7, p. 9; χ² statement pp. 12–13. For Gaussian, $\Var(x_i^2)=2$.)
  - **κ-inflation — the reader's own leptokurtic extension, derived in-chapter, NOT cited:** substitute $\Var(x_i^2) = \kappa - 1$ (kurtosis $\kappa$; Gaussian $\kappa=3 \Rightarrow 2$) into Boyle–Emanuel to get aggregate hedging-error variance $\;\propto \sigma^4\,(\kappa-1)/N\;$. Must be presented as a `keyresult` *with a derivation*, flagged "your extension, not in Boyle–Emanuel, Anagnou–Hodges, or Ahmad–Wilmott."
  - **The misattribution correction (prominent `warning`):** Ahmad–Wilmott 2005's closed-form variance "Result 2" $= G(S_0,t_0) - F(S_0,t_0)^2$ (§4.2, Eq. 10, p. 70) is a *continuous-hedging stock-path* variance with **no $1/N$ and no kurtosis term** — the words "kurtosis/Boyle/Emanuel" do not appear. The $1/N$-and-kurtosis discrete-rebalancing variance is **Boyle–Emanuel (1980)** plus the κ-extension, *not* Ahmad–Wilmott.
  - Vega packaging (practitioner, context-only): $\;\sigma_{\text{P\&L}} = \text{vega}\cdot\sigma\cdot\sqrt{\pi/(4N)}\;$ — Bennett, *Trading Volatility*, p. 95. Note the coefficient tension: $\sqrt{\pi/4}\approx0.886$ (half-normal $\E|\cdot|$) vs $1/\sqrt2\approx0.707$ (L2 std), depending on whether you report mean-absolute or L2.
  - **Where $1/N$ breaks — Broden–Tankov 2010** (arXiv 1003.0709): for pure-jump Lévy, $\lim_n n\,\E[\varepsilon_T^2] > 0$ and may be infinite; for vanilla calls/puts the $1/N$ rate survives but with a jump-inflated constant; for digital/barrier payoffs the rate is strictly slower than $1/\sqrt N$. ⇒ deterministic $1/N$ inflation is a **lower bound** once gaps/jumps are admitted.
- **Cross-ref:** deflated-Sharpe denominator usage in §18.10.
- **Boxes/figs:** `keyresult` (the κ-inflation, with derivation); `warning` (the misattribution); **Fig C** — hedging-error std vs $N$ (the $1/\sqrt N$ curve) with a Broden–Tankov jump floor overlaid.

### §18.8 Calibrating kurtosis κ from 5-minute data — Component 6
- **Teach:** how to estimate the κ that feeds §18.7, why realized kurtosis is trustworthy where realized variance is noisy, and why a flat κ = 4 is a defensible but imperfect convention.
- **Formulas / facts (exact):**
  - Realized kurtosis from intraday returns: $\;RK_t = \dfrac{n\sum_{i} r_{t,i}^4}{\big(\sum_i r_{t,i}^2\big)^2}\;$ — **Amaya–Christoffersen–Jacobs–Vásquez 2015** (JFE 118(1):135–167). Robust to microstructure noise (RV is the noise-sensitive moment, not the quartic RM4); verified under jump-robust RV and subsampling.
  - 5→15-min CLT aggregation; realized higher moments are **interval-variant** — they do not converge to sample skew/kurtosis and depend on the holding + sampling interval — **Ahadzie–Jeyasreedharan 2020** (Quant. Finance 20(7):1169–1184).
  - κ = 4.0 is conservative but cross-sectionally heterogeneous (systematically high for small-cap, high-B/M, low-beta single names).
- **Boxes:** `warning` ("κ = 4 is a convention, not a measurement; estimate per symbol and stress it"); `workedexample` (an $RK$ number from a toy day of 5-min returns).

### §18.9 Assembling the backtest: the algorithm — Build artifact
- **Teach:** put §§18.2–18.8 together into one precise, runnable loop. This is the "most realistic version."
- **Content:** an **algorithm box** (`keyidea`, numbered steps), per (symbol, day):
  1. Measure $\widehat{\RV}_t$, $\IVol_{t-1}$ pre-3:55 pm; form $X_{t-1}$; decide short/long/flat and graded size.
  2. On entry/flip/exit, charge option cost $c_{\text{opt}}$ (§18.5).
  3. Intraday: delta-hedge on the chosen schedule ($N$ rebalances), charging hedge cost (§18.6).
  4. Daily MTM via the gamma identity (§18.3).
  5. Accumulate per-(symbol, day) P&L; attach a hedging-error variance term (§18.7) using the calibrated κ (§18.8).
- **Boxes/figs:** **Fig E (recommended)** — P&L-attribution waterfall: gross gamma P&L − option cost − hedge cost − hedging-error drag = net.

### §18.10 Evaluation: from QLIKE to deflated Sharpe — Component 7
- **Teach:** how to aggregate per-(symbol, day) P&L into a defensible Sharpe, deflate it honestly, and connect it back to forecast accuracy.
- **Formulas / facts (exact):**
  - **Pooled vs per-symbol:** pooling (symbol, day) inflates $N$ and ignores cross-sectional dependence on common-vol days; per-symbol averaging discards the cross-section. Report both; **block-bootstrap by day**, not by observation.
  - **Deflated Sharpe — Bailey–López de Prado 2014** (cross-ref ch16 `\Cref{eq:dsr}`, `\Cref{eq:expected-max-sr}`; restate, do not re-derive):
    $\;\DSR = \Phi\!\Big(\tfrac{(\widehat{\SR}-\SR_0)\sqrt{T-1}}{\sqrt{1-\gamma_3\widehat{\SR}+\frac{\gamma_4-1}{4}\widehat{\SR}^2}}\Big)$ (Eq. 2, p. 8), with the expected-max threshold $\SR_0 = \sqrt{\Var[\SR_n]}\big[(1-\gamma)Z^{-1}(1-\tfrac1N) + \gamma\,Z^{-1}(1-\tfrac{1}{Ne})\big]$, $\gamma\approx0.5772$ (Eq. 1, p. 7).
  - **Three application traps (`warning`):** (a) the denominator uses the **observed** $\widehat{\SR}$, not $\SR_0$; (b) inputs are **non-annualized** at native frequency, $T$ = number of observations; (c) for $N=20$ variants the approximation $\SR_0=\sqrt{2\ln 20}=2.45$.
  - **QLIKE → economic bridge — Pollok 2025:** marginal forecast-error improvements can produce economically significant portfolio gains, while it is hard to beat the benchmark on QLIKE alone; economic evaluation separates models that statistical loss cannot. Pollok uses MSE/MAE/QLIKE/MZ-R² but **not** DM or MCS — so the formal "DM/MCS-significant QLIKE gain ⇒ guaranteed straddle-P&L gain" theorem does **not** exist and must be tested (§18.11). Cross-ref ch16 `\Cref{sec:eval-qlike}`, `\Cref{sec:eval-dm}`, `\Cref{sec:eval-mcs}`.
  - **Economic foundation — Bakshi–Kapadia 2003** (RFS 16(2):527–566): mean delta-hedged gain < 0 (negative volatility risk premium); smaller away-from-money, larger in high-vol, survives jump controls. Cross-ref ch09.
- **Boxes:** `warning` (the three DSR traps + honest $N$); `application` (the QLIKE→money bridge as the chapter's punchline).

### §18.11 What to compute on our data: four experiments — Build artifact
- **Content (`projectconnection` box, each with an explicit pass criterion):**
  1. **Hedging-error floor.** 5-min bar-by-bar simulation, $N\in\{1,\dots,26\}$, fit $\Var(\text{error}) = a/N + b$. If the floor $b>0$ materially (and $\sigma^4(\kappa-1)/N$ lies below the sim at high $N$), report the *simulated* variance in the Sharpe denominator, not the analytic one. Resolve κ first; test DSR sensitivity to $\kappa\in\{3,4,6\}$.
  2. **Cost-band Sharpe.** Pooled Sharpe under (a) full quoted half-spread, (b) Doshi maturity-resolved (~2% at 21–48 DTE), (c) timing-aware ~⅓ quoted. Credible only if it survives (a) or at least (b). Up-weight roll-date spreads as a robustness check.
  3. **Statistical → economic link.** Regress per-(symbol, day) P&L on $(\RV-\IVol^2/252)$ and on forecast error $(\RV-\widehat{\RV})$; test whether the QLIKE-better model's residual edge is DM-significant *and* predicts cross-sectional Sharpe.
  4. **Sharpe definition + deflation.** Compute pooled and per-symbol Sharpe; block-bootstrap by day; report DSR with honest $N$ = number of model variations actually tried.

### §18.12 Summary & honest caveats
- Key-results recap (`keyresult`): the strategy, the gamma engine, the corrected hedging-error variance, the cost band, the deflated-Sharpe gate.
- **Single biggest caveat (`warning`):** every economic-value source cited here is daily-frequency and 1993–2023; the intraday 5-min hedging-error and cost mechanics (§§18.5–18.8) must be confirmed by the reader's own bar-by-bar simulation, not borrowed.

## 6. Figures (TikZ / pgfplots, matching house style in `preamble.tex`)

| Fig | Where | What | Type |
|---|---|---|---|
| A | §18.1 | Strategy pipeline: forecast → signal → trade → hedge → MTM → evaluate | TikZ flow (`flowblock`/`decisionblock` styles) |
| B | §18.3 | Dollar-gamma weight $S^2\Gamma$ vs spot (peaks ATM, decays in wings) | pgfplots |
| C | §18.7 | Hedging-error std vs $N$: $1/\sqrt N$ curve + Broden–Tankov jump floor | pgfplots |
| D | §18.5 | Sharpe vs cost assumption (quoted / effective / timing-aware) | pgfplots bar/line |
| E (recommended) | §18.9 | P&L-attribution waterfall (gross − option cost − hedge cost − hedging-error drag = net) | TikZ/pgfplots |

## 7. New `references.bib` entries

All new (verified absent from `vol-learning-guide/references.bib`):

`Pollok2025`, `LiWu2026`, `AhmadWilmott2005`, `CarrMadan2002`, `CarrLee2009`, `BertsimasKoganLo2000`, `BoyleEmanuel1980`, `AnagnouHodges2007`, `BrodenTankov2010`, `Leland1985`, `ZhaoZiemba2003`, `KabanovSafarian1997`, `LepinetteKabanov2010`, `ArzelLehdili2026`, `BrugiereTurinici2025`, `WysockiSlepaczuk2024`, `MuravyevPearson2020`, `DoshiPariShamsuddin2025`, `AmayaEtAl2015`, `AhadzieJeyasreedharan2020`, `BakshiKapadia2003`.

Reused (already present): `Bailey2014DSR`, `BTZ2009`, `BekaertHoerova2014`, `BollerslevTodorov2015`, `Carr2009`, `Bennett2014`, `Patton2011`, `Bailey2014PBO`, `Fouhy2024`.

Bib metadata is sourced from the brief's evidence table + acquired PDFs in `reference/project-papers/`.

## 8. Cross-reference map (verified labels — reference, never repeat)

- **ch08 `ch:volsurface`:** `sec:greeks`, `sec:var-swap`, `eq:varswap-payoff`, `eq:vega-notional`, `eq:model-free-var`, `sec:vix-index`, `eq:vix`.
- **ch09 `ch:vrp`:** `sec:vrp-definition`, `eq:vrp-operational`, `eq:vrp-theoretical`, `sec:gamma-pnl`, `eq:daily-gamma-pnl`, `eq:cumulative-gamma-pnl`, `eq:gamma-pnl-simple`.
- **ch16 `ch:evaluation`:** `sec:eval-qlike`/`eq:qlike`, `sec:eval-mz`/`eq:mz`, `sec:eval-dm`/`eq:dm-stat`, `sec:eval-mcs`, `sec:eval-dsr`/`eq:dsr`/`eq:expected-max-sr`, `sec:eval-purgedcv`, `sec:eval-lookahead-taxonomy`/`tab:lookahead-taxonomy`, `sec:ch16:cpcv`, `sec:ch16:pbo`.
- **ch17 `ch:applications`:** `sec:net-econ-value`, `eq:net-pnl-vt`, `eq:turnover-vt`, `eq:sharpe-drag`, `eq:breakeven`, `sec:dealer-gamma`, `eq:gex`.

**Do NOT re-derive in this chapter:** Black–Scholes/Greeks (ch08), variance swap & log contract & 1/K² strip (ch08), VRP definition/economics & the base gamma-P&L identity (ch09), QLIKE/MZ/DM/MCS/purged-CV/DSR closed form (ch16), turnover/Sharpe-drag/breakeven cost mechanics (ch17). **Define fresh:** vanna, volga, half-normal hedge-cost logic, Boyle–Emanuel discrete-hedging error + κ-extension, option-spread→vega costing, kurtosis-from-5-min, pooled-vs-per-symbol Sharpe, the QLIKE→P&L bridge.

## 9. Conventions & tooling

- **Boxes:** use the existing `intuition`, `keyidea`, `definition`, `warning`, `prereq`, `workedexample`, `application`, `keyresult`, `projectconnection` (no new tcolorbox types).
- **Macros:** reuse `\RV`, `\IVol`, `\VRP`, `\QLIKE`, `\SR`, `\DSR`, `\Var`, `\E`, `\N` from `preamble.tex`. Add chapter-local macros only if needed (e.g., `\Vega`, `\Vanna`, `\Volga`) — declare in preamble if reused, else `\ensuremath` inline.
- **Citations:** `\citep`/`\citet` with `natbib`; bib at guide root.
- **No packages in the chapter file** (preamble owns them).
- **Authoring:** use the project `write-chapter` skill to draft `18-ivrv-straddle.tex`. After drafting, compile (`pdflatex → bibtex → pdflatex ×2`), then run `convert-chapter-markdown` for the markdown mirror and `sync-docs` if updating `docs-only`.
- **Style rules (from CLAUDE.md):** open with a concrete question; first box is a `prereq`; worked examples for hard concepts; `booktabs` tables only (no vertical rules); cite liberally; **no em dashes** in prose; define every term on first use (bold).

## 10. Out of scope

- No new code in this repo (modeling lives on the GS machine); the algorithm box and experiments are specification + pseudocode only.
- No re-derivation of theory owned by ch08/09/16/17 (cross-reference instead).
- Not a literature review of deep hedging; the NN/band material (Arzel–Lehdili, Brugière–Turinici) appears only as a one-paragraph "Leland is now a baseline" frontier note.

## 11. Acceptance criteria

1. All 7 components present, each with its exact formulas and source anchors (paper + equation/section/page).
2. Every displayed formula has an intuition treatment and every new term is defined on first use.
3. The Ahmad–Wilmott misattribution is corrected in a prominent box, and the κ-inflation is derived and labeled as an own extension (not cited).
4. Zero forward references; all reuse is via `\Cref` to ch08/09/16/17 labels in §8.
5. Algorithm box + 4 experiments (with pass criteria) + ≥4 figures present.
6. Compiles cleanly with the existing preamble; all new bib keys resolve.
7. Reads as a teaching chapter (naïve→realistic narrative, "what/why" throughout), not a reference sheet.

## 12. Open risks / notes

- **Notation reconciliation** between ch09's vol-form gamma-P&L and this chapter's variance-form is the most error-prone seam; handle explicitly in §18.3.
- **Effect-size honesty:** Pollok §6 numbers are unverified (figure/section not rendered); cite Pollok only for the protocol + qualitative bridge, never for specific magnitudes. Li & Wu, François near-zero VRP correlation, and the deep-hedging preprints are context-only.
- **Length:** ~30–40 pp. is a lot; if it overruns, the deep-hedging frontier note (§18.6 tail) and Fig E are the safe trims.
- **Symbol collision in §18.10:** the deflated-Sharpe block reuses $\gamma$ for the Euler–Mascheroni constant (≈0.5772, in $\SR_0$) and $\gamma_3,\gamma_4$ for skew/kurtosis (in the DSR denominator). Disambiguate explicitly in prose when writing the chapter (e.g., name the constant $\gamma_{EM}$) so the reader does not conflate them.
- **κ-inflation derivation check (for the implementer):** with $\Var(H_i)=(\tfrac12\Gamma S^2\sigma^2\,dt)^2(\kappa-1)$, $dt=T/N$, summing $N$ steps gives total variance $=(\tfrac12\Gamma S^2\sigma^2)^2 T^2(\kappa-1)/N \propto \sigma^4(\kappa-1)/N$. Show this chain explicitly in the `keyresult` box.
