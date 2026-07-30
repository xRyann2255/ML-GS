# Copilot Workflow Overhaul — Plan Suite Overview

**Date:** 2026-07-07 · **Status:** ACTIVE · **Suite id:** `wfo`
**Scope:** Remediate all 84 findings of the 2026-07 agentic-workflow audit (`deliverables/copilot-workflow-audit.md`) — credential incident, dead compute paths, governance fictions, duplicated rules, context waste — across the ml-vol-estimator Copilot execution surface, while preserving the working research workflow.

## 1. How to use this suite

- Plans live at `workspace/plans/copilot-workflow-overhaul/` on the executing machine (authored copy: ML-GS `deliverables/copilot-workflow-overhaul-plans/`).
- **One plan = one Copilot orchestrator session** started with `/execute` using the Orchestrator prompt in that plan's last section. One task = one subagent dispatched with the context packet embedded in the task section.
- **Plans are strictly sequential. Do not start Plan N+1 before Plan N's acceptance gate passes** (gates below). One plan = one MR = one feature branch off `master`.
- **Never run this suite while a research `/execute` session is live** — the suite shares `workspace/plans/`, `trials.yaml`, `./vol`, and the always-on rule files with the 5 active research plans.
- **Self-modification hazard (standing constraint):** Plans 02 and 05 rewrite the always-on rules that govern the executing sessions themselves. Every packet quotes the rule text as-of-its-execution; if a rule cited in a packet no longer matches the live file, the subagent must STOP and return `blocked` with the diff, not improvise.
- **Drift check (standing constraint):** this suite was written against a mirror verified byte-identical on 2026-07-07 (100% of audited findings live). Every packet carries: *"verify the cited path:line against the live tree before editing; if it moved, locate by content and note the delta in your return."*

## 2. Plan table and gates

| # | Plan | Primary AW-IDs killed | Gate to proceed |
|---|------|----------------------|-----------------|
| 01 | Credential incident & security hardening | 01, 02, 03, 08, 10, 32, 33 | **Gate A:** user confirms H1 (both PATs revoked) + H2 (GS notification decision made) BEFORE any MR referencing the secrets is pushed; then `git check-ignore workspace/config/.env` exits 0, PAT-prefix grep = 0 tracked hits, `lint_secrets.py` shown red pre-fix → green post-fix, 8/8 TLS clients verify certs |
| 02 | Surface contract & execution-rule scoping | 06, 07, G9, G11, G12, G13, G14, G27, G28, 39 | **Gate B (decision, default NO):** GitHub cloud coding agent supported? NO → scope-out lines land; YES → appendix plan 02b activates. **Gate C (decision):** CI home = GitLab job on the real remote vs `ci.yml` documented as mirror-only. Then: always-on files contain exactly one execution rule per surface; contradiction greps = 0 |
| 03 | Compute path works on both surfaces | 04, 05, 09, 13, 36, 41, 46, 54, G6, G7, G8, G10, G16, 55 | **Gate D (evidence):** on S-A `vol.cmd test -x -q` and the lint-workspace task produce sentinel OUTPUT_FILEs with `EXIT_CODE=0`; on S-B `./vol test` green; `./vol` on Windows fails loudly naming the fallback. Plans 04–08 may now use these commands as acceptance criteria |
| 04 | Lint gate real and green | 21, 44, G29, G30 (+ lint halves of 04, 12, 15, 20, 23, 47, 49, 55) | `python workspace/lint/lint_all.py` full PASS (14 + N new checks) on S-A and S-B; every NEW check has recorded red-then-green evidence; a deliberately planted violation is rejected by the pre-commit trigger (trigger proven live, then reverted) |
| 05 | Single source of truth (S3) | G2, G4, G5, 14, 22, 26, 27, 28, 35, 38, 42, 49, 53 | Lint stays green; the plan's contradiction grep-list returns 0 (one packet schema, one boot list, one lint policy, zero raw model-pin prose); boot-token bytes/4 measured before/after and recorded in the MR description |
| 06 | Memory & instruction-file honesty (S6) | 12, 15, 16, 17, 19, 20, 29, 34, 48, G15, G18, G19, G20, G22, G23, G24, G25, G26 | Memory-budget lint passes on measured bytes (P0+P1 ≤ 50k real tokens); broken-refs lint (now seeing plain-text paths + `_dormant`) passes; `_CANONICAL_EXAMPLE.yaml` self-validation command loads; boot re-measured (target ≤ ~7,500 t, directional) |
| 07 | Prompt & skill hygiene (S5) | G3, 11, 18, 23, 25, 30, 31, 37, 43, 45, 47, 50, 51, 52 | Model-pin-constant lint + prompts lint pass; `/fix-it` invocation verified live (AW-37 hypothesis check recorded); `.github/prompts/INDEX.md` complete in both directions; skill roster reconciled (counts match on-disk) |
| 08 | Deferred relocation & suite closure | 24 (CONTESTED), 40, G17, G31 | **Gate E (decision):** tutoring relocation scope + AW-24 selector-vs-WONTFIX, chosen by the user. Closure: `check_coverage.py` asserts 84/84 AW-IDs disposed; full `lint_all.py` PASS; `./vol test-all` green on S-B; suite synced back to ML-GS deliverables + docs-only |

Dependency graph (strictly sequential — every plan also depends on the standing lint gate from 04 onward):

```
01 ──► 02 ──► 03 ──► 04 ──► 05 ──► 06 ──► 07 ──► 08
(incident) (surfaces) (compute) (gates)  (rules)  (memory) (prompts) (closure)
```

