# Owner C — Verify and the command runner

## Paste this into Claude Code

```
I own stage 4 (VERIFY) and the command runner in Trailhead, a hackathon project
in this repo. VERIFY is the reason the project has a pitch: it re-reads every
anchor the model claimed, deletes what does not hold, and counts the deletions
on screen.

Read in this order:
  CLAUDE.md
  hackathon/briefs/C-verify.md          <- my brief, follow it
  hackathon/docs/pipeline-contracts.md  <- what I consume
  hackathon/docs/verified-contract.md   <- what I emit, frozen, sha256 rules
  hackathon/fixtures/content.sample.json + verified.sample.json

This is pure deterministic code with hard contracts, so it is strictly
test-driven: write the failing test first. I own src/trailhead/verify.py,
resolve.py, runner.py and their tests. I touch nothing else.

Start with the quote-to-line resolver — it is the highest-risk function in the
project. Propose its signature and its ambiguity policy before writing it.
```

## Mission

The model wrote prose. You are the machine that checks it. Everything you write
is ordinary code — a model cannot verify itself, and that is the entire pitch.

You also own the number that goes on stage: **the drop count**. If it is 40%,
the demo is embarrassing. If it is ~3%, it is credible. Most of that is B's
prompts, but the resolver is what turns a good quote into a surviving claim.

## You own

```
src/trailhead/resolve.py    quote -> line range. The critical function.
src/trailhead/verify.py     stage 4 merge + drop ledger
src/trailhead/runner.py     real command execution and capture
tests/test_resolve.py       where most of your tests live
tests/test_verify.py
tests/test_runner.py
```

**Never touch:** `narrate.py`, `survey.py`, `demo/`, `fixtures/*` (shared — ask).

## Input → output

```
content.json + survey.json + map.json + commands.json + the repo on disk
        │
        ▼
verified.json  +  verification-report.json
```

Field-by-field merge table is at the bottom of `docs/pipeline-contracts.md`.
Output contract is `docs/verified-contract.md` — **frozen**, and
`tools/verify-contract.js` already enforces it.

## Build order

### 1. `resolve.py` — do this first, test it hardest

```python
def resolve(quote: str, source: str) -> tuple[int, int]   # 1-based inclusive
```

Exact string search. The cases that decide your drop rate:

| Case | Policy |
|---|---|
| Found once | Return the range. The happy path. |
| Not found | Drop: `snippet not found verbatim in file` |
| **Found more than once** | **Drop: `quote matches N times in file — ambiguous`** |
| Found only after normalising trailing whitespace | Accept, and log it |
| CRLF vs LF | Normalise the *file* to `\n` before searching. Never the quote. |

The ambiguous case is the one that will bite you on a real repo — short quotes
like `return out` appear a dozen times. Dropping is correct: a claim anchored to
an arbitrary one of twelve matches is a false anchor, and a false anchor that
renders as verified is worse than a deletion. **Note this reason is not yet in
the frozen list** — add it to `docs/verified-contract.md`'s reason vocabulary
when you hit it, and tell E.

Then `focus`: each focus string is a substring of the quote; map each to its line
number within `[start, end]`. A focus string that isn't found doesn't drop the
claim — drop the focus and keep the anchor.

### 2. `sha256`

> Hex SHA-256 of source lines `start..end` **joined with `\n`**, **no trailing
> newline**, **no line numbers**, UTF-8.

Both sides must compute this identically or every anchor drops.
`tools/verify-contract.js` already implements the other side — read it and match
it exactly. Recompute after resolving, and again when you write `files`.

### 3. `runner.py`

Executes A's `command_candidates`, emits `trailhead/commands@1`.

- Combined stdout+stderr, real exit code, wall-clock duration, ISO start.
- **Timeout is mandatory** — 300 s default. A hanging setup command on stage is a
  dead demo. Record `timed_out: true` plus whatever was captured.
- Truncate `out` to 400 lines with an explicit `… N lines elided` marker.
- Empty output records `(no output)`, never an empty string.
- `env` string names OS, Python, and the relevant tool version.
- **Non-negotiable #4 is yours: never synthesise output, an exit code, or a
  timing.** A failing command is shown failing, in full, with a red banner. That
  failure is one of the most convincing things in the whole artifact.

### 4. `verify.py` — the merge

Walk `content.json`. For each block:

- **prose / excerpt / trace** — resolve every cite. Survivors get an `anchor`
  with `sha256`; failures go to the `dropped` ledger with a real reason and are
  removed from `tracks` entirely. An `inferred` claim passes through untouched
  and must still carry no anchor.
- **checkpoint** — substitute the full object from `survey.checkpoints[id]`.
  Unknown id → drop the block, log it. `fixtures/content.sample.json` has one
  deliberately (`cp-a9-does-not-exist`).
- **command** — match `commands.json` on `(cmd, cwd)`, merge in the real
  `exit`/`out`/`dur`/`env`. No match → drop the block, log it. The fixture has
  one deliberately (`make coverage`). Any `exit != 0` **must** get a `broken`
  banner string; `hypothesis` passes through and always renders tagged
  `inferred`.
- **graph / ledger** — field-free, pass through. `map` comes from `map.json`.

Then `files`: for every surviving anchor, read lines `start..end` from disk into
the sparse `files` map. This is what makes the bundle work offline.

Then `report`. Two fields are cross-checked by the gate and must agree exactly:
`report.dropped === dropped.length`, and `report.failed ===` the number of
command blocks with `exit != 0`.

## Done when

```bash
cd hackathon
PYTHONPATH=src py -3.11 -m unittest discover -s tests -v
PYTHONPATH=src py -3.11 -m trailhead.verify \
  --content fixtures/content.sample.json \
  --survey  fixtures/survey.sample.json \
  --commands fixtures/commands.sample.json \
  --repo <a checkout of the synthetic repo> \
  > /tmp/verified.json
node tools/verify-contract.js /tmp/verified.json    # must exit 0
```

`fixtures/content.sample.json` is built so that a correct verifier drops
**exactly the eight claims** in `verified.sample.json`'s ledger, plus one
checkpoint block and one command block. That is your acceptance test.

**One honest caveat:** it is a subset, not a byte-for-byte preimage — it doesn't
reproduce every stop. And one drop reason will differ: the frozen ledger records
`c-067` as `lines 44-51 out of range (file ends at 38)`, which is an artifact of
an older line-number design. In the quote-based pipeline that failure cannot
occur; `c-067` will drop as `snippet not found verbatim in file`. Reproducing the
**set of dropped ids** is the target, not that string.

## Traps

- **Hash mismatch from line endings.** The single most likely way to drop 100% of
  anchors. Normalise the file to `\n`, hash the joined lines with no trailing
  newline, and test it against `tools/verify-contract.js` on day one.
- **Trailing newline at EOF.** `"a\nb\n".split("\n")` gives you a phantom empty
  last line. Off-by-one here shifts every line number in the artifact.
- **Unicode.** Hash UTF-8 bytes, not the platform default. On Windows, open files
  with an explicit `encoding="utf-8"`.
- **Silent drops.** Every drop needs a real `reason` that a human reading the
  audit panel would accept. "verification failed" is not a reason.
- **Non-negotiable #3.** The drop count goes on screen. Never quietly filter.
