# Presentation Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the CDN-dependent 18-slide Reveal.js deck and 30-minute documentation-style script with a self-contained 9-slide dark deck (rewritten `generate.py`) and a 20-minute verbatim desk-pitch script plus beat sheet, per the approved spec.

**Architecture:** `generate.py` becomes a zero-dependency HTML generator: theme tokens + canonical numbers at the top, matplotlib-prerendered equation SVGs, 7 hand-authored diagram SVG functions, 9 slide functions, one CSS string, one vanilla-JS string, assembled by `generate()`. The script and beat sheet are one markdown file with cues matching the deck. No `src/` changes anywhere.

**Tech Stack:** Python 3.12 (project venv via `ml-vol-estimator/vol shell` only), matplotlib 3.10.9 mathtext (build-time only), vanilla HTML/CSS/JS output, pytest for structural tests.

**Spec:** `docs/superpowers/specs/2026-07-02-presentation-rewrite-design.md` (read it first; Section 3.5 is the canonical numbers table, Section 3.2 the slide table).

## Global Constraints

- No em dash (U+2014) in ANY deliverable: deck HTML, script, beat sheet. Applies to generated `presentation.html` too.
- Exactly two rendered equations in the deck: Kvar and QLIKE. No `$...$` LaTeX text anywhere in the HTML.
- No magic numbers on slides: `0.13679`, `0.1289`, `153 bps`, `138 bps` must NOT appear in the deck; use the translations from spec Section 3.5.
- Output HTML makes zero network requests: no `src="http`, `href="http`, `url(http`, `@import`. (SVG `xmlns="http://www.w3.org/2000/svg"` attributes are fine; they are namespaces, not requests.)
- Fonts: system stacks only. Serif display: `Georgia, 'Times New Roman', serif`. Sans labels/body: `'Segoe UI', Verdana, sans-serif`.
- Theme tokens (exact values, defined once in `THEME`): bg `#0c1117`, ink `#e8e4da`, muted `#7d8896`, muted2 `#9aa5b1`, body `#c7cdd6`, hairline `#1f2a37`, amber `#e8b339`, green `#4cc38a`, red `#e05252`.
- Green is used ONLY for wins (improved Sharpe, precision, loss reductions). Amber for structure/emphasis. Red only for drawdown marks.
- Never run bare `python`/`pip`/`pytest`. Everything runs through `./vol shell` from `ml-vol-estimator/`. If `vol shell` turns out not to forward script arguments, fall back to the same venv's interpreter directly: `ml-vol-estimator/src/.venv/Scripts/python.exe` (this is the interpreter the wrapper uses; it is not a bare system python).
- All file paths below are relative to the repo root `C:\Users\RyanPC\Documents\Projects\ML-GS`.
- Commit after every task with the message given in the task.

---

### Task 1: Skeleton deck with CLI contract, stage, and navigation (TDD)

**Files:**
- Create: `workspace/presentation/test_generate.py`
- Rewrite: `workspace/presentation/generate.py` (delete all existing content; it is preserved in git history)

**Interfaces:**
- Produces: `THEME: dict[str,str]` (keys: bg, ink, muted, muted2, body, hairline, amber, green, red, serif, sans); `NUMBERS: dict[str,str]`; `_slide(kicker, title, body, cls="") -> str`; `generate(dashboard_path: str, output_path: Path) -> str`; `main() -> None`. Slide functions `_slide_01()` .. `_slide_09()` returning `<section class="slide">...` HTML; later tasks fill their bodies.

- [ ] **Step 1: Write the failing tests**

