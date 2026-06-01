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
