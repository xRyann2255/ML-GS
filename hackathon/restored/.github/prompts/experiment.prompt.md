---
description: "Bridge research hypothesis to logged experiment — config generation, validation, result interpretation"
argument-hint: "hypothesis to test or 'interpret' to log results from a completed run"
model: Claude Opus 4.6
---

You are in **experiment mode**. Bridge a research hypothesis to a logged experiment result.

- `workspace/research/trials.yaml`
- `personas/model-builder.md`

## Context (auto-load)

1. `workspace/research/trials.yaml` — last 5 completed + all NOT_STARTED entries
2. Latest entry in `workspace/research/research-journal.md`
3. Current baseline config (from project-state.md or most recent LOCKED trial)

## Protocol

### Mode A: New Experiment (default)

**Input:** Hypothesis from latest journal entry, or user-specified text.

**Validation gates (ordered cheapest-first):**

1. **Redundancy check** — Has this been tested? Search trials.yaml.
   - If yes: show prior result, ask if user wants to re-test with different params.
2. **Data availability** — Does required data exist in `data/raw/`?
   - If no: flag and offer to run ingest first.
3. **Config validity** — Does the generated YAML parse correctly?

**Steps:**
1. Clone baseline config (or user-specified base)
2. Apply parameter changes implied by hypothesis
3. Show diff between new and base config
4. Ask user for approval
5. Save config: `./vol new-experiment --base <baseline> --name <name> --set <overrides>`
6. Register in trials.yaml with `status: NOT_STARTED`
7. Print run command: `./vol run --config workspace/configs/<name>.yaml`

### Mode B: Interpret Results (user says "interpret" or returns after a run)

**Steps:**
1. Read experiment output (metrics.json from output dir, or user-provided numbers)
2. Compute bps improvement vs baseline per horizon
3. Determine verdict per horizon:
   - PASS: DM p < 0.05 AND QLIKE improves
   - FAIL: otherwise
4. Update trials.yaml entry with results
5. Draft 3-line journal summary
6. Suggest next experiment based on result pattern

## Constraints

- Never auto-run `vol run`. Print the command for the user to execute.
- Always show config diff before saving.
- One experiment per invocation (no batch creation).
- QLIKE is the primary metric. Report MSE/MAE only as supplementary.
- Verdicts use DM test significance (p < 0.05) as the hard gate.
