"""Tests for dynamic universe discovery in vol audit.

The audit universe should be derived from on-disk parquet files
merged with SYMBOL_UNIVERSE from constants, NOT a hardcoded 34-symbol list.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root with data directories and parquets."""
    for subdir in ("ticks", "iv", "ohlcv", "micro"):
        (tmp_path / "data" / "raw" / subdir).mkdir(parents=True)

    # Create parquet files for a broader set of symbols than old 34
    symbols_on_disk = ["AAPL", "MSFT", "NVDA", "AMD", "INTC", "UBER", "BA", "CAT"]
    df = pd.DataFrame({"rv": [0.01]}, index=pd.to_datetime(["2024-01-02"]))
    for sym in symbols_on_disk:
        df.to_parquet(tmp_path / "data" / "raw" / "ticks" / f"{sym}.parquet")
        df.to_parquet(tmp_path / "data" / "raw" / "ohlcv" / f"{sym}.parquet")

    return tmp_path


class TestDiscoverUniverse:
    """Dynamic universe discovery from disk."""

    def test_discovers_symbols_from_disk(self, project_root: Path):
        """Universe includes all symbols found in data/raw source dirs."""
        from volforecast.cli.audit import _discover_universe

        universe = _discover_universe(project_root)
        # All on-disk symbols should be present
        for sym in ["AAPL", "MSFT", "NVDA", "AMD", "INTC", "UBER", "BA", "CAT"]:
            assert sym in universe, f"{sym} missing from discovered universe"

    def test_includes_constants_universe(self, project_root: Path):
        """Universe is the union of on-disk + SYMBOL_UNIVERSE from constants."""
        from volforecast.cli.audit import _discover_universe
        from volforecast.constants import SYMBOL_UNIVERSE

        universe = _discover_universe(project_root)
        # Every symbol from constants should be included
        for sym in SYMBOL_UNIVERSE:
            assert sym in universe, f"{sym} from SYMBOL_UNIVERSE missing"

    def test_universe_is_sorted(self, project_root: Path):
        """Returned universe is sorted for deterministic output."""
        from volforecast.cli.audit import _discover_universe

        universe = _discover_universe(project_root)
        assert universe == sorted(universe)

    def test_no_underscore_prefixed_files(self, project_root: Path):
        """Files like _MARKET.parquet should not appear as symbols."""
        df = pd.DataFrame({"x": [1]}, index=pd.to_datetime(["2024-01-02"]))
        (project_root / "data" / "raw" / "iv").mkdir(parents=True, exist_ok=True)
        df.to_parquet(project_root / "data" / "raw" / "iv" / "_MARKET.parquet")
        df.to_parquet(project_root / "data" / "raw" / "iv" / "_VIX.parquet")

        from volforecast.cli.audit import _discover_universe

        universe = _discover_universe(project_root)
        assert "_MARKET" not in universe
        assert "_VIX" not in universe

    def test_no_duplicate_symbols(self, project_root: Path):
        """Each symbol appears only once even if present in multiple sources."""
        from volforecast.cli.audit import _discover_universe

        universe = _discover_universe(project_root)
        assert len(universe) == len(set(universe))


class TestGetUniverseFromManifest:
    """_get_universe_from_manifest uses dynamic discovery, not hardcoded list."""

    def test_fallback_uses_full_constants_universe(self):
        """When manifest has no symbols, fallback includes full SYMBOL_UNIVERSE."""
        from volforecast.cli.audit import _get_universe_fallback
        from volforecast.constants import SYMBOL_UNIVERSE

        universe = _get_universe_fallback()
        assert len(universe) >= len(SYMBOL_UNIVERSE)
        for sym in SYMBOL_UNIVERSE:
            assert sym in universe
