---
created: 2026-04-14
updated: 2026-04-16
spec-expanded: 2026-04-16
tags: [ref, slang, language, types, operators, control-flow, functions, scopes, constants, arrays, structures, typed-structures, lambdas]
status: dormant
relates:
  - ref/secdb-graph.md
  - slang/best-practices.md
  - slang/formatting.md
  - slang/headers.md
---

# Slang Language Reference

Distilled from EngHub `secdb-platform-docs` (slang/ + platform/ products, Feb 2025).

---

## Language Properties

- Interpreted, dynamically typed, case-insensitive.
- C-like syntax with `;` statement terminators.
- No traditional keywords — `If`, `While`, `For`, etc. are function-style constructs.
- Variable and function names may contain spaces.
- Functions are first-class values (assignable, passable).
- Block expressions return values.
- If nothing is explicitly returned, a function returns `Null`.
- `:` is the else operator (not a keyword).
- `@` prefix required for calling user-defined functions.
- `//` line comments, `/* ... */` block comments.

---

## Data Types

| Type | Constructor / Literal | Description |
|------|----------------------|-------------|
| `Double` | `100.5`, `Double()` | Floating-point numeric. Also represents Boolean (1=True, 0=False). |
| `String` | `"text"`, `String()` | Character string. |
| `Boolean` | `True`, `False` | Logical (syntactic sugar for Double 1/0). |
| `Null` | `Null` | Missing / undefined value. |
| `Date` | `Date( "21Mar25" )` | Calendar date. Literals: `DDMMMYY`. |
| `RDate` | `RDate( "3b" )` | Relative date (number + time unit: `b`=business days, `m`=months, `y`=years, etc.). |
| `Time` | `Time()` | Calendar date + time. Supports time arithmetic. |
| `Array` | `[ 1, 2, 3 ]`, `Array()` | Ordered, heterogeneous, zero-indexed. |
| `Structure` | `{⎮ "K" := V ⎮}`, `Structure( "K", V )` | Key-value container, **case-insensitive** string keys. |
| `StructureCase` | `{\ "K" := V \}` | Key-value container, **case-sensitive** string keys. |
| `GStructure` | `GStructure( key, val; ... )` | Key-value container, **arbitrary key types** (arrays, structures, doubles, etc.). |
| `Curve` | `Curve( [ Date, val, Date, val ] )` | Indexed collection of dates and values (time-series). |
| `Binary` | `Binary()` | Raw binary memory block. |
| `Slang` | `Slang( expr )` | Parsed Slang expression (code as data). |
| `Security` | `Security()` | SecDB object reference. |
| `Diddlescope` | `Diddlescope()` | Graph diddlescope object. |

Any data type name acts as a constructor: `Double( 3 )`, `String( X )`.

---

## Operators

