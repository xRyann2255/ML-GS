# Slang Code Examples -- Reference Libraries

When you need to see **real-world, production-quality Slang code**, consult the libraries
listed below. These are well-structured, well-documented scripts that demonstrate
idiomatic Slang patterns at scale.

> **When to use this guide:**
> You are writing a non-trivial Slang script (library, typed structure, test, etc.)
> and want to see how experienced developers structure larger codebases.
> Open the referenced scripts, read them, and follow the same conventions.

---

## Recommended Libraries

### `_LIB Trade Control`

A comprehensive trade-control library. Good reference for:

- Clean function organisation across a large library
- Proper use of typed structures as function parameters and return values
- Error handling patterns
- Well-written SLAM documentation blocks

---

## General Conventions Observed in Good Libraries

| Convention | Detail |
|---|---|
| **Naming** | Libraries start with `_LIB`, types with `_TYPE`, constants with `_Const`, tests with `Test:` |
| **SLAM docs** | Every public function has a SLAM documentation block |
| **Error handling** | Functions return clear error indicators; callers check them |
| **Small functions** | Each function does one thing well |
| **No magic values** | Constants are defined in `_Const` scripts or at the top of the file |
