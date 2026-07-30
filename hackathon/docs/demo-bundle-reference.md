# `demo/trailhead-demo.html` — implementation reference

What the generated artifact actually is: its layout, its state model, how a payload
becomes a page, and what the gates hold it to. `walkthrough-spec.md` says what the
page *should* be and `verified-contract.md` says what it *eats*; this describes
what the file in the tree *does*.

## Snapshot this describes

| | |
|---|---|
| File | `hackathon/demo/trailhead-demo.html` |
| Lines | 2 976 |
| Size | 128 303 bytes (125.3 KB) |
| MD5 | `98394c995f67733752a052df46075859` |
| Captured | 2026-07-30 19:01:10 |
| Payloads carried | `payments-core` @ `a3f9c21`, `ML-GS` @ `fb3c3ce` |

> **Line numbers here go stale quickly.** This file was rewritten three times in the
> hour before this snapshot (1 677 → 1 729 → 2 976 lines), twice while it was being
> read. Treat every line reference as "as of the MD5 above" and re-pin with `grep -n`
> before relying on one. Structural landmarks — the marker comments, the function
> names, the `B` keys — are stable; the numbers are not.

---

## 1. Layout

One file, four regions.

| Lines | Region | Contents |
|---|---|---|
| 1–6 | Head | doctype, `lang="en"`, `data-theme="dark"`, charset, viewport, title |
| 7–550 | `<style>` | all CSS, ~540 lines, no external font or import |
| 552–590 | Body shell | static chrome only — every one of these elements is empty on load and filled by JS |
| 592–2557 | Data block | `const BUNDLES` + `const SYNTHETIC`, fenced by marker comments |
| 2559–2974 | Renderer | ~415 lines that know only the nine block types |

The body shell is worth reading once (552–590): it is nine empty containers.
`#rname`, `#rmeta`, `#badge`, `#rsel`, `#rail`, `#sprocket`, `#stage`, `#dbody`,
`#mbody` all start empty. Nothing about either repo is hard-coded in the markup —
which is a deliberate change from the earlier version, where the top bar carried
literal counts that could silently drift from the payload (`topbar()`, line 2585
comment).

---

## 2. The data block

Fenced by two literal markers, and the fence is load-bearing:

```
/* ==== TRAILHEAD-DATA-START ==== */     line 598
const BUNDLES = { … }                    599–2553
const SYNTHETIC = {"payments-core":true} 2556
/* ==== TRAILHEAD-DATA-END ==== */       line 2557
```

`BUNDLES` is a map of repo name → one complete `verified.json` payload. A real
generated artifact carries exactly one; this demo carries two so both walkthroughs
share a renderer instead of shipping as near-identical files (comment at 2565–2568).
The renderer never sees the map — `loadRepo()` picks one and assigns it to `D`.

`SYNTHETIC` is demo-only bookkeeping, kept *outside* the payloads so each stays a
pure `verified.json` (comment at 2554–2555). It drives one thing: the
`SAMPLE · SYNTHETIC REPO` chip in the top bar.

**Never hand-edit this block.** `tools/inline-fixture.js` regenerates it from a
fixture; the fixture is the source of truth.

---

## 3. State model

Four module-level bindings, all reassigned by `loadRepo()` (2569):

| Binding | What it holds |
|---|---|
| `D` | the active payload — the only thing the renderer reads |
| `KEY` | `"trailhead:" + repo.name + ":" + repo.commit` |
| `STOPS` | every stop, flattened across tracks, each tagged with its track title and index |
| `S` | learner state — the only thing the page writes |

`S` has five fields (2578):

```js
S = { cur: 0, done: {}, ans: {}, pred: {}, conf: {} }
```

- `cur` — current stop index
- `done[stopId]` — visited (non-checkpoint stops mark themselves done on render, 2845)
- `ans[cpId]` — `{pick, ok}` for checkpoints
- `pred[predId]` — `{pick, ok}` for predictions
- `conf[cpId]` — `"sure"` or `"guessing"`, captured *before* the answer

Persistence is deliberately forgiving: the read is wrapped in `try/catch` (2579) and
so is the write (2570), so private mode or a full quota degrades to in-memory state
rather than a broken page. Two keys are used — the per-walkthrough `KEY`, and
`"trailhead:repo"` (2581) remembering which bundle you were last in.

Because `KEY` includes the commit, a regenerated artifact starts clean instead of
replaying old answers against changed content.

---

