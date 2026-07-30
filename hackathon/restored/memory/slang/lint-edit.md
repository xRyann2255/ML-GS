---
created: 2026-03-26
updated: 2026-04-30
tags: [slang, lint, secexpr, edit, vscode]
status: active
relates:
  - slang/formatting.md
  - slang/best-practices.md
  - ref/devtools.md
---

# Slang Lint & Edit via secexpr

> **SAFETY:** ALWAYS `secexpr --safe`. No exceptions — all operations (reads, writes, deletes) use `--safe`.

## Lint Workflow

1. Run native lint via the `SLANG_LINT` skill (never the VS Code extension lint)
2. Confirm **0 Status-1** and **0 Status-2** issues (Status 3/3.75 are informational)
3. **Stale terminal issue:** If `run_task(id="lint-slang")` returns results from a PREVIOUS run (check the timestamp in the output), run `kill-orphans` first to clear stuck powershell/secexpr processes, then re-run. Read the JSON output file (from `output_json` in args) to verify you got fresh results.

## Editing Scripts with Colons

Windows can't handle `:` in filenames. The VFS (`slang:/`) path fails for colon-named scripts. Use `SLANG_EDIT` skill secexpr path (Section B) for ALL colon scripts:
- Simple: `--old "X" --new "Y"` or `--old-file`/`--new-file` for multi-line
- Batch: `--edit-file ops.json` (actions: replace, delete, delete-between, prepend, append, insert-before, insert-after)
- NEVER write bespoke Python for Slang edits

For scripts WITHOUT colons, use VFS directly (`read_file` / `replace_string_in_file` on `slang:/` path) — zero terminal commands needed.

### Edit Escalation Ladder

When editing colon-named scripts via `SLANG_EDIT`:

1. **Fragment edits** (`--edit-file` with targeted `replace` ops) — try first, fastest.
2. **If 2 consecutive fragment failures** (output JSON missing, terminal stuck on stale output) → run `kill-orphans` task to clear blocked processes, then retry once.
3. **If still failing** → fall back to `--rewrite --content-file` with the full desired script content. Read the current script via VFS first, apply changes locally, write to a `.s` temp file, then rewrite. This bypasses all fragment-matching issues.

The `--rewrite` path is heavier (overwrites the entire script) but is 100% reliable when fragment matching fails due to whitespace/tab differences between VFS rendering and SecDB storage.

### Slang String Functions

`StrPos(Txt, Sub)` → 0-based (`-1` if missing).

`SubStr(Txt, Start)` → from `Start` (0-based) to end.

`SubStr(Txt, Start, End)` → 0-based indices, **End inclusive** (this is NOT a length).

`StrReplace(Txt, Old, New, REPL_GLOBAL)`. `Size(Str)`. No `StrFind`.

### Key Rules

