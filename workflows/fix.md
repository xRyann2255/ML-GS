# Workflow: Fix

Implements [_protocol.md](_protocol.md). Structured code-fix pipeline — diagnose the issue, prescribe a validated fix, implement, test, and audit.

---

## Entry Conditions

Enter when:
- User explicitly uses `/fix it`.
- Task pattern matches: "fix", "fix bug", "fix code", "fix this", "fix the issue", "patch", "hotfix", "broken code".
- Routing policy classified task as fix.

---

## Complexity Gate

At the end of DIAGNOSE, classify the fix:

| Classification | Criteria | Path |
|----------------|----------|------|
| **TRIVIAL** | Single file, obvious fix, no side-effects, root cause is localized | DIAGNOSE → RECON → IMPLEMENT → REVIEW → REPORT → DONE |
| **STANDARD** | Multi-file, risk of regression, edge cases, or non-obvious fix | DIAGNOSE → RECON → PRESCRIBE → IMPLEMENT → TEST → REVIEW → AUDIT → REPORT → DONE |

DIAGNOSE must record the classification in its checkpoint. Default to STANDARD when uncertain.

---

## State Machine

### Standard Path

```
DIAGNOSE → RECON → PRESCRIBE → IMPLEMENT → TEST → REVIEW → AUDIT → REPORT → DONE
  ↓ (won't fix)          ↓ (escalate)   ↑←←←←←←←←←↓ (failed)  ↓ (failed)
  REPORT               plan.md        IMPLEMENT (loop)       DIAGNOSE (restart)
```

### Trivial Path

```
DIAGNOSE → RECON → IMPLEMENT → REVIEW → REPORT → DONE
  ↓ (won't fix)         ↑←←←←←←↓ (findings)
  REPORT              IMPLEMENT (loop)
```

On the trivial path, MODEL-BUILDER absorbs planning (single-file, obvious fix) and TEST is folded into IMPLEMENT's verification preflight. AUDIT is skipped (low risk of process deviation). RECON runs on both paths — it is lightweight and its leverage map directly accelerates IMPLEMENT by front-loading skill/memory discovery.

### DIAGNOSE

**Persona:** TRACEHOUND
**Memory:** Load `person/user.md` + domain-relevant P1 files per `INDEX.md` lookup tables.

**Actions:**
1. **Capture symptom** — exact error, unexpected behavior, reproduction steps.
2. **Reproduce** — run the failing command, read logs, check output. Record reproduction evidence.
3. **Hypothesize** — generate 2–3 ranked hypotheses for the root cause. For each, identify what evidence would confirm or refute it.
4. **Gather evidence** — read code, check logs, run diagnostics. Record evidence per hypothesis: `confirmed`, `refuted`, `inconclusive`.
5. **Narrow** — identify the confirmed root cause with evidence. Document: affected files, symptom, root cause, impact.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| Root cause identified, classified TRIVIAL | → RECON (trivial path) |
| Root cause identified, classified STANDARD | → RECON |
| Root cause identified but issue is by-design or non-actionable | → REPORT (“won’t fix” verdict) |
| Issue is a design violation, not a code bug | → Yield to `cure.md` |
| Insufficient context to diagnose | → Yield to `interview.md` for more info, resume DIAGNOSE on return |

Checkpoint: record symptom, root cause, affected files, evidence.

### RECON

**Constraints:** Read-only scan. Single-pass, no loops. Never writes files.
**Memory:** Reload DIAGNOSE checkpoint (root cause, affected files). Load `skills/INDEX.md` and `memory/INDEX.md`.

**Purpose:** Scan the agent's own asset inventory — skills, memory, and prior experience — to build a leverage map that accelerates downstream phases. This prevents ad-hoc discovery during PRESCRIBE and IMPLEMENT, reducing context switches and wasted tool calls.

**Actions:**
1. **Skill scan** — match root cause domain, affected file types, and involved systems against `skills/INDEX.md`. List skills that can accelerate implementation, testing, or verification (e.g., editing tools for script files, lint tools for gate checks, version history for context, codebase search for reference patterns).
2. **Memory scan** — match against `memory/INDEX.md` priority and load-trigger columns. List P1/P2 memory files whose triggers match the task context.
3. **Pattern recall** — check user memory and session memory for prior encounters with similar root causes, domains, or file types. Surface known gotchas, failed approaches, or proven patterns.
4. **Emit leverage map** — produce a compact ranked output:
   - **Skills to invoke** — which skills, in which phase (IMPLEMENT, TEST), and why.
   - **Memory to load** — which files, in which phase (PRESCRIBE, IMPLEMENT), and the specific knowledge they provide.
   - **Known patterns** — gotchas, prior fixes, or conventions that apply.
   - **Tools not needed** — explicitly note irrelevant skills to prevent unnecessary loading downstream.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| Leverage map produced (standard path) | → PRESCRIBE |
| Leverage map produced (trivial path) | → IMPLEMENT |
| No relevant skills or memory found (standard path) | → PRESCRIBE (empty map) |
| No relevant skills or memory found (trivial path) | → IMPLEMENT (empty map) |