## 4. Lifecycle

```
boot (2967–2973)
  └─ read "trailhead:repo"      → which bundle
  └─ loadRepo(name)             → D, KEY, STOPS, S, topbar()
  └─ draw(hash-stop or S.cur)
        ├─ veil(s.blocks) → B[b.type](b) per block
        ├─ rail()         → outline, sprocket, percentage
        └─ wireMap()      → graph hover/click, if a graph is on this stop
```

`draw(i)` (2832) is the single render entry point. Everything that changes state ends
by calling `save(); draw(S.cur)` — a full re-render rather than a patch. At this size
that is the right trade: no diffing, no stale DOM, and every block re-reads `S`.

Repo switching (2960–2965) is a full reload of the walkthrough: new payload, new
outline, new progress key, and the URL hash is dropped because stop ids are per-repo.

---

## 5. Block renderers

`B` (2659–2749) maps `block.type` → a function returning an HTML string. Nine keys,
matching the contract exactly.

| Type | Reads | Notes |
|---|---|---|
| `prose` | `claims[]` | Two branches. `inferred` → plain span + tag, **no marker, no popover**. Otherwise → claim + `.mark` button + hidden `.pop` holding the excerpt. The verified/inferred distinction lives in this markup, not in the data. |
| `excerpt` | `anchor`, `caption` | Thin wrapper over `excerpt()` |
| `command` | `cmd`, `exit`, `dur`, `out`, `env`, `broken?`, `hypothesis?`, `predict?` | With an open prediction, the verdict, timing, banner, output and fail border are all withheld |
| `callout` | `level`, `title`, `text` | Three levels: `info`, `inferred`, `broken` |
| `table` | `columns`, `rows`, `caption`, `sortable` | Cells are raw HTML; right-aligns numeric-looking columns past index 1 |
| `graph` | top-level `D.map` | Delegates to `graph()` |
| `trace` | `steps[]` | Worked-example fading — see §6 |
| `checkpoint` | `id`, `kind`, `prompt`, `options`, `answer`, `provenance`, `explanation` | Confidence-gated — see §6 |
| `ledger` | top-level `D.report`, `D.dropped` | Delegates to `ledgerTable()` |

Dispatch is unguarded: `B[b.type](b)` inside `veil()` (2653). A payload carrying a
type the renderer does not know throws a `TypeError` and the stage renders empty.
`tools/verify-contract.js` rejects unknown types on the payload side, but nothing
checks that the renderer learned a type the checker was taught — teaching one and
not the other yields a green gate and a blank stop.

### `excerpt(a, cap)` — 2628

The shared evidence renderer, used by `prose`, `excerpt` and `trace`. Walks
`a.start..a.end`, emits a two-column table of line number and source, highlights
`a.focus`, and emits a `… elided` row for any line missing from the bundle rather
than failing. The COPY button carries the joined raw text.

### `graph()` — 2788

Draws the module map into a 900×400 SVG. Node height is `44 + sqrt(loc)/6`; the
comment at 2791–2794 records why the floor is 44 (the previous `34 + sqrt(loc)/9`
bottomed out at 37 px and overlapped two text lines on five of six nodes). Edge
stroke width is `0.7 + n/16`. Layout comes from the payload — `x`, `y`, `w` are
computed at generation time; there is no layout engine in the page.

It also emits a `<details>` text equivalent listing every module and its imports,
which is what makes the map usable without the SVG.

---

## 6. Teaching mechanics

Three features that are not in the original spec and are worth understanding before
changing block rendering.

**Predict-then-reveal** (`predict()`, 2611). Commit to an answer before the page
shows you the real one. The key is never authored — for a command it is the captured
exit code, for a trace hop it is the next hop's resolved anchor. A prediction
therefore cannot disagree with what the page then shows (comment at 2605–2610).

**Veiling** (`veil()`, 2650). A prediction is worthless if the answer sits further
down the same screen. Everything after an unanswered prediction is rendered into the
DOM but wrapped in `.veil` — hidden visually, still present for print and for
assistive tech. Nothing is silently omitted.

**Confidence before answering** (2720–2729). A checkpoint asks "how sure are you?"
before it will accept an answer; `gate` disables the options until you say. Captured
before, never after, or it is hindsight rather than calibration. `yourScore()` (2773)
then reports the interesting number: confident *and* wrong.

`yourScore()` output is local-only, cleared by RESET, and explicitly never part of the
generated artifact (2784).

---

## 7. Interaction

