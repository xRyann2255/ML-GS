"""Tests for the reporting module."""

from __future__ import annotations

import pytest

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig


@pytest.fixture
def sample_config(tmp_path):
    """Create a minimal ExperimentConfig for testing."""
    return ExperimentConfig(
        name="test_report",
        universe=["SPY"],
        date_range=("2020-01-02", "2023-12-31"),
        horizons=[1, 5],
        feature_layers=["har_core"],
        model=ModelConfig(name="har", params={}),
        cv=CVConfig(method="expanding_window"),
        output_dir=tmp_path / "models" / "test_report",
    )


class TestGenerateReport:
    """Tests for the main generate_report() function."""

    def test_generate_report_raises_not_implemented(self, sample_config):
        """Stub raises NotImplementedError until implemented."""
        from volforecast.reporting import generate_report

        with pytest.raises(NotImplementedError, match="TODO"):
            generate_report(sample_config)


class TestSections:
    """Tests for individual report section renderers."""

    def test_summary_raises_not_implemented(self):
        from volforecast.reporting.sections.summary import render

        with pytest.raises(NotImplementedError, match="TODO"):
            render({}, {})

    def test_forecast_vs_actual_raises_not_implemented(self):
        from volforecast.reporting.sections.forecast_vs_actual import render

        with pytest.raises(NotImplementedError, match="TODO"):
            render({})

    def test_qlike_analysis_raises_not_implemented(self):
        from volforecast.reporting.sections.qlike_analysis import render

        with pytest.raises(NotImplementedError, match="TODO"):
            render({})

    def test_diagnostics_raises_not_implemented(self):
        from volforecast.reporting.sections.diagnostics import render

        with pytest.raises(NotImplementedError, match="TODO"):
            render({})

    def test_statistical_tests_raises_not_implemented(self):
        from volforecast.reporting.sections.statistical_tests import render

        with pytest.raises(NotImplementedError, match="TODO"):
            render({})

    def test_economic_value_renders_html_with_market_data(self):
        """Economic value section renders HTML when market_data is provided."""
        import numpy as np
        import pandas as pd

        from volforecast.reporting.sections.economic_value import render

        rng = np.random.default_rng(42)
        n = 200
        dates = pd.bdate_range("2022-01-03", periods=n)

        # predictions: {symbol: {horizon: DataFrame with 'prediction'}}
        predictions = {
            "SPY": {
                1: pd.DataFrame(
                    {"prediction": rng.normal(-8.5, 0.5, n)},
                    index=dates,
                ),
            },
        }

        # market_data: DataFrame with iv_1m_atm, close, log_rv columns
        market_data = pd.DataFrame(
            {
                "symbol": ["SPY"] * n,
                "iv_1m_atm": rng.uniform(15, 25, n),  # in % units
                "close": 100.0 + np.cumsum(rng.normal(0, 1, n)),
                "log_rv": rng.normal(-8.5, 0.5, n),
            },
            index=dates,
        )

        html = render(predictions, market_data=market_data)
        assert "<section" in html
        assert "Economic Value" in html
        assert "Sharpe" in html

    def test_economic_value_renders_placeholder_without_market_data(self):
        """Without market_data, renders a placeholder message."""
        import numpy as np
        import pandas as pd

        from volforecast.reporting.sections.economic_value import render

        rng = np.random.default_rng(42)
        n = 100
        dates = pd.bdate_range("2022-01-03", periods=n)
        predictions = {
            "SPY": {
                1: pd.DataFrame(
                    {"prediction": rng.normal(-8.5, 0.5, n)},
                    index=dates,
                ),
            },
        }

        html = render(predictions, market_data=None)
        assert "<section" in html
        assert "not available" in html.lower() or "placeholder" in html.lower()
