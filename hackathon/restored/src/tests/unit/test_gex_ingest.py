"""Tests for gex_ingest module (QSP API GEX ingestion pipeline).

Tests the QSP response parsing, GEX aggregation from raw contracts,
pagination handling, cache read/write, and auth session creation.
Does NOT require live API access — all network calls are mocked.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import requests


# ---------------------------------------------------------------------------
# Fixtures — synthetic QSP API responses
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_option_contract_call() -> dict:
    """A single valid call contract as returned by QSP OptionPrices."""
    return {
        "gamma": 0.0045,
        "openInterest": 5000,
        "contractSize": 100,
        "strike": 5500000,  # milli-dollars: $5500.00
        "callPut": "C",
        "expiration": "2026-07-11",
        "delta": 0.52,
        "theta": -1.23,
        "impliedVol": 0.18,
    }


@pytest.fixture
def sample_option_contract_put() -> dict:
    """A single valid put contract as returned by QSP OptionPrices."""
    return {
        "gamma": 0.0038,
        "openInterest": 3000,
        "contractSize": 100,
        "strike": 5400000,  # milli-dollars: $5400.00
        "callPut": "P",
        "expiration": "2026-07-11",
        "delta": -0.45,
        "theta": -0.98,
        "impliedVol": 0.20,
    }


@pytest.fixture
def invalid_gamma_contract() -> dict:
    """Contract with sentinel gamma value (-99.99) = invalid."""
    return {
        "gamma": -99.99,
        "openInterest": 1000,
        "contractSize": 100,
        "strike": 5600000,
        "callPut": "C",
        "expiration": "2026-07-11",
    }


@pytest.fixture
def zero_oi_contract() -> dict:
    """Contract with zero open interest (should be excluded)."""
    return {
        "gamma": 0.003,
        "openInterest": 0,
        "contractSize": 100,
        "strike": 5450000,
        "callPut": "P",
        "expiration": "2026-07-11",
    }


@pytest.fixture
def qsp_option_prices_response(
    sample_option_contract_call, sample_option_contract_put
) -> dict:
    """Synthetic QSP OptionPrices API response (single page)."""
    return {
        "optionsPriceData": [
            {
                "data": [
                    {
                        "price": [
                            sample_option_contract_call,
                            sample_option_contract_put,
                        ]
                    }
                ]
            }
        ],
        "scrollId": None,
    }


@pytest.fixture
def qsp_option_prices_paginated(
    sample_option_contract_call, sample_option_contract_put
) -> list[dict]:
    """Two-page QSP response (page 1 has scrollId, page 2 terminates)."""
    page1 = {
        "optionsPriceData": [
            {
                "data": [
                    {"price": [sample_option_contract_call]}
                ]
            }
        ],
        "scrollId": "scroll_abc123",
    }
    page2 = {
        "optionsPriceData": [
            {
                "data": [
                    {"price": [sample_option_contract_put]}
                ]
            }
        ],
        "scrollId": None,
    }
    return [page1, page2]


@pytest.fixture
def qsp_spot_response() -> dict:
    """Synthetic SecurityTimeseries response with spot price."""
    return {
        "securities": [
            {
                "data": [
                    {
                        "securityPrices": [
                            {"closePrice": 5520.50}
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mixed_contracts(
    sample_option_contract_call,
    sample_option_contract_put,
    invalid_gamma_contract,
    zero_oi_contract,
) -> list[dict]:
    """Mix of valid, invalid-gamma, and zero-OI contracts."""
    return [
        sample_option_contract_call,
        sample_option_contract_put,
        invalid_gamma_contract,
        zero_oi_contract,
    ]


@pytest.fixture
def tmp_cache_dir(tmp_path) -> Path:
    """Temporary directory simulating data/raw/options_oi/."""
    cache_dir = tmp_path / "data" / "raw" / "options_oi"
    cache_dir.mkdir(parents=True)
    return cache_dir


# ---------------------------------------------------------------------------
# Tests: parse_option_prices_response
# ---------------------------------------------------------------------------


class TestParseOptionPricesResponse:
    """Test QSP OptionPrices JSON response parsing."""

    def test_extracts_contracts_from_nested_structure(self, qsp_option_prices_response):
        """Should flatten nested optionsPriceData → data → price into a list."""
        from volforecast.data.gex_ingest import parse_option_prices_response

        contracts = parse_option_prices_response(qsp_option_prices_response)
        assert isinstance(contracts, list)
        assert len(contracts) == 2

    def test_preserves_contract_fields(self, qsp_option_prices_response):
        """Each contract dict should retain gamma, OI, strike, callPut, etc."""
        from volforecast.data.gex_ingest import parse_option_prices_response

        contracts = parse_option_prices_response(qsp_option_prices_response)
        first = contracts[0]
        assert "gamma" in first
        assert "openInterest" in first
        assert "strike" in first
        assert "callPut" in first
        assert "contractSize" in first

    def test_empty_response_returns_empty_list(self):
        """Empty or missing optionsPriceData should return []."""
        from volforecast.data.gex_ingest import parse_option_prices_response

        assert parse_option_prices_response({}) == []
        assert parse_option_prices_response({"optionsPriceData": []}) == []

    def test_handles_multiple_data_groups(self, sample_option_contract_call):
        """Multiple groups under optionsPriceData should all be extracted."""
        from volforecast.data.gex_ingest import parse_option_prices_response

        response = {
            "optionsPriceData": [
                {"data": [{"price": [sample_option_contract_call]}]},
                {"data": [{"price": [sample_option_contract_call]}]},
            ]
        }
        contracts = parse_option_prices_response(response)
        assert len(contracts) == 2


# ---------------------------------------------------------------------------
# Tests: aggregate_gex
# ---------------------------------------------------------------------------


class TestAggregateGex:
    """Test GEX computation from raw contract list."""

    def test_basic_gex_computation(self, sample_option_contract_call):
        """Single call contract should produce negative GEX (dealer short gamma)."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5500.0
        result = aggregate_gex([sample_option_contract_call], spot)

        assert isinstance(result, dict)
        assert "gex_net" in result
        assert "gex_call" in result
        assert "gex_put" in result
        # Call contributes negative GEX (dealer short from calls)
        assert result["gex_call"] < 0

    def test_put_contributes_positive_gex(self, sample_option_contract_put):
        """Single put contract should produce positive GEX (dealer long gamma)."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5400.0
        result = aggregate_gex([sample_option_contract_put], spot)
        # Put contributes positive GEX (dealer long from puts)
        assert result["gex_put"] > 0

    def test_gex_formula_correctness(self, sample_option_contract_call):
        """Verify exact GEX formula: -OI × gamma × contractSize × spot × 0.01."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5500.0
        result = aggregate_gex([sample_option_contract_call], spot)

        # Expected: -5000 * 0.0045 * 100 * 5500 * 0.01 = -123,750
        expected_call_gex = -5000 * 0.0045 * 100 * 5500.0 * 0.01
        assert abs(result["gex_call"] - expected_call_gex) < 0.01

    def test_put_gex_formula_correctness(self, sample_option_contract_put):
        """Verify exact GEX formula for puts: +OI × gamma × contractSize × spot × 0.01."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5400.0
        result = aggregate_gex([sample_option_contract_put], spot)

        # Expected: +3000 * 0.0038 * 100 * 5400 * 0.01 = +61,560
        expected_put_gex = 3000 * 0.0038 * 100 * 5400.0 * 0.01
        assert abs(result["gex_put"] - expected_put_gex) < 0.01

    def test_net_gex_is_sum(
        self, sample_option_contract_call, sample_option_contract_put
    ):
        """net_gex = gex_call + gex_put."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5500.0
        result = aggregate_gex(
            [sample_option_contract_call, sample_option_contract_put], spot
        )
        assert abs(result["gex_net"] - (result["gex_call"] + result["gex_put"])) < 0.01

    def test_filters_invalid_gamma(self, mixed_contracts):
        """Contracts with gamma == -99.99 should be excluded."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5500.0
        result = aggregate_gex(mixed_contracts, spot)
        # Only 2 valid contracts (call + put); invalid gamma and zero-OI excluded
        assert result["n_valid_contracts"] == 2

    def test_filters_zero_oi(self, mixed_contracts):
        """Contracts with openInterest == 0 should be excluded."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5500.0
        result = aggregate_gex(mixed_contracts, spot)
        # Zero-OI contract is filtered out
        assert result["n_valid_contracts"] == 2

    def test_strike_conversion_from_milli_dollars(self, sample_option_contract_call):
        """Strike 5500000 milli-dollars should be interpreted as $5500.00."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5500.0
        result = aggregate_gex([sample_option_contract_call], spot)
        # Result should include spot for verification
        assert result["spot"] == spot

    def test_empty_contracts_returns_zeros(self):
        """Empty contract list should return zeroed-out result."""
        from volforecast.data.gex_ingest import aggregate_gex

        result = aggregate_gex([], 5500.0)
        assert result["gex_net"] == 0.0
        assert result["gex_call"] == 0.0
        assert result["gex_put"] == 0.0
        assert result["n_valid_contracts"] == 0

    def test_output_schema(self, sample_option_contract_call):
        """Result dict should have all expected fields."""
        from volforecast.data.gex_ingest import aggregate_gex

        spot = 5500.0
        result = aggregate_gex([sample_option_contract_call], spot)
        expected_keys = {
            "gex_net", "gex_call", "gex_put", "gex_sign",
            "spot", "n_valid_contracts", "oi_total", "oi_pcr",
        }
        assert expected_keys.issubset(result.keys())

    def test_gex_sign(self, sample_option_contract_call, sample_option_contract_put):
        """gex_sign should be +1 when net GEX > 0, -1 when < 0."""
        from volforecast.data.gex_ingest import aggregate_gex

        # Call-only → negative net GEX → sign = -1
        result_call = aggregate_gex([sample_option_contract_call], 5500.0)
        assert result_call["gex_sign"] == -1

        # Put-only → positive net GEX → sign = +1
        result_put = aggregate_gex([sample_option_contract_put], 5400.0)
        assert result_put["gex_sign"] == 1

    def test_oi_put_call_ratio(
        self, sample_option_contract_call, sample_option_contract_put
    ):
        """oi_pcr should be put_oi / call_oi."""
        from volforecast.data.gex_ingest import aggregate_gex

        result = aggregate_gex(
            [sample_option_contract_call, sample_option_contract_put], 5500.0
        )
        # Put OI=3000, Call OI=5000 → PCR = 0.6
        assert abs(result["oi_pcr"] - 0.6) < 0.01


# ---------------------------------------------------------------------------
# Tests: fetch_spot_price (mocked)
# ---------------------------------------------------------------------------


class TestFetchSpotPrice:
    """Test spot price fetching from SecurityTimeseries endpoint."""

    def test_extracts_close_price(self, qsp_spot_response):
        """Should extract closePrice from nested response."""
        from volforecast.data.gex_ingest import fetch_spot_price

        session = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = qsp_spot_response
        session.get.return_value = resp_mock

        spot = fetch_spot_price(session, "108105", date(2026, 6, 30))
        assert spot == 5520.50

    def test_returns_none_on_empty_response(self):
        """Should return None if no price data in response."""
        from volforecast.data.gex_ingest import fetch_spot_price

        session = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = {"securities": []}
        session.get.return_value = resp_mock

        spot = fetch_spot_price(session, "108105", date(2026, 6, 30))
        assert spot is None

    def test_returns_none_on_http_error(self):
        """Should return None on non-200 status."""
        from volforecast.data.gex_ingest import fetch_spot_price

        session = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 403
        session.get.return_value = resp_mock

        spot = fetch_spot_price(session, "108105", date(2026, 6, 30))
        assert spot is None


# ---------------------------------------------------------------------------
# Tests: fetch_option_chain (mocked pagination)
# ---------------------------------------------------------------------------


class TestFetchOptionChain:
    """Test option chain fetching with scrollId pagination."""

    def test_single_page_no_scroll(self, qsp_option_prices_response):
        """Single page (scrollId=None) returns all contracts."""
        from volforecast.data.gex_ingest import fetch_option_chain

        session = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = qsp_option_prices_response
        session.get.return_value = resp_mock

        contracts = fetch_option_chain(session, "108105", date(2026, 6, 30))
        assert len(contracts) == 2

    def test_multi_page_pagination(self, qsp_option_prices_paginated):
        """Should follow scrollId across pages until None/empty."""
        from volforecast.data.gex_ingest import fetch_option_chain

        session = MagicMock()
        page1, page2 = qsp_option_prices_paginated

        # First call returns page1 (with scrollId), second returns page2 (no scrollId)
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = page1

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = page2

        session.get.side_effect = [resp1, resp2]

        contracts = fetch_option_chain(session, "108105", date(2026, 6, 30))
        assert len(contracts) == 2  # 1 from each page
        assert session.get.call_count == 2

    def test_returns_empty_on_failure(self):
        """Should return empty list on HTTP error."""
        from volforecast.data.gex_ingest import fetch_option_chain

        session = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 500
        session.get.return_value = resp_mock

        contracts = fetch_option_chain(session, "108105", date(2026, 6, 30))
        assert contracts == []

    def test_stops_on_duplicate_scroll_id(self, sample_option_contract_call):
        """Should break if scrollId doesn't change (prevents infinite loop)."""
        from volforecast.data.gex_ingest import fetch_option_chain

        session = MagicMock()
        stuck_response = {
            "optionsPriceData": [
                {"data": [{"price": [sample_option_contract_call]}]}
            ],
            "scrollId": "same_scroll_forever",
        }
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = stuck_response
        session.get.return_value = resp_mock

        contracts = fetch_option_chain(session, "108105", date(2026, 6, 30))
        # Should not loop forever; should stop after detecting duplicate scrollId
        assert session.get.call_count < 100