Create `workspace/presentation/test_generate.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: collection error or failures (old `generate.generate` has a different signature and old content). This is the red state.

- [ ] **Step 3: Rewrite `generate.py` as the skeleton**

Replace the entire file with:

```python
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
    return (
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add workspace/presentation/generate.py workspace/presentation/test_generate.py
git commit -m "feat(presentation): skeleton self-contained deck generator with TDD harness"
```

---

### Task 2: Dashboard toggle, build-time fallback, mock fixture

**Files:**
- Create: `workspace/presentation/tournament_dashboard_mock.html`
- Modify: `workspace/presentation/generate.py` (extend `generate()`, `_get_js()`, `_get_css()`)
- Modify: `workspace/presentation/test_generate.py` (append tests)

**Interfaces:**
- Consumes: `generate(dashboard_path, output_path)`, `THEME`.
- Produces: overlay markup ids `dashboard-overlay`, `dashboard-frame`, `dashboard-toggle`, placeholder id `dashboard-placeholder`; JS `toggleDashboard()` bound to `D` key and Escape-to-close.

- [ ] **Step 1: Append failing tests**

Append to `workspace/presentation/test_generate.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify the new ones fail**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: the 5 new tests FAIL; prior 7 still pass.

- [ ] **Step 3: Implement**

Create `workspace/presentation/tournament_dashboard_mock.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>MOCK tournament dashboard</title>
<style>
body { background:#1a1a2e; color:#e4e4e4; font-family:'Segoe UI',Verdana,sans-serif; padding:40px; }
.banner { background:#e8b339; color:#000; padding:10px 16px; font-weight:600; margin-bottom:24px; }
.tabs { display:flex; gap:8px; margin-bottom:24px; }
.tab { background:#16213e; border:1px solid #0f3460; padding:8px 18px; }
table { border-collapse:collapse; } td,th { border:1px solid #0f3460; padding:6px 14px; }
</style></head>
<body>
<div class="banner">MOCK FIXTURE for local toggle testing. Not real results. The real dashboard is GS-only.</div>
<div class="tabs"><div class="tab">Rankings</div><div class="tab">SHAP</div><div class="tab">ALE</div><div class="tab">GSVIVS</div></div>
<table><tr><th>model</th><th>qlike</th></tr><tr><td>mock_model</td><td>0.000</td></tr></table>
</body>
</html>
```

In `generate.py`:

1. Add to `_get_css()` (before the closing `"""`):

```python
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
```

2. In `generate()`, build the overlay body from the availability check:

```python
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
```

and insert into the HTML between `</div>` (stage) and the counter div:

```python
        '<button id="dashboard-toggle" onclick="toggleDashboard()">Dashboard [D]</button>\n'
        f'<div id="dashboard-overlay">{overlay_inner}</div>\n'
```

3. In `_get_js()`, add after `show(0);`:

```python
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
```

and extend the keydown handler with:

```python
  else if (e.key === 'd' || e.key === 'D') toggleDashboard();
  else if (e.key === 'Escape' && dashVisible) toggleDashboard();
```

- [ ] **Step 4: Run all tests**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add workspace/presentation/generate.py workspace/presentation/test_generate.py workspace/presentation/tournament_dashboard_mock.html
git commit -m "feat(presentation): dashboard toggle with build-time fallback and mock fixture"
```

---

### Task 3: Slide copy for all nine slides

**Files:**
- Modify: `workspace/presentation/generate.py` (fill `_slide_01()` .. `_slide_09()` bodies)
- Modify: `workspace/presentation/test_generate.py` (append tests)

**Interfaces:**
- Consumes: `_slide()`, `THEME`, `NUMBERS`.
- Produces: final on-slide text. Diagram/equation placeholders are `<div class="diagram" data-diagram="NAME"></div>` and `<div class="equation" data-eq="NAME"></div>`, replaced in Tasks 4 to 6 by real content (same class names kept).

- [ ] **Step 1: Append failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify the new ones fail**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: `test_key_copy_present` FAILS (bodies empty); others pass.

- [ ] **Step 3: Write the slide bodies (approved storyboard v3 copy, verbatim)**

Fill each `_slide_XX()`. Use `NUMBERS[...]` for every number. The exact copy:

```python
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
```

Also add these CSS rules to `_get_css()`:

```python
.title-slide h1 {{ font-size: 64px; margin-top: 140px; }}
.title-slide .subtitle-line {{ font-size: 22px; color: {t['muted2']}; }}
.title-slide .byline {{ position: absolute; bottom: 72px; font-size: 16px; color: {t['muted']}; }}
.diagram {{ margin: 20px 0; }}
.equation {{ margin: 18px 0; }}
```

- [ ] **Step 4: Run all tests**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add workspace/presentation/generate.py workspace/presentation/test_generate.py
git commit -m "feat(presentation): final slide copy for all nine slides"
```

---

### Task 4: Prerendered equations (Kvar, QLIKE)

**Files:**
- Modify: `workspace/presentation/generate.py`
- Modify: `workspace/presentation/test_generate.py`

**Interfaces:**
- Consumes: slide bodies' `<div class="equation" data-eq="kvar|qlike"></div>` placeholders.
- Produces: `render_equation_svg(latex: str, *, color: str, fontsize: float = 26.0) -> str` returning an `<svg...>` string; module constants `EQ_KVAR`, `EQ_QLIKE` (LaTeX strings); `_equation_block(name: str) -> str` that returns `<div class="equation" data-eq="NAME"><svg.../></div>`.

- [ ] **Step 1: Append failing tests**

```python
def test_exactly_two_equation_svgs(html):
    blocks = re.findall(r'<div class="equation"[^>]*>.*?</div>', html, re.S)
    assert len(blocks) == 2
    assert all("<svg" in b for b in blocks)


def test_no_raw_latex(html):
    assert "$$" not in html
    assert "\\frac" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: `test_exactly_two_equation_svgs` FAILS (placeholders are empty divs).

- [ ] **Step 3: Implement**

Add to `generate.py`:

```python
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

    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    fig = Figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${latex}$", fontsize=fontsize, color=color,
             math_fontfamily="cm")
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.03,
                transparent=True)
    svg = buf.getvalue().decode("utf-8")
    return svg[svg.index("<svg"):]


