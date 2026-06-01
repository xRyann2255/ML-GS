# Verify-Diagram v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the `verify-diagram` skill around a deterministic Python core (crop-to-figure + geometric defect detection) plus independent blind reviewers and a trustworthy fix-loop gate, and expose the same engine as a batch workflow over every diagram in all guides.

**Architecture:** A pure, unit-tested Python module `diag_inspect.py` does the deterministic work (locate figure, crop at high DPI, flag overlap/spill/tiny-font/node-overlap, emit `inspection.json`). The `verify-diagram` SKILL.md orchestrates a loop: compile → inspect → dispatch blind reviewer subagents (legibility + learning-clarity) → synthesize defects → fix TikZ → repeat until both gates pass or a cap is hit. A new `verify-all-diagrams.js` workflow discovers all figures and fans the engine out, grouped by file, in git worktrees.

> **Deviation from the spec (flagged for the user):** the spec said *standalone-first* compile. In practice the guide preamble assumes a chaptered `report` class (`\chaptermark`, `\thechapter`) and figures are wrapped in `\resizebox{\textwidth}{!}{...}` with inline TikZ styles, which makes true standalone compilation fragile. Cropping from the **whole-guide PDF already works** (proven in the design demo). So this plan makes **whole-guide compile + crop the reliable default**, and implements standalone compilation as an **optional speed optimization with automatic fallback** (Phase E). The engine is correct and complete without Phase E.

**Tech Stack:** Python 3 + PyMuPDF (`fitz` 1.27.x), pytest 9; `pdflatex` (MiKTeX); Node.js built-in test runner (`node --test`) for workflow helpers; the Workflow tool's JS DSL (`agent`/`pipeline`/`parallel`/`phase`/`log`).

---

## File Structure

- Create `.claude/skills/verify-diagram/diag_inspect.py` — deterministic core (pure functions + thin I/O/CLI).
- Create `.claude/skills/verify-diagram/test/test_diag_inspect.py` — pure-function unit tests (no LaTeX).
- Create `.claude/skills/verify-diagram/test/test_fixtures.py` — integration tests (compile fixtures, assert defects).
- Create `.claude/skills/verify-diagram/test/fixtures/{overlap,spill,tiny,clean,subscript}.tex` — TeX fixtures.
- Create `.claude/skills/verify-diagram/contact_sheet.py` — grid PNG assembler for the batch report.
- Create `.claude/skills/verify-diagram/test/test_contact_sheet.py` — grid-layout unit tests.
- Rewrite `.claude/skills/verify-diagram/SKILL.md` — the engine procedure + reviewer prompts/schemas + gate.
- Create `.claude/workflows/verify-all-diagrams.js` — batch workflow.
- Create `.claude/workflows/__tests__/verify-all-diagrams-helpers.test.mjs` — pure discovery/group helpers (TDD source of truth, mirrored into the workflow).
- Modify `.claude/skills/write-chapter/SKILL.md` — pass concept/relationships, surface `needs-human`.

Convention notes:
- All `py` invocations on Windows are prefixed `PYTHONIOENCODING=utf-8` to avoid encoding errors.
- Every git commit ends with the trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Defects are dicts: `{"type","severity","bbox":[x0,y0,x1,y1],"detail"}` with `severity ∈ {"blocking","warn","minor"}`.
- Spans are dicts: `{"bbox":[x0,y0,x1,y1],"text":str,"size":float,"font":str,"line_id":int}`.

---

# Phase A — Deterministic core (`diag_inspect.py`)

### Task A1: Geometry helpers

**Files:**
- Create: `.claude/skills/verify-diagram/diag_inspect.py`
- Test: `.claude/skills/verify-diagram/test/test_diag_inspect.py`

- [ ] **Step 1: Write the failing test**

```python
# .claude/skills/verify-diagram/test/test_diag_inspect.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import diag_inspect as di

def test_rect_area():
    assert di.rect_area([0, 0, 2, 3]) == 6
    assert di.rect_area([5, 5, 5, 9]) == 0          # zero width

def test_intersection_area():
    assert di.rect_intersection_area([0, 0, 2, 2], [1, 1, 3, 3]) == 1
    assert di.rect_intersection_area([0, 0, 1, 1], [2, 2, 3, 3]) == 0  # disjoint

def test_union_rect():
    assert di.union_rect([0, 0, 1, 1], [2, 2, 3, 3]) == [0, 0, 3, 3]

def test_overlap_fraction():
    # boxes [0,0,2,2] (area 4) and [1,0,3,2] (area 4) share [1,0,2,2] area 2 -> 2/4
    assert di.overlap_fraction([0, 0, 2, 2], [1, 0, 3, 2]) == 0.5
    assert di.overlap_fraction([0, 0, 1, 1], [5, 5, 6, 6]) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'diag_inspect'`.

- [ ] **Step 3: Write minimal implementation**

```python
# .claude/skills/verify-diagram/diag_inspect.py
"""Deterministic TikZ-diagram inspector: locate, crop, and flag geometric defects.

Pure functions (no LaTeX, no PDF) are tested in test/test_diag_inspect.py.
I/O wrappers (PyMuPDF) and the CLI are exercised by test/test_fixtures.py.
"""

def rect_area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])

def rect_intersection_area(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)

def union_rect(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]

def overlap_fraction(a, b):
    inter = rect_intersection_area(a, b)
    if inter <= 0:
        return 0.0
    denom = min(rect_area(a), rect_area(b))
    return inter / denom if denom else 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/diag_inspect.py .claude/skills/verify-diagram/test/test_diag_inspect.py
git commit -m "feat(verify-diagram): geometry helpers for diagram inspection

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A2: `find_overlaps`

**Files:**
- Modify: `.claude/skills/verify-diagram/diag_inspect.py`
- Test: `.claude/skills/verify-diagram/test/test_diag_inspect.py`

- [ ] **Step 1: Write the failing test** (append to the test file)

```python
def _span(bbox, text="x", size=9.0, line_id=0):
    return {"bbox": bbox, "text": text, "size": size, "font": "F", "line_id": line_id}

def test_find_overlaps_flags_cross_line_overlap():
    spans = [_span([0, 0, 20, 10], "Model", line_id=1),
             _span([10, 0, 30, 10], "Strat", line_id=2)]   # 50% overlap, different lines
    d = di.find_overlaps(spans, frac=0.20)
    assert len(d) == 1
    assert d[0]["type"] == "overlap" and d[0]["severity"] == "blocking"

def test_find_overlaps_ignores_same_line():
    spans = [_span([0, 0, 20, 10], "a", line_id=5),
             _span([10, 0, 30, 10], "b", line_id=5)]        # same line -> skip
    assert di.find_overlaps(spans, frac=0.20) == []

