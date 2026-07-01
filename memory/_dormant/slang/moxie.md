---
created: 2026-04-15
updated: 2026-04-15
tags: [slang, moxie, mocking, regtest, typed-structure]
status: active
relates:
  - slang/best-practices.md
---

# Moxie — Typed Structure & Function Mocking

`_TYPE Moxie` provides record/replay style mocks for RegTests. Complements `RegTestStubFunction` — use Moxie when you need to mock **typed structure instances** or need argument-matching control beyond what stubs offer.

## Setup

```slang
Link( "_TYPE Moxie" );
```

## Core API

```slang
// Create a mock expectation for a typed structure
M = Moxie::Typed Structure(
    Type Name := "MyTypedStructure",
);

// Record expectations
M.Call( "MethodName", Arg1 := Value1 ).Returning( ReturnValue );
M.Call( "MethodName", Arg1 := Value1 ).Throwing( ErrorValue );
M.Call Any( "MethodName" ).Returning( ReturnValue );   // matches any args

// Get the mock object (for injection into code under test)
MockObj = M.Get Mock();

// ... execute code that uses MockObj ...

// Verify all expectations were met
M.Verify();
```

## Key Patterns

- **`Call(...)`** — expects exact argument match (named args).
- **`Call Any(...)`** — matches any arguments to the named method.
- **`.Returning(value)`** — sets return value for matched call.
- **`.Throwing(value)`** — makes matched call throw an error.
- **`.Get Mock()`** — returns the mock object to inject into production code.
- **`.Verify()`** — asserts all recorded expectations were called exactly as specified. Fails the test if any expectation was unmet or if unexpected calls were made.
- **"Too many calls made. N/M"** — Moxie error when a mocked method is called more times than expected. Each `.Call(...)` registers exactly one expected invocation.

## When to Use Moxie vs RegTestStubFunction

| Scenario | Use |
|----------|-----|
| Mock a free function (global/library) | `RegTestStubFunction` |
| Mock a typed structure method | `Moxie::Typed Structure` |
| Need argument matching on typed structure calls | `Moxie` `.Call(...)` with named args |
| Need to verify call counts/order | `Moxie` `.Verify()` |
| Simple constant return from a function | Direct assignment in `Stubs` |

## Reference

- `Example: Moxie` — official example script with full patterns
- `_TYPE Moxie` — the type definition script
