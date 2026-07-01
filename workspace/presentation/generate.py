#!/usr/bin/env python3
"""Generate presentation.html with configurable dashboard path.

Usage:
    python generate.py --dashboard-path <path> [--output <path>]
    ./vol present --dashboard-path <path>

Examples:
    # Current champion dashboard
    ./vol present --dashboard-path '../../src/data/models/trial_036_drop_vrp_calendar/plots/tournament_dashboard.html'

    # New trial dashboard
    ./vol present --dashboard-path '../../src/workspace/tmp/trial_067_smoke/plots/tournament_dashboard.html'
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """\
:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-card: #0f3460;
    --text-primary: #e4e4e4;
    --text-secondary: #a0a0b0;
    --border: #2a2a4a;
    --accent: #4fc3f7;
    --accent-dim: #2196b3;
    --success: #66bb6a;
    --danger: #ef5350;
    --warning: #ffa726;
    --purple: #ab47bc;
    --fs-body: 0.95rem;
    --fs-small: 0.82rem;
    --fs-tiny: 0.72rem;
    --fs-label: 0.65rem;
}

.reveal {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Fira Sans', sans-serif;
    color: var(--text-primary);
    font-size: 28px;
}
.reveal .slides { text-align: left; }
.reveal .slides section {
    padding: 24px 44px;
    overflow: hidden;
    box-sizing: border-box;
    background: var(--bg-primary);
    position: relative;
}
.reveal h1, .reveal h2, .reveal h3 {
    color: var(--accent);
    font-weight: 600;
    text-transform: none;
    letter-spacing: -0.02em;
}
.reveal h1 { font-size: 2.2rem; }
.reveal h2 { font-size: 1.45rem; margin-bottom: 0.35em; }
.reveal h3 { font-size: 1.05rem; color: var(--text-secondary); margin-bottom: 0.25em; }
.reveal p  { font-size: var(--fs-body); line-height: 1.45; margin: 6px 0; }
.reveal li { font-size: var(--fs-body); line-height: 1.45; }
.reveal ul { list-style: none; padding-left: 0; margin: 6px 0; }
.reveal ul li::before {
    content: "\\25b8";
    color: var(--accent);
    font-weight: bold;
    margin-right: 0.6em;
}
.reveal code {
    background: var(--bg-card);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.92em;
    color: var(--warning);
}
.reveal .slides section p,
.reveal .slides section li { font-size: var(--fs-body); }
.reveal .slides section h2 { font-size: 1.45rem; }
.reveal .slides section h3 { font-size: 1.05rem; }
.reveal .info-card p,
.reveal .info-card li,
.reveal .info-card div:not(.katex):not(.katex-display),
.reveal .info-card span,
.reveal .stat-box .stat-label,
.reveal .signal-box div { font-size: inherit; }
.reveal .columns p[style*="font-size"],
.reveal .info-card p[style*="font-size"] { font-size: var(--fs-small) !important; }
.reveal .columns ul[style*="font-size"] li,
.reveal .info-card ul[style*="font-size"] li { font-size: inherit !important; }

.title-slide { text-align: center !important; }
.title-slide h1 { font-size: 2.4em; margin-bottom: 0.2em; }
.title-slide .subtitle { color: var(--text-secondary); font-size: 1.1em; margin-bottom: 2em; }
.title-slide .meta { color: var(--text-secondary); font-size: 0.75em; }

.eq-block {
    background: var(--bg-secondary);
    border-left: 3px solid var(--accent);
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    margin: 10px 0;
    text-align: center;
    overflow-x: auto;
}
.eq-block .katex { font-size: 1.0rem; }

.info-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    margin: 8px 0;
    overflow: hidden;
    font-size: var(--fs-small);
}
.info-card p, .info-card li, .info-card div, .info-card span, .info-card strong { font-size: inherit; }
.info-card ul { margin: 4px 0; }
.info-card li { margin: 2px 0; font-size: inherit; }
.info-card.accent { border-color: var(--accent); }
.info-card.success { border-color: var(--success); }
.info-card.warning { border-color: var(--warning); }
.info-card.danger { border-color: var(--danger); }

.reveal table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--fs-small);
    margin: 10px 0;
    table-layout: fixed;
}
.reveal table th {
    background: var(--bg-card);
    color: var(--accent);
    padding: 6px 10px;
    text-align: left;
    border-bottom: 2px solid var(--accent);
    overflow: hidden;
    text-overflow: ellipsis;
    word-wrap: break-word;
}
.reveal table td {
    padding: 5px 10px;
    border-bottom: 1px solid var(--border);
    overflow: hidden;
    text-overflow: ellipsis;
    word-wrap: break-word;
}
.reveal table tr:hover td { background: var(--bg-secondary); }
.reveal table.auto-layout { table-layout: auto; }

.columns { display: flex; gap: 30px; align-items: flex-start; }
.columns .col { flex: 1; min-width: 0; overflow: hidden; }
.columns .col-wide { flex: 1.4; min-width: 0; overflow: hidden; }
.columns .col-narrow { flex: 0.6; min-width: 0; overflow: hidden; }

.mermaid { text-align: center; margin: 20px 0; }
.mermaid svg { max-width: 100%; height: auto; }

.pca-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
.pca-card {
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 14px;
    text-align: center;
    border: 1px solid var(--border);
    position: relative;
    overflow: hidden;
}
.pca-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.pca-card.pc1::before { background: var(--accent); }
.pca-card.pc2::before { background: var(--warning); }
.pca-card.pc3::before { background: var(--purple); }
.pca-card .pca-pct { font-size: 1.5rem; font-weight: 700; margin: 3px 0; }
.pca-card.pc1 .pca-pct { color: var(--accent); }
.pca-card.pc2 .pca-pct { color: var(--warning); }
.pca-card.pc3 .pca-pct { color: var(--purple); }
.pca-card .pca-label { font-size: var(--fs-tiny); color: var(--text-secondary); margin-bottom: 4px; }
.pca-card .pca-name { font-size: var(--fs-body); font-weight: 600; margin-bottom: 4px; }
.pca-card .pca-proxy { font-size: var(--fs-label); color: var(--text-secondary); font-style: italic; }

.asymmetry-bar { display: flex; align-items: center; margin: 6px 0; font-size: var(--fs-small); }
.asymmetry-bar .label { width: 130px; flex-shrink: 0; color: var(--text-secondary); }
.asymmetry-bar .bar {
    height: 24px; border-radius: 4px; display: flex; align-items: center;
    padding: 0 10px; font-weight: 600; font-size: var(--fs-small);
}
.asymmetry-bar .bar.under { background: var(--danger); color: #fff; width: 60%; }
.asymmetry-bar .bar.over { background: var(--success); color: #fff; width: 38%; }

.result-highlight { font-size: 1.8rem; font-weight: 700; color: var(--accent); text-align: center; margin: 20px 0; }
.result-highlight .unit { font-size: 0.85rem; color: var(--text-secondary); font-weight: 400; }

.reveal .slide-number { color: var(--text-secondary); font-size: var(--fs-label); }

#dashboard-toggle {
    position: fixed; bottom: 20px; right: 20px; z-index: 100;
    background: var(--bg-card); border: 1px solid var(--accent);
    color: var(--accent); padding: 10px 18px; border-radius: 8px;
    cursor: pointer; font-size: 0.85em; font-weight: 600;
    transition: all 0.2s; display: flex; align-items: center; gap: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
#dashboard-toggle:hover {
    background: var(--accent); color: #000;
    transform: translateY(-2px); box-shadow: 0 6px 20px rgba(79, 195, 247, 0.3);
}
#dashboard-toggle.active { background: var(--danger); border-color: var(--danger); color: #fff; }
#dashboard-toggle.active:hover { background: #c62828; }

#dashboard-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    z-index: 99; background: var(--bg-primary);
    display: none; opacity: 0; transition: opacity 0.3s ease;
}
#dashboard-overlay.visible { display: block; opacity: 1; }
#dashboard-overlay iframe { width: 100%; height: 100%; border: none; }