def test_find_overlaps_ignores_blank_and_below_threshold():
    spans = [_span([0, 0, 20, 10], "  ", line_id=1),         # whitespace
             _span([10, 0, 30, 10], "b", line_id=2)]
    assert di.find_overlaps(spans) == []
    spans = [_span([0, 0, 20, 10], "a", line_id=1),
             _span([19, 0, 39, 10], "b", line_id=2)]         # 1/20 = 5% < 20%
    assert di.find_overlaps(spans, frac=0.20) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k overlaps -v`
Expected: FAIL — `AttributeError: module 'diag_inspect' has no attribute 'find_overlaps'`.

- [ ] **Step 3: Write minimal implementation** (append to `diag_inspect.py`)

```python
def find_overlaps(spans, frac=0.20):
    out = []
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            si, sj = spans[i], spans[j]
            if si.get("line_id") == sj.get("line_id"):
                continue                                   # same line: adjacent / sub-superscripts
            if not si["text"].strip() or not sj["text"].strip():
                continue
            f = overlap_fraction(si["bbox"], sj["bbox"])
            if f > frac:
                out.append({
                    "type": "overlap", "severity": "blocking",
                    "bbox": union_rect(si["bbox"], sj["bbox"]),
                    "detail": "text '%s' overlaps '%s' (%.0f%%)" % (
                        si["text"][:20], sj["text"][:20], f * 100),
                })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k overlaps -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/diag_inspect.py .claude/skills/verify-diagram/test/test_diag_inspect.py
git commit -m "feat(verify-diagram): find_overlaps glyph-box check

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A3: `find_node_text_spill`

**Files:** Modify `diag_inspect.py`; Test `test_diag_inspect.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_node_text_spill_flags_overflow():
    node = [0, 0, 30, 12]
    spans = [_span([-4, 1, 34, 11], "wide_label", line_id=1)]   # center inside, x overflows
    d = di.find_node_text_spill(spans, [node], margin=1.0)
    assert len(d) == 1 and d[0]["type"] == "node_text_spill" and d[0]["severity"] == "warn"

def test_node_text_spill_ok_when_contained():
    node = [0, 0, 30, 12]
    spans = [_span([3, 2, 27, 10], "fits", line_id=1)]
    assert di.find_node_text_spill(spans, [node], margin=1.0) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k spill -v`
Expected: FAIL — no attribute `find_node_text_spill`.

- [ ] **Step 3: Write minimal implementation**

```python
def find_node_text_spill(spans, node_rects, margin=1.0):
    out = []
    for s in spans:
        if not s["text"].strip():
            continue
        cx = (s["bbox"][0] + s["bbox"][2]) / 2
        cy = (s["bbox"][1] + s["bbox"][3]) / 2
        for r in node_rects:
            if r[0] <= cx <= r[2] and r[1] <= cy <= r[3]:        # text centered in this node
                b = s["bbox"]
                if (b[0] < r[0] - margin or b[2] > r[2] + margin or
                        b[1] < r[1] - margin or b[3] > r[3] + margin):
                    out.append({
                        "type": "node_text_spill", "severity": "warn", "bbox": b,
                        "detail": "label '%s' overflows its box" % s["text"][:20]})
                break
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k spill -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/diag_inspect.py .claude/skills/verify-diagram/test/test_diag_inspect.py
git commit -m "feat(verify-diagram): find_node_text_spill check

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A4: `find_tiny`

**Files:** Modify `diag_inspect.py`; Test `test_diag_inspect.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_find_tiny_warns_and_blocks():
    spans = [_span([0, 0, 10, 6], "a", size=5.5, line_id=1),   # <6 -> warn
             _span([0, 0, 10, 5], "b", size=4.0, line_id=2),   # <5 -> blocking
             _span([0, 0, 10, 9], "c", size=9.0, line_id=3)]   # ok
    d = di.find_tiny(spans, min_pt=6.0)
    sev = sorted(x["severity"] for x in d)
    assert sev == ["blocking", "warn"]
    assert all(x["type"] == "tiny_font" for x in d)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k tiny -v`
Expected: FAIL — no attribute `find_tiny`.

- [ ] **Step 3: Write minimal implementation**

```python
def find_tiny(spans, min_pt=6.0):
    out = []
    for s in spans:
        if not s["text"].strip():
            continue
        if s["size"] < min_pt:
            out.append({
                "type": "tiny_font",
                "severity": "blocking" if s["size"] < 5.0 else "warn",
                "bbox": s["bbox"],
                "detail": "label '%s' is %.1fpt" % (s["text"][:20], s["size"])})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k tiny -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/diag_inspect.py .claude/skills/verify-diagram/test/test_diag_inspect.py
git commit -m "feat(verify-diagram): find_tiny font-size check

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A5: `find_node_overlaps`

**Files:** Modify `diag_inspect.py`; Test `test_diag_inspect.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_find_node_overlaps():
    rects = [[0, 0, 20, 20], [10, 10, 30, 30], [100, 100, 110, 110]]
    d = di.find_node_overlaps(rects, frac=0.15)
    assert len(d) == 1 and d[0]["type"] == "node_overlap" and d[0]["severity"] == "blocking"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k node_overlaps -v`
Expected: FAIL — no attribute `find_node_overlaps`.

- [ ] **Step 3: Write minimal implementation**

```python
def find_node_overlaps(rects, frac=0.15):
    out = []
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            f = overlap_fraction(rects[i], rects[j])
            if f > frac:
                out.append({
                    "type": "node_overlap", "severity": "blocking",
                    "bbox": union_rect(rects[i], rects[j]),
                    "detail": "two boxes overlap (%.0f%%)" % (f * 100)})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k node_overlaps -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/diag_inspect.py .claude/skills/verify-diagram/test/test_diag_inspect.py
git commit -m "feat(verify-diagram): find_node_overlaps check

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A6: `figure_bbox`

**Files:** Modify `diag_inspect.py`; Test `test_diag_inspect.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_figure_bbox_unions_drawings_and_nearby_text():
    page = [0, 0, 600, 800]
    draws = [[100, 100, 200, 150], [220, 100, 320, 150]]      # two boxes
    spans = [_span([110, 160, 190, 170], "label", line_id=1), # just below box 1 (within expand)
             _span([10, 10, 40, 20], "header", line_id=2)]    # far away -> excluded
    bb = di.figure_bbox(draws, spans, page, expand=30.0, pad=8.0)
    # union of boxes is [100,100,320,150]; label extends bottom to 170; pad 8
    assert bb[0] == 92 and bb[1] == 92 and bb[2] == 328 and bb[3] == 178

