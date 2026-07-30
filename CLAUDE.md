# Trailhead — GS Hackathon, 30–31 July 2026

> **TEMPORARY FILE.** The real project instructions are archived at `CLAUDE.vol-project.md`.
> To restore after the hackathon:
> ```bash
> rm CLAUDE.md && git mv CLAUDE.vol-project.md CLAUDE.md
> ```
> Everything below applies only while the hackathon is running.

---

## What we are building

**Trailhead.** Point it at a repo, get one self-contained HTML file that teaches that repo to a new joiner — and that shows its own evidence for every claim it makes.

**Theme:** Improve the Developer Experience.

**Why it is not "explain my codebase":** other entrants build a chatbot you ask questions of. This generates an artifact you walk through without knowing what to ask, and every factual sentence is anchored to a `file:line` and re-checked after it was written. Claims whose anchors fail are deleted and counted on screen. Setup commands are actually executed and their real output embedded, failures included.

The pitch is **"the model writes prose, the machine checks the facts — here are the eight claims it caught the model inventing."**

---

## Working mode

**This inverts the archived vol-project rules. Read that as deliberate.**

The vol project is research: go deep, do not rush to code, no plans unless asked. The hackathon is the opposite — a fixed 10-hour budget with a demo at the end.

**Do:**
- Ship working code. Prefer a rough end-to-end loop over any polished fragment.
- Make the call and state it. Do not stop to ask about anything that has a defensible default.
- Test the deterministic stages (Survey, Verify, the quote→line resolver). They are pure functions with clear contracts and they are where correctness actually lives.
- Skip TDD on Render and anything visual. Iterate against the browser instead.
- Run the gate checks before saying anything works.

**Do not:**
- Refactor anything outside `hackathon/`.
- Add a dependency without a one-line reason. Stdlib `ast` beats tree-sitter here.
- Widen language support, add a second output format, or generalise the pipeline. Python-only is the plan.
- Chase generality after hour 4 — see the pivot rule.

**Time is the binding constraint, not tokens.** 10 hours total, inside working hours, 30–31 July.

---

## Where things are

```
hackathon/
├── README.md                 brief, architecture, state, build order
├── docs/
│   ├── ideas-shortlist.md    all 19 candidate ideas + the 10-hour plan
│   └── walkthrough-spec.md   THE SPEC for the generated artifact — read before touching render
├── demo/trailhead-demo.html  working front-end on a synthetic repo (stage 5, prototyped)
├── tools/
│   ├── check-bundle.js       self-containment + spec §1 checks
│   └── verify-contract.js    anchor + contract checks (stand-in for stage 4)
├── src/trailhead/            generator package — not started
├── tests/                    generator tests — not started
└── fixtures/                 hand-written verified.json fixtures
```

`hackathon/docs/walkthrough-spec.md` is authoritative for anything the HTML does. If code and spec disagree, fix one of them on purpose — do not let them drift.

---

## Architecture

Five stages. **Only stage 3 calls a model.**

```
repo ──▶ 1 SURVEY ──▶ survey.json ──▶ 2 MAP ──▶ map.json
                          │                        │
                          └──▶ 3 NARRATE (LLM) ──▶ content.json
                                                     │
                                    4 VERIFY ◀───────┘
                                        │
                    verified.json + verification-report.json
                                        │
                                   5 RENDER ──▶ trailhead.html
```

| Stage | Model? | Job |
|---|---|---|
| 1 Survey | no | File tree, import edges, entry points, git churn |
| 2 Map | no | Collapse to module level, compute layout at generation time |
| 3 Narrate | **yes** | Prose. One small call per unit, each returning claims + verbatim quotes |
| 4 Verify | no | Re-read anchors, hash-match excerpts, delete what fails |
| 5 Render | no | `verified.json` → one HTML file, knows only the 8 block types |

Plus a command runner that executes setup and test commands and captures real exit codes, stdout, and timings.

---

## Non-negotiables

Break any of these and the project becomes a generic codebase explainer with no pitch.

1. **Only stage 3 touches a model.** A model cannot verify itself. Everything that checks is ordinary code.
2. **No factual sentence without a resolvable anchor.** Unanchorable prose is cut or downgraded to `inferred` and visibly marked.
3. **Deleted claims are counted on screen.** Hiding the drop count defeats the entire point.
4. **Command output is real.** Never synthesise stdout, exit codes, or timings. A failing command is shown failing.
5. **One HTML file, zero external requests.** It must open from `file://` with the network off.
6. **Checkpoint answer keys come from `survey.json`,** never from the model. No free-text questions — there is no model in the page to grade them.
7. **Never ask the model for line numbers — ask it to quote.** Feed files with line numbers pre-pended, require the verbatim snippet, then resolve the range in code. Models count badly and copy well. This is the difference between a 40% drop rate and ~3%.

**Never cut, however far behind:** claim markers, the audit panel, the dropped-claim count.

---

## Gate checks

Both must exit 0 before claiming anything works:

```bash
cd hackathon
node tools/check-bundle.js
node tools/verify-contract.js
```

Do not report a stage as done on the strength of reading the code. Run the checks and quote the output.

---

## Build order and pivot rule

| Hours | Ship |
|---|---|
| 0–1 | Freeze `verified.json`; hand-write a fixture so render stays testable |
| 1–3 | Survey: tree, imports, entry points, git churn |
| 3–4 | Command runner with real capture |
| 4–5 | Narrate: per-unit calls, quote-based claims |
| 5–6 | Verify: quote → line resolution, hash check, deletions |
| 6–7 | Wire render to real `verified.json`; regenerate the demo from a real repo |
| 7–8 | Checkpoint generation from `survey.json` |
| 8–9 | Generate against two repos nobody has read; fix what breaks |
| 9–10 | Rehearse the pitch |

**Pivot rule:** if the core loop is still unreliable at hour 4, hard-code the demo path rather than chase generality.

**Cut list, in order:** stop 12 → stop 15 → stop 10 → checkpoint B → stop 7.

---

## Out of scope — do not touch

`notes/`, `guides/`, `reference/`, `docs/`, `archive/`, `qr-decode/`, and everything in `deliverables/` belong to the vol-forecasting project. The hackathon rules forbid submitting that work, and nothing in it needs to change this week.

`.claude/skills/` holds vol-project skills (`write-chapter`, `research`, `sync-docs`, …). Leave them alone; they will be wanted again on 1 August.

---

## Conventions

- Conventional commits with a scope, matching repo history: `feat(hackathon):`, `docs(hackathon):`, `fix(hackathon):`.
- Commit or push only when asked.
- Python 3.11, stdlib first. `ast` for Survey.
- Node is available and is what the gate checks run on.

**`docs-only` branch:** `hackathon/` is deliberately not synced there — a folder that will contain `.py` files does not belong on a branch that must have none. If you do touch that branch, the rules are in `CLAUDE.vol-project.md` and the `.py` prohibition is absolute.

---

## Open decisions

1. **Which internal GS tool does Narrate call?** It sits behind an interface so it changes nothing structural, but the brief requires naming it and its rate limits set how many modules can be narrated in a live on-stage run.
2. **Which repo do we demo on?** Mid-size, unread by the team, fast test suite. Live generation on an unfamiliar repo is the whole credibility story.
3. **Language scope.** Recommend Python-only via `ast` and say so plainly rather than implying more.