Severity discipline: all 6 BLOCKERs die in Plans 01–04; the 20 HIGHs concentrate in 02–05; MEDIUM/LOW absorb into 04–08. The audit's 10 ROI quick-wins are distributed to their thematic plans and always land in each plan's **first wave**.

### HUMAN ACTION items (Plan 01, individually gated — nothing bundled)

| ID | Action | Why an agent cannot do it |
|----|--------|---------------------------|
| H1 | Revoke BOTH Confluence PATs (`workspace/config/.env:1` fingerprint `NzM2…44ch`; `memory/_dormant/ref/gssso-auth.md:87` fingerprint `MTQ2…44ch`) at confluence.work.gs.com token settings | Confluence UI action, user credentials |
| H2 | Decide/execute GS security-compliance notification for the exposure (AW-02 is a reportable event) | Firm-policy judgment call |
| H3 | History purge of the secrets on the GS remote after `git rm --cached` lands (filter-repo/BFG + force-push) | Repo-admin rights + MR approval |
| H4 | Purge the **parent ML-GS repo's `origin/presentation` branch**, which independently carries the live token | Different repo, owner action |
| H5 | Disposition of the off-perimeter personal-machine copy (secure or delete) | Outside the repo entirely |

Gate A blocks all agent commits that reference the secrets until H1+H2 are confirmed. H3/H4 may lag (tokens are dead after H1) but AW-01 closes only when they complete.

## 3. What already exists (do not rebuild)

**Every plan extends these; duplicating them is a defect.** (Full inventory: recon `existing-inventory.md`.)

1. **The 84-finding audit** — sole finding source; no re-audit, consume AW-IDs / quick-wins / S1–S7 / target-architecture verbatim.
2. **The 5-primitive framework** (Persona/Skill/Memory/Workflow/Policy) + per-primitive `design.md` contracts.
3. **`./vol` 33-command dispatch + `vol exec`/`bg` sentinel protocol** (`workspace/tmp/exec/<ts>_<pid>.out`, `OUTPUT_FILE=`/`EXIT_CODE=` lines) — extended with an OS guard and a `forecast` arm; the setsid/sentinel machinery is untouched.
4. **`skills/_shared/_run.{sh,cmd}` bootstrap + per-OS `.sh`/`.cmd` wrapper convention** (~40/49 skills correct) — the 6 broken ML-skill wrappers collapse ONTO it.
5. **P0–P3 memory tiers, `memory/INDEX.md` table format, the 25 research cards' content** — fix token math and dead rows, never redesign tiering.
6. **The 34-prompt bare-backtick dispatcher pattern** — deliberate and lint-enforced; NEVER converted to Markdown links.
7. **`workspace/lint/` — all 14 existing check scripts + `lint_all.py`'s `LINTS` registry** — new checks are appended tuples + new `lint_<name>.py` files only; existing check logic is never rewritten.
8. **`skills/CONFLUENCE/src/client.py` env-var auth (`from_env()`)** — correct as written; only the `verify_ssl` default flips.
9. **ml-vol-estimator's exclusion from ML-GS git tracking** — intentional isolation; remediation happens in the real GS repo.
10. **`_CANONICAL_EXAMPLE.yaml` schema-maintenance mechanism** — content regenerated from live registries; mechanism kept.
11. **`src/volforecast/utils/paths.py::resolve_project_root()`** — already lists `vol.cmd` as a repo-root marker: the Plan-03 Windows shim fills a designed-for seam.
12. **`src/volforecast/cli/*.py` `register(subparsers)`/`set_defaults(func=…)` pattern** — model for the `forecast` arm and the BACKTEST args-file CLI.
13. **`etask.py:137` `ssl.create_default_context()` usage** — the in-repo-correct model for all 8 TLS fixes.
14. **`workspace/config/user.json.template`** — the model for `.env.template`.
15. **The 5 ACTIVE research plans in `workspace/plans/`** (`bug3-iv-context-fix`, `gnn-gpu-parallel-plan`, `linear-alpha-tuning`, `plan-c-prediction-blending`, `trial-068-conditional-duan`) — read-only/no-touch in every packet's constraints.

## 4. Research grounding and expected-outcome priors

Evidence base: the audit's Phase-0 context-cost map, 84 verified findings (each with path:line evidence that survived adversarial verification), quick-wins ROI ranking, and strategic recommendations S1–S7 — re-verified live on 2026-07-07 (recon `findings-freshness.md`: 14/14 probes STILL-PRESENT).

| Component | Realistic expected outcome | Source of the prior |
|---|---|---|
| Always-on boot load | ~10,235 t → **~7,500 t** per session (bytes/4, directional) | Audit context-cost map + AW-15/16/26 projections |
| Non-`src/` Python edit overhead | **−3,083 t** per edit once `python.instructions.md` `applyTo` is scoped to `src/**` (~21% of tracked .py affected) | AW-19 |
| Lint suite | 3 of 14 failing today (registry grows to 15 after Plan 01, 21 after Plan 04) → **full PASS incl. new checks**, trigger proven live by a planted violation | AW-21 + governance-map |
| Skill→memory references | 51 broken → **0** (48 recoverable rewrites + 3 truly-dead handled explicitly) | AW-12 + freshness §12 |
| Model-pin literals | 76 `Opus 4.6` + 2 slug hits → **0 outside the lint constant + prompt frontmatter** | AW-G3/AW-23 + freshness §7 |
| Credential exposure | 2 live PATs in tree → **0 in tree AND revoked** (dead even where history retains them until H3/H4) | AW-01/02 + freshness §1–2 |
| Findings disposed | **84/84** = fixed (plan/task) or WONTFIX-with-reason, script-asserted | This suite's coverage matrix (§9) |

