# Agentic Workflow Audit & Improvement -- Prompt Sequence

**Date:** 2026-05-26
**Goal:** Diagnose issues with the GS machine's agentic workflow, then improve it based on evidence.
**Target:** `h:\ml-vol-estimator\` running GitHub Copilot agent mode in VS Code.

## How to Use

1. Run each prompt in order by pasting it into Copilot agent mode chat
2. After each diagnostic prompt, run its validation prompt before moving on
3. After all 6 diagnostics, run the synthesis prompt
4. Review the synthesis proposal, then run implementation prompts one at a time
5. Each implementation prompt proposes changes for your approval -- nothing is applied until you say yes

All audit outputs go to `workspace/tmp/audit/`. Create the directory if it doesn't exist.

---

## Phase 1: Diagnostic Audits

### Prompt 1: Slash Command Inventory

```
I need you to audit every slash command in this repository. This is a diagnostic -- do not change any files.

Read every file in .github/prompts/ and for each command, record:
- Name
- What workflow and persona it references
- What it actually does (one sentence)
- Whether it overlaps with another command (and which one)

Then categorize every command into one of these buckets:
- ESSENTIAL: I would lose real capability without this
- USEFUL: Adds value but could be merged with something else
- REDUNDANT: Overlaps significantly with another command
- DEAD: Never referenced, no clear use case, or references files that don't exist

Be opinionated. If two commands do similar things, say which one should survive and why. If a command is over-engineered for what it does, say so.

Save the full report to workspace/tmp/audit/01-slash-commands.md with this structure:

## Summary
- Total commands: N
- Essential: N
- Useful: N
- Redundant: N
- Dead: N

## Essential Commands
(table: name, purpose, notes)

## Useful Commands (merge candidates)
(table: name, purpose, merge-into, reasoning)

## Redundant Commands
(table: name, overlaps-with, which-survives, reasoning)

## Dead Commands
(table: name, why-dead)

