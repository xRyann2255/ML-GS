---
created: 2026-04-13
updated: 2026-04-14
tags: [ai, slop, cleanup, smells, code-quality, refactoring]
status: dormant
relates:
  - slang/best-practices.md
  - slang/formatting.md
---

# AI Slop Smells — Identification & Fix Reference

Catalog of AI-generated code smells used by the `AI_SLOP_CLEANER` skill. Each smell has an ID, detection heuristic, fix strategy, confidence level, and known false-positive exceptions.

## Confidence Hierarchy

Smells are ranked by fix confidence — how safe it is to auto-fix without user review:

| Confidence | Meaning | Action |
|------------|---------|--------|
| **high** | Deterministic, always safe to remove | Auto-fix |
| **medium** | Usually safe but context-dependent | Auto-fix with regression test gate |
| **low** | Requires human judgment | Flag only, wait for approval |

---

## Smell ID Table

### Imports & Dependencies

| ID | Name | Detection | Fix | Confidence | Risk |
|----|------|-----------|-----|------------|------|
| `DEAD-IMPORT` | Unused import | Import symbol not referenced anywhere in file | Delete the import line | high | low |
| `SHADOW-IMPORT` | Redundant re-import | Same symbol imported twice, second shadows first | Delete the duplicate | high | low |
| `WILDCARD-IMPORT` | Star import | `from X import *` | Replace with explicit imports for used symbols | medium | medium |
| `UNUSED-DEP` | Unused dependency | Package in requirements but no import found | Remove from requirements (verify with grep across all files) | low | medium |

### Dead Code

| ID | Name | Detection | Fix | Confidence | Risk |
|----|------|-----------|-----|------------|------|
| `DEAD-VAR` | Unused variable | Assigned but never read | Delete assignment (watch for side-effects in RHS) | medium | low |
| `DEAD-FN` | Unused function | Defined but never called (within scope) | Delete function | low | medium |
| `DEAD-PARAM` | Unused parameter | Parameter never referenced in function body | Remove param if private; flag if public API | low | medium |
| `DEAD-BRANCH` | Unreachable branch | `if False`, `if 0`, code after unconditional `return` | Delete the branch | high | low |
| `DEAD-COMMENT` | Commented-out code | Heuristic: multi-line `#` blocks with code syntax | Delete | medium | low |

### Structural Smells

| ID | Name | Detection | Fix | Confidence | Risk |
|----|------|-----------|-----|------------|------|
| `WRAPPER-CLASS` | Unnecessary wrapper class | Class with single method, no state, no inheritance | Extract to standalone function | medium | medium |
| `GOD-FN` | Oversized function | Function >50 lines (configurable) | Split into helpers — but only when clear seams exist | low | high |
| `DEEP-NEST` | Deep nesting | >3 levels of indentation | Invert conditions / extract early returns | medium | medium |
| `COPY-PASTE` | Duplicated logic | Near-identical code blocks (>5 lines, >80% similarity) | Extract shared helper | low | high |
| `YAGNI-ABSTRACT` | Premature abstraction | Abstract class / interface with exactly 1 implementor | Inline the concrete implementation | medium | medium |
| `OVER-CONFIG` | Over-configuration | Multiple config params with only 1 ever used | Remove unused params, inline the one used value | medium | low |

### Error Handling

| ID | Name | Detection | Fix | Confidence | Risk |
|----|------|-----------|-----|------------|------|
| `CARGO-EXCEPT` | Bare exception catch | `except Exception: pass` or `except: pass` | Narrow to specific exception; add logging | low | high |
| `SWALLOW-ERR` | Swallowed error | Catch block with only `pass` or trivial log | Add proper error propagation or re-raise | low | high |
| `REDUNDANT-TRY` | Unnecessary try/except | Try block that catches and re-raises without modification | Remove the try/except wrapper | medium | low |

### Naming & Style

| ID | Name | Detection | Fix | Confidence | Risk |
|----|------|-----------|-----|------------|------|
| `VAGUE-NAME` | Vague variable name | `data`, `result`, `temp`, `x`, `val` in non-trivial scope | Rename to descriptive name | low | low |
| `BOOL-TRAP` | Boolean parameter trap | Function with >1 positional bool param | Convert to keyword-only or use enum | low | medium |
| `MAGIC-NUM` | Magic number | Literal number in logic (not 0, 1, -1) without name | Extract to named constant | medium | low |

### AI-Specific Smells

| ID | Name | Detection | Fix | Confidence | Risk |
|----|------|-----------|-----|------------|------|
| `FILLER-COMMENT` | Fluff comment | Comment that restates the code: `# increment counter` above `counter += 1` | Delete the comment | high | low |
| `DOCSTRING-NOVEL` | Excessive docstring | Docstring >5 lines on a function <10 lines | Trim to 1-2 line summary | medium | low |
| `SCAFFOLD-CODE` | Leftover scaffold | Empty `__init__`, `pass`-only methods, placeholder `TODO` without substance | Delete or implement | medium | low |
| `OVER-DEFENSIVE` | Over-defensive checks | `if x is not None` when `x` can never be None by type | Remove the check | medium | medium |
| `CEREMONIAL-LOG` | Ceremonial logging | `logger.info("Entering function X")` / `logger.info("Done")` with no diagnostic value | Delete | medium | low |

---

## Fix Order

When multiple smells exist in a file, fix in this order:

1. **Dead imports / dead code** (high confidence, low risk — clears noise)
2. **Filler comments / ceremonial code** (high confidence — improves readability)
3. **Naming / style** (low risk — cosmetic)
4. **Structural** (medium risk — may require new tests)
5. **Error handling** (high risk — behavior change possible)

---

## False-Positive Exceptions

These patterns look like smells but are intentional:

| Pattern | Why it's not a smell |
|---------|---------------------|
| `import X` used only in type annotation | Real usage — `TYPE_CHECKING` guard is acceptable |
| `except Exception` in top-level CLI handler | Intentional — catch-all for user-facing error reporting |
| Unused parameter in callback/hook signature | Required by framework contract (e.g., `on_event(sender, event)`) |
| `pass` in abstract method body | Required placeholder for abstract interface |
| Large function in test setup/teardown | Test fixtures are inherently procedural — don't split |
| `# type: ignore` or `# noqa` | Intentional suppression — verify the reason, don't auto-remove |

---

## Learned Patterns

Patterns discovered during cleanup sessions — update as new knowledge emerges:

- **Slang scripts:** Apply `SLANG_CLEANUP` skill instead, not AI_SLOP_CLEANER. Slang has its own formatting and best-practice rules that don't map to general smells.
- **Test files:** Be conservative — dead-looking code in tests may be intentional fixtures or regression anchors. Always verify before removing.
- **Generated API clients:** Skip entirely. Auto-generated code has intentional patterns that look like smells (wrapper classes, over-defensive checks, verbose docstrings).