def _equation_block(name: str) -> str:
    latex = {"kvar": EQ_KVAR, "qlike": EQ_QLIKE}[name]
    svg = render_equation_svg(latex, color=THEME["body"])
    return f'<div class="equation" data-eq="{name}">{svg}</div>'
```

In `_slide_03()` replace `'<div class="equation" data-eq="kvar"></div>'` with `_equation_block("kvar")`, and in `_slide_06()` replace the qlike placeholder with `_equation_block("qlike")`. Add CSS: `.equation svg {{ height: 74px; width: auto; }}`.

- [ ] **Step 4: Run all tests**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: 17 passed. If mathtext rejects the LaTeX, simplify per spec Section 10 fallback (e.g. drop `\;` spacing commands) until it renders; the two equations' content must stay intact.

- [ ] **Step 5: Commit**

```bash
git add workspace/presentation/generate.py workspace/presentation/test_generate.py
git commit -m "feat(presentation): prerender Kvar and QLIKE equations to inline SVG"
```

---

### Task 5: Diagrams part 1 (payoff motif, product day, architecture)

**Files:**
- Modify: `workspace/presentation/generate.py`
- Modify: `workspace/presentation/test_generate.py`

**Interfaces:**
- Consumes: `<div class="diagram" data-diagram="payoff_motif|product_day|architecture"></div>` placeholders, `THEME`.
- Produces: `_diagram_payoff_motif() -> str`, `_diagram_product_day() -> str`, `_diagram_architecture() -> str`, each returning a full `<svg>` string; `_diagram_block(name: str) -> str` dispatcher; shared `_SVG_DEFS` (arrowhead marker `arr`, hatch pattern `hatch`).

- [ ] **Step 1: Append failing test**

```python
def test_first_three_diagrams_are_svg(html):
    for name in ("payoff_motif", "product_day", "architecture"):
        m = re.search(rf'<div class="diagram" data-diagram="{name}">(.*?)</div>', html, re.S)
        assert m and "<svg" in m.group(1), f"diagram {name} not rendered"