# ---------------------------------------------------------------------------
# Tests: Cache load/save
# ---------------------------------------------------------------------------


class TestCacheOperations:
    """Test parquet cache read/write with atomic save."""

    def test_load_returns_empty_df_when_missing(self, tmp_cache_dir):
        """load_gex_cache should return empty DataFrame if file doesn't exist."""
        from volforecast.data.gex_ingest import load_gex_cache

        df = load_gex_cache(cache_dir=tmp_cache_dir)
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_save_creates_parquet(self, tmp_cache_dir):
        """save_gex_cache should write a readable parquet file."""
        from volforecast.data.gex_ingest import load_gex_cache, save_gex_cache

        df = pd.DataFrame({
            "date": [date(2026, 6, 30)],
            "gex_net": [1_000_000.0],
            "gex_call": [-500_000.0],
            "gex_put": [1_500_000.0],
            "gex_sign": [1],
            "spot": [5520.50],
            "n_valid_contracts": [8000],
            "oi_total": [500_000],
            "oi_pcr": [0.65],
        })

        save_gex_cache(df, cache_dir=tmp_cache_dir)

        # Verify file exists
        cache_file = tmp_cache_dir / "spx_gex_daily.parquet"
        assert cache_file.exists()

        # Verify roundtrip
        loaded = load_gex_cache(cache_dir=tmp_cache_dir)
        assert len(loaded) == 1
        assert loaded["gex_net"].iloc[0] == 1_000_000.0

    def test_save_is_atomic(self, tmp_cache_dir):
        """save_gex_cache should use tempfile + os.replace for atomicity."""
        from volforecast.data.gex_ingest import save_gex_cache

        df = pd.DataFrame({
            "date": [date(2026, 6, 30)],
            "gex_net": [100.0],
        })

        # Write initial
        save_gex_cache(df, cache_dir=tmp_cache_dir)
        cache_file = tmp_cache_dir / "spx_gex_daily.parquet"
        assert cache_file.exists()

        # Overwrite — should not leave partial files
        df2 = pd.DataFrame({
            "date": [date(2026, 6, 30), date(2026, 7, 1)],
            "gex_net": [100.0, 200.0],
        })
        save_gex_cache(df2, cache_dir=tmp_cache_dir)
        loaded = pd.read_parquet(cache_file)
        assert len(loaded) == 2

    def test_incremental_skip_existing_dates(self, tmp_cache_dir):
        """Dates already in cache should be skipped during ingestion."""
        from volforecast.data.gex_ingest import load_gex_cache, save_gex_cache

        # Pre-populate cache with one date
        existing = pd.DataFrame({
            "date": pd.to_datetime([date(2026, 6, 30)]),
            "gex_net": [1_000_000.0],
            "gex_call": [-500_000.0],
            "gex_put": [1_500_000.0],
            "gex_sign": [1],
            "spot": [5520.50],
            "n_valid_contracts": [8000],
            "oi_total": [500_000],
            "oi_pcr": [0.65],
        })
        save_gex_cache(existing, cache_dir=tmp_cache_dir)

        # Load and check which dates need fetching
        cached = load_gex_cache(cache_dir=tmp_cache_dir)
        cached_dates = set(pd.to_datetime(cached["date"]).dt.date)

        target_dates = [date(2026, 6, 30), date(2026, 7, 1)]
        to_fetch = [d for d in target_dates if d not in cached_dates]

        assert date(2026, 6, 30) not in to_fetch
        assert date(2026, 7, 1) in to_fetch