## Recommendations
(numbered list of specific changes: merge X into Y, retire Z, etc.)
```

### Validation 1

```
Read workspace/tmp/audit/01-slash-commands.md. Verify:
1. Every .github/prompts/*.prompt.md file is accounted for (count them and compare)
2. Every categorization cites specific evidence (not just "seems unused")
3. No command is categorized without reading its actual content
4. The recommendations are actionable (specific merge/retire proposals, not vague)

If anything is missing or unsupported, fix it in place and note what you changed at the bottom of the file.
```

---

### Prompt 2: Workflow Effectiveness

```
I need you to audit the workflow state machine system. This is a diagnostic -- do not change any files.

Read every file in workflows/ including _protocol.md. For each workflow, record:
- Name
- States and transitions
- Which personas it loads
- How much of the prompt is structural overhead (state definitions, transition rules, persona loading) vs. actual task-specific instructions

Then assess each workflow:
- Does the state machine add real structure, or is it ceremony that Copilot mostly ignores?
- Are the transitions meaningful (different behavior per state) or cosmetic (same behavior, different label)?
- Would a single focused prompt achieve the same result with less token overhead?

Be opinionated. If a workflow is over-engineered, say so. If the state machine pattern works well for a specific workflow, say that too.

Save the full report to workspace/tmp/audit/02-workflows.md with this structure:

## Summary
- Total workflows: N
- State machine adds value: N
- State machine is ceremony: N
- Could be a flat prompt: N

## Per-Workflow Assessment
(for each: name, states, verdict: "keeps structure" or "flatten to prompt", reasoning, token overhead estimate as % of prompt that is structural boilerplate)

## The Protocol Contract
- Is _protocol.md actually enforced or aspirational?
- Does the yield/composition system (max depth 2) ever fire in practice?

## Recommendations
(numbered list: which workflows to flatten, which to keep as state machines, what to simplify in the protocol)
```

### Validation 2

```
Read workspace/tmp/audit/02-workflows.md. Verify:
1. Every workflows/*.md file is covered (count them and compare)
2. Each assessment includes the actual states from the workflow (not invented)
3. The "ceremony vs. structure" judgments cite specific evidence (e.g., "states X and Y have identical instructions except for the label")
4. Token overhead estimates are grounded (approximate word counts, not guesses)

If anything is missing or unsupported, fix it in place and note what you changed at the bottom of the file.
```

---

### Prompt 3: Persona Value

```
I need you to audit the persona system. This is a diagnostic -- do not change any files.

Read every file in personas/. For each persona, record:
- Name
- What it's supposed to change about the agent's behavior
- Which workflows/commands reference it
- How many tokens the persona definition adds to the context

Then assess the persona system as a whole:
- Do personas actually change Copilot's behavior, or do they just add token overhead?
- Could the useful behavioral instructions be folded directly into the command prompts that need them?
- Are there personas that are essentially the same thing with different names?

Consider the alternative: no persona layer at all. Instead, each command prompt contains its own inline behavioral instructions and explicit constraints. The behavioral shaping lives in the task prompt itself, not a separate file. This eliminates a layer of indirection and reduces token overhead. Is this project's persona abstraction earning its keep compared to that simpler approach?

Be opinionated. If the persona system is adding complexity without proportional value, say so.

Save the full report to workspace/tmp/audit/03-personas.md with this structure:

## Summary
- Total personas: N
- Adds meaningful behavioral change: N
- Token overhead only: N
- Redundant with another persona: N

## Per-Persona Assessment
(for each: name, behavioral claims, referenced by, token count, verdict, reasoning)

## System-Level Assessment
- Does the persona abstraction layer earn its complexity?
- Would "inline the useful bits into command prompts" be better?

## Recommendations
(numbered list: which personas to keep, which to inline, which to retire)
```

### Validation 3

```
Read workspace/tmp/audit/03-personas.md. Verify:
1. Every personas/*.md file is covered
2. Token counts are real (approximate word count x 1.3, not invented)
3. "Referenced by" actually checked which prompts/workflows mention each persona
4. The system-level assessment addresses the alternative (inline into prompts) with a concrete argument

If anything is missing or unsupported, fix it in place and note what you changed at the bottom of the file.
```

---

### Prompt 4: Memory System Health

```
I need you to audit the memory system. This is a diagnostic -- do not change any files.

Read memory/INDEX.md, then read every file it references. Also read memory/meta/ for governance rules.

For each memory file, record:
- Path
- Priority tier (P0/P1/P2/P3)
- Last meaningful update (check content for dates or staleness signals)
- Whether the content is still accurate (spot-check claims against actual code/data)
- Token count (approximate)

Then assess the system:
- How much of the P0+P1 budget (~50k tokens) is actually used at boot?
- Are the lookup tables in INDEX.md accurate? Do they point to files that exist?
- Is the tier system working (right things at right priority) or are important things buried at P2/P3?
- Is there stale information that could mislead the agent?
- Are the 25 research cards in research/ still current with the project state?

Consider the alternative: instead of a general-purpose knowledge base with 56 files across tiers, a narrow experiment-focused memory. A single structured log tracking every experiment attempted (config, QLIKE result, pass/fail, motivation). The memory serves the research loop directly -- it's not general-purpose knowledge, it's experiment history that feeds the next iteration. Is this project's broad memory system serving the actual workflow, or is it mostly dead weight that the agent loads but never acts on?

Be opinionated about what's working and what's dead weight.

Save the full report to workspace/tmp/audit/04-memory.md with this structure:

## Summary
- Total files: N
- Accurate and useful: N
- Stale or outdated: N
- Missing (referenced but doesn't exist): N
- Estimated boot token load (P0+P1): N tokens

## Per-File Assessment
(table: path, tier, status: current/stale/missing, last-updated, token count, notes)

## Tier System Assessment
- Is the tier structure serving the right information at the right time?
- What's loaded at boot that shouldn't be?
- What's buried at P2/P3 that should be more accessible?

## Research Cards Assessment
- How many of the 25 research/ cards reflect current project state?
- Which are outdated by recent work?

## What's Missing
- Is there experiment history being tracked? (comparison to trial-log pattern)
- Is there a "what we've tried and what happened" record?

## Recommendations
(numbered list: files to update, files to retire, structural changes to the tier system, whether to add experiment logging)
```

### Validation 4

```
Read workspace/tmp/audit/04-memory.md. Verify:
1. The file count matches what's actually in memory/ (ls -R and count)
2. At least 5 files were spot-checked for accuracy (not just listed)
3. Token estimates are grounded (word counts, not guesses)
4. The "What's Missing" section specifically addresses whether experiment outcomes are tracked
5. INDEX.md lookup tables were actually tested (do the file paths resolve?)

If anything is missing or unsupported, fix it in place and note what you changed at the bottom of the file.
```

---

### Prompt 5: Research-to-Experiment Gap

```
I need you to trace the actual path from "I learned something in a research session" to "I ran an experiment to test it." This is a diagnostic -- do not change any files.

Start by reading:
- workspace/research/ (journal, open questions, any session artifacts)
- workspace/configs/ (all YAML experiment configs that exist)
- workspace/models/ (what experiments have actually been run, check for output artifacts)
- The /research prompt in .github/prompts/
- The /train prompt in .github/prompts/
- The /feature prompt in .github/prompts/
- The /evaluate prompt in .github/prompts/
- src/volforecast/config.py (ExperimentConfig dataclass)
- src/volforecast/__main__.py (CLI pipeline entry point)

Now trace the gap. Answer these questions:

1. After /research produces findings, what's the NEXT concrete step to test a hypothesis? Is there a command for it, or does the user have to manually bridge the gap?

2. To run an experiment, the user needs a YAML config. Is there any command that generates one? Or must it be written by hand?

3. After writing a YAML config, the user runs `vol run run-pipeline --config ...`. Does any slash command wrap this, or is it manual CLI work?

4. After an experiment runs, where do results go? Is there a command that interprets them, compares to baselines, and logs the outcome? Or is this manual?

5. Is there any record of "experiments attempted and their outcomes" beyond whatever's in git history?

6. What would a complete research-to-experiment loop look like today with the existing commands? Write out the exact sequence of steps a user would take.

7. Where does the loop break? What's the biggest friction point?

Be specific and opinionated. This is the core problem we're trying to solve.

Save the full report to workspace/tmp/audit/05-research-experiment-gap.md with this structure:

## The Current Path (step by step, what actually exists)

## The Gaps (numbered, specific)

## Friction Analysis
- Biggest friction point and why
- Second biggest friction point and why

## What the CLI Pipeline Already Handles Well

## What's Missing Between the Slash Commands and the CLI Pipeline

## Recommendations
(numbered list of specific new commands or modifications that would close the gaps)
```

### Validation 5

```
Read workspace/tmp/audit/05-research-experiment-gap.md. Verify:
1. The "Current Path" section references actual files and commands (not hypothetical)
2. workspace/configs/ was actually read -- list what YAML configs exist (or note if empty)
3. workspace/models/ was actually read -- list what experiment outputs exist (or note if empty)
4. The gap analysis distinguishes between "no command exists" vs "command exists but doesn't work well"
5. Recommendations are specific enough to implement (not just "add a command for X" but "add a command that does X, Y, Z in sequence")

If anything is missing or unsupported, fix it in place and note what you changed at the bottom of the file.
```

---

### Prompt 6: Session Continuity

```
I need you to assess how well context transfers between Copilot sessions. This is a diagnostic -- do not change any files.

Read:
- The /bootup prompt in .github/prompts/
- The /learn prompt in .github/prompts/
- The bootup workflow in workflows/bootup.md
- memory/person/user.md
- memory/INDEX.md (the boot protocol section)
- workspace/tmp/ (look for session-*-handoff.md files or any session artifacts)
- workspace/research/ (journal entries, if they exist)

Assess:
1. When a new session starts with /bootup, what context does the agent actually receive? Is it enough to pick up where the last session left off?

2. When a session ends, what gets persisted? Does /learn capture everything important, or do things fall through the cracks?

3. Is there a "what I was working on and what's next" handoff mechanism? Does it work?

4. If I started a fresh session right now and typed /bootup, would I know:
   - What the last session accomplished?
   - What experiment was run most recently and what the results were?
   - What the current open questions are?
   - What the recommended next step is?

5. Consider this alternative pattern: a structured trial log that the agent reads at session start before proposing anything. The log contains every experiment attempted (config, result, pass/fail), so the agent immediately knows what's been tried, what worked, and what to try next. How does this project's session continuity compare to that level of structured handoff?

Be opinionated about what's working and what's broken.

Save the full report to workspace/tmp/audit/06-session-continuity.md with this structure:

## What /bootup Actually Loads
(list every file/source it reads, with token estimates)

## What /learn Actually Persists
(list what gets saved, and what doesn't)

## The Handoff Gap
- What information survives between sessions
- What information is lost
- How much manual effort is required to resume context

## Session Start Quality
- If I ran /bootup right now, would I get a useful starting point? Why or why not?

## Recommendations
(numbered list: specific changes to /bootup, /learn, or the handoff mechanism)
```

### Validation 6

```
Read workspace/tmp/audit/06-session-continuity.md. Verify:
1. The /bootup assessment is based on the actual prompt content (not assumed)
2. The /learn assessment is based on the actual prompt content (not assumed)
3. workspace/tmp/ was actually checked for handoff files (list what was found or note if empty)
4. The "Session Start Quality" section is a concrete assessment, not vague
5. Recommendations address both the "session end" and "session start" sides of the problem

If anything is missing or unsupported, fix it in place and note what you changed at the bottom of the file.
```

---

## Phase 2: Synthesis

### Prompt 7: Synthesize and Propose

```
You have completed 6 diagnostic audits of this repository's agentic workflow. Now synthesize the findings into a concrete improvement proposal.

Read all 6 audit reports:
- workspace/tmp/audit/01-slash-commands.md
- workspace/tmp/audit/02-workflows.md
- workspace/tmp/audit/03-personas.md
- workspace/tmp/audit/04-memory.md
- workspace/tmp/audit/05-research-experiment-gap.md
- workspace/tmp/audit/06-session-continuity.md

Also read AGENTS.md for current project identity and constraints.

Now design an improved workflow. Consider these design patterns as OPTIONS -- adopt only what the diagnostics support:

1. **Narrow, constrained prompts** -- each command has one job, explicit output format, specific constraints. No persona swaps or state machine overhead unless the audit found they add real value. (Pattern: instead of a "persona" layer + "workflow" state machine + "prompt" entry point, a single focused prompt with inline behavioral instructions and explicit output schema.)

2. **Validation gates** -- cheap checks before expensive operations. Before running a full experiment: does the YAML config parse? Does the required data exist in workspace/raw/? After running: did the model converge? Is QLIKE reasonable? Is this better than the HAR baseline? Gate ordering: cheapest checks first (file existence, config validation), then computation (run pipeline), then statistical (QLIKE comparison, Diebold-Mariano).

3. **Trial/experiment memory** -- a structured log of every experiment attempted. For each trial, record: experiment name, YAML config used, QLIKE results per horizon, whether it beat baseline, and why it was run (which research finding motivated it). This log feeds into the next research cycle so the agent knows what's been tried and avoids redundant experiments. Format: a single markdown file (workspace/research/experiment-log.md) or structured YAML, not scattered across memory files.

4. **Tight research loop** -- a command or sequence that goes from hypothesis to experiment to logged result without manual bridging. The user should be able to go from "I think feature X improves QLIKE" to "experiment ran, QLIKE improved by N bps, logged" in one or two commands, not five manual steps.

5. **Session continuity by design** -- session start reads structured state (not just free-text notes). Session end writes structured state. The handoff is automatic, not dependent on the user remembering to run /learn. Structured state means: last experiment results, current open questions, recommended next step -- in a parseable format, not buried in prose.

Produce a proposal with these sections:

## Executive Summary
(3-5 sentences: what's wrong, what changes, expected improvement)

## Slash Command Changes
(table: command, action: keep/merge/retire/create/rewrite, details)

## Workflow Changes
(which workflows to keep as state machines, which to flatten, which to remove)

## Persona Changes
(which to keep, which to inline into prompts, which to retire)

## Memory System Changes
(structural changes, new files, retired files, experiment logging design)

## New: Research Loop Design
(the end-to-end flow from hypothesis to logged result -- what commands, what gates, what gets persisted)

## New: Session Continuity Design
(what happens at session start and end, what's automatic vs manual)

## Migration Plan
(ordered list of changes, grouped so each group can be implemented and validated independently)

Do NOT implement anything. This is a proposal for my review.

Save to workspace/tmp/audit/synthesis.md
```

### Validation 7

```
Read workspace/tmp/audit/synthesis.md. Verify:
1. Every recommendation traces back to a specific finding in the audit reports (no unsupported proposals)
2. The slash command table accounts for every existing command (nothing silently dropped)
3. The research loop design is concrete enough to implement (specific commands, specific gates, specific data flow)
4. The session continuity design specifies exactly what files are read/written and when
5. The migration plan is ordered by dependency (things that other changes depend on come first)
6. No change is proposed that contradicts the policy layer (read policy/ files to confirm)

If anything fails these checks, fix it in place and note what you changed at the bottom of the file.
```

---

## Phase 3: Implementation

Phase 3 prompts depend on what the synthesis proposes. After you review and approve the synthesis, come back here and I'll write targeted implementation prompts for each change in the migration plan.

The pattern for each will be:

```
Implementation prompt N:
- What to change (specific files, specific edits)
- Propose the change with a diff preview
- Wait for approval before applying
- Save what was changed to workspace/tmp/audit/implementation-log.md

Validation prompt N:
- Verify the change was applied correctly
- Test that referenced files/commands still work
- Confirm no unintended side effects
```

---

## Cleanup

After all phases are complete:

```
The agentic workflow audit and improvement is complete. Clean up the temporary audit files:
1. Move workspace/tmp/audit/synthesis.md to workspace/docs/workflow-redesign.md (permanent record)
2. Delete workspace/tmp/audit/ (diagnostic artifacts no longer needed)
3. Update memory/INDEX.md if the memory structure changed
4. Commit all changes with message: "refactor: streamline agentic workflow based on diagnostic audit"
```
