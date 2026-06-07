# Design: Chapter 20 — "Predicting Drawdowns of a Daily Variance-Swap Seller: The GSVIVS01 Index"

**Date:** 2026-06-07
**Status:** Design (awaiting research brief integration → user review → write-chapter)
**Target:** `vol-learning-guide/chapters/19-gsvivs01.tex` (new). Renders as **Chapter 20** (file numbers lag the chapter count by one because of the two `12-*.tex` files). Appended to Part "Evaluation and Practice" **after** `18-ivrv-straddle`.
**Primary source data:** `GSVIVS01.md` (repo root) — the strategy spec, real 2022 trade/index data, and the project's drawdown-prediction signal.
**Research brief:** `notes/deep-research/varswap-0dte-vrp.md` (landed; 15 sources kept of 33, 12 PDFs in `reference/project-papers/`). Supplies the canonical replication primaries (DDKZ 1999 + Carr–Lee 2009 + Du–Kapadia 2012 + Le Floc'h 2018) and the same-day 0DTE-VRP empirical thread (Almeida–Freire–Hizmeri, Vilkov, Yang, Beckmeyer, Bandi–Fusari–Renò). **Net message the chapter now carries (new vs. prior notes): replication theory is settled, but the harvesting state of the art is CONDITIONAL — the unconditional 0DTE short is tail-dominated and hard to monetize net of frictions; the edge is in the timing, which is precisely this project's thesis.**
**Chapter label:** `\label{ch:gsvivs}`

---

## 1. Goal

Teach, from first principles and with every formula reproduced exactly, **(Act 1)** what a variance swap is and how the real Goldman Sachs **GSVIVS01** strategy systematically sells one every day — replicating a short daily variance swap on the S&P 500 with a `1/K^2` strip of 0DTE SPX options, delta-hedged with E-mini (ES) futures, harvesting the variance risk premium — and **(Act 2)** how *this internship project* predicts and times the strategy's **drawdowns**: forecast next-day realized volatility, compare it to the variance-swap strike the strip is selling, and go flat or short the GSVIVS01 index on the days the forecast says realized variance will overshoot the strike. The chapter's payoff is the **evaluation metric** for the whole project: the economic value of the drawdown-timing overlay on the real GSVIVS01 index.

The chapter is the **second economic-value capstone**, the direct sequel to Chapter 19 (the IV–RV straddle). Chapter 19 traded the IV–RV gap through a *liquid-but-messy* delta-hedged straddle and stated plainly that a single straddle is **not** a clean variance bet (its dollar gamma collapses off-strike), that the instrument which *is* clean is the variance swap, and that it traded the straddle anyway only because the swap strip is less liquid. **GSVIVS01 is exactly that clean instrument, made tradeable**: the full `1/K^2` strip, executed daily on 0DTE options. This chapter picks up Chapter 19's thread at that precise sentence.

## 2. Teaching philosophy (load-bearing)

Same standard as Chapter 19. This is not a formula dump.

- **Two-act, naïve→real narrative.** Act 1 builds the instrument (abstract variance swap) and then the *real product* (GSVIVS01's 0DTE implementation, with its actual trades). Act 2 builds the prediction system (signal → classification → overlay → evaluation). Each section adds one concrete layer.
- **Intuition before algebra.** Every quantitative section opens with an `intuition` box before the formula and closes with "what breaks if you ignore this."
- **Full standalone re-derivation of the swap math (user decision).** Even though Chapter 8 derives the model-free implied variance integral and the CBOE discrete formula, Act 1 **re-derives them in full** so the chapter stands alone. Cross-reference Chapter 8 as "derived at greater length there," but reproduce the load-bearing steps here.
- **Real data throughout (user decision).** Worked examples use the **actual GSVIVS01 numbers** from `GSVIVS01.md`: the 2022-05-26 strip (25 options, strikes 3875–4095, the `|q|×K^2 ≈ 86,700` constant-weight verification), the real index path (2022-05-25 → 2022-06-01), and the `output.json` trade structure.
- **Define every term on first use** (bold): variance swap, variance notional, fair strike, model-free implied variance, log contract, `1/K^2` strip, 0DTE, TWAP, dollar gamma, short gamma / short vega / long theta, variance risk premium gap, drawdown, precision/recall, cost-sensitive classification, overlay.
- **Honesty boxes.** The chapter's signature intellectual content is (a) *why the variance-swap strike, not ATM IV, is the correct benchmark for the signal* (the skew-premium argument, paid off from Act 1), and (b) *honest statistical-power caveats* — GSVIVS01 has very few drawdown events and a short 0DTE-era history, so the overlay's edge is hard to establish. Both are `warning`/`keyresult` boxes, not footnotes.

## 3. Placement and dependencies

- **Insert** in `main.tex` after `\input{chapters/18-ivrv-straddle}`, still inside `\part{Evaluation and Practice}`.
- **Why here:** it consumes Chapter 8 (variance swaps, model-free implied variance, VIX, Greeks), Chapter 9 (VRP, gamma-P&L), Chapter 19 (IV–RV gap, gamma identity, transaction costs, deflated Sharpe), and the forecasting machinery of Parts 1–4 (HAR, trees, hybrid ensemble) that produces `\widehat{\RV}`. Placing it last means **zero forward references**.
- **Prereq box** (chapter opener) points at: `\Cref{sec:greeks}`, `\Cref{sec:var-swap}`, `\Cref{sec:vix-index}` (ch08); `\Cref{sec:vrp-definition}`, `\Cref{sec:gamma-pnl}` (ch09); `\Cref{ch:ivrv-straddle}` and specifically `\Cref{sec:ivrv:breaks}` (the "single straddle is not a clean variance bet" passage), `\Cref{sec:ivrv:evaluation}` (deflated Sharpe); `\Cref{ch:har}`, `\Cref{ch:hybrid-ensemble}` (the RV forecast). Note we re-derive the swap math so the chapter is self-contained.

## 4. The strategy in plain English (so this spec is self-contained)

**GSVIVS01** sells a **daily variance swap** on the S&P 500. A variance swap pays the holder the difference between realized variance and a pre-agreed strike; GSVIVS01 takes the **short** side, so it profits when realized variance comes in **below** the strike and loses when the market moves more than implied. It does this not by signing an OTC swap but by **replicating** one: each day around 13:10 ET it sells a strip of roughly 25 out-of-the-money 0DTE SPX options, with quantities weighted `1/K^2` so the position has constant dollar exposure to variance regardless of where spot goes (this is the variance-swap replication recipe). It executes the strip via TWAP between 13:30 and 14:00, then **delta-hedges** the residual directional exposure with E-mini S&P 500 futures in 5-minute TWAP intervals. The options are 0DTE, so by the close they have expired or settled, and the position is flat. The strategy is structurally **short gamma, short vega, long theta**: it earns time decay (the variance risk premium) on quiet days and suffers sharp losses on large-move days. The `gsvivs01` index compounds this daily P&L from a base of 100.

**The project (Act 2).** GSVIVS01 draws down precisely when **realized variance exceeds the variance-swap strike** (`RV > K_var`). The strike `K_var` is *observable at trade time* — it is the model-free implied variance the strip is selling — so predicting a drawdown reduces to forecasting next-day realized variance and comparing it to a known number. The signal is the **variance risk premium gap**, `VRP Gap = (K_var/100)^2 − \widehat{\sigma}^2_{RV}×252`: positive means the strike sits comfortably above expected realized (safe to be short vol), near-zero or negative means the edge has vanished or inverted (drawdown risk). We treat the worst days as a **classification** target (predict the 5–10 worst drawdown days per year, against a heavily imbalanced ~85–88% of safe days), trade the prediction as a **flat/short overlay** on the GSVIVS01 index, and evaluate the overlay's economic value (deflated Sharpe, max-drawdown reduction) as the project's headline metric.

## 5. Section-by-section design

Each entry: purpose → what is taught & why → exact formulas (with anchors) → boxes/figures/cross-refs. Section shorthand uses `\label`s (`sec:gsvivs:*`); the chapter renders as Chapter 20.

### Opening: `application` "Why This Chapter" + `prereq`
- **`application` (hook):** open cold on a real GSVIVS01 drawdown — e.g. **2022-06-01, −27.69 bps** (from the real index table) — and ask the blunt question: *the strip sold variance at a known strike that morning; the market then moved more than that strike priced; could a realized-volatility forecast have flagged the day in advance and told us to step aside?* State the chapter's two jobs: explain the strategy, then build the predictor.
- **`prereq`:** dependencies per §3.

---
### ACT 1 — THE INSTRUMENT AND THE PRODUCT (~55%)
---

### `sec:gsvivs:picture` — The strategy in one picture *(intuition; no new formula)*
- **Teach:** GSVIVS01 in one paragraph; the daily loop; the structural risk one-liner (short gamma / short vega / long theta). Explicitly connect to Chapter 19: this is the clean variance instrument that chapter could not trade.
- **Boxes/figs:** `intuition` (selling big-move insurance, every day, on 0DTE — the premium is the variance risk premium); **Fig A** — pipeline flow: VRP → sell `1/K^2` strip → ES delta-hedge → daily P&L → index → *overlay* (the overlay node previews Act 2). `keyidea` stating the trade and who profits when (`RV < K_var`).

### `sec:gsvivs:varswap-payoff` — What a variance swap pays — *re-derivation part 1*
- **Teach:** the variance-swap payoff; long vs short; GSVIVS01 is short; why *variance* (not volatility) is the replicable, additive object.
- **Formulas (exact):** payoff `\text{Payoff} = N_{var}(\sigma^2_{\text{realized}} − K_{var}^2)` (GSVIVS01.md §1.1); variance notional vs vega notional note.
- **Boxes/figs:** `definition` (variance swap, variance notional, fair strike); `workedexample` (single-swap P&L: pick a strike `K_var`, a realized `\sigma^2`, compute payoff for the short); `intuition` (variance is additive across time, so it replicates and accrues cleanly; volatility does not). Cross-ref ch08 `\Cref{eq:varswap-payoff}` ("introduced there; reproduced here").

### `sec:gsvivs:fair-strike` — The fair strike: model-free implied variance — *re-derivation part 2*
- **Teach:** *full re-derivation* of why the fair strike equals the price of a static `1/K^2` strip of OTM options (the model-free implied variance), via the log-contract / Breeden–Litzenberger argument; why `1/K^2` over-weights OTM puts; why this makes **`K_var` exceed ATM implied vol by 1–3 vol points** (the skew premium) — the linchpin of Act 2's signal.
- **Formulas (exact), with verified source anchors:**
  - **Path-by-path identity** (the heart of the re-derivation): `V = \frac{2}{T}\big[\int_0^T \frac{dS_t}{S_t} − \log\frac{S_T}{S_0}\big]` — `\citet{Demeterfi1999}` Eq 20 (p.17); verbatim "variance can be captured no matter which path … as long as it moves continuously." This is the cleanest way in.
  - **Log-contract → strip decomposition:** `−\log(S_T/S^*)` = short forwards + a `1/K^2`-weighted strip of OTM puts and calls — `\citet{Demeterfi1999}` Eq 25 (p.18).
  - **Closed-form strike** `K_{var}^2 = \frac{2}{T}\{rT − (\frac{S_0}{S^*}e^{rT}−1) − \log\frac{S^*}{S_0} + e^{rT}\int_0^{S^*}\frac{P(K)}{K^2}dK + e^{rT}\int_{S^*}^{\infty}\frac{C(K)}{K^2}dK\}` — `\citet{Demeterfi1999}` Eq 26 (p.19). Reconcile with the GSVIVS01.md §1.2 forward-split form `K_{var}^2 = \frac{2e^{rT}}{T}[\int_0^F\frac{P}{K^2}dK+\int_F^\infty\frac{C}{K^2}dK]`.
  - **Why `1/K^2` (derive it, do not assert):** demanding a strip whose variance-exposure is independent of spot forces `2\rho + K\,d\rho/dK = 0 \Rightarrow \rho = \text{const}/K^2` — `\citet{Demeterfi1999}` App. A Eq A3 (p.38). This is the first-principles justification of the `q_i = w\,\Delta K_i/K_i^2` quantities the strategy books.
  - **The skew premium, quantified:** for skew linear in strike `K_{var}\approx \Sigma_0^2(1+3Tb^2)` — `\citet{Demeterfi1999}` Eq 31 (p.23), Eq 33 (p.25), worked in Table 1 (a 1-vol-pt/5-strike skew lifts `K_{var}` from `(20)^2=400` to `(20.467)^2`). Verbatim: "the skew increases the value of the fair variance above the at-the-money-forward level of volatility."
  - **Empirical ordering** RV < vol-swap rate (≈ ATM IV) < variance-swap strike — `\citet{CarrWu2009}` Table 4 discussion (the var-vs-vol-swap gap is a Jensen / vol-of-vol convexity effect). Confirms ATM IV systematically *understates* what GSVIVS01 sells.
- **Boxes/figs:** `keyidea` (fair strike = cost of the replicating strip = model-free implied variance); `keyresult` (the `1/K^2` derivation from constant variance-vega — DDKZ App A); **`warning`** ("`K_var > σ_ATM` by 1–3 vol pts: the skew premium — using ATM IV in the signal is a *structural* error, paid off in `sec:gsvivs:signal`"), citing DDKZ Eq 31/33 + Carr–Wu's empirical ordering; **Fig B** — the `1/K^2` weight curve, annotated "OTM puts dominate ⇒ skew captured." Cross-ref ch08 `\Cref{eq:model-free-var}`, `\Cref{sec:var-swap}` ("derived at greater length there").

### `sec:gsvivs:cboe-discrete` — From integral to traded strip: the CBOE discrete formula — *re-derivation part 3*
- **Teach:** how the continuous integral becomes a finite sum over traded strikes (the VIX/CBOE construction); each term's meaning; why the forward-correction term is negligible at 0DTE.
- **Formulas (exact, GSVIVS01.md §1.3):**
  - `\sigma^2 = \frac{2}{T}\sum_i \frac{\Delta K_i}{K_i^2} e^{rT} Q(K_i) − \frac{1}{T}\big(\frac{F}{K_0}−1\big)^2`, with `\Delta K_i = (K_{i+1}−K_{i-1})/2` (single-sided at endpoints), `Q(K_i)` = OTM midpoint (put if `K_i<F`, call if `K_i>F`, average at `K_i=F`), `K_0` = first strike ≤ `F`.
  - `K_{var} = \sqrt{\sigma^2}\times 100` (vol%).
  - **CBOE/VIX basis (cite):** the strip equals a Gaussian-density-weighted average of total implied variances — `\citet{CarrLee2009}` (unnumbered display before Eq 15, p.331): "the model the CBOE uses implicitly … VIX." So this is literally the VIX construction GSVIVS01 uses to price what it sells.
- **Error budget (the honest part):** discretization on a dense liquid grid is modest (continuous-price error <0.03% vs 0.20% trapezoidal on 78 strikes); the real weaknesses are the piecewise-linear wing approximation and strike-range *truncation* (turns the swap into a corridor swap; 2.82 vol-pt error on a narrow range at 40% vol) — `\citet{LeFloch2018}` Tables 8–9. **Note:** GSVIVS01's strip is narrow (≈3875–4095, ±2.7% on the 2022-05-26 example), so corridor-truncation is a real, bookable approximation worth one sentence.
- **Boxes/figs:** `workedexample` (compute `K_var` from a small discrete strike grid to show the sum mechanics and the half-width endpoints); **`warning`** ("the strip prices *continuous* variance — it is a biased measure of true quadratic variation once the price can jump, and the bias bites exactly when jumps exceed ~70% of variance, i.e. the 0DTE regime": `\citet{DuKapadia2012}` §3.4, the JTIX = BKM − continuous-variance gap). This warning is the bridge to Act 2's drawdown mechanism. Cross-ref ch08 `\Cref{eq:vix}`.

### `sec:gsvivs:replication` — How GSVIVS01 trades it: 0DTE replication *(headline real-data section)*
- **Teach:** the actual product. The `1/K^2` quantity weighting that turns the formula into orders; constant dollar-variance exposure; the real strip; the daily schedule. This is where the chapter becomes concrete and unique.
- **Formulas (exact, GSVIVS01.md §2.3):** `q_i = \frac{w}{K_i^2}\Delta K_i` so `|q_i|\,K_i^2 ≈ \text{const}` (the variance notional `w`).
- **Boxes/figs:**
  - **Headline `workedexample`** — the real **2022-05-26** strip (SPX forward 4057.84): 25 options (14 puts + 11 calls), strikes 3875–4095, 10-pt spacing (5-pt edges), and the `|q|×K^2` verification table showing interior strikes ≈ 86,700 (constant to <0.05%), edges ≈ 43,360 (half-width), forward strike split. Lifted from GSVIVS01.md §2.3.
  - **Table** — daily schedule (13:10 generation, 13:30–14:00 option TWAP, 14:00–14:15+ ES hedge, EOD settle) from GSVIVS01.md §2.1.
  - **Fig C** — bar chart of `|q_i|×K_i^2` across the real 2022 strikes: a flat plateau at ~86,700 with half-height end bars. **This is the visual counterpart to Chapter 19's single-straddle dollar-gamma-collapse figure (`\Cref{fig:ivrv:dollar-gamma}`)** — the explicit contrast is the teaching point. `keyidea`: constant dollar variance across strikes ⇒ the clean variance bet Chapter 19 pointed to.

### `sec:gsvivs:hedge-index` — Delta hedging, daily P&L, and the index
- **Teach:** how the residual delta is neutralized with ES futures; the daily P&L decomposition; how the index compounds; the `output.json` data interface the project consumes.
- **Formulas (exact, GSVIVS01.md §2.4, §3.1):** ES TWAP hedge (5-min, ~25 trades/day); `\text{P\&L}_t = \sum_i q_i(\text{premium})_i − \sum_j \Delta_j(S_{\text{close}}−S_{\text{exec},j}) − \text{tx costs}`.
- **Boxes/figs:** **Table** — real index path (2022-05-25 → 2022-06-01) with daily returns in bps (GSVIVS01.md §3.2), including the +26.75 bps inception day and the −27.69 bps drawdown day used in the hook. **Table** — `output.json` key fields (index value, trades-for-date, instrument.k, quantity sign, source, execution instructions, risks-for-date) as the project's data contract (GSVIVS01.md §5). `intuition` (the index is just compounded daily variance-swap P&L).

### `sec:gsvivs:risk-profile` — The risk profile: short gamma, short vega, long theta
- **Teach:** the Greeks of the aggregate position; theta is the income, gamma is the danger; the signature P&L shape (steady drip punctuated by sharp losses). This sets up Act 2: the drawdowns *are* the short-gamma losses, and they occur exactly when `RV > K_var`.
- **Formulas/facts (GSVIVS01.md §3.3):** delta ≈ 0 (hedged), net short vega, net short gamma, net long theta.
- **Boxes/figs:** `keyidea` (short gamma ⇒ "collect a little most days, lose a lot rarely" — echo Chapter 19's three-day gamma worked example by reference); **Fig D** — the index path with drawdown episodes shaded, making the "drip + cliffs" signature visible. `warning` previewing that every drawdown cliff is an `RV > K_var` day, the thing Act 2 predicts.

---
### ACT 2 — PREDICTING AND TIMING THE DRAWDOWNS (~45%, the project)
---

### `sec:gsvivs:drawdown-mechanism` — The drawdown mechanism: when RV beats the strike (and why jumps make it worse)
- **Teach:** formalize the drawdown condition, why it is *more predictable* than a generic strategy drawdown, and — the new, research-driven content — why the drawdowns are mechanically **down-jump-driven**, not slow-grind-driven.
- **Formulas:** drawdown ⇔ `RV_t > (K_{var,t}/100)^2 / 252` (daily) ⇔ `VRP Gap_t < 0`.
- **The jump asymmetry (new subsection / `keyresult`):** the short-swap P&L from a single downward jump `J` is `(2/T)[−J − \log(1−J)] − J^2/T`, whose **leading term is cubic, `(2/3)J^3/T`** — the quadratic term cancels, so a deep down-gap hurts the short far more than a same-sized up-move (`\citet{Demeterfi1999}` Eq 42 p.31, Table 5: a 15%-down jump scores +101.5 to the short on a 3-month swap). Equivalently, the replication's leading error is **third order in the daily return, signed by `E[R^3]`** — the standard scheme *underprices* the swap when risk-neutral cubed returns are negative (`\citet{CarrLee2009}` Eq 9, p.328–329). **This is the mechanical source of GSVIVS01's asymmetric tail: down-gap days, not quiet grinds, are where the short blows up.**
- **Boxes:** `keyidea` — **`K_var` is observable at trade time** (it is what the strip sells); only `RV` is unknown; so drawdown prediction = an RV forecast vs. a *known* strike. Cleaner than Chapter 19's straddle, where the implied side was a noisy single-option number. `keyresult` (the cubic down-jump term, derived). **`warning`** ("the booked strike is a continuous-variance object; on a jump-laden 0DTE day it can be structurally below the seller's realized loss — so the drawdown signal may need to condition on *jump-share / leverage*, not just the VRP level"). `intuition` (we are not predicting direction, only whether the move — especially a downward gap — exceeds a number we can already see).
- **Cross-ref:** ch04 jumps / bipower variation and semivariance (`\Cref{ch:jumps}`) — the decomposition of realized QV into continuous vs. jump components is exactly the feature that sharpens this signal; this section is where the jumps chapter earns its keep.

### `sec:gsvivs:signal` — The signal: VRP gap with predicted RV
- **Teach:** the signal construction; the three drawdown channels; thresholds; the anti-lookahead boundary the product hands us for free.
- **Formulas (exact, GSVIVS01.md §4.2, §4.4):**
  - `VRP Gap_t = (iv\_vs\_0dte_t/100)^2 − \widehat{\sigma}^2_{RV,t}×252` (252 annualizes daily predicted variance to match the strike's units).
  - Signal rule: `+1` (stay short vol) if `VRP Gap > τ`; `−1` (go flat / counter-trade) if `VRP Gap < −τ_short`; `0` otherwise. Asymmetric thresholds permitted.
  - Three channels (GSVIVS.md §4.5): (1) **compression** `VRP Gap → 0`; (2) **inversion** `VRP Gap < 0`; (3) **contrarian spike** (re-entry after overshoot).
- **Boxes:**
  - **`warning` (signature teaching moment):** *why the variance-swap strike, not ATM IV.* The skew premium derived in `sec:gsvivs:fair-strike` (`K_var > σ_ATM` by 1–3 vol pts) means an ATM-IV signal systematically *understates* what GSVIVS01 sells, compressing the gap and firing too early/late (GSVIVS01.md §4.3). This is Act 1's payoff. Include the small comparison table (ATM IV vs strike, "exact match to what GSVIVS sells").
  - `keyidea` (the three channels as a labelled timeline).
  - **Anti-lookahead `keyidea`:** GSVIVS01 generates its signal at **13:10 ET**; our forecast must therefore use only information available by 13:10 on day `t`. The real product's schedule *is* the lookahead boundary — parallel to Chapter 19's 3:55 pm protocol (`\Cref{sec:ivrv:signal}`), cross-reference it rather than re-deriving the lookahead taxonomy.
  - **`application` (why conditional timing is the whole game — the research payoff):** the harvesting state of the art says an *unconditional* 0DTE short is tail-dominated and "small and difficult to monetize after realistic frictions" (`\citet{Vilkov2024}`), while a *conditioned* short — sized on a forecast/VRP signal — is what delivers net performance. A vol-forecast-conditioned overlay raises Sharpe (variance swaps 1.54→1.76) and cuts max drawdown, skew, and kurtosis (`\citet{Yang2024}`). This is the published justification for *why GSVIVS01 needs this project at all*: the premium is real (`\citet{AlmeidaFreireHizmeri2024}`: 0DTE VRP up to ~4× the 30-day) but only safely harvested with timing.
  - **`warning` (candidate conditioning variables):** the VRP gap is the natural signal, but the brief flags that the *predictable* 0DTE object is the instantaneous vol-of-vol / leverage premium (`\citet{BandiFusariReno2024}`, R² ≈ 21%), not the realized-minus-strike VRP directly. So the signal may benefit from conditioning on vol-of-vol and jump-share alongside the VRP gap. Flag as an open design choice resolved by the experiments, not a settled recipe.

### `sec:gsvivs:classification` — Drawdown prediction as classification
- **Teach (user-chosen framing):** treat the worst days as a binary classification target; the class-imbalance problem; the asymmetric cost of errors; the feature set.
- **Content:**
  - Label: drawdown day (`RV_t` materially over `K_var,t`) vs. safe day; ~85–88% safe ⇒ severe imbalance.
  - **Cost-sensitive framing:** false negative = eat a 50–200 bps drawdown; false positive = forgo one day's premium (small). Asymmetric cost matrix.
  - Metrics: precision/recall on the tail-day class, recall on the *worst* N days, PR-AUC; why raw accuracy is useless under imbalance.
  - **Table** — ML input layers (GSVIVS01.md §4.6): L0 HAR core, L1 asymmetric (semivariance/BPV/jumps), L2 options-implied (`iv_vs_0dte`, VRP, skew, term slope, VVIX), L3 microstructure (E-mini L2, VPIN), L4 cross-asset, L5 calendar (FOMC/NFP/OpEx). Cross-ref the feature chapters (ch10/ch04/ch08). **Highlight, given `sec:gsvivs:drawdown-mechanism`:** the L1 jump/semivariance features and a **jump-share** and **vol-of-vol / leverage** term (`\citet{BandiFusariReno2024}`) are *a priori* the most informative for this specific target, because the drawdowns are down-jump-driven — connect this back to the negative-`E[R^3]` mechanism rather than treating all features as interchangeable.
- **Boxes/figs:** `workedexample` (a confusion matrix on a stylized year → translate cells to bps); **Fig E** — cost-sensitive precision/recall tradeoff (or the cost matrix as a 2×2 heat block). `warning` (accuracy is a trap under 85–88% base rate).

### `sec:gsvivs:overlay` — From prediction to position: the overlay
- **Teach:** turn the prediction into a position on the GSVIVS01 index; full / flat / short; graded sizing; the specific act of shorting the index on high-conviction drawdown days (the project's core idea).
- **Formulas (exact, GSVIVS01.md §4.7):** `\text{Position}_t = \text{Signal}_t × \text{Base Notional}`; Signal `+1` = full GSVIVS01 (collect VRP), `0` = flat (avoid drawdown), `−1` = short / counter-trade (buy vol protection, rare).
- **Boxes:** `keyidea` (the overlay = buy-and-hold GSVIVS01 modulated by the signal); `warning` (graded sizing beats a binary switch — cross-ref Chapter 19's `LiWu2026` caveat at `\Cref{sec:ivrv:signal}`, cited narrowly); `intuition` (we are timing a known premium harvester: stay in when the edge is fat, step aside or fade it when the edge is gone).

### `sec:gsvivs:evaluation` — Evaluation: the project's metric
- **Teach:** how the overlay's performance becomes the project's headline evaluation metric, judged honestly; integrate classification quality with economic value.
- **Content/formulas:**
  - Headline metric: **overlaid index P&L vs. buy-and-hold GSVIVS01**; risk-adjusted via the **deflated Sharpe** (restate, cross-ref `\Cref{sec:ivrv:evaluation}`/`\Cref{eq:ivrv:dsr-restate}` and ch16 `\Cref{sec:eval-dsr}`), **max-drawdown reduction**, and Calmar.
  - Performance target (GSVIVS01.md §4.7): avoid the 5–10 worst days/yr (50–200 bps each) while staying invested ~85–88% of days.
  - **Classification ↔ economic-value bridge:** map precision/recall on tail days to bps saved (true positives) and bps forgone (false positives); a recall/precision pair *is* an expected-P&L number under the cost matrix.
  - **Published precedent (the benchmark to beat / match):** `\citet{Yang2024}` is the closest measured analogue — a vol-forecast-conditioned short-variance overlay that lifts Sharpe **1.54→1.76** on variance swaps and cuts max drawdown, skew, and kurtosis, cutting exposure only in high-vol regimes. State it as the directional target, with the explicit caveat that Yang is **1-month, monthly-rebalanced**, not 0DTE, so the magnitude does not transfer (see experiments).
  - Honest accounting: overlay transaction costs (entering/exiting the index; if shorting via the strip, Chapter 19's option/hedge costs apply — cross-ref `\Cref{sec:ivrv:option-costs}`), multiple-testing deflation for the variants tried, **purged/combinatorial CV** (cross-ref ch16) given the autocorrelated, event-clustered drawdowns.
- **Boxes/figs:** **Fig F** — overlay equity curve vs. buy-and-hold, with avoided drawdowns highlighted; **`warning` (the dominant honesty box):** the 0DTE short is *tail-dominated*, "wide, state-dependent, and dominated by tail risk rather than … stable mean carry" (`\citet{Vilkov2024}`), and GSVIVS01 has few drawdown events on a short 0DTE history ⇒ wide error bars; deflate honestly, use purged CV, and do not overfit to 2–3 historical crashes; `application` (the punchline: the project's deliverable is a *better-timed* GSVIVS01, the premium is real but only safely harvested conditionally, and the deflated Sharpe + max-DD reduction are how we prove the timing is skill, not luck).

### `sec:gsvivs:experiments` — What to compute on our data *(projectconnection, each with a pass criterion)*
1. **Strike vs. ATM-IV signal.** Build the VRP-gap signal with the variance-swap strike and, separately, with ATM 0DTE IV; compare drawdown-day classification and overlay P&L. *Pass:* the strike-based signal is meaningfully better (validates `sec:gsvivs:fair-strike` / §4.3 on our data), or we learn it is not.
2. **ML-RV vs. HAR-RV in the overlay.** Drive the overlay with the ML ensemble forecast and with a plain HAR forecast. *Pass:* the QLIKE-better model yields higher deflated overlay Sharpe and larger max-DD reduction — the QLIKE→P&L bridge of Chapter 19, retested on the real index.
3. **Cost-sensitive classification.** Tune the decision threshold on the asymmetric cost matrix; report precision/recall on the worst N days. *Pass:* the chosen threshold beats both "always invested" and "naïve VIX-level rule" in expected bps.
4. **Deflated, purged overlay Sharpe.** Report overlay Sharpe block-bootstrapped over drawdown-clustered blocks, deflated for the honest number of variants, under purged/combinatorial CV. *Pass:* clears `\SR_0` for the true variant count, not for `N=1`.
5. **Channel robustness.** Test the contrarian re-entry channel and asymmetric thresholds. *Pass:* re-entry adds value beyond flat-only, or is dropped.
6. **Conditional vs. unconditional (the monetizability test).** Backtest GSVIVS01 buy-and-hold vs. the VRP-gap-conditioned overlay over our SPX 0DTE sample. *Pass:* the conditioned book's deflated Sharpe dominates buy-and-hold **and** the RV forecast driving the gap beats a no-skill `E[RV]=K_var` benchmark by a Diebold–Mariano-significant QLIKE margin. (If timing adds Sharpe but forecast QLIKE is flat, the edge is regime/seasonality, not forecast skill — `\citet{Vilkov2024}` vs `\citet{AlmeidaFreireHizmeri2024}` tension.)
7. **Does the Yang mechanism survive at 0DTE? (horizon-transfer test).** Estimate the conditional **next-day** (not next-month) 0DTE-VRP response to a same-day vol shock. *Pass:* a same-day spike predicts a lower next-day VRP (Yang's "low-premium response" logic transfers); if not, switch the conditioning variable to vol-of-vol / leverage (`\citet{BandiFusariReno2024}`).
8. **Jump-share decomposition (is the strike structurally underpriced?).** Decompose realized 0DTE QV into continuous (bipower) vs. jump components and compute the realized third moment `E[R^3]` (cross-ref ch04). *Pass:* if negative `E[R^3]` dominates on drawdown days, quantify the bps gap between the booked strike and a jump-corrected (BKM/JTIX) strike (`\citet{DuKapadia2012}`) and test whether conditioning the signal on **jump-share** beats conditioning on VRP level alone.

### `sec:gsvivs:summary` — Summary & honest caveats
- `keyresult` recap: the swap and its strike; GSVIVS01 as the clean 0DTE variance seller; the drawdown condition `RV > K_var`; the strike-based VRP-gap signal; the classification→overlay→deflated-Sharpe evaluation chain.
- **Single biggest caveat (`warning`):** GSVIVS01's edge is a negative variance risk premium harvested daily; its history is short (0DTE era) and its drawdowns are few, so the overlay's statistical power is limited and the temptation to overfit a handful of crashes is acute. The metric is honest only with deflation, purged CV, and a cost band.

## 6. Figures (TikZ / pgfplots, matching `preamble.tex` house style)

| Fig | Where | What | Type |
|---|---|---|---|
| A | `sec:gsvivs:picture` | GSVIVS01 pipeline: VRP → sell `1/K^2` strip → ES hedge → daily P&L → index → overlay | TikZ flow (`flowblock`/`decisionblock`) |
| B | `sec:gsvivs:fair-strike` | `1/K^2` weight curve over strikes (OTM puts dominate ⇒ skew captured) | pgfplots |
| C | `sec:gsvivs:replication` | `|q_i|×K_i^2` across the real 2022 strikes: flat ~86,700 plateau, half-height edges (contrast Ch19 `fig:ivrv:dollar-gamma`) | pgfplots bar |
| D | `sec:gsvivs:risk-profile` | GSVIVS01 index path with drawdown episodes shaded ("drip + cliffs") | pgfplots |
| E | `sec:gsvivs:classification` | Cost-sensitive precision/recall tradeoff (or 2×2 cost matrix heat block) | pgfplots / TikZ |
| F | `sec:gsvivs:evaluation` | Overlay equity curve vs. buy-and-hold GSVIVS01, avoided drawdowns highlighted | pgfplots |
| G | `sec:gsvivs:drawdown-mechanism` | Short-swap P&L vs. jump size: the cubic `(2/3)J^3/T` asymmetry (down-gaps hurt far more than equal up-moves; DDKZ Eq 42) | pgfplots |

## 7. New `references.bib` entries  *(finalized from the brief; PDFs in `reference/project-papers/`)*

**Canonical replication (Act 1) — all downloaded this run:**
- `Demeterfi1999` — Demeterfi, Derman, Kamal & Zou, *More Than You Ever Wanted to Know About Volatility Swaps*, Goldman Sachs Quantitative Strategies Research Notes, 1999. The on-theme GS primary. `demeterfi-derman-1999-volatility-swaps.pdf`. **[Essential]**
- `CarrLee2009` — Carr & Lee, *Volatility Derivatives*, Annual Review of Financial Economics, 2009. Cleanest peer-reviewed derivation; third-order jump error; CBOE/VIX basis. `carr-lee-2009-volatility-derivatives.pdf`. **[Essential]**
- `CarrWu2009` — Carr & Wu, *Variance Risk Premiums*, RFS, 2009. RV < vol-swap (≈ATM IV) < var-swap-strike ordering. `carr-wu-2009-variance-risk-premia.pdf`. **[Essential]**
- `DuKapadia2012` — Du & Kapadia, *Tail and Volatility Indices…*, 2012. VIX/`1/K^2` strip jump bias (JTIX). `du-kapadia-2012-tail-volatility-index.pdf`. **[Essential]**
- `LeFloch2018` — Le Floc'h, *Variance Swap Replication: Discrete or Continuous?*, JRFM 11(1), 2018. Discretization/truncation/jump error budget. `lefloch-2018-variance-swap-replication.pdf`. **[Recommended]**
- `AschakulpornZhang2019` — Aschakulporn & Zhang, 2019 (BKM risk-neutral moment estimators). ATM+skew+kurtosis decomposition; strike-range error bounds. Cite as Aschakulporn–Zhang, **not** as BKM 2003. `aschakulporn-zhang-2019-bkm-moment-estimators.pdf`. **[Recommended]**

**Recent 0DTE / VRP / drawdown (Act 2) — downloaded this run:**
- `Yang2024` — Yang, *Volatility-Managed Volatility Trading*, 2024. Vol-forecast-conditioned overlay, Sharpe/DD deltas. Closest analogue to GSVIVS01 §4. `yang-2024-volatility-managed-vol-trading.pdf`. **[Essential]**
- `AlmeidaFreireHizmeri2024` — Almeida, Freire & Hizmeri, *0DTE Asset Pricing*, 2024. 0DTE VRP up to ~4× monthly; seller earns it. `almeida-freire-hizmeri-2024-0dte-asset-pricing.pdf`. **[Essential]**
- `BandiFusariReno2024` — Bandi, Fusari & Renò, *0DTE Option Pricing* (fc. J. Finance), 2024. 0DTE smile = leverage + vol-of-vol; predictable instantaneous vol premium. `bandi-fusari-reno-2024-0dte-option-pricing.pdf`. **[Essential]**
- `BeckmeyerBrangerGayda2023` — Beckmeyer, Branger & Gayda, *Retail 0DTE…*, 2023. Buyer-loss = seller-premium confirmation. `beckmeyer-branger-gayda-2023-retail-0dte.pdf`. **[Essential]**
- `DimErakerVilkov2024` — Dim, Eraker & Vilkov, *0DTE Gamma Risk*, 2024. Dealer-gamma dampening (microstructure context). `dim-eraker-vilkov-2024-0dte-gamma-risk.pdf`. **[Recommended]**

**Cited abstract-only (gated — cite carefully, no specific magnitudes from gated tables):**
- `Vilkov2024` — Vilkov, *0DTE Trading Rules*, SSRN 4641356, 2024. THE on-thesis harvesting/timing source: same-day VRP small/hard to monetize, tail-dominated, conditional timing works. Abstract verified; tables gated. Replication repo `github.com/vilkovgr/0dte-strategies` (check on H:\). **[Essential — acquisition target]**

**Reused (verify presence in `references.bib`):** `BakshiKapadia2003`, `AhmadWilmott2005`, `Pollok2025`, `LiWu2026`, `Bailey2014DSR`, `Bennett2014`, `CBOE2019`, `BollerslevTauchenZhou` (30-day VRP). Bib metadata: pull from the brief's evidence table + the acquired PDFs; the `reference/project-papers/` README index was auto-updated by the research run.

## 8. Cross-reference map (reference, do not repeat — except the deliberate swap re-derivation)

- **ch08 `ch:volsurface`:** `sec:greeks`, `sec:var-swap`, `eq:varswap-payoff`, `eq:model-free-var`, `sec:vix-index`, `eq:vix`. **Note:** Act 1 *deliberately re-derives* the model-free integral and CBOE formula (user decision: standalone chapter); cross-reference ch08 as "fuller treatment there," but reproduce here.
- **ch09 `ch:vrp`:** `sec:vrp-definition`, `eq:vrp-operational`, `sec:gamma-pnl`, `eq:gamma-pnl-simple`.
- **ch19 `ch:ivrv-straddle`:** `sec:ivrv:picture`, `sec:ivrv:signal` (lookahead protocol, graded-sizing caveat), `sec:ivrv:pnl-engine`/`eq:ivrv:daily-discrete`, **`sec:ivrv:breaks`** (the "single straddle is not a clean variance bet"/variance-swap contrast — the hinge this chapter swings on), `fig:ivrv:dollar-gamma` (contrast figure), `sec:ivrv:option-costs`/`eq:ivrv:vega-cost`, `sec:ivrv:evaluation`/`eq:ivrv:dsr-restate`, `sec:ivrv:experiments`.
- **ch16 `ch:evaluation`:** `sec:eval-qlike`, `sec:eval-dm`, `sec:eval-mcs`, `sec:eval-dsr`/`eq:dsr`, purged/combinatorial CV labels.
- **Forecast chapters:** `ch:har` (ch06), `ch:hybrid-ensemble` (ch13/14), feature labels in ch10/ch04 for the ML-input table. **Verify these labels at write time.**

**Do NOT re-derive:** Black–Scholes/Greeks (ch08), VRP economics & base gamma identity (ch09), the entire straddle backtest machinery and deflated-Sharpe closed form (ch19/ch16), turnover/Sharpe-drag mechanics (ch17). **Define fresh:** variance-swap payoff in this chapter's notation, the `1/K^2` quantity weighting and constant-dollar-variance property, 0DTE replication mechanics, the GSVIVS01 index, the strike-based VRP-gap signal and its three channels, drawdown-as-classification with a cost matrix, the flat/short overlay, the classification↔economic-value bridge.

## 9. Conventions & tooling

- **Boxes:** reuse existing `intuition`, `keyidea`, `definition`, `warning`, `prereq`, `workedexample`, `application`, `keyresult`, `projectconnection` (no new tcolorbox types).
- **Macros:** reuse `\RV`, `\IVol`, `\VRP`, `\SR`, `\DSR`, `\Var`, `\E`, `\N` from `preamble.tex`; add `\Kvar` only if it recurs enough to warrant it, else `\ensuremath{K_{\mathrm{var}}}` inline.
- **Citations:** `\citep`/`\citet` (`natbib`); bib at guide root.
- **No packages in the chapter file** (preamble owns them).
- **Authoring:** draft `19-gsvivs01.tex` with the project `write-chapter` skill. After drafting: compile (`pdflatex → bibtex → pdflatex ×2`); run `verify-diagram` on every TikZ figure (A–F); run `convert-chapter-markdown` for the markdown mirror; `sync-docs` if updating `docs-only`. Add the `\input` line to `main.tex` after ch18.
- **Style (CLAUDE.md):** open with a concrete question; first box is `prereq`; worked examples for hard concepts; `booktabs` tables only (no vertical rules); cite liberally; **no em dashes in prose**; define every term on first use (bold).

## 10. Out of scope

- No new code (modeling lives on the GS machine); the signal, classification, overlay, and experiments are specification + pseudocode only.
- No re-derivation of theory owned by ch09/ch16/ch17/ch19 (cross-reference). Act 1 *does* re-derive the ch08 swap math, by user decision.
- Not a survey of variance-swap pricing models (Heston, rough vol); rough-vol pricing stays in ch07. Mention only as a one-line pointer if needed.
- No live trading or execution-system detail beyond what `GSVIVS01.md` documents.

## 11. Acceptance criteria

1. Both acts present; Act 1 self-contained (full swap re-derivation), Act 2 builds signal → classification → overlay → evaluation.
2. Every displayed formula has an intuition treatment; every new term defined on first use.
3. The **real 2022-05-26 strip** worked example (with the `|q|×K^2 ≈ 86,700` verification) and the **real index path** table are present and correct against `GSVIVS01.md`.
4. The **strike-vs-ATM-IV** signal argument is a prominent `warning` and is explicitly traced back to the skew-premium re-derivation in Act 1.
5. The explicit **Chapter 19 contrast** (GSVIVS01 as the clean variance instrument; Fig C vs `fig:ivrv:dollar-gamma`) is made.
6. Drawdown-as-classification with an asymmetric cost matrix, the flat/short overlay, and the classification↔economic-value bridge are all present.
7. Eight experiments with explicit pass criteria; ≥7 figures; all run through `verify-diagram`.
8. Zero forward references; reuse via `\Cref` to ch08/09/16/17/19 labels in §8.
9. Compiles cleanly with the existing preamble; all new bib keys resolve.
10. Honest statistical-power / overfitting caveat is prominent (low event count, short 0DTE history; directional-analogue caveat on all Thread-2 magnitudes).
11. The **down-jump cubic mechanism** (DDKZ Eq 42 / Carr–Lee Eq 9) is derived in `sec:gsvivs:drawdown-mechanism`, tied to ch04 jumps, and motivates jump-share conditioning.
12. The **conditional-timing thesis** (unconditional 0DTE short is tail-dominated; conditional overlay is the SOTA — Vilkov, Yang) is stated as the project's published justification, with Yang as the directional precedent and explicit "not transferable" caveats.

## 12. Open risks / notes

- **Directional analogues, not transferable point estimates (the dominant Act-2 caveat).** None of the Thread-2 sources is GSVIVS01 itself — they are 1-month variance swaps (Yang), generic 0DTE straddles (Vilkov, Almeida–Freire–Hizmeri), or buyer-side (Beckmeyer). Cite Sharpe/VRP magnitudes (1.54→1.76; "4× monthly"; 2.87–8.00%) as *directional* evidence only; every number must be re-earned on our SPX 0DTE data. The chapter must say this explicitly, not bury it.
- **Three live tensions the chapter must present honestly (now resolved into experiments 6–8):** (1) *Monetizability* — Almeida–Freire–Hizmeri call the 0DTE VRP rich (4× monthly), Vilkov calls the same-day VRP small/hard to monetize net of frictions; richness-per-unit-time ≠ net monetizability, so do **not** present "4×" as a harvestable edge. (2) *Horizon transfer* — Yang's drawdown-reduction mechanism is a one-month result; it may not survive at the same-day horizon. (3) *Jump bias* — the `1/K^2` strike mismeasures jump-laden quadratic variation exactly in the 0DTE regime (Du–Kapadia), while the short collects a positive cubic term on down-jumps (DDKZ Eq 42); the net direction of the bias on drawdown days is an empirical question.
- **Statistical power is the dominant honesty risk.** GSVIVS01 has few drawdowns and a short 0DTE-era history, and the 0DTE short's P&L is tail-dominated (Vilkov); the overlay's deflated Sharpe will have wide error bars. Lead with this; deflate honestly; use purged/combinatorial CV.
- **`Vilkov2024` is abstract-only.** Cite it for the qualitative thesis (conditional > unconditional; tail-dominated) and never for a specific Sharpe/PnL number from its gated tables. Acquisition target: the `github.com/vilkovgr/0dte-strategies` repo on H:\ may expose the numbers.
- **Notation seam.** Keep variance vs. volatility units consistent: the strike is quoted in vol% (`K_var`), the predicted RV is a daily variance (`\widehat{\sigma}^2_{RV}`), and the VRP gap works in annualized variance. State the unit conversions explicitly (the `×252` and `/100`), mirroring how Chapter 19 reconciled its variance-vs-vol forms.
- **Label verification.** The forecast-chapter labels (`ch:har`, `ch:hybrid-ensemble`, feature labels) must be confirmed against the actual `.tex` files at write time; the ch08/09/16/19 labels are confirmed from reading those files.
- **Length.** Two acts + full re-derivation ⇒ likely ~30–40 pp. If it overruns, the safe trims are the discrete-grid CBOE worked example (`sec:gsvivs:cboe-discrete`) and Fig E.
