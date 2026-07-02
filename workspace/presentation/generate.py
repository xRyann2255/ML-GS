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

EQ_KVAR = (
    r"K_{\mathrm{var}} \;=\; \frac{2}{T}\left[\int_{0}^{F}\frac{P(K)}{K^{2}}\,dK"
    r"\;+\;\int_{F}^{\infty}\frac{C(K)}{K^{2}}\,dK\right]"
)
EQ_QLIKE = (
    r"\mathrm{QLIKE} \;=\; \frac{1}{T}\sum_{t=1}^{T}"
    r"\left[\frac{RV_{t}}{\hat{h}_{t}} - \log\frac{RV_{t}}{\hat{h}_{t}} - 1\right]"
)


def render_equation_svg(latex: str, *, color: str, fontsize: float = 26.0) -> str:
    """Render a LaTeX equation to an inline SVG string via matplotlib mathtext.

    Build-time only; the output HTML has no runtime math dependency.
    """
    import io
    import re

    import matplotlib

    matplotlib.use("Agg")
    # Deterministic ids in the SVG output so rebuilds are byte-stable.
    matplotlib.rcParams["svg.hashsalt"] = "volforecast-deck"
    from matplotlib.figure import Figure

    fig = Figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${latex}$", fontsize=fontsize, color=color,
             math_fontfamily="cm")
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.03,
                transparent=True)
    svg = buf.getvalue().decode("utf-8")
    svg = svg[svg.index("<svg"):]
    # Drop the <metadata> block: it carries a <dc:date> build timestamp that
    # breaks byte-stable rebuilds and adds ~0.5KB of dead weight per equation.
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.S)
    # The SVG backend echoes the source LaTeX in an XML comment; strip it so
    # the deck contains no raw LaTeX (glyphs are already rendered as paths).
    return re.sub(r"<!--.*?-->", "", svg, flags=re.S)


def _equation_block(name: str) -> str:
    latex = {"kvar": EQ_KVAR, "qlike": EQ_QLIKE}[name]
    svg = render_equation_svg(latex, color=THEME["body"])
    return f'<div class="equation" data-eq="{name}">{svg}</div>'


def _svg_defs(uid: str) -> str:
    # ids are namespaced per diagram: url(#...) resolves document-wide in HTML,
    # so duplicate ids would point into another slide's display:none SVG and
    # Chromium then drops the marker/pattern entirely.
    t = THEME
    return (
        "<defs>"
        f'<marker id="arr-{uid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{t["muted"]}"/></marker>'
        f'<pattern id="hatch-{uid}" width="7" height="7" patternTransform="rotate(45)" '
        'patternUnits="userSpaceOnUse">'
        f'<line x1="0" y1="0" x2="0" y2="7" stroke="{t["amber"]}" stroke-width="2" opacity="0.55"/>'
        "</pattern>"
        "</defs>"
    )


def _diagram_block(name: str) -> str:
    fn = {
        "payoff_motif": _diagram_payoff_motif,
        "product_day": _diagram_product_day,
        "architecture": _diagram_architecture,
        "feature_map": _diagram_feature_map,
        "cv_folds": _diagram_cv_folds,
        "beeswarm_guide": _diagram_beeswarm_guide,
        "results_bars": _diagram_results_bars,
    }[name]
    return f'<div class="diagram" data-diagram="{name}">{fn()}</div>'


def _diagram_payoff_motif() -> str:
    # Short-variance payoff vs realized vol: flat premium left, cubic-ish left-tail loss right.
    t = THEME
    return (
        '<svg viewBox="0 0 1280 300" style="position:absolute;left:0;bottom:0;width:1280px;'
        'height:300px;opacity:0.09;pointer-events:none;">'
        f'<path d="M60,80 C400,80 620,84 760,120 C900,158 1050,240 1200,290" '
        f'fill="none" stroke="{t["amber"]}" stroke-width="3"/>'
        f'<line x1="60" y1="150" x2="1200" y2="150" stroke="{t["ink"]}" stroke-width="1"/>'
        "</svg>"
    )


