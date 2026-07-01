---
name: SLANG_REGTEST_FIX
description: End-to-end workflow for diagnosing and fixing failing Slang RegTests
---

# SLANG_REGTEST_FIX — Diagnose, Fix, and Submit

> **Purpose:** End-to-end workflow for diagnosing failing RegTests, fixing issues, applying best practices and formatting, linting, re-running tests, and submitting code review.

**Out of scope:** Writing new tests from scratch, fixing non-RegTest scripts, or deploying changes.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_REGTEST_FIX` |
| **Scope** | Fix failing RegTests end-to-end (diagnose → fix → lint → retest → review) |
| **Inputs** | Failing test script name(s), DB path |
| **Outputs** | Fixed scripts, passing tests, submitted code review |
| **Authority** | Write (orchestrates SLANG_EDIT, SLANG_LINT, SLANG_REVIEW, SLANG_CLEANUP) |

## When to Use

- RegTest is failing and needs diagnosis and fix.
- After modifying a `_LIB` that has dependent tests.
- When a full fix-lint-test-review cycle is needed.

---

Iterative workflow: fix failing RegTest → best practices → formatting → lint → re-run → code review.

## Prerequisites

Skills required: `SLANG_EDIT` (read/write scripts), `SLANG_LINT` (native lint), `SLANG_REVIEW` (code review), `SLANG_CLEANUP` (best practices + formatting).

> **Memory:** `memory/slang/best-practices.md` (stubs, mocks, LintPragma), `memory/slang/formatting.md` (alignment, brace style).

## Procedure

### Step 1 — Run RegTest

```powershell
cmd /c "H:\all-languages-env.cmd >nul 2>&1 && secexpr NullDb --source ""~<user>!clean;PS"" --safe -s ""<Test Script>"" > workspace\tmp\regtest_output.txt 2>&1"
```

| Pattern | Meaning |
| --- | --- |
| `ASSERTION FAILED` | Test assertion failed |
| `ASSERTION PASSED` | Test assertion passed |
| `Suite took` | FasTest completed (may still have failures) |
| `Slang Error` / `failed @` | Runtime error |
| `SubDbDrvGetByName` | Missing security / DB lookup |

### Step 2 — Read Source

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

```powershell
PYTHON skills/SLANG_EDIT/src/edit.py ^
    --db "~<user>!clean" --script "<name>" --read
```

Read both test (`Test:` / `_UT`) and library under test (`_LIB`).

### Step 3 — Fix Failures

| Problem | Fix |
| --- | --- |
| Non-deterministic DB lookup | Stub with `RegTestStubFunction` |
| Live data dependency | Provide mock TDS/Structure via stub |
| Missing stub for external API | Add to `Stubs` or create `Private::Mock` |
| Wrong expected value | Update assertion to match correct behavior |
| Runtime error in `_LIB` | Fix the library, not the test |
| Test slow (heavy computation) | Stub expensive sub-functions (charting, formatting, nested loops) whose output isn't asserted |

**Key rules:** Never load live data. Never update expected data to match live data. Fix `_LIB` if `_LIB` is wrong. Constant stubs = direct constants (no lambda wrapper). Track all changed scripts.

**Stored format — preserve blank-line separators:** When using `--rewrite` or `--content-file`, ALWAYS preserve the original multi-blank separators (3-5 blank lines between sections). Read the original stored source FIRST and note where multi-blank separators exist. NEVER uniformize all blank spacing to 1-blank — this creates noisy code review diffs. After rewrite, compare old vs new stored content and verify only actual code changes appear in the diff.

**FasTest lifecycle:** `Setup Suite` (once) → `Setup` (each) → `Test` → `Teardown` (each) → `Teardown Suite` (once). Params resolved **before** Setup Suite. Tests run in **alphanumeric order**. If Setup throws, Test + Teardown are skipped.

### Steps 4-5 — Best Practices & Formatting

Use `SLANG_CLEANUP` skill. See SLANG_CLEANUP/SKILL.md.

### Step 6 — Lint

Use `SLANG_LINT` skill. Gate: fix all Status-1/Status-2. Status-3+ informational.

Exceptions to ignore: `Tests with 'Unknown' script` (Status 1, inherent to inline lint).

### Step 7 — Re-run RegTest

Same as Step 1. All `ASSERTION PASSED` + `Suite took` + no `ASSERTION FAILED` → proceed. Otherwise loop to Step 3.

### Step 8 — Code Review

```powershell
PYTHON skills/SLANG_REVIEW/src/review.py ^
    --db "~<user>!clean" --scripts "<all changed scripts>" ^
    --subject "<subject>" --description "<what>" ^
    --driver-for-change "<why>" ^
    --testing-description "RegTest <name> passes. Lint clean." ^
    > workspace/tmp/review_output.txt 2>&1
```

Include **every** changed script — both `_LIB` and test files.

## Task-Based Execution (Zero Allow — Preferred)

Use `run_task("slang-regtest")` instead of `run_in_terminal` to avoid the Copilot "Allow" prompt. **The entire workflow uses zero terminal calls.**

### Workflow

1. **Write args file** with a unique `run_id` (use `create_file` — no terminal):

```json
{
  "db": "~{kerberos}!{sub_db}",
  "test": "Test: Eq1D Brazil Foo",
  "libs": ["_LIB Eq1D Brazil Foo"],
  "run_only": true,
  "run_id": "<unique-id>"
}
```

For a full run+lint+review workflow:
```json
{
  "db": "~{kerberos}!{sub_db}",
  "test": "Test: Eq1D Brazil Foo",
  "libs": ["_LIB Eq1D Brazil Foo"],
  "review": true,
  "subject": "Fix RegTest Foo",
  "description": "Fixed stub for Get Data",
  "testing_description": "RegTest passes. Lint clean.",
  "run_id": "<unique-id>"
}
```

Generate `run_id` as a short UUID or timestamp string. This lets you distinguish fresh results from stale ones without touching the terminal.

2. **Launch via predefined VS Code Task** (no Allow):

```
run_task("slang-regtest", workspaceFolder: "h:\ml-vol-estimator")
```

The task reads `workspace/tmp/regtest_args.json` automatically.
```

