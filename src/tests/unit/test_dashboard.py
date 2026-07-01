"""Tests for the tournament dashboard builder."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.visualization.dashboard import (
    _best_model_for_horizon,
    _build_stats,
    _compute_divergence_dates,
    _compute_transition_matrices,
    _discretize_signal,
    _mz_label,
    _significance_stars,
    _worst_model_for_horizon,
    build_tournament_dashboard,
    save_tournament_dashboard,
)


@pytest.fixture()
def tournament_data():
    """Synthetic tournament tables, actuals, and forecasts."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2022-01-03", periods=100)
    models = ["har", "harq", "shar", "har_j", "har_cj", "ridge_har", "lasso_har"]
    symbols = ["SPY", "AAPL"]

    # Build tournament tables (sorted by qlike ascending)
    tables = {}
    actuals = {}
    forecasts = {}

    for h in [1, 5, 22]:
        # Per-symbol actuals and forecasts
        h_actuals: dict[str, pd.Series] = {}
        h_forecasts: dict[str, dict[str, pd.Series]] = {}

        qlike_vals = sorted(rng.uniform(0.3, 0.9, len(models)))
        rows = []
        for sym in symbols:
            actual = pd.Series(rng.normal(-8.0, 0.5, 100), index=dates)
            h_actuals[sym] = actual

            sym_forecasts: dict[str, pd.Series] = {}
            for i, m in enumerate(models):
                noise = rng.normal(0, 0.1 + i * 0.02, 100)
                sym_forecasts[m] = pd.Series(actual.values + noise, index=dates)
            h_forecasts[sym] = sym_forecasts

        for i, m in enumerate(models):
            dm_p = 0.001 if i == 0 else (0.03 if i < 3 else 0.5)
            rows.append(
                {
                    "model": m,
                    "qlike": qlike_vals[i],
                    "qlike_bps": (qlike_vals[-1] - qlike_vals[i]) / qlike_vals[-1] * 10000,
                    "mse": rng.uniform(0.05, 0.2),
                    "r_squared": rng.uniform(0.3, 0.6),
                    "mcs_included": i < 4,
                    "mcs_pvalue": rng.uniform(0.1, 1.0) if i < 4 else rng.uniform(0.0, 0.09),
                    "dm_stat": rng.normal(2.0, 1.0),
                    "dm_pvalue": dm_p,
                    "mz_alpha": rng.uniform(-0.1, 0.1),
                    "mz_beta": rng.uniform(0.8, 1.2),
                    "mz_f_pvalue": 0.8 if i < 5 else 0.01,
                }
            )

        actuals[h] = h_actuals
        forecasts[h] = h_forecasts
        tables[h] = pd.DataFrame(rows)

    return tables, actuals, forecasts


