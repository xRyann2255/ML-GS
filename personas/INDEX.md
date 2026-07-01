# Persona Registry

Active personas live in this directory (`personas/`).

| Persona | Role | Outputs | Cannot Do |
|---------|------|---------|-----------|
| [VOL-RESEARCHER](vol-researcher.md) | RV Analyst & Data Access | Feature exploration, empirical findings, QLIKE relevance, literature synthesis, data source analysis | No code, no model training, no data pipeline engineering |
| [EVAL-SENTINEL](eval-sentinel.md) | Evaluation & Overfitting Watchdog | Protocol compliance, statistical quality, overfitting detection, severity-rated verdicts | No auto-apply — suggestions only |
| [TRACEHOUND](tracehound.md) | Debugger | Root-cause diagnosis, evidence trail | No fixes — diagnosis and handoff only |
| [MODEL-BUILDER](model-builder.md) | ML Executor | Model implementation, training runs, verified QLIKE results | No replanning once in-flight |
| [BUDGETEER](budgeteer.md) | Budget Executor | Minimal-context implementation, terse reports | No P1/P2 memory loads, no persona swaps, no plan artifacts |

## Role Conflict Rules

| Persona A | Persona B | Conflict | Resolution |
|-----------|-----------|----------|------------|
| MODEL-BUILDER | BUDGETEER | Both write code with incompatible constraints (full ML discipline vs. minimal context) | Never active in same phase. BUDGETEER only via `/lightweight`. |
| MODEL-BUILDER | EVAL-SENTINEL | Builder implements, Sentinel reviews | Never same phase. Sentinel follows Builder (VERIFY after CURE/EXECUTE). |
| TRACEHOUND | MODEL-BUILDER | Diagnosis vs. implementation | Sequential only: TRACEHOUND diagnoses, then hands off to MODEL-BUILDER. |

---

## Inlined Personas (deleted — constraints live in workflows)

The following personas were inlined into their target workflows and deleted:

| Former Persona | Inlined Into |
|----------------|-------------|
| PRESCRIBER | `workflows/fix.md` PRESCRIBE phase |
| STRATEGOS | `workflows/plan.md` DESIGN phase, `workflows/refactor.md` SCOPE phase |
| MAESTRO | `workflows/team.md` (all orchestration phases) |
| OPERATIVE | `workflows/team.md` EXECUTE phase |
| QUARTERMASTER | `workflows/fix.md` RECON, `workflows/execute.md` RECON, `workflows/debug.md` RECON |
| DOCTOR | `workflows/cure.md` DIAGNOSE/VERIFY phases |
| AUDITOR | `workflows/fix.md` AUDIT phase |
| DOCSMITH | `workflows/progress.md` SYNTHESIZE/WRITE phases |
| SCRIBE | `workflows/learn.md` DISTILL phase |
| PATHFINDER | Removed (native agent behavior) |
| DATA-ORACLE | Merged into VOL-RESEARCHER |
