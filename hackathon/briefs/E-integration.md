# Owner E — Integration, hygiene, demo repos, the pitch

## Paste this into Claude Code

```
I own integration for Trailhead, a hackathon project in this repo: the CLI that
wires the five stages, the gate checks, the fixtures, choosing the demo repos,
and the pitch.

Read in this order:
  CLAUDE.md
  hackathon/briefs/E-integration.md   <- my brief, follow it
  hackathon/briefs/README.md          <- what the other four are doing
  hackathon/README.md                 <- stale in places, I own fixing it
  hackathon/docs/pipeline-contracts.md + verified-contract.md

I own src/trailhead/cli.py, render.py, tools/, fixtures/, and all the docs. I do
not implement stages 1-4 — A, B and C own those.

First job is repo hygiene, before anyone commits: hackathon/restored/ is a
14 MB copy of the vol-forecasting project sitting untracked inside the hackathon
folder. Help me deal with that first.
```

## Mission

Four people are building parts. You own whether the parts become a thing, and
whether that thing survives contact with a repo nobody has read.

You also own the pitch. The demo runs on your laptop.

## You own

```
src/trailhead/cli.py        `trailhead <repo>` — wires the five stages
src/trailhead/render.py     stage 5 — verified.json -> HTML (D owns the template)
tools/*.js                  the three gate checks
fixtures/*                  shared state — you are the gatekeeper
docs/*, README.md, briefs/  keeping them true
```

**Never touch:** `survey.py` `map.py` `checkpoints.py` (A), `narrate.py`
`prompts.py` `provider.py` (B), `verify.py` `resolve.py` `runner.py` (C),
`demo/trailhead-demo.html` (D).

## Hour 0 — hygiene, before anyone commits

**1. `hackathon/restored/` is a hazard.** 1065 files, 14 MB, 455 `.py`, and it is
a full copy of the `ml-vol-estimator` vol-forecasting project sitting inside the
hackathon folder. Three problems compounding:

- The brief forbids submitting the vol project, and this is it, inside `hackathon/`.
- It is untracked and **not** gitignored — `git add hackathon/` commits all 1065 files.
- 455 `.py` files would make the `docs-only` no-Python rule unenforceable.

Move it out of `hackathon/` or gitignore it. Decide out loud, then do it.

**2. Nothing in `hackathon/` is committed** except the demo and the ideas
shortlist. Land the docs, fixtures, tools and briefs before four people start
branching on top of nothing.

**3. Two doc bugs, both cheap:**
- `README.md` says Survey is "not started" — it isn't. `survey.py` has two
  functions and 8 passing tests. A will read that table and be misled.
- `docs/walkthrough-spec.md` §3 says "13 stops in 5 tracks"; the tables list 16,
  numbered 0–15. D is building a sidebar against that.

**4. Stray `bash.exe.stackdump`** in the repo root and in `hackathon/`.

## Then: the CLI

```bash
trailhead <repo> -o trailhead.html
```

Five stages behind one command, each writing its intermediate JSON to a
`--work-dir` so any stage can be re-run alone. `--stages 1,2` and
`--from-content content.json` will save you an hour at hour 8 when a stage 3 run
costs two minutes and you are debugging stage 5.

Stage 5 (`render.py`) is thin: read `verified.json`, splice into D's template,
write one file. `tools/inline-fixture.js` already does exactly this in Node —
port it or shell out, but the HTML template stays D's.

## Demo repos — decide by hour 2

Open decision #2, and it is yours. Criteria, in order:

1. **Nobody on the team has read it.** Live generation on an unfamiliar repo is
   the entire credibility story. A repo you know is a demo of nothing.
2. **Python, mid-size** — 30–80 files, 5–15 modules. Under 5 and the map is
   empty; over 40 and D's density cap has to save you.
3. **Fast test suite** — the command runner has to finish on stage. Under 60 s.
4. **Setup that works on your laptop, offline if possible.** A repo needing a
   database is a demo that fails at the worst moment.

Pick **two**, and generate against both by hour 8. The second one is where you
find what the first one hid. Ask B for their rate limit first — it caps how many
modules can be narrated live.

## Gate checks — you own all three

```bash
cd hackathon
node tools/check-bundle.js      # self-containment + spec §1
node tools/verify-contract.js   # anchors, sha256, contract
node tools/check-fixtures.js    # the fixture chain agrees with itself
```

All three exit 0 or nobody claims anything works. `verify-contract.js` has
already caught one real inconsistency — the badge said 2 failing commands while
the page showed 1. That is the gate earning its keep.

**Wire these into a git hook or a one-line `make gate`** so nobody has to
remember.

## The calls only you can make

- **The pivot, at hour 4.** If the core loop is unreliable, hard-code the demo
  path. Chasing generality after hour 4 is how this ends with nothing to show.
- **The cut list, in order:** stop 12 → stop 15 → stop 10 → checkpoint B → stop 7.
- **Never cut:** claim markers, the audit panel, the dropped-claim count.
- **Contract changes.** If A, B, or C wants a breaking change, it goes through
  you and it gets announced in the room, not in a commit message.

## The pitch — hours 9–10, and it is a real deliverable

The line is:

> **The model writes prose, the machine checks the facts — and here are the eight
> claims it caught the model inventing.**

Structure that survives ninety seconds:

1. Point it at a repo none of us has read. Run it live.
2. Open the artifact. Click one claim marker — the excerpt expands, `file:line`,
   real code.
3. Open the audit panel. **Show the deletions.** This is the moment; everything
   else is setup.
4. Scroll to a command block that **failed**, with its real output. "We show it
   failing, because it did."
5. Close: only one of five stages calls a model. Everything that checks is
   ordinary code, because a model cannot verify itself.

The drop count must be a real number from a real run. If it's zero, something is
wrong with your verifier and a judge will ask.

Rehearse it out loud, twice, on the machine and screen you will actually use.

## Done when

Both demo repos generate end to end, all three gates exit 0 on both outputs, the
pitch has been run twice, and the artifact opens from `file://` with the wifi
switched off. Test that last one literally — turn the wifi off.
