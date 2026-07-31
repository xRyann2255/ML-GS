# `verified.json` — frozen contract

**Version:** `trailhead/verified@3` (the `contract` key at the top of every payload)
**Status:** frozen 2026-07-30, extended to `@2` the same day and to `@3` on
2026-07-31 (template parity, see `docs/template-parity-spec.md`). Stages 3, 4 and 5
all code against this. `verify-contract.js` asserts the version string itself, so a
silent bump fails the gate. `@1` and `@2` payloads remain valid: every `@3` addition
is optional, and a payload that carries none of them renders exactly as `@2` did.

### What `@2` added

Two optional fields, both additive. A valid `@1` payload is a valid `@2` payload.

| Field | On | Meaning |
|---|---|---|
| `predict` | `command` block | Question asked *before* the result is revealed |
| `predict` | `trace` step | Question asked before the `next` pointer is revealed |

**Neither carries an answer, deliberately.** The key is derived by RENDER from data
that is already verified: the command's captured `exit`, and the next hop's resolved
`anchor.file`. A prediction therefore cannot disagree with the run or the call graph
shown beside it, and no new answer-key source was introduced (non-negotiable #6).
The gate rejects a `command.predict` that ships an `answer`, a `predict` on the last
trace hop (nothing to key against), and one whose next hop is the same file (the
question would be trivial).

### What `@3` added

All optional, all additive; the renderer conditions every new feature on its field.
The quality target is the hand-built template (`template/payload.mjs` is a full
worked example of every shape below).

| Field | Where | Meaning |
|---|---|---|
| `glossary` | top level | Term definitions with optional hashed anchors; popovers in the page |
| `` `code` `` and `[[id\|label]]` | authored text | Inline markup: code spans and glossary term buttons |
| `w`, `h` | `map` | Explicit SVG viewBox, computed by MAP (renderer falls back to 900x400 for `@2`) |
| `columns` | `map` | Pipeline-stage column headers: `{ label, x, line }`, `x` inside the viewBox |
| `note` | `map` | `{ title, text }` callout under the board naming what is deliberately off it |
| `tour` | `map` | Guided tour: `{ id, text }` steps, each `id` an existing node |
| `h`, `path` | `map.nodes[]` | Explicit node height (required on `@3` nodes) and directory path |
| `role`, `reads`, `feeds` | `map.nodes[]` | Narrated drawer paragraphs and data-flow lines; absent falls back to `why`/`top` |
| `key_files`, `concepts` | `map.nodes[]` | `[{ file, purpose }]` and concept chips for the drawer |
| `anchor`, `anchor_caption` | `map.nodes[]` | One hashed excerpt per node, shown in the drawer |
| `stats` | new block type | Cover / dive tiles: `{ items: [{ v, l, s?, of?, color? }] }` |
| `anchors` | `report` | Total anchors shipped (claims + excerpts + nodes + glossary); claim math unchanged |
| dash policy | authored text | No U+2014 / U+2013 in any authored string (details below) |

#### `glossary`

```jsonc
"glossary": [ { "id": "qlike", "term": "QLIKE", "def": "1-2 sentences.",
                "anchor": { "file": "…", "start": 1, "end": 9,
                            "focus": [3], "sha256": "…" } } ]
```

- `id` is a slug `[a-z0-9-]+`, unique across the glossary. `term` and `def` are
  required and non-empty.
- `anchor` is optional and, when present, is a standard anchor: bundled into
  `files`, whole, and sha256-matched like any claim anchor. No anchor means the
  popover shows the definition only.
- Stage 4 verifies glossary cites like claims; a failed anchor is dropped (the
  entry keeps its definition) and recorded in `dropped` with id `g-<slug>`.

#### Inline markup in authored text

In `claim.text`, `stop.lede`, `callout.text`, `map.note.text`, `map.tour[].text`,
`map.nodes[].role[]`, `reads`, `feeds`, and `key_files[].purpose`:

- `` `code` `` renders as `<code>`.
- `[[id|label]]` renders as a glossary term button (dotted underline, popover,
  jump to evidence). An explicit id that is not in `glossary` fails the gate;
  stage 4 rewrites unresolvable markers to the plain label before assembly, so a
  shipped payload never carries one.
- `[[Label]]` (bare form) slug-matches the label; no match degrades to plain
  text and is not gated. Raw HTML stays banned in claim text.
- Glossary `def`, checkpoint `provenance` and `explanation` are escaped by the
  renderer, not enriched: markers there are inert text and are not gated.

#### `stats` — the eleventh block type

```jsonc
{ "type": "stats", "items": [ { "v": "96,897", "l": "LINES OF CODE",
                                "s": "455 Python files", "of": "22",
                                "color": "inf" } ] }
```

`v` and `l` are required non-empty strings; `s` (sub line) and `of` (denominator,
rendered as `v / of`) are optional strings; `color` is optional and one of
`ok | inf | bad`, mapping to the renderer's semantic CSS variables. Every value is
computed by COMPOSE from `survey.json`, never authored by the model.

#### Dash policy (authored text only)

No U+2014 (em dash) or U+2013 (en dash) in any authored string: claim text,
ledes, callout text, tour text, map note, node `role`/`reads`/`feeds`,
`key_files[].purpose`, glossary `def`, checkpoint `provenance` and `explanation`.
COMPOSE transliterates model output at the source; the gate re-scans on `@3`
payloads only (the frozen `@2` fixtures predate the policy). Two surfaces are
exempt by design: the `files` map (the repo's own bytes; hash integrity wins) and
command `out` (real capture, non-negotiable #4).

---

This is the only interface between the generator and the artifact. RENDER consumes
this and nothing else; VERIFY produces it; NARRATE produces the pre-verification
form of it. `docs/walkthrough-spec.md` describes what the page *looks like* — this
describes what it *eats*.

Reference payloads: `fixtures/verified.sample.json` (synthetic repo, 13 anchors,
kept at `@2` for the demo bundle), `fixtures/verified.ml-gs.json` (this repo, 17
anchors, `@2`), and `fixtures/verified.parity.json` (minimal `@3`, exercises every
field `@3` added, 5 anchors hashed over its own `files` map).
Gate: `node tools/verify-contract.js fixtures/verified.parity.json`.

**How the demo bundle stores these.** Between the `TRAILHEAD-DATA-START` and
`TRAILHEAD-DATA-END` markers it declares `BUNDLES`, a map of repo name to payload,
plus a demo-only `SYNTHETIC` lookup that decides whether the SAMPLE chip shows.
Each value is a pure, unmodified `verified.json`; the wrapper exists so two
walkthroughs can share one renderer, and the gate checks every payload in it. A
real generated artifact holds one payload. The markers are what both tools key
off — the previous end marker was a prose comment containing an em dash, which
made the gate hostage to its wording.

---

## Why the names differ from spec §5

Spec §5 was written before the renderer. Where the two disagreed the renderer won,
because it works and rewriting it buys nothing. Deliberate deltas, all now
reflected back into §5:

| Spec §5 originally | Frozen as | Why |
|---|---|---|
| `block.focus_lines[]` | `anchor.focus[]` | Focus lines are a property of the anchor, not the block. A trace step and a claim can share one anchor. |
| `exit_code`, `stdout`, `duration_ms`, `env_note` | `exit`, `out`, `dur`, `env` | Renderer's names; the payload is inlined into the bundle, so shorter keys are free bytes. |
| `anchor.excerpt_sha256` | `anchor.sha256` | Renamed and, more importantly, **made mandatory** — see below. |
| `graph.ref` | `graph` (no fields) | One map per bundle. A ref with one possible value is ceremony. |
| — | `files` | Added. The bundled source lines. Self-containment depends on it. |
| — | `dropped` | Added. The ledger. Non-negotiable #3. |
| 8 block types | 9 — added `ledger` | Stop 14 renders the audit ledger; it needs a block type. |

**`sha256` was absent from the demo entirely.** Non-negotiable #2 — "no factual
sentence without a resolvable anchor" — is unenforceable without it, so it is now
required on every anchor and `verify-contract.js` fails a payload that omits one.

---

## Top level

```jsonc
{
  "contract": "trailhead/verified@1",
  "repo":   { "name": "payments-core", "commit": "a3f9c21",
              "generated_at": "2026-07-30T14:02:11Z" },   // ISO 8601 UTC
  "report": { "claims": 142, "verified": 134, "dropped": 8, "inferred": 19,
              "commands": 23, "failed": 2,
              "tool_version": "0.3.1", "duration_s": 238 },
  "map":    { "nodes": [], "edges": [] },
  "files":  { },
  "tracks": [ ],
  "dropped":[ ]
}
```

`report` is what the top bar shows. Two of its fields are cross-checked against
the rest of the payload and must agree exactly:

- `report.dropped` === `dropped.length`
- `report.failed` === number of `command` blocks with `exit !== 0`

`claims`/`verified`/`inferred` count the *whole generation run*, including claims
that never made it into a stop. They are deliberately larger than what the page
renders — that gap is the point of the pitch.

## `files` — the bundled source

```jsonc
"files": {
  "src/api/app.py": { "58": "@router.post(\"/v1/price\")", "59": "async def price_instrument(" }
}
```

Path → (line number as a string) → that line's text, **verbatim, without the
trailing newline**. Only lines actually reachable from some anchor need to be
present; the map is sparse and ranges may be non-contiguous. Every line in
`[anchor.start, anchor.end]` must exist or the anchor fails.

## `map`

```jsonc
"nodes": [ { "id": "api", "label": "src/api", "loc": 1240, "files": 9,
             "x": 88, "y": 212, "w": 132,
             "why": "Owns the single HTTP surface…",
             "top": ["app.py (41 commits)", "schemas.py (28)"] } ],
"edges": [ { "a": "api", "b": "instr", "n": 14 } ]
```

`x`/`y`/`w` are laid out at generation time — there is no layout engine in the
page (spec §4.4). Node area ∝ `loc`, edge thickness ∝ `n`. Every edge's `a` and
`b` must name an existing node.

`@3` extends the map additively (see the `@3` table above for the full list):

```jsonc
"map": {
  "w": 1000, "h": 520,
  "columns": [ { "label": "LAYER 2", "x": 340, "line": true } ],
  "note":    { "title": "WHAT IS NOT ON THIS BOARD", "text": "…" },
  "tour":    [ { "id": "n-data", "text": "…" } ],
  "nodes":   [ { "id": "n-data", "…": "@2 fields as above", "h": 64,
                 "path": "src/pkg/data/",
                 "role": ["para 1", "para 2"], "reads": "…", "feeds": "…",
                 "key_files": [ { "file": "measures.py", "purpose": "…" } ],
                 "concepts": ["…"],
                 "anchor": { "…": "standard anchor" }, "anchor_caption": "…" } ]
}
```

Gate rules: every `columns[].x` is numeric and inside `[0, map.w]` (renderer
fallback 900 when `w` is absent); every `tour[].id` names an existing node, once;
`role` is a non-empty array of strings, `key_files` entries carry `file` and
`purpose`, `concepts` is an array of strings; a node `anchor` is hashed exactly
like a claim anchor; and on an `@3` payload every node carries a numeric `h`
(the renderer no longer derives it there — `@2` nodes still get the derived
fallback). A node without `role` falls back to `why`/`top` in the drawer, which
is why both stay required on every node.

## `tracks` → `stops` → `blocks`

```jsonc
"tracks": [ { "title": "ORIENT",
              "stops": [ { "id": "five", "title": "Five sentences",
                           "minutes": 4, "blocks": [ ] } ] } ]
```

Stop `id` must be unique across the whole payload — it is the URL hash and the
localStorage key.

---

## Anchor and claim

```jsonc
{ "id": "c-001",
  "text": "payments-core prices instruments behind a single HTTP endpoint.",
  "status": "verified",
  "anchor": { "file": "src/api/app.py", "start": 58, "end": 66,
              "focus": [63, 65],
              "sha256": "a28c84fa7d06…" } }
```

- `start`/`end` are **1-based and inclusive**, matching the real file. Never
  renumbered from 1 (spec §4.2).
- `focus` lines must fall inside `[start, end]`.
- `status` is `verified` or `inferred`. **`dropped` never appears here** — dropped
  claims live only in the top-level `dropped` array.
- An `inferred` claim must carry **no anchor at all**. An anchor is what makes a
  claim render as verified; an inferred claim with one is a lie by markup, and the
  gate fails it.

### `sha256` — exactly what is hashed

> Hex SHA-256 of the source lines `start..end` **joined with `\n`**, with **no
> trailing newline** and **no line numbers**, UTF-8 encoded.

Both sides must compute it identically or every anchor drops:

- **Stage 4 (VERIFY)** computes it by re-reading the file on disk at the recorded
  commit. Mismatch → the claim is dropped and counted.
- **`tools/verify-contract.js`** recomputes it from `files`, which proves the
  excerpt shipped in the bundle is still the one that was hashed at generation
  time.

## Block types — the complete set

RENDER implements exactly these eleven and nothing more.

| `type` | Fields |
|---|---|
| `prose` | `claims[]` |
| `excerpt` | `anchor`, `caption` |
| `command` | `cmd`, `cwd`, `exit`, `dur`, `out`, `env`, `broken?`, `hypothesis?`, `predict?` |
| `graph` | *(none — renders the top-level `map`)* |
| `table` | `columns[]`, `rows[][]`, `caption`, `sortable` |
| `trace` | `steps[]` = `{ claim, anchor, next, predict? }` |
| `checkpoint` | `id`, `kind`, `prompt`, `options[]`, `answer`, `provenance`, `explanation` |
| `callout` | `level`, `title`, `text` |
| `ledger` | *(none — renders `report` + `dropped`)* |
| `lineage` | `title`, `entities[]` |
| `stats` (`@3`) | `items[]` = `{ v, l, s?, of?, color? }` |

Notes that the gate enforces:

- **`command`** — `dur` is a display string (`"11.4 s"`), `env` is the capture note
  (`"captured 2026-07-30, ubuntu-22.04, docker 24.0.7"`). Every command needs both,
  plus non-empty `out`. Any command with `exit !== 0` **must** carry `broken` (the
  red banner text); its `hypothesis` is the cause guess and is always rendered
  tagged `inferred`, because it is one. Output is real or the run is a fraud —
  non-negotiable #4.
- **`predict`** (`@2`) — a non-empty question string, nothing else. RENDER supplies
  the options and derives the key: for a command, "it passes / it fails" against
  `exit`; for a trace hop, the sorted set of files in that trace against the next
  hop's `anchor.file`. While a prediction is unanswered, RENDER withholds the exit
  pill, timing, `broken` banner and output (or the `next` pointer), **and veils the
  blocks after it** so the answer is not sitting further down the same screen.
  Veiled content is present in the DOM and is un-veiled for print, so nothing is
  silently omitted (spec §6) and acceptance test 11 still holds.
- **`table`** — every row's length must equal `columns.length`. Cells are HTML
  strings; a cell may carry a claim marker.
- **`checkpoint`** — `kind` is `single` (answer = 0-based index into `options`) or
  `order` (answer = permutation of `1..n`). `provenance` and `explanation` are
  both required: the answer key comes from `survey.json`, not the model
  (non-negotiable #6), and `provenance` is where it says so on screen.
- **`callout`** — `level` is `info`, `inferred`, or `broken`. Three, no more
  (spec §4.7).
- **`excerpt`** is specified and supported by the gate but unused in the current
  fixture; the demo shows excerpts through claim markers and `trace` instead.

### `lineage` — where values come from

Execution flow says function A calls function B. Lineage says a value originates
at Y, is rewritten by B, and decides Z. The unit is the value, not the call, so
the stages are fixed rather than discovered and the block sits beside `trace`
rather than replacing it.

```jsonc
{ "type": "lineage", "title": "Data Sources & Lineage",
  "entities": [
    { "id": "payload", "name": "The verified payload",
      "meaning": "Why the repository needs this data.",
      "status": "verified",
      "steps": [
        { "stage": "SOURCE", "label": "Fixture on disk",
          "description": "One sentence on what happens here.",
          "evidence_type": "config", "status": "verified",
          "anchor": { "file": "…", "start": 25, "end": 28, "sha256": "…" } }
      ],
      "failure_mode": { "text": "What happens when it is missing or invalid.",
                        "status": "verified", "anchor": { } },
      "boundary":     { "text": "Where the visible lineage stops.", "status": "inferred" },
      "tests":        [ { "label": "…", "kind": "runtime", "note": "…" } ] } ] }
```

`stage` is free text rendered as a small uppercase label — `SOURCE`, `INGESTION`,
`VALIDATION`, `PARSE`, `TRANSFORM`, `CONSUMER`, `OUTCOME` are the ones in use.

`evidence_type` is one of `source` · `runtime` · `test` · `config` · `graph` ·
`git` · `inference`, shown as quiet uppercase text beside the status.

**`status` on a step is `verified`, `derived` or `inferred`** — a third state the
rest of the contract does not have, because a lineage edge is often computed from
the call or import graph rather than read off one line. The gate enforces what
each may carry:

- `verified` **must** have an anchor, unless `evidence_type` is `runtime` — that
  evidence is captured output, not a line range.
- `derived` **may** have one. The anchor proves the code exists; the derivation is
  the reasoning laid over it, and the status label says so on screen.
- `inferred` **must not**. An anchor is what makes a step render as evidenced.

**A `boundary` can never be `verified`.** It is by definition the thing that could
not be established from this repository; calling it verified would claim knowledge
of what lies outside. The gate fails a payload that tries.

`tests` may be empty, and the renderer says *"No direct test was found for this
data flow"* rather than omitting the row — an absent test is information.

Unresolvable steps are **downgraded, not deleted**, unlike a trace hop. `SOURCE →
… → OUTCOME` is a fixed shape and removing its middle would misrepresent the flow
rather than shorten it: a reader would see INGESTION feeding CONSUMER and conclude
no transform happened. The step keeps its place, loses its anchor, becomes
`inferred`, and the drop is still recorded in the ledger.

## `dropped` — the ledger

```jsonc
{ "id": "c-031",
  "text": "Prices are cached in Redis for 30 seconds.",
  "file": "src/io/cache.py",
  "reason": "file does not exist at this commit" }
```

`reason` is required and must be the real one. Observed reasons so far:
snippet not found verbatim in file · file does not exist at this commit ·
lines N-M out of range (file ends at K) · excerpt hash mismatch — file changed
after narration.

A dropped `id` must not appear anywhere in `tracks`. The gate checks this, because
rendering a claim the report says was dropped is the one failure that would
discredit the entire pitch.

---

## Changing this contract

Bump `contract` to the next version, add it to the `KNOWN` list in
`tools/verify-contract.js`, update `fixtures/verified.sample.json`, re-run
`node tools/inline-fixture.js`, and confirm both gates still exit 0. The fixture
is the single source of truth for the demo bundle — edit the JSON, never the
`const D` block inside the HTML.

A new field is only real when the gate enforces it. `@2` shipped with four
assertions and four negative tests; do the same.

### What the gate asserts for `@3`

All additive; the frozen `@2` fixtures and the demo bundle pass unchanged.

- `trailhead/verified@3` appended to `KNOWN` (`@1`/`@2` still accepted).
- `glossary`: array; slug ids `[a-z0-9-]+`, unique; `term` and `def` non-empty;
  an `anchor`, when present, goes through the same validator as a claim anchor
  (bundled, whole, sha256-matched).
- Explicit `[[id|label]]` markers in claim text, ledes, callout text, map note,
  tour text, node `role`/`reads`/`feeds`, and `key_files[].purpose` must resolve
  to a glossary id. Bare `[[Label]]` markers degrade and are not gated.
- `map.columns[]`: non-empty `label`; numeric `x` inside `[0, map.w]`
  (900 when `w` is absent, mirroring the renderer's viewBox fallback).
- `map.tour[]`: each `id` names an existing node, no duplicates, non-empty text.
- `map.nodes[]`: `role` a non-empty array of strings; `key_files` entries carry
  `file` + `purpose`; `concepts` an array of strings; `reads`/`feeds` strings;
  node `anchor` hashed; on `@3`, every node carries a numeric `h`.
- `stats` joins the closed block-type vocabulary (an unknown type still fails):
  `items` non-empty; `v`/`l` non-empty strings; `s`/`of` strings when present;
  `color` one of `ok | inf | bad`.
- Dash scan (`@3` payloads only): no U+2014/U+2013 in authored strings (list in
  the dash-policy section above). The `files` map and command `out` are exempt.

Each assertion carries a negative test: a mutation harness clones
`fixtures/verified.parity.json`, breaks one rule per case (45 cases: 40 expected
failures with message match, 5 expected passes proving the exemptions and the
`@2` scoping), and asserts the gate's verdict. Re-create any case as a one-liner,
e.g.:

```bash
node -e "const D=require('./fixtures/verified.parity.json');D.map.tour[0].id='n-ghost';require('fs').writeFileSync('mut.json',JSON.stringify(D))" && node tools/verify-contract.js mut.json   # expect: FAIL tour step n-ghost
```