def _diagram_product_day() -> str:
    t = THEME
    # Equity curve: 24 hardcoded points, 100 -> 138 with three drawdown dips.
    # Source: GSVIVS01 shape per spec 3.5 [VERIFY on GS]; dips at COVID-era-free window are illustrative of drawdown DAYS, marked red.
    pts = [(0, 100.0), (1, 101.2), (2, 102.5), (3, 103.1), (4, 104.6), (5, 103.2),
           (6, 105.9), (7, 107.4), (8, 108.8), (9, 107.1), (10, 110.2), (11, 111.9),
           (12, 113.5), (13, 115.2), (14, 113.8), (15, 117.3), (16, 119.4), (17, 121.6),
           (18, 124.1), (19, 126.7), (20, 129.5), (21, 132.4), (22, 135.3), (23, 138.0)]
    dips = [5, 9, 14]
    x0, x1, y_lo, y_hi = 480, 1120, 100.0, 140.0
    top, bot = 30, 210
    def sx(i): return x0 + (x1 - x0) * i / 23
    def sy(v): return bot - (bot - top) * (v - y_lo) / (y_hi - y_lo)
    curve = " ".join(f"{sx(i):.0f},{sy(v):.0f}" for i, v in pts)
    ticks = "".join(
        f'<line x1="{sx(i):.0f}" y1="{sy(pts[i][1]) + 6:.0f}" x2="{sx(i):.0f}" '
        f'y2="{sy(pts[i][1]) + 22:.0f}" stroke="{t["red"]}" stroke-width="3"/>'
        for i in dips
    )
    # Left half: trading-day timeline with three nodes.
    def node(x, label, sub):
        return (
            f'<circle cx="{x}" cy="120" r="7" fill="none" stroke="{t["amber"]}" stroke-width="1.5"/>'
            f'<text x="{x}" y="95" text-anchor="middle" fill="{t["ink"]}" font-size="16">{label}</text>'
            f'<text x="{x}" y="150" text-anchor="middle" fill="{t["muted"]}" font-size="14">{sub}</text>'
        )
    return (
        '<svg viewBox="0 0 1180 252" style="width:1080px;height:231px;">'
        + _svg_defs("pd")
        + f'<line x1="40" y1="120" x2="420" y2="120" stroke="{t["muted"]}" stroke-width="1.5" marker-end="url(#arr-pd)"/>'
        + node(70, "09:30", "sell the strip")
        + node(230, "all day", "delta-hedge")
        + node(390, "16:00", "settle at MOC")
        + f'<polyline points="{curve}" fill="none" stroke="{t["ink"]}" stroke-width="1.5"/>'
        + ticks
        + f'<text x="{x0}" y="240" fill="{t["muted"]}" font-size="14">index level, four years, 100 to 138. '
          f'red ticks: days where realized variance beat the strike</text>'
        + "</svg>"
    )


def _diagram_architecture() -> str:
    t = THEME
    def box(x, y, w, h, title, sub, stroke):
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" '
            f'stroke="{stroke}" stroke-width="1.5"/>'
            f'<text x="{x + w / 2}" y="{y + 30}" text-anchor="middle" fill="{t["ink"]}" font-size="17">{title}</text>'
            f'<text x="{x + w / 2}" y="{y + 54}" text-anchor="middle" fill="{t["muted"]}" font-size="14">{sub}</text>'
        )
    def arrow(x1, y1, x2, y2, label=""):
        lab = (f'<text x="{(x1 + x2) / 2}" y="{y1 - 12}" text-anchor="middle" '
               f'fill="{t["muted"]}" font-size="13">{label}</text>') if label else ""
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["muted"]}" '
                f'stroke-width="1.5" marker-end="url(#arr-arch)"/>' + lab)
    tenor = (
        f'<rect x="820" y="150" width="300" height="100" fill="none" stroke="{t["hairline"]}" stroke-width="1.5"/>'
        f'<text x="970" y="175" text-anchor="middle" fill="{t["amber"]}" font-size="13" letter-spacing="2">TENOR MATCHING</text>'
        f'<text x="970" y="200" text-anchor="middle" fill="{t["body"]}" font-size="14">1-day forecast &#8596; same-day IV</text>'
        f'<text x="970" y="220" text-anchor="middle" fill="{t["body"]}" font-size="14">5-day &#8596; 1-week &#183; 22-day &#8596; 1-month</text>'
    )
    return (
        '<svg viewBox="0 0 1180 270" style="width:1080px;height:247px;">'
        + _svg_defs("arch")
        + box(20, 20, 200, 80, "market inputs", "prices, options, calendar", t["hairline"])
        + arrow(220, 60, 296, 60)
        + box(296, 20, 252, 80, "HAR-IV spine", "4 parameters, most of the forecast", t["amber"])
        + arrow(548, 60, 620, 60, "init_score")
        + box(620, 20, 220, 80, "LightGBM overlay", "learns only the residual", t["amber"])
        + arrow(840, 60, 912, 60)
        + box(912, 20, 220, 80, "forecast", "trained end to end on QLIKE", t["green"])
        + tenor
        + "</svg>"
    )