3. **Poll with `read_file`** on `workspace/tmp/slang_regtest_fix_results.json` (no terminal):
   - On launch, fix_regtest.py writes `{"status": "running", "run_id": "..."}`.
   - On completion, overwrites with `{"status": "done", "run_id": "...", "gate": "...", ...}`.
   - Poll: call `read_file` every ~30-60s. When `status == "done"` and `run_id` matches, results are fresh.

```json
{
  "status": "done",
  "run_id": "<unique-id>",
  "test": "Test: Eq1D Brazil Foo",
  "libs": ["_LIB Eq1D Brazil Foo"],
  "gate": "PASS",
  "mode": "run_only",
  "test_result": {
    "passed_count": 5,
    "failed_count": 0,
    "error_count": 0,
    "suite_completed": true,
    "success": true
  }
}
```

4. **Evaluate gate**: `gate == "PASS"` → done. `gate == "FAIL"` → check `step` (test/lint/review) and fix.

Failure example: `{"status": "done", "run_id": "...", "gate": "FAIL", "mode": "full", "step": "lint", "lint": {"errors": [...], "clean": false}}`

### CRITICAL: No `run_in_terminal` anywhere

| Step | Tool | Allow? |
|---|---|---|
| Write args JSON | `create_file` | No |
| Launch task | `run_task` | No |
| Poll results | `read_file` | No |
| Read results | `read_file` | No |

Do NOT use `run_in_terminal` to delete old results, poll, or check — all of those trigger Allow prompts.

### Args File Keys

| Key | Type | Description |
|---|---|---|
| `db` | string | SecDB database path (e.g. `~vicenf!commit`) |
| `test` | string | RegTest script name (e.g. `Test: Eq1D Brazil Foo`) |
| `libs` | string[] | Library scripts the test depends on (optional) |
| `run_only` | bool | Only run test, skip lint/review (optional) |
| `lint_only` | bool | Only run lint on the test (optional) |
| `read_source` | bool | Read and return source, then exit (optional) |
| `review` | bool | Submit code review after success (optional) |
| `subject` | string | Code review subject (optional) |
| `description` | string | Code review description (optional) |
| `testing_description` | string | Code review testing notes (optional) |
| `out_dir` | string | Output directory override (optional) |
| `output_json` | string | Custom output path (optional) |
| `run_id` | string | Unique ID to match results freshness |

### Notes

- **`regtest_fix_task.cmd`** auto-detects Python from `H:\venv*` (highest version first).
- **Default output**: `workspace/tmp/slang_regtest_fix_results.json`
- File starts with `{"status": "running", "run_id": "..."}`, then gets overwritten with `{"status": "done", ...}` on completion.
- Always generate a unique `run_id` per operation and match it when polling to avoid stale results.
- **RegTests can take 1-10 min** depending on library loading.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `cannot use this function outside regression tests` | Expected when linting inline — ignore |
| `SubDbDrvGetByName: Object not found` | Stub the `GetSecurity` call |
| `Access of an uninitialized variable` | Move declaration above first use |
| `RegTestStubFunction does not bind a block` | Add `Link("_Slang RegTest Stub Function")` |
| `Cannot pass positional argument 'X' by name` | Pass positionally |
| `member not part of scope` | Add `Link("_TYPE ...")` |
| secexpr hangs | Library loading — wait up to 10 min |
| Test passes but takes minutes | Heavy computation not stubbed — trace call graph, identify unstubbed callees (charting, formatting, S3 writes), stub with minimal return values |
| Stub silently doesn't fire (real function runs) | Stub key format wrong. Must be `"<script>::<namespace>::<fn>"`. Only `@`-called user functions are stubbable — native/builtin functions (`Size`, `GetValue`, `UpdateSecurity`) and VT nodes CANNOT be stubbed. To mock a native: wrap it in a `Private::` function in the _LIB, call via `@`, stub the wrapper |
| Not all public functions tested | Every public function in the _LIB must have at least one `Private::Test` covering it. Audit the function list (`Functions()` or read source) vs test names. Missing coverage → add test functions |
| `FasTest-wrap-with` annotation ignored (tests run without stubs) | Annotation must be the **last line** in the doc comment before `****/`, preceded by a blank `**` line. If description text follows the annotation, FasTest concatenates it into the wrapper name → silent mismatch. Move annotation to end of comment block |
| Stubs work for some tests but not others | Each test function needs its own `FasTest-wrap-with:` in its doc comment. The annotation is per-function, not per-script. Missing annotation → that test runs unwrapped |
| `FasTest-params` not discovered | Param variable must be at script-level (not inside Setup Suite). Params resolve before lifecycle |

## Output

Files in `workspace/tmp/`: `regtest_output.txt`, `lint_output.txt`, `review_output.txt`

## Links

- memory/slang/best-practices.md — stubs, mocks, LintPragma
- memory/slang/formatting.md — alignment, brace style
