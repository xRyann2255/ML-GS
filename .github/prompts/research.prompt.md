---
description: "Research workflow — structured vol research session: explore one topic deep on real data, or quick investigation of a specific question"
argument-hint: "topic or open question to explore"
model: Claude Opus 4.6
---

You are in **research mode**. Run a structured research session: read the journal for recent findings, check open questions, explore one topic in depth using real data, and document findings.

For **quick investigations** ("what does X mean?", "find Y", "explain Z"): gather evidence, deliver a cited answer. Journal update is optional for one-off questions — use your judgment on whether the finding is worth persisting.

- `workflows/research.md`
- `personas/vol-researcher.md`
- `memory/research/README.md`
- `workspace/research/research-journal.md`
- `workspace/research/open-questions.md`

**Session protocol:**

1. Read the research journal for the last 3 entries — what was explored recently?
2. Read open questions — which topics need investigation?
3. Ask the user which topic to explore (or suggest the highest-priority open question).
4. Load the relevant P1/P2 memory cards for that topic (see `memory/INDEX.md`).
5. Explore on real data — compute, visualize, verify. Use the FEATURE_BUILD or DATA_INGEST skill as needed.
6. Document findings in the research journal with: date, topic, method, data used, key results, next steps.
7. Update open questions (close resolved ones, add new ones discovered).

**Expected outputs:** Updated research journal entry, updated open questions, any computed artifacts in `workspace/tmp/`.
