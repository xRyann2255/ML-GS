# Template parity: `trailhead/verified@3` and the generator upgrade

**Status:** implementation spec, 2026-07-31. The quality lock is
`out/trailhead-mlvol-template.html` (hand-built; source in `template/`). This
spec makes the generator produce that artifact class for ANY repo.

**Strategy decision.** Two options were weighed: (a) port the template renderer
wholesale and teach stages 1-4 to feed it; (b) keep the old renderer and add
features incrementally. We take (a): the renderer IS the quality bar, reusing it
byte-for-byte removes an entire class of drift, and the old renderer has no
consumers other than the demo bundle (which keeps it, unchanged, at `@2`).

Everything below is additive: a valid `@2` payload renders correctly in the new
renderer (new features simply do not appear). The demo bundle is not migrated.

---

## 1. Contract additions (`trailhead/verified@3`)

### 1.1 `glossary` (top level, optional)

```jsonc
"glossary": [ { "id": "qlike", "term": "QLIKE", "def": "1-2 sentences.",
                "anchor": { "file": "...", "start": 1, "end": 9,
                            "focus": [3], "sha256": "..." } } ]
```

- `id` is a slug `[a-z0-9-]+`, unique. `anchor` optional; when present it is a
  standard anchor (hashed, verified, bundled into `files`). No anchor = the
  popover shows the definition only.
- Verified by stage 4 like a claim; failures drop the ANCHOR (entry keeps its
  definition) and are recorded in `dropped` with `id: "g-<slug>"`.

### 1.2 Inline markup in authored text

In `claim.text`, `stop.lede`, `callout.text`, `map.tour[].text`,
`map.nodes[].role[]`, `reads`, `feeds`, `key_files[].purpose`:

- `` `code` `` renders as `<code>`.
- `[[id|label]]` or `[[Label]]` renders as a glossary term (dotted underline,
  popover). An explicit `[[id|label]]` whose `id` is not in `glossary` FAILS the
  gate; a bare `[[Label]]` that does not slug-match degrades to plain text.
- Raw HTML stays banned in claim text (narrate schema already rejects `<`).

### 1.3 `map` additions

```jsonc
"map": {
  "w": 1000, "h": 520,                       // viewBox, computed by MAP
  "columns": [ { "label": "LAYER 2", "x": 340, "line": true } ],
  "note":    { "title": "WHAT IS NOT ON THIS BOARD", "text": "..." },   // optional
  "tour":    [ { "id": "n-data", "text": "..." } ],                     // optional
  "nodes":   [ { "id": "n-data", "label": "data", "loc": 9195, "files": 21,
                 "x": 260, "y": 40, "w": 150, "h": 64,
                 "path": "src/pkg/data/",
                 "role": ["para 1", "para 2"],                          // optional
                 "reads": "...", "feeds": "...",                        // optional
                 "key_files": [ { "file": "measures.py", "purpose": "..." } ],
                 "concepts": ["..."],
                 "anchor": { }, "anchor_caption": "...",                // optional
                 "why": "fallback text", "top": ["..."] } ],
  "edges":   [ { "a": "n-cli", "b": "n-data", "n": 48 } ]
}
```

- `h` on a node is now explicit (renderer no longer derives it).
- `role` present -> drawer renders narrated paragraphs; absent -> falls back to
  `why`/`top` exactly as `@2` renders today. Every `tour[].id` must name an
  existing node. `columns` may be empty (no header row painted).
- Nodes that are pure test containers (>= 60% of member files under a
  test-directory root) are OFF the board; they are named in `map.note` instead.

### 1.4 New block type `stats`

```jsonc
{ "type": "stats", "items": [ { "v": "96,897", "l": "LINES OF CODE",
                                "s": "sub line", "of": "22", "color": "inf" } ] }
```

`v`,`l` required strings; `s`,`of` optional; `color` optional, one of
`ok|inf|bad`. All values computed by COMPOSE from `survey.json`, never by the
model.

### 1.5 Existing block types