```

- [ ] **Step 2: Run tests to verify it fails**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: new test FAILS.

- [ ] **Step 3: Implement**

Add to `generate.py` (shared plumbing plus the three diagrams). All diagrams use `THEME` colors only, sans labels at 15 to 17px SVG units, one stroke width (1.5), and the shared defs:

```python
def _svg_defs() -> str:
    t = THEME
    return (
        "<defs>"
        '<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{t["muted"]}"/></marker>'
        '<pattern id="hatch" width="7" height="7" patternTransform="rotate(45)" '
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
        '<svg viewBox="0 0 1180 240" style="width:1080px;height:220px;">'
        + _svg_defs()
        + f'<line x1="40" y1="120" x2="420" y2="120" stroke="{t["muted"]}" stroke-width="1.5" marker-end="url(#arr)"/>'
        + node(70, "09:30", "sell the strip")
        + node(230, "all day", "delta-hedge")
        + node(390, "16:00", "settle at MOC")
        + f'<polyline points="{curve}" fill="none" stroke="{t["ink"]}" stroke-width="1.5"/>'
        + ticks
        + f'<text x="{x0}" y="235" fill="{t["muted"]}" font-size="14">index level, four years, 100 to 138. '
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
                f'stroke-width="1.5" marker-end="url(#arr)"/>' + lab)
    tenor = (
        f'<rect x="820" y="150" width="300" height="100" fill="none" stroke="{t["hairline"]}" stroke-width="1.5"/>'
        f'<text x="970" y="175" text-anchor="middle" fill="{t["amber"]}" font-size="13" letter-spacing="2">TENOR MATCHING</text>'
        f'<text x="970" y="200" text-anchor="middle" fill="{t["body"]}" font-size="14">1-day forecast &#8596; same-day IV</text>'
        f'<text x="970" y="220" text-anchor="middle" fill="{t["body"]}" font-size="14">5-day &#8596; 1-week &#183; 22-day &#8596; 1-month</text>'
    )
    return (
        '<svg viewBox="0 0 1180 270" style="width:1080px;height:247px;">'
        + _svg_defs()
        + box(20, 20, 200, 80, "market inputs", "prices, options, calendar", t["hairline"])
        + arrow(220, 60, 300, 60)
        + box(300, 20, 220, 80, "HAR-IV spine", "4 parameters, most of the forecast", t["amber"])
        + arrow(520, 60, 600, 60, "init_score")
        + box(600, 20, 220, 80, "LightGBM overlay", "learns only the residual", t["amber"])
        + arrow(820, 60, 900, 60)
        + box(900, 20, 220, 80, "forecast", "trained end to end on QLIKE", t["green"])
        + tenor
        + "</svg>"
    )
```

Replace the three placeholders in `_slide_01/_slide_02/_slide_04` with `_diagram_block("payoff_motif")` etc. Add forward stubs so the module imports before Task 6:

```python
def _diagram_feature_map() -> str:
    return "<svg viewBox='0 0 10 10'></svg>"


def _diagram_cv_folds() -> str:
    return "<svg viewBox='0 0 10 10'></svg>"


def _diagram_beeswarm_guide() -> str:
    return "<svg viewBox='0 0 10 10'></svg>"


def _diagram_results_bars() -> str:
    return "<svg viewBox='0 0 10 10'></svg>"
```

(Keep the remaining slide placeholders as `_diagram_block("feature_map")` etc. so Task 6 only replaces the stub functions.)

- [ ] **Step 4: Run all tests**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add workspace/presentation/generate.py workspace/presentation/test_generate.py
git commit -m "feat(presentation): payoff motif, product-day, and architecture diagrams"
```

---

### Task 6: Diagrams part 2 (feature map, CV folds, beeswarm guide, results bars)

**Files:**
- Modify: `workspace/presentation/generate.py` (replace the four stub functions)
- Modify: `workspace/presentation/test_generate.py`

**Interfaces:**
- Consumes: `_svg_defs()`, `THEME`, `_diagram_block()` dispatcher (already wired).
- Produces: real `_diagram_feature_map()`, `_diagram_cv_folds()`, `_diagram_beeswarm_guide()`, `_diagram_results_bars()`.

- [ ] **Step 1: Append failing test**

```python
def test_all_seven_diagrams_are_real_svg(html):
    names = ("payoff_motif", "product_day", "architecture", "feature_map",
             "cv_folds", "beeswarm_guide", "results_bars")
    for name in names:
        m = re.search(rf'<div class="diagram" data-diagram="{name}">(.*?)</div>', html, re.S)
        assert m and "<svg" in m.group(1)
        assert "viewBox='0 0 10 10'" not in m.group(1), f"{name} is still a stub"
```

- [ ] **Step 2: Run tests to verify it fails**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: new test FAILS on the stubs.

- [ ] **Step 3: Implement the four diagrams**