def test_figure_bbox_clamps_to_page():
    page = [0, 0, 50, 50]
    bb = di.figure_bbox([[5, 5, 45, 45]], [], page, expand=30.0, pad=8.0)
    assert bb == [0, 0, 50, 50]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k figure_bbox -v`
Expected: FAIL — no attribute `figure_bbox`.

- [ ] **Step 3: Write minimal implementation**

```python
def figure_bbox(draw_rects, spans, page_rect, expand=30.0, pad=8.0):
    rects = [r for r in draw_rects if (r[2] - r[0]) > 1 and (r[3] - r[1]) > 1]
    if rects:
        bb = list(rects[0])
        for r in rects[1:]:
            bb = union_rect(bb, r)
    elif spans:
        bb = list(spans[0]["bbox"])
    else:
        return list(page_rect)
    exp = [bb[0] - expand, bb[1] - expand, bb[2] + expand, bb[3] + expand]
    for s in spans:
        if rect_intersection_area(s["bbox"], exp) > 0:
            bb = union_rect(bb, s["bbox"])
    bb = [bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad]
    return [max(bb[0], page_rect[0]), max(bb[1], page_rect[1]),
            min(bb[2], page_rect[2]), min(bb[3], page_rect[3])]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k figure_bbox -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/diag_inspect.py .claude/skills/verify-diagram/test/test_diag_inspect.py
git commit -m "feat(verify-diagram): figure_bbox from drawings + nearby text

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A7: PyMuPDF I/O layer + `inspect()` + CLI

This wires the pure checks to real PDFs. Lightly tested here (one smoke assert on a generated PDF); the fixtures in A8 are the real integration coverage.

**Files:** Modify `diag_inspect.py`; Test `test_diag_inspect.py`.

- [ ] **Step 1: Write the failing test** (generates a one-page PDF with two overlapping text runs via fitz, no LaTeX)

```python
import fitz, json, tempfile

def test_inspect_pdf_end_to_end(tmp_path):
    pdf = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=200)
    page.insert_text((50, 100), "MARKER Alpha", fontsize=9)
    page.insert_text((90, 104), "Beta", fontsize=9)            # overlaps Alpha region
    page.draw_rect(fitz.Rect(40, 80, 200, 120))
    doc.save(pdf); doc.close()
    out = tmp_path / "out"
    res = di.inspect(str(pdf), locate="MARKER", out_dir=str(out), dpi=200)
    assert res["located"] is True
    assert os.path.exists(res["crop"])
    assert any(d["type"] == "overlap" for d in res["defects"])

def test_inspect_reports_not_located(tmp_path):
    pdf = tmp_path / "doc.pdf"
    doc = fitz.open(); doc.new_page(); doc.save(pdf); doc.close()
    res = di.inspect(str(pdf), locate="NOPE", out_dir=str(tmp_path / "o"))
    assert res["located"] is False and "error" in res
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k inspect -v`
Expected: FAIL — no attribute `inspect`.

- [ ] **Step 3: Write minimal implementation** (append to `diag_inspect.py`)

```python
import os as _os, json as _json, argparse as _argparse

def _spans_in(page, clip):
    import fitz
    spans, line_id = [], 0
    d = page.get_text("dict", clip=fitz.Rect(*clip)) if clip else page.get_text("dict")
    for blk in d.get("blocks", []):
        for ln in blk.get("lines", []):
            line_id += 1
            for sp in ln.get("spans", []):
                spans.append({"bbox": list(sp["bbox"]), "text": sp.get("text", ""),
                              "size": float(sp.get("size", 0.0)),
                              "font": sp.get("font", ""), "line_id": line_id})
    return spans

def _node_rects(page):
    rects = []
    for dr in page.get_drawings():
        r = dr["rect"]
        if (r.width > 10 and r.height > 8 and dr.get("type") in ("s", "f", "fs")):
            rects.append([r.x0, r.y0, r.x1, r.y1])
    return rects

def _draw_rects(page):
    out = []
    for dr in page.get_drawings():
        r = dr["rect"]
        if r.width > 1 and r.height > 1:
            out.append([r.x0, r.y0, r.x1, r.y1])
    return out

def locate_page(doc, substr):
    for i, page in enumerate(doc):
        if substr in page.get_text():
            return i
    return None

def inspect(pdf_path, locate, out_dir, dpi=300, min_font=6.0, overlap_frac=0.20,
            whole_guide=True):
    import fitz
    _os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    pi = locate_page(doc, locate)
    if pi is None:
        doc.close()
        return {"located": False, "error": "figure text '%s' not found in %s" % (locate, pdf_path)}
    page = doc[pi]
    page_rect = [page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1]
    draws = _draw_rects(page)
    all_spans = _spans_in(page, None)
    bb = figure_bbox(draws, all_spans, page_rect) if whole_guide else page_rect
    spans = _spans_in(page, bb)
    nodes = _node_rects(page)
    defects = (find_overlaps(spans, overlap_frac) + find_node_text_spill(spans, nodes)
               + find_tiny(spans, min_font) + find_node_overlaps(nodes))
    crop_path = _os.path.join(out_dir, "crop.png")
    page.get_pixmap(dpi=dpi, clip=fitz.Rect(*bb)).save(crop_path)
    result = {
        "located": True, "page": pi + 1, "bbox": [round(v, 1) for v in bb],
        "crop": crop_path, "tiles": [],
        "metrics": {"n_spans": len(spans),
                    "min_font_pt": round(min((s["size"] for s in spans if s["text"].strip()),
                                             default=0.0), 1)},
        "defects": defects,
    }
    doc.close()
    return result

def main(argv=None):
    p = _argparse.ArgumentParser(description="Inspect a TikZ diagram for geometric defects.")
    p.add_argument("--pdf", required=True)
    p.add_argument("--locate", required=True, help="unique caption/label substring on the figure's page")
    p.add_argument("--out", required=True)
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--min-font", type=float, default=6.0)
    p.add_argument("--overlap-frac", type=float, default=0.20)
    a = p.parse_args(argv)
    res = inspect(a.pdf, a.locate, a.out, a.dpi, a.min_font, a.overlap_frac)
    with open(_os.path.join(a.out, "inspection.json"), "w", encoding="utf-8") as f:
        _json.dump(res, f, indent=2)
    print(_json.dumps(res, indent=2))
    return 0 if res.get("located") else 2

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k inspect -v`
Expected: PASS (2 passed). Then run the whole file: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -v` — all green.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/diag_inspect.py .claude/skills/verify-diagram/test/test_diag_inspect.py
git commit -m "feat(verify-diagram): PyMuPDF I/O, inspect(), and CLI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A8: TeX fixtures + integration tests (the false-positive guard)

**Files:**
- Create: `.claude/skills/verify-diagram/test/fixtures/{overlap,spill,tiny,clean,subscript}.tex`
- Create: `.claude/skills/verify-diagram/test/test_fixtures.py`

- [ ] **Step 1: Write the five fixtures**

`overlap.tex` (two nodes forced to collide):
```latex
\documentclass[border=4pt]{standalone}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
  \node[draw, minimum width=2.2cm] (a) at (0,0) {Model Registry};
  \node[draw, minimum width=2.2cm] (b) at (1.3,0.15) {CV Strategies};
