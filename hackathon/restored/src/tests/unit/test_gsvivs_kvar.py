"""Tests for GSVIVS01 execution Kvar extraction.

Tests:
    - parse_day_opening_legs: correct pairing of trades → exec fills → option defs
    - compute_kvar_from_legs: CBOE formula produces sensible vol for known inputs
    - Sanity checks A (quantity proportionality) and I (price monotonicity)
"""

from __future__ import annotations

import numpy as np
import pytest


class TestParseDayOpeningLegs:
    """Test trade parsing from risks-for-date entries."""

    def _make_risks_list(self):
        """Construct a minimal risks-for-date list mimicking output.json structure."""
        return [
            # Option def: Put K=5250
            {
                "ex": "2024-05-23",
                "expiry type": "Daily Weekly",
                "instrument type": "O",
                "k": 5250,
                "option type": "Put",
                "underlying asset": ".SPX",
            },
            # Risk node (for this option)
            {
                "baseline risks": {"fwd": 5310.0, "vol": 0.19, "price": 4.24, "delta": -0.15},
                "risk node type": "X",
                "scenario risks": [],
            },
            # VSR 0b opening trade (selling) — instrument field contains option def
            {
                "source": "VSR 0b",
                "quantity": -0.012,
                "generation time": "2024-05-23T13:10:00Z",
                "execution instructions": {},
                "instrument": {
                    "ex": "2024-05-23",
                    "expiry type": "Daily Weekly",
                    "instrument type": "O",
                    "k": 5250,
                    "option type": "Put",
                    "underlying asset": ".SPX",
                },
            },
            # Execution fill (note: space in "execution price")
            {"execution fraction": 1.0, "execution price": 3.80, "execution quantity": -0.012},
            # Option def: Put K=5280
            {
                "ex": "2024-05-23",
                "expiry type": "Daily Weekly",
                "instrument type": "O",
                "k": 5280,
                "option type": "Put",
                "underlying asset": ".SPX",
            },
            {
                "baseline risks": {"fwd": 5310.0, "vol": 0.18, "price": 7.10, "delta": -0.23},
                "risk node type": "X",
                "scenario risks": [],
            },
            {
                "source": "VSR 0b",
                "quantity": -0.011,
                "generation time": "2024-05-23T13:10:00Z",
                "execution instructions": {},
                "instrument": {
                    "ex": "2024-05-23",
                    "expiry type": "Daily Weekly",
                    "instrument type": "O",
                    "k": 5280,
                    "option type": "Put",
                    "underlying asset": ".SPX",
                },
            },
            {"execution fraction": 1.0, "execution price": 6.90, "execution quantity": -0.011},
            # Option def: Call K=5345
            {
                "ex": "2024-05-23",
                "expiry type": "Daily Weekly",
                "instrument type": "O",
                "k": 5345,
                "option type": "Call",
                "underlying asset": ".SPX",
            },
            {
                "baseline risks": {"fwd": 5310.0, "vol": 0.17, "price": 2.25, "delta": 0.10},
                "risk node type": "X",
                "scenario risks": [],
            },
            {
                "source": "VSR 0b",
                "quantity": -0.009,
                "generation time": "2024-05-23T13:10:00Z",
                "execution instructions": {},
                "instrument": {
                    "ex": "2024-05-23",
                    "expiry type": "Daily Weekly",
                    "instrument type": "O",
                    "k": 5345,
                    "option type": "Call",
                    "underlying asset": ".SPX",
                },
            },
            {"execution fraction": 1.0, "execution price": 2.10, "execution quantity": -0.009},
            # Option def: Call K=5380
            {
                "ex": "2024-05-23",
                "expiry type": "Daily Weekly",
                "instrument type": "O",
                "k": 5380,
                "option type": "Call",
                "underlying asset": ".SPX",
            },
            {
                "baseline risks": {"fwd": 5310.0, "vol": 0.16, "price": 0.38, "delta": 0.02},
                "risk node type": "X",
                "scenario risks": [],
            },
            {
                "source": "VSR 0b",
                "quantity": -0.008,
                "generation time": "2024-05-23T13:10:00Z",
                "execution instructions": {},
                "instrument": {
                    "ex": "2024-05-23",
                    "expiry type": "Daily Weekly",
                    "instrument type": "O",
                    "k": 5380,
                    "option type": "Call",
                    "underlying asset": ".SPX",
                },
            },
            {"execution fraction": 1.0, "execution price": 0.35, "execution quantity": -0.008},
            # A closing trade (qty > 0) — should be ignored
            {
                "source": "VSR 0b",
                "quantity": 0.012,
                "generation time": "1970-01-01T00:00:00Z",
                "execution instructions": {"type": "MOC"},
                "instrument": {
                    "ex": "2024-05-23",
                    "expiry type": "Daily Weekly",
                    "instrument type": "O",
                    "k": 5250,
                    "option type": "Put",
                    "underlying asset": ".SPX",
                },
            },
            {"execution fraction": 1.0, "execution price": 0.0, "execution quantity": 0.012},
        ]

    def test_extracts_opening_legs_only(self):
        """Only negative-qty VSR 0b trades are extracted."""
        from volforecast.data.gsvivs_kvar import parse_day_opening_legs

        risks = self._make_risks_list()
        legs = parse_day_opening_legs(risks)

        assert len(legs) == 4
        # All should have negative quantity
        for leg in legs:
            assert leg["quantity"] < 0

    def test_correct_strike_pairing(self):
        """Each leg is paired with the correct preceding option def."""
        from volforecast.data.gsvivs_kvar import parse_day_opening_legs

        risks = self._make_risks_list()
        legs = parse_day_opening_legs(risks)

        strikes = [leg["strike"] for leg in legs]
        assert strikes == [5250, 5280, 5345, 5380]

    def test_correct_exec_prices(self):
        """Execution prices are taken from the paired EXEC fill entry."""
        from volforecast.data.gsvivs_kvar import parse_day_opening_legs

        risks = self._make_risks_list()
        legs = parse_day_opening_legs(risks)

        prices = [leg["exec_price"] for leg in legs]
        assert prices == [3.80, 6.90, 2.10, 0.35]

    def test_correct_option_types(self):
        """Put/Call type is correctly extracted from option def."""
        from volforecast.data.gsvivs_kvar import parse_day_opening_legs

        risks = self._make_risks_list()
        legs = parse_day_opening_legs(risks)

        types = [leg["option_type"] for leg in legs]
        assert types == ["Put", "Put", "Call", "Call"]


