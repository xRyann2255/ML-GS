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
