# GSVIVS Exec Kvar (Effective Net Strike)

## What this document is

This is a walkthrough of how we currently compute the variance-swap strike `Exec Kvar (true fill)` that the GSVIVS01 signal backtest consumes. It is written for someone who is encountering the problem for the first time, so the early sections explain the motivation before any math appears.

If you already know the setup and just want the formulas, skip to [Step 1](#step-1-parse-the-opening-option-legs).

---

## The problem: we do not have a clean IV number to compare RV against

The whole point of the GSVIVS01 signal is the IV-RV gap: take the implied variance the market is pricing for the next day, compare it to our own RV forecast for that same day, and decide whether to go long or short the variance swap.

To do that comparison we need a clean implied-variance number, expressed as an annualized vol, for the front 0DTE SPX strip. The natural source of that number is the option vol surface itself: feed the strike grid into the standardized model-free variance integral and read off Kvar directly.

We do not currently have that. The cached vol-surface data we need (Marquee EDRVS 0-DTE, or a reconstruction from EDRVOL_PERCENT_EXPIRY) is not yet wired up for daily use. The risk node marks in `output.json` are stale by the morning. SPY ATM IV is the wrong underlying.

So this document describes a workaround: **reverse-engineer Kvar from the trades the strategy actually executed that morning.** The fills are in the raw output of the live strategy, the quantities are in there too, and the strip is by construction a discrete approximation of the model-free variance integral. With a bit of care we can back out an implied variance strike from the executed strip and use that as our IV input until the proper vol-surface pipeline lands.

This is a stopgap. The assumption baked into the rest of this document is:

> Eventually we will have access to a proper 0DTE IV reconstruction from the vol surface. Until then, the reverse-engineered Kvar from the executed strip is the best available proxy for the same object.

---

## What you are looking at when you read this document

There are three flavors of the reverse-engineered strike, exposed side by side:

1. **Gross fill-based strike** — what the opening fills alone imply, ignoring frictions.
2. **Option-TC-adjusted strike** — strike after deducting option transaction costs.
3. **Full-friction effective strike** — strike after deducting option and futures transaction costs.

The default series cached as `kvar_vol_pct` is the third one. The other two are kept for auditability.

The reason the default is the friction-adjusted version is that this is meant to approximate the *effective* strike the strategy actually sold, not just the headline price printed at execution.

---

## Horizon convention (read before any equation)

Every variance-swap formula in this document has a tenor input $T$. Two choices of $T$ are mathematically valid but answer different questions:

1. **Residual-life tenor** (`6.25h` to `6.83h`): the literal time remaining on the 0DTE option being traded. This is contract-life-correct.
2. **Daily comparison tenor** (`24h / 8760`): a normalized daily horizon.

We use the daily tenor by default. The reason is purely about downstream use: we are comparing this IV against a daily realized-variance series, so we want the IV expressed on the same daily horizon. Annualized vol scales as

$$
\sigma \propto \frac{1}{\sqrt{T}}
$$

so moving from a `6.25h` residual life to a `24h` daily tenor lowers the reported vol by

$$
\sqrt{\frac{6.25}{24}} \approx 0.51
$$

Without this normalization the IV would mechanically look about twice the RV, just because of the tenor mismatch. The older `6.25h` convention is no longer the default.

### Multi-horizon usage in the dashboard

The cached `Exec Kvar (true fill)` series is used **without scaling** at all forecast horizons (h=1, 5, 22). Both the Kvar (annualized from T=24h) and the RV forecast (annualized via $\sqrt{252 \cdot \text{daily\_var}}$) are already in the same annualized vol units regardless of the forecast horizon h. No horizon-dependent normalization is applied.

Previously the code divided by $\sqrt{h}$, which was incorrect — it artificially deflated the IV side of the gap at longer horizons by treating the strip premium as if it accrued over h days instead of 1 day.

---

## Sources of truth

To keep this calculation honest, the inputs always come from a fixed place:

- Raw trade and cash data: `data/external/output.json`
- Strategy mechanics and cash-ledger identity: [workspace/docs/gsvivs_audit_results.md](workspace/docs/gsvivs_audit_results.md)
- **Not** used as a source of truth: `ch19-gsvivs01.md`

---

## The raw accounting model

Before we reverse-engineer anything, here is what the strategy's daily ledger actually looks like. From [workspace/docs/gsvivs_audit_results.md](workspace/docs/gsvivs_audit_results.md#L71):

$$
\text{Initial} + \text{Execution Cash} + \text{TC}_{O} + \text{TC}_{Fw} = \text{Index Value}
$$

Reading left to right:

- `Execution Cash` is cumulative trading cash for the day.
- `Transaction Costs O` is cumulative option transaction costs.
- `Transaction Costs Fw` is cumulative futures (ES hedge) transaction costs.

We do not assume these are dollar units. They are treated as index-point cash units, consistent with [workspace/docs/gsvivs_audit_results.md](workspace/docs/gsvivs_audit_results.md#L94).

Everything that follows is a careful decomposition of those buckets so we can rebuild an implied variance strike from them.

---

## Step 1: Parse the opening option legs

We start by pulling out the legs of the morning strip. These are the puts and calls the strategy sold at the open to short variance.

The work is done by `parse_day_opening_legs()` in [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L57).

A leg counts as an opening leg if all of the following hold:

- `source == "VSR 0b"` (the strategy's opening tag),
- `quantity < 0` (we are selling),
- the instrument is an SPX `Put` or `Call`,
- a paired fill record gives us the execution price (read at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L95)).

For each leg we record:

- strike $K_i$,
- option type,
- execution price $P_i$,
- executed quantity $q_i$.

This is the raw material for everything downstream.

---

## Step 2: Parse transaction costs

Next we pull out the realized transaction costs, separating option costs from futures costs. This is done by `parse_day_transaction_costs()` in [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L122).

The raw JSON exposes them as two distinct buckets, so we accumulate them separately at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L134):

$$
TC_O = \sum \text{option TC cash entries}
$$

$$
TC_{Fw} = \sum \text{futures TC cash entries}
$$

$$
TC_{\mathrm{all}} = TC_O + TC_{Fw}
$$

These are negative cash values in the raw ledger (costs reduce the cash account).

We keep them split because the option-TC-only and full-friction strikes will use different combinations.

---

## Step 3: Decompose trading cash

The execution-cash bucket lumps together several different kinds of trade. For audit purposes we want to see them individually. `parse_day_trade_cashflows()` in [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L153) splits the day into:

- opening option cash,
- closing option cash,
- ES hedge cash.

Each trade cashflow uses the standard sign convention

$$
\text{cash} = -q \times P_{\mathrm{exec}}
$$

implemented at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L170).