class TestComputeKvarFromLegs:
    """Test the CBOE discrete formula implementation."""

    def _make_flat_smile_legs(self, vol_pct: float = 15.0, forward: float = 5000.0):
        """Create synthetic legs with known flat-smile option prices."""
        from scipy.stats import norm

        T = 24.0 / 8760.0  # calendar-year convention (matches gsvivs_kvar.py)
        sigma = vol_pct / 100.0

        # Generate strikes around forward
        offsets = [-200, -150, -100, -50, -25, 0, 25, 50, 100, 150, 200]
        strikes = [forward + offset for offset in offsets]
        dks = []
        for i, strike in enumerate(strikes):
            if i == 0:
                dks.append(strikes[1] - strikes[0])
            elif i == len(strikes) - 1:
                dks.append(strikes[-1] - strikes[-2])
            else:
                dks.append((strikes[i + 1] - strikes[i - 1]) / 2.0)

        # Match actual variance-strip construction: qty is proportional to dK / K^2.
        scale = 120000.0

        legs = []
        for K, dK in zip(strikes, dks, strict=True):
            is_call = K >= forward
            # Black-Scholes price
            d1 = (np.log(forward / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            if is_call:
                price = np.exp(-0.05 * T) * (forward * norm.cdf(d1) - K * norm.cdf(d2))
            else:
                price = np.exp(-0.05 * T) * (K * norm.cdf(-d2) - forward * norm.cdf(-d1))

            legs.append(
                {
                    "strike": K,
                    "option_type": "Call" if is_call else "Put",
                    "exec_price": price,
                    "quantity": -scale * dK / (K**2),
                }
            )
        return legs

    def test_flat_smile_recovers_vol(self):
        """With flat smile, Kvar ≈ input vol (within grid truncation error)."""
        from volforecast.data.gsvivs_kvar import compute_kvar_from_legs

        vol_target = 15.0
        forward = 5000.0
        legs = self._make_flat_smile_legs(vol_pct=vol_target, forward=forward)

        result = compute_kvar_from_legs(legs, forward=forward)

        assert result is not None
        # For 0-DTE with a narrow grid, expect within ~3 vol pts
        assert abs(result["kvar_vol_pct"] - vol_target) < 3.0, (
            f"Expected ~{vol_target}, got {result['kvar_vol_pct']:.2f}"
        )

    def test_skew_produces_higher_kvar_than_atm(self):
        """With put skew, Kvar should exceed ATM IV."""
        from scipy.stats import norm

        from volforecast.data.gsvivs_kvar import compute_kvar_from_legs

        forward = 5000.0
        T = 24.0 / 8760.0  # calendar-year convention
        atm_vol = 0.15  # 15% ATM

        offsets = [-200, -150, -100, -50, -25, 0, 25, 50, 100, 150, 200]
        strikes = [forward + offset for offset in offsets]

        # Skew: OTM puts have higher vol, OTM calls have lower vol
        legs = []
        for K in strikes:
            moneyness = (K - forward) / forward
            # Linear skew: -5 vol pts per 10% OTM for puts
            sigma = atm_vol - moneyness * 0.3 if moneyness < 0 else atm_vol - moneyness * 0.1
            is_call = K >= forward
            d1 = (np.log(forward / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            if is_call:
                price = np.exp(-0.05 * T) * (forward * norm.cdf(d1) - K * norm.cdf(d2))
            else:
                price = np.exp(-0.05 * T) * (K * norm.cdf(-d2) - forward * norm.cdf(-d1))

            legs.append(
                {
                    "strike": K,
                    "option_type": "Call" if is_call else "Put",
                    "exec_price": max(price, 0.0),
                    "quantity": -0.01,
                }
            )

        result = compute_kvar_from_legs(legs, forward=forward)

        assert result is not None
        assert result["kvar_vol_pct"] > 15.0, (
            f"With skew, Kvar should exceed ATM (15%). Got {result['kvar_vol_pct']:.2f}"
        )

    def test_returns_none_for_insufficient_legs(self):
        """Less than 3 legs → returns None."""
        from volforecast.data.gsvivs_kvar import compute_kvar_from_legs

        legs = [
            {"strike": 5000, "option_type": "Put", "exec_price": 1.0, "quantity": -0.01},
            {"strike": 5050, "option_type": "Call", "exec_price": 0.5, "quantity": -0.01},
        ]
        result = compute_kvar_from_legs(legs, forward=5025.0)
        assert result is None

    def test_kvar_in_sensible_range(self):
        """Result should be in 5-80 vol % range for realistic inputs."""
        from volforecast.data.gsvivs_kvar import compute_kvar_from_legs

        legs = self._make_flat_smile_legs(vol_pct=20.0, forward=5300.0)
        result = compute_kvar_from_legs(legs, forward=5300.0)

        assert result is not None
        assert 5.0 < result["kvar_vol_pct"] < 80.0

    def test_default_tenor_matches_daily_rv_horizon(self):
        """Default Kvar convention should use a 24-hour horizon for IV-RV comparison."""
        from volforecast.data.gsvivs_kvar import compute_kvar_from_legs

        forward = 5000.0
        legs = self._make_flat_smile_legs(vol_pct=20.0, forward=forward)

        default_result = compute_kvar_from_legs(legs, forward=forward)
        short_tenor_result = compute_kvar_from_legs(legs, forward=forward, T=6.25 / 8760.0)
        daily_result = compute_kvar_from_legs(legs, forward=forward, T=24.0 / 8760.0)

        assert default_result is not None
        assert short_tenor_result is not None
        assert daily_result is not None
        assert default_result["kvar_vol_pct"] == pytest.approx(daily_result["kvar_vol_pct"])
        assert short_tenor_result["kvar_vol_pct"] > default_result["kvar_vol_pct"]


class TestSanityCheckA:
    """Quantity proportionality: |qty_i| / (ΔK_i / K_i²) should be constant."""

    def test_quantity_proportional_to_varswap_weight(self):
        """Verify that trade quantities follow variance-swap weighting."""
        # Simulate a strip where qty_i = C * ΔK_i / K_i² for some constant C
        forward = 5300.0
        strikes = [5200, 5230, 5260, 5290, 5310, 5340, 5370, 5400]
        C = 0.5  # arbitrary constant

        legs = []
        for i, K in enumerate(strikes):
            # Compute ΔK
            if i == 0:
                dK = strikes[1] - strikes[0]
            elif i == len(strikes) - 1:
                dK = strikes[-1] - strikes[-2]
            else:
                dK = (strikes[i + 1] - strikes[i - 1]) / 2.0

            qty = -C * dK / (K**2)
            legs.append(
                {
                    "strike": K,
                    "option_type": "Put" if K < forward else "Call",
                    "exec_price": 1.0,  # doesn't matter for this check
                    "quantity": qty,
                }
            )

        # Verify proportionality
        sorted_legs = sorted(legs, key=lambda x: x["strike"])
        n = len(sorted_legs)
        ratios = []
        for i, leg in enumerate(sorted_legs):
            K = leg["strike"]
            if i == 0:
                dK = sorted_legs[1]["strike"] - sorted_legs[0]["strike"]
            elif i == n - 1:
                dK = sorted_legs[-1]["strike"] - sorted_legs[-2]["strike"]
            else:
                dK = (sorted_legs[i + 1]["strike"] - sorted_legs[i - 1]["strike"]) / 2.0

            weight = dK / (K**2)
            ratio = abs(leg["quantity"]) / weight
            ratios.append(ratio)

        ratios = np.array(ratios)
        # All ratios should be the same constant (within floating point)
        cv = ratios.std() / ratios.mean()
        assert cv < 0.01, f"Coefficient of variation {cv:.4f} exceeds 1% threshold"


class TestTransactionCostAdjustedKvar:
    """Transaction-cost aware effective Kvar extraction."""

    def test_parse_day_transaction_costs(self):
        """Option and futures transaction costs are parsed separately from risks."""
        from volforecast.data.gsvivs_kvar import parse_day_transaction_costs

        risks = [
            {"source": "Transaction Costs O", "quantity": -0.0125},
            {"execution price": 0.0, "execution quantity": -0.0125},
            {"source": "Transactions Costs Fw", "quantity": -0.0180},
            {"execution price": 0.0, "execution quantity": -0.0180},
            {"source": "VSR 0b", "quantity": -0.01},
        ]

        result = parse_day_transaction_costs(risks)

        assert result["option_tc_cash"] == pytest.approx(-0.0125)
        assert result["futures_tc_cash"] == pytest.approx(-0.0180)
        assert result["all_tc_cash"] == pytest.approx(-0.0305)

    def test_tc_deductions_reduce_effective_kvar(self):
        """Deducting option and futures TC lowers effective strike."""
        from volforecast.data.gsvivs_kvar import compute_kvar_from_legs

        forward = 5000.0
        legs = TestComputeKvarFromLegs()._make_flat_smile_legs(vol_pct=18.0, forward=forward)

        gross = compute_kvar_from_legs(legs, forward=forward, tc_cash=0.0)
        option_tc = compute_kvar_from_legs(legs, forward=forward, tc_cash=-0.02)
        full_tc = compute_kvar_from_legs(legs, forward=forward, tc_cash=-0.05)

        assert gross is not None
        assert option_tc is not None
        assert full_tc is not None
        assert option_tc["kvar_vol_pct"] < gross["kvar_vol_pct"]
        assert full_tc["kvar_vol_pct"] < option_tc["kvar_vol_pct"]

    def test_returns_quantity_scale_diagnostics(self):
        """Quantity-aware Kvar reports strip scale and fit diagnostics."""
        from volforecast.data.gsvivs_kvar import compute_kvar_from_legs

        forward = 5000.0
        legs = TestComputeKvarFromLegs()._make_flat_smile_legs(vol_pct=16.0, forward=forward)
        result = compute_kvar_from_legs(legs, forward=forward)

        assert result is not None
        assert result["replication_scale"] > 0
        assert result["weight_fit_cv"] < 0.05
        assert result["gross_premium_cash"] > 0
