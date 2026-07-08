# Plan 02 — Surface Contract & Always-On Execution-Rule Scoping

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §10.
> Dispatch each task as a subagent with the context packet provided. Max 2 concurrent subagents.
> TDD is a hard gate (copilot-instructions.md Rule 5) — **every edit in this plan is Rule-5-EXEMPT**
> (config, docs, YAML workflows only; zero `.py` files touched). Requires **Plan 01 merged + Gate A
> confirmed**, and **Gates B and C decided by the user BEFORE Wave 1 dispatch** (§2).

**Goal:** AGENTS.md and `.github/copilot-instructions.md` declare exactly two supported execution surfaces (S-A, S-B) and scope every execution rule to a surface, killing the universal-rule fictions AW-06, AW-07, AW-G9, AW-G11, AW-G12, AW-G13, AW-G14, AW-G27, AW-G28, AW-39 — verified by a contradiction-grep list that returns 0.

**Architecture:** The load-bearing edit rewrites AGENTS.md's existing `## Environment (Linux / Coder Workspace)` section (AGENTS.md:212–217 region) into `## Supported Execution Surfaces` — **no new policy file** (honors the no-14th-policy-file guardrail and the do-not-rebuild inventory). One always-on scoping line plus per-surface rewrites of Critical Rules 2/3/8 land in `.github/copilot-instructions.md`. `ci.yml` is documented mirror-only (Gate C default) with the AW-06/G27/G28/39 fixes applied in place. Everything plugs into existing seams: the two always-on files, the existing `ci.yml`, and (conditionally) a new `.gitlab-ci.yml` invoking the existing `workspace/lint/lint_all.py`.

**Tech stack:** No new dependencies. All edits are Markdown/YAML. The optional `.gitlab-ci.yml` job runs the existing stdlib-only lint suite.

**Research grounding:** The 2026-07 agentic-workflow audit (`deliverables/copilot-workflow-audit.md`), findings AW-06 · AW-07 · AW-G9 · AW-G11 · AW-G12 · AW-G13 · AW-G14 · AW-G27 · AW-G28 · AW-39, all re-verified live 2026-07-07. Expected-outcome prior: this plan's win is **binary, not token-denominated** — the contradiction greps in §9 go from "present" to "0 hits", and the always-on files contain exactly one execution rule per surface. No token-saving claims belong here (those are Plans 05/06). **Calibration warning:** if a grep passes trivially on the pre-fix tree, the cited rule text has drifted since 2026-07-07 — STOP and reconcile before editing (standing drift-check constraint, 00-overview §1). None of the audit's 10 ROI quick-wins map to this plan's findings, so Wave 1 carries no quick-win rider.

---

## 1. Global constraints

All of 00-overview §5 (shared conventions) applies. Plan-specific hard rules:

