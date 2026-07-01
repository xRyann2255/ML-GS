---
created: 2026-03-26
updated: 2026-04-30
tags: [slang, formatting, style, code-style]
status: active
relates:
  - slang/best-practices.md
  - slang/lint-edit.md
---

# Slang Formatting Rules

## Indentation (MANDATORY)

- ALWAYS **4 spaces**. NEVER tabs. Replace tabs with 4 spaces when editing.
- When generating Slang via `create_file` (for `--rewrite`/`--content-file`), verify no tabs with `Select-String "`t"` before writing to SecDB.

## Function Call Parentheses (MANDATORY)

ALL function calls MUST include `()`, even with no arguments: `@Private::Stubs()` not `@Private::Stubs`.

## Function Definition Arguments (MANDATORY)

In `Func(` definitions, arguments MUST be on the **next indented line** — never on the same line as `Func(`. This applies even when the signature would fit on one line. Always include a trailing comma after the last argument.

```slang
// WRONG — args on same line as Func(
Private::Stub Wrapper = Func( Slang( Test Fn ) )
Returns( Slang() )

Private::Mock Foo = Func( Ellipsis( _ ) )
Returns( Double() )

// RIGHT — args on next indented line with trailing comma
Private::Stub Wrapper = Func(
    Slang( Test Fn ),
)
Returns( Slang() )

Private::Mock Foo = Func(
    Ellipsis( _ ),
)
Returns( Double() )

// No-arg functions remain on one line
Private::Test Foo = Func()
Returns()
```

## Multi-line Collections, Calls & Structures

When a construct doesn't fit on one line: break **after** the opening delimiter, **one element per indented line** with trailing comma, closing delimiter at original indent.

```slang
// WRONG → RIGHT (arrays, calls, Func, Structure all follow this pattern)
a = [1,                           a = [
2];                                   1,
                                      2,
                                  ];

Fn( "A",                          Fn(
    "B", X := 1 );                    "A",
                                      "B",
                                      X := 1,
                                  );
```

### JSON-Style `{\` / `\}`

`{\` at end of line or own line, each field indented, `\}` on own line. Never put content on same line as `{\` or `\}`.

## Alignment of `=`, `:=`, and Compound Operators

Consecutive lines with `=`, `:=`, `&=`, `+=`, `-=`, `*=`, `/=` (no blank line between) — pad so operators align to same column. Applies to assignments, Func param defaults, named call args.

**Verification (MANDATORY):** After writing aligned blocks (especially `{| |}` datatables), verify programmatically that all operators land on the same column (e.g., `IndexOf(':=')` per line). Do NOT eyeball — off-by-one errors are invisible to the eye. Compute key `.Length`, find the max, pad all to `max + 1` space before the operator.

```slang
// WRONG → RIGHT
Private::S3Db = "Equity";            Private::S3Db     = "Equity";
Private::S3Bucket = "volEst";        Private::S3Bucket = "volEst";

Pre := "B3File",                     Pre    := "B3File",
Suffix := "zip",                     Suffix := "zip",

Stub = @Mock::Stub();                Stub                      = @Mock::Stub();
Stub[ Mock Refresh ] &= Null;        Stub[ Mock Refresh ]      &= Null;
Stub[ "Extra" ] &= True;             Stub[ "Extra" ]           &= True;
```

## Structure Key-Value Pair Alignment

In multi-line `Structure( key, value, key, value, ... )` calls with key-value pairs, **align the value columns** — pad after each key's trailing comma so all values start at the same column. Same alignment principle as `=`/`:=`.

```slang
// WRONG — values not aligned
Result = Structure(
    "Onshore Cash", [ "CashAcct" ],
    "Onshore Cash Arb", [ "ArbAcct" ],
    "FX Tracking", [ "FXAcct" ],
    "BRCT Test Acct # 1 ", [ "TestAcct" ],
);