```python
def _diagram_feature_map() -> str:
    t = THEME
    quads = [
        (20, 20, "PRICE HISTORY", "how volatile we have been:",
         "up-moves, down-moves, jumps"),
        (600, 20, "OPTIONS SURFACE", "what the market pays for future vol:",
         "term slope, skew, vol of vol"),
        (20, 170, "MEASUREMENT QUALITY", "how much of today's reading is noise:",
         "kernel estimates, tick anomalies"),
        (600, 170, "CALENDAR", "what is scheduled:",
         "Fed meetings, payrolls, expiries"),
    ]
    cells = "".join(
        f'<rect x="{x}" y="{y}" width="540" height="130" fill="none" stroke="{t["hairline"]}" stroke-width="1.5"/>'
        f'<text x="{x + 20}" y="{y + 34}" fill="{t["amber"]}" font-size="14" letter-spacing="3">{title}</text>'
        f'<text x="{x + 20}" y="{y + 66}" fill="{t["ink"]}" font-size="16">{line1}</text>'
        f'<text x="{x + 20}" y="{y + 92}" fill="{t["muted2"]}" font-size="16">{line2}</text>'
        for x, y, title, line1, line2 in quads
    )
    return (
        '<svg viewBox="0 0 1180 320" style="width:1080px;height:293px;">'
        + _svg_defs() + cells
        + "</svg>"
    )


def _diagram_cv_folds() -> str:
    t = THEME
    # 4 folds: expanding train bar, hatched purge gap, test bar.
    rows = []
    x0, gap_w, test_w, row_h = 40, 26, 150, 30
    for k in range(4):
        y = 20 + k * (row_h + 14)
        train_w = 300 + k * 150
        rows.append(
            f'<rect x="{x0}" y="{y}" width="{train_w}" height="{row_h}" fill="{t["hairline"]}"/>'
            f'<rect x="{x0 + train_w}" y="{y}" width="{gap_w}" height="{row_h}" fill="url(#hatch)"/>'
            f'<rect x="{x0 + train_w + gap_w}" y="{y}" width="{test_w}" height="{row_h}" '
            f'fill="none" stroke="{t["green"]}" stroke-width="1.5"/>'
        )
    labels = (
        f'<text x="{x0}" y="212" fill="{t["muted"]}" font-size="14">grey: training, always in the past'
        f' &#183; hatched: {NUMBERS["purge_days"]} purged &#183; green: out-of-sample test</text>'
        f'<text x="{x0}" y="236" fill="{t["muted"]}" font-size="14">splits are by DATE across all '
        f'{NUMBERS["n_symbols"]} symbols; the early-stopping split sits behind its own gap</text>'
    )
    return ('<svg viewBox="0 0 1180 250" style="width:1080px;height:229px;">'
            + _svg_defs() + "".join(rows) + labels + "</svg>")


def _diagram_beeswarm_guide() -> str:
    t = THEME
    # Three example feature rows; dot color encodes feature value (blue low, red high).
    import random
    rng = random.Random(7)
    rows = [("feature pushing vol UP when high", 1), ("feature pushing vol DOWN when high", -1),
            ("feature with regime-dependent effect", 0)]
    dots = []
    for r, (_, direction) in enumerate(rows):
        y = 60 + r * 56
        for _ in range(46):
            v = rng.random()
            if direction == 1:
                x = 560 + (v - 0.5) * 700 * v
            elif direction == -1:
                x = 560 - (v - 0.5) * 700 * v
            else:
                x = 560 + (v - 0.5) * 500 * (1 if rng.random() > 0.5 else -1)
            x = max(180, min(1000, x))
            col = f"rgb({int(80 + 175 * v)},{int(120 - 40 * v)},{int(220 - 160 * v)})"
            dots.append(f'<circle cx="{x:.0f}" cy="{y + rng.uniform(-9, 9):.0f}" r="3.4" '
                        f'fill="{col}" opacity="0.85"/>')
    row_labels = "".join(
        f'<text x="165" y="{64 + r * 56}" text-anchor="end" fill="{t["body"]}" font-size="14">{label}</text>'
        for r, (label, _) in enumerate(rows)
    )
    return (
        '<svg viewBox="0 0 1180 240" style="width:1080px;height:220px;">'
        + _svg_defs()
        + f'<line x1="560" y1="30" x2="560" y2="190" stroke="{t["hairline"]}" stroke-width="1.5"/>'
        + f'<text x="560" y="216" text-anchor="middle" fill="{t["muted"]}" font-size="14">'
          "SHAP value: pushes this day's forecast down &#8592; 0 &#8594; up</text>"
        + f'<text x="1020" y="40" fill="{t["muted"]}" font-size="13">dot color = feature value (blue low, red high)</text>'
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
    x0, zero_y, w, scale = 220, 120, 160, 9.0
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
        '<svg viewBox="0 0 1180 200" style="width:1080px;height:183px;">'
        + _svg_defs()
        + f'<line x1="120" y1="{zero_y}" x2="1060" y2="{zero_y}" stroke="{t["hairline"]}" stroke-width="1.5"/>'
        + f'<text x="120" y="30" fill="{t["muted"]}" font-size="14">forecast-loss reduction vs HAR-IV '
          "(QLIKE, five-seed mean; positive = our model better)</text>"
        + "".join(parts)
        + "</svg>"
    )
```

