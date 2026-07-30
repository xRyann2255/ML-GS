# Plan 04 — Lint Gate Real and Green

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §9.
> Dispatch each task as a subagent with the context packet provided. Max 5 concurrent subagents.
> TDD is a hard gate (copilot-instructions.md Critical Rule 5; per 00-overview §5.3 item 5, **new lint modules are code** and get real red-then-green — the recorded RED lint run IS the failing test). Requires Plans 01–03 merged and **Gate D passed** (S-A `vol.cmd test -x -q` + lint-workspace task produce `EXIT_CODE=0` sentinels; S-B `./vol test` green).

**Goal:** `python workspace/lint/lint_all.py` reports full PASS (15 existing + 6 new checks = 21) on both supported surfaces, every checker computes what it claims to compute, and a local pre-commit trigger provably rejects a planted violation — killing AW-21, AW-44, AW-G29, AW-G30 and landing the lint halves of AW-04, AW-12, AW-15, AW-20, AW-23, AW-47, AW-49, AW-55.

**Architecture:** Everything extends the existing seams: new checks are new `workspace/lint/lint_<name>.py` files appended as 5-tuples to the `LINTS` registry (`lint_all.py:57-156`) — the 15 existing scripts' check logic is never rewritten (do-not-rebuild #7; the two sanctioned exceptions are the ledger's "Plan 04 rewrites math" mandate for `lint_memory_priority.py`/`validate_memory.py`, and additive appended check functions in `lint_broken_refs.py`, `lint_vscode_tasks.py`, `design_lint.py`). Findings whose content fix lands in a LATER plan get an honest lint now plus a **narrow recorded grandfather whitelist** under `workspace/lint/whitelists/` that only shrinks — Plans 05/06/07 burn the entries down. The trigger reuses the repo's existing `.pre-commit-config.yaml` (a `repo: local` hook) plus the Gate-C CI home decided in Plan 02.

**Tech stack:** No new dependencies. All new lint checks are stdlib-only Python matching the existing suite (00-overview §3 item 7 / candidate-4 "New dependencies"). `vol.cmd`/`./vol` and the lint-workspace VS Code task (from Plan 03) are the execution vehicles.

**Research grounding:** Audit AW-21 + recon governance-map: the 15-check suite has **no automated trigger anywhere** and the tracked tree fails it 3/15 (design rules, broken refs, vscode md compat; 2.4 s runtime); `lint_memory_priority.py` "PASS" is structurally vacuous (sums hand-typed INDEX numbers — real P0 is ~4.2× its 800-token cap); three incompatible domain whitelists; inconsistent `_dormant` exemption across linters. **Expected-outcome prior (00-overview §4):** 3/15 failing → full PASS incl. new checks, trigger proven live by a planted violation. **Calibration warning:** if after the checker-fiction fixes the suite passes *without* needing the grandfather whitelists, the measurement is wrong — governance-map proves the honest math MUST go red on pre-Plan-06 content. A suspiciously easy green means a check is not actually measuring; investigate before celebrating.

---

## §1 Global constraints

All of 00-overview §5 (shared conventions) applies verbatim to every task. Plan-specific hard rules:

1. **AW-21 atomicity:** the three current 15-check failures are fixed in ONE task (wfo-04-1) and committed together — "Converting only AGENTS.md:58 leaves the gate red" (audit AW-21, verbatim). No partial-fix commit may land.
2. **Never rewrite the 15 existing check scripts' logic** (do-not-rebuild #7). Sanctioned modifications only: (a) `lint_memory_priority.py` + `validate_memory.py` budget MATH per the ledger row "Memory-budget fix"; (b) constants (`VALID_DOMAINS`, `VALID_MEMORY_DOMAINS`, `ALLOWED_ROOT_ENTRIES`, skip-sets); (c) additive appended check functions in `lint_broken_refs.py`, `lint_vscode_tasks.py`, `design_lint.py`. Existing check functions' bodies are otherwise untouched.
3. **`LINTS` appends serialize through exactly one task** (wfo-04-12), per 00-overview §7. No other task touches `lint_all.py`.
4. **Whitelist discipline:** every `workspace/lint/whitelists/*.txt` file carries a header naming the plan that burns it down and the rule "this list only shrinks — adding entries is forbidden". Entries are populated ONLY from a recorded RED run's output (pasted into the return contract), never invented.
5. **Red-then-green evidence is mandatory for every new/changed check:** paste both the RED run and the GREEN run into the task's return-contract `verification` field. For checks whose companion content-fix already landed (Plans 01–03), RED is demonstrated by a **planted violation** (edit → run → capture → `git checkout --` revert, all pre-commit). For checks red against pre-Plan-05/06/07 content, RED is the run with an empty whitelist.
6. **AW-49 boundary:** Plan 04 fixes ONLY the `AGENTS.md:58` link form (backtick). The session-handoff writer-or-delete decision belongs to Plan 05 — do not add a writer, do not delete the boot step.
7. Self-modification hazard (00-overview §1): the two AGENTS.md edits in this plan (wfo-04-1 line 58; wfo-04-13 one Environment line) quote the surrounding text as-of-execution; if it no longer matches, STOP and return `blocked` with the diff.
8. Standing packet constraints in every task: *"verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"* and *"the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"* (trials.yaml is READ/measured by wfo-04-2, never modified).
9. Commit prefixes (ledger §5.4, path-grouped): `chore(lint):` for `workspace/lint/**`, `chore(ci):` for `.github/**` and `.pre-commit-config.yaml`, `chore(framework):` for AGENTS.md/workflows, `docs(memory):` for `memory/**`.

## §2 File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `AGENTS.md` | line 58 backtick fix (wfo-04-1); one Environment line re pre-commit hooks (wfo-04-13) |
| Modify | `.github/prompts/gsvivs-audit.prompt.md` | line 155 repoint to `workspace/research/` (wfo-04-1) |
| Modify | `workspace/lint/design_lint.py` | `ALLOWED_ROOT_ENTRIES` (wfo-04-1); domain whitelist + `_dormant` skips (wfo-04-3); appended §4.9 dispatch check (wfo-04-11) |
| Modify | files reported by `lint_vscode_md.py` | mojibake/anchor/#file: fixes, `--fix` first (wfo-04-1) |
| Modify | `workspace/lint/lint_memory_priority.py` | measured bytes/4 P0/P1 budget math (wfo-04-2) |
| Modify | `workspace/lint/validate_memory.py` | budget sees workspace-resident P1 files; bytes/4; `research` cap; 10-domain whitelist; `dormant` status (wfo-04-2, wfo-04-3) |
| Modify | `workspace/lint/lint_memory_index_completeness.py` | extend rule G3 (already-registered INDEX→file existence check) to also resolve `src/`- and `.github/`-prefixed entries (wfo-04-2) |
| Create | `workspace/lint/whitelists/budget_grandfather.txt` | recorded over-budget files, burned down by Plan 06 (wfo-04-2) |
| Modify | `memory/design.md` (line 49) + `memory/meta/guide.md` | `research ≤300` cap line; documented `_dormant`/`dormant` convention (wfo-04-3) |
| Modify | `workspace/lint/lint_forbidden_patterns.py`, `workspace/lint/lint_doc_safety.py` | comment-only: documented deliberate scan-`_dormant` safety policy (wfo-04-3) |
| Create | `workspace/lint/lint_args_contract.py` | AW-04 lint half (wfo-04-4) |
| Create | `workspace/lint/lint_model_pins.py` + `workspace/lint/whitelists/model_pins.txt` | owns `EXPECTED_MODEL`; AW-23/G3 lint half (wfo-04-5) |
| Create | `workspace/lint/lint_wrapper_targets.py` | wrapper `_PY_SCRIPT`/module targets exist + parse (wfo-04-6) |
| Create | `workspace/lint/lint_vol_parity.py` | vol help ↔ vol-cli.md parity; AW-55 lint half (wfo-04-7) |
| Create | `workspace/lint/lint_prompts.py` + `workspace/lint/whitelists/prompts.txt` | prompt hygiene lint, consumed by Plan 07 (wfo-04-8) |
| Modify | `workspace/lint/lint_broken_refs.py` + Create `workspace/lint/whitelists/broken_refs.txt` | appended plain-text-path + `_dormant`-aware checks; AW-12 lint half (wfo-04-9) |
| Create | `workspace/lint/lint_canonical_schema.py` + `workspace/lint/whitelists/canonical_schema.txt` | AW-20/G23 lint half (wfo-04-10) |
| Modify | `workspace/lint/lint_vscode_tasks.py` | appended rule T9 exit-0 wrapper check (wfo-04-11) |
| Create | `workspace/lint/whitelists/dispatch_registration.txt` | AW-47 grandfather, burned by Plan 07 (wfo-04-11) |
| Modify | `workspace/lint/lint_all.py` | append exactly 6 `LINTS` tuples (wfo-04-12) |
| Modify | `.pre-commit-config.yaml` | local lint hook + re-pins + `files: ^src/` scoping (wfo-04-13) |
| Modify | `.gitlab-ci.yml` **or** `.github/workflows/ci.yml` (Gate-C winner from Plan 02) | server-side lint gate — GitLab: flip Plan 02's existing `workspace-lint` job `allow_failure`→`false` (no new job); ci.yml: add lint step (wfo-04-13) |

## §3 Interfaces

**Consumes (from the ledger / earlier plans):**
- `S-A`/`S-B` surface contract (Plan 02); Gate D evidence commands: S-A lint-workspace task → sentinel `OUTPUT_FILE=`/`EXIT_CODE=`; S-B `./vol exec`.
- Args-file contract (Plan 03): fixed path `workspace/tmp/<task-name>_args.json`, `run_id` inside the JSON body pattern `[a-z0-9-]+`, `create_and_run_task` retired everywhere incl. `memory/ref/vscode-tasks.md` rule E3.
- `vol.cmd` + `./vol` OS guard + `forecast` arm + regenerated `memory/ref/vol-cli.md` (Plan 03).
- `.vscode/tasks.json` tracked task source + extended `lint_vscode_tasks.py` (Plan 03).
- `LINTS` registry entry format: existing 5-tuple `(label, script_path: Path, extra_args: list, is_slow: bool, supports_fix: bool)` at `lint_all.py:57-156`.
- Gate C decision (Plan 02): CI home = GitLab job on the real remote vs `ci.yml` documented mirror-only.

**Produces (added to the ledger; later plans rely on):**
- `lint_args_contract.py`, `lint_model_pins.py` (owns `EXPECTED_MODEL = "Claude Opus 4.6"` — THE constant; all other surfaces point here — plus `SANCTIONED_SITES`, the frozenset of two canonical prose sites the lint skips entirely), `lint_wrapper_targets.py`, `lint_vol_parity.py`, `lint_prompts.py` — per ledger rows.
- `lint_canonical_schema.py` (NEW name, not in ledger — **ledger deviation, back-port required**).
- `workspace/lint/whitelists/` grandfather convention (**ledger deviation**): `budget_grandfather.txt` + missing-path grandfather (Plan 06 burns), `model_pins.txt` (Plans 05/07 burn), `prompts.txt` (Plan 07), `broken_refs.txt` (Plan 06), `canonical_schema.txt` (Plan 06), `dispatch_registration.txt` (Plan 07).
- Pre-commit local hook id `workspace-lint` (the planted-violation vehicle; Plans 05–08 inherit "lint stays green" as a standing gate).
- Rule `T9` in `lint_vscode_tasks.py`; check `skill-dispatch` (§4.9) in `design_lint.py`.

---

## §4 Wave A — make the existing 15 honest and green

## Task 1: Fix the 3/15 current failures — atomically (AW-21, AW-49 link half)

**Files:** Modify `AGENTS.md` (line 58), `.github/prompts/gsvivs-audit.prompt.md` (line 155), `workspace/lint/design_lint.py` (`ALLOWED_ROOT_ENTRIES` only), plus every file `lint_vscode_md.py` reports. One commit.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-1"
goal: "python workspace/lint/lint_all.py goes from FAILED (3/15) to ALL PASSED (15 checks) in one commit, with both runs pasted as evidence"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §4 Task 1
  - AGENTS.md
  - .github/prompts/gsvivs-audit.prompt.md
  - workspace/lint/design_lint.py
  - workspace/lint/lint_vscode_md.py
write_scope:
  - AGENTS.md
  - .github/prompts/gsvivs-audit.prompt.md
  - workspace/lint/design_lint.py
  - "<files reported by lint_vscode_md.py — list them in files_changed>"
acceptance_criteria:
  - "python workspace/lint/lint_all.py → 'ALL PASSED (15 checks' (run BEFORE fix must show 'FAILED (3/15): design rules, broken refs, vscode md compat' — paste both)"
  - "python workspace/lint/lint_broken_refs.py → exit 0"
  - "grep -c 'workspace/research/gsvivs_iv_improvement_plan.md' .github/prompts/gsvivs-audit.prompt.md → 1"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "AW-49 boundary: change ONLY the link form at AGENTS.md:58 — no session-handoff writer, no boot-step deletion (Plan 05 decides)"
  - "design_lint.py: touch ONLY the ALLOWED_ROOT_ENTRIES constant (lines ~107-123); no check-function bodies"
