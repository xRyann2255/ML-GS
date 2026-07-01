---
name: SLANG_CLEANUP
description: Apply Slang best-practice conventions and formatting rules to scripts
---

# SLANG_CLEANUP — Best Practices & Formatting

> **Purpose:** Apply Slang best-practice conventions and formatting rules to one or more scripts. Used standalone or invoked as a sub-step by `SLANG_REGTEST_FIX`.

**Out of scope:** Writing new logic, fixing test failures, or creating code reviews.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_CLEANUP` |
| **Scope** | Audit and fix Slang formatting and best-practice violations |
| **Inputs** | Script name(s), DB path |
| **Outputs** | Updated script content via SLANG_EDIT |
| **Authority** | Write (via SLANG_EDIT) |

## When to Use

- After writing or modifying a Slang script, to normalize formatting.
- As part of the SLANG_REGTEST_FIX workflow.
- When auditing existing scripts for convention compliance.

---

Apply Slang best-practice conventions and formatting rules to one or more scripts.
This skill is used standalone or invoked as a sub-step by `SLANG_REGTEST_FIX`.

## Step 1 — Apply Best Practices

Audit the script(s) against the conventions documented in
memory/slang/best-practices.md.

Key areas to check:

- **RegTest Stubs** — stub patterns, variable assignment, `FasTest-wrap-with` usage
- **FasTest Framework** — Setup Suite / Setup / Teardown lifecycle, parameterized tests, wrap-with pattern
- **Making _LIBs Testable** — wrapping system/VT calls in `Private::` functions
- **Mock Functions / Stubs** — when to use constants vs. mock Funcs, LintPragma usage
- **Determinism** — no live DB lookups, no `Security()`, no `TDS Query`, stub `Load Data`
- **Type Hints** — `Structure` vs `StructureCase`, specific types over `Any`
- **General** — Allman braces, `@` for calls, `()` always, doc comments, test naming

## Step 2 — Fix Formatting

Apply all formatting rules documented in
memory/slang/formatting.md.

Key areas to check:

- **Multi-line Collections** — arrays, calls, Func definitions, Structure literals
- **JSON-style structures** (`{\` / `\}`) — opening on its own line, fields indented, closing on own line
- **Alignment** — `=`, `:=`, and compound operators (`&=`, `+=`, `-=`, `*=`, `/=`) aligned in consecutive lines
- **Empty brackets** — `()`, `[]`, `{}`, `{||}`, `{\\}` with no space, no line break
- **Brace placement** — Allman style, `{` always on its own line
- **If/Else alignment** — else branch (`:`) aligned with if branch
- **One-liners** — keep short constructs on one line

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Cleanup changes behavior | Formatting rule applied incorrectly | Review against `formatting.md`; revert and re-apply |
| Alignment off after edit | Mixed tabs/spaces or partial alignment | Ensure 4-space indent, re-align full block |

## Links

- memory/slang/best-practices.md — conventions reference
- memory/slang/formatting.md — formatting rules
