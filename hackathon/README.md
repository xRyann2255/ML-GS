# Trailhead

**Point it at a repo, get one self-contained HTML file that teaches that repo to a new joiner — and that shows its own evidence for every claim it makes.**

Built for the GS Hackathon (theme: *Improve the Developer Experience*), 30–31 July 2026, inside the 10-hour budget.

The pitch is not "the model wrote docs." It is **"the model writes prose, the machine checks the facts — here are the claims it caught the model inventing."** Every factual sentence in a generated walkthrough is anchored to a `file:line` range, hashed, and re-verified by ordinary code after the model wrote it. Claims that fail are deleted, and the deletion count is shown on the page.

---

## See it in 30 seconds

No setup. Every artifact opens from `file://` with the network off.

```bash
# the demo bundle (two walkthroughs behind a switcher in the top bar)
start demo/trailhead-demo.html          # Windows
open  demo/trailhead-demo.html          # macOS

# or any pre-generated walkthrough in out/, e.g. the committed demo repo
start out/restored.html
```

The demo bundle carries a synthetic repo (`payments-core`) and a real one (this repository) behind a switcher — a demo-only arrangement: a real generated artifact carries exactly one payload, and the gate checks every payload in the bundle either way. `out/` also holds walkthroughs generated against real repos nobody on the team had read — that is the credibility story, not a curated example.

## Why this is not "explain my codebase"

1. **It generates an artifact, not a conversation.** A new joiner walks through it without knowing what to ask.
2. **Every factual sentence is anchored and re-checked after it was written.** Failed claims are *deleted* and counted on screen.
3. **Command output is real.** Setup and test commands are actually executed; the page embeds captured exit codes, stdout, and timings. A failing command is shown failing, under a known-broken banner.

## Architecture

Five stages. **Only stage 3 touches a model.** A model cannot verify itself, so everything that checks anything is ordinary code.

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
| 1 Survey | no | File tree, import edges, entry points, git churn — stdlib `ast`, pure Python |
| 2 Map | no | Collapse to module level; layout computed at generation time, none in the page |
| 3 Narrate | **yes** | Prose. One prompt pack per unit; answers carry claims + verbatim quotes |
| 4 Verify | no | Resolve quotes to line ranges, hash excerpts, delete what fails |
| 5 Render | no | `verified.json` → one HTML file; knows only the fixed block-type vocabulary |

Between Map and Narrate, a command runner executes an allowlisted set of setup/test commands (deny by default, 60 s per command, 120 s total). A command that was not executed has no exit code or output fields to fabricate.

Output contracts are versioned (`trailhead/verified@3` current; the gate also accepts @1/@2) and frozen in `docs/verified-contract.md`.

### The one technique that matters

**Never ask the model for line numbers — ask it to quote.** The model sees files with line numbers pre-pended and must return each claim with the verbatim snippet it cites; code then finds the snippet and derives the range itself. Models count badly and copy well. This is the difference between a ~40% claim-drop rate and ~3% — and a snippet not found verbatim is still deleted.

## Run it

Requirements: Python 3.11+ and Node.js. The generator is pure stdlib — there is nothing to `pip install`. (The only optional dependency is `anthropic`, and only for the live-API route below.)

All commands run from `hackathon/`. On Windows, replace `python` with `py -3.11` (works in both Git Bash and PowerShell; in PowerShell set the path with `$env:PYTHONPATH="src"`).

### Generate a walkthrough

Narration runs in two passes with no API key required. Stage 3's prompts are written to disk as self-describing JSON packs; any coding agent answers them; the pipeline verifies whatever came back.

```bash
# Pass A — survey, map, run commands, emit one prompt pack per unit, stop
PYTHONPATH=src python -m trailhead build <repo> -o out/repo.html \
    --run-commands safe --emit-prompts -v

# Answer each pack in out/.trailhead/prompts/*.json — every pack contains its own
# schema and the exact output path it must be written to (out/.trailhead/narration/)

# Pass B — verify, render, gate
PYTHONPATH=src python -m trailhead build <repo> -o out/repo.html \
    --run-commands safe --from-stage narrate --offline --gate -v
```