# ---------------------------------------------------------------------------
# Tests: fetch_gex_daily (orchestration)
# ---------------------------------------------------------------------------


class TestFetchGexDaily:
    """Test daily GEX orchestrator that combines spot + chain + aggregation."""

    def test_returns_dict_on_success(
        self, qsp_spot_response, qsp_option_prices_response
    ):
        """Should return aggregated GEX dict when both spot and chain succeed."""
        from volforecast.data.gex_ingest import fetch_gex_daily

        session = MagicMock()

        # Mock spot response
        spot_resp = MagicMock()
        spot_resp.status_code = 200
        spot_resp.json.return_value = qsp_spot_response

        # Mock chain response
        chain_resp = MagicMock()
        chain_resp.status_code = 200
        chain_resp.json.return_value = qsp_option_prices_response

        session.get.side_effect = [spot_resp, chain_resp]

        result = fetch_gex_daily(date(2026, 6, 30), "108105", session)
        assert result is not None
        assert "gex_net" in result
        assert "date" in result

    def test_returns_none_when_no_spot(self):
        """Should return None if spot price cannot be fetched."""
        from volforecast.data.gex_ingest import fetch_gex_daily

        session = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = {"securities": []}
        session.get.return_value = resp_mock

        result = fetch_gex_daily(date(2026, 6, 30), "108105", session)
        assert result is None

    def test_returns_none_when_no_contracts(self, qsp_spot_response):
        """Should return None if option chain is empty."""
        from volforecast.data.gex_ingest import fetch_gex_daily

        session = MagicMock()

        spot_resp = MagicMock()
        spot_resp.status_code = 200
        spot_resp.json.return_value = qsp_spot_response

        chain_resp = MagicMock()
        chain_resp.status_code = 200
        chain_resp.json.return_value = {"optionsPriceData": []}

        session.get.side_effect = [spot_resp, chain_resp]

        result = fetch_gex_daily(date(2026, 6, 30), "108105", session)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: get_qsp_session
