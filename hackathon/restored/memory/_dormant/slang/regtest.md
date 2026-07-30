---
created: 2026-04-23
updated: 2026-04-30
tags: [slang, regtest, fastest, stubs, mocks, testing, procm, ut]
status: dormant
immutable: true
relates:
  - slang/best-practices.md
  - slang/moxie.md
  - slang/lint-edit.md
---

# Slang RegTest & FasTest

Extracted from `slang/best-practices.md` — RegTest stubs, mocks, FasTest framework, and test-specific conventions.

## RegTest Stubs

- Constant stub → assign directly (no lambda): `Stubs."lib::fn" = Structure( "Beta" := 1.0 );`
- **In `Structure( key, value )` stub definitions:** Lambda wrappers returning constants (`\Ellipsis( _ ) -> Value`) are unnecessary — assign the constant directly as the value. This applies to *all* constant types: scalars, arrays, structures, `TdsArray(...)`, `TdsDB(...)`.

```slang
// WRONG — lambda wrapper for a constant value
Stubs = Structure(
    "lib::fn", \Ellipsis( _ ) -> [ Structure( "K", "V" ) ],
    "lib::g",  \Ellipsis( _ ) -> TdsArray( [ Structure( "A", 1 ) ] ),
    "lib::h",  \Ellipsis( _ ) -> True,
);

// RIGHT — direct constant assignment
Stubs = Structure(
    "lib::fn", [ Structure( "K", "V" ) ],
    "lib::g",  TdsArray( [ Structure( "A", 1 ) ] ),
    "lib::h",  True,
);
```

### Stub Scope — Only Stub Tested Code Paths

Before adding a stub (or a `Private::Mock` function), trace the call graph of the function(s) under test. **Only stub functions that are reachable from the tested code paths.** Do not stub functions that exist in the _LIB but are never called by the tests.

- If a function is only called by `Foo` and you only test `Bar`, don't stub it.
- Don't add `Link( "_LIB X" )` just for a mock/stub of an untested function — unnecessary Links increase load time and lint noise.
- If you discover a stub never fires (test runtime unchanged with/without it), remove it.

### Preferred: FasTest Wrapper (shared stubs)

When all tests share stubs: define a **single** wrapper that builds stubs inline, tag tests with `FasTest-wrap-with:`. Lint traces `FasTest-wrap-with` annotations, so **no LintPragma** is needed for the wrapper function (adding one causes Status-2 "Unused global pragma").

**MUST merge stubs into wrapper.** Having a separate `Private::Stubs` function that is only called by `Private::Stub Wrapper` is an anti-pattern — it adds an unnecessary function, an extra doc comment block, and a call overhead for zero benefit. Define stubs directly inside the wrapper.

```slang
/****************************************************************
**  Routine: Private::Stub Wrapper
**
**  Applies shared stubs and runs the test function.
****************************************************************/
Private::Stub Wrapper = Func(
    Slang( Test Fn ),
)
Returns( Slang() )
{
    Stubs = Structure(
        "lib::Foo", 42,
        "lib::Bar", Null,
    );

    Return(
        Lambda()
        {
            RegTestStubFunction( Stubs )
            {
                @Test Fn();
            };
        }
    );
};

// In test doc comment:  FasTest-wrap-with: Private::Stub Wrapper
```

**`FasTest-wrap-with` belongs ONLY in test function doc comments** — never in the wrapper's own doc comment. The wrapper doesn't wrap itself; adding it there is misleading and may confuse FasTest routing.

```slang
// WRONG — separate Stubs function only called by Stub Wrapper
Private::Stubs = Func() Returns( Structure() ) { ... };
Private::Stub Wrapper = Func(
    Slang( Test Fn ),
)
Returns( Slang() )
{
    Return( Lambda() { RegTestStubFunction( @Private::Stubs() ) { @Test Fn(); }; } );
};

// RIGHT — stubs defined inline in the wrapper
Private::Stub Wrapper = Func(
    Slang( Test Fn ),
)
Returns( Slang() )
{
    Stubs = Structure( ... );
    Return( Lambda() { RegTestStubFunction( Stubs ) { @Test Fn(); }; } );
};
```

### Fallback: Local Variable (per-test stubs)

When tests need **different stubs**, use a local variable inside each test:

```slang
Stubs = Structure( "lib::fn" := True );

RegTestStubFunction( Stubs ) { ... };
```

### RegTestStubFunction Scope

