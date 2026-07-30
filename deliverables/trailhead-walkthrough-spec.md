# Trailhead — HTML Walkthrough Spec

**What this document covers:** the generated artifact only — the single HTML file a new joiner opens. The generator pipeline (survey → map → narrate → verify → render) is specified separately.

**One-line definition:** one self-contained HTML file, no server, no network, that teaches a specific repo in about 90 minutes and shows its own evidence.

---

## 1. Hard constraints

| Constraint | Value | Why |
|---|---|---|
| Output | 1 `.html` file | Opens from `file://` on a locked-down laptop |
| External requests | Zero | Corporate network blocks them; also a testable build invariant |
| CSS / JS / fonts / graph | All inline | Same reason |
| Model calls at view time | None | Page is static; grading is local JS against an embedded key |
| Size target | < 2 MB, hard cap 5 MB | Excerpts dominate; cap and elide |
| Browser floor | Chrome/Edge 110+ | No build step, no framework, no polyfills |
| Works offline after generation | Yes | Reviewers open it on a train |

**Build-time invariant:** render fails if the output contains `http://` or `https://` in any `src`, `href`, `fetch`, or `import`. One grep, enforced in CI.

---

## 2. Page shell

```
┌─────────────────────────────────────────────────────────────────────┐
│ payments-core   ·  commit a3f9c21  ·  gen 2026-07-30                │  top bar (sticky)
│                    [142 claims · 8 dropped · 23 cmds · 2 failing]   │  verification badge
│                                        [projector] [theme] [reset]  │
├──────────────────┬──────────────────────────────────────────────────┤
│ ORIENT           │                                                  │
│  ✓ Cover         │   Stop 2 — The map                               │
│  ✓ Summary       │                                                  │
│  ▸ The map       │   ┌────────────────────────────────────────┐     │
│    Where code is │   │                                        │     │
│    Checkpoint A  │   │      interactive module graph          │     │
│                  │   │                                        │     │
│ GET IT RUNNING   │   └────────────────────────────────────────┘     │
│    Setup         │                                                  │
│    First test    │   Prose with claim markers, code excerpts,       │
│    Dev loop      │   command blocks, tables.                        │
│    Checkpoint B  │                                                  │
│                  │                                                  │
│ ...              │   ┌──────────────────────┬──────────────────┐    │
│                  │   │ ← Prev               │  Next: Where ... │    │
│ ▓▓▓▓▓░░░░  38%   │   └──────────────────────┴──────────────────┘    │
└──────────────────┴──────────────────────────────────────────────────┘
```

- **Left rail** — course outline grouped by track, tick per completed stop, overall progress bar. Collapses to a top drawer below 900 px.
- **Top bar** — repo name, commit SHA, generation date, verification badge (opens the audit panel), projector toggle, theme toggle, reset progress.
- **Main column** — one stop at a time. Prose capped at 72 ch; code, tables, and the graph break out full width.
- **Footer nav** — Prev / Next with the next stop's title.

**Navigation:** sidebar click, Prev/Next, `←`/`→` keys, and URL hash (`#stop-4`) so links are shareable and reload lands you back in place.

**State** (localStorage, keyed `trailhead:<repo>:<commit>`): current stop, completed stops, checkpoint answers and scores, expanded/collapsed blocks, theme, projector mode. Reset button clears it. A new commit gets a fresh key — progress does not silently carry across regenerations.

---

## 3. Course structure

13 stops in 5 tracks. Sequence is fixed; content is generated. `P` = build priority (1 = must ship, 2 = if time, 3 = stretch).

### Track 1 — Orient (~15 min)

