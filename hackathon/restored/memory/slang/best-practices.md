---
created: 2026-03-26
updated: 2026-04-30
tags: [slang, best-practices, coding-style]
status: active
relates:
  - slang/formatting.md
  - slang/lint-edit.md
---

# Slang Best Practices

## RegTest & FasTest

See _dormant/slang/regtest.md — stubs, mocks, FasTest framework, parameterized tests, wrap-with, lifecycle.

## No Function Overriding

Slang does NOT support function overriding or redeclaring. A function name can only be declared **once** across all linked scripts. Never re-declare a function from a linked library (e.g. to "add a parameter"). Instead: modify the original function in its own library, or create a new wrapper function with a different name.

### Wrap UpdateSecurity / RenameSecurity / DeleteSecurity with Check()

`UpdateSecurity`, `RenameSecurity`, and `DeleteSecurity` must always be wrapped with `Check()`:

```slang
Check( UpdateSecurity( Sec ) );
Check( RenameSecurity( OldSec, NewSec ) );
Check( DeleteSecurity( Sec ) );
```

## Lambda

- Multi-line body → **MUST** use `{}` brackets.
- Single-expression → prefer **syntax sugar**: `\Type( Arg ) -> expr;`
- Ignore all args: `\Ellipsis( _ ) -> expr;`
- **Parameter ordering:** Required positional params MUST come before optional/Ellipsis. `Lambda( String( Name ) := "", Ellipsis( _ ) )` is WRONG — runtime error "Required Positional arguments must preceed all optional arguments". Make `Name` required or reorder.
- **Ellipsis default value:** `Ellipsis( Rest ) := Structure()` — default goes **OUTSIDE** the type parens. NOT `Ellipsis( Rest := Structure() )` (causes compile error at runtime). This is the universal Slang pattern: `Type( Name ) := Default`.
- In `StrReplace` string literals: use `"\\Ellipsis"` to store literal `\Ellipsis`.

```slang
// WRONG                                    // RIGHT
Lambda( Any( X ) ) { Return( X + 1 ); };   \Any( X ) -> X + 1;
```

## Prefer Structure Punning

When a variable name matches the desired key, use the shorthand `{| Var |}` instead of `{| "Var" := Var |}`. Never expand punning to the verbose form — it adds noise for zero benefit.

```slang
// WRONG — verbose redundant form
Result = {| "Trades" := Trades, "Date" := Date |};

// RIGHT — punning
Result = {| Trades, Date |};
```

## No Inline Structure Returns

Never return `{| |}` or `Structure()` directly inside `Return(...)`. Assign to variable first.

```slang
// WRONG — both forms
Return( {| "Key" := Value |} );
Return( Structure( "Key1", Value1, "Key2", Value2 ) );

// RIGHT — assign, then return
Result = {| "Key" := Value |};
Return( Result );
```

## Prefer ComponentTestAndGet Over ComponentExists + Extraction

When you need to check if a component exists **and** use its value, use `ComponentTestAndGet( Container, Key, OutVar )` — returns `True`/`False` and assigns to `OutVar` in one call. Avoids the double-lookup of `ComponentExists` followed by `Container[ Key ]`.

```slang
// WRONG — double lookup
If( ComponentExists( Contents, Asset ) )
{
    Entry = Contents[ Asset ];
    ...
};

// RIGHT — single lookup + assignment
If( ComponentTestAndGet( Contents, Asset, Entry ) )
{
    ...
};
```

Note: `ComponentExists` is still correct when you only need the boolean check and do NOT need the value (e.g., in Assert guards, or when the next operation is `Destroy`).

## LintPragma Spacing

Always add a **blank line** after `LintPragma(...)` before the next statement.

## Structure & Date Caveats
- **`StructureAdd`** — broken (scope/component issues). **Never use it.**
- **`ComponentEnsure`** — works, modifies in-place, persists across ForEach. Init with `{||}`.
- **`ForEach`** scopes variable rebinding (new bindings lost outside), but in-place mutation persists.
- **Structure union (`++`)** — merges two structures: `A ++ B`. Prefer over manually copying fields. Example: `Return( Metadata ++ {| Result |} );`
- **`ListAppend`** treats strings as security names. Use `+` for list concatenation.

## Type Checking — Use ValueExists, Not Chained !=

When checking `TypeOf()` against multiple allowed types, use `ValueExists()` — never chain `!=`.

