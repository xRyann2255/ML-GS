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

def find_node_text_spill(spans, node_rects, margin=1.0):
    out = []
    for s in spans:
        if not s["text"].strip():
            continue
        # associate the span with the node box it overlaps most (robust even when the
        # label overflows so far that its centre falls outside the box)
        best, best_ov = None, 0.0
        for r in node_rects:
            ov = rect_intersection_area(s["bbox"], r)
            if ov > best_ov:
                best_ov, best = ov, r
        if best is None or best_ov <= 0:
            continue
        b = s["bbox"]
        if (b[0] < best[0] - margin or b[2] > best[2] + margin or
                b[1] < best[1] - margin or b[3] > best[3] + margin):
            out.append({
                "type": "node_text_spill", "severity": "warn", "bbox": b,
                "detail": "label '%s' overflows its box" % s["text"][:20]})
    return out

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