| Category | Operators |
|----------|-----------|
| Arithmetic | `+`, `-`, `*`, `/` |
| No built-in | modulo → `Mod()`, power → `Pow()`, size → `Size()` / `DataTypeInfo()` |
| Unary | `-`, `!`, `++`, `--` |
| Assignment | `=`, `+=`, `-=`, `*=`, `/=`, `&=` (append) |
| Comparison | `==`, `<`, `>`, `<=`, `>=`, `!=`, `<=>` (spaceship) |
| Logical | `&&`, `⎮⎮`, `!` |
| Special | `@` (user fn call), `&` (pass-by-ref), `::` (scope), `.` (member access), `[]` (index), `$` (literal delimiter), `++` (concat/union), `` ` `` (infix) |

---

## Control Flow

| Construct | Syntax |
|-----------|--------|
| If / Else | `If( cond ) { ... } : { ... };` |
| While | `While( cond ) { ... };` |
| For | `For( init; cond; mod ) { ... };` |
| ForEach | `ForEach( elem, array ) { ... };` |
| ForComponent / ForComponentValue | Iterate structure keys / key-value |
| ForChildren | Iterate graph children |
| ForClass | Iterate all classes |
| ForSecurity | Iterate objects of a class: `ForSecurity( Instance, "ClassName" ) { /* Instance is each sec */ };` |
| ForFile | Iterate matching files |
| ForSQLQuery | Iterate SQL result rows |
| ForValue | Iterate VTs on an object |
| Switch | `Switch( var, val1, code1, ..., defaultCode );` |
| Typecase | Type-based dispatch |
| Try / Catch | `Try( excVar ) { ... } : { handler };` |
| Throw | `Throw( value );` |
| Break / Continue | Loop control |
| Finally | `Finally { ... };` — always runs |

---

## Scopes

| Scope | Syntax | Rule |
|-------|--------|------|
| Local | `Var` (no prefix) | Default. Exists within the function block only. |
| Global | `Global::Var` | Available throughout the script. **Discouraged.** |
| Private | `Private::Var` | Script-local. Parser rewrites to `~ScriptName::Var`. |
| Named | `MyScope::Var` | Globally available but namespaced. Requires explicit `::`. |
| Protected | `Protected::Var` | Shared across libraries via `ShareProtectedScope`. |
| Module | `Module::Var` | Brief mention — no detailed rules in current docs. |

### Scope Sharing

```slang
SharePrivateScope( "_LIB Top" );   // share Private:: across sub-libraries
ShareProtectedScope( "_LIB Top" ); // share Protected:: while keeping separate Private::
```

Must be the **first statement** in a script. Use with library stubs only.

### Scope Functions

- `Scope( scopeName, varName )` — access variable in a named scope
- `Scopes()` — enumerate all active scopes
- `Variables()` — enumerate variables in current scope

---

## Constants

- 1300+ built-in constants. Replaced by numeric values at parse time.
- Common prefixes: `WK_` (keystrokes), `EIC_` (colors), `DLG_`, `ERROR`, `CHART2D_`.
- User-defined: `Constant( MY_CONST, 42 );` — define in libraries only.
- `EvalOnce( expr )` — evaluate once, treat as constant. **Do not abuse** as lint workaround.
- An expression is constant if all its parts are constants or `EvalOnce`.

---

## Functions

### Definition

```slang
Scope::Fn Name = Func(
    Double( Arg1 ),
    String( Arg2 ) = "default",     // optional positional
    Named Arg := 10,                // named argument (requires default)
)
Returns( Double() )
{
    Return( Arg1 + Arg2 );
};
```

- Built-in functions: called directly (`Print`, `Sort`, `If`).
- User-defined: require `Link( "script" )` and `@` prefix to call.
- `Returns( Type1(), Type2() )` — one value, multiple acceptable types (not a tuple).
- **`Null()` is NOT a valid DataType Creator in `Returns()`.** Using `Null()` causes a runtime parse error: `"Returns(): Arguments must be DataType Creators or Null"`. Valid creators: `Security()`, `String()`, `Number()`, `Double()`, `Slang()`, `Any()`, `Array()`, `Structure()`, `Date()`, `Boolean()`. If a function can return null, just omit Null from Returns — Slang handles it implicitly.

### No Function Overriding

Slang does NOT support function overriding or redeclaring. A function name can only be declared **once** across all linked scripts. Never re-declare a function from a linked library in another script (e.g. to "add a parameter"). Instead, modify the original function in its own library, or create a new wrapper function with a different name.

### Arguments

| Kind | Syntax | Rule |
|------|--------|------|
| Positional | `Double( Arg )` | Required, order matters |
| Optional positional | `Double( Arg ) = default` | Must follow required args |
| Named | `Arg := default` | Must have default. Called with `:=` at call site. |
| Pass-by-reference | `& Arg` | Both declaration and call site need `&`. Must pass a variable, not a literal. |

- Default values evaluated in declaration order; may reference earlier params.
- Hybrid: required positional → optional positional → named (call site must follow same order).

### Value Specs (Preconditions)

Constraint annotations placed after the parameter name inside the type constructor. Runtime rejects values that violate the spec before the function body executes.

**Syntax:** `Type( ParamName, Spec::Type( ... ) )`

```slang
// String constraints
Spec::String( Must Be One Of := [ "1d", "1m", "1y" ] )       // enum of allowed values
Spec::String( Min Size := 3 )                                  // minimum length
Spec::String( Must Match Pattern := RegExP( "^\d{4}$" ) )     // regex match

