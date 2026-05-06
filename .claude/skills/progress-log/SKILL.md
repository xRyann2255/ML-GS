---
name: progress-log
description: Update the daily progress log and research journal. Invoke after meaningful progress, decisions, or at session end.
---

This skill updates TWO files: the progress log (what was done) and the research journal (what was learned).

## 1. Progress Log (`logs/progress.md`)

Read `logs/progress.md`. Check if today's date has an existing entry.

**If post-commit (granular update):**
- Read the latest git diff/commit message
- Append a bullet to today's entry (create entry if none exists)
- Small commits (typo, formatting): one-line bullet
- Meaningful commits: 2-3 line bullet with what changed and why

**If post-session (daily summary):**
- Consolidate today's granular bullets into a clean summary
- Add a "Next:" line for tomorrow's focus
- Do not duplicate existing bullets

**Entry format:**
## YYYY-MM-DD

**Focus:** [main topic]

- [bullet points]

**Next:** [tomorrow's focus]

## 2. Research Journal (`notes/research-journal.md`)

Read `notes/research-journal.md`. If there is no entry for today, or if the session explored something new, append an entry.

**Entry format:**
## YYYY-MM-DD -- [Topic explored]

**Question explored:** [what we were trying to understand]

**What we found:**
- [specific findings, with numbers/data where possible]

**What surprised us:**
- [anything that contradicted expectations or literature]

**Open threads:**
- [questions that came up during exploration, for future sessions]

**Skip the research journal entry if** the session was purely mechanical (repo cleanup, LaTeX compilation, file moves) with nothing learned.

## 3. Feature Notes (if applicable)

If the session explored a specific feature family, also update the relevant file in `notes/features/` with any findings.
