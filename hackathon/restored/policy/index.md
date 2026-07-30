---
title: Policy Index
created: 2026-04-08
updated: 2026-07-28
status: active
summary: Index of policy documents governing routing, interaction, and implementation boundaries.
---

# Policy Index

This folder contains authoritative policy documents for the agent system. Use this index to locate rules and operating contracts.

- `interaction_model.md` — User-facing interaction expectations, continuation policy, and response depth.
- `implementation_boundary.md` — What may be implemented, design-only items, prerequisites, and hard rules (secexpr --safe, no hardcoded DBs).
- `execution_protocol.md` — Default execution flow, verification rules, parallelisation, and continuation policy.
- `output_contract.md` — Response format by task type and quality standards.
- `subagent_protocol.md` — When to spawn subagents, model pinning (canonical, with fallback), context packets, leader/worker rules, depth limits, and concurrency.
- `context-isolation.md` — Context bloat prevention: spawn thresholds, context packet schema, return contract, anti-patterns, and workflow integration.
- `communication_protocol.md` — Handoff format, escalation path, and human-in-the-loop triggers.
- `preflight-gates.md` — Mandatory pre-flight checks (user profile, Slang ref, secexpr safe mode).
- `ml-constraints.md` — ML vol forecasting non-negotiable rules: QLIKE primary, purged CV only, log-RV space, COVID regime handling, research-first, feature engineering > model complexity.
- `working-agreements.md` — Cleanup plans, regression tests, CoALA compliance, Slang gates.

Reference: High-level operating contract is in AGENTS.md.