// Numeric constraints
Spec::Double( Min Value := 0, Max Value := 1 )
Spec::Double( Must Be One Of := [ 1, 2, 3 ] )

// Date constraints
Spec::Date( Min Value := Today() )

// Array constraints
Spec::Array( Min Size := 1, Max Size := 10, Element Spec := "String" )
Spec::Array( Exact Size := 2, Element Spec := Spec::Array( Element Spec := "String" ) )
```

**Usage in function signatures:**

```slang
// Constrain Tenor to allowed values; Env to allowed list with default
Private::My Func = Func(
    String( Tenor, Spec::String( Must Be One Of := [ "1d", "1m", "1y" ] ) ),
    String( Env, Spec::String( Must Be One Of := [ "DEV", "QA", "PROD" ] ) ) := "PROD"
)
{
    Return( Tenor );
};
```

### Lambdas & Closures

```slang
Square = \x -> x * x;
Add = \x, y -> x + y;

// Multi-statement lambda
Counter = Lambda() { Return( i++ ); };

// Closure — captures i
New Counter = Func() { i = 0; Return( Lambda() { Return( i++ ); } ); };
```

- Lambdas called with `@`: `@Square( 5 )`.
- Support default and named arguments.
- `Lambda` = `Func` that captures enclosing environment.
- Infix: `(\x -> x + 1) \`Mapcar\` Array`.

### Functional Library

`Link( "_LIB Functional" );` — provides `Bind1of2`, `Bind2of2`, etc.

---

## Arrays

```slang
A = [ 1, "two", 3.0 ];     // mixed types
A = Array();                 // empty
A = ArrayInitialize( n, val ); // n elements of val
```

- Zero-indexed. `Size( A )` for length. `Back( A )` for last element.
- `A &= elem;` — append.
- `A ++ B` — concatenate (also `ArrayConcat`, `Array::Concat`).
- `A[: start, end :]` — slice (returns `TypeSlice` — wrap in `Array()` for regular array).
- Copy-on-write semantics on assignment.

| Function | Purpose |
|----------|---------|
| `ArrayInsert( A, idx, count )` | Insert null slots before idx |
| `ArrayDelete( A, idx, count )` | Remove elements |
| `Sort( A, comparator )` | In-place sort. `<=>` for comparator. O(n log n) |
| `ArrayUnique( A, sortFirst )` | Remove duplicates (must be sorted). O(n log n) |
| `Array::Unique Stable( A )` | Remove duplicates preserving order |
| `Array::Splice( A, idx, count, replacements )` | Remove+insert |
| `Mapcar( fn, A )` | Map function over array |
| `Foldl( fn, init, A )` | Left-fold/reduce |
| `ValueExists( A, val )` | Membership test |
| `LSearch( A, val )` | Linear search → index or -1 |
| `BSearch( A, val )` | Binary search (requires sorted) |
| `SortTable( A, keys )` | Sort array of structures by component names |

**Complexity:** Index access O(1), insert/delete O(n), sort O(n log n).

---

## Structures

```slang
S = {| "Name" := "John", "Age" := 30 |};
S = Structure( "Name", "John", "Age", 30 );
S.City = "New York";                          // add field
```

- Case-insensitive keys (use `StructureCase` for case-sensitive).
- **Dot access is significantly faster** than `[]` for literal keys. Use `[]` only for dynamic keys.
- `S.Keys()`, `S.Values()`, `S.UnsortedKeys()`.
- `StructureUnion( A, B )` — merge B into A (existing A keys untouched).
- `A ++ B` — structure union shorthand.
- Punning: `{| Book Name |}` means `Book Name := Book Name`.
- Destructuring: `{| X, Y |} = S;` extracts fields into local variables.
- `StructureFromKeys( keyArray, valueArray )` — build from parallel arrays.
- `DtStructureKeyCaseSet` — explicitly set/preserve key casing.

