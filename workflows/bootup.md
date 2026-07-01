# Workflow: Bootup

Session-start checklist — load research state, present QLIKE scorecard, identify next action.

---

## Entry Conditions

Enter when:
- User explicitly uses `/bootup`.
- Session start with no prior context loaded.

---

## Checklist (execute sequentially)

1. **Read P0 state:** `memory/research/project-state.md` (current milestone, QLIKE scorecard, next action)
2. **Read trial registry:** `workspace/research/trials.yaml` — last 3 completed + all NOT_STARTED entries
3. **Read latest research journal entry:** `workspace/research/research-journal.md` (most recent `##` section only)
4. **Read user prefs:** `memory/person/user.md`
5. **Check handoff:** If `workspace/tmp/session-handoff.md` exists, read it (trust trial registry over handoff for experiment state)
6. **Synthesize and present:**
   - One-line last session summary (from journal or handoff)
   - QLIKE scorecard table (h=1/5/22: best number, status, trial ID)
   - Next experiment ready (from NOT_STARTED trials) or next implementation step
   - Recommended slash command to begin

---

## Output Format

```
## Session Start

**Last session:** [one-line summary]

| Horizon | Best QLIKE | vs HAR (bps) | Status | Trial |
|---------|-----------|--------------|--------|-------|
| h=1     | ...       | ...          | LOCKED | ...   |
| h=5     | ...       | ...          | ...    | ...   |
| h=22    | ...       | ...          | ...    | ...   |

**Next:** [trial-NNN description] or [implementation task]
**Recommended:** `/experiment` | `/research` | `/execute`
```

---

## Constraints

- Read-only — this workflow never writes files.
- Max context load: P0 + trial registry + 1 journal entry + handoff. No P1/P2 memory at boot.
- If project-state.md is missing, fall back to reading the full trial registry + journal (first session setup).

---

## Notes

- This workflow is read-only — it does not modify any files (except stale handoff cleanup).
- After bootup, route subsequent requests through `research.md` or `execute.md`.