These columns are written out as audit diagnostics so you can sanity-check the strike reconstruction against the raw ledger. They are not themselves plugged into the variance integral.

---

## Step 4: Recover the strip replication scale from the quantities

This step is the key piece of reverse engineering. We do not know what nominal "size" the strategy traded the variance swap at. But we do know the quantities of every individual option leg, and a variance-swap replication strip has a very specific quantity profile.

For a textbook strip, the absolute option quantity should satisfy

$$
|q_i| \approx N \cdot \frac{\Delta K_i}{K_i^2}
$$

where:

- $N$ is the (unknown) overall strip scale,
- $\Delta K_i$ is the local strike spacing around leg $i$.

So if we know $|q_i|$, $K_i$, and $\Delta K_i$, we can solve for $N$.

The strike spacing is computed by `_compute_delta_k()` in [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L24) using the standard centered difference, with one-sided differences at the boundary:

$$
\Delta K_i=
\begin{cases}
K_2-K_1 & i=1 \\
K_n-K_{n-1} & i=n \\
\tfrac12 (K_{i+1}-K_{i-1}) & \text{otherwise}
\end{cases}
$$

For each leg we then solve for its implied scale,

$$
N_i = \frac{|q_i|}{\Delta K_i / K_i^2}
$$

and take the median $N_i$ as the overall strip scale $N$. A coefficient-of-variation diagnostic `weight_fit_cv` is exposed so you can tell when the quantities deviated from the textbook replication weights. This logic is at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L52), inside `_infer_replication_scale()` at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L38).

Once we have $N$, we can convert any cash number into a per-strike premium curve proxy and feed it into the variance integral.

---

## Step 5: Compute the curve-based model-free variance strike (reference)