class TestBuildDashboard:
    def test_returns_valid_html(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_contains_horizon_tabs(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert 'id="tab-h1"' in html
        assert 'id="tab-h5"' in html
        assert 'id="tab-h22"' in html

    def test_contains_model_checkboxes(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert 'id="chk-har"' in html
        assert 'id="chk-harq"' in html
        assert 'id="chk-lasso_har"' in html

    def test_contains_stats_tables(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert 'id="stats-h1"' in html
        assert 'best' in html and 'clickable-row' in html
        assert 'worst' in html and 'clickable-row' in html

    def test_contains_plotly_script(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "Plotly.react" in html
        assert "plotly-2.35.0" in html

    def test_contains_divergence_data(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "divergenceLines" in html

    def test_dark_theme_css(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "#1a1a2e" in html  # dark bg color

    def test_custom_experiment_name(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(
            tables,
            actuals,
            forecasts,
            experiment_name="My Custom Tournament",
        )
        assert "My Custom Tournament" in html

    def test_show_best_only_button(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "showBestOnly" in html
        assert "Best Only" in html

    def test_show_all_button(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "showAll" in html
        assert "Show All" in html

    def test_contains_symbol_selector(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert 'id="symbol-select"' in html
        assert "switchSymbol" in html
        assert "__pooled__" in html
        # Individual symbols from fixture
        assert "SPY" in html
        assert "AAPL" in html

    def test_contains_model_tooltips(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        # HAR model description should appear as title attribute
        assert "Heterogeneous AR" in html

    def test_trace_data_keyed_by_symbol(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "traceDataBySymbol" in html

    def test_contains_statistical_test_columns(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        # New column headers present
        assert "bps" in html
        assert "DM" in html
        assert "MCS" in html
        assert "MZ" in html

    def test_column_header_tooltips(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "Quasi-likelihood loss" in html
        assert "Diebold-Mariano" in html
        assert "Model Confidence Set" in html
        assert "Mincer-Zarnowitz" in html
        assert "Out-of-sample R-squared" in html
        assert "QLIKE improvement" in html

    def test_explainer_element_present(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert 'id="explainer-container"' in html
        assert "openExplainer" in html
        assert "closeExplainer" in html

    def test_clickable_headers(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "clickable-header" in html
        assert "openExplainer('qlike')" in html
        assert "openExplainer('dm')" in html
        assert "openExplainer('mcs')" in html
        assert "openExplainer('mz')" in html
        assert "openExplainer('bps')" in html
        assert "openExplainer('r2')" in html

    def test_stat_meta_injected(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "statMeta" in html
        assert "econAssumptions" in html
        assert "statsByHorizon" in html

    def test_dm_stat_in_stats_data(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        # dm_stat should appear in the JSON stats data
        assert '"dm_stat"' in html
        assert '"mz_alpha"' in html
        assert '"mz_beta"' in html
        assert '"mz_f_pvalue"' in html

    def test_mcs_badge_renders(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert 'class="badge-mcs included"' in html
        assert 'class="badge-mcs excluded"' in html
        assert "&#10003;" in html  # checkmark for included

    def test_significance_stars_render(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        # Fixture has dm_pvalue=0.001 for first model → should render ***
        assert 'class="sig-stars"' in html
        assert "***" in html

    def test_mz_pass_reject_render(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "mz-pass" in html
        assert "mz-reject" in html
        assert "Pass" in html
        assert "Reject" in html

    def test_bps_color_coding(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        assert "bps-pos" in html or "bps-zero" in html

    def test_backward_compat_minimal_dataframe(self, tournament_data):
        """Dashboard renders when stat test columns are absent."""
        _, actuals, forecasts = tournament_data
        # Minimal tables with only model + qlike + r_squared
        minimal = {}
        for h in [1, 5, 22]:
            minimal[h] = pd.DataFrame(
                {
                    "model": ["har", "ridge_har"],
                    "qlike": [0.5, 0.4],
                    "r_squared": [0.3, 0.4],
                }
            )
        html = build_tournament_dashboard(minimal, actuals, forecasts)
        assert "<!DOCTYPE html>" in html
        assert "MCS" in html  # Column header still present
        # Default values used — no crash
        assert "Pass" in html  # Default mz_f_pvalue=1.0 → Pass

    def test_baselines_excluded_from_model_rankings(self, tournament_data):
        """Baseline models (always_long etc.) should NOT appear in Model Rankings.

        They are only relevant for the GSVIVS01 table.
        """
        tables, actuals, forecasts = tournament_data
        # Inject baseline rows into tournament tables (mimics statistical_tests.py)
        for h in [1, 5, 22]:
            baseline_rows = []
            for bname in ["always_long", "always_short", "always_flat", "random", "random_no_flip"]:
                baseline_rows.append(
                    {
                        "model": f"[baseline] {bname}",
                        "qlike": float("nan"),
                        "qlike_bps": float("nan"),
                        "r_squared": float("nan"),
                        "dm_stat": float("nan"),
                        "dm_pvalue": float("nan"),
                        "mcs_included": False,
                        "mcs_pvalue": float("nan"),
                        "mz_alpha": float("nan"),
                        "mz_beta": float("nan"),
                        "mz_f_pvalue": float("nan"),
                    }
                )
            tables[h] = pd.concat([tables[h], pd.DataFrame(baseline_rows)], ignore_index=True)

        model_colors = {row["model"]: "#888" for _, row in tables[1].iterrows()}
        stats = _build_stats(tables, [1, 5, 22], model_colors)

        for h in [1, 5, 22]:
            names = [r["name"] for r in stats[h]]
            for name in names:
                assert not name.startswith("[baseline]"), (
                    f"Baseline '{name}' should not appear in Model Rankings (h={h})"
                )
            # Original models should still be present
            assert len(names) == 7  # 7 real models from fixture

    def test_baselines_excluded_from_dashboard_html(self, tournament_data):
        """Baseline models should not appear in model checkboxes or rankings."""
        tables, actuals, forecasts = tournament_data
        for h in [1, 5, 22]:
            baseline_rows = []
            for bname in ["always_long", "always_short"]:
                baseline_rows.append(
                    {
                        "model": f"[baseline] {bname}",
                        "qlike": float("nan"),
                        "qlike_bps": float("nan"),
                        "r_squared": float("nan"),
                    }
                )
            tables[h] = pd.concat([tables[h], pd.DataFrame(baseline_rows)], ignore_index=True)

        html = build_tournament_dashboard(tables, actuals, forecasts)
        # Baselines should not have checkboxes (model legend entries)
        assert 'id="chk-[baseline] always_long"' not in html
        assert 'id="chk-[baseline] always_short"' not in html
        # Baselines should not appear in the stats JSON data
        # (the statsByHorizon object drives the rankings table)
        assert '"[baseline] always_long"' not in html
        assert '"[baseline] always_short"' not in html


class TestGsvivsIvFilter:
    """Dashboard IV source selector behavior.

    When multiple IV sources are provided, all are rendered with selector
    buttons. When only one IV source is provided, no selector UI appears.
    """

    def _gsvivs_payload(self, labels=None) -> tuple[dict[str, dict[int, list[dict]]], dict[str, dict[int, list[dict]]]]:
        if labels is None:
            labels = [
                "Exec Kvar (true fill)",
                "EDRVS morning 1-DTE",
                "EDRVS prev-close 1-DTE",
                "SPX ATM IV (1w)",
            ]
        stats = {
            label: {
                h: [
                    {
                        "name": "har",
                        "sharpe_0rf": 0.5 + i * 0.1,
                        "sharpe_5rf": 0.3,
                        "ann_return": 5.0,
                        "ann_vol": 10.0,
                        "total_return": 12.0,
                        "max_drawdown": 8.0,
                        "positive_days": "50/100 (50.0%)",
                        "precision": 0.6,
                        "recall": 0.5,
                        "f1": 0.55,
                        "mcc": 0.2,
                    }
                ]
                for h in [1, 5, 22]
            }
            for i, label in enumerate(labels)
        }
        traces = {
            label: {h: [{"x": [], "y": [], "name": "har"}] for h in [1, 5, 22]}
            for label in labels
        }
        return stats, traces

    def test_multi_iv_all_labels_rendered(self, tournament_data):
        """When multiple IV sources are provided, all labels appear."""
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_payload()
        html = build_tournament_dashboard(
            tables,
            actuals,
            forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
        )
        assert "Exec Kvar (true fill)" in html
        assert "EDRVS prev-close 1-DTE" in html
        assert "SPX ATM IV (1w)" in html

    def test_multi_iv_shows_selector_buttons(self, tournament_data):
        """When multiple IV sources are provided, selector buttons appear."""
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_payload()
        html = build_tournament_dashboard(
            tables,
            actuals,
            forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
        )
        assert "IV Source:" in html
        assert "gsvivs-iv-btn" in html
        assert "switchGsvivsIv" in html

    def test_single_iv_no_selector_buttons(self, tournament_data):
        """When only one IV source is provided, no selector UI appears."""
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_payload(
            labels=["Exec Kvar (true fill)"]
        )
        html = build_tournament_dashboard(
            tables,
            actuals,
            forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
        )
        # The single label is rendered
        assert "Exec Kvar (true fill)" in html
        # No selector toolbar (the "IV Source:" label only appears in the toolbar div)
        assert "IV Source:" not in html
        # No button elements with the gsvivs-iv-btn class (the class name may
        # appear in JS code, but no <button> elements should be rendered)
        assert 'class="tab-btn gsvivs-iv-btn' not in html


class TestSaveDashboard:
    def test_saves_file(self, tournament_data, tmp_path):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        path = save_tournament_dashboard(html, tmp_path)
        assert path.exists()
        assert path.name == "tournament_dashboard.html"
        assert path.stat().st_size > 5000

    def test_creates_plots_dir(self, tournament_data, tmp_path):
        tables, actuals, forecasts = tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts)
        save_tournament_dashboard(html, tmp_path)
        assert (tmp_path / "plots").is_dir()


class TestBestWorstModel:
    def test_best_is_first_row(self):
        df = pd.DataFrame({"model": ["a", "b", "c"], "qlike": [0.1, 0.2, 0.3]})
        assert _best_model_for_horizon(df) == "a"

    def test_worst_is_last_row(self):
        df = pd.DataFrame({"model": ["a", "b", "c"], "qlike": [0.1, 0.2, 0.3]})
        assert _worst_model_for_horizon(df) == "c"


class TestDivergenceDates:
    def test_returns_dates_above_threshold(self):
        dates = pd.bdate_range("2022-01-03", periods=100)
        rng = np.random.default_rng(99)
        # Most predictions are close, but inject a few outliers
        base = rng.normal(0, 0.01, 100)
        forecasts = {
            1: {
                "a": pd.Series(base, index=dates),
                "b": pd.Series(base + 0.01, index=dates),
            }
        }
        # Inject large divergence at specific indices
        forecasts[1]["b"].iloc[10] += 5.0
        forecasts[1]["b"].iloc[50] += 5.0

        result = _compute_divergence_dates(forecasts, [1], percentile=95.0)
        # Should find the injected outlier dates (top 5% = top 5 of 100)
        assert len(result[1]) <= 5
        assert len(result[1]) >= 2

    def test_empty_forecasts(self):
        result = _compute_divergence_dates({1: {}}, [1])
        assert result[1] == []

    def test_single_model_no_divergence(self):
        dates = pd.bdate_range("2022-01-03", periods=50)
        forecasts = {1: {"a": pd.Series(np.zeros(50), index=dates)}}
        result = _compute_divergence_dates(forecasts, [1])
        assert result[1] == []


class TestSignificanceStars:
    def test_triple_star(self):
        assert _significance_stars(0.005) == "***"

    def test_double_star(self):
        assert _significance_stars(0.03) == "**"

    def test_single_star(self):
        assert _significance_stars(0.08) == "*"

    def test_no_star(self):
        assert _significance_stars(0.15) == ""

    def test_boundary_001(self):
        assert _significance_stars(0.01) == "**"

    def test_boundary_005(self):
        assert _significance_stars(0.05) == "*"

    def test_boundary_010(self):
        assert _significance_stars(0.10) == ""


class TestMzLabel:
    def test_pass(self):
        assert _mz_label(0.5) == "Pass"

    def test_reject(self):
        assert _mz_label(0.01) == "Reject"

    def test_boundary(self):
        assert _mz_label(0.05) == "Pass"


class TestPhase3Explainer:
    """Tests that the Phase 3 realistic DH straddle explainer is wired into the dashboard."""

    @pytest.fixture()
    def dh_tournament_data(self, tournament_data):
        """Add DH per-symbol data to tournament fixture."""
        tables, actuals, forecasts = tournament_data
        dh_per_symbol = {
            "SPY": {
                1: [
                    {
                        "name": "har",
                        "dh_sharpe": 0.5,
                        "dh_pnl": 10.0,
                        "dh_max_dd": -5.0,
                        "dh_hit_rate": 0.55,
                        "dh_ann_ret": 8.0,
                        "dh_ann_vol": 16.0,
                    }
                ],
            },
        }
        return tables, actuals, forecasts, dh_per_symbol

    def test_dh_methodology_explainer_trigger_exists(self, dh_tournament_data):
        tables, actuals, forecasts, dh_per_symbol = dh_tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts, dh_per_symbol=dh_per_symbol)
        assert "openExplainer('dh_methodology')" in html

    def test_dh_methodology_case_in_js(self, dh_tournament_data):
        tables, actuals, forecasts, dh_per_symbol = dh_tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts, dh_per_symbol=dh_per_symbol)
        assert "case 'dh_methodology':" in html

    def test_phase3_formulas_present(self, dh_tournament_data):
        tables, actuals, forecasts, dh_per_symbol = dh_tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts, dh_per_symbol=dh_per_symbol)
        # Key formulas that must appear (as LaTeX in JS string literals — double-escaped)
        assert "\\\\Gamma_{\\\\text{ATM}}" in html
        assert "Boyle" in html
        assert "\\\\text{Var}(\\\\text{HE})" in html
        assert "\\\\text{DSR}" in html
        assert "\\\\text{VWAP}" in html

    def test_phase3_assumptions_present(self, dh_tournament_data):
        tables, actuals, forecasts, dh_per_symbol = dh_tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts, dh_per_symbol=dh_per_symbol)
        # All assumption categories must be documented
        assert "Black-Scholes" in html
        assert "15-min" in html or "15min" in html
        assert "kurtosis" in html or "kappa" in html
        assert "roll" in html
        assert "tenor" in html

    def test_cost_band_formulas(self, dh_tournament_data):
        tables, actuals, forecasts, dh_per_symbol = dh_tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts, dh_per_symbol=dh_per_symbol)
        assert "timing" in html.lower()
        assert "effective" in html.lower()
        assert "quoted" in html.lower()
        assert "Muravyev" in html

    def test_deflated_sharpe_formula(self, dh_tournament_data):
        tables, actuals, forecasts, dh_per_symbol = dh_tournament_data
        html = build_tournament_dashboard(tables, actuals, forecasts, dh_per_symbol=dh_per_symbol)
        assert "Bailey" in html
        assert "Lopez de Prado" in html or "Prado" in html

    def test_at_boundary_below(self):
        assert _mz_label(0.049) == "Reject"

    def test_just_above(self):
        assert _mz_label(0.051) == "Pass"


class TestDiscretizeSignal:
    """Test signal discretization for transition matrix computation."""

    def test_binary_maps_to_short_long(self):
        signal = [-1.0, 1.0, -1.0, 1.0, 1.0]
        states, labels = _discretize_signal(signal, "binary")
        assert labels == ["Short", "Long"]
        assert states == [0, 1, 0, 1, 1]

    def test_long_flat_maps_to_flat_long(self):
        signal = [0.0, 1.0, 0.0, 1.0, 1.0]
        states, labels = _discretize_signal(signal, "long_flat")
        assert labels == ["Flat", "Long"]
        assert states == [0, 1, 0, 1, 1]

    def test_zscore_maps_to_three_states(self):
        signal = [-1.5, 0.0, 0.3, 1.2, -0.8]
        states, labels = _discretize_signal(signal, "zscore")
        assert labels == ["Sell (< -0.5)", "Neutral", "Buy (> +0.5)"]
        assert states == [0, 1, 1, 2, 0]

    def test_asym_long_maps_to_three_states(self):
        # asym_long output: -1 (short), 1.0 (base long), >1 (leveraged long)
        signal = [-1.0, 1.0, 1.5, 2.0, -1.0]
        states, labels = _discretize_signal(signal, "asym_long")
        assert labels == ["Short", "Long \u00d71", "Long Lev"]
        assert states == [0, 1, 2, 2, 0]

    def test_boundary_values_zscore(self):
        signal = [-0.5, 0.5, -0.51, 0.51]
        states, _ = _discretize_signal(signal, "zscore")
        assert states == [1, 1, 0, 2]


class TestComputeTransitionMatrices:
    """Test transition matrix computation from trace data."""

    def test_binary_2x2_matrix(self):
        traces = [
            {
                "name": "har [binary]",
                "_signal_x": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
                "_signal_y": [1.0, 1.0, -1.0, 1.0, -1.0],
                "_sizing_label": "[binary]",
            }
        ]
        result = _compute_transition_matrices(traces, horizon=1, sizing_labels=["[binary]"])
        key = "har|[binary]|1"
        assert key in result
        m = result[key]
        assert m["labels"] == ["Short", "Long"]
        assert "rank" in m
        matrix = m["matrix"]
        assert len(matrix) == 2
        for row in matrix:
            assert abs(sum(row) - 100.0) < 0.1

    def test_zscore_3x3_matrix(self):
        traces = [
            {
                "name": "lgbm [zscore L=1]",
                "_signal_x": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                "_signal_y": [-1.0, 0.0, 0.8, -0.6],
                "_sizing_label": "[zscore L=1]",
            }
        ]
        result = _compute_transition_matrices(traces, horizon=1, sizing_labels=["[zscore L=1]"])
        key = "lgbm|[zscore L=1]|1"
        assert key in result
        assert result[key]["labels"] == ["Sell (< -0.5)", "Neutral", "Buy (> +0.5)"]
        matrix = result[key]["matrix"]
        assert len(matrix) == 3
        assert len(matrix[0]) == 3

    def test_multiple_models(self):
        traces = [
            {
                "name": "har [binary]",
                "_signal_x": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "_signal_y": [1.0, -1.0, 1.0],
                "_sizing_label": "[binary]",
            },
            {
                "name": "lgbm [binary]",
                "_signal_x": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "_signal_y": [1.0, 1.0, 1.0],
                "_sizing_label": "[binary]",
            },
        ]
        result = _compute_transition_matrices(traces, horizon=1, sizing_labels=["[binary]"])
        assert "har|[binary]|1" in result
        assert "lgbm|[binary]|1" in result

    def test_model_ranks_passed_through(self):
        traces = [
            {
                "name": "har [binary]",
                "_signal_x": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "_signal_y": [1.0, -1.0, 1.0],
                "_sizing_label": "[binary]",
            },
            {
                "name": "lgbm [binary]",
                "_signal_x": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "_signal_y": [1.0, 1.0, 1.0],
                "_sizing_label": "[binary]",
            },
        ]
        ranks = {"lgbm": 1, "har": 2}
        result = _compute_transition_matrices(
            traces, horizon=1, sizing_labels=["[binary]"], model_ranks=ranks,
        )
        assert result["lgbm|[binary]|1"]["rank"] == 1
        assert result["har|[binary]|1"]["rank"] == 2

    def test_empty_signal_skipped(self):
        traces = [
            {
                "name": "har [binary]",
                "_signal_x": [],
                "_signal_y": [],
                "_sizing_label": "[binary]",
            }
        ]
        result = _compute_transition_matrices(traces, horizon=1, sizing_labels=["[binary]"])
        assert len(result) == 0

    def test_single_observation_skipped(self):
        traces = [
            {
                "name": "har [binary]",
                "_signal_x": ["2024-01-01"],
                "_signal_y": [1.0],
                "_sizing_label": "[binary]",
            }
        ]
        result = _compute_transition_matrices(traces, horizon=1, sizing_labels=["[binary]"])
        assert len(result) == 0


class TestTransitionMatrixInDashboard:
    """Test that transition matrix data and UI are injected into the dashboard HTML."""

    def _gsvivs_with_traces(self):
        """Create GSVIVS payload with signal traces for testing."""
        stats = {
            "Exec Kvar (true fill)": {
                h: [
                    {
                        "name": "har [binary]",
                        "sizing_label": "[binary]",
                        "sharpe_0rf": 0.5,
                        "sharpe_5rf": 0.3,
                        "ann_return": 5.0,
                        "ann_vol": 10.0,
                        "total_return": 12.0,
                        "max_drawdown": 8.0,
                        "positive_days": "50/100 (50.0%)",
                        "precision": 0.6,
                        "recall": 0.5,
                        "f1": 0.55,
                        "mcc": 0.2,
                    }
                ]
                for h in [1, 5, 22]
            }
        }
        traces = {
            "Exec Kvar (true fill)": {
                h: [
                    {
                        "x": ["2024-01-02", "2024-01-03", "2024-01-04"],
                        "y": [1.0, 1.01, 0.99],
                        "name": "har [binary]",
                        "_signal_x": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                        "_signal_y": [1.0, -1.0, 1.0, 1.0],
                        "_sizing_label": "[binary]",
                    }
                ]
                for h in [1, 5, 22]
            }
        }
        return stats, traces

    def test_transition_button_present(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_with_traces()
        html = build_tournament_dashboard(
            tables, actuals, forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
        )
        assert 'id="gsvivs-matrix-btn"' in html
        assert "Transitions" in html

    def test_transition_data_injected(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_with_traces()
        html = build_tournament_dashboard(
            tables, actuals, forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
        )
        assert "gsvivsTransitionData" in html

    def test_transition_container_present(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_with_traces()
        html = build_tournament_dashboard(
            tables, actuals, forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
        )
        assert 'id="transition-matrix-container"' in html

    def test_matrix_render_function_present(self, tournament_data):
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_with_traces()
        html = build_tournament_dashboard(
            tables, actuals, forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
        )
        assert "renderTransitionMatrices" in html
        assert "gsvivs_matrix" in html

    def test_threshold_displayed_on_dashboard(self, tournament_data):
        """Dashboard must display the actual threshold value used."""
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_with_traces()
        html = build_tournament_dashboard(
            tables, actuals, forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
            gsvivs_short_threshold=0.003,
        )
        # The threshold value must appear somewhere in the rendered HTML
        assert "0.003" in html

    def test_threshold_zero_displayed(self, tournament_data):
        """Dashboard must display threshold=0 when that's the value used."""
        tables, actuals, forecasts = tournament_data
        gsvivs_stats, gsvivs_traces = self._gsvivs_with_traces()
        html = build_tournament_dashboard(
            tables, actuals, forecasts,
            gsvivs_per_iv=gsvivs_stats,
            gsvivs_traces_per_iv=gsvivs_traces,
            gsvivs_short_threshold=0.0,
        )
        # Should show "Threshold: 0" or similar
        assert "Threshold" in html

    def test_default_sizing_prefers_long_flat(self, tournament_data):
        """When long_flat is in sizing labels, it should be the default active tab."""
        from volforecast.visualization.dashboard import _default_active_sizing

        labels = ["[binary]", "[asym_long L=2]", "[zscore L=1]", "[long_flat]"]
        assert _default_active_sizing(labels) == "[long_flat]"
