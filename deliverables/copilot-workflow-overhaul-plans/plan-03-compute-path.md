# Plan 03 — Compute Path Works on Both Surfaces

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §8.
> Dispatch each task as a subagent with the context packet provided. Max 5 concurrent subagents.
> TDD is a hard gate (`.github/copilot-instructions.md` Rule 5) for every `src/` Python change in this
> plan; batch/bash/doc edits are Rule-5-exempt but carry runnable acceptance commands instead.
> Requires Plans 01 and 02 merged (Gate A confirmed; Gate B/C decisions recorded — this plan needs
> neither decision's YES branch, only that the surface contract S-A/S-B/S-C is landed in AGENTS.md).

**Goal:** Every compute entry point (`./vol`, the task layer, the 6 ML-skill wrappers) either works or fails loudly with a named fallback on both supported surfaces — S-A gets a real dev loop (`vol.cmd` + tracked `.vscode/tasks.json`), S-B keeps `./vol` untouched except an OS guard and the missing `forecast` arm, and the args-file contract becomes one spec everywhere.

**Architecture:** Four existing seams are extended, none replaced: (1) `./vol`'s 33-arm bash `case` dispatcher gains an OS guard and a `forecast)` arm (the subcommand is already registered in `src/volforecast/__main__.py` — recon `extension-surface.md` §5 checklist, steps 3–5 only); (2) `src/volforecast/utils/paths.py::resolve_project_root()` already lists `vol.cmd` as a repo-root marker (`paths.py:26-45` — "Returns the first ancestor directory containing AGENTS.md or vol.cmd"), so the new Windows shim fills a designed-for seam; (3) the 6 broken ML-skill wrappers collapse onto the existing `skills/_shared/_run.{sh,cmd}` bootstrap that ~40 other skills already use correctly; (4) the sentinel protocol (`workspace/tmp/exec/<ts>_<pid>.out` with `OUTPUT_FILE=` / `EXIT_CODE=` lines, `vol:327-411`) is reproduced byte-compatibly by `vol.cmd` so agent instructions stay identical across surfaces. The `setsid`/`exec`/`bg` machinery in `./vol` is untouched (00-overview §3 item 3).

**Tech stack:** No new dependencies. `vol.cmd` uses only cmd.exe built-ins + PowerShell one-liners (both present on S-A). New Python (`economic_value` CLI, `vf_entry.py`, `cleanup.py` `--out-file`) is stdlib + the already-locked numpy/pandas. All tests run under the existing pytest suite via `./vol test`.

**Research grounding:** This plan implements the audit findings AW-04, AW-05, AW-09, AW-13, AW-36, AW-41, AW-46, AW-54, AW-G6, AW-G7, AW-G8, AW-G10, AW-G16, AW-55 (verified live 2026-07-07, recon `findings-freshness.md`) plus the compute-path half of AW-G9. Expected outcome per 00-overview §4: the two BLOCKER compute findings (AW-04, AW-05) die here; the skill→pipeline bridge goes from 4-of-5 wrappers calling nonexistent modules to 5-of-5 calling modules that exist and import; `vol` coverage in `memory/ref/vol-cli.md` goes 19/33 → 34/34. **Calibration warning:** Gate D's S-A criteria assume pytest/ruff/mypy are importable from an `H:\venv*` or `src\.venv` on the GS Windows box. If they are not (decision-record risk 2), every S-A criterion falls back to S-B-only verification and is tagged per-criterion in the MR (see §9) — do not silently claim S-A green.

---

## 1. Global constraints

All of 00-overview §5 (shared conventions) applies to every task. Plan-specific hard rules:

1. **Never touch the `exec`/`bg`/`jobs` machinery in `./vol` (`vol:327-411`)** — the setsid/sentinel protocol is do-not-rebuild inventory item 3. Task 1 edits only the guard region (before `vol:20`), the uv hint (`vol:21`), one new `case` arm, and one help-heredoc line.
2. **Keep the H: probes in `skills/_shared/_run.cmd` verbatim** (`call H:\all-languages-env.cmd`, the `H:\venv315..38` scan loop) — AW-G11 do-NOT + `lint_vscode_tasks.py` rules W1/W6 mandate them. Task 5 only *appends* fallbacks and *guards* the env call with `if exist`.
3. **Do NOT delete `src/volforecast/cli/build_features.py`** — `src/tests/unit/test_features.py:20` imports `build_layer` from it (AW-G8 do-NOT). Only `cli/notebook.py` and `cli/research.py` (zero references outside themselves, verified 2026-07-07) are deleted.
4. **The 5 ACTIVE research plans in `workspace/plans/` are read-only.** Never touch `workspace/research/trials.yaml` or anything in `workspace/configs/`.
5. **Self-modification hazard:** Plan 02 rewrote the always-on rule scoping. Each packet below quotes the rule text it relies on as-of-execution; if the live file differs, STOP and return `blocked` with the diff.
6. **Drift check:** verify every cited `path:line` against the live tree before editing; if it moved, locate by content and note the delta in your return. (Mirror verified byte-identical 2026-07-07; the GS repo may have drifted.)
7. **T9 semantics are preserved:** `_run.{sh,cmd}` still exit 0 unconditionally at the end (VS Code `close:true` disposal). AW-41 is fixed by writing failure diagnostics *into the sentinel file*, never by changing the final exit code.
8. **`ml-vol-estimator.code-workspace` and `.vscode/tasks.json` have exactly one writer in this plan: Task 8.** No other task edits either file.
9. **Rule 2 as-of-execution** (`.github/copilot-instructions.md`, post-Plan-02 scoping): "`./vol` for all Python/CLI on S-B; on S-A use `vol.cmd`/`run_task` equivalents once Plan 03 lands (until then, S-A tasks are doc/config-only or routed to S-B)." This plan IS the landing — subagents executing on S-A before Task 2 merges must route Python verification through S-B.

---

## 2. File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `vol` | OS guard (exit 2 on non-Linux), softened uv hint, `forecast)` case arm, help-heredoc line |
| Create | `vol.cmd` | Windows dev-loop shim: test/test-all/testlf/lint/fmt/typecheck/exec/bg/jobs/help; same sentinel protocol; 4-step interpreter resolution; all other arms exit 2 naming S-B |
| Modify | `src/volforecast/evaluation/economic_value.py` | Append args-file CLI (`main(argv) -> int`, `__main__` block) — the BACKTEST entry point |
| Create | `src/tests/unit/test_economic_value_cli.py` | TDD for the above (red first) |
| Delete | `src/volforecast/cli/notebook.py`, `src/volforecast/cli/research.py` | Dead stubs — every function raises `NotImplementedError`, zero inbound references |
| Create | `skills/_shared/vf_entry.py` | Generic args-file adapter routing skill tasks to real volforecast entry points |
| Create | `src/tests/unit/test_vf_entry.py` | TDD for the adapter (red first) |
| Modify | `skills/{MODEL_TRAIN,FEATURE_BUILD,EVALUATE,DATA_INGEST,BACKTEST}/src/*_task.{sh,cmd}` | Collapse to 3–4-line `_shared/_run.{sh,cmd}` bootstrap callers pointing at modules that exist |
| Delete | `skills/{NOTEBOOK,RESEARCH}/src/*_task.{sh,cmd}` | Task paths removed; skills become agent-driven-only |
| Modify | `skills/{MODEL_TRAIN,FEATURE_BUILD,EVALUATE,DATA_INGEST,BACKTEST,NOTEBOOK,RESEARCH}/SKILL.md` | New args schema, drop `workspaceFolder: "h:\..."`, agent-driven-only marks, last-writer-wins caveat |
| Modify | `skills/_shared/_run.cmd`, `skills/_shared/_run.sh` | `if exist` guard on `H:\all-languages-env.cmd`, repo-local interpreter fallback chain, AW-41 failure sentinel |
| Modify | `skills/PYTHON_PATH/src/resolve.ps1` | `Get-Command python` fallback (mirrors `resolve.py`) |
| Modify | `skills/GIT/src/git_task.cmd` | `%~dp0noop_editor.cmd` instead of `H:/ml-vol-estimator/...` literal |
| Modify | `skills/SEARCH/SKILL.md` | Replace `H:\venv311\Scripts\python.exe` example with the resolution-order pointer |
| Modify | `skills/{GIT,GIT_COMMIT,SLANG_LINT,SLANG_TEST_COVERAGE}/SKILL.md` | Fixed args-file contract, `run_id` inside body `[a-z0-9-]+`, create_and_run_task retired |
| Modify | `.github/prompts/slang-review.prompt.md`, `.github/prompts/lint-workspace.prompt.md` | Args filenames matched to task definitions; poll-target fix |
| Modify | `memory/ref/vscode-tasks.md` | Rule E3 replaced (create_and_run_task retired), fixed-path contract + `.fail` sentinel documented |
| Modify | `skills/KILL_ORPHANS/SKILL.md`, `skills/KILL_ORPHANS/src/cleanup.py` | Single engine; `--out-file` sentinel; wmic→CIM fallback; dedupe 3× Troubleshooting |
| Delete | `skills/KILL_ORPHANS/src/cleanup.ps1` | Second divergent killer engine removed |
| Create | `src/tests/unit/test_kill_orphans_out.py` | TDD for cleanup.py `--out-file` (red first) |
| Modify | `.github/prompts/kill-orphans.prompt.md` | Route through `run_task`; no raw PowerShell |
| Modify | `skills/{SLANG_GLIMPSE,SLANG_LINT,SLANG_REGTEST_FIX,SLANG_REVIEW,SLANG_REVIEW_INSPECT}/SKILL.md` | Re-fence `^`-continuation blocks as ```cmd |
| Create | `.vscode/tasks.json` | Tracked task registry: 41 mirrored objects + `kill-orphans-force` + `vol-test`/`vol-lint`/`vol-typecheck` |
| Modify | `ml-vol-estimator.code-workspace` | Tasks array kept in lockstep with tasks.json (same 45 objects) |
| Modify | `workspace/lint/lint_vscode_tasks.py` | `load_workspace_tasks()` reads tasks.json as primary; V1 divergence check; T5 exemption for CLI tasks |
| Modify | `memory/ref/vol-cli.md` | Regenerated from the `vol` help heredoc — all 34 commands |

---

## 3. Interfaces

**Consumes (from earlier plans / the ledger — copied, not re-derived):**

- `S-A` / `S-B` / `S-C` surface definitions — AGENTS.md "Supported Execution Surfaces" (Plan 02).
- Sentinel protocol: `workspace/tmp/exec/<ts>_<pid>.out` with `OUTPUT_FILE=` and `EXIT_CODE=` lines (`vol:327-411`, unchanged).
- `src/volforecast/cli/*.py` `register(subparsers)` / `set_defaults(func=…)` pattern (00-overview §3 item 12) — the model for the `forecast` arm wiring and the shape of the BACKTEST CLI.
- `src/volforecast/utils/paths.py::resolve_project_root()` root markers `AGENTS.md` / `vol.cmd` / `vol` (00-overview §3 item 11).
- Return contract + packet schema — 00-overview §5.1/§5.2.

**Produces (later plans rely on these — ledger rows unless flagged as deviations in §9):**

- `vol.cmd` at repo root: `test`, `test-all`, `testlf`, `lint`, `fmt`, `typecheck`, `exec`, `bg`, `jobs`, `help`; every other arm → exit 2 with `"GS Coder workspace only — run via ./vol on S-B"`. All arms write the sentinel protocol.
- `./vol` OS guard: non-Linux `uname -s` → exit 2: `"ERROR: ./vol requires the GS Linux Coder workspace (nix+uv). On Windows use vol.cmd (dev loop) or VS Code tasks."`
- Interpreter resolution order (shared by `vol.cmd` and `_run.cmd` — kills AW-54): 1) `workspace/config/user.json` `python_path` → 2) `H:\venv315..38` scan → 3) `%ROOT%\src\.venv\Scripts\python.exe` → 4) `where python`.
- `forecast` case arm in `./vol` (→ 34 total arms; the count `lint_vol_parity.py` in Plan 04 asserts against `memory/ref/vol-cli.md`).
- `.vscode/tasks.json` tracked, primary task source; `lint_vscode_tasks.py` divergence check (Plan 04 registers no new tuple for this — the existing `vscode tasks` LINTS entry now covers it).
- Args-file contract: fixed path = the exact `--args-file` value in the task definition (naming convention for NEW tasks: `workspace/tmp/<task_label_with_dashes_as_underscores>_args.json`); `run_id` INSIDE the JSON body, pattern `[a-z0-9-]+`; `create_and_run_task` retired everywhere incl. `memory/ref/vscode-tasks.md` rule E3. Plan 04's `lint_args_contract.py` enforces doc↔task-def parity.
- `volforecast.evaluation.economic_value.main(argv) -> int` — args-file CLI (`--args-file <json>`), runnable as `python -m volforecast.evaluation.economic_value` (see §9 deviation 1).
- `skills/_shared/vf_entry.py` — generic adapter; target module pinned by wrapper env var `_VF_MODULE`; args JSON `{"argv": [...], "out_file": "workspace/tmp/..."}`. Plan 04's `lint_wrapper_targets.py` must treat `_VF_MODULE` values as wrapper targets.
- `<args-file>.fail` bootstrap-failure sentinel convention in `_run.{sh,cmd}` (see §9 deviation 5).
- `memory/ref/vol-cli.md` regenerated, command-for-command with the help heredoc — the fixture `lint_vol_parity.py` (Plan 04) locks.

---

## 4. Tasks

### Task 1: `./vol` OS guard + nix-graceful hint + `forecast` arm

**Files:** Modify — `vol` (only: new guard block after line 17 region, the uv-hint string at `vol:21`, one new `case` arm, one help-heredoc line).

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-1"
goal: "./vol exits 2 with the exact Windows-fallback error on non-Linux uname, hints a non-nix uv install, and dispatches the already-registered forecast subcommand via a new case arm + help line — with vol:327-411 byte-identical to before."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md   # this task section
  - vol
  - src/volforecast/__main__.py          # read-only: confirm forecast registered (~line 152-225 register block)
  - src/volforecast/cli/forecast.py      # read-only: help= string at ~line 480-482
write_scope:
  - vol
acceptance_criteria:
  - "S-B: ./vol forecast --help → exit 0, usage text mentions --symbol and --horizons"
  - "S-B: ./vol help | grep -c 'forecast' → >= 1"
  - "S-B: ./vol test -x -q → green (regression: guard does not break Linux)"
  - "S-A (or any non-Linux shell incl. Git-Bash on Windows): ./vol → exit code 2, stderr exactly: ERROR: ./vol requires the GS Linux Coder workspace (nix+uv). On Windows use vol.cmd (dev loop) or VS Code tasks."
  - "git diff vol | grep -c 'setsid' → 0 (exec/bg machinery untouched)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "do NOT edit vol lines 327-411 (exec/bg/jobs); do NOT reorder existing case arms"
  - "the error string is the interface ledger's, verbatim — later plans grep for it"
context_summary: |
  AW-07/AW-G9/AW-G19: ./vol is bash+nix-only with no OS guard — on Windows it dies at
  `source .venv/bin/activate` with no pointer to the fallback. AW-G7: `forecast` is registered in
  __main__.py (test_cli_dispatch.py ALL_COMMANDS includes it) but has no ./vol case arm, so it is
  unreachable through the mandated wrapper. Task 2 ships vol.cmd (the thing the error message names);
  Task 9 regenerates vol-cli.md and needs the final 34-arm help heredoc from this task.
depends_on: []
```

- [ ] **Step 1 (red):** on S-B run `./vol forecast --help` → expect `ERROR: Unknown command "forecast". Run "vol help" for usage.` and exit 1 (the `*)` default at `vol:412-415`). On a non-Linux shell run `./vol` → observe it proceeds past line 19 and fails uncontrolled (or errors at `uv`/`activate`). Paste both outputs as the red evidence.
- [ ] **Step 2 (implement):** three edits to `vol`:

  (a) Immediately after `SRC="${ROOT}/src"` (line ~17), insert:

  ```bash
  # ---- OS guard: ./vol is S-B (GS Linux Coder workspace) only ----
  case "$(uname -s)" in
      Linux) ;;
      *)
          echo "ERROR: ./vol requires the GS Linux Coder workspace (nix+uv). On Windows use vol.cmd (dev loop) or VS Code tasks." >&2
          exit 2
          ;;
  esac
  ```

  (b) Replace the uv-missing hint at `vol:21`:

  ```bash
  echo "ERROR: uv not found on PATH. Install via: nix-env -iA nixpkgs.uv (Coder workspace) or pipx install uv" >&2
  ```

  (c) Add the `forecast)` arm directly after the `run)` arm (`vol:231-233`), mirroring its exact shape:

  ```bash
      forecast)
          LD_LIBRARY_PATH="${_NIX_PY_LD_PATH}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" python -m volforecast forecast "$@"
          ;;
  ```

  (d) Add one help line under the `━━━ Experiment Management ━━━` heredoc section (after the `compare` block, before `kvar`):

  ```
    forecast [args]         Generate live RV forecast and IV-RV gap signal (LONG/SHORT/FLAT)
          --symbol <sym>      Target symbol (default: SPY)
          --horizons <list>   Forecast horizons, comma-separated (default: 1,5)
  ```

  (The one-line description is the `help=` string from `cli/forecast.py:482`, verbatim.)
- [ ] **Step 3 (green):** run all five acceptance commands; paste output. The nix-store probe (`vol:38-45`) needs no change — it already only fires when `python3` resolves into `/nix/store/`; confirm with `git diff` that the block is untouched.
- [ ] **Step 4 (commit):** `feat(cli): add OS guard and forecast arm to ./vol`

### Task 2: NEW `vol.cmd` — Windows dev-loop shim

**Files:** Create — `vol.cmd` (repo root).

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-2"
goal: "A repo-root vol.cmd implements test/test-all/testlf/lint/fmt/typecheck/exec/bg/jobs/help with the ./vol sentinel protocol (workspace\\tmp\\exec\\<ts>_<pid>.out, OUTPUT_FILE=/EXIT_CODE=) and the 4-step interpreter resolution, and exits 2 naming S-B for every other arm."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md   # carries the complete script
  - vol                                    # read-only: mirror test/lint/typecheck flags (vol:212-245)
  - skills/_shared/_run.cmd                # read-only: the H:\venv scan loop to mirror (lines 30-37)
  - workspace/config/user.json.template    # read-only: python_path key shape
write_scope:
  - vol.cmd
acceptance_criteria:
  - "S-A: vol.cmd test -x -q → prints OUTPUT_FILE=<path>; that file exists and its last line is EXIT_CODE=0  [S-B fallback if H:\\venv/src\\.venv lack pytest: run vol.cmd help + vol.cmd exec echo ok only, tag criterion S-A-DEFERRED]"
  - "S-A: vol.cmd exec python --version → sentinel file ends EXIT_CODE=0 and contains a Python version"
  - "S-A: vol.cmd bg ping -n 2 127.0.0.1 → returns immediately with OUTPUT_FILE=; vol.cmd jobs shows it RUNNING then DONE"
  - "S-A: vol.cmd run → exit code 2, stderr contains: GS Coder workspace only — run via ./vol on S-B"
  - "S-A: vol.cmd sync → same exit 2 message (any non-dev-loop arm)"
  - "S-B: file exists at repo root; resolve_project_root() still resolves (./vol exec python -c \"from volforecast.utils.paths import resolve_project_root; print(resolve_project_root())\" → repo root)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "interpreter resolution order is the ledger's, exactly: user.json python_path → H:\\venv315..38 → %ROOT%\\src\\.venv\\Scripts\\python.exe → where python"
  - "cmd.exe built-ins + PowerShell one-liners only; no new dependencies; no .ps1 sibling"
  - "test arm mirrors ./vol test flags: pytest tests/ -m \"not slow\" (vol:218); test-all: pytest tests/; testlf: pytest tests/ --lf; lint: ruff check .; fmt: ruff format .; typecheck: mypy volforecast/ — all run from src/"
context_summary: |
  S-A (GS Windows desktop) is the PRIMARY surface and executes this very plan suite, but ./vol is
  bash-only (Task 1 now makes it exit 2 there and point here). utils/paths.py::resolve_project_root()
  already lists vol.cmd as a repo-root marker — this file fills a designed-for seam. The sentinel
  protocol must match ./vol exec/bg byte-for-byte in its two contract lines (OUTPUT_FILE= to stdout,
  EXIT_CODE=<n> as the file's final line) so agent instructions are surface-independent. Task 8 wires
  vol-test/vol-lint/vol-typecheck VS Code tasks onto this shim.
depends_on: []
```

- [ ] **Step 1 (red):** on S-A run `vol.cmd help` → `'vol.cmd' is not recognized...` (file absent). Paste.
- [ ] **Step 2 (implement):** create `vol.cmd` with exactly this content:

  ```bat
  @echo off
  REM vol.cmd — Windows (S-A) dev-loop shim for ./vol. Plan 03 / wfo-03-2.
  REM Supported arms: test test-all testlf lint fmt typecheck exec bg jobs help.
  REM Every other ./vol arm is Linux-only: exit 2 pointing at S-B.
  REM Sentinel protocol (identical to ./vol exec/bg):
  REM   prints OUTPUT_FILE=<workspace\tmp\exec\<ts>_<pid>.out>; file's last line is EXIT_CODE=<rc>.
  setlocal EnableDelayedExpansion

  set "ROOT=%~dp0"
  set "SRC=%ROOT%src"

  REM ---- Interpreter resolution (ledger order; shared with skills\_shared\_run.cmd) ----
  set "PY="
  REM 1) workspace\config\user.json python_path
  if exist "%ROOT%workspace\config\user.json" (
      for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "try { (Get-Content -Raw '%ROOT%workspace\config\user.json' | ConvertFrom-Json).python_path } catch { '' }"`) do (
          if exist "%%P" set "PY=%%P"
      )
  )
  REM 2) H:\venv scan (newest first — same list as _run.cmd)
  if not defined PY for %%V in (315 314 313 312 311 310 39 38) do (
      if not defined PY if exist "H:\venv%%V\Scripts\python.exe" set "PY=H:\venv%%V\Scripts\python.exe"
  )
  REM 3) repo-local venv
  if not defined PY if exist "%SRC%\.venv\Scripts\python.exe" set "PY=%SRC%\.venv\Scripts\python.exe"
  REM 4) PATH
  if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
  if not defined PY (
      echo ERROR: no Python interpreter found. Checked: user.json python_path, H:\venv*, src\.venv, PATH. >&2
      echo Fallback: run this command via ./vol on S-B ^(GS Linux Coder workspace^). >&2
      exit /b 2
  )

  set "CMD=%~1"
  if "%CMD%"=="" set "CMD=help"

  REM ---- Collect args after the subcommand (%* cannot be shifted in cmd) ----
  set "ARGS="
  :collect
  shift
  if "%~1"=="" goto dispatch
  set ARGS=!ARGS! "%~1"
  goto collect

  :dispatch
  if /I "%CMD%"=="help"      goto do_help
  if /I "%CMD%"=="test"      goto do_test
  if /I "%CMD%"=="test-all"  goto do_testall
  if /I "%CMD%"=="testlf"    goto do_testlf
  if /I "%CMD%"=="lint"      goto do_lint
  if /I "%CMD%"=="fmt"       goto do_fmt
  if /I "%CMD%"=="typecheck" goto do_typecheck
  if /I "%CMD%"=="exec"      goto do_exec
  if /I "%CMD%"=="bg"        goto do_bg
  if /I "%CMD%"=="jobs"      goto do_jobs
  echo ERROR: "%CMD%" is GS Coder workspace only — run via ./vol on S-B. >&2
  exit /b 2

  :do_help
  echo vol.cmd — Windows dev-loop shim for ./vol (S-A)
  echo.
  echo Usage: vol.cmd ^<command^> [args...]
  echo.
  echo   test [args]        pytest, skipping @pytest.mark.slow (mirror of ./vol test)
  echo   test-all [args]    full pytest suite
  echo   testlf [args]      re-run last-failed tests
  echo   lint [args]        ruff check .
  echo   fmt [args]         ruff format .
  echo   typecheck [args]   mypy volforecast/
  echo   exec ^<cmd...^>      run captured: prints OUTPUT_FILE=, file ends EXIT_CODE=
  echo   bg ^<cmd...^>        fire-and-forget: poll OUTPUT_FILE for EXIT_CODE= sentinel
  echo   jobs               list background jobs (RUNNING/DONE by sentinel presence)
  echo.
  echo All other ./vol commands (run, sync, ingest-*, kvar, present, ...) are
  echo GS Coder workspace only — run via ./vol on S-B.
  exit /b 0

  :do_test
  call :mk_out
  pushd "%SRC%"
  "%PY%" -m pytest tests/ -m "not slow" !ARGS! > "!_OUT_FILE!" 2>&1
  set "_EC=!ERRORLEVEL!"
  popd
  goto finish

  :do_testall
  call :mk_out
  pushd "%SRC%"
  "%PY%" -m pytest tests/ !ARGS! > "!_OUT_FILE!" 2>&1
  set "_EC=!ERRORLEVEL!"
  popd
  goto finish

  :do_testlf
  call :mk_out
  pushd "%SRC%"
  "%PY%" -m pytest tests/ --lf !ARGS! > "!_OUT_FILE!" 2>&1
  set "_EC=!ERRORLEVEL!"
  popd
  goto finish

  :do_lint
  call :mk_out
  pushd "%SRC%"
  "%PY%" -m ruff check . !ARGS! > "!_OUT_FILE!" 2>&1
  set "_EC=!ERRORLEVEL!"
  popd
  goto finish

  :do_fmt
  call :mk_out
  pushd "%SRC%"
  "%PY%" -m ruff format . !ARGS! > "!_OUT_FILE!" 2>&1
  set "_EC=!ERRORLEVEL!"
  popd
  goto finish

  :do_typecheck
  call :mk_out
  pushd "%SRC%"
  "%PY%" -m mypy volforecast/ !ARGS! > "!_OUT_FILE!" 2>&1
  set "_EC=!ERRORLEVEL!"
  popd
  goto finish

  :do_exec
  if "!ARGS!"=="" (
      echo ERROR: vol exec requires a command. Usage: vol.cmd exec ^<command^> [args...] >&2
      exit /b 1
  )
  call :mk_out
  pushd "%SRC%"
  cmd /c !ARGS! > "!_OUT_FILE!" 2>&1
  set "_EC=!ERRORLEVEL!"
  popd
  goto finish

  :do_bg
  if "!ARGS!"=="" (
      echo ERROR: vol bg requires a command. Usage: vol.cmd bg ^<command^> [args...] >&2
      exit /b 1
  )
  call :mk_out
  set "_RUNNER=!_OUT_FILE!.run.cmd"
  >  "!_RUNNER!" echo @echo off
  >> "!_RUNNER!" echo cd /d "%SRC%"
  >> "!_RUNNER!" echo cmd /c !ARGS! ^> "!_OUT_FILE!" 2^>^&1
  >> "!_RUNNER!" echo echo EXIT_CODE=%%ERRORLEVEL%%^>^> "!_OUT_FILE!"
  >> "!_RUNNER!" echo del "%%~f0"
  start "" /b cmd /c "!_RUNNER!"
  echo ---
  echo Launched. Poll OUTPUT_FILE for EXIT_CODE= sentinel.
  exit /b 0

  :do_jobs
  set "_OUT_DIR=%ROOT%workspace\tmp\exec"
  set "_FOUND=0"
  if exist "%_OUT_DIR%" for %%F in ("%_OUT_DIR%\*.out") do (
      set "_FOUND=1"
      findstr /b /c:"EXIT_CODE=" "%%F" >nul 2>&1 && ( echo DONE     output=%%F ) || ( echo RUNNING  output=%%F )
  )
  if "!_FOUND!"=="0" echo No background jobs found.
  exit /b 0

  :mk_out
  set "_OUT_DIR=%ROOT%workspace\tmp\exec"
  if not exist "%_OUT_DIR%" mkdir "%_OUT_DIR%"
  for /f %%I in ('powershell -NoProfile -Command "[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()"') do set "_TS=%%I"
  for /f %%I in ('powershell -NoProfile -Command "$PID"') do set "_MYPID=%%I"
  set "_OUT_FILE=%_OUT_DIR%\!_TS!_!_MYPID!.out"
  echo OUTPUT_FILE=!_OUT_FILE!
  exit /b 0

  :finish
  echo EXIT_CODE=!_EC!>> "!_OUT_FILE!"
  echo EXIT_CODE=!_EC!
  echo Done. Read: !_OUT_FILE!
  exit /b !_EC!
  ```

  Design notes the subagent must not "improve away": dev-loop arms are exec-captured (Gate D reads their sentinel files); `jobs` classifies by sentinel presence instead of `.pid` files (no `$$` in cmd — documented divergence, §9 deviation 6); `bg` writes a self-deleting runner `.cmd` next to the out-file (the only reliable way to append `EXIT_CODE=` from a detached cmd process).
- [ ] **Step 3 (green):** run the six acceptance commands on the surfaces indicated; paste output. If pytest/ruff/mypy are missing from every resolved interpreter, apply the named fallback: verify `help`/`exec`/`bg`/`jobs`/exit-2 arms on S-A, tag the tool-arm criteria `S-A-DEFERRED (deps absent — decision-record risk 2)`, and record which interpreter step (1–4) resolved.
- [ ] **Step 4 (commit):** `feat(cli): add vol.cmd windows dev-loop shim with sentinel protocol`

### Task 3: BACKTEST args-file CLI (TDD) + delete dead CLI stubs

**Files:** Create — `src/tests/unit/test_economic_value_cli.py`. Modify — `src/volforecast/evaluation/economic_value.py`. Delete — `src/volforecast/cli/notebook.py`, `src/volforecast/cli/research.py`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-3"
goal: "python -m volforecast.evaluation.economic_value --args-file <json> computes economic_value_summary from a CSV and writes an out_file ending EXIT_CODE=<rc> (TDD, red first), and the NotImplementedError stubs cli/notebook.py + cli/research.py are gone."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md   # carries test + implementation code
  - src/volforecast/evaluation/economic_value.py       # economic_value_summary at ~line 878
  - src/tests/unit/test_cli_dispatch.py                # exemplar: characterization-test style
  - src/volforecast/cli/notebook.py                    # to delete
  - src/volforecast/cli/research.py                    # to delete
write_scope:
  - src/volforecast/evaluation/economic_value.py
  - src/tests/unit/test_economic_value_cli.py
  - src/volforecast/cli/notebook.py
  - src/volforecast/cli/research.py
acceptance_criteria:
  - "./vol test -k test_economic_value_cli → 4 passed (red shown first: ImportError on main)"
  - "./vol exec python -c \"import volforecast.cli.notebook\" → sentinel file shows ModuleNotFoundError (stub gone)"
  - "grep -rn 'cli.notebook\\|cli.research\\|cli import notebook\\|cli import research' src/ → 0 hits"
  - "./vol test → green (full non-slow suite; deletion broke nothing)"
  - "./vol test -k test_cli_dispatch → passed unchanged (characterization intact)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "TDD failing-first: show red, then green (HARD Rule 5 — this is src/ Python)"
  - "do NOT delete src/volforecast/cli/build_features.py (test_features.py:20 imports build_layer — AW-G8 do-NOT)"
  - "do NOT add a new vol subcommand or touch __main__.py — the CLI is module-level (python -m volforecast.evaluation.economic_value), matching the BACKTEST wrapper's existing dotted path"
context_summary: |
  AW-05 (BLOCKER, BACKTEST variant): skills/BACKTEST wrappers invoke
  `python -m volforecast.evaluation.economic_value --args-file ...` but the module has no argparse or
  __main__ handling, so the flag is silently ignored. This task gives the module a real main(argv)->int
  mirroring the cli/*.py handle() shape (returns int; args-file JSON in, out_file with EXIT_CODE
  sentinel out). cli/notebook.py and cli/research.py raise NotImplementedError in every function and
  have zero inbound references — Task 4 marks their skills agent-driven-only. Task 4's BACKTEST wrapper
  passthrough depends on main() existing.
depends_on: []
```

- [ ] **Step 1 (write the failing test):** create `src/tests/unit/test_economic_value_cli.py`:

  ```python
  """Args-file CLI for evaluation/economic_value.py (Plan 03 wfo-03-3, AW-05 BACKTEST variant).

  Contract: python -m volforecast.evaluation.economic_value --args-file <json>
    args JSON: {"csv": <path>, "columns": {<summary-kwarg>: <csv-column>, ...},
                "model_name": <str>, "out_file": <path>}
    columns required: vol_forecast, daily_returns.
    columns optional: realized_vol, implied_vol, spot, signal (absent -> vol-targeting-only).
    out_file: JSON summary body, then a final line EXIT_CODE=<rc>.
  """

  from __future__ import annotations

  import json
  from pathlib import Path

  import numpy as np
  import pandas as pd


  def _write_inputs(tmp_path: Path, *, full: bool = True) -> tuple[Path, Path]:
      rng = np.random.default_rng(42)
      n = 300
      data = {
          "fc": np.abs(rng.normal(0.15, 0.03, n)),
          "ret": rng.normal(0.0, 0.01, n),
      }
      columns = {"vol_forecast": "fc", "daily_returns": "ret"}
      if full:
          data.update(
              rv=np.abs(rng.normal(0.15, 0.03, n)),
              iv=np.abs(rng.normal(0.17, 0.03, n)),
              spot=100.0 + np.cumsum(rng.normal(0.0, 1.0, n)),
              sig=rng.choice([-1.0, 0.0, 1.0], n),
          )
          columns.update(realized_vol="rv", implied_vol="iv", spot="spot", signal="sig")
      csv = tmp_path / "preds.csv"
      pd.DataFrame(data).to_csv(csv, index=False)
      out = tmp_path / "backtest_out.json"
      args_file = tmp_path / "backtest_args.json"
      args_file.write_text(
          json.dumps(
              {"csv": str(csv), "columns": columns, "model_name": "har", "out_file": str(out)}
          ),
          encoding="utf-8",
      )
      return args_file, out


  def _parse_out(out: Path) -> tuple[dict, str]:
      lines = out.read_text(encoding="utf-8").rstrip().splitlines()
      return json.loads("\n".join(lines[:-1])), lines[-1]


  class TestEconomicValueCli:
      def test_full_columns_returns_zero_and_writes_summary(self, tmp_path: Path) -> None:
          from volforecast.evaluation.economic_value import main

          args_file, out = _write_inputs(tmp_path, full=True)
          rc = main(["--args-file", str(args_file)])
          assert rc == 0
          body, sentinel = _parse_out(out)
          assert sentinel == "EXIT_CODE=0"
          assert body["model"] == "har"
          for key in ("vol_target_sharpe", "vol_target_max_dd", "straddle_sharpe", "hit_rate"):
              assert key in body

      def test_vol_targeting_only_when_optional_columns_absent(self, tmp_path: Path) -> None:
          from volforecast.evaluation.economic_value import main

          args_file, out = _write_inputs(tmp_path, full=False)
          assert main(["--args-file", str(args_file)]) == 0
          body, sentinel = _parse_out(out)
          assert sentinel == "EXIT_CODE=0"
          assert "vol_target_sharpe" in body
          assert "straddle_sharpe" not in body

      def test_missing_args_file_returns_one(self, tmp_path: Path) -> None:
          from volforecast.evaluation.economic_value import main

          assert main(["--args-file", str(tmp_path / "absent.json")]) == 1

      def test_missing_required_column_writes_error_and_sentinel_one(self, tmp_path: Path) -> None:
          from volforecast.evaluation.economic_value import main

          args_file, out = _write_inputs(tmp_path, full=False)
          spec = json.loads(args_file.read_text(encoding="utf-8"))
          del spec["columns"]["daily_returns"]
          args_file.write_text(json.dumps(spec), encoding="utf-8")
          assert main(["--args-file", str(args_file)]) == 1
          body, sentinel = _parse_out(out)
          assert sentinel == "EXIT_CODE=1"
          assert "error" in body
  ```

- [ ] **Step 2 (run to confirm red):** `./vol test -k test_economic_value_cli` → expect 4 failures, each `ImportError: cannot import name 'main' from 'volforecast.evaluation.economic_value'`. Paste.
- [ ] **Step 3 (implement):** append to `src/volforecast/evaluation/economic_value.py` (after `gsvivs_baseline_signals`, end of file):

  ```python
  # ---------------------------------------------------------------------------
  # Args-file CLI — BACKTEST skill entry point (Plan 03 / AW-05).
  # Mirrors the cli/*.py handle() shape: argv in, int out, sentinel out_file.
  # Invoke: python -m volforecast.evaluation.economic_value --args-file <json>
  # ---------------------------------------------------------------------------

  _CLI_REQUIRED = ("vol_forecast", "daily_returns")
  _CLI_OPTIONAL = ("realized_vol", "implied_vol", "spot", "signal")


  def _cli_series(df: Any, columns: dict[str, str], key: str) -> np.ndarray | None:
      """Pull one mapped column as float64, or None if unmapped."""
      name = columns.get(key)
      if name is None:
          return None
      if name not in df.columns:
          raise KeyError(f"columns.{key} -> {name!r} not found in CSV")
      return df[name].to_numpy(dtype=np.float64)


  def main(argv: list[str] | None = None) -> int:
      """Args-file CLI entry point (see module docstring of the companion test)."""
      import argparse
      import json
      import sys
      from pathlib import Path

      import pandas as pd

      parser = argparse.ArgumentParser(
          prog="volforecast.evaluation.economic_value",
          description="Economic-value backtest from a predictions CSV (BACKTEST skill).",
      )
      parser.add_argument("--args-file", required=True, type=Path)
      ns = parser.parse_args(argv)

      if not ns.args_file.is_file():
          print(f"ERROR: args file not found: {ns.args_file}", file=sys.stderr)
          return 1

      spec = json.loads(ns.args_file.read_text(encoding="utf-8"))
      out_file = Path(spec["out_file"])
      rc = 0
      try:
          columns: dict[str, str] = spec["columns"]
          df = pd.read_csv(Path(spec["csv"]))
          series = {k: _cli_series(df, columns, k) for k in (*_CLI_REQUIRED, *_CLI_OPTIONAL)}
          missing = [k for k in _CLI_REQUIRED if series[k] is None]
          if missing:
              raise KeyError(f"required columns mapping missing: {missing}")
          result = economic_value_summary(
              signal=series["signal"],
              realized_vol=series["realized_vol"],
              implied_vol=series["implied_vol"],
              spot_prices=series["spot"],
              daily_returns=series["daily_returns"],
              vol_forecast=series["vol_forecast"],
              model_name=spec.get("model_name", ""),
          )
          body = json.dumps(result, indent=2, default=float)
      except Exception as exc:  # noqa: BLE001 — every failure must reach the sentinel file
          rc = 1
          body = json.dumps({"error": f"{type(exc).__name__}: {exc}"})

      out_file.parent.mkdir(parents=True, exist_ok=True)
      out_file.write_text(f"{body}\nEXIT_CODE={rc}\n", encoding="utf-8")
      print(f"OUTPUT_FILE={out_file}")
      return rc


  if __name__ == "__main__":  # pragma: no cover
      import sys

      sys.exit(main())
  ```

  (`Any` and `np` are already imported at module top — `economic_value.py:22-25`.) Then `git rm src/volforecast/cli/notebook.py src/volforecast/cli/research.py`.
- [ ] **Step 4 (run to green):** all five acceptance commands; paste. `./vol lint` and `./vol typecheck` must also stay green (new code is typed).
- [ ] **Step 5 (commit):** `feat(cli): args-file CLI for economic_value; drop dead notebook/research stubs`

### Task 4: Collapse the 6 ML-skill wrappers onto `_shared/_run.{sh,cmd}` and repoint at modules that exist

**Files:** Create — `skills/_shared/vf_entry.py`, `src/tests/unit/test_vf_entry.py`, `skills/BACKTEST/src/backtest_entry.py`. Modify — `skills/{MODEL_TRAIN,FEATURE_BUILD,EVALUATE,DATA_INGEST,BACKTEST}/src/*_task.{sh,cmd}` (10 files, rewritten), `skills/{MODEL_TRAIN,FEATURE_BUILD,EVALUATE,DATA_INGEST,BACKTEST,NOTEBOOK,RESEARCH}/SKILL.md`. Delete — `skills/NOTEBOOK/src/notebook_task.{sh,cmd}`, `skills/RESEARCH/src/research_task.{sh,cmd}`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-4"
goal: "All five runnable ML-skill task wrappers are 3-4-line _shared/_run.{sh,cmd} bootstrap callers whose Python targets exist and import (vf_entry.py TDD-first); NOTEBOOK/RESEARCH lose their task paths and their SKILL.mds say agent-driven-only."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md   # carries all code
  - skills/_shared/_run.sh                       # read-only: bootstrap contract (_PY_SCRIPT/_SKILL)
  - skills/_shared/_run.cmd                      # read-only: same, Windows
  - workspace/lint/lint_task.sh                  # exemplar: correct 4-line bootstrap wrapper
  - src/volforecast/cli/ingest.py                # read-only: main(argv) target for DATA_INGEST
  - src/volforecast/utils/paths.py               # read-only: resolve_project_root for the test loader
write_scope:
  - skills/_shared/vf_entry.py
  - src/tests/unit/test_vf_entry.py
  - skills/BACKTEST/src/backtest_entry.py
  - skills/MODEL_TRAIN/src/train_task.sh
  - skills/MODEL_TRAIN/src/train_task.cmd
  - skills/FEATURE_BUILD/src/feature_task.sh
  - skills/FEATURE_BUILD/src/feature_task.cmd
  - skills/EVALUATE/src/eval_task.sh
  - skills/EVALUATE/src/eval_task.cmd
  - skills/DATA_INGEST/src/ingest_task.sh
  - skills/DATA_INGEST/src/ingest_task.cmd
  - skills/BACKTEST/src/backtest_task.sh
  - skills/BACKTEST/src/backtest_task.cmd
  - skills/NOTEBOOK/src/notebook_task.sh
  - skills/NOTEBOOK/src/notebook_task.cmd
  - skills/RESEARCH/src/research_task.sh
  - skills/RESEARCH/src/research_task.cmd
  - skills/MODEL_TRAIN/SKILL.md
  - skills/FEATURE_BUILD/SKILL.md
  - skills/EVALUATE/SKILL.md
  - skills/DATA_INGEST/SKILL.md
  - skills/BACKTEST/SKILL.md
  - skills/NOTEBOOK/SKILL.md
  - skills/RESEARCH/SKILL.md
acceptance_criteria:
  - "./vol test -k test_vf_entry → 4 passed (red shown first: FileNotFoundError, vf_entry.py absent)"
  - "S-B: for each of the 5 runnable skills, bash skills/<X>/src/<x>_task.sh --args-file <smoke args per SKILL.md example> → out_file exists, last line EXIT_CODE=0 (MODEL_TRAIN/FEATURE_BUILD/EVALUATE smoke uses argv ['--help'] to avoid a real training run)"
  - "grep -rn 'volforecast.models.train\\|volforecast.features.build\\|volforecast.evaluation.evaluate\\|volforecast.data.ingest' skills/ → 0 hits"
  - "ls skills/NOTEBOOK/src/*_task.* skills/RESEARCH/src/*_task.* 2>/dev/null → no files"
  - "grep -c 'workspaceFolder: \"h:' skills/MODEL_TRAIN/SKILL.md skills/FEATURE_BUILD/SKILL.md skills/EVALUATE/SKILL.md skills/DATA_INGEST/SKILL.md skills/BACKTEST/SKILL.md → 0 each"
  - "grep -l 'agent-driven only' skills/NOTEBOOK/SKILL.md skills/RESEARCH/SKILL.md → both files"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "TDD failing-first for vf_entry.py (it is tested from src/tests — Rule 5 applies)"
  - "do not modify _run.sh/_run.cmd (Task 5 owns them); do not touch ml-vol-estimator.code-workspace or .vscode/ (Task 8 owns them)"
  - "wrappers must set _PY_SCRIPT and _SKILL exactly as _run.cmd:8-11 documents (B1/B2 lint rules)"
context_summary: |
  AW-05 (BLOCKER): 4 of 5 ML wrappers call Python modules that do not exist; BACKTEST's target exists
  but ignored --args-file until wfo-03-3 (now merged) gave it main(). The collapse target is the
  bootstrap architecture ~40 skills already use (exemplar: workspace/lint/lint_task.sh). One generic
  adapter (vf_entry.py, module pinned by _VF_MODULE env var set in the wrapper) routes MODEL_TRAIN/
  FEATURE_BUILD/EVALUATE to volforecast.__main__ (the working `run`/experiment path) and DATA_INGEST to
  volforecast.cli.ingest; BACKTEST gets a 7-line passthrough to economic_value.main. NOTEBOOK/RESEARCH
  have no working module (stubs deleted in wfo-03-3): their task paths die and SKILL.mds say
  agent-driven-only. Task 8 later removes their task objects from the registries.
depends_on: ["wfo-03-3"]
```

- [ ] **Step 1 (write the failing test):** create `src/tests/unit/test_vf_entry.py`:

  ```python
  """skills/_shared/vf_entry.py — generic args-file adapter (Plan 03 wfo-03-4, AW-05).

  Contract: wrapper sets _VF_MODULE (allowed volforecast entry point); args JSON is
  {"argv": [...], "out_file": <path>}; adapter imports the module, calls main(argv),
  captures stdout+stderr into out_file ending with EXIT_CODE=<rc>, and returns rc.
  """

  from __future__ import annotations

  import importlib.util
  import json
  from pathlib import Path

  import pytest

  from volforecast.utils.paths import resolve_project_root


  def _load_vf_entry():
      path = resolve_project_root() / "skills" / "_shared" / "vf_entry.py"
      spec = importlib.util.spec_from_file_location("vf_entry", path)
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      return mod


  def _args_file(tmp_path: Path, argv: list[str]) -> tuple[Path, Path]:
      out = tmp_path / "out.txt"
      af = tmp_path / "args.json"
      af.write_text(json.dumps({"argv": argv, "out_file": str(out)}), encoding="utf-8")
      return af, out


  def test_routes_help_to_volforecast_main(tmp_path, monkeypatch):
      vf = _load_vf_entry()
      af, out = _args_file(tmp_path, ["--help"])
      monkeypatch.setenv("_VF_MODULE", "volforecast.__main__")
      rc = vf.main(["--args-file", str(af)])
      assert rc == 0
      text = out.read_text(encoding="utf-8")
      assert "usage" in text.lower()
      assert text.rstrip().splitlines()[-1] == "EXIT_CODE=0"


  def test_disallowed_module_is_rejected(tmp_path, monkeypatch):
      vf = _load_vf_entry()
      af, out = _args_file(tmp_path, [])
      monkeypatch.setenv("_VF_MODULE", "os")
      rc = vf.main(["--args-file", str(af)])
      assert rc != 0
      assert "not an allowed entry point" in out.read_text(encoding="utf-8")


  def test_missing_args_file_returns_one(tmp_path, monkeypatch):
      vf = _load_vf_entry()
      monkeypatch.setenv("_VF_MODULE", "volforecast.__main__")
      assert vf.main(["--args-file", str(tmp_path / "absent.json")]) == 1


  def test_target_failure_reaches_sentinel(tmp_path, monkeypatch):
      vf = _load_vf_entry()
      af, out = _args_file(tmp_path, ["definitely-not-a-subcommand"])
      monkeypatch.setenv("_VF_MODULE", "volforecast.__main__")
      rc = vf.main(["--args-file", str(af)])
      assert rc != 0
      assert out.read_text(encoding="utf-8").rstrip().splitlines()[-1] == f"EXIT_CODE={rc}"
  ```

- [ ] **Step 2 (run to confirm red):** `./vol test -k test_vf_entry` → 4 errors (`FileNotFoundError` from `spec_from_file_location` — file absent). Paste.
- [ ] **Step 3 (implement):**

  (a) `skills/_shared/vf_entry.py`:

  ```python
  """Generic args-file adapter: routes a skill task to a real volforecast entry point.

  The calling wrapper pins the target via the _VF_MODULE env var; the args-file JSON
  supplies {"argv": [...], "out_file": "workspace/tmp/<skill>_out.txt"}. Output protocol
  matches ./vol exec: everything captured into out_file, final line EXIT_CODE=<rc>.
  Plan 03 wfo-03-4 (AW-05). Do not add modules to ALLOWED without a SKILL.md owner.
  """

  from __future__ import annotations

  import argparse
  import contextlib
  import importlib
  import io
  import json
  import os
  import sys
  from pathlib import Path

  ROOT = Path(__file__).resolve().parents[2]

  ALLOWED = {
      "volforecast.__main__",       # MODEL_TRAIN / FEATURE_BUILD / EVALUATE (run/experiments/compare)
      "volforecast.cli.ingest",     # DATA_INGEST
  }


  def main(argv: list[str] | None = None) -> int:
      parser = argparse.ArgumentParser(prog="vf_entry")
      parser.add_argument("--args-file", required=True, type=Path)
      ns = parser.parse_args(argv)

      if not ns.args_file.is_file():
          print(f"ERROR: args file not found: {ns.args_file}", file=sys.stderr)
          return 1
      spec = json.loads(ns.args_file.read_text(encoding="utf-8"))
      out_file = Path(spec["out_file"])
      module = os.environ.get("_VF_MODULE", "")
      mod_argv = [str(a) for a in spec.get("argv", [])]

      sys.path.insert(0, str(ROOT / "src"))  # volforecast importable from any H:\venv interpreter
      buf = io.StringIO()
      if module not in ALLOWED:
          rc = 1
          buf.write(f"ERROR: {module!r} is not an allowed entry point (allowed: {sorted(ALLOWED)})")
      else:
          try:
              with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                  rc = int(importlib.import_module(module).main(mod_argv) or 0)
          except SystemExit as exc:  # argparse --help / parser errors
              rc = int(exc.code or 0)
          except Exception as exc:  # noqa: BLE001 — must reach the sentinel
              buf.write(f"\n{type(exc).__name__}: {exc}")
              rc = 1

      out_file.parent.mkdir(parents=True, exist_ok=True)
      out_file.write_text(f"{buf.getvalue()}\nEXIT_CODE={rc}\n", encoding="utf-8")
      print(f"OUTPUT_FILE={out_file}")
      return rc


  if __name__ == "__main__":  # pragma: no cover
      sys.exit(main())
  ```

  (b) `skills/BACKTEST/src/backtest_entry.py` (passthrough — economic_value.main already speaks `--args-file`):

  ```python
  """BACKTEST task entry: passthrough to volforecast.evaluation.economic_value.main."""

  from __future__ import annotations

  import sys
  from pathlib import Path

  sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

  from volforecast.evaluation.economic_value import main  # noqa: E402

  if __name__ == "__main__":
      sys.exit(main(sys.argv[1:]))
  ```

  (c) The ten wrappers. `.cmd` shape (exactly this, per skill — `_run.cmd:8-11`'s documented 3-line form plus the module pin):

  ```bat
  @echo off
  set "_PY_SCRIPT=%~dp0..\..\_shared\vf_entry.py" & set "_SKILL=MODEL_TRAIN" & set "_VF_MODULE=volforecast.__main__"
  call "%~dp0..\..\_shared\_run.cmd" %*
  ```

  `.sh` shape (mirrors `workspace/lint/lint_task.sh`):

  ```bash
  #!/usr/bin/env bash
  _SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_shared" && pwd)"
  export _PY_SCRIPT="${_SHARED}/vf_entry.py" _SKILL="MODEL_TRAIN" _VF_MODULE="volforecast.__main__"
  exec "${_SHARED}/_run.sh" "$@"
  ```

  Per-skill values:

  | Skill | `_SKILL` | `_PY_SCRIPT` | `_VF_MODULE` |
  |---|---|---|---|
  | MODEL_TRAIN (`train_task.*`) | `MODEL_TRAIN` | `_shared/vf_entry.py` | `volforecast.__main__` |
  | FEATURE_BUILD (`feature_task.*`) | `FEATURE_BUILD` | `_shared/vf_entry.py` | `volforecast.__main__` |
  | EVALUATE (`eval_task.*`) | `EVALUATE` | `_shared/vf_entry.py` | `volforecast.__main__` |
  | DATA_INGEST (`ingest_task.*`) | `DATA_INGEST` | `_shared/vf_entry.py` | `volforecast.cli.ingest` |
  | BACKTEST (`backtest_task.*`) | `BACKTEST` | `%~dp0backtest_entry.py` (own dir) | *(unset)* |

  Delete `skills/NOTEBOOK/src/notebook_task.{sh,cmd}` and `skills/RESEARCH/src/research_task.{sh,cmd}` (`git rm`).

  (d) SKILL.md updates (docs, Rule-5-exempt):
  - **MODEL_TRAIN / FEATURE_BUILD / EVALUATE:** replace the old args schema (`model_type`/`feature_config`/`cv_params`, documented in `train_task.cmd`'s pre-collapse header) with the vf_entry schema and one worked example each: args file `workspace/tmp/train_args.json` (resp. `feature_args.json`, `eval_args.json`, i.e. the exact `--args-file` value in the task definition) containing e.g. `{"argv": ["run", "--config", "workspace/configs/<trial>.yaml", "--skip-ingest"], "out_file": "workspace/tmp/model_train_out.txt"}` (EVALUATE example uses `["compare", "--experiment", "<id>", "--baseline", "<id>"]`; FEATURE_BUILD notes that feature layers are built by the pipeline — its example runs a pipeline-mode config and points at `feature_layers` in the YAML). State: results = read `out_file`; success = final line `EXIT_CODE=0`.
  - **DATA_INGEST:** args example `{"argv": ["--config", "workspace/configs/<trial>.yaml", "--symbols", "SPY"], "out_file": "workspace/tmp/data_ingest_out.txt"}` (flags per `cli/ingest.py:parse_args`).
  - **BACKTEST:** document the wfo-03-3 schema (`csv`/`columns`/`model_name`/`out_file`) with the required/optional column split; delete the stale cost-parameter promise that only the prompt carried (AW-25 fixes the prompt in Plan 07 — here only the SKILL.md schema section changes).
  - **All five:** drop `workspaceFolder: "h:\ml-vol-estimator"` from every `run_task` example (AW-13); add the one-line last-writer-wins caveat: *"The args file path is fixed per task — two concurrent agents writing it race (last writer wins). Keep `out_file` unique per run (put a `run_id` slug in its name); the args file itself is not collision-safe."*
  - **NOTEBOOK / RESEARCH:** under `## Task-Based Execution`, replace the body with: *"**Agent-driven only — no VS Code task.** This skill has no Python entry point; execute its steps directly with file tools and `./vol exec` (S-B) / `vol.cmd exec` (S-A). The former `run_task(\"notebook\"|\"research\")` path was removed (AW-05: it invoked modules that never existed)."* Also fix `NOTEBOOK/SKILL.md:135-136` stale imports to `volforecast.features` / `volforecast.evaluation`.
- [ ] **Step 4 (run to green):** `./vol test -k test_vf_entry` → 4 passed; then the smoke runs per acceptance criteria (S-B): e.g.
  `bash skills/MODEL_TRAIN/src/train_task.sh --args-file workspace/tmp/train_args.json` with `{"argv": ["--help"], "out_file": "workspace/tmp/model_train_out.txt"}` → out_file ends `EXIT_CODE=0`. Paste all five.
- [ ] **Step 5 (commit):** `chore(framework): collapse ML skill wrappers onto shared bootstrap, repoint at live modules`

### Task 5: `_run.{cmd,sh}` hardening — env guard, repo-local fallback, AW-41 failure sentinel (+ AW-13 stragglers)

**Files:** Modify — `skills/_shared/_run.cmd`, `skills/_shared/_run.sh`, `skills/PYTHON_PATH/src/resolve.ps1`, `skills/GIT/src/git_task.cmd`, `skills/SEARCH/SKILL.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-5"
goal: "_run.{cmd,sh} keep their H: probes verbatim but gain an if-exist guard on H:\\all-languages-env.cmd, the ledger's repo-local interpreter fallback chain, and an AW-41 failure sentinel (<args-file>.fail on bootstrap death, EXIT_CODE=<rc> appended to out_file on post-bootstrap crash) — while still ending in unconditional exit 0 (T9)."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md
  - skills/_shared/_run.cmd
  - skills/_shared/_run.sh
  - skills/PYTHON_PATH/src/resolve.ps1     # AW-13: needs Get-Command python fallback
  - skills/PYTHON_PATH/src/resolve.py      # read-only: the portable pattern to mirror
  - skills/GIT/src/git_task.cmd            # AW-13: H:/ml-vol-estimator noop_editor literal at ~line 24
write_scope:
  - skills/_shared/_run.cmd
  - skills/_shared/_run.sh
  - skills/PYTHON_PATH/src/resolve.ps1
  - skills/GIT/src/git_task.cmd
  - skills/SEARCH/SKILL.md
acceptance_criteria:
  - "grep -c 'H:\\\\all-languages-env.cmd' skills/_shared/_run.cmd → >= 1 AND the call is inside an if exist guard (probe kept verbatim, guarded)"
  - "grep -c 'venv%%V' skills/_shared/_run.cmd → unchanged vs HEAD~ (H:\\venv scan loop untouched)"
  - "S-B simulation of a post-bootstrap crash: _PY_SCRIPT=<tmp script that sys.exit(3)> bash skills/_shared/_run.sh --args-file <tmp args with out_file> → shell exit code 0 AND out_file's last line is EXIT_CODE=3"
  - "S-B simulation of bootstrap death: point _run.sh at a nonexistent interpreter env; run with --args-file <af> → <af>.fail exists and names the failure"
  - "tail -3 skills/_shared/_run.cmd | grep -c 'exit /b 0' → 1 (T9 preserved); tail -3 skills/_shared/_run.sh | grep -c 'exit 0' → 1"
  - "grep -c 'H:/ml-vol-estimator' skills/GIT/src/git_task.cmd → 0 (now %~dp0noop_editor.cmd)"
  - "grep -c 'H:\\\\venv311' skills/SEARCH/SKILL.md → 0"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "do NOT remove or reorder the H:\\venv315..38 scan (AW-G11 do-NOT; lint_vscode_tasks W1/W6 mandate the H: references); APPEND fallbacks after it"
  - "do NOT change nix_ld.sh (already guarded off-nix); do NOT change the final unconditional exit-0 lines (T9)"
  - "fallback chain order is the ledger's: user.json python_path → H:\\venv scan → %ROOT%\\src\\.venv\\Scripts\\python.exe → where python (in _run.cmd the H:\\venv scan stays FIRST-positioned as today; insert the user.json check before it, append 3/4 after it)"
context_summary: |
  AW-13: _run.cmd hard-fails off the GS box — `call H:\all-languages-env.cmd` is unguarded and the
  venv probe has no repo-local fallback (the .sh twin already falls back to src/.venv). AW-54: three
  divergent interpreter resolvers exist (PYTHON_PATH/resolve.*, _run.cmd, and now vol.cmd) — this task
  adopts the same 4-step order vol.cmd (wfo-03-2) uses, killing the divergence. AW-41: _run.{cmd,sh}
  swallow every failure behind exit 0 — the fix writes diagnostics INTO the sentinel channel (out_file
  or <args-file>.fail), never changes the exit code. Task 8's lint update and memory/ref/vscode-tasks.md
  (Task 6) document the .fail convention.
depends_on: []
```

- [ ] **Step 1 (red):** on S-B run the two simulations from the acceptance criteria against HEAD: post-bootstrap crash → out_file has NO `EXIT_CODE=` line and shell exits 0 (failure invisible — AW-41 verbatim); bootstrap death → no `.fail` file. Paste both.
- [ ] **Step 2 (implement `_run.cmd`):** bounded edit script (the file is 66 lines; mirror its comment style):
  1. Line ~27: `call H:\all-languages-env.cmd >nul 2>&1` → `if exist H:\all-languages-env.cmd call H:\all-languages-env.cmd >nul 2>&1`.
  2. Before the venv scan, insert resolution step 1 (user.json), reusing the exact PowerShell one-liner from `vol.cmd` (Task 2 Step 2, resolution block) with `%~dp0..\..\..` as ROOT: derive `set "_R=%~dp0..\..\.."` then test `"%_R%\workspace\config\user.json"`.
  3. After the `if not defined PY (...)` H:-scan failure block — replace the hard `exit /b 1` there with the appended fallbacks: `if not defined PY if exist "%_R%\src\.venv\Scripts\python.exe" set "PY=%_R%\src\.venv\Scripts\python.exe"`, then the `where python` loop from `vol.cmd`, and only if still undefined: emit the diagnostic AND write the bootstrap sentinel before `exit /b 1`:

     ```bat
     if not defined PY (
         echo ERROR: No Python found. Checked: user.json python_path, H:\venv*, src\.venv, PATH. >&2
         call :_findaf %*
         if defined _AF echo BOOTSTRAP_FAIL: no Python interpreter (user.json, H:\venv*, src\.venv, PATH all empty)> "%_AF%.fail"
         exit /b 1
     )
     ```

     (`:_findaf` already exists at the file's tail; it is safe to call early.)
  4. After `set "_EC=%ERRORLEVEL%"` (line ~55), before `log_usage`, add the AW-41 post-crash guard:

     ```bat
     if not "%_EC%"=="0" if defined _AF (
         "%PY%" -c "import json,sys,os;a=json.load(open(sys.argv[1]));f=a.get('out_file') or a.get('output_json');f and (open(f,'a',encoding='utf-8').write('\nEXIT_CODE=%_EC%\n') if not (os.path.isfile(f) and 'EXIT_CODE=' in open(f,encoding='utf-8').read()) else None)" "%_AF%" 2>nul
     )
     ```
  5. Leave lines from `call "%~dp0log_usage.cmd"` to `exit /b 0` untouched.
- [ ] **Step 3 (implement `_run.sh`):** bounded edit script (bash-side twin of Step 2; reuse the file's existing `ROOT` and its final `exit 0`, mirror its comment style):
  1. No env-guard edit — `_run.sh` never calls `H:\all-languages-env.cmd` (the `.sh` twin is nix/Linux; `nix_ld.sh` is already guarded and is do-not-touch). Step 2's edit 1 has no bash counterpart.
  2. Before the existing `${ROOT}/src/.venv/bin/python` resolution, insert resolution step 1 (user.json `python_path`) — an interpreter-free `sed` extraction standing in for `_run.cmd`'s PowerShell one-liner (no interpreter is resolved yet):

     ```bash
     # ---- Interpreter resolution step 1: workspace/config/user.json python_path ----
     _UJSON="${ROOT}/workspace/config/user.json"
     if [ -z "${PY:-}" ] && [ -f "${_UJSON}" ]; then
         _CAND="$(sed -n 's/.*"python_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${_UJSON}" | head -n1)"
         [ -n "${_CAND}" ] && [ -x "${_CAND}" ] && PY="${_CAND}"
     fi
     ```

     (The existing `${ROOT}/src/.venv/bin/python` block is resolution step 2 — leave it, still gated on `PY` unset.)
  3. After the `src/.venv` block, append resolution step 3 (`command -v` — the ledger's last step) and, only if still unresolved, write the bootstrap sentinel before the existing `exit 1`:

     ```bash
     # ---- Interpreter resolution step 3: python3 / python on PATH ----
     [ -z "${PY:-}" ] && PY="$(command -v python3 || command -v python || true)"
     if [ -z "${PY:-}" ]; then
         echo "ERROR: No Python found. Checked: user.json python_path, ${ROOT}/src/.venv, PATH." >&2
         [ -n "${_AF:-}" ] && printf 'BOOTSTRAP_FAIL: no Python interpreter (user.json, src/.venv, PATH all empty)\n' > "${_AF}.fail"
         exit 1
     fi
     ```

     (`_AF` is the args-file path the file already resolves from `"$@"` — the bash counterpart of `:_findaf`; if the live file names it differently, bind to that variable and note the delta.)
  4. Immediately after the target runs, capture its code (`_EC="$?"`, the twin of Step 2's `set "_EC=%ERRORLEVEL%"`); before the final `exit 0`, add the AW-41 post-crash guard — if it is non-zero and the args-file's `out_file` has no `EXIT_CODE=` line yet, append one:

     ```bash
     if [ "${_EC:-0}" -ne 0 ] && [ -n "${_AF:-}" ]; then
         _OF="$(sed -n 's/.*"out_file"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${_AF}" 2>/dev/null | head -n1)"
         if [ -n "${_OF}" ] && [ -f "${_OF}" ] && ! grep -q '^EXIT_CODE=' "${_OF}"; then
             printf 'EXIT_CODE=%s\n' "${_EC}" >> "${_OF}"
         fi
     fi
     ```
  5. Leave the log-usage tail through the final unconditional `exit 0` (line ~90) untouched (T9).
- [ ] **Step 4 (stragglers):** `git_task.cmd:24` → `set "GIT_EDITOR=%~dp0noop_editor.cmd"` (co-located per AW-13); `resolve.ps1` → after the `H:\venv311` fallback add `if (-not (Test-Path $fallback)) { $cmd = Get-Command python -ErrorAction SilentlyContinue; if ($cmd) { $fallback = $cmd.Source } }` mirroring `resolve.py::_find_python_windows`; `skills/SEARCH/SKILL.md:60` → replace the `H:\venv311\Scripts\python.exe` literal with "the interpreter resolved by the standard order (user.json `python_path` → `H:\venv*` → `src\.venv` → PATH — see `memory/ref/vscode-tasks.md`)".
- [ ] **Step 5 (run to green):** re-run both simulations (now: `EXIT_CODE=3` appended; `.fail` written) + the five grep criteria. Paste.
- [ ] **Step 6 (commit):** `chore(framework): harden _run bootstrap with repo-local fallback and failure sentinel`

### Task 6: One args-file contract — SKILL.mds, prompts, and rule E3

**Files:** Modify — `skills/GIT/SKILL.md`, `skills/GIT_COMMIT/SKILL.md`, `skills/SLANG_LINT/SKILL.md`, `skills/SLANG_TEST_COVERAGE/SKILL.md`, `skills/SLANG_REVIEW/SKILL.md`, `.github/prompts/slang-review.prompt.md`, `.github/prompts/lint-workspace.prompt.md`, `memory/ref/vscode-tasks.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-6"
goal: "Every SKILL.md/prompt args-file filename matches its task definition verbatim, run_id lives inside the JSON body constrained to [a-z0-9-]+, create_and_run_task is retired everywhere including vscode-tasks.md rule E3, and the last-writer-wins caveat is stated."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md
  - skills/GIT/SKILL.md                       # :29 git_args_{run_id}.json vs task def git_args.json
  - skills/GIT_COMMIT/SKILL.md                # :37 git_commit_args_{run_id}.json vs git_commit_args.json
  - skills/SLANG_LINT/SKILL.md                # :107-131 create_and_run_task + {run_id} filenames
  - skills/SLANG_TEST_COVERAGE/SKILL.md       # :33 epssp_coverage_args.json vs slang_test_coverage_args.json
  - skills/SLANG_REVIEW/SKILL.md              # :149/:163/:241 create_and_run_task + polling notes
  - .github/prompts/slang-review.prompt.md    # :29-31 wrong args filename + poll target
  - .github/prompts/lint-workspace.prompt.md  # :16 lint_args_{run_id}.json vs lint_args.json
  - memory/ref/vscode-tasks.md                # :96 rule E3 endorses create_and_run_task
  - ml-vol-estimator.code-workspace           # READ-ONLY: the authoritative --args-file values (:59,:68,:94,:102,:198)
write_scope:
  - skills/GIT/SKILL.md
  - skills/GIT_COMMIT/SKILL.md
  - skills/SLANG_LINT/SKILL.md
  - skills/SLANG_TEST_COVERAGE/SKILL.md
  - skills/SLANG_REVIEW/SKILL.md
  - .github/prompts/slang-review.prompt.md
  - .github/prompts/lint-workspace.prompt.md
  - memory/ref/vscode-tasks.md
acceptance_criteria:
  - "grep -rn 'create_and_run_task' skills/ .github/ memory/ policy/ workflows/ → 0 hits"
  - "grep -c 'args_{run_id}.json\\|args_{run_id}\\.json' skills/GIT/SKILL.md skills/GIT_COMMIT/SKILL.md skills/SLANG_LINT/SKILL.md .github/prompts/lint-workspace.prompt.md → 0 each"
  - "grep -c 'workspace/tmp/git_args.json' skills/GIT/SKILL.md → >= 1; grep -c 'workspace/tmp/slang_test_coverage_args.json' skills/SLANG_TEST_COVERAGE/SKILL.md → >= 1"
  - "grep -c 'slang_lint_args.json' .github/prompts/slang-review.prompt.md → >= 1 (was lint_args.json)"
  - "grep -c '\\[a-z0-9-\\]' skills/GIT/SKILL.md skills/GIT_COMMIT/SKILL.md skills/SLANG_LINT/SKILL.md skills/SLANG_REVIEW/SKILL.md → >= 1 each (run_id constraint stated)"
  - "grep -c 'last writer wins\\|last-writer-wins' skills/GIT/SKILL.md skills/GIT_COMMIT/SKILL.md skills/SLANG_LINT/SKILL.md skills/SLANG_TEST_COVERAGE/SKILL.md → >= 1 each"
  - "grep -n 'E3' memory/ref/vscode-tasks.md → row present, text says stop-and-ask, no create_and_run_task"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "docs-only task (Rule-5 exempt); do NOT touch the SLANG SKILL.md powershell fences (Task 7 owns those lines) or task definitions (Task 8 owns the registries)"
  - "the fixed filename for each task is the LITERAL --args-file value in its task definition — copy it, do not apply a naming convention retroactively"
context_summary: |
  AW-04 (BLOCKER): SKILL.mds/prompts document {run_id}-suffixed args filenames while the task
  definitions read fixed paths — following the docs makes run_task read an absent file or replay a
  stale one. AW-09: create_and_run_task is a permission-gate bypass and rule E3 in
  memory/ref/vscode-tasks.md still endorses it. Resolution (already decided — do not relitigate):
  fixed args-file path per the task definition; run_id INSIDE the JSON body ([a-z0-9-]+) — safe because
  lint.py:498 reads run_id from the body and :514-517 still derives slang_lint_results_{run_id}.json,
  keeping result files collision-free. The caveat that fixed args files reintroduce last-writer-wins
  between concurrent agents must be stated (GIT/SKILL.md:29 currently promises collision avoidance).
  Plan 04's lint_args_contract.py will enforce doc↔task-def parity mechanically.
depends_on: []
```

- [ ] **Step 1 (red):** run the first two acceptance greps against HEAD; paste the nonzero hits (`create_and_run_task` in SLANG_LINT:99/122, SLANG_REVIEW:149/163, vscode-tasks.md:96; `{run_id}` filenames in GIT:29, GIT_COMMIT:37, SLANG_LINT:119, lint-workspace.prompt.md:16).
- [ ] **Step 2 (implement):** file-by-file (all quoted filenames verified against the task registry 2026-07-07):
  - **`skills/GIT/SKILL.md`** (:29 and every echo): args file is `workspace/tmp/git_args.json` (fixed); add `"run_id"` as an optional JSON body field, pattern `[a-z0-9-]+`, used only to uniquify `out_file` (e.g. `workspace/tmp/git_out_{run_id}.txt`); replace the "unique run_id slug to avoid collisions" promise with the last-writer-wins caveat sentence (Task 4 Step 3d wording).
  - **`skills/GIT_COMMIT/SKILL.md`** (:37): same treatment, filename `workspace/tmp/git_commit_args.json`.
  - **`skills/SLANG_LINT/SKILL.md`** (:107-131 + table :157): filename `workspace/tmp/slang_lint_args.json`; `run_id` moves inside the body (`"run_id": "smm-metrics-20260429"` example kept, constrained `[a-z0-9-]+`); note the script derives `slang_lint_results_{run_id}.json` from the body (`lint.py:498, :514-517`); replace both `create_and_run_task` blocks with `run_task("lint-slang")` (the label the table row :157 already names); delete the ad-hoc task-definition JSON example (:124-131).
  - **`skills/SLANG_TEST_COVERAGE/SKILL.md`** (:33): `epssp_coverage_args.json` → `workspace/tmp/slang_test_coverage_args.json` (task def ws:198); caveat sentence added.
  - **`skills/SLANG_REVIEW/SKILL.md`** (:149, :163): `create_and_run_task` → `run_task("slang-review")` (matching :117); delete/reword the :241 and :247 60-second-polling notes (run_task blocks — vscode-tasks.md E7); add the run_id body constraint.
  - **`.github/prompts/slang-review.prompt.md`** (:29-31): `lint_args.json` → `slang_lint_args.json`; poll target → "`workspace/tmp/slang_lint_results_{run_id}.json`, where `{run_id}` is the `run_id` field you wrote inside `slang_lint_args.json` (omit `run_id` → `slang_lint_results.json`)".
  - **`.github/prompts/lint-workspace.prompt.md`** (:16): `lint_args_{run_id}.json` → `workspace/tmp/lint_args.json` (task def ws:59); the ":56 never use create_and_run_task" line stays.
  - **`memory/ref/vscode-tasks.md`** (:96): rule E3 → `| E3 | If run_task cannot find a predefined task label, STOP and ask the user — never create_and_run_task (retired 2026-07: permission-gate bypass, AW-09) | Task labels live in .vscode/tasks.json (tracked) |`. Add two protocol rows: the fixed-path args-file contract (+ run_id-in-body `[a-z0-9-]+` + last-writer-wins caveat) and the `<args-file>.fail` bootstrap-failure sentinel from Task 5 ("on a missing out_file, check `<args-file>.fail`").
- [ ] **Step 3 (green):** run all seven acceptance greps; paste zeros/hits as specified.
- [ ] **Step 4 (commit):** `chore(framework): unify task args-file contract, retire create_and_run_task`

### Task 7: One KILL_ORPHANS engine + fix the 5 cmd-in-powershell fences

**Files:** Modify — `skills/KILL_ORPHANS/SKILL.md`, `skills/KILL_ORPHANS/src/cleanup.py`, `.github/prompts/kill-orphans.prompt.md`, `skills/{SLANG_GLIMPSE,SLANG_LINT,SLANG_REGTEST_FIX,SLANG_REVIEW,SLANG_REVIEW_INSPECT}/SKILL.md`. Create — `src/tests/unit/test_kill_orphans_out.py`. Delete — `skills/KILL_ORPHANS/src/cleanup.ps1`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-7"
goal: "cleanup.py is the single kill engine (cleanup.ps1 deleted, prompt routed through run_task, --out-file sentinel TDD-first, CIM fallback for wmic), and the five powershell-fenced ^-continuation blocks are re-fenced as cmd."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md
  - skills/KILL_ORPHANS/SKILL.md              # :21 Tool=cleanup.py; :78-96 Troubleshooting pasted 3x
  - skills/KILL_ORPHANS/src/cleanup.py        # main() at :216; wmic at :53
  - skills/KILL_ORPHANS/src/cleanup.ps1       # to delete (divergent second engine)
  - .github/prompts/kill-orphans.prompt.md    # :15 raw '& cleanup.ps1 -DryRun'
  - src/volforecast/utils/paths.py            # read-only: resolve_project_root for the test loader
write_scope:
  - skills/KILL_ORPHANS/SKILL.md
  - skills/KILL_ORPHANS/src/cleanup.py
  - skills/KILL_ORPHANS/src/cleanup.ps1
  - .github/prompts/kill-orphans.prompt.md
  - src/tests/unit/test_kill_orphans_out.py
  - skills/SLANG_GLIMPSE/SKILL.md
  - skills/SLANG_LINT/SKILL.md
  - skills/SLANG_REGTEST_FIX/SKILL.md
  - skills/SLANG_REVIEW/SKILL.md
  - skills/SLANG_REVIEW_INSPECT/SKILL.md
acceptance_criteria:
  - "./vol test -k test_kill_orphans_out → 2 passed (red shown first: TypeError/SystemExit — main() takes no argv / no --out-file flag)"
  - "ls skills/KILL_ORPHANS/src/cleanup.ps1 → No such file"
  - "grep -c 'cleanup.ps1' .github/prompts/kill-orphans.prompt.md skills/KILL_ORPHANS/SKILL.md → 0 each; grep -c 'run_task' .github/prompts/kill-orphans.prompt.md → >= 2 (dry-run + force)"
  - "grep -c '## Troubleshooting' skills/KILL_ORPHANS/SKILL.md → 1 (was 3 identical copies)"
  - "for f in SLANG_GLIMPSE SLANG_LINT SLANG_REGTEST_FIX SLANG_REVIEW SLANG_REVIEW_INSPECT; do awk '/```powershell/,/```/' skills/$f/SKILL.md | grep -c ' \\^$'; done → 0 for each (every ^-continuation block now fenced ```cmd)"
  - "S-B: ./vol exec python skills/KILL_ORPHANS/src/cleanup.py --dry-run → sentinel EXIT_CODE=0 (Linux /proc path still works)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "TDD failing-first for the cleanup.py change (Python code, Rule 5)"
  - "do NOT touch the args-file sections of SLANG_LINT/SLANG_REVIEW SKILL.mds (Task 6 owns them — this task changes ONLY code-fence language markers and, in KILL_ORPHANS, the named sections)"
  - "do not edit task definitions (Task 8 adds --dry-run/--out-file args and the kill-orphans-force label)"
  - "kill heuristics in cleanup.py are unchanged — only argv plumbing (--out-file), the wmic fallback, and dead-code removal"
context_summary: |
  AW-36: two divergent process-killer engines (cleanup.py 15.9KB via the task; cleanup.ps1 9.2KB via
  the slash prompt's raw PowerShell) must be hand-synced for a DESTRUCTIVE op, and the prompt path
  bypasses the no-raw-terminal doctrine; SKILL.md pastes its Troubleshooting table 3x; wmic is removed
  in Win11 24H2+. AW-46: five SLANG SKILL.mds fence cmd-only ^ continuations as ```powershell — copied
  into PowerShell they execute a broken split command. Decision (made): cleanup.py wins; the task
  gets --dry-run + --out-file defaults and a kill-orphans-force sibling in Task 8; output goes to a
  sentinel file because close:true disposes the terminal. The kill-orphans task wrapper already routes
  through _shared/_run.cmd — no wrapper change needed.
depends_on: []
```

- [ ] **Step 1 (write the failing test):** create `src/tests/unit/test_kill_orphans_out.py`:

  ```python
  """cleanup.py --out-file sentinel (Plan 03 wfo-03-7, AW-36)."""

  from __future__ import annotations

  import importlib.util
  from pathlib import Path

  from volforecast.utils.paths import resolve_project_root


  def _load_cleanup():
      path = resolve_project_root() / "skills" / "KILL_ORPHANS" / "src" / "cleanup.py"
      spec = importlib.util.spec_from_file_location("ko_cleanup", path)
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      return mod


  def test_dry_run_with_out_file_writes_sentinel(tmp_path: Path) -> None:
      mod = _load_cleanup()
      out = tmp_path / "kill_orphans_out.txt"
      rc = mod.main(["--dry-run", "--out-file", str(out)])
      assert rc == 0
      text = out.read_text(encoding="utf-8")
      assert text.rstrip().splitlines()[-1] == "EXIT_CODE=0"
      assert "dry" in text.lower() or "would kill" in text.lower() or "no orphan" in text.lower()


  def test_main_still_runs_without_out_file(capsys) -> None:
      mod = _load_cleanup()
      assert mod.main(["--dry-run"]) == 0
      assert capsys.readouterr().out  # summary still printed to console
  ```

- [ ] **Step 2 (run to confirm red):** `./vol test -k test_kill_orphans_out` → failures (`main()` takes 0 args / argparse rejects `--out-file`). Paste.
- [ ] **Step 3 (implement):**
  - `cleanup.py`: change `def main():` (line ~216) to `def main(argv: list[str] | None = None) -> int:`; `parser.parse_args(argv)`; add `parser.add_argument("--out-file", default=None, help="Mirror the summary into this file, ending with EXIT_CODE=<rc>")`; collect the existing printed summary into a list while still printing; at the end, if `--out-file` given, write the summary + `\nEXIT_CODE={rc}\n`; `return rc` (0 on success); `if __name__ == "__main__": sys.exit(main())`. For wmic (line ~53): wrap the `subprocess` call in `try/except FileNotFoundError` and fall back to `powershell -NoProfile -Command "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,WorkingSetSize | ConvertTo-Csv -NoTypeInformation"` parsed to the same `{pid: (ppid, name, mem)}` dict. Linux `/proc` path untouched.
  - `git rm skills/KILL_ORPHANS/src/cleanup.ps1`.
  - `kill-orphans.prompt.md`: replace the `& "skills/KILL_ORPHANS/src/cleanup.ps1" -DryRun` block (and its kill sibling) with: 1. `run_task("kill-orphans")` (task defaults to `--dry-run`, results in `workspace/tmp/kill_orphans_out.txt`); 2. show the user the dry-run summary and STOP for confirmation; 3. only on explicit confirmation `run_task("kill-orphans-force")`. Note the labels land in `.vscode/tasks.json` (this MR, Task 8).
  - `KILL_ORPHANS/SKILL.md`: delete two of the three identical Troubleshooting tables (:78-96); update the Identity table (`Tool` row stays `cleanup.py`; `Inputs` row → `--dry-run (default via task), --out-file`); document the two task labels and the sentinel out-file.
  - The five SLANG SKILL.mds: change ONLY the fence language of every ```` ```powershell ```` block whose body uses trailing `^` continuations (SLANG_GLIMPSE:45, SLANG_LINT:36, SLANG_REGTEST_FIX:42/58/98, SLANG_REVIEW:43/55/92, SLANG_REVIEW_INSPECT:36 — re-verify each block actually contains `^` before switching) to ```` ```cmd ````. Bodies byte-identical.
- [ ] **Step 4 (run to green):** all six acceptance commands; paste.
- [ ] **Step 5 (commit):** `chore(framework): single kill-orphans engine with sentinel out-file; fix cmd fences`

### Task 8: Tracked `.vscode/tasks.json` + `vol-*` tasks + divergence lint

**Files:** Create — `.vscode/tasks.json`. Modify — `ml-vol-estimator.code-workspace`, `workspace/lint/lint_vscode_tasks.py`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-8"
goal: ".vscode/tasks.json exists carrying all 45 task objects (41 mirrored + kill-orphans-force + vol-test/vol-lint/vol-typecheck), the .code-workspace tasks array matches it exactly, and lint_vscode_tasks.py reads tasks.json as primary with a divergence check — python workspace/lint/lint_vscode_tasks.py exits 0."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md   # carries the new task objects + lint code
  - ml-vol-estimator.code-workspace          # tasks.tasks array (43 objects at :41-390 pre-plan)
  - workspace/lint/lint_vscode_tasks.py      # load_workspace_tasks :48-55; T1-T8 :58-110; arch classifier :135-147
  - .vscode/settings.json                    # read-only: the only current .vscode file
write_scope:
  - .vscode/tasks.json
  - ml-vol-estimator.code-workspace
  - workspace/lint/lint_vscode_tasks.py
acceptance_criteria:
  - "python workspace/lint/lint_vscode_tasks.py → exit 0 (run on S-B via ./vol exec, or S-A via vol.cmd exec)"
  - "python -c \"import json; t=json.load(open('.vscode/tasks.json'))['tasks']; print(len(t))\" → 45"
  - "deliberate divergence probe: temporarily change one label in the .code-workspace copy → lint exits 1 naming rule V1 and the label; revert → exit 0 (paste both runs)"
  - "labels notebook and research absent from both files; labels vol-test, vol-lint, vol-typecheck, kill-orphans-force present in both"
  - "kill-orphans task args == ['--dry-run','--out-file','workspace/tmp/kill_orphans_out.txt']; kill-orphans-force args == ['--out-file','workspace/tmp/kill_orphans_out.txt']"
  - "S-A: run_task('vol-test') from Copilot Chat → sentinel OUTPUT_FILE ends EXIT_CODE=0  [S-B fallback: tag S-A-DEFERRED per §9 and verify ./vol test green instead]"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "mirror the 41 surviving objects byte-faithfully (keys, ordering, presentation blocks); do not 'normalize' paths or labels"
  - "never rewrite the existing T1-T8/W/B/P check logic (do-not-rebuild #7) — only load_workspace_tasks(), a new V1 check, and the narrow T5 exemption below"
  - "post-open task keeps its runOptions.runOn folderOpen block verbatim"
context_summary: |
  AW-G10: all 43 run_task labels live only inside ml-vol-estimator.code-workspace, invisible to
  folder-open sessions; the audit's fix is a tracked .vscode/tasks.json. Decision (made, judge 2):
  tasks.json lands unconditionally regardless of Gate B; both copies are kept and a lint divergence
  check (not a pointer comment) prevents drift. Task 4 deleted the notebook/research wrappers (their
  task objects go here too: 43→41); Task 7 decided kill-orphans defaults to --dry-run with a
  kill-orphans-force sibling; Task 2 shipped vol.cmd for the windows side of the three new vol-*
  tasks. AGENTS.md (Plan 02) already mandates run_task for vol commands — these tasks make that
  mandate satisfiable (AW-G10's necessary-but-not-sufficient caveat is honored: the vol-* tasks have
  per-OS commands, not just resolvable labels).
depends_on: ["wfo-03-2", "wfo-03-4", "wfo-03-7"]
```

- [ ] **Step 1 (red):** `python workspace/lint/lint_vscode_tasks.py` on HEAD → exit 0 (old world); `ls .vscode/tasks.json` → absent. Then note the four labels about to change (delete notebook/research; add 4). Paste.
- [ ] **Step 2 (build `.vscode/tasks.json`):** `{"version": "2.0.0", "tasks": [ ... ], "inputs": []}` where `tasks` = the 41 surviving objects copied verbatim from the `.code-workspace` `tasks.tasks` array (43 minus `notebook`, `research`), with these edits/additions:

  - `kill-orphans` object: `"args": ["--dry-run", "--out-file", "workspace/tmp/kill_orphans_out.txt"]`.
  - New object after it:

    ```json
    {
        "label": "kill-orphans-force",
        "type": "shell",
        "command": "skills/KILL_ORPHANS/src/kill_orphans_task.sh",
        "windows": { "command": "skills\\KILL_ORPHANS\\src\\kill_orphans_task.cmd" },
        "args": ["--out-file", "workspace/tmp/kill_orphans_out.txt"],
        "presentation": { "reveal": "always", "panel": "new", "close": true, "showReuseMessage": false }
    }
    ```
  - Three new CLI tasks (append before `post-open`):

    ```json
    {
        "label": "vol-test",
        "type": "shell",
        "command": "./vol",
        "windows": { "command": "vol.cmd" },
        "args": ["test", "-x", "-q"],
        "presentation": { "reveal": "always", "panel": "new", "close": true, "showReuseMessage": false }
    },
    {
        "label": "vol-lint",
        "type": "shell",
        "command": "./vol",
        "windows": { "command": "vol.cmd" },
        "args": ["lint"],
        "presentation": { "reveal": "always", "panel": "new", "close": true, "showReuseMessage": false }
    },
    {
        "label": "vol-typecheck",
        "type": "shell",
        "command": "./vol",
        "windows": { "command": "vol.cmd" },
        "args": ["typecheck"],
        "presentation": { "reveal": "always", "panel": "new", "close": true, "showReuseMessage": false }
    }
    ```

  Then replace the `.code-workspace` `tasks.tasks` array with the identical 45 objects (same order). All other `.code-workspace` content untouched.
- [ ] **Step 3 (extend the lint):** in `lint_vscode_tasks.py`:

  ```python
  TASKS_JSON = REPO_ROOT / ".vscode" / "tasks.json"

  def load_tasks_json() -> list[dict]:
      """Primary task source: tracked .vscode/tasks.json (Plan 03, AW-G10)."""
      if not TASKS_JSON.is_file():
          return []
      with open(TASKS_JSON, "r", encoding="utf-8") as f:
          return json.load(f).get("tasks", [])

  def check_divergence(primary: list[dict], mirror: list[dict]) -> list[str]:
      """V1: .vscode/tasks.json and the .code-workspace tasks array must be identical."""
      errors: list[str] = []
      p = {t.get("label"): t for t in primary}
      m = {t.get("label"): t for t in mirror}
      for label in sorted(set(p) | set(m)):
          if label not in p:
              errors.append(f"V1: task '{label}' only in ml-vol-estimator.code-workspace (add to .vscode/tasks.json)")
          elif label not in m:
              errors.append(f"V1: task '{label}' only in .vscode/tasks.json (mirror into ml-vol-estimator.code-workspace)")
          elif p[label] != m[label]:
              errors.append(f"V1: task '{label}' diverges between .vscode/tasks.json and the .code-workspace copy")
      return errors
  ```

  `main()` gains: `primary = load_tasks_json() or load_workspace_tasks()` for all existing checks (tasks.json primary), plus `errors += check_divergence(load_tasks_json(), load_workspace_tasks())` when both sources exist. T5 update ("args must use --args-file/--out-file"): exempt tasks whose `command` is `./vol`/`vol.cmd` (CLI passthrough tasks carry subcommand args by design) — implement as `T5_CLI_COMMANDS = {"./vol", "vol.cmd"}` checked before the existing assertion; `kill-orphans`/`kill-orphans-force` need no exemption (they now carry `--out-file`). Add both new functions to the module docstring's rule list (V1, T5 note).
- [ ] **Step 4 (green):** run the six acceptance criteria including the deliberate-divergence probe (change → red with V1 → revert → green); paste all.
- [ ] **Step 5 (commit):** `chore(framework): tracked .vscode/tasks.json with vol tasks and divergence lint`

### Task 9: Regenerate `memory/ref/vol-cli.md` from the help heredoc

**Files:** Modify — `memory/ref/vol-cli.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-03-9"
goal: "memory/ref/vol-cli.md documents all 34 ./vol commands (33 pre-existing + forecast) command-for-command with the help heredoc, plus the vol.cmd S-A subset note — closing the 19-of-33 'mirror' gap."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md
  - memory/ref/vol-cli.md          # current 19-command 'mirror'
  - vol                            # AUTHORITATIVE source: help heredoc vol:82-210 (post wfo-03-1)
  - vol.cmd                        # read-only: the S-A arm list for the new section
write_scope:
  - memory/ref/vol-cli.md
acceptance_criteria:
  - "for every case arm in vol (grep -oE '^\\s+[a-z-]+\\)' vol | tr -d ' )'), grep -q \"vol <arm>\" memory/ref/vol-cli.md → all 34 found, including test-all, notebook, ingest-ohlcv, ingest-ticks, ingest-iv, ingest-xasset, ingest-corr, ingest-micro, ingest-edrvs, kvar, cache-status, cache-clear, present, forecast, help"
  - "grep -c 'vol.cmd' memory/ref/vol-cli.md → >= 1 (S-A subset section present: test/test-all/testlf/lint/fmt/typecheck/exec/bg/jobs)"
  - "frontmatter updated: (updated: 2026-07-XX execution date) and the mirror claim now says 'mirrors ./vol help (34 commands; regenerated Plan 03; parity lint arrives in Plan 04)'"
  - "every table row's description is copied verbatim from the corresponding heredoc line (spot-check 5 rows against vol:82-210 in the return)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "keep the existing file's frontmatter schema (created/updated/tags/status/priority/relates) and table format — regenerate content, not structure (do-not-rebuild: INDEX table formats)"
  - "descriptions come from the heredoc, not from memory or invention; where the heredoc has sub-flag lines, fold the important flags into the row or a nested row exactly as the current file does for run"
context_summary: |
  AW-G6/G16/55: vol-cli.md claims to mirror ./vol help but omits 13-14 of 33 commands including the
  mandated pre-commit test-all and the whole tick/iv/micro ingest family; AW-G20's doc half: `present`
  is live CLI infra invisible to P1 docs. wfo-03-1 (merged) added `forecast`, making 34 arms. This
  file is P1 (INDEX.md:96, 'vol wrapper command lookup') — an agent that finds a command missing here
  concludes it does not exist. Plan 04 ships lint_vol_parity.py to lock heredoc↔doc parity; this task
  creates the state that lint will hold. Section order mirrors the heredoc: Core / Data & Ingestion /
  Experiment Management / Presentation / Environment, then a new 'Windows (S-A) subset — vol.cmd'
  section listing the 9 shim arms and the exit-2 rule for everything else.
depends_on: ["wfo-03-1"]
```

- [ ] **Step 1 (red):** `grep -c 'test-all\|ingest-iv\|kvar\|present\|forecast' memory/ref/vol-cli.md` → 0 on HEAD. Paste.
- [ ] **Step 2 (regenerate):** bounded recipe (the source of truth is in-repo — `vol:82-210` post-Task-1):
  1. Extract every command block from the help heredoc, in heredoc order (34 commands: help, run, test, test-all, testlf, lint, fmt, exec, bg, jobs, status, sync, notebook, shell, audit, refresh-ohlcv, ingest-edrvol, ingest-ohlcv, ingest-ticks, ingest-iv, ingest-xasset, ingest-corr, ingest-micro, ingest-edrvs, experiments, new-experiment, compare, kvar, backfill-rk, cache-status, cache-clear, present, forecast — plus the `help` arm itself).
  2. Rebuild the file's `| Command | Description |` tables, one table per `━━━` heredoc section, descriptions verbatim; keep the existing `run` row style for flag-heavy commands (main row + indented flag rows).
  3. Update frontmatter `updated:` to the execution date; line 13 becomes: `> This file mirrors \`./vol help\` (34 commands — regenerated 2026-07, Plan 03; \`lint_vol_parity.py\` enforces parity from Plan 04). If commands seem wrong or missing, run \`./vol help\` to validate.`
  4. Append the new section: `## Windows (S-A) subset — vol.cmd` — table of the 9 shim arms (test/test-all/testlf/lint/fmt/typecheck/exec/bg/jobs) + one line: "Every other command: `vol.cmd` exits 2 with `GS Coder workspace only — run via ./vol on S-B`."
  5. Note `sync`/`notebook` remain Linux-only (`vol notebook` routes to external jupyter — AW-G8's residual caveat stays as the existing description states it).
- [ ] **Step 3 (green):** run the arm-coverage loop from the acceptance criteria on S-B; paste the 34/34 result and the 5 spot-checked rows.
- [ ] **Step 4 (commit):** `docs(memory): regenerate vol-cli.md from vol help (34 commands incl. forecast)`

---

## 5. Configs / experiments

This plan ships **no runnable ML experiments and no YAML configs** — it never invokes `./vol run` and never touches `workspace/configs/` or `trials.yaml` (hard constraint in every packet). The only structured-data artifacts are `.vscode/tasks.json` (complete JSON in Task 8) and the args-file JSON examples embedded in Tasks 3, 4, 6, and 7. The smoke invocations in Task 4 deliberately use `["--help"]` argv so no training run is launched. Launch commands for real skill runs (e.g. `run_task("model-train")` with a champion config) are **documented in the SKILL.mds, never executed by any subagent in this plan**.

Hypothesis / expected-outcome / decision-rule for the plan as a whole (in lieu of experiment configs):

- **Hypothesis:** with `vol.cmd` + tracked tasks + repointed wrappers, an S-A Copilot Chat session can run test/lint/typecheck and all five ML-skill tasks with zero raw-terminal fallbacks.
- **Expected-outcome prior:** Gate D passes on first integration run on S-B; on S-A the exec/bg/help/exit-2 arms pass unconditionally, while the tool arms (pytest/ruff/mypy) carry the decision-record risk-2 probability of missing dev deps in `H:\venv*`.
- **Decision rule:** if any S-A tool-arm criterion fails for missing dependencies (not for script defects), apply the named fallback — verify that criterion on S-B, tag it `S-A-DEFERRED` in the MR, and file the dep-provisioning need as a Plan 04 precondition note. A script defect (wrong sentinel, wrong exit code) is a normal red → fix in-plan.

---

## 6. Findings disposed by this plan (coverage matrix slice)

AW-04 (Tasks 6, 8 — lint half in Plan 04) · AW-05 (Tasks 3, 4) · AW-09 (Task 6) · AW-13 (Tasks 4, 5) · AW-36 (Tasks 7, 8) · AW-41 (Task 5) · AW-46 (Task 7) · AW-54 (Tasks 2, 5) · AW-G6/G16/55 (Task 9) · AW-G7 (Task 1) · AW-G8 (Task 3 do-NOT honored; residual notebook caveat in Task 9) · AW-G10 (Task 8) · AW-G9-compute-half (Tasks 1, 2 — the scope-out half landed in Plan 02) · AW-G20-doc-half (Task 9).

---

## 7. Wave plan

Waves derive from `depends_on` + disjoint `write_scope`s (checked pairwise):

| Wave | Tasks (parallel) | Why disjoint |
|---|---|---|
| 1 | wfo-03-1 (`vol`) · wfo-03-2 (`vol.cmd`) · wfo-03-3 (`src/` CLI+stubs) · wfo-03-5 (`_run.{cmd,sh}` + stragglers) · wfo-03-6 (args-contract docs) | five non-overlapping file sets |
| 2 | wfo-03-4 (ML wrappers; needs 03-3's `economic_value.main`) · wfo-03-7 (KILL_ORPHANS + SLANG fences; deferred from wave 1 because 03-6 edits SLANG_LINT/SLANG_REVIEW SKILL.mds) · wfo-03-9 (vol-cli.md; needs 03-1's 34-arm heredoc) | wrapper dirs vs KILL_ORPHANS/SLANG-fence lines vs memory/ref |
| 3 | wfo-03-8 (task registries + lint; needs 03-2's vol.cmd, 03-4's deletions, 03-7's kill-orphans decision) | sole writer of `.code-workspace` / `.vscode/` / the lint script |

---

## 8. Orchestrator prompt

```
/execute Implement Plan 03 (Compute path works on both surfaces) from workspace/plans/copilot-workflow-overhaul/plan-03-compute-path.md

Precondition check: Plan 02 merged — grep -q "Supported Execution Surfaces" AGENTS.md (exit 0) and
git log --oneline -5 shows the chore/wf-overhaul-02-* merge. Also confirm no research /execute session
is live. Branch: chore/wf-overhaul-03-compute-path off master; rebase onto origin/master before push.
Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1 (parallel, max 5): wfo-03-1, wfo-03-2, wfo-03-3, wfo-03-5, wfo-03-6
  Wave 2 (parallel, max 3): wfo-03-4, wfo-03-7, wfo-03-9    # respect depends_on: 03-4←03-3, 03-9←03-1
  Wave 3: wfo-03-8                                          # depends_on 03-2, 03-4, 03-7
Each subagent: TDD where src/ Python is touched (show red, then green), terminal isolation
(./vol exec / vol.cmd exec, isBackground=true, read the OUTPUT_FILE= path), kill_terminal every
spawned terminal before returning, and return the 00-overview §5.2 return contract verbatim.
Retry a blocked/partial subagent once with a refined packet (add its diagnostics), then escalate
with both attempts' evidence.
Integration verification (orchestrator, after all tasks) — Gate D, tagged per-surface:
  [S-B] ./vol test            → green
  [S-B] ./vol forecast --help → exit 0
  [S-B] python workspace/lint/lint_vscode_tasks.py → exit 0
  [S-A] vol.cmd test -x -q    → OUTPUT_FILE sentinel with final line EXIT_CODE=0
  [S-A] run_task("lint-workspace") → out_file produced, gate result readable
  [S-A] ./vol (Git-Bash)      → exit 2, error names vol.cmd and VS Code tasks
  [either] grep -rn create_and_run_task skills/ .github/ memory/ policy/ workflows/ → 0
  If an S-A tool criterion fails on missing dev deps (not script defects): verify it on S-B and tag
  S-A-DEFERRED in the MR description, criterion by criterion (decision-record risk 2 fallback).
Paste all gate outputs into the MR description. MR title human-generic (no AW-IDs in the title).
Update workspace/research/weekly-progress.md (Shipped section, one line).
Do NOT start Plan 04.
```

---

## 9. Acceptance gate → Plan 04

**Gate D (00-overview §2, verbatim):** on S-A `vol.cmd test -x -q` and the lint-workspace task produce sentinel OUTPUT_FILEs with `EXIT_CODE=0`; on S-B `./vol test` green; `./vol` on Windows fails loudly naming the fallback. Plans 04–08 may now use these commands as acceptance criteria.

**Per-surface tagging (mandatory):** every criterion above is recorded in the MR as `[S-A]`, `[S-B]`, or `[S-A-DEFERRED → verified S-B]`. The deferral is legitimate ONLY for missing dev dependencies in `H:\venv*`/`src\.venv` (decision-record risk 2); a sentinel-protocol or exit-code defect is a red, not a deferral.

**Additional exit evidence for this plan:** `./vol test` includes the 10 new tests (4 economic-value CLI + 4 vf_entry + 2 kill-orphans) green; `lint_vscode_tasks.py` divergence probe shown red-then-green; `create_and_run_task` grep = 0; `memory/ref/vol-cli.md` arm-coverage loop 34/34.

**What Plan 04 consumes from here:** `vol.cmd exec` + the `lint-workspace`/`vol-*` tasks as its S-A execution vehicle; the `<args-file>.fail` + fixed-path args contract that `lint_args_contract.py` will enforce; `vf_entry.py`'s `_VF_MODULE` convention that `lint_wrapper_targets.py` must resolve; the regenerated `vol-cli.md` that `lint_vol_parity.py` locks against the heredoc; and the green `lint_vscode_tasks.py` baseline that Plan 04's "fix 3/15 then add new checks" work must not regress.

---

## 9a. Ledger deviations

The §3 **Produces** list is the interface ledger later plans consume; six of those rows diverge from a ledger default, a `./vol` precedent, or the original registry shape. They are enumerated here so downstream plans wire against the real contract rather than the assumed one — the `§9 deviation N` pointers in §3 (and in Task 2's design note) resolve to the numbered items below:

1. **Module-level `economic_value` CLI — not a `./vol` subcommand.** Unlike every other volforecast CLI, which registers as a subparser in `src/volforecast/__main__.py` (`register(subparsers)` / `set_defaults(func=…)`), the BACKTEST entry point is invoked as `python -m volforecast.evaluation.economic_value --args-file <json>` via a module-level `main(argv) -> int` — no `__main__.py` edit and no new `./vol` arm (Task 3 constraint; this matches the BACKTEST wrapper's pre-existing dotted path).
2. **`help` is a first-class `vol.cmd` arm and the no-arg default.** `vol.cmd` supports ten arms (`test test-all testlf lint fmt typecheck exec bg jobs help`); `help` exits 0 and is also what a bare `vol.cmd` (no subcommand) runs, whereas every non-dev-loop `./vol` arm on the shim exits 2 pointing at S-B (Task 2).
3. **Fixed args-file path = the literal task-definition value, not a retroactively applied naming convention.** For each existing task the `--args-file` path is the exact string already in its definition, copied verbatim; the `workspace/tmp/<label_with_dashes_as_underscores>_args.json` convention governs only NEW tasks. `run_id` moves INSIDE the JSON body (`[a-z0-9-]+`), and the fixed path reintroduces a last-writer-wins race that the SKILL.mds must state (Task 6).
4. **45-object task registries (was 43).** `.vscode/tasks.json` and the `.code-workspace` mirror each carry 45 task objects: the 41 survivors (43 pre-plan minus the deleted `notebook`/`research` per AW-05) plus `kill-orphans-force`, `vol-test`, `vol-lint`, and `vol-typecheck` (Task 8).
5. **`<args-file>.fail` bootstrap-failure sentinel.** Because `_run.{sh,cmd}` must keep their unconditional final `exit 0` (T9), a failure cannot surface through the exit code; instead a bootstrap death (no interpreter resolved) writes `<args-file>.fail` naming the cause, and a post-bootstrap crash appends `EXIT_CODE=<rc>` to the out_file — a new sentinel channel layered onto the original protocol (Task 5, AW-41).
6. **`vol.cmd jobs` classifies by sentinel presence, not `.pid` files.** cmd.exe has no `$$`/PID handle for a detached `start /b` process, so `vol.cmd jobs` reports RUNNING/DONE by whether a `.out` file already carries the `EXIT_CODE=` line, diverging from `./vol`'s `.pid`-file job tracking (Task 2 design note).
