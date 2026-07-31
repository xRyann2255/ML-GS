---
name: trailhead
description: Run the Trailhead pipeline end to end on a repo — survey, map, run commands, answer the narration prompt packs as the agent, verify, render, gate — and report the drop count. Use when asked to generate or regenerate a walkthrough, build a trailhead.html, narrate prompt packs, or demo Trailhead on an unfamiliar repo.
---

# Trailhead — generate one walkthrough

Point the pipeline at a repo and produce one self-contained HTML file whose every factual sentence is anchored to a `file:line` that was **re-read and hash-matched after the sentence was written**.

Five stages, and **only stage 3 NARRATE touches a model**. On this route the model is *you*: the CLI writes one prompt pack per unit, you answer each pack into the narration store, and the stub provider replays it. Everything that checks anything — survey, map, resolve, verify, render, the gates — is ordinary deterministic Python and Node that you do not get to influence.

The pipeline runs in **two CLI passes with the agent step in between**:

```
pass A: survey → map → run-commands → narrate --emit-prompts   (stops here)
        ↓
    YOU answer .trailhead/prompts/*.json into their own "out" paths
        ↓
pass B: --from-stage narrate → verify → render → --gate
```

## Execution

`$HACK` = `C:/Users/RyanPC/Documents/Projects/ML-GS/hackathon`. Every command runs from there, with `PYTHONPATH=src`, Python as `python`. `$REPO` is the repo to walk (a path, absolute or relative to `$HACK`); `restored` is the demo repo.

The work directory defaults to `<out-parent>/.trailhead`, so `-o out/restored.html` puts artifacts in `out/.trailhead/`. **Pass A and pass B must use the same `-o`/`--work` and the same `--run-commands` policy** — see *Why the packs go stale*.

### Step 1 — Pass A: survey, map, commands, and the prompt packs

```bash
cd $HACK && PYTHONPATH=src python -m trailhead build $REPO -o out/$REPO.html \
    --run-commands safe --emit-prompts -v
```

This surveys the repo, builds the map, **really executes** the allowlisted setup and test commands (real exit codes, real stdout, real timings — a failing command is kept failing), then writes one pack per narrate unit to `<work>/prompts/<key>.json` and stops. It prints one line per pack:

```
  five  ...\out\.trailhead\prompts\378587cf….json
  green ...\out\.trailhead\prompts\66295801….json
  conv  ...\out\.trailhead\prompts\9673867….json
  trace ...\out\.trailhead\prompts\e92abde….json
```

Read the `-v` lines it prints above that. `trace no fixtures/trace.<repo-dir>.json` means the trace stop will degrade to a labelled callout with zero anchored hops — that is correct behaviour for any repo without a hand-checked hop fixture, not something to fix by inventing hops.

Use `--run-commands none` only when the repo's commands are unsafe or slow; it costs the `green` unit and the real-output stop.

### Step 2 — THE AGENT STEP: answer every pack

For each `<work>/prompts/*.json`, in one sitting:

1. **Read the pack.** It is self-describing: `unit`, `kind`, `title`, `max_claims`, `system`, `user`, `windows`, `schema`, and `out` — the absolute path your answer goes to. The pack carries its own `out` so you never compute a sha256 by hand.
2. **Read the source it names.** The `user` field already contains the numbered source behind a `%5d| ` gutter, and `windows` lists `{file, start, end}` — the **quotable** spans. Open the files under the repo root as well if you want more context, but quote only from inside a listed window.
3. **Write the claims JSON to the pack's `out` path**, exactly matching the pack's `schema`:

```json
{ "claims": [
  { "text": "One plain sentence, ≤280 chars, no backticks, no newline, no '<', no '](' .",
    "status": "verified",
    "cite": { "file": "src/widget/__main__.py",
              "quote": "def main(argv=None):\n    args = build_parser().parse_args(argv)\n    return 0",
              "focus": ["    return 0"] } },
  { "text": "A sentence you cannot support with a quote.", "status": "inferred" }
] }
```

Rules, all enforced by code after you answer:

- **Never return a line number.** The gutter is orientation for you only; there is no schema field for a line number and a gutter prefix inside a quote is rejected. The resolver finds the range from the quote.
- `cite.quote` is **3–24 contiguous lines from one file**, joined with `\n`, copied byte for byte including leading indentation. `cite.focus` entries are exact substrings of your own quote.
- `cite` keys are `file`, `quote`, `focus` and nothing else. Any other key rejects the **whole response**, not just that claim.
- At most `max_claims` claims. For the `trace` unit, exactly one claim per hop.
- No `cite` at all when you set `"status": "inferred"`. An honest inferred sentence survives and is visibly marked; an invented quote does not survive.
- One file per pack. Do not merge two packs' answers into one file, and do not rename the file — the filename *is* the cache key the stub replays from.

### The @3 structured packs

Since `trailhead/verified@3`, pass A also emits STRUCTURED packs beside the
claim packs: `node:<gid>` (drawer narration), `dive:<gid>` (subsystem deep-dive
claims, answered exactly like `five`), `gloss` (glossary terms), `tour` (map
tour steps keyed to the node ids the pack fixes), and `cols` (column labels).
Each pack's own `schema` field is the authority; answer that shape, not
`{"claims": [...]}`, except for `dive:` which IS a claims pack.

Extra rules for every pack, old and new:

- BANNED in every text/def/role/purpose string: em dash U+2014, en dash
  U+2013, the character `<`, and the sequence `](`. Write "h up to 5", never
  "h<=5". Verify sanitises defensively, but a `<` rejects the whole response
  at parse time.
- Backticks and bare `[[Term]]` glossary markers are allowed where the pack's
  system says so; never the `[[id|label]]` form.
- `node:` cites resolve onto the map node as its drawer anchor; a failed cite
  keeps the mechanical fallback and ledgers under the node id. `tour` steps
  whose id is off the board are dropped (`t-<id>`), and the whole tour drops
  under 3 surviving steps.
- Unanswered structured packs degrade silently to the exact @2 page. Answer
  what you can support; skip what you cannot.

### Quotes are copied, never retyped

Copy the quote out of the window you were shown. Do not tidy the indentation, do not collapse a blank line, do not reflow a long line, do not "fix" a typo in a comment, do not substitute straight quotes for smart ones. The resolver searches for the snippet **verbatim** in the file on disk; the only normalisations it applies are CRLF folding and a trailing rstrip, and neither can rescue a retyped line.

A quote that does not appear verbatim is deleted with reason `snippet not found verbatim in file` and counted on screen. **That is the system working.** So is `snippet ambiguous`, `snippet resolved outside the excerpt shown to the model`, and `quote too thin to be unique`. None of them is a reason to go back and edit the quote until it passes — if you cannot find a real snippet that carries the sentence, the sentence is `inferred` or it does not exist.

### Step 3 — Pass B: verify, render, gate

```bash
cd $HACK && PYTHONPATH=src python -m trailhead build $REPO -o out/$REPO.html \
    --run-commands safe --from-stage narrate --offline --gate -v
```

`--from-stage narrate` reads `survey.json`, `map.json` and `commands.json` back off disk and re-runs narrate against the store you just wrote. `--offline` makes a store miss **fatal** instead of silently rendering that stop from templates, which is what you want the moment every pack has been answered — a mis-pathed answer file is then loud rather than invisible. Drop `--offline` if you deliberately left packs unanswered.

`--gate` runs `check-bundle.js` and `verify-contract.js` against the bundle just written and exits 3 if either fails.

### Step 4 — The three gates

`--gate` covers the two gates that read the generated artifact. Run all three from the repo as well, in their no-argument form, to prove the repo invariants are still green (`check-bundle.js` and `verify-contract.js` with no argv check `demo/trailhead-demo.html`; `check-fixtures.js` takes no argv at all and checks `fixtures/`):

```bash
cd $HACK && for g in check-bundle.js check-fixtures.js verify-contract.js; do
  out=$(node "tools/$g" 2>&1); rc=$?
  echo "$g: exit $rc  |  $(printf '%s' "$out" | tail -1)"
done
```

All three must exit 0. Leaving any of them non-zero is a failed run, whatever the HTML looks like.

### Step 5 — Report the drop count on screen

The build prints it itself, on every run, with or without `-v`:

```
wrote ...\out\restored.html  77.9 KB
  claims 6  verified 2  inferred 3  DROPPED 1
  commands 0 (0 failing)  stops 10  0s
  trace   no fixtures/trace.nested_root.json - the trace stop degrades to a labelled callout (0 anchored hops)
  model   4 claim(s) from 1/2 unit(s) via stub
```

