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
    body = (
        '<div class="diagram" data-diagram="payoff_motif"></div>'
        '<p class="subtitle-line">A machine-learned realized-variance forecast as a daily '
        "trade / stand-aside signal for the GSVIVS01 index</p>"
        '<p class="byline">Ryan &middot; July 2026</p>'
    )
    return _slide("ML Vol Forecasting", "Timing the Variance Seller", body, "title-slide")


def _slide_02() -> str:
    n = NUMBERS
    body = (
        "<p>Each morning it sells a strip of same-day SPX options that replicates a "
        "variance swap, delta-hedges through the day, and settles at the close. "
        f"Index level {n['index_path']} in four years, roughly {n['index_per_year']}.</p>"
        "<p>The gains are steady. The losses arrive on the few days when realized "
        "variance exceeds the strike it sold, and the index has no opinion about "
        "when those days come.</p>"
        '<div class="diagram" data-diagram="product_day"></div>'
    )
    return _slide("The product and its problem", "GSVIVS01 sells variance every single day", body)


def _slide_03() -> str:
    n = NUMBERS
    body = (
        "<p>At 09:10, before the strip is sold, the model's overnight forecast of "
        "today's realized variance is compared with the strike on offer. Variance "
        "rich: sell as usual. Forecast above the strike: stand aside for the day.</p>"
        '<div class="equation" data-eq="kvar"></div>'
        '<p class="dim">the same OTM-option integral as the VIX, which is why the strike '
        "sits above ATM implied vol: it inherits the skew</p>"
        f'<p>Annualized Sharpe {n["sharpe_before"]} &rarr; '
        f'<span class="g">{n["sharpe_after"]}</span>, backtest {n["backtest_window"]}</p>'
    )
    return _slide("The claim", "Every morning: compare the forecast to the strike", body)


def _slide_04() -> str:
    body = (
        "<p>The spine is HAR-IV: a four-parameter regression on today's, last week's "
        "and last month's realized variance, plus implied vol. It alone carries most "
        "of the forecast.</p>"
        "<p>LightGBM starts from the spine's prediction and learns only what is left "
        "over, trained end to end on the same loss we judge it by.</p>"
        "<p>Each horizon reads the option tenor that expires with it: the 1-day "
        "forecast uses same-day IV, the 5-day uses 1-week, the 22-day uses 1-month.</p>"
        '<div class="diagram" data-diagram="architecture"></div>'
    )
    return _slide("The model", "A linear spine and a tree overlay", body)


def _slide_05() -> str:
    n = NUMBERS
    body = (
        '<div class="diagram" data-diagram="feature_map"></div>'
        "<p>About 128 inputs once every series also contributes its daily change "
        "and how unusual it is against its own recent history.</p>"
    )
    return _slide("The features", "Four things the market tells you", body)


def _slide_06() -> str:
    n = NUMBERS
    body = (
        f"<p>Training always ends {n['purge_days']} before testing begins, on every fold, "
        "because the target itself overlaps days. Splits are by date across all "
        f"{n['n_symbols']} symbols, so no symbol leaks the future to another. Even the "
        "early-stopping check sits behind its own gap.</p>"
        '<div class="diagram" data-diagram="cv_folds"></div>'
        '<div class="equation" data-eq="qlike"></div>'
        "<p class=\"dim\">proportional error, so calm markets count as much as crises, and "
        "underprediction hurts more, as it should for an option seller. "
        f"One lucky seed looked {n['seed_inflation']}; every headline number is a five-seed mean.</p>"
    )
    return _slide("Why trust the number", "Walk-forward with a moat, five seeds", body)


def _slide_07() -> str:
    body = (
        "<p>SHAP splits every individual forecast into named feature contributions "
        "that sum exactly to the prediction, so we can audit what the trees add on "
        "top of the linear spine.</p>"
        "<p>What tops the list: the implied-to-realized relationship changing with "
        "regime, extremes of the variance risk premium, Fed-meeting proximity, and "
        "unusually-high-against-own-history flags.</p>"
        '<div class="diagram" data-diagram="beeswarm_guide"></div>'
    )
    return _slide("What it learned", "Everything it learned has a name you know", body)


