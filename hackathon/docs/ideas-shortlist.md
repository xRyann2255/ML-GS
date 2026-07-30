# GS Hackathon Ideas — July 30–31, 2026

**Constraints:** ~10 hrs total · must use internal AI tooling · can't submit the summer vol-forecasting project · one theme: Save Time / Save-Earn Money / Improve Client-User-Developer Experience.

**What wins:** a working demo of a workflow the judges personally do by hand, a stopwatched before/after, a defensible hours-or-£ number, and a credible path to production. Model novelty is irrelevant.

---

## Top 5 picks

| # | Idea | Track | Why |
|---|------|-------|-----|
| 1 | Bug report → failing test agent | Eng | Real market gap; demo proves correctness |
| 2 | Ask-the-Data (NL → time-series + chart) | Desk | Instantly recognisable on the floor |
| 3 | Compute-cost rightsizing agent | Eng | Only idea with a £ figure on screen |
| 4 | Constraint-aware synthetic test data | Eng | Bank-specific; zero prod data = compliance-safe |
| 5 | Desk-commentary / trade-idea drafting agent | Desk | Strongest Save/Earn + client-experience story |

---

## Track A — Desk-facing (traders, strats, quants)

**A1. Ask-the-Data — NL → time-series query + chart**
*Save Time / UX · after BondGPT, Legend AI Query, Kensho*
Ask a question in English, get the query, the chart, and a one-line read. Public data stands in for TSDB/Marquee. Wedge: shape queries (divergence, spikes) plain text-to-SQL can't do.

**A2. Desk-commentary / trade-idea drafting agent**
*Save-Earn Money · after Rogo, AlphaSense*
Overnight moves + signals → formatted desk note with chart, three trade ideas, and a translated client version. Ground every claim in a citation and add a review-before-send gate.

**A3. Backtest scaffolding agent**
*Save Time / DevEx · after AI Quant Forge, Man Group AlphaGPT*
Plain-English strategy description → runnable notebook with tearsheet (Sharpe, drawdown, turnover). Frame as generic desk infrastructure, not vol research.

**A4. Trade-break investigation copilot**
*Save-Earn Money · after Osfin, Xceptor*
Synthetic two-sided trade files with injected breaks; agent matches, classifies break type, hypothesises cause, drafts the resolution note. Prioritise by £ impact.

**A5. Codebase-onboarding copilot**
*DevEx · after Greptile, Augment, DeepWiki*
"Where is X computed and why" over a complex repo, plus an auto-generated architecture diagram and onboarding README. Crowded — needs the generated-doc angle to stand out.

**A6. Research & filings digestion agent**
*Save Time · after AlphaSense, Hebbia*
Public transcripts and 10-Ks → KPI changes, guidance shifts, and management tone shifts with cited snippets. Differentiator is the tone/hedging-language detection, not summarisation.

**A7. Data-catalog discovery assistant**
*Save Time / DevEx · after Legend, Glean*
"Who owns the EOD FX vol surface and how fresh is it?" over a synthetic catalog, returning owner, cadence, and a lineage graph. Risk: reads as generic enterprise search without the lineage twist.

**A8. Client RFQ triage & drafting assistant**
*Save-Earn Money · after LTX RFQ+, Terranoha*
Classify a synthetic inbox of client requests, extract instrument/size/direction, draft the structured reply, route to a pricing stub.

**A9. Incident/runbook copilot for the strat platform**
*Save Time · after PagerDuty SRE Agent, Rootly*
Synthetic logs plus a runbook library; agent triages a mock incident and cites likely cause and fix.

**A10. Model-risk documentation agent**
*Save Time · after ModelOp, ValidMind*
Model code and config → SR 11-7 documentation skeleton (purpose, lineage, assumptions, limitations, tests). Niche, but strong regulatory tailwind (SR 26-2 extends this to LLMs).

**A11. Meeting-note → CRM pipeline**
*Client Experience · after Gong, Zocks*
Transcript → structured CRM entry, follow-up draft, action items. Lowest differentiation on a trading floor.

---

## Track B — Engineering / platform

**B1. Bug report → failing test agent ("repro-bot")**
*Save Time / DevEx*
Issue text → retrieve relevant files → write a pytest that fails → iterate until it fails for the *right* reason. Ship the test, not the fix. Demo on a real closed issue, then check out the historical fix and watch it go green. Pick a repo with a fast test suite.

**B2. Compute-cost rightsizing agent**
*Save-Earn Money · after Kubecost, Cast AI, Sedai*
Job telemetry (requested vs actual) → cluster, recommend new requests with a safety margin, output config diffs and an OOM-risk score. Make cost-per-core-hour an editable input so judges set their own number.

**B3. Constraint-aware synthetic test-data generator**
*DevEx / Save Time · after Gretel, Tonic*
Schema plus English constraints → valid dataset **and** an adversarial edge-case suite with rationale (leap-day settlement, negative rate, holiday roll, zero notional). Demo a naive parser breaking on row 7. Headline the reasoning, not the volume.

**B4. Deprecation → codemod migration agent**
*Save Time / Money · after OpenRewrite, Grit, Sourcegraph Batch Changes*
Deprecation note → find every call site across repos, generate diffs, run tests, open PRs. Include one semantic case regex can't handle (renamed kwarg, changed return type).

**B5. Flaky-test triage & auto-quarantine**
*Save Time / DevEx · after Datadog Test Optimization, Trunk*
Detect flakes statistically, then have the LLM **classify the cause** (timing, ordering, shared state, external dep) and open quarantine PRs. Detection isn't the AI part — classification is.

**B6. House-style PR reviewer from your own review history**
*DevEx · after Greptile, CodeRabbit*
Mine a repo's historical PR comments into a house-style ruleset, then review a fresh PR citing "reviewers said this 23 times before." Only worth taking with that wedge — generic review is a solved product.

**B7. Runbook → executable diagnostic agent**
*Save Time / DevEx · after PagerDuty SRE Agent, Kubiya*
Parse a markdown runbook, execute **read-only** diagnostics against a mock service, return a triage summary and root-cause hypothesis. Read-only doubles as the safety story. Time goes on the mock env, not the agent.

**B8. Documentation-drift detector**
*DevEx · after Swimm, Unblocked*
Given a diff, find docs referencing changed symbols, flag contradictions, draft patches. Lowest wow-factor, cheapest build — good insurance if you're behind at hour five.

---

## Avoid

- Anything adjacent to the vol-forecasting summer project.
- Anything needing model training that won't finish, or production integrations you can't get approved.
- Anything requiring sensitive data you can't show on screen — default to synthetic or public data everywhere.
- The four things other teams will definitely submit: chatbot over Confluence, generic AI code reviewer, generic "explain this codebase," test generation with no angle.

## 10-hour plan

| Hours | Focus |
|---|---|
| 0–1 | Lock scope; assemble synthetic/public data |
| 1–4 | Core pipeline end-to-end, ugly but working |
| 4–6 | The wow layer (chart, narration, audit panel) |
| 6–8 | Harden 2–3 demo paths; pre-record a fallback video |
| 8–9 | Impact maths and slides |
| 9–10 | Rehearse the 3–5 min pitch |

**Pivot rule:** if the core loop is still unreliable at hour 4, hard-code the demo path rather than chase generality.

**Pitch shape:** name the persona and the daily pain → show the timed manual "before" → run it live → state hours or £ saved and the path to production → one honest risk plus mitigation.

---

*Vendor and startup figures referenced above are self-reported marketing or press-release numbers — present them as industry estimates, not audited facts.*