To call a model directly instead: `pip install anthropic`, set `ANTHROPIC_API_KEY` (optionally `TRAILHEAD_BASE_URL` for a gateway), and pass `--provider claude`.

Useful flags: `--run-commands {safe,none}`, `--from-stage {survey,map,commands,narrate,verify,render}` (every stage reads and writes disk artifacts in `out/.trailhead/`, so any stage can be resumed), `--max-units N`, `--gate`. Exit codes: `0` ok, `1` generation failed, `2` usage, `3` gates failed.

Every build prints its ledger, e.g. `claims 16  verified 12  inferred 3  DROPPED 1`, plus provenance lines for anything that degraded.

### Gate checks

Three deterministic Node scripts (zero dependencies) must all exit 0:

```bash
node tools/check-bundle.js        # self-containment: one file, zero external requests, size caps
node tools/check-fixtures.js     # the hand-written stage fixtures agree with each other
node tools/verify-contract.js    # re-resolves every anchor and recomputes every sha256 from the bundle
```

The first and third default to `demo/trailhead-demo.html` and accept any generated file as an argument; `verify-contract.js` also takes a bare `verified.json`. `--gate` on a build runs the two artifact gates against the file it just wrote.

### Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

587 tests, including end-to-end builds of four synthetic fixture repos (`tests/repos/`) that each force a different degradation path, checked against `expect.json` oracles. Known issue: 13 tests in `tests/test_render.py` currently fail — they eval the pre-@3 template's JS under Node and are stale against the shipped template. The pipeline and all three gates are unaffected.

## What the verifier enforces

- Every anchor carries a sha256 over its exact source excerpt. Stage 4 recomputes it against the repo; `verify-contract.js` recomputes it again from the files embedded in the shipped bundle. Tampering with one bundled line fails the gate.
- Claims are deleted for a fixed vocabulary of reasons (`snippet not found verbatim in file`, `excerpt hash mismatch — file changed after narration`, …). The resolver never fuzzy-matches or repairs; a near-miss is a drop.
- Dropped claims render only in the audit ledger, with their reason, and the dropped count sits in the top bar. Hiding it would defeat the point.
- `inferred` claims carry no anchor and are visibly marked — they are not allowed to look verified.
- Checkpoint (quiz) answer keys are derived from `survey.json` static analysis only, seeded by the repo commit. No free-text questions: there is no model in the page to grade them.
- Stats-tile numbers are computed by the pipeline, never authored by the model.

## Layout

```
hackathon/
├── README.md                 this file
├── briefs/                   per-stage build briefs (A-survey … E-integration)
├── demo/trailhead-demo.html  two-payload demo bundle, 165 KB, passes all gates
├── docs/                     walkthrough-spec.md   spec for the generated page (authoritative)
│                             verified-contract.md  frozen field-by-field payload contract
│                             pipeline-contracts.md stage-to-stage artifact contracts
│                             ideas-shortlist.md    pre-hackathon idea selection
├── fixtures/                 hand-written stage payloads; verified.parity.json is the minimal @3 reference
├── out/                      pre-generated walkthroughs (restored, imc, qrt, ryanatron-v2, …)
├── restored/                 the committed proving-ground repo out/restored.html is generated from
├── src/trailhead/            the generator — pure-stdlib Python package
├── template/                 hand-built template walkthrough and its build pipeline
├── tests/                    unittest suite + four synthetic fixture repos with oracles
└── tools/                    the three gate checks + inline-fixture.js (demo data splicing)
```

If code and `docs/walkthrough-spec.md` disagree about the page, the spec wins; `docs/verified-contract.md` wins about the payload.

## Known limits

- **Python repos only.** A deliberate scope decision.
- **The trace stop's call-chain hops are hand-verified input**, not generated: `fixtures/trace.<repo-dir>.json` exists only for `restored/`. Any other repo degrades to a labelled callout with zero anchored hops. Degradation is always labelled — no stop is ever silently omitted.
- **The map is capped** at 14 node groups and 7 columns.
- **Narration quality depends on the agent answering the packs.** The pipeline does not make bad prose good — it only guarantees that whatever survives verification is anchored to real code, and that everything else is deleted in the open.
