# Research Artifacts Index

Operational research artifacts — living documents that change as experiments run. For distilled knowledge cards agents load into context, see `memory/research/` via [memory/INDEX.md](../../memory/INDEX.md).

---

## Living Operational Docs

Updated frequently as experiments run and research progresses.

| File | Purpose | Update Cadence | Referenced By |
|------|---------|---------------|---------------|
| [trials.yaml](trials.yaml) | Structured experiment registry (all trials, configs, outcomes) | Every experiment | bootup, protocol, experiment prompt |
| [research-journal.md](research-journal.md) | Append-only session log (hypotheses, trial outcomes, retractions) | Every research session | research, bootup, experiment, progress, status prompts |
| [research-journal-archive.md](research-journal-archive.md) | Overflow archive for older journal entries | When journal gets too large | — |
| [weekly-progress.md](weekly-progress.md) | Manager-facing progress log (Shipped/Decided/Learned/Next) | Weekly | progress, plan, status prompts, AGENTS.md |
| [open-questions.md](open-questions.md) | Living backlog of unresolved research decisions | Every research session | research workflow |
| [feature-engineering-status.md](feature-engineering-status.md) | Implementation status tracker (implemented/stubbed/test counts per layer) | After code changes | memory/INDEX.md P1 |

## Major Findings & Reference

Created after significant discoveries. Updated infrequently.

| File | Purpose | Last Major Update |
|------|---------|-------------------|
| [bibliography.md](bibliography.md) | Full ~80-entry literature reference (papers, venues, key findings) | Ongoing |
| [alt_data_discovery_results.md](alt_data_discovery_results.md) | Verified API data sources: 22 Marquee datasets, TSDB fields, extended-hours ticks, with access status | 2026-05-28 |
| [final_optimal_feature_set.md](final_optimal_feature_set.md) | Comprehensive feature catalog: all layers (L0-L8), implemented vs available, gap analysis | 2026-06-01 |
| [gsvivs_iv_improvement_plan.md](gsvivs_iv_improvement_plan.md) | IV proxy improvement roadmap: EDRVS_EXPIRY, variance swap strike, corrected VRP signal | 2026-06-05 |
| [data-ingestion-architecture.md](data-ingestion-architecture.md) | Ingestion pipeline design: source-based storage, CLI commands, parallelism, manifest schema | 2026-05-28 |
| [lstm-v2-notes.md](lstm-v2-notes.md) | LSTM v2 experiment notes: split-adjustment audit, per-symbol normalisation, config decisions | 2026-06-22 |

## What goes where?

- **Experiment ran → result logged?** → `trials.yaml` + `research-journal.md`
- **Weekly check-in?** → `weekly-progress.md`
- **New research question?** → `open-questions.md`
- **Major finding worth preserving?** → New file in this folder (add to this INDEX)
- **Distilled knowledge for agent context?** → `memory/research/` (not here)
