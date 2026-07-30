# Workflow: Progress

Synthesize weekly progress from journal entries, git log, and auto-logged bullets. Output goes to `workspace/research/weekly-progress.md`.

---

## Entry Conditions

Enter when:
- User explicitly uses `/progress`.
- Task pattern matches: "weekly progress", "progress log", "write weekly update"

---

## Steps

1. **Gather sources:**
   - Read `workspace/research/weekly-progress.md` (current week section or backfill target)
   - Read `workspace/research/research-journal.md` (entries in target week)
   - Check git log: `git log --oneline --since="YYYY-MM-DD" --until="YYYY-MM-DD"`
2. **Draft entry** with four sections: Shipped, Decided, Learned, Next week
3. **Present draft** to user for approval
4. **Write** approved entry to `workspace/research/weekly-progress.md` in correct chronological position

---

## Format Constraints (non-negotiable)

- **No em dashes** in any entry.
- **Plain language.** A non-technical manager must be able to follow. No acronyms, function names, library names, or statistical test names.
- **Four sections only:** Shipped, Decided, Learned, Next week.
- **Concise bullets.** One line each. Sub-bullets only for clarifying lists.
- **Week heading:** `## Week N: Mon DD - Fri DD, YYYY`
- **Reverse-chronological order.** Newest week first in file.
- **Do not modify the research journal.** Read-only.
