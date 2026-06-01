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
