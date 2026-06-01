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

def test_node_text_spill_flags_overflow():
    node = [0, 0, 30, 12]
    spans = [_span([-4, 1, 34, 11], "wide_label", line_id=1)]   # center inside, x overflows
    d = di.find_node_text_spill(spans, [node], margin=1.0)
    assert len(d) == 1 and d[0]["type"] == "node_text_spill" and d[0]["severity"] == "warn"

def test_node_text_spill_ok_when_contained():
    node = [0, 0, 30, 12]
    spans = [_span([3, 2, 27, 10], "fits", line_id=1)]
    assert di.find_node_text_spill(spans, [node], margin=1.0) == []

def test_find_tiny_warns_and_blocks():
    spans = [_span([0, 0, 10, 6], "a", size=5.5, line_id=1),   # <6 -> warn
             _span([0, 0, 10, 5], "b", size=4.0, line_id=2),   # <5 -> blocking
             _span([0, 0, 10, 9], "c", size=9.0, line_id=3)]   # ok
    d = di.find_tiny(spans, min_pt=6.0)
    sev = sorted(x["severity"] for x in d)
    assert sev == ["blocking", "warn"]
    assert all(x["type"] == "tiny_font" for x in d)

def test_find_node_overlaps():
    rects = [[0, 0, 20, 20], [10, 10, 30, 30], [100, 100, 110, 110]]
    d = di.find_node_overlaps(rects, frac=0.15)
    assert len(d) == 1 and d[0]["type"] == "node_overlap" and d[0]["severity"] == "blocking"

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
