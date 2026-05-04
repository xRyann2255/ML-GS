# Guide to the Avellaneda & Stoikov Strategy — Hummingbot

**Source:** https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/
**Used in:** Ch 8 (Market making / Avellaneda–Stoikov)

## Model overview

The A–S model addresses two concerns jointly:
1. Inventory risk management
2. Optimal bid/ask spread determination

Two formulas:

- **Reservation price:** shifts the reference price based on current inventory, risk aversion, remaining time, and volatility.
- **Optimal spread:** determines the half-width around the reservation price based on order-book liquidity and risk aversion.

## Parameters (practitioner view)

### Reservation price variables

- **`q` — inventory deviation from target.** When `q = 0`, the reservation price equals mid. Negative q (short) raises the reservation price to pull in buys; positive q (long) lowers it to pull in sells.
- **`γ` — risk aversion.** Trader-set. Near zero keeps reservation near mid; larger values aggressively adjust toward the target inventory.
- **`T − t` — remaining session time.** As end-of-session approaches, the model pulls the reservation price back toward mid to flatten inventory risk. Hummingbot allows configurable session duration (relevant for 24/7 crypto).
- **`σ` — volatility.** Automatically estimated from recent price history. Higher σ widens the gap between reservation and mid.

### Spread variables

- **`κ` — order-book depth / arrival intensity.** Denser books (higher κ) → tighter optimal spread. Thinner books (lower κ) → wider optimal spread.

## Execution logic

1. Compute reservation price given target inventory.
2. Compute optimal half-spread.
3. Place orders at:
   - Bid = reservation − (optimal spread / 2)
   - Ask = reservation + (optimal spread / 2)

## Configuration knobs in Hummingbot

- Maximum / minimum desired spread (caps on the analytic optimal)
- Risk aversion parameter (values near 1 = conservative)
- Inventory target percentage (what fraction of portfolio should sit in the base asset)
- Closing time (session length — critical for `T − t`)
- Volatility buffer size (window for `σ` estimation)
- `easy mode`: Hummingbot auto-calibrates `κ` and `γ`; otherwise set `order_book_depth_factor` and `risk_factor` manually by disabling `parameters_based_on_spread`

## Notes for the PDF

- Pair this with the original Avellaneda–Stoikov paper (local copy: `Avellaneda_Stoikov_2008_LimitOrderBook.pdf`). Paper gives the derivation; Hummingbot guide gives the operational tuning intuition.
- The "what does each parameter feel like in practice" framing is what makes this blog post useful — reproduce that flavour in Ch 8's practitioner-notes box.