- **StrReplace**: always use `REPL_GLOBAL` for all occurrences (edit.py default)
- **Quoting**: Slang level (`"` → `""` via `esc()`) and batch level (`"` → `""` via `batch_escape()`) are separate steps
- **Backslashes**: script `\Ellipsis` → Slang literal needs `\\Ellipsis`. Use `--dry-run` for `\` lines
- **`!` in DB paths**: vulnerable to `cmd.exe` delayed expansion — use `setlocal DisableDelayedExpansion` wrapper
- **String concat**: use `+` operator (`"A" + Chr(10) + "B"`). Juxtaposition doesn't work
- **SecDB indentation**: stored as tabs (`\t`), VS Code VFS renders as spaces

## Common Lint Fixes

| Error | Fix |
|---|---|
| `Argument "X" apparently unused` | `LintPragma( "Ignore apparently unused X" );` inside body |
| `Ellipsis( X ) argument has no default` | `Ellipsis( X ) := Structure()` — default **outside** the parens |
| `Possible typo - unregistered vt X` | `X( arg )` → `arg.X()` |
| `Line too long` | Break across lines |
| `100% functions MUST be documented` | Add `/** ... */` doc comment |
| `Invalid pragma` | Check pragma format below |
| `IsError(X) is always false` | Remove dead `IsError()` guard — see § IsError Always False below |
| `Links "X" but uses no functions` | Remove the unnecessary `Link( "X" )` |
| `"X" does not include itself as Test Script` | Set `** Test Script : X` in header AND re-save once to sync VT metadata |

### LintPragma — lint-only, NOT runtime

`LintPragma()` is parsed by the lint AST analyzer but **causes hard compile errors at FasTest runtime**. Only use it in functions that are never executed (e.g. dead code pragmas at script level). For mock functions that run during tests, suppress unused args by:
- Using all args in a harmless guard: `If( !Arg ) Return( Null );`
- Matching the real function signature exactly
- Using `Ellipsis( _ )` to discard all args

### LintPragma Syntax

- Per-arg: `LintPragma( "Ignore apparently unused ArgName" );` — inside body, one per arg
- All args: `LintPragma( "Function with required signature" );` — covers all unused
- Defined-not-called: `LintPragma( "Ignore apparently unused FuncName" );` — script level
- INVALID: `"Ignore Unused Arguments of FuncName"`

### Valid Lint Pragmas (Complete Reference)

Some pragmas accept a name/identifier concatenated at the end (marked with `…`).

**Ignore — Unused / Undefined / Dead:**
- `Ignore apparently unused …` (variable, argument, or function name)
- `Ignore apparently undefined …`
- `Ignore apparently unchecked …`
- `Ignore apparently unchecked call to function …`
- `Ignore apparent dead group …` (specific group)
- `Ignore all apparent dead groups`
- `Ignore apparently not laid out`

**Ignore — Hardcoded / Literal / Constant:**
- `Ignore apparent hardcoded group …`
- `Ignore all apparent hardcoded groups`
- `Ignore apparent Database String literal`
- `Ignore apparent legal entity`
- `Ignore constant used for TypeName`

**Ignore — Type / Value / Assignment:**
- `Ignore Apparently Incorrect Value Type`
- `Ignore apparently invalid assignment …`
- `Ignore possible assignment in …`
- `Ignore InferredName`

**Ignore — Component / Class / Interface:**
- `Ignore component is not required in …`
- `Ignore component is optional in …`
- `Ignore undefined component`
- `Ignore undefined member function`
- `Ignore DefineAbstractClass`
- `Ignore DefineClass`
- `Ignore DefineClassNonStreamable`
- `Ignore DefineInterface`
- `Ignore Defined …`
- `Ignore duplicate definition of …`
- `Ignore JSI types in type definition`

**Ignore — VT / SecDB:**
- `Ignore implicit off-graph access of VT`
- `Ignore unchecked VTs in function argument`
- `Ignore VT Using VT in DSU`
- `Group VT not used to permission objects`
- `Ignore unconditional SetValue`
- `Ignore NonInteractive SetValue in …`
- `Ignore GetValue inside an UFO`
- `Ignore use of UFO Old`
- `Ignore physical database reference`
- `Ignore String Of Database`

**Ignore — Functions / Scope / Execution:**
- `Ignore Cyclomatic Complexity of …`
- `Cyclomatic Complexity limit`
- `Ignore use of function returning Null`
- `Ignore use of Global scope`
- `Ignore use of Slang script class`
- `Ignore use of MathNode functions`
- `Ignore use of Force flag in Transaction`
- `Ignore Scope …`
- `Ignore Exec`
- `Ignore Exit`
- `Ignore ErrorReturn`
- `Ignore Debug`
- `Ignore TransactionAbort`
- `Ignore TransactionCommit`
- `Ignore definition of nested diddlescopes`
- `Ignore DatabaseSearchPathAppend`

**Ignore — Testing / RegTest:**
- `Ignore no appropriate test for function …`
- `Ignore no appropriate test for script …`
- `Ignore Snap Dbs used in RegTests`
- `Ignore why not use @Regtest::Set Random Seed`

**Ignore — Date / Time:**
- `Ignore Time conversions`
- `Ignore Time Zone VT call on non-location`
- `Ignore TimeToDateNew`
- `Ignore timezone arg omission`
- `Ignore Today`

**Ignore — Market / Security / Misc:**
- `Ignore suspicious dependencies on Market Prefix`
- `Ignore incorrect entry to the Equities Market Model`
- `Ignore apparent bad RegEx assumptions for ID64`
- `Ignore ArrayConcat`
- `Ignore GobMushString greater than 7 chars`
- `Ignore w_RefOff`
- `Ignore w_RefOn`
- `Ignore subscript to component performance hint`
- `Ignore empty Lt Slang script`
- `Ignore apparently illegal TSecDb constructs`
- `Ignore explicit FIDM references`
- `Ignore explicit references to Prod Without Baseref`
- `Ignore KerberosAuthenticate functions`

**Non-Ignore Pragmas:**
- `Function with required signature` — suppresses all unused-arg warnings
- `Function Called Remotely` — function invoked externally (not dead code)
- `No function argument check for …`
- `No Side Effect Checking`
- `No sprintf check`
- `Implicit Function Call`
- `Implicitly Using Binder`
- `Implicitly Using Constant`
- `Implicitly Using Type`
- `Implicitly Using WI`
- `Implicitly Using Widget`
- `Variable Datatype …`
- `Variable Spec …`
- `Shares Private Scope with …`
- `SlangFunctionRegister`
- `Suppress RefCounted TS member default warning`
- `Check constant defines as mail addresses`
- `PLEX pool not aligned with BizUnit`
- `Pool Script Executing Code`
- `Required use of UIM::STM Point`
- `Debug`

### IsError Always False

Lint reports `IsError(X) is always false` when it proves the expression never produces an error object. The correct fix is to **remove the dead `IsError()` guard** — not to artificially make the error path reachable.

**Case 1 — function has no meaningful return value (void-like).** Remove the guard and call directly:

```slang
// BEFORE (lint S1):
Status = @MyLib::Save Status( Book, Record );
If( !IsError( Status ) )
    Print( "Updated." )
