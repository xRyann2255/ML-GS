# Trailhead — GS Hackathon, 30–31 July 2026

**One line:** point it at a repo, get one self-contained HTML file that teaches that repo to a new joiner — and that shows its own evidence for every claim it makes.

**Theme:** Improve the Developer Experience.

**Guardrails from the brief:** 10 hours total, inside working hours. Must use internal AI tooling. Cannot submit the summer vol-forecasting project (nothing here touches it).

---

## Why this is not "explain my codebase"

Most entrants will build a chatbot you ask questions of. Two differences:

1. **It generates an artifact, not a conversation.** A new joiner walks through it without knowing what to ask.
2. **Every factual sentence is anchored to a `file:line` and re-checked after it was written.** Claims whose anchors don't resolve are *deleted*, and the deletion count is on screen. Setup commands are actually executed and their real output embedded — including the ones that fail.

The pitch is not "the model wrote docs." It is **"the model writes prose, the machine checks the facts, and here are the eight claims it caught the model inventing."**

---

## Layout

```
hackathon/
├── README.md                    this file
├── docs/
│   ├── ideas-shortlist.md       all 19 candidate ideas + the 10-hour plan
│   ├── walkthrough-spec.md      full spec for the generated HTML artifact
│   └── verified-contract.md     FROZEN generator↔render contract — read first
├── demo/
│   └── trailhead-demo.html      working front-end, synthetic repo, 65 KB
├── tools/
│   ├── check-bundle.js          structural checks (spec §1, tests 1 + 12)
│   ├── verify-contract.js       anchor + sha256 + contract checks (tests 3–6)
│   └── inline-fixture.js        splice a verified.json into the demo bundle
├── src/trailhead/               generator package — not started
├── tests/                       generator tests — not started
└── fixtures/
    └── verified.sample.json     the frozen reference payload, 13 anchors
```

## Run it

```bash
# view the demo (self-contained — works with the network off)
start demo/trailhead-demo.html          # Windows
open  demo/trailhead-demo.html          # macOS

# gate checks — both must exit 0
node tools/check-bundle.js
node tools/verify-contract.js

# the same contract checks, straight on a payload
node tools/verify-contract.js fixtures/verified.sample.json

# the demo's data comes from the fixture — edit the JSON, never the HTML
node tools/inline-fixture.js
```

`check-bundle.js` proves the file is genuinely self-contained and spec-conformant.
`verify-contract.js` re-checks every anchor in the embedded data and asserts the
top-bar report matches what the page actually shows. It has already caught one
real inconsistency (badge said 2 failing commands, page displayed 1).

---

## Architecture

Five stages. **Only stage 3 calls a model.** That is what makes the trust claim real rather than rhetorical — a model cannot verify itself, so everything that does the checking is ordinary code.

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

| Stage | Model? | ~LOC | Job |
|---|---|---|---|
| 1 Survey | no | 250 | File tree, import edges, entry points, git churn → `survey.json` |
| 2 Map | no | 100 | Collapse to module level, compute layout at generation time |
| 3 Narrate | **yes** | — | Prose, one small call per unit, each returning claims + quotes |
| 4 Verify | no | 150 | Re-read anchors, hash-match excerpts, delete what fails |
| 5 Render | no | 400 | `verified.json` → one HTML file. Knows only the 8 block types |

Plus a command runner (~80 LOC) that executes the setup and test commands and captures real exit codes, stdout, and timings.

### The one technique that matters

**Never ask the model for line numbers. Ask it to quote.** Feed it the file with line numbers pre-pended and require each claim to carry the verbatim snippet it cites; then code searches the file for that snippet and derives the range itself. Models are bad at counting lines and good at copying text. This is the difference between a 40% drop rate (embarrassing on stage) and ~3% (credible), and it costs nothing — a snippet not found verbatim is still deleted.

---

## State

| Piece | State |
|---|---|
| Idea shortlist and 10-hour plan | done — `docs/ideas-shortlist.md` |
| HTML artifact spec | done — `docs/walkthrough-spec.md`, 9 sections, 12 acceptance tests |
| `verified.json` contract | **frozen** — `docs/verified-contract.md`, `trailhead/verified@1` |
| Reference fixture | **done** — `fixtures/verified.sample.json`, 13 sha256 anchors |
| Front-end (render output) | **working** — `demo/trailhead-demo.html`, all 9 block types |
| Gate checks | **working** — `tools/`, both passing on HTML and on JSON |
| Survey / Map / Narrate / Verify code | not started |

The demo is driven by `fixtures/verified.sample.json`, spliced in by
`tools/inline-fixture.js`; the renderer contains no reference to the sample repo.
It is a real render, not a mockup — so stage 5 is effectively prototyped and the
remaining work is stages 1–4.

Every anchor now carries a mandatory `sha256` over its excerpt, and
`verify-contract.js` recomputes all 13. Tampering with one bundled source line
fails the gate with a hash mismatch on both the claim and the trace hop that cite
it — the mechanic the pitch rests on is enforced, not asserted.

## Build order

| Hours | Ship |
|---|---|
| 0–1 | Freeze `verified.json`; hand-write a fixture so render is testable immediately |
| 1–3 | Survey: tree, imports, entry points, git churn |
| 3–4 | Command runner with real capture |
| 4–5 | Narrate: per-unit calls, quote-based claims |
| 5–6 | Verify: quote → line resolution, hash check, deletions |
| 6–7 | Wire render to real `verified.json`; regenerate the demo from a real repo |
| 7–8 | Checkpoint generation from `survey.json` |
| 8–9 | Generate against two repos nobody on the team has read; fix what breaks |
| 9–10 | Rehearse the pitch |

**Pivot rule:** if the core loop is still unreliable at hour 4, hard-code the demo path rather than chase generality.

**Never cut:** claim markers, the audit panel, the dropped-claim count. Remove those and it becomes another generic codebase explainer.

## Open decisions

1. **Which internal GS tool does Narrate call?** It sits behind an interface so it changes nothing above, but the brief requires naming it, and its rate limits set how many modules can be narrated inside a live on-stage run.
2. **Which repo do we demo on?** Should be mid-size and unread by the team — live generation on an unfamiliar repo is the whole credibility story. Needs a fast test suite so the command runner finishes on stage.
3. **Language scope.** Python-only Survey via `ast` is a few hours; multi-language via tree-sitter is a day. Recommend Python-only and say so plainly.

## Note on `docs-only`

These files used to live in `deliverables/`, which the `docs-only` sync copies for restricted machines. They no longer do, so **hackathon files will not appear on `docs-only`** until `hackathon/` is added to the sync list in `CLAUDE.md` and the `sync-docs` skill. Deliberate for now — a dev folder with source in it does not belong on a branch that must contain no `.py` files.
