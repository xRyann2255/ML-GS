# Plan 08 — Deferred Relocation & Suite Closure

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §8.
> Dispatch each task as a subagent with the context packet provided. Max 4 concurrent subagents.
> TDD is a hard gate (`.github/copilot-instructions.md` Rule 5) for the two Python deliverables
> (`check_coverage.py`, and `select_nodes.py` if Gate E Option 1 is chosen); every other task in
> this plan is config/docs/YAML and is Rule-5-exempt. Requires Plans 01–07 merged (Gate on Plan 07
> passed) **and the Gate E user decision recorded before Wave 1 is dispatched**.

**Goal:** Dispose the last four audit findings (AW-24 CONTESTED, AW-40, AW-G17, AW-G31) via the user's Gate E decision, then close the suite with script-asserted 84/84 findings coverage, a full green lint + test run, and a recorded final boot-token measurement.

**Architecture:** This plan plugs into three seams the earlier plans built: (1) the coverage-matrix block in `00-overview.md` §9 (`COVERAGE-MATRIX:BEGIN/END` markers) becomes machine-checked by the new `check_coverage.py`, exactly per its interface-ledger row; (2) the Gate E Option-1 selector writes its output through the existing sentinel convention (`OUTPUT_FILE=` line) and its `/study`–`/learning` prompt rewrites obey the Plan-07 prompt contract (`lint_prompts.py`: `[a-z0-9-]+\.prompt\.md` filenames, INDEX.md bijection, instruction verb in every body, bare backtick paths — never Markdown links); (3) the AW-G31 doc correction edits the `vol` help heredoc and `memory/ref/vol-cli.md` **as a pair**, because Plan 04's `lint_vol_parity.py` holds them in lockstep. No always-on rule file is touched by this plan — the self-modification hazard is dormant here.

**Tech stack:** No new dependencies. `check_coverage.py` is stdlib-only (mirrors the `workspace/lint/` suite style). `select_nodes.py` (Option 1 only) uses PyYAML, which the project environment already carries (every experiment config is YAML).

