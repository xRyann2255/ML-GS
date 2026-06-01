---
name: verify-diagram
description: Verify a TikZ diagram by cropping it to high resolution, running deterministic geometric checks plus independent blind reviewers (legibility + learning-clarity), then fixing and re-verifying in a loop until both gates pass. Use after creating or modifying any TikZ diagram.
---

# Verify Diagram (engine)

Inspect ONE diagram at its own resolution, judge it with a deterministic pass and two independent
reviewers that never see the TikZ source, fix defects, and loop until both gates pass — or stop and
report. This is the per-diagram engine; the `verify-all-diagrams` workflow runs it in bulk.

## When to Use
- After creating or modifying any TikZ diagram in a LaTeX guide.
- When a user reports a visual problem with a diagram.
- Called by `write-chapter` after any diagram is written.

## Inputs the caller should provide
- **guide** (e.g. `guides/vol-project-ref`) and the **figure's caption/label substring** (unique text on the figure's page).
- **concept**: one line — what the diagram is meant to teach.
- **relationships** (optional): the arrows/dependencies the diagram should encode (enables the correctness lens).

## The Loop (repeat until the gate passes or the cap is hit)

### Step 1 — Compile (whole-guide; reliable)
From the guide root, compile so the figure's page exists:
```bash
cd guides/<guide> && pdflatex -interaction=nonstopmode -halt-on-error main.tex
```
If references are stale, run `bibtex main` then `pdflatex` twice more. If compilation errors, fix the
LaTeX error first — do not inspect a stale PDF. (An optional faster path exists; see "Standalone fast
path" below. If anything about it fails, fall back to this whole-guide compile.)

### Step 2 — Inspect (deterministic, crops to the figure)
```bash
PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/diag_inspect.py \
  --pdf guides/<guide>/main.pdf --locate "<unique caption substring>" \
  --out guides/<guide>/.diagverify
```
Read `guides/<guide>/.diagverify/inspection.json`. It contains the cropped image `crop.png`, a defect
list (`overlap`, `node_text_spill`, `tiny_font`, `node_overlap`), and metrics. If `located` is false,
the caption substring is wrong — fix it and retry. **View `crop.png` with the Read tool** — this is the
figure at full resolution, not a shrunken page.

### Step 3 — Reviewers (independent, blind, parallel)
Dispatch BOTH reviewers as subagents using the Agent tool, **in the same message** so they run in
parallel. Give each ONLY: the path to `crop.png`, the caption, and the one-line concept — **never the
TikZ source**. Each must return strict JSON.

**Reviewer 1 — Legibility & layout.** Prompt:
> You are inspecting a single diagram image for visual defects a reader would hit. You can see only the
> image at `<crop.png>`. Caption: "<caption>". Concept: "<concept>". Report ONLY what you can see:
> overlapping or cramped text; labels too close to tell apart; arrows that are visually
> indistinguishable or ambiguous about which boxes they connect; boxes that touch or overlap; clipped
> content; severe imbalance or wasted whitespace. Do NOT comment on pedagogy. Return JSON:
> `{"defects":[{"type":str,"severity":"blocking"|"minor","where":str,"fix":str}],"summary":str}`.

**Reviewer 2 — Learning-clarity (first-time learner).** Prompt:
> You are seeing this diagram for the very first time and know only the caption. Image: `<crop.png>`.
> Caption: "<caption>". Concept it should teach: "<concept>". Answer as a first-time learner: what does
> your eye land on first? Can you follow the intended flow/relationships? What is confusing, unlabeled,
> or undefined? What ONE change would most improve how intuitively this teaches the concept? Mark a
> defect "blocking" only if a first-time learner would be actively misled or unable to follow. Return
> JSON: `{"clarity_score":1-5,"defects":[{"issue":str,"severity":"blocking"|"minor","suggestion":str}],"summary":str}`.

**Reviewer 3 — Correctness vs spec (ONLY if `relationships` was provided).** Prompt:
> The diagram should encode these relationships: "<relationships>". Looking only at `<crop.png>`, flag
> any arrow or label that contradicts them. Return JSON:
> `{"defects":[{"issue":str,"severity":"blocking"|"minor","where":str}]}`.

### Step 4 — Synthesize
Merge: deterministic defects (Step 2) + reviewer defects (Step 3). Deduplicate by region/description.
Sort blocking-first.

### Step 5 — Gate
The diagram **passes** when ALL hold:
- zero `blocking` deterministic defects (treat `tiny_font<5pt`, `overlap`, `node_overlap` as blocking),
- zero `blocking` legibility defects,
- learning-clarity `clarity_score >= 4` AND zero `blocking` clarity defects,
- (if run) zero correctness defects.

`warn`/`minor` defects are recorded but do NOT block. If the gate passes → **done**: report the clean
result, keep `crop.png`, delete the rest of `.diagverify`, and stop.

### Step 6 — Fix (you, the orchestrator — only you edit TikZ)
If the gate fails, edit the figure's TikZ to resolve the **blocking** defects (and cheap minors while
you're there), using the fixes below. Then return to Step 1. Reviewers never edit — they only judge.

### Step 7 — Cap
Do at most **5** iterations. If still failing, STOP and emit a `needs-human` report: the remaining
defects + the path to the latest `crop.png`. Do NOT report "clean". A caller (e.g. write-chapter) must
surface a `needs-human` result rather than proceeding.

## Standalone fast path (optional)
If `.claude/skills/verify-diagram/standalone_wrapper.py` exists (Phase E), you MAY compile just the one
figure for faster iteration:
```bash
PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/standalone_wrapper.py \
  --guide guides/<guide> --label "<fig:label>" --out /tmp/diagstandalone
```
then inspect that PDF with `--locate ""`. If it errors or the figure is missing/looks different from
the whole-guide render, **discard it and use the whole-guide path**.

## Common TikZ Fixes
- **Overlapping labels / boxes:** increase `node distance`, add `xshift`/`yshift`, or set `text width`
  so a long label wraps instead of overflowing.
- **Label overflows its box (`node_text_spill`):** add `text width=<w>, align=center`, raise
  `minimum width`, or shorten the label.
- **Tiny font:** raise the node `font=` (avoid `\tiny`/`\scriptsize` for primary labels); if the figure
  is `\resizebox`-shrunk, enlarge the natural layout so the shrink is gentler.
- **Arrows through nodes / ambiguous arrows:** route with intermediate coordinates
  (`(a.south) -- ++(0,-0.5) -| (c.north)`); separate shared-axis arrows with offset anchors
  (`.north east` vs `.north`).
- **Fan-out:** use a bus (`\draw (src.south) -- ++(0,-1) coordinate (bus);` then branch) instead of
  many overlapping paths.

## Cleanup
On a clean pass, delete the temp dir except the final crop if a report references it:
```bash
rm -rf guides/<guide>/.diagverify
```

## Dependencies
- `py` with `PyMuPDF` (`pip install PyMuPDF`), `pdflatex` (MiKTeX), and the Read tool's image rendering.