1. **Self-modification hazard (00-overview §1):** this plan rewrites the always-on rules that govern the executing session itself. Every packet quotes the rule text as-of-execution; if a quoted rule no longer matches the live file, the subagent STOPS and returns `blocked` with the diff. Never improvise a reconciliation.
2. **Drift check:** verify every cited `path:line` against the live tree before editing; if it moved, locate by the content patterns given in each task and note the delta in the return contract.
3. **Scope fence — do NOT touch:** AGENTS.md Boot Protocol (lines 54–60 region — the `session-handoff.md` broken link there is Plan 04's, AW-49); AGENTS.md Key Constraints table (77–86 region — Plan 05, AW-14); the rule-block *duplication* between the two always-on files (Plan 05, AW-26 — this plan **scopes** rules, it does not dedupe them, with the single exception noted in Task 1 Step 3); `policy/`, `workflows/`, `personas/`, `skills/`, `memory/` (later plans); `vol`, `src/**` (Plan 03+); `.pre-commit-config.yaml` (Plan 04, AW-44/G29/G30).
4. **The 5 ACTIVE research plans in `workspace/plans/` are read-only; never touch `trials.yaml` or `workspace/configs/`.**
5. **AW-06 do-NOT:** never set the ci.yml trigger to `[master, main]` blindly — the branch value is measured at execution time (Task 3 Step 2).
6. **AW-39 do-NOTs:** do not align CI mypy flags with `./vol`; do not route CI through `./vol` (it is hardwired to the GS nix/Coder env and cannot run on ubuntu-latest).
7. **AW-G27 do-NOT:** do not add `--cov-fail-under` to `src/pyproject.toml` addopts (would false-fail the fast `-m "not slow"` loop) — this plan ships the coverage **note** only.
8. **Lint baseline invariant:** `python workspace/lint/lint_all.py` fails exactly the same 3/15 checks (design rules, broken refs, vscode md compat) before and after this plan — captured and diffed in every task. New text must not add a broken reference: backtick file refs only, only to files that exist at HEAD, never Markdown links in prompt-adjacent files.
9. **Never run this plan while a research `/execute` session is live.**
10. Branch: `chore/wf-overhaul-02-surfaces` off `master`; rebase onto `origin/master` before push; MR-only; never amend; never `git add -A`.

---

## 2. Gate decisions (user records BOTH before Wave 1)

The orchestrator presents these two decisions, records the outcomes in the MR description and in `workspace/research/weekly-progress.md` (Decided section), and only then dispatches Wave 1.

### Gate B — Is the GitHub cloud coding agent (S-C) a supported consumer? **Default: NO.**

Rationale for NO (AW-G11, decisive): even a fully provisioned cloud runner cannot reach `*.gs.com` data services — every skill targets them, so "provisioning src/.venv would not help"; `./vol` hard-exits at `vol:20` (no uv/nix); 0 of 43 `run_task` labels resolve (tasks live only in the `.code-workspace`, AW-G10).

- **NO (default):** Tasks 1 and 2 land the scope-out lines. This closes AW-G9, AW-G12, AW-G14 and the scope-out halves of AW-G10/AW-G11 (their compute halves land in Plan 03). Appendix 02b (§8) is NOT executed.
- **YES (override):** Tasks 1 and 2 still land (with the S-C row swapped to the LIMITED variant given in §8), and Appendix 02b is dispatched as an extra Wave-2 task. Appendix 02b is **optional and never a blocker** — Plan 03 does not depend on it either way.

### Gate C — Where does CI live? **Default: ci.yml documented as GitHub-mirror-only, fixed in place.**

The real remote is GS GitLab (`memory/ref/git-workflow.md:16` — `https://gitlab.aws.site.gs.com/eq-tech/sts/ml-vol-estimator`, `master` protected/default). `.github/workflows/ci.yml` can therefore never fire on the real remote; it fires only on the personal GitHub mirror, and per AW-06 it has fired **0 times ever** even there.

- **Default (mirror-only):** Task 3 documents ci.yml as mirror-only AND applies the AW-06 fixes so the mirror workflow can actually run and pass: trigger branches set to the mirror's **measured** default branch (never `[master, main]` blindly), `UV_INDEX_URL` public-index override (the GS PyPI mirror at `src/uv.toml:7` is unreachable from ubuntu-latest), `--extra ml` (AW-G28), coverage note (AW-G27), and the CONFIRMED AW-39 cost controls only (paths filter, concurrency cancel, dep cache).
- **Alternative (GitLab CI):** additionally dispatch Task 4, which adds a `.gitlab-ci.yml` lint job on the real remote. Task 3 still executes (the mirror file still needs its lies fixed). Prerequisite for Task 4: the user confirms a usable GitLab runner exists on the GS instance; if none exists, record the decision as "mirror-only; pre-commit hook (Plan 04) is the only automated trigger" (decision-record open risk 6).

---

## 3. File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `AGENTS.md` | §Environment (212–217 region) → `## Supported Execution Surfaces` (S-A/S-B/S-C per ledger); reconcile the :157 run_task-primary bullet; :143 delegation honored |
| Modify | `.github/copilot-instructions.md` | Rules 2/3/8 scoped per surface; one always-on S-C scope-out line |
| Modify | `.github/workflows/ci.yml` | Mirror-only header; measured-branch trigger; `UV_INDEX_URL`; `--extra ml`; coverage note; paths filter + concurrency cancel + dep cache |
| Create (Gate C = GitLab only) | `.gitlab-ci.yml` | `workspace-lint` job running `workspace/lint/lint_all.py` on the real remote |
| Create (Gate B = YES only, Appendix 02b) | `.github/workflows/copilot-setup-steps.yml` | S-C runner provisioning (uv + public index) |

---

## 4. Interfaces

**Consumes (from the ledger / Plan 01):**
- Gate A passed (Plan 01 merged; secrets dead).
- Ledger `S-A` / `S-B` / `S-C` definitions (00-overview §6) — copied verbatim into the AGENTS.md table below, never re-derived.
- Ledger rule-2 scoping phrase: "`./vol` for all Python/CLI on S-B; on S-A use `vol.cmd`/`run_task` equivalents once Plan 03 lands (until then, S-A tasks are doc/config-only or routed to S-B)."
- `workspace/lint/lint_all.py` as-is (15 checks, 3 failing — baseline only, no edits).

**Produces (later plans rely on these):**
- `AGENTS.md` → `## Supported Execution Surfaces` section — the surface table every Plan 03–08 packet cites for S-A/S-B/S-C semantics. Plan 03's `vol.cmd` + `.vscode/tasks.json` slot into the S-A row's named seams.
- `.github/copilot-instructions.md` Rules 2/3/8 in per-surface form — the rule text-as-of-execution that Plans 03–08 packets quote; Plan 05 dedupes around this wording without changing its meaning.
- `.github/workflows/ci.yml` mirror-only contract (Gate C record) — Plan 04 wires the pre-commit trigger knowing CI is mirror-only (or GitLab, per the recorded decision).
- (Conditional) `.gitlab-ci.yml` `workspace-lint` job — Plan 04 flips its `allow_failure: true` to `false` when the lint suite goes green.

---

## 5. Task 1: Rewrite AGENTS.md Environment section into the Supported Execution Surfaces contract

**Files:** Modify — `AGENTS.md` (the `## Environment (Linux / Coder Workspace)` section, 212–217 region, and the :157 task-execution bullet). Nothing else in the file.

**Kills / advances:** AW-G13 (env hardwiring → surface table), AW-07 AGENTS.md half, AW-G12 AGENTS.md half (competing :157 rule removed; :143 delegation honored), AW-G9/G11/G14 scope-out halves (S-C row + wrapper-scoping paragraph).

**Copilot context packet:**

```yaml
subtask_id: "wfo-02-1"
goal: "Replace AGENTS.md's '## Environment (Linux / Coder Workspace)' section with the '## Supported Execution Surfaces' table (S-A/S-B/S-C verbatim from the plan) and replace the :157 run_task-primary bullet with a pointer that defers terminal mechanics to copilot-instructions.md, verified by the Task-1 grep set."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-02-surface-contract.md   # §5 — replacement text lives HERE
  - AGENTS.md
  - .github/copilot-instructions.md      # read-only: confirm the delegation target exists
  - memory/ref/vol-cli.md                # read-only: confirm the preserved pointer target exists
write_scope:
  - AGENTS.md
acceptance_criteria:
  - "git grep -n 'Environment (Linux / Coder Workspace)' -- AGENTS.md → no matches (exit 1)"
  - "git grep -n 'Tools are on PATH via nix' -- AGENTS.md → no matches"
  - "git grep -n 'fall back to run_in_terminal' -- AGENTS.md → no matches"
  - "git grep -c 'Supported Execution Surfaces' -- AGENTS.md → >= 1"
  - "git grep -c 'UNSUPPORTED' -- AGENTS.md → >= 1 (Gate B NO) — or the §8 LIMITED row if Gate B = YES"
  - "python workspace/lint/lint_all.py → identical failing set to pre-edit baseline (3/15: design rules, broken refs, vscode md compat)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "SELF-MODIFICATION HAZARD: this file governs your session. Quote the old section and the old :157 bullet verbatim in your return BEFORE deleting; if either content-locator matches 0 or >1 places, STOP and return blocked with the diff"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "do NOT touch AGENTS.md lines 54-60 (boot protocol, incl. the known-broken session-handoff link — Plan 04's), 77-86 (Key Constraints — Plan 05's), or any other section"
  - "backtick file refs only, targets must exist at HEAD; no Markdown links"
context_summary: |
  The audit proved every governance fiction traces to rules written as universal while the
  compute they mandate exists only on specific machines (AW-07/G9/G11/G12/G13/G14). The suite's
  decision record fixed the remedy: declare S-A (GS Windows, PRIMARY) and S-B (Linux Coder)
  supported, S-C (cloud coding agent) unsupported by default — Gate B decision is recorded in
  the MR description; check it before choosing the S-C row variant. The replacement text is
  final in plan §5; do not redesign it. vol.cmd and .vscode/tasks.json do not exist yet
  (Plan 03) — the S-A row already words that correctly.
depends_on: []
```

- [ ] **Step 1 — Baseline (the docs analog of "red"):** capture the pre-edit state proving the contradictions are live, and the lint baseline:
  ```bash
  git grep -n "Environment (Linux / Coder Workspace)" -- AGENTS.md      # expect: 1 hit (~line 212)
  git grep -n "Tools are on PATH via nix" -- AGENTS.md                  # expect: 1 hit (~line 216)
  git grep -n "fall back to run_in_terminal" -- AGENTS.md               # expect: 1 hit (~line 157)
  python workspace/lint/lint_all.py                                      # expect: FAILED (3/15): design rules, broken refs, vscode md compat
  ```
  (On S-A, run the lint via the existing `lint-workspace` VS Code task and `read_file` its OUTPUT_FILE; on S-B via `./vol exec python workspace/lint/lint_all.py`.) Paste all four outputs into the return contract's `verification`. If any grep already returns 0, the tree drifted — return `blocked`.

- [ ] **Step 2 — Replace the Environment section.** Delete everything from the `## Environment (Linux / Coder Workspace)` heading up to (not including) the next `##` heading. Quote the deleted block verbatim in your return. Insert in its place, verbatim:

  ```markdown
  ## Supported Execution Surfaces

  This repo runs on exactly two supported surfaces. Every execution rule in this file and in
  `.github/copilot-instructions.md` is scoped to a surface; a rule with no surface tag applies
  to both supported surfaces.

  | ID | Surface | Status | Compute path |
  |----|---------|--------|--------------|
  | S-A | GS Windows desktop — H: drive, VS Code Chat, `ml-vol-estimator.code-workspace` opened as a multi-root workspace | **PRIMARY** | `run_task` labels → per-skill `.cmd` wrappers → `skills/_shared/_run.cmd`. Dev loop (`test`/`lint`/`fmt`/`typecheck`) via the `vol.cmd` shim once it lands; until then S-A sessions are doc/config-only or route compute to S-B |
  | S-B | GS Linux Coder workspace — nix + uv, Python 3.11 UV-managed (`nix-env -iA nixpkgs.uv` if missing) | Secondary | `./vol` (all arms), per-skill `.sh` wrappers via `skills/_shared/_run.sh` |
  | S-C | GitHub cloud coding-agent runner (ephemeral Ubuntu) | **UNSUPPORTED** | None — do not dispatch work here. Rationale: no uv/nix so `./vol` hard-exits; the `.code-workspace` is never parsed so 0 of 43 `run_task` labels resolve; and every skill targets `*.gs.com` services unreachable from cloud runners — provisioning a venv would not help |

  Skill wrappers are GS-environment-only: `.cmd` wrappers assume the H: drive (S-A);
  `.sh` wrappers assume the Coder workspace `src/.venv` + nix (S-B). Neither runs on S-C.

  CLI reference: `memory/ref/vol-cli.md`. If a command seems missing there, run `./vol help`
  (S-B) — the doc is being reconciled to the help text.

  Terminal mechanics (isolation, `./vol exec`/`bg`, cleanup, bare-tool bans) are owned by
  `.github/copilot-instructions.md` Critical Rules 2, 3, 4 and 8 — this file does not define
  a competing rule.
  ```

  **Gate B = YES only:** use the S-C row variant from §8 instead of the UNSUPPORTED row above.
  **Carry-over rule:** if the deleted block contained a factual line not represented above and not one of the superseded universal claims ("Tools are on PATH via nix. No env scripts needed." / the :217 never-run restatement), fold it into the matching surface row and say so in `notes`. Dropping the :217 duplicate never-run list is deliberate — the table defers to copilot-instructions Rule 2 (note in your return that this pre-empts one of AW-26's five duplicated blocks; AW-26 itself stays Plan 05).

- [ ] **Step 3 — Reconcile the :157 bullet.** Locate the single bullet matching `git grep -n "fall back to run_in_terminal" -- AGENTS.md` (0 or >1 hits → `blocked`). Quote it verbatim in your return, then replace the entire bullet with, verbatim:

  ```markdown
  - **Task execution:** on S-A prefer predefined `run_task` labels where one exists. Where no
    predefined task covers the need, `run_in_terminal` with `isBackground=true` wrapping the
    surface's wrapper (`./vol exec …` on S-B) is the sanctioned form — never a raw, un-isolated
    command. Terminal mechanics are owned by `.github/copilot-instructions.md` §3.
  ```

  Leave the surrounding delegation line (the AGENTS.md:143-region "terminal rules → copilot-instructions.md" delegation) untouched — the fix honors it by removing the competing rule, not by rewording the delegation.

- [ ] **Step 4 — Run to green:** re-run the four Step-1 commands. Expected: the three greps now return **no matches** for the old strings, `git grep -c "Supported Execution Surfaces" -- AGENTS.md` ≥ 1, and the lint output is byte-identical in its failing set to Step 1 (same 3 checks, same broken-ref count of 2). Paste outputs.

- [ ] **Step 5 — Commit:**
  ```
  docs: scope AGENTS.md environment section to supported execution surfaces
  ```

---

## 6. Task 2: Scope copilot-instructions.md Rules 2/3/8 per surface + the always-on S-C scope-out line

**Files:** Modify — `.github/copilot-instructions.md` (Rules 2, 3, 8 bodies; one inserted line after the Critical Rules preamble). No other rules touched (Rule 6 lint policy is Plan 05's, AW-27; Rule 9 model pinning is Plan 05/07's, AW-G2/G3).

**Kills / advances:** AW-07 copilot-instructions half, AW-G12 copilot-instructions half, AW-G9/G14 scope-out (the one always-on line).

**Copilot context packet:**

```yaml
subtask_id: "wfo-02-2"
goal: "Rewrite copilot-instructions.md Rules 2, 3 and 8 into the per-surface forms given in plan §6 and insert the one-line S-C scope-out after the Critical Rules preamble, verified by the Task-2 grep set."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-02-surface-contract.md   # §6 — replacement text lives HERE
  - .github/copilot-instructions.md
  - AGENTS.md                            # read-only: the Supported Execution Surfaces section Task 1 just landed
write_scope:
  - .github/copilot-instructions.md
acceptance_criteria:
  - "git grep -n 'The `./vol` wrapper handles everything' -- .github/copilot-instructions.md → no matches"
  - "git grep -n 'Run ALL commands via' -- .github/copilot-instructions.md → no matches"
  - "git grep -c 'S-B' -- .github/copilot-instructions.md → >= 3 (rules 2, 3, 8 each scoped)"
  - "git grep -c 'Supported Execution Surfaces' -- .github/copilot-instructions.md → >= 1 (scope-out line cross-ref)"
  - "git grep -c 'coding agent' -- .github/copilot-instructions.md → >= 1"
  - "python workspace/lint/lint_all.py → identical failing set to pre-edit baseline (3/15)"
memory_refs: []
constraints:
  - "verify the cited rule text against the live tree before editing; the plan quotes Rules 2/3/8 as-of-2026-07-07 — if the live text differs, STOP and return blocked with the diff (SELF-MODIFICATION HAZARD: these rules govern your session)"
  - "do NOT touch Rules 1, 4, 5, 6, 7, 9 or any other content in the file"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "backtick file refs only, targets must exist at HEAD; no Markdown links"
context_summary: |
  Task 1 has already landed the AGENTS.md Supported Execution Surfaces table this file now
  points to — do not restate the table here, point to it. The per-surface rule wording below is
  final (ledger 00-overview §5.3 rule 2 phrasing is embedded verbatim); do not redesign it.
  vol.cmd does not exist yet (Plan 03) — the wording already accounts for that. Gate B's
  recorded decision only affects the scope-out line's variant noted in Step 2.
depends_on: ["wfo-02-1"]
```

- [ ] **Step 1 — Baseline:** confirm the as-of-execution rule text matches the plan's quotes and capture lint baseline:
  ```bash
  git grep -n "The \`./vol\` wrapper handles everything" -- .github/copilot-instructions.md   # expect: 1 hit (Rule 2)
  git grep -n "Run ALL commands via" -- .github/copilot-instructions.md                        # expect: 1 hit (Rule 3)
  git grep -n "No Bare Tool Invocations" -- .github/copilot-instructions.md                    # expect: 1 hit (Rule 8)
  python workspace/lint/lint_all.py                                                             # expect: FAILED (3/15), broken refs = 2
  ```
  The old texts being replaced (quoted as-of-2026-07-07; STOP if the live file differs):
  - Rule 2 body: "**NEVER** run `python`, `pytest`, `pip`, `uv`, or `mypy` directly — they will fail silently (wrong venv, missing LD_LIBRARY_PATH, broken nix deps). The `./vol` wrapper handles everything." (+ the equivalences table)
  - Rule 3 opens: "Run ALL commands via `./vol exec` or `./vol bg`. **NEVER** run compute commands directly in the terminal." followed by the four NEVER/ALWAYS bullets.
  - Rule 8: the bare-tool → `./vol` equivalence table titled "No Bare Tool Invocations".

- [ ] **Step 2 — Insert the scope-out line.** Immediately after the Critical Rules preamble (the "apply to ALL agents in ALL modes" line region), insert, verbatim:

  ```markdown
  **Execution surfaces:** exactly two are supported — S-A (GS Windows desktop, VS Code Chat) and
  S-B (GS Linux Coder workspace). The GitHub cloud coding agent (S-C) is **UNSUPPORTED**: `*.gs.com`
  services are unreachable from cloud runners, `./vol` hard-exits there, and no `run_task` labels
  resolve. Surface definitions: `AGENTS.md` → Supported Execution Surfaces.
  ```

  **Gate B = YES only:** replace "**UNSUPPORTED**: … resolve." with "**LIMITED** — src-only tests via `copilot-setup-steps.yml` provisioning; no GS data access, no skills, no `run_task`."

- [ ] **Step 3 — Rewrite Rule 2** (keep its heading number; replace body + retitle), verbatim:

  ```markdown
  ## 2. Python/CLI: Use the Surface's Wrapper — Never Bare Tools
  Surfaces per `AGENTS.md` → Supported Execution Surfaces.
  - **S-B (Linux Coder):** ALWAYS use `./vol` (`shell|test|lint|fmt|exec|bg|sync`). **NEVER** run
    `python`, `pytest`, `pip`, `uv`, `ruff`, or `mypy` directly — they fail silently (wrong venv,
    missing LD_LIBRARY_PATH, broken nix deps).
  - **S-A (GS Windows):** use `vol.cmd`/`run_task` equivalents once the Windows shim lands
    (until then, S-A tasks are doc/config-only or routed to S-B). `./vol` is bash-only and does
    not run on Windows.
  - **S-C:** unsupported — do not dispatch compute here.
  ```

  Keep the existing equivalences table beneath it, adding one header line above the table: "*(S-B forms; S-A equivalents arrive with `vol.cmd`.)*". Note: `ruff` is added to the never-run list here deliberately — it resolves the AW-26 ruff drift in the direction of the stricter list (record in `notes`; the AGENTS.md-side duplicate was already removed by Task 1).

- [ ] **Step 4 — Rewrite Rule 3** (keep heading number), verbatim:

  ```markdown
  ## 3. Terminal Isolation (both supported surfaces)
  - **S-B:** run ALL compute via `./vol exec` or `./vol bg`. **NEVER** run compute commands
    directly in the terminal.
  - **S-A:** run compute via the predefined VS Code tasks (their wrappers write the same
    `OUTPUT_FILE=` sentinel). Where no task exists and `vol.cmd` has not landed, the session is
    doc/config-only or routes compute to S-B.
  - **NEVER** trust terminal buffer output — always `read_file` on the OUTPUT_FILE path.
  - **ALWAYS** use `isBackground=true` for every `run_in_terminal` call.
  - **NEVER** use `setsid`, `nohup`, `&`, `disown`, or any manual signal-isolation trick.
  - If you see "terminal is blocked" or KeyboardInterrupt — use `./vol exec` (S-B). Do NOT retry.
  ```

- [ ] **Step 5 — Retitle Rule 8** to "No Bare Tool Invocations (per-surface wrappers)" and prepend one line above its table, verbatim: "Applies on both supported surfaces; the right-hand forms are S-B's — on S-A use the predefined task / `vol.cmd` equivalent once it lands." The table rows themselves are unchanged.

- [ ] **Step 6 — Run to green:** run the Task-2 acceptance greps (packet) — old strings 0 hits, `S-B` ≥ 3, cross-ref present — and re-run the lint suite: failing set identical to Step 1. Paste outputs.

- [ ] **Step 7 — Commit:**
  ```
  chore(ci): scope copilot hard rules 2/3/8 per execution surface
  ```

---

## 7. Task 3: ci.yml — mirror-only contract with the AW-06/G27/G28/39 fixes applied

**Files:** Modify — `.github/workflows/ci.yml` only.

**Kills:** AW-06 (trigger + deps), AW-G28 (`--extra ml`), AW-G27 (coverage note — the pyproject gate move is consciously NOT done, constraint 7), AW-39 (CONFIRMED cost-control parts only).

**Copilot context packet:**

```yaml
subtask_id: "wfo-02-3"
goal: "Apply the six surgical ci.yml edits in plan §7 (mirror-only header, measured-default-branch trigger + paths filter, concurrency cancel, uv cache, UV_INDEX_URL + --extra ml, coverage note), verified by the Task-3 grep set."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-02-surface-contract.md   # §7 — edit snippets live HERE
  - .github/workflows/ci.yml
  - src/uv.toml                          # read-only: confirm the GS-only index claim cited in the header
  - memory/ref/git-workflow.md           # read-only: confirm the GitLab-remote claim cited in the header
write_scope:
  - .github/workflows/ci.yml
acceptance_criteria:
  - "git grep -n 'branches: \\[main, develop\\]' -- .github/workflows/ci.yml → no matches"
  - "git grep -c 'MIRROR-ONLY' -- .github/workflows/ci.yml → >= 1"
  - "git grep -c 'extra ml' -- .github/workflows/ci.yml → 1"
  - "git grep -c 'UV_INDEX_URL' -- .github/workflows/ci.yml → 1"
  - "git grep -c 'cancel-in-progress' -- .github/workflows/ci.yml → 1"
  - "git grep -c 'enable-cache' -- .github/workflows/ci.yml → 1"
  - "git grep -c 'paths:' -- .github/workflows/ci.yml → 2 (push + pull_request)"
  - "git grep -c 'AW-G27' -- .github/workflows/ci.yml → 1 (coverage note)"
  - "python -c \"import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))\" → exit 0 (run via the surface's wrapper), OR a YAML-parse via the editor if no interpreter path is sanctioned yet on S-A"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "do NOT change mypy flags, do NOT route CI through ./vol (AW-39 refuted-parts do-NOT)"
  - "do NOT hardcode branches: [master, main] — measure the mirror's default branch (Step 2); fallback value 'main' as measured 2026-07-07, and say which path you took in notes"
  - "do NOT touch src/pyproject.toml (AW-G27 note-only in this plan)"
  - "the 5 research plans in workspace/plans/ are read-only"
context_summary: |
  Gate C's recorded decision (default: mirror-only) is in the MR description. The real remote is
  GS GitLab so this workflow can never fire there; it exists for the personal GitHub mirror,
  where it has fired 0 times because the trigger misses the default branch and uv can only see
  the GS-internal PyPI index. This task makes the file honest (header) and runnable (fixes).
  ci.yml as-of-2026-07-07: push trigger '[main, develop]' at ~:5, setup-uv@v3 at ~:25,
  'uv sync --dev' at ~:28, mypy at ~:37, pytest with --cov-fail-under=30 at ~:40.
depends_on: []
```

- [ ] **Step 1 — Baseline:** `git grep -n "branches:" -- .github/workflows/ci.yml` (expect the `[main, develop]` hit), `git grep -n "uv sync" -- .github/workflows/ci.yml` (expect `uv sync --dev`, no `--extra ml`), lint baseline as in Task 1. Paste outputs.

- [ ] **Step 2 — Measure the mirror's default branch.** If a GitHub remote is configured on the executing clone: `git ls-remote --symref <github-remote-name> HEAD` → read `ref: refs/heads/<BRANCH>`. If no GitHub remote is reachable from the GS box, use the fallback `main` (measured 2026-07-07 via the GitHub API on the mirror) and record "fallback used" in `notes`. `<MIRROR_DEFAULT>` below = that value. **Never write `[master, main]`.**

- [ ] **Step 3 — Apply the six edits** (surgical; everything not named stays byte-identical):

  **(a) Header comment** — insert at the very top of the file:
  ```yaml
  # ============================================================================
  # MIRROR-ONLY WORKFLOW (Gate C, plan-02, 2026-07): the real remote is GS GitLab
  # (memory/ref/git-workflow.md — gitlab.aws.site.gs.com/eq-tech/sts/ml-vol-estimator),
  # where GitHub Actions never fire. This file runs ONLY on the personal GitHub
  # mirror and only if that mirror's default branch carries it. It is NOT the
  # project's quality gate — the lint gate lives in workspace/lint/ (pre-commit
  # trigger: Plan 04). CI here is the sanctioned bare-command context: ./vol
  # cannot run on ubuntu-latest (nix/GS-internal deps), so ruff/mypy/pytest run
  # directly, with --ignore-missing-imports on mypy for absent GS packages.
  # ============================================================================
  ```

  **(b) Trigger** — replace the existing `on:` block's branch/path config with:
  ```yaml
  on:
    push:
      branches: [<MIRROR_DEFAULT>]
      paths: ['src/**', '.github/workflows/ci.yml']
    pull_request:
      branches: ["**"]
      paths: ['src/**', '.github/workflows/ci.yml']
  ```

  **(c) Concurrency** — insert at top level (after `on:`):
  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
  ```

  **(d) Cache** — on the `astral-sh/setup-uv@v3` step add:
  ```yaml
        with:
          enable-cache: true
  ```

  **(e) Deps** — replace the sync step's run line and add the index override:
  ```yaml
        - name: Install dependencies (public PyPI — the GS mirror in src/uv.toml is unreachable from ubuntu-latest)
          env:
            UV_INDEX_URL: https://pypi.org/simple
          run: uv sync --dev --extra ml   # --extra ml (AW-G28): without it every importorskip'd lightgbm/xgboost/optuna/shap test is silently SKIPPED here while ./vol test-all runs them
  ```

  **(f) Coverage note** — insert immediately above the pytest step:
  ```yaml
        # NOTE (AW-G27): this --cov-fail-under=30 is the ONLY coverage gate anywhere.
        # ./vol test / ./vol test-all measure no coverage, so local green is not a
        # coverage signal. Do not copy this gate into pyproject addopts — it would
        # false-fail the fast `-m "not slow"` loop (Plan 04 owns any gate unification).
  ```

- [ ] **Step 4 — Run to green:** run the Task-3 acceptance greps (packet list) — all expected values; validate the YAML parses (S-B: `./vol exec python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`; S-A: editor YAML diagnostics clean). Lint baseline unchanged. Paste outputs.

- [ ] **Step 5 — Commit:**
  ```
  chore(ci): document ci.yml as mirror-only; fix trigger, deps, cost controls
  ```

---

## 8. Task 4 (CONDITIONAL — dispatch only if Gate C = GitLab): `.gitlab-ci.yml` lint job

**Files:** Create — `.gitlab-ci.yml` at repo root. Skipped entirely under the Gate C default; skipping it is NOT a blocker for Plan 03.

**Copilot context packet:**

```yaml
subtask_id: "wfo-02-4"
goal: "Create .gitlab-ci.yml at repo root containing exactly the workspace-lint job in plan §8, so the stdlib-only lint suite runs on the real GS GitLab remote for MRs and the default branch."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-02-surface-contract.md   # §8 — the full file lives HERE
  - workspace/lint/lint_all.py           # read-only: confirm invocation path + stdlib-only claim
  - memory/ref/git-workflow.md           # read-only: remote/branch conventions
write_scope:
  - .gitlab-ci.yml
acceptance_criteria:
  - "test -f .gitlab-ci.yml → exit 0"
  - "git grep -c 'workspace-lint' -- .gitlab-ci.yml → 1"
  - "git grep -c 'allow_failure: true' -- .gitlab-ci.yml → 1"
  - "YAML parses (same mechanism as Task 3 Step 4)"
  - "python workspace/lint/lint_all.py → identical failing set to baseline (this task adds a runner config, it must not alter lint results)"
memory_refs: []
constraints:
  - "verify with the user (via the orchestrator, pre-dispatch) that a GitLab runner is available — this task must not be dispatched otherwise"
  - "allow_failure stays true in this plan: the suite is known-red 3/15 until Plan 04; Plan 04 flips it"
  - "do not add ruff/mypy/pytest jobs here — runner image capabilities are unconfirmed; the lint job is deliberately the only job (extension is a Plan 04 decision)"
  - "the 5 research plans in workspace/plans/ are read-only"
context_summary: |
  Gate C's recorded decision chose the GitLab-CI alternative branch. The lint suite
  (workspace/lint/lint_all.py, 15 checks, stdlib-only, ~2.4s) currently fails 3/15; Plan 04
  makes it green and flips allow_failure. This job is the "real gate on the real remote"
  half; ci.yml remains mirror-only per Task 3 regardless.
depends_on: []
```

- [ ] **Step 1 — Baseline:** `test -f .gitlab-ci.yml` → exit 1 (must not already exist; if it exists, return `blocked` with its content).

- [ ] **Step 2 — Create `.gitlab-ci.yml`**, verbatim:

  ```yaml
  # Agentic-config lint gate on the real GS GitLab remote (Gate C alternative, plan-02).
  # Runs the stdlib-only workspace lint suite. Deliberately the ONLY job: ruff/mypy/pytest
  # need GS-internal deps/images and are a Plan 04 decision.
  stages: [lint]

  workspace-lint:
    stage: lint
    image: python:3.11-slim   # any Python >= 3.10 runner image works — the suite is stdlib-only
    rules:
      - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    script:
      - python workspace/lint/lint_all.py
    allow_failure: true   # suite is known-red (3/15) until Plan 04 fixes it; Plan 04 flips this to false
  ```

- [ ] **Step 3 — Run to green:** acceptance greps from the packet; YAML parse check; lint baseline unchanged. Paste outputs.

- [ ] **Step 4 — Commit:**
  ```
  chore(ci): add gitlab workspace-lint job (allow_failure until suite green)
  ```

---

## 8b. OPTIONAL APPENDIX — Plan 02b (Gate B = YES override only; never a blocker)

Executed only if the user overrides Gate B to YES. This is a specification, not a default task; it adds one Wave-2 task (`wfo-02-5`, write_scope `.github/workflows/copilot-setup-steps.yml`; full context packet below) and swaps two row/line variants in Tasks 1–2.

**Copilot context packet for `wfo-02-5`:**

```yaml
subtask_id: "wfo-02-5"
goal: "Create .github/workflows/copilot-setup-steps.yml containing exactly the copilot-setup-steps job in plan §8b.3, so the GitHub Copilot coding-agent runner (S-C) provisions Python 3.11 + uv against public PyPI for src-only tests (Gate B = YES override)."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-02-surface-contract.md   # §8b.3 — the full file lives HERE
  - src/uv.toml                          # read-only: confirm the GS-only index claim behind the UV_INDEX_URL override
  - .github/workflows/ci.yml             # read-only: the setup-uv + UV_INDEX_URL pattern Task 3 landed, mirrored here
write_scope:
  - .github/workflows/copilot-setup-steps.yml
acceptance_criteria:
  - "test -f .github/workflows/copilot-setup-steps.yml → exit 0"
  - "git grep -c 'copilot-setup-steps' -- .github/workflows/copilot-setup-steps.yml → 2 (push-path filter + job id)"
  - "git grep -c 'actions/setup-python@v5' -- .github/workflows/copilot-setup-steps.yml → 1"
  - "git grep -c 'astral-sh/setup-uv@v3' -- .github/workflows/copilot-setup-steps.yml → 1"
  - "git grep -c 'UV_INDEX_URL' -- .github/workflows/copilot-setup-steps.yml → 1"
  - "YAML parses (same mechanism as Task 3 Step 4)"
  - "python workspace/lint/lint_all.py → identical failing set to baseline (3/15); this task adds a runner config and must not alter lint results"
memory_refs: []
constraints:
  - "verify with the user (via the orchestrator, pre-dispatch) that Gate B was overridden to YES — this appendix task must NOT be dispatched under the Gate B default (NO)"
  - "the job id MUST be exactly `copilot-setup-steps` — GitHub's documented contract for coding-agent provisioning; do not rename it"
  - "even fully provisioned, S-C cannot reach *.gs.com — this runner's ceiling is src-only tests; do NOT add GS-data, skill, or run_task steps (AW-G11)"
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
context_summary: |
  Gate B's recorded decision overrode the default to YES, activating optional Appendix 02b.
  The GitHub Copilot coding agent (S-C) has no Python/uv on its ephemeral Ubuntu runner unless a
  copilot-setup-steps.yml provisions it; this job supplies setup-python 3.11 + setup-uv + a
  public-PyPI UV_INDEX_URL sync (the GS mirror in src/uv.toml is unreachable from cloud runners).
  Even provisioned, S-C cannot reach *.gs.com, so src-only tests are the ceiling (AW-G11) — no GS
  data, no skills, no run_task. The full file text is final in plan §8b.3; do not redesign it.
  This task is optional and never a blocker — Plan 03 does not depend on it.
depends_on: []
```

**02b.1 — S-C row variant for the AGENTS.md table (Task 1 Step 2):**

```markdown
| S-C | GitHub cloud coding-agent runner (ephemeral Ubuntu) | **LIMITED** | `copilot-setup-steps.yml` provisions Python 3.11 + uv against public PyPI. src-only tests work; **no GS data access, no skills (`*.gs.com` unreachable), no `run_task`**. Never dispatch data/skill work here |
```

**02b.2 — Scope-out line variant for copilot-instructions.md:** given in Task 2 Step 2.

**02b.3 — `.github/workflows/copilot-setup-steps.yml`**, verbatim:

```yaml
# Provisions the GitHub Copilot coding-agent runner (Gate B = YES override, plan-02b).
# Even provisioned, S-C cannot reach *.gs.com — src-only tests are the ceiling (AW-G11).
name: "Copilot Setup Steps"
on:
  workflow_dispatch:
  push:
    paths: [".github/workflows/copilot-setup-steps.yml"]
jobs:
  copilot-setup-steps:            # job name MUST be exactly this — GitHub's documented contract
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - name: Sync deps against public PyPI (GS mirror in src/uv.toml unreachable from cloud)
        working-directory: src
        env:
          UV_INDEX_URL: https://pypi.org/simple
        run: uv sync --dev --extra ml
```

**02b.4 — Folder-scoped `.vscode/tasks.json`:** NOT duplicated here — it lands unconditionally in **Plan 03** (decision record explicitly rejected gating tasks.json behind Gate B). 02b adds nothing to it; the S-C LIMITED row already states `run_task` stays unavailable on S-C (task wrappers are GS-bound regardless, AW-G10 verifier note).

**02b.5 — Acceptance additions:** `git grep -c 'copilot-setup-steps' -- .github/workflows/copilot-setup-steps.yml → 2 (name + job id)`; `git grep -c 'LIMITED' -- AGENTS.md → 1`; commit `chore(ci): provision copilot coding-agent runner (gate B override)`.

---

## 9. Contradiction grep list (the plan's acceptance instrument)

Run from repo root after all waves. On S-B run verbatim (via `./vol exec` where a subprocess is spawned); on S-A use VS Code search with the same patterns, or the terminal forms once sanctioned. **Every row must match its Expected column.**

| # | Command | Expected |
|---|---|---|
| C1 | `git grep -n "Environment (Linux / Coder Workspace)" -- AGENTS.md` | no matches |
| C2 | `git grep -n "Tools are on PATH via nix" -- AGENTS.md` | no matches |
| C3 | `git grep -n "fall back to run_in_terminal" -- AGENTS.md` | no matches |
| C4 | `git grep -c "Supported Execution Surfaces" -- AGENTS.md .github/copilot-instructions.md` | ≥ 1 in EACH file |
| C5 | `git grep -n "The \`./vol\` wrapper handles everything" -- .github/copilot-instructions.md` | no matches |
| C6 | `git grep -n "Run ALL commands via" -- .github/copilot-instructions.md` | no matches |
| C7 | `git grep -c "S-B" -- .github/copilot-instructions.md` | ≥ 3 |
| C8 | `git grep -cE "UNSUPPORTED|LIMITED" -- AGENTS.md` | ≥ 1 (matching the recorded Gate B decision) |
| C9 | `git grep -n "branches: \[main, develop\]" -- .github/workflows/ci.yml` | no matches |
| C10 | `git grep -c "MIRROR-ONLY" -- .github/workflows/ci.yml` | ≥ 1 |
| C11 | `git grep -c "extra ml" -- .github/workflows/ci.yml` | 1 |
| C12 | `git grep -c "UV_INDEX_URL" -- .github/workflows/ci.yml` | 1 |
| C13 | `git grep -c "cancel-in-progress" -- .github/workflows/ci.yml` | 1 |
| C14 | `git grep -c "enable-cache" -- .github/workflows/ci.yml` | 1 |
| C15 | `git grep -c "AW-G27" -- .github/workflows/ci.yml` | 1 |
| C16 | `python workspace/lint/lint_all.py` | FAILED (3/15): design rules, broken refs, vscode md compat — **identical to the pre-plan baseline; any new failure = plan FAILED** |
| C17 (Gate C = GitLab only) | `git grep -c "workspace-lint" -- .gitlab-ci.yml` | 1 |
| C18 (Gate B = YES only) | `git grep -c "copilot-setup-steps" -- .github/workflows/copilot-setup-steps.yml` | 2 |

C1–C8 together operationalize the Gate-B closure claim "the always-on files contain exactly one execution rule per surface": every old universal-form string is gone, and each rule names its surfaces.

---

## 10. Orchestrator prompt

```
/execute Implement Plan 02 (Surface Contract & Always-On Execution-Rule Scoping) from workspace/plans/copilot-workflow-overhaul/plan-02-surface-contract.md

Precondition check: Plan 01 merged and Gate A confirmed (git check-ignore workspace/config/.env exits 0);
Gate B and Gate C decisions recorded by the user per plan §2 — if either is unrecorded, STOP and ask.
No research /execute session may be live.
Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.
Branch: chore/wf-overhaul-02-surfaces off master; rebase onto origin/master before push; MR-only.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1 (parallel, max 2): wfo-02-1, wfo-02-3     # disjoint write_scopes: AGENTS.md | ci.yml
  Wave 2: wfo-02-2                                  # depends_on wfo-02-1; sole writer of copilot-instructions.md
  Wave 2 (add if Gate C = GitLab, parallel with wfo-02-2): wfo-02-4   # write_scope .gitlab-ci.yml, disjoint
  Wave 2 (add if Gate B = YES): wfo-02-5 per plan §8b                 # write_scope copilot-setup-steps.yml, disjoint
Every task is Rule-5-EXEMPT (config/docs only) — no TDD red/green, but each task MUST show its
Step-1 baseline greps (contradictions present) and post-edit greps (absent), plus the unchanged
3/15 lint baseline. Self-modification hazard: packets quote rule text as-of-execution; a subagent
whose quoted text mismatches the live file returns blocked with the diff — do not let it improvise.
Each subagent: terminal isolation + cleanup (kill_terminal EXIT GATE), return the 00-overview §5.2
return contract verbatim.
Retry a blocked/partial subagent once with a refined packet, then escalate with both attempts' evidence.
Integration verification (orchestrator, after all waves): run the full §9 grep table C1–C16
(+C17/C18 if applicable) and paste every row's output into the MR description, together with the
recorded Gate B and Gate C decisions.
Update workspace/research/weekly-progress.md (Shipped: one line; Decided: Gate B + Gate C outcomes).
Do NOT start Plan 03.
```

---

## 11. Acceptance gate → Plan 03

Plan 03 may start only when ALL of:

1. **Gate B decision recorded** (default NO) and the matching S-C row/line variant is what landed (C8).
2. **Gate C decision recorded** and honored: ci.yml carries the MIRROR-ONLY header + all fixes (C9–C15); `.gitlab-ci.yml` exists iff the GitLab branch was chosen (C17).
3. **Contradiction greps C1–C16 all match Expected** — pasted in the MR description.
4. **Lint baseline unchanged:** still exactly 3/15 failing (design rules, broken refs, vscode md compat), broken-ref count still 2 — this plan added zero lint regressions.
5. MR merged to `master`; branch `chore/wf-overhaul-02-surfaces` closed; weekly-progress.md updated.

**What Plan 03 consumes from here:** the AGENTS.md `## Supported Execution Surfaces` table (its S-A row names the `vol.cmd` + tasks.json seams Plan 03 fills; its wrapper-scoping paragraph is the AW-G11 scope-out that Plan 03's `_run.cmd` hardening completes); copilot-instructions Rules 2/3/8 per-surface text (Plan 03's packets quote it as-of-execution when adding the `./vol` OS guard and `vol.cmd`); the recorded Gate B/C outcomes (Plan 03's tasks.json lands regardless of Gate B; Plan 04's trigger wiring reads Gate C).
