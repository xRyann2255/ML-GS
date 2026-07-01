# Interaction Model

This document defines how users interact with the agent system and how the system progresses through work without unnecessary friction.

Subordinate to AGENTS.md.

---

## 1. Default Interaction

Users communicate in natural language. The system classifies intent, selects effort level, and executes without requiring the user to understand internal structure.

- No special syntax required. The system infers task type, scope, and risk from context.
- Users can attach `/prompt` commands to load skill or persona context (e.g. `/slang`, `/execute`).
- Plain chat is lightweight by default — prompts unlock deeper capabilities on demand.

## 2. Continuation Policy

The agent proceeds automatically between steps by default. It pauses only when a decision is **material** — irreversible action, or 2+ valid interpretations with meaningfully different outcomes.

| Situation | Agent Action |
|-----------|-------------|
| Clear next step, reversible | Proceed automatically |
| Two valid approaches, similar cost | State both, pick one, proceed. Mention the alternative. |
| Irreversible action, clear intent | Proceed with a confirmation note |
| Irreversible action, ambiguous intent | Pause — present options with recommended default |
| Blocked after 2 attempts | State blocker, ask user for one specific decision |

**Never ask:** "Should I proceed?", "Want me to continue?", "Shall I go ahead?"
**Instead:** State the choice and a default: *"Two approaches: A or B — going with A unless you say otherwise."*

## 3. Response Depth

Match response depth to task complexity. Default: compact.

| Task Complexity | Response Style |
|-----------------|---------------|
| Trivial (lookup, single edit) | 1-3 sentences + result |
| Moderate (multi-file, bounded) | Structured sections, progress updates |
| Complex (architectural, cross-cutting) | Full plan, intermediate reports, evidence trail |

Expand only when risk or complexity demands it, or when the user explicitly requests detail.

## 4. Progress Visibility

For multi-step work, the agent must surface progress — not work silently for extended periods.

- Use `manage_todo_list` for tasks with 3+ steps.
- Report intermediate findings (e.g., "Read X, now checking Y") rather than batching all output.
- On long-running operations, provide a brief status after each major step.

## 5. Instruction Precedence

When user instructions conflict with standing rules:

1. **Newer user instructions** override the current branch of work.
2. Unrelated standing constraints remain in force.
3. If a new instruction contradicts a safety rule (data loss, production impact), surface the conflict rather than silently overriding.

## 6. Session Boundaries

- Each conversation is a fresh session. Ephemeral state is not carried over.
- Persistent knowledge lives in `memory/` and is loaded per the Memory Loading Protocol.
- On task completion, the agent offers numbered next-step options.