context_summary: |
  The 15-check suite currently fails 3/15 and the audit (AW-21) proves partial fixes leave it red,
  so all three failures land in this one task. The gsvivs target file EXISTS at
  workspace/research/gsvivs_iv_improvement_plan.md — the link just points at workspace/docs/.
  Later tasks in this plan add new checks on top of the green baseline this task creates.
depends_on: []
```

- [ ] **Step 1 (red):** Run `python workspace/lint/lint_all.py`. Expected: `FAILED (3/15): design rules, broken refs, vscode md compat`. Paste the full output — this is the recorded RED.
- [ ] **Step 2 (fix broken refs — both, per AW-21):**
      (a) `AGENTS.md:58` — change the Markdown link
      `4. Check for [workspace/tmp/session-handoff.md](workspace/tmp/session-handoff.md)` →
      `` 4. Check for `workspace/tmp/session-handoff.md` `` (backtick plain-code form; the target is a runtime-ephemeral file that never exists in a clean tree). Keep the rest of the sentence byte-identical.
      (b) `.github/prompts/gsvivs-audit.prompt.md:155` — replace `workspace/docs/gsvivs_iv_improvement_plan.md` with `workspace/research/gsvivs_iv_improvement_plan.md` (the file exists there — verify with `ls` first).
- [ ] **Step 3 (fix design rules):** In `workspace/lint/design_lint.py`, add to `ALLOWED_ROOT_ENTRIES` (lines ~107-123): `"docs",` (git-tracked `docs/superpowers/*` exists by design) and `".pre-commit-config.yaml",` — each with a trailing comment `# whitelisted wfo-04-1 (AW-21)`. Then re-run `python workspace/lint/design_lint.py`: if any OTHER root entry still errors, check it with `git ls-files <entry>` — untracked entries are local mirror artifacts (note them in `notes`, do not whitelist); tracked ones get whitelisted with the same comment and named in `files_changed`.
- [ ] **Step 4 (fix vscode md compat):** Run `python workspace/lint/lint_vscode_md.py --fix` (it is `supports_fix=True` in the registry), then re-run without `--fix` and hand-fix every residual error it reports (mojibake → correct UTF-8 text; broken `#file:` targets → repoint to the existing file located by content; bad anchors → correct heading slug). List every touched file in `files_changed`. The exact error list is determinable only at execution time — fallback: if an error cannot be fixed without a content decision (e.g., a `#file:` target that truly no longer exists anywhere), STOP and return `blocked` with the error line.
- [ ] **Step 5 (green):** `python workspace/lint/lint_all.py` → `ALL PASSED (15 checks, …)`. Paste output.
- [ ] **Step 6: Commit** — `chore(lint): green the 15-check gate — fix both broken refs, root whitelist, vscode-md errors`

## Task 2: Memory-budget math honesty — measure bytes, check paths (AW-15 lint half)

**Files:** Modify `workspace/lint/lint_memory_priority.py`, `workspace/lint/validate_memory.py` (budget MATH only), and `workspace/lint/lint_memory_index_completeness.py` (extend rule G3 to resolve `src/`- and `.github/`-prefixed INDEX entries — path existence stays G3's job). Create `workspace/lint/whitelists/budget_grandfather.txt`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-2"
goal: "lint_memory_priority.py and validate_memory.py compute P0/P1 budgets from measured file bytes/4 (incl. the 6 workspace-resident P1 files), going RED on honest math then GREEN via the recorded budget_grandfather.txt; SEPARATELY, lint_memory_index_completeness.py's already-registered rule G3 is extended to resolve src/- and .github/-prefixed INDEX entries so INDEX path-existence is checked for those too (no new path-existence check is added to lint_memory_priority.py)"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §4 Task 2
  - workspace/lint/lint_memory_priority.py
  - workspace/lint/validate_memory.py
  - workspace/lint/lint_memory_index_completeness.py
  - memory/INDEX.md
write_scope:
  - workspace/lint/lint_memory_priority.py
  - workspace/lint/validate_memory.py
  - workspace/lint/lint_memory_index_completeness.py
  - workspace/lint/whitelists/budget_grandfather.txt
acceptance_criteria:
  - "python workspace/lint/lint_memory_priority.py with empty grandfather → exit 1 with ERROR [p0-budget] naming measured totals (recorded RED)"
  - "python workspace/lint/lint_memory_priority.py with populated grandfather → exit 0, summary prints BOTH honest total and grandfathered residual"
  - "python workspace/lint/validate_memory.py → exit 0; its P0+P1 line now includes the workspace-resident files and says 'measured bytes/4'"
  - "temporarily renaming any INDEX-listed file path (incl. a src/- or .github/-prefixed one) → lint_memory_index_completeness.py's extended G3 exits 1 flagging the missing INDEX target (planted red for the existence check, reverted); lint_memory_priority.py itself no longer does path-existence"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; trials.yaml is READ for measurement only, never modified"
  - "in lint_memory_priority.py + validate_memory.py touch budget MATH only — do NOT touch check_reachability/is_referenced or validate_memory's frontmatter checks (ledger: 'Plan 04 rewrites math'); path-existence stays in lint_memory_index_completeness.py's rule G3, extended here for src/ + .github/ prefixes only (additive — G3's other logic byte-identical)"
  - "grandfather entries come ONLY from the red run's measured numbers; the file header forbids additions"
context_summary: |
  Today lint_memory_priority.py sums the hand-typed ~Tokens column (P0 'PASS' at 535 vs a real
  ~3,327 vs cap 800) and validate_memory.py globs only memory/**.md, blind to the 6 INDEX-listed
  P1 files under workspace/ (incl. 127KB trials.yaml). Plan 06 fixes the CONTENT (demotions,
  trims); this task fixes the MATH now and grandfathers the known offenders so the gate stays
  green without lying. The ledger row 'Memory-budget fix' sanctions rewriting these two scripts' math.
  INDEX path-existence is NOT re-implemented here: lint_memory_index_completeness.py's rule G3
  (~lines 88-101) already flags "INDEX lists a file that doesn't exist" and already resolves
  memory/- and workspace/-prefixed entries; this task only EXTENDS G3 to also resolve src/ and
  .github/ prefixes — the one registered path-existence check, new prefixes.
depends_on: []
```

- [ ] **Step 1: Write the grandfather file** at `workspace/lint/whitelists/budget_grandfather.txt` — start EMPTY apart from the header:

```text
# budget_grandfather.txt — GRANDFATHERED memory-budget entries.
# Burned down to empty by Plan 06 (wfo-06). This list only shrinks —
# adding entries is FORBIDDEN. Format: <repo-relative-path> <max_tokens>
# A grandfathered file is excluded from the P0/P1 totals but FAILS if it
# grows beyond its recorded ceiling.
```

- [ ] **Step 2: Implement the honest math.** In `lint_memory_priority.py`, replace the budget internals (keep the module structure, output style, and `check_reachability` untouched):

```python
import math

WHITELIST_DIR = Path(__file__).resolve().parent / "whitelists"

def load_grandfather() -> dict[str, int]:
    """Path -> max_tokens ceiling. Plan 06 burns this file down to empty."""
    gf: dict[str, int] = {}
    p = WHITELIST_DIR / "budget_grandfather.txt"
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            path_str, cap = line.rsplit(" ", 1)
            gf[path_str.strip()] = int(cap)
    return gf

def resolve_entry_path(repo_root: Path, index_path_str: str) -> Path:
    """INDEX paths are memory/-relative unless they start with workspace/."""
    if index_path_str.startswith(("workspace/", "src/", ".github/")):
        return repo_root / index_path_str
    return repo_root / "memory" / index_path_str

def measured_tokens(p: Path) -> int:
    """bytes/4, the suite-wide heuristic (ledger row 'Memory-budget fix')."""
    return math.ceil(p.stat().st_size / 4)

def check_p0_budget(entries, repo_root, grandfather) -> list[tuple[str, str, str]]:
    results = []
    p0 = [e for e in entries if e["priority"] == "P0"]
    measured, counted, gf_excess = {}, 0, []
    for e in p0:
        p = resolve_entry_path(repo_root, e["file"])
        if not p.is_file():
            continue  # missing files are reported by lint_memory_index_completeness.py G3
        t = measured_tokens(p)
        measured[e["file"]] = t
        if e["file"] in grandfather:
            if t > grandfather[e["file"]]:
                gf_excess.append((e["file"], t, grandfather[e["file"]]))
        else:
            counted += t
    honest_total = sum(measured.values())
    results.append(("INFO", "p0-budget",
        f"P0 measured (bytes/4): ~{honest_total} tokens across {len(p0)} files; "
        f"non-grandfathered ~{counted} vs cap {P0_TOKEN_CAP}."))
    if counted > P0_TOKEN_CAP:
        results.append(("ERROR", "p0-budget",
            f"Non-grandfathered P0 total ~{counted} exceeds cap {P0_TOKEN_CAP}: "
            + ", ".join(f"`{f}` (~{t})" for f, t in measured.items()
                        if f not in grandfather)))
    for f, t, cap in gf_excess:
        results.append(("ERROR", "p0-budget",
            f"Grandfathered `{f}` grew: measured ~{t} > recorded ceiling {cap}."))
    return results
```

Wire `main()` to pass `repo_root` and `load_grandfather()` into `check_p0_budget` (and the analogous P1 budget check), and add an `INFO` severity branch to the printer (print as `  INFO  [check] msg`, never affects exit code). Do NOT add a path-existence check here — that stays in `lint_memory_index_completeness.py`'s rule G3 (extended in Step 3a). The old typed-column sum may remain in the summary line as `claimed ~N` for the Plan-06 before/after record.
- [ ] **Step 3: Extend `validate_memory.py`'s budget** (its frontmatter/domain checks untouched): where it computes the P0+P1 / P2 budgets from `memory_dir.rglob("*.md")` line counts, (a) switch the token estimate to `math.ceil(bytes/4)`; (b) additionally iterate the INDEX priority map (`_load_priority_map`) and, for every entry resolving under `workspace/` (use the same `resolve_entry_path` logic — copy the ~8-line helper; the suite's scripts are deliberately self-contained), add its measured tokens to the matching priority bucket — including non-`.md` files such as `workspace/research/trials.yaml`; (c) subtract grandfathered files (read the same `whitelists/budget_grandfather.txt`) from the enforced totals, enforcing per-file ceilings exactly as in Step 2; (d) budget breach → ERROR (exit 1), matching design.md §7's declared ERROR severity for Rule 9. Print: `P0+P1 measured (bytes/4): ~<honest> tokens; enforced (non-grandfathered): ~<counted> (budget: 50000)`.
- [ ] **Step 3a: Extend rule G3** in `workspace/lint/lint_memory_index_completeness.py` (the existing "INDEX lists a file that doesn't exist" check, ~lines 88-101, which already resolves `memory/`- and `workspace/`-prefixed entries): add `src/` and `.github/` to the recognized path prefixes so those INDEX rows resolve to `repo_root / <entry>` (not `repo_root / memory / <entry>`) before the `.is_file()` existence test. Touch ONLY the prefix-resolution branch — additive, no other G3 logic (existing check functions byte-identical apart from the new prefixes). Re-run `python workspace/lint/lint_memory_index_completeness.py` → still exit 0 on the current tree (its `src/` + `.github/` INDEX targets exist). This is the sole home of INDEX path-existence; `lint_memory_priority.py` never re-implements it.
- [ ] **Step 4 (RED, recorded):** With the grandfather still empty, run both scripts. Expected: `lint_memory_priority.py` exits 1 with `ERROR [p0-budget]` (~3,327 measured vs 800) and `validate_memory.py` exits 1 with a P0+P1 total around ~111k vs 50000 (live numbers may drift — paste whatever the honest run says). **This is the failing test.** Paste both outputs.
- [ ] **Step 5 (populate grandfather → GREEN):** From the RED output, append these entries (ceilings = measured value from the red run rounded UP to the next 100; the values below are the 2026-07-07 recon measurements as a cross-check — if the live numbers differ, use the live ones and note the delta):

```text
memory/person/user.md 900
memory/research/project-state.md 2500
memory/research/lgbm-pooled-lessons.md 9500
workspace/docs/data-audit.md 9800
workspace/docs/user-manual.md 6500
memory/ref/python-tsdb.md 5600
memory/ref/python-chunk.md 3000
workspace/research/trials.yaml 31800
```

If the non-grandfathered P0+P1 residual still exceeds 50,000, add the minimal number of next-largest files from the red output and name each in the MR description. Re-run both scripts → exit 0. Paste outputs. (Dead INDEX rows are NOT a budget concern — they surface as `lint_memory_index_completeness.py` G3 errors, which Plan 06 clears by deleting the rows; do not grandfather them in `budget_grandfather.txt`.)
- [ ] **Step 6 (planted red for path existence — G3):** In a scratch edit, change one INDEX row's path to a nonexistent name, run `python workspace/lint/lint_memory_index_completeness.py` → its extended G3 exits 1 flagging the missing INDEX target, revert with `git checkout -- memory/INDEX.md`. Paste. (Path-existence is G3's job now, not `lint_memory_priority.py`'s.)
- [ ] **Step 7: Commit** — `chore(lint): memory budgets measure real bytes/4, see workspace P1 files, check INDEX paths`

## Task 3: One domain whitelist, one `_dormant` policy (governance-map Part 3)

**Files:** Modify `workspace/lint/validate_memory.py` (constants), `workspace/lint/design_lint.py` (constants + two skip-sets), `workspace/lint/lint_forbidden_patterns.py` + `workspace/lint/lint_doc_safety.py` (comments only), `memory/meta/guide.md`, `memory/design.md` (line 49).

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-3"
goal: "All linters use exactly meta/guide.md's 10 domains, research gains a documented 300-line soft cap, and every linter's _dormant handling follows one documented policy (schema/structure checks exempt; safety checks scan; dormant is a documented status)"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §4 Task 3
  - workspace/lint/validate_memory.py
  - workspace/lint/design_lint.py
  - memory/meta/guide.md
  - memory/design.md
write_scope:
  - workspace/lint/validate_memory.py
  - workspace/lint/design_lint.py
  - workspace/lint/lint_forbidden_patterns.py
  - workspace/lint/lint_doc_safety.py
  - memory/meta/guide.md
  - memory/design.md
acceptance_criteria:
  - "grep -c 'ops' workspace/lint/validate_memory.py inside VALID_DOMAINS → 0 (the 5 invented domains gone from both linters)"
  - "python workspace/lint/validate_memory.py → exit 0 and python workspace/lint/design_lint.py → exit 0 (no new errors from the narrowing)"
  - "python workspace/lint/design_lint.py --category structural no longer flags memory/_dormant/** for CoALA sections or INDEX coverage (was 37 files; paste before/after warning counts)"
  - "scratch dir memory/decision/ with a stub file passes both domain checks (planted GREEN for a guide.md-reserved domain, then removed); scratch memory/ops/ FAILS both (planted RED, then removed)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "constants and skip-sets only in the two linters — no check-function body rewrites; lint_forbidden_patterns/lint_doc_safety get COMMENTS only (their _dormant scanning is the deliberate policy)"
  - "guide.md/design.md edits are the ≤10-line documentation of what the lints enforce; per-file status flips of the 36 _dormant files are Plan 06's (AW-34)"
context_summary: |
  Three sources disagree on valid memory domains (guide.md 10, design_lint 12, validate_memory 15
  — five names invented, three reserved ones missing from design_lint) and four linters exempt
  _dormant while two scan it, undocumented anywhere. This task collapses everything onto
  meta/guide.md's 10 domains ('authoritative specification' by its own title) and writes the
  _dormant policy down where the lints and the spec both point at it. Runs after wfo-04-1
  (design_lint.py) and wfo-04-2 (validate_memory.py) to serialize writes to those files.
depends_on: ["wfo-04-1", "wfo-04-2"]
```

- [ ] **Step 1 (RED, recorded):** Create scratch `memory/decision/test-adr.md` with valid frontmatter (copy any active file's frontmatter block, set `status: draft`). Run `python workspace/lint/design_lint.py` → expect `ERROR "Unrecognized memory domain 'decision/'"` — the spec-vs-lint contradiction, live. Also run `python workspace/lint/design_lint.py --category structural` and record the `_dormant` CoALA/coverage warning count (~37×2). Paste both. Delete the scratch file.
- [ ] **Step 2: Collapse the whitelists.** In `validate_memory.py` set:

```python
# The 10 domains of memory/meta/guide.md §Domains (7 active + 3 reserved).
# Single source of truth — design_lint.py mirrors this set (wfo-04-3).
VALID_DOMAINS = {
    "meta", "person", "slang", "ref", "sys", "research", "vendor",
    "decision", "project", "episodic",
}
```

In `design_lint.py` set `VALID_MEMORY_DOMAINS` to the identical 10-name set with the same comment. Remove `domain`, `ops`, `instruments`, `infra`, `reg` from both.
- [ ] **Step 3: Cap `research`, drop the phantom `domain` cap.** In `validate_memory.py` `DOMAIN_SIZE_LIMITS`: delete the `"domain": 300,` row; add `"research": 300,  # wfo-04-3: busiest domain finally capped (soft WARN, like ref)`. In `memory/design.md:49` replace `domain ≤300` with `research ≤300` in the cap list (one token swap; quote the line as-of-execution first). Soft-cap breaches stay WARN (existing behavior) — the oversized research files WARN but do not redden the gate; Plan 06 trims them.
- [ ] **Step 4: Add `dormant` to the status lifecycle.** `validate_memory.py`: `VALID_STATUSES = {"draft", "active", "stale", "archived", "dormant"}`. In `memory/meta/guide.md`, after the status enum (lines ~82-85), add:

```markdown
### Dormant files

`memory/_dormant/` holds parked content (currently Slang/SecDB/sys). Files there
SHOULD carry `status: dormant`. Lint policy (enforced by `workspace/lint/`):
schema/structure checks (validate_memory, design_lint CoALA/coverage/domains,
index-completeness) skip `_dormant/`+`_archived/` as sources; safety checks
(forbidden patterns, doc safety, hardcoded env) deliberately still scan them;
broken-refs resolves refs *into* `_dormant/` as valid targets. Restore procedure
and per-file status flips: Plan 06 (AW-34).
```

- [ ] **Step 5: Make the `_dormant` skips uniform in `design_lint.py`:** add `"_archived", "_dormant"` to `COALA_SKIP_PREFIXES` (lines ~138-141) and give `check_memory_index_coverage` (lines ~611-676) the same skip its sibling `check_memory_domains` already has (line ~588) — a 1-2 line guard `if rel.parts[0] in ("_dormant", "_archived"): continue` at the top of each file loop, mirroring the existing pattern in `check_memory_domains`. In `lint_forbidden_patterns.py` (near `SKIP_DIRS`, line ~42) and `lint_doc_safety.py` (line ~33) add the comment: `# _dormant/_archived are DELIBERATELY scanned here: safety checks apply to parked content (policy: memory/meta/guide.md §Dormant files, wfo-04-3).`
- [ ] **Step 6 (GREEN + planted checks):** `python workspace/lint/lint_all.py` → `ALL PASSED (15 checks`. Re-run `design_lint.py --category structural` → `_dormant` CoALA/coverage warnings gone; paste count. Re-plant `memory/decision/test-adr.md` → both linters accept the domain (delete after). Plant `memory/ops/test.md` → both ERROR (delete after). Paste all runs.
- [ ] **Step 7: Commit** — `chore(lint): one 10-domain whitelist, research soft cap, documented uniform _dormant policy`

---

## §5 Wave B/C — the six new checks and three extensions (every one red-then-green)

Common requirements for Tasks 4–11: new modules are stdlib-only, self-contained, follow the house shape (module docstring with rules; `main() -> int`; `print` findings as `  ERROR [check] msg` / `  WARN [check] msg`; exit 1 on any ERROR, else 0 ending with `PASS`; resolve `repo_root = Path(__file__).resolve().parent.parent.parent`). Exemplar for shape and style: `workspace/lint/lint_memory_priority.py` (in `file_scope` of every task below via the plan file). Registration in `LINTS` happens ONLY in wfo-04-12.

## Task 4: `lint_args_contract.py` — the args-file contract can't drift again (AW-04 lint half)

**Files:** Create `workspace/lint/lint_args_contract.py`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-4"
goal: "New lint cross-checks every task args-file reference (tasks.json, .code-workspace, SKILL.mds, prompts, vscode-tasks.md) against Plan 03's fixed-path contract and bans create_and_run_task — green on the current tree, RED shown via a planted {run_id} violation"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §5 Task 4
  - workspace/lint/lint_memory_priority.py     # house-style exemplar
  - .vscode/tasks.json
  - memory/ref/vscode-tasks.md
  - skills/GIT/SKILL.md                        # representative args-file consumer
write_scope:
  - workspace/lint/lint_args_contract.py
acceptance_criteria:
  - "python workspace/lint/lint_args_contract.py → exit 0, 'PASS' on the post-Plan-03 tree"
  - "planted violation (change skills/GIT/SKILL.md args path to workspace/tmp/{run_id}_args.json) → exit 1 with ERROR [args-template]; reverted (paste red + green)"
  - "planted create_and_run_task mention in memory/ref/vscode-tasks.md → exit 1 with ERROR [retired-tool]; reverted"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "stdlib only; do not register in lint_all.py (wfo-04-12 owns that)"
context_summary: |
  Plan 03 unified the args-file interface to fixed workspace/tmp/<task-name>_args.json with
  run_id INSIDE the JSON body ([a-z0-9-]+) and retired create_and_run_task everywhere including
  vscode-tasks.md rule E3. This lint is the tripwire that keeps it unified (decision-record
  graft 1 names it one of the four highest-blast-radius checks). Expected green today; red is
  demonstrated by planting.
depends_on: ["wfo-04-1"]
```

- [ ] **Step 1: Implement** `workspace/lint/lint_args_contract.py`:

```python
"""
lint_args_contract.py — Enforce the fixed args-file contract (Plan 03 / AW-04).

Rules:
  A1. Every --args-file value in .vscode/tasks.json and the .code-workspace
      tasks array matches ^workspace/tmp/[a-z0-9_-]+_args\\.json$.
  A2. No templated args filenames ({run_id}, {name}, $RUN_ID …) anywhere in
      skills/**/SKILL.md, .github/prompts/*.prompt.md, memory/ref/vscode-tasks.md.
  A3. create_and_run_task is retired — zero mentions in the same scan set.
  A4. Every workspace/tmp/*_args.json path documented in a SKILL.md must also
      appear in a task definition (no phantom contracts).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARGS_FIXED = re.compile(r"^workspace/tmp/[a-z0-9_-]+_args\.json$")
ARGS_ANY = re.compile(r"workspace/tmp/[^\s`\"')\]]*_args\.json")
TEMPLATED = re.compile(r"workspace/tmp/[^\s`\"')\]]*[{$][^\s`\"')\]]*_args\.json")
DOC_SCAN = ["memory/ref/vscode-tasks.md"]


def task_args_values() -> list[tuple[str, str]]:
    """(source, value) for every --args-file in task definitions."""
    out: list[tuple[str, str]] = []
    for rel in [".vscode/tasks.json"] + [
        p.name for p in REPO_ROOT.glob("*.code-workspace")
    ]:
        p = REPO_ROOT / rel
        if not p.is_file():
            continue
        # tolerate comments in VS Code JSON
        text = re.sub(r"^\s*//.*$", "", p.read_text(encoding="utf-8", errors="replace"),
                      flags=re.MULTILINE)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            out.append((rel, "__UNPARSEABLE__"))
            continue
        tasks = data.get("tasks", {})
        task_list = tasks.get("tasks", tasks) if isinstance(tasks, dict) else tasks
        for t in task_list if isinstance(task_list, list) else []:
            args = t.get("args", [])
            for i, a in enumerate(args):
                if a == "--args-file" and i + 1 < len(args):
                    out.append((f"{rel}#{t.get('label', '?')}", args[i + 1]))
    return out