**Sanity rule:** a measured saving far better than the prior means the measurement is wrong (bytes/4 is crude) or load-bearing content was deleted — investigate before celebrating. Token numbers are directional acceptance evidence, never hard gates.

**Open hypotheses inherited from the audit** (each carries an in-plan verification step): AW-03 — whether the GS VS Code fork honors `commandAllowlist`/`additionalReadAccessPaths` (deletion is safe either way); AW-09 — whether `create_and_run_task` truly bypasses the Allow gate (retired regardless); AW-37 — how VS Code resolves the spaced `fix it.prompt.md` basename (live `/fix-it` check after rename); Opus-4.6 catalog availability (Rule-9 fallback clause added in Plan 05).

## 5. Shared conventions (repeated into every packet)

The target repo's own contract, extracted verbatim 2026-07-07 (recon `contract.md`). **Drafters copy from here; they never re-derive.**

### 5.1 Context-packet schema — the UNION resolution

The schema lives in TWO near-duplicate policy files. `policy/subagent_protocol.md:31-52` is canonical; `policy/context-isolation.md:48-66` adds `context_summary`; `workflows/plan.md:78-88` additionally requires `depends_on` for packets written into plans. **This suite's packets satisfy the union — all fields below, always** (this resolution is recorded here per the audit's AW-35; Plan 05 collapses the duplication, after which `subagent_protocol.md` alone is authoritative):

```yaml
subtask_id: "wfo-<NN>-<M>"            # suite id "wfo", plan NN, task M — stable, greppable
goal: "<ONE testable sentence>"
file_scope:                            # files the subagent may READ — minimal
  - workspace/plans/copilot-workflow-overhaul/plan-NN-<slug>.md   # its own task section
  - <2-5 true integration points>
write_scope:                           # the ONLY files the subagent may create/modify
  - <exact paths — disjoint from every concurrently-dispatched task>
acceptance_criteria:                   # machine-verifiable, no human judgment
  - "<command → expected output>"
memory_refs: []                        # memory files to load (usually empty for this suite)
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "<task-specific hard limits>"
context_summary: |
  <2-5 sentences replacing conversation history; states decided things as decided>
depends_on: ["<subtask_ids>"]
```

Packet rules (verbatim from `context-isolation.md:68-74`): goal is a single testable sentence; file_scope minimal; write_scope is the only writable set; acceptance criteria verifiable without human judgment; context_summary replaces conversation history.

### 5.2 Return contract (demand verbatim in every orchestrator prompt)

```yaml
status: complete | blocked | partial
files_changed: [{path, lines, summary}]
verification: ["<pasted command output>"]
blockers: ["<what prevented completion>"]
notes: ["<integration facts for the orchestrator>"]
```

Failure policy (`subagent_protocol.md:71-75`): blocked/partial → retry ONCE with a refined packet (add diagnostics), then escalate to the user with evidence from both attempts. Never more than one retry.

### 5.3 Hard rules every subagent inherits (`.github/copilot-instructions.md`, "Critical Rules (HARD — zero exceptions)")