Variables assigned inside `RegTestStubFunction { ... }` are **NOT visible outside** the block. Keep `Assert` calls **inside** the block — otherwise the result variable is undefined and assertions silently don't run (0 assertions, no error).

```slang
// WRONG — Result is undefined outside the block, Assert silently skipped
RegTestStubFunction( Stubs ) { Result = @Foo(); };
Assert( "msg", Size( Result ) == 1 );

// RIGHT — Assert inside the block
RegTestStubFunction( Stubs )
{
    Result = @Foo();
    Assert( "msg", Size( Result ) == 1 );
};
```

### FasTest Assertion Count

Always verify the **total assertion count** matches expected. "4 Passed, 0 Failed, 0 Errors" looks clean but if you expected 6, two tests silently produced zero assertions.

### Prefer Meaningful Assertions Over AssertNoException

`AssertNoException` only verifies the function didn't throw — it says nothing about correctness. **Use it only when no more meaningful assertion is possible** (e.g., void-like functions with side effects that can't be inspected).

If the function returns a value, assert on it:

```slang
// WRONG — lazy, doesn't verify correctness
AssertNoException( @Private::Calculate( 10, 2 ) );

// RIGHT — verifies actual behavior
Result = @Private::Calculate( 10, 2 );
Assert( "Calculate 10/2", Result == 5 );
```

**When AssertNoException IS appropriate:**
- Function returns nothing meaningful (`Returns()`)
- Side effects can't be inspected (e.g., writes to external system, stubbed out)
- Smoke test: just confirming the code path doesn't crash with given inputs

### Anti-patterns

- Do NOT declare stubs as script-level `Private::` variable.
- Do NOT inline `Structure(...)` inside `RegTestStubFunction(...)` — always pass a variable.
- Do NOT use sequential `RegTestStubFunction` blocks with the **same** stub variable. Merge assertions into a single block — each `RegTestStubFunction` has non-trivial setup/teardown cost, and splitting identical-stub blocks adds noise for zero benefit.
- Do NOT create a `Func()` that returns a constant — assign the constant directly in the stub structure. A stub function that ignores its arguments and returns a fixed value is unnecessary overhead.
- Do NOT write **tautological (dummy) assertions** — stubs that return a canned value paired with an assert that merely checks the canned value back. This tests the stub, not the code. Every assertion must exercise real logic.

```slang
// WRONG — tautological: stubs Null, asserts Null — tests nothing
Stubs = Structure( "lib::Get Data" := Null );
RegTestStubFunction( Stubs )
{
    Result = @Private::Process();
    Assert( "Result is null", IsError( Result ) );
    // ^^^ This always passes because the stub forces Null.
    // It proves the stub works, not that Process() handles Null correctly.
};

// RIGHT — test the LOGIC, not the stub
// Test 1: Verify the function handles missing data gracefully
Stubs = Structure( "lib::Get Data" := Null );
RegTestStubFunction( Stubs )
{
    Result = @Private::Process();
    Assert( "Returns fallback on missing data", Result == "N/A" );
    // ^^^ Verifies Process() produces the correct fallback value.
};

// Test 2: Verify the function processes real data correctly
Stubs = Structure( "lib::Get Data" := {| "Price" := 100.0, "Qty" := 5 |} );
RegTestStubFunction( Stubs )
{
    Result = @Private::Process();
    Assert( "Computes notional correctly", Result == 500.0 );
    // ^^^ Verifies Process() actually multiplies Price * Qty.
};
```

**Rule of thumb:** If removing the stub would not change the assertion outcome, the test is tautological. A meaningful test must verify a **transformation, decision, or side-effect** that the code-under-test performs on the stubbed input.

```slang
// WRONG — unnecessary function wrapper for a constant
Private::Mock Get Beta = Func(
    Ellipsis( _ ),
)
Returns( Double() )
{
    Return( 1.05 );
};
Stubs = Structure( "lib::fn", Private::Mock Get Beta );

// RIGHT — assign the constant directly
Stubs = Structure( "lib::fn", 1.05 );

// RIGHT — assign a constant structure directly
Stubs = Structure( "lib::fn", {| "Beta" := 1.0, "Gamma" := 0.5 |} );
```
// WRONG — redundant blocks with identical stubs
RegTestStubFunction( Stub )
{
    AssertNoException( @Foo( "A" ) );
};
RegTestStubFunction( Stub )
{
    AssertNoException( @Foo( "B" ) );
};