Unchanged. `checkpoint` gains optional confidence capture in the renderer (no
payload change). `command.predict` and `trace.predict` as `@2`.

### 1.6 Dash policy (authored text only)

No U+2014 or U+2013 in any AUTHORED string: claim/lede/callout/tour/role/def/
purpose/title/caption/provenance/explanation/`report.regen`. COMPOSE
transliterates model output (`—`->`, `, `–`->`-`) and the gate
re-scans. Bundled source lines in `files` are the repo's own bytes and are
EXEMPT (hash integrity wins); RESOLVE clips excerpt context windows to avoid
dash-bearing lines when the focus lines allow it, best effort.

---

## 2. Renderer (stage 5)

`src/trailhead/template.html` is replaced by an adaptation of
`template/walkthrough.template.html` (the quality lock):

- Payload embedding keeps the `@2` bundle shape for tool compatibility:
  `/* ==== TRAILHEAD-DATA-START ==== */` `const BUNDLES = {"<repo>": <payload>};`
  end marker, single entry, repo selector hidden for a single payload.
- All template features ship: engineering grid, whole-sentence claim toggles,
  sha chips, glossary popovers with jump-to-evidence, layered map with columns +
  default-dim edges + hover isolate + drawers + guided tour, stats tiles, cover
  START button, mobile rail toggle, print-all linearisation, confidence capture,
  predictions with veiling, audit modal with YOUR RECORD, quote-safe `esc()`
  (escapes `"` as well), overlay close on navigation.
- Renderer must render a `@2` payload (no glossary/columns/role/stats) without
  error: every new feature is conditional on its field.
- RENDER's own self-checks stay (payload marker replaced, no live external
  refs, balanced markers) and add: authored-string dash scan, `[[id|...]]`
  resolution scan.

## 3. Mapper (stage 2) additions

- Column assignment: longest-path layering over the group DAG after the existing
  backward-edge removal; column count capped at 7 (merge middle layers when
  deeper). Emit `columns[]` with `label: "LAYER <n>"` placeholders and `x`
  centers; geometry: `W=1000`, per-column span, node `w=150`,
  `h = 42 + min(28, sqrt(loc)/6)`, `y` stacked from 40 with 26 gap; `map.h`
  from tallest column + 8.
- Test-container groups off-board (rule in 1.3) and named in `map.note` along
  with the dangling-import count from `survey.dangling`.
- Emit `tour_order`: node ids in pipeline order (leftmost column to rightmost,
  top to bottom inside a column) for NARRATE to write tour text against.
- Keep `why`/`top` exactly as today (they are the no-narration fallback).

## 4. Narrate (stage 3) additions

New packs, same envelope (`unit`, `kind`, `title`, `system`, `user`, `windows`,
`schema`, `out`, `max_claims` where it applies). Every pack degrades to absence:
a missing answer file produces the `@2` behaviour, never a broken stop.

| unit | one per | answer schema (validated) |
|---|---|---|
| `node:<gid>` | top-K map groups (K<=10, by loc) | `{ "role": [2..3 strings], "reads": str, "feeds": str, "key_files": [{"file": one of the listed files, "purpose": str}], "concepts": [3..6 str], "cite": {file,quote,focus}?, "caption": str? }` |
| `gloss` | repo | `{ "terms": [ { "term": str<=40, "def": str<=300, "cite": {file,quote,focus}? } ] }`, max 14 terms |
| `dive:<gid>` | top-D groups (D<=5, by loc, excluding off-board) | claims pack identical to `five` (6..8 claims, each cite-or-inferred) |
| `tour` | repo | `{ "steps": [ { "id": <given node id>, "text": str<=340 } ] }`, ids fixed by the pack |
| `cols` | repo | `{ "labels": [str<=14 uppercase] }`, one per column, order given |

- Windows for `node:`/`dive:` packs: the group's top fan-in files (heads),
  package `__init__`, README slices. `gloss` windows: highest fan-in files
  across the repo plus README. `cite` rules identical to claims (verbatim,
  3-24 contiguous lines, resolver decides).
