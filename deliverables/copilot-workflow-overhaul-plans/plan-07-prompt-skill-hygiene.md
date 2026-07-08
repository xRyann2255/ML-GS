# Plan 07 — Prompt & Skill Hygiene (S5)

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §9.
> Dispatch each task as a subagent with the context packet provided. Max 5 concurrent subagents.
> TDD is a hard gate (`.github/copilot-instructions.md` Rule 5) — this plan is docs/config throughout and therefore Rule-5-exempt, EXCEPT the lint-script extensions in Tasks 6 and 12, which carry planted-violation red-then-green evidence. Requires Plans 01–06 merged (standing lint gate green since Plan 04; Gate D compute evidence from Plan 03 makes every acceptance command below runnable on S-A and S-B).

**Goal:** The prompt layer becomes a discoverable, dispatching-only surface and the skill layer a lint-clean roster: `.github/prompts/INDEX.md` exists and is bijective with the directory, every prompt body instructs `read_file`, model pins survive only where sanctioned, `/fix-it` resolves live, the 48-vs-54 skill roster is reconciled, and the ~27KB Task-Based-Execution boilerplate collapses to pointer blocks — killing AW-G3, 11, 18, 23, 25, 30, 31, 37, 43, 45, 47, 50, 51, 52.

**Architecture:** Everything plugs into seams that already exist. `lint_prompts.py` and `lint_model_pins.py` (shipped by Plan 04 with already-strict logic, kept green by external grandfather whitelist FILES under `workspace/lint/whitelists/`) are the enforcement rails — this plan makes content conform, then burns those whitelist files (`model_pins.txt`, `prompts.txt`) to header-only so the rails go strict; the two `SANCTIONED_SITES` (`policy/subagent_protocol.md`, `.github/copilot-instructions.md`) stay exempt structurally, not via whitelist. The thin-dispatcher rewrite copies the two in-repo exemplar prompts (`data-audit.prompt.md`, `git-commit.prompt.md`, confirmed single-link dispatchers by the audit). The boilerplate collapse points at `memory/ref/vscode-tasks.md`, already the canonical task protocol (rule E3 fixed by Plan 03). The roster reconciliation extends (never rewrites) `lint_skills_structure.py` / `validate_skills.py` per the do-not-rebuild inventory.

**Tech stack:** No new dependencies. Lint extensions are stdlib-only Python matching the existing `workspace/lint/` suite.

**Research grounding:** The 2026-07 84-finding audit (sole finding source), findings AW-G3/11/18/23/25/30/31/37/43/45/47/50/51/52, re-verified live 2026-07-07 (`findings-freshness.md`: all probes STILL-PRESENT). Expected-outcome priors (00-overview §4): model-pin literals 76 display-name + 2 slug hits → **0 outside `lint_model_pins.EXPECTED_MODEL` and retained prompt frontmatter**; Task-Based-Execution boilerplate 27,036 B ≈ 6,759 t across 34 SKILL.mds → ≤ ~7 KB of 4-line pointer blocks (saving ~5k tokens of drift surface); prompt registry 0 → 34-row bijection; dead routing pointers 5 → 0; skill-roster authorities 3-way disagreement → all agree at 54 (48 dirs + 6 guide-only). **Calibration warning (00-overview §4 sanity rule):** byte/token savings are bytes/4 and directional — a measured saving far better than the prior means load-bearing content (skill-specific args schemas, endpoint rows agents actually use) was deleted; investigate before celebrating.

---

## 1. Global constraints

All of 00-overview §5 (packet schema union, return contract, 9 HARD rules, git/MR conventions) applies to every task. Plan-specific hard rules:

