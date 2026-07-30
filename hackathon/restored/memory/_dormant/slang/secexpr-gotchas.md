---
created: 2026-04-09
updated: 2026-04-17
tags: [ref, slang, secexpr, gotchas, line-limit, parser, version-control, quoting, batch-file]
status: dormant
relates:
  - slang/lint-edit.md
  - slang/review.md
---

# secexpr Gotchas & Edge Cases

## secexpr CLI Reference (Quick)

```
secexpr [Database] [options] [-e Expression] [-s Security] ...
```

Key flags:
- `-e Expression` — evaluate expression from command line
- `-s Security` — evaluate a Slang security (script)
- `-t` — **trace all error messages** (stderr). NOT a mode — just enables verbose error output
- `--safe` — no writes to production dbs
- `--full` — full write access to production dbs
- `--source SourceDb` — set SourceDatabase
- `-w` — use windows (allow dialogs & windows); without it, Print() goes to stdout
- `-i` — interactive mode (prompt for input)
- `-x` — command processor mode
- `-r` — disable printing of final results
- `--quietstderr` — suppress "Evaluating..." message

When no `-e`, `-s`, `-i`, or `-x` is given, secexpr reads from **stdin**. Each line is evaluated as a separate expression. Top-level variable assignments persist across lines; variables scoped inside blocks (`Try`/`If`/`ForEach`) on one line do NOT persist to subsequent lines.

## Gotchas

- **secexpr stdin line limit:** When reading from stdin (`< file.slang`), secexpr has a ~4096-byte per-line buffer. Keep ALL lines in generated Slang expression files under 4096 characters. If a line (e.g. review.py's Try block) would exceed this, shorten the description or restructure as multiple top-level statements. Symptom: secexpr exits cleanly (rc=0) but simply drops all output after the truncated line. **This is a stdin buffer limit, not related to the `-t` flag.**

- **secexpr stdin: each line is a separate evaluation.** When reading from stdin, secexpr evaluates each line independently. Variables assigned at top-level on one line DO persist to subsequent lines. However, variables scoped inside `Try`/`If`/`ForEach` blocks on one line are NOT visible on other lines. This means you CANNOT split a `Try() { ... }` block across multiple lines and expect inner variables to persist. For complex expressions that exceed 4096 chars: restructure as sequential top-level statements, each on its own line under 4096 chars.

- **secexpr stderr noise:** When running secexpr with `--safe` against `!NYC_CoreData` (e.g., for ScriptReview), stderr produces massive volumes of 3001 "library not found" errors (tens of thousands of lines). This noise can overwhelm output capture and obscure actual markers in stdout. **Always redirect stderr** (`2>nul` in batch files, or `stderr=subprocess.DEVNULL` in Python) when running review expressions. Parse only stdout for markers.

- **ScriptReview parser limitations:** The ScriptReview diff parser (`@ScriptReview::Generate Diff Datum Structure`) does NOT support `Try() { } Catch() { }` syntax (gives "Can't convert Array to Slang Node" error). Use `Try() expr : default;` or `Try() { } : { };` instead. Always prefer the ternary `Try() expr : Error()` pattern when fixing `IsError(Structure) is always false` lint.

- **User DB copies — Version Control:** When creating a user DB copy of an existing CVSed script, ALWAYS use `edit.py --from-prod` so Version Control metadata is preserved. Never use `--create --content-file` for existing scripts — it creates a "naked" security without Version Control, causing ScriptReview to misclassify the script as "new" and fail with "Change is invalid". If a broken copy exists, delete it first (`--delete`), then `--from-prod --edit-file`.

- **Batch file approach for secexpr commands:** NEVER use `cmd /c "..."` with nested escaped quotes for secexpr invocations — nested quoting causes double-quoting of arguments (e.g., `--source` gets `'"~user!clean;PS"'` instead of `'~user!clean;PS'`). Instead, write the command to a temp `.cmd` file and run it with `subprocess.run(["cmd", "/c", batch_path])`. Use Python's `tempfile.mkstemp(suffix=".cmd")` for this. This applies to FasTest, lint, review, and any secexpr call from Python.

- **Replacing non-ASCII already in a script:** Extract the bad text at runtime using `StrPos` + slice, then replace: `Pos = StrPos(Txt, "asset name "); After = Pos + 11; Pos2 = StrPos(Txt, " should", After); Em = Txt[: After, Pos2 - 1 :]; Fixed = StrReplace(Txt, Em, "--", REPL_GLOBAL);`

- **Print() has no newlines:** `Print()` does NOT emit newline characters. Output from multiple `Print()` calls is concatenated. Use `Print( Sprintf( "...\n" ) )` to get line breaks in stdout.

- **Database vs source:** The DB positional arg (1st arg, e.g. `!NYC_Production`) controls security name resolution. `--source` controls where linked scripts load from. For real securities use a production DB — `NullDb` can't resolve real names, `PS` maps to `!NYC_EqVol_Source` (can't find general securities). NEVER put a non-Slang DB in `--source` (causes "SourceDb contains invalid non-slang db" error).

- **`;PS` in DB arg for ProdSource scripts:** `GetSecurity` resolves from the DB positional arg, NOT from `--source`. If the target script lives only in ProdSource (not in the user DB), append `;PS` to the DB arg: `secexpr "~user!clean;PS" ...`. For `edit.py`, use `--from-prod` for writes — this appends `;PS` to the DB arg so `GetSecurity` can find it. Read-only ops (`--read`, `--check-ascii`) automatically use the `;PS`-augmented source as the DB arg since the Apr 2026 fix. Without `;PS` in the DB arg, read-only operations silently return empty output (rc=0) for ProdSource-only scripts.

- **Always verify raw content before edit.py replace:** Before using `--old-file`/`--new-file` or `--edit-file` with `replace` action, ALWAYS read the raw script content first (via `--read`) and verify exact bytes match. Common traps: (1) assuming blank lines exist between comment blocks and function definitions when there are none, (2) assuming spaces when the content has tabs (or vice versa), (3) `\r\n` vs `\n` line endings. Use a Python script to `repr()` the exact lines around the target area.