def doc_files() -> list[Path]:
    files = [REPO_ROOT / d for d in DOC_SCAN if (REPO_ROOT / d).is_file()]
    files += sorted((REPO_ROOT / "skills").rglob("SKILL.md"))
    files += sorted((REPO_ROOT / ".github" / "prompts").glob("*.prompt.md"))
    return files


def main() -> int:
    errors: list[str] = []
    task_vals = task_args_values()
    for src, val in task_vals:
        if val == "__UNPARSEABLE__":
            errors.append(f"[args-parse] {src}: tasks JSON unparseable")
        elif not ARGS_FIXED.match(val.replace("\\", "/")):
            errors.append(f"[args-fixed] {src}: '{val}' violates the fixed-path "
                          f"contract workspace/tmp/<task-name>_args.json")
    task_set = {v.replace("\\", "/") for _, v in task_vals}
    for f in doc_files():
        rel = f.relative_to(REPO_ROOT).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in TEMPLATED.finditer(text):
            errors.append(f"[args-template] {rel}: templated args filename "
                          f"'{m.group(0)}' — run_id belongs INSIDE the JSON body")
        if "create_and_run_task" in text:
            errors.append(f"[retired-tool] {rel}: create_and_run_task is retired "
                          f"(Plan 03 / AW-09) — use run_task with the fixed args file")
        if rel.startswith("skills/") and rel.endswith("SKILL.md"):
            for m in ARGS_ANY.finditer(text):
                val = m.group(0)
                if ARGS_FIXED.match(val) and val not in task_set and task_set:
                    errors.append(f"[args-phantom] {rel}: documents '{val}' but no "
                                  f"task definition uses it")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {len(task_vals)} task args-file values and "
          f"{len(doc_files())} docs honor the fixed args contract.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2 (baseline GREEN):** `python workspace/lint/lint_args_contract.py` → exit 0 (Plan 03 already unified the contract). If it is RED, the live tree drifted from Plan 03 — return `blocked` with the errors (do not silently fix another plan's files).