// RIGHT — single block, multiple assertions
RegTestStubFunction( Stub )
{
    AssertNoException( @Foo( "A" ) );
    AssertNoException( @Foo( "B" ) );
};
```

### Only `@`-Called Functions Can Be Stubbed

`RegTestStubFunction` only stubs `@`-called user functions. **Native functions** (`UpdateSecurity`, `GetValue`, `Size`, etc.) cannot be stubbed. To mock a native: wrap it in a `Private::` function in the _LIB, call the wrapper with `@`, stub the wrapper.

### Cross-Library Stub Key Format

To stub a function from another library, the key must be `"<script>::<full_function_name>"`. For namespace-qualified functions, include the FULL function name including the namespace prefix:
- Function `Foo::Bar` defined in `_LIB Foo` → key is `"_LIB Foo::Foo::Bar"` (NOT `"_LIB Foo::Bar"`)
- The test script must `Link` the library that defines the function
- Do NOT create wrapper functions to avoid cross-library stubs — just use the correct key format

**Failure mode:** If the stub key is wrong, the stub **silently doesn't fire** — the real function runs with no error message. Symptoms: test takes much longer than expected, unexpected live data appears, or `TableInit` errors from unstubbed code paths. Always verify stubs fire by checking test runtime or adding a debug assertion in the stub body.

### No UpdateSecurity in RegTests

RegTests must never update securities. Wrap `UpdateSecurity` in `Private::Update Security` in _LIB, call `@Private::Update Security()`, stub it in tests. Also stub library wrappers like `MktData::UpdateSecurity`.

## Mock Functions

- Named `Func()` with doc comment (for `AllFunctionsDocumented`).
- Suppress unused args: single → `LintPragma( "Ignore apparently unused ArgName" );`, multiple → `LintPragma( "Function with required signature" );`
- **CRITICAL: LintPragma is LINT-ONLY.** It is parsed by the lint AST analyzer but causes **hard compile errors** at FasTest runtime. If a mock function will execute during tests, **never use LintPragma inside it**. Instead:
  - Use all args in a harmless guard: `If( !Container Name && Rest ) Return( Null );`
  - Or match the real function signature exactly (no unused params)
  - Or use `Ellipsis( _ )` to silently discard all args
- If mock ignores ALL args, use `Ellipsis( _ )` as sole parameter:

```slang
Private::Mock Foo = Func(
    Ellipsis( _ ),
)
Returns( Double() )
{
    Return( 0.0 );
};
```

- **Never use factory pattern for mocks.** The mock must BE the function itself, not a `Func() Returns( Slang() )` wrapper that returns the real mock. Reference the mock directly (without `@` call) in stub structures:

```slang
// WRONG — factory returning a Func
Private::Mock Fn = Func() Returns( Slang() ) { Return( Func( String( X ) ) Returns( Any() ) { ... }; ); };
// WRONG — calling the factory
Structure( "lib::fn", @Private::Mock Fn() )

// RIGHT — mock IS the function
Private::Mock Fn = Func(
    String( X ),
)
Returns( Any() )
{
    Return( Null );
};
// RIGHT — reference directly (no @, no ())
Structure( "lib::fn", Private::Mock Fn )
```

## Date Usage in RegTests

- **Never `Today()`** — use `Pricing Date( "Security Database" )`.
- Build date series with `ForEach` + `ComponentEnsure` over offset strings, not individual variables.

## Stub Heavy Computation Functions for Performance

When a function under test calls expensive sub-functions (charting, table generation, complex formatting, nested loops over large datasets) whose output **isn't asserted by the test**, stub them with minimal return values. Unstubbed heavy functions are the #1 cause of slow RegTests.

**Symptoms:** Test passes but takes minutes. FasTest `Suite took` shows unexpectedly high time.

**Pattern:** Identify the call graph of the function under test. For each callee:
- If its return value feeds an assertion → must stub with realistic mock data.
- If its return value is NOT asserted (e.g., stored to S3, displayed, logged) → stub with minimal skeleton (empty array, empty structure).
- One behavior per test. Names: `Private::Test <Subject> <Scenario>`.

## Testing `_PROCM` and `_UT` Scripts

**You CANNOT add a RegTest directly to a `_PROCM` or `_UT` script.** Process scripts (`_PROCM`) run under scheduler contexts and utility scripts (`_UT`) run under execution contexts that are both incompatible with the FasTest framework.

**Required pattern — extract to `_LIB`, test the `_LIB`:**

1. **Move all functions** (except the main entry point) from the `_PROCM` / `_UT` script into a `_LIB`:
   - If a closely-related `_LIB` already exists → move functions there.
   - Otherwise → create a new `_LIB` (e.g., `_LIB Eq1D Brazil Foo Fns` for `_PROCM Eq1D Brazil Foo`).
2. **Keep only the main entry function** in the `_PROCM` / `_UT`. It should `Link` the `_LIB` and delegate to its functions.
3. **Create a `Test:` script** that `Link`s the `_LIB` and tests the extracted functions via FasTest.

```
_PROCM Eq1D Brazil Foo          ← entry point only, Links _LIB
  └─ _LIB Eq1D Brazil Foo Fns   ← all logic lives here
       └─ Test: Eq1D Brazil Foo  ← RegTest targets the _LIB