1. **Bare backtick paths in prompt bodies are PRESERVED — never converted to Markdown links.** This is the deliberate, lint-enforced dispatcher pattern (do-not-rebuild #6; `implementation_boundary.md:64-70`; enforced by `lint_vscode_md.py` rules `file-ref-in-prompt` / `prompt-link-in-prompt`). The AW-11 fix is a prefixed instruction line, not links.
2. **Prompt frontmatter `model:` values that are kept must be the exact display name `Claude Opus 4.6`** (matching `lint_model_pins.EXPECTED_MODEL`) — never the API slug `claude-opus-4-6`, never capability prose (AW-G4/G5 do-NOTs). Capability/fallback language lives only in prose rules (Plan 05's territory — do not touch it here).
3. **Never rewrite the 14 pre-existing lint scripts' logic** (do-not-rebuild #7). Task 6 APPENDS check functions to two linters; Task 12 burns external grandfather whitelist FILES (`workspace/lint/whitelists/*.txt`) to header-only — neither edits existing `.py` check logic.
4. The 5 ACTIVE research plans in `workspace/plans/` are read-only; never touch `trials.yaml`, `workspace/configs/`, `./vol`, `vol.cmd`, or `skills/_shared/_run.{sh,cmd}`.
5. **The boilerplate collapse (Task 7) must preserve Plan 03's args-file contract text** in every SKILL.md it touches: fixed `workspace/tmp/<name>_args.json`, `run_id` inside the JSON body constrained to `[a-z0-9-]+`, the last-writer-wins caveat where Plan 03 added it, and `run_task` (never `create_and_run_task`).
6. **Self-modification / drift check (standing):** `AGENTS.md` is always-on and was rewritten by Plans 02 and 05. Every packet quotes the text it expects as-of-execution; verify every cited path:line against the live tree before editing (line numbers below are from the 2026-07-07 byte-identical mirror and WILL have shifted) — locate by content; if the quoted rule/claim no longer exists at all, STOP and return `blocked` with the diff.
7. One plan = one MR = one branch: `chore/wf-overhaul-07-prompt-skill-hygiene` off `master`, rebase on `origin/master` before push, never `git add -A`, deny-listed paths never staged.
8. Every task's acceptance ends with the standing gate: `python workspace/lint/lint_all.py` full PASS (on S-B via `./vol exec python workspace/lint/lint_all.py`; on S-A via the `lint-workspace` task or `vol.cmd exec python workspace/lint/lint_all.py` — read the sentinel `OUTPUT_FILE=`, require `EXIT_CODE=0`).

---

## 2. File map

| Action | Path | Responsibility |
|---|---|---|
| Rename | `.github/prompts/fix it.prompt.md` → `.github/prompts/fix-it.prompt.md` | AW-37: kill the spaced basename / built-in `/fix` collision |
| Modify | `workflows/fix.md` | AW-37: trigger line `/fix it` → `/fix-it` |
| Modify | `workflows/housekeep.md` | AW-37: drop the dangling `/housekeep` trigger (keep `/lint-workspace`) |
| Create | `.github/prompts/INDEX.md` | AW-43: 34-row prompt registry, bijective with the directory |
| Modify | `AGENTS.md` | AW-11/43: rewrite the false auto-injection claim; link the INDEX |
| Modify | 30 × `.github/prompts/*.prompt.md` (all except backtest, feature, research, gsvivs-audit) | AW-11: `read_file` preamble on verbless bodies; AW-23: drop pins on the 16 mechanical prompts; AW-50: `status.prompt.md` package path |
| Modify | `.github/prompts/{backtest,feature,research}.prompt.md` | AW-25: thin dispatchers; AW-50: `feature.prompt.md` package path |
| Modify | `.github/prompts/gsvivs-audit.prompt.md` | AW-51: replaced by 15-line parameterized stub |
| Create | `workspace/research/gsvivs-audit-2026-06.md` | AW-51: relocated one-shot analysis record |
| Modify | `skills/design.md` | AW-25: "prompts are dispatchers" rule; AW-18: guide-only skill variant sanctioned in §3 |
| Modify | `skills/INDEX.md` | AW-18: add the 6 guide-only skill rows (roster = 54) |
| Modify | `workspace/lint/lint_skills_structure.py`, `workspace/lint/validate_skills.py` | AW-18: teach both linters to see flat guide skills (append E9/E10 + guide-skill validation) |
| Modify | `policy/implementation_boundary.md` | AW-18: skill-roster row states "54 (48 dirs + 6 guide-only)" explicitly |
| Delete | `skills/ssp_helpers.py` | AW-18: orphan script, 0 tracked references |
| Modify | ~34 × `skills/*/SKILL.md` with `## Task-Based Execution` | AW-30: collapse boilerplate to 4-line pointer blocks |
| Modify | `skills/{DIRGET,PROCMON_JOBS,PROCMON_LOGS,ETASK,SECDB_TRANSLOG,PYTHON_MARKET_DATA,KILL_ORPHANS}/SKILL.md` | AW-50/52: dead pointers + machine-edit debris |
| Modify | `skills/FORWARD_NETWORK/SKILL.md` | AW-31: grep-recipe guard on the 485KB spec |
| Modify + Create | `skills/CANVAS/SKILL.md` + `skills/CANVAS/src/endpoints.md` | AW-31: endpoint tables move out of SKILL.md |
| Modify + Create | `skills/TMD/SKILL.md` + `skills/TMD/src/endpoints.md` | AW-31: same pattern (polish) |
| Modify | `skills/GIT/SKILL.md`, `skills/GIT_COMMIT/SKILL.md`, `skills/GIT_COMMIT/src/commit_task.py` | AW-45: `add -A` examples → explicit staging; enghub deny path refreshed |
| Modify | `workflows/INDEX.md` | AW-47: project-skill dispatch rows; PROCMON row split; Plan-row keyword disambiguation |
| Modify | `skills/{expand-learning-graph,learning-status,quiz,study,teach,weekly-learning-goals}.md`, `workspace/learning/README.md`, `workspace/learning/vol-learning-framework-design.md`, `workspace/docs/user-manual.md`, `memory/_dormant/sys/secdb-ecosystem.md` | AW-G3/23: remaining model-literal prose sweep |
| Modify | `workspace/lint/whitelists/model_pins.txt`, `workspace/lint/whitelists/prompts.txt` | AW-G3/23: burn both grandfather whitelist FILES to header-only (0 data lines) — the strict-already lint logic then enforces; NEVER edit the lint scripts' `.py` |

## 3. Interfaces

**Consumes (copied from the 00-overview §6 ledger — do not re-derive):**
- `lint_prompts.py` (Plan 04): filenames `[a-z-]+\.prompt\.md`; INDEX.md ↔ directory bijection; every body has an instruction verb; frontmatter `model:` matches `lint_model_pins.EXPECTED_MODEL` where pinned. The check logic is already strict; it is kept green until this plan by the EXTERNAL whitelist file `workspace/lint/whitelists/prompts.txt` (loaded via `load_whitelist()`), and skips bijection while INDEX.md is absent.
- `lint_model_pins.py` (Plan 04): owns `EXPECTED_MODEL = "Claude Opus 4.6"` + `SANCTIONED_SITES = frozenset({"policy/subagent_protocol.md", ".github/copilot-instructions.md"})` — the two paths where the raw literal is CANONICAL and structurally EXEMPT from the check. Flags raw literals outside prompt frontmatter, itself, and `SANCTIONED_SITES`; kept green until this plan by the EXTERNAL whitelist file `workspace/lint/whitelists/model_pins.txt` (temporary grandfathered prose only — burns fully EMPTY).
- `LINTS` registry (`workspace/lint/lint_all.py:57-156`): existing 5-tuple format; this plan appends NO new tuples (only extends two existing scripts and edits two Plan-04 scripts).
- Gate D evidence (Plan 03): `vol.cmd exec` / `./vol exec` sentinel protocol (`workspace/tmp/exec/<ts>_<pid>.out`, `OUTPUT_FILE=`/`EXIT_CODE=` lines) as the acceptance-command vehicle on both surfaces.
- Plan 03's args-file contract: fixed `workspace/tmp/<name>_args.json`, `run_id` in body `[a-z0-9-]+`, `create_and_run_task` retired.
- `subtask_id` format `wfo-07-<M>`; branch `chore/wf-overhaul-07-prompt-skill-hygiene`.

**Produces (later plans rely on):**
- `.github/prompts/INDEX.md` — registry table `| Command | File | Description | Dispatches to |`, 34 rows, linked from AGENTS.md (ledger row "NEW, Plan 07"). Plan 08's closure lint depends on its bijection holding.
- `skills/design.md` "Prompts are dispatchers, never procedure copies" rule (referenced by `design_lint`'s §4.9-adjacent checks from Plan 04).
- `skills/design.md` §3 guide-only skill variant + `lint_skills_structure.py` rules E9/E10 + `validate_skills.py` guide-skill validation — the reconciled 54-skill roster Plan 08's `check_coverage.py` run inherits.
- `skills/CANVAS/src/endpoints.md`, `skills/TMD/src/endpoints.md` — relocated endpoint references.
- `workspace/research/gsvivs-audit-2026-06.md` — relocated one-shot record; the stub prompt points at it.
- Strict lint state: both whitelist files `workspace/lint/whitelists/model_pins.txt` and `workspace/lint/whitelists/prompts.txt` reduced to header-only (0 data lines) — Plan 08 closure asserts the full suite green in this strict state.

---

## 4. Tasks

### Task 1: Rename `fix it.prompt.md` → `fix-it.prompt.md`; reconcile the fix/housekeep triggers (AW-37, quick win 5)

**Files:** Rename `.github/prompts/fix it.prompt.md` → `.github/prompts/fix-it.prompt.md` (git mv). Modify `workflows/fix.md` (trigger line, mirror line 10), `workflows/housekeep.md` (trigger line, mirror line 10).

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-1"
goal: "Rename '.github/prompts/fix it.prompt.md' to fix-it.prompt.md via git mv and reconcile the /fix-it and /housekeep trigger lines so no workflow documents an uninvocable command"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 1 section
  - .github/prompts/fix it.prompt.md
  - workflows/fix.md
  - workflows/housekeep.md
write_scope:
  - .github/prompts/fix it.prompt.md      # removed by git mv
  - .github/prompts/fix-it.prompt.md      # created by git mv
  - workflows/fix.md
  - workflows/housekeep.md
acceptance_criteria:
  - "git ls-files '.github/prompts/fix it.prompt.md' -> empty; git ls-files .github/prompts/fix-it.prompt.md -> 1 line"
  - "grep -n '/fix it' workflows/fix.md -> 0 hits; grep -n '/fix-it' workflows/fix.md -> >=1 hit"
  - "grep -n '/housekeep' workflows/housekeep.md -> 0 hits on the trigger line; grep -n '/lint-workspace' workflows/housekeep.md -> >=1 hit"
  - "./vol exec python workspace/lint/lint_all.py -> sentinel EXIT_CODE=0 (S-B) or vol.cmd exec equivalent (S-A)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/"
  - "do NOT edit the prompt body/frontmatter beyond the rename (Task 3 owns body edits); do NOT add a housekeep.prompt.md"
context_summary: |
  The spaced basename collides with Copilot's built-in /fix (AW-37, hypothesis: exact
  VS Code resolution unverified — the orchestrator performs the live check after this task).
  /housekeep is a dangling trigger with no prompt file; the decided disposition is to drop it —
  workflows/housekeep.md stays reachable via /lint-workspace (lint-workspace.prompt.md already
  reads it). Do not revisit either decision.
depends_on: []
```

- [ ] **Step 1 (red):** Record the defect: `git ls-files ".github/prompts/fix it.prompt.md"` → 1 hit (spaced name tracked). `grep -n "/fix it" workflows/fix.md` → the trigger line (`- User explicitly uses \`/fix it\``, near line 10). `grep -n "/housekeep" workflows/housekeep.md` → the trigger line (`- User explicitly uses \`/lint-workspace\` or \`/housekeep\``, near line 10).
- [ ] **Step 2 (implement):**
  1. `git mv ".github/prompts/fix it.prompt.md" .github/prompts/fix-it.prompt.md`
  2. In `workflows/fix.md`, replace the trigger line with:
     ```markdown
     - User explicitly uses `/fix-it` (note: bare `/fix` is a Copilot built-in and does NOT reach this workflow)
     ```
  3. In `workflows/housekeep.md`, replace the trigger line with:
     ```markdown
     - User explicitly uses `/lint-workspace`
     ```
- [ ] **Step 3 (green):** Re-run the Step-1 greps with inverted expectations (acceptance_criteria lines 1–3); run the standing lint gate.
- [ ] **Step 4 (commit):** `chore(ci): rename 'fix it' prompt to fix-it, reconcile fix/housekeep triggers`
- [ ] **Step 5 (live verification — orchestrator + user, recorded as the AW-37 hypothesis result):** After the commit, the orchestrator asks the user to open a fresh Copilot Chat, type `/fix-it`, and confirm (a) it appears in the picker and resolves to the renamed prompt, and (b) what `/fix it` now does (expected: built-in `/fix` with argument "it"). Paste both observations verbatim into the MR description under the heading `AW-37 hypothesis check`. If `/fix-it` does NOT resolve, add `name: fix-it` to the frontmatter (Task 3's sweep window) and re-verify.

### Task 2: Create `.github/prompts/INDEX.md`; rewrite AGENTS.md's false auto-injection claim and link the registry (AW-43 + AW-11 AGENTS half)

**Files:** Create `.github/prompts/INDEX.md`. Modify `AGENTS.md` (the auto-injection sentence, mirror line 62).

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-2"
goal: "Ship a 34-row .github/prompts/INDEX.md bijective with the directory and rewrite AGENTS.md's auto-injection claim to the read_file contract, linking the INDEX"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 2 section
  - .github/prompts/          # read every *.prompt.md frontmatter
  - AGENTS.md
write_scope:
  - .github/prompts/INDEX.md
  - AGENTS.md
acceptance_criteria:
  - "python one-liner (plan Task 2 Step 3) comparing INDEX rows to directory listing -> 'BIJECTIVE 34==34'"
  - "grep -n 'injected automatically' AGENTS.md -> 0 hits"
  - "grep -n '.github/prompts/INDEX.md' AGENTS.md -> >=1 hit"
  - "./vol exec python workspace/lint/lint_prompts.py -> PASS (bijection check now active)"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree before editing; AGENTS.md was rewritten by Plans 02/05 — locate the auto-injection claim by content; if it is already gone, STOP blocked with the diff"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "INDEX.md descriptions come from each prompt's live frontmatter description: — never invent them"
context_summary: |
  .github/prompts/ is the only primitive without a registry (AW-43); AGENTS.md falsely claims
  skill/persona/workflow content is 'injected automatically' (AW-11) — VS Code attaches nothing
  for backtick paths. Tasks 1/4/5 have already finalized the prompt roster (fix-it renamed,
  gsvivs-audit stubbed, three dispatchers rewritten), so frontmatter descriptions are final.
  lint_prompts.py's INDEX-bijection check activates the moment INDEX.md exists.
depends_on: ["wfo-07-1", "wfo-07-4", "wfo-07-5"]
```

- [ ] **Step 1 (red):** `ls .github/prompts/INDEX.md` → not found. `grep -n "injected automatically" AGENTS.md` → 1 hit (the AW-11 claim: "the full skill guide, persona instructions, and related knowledge are injected automatically").
- [ ] **Step 2 (implement INDEX.md):** Generate the table from the live directory. Extraction recipe (values determinable only at execution time — descriptions MUST come from each file):
  ```
  ./vol exec python - <<'PY'
  from pathlib import Path
  import re
  rows = []
  for p in sorted(Path(".github/prompts").glob("*.prompt.md")):
      text = p.read_text(encoding="utf-8")
      m = re.search(r'^description:\s*"?([^"\n]+)"?\s*$', text, re.M)
      desc = m.group(1).strip() if m else "MISSING-DESCRIPTION"
      targets = re.findall(r'`([^`\n]+\.(?:md|yaml|yml|py))`', text)
      rows.append((p.stem.replace(".prompt",""), p.name, desc, ", ".join(f"`{t}`" for t in targets) or "(self-contained)"))
  for r in rows:
      print(f"| /{r[0]} | `{r[1]}` | {r[2]} | {r[3]} |")
  PY
  ```
  Fallback if a file has no `description:`: fix that file's frontmatter first (it is a lint_prompts defect). Wrap the generated rows in this exact skeleton:
  ```markdown
  # Prompt Registry — `.github/prompts/`

  One row per `*.prompt.md` file (slash-command name = filename stem). This table and the
  directory must stay bijective — enforced by `workspace/lint/lint_prompts.py`.
  Prompts are dispatchers: mode + persona + backtick paths the agent reads via `read_file`
  (see `skills/design.md`, "Prompts are dispatchers"). Bodies never restate procedures.

  | Command | File | Description | Dispatches to |
  |---|---|---|---|
  <generated rows, alphabetical>
  ```
  Worked example rows (verify against live frontmatter; these anchor the expected shape):
  ```markdown
  | /backtest | `backtest.prompt.md` | Backtest — economic-value evaluation via the BACKTEST skill | `skills/BACKTEST/SKILL.md` |
  | /execute | `execute.prompt.md` | Execute workflow — implement, verify, and finish | `workflows/execute.md`, `personas/model-builder.md` |
  | /fix-it | `fix-it.prompt.md` | Fix workflow — diagnose and repair a defect | `workflows/fix.md` |
  | /gsvivs-audit | `gsvivs-audit.prompt.md` | GSVIVS audit — parameterized IV-surface audit of an output JSON | `workspace/research/gsvivs-audit-2026-06.md` |
  | /lint-workspace | `lint-workspace.prompt.md` | Workspace lint + housekeeping gate | `workflows/housekeep.md` |
  | /status | `status.prompt.md` | Read-only project status synthesis | `memory/research/project-state.md` |
  ```
- [ ] **Step 3 (implement AGENTS.md):** Replace the auto-injection sentence (locate by content) with:
  ```markdown
  Slash prompts list backtick-referenced files the agent must read via `read_file` — read them
  before acting; nothing is injected automatically. Full registry: `.github/prompts/INDEX.md`.
  ```
- [ ] **Step 4 (green):** Bijection check:
  ```
  ./vol exec python - <<'PY'
  from pathlib import Path
  import re
  files = {p.name for p in Path(".github/prompts").glob("*.prompt.md")}
  idx = set(re.findall(r'`([a-z-]+\.prompt\.md)`', Path(".github/prompts/INDEX.md").read_text(encoding="utf-8")))
  assert files == idx, f"MISSING {files-idx} EXTRA {idx-files}"
  print(f"BIJECTIVE {len(files)}=={len(idx)}")
  PY
  ```
  Expect `BIJECTIVE 34==34`. Then `./vol exec python workspace/lint/lint_prompts.py` → PASS, and the full `lint_all.py` gate.
- [ ] **Step 5 (commit):** `chore(ci): add .github/prompts/INDEX.md registry; fix AGENTS.md auto-injection claim`

### Task 3: Prompt-body sweep — `read_file` preamble, model-pin rationalization, status path fix (AW-11 + AW-23 + AW-50 half)

**Files:** Modify the 30 `.github/prompts/*.prompt.md` NOT owned by Tasks 4/5 (i.e., everything except `backtest`, `feature`, `research`, `gsvivs-audit`; includes `fix-it.prompt.md` post-rename).

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-3"
goal: "In one pass over 30 prompt files: prefix every verbless body with the read_file instruction, delete the model: pin on the 16 mechanical prompts, keep-and-verify pins elsewhere, and fix status.prompt.md's renamed package path"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 3 section
  - .github/prompts/          # the 30 in-scope files
  - workspace/lint/lint_model_pins.py   # EXPECTED_MODEL constant (read-only)
write_scope:
  - ".github/prompts/*.prompt.md EXCEPT backtest.prompt.md, feature.prompt.md, research.prompt.md, gsvivs-audit.prompt.md, INDEX.md"
acceptance_criteria:
  - "for each of the 16 named prompts: grep -c '^model:' <file> -> 0"
  - "for each of the other 14 in-scope prompts: grep '^model: Claude Opus 4.6$' <file> -> exactly 1 hit"
  - "grep -rn 'src/ml_vol_estimator' .github/prompts/status.prompt.md -> 0 hits; grep -n 'src/volforecast' .github/prompts/status.prompt.md -> >=1 hit"
  - "every in-scope body's first non-frontmatter line contains an imperative verb (lint_prompts instruction-verb check) -> ./vol exec python workspace/lint/lint_prompts.py PASS"
  - "grep -rn '](' <each edited file> introduces 0 new Markdown links (lint_vscode_md stays green)"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree before editing; locate by content"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "NEVER convert backtick paths to Markdown links (AW-11 do-NOT, lint-enforced)"
  - "kept pins are the exact display name 'Claude Opus 4.6' — never the slug, never prose"
  - "do not touch backtest/feature/research/gsvivs-audit (Tasks 4/5 own them)"
depends_on: ["wfo-07-1"]
```

- [ ] **Step 1 (red):** `grep -rc '^model: Claude Opus 4.6' .github/prompts/*.prompt.md` → 34/34 pinned (AW-23). `head -8 .github/prompts/bootup.prompt.md` → body is exactly `` - `workflows/bootup.md` `` (verbless, AW-11). `grep -n 'src/ml_vol_estimator' .github/prompts/status.prompt.md` → 1 hit near line 29 (AW-50).
- [ ] **Step 2 (implement — three edits per file, one pass):**
  1. **Verb preamble:** if the body (everything after the closing `---`) does not begin with an instruction verb, insert as the first body line:
     ```markdown
     Read each file below with read_file before acting.
     ```
     Known verbless bodies (audit list; sweep all 30 anyway): `bootup`, `learn`, `lightweight`, `slop-cleaner`, `plan`, plus any others lint_prompts flags.
  2. **Pin drop:** delete the entire `model: Claude Opus 4.6` frontmatter line in exactly these 16 files (AW-23's named mechanical/read-only set):
     `status, progress, learn, bootup, lightweight, learning-status, quiz, teach, study, git-commit, gitlab-search, glimpse, kill-orphans, data-audit, slop-cleaner, lint`.
     For the other 14 in-scope files (`cure, debug, execute, expand-learning-graph, experiment, fix-it, lint-workspace, plan, refactor, review, slang, slang-review, team, weekly-learning-goals`): keep the pin, verify it is byte-exact `model: Claude Opus 4.6`.
  3. **Path fix:** in `status.prompt.md`, `s|src/ml_vol_estimator/|src/volforecast/|` (the same file already uses `src/volforecast/` correctly 15 lines earlier — make them agree).
- [ ] **Step 3 (green):** Run the acceptance greps; then `./vol exec python workspace/lint/lint_prompts.py` → PASS and the full gate.
- [ ] **Step 4 (commit):** `chore(ci): read_file preamble on verbless prompts; drop pins on 16 mechanical prompts; fix status package path`

### Task 4: Relocate `gsvivs-audit.prompt.md`; keep a 15-line parameterized stub (AW-51)

**Files:** Create `workspace/research/gsvivs-audit-2026-06.md` (relocated body). Rewrite `.github/prompts/gsvivs-audit.prompt.md` as the stub.

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-4"
goal: "Move the dated one-shot gsvivs-audit prompt body to workspace/research/gsvivs-audit-2026-06.md and replace the prompt with a 15-line parameterized stub that takes the JSON path as its argument"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 4 section
  - .github/prompts/gsvivs-audit.prompt.md
  - workspace/research/          # target dir
write_scope:
  - .github/prompts/gsvivs-audit.prompt.md
  - workspace/research/gsvivs-audit-2026-06.md
acceptance_criteria:
  - "wc -l .github/prompts/gsvivs-audit.prompt.md -> <= 20 lines"
  - "test -f workspace/research/gsvivs-audit-2026-06.md -> exists; contains the original 'What We Already Know' narrative"
  - "grep -n 'Read .github/copilot-instructions.md' .github/prompts/gsvivs-audit.prompt.md -> 0 hits (redundant line dropped)"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree; Plan 04 already repointed the prompt's line-155 doc link to workspace/research/gsvivs_iv_improvement_plan.md — preserve that target in the relocated record"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "no file may claim data/external/output.json exists — the stub must fail loudly on a missing input"
context_summary: |
  gsvivs-audit.prompt.md (6,824 B, largest prompt) is a completed, dated analysis stored as a
  permanent slash command whose primary input (data/external/output.json) is untracked (AW-51).
  Nothing references the prompt, so relocation is safe. The decided disposition: keep a
  parameterized stub (preserves the capability and INDEX bijection).
depends_on: []
```

- [ ] **Step 1 (red):** `wc -c ".github/prompts/gsvivs-audit.prompt.md"` → ~6,824 B; body contains the dated "From a preliminary analysis of the first 5 days (2022-05-25 to 2022-06-01)" narrative and the redundant "Read `.github/copilot-instructions.md` before starting" line.
- [ ] **Step 2 (implement):**
  1. Create `workspace/research/gsvivs-audit-2026-06.md` with header, then the full original prompt body verbatim below it:
     ```markdown
     # GSVIVS Audit — method + findings record (relocated 2026-07)

     > Origin: `.github/prompts/gsvivs-audit.prompt.md` (one-shot analysis, June 2026), relocated
     > per AW-51. The live entry point is the parameterized `/gsvivs-audit` stub. Related plan:
     > `workspace/research/gsvivs_iv_improvement_plan.md`.

     <original prompt body, verbatim, including the What-We-Already-Know narrative>
     ```
  2. Replace `.github/prompts/gsvivs-audit.prompt.md` in full with:
     ```markdown
     ---
     description: "GSVIVS audit — parameterized IV-surface audit of a GSVIVS output JSON"
     argument-hint: "path to the GSVIVS output JSON to audit"
     model: Claude Opus 4.6
     ---
     Read each file below with read_file before acting.

     - `workspace/research/gsvivs-audit-2026-06.md`  (method + prior findings — do not re-derive)

     Audit the GSVIVS output JSON at the path given in the argument:
     1. Verify the file exists; if absent, STOP and report — never fabricate results.
     2. Apply the checks catalogued in the method record to the new file.
     3. Write findings to `workspace/research/` as a new dated record; do not edit the old one.
     ```
- [ ] **Step 3 (green):** acceptance greps + full lint gate.
- [ ] **Step 4 (commit):** `chore(ci): relocate gsvivs-audit one-shot to workspace/research; keep parameterized stub`

### Task 5: Rewrite backtest/feature/research prompts as thin dispatchers; add the dispatcher rule to `skills/design.md` (AW-25 + AW-50 half)

**Files:** Modify `.github/prompts/{backtest,feature,research}.prompt.md`, `skills/design.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-5"
goal: "Replace the three forked prompt runbooks with thin dispatchers deferring all parameters to skills/BACKTEST, skills/FEATURE_BUILD, and workflows/research.md, and codify 'prompts are dispatchers' in skills/design.md"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 5 section
  - .github/prompts/backtest.prompt.md
  - .github/prompts/feature.prompt.md
  - .github/prompts/research.prompt.md
  - .github/prompts/data-audit.prompt.md    # exemplar thin dispatcher (read-only)
  - skills/design.md
write_scope:
  - .github/prompts/backtest.prompt.md
  - .github/prompts/feature.prompt.md
  - .github/prompts/research.prompt.md
  - skills/design.md
acceptance_criteria:
  - "grep -n '5 bps round-trip' .github/prompts/backtest.prompt.md -> 0 hits (no cost model in the prompt)"
  - "grep -n 'src/ml_vol_estimator' .github/prompts/feature.prompt.md -> 0 hits"
  - "grep -cn 'SKILL.md' .github/prompts/backtest.prompt.md -> >=1; same for feature.prompt.md"
  - "wc -l on each of the three prompts -> <= 15 lines"
  - "grep -n 'Prompts are dispatchers' skills/design.md -> 1 hit"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree; Plan 06 repointed research.prompt.md's memory reference — PRESERVE that repoint, do not restore memory/research/README.md"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "NEVER Markdown links in prompt bodies; kept pins are exactly 'Claude Opus 4.6'"
  - "all parameters (cost model, thresholds, step sequences) live ONLY in the owning SKILL.md/workflow — deleting them from the prompt, never copying them anywhere"
context_summary: |
  backtest.prompt.md forks the BACKTEST skill with a drifted cost model ('5 bps round-trip' vs
  the skill's spread_bps 5 + commission_per_contract 1.25 + slippage_bps 2); feature.prompt.md
  routes to the renamed package src/ml_vol_estimator/; research.prompt.md duplicates a 7-step
  protocol omitting workflows/research.md's mandatory Hypothesis Card / FOCUS gate (AW-25).
  data-audit.prompt.md and git-commit.prompt.md are the sanctioned exemplars. The skill/workflow
  is the single source of truth; the prompts become mode + read-list only.
depends_on: []
```

- [ ] **Step 1 (red):** `grep -n "5 bps round-trip" .github/prompts/backtest.prompt.md` → 1 hit (line ~22). `grep -n "src/ml_vol_estimator" .github/prompts/feature.prompt.md` → 1 hit (line ~26). `grep -n "FOCUS" .github/prompts/research.prompt.md` → 0 hits despite a 7-step protocol at lines ~17-27.
- [ ] **Step 2 (implement — full replacement bodies):**
  `backtest.prompt.md`:
  ```markdown
  ---
  description: "Backtest — economic-value evaluation via the BACKTEST skill"
  argument-hint: "trial id or config to backtest"
  model: Claude Opus 4.6
  ---
  Read each file below with read_file before acting.

  - `skills/BACKTEST/SKILL.md`
  - `personas/eval-sentinel.md`

  Run the backtest per the skill. All parameters (cost model, thresholds, outputs) come from
  the skill — never restate or override them here.
  ```
  `feature.prompt.md`:
  ```markdown
  ---
  description: "Feature build — construct feature layers via the FEATURE_BUILD skill"
  argument-hint: "feature layer(s) to build"
  model: Claude Opus 4.6
  ---
  Read each file below with read_file before acting.

  - `skills/FEATURE_BUILD/SKILL.md`
  - `personas/model-builder.md`

  Build the requested layers per the skill (source tree: `src/volforecast/features/`). All
  parameters and the args-file contract come from the skill.
  ```
  `research.prompt.md` (preserve Plan 06's memory repoint target verbatim as found on the live tree):
  ```markdown
  ---
  description: "Research workflow — hypothesis-driven investigation"
  argument-hint: "research question or hypothesis"
  model: Claude Opus 4.6
  ---
  Read each file below with read_file before acting.

  - `workflows/research.md`
  - `memory/INDEX.md`  (research section — as repointed by Plan 06)
  - `workspace/research/research-journal.md`

  Follow the workflow exactly, including the Hypothesis Card / FOCUS gate — do not improvise
  a step list here.
  ```
  `skills/design.md` — append this rule as a new numbered rule in the rules section (match the file's existing rule formatting):
  ```markdown
  ## Prompts are dispatchers, never procedure copies

  A `.github/prompts/*.prompt.md` file may contain only: frontmatter, one mode sentence, the
  "Read each file below with read_file before acting." line, bare backtick paths to the owning
  SKILL.md / workflow / persona, and at most 3 lines of invocation-specific notes. All
  parameters, defaults, and step sequences live in the owning skill or workflow. A prompt that
  restates a procedure is a defect (drift fork — see audit AW-25). Registry:
  `.github/prompts/INDEX.md`.
  ```
- [ ] **Step 3 (green):** acceptance greps + full lint gate.
- [ ] **Step 4 (commit):** `chore(framework): backtest/feature/research prompts become thin dispatchers; dispatcher rule in skills/design.md`

### Task 6: Skill-roster reconciliation — DECISION, guide-only variant sanctioned, linters taught, orphan deleted (AW-18)

**Files:** Modify `skills/design.md` (§3), `skills/INDEX.md`, `workspace/lint/lint_skills_structure.py`, `workspace/lint/validate_skills.py`, `policy/implementation_boundary.md`; delete `skills/ssp_helpers.py`; frontmatter-normalize the 6 flat guide skills if needed.

**DECISION (orchestrator presents to the user before dispatching, default pre-selected):**
- **(b) DEFAULT — sanction the flat variant:** keep the 6 lowercase guide skills as files, codify the variant in `skills/design.md` §3, teach both linters, add 6 rows to `skills/INDEX.md`. Rationale: Plan 08's Gate E may relocate the whole tutoring cluster; converting to UPPER_SNAKE dirs now would be throwaway work.
- **(a) alternative — convert to dirs:** `git mv skills/quiz.md skills/QUIZ/SKILL.md` (etc. for all 6), author the missing Identity/When-to-Use/Links sections per `memory/ref/skill-authoring.md`, update the 6 prompts' backtick paths, update `skills/INDEX.md` + `policy/implementation_boundary.md` to 54 dirs. Only choose if the user rejects (b); then skip the linter guide-skill extensions but STILL append rule E10 (no loose scripts) and delete `ssp_helpers.py`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-6"
goal: "Reconcile the 48-vs-54 skill roster: sanction the guide-only flat-skill variant in design.md §3, extend both skill linters to validate flat files (red-then-green), add 6 INDEX rows, make implementation_boundary.md explicit, delete orphan ssp_helpers.py"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 6 section
  - skills/design.md
  - skills/INDEX.md
  - workspace/lint/lint_skills_structure.py
  - workspace/lint/validate_skills.py
  - policy/implementation_boundary.md
  - skills/quiz.md            # + the 5 sibling guide files (frontmatter check)
write_scope:
  - skills/design.md
  - skills/INDEX.md
  - workspace/lint/lint_skills_structure.py
  - workspace/lint/validate_skills.py
  - policy/implementation_boundary.md
  - skills/ssp_helpers.py     # delete
  - skills/expand-learning-graph.md   # frontmatter normalization only, if lint requires
  - skills/learning-status.md
  - skills/quiz.md
  - skills/study.md
  - skills/teach.md
  - skills/weekly-learning-goals.md
acceptance_criteria:
  - "RED evidence: new E10 check fails on skills/ssp_helpers.py BEFORE deletion (pasted output)"
  - "git ls-files skills/ssp_helpers.py -> empty after deletion"
  - "./vol exec python workspace/lint/lint_skills_structure.py -> PASS; planted skills/zz-bad-guide.md (no frontmatter) -> FAIL E9, then deleted -> PASS"
  - "./vol exec python workspace/lint/validate_skills.py -> PASS including the 6 guide files"
  - "grep -c '^| \\*\\*' skills/INDEX.md rows now include the 6 guide skills; grep -n 'guide-only' policy/implementation_boundary.md -> >=1 hit"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0 (registry-drift stays 54==54)"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree before editing; locate by content"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "APPEND-only to both linters — never modify existing E1-E8 / Rule 1-9 logic (do-not-rebuild #7)"
  - "the decision default is variant (b); if the user chose (a) at dispatch, follow the alternative recipe in the plan Task 6 section instead"
context_summary: |
  Three authorities disagree on the roster: skills/INDEX.md lists 48 dir skills, policy/
  implementation_boundary.md says 54, design.md's contract is dirs-only — while 6 lowercase
  guide skills sit at skills/ root, wired to prompts but invisible to both linters, plus the
  orphan ssp_helpers.py (5,045 B, 0 refs) (AW-18). lint_registry_drift.py already counts flat
  files (54 actual), so sanctioning the variant makes all authorities agree at 54.
depends_on: ["wfo-07-5"]
```

- [ ] **Step 1 (write the failing check — this is the red):** Append to `workspace/lint/lint_skills_structure.py` (exemplar for shape: the existing `RE_FOLDER_NAME` constant near line 60 and E-rule reporting; wire `check_root_files` into the same error-collection path `main()` uses for E1–E8):
  ```python
  # --- Guide-only skills at skills/ root (sanctioned variant, skills/design.md section 3) ---
  RE_GUIDE_SKILL_NAME = re.compile(r"^[a-z][a-z0-9-]*\.md$")
  GUIDE_SKILL_EXEMPT = {"INDEX.md", "design.md"}

  def check_root_files(skills_dir, errors):
      """E9: guide-only skill files must be lowercase-kebab .md with name/description frontmatter.
      E10: no loose non-.md files (scripts) at skills/ root."""
      for entry in sorted(skills_dir.iterdir()):
          if entry.is_dir() or entry.name in GUIDE_SKILL_EXEMPT:
              continue
          if entry.suffix != ".md":
              errors.append(f"E10 {entry}: loose non-.md file at skills/ root; scripts live under a skill's src/")
              continue
          if not RE_GUIDE_SKILL_NAME.match(entry.name):
              errors.append(f"E9 {entry}: guide-only skill filename must be lowercase-kebab .md")
              continue
          text = entry.read_text(encoding="utf-8", errors="replace")
          if not text.startswith("---") or "name:" not in text[:400] or "description:" not in text[:800]:
              errors.append(f"E9 {entry}: guide-only skill missing frontmatter name:/description:")
  ```
  Append to `workspace/lint/validate_skills.py` (reuse the existing `RE_FRONTMATTER` at ~line 59; wire into `main()`'s aggregation next to the dir iteration at ~line 240):
  ```python
  def validate_guide_skills(skills_dir):
      """Guide-only skills (skills/design.md section 3): frontmatter name (== stem) + description."""
      problems = []
      for entry in sorted(skills_dir.glob("*.md")):
          if entry.name in ("INDEX.md", "design.md"):
              continue
          m = RE_FRONTMATTER.match(entry.read_text(encoding="utf-8", errors="replace"))
          if not m:
              problems.append(f"{entry}: guide skill has no frontmatter block")
              continue
          fm = m.group(1)
          if f"name: {entry.stem}" not in fm:
              problems.append(f"{entry}: frontmatter name must equal filename stem '{entry.stem}'")
          if "description:" not in fm:
              problems.append(f"{entry}: frontmatter missing description:")
      return problems
  ```
- [ ] **Step 2 (run to confirm red):** `./vol exec python workspace/lint/lint_skills_structure.py` → **FAIL** with `E10 skills/ssp_helpers.py: loose non-.md file at skills/ root...`. Paste this output into the return contract (it is the red evidence). Additionally plant `skills/zz-bad-guide.md` containing only `# junk`, re-run → **FAIL E9**; delete the plant.
- [ ] **Step 3 (implement the content fixes):**
  1. `git rm skills/ssp_helpers.py` (0 tracked references — verified by the audit and freshness §10).
  2. If `validate_guide_skills` flags any of the 6 guide files (name != stem), normalize that file's frontmatter `name:` to the stem — no other content edits.
  3. `skills/design.md` §3 — append after the "One directory per skill. Name: UPPER_SNAKE_CASE" rule:
     ```markdown
     **Sanctioned variant — guide-only skills.** A skill that is pure prompt-guidance (no src/,
     no task wrapper) MAY live as a single lowercase-kebab file at `skills/<name>.md` with
     frontmatter `name:` (== filename stem) and `description:`, wired to a matching
     `.github/prompts/<name>.prompt.md`. Current roster: expand-learning-graph, learning-status,
     quiz, study, teach, weekly-learning-goals. Validated by lint_skills_structure E9/E10 and
     validate_skills guide-skill checks. Everything else follows the directory contract.
     ```
  4. `skills/INDEX.md` — add a `### Learning (guide-only)` section with 6 rows in the existing row format: `| **quiz** | [quiz.md](quiz.md) | <one-line description from its frontmatter> |` (etc.).
  5. `policy/implementation_boundary.md` — edit the skill-system row (mirror line 24) so the count reads `Skill system (54 skills: 48 directories + 6 guide-only files)` with the same comma-list `lint_registry_drift.py`'s `RE_SKILL_ROW` parses — change ONLY the parenthetical text, keep the name list intact so the drift lint stays 54==54.
- [ ] **Step 4 (run to green):** `./vol exec python workspace/lint/lint_skills_structure.py` → PASS; `./vol exec python workspace/lint/validate_skills.py` → PASS; full `lint_all.py` → PASS (registry drift unchanged at 54).
- [ ] **Step 5 (commit):** `chore(framework): sanction guide-only skill variant, lint flat skills (E9/E10), drop orphan ssp_helpers.py`

### Task 7: Collapse the Task-Based-Execution boilerplate in ~34 SKILL.mds to 4-line pointer blocks (AW-30 — biggest mechanical sweep)

**Files:** Modify every `skills/*/SKILL.md` containing a `## Task-Based Execution` section (~34 files; enumerate at execution). `memory/ref/vscode-tasks.md` is read-only (already canonical; rule E3 fixed by Plan 03).

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-7"
goal: "Replace every '## Task-Based Execution' boilerplate section (~34 SKILL.mds, 27,036 B) with a 4-line pointer block that keeps only the skill-specific label, args-file path, and one example JSON, pointing at memory/ref/vscode-tasks.md for the shared protocol"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 7 section
  - memory/ref/vscode-tasks.md          # canonical protocol (read-only)
  - skills/                              # enumerate via grep
write_scope:
  - "skills/*/SKILL.md — only files containing a '## Task-Based Execution' heading"
acceptance_criteria:
  - "before/after byte measurement of the sections (plan Task 7 Step 1 script) recorded in the return contract; after-total <= ~9,000 B"
  - "grep -rln '## Task-Based Execution' skills/*/SKILL.md -> same file COUNT as before (sections collapsed, not deleted)"
  - "every collapsed block still names its task label, its fixed workspace/tmp/<name>_args.json path, run_id-in-body [a-z0-9-]+, and memory/ref/vscode-tasks.md"
  - "grep -rn 'create_and_run_task' skills/*/SKILL.md -> 0 hits (Plan 03 state preserved)"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0 (incl. lint_vscode_md, lint_args_contract)"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree; Plan 03 rewrote the args-contract text in GIT/GIT_COMMIT/SLANG_LINT/SLANG_TEST_COVERAGE — PRESERVE the fixed-path contract and the last-writer-wins caveat verbatim in those files' blocks"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "keep skill-SPECIFIC content (args JSON schema/example, out-file name); delete only the shared protocol prose duplicated from vscode-tasks.md"
  - "do not touch any other section of any SKILL.md"
depends_on: []
```

- [ ] **Step 1 (red — measure):**
  ```
  ./vol exec python - <<'PY'
  from pathlib import Path
  import re
  total = 0; files = 0
  for p in sorted(Path("skills").glob("*/SKILL.md")):
      t = p.read_text(encoding="utf-8", errors="replace")
      m = re.search(r"(^## Task-Based Execution.*?)(?=^## |\Z)", t, re.M | re.S)
      if m:
          files += 1; total += len(m.group(1).encode())
  print(f"FILES={files} SECTION_BYTES={total}")
  PY
  ```
  Expect `FILES=34 SECTION_BYTES=~27036` (record exact live numbers).
- [ ] **Step 2 (implement — bounded recipe, applied per file):** For each of the enumerated files, replace the section body (heading kept, heading normalized to plain `## Task-Based Execution`) with exactly this template, filled from the section's OWN existing content (label, args filename, one example JSON — execution-time values, present in every section today):
  ```markdown
  ## Task-Based Execution

  - Task label: `<label from this section>` — run via `run_task`; args file: `workspace/tmp/<name>_args.json` (`run_id` inside the JSON body, `[a-z0-9-]+`; last writer wins across concurrent sessions).
  - Example args: `{"run_id": "<example>", <this skill's own args fields, one line>}`
  - Protocol (Zero-Allow, blocking, out-file read, cleanup): `memory/ref/vscode-tasks.md`
  ```
  Rules: if the existing section documents multiple task labels, one bullet per label; if Plan 03 added a longer contract note (GIT/GIT_COMMIT/SLANG_LINT/SLANG_TEST_COVERAGE), carry that note's sentences into the first bullet unchanged rather than shortening them.
- [ ] **Step 3 (green):** Re-run the Step-1 measurement → `FILES=34 SECTION_BYTES<=~9000`. Run `grep -rn 'create_and_run_task' skills/*/SKILL.md` → 0. Full lint gate (lint_args_contract from Plan 04 confirms every documented args filename still matches its task definition).
- [ ] **Step 4 (commit):** `chore(framework): collapse Task-Based Execution boilerplate to 4-line pointer blocks (34 SKILL.mds)`

### Task 8: Dead routing pointers and machine-edit debris in skills (AW-50 skills half + AW-52)

**Files:** Modify `skills/DIRGET/SKILL.md`, `skills/PROCMON_JOBS/SKILL.md`, `skills/PROCMON_LOGS/SKILL.md`, `skills/ETASK/SKILL.md`, `skills/SECDB_TRANSLOG/SKILL.md`, `skills/PYTHON_MARKET_DATA/SKILL.md`, `skills/KILL_ORPHANS/SKILL.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-8"
goal: "Fix the five dead routing pointers (phantom skills APPDIR_API/CPNL_SUPPORT/GET_ISSUANCE_TASKS) and the machine-edit debris (corrupted ETASK headings, duplicate step numbers in SECDB_TRANSLOG and PYTHON_MARKET_DATA, KILL_ORPHANS triple-pasted Troubleshooting) across 7 SKILL.mds"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 8 section
  - skills/DIRGET/SKILL.md
  - skills/PROCMON_JOBS/SKILL.md
  - skills/PROCMON_LOGS/SKILL.md
  - skills/ETASK/SKILL.md
  - skills/SECDB_TRANSLOG/SKILL.md
  - skills/PYTHON_MARKET_DATA/SKILL.md
  - skills/KILL_ORPHANS/SKILL.md
write_scope:
  - skills/DIRGET/SKILL.md
  - skills/PROCMON_JOBS/SKILL.md
  - skills/PROCMON_LOGS/SKILL.md
  - skills/ETASK/SKILL.md
  - skills/SECDB_TRANSLOG/SKILL.md
  - skills/PYTHON_MARKET_DATA/SKILL.md
  - skills/KILL_ORPHANS/SKILL.md
acceptance_criteria:
  - "grep -rn 'APPDIR_API\\|CPNL_SUPPORT\\|GET_ISSUANCE_TASKS' skills/ -> 0 hits"
  - "grep -n 'CList\\|LI Commands' skills/ETASK/SKILL.md -> 0 hits"
  - "no duplicate step ordinals: SECDB_TRANSLOG and PYTHON_MARKET_DATA step sequences strictly increasing (manual check pasted)"
  - "grep -c '<first row text of the Troubleshooting table>' skills/KILL_ORPHANS/SKILL.md -> 1"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree; Plan 03 (AW-36) already reworked KILL_ORPHANS — if the Troubleshooting dedup is already done, record no_change_needed for that item and move on"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "content fixes only — do not restructure sections Task 7 just collapsed"
depends_on: ["wfo-07-7"]
```

- [ ] **Step 1 (red):** `grep -rn 'APPDIR_API' skills/DIRGET/SKILL.md` → 1 hit (~:32); `grep -n 'CPNL_SUPPORT' skills/PROCMON_JOBS/SKILL.md` → 1 hit (~:14); `grep -n 'GET_ISSUANCE_TASKS' skills/PROCMON_LOGS/SKILL.md` → 1 hit (~:67); `grep -n 'CList\|LI Commands' skills/ETASK/SKILL.md` → 2 hits (~:54/:67); duplicate `step 3` in SECDB_TRANSLOG (~:152-155) and duplicate `### 3.` in PYTHON_MARKET_DATA (~:110/:118); Troubleshooting table appears 3 times in KILL_ORPHANS (~:78-96) unless Plan 03 already deduped.
- [ ] **Step 2 (implement):**
  1. DIRGET: `s/APPDIR_API/CANVAS/` (the skill was renamed; CANVAS is the live name).
  2. PROCMON_JOBS: delete or rewrite the "Called by CPNL_SUPPORT" sentence — replace with "Invoked directly or via the PROCMON dispatch rows in `workflows/INDEX.md`."
  3. PROCMON_LOGS: delete the GET_ISSUANCE_TASKS sentence (no such skill exists anywhere).
  4. ETASK: `## CList Open Tasks` → `## List Open Tasks (Aggregated)`; `### LI Commands` → `## CLI Commands`.
  5. SECDB_TRANSLOG: renumber the duplicated step 3 → steps 3, 4 (and shift any following ordinals).
  6. PYTHON_MARKET_DATA: renumber the second `### 3.` → `### 4.` (and shift following ordinals).
  7. KILL_ORPHANS: keep exactly one Troubleshooting table, delete the other two copies (skip with `no_change_needed` if Plan 03's AW-36 rework already did this).
- [ ] **Step 3 (green):** acceptance greps + full lint gate.
- [ ] **Step 4 (commit):** `chore(framework): fix dead skill routing pointers and machine-edit debris (7 SKILL.mds)`

### Task 9: Knowledge-store guards — FORWARD_NETWORK grep recipe, CANVAS/TMD table moves (AW-31)

**Files:** Modify `skills/FORWARD_NETWORK/SKILL.md`, `skills/CANVAS/SKILL.md`, `skills/TMD/SKILL.md`; create `skills/CANVAS/src/endpoints.md`, `skills/TMD/src/endpoints.md`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-9"
goal: "Replace FORWARD_NETWORK's 'consult the 485KB spec' instruction with a grep-extraction recipe plus an explicit never-read-whole guard, and move the CANVAS (46-row) and TMD (33-row) inline endpoint tables to src/endpoints.md files keeping ~10-row most-used tables plus pointers"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 9 section
  - skills/FORWARD_NETWORK/SKILL.md
  - skills/CANVAS/SKILL.md
  - skills/TMD/SKILL.md
write_scope:
  - skills/FORWARD_NETWORK/SKILL.md
  - skills/CANVAS/SKILL.md
  - skills/CANVAS/src/endpoints.md
  - skills/TMD/SKILL.md
  - skills/TMD/src/endpoints.md
acceptance_criteria:
  - "grep -n 'NEVER read the whole' skills/FORWARD_NETWORK/SKILL.md -> 1 hit; grep -n 'Consult' <same section> -> 0 hits"
  - "wc -l skills/CANVAS/SKILL.md -> < 250 lines (design_lint WARN threshold cleared)"
  - "test -f skills/CANVAS/src/endpoints.md and skills/TMD/src/endpoints.md; row counts >= the rows removed from the SKILL.mds"
  - "grep -n 'src/endpoints.md' skills/CANVAS/SKILL.md skills/TMD/SKILL.md -> 1 hit each"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0 (skills-structure: .md is an allowed src/ extension)"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree before editing"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "do NOT delete or edit skills/FORWARD_NETWORK/src/forward_network_api.yaml itself"
  - "most-used selection rule: keep the endpoint rows referenced elsewhere in the same SKILL.md's examples; fallback: the first 10 rows of the original table"
depends_on: ["wfo-07-7"]
```

- [ ] **Step 1 (red):** `wc -c skills/FORWARD_NETWORK/src/forward_network_api.yaml` → ~485,434 B; `grep -n 'Consult' skills/FORWARD_NETWORK/SKILL.md` → the "Consult ... for complete schemas" line (~:129) with no read guard. `wc -l skills/CANVAS/SKILL.md` → ~260 (trips the 250-line WARN); TMD ~149 with a 33-row inline table.
- [ ] **Step 2 (implement):**
  1. FORWARD_NETWORK — replace the consult line (locate by content) with:
     ```markdown
     **Schema lookup — NEVER read the whole file.** `src/forward_network_api.yaml` is ~485 KB
     (~121k tokens); reading it whole detonates the context window. Extract only what you need:
     - List all endpoint paths: `grep -n '^  /' skills/FORWARD_NETWORK/src/forward_network_api.yaml`
     - Extract one endpoint's block (example):
       `awk '/^  \/network\/search:/{f=1} f&&/^  \/[a-z]/&&!/network\/search/{exit} f' skills/FORWARD_NETWORK/src/forward_network_api.yaml`
     - Search a schema/field name: `grep -n -A 5 '<FieldName>' skills/FORWARD_NETWORK/src/forward_network_api.yaml`
     Run these via the sanctioned wrapper (`./vol exec ...` on S-B, `vol.cmd exec ...` on S-A).
     ```
  2. CANVAS — cut the "Canvas Backend Endpoints" table rows (~46 rows, lines ~43-192) into a new `skills/CANVAS/src/endpoints.md` (`# CANVAS — full endpoint reference` + the table verbatim). In SKILL.md keep a `### Most-used endpoints` table with ~10 rows (selection rule in the packet) followed by:
     ```markdown
     Full endpoint reference (46 rows): `src/endpoints.md` — grep it for the endpoint you need;
     do not paste the whole table back here.
     ```
  3. TMD — same pattern: 33-row table → `skills/TMD/src/endpoints.md`, keep ~10 most-used rows + the same pointer sentence.
- [ ] **Step 3 (green):** acceptance checks + full lint gate (`lint_skills_structure` E-rules allow `.md` under `src/`).
- [ ] **Step 4 (commit):** `chore(framework): FORWARD_NETWORK grep-recipe guard; CANVAS/TMD endpoint tables move to src/endpoints.md`

### Task 10: GIT staging examples and enghub deny-path refresh (AW-45)

**Files:** Modify `skills/GIT/SKILL.md`, `skills/GIT_COMMIT/SKILL.md`, `skills/GIT_COMMIT/src/commit_task.py`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-10"
goal: "Replace both 'git add -A' examples in GIT/SKILL.md with explicit staging, update the embedded-repo rule and GIT_COMMIT deny list to the live enghub path workspace/knowledge/enghub/ (keeping the legacy path defensively)"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 10 section
  - skills/GIT/SKILL.md
  - skills/GIT_COMMIT/SKILL.md
  - skills/GIT_COMMIT/src/commit_task.py
  - skills/ENGHUB/src/enghub.py        # read-only: confirms the live clone path (:26)
write_scope:
  - skills/GIT/SKILL.md
  - skills/GIT_COMMIT/SKILL.md
  - skills/GIT_COMMIT/src/commit_task.py
acceptance_criteria:
  - "grep -n '\"add\", *\"-A\"\\|add -A' skills/GIT/SKILL.md -> hits only inside the NEVER rule text, none in examples"
  - "grep -n 'workspace/knowledge/enghub/' skills/GIT/SKILL.md skills/GIT_COMMIT/src/commit_task.py -> >=1 hit each"
  - "./vol exec python -c \"import re,pathlib; s=pathlib.Path('skills/GIT_COMMIT/src/commit_task.py').read_text(); assert 'workspace/knowledge/enghub/' in s and 'workspace/docs/enghub/' in s; print('DENY-LIST OK')\" -> DENY-LIST OK"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree; Plans 03/07-7 edited these SKILL.mds — locate the two add -A examples by content (near old :40 and :112)"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "commit_task.py: APPEND to DENIED_PREFIXES only; TDD note: skills/ Python has no test suite — the import-assert acceptance line above is the verification"
context_summary: |
  GIT/SKILL.md's flagship 'Full push workflow' example (and a second example) uses git add -A,
  violating its own NEVER rule; the rule and GIT_COMMIT's deny list guard the STALE enghub path
  workspace/docs/enghub/ while ENGHUB now clones to workspace/knowledge/enghub/ (AW-45,
  mitigated today only by .gitignore:30). Keep the legacy prefix defensively; add the live one.
depends_on: ["wfo-07-7"]
```

- [ ] **Step 1 (red):** `grep -n '"add"' skills/GIT/SKILL.md` → two examples containing `["add","-A"]` (near old :40 and :112); `grep -n 'workspace/knowledge/enghub' skills/GIT_COMMIT/src/commit_task.py` → 0 hits; `grep -n 'workspace/docs/enghub' skills/GIT/SKILL.md skills/GIT_COMMIT/src/commit_task.py` → 1 hit each (stale rationale path).
- [ ] **Step 2 (implement):**
  1. Both GIT/SKILL.md examples: replace `["add", "-A"]` with explicit staging, e.g.
     ```json
     "args": ["add", "src/volforecast/models/example.py", "src/tests/unit/test_example.py"]
     ```
     with a following note line: `Stage files explicitly by path — NEVER add -A.`
  2. GIT/SKILL.md NEVER rule (old :137): update to `NEVER git add -A (embedded repo at workspace/knowledge/enghub/; legacy path workspace/docs/enghub/ also denied).`
  3. `commit_task.py` — append to the deny tuple (keep every existing entry):
     ```python
     DENIED_PREFIXES = (
         # ... existing entries unchanged ...
         "workspace/docs/enghub/",       # legacy ENGHUB clone path (kept defensively)
         "workspace/knowledge/enghub/",  # live ENGHUB clone path (skills/ENGHUB/src/enghub.py:26)
     )
     ```
     (De-duplicate if `workspace/docs/enghub/` is already present — append only the missing prefix.)
  4. GIT_COMMIT/SKILL.md conventions block (old :186 area): if it names the enghub path or an `add -A` example, apply the same two fixes; otherwise `no_change_needed`.
- [ ] **Step 3 (green):** acceptance greps + the import-assert one-liner + full lint gate.
- [ ] **Step 4 (commit):** `chore(framework): explicit staging in GIT examples; enghub deny path refreshed to workspace/knowledge/`

### Task 11: Dispatch registry — project-skill rows, PROCMON split, keyword disambiguation (AW-47)

**Files:** Modify `workflows/INDEX.md` (Skill Dispatch table + Plan row keywords).

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-11"
goal: "Register the 9 project skills in workflows/INDEX.md's Skill Dispatch table, replace the phantom PROCMON row with PROCMON_JOBS/PROCMON_LOGS rows, and remove the ambiguous keywords from the Plan workflow row"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 11 section
  - workflows/INDEX.md
  - AGENTS.md                 # read-only: the project-skills table (old :180-188)
  - skills/INDEX.md           # read-only: one-line descriptions
write_scope:
  - workflows/INDEX.md
acceptance_criteria:
  - "grep -n 'PROCMON |' workflows/INDEX.md -> 0 hits; grep -n 'PROCMON_JOBS\\|PROCMON_LOGS' workflows/INDEX.md -> 2 rows"
  - "grep -c 'DATA_INGEST\\|FEATURE_BUILD\\|MODEL_TRAIN\\|EVALUATE\\|BACKTEST\\|RESEARCH\\|NOTEBOOK' workflows/INDEX.md -> >= 7"
  - "grep -n \"don't assume\\|let's discuss\" workflows/INDEX.md -> 0 hits"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0 (incl. Plan 04's design_lint 4.9 dispatch-registration check)"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree before editing"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "every dispatch keyword must be unique across rows — no keyword may appear in two rows (collision rule)"
  - "NOTEBOOK/RESEARCH rows must note 'agent-driven only, no task' per Plan 03's AW-05 disposition"
depends_on: []
```

- [ ] **Step 1 (red):** `grep -n 'PROCMON' workflows/INDEX.md` → 1 row naming no real skill; `grep -c 'MODEL_TRAIN\|BACKTEST' workflows/INDEX.md` → 0 (zero project skills registered); Plan row (~:23) contains "don't assume" / "let's discuss" colliding with the Interview row (~:36).
- [ ] **Step 2 (implement):** In the Skill Dispatch table append one row per project skill listed in AGENTS.md's project-skills table (enumerate live; expected 9), with unique keywords:
  ```markdown
  | ingest, data pull, backfill | DATA_INGEST |
  | feature build, build layer | FEATURE_BUILD |
  | train, tune, fit model | MODEL_TRAIN |
  | evaluate, QLIKE, diebold | EVALUATE |
  | backtest, economic value | BACKTEST |
  | literature, hypothesis | RESEARCH (agent-driven only, no task) |
  | notebook, exploration | NOTEBOOK (agent-driven only, no task) |
  ```
  (Add rows for any further skills in the live AGENTS.md table using their When-to-Use keywords; keywords must not collide with existing rows.) Replace the PROCMON row with two rows: `| process monitor, jobs | PROCMON_JOBS |` and `| process logs | PROCMON_LOGS |`. In the workflow-registry Plan row, delete the keywords "don't assume" and "let's discuss" (they stay on the Interview row only).
- [ ] **Step 3 (green):** acceptance greps + full lint gate.
- [ ] **Step 4 (commit):** `chore(framework): register project skills in dispatch table; split PROCMON row; disambiguate plan keywords`

### Task 12: Finish the model-literal sweep; burn both lint whitelist files — lints go strict (AW-G3 + AW-23 completion)

**Files:** Modify `skills/{expand-learning-graph,learning-status,quiz,study,teach,weekly-learning-goals}.md`, `workspace/learning/README.md`, `workspace/learning/vol-learning-framework-design.md`, `workspace/docs/user-manual.md`, `memory/_dormant/sys/secdb-ecosystem.md`, `workspace/lint/whitelists/model_pins.txt`, `workspace/lint/whitelists/prompts.txt`.

**Copilot context packet:**

```yaml
subtask_id: "wfo-07-12"
goal: "Replace every remaining raw model literal outside prompt frontmatter and the two SANCTIONED_SITES (skills flat files 11, workspace/learning 21+2 slugs, user-manual 1, _dormant/sys 1) with the subagent-protocol pointer, then burn the whitelist files workspace/lint/whitelists/model_pins.txt and workspace/lint/whitelists/prompts.txt to header-only so both lints run strict, red-then-green"
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md   # Task 12 section
  - workspace/lint/whitelists/model_pins.txt
  - workspace/lint/whitelists/prompts.txt
  - workspace/lint/lint_model_pins.py   # read-only: confirm SANCTIONED_SITES + whitelist load path
  - workspace/lint/lint_prompts.py      # read-only: confirm whitelist load path
  - skills/                    # the 6 flat guide files
  - workspace/learning/
  - workspace/docs/user-manual.md
  - memory/_dormant/sys/secdb-ecosystem.md
write_scope:
  - skills/expand-learning-graph.md
  - skills/learning-status.md
  - skills/quiz.md
  - skills/study.md
  - skills/teach.md
  - skills/weekly-learning-goals.md
  - workspace/learning/README.md
  - workspace/learning/vol-learning-framework-design.md
  - workspace/docs/user-manual.md
  - memory/_dormant/sys/secdb-ecosystem.md
  - workspace/lint/whitelists/model_pins.txt
  - workspace/lint/whitelists/prompts.txt
acceptance_criteria:
  - "RED evidence: with content fixed but the whitelist files still populated, planting workspace/tmp/../zz-probe files per plan Step 3 shows both lints fail on violations (pasted), then pass after removal"
  - "grep -rln 'Opus 4.6' --include='*.md' . | grep -v -e '\\.prompt\\.md' -e 'policy/subagent_protocol.md' -e '.github/copilot-instructions.md' -e 'workspace/plans/' -> 0 files (the only permitted homes are the two SANCTIONED_SITES, prompt frontmatter, and this suite's own plan files); grep -rn 'claude-opus-4-6' . -> 0 hits"
  - "both whitelist files are header-only: awk 'NF && $1 !~ /^#/' workspace/lint/whitelists/model_pins.txt workspace/lint/whitelists/prompts.txt -> 0 data lines"
  - "./vol exec python workspace/lint/lint_model_pins.py -> PASS with model_pins.txt header-only (the 2 SANCTIONED_SITES pass because they are structurally exempt, NOT whitelisted); ./vol exec python workspace/lint/lint_prompts.py -> PASS with prompts.txt header-only"
  - "./vol exec python workspace/lint/lint_all.py -> EXIT_CODE=0 on S-B AND sentinel EXIT_CODE=0 on S-A (lint-workspace task or vol.cmd)"
memory_refs: []
constraints:
  - "verify cited path:line against the live tree; Plan 05 already cleared the non-sanctioned prose (AGENTS.md, workflows/, personas/, policy/index.md) — but policy/subagent_protocol.md and .github/copilot-instructions.md Rule 9 LEGITIMATELY keep the raw literal (they are SANCTIONED_SITES, structurally exempt); do NOT touch those two, and if a literal remains in any OTHER Plan-05 prose site STOP blocked (Plan 05 regression)"
  - "the 5 research plans in workspace/plans/ are read-only"
  - "prompt frontmatter pins (the 18 kept by Tasks 3/4/5) are NOT literals to remove — they are the sanctioned exception lint_model_pins already allows"
  - "the ONLY lint edits are burning the two whitelist FILES (workspace/lint/whitelists/{model_pins,prompts}.txt) to header-only — NEVER edit lint_model_pins.py / lint_prompts.py .py logic"
depends_on: ["wfo-07-1", "wfo-07-2", "wfo-07-3", "wfo-07-4", "wfo-07-5", "wfo-07-6", "wfo-07-7", "wfo-07-8", "wfo-07-9", "wfo-07-10", "wfo-07-11"]
```

- [ ] **Step 1 (red — inventory):** `grep -rn 'Opus 4.6\|claude-opus-4-6' skills/*.md workspace/learning/ workspace/docs/user-manual.md memory/_dormant/sys/secdb-ecosystem.md` → expected per freshness §7: 11 hits in the 6 flat skill files, 2 in `workspace/learning/README.md`, 19 display + 2 slug in `vol-learning-framework-design.md`, 1 in `user-manual.md`, 1 in `secdb-ecosystem.md` (36 prose total; record live counts).
- [ ] **Step 2 (implement content):** Replace every occurrence:
  - Prose sentences: `Claude Opus 4.6` → `the pinned subagent model (see \`policy/subagent_protocol.md\`)`.
  - Frontmatter-style `model: Claude Opus 4.6` lines inside the 6 flat guide files (inert — guide skills are not prompts): delete the line.
  - Both slug occurrences in `vol-learning-framework-design.md` (old :1079/:1175): replace the whole identifier phrase with `the pinned model (see \`policy/subagent_protocol.md\`)` — do NOT keep a labeled slug (the lint must pass with the whitelist file burned to header-only; supersedes AW-G5's label-only option).
- [ ] **Step 3 (implement lint strictness, red-then-green):**
  1. Burn both grandfather whitelist FILES to header-only: reduce `workspace/lint/whitelists/model_pins.txt` and `workspace/lint/whitelists/prompts.txt` to their leading `#` header comment with 0 data lines (delete every data line; keep the header). NEVER edit `lint_model_pins.py` / `lint_prompts.py` — the check logic is already strict, so emptying the whitelist file is exactly what flips it strict. The two SANCTIONED_SITES (`policy/subagent_protocol.md`, `.github/copilot-instructions.md`) still pass because they are structurally exempt, not whitelisted.
  2. **Red proof:** plant `.github/prompts/zz probe.prompt.md` (spaced name, `model: GPT-5`, verbless body) and a line `Claude Opus 4.6` in a new `workspace/tmp/zz-probe.md`... note `workspace/tmp/` is gitignored/skipped — instead temporarily append the literal to `workspace/docs/user-manual.md`. Run both lints → **FAIL** (filename + pin mismatch + raw literal). Paste outputs.
  3. Delete the planted prompt file and revert the planted literal line. Run both lints → **PASS**.
- [ ] **Step 4 (green — plan-level gate):** `./vol exec python workspace/lint/lint_all.py` → full PASS on S-B; on S-A run the `lint-workspace` task (or `vol.cmd exec python workspace/lint/lint_all.py`) and read the sentinel `OUTPUT_FILE=` → `EXIT_CODE=0`. Record the repo-wide grep from acceptance line 2.
- [ ] **Step 5 (commit):** `chore(framework): finish model-literal sweep; burn model_pins/prompts whitelists to header-only (lints go strict)`

---

## 5. Configs / experiments

None — this plan ships no runnable experiments, no YAML configs, and touches nothing under `workspace/configs/` or `workspace/research/trials.yaml`. The only new files are documentation/registry artifacts (INDEX.md, endpoints.md, the relocated audit record) and the stub prompt.

---

## 6. Orchestrator prompt

```
/execute Implement Plan 07 (Prompt & Skill Hygiene) from workspace/plans/copilot-workflow-overhaul/plan-07-prompt-skill-hygiene.md

Precondition check: Plan 06 gate passed — run `./vol exec python workspace/lint/lint_all.py`
(must be full PASS, incl. the memory-budget and broken-refs checks Plan 06 made green) and
confirm Plans 01-06 are merged to master. Also confirm no research /execute session is live.
Decision to collect from the user BEFORE Wave 3: Task 6 roster decision — default (b) sanction
the guide-only flat-skill variant; alternative (a) convert the 6 files to UPPER_SNAKE dirs.
Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.
Branch: chore/wf-overhaul-07-prompt-skill-hygiene off master.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1 (parallel, max 4): wfo-07-1, wfo-07-4, wfo-07-7, wfo-07-11
  Wave 2 (parallel, max 5): wfo-07-3, wfo-07-5, wfo-07-8, wfo-07-9, wfo-07-10
  Wave 3 (parallel, max 2): wfo-07-2, wfo-07-6
  Wave 4: wfo-07-12
Waves are disjoint write_scopes; respect each packet's depends_on. Each subagent: docs/config
tasks are TDD-exempt but must paste red-state and green-state command output; Tasks 6 and 12
show planted-violation red then green for the lint changes; terminal isolation via
./vol exec / vol.cmd exec + kill_terminal EXIT GATE; return the 00-overview §5.2 return
contract verbatim.
Retry a blocked/partial subagent once with a refined packet, then escalate with both attempts'
evidence.
After Wave 1, Task 1 Step 5: ask the user to live-verify /fix-it in a fresh chat and paste the
observation into the MR description under 'AW-37 hypothesis check'.
Integration verification (orchestrator, after all tasks):
  1. ./vol exec python workspace/lint/lint_all.py            -> full PASS (S-B)
  2. run_task lint-workspace (or vol.cmd exec equivalent)     -> sentinel EXIT_CODE=0 (S-A)
  3. Task 2's bijection one-liner                             -> BIJECTIVE 34==34
  4. grep -rln 'Opus 4.6' --include='*.md' . | grep -v -e '\.prompt\.md' -e 'policy/subagent_protocol.md' -e '.github/copilot-instructions.md' -e 'workspace/plans/' -> 0
     (the two SANCTIONED_SITES + prompt frontmatter + suite plan files are the only permitted homes)
  5. ./vol test (S-B)                                         -> green (no src/ change expected;
     confirms commit_task.py edit broke nothing)
Update workspace/research/weekly-progress.md (Shipped section, one line).
MR description must contain: AW-37 hypothesis check result, Task 7 before/after byte
measurement, Task 12 strict-lint red/green evidence. MR title human-generic
(e.g. "Prompt registry, dispatcher cleanup, and skill-roster reconciliation").
Do NOT start Plan 08.
```

---

## 7. Acceptance gate → Plan 08

Verbatim from 00-overview §2, Plan 07 row — all four must hold before Plan 08 starts:

> **Model-pin-constant lint + prompts lint pass; `/fix-it` invocation verified live (AW-37 hypothesis check recorded); `.github/prompts/INDEX.md` complete in both directions; skill roster reconciled (counts match on-disk).**

Operationally:
1. `./vol exec python workspace/lint/lint_model_pins.py` and `./vol exec python workspace/lint/lint_prompts.py` → PASS **with both whitelist files `workspace/lint/whitelists/{model_pins,prompts}.txt` burned to header-only** (strict state) — `lint_model_pins.py` passes BECAUSE `policy/subagent_protocol.md` and `.github/copilot-instructions.md` are structurally exempt via `SANCTIONED_SITES` (not whitelisted), plus full `lint_all.py` PASS on S-A and S-B.
2. The MR description contains the pasted live `/fix-it` observation (AW-37 hypothesis check), including what `/fix it` now resolves to.
3. Task 2's bijection check prints `BIJECTIVE 34==34` (INDEX → directory and directory → INDEX).
4. `lint_registry_drift.py` green with `policy/implementation_boundary.md` reading "54 (48 directories + 6 guide-only)" and `skills/INDEX.md` carrying all 54 rows; `skills/ssp_helpers.py` gone.

**What Plan 08 consumes from this plan:** the strict lint state (its closure task re-runs `lint_all.py` and `check_coverage.py` asserting AW-G3/11/18/23/25/30/31/37/43/45/47/50/51/52 = disposed by Plan 07 tasks); the reconciled 54-skill roster and guide-only sanction (Gate E's tutoring-relocation decision starts from the 6 guide files as a clean, linted set); `.github/prompts/INDEX.md` (any Plan 08 prompt removal/relocation must update it or `lint_prompts` goes red — the registry is now load-bearing).
