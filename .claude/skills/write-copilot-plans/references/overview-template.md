# 00-overview.md Template (the suite's anchor document)

The overview is written BY HAND in the main session after design sign-off and BEFORE any plan. Every plan-drafter receives it verbatim; every later Copilot session reads it first. Required sections, in order:

## 1. Header + how-to-use

Date, status, scope in two sentences. Then the execution instructions: where the suite lives on the executing machine, "one plan = one Copilot session with `/execute`", "plans are sequential; do not start N+1 before N's acceptance gate passes."

## 2. The plan table (with gates)

| # | Plan | Deliverable | New registry keys / public symbols | Gate to proceed |
|---|------|-------------|-------------------------------------|-----------------|

Every row's gate is a decision rule, not a task ("best arm beats control, DM p<0.05 — else plans N..M shrink to X"). Follow with the dependency graph as ASCII:

```
01 ──► 02 ──► 03 ──► 04 ─┐
              │        05 ┼──► 08
              └──► 06 ────┘   (06 can start any time after 02)
```

## 3. What already exists (do not rebuild)

The recon's already-exists inventory, verbatim signatures included, with the sentence: "Every plan extends these; duplicating them is a defect." This section is the input to the verify phase's rebuild check.

## 4. Research grounding

The evidence behind each design decision, with citations, and the **honest expected-outcome priors table**:

| Component | Realistic expected outcome | Source of the prior |
|---|---|---|

Close with the sanity rule ("a result far better than the prior is a bug or a leak until proven otherwise").

## 5. Shared conventions (repeated into every packet)

The target repo's hard rules as one bullet list: TDD gate wording, CLI discipline, file-write discipline, ML/domain guardrails, commit style, return contract, retry policy. Plus the packet template itself (from references/context-packet.md, instantiated with the recon's verbatim schema).

## 6. Interface ledger (authoritative)

| Symbol | Defined in | Signature (summary) |
|---|---|---|

One row per symbol that crosses a plan boundary: dataclasses with field lists and defaults, function signatures with keyword names, registry keys, config-block fields, event schemas, column names. Rules:

- Drafters COPY from the ledger; they never re-derive a signature.
- Any deviation discovered while drafting is back-ported to the ledger in the same sitting.
- The verify phase's cross-plan consistency judge treats the ledger as ground truth.

## 7. Resource topology (if relevant)

GPU/parallelism budget and which existing repo patterns each plan reuses (fold×GPU, HPO×GPU, progress-event invariants...). Name the precedent file+lines for each pattern so drafters mirror rather than invent.

## 8. Execution order and session budget

Plans per week/session estimate, which plans parallelize, and the standing session-close duties (full test suite, commit series, progress entry).
