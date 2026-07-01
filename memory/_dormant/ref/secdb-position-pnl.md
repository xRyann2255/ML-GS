---
created: 2026-04-15
updated: 2026-04-15
tags: [ref, secdb, position, pnl, diddle, archive, realtime, book, portfolio, trading]
status: active
relates:
  - ref/secdb-trade-model.md
  - ref/secdb-ufo-diddles.md
  - ref/secdb-graph.md
---

# SecDB Position & PnL Sourcing

How to retrieve positions from books/portfolios and compute PnL in SecDB, covering historical (EOD archive) and realtime (intraday) scenarios.

Reference script: `AHN: Get Position` in `~nunesa!utils`.

---

## Minimal Position Pattern

```slang
Link( "_LIB EOD Archive Procedure" );
Target   = "ISELANIM";
Date     = Today() - 1;
Database = Trade Database( Group Names( Target )[ 0 ] );
UseDatabase( Database )
    Eval
    {
        If( Date != Today() )
            Check( @Archive::DiddlePositions( Target, Date ) );
        Print( Children( Target ) );
    };
```

Key elements:
- `Group Names( Target )[ 0 ]` — resolves the group for a book/portfolio
- `Trade Database( ... )` — gets the trade DB for that group
- `UseDatabase()` — scopes into the trade DB (required for positions)
- `@Archive::DiddlePositions()` — replays historical position state

---

## secexpr Execution Notes

