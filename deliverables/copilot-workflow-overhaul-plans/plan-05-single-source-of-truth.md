# Plan 05 — Single Source of Truth

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §9.
> Dispatch each task as a subagent with the context packet provided. Max 4 concurrent subagents (waves below).
> TDD is a hard gate (Rule 5, `.github/copilot-instructions.md`) — **every task in this plan is docs/config/policy-only and therefore TDD-exempt**; red→green is demonstrated with contradiction greps instead of tests. Requires Plans 01–04 merged (Gate D evidence + `lint_all.py` full PASS).

**Goal:** Every rule, schema, and list that today exists in 2+ divergent copies (HARD rules, lint policy, tmp/-script policy, context-packet schema, return contract, depth table, boot list, model pin, routing rule, ML constraints) exists in exactly ONE canonical home, with every other surface reduced to a pointer — and the plan's contradiction grep-list returns 0.

**Architecture:** This plan plugs into three existing seams: (1) `.github/copilot-instructions.md` "Critical Rules (HARD — zero exceptions)" becomes the sole owner of the 9 HARD rules — `AGENTS.md` already models the pointer pattern at its line 9 ("Critical operational rules … see .github/copilot-instructions.md"), so the 5 duplicated rule blocks in AGENTS.md collapse onto that existing pattern; (2) `policy/subagent_protocol.md` — already named canonical by `copilot-instructions.md:74` — absorbs the union packet schema (adds `context_summary` + `depends_on`) so `policy/context-isolation.md` and `workflows/plan.md` can drop their copies; (3) the Plan-04 lint suite (`lint_all.py` + `lint_model_pins.py` + `lint_broken_refs.py` with plain-text-path detection) is the standing gate that must stay green after **every** task, so no dedup can silently orphan a reference.

**Tech stack:** No new dependencies. No Python code changes. All edits are Markdown policy/workflow/instruction files plus two file deletions. Only sanctioned tooling: `vol.cmd exec` / `run_task("lint-workspace")` on S-A, `./vol exec` on S-B, GIT_COMMIT conventions for commits.

**Research grounding:** Implements audit strategic move **S3** ("One source of truth per rule; everything else points") killing AW-G2, AW-G4, AW-G5, AW-14, AW-22, AW-26, AW-27, AW-28, AW-35, AW-38, AW-42, AW-49, AW-53. Expected-outcome priors (audit context-cost map, all bytes/4, directional): AGENTS.md sheds the 5 duplicated blocks (~350–1,200 tokens/request per AW-26); the subagent-protocol pair sheds ~700 tokens per subagent workflow (AW-35 verifier's corrected figure — NOT the ~1.4k "half" the finding's title implies); suite-level boot target ~10,235 t → ~7,500 t is shared with Plan 06 — **this plan records its before/after measurement in the MR description and treats the number as directional evidence, never a hard gate**. Calibration warning: a measured saving far better than these priors means bytes/4 mis-measured or load-bearing content was deleted — investigate before celebrating.

---

## 1. Global constraints

Suite-wide rules: `workspace/plans/copilot-workflow-overhaul/00-overview.md` §5 (shared conventions) apply to every task. Plus this plan's specific hard rules:

### ⚠ SELF-MODIFICATION CONSTRAINT (read before dispatching anything)

**This plan rewrites the rules that govern the very session executing it.** `.github/copilot-instructions.md` and `AGENTS.md` are injected into every request — including the orchestrator's and every subagent's.

1. **Every context packet below quotes the pre-edit text of each rule it touches.** The subagent obeys the QUOTED text for its own conduct, executes the rewrite as its work product, and never obeys a half-rewritten rule mid-task. Concretely: a subagent editing Rule 6 still runs lint only at its own commit gate (the pre- and post-edit policies happen to agree — that is by design; the rewrite changes wording and ownership, not the operative behavior of any rule the executing session depends on).
2. **If the live file text differs from the packet's quote, STOP** — return `status: blocked` with the diff. Do not improvise, do not "fix forward". (Plans 01–04 legitimately edited both always-on files; the packets below quote the fields Plans 01–04 do NOT touch. Any mismatch means either drift or an unmerged prior plan.)
3. **The two always-on files are never in two concurrent write_scopes** (overview §7). Wave ordering below enforces this.
4. **No task changes the operative meaning of Rules 1–5, 7, 8** (file output location, ./vol/vol.cmd mandate, terminal isolation, cleanup, TDD, evidence, no-bare-tools). This plan changes ownership, wording, and pointers. The only operative-behavior changes are the ones the audit mandates: ONE lint policy (Rule 6 already says on-request/pre-commit — the *other* files move to match it), ONE tmp-scripts policy (Rule 1 absorbs the reconciled wording), the model-pin fallback clause, /team depth = 2 everywhere, and the plan↔execute yield fix.

### Other hard rules

