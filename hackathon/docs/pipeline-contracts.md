# Pipeline contracts — the seams between owners

**Status:** frozen 2026-07-30. `docs/verified-contract.md` (`trailhead/verified@1`) is
the generator↔render seam and was frozen first. This document freezes the three
seams *inside* the generator so the five owners can work without waiting on each
other.

| Contract | Produced by | Consumed by | Fixture |
|---|---|---|---|
| `trailhead/survey@1` | A — stage 1 | A (map), B (narrate), C (verify) | `fixtures/survey.sample.json` |
| `trailhead/map@1` | A — stage 2 | C (verify) | inline in survey fixture, see below |
| `trailhead/content@1` | B — stage 3 | C (verify) | `fixtures/content.sample.json` |
| `trailhead/commands@1` | C — runner | C (verify) | `fixtures/commands.sample.json` |
| `trailhead/verified@1` | C — stage 4 | D — render | `fixtures/verified.sample.json` |

All four fixtures describe the **same synthetic repo** (`payments-core`, commit
`a3f9c21`) so the chain is testable end to end before any real repo exists:

```
survey.sample.json ─┐
content.sample.json ─┼─▶ verify ─▶ should reproduce ─▶ verified.sample.json
commands.sample.json ┘
```

**Extending these is additive only.** Add a key, never rename or remove one, and
never change a type. If you genuinely need a breaking change, bump to `@2` and
tell the other four in the room, not in a commit message.

---

## `trailhead/survey@1`

