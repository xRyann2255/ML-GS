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
