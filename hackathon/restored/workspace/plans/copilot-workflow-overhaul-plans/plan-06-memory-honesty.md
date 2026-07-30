# Plan 06 — Memory & Instruction-File Honesty (S6)

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §8.
> Dispatch each task as a subagent with the context packet provided. Max 6 concurrent subagents.
> TDD (copilot-instructions.md Rule 5) exempts config, docs, memory, YAML, workflows, prompts — which is
> this entire plan. The only non-doc touch is a one-line comment fix in `src/volforecast/registry.py`
> (no behavior change; no test applicable — justified in Task 5). The Plan-04 lint gates stay strict; this
> plan makes their content honest and burns the grandfather whitelists (`budget_grandfather.txt`,
> `broken_refs.txt`, `canonical_schema.txt`) to header-only — red-then-green shown via each lint itself
> (Tasks 3, 5, 8).
> Requires Plans 01–05 merged; the Plan-04 lint gate (`python workspace/lint/lint_all.py` → PASS) must be
> green at start and stay green at every commit.

**Goal:** every boot-loaded and on-demand memory/instruction file tells the truth — measured token
numbers, no dead paths, no self-contradictions, no Brazil-desk examples for a US project — so the
memory-budget and broken-refs lints pass on *measured* content (P0+P1 ≤ 50k real tokens) and the
always-on boot chain drops toward ~7,500 tokens.

