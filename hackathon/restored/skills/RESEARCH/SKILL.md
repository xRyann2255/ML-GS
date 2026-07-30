---
name: RESEARCH
description: "Structured research sessions for ML vol forecasting exploration. USE FOR: literature deep-dives, feature exploration on real data, hypothesis testing, research journal updates, open question investigation. DO NOT USE FOR: building production features (use FEATURE_BUILD), training models (use MODEL_TRAIN), bulk data pulls (use DATA_INGEST)."
---

# RESEARCH — Structured Research Sessions

> **Purpose:** Conduct structured, documented research sessions. Each session explores one topic in depth, verifies findings on real data, and documents results in the research journal. This skill is primarily agent instructions — the `.cmd` wrapper is minimal.

**Out of scope:** Production feature building (use FEATURE_BUILD), model training (use MODEL_TRAIN), bulk data ingestion (use DATA_INGEST).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `RESEARCH` |
| **Scope** | Structured research exploration and documentation |
| **Inputs** | JSON args: topic, depth (quick/deep) |
| **Outputs** | Updated research journal, feature notes, exploration artifacts |
| **Authority** | Read + write to `workspace/research/` and `memory/research/` |

## When to Use

- Starting a new research session on a specific topic
- Exploring a feature layer's behavior on real data
- Investigating an open question from the research backlog
- Reviewing and synthesizing literature findings
- Updating the research journal with new insights

## When NOT to Use

- Building features for a training pipeline — use FEATURE_BUILD
- Running a model training experiment — use MODEL_TRAIN
- Quick data exploration in a notebook — use NOTEBOOK

## Research-First Philosophy

This skill enforces the project's research-first philosophy:

1. **Explore before building.** One topic deep per session.
2. **Verify findings on real data** before proposing architectures.
3. **No implementation plans** unless explicitly asked — research first.
4. **The implementation plan emerges from research**, not the other way around.
5. **Feature engineering > model complexity.** Understand the features before choosing the model.

## Memory References

| File | Content | When to Load |
|------|---------|--------------|
| `workspace/research/open-questions.md` | Exploration backlog | Session start |
| `memory/research/research-journal.md` | Previous session findings | Session start |
| `workspace/research/research-journal.md` | Full research journal | Session start |
| `workspace/research/open-questions.md` | Full open questions list | Session start |
| `workspace/docs/vol-project-ref/INDEX.md` | Authoritative project spec — milestones, feature formulas, model architecture | Session start, topic lookup |
| `workspace/docs/vol-learning-guide/INDEX.md` | Comprehensive theory & equations — full mathematical derivations for every estimator, model, and test. Source of truth for formulas | When exploring why something works, verifying derivations, understanding theory |
| Feature-specific P1/P2 cards | Relevant research context | When topic matches |
| `workspace/docs/data-audit.md` | Query cookbook for all data sources | When exploring data or running ad-hoc queries |

## Session Protocol

### 1. Start — Load Context

- Read `workspace/research/research-journal.md` for recent findings
- Read `workspace/research/open-questions.md` for topic backlog
- Read `memory/INDEX.md` to identify relevant memory cards
- Ask the user: **"What do you want to explore today?"**

### 2. Explore — Deep Dive

- Focus on **one topic** per session
- Load relevant memory cards (P1/P2) for the chosen topic
- If the topic involves data, use DATA_INGEST or PYTHON_MARKET_DATA to fetch real data
- Compute exploratory statistics, distributions, correlations on real data
- Compare findings with literature expectations

### 3. Verify — Test on Data

- Every claim must be verified on real data before being accepted
- Use NOTEBOOK for interactive exploration if needed
- Document any discrepancies between literature and observed data
- Note data quality issues encountered

### 4. Document — Update Records

- Update `workspace/research/research-journal.md` with session findings
- Update relevant memory cards if new facts are established
- Update `workspace/research/open-questions.md`:
  - Mark investigated questions as resolved (with summary)
  - Add new open questions that emerged
- If a feature's behavior is confirmed, update the corresponding feature notes

### 5. Summarize — Session Close

- Present key findings to the user
- List new open questions generated
- Suggest next research topic based on findings

## Task-Based Execution

**Agent-driven only — no VS Code task.** This skill has no Python entry point; execute its steps directly with file tools and `./vol exec` (S-B) / `vol.cmd exec` (S-A). The former `run_task("research")` path was removed (AW-05: it invoked modules that never existed).

The session protocol above is the entry point — the agent walks through it directly.

## Depth Levels

### `quick` — 30-minute Survey

- Read relevant P1/P2 memory cards
- Summarize current state of knowledge
- Identify 2-3 specific questions to investigate in a deep session
- No data computation

### `deep` — Full Research Session

- Full protocol: load → explore → verify → document → summarize
- Compute on real data
- Update journal and feature notes
- May take 1-2 hours of interactive work

## Links

- memory/research/research-journal.md — session log and findings
- workspace/research/open-questions.md — exploration backlog
- workspace/research/research-journal.md — active research journal
