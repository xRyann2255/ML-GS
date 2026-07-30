# Workflow: Research

Implements [_protocol.md](_protocol.md). Structured research session — explore one topic in depth on real data, document findings, and update the research journal.

---

## Entry Conditions

Enter when:
- User explicitly uses `/research`.
- Task pattern matches: "explore", "research", "investigate feature", "what does the data show"
- Bootup workflow routes here after user states an exploration goal.

---

## State Machine

```
ORIENT → FOCUS → EXPLORE → DOCUMENT → DONE
```

### ORIENT

**Persona:** VOL-RESEARCHER
**Memory:** Load `memory/person/user.md` + `memory/INDEX.md`. Load P1 research cards relevant to the session topic.

**Actions:**
1. Read `workspace/research/research-journal.md` for recent findings and session history.
2. Read `workspace/research/open-questions.md` for unresolved topics.
3. Read `workspace/docs/vol-project-ref/INDEX.md` for the authoritative project spec — use chapter links to drill into feature formulas, model architecture, or milestones relevant to the exploration topic.
4. Read `workspace/docs/vol-learning-guide/INDEX.md` for comprehensive theory and equations — use chapter links to drill into full mathematical derivations, estimator properties, and proofs when exploring why a formula works or verifying an implementation.
4. Identify where the last session left off.
5. If user has stated a topic, confirm it. If not, propose 2–3 topics from open questions.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| Topic confirmed by user | → FOCUS |
| No topic stated, user chooses from proposals | → FOCUS |
| User wants to continue previous session | → FOCUS (load prior context) |

Checkpoint: record chosen topic and rationale.

### FOCUS

**Persona:** VOL-RESEARCHER
**Memory:** Load feature layer cards, data access cards, and evaluation framework cards from `memory/research/` relevant to the chosen topic.

**Actions:**
1. Define the research question precisely (one sentence).
2. Identify what data is needed (symbol, date range, frequency, data source).
3. Identify what computation to perform (feature, model, statistical test).
4. State the expected outcome (what would confirm/refute the hypothesis).
5. Check for potential pitfalls: look-ahead bias, COVID regime, insufficient data.
6. Present the **Hypothesis Card** (mandatory before moving to EXPLORE):

```
## Hypothesis Card
- Question: [one testable sentence]
- Feature layer: [0-6]
- Data needed: [symbols, date range, frequency, source]
- Method: [exact computation or statistical test]
- Success criterion: [quantitative threshold that confirms]
- Null hypothesis: [what rejection looks like]
- Pitfalls: [look-ahead bias, COVID, survivorship, etc.]
```

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| Hypothesis card completed, data identified | → EXPLORE |
| Data not available or question too broad | → ORIENT (refine scope) |

Checkpoint: the hypothesis card itself.

### EXPLORE

**Persona:** VOL-RESEARCHER
**Memory:** Load relevant skill SKILL.md (DATA_INGEST, FEATURE_BUILD, or EVALUATE as needed).

**Subagent delegation:** When exploration involves multiple independent computation slices (e.g., multi-symbol analysis, per-horizon comparison, multi-feature ablation), spawn subagents to keep the orchestrator's context lean:
- Each subagent gets ONE slice (e.g., "compute QLIKE for symbols AAPL,MSFT,GOOG at h=1")
- Orchestrator stays in EXPLORE state, collecting results into a summary table
- Subagent context packet includes: hypothesis card, data location, computation spec, expected output format
- Use Explore agent for read-only research; use full subagent for computation that produces artifacts
- Subagent model pinning: per `policy/subagent_protocol.md`

**Spawn threshold for research:**
- 1 symbol, 1 horizon, 1 feature → inline (orchestrator does it)
- 3+ symbols OR 2+ horizons OR computation involves iterative debugging → spawn subagents

**Actions:**
1. Fetch required data using DATA_INGEST skill or direct Python queries.
2. Compute features/metrics as defined in FOCUS (delegate to subagents if above threshold).
3. Visualize results (distributions, time series, correlations).
4. Compare against expected outcome — does the data support the hypothesis?
5. If results are surprising, dig deeper: check for data quality issues, try subsets, test robustness.

**Research discipline:**
- One topic deep per session — resist the urge to branch.
- Verify on real data before proposing architecture changes.
- Note any look-ahead bias risks in the computation.
- If COVID period is included, note its effect explicitly.

> **Precedence:** Conditions are evaluated top-to-bottom; first match wins.

| Condition | Transition |
|-----------|-----------|
| Analysis complete, findings clear | → DOCUMENT |
| Results inconclusive, more data needed | → FOCUS (refine question) |
| Unexpected finding worth deeper investigation | → FOCUS (new sub-question, max 1 recursion) |
| Data access failure | → DOCUMENT (record partial findings + blocker) |

Checkpoint: record findings with evidence (numbers, plots, tables).

### DOCUMENT

**Persona:** VOL-RESEARCHER
**Memory:** No additional loads.

**Actions:**
1. **Update research journal** (`workspace/research/research-journal.md`) using this template:

```
## YYYY-MM-DD -- [Title]

**Hypothesis card:** [copy from FOCUS]

**Result:** confirmed / rejected / inconclusive
**Key statistic:** [number with CI or p-value]
**Effect size:** [practical significance for QLIKE, in bps if possible]
**Robustness:** [N symbols tested, regime stability, subsample checks]
**Implication:** [what this means for model design]

**Method:** [what was computed, on what data]
**Surprise:** [anything unexpected]
**Open threads:** [new questions spawned]
```

2. **Update open questions** (`workspace/research/open-questions.md`):
   - Mark resolved questions as answered (with date and journal reference).
   - Add new questions spawned by this session.

3. **Update feature notes** (if findings affect feature design):
   - Update relevant feature layer documentation in `workspace/research/`.
   - Update relevant memory cards in `memory/research/` if findings change design decisions.

4. **Update weekly progress log** (`workspace/research/weekly-progress.md`):
   - Append a bullet under the current week's Shipped/Decided/Learned section as appropriate.
   - Keep entries concise (one line per finding/decision).
   - Skip if session was inconclusive with no new findings.

5. **Present summary to user:**
   - One-paragraph finding summary.
   - Key numbers/evidence.
   - Recommended next exploration session topic.
   - Numbered next-steps.

6. Exit per `_protocol.md` exit contract.

→ DONE.

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| ORIENT | VOL-RESEARCHER |
| FOCUS | VOL-RESEARCHER |
| EXPLORE | VOL-RESEARCHER |
| DOCUMENT | VOL-RESEARCHER |

---

## Error Handling

Per `_protocol.md` error hooks (4-class model).
- Data access failures: note in journal as blocker, propose alternative data source or approach.
- Inconclusive results after 2 refinement rounds: document partial findings, add to open questions, move on.
- Computation errors: debug in-session (hand off to `debug.md` only if complex).

---

## Constraints

- **One topic deep per session.** Do not branch into multiple unrelated explorations.
- **Real data only.** Never draw conclusions from synthetic data or assumptions without explicit statement.
- **No premature architecture.** Research findings inform architecture — never propose model changes without data evidence.
- **Always state COVID handling.** If the analysis period includes Feb–Jun 2020, note its inclusion/exclusion explicitly.
- **Log-RV space.** All RV analysis should be in log space unless explicitly comparing raw vs. log.
- **Document everything.** Even null results are valuable — they narrow the search space.