\end{tikzpicture}
\end{document}
```

`spill.tex` (label wider than its fixed-size box, no `text width`):
```latex
\documentclass[border=4pt]{standalone}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
  \node[draw, minimum width=1cm, minimum height=0.8cm, inner sep=0pt]
    {expanding\_window\_cv};
\end{tikzpicture}
\end{document}
```

`tiny.tex` (a sub-5pt label):
```latex
\documentclass[border=4pt]{standalone}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
  \node {{\fontsize{4}{5}\selectfont microscopic label}};
\end{tikzpicture}
\end{document}
```

`clean.tex` (well spaced — must yield ZERO defects):
```latex
\documentclass[border=6pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{positioning}
\begin{document}
\begin{tikzpicture}
  \node[draw, minimum width=2.4cm, minimum height=1cm] (a) {Ingest};
  \node[draw, minimum width=2.4cm, minimum height=1cm, right=1.4cm of a] (b) {Train};
  \draw[->] (a) -- (b);
\end{tikzpicture}
\end{document}
```

`subscript.tex` (legitimate math sub/superscripts and accents — must yield ZERO defects):
```latex
\documentclass[border=6pt]{standalone}
\usepackage{tikz, amsmath}
\begin{document}
\begin{tikzpicture}
  \node[draw, minimum width=3cm, minimum height=1.2cm]
    {$\hat{\sigma}^2_{t} = \beta_0 + \beta_1 RV_{t-1} + \beta_2 RV_{t-5}$};
\end{tikzpicture}
\end{document}
```

- [ ] **Step 2: Write the failing integration test**

```python
# .claude/skills/verify-diagram/test/test_fixtures.py
import os, sys, shutil, subprocess, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import diag_inspect as di

FX = os.path.join(os.path.dirname(__file__), "fixtures")
HAS_LATEX = shutil.which("pdflatex") is not None

def _compile(name, workdir):
    src = os.path.join(FX, name + ".tex")
    shutil.copy(src, workdir)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", name + ".tex"],
                   cwd=workdir, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.join(workdir, name + ".pdf")

def _types(name, tmp_path):
    pdf = _compile(name, str(tmp_path))
    # standalone page IS the figure -> whole_guide=False so bbox is the page
    res = di.inspect(pdf, locate="", out_dir=str(tmp_path / "o"), whole_guide=False)
    # locate="" matches every page's text; page 0 is the figure
    return {d["type"] for d in res["defects"]}, res

@pytest.mark.skipif(not HAS_LATEX, reason="pdflatex not installed")
def test_overlap_fixture(tmp_path):
    t, _ = _types("overlap", tmp_path)
    assert "overlap" in t

@pytest.mark.skipif(not HAS_LATEX, reason="pdflatex not installed")
def test_spill_fixture(tmp_path):
    t, _ = _types("spill", tmp_path)
    assert "node_text_spill" in t

@pytest.mark.skipif(not HAS_LATEX, reason="pdflatex not installed")
def test_tiny_fixture(tmp_path):
    t, _ = _types("tiny", tmp_path)
    assert "tiny_font" in t

@pytest.mark.skipif(not HAS_LATEX, reason="pdflatex not installed")
def test_clean_fixture_is_clean(tmp_path):
    t, res = _types("clean", tmp_path)
    assert t == set(), "clean fixture must produce zero defects, got %s" % res["defects"]

@pytest.mark.skipif(not HAS_LATEX, reason="pdflatex not installed")
def test_subscript_fixture_is_clean(tmp_path):
    t, res = _types("subscript", tmp_path)
    assert t == set(), "subscript fixture must produce zero defects, got %s" % res["defects"]
```

> Note on `locate=""`: `"" in page.get_text()` is always `True`, so `locate_page` returns page 0 — correct for single-page standalone fixtures. The engine always passes a real substring.

- [ ] **Step 3: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_fixtures.py -v`
Expected: FAIL — fixtures `.tex` compile but assertions fail until thresholds are right, OR the clean/subscript tests fail if defaults over-flag.

- [ ] **Step 4: Tune until green**

If `test_clean_fixture_is_clean` or `test_subscript_fixture_is_clean` fails, the thresholds over-flag. Adjust in `diag_inspect.py` (do **not** weaken the positive fixtures):
- Raise `overlap_frac` default toward `0.25` if adjacent clean nodes touch.
- In `find_node_text_spill`, raise `margin` to `2.0` so anti-aliasing/feathering at box edges doesn't trip.
Re-run until all five pass.

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/ -v`
Expected: PASS (all unit + integration tests green).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/test/fixtures .claude/skills/verify-diagram/test/test_fixtures.py .claude/skills/verify-diagram/diag_inspect.py
git commit -m "test(verify-diagram): TeX fixtures + integration coverage incl. false-positive guards

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase B — Reviewers + engine skill

### Task B1: Rewrite `SKILL.md` as the engine

The skill is LLM-executed (not unit-tested); its content IS the deliverable. Replace the file wholesale.

**Files:** Rewrite `.claude/skills/verify-diagram/SKILL.md`

- [ ] **Step 1: Write the new SKILL.md** (full content)

````markdown
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
````

- [ ] **Step 2: Sanity-check the skill references**

Run: `PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/diag_inspect.py --help`
Expected: argparse usage prints with `--pdf`, `--locate`, `--out`, `--dpi`, `--min-font`, `--overlap-frac`. (Confirms the command in SKILL.md is correct.)

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/verify-diagram/SKILL.md
git commit -m "feat(verify-diagram): rewrite SKILL.md as crop+reviewers+gate engine

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B2: Engine smoke test on a real diagram

Confirms the deterministic core flags a genuinely broken real diagram and is clean after a fix. (The reviewer/loop layer is LLM-driven; this automates the deterministic half of the acceptance.)

**Files:** Create `.claude/skills/verify-diagram/test/test_smoke_real.py`

- [ ] **Step 1: Write the test** (compiles vol-project-ref, asserts the real Fig 17.1 page is locatable and inspectable, and that an artificially overlapped variant flags `overlap`)

```python
# .claude/skills/verify-diagram/test/test_smoke_real.py
import os, sys, shutil, subprocess, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import diag_inspect as di

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
GUIDE = os.path.join(REPO, "guides", "vol-project-ref")
PDF = os.path.join(GUIDE, "main.pdf")
HAS = shutil.which("pdflatex") is not None and os.path.exists(PDF)

@pytest.mark.skipif(not HAS, reason="needs compiled vol-project-ref/main.pdf")
def test_real_pipeline_figure_is_locatable_and_cropped(tmp_path):
    res = di.inspect(PDF, locate="Pipeline architecture with plug points",
                     out_dir=str(tmp_path), dpi=200)
    assert res["located"] is True
    assert os.path.exists(res["crop"])
    # crop must be substantially smaller than a full page region (it is cropped, not full-page)
    import fitz
    pm = fitz.open(PDF)[res["page"] - 1].rect
    assert (res["bbox"][3] - res["bbox"][1]) < (pm.y1 - pm.y0) * 0.6
```

- [ ] **Step 2: Run it**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_smoke_real.py -v`
Expected: PASS (or SKIP if `main.pdf` isn't compiled — compile it first with the Step 1 command in SKILL.md).

- [ ] **Step 3: Manual engine acceptance (document, do not automate)**

In a scratch branch, edit `guides/vol-project-ref/chapters/ch17-modular-pipeline.tex` to force an
overlap (e.g. set the three `registry` nodes' `xshift` to `-1.2cm`/`0`/`1.2cm` so they collide).
Invoke the `verify-diagram` skill on Fig 17.1. Confirm: it crops, the deterministic pass reports
`overlap`/`node_overlap`, the loop edits the TikZ, and it terminates clean within 5 iterations. Revert
the scratch edit. Record the run in `logs/progress.md`.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/verify-diagram/test/test_smoke_real.py
git commit -m "test(verify-diagram): smoke test on real pipeline figure

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase C — Batch workflow

### Task C1: Pure discovery/group helpers (TDD, Node test runner)

**Files:** Create `.claude/workflows/__tests__/verify-all-diagrams-helpers.test.mjs`

- [ ] **Step 1: Write the failing test + helper block** (test file is the source of truth; mirrored into the workflow in C2)

```js
// .claude/workflows/__tests__/verify-all-diagrams-helpers.test.mjs
import { test } from 'node:test'
import assert from 'node:assert'

// >>> VERIFY-ALL-DIAGRAMS HELPERS (mirror into .claude/workflows/verify-all-diagrams.js) >>>
// Pure, dependency-free. EDIT HERE ONLY; the workflow mirrors this block verbatim.

function discoverFiguresInTex(relPath, tex) {
  // Returns one entry per tikzpicture, with the nearest enclosing \label and \caption if present.
  const out = []
  const lines = String(tex).split('\n')
  for (let i = 0; i < lines.length; i++) {
    if (!/\\begin\{tikzpicture\}/.test(lines[i])) continue
    let end = i
    for (let j = i; j < lines.length; j++) { if (/\\end\{tikzpicture\}/.test(lines[j])) { end = j; break } }
    // search a small window around the picture for label/caption
    const lo = Math.max(0, i - 3), hi = Math.min(lines.length, end + 6)
    const window = lines.slice(lo, hi).join('\n')
    const label = (window.match(/\\label\{([^}]+)\}/) || [])[1] || null
    const caption = (window.match(/\\caption\{([\s\S]*?)\}/) || [])[1] || null
    out.push({
      file: relPath,
      label,
      caption: caption ? caption.replace(/\s+/g, ' ').trim().slice(0, 80) : null,
      lineStart: i + 1,
      lineEnd: end + 1,
      id: label || `${relPath}:${i + 1}`,
    })
  }
  return out
}

function groupByFile(figures) {
  const m = new Map()
  for (const f of figures) {
    if (!m.has(f.file)) m.set(f.file, [])
    m.get(f.file).push(f)
  }
  return Array.from(m.entries()).map(([file, figs]) => ({ file, figures: figs }))
}

function locateSubstr(fig) {
  // what diag_inspect --locate should use: prefer a distinctive caption fragment, else the label
  if (fig.caption) return fig.caption.split(' ').slice(0, 6).join(' ')
  return fig.label || fig.id
}
// <<< VERIFY-ALL-DIAGRAMS HELPERS <<<

const SAMPLE = String.raw`
\begin{figure}
\centering
\resizebox{\textwidth}{!}{%
\begin{tikzpicture}
  \node {A};
\end{tikzpicture}}
\caption{Pipeline architecture with plug points. Config parameterises all.}
\label{fig:pipeline-plugpoints}
\end{figure}
\begin{tikzpicture}\node{bare};\end{tikzpicture}
`

test('discoverFiguresInTex finds both figures with metadata', () => {
  const figs = discoverFiguresInTex('guides/g/chapters/ch.tex', SAMPLE)
  assert.equal(figs.length, 2)
  assert.equal(figs[0].label, 'fig:pipeline-plugpoints')
  assert.match(figs[0].caption, /Pipeline architecture/)
  assert.equal(figs[1].label, null)
  assert.equal(figs[1].id, 'guides/g/chapters/ch.tex:9')
})

test('groupByFile groups figures by their file', () => {
  const groups = groupByFile([
    { file: 'a.tex', id: '1' }, { file: 'a.tex', id: '2' }, { file: 'b.tex', id: '3' },
  ])
  assert.equal(groups.length, 2)
  assert.equal(groups[0].figures.length, 2)
})

test('locateSubstr prefers a caption fragment', () => {
  assert.equal(
    locateSubstr({ caption: 'Pipeline architecture with plug points here now', label: 'x' }),
    'Pipeline architecture with plug points')
  assert.equal(locateSubstr({ caption: null, label: 'fig:y', id: 'z' }), 'fig:y')
})
```

- [ ] **Step 2: Run test to verify it fails, then passes**

Run: `node --test .claude/workflows/__tests__/verify-all-diagrams-helpers.test.mjs`
Expected: the three tests PASS (the helper block is defined in the same file). If any fail, fix the helper block until green. (This file is both the spec and the test for the pure logic.)

- [ ] **Step 3: Commit**

```bash
git add .claude/workflows/__tests__/verify-all-diagrams-helpers.test.mjs
git commit -m "test(verify-all-diagrams): discovery + grouping helpers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task C2: The `verify-all-diagrams.js` workflow

**Files:** Create `.claude/workflows/verify-all-diagrams.js`

- [ ] **Step 1: Write the workflow** (full content; the helper block is the verbatim mirror from C1)

```js
export const meta = {
  name: 'verify-all-diagrams',
  description: 'Audit and fix every TikZ diagram across all guides: crop + deterministic checks + blind reviewers + fix-loop, grouped by file in isolated worktrees, with a contact-sheet report.',
  whenToUse: 'When you want to sweep all guide diagrams for legibility/clarity defects and fix the failures. Pass args="guides/vol-project-ref" to limit to one guide, or omit for all.',
  phases: [
    { title: 'Discover', detail: 'enumerate every tikzpicture figure across the guides' },
    { title: 'Verify', detail: 'run the engine per diagram, grouped by file, in parallel worktrees' },
    { title: 'Consolidate', detail: 'recompile guides, build the contact sheet, write the summary' },
  ],
}

// >>> VERIFY-ALL-DIAGRAMS HELPERS (mirror of __tests__/verify-all-diagrams-helpers.test.mjs) >>>
// EDIT IN THE TEST FILE ONLY; paste verbatim here.
function discoverFiguresInTex(relPath, tex) {
  const out = []
  const lines = String(tex).split('\n')
  for (let i = 0; i < lines.length; i++) {
    if (!/\\begin\{tikzpicture\}/.test(lines[i])) continue
    let end = i
    for (let j = i; j < lines.length; j++) { if (/\\end\{tikzpicture\}/.test(lines[j])) { end = j; break } }
    const lo = Math.max(0, i - 3), hi = Math.min(lines.length, end + 6)
    const window = lines.slice(lo, hi).join('\n')
    const label = (window.match(/\\label\{([^}]+)\}/) || [])[1] || null
    const caption = (window.match(/\\caption\{([\s\S]*?)\}/) || [])[1] || null
    out.push({ file: relPath, label,
      caption: caption ? caption.replace(/\s+/g, ' ').trim().slice(0, 80) : null,
      lineStart: i + 1, lineEnd: end + 1, id: label || `${relPath}:${i + 1}` })
  }
  return out
}
function groupByFile(figures) {
  const m = new Map()
  for (const f of figures) { if (!m.has(f.file)) m.set(f.file, []); m.get(f.file).push(f) }
  return Array.from(m.entries()).map(([file, figs]) => ({ file, figures: figs }))
}
function locateSubstr(fig) {
  if (fig.caption) return fig.caption.split(' ').slice(0, 6).join(' ')
  return fig.label || fig.id
}
// <<< VERIFY-ALL-DIAGRAMS HELPERS <<<

const GUIDES = args && String(args).trim()
  ? [String(args).trim()]
  : ['guides/vol-project-ref', 'guides/quant-trading', 'vol-learning-guide']

// ---- Phase 1: Discover ----
phase('Discover')
const DISCOVER_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    files: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: {
        file: { type: 'string' },
        figures: { type: 'array', items: {
          type: 'object', additionalProperties: false,
          properties: {
            id: { type: 'string' }, label: { type: 'string' },
            caption: { type: 'string' }, locate: { type: 'string' },
            guide: { type: 'string' },
          },
          required: ['id', 'locate', 'guide'],
        } },
      },
      required: ['file', 'figures'],
    } },
  },
  required: ['files'],
}

