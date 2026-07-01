"""Desk-pitch deck generator: Timing the Variance Seller.

Builds ONE self-contained HTML file (no CDN, no network requests) for the
GSVIVS01 presentation. 9 slides, dark serif theme, dashboard iframe toggle.

Regenerate (GS):      ./vol present --dashboard-path '<rel path from output HTML>'
Regenerate (local):   cd ml-vol-estimator && ./vol shell ../workspace/presentation/generate.py \
                          --dashboard-path tournament_dashboard_mock.html

Canonical numbers live in NUMBERS below and carry [VERIFY on GS] flags from
the spec (docs/superpowers/specs/2026-07-02-presentation-rewrite-design.md 3.5).
"""
from __future__ import annotations

import argparse
from pathlib import Path

THEME = {
    "bg": "#0c1117",
    "ink": "#e8e4da",
    "muted": "#7d8896",
    "muted2": "#9aa5b1",
    "body": "#c7cdd6",
    "hairline": "#1f2a37",
    "amber": "#e8b339",
    "green": "#4cc38a",
    "red": "#e05252",
    "serif": "Georgia, 'Times New Roman', serif",
    "sans": "'Segoe UI', Verdana, sans-serif",
}

# Single source of truth for every number said or shown. [VERIFY on GS] before delivery.
NUMBERS = {
    "sharpe_before": "1.60",
    "sharpe_after": "1.95",
    "backtest_window": "May 2022 to Jun 2026",
    "stand_aside_share": "2%",
    "precision": "7 of 10",
    "transitions_per_year": "about ten",
    "index_path": "100 to 138",
    "index_per_year": "9.6 points a year",
    "h1_improvement": "about 10% lower forecast loss",
    "h5_improvement": "about 11% lower",
    "seed_inflation": "6% better than the truth",
    "mse_sharpe": "0.3",
    "n_symbols": "21",
    "n_features": "about 128",
    "purge_days": "ten trading days",
    "kvar_proxy_corr": "above 0.99",
}


def _slide(kicker: str, title: str, body: str, cls: str = "") -> str:
    klass = f"slide {cls}".strip()
    return (
        f'<section class="{klass}">\n'
        f'  <div class="kicker">{kicker}</div>\n'
        f'  <div class="rule"></div>\n'
        f'  <h1>{title}</h1>\n'
        f'{body}\n'
        f'</section>'
    )


def _slide_01() -> str:
    return _slide("ML Vol Forecasting", "Timing the Variance Seller", "", "title-slide")


def _slide_02() -> str:
    return _slide("The product and its problem", "GSVIVS01 sells variance every single day", "")


def _slide_03() -> str:
    return _slide("The claim", "Every morning: compare the forecast to the strike", "")


def _slide_04() -> str:
    return _slide("The model", "A linear spine and a tree overlay", "")


def _slide_05() -> str:
    return _slide("The features", "Four things the market tells you", "")


def _slide_06() -> str:
    return _slide("Why trust the number", "Walk-forward with a moat, five seeds", "")


def _slide_07() -> str:
    return _slide("What it learned", "Everything it learned has a name you know", "")


def _slide_08() -> str:
    return _slide("Results", "Where it wins, and where it honestly doesn't", "")


def _slide_09() -> str:
    return _slide("The fine print, and the point", "Three caveats, three numbers", "")


def _get_slides() -> str:
    return "\n\n".join(f() for f in (
        _slide_01, _slide_02, _slide_03, _slide_04, _slide_05,
        _slide_06, _slide_07, _slide_08, _slide_09,
    ))


def _get_css() -> str:
    t = THEME
    return f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ height: 100%; background: {t['bg']}; overflow: hidden; }}
#stage {{
  position: absolute; top: 50%; left: 50%;
  width: 1280px; height: 720px;
  transform-origin: center center;
  background: {t['bg']}; color: {t['ink']};
  font-family: {t['sans']};
}}
.slide {{ display: none; width: 100%; height: 100%; padding: 72px 96px; position: relative; }}
.slide.active {{ display: block; }}
.kicker {{
  font-size: 15px; letter-spacing: 4px; text-transform: uppercase;
  color: {t['amber']};
}}
.rule {{ border-top: 1px solid {t['amber']}; width: 64px; margin: 18px 0 26px; opacity: .7; }}
h1 {{ font-family: {t['serif']}; font-weight: normal; font-size: 46px; line-height: 1.15; color: {t['ink']}; margin-bottom: 26px; }}
p {{ font-size: 20px; line-height: 1.6; color: {t['body']}; max-width: 1000px; margin-bottom: 16px; }}
p.dim {{ color: {t['muted2']}; }}
.g {{ color: {t['green']}; }}
.a {{ color: {t['amber']}; }}
.footer-band {{
  position: absolute; left: 96px; right: 96px; bottom: 56px;
  border-top: 1px solid {t['hairline']}; padding-top: 16px;
  display: flex; justify-content: space-between;
  font-size: 15px; color: {t['muted']};
}}
#counter {{
  position: fixed; right: 18px; bottom: 12px; z-index: 30;
  font-family: {t['sans']}; font-size: 12px; color: {t['muted']};
}}
"""


def _get_js(dashboard_available: bool, dashboard_path: str) -> str:
    safe = dashboard_path.replace("'", "\\'")
    return f"""
const slides = [...document.querySelectorAll('.slide')];
let idx = 0;
function show(n) {{
  idx = Math.max(0, Math.min(slides.length - 1, n));
  slides.forEach((s, k) => s.classList.toggle('active', k === idx));
  document.getElementById('counter').textContent = (idx + 1) + ' / ' + slides.length;
}}
function fit() {{
  const s = Math.min(innerWidth / 1280, innerHeight / 720);
  document.getElementById('stage').style.transform =
    'translate(-50%, -50%) scale(' + s + ')';
}}
addEventListener('resize', fit);
addEventListener('keydown', (e) => {{
  if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') show(idx + 1);
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') show(idx - 1);
}});
fit();
show(0);
"""


def generate(dashboard_path: str, output_path: Path) -> str:
    """Return the complete presentation HTML.

    dashboard_path is relative to output_path's directory; availability is
    resolved at build time (missing file -> placeholder panel, Task 2).
    """
    dashboard_available = (Path(output_path).parent / dashboard_path).exists()
    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        "<title>Timing the Variance Seller</title>\n"
        f"<style>{_get_css()}</style>\n"
        "</head>\n"
        "<body>\n"
        '<div id="stage">\n'
        f"{_get_slides()}\n"
        "</div>\n"
        '<div id="counter"></div>\n'
        f"<script>{_get_js(dashboard_available, dashboard_path)}</script>\n"
        "</body>\n"
        "</html>\n"
    )
    if "—" in html:
        raise ValueError("em dash (U+2014) found in generated HTML; the deck bans em dashes")
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the desk-pitch presentation HTML")
    parser.add_argument(
        "--dashboard-path",
        default="../../src/data/models/trial_036_drop_vrp_calendar/plots/tournament_dashboard.html",
        help="Dashboard HTML path, relative to the output file's directory",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "presentation.html"),
        help="Output HTML path",
    )
    args = parser.parse_args()
    out = Path(args.output)
    out.write_text(generate(args.dashboard_path, out), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