- `five` system prompt upgraded: sentences must state WHAT THE SYSTEM DOES in
  domain terms (never parser/CLI mechanics when a README or package docstring
  states a purpose); shape: what it is, what it consumes, how quality is
  judged, what the outputs feed, what is unusual about the repo, plus one
  honest inferred "what it is not".
- Model text may use backticks and `[[...]]` glossary markers; narrate schema
  keeps rejecting `<` and `](`.

## 5. Verify (stage 4) additions

- Resolve + hash: node `cite` -> `anchor` (failure: node keeps `why` fallback,
  ledger entry `n-<gid>`), glossary `cite` -> `anchor` (failure: definition
  kept, ledger entry `g-<slug>`), dive/five claims exactly as today.
- Tour: drop any step whose `id` is not on the board (ledger `t-<id>`); drop the
  whole tour if fewer than 3 steps survive.
- `[[id|label]]` refs: every explicit id must exist in the surviving glossary,
  else the marker is REWRITTEN to plain label (and counted in the
  verification-report, not the ledger; it is a formatting downgrade, not a lie).
- Dash transliteration of all authored strings (1.6) happens here, after
  resolution, before assembly.
- `report` counting now includes glossary and node cites in `claims`/`verified`
  totals? NO: they are anchors, not claims. New report fields (additive):
  `report.anchors` (total anchors shipped), unchanged claim math. The gate
  cross-checks `dropped.length` as today.

## 6. Compose additions

- Cover: `stats` tiles (loc, py files, test file count, module count, command
  count/failures, dangling count when > 0), generation-record table, START
  handled by renderer.
- Setup stop: when `survey.dangling` is non-empty, insert the RESTORE LEDGER
  table (module, import-site count) + a `broken` callout naming the top
  offenders. Generic title: "Missing at this commit".
- New track `INSIDE THE SYSTEM` with one stop per `dive:` answer, titled
  `Inside <label>`, blocks: prose claims + one `excerpt` (the node anchor when
  present) + optional `stats` for that group (loc/files/fan-in, deterministic).
- Glossary stop in CLOSE: table generated from surviving glossary entries.
- Map stop lede mentions the tour when `map.tour` is present.
- All authored compose text is dash-free at the source.

## 7. Gates and docs

- `tools/verify-contract.js`: add `@3` to `KNOWN`; enforce: glossary shape +
  anchor hashes + id uniqueness; tour ids exist on the board; stats field
  types + color enum; node `role`/`key_files`/`concepts` types; explicit
  `[[id|...]]` refs resolve; authored-string dash scan (files{} exempt);
  `node.h` present and numeric; every column `x` inside the viewBox. Negative
  tests for each, per the contract-change protocol.
- `tools/check-bundle.js`: unchanged checks still pass against the new
  renderer (no font at-rules, no external refs, reduced-motion, print,
  focus-visible, data-theme, localStorage, contained overflow). Add: grid
  background present, `railbtn` present.
- `docs/verified-contract.md` and `docs/walkthrough-spec.md` updated in the
  same change (the `@2` protocol requires all three to move together).
- `fixtures/verified.sample.json` stays `@2` (demo). New
  `fixtures/verified.parity.json`: minimal `@3` payload exercising every new
  field, used by gate tests and `tests/test_render.py`.

## 8. Test plan

pytest additions: mapper layering (DAG -> columns, off-board tests rule),
compose @3 assembly (stats math, restore ledger, dive stops, glossary stop),
verify (glossary/node/tour resolution, ref rewriting, dash transliteration),
narrate (new pack schemas accept/reject), render (parity fixture renders, @2
fixture renders). Existing tests must stay green except where they pin `@2`
behaviour that `@3` deliberately extends (update those with a comment).

## 9. Rollout order

1. Renderer + render.py + parity fixture (everything else still emits @2).
2. Mapper columns/geometry/off-board/tour_order.
3. Prompts/narrate new packs.
4. Verify resolution + sanitisation.
5. Compose @3 assembly + checkpoints untouched.
6. Gates + docs + tests.
7. End-to-end on `restored` + fixture repos; judge loop against the template.
