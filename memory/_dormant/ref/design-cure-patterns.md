---
created: 2026-04-14
updated: 2026-04-23
confidence: high
tags: [design, cure, audit, patterns, workflow, session-state]
status: active
relates:
  - slang/lint-edit.md
---

# Design Cure Patterns — Recurring Gap Types

Findings from design compliance audits (`/cure` workflow). Use this to accelerate future audits.

## Recurring Gap: New-Workflow Checklist Omissions

When a new workflow is added, multiple cross-references must be updated atomically. Common misses:

1. **`session-state.md` `active_workflow` enum** — must list every workflow file. Easy to forget when adding a workflow after the initial batch.
2. **Allowed-persona lists in workflow phases** — a persona can exist in `INDEX.md` but never appear in any workflow's allowed-persona table, making it unreachable.
3. **Decision Tree in `workflows/INDEX.md`** — step 5 pattern list must cover every non-default workflow.
4. **Quick Reference table in `workflows/INDEX.md`** — must have a row for every workflow. The Decision Tree can route correctly while the Quick Reference is incomplete.
5. **Memory paths in workflow phases** — must match actual `memory/INDEX.md` paths. After a reorg (e.g. `supports/` → `domain/`, `ref/slang-*` → `slang/*`), all workflows referencing the old paths silently fail to load.
6. **Skill-name abstraction** — workflows must not embed concrete skill identifiers (e.g. `SLANG_EDIT`, `SLANG_GLIMPSE`, `CVS`). Use generic descriptions ("read scripts", "search codebase", "check history"). Concrete names couple the workflow to skill implementation details.
7. **Tool flags and CLI details** — workflows must not embed concrete tool flags (`secexpr --safe`, `edit.py`), lint status codes (`Status-1`/`Status-2`), or filenames (e.g. AGENTS.md). These belong in policy or memory, not orchestration.
8. **Persona routing leakage** — personas must not embed "route to X" dispatch instructions (e.g. "route to PATHFINDER"). Scope boundary notes ("out of scope for this persona") are OK; explicit cross-persona dispatch is not.
9. **Decision-tree prompt-command alignment** — `workflows/INDEX.md` step 1 must list every `/prompt` command from `policy/routing.md`. After adding a new prompt, verify the INDEX decision tree mirrors it.
10. **`<effort_gate>` sub-section** — every persona must include an `<effort_gate>` within `<constraints>`. R12 found 4 remaining violations (DOCSMITH missing, OPERATIVE wrong tag name `<reasoning_effort>`, STRATEGOS missing, TRACEHOUND missing) and fixed all. 16/16 now compliant. Still not lint-enforced — manual audit required.
11. **`routing.md` step-1 completeness** — `policy/routing.md` step 1 must list every `/prompt` command. R12 found `/support` missing despite the prompt file and INDEX.md entry existing.
12. **Cross-persona dispatch in persona docs** — personas must not name specific dispatch targets (e.g. "Escalate upward to STRATEGOS", "hands to FORGE"). Use generic language ("escalate upward", "diagnosis and handoff only"). R13 found PRESCRIBER scenario_handling and INDEX.md TRACEHOUND row.
13. **§4.2 transition-table determinism** — every transition table with 2+ conditions that can be simultaneously true MUST declare precedence ordering. R14 found 11/13 workflows had overlapping conditions. Fix: add `> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.` above the table and reorder rows (success first, fallback last). R15 found 4 remaining tables in cure.md (TRIAGE), fix.md (DIAGNOSE), investigate.md (GATHER), learn.md (DISTILL) — all fixed.
14. **Read-only persona tool lists** — read-only personas must not list `run_in_terminal` or other write/execute tools. R14 found SCRIBE listing `run_in_terminal` despite read-only declaration. R15 found 5 personas (AUDITOR, ORACLE, PATHFINDER, SENTINEL, TRACEHOUND) listing `run_in_terminal` for "read-only git" ops — all removed.
15. **Dispatch tables are §4.7 exceptions** — `keyword-dispatch.md` and `session-state.md` use concrete skill names by design (routing dispatch, not orchestration). Mark with HTML design exception comments rather than genericizing.
16. **`<verification_loop>` in `<execution_loop>`** — design.md §3 specifies "success criteria, verification checklist." R15 found 6 personas (ORACLE, MAESTRO, OPERATIVE, PRESCRIBER, SCRIBE, SENTINEL) with `<success_criteria>` but no `<verification_loop>` — all added. R18 found FORGE and BUDGETEER regressed (used `<verification_preflight>` instead of `<verification_loop>`) — fixed. 16/16 now compliant.
17. **Transition-table precedence stragglers** — R16 found `support.md` had 4 tables (TRIAGE, DIAGNOSE, RESOLVE, VERIFY) and `review.md` had 1 table (SCOPE) without precedence declarations despite all other workflows being compliant since R14/R15. All 5 fixed.
18. **§4.7 domain leakage in support.md** — R19 found support.md embedded Slang-specific routing (`"fix requires Slang script edit"`), action steps (`"If the fix involves Slang script changes, follow all mandatory gates"`), and constraints (`"mandatory lint and RegTest gates"`). Fix: genericize to technology-neutral language (`"code changes"`, `"mandatory gates per global policy"`) and let `fix.md` own domain-specific gates.
19. **Read-only personas referencing terminal commands** — R19 found SENTINEL (`git diff`) and TRACEHOUND (`git log`/`git blame`) referencing commands unavailable to read-only personas. Fix: rephrase to tool-agnostic language (`"available diff and search tools"`, `"check recent changes to suspect files"`).
20. **Missing optional `<style>` subsections** — R19 found MAESTRO and OPERATIVE missing `<anti_patterns>`, `<scenario_handling>`, `<final_checklist>` in `<style>`. Added minimal, role-appropriate content to both.
21. **Dead tool entries** — R19 found SCRIBE listing `read_file`/`grep_search` "for internal codebase context" despite internal questions being declared out-of-scope. Removed dead entries.
22. **INDEX.md step-1 `/support` omission** — R20 found `policy/routing.md` step 1 lists `/support → support.md` but `workflows/INDEX.md` decision tree step 1 was missing it. Added.
23. **`<success_checklist>` naming** — R20 found FORGE and BUDGETEER used `<success_checklist>` instead of `<success_criteria>` (the §3-standard tag name). Renamed both.
24. **FORGE missing `<final_checklist>`** — R20 found FORGE `<style>` had no `<final_checklist>`. Added minimal role-appropriate checklist.
25. **Phase header vs Allowed Personas table mismatch** — R22 found `team.md` EXECUTE phase header stated "Workers (FORGE default, specialist as needed)" while the Allowed Personas table listed OPERATIVE as primary and FORGE as fallback. Fix: align header to match table ("OPERATIVE (primary), FORGE (fallback), specialist as needed"). Always verify freeform header summaries against their authoritative tables.
26. **Non-tool behavioral rules in `<tools>` section** — R22 found `strategos.md` `<tools>` contained ask-gate behavioral rules ("Never ask ... unless") alongside actual tool entries. Fix: remove non-tool lines; behavioral rules belong in `<ask_gate>` or `<constraints>`. `<tools>` must only list tool names.
27. **ABORT/exception blocks need formal transition tables** — R22 found `team.md` ABORT re-entry decision used narrative bullets instead of a §4.2-compliant transition table with precedence. Fix: convert to table with condition → action rows and `> **Precedence:** ...` block. Applies to any workflow phase that decides between multiple recovery paths.
28. **Internal section contradiction (effort defaults)** — R22 found `analyst.md` `<effort_gate>` declared "Default effort: medium" while `<verification_loop>` said "Default effort: high (thorough gap analysis)." Fix: reconcile to single consistent statement. When two sections reference the same parameter, they must agree.
29. **`<style>` subsection completeness (7 personas)** — R24 found AUDITOR, BUDGETEER, ORACLE, QUARTERMASTER, SCRIBE, SENTINEL, STRATEGOS missing one or more of `<anti_patterns>`, `<scenario_handling>`, `<final_checklist>`. These are HIGH per §3 (required structure). Fix: add minimal role-appropriate content for each missing subsection. Also removed non-standard `<escalation>` from SCRIBE (content moved to scenario_handling).
30. **Behavioral rules in `<tools>` (2 personas)** — R24 found PATHFINDER ("never read large files whole", "Prefer the right tool") and TRACEHOUND ("Execute all evidence-gathering in parallel") embedding behavioral/execution rules in `<tools>`. Fix: remove non-tool lines; behavioral rules belong in `<constraints>` or `<execution_loop>`.
31. **§4.7 domain examples in fix.md RECON** — R24 found fix.md RECON memory-scan action included domain-specific file path examples (`slang/best-practices.md`, `sys/atlas-brazil.md`). Fix: remove parenthetical examples; the instruction is INDEX.md-driven.
32. **Inline governance concepts in support.md** — R24 found support.md constraints referencing "safe-mode policy" (a domain-specific governance concept). Fix: replace with generic `policy/` reference.
33. **Decision-tree step-5 plan.md keywords** — R24 found `workflows/INDEX.md` step 5 missing plan.md keyword triggers ("break down", "decompose", "scope this") from `keyword-dispatch.md`. Fix: add explicit row before the fallback.