```slang
// WRONG — verbose, error-prone, high cyclomatic complexity
If( Type != "String" && Type != "Double" && Type != "Date" && Type != "Array" && Type != "Structure" )

// RIGHT — compact, maintainable
If( !ValueExists( [ "String", "Double", "Date", "Array", "Structure" ], Type ) )
```

## Slang Runtime Types — TypeOf() Values

`TypeOf()` returns these runtime type strings: `"String"`, `"Double"`, `"Date"`, `"Array"`, `"Structure"`, `"Boolean"`, `"Null"`, `"Binary"`, `"Curve"`, `"RDate"`, `"Slang"`, `"Time"`, `"Security"`.

**`TypeName()` does not exist** — always use `TypeOf( Val )`. See `Switch( TypeOf( Value ), ... )` pattern in SLAM builtins reference.

Key gotchas:
- **`"Number"` is never returned.** All numerics are `"Double"` at runtime. `Number()` is only valid as a DataType Creator in `Returns()`.
- **`True`/`False` are `"Double"` (1/0), not `"Boolean"`.** Only `TrueBool`/`FalseBool` have TypeOf `"Boolean"`.
- **JSON-safe types** for `Jsonify()`: `"String"`, `"Double"`, `"Date"`, `"Array"`, `"Structure"`. Not `"Boolean"` (use `True`/`False` doubles).
  - `"Date"` requires `dateFormat` parameter: `Jsonify( Value, dateFormat := JSON_DATE_FORMAT_ISO_8601 )` — without it Jsonify throws. Constants: `JSON_DATE_FORMAT_NONE=0`, `JSON_DATE_FORMAT_ISO_8601=1`, `JSON_DATE_FORMAT_DT=2`.
  - `"Security"` and `"Time"` (including "Invalid Time") must be converted to `String()` before Jsonify.
  - **`IsError()` and Invalid values**: An "Invalid Time" value has `IsError() == True`. When stripping non-serializable types, do NOT skip error values — they still need conversion: `If( !ValueExists( [...], Type ) && Val != Null )` (no `!IsError` check).
  - **Recursive stripping**: Trade structures from `Instream::Values( Recurse := True )` have deeply nested structures/arrays. Use mutual recursion: `Strip Non Serializable(Structure)` ↔ `Strip Array(Array)` to handle arbitrary nesting.

## Slang `Else If` — NOT Valid After Blocks

`Else If(...)` does NOT work after `}` on a separate line — parser error. Use `If + Continue` chains instead:

```slang
// WRONG — "Value func 'Else If' does not bind a block"
If( X ) { DoA(); } Else If( Y ) DoB();

// RIGHT — use If + Continue inside loops
If( X ) { DoA(); Continue; };
If( Y ) DoB();
```

## Structure Iteration — ForEachComponent, Not _keys + ForEach

Use `ForEachComponent( Key, Val, S )` — never `S._keys` + `ForEach` + manual `S[Key]` lookup. Also wrong: `ComponentNames( S )` — lint flags it as "unregistered vt".

```slang
// WRONG — verbose, S._keys may be unsafe with Destroy mid-loop
Keys = S._keys; ForEach( Key, Keys ) { Val = S[ Key ]; ... };

// RIGHT — single construct binds both
ForEachComponent( Key, Val, S ) { ... };
```

**Direct access** (non-iterating): `S._keys` → Array of key strings, `S._values` → Array of values. Case-insensitive.

## Structure Component Removal — Destroy, Not ComponentRemove

`ComponentRemove( S, Key )` is **wrong**. Use `Destroy( S[ Key ] )` to remove a component from a structure.

```slang
// WRONG
ComponentRemove( S, Key );

// RIGHT
Destroy( S[ Key ] );
```

## Null / Error Checking — IsError + Null Comparison

