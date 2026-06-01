# Verify-Diagram v2 — Design

**Date:** 2026-06-01
**Status:** Approved (design); ready for implementation plan
**Targets:**
- `.claude/skills/verify-diagram/SKILL.md` (rewrite)
- `.claude/skills/verify-diagram/diag_inspect.py` (new — deterministic core)
- `.claude/skills/verify-diagram/test/` (new — fixtures + runner for the core)
- `.claude/workflows/verify-all-diagrams.js` (new — batch audit & fix)
- `.claude/skills/write-chapter/SKILL.md` (minor — pass concept/deps; surface "needs-human")

## Problem

The current `verify-diagram` skill compiles the *whole guide*, finds the figure's page by a
caption text-search, renders that **entire page** to one PNG at 250 DPI, and has the same agent
that drew the diagram read that PNG against a checklist, looping until it judges the diagram clean.
Four things make it miss exactly the defects it was built to catch:

1. **No crop / no zoom.** It inspects a full page, so a typical figure is ~1/6 of the frame and box
   labels render tiny. Overlapping, cramped, or clipped text is effectively sub-pixel — invisible to
   the reviewing agent. (The user assumed it already cropped to the figure; it never has.)
2. **Eyeball-only detection.** Even at the right scale, "do any labels overlap?" is judged by visual
   impression. There is no deterministic check, so subtle overlaps slip through inconsistently.
3. **Self-grading.** The agent that wrote the TikZ also grades it, against a mechanical checklist
   (arrows, routing). Confirmation bias plus a low-res glance means it declares "clean" early.
4. **No pedagogy lens.** Nothing asks whether the diagram actually *teaches* the concept — only
   whether arrows avoid boxes. The user wants diagrams that are as intuitive to learn from as possible.

The loop-until-clean intent (Step 5 of the current skill) is sound; the **exit condition is
untrustworthy**, which is the root cause of all four symptoms.

## Goal

Rebuild verification around one reusable **engine** with a trustworthy exit gate, and expose it two
ways:

- A diagram is inspected at **its own resolution** — auto-cropped to the figure bbox and rendered at
  ~300 DPI (tiled when dense), so fine text problems are visible to both a human and the reviewer.
- Defects are caught by a **deterministic Python pass** (overlap / clipping / font-size — things low
  resolution cannot hide) **and** by **independent blind reviewers** that never see the TikZ source.
- One reviewer judges **legibility & layout**; another judges **learning-clarity** as a first-time
  learner, and proposes concrete improvements toward intuitiveness.
- The fix loop **exits only when both gates pass**, with an iteration cap that **stops and reports
  remaining defects rather than silently passing**.
- The same engine runs as a **batch workflow** over every diagram in all three guides, fixing those
  that fail and producing a per-diagram report + a contact sheet, leaving edits for the user to review.

**Non-goals:** auto-committing fixes or downloads; redrawing diagrams from scratch when a targeted fix
suffices; a general image-diff/regression harness; changing the guides' visual style guide; supporting
non-TikZ figures (raster images, externally-included PDFs).

## Architecture

```
                         ┌──────────────────────────────────────┐
   write-chapter ──────▶ │           THE ENGINE                 │
   (one diagram)         │  per diagram, loops to a gate        │ ◀────── verify-all-diagrams
   manual invoke ──────▶ │                                      │         (workflow, fans out)
                         └──────────────────────────────────────┘
                                          │ uses
                                          ▼
                         diag_inspect.py  (compile-adjacent render + deterministic checks; no LLM)
```

The **skill** is the engine for one diagram. The **workflow** discovers all diagrams and runs the
engine on each, in parallel. Both call the **shared Python core** for the deterministic, testable work.

## Component A — `diag_inspect.py` (deterministic core)

Pure PyMuPDF, no LLM. Given a compiled PDF (or a figure to compile) and a figure identifier, it
locates the figure, renders crops, runs geometric checks, and emits `inspection.json`.

### Inputs
- `--pdf <path>` the compiled PDF, **or** `--standalone <wrapper.tex>` to compile first.
- `--locate <label|caption-substring>` how to find the figure's page.
- `--out <dir>` where to write crops + `inspection.json`.
- `--min-font 6` `--overlap-frac 0.20` thresholds (overridable).

### Figure location & bbox
- Find the page whose text contains the label/caption substring.
- **Bounding box:** union of vector drawing rects (`page.get_drawings()`, `rect.width/height > 1`),
  expanded to include any text span intersecting a ~30pt margin around that union, then padded 8pt and
  clamped to the page. (Standalone mode: the cropped page *is* the figure, so bbox = page rect.)

### Crops
- `crop.png` — the figure bbox at **300 DPI**.
- **Tiling:** if bbox area > a threshold or span-density is high, also emit `tile_00..11.png` (2×2 with
  slight overlap) so dense regions reach the reviewers at full resolution.

### Deterministic checks
For every text span in the figure bbox (`page.get_text("dict")` → bbox, text, size, font):

