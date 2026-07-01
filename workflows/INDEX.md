---
title: Workflows Index
created: 2026-04-08
updated: 2026-06-22
status: active
summary: Workflow registry with dispatch keywords
---

# Workflows

All workflows follow [_protocol.md](_protocol.md).

**Routing rule:** Follow the `/prompt` attachment. No prompt? Match keywords below. No match? Default to `plan.md`.

**Subagent-driven execution:** /plan, /execute, /research, and /refactor support context-isolated subagent decomposition. When a task exceeds spawn thresholds (3+ files, 2+ modules, >200 lines of context), the orchestrator decomposes into subtasks and spawns subagents with fresh context. See [policy/context-isolation.md](../policy/context-isolation.md) and [policy/subagent_protocol.md](../policy/subagent_protocol.md).

---

## Registry

| Workflow | File | Persona | Keywords | When |
|----------|------|---------|----------|------|
| Plan | [plan.md](plan.md) | — | "plan", "break down", "decompose", "scope this", "don't assume", "let's discuss", "walk me through" | Default. Scoping, design, and clarification. |
| Execute | [execute.md](execute.md) | MODEL-BUILDER | "implement", "build", "ship" | ML implementation and delivery |
| Research | [research.md](research.md) | VOL-RESEARCHER | "explore", "research feature", "what does the data show", "find X", "explain Y", "what does", "how does" | One topic deep on real data, or quick investigations |
| Debug | [debug.md](debug.md) | TRACEHOUND | "debug", "root cause", "why is X broken" | Diagnosis |
| Fix | [fix.md](fix.md) | TRACEHOUND → MODEL-BUILDER | "fix", "patch", "hotfix", "broken code" | Diagnose and fix |
| Review | [review.md](review.md) | EVAL-SENTINEL | "review", "check", "audit" | Code review and quality |
| Refactor | [refactor.md](refactor.md) | MODEL-BUILDER | "refactor", "restructure", "reorganize" | Lock tests, restructure |
| Housekeep | [housekeep.md](housekeep.md) | MODEL-BUILDER | "lint", "clean up", "fix lint", "update memory" | Maintenance (via `/lint-workspace`) |
| Cure | [cure.md](cure.md) | MODEL-BUILDER | "cure", "healthcheck", "fix design", "audit and fix" | Design violations |
| Learn | [learn.md](learn.md) | — | "learn this", "remember this", "save to memory" | Persist knowledge |
| Lightweight | [lightweight.md](lightweight.md) | BUDGETEER | "lightweight", "budget mode", "quick mode", "lite" | Minimal context, fast |
| Team | [team.md](team.md) | — | (3+ independent parallel streams) | Parallel orchestration |
| Progress | [progress.md](progress.md) | — | "weekly progress", "progress log" | Weekly log synthesis |
| Interview | [interview.md](interview.md) | — | "don't assume", "let's discuss", ambiguous scope | Clarification before action |
| Bootup | [bootup.md](bootup.md) | — | (via `/bootup` prompt only) | Session start |

---

## Skill Dispatch (keyword → skill)

When a message matches these keywords, load the skill context directly (no workflow needed):

| Keywords | Skill |
|----------|-------|
| "procmon", "proc logs", "job status", "failing job" | PROCMON |
| "enghub", "clone docs", "engineering docs" | ENGHUB |
| "elps", "glimpse", "search slang codebase", "production slang" | SLANG_GLIMPSE |
| `.s` filename, "slang script", "slang file" | SLANG_EDIT |
| "slang lint", "run lint", "native lint" | SLANG_LINT |
| "create review", "submit review", "script review" | SLANG_REVIEW |
| "cvs", "revision history", "who changed" | CVS |
| "confluence", "confluence page" | CONFLUENCE |
| "gitlab search", "search gitlab" | GITLAB_SEARCH |
| "prime", "primeid", "prime security" | PRIME_QUERY |
| "compare instream", "diff instream", "security diff" | SECDB_DIFF |
