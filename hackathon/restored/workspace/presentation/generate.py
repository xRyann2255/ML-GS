"""Desk-pitch deck generator: Timing the Variance Seller.

Builds ONE self-contained HTML file (no CDN, no network requests) for the
GSVIVS01 presentation. 11 slides, dark serif theme, dashboard iframe toggle.

Regenerate (GS):      ./vol present --dashboard-path '<rel path from output HTML>'
Regenerate (local):   cd ml-vol-estimator && ./vol shell ../../workspace/presentation/generate.py \
                          --dashboard-path tournament_dashboard_mock.html

Canonical numbers live in NUMBERS below and carry [VERIFY on GS] flags from
the spec (docs/superpowers/specs/2026-07-02-presentation-rewrite-design.md 3.5).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from datetime import date
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

# Single source of truth for every number said or shown.
# Source: src/data/models/trial_067_xgboost_all_layers (metrics.json + dashboard)
NUMBERS = {
    "sharpe_before": "2.09",
    "sharpe_after": "2.45",
    "backtest_window": "May 2022 to Jun 2026",
    "stand_aside_share": "33%",
    "stand_aside_precision": "41% smaller max drawdown",
    "transitions_per_year": "about 120",
    "index_path": "100 to 138",
    "index_per_year": "10.1 points a year",
    "h1_improvement": "about 13% lower forecast loss",
    "h5_improvement": "about 6% lower",
    "seed_inflation": "6% better than the truth",
    "mse_sharpe": "2.32",
    "qlike_sharpe": "2.45",
    "n_symbols": "21",
    "n_features": "about 128",
    "purge_days": "ten trading days",
    "kvar_proxy_corr": "above 0.99",
}


def _parse_gsvivs_traces(html_text: str) -> dict | None:
    """Extract the gsvivsPnlTraces JSON blob from a tournament dashboard HTML.

    Coupled to the literal `const gsvivsPnlTraces` in the dashboard template
    (src/volforecast/visualization/templates/tournament_dashboard.html). Any
    failure returns None and the caller falls back to the synthetic series.
    """
    marker = "const gsvivsPnlTraces"
    i = html_text.find(marker)
    if i == -1:
        return None
    j = html_text.find("{", i)
    if j == -1:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(html_text[j:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _select_index_trace(traces_by_h: dict) -> dict | None:
    """Pick the raw-index trace from the h=1 list.

    [baseline] always_long holds the index every day (_signal_y all +1), so
    its wealth curve IS the GSVIVS01 index normalized to its first date.
    JSON keys are strings because the dashboard json.dumps's an int-keyed dict.
    """
    h_traces = traces_by_h.get("1") or traces_by_h.get(1) or []
    for tr in h_traces:
        sig = tr.get("_signal_y") or []
        if "[baseline]" in str(tr.get("name", "")) and sig and all(s == 1.0 for s in sig):
            return tr
    for tr in h_traces:
        if "always_long" in str(tr.get("name", "")):
            return tr
    return None


def _extract_index_series(html_text: str) -> list[tuple[str, float]] | None:
    """Return [(iso_date, index_level)] rescaled so the series starts at 100."""
    traces = _parse_gsvivs_traces(html_text)
    if not traces:
        return None
    tr = _select_index_trace(traces)
    if tr is None:
        return None
    xs, ys = tr.get("x") or [], tr.get("y") or []
    if len(xs) != len(ys) or len(xs) < 2 or not ys[0]:
        return None
    # Normalize/validate every point: dates may carry a time suffix (plotly/
    # pandas datetime64 axes serialize as "YYYY-MM-DDTHH:MM:SS") and levels
    # may be non-numeric; any parse failure means silent synthetic fallback,
    # never a crashed build.
    try:
        y0 = float(ys[0])
        if not (math.isfinite(y0) and y0 > 0):
            return None
        scale = 100.0 / y0
    except (ValueError, TypeError):
        return None
    out: list[tuple[str, float]] = []
    prev_ord = None
    for d, v in zip(xs, ys):
        ds = str(d)[:10]
        try:
            d_ord = date.fromisoformat(ds).toordinal()
            lv = float(v) * scale
        except (ValueError, TypeError):
            return None
        if not (math.isfinite(lv) and lv > 0):
            return None
        if prev_ord is not None and d_ord <= prev_ord:
            return None
        prev_ord = d_ord
        out.append((ds, lv))
    return out


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
        "architecture": _diagram_architecture,
        "feature_map": _diagram_feature_map,
        "feature_stack": _diagram_feature_stack,
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


# Fallback series for local builds where the dashboard is a stub: the same
# 24-point 100->136 shape the deck used before real data, with plausible dates.
SYNTHETIC_INDEX: list[tuple[str, float]] = [
    ("2022-07-01", 100.0), ("2022-09-01", 101.0), ("2022-11-01", 102.1),
    ("2023-01-02", 102.7), ("2023-03-01", 104.0), ("2023-05-01", 102.7),
    ("2023-07-03", 105.2), ("2023-09-01", 106.6), ("2023-11-01", 107.9),
    ("2024-01-02", 106.4), ("2024-03-01", 109.3), ("2024-05-01", 110.9),
    ("2024-07-01", 112.3), ("2024-09-02", 113.9), ("2024-11-01", 112.5),
    ("2025-01-02", 115.8), ("2025-03-03", 117.8), ("2025-05-01", 119.9),
    ("2025-07-01", 122.2), ("2025-09-01", 124.6), ("2025-11-03", 127.2),
    ("2026-01-02", 129.9), ("2026-03-02", 132.8), ("2026-05-01", 136.0),
]

MAX_RED_TICKS = 15


def _diagram_product_day(series: list[tuple[str, float]] | None) -> str:
    """Slide-2 chart: trading-day timeline strip + GSVIVS01 index with axes.

    series is [(iso_date, level)] from the real dashboard, or None to render
    the synthetic fallback through the same axis machinery.
    """
    t = THEME
    is_real = series is not None
    if series is None:
        series = SYNTHETIC_INDEX

    days = [date.fromisoformat(d).toordinal() for d, _ in series]
    vals = [v for _, v in series]
    d_lo, d_hi = days[0], days[-1]
    y_lo = min(100.0, 10.0 * math.floor(min(vals) / 10.0))
    y_hi = max(140.0, 10.0 * math.ceil(max(vals) / 10.0))

    # top=104 clears the timeline strip and the axis title; bot=304 uses the
    # slide's spare lower space for a taller plot (real data is 950+ points).
    x0, x1, top, bot = 70, 1130, 104, 304

    def sx(o: int) -> float:
        return x0 + (x1 - x0) * (o - d_lo) / (d_hi - d_lo)

    def sy(v: float) -> float:
        return bot - (bot - top) * (v - y_lo) / (y_hi - y_lo)

    # Y axis: gridlines + labels every 10 index points
    grid = "".join(
        f'<line x1="{x0}" y1="{sy(gv):.0f}" x2="{x1}" y2="{sy(gv):.0f}" '
        f'stroke="{t["hairline"]}" stroke-width="1"/>'
        f'<text x="{x0 - 12}" y="{sy(gv) + 5:.0f}" text-anchor="end" '
        f'fill="{t["muted"]}" font-size="13">{gv:.0f}</text>'
        for gv in range(int(y_lo), int(y_hi) + 1, 10)
    )
    # anchored start at the left edge: right-anchoring at the label gutter
    # (x0 - 12) clips the first glyphs at the viewBox boundary. top - 16 keeps
    # clear vertical gaps to the timeline subs above and the y labels below.
    axis_title = (f'<text x="8" y="{top - 16}" text-anchor="start" '
                  f'fill="{t["muted"]}" font-size="13">index level</text>')

    # X axis: a tick at Jan 1 of every year inside the span
    year_ticks = []
    for yr in range(date.fromordinal(d_lo).year + 1, date.fromordinal(d_hi).year + 1):
        o = date(yr, 1, 1).toordinal()
        if d_lo <= o <= d_hi:
            year_ticks.append(
                f'<line x1="{sx(o):.0f}" y1="{bot}" x2="{sx(o):.0f}" y2="{bot + 8}" '
                f'stroke="{t["muted"]}" stroke-width="1"/>'
                # bot + 26 sits clear below the axis; caption is further down at y=358
                f'<text x="{sx(o):.0f}" y="{bot + 26}" text-anchor="middle" '
                f'fill="{t["muted"]}" font-size="13">{yr}</text>'
            )
    x_axis = (f'<line x1="{x0}" y1="{bot}" x2="{x1}" y2="{bot}" '
              f'stroke="{t["muted"]}" stroke-width="1"/>' + "".join(year_ticks))

    curve = " ".join(f"{sx(o):.1f},{sy(v):.1f}" for o, v in zip(days, vals))

    # Red ticks: the worst daily-return days (all-negative, capped for legibility)
    rets = [(i, vals[i] / vals[i - 1] - 1.0) for i in range(1, len(vals))]
    negative = sorted((p for p in rets if p[1] < 0), key=lambda p: p[1])
    worst = negative[: min(MAX_RED_TICKS, len(negative))]
    ticks = "".join(
        f'<line x1="{sx(days[i]):.0f}" y1="{sy(vals[i]) + 5:.0f}" '
        f'x2="{sx(days[i]):.0f}" y2="{sy(vals[i]) + 19:.0f}" '
        f'stroke="{t["red"]}" stroke-width="2.5"/>'
        for i, _ in worst
    )

    # Trading-day timeline, compressed to a strip above the chart
    def node(x: int, label: str, sub: str) -> str:
        return (
            f'<circle cx="{x}" cy="32" r="6" fill="none" stroke="{t["amber"]}" stroke-width="1.5"/>'
            f'<text x="{x}" y="14" text-anchor="middle" fill="{t["ink"]}" font-size="15">{label}</text>'
            f'<text x="{x}" y="56" text-anchor="middle" fill="{t["muted"]}" font-size="13">{sub}</text>'
        )
    timeline = (
        f'<line x1="40" y1="32" x2="640" y2="32" stroke="{t["muted"]}" '
        f'stroke-width="1.5" marker-end="url(#arr-pd)"/>'
        + node(95, "09:30", "sell the strip")
        + node(330, "all day", "delta-hedge")
        + node(565, "16:00", "settle at MOC")
    )

    note = "" if is_real else " (illustrative shape)"
    caption = (
        f'<text x="{x0}" y="358" fill="{t["muted"]}" font-size="14">'
        f'GSVIVS01 index level{note}, {series[0][0][:4]} to {series[-1][0][:4]}, '
        f'{vals[0]:.0f} to {vals[-1]:.0f}. red ticks: the {len(worst)} worst days, '
        f'where realized variance beat the strike</text>'
    )

    return (
        '<svg viewBox="0 0 1180 372" style="width:1000px;height:315px;">'
        + _svg_defs("pd") + timeline + grid + axis_title + x_axis
        + f'<polyline points="{curve}" fill="none" stroke="{t["ink"]}" stroke-width="1.5"/>'
        + ticks + caption
        + "</svg>"
    )


def _apply_series_numbers(series: list[tuple[str, float]]) -> None:
    """Overwrite NUMBERS entries derived from the real index series."""
    (d0, y0), (d1, y1) = series[0], series[-1]
    span_days = date.fromisoformat(d1).toordinal() - date.fromisoformat(d0).toordinal()
    NUMBERS["index_path"] = f"{y0:.0f} to {y1:.0f}"
    if span_days > 0:
        per_year = (y1 - y0) / (span_days / 365.25)
        NUMBERS["index_per_year"] = f"{per_year:.1f} points a year"


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
        + box(620, 20, 220, 80, "XGBoost overlay", "learns only the residual", t["amber"])
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


def _diagram_feature_stack() -> str:
    """Slide-6 diagram: Layer 1's RV decomposition (left) + layer stack (right)."""
    t = THEME
    x0, w, h = 40, 560, 34
    cont_w = int(w * 0.78)   # continuous share of the example day
    rsn_w = int(w * 0.58)    # down-semivariance share

    def outline(x: float, y: float, width: float) -> str:
        return (f'<rect x="{x}" y="{y}" width="{width}" height="{h}" fill="none" '
                f'stroke="{t["hairline"]}" stroke-width="1.5"/>')

    def txt(x: float, y: float, s: str, color: str, size: int = 14,
            anchor: str = "start") -> str:
        return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" '
                f'font-size="{size}">{s}</text>')

    def arrow_down(x: float, y1: float, y2: float) -> str:
        return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{t["muted"]}" '
                f'stroke-width="1.5" marker-end="url(#arr-fs)"/>')

    left = (
        outline(x0, 20, w)
        + txt(x0 + w / 2, 42, "one day&#39;s realized variance (RV)", t["ink"], 15, "middle")
        + arrow_down(x0 + w / 2, 56, 82)
        + txt(x0 + w / 2 + 12, 74, "how did it arrive?", t["muted"], 13)
        + f'<rect x="{x0}" y="88" width="{cont_w}" height="{h}" fill="{t["hairline"]}"/>'
        + f'<rect x="{x0 + cont_w}" y="88" width="{w - cont_w}" height="{h}" fill="url(#hatch-fs)"/>'
        + outline(x0, 88, w)
        + txt(x0 + 14, 110, "continuous (bipower variation)", t["body"])
        + txt(x0 + w + 12, 110, "jump", t["amber"])
        + arrow_down(x0 + w / 2, 124, 150)
        + txt(x0 + w / 2 + 12, 142, "which direction?", t["muted"], 13)
        + f'<rect x="{x0}" y="156" width="{rsn_w}" height="{h}" fill="{t["red"]}" opacity="0.4"/>'
        + f'<rect x="{x0 + rsn_w}" y="156" width="{w - rsn_w}" height="{h}" fill="{t["green"]}" opacity="0.4"/>'
        + outline(x0, 156, w)
        + txt(x0 + 14, 178, "down-move semivariance", t["ink"])
        + txt(x0 + rsn_w + 14, 178, "up-move", t["ink"])
        + txt(x0, 216, "signed jump = up minus down &#183; jump days flagged by a formal "
                       "statistical test, not a threshold", t["muted"], 13)
        + txt(x0, 244, "continuous vol mean-reverts and forecasts well; jumps do not.",
              t["body"])
        + txt(x0, 266, "separating them keeps the persistent part clean.", t["body"])
    )

    rx, rw = 660, 480

    def layer_box(y: float, tag: str, line: str) -> str:
        return (
            f'<rect x="{rx}" y="{y}" width="{rw}" height="70" fill="none" '
            f'stroke="{t["hairline"]}" stroke-width="1.5"/>'
            + txt(rx + 18, y + 28, tag, t["amber"], 13)
            + txt(rx + 18, y + 52, line, t["muted2"], 14)
        )

    right = (
        layer_box(20, "LAYER 0 &#183; HAR CORE + MEASUREMENT QUALITY",
                  "log RV daily, weekly, monthly &#183; realized quarticity: today&#39;s error bar")
        + layer_box(104, "LAYER 1 &#183; ASYMMETRY",
                    "the split at left, taken at daily and weekly lags")
        + layer_box(188, "LAYER 2 &#183; OPTIONS-IMPLIED",
                    "term slope, skew, vol of vol, variance risk premium")
        + txt(rx, 286, "layers 3 to 5 add microstructure, cross-asset spillovers and "
                       "the calendar", t["muted"], 13)
    )

    return (
        '<svg viewBox="0 0 1180 300" style="width:1080px;height:275px;">'
        + _svg_defs("fs") + left + right
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
    # Improvement vs HAR-IV baseline. h=22 flipped (linear wins).
    # Source: trial_067_xgboost_all_layers/metrics.json
    bars = [
        ("1-day", 13.3, "+13% vs baseline", t["green"]),
        ("5-day", 5.7, "+6% vs baseline", t["green"]),
        ("22-day", -1.1, "linear wins by 1%", t["amber"]),
    ]
    x0, zero_y, w, scale = 220, 180, 160, 8.0
    parts = []
    for k, (label, pct, bar_label, color) in enumerate(bars):
        x = x0 + k * 300
        h = abs(pct) * scale
        y = zero_y - h if pct > 0 else zero_y
        parts.append(
            f'<rect x="{x}" y="{y:.0f}" width="{w}" height="{max(h, 4):.0f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + w / 2}" y="{(y - 14) if pct > 0 else (zero_y + h + 24):.0f}" text-anchor="middle" '
            f'fill="{t["ink"]}" font-size="16">{bar_label}</text>'
            f'<text x="{x + w / 2}" y="{zero_y + 56}" text-anchor="middle" fill="{t["muted2"]}" font-size="15">{label}</text>'
        )
    return (
        '<svg viewBox="0 0 1180 280" style="width:1080px;height:256px;">'
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


def _slide_title() -> str:
    body = (
        _diagram_block("payoff_motif")
        + '<p class="subtitle-line">A machine-learned realized-variance forecast as a daily '
        "trade / stand-aside signal for the GSVIVS01 index</p>"
        '<p class="byline">Ryan &middot; July 2026</p>'
    )
    return _slide("ML Vol Forecasting", "Timing the Variance Seller", body, "title-slide")


def _slide_product(index_series: list[tuple[str, float]] | None = None) -> str:
    n = NUMBERS
    body = (
        "<p>Each morning it sells a strip of same-day SPX options that replicates a "
        "variance swap, delta-hedges through the day, and settles at the close. "
        f"Index level {n['index_path']} in four years, roughly {n['index_per_year']}.</p>"
        "<p>The gains are steady. The losses arrive on the few days when realized "
        "variance exceeds the strike it sold, and the index has no opinion about "
        "when those days come.</p>"
        + f'<div class="diagram" data-diagram="product_day">{_diagram_product_day(index_series)}</div>'
    )
    return _slide("The product and its problem", "GSVIVS01 sells variance every single day", body)


def _slide_claim() -> str:
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


def _slide_model() -> str:
    body = (
        "<p>The spine is HAR-IV: a four-parameter regression on today's, last week's "
        "and last month's realized variance, plus implied vol. It alone carries most "
        "of the forecast.</p>"
        "<p>XGBoost starts from the spine's prediction and learns only what is left "
        "over, trained end to end on the same loss we judge it by.</p>"
        "<p>Each horizon reads the option tenor that expires with it: the 1-day "
        "forecast uses same-day IV, the 5-day uses 1-week, the 22-day uses 1-month.</p>"
        + _diagram_block("architecture")
    )
    return _slide("The model", "A linear spine and a tree overlay", body)


def _slide_families() -> str:
    body = (
        _diagram_block("feature_map")
        + f"<p>{NUMBERS['n_features'].capitalize()} inputs, once every series also contributes its daily change "
        "and how unusual it is against its own recent history.</p>"
    )
    return _slide("The features", "Four things the market tells you", body)


def _slide_feature_stack() -> str:
    body = (
        "<p>Those four families are built as numbered layers, and the first three "
        "do most of the work. Variance that arrives smoothly is not the same signal "
        "as variance that arrives in jumps, so we split the two parts.</p>"
        + _diagram_block("feature_stack")
    )
    return _slide("The features, up close", "Layers 0, 1, 2: split the jumps from the flow", body)


def _slide_validation() -> str:
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


def _slide_learned() -> str:
    body = (
        "<p>SHAP splits every individual forecast into named feature contributions "
        "that sum exactly to the prediction, so we can audit what the trees add on "
        "top of the linear spine.</p>"
        "<p>What tops the list: the implied-to-realized relationship changing with "
        "regime, extremes of the variance risk premium, Fed-meeting proximity, and "
        "flags for readings unusually high against their own history.</p>"
        + _diagram_block("beeswarm_guide")
    )
    return _slide("What it learned", "Making the black-box interpretable", body)


def _slide_results() -> str:
    n = NUMBERS
    body = (
        f"<p><span class=\"a\">1-day ahead</span>: <span class=\"g\">{n['h1_improvement']}</span> "
        "than the strongest linear baseline, statistically significant. "
        f"<span class=\"a\">5-day</span>: <span class=\"g\">{n['h5_improvement']}</span>, significant. "
        '<span class="a">22-day</span>: the four-parameter linear model wins; at a monthly '
        "horizon the option market has already done the work.</p>"
        + _diagram_block("results_bars")
        + f"<p class=\"dim\">Loss function matters: same model trained on MSE trades at Sharpe "
        f"{n['mse_sharpe']} vs {n['qlike_sharpe']} for QLIKE (3-seed means, identical "
        "features and CV). QLIKE penalizes underprediction more than overprediction, "
        "is scale-invariant across regimes, and its rankings are robust to noise in the "
        "realized-variance proxy (Patton 2011).</p>"
    )
    return _slide("Results", "Where it wins, and where it doesn't", body)


def _stat_cell(pre: str, num: str, label: str) -> str:
    # Visible copy is frozen: pre + num + label must concatenate to the
    # user-approved stat line, in reading order (top to bottom).
    return (
        '<div class="stat">'
        f'<div class="stat-pre">{pre}</div>'
        f'<div class="stat-num g">{num}</div>'
        f'<div class="stat-label">{label}</div>'
        "</div>"
    )


def _slide_close() -> str:
    n = NUMBERS
    body = (
        '<div class="stat-row">'
        + _stat_cell("Sharpe", n["sharpe_after"],
                     f"with the signal vs {n['sharpe_before']} without")
        + _stat_cell("stands aside on", n["stand_aside_share"], "of days")
        + _stat_cell("max drawdown reduction", "41%", "peak-to-trough vs always-sell")
        + "</div>"
        + '<p class="dim">Out of sample, purged, five-seeded. No cherry picks.</p>'
    )
    return _slide("The point", "Three numbers", body)


def _slide_next() -> str:
    n = NUMBERS
    cells = [
        ("Regime detection", "hidden Markov models to name the market state",
         "calm, stressed, transitioning, learned from the data"),
        ("Cross-asset spillovers",
         f"graph neural networks across the {n['n_symbols']}-symbol panel",
         "one name's shock informs its neighbours' forecasts"),
        ("Sentiment", "the input family the model doesn't read yet",
         "news flow scored before the calendar knows"),
        ("Sequence models", "LSTMs read the path directly",
         "instead of hand-built lags and averages"),
        ("Regime-routed ensembles", "a different model for each regime",
         "the detector above decides which one speaks"),
        ("Your strategy", "the forecast is not specific to GSVIVS01",
         "if it's directly applicable to another STS strategy, reach out"),
    ]
    grid = "".join(
        '<div class="next-cell">'
        f'<div class="next-label">{label}</div>'
        f'<div class="next-line">{line}</div>'
        f'<div class="next-sub">{sub}</div>'
        "</div>"
        for label, line, sub in cells
    )
    body = (
        f'<div class="next-grid">{grid}</div>'
        '<p class="next-cta">message me on Teams if you\'d like to learn more, '
        "or just want a chat :)</p>"
    )
    return _slide("Next steps", "Where this goes next", body)


def _get_slides(index_series: list[tuple[str, float]] | None = None) -> str:
    slides = [
        _slide_title(),
        _slide_product(index_series),
        _slide_claim(),
        _slide_model(),
        _slide_families(),
        _slide_feature_stack(),
        _slide_validation(),
        _slide_learned(),
        _slide_results(),
        _slide_close(),
        _slide_next(),
    ]
    return "\n\n".join(slides)


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
.stat-row {{
  position: absolute; left: 96px; right: 96px; top: 430px;
  border-top: 1px solid {t['hairline']}; padding-top: 38px;
  display: flex; gap: 56px;
}}
.stat {{ flex: 1; }}
.stat-pre {{ font-size: 16px; color: {t['muted']}; min-height: 24px; margin-bottom: 8px; }}
.stat-num {{ font-family: {t['serif']}; font-size: 54px; line-height: 1.05; margin-bottom: 12px; }}
.stat-label {{ font-size: 16px; color: {t['muted']}; line-height: 1.5; max-width: 340px; }}
.title-slide h1 {{ font-size: 64px; margin-top: 140px; }}
.title-slide .subtitle-line {{ font-size: 22px; color: {t['muted2']}; max-width: 640px; }}
.title-slide .byline {{ position: absolute; bottom: 72px; font-size: 16px; color: {t['muted']}; }}
.next-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 6px;
}}
.next-cell {{ border: 1px solid {t['hairline']}; padding: 18px 22px; }}
.next-label {{
  font-size: 13px; letter-spacing: 3px; text-transform: uppercase;
  color: {t['amber']}; margin-bottom: 10px;
}}
.next-line {{ font-size: 17px; color: {t['ink']}; margin-bottom: 6px; }}
.next-sub {{ font-size: 15px; color: {t['muted2']}; }}
.next-cta {{
  font-family: {t['serif']}; font-size: 18px; color: {t['muted2']};
  margin-top: 26px; letter-spacing: 0.3px;
}}
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