## False-Positive Watch

- The Decision Tree in `INDEX.md` can span many lines. Read the full step-5 block before declaring a workflow missing — partial reads cause false positives (e.g. `learn.md` was falsely flagged because the tree was only partially read).
- **§4.4 memory loading (parameterized declarations):** All 13 workflows use "Load per INDEX.md lookup tables" style declarations. This is intentional — not a violation. Only truly implicit "load what you need" without referencing INDEX is a violation.
- **§4.8 error handling (global):** All 13 workflows use a single error-handling section referencing the 4-class model globally. This is by-design convention. Only missing the 4-class model reference entirely is a violation.
- **INDEX.md step 5 coverage:** Steps 1-4 route `execute`, `interview`, `lightweight`, and `team` via prompt commands, signals, and stream detection. Step 5 only needs to cover keyword-triggered workflows. Do not flag these 4 as missing from step 5.
- **§4.2 doctor.md design-doc references:** DOCTOR's `<identity>` and `<execution_loop>` reference `design.md`, `personas/design.md`, `workflows/design.md` — these are operational inputs (the spec it audits against), not domain knowledge. The severity model is reasoning style. Not a violation.
- **§4.2 quartermaster.md INDEX/extension references:** QUARTERMASTER references `skills/INDEX.md` and `memory/INDEX.md` as primary data sources — these are operational inputs. File extensions (.s, .py, .ts) in execution_loop are LOW at most (style, not domain knowledge).