1. **File writes → `workspace/tmp/` only.** Never `/tmp/`, `~`, or outside the repo.
2. **`./vol` for all Python/CLI on S-B** (`./vol shell|test|lint|fmt|exec|bg|sync`); on S-A use `vol.cmd`/`run_task` equivalents once Plan 03 lands (until then, S-A tasks are doc/config-only or routed to S-B).
3. **Terminal isolation:** everything via `./vol exec`/`bg`; `isBackground=true` on every `run_in_terminal`; never trust the buffer — `read_file` the `OUTPUT_FILE=` path.
4. **Terminal cleanup EXIT GATE:** `kill_terminal` every spawned terminal before returning; unkilled terminals = FAILED subagent.
5. **TDD (Rule 5):** failing test BEFORE implementation for all Python code changes. **Exempt: config, docs, memory, YAML, workflows, prompts** — which covers most of this suite; the exceptions (BACKTEST CLI, `forecast` arm, new lint modules, `vol.cmd` behavior where testable) get real red-then-green.
6. **Lint gate:** per Rule 6 lint runs on explicit request or pre-PR/commit (controls over `working-agreements.md:9` until Plan 05 reconciles them — surface the tension, don't relitigate it).
7. **Evidence over assumption:** verify with actual output; no fabrication; never claim done without evidence.
8. **No bare tool invocations** (`python x.py` → `./vol shell x.py`, etc.).
9. **Model pinning:** all subagents on Claude Opus 4.6; depth limit 1 from `/execute` (subagents do NOT spawn subagents); max 6 concurrent.

### 5.4 Git / MR conventions

- Branch per plan: `chore/wf-overhaul-NN-<topic>` off `master`; **never `main`**; rebase onto `origin/master` before push; MR-only; never amend; never `git add -A` (embedded repo at `workspace/docs/enghub/`); denied paths never staged: `workspace/docs/enghub/`, `workspace/tmp/`, `__pycache__/`, `*.pyc`.
- Commit style (GIT_COMMIT skill): lowercase verb, specific, ≤72 chars; prefix by path group — `chore(framework):` for policy/workflows/personas, `chore(ci):` for `.github/`, `docs(memory):` for memory/, `feat(cli):`/`test:` for the src-touching tasks.
- MR titles human-generic (no internal jargon, no finding IDs in the title; AW-IDs and measurements go in the description).

### 5.5 Orchestrator prompt template (instantiated; last section of every plan)

```
/execute Implement Plan NN (<title>) from workspace/plans/copilot-workflow-overhaul/plan-NN-<slug>.md

Precondition check: <previous plan's gate, as a runnable command or confirmed user decision>.
Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1: <ids>          # waves = disjoint write_scopes; respect depends_on
  Wave 2 (parallel, max <k≤6>): <ids>
Each subagent: TDD where code is touched (show red, then green), terminal isolation + cleanup,
return the §5.2 return contract verbatim.
Retry a blocked/partial subagent once with a refined packet, then escalate with both attempts' evidence.
Integration verification (orchestrator, after all tasks): <plan-specific gate commands>.
Update workspace/research/weekly-progress.md (Shipped section, one line).
Do NOT start Plan NN+1.
```

## 6. Interface ledger (authoritative — drafters copy, never re-derive; deviations back-ported same-sitting)

| Symbol | Defined in | Signature / value |
|---|---|---|
| `S-A` | 00-overview §2 / AGENTS.md "Supported Execution Surfaces" (Plan 02 rewrites `AGENTS.md` Environment section, no new policy file) | GS Windows desktop, H: drive, VS Code Chat, `.code-workspace` opened multi-root. PRIMARY. Compute: `run_task` labels → `.cmd` wrappers → `_run.cmd`; dev loop via `vol.cmd` |
| `S-B` | same | GS Linux Coder workspace (nix + uv). Secondary. Compute: `./vol` (all arms), `.sh` wrappers via `_run.sh` |
| `S-C` | same | GitHub cloud coding-agent runner — **UNSUPPORTED by default** (Gate B); scope-out lines in both always-on files |
| Gates A–E | 00-overview §2 | Decision rules exactly as written in the plan table — plans cite them by letter |
| `vol.cmd` | repo root (NEW, Plan 03) | 10 arms: `test`, `test-all`, `testlf`, `lint`, `fmt`, `typecheck`, `exec`, `bg`, `jobs`, `help` (`help` exits 0 and is the no-arg default). Writes the SAME sentinel protocol as `./vol`: `workspace/tmp/exec/<ts>_<pid>.out` with `OUTPUT_FILE=` and `EXIT_CODE=` lines. Every OTHER arm → exit 2 with `"GS Coder workspace only — run via ./vol on S-B"` |
| `./vol` OS guard | `vol` line ~1 region (Plan 03) | Non-Linux `uname -s` → exit 2: `"ERROR: ./vol requires the GS Linux Coder workspace (nix+uv). On Windows use vol.cmd (dev loop) or VS Code tasks."` |
| Interpreter resolution order | `vol.cmd` + `skills/_shared/_run.cmd` (Plan 03 unifies; kills AW-54) | 1) `workspace/config/user.json` `python_path` → 2) `H:\venv315`..`H:\venv38` scan → 3) `%ROOT%\src\.venv\Scripts\python.exe` → 4) `where python` |
| `forecast` case arm | `vol` dispatch (Plan 03) | Mirrors existing arms; routes to already-registered `volforecast.cli.forecast`; help-heredoc line added |
| `.vscode/tasks.json` | NEW, Plan 03, tracked | 45 task objects: 41 mirrored from `ml-vol-estimator.code-workspace` (43 minus notebook/research, deleted per AW-05) + kill-orphans-force + NEW `vol-test`/`vol-lint`/`vol-typecheck` per-OS tasks; `lint_vscode_tasks.py` extended to read it as primary source and flag divergence |
| Args-file contract | Plan 03 (kills AW-04/09) | Fixed path `workspace/tmp/<task-name>_args.json`; `run_id` INSIDE the JSON body, pattern `[a-z0-9-]+`; `create_and_run_task` retired everywhere incl. `memory/ref/vscode-tasks.md` rule E3 |
| `LINTS` registry entry | `workspace/lint/lint_all.py:57-156` | Existing 5-tuple format — new checks APPEND tuples; existing 14 scripts never rewritten |
| `lint_secrets.py` | `workspace/lint/` (NEW, Plan 01) | Scans tracked tree for PAT-shaped base64 tokens (len≥40, mixed-case+digits+`+/=`), `.env` files outside gitignore, bearer-header literals; whitelist file for sanctioned fingerprint mentions in docs |
| `lint_args_contract.py` | NEW, Plan 04 | Cross-checks every `*_task.{cmd,sh}` + SKILL.md documented args filename against the fixed-path contract |
| `lint_model_pins.py` | NEW, Plan 04 | Owns `EXPECTED_MODEL = "Claude Opus 4.6"` (THE constant) + `SANCTIONED_SITES = frozenset({"policy/subagent_protocol.md", ".github/copilot-instructions.md"})` — the two paths where the raw display-name literal is CANONICAL (pin + Rule 9 fallback) and structurally EXEMPT from the check. Flags raw literals outside prompt frontmatter, this file, and `SANCTIONED_SITES`. The `model_pins.txt` whitelist is temporary grandfathered prose only and burns fully EMPTY (Plans 05 partial → 07 empty) |
| `lint_wrapper_targets.py` | NEW, Plan 04 | Every skill task wrapper's `_PY_SCRIPT`/module target must exist and import |
| `lint_vol_parity.py` | NEW, Plan 04 | `vol` help heredoc ↔ `memory/ref/vol-cli.md` command-for-command parity |
| `lint_prompts.py` | NEW, Plan 04 (used by Plan 07) | Prompt filenames `^[a-z0-9-]+\.prompt\.md$`; INDEX.md ↔ directory bijection; every body has an instruction verb; frontmatter `model:` matches `lint_model_pins.EXPECTED_MODEL` where pinned |
| Memory-budget fix | `lint_memory_priority.py` + `validate_memory.py` (Plan 04 rewrites math; Plan 06 makes content pass) | Tokens = `bytes/4` measured, not claimed; P0+P1 ≤ 50k real; `research` domain gains a cap; path-existence checked |
| `.env.template` | `workspace/config/.env.template` (NEW, Plan 01) | `CONFLUENCE_PAT=` + `CONFLUENCE_URL=` placeholders, mirrors `user.json.template` style |
| `.github/prompts/INDEX.md` | NEW, Plan 07 | Registry table: prompt → description → dispatches-to (workflow/skill/persona); linked from AGENTS.md |
| `check_coverage.py` | `workspace/plans/copilot-workflow-overhaul/` (NEW, ships with suite) | Asserts every AW-ID in §9 appears exactly once with disposition ∈ {plan-task, WONTFIX}; exit 1 on gap/dupe. Run at Plan 08 closure |
| Boot measurement | recorded in Plan 05/06 MR descriptions | `bytes/4` over the 5 always-on/boot files (copilot-instructions, AGENTS.md, user.md, project-state.md, INDEX.md), before vs after |
| `subtask_id` format | §5.1 | `wfo-<NN>-<M>` |
| Branch format | §5.4 | `chore/wf-overhaul-NN-<topic>` |