We keep the textbook curve-based calculation around as a reference series, even though it does not incorporate any transaction costs.

The discrete model-free variance term, in `compute_kvar_from_legs()` at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L263), is

$$
\sigma_{\mathrm{curve}}^2 = \frac{2}{T} \sum_i \frac{\Delta K_i}{K_i^2} e^{rT} Q(K_i)
$$

with code at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L257).

The standard forward correction is

$$
\mathrm{corr} = \frac{1}{T}\left(\frac{F}{K_0}-1\right)^2
$$

applied at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L260), and the curve-based strike is

$$
K_{\mathrm{var,curve}}^2 = \sigma_{\mathrm{curve}}^2 - \mathrm{corr}
$$

This series is useful as a sanity check against the cash-based versions in the next steps. It is not used as the trading signal because it ignores frictions.

---

## Step 6: Compute the quantity-aware gross premium cash

Now we switch from a curve-based integral to a cash-based one. The executed opening strip premium is just the sum of the cash collected across legs:

$$
C_{\mathrm{gross}} = \sum_i -q_i P_i
$$

(see [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L266)).

Because the strip quantities are proportional to $\Delta K_i / K_i^2$ (Step 4), dividing this cash total by the inferred strip scale gives a quantity-normalized premium curve proxy:

$$
\widetilde{Q}_{\mathrm{gross}} = \frac{C_{\mathrm{gross}}}{N}
$$

Plugging that into the same variance-strip formula gives the gross cash-implied variance strike:

$$
K_{\mathrm{var,gross}}^2 = \frac{2}{T} e^{rT} \frac{C_{\mathrm{gross}}}{N} - \frac{1}{T}\left(\frac{F}{K_0}-1\right)^2
$$

implemented at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L269).

This is the first version that actually uses the executed quantities. It is exposed as `kvar_gross_vol_pct`.

---

## Step 7: Deduct transaction costs

The gross strike tells you what the prints alone imply. But the strategy did not actually pocket that premium — execution frictions ate part of it. So we run the same calculation twice more, replacing $C_{\mathrm{gross}}$ with a frictions-adjusted cash number.

### Option-TC-adjusted strike

If we only care about the effective option strike after option execution frictions, we shrink the premium cash by $TC_O$:

$$
C_{\mathrm{opt\ net}} = C_{\mathrm{gross}} + TC_O
$$

($TC_O$ is already negative.) The resulting strike is exposed as `kvar_option_tc_vol_pct` in [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L464).

### Full-friction strike

If we want the effective economic strike after every explicitly booked execution friction, we deduct both option and futures TC:

$$
C_{\mathrm{full\ net}} = C_{\mathrm{gross}} + TC_O + TC_{Fw}
$$

and the full-friction cash-implied strike is

$$
K_{\mathrm{var,full}}^2 = \frac{2}{T} e^{rT} \frac{C_{\mathrm{full\ net}}}{N} - \frac{1}{T}\left(\frac{F}{K_0}-1\right)^2
$$

implemented at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L270).

This full-friction version is what is assigned to:

- `kvar_vol_pct`
- `kvar_variance_ann`

at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L299).

So the default cached series is the executed strip's gross premium, normalized by the inferred replication scale, with option and futures transaction costs subtracted.

---

## A subtle but important point: what is the information set at 09:10?

The signal that uses this Kvar is formed *before* the strip is executed. So it is worth being precise about what is known at signal time and what is not.

At 09:10, the strategy knows:

- the current date,
- the published GSVIVS rules,
- pre-trade market data and model forecasts available before execution,
- the opening-strip design and expected execution window,
- assumptions about transaction costs estimable before trading.

At 09:10, the strategy does **not** yet know:

- the opening option fill prices that will print during the TWAP window,
- the realized ES hedge trades needed later in the day,
- the realized ES hedge execution prices,
- the option close / expiry cash flows at end of day,
- the full realized day P&L.

That means there are two distinct classes of objects we could compute.

### 1. Signal-time objects

Things that can legitimately enter the live trading signal because they are known or estimable before the strategy commits risk. For example:

- a mark-based implied strike,
- an opening-fill-based strike used only for ex-post evaluation,
- a strike adjusted by expected or mechanically known transaction costs.

In notation,

