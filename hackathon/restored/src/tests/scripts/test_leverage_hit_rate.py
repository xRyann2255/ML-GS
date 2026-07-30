"""Tests for leverage attribution hit-rate analysis (Step 2)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "workspace" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from leverage_attribution import compute_attribution, OUTPUT_PATH


# ---------------------------------------------------------------------------
# Unit tests with synthetic data
# ---------------------------------------------------------------------------


class TestComputeAttributionSynthetic:
    """Unit tests using synthetic data with known outcomes."""

    @pytest.fixture
    def synthetic_df(self) -> pd.DataFrame:
        """Create a small synthetic dataset with known outcomes.

        Layout (10 days):
        - Days 0-4: SPX was up yesterday (spx_return_t1 >= 0)
        - Days 5-9: SPX was down yesterday (spx_return_t1 < 0)
        - Days 5-7: correlation < -0.5 (corr leverage triggers)
        - Days 8-9: correlation > -0.5 (corr leverage does NOT trigger)

        GSVIVS returns:
        - Days 0,1,2,3,5,6: positive (no loss)
        - Days 4,7,8,9: negative (loss days)

        ML signal: stand aside on days 4,7,8 (ml_signal=0)
        """
        dates = pd.date_range("2023-01-02", periods=10, freq="B")
        df = pd.DataFrame(
            {
                "spx_return_t1": [0.01, 0.005, 0.002, 0.01, 0.003,
                                  -0.01, -0.005, -0.02, -0.01, -0.003],
                "vix_change_t1": [-0.5, -0.3, -0.1, -0.4, -0.2,
                                  1.0, 0.5, 1.5, 0.8, 0.2],
                "rolling_corr_21d": [-0.7, -0.6, -0.8, -0.5, -0.4,
                                     -0.8, -0.6, -0.7, -0.3, -0.2],
                "ml_signal": [1, 1, 1, 1, 0, 1, 1, 0, 0, 1],
                "gsvivs_daily_return": [0.005, 0.003, 0.002, 0.004, -0.01,
                                        0.006, 0.003, -0.015, -0.008, -0.005],
            },
            index=dates,
        )
        return df

    def test_simple_leverage_signal(self, synthetic_df: pd.DataFrame):
        """Simple leverage: stand aside when spx_return_t1 < 0 (days 5-9)."""
        # Days 5-9 have negative spx_return_t1 → simple_lev = 0
        # Days 0-4 have positive spx_return_t1 → simple_lev = 1
        # Firing rate = 5/10 = 50%
        result = compute_attribution(synthetic_df)
        assert "Simple Lev" in result

    def test_corr_leverage_signal(self, synthetic_df: pd.DataFrame):
        """Corr leverage: stand aside when spx < 0 AND corr < -0.5 (days 5,6,7)."""
        # Days 5,6,7: spx < 0 AND corr < -0.5 → corr_lev = 0
        # Days 8,9: spx < 0 but corr > -0.5 → corr_lev = 1
        # Firing rate = 3/10 = 30%
        result = compute_attribution(synthetic_df)
        assert "Corr Lev" in result

    def test_precision_ml(self, synthetic_df: pd.DataFrame):
        """ML stands aside on days 4,7,8. Loss days are 4,7,8,9.
        ML stand-aside precision = 3/3 = 100%."""
        result = compute_attribution(synthetic_df)
        # ML stands aside on days 4,7,8 — all are loss days → 100% precision
        assert "ML Signal" in result
        # Parse ML precision from the output
        lines = result.split("\n")
        precision_line = [l for l in lines if "Stand-aside precision" in l][0]
        # ML is the first value after the label
        ml_precision = float(precision_line.split("%")[0].split()[-1])
        assert ml_precision == pytest.approx(100.0, abs=0.1)

    def test_precision_simple_leverage(self, synthetic_df: pd.DataFrame):
        """Simple lev stands aside on days 5-9. Loss days in that set: 7,8,9.
        Precision = 3/5 = 60%."""
        result = compute_attribution(synthetic_df)
        lines = result.split("\n")
        precision_line = [l for l in lines if "Stand-aside precision" in l][0]
        parts = precision_line.replace("%", "").split()
        # Find the Simple Lev value (second percentage)
        # Format: "Stand-aside precision   100.0%   60.0%   66.7%"
        pct_values = [float(x) for x in parts if _is_float(x)]
        assert len(pct_values) >= 2
        assert pct_values[1] == pytest.approx(60.0, abs=0.1)

    def test_precision_corr_leverage(self, synthetic_df: pd.DataFrame):
        """Corr lev stands aside on days 5,6,7. Loss day in that set: 7.
        Precision = 1/3 = 33.3%."""
        result = compute_attribution(synthetic_df)
        lines = result.split("\n")
        precision_line = [l for l in lines if "Stand-aside precision" in l][0]
        parts = precision_line.replace("%", "").split()
        pct_values = [float(x) for x in parts if _is_float(x)]
        assert len(pct_values) >= 3
        assert pct_values[2] == pytest.approx(33.3, abs=0.1)

    def test_hit_rate_ml(self, synthetic_df: pd.DataFrame):
        """ML hit rate:
        - signal=1 AND no loss: days 0,1,2,3,5,6 → 6 correct
        - signal=0 AND loss: days 4,7,8 → 3 correct
        - signal=1 AND loss: day 9 → 1 incorrect
        Total correct = 9/10 = 90%."""
        result = compute_attribution(synthetic_df)
        lines = result.split("\n")
        hit_line = [l for l in lines if "Overall hit rate" in l][0]
        parts = hit_line.replace("%", "").split()
        pct_values = [float(x) for x in parts if _is_float(x)]
        assert pct_values[0] == pytest.approx(90.0, abs=0.1)

    def test_always_short_sharpe(self, synthetic_df: pd.DataFrame):
        """Always-short sharpe uses all gsvivs returns."""
        result = compute_attribution(synthetic_df)
        assert "Always-short Sharpe:" in result
        # Extract value
        line = [l for l in result.split("\n") if "Always-short Sharpe:" in l][0]
        sharpe_val = float(line.split(":")[-1].strip())
        # Manually compute
        rets = synthetic_df["gsvivs_daily_return"]
        expected = rets.mean() / rets.std() * np.sqrt(252)
        assert sharpe_val == pytest.approx(expected, abs=0.01)

    def test_output_contains_all_sections(self, synthetic_df: pd.DataFrame):
        result = compute_attribution(synthetic_df)
        expected_sections = [
            "LEVERAGE ATTRIBUTION",
            "Signal Comparison",
            "Baselines",
            "Disagreement Analysis (vs Simple Leverage Rule)",
            "Disagreement Analysis (vs Correlated Leverage Rule)",
            "Interpretation",
        ]
        for section in expected_sections:
            assert section in result, f"Missing section: {section}"

    def test_firing_rate_simple(self, synthetic_df: pd.DataFrame):
        """Simple leverage fires on 5/10 = 50% of days."""
        result = compute_attribution(synthetic_df)
        lines = result.split("\n")
        firing_line = [l for l in lines if "Stand-aside firing rate" in l][0]
        parts = firing_line.replace("%", "").split()
        pct_values = [float(x) for x in parts if _is_float(x)]
        assert pct_values[1] == pytest.approx(50.0, abs=0.1)


# ---------------------------------------------------------------------------
# Integration tests on real data
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestComputeAttributionReal:
    """Integration tests using the real aligned parquet from Step 1."""

    @pytest.fixture(scope="class")
    def real_df(self) -> pd.DataFrame:
        if not OUTPUT_PATH.exists():
            pytest.skip(f"Aligned data not found at {OUTPUT_PATH}")
        df = pd.read_parquet(OUTPUT_PATH)
        df.index = pd.to_datetime(df.index)
        return df

    @pytest.fixture(scope="class")
    def attribution_output(self, real_df: pd.DataFrame) -> str:
        return compute_attribution(real_df)

    def test_output_is_nonempty(self, attribution_output: str):
        assert len(attribution_output) > 100

    def test_contains_section_headers(self, attribution_output: str):
        expected = [
            "LEVERAGE ATTRIBUTION",
            "Signal Comparison",
            "Baselines",
            "Disagreement Analysis (vs Simple Leverage Rule)",
            "Disagreement Analysis (vs Correlated Leverage Rule)",
            "Interpretation",
        ]
        for header in expected:
            assert header in attribution_output, f"Missing header: {header}"

    def test_sharpe_values_reasonable(self, attribution_output: str):
        """All Sharpe ratios should be finite and in a reasonable range."""
        import re

        sharpe_pattern = re.compile(r"Sharpe[:\s]+(-?\d+\.\d+)")
        matches = sharpe_pattern.findall(attribution_output)
        assert len(matches) >= 5, f"Expected >=5 Sharpe values, found {len(matches)}"
        for val_str in matches:
            val = float(val_str)
            assert not np.isnan(val), f"NaN Sharpe found"
            assert -3.0 <= val <= 7.0, f"Sharpe {val} out of range [-3, 7]"

    def test_precision_values_valid(self, attribution_output: str):
        """Precision values should be between 0 and 100."""
        import re

        # Match "precision" lines with percentage values
        precision_pattern = re.compile(r"precision.*?(\d+\.\d+)%")
        matches = precision_pattern.findall(attribution_output)
        assert len(matches) >= 3, f"Expected >=3 precision values, found {len(matches)}"
        for val_str in matches:
            val = float(val_str)
            assert 0.0 <= val <= 100.0, f"Precision {val}% out of range [0, 100]"

    def test_firing_rates_valid(self, attribution_output: str):
        """Firing rates should be between 0 and 100."""
        import re

        line = [l for l in attribution_output.split("\n") if "firing rate" in l][0]
        vals = re.findall(r"(\d+\.\d+)%", line)
        assert len(vals) == 3
        for v in vals:
            assert 0.0 <= float(v) <= 100.0

    def test_loss_days_reported(self, attribution_output: str):
        """Output should report loss day count."""
        assert "Loss days (GSVIVS return < 0):" in attribution_output

    def test_date_range_reported(self, attribution_output: str):
        """Output should contain date range."""
        import re

        assert re.search(r"\d{4}-\d{2}-\d{2} to \d{4}-\d{2}-\d{2}", attribution_output)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_float(s: str) -> bool:
    """Check if a string can be parsed as a float."""
    try:
        float(s)
        return True
    except ValueError:
        return False
