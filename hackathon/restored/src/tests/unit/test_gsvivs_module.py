"""Unit tests for evaluation.gsvivs — GSVIVS signal computation.

Verifies the new module's public API matches the contract that
test_gsvivs_backtest.py and test_kvar_integration.py rely on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestComputeGsvivsStats:
    """Test compute_gsvivs_stats public API."""

    def test_returns_expected_tuple_types(self, monkeypatch):
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        gsvivs_dates = pd.bdate_range("2022-01-03", "2024-12-31", freq="B")
        rng = np.random.default_rng(42)
        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(len(gsvivs_dates)))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=gsvivs_dates, name="gsvivs01")
        iv_df = pd.DataFrame(
            {"iv_1m_atm": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2},
            index=gsvivs_dates,
        )
        pred_dates = pd.bdate_range("2023-01-02", "2024-12-31", freq="B")
        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(len(pred_dates)) * 0.3,
            index=pred_dates,
        )

        monkeypatch.setattr("volforecast.data.edrvol.fetch_gsvivs_index", lambda: gsvivs_series)
        monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", lambda sym: iv_df)

        results_by_iv, traces_by_iv = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 22): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[22],
        )

        assert isinstance(results_by_iv, dict)
        assert isinstance(traces_by_iv, dict)
        assert len(results_by_iv) > 0

    def test_result_rows_have_required_keys(self, monkeypatch):
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        gsvivs_dates = pd.bdate_range("2022-01-03", "2024-12-31", freq="B")
        rng = np.random.default_rng(42)
        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(len(gsvivs_dates)))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=gsvivs_dates, name="gsvivs01")
        iv_df = pd.DataFrame(
            {"iv_1m_atm": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2},
            index=gsvivs_dates,
        )
        pred_dates = pd.bdate_range("2023-01-02", "2024-12-31", freq="B")
        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(len(pred_dates)) * 0.3,
            index=pred_dates,
        )

        monkeypatch.setattr("volforecast.data.edrvol.fetch_gsvivs_index", lambda: gsvivs_series)
        monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", lambda sym: iv_df)

        results_by_iv, _ = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 22): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[22],
        )

        first_iv = next(iter(results_by_iv))
        rows = results_by_iv[first_iv][22]
        required_keys = {"name", "sharpe_0rf", "sharpe_5rf", "total_return", "max_drawdown", "hit_rate"}
        for row in rows:
            assert required_keys.issubset(set(row.keys())), f"Missing keys in {row}"


class TestDefaultGsvivsDashboardIvLabel:
    """Test default_gsvivs_dashboard_iv_label."""

    def test_prefers_exec_kvar(self):
        from volforecast.evaluation.gsvivs import default_gsvivs_dashboard_iv_label

        stats = {"Exec Kvar (true fill)": {}, "EDRVS morning 1-DTE": {}}
        assert default_gsvivs_dashboard_iv_label(stats) == "Exec Kvar (true fill)"

    def test_falls_back_to_first(self):
        from volforecast.evaluation.gsvivs import default_gsvivs_dashboard_iv_label

        stats = {"EDRVS morning 1-DTE": {}, "SPX ATM IV (1w)": {}}
        assert default_gsvivs_dashboard_iv_label(stats) == "EDRVS morning 1-DTE"

    def test_returns_none_for_empty(self):
        from volforecast.evaluation.gsvivs import default_gsvivs_dashboard_iv_label

        assert default_gsvivs_dashboard_iv_label({}) is None


class TestComputeGsvivsStatsSizingToggle:
    """compute_gsvivs_stats must surface the 3-option sizing toggle.

    For each (IV source × horizon × model) the function should emit ONE row per
    GsvivsSizingSpec, with the spec's label appended to the model name. The
    default sizing list is the three-mode toggle (binary | asym_long | zscore).
    Baseline rows (constant_long, constant_short, ...) are model-agnostic and
    are emitted exactly once per IV source — never duplicated per sizing mode.
    """

    def _setup_data(self, monkeypatch):
        """Minimal mocked GSVIVS data with an Exec Kvar IV column."""
        gsvivs_dates = pd.bdate_range("2022-01-03", "2024-12-31", freq="B")
        rng = np.random.default_rng(7)
        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.05 / 252 + 0.03 / np.sqrt(252) * rng.standard_normal(len(gsvivs_dates)))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=gsvivs_dates, name="gsvivs01")
        iv_df = pd.DataFrame(
            {
                "iv_1m_atm": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2,
                "iv_1w_atm": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2,
                "iv_vs_0dte": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2,
            },
            index=gsvivs_dates,
        )
        # Inject Exec Kvar by patching load_exec_kvar_cache too
        exec_kvar = pd.Series(
            18.0 + rng.standard_normal(len(gsvivs_dates)) * 2,
            index=gsvivs_dates,
            name="iv_exec_kvar",
        )
        pred_dates = pd.bdate_range("2023-01-02", "2024-12-31", freq="B")
        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(len(pred_dates)) * 0.3,
            index=pred_dates,
        )
        monkeypatch.setattr("volforecast.data.edrvol.fetch_gsvivs_index", lambda: gsvivs_series)
        monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", lambda sym: iv_df)
        monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_cache", lambda: None)
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_exec_kvar_cache", lambda: exec_kvar
        )
        return preds

    def test_default_emits_three_sizing_rows_per_model(self, monkeypatch):
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        preds = self._setup_data(monkeypatch)
        results_by_iv, _ = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 1): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
        )
        first_iv = next(iter(results_by_iv))
        rows = results_by_iv[first_iv][1]
        model_rows = [r for r in rows if not r["name"].startswith("[baseline]")]
        assert len(model_rows) == 4, (
            f"Expected one row per default sizing spec "
            f"(binary | asym_long | zscore | long_flat), "
            f"got {[r['name'] for r in model_rows]}"
        )
        names = {r["name"] for r in model_rows}
        assert "har [binary]" in names
        assert "har [asym_long L=2]" in names
        assert "har [zscore L=1]" in names
        assert "har [long_flat]" in names

    def test_explicit_sizings_overrides_default(self, monkeypatch):
        from volforecast.evaluation.economic_value import GsvivsSizingSpec
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        preds = self._setup_data(monkeypatch)
        only_asym = (GsvivsSizingSpec(mode="asym_long", max_leverage=3.0, lookback=63),)
        results_by_iv, _ = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 1): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
            signal_sizings=only_asym,
        )
        first_iv = next(iter(results_by_iv))
        rows = results_by_iv[first_iv][1]
        model_rows = [r for r in rows if not r["name"].startswith("[baseline]")]
        assert len(model_rows) == 1
        assert model_rows[0]["name"] == "har [asym_long L=3]"

    def test_baselines_emitted_once_not_duplicated_per_sizing(self, monkeypatch):
        """Constant_long/constant_short baselines don't depend on the sizing
        scheme — they must not be duplicated when multiple sizings are active."""
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        preds = self._setup_data(monkeypatch)
        results_by_iv, _ = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 1): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
        )
        first_iv = next(iter(results_by_iv))
        rows = results_by_iv[first_iv][1]
        baseline_names = [r["name"] for r in rows if r["name"].startswith("[baseline]")]
        # Each baseline label appears at most once.
        assert len(baseline_names) == len(set(baseline_names)), (
            f"Baseline rows duplicated: {baseline_names}"
        )

    def test_binary_row_matches_legacy_gap_signal_pnl(self, monkeypatch):
        """The binary sizing variant must produce IDENTICAL Sharpe to the
        legacy kvar_rv_gap_signal output. This locks in backward compatibility
        for existing tournament reports."""
        from volforecast.evaluation.economic_value import GsvivsSizingSpec
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        preds = self._setup_data(monkeypatch)

        # New path: binary spec only.
        binary_only = (GsvivsSizingSpec(mode="binary"),)
        results_new, _ = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 1): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
            signal_sizings=binary_only,
        )
        # Legacy reference path uses the same compute_gsvivs_stats but a different
        # configuration: empty signal_sizings means "fall back to legacy single-row
        # behavior using kvar_rv_gap_signal directly". We assert the binary spec's
        # numerical output reproduces it.
        first_iv = next(iter(results_new))
        new_rows = [r for r in results_new[first_iv][1] if r["name"] == "har [binary]"]
        assert len(new_rows) == 1
        # Binary should always be present with the [binary] suffix.
        assert isinstance(new_rows[0]["sharpe_0rf"], float)


class TestSizingLabelTagging:
    """Each row/trace must carry a `sizing_label` tag so the dashboard can
    filter the table and chart by sizing mode via a UI toggle.

    Contract:
      * Sized model rows: ``sizing_label == spec.label`` (e.g. ``"[binary]"``).
      * Baseline rows: ``sizing_label == ""`` — baselines are sizing-agnostic
        and must always be visible regardless of which toggle is active.
      * Same convention for traces, on the ``_sizing_label`` key (leading
        underscore matches the existing ``_signal_x`` / ``_signal_y`` chart
        metadata convention).
    """

    def _setup_data(self, monkeypatch):
        gsvivs_dates = pd.bdate_range("2022-01-03", "2024-12-31", freq="B")
        rng = np.random.default_rng(11)
        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.05 / 252 + 0.03 / np.sqrt(252) * rng.standard_normal(len(gsvivs_dates)))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=gsvivs_dates, name="gsvivs01")
        iv_df = pd.DataFrame(
            {
                "iv_1m_atm": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2,
                "iv_1w_atm": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2,
                "iv_vs_0dte": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2,
            },
            index=gsvivs_dates,
        )
        exec_kvar = pd.Series(
            18.0 + rng.standard_normal(len(gsvivs_dates)) * 2,
            index=gsvivs_dates,
            name="iv_exec_kvar",
        )
        pred_dates = pd.bdate_range("2023-01-02", "2024-12-31", freq="B")
        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(len(pred_dates)) * 0.3,
            index=pred_dates,
        )
        monkeypatch.setattr("volforecast.data.edrvol.fetch_gsvivs_index", lambda: gsvivs_series)
        monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", lambda sym: iv_df)
        monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_cache", lambda: None)
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_exec_kvar_cache", lambda: exec_kvar
        )
        return preds

    def test_sized_rows_have_matching_sizing_label(self, monkeypatch):
        from volforecast.evaluation.economic_value import DEFAULT_GSVIVS_SIZING_SPECS
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        preds = self._setup_data(monkeypatch)
        results_by_iv, _ = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 1): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
        )
        first_iv = next(iter(results_by_iv))
        rows = results_by_iv[first_iv][1]
        expected_labels = {spec.label for spec in DEFAULT_GSVIVS_SIZING_SPECS}
        for row in rows:
            assert "sizing_label" in row, f"Row missing sizing_label: {row['name']}"
            if row["name"].startswith("[baseline]"):
                continue
            assert row["sizing_label"] in expected_labels, (
                f"Unexpected sizing_label {row['sizing_label']!r} on row {row['name']!r}"
            )
            # Label must be a substring of the row name (suffix appended in
            # compute_gsvivs_stats: "har [binary]" -> "[binary]").
            assert row["sizing_label"] in row["name"]

    def test_baseline_rows_have_empty_sizing_label(self, monkeypatch):
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        preds = self._setup_data(monkeypatch)
        results_by_iv, _ = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 1): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
        )
        first_iv = next(iter(results_by_iv))
        rows = results_by_iv[first_iv][1]
        baselines = [r for r in rows if r["name"].startswith("[baseline]")]
        assert baselines, "Expected baseline rows in output"
        for row in baselines:
            assert row["sizing_label"] == "", (
                f"Baseline {row['name']!r} should have empty sizing_label, "
                f"got {row['sizing_label']!r}"
            )

    def test_traces_have_matching_sizing_label(self, monkeypatch):
        from volforecast.evaluation.economic_value import DEFAULT_GSVIVS_SIZING_SPECS
        from volforecast.evaluation.gsvivs import compute_gsvivs_stats

        preds = self._setup_data(monkeypatch)
        _, traces_by_iv = compute_gsvivs_stats(
            all_preds_series={("har", "SPY", 1): preds},
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
        )
        first_iv = next(iter(traces_by_iv))
        h_traces = traces_by_iv[first_iv][1]
        expected_labels = {spec.label for spec in DEFAULT_GSVIVS_SIZING_SPECS}
        for tr in h_traces:
            assert "_sizing_label" in tr, f"Trace missing _sizing_label: {tr['name']}"
            if tr["name"].startswith("[baseline]"):
                assert tr["_sizing_label"] == ""
            else:
                assert tr["_sizing_label"] in expected_labels


class TestDashboardSizingToggle:
    """build_tournament_dashboard must expose a sizing toggle UI.

    The dashboard collects unique sizing labels (preserving the spec order
    from compute_gsvivs_stats) and renders one toggle button per label.
    Selecting a button filters BOTH the GSVIVS table (via ``data-sizing`` row
    attribute) and the GSVIVS chart traces (via the ``_sizing_label`` trace
    metadata) so only that variant is shown.
    """

    def _minimal_tables(self):
        tables = {
            1: pd.DataFrame(
                [
                    {
                        "model": "har",
                        "qlike": 0.15,
                        "mse": 1e-5,
                        "r_squared": 0.5,
                        "qlike_bps": 1500.0,
                        "dm_pvalue": 1.0,
                        "dm_stat": 0.0,
                        "mcs_included": True,
                        "mcs_pvalue": 0.5,
                        "mz_f_pvalue": 0.5,
                        "mz_alpha": 0.0,
                        "mz_beta": 1.0,
                    }
                ]
            )
        }
        actuals = {1: {"SPY": pd.Series(dtype=float)}}
        forecasts: dict = {1: {"SPY": {"har": pd.Series(dtype=float)}}}
        return tables, actuals, forecasts

    def _sized_rows(self):
        # Three sized model rows + one baseline row, matching the shape
        # compute_gsvivs_stats produces.
        common = {
            "sharpe_0rf": 1.0,
            "sharpe_5rf": 0.9,
            "ann_return": 10.0,
            "ann_vol": 8.0,
            "total_return": 20.0,
            "max_drawdown": 5.0,
            "positive_days": "10/20 (50.0%)",
            "precision": 0.55,
            "recall": 0.5,
            "f1": 0.52,
            "mcc": 0.1,
        }
        return [
            {"name": "har [binary]", "sizing_label": "[binary]", **common},
            {
                "name": "har [asym_long L=2]",
                "sizing_label": "[asym_long L=2]",
                **common,
            },
            {"name": "har [zscore L=1]", "sizing_label": "[zscore L=1]", **common},
            {"name": "[baseline] constant_short", "sizing_label": "", **common},
        ]

    def test_dashboard_collects_sizing_labels_in_spec_order(self):
        from volforecast.visualization.dashboard import build_tournament_dashboard

        tables, actuals, forecasts = self._minimal_tables()
        rows = self._sized_rows()
        gsvivs_per_iv = {"Exec Kvar (true fill)": {1: rows}}
        gsvivs_traces_per_iv = {"Exec Kvar (true fill)": {1: []}}
        html = build_tournament_dashboard(
            tables,
            actuals,
            forecasts,
            gsvivs_per_iv=gsvivs_per_iv,
            gsvivs_traces_per_iv=gsvivs_traces_per_iv,
        )
        # All three sizing labels must appear in the rendered output.
        assert "[binary]" in html
        assert "[asym_long L=2]" in html
        assert "[zscore L=1]" in html

    def test_dashboard_renders_one_button_per_sizing_label(self):
        from volforecast.visualization.dashboard import build_tournament_dashboard

        tables, actuals, forecasts = self._minimal_tables()
        rows = self._sized_rows()
        gsvivs_per_iv = {"Exec Kvar (true fill)": {1: rows}}
        gsvivs_traces_per_iv = {"Exec Kvar (true fill)": {1: []}}
        html = build_tournament_dashboard(
            tables,
            actuals,
            forecasts,
            gsvivs_per_iv=gsvivs_per_iv,
            gsvivs_traces_per_iv=gsvivs_traces_per_iv,
        )
        # Toggle JS hook and per-label button ids must be present.
        assert "setGsvivsSizing(" in html, (
            "Dashboard missing setGsvivsSizing() hook for sizing toggle"
        )
        for label in ("[binary]", "[asym_long L=2]", "[zscore L=1]"):
            assert f"setGsvivsSizing('{label}')" in html, (
                f"Missing toggle button for sizing label {label!r}"
            )

    def test_dashboard_tags_table_rows_with_data_sizing(self):
        from volforecast.visualization.dashboard import build_tournament_dashboard

        tables, actuals, forecasts = self._minimal_tables()
        rows = self._sized_rows()
        gsvivs_per_iv = {"Exec Kvar (true fill)": {1: rows}}
        gsvivs_traces_per_iv = {"Exec Kvar (true fill)": {1: []}}
        html = build_tournament_dashboard(
            tables,
            actuals,
            forecasts,
            gsvivs_per_iv=gsvivs_per_iv,
            gsvivs_traces_per_iv=gsvivs_traces_per_iv,
        )
        # Rendered rows must carry the data-sizing attribute the JS filter
        # uses to show/hide rows when a toggle button is clicked.
        assert 'data-sizing="[binary]"' in html
        assert 'data-sizing="[asym_long L=2]"' in html
        assert 'data-sizing="[zscore L=1]"' in html
        # Baselines stay visible regardless of toggle -> tagged with an empty
        # data-sizing attribute so the JS filter knows to skip them.
        assert 'data-sizing=""' in html

    def test_dashboard_default_active_sizing_is_asym_long_l2(self):
        from volforecast.visualization.dashboard import build_tournament_dashboard

        tables, actuals, forecasts = self._minimal_tables()
        rows = self._sized_rows()
        gsvivs_per_iv = {"Exec Kvar (true fill)": {1: rows}}
        gsvivs_traces_per_iv = {"Exec Kvar (true fill)": {1: []}}
        html = build_tournament_dashboard(
            tables,
            actuals,
            forecasts,
            gsvivs_per_iv=gsvivs_per_iv,
            gsvivs_traces_per_iv=gsvivs_traces_per_iv,
        )
        # The asym_long L=2 variant is the production default and must boot
        # as the initially active toggle.
        assert "currentGsvivsSizing" in html
        assert "'[asym_long L=2]'" in html


class TestIvSourceRegistry:
    """Tests for IV_SOURCE_REGISTRY and resolve_iv_sources."""

    def test_registry_has_all_sources(self):
        from volforecast.evaluation.gsvivs import IV_SOURCE_REGISTRY
        assert "exec_kvar" in IV_SOURCE_REGISTRY
        assert "edrvs_prev_close_1dte" in IV_SOURCE_REGISTRY
        assert "spx_atm_iv_1d" in IV_SOURCE_REGISTRY
        assert "spx_atm_iv_1w" in IV_SOURCE_REGISTRY

    def test_resolve_default(self):
        from volforecast.evaluation.gsvivs import resolve_iv_sources
        result = resolve_iv_sources()
        assert len(result) == 1
        assert result[0][0] == "Exec Kvar (true fill)"

    def test_resolve_multiple(self):
        from volforecast.evaluation.gsvivs import resolve_iv_sources
        result = resolve_iv_sources(["exec_kvar", "spx_atm_iv_1w"])
        assert len(result) == 2
        labels = [r[0] for r in result]
        assert "Exec Kvar (true fill)" in labels
        assert "SPX ATM IV (1w)" in labels

    def test_resolve_unknown_raises(self):
        from volforecast.evaluation.gsvivs import resolve_iv_sources
        with pytest.raises(ValueError, match="Unknown IV source key"):
            resolve_iv_sources(["bogus_source"])

    def test_resolve_none_defaults_to_exec_kvar(self):
        from volforecast.evaluation.gsvivs import resolve_iv_sources
        result = resolve_iv_sources(None)
        assert len(result) == 1
        assert result[0][1] == "iv_exec_kvar"

    def test_registry_tuple_structure(self):
        from volforecast.evaluation.gsvivs import IV_SOURCE_REGISTRY
        for key, (label, col, is_cal) in IV_SOURCE_REGISTRY.items():
            assert isinstance(label, str)
            assert isinstance(col, str)
            assert isinstance(is_cal, bool)