Note: `_diagram_beeswarm_guide` seeds `random.Random(7)` so output is deterministic build-to-build.

- [ ] **Step 4: Run all tests**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add workspace/presentation/generate.py workspace/presentation/test_generate.py
git commit -m "feat(presentation): feature map, CV folds, beeswarm guide, results bars diagrams"
```

---

### Task 7: Visual QA loop and committed artifact

**Files:**
- Modify: `workspace/presentation/generate.py` (polish only; no structural changes)
- Create/overwrite: `workspace/presentation/presentation.html` (built artifact, committed)

**Interfaces:**
- Consumes: the complete generator.
- Produces: the final `presentation.html` built against the mock dashboard path replaced by the real default (see step 3).

- [ ] **Step 1: Build and open the deck**

```bash
cd ml-vol-estimator && ./vol shell ../workspace/presentation/generate.py --dashboard-path tournament_dashboard_mock.html --output ../workspace/presentation/presentation.html
```
Expected: `Wrote ...presentation.html`. Open it in a browser (e.g. `start workspace\presentation\presentation.html` from PowerShell, or drive it with the Chrome DevTools / Playwright MCP tools if available).

- [ ] **Step 2: Screenshot every slide and check against this list**

Navigate with ArrowRight through all 9 slides, press D on and off once. Fix and rebuild until every item passes:

- Slide text fits inside the 1280x720 stage at every slide; nothing clipped or overlapping the footer band.
- Kicker / rule / title alignment identical on slides 2 to 9.
- Both equations render crisply, are legible from 3 meters (title-size test: equation height roughly 70 to 80px), and their color matches body text.
- Diagram labels are legible; no label collides with a mark; every axis or encoding is titled.
- Amber appears only as structure/emphasis; green only on wins; red only on drawdown ticks.
- Dashboard toggle: D opens the mock instantly, Escape closes, slide state preserved.
- Window resize keeps the stage centered and scaled.
- No em dash anywhere on any slide (visual spot check; the test already enforces it).

Iterate: adjust CSS sizes/coordinates in `generate.py`, rebuild (same command), re-screenshot. Keep all tests green.

- [ ] **Step 3: Rebuild the committed artifact with the real (GS) dashboard default**

```bash
cd ml-vol-estimator && ./vol shell ../workspace/presentation/generate.py --output ../workspace/presentation/presentation.html
```
Expected: build succeeds; because the trial-036 dashboard does not exist locally, the artifact contains the labeled placeholder (correct behavior for the committed version; on GS a rebuild picks up the real dashboard).

- [ ] **Step 4: Run the full test suite one more time**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
```
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add workspace/presentation/generate.py workspace/presentation/presentation.html
git commit -m "feat(presentation): visual QA pass and committed deck artifact"
```

---

### Task 8: Rewrite the presentation script

**Files:**
- Rewrite: `workspace/presentation/presentation-script.md` (from scratch; old content is in git history)

**Interfaces:**
- Consumes: slide titles/kickers exactly as in `generate.py` Task 3; `NUMBERS` translations; spec Sections 3.1, 3.4, 4.
- Produces: the verbatim script; Task 9 appends the beat sheet to this file.

- [ ] **Step 1: Write the header and regeneration block**

```markdown
# Presentation Script: Timing the Variance Seller

**Duration:** ~20 minutes + open Q&A
**Audience:** trading desk (traders + quants)
**Deck:** `workspace/presentation/presentation.html` (9 slides, self-contained)
**Q&A backstop:** `qa-comprehensive.md`

## Regeneration

