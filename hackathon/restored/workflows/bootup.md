# Workflow: Bootup

Session-start checklist — load research state, present QLIKE scorecard, identify next action.

---

## Entry Conditions

Enter when:
- User explicitly uses `/bootup`.
- Session start with no prior context loaded.

---

## Checklist (execute sequentially)

1. **Execute the AGENTS.md Boot Protocol** (§Context Loading). Do NOT re-read files it already loaded.
2. **Read trial registry:** `workspace/research/trials.yaml` — last 3 completed + all NOT_STARTED entries
3. **Read latest research journal entry:** `workspace/research/research-journal.md` (most recent `##` section only)
4. **Synthesize and present:** one-line last-session summary (from the journal), QLIKE scorecard table (h=1/5/22), next experiment or implementation step, recommended slash command

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
- Max context load: Boot Protocol files + trial registry slice + 1 journal entry. No P1/P2 memory at boot.
- If project-state.md is missing, fall back to reading the full trial registry + journal (first session setup).

---

## Notes

- This workflow is read-only — it does not modify any files.
- After bootup, route subsequent requests through `research.md` or `execute.md`.
