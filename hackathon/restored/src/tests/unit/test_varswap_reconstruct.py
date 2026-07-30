"""Tests for variance swap strike reconstruction from EDRVOL_PERCENT_EXPIRY chain.

Covers reconstruct_0dte_varswap_strike() — numerical integration of the
CBOE VIX-style discrete formula to compute model-free implied variance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class TestReconstructVarswapStrike:
    """Tests for model-free implied variance reconstruction."""

    def test_known_chain_produces_expected_variance(self):
        """Textbook example: uniform IV across strikes → variance ≈ IV^2."""
        from volforecast.data.varswap_reconstruct import compute_varswap_strike_from_chain

        # Flat smile at 20% IV with longer maturity for numerical stability
        # (very short T with sparse grid causes finite-difference errors)
        strikes = np.array(
            [0.90, 0.92, 0.95, 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 1.03, 1.05, 1.08, 1.10]
        )
        ivs = np.full_like(strikes, 20.0)  # 20% flat smile
        T = 30.0 / 252.0  # 30 days for better numerical stability
        forward = 1.0
        r = 0.05

        result = compute_varswap_strike_from_chain(strikes, ivs, T, forward, r)

        # For flat smile, var swap strike should be close to the common IV
        assert result is not None
        assert abs(result - 20.0) < 2.0  # Within 2 vol pts (grid truncation effects)

    def test_skew_produces_higher_variance_than_atm(self):
        """With put-skew, variance swap strike > ATM IV (OTM puts are expensive)."""
        from volforecast.data.varswap_reconstruct import compute_varswap_strike_from_chain

        # Steep skew: OTM puts have higher IV, OTM calls lower
        strikes = np.array(
            [0.90, 0.92, 0.95, 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 1.03, 1.05, 1.08, 1.10]
        )
        # Typical SPX skew pattern
        ivs = np.array(
            [35.0, 32.0, 28.0, 24.0, 22.0, 21.0, 20.0, 19.5, 19.0, 18.5, 18.0, 17.5, 17.0]
        )
        T = 30.0 / 252.0  # 30 days for numerical stability
        forward = 1.0
        r = 0.05

        result = compute_varswap_strike_from_chain(strikes, ivs, T, forward, r)

        # With skew, var swap strike should exceed ATM (20%)
        assert result is not None
        assert result > 20.0, f"Var swap strike {result} should exceed ATM IV (20%)"

    def test_weights_otm_puts_more_than_calls(self):
        """The 1/K^2 weighting gives more weight to lower strikes (OTM puts)."""
        from volforecast.data.varswap_reconstruct import compute_varswap_strike_from_chain

        strikes = np.array([0.90, 0.95, 1.00, 1.05, 1.10])
        T = 30.0 / 252.0
        forward = 1.0
        r = 0.05

        # Case A: only OTM puts are expensive
        ivs_put_skew = np.array([30.0, 25.0, 20.0, 20.0, 20.0])
        result_put = compute_varswap_strike_from_chain(
            strikes_rel=strikes, ivs=ivs_put_skew, T=T, forward=forward, r=r
        )

        # Case B: only OTM calls are expensive (same magnitude)
        ivs_call_skew = np.array([20.0, 20.0, 20.0, 25.0, 30.0])
        result_call = compute_varswap_strike_from_chain(
            strikes_rel=strikes, ivs=ivs_call_skew, T=T, forward=forward, r=r
        )

        # Put-skew should produce HIGHER variance than call-skew
        # because 1/K^2 weights puts (K < F) more heavily
        assert result_put > result_call, (
            f"Put-skew var ({result_put:.2f}) should exceed call-skew var ({result_call:.2f})"
        )

    def test_handles_missing_strikes_gracefully(self):
        """Returns result even with gaps in strike grid (uses available strikes)."""
        from volforecast.data.varswap_reconstruct import compute_varswap_strike_from_chain

        # Only 5 strikes available (sparse)
        strikes = np.array([0.90, 0.95, 1.00, 1.05, 1.10])
        ivs = np.array([25.0, 22.0, 20.0, 19.0, 18.0])
        T = 30.0 / 252.0
        forward = 1.0
        r = 0.05

        result = compute_varswap_strike_from_chain(strikes, ivs, T, forward, r)

        # Should still produce a valid result
        assert result is not None
        assert 15.0 < result < 40.0  # Reasonable range

    def test_returns_nan_for_insufficient_strikes(self):
        """Returns NaN when fewer than 3 valid strikes available."""
        from volforecast.data.varswap_reconstruct import compute_varswap_strike_from_chain

        # Only 2 strikes — insufficient for integration
        strikes = np.array([0.95, 1.05])
        ivs = np.array([22.0, 19.0])
        T = 30.0 / 252.0
        forward = 1.0
        r = 0.05

        result = compute_varswap_strike_from_chain(strikes, ivs, T, forward, r)

        assert result is None or np.isnan(result)

    def test_returns_nan_for_zero_time_to_expiry(self):
        """Returns NaN when T=0 (division by zero protection)."""
        from volforecast.data.varswap_reconstruct import compute_varswap_strike_from_chain

        strikes = np.array([0.90, 0.95, 1.00, 1.05, 1.10])
        ivs = np.array([25.0, 22.0, 20.0, 19.0, 18.0])
        T = 0.0
        forward = 1.0
        r = 0.05

        result = compute_varswap_strike_from_chain(strikes, ivs, T, forward, r)

        assert result is None or np.isnan(result)

    def test_output_is_in_vol_percent(self):
        """Output is annualized vol in percentage points (not decimal, not variance)."""
        from volforecast.data.varswap_reconstruct import compute_varswap_strike_from_chain

        strikes = np.array(
            [0.90, 0.92, 0.95, 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 1.03, 1.05, 1.08, 1.10]
        )
        ivs = np.full_like(strikes, 20.0)
        T = 30.0 / 252.0
        forward = 1.0
        r = 0.05

        result = compute_varswap_strike_from_chain(strikes, ivs, T, forward, r)

        # Should be in vol% range (5-80%), not variance range (0.0004-0.64)
        assert 5.0 < result < 80.0


class TestReconstructFromMarquee:
    """Tests for the end-to-end reconstruction from Marquee EDRVOL_PERCENT_EXPIRY."""

    def test_reconstruct_series_returns_correct_type(self):
        """reconstruct_0dte_varswap_strike returns pd.Series with proper name."""
        from unittest.mock import patch

        from volforecast.data.varswap_reconstruct import reconstruct_0dte_varswap_strike

        # Mock the Marquee query to return a multi-strike IV chain
        # Need enough strikes for the discrete integration to converge
        strikes = [
            0.90,
            0.92,
            0.94,
            0.95,
            0.96,
            0.97,
            0.98,
            0.99,
            1.00,
            1.01,
            1.02,
            1.03,
            1.04,
            1.05,
            1.06,
            1.08,
            1.10,
        ]
        ivs = [
            30.0,
            28.0,
            26.0,
            25.0,
            24.0,
            23.0,
            22.0,
            21.0,
            20.0,
            19.5,
            19.0,
            18.5,
            18.0,
            17.5,
            17.0,
            16.5,
            16.0,
        ]
        n = len(strikes)
        mock_data = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-06-03")] * n,
                "expirationDate": [pd.Timestamp("2024-06-03")] * n,
                "relativeStrike": strikes,
                "impliedVolatility": ivs,
                "strikeReference": ["forward"] * n,
            }
        )

        with patch(
            "volforecast.data.varswap_reconstruct._query_expiry_chain",
            return_value=mock_data,
        ):
            from datetime import date

            result = reconstruct_0dte_varswap_strike(date(2024, 6, 3), date(2024, 6, 3))

        assert isinstance(result, pd.Series)
        assert result.name == "iv_vs_0dte_reconstructed"
        assert len(result) > 0

    def test_reconstruct_returns_empty_on_no_data(self):
        """Returns empty Series when no option chain data available."""
        from datetime import date
        from unittest.mock import patch

        from volforecast.data.varswap_reconstruct import reconstruct_0dte_varswap_strike

        with patch(
            "volforecast.data.varswap_reconstruct._query_expiry_chain",
            return_value=pd.DataFrame(),
        ):
            result = reconstruct_0dte_varswap_strike(date(2024, 6, 3), date(2024, 6, 7))

        assert isinstance(result, pd.Series)
        assert len(result) == 0