**Research grounding:** Audit findings AW-24 (HIGH · context · **CONTESTED — the only finding of 84 whose adversarial verifier did not confirm it**; per-session cost measured at 194,412 B graph ≈ 48,603 t + 21,984 B state ≈ 5,496 t ≈ ~54k t ≈ 27% of a 200k window), AW-40 (MEDIUM · 6 of 34 slash commands + ~490 KB tracked tutoring state + a generated dashboard.html in a team-visible tree), AW-G17 (LOW · 15 tracked one-off scripts in `workspace/scripts/`, verifier guardrail: **do NOT delete** — it is the AGENTS.md:168-sanctioned "Build here" tree, referenced by `workspace/docs/gsvivs_audit_results.md:165` and `workspace/plans/plan-b-enriched-5min-lstm.md:163/436`; the one broken artifact is `trials.yaml:1144`'s dangling `script:` path), AW-G31 (LOW · verifier **inverted the primary fix**: un-ignoring `tests/slow` would break CI because those tests need real data absent on runners — only the doc-correction alternative is in scope), and strategic move S7. Expected-outcome priors: Option 1 saves **~40k tokens per /study session** (audit estimate); findings disposed **84/84 script-asserted**; final boot load ≈ **~7,500 t directional** (vs ~10,235 t pre-suite). Calibration warning (overview §4 sanity rule): bytes/4 is crude — a measurement far better than the prior means the measurement is wrong or load-bearing content was deleted; investigate before celebrating. Token numbers are directional acceptance evidence, never hard gates.

---

## 1. Global constraints

All shared conventions from `workspace/plans/copilot-workflow-overhaul/00-overview.md` §5 apply (packet schema union, return contract, the 9 HARD rules, git/MR conventions). Plan-specific hard rules:

1. **Gate E has NO default.** The orchestrator must obtain an explicit user choice (Option 1 / 2 / 3, plus the G17 sub-decision) before dispatching Wave 1. If the user is unavailable, stop — do not infer a choice from the plan text.
2. **Drift check (standing):** verify every cited path:line against the live tree before editing; if it moved, locate by content and note the delta in your return. This suite was written against a mirror verified byte-identical on 2026-07-07.
3. **The 5 ACTIVE research plans** in `workspace/plans/` (`bug3-iv-context-fix`, `gnn-gpu-parallel-plan`, `linear-alpha-tuning`, `plan-c-prediction-blending`, `trial-068-conditional-duan`) are read-only. `trials.yaml` is no-touch **except** Task 1, which edits exactly one field at line ~1144 and nothing else.
4. **`./vol` semantics untouched:** Task 3 edits only the help heredoc *text* for `test-all`; the `exec`/`bg`/sentinel machinery and every dispatch arm stay byte-identical. `--ignore=tests/slow` in `src/pyproject.toml` addopts is **kept** (AW-G31 do-NOT).
5. **Overview edits are confined to the §9 matrix block** (Plan and Notes cells of the four Plan-08 rows, and — Option 3 only — their disposition) plus the per-plan totals line. Task 5 is the sole owner of that file in this plan.
6. **Never load `workspace/learning/graph.yaml` in full** into any subagent's context (that is the AW-24 defect itself). Schema confirmation reads the first ~80 lines only.
7. Branch: `chore/wf-overhaul-08-closure` off `master`; rebase onto `origin/master` before push; MR-only; never `git add -A`; denied paths never staged (`workspace/docs/enghub/`, `workspace/tmp/`, `__pycache__/`, `*.pyc`).
8. Terminal isolation + cleanup EXIT GATE per overview §5.3 rules 3–4 on every task.

---

## 2. Gate E — the decision this plan opens with

The orchestrator presents this section to the user verbatim and records the answers in the session log before Wave 1. **User chooses; no default is enforced.**

**Decision E-main — tutoring machinery (AW-24 + AW-40):**

| Option | What happens | Cost/benefit |
|---|---|---|
| **1 — Collapse + selector** (the cheap AW-24 variant) | Keep tutoring in-repo. Collapse the 6 tutoring slash commands to `/study` + one `/learning`; ship `workspace/learning/select_nodes.py` so `/study` loads a ~5-node slice (~a few KB) instead of the 194 KB graph. Dispatches **Task 2A**. | Saves ~40k t/session (audit prior); one new tested script; tutoring stays team-visible (AW-40 only shrinks) |
| **2 — Relocate out of the work repo** (S7) | Remove the ~490 KB `workspace/learning/` tree and all 6 tutoring prompts from the repo; bundle content to `workspace/tmp/learning-relocation/` for the user to move into their VS Code user-profile prompts (user action U1). Dispatches **Task 2B**. | Kills AW-24 and AW-40 outright; tutoring survives only user-side; no new code |
| **3 — WONTFIX both, with reasons** | Legitimate: AW-24 is the audit's **sole contested finding** (its adversarial verifier did not confirm it — record this counter-evidence in the Notes cell). No Task 2 runs; Task 5 writes `WONTFIX` rows for AW-24 and AW-40 with the user's stated reasons. | Zero work now; the ~54k t/session /study cost and the 490 KB footprint are consciously accepted and documented |

**Decision E-sub — `workspace/scripts/` (AW-G17): archive or sanction?**
- **sanction (recommended, matches the verifier guardrail):** keep the 15 scripts in place, add a `README.md` documenting them as the ordered idempotent pipeline the docs already describe.
- **archive:** `git mv` the 15 scripts to `workspace/scripts/archive/` (README still added; `trials.yaml` path fix then points into `archive/`).

Either way Task 1 also fixes the dangling `trials.yaml:1144` `script:` path and gitignores + untracks the generated `dashboard.html` (skip the dashboard step under Option 2 — the file is removed with the tree).

**Record:** chosen option, chosen sub-decision, and (Option 3 only) the user's WONTFIX reason sentences for AW-24 and AW-40 — Task 5 pastes them verbatim into the matrix Notes cells.

---

## 3. File map

| Action | Path | Responsibility |
|---|---|---|
| Create | `workspace/scripts/README.md` | Sanction/archive record for the 15 analysis scripts (AW-G17) |
| Modify | `workspace/research/trials.yaml` (line ~1144 only) | Fix trial-042's dangling `script:` path to the real filename |
| Modify | `.gitignore` | Add the generated learning dashboard (skip under Gate E Option 2) |
| Create (Opt 1) | `workspace/learning/select_nodes.py` | Due+frontier node selector; writes `workspace/tmp/study_nodes.yaml` |
| Create (Opt 1) | `workspace/learning/test_select_nodes.py` | TDD tests for the selector (fixture-driven, REAL schema) |
| Modify (Opt 1) | `workspace/learning/generate_dashboard.py` | Factor path-param loaders + the shared due+frontier helper the selector reuses (no re-derivation) |
| Modify (Opt 1) | `.github/prompts/study.prompt.md` | Body rewritten to run the selector and load the slice, never the graph |
| Create (Opt 1) | `.github/prompts/learning.prompt.md` | Consolidated quiz/teach/progress modes |
| Delete (Opt 1) | 4 tutoring prompts (all `workspace/learning/`-loading prompts except study; names confirmed at execution) | Collapse 6 → 2 |
| Modify (Opt 1) | `skills/design.md`, `skills/INDEX.md` | Reconcile the guide-skill roster/rows after tutoring-prompt retirement (route via /study + /learning) |
| Delete (Opt 2) | `workspace/learning/` (entire tree) + all 6 tutoring prompts | Relocation out of the work repo |
| Modify (Opt 1/2) | `.github/prompts/INDEX.md` | Registry rows updated (Plan-07 bijection lint holds it) |
| Modify (Opt 2) | `memory/INDEX.md` | Delete `workspace/learning/` rows (e.g. line ~112 graph.yaml) |
| Modify | `vol` (help heredoc text only) | `test-all` description names the `tests/slow` exclusion (AW-G31) |
| Modify | `src/pyproject.toml` (comments only) | addopts comment explains the two "slow" mechanisms |
| Modify | `memory/ref/vol-cli.md` | `test-all` row matches the new help text (`lint_vol_parity.py` pair) |
| Create | `workspace/plans/copilot-workflow-overhaul/check_coverage.py` | Suite-closure gate: 84/84 AW-IDs disposed exactly once |
| Create | `workspace/plans/copilot-workflow-overhaul/test_check_coverage.py` | TDD fixture matrix for the checker |
| Modify | `workspace/plans/copilot-workflow-overhaul/00-overview.md` (§9 block only) | Final `/T` refs; WONTFIX rows + Notes per Gate E |
| Modify | `workspace/research/weekly-progress.md` | One Shipped line closing the suite |

---

## 4. Interfaces

**Consumes (copied from the overview §6 ledger — do not re-derive):**
- `check_coverage.py` ledger row: lives at `workspace/plans/copilot-workflow-overhaul/`; asserts every AW-ID in §9 appears exactly once with disposition ∈ {plan-task, WONTFIX}; exit 1 on gap/dupe; run at Plan 08 closure.
- `S-B` compute: `./vol` all arms; sanctioned arbitrary-python form is `./vol exec python …` (sentinel: `workspace/tmp/exec/<ts>_<pid>.out` with `OUTPUT_FILE=`/`EXIT_CODE=` lines).
- `S-A` compute: `vol.cmd` (Plan 03) with 10 arms — `test`, `test-all`, `testlf`, `lint`, `fmt`, `typecheck`, `exec`, `bg`, `jobs`, `help` (`help` exits 0 and is the no-arg default; every OTHER arm → exit 2), same sentinel protocol; plus the `lint-workspace` VS Code task.
- `LINTS` registry / `python workspace/lint/lint_all.py` full-suite run (Plan 04 gate, standing).
- `lint_vol_parity.py` (Plan 04): `vol` help heredoc ↔ `memory/ref/vol-cli.md` command-for-command parity.
- `lint_prompts.py` (Plan 04/07): prompt filenames `[a-z0-9-]+\.prompt\.md`; `INDEX.md` ↔ directory bijection; every body has an instruction verb; frontmatter `model:` matches `lint_model_pins.EXPECTED_MODEL` where pinned.
- `.github/prompts/INDEX.md` (Plan 07): registry table prompt → description → dispatches-to.
- Boot measurement definition: bytes/4 over the 5 always-on/boot files (`.github/copilot-instructions.md`, `AGENTS.md`, `memory/person/user.md`, `memory/research/project-state.md`, `memory/INDEX.md`); Plan 06 recorded the ≤ ~7,500 t directional value this plan re-measures against.
- Gate E definition (overview §2 Plan-08 row); `subtask_id` format `wfo-<NN>-<M>`; branch format `chore/wf-overhaul-NN-<topic>`.

**Produces (added to the ledger):**
- `check_coverage.py` CLI: `python workspace/plans/copilot-workflow-overhaul/check_coverage.py [--overview PATH]` (default: sibling `00-overview.md`) → exit 0 printing `OK: 84/84 AW-IDs disposed exactly once`, or exit 1 with one `FAIL: <defect>` line each. Disposition grammar (concretizes the ledger row): Plan cell matches `^(0[1-8])(/T\d+)?$` (plan-task) **or** is the literal `WONTFIX` with a non-empty Notes cell. Expected-ID universe frozen in-module: `AW-01`…`AW-55` + `AW-G2`…`AW-G31` minus `AW-G21` = 84.
- (Gate E Option 1 only) `workspace/learning/select_nodes.py` CLI: `python workspace/learning/select_nodes.py [--max-nodes 5] [--graph PATH] [--state PATH] [--out PATH] [--today YYYY-MM-DD]` → writes `workspace/tmp/study_nodes.yaml` and prints `OUTPUT_FILE=<path>` + `SELECTED=<n> of <max> max (due+frontier)`.
- (Gate E Option 1 only) `/learning` prompt at `.github/prompts/learning.prompt.md` (modes: quiz / teach / progress).

---

## 5. Tasks

### Task 0: Gate E decision (USER — no packet, no subagent)

Present §2 verbatim; record E-main (Option 1/2/3), E-sub (sanction/archive), and — Option 3 — the two WONTFIX reason sentences. Acceptance = the orchestrator restates the recorded decision and the user confirms it. **Nothing in Wave 1 dispatches before this.**

---

### Task 1: workspace/scripts sanction + trials.yaml path fix + dashboard gitignore (AW-G17)

**Files:** Create `workspace/scripts/README.md` · Modify `workspace/research/trials.yaml` (one field, line ~1144) · Modify `.gitignore` (one line; skip under Gate E Option 2). TDD-exempt (docs/config/YAML).

**Copilot context packet:**

```yaml
subtask_id: "wfo-08-1"
goal: "workspace/scripts/ carries a README sanctioning (or archiving) the 15 analysis scripts, trial-042's script: path resolves to a real file, and the generated learning dashboard is untracked+ignored"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-08-closure.md   # Task 1 section
  - workspace/scripts/                                             # inventory the 15 scripts
  - workspace/research/trials.yaml                                 # line ~1144 (trial-042) only
  - workspace/docs/gsvivs_audit_results.md                         # :165 documents the pipeline order
  - .gitignore
write_scope:
  - workspace/scripts/README.md
  - workspace/research/trials.yaml
  - .gitignore
acceptance_criteria:
  - "./vol exec python -c \"import re,pathlib; t=pathlib.Path('workspace/research/trials.yaml').read_text(encoding='utf-8'); m=[p for p in re.findall(r'script:\\s*(\\S+)', t) if not pathlib.Path(p).exists()]; print('MISSING:', m); raise SystemExit(1 if m else 0)\" -> OUTPUT_FILE shows MISSING: [] and EXIT_CODE=0"
  - "git check-ignore workspace/learning/dashboard.html -> exit 0 (SKIP this criterion under Gate E Option 2)"
  - "test -f workspace/scripts/README.md -> exit 0"
  - "python workspace/lint/lint_all.py -> full PASS"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; trials.yaml may ONLY have trial-042's script: field changed — no other line"
  - "do NOT delete workspace/scripts/ or any script (AW-G17 verifier guardrail); 'archive' sub-decision means git mv into workspace/scripts/archive/, nothing removed"
context_summary: |
  AW-G17: 15 tracked one-off analysis scripts live in workspace/scripts/ with ~0 agentic references,
  but the audit verifier confirmed the tree is sanctioned (AGENTS.md:168 "Build here"; documented as an
  ordered idempotent pipeline at gsvivs_audit_results.md:165) — the fix is to record that status, not
  delete. trials.yaml:1144 (trial-042) points at workspace/scripts/gsvivs_threshold_sweep.py, which does
  not exist; on-disk candidates are sweep_gsvivs_threshold.py, gsvivs_walkforward_threshold.py,
  sweep_gsvivs_long_flat_threshold.py. The user decided sanction-vs-archive at Gate E (Task 0);
  apply whichever was recorded. AW-40's generated dashboard.html is tracked; gitignore + untrack it
  here unless Gate E chose Option 2 (relocation removes it wholesale).
depends_on: []
```

- [ ] **Step 1 (recipe — docs/config, no test):**
  1. `ls workspace/scripts/` and record the actual filenames (expect 15 `.py`).
  2. Write `workspace/scripts/README.md` with exactly this content, substituting the real file list and today's date:

     ```markdown
     # workspace/scripts/ — sanctioned one-off analysis pipeline

     Status: SANCTIONED in place (wf-overhaul Plan 08, Gate E sub-decision, <YYYY-MM-DD>).
     <!-- If Gate E chose "archive": Status: ARCHIVED to workspace/scripts/archive/ (same date). -->

     These are the ordered, idempotent analysis scripts documented in
     `workspace/docs/gsvivs_audit_results.md` (§ pipeline, line ~165) and referenced by
     `workspace/plans/plan-b-enriched-5min-lstm.md`. They are NOT session debris: the
     AGENTS.md workspace policy bans throwaway scripts in `workspace/tmp/` only, and
     designates `workspace/` as the build tree. Do not delete without checking the two
     referencing documents above. Referenced from config: `workspace/research/trials.yaml`
     (trial-042 `script:` field).

     Inventory (<n> scripts, audit 2026-07):
     <one bullet per script: filename — one-clause purpose taken from its module docstring>
     ```
  3. If E-sub = **archive**: `git mv` each script to `workspace/scripts/archive/` (create dir), and use the archive Status line in the README.
  4. Open the three candidate scripts' docstrings; set trial-042's `script:` to the one implementing the threshold sweep described by the surrounding trial-042 fields (**fallback if ambiguous: `workspace/scripts/sweep_gsvivs_threshold.py`**, prefixed with `archive/` if E-sub = archive). Note the choice in your return.
  5. Unless Gate E = Option 2: locate the tracked dashboard via `git ls-files | grep -i dashboard.html` (expected `workspace/learning/dashboard.html`; if it differs, use the real path and note the delta). Append that path to `.gitignore` under the Plan-01 entries, then `git rm --cached <path>`.
- [ ] **Step 2: Verify** — run all four acceptance commands; paste sentinel outputs.
- [ ] **Step 3: Commit** — `chore(workspace): sanction analysis scripts, fix trial-042 path, ignore dashboard`

---

### Task 2A (Gate E Option 1 ONLY): node selector + collapse tutoring prompts to /study + /learning (AW-24, AW-40)

**Files:** Create `workspace/learning/select_nodes.py`, `workspace/learning/test_select_nodes.py` · Modify `workspace/learning/generate_dashboard.py` (factor the shared due+frontier helper the selector reuses), `.github/prompts/study.prompt.md`, `.github/prompts/INDEX.md`, `skills/design.md`, `skills/INDEX.md` · Create `.github/prompts/learning.prompt.md` · Delete the other tutoring prompts. **TDD required** for the selector (real red → green below).

**Copilot context packet:**

```yaml
subtask_id: "wfo-08-2"
goal: "select_nodes.py emits a <=5-node due+frontier YAML slice to workspace/tmp/ (tests green, red shown first), and exactly two prompts (/study, /learning) reference workspace/learning/ — neither loads graph.yaml directly"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-08-closure.md   # Task 2A section (code lives here)
  - workspace/learning/generate_dashboard.py                       # REUSE its loaders + due/frontier logic (the REAL schema)
  - workspace/learning/graph.yaml                                   # FIRST ~80 LINES ONLY (schema spot-check; generate_dashboard already encodes it)
  - workspace/learning/mastery-state.json                           # top-level keys only
  - .github/prompts/                                                # the 6 tutoring prompts + INDEX.md
  - workspace/lint/lint_prompts.py                                  # the contract the prompts must pass
  - skills/design.md                                                # §3 guide-skill roster sentence (Plan 07 sanction text)
  - skills/INDEX.md                                                 # rows for the retired guide-only skills
write_scope:
  - workspace/learning/select_nodes.py
  - workspace/learning/test_select_nodes.py
  - workspace/learning/generate_dashboard.py                       # path-param loaders + extracted enrich_nodes/compute_due_and_frontier (pure refactor)
  - .github/prompts/study.prompt.md
  - .github/prompts/learning.prompt.md
  - .github/prompts/INDEX.md
  - .github/prompts/<the 4 retired tutoring prompts — deletions>
  - skills/design.md                                                # reconcile §3 roster claim
  - skills/INDEX.md                                                 # annotate retired-prompt rows
acceptance_criteria:
  - "./vol exec python -m pytest workspace/learning/test_select_nodes.py -q -> 6 passed (red run recorded first: ModuleNotFoundError before select_nodes.py exists)"
  - "./vol exec python workspace/learning/select_nodes.py --max-nodes 5 -> prints OUTPUT_FILE=...study_nodes.yaml and SELECTED=<n> with n<=5; output file < 20 KB"
  - "./vol exec python workspace/learning/generate_dashboard.py --text -> byte-identical before and after the generate_dashboard refactor; and every id the selector tags _status: frontier against the LIVE graph appears in that output's 'Frontier Nodes' section (selector REUSES generate_dashboard's due/frontier logic — proves no re-derivation with wrong constants)"
  - "grep -l 'workspace/learning' .github/prompts/*.prompt.md -> exactly study.prompt.md and learning.prompt.md"
  - "skills/design.md §3 no longer claims a retired guide-only skill is 'wired to a matching .github/prompts/<name>.prompt.md', and the skills/INDEX.md rows for retired prompts route via /study + /learning (manual diff check)"
  - "python workspace/lint/lint_all.py -> full PASS (prompts bijection + model-pin checks included)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "NEVER read graph.yaml in full into your own context (194 KB — the defect under repair); you do NOT need to — reuse generate_dashboard.py, which already encodes the real schema (nodes LIST keyed by `id` with a `requires:` prereq list; flat mastery-state {id:{tier,next_review,...}} with a `tier` STRING, not a numeric mastery). A head -80 spot-check is the most you should read directly."
  - "the generate_dashboard.py change is a PURE EXTRACTION (path-parametrized loaders + two importable helpers enrich_nodes/compute_due_and_frontier); its --text output must be byte-identical before/after. select_nodes.py REUSES those — it does NOT re-derive due/frontier and defines NO field-name constants (no `prerequisites`, no `mastery`, no 0.8 cutoff — those were all wrong)"
  - "TDD failing-first: show red, then green; test fixtures use the REAL field names (LIST-form graph nodes with `id`/`requires`; flat state dict with `tier`/`next_review`); prompts keep bare backtick paths (never Markdown links) and mirror study.prompt.md's existing frontmatter keys"
context_summary: |
  Gate E chose Option 1: keep tutoring in-repo but stop /study from loading the 194 KB graph (~48.6k t)
  every session (AW-24, the audit's sole contested finding — fix chosen anyway). The due+frontier
  selection ALREADY EXISTS in generate_dashboard.py::generate_text_status() against the REAL schema:
  graph `nodes:` is a LIST of dicts keyed by `id`, each with a `requires:` prereq list (NOT
  `prerequisites`); mastery-state.json is a FLAT {id: {tier, next_review, ...}} dict whose `tier` is a
  STRING (untested/recognized/understood/mastered), NOT a numeric `mastery`. "Mastered" for the frontier
  gate means tier >= understood (tier_rank >= 2). So do NOT re-derive with guessed constants
  (prerequisites / mastery / 0.8 — every one is wrong and would make every non-due node vacuously a
  frontier): make generate_dashboard's loaders path-parametrized, extract enrich_nodes(nodes,state) and
  compute_due_and_frontier(enriched,today) from generate_text_status (which then calls them — pure
  refactor, --text output unchanged), and have select_nodes.py IMPORT + reuse them, emitting only due +
  frontier nodes capped at --max-nodes to workspace/tmp/study_nodes.yaml. The 6 tutoring slash commands
  collapse to /study + /learning (AW-40 footprint cut). Plan-07's lint_prompts.py enforces the INDEX
  bijection and instruction-verb rule — update .github/prompts/INDEX.md in the same commit as the
  deletions. Retiring prompts also falsifies Plan-07's skills/design.md §3 claim that each guide-only
  skill is "wired to a matching .prompt.md" plus its skills/INDEX.md rows — reconcile both (retired
  prompts now route via /study + /learning) in the same commit.
depends_on: []
```

- [ ] **Step 1: Write the failing test** — `workspace/learning/test_select_nodes.py`, exactly:

```python
"""Fixture tests for the /study node selector (TDD - written before select_nodes.py).

Fixtures use the REAL learning schema, confirmed against the live files:
  * graph.yaml -> {"nodes": [ {id, name, requires: [...]}, ... ]}   (a LIST of node dicts)
  * mastery-state.json -> {node_id: {tier, next_review, ...}}       (a FLAT dict; tier is a STRING)
A node counts as "mastered" for the frontier gate when its tier is understood or mastered
(tier_rank >= 2) - there is NO numeric mastery field.
"""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import select_nodes as sn  # noqa: E402

TODAY = "2026-07-10"


def write_fixture(tmp_path, nodes, state):
    g = tmp_path / "graph.yaml"
    s = tmp_path / "state.json"
    g.write_text(yaml.safe_dump({"nodes": nodes}), encoding="utf-8")   # nodes: LIST of dicts (real schema)
    s.write_text(json.dumps(state), encoding="utf-8")                  # state: FLAT {id: {...}} dict
    return g, s


def run(tmp_path, nodes, state, max_nodes=5):
    g, s = write_fixture(tmp_path, nodes, state)
    out = tmp_path / "study_nodes.yaml"
    rc = sn.main(["--graph", str(g), "--state", str(s), "--out", str(out),
                  "--today", TODAY, "--max-nodes", str(max_nodes)])
    assert rc == 0
    return yaml.safe_load(out.read_text(encoding="utf-8"))


def test_due_node_selected_mastered_future_node_excluded(tmp_path):
    nodes = [{"id": "har", "name": "HAR", "requires": []},
             {"id": "garch", "name": "GARCH", "requires": []}]
    state = {"har": {"tier": "understood", "next_review": "2026-07-01"},
             "garch": {"tier": "understood", "next_review": "2027-01-01"}}
    got = run(tmp_path, nodes, state)
    ids = [n["id"] for n in got["nodes"]]
    assert "har" in ids and "garch" not in ids  # har is due; garch's review is in the future
    assert [n["_status"] for n in got["nodes"] if n["id"] == "har"] == ["due"]


def test_frontier_requires_all_prereqs_mastered(tmp_path):
    nodes = [{"id": "rv-basics", "name": "RV", "requires": []},
             {"id": "har", "name": "HAR", "requires": ["rv-basics"]},
             {"id": "harq", "name": "HARQ", "requires": ["har"]}]
    state = {"rv-basics": {"tier": "understood"}}  # har unlocked; harq still locked
    got = run(tmp_path, nodes, state)
    ids = [n["id"] for n in got["nodes"]]
    assert "har" in ids            # untested, all prereqs (rv-basics) >= understood -> frontier
    assert "harq" not in ids       # prereq har is untested -> still locked
    assert "rv-basics" not in ids  # understood (>= frontier bar) and not due


def test_cap_respected(tmp_path):
    nodes = [{"id": f"n{i}", "name": f"N{i}", "requires": []} for i in range(10)]
    got = run(tmp_path, nodes, state={}, max_nodes=5)
    assert got["node_count"] == 5 and len(got["nodes"]) == 5


def test_due_ranked_before_frontier(tmp_path):
    nodes = [{"id": "a", "name": "A", "requires": []},
             {"id": "b", "name": "B", "requires": []}]
    state = {"a": {"tier": "understood", "next_review": "2026-01-01"}}  # a is due; b is an untested frontier
    got = run(tmp_path, nodes, state, max_nodes=1)
    assert [n["id"] for n in got["nodes"]] == ["a"]


def test_output_is_small_slice_not_full_graph(tmp_path):
    nodes = [{"id": f"n{i}", "name": f"N{i}", "requires": [],
              "key_points": ["x" * 2000]} for i in range(50)]
    got = run(tmp_path, nodes, state={}, max_nodes=5)
    assert got["node_count"] == 5
    assert (tmp_path / "study_nodes.yaml").stat().st_size < 15_000  # enrichment drops bulky fields


def test_sentinel_lines_printed(tmp_path, capsys):
    run(tmp_path, [{"id": "a", "name": "A", "requires": []}], state={})
    outp = capsys.readouterr().out
    assert "OUTPUT_FILE=" in outp and "SELECTED=" in outp
```

- [ ] **Step 2: Run to confirm red** — `./vol exec python -m pytest workspace/learning/test_select_nodes.py -q` → expected failure: `ModuleNotFoundError: No module named 'select_nodes'` (collection error). Paste the sentinel output.
- [ ] **Step 3a: Factor the shared selection logic into `generate_dashboard.py`** (so the selector cannot drift from the text dashboard — fix-authority §F; the due/frontier algorithm ALREADY lives in `generate_text_status()`, do NOT re-derive it):
  1. Make its loaders path-parametrized, backward-compatibly: `def load_graph(path: Path | None = None)` defaulting to `GRAPH_PATH`, `def load_state(path: Path | None = None)` defaulting to `STATE_PATH` (so `generate()` still calls them with no args).
  2. Extract two importable helpers **verbatim** from `generate_text_status()` and have that function call them (pure refactor, no behaviour change):
     - `enrich_nodes(nodes, state)` → the existing per-node enrichment block (`id`, `name`, `layer`, `requires`, `tier` via `state.get(id,{}).get("tier","untested")`, `next_review` via `_parse_review_date`, `last_tested`, `consecutive_passes`, `downstream_count` via `compute_downstream_counts`).
     - `compute_due_and_frontier(enriched, today)` → returns `(due, frontiers)` exactly as generate_text_status computes them today: **due** = nodes whose `next_review` is set and `<= today`, sorted by `TIER_ORDER`; **frontier** = nodes whose `tier` ∉ {understood, mastered} and whose every `requires` prereq is at `tier_rank >= 2` (i.e. >= understood), sorted by `-downstream_count`.
  3. Confirm `./vol exec python workspace/learning/generate_dashboard.py --text` prints byte-identical output before and after this extraction.
- [ ] **Step 3b: Implement the selector** — `workspace/learning/select_nodes.py`, exactly (it IMPORTS the helpers from Step 3a and reuses them; there are NO field-name constants to guess — `requires`, `tier`, `next_review`, `TIER_ORDER` all come from `generate_dashboard.py`):

```python
#!/usr/bin/env python3
"""Select due + frontier learning nodes so /study loads a ~5-node slice, not the 194 KB graph.

Reads workspace/learning/graph.yaml + mastery-state.json and writes a compact YAML slice to
workspace/tmp/study_nodes.yaml. The due/frontier DEFINITION is NOT re-implemented here: this
module reuses generate_dashboard.py's own loaders, enrichment, and due+frontier computation
(the same logic behind `generate_dashboard.py --text`), so the /study slice can never drift from
the dashboard. Prints OUTPUT_FILE= and SELECTED= lines (sentinel style).
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml  # PyYAML - already in the project environment (all experiment configs are YAML)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # generate_dashboard.py is a sibling module
# Reuse the REAL schema + selection logic (no guessed field-name constants):
from generate_dashboard import (  # noqa: E402
    load_graph,
    load_state,
    enrich_nodes,
    compute_due_and_frontier,
)

REPO_ROOT = HERE.parents[1]  # workspace/learning/ -> repo root
GRAPH = HERE / "graph.yaml"
STATE = HERE / "mastery-state.json"
DEFAULT_OUT = REPO_ROOT / "workspace" / "tmp" / "study_nodes.yaml"


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def select(graph_path: Path, state_path: Path, max_nodes: int, today: dt.date) -> list:
    enriched = enrich_nodes(load_graph(graph_path), load_state(state_path))
    due, frontiers = compute_due_and_frontier(enriched, today)
    due_ids = {n["id"] for n in due}
    picked, seen = [], set()
    for n in due + frontiers:               # due ranked before frontier
        if n["id"] in seen:
            continue
        seen.add(n["id"])
        node = {k: _iso(v) for k, v in n.items()}   # date objects -> ISO strings
        node["_status"] = "due" if n["id"] in due_ids else "frontier"
        picked.append(node)
        if len(picked) >= max_nodes:
            break
    return picked


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", default=str(GRAPH))
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--max-nodes", type=int, default=5)
    ap.add_argument("--today", default=None, help="ISO date override (tests)")
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    selected = select(Path(a.graph), Path(a.state), a.max_nodes, today)
    payload = {"generated_from": a.graph, "date": today.isoformat(),
               "node_count": len(selected), "nodes": selected}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
                   encoding="utf-8")
    print(f"OUTPUT_FILE={out}")
    print(f"SELECTED={len(selected)} of {a.max_nodes} max (due+frontier)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to green** — `./vol exec python -m pytest workspace/learning/test_select_nodes.py -q` → `6 passed`. Then the live smoke: `./vol exec python workspace/learning/select_nodes.py --max-nodes 5` → `OUTPUT_FILE=` + `SELECTED=n` with n ≤ 5. Finally the **no-drift cross-check**: `./vol exec python workspace/learning/generate_dashboard.py --text` and confirm every id the selector tagged `_status: frontier` appears in that output's "Frontier Nodes" section (they share one code path, so they must agree). Paste all three sentinel/command outputs.
- [ ] **Step 5: Collapse the prompts (recipe — prompts are TDD-exempt):**
  1. `grep -l 'workspace/learning' .github/prompts/*.prompt.md` — expect **6** files including `study.prompt.md`, `quiz.prompt.md`, `learn.prompt.md`, and the teach prompt; record the actual six names in your return (if the count differs, list what you found and proceed with the actual set).
  2. Rewrite `.github/prompts/study.prompt.md`: **preserve its existing frontmatter keys unchanged**, replace the body with exactly:

     ```markdown
     Run the node selector first, then read only its output — never load `workspace/learning/graph.yaml` directly (194 KB; the selector exists to keep it out of context).

     1. Run the selector: on S-B `./vol exec python workspace/learning/select_nodes.py --max-nodes 5`; on S-A the `vol.cmd exec` equivalent. Read the `OUTPUT_FILE=` path it prints.
     2. Read each file below with read_file before acting:
        - `workspace/tmp/study_nodes.yaml`
     3. Teach the selected nodes one at a time: explain, then ask 2-3 questions per node and grade the answers.
     4. At session end, update `workspace/learning/mastery-state.json` for the studied nodes only (mastery + next_review); leave every other entry untouched.
     ```
  3. Create `.github/prompts/learning.prompt.md`: copy `study.prompt.md`'s frontmatter (adjust any description field to "Consolidated learning admin: quiz / teach / progress"), body exactly:

     ```markdown
     Read each file below with read_file before acting:
     - `workspace/learning/mastery-state.json`

     Consolidated learning command (absorbs the retired tutoring prompts). Ask the user which mode they want, then follow it:
     - **quiz** — run `./vol exec python workspace/learning/select_nodes.py --max-nodes 3` (S-A: `vol.cmd exec` equivalent), read `workspace/tmp/study_nodes.yaml`, and quiz the user on those nodes only.
     - **teach** — same selection, but explain each node from first principles before questioning.
     - **progress** — summarize `workspace/learning/mastery-state.json`: mastered / in-progress / frontier counts and the next 5 due dates. Do not open `workspace/learning/graph.yaml`.

     Update `workspace/learning/mastery-state.json` only for nodes actually exercised.
     ```
  4. `git rm` the other four tutoring prompts from step 1's list; update `.github/prompts/INDEX.md`: remove their rows, add a `learning` row (`/learning — consolidated quiz/teach/progress — dispatches to workspace/learning/select_nodes.py + mastery-state.json`), and update the `/study` row's description to mention the selector.
  5. Reconcile the Plan-07 skill roster so no sanction text outlives its prompt: in `skills/design.md` §3, revise the guide-skill roster sentence so it no longer claims every guide-only skill is "wired to a matching `.github/prompts/<name>.prompt.md`" — state that the retired tutoring prompts now route through `/study` + `/learning`. In `skills/INDEX.md`, update (or annotate) each row whose `.prompt.md` was retired to point at `/study` / `/learning` instead of the deleted file. Commit these together with the prompt deletions.
- [ ] **Step 6: Verify** — run the six packet acceptance commands; paste outputs.
- [ ] **Step 7: Commit** (two commits) — `test(learning): fixture tests for the /study node selector` then `feat(learning): node selector caps /study context to due+frontier nodes` (include the prompt collapse + INDEX update in the second, or a third `chore(ci): collapse tutoring prompts to /study + /learning`).

---

### Task 2B (Gate E Option 2 ONLY): relocate the tutoring machinery out of the work repo (AW-24, AW-40)

**Files:** Delete `workspace/learning/` (tracked contents) and all 6 tutoring prompts · Modify `.github/prompts/INDEX.md`, `memory/INDEX.md` · Bundle to `workspace/tmp/learning-relocation/`. TDD-exempt (no Python authored).

**Copilot context packet:**

```yaml
subtask_id: "wfo-08-2"
goal: "the tracked tree contains zero workspace/learning/ files and zero tutoring prompts; a complete relocation bundle sits in workspace/tmp/learning-relocation/ for the user to move to their VS Code user profile"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-08-closure.md   # Task 2B section
  - .github/prompts/                                               # the 6 tutoring prompts + INDEX.md
  - memory/INDEX.md                                                # learning rows (e.g. graph.yaml at ~:112)
write_scope:
  - workspace/learning/                                            # deletions only
  - .github/prompts/<the 6 tutoring prompts — deletions>
  - .github/prompts/INDEX.md
  - memory/INDEX.md
  - workspace/tmp/learning-relocation/                             # untracked bundle
acceptance_criteria:
  - "git ls-files workspace/learning/ -> empty output"
  - "grep -l 'workspace/learning' .github/prompts/*.prompt.md -> no matches (exit 1)"
  - "ls workspace/tmp/learning-relocation/ -> contains graph.yaml, mastery-state.json, and the 6 prompt files"
  - "python workspace/lint/lint_all.py -> full PASS (prompts bijection, memory-budget, broken-refs all still green)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "COPY to the bundle BEFORE git rm — the bundle is the only surviving copy on this box"
  - "grep memory/ and skills/ for 'workspace/learning' after deletion; repoint or delete any dangling refs found (lint_broken_refs now sees plain-text paths) and list them in your return"
context_summary: |
  Gate E chose Option 2 (S7): the ~490 KB personal-tutoring machinery (graph.yaml 194 KB,
  mastery-state.json 22 KB, dashboard.html, 6 of 34 slash prompts) leaves the team-visible repo and
  moves to the user's VS Code user-profile prompts. This kills AW-24 (nothing left to load) and AW-40
  outright. The agent's job ends at the bundle in workspace/tmp/ (gitignored since Plan 01); the
  physical move to the user profile is user action U1, outside the repo. memory/INDEX.md rows pointing
  into workspace/learning/ must go in the same commit or Plan 04's memory lints break.
depends_on: []
```

- [ ] **Step 1 (recipe):**
  1. `grep -l 'workspace/learning' .github/prompts/*.prompt.md` — record the six prompt names (expect study, quiz, learn, the teach prompt + 2 more; proceed with the actual set and note it).
  2. `mkdir -p workspace/tmp/learning-relocation/prompts` · copy the full `workspace/learning/` contents into `workspace/tmp/learning-relocation/` and the six prompts into `.../prompts/`.
  3. `git rm -r workspace/learning/` · `git rm` the six prompts.
  4. Update `.github/prompts/INDEX.md` (drop the six rows) and `memory/INDEX.md` (drop every row whose path starts `workspace/learning/`, e.g. the graph.yaml row near line 112).
  5. Grep `memory/ skills/ workflows/ personas/` for `workspace/learning` — fix any dangling plain-text refs (delete the sentence or repoint); list each in your return.
  6. Write `workspace/tmp/learning-relocation/README-RELOCATE.md`: one paragraph telling the user to move `prompts/*.prompt.md` into their VS Code **user-profile** prompts folder and the data files anywhere personal, then delete the bundle (workspace/tmp is ephemeral).
- [ ] **Step 2: Verify** — run the four acceptance commands; paste outputs.
- [ ] **Step 3: Commit** — `chore(workspace): relocate personal tutoring machinery out of the repo`

---

### Task 3: AW-G31 doc correction — `test-all` names the tests/slow exclusion

**Files:** Modify `vol` (help heredoc text for `test-all` only) · `src/pyproject.toml` (comment lines around addopts, and the line-88 doc note) · `memory/ref/vol-cli.md` (`test-all` row). TDD-exempt (docs/comments only). **Do NOT remove `--ignore=tests/slow`** — the audit verifier inverted the primary fix: `tests/slow/` needs real data absent on CI runners.

**Copilot context packet:**

```yaml
subtask_id: "wfo-08-3"
goal: "no surface claims ./vol test-all runs 'the complete suite': vol help, pyproject comments, and vol-cli.md all state the tests/slow/ real-data exclusion and how to run it explicitly, with lint_vol_parity still green"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-08-closure.md   # Task 3 section (replacement text here)
  - vol                                                             # help heredoc, test-all entry near :98-99
  - src/pyproject.toml                                              # :82-88 addopts + doc note
  - src/tests/slow/conftest.py                                      # the documented design being surfaced
  - memory/ref/vol-cli.md                                           # test-all row (parity-linted pair)
write_scope:
  - vol
  - src/pyproject.toml
  - memory/ref/vol-cli.md
acceptance_criteria:
  - "./vol help | grep -A1 'test-all' -> mentions tests/slow and contains no 'complete' claim"
  - "grep -c 'tests/slow' src/pyproject.toml -> >= 2 (the addopts flag + the new explanatory comment)"
  - "python workspace/lint/lint_all.py -> full PASS (lint_vol_parity.py included)"
  - "git diff vol -> touches ONLY heredoc text lines (no dispatch case arms, no exec/bg lines)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "KEEP --ignore=tests/slow in addopts; do NOT un-ignore, rename, or move tests/slow/ (verifier-inverted primary fix); no ./vol semantics changes"
context_summary: |
  AW-G31: src/pyproject.toml:84 addopts --ignore=tests/slow silently excludes the tests/slow/ DIRECTORY
  from ./vol test, ./vol test-all, and CI, while the @pytest.mark.slow MARKER is a separate mechanism
  that test-all DOES include (13 marked files run). tests/slow/ currently holds no tests (only
  __init__.py + conftest.py) and its conftest documents the design: real-data staging, run explicitly.
  The fix is documentation only — the 'complete suite' language (vol:99 help text, pyproject:82-83)
  must name the exclusion so a future real-data test is not silently dropped. Plan 04's
  lint_vol_parity.py holds vol help and memory/ref/vol-cli.md in lockstep: edit both in this task.
depends_on: []
```

- [ ] **Step 1 (recipe):**
  1. In `vol`'s help heredoc, locate the `test-all` entry by content (near line 98-99; the text contains "complete" and "Run `test-all` before committing"). Replace its description with exactly:
     `Run all tests under tests/ including @pytest.mark.slow (excludes the tests/slow/ real-data staging dir — run that explicitly: ./vol exec python -m pytest tests/slow/). Run test-all before committing.`
     (Wrap to the heredoc's existing column width; keep the command name and any table alignment untouched.)
  2. In `src/pyproject.toml`, directly above the addopts line (~:84), insert this comment block:
     ```toml
     # NOTE: --ignore=tests/slow excludes the tests/slow/ real-data STAGING DIRECTORY from every
     # automated surface (./vol test, ./vol test-all, CI). It is a different mechanism from the
     # @pytest.mark.slow MARKER, which ./vol test filters out (-m "not slow") and ./vol test-all
     # includes. Real-data tests are run explicitly: uv run pytest tests/slow/
     ```
     Then reword the ~:88 doc note ("included in ./vol test-all") to say: `# @pytest.mark.slow tests ARE included in ./vol test-all; the tests/slow/ directory is NOT (see NOTE above).`
  3. Update the `test-all` row in `memory/ref/vol-cli.md` to the same one-line description used in the heredoc (parity lint requirement).
- [ ] **Step 2: Verify** — run the four acceptance commands; paste outputs (S-B; on S-A use `vol.cmd exec` for the grep/python equivalents).
- [ ] **Step 3: Commit** — `docs: clarify test-all scope vs tests/slow real-data staging`

---

### Task 4: `check_coverage.py` — the script-asserted 84/84 closure gate (TDD)

**Files:** Create `workspace/plans/copilot-workflow-overhaul/test_check_coverage.py` then `workspace/plans/copilot-workflow-overhaul/check_coverage.py`. **TDD required** — this is new code; red shown before implementation.

**Copilot context packet:**

```yaml
subtask_id: "wfo-08-4"
goal: "check_coverage.py (stdlib-only) parses 00-overview.md section 9 and exits 0 only when all 84 frozen AW-IDs appear exactly once with a valid disposition — fixture matrix green, red shown first"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-08-closure.md   # Task 4 section (code lives here)
  - workspace/plans/copilot-workflow-overhaul/00-overview.md       # section 9 matrix format (read-only here)
  - workspace/lint/lint_all.py                                     # style exemplar (stdlib, FAIL lines, exit codes)
write_scope:
  - workspace/plans/copilot-workflow-overhaul/check_coverage.py
  - workspace/plans/copilot-workflow-overhaul/test_check_coverage.py
acceptance_criteria:
  - "./vol exec python -m pytest workspace/plans/copilot-workflow-overhaul/test_check_coverage.py -q -> 9 passed (red run recorded first: ModuleNotFoundError before check_coverage.py exists)"
  - "./vol exec python workspace/plans/copilot-workflow-overhaul/check_coverage.py -> runs against the real overview; record the output (exit 0 'OK: 84/84...' expected AFTER Task 5; a FAIL listing missing /T refs is acceptable and expected BEFORE it)"
  - "grep -c 'import' workspace/plans/copilot-workflow-overhaul/check_coverage.py -> stdlib-only (argparse, re, sys, pathlib; no third-party imports)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/; 00-overview.md is READ-only for this task (Task 5 owns its edits)"
  - "TDD failing-first: show red, then green; stdlib only (matches the workspace/lint suite convention)"
context_summary: |
  Interface-ledger row (overview section 6): check_coverage.py lives in
  workspace/plans/copilot-workflow-overhaul/, asserts every AW-ID in section 9 appears exactly once with
  disposition in {plan-task, WONTFIX}, exit 1 on gap/dupe, run at Plan 08 closure. The audit is frozen:
  84 findings = AW-01..AW-55 plus AW-G2..AW-G31 minus AW-G21 (never issued) — hardcode this universe.
  Disposition grammar: Plan cell matches ^(0[1-8])(/T\d+)?$ or is the literal WONTFIX with a non-empty
  Notes cell. The matrix sits between the COVERAGE-MATRIX:BEGIN and :END HTML-comment markers; rows are
  5-cell pipe tables. Task 5 will finalize the matrix and re-run this script for the green 84/84.
depends_on: []
```

- [ ] **Step 1: Write the failing test** — `workspace/plans/copilot-workflow-overhaul/test_check_coverage.py`, exactly:

```python
"""Fixture-matrix tests for check_coverage.py (TDD - written before the module)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_coverage as cc  # noqa: E402

ALL_IDS = sorted(cc.EXPECTED_IDS)

HEADER = [
    "# fixture overview",
    "## 9. Findings-coverage matrix",
    "<!-- COVERAGE-MATRIX:BEGIN (fixture) -->",
    "| AW-ID | Sev | Finding (abridged) | Plan | Notes |",
    "|---|---|---|---|---|",
]
FOOTER = ["<!-- COVERAGE-MATRIX:END -->"]


def build(tmp_path, rows):
    body = [f"| {i} | M | synthetic | {plan} | {notes} |" for i, plan, notes in rows]
    p = tmp_path / "00-overview.md"
    p.write_text("\n".join(HEADER + body + FOOTER) + "\n", encoding="utf-8")
    return p


def full_rows():
    return [(i, "08", "") for i in ALL_IDS]


def test_universe_is_exactly_84():
    assert len(cc.EXPECTED_IDS) == 84
    assert "AW-G21" not in cc.EXPECTED_IDS
    assert {"AW-01", "AW-55", "AW-G2", "AW-G31"} <= cc.EXPECTED_IDS


def test_complete_matrix_passes(tmp_path):
    p = build(tmp_path, full_rows())
    assert cc.check(p) == []
    assert cc.main(["--overview", str(p)]) == 0


def test_task_refs_and_wontfix_with_reason_pass(tmp_path):
    rows = full_rows()
    rows[0] = (rows[0][0], "01/T3", "")
    rows[-1] = (rows[-1][0], "WONTFIX",
                "user declined at Gate E; audit counter-evidence recorded")
    assert cc.check(build(tmp_path, rows)) == []


def test_missing_id_fails(tmp_path):
    rows = [r for r in full_rows() if r[0] != "AW-40"]
    p = build(tmp_path, rows)
    errs = cc.check(p)
    assert any("AW-40" in e and "missing" in e for e in errs)
    assert cc.main(["--overview", str(p)]) == 1


def test_duplicate_id_fails(tmp_path):
    rows = full_rows() + [("AW-24", "08", "")]
    errs = cc.check(build(tmp_path, rows))
    assert any("AW-24" in e and "2 times" in e for e in errs)


def test_invalid_disposition_fails(tmp_path):
    rows = full_rows()
    rows[3] = (rows[3][0], "09", "")
    errs = cc.check(build(tmp_path, rows))
    assert any("invalid disposition" in e for e in errs)


def test_wontfix_without_reason_fails(tmp_path):
    rows = full_rows()
    rows[5] = (rows[5][0], "WONTFIX", "")
    errs = cc.check(build(tmp_path, rows))
    assert any("WONTFIX without a reason" in e for e in errs)


def test_unknown_id_fails(tmp_path):
    rows = full_rows() + [("AW-G21", "08", "")]
    errs = cc.check(build(tmp_path, rows))
    assert any("AW-G21" in e and "unknown" in e for e in errs)


def test_missing_markers_fail(tmp_path):
    p = tmp_path / "00-overview.md"
    p.write_text("no matrix here\n", encoding="utf-8")
    assert cc.check(p) != []
```

- [ ] **Step 2: Run to confirm red** — `./vol exec python -m pytest workspace/plans/copilot-workflow-overhaul/test_check_coverage.py -q` → expected failure: `ModuleNotFoundError: No module named 'check_coverage'`. Paste the sentinel output.
- [ ] **Step 3: Implement** — `workspace/plans/copilot-workflow-overhaul/check_coverage.py`, exactly:

```python
#!/usr/bin/env python3
"""Suite-closure gate: assert every audit finding is disposed exactly once.

Parses the findings-coverage matrix (section 9) of 00-overview.md - the block between the
COVERAGE-MATRIX:BEGIN / COVERAGE-MATRIX:END markers - and asserts:

  * every one of the 84 frozen audit AW-IDs appears exactly once (no gaps, no dupes),
  * no unknown AW-IDs appear,
  * every row carries a valid disposition: Plan cell matching NN or NN/T<m> (plan-task)
    or the literal WONTFIX, and
  * every WONTFIX row has a non-empty Notes cell (the recorded reason).

Exit 0 with "OK: 84/84 AW-IDs disposed exactly once" on success; exit 1 with one
"FAIL: <defect>" line per defect otherwise. Stdlib only (workspace/lint suite style).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

# The audit is frozen: 84 findings = AW-01..AW-55 (dimension auditors)
# + AW-G2..AW-G31 minus AW-G21 (gap-chase; G21 was never issued).
EXPECTED_IDS = frozenset(
    [f"AW-{n:02d}" for n in range(1, 56)]
    + [f"AW-G{n}" for n in range(2, 32) if n != 21]
)
assert len(EXPECTED_IDS) == 84, "expected-ID universe must be exactly 84"

BEGIN_MARK = "<!-- COVERAGE-MATRIX:BEGIN"
END_MARK = "<!-- COVERAGE-MATRIX:END"
PLAN_TASK_RE = re.compile(r"^(0[1-8])(/T\d+)?$")
ID_RE = re.compile(r"^AW-(G?\d+)$")


def extract_block(text: str) -> list:
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if l.strip().startswith(BEGIN_MARK)]
    ends = [i for i, l in enumerate(lines) if l.strip().startswith(END_MARK)]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise ValueError("COVERAGE-MATRIX BEGIN/END markers missing or malformed")
    return lines[starts[0] + 1 : ends[0]]


def check(path: Path) -> list:
    try:
        block = extract_block(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [str(exc)]

    errors = []
    seen = {}
    for line in block:
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [c.strip() for c in line.split("|")]
        if len(parts) != 7:  # '' + 5 cells + ''
            if len(parts) > 1 and ID_RE.match(parts[1]):
                errors.append(f"malformed row (need 5 cells): {line[:60]}")
            continue
        aw_id, plan, notes = parts[1], parts[4], parts[5]
        if aw_id == "AW-ID" or set(aw_id) <= {"-"} or not ID_RE.match(aw_id):
            continue  # header / separator / non-finding rows
        if aw_id not in EXPECTED_IDS:
            errors.append(f"unknown AW-ID not in the frozen 84: {aw_id}")
            continue
        seen[aw_id] = seen.get(aw_id, 0) + 1
        if plan == "WONTFIX":
            if not notes:
                errors.append(f"{aw_id}: WONTFIX without a reason in Notes")
        elif not PLAN_TASK_RE.match(plan):
            errors.append(
                f"{aw_id}: invalid disposition {plan!r} (need NN, NN/T<m>, or WONTFIX)"
            )

    for aw_id, n in sorted(seen.items()):
        if n > 1:
            errors.append(f"{aw_id}: appears {n} times (must be exactly once)")
    for aw_id in sorted(EXPECTED_IDS - set(seen)):
        errors.append(f"{aw_id}: missing from the coverage matrix")
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--overview",
        default=str(Path(__file__).resolve().parent / "00-overview.md"),
        help="path to the suite overview (default: sibling 00-overview.md)",
    )
    args = ap.parse_args(argv)
    errors = check(Path(args.overview))
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        print(f"check_coverage: {len(errors)} defect(s)")
        return 1
    print("OK: 84/84 AW-IDs disposed exactly once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to green** — `./vol exec python -m pytest workspace/plans/copilot-workflow-overhaul/test_check_coverage.py -q` → `9 passed`. Then run once against the real overview (`./vol exec python workspace/plans/copilot-workflow-overhaul/check_coverage.py`) and paste the output — before Task 5 finalizes the matrix, a `FAIL` list naming un-suffixed dispositions is possible and fine; the current matrix's bare `NN` cells are valid, so `OK` is also possible. Either way, record it.
- [ ] **Step 5: Commit** (two commits) — `test(plans): fixture matrix for the findings-coverage checker` then `feat(plans): check_coverage.py asserts 84/84 findings disposed`

---

### Task 5: Finalize the findings-coverage matrix per Gate E (WONTFIX ledger)

**Files:** Modify `workspace/plans/copilot-workflow-overhaul/00-overview.md` — the §9 `COVERAGE-MATRIX` block and the per-plan totals line only. TDD-exempt (docs).

**Copilot context packet:**

```yaml
subtask_id: "wfo-08-5"
goal: "the section-9 matrix carries final /T dispositions for AW-24/40/G17/G31 (or WONTFIX rows with the user's Gate-E reasons in Notes), and check_coverage.py exits 0 with 84/84"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-08-closure.md   # Task 5 section + Gate E record
  - workspace/plans/copilot-workflow-overhaul/00-overview.md       # section 9
  - workspace/plans/copilot-workflow-overhaul/check_coverage.py    # the gate this must satisfy
write_scope:
  - workspace/plans/copilot-workflow-overhaul/00-overview.md
acceptance_criteria:
  - "./vol exec python workspace/plans/copilot-workflow-overhaul/check_coverage.py -> exit 0, prints 'OK: 84/84 AW-IDs disposed exactly once'"
  - "git diff workspace/plans/copilot-workflow-overhaul/00-overview.md -> touches only the COVERAGE-MATRIX block rows for AW-24, AW-40, AW-G17, AW-G31 and the per-plan totals line"
  - "python workspace/lint/lint_all.py -> full PASS"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "WONTFIX reasons must be the user's recorded Gate-E sentences verbatim; do not paraphrase; AW-24's Notes must also carry the counter-evidence clause given in the plan"
context_summary: |
  Tasks 1-4 have landed. The orchestrator recorded the Gate E decision at Task 0. This task writes the
  final dispositions into the section-9 matrix so check_coverage.py (Task 4) goes green: plan-task rows
  get their /T suffix; WONTFIX rows (Option 3 only) get Plan cell 'WONTFIX' and the user's reason in
  Notes. The disposition grammar is Plan cell ^(0[1-8])(/T\d+)?$ or WONTFIX + non-empty Notes.
depends_on: ["wfo-08-1", "wfo-08-2", "wfo-08-3", "wfo-08-4"]
```

- [ ] **Step 1 (recipe):** edit exactly four rows in the §9 matrix:
  - **AW-G17** → Plan cell `08/T1`; Notes: keep existing text, append `; sanctioned in place with README` (or `; archived to workspace/scripts/archive/` per E-sub).
  - **AW-G31** → Plan cell `08/T3`; Notes: keep existing text, append `; doc-correction landed, --ignore retained`.
  - **AW-24** and **AW-40**, by Gate E option:
    - *Option 1:* both → `08/T2`; AW-24 Notes append `; selector shipped (~40k t/session saving), relocation declined at Gate E`; AW-40 Notes append `; collapsed 6→2 prompts + selector + dashboard gitignored; full relocation declined at Gate E`.
    - *Option 2:* both → `08/T2`; Notes append `; relocated to VS Code user profile (bundle: workspace/tmp/learning-relocation/), tree and prompts removed`.
    - *Option 3:* both → Plan cell `WONTFIX`; AW-24 Notes = `WONTFIX: <user's verbatim Gate-E reason>. Counter-evidence: sole CONTESTED finding of 84 — its adversarial verifier did not confirm the defect; per-session cost (~54k t) is measured but accepted.` AW-40 Notes = `WONTFIX: <user's verbatim Gate-E reason>.`
  - Update the per-plan totals line under the matrix only if a WONTFIX changes its phrasing needs (the count stays 84/84 disposed — WONTFIX is a disposition).
- [ ] **Step 2: Verify** — run the three acceptance commands; paste the `OK: 84/84` output.
- [ ] **Step 3: Commit** — `docs(plans): finalize findings-coverage matrix per Gate E`

---

### Task 6: Closure evidence — coverage gate, full lint, test-all, boot measurement, Shipped entry

**Files:** Modify `workspace/research/weekly-progress.md` (one line). All other output is pasted evidence (return contract + MR description). TDD-exempt.

**Copilot context packet:**

```yaml
subtask_id: "wfo-08-6"
goal: "closure evidence recorded: check_coverage 84/84, full lint_all PASS on S-A, ./vol test-all green on S-B, boot-token measurement vs the ~7,500 prior, and one Shipped line in weekly-progress"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-08-closure.md   # Task 6 section
  - workspace/plans/copilot-workflow-overhaul/check_coverage.py
  - workspace/research/weekly-progress.md
write_scope:
  - workspace/research/weekly-progress.md
acceptance_criteria:
  - "./vol exec python workspace/plans/copilot-workflow-overhaul/check_coverage.py -> 'OK: 84/84 AW-IDs disposed exactly once' (paste)"
  - "S-A: lint-workspace task (or vol.cmd exec python workspace/lint/lint_all.py) -> sentinel OUTPUT_FILE with full PASS and EXIT_CODE=0 (paste)"
  - "S-B: ./vol test-all -> all tests pass, exit 0 (paste the tail incl. the summary line)"
  - "boot measurement command below -> bytes and bytes/4 printed; value and delta vs the Plan-06 recorded prior (~7,500 t) written into the MR description AND the Shipped line"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "token numbers are directional, never hard gates (overview section 4 sanity rule): if the measurement is far BETTER than ~7,500, flag it in your return instead of celebrating"
context_summary: |
  Final task of the final plan. Everything is landed; this task produces the evidence the Plan-08
  acceptance gate demands and the one-line Shipped entry. The boot prior is the value Plan 06 recorded
  in its MR description (target was <= ~7,500 t directional, down from ~10,235 t pre-suite); read it
  from that MR if reachable, else use ~7,500 as the comparison point and say so. The suite sync-back to
  ML-GS deliverables + docs-only is a USER action (U2) on the personal machine — note it, do not
  attempt it from this repo.
depends_on: ["wfo-08-5"]
```

- [ ] **Step 1: Run the four evidence commands** and paste every output verbatim into the return contract and the MR description:
  1. Coverage: `./vol exec python workspace/plans/copilot-workflow-overhaul/check_coverage.py`
  2. Lint on S-A: the `lint-workspace` VS Code task (or `vol.cmd exec python workspace/lint/lint_all.py`) → read the `OUTPUT_FILE=` sentinel; require full PASS, `EXIT_CODE=0`.
  3. Tests on S-B: `./vol test-all` → green.
  4. Boot measurement (S-B):
     `./vol exec python -c "import pathlib; fs=['.github/copilot-instructions.md','AGENTS.md','memory/person/user.md','memory/research/project-state.md','memory/INDEX.md']; b=sum(pathlib.Path(f).stat().st_size for f in fs); print(f'BOOT_BYTES={b}'); print(f'BOOT_TOKENS_EST={b//4}')"`
     Record `BOOT_TOKENS_EST`, the Plan-06 prior, and the delta.
- [ ] **Step 2: Shipped entry** — append one line to the Shipped section of `workspace/research/weekly-progress.md`:
  `- wf-overhaul Plan 08 (suite CLOSED): 84/84 audit findings disposed (check_coverage green); lint_all full PASS (S-A); ./vol test-all green (S-B); boot <BOOT_TOKENS_EST> t vs ~7,500 prior; Gate E = Option <n>.`
- [ ] **Step 3: Commit** — `docs: record wf-overhaul suite closure evidence`
- [ ] **Step 4: Remind the user of the two USER actions** in your return notes: **U1** (Option 2 only) move `workspace/tmp/learning-relocation/` into the VS Code user profile, then delete the bundle; **U2** sync the finished suite back to ML-GS on the personal machine — copy `workspace/plans/copilot-workflow-overhaul/*.md` + `check_coverage.py` into ML-GS `deliverables/copilot-workflow-overhaul-plans/` and run the ML-GS `sync-docs` skill so `docs-only` picks them up (any `.py` becomes `.py.txt` on that branch per ML-GS policy).

---

## 6. Configs / experiments

None — this plan ships no runnable ML experiments (no trials.yaml entries beyond Task 1's single path repair, no launch commands).

---

## 7. Orchestrator prompt

```
/execute Implement Plan 08 (Deferred Relocation & Suite Closure) from workspace/plans/copilot-workflow-overhaul/plan-08-closure.md

Precondition check: Plan 07 gate passed — run `python workspace/lint/lint_all.py` (must be full PASS,
including lint_model_pins and lint_prompts) and confirm with the user that the Plan 07 MR is merged and
the /fix-it live verification was recorded. Then run Task 0 (Gate E, plan §2) with the user and record:
Option 1/2/3, the G17 sub-decision (sanction/archive), and — Option 3 — the verbatim WONTFIX reasons.
Do NOT dispatch any subagent before Gate E is recorded. Gate E has no default.

Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1 (parallel, max 4): wfo-08-1, wfo-08-2 (dispatch Task 2A if Gate E = Option 1, Task 2B if
    Option 2, dispatch NOTHING for this id if Option 3), wfo-08-3, wfo-08-4
  Wave 2: wfo-08-5   # sole writer of 00-overview.md; needs the Gate E record + all Wave-1 returns
  Wave 3: wfo-08-6   # closure evidence; needs the green matrix from wfo-08-5
Each subagent: TDD where code is touched (show red, then green — Tasks 2A and 4), terminal isolation +
cleanup EXIT GATE, return the §5.2 return contract verbatim.
Retry a blocked/partial subagent once with a refined packet, then escalate with both attempts' evidence.
Integration verification (orchestrator, after all tasks):
  ./vol exec python workspace/plans/copilot-workflow-overhaul/check_coverage.py   -> OK: 84/84
  python workspace/lint/lint_all.py                                               -> full PASS (S-A and S-B)
  ./vol test-all                                                                  -> green (S-B)
Paste all three outputs plus the boot measurement into the MR description.
Update workspace/research/weekly-progress.md (Shipped section, one line — Task 6 owns it).
Remind the user of U1 (Option 2 only) and U2 (suite sync-back to ML-GS deliverables + docs-only,
personal machine). There is no Plan 09 — do NOT start anything further.
```

---

## 8. Acceptance gate → suite closed

Overview §2 Plan-08 gate, verbatim:

> **Gate E (decision):** tutoring relocation scope + AW-24 selector-vs-WONTFIX, chosen by the user. Closure: `check_coverage.py` asserts 84/84 AW-IDs disposed; full `lint_all.py` PASS; `./vol test-all` green on S-B; suite synced back to ML-GS deliverables + docs-only

Expanded — all of the following must be true before the suite is declared closed:

1. Gate E decision recorded (option + sub-decision + any WONTFIX reasons), and the matching Task 2 variant (or none, for Option 3) executed.
2. `./vol exec python workspace/plans/copilot-workflow-overhaul/check_coverage.py` → exit 0, `OK: 84/84 AW-IDs disposed exactly once` — pasted in the MR.
3. `python workspace/lint/lint_all.py` → full PASS on S-A (sentinel evidence) and S-B — pasted in the MR.
4. `./vol test-all` → green on S-B — tail pasted in the MR.
5. Boot-token measurement recorded (BOOT_BYTES + BOOT_TOKENS_EST) with the delta vs the ~7,500 t Plan-06 prior, in the MR description and the Shipped line — directional, not a hard gate; a far-better-than-prior number is investigated, not celebrated.
6. WONTFIX ledger final: any WONTFIX row in §9 carries the user's verbatim reason (AW-24's also carries the contested-finding counter-evidence clause).
7. `workspace/research/weekly-progress.md` Shipped line landed; MR `chore/wf-overhaul-08-closure` merged.
8. **USER (outside this repo):** U2 — suite files copied to ML-GS `deliverables/copilot-workflow-overhaul-plans/` and `docs-only` synced (`.py` → `.py.txt` on that branch). Option 2 only: U1 — relocation bundle moved to the VS Code user profile and the tmp bundle deleted.

Nothing consumes this plan — it is the suite's terminal node. The audit's 84 findings are, at this point, each either fixed by a named plan/task or consciously rejected with a recorded reason, and a script — not a promise — says so.
