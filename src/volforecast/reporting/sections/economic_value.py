"""Economic value section: IV-RV gap signal, P&L curves, Sharpe.

Renders realistic delta-hedged straddle metrics using the Phase 1
analytic engine (tenor-decayed gamma, vanna/volga, cost bands, DSR).
Gracefully handles missing IV data by rendering a placeholder message.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def render(
    predictions: dict[str, dict[int, pd.DataFrame]],
    market_data: pd.DataFrame | None = None,
) -> str:
    """Render the economic value section as an HTML fragment.

    Parameters
    ----------
    predictions : dict
        ``{symbol: {horizon: DataFrame}}`` with ``prediction`` column.
    market_data : pd.DataFrame, optional
        Daily market data with columns: iv_1m_atm (%), close, log_rv,
        and optionally 'symbol' for multi-symbol data.
        If None, section renders a placeholder.

    Returns
    -------
    str
        HTML ``<section>`` block with delta-hedged straddle metrics,
        cost band table, and cumulative P&L summary.
    """
    if market_data is None:
        return (
            '<section id="economic-value">\n'
            "<h2>Economic Value</h2>\n"
            '<p class="placeholder">Market data (IV, spot) not available. '
            "Economic value tests require iv_1m_atm and close columns.</p>\n"
            "</section>"
        )

    from volforecast.evaluation.realistic_straddle import (
        realistic_delta_hedged_sharpe,
    )

    rows: list[dict] = []

    for symbol, horizons in predictions.items():
        # Filter market_data for this symbol
        if "symbol" in market_data.columns:
            sym_md = market_data[market_data["symbol"] == symbol]
        else:
            sym_md = market_data

        if sym_md.empty:
            continue

        # Need iv_1m_atm and close columns
        if "iv_1m_atm" not in sym_md.columns or "close" not in sym_md.columns:
            continue

        for horizon, pred_df in horizons.items():
            if "prediction" not in pred_df.columns:
                continue

            # Align data on common index
            common_idx = pred_df.index.intersection(sym_md.index)
            if len(common_idx) < 60:
                continue
            common_idx = common_idx.sort_values()

            log_rv_preds = pred_df.loc[common_idx, "prediction"].values

            # IV: shift(1) to avoid look-ahead, convert from % to decimal
            iv_series = sym_md["iv_1m_atm"].reindex(common_idx).shift(1)
            spot_series = sym_md["close"].reindex(common_idx)

            # Realized variance from log_rv if available
            if "log_rv" in sym_md.columns:
                rv_series = np.exp(sym_md["log_rv"].reindex(common_idx))
            else:
                # Fallback: use predictions as proxy (less useful)
                rv_series = np.exp(pd.Series(log_rv_preds, index=common_idx))

            # Drop NaN rows
            mask = (
                ~np.isnan(iv_series.values)
                & ~np.isnan(spot_series.values)
                & ~np.isnan(rv_series.values)
                & ~np.isnan(log_rv_preds)
            )
            if mask.sum() < 60:
                continue

            iv_arr = iv_series.values[mask] / 100.0
            spot_arr = spot_series.values[mask]
            rv_arr = rv_series.values[mask]
            pred_arr = log_rv_preds[mask]

            try:
                result = realistic_delta_hedged_sharpe(
                    log_rv_predictions=pred_arr,
                    implied_vol=iv_arr,
                    realized_var=rv_arr,
                    spot_prices=spot_arr,
                    n_bootstrap=500,
                    bootstrap_seed=42,
                )
            except Exception:
                continue

            cost_band = result.get("cost_band", {})
            bootstrap_ci = result.get("bootstrap_ci", (None, None))

            rows.append(
                {
                    "symbol": symbol,
                    "horizon": horizon,
                    "sharpe_raw": result["dh_sharpe"],
                    "sharpe_adjusted": result["dh_sharpe_adjusted"],
                    "sharpe_timing": cost_band.get("timing_aware", None),
                    "sharpe_effective": cost_band.get("effective", None),
                    "sharpe_quoted": cost_band.get("quoted", None),
                    "cum_pnl": result["dh_pnl"],
                    "max_dd": result["dh_max_dd"],
                    "hit_rate": result["dh_hit_rate"],
                    "dsr": result.get("dsr", None),
                    "ci_low": bootstrap_ci[0],
                    "ci_high": bootstrap_ci[1],
                    "n_obs": int(mask.sum()),
                }
            )

    if not rows:
        return (
            '<section id="economic-value">\n'
            "<h2>Economic Value</h2>\n"
            '<p class="placeholder">Insufficient data for economic value '
            "computation (need IV, spot, and predictions aligned).</p>\n"
            "</section>"
        )

    # Build HTML table
    html_parts = [
        '<section id="economic-value">',
        "<h2>Economic Value: Realistic Delta-Hedged Straddle</h2>",
        "<p>Phase 1 analytic engine: tenor-decayed gamma, vanna/volga, "
        "event-driven option costs, Leland hedge costs, "
        "Boyle-Emanuel hedge error variance.</p>",
        _render_metrics_table(rows),
        _render_cost_band_table(rows),
        "</section>",
    ]
    return "\n".join(html_parts)


def _render_metrics_table(rows: list[dict]) -> str:
    """Render the main metrics summary table."""
    lines = [
        "<h3>Sharpe Ratios &amp; P&amp;L</h3>",
        "<table>",
        "<thead><tr>",
        "<th>Symbol</th><th>h</th><th>Sharpe (raw)</th>",
        "<th>Sharpe (adj)</th><th>DSR</th>",
        "<th>95% CI</th><th>Cum P&amp;L (%)</th>",
        "<th>Max DD (%)</th><th>Hit Rate</th><th>N</th>",
        "</tr></thead>",
        "<tbody>",
    ]
    for r in rows:
        ci_str = f"[{r['ci_low']:.2f}, {r['ci_high']:.2f}]" if r["ci_low"] is not None else "—"
        dsr_str = f"{r['dsr']:.3f}" if r["dsr"] is not None else "—"
        lines.append(
            f"<tr><td>{r['symbol']}</td><td>{r['horizon']}</td>"
            f"<td>{r['sharpe_raw']:.2f}</td>"
            f"<td>{r['sharpe_adjusted']:.2f}</td>"
            f"<td>{dsr_str}</td>"
            f"<td>{ci_str}</td>"
            f"<td>{r['cum_pnl']:.1f}</td>"
            f"<td>{r['max_dd']:.1f}</td>"
            f"<td>{r['hit_rate']:.1%}</td>"
            f"<td>{r['n_obs']}</td></tr>"
        )
    lines.extend(["</tbody>", "</table>"])
    return "\n".join(lines)


def _render_cost_band_table(rows: list[dict]) -> str:
    """Render cost band sensitivity table."""
    lines = [
        "<h3>Cost Band Sensitivity (Sharpe)</h3>",
        "<p>Base option spread: timing-aware=0.5, effective=1.0, quoted=1.5 vol pts.</p>",
        "<table>",
        "<thead><tr>",
        "<th>Symbol</th><th>h</th>",
        "<th>Timing-Aware</th><th>Effective</th><th>Quoted</th>",
        "</tr></thead>",
        "<tbody>",
    ]
    for r in rows:
        ta = f"{r['sharpe_timing']:.2f}" if r["sharpe_timing"] else "—"
        eff = f"{r['sharpe_effective']:.2f}" if r["sharpe_effective"] else "—"
        qt = f"{r['sharpe_quoted']:.2f}" if r["sharpe_quoted"] else "—"
        lines.append(
            f"<tr><td>{r['symbol']}</td><td>{r['horizon']}</td>"
            f"<td>{ta}</td><td>{eff}</td><td>{qt}</td></tr>"
        )
    lines.extend(["</tbody>", "</table>"])
    return "\n".join(lines)