- [ ] **Step 3 (planted RED ×2, recorded):** (a) In `skills/GIT/SKILL.md`, change one documented args path to `workspace/tmp/{run_id}_args.json`; run → `ERROR [args-template]`; revert (`git checkout -- skills/GIT/SKILL.md`). (b) Add the line `Use create_and_run_task as fallback.` to `memory/ref/vscode-tasks.md`; run → `ERROR [retired-tool]`; revert. Paste all four runs (red, green each).
- [ ] **Step 4: Commit** — `chore(lint): add args-contract lint (fixed path, no templates, create_and_run_task banned)`

## Task 5: `lint_model_pins.py` — one model constant to rule them all (AW-23/G3 lint half)

**Files:** Create `workspace/lint/lint_model_pins.py`, `workspace/lint/whitelists/model_pins.txt`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-5"
goal: "New lint owns EXPECTED_MODEL='Claude Opus 4.6' and flags every raw model literal outside prompt frontmatter, itself, and the two SANCTIONED_SITES (policy/subagent_protocol.md + .github/copilot-instructions.md, structurally exempt) — genuinely RED on the current tree (~42 prose hits), GREEN via the recorded model_pins.txt whitelist that Plans 05/07 burn fully EMPTY"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §5 Task 5
  - workspace/lint/lint_memory_priority.py     # house-style exemplar
  - .github/copilot-instructions.md            # a known prose-pin holder (read-only)
write_scope:
  - workspace/lint/lint_model_pins.py
  - workspace/lint/whitelists/model_pins.txt
acceptance_criteria:
  - "python workspace/lint/lint_model_pins.py with empty whitelist → exit 1 listing every prose literal OUTSIDE the two SANCTIONED_SITES (recorded RED; count ≈ 42 minus the exempt sites, live number may drift)"
  - "with whitelist populated from the red run → exit 0"
  - "policy/subagent_protocol.md and .github/copilot-instructions.md are NOT flagged even with an EMPTY whitelist (structurally exempt via SANCTIONED_SITES); they never appear in model_pins.txt, which therefore burns fully EMPTY by Plan 07"
  - "scratch prompt frontmatter 'model: Claude Opus 4.5' → exit 1 ERROR [pin-mismatch] regardless of whitelist (planted, reverted)"
  - "python -c \"from lint_model_pins import EXPECTED_MODEL; print(EXPECTED_MODEL)\" (cwd workspace/lint) → Claude Opus 4.6"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "do NOT edit any file holding a literal — Plans 05 (prose) and 07 (prompt rationalization) own the content; this task ships the tripwire + whitelist only"
context_summary: |
  The model is pinned as a hardcoded display-name literal in ~76 places (34 prompt frontmatter
  pins + ~42 prose). The ledger makes lint_model_pins.py the single owner of the constant;
  lint_prompts.py (wfo-04-8) imports it; Plans 05/07 replace prose literals with pointers and
  burn the whitelist. Frontmatter pins are ALLOWED but must equal the constant. TWO prose sites
  keep the raw literal by design — policy/subagent_protocol.md (canonical pin) and
  .github/copilot-instructions.md Rule 9 (fallback clause) — so the lint hardcodes them in
  SANCTIONED_SITES (structurally exempt, never whitelisted); model_pins.txt burns fully EMPTY.
depends_on: ["wfo-04-1"]
```

- [ ] **Step 1: Implement** `workspace/lint/lint_model_pins.py`:

```python
"""
lint_model_pins.py — Single source of truth for the subagent model pin (AW-G3/AW-23).

EXPECTED_MODEL is THE constant. All other surfaces must point here, not restate it.
Rules:
  M1. In .github/prompts/*.prompt.md frontmatter, any 'model:' value must equal
      EXPECTED_MODEL exactly (frontmatter pins are allowed; mismatches never are).
  M2. Any other occurrence of a model literal (display name 'Claude Opus <ver>'
      or slug 'claude-opus…') in tracked text surfaces is an ERROR unless the
      file is grandfathered in whitelists/model_pins.txt (burned by Plans 05/07).
  M3. Files in SANCTIONED_SITES are skipped ENTIRELY — the raw literal is
      canonical there (the pin itself + the fallback clause). These are
      structurally exempt, NOT whitelist entries, so model_pins.txt burns EMPTY.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EXPECTED_MODEL = "Claude Opus 4.6"

# Sites where the raw display-name literal is CANONICAL and must remain —
# structurally exempt (NOT whitelisted): policy/subagent_protocol.md (the
# canonical pin) and .github/copilot-instructions.md Rule 9 (fallback clause).
# The lint skips these two paths entirely; every OTHER prose literal is an ERROR
# (grandfathered via model_pins.txt until Plans 05/07 burn it fully EMPTY).
SANCTIONED_SITES = frozenset({
    "policy/subagent_protocol.md",
    ".github/copilot-instructions.md",
})

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WHITELIST = Path(__file__).resolve().parent / "whitelists" / "model_pins.txt"
LITERAL = re.compile(r"Claude\s+Opus\s+[0-9][0-9.]*|claude-opus[\w.\-]*", re.IGNORECASE)
FRONTMATTER_MODEL = re.compile(r"^model:\s*(.+?)\s*$", re.MULTILINE)
SCAN_DIRS = [".github", "workflows", "policy", "personas", "skills", "memory"]
SCAN_FILES = ["AGENTS.md"]
SKIP_PARTS = {"_dormant", "_archived", "node_modules", "__pycache__", "enghub", "knowledge", "tmp"}
EXTS = {".md", ".yaml", ".yml", ".json"}


def load_whitelist() -> set[str]:
    if not WHITELIST.is_file():
        return set()
    return {
        line.strip() for line in WHITELIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def frontmatter_span(text: str) -> tuple[int, int]:
    m = re.match(r"^---\s*\n.*?\n---", text, re.DOTALL)
    return (m.start(), m.end()) if m else (0, 0)


def scan_files() -> list[Path]:
    files = [REPO_ROOT / f for f in SCAN_FILES if (REPO_ROOT / f).is_file()]
    for d in SCAN_DIRS:
        root = REPO_ROOT / d
        if root.is_dir():
            files += [
                p for p in sorted(root.rglob("*"))
                if p.suffix in EXTS and not (set(p.parts) & SKIP_PARTS)
            ]
    return files


def main() -> int:
    wl = load_whitelist()
    errors: list[str] = []
    for f in scan_files():
        rel = f.relative_to(REPO_ROOT).as_posix()
        if rel in SANCTIONED_SITES:
            continue  # canonical pin lives here — structurally exempt (not whitelisted)
        text = f.read_text(encoding="utf-8", errors="replace")
        is_prompt = rel.startswith(".github/prompts/") and rel.endswith(".prompt.md")
        fm_start, fm_end = frontmatter_span(text) if is_prompt else (0, 0)
        if is_prompt:
            for m in FRONTMATTER_MODEL.finditer(text[fm_start:fm_end]):
                if m.group(1).strip().strip("'\"") != EXPECTED_MODEL:
                    errors.append(f"[pin-mismatch] {rel}: frontmatter model "
                                  f"'{m.group(1).strip()}' != EXPECTED_MODEL "
                                  f"'{EXPECTED_MODEL}'")
        for m in LITERAL.finditer(text):
            if is_prompt and fm_start <= m.start() < fm_end:
                continue  # frontmatter pins handled by M1
            if rel in wl:
                break  # grandfathered file — Plans 05/07 burn it down
            line_no = text.count("\n", 0, m.start()) + 1
            errors.append(f"[raw-literal] {rel}:{line_no}: raw model literal "
                          f"'{m.group(0)}' — point at lint_model_pins.EXPECTED_MODEL "
                          f"or policy/subagent_protocol.md instead")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: model pin literals confined to prompt frontmatter (== "
          f"'{EXPECTED_MODEL}') and {len(wl)} grandfathered files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2 (RED, recorded):** Create `workspace/lint/whitelists/model_pins.txt` containing ONLY the header (`# model_pins.txt — GRANDFATHERED files holding raw model literals.` / `# Plans 05 (prose) and 07 (prompt hygiene) burn this to empty. Only shrinks.` / `# One repo-relative path per line.`). Run the lint → exit 1 listing every prose-literal file (recon predicts ~42 hits across AGENTS.md, workflows, policy, skills, memory; the two SANCTIONED_SITES — `policy/subagent_protocol.md` and `.github/copilot-instructions.md` — are structurally exempt and absent from this list, so they are NOT whitelisted). Paste the full output. **This is the failing test.**
- [ ] **Step 3 (GREEN):** Append every distinct file path from the red run to the whitelist (paths only, deduplicated, sorted). Re-run → exit 0. Paste.
- [ ] **Step 4 (planted pin-mismatch):** In a scratch edit change one prompt's frontmatter to `model: Claude Opus 4.5`, run → `ERROR [pin-mismatch]` (whitelist does NOT save it — mismatches are never grandfathered), revert. Paste.
- [ ] **Step 5: Commit** — `chore(lint): add model-pin lint owning EXPECTED_MODEL, grandfathered prose recorded for Plans 05/07`

## Task 6: `lint_wrapper_targets.py` — no wrapper may point at a ghost (AW-05 regression guard)

**Files:** Create `workspace/lint/lint_wrapper_targets.py`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-6"
goal: "New lint asserts every *_task.{cmd,sh} wrapper's _PY_SCRIPT / 'python -m volforecast.*' target exists on disk and parses (ast.parse) — green post-Plan-03, RED shown by planting a ghost target"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §5 Task 6
  - workspace/lint/lint_memory_priority.py     # house-style exemplar
  - workspace/lint/lint_task.cmd               # wrapper format exemplar
  - skills/DATA_INGEST/src/ingest_task.cmd     # repointed-by-Plan-03 wrapper
write_scope:
  - workspace/lint/lint_wrapper_targets.py
acceptance_criteria:
  - "python workspace/lint/lint_wrapper_targets.py → exit 0 on the post-Plan-03 tree, summary counts >= 40 wrappers checked"
  - "planted ghost (_PY_SCRIPT pointed at nonexistent .py in one wrapper) → exit 1 ERROR [target-missing]; reverted (paste red + green)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "stdlib only; 'import' is implemented as ast.parse (env-independent — never actually import: skill code targets GS services and heavy deps)"
context_summary: |
  Before Plan 03, MODEL_TRAIN/NOTEBOOK/RESEARCH wrappers invoked nonexistent Python modules
  (AW-05, BLOCKER). Plan 03 repointed or deleted them; this lint (decision-record graft 1,
  highest-blast-radius class) makes a recurrence impossible. Targets are resolved statically:
  %~dp0-relative _PY_SCRIPT paths and python -m volforecast.<mod> module paths mapped to
  src/volforecast/<mod path>.py — checked for existence and syntax only.
depends_on: ["wfo-04-1"]
```

- [ ] **Step 1: Implement** `workspace/lint/lint_wrapper_targets.py`:

```python
"""
lint_wrapper_targets.py — Every skill/lint task wrapper must target real code (AW-05 guard).

