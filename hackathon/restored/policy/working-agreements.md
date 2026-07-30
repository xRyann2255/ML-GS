# Working Agreements

- Write a cleanup plan before modifying code for refactor/cleanup work.
- Lock existing behavior with regression tests before cleanup edits.
- Prefer deletion over addition.
- Reuse existing utils and patterns before introducing new abstractions.
- No new dependencies without explicit request.
- Keep diffs small, reviewable, and reversible.
- Run tests after changes. Run lint and typecheck only on explicit request or before a PR/commit — per Rule 6 in `.github/copilot-instructions.md`.
- Final reports: changed files, simplifications made, remaining risks.
- **Before writing any `memory/` file:** verify CoALA compliance (`{domain}/{subject}.md` naming, valid domain, complete frontmatter) — see `memory/meta/guide.md` Hard Gates.

## Test-first gate (TDD)

When modifying or creating Python code files, write or update tests BEFORE implementation:

| Scenario | Required test-first action |
|----------|---------------------------|
| **New feature / new module** | Write a failing test that defines expected behavior. Implement the minimum code to pass. Refactor while keeping tests green. |
| **Bug fix** | Write a test that reproduces the diagnosed symptom. Confirm it fails. Then implement the fix. |
| **Refactor / cleanup** | Run existing tests (baseline). Write characterization tests for uncovered behavior. Then restructure. (Already enforced by `refactor.md` LOCK phase.) |

Skip for non-code files (config, docs, memory, workflows, prompts).

## Slang-specific

See `memory/slang/*.md` files for Slang conventions (best practices, formatting, lint, headers).

When in a Slang context, mandatory pre-flight gate — never bypass:
- **Read `memory/slang/best-practices.md` and `memory/slang/formatting.md` before any `.s` file interaction.**

**Files with `:` in the name** (e.g. `SVE: _LIB SVE piresm.s`) cannot be edited via VFS — use the SLANG_EDIT skill secexpr path (Section B).

Full pre-flight gate list (user profile, Slang refs, RegTest, secexpr --safe, no hardcoded DBs): `policy/preflight-gates.md`.