const discovery = await agent(
  `Enumerate every TikZ figure in these guides: ${JSON.stringify(GUIDES)}.
For each guide, Glob its chapter .tex files (e.g. <guide>/chapters/*.tex and <guide>/*.tex), Read each,
and find every \\begin{tikzpicture}. For each, record the nearest \\label and \\caption, the file path
(repo-relative), the guide root, and a "locate" string = the first ~6 words of the caption if present,
else the label. Group the result by file. Return strictly the schema.`,
  { label: 'discover:figures', phase: 'Discover', agentType: 'Explore', schema: DISCOVER_SCHEMA }
)

const fileGroups = discovery.files.filter(g => g.figures && g.figures.length)
const totalFigs = fileGroups.reduce((n, g) => n + g.figures.length, 0)
log(`Discovered ${totalFigs} figures across ${fileGroups.length} files`)

// ---- Phase 2: Verify (one agent per FILE-group; figures within a file handled sequentially) ----
phase('Verify')
const FILE_RESULT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    file: { type: 'string' },
    results: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: {
        id: { type: 'string' },
        status: { type: 'string', enum: ['already_clean', 'fixed', 'needs_human'] },
        blockingBefore: { type: 'number' }, blockingAfter: { type: 'number' },
        finalCrop: { type: 'string' }, notes: { type: 'string' },
      },
      required: ['id', 'status'],
    } },
  },
  required: ['file', 'results'],
}

