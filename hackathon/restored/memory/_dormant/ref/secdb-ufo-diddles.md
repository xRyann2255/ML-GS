---
created: 2026-04-14
updated: 2026-04-14
tags: [ref, secdb, ufo, class, vt, diddles, diddlescope, privacy, inheritance, debugging, breakpoints]
status: dormant
relates:
  - ref/secdb-graph.md
  - slang/best-practices.md
  - slang/lint-edit.md
---

# SecDB UFO Classes, Diddles & Debugging

Split from `ref/secdb-graph.md`. Covers UFO class system, diddle mechanics, and graph debugging.

---

## UFO Class System

*Universal Financial Objects* (UFOs) define SecDB classes in Slang. Legacy classes are C++ (GOBs).

### DefineClass / DefineInterface

```slang
DefineClass( "Demo Option" )          // streamable — objects can be saved to DB
DefineClassNonStreamable( "Foo" )     // in-memory only
DefineInterface( "Demo Option Interface" )  // contract — VT name + return type
```

- **Streamable** classes serialize objects as BLOBs (metadata + Class/Type ID, no schema). Changing attributes needs extra care — deserialization depends on the UFO script source.
- All classes registered in `_LIB Class Declarations XXX` scripts using `DeclareClassWithSeq`:

```slang
DeclareClassWithSeq( x, y, "Demo Option", "UFO Demo Option" );
DeclareClassWithSeq( x+1, y+1, "Demo Option Interface", "UFO Demo Option Interface", SLANG_DEFINE_CLASS_INTERFACE );
```

### @TableInit and VT Handlers

VTs are defined inside `@TableInit` as arrays: `[ "VT Name", ReturnType(), VTType, ...handlers ]`.

| Handler | Purpose |
|---------|---------|
| `@Stored` | Instream — persisted to DB. **Order matters** (serialization). |
| `@Retain` | Calculated once, retained until invalidated. Lost on session end. |
| `@Calc` | Calculated VT (pure function). |
| `@Get( FnName )` | Getter function for `@Calc` VTs. Signature: `Func( Self, VTI )`. |
| `@Set( FnName )` | Custom setter (enables `SetValue` on `@Calc` VTs). |
| `@Data( value )` | Default value. |
| `@Alias( "OtherVT" )` | Delegation — returns value of another VT on the same security. |
| `@Child( "InStreamVT" )` | Delegation — evaluates VT on the security referenced by the instream. |
| `@Public` | Makes VT publicly accessible (when Graph Privacy is on). |
| `@Diddleable` | Allows diddles on this VT (when Graph Privacy is on). |

**Convention:** UFO script name = `UFO <ClassName>`, VF script = `UFO <ClassName> VF`. Class name ≤ 30 chars.

### Graph Privacy

Opt-in per class in `_LIB Class Declarations`:
```slang
DeclareClassWithSeq( x, y, "Demo Option", "UFO Demo Option", SLANG_DEFINE_CLASS_GRAPH_PRIVACY_ON );
```

When privacy is ON, VTs default to **private and non-diddleable**. Must explicitly add `@Public` and/or `@Diddleable` to each VT that should be accessible or simulatable.

### Inheritance & Composition

```slang
@TableInit( [
    @InheritClass( "Base Class" );
    @InheritValue( "Denominated" );   // inherit this instream
    @DisinheritValue( "OtherAttr" );  // explicitly exclude (needed if multiple inheritance + name collision)
    @InheritReplace( "Base Class", "Expiration Date", [ @Get( My New Get ) ] ),  // override a VT
    @ImplementInterface( "Demo Option Interface" ),  // interface check — must provide all VTs
    ...
] );
```

