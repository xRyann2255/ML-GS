"""Structural tests for the desk-pitch deck generator.

Run:  cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import generate  # noqa: E402


@pytest.fixture(scope="module")
def html() -> str:
    return generate.generate(
        dashboard_path="tournament_dashboard_mock.html",
        output_path=HERE / "presentation.html",
    )


def test_nine_slides(html):
    assert len(re.findall(r'<section class="slide', html)) == 9


def test_title_present(html):
    assert "Timing the Variance Seller" in html


def test_no_external_requests(html):
    for pat in ('src="http', "src='http", 'href="http', "href='http", "url(http", "@import"):
        assert pat not in html, f"external request pattern found: {pat}"


def test_no_em_dash(html):
    assert "—" not in html


def test_keyboard_nav_and_counter(html):
    assert "'ArrowRight'" in html
    assert 'id="counter"' in html
    assert 'id="stage"' in html


def test_cli_writes_output(tmp_path):
    out = tmp_path / "deck.html"
    subprocess.run(
        [sys.executable, str(HERE / "generate.py"),
         "--dashboard-path", "tournament_dashboard_mock.html",
         "--output", str(out)],
        check=True,
    )
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>")


def test_em_dash_guard(monkeypatch):
    monkeypatch.setattr(
        generate, "_get_slides",
        lambda: '<section class="slide">bad — dash</section>',
    )
    with pytest.raises(ValueError, match="em dash"):
        generate.generate(
            dashboard_path="tournament_dashboard_mock.html",
            output_path=HERE / "presentation.html",
        )