```bash
# GS (real dashboard):
./vol present --dashboard-path '../../src/data/models/trial_036_drop_vrp_calendar/plots/tournament_dashboard.html'
# Local (mock dashboard):
cd ml-vol-estimator && ./vol shell ../workspace/presentation/generate.py --dashboard-path tournament_dashboard_mock.html
```
```

- [ ] **Step 2: Write the seven sections to this contract**

Rules for every section (spec 3.4): spoken register, short sentences, first person, no em dashes, every number said with what it is / period / baseline. Cues on their own lines: `> [SLIDE n: title]` / `> [DASHBOARD: tab, what to point at]`, placed at the exact sentence where they fire. Word budgets are for spoken text excluding cues; total 2,600 to 2,800.

**Section 1, slides 1-2, ~300 words.** Opens the talk. Mandated opening sentence: "GSVIVS01 is about the simplest short volatility product we run: every morning it sells the day, and every afternoon it finds out what the day cost." Beats: strip mechanics in one breath (sell 09:30, hedge, settle 16:00); index 100 to 138 over four years, roughly 9.6 points a year; the equity curve's smoothness is bought with left-tail days; drawdown days are exactly the days realized variance beat the strike it sold. Mandated closing transition: "So the question this project answers is simple. Can we tell, before nine thirty, which mornings are the wrong mornings to sell?"

**Section 2, slide 3 + Dashboard 1, ~350 words.** Beats: the decision each morning at 09:10 (forecast of today's realized variance vs the strike on offer from the previous close); rule: rich means sell as usual, forecast above strike means stand aside; 30 seconds on Kvar: same OTM-option integral as the VIX, inherits the skew, always above ATM IV, so benchmarking against ATM IV would flatter the signal; headline: annualized Sharpe 1.60 as-is to 1.95 with the signal, backtest May 2022 to Jun 2026. Cue `> [DASHBOARD: GSVIVS tab, Sharpe column, then the stand-aside precision]` lands right after the headline. On the dashboard: 7 of the 10 stand-aside days preceded genuine drawdowns. Mandated transition: "That is the claim. The rest of the talk is me earning it."

**Section 3, slides 4-5, ~520 words.** Beats: HAR-IV spine (four parameters: today's, last week's, last month's realized variance plus implied vol; carries most of the forecast; a desk classic, not a black box); LightGBM overlay starts from the spine's prediction via init_score and learns only the residual, end to end on the same loss we report; tenor matching (each horizon reads the IV that expires with it; using week IV for a one-day forecast smuggles in four days of term premium; fixing that was one of the cleanest gains); the four feature families in trader words, one sentence each; about 128 inputs once each series contributes its change and its own-history z-score. Mandated transition: "That is the model. Here is why you should believe the numbers it produces."

**Section 4, slide 6 + Dashboard 2, ~580 words.** Beats: every number is out-of-sample; expanding walk-forward; the ten-trading-day purge either side of every test block and WHY (the target overlaps days); panel-aware date splits across 21 symbols (no cross-symbol leakage of the future); even early stopping validates behind its own gap; QLIKE in one confident spoken line (proportional loss, calm markets count as much as crises, underprediction punished more, and rankings under it are robust to the fact that measured RV is itself a noisy proxy); seeds: one lucky seed looked six percent better than the truth, so every headline number is a five-seed mean. Cue `> [DASHBOARD: Rankings tab, QLIKE column, OOS window in the header]`; DM and MCS each get exactly one sentence as pointers ("a paired test that the gap is real" / "the set of models you cannot statistically tell from the best"). Mandated transition: "So the protocol is airtight. The next question is what the model actually learned."

**Section 5, slide 7 + Dashboards 3-4, ~500 words.** Beats: SHAP in two sentences (every forecast splits into named contributions that sum exactly to the prediction; we audit the trees' additions on top of the spine); 20-second beeswarm reading guide off the slide; then live tour of the top five (implied-to-realized relationship shifting with regime; VRP extremes; Fed proximity; z-score mean-reversion flags), each tied to a concept the room already trades; then one ALE curve (same-day IV: monotone rising, slope steepens in the tail, information content highest exactly when it matters). Cues: `> [DASHBOARD: SHAP beeswarm, h=1]` then `> [DASHBOARD: ALE, h=1, same-day IV]`. Mandated transition: "Which brings us to the honest scorecard."

**Section 6, slide 8, ~330 words.** Beats: one-day about 10% lower forecast loss than the strongest linear baseline, statistically significant; five-day about 11%, significant; 22-day the four-parameter linear model wins and that is a feature of knowing when to stop, the month-ahead option market has already done the work; the MSE line: the identical model trained on MSE trades at Sharpe 0.3, the loss function is the product. Mandated transition: "Three caveats before I stop, and then three numbers I want you to leave with."

**Section 7, slide 9, ~170 words.** Beats: proxy strike (tracks the real one, correlation above 0.99, production feed exists); concentrated edge (about ten signal changes a year, each call matters); COVID enters training only from 2022 onward by construction. Then the three numbers, spoken slowly, each with its label: 1.95 against 1.60; 2% of days; 7 of 10. Mandated closing: "No slideware claims, no cherry picks: everything you saw is out of sample, purged, and five-seeded. The floor is open."

- [ ] **Step 3: Verify mechanically**

```bash
grep -c $'—' workspace/presentation/presentation-script.md
```
Expected: `0` (grep exits 1).

```bash
grep -v "^>" workspace/presentation/presentation-script.md | grep -v "^#" | grep -v '^```' | wc -w
```
Expected: between 2,600 and 2,900 (header block adds a small overhead over the 2,600 to 2,800 spoken-word target).

```bash
grep -n "^> \[" workspace/presentation/presentation-script.md
```
Expected: 9 SLIDE cues (slides 1 to 9 in order) and 4 DASHBOARD cues (GSVIVS, Rankings, SHAP, ALE).

- [ ] **Step 4: Read-aloud pass**

Read the full script once aloud (or estimate at 135 words/min: ~2,700 words is ~20 min). Fix any sentence you stumble on: if it cannot be said in one breath, split it.

- [ ] **Step 5: Commit**

```bash
git add workspace/presentation/presentation-script.md
git commit -m "feat(presentation): verbatim 20-minute desk-pitch script"
```

---

### Task 9: Beat sheet and final consistency pass

**Files:**
- Modify: `workspace/presentation/presentation-script.md` (append beat sheet)

**Interfaces:**
- Consumes: the final script (Task 8) and deck slide titles (Task 3).

- [ ] **Step 1: Append the beat sheet**

Append to the script file, following this exact format (fill from the final script text; transitions must be copied verbatim from the script):

```markdown
## Beat Sheet (one page)