| Check | Rule | Severity |
|---|---|---|
| `overlap` | Two spans from **different words/lines** whose boxes intersect by `> overlap-frac` (default 20%) of the smaller box's area. Excludes sub/superscripts, accents, and sub-1pt kerning touches. | blocking |
| `clip` | A span extending beyond the figure bbox (text spilling out of the figure). | blocking |
| `node_text_spill` | A span wider/taller than the filled node rect it sits in (`get_drawings()` fills), i.e. label overflowing its box. Heuristic. | warn |
| `tiny_font` | `span["size"] < min-font` (default 6pt). `< 5pt` escalates. | warn / blocking |
| `node_overlap` | Two filled node rects overlapping past tolerance. | blocking |
| `line_crosses_label` *(v2, optional)* | A stroked path passing through a label box that is not its own connector. | minor |

**False-positive discipline is a first-class requirement:** legitimate tight typography (subscripts,
stacked fractions, math accents, small-caps kerning) must **not** flag. The `clean` and `subscript`
fixtures (see TDD) are the guardrail — over-flagging would prevent the loop from ever terminating.

### Output — `inspection.json`
```json
{
  "located": true,
  "page": 49,
  "bbox": [48.7, 332.8, 546.6, 584.9],
  "crop": "crop.png",
  "tiles": ["tile_00.png", "..."],
  "metrics": { "n_spans": 73, "min_font_pt": 7.0, "crop_px": [2076, 1052], "density": 0.0021 },
  "defects": [
    { "type": "overlap", "severity": "blocking", "bbox": [x0,y0,x1,y1],
      "detail": "spans 'Model_Registry' and 'CV Strategies' overlap 34%",
      "where_human": "upper-right registry boxes" }
  ]
}
```
- If the figure can't be located: `{"located": false, "error": "..."}` and a non-zero exit — the
  engine must **not** proceed to inspection on a stale/wrong page.

### Robustness
- Never crash on a locate miss or an empty drawings list — emit structured error.
- Windows: callers invoke with `PYTHONIOENCODING=utf-8`.

## Component B — Reviewers + exit gate

Independent subagents, dispatched **in parallel**, each given **only** the `crop.png` (+ tiles), the
figure **caption**, and a one-line **concept** statement (what the diagram should teach). They **never
see the TikZ source**, so they cannot self-confirm the author's intent.

### Lenses
- **Legibility & layout.** Catches what geometry can't: two arrows visually indistinguishable,
  ambiguity about which node an arrow connects, crowding, imbalance, clipped content. Returns
  `{ defects: [{ type, severity: blocking|minor, where, fix }], summary }`.
- **Learning-clarity (first-time learner).** Sees the diagram cold. Reports: what the eye lands on
  first, whether the intended flow/relationships are followable, what is confusing / unlabeled /
  undefined, and the **single change that would most improve how intuitively it teaches the concept**.
  Returns `{ clarity_score: 1-5, defects: [{ issue, severity, suggestion }], summary }`.
- **Correctness-vs-spec** *(only when intended relationships are known, e.g. inside write-chapter).*
  Given the relationships the diagram should encode, flags any arrow/label that contradicts them.
  Returns `{ defects: [...] }`.

Structured output enforced by schema; a malformed return is re-requested.

### The gate (loop exits only when ALL hold)
- Zero **blocking** deterministic defects.
- Zero **blocking** legibility defects.
- Learning-clarity `clarity_score ≥ 4` **and** zero blocking clarity defects.
- (When run) zero correctness-vs-spec defects.

**Minor** defects are logged in the report but do **not** block the exit, to prevent infinite
polishing. The orchestrator may opportunistically fix cheap minors while it is editing anyway.

### Iteration cap
Default **5**. On reaching the cap without passing, the engine **stops** and emits a `needs-human`
report containing the remaining defects and the final `crop.png`. It never reports "clean" when the
gate did not pass. `write-chapter` must surface a `needs-human` result rather than proceeding.

## Component C — The engine loop (orchestration)

The agent running the skill performs, per diagram:

1. **Compile.** Build a **standalone wrapper** that `\input`s the guide's `preamble.tex` plus only the
   target figure, compiled with the `standalone` class (`preview`/`crop` for a tight page). If that
   fails (missing chapter-local macro, counter, or cross-reference) or the figure can't be located,
   **fall back to a whole-guide compile** automatically.
2. **Inspect.** Run `diag_inspect.py` → crop(s) + deterministic defects.
3. **Review.** Dispatch the reviewer subagents (B) on the crop(s) in parallel.
4. **Synthesize.** Merge deterministic + reviewer defects, dedupe by region, sort blocking-first.
5. **Gate.** If it passes → **done**: report clean, keep the final crop, clean up temp PNGs.
6. **Fix.** Otherwise the **orchestrator (and only it)** edits the TikZ to resolve the top defects,
   then returns to step 1. Reviewers stay read-only, preserving independence and avoiding edit races.
