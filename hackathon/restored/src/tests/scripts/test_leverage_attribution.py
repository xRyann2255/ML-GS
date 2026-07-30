"""Tests for leverage attribution data assembly script."""
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

from leverage_attribution import assemble_leverage_data, OUTPUT_PATH

EXPECTED_COLUMNS = [
    "spx_return_t1",
    "vix_change_t1",
    "rolling_corr_21d",
    "ml_signal",
    "gsvivs_daily_return",
]


@pytest.mark.integration
class TestLeverageAttribution:
    """Integration tests for leverage attribution data assembly."""

    @pytest.fixture(scope="class")
    def assembled_df(self) -> pd.DataFrame:
        """Run assembly once for all tests in this class."""
        return assemble_leverage_data()

    def test_output_has_correct_columns(self, assembled_df: pd.DataFrame):
        assert list(assembled_df.columns) == EXPECTED_COLUMNS

    def test_date_range_starts_around_2022_05(self, assembled_df: pd.DataFrame):
        start = assembled_df.index.min()
        # Should start in May or June 2022 (after 21-day warmup)
        assert start.year == 2022
        assert start.month <= 7, f"Start date too late: {start}"

    def test_no_nan_values(self, assembled_df: pd.DataFrame):
        nan_counts = assembled_df.isna().sum()
        assert nan_counts.sum() == 0, f"NaN values found:\n{nan_counts[nan_counts > 0]}"

    def test_signal_is_binary(self, assembled_df: pd.DataFrame):
        unique_vals = set(assembled_df["ml_signal"].unique())
        assert unique_vals <= {0, 1}, f"Signal has non-binary values: {unique_vals}"

    def test_signal_has_both_classes(self, assembled_df: pd.DataFrame):
        counts = assembled_df["ml_signal"].value_counts()
        assert 1 in counts.index, "No short-vol signals (1) found"
        assert 0 in counts.index, "No flat signals (0) found"

    def test_no_lookahead_bias_spx(self, assembled_df: pd.DataFrame):
        """spx_return_t1 on date T should equal SPX return from T-2 to T-1."""
        from leverage_attribution import load_spx

        spx = load_spx()
        spx_ret = spx.pct_change()
        # For a sample date in the assembled data, verify alignment
        sample_dates = assembled_df.index[10:15]
        for t in sample_dates:
            # spx_return_t1[T] should be the return on T-1
            t_minus_1 = spx_ret.index[spx_ret.index < t][-1]
            expected = spx_ret.loc[t_minus_1]
            actual = assembled_df.loc[t, "spx_return_t1"]
            np.testing.assert_allclose(
                actual, expected, rtol=1e-10,
                err_msg=f"Lookahead bias at {t}: got {actual}, expected {expected}"
            )

    def test_no_lookahead_bias_vix(self, assembled_df: pd.DataFrame):
        """vix_change_t1 on date T should equal VIX change from T-2 to T-1."""
        from leverage_attribution import load_vix

        vix = load_vix()
        vix_chg = vix.diff()
        sample_dates = assembled_df.index[10:15]
        for t in sample_dates:
            t_minus_1 = vix_chg.index[vix_chg.index < t][-1]
            expected = vix_chg.loc[t_minus_1]
            actual = assembled_df.loc[t, "vix_change_t1"]
            np.testing.assert_allclose(
                actual, expected, rtol=1e-10,
                err_msg=f"Lookahead bias at {t}: got {actual}, expected {expected}"
            )

    def test_output_parquet_can_be_saved(self, assembled_df: pd.DataFrame):
        """Verify the output path is writable and round-trips correctly."""
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        assembled_df.to_parquet(OUTPUT_PATH)
        assert OUTPUT_PATH.exists()
        reloaded = pd.read_parquet(OUTPUT_PATH)
        assert list(reloaded.columns) == EXPECTED_COLUMNS
        assert len(reloaded) == len(assembled_df)

    def test_reasonable_row_count(self, assembled_df: pd.DataFrame):
        """Should have roughly 2-4 years of trading days (~500-1000 rows)."""
        assert len(assembled_df) >= 400, f"Too few rows: {len(assembled_df)}"
        assert len(assembled_df) <= 1200, f"Too many rows: {len(assembled_df)}"