| # | Slide | Beats | Transition out (verbatim) | The number |
|---|-------|-------|---------------------------|------------|
| 1-2 | Title / The product | sells daily; 100 to 138; smooth gains, left-tail losses; no opinion | "So the question this project answers is simple. ..." | 9.6 pts/yr |
| 3 | The claim | 09:10 rule; Kvar = VIX-style integral, above ATM IV; headline Sharpe | "That is the claim. The rest of the talk is me earning it." | 1.60 to 1.95 |
| 4 | The model | HAR-IV spine; residual trees via init_score; tenor matching | (into features, same section) | 4 parameters |
| 5 | The features | 4 families in trader words; change + z-score expansion | "That is the model. Here is why you should believe..." | ~128 inputs |
| 6 | Why trust | purge moat; panel splits; QLIKE one-liner; 5 seeds | "So the protocol is airtight. ..." | 6% lucky seed |
| 7 | What it learned | SHAP in 2 sentences; beeswarm guide; live tour; one ALE | "Which brings us to the honest scorecard." | top-5 features |
| 8 | Results | 10% / 11% / linear wins at 22d; MSE Sharpe 0.3 | "Three caveats before I stop, ..." | Sharpe 0.3 (MSE) |
| 9 | Close | proxy strike; concentrated edge; COVID timing; three numbers | "The floor is open." | 1.95 / 2% / 7 of 10 |
```

- [ ] **Step 2: Cross-check script vs deck**

For each of the 9 `> [SLIDE n: ...]` cues, confirm the title text matches the `<h1>` in `generate.py` exactly. For each number spoken in the script, confirm it matches `NUMBERS` in `generate.py`. Fix mismatches in the script (the deck is the source of truth).

- [ ] **Step 3: Full final verification**

```bash
cd ml-vol-estimator && ./vol shell -m pytest ../workspace/presentation/test_generate.py -v
grep -c "—" workspace/presentation/presentation-script.md
git diff --stat HEAD -- src/
git status
```
Expected: 19 passed; em-dash count 0 (grep exits 1); the `src/` diff is empty; only intended `workspace/presentation/` and docs files appear in status.

- [ ] **Step 4: Commit**

```bash
git add workspace/presentation/presentation-script.md
git commit -m "feat(presentation): beat sheet and script-deck consistency pass"
```