def _get_js(dashboard_available: bool, dashboard_path: str, dashboard_hash: str = "") -> str:
    # json.dumps supplies the quotes and escapes backslashes, so Windows-style
    # paths cannot inject JS escape sequences into the string literal.
    # Cache-busting: append build-time hash as query param so the browser
    # always fetches a fresh copy after a rebuild.
    bust_path = dashboard_path + (f"?_={dashboard_hash}" if dashboard_hash else "")
    safe = json.dumps(bust_path)
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
const DASHBOARD_PATH = {safe};
let dashVisible = false;
function toggleDashboard() {{
  dashVisible = !dashVisible;
  const overlay = document.getElementById('dashboard-overlay');
  if (dashVisible) {{
    const frame = document.getElementById('dashboard-frame');
    if (frame && !frame.getAttribute('src')) {{
      frame.setAttribute('src', DASHBOARD_PATH);
      frame.onerror = showDashboardError;
      frame.addEventListener('load', function() {{
        try {{ frame.contentDocument; }} catch(e) {{ showDashboardError(); }}
      }});
    }}
    overlay.classList.add('visible');
  }} else {{
    overlay.classList.remove('visible');
  }}
}}
function showDashboardError() {{
  const overlay = document.getElementById('dashboard-overlay');
  overlay.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;'
    + 'height:100%;color:#e8e4da;font-family:Georgia,serif;text-align:center;padding:2rem;">'
    + '<div><h2 style="color:#e8b339;margin-bottom:1rem;">Dashboard not found</h2>'
    + '<p style="max-width:600px;line-height:1.6;">Download <code>tournament_dashboard.html</code> '
    + 'from JupyterHub and place it in the <strong>same folder</strong> as this presentation file.</p>'
    + '<p style="margin-top:1rem;opacity:0.6;">Press D or Escape to close this overlay.</p></div></div>';
}}
// Detect iframe load failure (file:// protocol won't trigger onerror reliably)
setTimeout(function() {{
  if (!dashVisible) return;
  var frame = document.getElementById('dashboard-frame');
  if (frame) {{
    try {{
      var doc = frame.contentDocument || frame.contentWindow.document;
      if (!doc || !doc.body || doc.body.innerHTML.length < 100) showDashboardError();
    }} catch(e) {{}}
  }}
}}, 2000);
"""


def generate(dashboard_path: str, output_path: Path) -> str:
    """Return the complete presentation HTML.

    dashboard_path can be relative to CWD, relative to the repo root, or
    relative to the output file's directory. We try all three. When found,
    the dashboard is copied next to the output file with the fixed name
    'tournament_dashboard.html'. Cache-busting is handled in JavaScript
    using a build-time timestamp appended to the iframe src.
    """
    output_dir = Path(output_path).parent.resolve()
    repo_root = Path(__file__).resolve().parents[2]  # workspace/presentation/generate.py -> repo root
    candidate = Path(dashboard_path)
    resolved = None
    # Try resolving relative to CWD first (how users naturally pass paths)
    if candidate.exists():
        resolved = candidate.resolve()
    # Try relative to the repo root (vol script cd's into src/ before calling us)
    elif (repo_root / dashboard_path).exists():
        resolved = (repo_root / dashboard_path).resolve()
    # Try relative to the output directory (legacy behaviour)
    elif (output_dir / dashboard_path).exists():
        resolved = (output_dir / dashboard_path).resolve()

    if resolved is not None:
        dashboard_available = True
        # Copy dashboard next to output with a fixed name. JupyterHub can't
        # follow symlinks or serve ../.. paths, so a real file is required.
        dest = output_dir / "tournament_dashboard.html"
        # Remove stale symlink if present from previous approach
        if dest.is_symlink():
            dest.unlink()
        if dest.resolve() != resolved:
            shutil.copy2(resolved, dest)
        dashboard_path = "tournament_dashboard.html"
        # Build-time timestamp for cache-busting (changes every rebuild)
        dashboard_hash = str(int(date.today().toordinal() * 100000 + hash(resolved.stat().st_mtime) % 100000))
    else:
        dashboard_available = False
        dashboard_hash = ""
    index_series = None
    if resolved is not None:
        index_series = _extract_index_series(resolved.read_text(encoding="utf-8"))
    print("slide 2 chart: real dashboard data" if index_series
          else "slide 2 chart: synthetic fallback")
    if index_series:
        _apply_series_numbers(index_series)
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
        f"{_get_slides(index_series)}\n"
        "</div>\n"
        '<button id="dashboard-toggle" onclick="toggleDashboard()">Dashboard [D]</button>\n'
        f'<div id="dashboard-overlay">{overlay_inner}</div>\n'
        '<div id="counter"></div>\n'
        f"<script>{_get_js(dashboard_available, dashboard_path, dashboard_hash)}</script>\n"
        "</body>\n"
        "</html>\n"
    )
    if "\u2014" in html:
        raise ValueError("em dash (U+2014) found in generated HTML; the deck bans em dashes")
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the desk-pitch presentation HTML")
    parser.add_argument(
        "--dashboard-path",
        default="../../src/data/models/trial_067_xgboost_all_layers/plots/tournament_dashboard.html",
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