_UT Eq1D Brazil Bar              ← entry point only, Links _LIB
  └─ _LIB Eq1D Brazil Bar Fns   ← all logic lives here
       └─ Test: Eq1D Brazil Bar  ← RegTest targets the _LIB
```

This is a **hard rule** — never attempt to work around it by adding `Test:` functions inside a `_PROCM` or `_UT`. Always extract to a `_LIB` first.

## FasTest Framework

xUnit-like test runner. Discovers `Private::Test ...` functions automatically. Call `@FasTest::Go(...)` at script end.

- Options: `Protect := True` (catch per-test), `Assert Is Guard := True`.
- **Do NOT pass `Database := Database( "RegTest Scratch" )`** — just `@FasTest::Go( "Eq1D.NYC.Intl" );`. The database is handled by the secexpr invocation, not the Go call.

### Lifecycle

| Function | When |
|---|---|
| `Private::Setup Suite` | Once at start |
| `Private::Setup` | Before every test |
| `Private::Teardown` | After every test |
| `Private::Teardown Suite` | Once at end |

All optional. **MANDATORY: remove empty lifecycle functions** (empty body `{}`) — including their doc comment. Diddles from Setup/Setup Suite are available to tests.

Typical: Setup Suite → random seed, shared configs. Setup → reset state, mock data. Teardown → rarely needed.

### Parameterized Tests (`FasTest-params`)

```slang
// In doc comment: FasTest-params: Private::Size Cases
Private::Test Size = Func(
    Any( Input ),
    Double( Expected ),
)
Returns()
{
    Assert( "Size matches", Size( Input ) == Expected );
};

Private::Size Cases = [ [ "", 0 ], [ "foo", 3 ], [ {||}, 0 ] ];
```

- Param variable at **script-level** (not Setup Suite — params resolve before lifecycle).
- Param types: `Array(Array())`, `Array(Structure())`, TDS, `TableInit(...)`, keyed Structure.
- Param args come **first** in function signature.

### FasTest-wrap-with

In doc comment: `FasTest-wrap-with: Private::Stub Wrapper`. Combining with params: param args first.

**CRITICAL placement rule:** `FasTest-wrap-with:` MUST be the **last line** in the doc comment before `****/`, AND must be preceded by a **blank comment line** (`**`) to visually separate it from the description. FasTest reads everything after `FasTest-wrap-with:` to the end of the comment as the parameterizer name. If description text follows the annotation, it gets concatenated into the name and the annotation is silently ignored (tests run without stubs, causing "Object modified" or other errors).

```slang
// WRONG — description after annotation gets parsed as part of the name:
/****************************************************************
**  Routine: Private::My Function
**
**  FasTest-wrap-with: Private::Stub Wrapper
**  Brief description of what this function does. <-- FasTest reads this as part of the name!
****************************************************************/

// WRONG — no blank line before annotation (hard to read, easy to merge into description)
/****************************************************************
**  Routine: Private::My Function
**
**  Brief description of what this function does.
**  FasTest-wrap-with: Private::Stub Wrapper
****************************************************************/