.slide-badge {
    position: absolute; top: 20px; right: 30px;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 20px; padding: 4px 14px;
    font-size: 0.6em; color: var(--text-secondary);
    text-transform: uppercase; letter-spacing: 0.05em;
}

.cv-timeline { position: relative; padding: 20px 0; }
.cv-timeline .track { display: flex; align-items: center; margin: 8px 0; font-size: 0.75em; }
.cv-timeline .track-label { width: 60px; color: var(--text-secondary); font-weight: 600; }
.cv-timeline .track-bar { flex: 1; height: 28px; display: flex; border-radius: 4px; overflow: hidden; position: relative; }
.cv-timeline .segment { display: flex; align-items: center; justify-content: center; font-size: 0.85em; font-weight: 500; }
.cv-timeline .seg-train { background: var(--accent-dim); color: #fff; }
.cv-timeline .seg-purge { background: var(--warning); color: #000; min-width: 20px; }
.cv-timeline .seg-test { background: var(--success); color: #000; }
.cv-timeline .seg-future { background: var(--bg-card); color: var(--text-secondary); }

.stat-row { display: flex; gap: 12px; margin: 10px 0; }
.stat-box {
    flex: 1; background: var(--bg-secondary); border-radius: 8px;
    padding: 10px; text-align: center; border: 1px solid var(--border); overflow: hidden;
}
.stat-box .stat-value { font-size: 1.5rem; font-weight: 700; color: var(--accent); }
.stat-box .stat-label { font-size: var(--fs-label); color: var(--text-secondary); margin-top: 3px; }
.stat-box.green .stat-value { color: var(--success); }
.stat-box.red .stat-value { color: var(--danger); }
.stat-box.orange .stat-value { color: var(--warning); }

.signal-diagram { display: flex; align-items: center; justify-content: center; gap: 20px; margin: 20px 0; font-size: 0.85em; }
.signal-box {
    background: var(--bg-secondary); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px 20px; text-align: center;
}
.signal-box.forecast { border-color: var(--accent); }
.signal-box.kvar { border-color: var(--warning); }
.signal-box.decision { border-color: var(--success); }
.signal-arrow { font-size: 1.5em; color: var(--text-secondary); }

.reveal .slide-background { background: var(--bg-primary); }
section.has-dark-background h1,
section.has-dark-background h2,
section.has-dark-background h3 { color: var(--accent); }

.info-card .katex { font-size: 0.9rem; }
.eq-block .katex { font-size: 1.0rem; }
.cv-timeline .segment { font-size: var(--fs-label); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.signal-diagram { flex-wrap: wrap; }
.signal-box { min-width: 130px; }
.signal-box div { font-size: inherit; }
.reveal [style*="font-size"] p,
.reveal [style*="font-size"] li,
.reveal [style*="font-size"] div:not(.katex):not(.katex-display) { font-size: inherit; }

"""

# ---------------------------------------------------------------------------
# SLIDES (18 total)
# ---------------------------------------------------------------------------

_SLIDE_01_TITLE = """\
<section class="title-slide" data-transition="fade">
    <h1>ML Realized Volatility<br>Forecasting</h1>
    <div class="subtitle">Signal Discovery for GSVIVS01 - 0-DTE Variance Swap Strategy</div>
    <div style="margin: 40px 0;">
        <div style="display: inline-block; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 16px 30px;">
            <span style="color: var(--accent); font-size: 0.9em;">21 symbols</span>
            <span style="color: var(--text-secondary); margin: 0 15px;">&middot;</span>
            <span style="color: var(--success); font-size: 0.9em;">11 years</span>
            <span style="color: var(--text-secondary); margin: 0 15px;">&middot;</span>
            <span style="color: var(--warning); font-size: 0.9em;">128 features</span>
            <span style="color: var(--text-secondary); margin: 0 15px;">&middot;</span>
            <span style="color: var(--purple); font-size: 0.9em;">QLIKE optimized</span>
        </div>
    </div>
    <div class="meta">20-Week Internship &middot; May - Sep 2026</div>
</section>"""

_SLIDE_02_PROBLEM = """\
<section data-transition="slide">
    <span class="slide-badge">Motivation</span>
    <h2>Why Forecast Realized Volatility?</h2>
    <div class="columns">
        <div class="col">
            <p>Realized variance, the sum of squared intraday returns, is the quantity that options ultimately pay off against.</p>
            <div class="eq-block">
                $$RV_t = \\sum_{i=1}^{n} r_{t,i}^2$$
            </div>
            <p>If you can forecast tomorrow's RV better than the market's implied estimate, you know when options are <span style="color:var(--success)">cheap</span> and when they're <span style="color:var(--danger)">expensive</span>. That's where the edge lives.</p>
        </div>
        <div class="col-narrow">
            <div class="info-card accent">
                <strong style="color:var(--accent)">Universe</strong><br>
                <span style="font-size:0.85em">17 mega-cap equities + 4 ETFs<br>Pooled training</span>
            </div>
            <div class="info-card success">
                <strong style="color:var(--success)">History</strong><br>
                <span style="font-size:0.85em">2015 - May 2026<br>~2,800 obs/symbol</span>
            </div>
            <div class="info-card warning">
                <strong style="color:var(--warning)">Target</strong><br>
                <span style="font-size:0.85em">h = 1, 5, 22 days<br>Log-space predictions</span>
            </div>
        </div>
    </div>
</section>"""

_SLIDE_03_HAR = """\
<section data-transition="slide">
    <span class="slide-badge">Baseline</span>
    <h2>HAR: Heterogeneous Autoregressive Model</h2>
    <p style="color:var(--text-secondary)">Corsi (2009). 3 features, 1 linear regression. The standard benchmark.</p>
    <div class="eq-block">
        $$\\log \\widehat{RV}_{t+1} = \\beta_0 + \\beta_d \\log RV_t + \\beta_w \\log \\overline{RV}_{t-4:t} + \\beta_m \\log \\overline{RV}_{t-21:t}$$
    </div>
    <div class="mermaid" style="margin-top:30px">
    graph LR
        D["<b>Daily</b><br/>log RV<sub>t</sub><br/><i style='font-size:0.8em'>Day traders</i>"]
        W["<b>Weekly</b><br/>log RV<sub>5d</sub><br/><i style='font-size:0.8em'>Portfolio managers</i>"]
        M["<b>Monthly</b><br/>log RV<sub>22d</sub><br/><i style='font-size:0.8em'>Pension funds</i>"]
        F["<b>Forecast</b><br/>log RV<sub>t+1</sub>"]
        D --> F
        W --> F
        M --> F
        style D fill:#0f3460,stroke:#4fc3f7,color:#e4e4e4
        style W fill:#0f3460,stroke:#66bb6a,color:#e4e4e4
        style M fill:#0f3460,stroke:#ffa726,color:#e4e4e4
        style F fill:#16213e,stroke:#4fc3f7,color:#4fc3f7,stroke-width:2px
    </div>
    <p style="font-size:var(--fs-tiny); color:var(--text-secondary); text-align:center; margin-top:10px;">
        Heterogeneous market hypothesis: different traders operate on different time scales
    </p>
</section>"""

_SLIDE_04_HARIV = """\
<section data-transition="slide">
    <span class="slide-badge">Extension</span>
    <h2>HAR-IV: Adding Forward-Looking Information</h2>
    <div class="columns">
        <div class="col-wide">
            <div class="eq-block">
                $$\\log \\widehat{RV}_{t+1} = \\beta_0 + \\beta_d \\log RV_t + \\beta_w \\log \\overline{RV}_{t-4:t} + \\beta_m \\log \\overline{RV}_{t-21:t} + \\beta_{iv} \\log IV_t^{ATM}$$
            </div>
            <div class="info-card accent" style="margin-top:20px">
                <strong>Why log-space?</strong>
                <ul style="margin:8px 0 0 0;">
                    <li>RV is approx log-normal, so log-RV is approx Gaussian</li>
                    <li>Symmetric errors, well-behaved residuals</li>
                    <li>No negative variance forecasts by construction</li>
                </ul>
            </div>
            <div class="info-card warning" style="margin-top:12px">
                <strong>Bias correction (Duan 1995):</strong>
                <div style="text-align:center; margin-top:8px">
                    $\\hat{\\sigma}^2 = \\exp(\\hat{y}) \\cdot E[\\exp(\\epsilon)]$
                </div>
                <p style="color:var(--text-secondary); margin-top:6px">
                    Smearing factor estimated non-parametrically from in-sample residuals
                </p>
            </div>
        </div>
        <div class="col-narrow">
            <div class="stat-box green" style="margin-top:20px">
                <div class="stat-value">+100</div>
                <div class="stat-label">bps QLIKE gain<br>over pure HAR</div>
            </div>
            <p style="color:var(--text-secondary); margin-top:15px; text-align:center">
                IV embeds the market's expectation of future vol. Forward-looking by construction.
            </p>
        </div>
    </div>
</section>"""

_SLIDE_05_STACK = """\
<section data-transition="slide">
    <span class="slide-badge">Architecture</span>
    <h2>Residual Stacking: HAR-IV + LightGBM</h2>
    <p style="color:var(--text-secondary); font-size:var(--fs-small)">The champion model: a strong linear prior + nonlinear residual learner</p>
    <div class="mermaid">
    graph TD
        A["<b>Training Data</b><br/>21 symbols x 2,800 days"]
        B["<b>HAR-IV</b><br/>4-param linear model<br/><i>Fit via OLS</i>"]
        C["<b>y&#x0302;<sub>base</sub></b><br/>Linear prediction"]
        D["<b>LightGBM</b><br/>init_score = y&#x0302;<sub>base</sub><br/>Custom QLIKE objective"]
        E["<b>f<sub>tree</sub>(X)</b><br/>Nonlinear residual"]
        F["<b>Final: y&#x0302; = y&#x0302;<sub>base</sub> + f<sub>tree</sub>(X)</b>"]
        A --> B
        B --> C
        A --> D
        C -.->|"init_score"| D
        D --> E
        C --> F
        E --> F
        style A fill:#16213e,stroke:#a0a0b0,color:#e4e4e4
        style B fill:#0f3460,stroke:#4fc3f7,color:#e4e4e4
        style C fill:#0f3460,stroke:#66bb6a,color:#e4e4e4
        style D fill:#0f3460,stroke:#ffa726,color:#e4e4e4
        style E fill:#0f3460,stroke:#ffa726,color:#e4e4e4
        style F fill:#16213e,stroke:#4fc3f7,color:#4fc3f7,stroke-width:2px
    </div>
    <div class="info-card accent" style="font-size:var(--fs-small)">
        <strong>Key insight:</strong> LightGBM's QLIKE gradients see the <em>full</em> target but start from the linear prediction. Trees only learn what's <em>left over</em> after removing linear structure -- better OOS generalization.
    </div>
</section>"""

_SLIDE_06_TENOR = """\
<section data-transition="slide">
    <span class="slide-badge">trial-036</span>
    <h2>Per-Horizon Tenor Matching</h2>
    <p style="color:var(--text-secondary); font-size:var(--fs-small)">Match the HAR-IV base's implied vol tenor to the forecast horizon to eliminate term premium contamination</p>
    <div class="mermaid">
    graph LR
        subgraph "Forecast Horizon"
            H1["<b>h = 1</b><br/>1-day ahead"]
            H5["<b>h = 5</b><br/>5-day ahead"]
            H22["<b>h = 22</b><br/>22-day ahead"]
        end
        subgraph "IV Tenor (HAR-IV base)"
            IV0["<b>0-DTE IV</b><br/>Same-day expiry"]
            IV1W["<b>1-Week IV</b><br/>Weekly expiry"]
            IV1M["<b>1-Month IV</b><br/>Monthly expiry"]
        end
        H1 ===|"exact match"| IV0
        H5 ===|"exact match"| IV1W
        H22 ===|"exact match"| IV1M
        style H1 fill:#0f3460,stroke:#4fc3f7,color:#e4e4e4
        style H5 fill:#0f3460,stroke:#66bb6a,color:#e4e4e4
        style H22 fill:#0f3460,stroke:#ffa726,color:#e4e4e4
        style IV0 fill:#16213e,stroke:#4fc3f7,color:#4fc3f7
        style IV1W fill:#16213e,stroke:#66bb6a,color:#66bb6a
        style IV1M fill:#16213e,stroke:#ffa726,color:#ffa726
    </div>
    <div class="stat-row">
        <div class="stat-box green">
            <div class="stat-value">+8 bps</div>
            <div class="stat-label">QLIKE gain at h=1<br>from tenor matching</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="font-size:1.1rem; color:var(--text-secondary)">Prior approach</div>
            <div class="stat-label">Used 1-week IV for ALL horizons<br>4-day term premium leaked into h=1</div>
        </div>
    </div>
</section>"""

_SLIDE_07_PRICE_TO_VAR = """\
<section data-transition="zoom">
    <span class="slide-badge">Layer 0 &middot; The Journey</span>
    <h2>From Price to Realized Variance</h2>
    <p style="color:var(--text-secondary); font-size:var(--fs-small)">The foundation: how do we measure volatility?</p>
    <div class="mermaid">
    graph TD
        P["<b>Price Series</b><br/>P<sub>t,1</sub>, P<sub>t,2</sub>, ..., P<sub>t,n</sub><br/><i style='font-size:0.8em'>5-minute intervals from tick data</i>"]
        R["<b>Log Returns</b><br/>r<sub>t,i</sub> = log(P<sub>t,i</sub> / P<sub>t,i-1</sub>)<br/><i style='font-size:0.8em'>Stationary, additive</i>"]
        S["<b>Squared Returns</b><br/>r<sub>t,i</sub>&#178;<br/><i style='font-size:0.8em'>Instantaneous variance contribution</i>"]
        RV["<b>Realized Variance</b><br/>RV<sub>t</sub> = &#931; r<sub>t,i</sub>&#178;<br/><i style='font-size:0.8em'>Daily volatility measure</i>"]
        P -->|"log difference"| R
        R -->|"square"| S
        S -->|"sum over day"| RV
        style P fill:#16213e,stroke:#a0a0b0,color:#e4e4e4
        style R fill:#0f3460,stroke:#4fc3f7,color:#e4e4e4
        style S fill:#0f3460,stroke:#ffa726,color:#e4e4e4
        style RV fill:#0f3460,stroke:#66bb6a,color:#66bb6a,stroke-width:2px
    </div>
    <div class="eq-block">
        $$RV_t = \\sum_{i=1}^{n} r_{t,i}^2 \\quad \\xrightarrow{n \\to \\infty} \\quad \\int_0^T \\sigma_s^2 \\, ds$$
    </div>
    <p style="font-size:var(--fs-tiny); color:var(--text-secondary); text-align:center">
        As sampling frequency increases, RV converges to the integrated variance (the "true" latent volatility)
    </p>
</section>"""

_SLIDE_08_LOG_QUALITY = """\
<section data-transition="zoom">
    <span class="slide-badge">Layer 0 &middot; Transform</span>
    <h2>Log Transform & Measurement Quality</h2>
    <div class="columns">
        <div class="col">
            <h3 style="color:var(--accent)">Why log-RV?</h3>
            <div style="display:flex; gap:20px; margin:15px 0;">
                <div style="flex:1; text-align:center;">
                    <svg width="140" height="80" viewBox="0 0 140 80">
                        <path d="M 10 70 Q 30 70 40 30 Q 50 5 60 20 Q 80 60 120 68" fill="none" stroke="#ef5350" stroke-width="2"/>
                        <text x="70" y="78" fill="#a0a0b0" font-size="10" text-anchor="middle">Raw RV</text>
                        <text x="100" y="25" fill="#ef5350" font-size="9">right-skewed</text>
                    </svg>
                </div>
                <div style="flex:0.3; display:flex; align-items:center; justify-content:center;">
                    <span style="font-size:1.3rem; color:var(--accent)">&#x2192;</span>
                </div>
                <div style="flex:1; text-align:center;">
                    <svg width="140" height="80" viewBox="0 0 140 80">
                        <path d="M 10 68 Q 40 65 55 40 Q 65 15 75 15 Q 85 15 95 40 Q 110 65 130 68" fill="none" stroke="#66bb6a" stroke-width="2"/>
                        <text x="70" y="78" fill="#a0a0b0" font-size="10" text-anchor="middle">log RV</text>
                        <text x="75" y="10" fill="#66bb6a" font-size="9">approx Gaussian</text>
                    </svg>
                </div>
            </div>
            <div class="eq-block">
                $$\\log RV_t \\approx \\mathcal{N}(\\mu, \\sigma^2)$$
            </div>
        </div>
        <div class="col">
            <h3 style="color:var(--warning)">Measurement Quality (HARQ)</h3>
            <p>Not all RV estimates are equally precise. Realized Quarticity measures noise:</p>
            <div class="eq-block">
                $$RQ_t = \\frac{n}{3}\\sum_{i=1}^{n} r_{t,i}^4$$
            </div>
            <div class="info-card warning">
                <strong>HARQ Interaction:</strong>
                <div style="margin-top:6px">$\\log(RV_t) \\times \\sqrt{RQ_t}$</div>
                <p style="margin-top:6px; color:var(--text-secondary)">
                    "Discount today's RV when measurement quality is poor"<br>
                    (Bollerslev, Patton & Quaedvlieg 2016)
                </p>
            </div>
        </div>
    </div>
</section>"""

_SLIDE_09_DECOMP = """\
<section data-transition="zoom">
    <span class="slide-badge">Layer 1 &middot; Decomposition</span>
    <h2>Breaking Down Variance: The Components</h2>
    <p style="color:var(--text-secondary); font-size:var(--fs-small)">Every day's realized variance decomposes into distinct economic forces</p>
    <div class="mermaid">
    graph TD
        RV["<b>Realized Variance</b><br/>RV<sub>t</sub> = &#931; r<sub>t,i</sub>&#178;<br/><i>Total daily variance</i>"]
        BPV["<b>Continuous Variation</b><br/>BPV<sub>t</sub> (Bipower Variation)<br/><i>Smooth, diffusive price movement</i>"]
        J["<b>Jump Variation</b><br/>J<sub>t</sub> = max(RV<sub>t</sub> - BPV<sub>t</sub>, 0)<br/><i>Rare, discontinuous shocks</i>"]
        RSP["<b>Upside Semivariance</b><br/>RS<sup>+</sup> = &#931; r<sub>i</sub>&#178; &middot; 1(r<sub>i</sub> &gt; 0)<br/><i>Variance from positive returns</i>"]
        RSN["<b>Downside Semivariance</b><br/>RS<sup>-</sup> = &#931; r<sub>i</sub>&#178; &middot; 1(r<sub>i</sub> &lt; 0)<br/><i>Variance from negative returns</i>"]
        LEV["<span style='color:#ef5350'><b>Leverage Effect</b></span><br/><i>RS<sup>-</sup> predicts more future vol<br/>than RS<sup>+</sup> (Black 1976)</i>"]
        RV -->|"BPV robust<br/>to jumps"| BPV
        RV -->|"residual"| J
        BPV -->|"positive returns"| RSP
        BPV -->|"negative returns"| RSN
        RSN -.->|"asymmetric<br/>predictability"| LEV
        style RV fill:#0f3460,stroke:#4fc3f7,color:#e4e4e4,stroke-width:2px
        style BPV fill:#0f3460,stroke:#66bb6a,color:#e4e4e4
        style J fill:#0f3460,stroke:#ef5350,color:#e4e4e4
        style RSP fill:#16213e,stroke:#66bb6a,color:#66bb6a
        style RSN fill:#16213e,stroke:#ef5350,color:#ef5350
        style LEV fill:#1a1a2e,stroke:#ef5350,color:#ef5350,stroke-dasharray:5 5
    </div>
    <div class="columns" style="margin-top:15px">
        <div class="col">
            <div class="eq-block" style="font-size:var(--fs-small)">
                $$BPV_t = \\frac{\\pi}{2} \\cdot \\frac{1}{n-1}\\sum_{i=2}^{n} |r_{t,i}| \\cdot |r_{t,i-1}|$$
            </div>
        </div>
        <div class="col">
            <div class="eq-block" style="font-size:var(--fs-small)">
                $$J_t = \\max\\left(RV_t - BPV_t,\\; 0\\right)$$
            </div>
        </div>
    </div>
    <p style="font-size:var(--fs-label); color:var(--text-secondary); text-align:center; margin-top:6px">
        Barndorff-Nielsen, Kinnebrock & Shephard (2010) &middot; SHAR: Patton & Sheppard (2015)
    </p>
</section>"""

_SLIDE_10_PCA = """\
<section data-transition="zoom">
    <span class="slide-badge">Layer 2 &middot; Options</span>
    <h2>The Volatility Surface: 85% in 3 Numbers</h2>
    <p style="color:var(--text-secondary); font-size:var(--fs-small)">PCA of the IV surface reveals three dominant modes of variation</p>
    <div style="text-align:center; margin: 15px 0;">
        <svg width="680" height="160" viewBox="0 0 680 160">
            <line x1="60" y1="130" x2="300" y2="130" stroke="#a0a0b0" stroke-width="1"/>
            <line x1="60" y1="130" x2="60" y2="20" stroke="#a0a0b0" stroke-width="1"/>
            <text x="180" y="150" fill="#a0a0b0" font-size="10" text-anchor="middle">Strike (&#916;)</text>
            <text x="30" y="75" fill="#a0a0b0" font-size="10" text-anchor="middle" transform="rotate(-90,30,75)">IV (%)</text>
            <path d="M 80 50 Q 120 80 180 85 Q 240 80 280 45" fill="none" stroke="#4fc3f7" stroke-width="2.5"/>
            <text x="80" y="45" fill="#ef5350" font-size="9">25&#916; Put</text>
            <text x="170" y="100" fill="#4fc3f7" font-size="9">ATM</text>
            <text x="260" y="40" fill="#66bb6a" font-size="9">25&#916; Call</text>
            <text x="330" y="80" fill="#a0a0b0" font-size="24">&#x2192;</text>
            <text x="350" y="95" fill="#a0a0b0" font-size="9">PCA</text>
            <rect x="380" y="30" width="80" height="100" rx="6" fill="#16213e" stroke="#4fc3f7" stroke-width="1.5"/>
            <text x="420" y="50" fill="#4fc3f7" font-size="9" text-anchor="middle" font-weight="bold">PC1: Level</text>
            <path d="M 395 90 L 445 90" stroke="#4fc3f7" stroke-width="1.5" stroke-dasharray="3"/>
            <path d="M 395 70 L 445 70" stroke="#4fc3f7" stroke-width="1.5"/>
            <text x="430" y="62" fill="#4fc3f7" font-size="7">&#x2191;</text>
            <text x="420" y="120" fill="#a0a0b0" font-size="8" text-anchor="middle">~60%</text>
            <rect x="480" y="30" width="80" height="100" rx="6" fill="#16213e" stroke="#ffa726" stroke-width="1.5"/>
            <text x="520" y="50" fill="#ffa726" font-size="9" text-anchor="middle" font-weight="bold">PC2: Skew</text>
            <path d="M 495 60 L 545 90" stroke="#ffa726" stroke-width="1.5"/>
            <path d="M 495 80 L 545 80" stroke="#ffa726" stroke-width="1" stroke-dasharray="3"/>
            <text x="520" y="120" fill="#a0a0b0" font-size="8" text-anchor="middle">~20%</text>
            <rect x="580" y="30" width="80" height="100" rx="6" fill="#16213e" stroke="#ab47bc" stroke-width="1.5"/>
            <text x="620" y="50" fill="#ab47bc" font-size="9" text-anchor="middle" font-weight="bold">PC3: Smile</text>
            <path d="M 595 70 Q 620 90 645 70" stroke="#ab47bc" stroke-width="1.5"/>
            <path d="M 595 80 L 645 80" stroke="#ab47bc" stroke-width="1" stroke-dasharray="3"/>
            <text x="620" y="120" fill="#a0a0b0" font-size="8" text-anchor="middle">~5%</text>
        </svg>
    </div>
    <div class="pca-grid">
        <div class="pca-card pc1">
            <div class="pca-label">Principal Component 1</div>
            <div class="pca-pct">~60%</div>
            <div class="pca-name">Level (Parallel Shift)</div>
            <div style="margin:6px 0">$IV_{ATM}$</div>
            <div class="pca-proxy">Feature: <code>log_atm_iv_d/w/m</code></div>
        </div>
        <div class="pca-card pc2">
            <div class="pca-label">Principal Component 2</div>
            <div class="pca-pct">~20%</div>
            <div class="pca-name">Skew (Risk Reversal)</div>
            <div style="margin:6px 0">$IV_{25\\delta P} - IV_{25\\delta C}$</div>
            <div class="pca-proxy">Feature: <code>iv_skew_d/w</code></div>
        </div>
        <div class="pca-card pc3">
            <div class="pca-label">Principal Component 3</div>
            <div class="pca-pct">~5%</div>
            <div class="pca-name">Convexity (Butterfly)</div>
            <div style="margin:6px 0">$\\frac{1}{2}(IV_{25\\delta P} + IV_{25\\delta C}) - IV_{ATM}$</div>
            <div class="pca-proxy">Feature: <code>iv_butterfly_d/w</code></div>
        </div>
    </div>
    <div class="info-card accent" style="text-align:center;">
        <strong>85% of all vol surface movement captured by 3 intuitive features.</strong>
        The remaining 15% is noise, illiquidity artifacts, and higher-order effects.
    </div>
</section>"""

_SLIDE_11_VRP = """\
<section data-transition="zoom">
    <span class="slide-badge">Layer 2 &middot; Signal</span>
    <h2>Variance Risk Premium & IV-RV Interactions</h2>
    <div class="columns">
        <div class="col">
            <h3 style="color:var(--accent)">Variance Risk Premium</h3>
            <div class="eq-block">
                $$VRP_t = \\left(\\frac{IV_t}{100}\\right)^2 - RV_t \\times 252$$
            </div>
            <p style="font-size:var(--fs-small); color:var(--text-secondary)">The "insurance premium" investors pay for vol protection. Positive on average (Carr & Wu 2009). When VRP is large, options are expensive -- sell variance.</p>
            <h3 style="color:var(--warning); margin-top:16px">Term Structure</h3>
            <div class="eq-block">
                $$\\text{Slope}_{0DTE \\to 1W} = IV_{1W} - IV_{0DTE}$$
            </div>
            <p style="font-size:var(--fs-small); color:var(--text-secondary)">Normally in contango (upward sloping). Inversion signals gamma spikes, imminent realized vol events.</p>
        </div>
        <div class="col">
            <h3 style="color:var(--success)">IV x RV Interactions</h3>
            <div class="info-card success">
                <strong>#1 ML gain source</strong> (Christensen, Siggaard & Veliyev 2023)
                <div style="margin-top:8px">
                    $IV_{ATM} \\times \\log(RV_t)$
                </div>
                <p style="margin-top:6px; color:var(--text-secondary)">
                    The <em>relationship</em> between implied and realized vol varies with regime:
                </p>
                <ul>
                    <li>High IV + High RV: VRP behaves differently</li>
                    <li>High IV + Low RV: overpriced (sell)</li>
                    <li>Low IV + Low RV: regime-dependent</li>
                </ul>
            </div>
            <div class="info-card">
                <strong>VVIX</strong>: Vol-of-vol (uncertainty about uncertainty)
                <div style="margin-top:4px">$VVIX\\_RP = VVIX/100 - \\text{RealizedVolOfVIX}$</div>
            </div>
        </div>
    </div>
</section>"""

_SLIDE_12_LAYERS = """\
<section data-transition="zoom">
    <span class="slide-badge">Layers 3-5</span>
    <h2>Noise, Calendar & Feature Expansion</h2>
    <div class="columns">
        <div class="col">
            <h3 style="color:var(--accent)">Layer 3: Noise-Robust</h3>
            <div class="info-card">
                <strong>Realized Kernel</strong> (Barndorff-Nielsen et al. 2008)
                <div style="margin:8px 0">$RK_t = \\sum_{h=-H}^{H} k(h/H) \\cdot \\hat{\\gamma}_h$</div>
                <p style="color:var(--text-secondary)">Parzen kernel weights autocovariances -- corrects bid-ask bounce</p>
                <div style="margin-top:8px"><strong>Noise gap:</strong> $RV_t - RK_t$ = microstructure noise estimate</div>
            </div>
            <h3 style="color:var(--warning); margin-top:20px">Layer 4: Calendar</h3>
            <div class="info-card">
                <table style="margin:0;">
                    <tr><td><code>days_to_fomc</code></td><td>Vol compresses before, spikes on announcement</td></tr>
                    <tr><td><code>days_to_nfp</code></td><td>Non-Farm Payrolls, labor data shock</td></tr>
                    <tr><td><code>days_to_opex</code></td><td>Options expiration, gamma pinning</td></tr>
                    <tr><td><code>day_of_week</code></td><td>Monday/Friday effects</td></tr>
                </table>
                <p style="color:var(--text-secondary); margin-top:8px">Only features known in advance, no shift needed</p>
            </div>
        </div>
        <div class="col">
            <h3 style="color:var(--success)">Layer 5: Tree Expansion</h3>
            <p style="color:var(--text-secondary)">For every continuous feature, compute two additional transforms:</p>
            <table>
                <thead>
                    <tr><th>Transform</th><th>Formula</th><th>Purpose</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>_change</code></td>
                        <td>$x_t - x_{t-1}$</td>
                        <td>Momentum</td>
                    </tr>
                    <tr>
                        <td><code>_zscore</code></td>
                        <td>$\\frac{x_t - \\overline{x}_{20}}{\\sigma_{20}}$</td>
                        <td>Regime deviation</td>
                    </tr>
                </tbody>
            </table>
            <div class="stat-row" style="margin-top:25px">
                <div class="stat-box">
                    <div class="stat-value">~65</div>
                    <div class="stat-label">Base features<br>(Layers 0-4)</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" style="color:var(--text-secondary)">x2</div>
                    <div class="stat-label">Expansion</div>
                </div>
                <div class="stat-box green">
                    <div class="stat-value">~128</div>
                    <div class="stat-label">Total features<br>into LightGBM</div>
                </div>
            </div>
            <p style="font-size:var(--fs-tiny); color:var(--text-secondary); margin-top:10px">
                Expansion features contribute ~9% of total SHAP importance collectively
            </p>
        </div>
    </div>
</section>"""

_SLIDE_13_QLIKE = """\
<section data-transition="slide">
    <span class="slide-badge">Evaluation</span>
    <h2>QLIKE: The Right Loss Function</h2>
    <div class="eq-block">
        $$QLIKE = \\frac{1}{T}\\sum_{t=1}^{T} \\left[\\frac{RV_t}{\\hat{h}_t} - \\log\\frac{RV_t}{\\hat{h}_t} - 1\\right]$$
    </div>
    <p style="color:var(--text-secondary); text-align:center">Minimized when $RV_t / \\hat{h}_t = 1$ for all $t$. Measures proportional forecast error.</p>
    <div class="columns" style="margin-top:20px">
        <div class="col">
            <h3 style="color:var(--danger)">Why not MSE?</h3>
            <ul>
                <li><strong>Scale invariance</strong>: 2x error at 10% vol = same penalty as at 40% vol. MSE lets COVID dominate everything.</li>
                <li><strong>Asymmetric penalty</strong>: underpredicting is costlier (sell options too cheap)</li>
                <li><strong>Proxy robustness</strong> (Patton 2011): QLIKE rankings are <em>consistent</em> regardless of proxy noise. MSE rankings can flip.</li>
            </ul>
        </div>
        <div class="col">
            <h3 style="color:var(--warning)">Natural Asymmetry</h3>
            <div class="asymmetry-bar">
                <span class="label">2x underestimate</span>
                <div class="bar under">0.307</div>
            </div>
            <div class="asymmetry-bar">
                <span class="label">2x overestimate</span>
                <div class="bar over">0.193</div>
            </div>
            <p style="color:var(--text-secondary); margin-top:15px">Underestimating vol is 60% more costly. Matches economic reality.</p>
            <h3 style="color:var(--accent); margin-top:20px">Custom LightGBM Objective</h3>
            <div class="info-card">
                $g_i = 1 - \\exp(y_i - \\hat{y}_i)$<br>
                $h_i = \\exp(y_i - \\hat{y}_i)$
                <p style="color:var(--text-secondary); margin-top:6px">Tree splits optimized end-to-end for QLIKE</p>
            </div>
        </div>
    </div>
</section>"""

_SLIDE_14_CV = """\
<section data-transition="slide">
    <span class="slide-badge">Protocol</span>
    <h2>Purged Expanding-Window Walk-Forward</h2>
    <p style="color:var(--text-secondary); font-size:var(--fs-small)">Every number on the dashboard is purely out-of-sample. No lookahead, no leakage.</p>
    <div class="cv-timeline">
        <div class="track">
            <span class="track-label">Fold 1</span>
            <div class="track-bar">
                <div class="segment seg-train" style="flex:4">Train (504d)</div>
                <div class="segment seg-purge" style="flex:0.3" title="10-day purge gap">&#9888;</div>
                <div class="segment seg-test" style="flex:1">Test (126d)</div>
                <div class="segment seg-future" style="flex:6"></div>
            </div>
        </div>
        <div class="track">
            <span class="track-label">Fold 2</span>
            <div class="track-bar">
                <div class="segment seg-train" style="flex:5.2">Train (expands)</div>
                <div class="segment seg-purge" style="flex:0.3">&#9888;</div>
                <div class="segment seg-test" style="flex:1">Test</div>
                <div class="segment seg-future" style="flex:4.8"></div>
            </div>
        </div>
        <div class="track">
            <span class="track-label">Fold 3</span>
            <div class="track-bar">
                <div class="segment seg-train" style="flex:6.4">Train (expands)</div>
                <div class="segment seg-purge" style="flex:0.3">&#9888;</div>
                <div class="segment seg-test" style="flex:1">Test</div>
                <div class="segment seg-future" style="flex:3.6"></div>
            </div>
        </div>
        <div class="track">
            <span class="track-label" style="color:var(--accent)">Fold N</span>
            <div class="track-bar">
                <div class="segment seg-train" style="flex:9.5">Train (full history)</div>
                <div class="segment seg-purge" style="flex:0.3">&#9888;</div>
                <div class="segment seg-test" style="flex:1">Test</div>
            </div>
        </div>
    </div>
    <div class="columns" style="margin-top:15px">
        <div class="col">
            <div class="info-card accent">
                <strong>Purge Gap: 10 trading days</strong><br>
                Accounts for overlapping targets: $RV_{t+1}$ uses tomorrow's returns which overlap with today's close-to-close.
                Panel-aware: purge computed in <em>dates</em>, not row indices (multiple symbols per date).
            </div>
        </div>
        <div class="col">
            <div class="info-card warning">
                <strong>Multi-seed validation</strong><br>
                Single-seed can be lucky. All champion claims require 3+ seeds, report mean +/- std.
                Trial-047 reseed: 5 seeds confirmed trial-036 champion status.
            </div>
        </div>
    </div>
</section>"""

_SLIDE_15_TESTS = """\
<section data-transition="slide">
    <span class="slide-badge">Inference</span>
    <h2>Statistical Significance: DM & MCS</h2>
    <div class="columns">
        <div class="col">
            <h3 style="color:var(--accent)">Diebold-Mariano Test</h3>
            <p style="color:var(--text-secondary)">Is model A's loss significantly lower than B's?</p>
            <div class="eq-block">
                $$DM = \\frac{\\bar{d}}{\\sqrt{\\hat{V}(d)/T}} \\quad \\sim N(0,1)$$
            </div>
            <div class="info-card">
                <div>$d_t = L_{baseline}(t) - L_{model}(t)$</div>
                <div style="margin-top:6px">$\\hat{V}(d)$: Newey-West HAC with Bartlett kernel</div>
                <div style="margin-top:6px">Bandwidth = $h - 1$ for horizon $h$</div>
                <div style="margin-top:8px; color:var(--success)">Positive DM means our model wins</div>
            </div>
        </div>
        <div class="col">
            <h3 style="color:var(--warning)">Model Confidence Set</h3>
            <p style="color:var(--text-secondary)">Hansen, Lunde & Nason (2011). The set containing the true best model at 90% confidence.</p>
            <div class="info-card">
                <strong>Sequential elimination:</strong>
                <ol style="padding-left:20px; margin:8px 0">
                    <li style="margin:4px 0">Start with all models</li>
                    <li style="margin:4px 0">Compute range statistic $T_R = \\max_{i,j}|t_{ij}|$</li>
                    <li style="margin:4px 0">Bootstrap under null (10,000 replicates)</li>
                    <li style="margin:4px 0">If p &lt; 0.10: eliminate worst model, repeat</li>
                    <li style="margin:4px 0">Otherwise: remaining models = MCS</li>
                </ol>
            </div>
            <p style="color:var(--text-secondary); margin-top:10px">
                If only LightGBM + HAR-IV are in the MCS, we reject (at 90% confidence) that any other model is as good.
            </p>
        </div>
    </div>
</section>"""

_SLIDE_16_SIGNAL = """\
<section data-transition="slide">
    <span class="slide-badge">Application</span>
    <h2>GSVIVS01: The Trading Signal</h2>
    <p style="color:var(--text-secondary); font-size:var(--fs-small)">Upgrading a blind short-variance carry trade into a directional strategy</p>
    <div class="signal-diagram">
        <div class="signal-box forecast">
            <div style="color:var(--text-secondary)">Our Model</div>
            <div style="font-size:1.1rem; font-weight:600; color:var(--accent)">$\\widehat{RV}_{t+1}$</div>
            <div style="color:var(--text-secondary)">Made at last night's close</div>
        </div>
        <div class="signal-arrow">vs</div>
        <div class="signal-box kvar">
            <div style="color:var(--text-secondary)">Market Price</div>
            <div style="font-size:1.1rem; font-weight:600; color:var(--warning)">$K_{var}$</div>
            <div style="color:var(--text-secondary)">Variance swap strike (EDRVS)</div>
        </div>
        <div class="signal-arrow">&#x2192;</div>
        <div class="signal-box decision">
            <div style="color:var(--text-secondary)">Decision @ 09:10 ET</div>
            <div style="margin-top:4px">
                <span style="color:var(--success)">$K_{var} > \\widehat{RV}$</span> &#x2192; <strong>Short</strong><br>
                <span style="color:var(--danger)">$K_{var} < \\widehat{RV}$</span> &#x2192; <strong>Flat</strong>
            </div>
        </div>
    </div>
    <div class="columns" style="margin-top:20px">
        <div class="col">
            <h3 style="color:var(--accent)">Carr-Madan Variance Swap Strike</h3>
            <div class="eq-block">
                $$K_{var} = \\frac{2}{T}\\left[\\int_0^F \\frac{P(K)}{K^2}dK + \\int_F^\\infty \\frac{C(K)}{K^2}dK\\right]$$
            </div>
            <p style="color:var(--text-secondary)">
                Model-free. $1/K^2$ weighting gives more weight to OTM puts (skew), so $K_{var} > IV_{ATM}$ always.
            </p>
        </div>
        <div class="col">
            <div class="stat-row">
                <div class="stat-box green">
                    <div class="stat-value">~2%</div>
                    <div class="stat-label">Days signal<br>= "go flat"</div>
                </div>
                <div class="stat-box green">
                    <div class="stat-value">70%</div>
                    <div class="stat-label">Precision on<br>flat calls</div>
                </div>
            </div>
            <p style="color:var(--text-secondary); margin-top:8px; text-align:center">
                Edge is concentrated: correctly avoiding ~10 worst days/year
            </p>
        </div>
    </div>
</section>"""

_SLIDE_17_RESULTS = """\
<section data-transition="slide">
    <span class="slide-badge">Results</span>
    <h2>Tournament Results: 5-Seed Means (trial-047)</h2>
    <table style="margin-top:20px">
        <thead>
            <tr>
                <th>Horizon</th>
                <th>Champion</th>
                <th>QLIKE</th>
                <th>vs HAR-IV (bps)</th>
                <th>DM Significant?</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>h = 1</strong></td>
                <td style="color:var(--accent)">LightGBM + har_iv_0dte</td>
                <td><strong>0.13679</strong></td>
                <td style="color:var(--success)">+153 bps</td>
                <td style="color:var(--success)">Yes (p &lt; 0.01)</td>
            </tr>
            <tr>
                <td><strong>h = 5</strong></td>
                <td style="color:var(--accent)">LightGBM + har_iv_1w</td>
                <td><strong>0.10804</strong></td>
                <td style="color:var(--success)">+138 bps</td>
                <td style="color:var(--success)">Yes (p &lt; 0.01)</td>
            </tr>
            <tr>
                <td><strong>h = 22</strong></td>
                <td style="color:var(--warning)">HAR-IV (4 params!)</td>
                <td><strong>0.16755</strong></td>
                <td style="color:var(--danger)">LightGBM is -7 bps WORSE</td>
                <td style="color:var(--text-secondary)">No</td>
            </tr>
        </tbody>
    </table>
    <div class="info-card danger" style="margin-top:15px">
        <strong>h = 22 insight:</strong> At the monthly horizon, a 4-parameter linear model beats 128-feature gradient boosting. ATM 1-month IV already contains so much forward information that trees cannot improve on it. <em>Know when to stop.</em>
    </div>
    <div class="stat-row" style="margin-top:20px">
        <div class="stat-box green">
            <div class="stat-value">1.95</div>
            <div class="stat-label">GSVIVS01 Sharpe<br>(with signal)</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color:var(--text-secondary)">1.60</div>
            <div class="stat-label">Always-short Sharpe<br>(no signal)</div>
        </div>
        <div class="stat-box green">
            <div class="stat-value">+22%</div>
            <div class="stat-label">Sharpe improvement<br>Zero additional TC</div>
        </div>
        <div class="stat-box red">
            <div class="stat-value">~0.3</div>
            <div class="stat-label">MSE-optimized Sharpe<br><em>Loss function matters</em></div>
        </div>
    </div>
</section>"""

_SLIDE_18_CLOSING = """\
<section class="title-slide" data-transition="fade">
    <h2 style="margin-bottom:30px">Summary</h2>
    <div style="text-align:left; max-width:700px; margin:0 auto;">
        <ul style="line-height:2">
            <li>Pure carry trade to ML-augmented directional signal</li>
            <li>Residual stack: HAR-IV (tenor-matched) + LightGBM (QLIKE objective)</li>
            <li>128 features across 5 layers, interpretable decomposition</li>
            <li>Rigorous OOS evaluation: purged CV, 5-seed, DM tests, MCS</li>
            <li>+22% Sharpe by going flat on ~2% of days (zero additional TC)</li>
        </ul>
    </div>
    <div style="margin-top:40px">
        <h3 style="color:var(--warning)">Next Steps</h3>
        <div style="display:flex; gap:20px; justify-content:center; margin-top:15px">
            <div class="info-card" style="flex:1; max-width:250px; text-align:center">
                Cache EDRVS_EXPIRY Kvar<br><span style="color:var(--text-secondary)">Backtest fidelity</span>
            </div>
            <div class="info-card" style="flex:1; max-width:250px; text-align:center">
                LSTM on raw tick sequences<br><span style="color:var(--text-secondary)">trial-051, intraday patterns</span>
            </div>
            <div class="info-card" style="flex:1; max-width:250px; text-align:center">
                Production deployment<br><span style="color:var(--text-secondary)">09:10 ET signal pipeline</span>
            </div>
        </div>
    </div>
</section>"""


def _get_slides() -> str:
    slides = [
        _SLIDE_01_TITLE,
        _SLIDE_02_PROBLEM,
        _SLIDE_03_HAR,
        _SLIDE_04_HARIV,
        _SLIDE_05_STACK,
        _SLIDE_06_TENOR,
        _SLIDE_07_PRICE_TO_VAR,
        _SLIDE_08_LOG_QUALITY,
        _SLIDE_09_DECOMP,
        _SLIDE_10_PCA,
        _SLIDE_11_VRP,
        _SLIDE_12_LAYERS,
        _SLIDE_13_QLIKE,
        _SLIDE_14_CV,
        _SLIDE_15_TESTS,
        _SLIDE_16_SIGNAL,
        _SLIDE_17_RESULTS,
        _SLIDE_18_CLOSING,
    ]
    return "\n\n".join(slides)


# ---------------------------------------------------------------------------
# JAVASCRIPT
# ---------------------------------------------------------------------------


def _get_js(dashboard_path: str) -> str:
    # Escape single quotes in dashboard_path for JS string safety
    safe_path = dashboard_path.replace("'", "\\'")
    return (
        "// Dashboard configuration\n"
        f"const DASHBOARD_PATH = '{safe_path}';\n"
        "\n"
        "// Initialize Reveal.js\n"
        "Reveal.initialize({\n"
        "    hash: true,\n"
        "    slideNumber: true,\n"
        "    transition: 'slide',\n"
        "    transitionSpeed: 'default',\n"
        "    backgroundTransition: 'fade',\n"
        "    center: false,\n"
        "    width: 1280,\n"
        "    height: 720,\n"
        "    margin: 0.04,\n"
        "    controls: true,\n"
        "    progress: true,\n"
        "    history: true,\n"
        "});\n"
        "\n"
        "// Initialize Mermaid after Reveal is ready\n"
        "Reveal.on('ready', () => {\n"
        "    mermaid.initialize({\n"
        "        startOnLoad: false,\n"
        "        theme: 'base',\n"
        "        themeVariables: {\n"
        "            primaryColor: '#0f3460',\n"
        "            primaryTextColor: '#e4e4e4',\n"
        "            primaryBorderColor: '#4fc3f7',\n"
        "            lineColor: '#4fc3f7',\n"
        "            secondaryColor: '#16213e',\n"
        "            tertiaryColor: '#1a1a2e',\n"
        "            background: '#1a1a2e',\n"
        "            mainBkg: '#0f3460',\n"
        "            nodeBorder: '#4fc3f7',\n"
        "            clusterBkg: '#16213e',\n"
        "            clusterBorder: '#2a2a4a',\n"
        "            titleColor: '#4fc3f7',\n"
        "            edgeLabelBackground: '#16213e',\n"
        "            fontSize: '14px',\n"
        "        },\n"
        "        flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },\n"
        "    });\n"
        "    mermaid.run({ nodes: document.querySelectorAll('.mermaid') });\n"
        "});\n"
        "\n"
        "// Re-render KaTeX on slide change\n"
        "Reveal.on('slidechanged', () => {\n"
        "    if (typeof renderMathInElement === 'function') {\n"
        "        renderMathInElement(document.body, {\n"
        "            delimiters: [\n"
        "                { left: '$$', right: '$$', display: true },\n"
        "                { left: '$', right: '$', display: false }\n"
        "            ]\n"
        "        });\n"
        "    }\n"
        "});\n"
        "\n"
        "// Dashboard toggle\n"
        "let dashboardVisible = false;\n"
        "const overlay = document.getElementById('dashboard-overlay');\n"
        "const frame = document.getElementById('dashboard-frame');\n"
        "const toggleBtn = document.getElementById('dashboard-toggle');\n"
        "const toggleIcon = document.getElementById('toggle-icon');\n"
        "const toggleText = document.getElementById('toggle-text');\n"
        "\n"
        "function toggleDashboard() {\n"
        "    dashboardVisible = !dashboardVisible;\n"
        "    if (dashboardVisible) {\n"
        "        if (!frame.src || frame.src === window.location.href) {\n"
        "            frame.src = DASHBOARD_PATH;\n"
        "        }\n"
        "        overlay.style.display = 'block';\n"
        "        requestAnimationFrame(() => overlay.classList.add('visible'));\n"
        "        toggleBtn.classList.add('active');\n"
        "        toggleIcon.textContent = '\\u2715';\n"
        "        toggleText.textContent = 'Back to Slides';\n"
        "        Reveal.configure({ keyboard: false });\n"
        "    } else {\n"
        "        overlay.classList.remove('visible');\n"
        "        setTimeout(() => { overlay.style.display = 'none'; }, 300);\n"
        "        toggleBtn.classList.remove('active');\n"
        "        toggleIcon.textContent = '\\ud83d\\udcca';\n"
        "        toggleText.textContent = 'Dashboard';\n"
        "        Reveal.configure({ keyboard: true });\n"
        "    }\n"
        "}\n"
        "\n"
        "document.addEventListener('keydown', (e) => {\n"
        "    if (e.key === 'Escape' && dashboardVisible) {\n"
        "        toggleDashboard();\n"
        "    }\n"
        "});\n"
    )


# ---------------------------------------------------------------------------
# ASSEMBLY
# ---------------------------------------------------------------------------


def generate(dashboard_path: str) -> str:
    """Return the complete HTML string for the presentation."""
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '    <meta charset="UTF-8">\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '    <title>ML Realized Volatility Forecasting - Capstone Presentation</title>\n'
        '    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">\n'
        '    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/black.css">\n'
        '    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">\n'
        '    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>\n'
        '    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"\n'
        "        onload=\"renderMathInElement(document.body, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]});\"></script>\n"
        '    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>\n'
        '    <style>\n'
        f'{_CSS}'
        '    </style>\n'
        '</head>\n'
        '<body>\n'
        '\n'
        '<button id="dashboard-toggle" onclick="toggleDashboard()">\n'
        '    <span id="toggle-icon">\U0001f4ca</span>\n'
        '    <span id="toggle-text">Dashboard</span>\n'
        '</button>\n'
        '\n'
        '<div id="dashboard-overlay">\n'
        '    <iframe id="dashboard-frame" src="" loading="lazy"></iframe>\n'
        '</div>\n'
        '\n'
        '<div class="reveal">\n'
        '<div class="slides">\n'
        '\n'
        f'{_get_slides()}\n'
        '\n'
        '</div>\n'
        '</div>\n'
        '\n'
        '<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>\n'
        '<script>\n'
        f'{_get_js(dashboard_path)}'
        '</script>\n'
        '\n'
        '</body>\n'
        '</html>\n'
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate presentation.html with configurable dashboard path",
    )
    parser.add_argument(
        "--dashboard-path",
        required=True,
        help="Path to tournament dashboard HTML (relative to repo root, or already relative to output file)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: <script_dir>/presentation.html)",
    )
    args = parser.parse_args()

    output = (
        Path(args.output)
        if args.output
        else Path(__file__).parent / "presentation.html"
    )

    # Resolve dashboard path relative to output file location.
    # If the user passes a path relative to repo root (e.g. src/data/models/...),
    # compute the correct relative path from the output HTML's directory.
    repo_root = Path(__file__).resolve().parent.parent.parent  # workspace/presentation -> workspace -> repo
    dashboard_input = Path(args.dashboard_path)
    output_resolved = output.resolve()

    if not dashboard_input.is_absolute() and not args.dashboard_path.startswith(".."):
        # Treat as relative to repo root, compute relative path from output dir
        dashboard_abs = repo_root / dashboard_input
        try:
            rel_path = os.path.relpath(dashboard_abs, output_resolved.parent)
        except ValueError:
            rel_path = args.dashboard_path
        dashboard_rel = rel_path
    else:
        dashboard_rel = args.dashboard_path

    html = generate(dashboard_rel)

    # Safety check: no em dashes (U+2014) or en dashes (U+2013)
    if "\u2014" in html:
        raise ValueError("Em dash (U+2014) found in generated HTML!")
    if "\u2013" in html:
        raise ValueError("En dash (U+2013) found in generated HTML!")

    output.write_text(html, encoding="utf-8")
    print(f"Generated: {output}  ({len(html):,} bytes, {html.count(chr(10)):,} lines)")


if __name__ == "__main__":
    main()
