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


@pytest.fixture(scope="module")
def html_missing_dash() -> str:
    return generate.generate(
        dashboard_path="does_not_exist/nowhere.html",
        output_path=HERE / "presentation.html",
    )


def test_mock_fixture_exists():
    assert (HERE / "tournament_dashboard_mock.html").exists()


def test_dashboard_iframe_when_available(html):
    assert 'id="dashboard-frame"' in html
    assert "tournament_dashboard_mock.html" in html
    assert 'id="dashboard-placeholder"' not in html


def test_placeholder_when_missing(html_missing_dash):
    assert 'id="dashboard-placeholder"' in html_missing_dash
    assert 'id="dashboard-frame"' not in html_missing_dash
    assert "does_not_exist/nowhere.html" in html_missing_dash


def test_d_key_toggles(html):
    assert "toggleDashboard" in html
    assert "'d'" in html.lower()


def test_no_magic_numbers(html):
    for bad in ("0.13679", "0.1289", "153 bps", "138 bps", "+153", "+138"):
        assert bad not in html, f"magic number leaked: {bad}"


def test_kickers_in_order(html):
    order = ["ML Vol Forecasting", "The product and its problem", "The claim",
             "The model", "The features", "Why trust the number",
             "What it learned", "Results", "The fine print, and the point"]
    positions = [html.index(k) for k in order]
    assert positions == sorted(positions)


def test_key_copy_present(html):
    for phrase in (
        "sells a strip of same-day SPX options",
        "stand aside for the day",
        "A linear spine and a tree overlay",
        "lucky seed looked 6% better than the truth",
        "the identical model trained on MSE instead of QLIKE trades at Sharpe 0.3",
        "7 of 10",
    ):
        assert phrase in html, f"missing copy: {phrase}"
