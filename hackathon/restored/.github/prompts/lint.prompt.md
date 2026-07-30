---
description: "Run native Slang lint on one or more scripts to check for errors and warnings"
model: Claude Opus 4.6
---

Run native Slang lint on the following scripts: ${input}

## How to invoke

Use the **task-based workflow** from the SLANG_LINT skill (`skills/SLANG_LINT/SKILL.md` § Task-Based Execution).
Read the skill FIRST — it has the complete `run_task` workflow that avoids Allow prompts.

**Never use `run_in_terminal` or ad-hoc task definitions for lint** (see `memory/ref/vscode-tasks.md` rule E3 — the ad-hoc-task API was retired 2026-07, AW-09). Always use `run_task` with `lint-slang`.

## Options to consider

- **Default backend** (`@LIBSlang::Lint`): fast, covers type issues, collisions, unused vars
- **Precommit backend** (`@ScriptVal::PreCommit Check Lint`): add `--precommit` — full precommit pipeline (unused links, deeper cross-library checks); slower but matches ScriptReview's lint
- **Custom timeout**: add `--timeout 600` for large script sets (default: 300s)
- **Custom source**: add `--source "!NYC_Eq_Vol_Source;PS"` to override the default source chain

## Interpreting results

- **Status-1**: errors — MUST be fixed before declaring done
- **Status-2**: warnings — MUST be fixed before declaring done
- **Status-3 / Status-3.75**: informational — acceptable, no action needed
- **Gate: PASS** means 0 Status-1 and 0 Status-2 issues

## Important rules

- ALWAYS poll with `Start-Sleep 5` — never sleep longer than 5 seconds between checks
- If lint reports issues, fix them using the SLANG_EDIT skill, then **re-run lint** to confirm
- Cascading fixes are common: a LintPragma fix may need a blank line after it, an alignment fix may break neighbor alignment — always re-lint after every fix round
- After ALL edits are done, run lint one final time and confirm **0 Status-1, 0 Status-2** before declaring done
