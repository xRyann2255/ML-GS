# Context Isolation Policy

Context bloat is the primary failure mode for complex agentic tasks. This policy defines when and how to spawn subagents for context isolation — keeping the orchestrating agent's context lean so it can plan, coordinate, and verify without drowning in implementation details.

---

## Philosophy

The orchestrating agent is a **coordinator**, not a laborer. It:
- Plans the decomposition
- Writes context packets for each subtask
- Spawns subagents to execute
- Collects results and verifies integration
- Never accumulates raw file contents or tool output beyond what's needed to coordinate

Subagents are **workers** with fresh context. They:
- Receive a bounded task with clear scope
- Read only what they need
- Execute and verify locally
- Return a structured report

---

## Spawn Thresholds

Spawn a subagent when ANY of these hold:

| Signal | Why |
|--------|-----|
| Task requires reading 3+ files | Each file adds ~50-200 lines to context |
| Task modifies 2+ modules | Cross-module work accumulates imports, tests, conventions |
| Single task would generate >200 lines of tool output | Drowns the orchestrator's reasoning |
| Task involves iterative debugging (read → edit → test → repeat >2 cycles) | Each cycle adds to context; subagent gets fresh start |
| Task is a leaf in the plan (no downstream dependencies on orchestrator seeing the work) | No reason for orchestrator to hold this context |

**Do NOT spawn when:**
- Task is trivial (<50 lines, single file, obvious fix)
- Result is needed immediately for the NEXT decision (serial dependency with tight coupling)
- Task is pure lookup (single file read, single grep)
- Orchestrator already has the needed context loaded

---

## Context Packet Schema, Return Contract, Depth Limits

Canonical definitions live in `policy/subagent_protocol.md` — the sole home of the packet schema
(including `context_summary` and `depends_on`), the return contract, and the depth table. Never restate them.

**Rules for writing context packets:**
1. `goal` must be a single, testable sentence. Not "implement the feature" but "add `compute_vwap()` to `features/micro.py` that returns a DataFrame with columns [symbol, date, vwap]".
2. `file_scope` lists files to READ. Keep it minimal — only what's needed for this subtask.
3. `write_scope` is the ONLY files the subagent may create or modify. Anything outside is out of bounds.
4. `acceptance_criteria` must be verifiable without human judgment.
5. `context_summary` replaces the need for the subagent to read the full conversation history.

---

## Orchestrator Behavior

After spawning subagents, the orchestrator:

1. **Does NOT re-read files the subagent modified** unless integration requires it (e.g., merging outputs from multiple subagents touching the same module).
2. **Trusts the subagent's verification** unless acceptance criteria are complex or cross-cutting.
3. **Runs integration verification** (full test suite, lint) only AFTER all subtasks complete — not after each one.
4. **Logs progress** via todo list updates after each subagent returns.

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Correct Approach |
|---|---|---|
| Spawning for a single-file trivial edit | Subagent overhead > context cost | Edit inline |
| Spawning when you need the result to make the NEXT decision | Creates serial bottleneck, no context benefit | Execute inline, use result immediately |
| Including the full conversation history in context_summary | Defeats the purpose of fresh context | Summarize in 2-5 sentences |
| Spawning a subagent that spawns further subagents | Context explosion, lost coordination | Max depth = 1 (except /team) |
| Re-reading subagent's output files to "verify" | Bloats orchestrator context | Trust subagent verification + run integration tests at end |

---

## Workflow Integration

| Workflow | When to Spawn | Orchestrator Retains |
|----------|---------------|---------------------|
| /plan | Discovery research, multi-file analysis | Plan artifact, decomposition |
| /execute | Per-subtask implementation | Todo list, integration test results |
| /research | Per-symbol or per-horizon computation | Hypothesis card, final summary table |
| /refactor | Per-module restructuring | Test baseline, integration verification |
| /team | Always (by definition) | Decomposition, merge conflicts, final verify |
