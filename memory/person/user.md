---
created: 2026-04-07
updated: 2026-04-07
tags: [person, user, profile, goldman-sachs, strategist, equities, vol-forecasting, risk, pnl, modeling, programming]
status: active
---

# The User (Profile) Kerberos: vincry

## Role

The user is a Goldman Sachs **Strategist** (Equities / ML Vol Forecasting context) who needs hands-on capability across **modeling + programming**. 

- **Products:** Equity Stocks, Derivatives, Futures, Synthetics, FX, Commodities, Interest Rate, etc.
- **Processes:** Inventory optimization, indexation, hedging, algo.
- **Fundamentals:** Pricing, Marking, Risk (Greeks) computation & Tradable modeling.
- **Tools:** SecDB framework and Slang.

**Tone:** Terse, direct. Use industry shorthand freely. No filler phrases. State uncertainty explicitly. Hand holding when it comes to finance - assume the user has limited finance knowledge.

## Typical Work / Problem Space

- Build and maintain quantitative models (signals, forecasts, risk, scenario / stress, portfolio construction).
- Implement and validate **booking**, **risk**, **P&L**, and **flows** logic (trade lifecycle, position/holdings, corporate actions, calendars).
- Work across product surfaces (cash equities, derivatives/structured products as needed) and connect model outputs to downstream consumers.
- Diagnose data issues (tickers/identifiers, mappings, survivorship, corporate actions, missing data) and harden pipelines.
- Create automation for research, monitoring, and productionization.

## What “Good Output” Looks Like

- Clear, reproducible implementations with minimal assumptions.
- Practical engineering: versioned artifacts, deterministic runs, strong input validation, sensible defaults.
- Explicit units/definitions (e.g., returns, FX conventions, risk metrics, P&L decomposition).
- Workflow-aware: integrates with existing Slang/GS tooling and review processes.
- Validation-first: any change to scripts is accompanied by the best available validation (native lint, ScriptVal, and RegTest re-runs when applicable), with results summarized.

## Technical Skills Expected

- Strong programming: Python (primary), plus ability to read/modify Slang scripts and build lightweight tooling.
- Data engineering basics: joins/keys, incremental pipelines, caching, reproducibility.
- Model implementation: regression/regularization, time series, cross-sectional modeling, backtests, evaluation.
- Production hygiene: linting, code review workflow, and safe editing for scripts with special naming.

## Preferences / Conventions (Known)

Detailed rules are in the copilot memory preferences.md (always loaded) and topic-specific disk memory files. Key conventions:

- Disk memory is primary — always write to `memory/` folder.
- SLANG_EDIT skill for all script edits. VFS primary path; secexpr fallback for colon-named scripts, deletes.
- `secexpr --safe` always. No exceptions.
- SLANG_LINT skill for lint. Never VS Code extension.
- ScriptReview: verify zero delta shame + show BROWSER_URL.
- Polling: max 5s sleep. Temp files: `workspace/tmp/` only.
- Validate script changes: lint (mandatory), ScriptVal and RegTest (when applicable).
- GitLab MRs: always set `squash: true` (squash commits on merge).
- Every prompt output should end with numbered next-steps that include the relevant `/slash command` to use. This applies to all workflows, not just `/bootup`.