**Architecture:** this plan is pure content remediation riding on machinery earlier plans built. Plan 04
rewrote `lint_memory_priority.py` to measure bytes/4 and extended `lint_broken_refs.py` to see plain-text
paths and `_dormant` (both shipped with grandfather escapes so Plan 04's gate could pass on the then-broken
content — this plan fixes the content and removes the escapes). Plan 05 made `copilot-instructions.md` the
sole HARD-rule owner, so the files edited here are pointers-and-content only, never rule owners. The
existing P0–P3 tier scheme, `memory/INDEX.md` table format, and the `_CANONICAL_EXAMPLE.yaml`
schema-maintenance mechanism are kept (do-not-rebuild inventory #5/#10) — only their content is
regenerated from measurement and live registries.

**Tech stack:** No new dependencies. All edits are Markdown/YAML plus one comment line in existing
Python and three grandfather-whitelist `.txt` files burned to header-only; verification via the existing
stdlib-only `workspace/lint/` suite and `./vol exec` / `vol.cmd exec`.

**Research grounding:** the 2026-07 agentic-workflow audit, findings AW-12, 15, 16, 17, 19, 20, 29, 34,
48, G15, G18, G19, G20, G22, G23, G24, G25, G26 (all re-verified live 2026-07-07). Expected-outcome
priors (00-overview §4): P0+P1 measured 79,779 t (excl. `trials.yaml`; 111,536 incl.) → **≤ 50k**;
non-`src/` Python edit overhead **−3,083 t/edit** (AW-19); broken skill→memory refs **51 → 0**
(48 rewrites + 3 dead handled); boot chain ~10,235 t → **~7,500 t** directional. **Sanity rule:** a
measured saving far better than the prior means bytes/4 mismeasured or load-bearing content was deleted —
investigate before celebrating. Token numbers are directional evidence, never hard gates.

---

## 1. Global constraints

All of 00-overview §5 (shared conventions) applies. Plan-specific hard rules:

1. **Drift check (every packet):** verify the cited path:line against the live tree before editing; if it
   moved, locate by content and note the delta in your return. This plan was written against a mirror
   verified byte-identical 2026-07-07.
2. **The 5 ACTIVE research plans in `workspace/plans/` are read-only.** Never touch `trials.yaml` content
   or `workspace/configs/` beyond `_CANONICAL_EXAMPLE.yaml` (Task 5). (`trials.yaml`'s INDEX *row* may be
   re-tiered in Task 8; the file itself is untouched.)
3. **Never redesign the tier scheme, the INDEX table concept, or the canonical-example mechanism** —
   regenerate content only (do-not-rebuild #5/#10).
4. **Preserve the load-bearing:** `memory/person/user.md` line 56 (numbered next-steps + /slash
   convention) survives verbatim (AW-16 do-NOT). `skills/CANVAS/SKILL.md:32` is already correct — do not
   touch it (only :258/:260 are wrong). Do NOT claim gnn configs fail at `runner.py:1509` in any doc text
   (AW-G22 do-NOT). Do NOT convert any bare backtick path to a Markdown link (lint-enforced repo pattern).
5. **memory/INDEX.md has exactly one writer in this plan: Task 8.** Tasks 1–7 that create/resize/re-tier
   files emit the needed INDEX row facts in their return `notes:` and never edit INDEX themselves.
6. **Lint stays green at every commit** except where a task explicitly shows a red→green transition on the
   check it owns (Tasks 3 and 8, which remove the Plan-04 grandfather escapes).
7. Self-modification hazard does not apply here (no always-on rule files are rewritten by this plan —
   Plan 05 finished that), but `.github/instructions/*.md` edits change what attaches to future edits in
   this very session: instruction-file tasks (4, 5) note this in their packets and do not rely on the
   pre-edit instruction content after their own commit.

## 2. File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `memory/research/project-state.md` | Reconcile LSTM + Blocker contradictions; prune ~40% stale history (AW-16) |
| Modify | `memory/person/user.md` | Collapse dormant Slang block :44-55 to one line; preserve :56 (AW-16) |
| Modify | `workspace/research/research-journal.md` | Receive the pruned project-state history as a dated entry (AW-16) |
| Rewrite | `memory/research/research-journal.md` | Convert stale fork to a ≤15-line pointer card (AW-17) |
| Delete | `memory/research/README.md` | Orphaned stale second index with 3 dead filenames (AW-48) |
| Modify | `.github/prompts/research.prompt.md` | Line 13 repointed from README.md to `memory/INDEX.md` (AW-48) |
| Modify | 27 × `skills/*/SKILL.md` | Batch-rewrite 48 `memory/{ref,sys,slang}/` refs → `memory/_dormant/…`; fix RESEARCH:50/:145; delete SEARCH:75 dead ref (AW-12) |
| Modify | `memory/meta/guide.md` | Add `dormant` status + park/restore procedure (AW-34) |
| Modify | 37 × `memory/_dormant/**/*.md` frontmatter | `status: dormant`; fix `secdb.md` malformed `source:` (AW-34) |
| Modify | `workspace/lint/whitelists/broken_refs.txt` | Burn the Plan-04 broken-refs grandfather whitelist to header-only (AW-12 closure) |
| Modify | `.github/instructions/python.instructions.md` | `applyTo` → `src/**/*.py`; fix PurgedKFold import; delete embedded class + duplicated blocks; kill EDRVOL typo (AW-19, AW-14-import) |
| Create | `.github/instructions/python-helpers.instructions.md` | Small env + file-output instruction for `{skills,workspace}/**/*.py` (AW-19) |
| Modify | `.github/instructions/yaml-config.instructions.md` | Enum tables regenerated from live registries; ale_features default fix (AW-20, G24, G25, G26, G22-doc) |
| Modify | `workspace/configs/_CANONICAL_EXAMPLE.yaml` | Add conditional_duan, cv.embargo, gnn, blend, implied_correlation, sequences.source (AW-G23) |
| Modify | `workspace/lint/whitelists/canonical_schema.txt` | Burn the Plan-04 canonical-schema grandfather whitelist to header-only (AW-G23 closure) |
| Modify | `src/volforecast/registry.py` | Line ~45 comment-only correction (AW-G22; no behavior change) |
| Rewrite | `memory/ref/python-tsdb.md` | ≤250 lines, US-universe examples (AW-29) |
| Rewrite | `memory/ref/python-chunk.md` | ≤250 lines, US-universe examples (AW-29) |
| Create | `memory/ref/python-tsdb-fields.md` | P2 companion holding the ~185-row TSDB field dictionary (AW-29) |
| Modify | `workspace/docs/data-audit.md` | TODO→Implemented appendix rows; reproducible provenance (AW-G15, G18) |
| Modify | `workspace/docs/user-manual.md` | Surface tags, ${ROOT} paths, present/kvar/cache rows, plans-tree row (AW-G19, G20-residue) |
| Rewrite | `memory/INDEX.md` | Measured ~Tokens, Status/Updated columns, dead rows deleted, demotions, dormant + new-file rows (AW-15, 48) |
| Modify | `workspace/lint/whitelists/budget_grandfather.txt` | Burn the Plan-04 budget grandfather whitelist to header-only once demotions land P0+P1 ≤ 50k (AW-15 closure) |

Branch: `chore/wf-overhaul-06-memory-honesty` off `master`. One MR. MR description carries the
before/after boot-token measurement (ledger row "Boot measurement").

## 3. Interfaces

**Consumes (copied from the 00-overview §6 ledger — never re-derived):**
- `S-A` / `S-B` surface definitions; Gate D evidence commands (`vol.cmd test -x -q` on S-A, `./vol test` on S-B) are available as acceptance vehicles.
- `vol.cmd` (Plan 03): `exec`/`bg` writing the sentinel protocol `workspace/tmp/exec/<ts>_<pid>.out` with `OUTPUT_FILE=`/`EXIT_CODE=` lines — used for all S-A command evidence.
- Memory-budget fix (Plan 04): `lint_memory_priority.py` + `validate_memory.py` measure tokens = bytes/4; `research` domain has a cap. INDEX path-existence is enforced separately by `lint_memory_index_completeness.py` (Plan 04 G3). The budget check is always strict, kept green by `workspace/lint/whitelists/budget_grandfather.txt`; Plan 06 makes content pass and burns that whitelist to header-only.
- `LINTS` registry (`workspace/lint/lint_all.py:57-156`): run checks via `python workspace/lint/lint_all.py [--check <label>]`.
- Boot measurement definition: bytes/4 over the 5 boot files (`.github/copilot-instructions.md`, `AGENTS.md`, `memory/person/user.md`, `memory/research/project-state.md`, `memory/INDEX.md`), recorded in the MR description.
- `subtask_id` format `wfo-06-<M>`; branch format `chore/wf-overhaul-NN-<topic>`.

**Consumed from the §6a ledger addenda (authoritative names — the producer plan's spelling wins; if the live artifact differs, locate by content and note the delta):**
- Plan-04 broken-refs grandfather whitelist: `workspace/lint/whitelists/broken_refs.txt` (§6a; created by wfo-04-9) — one repo-relative "source-file:line → target" entry per line, read by the extended `lint_broken_refs.py`. Task 3 burns it to header-only.
- Plan-04 budget grandfather whitelist: `workspace/lint/whitelists/budget_grandfather.txt` (§6a; created by wfo-04-2) — holds the grandfathered over-budget allowance while the always-strict budget check in `lint_memory_priority.py` stays green. Task 8 burns it to header-only once demotions land P0+P1 ≤ 50k.
- Plan-04 canonical/enum completeness check: `workspace/lint/lint_canonical_schema.py`, LINTS label `canonical schema` (§6a; created by wfo-04-10), kept green by `workspace/lint/whitelists/canonical_schema.txt`. Task 5's gate; the whitelist burns to header-only.

**Produces (later plans rely on):**
- `.github/instructions/python-helpers.instructions.md` — `applyTo: "{skills,workspace}/**/*.py"`, env + file-output rules only (~25 lines).
- `memory/ref/python-tsdb-fields.md` — P2, on-demand TSDB field dictionary.
- `memory/INDEX.md` v2 format: columns `File | Priority | ~Tokens | Status | Updated | Load Trigger`; ~Tokens always measured bytes/4.
- Canonical self-validation command (used again at Plan-08 closure):
  `./vol exec python -c "from volforecast.config import load_config; load_config('workspace/configs/_CANONICAL_EXAMPLE.yaml'); print('CANONICAL-OK')"`
  (if `load_config` is not the public loader name, substitute the entry point `src/volforecast/cli/experiment.py` uses and note the delta).
- An honest prompt-adjacent surface for Plan 07: `research.prompt.md:13` points at `memory/INDEX.md`; INDEX Status column lets Plan 07's INDEX-of-prompts work cite live docs only.

---

## Task 1: project-state.md and user.md tell one story (AW-16)

**Files:** Modify `memory/research/project-state.md`, `memory/person/user.md`,
`workspace/research/research-journal.md` (append-only). Test = lint + greps (doc task, TDD-exempt).

**Copilot context packet:**

```yaml
subtask_id: "wfo-06-1"
goal: "memory/research/project-state.md contains zero self-contradictions (LSTM status, Blocker), ~40% stale history is moved verbatim to the live journal, and user.md's dormant Slang block collapses to one line — verified by the greps in acceptance_criteria."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md   # this task section
  - memory/research/project-state.md
  - memory/person/user.md
  - workspace/research/research-journal.md
write_scope:
  - memory/research/project-state.md
  - memory/person/user.md
  - workspace/research/research-journal.md
acceptance_criteria:
  - "grep -n 'CLOSED (2026-06-22)' memory/research/project-state.md -> 0 matches"
  - "grep -c 'reopened' memory/research/project-state.md -> exactly 1 (the reconciled Current State line)"
  - "grep -n 'Blocker' memory/research/project-state.md -> the :21 field reads 'None for the champion (tree-model) track; data-ingestion BLOCKER for L3-L7 feature layers' (one statement, no bare 'Blocker: None')"
  - "grep -n 'Retracted' workspace/research/research-journal.md -> the moved table is present under a 2026-07-dated heading"
  - "sed -n '56p' memory/person/user.md (pre-edit line 56 content) still present verbatim somewhere in user.md"
  - "python workspace/lint/validate_memory.py -> PASS"
  - "wc -c memory/research/project-state.md -> <= 6500 bytes (from 9,928)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "move history VERBATIM (no paraphrase) so nothing is lost; the boot file keeps only operative methodology"
  - "PRESERVE user.md line 56 (numbered next-steps + /slash command convention) exactly"
  - "do not edit memory/INDEX.md — Task 8 owns it; report your final byte counts in notes"
context_summary: |
  project-state.md is a P0 boot file loaded every session. It currently says both "LSTM research line
  reopened" (line 15, trial-073, 2026-07-01) and "LSTM research line CLOSED (2026-06-22)" (line 84), and
  both "Blocker: None" (line 21) and "Data Ingestion Infrastructure (BLOCKER — blocks L3-L7)" (line 89).
  ~4,032 of 10,038 bytes are dated history. The live journal is workspace/research/research-journal.md
  (the memory/ twin becomes a pointer card in Task 2 — do not touch it). Decided: prune-and-move, not
  rewrite; the reconciliation wordings below are fixed, do not redesign them.
depends_on: []
```

- [ ] **Step 1 — record the red state:** run and paste:
  `grep -n "reopened\|CLOSED (2026-06-22)\|Blocker" memory/research/project-state.md`
  Expected: hits at :15, :21, :84, :89 (or content-located equivalents) showing both contradiction pairs.
- [ ] **Step 2 — move history to the journal (verbatim):** append to
  `workspace/research/research-journal.md` a new entry at the top of the entries section:

  ```markdown
  ## 2026-07-XX — project-state.md pruning (workflow-overhaul Plan 06, AW-16)

  The following blocks were moved verbatim from memory/research/project-state.md (P0 boot file)
  to keep the boot file operative-only. Original locations noted.

  ### Retracted results table (was project-state.md:40-51)
  <paste lines 40-51 verbatim>

  ### IV-sanity results (was project-state.md:53-60)
  <paste lines 53-60 verbatim>

  ### Key Decisions log, 22 dated entries (was project-state.md:62-85)
  <paste lines 62-85 verbatim>
  ```

  Substitute the actual date for `2026-07-XX` (execution-day value — sanctioned deferral).
- [ ] **Step 3 — reconcile project-state.md:** delete the moved lines; then:
  - Current State LSTM line becomes exactly:
    `LSTM research line reopened 2026-07-01 via trial-073 (previously closed 2026-06-22; closure entry moved to the research journal).`
  - Line 21 Blocker field becomes exactly:
    `**Blocker:** None for the champion (tree-model) track; data-ingestion BLOCKER for L3-L7 feature layers (see Data Ingestion Infrastructure below).`
  - The `### Data Ingestion Infrastructure (BLOCKER — blocks L3-L7 feature layers)` section stays (it is
    operative: Step 3 of 3 incomplete). Keep any still-operative methodology bullets from the Key
    Decisions block by rewriting them as present-tense facts under Current State (e.g. evaluation
    settings), but no dated decision entries remain in the file.
  - Update frontmatter `updated:` to the execution date.
- [ ] **Step 4 — collapse user.md dormant block:** replace lines 44-55 (dormant Slang/GitLab conventions)
  with the single line:
  `Slang/GitLab working conventions: parked in memory/_dormant/ — restore if Slang work resumes.`
  Line 56 survives verbatim. Update frontmatter `updated:`.
- [ ] **Step 5 — run to green:** all acceptance_criteria commands; paste outputs. Note final `wc -c` of
  both memory files in the return `notes:` (Task 8 needs them).
- [ ] **Step 6 — commit:** `docs(memory): reconcile project-state contradictions, move stale history to journal`

## Task 2: un-fork the research journal, delete the stale second index (AW-17, AW-48)

**Files:** Rewrite `memory/research/research-journal.md`; delete `memory/research/README.md`;
modify `.github/prompts/research.prompt.md`. Doc task, TDD-exempt.

**Copilot context packet:**

```yaml
subtask_id: "wfo-06-2"
goal: "memory/research/research-journal.md is a <=15-line pointer card to the live workspace twin, memory/research/README.md is deleted, and research.prompt.md:13 loads memory/INDEX.md instead — with lint_broken_refs green and weekly-progress.md's relates: link still resolving."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md   # this task section
  - memory/research/research-journal.md
  - memory/research/weekly-progress.md          # the pointer-card exemplar — mirror its frontmatter keys
  - workspace/research/research-journal.md      # READ-ONLY here (Task 1 appends to it; do not write)
  - .github/prompts/research.prompt.md
write_scope:
  - memory/research/research-journal.md
  - memory/research/README.md                   # delete
  - .github/prompts/research.prompt.md
acceptance_criteria:
  - "test ! -f memory/research/README.md (file gone)"
  - "wc -l memory/research/research-journal.md -> <= 20 (frontmatter + <=15 body lines)"
  - "grep -n 'workspace/research/research-journal.md' memory/research/research-journal.md -> >=1 match (Location line)"
  - "grep -n 'README' .github/prompts/research.prompt.md -> 0 matches; grep -n 'memory/INDEX.md' .github/prompts/research.prompt.md -> 1 match at the former line-13 bullet"
  - "grep -n 'research-journal' memory/research/weekly-progress.md -> its relates:/pointer text still resolves to an existing file"
  - "python workspace/lint/lint_all.py --check 'broken refs' -> PASS"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "BEFORE converting: spot-check that the memory copy's 3 newest entry headings exist in the workspace twin; if any entry is missing there, STOP and return blocked with the list (Task 1 owns workspace-journal writes)"
  - "keep the bare-backtick path style in research.prompt.md — never a Markdown link"
  - "do not edit memory/INDEX.md (row :39 repoint is Task 8's)"
context_summary: |
  The journal is forked: memory/INDEX.md:39 routes continuity to memory/research/research-journal.md
  (11,332 B, newest entry 2026-06-03) while every workflow writes/reads
  workspace/research/research-journal.md (33,736 B, newest 2026-07-01). Decided: the workspace file is
  the single live journal; the memory twin becomes a pointer card mirroring how
  memory/research/weekly-progress.md points to ITS workspace twin (Location line + source frontmatter).
  memory/research/README.md lists three files that do not exist and is loaded by /research every
  invocation (AW-48) — it is deleted, not fixed. INDEX row :39 is repointed by Task 8, not here.
depends_on: []
```

- [ ] **Step 1 — record the red state:** paste `wc -c` of both journals and
  `grep -n "project-plan.md\|open-questions.md\|project-proposals.md" memory/research/README.md`
  (3 dead filenames) and `sed -n '13p' .github/prompts/research.prompt.md`.
- [ ] **Step 2 — overlap check** (constraint above). Paste the 3 newest memory-copy headings and their
  grep hits in the workspace twin.
- [ ] **Step 3 — write the pointer card:** replace the body of `memory/research/research-journal.md`
  with (copy frontmatter *keys* from `memory/research/weekly-progress.md`, keep `created:` from the old
  file, set `updated:` to today, keep the filename so `relates: [research-journal]` elsewhere still
  resolves):

  ```markdown
  ---
  <weekly-progress.md's frontmatter keys, incl. its source/Location convention>
  ---
  # Research Journal — moved

  **Location:** `workspace/research/research-journal.md` — the live, append-only session journal
  (written by workflows/research.md step "journal", read by workflows/bootup.md and /research).

  This memory copy stopped receiving entries on 2026-06-03 and is now a pointer (Plan 06, AW-17).
  All entries live in the workspace journal. Do not append here.
  ```

- [ ] **Step 4 — delete README + repoint the prompt:** delete `memory/research/README.md`. In
  `.github/prompts/research.prompt.md` line 13, replace the `memory/research/README.md` bullet with
  `` - `memory/INDEX.md` (research section — load-trigger table)`` (bare backticks).
- [ ] **Step 5 — run to green:** all acceptance_criteria; paste outputs.
- [ ] **Step 6 — commit:** `docs(memory): journal pointer card + delete stale research README, repoint /research`

## Task 3: `_dormant` gets a real lifecycle; 51 broken skill→memory refs die (AW-12, AW-34)

**Files:** Modify up to 27 `skills/*/SKILL.md`; `memory/meta/guide.md`; 37 `memory/_dormant/**/*.md`
frontmatters; burn `workspace/lint/whitelists/broken_refs.txt` to header-only. Doc task, TDD-exempt; the
red→green is the broken-refs lint with its grandfather whitelist emptied.

**Copilot context packet:**

```yaml
subtask_id: "wfo-06-3"
goal: "All 48 recoverable skill->memory refs point at their real memory/_dormant/ targets, RESEARCH's 2 refs point at workspace/research/open-questions.md, SEARCH's dead gs-trade-flows ref is deleted, guide.md defines a dormant lifecycle, all 37 _dormant files carry status: dormant — and lint_broken_refs passes with the Plan-04 grandfather whitelist (workspace/lint/whitelists/broken_refs.txt) emptied to header-only."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md   # this task section
  - skills/                                     # SKILL.md files with memory/{ref,sys,slang}/ refs
  - memory/meta/guide.md
  - memory/_dormant/
  - workspace/lint/whitelists/broken_refs.txt
  - workspace/lint/lint_broken_refs.py          # READ-ONLY — understand what the extended check matches
write_scope:
  - skills/*/SKILL.md                           # only files with broken memory refs (27 expected)
  - memory/meta/guide.md
  - memory/_dormant/**/*.md                     # frontmatter only
  - workspace/lint/whitelists/broken_refs.txt
acceptance_criteria:
  - "grep -rn 'memory/ref/gssso-auth\\|memory/sys/canvas-appdir\\|memory/sys/enghub-repos\\|memory/ref/forward-network\\|memory/ref/symphony-bot-framework' skills/ -> 0 matches"
  - "grep -rn 'memory/research/open-questions' skills/RESEARCH/SKILL.md -> 0; grep -c 'workspace/research/open-questions.md' skills/RESEARCH/SKILL.md -> 2"
  - "grep -n 'gs-trade-flows' skills/SEARCH/SKILL.md -> 0 matches"
  - "grep -n 'dormant' memory/meta/guide.md -> status enum + park/restore section present"
  - "grep -rL 'status: dormant' memory/_dormant --include='*.md' -> empty (all 37 carry it)"
  - "wc -l workspace/lint/whitelists/broken_refs.txt -> 0 content lines (header comment allowed)"
  - "python workspace/lint/lint_all.py --check 'broken refs' -> PASS with workspace/lint/whitelists/broken_refs.txt reduced to header-only"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "rewrite a ref ONLY after confirming memory/_dormant/<same subpath> exists on disk; anything with no counterpart is handled per the explicit list below, never guessed"
  - "skills/CANVAS/SKILL.md:32 is ALREADY correct — do not touch it; fix only :258 and :260"
  - "do not move any file out of _dormant (refs are rewritten TO _dormant; INDEX rows come in Task 8) and do not edit memory/INDEX.md"
  - "if the Plan-04 whitelist artifact is not workspace/lint/whitelists/broken_refs.txt, locate the grandfather mechanism by content in lint_broken_refs.py and empty THAT to header-only, noting the delta (NEVER edit the lint .py logic)"
context_summary: |
  A half-finished _dormant migration left 51 broken plain-text memory/ refs across 27 SKILL.md files;
  48 have byte-identical counterparts under memory/_dormant/ (ref 28, sys 4, slang 16), 2 (RESEARCH:50,
  :145) really live at workspace/research/open-questions.md, and 1 (SEARCH:75 memory/sys/gs-trade-flows.md)
  exists NOWHERE. Decided: files stay in _dormant and refs move to them (promoting files would re-break
  the 48 rewritten refs); the SEARCH dead ref is DELETED, not stubbed (a stub would fabricate GS
  trade-flow content). Plan 04 taught lint_broken_refs to see plain-text paths and _dormant, shipping a
  grandfather whitelist of these 51 so its own gate could pass — this task makes the content honest and
  burns the whitelist to header-only. guide.md and design.md never define _dormant; the lifecycle lands in guide.md only
  (design.md is Plan-05 territory).
depends_on: []
```

- [ ] **Step 1 — record the red state:** empty `workspace/lint/whitelists/broken_refs.txt` to header-only
  FIRST in the working tree (do not commit yet), run `python workspace/lint/lint_all.py --check "broken refs"`
  and paste the FAIL listing ~51 refs. Restore the whitelist content until Step 5 if the orchestrator
  requires green-between-steps; the commit at Step 6 lands fixes + emptied whitelist atomically.
- [ ] **Step 2 — enumerate and rewrite the 48:** for every match of
  `grep -rnE "memory/(ref|sys|slang)/[a-z0-9_-]+\.md" skills/ --include=SKILL.md`
  where the path does not exist but `memory/_dormant/<ref|sys|slang>/<file>` does, rewrite the path to
  `memory/_dormant/<same subpath>`. Verified anchor cases that MUST end up fixed (from
  findings-freshness §12):
  - `skills/GSSSO_AUTH/SKILL.md:91` → `memory/_dormant/ref/gssso-auth.md`
  - `skills/CANVAS/SKILL.md:258` → `memory/_dormant/ref/gssso-auth.md`; `:260` → `memory/_dormant/sys/canvas-appdir.md` (leave :32 alone)
  - `skills/ENGHUB/SKILL.md:161` → `memory/_dormant/sys/enghub-repos.md`
  - `skills/FORWARD_NETWORK/SKILL.md` (5 citations incl. :61, :185) → `memory/_dormant/ref/forward-network.md`
  - `skills/SYMPHONY/SKILL.md:42,:97` → `memory/_dormant/ref/symphony-bot-framework.md`; `:98` → `memory/_dormant/ref/gssso-auth.md`
- [ ] **Step 3 — the 3 non-recoverable refs:**
  - `skills/RESEARCH/SKILL.md:50` and `:145` → `workspace/research/open-questions.md` (real location; :50
    is the backtick one inside a table, keep its formatting).
  - `skills/SEARCH/SKILL.md:75` — delete the `memory/sys/gs-trade-flows.md` reference line (or the
    clause, if mid-sentence). Decision recorded: target exists nowhere in the tree; do not create a stub.
- [ ] **Step 4 — lifecycle:** in `memory/meta/guide.md`: (a) add `dormant` to the status enum (lines
  82-85 region); (b) add a short section after the Domains table:

  ```markdown
  ### Dormant files (`_dormant/`)

  Parked-but-load-bearing content (Slang/SecDB/sys) lives under `memory/_dormant/<domain>/`,
  keeping its domain subpath. Rules: frontmatter `status: dormant`; every dormant file referenced
  by an active skill or memory file gets an INDEX.md row (P3, Status dormant); lints scan
  `_dormant` as a source tree and validate refs INTO it (per the lint policy landed in Plan 04).
  **Park:** move `memory/<domain>/x.md` → `memory/_dormant/<domain>/x.md`, set `status: dormant`,
  rewrite inbound refs, update INDEX. **Restore:** reverse the same four steps.
  ```

  Then set `status: dormant` in all 37 `memory/_dormant/**/*.md` frontmatters (36 currently claim
  `active`), and fix `memory/_dormant/sys/secdb.md`'s malformed frontmatter (dangling
  `- sys/enghub.md` sequence item under the scalar `source:` — fold it into a proper `relates:` list
  or delete the stray line).
- [ ] **Step 5 — run to green:** whitelist emptied to header-only, `python workspace/lint/lint_all.py --check "broken refs"`
  → PASS; then FULL `python workspace/lint/lint_all.py` → PASS (the `_dormant` frontmatter edits must not
  trip validate_memory — its Plan-04 policy update governs; if a `_dormant` schema check fires on the new
  status value, that is a Plan-04 regression: STOP and return blocked with the output).
- [ ] **Step 6 — commit:** `docs(memory): _dormant lifecycle + rewrite 48 skill refs, drop 3 dead ones`
  In return `notes:` list the ~8 `_dormant` files referenced by active skills (Task 8 adds their INDEX rows).

## Task 4: python.instructions.md scoped to src/, helpers get their own small file (AW-19 + AW-14 import)

**Files:** Modify `.github/instructions/python.instructions.md`; create
`.github/instructions/python-helpers.instructions.md`. Doc/config task, TDD-exempt; import fix verified
by executing the import.

**Copilot context packet:**

```yaml
subtask_id: "wfo-06-4"
goal: "python.instructions.md attaches only to src/**/*.py, teaches the real PurgedKFoldCV import with no embedded stale class and no EDRVOL typo, drops its ~1,050t of self-duplicated data-access blocks; a new python-helpers.instructions.md carries env + file-output rules for {skills,workspace}/**/*.py."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md   # this task section
  - .github/instructions/python.instructions.md
  - src/volforecast/utils/cv.py                 # READ-ONLY — confirm PurgedKFoldCV at ~:45
write_scope:
  - .github/instructions/python.instructions.md
  - .github/instructions/python-helpers.instructions.md
acceptance_criteria:
  - "head -3 .github/instructions/python.instructions.md -> applyTo: \"src/**/*.py\" (no .ipynb branch)"
  - "grep -n 'PurgedKFold' .github/instructions/python.instructions.md -> only 'from volforecast.utils.cv import PurgedKFoldCV'; no class definition"
  - "grep -n 'EDRVOL_PERCENT' .github/instructions/python.instructions.md -> 0 matches (only ERDVOL_PERCENT_STANDARD may appear)"
  - "./vol exec python -c \"from volforecast.utils.cv import PurgedKFoldCV; print('CV-OK')\" -> OUTPUT_FILE shows CV-OK, EXIT_CODE=0 (S-B; on S-A use vol.cmd exec)"
  - "head -3 .github/instructions/python-helpers.instructions.md -> applyTo: \"{skills,workspace}/**/*.py\""
  - "wc -c .github/instructions/python.instructions.md -> <= 7000 bytes (from 12,333)"
  - "python workspace/lint/lint_all.py -> PASS"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "keep the L8-16 route pointers to memory/ref/python-{pyslang,tsdb,chunk}.md and PYTHON_MARKET_DATA — delete only the RE-EMBEDDED copies (L60-148 code blocks, L302-329 duplicated Key Rules)"
  - "ML Key Constraints stay a one-line pointer to AGENTS.md's canonical table (Plan 05 made it canonical) — do not restate the rules"
  - "purge_gap: the embedded class used 22 vs config default 5 — deleting the class removes the conflict; do not add a new purge_gap literal"
context_summary: |
  python.instructions.md (12,333 B ~= 3,083 t) attaches to ALL 350 tracked .py incl. 73 non-src files
  (21%), teaches a nonexistent import (volforecast.utils.time_series.PurgedKFold — real class is
  PurgedKFoldCV in volforecast/utils/cv.py:45), embeds a stale PurgedKFold implementation with
  purge_gap=22 (config default 5), duplicates ~1,050 t of the ref docs it routes to, and carries an
  EDRVOL_PERCENT dataset-id typo (correct: ERDVOL_PERCENT_STANDARD). Decided: applyTo narrows to
  src/**/*.py; the universal env + file-output guidance the narrowing would strip from helper scripts
  moves to a NEW small instructions file for {skills,workspace}/**/*.py whose full text is in the plan.
  This edit changes what attaches to future .py edits in this session — expected, not a drift signal.
depends_on: []
```

- [ ] **Step 1 — record the red state:** paste `sed -n '2p;46p;120p;126p' .github/instructions/python.instructions.md`
  (glob, bad import, both dataset-id lines) and
  `./vol exec python -c "from volforecast.utils.time_series import PurgedKFold"` → OUTPUT_FILE shows
  `ModuleNotFoundError` (the taught import really is dead).
- [ ] **Step 2 — edit python.instructions.md:**
  1. Frontmatter `applyTo: "**/*.{py,ipynb}"` → `applyTo: "src/**/*.py"`.
  2. Line 46: `from volforecast.utils.time_series import PurgedKFold` →
     `from volforecast.utils.cv import PurgedKFoldCV`.
  3. Delete the embedded PurgedKFold class (lines ~178-202, the block defining the stale
     `purge_gap=22` implementation).
  4. Delete the Data Access re-embedded example blocks (lines ~60-148: chunk_query/TSDB/Marquee
     code the file already routes to at L8-16) and the duplicated Key Rules block (lines ~302-329),
     keeping one pointer line each: `See memory/ref/python-tsdb.md / python-chunk.md /
     skills/PYTHON_MARKET_DATA/SKILL.md — load on demand; do not restate here.`
  5. After the deletions, `grep -n "EDRVOL_PERCENT"` the file; if any survivor remains (the typo sat at
     L126 inside the deleted region), correct it to `ERDVOL_PERCENT_STANDARD`.
- [ ] **Step 3 — create `.github/instructions/python-helpers.instructions.md`** with exactly:

  ```markdown
  ---
  applyTo: "{skills,workspace}/**/*.py"
  ---

  # Helper-Script Python Rules (skills/, workspace/)

  Scope: skill scripts, lint modules, workspace scripts/presentation. The ML/data-access
  instruction file (`python.instructions.md`) applies only to `src/**/*.py`.

  ## Environment
  - Never invoke a bare interpreter. S-B (GS Linux Coder): `./vol shell <script>` or
    `./vol exec python ...`. S-A (GS Windows): the skill's `run_task` label, or `vol.cmd exec ...`
    for the dev loop.
  - Interpreter resolution is owned by `skills/_shared/_run.sh` / `_run.cmd` — never hardcode a
    venv path in a script.

  ## File output (HARD rule)
  - ALL file writes (temp files, outputs, scripts, artifacts) go to `workspace/tmp/`. Never
    `/tmp/`, `~`, or outside the repo.
  - `workspace/tmp/` is ephemeral: delete what you create. Persisted outputs go to
    `workspace/<area>/`.

  ## Out of scope here
  - TSDB/Chunk/Marquee data-access patterns and the ML Key Constraints (AGENTS.md) are
    src/-scoped. Load `memory/ref/python-tsdb.md` only if a helper genuinely touches market data.
  ```

- [ ] **Step 4 — run to green:** all acceptance_criteria; paste sentinel OUTPUT_FILE contents for the
  import check.
- [ ] **Step 5 — commit:** `chore(ci): scope python.instructions to src, fix PurgedKFoldCV import, add helpers instruction`

## Task 5: yaml-config enum tables + canonical example regenerated from live registries (AW-20, G22–G26)

**Files:** Modify `.github/instructions/yaml-config.instructions.md`,
`workspace/configs/_CANONICAL_EXAMPLE.yaml`, `src/volforecast/registry.py` (one comment line); burn
`workspace/lint/whitelists/canonical_schema.txt` to header-only. Docs/YAML, TDD-exempt; the registry.py
edit is comment-only (no executable change — Rule 5 has nothing to test; justified here explicitly).

**Copilot context packet:**

```yaml
subtask_id: "wfo-06-5"
goal: "yaml-config.instructions.md enum/field tables and _CANONICAL_EXAMPLE.yaml are regenerated to match the LIVE registries and config.py exactly (incl. gnn, blend, implied_correlation, conditional_duan, feature_selection, cv.n_splits/embargo, sequences.source + daily_lookback features, node_attention, ale_features top_20), the canonical self-validation command loads, and the Plan-04 completeness lint passes."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md   # this task section
  - .github/instructions/yaml-config.instructions.md
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
  - src/volforecast/config.py                   # READ-ONLY source of truth (fields + defaults)
  - src/volforecast/registry.py                 # comment fix at ~:45 only
  - src/volforecast/models/                     # READ-ONLY — @register_model enumeration
  - src/volforecast/features/                   # READ-ONLY — @register_feature_layer enumeration
write_scope:
  - .github/instructions/yaml-config.instructions.md
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
  - src/volforecast/registry.py                 # the :45 comment line ONLY
  - workspace/lint/whitelists/canonical_schema.txt
acceptance_criteria:
  - "every name from grep -rhoE '@register_model\\(\"[a-z0-9_]+\"\\)' src/volforecast/models/ appears in the doc's model table, and every @register_feature_layer name in the layer table (13 layers incl. implied_correlation)"
  - "grep -c 'conditional_duan\\|feature_selection\\|embargo\\|implied_correlation\\|gnn' workspace/configs/_CANONICAL_EXAMPLE.yaml -> all five > 0"
  - "grep -n 'top_10' .github/instructions/yaml-config.instructions.md -> 0 matches; ale_features default row reads top_20"
  - "doc has a sequences.source enum row: parquet | parquet_5min | parquet_5min_multiday | daily_lookback, plus bar_interval/lookback_days rows and a daily_lookback features table"
  - "./vol exec python -c \"from volforecast.config import load_config; load_config('workspace/configs/_CANONICAL_EXAMPLE.yaml'); print('CANONICAL-OK')\" -> OUTPUT_FILE shows CANONICAL-OK, EXIT_CODE=0"
  - "python workspace/lint/lint_all.py --check 'canonical schema' -> PASS"
  - "wc -l workspace/lint/whitelists/canonical_schema.txt -> 0 content lines (header comment allowed); the canonical-schema check passes with it reduced to header-only"
  - "grep -rn 'runner.py:1509' .github/instructions/ workspace/configs/ -> 0 matches (no false failure-mode claim)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or any workspace/configs/ file EXCEPT _CANONICAL_EXAMPLE.yaml"
  - "do NOT claim gnn configs fail at runner.py:1509 — torch_geometric imports lazily; absence surfaces as an ImportError during GNN construction (AW-G22 verifier correction); the doc's gnn row notes 'requires the torch-geometric extra' only"
  - "src/volforecast/registry.py: change ONLY the misleading ~:45 comment ('torch-geometric not installed' -> 'torch missing; torch_geometric imports lazily inside gnn.py'); no executable line changes, no lazy-guard (out of scope)"
  - "if load_config is not the public loader name, use the entry point cli/experiment.py uses and note the delta in your return"
  - "the canonical keeps its existing structure/comment style — new sections are appended in matching style, nothing existing is deleted"
context_summary: |
  yaml-config.instructions.md (applyTo workspace/configs/**) presents 'Valid Enum Values' tables that
  omit implied_correlation (1 of 13 registered layers), ~10 registered models (blend, gnn, har_cj_iv_*,
  sharq_cj_iv_*, ridge/lasso_har_iv_ratevol), conditional_duan (config.py:463), feature_selection,
  cv.n_splits (config.py:178), cv.embargo (:183), the entire sequences.source enum (:314-333) and
  daily_lookback feature vocabulary, gnn's node_attention output (gnn.py:626), and documents
  ale_features default as top_10 vs code top_20 (config.py:237, doc line 176 vs its own example at
  :163). _CANONICAL_EXAMPLE.yaml (19,438 B) violates its own Maintenance Rule: conditional_duan, gnn,
  implied_correlation, embargo all absent. Decided: regenerate FROM the live code (never from this plan's
  numbers — code wins on any discrepancy); the Plan-04 completeness lint is the permanent drift guard.
  Unknown-key errors are hard TypeErrors (CVConfig/SequenceConfig **-unpack), so these gaps are
  load-relevant, not cosmetic.
depends_on: []
```

- [ ] **Step 1 — record the red state:** paste
  `python workspace/lint/lint_all.py --check "canonical schema"` (expected: FAIL or the Plan-04-recorded
  grandfather note) and `grep -c "implied_correlation\|conditional_duan\|embargo" workspace/configs/_CANONICAL_EXAMPLE.yaml` → 0.
- [ ] **Step 2 — enumerate the live schema (code is the source of truth):**
  `grep -rhoE '@register_model\("[a-z0-9_]+"\)' src/volforecast/models/`,
  `grep -rhoE '@register_feature_layer\("[a-z0-9_]+"\)' src/volforecast/features/`,
  and read `src/volforecast/config.py` for: `conditional_duan` (~:463 — copy every field + default),
  `CVConfig.n_splits` (~:178), `CVConfig.embargo` (~:183), `SequenceConfig.source/bar_interval/lookback_days`
  (~:314-333), `ale_features` default (~:237). Paste the enumerations into your return `verification:`.
- [ ] **Step 3 — update the instruction doc tables:** add every missing registered layer/model name;
  add Optional Fields rows for `conditional_duan`, `feature_selection`, `blend` (model + section),
  `cv.n_splits`, `cv.embargo` (note: "valid; used by no trial config to date"); add the
  `sequences.source` enum table + `bar_interval`/`lookback_days` rows + a second sequences.features
  table for daily_lookback panel columns
  (`log_rv_d, log_rv_w, log_rv_m, signed_return_d, abs_ret_d, log_rs_negative_d, log_jump_d, log_bpv_d, log_cont_d`
  — cross-check against `trial_068_gnn_standalone.yaml:96-105` and the SequenceConfig code); add
  `node_attention` to the gnn outputs table with the note "gnn requires the torch-geometric extra";
  change the ale_features default cell `"top_10"` → `"top_20"` (line ~176).
- [ ] **Step 4 — extend `_CANONICAL_EXAMPLE.yaml`** (appended in the file's existing commented style;
  defaults copied from config.py at execution time — sanctioned deferral, code wins):

  ```yaml
  # ---- conditional_duan (config.py ~:463; heteroscedastic Duan correction, trial-068 family) ----
  # conditional_duan:
  #   <every field defined at config.py ~:463, with its code default and a one-line comment>

  # ---- cv extras (CVConfig, config.py ~:178/:183) ----
  # cv:
  #   n_splits: 5        # already documented; shown here for completeness
  #   embargo: 0         # valid; no trial config uses it yet

  # ---- graph model (models/gnn.py; requires the torch-geometric extra) ----
  # model:
  #   name: gnn
  # feature_stack:
  #   outputs: [prediction, node_attention]

  # ---- blend (trial-072 family) ----
  # <the blend model line + its section, fields from config.py>

  # ---- implied_correlation feature layer (features/implied_correlation.py:66) ----
  # layers:
  #   - implied_correlation

  # ---- sequences.source enum (SequenceConfig, config.py ~:314-333) ----
  # sequences:
  #   source: parquet_5min   # parquet | parquet_5min | parquet_5min_multiday | daily_lookback
  #   bar_interval: <code default>
  #   lookback_days: <code default>
  ```

- [ ] **Step 5 — registry.py comment:** at `src/volforecast/registry.py` ~:45, replace the misleading
  `# torch-geometric not installed` comment with
  `# torch missing (torch_geometric is imported lazily inside gnn.py — its absence surfaces later, at GNN construction)`.
  Comment-only; diff must show no executable-line change.
- [ ] **Step 6 — burn the grandfather whitelist:** empty `workspace/lint/whitelists/canonical_schema.txt`
  to header-only (0 data lines). Plan 04 grandfathered the then-missing keys (gnn, conditional_duan,
  implied_correlation, embargo) into this file so its always-strict completeness check could pass; Steps
  3–4 have now added them for real, so the whitelist is no longer needed. NEVER edit the lint `.py` logic.
- [ ] **Step 7 — run to green:** all acceptance_criteria; paste the CANONICAL-OK sentinel and
  `python workspace/lint/lint_all.py --check "canonical schema"` PASS with the whitelist emptied.
- [ ] **Step 8 — commit:** `chore(ci): regenerate yaml-config enums + canonical example from live registries`

## Task 6: market-data refs distilled to the US universe (AW-29)

**Files:** Rewrite `memory/ref/python-tsdb.md`, `memory/ref/python-chunk.md`; create
`memory/ref/python-tsdb-fields.md`. Doc task, TDD-exempt.

**Copilot context packet:**

```yaml
subtask_id: "wfo-06-6"
goal: "python-tsdb.md and python-chunk.md are <=250 lines each with US-universe (SPY/E-mini, America/New_York, eqpad_) examples, the ~185-row TSDB field dictionary moves to a new P2 memory/ref/python-tsdb-fields.md, and validate_memory's ref soft-cap warnings for both files disappear."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md   # this task section
  - memory/ref/python-tsdb.md
  - memory/ref/python-chunk.md
  - memory/meta/guide.md                        # frontmatter schema for the new file
  - memory/research/data-access.md              # READ-ONLY — the project universe (34 US symbols + E-mini)
write_scope:
  - memory/ref/python-tsdb.md
  - memory/ref/python-chunk.md
  - memory/ref/python-tsdb-fields.md
acceptance_criteria:
  - "wc -l memory/ref/python-tsdb.md memory/ref/python-chunk.md -> both <= 250"
  - "grep -in 'brazil\\|PETR4\\|DAPQ40\\|WINJ25\\|Sao_Paulo' memory/ref/python-tsdb.md memory/ref/python-chunk.md -> 0 matches"
  - "grep -c 'America/New_York' memory/ref/python-chunk.md -> >= 1"
  - "grep -n 'ERDVOL_PERCENT_STANDARD' memory/ref/python-tsdb.md -> the dataset id appears in its correct form only (EDRVOL_PERCENT -> 0 matches)"
  - "test -f memory/ref/python-tsdb-fields.md and grep -c '|' memory/ref/python-tsdb-fields.md -> >= 180 (field table moved intact)"
  - "python workspace/lint/validate_memory.py -> PASS with no 'exceeds ref soft cap' WARN for python-tsdb.md or python-chunk.md"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "DISTILL, don't delete: every API call pattern, function signature, gotcha, and the pyslang.start() bootstrap note survive; only the field dictionary moves and Brazil-desk examples are replaced 1:1 with US equivalents (symbols from research/data-access.md)"
  - "python-tsdb-fields.md frontmatter follows meta/guide.md schema (domain ref, status: active) with a relates: link back to python-tsdb.md; python-tsdb.md gains a one-line pointer to it"
  - "do not edit memory/INDEX.md — report the new file's byte size and intended row (P2, load trigger 'TSDB field/dataset lookup') in your return notes for Task 8"
context_summary: |
  python.instructions.md mandates python-tsdb.md before market-data work: 514 lines / 22,838 B
  (~5,709 t) against a ref cap of 250 lines, roughly half of it a ~185-row field dictionary, with all
  examples Brazilian (_lib_eq1d_brazil_tsdb_fns, DAPQ40, PETR4.SA) for a project whose universe is 34 US
  symbols + E-mini. python-chunk.md is 333 lines with America/Sao_Paulo and WINJ25. Decided: both
  distilled to <=250 lines with US examples; the field dictionary becomes a P2 on-demand companion
  (loaded only on field lookup), expected saving ~4-5k tokens per market-data task. Task 4 (parallel)
  edits python.instructions.md — its pointers keep the same filenames, so no coordination is needed
  beyond both landing this plan.
depends_on: []
```

- [ ] **Step 1 — record the red state:** paste `wc -l` of both files and the two
  `WARN ... exceeds ref soft cap of 250` lines from `python workspace/lint/validate_memory.py`.
- [ ] **Step 2 — split python-tsdb.md:** move the field-dictionary table (~185 rows) verbatim into new
  `memory/ref/python-tsdb-fields.md`:

  ```markdown
  ---
  <frontmatter per meta/guide.md: created: <today>, updated: <today>, status: active, relates: [python-tsdb]>
  ---
  # TSDB Field Dictionary (P2 — load on field/dataset lookup only)

  Companion to `python-tsdb.md` (API patterns live there). This file is the full field/dataset
  reference; load it only when resolving a specific field or dataset id.

  <the moved table, verbatim>
  ```

  In python-tsdb.md, replace the table with:
  `Full field/dataset dictionary: memory/ref/python-tsdb-fields.md (P2 — load on lookup only).`
- [ ] **Step 3 — re-example both files for the US universe:** replace `_lib_eq1d_brazil_tsdb_fns`-based
  examples with the project's actual fns/library path as used in `src/volforecast/data/tsdb.py`
  (read it for the real call pattern — code wins), `PETR4.SA`/`DAPQ40` → `SPY` / E-mini symbols from
  `research/data-access.md`, `America/Sao_Paulo` → `America/New_York`, `WINJ25` → the E-mini contract
  form data-access.md uses. Ensure the dataset id appears as `ERDVOL_PERCENT_STANDARD` (never
  `EDRVOL_PERCENT`). Trim narrative until both files are ≤250 lines; keep every distinct API pattern.
- [ ] **Step 4 — run to green:** all acceptance_criteria; paste outputs. Report byte sizes of all three
  files in `notes:` for Task 8.
- [ ] **Step 5 — commit:** `docs(memory): distill tsdb/chunk refs to US universe, split field dictionary to P2`

## Task 7: P1 workspace docs stop lying (AW-G15, G18, G19, G20-residue)

**Files:** Modify `workspace/docs/data-audit.md`, `workspace/docs/user-manual.md`. Doc task, TDD-exempt.

**Copilot context packet:**

```yaml
subtask_id: "wfo-06-7"
goal: "data-audit.md's appendix matches the implemented tsdb.py fetchers and carries reproducible provenance; user-manual.md declares execution surfaces, uses ${ROOT}-relative paths, and documents present/kvar/cache-* and the plans/presentation trees."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md   # this task section
  - workspace/docs/data-audit.md
  - workspace/docs/user-manual.md
  - src/volforecast/data/tsdb.py                # READ-ONLY — confirm the four fetchers + module naming
  - vol                                          # READ-ONLY — confirm audit/present/kvar/cache-* arms
write_scope:
  - workspace/docs/data-audit.md
  - workspace/docs/user-manual.md
acceptance_criteria:
  - "grep -n 'TODO' workspace/docs/data-audit.md -> no TODO rows for fetch_daily_ohlcv/fetch_treasury_yields/fetch_fx_rates/fetch_commodity_prices"
  - "grep -n 'until the volforecast.data wrappers are implemented' workspace/docs/data-audit.md -> 0 matches"
  - "grep -n 'sp500_data_probe' workspace/docs/data-audit.md -> 0 matches; the provenance line names a reproducible command"
  - "grep -n '/home/developer' workspace/docs/user-manual.md -> 0 matches"
  - "grep -cn 'vol present\\|kvar\\|cache-status\\|cache-clear' workspace/docs/user-manual.md -> all four present"
  - "grep -n 'workspace/plans\\|workspace/presentation' workspace/docs/user-manual.md -> both trees appear in the layout/visibility table"
  - "grep -n 'S-A\\|S-B\\|vol.cmd' workspace/docs/user-manual.md -> the surfaces note exists and names vol.cmd for Windows"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "drop the unreproducible '147/206 checks passed' figure rather than restating it (AW-G18: the probe script is deleted; do not fabricate a rerun)"
  - "surface wording must match AGENTS.md's 'Supported Execution Surfaces' section as rewritten by Plan 02 — quote it, don't re-derive; if it differs from S-A/S-B as summarized here, STOP and return blocked with the diff"
  - "do not edit memory/INDEX.md; report both files' final byte sizes in notes (both are P1 rows headed for P2 demotion in Task 8 — content still must be honest)"
context_summary: |
  data-audit.md:937-940 marks tsdb.py's fetch_daily_ohlcv/treasury/fx/commodity fetchers TODO and :946
  tells agents to hand-write inline query snippets 'until the wrappers are implemented' — but all four
  exist (tsdb.py:142/:210/:256/:301) and the doc's own Layer-4 table calls them Implemented (AW-G15).
  Its only provenance (:5) cites a deleted workspace/tmp probe script with an unverifiable 147/206 pass
  count (AW-G18). user-manual.md hardcodes /home/developer paths and documents a bash/nix-only loop with
  no surface note (AW-G19), and neither P1 doc mentions vol present/kvar/cache-* or the
  workspace/plans + workspace/presentation trees (AW-G20 residue; vol-cli.md's half landed in Plan 03).
  Plan 03 shipped vol.cmd for the S-A dev loop — the manual may now reference it as real.
depends_on: []
```

- [ ] **Step 1 — record the red state:** paste `sed -n '5p;937,946p' workspace/docs/data-audit.md` and
  `grep -n "/home/developer" workspace/docs/user-manual.md` and
  `grep -c "present\|kvar" workspace/docs/user-manual.md`.
- [ ] **Step 2 — data-audit.md:** flip appendix rows ~937-940 `TODO` → `Implemented` (verify each
  function exists in `src/volforecast/data/tsdb.py` first: :142/:210/:256/:301 regions); delete the
  :946 "use the direct query snippets … until the wrappers are implemented" fallback sentence; reconcile
  the iv-module naming (grep the doc for `iv_ingest.py` vs `marquee.py`, check which file exists under
  `src/volforecast/data/`, and make the doc name the real one); replace line 5's provenance with:
  `**Last validated:** 2026-05-18 (historical; original probe script deleted per workspace/tmp policy). Revalidate with: ./vol audit (S-B) — record date + output summary here on each rerun.`
- [ ] **Step 3 — user-manual.md:** (a) add near the top an "Execution surfaces" note quoting the
  AGENTS.md surface contract: `./vol` = S-B (GS Linux Coder, nix+uv) only; on S-A (GS Windows desktop)
  use `vol.cmd` (dev-loop subset: test/test-all/testlf/lint/fmt/typecheck/exec/bg/jobs) or the VS Code
  tasks; (b) replace the :405-406 `/home/developer/ml-vol-estimator/...` example output with
  `${ROOT}/workspace/configs/...`; (c) add command rows for `vol present`, `vol kvar`,
  `vol cache-status`, `vol cache-clear` (one-line purposes taken from the `vol` help heredoc); (d) add
  `workspace/plans/` ("plan-suite + /plan output tree — read-only for subagents") and
  `workspace/presentation/` ("`vol present` generator") rows to the layout table.
- [ ] **Step 4 — run to green:** all acceptance_criteria; paste outputs; report byte sizes in `notes:`.
- [ ] **Step 5 — commit:** `docs(workspace): data-audit appendix honesty + user-manual surfaces and vol coverage`

## Task 8: INDEX.md regenerated from measurement; budget enforced; boot re-measured (AW-15, AW-48-columns, closure)

**Files:** Rewrite `memory/INDEX.md`; burn `workspace/lint/whitelists/budget_grandfather.txt` to
header-only. The red→green is the budget lint itself (Plan 04's budget check is already strict and
6-column-tolerant — its `.py` logic is never edited here).

**Copilot context packet:**

```yaml
subtask_id: "wfo-06-8"
goal: "memory/INDEX.md's every row carries measured bytes/4 ~Tokens plus Status/Updated columns, dead rows are gone, P0+P1 is demoted under 50k measured tokens, dormant + new-file rows exist — and lint_memory_priority.py passes with workspace/lint/whitelists/budget_grandfather.txt burned to header-only; boot chain re-measured and recorded."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md   # this task section
  - memory/INDEX.md
  - workspace/lint/whitelists/budget_grandfather.txt
  - workspace/lint/lint_memory_priority.py      # READ-ONLY — the always-strict budget check (never edited)
  - workspace/lint/validate_memory.py           # READ-ONLY — the second budget check
  - memory/                                     # READ-ONLY except INDEX.md — byte measurement
  - workspace/docs/                             # READ-ONLY — P1 file measurement
  - workspace/research/                          # READ-ONLY — P1 file measurement
write_scope:
  - memory/INDEX.md
  - workspace/lint/whitelists/budget_grandfather.txt
acceptance_criteria:
  - "python workspace/lint/lint_memory_priority.py -> PASS with workspace/lint/whitelists/budget_grandfather.txt reduced to header-only (0 data lines): P0 <= 800 measured tokens, P0+P1 <= 50,000 measured tokens"
  - "python workspace/lint/validate_memory.py -> PASS"
  - "python workspace/lint/lint_memory_index_completeness.py -> PASS (no phantom INDEX entries, no unlisted files)"
  - "grep -n 'architecture-audit' memory/INDEX.md -> 0 matches (dead row deleted)"
  - "INDEX header row is: File | Priority | ~Tokens | Status | Updated | Load Trigger, and every ~Tokens cell equals round(bytes/4) of the file it names (spot-check 5 rows incl. lgbm-pooled-lessons)"
  - "grep -n 'lgbm-pooled-lessons\\|data-audit\\|user-manual' memory/INDEX.md -> all carry P2"
  - "grep -n 'python-tsdb-fields' memory/INDEX.md -> 1 row, P2"
  - "row for research continuity points at workspace/research/research-journal.md (not the memory pointer card)"
  - "python workspace/lint/lint_all.py -> full PASS"
  - "boot measurement pasted: sum of bytes/4 over .github/copilot-instructions.md, AGENTS.md, memory/person/user.md, memory/research/project-state.md, memory/INDEX.md — before (from the Plan-05 MR figure) and after; after <= ~7,500 directional"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; trials.yaml CONTENT untouched — only its INDEX row may be re-tiered"
  - "measure, never estimate: every ~Tokens value comes from an actual byte count taken AFTER Tasks 1-7 merged; run the measurement via ./vol exec (S-B) or vol.cmd exec (S-A)"
  - "demotion order is fixed (below); stop demoting once measured P0+P1 <= 50k; record each demotion + justification in the row's Load Trigger or the MR description"
  - "NEVER edit lint_memory_priority.py's .py logic — its budget check is already strict and its _INDEX_ROW regex already tolerates the six-column INDEX (Plan 04). Enforcement = burning workspace/lint/whitelists/budget_grandfather.txt to header-only; if that whitelist path differs, locate the Plan-04 grandfather mechanism by content and empty THAT, noting the delta"
  - "a result dramatically under 50k means something load-bearing was deleted or mismeasured — investigate before accepting (overview sanity rule)"
context_summary: |
  memory/INDEX.md's hand-typed ~Tokens column is wrong up to 10.6x (lgbm-pooled-lessons: claimed 890,
  measured ~9,453), lists dead paths, and P0+P1 measures ~79.8k tokens (excl. trials.yaml) against a 50k
  cap. Plan 04 rewrote lint_memory_priority.py to measure bytes/4, shipping its always-strict budget
  check kept green by workspace/lint/whitelists/budget_grandfather.txt (grandfathered over-budget); this
  task makes content pass and burns that whitelist to header-only. All
  content tasks (1-7) have landed and reported their final byte sizes in their return notes — use them
  as cross-checks, but re-measure everything yourself. This is the plan's last task and the sole
  INDEX.md writer.
depends_on: ["wfo-06-1", "wfo-06-2", "wfo-06-3", "wfo-06-4", "wfo-06-5", "wfo-06-6", "wfo-06-7"]
```

- [ ] **Step 1 — record the red state:** empty `workspace/lint/whitelists/budget_grandfather.txt` to
  header-only in the working tree (do not commit yet), run `python workspace/lint/lint_memory_priority.py`,
  and paste the FAIL (un-demoted content over budget with the grandfather entries removed). This is the
  failing test for this task.
- [ ] **Step 2 — measure everything:** for every file INDEX lists (and the new
  `memory/ref/python-tsdb-fields.md`), take bytes and compute `round(bytes/4)`. One-liner (S-B):
  `./vol exec python -c "import os,sys; [print(p, os.path.getsize(p), round(os.path.getsize(p)/4)) for p in sys.argv[1:]]" <paths>`
  (S-A: same via `vol.cmd exec`). Paste the table.
- [ ] **Step 3 — rewrite INDEX.md:**
  1. Header per domain table becomes `| File | Priority | ~Tokens | Status | Updated | Load Trigger |`.
     `Status`/`Updated` come from each file's frontmatter (`—` where a file has none, e.g. trials.yaml).
  2. Every `~Tokens` cell = the Step-2 measurement.
  3. Delete the dead row `workspace/docs/architecture-audit.md` (~row :69 — file exists nowhere). For
     the `vol-learning-framework-design.md` row (~:114): the file exists at
     `workspace/learning/vol-learning-framework-design.md` — repoint the row's path there (verify on
     disk first; if absent there too, delete the row).
  4. Repoint the research-continuity row (~:39) to `workspace/research/research-journal.md`; add a P3
     row for the `memory/research/research-journal.md` pointer card (Status active, trigger "pointer
     only"). Mark `layer01-gap-analysis.md`'s row Status `archived` and change its Load Trigger to
     `historical only — gaps all implemented (banner :13)`.
  5. **Demote to P2, in this order, until measured P0+P1 ≤ 50,000:**
     (a) `research/lgbm-pooled-lessons.md` (~9,453 t; also reachability-orphaned),
     (b) `workspace/docs/data-audit.md` (~9,713 t pre-Task-7),
     (c) `workspace/docs/user-manual.md` (~6,451 t),
     (d) `workspace/research/trials.yaml` (~31,758 t; loaded on-demand by the experiment loop anyway —
     INDEX row re-tiered, file untouched),
     (e) `slang/lint-edit.md` (~4,071 t), (f) `slang/best-practices.md` (~3,176 t),
     (g) `slang/formatting.md` (~2,029 t) — justification for e-g: Slang work is parked per INDEX.md:9.
     With Tasks 1/6 shrinkage plus (a)-(d), the expected landing point is ~40-44k; demotions (e)-(g)
     are the reserve. Record the stop-point.
  6. Add P3 `Status dormant` rows for the skill-referenced `_dormant` files from Task 3's return notes
     (~8 files), and the P2 row for `memory/ref/python-tsdb-fields.md` (trigger: "TSDB field/dataset
     lookup"). Update the INDEX.md:9 dormant note to end with `Lifecycle: meta/guide.md §Dormant files.`
- [ ] **Step 4 — run to green:** `python workspace/lint/lint_memory_priority.py` → PASS with
  `workspace/lint/whitelists/budget_grandfather.txt` reduced to header-only; `validate_memory.py`,
  `lint_memory_index_completeness.py`, then full `python workspace/lint/lint_all.py` → PASS. Do not edit
  the lint: its `_INDEX_ROW` regex already tolerates the six-column INDEX (Plan 04); if it chokes, that is
  a Plan-04 regression — STOP and return blocked with the output.
- [ ] **Step 5 — boot re-measurement:** run the Step-2 one-liner over the 5 boot files
  (`.github/copilot-instructions.md AGENTS.md memory/person/user.md memory/research/project-state.md memory/INDEX.md`),
  paste before (Plan-05 MR figure) vs after, and put both numbers in this MR's description. After ≤
  ~7,500 t is directional — do not delete content to hit it; if materially above, note why.
- [ ] **Step 6 — commit:** `docs(memory): INDEX regenerated from measured bytes, demotions under 50k, budget lint enforced`

---

## 4. Configs / experiments

This plan ships **no runnable experiments** — nothing here is launched, and `trials.yaml` is untouched.
The single YAML artifact is the regenerated `workspace/configs/_CANONICAL_EXAMPLE.yaml` (Task 5), a
schema reference that is loaded, never run:

- **Hypothesis:** the canonical example and the yaml-config enum tables have drifted from the live
  registries (verified: conditional_duan/gnn/implied_correlation/embargo all grep=0 in the canonical;
  13th layer + ~10 models missing from the doc).
- **Expected outcome (prior):** after regeneration, the canonical loads through the real config parser
  and the Plan-04 completeness lint passes with zero omissions; agents editing `workspace/configs/**`
  stop "correcting" valid keys.
- **Decision rule:** if any registered name or config.py field cannot be represented in the canonical
  without breaking its load (e.g. mutually exclusive sections), represent it as a commented block (the
  file's existing convention) and note it; if the completeness lint and the loader disagree, the loader
  (code) wins and the lint finding is escalated as a Plan-04 defect — do not weaken the lint.
- **Validation command (printed here, run as acceptance):**
  `./vol exec python -c "from volforecast.config import load_config; load_config('workspace/configs/_CANONICAL_EXAMPLE.yaml'); print('CANONICAL-OK')"`

## 5. Orchestrator prompt

```
/execute Implement Plan 06 (Memory & instruction-file honesty) from workspace/plans/copilot-workflow-overhaul/plan-06-memory-honesty.md

Precondition check: Plan 05 merged; `python workspace/lint/lint_all.py` -> full PASS on this machine;
the Plan-05 MR description contains the boot-token before/after figures (needed by Task 8). No research
/execute session is live.
Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1 (parallel, max 6): wfo-06-1, wfo-06-2, wfo-06-3, wfo-06-4, wfo-06-5, wfo-06-6
  Wave 2: wfo-06-7
  Wave 3: wfo-06-8            # depends on ALL of 1-7; sole memory/INDEX.md writer
Each subagent: docs/config are TDD-exempt but every task shows its recorded red state first, then green
(the lint or grep it owns); terminal isolation (./vol exec / vol.cmd exec, isBackground=true, read the
OUTPUT_FILE= path, never trust the buffer) + kill_terminal cleanup EXIT GATE; return the 00-overview
§5.2 return contract verbatim.
Retry a blocked/partial subagent once with a refined packet (add diagnostics from attempt 1), then
escalate to the user with evidence from both attempts.
Integration verification (orchestrator, after all tasks):
  python workspace/lint/lint_all.py                      -> full PASS
  python workspace/lint/lint_memory_priority.py          -> PASS with budget_grandfather.txt burned to header-only
  ./vol exec python -c "from volforecast.config import load_config; load_config('workspace/configs/_CANONICAL_EXAMPLE.yaml'); print('CANONICAL-OK')"  -> CANONICAL-OK
  grep -rnE "memory/(ref|sys|slang)/[a-z0-9_-]+\.md" skills/ --include=SKILL.md  -> every hit resolves on disk
Paste the Task-8 boot before/after measurement into the MR description.
Branch chore/wf-overhaul-06-memory-honesty off master; rebase onto origin/master before push; MR-only;
never git add -A. Update workspace/research/weekly-progress.md (Shipped section, one line).
Do NOT start Plan 07.
```

## 6. Acceptance gate → Plan 07

Verbatim from 00-overview §2, all four must hold before Plan 07 starts:

1. **Memory-budget lint passes on measured bytes (P0+P1 ≤ 50k real tokens)** —
   `python workspace/lint/lint_memory_priority.py` → PASS with `workspace/lint/whitelists/budget_grandfather.txt` reduced to header-only (0 data lines).
2. **Broken-refs lint (now seeing plain-text paths + `_dormant`) passes** —
   `python workspace/lint/lint_all.py --check "broken refs"` → PASS with `workspace/lint/whitelists/broken_refs.txt` reduced to header-only.
3. **`_CANONICAL_EXAMPLE.yaml` self-validation command loads** — the §4 command prints `CANONICAL-OK`,
   `EXIT_CODE=0`.
4. **Boot re-measured (target ≤ ~7,500 t, directional)** — before/after bytes/4 figures recorded in the
   MR description.

Plus the standing gate: full `python workspace/lint/lint_all.py` PASS on the executing surface.

**What Plan 07 consumes from this plan:** an INDEX.md with Status/Updated columns whose rows are all
live (so /research and the prompt-INDEX work cite real files); `research.prompt.md` already repointed
(Plan 07 must not re-touch that line); the honest instruction-file pair
(`python.instructions.md` src-scoped + `python-helpers.instructions.md`) so prompt/skill hygiene edits
in `{skills,workspace}/**/*.py` no longer drag 3,083 t of ML rules into context; and the burned
broken-refs whitelist (`workspace/lint/whitelists/broken_refs.txt`) as the regression net under Plan 07's skill-file edits.

**AW-IDs disposed by this plan (coverage-matrix rows):** AW-12, AW-15, AW-16, AW-17, AW-19, AW-20,
AW-29, AW-34, AW-48, AW-G15, AW-G18, AW-G19, AW-G20 (residue; vol-cli half landed in Plan 03), AW-G22
(doc + comment; runtime lazy-guard consciously out of scope per the verifier's do-NOT), AW-G23, AW-G24,
AW-G25, AW-G26 — 18 findings, matching the overview's Plan-06 total.