def _slide_08() -> str:
    n = NUMBERS
    body = (
        f"<p><span class=\"a\">1-day ahead</span>: <span class=\"g\">{n['h1_improvement']}</span> "
        "than the strongest linear baseline, statistically significant. "
        f"<span class=\"a\">5-day</span>: <span class=\"g\">{n['h5_improvement']}</span>, significant. "
        '<span class="a">22-day</span>: the four-parameter linear model wins; at a monthly '
        "horizon the option market has already done the work.</p>"
        '<div class="diagram" data-diagram="results_bars"></div>'
        f"<p class=\"dim\">And the loss function is the product: the identical model trained on "
        f"MSE instead of QLIKE trades at Sharpe {n['mse_sharpe']}.</p>"
    )
    return _slide("Results", "Where it wins, and where it honestly doesn't", body)


def _slide_09() -> str:
    n = NUMBERS
    body = (
        "<p>The backtest strike is a proxy from the index's own marks; it tracks the "
        f"real strike almost perfectly (correlation {n['kvar_proxy_corr']}) and the "
        "production feed exists. The edge is concentrated in "
        f"{n['transitions_per_year']} signal changes a year, so each call matters. "
        "COVID only enters training from 2022 onward, by construction.</p>"
        '<div class="footer-band">'
        f"<span>Sharpe <span class=\"g\">{n['sharpe_after']}</span> with the signal vs "
        f"{n['sharpe_before']} without</span>"
        f"<span>stands aside on <span class=\"g\">{n['stand_aside_share']}</span> of days</span>"
        f"<span><span class=\"g\">{n['precision']}</span> stand-asides preceded genuine drawdowns</span>"
        "</div>"
    )
    return _slide("The fine print, and the point", "Three caveats, three numbers", body)


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
.title-slide h1 {{ font-size: 64px; margin-top: 140px; }}
.title-slide .subtitle-line {{ font-size: 22px; color: {t['muted2']}; }}
.title-slide .byline {{ position: absolute; bottom: 72px; font-size: 16px; color: {t['muted']}; }}
.diagram {{ margin: 20px 0; }}
.equation {{ margin: 18px 0; }}
#counter {{
  position: fixed; right: 18px; bottom: 12px; z-index: 30;
  font-family: {t['sans']}; font-size: 12px; color: {t['muted']};
}}
#dashboard-toggle {{
  position: fixed; top: 14px; right: 18px; z-index: 40;
  background: transparent; color: {t['muted']};
  border: 1px solid {t['hairline']}; padding: 6px 14px;
  font-family: {t['sans']}; font-size: 12px; letter-spacing: 1px;
  cursor: pointer;
}}
#dashboard-toggle:hover {{ color: {t['amber']}; border-color: {t['amber']}; }}
#dashboard-overlay {{
  position: fixed; inset: 0; z-index: 35; display: none; background: {t['bg']};
}}
#dashboard-overlay.visible {{ display: block; }}
#dashboard-frame {{ width: 100%; height: 100%; border: 0; }}
#dashboard-placeholder {{
  height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px;
  color: {t['muted']}; font-size: 16px;
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
  else if (e.key === 'd' || e.key === 'D') toggleDashboard();
  else if (e.key === 'Escape' && dashVisible) toggleDashboard();
}});
fit();
show(0);
const DASHBOARD_PATH = '{safe}';
const DASHBOARD_AVAILABLE = {str(dashboard_available).lower()};
let dashVisible = false;
function toggleDashboard() {{
  dashVisible = !dashVisible;
  const overlay = document.getElementById('dashboard-overlay');
  if (dashVisible) {{
    const frame = document.getElementById('dashboard-frame');
    if (frame && !frame.getAttribute('src')) frame.setAttribute('src', DASHBOARD_PATH);
    overlay.classList.add('visible');
  }} else {{
    overlay.classList.remove('visible');
  }}
}}
"""


def generate(dashboard_path: str, output_path: Path) -> str:
    """Return the complete presentation HTML.

    dashboard_path is relative to output_path's directory; availability is
    resolved at build time (missing file -> placeholder panel, Task 2).
    """
    dashboard_available = (Path(output_path).parent / dashboard_path).exists()
    if dashboard_available:
        overlay_inner = '<iframe id="dashboard-frame" loading="lazy"></iframe>'
    else:
        overlay_inner = (
            '<div id="dashboard-placeholder">'
            "<div>Dashboard not found at build time.</div>"
            f"<div>Expected (relative to this file): {dashboard_path}</div>"
            "<div>Rebuild with --dashboard-path once the dashboard exists.</div>"
            "</div>"
        )
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
        '<button id="dashboard-toggle" onclick="toggleDashboard()">Dashboard [D]</button>\n'
        f'<div id="dashboard-overlay">{overlay_inner}</div>\n'
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
