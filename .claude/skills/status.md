---
name: status
description: Surface current project status — reads memory files and recent git history to show phase, progress, next steps, and open decisions.
---

# Status

Show the current state of the ML vol internship project. This skill READS memory but never writes it.

## Execution

1. Read `memory/project-status.md` from the Claude Code memory directory
2. Read `memory/decisions.md` from the Claude Code memory directory
3. Run `git log --oneline -10` to see recent commits

## Output Format

Combine memory and git history into this structure:

```
## Current Phase
[Phase name and approximate timeline from project-status.md]

## Recently Completed
[Items from "Completed" section of project-status.md, cross-referenced with recent git commits]

## Next Steps (priority order)
1. [From "Next Steps" section of project-status.md]
2. [...]
3. [...]

## Open Decisions
[From "Open Questions" in project-status.md + any unresolved items in decisions.md]
```

## Important

- This skill is READ-ONLY. It surfaces information, it does not update memory.
- Memory updates happen naturally during work sessions (e.g., after completing a chapter, making a decision, finishing a task).
- If project-status.md looks stale relative to git history, mention this: "Note: status file may be outdated — last 3 commits suggest [X] has been completed since last update."
