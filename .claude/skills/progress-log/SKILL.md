---
name: progress-log
description: Update the daily progress log. Invoke after meaningful progress, decisions, or at session end.
---

Read `logs/progress.md`. Check if today's date has an existing entry.

**If post-commit (granular update):**
- Read the latest git diff/commit message
- Append a bullet to today's entry (create entry if none exists)
- Small commits (typo, formatting): one-line bullet
- Meaningful commits: 2-3 line bullet with what changed and why

**If post-session (daily summary):**
- Consolidate today's granular bullets into a clean summary
- Add a "Next:" line for tomorrow's plan
- Do not duplicate existing bullets

**Entry format:**
## YYYY-MM-DD

**Sprint:** N -- [Sprint Name]
**Focus:** [main topic]

- [bullet points]

**Next:** [tomorrow's plan]