| # | Stop | Content | P |
|---|---|---|---|
| 0 | Cover | Repo name, one-paragraph what-it-does, generation stamp, verification badge, prerequisites, time estimate, Start button | 1 |
| 1 | Five sentences | What it does · who uses it · what it produces · what it depends on · what it is **not**. Each sentence is one anchored claim | 1 |
| 2 | The map | Interactive module graph, full width. Click a node → drawer with narration, top files by churn, one excerpt | 1 |
| 3 | Where the code lives | Sortable table: path, purpose (anchored), files, LOC, churn rank, recent committers | 1 |
| 4 | Checkpoint A | 3 questions from `survey.json` | 2 |

### Track 2 — Get it running (~20 min)

| # | Stop | Content | P |
|---|---|---|---|
| 5 | Prerequisites and setup | Each step a command block: command, exit code, real captured output, duration. Failures shown, not hidden | 1 |
| 6 | Your first green test | The single command that proves the env works, with real output and real wall-clock time | 1 |
| 7 | The dev loop | edit → test → lint → commit, using this repo's actual commands. Plus the 3 commands you will run most, by git history | 2 |
| 8 | Checkpoint B | "You hit error X — which command next?" Derived from failures captured during generation | 2 |

### Track 3 — Follow one request end-to-end (~25 min)

| # | Stop | Content | P |
|---|---|---|---|
| 9 | The trace | Vertical stepper, entry point → output. Each hop: `file:line`, excerpt with focus lines highlighted, one-sentence narration, pointer to next hop | 1 |
| 10 | The data | Key types/schemas that flow through: where defined, where validated, where persisted | 2 |
| 11 | Checkpoint C | Put 5 hops in call order. Graded against the real trace | 2 |

### Track 4 — Change something (~20 min)

| # | Stop | Content | P |
|---|---|---|---|
| 12 | Your first change | One small real task: what to edit, how to test, how to know you're done. Manual checklist, not auto-graded | 3 |
| 13 | Conventions and gotchas | House style, naming, traps. **All content here marked `inferred`** — this is the low-verifiability material, quarantined in one clearly labelled stop | 2 |

### Track 5 — Close (~10 min)

| # | Stop | Content | P |
|---|---|---|---|
| 14 | Audit | Full claim ledger, verification report, regeneration command | 1 |
| 15 | Who to ask | Recent committers per module, labelled "most recent committers" — not "owners" | 2 |

---

## 4. Components

### 4.1 Claim — the atomic unit

Every factual sentence is a claim. This component is what separates the artifact from generated filler.

```json
{
  "id": "c-084",
  "text": "Settlement dates are rolled forward on the holiday calendar before pricing.",
  "anchor": { "file": "src/pricing/schedule.py", "start": 112, "end": 131,
              "excerpt_sha256": "9f2c…" },
  "status": "verified"
}
```

| Status | Renders as | Behaviour |
|---|---|---|
| `verified` | Normal text + small superscript marker | Click marker → excerpt expands inline below the paragraph |
| `inferred` | Dotted amber underline | Tooltip and inline label: "inferred — not verified against code" |
| `dropped` | **Never rendered** | Appears only in the audit ledger with the reason |

Rules:
- No sentence of fact without an anchor. Prose that cannot be anchored is either cut or downgraded to `inferred`.
- Anchors are verified by re-reading the file and comparing `excerpt_sha256`. Mismatch → `dropped`.
- The count of dropped claims is displayed in the top bar. Hiding it defeats the point.

### 4.2 CodeExcerpt

```
src/pricing/schedule.py : 112–131                              [copy]
─────────────────────────────────────────────────────────────────────
 112   def roll_forward(d: date, cal: Calendar) -> date:
 113       while not cal.is_business_day(d):
▸114           d += timedelta(days=1)          ← focus line
 115       return d
 …
```

- Line numbers match the real file; never restart at 1.
- Focus lines highlighted with a left marker plus background — not colour alone.
- Max 24 lines visible, then scrolls **inside its own box**. Horizontal overflow contained; the page body never scrolls sideways.
- Elision shown as `…` with the number of omitted lines.
- Copy button copies the raw excerpt, no line numbers.

### 4.3 CommandBlock