## Lint Coverage Gaps

These design rules are NOT enforced by `design_lint.py` today (manual audit required):

| Rule | Source | Gap |
|------|--------|-----|
| INDEX.md entry exists for every persona | `personas/design.md §4.1` | Not checked |
| Write-tool blocking declared on read-only personas | `personas/design.md §4.5` | Not checked |
| Conflict rules documented for mutually exclusive personas | `personas/design.md §4.6` | Not checked |
| `_protocol.md` referenced in first paragraph | `workflows/design.md §4.1` | Not checked |
| State machine present in workflow | `workflows/design.md §4.2` | Not checked |
| `active_workflow` enum in `session-state.md` matches workflow file list | Implicit | Not checked |
| Quick Reference table row for every workflow | `workflows/design.md §4 Rule 10` | Not checked |
| Memory paths in workflow phases match `INDEX.md` | `workflows/design.md §4 Rule 4` | Not checked |
| No concrete skill names in workflow phase actions | `workflows/design.md §4 Rule 7` | Not checked |
| `<effort_gate>` present in every persona | `personas/design.md §3` | Not checked |
| No cross-persona dispatch in persona docs ("route to X") | `personas/design.md §4.3` | Not checked |
| Transition-table precedence declared on overlapping conditions | `workflows/design.md §4.2` | Not checked |
| Read-only persona tool lists exclude write/execute tools | `personas/design.md §4.5` | Not checked |\n| `<verification_loop>` present in every persona's `<execution_loop>` | `personas/design.md §3` | **Check 15** (`persona-verification-loop`) |
| INDEX.md step 1 decision tree covers all `/prompt` commands | `workflows/INDEX.md` alignment | Not checked |
| Memory loading spec must reference INDEX.md (not implicit) | `workflows/design.md §4 Rule 4` | Not checked |
| No inline governance/policy rule content in workflow actions | `workflows/design.md §4 Rule 7` | Not checked |

## Automated Checks (design_lint.py)

As of R18, `design_lint.py` has 25 checks. Notable additions:

- **Check 9 — memory-domain:** ERROR if any `memory/` subfolder is not a valid domain (per `meta/guide.md`).
- **Check 10 — memory-index-coverage:** WARN if a memory file has no INDEX entry; ERROR if INDEX references a missing file.

These reduce manual audit surface for memory governance. The "Lint Coverage Gaps" table above lists rules still requiring manual inspection.



## Pre-Existing Lint Issues (Not Cure Scope)

- `ml-vol-estimator.code-workspace` — structural ERROR (unrecognised top-level entry). Housekeep scope, not cure.
- `skills/DIRGET/SKILL.md` — WARN (82 lines, no memory ref). Housekeep scope.
- `skills/PROCMON_LOGS/SKILL.md` — WARN (81 lines, no memory ref). Housekeep scope.
- `skills/SECDB_INSPECT/SKILL.md` — WARN (118 lines, no memory ref). Housekeep scope.

## Recurring Gap: Persona Sub-Section Completeness

New personas are often created with minimal sub-sections. Check for:
- Missing `<effort_gate>` (now required per §3)
- Missing `<anti_patterns>` / `<scenario_handling>` / `<final_checklist>` in `<style>` (standard, not required)
- Read-only personas without formal "Write and Edit tools are blocked" declaration
- `personas/design.md §4.5` enumerated list must be updated when a new read-only persona is added
25. **§4.4 implicit memory specs** — R22 found 3 workflow phases (debug.md HYPOTHESIZE, interview.md GATHER, housekeep.md APPLY) using implicit memory declarations ("Load relevant code context", "Load domain-relevant memory to ask informed questions", "Skill-specific memory as needed") without referencing INDEX.md. Fix: replace with parameterized INDEX.md lookup declarations.
26. **§4.7 domain-conditional memory in support.md** — R22 found support.md DIAGNOSE listing 4 specific memory files with domain-conditional guards ("if issue involves VTs", "if issue involves Slang"). Fix: replace with parameterized INDEX.md lookup. Also genericized "inspect SecDB state" to "inspect application state".
27. **§4.7 language-specific CONFORM in cure.md** — R22 found cure.md CURE step 3 hard-coding .s file handling, naming memory/slang/ paths, and specifying re-lint mechanics. Fix: genericize to "audit against applicable domain conventions loaded in memory."
28. **§4.7 governance principles in learn.md / housekeep.md** — R22 found two workflows embedding governance rule content (learn.md DISTILL/PERSIST, housekeep.md APPLY) instead of referencing the governance guide. Fix: replace inline enumerations with "per governance guide" references.
