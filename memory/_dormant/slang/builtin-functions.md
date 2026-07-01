---
created: 2026-04-14
updated: 2026-04-14
tags: [slang, functions, builtins, introspection, functioninfo]
status: active
relates:
  - slang/language.md
  - slang/research.md
  - slang/utility-libs.md
  - slang/builtin-functions-ref.md
---

# Slang Builtin Functions — Quick Reference

## Introspection Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `Functions()` | All standard builtin function names | Array (~44,500) |
| `Functions( True )` | Deprecated function names only | Array |
| `Functions( Internal := True )` | Internal function names only | Array |
| `FunctionInfo( "Name" )` | Detailed info for one function | Structure |

## FunctionInfo Structure

Fields returned by `FunctionInfo( "SomeName" )`:

| Field | Type | Example |
|-------|------|---------|
| **DllPath** | String | `slang`, `slangs`, `x_core` |
| **FilePath** | String | C source file path (may be empty) |
| **FuncName** | String | Internal SlangX name (e.g. `_SlangXPrint`) |
| **Line Number** | Number | Source line number (0 if unavailable) |
| **name** | String | Slang-visible function name |
| **ParseFlags** | Number | Internal parser flags |
| **Usage** | Structure | Nested — see below |

**Usage** sub-structure:
- **Arguments** — indexed array of `{Datatype, Description, Flags, name}` per arg
- **ReturnType** — `{Datatype, Description, Flags}`
- **Text** — human-readable usage string with examples and comments

## secexpr Patterns

```slang
// Print all function names (one per line)
ForEach( f, Functions() ) { Print( f, "\n" ); };

// Get detailed info for a specific function
Print( FunctionInfo( "ForEach" ) );
```

**Note:** `PrintLn()` does not exist in Slang. Use `Print( value, "\n" )` for line breaks.

## Detailed Reference

See **[slang/builtin-functions-ref.md](builtin-functions-ref.md)** for a curated reference of **385 functions** across 20 categories (Control Flow, Type System, Math, Array, String, Structure, TDS, SecDB Core, etc.) with signatures, return types, and descriptions.

## Cached Full List

A full dump of `Functions()` (~44,500 names, 1.3 MB) is at `workspace/tmp/slang-functions-list.txt`. Re-run the introspection expression to refresh — the list may grow with SecDB updates.
