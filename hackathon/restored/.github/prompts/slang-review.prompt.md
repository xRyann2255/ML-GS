---
description: "Create or update a Slang ScriptReview for code review submission"
model: Claude Opus 4.6
---

Create or update a Slang ScriptReview: ${input}

**Python path:** Resolve using the PYTHON_PATH skill (`skills/PYTHON_PATH/SKILL.md`). Use the resolved path as `PYTHON` below.

## AUTO-FILL WORKFLOW (MANDATORY for new reviews)

Before creating a review, you MUST automatically derive all required fields by comparing the userdb version with production. **Never ask the user for subject, description, or driver-for-change** — infer them from the diff.

### Step 1: Get diffs for each script

For each script in `--scripts`:

1. **Read userdb version** — via VFS: `read_file("slang:/!NYC UserDBs!home!{kerberos}!{db}/{script}.s")`
2. **Read prod version** — via VFS: `read_file("slang:/!NYC_Source/{script}.s")`
3. **Compare** — identify what changed (added functions, modified logic, new stubs, etc.)

If VFS is unavailable, use the task-based secexpr read (see SLANG_EDIT SKILL.md).

If the script is brand new (doesn't exist in prod), note it as "New script".

### Step 2: Run lint (task-based, zero Allow)

Run SLANG_LINT on all scripts using the task-based workflow (see SLANG_LINT SKILL.md):
- Write args to `workspace/tmp/slang_lint_args.json` (fixed path per the `lint-slang` task definition; include a `run_id` slug in the JSON body, pattern `[a-z0-9-]+`)
- Launch via `run_task` with `lint-slang`
- Read `workspace/tmp/slang_lint_results_{run_id}.json`, where `{run_id}` is the `run_id` field you wrote inside `slang_lint_args.json` (omit `run_id` → `slang_lint_results.json`) — `run_task` blocks until done, no polling needed
- Extract gate result and issue counts

### Step 3: Auto-fill fields from the diff

| Field | How to derive |
|-------|---------------|
| **--subject** | Summarize the main change in plain English (max ~60 chars). E.g. "Add RegTest for Fut Netting rolls", "Fix Boxes PNL calculation" |
| **--description** | List the key changes per script (bullet points). Focus on what was added/modified/removed. |
| **--driver-for-change** | Infer the motivation: "New feature", "Bug fix", "Refactor", "Add test coverage", etc. |
| **--testing-description** | Format lint results: `"Lint pass 0 S1 0 S2. FasTest N passed 0 failed 0 errors."` Use simple ASCII only — no `()`, no `:`, no `:=`. |

### Step 4: Show the user a summary and proceed

Display a brief summary of the auto-filled fields to the user, then proceed with creating the review. Do NOT wait for confirmation unless something looks wrong.

---

## Create a new review

```powershell
PYTHON skills/SLANG_REVIEW/src/review.py --db "~{kerberos}!{db}" --scripts "SCRIPT1" "SCRIPT2" --subject "SUBJECT" --description "DESCRIPTION" --driver-for-change "REASON" --testing-description "TESTING NOTES" --timeout 600
```

## Refresh an existing review (new version with updated diffs)

```powershell
PYTHON skills/SLANG_REVIEW/src/review.py --db "~{kerberos}!{db}" --scripts "SCRIPT1" "SCRIPT2" --review "Review YYYYMMDD 6010-NNNNNNNs*" --testing-description "TESTING NOTES" --timeout 600
```

## Update metadata only (no diff refresh)

```powershell
PYTHON skills/SLANG_REVIEW/src/review.py --db "~{kerberos}!{db}" --scripts "SCRIPT1" "SCRIPT2" --review "Review YYYYMMDD 6010-NNNNNNNs*" --metadata-only --testing-description "TESTING NOTES"
```

## Required fields for new reviews

- **--scripts** — ALL scripts in the review (always required)
- **--subject** — mail subject / title (auto-derived from diff)
- **--description** — what changed (auto-derived from diff)
- **--driver-for-change** — why the change was made (auto-derived from diff)
- **--testing-description** — lint and FasTest results (auto-derived from lint run)

## Required fields for refresh

- **--scripts** — full list of ALL scripts (must match review)
- **--review** — existing review name (e.g. `"Review 20260409 6010-2223921S*"`)
- **--testing-description** — updated test results

## Important rules

- **--timeout 600** for reviews with 3+ scripts (default 300s is often insufficient)
- **testing-description**: Use simple ASCII only — no `()`, no `:`, no `:=`. Good: `"Lint pass 0 S1 0 S2. FasTest 6 passed 0 failed 0 errors."` Bad: `"FasTest: 6 passed (0 failed)"`
- **NEVER run `Get-Process secexpr | Stop-Process -Force`** — this kills secexpr processes from ALL VS Code sessions, crashing other windows (REPL code=255). Only kill secexpr by PID if you started it and it hung.
- After creating, verify **delta shame is zero** in the review URL
- Review URL: `https://www.epssp.site.gs.com/ssps/ProdSource/ScriptReview?Name=Review+...`
- Unsubmitted reviews: `https://www.epssp.site.gs.com/ssps/ProdSource/MyScriptReviews#unsubmitted-reviews`

## Post-Create: Handoff Prompt (MANDATORY after successful create)

After a successful review creation (gate=PASS), **ask the user** if they want to generate a handoff prompt that another person can use to **recreate the same ScriptReview** from their own session.

If the user says yes, output a self-contained text block (fenced in triple backticks) that serves as an actionable prompt — NOT a review summary. The recipient should be able to paste this into their agent and get the same review created. Do NOT include the review URL or review name — those belong to the original author's review. The prompt MUST start with an instruction to use the `/slang-review` prompt so the recipient's agent loads the correct skill.

```
Use /slang-review to create a new ScriptReview with the following details:

UserDB: ~{kerberos}!{db}
Scripts:
  - {script1}
  - {script2}
  - ...

Subject: {subject}
Description: {description}
Driver for change: {driver-for-change}
Testing: {testing-description}
```

Fill every field from the values actually used during review creation. Include ALL scripts from `--scripts`.

---

## Instructions

Based on "${input}", determine the action:
- If the user provides a review name (e.g. "Review 20260409 6010-..."), **refresh** it
- If the user says "update metadata", use **--metadata-only**
- Otherwise, **create** a new review using the AUTO-FILL WORKFLOW above
- NEVER ask for subject, description, or driver-for-change — derive them from diffs
- After completion, report the review URL and remind to check delta shame
- After a successful create, ask if the user wants a handoff prompt (see Post-Create section)
