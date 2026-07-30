# Owner D — The artifact. The thing on the projector.

## Paste this into Claude Code

```
I own RENDER — the generated HTML artifact — for Trailhead, a hackathon project
in this repo. The renderer already works; my job is to make it demo-grade.

Read in this order:
  CLAUDE.md
  hackathon/briefs/D-render.md          <- my brief, follow it
  hackathon/docs/walkthrough-spec.md    <- authoritative for anything the page does
  hackathon/docs/verified-contract.md   <- the 9 block types, frozen
  hackathon/demo/trailhead-demo.html    <- what exists, 65 KB, gates passing

Rules: I edit demo/trailhead-demo.html only. The page's DATA comes from
fixtures/verified.sample.json spliced in by tools/inline-fixture.js — I never
edit the data inside the HTML. No external requests, ever: no CDN, no font, no
fetch. Skip TDD here and iterate against the browser, but both gate checks must
exit 0 before I claim anything works.

Start by opening the demo, then tell me the three biggest gaps against spec §7
and §8 in priority order.
```

## Mission

Four people generate a JSON file. You are the reason anyone cares. The artifact
is what goes on the projector, and the judges' entire impression of Trailhead is
formed by how this page looks and feels in about ninety seconds.

## You own

```
demo/trailhead-demo.html   the renderer + the page
tools/inline-fixture.js    the splice step (coordinate with E)
```

Later, when E stands up `src/trailhead/render.py`, the HTML becomes its template
and you still own it. **Never touch:** any `.py` in `src/trailhead/`,
`fixtures/*` (shared — ask E first).

## Where you're starting from — better than it sounds

```bash
cd hackathon
node tools/check-bundle.js      # BUNDLE OK — 21 checks, 65.2 KB
node tools/verify-contract.js   # ALL ANCHOR + CONTRACT CHECKS PASS
                                # 5 tracks | 11 stops | 13 anchors | 8 dropped
```

This is a **real render**, not a mockup: it renders `verified.sample.json`
through the same code path the generator will use, and the renderer contains no
reference to the sample repo. Claim markers, the audit panel, the trace stepper,
checkpoints and the graph all work today.

So your job is not to rebuild it. It is the gap between "works" and "makes a
room go quiet."

## The one workflow rule

```bash
# change what the page SAYS:
$EDITOR fixtures/verified.sample.json   # <- ask E first, it is shared
node tools/inline-fixture.js

# change what the page IS:
$EDITOR demo/trailhead-demo.html        # <- yours alone
```

Never hand-edit the `const D` data block inside the HTML. It gets overwritten,
and the gates will catch you.

## Build order

1. **Projector mode.** Spec §7 budgets two hours and says plainly: *this is what
   the pitch runs on.* One toggle → base font 20 px, sidebar hidden, excerpts to
   12 visible lines. Test it at the back of an actual room if you can.
2. **The claim marker interaction.** This is the money shot — click a superscript,
   the excerpt expands inline with focus lines marked. It exists; make it fast,
   obvious, and beautiful. A judge will click exactly one, and that click is the
   pitch. Focus lines need a left marker *and* a background, never colour alone.
3. **The audit panel.** Second money shot: "here are the eight claims it caught
   the model inventing." Sortable, filterable, with the reason column readable
   from six feet away. Non-negotiable #3 — the drop count lives in the top bar
   and never comes off.
4. **MapGraph.** Inline SVG, layout already computed by A. Hover highlights
   neighbours, click opens the drawer, `0` resets zoom. The 40-node density cap
   and the text fallback beneath both matter on a real repo — the fixture's six
   nodes will not show you the hairball.
5. **Degraded generation (§6).** Every one of these *will* fire on an unfamiliar
   repo at hour 8: no entry point, no test command, all setup commands failed,
   fewer than three modules, over 40% of claims dropped → amber badge. A labelled
   gap reads as a tool that knows its limits; a blank stop reads as a bug.
   **Build these before hour 8, not during the panic.**
6. **Acceptance tests 7–11**, from spec §8 — these are yours and nobody else will
   run them:
   - 7 — progress survives reload; a changed commit SHA starts fresh state
   - 8 — no horizontal body scroll at 1440 / 1024 / 768 / 375 px
   - 9 — the full course completable by keyboard only, visible focus ring
   - 10 — light and dark both pass 4.5:1 on every text/background pair
   - 11 — print output contains every stop with all blocks expanded
7. **Print stylesheet.** Cheap, and it means a judge can PDF the whole course.

## Hard constraints — the gates enforce all of these

| | |
|---|---|
| One file | No sidecar CSS, JS, fonts, or images |
| Zero external requests | No `http://` or `https://` in any `src`, `href`, `fetch`, `import`. Opens from `file://` with the network off. |
| Nine block types | `prose` `excerpt` `command` `graph` `table` `trace` `checkpoint` `callout` `ledger`. Render exactly these. A tenth needs a contract bump. |
| Under 5 MB | Currently 65 KB. Excerpts dominate on a real repo. |
| Chrome/Edge 110+ | No framework, no build step, no polyfills |
| No model in the page | Grading is local JS against an embedded key. No free-text questions. |

**Never cut, however far behind:** claim markers, the audit panel, the
dropped-claim count.

## Done when

```bash
cd hackathon
node tools/check-bundle.js && node tools/verify-contract.js   # both exit 0
```

plus acceptance tests 7–11 pass by hand, and projector mode is legible from the
back of the room.

## Traps

- **Reaching for a CDN.** One `<script src="https://…">` fails the gate and
  breaks the offline promise the whole artifact rests on. Inline everything;
  embed images as `data:` URIs.
- **Colour-only meaning.** Verified/inferred/broken each need an icon or label
  too. It is in the spec, it is an acceptance test, and it is the kind of thing a
  judge notices.
- **Making it pretty at the cost of the evidence.** If a redesign hides the drop
  count or softens the claim markers, it is the wrong redesign.
- **The fixture is six modules and eleven stops.** A real repo gives you forty
  modules, sixteen stops, and a 400-line command output. Test against something
  hostile before hour 8 — ask E for an early real `verified.json`.
