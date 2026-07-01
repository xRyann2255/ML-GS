# Communication Protocol

## Handoff

When one persona completes and transfers to another, state the handoff inline:

> `[DEBUGGER → EXECUTOR] Root cause: null deref at line 42 of foo.ts. Fix: add null guard before .value access. Artifacts: diagnosis above.`

Include: source persona, target persona, one-sentence output summary, any artifacts produced, and an explicit next instruction.

## Escalation Path

| Condition | Action |
|-----------|--------|
| Blocked after 2 attempts | State blocker explicitly; ask user for one specific decision |
| Irreversible action with 2+ valid interpretations | Stop, present options with recommended default |
| Verification fails after 2 fix cycles | Escalate to user with full evidence trail |
| External system unreachable (e.g. ELPS timeout) | Report failure, offer cached/alternative approach |

## Human-in-the-Loop Triggers

Pause and ask the user when **all** of these hold:
1. The action is irreversible (deletes, publishes, CVS commits)
2. Intent is ambiguous (2+ interpretations with meaningfully different outcomes)
3. No safe default exists

Never ask for permission on reversible, low-risk, clearly-intended actions.