Quote those lines back verbatim. Report, in this order: the bundle path and size, the four claim counts with **DROPPED named explicitly**, how many commands ran and how many failed, the provenance lines, and the three gate exit codes. The per-drop rows — id, text, file, reason — are in `<work>/verification-report.json` under `dropped`; list them if there is any drop at all. A high drop count is a result to present, not a number to bury.

## THE PROHIBITION

**The agent writes narration files and nothing else.**

- Write only `<work>/narration/<key>.json`, only at the `out` path a pack states, only between pass A and pass B.
- **Never edit `verified.json`.** Never edit `verification-report.json`, `content.json`, `survey.json`, `map.json` or `commands.json`.
- **Never touch the ledger.** Not to remove a row, not to soften a reason, not to reword the detail.
- **Never revise a claim after VERIFY has run.** Not the text, not the quote, not the status. Do not re-answer a pack to make a drop disappear.
- Never hand-edit the rendered HTML, and never edit `src/trailhead/` to make a claim pass.

If verify drops eight claims, **that is the deliverable**, not a bug to fix. The whole pitch is "the model writes prose, the machine checks the facts — here are the eight claims it caught the model inventing." A run where the thing that wrote the prose was allowed to go back and repair the checker's verdict is worth nothing, and no one in the room can tell the difference afterwards. That is exactly why the separation is structural: you produce claims, ordinary code decides which ones survive, and the count is printed by the same command the audience watches you run.

The only legitimate response to a drop is to say what was dropped and why.

## Flags that actually exist

Read `src/trailhead/cli.py` before using anything not on this list — fourteen plausible-sounding flags were deliberately cut and argparse will exit 2.

| Flag | Meaning |
|---|---|
| `-o, --out PATH` | output bundle (default `trailhead.html`) |
| `--work DIR` | artifacts (default `<out-parent>/.trailhead`) |
| `--payload PATH` | `verified.json` to render; only with `--from-stage render` |
| `--provider {stub,claude}` | default `stub` — the agent route. `claude` is opt-in and live |
| `--offline` | a narration-store miss is an error, not an empty unit |
| `--run-commands {safe,none}` | default `safe` |
| `--from-stage {survey,map,commands,narrate,verify,render}` | skip earlier stages, read their artifacts |
| `--emit-prompts` | write one pack per unit and stop |
| `--max-units N` / `--max-nodes N` | defaults 12 / 14 |
| `--gate` | run the two artifact gates on the output |
| `-v, --verbose` | per-stage progress to stderr |

`$REPO` is required except with `--from-stage render`. Exit codes: `0` ok · `1` generation failed · `2` usage · `3` gates failed.

## Why the packs go stale

The narration key is `sha256(system + "\0" + user)`, and the prompt embeds its own evidence — the numbered source windows, the survey facts, the command results. So **anything that changes the prompt changes the filename**: editing the repo, re-running survey, switching `--run-commands safe` to `none`, changing `--max-units`, or pointing at a different repo. When that happens the old answers stop being found and every unit falls back to templates.

Symptom: `narrate <unit>: 0 claims, 0 dropped (provider, key …)` plus `model 0 claim(s) from 0/N unit(s)` and the tail `- every sentence on the page is a deterministic template`. Fix: re-run pass A, re-answer the new packs. Never rename an answer file to match a new key — the answer was written against different evidence.

## Critical rules

- ALWAYS run from `$HACK` with `PYTHONPATH=src`; Python is `python` (3.12) on this machine.
- ALWAYS use the same `-o`/`--work` and the same `--run-commands` value in pass A and pass B.
- ALWAYS answer a pack into the `out` path the pack itself carries. Never compute the key yourself.
- ALWAYS re-run pass A after touching the repo — a stale pack silently costs you the whole unit.
- ALWAYS quote byte-exactly from a listed window; never retype, tidy, re-indent or elide.
- ALWAYS report DROPPED explicitly, with the reasons from `verification-report.json`.
- NEVER put a line number anywhere in an answer.
- NEVER edit `verified.json`, the ledger, the report, the rendered HTML, or any claim after verify has run.
- NEVER synthesise command output, exit codes or timings; a failing command is shown failing.
- NEVER call a model from any stage but narrate — survey, map, resolve, verify, checkpoints and render are deterministic code and stay that way.
- NEVER report a stage as working on the strength of reading the code. Run it, and quote what it printed.