def _diagram_feature_map() -> str:
    t = THEME
    quads = [
        (20, 20, "PRICE HISTORY", "how volatile we have been:",
         "up-moves, down-moves, jumps"),
        (600, 20, "OPTIONS SURFACE", "what the market pays for future vol:",
         "term slope, skew, vol of vol"),
        (20, 184, "MEASUREMENT QUALITY", "how much of today's reading is noise:",
         "kernel estimates, tick anomalies"),
        (600, 184, "CALENDAR", "what is scheduled:",
         "Fed meetings, payrolls, expiries"),
    ]
    cells = "".join(
        f'<rect x="{x}" y="{y}" width="540" height="144" fill="none" stroke="{t["hairline"]}" stroke-width="1.5"/>'
        f'<text x="{x + 22}" y="{y + 38}" fill="{t["amber"]}" font-size="14" letter-spacing="3">{title}</text>'
        f'<text x="{x + 22}" y="{y + 74}" fill="{t["ink"]}" font-size="16">{line1}</text>'
        f'<text x="{x + 22}" y="{y + 102}" fill="{t["muted2"]}" font-size="16">{line2}</text>'
        for x, y, title, line1, line2 in quads
    )
    return (
        '<svg viewBox="0 0 1180 348" style="width:1080px;height:318px;">'
        + _svg_defs("fm") + cells
        + "</svg>"
    )


def _diagram_cv_folds() -> str:
    t = THEME
    # 4 folds: expanding train bar, hatched purge gap, test bar.
    rows = []
    x0, gap_w, test_w, row_h = 40, 26, 150, 26
    for k in range(4):
        y = 12 + k * (row_h + 10)
        train_w = 300 + k * 150
        rows.append(
            f'<rect x="{x0}" y="{y}" width="{train_w}" height="{row_h}" fill="{t["hairline"]}"/>'
            f'<rect x="{x0 + train_w}" y="{y}" width="{gap_w}" height="{row_h}" fill="url(#hatch-cv)"/>'
            f'<rect x="{x0 + train_w + gap_w}" y="{y}" width="{test_w}" height="{row_h}" '
            f'fill="none" stroke="{t["green"]}" stroke-width="1.5"/>'
        )
    labels = (
        f'<text x="{x0}" y="182" fill="{t["muted"]}" font-size="14">grey: training, always in the past'
        f' &#183; hatched: {NUMBERS["purge_days"]} purged &#183; green: out-of-sample test</text>'
        f'<text x="{x0}" y="206" fill="{t["muted"]}" font-size="14">splits are by DATE across all '
        f'{NUMBERS["n_symbols"]} symbols; the early-stopping split sits behind its own gap</text>'
    )
    return ('<svg viewBox="0 0 1180 216" style="width:1080px;height:198px;">'
            + _svg_defs("cv") + "".join(rows) + labels + "</svg>")


def _diagram_beeswarm_guide() -> str:
    t = THEME
    # Three example feature rows; dot color encodes feature value (blue low, red high).
    import random
    rng = random.Random(7)
    rows = [("feature pushing vol UP when high", 1), ("feature pushing vol DOWN when high", -1),
            ("feature with regime-dependent effect", 0)]
    zero_x = 685  # plot region shifted right to leave a full label gutter
    dots = []
    for r, (_, direction) in enumerate(rows):
        y = 60 + r * 56
        for _ in range(46):
            v = rng.random()
            if direction == 1:
                x = zero_x + (v - 0.5) * 700 * v
            elif direction == -1:
                x = zero_x - (v - 0.5) * 700 * v
            else:
                x = zero_x + (v - 0.5) * 500 * (1 if rng.random() > 0.5 else -1)
            x = max(300, min(1070, x))
            col = f"rgb({int(80 + 175 * v)},{int(120 - 40 * v)},{int(220 - 160 * v)})"
            dots.append(f'<circle cx="{x:.0f}" cy="{y + rng.uniform(-9, 9):.0f}" r="3.4" '
                        f'fill="{col}" opacity="0.85"/>')
    row_labels = "".join(
        f'<text x="272" y="{64 + r * 56}" text-anchor="end" fill="{t["body"]}" font-size="14">{label}</text>'
        for r, (label, _) in enumerate(rows)
    )
    return (
        '<svg viewBox="0 0 1180 240" style="width:1080px;height:220px;">'
        + _svg_defs("bee")
        + f'<line x1="{zero_x}" y1="30" x2="{zero_x}" y2="190" stroke="{t["hairline"]}" stroke-width="1.5"/>'
        + f'<text x="{zero_x}" y="216" text-anchor="middle" fill="{t["muted"]}" font-size="14">'
          "SHAP value: pushes this day's forecast down &#8592; 0 &#8594; up</text>"
        + f'<text x="1160" y="40" text-anchor="end" fill="{t["muted"]}" font-size="13">'
          "dot color = feature value (blue low, red high)</text>"
        + row_labels + "".join(dots)
        + "</svg>"
    )