$$
K_{\mathrm{signal}} = \text{opening implied strike or expected net strike available at decision time.}
$$

### 2. Ex-post realized objects

Things only known after the day plays out:

- realized ES hedge cash,
- realized option close / expiry cash,
- realized same-day implementation P&L.

In notation,

$$
K_{\mathrm{realized}} = \text{effective strike inferred after the full day path is known.}
$$

Both are meaningful. They are not the same object, and confusing them creates lookahead.

---

## Why we include futures TC but not realized ES hedge cash

The cached `kvar_vol_pct` is intended to remain a *signal-time-style* implied strike proxy, not an ex-post realized net-strike inversion. That distinction drives what we include and what we exclude.

Included:

- option transaction costs,
- futures transaction costs.

Not included:

- realized ES hedge trading cash,
- realized option close cash.

The reasoning:

- Transaction costs are execution frictions. They can be treated as a clean reduction to the effective strike sold, and we can estimate them well enough at signal time to fold them in.
- Realized ES hedge cash and realized option close cash depend on the *intraday price path*. They are only known after the day plays out. Pushing them into the morning's implied variance term would contaminate the signal with future information.

### Signal-time interpretation (what we actually compute)

So our default object is

$$
K_{\mathrm{var,full}}^2 = \frac{2}{T} e^{rT} \frac{C_{\mathrm{gross}} + TC_O + TC_{Fw}}{N} - \frac{1}{T}\left(\frac{F}{K_0}-1\right)^2
$$

where:

- $C_{\mathrm{gross}}$ is the opening option premium collected from the strip,
- $TC_O$ is the option transaction cost,
- $TC_{Fw}$ is the futures transaction cost,
- $N$ is the inferred strip replication scale.

This is an opening-strike concept adjusted for execution frictions. It is still a signal-time-style object.

### Ex-post realized inversion (what we deliberately do not compute)

If we instead folded in realized hedge cash and realized option close / expiry cash, we would be computing

$$
C_{\mathrm{realized\ net}} = C_{\mathrm{gross}} + C_{\mathrm{opt\ close}} + C_{\mathrm{hedge}} + TC_O + TC_{Fw}
$$

and the corresponding ex-post realized strike would be

$$
K_{\mathrm{var,realized}}^2 = \frac{2}{T} e^{rT} \frac{C_{\mathrm{realized\ net}}}{N} - \frac{1}{T}\left(\frac{F}{K_0}-1\right)^2
$$

This is a perfectly valid analytical quantity. It is just not available at 09:10, because $C_{\mathrm{hedge}}$ depends on the realized intraday SPX path and $C_{\mathrm{opt\ close}}$ depends on the day-end payoff.

> If realized ES hedge cash or realized option close cash were folded into Kvar, the result would no longer be a signal-time implied strike. It would become an ex-post realized net-strike measure for that day.

That is a different object, and using it directly in the trading signal would introduce lookahead.

### What we could do at 09:10 but currently don't

At 09:10, you could in principle define an *expected* all-in strike by replacing the realized path-dependent terms with expectations:

$$
K_{\mathrm{eff,expected}} = K_{\mathrm{open}} - \mathbb{E}[TC_O] - \mathbb{E}[TC_{Fw}] - \mathbb{E}[\text{hedge drag}] - \mathbb{E}[\text{hedge slippage}]
$$

That would still be a signal-time quantity, because every adjustment is an expectation formed before the trade. The current implementation does **not** estimate those expectations. It only deducts the explicitly booked transaction-cost cash buckets from `output.json`.

For audit purposes, the realized cash flows are still surfaced as separate columns so the decomposition can be inspected after the fact:

- `option_open_cash`
- `option_close_cash`
- `futures_hedge_cash`
- `full_day_pnl_cash`

set at [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L470) and [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L474).

---

## Step 8: The daily extraction pipeline

Putting all the per-day pieces together, the end-to-end extraction is `extract_all_exec_kvar()` in [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L390). For each day it:

1. parses opening option legs (Step 1),
2. infers the same-day forward,
3. parses option and futures TC cash (Step 2),
4. decomposes trade cashflows for audit columns (Step 3),
5. computes the gross strike (Step 6),
6. computes the option-TC-adjusted strike (Step 7),
7. computes the full-friction strike (Step 7),
8. saves all outputs into the daily row.

