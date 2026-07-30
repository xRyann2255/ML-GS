---
description: "Project status dashboard — milestones, progress, what's built, open questions, next steps"
model: Claude Opus 4.6
---

You are in **status mode**. Produce a concise, single-screen project dashboard by reading the living source files below. Do not modify any files.

**Sources to read:**

- `memory/research/project-state.md` — current milestone, QLIKE scorecard, next action
- `workspace/research/trials.yaml` — last 3 completed + all NOT_STARTED trials
- `workspace/research/weekly-progress.md` — read the `## Milestones` section (top) for milestone progression, then the most recent week entry for Shipped/Decided/Next week
- `workspace/research/research-journal.md` — last 1-2 entries for recent research context
- Inspect `src/volforecast/` directory structure — list which modules exist

**Output format (all sections required, keep each concise):**

```
## Project Status — [date]

### Milestones
[Milestone progression table from weekly-progress.md showing DONE / ACTIVE / NOT STARTED for each milestone]

### This Week (Week N)
**Shipped:** [1-3 line summary from weekly-progress "Shipped"]
**Decided:** [key decisions from "Decided"]

### What's Built
[List of src/ml_vol_estimator/ modules with one-line purpose each]
[Test count if available]

### Open Questions (Top 3-5)
[Highest-priority unchecked items from open-questions.md]

### Next Steps
[From weekly-progress "Next week" section]

### Blockers
[Any blockers identified, or "None"]
```

**Rules:**
- Keep total output under ~40 lines. This is a dashboard, not a report.
- Do not load skills, workflows, or persona context. This is read-only synthesis.
- Do not ask "what would you like to explore?" — just present the status.
- If a section has no data (e.g., no blockers), say "None" and move on.