### 6a. Ledger addenda (back-ported from drafting — these names are authoritative; the producer plan's spelling wins)

| Symbol | Defined in | Authoritative signature / value |
|---|---|---|
| `lint_secrets.py` scan classes | Plan 01 (wfo-01-1) | FOUR classes: S1 PAT-shaped base64 (len≥40, mixed-case+digit, `[A-Za-z0-9+/=]`); S2 tracked `.env` outside gitignore (`git check-ignore workspace/config/.env` must exit 0); S3 bearer/basic header literals (≥16 b64 chars w/ digit or `=`); **S4 disabled-TLS patterns** (`ssl.CERT_NONE`, `_create_unverified_context`, `verify=False`, `verify_ssl: bool = False`, `CONFLUENCE_VERIFY_SSL` default `"false"`) over `skills/**/*.py`. LINTS label `"secrets"`. Masks all tokens; `--selftest` mode |
| `lint_secrets_allowlist.txt` | `workspace/lint/` (Plan 01) | Suppression file; lines `<repo-relative-path><TAB><substring>`; ships EMPTY |
| Grandfather-whitelist convention | `workspace/lint/whitelists/*.txt` (Plan 04) | The mechanism a new check uses when its content-fix lands in a LATER plan: honest check goes RED now, a **recorded whitelist that only shrinks** keeps the gate green until the owner plan burns it to empty. Files + burner: `budget_grandfather.txt`→Plan 06; `broken_refs.txt`→Plan 06; `canonical_schema.txt`→Plan 06; `model_pins.txt`→Plans 05/07; `prompts.txt`→Plan 07; `dispatch_registration.txt`→Plan 07. **Replaces the `P0P1_BUDGET_ENFORCED` toggle any consumer plan may have assumed — there is no boolean toggle; enforcement = whitelist burned empty** |
| `lint_canonical_schema.py` | NEW, Plan 04 (wfo-04-10) — **NOT `lint_canonical_yaml.py`** | Regex-extracts every `@register_model`/`@register_feature_layer` key + `sequences.source` enum from src; asserts each appears in BOTH `_CANONICAL_EXAMPLE.yaml` and `yaml-config.instructions.md`. RED today (gnn, conditional_duan, implied_correlation, embargo missing) → green via `canonical_schema.txt`. Stdlib only |
| `lint_broken_refs.py` extension | Plan 04 (wfo-04-9) + whitelist `broken_refs.txt` — **NOT `broken_refs_allowlist.txt`** | Appended plain-text-path + `_dormant`-aware checks (AW-12 lint half); Plan 06 burns `broken_refs.txt` |
| Memory-budget fix (restated) | `lint_memory_priority.py` + `validate_memory.py` (Plan 04 wfo-04-2/3) | bytes/4 measured incl. the 6 workspace-resident P1 files; INDEX path-existence; `research` cap (`≤300` lines per `memory/design.md:49`); 10-domain whitelist collapsed to `meta/guide.md`; `dormant` added to `VALID_STATUSES`. Over-budget → recorded in `budget_grandfather.txt` (Plan 06 burns). `_INDEX_ROW` regex must tolerate the v2 6-column INDEX (Status/Updated added by Plan 06) |
| `python-helpers.instructions.md` | `.github/instructions/` (NEW, Plan 06, AW-19 companion) | Carries only env + file-output rules for `{skills,workspace}/**/*.py`; `python.instructions.md` `applyTo` narrows to `src/**/*.py` |
| `load_config` | `volforecast.config.load_config(path)` (Plan 06 self-validation) | Canonical-example loader; fallback recipe in Plan 06 Task 5 if the entry point differs |
| AW-49 resolution | Plan 05 | **DELETE boot step 4** (session-handoff check removed from `AGENTS.md` + `bootup.md`; NO handoff writer created). Plan 06 must NOT re-add a session-handoff reader/writer |
| `/team` max depth | Plan 05 | Resolved to **2** (leader→worker→sub-worker) with a leader-notification clause; `team.md:217` = `subagent_protocol.md`/`context-isolation.md`/`AGENTS.md:25` |
| Model-pin prose sites after Plan 05 | Plan 05 | Exactly TWO sanctioned raw-`Claude Opus 4.6` prose sites remain: `policy/subagent_protocol.md` (canonical pin) + `copilot-instructions.md` Rule 9 (1 occ, fallback clause); plus prompt frontmatter. These two are `SANCTIONED_SITES` (structurally exempt from `lint_model_pins.py`), NOT whitelist entries. `model_pins.txt` holds only temporary grandfathered prose and burns fully EMPTY (Plan 05 partial → Plan 07 empty). Plan 05 G7 grep excludes `_dormant/` (the `secdb-ecosystem.md` residue is Plan 07's) |
| PII placeholder table | Plan 01 (wfo-01-5), honored by `lint_hardcoded_env.py` `PII_PLACEHOLDERS_OK` | `jdoe` (kerberos), `first.last@gs.com` (email), `10.0.0.1` (IP), `SN0000000` (serial), `EXAMPLEBOOK` (book), `T0000000` (trade) |
| Gate A PAT-grep exclusion | Plan 01, overview §2 row 01 | `git grep -n -e "NzM2" -e "MTQ2" -- ':!workspace/plans/copilot-workflow-overhaul/'` — the suite's own plan files cite the sanctioned fingerprints; one unexcluded run with hand-inspection is also mandated |
| `.gitlab-ci.yml` job `workspace-lint` | Plan 02 (Gate C=GitLab branch) | `allow_failure: true` initially; **Plan 04 flips to `false`** when lint goes green |
| `wfo-02-5` | Plan 02 appendix §8b (Gate B=YES override only) | `copilot-setup-steps.yml`, job id `copilot-setup-steps` (setup-python 3.11 + setup-uv + `UV_INDEX_URL` sync) |
| `check_coverage.py` grammar | Plan 08 | Disposition cell matches `^(0[1-8])(/T\d+)?$` OR literal `WONTFIX` + non-empty Notes; 84-ID universe frozen in-module = AW-01..AW-55 + AW-G2..AW-G31 **minus AW-G21** (no such finding); exit 1 on gap/dupe |
| `select_nodes.py` | `workspace/learning/select_nodes.py` (Plan 08, Gate E Option 1) — with `test_select_nodes.py` beside it | Node-selector so `/study` loads ~5 nodes not the 194KB graph; kept in the tutoring tree, NOT a new skill dir |

## 7. Resource topology

No GPU/parallel compute involved. Concurrency mechanics: max 6 concurrent subagents (repo policy), waves formed by disjoint `write_scope`s; most waves in this suite are 2–4 wide because the same files (always-on pair, `lint_all.py`, SKILL.mds) recur across tasks. The scarce resources are (a) the always-on rule files — never in two concurrent write_scopes, (b) `lint_all.py` — LINTS appends serialize through one task per plan, (c) user attention at gates A/B/C/E.

## 8. Execution order and session budget

Expected cadence: one plan-session per sitting (Plans 01–04 are 60–90 min sessions; 05–07 are wider but mechanical; 08 is short). Realistic total: **8 orchestrator sessions + 5 human actions**, landing inside two working weeks alongside research.

Standing session-close duties (every plan): run the plan's gate commands and paste evidence into the MR; one-line entry in `workspace/research/weekly-progress.md` Shipped; kill all terminals (EXIT GATE); do not start the next plan.

## 9. Findings-coverage matrix (script-asserted at closure)

Disposition legend: `NN/T*` = plan NN, fixed by its tasks (T* assigned at draft time) · `WONTFIX(reason)` — consciously rejected, reason recorded · split findings name their secondary plan in Notes. `check_coverage.py` fails on any AW-ID missing, duplicated, or dispositionless.

<!-- COVERAGE-MATRIX:BEGIN (generated from audit headings + decision-record mapping; verified 84/84) -->
| AW-ID | Sev | Finding (abridged) | Plan | Notes |
|---|---|---|---|---|
| AW-01 | B | Two live GS Confluence Personal Access Tokens committed in the tracked tree | 01 |  |
| AW-02 | B | Entire internal-GS tooling snapshot (credentials, endpoints, PII) resides on a personal off-… | 01 | H2/H4/H5 human limbs; in-repo limb closes in 01, off-perimeter limb is user-side |
| AW-03 | B | commandAllowlist terminal:["*"] auto-approves every terminal command; additionalReadAccessPa… | 01 |  |
| AW-04 | B | Task args-file interface has divergent specs: SKILL.md/prompt {run_id} filenames vs fixed pa… | 03 | lint half (lint_args_contract.py) lands in 04 |
| AW-05 | B | MODEL_TRAIN / NOTEBOOK / RESEARCH task wrappers invoke nonexistent Python modules — core ski… | 03 |  |
| AW-06 | B | CI has never run and cannot pass: push trigger misses the default branch and deps require th… | 02 |  |
| AW-G2 | H | 'Non-negotiable' Opus-4.6 subagent mandate is structurally unenforceable — no fallback model… | 05 | surface scoping begins in 02; prose fix + fallback clause in 05 |
| AW-G3 | H | Model pinned as a hardcoded display-name literal in 76 places — fragile against documented C… | 07 |  |
| AW-07 | H | Two mutually exclusive execution architectures both mandated as universal HARD rules; ./vol … | 02 |  |
| AW-08 | H | Live API credentials transmitted over TLS with certificate verification disabled (CERT_NONE)… | 01 |  |
| AW-09 | H | 'Zero Allow' create_and_run_task pattern is a deliberate permission-gate bypass, and lint.pr… | 03 |  |
| AW-G9 | H | No copilot-setup-steps.yml: ./vol hard-exits on the coding agent's runner (no uv, no nix), a… | 02 |  |
| AW-10 | H | CONFLUENCE skill mandates storing the PAT in git-tracked workspace/config/.env (not gitignor… | 01 |  |
| AW-11 | H | Prompt context files are bare backtick paths (0 of 34 use Markdown links); AGENTS.md falsely… | 07 |  |
| AW-12 | H | ~13-51 skill→memory references broke after a half-finished _dormant migration; invisible to … | 06 | lint half (broken-refs plain-text + _dormant) lands in 04 |
| AW-13 | H | Windows task layer hardcodes drive H: (workspaceFolder h:\ml-vol-estimator, H:\all-languages… | 03 |  |
| AW-14 | H | Non-negotiable ML constraints exist in 5-7 copies across 4 layers, the canonical owner is or… | 05 | PurgedKFold import fix lands in 06 (python.instructions.md) |
| AW-15 | H | memory/INDEX.md token estimates are wrong up to 10.8x, list dead paths, and P0+P1 is 81k tok… | 06 | lint half (bytes/4 math) lands in 04 |
| AW-16 | H | P0 boot file project-state.md self-contradicts on LSTM status and blockers and is ~40% stale… | 06 |  |
| AW-19 | H | python.instructions.md (3,083 tokens of GS data-access + ML rules) attaches to all 349 .py f… | 06 |  |
| AW-20 | H | yaml-config.instructions.md enum tables are stale vs the live registries it names as source … | 06 | canonical-completeness lint lands in 04 |
| AW-22 | H | Six of 14 policy files are orphaned from all loading surfaces, including two that self-decla… | 05 |  |
| AW-24 | H | /study, /quiz, /teach load a 194KB YAML graph + 22KB state (~54k tokens per session) despite… | 08 | CONTESTED finding — Gate E: selector script vs WONTFIX-with-reason, user decides |
| AW-25 | H | Prompt runbooks fork the skills they shadow: backtest/feature/research prompts re-implement … | 07 |  |
| AW-G27 | H | Coverage gate (--cov-fail-under=30) exists only in CI; ./vol test/test-all and pyproject enf… | 02 |  |
| AW-G28 | H | CI installs --dev only, not the `ml` extra, so every importorskip'd ML model test is silentl… | 02 |  |
| AW-G6 | M | memory/ref/vol-cli.md claims to "mirror ./vol help" but omits 13 of 33 vol commands, incl. t… | 03 |  |
| AW-G10 | M | All 43 run_task skill tasks live only in ml-vol-estimator.code-workspace; the folder-opened … | 03 |  |
| AW-G11 | M | Skill bootstrap wrappers assume GS-mapped H: drive (Windows) or a prebuilt src/.venv+nix (Li… | 02 | scope-out declaration in 02; _run.cmd fallback hardening in 03 |
| AW-G12 | M | AGENTS.md and copilot-instructions.md give contradictory terminal rules that livelock the co… | 02 |  |
| AW-G14 | M | No MCP config, no .github/agents, no .github/chatmodes: the coding agent has no alternative … | 02 |  |
| AW-G15 | M | data-audit.md Appendix marks tsdb.py OHLCV/treasury/fx/commodity fetchers TODO, but they're … | 06 |  |
| AW-G16 | M | memory/ref/vol-cli.md claims to mirror ./vol help but documents only 19 of the 33 vol subcom… | 03 |  |
| AW-17 | M | Research journal is forked: memory/INDEX.md routes continuity to a copy 8 weeks staler than … | 06 |  |
| AW-18 | M | Six flat-file skills plus an orphan ssp_helpers.py sit at skills/ root, violating the skill … | 07 |  |
| AW-G19 | M | user-manual.md hardcodes Linux /home/developer paths and the vol wrapper is bash/nix-only — … | 06 |  |
| AW-21 | M | A 14-check agentic-config lint suite has no deterministic trigger (CI/pre-commit both skip i… | 04 |  |
| AW-G22 | M | gnn feature-stack configs break at load when torch-geometric is absent; doc lists neither `g… | 06 |  |
| AW-23 | M | All 34 slash prompts pin premium 'Claude Opus 4.6' (incl. read-only dashboards and 161-byte … | 07 | lint_model_pins constant lands in 04 |
| AW-G23 | M | _CANONICAL_EXAMPLE.yaml violates its own Schema Maintenance Rule: missing conditional_duan, … | 06 |  |
| AW-G24 | M | Instruction doc's Optional Fields / enum tables omit real top-level schema: conditional_duan… | 06 |  |
| AW-G25 | M | Doc omits sequences.source enum (and bar_interval/lookback_days) and all daily_lookback sequ… | 06 |  |
| AW-26 | M | The two always-on files duplicate five rule blocks (~350-1,200 tokens/request) and have alre… | 05 |  |
| AW-27 | M | Lint-gate contradiction: always-on rule 6 declares lint DISABLED while working-agreements.md… | 05 |  |
| AW-28 | M | workspace/tmp/ and throwaway-script semantics contradict across the two always-on files (per… | 05 |  |
| AW-29 | M | Mandated market-data refs are 2x over the ref line cap and use Brazil-desk examples for a US… | 06 |  |
| AW-G29 | M | pre-commit mypy runs from repo root where no [tool.mypy] exists, dropping check_untyped_defs… | 04 |  |
| AW-30 | M | Task-Based Execution boilerplate copy-pasted into ~33 SKILL.mds (~27KB / 6,700 tokens) dupli… | 07 |  |
| AW-G30 | M | pre-commit ruff/ruff-format run repo-wide from root; files outside src/ get ruff DEFAULT con… | 04 |  |
| AW-31 | M | Skill-as-knowledge-store: FORWARD_NETWORK tells agents to 'consult' a 485KB (~121k token) Op… | 07 |  |
| AW-32 | M | Hardcoded real kerberos IDs, employee PII, and book/trade identifiers in write-capable skill… | 01 |  |
| AW-33 | M | GSSSO ~24h SSO cookie written plaintext to workspace/tmp/, which is not gitignored | 01 |  |
| AW-34 | M | _dormant is a load-bearing dependency of 10 skills + 2 active memory files but is excluded f… | 06 |  |
| AW-35 | M | subagent_protocol.md and context-isolation.md are ~80% redundant, the context-packet schema … | 05 |  |
| AW-36 | M | KILL_ORPHANS maintains two divergent process-killer implementations wired to different entry… | 03 |  |
| AW-37 | M | 'fix it.prompt.md' filename contains a space with no name: override and /housekeep has no pr… | 07 |  |
| AW-38 | M | plan.md forbids the exact yield-back that execute.md prescribes — the default plan->execute … | 05 |  |
| AW-40 | M | Personal-tutoring machinery occupies 6 of 34 slash commands and 490KB of tracked state in a … | 08 | Gate E decision: relocation scope |
| AW-41 | M | _run wrappers always exit 0, so bootstrap/lint failures and timeouts are invisible — the age… | 03 |  |
| AW-42 | M | Boot sequence specified twice with drift: AGENTS.md Boot Protocol vs workflows/bootup.md rea… | 05 |  |
| AW-43 | M | No prompt INDEX and no runnable onboarding path: .github/prompts/ is the only artifact layer… | 07 |  |
| AW-44 | M | pre-commit pins ruff v0.4.4 / mypy v1.10.0 while the project locks ruff 0.15.12 / mypy 2.0.0… | 04 |  |
| AW-45 | M | GIT skill's flagship 'Full push workflow' example uses git add -A, violating its own rule th… | 07 |  |
| AW-46 | M | 'powershell'-fenced examples use cmd-only ^ line continuation in 5 SLANG SKILL.md files | 03 |  |
| AW-47 | M | Keyword-dispatch registry routes only to de-scoped GS-internal skills; zero project skills r… | 07 | dispatch-registration lint half in 04 |
| AW-48 | M | memory/research/README.md is an orphaned stale second index that /research actively loads; I… | 06 |  |
| AW-G4 | L | Rule 9 forbids every currently-available Anthropic model (Sonnet, Haiku) and never names Cla… | 05 |  |
| AW-G5 | L | Two divergent identifier forms for the same pin — display name 'Claude Opus 4.6' vs slug 'cl… | 05 |  |
| AW-G7 | L | `forecast` is a registered, working CLI subcommand but has no ./vol case arm — unreachable t… | 03 |  |
| AW-G8 | L | `vol notebook` routes to external jupyter (self-admittedly usually absent) while the sibling… | 03 |  |
| AW-G13 | L | AGENTS.md hardwires the environment to 'Linux / Coder Workspace' with nix + H: + /sw/ficc as… | 02 |  |
| AW-G17 | L | workspace/scripts/ holds 15 git-tracked one-off analysis scripts with ~0 agentic references,… | 08 |  |
| AW-G18 | L | data-audit.md's only validation provenance points at a deleted ephemeral tmp/ probe script | 06 |  |
| AW-G20 | L | `vol present`/workspace/presentation is live CLI infra invisible to both P1 docs, while work… | 06 | vol-cli doc half lands in 03 |
| AW-G26 | L | Doc states ale_features default `top_10` but code default is `top_20` (contradicts its own e… | 06 |  |
| AW-G31 | L | addopts `--ignore=tests/slow` silently drops the whole tests/slow/ directory from every surf… | 08 | doc-correction alternative only (primary fix verifier-inverted) |
| AW-39 | L | CI lacks cost controls (no paths filter, no concurrency cancel, no dep cache) and runs bare … | 02 |  |
| AW-49 | L | Boot-protocol session-handoff check reads a file nothing writes, and the memory system is un… | 05 | AGENTS.md:58 backtick fix lands in 04 (one of the 3 failing checks made green); boot step 4 deleted in 05 |
| AW-50 | L | Dead routing pointers in live surfaces: phantom skills (APPDIR_API, CPNL_SUPPORT, GET_ISSUAN… | 07 |  |
| AW-51 | L | gsvivs-audit.prompt.md is a completed one-shot dated analysis stored as a permanent slash co… | 07 |  |
| AW-52 | L | Unreviewed machine-edit debris in SKILL.mds: corrupted headings and duplicate step numbering… | 07 |  |
| AW-53 | L | Model-pinning and routing rules restated in prose across many files (8+ workflow copies, 4 r… | 05 |  |
| AW-54 | L | PYTHON_PATH ships a 4.8KB Python resolver nothing references, and _run.cmd bypasses the skil… | 03 |  |
| AW-55 | L | memory/ref/vol-cli.md 'mirror' documents only 19 of 33 vol commands (omits the mandated test… | 03 | parity lint (lint_vol_parity.py) lands in 04 |

Per-plan totals: Plan 01: 7 · Plan 02: 10 · Plan 03: 14 · Plan 04: 4 · Plan 05: 13 · Plan 06: 18 · Plan 07: 14 · Plan 08: 4 — **84/84 disposed, 0 unassigned**.
<!-- COVERAGE-MATRIX:END -->