const perFile = await parallel(fileGroups.map(group => () =>
  agent(
    `You are fixing the TikZ diagrams in ONE file, in an isolated git worktree.
FILE: ${group.file}
FIGURES (process sequentially, one at a time, because they share this file):
${JSON.stringify(group.figures, null, 1)}

For EACH figure, follow the verify-diagram skill engine exactly:
1. Compile the figure's guide ('${''}' the figure carries its guide root) with
   pdflatex -interaction=nonstopmode -halt-on-error main.tex.
2. Run: PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/diag_inspect.py --pdf <guide>/main.pdf
   --locate "<figure.locate>" --out <guide>/.diagverify
3. View <guide>/.diagverify/crop.png (Read tool). Dispatch the two blind reviewers (legibility +
   learning-clarity) on the crop — they must NOT see the TikZ. Apply the gate from the skill.
4. If it fails, edit ONLY this file's TikZ for that figure, recompile, re-inspect. Cap 5 iterations.
5. Record status: already_clean (passed first try), fixed (passed after edits), or needs_human (hit cap).
Do NOT commit. Leave edits in the working tree of this worktree. Return the schema with one result per figure.`,
    { label: `verify:${group.file.split('/').pop()}`.slice(0, 40), phase: 'Verify',
      isolation: 'worktree', schema: FILE_RESULT_SCHEMA }
  )
)).filter(Boolean)

const flat = perFile.flatMap(f => f.results.map(r => ({ file: f.file, ...r })))
const needHuman = flat.filter(r => r.status === 'needs_human')
const fixed = flat.filter(r => r.status === 'fixed')
log(`Verified ${flat.length} figures: ${fixed.length} fixed, ${needHuman.length} need human, ` +
    `${flat.length - fixed.length - needHuman.length} already clean`)

// ---- Phase 3: Consolidate ----
phase('Consolidate')
const SUMMARY_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { reportPath: { type: 'string' }, contactSheet: { type: 'string' },
                guidesRecompiled: { type: 'array', items: { type: 'string' } },
                written: { type: 'boolean' } },
  required: ['reportPath', 'written'],
}