Checkpoint: record leverage map (skills, memory files, patterns, exclusions).

### PRESCRIBE

**Constraints:** One-pass tactical plan. Smallest diff. Self-validate. No interviews. No code writes. Escalate at 4+ files.
**Memory:** Load memory files listed in RECON leverage map. Reload DIAGNOSE checkpoint (symptom, root cause, affected files) and RECON checkpoint (leverage map).
**Path:** Standard only (trivial path skips this phase).

**Actions:**
1. Ingest DIAGNOSE checkpoint (symptom, root cause, affected files, evidence) and RECON checkpoint (leverage map — skills, memory, patterns).
2. Inspect affected code. Identify the minimal change set. Use RECON's skill recommendations to inform which tools are available for implementation.
3. Design a fix strategy: what changes, in which files, in what order. List preconditions and side-effects.
4. Self-validate: does the plan address the root cause (not just symptoms)? Edge cases covered? Downstream regressions checked? AC sufficient?
5. Draft **acceptance criteria (AC)** — at minimum: (a) original symptom no longer reproduces, (b) existing tests pass, (c) lint passes, (d) changed files conform to applicable domain conventions.
6. Emit validated plan with flagged concerns (if any).

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| Plan validated (self-validation passes or concerns flagged) | → IMPLEMENT |
| Diagnosis ambiguous — two plausible fixes with materially different outcomes | → Escalate to user with options |
| Fix requires 4+ files across subsystems or architectural change | → Escalate: yield to `plan.md` for full planning, resume at IMPLEMENT on return |

Checkpoint: record plan (steps, files, risk assessment, acceptance criteria, flagged concerns).

### IMPLEMENT

**Persona:** MODEL-BUILDER
**Memory:** Load memory files from RECON leverage map. On trivial path, also reload RECON checkpoint directly (no PRESCRIBE intermediary).

**Actions:**
1. **TEST-FIRST gate** — before applying the fix:
   a. Write a test that reproduces the diagnosed symptom (from DIAGNOSE checkpoint).
   b. Confirm the test fails (red). This becomes the regression guard.
   c. Skip for non-code files (config, docs, memory).
2. Track each planned change as a todo item — per-step progress. Reference RECON leverage map for which skills to invoke at each step.
3. Per todo item: apply the change (using RECON-identified skills) to make the failing test pass (green) → run lint → self-check against plan → mark complete.
4. **CONFORM** — for each changed file, audit against domain-specific conventions per the active persona's execution loop and applicable memory. Fix any violations found.
   - Skip for non-code files (config, docs, memory).
5. After all changes, verify the accumulated diff matches the plan — no unintended additions or omissions.

**Scope Drift Detection** (checked at each step):
- 1–2 new files beyond original plan: note in progress update, continue.
- 3+ new files OR any new external dependency: pause, report drift, ask user.
- Remaining work >2× original plan estimate: stop and re-scope with user.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| All planned changes applied, lint + CONFORM pass (standard) | → TEST |
| All planned changes applied, lint + CONFORM pass (trivial) | → REVIEW |
| CONFORM finds violations | Fix violations, re-lint (counted within lint retries, not a separate loop) |
| Lint failure after fix attempt | Fix lint issues, re-check (max 2 retries) |
| Scope drift detected (3+ new files or new dependency) | → Escalate to user with drift report |
| Implementation blocked (deterministic) | → Escalate to user with what was tried |

Checkpoint: record files changed, lint results, CONFORM audit results, drift notes (if any).

### TEST

**Persona:** MODEL-BUILDER
**Memory:** No additional loads.

**Actions:**
1. **Re-verify symptom** — re-run the regression test written in IMPLEMENT's TEST-FIRST gate. Confirm it now passes (green).
2. **Check acceptance criteria** — reload PRESCRIBE checkpoint AC. Verify each criterion is met with evidence.
3. Run existing tests/checks to confirm no regressions.
4. If the fix targets a code file, add any additional test coverage beyond the regression guard (edge cases, boundary conditions). Run the new tests and lint.
5. If the fix targets non-code files (config, docs, memory, workflows), verify correctness through appropriate validation (lint, manual inspection, tool re-run).

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|------------|
| All tests pass (existing + new) | → REVIEW |
| New test fails — reveals incomplete fix | → IMPLEMENT (targeted fix) |
| Existing test regresses | → IMPLEMENT (fix regression) |
| 3 IMPLEMENT↔TEST loops exhausted | → Escalate to user |

Checkpoint: record test results, AC verification evidence, new test files created.

### REVIEW

**Persona:** EVAL-SENTINEL
**Memory:** Reload DIAGNOSE checkpoint (root cause context). Load domain-relevant convention memory for the file types under review.

**Actions:**
1. Review the code changes for quality: security, best practices, code smells.
2. Verify changes follow applicable domain conventions and lint rules.
3. Rate any findings by severity (CRITICAL, HIGH, MEDIUM, LOW).
4. Render verdict: **approve** or **request changes with reasons**.
> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.
| Condition | Transition |
|-----------|-----------|
| Review passes — no CRITICAL or HIGH findings (standard) | → AUDIT |
| Review passes — no CRITICAL or HIGH findings (trivial) | → REPORT |
| CRITICAL or HIGH findings identified | → IMPLEMENT (fix findings, shares the IMPLEMENT↔TEST↔REVIEW loop limit of 3) |