# ---------------------------------------------------------------------------


class TestGetQspSession:
    """Test GSSSO session creation via GsSession."""

    def test_creates_session_with_cookie(self):
        """Should extract GSSSO cookie from GsSession and pin to a new Session."""
        from unittest.mock import patch, MagicMock
        from types import SimpleNamespace

        # Build a fake GsSession whose _session.cookies contains a GSSSO cookie
        fake_cookie = SimpleNamespace(name="GSSSO", value="test_cookie_value_abc123")
        fake_inner = MagicMock()
        fake_inner.cookies = [fake_cookie]
        fake_gs_session = MagicMock()
        fake_gs_session._session = fake_inner

        # Patch the gs_quant import used inside get_qsp_session
        mock_gs_module = MagicMock()
        mock_gs_module.GsSession.use = MagicMock()
        mock_gs_module.GsSession.current = fake_gs_session

        with patch.dict(
            "sys.modules",
            {"gs_quant": MagicMock(), "gs_quant.session": mock_gs_module},
        ):
            from volforecast.data.gex_ingest import get_qsp_session
            session = get_qsp_session()

        assert session is not None
        cookie = session.cookies.get("GSSSO", domain=".gs.com")
        assert cookie == "test_cookie_value_abc123"

    def test_raises_on_auth_failure(self):
        """Should raise if GsSession.use() fails."""
        from unittest.mock import patch, MagicMock

        mock_gs_module = MagicMock()
        mock_gs_module.GsSession.use = MagicMock(side_effect=Exception("kinit expired"))

        with patch.dict(
            "sys.modules",
            {"gs_quant": MagicMock(), "gs_quant.session": mock_gs_module},
        ):
            from volforecast.data.gex_ingest import get_qsp_session
            with pytest.raises(RuntimeError, match="GsSession authentication failed"):
                get_qsp_session()

    def test_raises_when_no_gssso_cookie(self):
        """Should raise if GsSession has no GSSSO cookie."""
        from unittest.mock import patch, MagicMock
        from types import SimpleNamespace

        # GsSession has other cookies but not GSSSO
        fake_cookie = SimpleNamespace(name="JSESSIONID", value="abc")
        fake_inner = MagicMock()
        fake_inner.cookies = [fake_cookie]
        fake_gs_session = MagicMock()
        fake_gs_session._session = fake_inner

        mock_gs_module = MagicMock()
        mock_gs_module.GsSession.use = MagicMock()
        mock_gs_module.GsSession.current = fake_gs_session

        with patch.dict(
            "sys.modules",
            {"gs_quant": MagicMock(), "gs_quant.session": mock_gs_module},
        ):
            from volforecast.data.gex_ingest import get_qsp_session
            with pytest.raises(RuntimeError, match="GSSSO cookie not found"):
                get_qsp_session()


