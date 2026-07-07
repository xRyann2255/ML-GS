---
name: write-copilot-plans
description: Use when asked to write implementation plans — especially a multi-plan suite — that GitHub Copilot agents will execute in a repo with an agent contract (AGENTS.md / copilot-instructions / subagent protocol), or when the user mentions context packets, plan suites, subagent-driven Copilot execution, or planning a large feature before building it.
---

# Write Copilot Plans

Author a suite of sequential, TDD implementation plans that GitHub Copilot agents execute in a target repo, one orchestrator session per plan, one context-packet subagent per task. The plans are the only memory the executing agents have — everything they need lives in the plan file or the packet.

**Core principle:** recon before design, design before decomposition, ledger before drafting, verification before delivery. Each phase produces a required artifact; the next phase consumes it.

**Companion workflow:** `.claude/workflows/write-copilot-plans.js` — invoke by name with `args={mode, ...}` for the fan-out phases (recon / design / draft / verify). The main session writes the overview and makes the decisions; the workflow does the parallel reading, judging, drafting, and checking.

**Worked exemplar:** `deliverables/gnn-implementation-plans/` (00-overview + plans 01–10). When in doubt about depth or tone, open plan-01 and plan-08 there.

## Phase 0 — Recon (workflow `mode: "recon"`)

Launch the recon workflow before forming any opinion about the design. It fans out parallel readers and returns structured maps:

1. **Contract map (always first-class):** the target repo's CURRENT Copilot execution contract — AGENTS.md, `.github/copilot-instructions.md`, `policy/subagent_protocol.md`, `policy/context-isolation.md`, `.github/prompts/`, the CLI wrapper. The packet schema is extracted **verbatim**. Prompt formats drift (this repo's own precedent went from handoff-files to context packets between snapshots); a plan suite written against last month's contract is rejected by the repo's own policy files, so the contract is re-read every suite, never recalled from memory.
2. **Research maps:** one reader per research artifact family the feature touches (guide chapters, deep-research briefs, paper catalogs). Output: what to build, in what order, with what expected outcomes — with exact numbers and citations preserved.
3. **Codebase maps:** extension surface (registries, base classes, protocols — with verbatim signatures), execution/config system, testing conventions, parallelism/progress infrastructure, and an **already-exists inventory** for the feature area (grep for the feature's nouns inside source files, not just directory listings — buried half-implementations change plan scope).

Persist each returned report to its own file so later phases' `groundingPaths` point at stable paths. Intermediate artifacts (recon reports, decision record, draft `outDir`) live in the **session scratchpad**, never inside the target-repo mirror (in this project `ml-vol-estimator/` is replaced wholesale by QR restores — anything written there is lost) — finished plans move to their delivery home in Phase 5.

**Checkpoint:** you can list (a) the packet schema verbatim, (b) every existing component the suite must extend rather than rebuild, (c) the evidence-backed expected outcome for the feature. Missing any → recon again, deeper. If contract files disagree with each other (packet schema variants across policy files), resolve which one the repo's execute workflow actually uses and record the answer in the overview — never silently pick one.

## Phase 1 — Design (workflow `mode: "design"`, then user sign-off)

The user asked for the *best* implementation, not the first one. Generate 2–4 candidate architectures through different lenses (minimal-diff, library-first, performance-first, convention-purist), have a judge panel score them against: fit to the repo's existing seams, evidence support from the research maps, risk, and total complexity. The main session reads the scored candidates and writes a **decision record** (chosen approach, rejected alternatives with reasons, open risks).

**Checkpoint — stop and get explicit user approval of the decision record and the plan-suite scope (how many plans, what each delivers, which gates sit between them) before writing any plan.** A design mistake multiplies across every plan and every Copilot session that executes them.

## Phase 2 — Overview + interface ledger (main session writes this by hand)

Write `00-overview.md` from `references/overview-template.md`. Its required sections: the plan table with **gates**, the dependency graph, the *what-already-exists* list, research grounding with **honest expected-outcome priors**, the shared conventions every packet repeats, and the **interface ledger** — one row per cross-plan symbol with its exact signature. The ledger is authoritative: drafters copy signatures from it, and any deviation during drafting is back-ported to it in the same sitting.

## Phase 3 — Draft the plans

Per-plan structure and task anatomy: `references/plan-template.md`. Packet schema and orchestrator prompt: `references/context-packet.md`.

- **≤4 plans:** write them inline in the main session, sequentially, updating the ledger as you go.
- **>4 plans:** fan out via workflow `mode: "draft"` — one drafter per plan, each given the overview verbatim plus a one-paragraph brief; drafters write the plan files directly and return their produced interfaces and any ledger deviations. A per-plan packet lint runs in the same pipeline.

Every plan ends with an acceptance gate; every experiment ships with a hypothesis, an expected-outcome prior, and a decision rule (what changes downstream if it fails — a null result must have a defined consequence, not just disappointment).

## Phase 4 — Verify (workflow `mode: "verify"`)

Four checks over the finished suite, findings fixed inline by the main session:

| Check | Catches |
|---|---|
| Packet lint (per plan) | missing packet fields, non-minimal file_scope, overlapping write_scopes, acceptance criteria a human must judge |
| Cross-plan consistency (one judge over all plans + ledger) | signature drift, registry-name mismatches, numbering collisions, dependency-order violations |
| Placeholder scan | TBD/TODO/"similar to Task N"/steps that describe without showing code |
| Rebuild check (vs the already-exists inventory) | plans that recreate components the recon found |

## Phase 5 — Deliver

Plans live where the target repo's executors can read them (in this project: `deliverables/<slug>-plans/` on main, synced to docs-only, copied to `<target-repo>/workspace/plans/<slug>/` on the executing machine — packets reference plan sections by that path). Commit, update the progress log, and hand the user the Plan-01 orchestrator prompt as the next action.

## Common mistakes

- **Writing packets from memory of the contract.** The schema you remember is the schema that drifted. Contract map first, every time.
- **Skipping the design phase because the feature "has an obvious shape."** The judge panel exists to find the seam you didn't know the repo already had.
- **Fat packets.** Code, tests, and math live in the plan file; the packet carries pointers (plan section anchors), scopes, criteria, and a 2–5 sentence context summary. A packet that embeds the implementation defeats context isolation.
- **Ledger as an afterthought.** If the ledger is written after the plans, it documents the drift instead of preventing it.
- **Gates without consequences.** "Run experiment X" is not a gate; "if X's best arm fails DM p<0.05 vs control, plans N..M shrink to replication arms" is.
- **Placeholder acceptance criteria.** "Works correctly" is unverifiable; "`./vol test -k <expr>` → N passed" is a criterion.