// RIGHT — values aligned
Result = Structure(
    "Onshore Cash",        [ "CashAcct" ],
    "Onshore Cash Arb",    [ "ArbAcct" ],
    "FX Tracking",         [ "FXAcct" ],
    "BRCT Test Acct # 1 ", [ "TestAcct" ],
);
```

## Preserve Stored-Format Blank-Line Separators

When rewriting a script (`--rewrite`), ALWAYS preserve the original multi-blank separators (3-5 blank lines between sections). Never uniformize all blank spacing to 1-blank — this creates noisy code review diffs full of blank-line additions/removals. Read the original stored source first, note separator patterns, and reproduce them in the new content.

## New/Generated Code — Single Blank Line Between Functions

When writing **new** scripts or adding new functions, use exactly **one blank line** between function definitions (between closing `};` and the next function's doc comment `/**`). Never insert double or triple blank lines — they waste vertical space and reduce readability.

```slang
// WRONG — double blank line between functions
};


/*** Next Function ***/

// RIGHT — single blank line
};

/*** Next Function ***/
```

## Empty Brackets — No Space, No Line Break

`()`, `[]`, `{}`, `{||}`, `{\\}` — no spaces inside, same line. `Func()` not `Func( )` or `Func(\n)`.

## Indexing Brackets — Spaces Inside

When indexing a variable or expression with `[ ]`, always include spaces inside the brackets: `Data[ Pos ]` not `Data[Pos]`. This applies to all subscript access: `Array[ i ]`, `Structure[ Key ]`, `Tds[ "Col" ]`, etc.

```slang
// WRONG
Data[Pos] = Data[Pos] ++ [ Double( Pos + 1 ) ];
Years Total[Yr] += Value;
Parameters = S3 Data[Tier][Range];

// RIGHT
Data[ Pos ] = Data[ Pos ] ++ [ Double( Pos + 1 ) ];
Years Total[ Yr ] += Value;
Parameters = S3 Data[ Tier ][ Range ];
```

## Blank Lines Around Block Statements

Add blank line between assignment and block statement (`ForEach`, `If`, `RegTestStubFunction`, `Try`, etc.) and between block and next assignment.

Exception: consecutive assignments to the **same variable** — no blank line between them.

## One-liners Are Fine When Short

If everything fits on one line: `a = [ 1, 2, 3 ];`

## Brace Placement (Allman Style)

Opening `{` on its **own line**, never on same line as keyword. Applies to `Func`, `Lambda`, `If`, `RegTestStubFunction`, all blocks.

```slang
// WRONG          // RIGHT
Lambda() {        Lambda()
    ...           {
}                     ...
                  }
```

## If/Else Alignment

`:` (else) aligns its statement with the if branch's statement.

**Single-line else:** `:` followed by **3 spaces** then the statement, all on the **same line**. Never put the statement on the next line after a bare `:`.

```slang
// WRONG — statement on next line after bare ":"
If( X )
    Return( [] )
:
    Return( Y );

// RIGHT — single-line else, 3 spaces after ":"
If( X )
    Return( [] )
:   Return( Y );
```

**Multi-line else:** use `{` on the next line (Allman style):

```slang
If( X )
    Return( [] )
:
{
    Y = Compute();
    Return( Y );
};
```

## `RegTestStubFunction` Body Braces

`RegTestStubFunction` body **MUST** always be wrapped in `{ }` — even for a single statement. Bare statement after `RegTestStubFunction(...)` without braces is WRONG.

```slang
// WRONG
RegTestStubFunction( Stubs )
    @Fn();

// RIGHT
RegTestStubFunction( Stubs )
{
    @Fn();
};
```

## Comment Block Closing

No blank `**` line before closing `********/` delimiter.

## Doc Comment — FasTest-wrap-with Separator

When a doc comment includes a `FasTest-wrap-with:` annotation, add a blank `**` separator line between the description and the annotation. The annotation is metadata, not part of the description — visually separate them.

```slang
// WRONG — no blank separator before FasTest-wrap-with
/****************************************************************
**  Routine: Private::Test Foo
**
**  Tests Foo returns expected result.
**  FasTest-wrap-with: Private::Stub Wrapper
****************************************************************/

// RIGHT — blank ** line separates description from annotation
/****************************************************************
**  Routine: Private::Test Foo
**
**  Tests Foo returns expected result.
**
**  FasTest-wrap-with: Private::Stub Wrapper
****************************************************************/
```