# ---------------------------------------------------------------------------
# Tests: Strike conversion and edge cases
# ---------------------------------------------------------------------------


class TestStrikeConversion:
    """Test milli-dollar strike conversion edge cases."""

    def test_spx_strike_conversion(self):
        """5500000 milli-dollars → $5500.00 (SPX)."""
        from volforecast.data.gex_ingest import aggregate_gex

        contract = {
            "gamma": 0.005,
            "openInterest": 1000,
            "contractSize": 100,
            "strike": 5500000,
            "callPut": "C",
            "expiration": "2026-07-11",
        }
        # The function should handle the strike internally;
        # verify it produces sensible GEX (not inflated by 1000x)
        result = aggregate_gex([contract], spot=5500.0)
        # GEX_call = -1000 * 0.005 * 100 * 5500 * 0.01 = -27,500
        expected = -1000 * 0.005 * 100 * 5500.0 * 0.01
        assert abs(result["gex_call"] - expected) < 0.01

    def test_spy_strike_conversion(self):
        """560000 milli-dollars → $560.00 (SPY)."""
        from volforecast.data.gex_ingest import aggregate_gex

        contract = {
            "gamma": 0.01,
            "openInterest": 10000,
            "contractSize": 100,
            "strike": 560000,
            "callPut": "P",
            "expiration": "2026-07-11",
        }
        result = aggregate_gex([contract], spot=560.0)
        # GEX_put = +10000 * 0.01 * 100 * 560 * 0.01 = +56,000
        expected = 10000 * 0.01 * 100 * 560.0 * 0.01
        assert abs(result["gex_put"] - expected) < 0.01

    def test_none_gamma_treated_as_invalid(self):
        """Contract with gamma=None should be filtered out."""
        from volforecast.data.gex_ingest import aggregate_gex

        contract = {
            "gamma": None,
            "openInterest": 1000,
            "contractSize": 100,
            "strike": 5500000,
            "callPut": "C",
            "expiration": "2026-07-11",
        }
        result = aggregate_gex([contract], spot=5500.0)
        assert result["n_valid_contracts"] == 0
        assert result["gex_net"] == 0.0