Everything stage 1 can know without a model. Also the source of every checkpoint
answer key (non-negotiable #6).

```jsonc
{
  "contract": "trailhead/survey@1",
  "repo": { "name": "payments-core", "root": "/abs/path", "commit": "a3f9c21",
            "branch": "main", "surveyed_at": "2026-07-30T13:58:04Z" },

  "stats": { "files": 128, "py_files": 96, "loc": 12660, "modules": 6,
             "external_deps": ["fastapi", "pydantic", "numpy"] },

  // Every Python file. `module` is the dotted name; null if not importable.
  "files": [
    { "path": "src/api/app.py", "module": "src.api.app", "loc": 214,
      "commits": 41, "last_commit": "2026-07-02",
      "authors": ["r.vincent", "a.okafor"] }
  ],

  // Module-level rollup. Keys are dotted module names; `path` is the directory.
  "modules": {
    "src.api": { "path": "src/api", "files": 9, "loc": 1240, "commits": 74,
                 "top": [ { "path": "src/api/app.py", "commits": 41 } ] }
  },

  // Import edges, module → module, already resolved by resolve_import().
  // External imports are NOT edges. `n` is the number of import statements.
  "edges": [ { "a": "src.api", "b": "src.instruments", "n": 14 } ],

  // kind: console_script | module_main | main_guard | http_route | dockerfile_cmd
  "entry_points": [
    { "kind": "http_route", "name": "POST /v1/price",
      "file": "src/api/app.py", "line": 58, "target": "price_instrument" }
  ],

  // Candidates only — nothing has been run yet. C's runner executes these.
  // kind: setup | test | lint | run.  source cites where the command was found.
  "command_candidates": [
    { "cmd": "poetry install --with dev", "kind": "setup", "cwd": ".",
      "source": "pyproject.toml:1", "confidence": "high" }
  ],

  // Answer keys. Derived by static analysis, never by a model.
  // kind: single (answer = 0-based index) | order (answer = permutation of 1..n)
  "checkpoints": {
    "cp-a2": { "kind": "single",
               "prompt": "Which directory owns holiday-calendar logic?",
               "options": ["src/pricing/", "src/calendars/", "src/io/", "tests/"],
               "answer": 1,
               "provenance": "survey.json → edges → src.calendars imported by 3 modules",
               "explanation": "src/calendars/ defines Calendar; src/pricing/ consumes it." }
  }
}
```

Rules the gate will enforce:

- Every `edges[].a` and `.b` must be a key in `modules`.
- Every `files[].path` is repo-relative, forward slashes, on every OS.
- `checkpoints` values must satisfy `verified@1`'s checkpoint block exactly —
  `provenance` and `explanation` are both required, and `provenance` must name
  the survey field it came from.
- `command_candidates[].cwd` is repo-relative.

## `trailhead/map@1`

Stage 2 output. Identical in shape to `verified@1`'s `map` key, plus a contract
tag; VERIFY copies `nodes`/`edges` straight through.

```jsonc
{ "contract": "trailhead/map@1",
  "nodes": [ { "id": "api", "label": "src/api", "loc": 1240, "files": 9,
               "x": 88, "y": 212, "w": 132, "why": "…", "top": ["app.py (41 commits)"] } ],
  "edges": [ { "a": "api", "b": "instr", "n": 14 } ] }
```

`id` is a short slug, not the dotted module name — it is used in edges and in the
SVG. `x`/`y`/`w` are laid out **at generation time**; there is no layout engine in
the page (spec §4.4). `why` is one sentence and may be authored by B, in which
case it is a claim and must carry a cite like any other.

## `trailhead/content@1`

Stage 3 output — the only artifact a model writes. Same track/stop/block shape as
`verified@1` with **one difference that is the whole point:**

> **A claim carries a verbatim `quote`, never a line number.**

```jsonc
{
  "contract": "trailhead/content@1",
  "repo": { "name": "payments-core", "commit": "a3f9c21" },
  "model": { "provider": "…", "model": "…", "calls": 37, "duration_s": 122 },

  "tracks": [
    { "title": "ORIENT",
      "stops": [
        { "id": "five", "title": "Five sentences", "minutes": 4,
          "blocks": [
            { "type": "prose",
              "claims": [
                { "id": "c-001",
                  "text": "payments-core prices instruments behind one HTTP endpoint.",
                  "status": "verified",
                  "cite": { "file": "src/api/app.py",
                            "quote": "@router.post(\"/v1/price\", response_model=PriceResponse)\nasync def price_instrument(",
                            "focus": "async def price_instrument(" } },

                { "id": "c-002",
                  "text": "The team seems to prefer explicit errors over silent defaults.",
                  "status": "inferred" }
              ] } ] } ] } ]
}
```

### Claim rules — B implements, C enforces

1. `status` is `verified` or `inferred`. `dropped` never appears; only stage 4
   drops things.
2. A `verified` claim **must** carry `cite`; an `inferred` claim **must not**.
   Same rule as `verified@1`, one stage earlier.
3. `cite.quote` is a **contiguous verbatim** snippet of `cite.file`, lines joined
   with `\n`. Leading indentation is preserved. Stage 4 finds it by exact string
   search and derives `start`/`end` itself.
4. `cite.focus` is an optional **array** of verbatim substrings of `quote`. Stage 4
   resolves each to the line it falls on and emits `anchor.focus[]`. An array,
   not a string, because focus lines are often non-contiguous — line 63 and line
   65 of the same excerpt, with 64 unremarkable.
5. **Never emit a line number.** If a prompt response contains `"start"` or
   `"end"`, the response is malformed — reject it in the parser, do not repair it.
6. Claim ids are unique across the payload and stable across a run.

### Blocks B may emit

`prose`, `excerpt` (with `cite` instead of `anchor`), `trace` (steps carry `cite`),
`table`, `callout`, `graph`, `ledger`.

### Blocks B may **not** author

| Block | Why | What B emits instead |
|---|---|---|
| `checkpoint` | Answer keys come from survey, not a model (non-neg. #6) | `{ "type": "checkpoint", "id": "cp-a2" }` — a reference. VERIFY substitutes the full object from `survey.checkpoints`. Unknown id → block dropped and logged. |
| `command` output | Output is real or the run is a fraud (non-neg. #4) | `{ "type": "command", "cmd": "make test", "cwd": ".", "hypothesis": "…" }`. VERIFY merges the real capture from `commands.json` by `(cmd, cwd)`. No match → block dropped and logged. `hypothesis` is optional and always renders tagged `inferred`. |

## `trailhead/commands@1`

Produced by the command runner. Never hand-written, never model-written.

```jsonc
{
  "contract": "trailhead/commands@1",
  "env": "captured 2026-07-30, ubuntu-22.04, python 3.11.8",
  "runs": [
    { "cmd": "poetry run pytest -q", "cwd": ".", "exit": 0,
      "dur_ms": 41200, "dur": "41.2 s",
      "out": "…combined stdout+stderr, real…",
      "started": "2026-07-30T14:01:02Z", "timed_out": false }
  ]
}
```

- `out` is combined stdout+stderr, truncated to 400 lines with an explicit
  `… N lines elided` marker if longer. Never empty — a command that printed
  nothing records `(no output)`.
- `dur` is the display string; `dur_ms` is the number. Render uses `dur`.
- A timeout records `timed_out: true` and whatever output was captured, with the
  real exit code the OS gave.
- `env` is one string, reused for every run in the file, and lands in each
  command block's `env` field. A run **may** override it with its own `env` when
  the relevant toolchain differs — `fixtures/verified.sample.json` already does
  this, naming the docker version on the docker command and the ruff version on
  the lint command. Per-run wins when present.

---

## What VERIFY (stage 4) consumes

```
content.json  +  survey.json  +  map.json  +  commands.json  +  the repo on disk
                                   │
                                   ▼
              verified.json  +  verification-report.json
```

Merge order, and where each `verified@1` field comes from:

| `verified@1` field | Source |
|---|---|
| `repo`, `report` | computed by VERIFY |
| `map` | `map.json` verbatim |
| `tracks` | `content.json`, with claims resolved, checkpoints substituted, commands merged |
| `files` | read from disk for every surviving anchor range |
| `dropped` | VERIFY's ledger |

Every drop needs a real `reason`. The four seen so far, all worth keeping verbatim:
`snippet not found verbatim in file` · `file does not exist at this commit` ·
`lines N-M out of range (file ends at K)` · `excerpt hash mismatch — file changed
after narration`. Add to that list only when a new failure genuinely occurs.