:
    Print( "Failed." );

// AFTER:
@MyLib::Save Status( Book, Record );
Print( "Updated." );
```

**Case 2 — function returns a checkable value (Double, Boolean).** Replace `IsError()` with a direct value check:

```slang
// BEFORE (lint S1):
Result = @MyLib::Compute Qty( Trade );
If( !IsError( Result ) ) { Use( Result ); };

// AFTER — check the actual return value:
Result = @MyLib::Compute Qty( Trade );
If( Result > 0 ) { Use( Result ); };
```

Do NOT "fix" this by wrapping in `Try() expr : Error()` or `Check()` — both are workarounds that hide the real issue (the guard was always dead code). `Check()` is reserved for `UpdateSecurity`, `RenameSecurity`, `DeleteSecurity`. Adding `Check()` to a non-error-returning function can cause spurious regtest failures.

## VFS Multi-Function Deletion

When removing multiple functions from a Slang script via VFS, **delete one function per `replace_string_in_file` call** (sequential). Do NOT batch into a single large `oldString` — A/B testing showed sequential is ~4× faster, 100% reliable, and recoverable. Anchor each replacement on the preceding function's close + target body + next function's header. See `SLANG_EDIT` SKILL.md § A2b for the full pattern.

## MANDATORY Post-Edit Audit

After ANY edit to a Slang script, MUST re-read the script and verify ALL formatting rules (`slang/formatting.md`) and best practices (`slang/best-practices.md`) BEFORE declaring done. This includes: alignment of `=`/`:=`/`&=`, blank lines around block statements, no double blank lines, Allman brace style, multi-line formatting, `Ellipsis( _ )` for mocks, constant stubs assigned directly, FasTest-wrap-with for shared stubs, no empty lifecycle functions, blank line after LintPragma, etc. This is separate from lint — formatting issues that lint doesn't catch are still mandatory to fix.

## Cascading Lint Fixes

1. LintPragma added → forgot blank line after it
2. Alignment fix → broke neighbor alignment
3. Deleted code → orphan blank lines
4. Always re-lint after every fix round

If under review: refresh diffs via `_dormant/slang/review.md` (metadata-only doesn't update diffs).

## edit.py Pitfalls

- **`--from-prod` is now automatic**: edit.py auto-includes `;PS` in the `--source` resolution chain for all operations. The `--from-prod` flag still works (adds `;PS` to the *write* db too) but is no longer required for GetSecurity to find ProdSource scripts. Additionally, edit.py now detects `ERROR: Slang Error encountered` in secexpr stderr and fails with exit code 1 instead of silently succeeding.
- **Large script handling (`build_content_stmts`)**: edit.py builds script content line-by-line (`T = T + "lineN" + Chr(10);`) to avoid Slang's expression depth limit. The old chunk-based approach (concatenating 800-char chunks) failed for scripts >4k chars due to `+`-operator nesting depth. No size limit now.
- **`Check()` wrappers**: `SetValue` and `UpdateSecurity` are wrapped in `Check(...)` to propagate errors. Without `Check()`, these calls can silently fail while `Print("saved=1")` still executes — producing false success.
- **stderr noise suppression**: secexpr emits `ERROR: Slang Error encountered` in stderr even on successful saves (internal evaluation noise). edit.py checks `save_ok = "saved=1" in stdout` and suppresses stderr when true. Only surfaces stderr when the operation actually failed.
- **`--script` (singular)** for edit.py. `--scripts` (plural) is lint.py. Using the wrong flag gives exit code 2.
- **`insert-before` / `insert-after` are still fragile**: Always verify the exact marker text exists in `--read` output first. If you are editing around banner comments or making structural changes, prefer `--rewrite`.
- **`--rewrite` for complex changes**: When making multiple structural edits (move code, delete functions, add code), use `--rewrite --content-file` instead of chaining fragile `insert-before`/`insert-after` operations.
- **Backslash in JSON**: `\Ellipsis` in JSON `--edit-file` stores literal `\Ellipsis` (double backslash). For Slang `\Ellipsis` in source, use single `\` in JSON (tool handles Slang escaping via `Chr()`).
- **`--delete` output**: Prints progress: `Deleting script '...' ...`, `Verifying deletion ...`, `OK: script '...' deleted successfully.` Uses `--safe` mode. After deletion, edit.py re-reads the script with `--safe` to confirm it's gone. If the script still exists, prints `WARNING` and returns exit code 1.
- **`DeleteSecurity` API**: Takes a **String** (security name like `"_TMP Foo"`), NOT a Security handle. Passing `GetSecurity()` result causes `Expected String, found Security, for SecName`. Correct: `Check( DeleteSecurity( "name" ) )`. Wrap in a block `{ ... };` when piping via stdin to prevent subsequent statements from running on failure.
- **`--read` capture artifacts**: `edit.py --read` prints plain text to stdout, but some capture methods can introduce artifacts (UTF-8 BOM, CRCRLF, extra blank lines). For the most literal capture, prefer cmd redirection (`> out.txt`) rather than PowerShell `Out-File`.
- **Reverting changes — header is IMMUTABLE**: When reverting local Slang changes (deleting overlay or rewriting to restore production code), NEVER modify the top header comment block (`/** ... $Log:$ ... **/`). The header contains CVS version metadata managed by the system. Only revert the code body below the header.

### Leading Blank Line at File Start

If SecDB shows a leading blank line at the very top of an Expression, it can be **real stored content** (the Expression starts with `Chr(10)`). Historically, `Print(Txt)` can mask that leading newline in some captures.

Fix: use `SLANG_EDIT` with `--trim-leading-blank-lines` (rewrites only if there is a real leading blank/whitespace-only line).

## edit.py Overlay Types (CRITICAL)

| Command | Creates | CVS metadata? | Use for |
|---|---|---|---|
| `--create --content-file` | New security (SecDbNew + Rename) | NO | Brand new scripts only |
| `--rewrite --from-prod --content-file` | Overlay on production (GetSecurity + SetValue) | YES (preserves rev) | Modifying existing CVSed scripts |
| `--rewrite --content-file` (no `--from-prod`) | Overlay on user DB copy | YES if copy exists | Updating user DB overlays |
| `--delete` | Removes local overlay | N/A | Cleaning up user DB |
| `--delete --from-prod` | NOT SUPPORTED | — | Don't use — causes error |

**Decision rule:** Does the script already exist in production? → `--rewrite` (no `--from-prod` needed — source chain auto-includes `;PS`). Use `--from-prod` only when you want the *write* db to also include `;PS`. Is it brand new? → `--create`.

**`--rewrite` stdout**: Produces NO stdout output (silently applies). Verify success via `--read --from-prod` afterward. A failed `--rewrite` will have non-empty stderr.

**NEVER use `--create` for existing CVSed scripts** — it creates a "naked" security without Version Control metadata. ScriptReview will fail with "Script is not under CVS" when trying to generate diffs. If you accidentally created one, `--delete` it first, then `--rewrite --from-prod`.