The extra output columns are attached in:

- gross series: [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L460)
- option-TC-adjusted series: [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L464)
- futures TC cash: [src/volforecast/data/gsvivs_kvar.py](src/volforecast/data/gsvivs_kvar.py#L471)

---

## Step 9: How the cache is loaded and used

The processed parquet is loaded by `load_exec_kvar_cache()` in [src/volforecast/data/edrvol.py](src/volforecast/data/edrvol.py#L1080), which returns the `kvar_vol_pct` column at [src/volforecast/data/edrvol.py](src/volforecast/data/edrvol.py#L1094). So the dashboard and backtest consume the full-friction effective strike by default.

In the tournament pipeline it is wired into `iv_exec_kvar` at [src/volforecast/evaluation/tournament.py](src/volforecast/evaluation/tournament.py#L1229), labeled `Exec Kvar (true fill)` at [src/volforecast/evaluation/tournament.py](src/volforecast/evaluation/tournament.py#L1245), and passed into `kvar_rv_gap_signal()` at [src/volforecast/evaluation/tournament.py](src/volforecast/evaluation/tournament.py#L1575).

One last conversion happens inside the signal: the calendar-annualized Kvar is converted into trading-day annualization using

$$
K_{\mathrm{var,252}} = K_{\mathrm{var,365}} \sqrt{\frac{252}{365}}
$$

at [src/volforecast/evaluation/economic_value.py](src/volforecast/evaluation/economic_value.py#L148). This ensures the Kvar is on the same trading-day basis as our RV forecasts before the IV-RV gap is taken.

---

## Output columns reference

The regenerated parquet contains at least:

- `kvar_vol_pct` — full-friction effective strike (the default we use as IV).
- `kvar_gross_vol_pct` — gross quantity-aware strike.
- `kvar_option_tc_vol_pct` — option-TC-adjusted strike.
- `option_tc_cash`
- `futures_tc_cash`
- `all_tc_cash`
- `replication_scale` — the inferred $N$ from Step 4.
- `weight_fit_cv` — diagnostic for how textbook-shaped the quantities were.
- `option_open_cash`
- `option_close_cash`
- `futures_hedge_cash`
- `full_day_pnl_cash`

---

## How to read the three strike series

The implementation answers three different questions cleanly:

1. *What strike is implied by the opening strip fill prices alone?* → `kvar_gross_vol_pct`.
2. *What strike is implied after deducting option execution frictions?* → `kvar_option_tc_vol_pct`.
3. *What strike is implied after deducting all explicitly booked execution frictions?* → `kvar_vol_pct` (the default).

What it deliberately does **not** do is invert the entire realized day P&L into a synthetic strike by pushing realized ES hedge cash or realized option close cash into the opening implied variance term. That would create an ex-post realized net-strike measure rather than a signal-time strike proxy, and using it as a signal would introduce lookahead.

---

## Validation

The implementation was validated with:

- quantity-proportionality tests in [src/tests/unit/test_gsvivs_kvar.py](src/tests/unit/test_gsvivs_kvar.py#L255),
- TC parsing and monotonic net-strike tests in [src/tests/unit/test_gsvivs_kvar.py](src/tests/unit/test_gsvivs_kvar.py#L305),
- full backtest integration tests in [src/tests/integration/test_kvar_integration.py](src/tests/integration/test_kvar_integration.py#L92).

---

## Summary

The earlier implementation was a gross fill-based model-free strike proxy — useful but missing both the strip's executed size and any notion of friction.

The current implementation improves on it in three ways:

- it uses the actual traded strip quantities to infer the replication scale $N$,
- it deducts option and futures transaction costs using the separate raw cash buckets from `output.json`,
- it preserves the gross, option-net, and full-friction variants side by side for auditability.

That makes the default `Exec Kvar (true fill)` materially closer to the *effective net strike* the strategy actually sold, while still keeping the object in the domain of a signal-time opening-strike proxy rather than an ex-post full-day P&L inversion.

The whole construction is, again, a stopgap. The moment a clean 0DTE IV from the vol surface is available, this reverse-engineered Kvar can be retired (or kept as a useful cross-check), and the IV-RV gap signal can consume the surface-based number directly.