### GStructure

```slang
G = GStructure( [ 1, 2 ], "Hello"; {| "X" := "Y" |}, "World"; 123.45, "Number" );
```

Arbitrary key types. Different hash function. Performant for large data sets.

---

## Typed Structures

```slang
// Non-streamable (in-memory only)
TypeDefine( "MyScope::MyType" )
{
    Members()
    {
        String( Name );
        Double( Value ) = 0;
    };

    My Method = Func( Self ) { Return( Self.Name ++ ": " ++ String( Self.Value ) ); };
};

// Streamable (persistable, requires unique ID)
TypeDefineStreamable( 12345, "MyScope::StreamType" )
{
    Members() { ... };
};
```

- Instantiate: `MyScope::MyType()`.
- `Self` refers to current instance inside methods.
- Inheritance: `Members( "BaseType" ) { ... };`. Override methods. `Self.Super(...)` calls base.
- Non-streamable types require `Link( "_TYPE MyScope::MyType" )` where used.
- Streamable types registered in `_LIB Typed Structure Decl`.

### Reference Counting

- Add `Double( _RefCount )` member → instance is passed by reference, not value.
- Assigning one variable to another shares the same instance (no copy-on-write).
- **Cyclic references cause memory leaks.**
- Constructors are `EvalOnce` by default → repeated `TypeName()` can return the same instance.
- Force new: `New( "MyScope::MyType" )` or `TypedStructureClone( existing )`.

### Reflection

- `TypeInfo( "TypeName" )`, `Structure( instance )`, `DataType::Names()`, `DataType::Info()`.
- `DataType::Is Typed Structure( info )`, `Typed Structure::Components( instance )`.

---

## Script Structure & Naming

Standard script order:
1. Header block (`/****...****/`)
2. `Link( "..." );` statements
3. Function definitions
4. Main script body (if applicable)

Libraries should end with `SmartLinkEnable()` so re-linking doesn't re-parse.

| Prefix | Purpose |
|--------|---------|
| `_LIB` | Library (functions only, no executable body) |
| `_CFG` | Configuration (loaded via `_LIB Config Script`) |
| `_PROCM` | Procmon process script |
| `_SSP` | Slang Server Page |
| `_TYPE` | Typed structure declaration |
| `_UT` | Utility (interactive helper) |
| `_APP` | Stand-alone application |
| `_Const` | Constant library |
| `UFO` | Universal Financial Object class |
| `Test:` | Test script |
| `Example:` | Example script |

---

## SLAM Markup (Documentation)

| Feature | Syntax |
|---------|--------|
| H1 / H2 / H3 | `== H ==` / `=== H ===` / `==== H ====` |
| Bold / Italic | `'''bold'''` / `''italic''` |
| Monospace | `<tt>code</tt>` |
| Bullets / Numbered | `*` `**` / `#` `##` |
| Code block | Lines starting with `>` |
| Preformatted | `<pre>...</pre>` |
| Script link | `[[_LIB Array Functions]]` |
| Function link | `[[@Array::Flatten Unique]]` |
| Review link | `[[Review 20221118 6010-7965408S*]]` |
| Issue link | `[[IS:1234-5678]]` or `[[Jira:MYPRODUCT-1]]` |
| FAQ link | `[[FAQE is SLAM. F2R 0]]` |
| External link | `[https://...]` |

---

## Deployment Surface

| Tool | Purpose |
|------|---------|
| **CVS** | Version control for Slang scripts |
| **ScriptReview** | Code review (required for all changes) |
| **FasTest** | Test runner (RegTest execution) |
| **Zebra Farm** | Remote test execution platform (successor to RAMS) |
| **Procmon** | Runtime platform for scheduled `_PROCM` scripts |
| **PLEX** | Distributed computing platform for SSPs |
| **SecExpr** | Command-line Slang evaluator |
| **TOPS** | Entitlement system for SecDB permissioning |
| **Safe / Full mode** | Operational modes (Safe = no Production writes) |
| **Managed Slang** | Onboarding for managed runtime |