Checkpoint: record review verdict, findings by severity.

### AUDIT

**Constraints:** Prove/disprove with evidence. Severity-rate findings. Pass/fail only — no code changes.
**Memory:** Reload DIAGNOSE and PRESCRIBE checkpoints.

**Actions:**
1. Verify root cause from DIAGNOSE checkpoint is addressed by the implementation.
2. Verify all planned steps from PRESCRIBE checkpoint were executed.
3. Verify IMPLEMENT checkpoint shows lint passing on all changed files.
4. Verify TEST checkpoint shows tests exist and pass, and AC are met with evidence.
5. Verify REVIEW checkpoint shows no CRITICAL or HIGH findings.
6. Check no unintended side-effects or scope drift (compare IMPLEMENT files changed vs. PRESCRIBE files list).
7. Render pass/fail verdict with evidence per check.
> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.
| Condition | Transition |
|-----------|-----------|
| Audit passes — all checks green | → REPORT → DONE |
| Audit fails — fix incomplete or plan was wrong | → DIAGNOSE (full restart with accumulated evidence, max 1 AUDIT→DIAGNOSE loop) |
| 1 AUDIT→DIAGNOSE loop exhausted | → Escalate to user with all evidence |

Checkpoint: record audit verdict, evidence per check.

### REPORT

**Persona:** —
**Memory:** Unload task-specific memory.

**Actions:**
1. Produce summary: root cause → fix plan → implementation → test results → audit verdict.
2. List files changed with before/after description.
3. Present numbered next-steps. Include:
   - "Submit for code review" when applicable.
   - "Persist root cause to memory (`/learn`)" when the root cause reveals a recurring pattern, non-obvious gotcha, or domain-specific lesson worth retaining.
4. Exit per `_protocol.md` exit contract.

→ DONE.

---

## Allowed Personas

| Phase | Allowed | Path |
|-------|---------|------|
| DIAGNOSE | TRACEHOUND | Both |
| RECON | (inline constraints) | Both |
| PRESCRIBE | (inline constraints) | Standard |
| IMPLEMENT | MODEL-BUILDER | Both |
| TEST | MODEL-BUILDER | Standard |
| REVIEW | EVAL-SENTINEL | Both |
| AUDIT | (inline constraints) | Standard |
| REPORT | Any | Both |

---

## Error Handling

Per `_protocol.md` error hooks (4-class model).
- Diagnosis failure: retry once with broader context, then escalate.
- RECON failure: proceed to next phase with empty leverage map (RECON is best-effort, never blocks the pipeline).
- Prescribe escalation: yield to `plan.md` for complex fixes, or escalate to user for ambiguous diagnoses.
- Implementation failure: try alternative approach (max 2), then escalate.
- Test failure: loop IMPLEMENT↔TEST (max 3 rounds), then escalate.
- Audit failure: restart from DIAGNOSE with accumulated evidence (max 1 loop), then escalate.

---

## Constraints

- DIAGNOSE is analysis-only — TRACEHOUND does not write code.
- RECON is read-only — QUARTERMASTER scans skills/memory indexes, never writes files. RECON is best-effort and non-blocking: an empty leverage map is valid output.
- PRESCRIBER never writes code — PRESCRIBE is plan+validate only. Escalates to `plan.md` for architectural fixes.
- EVAL-SENTINEL never writes code — REVIEW is quality-gate only.
- AUDITOR never writes code — AUDIT is verification-only.
- Only MODEL-BUILDER writes files, and only during IMPLEMENT and TEST phases.
- Lint retries within IMPLEMENT (max 2) do not count toward the IMPLEMENT↔TEST loop limit.
- Lint gate is mandatory after every file change (per policy).
- CONFORM gate is mandatory for code files after lint passes — re-read and verify domain-specific formatting and best-practice rules before transitioning out of IMPLEMENT. CONFORM violations are fixed in-place (no new loop) and re-linted within the existing lint retry budget.
- Test coverage is mandatory for code fixes — no code fix ships without a test proving it works. Non-code fixes use appropriate validation instead.
- Max loop counts prevent infinite cycles: 3 for IMPLEMENT↔TEST↔REVIEW, 1 for AUDIT→DIAGNOSE.
- Trivial path skips PRESCRIBE, TEST, and AUDIT — MODEL-BUILDER absorbs planning, verification is via its internal preflight. RECON runs on both paths.
- RECON must complete in a single pass — no loops, no retries. It is a fast scan, not a deep investigation.
- Changes must be small, reviewable, and reversible.
- Scope drift detection is enforced during IMPLEMENT — 3+ unplanned files or new dependencies require user approval.
- Multi-step fixes must use per-step tracking during IMPLEMENT.
- TEST must explicitly verify PRESCRIBE acceptance criteria and re-run DIAGNOSE reproduction steps — not just "tests pass."
- Max 1 workflow yield (to `interview.md` for context, `cure.md` for design issues, or `plan.md` for architectural fixes).