const consolidation = await agent(
  `Consolidate the batch diagram audit. The per-file worktrees hold the edits (disjoint files).
INPUTS (one row per figure): ${JSON.stringify(flat, null, 1)}
Guides touched: ${JSON.stringify(GUIDES)}

Do:
1. Recompile each touched guide whole (cd <guide> && pdflatex -interaction=nonstopmode -halt-on-error
   main.tex) to confirm nothing broke. Note any guide that now fails to compile.
2. Build a contact sheet of the final crops:
   PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/contact_sheet.py --crops <crop1> <crop2> ...
   --out notes/diagram-audit/contact-sheet.png   (create the dir; skip crops that don't exist).
3. Write a markdown report to notes/diagram-audit/2026-06-01-audit.md: a table of file | figure |
   status | blockingBefore->blockingAfter, then a "Needs human" section listing the unresolved ones
   with their final crop paths, then an embedded link to the contact sheet.
4. Do NOT commit anything. Return the schema.`,
  { label: 'consolidate', phase: 'Consolidate', schema: SUMMARY_SCHEMA }
)

return {
  guides: GUIDES,
  totalFigures: totalFigs,
  fixed: fixed.length,
  needHuman: needHuman.map(r => `${r.file}#${r.id}`),
  report: consolidation.reportPath,
  contactSheet: consolidation.contactSheet,
}
```

- [ ] **Step 2: Verify the mirrored helper block matches the test file**

Run: `node --test .claude/workflows/__tests__/verify-all-diagrams-helpers.test.mjs`
Expected: PASS — and visually confirm the three helper functions in the workflow are byte-identical to the test file's block (between the `>>>`/`<<<` markers).

- [ ] **Step 3: Syntax-check the workflow**

Run: `node --check .claude/workflows/verify-all-diagrams.js`
Expected: no output (valid JS).

- [ ] **Step 4: Commit**

```bash
git add .claude/workflows/verify-all-diagrams.js
git commit -m "feat(verify-all-diagrams): batch audit-and-fix workflow

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task C3: Contact-sheet generator

**Files:**
- Create `.claude/skills/verify-diagram/contact_sheet.py`
- Create `.claude/skills/verify-diagram/test/test_contact_sheet.py`

- [ ] **Step 1: Write the failing test** (grid-layout math is pure and testable)

```python
# .claude/skills/verify-diagram/test/test_contact_sheet.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import contact_sheet as cs

def test_grid_dims():
    assert cs.grid_dims(1) == (1, 1)
    assert cs.grid_dims(4) == (2, 2)
    assert cs.grid_dims(5) == (3, 2)     # cols=ceil(sqrt), rows=ceil(n/cols)
    assert cs.grid_dims(7) == (3, 3)

def test_cell_origin():
    # cell index 3 in a 3-col grid with 100x80 cells, 10 gap -> row1,col0
    assert cs.cell_origin(3, cols=3, cw=100, ch=80, gap=10) == (10, 100)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_contact_sheet.py -v`
Expected: FAIL — no module `contact_sheet`.

- [ ] **Step 3: Write the implementation**

```python
# .claude/skills/verify-diagram/contact_sheet.py
"""Assemble a grid PNG ("contact sheet") from per-diagram crop PNGs."""
import math, argparse, os

def grid_dims(n):
    if n <= 0:
        return (0, 0)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    return (cols, rows)

def cell_origin(index, cols, cw, ch, gap):
    row, col = divmod(index, cols)
    return (gap + col * (cw + gap), gap + row * (ch + gap))

def build(crop_paths, out_path, cell=420, gap=14):
    import fitz
    paths = [p for p in crop_paths if p and os.path.exists(p)]
    if not paths:
        return None
    cols, rows = grid_dims(len(paths))
    W = gap + cols * (cell + gap)
    H = gap + rows * (cell + gap)
    sheet = fitz.open()
    page = sheet.new_page(width=W, height=H)
    for i, p in enumerate(paths):
        x, y = cell_origin(i, cols, cell, cell, gap)
        img = fitz.open(p)
        r = img[0].rect
        scale = min(cell / r.width, cell / r.height)
        w, h = r.width * scale, r.height * scale
        page.insert_image(fitz.Rect(x, y, x + w, y + h), filename=p)
        img.close()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    page.get_pixmap(dpi=150).save(out_path)
    sheet.close()
    return out_path

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--crops", nargs="*", default=[])
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    res = build(a.crops, a.out)
    print(res or "no crops")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_contact_sheet.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/contact_sheet.py .claude/skills/verify-diagram/test/test_contact_sheet.py
git commit -m "feat(verify-diagram): contact-sheet generator for batch report

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase D — write-chapter integration

### Task D1: Pass concept/relationships and surface `needs-human`

**Files:** Modify `.claude/skills/write-chapter/SKILL.md`

- [ ] **Step 1: Update the Diagrams paragraph**

Find this text in `.claude/skills/write-chapter/SKILL.md` (under `### Diagrams`):

> **After writing any TikZ diagram, invoke the `verify-diagram` skill to visually inspect the rendered output.** The skill compiles the LaTeX, renders the diagram page to a PNG, and checks for arrows going through boxes, overlapping paths, broken routing, and dependency accuracy. Fix any issues found and re-verify until the diagram is clean. Never submit a chapter with an unverified diagram.

Replace it with:

> **After writing any TikZ diagram, invoke the `verify-diagram` skill.** Pass it: the guide root, a unique caption/label substring on the figure's page, a one-line **concept** (what the diagram should teach), and the intended **relationships** (the arrows/dependencies it should encode — this enables the correctness lens). The engine crops the figure to high resolution, runs deterministic geometric checks plus two blind reviewers (legibility + learning-clarity), and loops fix→re-verify until both gates pass. If it returns a **`needs-human`** result (it hit the iteration cap), do NOT proceed — surface the remaining defects to the user and resolve them before submitting the chapter. Never submit a chapter with an unverified diagram.

- [ ] **Step 2: Verify the edit applied**

Run: `grep -n "needs-human" .claude/skills/write-chapter/SKILL.md`
Expected: one match (the new clause).

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/write-chapter/SKILL.md
git commit -m "feat(write-chapter): pass concept/relationships to verify-diagram, surface needs-human

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase E — Optional: standalone fast-path

> Optional speed optimization. The engine is correct without it (whole-guide compile). Implement only if
> per-iteration compile time becomes painful in practice.

### Task E1: `standalone_wrapper.py` (extract figure + preview-compile, with fallback contract)

**Files:**
- Create `.claude/skills/verify-diagram/standalone_wrapper.py`
- Add tests to `.claude/skills/verify-diagram/test/test_diag_inspect.py`

- [ ] **Step 1: Write the failing test for the pure extractor**

