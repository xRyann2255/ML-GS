# Subagent Protocol

## When to Spawn

Spawn a subagent when **any** of these hold:
1. The work is independent of any in-flight task AND parallelism saves real time
2. **Context isolation** — the subtask would accumulate >200 lines of context, requires reading 3+ files, or touches 2+ modules. Spawn even for SEQUENTIAL work to keep the orchestrator's context lean.
3. Output is verifiable and the subtask is self-contained

**Context isolation is the primary reason for spawning.** Even sequential tasks get subagents if they'd bloat the orchestrator's context. The orchestrator stays thin: plan, coordinate, verify. Subagents do heavy lifting (file reads, code writes, computations) on fresh context.

## Model Pinning (HARD RULE)

**All subagents MUST use Claude Opus 4.6.** Never spawn a subagent on a weaker model. If the environment offers model selection, always choose Opus 4.6. If no model selector is available, the `runSubagent` tool uses the current conversation model — ensure your session is on Opus 4.6.

## Roles

**Leader:** decompose → assign bounded write scopes → own final verification — never delegate verification.
**Worker:** execute assigned slice only → stay in scope → report blockers up → do not replan.

## Spawn Thresholds

| Signal | Action |
|--------|--------|
| Task reads 3+ files | Spawn subagent |
| Task modifies 2+ modules | Spawn subagent |
| Task would accumulate >200 lines of tool output | Spawn subagent |
| Task is trivial (single file, <50 lines, one module) | Execute inline |
| Task depends on output of an unfinished prior subagent | Wait, then spawn |

## Context Packets

Every subagent spawn MUST include a structured context packet:

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

This file is the SOLE home of the packet schema, return contract, spawn-threshold table, and depth table. `policy/context-isolation.md` (rationale and anti-patterns) and `workflows/plan.md` point here — never restate the schema.

The orchestrator writes this packet into the `runSubagent` prompt. No separate handoff files.

## Return Contract

Every subagent MUST return:

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

## Depth Limit

- Workflows (/plan, /execute, /research, /refactor): max subagent depth = 1. Subagents do NOT spawn further subagents.
- /team workflow: max depth = 2 (Leader → Worker → Sub-worker).
- Sub-worker spawns must be reported to the leader in the worker's return notes.

## Concurrency

Max 6 concurrent subagents. Full orchestration rules: workflows/team.md.

## Failure Handling

1. Subagent returns `blocked` or `partial` → retry ONCE with refined context packet (add diagnostic info from first attempt)
2. Second failure → escalate to user with evidence from both attempts
3. Never retry more than once — avoid infinite loops

---

---

## Terminal Isolation (HARD RULE — zero exceptions)

1. **ALL subagents MUST use `isBackground=true` for EVERY `run_in_terminal` call.** Not just for output-parsing — for ALL terminal calls. `isBackground=false` is FORBIDDEN for subagents. No exceptions. No "quick" commands. No "just checking". ALWAYS `isBackground=true`.
2. **Use `./vol exec <cmd>` or `./vol bg <cmd>`.** Never read terminal buffer output directly — always read the OUTPUT_FILE. NEVER use `setsid`, `nohup`, `&`, `disown`, or any manual signal-isolation technique — `./vol exec` and `./vol bg` handle this internally.
3. **Never use `isBackground=false` in a multi-agent context.** The shared foreground terminal is a single resource — concurrent access causes "terminal is blocked" errors AND cross-session SIGINT propagation that kills other agents' long-running processes.
4. **"Terminal is blocked" or KeyboardInterrupt = use `./vol exec` or `./vol bg`.** Do NOT wait or retry. Do NOT use `nohup`, `setsid`, `&`, or `disown` manually. The vol wrappers handle isolation correctly.
5. **Use `./vol bg` for long-running jobs** (data ingestion, model training, anything >30s). It returns immediately. Poll the OUTPUT_FILE for the `EXIT_CODE=` sentinel line. Check `./vol jobs` for status.
6. **Kill your terminals before returning (EXIT GATE).** Before sending your final response, you MUST call `kill_terminal(id=<terminal_id>)` for every background terminal you spawned. This is not optional. A subagent that returns without killing its terminals is FAILED.
7. **Leader kills ALL worker terminals.** In the INTEGRATE phase, the leader MUST kill every terminal spawned by workers. Use `kill_terminal` for each known ID.
8. **Never leave terminals running.** Orphaned terminals accumulate across sessions, exhaust system resources, and confuse future agents. If you spawned it, you own its lifecycle — kill it before you exit.