def _diagram_results_bars() -> str:
    t = THEME
    # Improvement vs HAR-IV baseline. h=22 flipped (linear wins). [VERIFY on GS]
    bars = [
        ("1-day", 10.0, "+10% vs baseline", t["green"]),
        ("5-day", 11.3, "+11% vs baseline", t["green"]),
        ("22-day", -0.4, "linear wins by 0.4%", t["amber"]),
    ]
    x0, zero_y, w, scale = 220, 150, 160, 8.0
    parts = []
    for k, (label, pct, bar_label, color) in enumerate(bars):
        x = x0 + k * 300
        h = abs(pct) * scale
        y = zero_y - h if pct > 0 else zero_y
        parts.append(
            f'<rect x="{x}" y="{y:.0f}" width="{w}" height="{max(h, 4):.0f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + w / 2}" y="{(y - 10) if pct > 0 else (zero_y + h + 24):.0f}" text-anchor="middle" '
            f'fill="{t["ink"]}" font-size="16">{bar_label}</text>'
            f'<text x="{x + w / 2}" y="{zero_y + 50}" text-anchor="middle" fill="{t["muted2"]}" font-size="15">{label}</text>'
        )
    return (
        '<svg viewBox="0 0 1180 240" style="width:1080px;height:220px;">'
        + _svg_defs("rb")
        + f'<line x1="120" y1="{zero_y}" x2="1060" y2="{zero_y}" stroke="{t["hairline"]}" stroke-width="1.5"/>'
        + f'<text x="120" y="24" fill="{t["muted"]}" font-size="14">forecast-loss reduction vs HAR-IV '
          "(QLIKE, five-seed mean; positive = our model better)</text>"
        + "".join(parts)
        + "</svg>"
    )


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
        _diagram_block("payoff_motif")
        + '<p class="subtitle-line">A machine-learned realized-variance forecast as a daily '
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
        + _diagram_block("product_day")
    )
    return _slide("The product and its problem", "GSVIVS01 sells variance every single day", body)


def _slide_03() -> str:
    n = NUMBERS
    body = (
        "<p>At 09:10, before the strip is sold, the model's overnight forecast of "
        "today's realized variance is compared with the strike on offer. Variance "
        "rich: sell as usual. Forecast above the strike: stand aside for the day.</p>"
        + _equation_block("kvar")
        + '<p class="dim">the same OTM-option integral as the VIX, which is why the strike '
        "sits above ATM implied vol: it inherits the skew</p>"
        f'<p class="claim-stat">Annualized Sharpe {n["sharpe_before"]} &rarr; '
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
        + _diagram_block("architecture")
    )
    return _slide("The model", "A linear spine and a tree overlay", body)


def _slide_05() -> str:
    body = (
        _diagram_block("feature_map")
        + "<p>About 128 inputs once every series also contributes its daily change "
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
        + _diagram_block("cv_folds")
        + _equation_block("qlike")
        + "<p class=\"dim\">proportional error, so calm markets count as much as crises, and "
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
        + _diagram_block("beeswarm_guide")
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
        + _diagram_block("results_bars")
        + f"<p class=\"dim\">And the loss function is the product: the identical model trained on "
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
p.dim {{ color: {t['muted2']}; font-size: 18px; }}
p.claim-stat {{
  font-family: {t['serif']}; font-size: 30px; color: {t['ink']};
  margin-top: 34px; letter-spacing: 0.3px;
}}
.g {{ color: {t['green']}; }}
.a {{ color: {t['amber']}; }}
.footer-band {{
  position: absolute; left: 96px; right: 96px; bottom: 56px;
  border-top: 1px solid {t['hairline']}; padding-top: 18px;
  display: flex; justify-content: space-between;
  font-size: 17px; color: {t['muted']};
}}
.title-slide h1 {{ font-size: 64px; margin-top: 140px; }}
.title-slide .subtitle-line {{ font-size: 22px; color: {t['muted2']}; max-width: 640px; }}
.title-slide .byline {{ position: absolute; bottom: 72px; font-size: 16px; color: {t['muted']}; }}
.diagram {{ margin: 18px 0; }}
.equation {{ margin: 14px 0; }}
.equation svg {{ height: 72px; width: auto; }}
.equation[data-eq="kvar"] {{ margin: 34px 0 28px; }}
.equation[data-eq="kvar"] svg {{ height: 80px; }}
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
