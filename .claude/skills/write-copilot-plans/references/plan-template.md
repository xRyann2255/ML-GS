# Per-Plan Template

One file per plan: `plan-NN-<slug>.md`. Sections in order; nothing optional except where marked.

## Header block

```markdown
# Plan NN — <Title>

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §<last>.
> Dispatch each task as a subagent with the context packet provided. Max <k> concurrent subagents.
> TDD is a hard gate (<repo's rule reference>). Requires Plans <deps> merged <+ any science gate>.

**Goal:** one sentence — the single demoable increment.
**Architecture:** 2-4 sentences — how it plugs into the repo's existing seams (name them).
**Tech stack:** libraries used; state "No new dependencies" or list the exact pyproject additions.
**Research grounding:** the paper/brief/chapter claims this plan implements, with the expected-outcome prior and the calibration warning.
```

## Global constraints

The suite-wide rules (pointer to 00-overview §conventions) PLUS this plan's specific hard rules — e.g. "characterization test pins current behavior before any refactor", "do not touch <legacy path>".

## File map

| Action | Path | Responsibility |
|---|---|---|
| Create/Modify | exact path | one clause |

## Interfaces

- **Consumes:** exact symbols from earlier plans (copied from the ledger).
- **Produces:** exact symbols later plans rely on (added to the ledger).

## Tasks (the body)

Each task:

```markdown
## Task N: <name>

**Files:** Create/Modify/Test — exact paths.

**Copilot context packet:**   <- the yaml block, per references/context-packet.md

- [ ] **Step 1: Write the failing test** — actual test code, complete, in a fenced block
- [ ] **Step 2: Run to confirm red** — exact command + expected failure
- [ ] **Step 3: Implement** — actual code (or a bounded recipe: numbered steps + the exemplar
      file to mirror, when the pattern file already exists in-repo and is named in file_scope)
- [ ] **Step 4: Run to green** — exact command + expected output
- [ ] **Step 5: Commit** — exact conventional-commit message
```

Task-sizing: one task = one subagent = one commit-worthy deliverable a reviewer could reject independently. Fold scaffolding into the task that needs it.

No placeholders: no TBD/TODO-as-content, no "add appropriate error handling", no "similar to Task N" (repeat or point to a plan-file anchor), no test steps without test code. The one sanctioned deferral: values only determinable at execution time ("take the next free trial number", "substitute the recorded gate winner") — stated as an explicit instruction with a fallback.

## Configs / experiments (when the plan ships runnable experiments)

Full config files inline (verbatim YAML), each with: hypothesis comment, expected-outcome prior, decision rule, domain caveats (e.g. COVID handling), registry entry instructions, and the launch command **printed, never run by the agent**.

## Orchestrator prompt

Last section — the paste-ready block per references/context-packet.md, with wave ordering derived from depends_on + disjoint write_scopes.

## Acceptance gate → Plan NN+1

What must be true (commands green, artifacts present, science verdicts recorded) before the next plan starts, and what the next plan consumes from this one.