- **TDD-exempt, lint-gated:** every task is config/docs (Rule 5 exemption: "config, docs, memory, workflows, prompts"). In exchange, **`lint_all.py` full PASS is an acceptance criterion of every single task** — run via `vol.cmd exec python workspace/lint/lint_all.py` (S-A) and read the sentinel `OUTPUT_FILE` for `PASS` + `EXIT_CODE=0`. A task that turns any lint red is `blocked`, not "mostly done".
- **Drift check (standing):** verify every cited `path:line` against the live tree before editing; if it moved, locate by content and note the delta in your return. (Cited lines below were verified against the byte-identical mirror on 2026-07-07; Plans 01–04 have since edited `AGENTS.md`, `copilot-instructions.md`, and `workflows/` — expect small offsets, not different content.)
- **The 5 ACTIVE research plans in `workspace/plans/` are read-only** (`bug3-iv-context-fix`, `gnn-gpu-parallel-plan`, `linear-alpha-tuning`, `plan-c-prediction-blending`, `trial-068-conditional-duan`). Never touch `trials.yaml` or `workspace/configs/`.
- **Do-NOTs inherited from the audit verifiers:** do NOT collapse `subagent_protocol.md` + `context-isolation.md` into one file (AW-35 caveat — they stay two files); do NOT touch prompt frontmatter `model:` literals (functional per-prompt config — AW-53/AW-G4; Plan 07 rationalizes them); do NOT treat the slug `claude-opus-4-6` as frontmatter-ready (AW-G5); do NOT fix the `PurgedKFold` import or delete the embedded class in `python.instructions.md` (AW-14's code half lands in Plan 06); do NOT re-edit the Plan-02 surface-scoping language in either always-on file — convert duplication to pointers around it.
- **Deletions must leave `lint_broken_refs.py` green:** before deleting any file, grep the tracked tree for inbound references and repoint/remove them in the same task.
- **Branch:** `chore/wf-overhaul-05-ssot` off `master`; rebase onto `origin/master` before push; MR-only; never amend; never `git add -A`; denied paths never staged (`workspace/docs/enghub/`, `workspace/tmp/`, `__pycache__/`, `*.pyc`).

---

## 2. File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `.github/copilot-instructions.md` | Sole owner of the 9 HARD rules: Rule 1 unified tmp policy, Rule 2 +ruff, Rule 6 one lint policy, Rule 9 pointer + fallback clause, 3-line boot pointer |
| Modify | `AGENTS.md` | 5 duplicated rule blocks → pointers; boot list canonical + step 4 deleted; internal INDEX ambiguity fixed; operating-principles unique bullets folded in (Task 6) |
| Modify | `workflows/bootup.md` | Boot delta only — executes AGENTS.md Boot Protocol, drops its duplicate read list + handoff step |
| Modify | `policy/working-agreements.md` | Line 9 lint policy aligned; preflight-gates wiring line (Task 6) |
| Modify | `workflows/fix.md` | Lint-gate lines 150-153/168/209/275-276 aligned to one lint policy |
| Modify | `workflows/execute.md` | Lint lines 62/82; yield contradiction at BOTH :76 and :104; model-pin prose :35/:106 → pointers |
| Modify | `policy/subagent_protocol.md` | SOLE home of packet schema (union: +`context_summary`, +`depends_on`), return contract (+`notes`), depth table, canonical model pin + fallback |
| Modify | `policy/context-isolation.md` | Drops schema/return/depth copies → pointers; keeps unique sections (Philosophy, spawn thresholds, packet-writing rules incl. context_summary rationale, Orchestrator Behavior, Anti-Patterns, Workflow Integration) |
| Modify | `workflows/plan.md` | Lines 78-88 packet YAML → pointer + `depends_on` requirement note |
| Modify | `workflows/team.md` | Line 217 sub-worker rule reconciled to depth-2 table |
| Modify | `workflows/research.md`, `workflows/refactor.md` | Model-pin prose (both :88) → "per policy/subagent_protocol.md" |
| Modify | `workflows/INDEX.md`, `workflows/_protocol.md` | Routing rule → "canonical in AGENTS.md" pointers |
| Modify | `workspace/learning/vol-learning-framework-design.md` | Slug `claude-opus-4-6` at :1079/:1175 labeled informational (AW-G5) |
| Modify | `workspace/lint/whitelists/model_pins.txt` | PARTIAL burn (Task 5) — delete the whitelist entries for the prose sites Plan 05 just cleaned; Plan 07 empties it |
| Delete | `policy/routing.md` | 212-byte stub, zero unique content (AW-53) |
| Delete | `policy/operating-principles.md` | Near-100% duplicated in AGENTS.md:145-158; 3 unique bullets folded into AGENTS.md first (AW-22) |
| Modify | `policy/index.md` | Remove deleted-file rows; strip "(Opus 4.6)" gloss; note ml-constraints loading surface |
| Modify | `.github/instructions/python.instructions.md` | ONE added mandated-read line wiring `policy/ml-constraints.md` (AW-14/AW-22) — nothing else |
| Modify | `policy/ml-constraints.md` | Header line 3 states its loading surfaces (no longer self-declares an activation it doesn't have) |
| Modify | `personas/model-builder.md`, `personas/eval-sentinel.md` (+ sweep of the other 3 personas) | Restated constraint blocks → "apply Key Constraints (AGENTS.md)" pointers |
| Create (ephemeral) | `workspace/tmp/wfo05_boot_measure.py` | bytes/4 before/after measurement script; deleted after use per Rule 1 |

---

## 3. Interfaces

**Consumes (from the ledger / earlier plans — copied, never re-derived):**
- `lint_model_pins.py` with `EXPECTED_MODEL = "Claude Opus 4.6"` (Plan 04) — THE model-pin constant; the display-name form, never the slug.
- `lint_broken_refs.py` extended to plain-text repo paths + `_dormant` (Plan 04) — the deletion-safety net.
- `python workspace/lint/lint_all.py` full PASS on S-A and S-B (Plan 04 gate) — the standing green baseline this plan must preserve.
- `vol.cmd` (`exec` arm, sentinel protocol) + `run_task("lint-workspace")` on S-A; `./vol exec` on S-B (Plan 03 / Gate D).
- Plan-02 surface-scoped wording of copilot-instructions Rules 2/3/8 and AGENTS.md Environment section — preserved verbatim around this plan's edits.
- Boot measurement definition (ledger): bytes/4 over the 5 always-on/boot files (`copilot-instructions.md`, `AGENTS.md`, `memory/person/user.md`, `memory/research/project-state.md`, `memory/INDEX.md`), before vs after, recorded in the MR description.

**Produces (later plans rely on; back-ported to the ledger):**
- `policy/subagent_protocol.md` = the ONLY file containing the packet schema — final field set: `subtask_id, goal, file_scope, write_scope, acceptance_criteria, memory_refs, constraints, context_summary, depends_on` — the return contract (incl. `notes`), the spawn-threshold table, and the depth table. Overview §5.1's "union" resolution is hereby physically realized.
- Rule 6 final wording (consumed by Plan 07 prompt edits and by every later plan's session conduct): *"Run `./vol lint` / `vol.cmd lint` only when explicitly requested by the user or before a PR/commit. Lint is NOT required after every change. The pre-commit hook (Plan 04) is the enforcement point."*
- Rule 9 fallback clause (consumed by Plan 07's pin rationalization): prefer **Claude Opus 4.6** (display name = `lint_model_pins.EXPECTED_MODEL`); if not selectable, use the strongest available Claude model and record the substitution in the return contract's `notes`; never a small/short-context model.
- **DECISION (AW-49), executed here:** boot step 4 (session-handoff check) is **DELETED**, not given a writer. Rationale from research-4: the file has zero producers ("2 hits, both readers"), the trial registry is already declared the source of truth over any handoff ("trust trial registry over handoff"), and adding a session-end writer would create a new always-on obligation in the very plan whose job is removing duplicated obligations. `workflows/bootup.md`'s handoff step and both reader references die with it.
- **DECISION (/team depth):** resolved to **2** (leader → worker → sub-worker) — 3 of 4 surfaces already said 2 (`AGENTS.md:25`, `subagent_protocol.md:65`, `context-isolation.md:137`); `team.md:217` is rewritten to match, with leader notification required.
- Deletions later plans must not re-reference: `policy/routing.md`, `policy/operating-principles.md`.
- AGENTS.md Boot Protocol = the single canonical boot list (3 reads; Plan 06 edits the *contents* of those files, not the list).

---

## 4. Tasks

### Task 1: copilot-instructions.md becomes sole owner of the 9 HARD rules

**Files:** Modify — `.github/copilot-instructions.md` (only).

**Copilot context packet:**

```yaml
subtask_id: "wfo-05-1"
goal: "Rewrite .github/copilot-instructions.md rules 1, 2, 6, 9 and add a 3-line boot pointer so the file is the sole, self-sufficient owner of the 9 HARD rules, with grep evidence red-then-green and lint_all.py PASS"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md   # this task section carries all replacement text
  - .github/copilot-instructions.md
  - workspace/lint/lint_model_pins.py        # confirm EXPECTED_MODEL string matches exactly
write_scope:
  - .github/copilot-instructions.md
acceptance_criteria:
  - "grep -n 'DISABLED' .github/copilot-instructions.md -> 0 hits"
  - "grep -c 'Opus 4.6' .github/copilot-instructions.md -> 1 (the Rule 9 preferred-model naming, exact display-name form)"
  - "grep -n 'ruff' .github/copilot-instructions.md -> Rule 2 NEVER-list now includes ruff"
  - "grep -n 'Session boot' .github/copilot-instructions.md -> 1 hit (the new 3-line boot pointer)"
  - "grep -n 'delete anything you create' .github/copilot-instructions.md -> 1 hit (unified tmp policy in Rule 1)"
  - "vol.cmd exec python workspace/lint/lint_all.py -> OUTPUT_FILE contains PASS and EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "SELF-MODIFICATION: you are editing the rules that govern this very session. Obey the PRE-EDIT text quoted in context_summary for your own conduct; if the live text of rules 1/6/9 differs from those quotes, STOP and return blocked with the diff. Never obey a half-rewritten rule mid-task."
  - "Do NOT touch rules 3, 4, 5, 7 or the Plan-02 surface-scoping additions to rules 2/3/8 beyond the single 'ruff' insertion specified"
  - "Do NOT use the slug claude-opus-4-6 anywhere; the display name 'Claude Opus 4.6' must byte-match EXPECTED_MODEL in workspace/lint/lint_model_pins.py"
context_summary: |
  Plan 05 makes copilot-instructions.md the sole owner of the 9 HARD rules (audit S3; AW-26/27/28/49/G2/G4).
  Pre-edit Rule 6 reads: "## 6. Lint Gate (DISABLED) / ~~Run `./vol lint` after every code change.~~ Lint is
  NOT required after every change. Only run lint when explicitly requested by the user or before a PR/commit."
  Pre-edit Rule 9 begins: "**All subagents MUST use Claude Opus 4.6.** Never spawn a subagent on a weaker
  model (Sonnet, Haiku, GPT, etc.). This is non-negotiable —". Pre-edit Rule 1 is the workspace/tmp-only rule
  with no scratch-script clause. AGENTS.md will be pointer-ized in the NEXT wave (wfo-05-2) — this task must
  make this file self-sufficient FIRST so the pointers have a complete target. The lint policy's operative
  meaning does not change (lint on request or pre-commit/PR); only wording and sole ownership do.
depends_on: []
```

- [ ] **Step 1 (red):** capture the pre-edit contradictions — run and paste output:
  ```
  grep -n "DISABLED" .github/copilot-instructions.md          # expect 1 hit (line ~50)
  grep -c "Opus 4.6" .github/copilot-instructions.md           # expect 2 (rule 9 mandate + prose)
  grep -n "ruff" .github/copilot-instructions.md               # expect: only in the Rule 8 table, NOT in Rule 2's NEVER list
  ```
- [ ] **Step 2 (edit):** apply exactly these four replacements (leave everything else byte-identical, including all Plan-02 surface scoping):

  **(a) Rule 1** — replace the two paragraphs under `## 1. File Output:` with:
  ```markdown
  ALL file writes (temp files, outputs, scripts, artifacts) MUST go to `workspace/tmp/` relative to repo root.

  **NEVER** write to `/tmp/`, `~`, `/home/*/`, or any path outside this repository. Violations trigger manual approval prompts that block automation.

  **Scratch scripts:** prefer inline execution for one-off commands. A helper script for a bounded job MAY be written to `workspace/tmp/` — delete anything you create there after use. Persisted outputs go to `workspace/<area>/` (research, docs, configs), never to `tmp/`. This is the single tmp/-policy; no other file restates it.
  ```
  *(This absorbs and reconciles AW-28's three contradictory statements: AGENTS.md:154 "No throwaway scripts in tmp/", this file's "scripts … MUST go to workspace/tmp/", and AGENTS.md:206 "ephemeral … delete files you create".)*

  **(b) Rule 2** — in the NEVER-run sentence, change the tool list `python`, `pytest`, `pip`, `uv`, or `mypy` to `python`, `pytest`, `pip`, `uv`, `mypy`, or `ruff` *(merges the AW-26 drift item: AGENTS.md:217 had `ruff`; this file didn't)*.

  **(c) Rule 6** — replace the entire section with:
  ```markdown
  ## 6. Lint Gate (on request or pre-commit/PR)

  Run `./vol lint` (S-B) / `vol.cmd lint` (S-A) **only** when explicitly requested by the user or before a PR/commit. Lint is NOT required after every change. The pre-commit hook (`workspace/lint/`, Plan 04) is the enforcement point at commit time. This is the single lint policy — `policy/working-agreements.md` and the workflows defer to this rule.
  ```

  **(d) Rule 9** — replace the entire section with:
  ```markdown
  ## 9. Subagent Model Pinning

  Prefer **Claude Opus 4.6** for every subagent (the model-picker display name; this exact string is `EXPECTED_MODEL` in `workspace/lint/lint_model_pins.py`). **Fallback:** if it is not selectable in the current environment, use the strongest available Claude model, record the substitution in the return contract's `notes`, and never downgrade to a small/short-context model (Haiku-class). Canonical statement, depth limits (workflows = 1, /team = 2), and max concurrency (6): `policy/subagent_protocol.md`. When spawning subagents, always include the context packet schema from `policy/subagent_protocol.md`.
  ```

  **(e) Boot pointer** — insert immediately after the file's opening paragraph (line ~3, after "Full policy: see `AGENTS.md`."):
  ```markdown
  **Session boot:** execute the Boot Protocol in `AGENTS.md` (§Context Loading) before substantive work.
  If this file is the only instruction file injected in your surface, read `AGENTS.md` first — nothing is auto-injected beyond these rules.
  ```
  *(AW-49's surface-divergence half: chat-only surfaces that inject only this file previously never learned the memory system exists.)*
- [ ] **Step 3 (green):** re-run the Step-1 greps — `DISABLED` → 0; `Opus 4.6` count → 1; `ruff` present in Rule 2. Then run `vol.cmd exec python workspace/lint/lint_all.py`, `read_file` the printed `OUTPUT_FILE`, confirm `PASS` and `EXIT_CODE=0` (in particular `lint_model_pins` and `lint_broken_refs` stay green).
- [ ] **Step 4 (commit):** `chore(ci): single-source hard rules — lint policy, tmp policy, model fallback`

---

### Task 2: AGENTS.md — pointers for the 5 duplicated blocks + one canonical boot list

**Files:** Modify — `AGENTS.md`, `workflows/bootup.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-05-2"
goal: "Replace AGENTS.md's 5 duplicated HARD-rule blocks with pointers to copilot-instructions.md, make the AGENTS.md Boot Protocol the single boot list (delete step 4 per the AW-49 decision, fix the step-3-vs-line-60 self-contradiction), and reduce workflows/bootup.md to its delta"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md
  - AGENTS.md
  - workflows/bootup.md
  - .github/copilot-instructions.md          # READ-ONLY: the pointer target rewritten by wfo-05-1
write_scope:
  - AGENTS.md
  - workflows/bootup.md
acceptance_criteria:
  - "grep -rn 'session-handoff' AGENTS.md workflows/bootup.md -> 0 hits"
  - "grep -n 'No throwaway scripts' AGENTS.md -> 0 hits"
  - "grep -c 'Opus 4.6' AGENTS.md -> 0"
  - "grep -n 'memory/person/user.md' workflows/bootup.md -> 0 hits (bootup no longer re-lists the P0 reads)"
  - "grep -c 'copilot-instructions.md' AGENTS.md -> >= 6 (the pointer pattern now covers model pin, TDD, evidence, file-output, never-run)"
  - "vol.cmd exec python workspace/lint/lint_all.py -> OUTPUT_FILE contains PASS and EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "SELF-MODIFICATION: AGENTS.md governs this session. The 5 blocks you replace duplicate rules that continue to exist verbatim in copilot-instructions.md (rewritten by wfo-05-1, already merged) — your own conduct obligations are unchanged. If any block's live text differs materially from the quotes in context_summary, STOP and return blocked with the diff."
  - "Do NOT touch: Project Identity, Key Constraints table (rows for TDD excepted as specified), Data Access, Feature Layer, Model Architecture, Memory (CoALA), Workspace, Available Skills, Skill Output rules 1/3/4, the Plan-02 'Supported Execution Surfaces'/Environment content, Cross-References"
  - "wfo-05-1 must be merged first; confirm copilot-instructions.md Rule 6 header reads 'on request or pre-commit/PR' before starting"
depends_on: ["wfo-05-1"]
```

- [ ] **Step 1 (red):** paste output of:
  ```
  grep -n "MUST use Claude Opus 4.6" AGENTS.md                 # ~line 23 (block 5 of 5)
  grep -n "No throwaway scripts" AGENTS.md                     # ~line 154 (block 4)
  grep -n "ALL file writes MUST stay inside the workspace" AGENTS.md   # ~line 155
  grep -n "session-handoff" AGENTS.md workflows/bootup.md      # boot step 4 + bootup step 5
  grep -n "NEVER run \`python\`" AGENTS.md                     # ~line 217 (block 1)
  ```
- [ ] **Step 2 (edit AGENTS.md):** the 5 duplicated blocks (AW-26's enumeration, with research-3's line refs) become pointers:

  **Block 1 — model pinning (`AGENTS.md:23` + the `:25` depth line):** replace
  > `**Model pinning:** All subagents MUST use Claude Opus 4.6. No exceptions.`
  > `**Depth limit:** Workflows (/plan, /execute, /research, /refactor) → max depth 1. /team → max depth 2.`

  with one line:
  ```markdown
  **Model pinning, depth limits, concurrency:** per [policy/subagent_protocol.md](policy/subagent_protocol.md) (Rule 9 in [.github/copilot-instructions.md](.github/copilot-instructions.md)).
  ```

  **Block 2 — TDD (`AGENTS.md:85`, Key Constraints row):** replace the row's rule cell with:
  ```
  Per Rule 5 in [.github/copilot-instructions.md](.github/copilot-instructions.md); scenario table in [policy/working-agreements.md](policy/working-agreements.md).
  ```

  **Block 3 — evidence/no-fabrication (`AGENTS.md:145-146`):** replace the two bullets with:
  ```markdown
  - **Evidence over assumption / no fabrication:** per Rule 7 in [.github/copilot-instructions.md](.github/copilot-instructions.md).
  ```

  **Block 4 — file-output + tmp scripts (`AGENTS.md:154-155`):** replace BOTH bullets ("No throwaway scripts in `tmp/`…" and "ALL file writes MUST stay inside the workspace…") with:
  ```markdown
  - **File output & scratch scripts:** per Rule 1 in [.github/copilot-instructions.md](.github/copilot-instructions.md) — `workspace/tmp/` is the only writable scratch area; delete what you create there.
  ```
  *(Kills the AW-28 contradiction: Rule 1 now owns the reconciled policy. The Skill Output section's rule 2 at ~:206 is consistent with it and stays.)*

  **Block 5 — never-run list (`AGENTS.md:217`, Environment section):** replace the bullet with:
  ```markdown
  - **Never run tools bare** (`python`, `pytest`, `pip`, `uv`, `mypy`, `ruff`): per Rules 2 and 8 in [.github/copilot-instructions.md](.github/copilot-instructions.md).
  ```
  *(Preserve every other Environment/surface line Plan 02 wrote.)*

  **Boot Protocol (AW-42 + AW-49):** replace the 4-step "Session start (always)" list and the line-60 sentence with:
  ```markdown
  **Session start (always):**
  1. Read [memory/person/user.md](memory/person/user.md) — user identity and preferences.
  2. Read [memory/research/project-state.md](memory/research/project-state.md) — current milestone, QLIKE scorecard, next action.
  3. Read [memory/INDEX.md](memory/INDEX.md) — memory index and lookup tables.

  This is the canonical boot list — `workflows/bootup.md` executes it and adds only its own delta (trial registry slice, latest journal entry). `user.md` and `project-state.md` are the P0 "Always" files; `INDEX.md` is read for its lookup tables; everything else loads on demand per those tables.
  ```
  *(Step 4 — "Check for workspace/tmp/session-handoff.md" — is deleted per the AW-49 decision recorded in §3: the file has no producer anywhere in the tree, and the trial registry is already the declared source of truth for experiment state. The line-60 self-contradiction — step 3 reads INDEX.md "always" while line 60 said only 2 files are "Always" — is resolved by the sentence above.)*
- [ ] **Step 3 (edit workflows/bootup.md):** replace the 6-step checklist with:
  ```markdown
  1. **Execute the AGENTS.md Boot Protocol** (§Context Loading). Do NOT re-read files it already loaded.
  2. **Read trial registry:** `workspace/research/trials.yaml` — last 3 completed + all NOT_STARTED entries
  3. **Read latest research journal entry:** `workspace/research/research-journal.md` (most recent `##` section only)
  4. **Synthesize and present:** one-line last-session summary (from the journal), QLIKE scorecard table (h=1/5/22), next experiment or implementation step, recommended slash command
  ```
  Keep the Output Format block unchanged. In Constraints, change the max-context line to: `Max context load: Boot Protocol files + trial registry slice + 1 journal entry. No P1/P2 memory at boot.` Delete the handoff mentions in Constraints/Notes (including "except stale handoff cleanup").
- [ ] **Step 4 (green):** re-run Step-1 greps (all → 0 where specified); `grep -c "Opus 4.6" AGENTS.md` → 0; `vol.cmd exec python workspace/lint/lint_all.py` → `PASS`, `EXIT_CODE=0` (broken-refs must not flag the removed `session-handoff` link — it is deleted, not retargeted).
- [ ] **Step 5 (commit):** `chore(framework): point AGENTS.md at canonical rules; single boot list`

---

### Task 3: One lint policy propagated pair-complete + plan↔execute yield fix

**Files:** Modify — `policy/working-agreements.md`, `workflows/fix.md`, `workflows/execute.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-05-3"
goal: "Propagate the Rule-6 lint policy ('on request or pre-commit/PR') through working-agreements.md:9 and every mandatory-lint line in fix.md (150-153, 157, 168, 209, 275-277) and execute.md (62, 82), fix the plan↔execute yield contradiction at BOTH execute.md:76 and :104, and pointer-ize execute.md's two model-pin prose lines (:35, :106)"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md
  - policy/working-agreements.md
  - workflows/fix.md
  - workflows/execute.md
  - workflows/plan.md                        # READ-ONLY: :159 is the composition rule execute.md must match
write_scope:
  - policy/working-agreements.md
  - workflows/fix.md
  - workflows/execute.md
acceptance_criteria:
  - "grep -n 'Run lint, typecheck, and tests after changes' policy/working-agreements.md -> 0 hits"
  - "grep -n 'Lint gate is mandatory' workflows/fix.md -> 0 hits"
  - "grep -rn 'MUST use Claude Opus 4.6' workflows/execute.md -> 0 hits"
  - "grep -c 'entered from' workflows/execute.md -> >= 2 (both :76 and :104 are entry-source aware)"
  - "grep -in 'lint' workflows/fix.md workflows/execute.md -> every remaining hit either defers to Rule 6 or refers to pre-commit/PR/on-request; paste the full hit list in your return as evidence"
  - "vol.cmd exec python workspace/lint/lint_all.py -> OUTPUT_FILE contains PASS and EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "SELF-MODIFICATION: these workflow files may be loaded by the session executing this plan. The pre-edit lines you are changing MANDATE per-change lint; the post-edit policy is lint on request/pre-commit only. For your own conduct, follow the packet: run lint exactly once, at your acceptance gate. Quoted pre-edit anchors: working-agreements.md:9 'Run lint, typecheck, and tests after changes.'; fix.md:276 'Lint gate is mandatory after every file change (per policy).'; execute.md:76 '| Scope unclear mid-execution | → Yield to `plan.md`, resume on return |'; execute.md:104 '- Max 1 yield to `plan.md`. No circular yields.'; plan.md:159 'Max composition depth: `plan → execute → plan` is not allowed.' If live text differs materially, STOP and return blocked with the diff."
  - "Do NOT weaken the TEST-FIRST gate, CONFORM gate, or test-coverage mandates in either workflow — only the lint-frequency lines change"
  - "AW-27's cited line list is the minimum; ALSO sweep both files for residual per-change-lint phrasing (e.g. fix.md:136 '→ run lint →', fix.md:157 checkpoint 'lint results') and align it, noting each extra line in your return"
depends_on: ["wfo-05-1"]
```

- [ ] **Step 1 (red):** paste output of `grep -n "Run lint, typecheck" policy/working-agreements.md`, `grep -in "lint" workflows/fix.md`, `grep -in "lint" workflows/execute.md`, `grep -n "Yield to" workflows/execute.md` — the mandatory-lint lines and the yield contradiction are visible.
- [ ] **Step 2 (edit):** apply exactly:

  **working-agreements.md:9:**
  `- Run lint, typecheck, and tests after changes.` →
  `- Run tests after changes. Run lint and typecheck only on explicit request or before a PR/commit — per Rule 6 in `.github/copilot-instructions.md`.`

  **fix.md:150-153 (IMPLEMENT transition table):**
  ```
  | All planned changes applied, CONFORM pass (standard) | → TEST |
  | All planned changes applied, CONFORM pass (trivial) | → REVIEW |
  | CONFORM finds violations | Fix violations, re-check (max 2 retries) |
  ```
  *(the standalone "Lint failure after fix attempt" row is deleted; the "lint +" prefix drops from the two pass rows)*

  **fix.md:136 (residual sweep):** `…to make the failing test pass (green) → run lint → self-check against plan → mark complete.` → `…to make the failing test pass (green) → self-check against plan → mark complete.`

  **fix.md:157:** `Checkpoint: record files changed, lint results, CONFORM audit results, drift notes (if any).` → `Checkpoint: record files changed, CONFORM audit results, drift notes (if any).`

  **fix.md:168:** `Run the new tests and lint.` → `Run the new tests.`

  **fix.md:209:** `3. Verify IMPLEMENT checkpoint shows lint passing on all changed files.` → `3. Verify IMPLEMENT checkpoint shows CONFORM passing on all changed files (lint runs at the pre-commit/PR gate per Rule 6).`

  **fix.md:275-277 (Constraints):**
  `- Lint gate is mandatory after every file change (per policy).` →
  `- Lint runs only on explicit request or at the pre-commit/PR gate — per Rule 6 in `.github/copilot-instructions.md`. The pre-commit hook is the enforcement point.`
  And in the CONFORM bullet (:277): `…mandatory for code files after lint passes…` → `…mandatory for code files after implementation…`; `…re-linted within the existing lint retry budget.` → `…re-checked within the existing retry budget.`

  **execute.md:62:** `2. Per todo item: implement to make the test pass (green) → lint → checkpoint.` → `2. Per todo item: implement to make the test pass (green) → checkpoint.`

  **execute.md:82:** `2. Run lint/typecheck/build when applicable.` → `2. Run build when applicable. Run lint/typecheck only if explicitly requested or when preparing a commit/PR (Rule 6).`

  **execute.md:76 (AW-38, fix BOTH lines):**
  `| Scope unclear mid-execution | → Yield to `plan.md`, resume on return |` →
  `| Scope unclear mid-execution | → if entered from `plan.md`, escalate to the user; otherwise yield to `plan.md` (max 1), resume on return |`

  **execute.md:104:**
  `- Max 1 yield to `plan.md`. No circular yields.` →
  `- Max 1 yield to `plan.md`, and only when NOT entered from `plan.md`; if entered from `plan.md`, escalate to the user instead (matches `plan.md`'s composition limit). No circular yields.`

  **execute.md:35 (AW-53):** `- All subagents MUST use Claude Opus 4.6 (see `policy/subagent_protocol.md`).` → `- Subagent model pinning: per `policy/subagent_protocol.md`.`

  **execute.md:106:** `- **Subagent model pinning:** all spawned subagents MUST use Claude Opus 4.6 (see `policy/subagent_protocol.md`).` → `- **Subagent model pinning:** per `policy/subagent_protocol.md`.`
- [ ] **Step 3 (green):** re-run Step-1 greps; every remaining `lint` hit in both workflows defers to Rule 6 / pre-commit (paste the list); `grep -c "entered from" workflows/execute.md` ≥ 2; `vol.cmd exec python workspace/lint/lint_all.py` → `PASS`, `EXIT_CODE=0`.
- [ ] **Step 4 (commit):** `chore(framework): one lint policy in workflows; fix plan-execute yield rule`

---

### Task 4: Packet schema, return contract, depth table live ONLY in subagent_protocol.md

**Files:** Modify — `policy/subagent_protocol.md`, `policy/context-isolation.md`, `workflows/plan.md`, `workflows/team.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-05-4"
goal: "Make policy/subagent_protocol.md the sole home of the (union) context-packet schema, return contract, spawn-threshold table and depth table; replace the copies in context-isolation.md:48-93/132-138 and plan.md:78-88 with pointers while keeping each file's unique sections; resolve /team depth to 2 at team.md:217"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md
  - policy/subagent_protocol.md
  - policy/context-isolation.md
  - workflows/plan.md
  - workflows/team.md
write_scope:
  - policy/subagent_protocol.md
  - policy/context-isolation.md
  - workflows/plan.md
  - workflows/team.md
acceptance_criteria:
  - "grep -rln 'subtask_id:' policy/ workflows/ -> exactly one file: policy/subagent_protocol.md"
  - "grep -n 'context_summary' policy/subagent_protocol.md -> >= 1 (union schema absorbed)"
  - "grep -n 'depends_on' policy/subagent_protocol.md -> >= 1"
  - "grep -n 'notes:' policy/subagent_protocol.md -> >= 1 (return contract absorbed)"
  - "grep -rn 'must NOT spawn sub-workers' workflows/team.md -> 0 hits"
  - "grep -rn 'Leader → Worker → Sub-worker' policy/ -> exactly one file: policy/subagent_protocol.md"
  - "vol.cmd exec python workspace/lint/lint_all.py -> OUTPUT_FILE contains PASS and EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "SELF-MODIFICATION: this plan's own packets (including yours) were written against the UNION schema — the exact schema you are making canonical. Your edit legalizes the packets already in flight; it must not remove any field they use. If subagent_protocol.md's live schema block differs from the quote in context_summary, STOP and return blocked."
  - "AW-35 do-NOT: context-isolation.md and subagent_protocol.md STAY SEPARATE FILES — do not merge them; do not delete context-isolation.md's unique sections (Philosophy, Spawn Thresholds + do-NOT-spawn list, packet-writing rules 1-5 incl. the context_summary rationale, Orchestrator Behavior, Anti-Patterns, Workflow Integration)"
  - "Do not touch subagent_protocol.md's Terminal Isolation block (lines 81-91) or Model Pinning section beyond what wfo-05-1's Rule 9 already reflects — the Model Pinning section at :12-14 is the canonical prose pin and KEEPS the literal 'Claude Opus 4.6'"
context_summary: |
  The packet schema is duplicated in 3 tracked files (subagent_protocol.md:36, context-isolation.md:49,
  plan.md:79 — grep -c subtask_id: = 1 each) and the /team depth drifted: subagent_protocol.md:65 and
  context-isolation.md:137 permit depth 2 while team.md:217 says "Workers must NOT spawn sub-workers …
  unless explicitly authorized." Plan 05 resolves depth to 2 (three of four surfaces already say 2).
  Pre-edit canonical schema (subagent_protocol.md:36-50) has fields subtask_id/goal/file_scope/write_scope/
  acceptance_criteria/memory_refs/constraints — it LACKS context_summary (context-isolation adds it) and
  depends_on (plan.md adds it). Your job: absorb both into subagent_protocol.md, absorb the fuller return
  contract (context-isolation.md:81-93 YAML incl. notes), then reduce the other two copies to pointers.
  Verifier-corrected saving prior: ~700 tokens per subagent workflow, not half the pair.
depends_on: ["wfo-05-1"]
```

- [ ] **Step 1 (red):** paste `grep -rln "subtask_id:" policy/ workflows/` (3 files) and `grep -n "spawn sub-workers" workflows/team.md` (the depth contradiction).
- [ ] **Step 2 (edit `policy/subagent_protocol.md`):**
  - Under `## Context Packets`, replace the YAML block with the union schema:
    ```yaml
    subtask_id: "<workflow>-<seq>"       # e.g. "execute-3"
    goal: "<one testable sentence>"      # names the deliverable and its observable behavior
    file_scope:                          # files the subagent may READ — keep minimal
      - path/to/file.py
    write_scope:                         # the ONLY files the subagent may create/modify
      - path/to/target.py
    acceptance_criteria:                 # machine-verifiable, no human judgment
      - "Tests pass"
      - "Function X returns Y"
    memory_refs:                         # memory files to load (if any)
      - memory/research/project-state.md
    constraints:                         # hard limits
      - "Do not modify public API"
      - "TDD: write failing test first"
    context_summary: |
      <2-5 sentences replacing conversation history: why this task exists,
      what neighbors produce/consume, the one decision not to revisit>
    depends_on: []                       # subtask_ids that must complete first;
                                         # REQUIRED for packets written into plans (workflows/plan.md)
    ```
    Add directly beneath it: `This file is the SOLE home of the packet schema, return contract, spawn-threshold table, and depth table. `policy/context-isolation.md` (rationale and anti-patterns) and `workflows/plan.md` point here — never restate the schema.`
  - Under `## Return Contract`, replace the 4-item numbered list with the literal YAML shape (from context-isolation.md:81-93):
    ```yaml
    status: complete | blocked | partial
    files_changed:
      - path: <file>
        lines: <start>-<end>
        summary: "<what changed>"
    verification:
      - "<test output or assertion result>"
    blockers:
      - "<what prevented completion, if any>"
    notes:
      - "<anything the orchestrator should know for integration>"
    ```
  - Depth Limit section: unchanged (already says /team max depth = 2) — append one clause: `Sub-worker spawns must be reported to the leader in the worker's return notes.`
- [ ] **Step 3 (edit `policy/context-isolation.md`):** replace the `## Context Packet Schema` YAML block AND the `## Return Contract` YAML block AND the `## Depth Limits` table with:
  ```markdown
  ## Context Packet Schema, Return Contract, Depth Limits

  Canonical definitions live in `policy/subagent_protocol.md` — the sole home of the packet schema
  (including `context_summary` and `depends_on`), the return contract, and the depth table. Never restate them.
  ```
  KEEP unchanged: Philosophy, Spawn Thresholds (incl. the do-NOT-spawn list), the 5 packet-writing rules (the `context_summary` rationale lives here), Orchestrator Behavior, Anti-Patterns, Workflow Integration.
- [ ] **Step 4 (edit `workflows/plan.md:78-88`):** replace the inline packet YAML (the block from ` ```yaml ` through ` ``` ` under DECOMPOSE action 4) with:
  ```markdown
  - For each `subagent`-tagged step, write a context packet per the canonical schema in
    `policy/subagent_protocol.md` (ALL fields, including `context_summary`), inline in the plan.
    `depends_on` is REQUIRED for every packet written into a plan — `execute.md` derives
    parallel-vs-sequential spawn order from it.
  ```
- [ ] **Step 5 (edit `workflows/team.md:217`):** replace `- Workers must NOT spawn sub-workers (no recursive delegation) unless explicitly authorized.` with `- Workers MAY spawn sub-workers only within the /team depth limit (max depth 2, leader → worker → sub-worker — see `policy/subagent_protocol.md`) and MUST report every sub-worker spawn to the leader.`
- [ ] **Step 6 (green):** `grep -rln "subtask_id:" policy/ workflows/` → exactly `policy/subagent_protocol.md`; remaining greps per acceptance; `vol.cmd exec python workspace/lint/lint_all.py` → `PASS`, `EXIT_CODE=0`.
- [ ] **Step 7 (commit):** `chore(framework): packet schema and depth table single-sourced in subagent_protocol`

---

### Task 5: Model-pin prose and routing-rule pointer sweep

**Files:** Modify — `workflows/research.md`, `workflows/refactor.md`, `workflows/INDEX.md`, `workflows/_protocol.md`, `workspace/learning/vol-learning-framework-design.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-05-5"
goal: "Replace the remaining model-pin prose (research.md:88, refactor.md:88) with 'per policy/subagent_protocol.md' pointers, mark AGENTS.md canonical for the routing rule in workflows/INDEX.md:13 and workflows/_protocol.md:13, label the two claude-opus-4-6 slug occurrences in vol-learning-framework-design.md as informational (AW-G5), and PARTIAL-burn workspace/lint/whitelists/model_pins.txt by deleting the whitelist entries for the prose sites now cleaned (Plan 07 finishes it to empty)"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md
  - workflows/research.md
  - workflows/refactor.md
  - workflows/INDEX.md
  - workflows/_protocol.md
  - workspace/learning/vol-learning-framework-design.md
  - workspace/lint/whitelists/model_pins.txt
write_scope:
  - workflows/research.md
  - workflows/refactor.md
  - workflows/INDEX.md
  - workflows/_protocol.md
  - workspace/learning/vol-learning-framework-design.md
  - workspace/lint/whitelists/model_pins.txt
acceptance_criteria:
  - "grep -rln 'Opus 4.6' workflows/ -> 0 files"
  - "grep -c 'AGENTS.md' workflows/INDEX.md -> >= 1 AND grep -c 'AGENTS.md' workflows/_protocol.md -> >= 1 (routing canonical marked)"
  - "grep -n 'claude-opus-4-6' workspace/learning/vol-learning-framework-design.md -> both hits now carry the 'API slug, informational' label; display name declared the operative form"
  - "workspace/lint/whitelists/model_pins.txt no longer lists the just-cleaned prose sites (research.md, refactor.md, INDEX.md, _protocol.md); every entry you deleted is grep-confirmed to no longer contain 'Claude Opus 4.6' in its target file (a shrinking, lint-safe PARTIAL burn — remaining entries + _dormant residue are Plan 07's to empty)"
  - "vol.cmd exec python workspace/lint/lint_all.py -> OUTPUT_FILE contains PASS and EXIT_CODE=0 (lint_model_pins in particular)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "Do NOT touch .github/prompts/*.prompt.md frontmatter model: lines (functional config; Plan 07 owns them). Do NOT delete the slug from vol-learning-framework-design.md — label it."
  - "The grandfathered-prose whitelist is workspace/lint/whitelists/model_pins.txt (IN your write_scope — edit it directly, do not defer). PARTIAL-burn it: delete every entry whose target file no longer contains the raw 'Claude Opus 4.6' literal — grep-verify each file BEFORE deleting its entry — at minimum the four sites this task just cleaned (research.md, refactor.md, INDEX.md, _protocol.md). A whitelist that only shrinks can keep lint green or make it stricter; NEVER delete an entry for a site that still holds the literal (that turns lint red). This is a PARTIAL burn: leave any entry whose site is still uncleaned (AGENTS.md/personas/policy-index sites cleaned by sibling tasks, and the _dormant residue) for Plan 07, which empties the file. The two SANCTIONED_SITES (policy/subagent_protocol.md, .github/copilot-instructions.md) are structurally exempt, not whitelist entries — never add or touch them here."
  - "SELF-MODIFICATION: research.md/refactor.md may govern sessions; the pin's operative meaning is unchanged (canonical statement + fallback now lives in subagent_protocol.md/Rule 9). Pre-edit anchors: research.md:88 '- All subagents MUST use Claude Opus 4.6'; refactor.md:88 '- All subagents MUST use Claude Opus 4.6, depth = 1 (no further spawning)'. If live text differs materially, STOP and return blocked."
context_summary: |
  AW-53: model-pin prose is restated across workflows while policy/subagent_protocol.md:14 is canonical;
  the routing rule appears in 4 places (AGENTS.md:7 canonical, workflows/INDEX.md:13, _protocol.md:13,
  policy/routing.md:5 — the last is deleted by wfo-05-6, not you). AW-G5: the API slug claude-opus-4-6
  appears only at vol-learning-framework-design.md:1079/:1175; VS Code frontmatter matches picker DISPLAY
  names, so the display name 'Claude Opus 4.6' (== lint_model_pins.EXPECTED_MODEL) is the operative form.
  execute.md's two pin lines are handled by wfo-05-3 — do not touch execute.md.
  workspace/lint/whitelists/model_pins.txt (Plan 04) is the temporary grandfathered-prose whitelist that
  keeps lint_model_pins green while raw literals still exist; the two SANCTIONED_SITES are exempt via a
  module constant, NOT via this file. Plan 05 partial-burns it (this task deletes the entries for the sites
  it just cleaned); Plan 07 finishes it to empty.
depends_on: ["wfo-05-1"]
```

- [ ] **Step 1 (red):** paste `grep -rn "Opus 4.6" workflows/` (expect research.md:88, refactor.md:88 — execute.md's two are gone if wfo-05-3 merged first; if still present, note it and leave them to wfo-05-3) and `grep -n "claude-opus-4-6" workspace/learning/vol-learning-framework-design.md` (2 hits).
- [ ] **Step 2 (edit):**
  - `workflows/research.md:88`: `- All subagents MUST use Claude Opus 4.6` → `- Subagent model pinning: per `policy/subagent_protocol.md``
  - `workflows/refactor.md:88`: `- All subagents MUST use Claude Opus 4.6, depth = 1 (no further spawning)` → `- Subagent model pinning and depth (= 1, no further spawning): per `policy/subagent_protocol.md``
  - `workflows/INDEX.md:13`: `**Routing rule:** Follow the `/prompt` attachment. No prompt? Match keywords below. No match? Default to `plan.md`.` → `**Routing rule (canonical: AGENTS.md §Routing):** follow the `/prompt` attachment; no prompt → match keywords below; no match → default to `plan.md`.`
  - `workflows/_protocol.md:13`: `If unclear which workflow applies: follow the `/prompt` attachment. No prompt? Use keywords from `INDEX.md`. Still unclear? Default to `plan.md`.` → `If unclear which workflow applies: apply the routing rule in `AGENTS.md` (keywords live in `INDEX.md`).`
  - `vol-learning-framework-design.md:1079`: extend the parenthetical to `(claude-opus-4-6 — API slug, informational only; VS Code prompt frontmatter uses the picker display name "Claude Opus 4.6")`. At `:1175`, append to the criterion line: `(the display name is the operative form; the slug never goes in frontmatter)`.
  - `workspace/lint/whitelists/model_pins.txt` (PARTIAL burn): after the pointer/label edits above, `grep -n "Claude Opus 4.6"` each path the whitelist lists and delete every entry whose target file no longer contains the literal — at minimum the four sites just cleaned (`research.md`, `refactor.md`, `INDEX.md`, `_protocol.md`). Leave any entry whose site still holds the literal (deleting it turns lint red); those, plus the `_dormant` residue, are Plan 07's to empty. Do NOT add or touch the two SANCTIONED_SITES (they are structurally exempt, never whitelisted).
- [ ] **Step 3 (green):** `grep -rln "Opus 4.6" workflows/` → 0 files; `workspace/lint/whitelists/model_pins.txt` no longer lists the four just-cleaned sites (paste the before/after entry list); `vol.cmd exec python workspace/lint/lint_all.py` → `PASS`, `EXIT_CODE=0`.
- [ ] **Step 4 (commit):** `chore(framework): pointer-ize model-pin prose and routing rule; label api slug`

---

### Task 6: Orphaned policy files — wired or folded, then deleted

**Files:** Modify — `AGENTS.md`, `policy/index.md`, `policy/working-agreements.md`, `policy/ml-constraints.md`, `.github/instructions/python.instructions.md`. Delete — `policy/routing.md`, `policy/operating-principles.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-05-6"
goal: "Kill AW-22/AW-53's orphan layer: delete policy/routing.md and policy/operating-principles.md (unique bullets folded into AGENTS.md first), wire policy/ml-constraints.md from python.instructions.md's mandated reads, wire preflight-gates.md from working-agreements.md's Slang section, wire interaction_model/communication_protocol/implementation_boundary from AGENTS.md Cross-References, and update policy/index.md — with zero broken references"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md
  - policy/index.md
  - policy/routing.md
  - policy/operating-principles.md
  - policy/ml-constraints.md
  - AGENTS.md
  - policy/working-agreements.md
  - .github/instructions/python.instructions.md
write_scope:
  - AGENTS.md
  - policy/index.md
  - policy/working-agreements.md
  - policy/ml-constraints.md
  - .github/instructions/python.instructions.md
  - policy/routing.md            # delete
  - policy/operating-principles.md   # delete
acceptance_criteria:
  - "test ! -f policy/routing.md AND test ! -f policy/operating-principles.md"
  - "grep -rn 'routing.md\\|operating-principles' AGENTS.md .github/ policy/ workflows/ personas/ skills/ memory/ -> 0 hits"
  - "grep -n 'ml-constraints' .github/instructions/python.instructions.md -> 1 hit (new mandated-read line)"
  - "grep -n 'preflight-gates' policy/working-agreements.md -> 1 hit"
  - "grep -c 'Opus 4.6' policy/index.md -> 0 (gloss stripped)"
  - "grep -n 'interaction_model\\|communication_protocol\\|implementation_boundary' AGENTS.md -> 3 hits (Cross-References rows)"
  - "vol.cmd exec python workspace/lint/lint_all.py -> OUTPUT_FILE contains PASS and EXIT_CODE=0 (lint_broken_refs must not flag the deletions)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "SELF-MODIFICATION: operating-principles.md duplicates rules that remain live in AGENTS.md/copilot-instructions.md — deleting it changes no obligation of this session. Before deleting either file, run the inbound-reference grep and repoint EVERY hit in the same commit."
  - "python.instructions.md: add EXACTLY ONE list line — do NOT fix the PurgedKFold import, do NOT delete the embedded class, do NOT touch applyTo (all Plan 06). ml-constraints.md: edit ONLY line 3's activation claim — its 8 rule sections are untouched (the purge-window >= horizon detail and QLIKE formula are the unique operative content being wired, not moved)"
  - "AGENTS.md is also edited by wfo-05-2 — this task runs in a LATER wave; rebase on the branch head and verify wfo-05-2's pointer lines are present before editing"
context_summary: |
  AW-22: six policy files are orphaned from all loading surfaces; two self-declare mandatory
  (preflight-gates.md:3 'Never skip, never defer.'; ml-constraints.md:3 'always active and cannot be
  overridden'). Nothing loads them — the only inbound path is the passive catalog policy/index.md.
  AW-53: policy/routing.md is a 212-byte stub whose index description ('prompt → keyword → pattern →
  effort pipeline') describes content it does not contain. Plan 05 wires the orphans to real loading
  surfaces (python.instructions.md mandated reads for ml-constraints; working-agreements Slang gate for
  preflight-gates; AGENTS.md Cross-References for the other three) and deletes the two zero-unique-content
  files. operating-principles.md's only content NOT already in AGENTS.md:145-158 is three bullets
  (solve directly; proceed automatically on low-risk reversible steps; newer instructions override the
  current branch without discarding standing constraints) — fold those into AGENTS.md Policy Quick-Ref
  BEFORE deleting. AW-14's canonical Key Constraints table already lives in AGENTS.md:77-86 (untouched).
depends_on: ["wfo-05-2", "wfo-05-3"]
```

- [ ] **Step 1 (red):** paste `grep -rn "routing.md" policy/ workflows/ AGENTS.md` and `grep -rn "operating-principles" policy/ AGENTS.md` (inbound refs: `policy/index.md:21,24`; possibly `workflows/INDEX.md`/`_protocol.md` — wfo-05-5 already repointed those routing lines) and `grep -rn "ml-constraints" .github/` (expect 0 — the orphan proof).
- [ ] **Step 2 (fold, then delete):**
  - Append to AGENTS.md Policy Quick-Ref (after the wfo-05-2 pointer bullets):
    ```markdown
    - **Solve directly** when you can do so safely and well.
    - **Proceed automatically** on clear, low-risk, reversible steps. Ask only for irreversible or materially branching decisions.
    - **Newer user instructions override** the current branch of work without discarding unrelated standing constraints.
    ```
  - Delete `policy/operating-principles.md` and `policy/routing.md` (git rm, explicit paths).
- [ ] **Step 3 (wire the survivors):**
  - `.github/instructions/python.instructions.md` — append to the numbered mandated-reads list (after item 4, `skills/PYTHON_MARKET_DATA/SKILL.md`):
    ```markdown
    5. policy/ml-constraints.md — non-negotiable ML constraints (purged CV with purge window ≥ forecast horizon, the QLIKE formula, log-RV space, COVID regime handling, per-experiment checklist) — read before any model, CV, or evaluation code change
    ```
  - `policy/ml-constraints.md:3` — replace `These rules govern all ML vol forecasting work. They are always active and cannot be overridden without explicit user approval.` with `These rules govern all ML vol forecasting work and cannot be overridden without explicit user approval. Loading surfaces: mandated read #5 in .github/instructions/python.instructions.md (every src Python edit touching models/CV/eval); summarized in the AGENTS.md Key Constraints table (canonical summary — this file owns the operative detail).`
  - `policy/working-agreements.md` — in the `## Slang-specific` section, append: `Full pre-flight gate list (user profile, Slang refs, RegTest, secexpr --safe, no hardcoded DBs): `policy/preflight-gates.md`.`
  - `AGENTS.md` Cross-References table — add three rows:
    ```markdown
    | Interaction & response depth | [policy/interaction_model.md](policy/interaction_model.md) |
    | Handoffs & escalation | [policy/communication_protocol.md](policy/communication_protocol.md) |
    | Implementation boundary | [policy/implementation_boundary.md](policy/implementation_boundary.md) |
    ```
- [ ] **Step 4 (edit `policy/index.md`):** delete the `routing.md` line (:24) and the `operating-principles.md` line (:21); in the `subagent_protocol.md` line (:17), change `model pinning (Opus 4.6), context packets` → `model pinning (canonical, with fallback), context packets`; bump the frontmatter `updated:` date.
- [ ] **Step 5 (green):** re-run Step-1 greps → 0; `test ! -f` both; `vol.cmd exec python workspace/lint/lint_all.py` → `PASS`, `EXIT_CODE=0`.
- [ ] **Step 6 (commit):** `chore(framework): wire orphan policy files, fold and delete routing and operating-principles`

---

### Task 7: Personas point at the canonical Key Constraints table

**Files:** Modify — `personas/model-builder.md`, `personas/eval-sentinel.md` (+ inspect the other 3 persona files, edit only if they restate constraints).

**Copilot context packet:**

```yaml
subtask_id: "wfo-05-7"
goal: "Replace restated ML-constraint blocks in the personas with 'apply the Key Constraints table (AGENTS.md)' pointers — model-builder.md's 'ML discipline (non-negotiable)' bullet block and eval-sentinel.md's constraint restatements — while keeping each persona's operative checklists"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md
  - personas/model-builder.md
  - personas/eval-sentinel.md
  - personas/                              # list the dir; inspect all 5 persona files
  - AGENTS.md                              # READ-ONLY: the Key Constraints table being pointed at
write_scope:
  - personas/model-builder.md
  - personas/eval-sentinel.md
  - personas/*.md                          # only the files found restating Key-Constraints content
acceptance_criteria:
  - "grep -rn 'ALWAYS train in log-RV space' personas/ -> 0 hits (restatement gone from constraints blocks)"
  - "grep -rln 'Key Constraints' personas/ -> >= 2 files (the pointer present)"
  - "grep -rn 'Opus 4.6' personas/ -> 0 hits"
  - "eval-sentinel.md still contains its Stage 1-3 execution-loop checklist (operative verification list is KEPT)"
  - "vol.cmd exec python workspace/lint/lint_all.py -> OUTPUT_FILE contains PASS and EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "Personas are role/behavior contracts — keep every non-constraint element (identity, effort gates, execution loops, ask gates, output formats) byte-identical. Only the blocks that RESTATE the AGENTS.md Key Constraints rows (QLIKE primary, purged CV, log-RV, COVID, feature-set>model, experiment logging) become pointers."
  - "eval-sentinel's Stage 1 'Protocol Compliance' CHECKLIST stays — it operationalizes the constraints for review; add the canonical-source pointer above it instead of deleting it"
context_summary: |
  AW-14: the non-negotiable ML constraints exist in 5-7 copies across 4 layers; AGENTS.md:77-86 is
  declared the canonical Key Constraints table (Plan 05 leaves the table untouched). model-builder.md:20's
  '**ML discipline (non-negotiable):**' block restates 6 of its rows in drifted wording;
  eval-sentinel.md:28 area restates them again. Personas must APPLY the table, not own a copy that
  can drift. python.instructions.md's copy is Plan 06's problem; ml-constraints.md's operative detail
  was wired by wfo-05-6.
depends_on: ["wfo-05-2"]
```

- [ ] **Step 1 (red):** paste `grep -rn "log-RV\|purged\|QLIKE\|COVID" personas/` — the duplicated constraint prose across persona files.
- [ ] **Step 2 (edit `personas/model-builder.md`):** replace the six-bullet `**ML discipline (non-negotiable):**` block with:
  ```markdown
  **ML discipline (non-negotiable):** apply the **Key Constraints** table in `AGENTS.md` — the canonical
  statement (QLIKE primary, purged/expanding CV only, log-RV training space, explicit COVID regime handling,
  feature set > model complexity, every experiment independently reportable). Operative detail:
  `policy/ml-constraints.md`. Do not restate or reinterpret these rules.
  - Log all experiments: hyperparameters, CV strategy, feature config, QLIKE results.
  ```
  *(The logging bullet survives as the persona-specific operationalization of the reproducibility row.)*
- [ ] **Step 3 (edit `personas/eval-sentinel.md`):** in its `<constraints>` block, replace any restated constraint sentences (the ~:28 region) with the same one-line pointer (`apply the **Key Constraints** table in `AGENTS.md`; operative detail in `policy/ml-constraints.md``). Directly above the Stage 1 checklist in `<execution_loop>`, insert: `Verify against the canonical Key Constraints table (`AGENTS.md`); this checklist operationalizes it and must not drift from it.` Keep the checklist itself.
- [ ] **Step 4 (sweep):** open the remaining 3 persona files; where a Key-Constraints row is restated as a rule (not as a domain-identity sentence), apply the same pointer treatment; list every file you did/didn't touch and why in the return `notes`.
- [ ] **Step 5 (green):** acceptance greps; `vol.cmd exec python workspace/lint/lint_all.py` → `PASS`, `EXIT_CODE=0`.
- [ ] **Step 6 (commit):** `chore(framework): personas apply canonical key constraints instead of restating`

---

### Task 8: Contradiction grep-list, boot measurement, MR evidence

**Files:** Create (ephemeral) — `workspace/tmp/wfo05_boot_measure.py` (deleted after use). No tracked-file edits.

**Copilot context packet:**

```yaml
subtask_id: "wfo-05-8"
goal: "Run the full Plan-05 contradiction grep-list (G1-G13) and the boot bytes/4 before/after measurement, paste all outputs, and assemble the MR-description evidence block — zero repo files modified"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md   # §8 carries the grep-list and script
  - AGENTS.md
  - .github/copilot-instructions.md
  - workflows/
  - policy/
  - personas/
write_scope:
  - workspace/tmp/wfo05_boot_measure.py     # created, run, then DELETED (Rule 1)
acceptance_criteria:
  - "All 13 grep-list checks in plan §8 pass with the exact expected counts; full output pasted in the return"
  - "Boot measurement table (5 files, bytes/4 before from git merge-base, after from worktree) produced and pasted"
  - "vol.cmd exec python workspace/lint/lint_all.py -> OUTPUT_FILE contains PASS and EXIT_CODE=0"
  - "workspace/tmp/wfo05_boot_measure.py deleted after use (show the delete)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "READ/MEASURE ONLY — if any check fails, do NOT fix it; return blocked naming the failing check and the owning task (wfo-05-1..7) so the orchestrator can re-dispatch"
  - "Run everything via vol.cmd exec (S-A) / ./vol exec (S-B) sentinels; never trust the terminal buffer; kill all terminals before returning"
context_summary: |
  Final verification task. The Plan-05 acceptance gate is: lint stays green; the contradiction grep-list
  (§8, G1-G13) returns 0 / the exact expected counts; boot-token bytes/4 measured before/after and recorded
  in the MR description (target direction ~10,235 -> toward ~7,500 suite-wide; Plan 05 moves the
  copilot-instructions/AGENTS pair — Plan 06 moves the three memory files; treat numbers as directional,
  never a hard gate; a dramatic saving means bytes/4 mis-measured or content lost — investigate).
  'Before' = the merge-base with origin/master (pre-Plan-05 branch point), recovered via git show.
depends_on: ["wfo-05-1", "wfo-05-2", "wfo-05-3", "wfo-05-4", "wfo-05-5", "wfo-05-6", "wfo-05-7"]
```

- [ ] **Step 1:** run every check in §8 (the grep-list) via `vol.cmd exec`; paste all outputs.
- [ ] **Step 2:** write, run, and then delete this exact script (`workspace/tmp/wfo05_boot_measure.py`):
  ```python
  """Boot-load measurement: bytes/4 before (merge-base with origin/master) vs after (worktree)."""
  import subprocess, os
  FILES = [".github/copilot-instructions.md", "AGENTS.md", "memory/person/user.md",
           "memory/research/project-state.md", "memory/INDEX.md"]
  base = subprocess.run(["git", "merge-base", "HEAD", "origin/master"],
                        capture_output=True, text=True, check=True).stdout.strip()
  tb = ta = 0
  print(f"{'file':<45}{'before_B':>9}{'after_B':>9}{'before_t':>9}{'after_t':>9}")
  for f in FILES:
      b = len(subprocess.run(["git", "show", f"{base}:{f}"], capture_output=True, check=True).stdout)
      a = os.path.getsize(f)
      tb += b; ta += a
      print(f"{f:<45}{b:>9}{a:>9}{b//4:>9}{a//4:>9}")
  print(f"{'TOTAL':<45}{tb:>9}{ta:>9}{tb//4:>9}{ta//4:>9}")
  ```
  Expected direction: the pair `copilot-instructions.md` + `AGENTS.md` shrinks (pre-suite mirror baseline: 3,967 B + 12,844 B ≈ 4,203 t; AW-26 prior: ~350–1,200 t/request of duplication removed); the three memory files are ~unchanged (Plan 06's job). Paste the table verbatim into the MR description under a `## Boot-load measurement (bytes/4, directional)` heading.
- [ ] **Step 3:** confirm `lint_all.py` PASS on S-A (sentinel evidence). If an S-B Coder session is available this sitting, also run `./vol exec python workspace/lint/lint_all.py` and paste; if not, state "S-B deferred to Plan 06 session-start precondition" in `notes`.
- [ ] **Step 4:** delete `workspace/tmp/wfo05_boot_measure.py`; kill all terminals (EXIT GATE); return the assembled MR-description evidence block in `notes`.

*(No commit — this task produces evidence, not tree changes.)*

---

## 5. Configs / experiments

None. This plan ships no runnable experiments — it is policy/docs-only, TDD-exempt under Rule 5, and gated entirely by the lint suite plus the §8 grep-list. (The template's YAML-config section is intentionally empty; do not invent a config.)

---

## 6. Findings coverage (this plan's 13 AW-IDs → tasks)

| AW-ID | Killed by | Note |
|---|---|---|
| AW-G2 | T1 (Rule 9 fallback) | surface scoping began in Plan 02 |
| AW-G4 | T1 (fallback clause; prompt frontmatter untouched per do-NOT) | |
| AW-G5 | T1 + T5 (display name = `EXPECTED_MODEL`; slug labeled informational) | |
| AW-14 | T2 (canonical table stands) + T6 (ml-constraints wired) + T7 (personas point) | PurgedKFold import + embedded-class deletion → Plan 06 |
| AW-22 | T6 (all 6 orphans wired or folded+deleted) | preflight gates stay a file, now wired |
| AW-26 | T1 (ruff merge) + T2 (5 blocks → pointers) | /team depth drift closed via T4 pointer |
| AW-27 | T1 (Rule 6) + T3 (working-agreements:9, fix.md ×6 lines, execute.md ×2) | pair-complete list is T3's write_scope |
| AW-28 | T1 (unified Rule 1) + T2 (AGENTS:154-155 deleted) | gsvivs-audit.prompt.md:147 relocates in Plan 07 |
| AW-35 | T4 | do-NOT-collapse honored: two files remain |
| AW-38 | T3 (BOTH execute.md:76 and :104) | |
| AW-42 | T2 (AGENTS boot canonical; bootup.md = delta; INDEX ambiguity fixed) | |
| AW-49 | T2 (boot step 4 DELETED — decision recorded §3) + T1 (3-line boot pointer) | AGENTS.md:58 backtick fix already landed in Plan 04 |
| AW-53 | T3/T5 (pin prose) + T5 (routing pointers) + T6 (routing.md deleted, index updated) | prompt frontmatter untouched |

---

## 7. Wave plan (disjoint write_scopes; from `depends_on`)

| Wave | Tasks | Write scopes (disjoint within wave) |
|---|---|---|
| 1 | wfo-05-1 | `.github/copilot-instructions.md` |
| 2 (parallel, max 4) | wfo-05-2 · wfo-05-3 · wfo-05-4 · wfo-05-5 | `AGENTS.md`+`bootup.md` · `working-agreements.md`+`fix.md`+`execute.md` · `subagent_protocol.md`+`context-isolation.md`+`plan.md`+`team.md` · `research.md`+`refactor.md`+`INDEX.md`+`_protocol.md`+`vol-learning-framework-design.md`+`workspace/lint/whitelists/model_pins.txt` |
| 3 (parallel, max 2) | wfo-05-6 · wfo-05-7 | `routing.md`+`operating-principles.md`+`index.md`+`ml-constraints.md`+`python.instructions.md`+`AGENTS.md`+`working-agreements.md` (both free — their Wave-2 owners finished) · `personas/*.md` |
| 4 | wfo-05-8 | `workspace/tmp/` only (evidence) |

The always-on pair is never in two concurrent write_scopes: `copilot-instructions.md` only in Wave 1; `AGENTS.md` in Wave 2 (T2) then Wave 3 (T6), never twice at once.

---

## 8. Acceptance gate → Plan 06 (the contradiction grep-list, enumerated)

All commands run via `vol.cmd exec` (S-A) or `./vol exec` (S-B); every expected value exact:

| # | Check | Command | Expected |
|---|---|---|---|
| G1 | One lint policy (agreements) | `grep -rn "Run lint, typecheck, and tests after changes" policy/` | 0 hits |
| G2 | One lint policy (fix.md) | `grep -rn "Lint gate is mandatory" workflows/` | 0 hits |
| G3 | Rule 6 not struck-through | `grep -n "DISABLED" .github/copilot-instructions.md` | 0 hits |
| G4 | One packet schema | `grep -rln "subtask_id:" policy/ workflows/` | exactly `policy/subagent_protocol.md` |
| G5 | Boot step 4 dead | `grep -rn "session-handoff" AGENTS.md workflows/` | 0 hits |
| G6 | One boot list | `grep -n "memory/person/user.md" workflows/bootup.md` | 0 hits |
| G7 | Zero raw model-pin prose | `grep -rln "Opus 4.6" AGENTS.md policy/ workflows/ personas/ memory/ --exclude-dir=_dormant` | exactly `policy/subagent_protocol.md` |
| G8 | Rule-9 pointer form only | `grep -c "Opus 4.6" .github/copilot-instructions.md` | 1 |
| G9 | One tmp policy | `grep -n "No throwaway scripts" AGENTS.md` | 0 hits |
| G10 | One /team depth | `grep -rn "must NOT spawn sub-workers" workflows/` | 0 hits |
| G11 | One depth table | `grep -rln "Leader → Worker → Sub-worker" policy/ workflows/` | exactly `policy/subagent_protocol.md` |
| G12 | Orphans dead + unreferenced | `test ! -f policy/routing.md && test ! -f policy/operating-principles.md; grep -rn "routing.md\|operating-principles" AGENTS.md .github/ policy/ workflows/ personas/ skills/ memory/` | files absent; 0 hits |
| G13 | Standing lint gate | `python workspace/lint/lint_all.py` (via sentinel) | full PASS, `EXIT_CODE=0`, on S-A (and S-B when a Coder session is available) |

**G7 scope note:** the `--exclude-dir=_dormant` is deliberate. `memory/_dormant/sys/secdb-ecosystem.md` still carries a raw `Opus 4.6` literal, and only **Plan 07 Task 12** sweeps it — at Plan 05's gate that residue is out of scope, so the scan excludes `_dormant/` and asserts the match set == exactly `policy/subagent_protocol.md`. The other sanctioned raw-literal site, `.github/copilot-instructions.md` Rule 9 (fallback clause), lives under `.github/` and is intentionally outside this scan set (it is a `SANCTIONED_SITES` path, not prose to purge). After Plan 05, `policy/subagent_protocol.md` is the only in-scope file that keeps the literal.

Plus: the boot-measurement table (Task 8) is present in the MR description with before/after bytes/4 for all 5 boot files — directional evidence, not a hard gate.

**What Plan 06 consumes from this plan:** the canonical boot list in AGENTS.md (Plan 06 edits `project-state.md`/`user.md`/`INDEX.md` *contents*, never the list); the single packet schema in `subagent_protocol.md` (Plan 06 packets validate against it); Rule 6's final wording (Plan 06's `python.instructions.md` rework must not reintroduce a per-change lint mandate); the ml-constraints wire from `python.instructions.md` (Plan 06 keeps that line when it re-scopes `applyTo` and fixes the PurgedKFold import); the deleted-files list (Plan 06's broken-refs sweeps must not resurrect `routing.md`/`operating-principles.md` references).

---

## 9. Orchestrator prompt

```
/execute Implement Plan 05 (Single Source of Truth) from workspace/plans/copilot-workflow-overhaul/plan-05-single-source-of-truth.md

Precondition check: Plan 04 gate — run `vol.cmd exec python workspace/lint/lint_all.py`, read the
OUTPUT_FILE: full PASS (21 checks: 14 base + 1 Plan-01 secrets + 6 Plan-04) and EXIT_CODE=0. If not green, STOP: Plan 05 may not start.
Create branch chore/wf-overhaul-05-ssot off master (rebase onto origin/master first).

Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.

⚠ SELF-MODIFICATION: this plan rewrites the always-on rules governing THIS session and its subagents.
Every packet quotes the pre-edit rule text — subagents obey the QUOTED text for their own conduct and
return blocked (with the diff) if the live file differs. Never let a subagent obey a half-rewritten rule.
Do not run this plan while any research /execute session is live.

Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1: wfo-05-1
  Wave 2 (parallel, max 4): wfo-05-2, wfo-05-3, wfo-05-4, wfo-05-5
  Wave 3 (parallel, max 2): wfo-05-6, wfo-05-7
  Wave 4: wfo-05-8
Waves = disjoint write_scopes; respect depends_on. The always-on pair is never in two concurrent
write_scopes (copilot-instructions.md: Wave 1 only; AGENTS.md: wfo-05-2 then wfo-05-6, sequential).

Each subagent: docs/config only (TDD-exempt per Rule 5) — show red-then-green via the task's greps;
lint_all.py PASS is part of EVERY task's acceptance; terminal isolation + cleanup (kill_terminal EXIT
GATE); return the §5.2 return contract verbatim (status, files_changed, verification, blockers, notes).
Retry a blocked/partial subagent once with a refined packet, then escalate with both attempts' evidence.

Integration verification (orchestrator, after all tasks): run the full §8 grep-list G1–G13 and paste
outputs; confirm the boot-measurement table from wfo-05-8; put both into the MR description
(human-generic title, no finding IDs in the title; AW-IDs and measurements in the description).
Update workspace/research/weekly-progress.md (Shipped section, one line, plain language).
Kill all terminals. Do NOT start Plan 06.
```