`Val.IsNull()` is **wrong** (method syntax doesn't exist for Null checking). Use `IsError( Val )` and `Val == Null`.

```slang
// WRONG
!Val.IsNull()

// RIGHT — check both error and null
!IsError( Val ) && Val != Null
```

## Prefer Inline Structure Literals Over ComponentEnsure Chains

Static keys/values → use `{| ... |}` literal. Reserve `ComponentEnsure` for dynamic cases (keys in `ForEach`).

```slang
// WRONG — empty init + chain    →  RIGHT — inline literal
S = {||};                             S = {|
ComponentEnsure( S, "k1", True );         "k1" := True, "k2" := Val,
ComponentEnsure( S, "k2", Val );      |};
```

Prefer `Structure( "Key", Value )` positional — NOT `Structure( "Key" := Value )`. Lint rejects `:=` inside `Structure()`; `:=` syntax is only valid inside `{| ... |}` datatable literals.

## Returns() — Valid DataType Creators

`Returns()` only accepts **DataType Creators**: `Security()`, `String()`, `Number()`, `Double()`, `Slang()`, `Any()`, `Array()`, `Structure()`, `Date()`, `Boolean()`. Multiple return types: `Returns( Security(), String() )`.

**`Null()` is NOT a valid DataType Creator.** Using `Returns( Security(), String(), Null() )` causes a runtime parse error: `"Returns(): Arguments must be DataType Creators or Null"` — but `Null()` here means the function can return null *implicitly*; it's NOT listed as an argument. If a function can return null, just omit it from `Returns()` — Slang handles nullable returns automatically.

## Deleting Multiple Functions (Sequential Pattern)

When removing several functions from a script (e.g. library decomposition), **delete one function per edit call** rather than batching into a single large replacement.

**Why:** Sequential single-function deletes are faster (~4×), 100% reliable, and easier to recover from errors. Large multi-hundred-line replacement blocks are fragile — a single character mismatch silently fails.

**Pattern for each deletion:**
1. Anchor the old text on 2–3 lines of the **preceding function's closing** at the top
2. Include the full target function body
3. Anchor on the **next function's comment header** at the bottom
4. Set new text to just the joining text (preceding close + next header)

**Execution:** Run deletions sequentially — each call succeeds independently (no cascading failures). If one fails, re-read and retry just that one.

## General

- Allman brace style — opening `{` on its own line.
- `@` prefix for ALL function calls, including `Private::`.
- Always `()` on calls, even no-arg: `@Private::Stubs()`.
- `Link()` at top for dependencies.
- `IsError()` + `.Describe()` over `ErrString()`.
- `AllFunctionsDocumented` → every function needs `/** ... */` doc comment.
- **MANDATORY function headers:** ALL Slang scripts must have a top header with a description. If editing a script with an empty/missing header, you MUST fill it in — even if you didn't create the script.
- **MANDATORY Title Case:** ALL function names MUST use Title Case (capitalize each word). `Private::Test Func` not `private::test func`. Applies to `Private::`, namespaced (`Lib::Fn`), and plain function names.

## TDS fstring32 Auto-Typing Gotcha

`TableInit` auto-types short string values (≤32 chars) as `fstring32`. When this TDS is later concatenated (`TdsConcat`) with a TDS whose column is typed `String`, a schema mismatch error occurs.

**Fix:** Use `TdsMapToSchema` to coerce columns to explicit `String()` type:

```slang
Schema = TableInit( [ [ "Col1", "Col2" ], [ String(), String() ] ] );
Result = TdsMapToSchema( MyTds, Schema );
```

This is common in RegTest stubs where `TableInit` with literal string values creates `fstring32` columns, but production code expects `String` columns.

## Avoid Duplicate Code

Extract repeated logic into a shared `Private::` function. Must be **meaningful logic** (multiple statements, conditionals) — not a single-line wrapper. Replace all occurrences with call to new function.

## Prefer Functional Builtins & _LIB Over Manual Loops

Use `Mapcar`, `Foldl`, `Filter` and `_LIB` functions over manual `ForEach` + accumulator **when it simplifies code**:

| Manual Pattern | Replace With |
|---------|-------------|
| `ForEach` + `&=` (transform) | `Mapcar( \x -> expr, List )` |
| `ForEach` + conditional `&=` | `Filter( \x -> cond, List )` |
| `ForEach` + accumulator | `Foldl( \acc, x -> expr, Init, List )` |
| Manual key/value iteration | `ForEachComponent( K, V, S )` |

**Exception:** If the loop body has side effects, multi-statement logic, or early exit — keep `ForEach`.

## Stored Format — Preserve Blank-Line Separators

Two formats: **Stored source** (`edit.py --read`) vs **VFS display** (VS Code explorer). VFS strips inter-line blanks (N stored blanks → N-1 display blanks).

- If `--read` shows "blank line between every line", treat as **CRCRLF capture artifact** — fix the reader, don't rewrite.
- A leading blank line (stored `Chr(10)`) can be removed via `--trim-leading-blank-lines`. Don't do broad whitespace rewrites.
- **Authoring:** max one blank line between logical blocks. No 2+ blank separators.
- **Editing (`--rewrite`/`--content-file`):** ALWAYS preserve the original blank-line pattern. NEVER uniformize to 1-blank — creates noisy diffs.
- **Quality check:** After `--rewrite`, diff old vs new. Many blank-line-only changes = broken separator pattern — fix before review.
