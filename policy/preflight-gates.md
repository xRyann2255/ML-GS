# Mandatory Pre-Flight Gates

> These fire before any other logic. Never skip, never defer.

1. **Load user profile FIRST.** Read person/user.md before doing anything else. Never assume you know what's in it.

2. **Slang reference at session start.** Read workspace/docs/slang/copilot-instructions.md for the Slang language reference.

3. **Before any `.s` file work**, read and follow these memory files — never guess Slang conventions:
   - slang/best-practices.md — stubs, mocks, lambdas, LintPragma
   - slang/formatting.md — alignment, braces, multi-line rules
   - slang/lint-edit.md — lint fixes, secexpr edit patterns

4. **RegTest scripts (`Test:` prefix):** After any change, re-run FasTest and confirm **all tests pass with 0 errors**. Never declare a RegTest change "done" with failing tests.

5. **secexpr safe mode:** ALWAYS run `secexpr` with `--safe`. No exceptions — all operations including writes and deletes work in safe mode.

6. **Never hardcode kerberos, UserDB paths, or Object DB names.** All DB identifiers and user-specific paths must be resolved at runtime — user argument first, `person/user.md` fallback. Use `<ObjectDB>`, `<Slang DB>`, `<kerberos>` placeholders in examples and docs.