Rules:
  W-T1. Each *_task.cmd / *_task.sh under skills/**/src/ and workspace/lint/
        declaring _PY_SCRIPT must point at an existing .py file (after resolving
        %~dp0 / ${SCRIPT_DIR} / $(dirname …) to the wrapper's directory).
  W-T2. That file must be syntactically valid Python (ast.parse — we never
        import: skill code targets GS services and heavy optional deps).
  W-T3. Any 'python -m volforecast.<mod>' in a wrapper must map to an existing
        src/volforecast/<mod>.py or <mod>/__init__.py that parses.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PY_SCRIPT_CMD = re.compile(r'_PY_SCRIPT=(?:%~dp0)?([^"&\r\n]+\.py)')
PY_SCRIPT_SH = re.compile(r'_PY_SCRIPT="?(?:\$\{?SCRIPT_DIR\}?/|\$\(dirname[^)]*\)/)?([^"\s]+\.py)')
MODULE_TARGET = re.compile(r"python[3]?\s+-m\s+(volforecast[\w.]*)")


def wrappers() -> list[Path]:
    out: list[Path] = []
    for root in [REPO_ROOT / "skills", REPO_ROOT / "workspace" / "lint"]:
        if root.is_dir():
            out += sorted(root.rglob("*_task.cmd")) + sorted(root.rglob("*_task.sh"))
    return out


def check_parses(p: Path) -> str | None:
    try:
        ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return f"line {exc.lineno}: {exc.msg}"
    return None


def module_to_path(mod: str) -> Path | None:
    base = REPO_ROOT / "src" / Path(*mod.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def main() -> int:
    errors: list[str] = []
    checked = 0
    for w in wrappers():
        rel = w.relative_to(REPO_ROOT).as_posix()
        text = w.read_text(encoding="utf-8", errors="replace")
        pat = PY_SCRIPT_CMD if w.suffix == ".cmd" else PY_SCRIPT_SH
        for m in pat.finditer(text):
            checked += 1
            target = (w.parent / m.group(1).strip().replace("\\", "/")).resolve()
            if not target.is_file():
                errors.append(f"[target-missing] {rel}: _PY_SCRIPT → "
                              f"'{m.group(1).strip()}' does not exist")
            else:
                err = check_parses(target)
                if err:
                    errors.append(f"[target-syntax] {rel}: {target.name} — {err}")
        for m in MODULE_TARGET.finditer(text):
            checked += 1
            mod_path = module_to_path(m.group(1))
            if mod_path is None:
                errors.append(f"[module-missing] {rel}: python -m {m.group(1)} — "
                              f"no such module under src/volforecast/")
            else:
                err = check_parses(mod_path)
                if err:
                    errors.append(f"[module-syntax] {rel}: {mod_path.name} — {err}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {checked} wrapper targets across {len(wrappers())} wrappers "
          f"exist and parse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2 (baseline GREEN):** run → exit 0, `checked >= 40`. If RED: the live tree drifted from Plan 03 — return `blocked` with the errors.
- [ ] **Step 3 (planted RED, recorded):** In `workspace/lint/lint_task.cmd` change `_PY_SCRIPT=%~dp0lint_all.py` to `_PY_SCRIPT=%~dp0lint_all_GHOST.py`; run → `ERROR [target-missing]`; revert with `git checkout -- workspace/lint/lint_task.cmd`; re-run green. Paste all three runs.
- [ ] **Step 4: Commit** — `chore(lint): add wrapper-target lint (every task wrapper points at code that exists and parses)`

## Task 7: `lint_vol_parity.py` — `./vol help` and vol-cli.md can't diverge again (AW-55/G6/G16 lint half)

**Files:** Create `workspace/lint/lint_vol_parity.py`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-7"
goal: "New lint asserts command-for-command parity between the vol dispatch case arms / help heredoc and memory/ref/vol-cli.md — green after Plan 03's regeneration, RED shown by deleting one doc row (planted, reverted)"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §5 Task 7
  - workspace/lint/lint_memory_priority.py     # house-style exemplar
  - vol                                        # dispatch arms + help heredoc (read-only)
  - memory/ref/vol-cli.md
write_scope:
  - workspace/lint/lint_vol_parity.py
acceptance_criteria:
  - "python workspace/lint/lint_vol_parity.py → exit 0, summary names the parity count (34 commands: 33 + forecast, per Plan 03; use the live count)"
  - "planted: delete the test-all row from memory/ref/vol-cli.md → exit 1 ERROR [doc-missing] naming test-all; reverted (paste red + green)"
  - "planted: append a fake 'zzz)' case arm to a scratch COPY of vol parsed via --vol-path override is NOT required — the doc-row deletion suffices as the red demonstration"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta (vol's case block was at ~lines 211-340 pre-Plan-03; Plan 03 added the OS guard and forecast arm — anchors WILL have moved)"
  - "the 5 research plans in workspace/plans/ are read-only; never modify the vol script itself"
  - "stdlib only; parse vol as TEXT (never execute it — it hard-exits off-Linux by design)"
context_summary: |
  memory/ref/vol-cli.md claimed to 'mirror ./vol help' while omitting 13-14 of 33 commands
  (AW-G6/G16/55). Plan 03 regenerated the doc from the help heredoc and added the forecast arm;
  this lint keeps them locked. Parse both sides as text: case arms from the dispatch block,
  command tokens from the doc's table rows.
depends_on: ["wfo-04-1"]
```

- [ ] **Step 1: Implement** `workspace/lint/lint_vol_parity.py`:

```python
"""
lint_vol_parity.py — ./vol dispatch arms <-> memory/ref/vol-cli.md parity (AW-55/G6/G16).

Rules:
  V1. Every case arm in vol's dispatch block has a row in vol-cli.md.
  V2. Every command documented in vol-cli.md is a real case arm.
  V3. Every case arm also appears in vol's help heredoc (self-consistency).
vol is parsed as TEXT (never executed — it exits 2 off-Linux by design, Plan 03).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VOL = REPO_ROOT / "vol"
DOC = REPO_ROOT / "memory" / "ref" / "vol-cli.md"
# case arms:   two spaces/tab indent, token(s), ')' — e.g. "  test|testlf)"
CASE_ARM = re.compile(r"^\s{2,}([a-z][a-z0-9_|-]*)\)\s*(?:#.*)?$", re.MULTILINE)
# doc rows:    | `command ...` | description |
DOC_CMD = re.compile(r"^\|\s*`([a-z][a-z0-9-]*)", re.MULTILINE)
IGNORE_ARMS = {"help", "-h", "--help"}  # help documents itself


def vol_case_arms(text: str) -> set[str]:
    arms: set[str] = set()
    for m in CASE_ARM.finditer(text):
        for tok in m.group(1).split("|"):
            if tok and tok not in IGNORE_ARMS and not tok.startswith("-"):
                arms.add(tok)
    return arms


def help_commands(text: str) -> set[str]:
    # help heredoc lines look like "  test [args]      Run pytest …"
    out: set[str] = set()
    m = re.search(r"<<\s*'?EOF'?\s*\n(.*?)\nEOF", text, re.DOTALL)
    block = m.group(1) if m else text
    for line in block.splitlines():
        lm = re.match(r"^\s{2}([a-z][a-z0-9-]*)\b", line)
        if lm:
            out.add(lm.group(1))
    return out


def main() -> int:
    if not VOL.is_file() or not DOC.is_file():
        print(f"  ERROR [missing] vol or vol-cli.md not found")
        return 1
    vol_text = VOL.read_text(encoding="utf-8", errors="replace")
    doc_text = DOC.read_text(encoding="utf-8", errors="replace")
    arms = vol_case_arms(vol_text)
    doc_cmds = {c for c in (m.group(1) for m in DOC_CMD.finditer(doc_text))
                if c not in IGNORE_ARMS}
    help_cmds = help_commands(vol_text)
    if len(arms) < 20:
        print(f"  ERROR [parse] only {len(arms)} case arms parsed from vol — "
              f"the dispatch-block regex anchor has drifted; fix CASE_ARM")
        return 1
    errors: list[str] = []
    for c in sorted(arms - doc_cmds):
        errors.append(f"[doc-missing] vol arm '{c}' has no row in memory/ref/vol-cli.md")
    for c in sorted(doc_cmds - arms):
        errors.append(f"[doc-phantom] vol-cli.md documents '{c}' but vol has no such arm")
    for c in sorted(arms - help_cmds):
        errors.append(f"[help-missing] vol arm '{c}' absent from vol's own help heredoc")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {len(arms)} vol commands in full parity with vol-cli.md and vol help.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2 (baseline GREEN):** run → exit 0 with the live command count (expected 34 post-Plan-03). If `[parse]` fires, adjust `CASE_ARM`/`DOC_CMD` against the live files and note the anchor delta in `notes`. If genuine parity errors fire, the live tree drifted from Plan 03 — return `blocked`.
- [ ] **Step 3 (planted RED, recorded):** Delete the `test-all` row from `memory/ref/vol-cli.md`; run → `ERROR [doc-missing] vol arm 'test-all'…`; revert (`git checkout -- memory/ref/vol-cli.md`); re-run green. Paste all three runs.
- [ ] **Step 4: Commit** — `chore(lint): add vol-parity lint (dispatch arms == vol-cli.md rows == help heredoc)`

## Task 8: `lint_prompts.py` — prompt-layer hygiene tripwire (consumed by Plan 07)

**Files:** Create `workspace/lint/lint_prompts.py`, `workspace/lint/whitelists/prompts.txt`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-8"
goal: "New lint enforces prompt filename shape, instruction-verb presence, frontmatter model == lint_model_pins.EXPECTED_MODEL, and (once it exists) INDEX.md bijection — genuinely RED on the current tree ('fix it.prompt.md', verbless stubs), GREEN via the recorded prompts.txt whitelist Plan 07 burns"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §5 Task 8
  - workspace/lint/lint_memory_priority.py     # house-style exemplar
  - workspace/lint/lint_model_pins.py          # EXPECTED_MODEL import
  - .github/prompts/learn.prompt.md            # known verbless stub (read-only)
write_scope:
  - workspace/lint/lint_prompts.py
  - workspace/lint/whitelists/prompts.txt
acceptance_criteria:
  - "python workspace/lint/lint_prompts.py with empty whitelist → exit 1 flagging 'fix it.prompt.md' [filename] and each verbless body [no-verb] (recorded RED)"
  - "with whitelist populated from the red run → exit 0, and prints 'NOTICE [index] .github/prompts/INDEX.md absent — bijection check activates when Plan 07 lands it'"
  - "scratch INDEX.md with one phantom row → exit 1 ERROR [index-phantom] (planted, deleted)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "do NOT rename 'fix it.prompt.md' or edit any prompt body — Plan 07 owns the content; this task ships the tripwire + whitelist only"
  - "import EXPECTED_MODEL from lint_model_pins (same directory — script-dir sys.path makes it importable); never restate the literal"
context_summary: |
  Plan 07 renames 'fix it.prompt.md', adds instruction verbs to verbless bodies, creates
  .github/prompts/INDEX.md, and rationalizes pins — this lint is the gate Plan 07's acceptance
  runs against. The bare-backtick dispatcher pattern is deliberate and lint-enforced elsewhere
  (do-not-rebuild #6): this lint must NOT require Markdown links. Depends on wfo-04-5 for
  EXPECTED_MODEL.
depends_on: ["wfo-04-5"]
```

- [ ] **Step 1: Implement** `workspace/lint/lint_prompts.py`:

```python
"""
lint_prompts.py — Prompt-layer hygiene (AW-11/23/37/43 halves; Plan 07's gate).

Rules:
  P1. Filenames match ^[a-z0-9-]+\\.prompt\\.md$ (no spaces — AW-37).
  P2. If .github/prompts/INDEX.md exists: bijection — every prompt has a row,
      every row's prompt exists. (Activates when Plan 07 lands INDEX.md.)
  P3. Every prompt body (post-frontmatter) contains at least one instruction
      verb — bare backtick context paths alone are NOT auto-injected (AW-11).
  P4. Frontmatter 'model:' (when present) == lint_model_pins.EXPECTED_MODEL.
Whitelist: whitelists/prompts.txt grandfathers pre-Plan-07 violations (only shrinks).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from lint_model_pins import EXPECTED_MODEL  # single source of truth (wfo-04-5)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS = REPO_ROOT / ".github" / "prompts"
WHITELIST = Path(__file__).resolve().parent / "whitelists" / "prompts.txt"
FNAME = re.compile(r"^[a-z0-9-]+\.prompt\.md$")
VERB = re.compile(
    r"\b(read|run|load|execute|follow|use|apply|check|review|generate|write|"
    r"report|analyze|analyse|inspect|summarize|produce|update|create|fix|"
    r"validate|verify|list|search|open)\b", re.IGNORECASE)
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
FM_MODEL = re.compile(r"^model:\s*(.+?)\s*$", re.MULTILINE)
INDEX_ROW = re.compile(r"^\|\s*`?/?([a-z0-9 -]+?)`?\s*\|", re.MULTILINE)


def load_whitelist() -> set[str]:
    if not WHITELIST.is_file():
        return set()
    return {line.strip() for line in WHITELIST.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


def main() -> int:
    wl = load_whitelist()
    errors: list[str] = []
    notices: list[str] = []
    prompt_files = sorted(p for p in PROMPTS.glob("*.prompt.md"))
    stems: set[str] = set()
    for p in prompt_files:
        name = p.name
        stems.add(name[: -len(".prompt.md")])
        wl_hit = name in wl
        if not FNAME.match(name) and not wl_hit:
            errors.append(f"[filename] '{name}' violates ^[a-z0-9-]+\\.prompt\\.md$")
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = FRONTMATTER.match(text)
        body = text[fm.end():] if fm else text
        if fm:
            for m in FM_MODEL.finditer(fm.group(1)):
                val = m.group(1).strip().strip("'\"")
                if val != EXPECTED_MODEL:
                    errors.append(f"[pin-mismatch] {name}: model '{val}' != "
                                  f"'{EXPECTED_MODEL}'")  # never whitelisted
        if not VERB.search(body) and not wl_hit:
            errors.append(f"[no-verb] {name}: body has no instruction verb — "
                          f"backtick paths are not auto-injected (AW-11)")
    index = PROMPTS / "INDEX.md"
    if index.is_file():
        rows = {m.group(1).strip().replace(" ", "-")
                for m in INDEX_ROW.finditer(index.read_text(encoding="utf-8"))}
        rows.discard("prompt")  # header row
        for s in sorted(stems - rows):
            errors.append(f"[index-missing] {s}.prompt.md has no INDEX.md row")
        for r in sorted(rows - stems):
            errors.append(f"[index-phantom] INDEX.md row '{r}' has no prompt file")
    else:
        notices.append("[index] .github/prompts/INDEX.md absent — bijection check "
                       "activates when Plan 07 lands it")
    for n in notices:
        print(f"  NOTICE {n}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {len(prompt_files)} prompts hygienic "
          f"({len(wl)} grandfathered until Plan 07).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2 (RED, recorded):** Create `workspace/lint/whitelists/prompts.txt` with header only (`# prompts.txt — GRANDFATHERED prompt files. Plan 07 burns to empty. Only shrinks.` / `# One prompt filename per line.`). Run → exit 1: `[filename] 'fix it.prompt.md'…` plus `[no-verb]` for each verbless stub (recon names `learn.prompt.md`; the live red run is authoritative). Paste. **This is the failing test.**
- [ ] **Step 3 (GREEN):** Append each flagged filename to the whitelist. Re-run → exit 0 with the `NOTICE [index]` line. Paste.
- [ ] **Step 4 (planted index red):** Create a scratch `.github/prompts/INDEX.md` with a single table containing one row naming a nonexistent prompt (`| ghost-prompt | x |`); run → `ERROR [index-phantom]` plus `[index-missing]` for every real prompt; delete the scratch file; re-run green. Paste.
- [ ] **Step 5: Commit** — `chore(lint): add prompts lint (filenames, verbs, pin==constant, future INDEX bijection), grandfathered for Plan 07`

## Task 9: Extend `lint_broken_refs.py` — plain-text paths + `_dormant` awareness (AW-12 lint half)

**Files:** Modify `workspace/lint/lint_broken_refs.py` (appended functions only). Create `workspace/lint/whitelists/broken_refs.txt`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-9"
goal: "lint_broken_refs.py gains two APPENDED checks — plain-text repo-path refs must resolve, and refs whose target migrated into memory/_dormant/ are named as such — genuinely RED on the current tree (~51 broken skill→memory refs), GREEN via the recorded broken_refs.txt whitelist Plan 06 burns"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §5 Task 9
  - workspace/lint/lint_broken_refs.py
  - skills/RESEARCH/SKILL.md        # known broken-ref holder (:50/:145, read-only)
write_scope:
  - workspace/lint/lint_broken_refs.py
  - workspace/lint/whitelists/broken_refs.txt
acceptance_criteria:
  - "python workspace/lint/lint_broken_refs.py with empty whitelist → exit 1; new [plain-ref]/[dormant-migrated] errors ≈ the audit's 51 (13-51 band; live run authoritative — paste it)"
  - "with whitelist populated from the red run → exit 0"
  - "refs to workspace/tmp/** are exempt (runtime-ephemeral) — AGENTS.md:58's backticked session-handoff path from wfo-04-1 must NOT be flagged"
  - "existing check functions byte-identical (git diff shows only appended code + main() wiring)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "APPEND-only: new functions + two lines in main(); existing SKIP_DIRS / EXTERNAL_DOC_DIRS behavior untouched (do-not-rebuild #7)"
  - "do NOT fix any broken ref — Plan 06 rewrites the 48 recoverable and disposes the 3 dead ones; this task makes them VISIBLE and grandfathers them"
context_summary: |
  ~13-51 skill→memory references broke when files moved to memory/_dormant/ — invisible because
  the existing checks miss plain-text path mentions and treat _dormant only as a skipped SOURCE
  dir. The extension resolves plain-text repo paths, resolves refs INTO _dormant as valid
  targets, and specifically labels refs whose target now lives under _dormant (Plan 06's
  work-list). wfo-04-1 must land first (its backtick fix must be exempted via the
  workspace/tmp runtime rule, not whitelisted).
depends_on: ["wfo-04-1"]
```

- [ ] **Step 1: Append** to `lint_broken_refs.py` (below the existing checks; wire into `main()`'s results collection the same way existing checks are — mirror the call pattern already in that file):

```python
# ── wfo-04-9 appended checks (AW-12 lint half) — existing logic above untouched ──

PLAIN_PATH = re.compile(
    r"(?<![\w/(\[])((?:memory|skills|workflows|policy|personas|workspace|src|"
    r"\.github)/[\w][\w./-]*\.(?:md|py|yaml|yml|json|sh|cmd|s))\b")
RUNTIME_DIRS = ("workspace/tmp/",)  # ephemeral by design — never checked
REFS_WHITELIST = Path(__file__).resolve().parent / "whitelists" / "broken_refs.txt"


def _load_refs_whitelist() -> set[str]:
    if not REFS_WHITELIST.is_file():
        return set()
    return {ln.strip() for ln in REFS_WHITELIST.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


def check_plain_text_refs(md_files, repo_root) -> list[str]:
    """Plain-text repo paths must resolve; targets migrated to _dormant are named."""
    wl = _load_refs_whitelist()
    errors: list[str] = []
    for f in md_files:  # the same scanned-source list the existing checks use
        rel = f.relative_to(repo_root).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in PLAIN_PATH.finditer(text):
            target = m.group(1)
            if target.startswith(RUNTIME_DIRS):
                continue
            if (repo_root / target).exists():
                continue
            key = f"{rel} -> {target}"
            if key in wl:
                continue  # grandfathered — Plan 06 burns this down
            dormant = repo_root / "memory" / "_dormant" / Path(target).relative_to(
                "memory") if target.startswith("memory/") else None
            if dormant is not None and dormant.exists():
                errors.append(f"[dormant-migrated] {rel}: '{target}' migrated to "
                              f"memory/_dormant/ — update the ref or restore (Plan 06)")
            else:
                errors.append(f"[plain-ref] {rel}: plain-text path '{target}' "
                              f"does not exist")
    return errors
```

Note: refs written directly as `memory/_dormant/...` resolve via the plain `(repo_root / target).exists()` branch — `_dormant` is a valid TARGET (uniform policy, wfo-04-3).
- [ ] **Step 2 (RED, recorded):** Create `workspace/lint/whitelists/broken_refs.txt` with header only (`# broken_refs.txt — GRANDFATHERED broken refs (source -> target). Plan 06 burns to empty. Only shrinks.`). Run `python workspace/lint/lint_broken_refs.py` → exit 1 with the new errors (audit band 13–51; expect `skills/RESEARCH/SKILL.md`, `skills/SEARCH/SKILL.md` among them). Paste in full. **This is the failing test.**
- [ ] **Step 3 (GREEN):** Copy every `source -> target` pair from the red output into the whitelist. Re-run → exit 0. Verify with `git diff workspace/lint/lint_broken_refs.py` that only appended code + `main()` wiring changed. Paste both.
- [ ] **Step 4: Commit** — `chore(lint): broken-refs sees plain-text paths and _dormant migrations; 51 knowns grandfathered for Plan 06`

## Task 10: `lint_canonical_schema.py` — the canonical example can't rot again (AW-20/G23 lint half)

**Files:** Create `workspace/lint/lint_canonical_schema.py`, `workspace/lint/whitelists/canonical_schema.txt`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-10"
goal: "New lint regex-extracts every @register_model/@register_feature_layer key and the sequences.source enum from src, and asserts each appears in BOTH _CANONICAL_EXAMPLE.yaml and yaml-config.instructions.md — genuinely RED today (gnn, conditional_duan, implied_correlation, embargo missing), GREEN via the recorded whitelist Plan 06 burns"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §5 Task 10
  - workspace/lint/lint_memory_priority.py     # house-style exemplar
  - workspace/configs/_CANONICAL_EXAMPLE.yaml  # read-only
  - .github/instructions/yaml-config.instructions.md   # read-only
  - src/volforecast/config.py                  # read-only (regex source)
write_scope:
  - workspace/lint/lint_canonical_schema.py
  - workspace/lint/whitelists/canonical_schema.txt
acceptance_criteria:
  - "python workspace/lint/lint_canonical_schema.py with empty whitelist → exit 1 naming at least gnn, implied_correlation, conditional_duan, embargo (recorded RED)"
  - "with whitelist populated from the red run → exit 0"
  - "the lint never imports volforecast (grep -c 'import volforecast' → 0) — registry keys come from regex over source text"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; workspace/configs/ is READ-only here — the canonical is regenerated by Plan 06, never by this task"
  - "stdlib only — no yaml import; token-presence checks over raw text (Plan 06 owns the 'canonical loads' self-validation)"
context_summary: |
  _CANONICAL_EXAMPLE.yaml violates its own Schema Maintenance Rule (4 live registry/schema
  additions never propagated) and the instruction doc's enum tables are stale versus the live
  registries (AW-G23/G24/G25). Plan 06 regenerates the content; this lint keeps it regenerated.
  The G22 do-NOT applies: never claim gnn fails at runner.py:1509 — this lint checks DOC
  completeness only.
depends_on: ["wfo-04-1"]
```

- [ ] **Step 1: Implement** `workspace/lint/lint_canonical_schema.py`:

```python
"""
lint_canonical_schema.py — canonical YAML + instruction-doc completeness vs live
registries (AW-20/G23/G24/G25 lint half).

Rules:
  C1. Every @register_model("<key>") and @register_feature_layer("<key>") in
      src/volforecast/**/*.py appears as a token in BOTH
      workspace/configs/_CANONICAL_EXAMPLE.yaml and
      .github/instructions/yaml-config.instructions.md.
  C2. Every sequences 'source' enum literal in src/volforecast/config.py
      appears in both docs; so do the schema fields in EXTRA_FIELDS.
Registry keys come from REGEX over source text — never import volforecast
(heavy/optional deps; lints must run env-independent).
Whitelist: whitelists/canonical_schema.txt grandfathers pre-Plan-06 gaps.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL = REPO_ROOT / "workspace" / "configs" / "_CANONICAL_EXAMPLE.yaml"
DOC = REPO_ROOT / ".github" / "instructions" / "yaml-config.instructions.md"
WHITELIST = Path(__file__).resolve().parent / "whitelists" / "canonical_schema.txt"
REGISTER = re.compile(r'@register_(?:model|feature_layer)\(\s*"([\w-]+)"\s*\)')
SOURCE_ENUM = re.compile(r'"(parquet[\w]*|daily_lookback)"')
# Fields the audit proved live in config.py but missing from the docs (AW-G24/G25):
EXTRA_FIELDS = ["conditional_duan", "feature_selection", "blend",
                "n_splits", "embargo", "bar_interval", "lookback_days"]


def load_whitelist() -> set[str]:
    if not WHITELIST.is_file():
        return set()
    return {ln.strip() for ln in WHITELIST.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


def main() -> int:
    wl = load_whitelist()
    src_dir = REPO_ROOT / "src" / "volforecast"
    keys: set[str] = set()
    for py in sorted(src_dir.rglob("*.py")):
        keys |= set(REGISTER.findall(py.read_text(encoding="utf-8", errors="replace")))
    config_py = (src_dir / "config.py").read_text(encoding="utf-8", errors="replace")
    enum_vals = set(SOURCE_ENUM.findall(config_py))
    if not keys:
        print("  ERROR [parse] zero registry keys extracted — REGISTER regex drifted")
        return 1
    canonical = CANONICAL.read_text(encoding="utf-8", errors="replace")
    doc = DOC.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    for token in sorted(keys | enum_vals | set(EXTRA_FIELDS)):
        for label, text in (("canonical", canonical), ("instruction-doc", doc)):
            if not re.search(rf"\b{re.escape(token)}\b", text):
                key = f"{label}:{token}"
                if key not in wl:
                    errors.append(f"[schema-gap] '{token}' missing from the {label} "
                                  f"({CANONICAL.name if label == 'canonical' else DOC.name})")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {len(keys)} registry keys + {len(enum_vals)} enum values + "
          f"{len(EXTRA_FIELDS)} schema fields present in both docs "
          f"({len(wl)} grandfathered until Plan 06).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2 (RED, recorded):** Create `workspace/lint/whitelists/canonical_schema.txt` with header only (`# canonical_schema.txt — GRANDFATHERED doc gaps (canonical:<token> / instruction-doc:<token>). Plan 06 burns to empty. Only shrinks.`). Run → exit 1 naming at least `gnn`, `implied_correlation`, `conditional_duan`, `embargo` gaps. Paste in full. **This is the failing test.**
- [ ] **Step 3 (GREEN):** Copy every `label:token` key from the red output into the whitelist. Re-run → exit 0. Paste.
- [ ] **Step 4: Commit** — `chore(lint): add canonical-schema lint (registry/enum/doc completeness), gaps grandfathered for Plan 06`

## Task 11: Rule T9 (exit-0 wrappers) + design_lint §4.9 (skill-dispatch registration)

**Files:** Modify `workspace/lint/lint_vscode_tasks.py` (append T9), `workspace/lint/design_lint.py` (append `skill-dispatch` check). Create `workspace/lint/whitelists/dispatch_registration.txt`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-11"
goal: "lint_vscode_tasks.py gains rule T9 (no wrapper swallows exit codes) and design_lint.py gains the §4.9 skill-dispatch-registration check — T9 planted-red then green, §4.9 genuinely RED (~38 unregistered skills) then GREEN via the recorded dispatch_registration.txt Plan 07 burns"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §5 Task 11
  - workspace/lint/lint_vscode_tasks.py
  - workspace/lint/design_lint.py
  - skills/_shared/_run.cmd            # post-Plan-03 exit-propagation exemplar (read-only)
  - workflows/INDEX.md                 # dispatch table (read-only)
write_scope:
  - workspace/lint/lint_vscode_tasks.py
  - workspace/lint/design_lint.py
  - workspace/lint/whitelists/dispatch_registration.txt
acceptance_criteria:
  - "python workspace/lint/lint_vscode_tasks.py → exit 0 (T9 green post-Plan-03); planted unconditional 'exit /b 0' in skills/_shared/_run.cmd → exit 1 ERROR [T9]; reverted (paste red + green)"
  - "python workspace/lint/design_lint.py with empty dispatch whitelist → errors listing every unregistered skill (~38; recorded RED) and the PROCMON phantom row; with whitelist → exit 0"
  - "existing check functions in both files byte-identical (git diff shows appended code + runner wiring only)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "APPEND-only in both linters (do-not-rebuild #7); register the new checks in each file's runner exactly the way check_memory_domains (design_lint.py ~580) and the W-rules (lint_vscode_tasks.py) are registered"
  - "do NOT add dispatch rows to workflows/INDEX.md or fix the PROCMON row — Plan 07 decides register-vs-exempt per skill; this task ships tripwire + whitelist"
context_summary: |
  AW-41's exit-0-swallowing wrappers were fixed in Plan 03 — T9 pins that behavior. skills/
  design.md §4.9 requires every skill a dispatch row in workflows/INDEX.md, but design_lint's
  26 checks never enforce it and ~38 of 48 skills are unregistered (AW-47); Plan 07 registers
  the 9 project skills or documents exemptions. Runs after wfo-04-3 to serialize design_lint.py
  writes (wfo-04-1 → wfo-04-3 → this).
depends_on: ["wfo-04-3"]
```

- [ ] **Step 1: Append T9** to `lint_vscode_tasks.py` (self-contained function, wired into the existing W-rule runner):

```python
# ── wfo-04-11: rule T9 (AW-41 regression guard) ──────────────────────────
_T9_CMD_EXIT0 = re.compile(r"^\s*exit\s*/b\s*0\s*$", re.IGNORECASE | re.MULTILINE)
_T9_SH_EXIT0 = re.compile(r"^\s*exit\s+0\s*$", re.MULTILINE)


def check_t9_exit_propagation(repo_root) -> list[str]:
    """T9: no wrapper ends in an unconditional exit-0 that swallows _EC/rc."""
    errors: list[str] = []
    roots = [repo_root / "skills", repo_root / "workspace" / "lint"]
    for root in roots:
        if not root.is_dir():
            continue
        for w in sorted(root.rglob("_run.cmd")) + sorted(root.rglob("*_task.cmd")):
            text = w.read_text(encoding="utf-8", errors="replace")
            if _T9_CMD_EXIT0.search(text) and "%_EC%" not in text.split(
                    _T9_CMD_EXIT0.search(text).group(0))[0][-200:]:
                errors.append(f"[T9] {w.relative_to(repo_root).as_posix()}: "
                              f"unconditional 'exit /b 0' swallows the exit code "
                              f"— propagate %_EC% (AW-41, fixed in Plan 03)")
        for w in sorted(root.rglob("_run.sh")) + sorted(root.rglob("*_task.sh")):
            text = w.read_text(encoding="utf-8", errors="replace")
            tail = "\n".join(text.splitlines()[-5:])
            if _T9_SH_EXIT0.search(tail) and "$_EC" not in tail and "$rc" not in tail:
                errors.append(f"[T9] {w.relative_to(repo_root).as_posix()}: "
                              f"unconditional 'exit 0' swallows the exit code")
    return errors
```

- [ ] **Step 2: Append the §4.9 check** to `design_lint.py`:

```python
# ── wfo-04-11: §4.9 skill-dispatch registration (AW-47 lint half) ────────
_DISPATCH_WHITELIST = Path(__file__).resolve().parent / "whitelists" / \
    "dispatch_registration.txt"


def check_skill_dispatch_registration(repo_root) -> list[tuple[str, str, str]]:
    """design.md §4.9: every skill needs a workflows/INDEX.md dispatch row
    (or a recorded exemption — Plan 07 burns the whitelist down)."""
    results: list[tuple[str, str, str]] = []
    wl = set()
    if _DISPATCH_WHITELIST.is_file():
        wl = {ln.strip() for ln in
              _DISPATCH_WHITELIST.read_text(encoding="utf-8").splitlines()
              if ln.strip() and not ln.startswith("#")}
    index = repo_root / "workflows" / "INDEX.md"
    dispatch_text = index.read_text(encoding="utf-8", errors="replace") \
        if index.is_file() else ""
    skills = sorted(p.parent.name for p in
                    (repo_root / "skills").glob("*/SKILL.md"))
    for name in skills:
        if name in wl:
            continue
        if not re.search(rf"\b{re.escape(name)}\b", dispatch_text):
            results.append(("ERROR", "skill-dispatch",
                f"skills/{name}/ has no dispatch row in workflows/INDEX.md "
                f"(design.md §4.9) and no recorded exemption"))
    # phantom rows: dispatch names that resolve to no skill dir
    for m in re.finditer(r"\b([A-Z][A-Z0-9_]{2,})\b", dispatch_text):
        cand = m.group(1)
        if cand not in skills and (repo_root / "skills").is_dir() and \
                re.search(rf"skills?\W*{cand}", dispatch_text) is None and \
                cand in {"PROCMON"}:
            results.append(("ERROR", "skill-dispatch",
                f"workflows/INDEX.md dispatch row names '{cand}' but no "
                f"skills/{cand}/ exists (use PROCMON_JOBS/PROCMON_LOGS)"))
    return results
```

Wire both functions into their runners following each file's existing registration pattern (design_lint: same list/loop `check_memory_domains` sits in; vscode_tasks: same place the W-rules are invoked). Adjust the two functions' signatures to whatever those runners actually pass (repo_root vs no-arg with module global) — note any adaptation in `notes`.
- [ ] **Step 3 (T9 planted RED):** run `lint_vscode_tasks.py` → exit 0. Append a final unconditional `exit /b 0` line to `skills/_shared/_run.cmd` (after the existing `%_EC%` propagation); run → `ERROR [T9]`; revert (`git checkout -- skills/_shared/_run.cmd`); re-run green. Paste all three.
- [ ] **Step 4 (§4.9 genuine RED → GREEN):** Create `workspace/lint/whitelists/dispatch_registration.txt` with header only (`# dispatch_registration.txt — skills without a workflows/INDEX.md dispatch row.` / `# Plan 07 registers the project skills or converts entries to documented exemptions,` / `# burning this file down. Only shrinks. One UPPER_SNAKE skill-dir name per line.`). Run `design_lint.py` → ~38 `[skill-dispatch]` errors + the PROCMON phantom (recorded RED — **the failing test**). Append every flagged skill name (NOT the PROCMON phantom — fix nothing, but the phantom row error will remain red…: the PROCMON phantom IS pre-existing content that Plan 07 fixes, so ALSO whitelist it as the literal line `PROCMON-phantom-row` and add a matching `if "PROCMON-phantom-row" in wl: skip` guard clause in the phantom check). Re-run → exit 0. Paste both runs.
- [ ] **Step 5: Commit** — `chore(lint): add T9 exit-propagation rule and design_lint §4.9 dispatch-registration check (grandfathered for Plan 07)`

---

## §6 Wave D — registration and triggers

## Task 12: Register the six new checks in `LINTS` and prove the suite green on both surfaces

**Files:** Modify `workspace/lint/lint_all.py` (append 6 tuples — nothing else).

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-12"
goal: "lint_all.py's LINTS registry grows from 15 to 21 tuples and the full suite reports ALL PASSED (21 checks) via the sanctioned execution vehicle on S-A and S-B"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §6 Task 12
  - workspace/lint/lint_all.py
write_scope:
  - workspace/lint/lint_all.py
acceptance_criteria:
  - "S-A: run_task lint-workspace (args {} in workspace/tmp/lint_args.json) → OUTPUT_FILE contains 'ALL PASSED (21 checks' and EXIT_CODE=0"
  - "S-B: ./vol exec 'python workspace/lint/lint_all.py' → OUTPUT_FILE contains 'ALL PASSED (21 checks' and EXIT_CODE=0"
  - "python workspace/lint/lint_all.py --check 'model pins' runs exactly one lint (single-check plumbing works for a new tuple)"
  - "git diff workspace/lint/lint_all.py shows ONLY the 6 appended tuples"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "append AFTER the 15th tuple (Plan 01's `secrets`), matching the existing multi-line tuple literal format exactly; never reorder or edit existing tuples"
  - "if either surface's run is impossible this sitting (e.g. S-B box unavailable), tag the criterion per-surface and return partial with the completed surface's evidence — never claim both"
context_summary: |
  All six new lint modules and three extensions exist and are individually green (Tasks 4-11).
  This task is the single sanctioned LINTS-append point (00-overview §7 serialization rule).
  After it, 'lint stays green' becomes the standing gate every later plan inherits.
depends_on: ["wfo-04-4", "wfo-04-5", "wfo-04-6", "wfo-04-7", "wfo-04-8", "wfo-04-9", "wfo-04-10", "wfo-04-11"]
```

- [ ] **Step 1 (red — unregistered proof):** `python workspace/lint/lint_all.py` → `ALL PASSED (15 checks` — the new lints are NOT yet counted (this is the "failing" state for registration: the gate does not yet see them). Paste.
- [ ] **Step 2: Append** after the final registered tuple (Plan 01's `("secrets", …)` — the 15th), in the file's exact existing format:

```python
    (
        "args contract",
        TOOLS_DIR / "lint_args_contract.py",
        [],
        False,
        False,
    ),
    (
        "model pins",
        TOOLS_DIR / "lint_model_pins.py",
        [],
        False,
        False,
    ),
    (
        "wrapper targets",
        TOOLS_DIR / "lint_wrapper_targets.py",
        [],
        False,
        False,
    ),
    (
        "vol parity",
        TOOLS_DIR / "lint_vol_parity.py",
        [],
        False,
        False,
    ),
    (
        "prompts",
        TOOLS_DIR / "lint_prompts.py",
        [],
        False,
        False,
    ),
    (
        "canonical schema",
        TOOLS_DIR / "lint_canonical_schema.py",
        [],
        False,
        False,
    ),
```

- [ ] **Step 3 (green, both surfaces):** S-A: write `{}` to `workspace/tmp/lint_args.json`, `run_task("lint-workspace")`, `read_file` the sentinel `OUTPUT_FILE=` path → `ALL PASSED (21 checks` + `EXIT_CODE=0`. S-B: `./vol exec "python workspace/lint/lint_all.py"` → same. Also run `python workspace/lint/lint_all.py --check "model pins"` → single-check pass. Paste all outputs (kill spawned terminals — EXIT GATE).
- [ ] **Step 4: Commit** — `chore(lint): register 6 new checks — gate is now 21 wide`

## Task 13: Triggers — local pre-commit for real, pins fixed, scopes aligned (AW-44, AW-G29, AW-G30)

**Files:** Modify `.pre-commit-config.yaml`, `AGENTS.md` (one Environment line), and the Gate-C CI file (`.gitlab-ci.yml` or `.github/workflows/ci.yml` — substitute the recorded Gate-C winner from Plan 02).

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-13"
goal: "Committing runs workspace/lint/lint_all.py plus correctly-pinned, src/-scoped ruff/mypy via pre-commit, agents are told the hooks exist, and the Gate-C CI home runs the same lint server-side"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §6 Task 13
  - .pre-commit-config.yaml
  - src/pyproject.toml            # [tool.ruff]/[tool.mypy] + locked versions (read-only)
  - src/uv.lock                   # ruff 0.15.12 (~:2856), mypy 2.0.0 (~:1740) (read-only)
  - AGENTS.md
write_scope:
  - .pre-commit-config.yaml
  - AGENTS.md
  - "<Gate-C CI file: .gitlab-ci.yml OR .github/workflows/ci.yml — exactly one, per Plan 02's recorded decision>"
acceptance_criteria:
  - "pre-commit run --all-files → workspace-lint hook Passed (paste)"
  - "git ls-remote --tags output pasted for BOTH pins: ruff-pre-commit v0.15.12 (must exist) and mirrors-mypy v2.0.0 (if ABSENT: mypy hook block deleted + noted — AW-44 caveat)"
  - "grep -c 'files: ^src/' .pre-commit-config.yaml → one per surviving ruff/ruff-format/mypy hook (G29/G30)"
  - "grep -c 'config-file=src/pyproject.toml' .pre-commit-config.yaml → 1 if the mypy hook survives, else 0"
  - "the Gate-C CI file runs python workspace/lint/lint_all.py as a BLOCKING gate — GitLab: the pre-existing workspace-lint job now has allow_failure: false and there is exactly ONE such job (grep -c 'workspace-lint:' .gitlab-ci.yml → 1); ci.yml: a lint step is present"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "self-modification hazard: the AGENTS.md addition is ONE line in the Environment section; quote the surrounding lines as-of-execution in your return; if Plan 02's rewritten Environment section doesn't match expectations, STOP and return blocked with the diff"
  - "network fallback: if the GS box cannot fetch github.com hook repos (pre-commit install-hooks fails), DELETE the ruff and mypy remote-repo blocks (AW-44's sanctioned delete option), keep the local workspace-lint hook (language: system, zero network), and record the decision in notes"
context_summary: |
  The 15-check suite had no deterministic trigger (AW-21) and pre-commit pinned ruff v0.4.4 /
  mypy v1.10.0 against locked 0.15.12 / 2.0.0 (AW-44), ran them repo-wide from root so
  out-of-src files got default config (G30) and mypy lost check_untyped_defs (G29). Plan 02
  decided the CI home at Gate C — substitute that recorded winner; do not relitigate it.
depends_on: ["wfo-04-12"]
```

**Config (complete file, verbatim — the plan's one shipped config):**

```yaml
# .pre-commit-config.yaml — rewritten by wfo-04-13 (AW-21 trigger / AW-44 pins / G29-G30 scoping)
#
# Hypothesis: a local `repo: local` hook is the only trigger that cannot rot —
#   it needs no CI runner, no network, no branch-name match (AW-21's CI trigger
#   never fired because push was [main,develop] on a master repo).
# Expected-outcome prior (00-overview §4): 3/15 failing suite → full 21-check PASS
#   enforced at every commit; planted violation rejected (Plan-04 gate, proven in wfo-04-14).
# Decision rule: if `git ls-remote --tags https://github.com/pre-commit/mirrors-mypy`
#   shows no v2.0.0 tag, DELETE the mypy block (AW-44 verbatim caveat) — never pin a
#   phantom tag; if github.com is unreachable from the GS box, delete BOTH remote
#   blocks and keep only the local hook. Record either decision in the MR.
repos:
  - repo: local
    hooks:
      - id: workspace-lint
        name: workspace governance lint (lint_all.py, 21 checks)
        entry: python workspace/lint/lint_all.py
        language: system
        pass_filenames: false
        always_run: true

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12            # == src/uv.lock ruff (AW-44); verify tag before commit
    hooks:
      - id: ruff
        args: [--fix]
        files: ^src/.*\.py$   # G30: same tree CI/./vol lint covers, same config
      - id: ruff-format
        files: ^src/.*\.py$

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-yaml
      - id: check-toml
      - id: end-of-file-fixer
      - id: trailing-whitespace

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v2.0.0              # == src/uv.lock mypy — DELETE THIS BLOCK if tag absent (AW-44)
    hooks:
      - id: mypy
        additional_dependencies: [numpy, pandas-stubs]
        args: [--config-file=src/pyproject.toml, --ignore-missing-imports]  # G29
        files: ^src/.*\.py$
```

- [ ] **Step 1 (verify tags BEFORE pinning — AW-44 caveat):** `git ls-remote --tags https://github.com/astral-sh/ruff-pre-commit refs/tags/v0.15.12` and `git ls-remote --tags https://github.com/pre-commit/mirrors-mypy refs/tags/v2.0.0`. Paste both outputs. Empty mypy result → delete the mirrors-mypy block from the config above and note it. Empty ruff result → pin the newest available `v0.15.x` tag and note the reconciliation. Network failure → apply the packet's network fallback.
- [ ] **Step 2:** Write the config (as adjusted by Step 1). Run `pre-commit install` then `pre-commit run --all-files`. Expected: `workspace-lint … Passed` (plus the surviving remote hooks). Paste. (RED precondition for the trigger itself is proven end-to-end in wfo-04-14.)
- [ ] **Step 3 (one-line doc):** In `AGENTS.md`'s Environment section (as rewritten by Plan 02), append: `- Git hooks: run \`pre-commit install\` once per clone — every commit then runs \`workspace/lint/lint_all.py\` (21 checks) plus ruff/ruff-format/mypy scoped to \`src/\`; hooks may mutate staged files and use a separate env from \`./vol\`.`
- [ ] **Step 4 (server-side, Gate-C winner):** If Gate C chose **GitLab**: the `workspace-lint` job already EXISTS in `.gitlab-ci.yml` (Plan 02's Gate-C=GitLab branch created it with `allow_failure: true` and a `# Plan 04 flips this to false when lint goes green` comment — per 00-overview §6a). MODIFY that job in place: flip `allow_failure: true` → `allow_failure: false` and delete the "Plan 04 flips" comment. Do NOT append a second `workspace-lint` job. If Gate C chose **mirror-only ci.yml**: add the step `- name: Workspace governance lint` / `run: python workspace/lint/lint_all.py` (repo root, NOT `working-directory: src`) to the existing job, relying on Plan 02's already-fixed branch trigger. Exactly one of the two.
- [ ] **Step 5: Commit** — `chore(ci): pre-commit runs the 21-check gate; ruff/mypy re-pinned to locked versions and scoped to src/`

## Task 14: Prove the trigger live — planted violation rejected, then reverted

**Files:** Temporary edit to `workflows/INDEX.md` (reverted — zero net diff); evidence pasted to return contract + MR description.

**Copilot context packet:**

```yaml
subtask_id: "wfo-04-14"
goal: "A deliberately planted violation is REJECTED by the pre-commit trigger at an actual git commit attempt, the plant is reverted, and a clean commit passes — the Plan-04 gate's live-trigger proof"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md   # §6 Task 14
  - workflows/INDEX.md
write_scope:
  - workflows/INDEX.md   # planted line only — MUST be reverted; net diff zero
acceptance_criteria:
  - "git commit attempt with the planted line → non-zero exit, output shows workspace-lint … Failed with the model-pins ERROR (paste)"
  - "git log -1 --oneline unchanged by the failed attempt (paste before/after)"
  - "after revert: git status clean for workflows/INDEX.md and a subsequent real commit (or pre-commit run --all-files) passes (paste)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "the plant must NEVER be committed: if the hook unexpectedly passes, git reset HEAD~1 is FORBIDDEN — instead verify nothing was committed, revert the plant, and return blocked with the full hook output"
  - "run on the branch chore/wf-overhaul-04-lint-gate only"
context_summary: |
  The gate requires the trigger proven live, not assumed: wfo-04-13 installed the hook; this
  task plants a raw model literal (a violation lint_model_pins cannot miss and no whitelist
  covers — workflows/INDEX.md is grandfathered as a FILE only if it appeared in wfo-04-5's
  red run; if it did, plant in a non-whitelisted file instead, e.g. a new line in
  workspace/lint/whitelists/README-check.md scratch — pick any scanned file absent from
  model_pins.txt and name it in notes).
depends_on: ["wfo-04-13"]
```

- [ ] **Step 1 (choose the plant site):** Pick a file scanned by `lint_model_pins.py` that is NOT in `workspace/lint/whitelists/model_pins.txt` (default: `workflows/INDEX.md`; verify with `grep -c 'workflows/INDEX.md' workspace/lint/whitelists/model_pins.txt` → 0, else pick another and note it).
- [ ] **Step 2 (plant + RED):** Append the line `Planted for wfo-04-14: subagents run on Claude Opus 4.6.` to the chosen file. `git add <file>`, `git log -1 --oneline` (record), then `git commit -m "tmp: wfo-04-14 planted violation probe"`. Expected: commit REJECTED — `workspace-lint … Failed`, output contains `ERROR [raw-literal]` naming the planted line, and `git log -1 --oneline` is unchanged. Paste everything.
- [ ] **Step 3 (revert + GREEN):** `git checkout -- <file>` (and `git reset <file>` to unstage). `pre-commit run --all-files` → all hooks pass. Paste. Confirm `git status` shows no residue.
- [ ] **Step 4: Commit** — nothing to commit (net-zero task). Record the evidence block in the MR description under "Planted-violation proof (Plan-04 gate)".

---

## §7 Configs / experiments

This plan ships one runnable config — the rewritten `.pre-commit-config.yaml` — presented complete with hypothesis, prior, and decision rule inline in Task 13. No ML experiment configs; no launch commands beyond the lint/pre-commit invocations already embedded in the tasks (all printed there, executed by the tasked subagents as their own acceptance evidence).

## §8 Findings disposed by this plan

| AW-ID | Disposition here |
|---|---|
| AW-21 | wfo-04-1 (all three failures atomically) + wfo-04-13/14 (deterministic trigger, proven live) |
| AW-44 | wfo-04-13 (re-pin ruff 0.15.12; mypy tag verified-else-deleted; hooks documented) |
| AW-G29 | wfo-04-13 (`--config-file=src/pyproject.toml`, `files: ^src/`) |
| AW-G30 | wfo-04-13 (`files: ^src/` on ruff/ruff-format — three surfaces cover the same tree) |
| AW-04 lint half | wfo-04-4 (`lint_args_contract.py`) |
| AW-12 lint half | wfo-04-9 (broken-refs plain-text + `_dormant` awareness; content fix = Plan 06) |
| AW-15 lint half | wfo-04-2 (bytes/4 math + path existence; content fix = Plan 06) |
| AW-20 lint half | wfo-04-10 (`lint_canonical_schema.py`; regeneration = Plan 06) |
| AW-23/G3 lint half | wfo-04-5 (`lint_model_pins.py` + `EXPECTED_MODEL`; rationalization = Plans 05/07) |
| AW-47 lint half | wfo-04-11 (design_lint §4.9 check; registration/exemptions = Plan 07) |
| AW-49 link half | wfo-04-1 (AGENTS.md:58 backtick; writer-or-delete = Plan 05) |
| AW-55/G6/G16 lint half | wfo-04-7 (`lint_vol_parity.py`; doc regeneration landed in Plan 03) |
| AW-41 regression guard | wfo-04-11 (rule T9; the fix itself landed in Plan 03) |
| governance-map Part 3 | wfo-04-3 (10-domain collapse, research cap, uniform `_dormant` policy) |

## §9 Orchestrator prompt

```
/execute Implement Plan 04 (Lint Gate Real and Green) from workspace/plans/copilot-workflow-overhaul/plan-04-lint-gate.md

Precondition check: Gate D passed — on S-A, vol.cmd test -x -q and the lint-workspace task
produced sentinel OUTPUT_FILEs with EXIT_CODE=0; on S-B, ./vol test green (paste the Plan-03
MR's gate evidence or re-run). Also verify no research /execute session is live.
Branch: chore/wf-overhaul-04-lint-gate off master (rebase onto origin/master before push).
Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1: wfo-04-1, wfo-04-2                      # disjoint write_scopes
  Wave 2 (parallel, max 5): wfo-04-3, wfo-04-4, wfo-04-5, wfo-04-6, wfo-04-7
  Wave 3 (parallel, max 4): wfo-04-8, wfo-04-9, wfo-04-10, wfo-04-11
  Wave 4: wfo-04-12                               # LINTS registration — sole append point, runs alone
  Wave 5: wfo-04-13                               # pre-commit trigger — depends_on wfo-04-12
  Wave 6: wfo-04-14                               # planted-violation proof — depends_on wfo-04-13
Each subagent: red-then-green evidence pasted into the return contract's verification field
(planted-red where the companion fix already landed; whitelist-red where content lands in
Plans 05/06/07), terminal isolation via ./vol exec / vol.cmd exec with isBackground=true,
kill_terminal before returning (EXIT GATE), and return the 00-overview §5.2 return contract
verbatim.
Retry a blocked/partial subagent once with a refined packet (add the first attempt's
diagnostics), then escalate to the user with evidence from both attempts.
Integration verification (orchestrator, after all tasks):
  1. python workspace/lint/lint_all.py → 'ALL PASSED (21 checks' on S-A (lint-workspace task
     sentinel) AND on S-B (./vol exec) — tag each criterion with its surface.
  2. Aggregate every task's red-then-green evidence into the MR description (one subsection
     per new/changed check), plus wfo-04-14's planted-violation proof.
  3. git diff origin/master --stat contains NO file under workspace/plans/ other than this
     suite's own directory, and no trials.yaml / workspace/configs changes.
Update workspace/research/weekly-progress.md (Shipped section, one line).
MR title (human-generic): "Make the workspace lint suite green, honest, and enforced at commit".
Do NOT start Plan 05.
```

## §10 Acceptance gate → Plan 05

Verbatim from 00-overview §2 (Plan 04 row): **`python workspace/lint/lint_all.py` full PASS (15 + N new checks) on S-A and S-B; every NEW check has recorded red-then-green evidence; a deliberately planted violation is rejected by the pre-commit trigger (trigger proven live, then reverted)** — with N = 6 (registry width 21).

Checklist before opening Plan 05:
1. Both surfaces' `ALL PASSED (21 checks` outputs pasted in the MR (per-surface tags if one box was unavailable — then the missing surface is a named follow-up, not silently skipped).
2. Red-then-green evidence recorded in the MR for ALL of: the 3/15 fix (wfo-04-1), budget math (wfo-04-2), domain/planted-domain runs (wfo-04-3), and each of the 9 new/extended checks (wfo-04-4…11).
3. wfo-04-14's rejected-commit transcript in the MR; working tree net-clean of the plant.
4. Whitelist inventory table in the MR: each `workspace/lint/whitelists/*.txt` file, its entry count, and the plan that burns it (budget_grandfather + broken_refs + canonical_schema → Plan 06; model_pins → Plans 05/07; prompts + dispatch_registration → Plan 07). **Plan 05 consumes:** the standing green gate, `EXPECTED_MODEL` in `lint_model_pins.py`, and the model_pins whitelist as its prose-literal work-list. The two canonical model-pin prose sites (`policy/subagent_protocol.md` + `.github/copilot-instructions.md` Rule 9) are structurally exempt via `SANCTIONED_SITES` in `lint_model_pins.py` — NOT whitelist entries — so `model_pins.txt` burns fully EMPTY (Plan 05 partial → Plan 07 empty; two canonical sites exempt via SANCTIONED_SITES). **Plans 06/07 consume** their whitelists as enumerated work-lists — burning each file to empty is part of THOSE plans' acceptance.
5. MR merged to master; branch cleaned up; one-line Shipped entry in `workspace/research/weekly-progress.md`.