```
$ make test                                        exit 0 · 41.2 s
─────────────────────────────────────────────────────────────────────
▸ output (238 lines)                                    [expand]
```

- Exit-code badge: green `exit 0`, red `exit N`.
- Real captured stdout/stderr, collapsed by default, expanded for print.
- Footer note: "captured during generation on 2026-07-30, ubuntu-22.04, python 3.11".
- Failure renders a red **known-broken** banner with the actual error, plus a cause hypothesis explicitly tagged `inferred`.

### 4.4 MapGraph

- Inline SVG. Nodes = modules, area ∝ LOC. Edges = imports, thickness ∝ import count. Layered layout, computed at generation time — no layout engine in the page.
- Hover: highlight node + neighbours, dim the rest.
- Click: right drawer — module name, narration, top 5 files by churn, one excerpt, list of dependencies in and out.
- Zoom and pan; `0` resets.
- **Density cap:** more than 40 modules → collapse to top-level packages with per-node expand. Prevents the hairball on a large repo.
- **Text fallback** directly beneath: nested list of modules and dependencies. Serves screen readers, and serves you when the graph is too dense to read.

### 4.5 Checkpoint

```json
{
  "id": "cp-a2",
  "kind": "single",
  "prompt": "Which directory owns holiday-calendar logic?",
  "options": ["src/pricing/", "src/calendars/", "src/io/", "tests/fixtures/"],
  "answer": 1,
  "provenance": "survey.json → imports → calendars.* referenced by 14 modules",
  "explanation": "src/calendars/ defines Calendar; src/pricing/ only consumes it."
}
```

- Kinds: `single`, `multi`, `order` (drag or numbered select), `file-pick` (choose from a real file list).
- Answer keys come from `survey.json` — static analysis, not model opinion. `provenance` is displayed after answering.
- Feedback is immediate. Explanation shown whether right or wrong.
- No free-text questions. There is no model in the page to grade them.
- Scores are local, visible only to the learner, and resettable. Not a test.

### 4.6 AuditPanel

Opened from the verification badge; also stop 14.

- Summary line: claims made, verified, dropped, inferred; commands run, passed, failed; generation duration; tool version; commit SHA.
- Sortable, filterable table: claim id · text · file · lines · status · reason if dropped.
- Regeneration command, copy-paste ready.

### 4.7 Callout

Three levels only. `info` (grey), `inferred` (amber), `broken` (red). No other decorative boxes.

---

## 5. Render input contract

Render consumes `verified.json`. Nothing else. Shape:

```json
{
  "repo": { "name": "payments-core", "commit": "a3f9c21", "generated_at": "2026-07-30T14:02:11Z" },
  "report": { "claims": 142, "verified": 134, "dropped": 8, "inferred": 19,
              "commands": 23, "failed": 2, "tool_version": "0.3.1" },
  "map": { "nodes": [], "edges": [] },
  "tracks": [
    { "title": "Orient",
      "stops": [
        { "id": "stop-1", "title": "Five sentences", "minutes": 4,
          "blocks": [ { "type": "prose", "claims": [] } ] }
      ] }
  ]
}
```

Block types — the complete set. Render implements exactly these and nothing more:

| Type | Fields |
|---|---|
| `prose` | `claims[]` |
| `excerpt` | `anchor`, `focus_lines[]`, `caption` |
| `command` | `cmd`, `cwd`, `exit_code`, `stdout`, `stderr`, `duration_ms`, `env_note` |
| `graph` | `ref` (points at `map`) |
| `table` | `columns[]`, `rows[]` (cells may be claims), `caption`, `sortable` |
| `trace` | `steps[]` = `{ anchor, focus_lines, claim, next_hint }` |
| `checkpoint` | see 4.5 |
| `callout` | `level`, `claims[]` or `text` |

---

## 6. Degraded generation

Never silently omit a stop. A missing input renders a labelled placeholder.

