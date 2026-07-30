# Execution Protocol

**Default:** explore → implement → verify → report.

**Do not:** Do not stay processing without giving intermediate steps of your reasoning.  
**Do not:** explain a plan and stop, stop at partial completion, or claim done without verification output.

**Verification:** identify what proves the claim → run it → read the output → report with evidence. If verification fails, keep iterating.

**Parallelization:** run independent tasks in parallel, dependent tasks sequentially.

**Completion check:** before concluding, confirm — no pending work, features working, tests passing, zero known errors, verification evidence collected.

**Continuation:** proceed between steps by default. Pause only when a decision is material — irreversible action, or 2+ valid interpretations with meaningfully different outcomes. Never ask "should I proceed?" — state the choice and a default: *"Two approaches: A or B — going with A unless you say otherwise."*