// CORRECT — blank line separator + annotation is the last line:
/****************************************************************
**  Routine: Private::My Function
**
**  Brief description of what this function does.
**
**  FasTest-wrap-with: Private::Stub Wrapper
****************************************************************/
```

### Skip / Focus

- `FasTest: skip` — always skips. `FasTest: focus` — runs only focused tests.

### Running

```powershell
secexpr NullDb --source "~user!clean;PS" --safe -s "Test Script Name"
secexpr --safe "test script" "Case1" "Case2" -s "_UT FasTest"
```

## Modifying the _LIB for Testability

When creating a new RegTest, you ARE expected to modify the underlying `_LIB` to make tests easier or possible. The `_LIB` is not frozen — refactor it as needed:

- Extract native/system calls (`UpdateSecurity`, `TDS Query`, `Load Data`, etc.) into `Private::` wrapper functions so they can be stubbed.
- Split large functions into smaller testable units.
- Add optional parameters for injectable dependencies.
- Make implicit global state explicit (pass as arguments instead of reading environment).

This is the standard workflow: **write the test → discover what's hard to test → refactor the _LIB → stub the wrappers → verify**.

## Setting the Test Script on the _LIB (MANDATORY)

After creating a `Test:` script for a `_LIB`, you **MUST** set the `Test Script` field in the `_LIB`'s script header to point to the test script name. This is a **hard rule** — not setting it is an anti-pattern.

**Why:**
- Links the library to its test for discoverability.
- Enables CI/FasTest infrastructure to find and run associated tests.
- Lint and ScriptReview can validate test coverage.

**How:** Edit the `_LIB` script header via SLANG_EDIT and set `Test Script := "Test: Foo Bar"` (the full script name including the `Test:` prefix).

## DB Propagation Lag After SLANG_EDIT Rewrite

After `slang-edit` with `--rewrite` saves successfully (`changed=1 saved=1`), the script is persisted to SecDB. However, **subsequent FasTest runs may still see the previous version** for 1-2 executions due to SecDB caching/propagation. This manifests as:

- Errors referencing lines from the OLD file (wrong line numbers)
- Compile errors for code that was already fixed
- Stale terminal output showing previous run results

**Fix:** Simply re-run the FasTest task. The second or third run will pick up the current version. **Never fall back to `run_in_terminal`** — this is a propagation timing issue, not a task issue.

## RegTest Script Header Requirements

The script header for a `Test:` script must include these fields **in order**:

```
** Script Name : Test: Foo Bar
** Script Type : RegTest
** Summary     : RegTest for _LIB Foo Bar
** Test Script : Test: Foo Bar
** Notifyees   : EL{gs-eq-strats-dev}
** Created     : 30Jan26
** Log         :
** Description :
**     <description text>
**
** Copyright 2026 - Goldman, Sachs & Co. - New York
```

**Key rules:**
- `** Log :` MUST come **before** `** Description :` — if placed after, lint reports "Script Header missing 1 fields: Log"
- `** Test Script :` should reference the test script itself (self-reference) — this is for SecDB VT metadata registration
- The header metadata property "Test Script" is separate from the text — `secexpr --safe` rewrite sets the header text but the VT property may need one more save cycle to sync

## RegTest Execution Environment

RegTests run in the **"RegTest Scratch"** database — NOT NullDb. This means:

- **Real securities are available.** `Asset Name( "Eq PETR4.SA 0" )` resolves correctly.
- **Never claim "NullDb limitations"** when discussing what's possible in RegTests.
- The secexpr invocation command uses `NullDb` in the syntax (`secexpr NullDb --source ...`) but the actual execution context is RegTest Scratch.
- You can use `GetSecurity(...)` and `Asset Name(...)` to obtain real security objects for testing.

## Private:: Function Visibility

**`Private::` functions are truly private to their defining script.** You CANNOT call them from a test script, regardless of qualifier format:

- `@Private::Foo()` → resolves to `~Test Script::Private::Foo`, NOT the _LIB's private function
- `@_LIB Foo::Private::Bar()` → "could not find function" error — cross-script Private access is blocked

**Consequences for testing:**
- You must test private logic **through the public API** (namespace-prefixed functions).
- Use stubs to control inputs to the public functions, which internally call Private:: helpers.
- If a Private:: function contains critical logic that needs direct testing, consider making it a namespace-prefixed (public) function in the _LIB.

## Inline Structure Syntax in Stubs

Use `{| "key" := value |}` for inline structure literals:

```slang
// WRONG — Structure("key" := value) throws "Expected even number of args"
Stubs = Structure( "lib::fn", Structure( "Price" := 100.0 ) );

// RIGHT — use {| ... |} for inline structures
Stubs = Structure( "lib::fn", {| "Price" := 100.0, "Qty" := 5 |} );

// ALSO RIGHT — positional (key, value) pairs without :=
Stubs = Structure( "lib::fn", Structure( "Price", 100.0 ) );
```

**Why:** `Structure(...)` with `:=` uses named-argument syntax but the function expects positional pairs. The `{| ... |}` literal supports `:=` assignment syntax natively.
