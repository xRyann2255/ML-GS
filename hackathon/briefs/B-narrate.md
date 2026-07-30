# Owner B — Narrate, the only stage that touches a model

## Paste this into Claude Code

```
I own stage 3 (NARRATE) of Trailhead, a hackathon project in this repo. It is the
only stage that calls a model.

Read in this order:
  CLAUDE.md
  hackathon/briefs/B-narrate.md         <- my brief, follow it
  hackathon/docs/pipeline-contracts.md  <- trailhead/content@1, the claim rules
  hackathon/fixtures/content.sample.json <- exactly what I must emit

The single rule that makes this project work: I never ask the model for line
numbers. I feed it files with line numbers pre-pended and require a verbatim
quote back; stage 4 resolves the quote to a range in code. A response containing
"start" or "end" is malformed and gets rejected, not repaired.

I own src/trailhead/narrate.py, prompts.py, provider.py and their tests.

Build the provider interface with a StubProvider first so everything is testable
before real tool access exists. Start by proposing the prompt-response schema and
the parser's rejection rules.
```

## Mission

Turn `survey.json` into prose that carries its own evidence. One small call per
unit, each returning claims with verbatim quotes.

**You are the only person who can discover a tool-access problem, and the whole
demo's shape depends on the answer.** So your first hour is one thing: get a
single successful call through the internal GS tool. Not prompts, not
architecture — one round trip. If it is still blocked at hour 2, say so in the
room immediately; that triggers the pivot rule.

## You own

```
src/trailhead/narrate.py    stage 3 orchestration
src/trailhead/prompts.py    prompt construction
src/trailhead/provider.py   the model interface + StubProvider + the real one
tests/test_narrate.py       parser and schema tests, against StubProvider
```

**Never touch:** `verify.py`, `survey.py`, `fixtures/*` (shared — ask first).

## Output

`trailhead/content@1`, defined in `docs/pipeline-contracts.md`. Reference:
`fixtures/content.sample.json` — read it before writing a prompt. It is a
hand-written example of exactly what a good run looks like, including the
failures a real run produces.

## The one technique that matters

> **Never ask for line numbers. Ask for a quote.**

Feed the file with line numbers pre-pended, require the verbatim snippet, and let
stage 4 find it. Models count badly and copy well. This is the difference between
a 40% drop rate — embarrassing on stage — and ~3%. It costs nothing: a snippet
not found verbatim is dropped either way, so the failure mode is identical and
the success rate is an order of magnitude better.

Two consequences for your parser:

- A response containing `start`, `end`, or a bare line number in the cite is
  **malformed**. Reject the response and retry the call. Do not "helpfully"
  convert it — that is the model verifying itself through your code.
- `cite.focus` is an **array of substrings of the quote**, not line numbers.
  Non-contiguous focus is normal: line 63 and line 65 matter, 64 doesn't.

## Build order

1. **`provider.py` first.** One interface, two implementations:
   `StubProvider` (returns canned JSON from a file — makes everything below
   testable with zero tool access) and the real one. Nothing above this line
   knows which is in use.
2. **Response schema and parser.** Strict. Reject on: missing `text`, `verified`
   with no `cite`, `inferred` with a `cite`, a `focus` string that isn't a
   substring of `quote`, or any line number. Every rejection is retried once,
   then the claim is abandoned and logged. Test all of these against
   `StubProvider` — they are pure functions and they are where your correctness
   lives.
3. **Prompt construction.** Line-numbered file content, plus the survey facts for
   that unit. One call per unit, small. Ask for few claims and good quotes rather
   than many claims.
4. **Unit loop.** Per stop / per module. Budget-aware: your tool's rate limits
   set how many modules a live on-stage run can narrate — **find that number and
   tell E, it constrains the demo repo choice.**
5. **The blocks you must not author.** Two, both non-negotiables:
   - `checkpoint` — emit `{"type":"checkpoint","id":"cp-a1"}`, a reference only.
     The answer key is A's, from static analysis. Non-negotiable #6.
   - `command` output — emit `{"type":"command","cmd":"…","cwd":"…"}` plus an
     optional `hypothesis`. Never `exit`, `out`, or `dur`. C's runner produces
     those from a real execution. Non-negotiable #4.
6. **Inferred is a legitimate answer.** A claim you cannot anchor is `inferred`
   with no cite, and it renders visibly marked. That is honest and it is
   quarantined in stop 13. Prose that is neither anchorable nor worth marking
   gets cut. Never invent a quote to make a sentence survive.

## Done when

```bash
cd hackathon
PYTHONPATH=src py -3.11 -m unittest discover -s tests -v
PYTHONPATH=src py -3.11 -m trailhead.narrate fixtures/survey.sample.json --provider stub \
  > /tmp/content.json
node tools/check-fixtures.js   # still exit 0
```

and a real run against a real `survey.json` produces content whose drop rate,
once C runs verify over it, is **under 10%**. Above that, your prompts are the
problem, not the verifier.

## Traps

- **Waiting on tool access before building anything.** `StubProvider` means the
  parser, the schema, the prompts and the unit loop are all testable now.
- **Repairing a bad response.** Reject and retry. A parser that patches model
  output is a model verifying itself with extra steps.
- **Long quotes.** A 40-line quote is more likely to contain a typo and drop.
  Ask for the smallest snippet that supports the sentence.
- **Trailing whitespace and tabs.** The quote must match the file byte for byte.
  Strip nothing, normalise nothing, and make sure your prompt doesn't reformat
  the code you feed it.
- **Claim ids must be unique and stable across a run** — they key the audit
  ledger and the drop count.
