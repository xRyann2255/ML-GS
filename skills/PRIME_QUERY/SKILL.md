---
name: PRIME_QUERY
description: Query Prime security details (identifiers, classification, builder, instrument metadata) from GS2ClassificationView by PrimeId or sector-specific lookup
---

# PRIME_QUERY — Prime Security Lookup

> **Purpose:** Fetch Prime security data from the EPSSP `GS2ClassificationView` page — identifiers, classification, builder assignment, instrument metadata — for a given PrimeId or sector-specific YAQL query.

**Out of scope:** Modifying Prime data, bulk batch queries, or Bloomberg data retrieval.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `PRIME_QUERY` |
| **Scope** | Read-only Prime security lookup |
| **Inputs** | A YAQL selector (PrimeId, ticker) + optional Sector |
| **Outputs** | Console summary + JSON in `workspace/tmp/` |
| **Authority** | Read-only (GSSSO auth) |

## When to Use

- Look up **identifiers** for a PrimeId: Ticker, ISIN, CUSIP, GSSymbol, GSNumber, PrimaryExchangeRIC, BID.
- Check what **Builder** GS2 assigned (EUROBOND, STOCK, etc.) and the classification map row that matched.
- Inspect **instrument metadata**: InstrumentType, InstrumentSubType, Currency, Country, MarketType, IssueStatus, IssuerLegalName, Description.
- Debug **booking/classification issues**: which builder was selected, what classification codes apply, settlement currency, trade-to-settle delay.
- Query by **sector** (Stocks, StockOptions, Futures, etc.) instead of raw PrimeId.

Do **not** use for:
- Modifying Prime records → use PDQ tickets.
- Bulk enumeration of all securities in a sector.
- Real-time pricing or market data → use **PYTHON_MARKET_DATA**.

## Connection

| Field | Value |
|-------|-------|
| **URL** | `https://strategy.eq.gs.com/ssps/ProdSource/GS2ClassificationView?Sector={sector}&Select={select}` |
| **Auth** | GSSSO cookie |
| **Response** | HTML page with classification + Prime data-frame tables |

### Sectors

Default sector is `PrimeId`. Other available sectors:

| Category | Sectors |
|----------|---------|
| Equities | `Stocks`, `StockOptions`, `StockIndices`, `CFD` |
| Futures | `Futures`, `FuturesOptions`, `RollingFutures` |
| FX | `Currencies`, `PADCurrencies` |
| Fixed Income | `CorporateDebt`, `GovernmentDebt`, `MunicipalDebt`, `EuroBonds`, `EmergingMarketDebt`, … |
| PAD | `PADStocks`, `PADFutures`, `PADFunds`, `PADIndices`, `PADWarrants` |
| Other | `MM`, `NBBO`, `OSD`, `UPS`, `VADER`, `EMM`, `ETFTV`, … |

## Usage

```bash
# Lookup by PrimeId (default sector)
uv run python skills/PRIME_QUERY/src/prime.py 1000294460

# Multiple PrimeIds
uv run python skills/PRIME_QUERY/src/prime.py 1000294460 1000843846

# Specify a sector (auto-follows disambiguation to full PrimeId results)
uv run python skills/PRIME_QUERY/src/prime.py --sector Stocks VALE3

# List disambiguation matches without following
uv run python skills/PRIME_QUERY/src/prime.py --sector Stocks --no-follow VALE3

# JSON output only
uv run python skills/PRIME_QUERY/src/prime.py --json 1000294460

# Select specific fields
uv run python skills/PRIME_QUERY/src/prime.py --fields Ticker,ISIN,Currency,Builder 1000294460
```

### Disambiguation

Non-PrimeId sectors (e.g. `Stocks`) often return a disambiguation page listing multiple products that match the query. By default the script **auto-follows** each match to fetch full Prime data. Use `--no-follow` to just list the PrimeId/description/CUSIP without fetching details.

## Output Sections

The page returns three data sections, all parsed into JSON:

### 1. Builder

The GS2 builder assigned to this security (e.g. `EUROBOND`, `STOCK`).

### 2. Classification Map

The `usf_classification_map` row that matched. Fields: Brady, Builder, couponType, InstrumentSubType, instrumentType, IssueCurrency, IssueMarket, IssuerCountry, IssueType, MarketType, MaturityType, PrincipleStruct, Type.

### 3. Data Frame (Prime Security)

~100+ slot name/value pairs. Key fields include:

| Field | Example |
|-------|---------|
| `Ticker` | \*PETR4 |
| `ISIN` | BRPETRACNPR6 |
| `CUSIP` | 9FIA0KXP2 |
| `GSSymbol` | \*PETR4 |
| `GSNumber` | 0186B2 |
| `PrimaryExchangeRIC` | PETR4.SA |
| `PrimaryExchangeBID` | PETR4 BS |
| `Currency` | BRL |
| `Country` | Brazil |
| `instrumentType` | STOCK |
| `InstrumentSubType` | PREF |
| `Builder` | EUROBOND |
| `IssuerLegalName` | PETROLEO BRASILEIRO S A PETROBRAS |
| `IssueStatus` | ISS |
| `IssueStatusDescription` | Active, trading normally |
| `MarketType` | DOMESTIC |
| `settlementCurrency` | BRL |
| `TradeToSettleDelay` | 2 |
| `PrimeID` | 1000294460 |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 Unauthorized | GSSSO cookie expired — script auto-obtains it |
| Empty data frame | PrimeId may not exist or sector mismatch — try `PrimeId` sector with numeric ID |
| `Product Calculator` error in HTML | Normal for some securities — data frame still parses correctly |
| Wrong security | Verify PrimeId is numeric; for ticker-based lookups, use the correct Sector (e.g. `Stocks`) |
| Multiple matches | Non-PrimeId sectors return disambiguation pages — script auto-follows by default |
| `WARNING: Sector expects ...` | Selector format doesn't match sector — e.g. sending a ticker to `PrimeId` sector |
| Table structure changed | Parser falls back to title-text matching if `summary` attributes shift |

## Task-Based Execution

**Task label:** `prime-query` | **Args file:** `workspace/tmp/prime_query_args.json`

Preferred. Write args JSON, then `run_task("prime-query")`. CLI args pass through via `%*`.

## Links

- memory/ref/gssso-auth.md — GSSSO authentication (used for Prime API)
