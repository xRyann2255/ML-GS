---
created: 2026-04-14
updated: 2026-04-14
tags: [ref, secdb, trade, tradeable, position, book, group, portfolio, booking, inference, naming]
status: active
relates:
  - ref/secdb-graph.md
  - slang/language.md
---

# SecDB Trade Model

Distilled from EngHub `secdb-platform-docs` platform/ product — trading-and-booking chapters.

---

## Core Entities

### Trade

- A **trade** in SecDB is an **event** in the lifecycle of a deal — not the deal itself.
- Trade types: buy, sell, amendment, termination, settlement, and other lifecycle events.
- Every trade must point to a tradeable via `Security Traded Pointer`.
- Minimum booking fields: Security (tradeable), Trade Type, Quantity, Portfolio1, Portfolio2, Trader.
- For derivatives: quantity should be 1 or -1.
- Trades have their own `Dollar Price` VT representing the trade event's value.
- Same-day corrections may be in-place; after EOD, corrections = backout + rebook for audit trail.

### Tradeable

- The **economic object** — encapsulates the full instrument terms.
- Tradeables are **priceables**: expose `Price` and `Dollar Price`.
- Tradeables are **immutable**. Changing economics → create new tradeable.
- Position-bearing tradeables must inherit from `GenericTradeable` interface.
- `Dollar Price` is the cross-product/common-currency aggregation VT.
- FX crosses used for conversion are themselves modeled as tradeables.
- `Normal Spot Cross` = canonical FX quoting convention.

### Position

- The **book-level holding** object built from trades.
- Key attributes: Book Name, Quantity Unit, Next Transaction Date, Expiration Date, Trade IDs.
- Trade IDs provide auditability for how position quantity was formed.
- `Next Transaction Date` — key lifecycle field for coupon/exercise/expiry processing.
- **Do not hand-edit positions.** Use booking/update APIs.

### Book

- Primary container for positions and risk. Behaves like an account.
- Book types: Profit Center Books (trader risk), Customer Books (counterparty exposure), Sales Books, Match Books.
- `Children` returns active non-zero positions. `All Children` includes zeroed/flattened.
- `Leaves` recursively drills to lowest-level components.
- **Position access pattern:** `Database = Trade Database( Group Names( Target )[ 0 ] ); UseDatabase( Database ) Eval { ... Children( Target ) ... };` — `Group Names()` returns an array (take `[0]`), `Trade Database()` returns the trade DB for that group.

### Group

- Parent entity for related books sharing the same `Group` VT.
- Controls entitlements and hosts trade-validation logic.
- Group-level validation scripts run on every booking into the group's books.

### Portfolio

- Aggregation container. Can contain books, groups, or other portfolios.
- Has same aggregation VTs: `Children`, `Leaves`, `Dollar Price`.
- Group portfolios: all books in the group must be leaves of the group portfolio.
- Don't mix books/groups/portfolios arbitrarily.

---

## Trade Fields

| Field | Description |
|-------|-------------|
| `Security Traded Pointer` | Reference to the tradeable |
| `Trade Type` | Buy, sell, amendment, termination, etc. |
| `Quantity` | Amount (1/-1 for derivatives) |
| `Portfolio1` | Booker's perspective (trader's risk book) |
| `Portfolio2` | Counter side (client, salesperson, intercompany, etc.) |
| `Trader` | Trade initiator |
| `Dollar Price` | Trade event value |
| Comments, Unit Price, Currency, Addendum | Optional metadata |

---

## Booking APIs

Use `_LIB TRADE API` wrappers — never ad-hoc writes:

- `TradeAPI::Add` — new trade
- `TradeAPI::Update` — amend trade
- `TradeAPI::Delete` — remove trade

---

## Inference & Naming

- Tradeable names are **deterministic from economics** — not user-entered.
- **Implied name**: generated from economics (product prefix + denomination + maturity + mush hash).
- **Inferred name**: implied name + collision digit.
- **Mush**: hash over selected economic instreams (may include nested components like swap legs).
- Each product/UFO defines which fields participate in the mush.

### GetByInference Workflow

1. Build implied name from economics.
2. Start with collision digit 0.
3. Check if inferred object exists.
4. If no → create it.
5. If yes and exact match → reuse it.
6. If economics equivalent but structure differs → increment collision digit, retry.

### Rules

- Same economics must yield same implied name.
- Non-economic fields can still matter for identity/audit.
- Inconsistent inference → position/risk mismatches from incorrect netting.
- Security name limit: **31 characters**.

---

## Instruments: Fungible vs Contractual

| Type | Description |
|------|-------------|
| **Fungible** | Exists independently of any trade. Interchangeable (e.g. stocks, bonds). |
| **Contractual** | Created only when agreed/signed. Subject to counterparty lifecycle risk (e.g. swaps, options). |

---

## Indices & Performance

- Book position aggregation is index-driven for speed.
- Indices: trades by group/location/time, external trade ID, match IDs, security traded.
- Incremental updates: booking/amending a trade updates only necessary indices/positions.
- Default views focus on live non-zero positions; exclude expired/matured with ~14-day rolling horizon.

---

## Validation

- Group-level validation scripts run on booking.
- Broad base validation + product/region-specific layers.
- Validation latency matters — traders expect near-immediate risk visibility.