| Situation | Page shows |
|---|---|
| No entry point found | Stop 9: "No traceable entry point found in this repo. Trace unavailable." |
| No test command found | Stop 6: "No test command detected. Candidates considered: …" |
| Setup commands all failed | Stop 5 renders every failure in full, banner: "This repo did not build during generation." |
| Fewer than 3 modules | Map replaced by the text fallback list |
| More than 40 % of claims dropped | Top-bar badge turns amber: "low confidence — 47 % of claims dropped" |

Honest degradation is a feature. A blank stop reads as a bug; a labelled gap reads as a tool that knows what it does not know.

---

## 7. Visual and interaction rules

**Type** — system stack (`-apple-system, Segoe UI, Roboto, sans-serif`); monospace stack for code. Body 16 px / line-height 1.6. Prose column 72 ch.

**Colour** — light and dark, driven by `prefers-color-scheme`, overridden by an explicit toggle stamping `data-theme` on `:root`. Semantic set: verified green, inferred amber, broken red, chrome grey. Everything ≥ 4.5:1. No meaning carried by colour alone — always a paired icon or label.

**Projector mode** — one toggle: base font to 20 px, sidebar hidden, code excerpts to 12 visible lines. Two hours of build time, and it is what the pitch runs on.

**Print** (`@media print`) — linearise all stops, expand every collapsed block, drop nav and toggles, print URLs for anchors. A new joiner can PDF the whole course.

**Motion** — transitions ≤ 150 ms; all disabled under `prefers-reduced-motion`.

**Keyboard** — every control reachable and operable. Visible focus ring. `←`/`→` stops, `/` search, `0` reset graph zoom, `Esc` close drawer.

**Responsive** — sidebar → top drawer below 900 px. Tables, code, and graph each scroll inside their own `overflow-x: auto` container. Body never scrolls horizontally at any width.

---

## 8. Acceptance tests

Run against a generated file. All deterministic; no model needed.

| # | Test |
|---|---|
| 1 | Output is a single file; zero external URLs in `src`/`href`/`fetch`/`import` |
| 2 | Opens from `file://` with the network disabled; graph, checkpoints, and toggles all work |
| 3 | Every rendered claim marker resolves to an embedded excerpt; every excerpt's `sha256` matches the source file at the recorded commit |
| 4 | No claim with `status: dropped` appears anywhere outside the audit ledger |
| 5 | Every `command` block shows a real exit code and non-placeholder output |
| 6 | Checkpoint answer keys match `survey.json` — recompute independently and compare |
| 7 | Progress survives reload; a changed commit SHA starts fresh state |
| 8 | Body has no horizontal scroll at 1440 / 1024 / 768 / 375 px |
| 9 | Full course completable by keyboard only |
| 10 | Light and dark both pass 4.5:1 on every text/background pair |
| 11 | Print output contains every stop with all blocks expanded |
| 12 | File size < 5 MB on a 4 000-file repo |

---

## 9. Build order for 10 hours

| Hours | Ship |
|---|---|
| 0–1 | `verified.json` contract fixed; hand-write one fixture by hand so render can be built against it immediately |
| 1–3 | Render: shell, sidebar, stops, `prose` + `excerpt` + `command` blocks |
| 3–4 | Claim markers and inline excerpt expansion — the trust mechanic |
| 4–5 | MapGraph with drawer and text fallback |
| 5–6 | Trace stepper; audit panel |
| 6–7 | Checkpoints A and C; localStorage progress |
| 7–8 | Projector mode, theme, print; acceptance tests 1–6 |
| 8–9 | Generate on two unfamiliar repos; fix what breaks |
| 9–10 | Rehearse |

**Cut list, in order, if behind:** stop 12 → stop 15 → stop 10 → checkpoint B → stop 7.

**Never cut:** claim markers, the audit panel, the dropped-claim count. Remove those and it is another generic codebase explainer.