7. **Cap.** At 5 iterations without passing → stop with the `needs-human` report.

Common TikZ fixes (routing around nodes, bus fan-out, separating shared-axis arrows, increasing node
spacing, shrinking/relabelling overlong labels) carry over from the current skill's "Common Fixes"
section, retained and extended with spacing/label-length remedies.

## Component D — `verify-all-diagrams.js` (batch workflow)

`meta.phases`: Discover → Verify-and-fix (fan-out) → Consolidate.

- **Discover.** A script enumerates every `tikzpicture` figure across the three guides into a work-list
  `{ guide, file, label, caption, line_start, line_end, concept? }`. Figures inside a `figure` float
  take their `\label`/`\caption`; bare inline `tikzpicture` blocks get a synthetic id + line range.
- **Group by file.** Diagrams in the **same file run sequentially** (one writer per file); **different
  files run in parallel**. Each file-group runs in its own **git worktree** (`isolation: 'worktree'`)
  so parallel edits cannot collide. (Fallback if worktrees are problematic: parallel agents editing
  **disjoint** files in a single tree, which is also collision-free since groups touch different files.)
- **Verify-and-fix.** Each diagram runs through the engine (Component C). The workflow's per-diagram
  agent owns the fix edits; the reviewer lenses are sub-dispatched read-only judges. The batch may use a
  **2-vote learner panel** for the clarity lens (variance reduction) where the inline skill uses one.
- **Consolidate.** Merge the per-worktree edits back (disjoint files → clean merge), **recompile each
  whole guide** to confirm nothing broke, and emit:
  - a **batch summary** markdown: per diagram `already_clean | fixed | needs_human`, blocking-defect
    counts before→after, and links to before/after crops;
  - a **contact-sheet** PNG (grid of all final crops) for a one-glance consistency review.
- **No auto-commit.** Edits are left on a branch / in the working tree; the summary is surfaced for the
  user to review and commit. One diagram failing drops to a `needs_human` entry and never aborts the batch.

## Component E — write-chapter integration (minor)

- When write-chapter invokes the engine, it passes the figure's **concept** (one line) and intended
  **relationships** so the correctness-vs-spec lens can run.
- write-chapter treats a `needs-human` engine result as a blocker to surface, not a pass.
- No other change; the existing "invoke verify-diagram after any TikZ diagram" instruction stands.

## TDD plan (the Python core is the testable heart)

Fixtures under `.claude/skills/verify-diagram/test/fixtures/`, each a tiny one-figure `.tex` compiling
to a single-figure PDF:

| Fixture | Construction | Expected |
|---|---|---|
| `overlap.tex` | Two nodes placed to force label-box overlap | ≥1 `overlap` (blocking) |
| `clip.tex` | A label spilling past the figure bbox | `clip` (blocking) |
| `tiny.tex` | A `\tiny` (~4pt) label | `tiny_font` (blocking, since <5pt) |
| `clean.tex` | A well-spaced, legible diagram | **zero defects** (false-positive guard) |
| `subscript.tex` | Legitimate subscripts / `\hat` accents / stacked frac | **zero defects** (tolerance guard) |

- Red → green → commit **per check**; tolerances tuned against `clean` and `subscript`.
- Reviewer/loop layer (LLM-driven) gets a **smoke test**: on a known-bad real diagram, blocking-defect
  count must reach zero and the loop must terminate within the cap.

## Constraints / notes

- PyMuPDF (`fitz`) 1.27.x is installed; `pdflatex` (MiKTeX) is available. Standalone compile needs the
  `standalone` + `preview` packages (in MiKTeX).
- Run `py` with `PYTHONIOENCODING=utf-8` on Windows to avoid encoding errors.
- Standalone-first keeps the loop fast (no whole-guide recompile per iteration) and gives an exact crop;
  whole-guide fallback preserves correctness when a figure depends on chapter-local context.
- Workflow scripts are plain JS; `Date.now()`/`Math.random()`/argless `new Date()` are unavailable —
  derive any timestamp from `args`/slug.
- Respect repo norm: **never auto-commit**; leave edits and new PDFs staged for review.
- Temp PNGs are cleaned up on a clean pass; the final crop is retained only where a report references it.

## Acceptance

- On the existing Fig 17.1 (`vol-project-ref`), the engine crops to the figure and renders it at ~300
  DPI (crop fills the frame), not the whole page.
- `diag_inspect.py` flags every defect fixture (`overlap`/`clip`/`tiny`) and returns **zero** on both
  `clean` and `subscript`.
- A diagram with a real overlapping-label defect is **fixed** by the loop, and the loop **terminates**;
  a deliberately unfixable case **stops at the cap with a `needs-human` report**, never a false "clean".
- The reviewers receive only the crop + caption + concept (no TikZ), verified by their dispatch inputs.
- `verify-all-diagrams` produces a per-diagram summary + a contact sheet across all three guides, edits
  isolated per file with no cross-file collisions, recompiles each guide clean, and commits nothing.