```python
def test_extract_figure_body_grabs_resizebox_tikz():
    tex = r"""
\begin{figure}
\centering
\resizebox{\textwidth}{!}{%
\begin{tikzpicture}
\node {A};
\end{tikzpicture}}
\caption{Cap}
\label{fig:demo}
\end{figure}
"""
    import standalone_wrapper as sw
    body = sw.extract_figure_body(tex, "fig:demo")
    assert "\\begin{tikzpicture}" in body and "\\end{tikzpicture}" in body
    assert "\\caption" not in body and "\\label" not in body
    assert body.strip().startswith("\\resizebox")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k extract_figure_body -v`
Expected: FAIL — no module `standalone_wrapper`.

- [ ] **Step 3: Implement**

```python
# .claude/skills/verify-diagram/standalone_wrapper.py
"""Optional fast path: build a preview-cropped standalone PDF of ONE figure.
Falls back to whole-guide compile (caller's responsibility) if anything here fails."""
import re, os, argparse, subprocess

def _figure_env(tex, label):
    # the figure environment that contains \label{label}
    for m in re.finditer(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", tex, re.DOTALL):
        if ("\\label{%s}" % label) in m.group(1):
            return m.group(1)
    return None

def _balanced(s, start):
    # given index at '{', return index just after its matching '}'
    depth, i = 0, start
    while i < len(s):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(s)

def extract_figure_body(tex, label):
    env = _figure_env(tex, label)
    if env is None:
        raise ValueError("no figure with label %s" % label)
    m = re.search(r"\\(resizebox|scalebox)", env)
    if m:
        # consume macro + all its brace groups
        i = m.start()
        # skip to first '{' then balance repeatedly until the group containing tikzpicture closes
        # resizebox has {w}{h}{body}; scalebox has {f}{body}. Consume groups until one holds tikzpicture.
        j = i
        body_end = i
        while j < len(env):
            b = env.find('{', j)
            if b == -1:
                break
            e = _balanced(env, b)
            body_end = e
            if "\\begin{tikzpicture}" in env[b:e]:
                break
            j = e
        return env[i:body_end].strip()
    # bare tikzpicture
    t0 = env.find("\\begin{tikzpicture}")
    t1 = env.find("\\end{tikzpicture}")
    if t0 == -1 or t1 == -1:
        raise ValueError("no tikzpicture in figure %s" % label)
    return env[t0:t1 + len("\\end{tikzpicture}")].strip()

def build_pdf(guide_dir, label, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    # find the chapter file containing the label
    chap = None
    for root, _, files in os.walk(os.path.join(guide_dir, "chapters")):
        for fn in files:
            if fn.endswith(".tex"):
                p = os.path.join(root, fn)
                with open(p, encoding="utf-8") as f:
                    if ("\\label{%s}" % label) in f.read():
                        chap = p
                        break
        if chap:
            break
    if not chap:
        raise ValueError("label %s not found under %s/chapters" % (label, guide_dir))
    with open(chap, encoding="utf-8") as f:
        body = extract_figure_body(f.read(), label)
    wrapper = (
        "\\documentclass[11pt,a4paper]{report}\n"
        "\\usepackage[active,tightpage]{preview}\n"
        "\\input{preamble}\n"
        "\\setlength\\PreviewBorder{6pt}\n"
        "\\begin{document}\n\\begin{preview}\n" + body + "\n\\end{preview}\n\\end{document}\n"
    )
    wpath = os.path.join(guide_dir, "_diagstandalone.tex")
    with open(wpath, "w", encoding="utf-8") as f:
        f.write(wrapper)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "_diagstandalone.tex"],
                       cwd=guide_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(guide_dir, "_diagstandalone.pdf")
    if r.returncode != 0 or not os.path.exists(pdf):
        raise RuntimeError("standalone compile failed; caller should fall back to whole-guide")
    return pdf

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--guide", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        print(build_pdf(a.guide, a.label, a.out))
        return 0
    except Exception as e:
        print("FALLBACK: %s" % e)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the unit test, then a real integration check**

Run: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/test_diag_inspect.py -k extract_figure_body -v`
Expected: PASS.

Real check (manual, may fall back):
`PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/standalone_wrapper.py --guide guides/vol-project-ref --label fig:pipeline-plugpoints --out /tmp/ds`
Expected: prints a PDF path (success) OR `FALLBACK: ...` (then the engine uses whole-guide — acceptable). Clean up `guides/vol-project-ref/_diagstandalone.*` afterward.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/verify-diagram/standalone_wrapper.py .claude/skills/verify-diagram/test/test_diag_inspect.py
git commit -m "feat(verify-diagram): optional standalone fast-path with whole-guide fallback

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final verification

- [ ] Run the full Python suite: `PYTHONIOENCODING=utf-8 py -m pytest .claude/skills/verify-diagram/test/ -v` — all pass (fixture/smoke tests may SKIP without pdflatex/main.pdf).
- [ ] Run the JS helpers: `node --test .claude/workflows/__tests__/verify-all-diagrams-helpers.test.mjs` — all pass.
- [ ] `node --check .claude/workflows/verify-all-diagrams.js` — valid.
- [ ] Confirm `.gitignore` ignores the engine's temp dir: add `**/.diagverify/` and `**/_diagstandalone.*` if not already covered by the LaTeX-artifact rules.

---

## Self-Review (completed during planning)

**Spec coverage:**
- Component A (deterministic core) → Tasks A1–A8. ✓ (The spec's `clip` is implemented as `node_text_spill` — a label overflowing its own box, which is the readability-relevant, mode-independent form. Raw page-margin clipping was intentionally dropped because it false-positives under `tightpage`/standalone rendering. Flagged here so it isn't mistaken for a gap.)
- Component B (reviewers + gate) → Task B1 (reviewer prompts, blind constraint, gate, cap). ✓
- Component C (engine loop, standalone-first) → Task B1 loop + Phase E (standalone). Standalone demoted to optional with fallback — flagged. ✓
- Component D (batch workflow, worktree isolation, contact sheet, no auto-commit) → Tasks C1–C3. ✓
- Component E (write-chapter integration) → Task D1. ✓
- TDD plan (five fixtures incl. clean + subscript guards) → Task A8. ✓
- Acceptance criteria → covered by A8 (fixtures), B2 (real crop), C (workflow). ✓

**Placeholder scan:** no TBD/TODO; every code step shows complete code. ✓

**Type/name consistency:** defect dict shape (`type/severity/bbox/detail`), span shape (`bbox/text/size/line_id`), and function names (`find_overlaps`, `find_node_text_spill`, `find_tiny`, `find_node_overlaps`, `figure_bbox`, `inspect`, `discoverFiguresInTex`, `groupByFile`, `locateSubstr`, `grid_dims`, `cell_origin`, `extract_figure_body`) are used identically across tasks. ✓
