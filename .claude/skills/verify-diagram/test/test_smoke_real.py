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
