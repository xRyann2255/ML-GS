# Context Packets and Orchestrator Prompts

The packet is the ONLY context a Copilot subagent gets beyond the files it may read. The orchestrator prompt is the ONLY instruction the user pastes into Copilot Chat. Both instantiate the target repo's own protocol — extract the current schema during recon and instantiate it; the schema below is the reference shape (ml-vol-estimator's `policy/subagent_protocol.md`, 2026-07 snapshot) to be diffed against what recon finds, never used blind.

## Packet schema (embed one per task, inside the task's section of the plan)

```yaml
subtask_id: "<suite>-<plan>-<task>"      # e.g. "gnn-03-2" — stable, greppable
goal: "<ONE testable sentence>"          # not "implement the feature" — name the artifact and its observable behavior
file_scope:                              # files the subagent may READ — keep minimal
  - workspace/plans/<suite>/plan-NN-<slug>.md   # its own task section — the code/tests live THERE
  - <integration points only — the 2-5 source files the task touches or mirrors>
write_scope:                             # the ONLY files the subagent may create/modify
  - <exact paths — must not overlap any concurrent task's write_scope>
acceptance_criteria:                     # machine-verifiable, no human judgment
  - "./vol test -k <expr> -> N passed"
  - "<specific assertion: signature exists, output matches hand-computed value, characterization unchanged>"
constraints:                             # the subset of global constraints this task can violate
  - "TDD failing-first: show red, then green"
  - "<task-specific hard rules: 'do not modify X', 'no torch at module level', 'no new dependencies'>"
context_summary: |
  <2-5 sentences replacing conversation history: why this task exists, what the
  neighboring tasks produce/consume, the one design decision the subagent must not revisit>
depends_on: ["<subtask_ids that must be complete first>"]
```

## Packet-writing rules

1. `goal` names a deliverable and a verification, in one sentence.
2. `file_scope` minimal: the plan section (which carries the code) + true integration points. Ten files in scope means the task is cut wrong.
3. `write_scope` is exclusive per concurrent wave — the orchestrator parallelizes by disjoint write_scopes.
4. Every `acceptance_criteria` line is a command with an expected output or a mechanically checkable assertion.
5. Heavy content (test code, implementation code, math, YAML configs) lives in the **plan file**, referenced by section — packets stay under ~30 lines.
6. `context_summary` states decided things as decided ("the ledger says X; do not redesign it").

## Return contract (demand it verbatim in the orchestrator prompt)

```yaml
status: complete | blocked | partial
files_changed: [{path, lines, summary}]
verification: ["<pasted test/command output>"]
blockers: ["<what prevented completion>"]
notes: ["<integration facts the orchestrator needs>"]
```

Failure policy: blocked/partial → orchestrator retries ONCE with a refined packet (add diagnostics from the first attempt), then escalates to the user with evidence from both attempts.

## Orchestrator prompt template (last section of every plan; the user pastes this)

```
/execute Implement Plan NN (<title>) from workspace/plans/<suite>/plan-NN-<slug>.md

Precondition check: <the previous plan's acceptance gate, as a runnable command>.
Read workspace/plans/<suite>/00-overview.md §<conventions section> first.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1: <ids>            # waves = disjoint write_scopes; respect depends_on
  Wave 2 (parallel, max 2): <ids>
  ...
Each subagent: TDD (show red, then green), <repo CLI> only, return the §<n> return contract.
Retry a blocked/partial subagent once with a refined packet, then escalate.
Integration verification (orchestrator, after all tasks): <full test suite command>, <lint>, <typecheck>.
<repo-specific closing duties: progress log entry, print-don't-run launch commands>.
Do NOT start Plan NN+1.
```

## Hard rules the recon must confirm before any packet is written

- The current packet schema and return contract, verbatim (they drift between snapshots).
- Model pinning, depth limits, and max-concurrency the repo's policy imposes on subagents.
- The CLI discipline (e.g. `./vol` only, terminal isolation, workspace-only writes).
- The TDD gate's exact wording and its exemptions (configs/docs).
- Where plans must live for `file_scope` references to resolve on the executing machine.