- `Ufo::Super( Self, VTI )` calls the base version of a VT (same args only — can't add new args).
- `@Alias( "VTName" )` — simple delegation to another VT on Self.
- `@Child( "UnderlyingInstream" )` — delegation to VT on a referenced security.
- Abstract classes supported. Browse with `_UT Class Inheritance Browser`, `_LIB Class Functions`.

---

## Diddles

A **diddle** is a temporary alteration of a value for what-if analysis. Does not modify DB contents.

### SetDiddle

```slang
SetDiddle( Spot( "USD/GBP" ), 1.42 );           // Value Reference form
SetDiddle( "Spot", "USD/GBP", 1.42 );           // String form
Spot( "USD/GBP" ) = 1.42;                        // Legacy direct assignment
```

Always wrap in `Check()` to catch errors.

### SetValue vs SetDiddle

| | SetValue | SetDiddle |
|---|---------|-----------|
| **Persistence** | Permanent (saved to DB on `UpdateSecurity`) | Temporary (scoped) |
| **Applicable to** | `@Retain`, `@Stored`, or custom `@Set` VTs | Any VT by default (restricted by Graph Privacy) |
| **Scope** | Session-permanent; `@Stored` survives save | Removed by Restore or scope exit |

### Restore (Remove Diddles)

```slang
Restore( Spot( "USD/GBP" ) );   // specific node in current scope
Restore( "USD/GBP" );           // all VTs on a security in current scope
Restore();                       // all diddles in current scope
```

`Restore` only removes diddles in the **currently active scope**.

### WhiteoutDiddle

Restores a node to its **"true" (undiddled) value** even inside a diddle scope:
```slang
Eval { Spot( "JPY/USD" ) = 100; Eval { WhiteOutDiddle( Spot( "JPY/USD" ) ); /* true value here */ }; };
```

---

## Diddle Scopes

### Global Scope

Script starts here. Diddles persist until `Restore()`.

### Eval Scope (Temporary)

All diddles within `Eval {}` auto-removed on block exit. Nestable — creates a stack of diddle values.

### Diddlescope (Persistent)

Creates a **virtual database** layer (`!1`, `!2`, ...). Persists beyond the `DiddlescopeUse` block.

```slang
DS = DiddleScopeDefine() { SetDiddle( Pricing Date( "Security Database" ), Date( "31Jan22" ) ); };
DiddleScopeUse( DS ) { Check( Expiration Date( Sec ) ); };
```

**On-graph Diddlescopes:** Attach `Diddlescope()` as a VT return type → lifetime tied to the node.

**Off-graph Diddlescopes:** Caution — Slang tries to reuse off-graph Diddlescopes, so unexpected diddles from prior evaluations may persist.

### Node Split vs Share

- When a Diddlescope has relevant diddles, entering `DiddlescopeUse` causes a **node split** — a new node for the DS layer.
- If no relevant diddles exist, nodes are **shared** (DbSet gets extended).

### UseDatabase ≠ Diddle Scope

`UseDatabase` does NOT create a diddle scope. `Restore()` inside one `UseDatabase` block removes diddles across all databases.

---

## Value Method / Value Reference / VTApply

Graph expressions can be constructed programmatically:

```slang
Spot( "USD/GBP" )                                // Value Method — direct VT call
V = VTApply( [ Value Type( "Spot" ) ] );
( V )( "USD/GBP" );                              // VTApply — construct then apply
Value Reference( "Spot", "USD/GBP" );            // Value Reference
Node = SecDb Node( Spot( "USD/GBP" ) );
Node.ValueReference();                            // From SecDb Node (no DbSet capture)
```

Used as input to graph addins like `ForChildren`:
```slang
ForChildren( Child, Spot( "USD/GBP" ), , , _Tree )
    Print( Child, "\n" );
```

---

## Debugging

### TraceOn (Block-Scoped)

```slang
TraceOn( TRACE_PRINT )
    Check( SetDiddle( Pricing Date( "Security Database" ), Today() - 5 ) );
```

**Trace flags** (combinable with `+`): `TRACE_VERBOSE`, `TRACE_PRINT`, `TRACE_STEP`, `TRACE_MESSAGE`, `TRACE_SKIP_ERRORS`, `TRACE_NO_REFRESH`, `TRACE_STOP`, `TRACE_START_ON_ERROR`, `TRACE_CLASS_INFO`.

**Tip:** Execute the code first, then wrap a second execution in `TraceOn` for less noise.

### SecDbTrace (Global Toggle)

```slang
SecDbTrace( TRACE_VERBOSE + TRACE_SKIP_ERRORS );  // turn on
SecDbTrace( TRACE_STOP );                          // turn off
```

### SecDb Node (Debugging Pointer)

```slang
N = SecDb Node( Expiration Date( Sec ) );
// Pointer to node — inspection only, may become invalid
```

### UFO Breakpoints

```slang
UfoBreakpointSet( "VTName", "ClassName" [, [ MessageTypes ], Condition ] );
UfoBreakpointClear( "VTName", "ClassName" );
```

**Message types:** `UFO_BREAKPOINT_GET_VALUE`, `UFO_BREAKPOINT_SET_VALUE`, `UFO_BREAKPOINT_SET_DIDDLE`, `UFO_BREAKPOINT_CHANGE_DIDDLE`, `UFO_BREAKPOINT_INVALIDATE`, `UFO_BREAKPOINT_SPLIT_NODE`.

**Conditional breakpoints:**
```slang
UfoBreakpointSet( "Spot", "Cross", [ UFO_BREAKPOINT_SET_DIDDLE ],
    \x -> String( x.Object.Value ) == "USD/GBP" );
```

Also settable via VS Code Slang extension: **UFO BREAKPOINTS** TreeView → **+** → select class → VT → message type.