All clicks go through one delegated listener (2884–2941), matched by `closest()` in
priority order:

`[data-go]` stop nav · `[data-nav]` prev/next · `.mark` claim popover ·
`[data-copy]` copy · `[data-pi]` prediction pick · `[data-conf]` confidence ·
`[data-pick]` checkpoint pick · `.sub[data-go]` order submit · `th[data-sort]` sort ·
`#badge` ledger modal · `#mx`/`#scrim` close · `#dx` drawer · `#menu` rail ·
`#theme` · `#proj` · `#reset`

Keyboard (2942–2951): `Escape` closes drawer and modal, `←`/`→` move between stops
(suppressed inside form fields), `Enter`/`Space` activate checkpoint and prediction
options. Table sort is numeric when both cells parse as numbers, `localeCompare`
otherwise.

---

## 8. Presentation

**Theming.** `:root` (23) is dark; `:root[data-theme="light"]` (47) overrides, and
`@media (prefers-color-scheme:light)` (59) picks up system preference. The `#theme`
button flips `data-theme` on the root element, which wins over the media query.

Three font stacks — `--sans`, `--serif`, `--mono` (30–32) — all system faces.
Goldman Sans cannot ship in this file: embedded font at-rules are barred by
`check-bundle.js`, so `--sans` approximates it (header comment, 13).

**Projector mode.** `:root[data-proj="1"]` (475–479) raises base font to 20 px, hides
the rail and progress bar, widens the column and enlarges code.

**Responsive.** Breakpoints at 900, 700 and 480 px (482, 498, 509); the hamburger is
hidden above 900 (515).

**Reduced motion.** All animation and transition disabled under
`prefers-reduced-motion` (516).

**Print.** `@media print` (519) forces a page break after each stop and kills
animation, so the printed copy contains every stop with blocks expanded.

---

## 9. What the gates enforce

| Gate | Holds this file to |
|---|---|
| `tools/check-bundle.js` | Zero external loads, no stylesheet links, no embedded font at-rules, inline style and script present, doctype/title/lang/viewport, under 5 MB, theme + reduced-motion + print + focus-visible + projector + localStorage all present, inline JS parses, CSS braces balanced |
| `tools/verify-contract.js` | Every anchor resolves and re-hashes, focus lines inside range, inferred claims carry no anchor, dropped claims render nowhere, failing commands carry a banner, checkpoint keys well formed, report matches the page |
| `tools/check-fixtures.js` | The four `*.sample.json` fixtures still describe one repo at one commit |

---

## 10. Known issues as of this snapshot

**`verify-contract.js` cannot read this file.** It exits 1 with a `SyntaxError`, so
the demo currently has no contract coverage.

```
node tools/verify-contract.js
→ SyntaxError: Unexpected token ';'  at verify-contract.js:41
```

Cause: the extractor slices from `BUNDLES`'s opening brace to
`raw.lastIndexOf('};')` (line 41). `raw` is everything between the two markers,
which also contains `const SYNTHETIC = {…};` — so the last `};` belongs to
`SYNTHETIC`, and the slice swallows the end of `BUNDLES`, the comment and the
`SYNTHETIC` declaration. The `eval` then fails.

Both payloads pass when checked directly, which isolates the fault to the scraper:

```
node tools/verify-contract.js fixtures/verified.sample.json  → PASS  exit 0
node tools/verify-contract.js fixtures/verified.ml-gs.json   → PASS  exit 0
```

Two fixes, either sufficient: move `SYNTHETIC` outside the marker fence, or bound the
slice to the `BUNDLES` declaration by brace-matching the way `inline-fixture.js`
already does.

**`demo/trailhead-ml-gs.html` fails the same gate differently.** It was built from
the pre-marker shell, so it carries `const D = {` and no fence:

```
node tools/verify-contract.js demo/trailhead-ml-gs.html
→ data markers not found (start=-1 end=-1)   exit 2
```

Since its payload is now carried inside `trailhead-demo.html` as the `ML-GS` bundle,
that standalone file is redundant and can be deleted, or regenerated from the current
shell if a single-repo artifact is still wanted.

**`check-bundle.js` cannot appear in its own artifact.** Its pass lines name a
stylesheet link tag and a font at-rule, and the gate greps raw bytes — so embedding
its output makes it match its own report. It cannot distinguish real markup from
string data inside the payload. This is why the ML-GS walkthrough shows four
captured commands and a callout rather than five.