- **Database param** (1st positional arg): Controls security name resolution. Must be a production DB (e.g. `!NYC_Production`) for real securities. `NullDb` cannot resolve real names. `PS` maps to `!NYC_EqVol_Source` (specialized, can't resolve general securities).
- **Source param** (`--source`): Controls where linked scripts are loaded from. Separate from DB. Use `PS` for standard scripts.
- **stdin line-by-line**: Each line is an independent expression. Top-level variables persist. Blocks (`Eval`/`If`/`ForEach`) must NOT span lines.
- **Print() has no newlines**: Use `Sprintf("...\n")` to get line breaks in stdout.

---

## Core Concepts

### Position Access

- **Book/portfolio positions** are accessed via `Children( Sec )` where `Sec` is a book, group, or portfolio security.
- `Children()` returns active non-zero positions. `All Children()` includes zeroed/flattened.
- `Leaves()` recursively drills to lowest-level components.
- Positions are `Structure` keyed by security name → quantity.

### Trade Database

Always wrap position/PnL operations in:
```slang
Database = Trade Database( Group Names( Sec )[ 0 ] );
UseDatabase( Database )
    ...
```
This resolves the group for the security and scopes into the correct trade database.

### Dollar Price

- `Dollar Price( Children( Sec ) )` returns a position-level PnL vector (Structure keyed by security → dollar value).
- Multiply by `Children( Sec )` to get quantity-weighted values.
- `Sum()` aggregates across all positions.

---

## Diddle Modes: Historical vs Realtime

**Key distinction:** Positions and market data exist in two states:
- **EOD archived** (historical) — frozen snapshots from end-of-day archive
- **Realtime** (intraday) — live feeds from market data sources

### Historical Diddles

For any past date (or for yesterday's close):

```slang
// Restore positions to a historical snapshot
Check( @Archive::DiddlePositions( Sec, Date ) );

// Restore market data to a historical snapshot
Check( @Archive::DiddleMktData( Date ) );
```

**Library:** `_LIB EOD Archive Procedure` (namespace `Archive`)

- `@Archive::DiddlePositions( Sec, Date )` — replays the position state as of `Date` by diddling `Children()`.
- `@Archive::DiddleMktData( Date )` — replays all market data (spots, vols, rates, divs) from the EOD archive for `Date`.

Both should always be wrapped in `Check()` to catch errors.

### Realtime Diddles

For today's live/intraday data:

```slang
// Apply realtime market data feed
Check( @Eq Asset::RT Diddle() );

// Create and apply a market-source diddlescope
DS = Market Source DS w Defaults( Source, QuoteSource, TimeSource, Fallback, TimeZone );
DL = SecDbDiddleScopeToArray( DS );
SecDbApplyDiddleState( DL );
```

**Libraries:**
- `_LIB Eq Asset RT Fns` (namespace `Eq Asset`) — `@Eq Asset::RT Diddle()` applies realtime equity asset data.
- `Market Source DS w Defaults()` — builtin that creates a diddlescope from a named market data source (e.g., `"Maia PM Helper"`, `"Maia:Liberty Global"`).
- `SecDbDiddleScopeToArray()` / `SecDbApplyDiddleState()` — convert and apply diddlescope.

### Zone Pricing Environment

For zone-specific pricing (e.g., London close, NY close):

```slang
Config = @Eq RTR Common::Get Config( Zone, "Eq RTR Calc" );
ForComponentValue( ZPE Label, ZPE Func Args, Config.Zone Pricing Env )
    @EqRTRZPE::Execute Diddle Func( ZPE Label, ZPE Func Args, "Calculator" );
```

**Libraries:**
- `_LIB Eq RTR Common Fns` (namespace `Eq RTR Common`)
- `_LIB Eq RTR Zone Prc Env Fns` (namespace `EqRTRZPE`)

If no zone, use the Brazil default: `@Eq1D Brazil::Diddle For All()`.

---

## PnL Decomposition Pattern

The standard Trading + Position PnL split:

```
Yesterday          = DollarPrice(positions_prev,  mktdata_prev)
Today Same Pos     = DollarPrice(positions_prev,  mktdata_today)
Today              = DollarPrice(positions_today,  mktdata_today)

Position PnL  = Today Same Pos - Yesterday     // mark-to-market on unchanged position
Trading PnL   = Total PnL - Position PnL       // impact of new trades
Total PnL     = Today - Yesterday               // end-to-end
```

### Eval Scope Nesting

Each scenario runs inside its own `Eval {}` block so diddles are isolated:

```slang
UseDatabase( Trade Database( Group( Sec ) ) )
    Eval
    {
        // Zone or Brazil default diddles (applied once, outermost Eval)
        ...

        // Filter Date to control position visibility
        Check( SetDiddle( Filter Date( "Book Parameters" ), Date( "1Jan18" ) ) );

        Eval
        {
            // Diddle positions to PREVIOUS date if needed
            If( IsBook || IsPortfolio )
                Check( @Archive::DiddlePositions( Sec, Previous ) );

            Eval
            {
                Check( @Archive::DiddleMktData( Previous ) );
                Yesterday = Dollar Price( Children( Sec ) ) * Children( Sec ) * Qty;
            };

            Eval
            {
                // Today's market data (RT or archive)
                If( Date == Today() )
                {
                    Check( @Eq Asset::RT Diddle() );
                    DS = Market Source DS w Defaults( ... );
                    DL = SecDbDiddleScopeToArray( DS );
                    SecDbApplyDiddleState( DL );
                }
                :   Check( @Archive::DiddleMktData( Date ) );

                Today Same Position = Dollar Price( Children( Sec ) ) * Children( Sec ) * Qty;
            };
        };

        Eval
        {
            // Today's full scenario: market data + actual positions
            If( Date == Today() )
            {
                Check( @Eq Asset::RT Diddle() );
                DS = Market Source DS w Defaults( ... );
                DL = SecDbDiddleScopeToArray( DS );
                SecDbApplyDiddleState( DL );
            }
            :
            {
                Check( @Archive::DiddleMktData( Date ) );
                If( IsBook || IsPortfolio )
                    Check( @Archive::DiddlePositions( Sec, Date ) );
            };

            Today = Dollar Price( Children( Sec ) ) * Children( Sec ) * New Qty;
        };

        Total PnL    = Today - Yesterday;
        Position PnL = Today Same Position - Yesterday;
        Trading PnL  = Total PnL - Position PnL;
    };
```

### Grouping by Security Type

`By Type = \Pnl -> @Structure::Filter( Mapcar( \x -> Sum(x), @Structure::Group By( Pnl, \x -> Sprintf("%s %s", Security Type(x), Denominated(x)) ) ), \x -> x );`

## Key Libraries

| Library | Key Functions |
|---------|-----------|
| `_LIB EOD Archive Procedure` (`Archive`) | `DiddlePositions()`, `DiddleMktData()` |
| `_LIB Eq Asset RT Fns` (`Eq Asset`) | `RT Diddle()` |
| `_LIB Eq RTR Common Fns` / `_LIB Eq RTR Zone Prc Env Fns` | `Get Config()`, `Execute Diddle Func()` |
| `_LIB Market Diddle fns` | `Market Source DS w Defaults()` (builtin) |
| `_LIB Structure Functions` (`Structure`) | `Filter()`, `Group By()` |
| `_LIB Eq1D Brazil Tools` (`Eq1D Brazil`) | `Diddle For All()` |

## Common Pitfalls

1. **Missing `UseDatabase`** — positions live in trade database. Always `UseDatabase( Trade Database( Group( Sec ) ) )`.
2. **Diddle scope leaks** — use `Eval {}` to isolate historical vs realtime. Leaked diddles corrupt pricing.
3. **Position vs single security** — `Children()` only works on books/groups/portfolios.
4. **Filter Date** — `SetDiddle( Filter Date( "Book Parameters" ), Date(...) )` controls position visibility.
5. **RT vs Archive branching** — branch on `Date == Today()`. Don't mix realtime and archive diddles.
6. **Market Source naming** — `Market Source DS w Defaults()` takes names like `"Maia PM Helper"`. Configured per desk/region.
