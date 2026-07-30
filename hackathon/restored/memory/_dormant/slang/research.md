---
created: 2026-04-09
updated: 2026-04-16
tags: [ref, slang, research, glimpse, elps, enghub, functions, introspection]
status: dormant
relates:
  - sys/enghub.md
  - ref/skill-scripts.md
  - slang/utility-libs.md
---

# Slang Research Sources

When looking up Slang functions, usage examples, references, or implementations, use **all** of these sources — not just EngHub.

## SLANG_GLIMPSE (primary for code search)

Skill: `skills/SLANG_GLIMPSE/` — searches the Slang script database directly.

- **Best for:** finding function usages, call sites, examples, implementations, imports (Link statements), RegTest stubs, and discovering which scripts use a given function or pattern.
- **Default backend:** ELPS (Elasticsearch) for Slang indices (`slangprod`, `slangdev`, `slanguser`, `slangarch`). Falls back to Glimpse (TCP socket) if no results.
- **Field search:** `--field references` (who references a function), `--field defines` (who defines it), `--field name` (script name search), `--field comments`.
- **Key flags:** `--files-only` (script names only), `--no-comments` (skip comment lines), `--max-results N`.
- **Example:** Find all callers of `Glimpse::Find`: `glimpse.py --index slangprod --query "Glimpse::Find" --max-results 20`
- **Example:** Find scripts that reference `Array::Diff`: `glimpse.py --index slangprod --query "Array::Diff" --field references --files-only`

## slang/utility-libs.md (quick reference for common libs)

Memory file: `memory/slang/utility-libs.md` — lists commonly available Slang library scripts.

- **Best for:** quickly recalling which utility libraries exist (`_LIB Array Functions`, `_LIB Structure Functions`, `_LIB String Functions`, etc.) without needing a search.
- **Use before SLANG_GLIMPSE** when you just need to remember the name of a standard library.

## Functions() / FunctionInfo() (builtin introspection)

Builtin Slang functions — no skill or external tool needed.

- **Best for:** looking up exact function signatures, argument names/types, return types, and usage text for Slang builtins.
- **`Functions()`** returns an array of ~44,500 standard builtin function names.
- **`FunctionInfo( "Name" )`** returns a structure with DllPath, Arguments, ReturnType, and human-readable usage text.
- **Details:** `memory/slang/builtin-functions.md`

## EngHub (primary for documentation)

Skill: `skills/ENGHUB/SKILL.md` — searches GS internal documentation.

- **Best for:** conceptual docs, API references, system architecture, configuration guides, onboarding material.
- **Not good for:** finding specific Slang function call sites or code examples.

## Unknown Syntax — Always Glimpse First

**Never fabricate Slang syntax.** The language is proprietary and undocumented externally. If unsure about a syntax form, **always** search Glimpse for production examples before answering. Use `--query "Spec::String"` style searches. If Glimpse returns 0 results, the syntax likely does not exist — say so rather than inventing.

## When to use which

| Need | Source |
|------|--------|
| "How is `Foo::Bar` used?" | SLANG_GLIMPSE |
| "Which scripts call `Foo::Bar`?" | SLANG_GLIMPSE (`--field references`) |
| "What standard utility libs exist?" | slang/utility-libs.md |
| "What does `Foo::Bar` do?" | SLANG_GLIMPSE (find definition) + EngHub (docs) |
| "How do I configure system X?" | EngHub |
| "Show me examples of TDS queries" | SLANG_GLIMPSE |
| "What's the API for service Y?" | EngHub |
| "Does syntax X exist in Slang?" | SLANG_GLIMPSE (search for it) — never guess |
